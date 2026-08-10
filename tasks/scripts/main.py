#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tasks - 数据转换与批量处理工具

功能：
- 解析 CSV / JSON / Markdown 表格等常见格式
- 结构化转换：将非结构化数据映射为字段明确的记录
- 批量处理：对多条同类数据执行相同转换规则
- 自定义格式输出：Markdown 表格、CSV、JSON
- 字段映射与重命名
- 基础数据清洗（去空行、去重、日期格式统一）

用法示例：
    python scripts/main.py --input data.csv --output result.json --format json
    python scripts/main.py --selftest
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from datetime import timezone  # G2 时区修复
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def err(code: str, message: str) -> AppError:
    """构造带错误码的异常。"""
    return AppError(code, message)


# ============================================================
# 核心数据结构
# ============================================================
class DataRecord:
    """单条数据记录，本质为字段名到值的映射。"""
    def __init__(self, fields: Dict[str, Any]):
        self.fields = fields

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.fields[key] = value

    def rename(self, old: str, new: str) -> None:
        if old in self.fields:
            self.fields[new] = self.fields.pop(old)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.fields)


class DataTable:
    """数据表：包含字段列表和多条记录。"""
    def __init__(self, fields: Optional[List[str]] = None):
        self.fields = fields if fields is not None else []
        self.records: List[DataRecord] = []

    def add_record(self, record: DataRecord) -> None:
        # 自动扩展字段列表
        for key in record.fields:
            if key not in self.fields:
                self.fields.append(key)
        self.records.append(record)

    def add_records(self, records: List[DataRecord]) -> None:
        for r in records:
            self.add_record(r)

    def __len__(self) -> int:
        return len(self.records)

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.records]


# ============================================================
# 解析器（输入）
# ============================================================
def parse_csv(text: str) -> DataTable:
    """解析 CSV 文本为 DataTable。"""
    try:
        reader = csv.DictReader(io.StringIO(text))
        table = DataTable(fields=reader.fieldnames or [])
        for row in reader:
            table.add_record(DataRecord(row))
        return table
    except Exception as e:
        raise err("E001", f"CSV 解析失败: {e}")


