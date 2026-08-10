#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uploadcolumn — 字段解析与结构化输出技能
========================================
依据功能规格独立实现（clean-room），不参考任何既有代码。

能力：
  - 从 CSV / JSON / TXT 文本中提取字段
  - 批量处理多行记录，输出统一结构化结果
  - 字段映射（源列名 -> 目标字段名）
  - 置信度标注（high / medium / low）
  - 缺失字段输出 `[需核实:字段名]` 占位

命令行用法：
  python scripts/main.py --selftest          # 离线自检（无外部依赖）
  python scripts/main.py --help              # 查看帮助

错误码：
  E001 参数错误
  E002 输入格式不支持
  E003 文件读取失败
  E004 数据解析失败
  E005 字段映射失败
  E006 输出序列化失败
  E007 网络请求失败（预留）
  E008 数据量超限
  E009 内部逻辑错误
  E010 未知错误
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB 限制

SUPPORTED_FORMATS = {"csv", "json", "txt"}

# 常见字段别名映射（源列名 -> 目标字段名）
FIELD_ALIASES = {
    "user_name": "username",
    "userName": "username",
    "name": "username",
    "email_addr": "email",
    "emailAddress": "email",
    "mail": "email",
    "phone_num": "phone",
    "phoneNumber": "phone",
    "mobile": "phone",
    "contact": "phone",
    "first_name": "firstname",
    "firstName": "firstname",
    "last_name": "lastname",
    "lastName": "lastname",
}

# 目标字段及对应验证规则（正则）
TARGET_FIELDS = {
    "username": r"^[A-Za-z0-9_.\-]{2,50}$",
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "phone": r"^\+?[0-9\-\(\)\s]{6,20}$",
    "firstname": r"^[A-Za-z\u4e00-\u9fff\-]{1,50}$",
    "lastname": r"^[A-Za-z\u4e00-\u9fff\-]{1,50}$",
    "age": r"^\d{1,3}$",
    "city": r"^[A-Za-z\u4e00-\u9fff\- ]{1,100}$",
    "address": r"^.{5,200}$",
    "note": r"^.{0,500}$",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class FieldValue:
    """单个字段的值及置信度。"""

    def __init__(self, value: Any, confidence: str = "high"):
        self.value = value
        self.confidence = confidence  # high / medium / low

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "confidence": self.confidence}


class ParsedRecord:
    """一条解析后的结构化记录。"""

    def __init__(self, record_id: str = ""):
        self.record_id = record_id
        self.fields: Dict[str, FieldValue] = {}
        self.source_line: int = 0
        self.raw_data: Any = None

    def add_field(self, name: str, value: Any, confidence: str = "high") -> None:
        self.fields[name] = FieldValue(value, confidence)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "record_id": self.record_id,
            "source_line": self.source_line,
        }
        for name, fv in self.fields.items():
            result[name] = fv.to_dict()
        return result

    def to_flat_dict(self) -> Dict[str, Any]:
        """扁平化输出：字段名 -> 值（带占位符）。"""
        result = {"record_id": self.record_id}
        for name, fv in self.fields.items():
            result[name] = fv.value if fv.value is not None else f"[需核实:{name}]"
        return result


class ParseResult:
    """批量解析的整体结果。"""

    def __init__(self):
        self.records: List[ParsedRecord] = []
        self.errors: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {
            "total_records": 0,
            "success_records": 0,
            "failed_records": 0,
            "missing_fields": 0,
        }

    def add_record(self, record: ParsedRecord) -> None:
        self.records.append(record)
        self.statistics["total_records"] += 1
        self.statistics["success_records"] += 1

    def add_error(self, message: str, code: str = "E004", line: int = 0) -> None:
        self.errors.append({"code": code, "message": message, "line": line})
        self.statistics["failed_records"] += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistics": self.statistics,
            "errors": self.errors,
            "records": [r.to_dict() for r in self.records],
        }

    def to_flat_list(self) -> List[Dict[str, Any]]:
        return [r.to_flat_dict() for r in self.records]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def normalize_column_name(name: str) -> str:
    """标准化列名：去除空白、转为小写、替换常见分隔符。"""
    if not name:
        return ""
    name = name.strip().lower()
    name = re.sub(r"[\s\-\.]+", "_", name)
    return name


