#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - SQL查询技能核心实现

本脚本根据功能规格独立实现（clean-room），不依赖任何既有代码。
提供 SQL 查询构建、ORM/Factory 生成辅助、以及离线自检功能。
"""

import argparse
import json
import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码对应的标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{\"table\": \"users\", \"fields\": [\"id\", \"name\"]}",
    "E004": "这超出了本工具的能力范围，建议：仅处理与 SQL 查询构建、ORM/Factory 生成相关的内容",
    "E005": "结果无法确定，建议：补充更完整的字段定义或表结构信息",
    "E006": "内部处理错误，请检查输入数据是否符合规范",
    "E007": "不支持的数据库类型，支持：postgresql、mysql、sqlite",
    "E008": "字段定义不完整，每个字段必须包含 name 和 type",
    "E009": "表名不能为空，且只能包含字母、数字和下划线",
    "E010": "输出格式不支持，支持：json、text",
}

# 支持的数据库类型
SUPPORTED_DATABASES: List[str] = ["postgresql", "mysql", "sqlite"]

# Go 类型映射
GO_TYPE_MAP: Dict[str, str] = {
    "int": "int",
    "integer": "int",
    "bigint": "int64",
    "smallint": "int16",
    "serial": "int",
    "bigserial": "int64",
    "varchar": "string",
    "text": "string",
    "char": "string",
    "boolean": "bool",
    "bool": "bool",
    "timestamp": "time.Time",
    "datetime": "time.Time",
    "date": "time.Time",
    "time": "time.Time",
    "float": "float64",
    "double": "float64",
    "decimal": "float64",
    "numeric": "float64",
    "json": "json.RawMessage",
    "jsonb": "json.RawMessage",
    "uuid": "string",
    "bytea": "[]byte",
}

# SQL 类型对应的 Go 默认值
GO_DEFAULT_VALUES: Dict[str, str] = {
    "int": "0",
    "int64": "0",
    "int16": "0",
    "string": "\"\"",
    "bool": "false",
    "time.Time": "time.Time{}",
    "float64": "0.0",
    "json.RawMessage": "nil",
    "[]byte": "nil",
}

# 常见复数表名到单数形式的映射
SINGULAR_MAP: Dict[str, str] = {
    "users": "user",
    "orders": "order",
    "products": "product",
    "categories": "category",
    "items": "item",
    "people": "person",
    "children": "child",
    "men": "man",
    "women": "woman",
    "teeth": "tooth",
    "feet": "foot",
    "mice": "mouse",
    "geese": "goose",
}


# ============================================================
# 核心数据结构
# ============================================================

class FieldDefinition:
    """字段定义"""
    def __init__(self, name: str, field_type: str, nullable: bool = True, primary_key: bool = False):
        self.name = name
        self.field_type = field_type
        self.nullable = nullable
        self.primary_key = primary_key

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.field_type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldDefinition":
        """从字典创建字段定义"""
        name = data.get("name", "")
        field_type = data.get("type", "")
        nullable = data.get("nullable", True)
        primary_key = data.get("primary_key", False)
        return cls(name, field_type, nullable, primary_key)


class TableDefinition:
    """表定义"""
    def __init__(self, name: str, fields: List[FieldDefinition], database: str = "postgresql"):
        self.name = name
        self.fields = fields
        self.database = database

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.name,
            "database": self.database,
            "fields": [f.to_dict() for f in self.fields],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableDefinition":
        """从字典创建表定义"""
        name = data.get("table", "")
        database = data.get("database", "postgresql")
        fields_data = data.get("fields", [])
        fields = [FieldDefinition.from_dict(f) for f in fields_data]
        return cls(name, fields, database)


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(data: Dict[str, Any]) -> Tuple[bool, str, Optional[TableDefinition]]:
    """
    验证输入数据并构建 TableDefinition
    
    返回: (是否成功, 错误码或空字符串, 表定义或None)
    """
    # 检查输入是否为空
    if not data:
        return False, "E001", None
    
    # 检查表名
    table_name = data.get("table", "")
    if not table_name:
        return False, "E009", None
    
    if not re.match(r'^[A-Za-z0-9_]+$', table_name):
        return False, "E009", None
    
    # 检查数据库类型
    database = data.get("database", "postgresql")
    if database not in SUPPORTED_DATABASES:
        return False, "E007", None
    
    # 检查字段
    fields_data = data.get("fields", [])
    if not fields_data:
        return False, "E002", None
    
    fields: List[FieldDefinition] = []
    for field_data in fields_data:
        if not isinstance(field_data, dict):
            return False, "E003", None
        
        name = field_data.get("name", "")
        field_type = field_data.get("type", "")
        
        if not name or not field_type:
            return False, "E008", None
        
        nullable = field_data.get("nullable", True)
        primary_key = field_data.get("primary_key", False)
        
        fields.append(FieldDefinition(name, field_type, nullable, primary_key))
    
    table_def = TableDefinition(table_name, fields, database)
    return True, "", table_def


def to_singular(name: str) -> str:
    """将表名转换为单数形式"""
    # 检查常见不规则复数
    if name in SINGULAR_MAP:
        return SINGULAR_MAP[name]
    
    # 处理规则复数
    if name.endswith("ies") and len(name) > 3:
        return name[:-3] + "y"
    elif name.endswith("ses") and len(name) > 3:
        return name[:-2]
    elif name.endswith("es") and len(name) > 2:
        return name[:-2]
    elif name.endswith("s") and not name.endswith("ss") and len(name) > 1:
        return name[:-1]
    
    return name


def generate_sql_create_table(table_def: TableDefinition) -> str:
    """
    生成 CREATE TABLE SQL 语句
    """
    lines: List[str] = []
    lines.append(f"CREATE TABLE {table_def.name} (")
    
    field_lines: List[str] = []
    for field in table_def.fields:
        field_type = field.field_type
        # 根据数据库类型调整类型映射
        if table_def.database == "mysql":
            if field_type == "serial" or field_type == "bigserial":
                field_type = "int"
        elif table_def.database == "sqlite":
            if field_type == "serial" or field_type == "bigserial":
                field_type = "INTEGER"
            elif field_type == "varchar":
                field_type = "TEXT"
        
        line = f"    {field.name} {field_type}"
        if field.primary_key:
            line += " PRIMARY KEY"
        elif field.nullable:
            line += " NULL"
        else:
            line += " NOT NULL"
        field_lines.append(line)
    
    lines.append(",\n".join(field_lines))
    lines.append(");")
    
    return "\n".join(lines)


def generate_orm_struct(table_def: TableDefinition) -> str:
    """
    生成 Go ORM 结构体定义
    """
    lines: List[str] = []
    struct_name = camel_case(to_singular(table_def.name))
    lines.append(f"// {table_def.name} 表对应的结构体")
    lines.append(f"type {struct_name} struct {{")
    
    for field in table_def.fields:
        go_type = GO_TYPE_MAP.get(field.field_type.lower(), "interface{}")
        field_name = camel_case(field.name)
        
        # 生成字段标签
        tags = []
        if table_def.database == "postgresql":
            tags.append(f"db:\"{field.name}\"")
        elif table_def.database == "mysql":
            tags.append(f"db:\"{field.name}\"")
        elif table_def.database == "sqlite":
            tags.append(f"db:\"{field.name}\"")
        
        if field.primary_key:
            tags.append("primary_key")
        
        tag_str = " ".join(tags)
        lines.append(f"    {field_name} {go_type} `{tag_str}`")
    
    lines.append("}")
    return "\n".join(lines)


def generate_orm_factory(table_def: TableDefinition) -> str:
    """
    生成 Go Factory 函数
    """
    lines: List[str] = []
    struct_name = camel_case(to_singular(table_def.name))
    
    lines.append(f"// New{struct_name} 创建 {table_def.name} 记录")
    lines.append(f"func New{struct_name}(data map[string]interface{{}}) (*{struct_name}, error) {{")
    lines.append(f"    obj := &{struct_name}{{}}")
    
    for field in table_def.fields:
        go_type = GO_TYPE_MAP.get(field.field_type.lower(), "interface{}")
        field_name = camel_case(field.name)
        default_value = GO_DEFAULT_VALUES.get(go_type, "nil")
        
        lines.append(f"    if val, ok := data[\"{field.name}\"]; ok {{")
        lines.append(f"        obj.{field_name} = val.({go_type})")
        lines.append(f"    }} else {{")
        lines.append(f"        obj.{field_name} = {default_value}")
        lines.append(f"    }}")
    
    lines.append("    return obj, nil")
    lines.append("}")
    
    return "\n".join(lines)


def process_sql_query(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理 SQL 查询构建请求
    
    返回包含 SQL、ORM 结构体和 Factory 的结果
    """
    success, error_code, table_def = validate_input(data)
    
    if not success:
        return {
            "status": "error",
            "error_code": error_code,
            "message": ERROR_MESSAGES.get(error_code, "未知错误"),
        }
    
    # 生成 SQL 语句
    sql_create = generate_sql_create_table(table_def)
    
    # 生成 ORM 结构体
    orm_struct = generate_orm_struct(table_def)
    
    # 生成 Factory
    orm_factory = generate_orm_factory(table_def)
    
    # 计算置信度
    confidence = calculate_confidence(table_def)
    
    result: Dict[str, Any] = {
        "status": "success",
        "data": {
            "table": table_def.name,
            "database": table_def.database,
            "sql_create": sql_create,
            "orm_struct": orm_struct,
            "orm_factory": orm_factory,
            "confidence": confidence,
        }
    }
    
    # 根据置信度添加标注
    if confidence < 85:
        result["data"]["warning"] = "[需核实] 部分字段类型映射可能存在不确定性，请人工复核"
    elif confidence < 90:
        result["data"]["warning"] = "建议复核：字段类型映射置信度中等"
    
    return result


