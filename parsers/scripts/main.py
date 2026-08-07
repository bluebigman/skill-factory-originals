#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 数据解析 / 信息抽取 / 格式转换 技能实现

依据功能规格独立实现（clean-room），不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能概览:
  - 从文本 / CSV / JSON / 简单键值对 中抽取结构化字段
  - 实体识别（邮箱、URL、日期、数字）
  - 批量处理同构数据行
  - 每个输出字段标注置信度（高/中/低）
  - 输出格式支持 JSON / Markdown 表格 / 自定义分隔符文本
  - 内置 --selftest 离线自检（硬编码样例，不依赖外部环境）

错误码约定:
  E001 参数错误
  E002 输入数据为空或格式非法
  E003 无法识别的输入类型
  E004 输出格式不支持
  E005 批量处理时数据行不一致
  E006 实体抽取内部错误
  E007 字段映射失败
  E008 置信度计算异常
  E009 输出序列化失败
  E010 未知运行时错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 基础数据结构
# ---------------------------------------------------------------------------

class ParseResult:
    """单条解析结果，包含字段与置信度。"""

    def __init__(self, fields: Dict[str, Any], confidence: Dict[str, str]):
        self.fields = fields          # 字段名 -> 值
        self.confidence = confidence  # 字段名 -> '高'|'中'|'低'

    def to_dict(self) -> Dict[str, Any]:
        """转为普通字典，附带置信度信息。"""
        return {
            "fields": self.fields,
            "confidence": self.confidence,
        }


class BatchResult:
    """批量解析结果。"""

    def __init__(self, items: List[ParseResult], summary: Dict[str, Any]):
        self.items = items
        self.summary = summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# 实体识别与字段抽取
# ---------------------------------------------------------------------------

# 邮箱正则（宽松匹配）
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# URL 正则（宽松匹配 http/https）
_URL_RE = re.compile(r"https?://[\w./?=&%#@:-]+", re.IGNORECASE)

# 日期正则（支持 2024-01-15、2024/01/15、2024年1月15日 等）
_DATE_RE = re.compile(
    r"(\d{4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?"
)

# 数字正则（整数或小数，可带千分位逗号）
_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def extract_emails(text: str) -> List[str]:
    """从文本中提取所有邮箱地址。"""
    if not text:
        return []
    found = _EMAIL_RE.findall(text)
    # 去重并保持顺序
    seen = set()
    result = []
    for email in found:
        if email not in seen:
            seen.add(email)
            result.append(email)
    return result


def extract_urls(text: str) -> List[str]:
    """从文本中提取所有 URL。"""
    if not text:
        return []
    found = _URL_RE.findall(text)
    seen = set()
    result = []
    for url in found:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def extract_dates(text: str) -> List[str]:
    """从文本中提取日期，统一格式为 YYYY-MM-DD。"""
    if not text:
        return []
    result = []
    seen = set()
    for match in _DATE_RE.finditer(text):
        year, month, day = match.group(1), match.group(2), match.group(3)
        try:
            # 验证日期合法性
            normalized = datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            # 非法日期（如 2024-13-40）跳过
            continue
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def extract_numbers(text: str) -> List[float]:
    """从文本中提取所有数字（整数或小数），转为 float。"""
    if not text:
        return []
    result = []
    for match in _NUMBER_RE.finditer(text):
        raw = match.group(0).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        result.append(value)
    return result


def detect_entity_type(value: str) -> str:
    """根据值内容推断实体类型。"""
    if not value:
        return "未知"
    if _EMAIL_RE.fullmatch(value.strip()):
        return "邮箱"
    if _URL_RE.fullmatch(value.strip()):
        return "URL"
    if _DATE_RE.fullmatch(value.strip().replace("年", "-").replace("月", "-").replace("日", "")):
        return "日期"
    try:
        float(value.replace(",", ""))
        return "数字"
    except ValueError:
        return "文本"


def compute_confidence(field_name: str, value: Any, source_type: str) -> str:
    """
    计算字段置信度。
    规则:
      - 值非空且类型明确 -> 高
      - 值非空但类型模糊（如长文本） -> 中
      - 值为空或无法识别 -> 低
    """
    if value is None or value == "":
        return "低"

    if isinstance(value, (int, float)):
        return "高"

    if isinstance(value, list):
        if len(value) > 0:
            return "高"
        return "低"

    if isinstance(value, str):
        if len(value) > 200:
            return "中"
        entity_type = detect_entity_type(value)
        if entity_type != "文本":
            return "高"
        return "中"

    return "中"


# ---------------------------------------------------------------------------
# 输入解析
# ---------------------------------------------------------------------------

