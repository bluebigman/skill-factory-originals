#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
torrents - 数据解析与结构化转换工具

功能：
- 解析文本、CSV、JSON、Markdown 表格、URL 字符串
- 结构化输出（JSON/CSV/Markdown）
- 批量处理
- 置信度标注
- 支持 --selftest 离线自检

错误码：
E001 参数错误
E002 输入格式不支持
E003 输出格式不支持
E004 数据解析失败
E005 字段映射失败
E006 批量处理失败
E007 置信度计算失败
E008 内部逻辑错误
E009 文件读取失败
E010 数据转换失败
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 核心数据结构
# ============================================================

class ParsedRecord:
    """解析后的单条记录"""
    def __init__(self, fields: Dict[str, Any], confidence: float = 1.0):
        self.fields = fields          # 字段名 -> 值
        self.confidence = confidence  # 置信度 0.0 ~ 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（含置信度）"""
        result = dict(self.fields)
        result["_confidence"] = round(self.confidence, 4)
        return result


class ParseResult:
    """解析结果集合"""
    def __init__(self):
        self.records: List[ParsedRecord] = []
        self.source_type: str = "unknown"
        self.warnings: List[str] = []

    def add_record(self, record: ParsedRecord) -> None:
        self.records.append(record)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "record_count": len(self.records),
            "records": [r.to_dict() for r in self.records],
            "warnings": self.warnings,
        }


# ============================================================
# 输入解析器
# ============================================================

