#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
microsis — 旧档解析与结构化提取工具
=====================================
将老旧数据/文件/URL解析为结构化结果，保留关键信息并标注置信度。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_INVALID_INPUT = "E001"      # 输入为空或类型错误
ERR_INPUT_TOO_LONG = "E002"     # 输入文本超长（>8000字符）
ERR_BATCH_TOO_LARGE = "E003"    # 批量处理条数超限（>50）
ERR_FIELD_OVERFLOW = "E004"     # 自定义字段数量超限（>20）
ERR_URL_FETCH_FAIL = "E005"     # URL抓取失败
ERR_URL_TIMEOUT = "E006"        # URL抓取超时（>10秒）
ERR_PARSE_FAIL = "E007"         # 解析失败（无法识别任何字段）
ERR_INVALID_SCHEMA = "E008"     # 自定义输出模板不合法
ERR_IO_FAIL = "E009"            # 文件读写失败
ERR_INTERNAL = "E010"           # 内部错误（未知异常）


# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------
MAX_TEXT_LEN = 8000
MAX_BATCH_SIZE = 50
MAX_FIELDS = 20
URL_TIMEOUT = 10
TRUNCATED_MARK = "[truncated]"
FETCH_TIMEOUT_MARK = "[fetch_timeout]"


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def _safe_text(text: Any) -> Tuple[str, bool]:
    """将输入转为字符串并进行长度截断。返回(处理后的文本, 是否被截断)。"""
    if text is None:
        raise ValueError(ERR_INVALID_INPUT)
    s = str(text).strip()
    if not s:
        raise ValueError(ERR_INVALID_INPUT)
    truncated = len(s) > MAX_TEXT_LEN
    if truncated:
        s = s[:MAX_TEXT_LEN] + TRUNCATED_MARK
    return s, truncated


def _confidence_score(patterns_hit: int, total_patterns: int) -> float:
    """根据命中模式比例计算置信度（0.0 ~ 1.0）。"""
    if total_patterns <= 0:
        return 0.0
    return round(min(1.0, patterns_hit / total_patterns), 2)