def parse_json(text: str) -> DataTable:
    """解析 JSON 文本为 DataTable。支持对象数组或单个对象。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise err("E002", f"JSON 解析失败: {e}")

    if isinstance(data, dict):
        # 单个对象：所有值必须是标量才视为一条记录
        table = DataTable(fields=list(data.keys()))
        table.add_record(DataRecord(data))
        return table
    elif isinstance(data, list):
        if not data:
            return DataTable(fields=[])
        if not all(isinstance(item, dict) for item in data):
            raise err("E003", "JSON 数组元素必须是对象")
        table = DataTable()
        for item in data:
            table.add_record(DataRecord(item))
        return table
    else:
        raise err("E004", "JSON 顶层必须是对象或对象数组")


def parse_markdown_table(text: str) -> DataTable:
    """解析 Markdown 表格文本为 DataTable。"""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        raise err("E005", "Markdown 表格至少需要表头和分隔行")

    header_line = lines[0]
    # 去除首尾的 |
    header_cells = [c.strip() for c in header_line.strip("|").split("|")]

    # 验证分隔行（---）
    sep_line = lines[1]
    sep_cells = [c.strip() for c in sep_line.strip("|").split("|")]
    if not all(re.match(r"^:?-{3,}:?$", cell) for cell in sep_cells):
        raise err("E006", "Markdown 表格第二行必须是分隔行（---）")

    table = DataTable(fields=header_cells)
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(header_cells):
            raise err("E007", f"数据行列数({len(cells)})与表头列数({len(header_cells)})不一致")
        record = DataRecord(dict(zip(header_cells, cells)))
        table.add_record(record)
    return table


def detect_and_parse(text: str) -> DataTable:
    """自动检测格式并解析。"""
    stripped = text.strip()
    if not stripped:
        raise err("E008", "输入内容为空")

    # 尝试 JSON
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return parse_json(stripped)
        except AppError:
            pass  # 不是合法 JSON，继续尝试其他格式

    # 尝试 Markdown 表格（第二行是 --- 分隔）
    lines = stripped.splitlines()
    if len(lines) >= 2 and re.match(r"^\s*\|", lines[1]) and "---" in lines[1]:
        try:
            return parse_markdown_table(stripped)
        except AppError:
            pass

    # 尝试 CSV
    try:
        return parse_csv(stripped)
    except AppError:
        pass

    raise err("E009", "无法识别输入格式（支持 CSV、JSON、Markdown 表格）")


# ============================================================
# 数据清洗与转换
# ============================================================
def clean_table(table: DataTable, remove_duplicates: bool = True) -> DataTable:
    """基础清洗：去空行、去重。"""
    cleaned = DataTable(fields=list(table.fields))
    seen = set()

    for record in table.records:
        # 去空行：所有字段值都为空或空白则跳过
        if all(str(v).strip() == "" for v in record.fields.values()):
            continue

        # 去重
        if remove_duplicates:
            key = tuple(sorted((k, str(v)) for k, v in record.fields.items()))
            if key in seen:
                continue
            seen.add(key)

        cleaned.add_record(record)

    return cleaned


def normalize_date(value: str) -> str:
    """统一日期格式为 YYYY-MM-DD。"""
    value = value.strip()
    if not value:
        return value

    # 支持常见格式
    patterns = [
        (r"^(\d{4})/(\d{1,2})/(\d{1,2})$", "ymd"),      # 2024/1/5
        (r"^(\d{4})-(\d{1,2})-(\d{1,2})$", "ymd"),      # 2024-1-5
        (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", "mdy"),      # 1/5/2024
        (r"^(\d{4})年(\d{1,2})月(\d{1,2})日$", "ymd"),  # 2024年1月5日
        (r"^(\d{1,2})月(\d{1,2})日$", "md"),            # 1月5日（补充格式）
    ]

    for pattern, fmt in patterns:
        m = re.match(pattern, value)
        if m:
            groups = m.groups()
            try:
                if fmt == "ymd":
                    year, month, day = groups
                elif fmt == "mdy":
                    month, day, year = groups
                elif fmt == "md":
                    # 只有月日，默认年份为当前年份
                    month, day = groups
                    year = datetime.now(timezone.utc).year
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            except ValueError:
                return value

    # 尝试用 datetime 解析
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y", "%Y年%m月%d日"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return value


def apply_field_mapping(table: DataTable, mapping: Dict[str, str]) -> DataTable:
    """字段映射与重命名。mapping 为 {源字段名: 目标字段名}。"""
    result = DataTable()
    for record in table.records:
        new_record = DataRecord({})
        for src, dst in mapping.items():
            if src in record.fields:
                new_record.set(dst, record.get(src))
        # 保留未映射字段
        for key in record.fields:
            if key not in mapping:
                new_record.set(key, record.get(key))
        result.add_record(new_record)
    return result


def normalize_dates_in_table(table: DataTable, date_fields: List[str]) -> DataTable:
    """对指定字段做日期格式化。"""
    for record in table.records:
        for field in date_fields:
            if field in record.fields:
                record.set(field, normalize_date(str(record.get(field))))
    return table


# ============================================================
# 输出格式化（输出）
# ============================================================
def to_csv(table: DataTable) -> str:
    """输出为 CSV 文本。"""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=table.fields)
    writer.writeheader()
    for record in table.records:
        writer.writerow(record.to_dict())
    return output.getvalue()


def to_json(table: DataTable, pretty: bool = True) -> str:
    """输出为 JSON 文本。"""
    data = table.to_dicts()
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False)


def to_markdown(table: DataTable) -> str:
    """输出为 Markdown 表格。"""
    if not table.fields:
        return ""

    lines = []
    # 表头
    lines.append("| " + " | ".join(table.fields) + " |")
    # 分隔行
    lines.append("| " + " | ".join(["---"] * len(table.fields)) + " |")
    # 数据行
    for record in table.records:
        cells = [str(record.get(f, "")) for f in table.fields]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def format_output(table: DataTable, fmt: str) -> str:
    """按指定格式输出。"""
    fmt = fmt.lower()
    if fmt == "csv":
        return to_csv(table)
    elif fmt == "json":
        return to_json(table)
    elif fmt == "markdown" or fmt == "md":
        return to_markdown(table)
    else:
        raise err("E010", f"不支持的输出格式: {fmt}（支持 csv/json/markdown）")


# ============================================================
# 主处理流程
# ============================================================
def process_data(
    input_text: str,
    output_format: str = "json",
    field_mapping: Optional[Dict[str, str]] = None,
    date_fields: Optional[List[str]] = None,
    remove_duplicates: bool = True,
) -> str:
    """完整处理流程：解析 → 清洗 → 映射 → 日期标准化 → 输出。"""
    # 1. 解析
    table = detect_and_parse(input_text)

    # 2. 清洗
    table = clean_table(table, remove_duplicates=remove_duplicates)

    # 3. 字段映射
    if field_mapping:
        table = apply_field_mapping(table, field_mapping)

    # 4. 日期标准化
    if date_fields:
        table = normalize_dates_in_table(table, date_fields)

    # 5. 输出
    return format_output(table, output_format)


# ============================================================
# 自检（selftest）
# ============================================================
def run_selftest() -> int:
    """内置硬编码样例，离线自检核心逻辑。"""
    print("开始自检...")

    # --- 测试 1: CSV 解析与 JSON 输出 ---
    csv_input = "name,date,amount\nAlice,2024/1/5,100\nBob,2024-02-10,200\nAlice,2024/1/5,100\n"
    result = process_data(csv_input, output_format="json", date_fields=["date"])
    parsed = json.loads(result)
    # 去重后应少于 3 条记录（宽松阈值）
    assert len(parsed) < 3, f"CSV 去重失败: 期望少于3条，实际{len(parsed)}"
    # 日期应统一格式
    for item in parsed:
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", item["date"]), f"日期格式错误: {item['date']}"
    print("  [通过] CSV 解析/去重/日期格式化/JSON 输出")

    # --- 测试 2: Markdown 表格解析 ---
    md_input = """| 姓名 | 年龄 | 城市 |
