#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tasks - 数据转换与批量处理工具

功能：
- 解析 CSV / JSON / JSONL / TXT 等常见格式
- 结构化转换：将非结构化数据映射为字段明确的记录
- 批量处理：对多条同类数据执行相同转换规则
- 自定义格式输出：JSON / JSONL / CSV
- 字段映射与重命名（支持点号嵌套展开）
- 日期格式化、常量字段注入
- 试运行模式（--dry-run）与小样本验证（--sample）

用法示例：
    python run.py --input data.csv --output result.json --format json
    python run.py --input-dir ./input --output-dir ./output --format jsonl
    python run.py --input data.csv --dry-run --sample 5 --verbose
    python run.py --selftest
"""

import argparse
import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
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
            if new in self.fields and new != old:
                raise err("E003", f"字段重命名冲突: '{old}' -> '{new}'，目标字段已存在")
            self.fields[new] = self.fields.pop(old)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.fields)


class DataTable:
    """数据表：包含字段列表和多条记录。"""
    def __init__(self, fields: List[str], records: List[DataRecord]):
        self.fields = fields
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def add_record(self, record: DataRecord) -> None:
        self.records.append(record)
        for key in record.fields:
            if key not in self.fields:
                self.fields.append(key)


# ============================================================
# 输入解析
# ============================================================
def read_file_with_encoding(filepath: str) -> str:
    """读取文件内容，自动尝试多种编码。"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise err("E001", f"输入文件不存在: {filepath}")
    raise err("E006", f"无法识别文件编码: {filepath}（尝试了 utf-8/gbk/gb18030）")


def parse_csv(content: str) -> DataTable:
    """解析 CSV 内容。"""
    reader = csv.DictReader(io.StringIO(content))
    fields = reader.fieldnames or []
    records = []
    for row in reader:
        records.append(DataRecord(dict(row)))
    return DataTable(fields, records)


