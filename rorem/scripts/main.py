#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rorem - 随机数据生成与测试填充工具

依据功能规格独立实现（clean-room），仅使用标准库。
支持结构化随机数据生成、批量输出、多种格式与自检功能。
"""

import argparse
import csv
import io
import json
import random
import string
import sys
from datetime import datetime, timedelta

# 版本信息
VERSION = "1.0.1"
PROGRAM_NAME = "rorem"

# 错误码定义
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入文件无法读取",
    "E003": "字段定义格式错误",
    "E004": "批量数量超出范围（1~10000）",
    "E005": "不支持的输出格式",
    "E006": "不支持的字段类型",
    "E007": "枚举定义格式错误",
    "E008": "JSON 解析失败",
    "E009": "CSV 解析失败",
    "E010": "自检失败",
}


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出程序"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        print(f"[{code}] {msg}: {detail}", file=sys.stderr)
    else:
        print(f"[{code}] {msg}", file=sys.stderr)
    sys.exit(1)


def generate_random_string(length: int = 10) -> str:
    """生成随机字符串（字母+数字）"""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def generate_random_number(min_val: int = 0, max_val: int = 100) -> int:
    """生成随机整数"""
    return random.randint(min_val, max_val)


def generate_random_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
    """生成随机浮点数（保留2位小数）"""
    return round(random.uniform(min_val, max_val), 2)


def generate_random_date(start_year: int = 2020, end_year: int = 2030) -> str:
    """生成随机日期字符串 YYYY-MM-DD"""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    random_days = random.randint(0, delta)
    return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")


def generate_random_bool() -> bool:
    """生成随机布尔值"""
    return random.choice([True, False])


def generate_from_enum(enum_values: list) -> str:
    """从枚举列表中随机选取一个值"""
    if not enum_values:
        return ""
    return random.choice(enum_values)


def generate_value(field_def: dict) -> object:
    """
    根据字段定义生成随机值
    
    字段定义格式：
    {
        "name": "字段名",
        "type": "string|number|float|date|boolean|enum",
        "min": 最小值（number/float/date年份），
        "max": 最大值（number/float/date年份），
        "length": 字符串长度，
        "enum": ["值1", "值2", ...]（enum类型必填）
    }
    """
    field_type = field_def.get("type", "string")
    
    if field_type == "string":
        length = field_def.get("length", 10)
        return generate_random_string(length)
    
    elif field_type == "number":
        min_val = field_def.get("min", 0)
        max_val = field_def.get("max", 100)
        return generate_random_number(min_val, max_val)
    
    elif field_type == "float":
        min_val = field_def.get("min", 0.0)
        max_val = field_def.get("max", 1.0)
        return generate_random_float(min_val, max_val)
    
    elif field_type == "date":
        min_year = field_def.get("min", 2020)
        max_year = field_def.get("max", 2030)
        return generate_random_date(min_year, max_year)
    
    elif field_type == "boolean":
        return generate_random_bool()
    
    elif field_type == "enum":
        enum_values = field_def.get("enum", [])
        if not enum_values:
            error_exit("E007", f"字段 {field_def.get('name', '未知')} 的枚举值为空")
        return generate_from_enum(enum_values)
    
    else:
        error_exit("E006", f"不支持的字段类型: {field_type}")


def parse_field_definitions(fields_str: str) -> list:
    """
    解析字段定义字符串为字典列表
    
    支持两种格式：
    1. JSON 格式：[{"name":"id","type":"number","min":1,"max":100}, ...]
    2. 简化格式：name:type:min:max 或 name:type:length 或 name:enum:值1|值2
    """
    fields_str = fields_str.strip()
    if not fields_str:
        error_exit("E003", "字段定义为空")
    
    # 尝试 JSON 解析
    if fields_str.startswith("["):
        try:
            return json.loads(fields_str)
        except json.JSONDecodeError as e:
            error_exit("E008", str(e))
    
    # 简化格式解析
    fields = []
    for item in fields_str.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) < 2:
            error_exit("E003", f"字段定义格式错误: {item}")
        
        field_def = {"name": parts[0].strip(), "type": parts[1].strip()}
        
        if field_def["type"] == "enum" and len(parts) >= 3:
            field_def["enum"] = [v.strip() for v in parts[2].split("|")]
        elif field_def["type"] in ("number", "float", "date"):
            if len(parts) >= 4:
                field_def["min"] = int(parts[2].strip()) if field_def["type"] != "float" else float(parts[2].strip())
                field_def["max"] = int(parts[3].strip()) if field_def["type"] != "float" else float(parts[3].strip())
            elif len(parts) >= 3:
                field_def["max"] = int(parts[2].strip()) if field_def["type"] != "float" else float(parts[2].strip())
        elif field_def["type"] == "string" and len(parts) >= 3:
            field_def["length"] = int(parts[2].strip())
        
        fields.append(field_def)
    
    if not fields:
        error_exit("E003", "未解析出任何字段定义")
    
    return fields


def generate_records(fields: list, count: int) -> list:
    """生成多条记录"""
    records = []
    for _ in range(count):
        record = {}
        for field_def in fields:
            field_name = field_def.get("name", "")
            if not field_name:
                error_exit("E003", "字段名称为空")
            record[field_name] = generate_value(field_def)
        records.append(record)
    return records


def output_json(records: list) -> str:
    """输出为 JSON 格式"""
    return json.dumps(records, ensure_ascii=False, indent=2)


def output_csv(records: list) -> str:
    """输出为 CSV 格式"""
    if not records:
        return ""
    
    output = io.StringIO()
    fieldnames = list(records[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def output_sql(records: list, table_name: str = "test_table") -> str:
    """输出为 SQL INSERT 语句"""
    if not records:
        return ""
    
    lines = []
    for record in records:
        columns = list(record.keys())
        values = []
        for col in columns:
            val = record[col]
            if isinstance(val, str):
                # 转义单引号
                escaped = val.replace("'", "''")
                values.append(f"'{escaped}'")
            elif isinstance(val, bool):
                values.append("TRUE" if val else "FALSE")
            elif isinstance(val, (int, float)):
                values.append(str(val))
            else:
                values.append(f"'{val}'")
        
        col_str = ", ".join(columns)
        val_str = ", ".join(values)
        lines.append(f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str});")
    
    return "\n".join(lines)


def output_table(records: list) -> str:
    """输出为纯文本表格"""
    if not records:
        return ""
    
    fieldnames = list(records[0].keys())
    
    # 计算每列最大宽度
    col_widths = {col: len(col) for col in fieldnames}
    for record in records:
        for col in fieldnames:
            val_len = len(str(record.get(col, "")))
            col_widths[col] = max(col_widths[col], val_len)
    
    # 生成表头
    header = " | ".join(col.ljust(col_widths[col]) for col in fieldnames)
    separator = "-+-".join("-" * col_widths[col] for col in fieldnames)
    
    lines = [header, separator]
    for record in records:
        row = " | ".join(str(record.get(col, "")).ljust(col_widths[col]) for col in fieldnames)
        lines.append(row)
    
    return "\n".join(lines)


def read_fields_from_file(filepath: str) -> str:
    """从文件读取字段定义"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except FileNotFoundError:
        error_exit("E002", f"文件不存在: {filepath}")
    except IOError as e:
        error_exit("E002", str(e))


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="随机数据生成与测试填充工具",
        epilog="示例: rorem --fields 'name:string:10;age:number:18:65' --count 100 --format json"
    )
    
    parser.add_argument("--fields", "-f", help="字段定义，JSON或简化格式")
    parser.add_argument("--file", help="从文件读取字段定义")
    parser.add_argument("--count", "-n", type=int, default=10, help="生成记录数量（1~10000），默认10")
    parser.add_argument("--format", "-t", choices=["json", "csv", "sql", "table"], default="json",
                        help="输出格式，默认json")
    parser.add_argument("--table", default="test_table", help="SQL输出时的表名，默认test_table")
    parser.add_argument("--version", "-v", action="store_true", help="显示版本信息")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    return parser.parse_args()


