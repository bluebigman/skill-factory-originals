#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sql-query-generator 技能实现脚本
================================
将自然语言或数据文件转换为可执行的SQL查询语句，支持无模式数据源。

本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例:
    python scripts/main.py --selftest                     # 离线自检
    python scripts/main.py --infer-schema data.csv        # 推断表结构
    python scripts/main.py --generate "查询订单量前10的商品" --dialect mysql

错误码:
    E001: 参数解析错误
    E002: 文件读取失败
    E003: 不支持的方言
    E004: 自然语言解析失败
    E005: 字段类型推断失败
    E006: 无效的SQL标识符
    E007: 数据为空或结构无效
    E008: 生成SQL失败
    E009: 自检失败
    E010: 未预期的运行时错误
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 支持的数据库方言
SUPPORTED_DIALECTS = {"mysql", "postgresql", "sqlite", "sqlserver"}

# 方言对应的分页语法模板
PAGINATION_TEMPLATES = {
    "mysql": "LIMIT {limit} OFFSET {offset}",
    "postgresql": "LIMIT {limit} OFFSET {offset}",
    "sqlite": "LIMIT {limit} OFFSET {offset}",
    "sqlserver": "OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY",
}

# 方言对应的字符串拼接方式
CONCAT_FUNCTIONS = {
    "mysql": "CONCAT({fields})",
    "postgresql": "{fields} || ",
    "sqlite": "{fields} || ",
    "sqlserver": "CONCAT({fields})",
}

# 常见字段类型映射（用于结构推断）
FIELD_TYPE_MAPPING = {
    "int": "INTEGER",
    "integer": "INTEGER",
    "float": "FLOAT",
    "double": "FLOAT",
    "decimal": "DECIMAL(10,2)",
    "str": "VARCHAR(255)",
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "date": "DATE",
    "datetime": "TIMESTAMP",
    "bool": "BOOLEAN",
    "boolean": "BOOLEAN",
}

# 关键词与SQL操作的映射（自然语言解析用）
KEYWORD_ACTION_MAP = {
    "查询": "SELECT",
    "选择": "SELECT",
    "统计": "SELECT COUNT",
    "计算": "SELECT",
    "求和": "SELECT SUM",
    "平均": "SELECT AVG",
    "最大值": "SELECT MAX",
    "最小值": "SELECT MIN",
    "按": "GROUP BY",
    "分组": "GROUP BY",
    "排序": "ORDER BY",
    "过滤": "WHERE",
    "条件": "WHERE",
    "分页": "LIMIT",
    "前": "LIMIT",
    "最近": "DATE_FILTER",
    "包含": "LIKE",
    "等于": "=",
    "大于": ">",
    "小于": "<",
}


# ============================================================
# 工具函数
# ============================================================

def validate_identifier(identifier: str) -> bool:
    """校验是否为合法的SQL标识符。"""
    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    return bool(re.match(pattern, identifier))


def safe_quote_identifier(identifier: str, dialect: str = "mysql") -> str:
    """根据方言安全地引用标识符。"""
    if not validate_identifier(identifier):
        raise ValueError(f"E006: 无效的SQL标识符: {identifier}")
    if dialect == "mysql":
        return f"`{identifier}`"
    elif dialect == "sqlserver":
        return f"[{identifier}]"
    else:
        return f'"{identifier}"'


def infer_field_type(value: Any) -> str:
    """从单个值推断字段类型。"""
    if value is None:
        return "TEXT"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, float):
        return "FLOAT"
    if isinstance(value, datetime):
        return "TIMESTAMP"
    if isinstance(value, (dict, list)):
        return "JSON"
    
    # 处理字符串值，尝试识别数字
    if isinstance(value, str):
        # 去除可能的空格
        str_value = value.strip()
        if str_value:
            # 尝试解析为整数
            try:
                int(str_value)
                return "INTEGER"
            except ValueError:
                pass
            # 尝试解析为浮点数
            try:
                float(str_value)
                return "FLOAT"
            except ValueError:
                pass
            # 尝试解析为布尔值
            if str_value.lower() in ("true", "false"):
                return "BOOLEAN"
            # 尝试解析为日期时间
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    datetime.strptime(str_value, fmt)
                    return "TIMESTAMP" if " " in str_value or "T" in str_value else "DATE"
                except ValueError:
                    continue
    
    return "VARCHAR(255)"


