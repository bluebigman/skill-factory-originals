#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

SQL 转 Prisma Schema 生成器（干净房实现，仅依据功能规格独立开发）。
提供命令行入口，支持将 SQL 建表语句转换为 Prisma Schema 格式。
包含 --selftest 离线自检模式，不依赖外部文件与网络。
"""

import argparse
import re
import sys
from typing import Dict, List, Optional, Tuple


# 错误码定义（对应功能规格第五节）
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的 SQL 内容。",
    "E002": "关键信息缺失，无法完成转换。",
    "E003": "输入格式错误，无法解析 SQL 语句。",
    "E004": "超出能力边界，暂不支持该 SQL 特性。",
    "E005": "置信度过低，结果可能不准确，请人工复核。",
    "E006": "内部错误：数据映射失败。",
    "E007": "内部错误：模板渲染失败。",
    "E008": "参数错误：命令行参数不合法。",
    "E009": "自检失败：核心逻辑未通过验证。",
    "E010": "未知错误。",
}


def err(code: str) -> str:
    """返回标准错误信息。"""
    return f"[{code}] {ERROR_CODES.get(code, ERROR_CODES['E010'])}"


# ---------- SQL 解析核心 ----------

# SQL 类型到 Prisma 类型的映射（宽松映射，不追求穷尽）
TYPE_MAP: Dict[str, str] = {
    "int": "Int",
    "integer": "Int",
    "bigint": "BigInt",
    "smallint": "Int",
    "tinyint": "Int",
    "decimal": "Decimal",
    "numeric": "Decimal",
    "float": "Float",
    "double": "Float",
    "real": "Float",
    "varchar": "String",
    "char": "String",
    "text": "String",
    "mediumtext": "String",
    "longtext": "String",
    "datetime": "DateTime",
    "timestamp": "DateTime",
    "date": "DateTime",
    "time": "DateTime",
    "boolean": "Boolean",
    "bool": "Boolean",
    "blob": "Bytes",
    "json": "Json",
}


def normalize_type(sql_type: str) -> Optional[str]:
    """将 SQL 类型名标准化，返回 Prisma 类型；未知返回 None。"""
    if not sql_type:
        return None
    # 提取类型名（去掉括号参数，如 varchar(255) -> varchar）
    base = re.sub(r"\(.*\)", "", sql_type).strip().lower()
    # 处理 unsigned / zerofill 等修饰
    base = base.replace("unsigned", "").replace("zerofill", "").strip()
    return TYPE_MAP.get(base)


class Column:
    """表示一个数据库列。"""

    def __init__(self, name: str, sql_type: str, nullable: bool = True,
                 primary_key: bool = False, unique: bool = False,
                 default: Optional[str] = None):
        self.name = name
        self.sql_type = sql_type
        self.nullable = nullable
        self.primary_key = primary_key
        self.unique = unique
        self.default = default

    def to_prisma_field(self) -> str:
        """将列转换为 Prisma Schema 字段定义行。"""
        prisma_type = normalize_type(self.sql_type)
        if prisma_type is None:
            # 未知类型：给出警告并回退到 String
            prisma_type = "String"
            # 标记不确定
            marker = " // [需核实] 未知类型"
        else:
            marker = ""

        # 属性列表
        attrs = []
        if self.primary_key:
            attrs.append("@id")
        if self.unique:
            attrs.append("@unique")
        if not self.nullable and not self.primary_key:
            attrs.append("")
        if self.default is not None:
            attrs.append(f"@default({self.default})")

        # 构造字段行
        optional_marker = "?" if self.nullable and not self.primary_key else ""
        attr_str = " ".join(a for a in attrs if a)
        line = f"  {self.name} {prisma_type}{optional_marker}{attr_str}".rstrip()
        if marker:
            line += marker
        return line


class Table:
    """表示一个数据库表。"""

    def __init__(self, name: str):
        self.name = name
        self.columns: List[Column] = []

    def add_column(self, col: Column) -> None:
        self.columns.append(col)

    def to_prisma_model(self) -> str:
        """将表转换为 Prisma Model 定义。"""
        if not self.columns:
            return f"model {self.name} {{\n  // 无字段\n}}"
        lines = [f"model {self.name} {{"]
        for col in self.columns:
            lines.append(col.to_prisma_field())
        lines.append("}")
        return "\n".join(lines)


def parse_create_table(sql: str) -> Optional[Table]:
    """
    解析单个 CREATE TABLE 语句。
    返回 Table 对象；解析失败返回 None。
    """
    # 提取表名
    m = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\(", sql, re.IGNORECASE)
    if not m:
        return None
    table_name = m.group(1)
    table = Table(table_name)

    # 提取括号内的字段定义部分（简单括号匹配）
    start = sql.find("(", m.end())
    if start == -1:
        return None
    # 找到匹配的右括号
    depth = 0
    end = -1
    for i in range(start, len(sql)):
        if sql[i] == "(":
            depth += 1
        elif sql[i] == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None

    content = sql[start + 1:end]
    # 按逗号分割（忽略括号内的逗号）
    parts = split_ignore_parens(content)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 跳过表级约束（PRIMARY KEY (xxx), FOREIGN KEY 等）
        if re.match(r"^(PRIMARY|FOREIGN|UNIQUE|KEY|CONSTRAINT|INDEX)", part, re.IGNORECASE):
            # 尝试提取主键信息（简化处理：单列主键）
            pk_m = re.search(r"PRIMARY\s+KEY\s*\(\s*`?(\w+)`?\s*\)", part, re.IGNORECASE)
            if pk_m:
                col_name = pk_m.group(1)
                for col in table.columns:
                    if col.name == col_name:
                        col.primary_key = True
                        col.nullable = False
            continue

        # 解析列定义：列名 类型 [属性...]
        col_m = re.match(r"`?(\w+)`?\s+([A-Za-z0-9_()\s]+?)(?:\s+(.*))?$", part, re.IGNORECASE)
        if not col_m:
            continue
        col_name = col_m.group(1)
        type_part = col_m.group(2).strip()
        attr_part = col_m.group(3) or ""

        # 提取类型（去掉可能的修饰符）
        type_match = re.match(r"([a-zA-Z]+(?:\([^)]*\))?)", type_part)
        if not type_match:
            continue
        sql_type = type_match.group(1)

        # 判断属性
        nullable = True
        primary_key = False
        unique = False
        default = None

        if re.search(r"NOT\s+NULL", attr_part, re.IGNORECASE):
            nullable = False
        if re.search(r"PRIMARY\s+KEY", attr_part, re.IGNORECASE):
            primary_key = True
            nullable = False
        if re.search(r"UNIQUE", attr_part, re.IGNORECASE):
            unique = True
        # 默认值
        def_m = re.search(r"DEFAULT\s+('([^']*)'|([\w.]+))", attr_part, re.IGNORECASE)
        if def_m:
            default = def_m.group(2) if def_m.group(2) else def_m.group(3)
            if default is not None:
                default = f'"{default}"' if def_m.group(2) else default

        # 自增列默认为主键
        if re.search(r"AUTO_INCREMENT", attr_part, re.IGNORECASE):
            primary_key = True
            nullable = False

        col = Column(
            name=col_name,
            sql_type=sql_type,
            nullable=nullable,
            primary_key=primary_key,
            unique=unique,
            default=default,
        )
        table.add_column(col)

    return table


def split_ignore_parens(s: str) -> List[str]:
    """按逗号分割字符串，忽略括号内的逗号。"""
    parts = []
    depth = 0
    current = []
    for ch in s:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def sql_to_prisma(sql_text: str) -> Tuple[str, List[str]]:
    """
    将 SQL 文本转换为 Prisma Schema。
    返回 (schema字符串, 警告列表)。
    """
    if not sql_text or not sql_text.strip():
        raise ValueError(err("E001"))

    warnings: List[str] = []
    # 按分号分割语句
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    if not statements:
        raise ValueError(err("E001"))

    models = []
    for stmt in statements:
        # 只处理 CREATE TABLE
        if not re.match(r"CREATE\s+TABLE", stmt, re.IGNORECASE):
            warnings.append(f"跳过非 CREATE TABLE 语句: {stmt[:50]}...")
            continue
        table = parse_create_table(stmt)
        if table is None:
            warnings.append(f"无法解析语句: {stmt[:50]}...")
            continue
        if not table.columns:
            warnings.append(f"表 {table.name} 无有效字段")
        models.append(table.to_prisma_model())

    if not models:
        raise ValueError(err("E003") + " 未找到有效的 CREATE TABLE 语句。")

    # 组装 schema
    schema = "// 由 SQL 转 Prisma Schema 生成器生成\n"
    schema += "// 注意：自动生成结果，请人工复核关键字段\n\n"
    schema += "generator client {\n  provider = \"prisma-client-js\"\n}\n\n"
    schema += "datasource db {\n  provider = \"postgresql\"\n  url      = env(\"DATABASE_URL\")\n}\n\n"
    schema += "\n\n".join(models)
    schema += "\n"

    return schema, warnings


# ---------- 自检模块 ----------

def run_selftest() -> int:
    """离线自检核心逻辑。返回 0 表示通过，非 0 表示失败。"""
    print("=== 自检开始 ===")

    # 硬编码样例数据
    sample_sql = """
    CREATE TABLE users (
        id INT NOT NULL AUTO_INCREMENT,
        email VARCHAR(255) NOT NULL UNIQUE,
        name VARCHAR(100),
        age INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    );
    CREATE TABLE posts (
        id INT PRIMARY KEY,
        title VARCHAR(200) NOT NULL,
        content TEXT,
        published BOOLEAN DEFAULT false,
        user_id INT NOT NULL
    );
    """

    try:
        schema, warnings = sql_to_prisma(sample_sql)
    except ValueError as e:
        print(f"自检失败: {e}")
        return 1

    # 宽松断言（不依赖精确值）
    assert "model users" in schema, "缺少 users 模型"
    assert "model posts" in schema, "缺少 posts 模型"
    # 检查字段名（去掉前导空格）
    assert re.search(r"\bid\b", schema), "缺少 id 字段"
    assert re.search(r"\bemail\b", schema), "缺少 email 字段"
    assert "@id" in schema, "缺少主键标记"
    assert "String" in schema, "缺少 String 类型映射"
    assert "Int" in schema, "缺少 Int 类型映射"
    assert "Boolean" in schema, "缺少 Boolean 类型映射"
    assert "DateTime" in schema, "缺少 DateTime 类型映射"
    # 检查字段数量（宽松：至少 5 个字段）
    field_count = len(re.findall(r"\n  \w+", schema))
    assert field_count >= 5, f"字段数量过少: {field_count}"
    # 检查行数（宽松）
    line_count = len(schema.splitlines())
    assert line_count >= 15, f"Schema 行数过少: {line_count}"

    # 测试空输入
    try:
        sql_to_prisma("")
        print("自检失败: 空输入未抛出异常")
        return 1
    except ValueError as e:
        assert "E001" in str(e), "空输入错误码不正确"

    # 测试无效输入
    try:
        sql_to_prisma("SELECT * FROM foo;")
        print("自检失败: 无效输入未抛出异常")
        return 1
    except ValueError as e:
        assert "E003" in str(e), "无效输入错误码不正确"

    # 测试类型映射
    assert normalize_type("varchar(255)") == "String", "varchar 映射错误"
    assert normalize_type("INT") == "Int", "INT 映射错误"
    assert normalize_type("timestamp") == "DateTime", "timestamp 映射错误"
    assert normalize_type("unknown_type") is None, "未知类型应返回 None"

    # 测试 split_ignore_parens
    parts = split_ignore_parens("a, b(c,d), e")
    assert len(parts) == 3, f"split_ignore_parens 结果数量错误: {len(parts)}"
    assert parts[1] == " b(c,d)", f"split_ignore_parens 内容错误: {parts[1]}"

    print("=== 自检通过 ===")
    return 0


# ---------- 命令行入口 ----------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="SQL 转 Prisma Schema 生成器",
        epilog="示例: python main.py input.sql -o schema.prisma",
    )
    parser.add_argument("input", nargs="?", help="输入 SQL 文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径（默认 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--sql", help="直接传入 SQL 字符串")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 获取 SQL 输入
    sql_text = None
    if args.sql:
        sql_text = args.sql
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                sql_text = f.read()
        except FileNotFoundError:
            print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"读取文件失败: {e}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    # 执行转换
    try:
        schema, warnings = sql_to_prisma(sql_text)
    except ValueError as e:
        print(f"转换失败: {e}", file=sys.stderr)
        return 1

    # 输出警告
    for w in warnings:
        print(f"警告: {w}", file=sys.stderr)

    # 输出结果
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(schema)
            print(f"已写入: {args.output}")
        except Exception as e:
            print(f"写入文件失败: {e}", file=sys.stderr)
            return 1
    else:
        print(schema)

    return 0


if __name__ == "__main__":
    sys.exit(main())