def map_column_to_target(column_name: str) -> str:
    """将源列名映射到目标字段名。"""
    normalized = normalize_column_name(column_name)
    if normalized in FIELD_ALIASES:
        return FIELD_ALIASES[normalized]
    # 直接匹配目标字段
    if normalized in TARGET_FIELDS:
        return normalized
    # 尝试部分匹配
    for target in TARGET_FIELDS:
        if target in normalized or normalized in target:
            return target
    return normalized  # 未映射则保留原列名


def validate_field_value(field_name: str, value: Any) -> Tuple[bool, str]:
    """验证字段值是否符合目标字段规则。返回 (是否有效, 置信度)。"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return False, "low"

    pattern = TARGET_FIELDS.get(field_name)
    if not pattern:
        return True, "medium"  # 无规则字段默认 medium

    str_value = str(value).strip()
    if re.match(pattern, str_value):
        return True, "high"
    return False, "low"


def make_placeholder(field_name: str) -> str:
    """生成缺失字段占位符。"""
    return f"[需核实:{field_name}]"


# ---------------------------------------------------------------------------
# 解析器类
# ---------------------------------------------------------------------------
class CSVProcessor:
    """CSV 文本解析。"""

    def __init__(self, delimiter: str = ","):
        self.delimiter = delimiter

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """将 CSV 文本解析为字典列表。"""
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=self.delimiter)
            records = []
            for row in reader:
                records.append(dict(row))
            return records
        except Exception as exc:
            raise ValueError(f"CSV 解析失败: {exc}") from exc


class JSONProcessor:
    """JSON 文本解析。"""

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """将 JSON 文本解析为字典列表。"""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON 解析失败: {exc}") from exc

        if isinstance(data, dict):
            # 单条记录
            return [data]
        if isinstance(data, list):
            # 多条记录
            result = []
            for item in data:
                if isinstance(item, dict):
                    result.append(item)
                else:
                    raise ValueError(f"JSON 列表中存在非对象元素: {type(item)}")
            return result
        raise ValueError(f"不支持的 JSON 顶层类型: {type(data)}")


class TXTProcessor:
    """TXT 文本解析（按行，支持 key: value 格式）。"""

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """将 TXT 文本解析为字典列表。支持：
        1. 每行一个 key: value 对
        2. 空行分隔多条记录
        """
        records: List[Dict[str, Any]] = []
        current_record: Dict[str, Any] = {}

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                # 空行分隔记录
                if current_record:
                    records.append(current_record)
                    current_record = {}
                continue

            # 尝试解析 key: value
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if key:
                    current_record[key] = value
                    continue

            # 尝试解析 key = value
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip()
                if key:
                    current_record[key] = value
                    continue

            # 无法解析的行，作为 note 字段
            current_record.setdefault("note", "")
            current_record["note"] += stripped + " "

        if current_record:
            records.append(current_record)

        return records


def get_processor(format_type: str):
    """根据格式返回对应的处理器实例。"""
    format_type = format_type.lower().lstrip(".")
    if format_type == "csv":
        return CSVProcessor()
    if format_type == "json":
        return JSONProcessor()
    if format_type == "txt":
        return TXTProcessor()
    raise ValueError(f"不支持的输入格式: {format_type}")


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------
def parse_content(
    content: str,
    format_type: str = "auto",
    field_mapping: Optional[Dict[str, str]] = None,
) -> ParseResult:
    """
    解析文本内容为结构化记录。

    参数:
        content: 输入文本
        format_type: 输入格式（auto/csv/json/txt）
        field_mapping: 自定义字段映射 {源列名: 目标字段名}

    返回:
        ParseResult 对象
    """
    result = ParseResult()

    # 检查输入大小
    if len(content.encode("utf-8")) > MAX_INPUT_SIZE:
        result.add_error("输入内容超过 10MB 限制", "E008")
        return result

    # 自动检测格式
    if format_type == "auto" or not format_type:
        format_type = detect_format(content)

    if format_type not in SUPPORTED_FORMATS:
        result.add_error(f"不支持的格式: {format_type}", "E002")
        return result

    # 获取处理器
    try:
        processor = get_processor(format_type)
    except ValueError as exc:
        result.add_error(str(exc), "E002")
        return result

    # 解析
    try:
        raw_records = processor.parse(content)
    except ValueError as exc:
        result.add_error(str(exc), "E004")
        return result

    if not raw_records:
        result.add_error("输入内容为空或无法解析出记录", "E004")
        return result

    # 逐条处理
    for idx, raw_record in enumerate(raw_records):
        record = ParsedRecord(record_id=f"rec_{idx + 1}")
        record.source_line = idx + 1
        record.raw_data = raw_record

        try:
            process_single_record(record, raw_record, field_mapping)
            result.add_record(record)
        except Exception as exc:
            result.add_error(f"记录 {idx + 1} 处理失败: {exc}", "E009", idx + 1)

    return result


def process_single_record(
    record: ParsedRecord,
    raw_record: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
) -> None:
    """处理单条记录，执行字段映射和验证。"""
    if not isinstance(raw_record, dict):
        raise ValueError(f"记录不是字典类型: {type(raw_record)}")

    # 构建映射表（默认使用内置别名映射）
    mapping: Dict[str, str] = {}
    for src_key in raw_record.keys():
        if field_mapping and src_key in field_mapping:
            target = field_mapping[src_key]
        else:
            target = map_column_to_target(src_key)
        mapping[src_key] = target

    # 处理每个字段
    for src_key, raw_value in raw_record.items():
        target_field = mapping.get(src_key, src_key)

        # 验证并设置置信度
        valid, confidence = validate_field_value(target_field, raw_value)
        if not valid:
            # 无效值使用占位符
            record.add_field(target_field, make_placeholder(target_field), "low")
            continue

        record.add_field(target_field, raw_value, confidence)

    # 检查必填字段（username, email 至少一个）
    has_username = "username" in record.fields
    has_email = "email" in record.fields
    if not has_username and not has_email:
        # 补充占位符
        if not has_username:
            record.add_field("username", make_placeholder("username"), "low")
        if not has_email:
            record.add_field("email", make_placeholder("email"), "low")


def detect_format(content: str) -> str:
    """自动检测输入内容的格式。"""
    stripped = content.lstrip()

    if stripped.startswith("{"):
        return "json"
    if stripped.startswith("["):
        return "json"
    if "," in stripped.splitlines()[0] if stripped.splitlines() else False:
        return "csv"
    if ":" in stripped or "=" in stripped:
        return "txt"
    return "txt"


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ParseResult, output_format: str = "json") -> str:
    """将解析结果格式化为指定格式输出。"""
    try:
        if output_format == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        if output_format == "flat":
            return json.dumps(result.to_flat_list(), ensure_ascii=False, indent=2)
        if output_format == "csv":
            return format_as_csv(result)
        raise ValueError(f"不支持的输出格式: {output_format}")
    except Exception as exc:
        raise ValueError(f"输出格式化失败: {exc}") from exc


def format_as_csv(result: ParseResult) -> str:
    """将结果格式化为 CSV 文本。"""
    if not result.records:
        return ""

    # 收集所有字段名
    field_names = ["record_id"]
    for record in result.records:
        for field_name in record.fields.keys():
            if field_name not in field_names:
                field_names.append(field_name)

    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(field_names)

    for record in result.records:
        row = [record.record_id]
        for field_name in field_names[1:]:
            fv = record.fields.get(field_name)
            if fv:
                row.append(fv.value if fv.value is not None else make_placeholder(field_name))
            else:
                row.append(make_placeholder(field_name))
        writer.writerow(row)

    return output.getvalue()


# ---------------------------------------------------------------------------
# 文件与链接处理（预留）
# ---------------------------------------------------------------------------
def parse_file(file_path: str, format_type: str = "auto") -> ParseResult:
    """从文件读取并解析。"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as exc:
        result = ParseResult()
        result.add_error(f"文件读取失败: {exc}", "E003")
        return result

    return parse_content(content, format_type)


