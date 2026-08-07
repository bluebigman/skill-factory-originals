#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
microsis — 旧档解析与字段还原（干净室独立实现）
=================================================
功能：将老旧数据/文件/URL 内容解析为结构化结果，保留关键信息并标注置信度。

本脚本为 clean-room 实现，仅依据功能规格独立编写，不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

用法：
    python scripts/main.py --selftest   # 离线自检核心逻辑
    python scripts/main.py --parse "文本内容"  # 解析文本
    python scripts/main.py --file path   # 解析文件内容
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件错误：文件不存在或无法读取",
    "E003": "URL 错误：URL 格式无效",
    "E004": "解析错误：输入内容为空或无法解析",
    "E005": "编码错误：文件编码不支持",
    "E006": "JSON 错误：输出序列化失败",
    "E007": "内部错误：未知异常",
    "E008": "自检错误：自检断言失败",
    "E009": "类型错误：输入类型不支持",
    "E010": "路径错误：输出路径无效",
}


class MicrosisError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心解析逻辑
# ============================================================

def _normalize_text(text: str) -> str:
    """规范化文本：去除多余空白，保留基本结构。"""
    if not text:
        return ""
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去除首尾空白
    text = text.strip()
    return text


def _detect_date_fields(text: str) -> List[Dict[str, Any]]:
    """
    检测文本中的日期字段（宽松模式）。
    支持格式：YYYY-MM-DD, YYYY/MM/DD, YYYY年MM月DD日, YYYY.MM.DD 等。
    返回字段列表，每个字段含 value、confidence、type。
    """
    fields = []
    # 宽松日期模式（年份 1900-2100，月份/日期 1-31 或 01-31）
    patterns = [
        r"(?<!\d)(19\d{2}|20\d{2})[-/.年](0?[1-9]|1[0-2])[-/.月](0?[1-9]|[12]\d|3[01])日?",
        r"(?<!\d)(19\d{2}|20\d{2})年(0?[1-9]|1[0-2])月(0?[1-9]|[12]\d|3[01])日",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            raw = match.group(0)
            # 尝试解析为日期对象
            try:
                # 统一分隔符
                normalized = raw.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-")
                parts = normalized.split("-")
                if len(parts) >= 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    # 基本合理性检查
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        fields.append({
                            "value": f"{year:04d}-{month:02d}-{day:02d}",
                            "confidence": 0.8,  # 宽松置信度
                            "type": "date",
                            "raw": raw,
                        })
            except (ValueError, IndexError):
                continue
    return fields


def _detect_phone_fields(text: str) -> List[Dict[str, Any]]:
    """
    检测电话号码字段（宽松模式）。
    支持：+86 138-1234-5678, 010-12345678, 13812345678 等。
    """
    fields = []
    # 宽松电话模式：可选 +86 前缀，支持数字、空格、连字符、括号
    # 匹配模式：可能包含国家代码、区号、分隔符
    patterns = [
        # 带国家代码 +86 或 86 的格式
        r"(?<!\d)(?:\+?86[- ]?)?(?:\(0\d{2,3}\)[- ]?)?(?:0\d{2,3}[- ]?)?\d{7,8}(?:[- ]?\d{3,4})?(?!\d)",
        # 国内手机号格式（11位，1开头）
        r"(?<!\d)1[3-9]\d{9}(?!\d)",
        # 带分隔符的手机号格式
        r"(?<!\d)1[3-9][- ]\d{4}[- ]\d{4}(?!\d)",
        # 座机号格式（区号-号码）
        r"(?<!\d)0\d{2,3}[- ]\d{7,8}(?!\d)",
        # 带括号的座机号
        r"(?<!\d)\(0\d{2,3}\)[- ]?\d{7,8}(?!\d)",
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            raw = match.group(0).strip()
            # 提取纯数字
            digits = re.sub(r"\D", "", raw)
            # 基本长度检查（7-15位）
            if 7 <= len(digits) <= 15:
                # 避免重复检测（如果相同数字已存在则跳过）
                if not any(f["value"] == digits for f in fields):
                    fields.append({
                        "value": digits,
                        "confidence": 0.7,  # 宽松置信度
                        "type": "phone",
                        "raw": raw,
                    })
    return fields


def _detect_email_fields(text: str) -> List[Dict[str, Any]]:
    """检测电子邮件字段（宽松模式）。"""
    fields = []
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    for match in re.finditer(pattern, text):
        raw = match.group(0)
        # 基本格式检查
        if "@" in raw and "." in raw.split("@")[-1]:
            fields.append({
                "value": raw,
                "confidence": 0.9,  # 邮箱格式较严格
                "type": "email",
                "raw": raw,
            })
    return fields


def _detect_url_fields(text: str) -> List[Dict[str, Any]]:
    """检测 URL 字段（宽松模式）。"""
    fields = []
    pattern = r"https?://[^\s<>\"']+"
    for match in re.finditer(pattern, text):
        raw = match.group(0)
        # 尝试解析 URL
        try:
            parsed = urllib.parse.urlparse(raw)
            if parsed.scheme and parsed.netloc:
                fields.append({
                    "value": raw,
                    "confidence": 0.85,
                    "type": "url",
                    "raw": raw,
                })
        except ValueError:
            continue
    return fields


def _detect_id_fields(text: str) -> List[Dict[str, Any]]:
    """
    检测常见 ID 字段（宽松模式）。
    支持：身份证号（18位）、订单号、编号等。
    """
    fields = []
    # 身份证号（宽松）：18位，最后一位可能是X
    id_pattern = r"(?<!\d)\d{17}[\dXx](?!\d)"
    for match in re.finditer(id_pattern, text):
        raw = match.group(0)
        fields.append({
            "value": raw.upper(),
            "confidence": 0.75,
            "type": "id_card",
            "raw": raw,
        })
    # 通用编号（字母+数字组合，长度>=6）
    code_pattern = r"(?<![A-Za-z0-9])[A-Za-z]{2,}\d{4,}(?![A-Za-z0-9])"
    for match in re.finditer(code_pattern, text):
        raw = match.group(0)
        fields.append({
            "value": raw,
            "confidence": 0.6,
            "type": "code",
            "raw": raw,
        })
    return fields


def _detect_name_fields(text: str) -> List[Dict[str, Any]]:
    """
    检测可能的姓名字段（宽松模式）。
    基于常见称呼和姓名模式，仅做启发式检测。
    """
    fields = []
    # 常见称呼后跟2-4个中文字符
    pattern = r"(?:姓名|名字|称呼)[:：\s]*([\u4e00-\u9fa5]{2,4})"
    for match in re.finditer(pattern, text):
        raw = match.group(1)
        fields.append({
            "value": raw,
            "confidence": 0.5,  # 启发式，置信度较低
            "type": "name",
            "raw": raw,
        })
    # 独立的中文姓名模式（2-4字，前后有分隔符）
    pattern2 = r"(?<=[\s,，。；;])([\u4e00-\u9fa5]{2,4})(?=[\s,，。；;])"
    for match in re.finditer(pattern2, text):
        raw = match.group(1)
        # 排除常见非姓名词汇
        if raw not in ("数据", "信息", "内容", "文件", "记录", "字段", "系统", "用户"):
            fields.append({
                "value": raw,
                "confidence": 0.3,  # 启发式，置信度低
                "type": "name",
                "raw": raw,
            })
    return fields


def parse_text(text: str) -> Dict[str, Any]:
    """
    解析文本，提取结构化字段并标注置信度。

    参数：
        text: 待解析的原始文本

    返回：
        结构化结果字典，包含：
        - text: 规范化后的文本
        - fields: 检测到的字段列表
        - summary: 统计信息
        - timestamp: 解析时间
    """
    if not text or not text.strip():
        raise MicrosisError("E004")

    normalized = _normalize_text(text)

    # 收集所有字段
    all_fields: List[Dict[str, Any]] = []
    all_fields.extend(_detect_date_fields(normalized))
    all_fields.extend(_detect_phone_fields(normalized))
    all_fields.extend(_detect_email_fields(normalized))
    all_fields.extend(_detect_url_fields(normalized))
    all_fields.extend(_detect_id_fields(normalized))
    all_fields.extend(_detect_name_fields(normalized))

    # 按类型分组统计
    type_stats: Dict[str, int] = {}
    for field in all_fields:
        ftype = field["type"]
        type_stats[ftype] = type_stats.get(ftype, 0) + 1

    # 计算整体置信度（所有字段置信度的平均值）
    overall_confidence = 0.0
    if all_fields:
        overall_confidence = sum(f["confidence"] for f in all_fields) / len(all_fields)

    return {
        "text": normalized,
        "fields": all_fields,
        "summary": {
            "total_fields": len(all_fields),
            "type_stats": type_stats,
            "overall_confidence": round(overall_confidence, 4),
        },
        "timestamp": datetime.now().isoformat(),
    }


def parse_file(filepath: str) -> Dict[str, Any]:
    """解析文件内容。"""
    if not os.path.isfile(filepath):
        raise MicrosisError("E002", f"文件不存在: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # 尝试其他常见编码
        try:
            with open(filepath, "r", encoding="gbk") as f:
                content = f.read()
        except Exception:
            raise MicrosisError("E005")
    except Exception:
        raise MicrosisError("E002")

    result = parse_text(content)
    result["source"] = {"type": "file", "path": filepath}
    return result


def parse_url(url: str) -> Dict[str, Any]:
    """
    解析 URL（仅做格式检测和 URL 字段提取，不实际访问网络）。
    注意：本函数不访问网络，仅解析 URL 字符串本身。
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise MicrosisError("E003")
    except ValueError:
        raise MicrosisError("E003")

    # 将 URL 本身作为文本解析
    result = parse_text(url)
    result["source"] = {"type": "url", "url": url}
    return result


# ============================================================
# 输出与序列化
# ============================================================

def format_output(result: Dict[str, Any], format_type: str = "json") -> str:
    """格式化输出结果。"""
    if format_type == "json":
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            raise MicrosisError("E006")
    elif format_type == "text":
        # 简洁文本格式
        lines = []
        lines.append("=== 解析结果 ===")
        if "source" in result:
            src = result["source"]
            lines.append(f"来源: {src.get('type', 'unknown')}")
            if "path" in src:
                lines.append(f"路径: {src['path']}")
            if "url" in src:
                lines.append(f"URL: {src['url']}")
        lines.append(f"文本长度: {len(result.get('text', ''))}")
        lines.append(f"字段总数: {result.get('summary', {}).get('total_fields', 0)}")
        lines.append(f"整体置信度: {result.get('summary', {}).get('overall_confidence', 0)}")
        lines.append("")
        if result.get("fields"):
            lines.append("检测到的字段:")
            for field in result["fields"]:
                lines.append(
                    f"  [{field['type']}] {field['value']} "
                    f"(置信度: {field['confidence']})"
                )
        else:
            lines.append("未检测到明确字段。")
        return "\n".join(lines)
    else:
        raise MicrosisError("E001", f"不支持的输出格式: {format_type}")


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。使用硬编码样例数据，不读取外部文件。
    断言采用宽松阈值，确保稳健。

    返回 True 表示自检通过。
    """
    print("=== microsis 自检开始 ===")

    # 测试样例1：综合文本
    sample1 = """
    客户信息登记表
    姓名：张三
    联系电话：138-1234-5678
    电子邮箱：zhangsan@example.com
    注册日期：2023-05-15
    身份证号：110101199003071234
    备注：该客户于2023年6月1日首次购买。
    """

    try:
        result1 = parse_text(sample1)
        # 断言：应检测到至少4个字段
        assert result1["summary"]["total_fields"] >= 4, \
            f"样例1字段数不足: {result1['summary']['total_fields']}"
        # 断言：应包含姓名
        name_found = any(f["type"] == "name" for f in result1["fields"])
        assert name_found, "样例1未检测到姓名字段"
        # 断言：应包含电话
        phone_found = any(f["type"] == "phone" for f in result1["fields"])
        assert phone_found, "样例1未检测到电话字段"
        # 断言：应包含邮箱
        email_found = any(f["type"] == "email" for f in result1["fields"])
        assert email_found, "样例1未检测到邮箱字段"
        # 断言：应包含日期
        date_found = any(f["type"] == "date" for f in result1["fields"])
        assert date_found, "样例1未检测到日期字段"
        print("  [PASS] 样例1（综合文本）解析通过")

    except AssertionError as e:
        print(f"  [FAIL] 样例1断言失败: {e}")
        raise MicrosisError("E008", str(e))

    # 测试样例2：纯文本无字段
    sample2 = "这是一段没有结构化字段的普通文本内容，用于测试解析器的稳健性。"

    try:
        result2 = parse_text(sample2)
        # 断言：不应检测到字段（或字段数很少）
        assert result2["summary"]["total_fields"] <= 1, \
            f"样例2字段数异常: {result2['summary']['total_fields']}"
        # 断言：文本应被保留
        assert len(result2["text"]) > 0, "样例2文本为空"
        print("  [PASS] 样例2（无字段文本）解析通过")

    except AssertionError as e:
        print(f"  [FAIL] 样例2断言失败: {e}")
        raise MicrosisError("E008", str(e))

    # 测试样例3：URL 解析
    sample3 = "https://example.com/data/archive/2024/old_record.html"

    try:
        result3 = parse_url(sample3)
        # 断言：应检测到 URL 字段
        url_found = any(f["type"] == "url" for f in result3["fields"])
        assert url_found, "样例3未检测到 URL 字段"
        # 断言：来源信息正确
        assert result3["source"]["type"] == "url", "样例3来源类型错误"
        print("  [PASS] 样例3（URL解析）通过")

    except AssertionError as e:
        print(f"  [FAIL] 样例3断言失败: {e}")
        raise MicrosisError("E008", str(e))

    # 测试样例4：日期检测（多种格式）
    sample4 = "日期1: 2024/12/31, 日期2: 2023年6月15日, 日期3: 2022.01.01"

    try:
        result4 = parse_text(sample4)
        # 断言：应检测到至少3个日期字段
        date_count = sum(1 for f in result4["fields"] if f["type"] == "date")
        assert date_count >= 3, f"样例4日期字段不足: {date_count}"
        print("  [PASS] 样例4（日期多格式）通过")

    except AssertionError as e:
        print(f"  [FAIL] 样例4断言失败: {e}")
        raise MicrosisError("E008", str(e))

    # 测试样例5：空输入错误处理
    try:
        parse_text("")
        print("  [FAIL] 样例5（空输入）应抛出异常")
        raise MicrosisError("E008", "空输入未抛出异常")
    except MicrosisError as e:
        assert e.code == "E004", f"空输入错误码错误: {e.code}"
        print("  [PASS] 样例5（空输入错误处理）通过")

    # 测试样例6：输出格式化
    try:
        sample6 = "测试格式化输出 电话: 010-12345678"
        result6 = parse_text(sample6)
        json_out = format_output(result6, "json")
        # 断言：JSON 输出应可解析
        parsed_json = json.loads(json_out)
        assert "fields" in parsed_json, "JSON 输出缺少 fields 字段"
        assert "summary" in parsed_json, "JSON 输出缺少 summary 字段"
        print("  [PASS] 样例6（JSON格式化）通过")

    except AssertionError as e:
        print(f"  [FAIL] 样例6断言失败: {e}")
        raise MicrosisError("E008", str(e))

    # 测试样例7：宽泛置信度检查
    try:
        sample7 = "订单号: ABC2024001, 金额: 100元, 日期: 2024-01-15"
        result7 = parse_text(sample7)
        # 断言：整体置信度应在合理区间（0-1）
        conf = result7["summary"]["overall_confidence"]
        assert 0 <= conf <= 1, f"置信度超出范围: {conf}"
        # 断言：至少有一个字段
        assert result7["summary"]["total_fields"] > 0, "样例7无字段"
        print("  [PASS] 样例7（置信度检查）通过")

    except AssertionError as e:
        print(f"  [FAIL] 样例7断言失败: {e}")
        raise MicrosisError("E008", str(e))

    print("=== 自检全部通过 ===")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="microsis - 旧档解析与字段还原",
        epilog="示例: python scripts/main.py --parse '姓名: 李四, 电话: 13912345678'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置数据，不依赖外部文件）"
    )
    parser.add_argument(
        "--parse",
        metavar="TEXT",
        help="解析文本内容"
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="解析文件内容"
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        help="解析 URL（仅格式检测，不访问网络）"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="输出到文件（可选）"
    )

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            run_selftest()
            return 0

        # 解析模式
        result = None
        if args.parse:
            result = parse_text(args.parse)
        elif args.file:
            result = parse_file(args.file)
        elif args.url:
            result = parse_url(args.url)
        else:
            parser.print_help()
            return 0

        # 格式化输出
        output = format_output(result, args.format)

        # 输出到文件或标准输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"结果已写入: {args.output}")
            except Exception:
                raise MicrosisError("E010")
        else:
            print(output)

        return 0

    except MicrosisError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E007']}] 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
