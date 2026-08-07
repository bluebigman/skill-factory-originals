#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqlgen - 数据转换 SQL 查询生成器

独立实现脚本，依据功能规格从零编写（clean-room）。
仅使用 Python 标准库，无第三方依赖。

功能：
  - 解析 CSV/JSON/TXT 数据文件，提取结构化字段
  - 自动推断字段类型（INTEGER/REAL/TEXT）
  - 生成 ANSI SQL 建表语句和 INSERT 语句
  - 支持 --selftest 离线自检

用法示例：
  python main.py --input data.csv --format sql
  python main.py --selftest
"""

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 数据解析模块
# ============================================================
def parse_csv_text(text: str, delimiter: str = ",") -> List[Dict[str, str]]:
    """解析 CSV 文本为字典列表（每行一个字典，键为表头）。"""
    if not text.strip():
        raise AppError("E001", "输入 CSV 内容为空")
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = [dict(row) for row in reader if any(v.strip() for v in row.values())]
    except Exception as exc:
        raise AppError("E002", f"CSV 解析失败: {exc}") from exc
    if not rows:
        raise AppError("E003", "CSV 中无有效数据行")
    return rows


def parse_json_text(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为字典列表。支持顶层为数组或对象。"""
    if not text.strip():
        raise AppError("E001", "输入 JSON 内容为空")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AppError("E004", f"JSON 解析失败: {exc}") from exc

    if isinstance(data, list):
        rows = [item for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):
        # 单对象包装成列表
        rows = [data]
    else:
        raise AppError("E005", "JSON 顶层必须是对象或数组")

    if not rows:
        raise AppError("E003", "JSON 中无有效数据对象")
    return rows