def _extract_date(text: str) -> Optional[str]:
    """尝试从文本中提取日期（支持多种常见格式）。"""
    patterns = [
        r"\b(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?\b",
        r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",
        r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                groups = m.groups()
                if len(groups[0]) == 4:
                    y, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
                else:
                    d, mo, y = int(groups[0]), int(groups[1]), int(groups[2])
                if 1900 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                    return f"{y:04d}-{mo:02d}-{d:02d}"
            except (ValueError, IndexError):
                continue
    return None


def _extract_entities(text: str) -> Dict[str, List[str]]:
    """提取常见实体（编号、金额、邮箱、电话、URL）。"""
    entities: Dict[str, List[str]] = {
        "ids": [],
        "amounts": [],
        "emails": [],
        "phones": [],
        "urls": [],
    }

    # 编号（数字+字母组合，如订单号/单号）
    id_pat = r"\b(?:编号|单号|订单号|编号[:：]?|No\.?[:：]?)\s*([A-Za-z0-9\-]{4,20})\b"
    entities["ids"] = list(dict.fromkeys(re.findall(id_pat, text, re.I)))

    # 金额（人民币/美元）
    amount_pat = r"(?:¥|￥|RMB|CNY|\$|USD)\s?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)"
    entities["amounts"] = list(dict.fromkeys(re.findall(amount_pat, text, re.I)))

    # 邮箱
    email_pat = r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"
    entities["emails"] = list(dict.fromkeys(re.findall(email_pat, text)))

    # 电话（简单匹配：11位手机号或带区号座机）
    phone_pat = r"\b(?:1[3-9]\d{9}|\d{3,4}[- ]?\d{7,8})\b"
    entities["phones"] = list(dict.fromkeys(re.findall(phone_pat, text)))

    # URL
    url_pat = r"https?://[^\s<>\"']+"
    entities["urls"] = list(dict.fromkeys(re.findall(url_pat, text)))

    return entities


def _detect_format(text: str) -> str:
    """检测文本大致格式类型。"""
    if re.search(r"<[a-zA-Z][^>]*>", text):
        return "markup"
    if re.search(r"^\s*\{.*\}\s*$", text, re.S):
        return "json"
    if re.search(r"^\s*\[.*\]\s*$", text, re.S):
        return "array"
    if re.search(r"\t", text):
        return "tsv"
    if re.search(r",", text) and len(text.splitlines()) > 1:
        return "csv"
    return "plain"


def _parse_key_value(text: str) -> Dict[str, Any]:
    """从文本中解析键值对字段。"""
    fields: Dict[str, Any] = {}
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 匹配 键:值 或 键=值
        m = re.match(r"^([^:=]{1,30})[:=]\s*(.+)$", line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            if key and value and key not in fields:
                fields[key] = value
    return fields


# ---------------------------------------------------------------------------
# 主解析函数
# ---------------------------------------------------------------------------
def parse_single(text: Any, custom_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """解析单条输入为结构化结果。

    参数:
        text: 输入文本（字符串或可转为字符串的对象）
        custom_fields: 自定义字段名列表（最多20个）

    返回:
        结构化字典，包含解析字段、实体、置信度等。
    """
    # 输入校验
    if text is None or (isinstance(text, str) and not text.strip()):
        raise ValueError(ERR_INVALID_INPUT)

    try:
        content, truncated = _safe_text(text)
    except ValueError:
        raise ValueError(ERR_INVALID_INPUT)

    if len(custom_fields or []) > MAX_FIELDS:
        raise ValueError(ERR_FIELD_OVERFLOW)

    # 基础结构
    result: Dict[str, Any] = {
        "schema_version": "1.0",
        "truncated": truncated,
        "format": _detect_format(content),
        "fields": {},
        "entities": {},
        "confidence": 0.0,
        "warnings": [],
    }

    # 提取键值对字段
    kv_fields = _parse_key_value(content)
    result["fields"].update(kv_fields)

    # 提取实体
    entities = _extract_entities(content)
    result["entities"] = entities

    # 提取日期
    date_val = _extract_date(content)
    if date_val:
        result["fields"]["date"] = date_val

    # 自定义字段：从文本中尝试匹配
    if custom_fields:
        for f in custom_fields[:MAX_FIELDS]:
            if f not in result["fields"]:
                pat = re.compile(rf"{re.escape(f)}[:=]\s*([^\n,;]+)")
                m = pat.search(content)
                if m:
                    result["fields"][f] = m.group(1).strip()
                else:
                    result["fields"][f] = None

    # 计算置信度
    pattern_hits = 0
    total_patterns = 4  # 键值对、日期、实体、格式识别
    if kv_fields:
        pattern_hits += 1
    if date_val:
        pattern_hits += 1
    if any(entities.values()):
        pattern_hits += 1
    if result["format"] != "plain":
        pattern_hits += 1
    result["confidence"] = _confidence_score(pattern_hits, total_patterns)

    # 空结果检查
    if not kv_fields and not any(entities.values()) and not date_val:
        result["warnings"].append("未能识别出有效字段")

    return result


def parse_batch(items: List[Any], custom_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """批量解析多条输入。"""
    if not items:
        raise ValueError(ERR_INVALID_INPUT)
    if len(items) > MAX_BATCH_SIZE:
        raise ValueError(ERR_BATCH_TOO_LARGE)

    results = []
    for item in items:
        try:
            results.append(parse_single(item, custom_fields))
        except ValueError as e:
            results.append({
                "error": str(e),
                "message": f"解析失败: {e}",
            })
    return results


def fetch_url(url: str) -> str:
    """从URL抓取文本内容（超时10秒）。"""
    if not url.startswith(("http://", "https://")):
        raise ValueError(ERR_URL_FETCH_FAIL)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "microsis/1.0"})
        with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as resp:
            data = resp.read()
            # 尝试多种编码
            for enc in ("utf-8", "gbk", "latin-1"):
                try:
                    return data.decode(enc)
                except UnicodeDecodeError:
                    continue
            return data.decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        raise ValueError(ERR_URL_FETCH_FAIL)
    except Exception:
        raise ValueError(ERR_URL_TIMEOUT)


def parse_url(url: str, custom_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """解析URL指向的文本资源。"""
    try:
        content = fetch_url(url)
    except ValueError as e:
        return {
            "error": str(e),
            "message": "URL抓取失败",
            "url": url,
        }
    return parse_single(content, custom_fields)


def _merge_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """合并多条解析结果为汇总结构。"""
    merged: Dict[str, Any] = {
        "count": len(results),
        "success_count": 0,
        "error_count": 0,
        "items": results,
        "summary": {},
    }

    # 统计成功/失败
    for r in results:
        if "error" in r:
            merged["error_count"] += 1
        else:
            merged["success_count"] += 1

    # 汇总字段出现频次
    field_freq: Dict[str, int] = {}
    for r in results:
        if "fields" in r:
            for k in r["fields"].keys():
                field_freq[k] = field_freq.get(k, 0) + 1
    merged["summary"]["field_frequency"] = field_freq

    # 平均置信度
    confidences = [r.get("confidence", 0.0) for r in results if "confidence" in r]
    if confidences:
        merged["summary"]["avg_confidence"] = round(sum(confidences) / len(confidences), 2)

    return merged


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    """内置自检：使用硬编码样例数据验证核心逻辑。"""
    print("[selftest] 开始自检...")
    failures = 0

    # 测试1: 单条解析 - 键值对
    try:
        sample1 = "订单号: ABC12345, 金额: ￥1,234.56, 日期: 2024-03-15"
        r1 = parse_single(sample1)
        assert "ABC12345" in str(r1.get("fields", {})), "订单号提取失败"
        assert "1,234.56" in str(r1.get("entities", {}).get("amounts", [])), "金额提取失败"
        assert r1.get("confidence", 0) >= 0.5, "置信度过低"
        print("  [OK] 单条解析 - 键值对")
    except Exception as e:
        print(f"  [FAIL] 单条解析: {e}")
        failures += 1

    # 测试2: 实体提取
    try:
        sample2 = "联系邮箱: test@example.com, 电话: 13800138000, 网址: https://example.com"
        r2 = parse_single(sample2)
        assert "test@example.com" in r2.get("entities", {}).get("emails", []), "邮箱提取失败"
        assert "13800138000" in r2.get("entities", {}).get("phones", []), "电话提取失败"
        assert "https://example.com" in r2.get("entities", {}).get("urls", []), "URL提取失败"
        print("  [OK] 实体提取")
    except Exception as e:
        print(f"  [FAIL] 实体提取: {e}")
        failures += 1

    # 测试3: 批量解析
    try:
        items = ["名称: 项目A, 状态: 进行中", "名称: 项目B, 状态: 已完成", "无效输入"]
        results = parse_batch(items)
        assert len(results) == 3, "批量解析数量错误"
        assert results[0].get("fields", {}).get("名称") == "项目A", "批量解析字段错误"
        assert "error" in results[2], "无效输入应返回错误"
        print("  [OK] 批量解析")
    except Exception as e:
        print(f"  [FAIL] 批量解析: {e}")
        failures += 1

    # 测试4: 输入截断
    try:
        long_text = "内容" * 5000  # 10000字符
        r4 = parse_single(long_text)
        assert r4.get("truncated") is True, "长文本应被截断"
        assert TRUNCATED_MARK in str(r4), "截断标记缺失"
        print("  [OK] 输入截断")
    except Exception as e:
        print(f"  [FAIL] 输入截断: {e}")
        failures += 1

    # 测试5: 错误处理
    try:
        try:
            parse_single("")
            assert False, "空输入应报错"
        except ValueError as e:
            assert str(e) == ERR_INVALID_INPUT, f"错误码错误: {e}"

        try:
            parse_batch([1] * 51)
            assert False, "超批量应报错"
        except ValueError as e:
            assert str(e) == ERR_BATCH_TOO_LARGE, f"错误码错误: {e}"

        print("  [OK] 错误处理")
    except Exception as e:
        print(f"  [FAIL] 错误处理: {e}")
        failures += 1

    # 测试6: 日期提取
    try:
        sample6 = "创建于2024年1月5日，编号: X-001"
        r6 = parse_single(sample6)
        assert r6.get("fields", {}).get("date") == "2024-01-05", f"日期提取错误: {r6.get('fields', {}).get('date')}"
        print("  [OK] 日期提取")
    except Exception as e:
        print(f"  [FAIL] 日期提取: {e}")
        failures += 1

    # 测试7: 合并结果
    try:
        results = [
            parse_single("名称: 甲, 金额: ￥100"),
            parse_single("名称: 乙, 金额: ￥200"),
        ]
        merged = _merge_results(results)
        assert merged["count"] == 2, "合并数量错误"
        assert merged["success_count"] == 2, "成功数量错误"
        assert "名称" in merged["summary"]["field_frequency"], "字段频次统计错误"
        print("  [OK] 结果合并")
    except Exception as e:
        print(f"  [FAIL] 结果合并: {e}")
        failures += 1

    print(f"\n[selftest] 完成: {7 - failures}/7 通过")
    return 0 if failures == 0 else 1


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="microsis - 旧档解析与结构化提取工具"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入文本、文件路径或URL（以http://或https://开头）"
    )
    parser.add_argument(
        "-f", "--file",
        help="从文件读取输入"
    )
    parser.add_argument(
        "-u", "--url",
        help="从URL抓取文本"
    )
    parser.add_argument(
        "--fields",
        help="自定义字段列表，逗号分隔"
    )
    parser.add_argument(
        "--batch-file",
        help="批量处理文件（每行一条记录）"
    )
    parser.add_argument(
        "--output",
        help="输出文件路径（默认输出到stdout）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部资源）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 解析自定义字段
    custom_fields = None
    if args.fields:
        custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    try:
        results = None
        source_desc = ""

        # 处理URL
        if args.url:
            source_desc = f"URL: {args.url}"
            r = parse_url(args.url, custom_fields)
            results = [r]

        # 处理文件
        elif args.file:
            source_desc = f"文件: {args.file}"
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                print(f"错误码 {ERR_IO_FAIL}: 无法读取文件 {args.file}", file=sys.stderr)
                return 1
            results = [parse_single(content, custom_fields)]

        # 批量文件
        elif args.batch_file:
            source_desc = f"批量文件: {args.batch_file}"
            try:
                with open(args.batch_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except OSError:
                print(f"错误码 {ERR_IO_FAIL}: 无法读取文件 {args.batch_file}", file=sys.stderr)
                return 1
            try:
                parsed_items = parse_batch(lines, custom_fields)
                results = [_merge_results(parsed_items)]
            except ValueError as e:
                print(f"错误码 {e}: 批量处理失败", file=sys.stderr)
                return 1

        # 命令行直接输入
        elif args.input:
            source_desc = "命令行输入"
            results = [parse_single(args.input, custom_fields)]

        # 无输入
        else:
            parser.print_help()
            return 1

        # 输出结果
        output_data = {
            "source": source_desc,
            "timestamp": datetime.now().isoformat(),
            "results": results,
        }
        output_json = json.dumps(output_data, ensure_ascii=False, indent=2)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
            except OSError:
                print(f"错误码 {ERR_IO_FAIL}: 无法写入文件 {args.output}", file=sys.stderr)
                return 1
        else:
            print(output_json)

        return 0

    except ValueError as e:
        print(f"错误码 {e}: 输入处理失败", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误码 {ERR_INTERNAL}: 内部错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