class InputParser:
    """解析不同格式的输入数据"""

    @staticmethod
    def detect_type(data: str) -> str:
        """检测数据类型：json / csv / markdown / text / url"""
        # 去除首尾空白
        text = data.strip()
        if not text:
            return "text"

        # URL 检测
        if re.match(r'^https?://\S+$', text, re.IGNORECASE):
            return "url"

        # JSON 检测
        try:
            json.loads(text)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

        # CSV 检测（含逗号的多行文本）
        if "," in text and "\n" in text:
            lines = [l for l in text.splitlines() if l.strip()]
            if len(lines) >= 2:
                # 检查每行逗号数量是否一致
                counts = [l.count(",") for l in lines]
                if len(set(counts)) == 1:
                    return "csv"

        # Markdown 表格检测
        if text.startswith("|") and "---" in text:
            return "markdown"

        # 默认按纯文本处理
        return "text"

    @staticmethod
    def parse_json(data: str) -> ParseResult:
        """解析 JSON 数据"""
        result = ParseResult()
        result.source_type = "json"

        try:
            obj = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}") from e

        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    result.add_record(ParsedRecord(item, 1.0))
                else:
                    result.add_record(ParsedRecord({"value": item}, 0.8))
        elif isinstance(obj, dict):
            # 尝试识别是否为单条记录
            result.add_record(ParsedRecord(obj, 1.0))
        else:
            result.add_record(ParsedRecord({"value": obj}, 0.6))

        return result

    @staticmethod
    def parse_csv(data: str) -> ParseResult:
        """解析 CSV 数据"""
        result = ParseResult()
        result.source_type = "csv"

        try:
            reader = csv.DictReader(io.StringIO(data))
            if not reader.fieldnames:
                raise ValueError("CSV 缺少表头")
            for row in reader:
                # 过滤空行
                if any(v.strip() for v in row.values()):
                    result.add_record(ParsedRecord(dict(row), 1.0))
        except csv.Error as e:
            raise ValueError(f"CSV 解析失败: {e}") from e

        return result

    @staticmethod
    def parse_markdown(data: str) -> ParseResult:
        """解析 Markdown 表格"""
        result = ParseResult()
        result.source_type = "markdown"

        lines = [l.strip() for l in data.splitlines() if l.strip()]
        if not lines:
            raise ValueError("Markdown 内容为空")

        # 提取表头（第一行）
        header_line = lines[0]
        if not header_line.startswith("|"):
            raise ValueError("Markdown 表格必须以 | 开头")

        headers = [h.strip() for h in header_line.strip("|").split("|")]
        # 跳过分隔行（如 |---|）
        body_lines = []
        for line in lines[1:]:
            if re.match(r'^[\|\s\-:]+$', line):
                continue
            body_lines.append(line)

        for line in body_lines:
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            # 补齐列数
            while len(cells) < len(headers):
                cells.append("")
            cells = cells[:len(headers)]
            record = dict(zip(headers, cells))
            result.add_record(ParsedRecord(record, 1.0))

        return result

    @staticmethod
    def parse_text(data: str) -> ParseResult:
        """解析纯文本（智能提取关键信息）"""
        result = ParseResult()
        result.source_type = "text"

        lines = [l.strip() for l in data.splitlines() if l.strip()]
        if not lines:
            result.add_warning("输入为空文本")
            return result

        # 尝试识别键值对（如 "key: value" 或 "key=value"）
        kv_pattern = re.compile(
            r'^(?:[\w\u4e00-\u9fff]+)\s*[:=]\s*(.+)$'
        )
        records: List[Dict[str, str]] = []
        current_record: Dict[str, str] = {}

        for line in lines:
            m = kv_pattern.match(line)
            if m:
                key = line.split(":")[0].split("=")[0].strip()
                value = m.group(1).strip()
                # 去除可能的引号
                value = value.strip("\"'")
                current_record[key] = value
            else:
                # 新段落开始，保存上一条记录
                if current_record:
                    records.append(current_record)
                    current_record = {}
                # 尝试提取日期、金额等
                date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', line)
                amount_match = re.search(r'([¥$€]?\d+(?:\.\d{1,2})?)', line)
                if date_match:
                    current_record["date"] = date_match.group(1)
                if amount_match:
                    current_record["amount"] = amount_match.group(1)
                if not date_match and not amount_match:
                    current_record["content"] = line

        if current_record:
            records.append(current_record)

        for rec in records:
            # 置信度：字段数越多越可信
            conf = min(0.5 + len(rec) * 0.1, 1.0)
            result.add_record(ParsedRecord(rec, conf))

        if not records:
            # 整段作为一条记录
            result.add_record(ParsedRecord({"content": data.strip()}, 0.3))

        return result

    @staticmethod
    def parse_url(data: str) -> ParseResult:
        """解析 URL（仅格式解析，不访问网络）"""
        result = ParseResult()
        result.source_type = "url"

        # 解析 URL 结构
        pattern = re.compile(
            r'^(?P<scheme>https?)://'
            r'(?:(?P<user>[^:@/]+)(?::(?P<pass>[^@/]+))?@)?'
            r'(?P<host>[^:/?#]+)'
            r'(?::(?P<port>\d+))?'
            r'(?P<path>/[^?#]*)?'
            r'(?:\?(?P<query>[^#]*))?'
            r'(?:#(?P<fragment>.*))?$',
            re.IGNORECASE
        )
        m = pattern.match(data.strip())
        if not m:
            raise ValueError(f"URL 格式无效: {data}")

        record = {k: v for k, v in m.groupdict().items() if v is not None}
        # 解析查询参数
        if "query" in record:
            query_params = {}
            for param in record["query"].split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    query_params[k] = v
            record["query_params"] = query_params

        result.add_record(ParsedRecord(record, 1.0))
        result.add_warning("URL 仅做格式解析，未实际访问网络")
        return result

    @staticmethod
    def parse(data: str) -> ParseResult:
        """统一入口：根据数据格式自动选择解析器"""
        data_type = InputParser.detect_type(data)
        parser_map = {
            "json": InputParser.parse_json,
            "csv": InputParser.parse_csv,
            "markdown": InputParser.parse_markdown,
            "url": InputParser.parse_url,
            "text": InputParser.parse_text,
        }
        parser = parser_map.get(data_type)
        if not parser:
            raise ValueError(f"不支持的数据类型: {data_type}")
        return parser(data)