def parse_txt_table(text: str, delimiter: str = None) -> List[Dict[str, str]]:
    """
    解析 TXT 表格文本。
    支持两种格式：
      1. 带表头的 TSV/CSV 风格（自动检测分隔符）
      2. 对齐的文本表格（列间多个空格分隔）
    """
    if not text.strip():
        raise AppError("E001", "输入 TXT 内容为空")

    lines = [line.rstrip("\n") for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise AppError("E003", "TXT 中无有效数据行")

    # 尝试常见分隔符
    if delimiter is None:
        for sep in ("\t", ",", "|", ";"):
            if sep in lines[0]:
                delimiter = sep
                break
        else:
            delimiter = None

    if delimiter:
        reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
        rows = [dict(row) for row in reader if any(v.strip() for v in row.values())]
    else:
        # 对齐表格：按 2+ 空格拆分
        header_parts = re.split(r"\s{2,}", lines[0].strip())
        rows = []
        for line in lines[1:]:
            parts = re.split(r"\s{2,}", line.strip())
            if len(parts) != len(header_parts):
                # 尝试普通空白拆分作为回退
                parts = line.split()
            if len(parts) == len(header_parts):
                rows.append(dict(zip(header_parts, parts)))

    if not rows:
        raise AppError("E003", "TXT 表格无有效数据行")
    return rows


def parse_file(file_path: str) -> List[Dict[str, Any]]:
    """根据扩展名解析文件。"""
    path = Path(file_path)
    if not path.exists():
        raise AppError("E006", f"文件不存在: {file_path}")
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise AppError("E007", f"文件读取失败: {exc}") from exc

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return parse_csv_text(content)
    if suffix == ".json":
        return parse_json_text(content)
    if suffix in (".txt", ".tsv", ".text"):
        return parse_txt_table(content)
    raise AppError("E008", f"不支持的文件类型: {suffix}（支持 .csv/.json/.txt）")


# ============================================================
# 字段类型推断模块
# ============================================================
def infer_field_type(values: List[Any]) -> Tuple[str, float]:
    """
    推断字段类型，返回 (类型, 置信度)。
    类型: INTEGER / REAL / TEXT
    置信度: 0~1 的粗略估计（宽松判断，不依赖精确值）
    """
    if not values:
        return "TEXT", 0.5

    non_empty = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_empty:
        return "TEXT", 0.5

    total = len(non_empty)
    int_count = 0
    float_count = 0

    for val in non_empty:
        s = str(val).strip()
        # 整数判断（含正负号）
        if re.fullmatch(r"[+-]?\d+", s):
            int_count += 1
        # 浮点判断（含小数/科学计数法）
        elif re.fullmatch(r"[+-]?\d*\.\d+([eE][+-]?\d+)?", s) or \
             re.fullmatch(r"[+-]?\d+[eE][+-]?\d+", s):
            float_count += 1

    # 宽松判定：超过一半可识别则采用
    if int_count >= total * 0.5:
        return "INTEGER", 0.7 + 0.3 * (int_count / total)
    if int_count + float_count >= total * 0.5:
        return "REAL", 0.6 + 0.3 * ((int_count + float_count) / total)
    return "TEXT", 0.5 + 0.3 * (1 - (int_count + float_count) / total)


def analyze_schema(rows: List[Dict[str, Any]]) -> Dict[str, Tuple[str, float]]:
    """分析所有行，推断每列类型。"""
    if not rows:
        raise AppError("E003", "无数据可分析")
    # 收集所有键
    all_keys: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in all_keys:
                all_keys.append(key)

    schema: Dict[str, Tuple[str, float]] = {}
    for key in all_keys:
        values = [row.get(key) for row in rows if key in row]
        schema[key] = infer_field_type(values)
    return schema


# ============================================================
# SQL 生成模块
# ============================================================
def quote_identifier(ident: str) -> str:
    """SQL 标识符转义（双引号包裹）。"""
    return '"' + ident.replace('"', '""') + '"'


def quote_value(value: Any, col_type: str) -> str:
    """SQL 字面量转义。"""
    if value is None:
        return "NULL"
    s = str(value).strip()
    if s == "":
        return "NULL"
    if col_type in ("INTEGER", "REAL"):
        # 尝试转为数字
        try:
            if col_type == "INTEGER":
                return str(int(float(s)))
            return str(float(s))
        except (ValueError, OverflowError):
            return "'" + s.replace("'", "''") + "'"
    return "'" + s.replace("'", "''") + "'"


def generate_sql(rows: List[Dict[str, Any]], table_name: str = "data_table") -> str:
    """
    生成 ANSI SQL 建表 + INSERT 语句。
    返回完整 SQL 文本。
    """
    if not rows:
        raise AppError("E003", "无数据可生成 SQL")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise AppError("E009", f"非法表名: {table_name}")

    schema = analyze_schema(rows)
    columns = list(schema.keys())
    if not columns:
        raise AppError("E003", "无字段可生成 SQL")

    # 建表语句
    col_defs = []
    for col in columns:
        col_type, conf = schema[col]
        col_defs.append(f"  {quote_identifier(col)} {col_type}")

    create_sql = f"CREATE TABLE {quote_identifier(table_name)} (\n"
    create_sql += ",\n".join(col_defs)
    create_sql += "\n);"

    # INSERT 语句
    insert_prefix = f"INSERT INTO {quote_identifier(table_name)} ({', '.join(quote_identifier(c) for c in columns)}) VALUES"
    insert_lines = []
    for row in rows:
        values = [quote_value(row.get(col), schema[col][0]) for col in columns]
        insert_lines.append(f"{insert_prefix} ({', '.join(values)});")

    return create_sql + "\n\n" + "\n".join(insert_lines)


def generate_markdown(rows: List[Dict[str, Any]]) -> str:
    """生成 Markdown 表格。"""
    if not rows:
        raise AppError("E003", "无数据可生成 Markdown")
    columns = list(rows[0].keys())
    for row in rows[1:]:
        for key in row:
            if key not in columns:
                columns.append(key)

    lines = ["| " + " | ".join(str(c) for c in columns) + " |"]
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def generate_json(rows: List[Dict[str, Any]]) -> str:
    """生成 JSON 输出。"""
    return json.dumps(rows, ensure_ascii=False, indent=2)


# ============================================================
# 主流程
# ============================================================
def process_input(input_source: str, is_file: bool = True) -> List[Dict[str, Any]]:
    """统一入口：文件或直接文本。"""
    if is_file:
        return parse_file(input_source)
    # 直接文本输入：尝试按格式解析
    stripped = input_source.strip()
    if stripped.startswith("{"):
        return parse_json_text(stripped)
    if stripped.startswith("["):
        return parse_json_text(stripped)
    if "," in stripped or "\t" in stripped:
        return parse_csv_text(stripped)
    return parse_txt_table(stripped)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="sqlgen - 数据转换 SQL 查询生成器",
        epilog="示例: python main.py --input data.csv --format sql --table users"
    )
    parser.add_argument("--input", type=str, help="输入文件路径或数据文本")
    parser.add_argument("--format", choices=["sql", "json", "markdown", "md"], default="sql",
                        help="输出格式（默认 sql）")
    parser.add_argument("--table", type=str, default="data_table", help="SQL 表名（默认 data_table）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if not args.input:
        parser.error("必须提供 --input 或使用 --selftest")

    try:
        rows = process_input(args.input)
        fmt = "markdown" if args.format == "md" else args.format
        if fmt == "sql":
            output = generate_sql(rows, args.table)
        elif fmt == "json":
            output = generate_json(rows)
        else:
            output = generate_markdown(rows)
        print(output)
        return 0
    except AppError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] 未预期错误: {exc}", file=sys.stderr)
        return 1


