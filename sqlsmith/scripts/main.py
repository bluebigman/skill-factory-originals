#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqlsmith - 随机 SQL 查询生成器（独立实现）

本脚本依据功能规格独立编写（clean-room），不包含任何既有代码。
仅使用标准库实现，无第三方依赖。

功能概述：
    1. 根据用户提供的表名、列信息等，生成随机 SQL 查询语句。
    2. 支持多种查询类型：简单选择、聚合、连接、子查询等。
    3. 提供 --selftest 参数进行离线自检，不依赖外部文件或网络。

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 参数解析失败
    E007 自检失败
    E008 未知查询类型
    E009 无效表名
    E010 无效列名
"""

import argparse
import random
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误处理模块
# ============================================================

class SqlSmithError(Exception):
    """自定义异常基类，携带错误码和消息。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def raise_error(code: str, message: str) -> None:
    """抛出带错误码的异常。"""
    raise SqlSmithError(code, message)


# ============================================================
# 数据模型与输入解析
# ============================================================

class Column:
    """列定义。"""
    def __init__(self, name: str, data_type: str):
        self.name = name
        self.data_type = data_type  # 如 int, text, real

    def __repr__(self) -> str:
        return f"Column({self.name}, {self.data_type})"


class Table:
    """表定义。"""
    def __init__(self, name: str, columns: List[Column]):
        self.name = name
        self.columns = columns

    def __repr__(self) -> str:
        return f"Table({self.name}, {self.columns})"


def parse_input(input_text: str) -> List[Table]:
    """
    解析用户输入，提取表结构信息。
    输入格式（每行一个表）：
        表名: 列名1:类型1, 列名2:类型2, ...
    示例：
        users: id:int, name:text, age:int
        orders: id:int, user_id:int, amount:real
    """
    if not input_text or not input_text.strip():
        raise_error("E001", "输入为空。请提供表结构信息，格式：表名: 列名:类型, ...")

    tables: List[Table] = []
    lines = [line.strip() for line in input_text.strip().splitlines() if line.strip()]

    for line in lines:
        if ":" not in line:
            raise_error("E003", f"输入格式错误，行缺少冒号分隔符: '{line}'。示例：users: id:int, name:text")

        parts = line.split(":", 1)
        table_name = parts[0].strip()
        cols_part = parts[1].strip()

        if not table_name:
            raise_error("E003", f"表名为空: '{line}'")

        if not cols_part:
            raise_error("E003", f"表 '{table_name}' 没有定义任何列")

        columns: List[Column] = []
        for col_item in cols_part.split(","):
            col_item = col_item.strip()
            if not col_item:
                continue
            if ":" not in col_item:
                raise_error("E003", f"列定义缺少冒号分隔符: '{col_item}'。示例：id:int")
            col_name, col_type = col_item.split(":", 1)
            col_name = col_name.strip()
            col_type = col_type.strip()
            if not col_name or not col_type:
                raise_error("E003", f"列名或类型为空: '{col_item}'")
            columns.append(Column(col_name, col_type))

        if not columns:
            raise_error("E003", f"表 '{table_name}' 没有有效列定义")

        tables.append(Table(table_name, columns))

    if not tables:
        raise_error("E001", "未能解析出任何表结构。")

    return tables


# ============================================================
# SQL 生成核心逻辑
# ============================================================