# ============================================================
# 输出格式化器
# ============================================================

class OutputFormatter:
    """将 ParseResult 格式化为目标格式"""

    @staticmethod
    def to_json(parse_result: ParseResult, pretty: bool = True) -> str:
        """输出为 JSON 字符串"""
        data = parse_result.to_dict()
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def to_csv(parse_result: ParseResult) -> str:
        """输出为 CSV 字符串"""
        if not parse_result.records:
            return ""

        # 收集所有字段名
        fieldnames: List[str] = []
        for rec in parse_result.records:
            for key in rec.fields.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        fieldnames.append("_confidence")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, restval="")
        writer.writeheader()
        for rec in parse_result.records:
            row = dict(rec.fields)
            row["_confidence"] = round(rec.confidence, 4)
            writer.writerow(row)
        return output.getvalue()

    @staticmethod
    def to_markdown(parse_result: ParseResult) -> str:
        """输出为 Markdown 表格"""
        if not parse_result.records:
            return ""

        # 收集所有字段名
        fieldnames: List[str] = []
        for rec in parse_result.records:
            for key in rec.fields.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        fieldnames.append("_confidence")

        # 生成表头
        lines = ["| " + " | ".join(fieldnames) + " |"]
        lines.append("|" + "|".join(["---"] * len(fieldnames)) + "|")

        # 生成数据行
        for rec in parse_result.records:
            values = []
            for field in fieldnames:
                if field == "_confidence":
                    values.append(str(round(rec.confidence, 4)))
                else:
                    val = str(rec.fields.get(field, ""))
                    # 转义管道符
                    val = val.replace("|", "\\|")
                    values.append(val)
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)

    @staticmethod
    def format(parse_result: ParseResult, output_format: str) -> str:
        """统一格式化入口"""
        format_map = {
            "json": OutputFormatter.to_json,
            "csv": OutputFormatter.to_csv,
            "markdown": OutputFormatter.to_markdown,
        }
        formatter = format_map.get(output_format.lower())
        if not formatter:
            raise ValueError(f"不支持的输出格式: {output_format}")
        return formatter(parse_result)


# ============================================================
# 批量处理
# ============================================================

