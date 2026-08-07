#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

SQL 查询转 GraphQL Schema 生成器（独立实现）

功能：
  将 SQL 查询语句解析为 GraphQL Schema 定义。
  支持常见 SQL 类型映射、表名/字段名提取、主键识别等。

用法：
  python main.py --sql "SELECT id, name FROM users"
  python main.py --selftest

错误码：
  E001 输入为空
  E002 关键信息缺失（如无表名）
  E003 输入格式错误（SQL 语法无法解析）
  E004 超出能力边界（不支持的 SQL 特性）
  E005 置信度过低（无法可靠生成）
  E006 文件读取失败
  E007 参数解析失败
  E008 内部逻辑错误
  E009 输出写入失败
  E010 未知错误
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# SQL 类型到 GraphQL 类型的映射
TYPE_MAPPING: Dict[str, str] = {
    "int": "Int",
    "integer": "Int",
    "smallint": "Int",
    "bigint": "Int",
    "tinyint": "Int",
    "serial": "Int",
    "bigserial": "Int",
    "decimal": "Float",
    "numeric": "Float",
    "float": "Float",
    "real": "Float",
    "double": "Float",
    "double precision": "Float",
    "money": "Float",
    "char": "String",
    "varchar": "String",
    "character": "String",
    "character varying": "String",
    "text": "String",
    "tinytext": "String",
    "mediumtext": "String",
    "longtext": "String",
    "nchar": "String",
    "nvarchar": "String",
    "ntext": "String",
    "date": "String",
    "datetime": "String",
    "timestamp": "String",
    "time": "String",
    "year": "Int",
    "boolean": "Boolean",
    "bool": "Boolean",
    "blob": "String",
    "binary": "String",
    "varbinary": "String",
    "json": "String",
    "enum": "String",
    "set": "String",
    "uuid": "String",
    "xml": "String",
    "array": "String",
}

# 常见主键标识
PRIMARY_KEY_HINTS: List[str] = ["primary key", "pk", "id"]


# ============================================================
# 核心数据结构
# ============================================================

class FieldInfo:
    """字段信息"""

    def __init__(self, name: str, sql_type: str, nullable: bool = True,
                 is_primary: bool = False, default: Optional[str] = None,
                 comment: Optional[str] = None):
        self.name = name
        self.sql_type = sql_type
        self.nullable = nullable
        self.is_primary = is_primary
        self.default = default
        self.comment = comment

    def to_graphql_type(self) -> str:
        """转换为 GraphQL 类型字符串"""
        gql_type = TYPE_MAPPING.get(self.sql_type.lower(), "String")
        if not self.nullable and not self.is_primary:
            gql_type += "!"
        return gql_type

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "sql_type": self.sql_type,
            "graphql_type": self.to_graphql_type(),
            "nullable": self.nullable,
            "is_primary": self.is_primary,
            "default": self.default,
            "comment": self.comment,
        }


class TableInfo:
    """表信息"""

    def __init__(self, name: str, fields: List[FieldInfo],
                 comment: Optional[str] = None):
        self.name = name
        self.fields = fields
        self.comment = comment

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "fields": [f.to_dict() for f in self.fields],
            "comment": self.comment,
        }


class SchemaResult:
    """生成结果"""

    def __init__(self, schema_text: str, tables: List[TableInfo],
                 confidence: float, warnings: List[str]):
        self.schema_text = schema_text
        self.tables = tables
        self.confidence = confidence
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "schema_text": self.schema_text,
            "tables": [t.to_dict() for t in self.tables],
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ============================================================
# SQL 解析器（轻量级、规则驱动）
# ============================================================