class SqlGenerator:
    """随机 SQL 查询生成器。"""

    # 支持的聚合函数
    AGG_FUNCS = ["COUNT", "SUM", "AVG", "MIN", "MAX"]

    # 支持的比较运算符
    COMPARE_OPS = ["=", "<>", ">", "<", ">=", "<="]

    # 支持的逻辑运算符
    LOGIC_OPS = ["AND", "OR"]

    def __init__(self, tables: List[Table], seed: Optional[int] = None):
        self.tables = tables
        self.rng = random.Random(seed)  # 可复现的随机

    def generate(self, query_type: str = "random") -> str:
        """根据类型生成 SQL 查询。"""
        if query_type == "random":
            # 随机选择一种类型
            types = ["simple", "aggregate", "join", "subquery"]
            query_type = self.rng.choice(types)

        if query_type == "simple":
            return self._gen_simple_select()
        elif query_type == "aggregate":
            return self._gen_aggregate_select()
        elif query_type == "join":
            return self._gen_join_select()
        elif query_type == "subquery":
            return self._gen_subquery_select()
        else:
            raise_error("E008", f"未知查询类型: '{query_type}'。可选: simple, aggregate, join, subquery, random")

    def _pick_table(self) -> Table:
        """随机选择一个表。"""
        if not self.tables:
            raise_error("E002", "没有可用表。")
        return self.rng.choice(self.tables)

    def _pick_column(self, table: Table) -> Column:
        """从表中随机选择一列。"""
        if not table.columns:
            raise_error("E002", f"表 '{table.name}' 没有列。")
        return self.rng.choice(table.columns)

    def _gen_where_clause(self, table: Table) -> Optional[str]:
        """生成 WHERE 子句（可能为空）。"""
        if not table.columns or self.rng.random() < 0.3:
            return None  # 30% 概率无 WHERE

        col = self._pick_column(table)
        op = self.rng.choice(self.COMPARE_OPS)
        value = self._gen_value_for_type(col.data_type)
        return f"WHERE {col.name} {op} {value}"

    def _gen_value_for_type(self, data_type: str) -> str:
        """根据列类型生成一个随机值。"""
        dt = data_type.lower().strip()
        if dt in ("int", "integer", "bigint", "smallint"):
            return str(self.rng.randint(0, 1000))
        elif dt in ("real", "float", "double", "numeric", "decimal"):
            return f"{self.rng.uniform(0, 1000):.2f}"
        elif dt in ("text", "varchar", "char", "string"):
            choices = ["'Alice'", "'Bob'", "'Charlie'", "'测试'", "'数据'", "'hello'"]
            return self.rng.choice(choices)
        elif dt in ("bool", "boolean"):
            return self.rng.choice(["TRUE", "FALSE"])
        elif dt in ("date", "datetime", "timestamp"):
            return f"DATE '{self.rng.randint(2000, 2024)}-{self.rng.randint(1, 12):02d}-{self.rng.randint(1, 28):02d}'"
        else:
            # 默认按文本处理
            return "'value'"

    def _gen_simple_select(self) -> str:
        """生成简单 SELECT 查询。"""
        table = self._pick_table()
        col = self._pick_column(table)
        where = self._gen_where_clause(table)
        limit = self.rng.randint(1, 100) if self.rng.random() < 0.7 else None

        sql = f"SELECT {col.name} FROM {table.name}"
        if where:
            sql += f" {where}"
        if limit:
            sql += f" LIMIT {limit}"
        return sql + ";"

    def _gen_aggregate_select(self) -> str:
        """生成聚合查询。"""
        table = self._pick_table()
        if not table.columns:
            raise_error("E002", f"表 '{table.name}' 没有列，无法聚合。")

        agg_func = self.rng.choice(self.AGG_FUNCS)
        col = self._pick_column(table)
        where = self._gen_where_clause(table)

        sql = f"SELECT {agg_func}({col.name}) FROM {table.name}"
        if where:
            sql += f" {where}"
        return sql + ";"

    def _gen_join_select(self) -> str:
        """生成 JOIN 查询（需要至少 2 张表）。"""
        if len(self.tables) < 2:
            raise_error("E004", "JOIN 查询需要至少 2 张表。当前仅提供 1 张表。")

        # 随机选择两张不同的表
        t1, t2 = self.rng.sample(self.tables, 2)

        # 尝试寻找可连接的列（同名同类型）
        join_cols = self._find_join_columns(t1, t2)
        if not join_cols:
            # 退化为 CROSS JOIN
            return f"SELECT * FROM {t1.name} CROSS JOIN {t2.name};"

        col1, col2 = join_cols
        join_type = self.rng.choice(["INNER", "LEFT", "RIGHT"])

        sql = f"SELECT * FROM {t1.name} {join_type} JOIN {t2.name} ON {t1.name}.{col1.name} = {t2.name}.{col2.name}"
        return sql + ";"

    def _find_join_columns(self, t1: Table, t2: Table) -> Optional[Tuple[Column, Column]]:
        """查找两张表之间的可连接列（同名同类型）。"""
        for c1 in t1.columns:
            for c2 in t2.columns:
                if c1.name == c2.name and c1.data_type == c2.data_type:
                    return c1, c2
        return None

    def _gen_subquery_select(self) -> str:
        """生成带子查询的 SELECT。"""
        if len(self.tables) < 1:
            raise_error("E002", "没有可用表。")

        outer = self._pick_table()
        inner = self._pick_table()

        # 子查询：SELECT 某列 FROM 表
        inner_col = self._pick_column(inner)
        subquery = f"(SELECT {inner_col.name} FROM {inner.name})"

        # 外层查询
        outer_col = self._pick_column(outer)
        op = self.rng.choice(["IN", "NOT IN"])
        where = f"WHERE {outer_col.name} {op} {subquery}"

        sql = f"SELECT {outer_col.name} FROM {outer.name} {where}"
        return sql + ";"


