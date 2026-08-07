#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schemaz - SQL查询技能独立实现

一个纯函数式的轻量级库，用于定义代数数据类型的类型安全模式，
提供免费的生成器、SQL查询构建等能力。

本脚本为 clean-room 重写实现，仅依据功能规格独立开发。

用法:
    python scripts/main.py --selftest    # 运行内置自检
    python scripts/main.py --help        # 显示帮助
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部错误：文件读写失败",
    "E007": "内部错误：JSON 解析失败",
    "E008": "内部错误：不支持的字段类型",
    "E009": "内部错误：SQL 语法生成失败",
    "E010": "内部错误：未知错误",
}


class SchemazError(Exception):
    """schemaz 自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
@dataclass
class Field:
    """字段定义。"""
    name: str
    type: str  # 类型: string, int, float, bool, date, datetime
    nullable: bool = True
    default: Any = None
    description: str = ""


@dataclass
class Schema:
    """模式定义（代数数据类型）。"""
    name: str
    fields: List[Field] = field(default_factory=list)
    description: str = ""

    def add_field(self, field: Field) -> "Schema":
        """添加字段。"""
        self.fields.append(field)
        return self

    def get_field(self, name: str) -> Optional[Field]:
        """按名称获取字段。"""
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "name": self.name,
            "description": self.description,
            "fields": [
                {
                    "name": f.name,
                    "type": f.type,
                    "nullable": f.nullable,
                    "default": f.default,
                    "description": f.description,
                }
                for f in self.fields
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schema":
        """从字典创建。"""
        schema = cls(name=data.get("name", ""), description=data.get("description", ""))
        for fd in data.get("fields", []):
            schema.add_field(
                Field(
                    name=fd.get("name", ""),
                    type=fd.get("type", "string"),
                    nullable=fd.get("nullable", True),
                    default=fd.get("default"),
                    description=fd.get("description", ""),
                )
            )
        return schema


# ============================================================
# 类型校验与转换
# ============================================================
class TypeValidator:
    """字段类型校验器。"""

    SUPPORTED_TYPES = {"string", "int", "float", "bool", "date", "datetime"}

    @staticmethod
    def validate_type(type_name: str) -> bool:
        """检查类型是否受支持。"""
        return type_name in TypeValidator.SUPPORTED_TYPES

    @staticmethod
    def convert(value: Any, type_name: str) -> Any:
        """将值转换为指定类型，失败时抛出异常。"""
        if value is None:
            return None

        try:
            if type_name == "string":
                return str(value)
            elif type_name == "int":
                return int(value)
            elif type_name == "float":
                return float(value)
            elif type_name == "bool":
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "y")
                return bool(value)
            elif type_name == "date":
                if isinstance(value, datetime):
                    return value.date().isoformat()
                return str(value)[:10]  # 取前10位作为日期
            elif type_name == "datetime":
                if isinstance(value, datetime):
                    return value.isoformat()
                return str(value)
            else:
                raise SchemazError("E008", f"不支持的字段类型: {type_name}")
        except (ValueError, TypeError) as e:
            raise SchemazError("E003", f"类型转换失败: {value} -> {type_name}: {e}")


# ============================================================
# 数据解析与结构化
# ============================================================
class DataParser:
    """输入解析器。"""

    @staticmethod
    def parse_json(text: str) -> Dict[str, Any]:
        """解析 JSON 输入。"""
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise SchemazError("E007", f"JSON 解析失败: {e}")

    @staticmethod
    def parse_csv(text: str) -> List[Dict[str, Any]]:
        """解析简单 CSV 输入（第一行为表头）。"""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if len(lines) < 2:
            raise SchemazError("E001", "CSV 数据至少需要表头和一行数据")

        headers = [h.strip() for h in lines[0].split(",")]
        records = []
        for line in lines[1:]:
            values = [v.strip() for v in line.split(",")]
            if len(values) != len(headers):
                raise SchemazError("E003", f"CSV 列数不匹配: 期望 {len(headers)} 列，实际 {len(values)} 列")
            records.append(dict(zip(headers, values)))
        return records

    @staticmethod
    def parse_key_value(text: str) -> Dict[str, Any]:
        """解析 key=value 格式（每行一个）。"""
        result = {}
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if "=" not in line:
                raise SchemazError("E003", f"格式错误（应为 key=value）: {line}")
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
        return result

    @staticmethod
    def detect_and_parse(text: str) -> Tuple[Dict[str, Any], str]:
        """自动检测输入格式并解析。返回 (数据, 格式类型)。"""
        text = text.strip()
        if not text:
            raise SchemazError("E001")

        # 尝试 JSON
        if text.startswith("{") or text.startswith("["):
            data = DataParser.parse_json(text)
            return data, "json"

        # 尝试 CSV（包含逗号且有多行）
        if "," in text and "\n" in text:
            records = DataParser.parse_csv(text)
            if records:
                return {"records": records}, "csv"

        # 尝试 key=value
        if "=" in text:
            data = DataParser.parse_key_value(text)
            return data, "keyvalue"

        # 默认当作纯文本
        return {"text": text}, "text"


# ============================================================
# 数据处理与转换引擎
# ============================================================
class DataProcessor:
    """核心数据处理引擎。"""

    def __init__(self, schema: Optional[Schema] = None):
        self.schema = schema

    def process(self, data: Dict[str, Any], input_format: str = "") -> Dict[str, Any]:
        """处理数据，返回结构化结果。"""
        # 检查输入是否为空
        if not data:
            raise SchemazError("E001")

        # 检查关键信息
        if self.schema is None:
            # 无模式时，尝试自动识别
            return self._auto_process(data, input_format)

        # 有模式时，按模式校验和转换
        return self._schema_process(data)

    def _auto_process(self, data: Dict[str, Any], input_format: str) -> Dict[str, Any]:
        """无模式时的自动处理。"""
        result = {
            "input_format": input_format or "unknown",
            "processed_at": datetime.now().isoformat(),
            "confidence": 0.9,  # 自动处理的置信度
            "data": data,
            "warnings": [],
        }

        # 检查是否有记录数组
        if "records" in data and isinstance(data["records"], list):
            records = data["records"]
            if not records:
                raise SchemazError("E001", "记录列表为空")
            # 检查字段一致性
            first_keys = set(records[0].keys())
            for i, rec in enumerate(records[1:], 1):
                if set(rec.keys()) != first_keys:
                    result["confidence"] = 0.85
                    result["warnings"].append(f"记录 {i} 的字段与其他记录不一致")

        return result

    def _schema_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """按模式处理数据。"""
        schema = self.schema
        assert schema is not None

        # 检查必填字段
        missing = []
        for field in schema.fields:
            if not field.nullable and field.default is None:
                if field.name not in data or data[field.name] is None:
                    missing.append(field.name)

        if missing:
            raise SchemazError("E002", f"缺少必填字段: {', '.join(missing)}")

        # 转换字段
        converted = {}
        for field in schema.fields:
            if field.name in data:
                converted[field.name] = TypeValidator.convert(data[field.name], field.type)
            elif field.default is not None:
                converted[field.name] = field.default
            elif field.nullable:
                converted[field.name] = None
            else:
                raise SchemazError("E002", f"缺少字段: {field.name}")

        return {
            "schema": schema.name,
            "data": converted,
            "confidence": 0.95,  # 模式匹配的置信度较高
            "processed_at": datetime.now().isoformat(),
        }


# ============================================================
# SQL 查询生成器
# ============================================================
class SQLGenerator:
    """SQL 查询生成器。"""

    TYPE_MAP = {
        "string": "TEXT",
        "int": "INTEGER",
        "float": "REAL",
        "bool": "BOOLEAN",
        "date": "DATE",
        "datetime": "TIMESTAMP",
    }

    @staticmethod
    def generate_create_table(schema: Schema, table_name: Optional[str] = None) -> str:
        """生成 CREATE TABLE 语句。"""
        table = table_name or schema.name
        if not table:
            raise SchemazError("E009", "表名不能为空")

        if not schema.fields:
            raise SchemazError("E009", "模式中没有字段")

        columns = []
        for field in schema.fields:
            if field.type not in SQLGenerator.TYPE_MAP:
                raise SchemazError("E008", f"不支持的字段类型: {field.type}")
            col_type = SQLGenerator.TYPE_MAP[field.type]
            nullable = "" if field.nullable else " NOT NULL"
            default = ""
            if field.default is not None:
                if field.type == "string":
                    default = f" DEFAULT '{field.default}'"
                else:
                    default = f" DEFAULT {field.default}"
            columns.append(f"    {field.name} {col_type}{nullable}{default}")

        return f"CREATE TABLE {table} (\n" + ",\n".join(columns) + "\n);"

    @staticmethod
    def generate_select(schema: Schema, table_name: str, where: Optional[str] = None) -> str:
        """生成 SELECT 语句。"""
        if not schema.fields:
            raise SchemazError("E009", "模式中没有字段")
        fields = ", ".join(f.name for f in schema.fields)
        query = f"SELECT {fields} FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        return query + ";"

    @staticmethod
    def generate_insert(schema: Schema, table_name: str, data: Dict[str, Any]) -> str:
        """生成 INSERT 语句。"""
        if not schema.fields:
            raise SchemazError("E009", "模式中没有字段")

        columns = []
        values = []
        for field in schema.fields:
            if field.name in data:
                columns.append(field.name)
                val = data[field.name]
                if val is None:
                    values.append("NULL")
                elif field.type == "string":
                    values.append(f"'{val}'")
                elif field.type == "bool":
                    values.append("TRUE" if val else "FALSE")
                else:
                    values.append(str(val))

        if not columns:
            raise SchemazError("E009", "没有可插入的字段")

        cols_str = ", ".join(columns)
        vals_str = ", ".join(values)
        return f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str});"


# ============================================================
# 主应用类
# ============================================================
class SchemazApp:
    """schemaz 主应用。"""

    def __init__(self):
        self.processor = DataProcessor()
        self.sql_gen = SQLGenerator()

    def run(self, input_text: str, schema_spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """主流程：解析 → 处理 → 输出。"""
        # Step 1: 解析输入
        data, fmt = DataParser.detect_and_parse(input_text)

        # Step 2: 构建模式（如果提供）
        if schema_spec:
            schema = Schema.from_dict(schema_spec)
            self.processor.schema = schema

        # Step 3: 处理数据
        result = self.processor.process(data, fmt)

        # Step 4: 补充置信度标注
        confidence = result.get("confidence", 0.9)
        if confidence >= 0.9:
            result["status"] = "直接输出"
        elif confidence >= 0.85:
            result["status"] = "建议复核"
        else:
            result["status"] = "[需核实]"

        return result


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """内置自检：使用硬编码样例数据离线验证核心逻辑。

    断言使用宽松阈值（大小比较/区间判断），确保稳健。
    """
    print("=" * 60)
    print("schemaz 自检开始")
    print("=" * 60)

    # ---------- 测试 1: 数据解析（JSON） ----------
    print("\n[测试 1] JSON 解析")
    json_input = '{"name": "张三", "age": 30, "active": true}'
    data, fmt = DataParser.detect_and_parse(json_input)
    assert fmt == "json", f"期望 json，实际 {fmt}"
    assert data.get("name") == "张三", "姓名解析失败"
    assert data.get("age") == 30, "年龄解析失败"
    print("  ✓ JSON 解析通过")

    # ---------- 测试 2: 数据解析（CSV） ----------
    print("\n[测试 2] CSV 解析")
    csv_input = "id,name,score\n1,Alice,95.5\n2,Bob,87.0\n"
    data, fmt = DataParser.detect_and_parse(csv_input)
    assert fmt == "csv", f"期望 csv，实际 {fmt}"
    records = data.get("records", [])
    assert len(records) == 2, f"期望 2 条记录，实际 {len(records)}"
    assert records[0]["name"] == "Alice", "CSV 第一行解析失败"
    print("  ✓ CSV 解析通过")

    # ---------- 测试 3: 数据解析（key=value） ----------
    print("\n[测试 3] key=value 解析")
    kv_input = "host=localhost\nport=8080\n"
    data, fmt = DataParser.detect_and_parse(kv_input)
    assert fmt == "keyvalue", f"期望 keyvalue，实际 {fmt}"
    assert data.get("host") == "localhost", "host 解析失败"
    assert data.get("port") == "8080", "port 解析失败"
    print("  ✓ key=value 解析通过")

    # ---------- 测试 4: 类型转换 ----------
    print("\n[测试 4] 类型转换")
    assert TypeValidator.convert("42", "int") == 42, "字符串转 int 失败"
    assert TypeValidator.convert("3.14", "float") == 3.14, "字符串转 float 失败"
    assert TypeValidator.convert("true", "bool") is True, "字符串转 bool 失败"
    assert TypeValidator.convert(123, "string") == "123", "int 转 string 失败"
    print("  ✓ 类型转换通过")

    # ---------- 测试 5: 模式处理 ----------
    print("\n[测试 5] 模式处理")
    schema_spec = {
        "name": "person",
        "fields": [
            {"name": "name", "type": "string", "nullable": False},
            {"name": "age", "type": "int", "nullable": False},
            {"name": "email", "type": "string", "nullable": True},
        ],
    }
    schema = Schema.from_dict(schema_spec)
    processor = DataProcessor(schema)
    result = processor.process({"name": "李四", "age": 25})
    assert result["schema"] == "person", "模式名称错误"
    assert result["data"]["name"] == "李四", "数据转换失败"
    assert result["data"]["age"] == 25, "年龄转换失败"
    assert result["data"]["email"] is None, "可空字段应为 None"
    assert result["confidence"] > 0.9, "置信度应大于 0.9"
    print("  ✓ 模式处理通过")

    # ---------- 测试 6: 缺少必填字段 ----------
    print("\n[测试 6] 缺少必填字段")
    try:
        processor.process({"name": "王五"})  # 缺少 age
        assert False, "应该抛出 E002 错误"
    except SchemazError as e:
        assert e.code == "E002", f"期望 E002，实际 {e.code}"
        print("  ✓ 缺少字段检测通过")

    # ---------- 测试 7: SQL 生成 ----------
    print("\n[测试 7] SQL 生成")
    sql = SQLGenerator.generate_create_table(schema)
    assert "CREATE TABLE person" in sql, "CREATE TABLE 语句错误"
    assert "name TEXT NOT NULL" in sql, "name 字段定义错误"
    assert "age INTEGER NOT NULL" in sql, "age 字段定义错误"

    sql_insert = SQLGenerator.generate_insert(schema, "person", {"name": "赵六", "age": 30})
    assert "INSERT INTO person" in sql_insert, "INSERT 语句错误"
    assert "'赵六'" in sql_insert, "INSERT 值错误"

    sql_select = SQLGenerator.generate_select(schema, "person", "age > 18")
    assert "SELECT name, age, email FROM person WHERE age > 18;" == sql_select, "SELECT 语句错误"
    print("  ✓ SQL 生成通过")

    # ---------- 测试 8: 错误码体系 ----------
    print("\n[测试 8] 错误码体系")
    assert "E001" in ERROR_CODES, "E001 未定义"
    assert "E002" in ERROR_CODES, "E002 未定义"
    assert "E010" in ERROR_CODES, "E010 未定义"
    try:
        raise SchemazError("E001")
    except SchemazError as e:
        assert str(e).startswith("[E001]"), "错误码格式化失败"
        print("  ✓ 错误码体系通过")

    # ---------- 测试 9: 空输入处理 ----------
    print("\n[测试 9] 空输入处理")
    try:
        DataParser.detect_and_parse("   ")
        assert False, "应该抛出 E001 错误"
    except SchemazError as e:
        assert e.code == "E001", f"期望 E001，实际 {e.code}"
        print("  ✓ 空输入检测通过")

    # ---------- 测试 10: 文件读写 ----------
    print("\n[测试 10] 文件读写")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 写入测试
        test_file = os.path.join(tmpdir, "test.json")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write('{"test": true}')
        # 读取测试
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "test" in content, "文件读写失败"
        print("  ✓ 文件读写通过")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="schemaz - SQL查询技能（clean-room 独立实现）",
        epilog="示例: python scripts/main.py --input '{\"name\":\"test\"}' --schema schema.json",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本（JSON/CSV/key=value）",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="输入文件路径",
    )
    parser.add_argument(
        "--schema",
        type=str,
        help="模式 JSON 文件路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "--generate-sql",
        type=str,
        metavar="TABLE_NAME",
        help="生成 CREATE TABLE SQL 语句",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    if not args.input and not args.input_file:
        parser.print_help()
        return 0

    try:
        # 读取输入
        if args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    input_text = f.read()
            except OSError as e:
                print(f"[E006] 文件读取失败: {e}", file=sys.stderr)
                return 1
        else:
            input_text = args.input or ""

        # 读取模式（可选）
        schema_spec = None
        if args.schema:
            try:
                with open(args.schema, "r", encoding="utf-8") as f:
                    schema_spec = json.load(f)
            except OSError as e:
                print(f"[E006] 模式文件读取失败: {e}", file=sys.stderr)
                return 1
            except json.JSONDecodeError as e:
                print(f"[E007] 模式 JSON 解析失败: {e}", file=sys.stderr)
                return 1

        # 处理
        app = SchemazApp()
        result = app.run(input_text, schema_spec)

        # 生成 SQL（可选）
        if args.generate_sql:
            schema = Schema.from_dict(schema_spec) if schema_spec else None
            if schema:
                sql = SQLGenerator.generate_create_table(schema, args.generate_sql)
                result["sql"] = sql
            else:
                print("[E002] 生成 SQL 需要提供 --schema", file=sys.stderr)
                return 1

        # 输出
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            except OSError as e:
                print(f"[E006] 输出文件写入失败: {e}", file=sys.stderr)
                return 1
        else:
            print(output)

        return 0

    except SchemazError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