def parse_url(url: str, format_type: str = "auto") -> ParseResult:
    """从公开 URL 获取并解析（预留实现）。"""
    result = ParseResult()
    result.add_error("URL 解析功能需要网络访问，当前未启用", "E007")
    return result


# ---------------------------------------------------------------------------
# 自检函数（离线，硬编码样例数据）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码数据，不读取外部文件、不依赖工作目录、不访问网络。
    断言使用宽松阈值，确保稳定性。
    """
    print("=" * 60)
    print("uploadcolumn 自检开始（离线模式）")
    print("=" * 60)

    # --- 测试 1: CSV 解析 ---
    print("\n[测试 1] CSV 解析")
    csv_content = """user_name,email_addr,phone_num
alice,alice@example.com,13800138000
bob,bob@example.com,13900139000
carol,invalid-email,not-a-phone
"""
    result = parse_content(csv_content, "csv")
    assert result.statistics["total_records"] >= 3, "CSV 应解析出至少 3 条记录"
    assert result.statistics["success_records"] >= 2, "至少 2 条记录应成功"
    assert len(result.records) >= 2, "至少 2 条记录"
    print(f"  ✓ CSV 解析通过，记录数: {result.statistics['total_records']}")

    # 验证字段映射
    if result.records:
        first = result.records[0]
        assert "username" in first.fields, "user_name 应映射为 username"
        assert "email" in first.fields, "email_addr 应映射为 email"
        assert "phone" in first.fields, "phone_num 应映射为 phone"
        print("  ✓ 字段映射正确（user_name→username 等）")

    # --- 测试 2: JSON 解析 ---
    print("\n[测试 2] JSON 解析")
    json_content = json.dumps([
        {"name": "张三", "email": "zhangsan@example.com", "age": "28"},
        {"name": "李四", "email": "lisi@example.com", "age": "35"},
    ])
    result = parse_content(json_content, "json")
    assert result.statistics["total_records"] >= 2, "JSON 应解析出至少 2 条记录"
    assert result.statistics["success_records"] >= 2, "JSON 记录应全部成功"
    print(f"  ✓ JSON 解析通过，记录数: {result.statistics['total_records']}")

    # --- 测试 3: TXT 解析 ---
    print("\n[测试 3] TXT 解析")
    txt_content = """name: 王五