# ============================================================
# 自检模块（内置硬编码样例数据）
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑正确性。
    使用硬编码数据，不依赖外部文件、网络或当前工作目录。
    使用宽松断言（大小比较/区间判断），确保稳定通过。
    """
    print("[自检] 开始离线自检...")

    # 内置样例数据
    sample_input = """
    users: id:int, name:text, age:int
    orders: id:int, user_id:int, amount:real
    products: id:int, name:text, price:real
    """

    try:
        # 测试 1: 输入解析
        print("[自检] 测试输入解析...")
        tables = parse_input(sample_input)
        assert len(tables) == 3, f"预期 3 张表，实际 {len(tables)}"
        assert tables[0].name == "users", f"第一张表应为 users，实际 {tables[0].name}"
        assert len(tables[0].columns) == 3, f"users 表应有 3 列，实际 {len(tables[0].columns)}"
        assert tables[1].name == "orders", f"第二张表应为 orders，实际 {tables[1].name}"
        assert tables[2].name == "products", f"第三张表应为 products，实际 {tables[2].name}"
        print("  [通过] 输入解析正确")

        # 测试 2: 各类查询生成
        print("[自检] 测试简单查询...")
        gen = SqlGenerator(tables, seed=42)
        for _ in range(20):
            sql = gen.generate("simple")
            assert sql.endswith(";"), f"SQL 应以分号结尾: {sql}"
            assert "SELECT" in sql.upper(), f"应为 SELECT 查询: {sql}"
            assert "users" in sql or "orders" in sql or "products" in sql, f"应包含表名: {sql}"
        print("  [通过] 简单查询生成正确")

        print("[自检] 测试聚合查询...")
        for _ in range(20):
            sql = gen.generate("aggregate")
            assert sql.endswith(";"), f"SQL 应以分号结尾: {sql}"
            assert any(func in sql.upper() for func in gen.AGG_FUNCS), f"应包含聚合函数: {sql}"
        print("  [通过] 聚合查询生成正确")

        print("[自检] 测试 JOIN 查询...")
        join_count = 0
        for _ in range(50):
            try:
                sql = gen.generate("join")
                assert sql.endswith(";"), f"SQL 应以分号结尾: {sql}"
                assert "JOIN" in sql.upper(), f"应包含 JOIN: {sql}"
                join_count += 1
            except SqlSmithError as e:
                # JOIN 可能因列不匹配退化为 CROSS JOIN，也属于合法输出
                if e.code == "E004":
                    continue  # 表不足时跳过
                else:
                    raise
        assert join_count > 0, "应至少生成一个 JOIN 查询"
        print(f"  [通过] JOIN 查询生成正确（成功 {join_count} 次）")

        print("[自检] 测试子查询...")
        for _ in range(20):
            sql = gen.generate("subquery")
            assert sql.endswith(";"), f"SQL 应以分号结尾: {sql}"
            assert "(" in sql and ")" in sql, f"应包含子查询括号: {sql}"
            assert "IN" in sql.upper() or "NOT IN" in sql.upper(), f"应包含 IN 或 NOT IN: {sql}"
        print("  [通过] 子查询生成正确")

        # 测试 3: 随机生成
        print("[自检] 测试随机生成...")
        for _ in range(50):
            sql = gen.generate("random")
            assert sql.endswith(";"), f"SQL 应以分号结尾: {sql}"
            assert "SELECT" in sql.upper(), f"应为 SELECT 查询: {sql}"
        print("  [通过] 随机生成正确")

        # 测试 4: 错误处理
        print("[自检] 测试错误处理...")
        try:
            parse_input("")
            assert False, "空输入应抛出 E001"
        except SqlSmithError as e:
            assert e.code == "E001", f"空输入应返回 E001，实际 {e.code}"

        try:
            parse_input("invalid_line_without_colon")
            assert False, "无冒号行应抛出 E003"
        except SqlSmithError as e:
            assert e.code == "E003", f"格式错误应返回 E003，实际 {e.code}"

        try:
            gen = SqlGenerator([])
            gen.generate("simple")
            assert False, "空表应抛出 E002"
        except SqlSmithError as e:
            assert e.code == "E002", f"空表应返回 E002，实际 {e.code}"

        try:
            gen = SqlGenerator(tables)
            gen.generate("unknown_type")
            assert False, "未知类型应抛出 E008"
        except SqlSmithError as e:
            assert e.code == "E008", f"未知类型应返回 E008，实际 {e.code}"
        print("  [通过] 错误处理正确")

        # 测试 5: 可复现性（相同种子生成相同结果）
        print("[自检] 测试可复现性...")
        gen1 = SqlGenerator(tables, seed=123)
        gen2 = SqlGenerator(tables, seed=123)
        sql1 = gen1.generate("simple")
        sql2 = gen2.generate("simple")
        assert sql1 == sql2, "相同种子应生成相同查询"
        print("  [通过] 可复现性正确")

        print("[自检] 全部通过！")
        return True

    except AssertionError as e:
        print(f"[自检] 失败: {e}")
        raise_error("E007", f"自检断言失败: {e}")
        return False
    except SqlSmithError as e:
        print(f"[自检] 失败: [{e.code}] {e.message}")
        return False
    except Exception as e:
        print(f"[自检] 意外错误: {e}")
        raise_error("E007", f"自检异常: {e}")
        return False


# ============================================================
# 主程序入口
# ============================================================

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="sqlsmith - 随机 SQL 查询生成器",
        epilog="示例: echo 'users: id:int, name:text' | python scripts/main.py"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置数据，不依赖外部环境）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="表结构输入。格式：表名: 列名:类型, 列名:类型（多表用换行分隔）"
    )
    parser.add_argument(
        "--type",
        type=str,
        default="random",
        choices=["simple", "aggregate", "join", "subquery", "random"],
        help="查询类型（默认 random）"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子（用于复现）"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="生成查询数量（默认 1）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常模式：从命令行参数或 stdin 读取输入
    try:
        input_text = args.input
        if not input_text:
            # 从 stdin 读取
            input_text = sys.stdin.read()

        if not input_text or not input_text.strip():
            raise_error("E001", "输入为空。请提供表结构信息，或使用 --input 参数。")

        # 解析输入
        tables = parse_input(input_text)

        # 检查参数
        if args.count < 1:
            raise_error("E003", f"count 必须为正整数，实际 {args.count}")

        # 生成查询
        generator = SqlGenerator(tables, seed=args.seed)
        for i in range(args.count):
            sql = generator.generate(args.type)
            print(sql)

        return 0

    except SqlSmithError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