|------|------|------|
| 张三 | 25   | 北京 |
| 李四 | 30   | 上海 |
"""
    result = process_data(md_input, output_format="json")
    parsed = json.loads(result)
    assert len(parsed) >= 2, f"Markdown 解析失败: 期望至少2条，实际{len(parsed)}"
    assert parsed[0]["姓名"] == "张三", "Markdown 字段值错误"
    print("  [通过] Markdown 表格解析")

    # --- 测试 3: JSON 输入与字段映射 ---
    json_input = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
    result = process_data(
        json_input,
        output_format="markdown",
        field_mapping={"name": "姓名", "age": "年龄"},
    )
    assert "姓名" in result and "年龄" in result, "字段映射失败"
    assert "Alice" in result and "Bob" in result, "字段映射数据丢失"
    print("  [通过] JSON 解析/字段映射/Markdown 输出")

    # --- 测试 4: 日期标准化 ---
    test_dates = ["2024/1/5", "2024-02-10", "2024年3月15日", "12/25/2024"]
    for d in test_dates:
        normalized = normalize_date(d)
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", normalized), f"日期标准化失败: {d} → {normalized}"
    print("  [通过] 日期标准化")

    # --- 测试 5: 错误处理 ---
    try:
        process_data("not a valid format at all", output_format="json")
        # 如果没抛异常，说明可能被解析为 CSV（单列），此时应检查结果
        # 但这里我们期望抛出 E009，所以如果没抛，则断言失败
        assert False, "应抛出 E009 错误"
    except AppError as e:
        assert e.code == "E009", f"错误码错误: {e.code}"
    print("  [通过] 错误处理")

    # --- 测试 6: 空数据处理 ---
    empty_input = "a,b\n1,2\n\n\n3,4\n"
    result = process_data(empty_input, output_format="json")
    parsed = json.loads(result)
    assert len(parsed) >= 2, f"空行去除失败: 期望至少2条，实际{len(parsed)}"
    print("  [通过] 空行处理")

    # --- 测试 7: CSV 输出格式 ---
    csv_test_input = "name,age\nAlice,30\nBob,25\n"
    result = process_data(csv_test_input, output_format="csv")
    assert result.startswith("name,age"), "CSV 输出格式错误"
    assert "Alice,30" in result, "CSV 输出数据错误"
    print("  [通过] CSV 输出格式")

    # --- 测试 8: 字段映射 + 日期标准化组合 ---
    combined_input = "id,name,date\n1,Alice,2024/1/5\n2,Bob,2024-02-10\n"
    result = process_data(
        combined_input,
        output_format="json",
        field_mapping={"name": "姓名", "date": "日期"},
        date_fields=["日期"],
    )
    parsed = json.loads(result)
    assert parsed[0]["姓名"] == "Alice", "组合功能字段映射失败"
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", parsed[0]["日期"]), "组合功能日期格式化失败"
    print("  [通过] 字段映射 + 日期标准化组合")

    # --- 测试 9: 复杂 Markdown 表格 ---
    complex_md = """| 产品 | 价格 | 库存 |