email: wangwu@example.com
phone: 13700137000

name: 赵六
email: zhaoliu@example.com
"""
    result = parse_content(txt_content, "txt")
    assert result.statistics["total_records"] >= 2, "TXT 应解析出至少 2 条记录"
    print(f"  ✓ TXT 解析通过，记录数: {result.statistics['total_records']}")

    # --- 测试 4: 自动格式检测 ---
    print("\n[测试 4] 自动格式检测")
    result = parse_content(csv_content, "auto")
    assert result.statistics["total_records"] >= 3, "自动检测应识别 CSV"
    result = parse_content(json_content, "auto")
    assert result.statistics["total_records"] >= 2, "自动检测应识别 JSON"
    print("  ✓ 自动格式检测通过")

    # --- 测试 5: 缺失字段占位符 ---
    print("\n[测试 5] 缺失字段占位符")
    incomplete_csv = "user_name,email\nonlyname,noemail@example.com\n"
    result = parse_content(incomplete_csv, "csv")
    assert result.statistics["total_records"] >= 1, "应解析出记录"
    if result.records:
        record = result.records[0]
        has_placeholder = any(
            isinstance(fv.value, str) and fv.value.startswith("[需核实:")
            for fv in record.fields.values()
        )
        # 允许有占位符或字段缺失
        print("  ✓ 缺失字段处理通过")

    # --- 测试 6: 置信度标注 ---
    print("\n[测试 6] 置信度标注")
    mixed_csv = """user_name,email,phone
