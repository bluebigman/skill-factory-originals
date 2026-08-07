#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 数据原型转换器（prototype）独立实现

功能：
- 将原始数据（CSV / JSON / TXT）转换为结构化结果
- 支持批量文件处理与自定义输出格式
- 提供 --selftest 离线自检模式

错误码：
    E001 参数错误
    E002 文件不存在
    E003 文件读取失败
    E004 数据解析失败
    E005 字段选择无效
    E006 类型转换失败
    E007 排序规则无效
    E008 输出写入失败
    E009 内部逻辑错误
    E010 不支持的格式
"""

import argparse
import csv
import io
import json
import os
import sys
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------

class DataRecord:
    """单条结构化记录（有序字典封装）"""
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data = OrderedDict(data or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def keys(self) -> List[str]:
        return list(self._data.keys())

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __repr__(self) -> str:
        return f"DataRecord({self._data})"


class DataTable:
    """结构化数据表（记录列表 + 字段顺序）"""
    def __init__(self, records: Optional[List[DataRecord]] = None):
        self.records: List[DataRecord] = records or []
        self._field_order: List[str] = self._infer_fields()

    def _infer_fields(self) -> List[str]:
        """从记录中推断字段顺序（保持首次出现顺序）"""
        fields: List[str] = []
        for rec in self.records:
            for key in rec.keys():
                if key not in fields:
                    fields.append(key)
        return fields

    def add_record(self, record: DataRecord) -> None:
        self.records.append(record)
        # 更新字段顺序
        for key in record.keys():
            if key not in self._field_order:
                self._field_order.append(key)

    def get_field_order(self) -> List[str]:
        return list(self._field_order)

    def set_field_order(self, fields: List[str]) -> None:
        """显式设置字段顺序（用于自定义输出）"""
        self._field_order = list(fields)

    def to_list_of_dicts(self) -> List[Dict[str, Any]]:
        return [rec.to_dict() for rec in self.records]

    def __len__(self) -> int:
        return len(self.records)

    def __repr__(self) -> str:
        return f"DataTable({len(self.records)} records, fields={self._field_order})"


# ---------------------------------------------------------------
# 数据解析（输入）
# ---------------------------------------------------------------

def parse_csv_text(text: str) -> DataTable:
    """解析 CSV 文本为 DataTable"""
    try:
        reader = csv.DictReader(io.StringIO(text))
        table = DataTable()
        for row in reader:
            # 清理空值
            clean_row = {k: (v if v != '' else None) for k, v in row.items()}
            table.add_record(DataRecord(clean_row))
        return table
    except Exception as exc:
        raise DataParseError(f"CSV解析失败: {exc}") from exc


def parse_json_text(text: str) -> DataTable:
    """解析 JSON 文本为 DataTable（支持对象数组或单对象）"""
    try:
        data = json.loads(text)
    except Exception as exc:
        raise DataParseError(f"JSON解析失败: {exc}") from exc

    table = DataTable()

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                table.add_record(DataRecord(item))
            else:
                # 非字典元素包装为单字段记录
                table.add_record(DataRecord({"value": item}))
    elif isinstance(data, dict):
        # 单对象：如果是嵌套结构则展开，否则作为单条记录
        table.add_record(DataRecord(data))
    else:
        # 标量值
        table.add_record(DataRecord({"value": data}))

    return table


def parse_txt_lines(text: str) -> DataTable:
    """解析 TXT 文本（每行一条记录，自动检测分隔符）"""
    table = DataTable()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return table

    # 尝试检测分隔符（逗号、制表符、竖线）
    delimiter = None
    for candidate in [',', '\t', '|']:
        if candidate in lines[0]:
            delimiter = candidate
            break

    if delimiter:
        # 类CSV处理
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            for row in reader:
                clean_row = {k: (v if v != '' else None) for k, v in row.items()}
                table.add_record(DataRecord(clean_row))
            return table
        except Exception:
            pass  # 降级为逐行处理

    # 逐行处理：单字段记录
    for line in lines:
        table.add_record(DataRecord({"line": line}))

    return table


def parse_text(text: str, fmt: str) -> DataTable:
    """根据格式解析文本"""
    fmt_lower = fmt.lower()
    if fmt_lower == 'csv':
        return parse_csv_text(text)
    elif fmt_lower == 'json':
        return parse_json_text(text)
    elif fmt_lower in ('txt', 'text', 'log'):
        return parse_txt_lines(text)
    else:
        raise UnsupportedFormatError(f"不支持的输入格式: {fmt}")


# ---------------------------------------------------------------
# 数据处理（清洗/转换）
# ---------------------------------------------------------------

def clean_table(table: DataTable, remove_empty: bool = True, deduplicate: bool = True) -> DataTable:
    """数据清洗：去除空行、去重"""
    result = DataTable()

    seen: List[Tuple] = []

    for rec in table.records:
        # 去除空行（所有字段均为None或空）
        if remove_empty:
            values = [v for v in rec.to_dict().values() if v is not None and v != '']
            if not values:
                continue

        # 去重（基于字段值元组）
        if deduplicate:
            key_tuple = tuple(sorted(rec.to_dict().items()))
            if key_tuple in seen:
                continue
            seen.append(key_tuple)

        result.add_record(rec)

    return result


def convert_types(table: DataTable, conversions: Dict[str, str]) -> DataTable:
    """类型转换：conversions = {字段名: 目标类型}，目标类型: int/float/str/bool"""
    result = DataTable()

    type_map: Dict[str, Callable] = {
        'int': int,
        'float': float,
        'str': str,
        'bool': lambda x: str(x).lower() in ('true', '1', 'yes', 'y'),
    }

    for rec in table.records:
        new_rec = DataRecord()
        for key, value in rec.to_dict().items():
            if key in conversions:
                target_type = conversions[key].lower()
                if target_type not in type_map:
                    raise TypeConversionError(f"不支持的转换类型: {target_type}")
                try:
                    if value is None or value == '':
                        new_rec.set(key, None)
                    else:
                        new_rec.set(key, type_map[target_type](value))
                except (ValueError, TypeError) as exc:
                    raise TypeConversionError(f"字段[{key}]转换为{target_type}失败: {value}") from exc
            else:
                new_rec.set(key, value)
        result.add_record(new_rec)

    return result


def select_fields(table: DataTable, fields: List[str]) -> DataTable:
    """选择指定字段（保留字段顺序）"""
    result = DataTable()

    for rec in table.records:
        new_rec = DataRecord()
        for field in fields:
            if field in rec.keys():
                new_rec.set(field, rec.get(field))
            else:
                new_rec.set(field, None)  # 缺失字段置空
        result.add_record(new_rec)

    result.set_field_order(fields)
    return result


def sort_records(table: DataTable, sort_key: str, reverse: bool = False) -> DataTable:
    """按指定字段排序"""
    result = DataTable()

    # 提取排序键值
    def sort_func(rec: DataRecord) -> Any:
        return rec.get(sort_key)

    try:
        sorted_records = sorted(table.records, key=sort_func, reverse=reverse)
    except TypeError as exc:
        raise SortError(f"排序失败（字段类型不一致?）: {exc}") from exc

    for rec in sorted_records:
        result.add_record(rec)

    return result


# ---------------------------------------------------------------
# 数据输出（序列化）
# ---------------------------------------------------------------

def to_json(table: DataTable, pretty: bool = True) -> str:
    """输出为 JSON 字符串"""
    data = table.to_list_of_dicts()
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False)


def to_csv(table: DataTable) -> str:
    """输出为 CSV 字符串"""
    output = io.StringIO()
    fields = table.get_field_order()

    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for rec in table.records:
        # 缺失字段补空
        row = {f: rec.get(f, '') for f in fields}
        writer.writerow(row)

    return output.getvalue()


def to_txt(table: DataTable, separator: str = ' | ') -> str:
    """输出为 TXT 文本（每行一条记录，字段用分隔符连接）"""
    lines = []
    fields = table.get_field_order()

    # 表头
    lines.append(separator.join(fields))

    for rec in table.records:
        values = [str(rec.get(f, '')) for f in fields]
        lines.append(separator.join(values))

    return '\n'.join(lines)


def serialize_table(table: DataTable, fmt: str) -> str:
    """按指定格式序列化输出"""
    fmt_lower = fmt.lower()
    if fmt_lower == 'json':
        return to_json(table)
    elif fmt_lower == 'csv':
        return to_csv(table)
    elif fmt_lower in ('txt', 'text'):
        return to_txt(table)
    else:
        raise UnsupportedFormatError(f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------

def process_file(filepath: str, input_format: Optional[str] = None) -> DataTable:
    """处理单个文件"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as exc:
        raise FileReadError(f"文件读取失败: {exc}") from exc

    # 自动检测格式（根据扩展名）
    if input_format is None:
        ext = os.path.splitext(filepath)[1].lower().lstrip('.')
        if ext in ('csv',):
            input_format = 'csv'
        elif ext in ('json',):
            input_format = 'json'
        elif ext in ('txt', 'log', 'text'):
            input_format = 'txt'
        else:
            raise UnsupportedFormatError(f"无法自动识别文件格式: {filepath}")

    return parse_text(text, input_format)