def parse_key_value_text(text: str, delimiter: str = ":") -> Dict[str, str]:
    """解析简单的 'key: value' 格式文本。"""
    result: Dict[str, str] = {}
    if not text:
        return result
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if delimiter in line:
            key, _, value = line.partition(delimiter)
            result[key.strip()] = value.strip()
    return result


def parse_csv_text(text: str, has_header: bool = True) -> List[Dict[str, str]]:
    """解析 CSV 文本（简单实现，支持逗号分隔，忽略引号内逗号）。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    def split_csv_line(line: str) -> List[str]:
        """简单 CSV 行切分，处理双引号包裹的字段。"""
        result = []
        current = []
        in_quote = False
        for char in line:
            if char == '"':
                in_quote = not in_quote
            elif char == "," and not in_quote:
                result.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        result.append("".join(current).strip())
        return result

    if has_header:
        header = split_csv_line(lines[0])
        data_lines = lines[1:]
    else:
        # 无表头时自动生成列名 col_1, col_2, ...
        first_line = split_csv_line(lines[0])
        header = [f"col_{i + 1}" for i in range(len(first_line))]
        data_lines = lines

    records = []
    for line in data_lines:
        values = split_csv_line(line)
        if len(values) != len(header):
            continue  # 跳过不一致的行（宽松处理）
        record = {}
        for col_name, value in zip(header, values):
            record[col_name] = value
        records.append(record)

    return records


def parse_json_text(text: str) -> Any:
    """解析 JSON 文本。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: {exc}") from exc


def parse_input(data: str, input_type: str = "auto") -> Any:
    """
    统一入口解析输入数据。
    input_type: auto / text / csv / json / keyvalue
    """
    if not data or not data.strip():
        raise ValueError("E002: 输入数据为空")

    data = data.strip()

    if input_type == "auto":
        # 自动检测类型
        if data.startswith("{") and data.endswith("}"):
            return parse_json_text(data)
        if "," in data.splitlines()[0]:
            return parse_csv_text(data)
        if ":" in data.splitlines()[0]:
            return parse_key_value_text(data)
        return data

    if input_type == "text":
        return data

    if input_type == "csv":
        return parse_csv_text(data)

    if input_type == "json":
        return parse_json_text(data)

    if input_type == "keyvalue":
        return parse_key_value_text(data)

    raise ValueError("E003: 无法识别的输入类型")


# ---------------------------------------------------------------------------
# 结构化输出
# ---------------------------------------------------------------------------

def to_json(result: Any) -> str:
    """序列化为 JSON 字符串。"""
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except TypeError as exc:
        raise ValueError(f"E009: JSON 序列化失败: {exc}") from exc


def to_markdown_table(result: Any) -> str:
    """将解析结果转为 Markdown 表格。"""
    # 支持 ParseResult / BatchResult / 简单字典
    if isinstance(result, BatchResult):
        if not result.items:
            return "_无数据_"
        # 收集所有字段名
        all_keys = []
        for item in result.items:
            for key in item.fields.keys():
                if key not in all_keys:
                    all_keys.append(key)
        if not all_keys:
            return "_无字段_"

        lines = []
        lines.append("| " + " | ".join(all_keys) + " |")
        lines.append("|" + "---|" * len(all_keys))
        for item in result.items:
            row = []
            for key in all_keys:
                value = item.fields.get(key, "")
                conf = item.confidence.get(key, "低")
                row.append(f"{value} (置信度:{conf})")
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    if isinstance(result, ParseResult):
        lines = []
        lines.append("| 字段 | 值 | 置信度 |")
        lines.append("|---|---|---|")
        for key in result.fields:
            value = result.fields[key]
            conf = result.confidence.get(key, "低")
            lines.append(f"| {key} | {value} | {conf} |")
        return "\n".join(lines)

    if isinstance(result, dict):
        lines = []
        lines.append("| 字段 | 值 |")
        lines.append("|---|---|")
        for key, value in result.items():
            lines.append(f"| {key} | {value} |")
        return "\n".join(lines)

    return str(result)


def to_delimited_text(result: Any, delimiter: str = "\t") -> str:
    """将解析结果转为自定义分隔符文本。"""
    if isinstance(result, BatchResult):
        if not result.items:
            return ""
        all_keys = []
        for item in result.items:
            for key in item.fields.keys():
                if key not in all_keys:
                    all_keys.append(key)
        lines = []
        # 表头
        lines.append(delimiter.join(all_keys))
        for item in result.items:
            row = [str(item.fields.get(key, "")) for key in all_keys]
            lines.append(delimiter.join(row))
        return "\n".join(lines)

    if isinstance(result, ParseResult):
        lines = []
        for key in result.fields:
            lines.append(f"{key}{delimiter}{result.fields[key]}")
        return "\n".join(lines)

    if isinstance(result, dict):
        lines = []
        for key, value in result.items():
            lines.append(f"{key}{delimiter}{value}")
        return "\n".join(lines)

    return str(result)