class SQLParser:
    """轻量级 SQL 解析器，仅提取生成 GraphQL Schema 所需信息"""

    # 提取 SELECT 子句中的字段列表
    SELECT_RE = re.compile(
        r"SELECT\s+(.+?)\s+FROM", re.IGNORECASE | re.DOTALL
    )

    # 提取 FROM 子句中的表名
    FROM_RE = re.compile(
        r"FROM\s+([`\"\w\.]+)", re.IGNORECASE
    )

    # 提取 CREATE TABLE 语句中的表名
    CREATE_TABLE_RE = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\w\.]+)",
        re.IGNORECASE,
    )

    # 提取字段定义行
    FIELD_LINE_RE = re.compile(
        r"^\s*([`\"\w]+)\s+([a-zA-Z\s]+?)(?:\s+\([^)]*\))?"
        r"(?:\s+(UNSIGNED|ZEROFILL))?"
        r"(?:\s+(?:NOT\s+NULL|NULL))?"
        r"(?:\s+DEFAULT\s+([^,]+))?"
        r"(?:\s+COMMENT\s+'([^']*)')?",
        re.IGNORECASE | re.MULTILINE,
    )

    # 主键约束提取
    PRIMARY_KEY_RE = re.compile(
        r"PRIMARY\s+KEY\s*\(([^)]+)\)", re.IGNORECASE
    )

    # 字段级 PRIMARY KEY 标记
    INLINE_PRIMARY_KEY_RE = re.compile(
        r"PRIMARY\s+KEY", re.IGNORECASE
    )

    def __init__(self, sql_text: str):
        self.sql_text = sql_text.strip()

    def parse(self) -> List[TableInfo]:
        """解析 SQL，返回表信息列表"""
        if not self.sql_text:
            raise ValueError("E001: 输入为空")

        # 支持多语句，按分号分割（简单处理，不处理字符串内的分号）
        statements = self._split_statements(self.sql_text)
        tables: List[TableInfo] = []

        for stmt in statements:
            if not stmt.strip():
                continue

            # 尝试解析 CREATE TABLE
            create_table = self._parse_create_table(stmt)
            if create_table:
                tables.append(create_table)
                continue

            # 尝试解析 SELECT
            select_table = self._parse_select(stmt)
            if select_table:
                tables.append(select_table)
                continue

            # 无法识别的语句，跳过（不报错，保持宽容）

        if not tables:
            raise ValueError("E003: 输入格式错误，无法识别任何表结构")

        return tables

    def _split_statements(self, sql: str) -> List[str]:
        """简单分割多条 SQL 语句"""
        # 简化处理：按分号分割，忽略引号内的分号
        statements = []
        current = []
        in_single_quote = False
        in_double_quote = False

        for char in sql:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == ";" and not in_single_quote and not in_double_quote:
                statements.append("".join(current))
                current = []
                continue
            current.append(char)

        if current:
            statements.append("".join(current))

        return statements

    def _parse_create_table(self, stmt: str) -> Optional[TableInfo]:
        """解析 CREATE TABLE 语句"""
        match = self.CREATE_TABLE_RE.search(stmt)
        if not match:
            return None

        table_name = self._clean_identifier(match.group(1))

        # 提取字段定义部分（括号内的内容）
        start = stmt.find("(")
        end = stmt.rfind(")")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("E003: CREATE TABLE 语句缺少括号定义")

        body = stmt[start + 1:end]

        # 提取主键约束
        primary_keys: List[str] = []
        pk_match = self.PRIMARY_KEY_RE.search(body)
        if pk_match:
            pk_list = pk_match.group(1).split(",")
            primary_keys = [self._clean_identifier(k) for k in pk_list]

        # 提取字段行
        fields: List[FieldInfo] = []
        lines = body.split("\n")
        for line in lines:
            line = line.strip().rstrip(",")
            if not line or line.upper().startswith(("PRIMARY", "UNIQUE",
                                                    "FOREIGN", "CONSTRAINT",
                                                    "KEY", "INDEX",
                                                    "CHECK", "FULLTEXT",
                                                    "SPATIAL")):
                continue

            field = self._parse_field_line(line)
            if field:
                # 检查是否为主键
                if field.name in primary_keys or self.INLINE_PRIMARY_KEY_RE.search(line):
                    field.is_primary = True
                    field.nullable = False
                fields.append(field)

        if not fields:
            raise ValueError("E003: 无法从 CREATE TABLE 中提取字段")

        return TableInfo(table_name, fields)

    def _parse_field_line(self, line: str) -> Optional[FieldInfo]:
        """解析单个字段定义行"""
        match = self.FIELD_LINE_RE.match(line)
        if not match:
            return None

        name = self._clean_identifier(match.group(1))
        sql_type = match.group(2).strip()

        # 判断可空性
        nullable = True
        if "NOT NULL" in line.upper():
            nullable = False
        elif "PRIMARY KEY" in line.upper():
            nullable = False

        # 提取默认值
        default = None
        default_match = re.search(r"DEFAULT\s+([^,\s]+)", line, re.IGNORECASE)
        if default_match:
            default = default_match.group(1).strip("'\"")

        # 提取注释
        comment = None
        comment_match = re.search(r"COMMENT\s+'([^']*)'", line, re.IGNORECASE)
        if comment_match:
            comment = comment_match.group(1)

        return FieldInfo(
            name=name,
            sql_type=sql_type,
            nullable=nullable,
            is_primary=bool(self.INLINE_PRIMARY_KEY_RE.search(line)),
            default=default,
            comment=comment,
        )

    def _parse_select(self, stmt: str) -> Optional[TableInfo]:
        """解析 SELECT 语句（生成查询结果对应的虚拟表）"""
        select_match = self.SELECT_RE.search(stmt)
        from_match = self.FROM_RE.search(stmt)

        if not select_match or not from_match:
            return None

        select_part = select_match.group(1)
        table_name = self._clean_identifier(from_match.group(1))

        # 解析字段列表
        fields: List[FieldInfo] = []
        # 按逗号分割，但忽略括号内的逗号（如函数参数）
        parts = self._split_select_fields(select_part)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 处理别名
            field_name = self._extract_field_name(part)
            if not field_name:
                continue

            # 推断类型（SELECT 中无法准确推断，默认为 String）
            fields.append(FieldInfo(
                name=field_name,
                sql_type="unknown",
                nullable=True,
                is_primary=False,
            ))

        if not fields:
            raise ValueError("E003: SELECT 语句中没有有效字段")

        return TableInfo(f"query_{table_name}", fields)

    def _split_select_fields(self, select_part: str) -> List[str]:
        """分割 SELECT 字段列表，处理括号嵌套"""
        parts = []
        current = []
        depth = 0

        for char in select_part:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append("".join(current))
                current = []
                continue
            current.append(char)

        if current:
            parts.append("".join(current))

        return parts

    def _extract_field_name(self, part: str) -> Optional[str]:
        """从字段表达式中提取字段名"""
        # 处理别名
        alias_match = re.search(r"(?:AS\s+)?([`\"\w]+)\s*$", part, re.IGNORECASE)
        if alias_match:
            return self._clean_identifier(alias_match.group(1))

        # 处理简单字段
        field_match = re.match(r"^[`\"\w\.]+$", part.strip())
        if field_match:
            # 取最后一部分（去掉表前缀）
            return self._clean_identifier(part.strip().split(".")[-1])

        # 复杂表达式，使用哈希生成名称
        import hashlib
        hash_val = hashlib.md5(part.encode()).hexdigest()[:8]
        return f"expr_{hash_val}"

    def _clean_identifier(self, ident: str) -> str:
        """清理标识符（去除引号和反引号）"""
        return ident.strip().strip('`"\' ')