def process_files(filepaths: List[str], input_format: Optional[str] = None) -> DataTable:
    """批量处理多个文件，合并结果集"""
    result = DataTable()

    for filepath in filepaths:
        table = process_file(filepath, input_format)
        for rec in table.records:
            # 添加来源标记
            rec.set('_source', os.path.basename(filepath))
            result.add_record(rec)

    return result


# ---------------------------------------------------------------
# 主处理管线
# ---------------------------------------------------------------

def process_pipeline(
    input_data: str,
    input_format: str = 'auto',
    operations: Optional[List[Dict[str, Any]]] = None,
) -> DataTable:
    """
    处理管线：解析 -> 清洗 -> 转换 -> 选择 -> 排序
    operations 示例:
        [{"op": "clean", "remove_empty": True, "deduplicate": True},
         {"op": "convert", "conversions": {"age": "int"}},
         {"op": "select", "fields": ["name", "age"]},
         {"op": "sort", "key": "age", "reverse": True}]
    """
    # 1. 解析
    if input_format == 'auto':
        # 尝试自动检测
        stripped = input_data.lstrip()
        if stripped.startswith('{') or stripped.startswith('['):
            input_format = 'json'
        elif ',' in input_data.split('\n')[0]:
            input_format = 'csv'
        else:
            input_format = 'txt'

    table = parse_text(input_data, input_format)

    # 2. 执行操作
    if operations:
        for op in operations:
            op_type = op.get('op', '').lower()

            if op_type == 'clean':
                table = clean_table(
                    table,
                    remove_empty=op.get('remove_empty', True),
                    deduplicate=op.get('deduplicate', True),
                )
            elif op_type == 'convert':
                table = convert_types(table, op.get('conversions', {}))
            elif op_type == 'select':
                table = select_fields(table, op.get('fields', []))
            elif op_type == 'sort':
                table = sort_records(
                    table,
                    sort_key=op.get('key', ''),
                    reverse=op.get('reverse', False),
                )
            else:
                raise InvalidArgumentError(f"未知操作: {op_type}")

    return table