def calculate_confidence(table_def: TableDefinition) -> int:
    """
    计算置信度（0-100）
    
    基于字段类型映射的确定性
    """
    if not table_def.fields:
        return 0
    
    known_types = 0
    for field in table_def.fields:
        if field.field_type.lower() in GO_TYPE_MAP:
            known_types += 1
    
    base_confidence = (known_types / len(table_def.fields)) * 100
    
    # 根据数据库类型调整
    if table_def.database == "postgresql":
        base_confidence += 5
    elif table_def.database in ("mysql", "sqlite"):
        base_confidence += 2
    
    # 限制在 0-100 范围
    return max(0, min(100, int(base_confidence)))


def camel_case(name: str) -> str:
    """将 snake_case 转换为 CamelCase"""
    parts = name.split("_")
    return "".join(p.capitalize() for p in parts if p)


def format_output(result: Dict[str, Any], output_format: str = "text") -> str:
    """
    格式化输出结果
    """
    if result["status"] == "error":
        return f"错误 [{result['error_code']}]: {result['message']}"
    
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    # text 格式
    data = result["data"]
    lines: List[str] = []
    lines.append(f"=== SQL 查询构建结果 ===")
    lines.append(f"表名: {data['table']}")
    lines.append(f"数据库: {data['database']}")
    lines.append(f"置信度: {data['confidence']}%")
    
    if "warning" in data:
        lines.append(f"警告: {data['warning']}")
    
    lines.append("")
    lines.append("--- SQL CREATE TABLE ---")
    lines.append(data["sql_create"])
    
    lines.append("")
    lines.append("--- Go ORM 结构体 ---")
    lines.append(data["orm_struct"])
    
    lines.append("")
    lines.append("--- Go Factory ---")
    lines.append(data["orm_factory"])
    
    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑
    
    使用硬编码样例数据，不依赖外部文件或网络。
    """
    print("=" * 60)
    print("开始自检 (selftest)...")
    print("=" * 60)
    
    # 测试样例 1: 基本表定义
    print("\n[测试 1] 基本表定义处理")
    test_data_1 = {
        "table": "users",
        "database": "postgresql",
        "fields": [
            {"name": "id", "type": "bigserial", "primary_key": True, "nullable": False},
            {"name": "username", "type": "varchar", "nullable": False},
            {"name": "email", "type": "varchar", "nullable": True},
            {"name": "created_at", "type": "timestamp", "nullable": True},
        ]
    }
    
    result_1 = process_sql_query(test_data_1)
    assert result_1["status"] == "success", f"测试 1 失败: {result_1}"
    assert "users" in result_1["data"]["sql_create"], "SQL 中应包含表名 users"
    assert "type User struct" in result_1["data"]["orm_struct"], "ORM 结构体应包含 User"
    assert result_1["data"]["confidence"] >= 80, f"置信度应 >= 80, 实际: {result_1['data']['confidence']}"
    print("  通过")
    
    # 测试样例 2: MySQL 表
    print("\n[测试 2] MySQL 表处理")
    test_data_2 = {
        "table": "orders",
        "database": "mysql",
        "fields": [
            {"name": "id", "type": "int", "primary_key": True, "nullable": False},
            {"name": "user_id", "type": "int", "nullable": False},
            {"name": "total", "type": "decimal", "nullable": True},
            {"name": "status", "type": "varchar", "nullable": True},
        ]
    }
    
    result_2 = process_sql_query(test_data_2)
    assert result_2["status"] == "success", f"测试 2 失败: {result_2}"
    assert "orders" in result_2["data"]["sql_create"], "SQL 中应包含表名 orders"
    assert "type Order struct" in result_2["data"]["orm_struct"], "ORM 结构体应包含 Order"
    print("  通过")
    
    # 测试样例 3: SQLite 表
    print("\n[测试 3] SQLite 表处理")
    test_data_3 = {
        "table": "products",
        "database": "sqlite",
        "fields": [
            {"name": "id", "type": "integer", "primary_key": True, "nullable": False},
            {"name": "name", "type": "text", "nullable": False},
            {"name": "price", "type": "real", "nullable": True},
        ]
    }
    
    result_3 = process_sql_query(test_data_3)
    assert result_3["status"] == "success", f"测试 3 失败: {result_3}"
    assert "products" in result_3["data"]["sql_create"], "SQL 中应包含表名 products"
    assert "type Product struct" in result_3["data"]["orm_struct"], "ORM 结构体应包含 Product"
    print("  通过")
    
    # 测试样例 4: 错误处理 - 空输入
    print("\n[测试 4] 错误处理 - 空输入")
    result_4 = process_sql_query({})
    assert result_4["status"] == "error", "空输入应返回错误"
    assert result_4["error_code"] == "E001", f"错误码应为 E001, 实际: {result_4['error_code']}"
    print("  通过")
    
    # 测试样例 5: 错误处理 - 非法表名
    print("\n[测试 5] 错误处理 - 非法表名")
    test_data_5 = {
        "table": "invalid table!",
        "database": "postgresql",
        "fields": [{"name": "id", "type": "int"}]
    }
    result_5 = process_sql_query(test_data_5)
    assert result_5["status"] == "error", "非法表名应返回错误"
    assert result_5["error_code"] == "E009", f"错误码应为 E009, 实际: {result_5['error_code']}"
    print("  通过")
    
    # 测试样例 6: 错误处理 - 不支持的数据库
    print("\n[测试 6] 错误处理 - 不支持的数据库")
    test_data_6 = {
        "table": "test",
        "database": "oracle",
        "fields": [{"name": "id", "type": "int"}]
    }
    result_6 = process_sql_query(test_data_6)
    assert result_6["status"] == "error", "不支持的数据库应返回错误"
    assert result_6["error_code"] == "E007", f"错误码应为 E007, 实际: {result_6['error_code']}"
    print("  通过")
    
    # 测试样例 7: 字段类型映射
    print("\n[测试 7] 字段类型映射")
    test_data_7 = {
        "table": "test_types",
        "database": "postgresql",
        "fields": [
            {"name": "int_col", "type": "int"},
            {"name": "str_col", "type": "varchar"},
            {"name": "bool_col", "type": "boolean"},
            {"name": "time_col", "type": "timestamp"},
        ]
    }
    result_7 = process_sql_query(test_data_7)
    assert result_7["status"] == "success", f"测试 7 失败: {result_7}"
    orm_struct_7 = result_7["data"]["orm_struct"]
    assert "int" in orm_struct_7, "应包含 int 类型"
    assert "string" in orm_struct_7, "应包含 string 类型"
    assert "bool" in orm_struct_7, "应包含 bool 类型"
    assert "time.Time" in orm_struct_7, "应包含 time.Time 类型"
    print("  通过")
    
    # 测试样例 8: Factory 生成
    print("\n[测试 8] Factory 生成")
    test_data_8 = {
        "table": "categories",
        "database": "postgresql",
        "fields": [
            {"name": "id", "type": "int", "primary_key": True},
            {"name": "name", "type": "varchar"},
        ]
    }
    result_8 = process_sql_query(test_data_8)
    assert result_8["status"] == "success", f"测试 8 失败: {result_8}"
    factory_str = result_8["data"]["orm_factory"]
    assert "NewCategory" in factory_str, "Factory 函数名应包含 NewCategory"
    assert "map[string]interface{}" in factory_str, "Factory 参数应为 map"
    print("  通过")
    
    # 测试样例 9: 输出格式化
    print("\n[测试 9] 输出格式化")
    test_data_9 = {
        "table": "test_format",
        "database": "postgresql",
        "fields": [{"name": "id", "type": "int"}]
    }
    result_9 = process_sql_query(test_data_9)
    json_output = format_output(result_9, "json")
    assert json_output.startswith("{"), "JSON 输出应以 { 开头"
    
    text_output = format_output(result_9, "text")
    assert "SQL 查询构建结果" in text_output, "文本输出应包含标题"
    print("  通过")
    
    # 测试样例 10: 置信度计算
    print("\n[测试 10] 置信度计算")
    test_data_10 = {
        "table": "known_types",
        "database": "postgresql",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "varchar"},
        ]
    }
    result_10 = process_sql_query(test_data_10)
    assert result_10["status"] == "success", f"测试 10 失败: {result_10}"
    assert result_10["data"]["confidence"] >= 90, "已知类型置信度应 >= 90"
    print("  通过")
    
    # 测试样例 11: 低置信度处理
    print("\n[测试 11] 低置信度处理")
    test_data_11 = {
        "table": "unknown_types",
        "database": "postgresql",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "custom", "type": "custom_type"},
        ]
    }
    result_11 = process_sql_query(test_data_11)
    assert result_11["status"] == "success", f"测试 11 失败: {result_11}"
    assert "warning" in result_11["data"], "低置信度应包含警告"
    print("  通过")
    
    # 测试样例 12: camel_case 函数
    print("\n[测试 12] camel_case 函数")
    assert camel_case("user_name") == "UserName", "camel_case 转换失败"
    assert camel_case("id") == "Id", "单字段转换失败"
    assert camel_case("") == "", "空字符串转换失败"
    print("  通过")
    
    # 测试样例 13: to_singular 函数
    print("\n[测试 13] to_singular 函数")
    assert to_singular("users") == "user", "users 应转换为 user"
    assert to_singular("orders") == "order", "orders 应转换为 order"
    assert to_singular("products") == "product", "products 应转换为 product"
    assert to_singular("categories") == "category", "categories 应转换为 category"
    assert to_singular("user") == "user", "user 应保持不变"
    print("  通过")
    
    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数
    """
    parser = argparse.ArgumentParser(
        description="SQL查询技能 - SQL query builder and ORM/Factory generator for Go",
        epilog="示例: python main.py '{\"table\": \"users\", \"fields\": [{\"name\": \"id\", \"type\": \"int\"}]}'"
    )
    
    parser.add_argument(
        "--input",
        nargs="?",
        help="JSON 格式的输入数据，包含表定义和字段信息",
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件或网络）",
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="输出格式 (默认: text)",
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1
    
    # 检查输入
    if not args.input:
        print(f"错误 [E001]: {ERROR_MESSAGES['E001']}")
        return 1
    
    # 解析 JSON 输入
    try:
        input_data = json.loads(args.input)
    except json.JSONDecodeError:
        print(f"错误 [E003]: {ERROR_MESSAGES['E003']}")
        return 1
    
    # 处理请求
    result = process_sql_query(input_data)
    
    # 输出结果
    output = format_output(result, args.format)
    print(output)
    
    # 根据状态返回退出码
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
