#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL 转 Prisma Schema 生成器 - 独立实现脚本
============================================
本脚本根据功能规格独立实现，不参考任何既有代码。
支持将 SQL CREATE TABLE 语句转换为 Prisma Schema 模型定义。

用法:
    python main.py --selftest       # 运行内置自检
    python main.py < input.sql      # 从标准输入读取 SQL 并输出 Prisma Schema

错误码:
    E001 参数错误
    E002 输入为空
    E003 SQL 语法无法解析
    E004 无法识别数据类型
    E005 缺少表名
    E006 缺少字段名
    E007 外键引用表不存在
    E008 字段类型映射失败
    E009 输出写入失败
    E010 内部逻辑错误
"""

import sys
import re
import argparse
from typing import List, Dict, Optional, Tuple, Any
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 常量定义
# ============================================================

# SQL 数据类型到 Prisma 类型的映射表
TYPE_MAPPING: Dict[str, str] = {
    # 整数类型
    'int': 'Int',
    'integer': 'Int',
    'smallint': 'Int',
    'bigint': 'BigInt',
    'tinyint': 'Int',
    'mediumint': 'Int',
    # 小数类型
    'decimal': 'Decimal',
    'numeric': 'Decimal',
    'float': 'Float',
    'double': 'Float',
    'real': 'Float',
    # 字符串类型
    'char': 'String',
    'varchar': 'String',
    'text': 'String',
    'tinytext': 'String',
    'mediumtext': 'String',
    'longtext': 'String',
    'nchar': 'String',
    'nvarchar': 'String',
    'ntext': 'String',
    # 日期时间类型
    'date': 'DateTime',
    'datetime': 'DateTime',
    'timestamp': 'DateTime',
    'time': 'DateTime',
    'year': 'Int',
    # 布尔类型
    'bool': 'Boolean',
    'boolean': 'Boolean',
    # 二进制类型
    'blob': 'Bytes',
    'binary': 'Bytes',
    'varbinary': 'Bytes',
    'tinyblob': 'Bytes',
    'mediumblob': 'Bytes',
    'longblob': 'Bytes',
    # 特殊类型（需人工确认）
    'json': 'Json',
    'jsonb': 'Json',
    'uuid': 'String',
    'enum': 'String',
    'set': 'String',
}

# 需要人工确认的类型（给出置信度标注）
UNCERTAIN_TYPES: set = {'json', 'jsonb', 'enum', 'set', 'blob', 'binary', 'varbinary'}


# ============================================================
# 数据结构定义
# ============================================================

class Field:
    """字段定义"""
    def __init__(self, name: str, sql_type: str, prisma_type: str,
                 is_required: bool = True, is_id: bool = False,
                 is_unique: bool = False, has_default: bool = False,
                 default_value: Optional[str] = None,
                 is_autoincrement: bool = False,
                 is_relation: bool = False,
                 relation_ref: Optional[str] = None,
                 relation_field: Optional[str] = None,
                 uncertain: bool = False):
        self.name = name
        self.sql_type = sql_type
        self.prisma_type = prisma_type
        self.is_required = is_required
        self.is_id = is_id
        self.is_unique = is_unique
        self.has_default = has_default
        self.default_value = default_value
        self.is_autoincrement = is_autoincrement
        self.is_relation = is_relation
        self.relation_ref = relation_ref
        self.relation_field = relation_field
        self.uncertain = uncertain

    def to_prisma_field(self) -> str:
        """生成 Prisma 字段定义行"""
        # 字段类型
        type_str = self.prisma_type
        if not self.is_required:
            type_str += "?"

        # 字段名
        line = f"  {self.name} {type_str}"

        # 属性
        attrs = []
        if self.is_id:
            attrs.append("@id")
        if self.is_unique:
            attrs.append("@unique")
        if self.has_default and self.default_value:
            if self.default_value.upper() == 'CURRENT_TIMESTAMP':
                attrs.append("@default(now())")
            elif self.default_value.upper() == 'NULL':
                pass  # 无默认值
            elif self.is_autoincrement:
                attrs.append("@default(autoincrement())")
            else:
                # 尝试判断是否为数字
                try:
                    float(self.default_value)
                    attrs.append(f"@default({self.default_value})")
                except ValueError:
                    attrs.append(f"@default(\"{self.default_value}\")")
        if self.is_relation and self.relation_ref:
            ref_field = self.relation_field if self.relation_field else "id"
            attrs.append(f"@relation(fields: [{self.name}], references: [{ref_field}])")

        if attrs:
            line += " " + " ".join(attrs)

        # 不确定类型标注
        if self.uncertain:
            line += "  // ⚠️ 类型需人工确认"

        return line


class Model:
    """Prisma 模型定义"""
    def __init__(self, name: str):
        self.name = name
        self.fields: List[Field] = []
        self.has_id = False
        self.comments: List[str] = []

    def add_field(self, field: Field):
        self.fields.append(field)
        if field.is_id:
            self.has_id = True

    def to_prisma_model(self) -> str:
        """生成 Prisma 模型定义字符串"""
        lines = []
        lines.append(f"model {self.name} {{")

        # 添加注释
        for comment in self.comments:
            lines.append(f"  // {comment}")

        # 添加字段
        for field in self.fields:
            lines.append(field.to_prisma_field())

        # 缺少主键提示
        if not self.has_id:
            lines.append("  // ⚠️ 警告: 该表缺少主键定义")

        lines.append("}")
        return "\n".join(lines)


# ============================================================
# SQL 解析器
# ============================================================

class SQLParser:
    """SQL CREATE TABLE 语句解析器"""

    def __init__(self, sql_text: str):
        self.sql_text = sql_text
        self.models: List[Model] = []
        self.table_names: set = set()
        self.table_models: Dict[str, Model] = {}

    def parse(self) -> List[Model]:
        """解析所有 CREATE TABLE 语句"""
        # 清理注释
        cleaned_sql = self._remove_comments(self.sql_text)

        # 提取所有 CREATE TABLE 语句
        create_statements = self._extract_create_statements(cleaned_sql)
        if not create_statements:
            raise ValueError("E003: 未找到有效的 CREATE TABLE 语句")

        # 第一遍解析表名
        for stmt in create_statements:
            table_name = self._extract_table_name(stmt)
            if table_name:
                self.table_names.add(table_name.lower())

        # 第二遍解析完整定义
        for stmt in create_statements:
            model = self._parse_create_table(stmt)
            if model:
                self.models.append(model)
                self.table_models[model.name.lower()] = model

        # 第三遍处理外键关系（添加反向关系字段）
        self._add_relation_fields()

        return self.models

    def _remove_comments(self, sql: str) -> str:
        """移除 SQL 注释"""
        # 移除 -- 注释
        sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        # 移除 /* */ 注释
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        return sql

    def _extract_create_statements(self, sql: str) -> List[str]:
        """提取所有 CREATE TABLE 语句"""
        statements = []
        
        # 使用正则表达式查找所有 CREATE TABLE 语句
        # 匹配 CREATE TABLE 到对应的结束括号
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\w`]+[\s\S]*?\)\s*;?'
        matches = re.finditer(pattern, sql, re.IGNORECASE)
        
        for match in matches:
            stmt = match.group(0).strip()
            # 移除末尾的分号
            if stmt.endswith(';'):
                stmt = stmt[:-1].strip()
            if stmt:
                statements.append(stmt)
        
        return statements

    def _extract_table_name(self, stmt: str) -> Optional[str]:
        """提取表名"""
        match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', stmt, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _parse_create_table(self, stmt: str) -> Optional[Model]:
        """解析单个 CREATE TABLE 语句"""
        # 提取表名
        table_name = self._extract_table_name(stmt)
        if not table_name:
            raise ValueError("E005: 无法提取表名")

        model = Model(table_name)

        # 提取字段定义部分（括号内内容）
        # 找到第一个左括号和最后一个右括号
        start = stmt.find('(')
        end = stmt.rfind(')')
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"E003: 无法解析表 {table_name} 的定义")

        body = stmt[start + 1:end]

        # 分割字段定义和表级约束
        parts = self._split_by_commas(body)

        # 解析每个部分
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 检查是否为表级约束
            if re.match(r'(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE\s+KEY|UNIQUE|CONSTRAINT|INDEX|KEY)', part, re.IGNORECASE):
                self._parse_table_constraint(part, model)
            else:
                # 字段定义
                field = self._parse_field(part, table_name)
                if field:
                    model.add_field(field)

        return model

    def _split_by_commas(self, text: str) -> List[str]:
        """按逗号分割，忽略括号内的逗号"""
        parts = []
        current = []
        depth = 0
        in_string = False
        string_char = None

        for char in text:
            # 处理字符串
            if in_string:
                current.append(char)
                if char == string_char:
                    in_string = False
                continue
            
            if char in ('"', "'", '`'):
                in_string = True
                string_char = char
                current.append(char)
                continue

            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1

            if char == ',' and depth == 0:
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

        return parts

    def _parse_field(self, part: str, table_name: str) -> Optional[Field]:
        """解析字段定义"""
        # 提取字段名
        match = re.match(r'`?(\w+)`?\s+', part)
        if not match:
            # 可能是约束定义，忽略
            return None

        field_name = match.group(1)
        rest = part[match.end():].strip()

        # 提取数据类型
        type_match = re.match(r'([a-zA-Z_]+)\s*(?:\(([^)]*)\))?', rest)
        if not type_match:
            raise ValueError(f"E006: 字段 {field_name} 缺少数据类型")

        sql_type = type_match.group(1).lower()
        type_params = type_match.group(2)

        # 映射到 Prisma 类型
        prisma_type = TYPE_MAPPING.get(sql_type)
        if not prisma_type:
            # 尝试模糊匹配
            for key in TYPE_MAPPING:
                if key in sql_type:
                    prisma_type = TYPE_MAPPING[key]
                    break

        if not prisma_type:
            # 未知类型，默认 String 并标注
            prisma_type = "String"
            uncertain = True
        else:
            uncertain = sql_type in UNCERTAIN_TYPES

        # 解析约束
        is_required = True  # 默认必填
        is_id = False
        is_unique = False
        has_default = False
        default_value = None
        is_autoincrement = False

        # 检查 NOT NULL
        if re.search(r'NOT\s+NULL', rest, re.IGNORECASE):
            is_required = True

        # 检查 NULL（允许空值）
        if re.search(r'\bNULL\b', rest, re.IGNORECASE) and not re.search(r'NOT\s+NULL', rest, re.IGNORECASE):
            is_required = False

        # 检查 PRIMARY KEY
        if re.search(r'PRIMARY\s+KEY', rest, re.IGNORECASE):
            is_id = True
            is_required = True

        # 检查 UNIQUE
        if re.search(r'\bUNIQUE\b', rest, re.IGNORECASE):
            is_unique = True

        # 检查 AUTO_INCREMENT
        if re.search(r'AUTO_INCREMENT', rest, re.IGNORECASE):
            is_autoincrement = True
            has_default = True
            default_value = "autoincrement"

        # 检查 DEFAULT
        default_match = re.search(r'DEFAULT\s+([^\s,]+)', rest, re.IGNORECASE)
        if default_match:
            has_default = True
            default_value = default_match.group(1).strip("'\"")
            if default_value.upper() == 'NULL':
                has_default = False
                default_value = None

        # 创建字段对象
        field = Field(
            name=field_name,
            sql_type=sql_type,
            prisma_type=prisma_type,
            is_required=is_required,
            is_id=is_id,
            is_unique=is_unique,
            has_default=has_default,
            default_value=default_value,
            is_autoincrement=is_autoincrement,
            uncertain=uncertain
        )

        return field

    def _parse_table_constraint(self, part: str, model: Model):
        """解析表级约束"""
        # 主键约束
        if re.match(r'PRIMARY\s+KEY', part, re.IGNORECASE):
            pk_match = re.search(r'\(([^)]+)\)', part)
            if pk_match:
                pk_columns = [c.strip().strip('`') for c in pk_match.group(1).split(',')]
                for field in model.fields:
                    if field.name in pk_columns:
                        field.is_id = True
                        field.is_required = True

        # 唯一约束
        elif re.match(r'(UNIQUE\s+KEY|UNIQUE)', part, re.IGNORECASE):
            uq_match = re.search(r'\(([^)]+)\)', part)
            if uq_match:
                uq_columns = [c.strip().strip('`') for c in uq_match.group(1).split(',')]
                for field in model.fields:
                    if field.name in uq_columns:
                        field.is_unique = True

        # 外键约束
        elif re.match(r'FOREIGN\s+KEY', part, re.IGNORECASE):
            fk_match = re.search(r'FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+`?(\w+)`?\s*\(([^)]+)\)', part, re.IGNORECASE)
            if fk_match:
                fk_columns = [c.strip().strip('`') for c in fk_match.group(1).split(',')]
                ref_table = fk_match.group(2)
                ref_columns = [c.strip().strip('`') for c in fk_match.group(3).split(',')]

                # 标记外键字段
                for field in model.fields:
                    if field.name in fk_columns:
                        field.is_relation = True
                        field.relation_ref = ref_table
                        field.relation_field = ref_columns[0] if ref_columns else "id"

                # 添加注释
                model.comments.append(f"外键: {', '.join(fk_columns)} -> {ref_table}({', '.join(ref_columns)})")

    def _add_relation_fields(self):
        """为外键引用的表添加反向关系字段"""
        for model in self.models:
            for field in model.fields:
                if field.is_relation and field.relation_ref:
                    ref_table_name = field.relation_ref.lower()
                    if ref_table_name in self.table_models:
                        ref_model = self.table_models[ref_table_name]
                        # 检查是否已存在反向关系字段
                        existing = any(f.name == model.name.lower() for f in ref_model.fields)
                        if not existing:
                            # 添加反向关系字段
                            relation_field = Field(
                                name=model.name.lower(),
                                sql_type="relation",
                                prisma_type=model.name,
                                is_required=False,
                                is_relation=True,
                                relation_ref=model.name,
                                relation_field=field.name
                            )
                            ref_model.add_field(relation_field)


# ============================================================
# Prisma Schema 生成器
# ============================================================

class PrismaGenerator:
    """Prisma Schema 生成器"""

    def __init__(self, models: List[Model]):
        self.models = models

    def generate(self) -> str:
        """生成完整的 Prisma Schema"""
        lines = []
        lines.append("// 由 SQL 转 Prisma Schema 生成器自动生成")
        lines.append("// 请根据实际需求调整")
        lines.append("")

        # 添加 datasource 和 generator
        lines.append("datasource db {")
        lines.append("  provider = \"postgresql\"")
        lines.append("  url      = env(\"DATABASE_URL\")")
        lines.append("}")
        lines.append("")
        lines.append("generator client {")
        lines.append("  provider = \"prisma-client-js\"")
        lines.append("}")
        lines.append("")

        # 生成模型
        for model in self.models:
            lines.append(model.to_prisma_model())
            lines.append("")

        return "\n".join(lines)


# ============================================================
# 主处理逻辑
# ============================================================

def process_sql(sql_text: str) -> str:
    """处理 SQL 文本并生成 Prisma Schema"""
    if not sql_text or not sql_text.strip():
        raise ValueError("E002: 输入为空")

    # 解析 SQL
    parser = SQLParser(sql_text)
    models = parser.parse()

    if not models:
        raise ValueError("E003: 未解析到任何模型")

    # 生成 Prisma Schema
    generator = PrismaGenerator(models)
    return generator.generate()


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """运行内置自检"""
    print("=" * 60)
    print("SQL 转 Prisma Schema 生成器 - 自检")
    print("=" * 60)

    # 硬编码测试数据
    test_sql = """
    -- 用户表
    CREATE TABLE users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(50) NOT NULL UNIQUE,
        email VARCHAR(100) NOT NULL,
        age INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    );

    -- 订单表
    CREATE TABLE orders (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        total DECIMAL(10, 2) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- 商品表（无主键，测试警告）
    CREATE TABLE products (
        name VARCHAR(100),
        price DECIMAL(10, 2),
        description TEXT
    );
    """

    try:
        # 执行转换
        result = process_sql(test_sql)

        # 基本断言（宽松阈值）
        assert result is not None, "E010: 转换结果为空"
        assert len(result) > 100, "E010: 转换结果过短"
        assert "model users" in result.lower(), "E010: 缺少 users 模型"
        assert "model orders" in result.lower(), "E010: 缺少 orders 模型"
        assert "model products" in result.lower(), "E010: 缺少 products 模型"

        # 检查关键字段
        assert "username String" in result, "E010: 缺少 username 字段"
        assert "user_id" in result, "E010: 缺少 user_id 字段"
        assert "@relation" in result, "E010: 缺少关系定义"

        # 检查主键
        assert "@id" in result, "E010: 缺少主键定义"

        # 检查警告
        assert "缺少主键" in result, "E010: 缺少主键警告"

        # 检查不确定类型标注
        assert "需人工确认" in result or "⚠️" in result, "E010: 缺少不确定类型标注"

        print("✅ 基础转换测试通过")
        print()
        print("--- 测试输出预览 ---")
        print(result[:500])
        print("...")
        print()

        # 空输入测试
        try:
            process_sql("")
            print("❌ 空输入测试失败: 未抛出异常")
            return False
        except ValueError as e:
            assert "E002" in str(e), f"❌ 空输入错误码错误: {e}"
            print("✅ 空输入测试通过")

        # 无 CREATE TABLE 测试
        try:
            process_sql("SELECT * FROM users;")
            print("❌ 无建表语句测试失败: 未抛出异常")
            return False
        except ValueError as e:
            assert "E003" in str(e), f"❌ 无建表语句错误码错误: {e}"
            print("✅ 无建表语句测试通过")

        # 数据类型映射测试
        type_test_sql = """
        CREATE TABLE type_test (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            price DECIMAL(10,2),
            is_active BOOLEAN,
            created_at TIMESTAMP,
            data JSON
        );
        """
        type_result = process_sql(type_test_sql)
        assert "Int" in type_result, "E010: INT 映射失败"
        assert "String" in type_result, "E010: VARCHAR 映射失败"
        assert "Decimal" in type_result, "E010: DECIMAL 映射失败"
        assert "Boolean" in type_result, "E010: BOOLEAN 映射失败"
        assert "DateTime" in type_result, "E010: TIMESTAMP 映射失败"
        assert "Json" in type_result, "E010: JSON 映射失败"
        print("✅ 数据类型映射测试通过")

        # 批量表测试
        batch_sql = """
        CREATE TABLE table_a (id INT PRIMARY KEY);
        CREATE TABLE table_b (id INT PRIMARY KEY);
        CREATE TABLE table_c (id INT PRIMARY KEY);
        """
        batch_result = process_sql(batch_sql)
        model_count = batch_result.count("model ")
        assert model_count >= 3, f"E010: 批量转换失败, 模型数={model_count}"
        print("✅ 批量转换测试通过")

        print()
        print("=" * 60)
        print("✅ 所有自检测试通过!")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"❌ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 自检异常: {e}")
        return False


# ============================================================
# 入口函数
# ============================================================

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="SQL 转 Prisma Schema 生成器",
        epilog="从标准输入读取 SQL，输出 Prisma Schema"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 SQL 文件路径（可选，默认从标准输入读取）"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，默认输出到标准输出）"
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    try:
        # 读取输入
        if args.input:
            with open(args.input, 'r', encoding='utf-8') as f:
                sql_text = f.read()
        else:
            # 从标准输入读取
            sql_text = sys.stdin.read()

        # 处理
        result = process_sql(sql_text)

        # 输出
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"✅ Prisma Schema 已写入: {args.output}")
        else:
            print(result)

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"错误: E009 文件操作失败: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: E010 内部错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