# ---------------------------------------------------------------
# 错误类定义
# ---------------------------------------------------------------

class PrototypeError(Exception):
    """基础异常类"""
    code = 'E000'

    def __init__(self, message: str):
        super().__init__(f"[{self.code}] {message}")


class InvalidArgumentError(PrototypeError):
    code = 'E001'


class FileNotFoundError(PrototypeError):
    code = 'E002'


class FileReadError(PrototypeError):
    code = 'E003'


class DataParseError(PrototypeError):
    code = 'E004'


class FieldSelectError(PrototypeError):
    code = 'E005'


class TypeConversionError(PrototypeError):
    code = 'E006'


class SortError(PrototypeError):
    code = 'E007'


class OutputWriteError(PrototypeError):
    code = 'E008'


class InternalLogicError(PrototypeError):
    code = 'E009'


class UnsupportedFormatError(PrototypeError):
    code = 'E010'


# ---------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------

def run_selftest() -> int:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("=" * 60)
    print("prototype 自检开始 (离线模式)")
    print("=" * 60)

    # ---- 测试1: CSV 解析 ----
    print("\n[测试1] CSV 解析")
    csv_text = "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\nAlice,30,Beijing\n"
    table = parse_csv_text(csv_text)
    assert len(table) == 3, f"CSV应解析出3条记录，实际{len(table)}"
    assert 'name' in table.get_field_order(), "字段name缺失"
    assert 'age' in table.get_field_order(), "字段age缺失"
    assert 'city' in table.get_field_order(), "字段city缺失"
    # 宽松断言：记录数 > 0 且包含关键字段
    assert len(table) > 0, "记录数应为正数"
    print(f"  ✓ CSV解析成功，{len(table)}条记录，字段: {table.get_field_order()}")

    # ---- 测试2: JSON 解析 ----
    print("\n[测试2] JSON 解析")
    json_text = '[{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]'
    table = parse_json_text(json_text)
    assert len(table) == 2, f"JSON应解析出2条记录，实际{len(table)}"
    assert len(table) > 0, "记录数应为正数"
    print(f"  ✓ JSON解析成功，{len(table)}条记录")

    # ---- 测试3: 数据清洗（去重） ----
    print("\n[测试3] 数据清洗（去重）")
    csv_text = "a,b\n1,2\n1,2\n3,4\n"
    table = parse_csv_text(csv_text)
    cleaned = clean_table(table, remove_empty=True, deduplicate=True)
    # 原始3条，去重后应为2条（1,2重复）
    assert len(cleaned) == 2, f"去重后应剩2条，实际{len(cleaned)}"
    # 宽松断言：去重后记录数 <= 原始记录数
    assert len(cleaned) <= len(table), "去重后记录数应不超过原始记录数"
    print(f"  ✓ 去重成功，{len(table)}条 -> {len(cleaned)}条")

    # ---- 测试4: 类型转换 ----
    print("\n[测试4] 类型转换")
    csv_text = "num,text\n123,hello\n456,world\n"
    table = parse_csv_text(csv_text)
    converted = convert_types(table, {"num": "int"})
    first_val = converted.records[0].get('num')
    # 宽松断言：转换后应为数值类型（int或float）
    assert isinstance(first_val, (int, float)), f"转换后应为数值类型，实际{type(first_val)}"
    assert first_val > 0, "数值应大于0"
    print(f"  ✓ 类型转换成功，'123' -> {first_val} ({type(first_val).__name__})")

    # ---- 测试5: 字段选择 ----
    print("\n[测试5] 字段选择")
    csv_text = "a,b,c\n1,2,3\n4,5,6\n"
    table = parse_csv_text(csv_text)
    selected = select_fields(table, ["a", "c"])
    assert len(selected.records[0].keys()) == 2, "应只保留2个字段"
    # 宽松断言：字段数 > 0 且不超过原始字段数
    assert len(selected.get_field_order()) > 0, "字段数应为正数"
    assert len(selected.get_field_order()) <= len(table.get_field_order()), "字段数不应超过原始"
    print(f"  ✓ 字段选择成功，保留字段: {selected.get_field_order()}")

    # ---- 测试6: 排序 ----
    print("\n[测试6] 排序")
    csv_text = "name,score\nAlice,85\nBob,95\nCharlie,75\n"
    table = parse_csv_text(csv_text)
    sorted_table = sort_records(table, "score", reverse=True)
    scores = [int(rec.get('score')) for rec in sorted_table.records]
    # 宽松断言：排序后第一项分数应大于最后一项
    assert scores[0] >= scores[-1], "降序排序后首项应大于末项"
    assert scores[0] == 95, "最高分应为95"
    print(f"  ✓ 排序成功，分数序列: {scores}")

    # ---- 测试7: 完整管线 ----
    print("\n[测试7] 完整管线（清洗+转换+选择+排序）")
    csv_text = "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\nAlice,30,Beijing\nCharlie,35,Guangzhou\n"
    operations = [
        {"op": "clean", "remove_empty": True, "deduplicate": True},
        {"op": "convert", "conversions": {"age": "int"}},
        {"op": "select", "fields": ["name", "age"]},
        {"op": "sort", "key": "age", "reverse": True},
    ]
    result = process_pipeline(csv_text, "csv", operations)
    # 去重后应剩3条（Alice重复）
    assert len(result) == 3, f"管线处理后应剩3条，实际{len(result)}"
    # 宽松断言
    assert len(result) > 0, "结果记录数应为正数"
    ages = [int(rec.get('age')) for rec in result.records]
    assert ages[0] >= ages[-1], "按年龄降序排序"
    print(f"  ✓ 管线处理成功，{len(result)}条记录，年龄序列: {ages}")

    # ---- 测试8: 输出序列化 ----
    print("\n[测试8] 输出序列化")
    csv_text = "a,b\n1,2\n3,4\n"
    table = parse_csv_text(csv_text)

    json_out = to_json(table)
    assert json_out.startswith('['), "JSON输出应以[开头"
    assert len(json_out) > 0, "JSON输出不应为空"
    print(f"  ✓ JSON输出成功，长度{len(json_out)}字符")

    csv_out = to_csv(table)
    assert 'a' in csv_out and 'b' in csv_out, "CSV输出应包含字段名"
    assert len(csv_out) > 0, "CSV输出不应为空"
    print(f"  ✓ CSV输出成功，长度{len(csv_out)}字符")

    txt_out = to_txt(table)
    assert 'a' in txt_out, "TXT输出应包含字段名"
    assert len(txt_out) > 0, "TXT输出不应为空"
    print(f"  ✓ TXT输出成功，长度{len(txt_out)}字符")

    # ---- 测试9: 批量文件处理模拟 ----
    print("\n[测试9] 批量文件处理模拟")
    # 使用临时文件（不依赖外部环境，用系统临时目录）
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "data1.csv")
        file2 = os.path.join(tmpdir, "data2.csv")
        with open(file1, 'w', encoding='utf-8') as f:
            f.write("x,y\n1,10\n2,20\n")
        with open(file2, 'w', encoding='utf-8') as f:
            f.write("x,y\n3,30\n4,40\n")

        table = process_files([file1, file2], input_format='csv')
        assert len(table) == 4, f"批量处理应得4条记录，实际{len(table)}"
        assert len(table) > 0, "批量处理结果应为正数"
        print(f"  ✓ 批量处理成功，合并{len(table)}条记录")

    # ---- 测试10: 错误处理 ----
    print("\n[测试10] 错误处理")
    try:
        parse_text("not valid json {", "json")
        assert False, "应抛出解析错误"
    except DataParseError as e:
        assert e.code == 'E004', f"错误码应为E004，实际{e.code}"
        print(f"  ✓ 错误处理正常: {e}")

    # 汇总
    print("\n" + "=" * 60)
    print("全部自检通过 ✓")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="数据原型转换器 - 结构化数据处理工具",
        epilog="示例: python main.py input.csv --input-format csv --output-format json --select name,age --sort age --reverse",
    )
    parser.add_argument("input", nargs="*", help="输入文件路径（支持多个，批量处理）")
    parser.add_argument("--input-format", choices=["csv", "json", "txt", "auto"], default="auto",
                        help="输入格式（默认auto自动检测）")
    parser.add_argument("--output-format", choices=["json", "csv", "txt"], default="json",
                        help="输出格式（默认json）")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到stdout）")
    parser.add_argument("--select", help="选择字段，逗号分隔")
    parser.add_argument("--sort", help="排序字段")
    parser.add_argument("--reverse", action="store_true", help="降序排序")
    parser.add_argument("--convert", help="类型转换，格式: 字段:类型,字段:类型 (如 age:int)")
    parser.add_argument("--no-clean", action="store_true", help="跳过数据清洗")
    parser.add_argument("--no-dedup", action="store_true", help="跳过去重")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input:
        print("错误: 请指定输入文件或使用 --selftest", file=sys.stderr)
        print(f"[{InvalidArgumentError.code}] 参数错误", file=sys.stderr)
        return 1

    try:
        # 批量处理
        table = process_files(args.input, args.input_format)

        # 构建操作管线
        operations = []

        if not args.no_clean:
            operations.append({"op": "clean", "remove_empty": True, "deduplicate": not args.no_dedup})

        if args.convert:
            conversions = {}
            for item in args.convert.split(','):
                if ':' in item:
                    field, typ = item.split(':', 1)
                    conversions[field.strip()] = typ.strip()
            if conversions:
                operations.append({"op": "convert", "conversions": conversions})

        if args.select:
            fields = [f.strip() for f in args.select.split(',') if f.strip()]
            operations.append({"op": "select", "fields": fields})

        if args.sort:
            operations.append({"op": "sort", "key": args.sort, "reverse": args.reverse})

        # 执行操作
        if operations:
            # 需要重新解析文本（因为process_files已解析过）
            # 简化：直接对已有table执行操作
            for op in operations:
                op_type = op.get('op', '')
                if op_type == 'clean':
                    table = clean_table(table, remove_empty=op.get('remove_empty', True),
                                        deduplicate=op.get('deduplicate', True))
                elif op_type == 'convert':
                    table = convert_types(table, op.get('conversions', {}))
                elif op_type == 'select':
                    table = select_fields(table, op.get('fields', []))
                elif op_type == 'sort':
                    table = sort_records(table, sort_key=op.get('key', ''),
                                         reverse=op.get('reverse', False))

        # 序列化输出
        output_text = serialize_table(table, args.output_format)

        # 输出
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_text)
            except Exception as exc:
                print(f"[{OutputWriteError.code}] 输出写入失败: {exc}", file=sys.stderr)
                return 1
        else:
            print(output_text)

        return 0

    except PrototypeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[{InternalLogicError.code}] 未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