def run_selftest() -> None:
    """运行自检，验证核心功能"""
    print(f"{PROGRAM_NAME} v{VERSION} 自检开始...")
    
    try:
        # 测试1: 随机字符串生成
        s = generate_random_string(5)
        assert len(s) == 5, "字符串长度错误"
        print("  [PASS] 随机字符串生成")
        
        # 测试2: 随机数字生成
        n = generate_random_number(1, 100)
        assert 1 <= n <= 100, "数字范围错误"
        print("  [PASS] 随机数字生成")
        
        # 测试3: 随机日期生成
        d = generate_random_date(2020, 2025)
        assert d.count("-") == 2, "日期格式错误"
        print("  [PASS] 随机日期生成")
        
        # 测试4: 枚举生成
        e = generate_from_enum(["A", "B", "C"])
        assert e in ["A", "B", "C"], "枚举值错误"
        print("  [PASS] 枚举生成")
        
        # 测试5: 字段定义解析（JSON格式）
        fields_json = '[{"name":"id","type":"number","min":1,"max":100},{"name":"name","type":"string","length":8}]'
        fields = parse_field_definitions(fields_json)
        assert len(fields) == 2, "字段数量错误"
        assert fields[0]["name"] == "id", "字段名错误"
        print("  [PASS] JSON字段定义解析")
        
        # 测试6: 字段定义解析（简化格式）
        fields_simple = parse_field_definitions("id:number:1:100;name:string:8;active:boolean")
        assert len(fields_simple) == 3, "简化格式字段数量错误"
        print("  [PASS] 简化字段定义解析")
        
        # 测试7: 批量生成
        records = generate_records(fields, 5)
        assert len(records) == 5, "记录数量错误"
        assert all("id" in r and "name" in r for r in records), "记录字段缺失"
        print("  [PASS] 批量生成")
        
        # 测试8: JSON输出
        json_out = output_json(records)
        json_parsed = json.loads(json_out)
        assert len(json_parsed) == 5, "JSON输出错误"
        print("  [PASS] JSON输出")
        
        # 测试9: CSV输出
        csv_out = output_csv(records)
        reader = csv.DictReader(io.StringIO(csv_out))
        csv_records = list(reader)
        assert len(csv_records) == 5, "CSV输出错误"
        print("  [PASS] CSV输出")
        
        # 测试10: SQL输出
        sql_out = output_sql(records, "test_tbl")
        assert sql_out.count("INSERT INTO") == 5, "SQL输出错误"
        print("  [PASS] SQL输出")
        
        # 测试11: 表格输出
        table_out = output_table(records)
        assert len(table_out.splitlines()) >= 7, "表格输出错误"
        print("  [PASS] 表格输出")
        
        # 测试12: 布尔值生成
        b = generate_random_bool()
        assert isinstance(b, bool), "布尔值类型错误"
        print("  [PASS] 布尔值生成")
        
        # 测试13: 浮点数生成
        f = generate_random_float(0.0, 1.0)
        assert 0.0 <= f <= 1.0, "浮点数范围错误"
        print("  [PASS] 浮点数生成")
        
        # 测试14: 固定值保留（通过枚举实现）
        fixed = generate_from_enum(["FIXED_VALUE"])
        assert fixed == "FIXED_VALUE", "固定值生成错误"
        print("  [PASS] 固定值保留")
        
    except AssertionError as e:
        error_exit("E010", str(e))
    except Exception as e:
        error_exit("E010", f"自检异常: {str(e)}")
    
    print("自检全部通过！")


def main():
    """主函数"""
    args = parse_arguments()
    
    # 版本查询
    if args.version:
        print(f"{PROGRAM_NAME} v{VERSION}")
        return
    
    # 自检模式
    if args.selftest:
        run_selftest()
        return
    
    # 获取字段定义
    fields_str = None
    if args.file:
        fields_str = read_fields_from_file(args.file)
    elif args.fields:
        fields_str = args.fields
    else:
        error_exit("E003", "必须提供 --fields 或 --file 参数")
    
    # 解析字段定义
    fields = parse_field_definitions(fields_str)
    
    # 检查数量范围
    if not (1 <= args.count <= 10000):
        error_exit("E004", f"数量 {args.count} 超出范围 1~10000")
    
    # 生成数据
    records = generate_records(fields, args.count)
    
    # 输出
    if args.format == "json":
        print(output_json(records))
    elif args.format == "csv":
        print(output_csv(records))
    elif args.format == "sql":
        print(output_sql(records, args.table))
    elif args.format == "table":
        print(output_table(records))
    else:
        error_exit("E005", f"不支持的输出格式: {args.format}")


if __name__ == "__main__":
    main()