# ============================================================
# GraphQL Schema 生成器
# ============================================================

class GraphQLSchemaGenerator:
    """将解析后的表结构生成 GraphQL Schema"""

    def generate(self, tables: List[TableInfo]) -> SchemaResult:
        """生成 GraphQL Schema"""
        if not tables:
            raise ValueError("E002: 没有可用的表结构信息")

        schema_parts: List[str] = []
        warnings: List[str] = []

        # 生成类型定义
        for table in tables:
            type_def = self._generate_type(table, warnings)
            schema_parts.append(type_def)

        # 生成查询入口
        query_def = self._generate_query(tables)
        schema_parts.append(query_def)

        schema_text = "\n\n".join(schema_parts)

        # 计算置信度
        confidence = self._calculate_confidence(tables, warnings)

        return SchemaResult(
            schema_text=schema_text,
            tables=tables,
            confidence=confidence,
            warnings=warnings,
        )

    def _generate_type(self, table: TableInfo, warnings: List[str]) -> str:
        """生成单个类型的 GraphQL 定义"""
        lines = []
        lines.append(f"type {self._to_pascal_case(table.name)} {{")

        for field in table.fields:
            gql_type = field.to_graphql_type()
            field_line = f"  {field.name}: {gql_type}"

            # 添加注释
            if field.comment:
                field_line += f" # {field.comment}"
            elif field.is_primary:
                field_line += " # primary key"

            lines.append(field_line)

            # 检查类型映射
            if field.sql_type.lower() not in TYPE_MAPPING and field.sql_type != "unknown":
                warnings.append(
                    f"字段 {table.name}.{field.name} 的类型 '{field.sql_type}' "
                    f"未在映射表中，已使用 String"
                )

        lines.append("}")
        return "\n".join(lines)

    def _generate_query(self, tables: List[TableInfo]) -> str:
        """生成 Query 类型定义"""
        lines = ["type Query {"]

        for table in tables:
            type_name = self._to_pascal_case(table.name)
            # 查询单条
            lines.append(f"  {table.name}(id: ID!): {type_name}")
            # 查询列表
            lines.append(f"  {table.name}List(limit: Int, offset: Int): [{type_name}]")

        lines.append("}")
        return "\n".join(lines)

    def _calculate_confidence(self, tables: List[TableInfo],
                              warnings: List[str]) -> float:
        """计算置信度"""
        base = 95.0  # 基础置信度

        # 有警告则降低置信度
        base -= len(warnings) * 3

        # 有未知类型字段降低置信度
        unknown_count = 0
        for table in tables:
            for field in table.fields:
                if field.sql_type.lower() not in TYPE_MAPPING:
                    unknown_count += 1

        base -= unknown_count * 2

        # 限制范围
        return max(50.0, min(99.0, base))

    def _to_pascal_case(self, name: str) -> str:
        """转换为 PascalCase"""
        # 移除特殊字符，按分隔符拆分
        parts = re.split(r"[_\-\s\.]+", name)
        pascal = "".join(p.capitalize() for p in parts if p)
        return pascal if pascal else "UnknownType"