def format_output(result: Any, output_format: str = "json") -> str:
    """按指定格式输出结果。"""
    if output_format == "json":
        return to_json(result)
    if output_format == "markdown":
        return to_markdown_table(result)
    if output_format == "csv":
        return to_delimited_text(result, delimiter=",")
    if output_format == "tsv":
        return to_delimited_text(result, delimiter="\t")
    raise ValueError("E004: 不支持的输出格式")


# ---------------------------------------------------------------------------
# 核心处理流程
# ---------------------------------------------------------------------------

def process_single_text(text: str) -> ParseResult:
    """处理单段文本，抽取实体与统计信息。"""
    fields: Dict[str, Any] = {}
    confidence: Dict[str, str] = {}

    # 提取实体
    emails = extract_emails(text)
    urls = extract_urls(text)
    dates = extract_dates(text)
    numbers = extract_numbers(text)

    fields["原文长度"] = len(text)
    fields["邮箱"] = emails
    fields["URL"] = urls
    fields["日期"] = dates
    fields["数字列表"] = numbers

    # 统计词频（简单统计 Top 5 高频词）
    words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    word_count: Dict[str, int] = {}
    for word in words:
        if len(word) < 2:
            continue
        word_count[word] = word_count.get(word, 0) + 1
    top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:5]
    fields["高频词"] = [word for word, _ in top_words]

    # 计算置信度
    for key in fields:
        confidence[key] = compute_confidence(key, fields[key], "text")

    return ParseResult(fields, confidence)


def process_keyvalue(data: Dict[str, str]) -> ParseResult:
    """处理键值对数据。"""
    fields: Dict[str, Any] = {}
    confidence: Dict[str, str] = {}

    for key, value in data.items():
        fields[key] = value
        confidence[key] = compute_confidence(key, value, "keyvalue")

    return ParseResult(fields, confidence)


def process_csv(records: List[Dict[str, str]]) -> BatchResult:
    """处理 CSV 记录列表。"""
    if not records:
        raise ValueError("E002: CSV 数据为空")

    items = []
    for record in records:
        fields: Dict[str, Any] = {}
        confidence: Dict[str, str] = {}
        for key, value in record.items():
            fields[key] = value
            confidence[key] = compute_confidence(key, value, "csv")
        items.append(ParseResult(fields, confidence))

    summary = {
        "总行数": len(items),
        "字段数": len(records[0]) if records else 0,
        "处理时间": datetime.now().isoformat(timespec="seconds"),
    }
    return BatchResult(items, summary)


def process_json(data: Any) -> ParseResult:
    """处理 JSON 数据（扁平化一层）。"""
    if not isinstance(data, dict):
        # 非字典 JSON 转为文本处理
        return process_single_text(json.dumps(data, ensure_ascii=False))

    fields: Dict[str, Any] = {}
    confidence: Dict[str, str] = {}

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            # 复杂类型转为 JSON 字符串
            value_str = json.dumps(value, ensure_ascii=False)
            fields[key] = value_str
            confidence[key] = "中"
        else:
            fields[key] = value
            confidence[key] = compute_confidence(key, value, "json")

    return ParseResult(fields, confidence)