def parse_json(content: str) -> DataTable:
    """解析 JSON 内容（支持数组或对象数组）。"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise err("E007", f"JSON 解析失败: {e}")
    if not isinstance(data, list):
        raise err("E008", "JSON 顶层必须是数组")
    records = []
    fields = []
    for item in data:
        if not isinstance(item, dict):
            raise err("E009", f"JSON 数组元素必须是对象，得到: {type(item)}")
        records.append(DataRecord(item))
        for key in item:
            if key not in fields:
                fields.append(key)
    return DataTable(fields, records)


def parse_jsonl(content: str) -> DataTable:
    """解析 JSONL 内容（每行一个 JSON 对象）。"""
    records = []
    fields = []
    for line_num, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as e:
            raise err("E010", f"JSONL 第 {line_num} 行解析失败: {e}")
        if not isinstance(item, dict):
            raise err("E011", f"JSONL 第 {line_num} 行不是对象")
        records.append(DataRecord(item))
        for key in item:
            if key not in fields:
                fields.append(key)
    return DataTable(fields, records)


def parse_txt(content: str) -> DataTable:
    """解析 TXT 内容（Tab 分隔，首行为表头）。"""
    lines = content.splitlines()
    if not lines:
        return DataTable([], [])
    header = lines[0].split("\t")
    records = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = line.split("\t")
        row = {}
        for i, field in enumerate(header):
            row[field] = values[i] if i < len(values) else ""
        records.append(DataRecord(row))
    return DataTable(header, records)


def parse_input(filepath: str) -> DataTable:
    """根据文件扩展名解析输入文件。"""
    ext = os.path.splitext(filepath)[1].lower()
    content = read_file_with_encoding(filepath)
    if ext == ".csv":
        return parse_csv(content)
    elif ext == ".json":
        return parse_json(content)
    elif ext == ".jsonl":
        return parse_jsonl(content)
    elif ext == ".txt":
        return parse_txt(content)
    else:
        raise err("E002", f"不支持的输入格式: {ext}（支持 .csv/.json/.jsonl/.txt）")


# ============================================================
# 字段映射与转换
# ============================================================
def resolve_nested_path(data: Dict[str, Any], path: str) -> Any:
    """解析点号路径，如 'user.address.city'。"""
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def apply_field_mapping(record: DataRecord, mapping: Dict[str, str]) -> DataRecord:
    """应用字段映射（支持点号嵌套展开）。"""
    new_fields = {}
    for old_path, new_name in mapping.items():
        value = resolve_nested_path(record.fields, old_path)
        if value is not None:
            new_fields[new_name] = value
    # 保留未映射的字段
    mapped_old = set(mapping.keys())
    for key, value in record.fields.items():
        if key not in mapped_old:
            new_fields[key] = value
    return DataRecord(new_fields)


def apply_output_fields(record: DataRecord, output_fields: List[str]) -> DataRecord:
    """按白名单筛选字段并排序。"""
    if not output_fields:
        return record
    new_fields = {}
    for field in output_fields:
        if field in record.fields:
            new_fields[field] = record.fields[field]
    return DataRecord(new_fields)


def apply_date_format(record: DataRecord, date_fields: List[str], date_format: str) -> DataRecord:
    """格式化日期字段。"""
    if not date_fields or not date_format:
        return record
    for field in date_fields:
        if field in record.fields:
            value = record.fields[field]
            if isinstance(value, str) and value.strip():
                try:
                    # 尝试多种常见日期格式
                    parsed = None
                    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            parsed = datetime.strptime(value.strip(), fmt)
                            break
                        except ValueError:
                            continue
                    if parsed is None:
                        raise ValueError(f"无法解析日期: {value}")
                    record.fields[field] = parsed.strftime(date_format)
                except ValueError as e:
                    print(f"[WARN] 日期格式化失败: {e}", file=sys.stderr)
    return record


def apply_constant_fields(record: DataRecord, constant_fields: Dict[str, str]) -> DataRecord:
    """注入常量字段。"""
    for key, value in constant_fields.items():
        record.fields[key] = value
    return record


def transform_record(record: DataRecord, args) -> DataRecord:
    """对单条记录执行完整转换流程。"""
    # 字段映射
    if args.field_mapping:
        record = apply_field_mapping(record, args.field_mapping)
    # 日期格式化
    if args.date_fields and args.date_format:
        record = apply_date_format(record, args.date_fields, args.date_format)
    # 常量字段
    if args.constant_fields:
        record = apply_constant_fields(record, args.constant_fields)
    # 输出字段筛选
    if args.output_fields:
        record = apply_output_fields(record, args.output_fields)
    return record


# ============================================================
# 输出
# ============================================================
def atomic_write(filepath: str, content: str) -> None:
    """原子化写入文件（先写临时文件再重命名）。"""
    dirname = os.path.dirname(filepath)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
    tmp_path = filepath + f".tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def format_output(table: DataTable, output_format: str) -> str:
    """将数据表格式化为指定格式的字符串。"""
    if output_format == "json":
        return json.dumps([r.to_dict() for r in table.records], ensure_ascii=False, indent=2)
    elif output_format == "jsonl":
        return "\n".join(json.dumps(r.to_dict(), ensure_ascii=False) for r in table.records)
    elif output_format == "csv":
        if not table.records:
            return ""
        fields = table.fields
        output = [",".join(fields)]
        for record in table.records:
            output.append(",".join(str(record.get(f, "")) for f in fields))
        return "\n".join(output)
    else:
        raise err("E012", f"不支持的输出格式: {output_format}")


def write_output(table: DataTable, output_path: str, output_format: str, dry_run: bool) -> None:
    """写入输出文件（支持 dry-run 模式）。"""
    content = format_output(table, output_format)
    if not dry_run:
        atomic_write(output_path, content)
        print(f"[OK] 已写入: {output_path} ({len(table.records)} 条记录)")
        return
    print(f"[DRY-RUN] 将写入: {output_path}")
    print(f"[DRY-RUN] 内容预览（前 500 字符）:")
    print(content[:500])


def write_report(report: Dict[str, Any], output_dir: str, dry_run: bool) -> None:
    """写入处理报告。"""
    report_path = os.path.join(output_dir, "report.txt")
    lines = [
        f"处理时间: {report['timestamp']}",
        f"输入文件数: {report['input_files']}",
        f"总记录数: {report['total_records']}",
        f"成功记录数: {report['success_records']}",
        f"失败记录数: {report['failed_records']}",
        f"处理耗时: {report['elapsed_seconds']:.2f} 秒",
    ]
    if report["errors"]:
        lines.append("\n失败详情:")
        for error in report["errors"]:
            lines.append(f"  - {error}")
    content = "\n".join(lines)
    if not dry_run:
        atomic_write(report_path, content)
        print(f"[OK] 报告已写入: {report_path}")
        return
    print(f"[DRY-RUN] 将写入报告: {report_path}")
    print(content)


# ============================================================
# 主流程
# ============================================================
def process_file(filepath: str, output_path: str, args) -> Tuple[int, int, List[str]]:
    """处理单个文件，返回 (成功数, 失败数, 错误列表)。"""
    try:
        table = parse_input(filepath)
    except AppError as e:
        return 0, 0, [f"{filepath}: {e.code} {e.message}"]

    success = 0
    failed = 0
    errors = []
    transformed_records = []

    for i, record in enumerate(table.records):
        if args.sample and i >= args.sample:
            break
        try:
            transformed = transform_record(record, args)
            transformed_records.append(transformed)
            success += 1
        except AppError as e:
            failed += 1
            errors.append(f"{filepath} 第 {i+1} 行: {e.code} {e.message}")
        except Exception as e:
            failed += 1
            errors.append(f"{filepath} 第 {i+1} 行: 未知错误 {e}")

    if transformed_records:
        output_table = DataTable(
            list(transformed_records[0].fields.keys()),
            transformed_records
        )
        try:
            write_output(output_table, output_path, args.format, args.dry_run)
        except AppError as e:
            errors.append(f"{output_path}: {e.code} {e.message}")

    return success, failed, errors


def process_directory(input_dir: str, output_dir: str, args) -> Tuple[int, int, int, List[str]]:
    """处理目录下所有支持的文件。"""
    supported_exts = {".csv", ".json", ".jsonl", ".txt"}
    files = [f for f in os.listdir(input_dir) if os.path.splitext(f)[1].lower() in supported_exts]
    files.sort()

    total_success = 0
    total_failed = 0
    all_errors = []

    for filename in files:
        input_path = os.path.join(input_dir, filename)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.{args.format}")
        success, failed, errors = process_file(input_path, output_path, args)
        total_success += success
        total_failed += failed
        all_errors.extend(errors)

    return len(files), total_success, total_failed, all_errors


def main() -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="数据转换与批量处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--input-dir", type=str, help="输入目录路径")
    parser.add_argument("--output", type=str, default="./output/result.json", help="输出文件路径")
    parser.add_argument("--output-dir", type=str, default="./output", help="输出目录路径")
    parser.add_argument("--format", type=str, default="json", choices=["json", "jsonl", "csv"], help="输出格式")
    parser.add_argument("--field-mapping", type=str, help="字段映射 JSON，如 '{\"old\": \"new\"}'")
    parser.add_argument("--output-fields", type=str, help="输出字段白名单，逗号分隔")
    parser.add_argument("--date-format", type=str, help="日期输出格式（Python strftime 语法）")
    parser.add_argument("--date-fields", type=str, help="日期字段列表，逗号分隔")
    parser.add_argument("--constant-fields", type=str, help="常量字段，如 'source=internal'")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不写盘")
    parser.add_argument("--sample", type=int, help="仅处理前 N 条记录")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    if args.selftest:
        return run_selftest()

    # 解析复杂参数
    try:
        args.field_mapping = json.loads(args.field_mapping) if args.field_mapping else {}
        args.output_fields = [f.strip() for f in args.output_fields.split(",")] if args.output_fields else []
        args.date_fields = [f.strip() for f in args.date_fields.split(",")] if args.date_fields else []
        args.constant_fields = {}
        if args.constant_fields:
            for pair in args.constant_fields.split(","):
                key, _, value = pair.partition("=")
                args.constant_fields[key.strip()] = value.strip()
    except json.JSONDecodeError as e:
        print(f"[ERROR] 参数解析失败: {e}", file=sys.stderr)
        return 1

    # 输入校验
    if not args.input and not args.input_dir:
        print("[ERROR] 必须指定 --input 或 --input-dir", file=sys.stderr)
        return 1
    if args.input and args.input_dir:
        print("[ERROR] --input 和 --input-dir 只能指定一个", file=sys.stderr)
        return 1

    start_time = time.time()
    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "input_files": 0,
        "total_records": 0,
        "success_records": 0,
        "failed_records": 0,
        "elapsed_seconds": 0.0,
        "errors": [],
    }

    try:
        if args.input:
            # 单文件模式
            if not os.path.exists(args.input):
                raise err("E001", f"输入文件不存在: {args.input}")
            success, failed, errors = process_file(args.input, args.output, args)
            report["input_files"] = 1
            report["success_records"] = success
            report["failed_records"] = failed
            report["errors"] = errors
        else:
            # 目录模式
            if not os.path.exists(args.input_dir):
                raise err("E001", f"输入目录不存在: {args.input_dir}")
            file_count, success, failed, errors = process_directory(args.input_dir, args.output_dir, args)
            report["input_files"] = file_count
            report["success_records"] = success
            report["failed_records"] = failed
            report["errors"] = errors
    except AppError as e:
        print(f"[ERROR] {e.code} {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] 未知错误: {e}", file=sys.stderr)
        return 1

    report["total_records"] = report["success_records"] + report["failed_records"]
    report["elapsed_seconds"] = time.time() - start_time

    # 写入报告
    output_dir = args.output_dir if args.input_dir else os.path.dirname(args.output)
    write_report(report, output_dir, args.dry_run)

    if args.verbose:
        print(f"\n[VERBOSE] 处理完成: {report['input_files']} 个文件, "
              f"{report['total_records']} 条记录, "
              f"成功 {report['success_records']}, 失败 {report['failed_records']}")
        for error in report["errors"]:
            print(f"[VERBOSE] 错误: {error}")

    return 0 if report["failed_records"] == 0 else 2


# ============================================================
# 自检
# ============================================================
def run_selftest() -> int:
    """运行内置自检，验证核心功能。"""
    print("=" * 60)
    print("运行自检...")
    failures = []

    # 测试 1: CSV 解析
    print("\n[测试 1] CSV 解析")
    csv_content = "name,age,city\n张三,28,北京\n李四,35,上海\n"
    table = parse_csv(csv_content)
    assert len(table) == 2, f"CSV 解析失败: 期望 2 条记录，得到 {len(table)}"
    assert table.records[0].get("name") == "张三", "CSV 解析失败: 第一条记录 name 字段错误"
    print(f"  [PASS] 解析 {len(table)} 条记录")

    # 测试 2: JSON 解析
    print("\n[测试 2] JSON 解析")
    json_content = '[{"name": "张三", "age": 28}, {"name": "李四", "age": 35}]'
    table = parse_json(json_content)
    assert len(table) == 2, f"JSON 解析失败: 期望 2 条记录，得到 {len(table)}"
    assert table.records[0].get("age") == 28, "JSON 解析失败: age 字段错误"
    print(f"  [PASS] 解析 {len(table)} 条记录")

    # 测试 3: JSONL 解析
    print("\n[测试 3] JSONL 解析")
    jsonl_content = '{"name": "张三", "age": 28}\n{"name": "李四", "age": 35}\n'
    table = parse_jsonl(jsonl_content)
    assert len(table) == 2, f"JSONL 解析失败: 期望 2 条记录，得到 {len(table)}"
    print(f"  [PASS] 解析 {len(table)} 条记录")

    # 测试 4: TXT 解析
    print("\n[测试 4] TXT 解析")
    txt_content = "name\tage\tcity\n张三\t28\t北京\n李四\t35\t上海\n"
    table = parse_txt(txt_content)
    assert len(table) == 2, f"TXT 解析失败: 期望 2 条记录，得到 {len(table)}"
    assert table.records[0].get("city") == "北京", "TXT 解析失败: city 字段错误"
    print(f"  [PASS] 解析 {len(table)} 条记录")

    # 测试 5: 字段映射
    print("\n[测试 5] 字段映射")
    record = DataRecord({"user": {"name": "张三", "age": "28"}})
    mapping = {"user.name": "name", "user.age": "age"}
    transformed = apply_field_mapping(record, mapping)
    assert transformed.get("name") == "张三", "字段映射失败: name 字段错误"
    assert transformed.get("age") == "28", "字段映射失败: age 字段错误"
    print("  [PASS] 字段映射正确")

    # 测试 6: 嵌套路径展开
    print("\n[测试 6] 嵌套路径展开")
    record = DataRecord({"user": {"address": {"city": "北京"}}})
    value = resolve_nested_path(record.fields, "user.address.city")
    assert value == "北京", f"嵌套路径展开失败: 期望 '北京'，得到 {value}"
    print("  [PASS] 嵌套路径展开正确")

    # 测试 7: 日期格式化
    print("\n[测试 7] 日期格式化")
    record = DataRecord({"created_at": "2024/01/15"})
    transformed = apply_date_format(record, ["created_at"], "%Y-%m-%d")
    assert transformed.get("created_at") == "2024-01-15", f"日期格式化失败: {transformed.get('created_at')}"
    print("  [PASS] 日期格式化正确")

    # 测试 8: 常量字段注入
    print("\n[测试 8] 常量字段注入")
    record = DataRecord({"name": "张三"})
    transformed = apply_constant_fields(record, {"source": "internal"})
    assert transformed.get("source") == "internal", "常量字段注入失败"
    print("  [PASS] 常量字段注入正确")

    # 测试 9: 输出字段筛选
    print("\n[测试 9] 输出字段筛选")
    record = DataRecord({"name": "张三", "age": "28", "city": "北京"})
    transformed = apply_output_fields(record, ["name", "city"])
    assert "age" not in transformed.fields, "输出字段筛选失败: age 不应存在"
    assert transformed.get("name") == "张三", "输出字段筛选失败: name 字段错误"
    print("  [PASS] 输出字段筛选正确")

    # 测试 10: 完整转换流程
    print("\n[测试 10] 完整转换流程")
    class Args:
        field_mapping = {"user_name": "name"}
        date_fields = ["created_at"]
        date_format = "%Y-%m-%d"
        constant_fields = {"source": "test"}
        output_fields = ["name", "created_at", "source"]

    args = Args()
    record = DataRecord({"user_name": "张三", "created_at": "2024/01/15"})
    transformed = transform_record(record, args)
    assert transformed.get("name") == "张三", "完整转换失败: name 字段错误"
    assert transformed.get("created_at") == "2024-01-15", "完整转换失败: 日期格式化错误"
    assert transformed.get("source") == "test", "完整转换失败: 常量字段错误"
    assert "user_name" not in transformed.fields, "完整转换失败: 原字段应被映射"
    print("  [PASS] 完整转换流程正确")

    # 测试 11: 输出格式化
    print("\n[测试 11] 输出格式化")
    table = DataTable(["name", "age"], [DataRecord({"name": "张三", "age": "28"})])
    json_output = format_output(table, "json")
    assert "张三" in json_output, "JSON 输出失败"
    jsonl_output = format_output(table, "jsonl")
    assert "张三" in jsonl_output, "JSONL 输出失败"
    csv_output = format_output(table, "csv")
    assert "name,age" in csv_output, "CSV 输出失败"
    print("  [PASS] 输出格式化正确")

    # 测试 12: 空输入处理
    print("\n[测试 12] 空输入处理")
    empty_table = parse_csv("")
    assert len(empty_table) == 0, "空输入处理失败"
    print("  [PASS] 空输入处理正确")

    # 测试 13: 编码兼容
    print("\n[测试 13] 编码兼容")
    # 模拟 GBK 编码内容
    gbk_content = "name,age\n张三,28\n".encode("gbk")
    import io as io_module
    with open("/tmp/test_gbk.csv", "wb") as f:
        f.write(gbk_content)
    table = parse_input("/tmp/test_gbk.csv")
    assert len(table) == 1, "GBK 编码解析失败"
    assert table.records[0].get("name") == "张三", "GBK 编码解析失败: name 字段错误"
    # 使用 try/except 包裹删除操作，避免沙箱回收站问题
    try:
        os.remove("/tmp/test_gbk.csv")
    except OSError as e:
        print(f"  [WARN] 清理临时文件失败（不影响测试结果）: {e}")
    print("  [PASS] GBK 编码兼容正确")

    # 测试 14: 错误处理
    print("\n[测试 14] 错误处理")
    try:
        parse_input("/nonexistent/file.csv")
        failures.append("错误处理失败: 应抛出 E001 错误")
    except AppError as e:
        assert e.code == "E001", f"错误码错误: 期望 E001，得到 {e.code}"
        print("  [PASS] 错误处理正确")

    # 汇总
    print("\n" + "=" * 60)
    if failures:
        print(f"自检失败: {len(failures)} 项")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    else:
        print("全部 14 项测试通过 ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())
