#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - SQL 到 GraphQL Schema 生成器（干净房重写版）

本脚本依据功能规格独立实现，不引用任何既有代码。
核心功能：解析 SQL CREATE TABLE 语句，生成对应的 GraphQL Schema 定义。
"""

import argparse
import re
import sys
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的 SQL 内容。",
    "E002": "关键信息缺失，无法解析 SQL 语句。",
    "E003": "输入格式错误，无法识别为有效的 SQL CREATE TABLE 语句。",
    "E004": "超出能力边界，不支持的 SQL 语法或特性。",
    "E005": "置信度过低，解析结果可能不准确。",
    "E006": "内部错误：解析器状态异常。",
    "E007": "内部错误：字段类型映射失败。",
    "E008": "内部错误：输出格式化失败。",
    "E009": "参数错误：命令行参数不合法。",
    "E010": "未知错误，请检查输入。",
}


class GeneratorError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class FieldInfo:
    """字段信息。"""

    def __init__(self, name: str, sql_type: str, nullable: bool = True):
        self.name = name
        self.sql_type = sql_type
        self.nullable = nullable

    def to_graphql_type(self) -> str:
        """将 SQL 类型映射为 GraphQL 类型（基础映射）。"""
        base = self._map_sql_type(self.sql_type)
        # GraphQL 中非空类型用 ! 后缀
        return base if self.nullable else f"{base}!"

    @staticmethod
    def _map_sql_type(sql_type: str) -> str:
        """SQL 类型到 GraphQL 标量类型的宽松映射。"""
        t = sql_type.strip().lower()
        # 字符串类
        if any(k in t for k in ("char", "text", "string", "clob", "enum")):
            return "String"
        # 整数类
        if any(k in t for k in ("int", "integer", "smallint", "bigint", "tinyint", "mediumint", "serial")):
            return "Int"
        # 浮点数类
        if any(k in t for k in ("float", "double", "real", "decimal", "numeric", "number")):
            return "Float"
        # 布尔类
        if any(k in t for k in ("bool", "boolean")):
            return "Boolean"
        # 时间日期类
        if any(k in t for k in ("date", "time", "datetime", "timestamp", "year")):
            return "String"  # 宽松处理为 String
        # 二进制类
        if any(k in t for k in ("blob", "binary", "varbinary")):
            return "String"
        # 其他 / 未知类型：默认 String，并可能触发 E005 提示
        return "String"


class TableInfo:
    """表信息。"""

    def __init__(self, name: str):
        self.name = name
        self.fields: List[FieldInfo] = []

    def add_field(self, field: FieldInfo) -> None:
        self.fields.append(field)


class ParsedSchema:
    """解析结果。"""

    def __init__(self):
        self.tables: List[TableInfo] = []
        self.confidence: float = 1.0  # 置信度 0~1
        self.warnings: List[str] = []

    def add_table(self, table: TableInfo) -> None:
        self.tables.append(table)

    def lower_confidence(self, amount: float, reason: str) -> None:
        """降低置信度并记录原因。"""
        self.confidence = max(0.0, self.confidence - amount)
        self.warnings.append(reason)


# ---------------------------------------------------------------------------
# SQL 解析器（核心逻辑）
# ---------------------------------------------------------------------------
class SqlParser:
    """解析 SQL CREATE TABLE 语句。"""

    # 匹配 CREATE TABLE 语句（支持可选的 IF NOT EXISTS）
    CREATE_TABLE_RE = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\((.*)\)\s*;?",
        re.IGNORECASE | re.DOTALL,
    )

    # 匹配字段定义行（宽松模式）
    FIELD_LINE_RE = re.compile(
        r"^\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s+([A-Za-z0-9_]+(?:\([^)]*\))?)\s*(.*)$",
        re.IGNORECASE,
    )

    # 识别约束关键字（这些行不应被当作字段）
    CONSTRAINT_KEYWORDS = {
        "PRIMARY", "KEY", "UNIQUE", "FOREIGN", "REFERENCES", "CHECK", "CONSTRAINT", "INDEX",
    }

    def parse(self, sql_text: str) -> ParsedSchema:
        """解析 SQL 文本，返回结构化结果。"""
        if not sql_text or not sql_text.strip():
            raise GeneratorError("E001")

        result = ParsedSchema()
        # 按分号分割，逐个处理 CREATE TABLE 语句
        statements = self._split_statements(sql_text)
        if not statements:
            raise GeneratorError("E003")

        for stmt in statements:
            table = self._parse_create_table(stmt)
            if table is not None:
                result.add_table(table)

        if not result.tables:
            raise GeneratorError("E003")

        # 置信度评估：如果解析出的字段较少或存在未知类型，降低置信度
        for table in result.tables:
            if not table.fields:
                result.lower_confidence(0.2, f"表 {table.name} 没有解析到字段")
            for field in table.fields:
                if field.sql_type.strip().lower() not in self._KNOWN_TYPES:
                    result.lower_confidence(0.1, f"字段 {field.name} 类型 {field.sql_type} 未知")

        return result

    # 已知类型集合（用于置信度评估）
    _KNOWN_TYPES = {
        "char", "varchar", "text", "string", "clob", "enum",
        "int", "integer", "smallint", "bigint", "tinyint", "mediumint", "serial",
        "float", "double", "real", "decimal", "numeric", "number",
        "bool", "boolean",
        "date", "time", "datetime", "timestamp", "year",
        "blob", "binary", "varbinary",
    }

    @staticmethod
    def _split_statements(sql_text: str) -> List[str]:
        """将 SQL 文本按分号分割为语句列表（简单分割，不考虑字符串内分号）。"""
        # 移除注释（-- 开头的行）
        lines = sql_text.splitlines()
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--") or stripped.startswith("#"):
                continue
            # 移除行内注释（-- 后的内容）
            idx = stripped.find("--")
            if idx >= 0:
                stripped = stripped[:idx]
            clean_lines.append(stripped)

        text = "\n".join(clean_lines)
        # 按分号分割
        parts = [p.strip() for p in text.split(";") if p.strip()]
        return parts

    def _parse_create_table(self, statement: str) -> Optional[TableInfo]:
        """解析单个 CREATE TABLE 语句。"""
        match = self.CREATE_TABLE_RE.search(statement)
        if not match:
            # 不是 CREATE TABLE 语句，忽略
            return None

        table_name = match.group(1)
        body = match.group(2)

        table = TableInfo(table_name)

        # 按逗号分割字段定义（简单分割，不考虑函数内逗号）
        # 为了稳健，这里按行处理更安全
        lines = body.splitlines()
        current_line = ""
        for line in lines:
            current_line += " " + line.strip()
            # 检查是否以逗号结尾（字段定义结束）
            if current_line.rstrip().endswith(","):
                self._process_field_line(current_line[:-1], table)
                current_line = ""
        # 处理最后一行（可能没有逗号）
        if current_line.strip():
            self._process_field_line(current_line, table)

        return table

    def _process_field_line(self, line: str, table: TableInfo) -> None:
        """处理单行字段定义。"""
        line = line.strip()
        if not line:
            return

        # 跳过约束定义
        first_word = line.split()[0].upper() if line.split() else ""
        if first_word in self.CONSTRAINT_KEYWORDS:
            return

        match = self.FIELD_LINE_RE.match(line)
        if not match:
            # 无法解析的行，降低置信度
            table.add_field(FieldInfo(f"unparsed_{len(table.fields)}", "unknown", True))
            return

        field_name = match.group(1)
        sql_type = match.group(2)
        remainder = match.group(3).upper()

        # 判断是否非空
        nullable = True
        if "NOT NULL" in remainder or "PRIMARY KEY" in remainder:
            nullable = False

        table.add_field(FieldInfo(field_name, sql_type, nullable))


# ---------------------------------------------------------------------------
# GraphQL Schema 生成器
# ---------------------------------------------------------------------------
class GraphQLGenerator:
    """从解析结果生成 GraphQL Schema 文本。"""

    def generate(self, schema: ParsedSchema) -> str:
        """生成 GraphQL Schema 字符串。"""
        if not schema.tables:
            raise GeneratorError("E002")

        lines = []
        lines.append("# 由 SQL 自动生成的 GraphQL Schema")
        lines.append("# 置信度: {:.0%}".format(schema.confidence))
        if schema.warnings:
            lines.append("# 警告:")
            for w in schema.warnings:
                lines.append(f"#   - {w}")
        lines.append("")

        for table in schema.tables:
            lines.append(f"type {self._to_pascal_case(table.name)} {{")
            for field in table.fields:
                gql_type = field.to_graphql_type()
                lines.append(f"  {field.name}: {gql_type}")
            lines.append("}")
            lines.append("")

        # 添加 Query 类型（简单骨架）
        lines.append("type Query {")
        for table in schema.tables:
            pascal = self._to_pascal_case(table.name)
            lines.append(f"  {table.name}(id: ID!): {pascal}")
        lines.append("}")

        return "\n".join(lines)

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """将 snake_case 或普通名称转换为 PascalCase。"""
        parts = re.split(r"[_\- ]+", name)
        return "".join(p.capitalize() for p in parts if p)


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_sql(sql_text: str) -> str:
    """处理 SQL 文本，返回 GraphQL Schema。"""
    parser = SqlParser()
    generator = GraphQLGenerator()

    try:
        parsed = parser.parse(sql_text)
        output = generator.generate(parsed)
        return output
    except GeneratorError:
        raise
    except Exception as exc:
        raise GeneratorError("E010", f"未知错误: {exc}") from exc


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行内置自检，返回退出码（0 表示通过）。"""
    # 硬编码测试数据（不依赖外部文件）
    test_sql = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255),
        age INT,
        created_at TIMESTAMP
    );

    CREATE TABLE orders (
        order_id BIGINT PRIMARY KEY,
        user_id INT NOT NULL,
        total DECIMAL(10,2),
        status VARCHAR(50)
    );
    """

    try:
        result = process_sql(test_sql)
    except GeneratorError as exc:
        print(f"自检失败: {exc}")
        return 1

    # 宽松断言（不依赖精确值）
    checks = []
    # 检查基本输出结构
    checks.append(("包含 type 定义", "type " in result))
    checks.append(("包含 Users 类型", "Users" in result))
    checks.append(("包含 Orders 类型", "Orders" in result))
    checks.append(("包含 Query 类型", "type Query" in result))
    checks.append(("包含字段 id", "id:" in result))
    checks.append(("包含字段 name", "name:" in result))

    # 检查非空标记（宽松：至少有一个 !）
    checks.append(("包含非空标记", "!" in result))

    # 检查置信度标注
    checks.append(("包含置信度", "置信度" in result))

    all_passed = True
    for name, passed in checks:
        status = "通过" if passed else "失败"
        print(f"  [{'✓' if passed else '✗'}] {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("自检全部通过 ✓")
        return 0
    else:
        print("自检存在失败项 ✗")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="SQL 到 GraphQL Schema 生成器",
        epilog="示例: python main.py --sql 'CREATE TABLE users (id INT, name VARCHAR(100));'",
    )
    parser.add_argument(
        "--sql",
        type=str,
        help="SQL CREATE TABLE 语句文本",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="包含 SQL 语句的文件路径",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 获取 SQL 输入
    sql_text = None
    if args.sql:
        sql_text = args.sql
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                sql_text = f.read()
        except OSError as exc:
            print(f"[E010] 无法读取文件: {exc}")
            return 1
    else:
        # 尝试从标准输入读取
        print("请输入 SQL 语句（Ctrl-D 结束）：", file=sys.stderr)
        try:
            sql_text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\n[E001] 输入被取消", file=sys.stderr)
            return 1

    if not sql_text or not sql_text.strip():
        print(f"[E001] {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    # 处理
    try:
        output = process_sql(sql_text)
        print(output)
        return 0
    except GeneratorError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