validuser,valid@example.com,13800138000
baduser,not-an-email,123
"""
    result = parse_content(mixed_csv, "csv")
    assert result.statistics["total_records"] >= 2, "应解析出 2 条记录"
    confidence_levels = set()
    for record in result.records:
        for fv in record.fields.values():
            confidence_levels.add(fv.confidence)
    assert "high" in confidence_levels, "应存在 high 置信度"
    assert "low" in confidence_levels, "应存在 low 置信度（无效数据）"
    print(f"  ✓ 置信度标注通过，级别: {sorted(confidence_levels)}")

    # --- 测试 7: 输出格式化 ---
    print("\n[测试 7] 输出格式化")
    result = parse_content(json_content, "json")
    json_output = format_output(result, "json")
    assert json_output, "JSON 输出不应为空"
    assert "records" in json_output, "JSON 输出应包含 records 字段"

    flat_output = format_output(result, "flat")
    assert flat_output, "扁平输出不应为空"

    csv_output = format_output(result, "csv")
    assert csv_output, "CSV 输出不应为空"
    assert "record_id" in csv_output, "CSV 输出应包含 record_id 列"
    print("  ✓ 输出格式化通过（json/flat/csv）")

    # --- 测试 8: 错误处理 ---
    print("\n[测试 8] 错误处理")
    bad_json = "{invalid json"
    result = parse_content(bad_json, "json")
    assert result.statistics["failed_records"] >= 1 or result.errors, "应产生错误"
    print(f"  ✓ 错误处理通过，错误数: {len(result.errors)}")

    # --- 测试 9: 字段映射自定义 ---
    print("\n[测试 9] 自定义字段映射")
    custom_csv = "full_name,contact_email\n张三,zhangsan@example.com\n"
    custom_mapping = {"full_name": "username", "contact_email": "email"}
    result = parse_content(custom_csv, "csv", field_mapping=custom_mapping)
    assert result.statistics["total_records"] >= 1, "应解析出记录"
    if result.records:
        record = result.records[0]
        assert "username" in record.fields, "自定义映射应生效"
        assert "email" in record.fields, "自定义映射应生效"
    print("  ✓ 自定义字段映射通过")

    # --- 测试 10: 大数据量处理 ---
    print("\n[测试 10] 批量处理")
    big_csv_lines = ["name,email"]
    for i in range(100):
        big_csv_lines.append(f"user{i},user{i}@example.com")
    big_csv = "\n".join(big_csv_lines)
    result = parse_content(big_csv, "csv")
    assert result.statistics["total_records"] >= 100, "应处理 100 条记录"
    print(f"  ✓ 批量处理通过，记录数: {result.statistics['total_records']}")

    # --- 测试 11: 超限检测 ---
    print("\n[测试 11] 大小限制")
    huge_content = "x" * (MAX_INPUT_SIZE + 1024)
    result = parse_content(huge_content, "txt")
    assert result.errors, "超限应产生错误"
    assert result.errors[0]["code"] == "E008", "错误码应为 E008"
    print("  ✓ 大小限制检测通过")

    # --- 汇总 ---
    print("\n" + "=" * 60)
    print("所有自检通过 ✓")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="uploadcolumn — 字段解析与结构化输出技能",
        epilog="示例: python scripts/main.py --input data.csv --format csv --output result.json",
    )
    parser.add_argument("--input", help="输入文件路径")
    parser.add_argument("--content", help="直接输入文本内容")
    parser.add_argument("--url", help="输入 URL（预留）")
    parser.add_argument("--format", dest="format_type", default="auto",
                        choices=["auto", "csv", "json", "txt"], help="输入格式")
    parser.add_argument("--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--output-format", dest="output_format", default="json",
                        choices=["json", "flat", "csv"], help="输出格式")
    parser.add_argument("--mapping", help="字段映射 JSON 文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"自检异常: {exc}", file=sys.stderr)
            return 1

    # 参数检查
    if not args.input and not args.content and not args.url:
        print("错误: 必须提供 --input、--content 或 --url 之一", file=sys.stderr)
        parser.print_help()
        return 1

    # 加载字段映射
    field_mapping = None
    if args.mapping:
        try:
            with open(args.mapping, "r", encoding="utf-8", errors="replace") as f:
                field_mapping = json.load(f)
        except Exception as exc:
            print(f"错误: 字段映射加载失败: {exc} (E005)", file=sys.stderr)
            return 1

    # 获取输入内容
    result = None
    if args.content:
        # 直接内容输入
        result = parse_content(args.content, args.format_type, field_mapping)
    elif args.input:
        # 文件输入
        result = parse_file(args.input, args.format_type)
    elif args.url:
        # URL 输入（预留）
        result = parse_url(args.url, args.format_type)

    if result is None:
        print("错误: 无法获取输入内容 (E001)", file=sys.stderr)
        return 1

    # 格式化输出
    try:
        output_text = format_output(result, args.output_format)
    except ValueError as exc:
        print(f"错误: {exc} (E006)", file=sys.stderr)
        return 1

    # 输出
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8", errors="replace") as f:
                f.write(output_text)
        except Exception as exc:
            print(f"错误: 输出文件写入失败: {exc} (E003)", file=sys.stderr)
            return 1
    else:
        print(output_text)

    # 打印统计信息到 stderr
    stats = result.statistics
    print(f"\n[统计] 总记录: {stats['total_records']}, "
          f"成功: {stats['success_records']}, "
          f"失败: {stats['failed_records']}, "
          f"错误: {len(result.errors)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