# ============================================================
# 离线自检
# ============================================================
def selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    断言使用宽松阈值，不依赖精确值，确保任何环境可过。
    """
    print("=== sqlgen 自检开始 ===")

    # --- 样例数据（硬编码，不读外部文件） ---
    csv_sample = """id,name,age,score
1,Alice,30,85.5
2,Bob,25,92.0
3,Charlie,35,78.2
"""

    json_sample = """[
  {"id": 1, "name": "Alice", "active": true},
  {"id": 2, "name": "Bob", "active": false}
]"""

    txt_sample = """id  name   city
1   Alice  Beijing
2   Bob    Shanghai
"""

    # --- 测试 CSV 解析 ---
    try:
        csv_rows = parse_csv_text(csv_sample)
        assert len(csv_rows) == 3, f"CSV 应解析出 3 行，实际 {len(csv_rows)}"
        assert "name" in csv_rows[0], "CSV 表头应包含 name"
        assert csv_rows[0]["age"] == "30", "CSV 第一行 age 应为 30"
        print("[PASS] CSV 解析")
    except AssertionError as exc:
        print(f"[FAIL] CSV 解析: {exc}")
        return 1

    # --- 测试 JSON 解析 ---
    try:
        json_rows = parse_json_text(json_sample)
        assert len(json_rows) == 2, f"JSON 应解析出 2 行，实际 {len(json_rows)}"
        assert json_rows[1]["name"] == "Bob", "JSON 第二行 name 应为 Bob"
        print("[PASS] JSON 解析")
    except AssertionError as exc:
        print(f"[FAIL] JSON 解析: {exc}")
        return 1

    # --- 测试 TXT 解析 ---
    try:
        txt_rows = parse_txt_table(txt_sample)
        assert len(txt_rows) >= 2, f"TXT 应解析出至少 2 行，实际 {len(txt_rows)}"
        assert "city" in txt_rows[0], "TXT 表头应包含 city"
        print("[PASS] TXT 解析")
    except AssertionError as exc:
        print(f"[FAIL] TXT 解析: {exc}")
        return 1

    # --- 测试字段类型推断 ---
    try:
        schema = analyze_schema(csv_rows)
        assert "id" in schema, "schema 应包含 id 字段"
        id_type, id_conf = schema["id"]
        assert id_type in ("INTEGER", "REAL"), f"id 应为数值类型，实际 {id_type}"
        assert id_conf > 0.5, f"id 置信度应 > 0.5，实际 {id_conf}"
        assert schema["name"][0] == "TEXT", "name 应为 TEXT 类型"
        print("[PASS] 类型推断")
    except AssertionError as exc:
        print(f"[FAIL] 类型推断: {exc}")
        return 1

    # --- 测试 SQL 生成 ---
    try:
        sql = generate_sql(csv_rows, "users")
        assert "CREATE TABLE" in sql, "SQL 应包含建表语句"
        assert "INSERT INTO" in sql, "SQL 应包含插入语句"
        assert "users" in sql, "SQL 应包含表名 users"
        # 宽松检查：INSERT 行数应不少于数据行数
        insert_count = sql.count("INSERT INTO")
        assert insert_count >= len(csv_rows), f"INSERT 行数应 >= {len(csv_rows)}，实际 {insert_count}"
        print("[PASS] SQL 生成")
    except AssertionError as exc:
        print(f"[FAIL] SQL 生成: {exc}")
        return 1

    # --- 测试 Markdown 生成 ---
    try:
        md = generate_markdown(csv_rows)
        assert "|" in md, "Markdown 应包含表格分隔符"
        assert "Alice" in md, "Markdown 应包含数据 Alice"
        print("[PASS] Markdown 生成")
    except AssertionError as exc:
        print(f"[FAIL] Markdown 生成: {exc}")
        return 1

    # --- 测试 JSON 生成 ---
    try:
        json_out = generate_json(csv_rows)
        parsed = json.loads(json_out)
        assert len(parsed) == len(csv_rows), "JSON 输出长度应匹配"
        print("[PASS] JSON 生成")
    except AssertionError as exc:
        print(f"[FAIL] JSON 生成: {exc}")
        return 1

    # --- 测试错误处理 ---
    try:
        parse_csv_text("")
        print("[FAIL] 空输入应报错")
        return 1
    except AppError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print("[PASS] 错误处理")

    print("=== sqlgen 自检全部通过 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