def run_parse(data: str, input_type: str = "auto") -> Any:
    """主处理函数，返回 ParseResult 或 BatchResult。"""
    try:
        parsed = parse_input(data, input_type)
    except ValueError as exc:
        # 透传错误码
        raise

    if isinstance(parsed, str):
        return process_single_text(parsed)
    if isinstance(parsed, dict):
        return process_keyvalue(parsed)
    if isinstance(parsed, list):
        # 列表可能是 CSV 记录或 JSON 数组
        if parsed and all(isinstance(item, dict) for item in parsed):
            return process_csv(parsed)
        # 简单列表转为文本处理
        return process_single_text(str(parsed))
    # 其他情况按文本处理
    return process_single_text(str(parsed))


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    使用宽松阈值断言，不依赖精确值。
    """
    print("===== parsers 技能自检开始 =====")

    # 测试1: 邮箱与URL抽取
    sample_text = "联系 support@example.com 或访问 https://example.com/path?q=1"
    emails = extract_emails(sample_text)
    urls = extract_urls(sample_text)
    assert len(emails) >= 1, "E006: 邮箱抽取失败"
    assert len(urls) >= 1, "E006: URL抽取失败"
    assert "example.com" in emails[0], "E006: 邮箱内容不正确"
    print(f"[通过] 实体抽取: 邮箱={emails}, URL={urls}")

    # 测试2: 日期抽取
    date_text = "会议定于2024年3月15日召开，截止2024/12/31。"
    dates = extract_dates(date_text)
    assert len(dates) >= 2, "E006: 日期抽取数量不足"
    assert all("-" in d for d in dates), "E006: 日期格式未规范化"
    print(f"[通过] 日期抽取: {dates}")

    # 测试3: 数字抽取
    num_text = "价格 1,200元 和 45.5 以及 78"
    numbers = extract_numbers(num_text)
    assert len(numbers) >= 3, "E006: 数字抽取数量不足"
    assert any(n > 1000 for n in numbers), "E006: 千分位数字解析失败"
    print(f"[通过] 数字抽取: {numbers}")

    # 测试4: 键值对解析
    kv_text = "姓名: 张三\n年龄: 30\n城市: 北京"
    kv_result = parse_key_value_text(kv_text)
    assert "姓名" in kv_result, "E007: 键值对解析失败"
    assert kv_result["姓名"] == "张三", "E007: 键值对值错误"
    print(f"[通过] 键值对解析: {kv_result}")

    # 测试5: CSV解析
    csv_text = "name,age,city\n李四,25,上海\n王五,35,广州"
    csv_records = parse_csv_text(csv_text)
    assert len(csv_records) >= 2, "E007: CSV解析行数不足"
    assert csv_records[0]["name"] == "李四", "E007: CSV解析内容错误"
    print(f"[通过] CSV解析: 共{len(csv_records)}行")

    # 测试6: JSON解析
    json_text = '{"product": "笔记本电脑", "price": 5999, "in_stock": true}'
    json_data = parse_json_text(json_text)
    assert isinstance(json_data, dict), "E007: JSON解析类型错误"
    assert "product" in json_data, "E007: JSON解析字段缺失"
    print(f"[通过] JSON解析: {json_data}")

    # 测试7: 完整处理流程（文本）
    result = run_parse("联系人: alice@test.com, 电话: 13800138000, 日期: 2024-06-01")
    assert isinstance(result, ParseResult), "E008: 文本处理结果类型错误"
    assert "邮箱" in result.fields, "E008: 文本处理字段缺失"
    assert len(result.fields["邮箱"]) >= 1, "E008: 文本处理邮箱抽取失败"
    print(f"[通过] 文本处理: 字段数={len(result.fields)}")

    # 测试8: 完整处理流程（CSV批量）
    csv_data = "id,name,score\n1,张三,85\n2,李四,92\n3,王五,78"
    batch_result = run_parse(csv_data, input_type="csv")
    assert isinstance(batch_result, BatchResult), "E008: CSV批量处理类型错误"
    assert len(batch_result.items) >= 3, "E008: CSV批量处理行数不足"
    assert batch_result.summary["总行数"] >= 3, "E008: CSV汇总信息错误"
    print(f"[通过] CSV批量处理: {batch_result.summary}")

    # 测试9: 输出格式
    json_output = format_output(result, "json")
    assert json_output.startswith("{"), "E009: JSON输出格式错误"
    md_output = format_output(result, "markdown")
    assert "|" in md_output, "E009: Markdown输出格式错误"
    print("[通过] 输出格式: JSON/Markdown")

    # 测试10: 置信度计算
    conf_high = compute_confidence("email", "test@example.com", "text")
    conf_low = compute_confidence("empty", "", "text")
    assert conf_high == "高", "E008: 置信度计算错误（应为高）"
    assert conf_low == "低", "E008: 置信度计算错误（应为低）"
    print("[通过] 置信度计算")

    print("===== 自检全部通过 =====")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="数据解析 / 信息抽取 / 格式转换 技能工具",
        epilog="示例: python main.py --input '姓名: 张三' --type keyvalue --format json",
    )
    parser.add_argument("--input", "-i", help="输入数据（文本/CSV/JSON 等）")
    parser.add_argument("--type", "-t", default="auto",
                        choices=["auto", "text", "csv", "json", "keyvalue"],
                        help="输入数据类型")
    parser.add_argument("--format", "-f", default="json",
                        choices=["json", "markdown", "csv", "tsv"],
                        help="输出格式")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检并退出")

    args = parser.parse_args()

    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"自检异常: {exc}", file=sys.stderr)
            return 1

    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest", file=sys.stderr)
        print("错误码: E001", file=sys.stderr)
        return 1

    try:
        result = run_parse(args.input, args.type)
        output = format_output(result, args.format)
        print(output)
        return 0
    except ValueError as exc:
        # 提取错误码（如 E002）
        error_msg = str(exc)
        code = "E010"  # 默认未知错误
        if error_msg.startswith("E0"):
            code = error_msg.split(":", 1)[0]
        print(f"处理失败: {error_msg}", file=sys.stderr)
        print(f"错误码: {code}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未知错误: {exc}", file=sys.stderr)
        print("错误码: E010", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
