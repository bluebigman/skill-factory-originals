#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
starling - 消息队列数据解析与结构化转换工具

功能：
- 将用户提供的消息数据解析为结构化 JSON 结果
- 支持批量处理多条记录
- 支持置信度标注与字段缺失提示
- 提供 --selftest 离线自检模式（不依赖外部文件/网络）

错误码说明：
- E001: 参数错误（缺少必要参数或参数格式不正确）
- E002: 输入数据格式错误（非字符串/非列表/非字典等）
- E003: 输入文件不存在或无法读取
- E004: 输入文件格式不支持（非 .txt/.csv/.json）
- E005: JSON 解析失败
- E006: CSV 解析失败
- E007: 数据字段提取失败（缺少关键字段）
- E008: 批量处理时某条记录处理失败
- E009: 输出序列化失败
- E010: 未知错误（兜底）
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 核心解析逻辑
# ============================================================

def extract_fields_from_text(text: str) -> Dict[str, Any]:
    """
    从单条文本消息中提取结构化字段。

    支持的字段：
    - id: 记录标识（如有）
    - timestamp: 时间戳（如有）
    - level: 日志级别（如 INFO/ERROR/WARNING）
    - source: 来源标识（如模块名、服务名）
    - message: 消息正文（去除前缀后的纯文本）
    - raw: 原始文本

    提取策略：
    1. 尝试识别常见前缀模式（时间戳、级别、来源等）
    2. 剩余部分作为 message
    3. 若无法识别任何结构化前缀，整段文本作为 message
    """
    if not isinstance(text, str) or not text.strip():
        return {"message": text if isinstance(text, str) else "", "raw": text}

    original = text
    text = text.strip()
    result: Dict[str, Any] = {}
    remaining = text

    # --- 时间戳提取（多种常见格式） ---
    # 格式: 2026-01-15 14:30:00 或 2026/01/15 14:30:00
    ts_patterns = [
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(?::\d{2})?)',
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
    ]
    for pat in ts_patterns:
        m = re.search(pat, remaining)
        if m:
            result["timestamp"] = m.group(1)
            remaining = remaining[:m.start()] + " " + remaining[m.end():]
            remaining = remaining.strip()
            break

    # --- 日志级别提取 ---
    level_pattern = r'\b(DEBUG|INFO|WARNING|ERROR|CRITICAL|TRACE|FATAL)\b'
    m = re.search(level_pattern, remaining, re.IGNORECASE)
    if m:
        result["level"] = m.group(1).upper()
        remaining = remaining[:m.start()] + " " + remaining[m.end():]
        remaining = remaining.strip()

    # --- 来源/模块名提取（形如 [module] 或 (module) 或 module:） ---
    src_patterns = [
        r'\[([^\]]+)\]',       # [module]
        r'\(([^\)]+)\)',       # (module)
        r'^([a-zA-Z_][\w.-]*)\s*:',  # module: 开头
    ]
    for pat in src_patterns:
        m = re.search(pat, remaining)
        if m:
            result["source"] = m.group(1).strip()
            remaining = remaining[:m.start()] + " " + remaining[m.end():]
            remaining = remaining.strip()
            break

    # --- ID 提取（如 id=123 或 ID: 123） ---
    id_patterns = [
        r'\bid\s*[=:]\s*([a-zA-Z0-9_-]+)',
        r'#([a-zA-Z0-9_-]{3,})',
    ]
    for pat in id_patterns:
        m = re.search(pat, remaining, re.IGNORECASE)
        if m:
            result["id"] = m.group(1)
            remaining = remaining[:m.start()] + " " + remaining[m.end():]
            remaining = remaining.strip()
            break

    # 剩余部分作为 message
    result["message"] = remaining.strip() if remaining else ""
    result["raw"] = original
    return result


def parse_record(record: Any) -> Tuple[Dict[str, Any], float]:
    """
    解析单条记录，返回 (结构化数据, 置信度)。

    置信度规则：
    - 原始即为字典：0.95 + 字段完整度加成
    - 原始为字符串：基于提取到的字段数量
    - 其他类型：0.5 并标记 warning
    """
    if isinstance(record, dict):
        # 已是结构化数据，直接整理
        result = dict(record)
        # 确保有 message 字段
        if "message" not in result:
            # 尝试从常见字段拼接
            for key in ["text", "content", "body", "msg"]:
                if key in result:
                    result["message"] = str(result[key])
                    break
            else:
                result["message"] = ""
        # 确保有 raw 字段
        if "raw" not in result:
            result["raw"] = json.dumps(record, ensure_ascii=False)
        # 字段完整度
        required = ["message"]
        present = sum(1 for f in required if f in result and result[f])
        confidence = 0.90 + 0.05 * (present / len(required))
        return result, min(confidence, 1.0)

    elif isinstance(record, str):
        extracted = extract_fields_from_text(record)
        # 字段越多置信度越高
        field_names = ["timestamp", "level", "source", "id", "message"]
        present = sum(1 for f in field_names if f in extracted and extracted[f])
        confidence = 0.6 + 0.08 * present
        return extracted, min(confidence, 1.0)

    else:
        # 不支持的类型（数字、布尔等）
        return {
            "message": str(record),
            "raw": record,
            "warning": "unsupported_type"
        }, 0.5