# ============================================================
# 主程序
# ============================================================

def process_sql(sql_text: str) -> Dict[str, Any]:
    """处理 SQL 文本，返回结果字典"""
    try:
        # 解析 SQL
        parser = SQLParser(sql_text)
        tables = parser.parse()

        # 生成 Schema
        generator = GraphQLSchemaGenerator()
        result = generator.generate(tables)

        return result.to_dict()

    except ValueError as e:
        # 转换错误信息为错误码格式
        error_msg = str(e)
        if error_msg.startswith("E0"):
            return {"error": error_msg}
        return {"error": f"E003: {error_msg}"}
    except Exception as e:
        return {"error": f"E010: 未知错误 - {str(e)}"}


def run_selftest() -> bool:
    """内置自检函数，使用硬编码样例数据"""
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 测试用例 1: CREATE TABLE 语句
    print("\n[测试 1] CREATE TABLE 语句")
    sql1 = """
    CREATE TABLE users (
        id INT NOT NULL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255),
        age INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    );
    """
    result1 = process_sql(sql1)
    assert "error" not in result1, f"测试 1 失败: {result1.get('error')}"
    assert "schema_text" in result1, "测试 1 失败: 缺少 schema_text"
    assert "users" in result1["schema_text"].lower(), "测试 1 失败: 缺少 users 类型"
    # 修正：确保置信度检查更合理
    assert result1["confidence"] > 70, f"测试 1 失败: 置信度过低 ({result1['confidence']})"
    print(f"  通过 (置信度: {result1['confidence']:.1f}%)")

    # 测试用例 2: SELECT 语句
    print("\n[测试 2] SELECT 语句")
    sql2 = "SELECT id, name, email FROM customers;"
    result2 = process_sql(sql2)
    assert "error" not in result2, f"测试 2 失败: {result2.get('error')}"
    assert "schema_text" in result2, "测试 2 失败: 缺少 schema_text"
    assert "customers" in result2["schema_text"].lower(), "测试 2 失败: 缺少 customers 类型"
    print(f"  通过 (置信度: {result2['confidence']:.1f}%)")

    # 测试用例 3: 复杂 CREATE TABLE
    print("\n[测试 3] 复杂 CREATE TABLE")
    sql3 = """
    CREATE TABLE orders (
        id INT NOT NULL AUTO_INCREMENT,
        user_id INT NOT NULL,
        total DECIMAL(10,2) DEFAULT 0.00,
        status ENUM('pending', 'paid', 'shipped') DEFAULT 'pending',
        created_at TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_user (user_id)
    );
    """
    result3 = process_sql(sql3)
    assert "error" not in result3, f"测试 3 失败: {result3.get('error')}"
    assert "schema_text" in result3, "测试 3 失败: 缺少 schema_text"
    assert "orders" in result3["schema_text"].lower(), "测试 3 失败: 缺少 orders 类型"
    assert "Query" in result3["schema_text"], "测试 3 失败: 缺少 Query 类型"
    print(f"  通过 (置信度: {result3['confidence']:.1f}%)")

    # 测试用例 4: 错误处理
    print("\n[测试 4] 错误处理")
    result4 = process_sql("")
    assert "error" in result4, "测试 4 失败: 空输入应该报错"
    assert result4["error"].startswith("E001"), "测试 4 失败: 错误码应为 E001"
    print(f"  通过 (错误码: {result4['error']})")

    # 测试用例 5: 多表
    print("\n[测试 5] 多表 SQL")
    sql5 = """
    CREATE TABLE products (
        id INT NOT NULL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        price FLOAT
    );
    CREATE TABLE categories (
        id INT NOT NULL PRIMARY KEY,
        name VARCHAR(100)
    );
    """
    result5 = process_sql(sql5)
    assert "error" not in result5, f"测试 5 失败: {result5.get('error')}"
    assert "products" in result5["schema_text"].lower(), "测试 5 失败: 缺少 products"
    assert "categories" in result5["schema_text"].lower(), "测试 5 失败: 缺少 categories"
    print(f"  通过 (置信度: {result5['confidence']:.1f}%)")

    # 测试用例 6: 类型映射
    print("\n[测试 6] 类型映射")
    sql6 = """
    CREATE TABLE test_types (
        id INT NOT NULL PRIMARY KEY,
        name VARCHAR(100),
        price DECIMAL(10,2),
        is_valid BOOLEAN,
        created_at DATETIME,
        data JSON
    );
    """
    result6 = process_sql(sql6)
    assert "error" not in result6, f"测试 6 失败: {result6.get('error')}"
    schema_text = result6["schema_text"]
    assert "Int" in schema_text, "测试 6 失败: INT 应映射为 Int"
    assert "Float" in schema_text, "测试 6 失败: DECIMAL 应映射为 Float"
    assert "Boolean" in schema_text, "测试 6 失败: BOOLEAN 应映射为 Boolean"
    print(f"  通过 (置信度: {result6['confidence']:.1f}%)")

    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return True


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SQL 查询转 GraphQL Schema 生成器"
    )
    parser.add_argument(
        "--sql", type=str, help="SQL 查询语句"
    )
    parser.add_argument(
        "--file", type=str, help="SQL 文件路径"
    )
    parser.add_argument(
        "--output", type=str, help="输出文件路径（JSON 格式）"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行自检"
    )

    args = parser.parse_args()

    # 自检模式
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

    # 获取 SQL 输入
    sql_text = None
    if args.sql:
        sql_text = args.sql
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                sql_text = f.read()
        except FileNotFoundError:
            print("E006: 文件不存在")
            return 1
        except Exception as e:
            print(f"E006: 文件读取失败 - {e}")
            return 1
    else:
        # 从标准输入读取
        print("请输入 SQL 查询（输入空行结束）：")
        lines = []
        try:
            while True:
                line = input()
                if not line.strip():
                    break
                lines.append(line)
        except EOFError:
            pass
        sql_text = "\n".join(lines)

    # 处理 SQL
    result = process_sql(sql_text)

    # 输出结果
    if "error" in result:
        print(f"错误: {result['error']}")
        return 1

    # 输出 Schema
    print("\n" + "=" * 60)
    print("生成的 GraphQL Schema：")
    print("=" * 60)
    print(result["schema_text"])
    print("=" * 60)
    print(f"置信度: {result['confidence']:.1f}%")

    if result["warnings"]:
        print("\n警告：")
        for warning in result["warnings"]:
            print(f"  - {warning}")

    # 输出到文件
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")
        except Exception as e:
            print(f"E009: 输出写入失败 - {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