def normalize_date_filter(text: str) -> Optional[Tuple[int, str]]:
    """从自然语言中提取日期过滤条件，返回(天数, 日期字段名)。"""
    # 匹配"最近N天"模式
    match = re.search(r"最近(\d+)天", text)
    if match:
        days = int(match.group(1))
        # 查找可能的日期字段名
        field_match = re.search(r"(?:的|按)?([a-zA-Z_][a-zA-Z0-9_]*日期|date|created_at|时间)", text, re.IGNORECASE)
        field = field_match.group(1) if field_match else "created_at"
        return days, field
    return None


def parse_top_n(text: str) -> Optional[int]:
    """从自然语言中提取"前N"的数量。"""
    match = re.search(r"前(\d+)", text)
    if match:
        return int(match.group(1))
    # 匹配"top N"模式
    match = re.search(r"top\s*(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parse_order_direction(text: str) -> str:
    """判断排序方向。"""
    if "降序" in text or "倒序" in text or "desc" in text.lower():
        return "DESC"
    return "ASC"


def extract_fields(text: str) -> List[str]:
    """从自然语言中提取可能的字段名（简单启发式）。"""
    # 常见字段名模式
    field_patterns = [
        r"([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)",
    ]
    fields = []
    for pattern in field_patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            # 过滤掉常见词
            if m.lower() not in {"select", "from", "where", "group", "order", "by", "limit", "and", "or", "not", "in", "like", "as", "on", "join", "left", "right", "inner", "outer", "full", "cross", "union", "all", "distinct", "count", "sum", "avg", "max", "min", "top", "desc", "asc"}:
                if m not in fields:
                    fields.append(m)
    return fields


# ============================================================
# 核心功能类
# ============================================================

class SchemaInferencer:
    """从数据文件推断表结构。"""

    @staticmethod
    def from_csv(filepath: str, sample_size: int = 100) -> Dict[str, Any]:
        """从CSV文件推断结构。"""
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("E007: CSV文件没有字段名")
                fields = reader.fieldnames
                type_map: Dict[str, str] = {}
                for i, row in enumerate(reader):
                    if i >= sample_size:
                        break
                    for field in fields:
                        value = row.get(field)
                        inferred = infer_field_type(value)
                        if field not in type_map:
                            type_map[field] = inferred
                        elif type_map[field] != inferred:
                            # 类型冲突时升级为更通用的类型
                            if type_map[field] == "INTEGER" and inferred == "FLOAT":
                                type_map[field] = "FLOAT"
                            elif type_map[field] in ("INTEGER", "FLOAT") and inferred == "VARCHAR(255)":
                                type_map[field] = "VARCHAR(255)"
                            elif type_map[field] in ("INTEGER", "FLOAT", "VARCHAR(255)") and inferred in ("DATE", "TIMESTAMP"):
                                type_map[field] = "VARCHAR(255)"
                return {"table_name": os.path.splitext(os.path.basename(filepath))[0], "fields": type_map}
        except FileNotFoundError:
            raise FileNotFoundError("E002: 文件不存在")
        except Exception as e:
            raise ValueError(f"E005: 字段类型推断失败: {str(e)}")

    @staticmethod
    def from_json(filepath: str, sample_size: int = 100) -> Dict[str, Any]:
        """从JSON文件推断结构。"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                if not data:
                    raise ValueError("E007: JSON数组为空")
                sample = data[:sample_size]
                type_map: Dict[str, str] = {}
                for item in sample:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            inferred = infer_field_type(value)
                            if key not in type_map:
                                type_map[key] = inferred
                            elif type_map[key] != inferred:
                                if type_map[key] == "INTEGER" and inferred == "FLOAT":
                                    type_map[key] = "FLOAT"
                                elif type_map[key] in ("INTEGER", "FLOAT") and inferred == "VARCHAR(255)":
                                    type_map[key] = "VARCHAR(255)"
                                elif type_map[key] in ("INTEGER", "FLOAT", "VARCHAR(255)") and inferred in ("DATE", "TIMESTAMP"):
                                    type_map[key] = "VARCHAR(255)"
                return {"table_name": os.path.splitext(os.path.basename(filepath))[0], "fields": type_map}
            elif isinstance(data, dict):
                type_map = {k: infer_field_type(v) for k, v in data.items()}
                return {"table_name": os.path.splitext(os.path.basename(filepath))[0], "fields": type_map}
            else:
                raise ValueError("E007: JSON数据不是对象或数组")
        except FileNotFoundError:
            raise FileNotFoundError("E002: 文件不存在")
        except json.JSONDecodeError:
            raise ValueError("E007: JSON解析失败")
        except Exception as e:
            raise ValueError(f"E005: 字段类型推断失败: {str(e)}")


class SQLGenerator:
    """SQL查询生成器。"""

    def __init__(self, dialect: str = "mysql"):
        if dialect not in SUPPORTED_DIALECTS:
            raise ValueError(f"E003: 不支持的方言: {dialect}，支持: {', '.join(SUPPORTED_DIALECTS)}")
        self.dialect = dialect

    def generate_create_table(self, table_name: str, fields: Dict[str, str]) -> str:
        """生成CREATE TABLE语句。"""
        if not validate_identifier(table_name):
            raise ValueError(f"E006: 无效的表名: {table_name}")
        if not fields:
            raise ValueError("E007: 字段列表为空")

        quoted_table = safe_quote_identifier(table_name, self.dialect)
        columns = []
        for field_name, field_type in fields.items():
            if not validate_identifier(field_name):
                raise ValueError(f"E006: 无效的字段名: {field_name}")
            quoted_field = safe_quote_identifier(field_name, self.dialect)
            columns.append(f"    {quoted_field} {field_type}")

        return f"CREATE TABLE {quoted_table} (\n" + ",\n".join(columns) + "\n);"

    def generate_select(
        self,
        table_name: str,
        fields: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
        group_by: Optional[List[str]] = None,
        order_by: Optional[List[Tuple[str, str]]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        aggregate: Optional[str] = None,
    ) -> str:
        """生成SELECT查询语句。"""
        if not validate_identifier(table_name):
            raise ValueError(f"E006: 无效的表名: {table_name}")

        quoted_table = safe_quote_identifier(table_name, self.dialect)

        # 选择字段
        if aggregate:
            select_clause = f"SELECT {aggregate}"
        elif fields:
            quoted_fields = [safe_quote_identifier(f, self.dialect) for f in fields]
            select_clause = "SELECT " + ", ".join(quoted_fields)
        else:
            select_clause = "SELECT *"

        # FROM
        from_clause = f"FROM {quoted_table}"

        # WHERE
        where_clause_str = ""
        if where_clause:
            where_clause_str = f"WHERE {where_clause}"

        # GROUP BY
        group_clause = ""
        if group_by:
            quoted_group = [safe_quote_identifier(g, self.dialect) for g in group_by]
            group_clause = "GROUP BY " + ", ".join(quoted_group)

        # ORDER BY
        order_clause = ""
        if order_by:
            order_parts = []
            for field, direction in order_by:
                quoted_field = safe_quote_identifier(field, self.dialect)
                order_parts.append(f"{quoted_field} {direction}")
            order_clause = "ORDER BY " + ", ".join(order_parts)

        # LIMIT
        limit_clause = ""
        if limit is not None:
            if self.dialect == "sqlserver":
                if not order_clause:
                    # SQL Server需要ORDER BY才能使用OFFSET FETCH
                    order_clause = "ORDER BY (SELECT NULL)"
                limit_clause = PAGINATION_TEMPLATES[self.dialect].format(limit=limit, offset=offset)
            else:
                limit_clause = PAGINATION_TEMPLATES[self.dialect].format(limit=limit, offset=offset)

        # 组装
        parts = [select_clause, from_clause]
        if where_clause_str:
            parts.append(where_clause_str)
        if group_clause:
            parts.append(group_clause)
        if order_clause:
            parts.append(order_clause)
        if limit_clause:
            parts.append(limit_clause)

        return " ".join(parts) + ";"

    def generate_from_natural_language(self, text: str, table_name: str = "table") -> str:
        """从自然语言生成SQL查询。"""
        try:
            # 提取字段
            fields = extract_fields(text)
            # 过滤掉可能的表名
            fields = [f for f in fields if f != table_name]

            # 提取排序
            order_by = []
            if "排序" in text or "order" in text.lower():
                order_fields = [f for f in fields if f not in ("date", "时间")]
                if order_fields:
                    direction = parse_order_direction(text)
                    order_by.append((order_fields[0], direction))

            # 提取LIMIT
            limit = parse_top_n(text)

            # 提取日期过滤
            where_parts = []
            date_filter = normalize_date_filter(text)
            if date_filter:
                days, date_field = date_filter
                if self.dialect == "mysql":
                    where_parts.append(f"{date_field} >= DATE_SUB(NOW(), INTERVAL {days} DAY)")
                elif self.dialect == "postgresql":
                    where_parts.append(f"{date_field} >= NOW() - INTERVAL '{days} days'")
                elif self.dialect == "sqlite":
                    where_parts.append(f"{date_field} >= datetime('now', '-{days} days')")
                elif self.dialect == "sqlserver":
                    where_parts.append(f"{date_field} >= DATEADD(day, -{days}, GETDATE())")

            # 提取聚合
            aggregate = None
            if "统计" in text or "count" in text.lower():
                agg_field = fields[0] if fields else "*"
                aggregate = f"COUNT({agg_field})"
            elif "求和" in text or "sum" in text.lower():
                agg_field = fields[0] if fields else "*"
                aggregate = f"SUM({agg_field})"
            elif "平均" in text or "avg" in text.lower():
                agg_field = fields[0] if fields else "*"
                aggregate = f"AVG({agg_field})"
            elif "最大" in text or "max" in text.lower():
                agg_field = fields[0] if fields else "*"
                aggregate = f"MAX({agg_field})"
            elif "最小" in text or "min" in text.lower():
                agg_field = fields[0] if fields else "*"
                aggregate = f"MIN({agg_field})"

            # 提取GROUP BY
            group_by = None
            if "分组" in text or "group" in text.lower():
                if fields:
                    group_by = [fields[0]]

            # 生成SQL
            return self.generate_select(
                table_name=table_name,
                fields=fields if not aggregate else None,
                where_clause=" AND ".join(where_parts) if where_parts else None,
                group_by=group_by,
                order_by=order_by,
                limit=limit,
                aggregate=aggregate,
            )
        except Exception as e:
            if str(e).startswith("E"):
                raise
            raise ValueError(f"E004: 自然语言解析失败: {str(e)}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """内置硬编码样例数据离线自检核心逻辑。"""
    print("=== SQL Query Generator 自检开始 ===")
    try:
        # 测试1: Schema推断（使用内置数据）
        print("\n[测试1] 字段类型推断")
        test_values = [1, 1.5, "text", True, None, datetime(2024, 1, 1)]
        inferred_types = [infer_field_type(v) for v in test_values]
        assert inferred_types[0] == "INTEGER", f"整数推断失败: {inferred_types[0]}"
        assert inferred_types[1] == "FLOAT", f"浮点推断失败: {inferred_types[1]}"
        assert "VARCHAR" in inferred_types[2], f"字符串推断失败: {inferred_types[2]}"
        assert inferred_types[3] == "BOOLEAN", f"布尔推断失败: {inferred_types[3]}"
        assert inferred_types[4] == "TEXT", f"None推断失败: {inferred_types[4]}"
        assert inferred_types[5] == "TIMESTAMP", f"时间推断失败: {inferred_types[5]}"
        print("  字段类型推断通过")

        # 测试2: 标识符校验
        print("\n[测试2] 标识符校验")
        assert validate_identifier("valid_name") is True
        assert validate_identifier("_valid1") is True
        assert validate_identifier("1invalid") is False
        assert validate_identifier("invalid-name") is False
        print("  标识符校验通过")

        # 测试3: CREATE TABLE生成（所有方言）
        print("\n[测试3] CREATE TABLE生成")
        schema = {"id": "INTEGER", "name": "VARCHAR(255)", "price": "FLOAT"}
        for dialect in SUPPORTED_DIALECTS:
            gen = SQLGenerator(dialect)
            sql = gen.generate_create_table("products", schema)
            assert "CREATE TABLE" in sql.upper(), f"{dialect} CREATE TABLE失败"
            assert "products" in sql, f"{dialect} 表名缺失"
            assert "id" in sql and "name" in sql and "price" in sql, f"{dialect} 字段缺失"
        print("  CREATE TABLE生成通过")

        # 测试4: SELECT生成（所有方言）
        print("\n[测试4] SELECT生成")
        for dialect in SUPPORTED_DIALECTS:
            gen = SQLGenerator(dialect)
            sql = gen.generate_select(
                table_name="orders",
                fields=["id", "amount"],
                where_clause="amount > 100",
                order_by=[("id", "DESC")],
                limit=10,
            )
            assert "SELECT" in sql.upper(), f"{dialect} SELECT缺失"
            assert "FROM" in sql.upper(), f"{dialect} FROM缺失"
            assert "WHERE" in sql.upper(), f"{dialect} WHERE缺失"
            assert "ORDER BY" in sql.upper(), f"{dialect} ORDER BY缺失"
            assert "LIMIT" in sql.upper() or "OFFSET" in sql.upper(), f"{dialect} 分页缺失"
        print("  SELECT生成通过")

        # 测试5: 自然语言转SQL
        print("\n[测试5] 自然语言转SQL")
        gen = SQLGenerator("mysql")
        # 测试查询前10
        sql = gen.generate_from_natural_language("查询订单量前10的商品", "orders")
        assert "SELECT" in sql.upper(), "自然语言转换失败: 缺少SELECT"
        assert "LIMIT 10" in sql.upper(), f"自然语言转换失败: 缺少LIMIT 10, got: {sql}"
        # 测试日期过滤
        sql = gen.generate_from_natural_language("查询最近7天的订单", "orders")
        assert "DATE_SUB" in sql.upper(), f"日期过滤失败: {sql}"
        assert "7" in sql, f"日期天数缺失: {sql}"
        # 测试聚合
        sql = gen.generate_from_natural_language("统计用户数量", "users")
        assert "COUNT" in sql.upper(), f"聚合失败: {sql}"
        print("  自然语言转SQL通过")

        # 测试6: 分页语法（SQL Server特殊处理）
        print("\n[测试6] SQL Server分页")
        gen = SQLGenerator("sqlserver")
        sql = gen.generate_select("table", limit=10, offset=20)
        assert "OFFSET 20 ROWS" in sql, f"SQL Server OFFSET失败: {sql}"
        assert "FETCH NEXT 10 ROWS ONLY" in sql, f"SQL Server FETCH失败: {sql}"
        print("  SQL Server分页通过")

        # 测试7: 错误处理
        print("\n[测试7] 错误处理")
        try:
            SQLGenerator("unknown_dialect")
            assert False, "应抛出E003错误"
        except ValueError as e:
            assert "E003" in str(e), f"错误码错误: {e}"

        try:
            gen = SQLGenerator("mysql")
            gen.generate_select("invalid-table")
            assert False, "应抛出E006错误"
        except ValueError as e:
            assert "E006" in str(e), f"错误码错误: {e}"
        print("  错误处理通过")

        # 测试8: CSV结构推断（使用硬编码数据模拟）
        print("\n[测试8] CSV结构推断")
        import io
        csv_data = "id,name,price,created_at\n1,apple,1.5,2024-01-01\n2,banana,2.0,2024-01-02\n"
        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames
        assert fieldnames == ["id", "name", "price", "created_at"], f"CSV字段名错误: {fieldnames}"
        type_map = {}
        for row in reader:
            for field in fieldnames:
                inferred = infer_field_type(row[field])
                if field not in type_map:
                    type_map[field] = inferred
        assert type_map["id"] == "INTEGER", f"id类型错误: {type_map['id']}"
        assert "VARCHAR" in type_map["name"], f"name类型错误: {type_map['name']}"
        assert type_map["price"] == "FLOAT", f"price类型错误: {type_map['price']}"
        print("  CSV结构推断通过")

        print("\n=== 自检全部通过 ===")
        return True
    except AssertionError as e:
        print(f"\n自检失败: {e}")
        return False
    except Exception as e:
        print(f"\n自检异常: E010: {str(e)}")
        return False


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="数据查询 SQL 语句生成器",
        epilog="示例: python scripts/main.py --selftest",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--infer-schema", metavar="FILE", help="从数据文件推断表结构（支持CSV/JSON）")
    parser.add_argument("--generate", metavar="TEXT", help="从自然语言生成SQL查询")
    parser.add_argument("--table", default="table", help="表名（默认: table）")
    parser.add_argument("--dialect", default="mysql", choices=sorted(SUPPORTED_DIALECTS), help="数据库方言")
    parser.add_argument("--fields", nargs="*", help="字段列表（用于SELECT）")
    parser.add_argument("--where", help="WHERE条件")
    parser.add_argument("--order-by", nargs=2, action="append", metavar=("FIELD", "DIR"), help="排序字段和方向")
    parser.add_argument("--limit", type=int, help="限制返回行数")
    parser.add_argument("--offset", type=int, default=0, help="偏移量")

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            success = run_selftest()
            return 0 if success else 1

        # 结构推断模式
        if args.infer_schema:
            filepath = args.infer_schema
            if not os.path.exists(filepath):
                print(f"E002: 文件不存在: {filepath}", file=sys.stderr)
                return 1

            ext = os.path.splitext(filepath)[1].lower()
            try:
                if ext == ".csv":
                    schema = SchemaInferencer.from_csv(filepath)
                elif ext == ".json":
                    schema = SchemaInferencer.from_json(filepath)
                else:
                    print(f"E007: 不支持的文件类型: {ext}，仅支持CSV/JSON", file=sys.stderr)
                    return 1

                gen = SQLGenerator(args.dialect)
                create_sql = gen.generate_create_table(schema["table_name"], schema["fields"])
                print(f"# 推断的表结构: {schema['table_name']}")
                print(f"# 字段: {', '.join(schema['fields'].keys())}")
                print()
                print(create_sql)
                return 0
            except (FileNotFoundError, ValueError) as e:
                print(str(e), file=sys.stderr)
                return 1

        # 自然语言生成模式
        if args.generate:
            gen = SQLGenerator(args.dialect)
            sql = gen.generate_from_natural_language(args.generate, args.table)
            print(sql)
            return 0

        # 手动参数生成模式
        if args.fields or args.where or args.order_by or args.limit is not None:
            gen = SQLGenerator(args.dialect)
            sql = gen.generate_select(
                table_name=args.table,
                fields=args.fields,
                where_clause=args.where,
                order_by=args.order_by,
                limit=args.limit,
                offset=args.offset,
            )
            print(sql)
            return 0

        # 无参数时显示帮助
        parser.print_help()
        return 0

    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未预期的运行时错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