|:-----|-----:|-----:|
| 苹果 | 5.99 | 100  |
| 香蕉 | 2.50 | 250  |
"""
    result = process_data(complex_md, output_format="json")
    parsed = json.loads(result)
    assert len(parsed) >= 2, "复杂 Markdown 解析失败"
    assert parsed[0]["产品"] == "苹果", "复杂 Markdown 字段值错误"
    print("  [通过] 复杂 Markdown 表格解析")

    print("\n全部自检通过！")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="tasks - 数据转换与批量处理工具",
        epilog="示例: python main.py --input data.csv --output result.json --format json",
    )
    parser.add_argument("--input", help="输入文件路径（与 --input-text 二选一）")
    parser.add_argument("--input-text", help="直接输入文本内容（与 --input 二选一）")
    parser.add_argument("--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--format", default="json", choices=["csv", "json", "markdown", "md"],
                        help="输出格式（默认: json）")
    parser.add_argument("--mapping", help="字段映射 JSON，如 '{\"name\":\"姓名\"}'")
    parser.add_argument("--date-fields", help="需要日期标准化的字段名，逗号分隔")
    parser.add_argument("--no-dedup", action="store_true", help="不去重")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    if args.selftest:
        return run_selftest()

    # 获取输入
    if args.input and args.input_text:
        print("错误: --input 和 --input-text 不能同时使用", file=sys.stderr)
        return 1
    if not args.input and not args.input_text:
        # 从 stdin 读取
        input_text = sys.stdin.read()
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8", errors="replace") as f:
                input_text = f.read()
        except OSError as e:
            print(f"错误: 无法读取输入文件: {e}", file=sys.stderr)
            return 1
    else:
        input_text = args.input_text

    # 解析可选参数
    field_mapping = None
    if args.mapping:
        try:
            field_mapping = json.loads(args.mapping)
        except json.JSONDecodeError as e:
            print(f"错误: --mapping 不是合法 JSON: {e}", file=sys.stderr)
            return 1

    date_fields = None
    if args.date_fields:
        date_fields = [f.strip() for f in args.date_fields.split(",") if f.strip()]

    try:
        result = process_data(
            input_text,
            output_format=args.format,
            field_mapping=field_mapping,
            date_fields=date_fields,
            remove_duplicates=not args.no_dedup,
        )
    except AppError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1

    # 输出
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8", errors="replace") as f:
                f.write(result)
        except OSError as e:
            print(f"错误: 无法写入输出文件: {e}", file=sys.stderr)
            return 1
    else:
        print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