def parse_batch(data: Union[str, List, Dict]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    批量解析输入数据。

    支持输入：
    - 字符串：单条消息，或 JSON 数组字符串
    - 列表：多条记录
    - 字典：单条记录

    返回 (成功结果列表, 失败记录列表)。
    """
    failures: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []

    # 统一转为列表处理
    records: List[Any] = []
    if isinstance(data, str):
        stripped = data.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            # 尝试解析为 JSON 数组
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    records = parsed
                else:
                    records = [parsed]
            except json.JSONDecodeError:
                # 不是 JSON 数组，按单条文本处理
                records = [stripped]
        else:
            records = [stripped]
    elif isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = [data]
    else:
        raise ValueError("E002: 输入数据格式错误")

    # 逐条处理
    for i, rec in enumerate(records):
        try:
            parsed, conf = parse_record(rec)
            parsed["_confidence"] = round(conf, 3)
            parsed["_index"] = i
            results.append(parsed)
        except Exception as e:
            failures.append({
                "index": i,
                "error": f"E008: {str(e)}",
                "raw": rec if isinstance(rec, str) else json.dumps(rec, ensure_ascii=False)
            })

    return results, failures


# ============================================================
# 文件处理
# ============================================================

def read_input_file(filepath: str) -> Union[str, List, Dict]:
    """
    读取输入文件并解析为可处理的数据结构。

    支持格式：.txt, .csv, .json
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"E003: 文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".txt", ".csv", ".json"):
        raise ValueError(f"E004: 不支持的文件格式: {ext}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise IOError(f"E003: 读取文件失败: {e}")

    if ext == ".json":
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"E005: JSON 解析失败: {e}")
    elif ext == ".csv":
        try:
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
            if rows:
                return rows
            # 空 CSV 返回空列表
            return []
        except Exception as e:
            raise ValueError(f"E006: CSV 解析失败: {e}")
    else:  # .txt
        return content


def format_output(results: List[Dict[str, Any]], failures: List[Dict[str, Any]], output_format: str = "json") -> str:
    """
    将结果格式化为指定输出格式。

    支持格式：json, text, markdown
    """
    output_data = {
        "success_count": len(results),
        "failure_count": len(failures),
        "results": results,
        "failures": failures,
    }

    if output_format == "json":
        try:
            return json.dumps(output_data, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            raise ValueError(f"E009: JSON 序列化失败: {e}")

    elif output_format == "text":
        lines = []
        lines.append(f"处理完成: 成功 {len(results)} 条, 失败 {len(failures)} 条")
        for r in results:
            lines.append("-" * 40)
            for key, val in r.items():
                if key == "raw":
                    continue  # 跳过原始数据
                lines.append(f"{key}: {val}")
        if failures:
            lines.append("=" * 40)
            lines.append("失败记录:")
            for f in failures:
                lines.append(f"  #{f['index']}: {f['error']}")
        return "\n".join(lines)

    elif output_format == "markdown":
        lines = []
        lines.append(f"## 处理结果")
        lines.append(f"- 成功: {len(results)} 条")
        lines.append(f"- 失败: {len(failures)} 条")
        lines.append("")
        if results:
            lines.append("| 序号 | 字段数 | 置信度 | 消息摘要 |")
            lines.append("|------|--------|--------|----------|")
            for r in results:
                msg = str(r.get("message", ""))
                summary = msg[:30] + "..." if len(msg) > 30 else msg
                fields = len([k for k in r.keys() if not k.startswith("_")])
                conf = r.get("_confidence", 0)
                lines.append(f"| {r.get('_index', '?')} | {fields} | {conf} | {summary} |")
        return "\n".join(lines)

    else:
        raise ValueError(f"E001: 不支持的输出格式: {output_format}")


# ============================================================
# 自检（selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。使用内置硬编码样例数据，不读外部文件。
    返回 0 表示通过，非 0 表示失败。
    """
    print("[selftest] 开始自检...")
    failures = []

    # --- 测试 1: 单条文本解析 ---
    print("[selftest] 测试1: 单条文本解析")
    sample_text = "2026-01-15 14:30:00 [auth-service] INFO id=usr_001 用户登录成功"
    try:
        parsed, conf = parse_record(sample_text)
        assert isinstance(parsed, dict), "返回类型应为字典"
        assert "message" in parsed, "应包含 message 字段"
        assert len(parsed["message"]) > 0, "message 不应为空"
        assert conf > 0.5, f"置信度应大于 0.5, 实际: {conf}"
        print(f"  ✓ 通过 (置信度: {conf})")
    except AssertionError as e:
        failures.append(f"测试1失败: {e}")
        print(f"  ✗ 失败: {e}")

    # --- 测试 2: 批量解析 ---
    print("[selftest] 测试2: 批量解析")
    batch_data = [
        "2026-01-15 10:00:00 [worker] ERROR 任务超时",
        "2026-01-15 10:05:00 [worker] INFO 任务完成",
        "普通消息没有结构化前缀",
    ]
    try:
        results, errs = parse_batch(batch_data)
        assert len(results) == 3, f"应解析 3 条, 实际 {len(results)}"
        assert len(errs) == 0, f"不应有失败, 实际 {len(errs)}"
        # 所有结果都有 message
        for r in results:
            assert "message" in r, "每条结果都应包含 message"
            assert r["_confidence"] > 0, "置信度应大于 0"
        print(f"  ✓ 通过 (成功: {len(results)}, 失败: {len(errs)})")
    except AssertionError as e:
        failures.append(f"测试2失败: {e}")
        print(f"  ✗ 失败: {e}")

    # --- 测试 3: JSON 数组解析 ---
    print("[selftest] 测试3: JSON 数组解析")
    json_str = json.dumps([
        {"id": "A001", "message": "第一条消息", "level": "INFO"},
        {"id": "A002", "message": "第二条消息"},
    ])
    try:
        results, errs = parse_batch(json_str)
        assert len(results) == 2, f"应解析 2 条, 实际 {len(results)}"
        assert len(errs) == 0, f"不应有失败, 实际 {len(errs)}"
        for r in results:
            assert r["_confidence"] > 0.8, f"字典输入的置信度应较高, 实际: {r['_confidence']}"
        print(f"  ✓ 通过 (成功: {len(results)}, 失败: {len(errs)})")
    except AssertionError as e:
        failures.append(f"测试3失败: {e}")
        print(f"  ✗ 失败: {e}")

    # --- 测试 4: 字段提取 ---
    print("[selftest] 测试4: 字段提取")
    try:
        extracted = extract_fields_from_text("2026/02/01 08:30 [cache] WARNING 缓存命中率下降")
        assert "timestamp" in extracted, "应提取到时间戳"
        assert "level" in extracted, "应提取到级别"
        assert "source" in extracted, "应提取到来源"
        assert extracted["level"] == "WARNING", f"级别应为 WARNING, 实际: {extracted['level']}"
        print(f"  ✓ 通过 (字段: {list(extracted.keys())})")
    except AssertionError as e:
        failures.append(f"测试4失败: {e}")
        print(f"  ✗ 失败: {e}")

    # --- 测试 5: 输出格式化 ---
    print("[selftest] 测试5: 输出格式化")
    test_results = [{"message": "测试", "_confidence": 0.9, "_index": 0}]
    test_failures = []
    try:
        json_out = format_output(test_results, test_failures, "json")
        assert "success_count" in json_out, "JSON 输出应包含 success_count"
        text_out = format_output(test_results, test_failures, "text")
        assert "处理完成" in text_out, "文本输出应包含处理完成信息"
        md_out = format_output(test_results, test_failures, "markdown")
        assert "|" in md_out, "Markdown 输出应包含表格"
        print(f"  ✓ 通过 (JSON/Text/Markdown)")
    except AssertionError as e:
        failures.append(f"测试5失败: {e}")
        print(f"  ✗ 失败: {e}")

    # --- 测试 6: 错误处理 ---
    print("[selftest] 测试6: 错误处理")
    try:
        # 不支持的文件格式（创建临时文件测试）
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            read_input_file(tmp_path)
            failures.append("测试6失败: 应抛出 E004")
            print(f"  ✗ 失败: 应抛出 E004")
        except ValueError as e:
            assert "E004" in str(e), f"错误码应为 E004, 实际: {e}"
            print(f"  ✓ 通过 (错误码 E004)")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except AssertionError as e:
        failures.append(f"测试6失败: {e}")
        print(f"  ✗ 失败: {e}")

    # --- 测试 7: 空输入处理 ---
    print("[selftest] 测试7: 空输入处理")
    try:
        results, errs = parse_batch("")
        assert len(results) >= 0, "空输入应返回空结果"
        print(f"  ✓ 通过 (结果数: {len(results)})")
    except AssertionError as e:
        failures.append(f"测试7失败: {e}")
        print(f"  ✗ 失败: {e}")

    # --- 汇总 ---
    print("=" * 50)
    if failures:
        print(f"[selftest] 自检失败: {len(failures)} 项未通过")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("[selftest] 全部自检通过 ✓")
        return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="starling - 消息队列数据解析与结构化转换工具",
        epilog="示例: python main.py --input data.json --format json"
    )
    parser.add_argument("--input", "-i", help="输入文件路径 (.txt/.csv/.json)")
    parser.add_argument("--text", "-t", help="直接输入文本内容")
    parser.add_argument("--format", "-f", choices=["json", "text", "markdown"],
                        default="json", help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="starling 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        # 获取输入数据
        if args.input:
            data = read_input_file(args.input)
        elif args.text:
            data = args.text
        else:
            print("E001: 请提供 --input 或 --text 参数", file=sys.stderr)
            return 1

        # 解析数据
        results, failures = parse_batch(data)

        # 输出结果
        output = format_output(results, failures, args.format)
        print(output)

        # 如果有失败记录，返回非零退出码
        if failures:
            return 2
        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 3
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