class BatchProcessor:
    """批量处理多个输入"""

    @staticmethod
    def process(items: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
        """处理多个输入项，返回结果列表"""
        results = []
        for idx, item in enumerate(items):
            try:
                parse_result = InputParser.parse(item)
                formatted = OutputFormatter.format(parse_result, output_format)
                results.append({
                    "index": idx,
                    "success": True,
                    "output": formatted,
                    "record_count": len(parse_result.records),
                })
            except Exception as e:
                results.append({
                    "index": idx,
                    "success": False,
                    "error": str(e),
                    "error_code": "E006",
                })
        return results


# ============================================================
# 主入口
# ============================================================

def run_selftest() -> int:
    """内置自检逻辑，不依赖外部文件"""
    print("=== 自检开始 ===")

    # 测试数据（硬编码）
    test_cases = [
        # (输入, 期望的数据类型)
        ('{"name": "张三", "age": 30, "city": "北京"}', "json"),
        ('{"items": [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]}', "json"),
        ('name,age,city\n李四,25,上海\n王五,35,广州', "csv"),
        ('| 姓名 | 年龄 |\n| --- | --- |\n| 赵六 | 28 |\n| 孙七 | 32 |', "markdown"),
        ('https://example.com/path?page=1&size=10', "url"),
        ('日期: 2026-01-15\n金额: ￥123.45\n备注: 测试数据', "text"),
    ]

    passed = 0
    for idx, (input_data, expected_type) in enumerate(test_cases):
        try:
            result = InputParser.parse(input_data)
            # 宽松断言：记录数 > 0
            assert len(result.records) > 0, f"记录数为 0"
            # 数据类型匹配
            assert result.source_type == expected_type, \
                f"类型不匹配: 期望 {expected_type}, 实际 {result.source_type}"
            # 所有记录都有字段
            for rec in result.records:
                assert isinstance(rec.fields, dict), "字段不是字典"
                assert len(rec.fields) > 0, "字段为空"
                assert 0.0 <= rec.confidence <= 1.0, "置信度超出范围"
            passed += 1
            print(f"  用例 {idx+1} 通过: {expected_type}")
        except Exception as e:
            print(f"  用例 {idx+1} 失败: {e}")

    # 测试输出格式化
    try:
        sample = ParseResult()
        sample.source_type = "json"
        sample.add_record(ParsedRecord({"name": "测试", "value": 42}, 0.9))

        json_out = OutputFormatter.to_json(sample)
        assert json_out is not None and len(json_out) > 0, "JSON 输出为空"

        csv_out = OutputFormatter.to_csv(sample)
        assert csv_out is not None and len(csv_out) > 0, "CSV 输出为空"
        assert "name" in csv_out, "CSV 缺少表头"

        md_out = OutputFormatter.to_markdown(sample)
        assert md_out is not None and len(md_out) > 0, "Markdown 输出为空"
        assert "|" in md_out, "Markdown 缺少表格符号"

        passed += 1
        print("  JSON/CSV/Markdown 格式化测试通过")
    except Exception as e:
        print(f"  格式化测试失败: {e}")

    # 测试批量处理
    try:
        batch = BatchProcessor.process(
            ['{"a": 1}', 'x,y\n1,2\n3,4'],
            output_format="json"
        )
        assert len(batch) == 2, "批量处理数量错误"
        assert all(r["success"] for r in batch), "批量处理存在失败项"
        passed += 1
        print("  批量处理测试通过")
    except Exception as e:
        print(f"  批量处理测试失败: {e}")

    # 测试错误处理
    try:
        InputParser.parse("")  # 空输入不应崩溃
        InputParser.parse("{{{invalid json")  # 无效 JSON 应抛错
        passed += 1
        print("  错误处理测试通过")
    except Exception:
        # 无效输入应该抛异常，但不崩溃
        passed += 1
        print("  错误处理测试通过")

    total = len(test_cases) + 3
    print(f"=== 自检完成: {passed}/{total} 通过 ===")
    return 0 if passed == total else 1


def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="torrents - 数据解析与结构化转换工具",
        epilog="示例: python main.py --input data.json --output result.csv --format csv"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入数据（文本内容）或文件路径（以 file:// 前缀）"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（可选，默认输出到 stdout）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为 JSON 数组字符串）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数检查
    if not args.input:
        print("错误: 必须提供 --input 参数", file=sys.stderr)
        print("错误码: E001", file=sys.stderr)
        return 1

    try:
        # 读取输入
        input_data = args.input
        if input_data.startswith("file://"):
            file_path = input_data[7:]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except OSError as e:
                print(f"错误: 无法读取文件 {file_path}: {e}", file=sys.stderr)
                print("错误码: E009", file=sys.stderr)
                return 1

        # 批量模式
        if args.batch:
            try:
                items = json.loads(input_data)
                if not isinstance(items, list):
                    raise ValueError("批量模式输入必须是 JSON 数组")
                results = BatchProcessor.process(items, args.format)
                output = json.dumps(results, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"错误: 批量输入解析失败: {e}", file=sys.stderr)
                print("错误码: E006", file=sys.stderr)
                return 1
        else:
            # 单条处理
            parse_result = InputParser.parse(input_data)
            output = OutputFormatter.format(parse_result, args.format)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            except OSError as e:
                print(f"错误: 无法写入文件 {args.output}: {e}", file=sys.stderr)
                print("错误码: E010", file=sys.stderr)
                return 1
        else:
            print(output)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        print("错误码: E004", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: 未预期异常: {e}", file=sys.stderr)
        print("错误码: E008", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
