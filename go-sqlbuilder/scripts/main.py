#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于 go-sqlbuilder 功能规格的独立实现（clean-room）。
提供 SQL 查询生成器的核心逻辑、命令行接口与离线自检。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# 错误码定义
# --------------------------------------------------------------------------- #
ERROR_CODES: Dict[str, str] = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "不支持的表名或字段",
    "E007": "SQL 生成失败",
    "E008": "参数类型错误",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class SQLBuilderError(Exception):
    """带错误码的异常类。"""

    def __init__(self, code: str, message: Optional[str] = None) -> None:
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# --------------------------------------------------------------------------- #
# 核心数据结构
# --------------------------------------------------------------------------- #
class QuerySpec:
    """SQL 查询的规格对象，描述一次查询的各个组成部分。"""

    def __init__(self) -> None:
        self.table: Optional[str] = None
        self.columns: List[str] = []
        self.conditions: List[str] = []
        self.order_by: List[str] = []
        self.group_by: List[str] = []
        self.limit: Optional[int] = None
        self.offset: Optional[int] = None
        self.distinct: bool = False
        self.join_clauses: List[str] = []

    def has_content(self) -> bool:
        """判断是否至少包含一个有效查询要素。"""
        return bool(
            self.table
            or self.columns
            or self.conditions
            or self.order_by
            or self.group_by
            or self.join_clauses
            or self.limit is not None
            or self.offset is not None
        )


# --------------------------------------------------------------------------- #
# 输入解析模块
# --------------------------------------------------------------------------- #
def parse_input(raw_input: Any) -> QuerySpec:
    """
    将用户输入解析为 QuerySpec 对象。

    支持两种输入形式：
      1. 字典形式：{"table": "users", "columns": ["id", "name"], ...}
      2. 字符串形式：自然语言或简单描述（此处按最小规则提取表名）

    参数:
        raw_input: 用户提供的原始输入。

    返回:
        QuerySpec 对象。

    异常:
        SQLBuilderError: E001 输入为空；E003 格式错误；E002 关键信息缺失。
    """
    if raw_input is None:
        raise SQLBuilderError("E001")

    # 字典输入
    if isinstance(raw_input, dict):
        spec = QuerySpec()
        table = raw_input.get("table") or raw_input.get("表")
        if table is None:
            raise SQLBuilderError("E002", "缺少表名（table）")
        if not isinstance(table, str) or not table.strip():
            raise SQLBuilderError("E003", "表名必须是有效字符串")
        spec.table = table.strip()

        # 列
        cols = raw_input.get("columns") or raw_input.get("列")
        if cols is not None:
            if not isinstance(cols, list) or not all(isinstance(c, str) for c in cols):
                raise SQLBuilderError("E003", "columns 必须是字符串列表")
            spec.columns = [c.strip() for c in cols if c.strip()]

        # 条件
        conds = raw_input.get("conditions") or raw_input.get("条件")
        if conds is not None:
            if isinstance(conds, str):
                spec.conditions = [conds.strip()] if conds.strip() else []
            elif isinstance(conds, list) and all(isinstance(c, str) for c in conds):
                spec.conditions = [c.strip() for c in conds if c.strip()]
            else:
                raise SQLBuilderError("E003", "conditions 必须是字符串或字符串列表")

        # 排序
        order = raw_input.get("order_by") or raw_input.get("排序")
        if order is not None:
            if isinstance(order, str):
                spec.order_by = [order.strip()] if order.strip() else []
            elif isinstance(order, list) and all(isinstance(o, str) for o in order):
                spec.order_by = [o.strip() for o in order if o.strip()]
            else:
                raise SQLBuilderError("E003", "order_by 必须是字符串或字符串列表")

        # 分组
        group = raw_input.get("group_by") or raw_input.get("分组")
        if group is not None:
            if isinstance(group, str):
                spec.group_by = [group.strip()] if group.strip() else []
            elif isinstance(group, list) and all(isinstance(g, str) for g in group):
                spec.group_by = [g.strip() for g in group if g.strip()]
            else:
                raise SQLBuilderError("E003", "group_by 必须是字符串或字符串列表")

        # 数量限制
        limit = raw_input.get("limit") or raw_input.get("限制")
        if limit is not None:
            if not isinstance(limit, int) or limit < 0:
                raise SQLBuilderError("E003", "limit 必须是非负整数")
            spec.limit = limit

        # 偏移
        offset = raw_input.get("offset") or raw_input.get("偏移")
        if offset is not None:
            if not isinstance(offset, int) or offset < 0:
                raise SQLBuilderError("E003", "offset 必须是非负整数")
            spec.offset = offset

        # 去重
        distinct = raw_input.get("distinct") or raw_input.get("去重")
        if distinct is not None:
            if not isinstance(distinct, bool):
                raise SQLBuilderError("E003", "distinct 必须是布尔值")
            spec.distinct = distinct

        # JOIN
        joins = raw_input.get("joins") or raw_input.get("连接")
        if joins is not None:
            if not isinstance(joins, list) or not all(isinstance(j, str) for j in joins):
                raise SQLBuilderError("E003", "joins 必须是字符串列表")
            spec.join_clauses = [j.strip() for j in joins if j.strip()]

        if not spec.has_content():
            raise SQLBuilderError("E002", "查询规格中没有有效内容")
        return spec

    # 字符串输入（简化处理：尝试提取表名）
    if isinstance(raw_input, str):
        text = raw_input.strip()
        if not text:
            raise SQLBuilderError("E001")

        spec = QuerySpec()
        # 极简启发式：寻找 "表" 或 "table" 关键字后的词语
        import re

        match = re.search(r"(?:表|table)[:：]?\s*([a-zA-Z_][a-zA-Z0-9_]*)", text, re.IGNORECASE)
        if match:
            spec.table = match.group(1)
        else:
            # 取第一个非空词组作为表名
            words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text)
            if words:
                spec.table = words[0]
            else:
                raise SQLBuilderError("E003", "无法从输入中识别表名")

        # 简单提取列（含 "列" 或 "字段" 关键字后的内容）
        col_match = re.search(r"(?:列|字段|columns)[:：]?\s*\[?([^\]]+)\]?", text, re.IGNORECASE)
        if col_match:
            raw_cols = col_match.group(1)
            spec.columns = [c.strip() for c in re.split(r"[,\s，、]+", raw_cols) if c.strip()]

        if not spec.has_content():
            raise SQLBuilderError("E002", "查询规格中没有有效内容")
        return spec

    # 其他类型
    raise SQLBuilderError("E003", f"不支持的输入类型: {type(raw_input).__name__}")


# --------------------------------------------------------------------------- #
# SQL 生成模块
# --------------------------------------------------------------------------- #
def _validate_identifier(identifier: str) -> None:
    """校验 SQL 标识符（表名、列名）的合法性，防止注入。
    
    允许以下形式：
    - 简单标识符: users, id, name
    - 带表前缀: users.id, o.amount
    - 带函数调用: SUM(amount), COUNT(*)
    - 带别名: SUM(amount) as total, u.id AS user_id
    - 带排序: price DESC, created_at ASC
    """
    if not identifier or not identifier.strip():
        raise SQLBuilderError("E003", "标识符不能为空")
    
    import re
    
    # 去除可能的排序方向
    base = identifier.strip()
    # 检查是否包含排序方向
    parts = base.split()
    if len(parts) > 1 and parts[-1].upper() in ("ASC", "DESC"):
        base = " ".join(parts[:-1])
    
    # 允许的模式：
    # 1. 简单标识符: [a-zA-Z_][a-zA-Z0-9_]*
    # 2. 带点号: table.column
    # 3. 函数调用: FUNC(args)
    # 4. 带别名: expr AS alias 或 expr as alias
    # 5. 通配符: *
    
    # 去除别名部分（AS 或 as）
    if re.search(r'\s+(AS|as)\s+', base):
        # 检查别名部分
        alias_match = re.search(r'\s+(AS|as)\s+([a-zA-Z_][a-zA-Z0-9_]*)', base)
        if not alias_match:
            raise SQLBuilderError("E003", f"非法别名: {identifier}")
        # 检查表达式部分（去掉别名）
        expr_part = re.split(r'\s+(AS|as)\s+', base)[0].strip()
        if not _is_valid_expression(expr_part):
            raise SQLBuilderError("E003", f"非法表达式: {identifier}")
        return
    
    # 检查是否为函数调用
    if '(' in base and ')' in base:
        # 提取函数名和参数
        func_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)$', base, re.DOTALL)
        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2).strip()
            # 函数名必须是合法标识符
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', func_name):
                raise SQLBuilderError("E003", f"非法函数名: {func_name}")
            # 检查参数（允许 *、列名、表达式）
            if args_str in ('*', ''):
                return
            # 参数可以是简单标识符或带表前缀
            args_list = [a.strip() for a in args_str.split(',')]
            for arg in args_list:
                if not _is_valid_expression(arg):
                    raise SQLBuilderError("E003", f"非法函数参数: {arg}")
            return
        else:
            raise SQLBuilderError("E003", f"非法函数调用: {identifier}")
    
    # 简单标识符或带表前缀
    if _is_valid_expression(base):
        return
    
    raise SQLBuilderError("E003", f"非法标识符: {identifier}")


def _is_valid_expression(expr: str) -> bool:
    """检查是否为合法的表达式（标识符、带表前缀的列名等）。"""
    import re
    expr = expr.strip()
    if expr == '*':
        return True
    # 支持 table.column 或简单标识符
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$', expr))


def _validate_condition(condition: str) -> None:
    """校验条件表达式的合法性（宽松校验）。"""
    if not condition or not condition.strip():
        raise SQLBuilderError("E003", "条件不能为空")
    # 仅检查基本结构，不深入解析
    if len(condition.strip()) < 3:
        raise SQLBuilderError("E003", f"条件太短: {condition}")


def generate_sql(spec: QuerySpec) -> Tuple[str, int]:
    """
    根据 QuerySpec 生成 SQL 语句。

    参数:
        spec: 查询规格对象。

    返回:
        (SQL 语句, 置信度)。置信度为 0-100 的整数。

    异常:
        SQLBuilderError: E007 SQL 生成失败；E006 非法标识符。
    """
    if spec is None or not isinstance(spec, QuerySpec):
        raise SQLBuilderError("E008", "spec 必须是 QuerySpec 实例")

    try:
        # 校验表名
        if not spec.table:
            raise SQLBuilderError("E002", "缺少表名")
        _validate_identifier(spec.table)

        # 构建 SELECT 子句
        select_keyword = "SELECT DISTINCT" if spec.distinct else "SELECT"
        if spec.columns:
            for col in spec.columns:
                _validate_identifier(col)
            column_sql = ", ".join(spec.columns)
        else:
            column_sql = "*"

        sql_parts: List[str] = [f"{select_keyword} {column_sql}"]

        # FROM 子句
        sql_parts.append(f"FROM {spec.table}")

        # JOIN 子句
        for join in spec.join_clauses:
            # 宽松校验：至少包含 JOIN 关键字
            if "JOIN" not in join.upper():
                raise SQLBuilderError("E003", f"JOIN 子句缺少 JOIN 关键字: {join}")
            sql_parts.append(join.strip())

        # WHERE 子句
        if spec.conditions:
            for cond in spec.conditions:
                _validate_condition(cond)
            where_sql = " AND ".join(f"({c.strip()})" for c in spec.conditions)
            sql_parts.append(f"WHERE {where_sql}")

        # GROUP BY 子句
        if spec.group_by:
            for g in spec.group_by:
                _validate_identifier(g)
            sql_parts.append(f"GROUP BY {', '.join(spec.group_by)}")

        # ORDER BY 子句
        if spec.order_by:
            for o in spec.order_by:
                # 允许 "列名 ASC/DESC" 形式
                parts = o.strip().split()
                if len(parts) > 0:
                    _validate_identifier(parts[0])
                if len(parts) > 1 and parts[1].upper() not in ("ASC", "DESC"):
                    raise SQLBuilderError("E003", f"排序方向非法: {parts[1]}")
            sql_parts.append(f"ORDER BY {', '.join(spec.order_by)}")

        # LIMIT 子句
        if spec.limit is not None:
            sql_parts.append(f"LIMIT {spec.limit}")

        # OFFSET 子句
        if spec.offset is not None:
            if spec.limit is None:
                raise SQLBuilderError("E003", "OFFSET 需要 LIMIT 配合使用")
            sql_parts.append(f"OFFSET {spec.offset}")

        sql = " ".join(sql_parts) + ";"

        # 计算置信度
        confidence = 95  # 基础置信度
        if spec.columns:
            confidence += 2
        if spec.conditions:
            confidence += 2
        if spec.order_by or spec.group_by:
            confidence += 1
        confidence = min(confidence, 99)

        return sql, confidence

    except SQLBuilderError:
        raise
    except Exception as exc:
        raise SQLBuilderError("E007", f"SQL 生成失败: {str(exc)}") from exc


def format_output(sql: str, confidence: int) -> Dict[str, Any]:
    """
    根据置信度格式化输出结果。

    参数:
        sql: 生成的 SQL 语句。
        confidence: 置信度（0-100）。

    返回:
        包含 SQL、置信度和标注信息的字典。
    """
    result: Dict[str, Any] = {
        "sql": sql,
        "confidence": confidence,
        "annotation": "",
    }

    if confidence >= 90:
        result["annotation"] = "可直接使用"
    elif confidence >= 85:
        result["annotation"] = "建议复核"
    else:
        result["annotation"] = "[需核实]"

    return result


# --------------------------------------------------------------------------- #
# 主处理流程
# --------------------------------------------------------------------------- #
def process_input(raw_input: Any) -> Dict[str, Any]:
    """
    完整处理流程：解析 → 生成 SQL → 格式化输出。

    参数:
        raw_input: 原始输入。

    返回:
        包含 SQL、置信度和标注的结果字典。

    异常:
        SQLBuilderError: 各阶段可能抛出的错误。
    """
    # Step 1: 解析输入
    spec = parse_input(raw_input)

    # Step 2: 生成 SQL
    sql, confidence = generate_sql(spec)

    # Step 3: 格式化输出
    result = format_output(sql, confidence)

    # 附加规格信息（供调试/展示）
    result["spec"] = {
        "table": spec.table,
        "columns": spec.columns,
        "conditions": spec.conditions,
        "order_by": spec.order_by,
        "group_by": spec.group_by,
        "limit": spec.limit,
        "offset": spec.offset,
        "distinct": spec.distinct,
        "joins": spec.join_clauses,
    }

    return result


# --------------------------------------------------------------------------- #
# 自检模块（--selftest）
# --------------------------------------------------------------------------- #
def run_selftest() -> int:
    """
    离线自检核心逻辑。使用内置硬编码样例数据，不依赖外部文件或网络。

    返回:
        0 表示全部通过，非 0 表示失败。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    test_cases = [
        {
            "name": "基础查询",
            "input": {"table": "users", "columns": ["id", "name"]},
            "check": lambda r: (
                r["sql"].startswith("SELECT id, name FROM users")
                and r["confidence"] > 0
                and r["confidence"] <= 100
            ),
        },
        {
            "name": "带条件查询",
            "input": {
                "table": "orders",
                "columns": ["id", "amount"],
                "conditions": ["amount > 100", "status = 'paid'"],
            },
            "check": lambda r: (
                "WHERE" in r["sql"]
                and "amount > 100" in r["sql"]
                and "status = 'paid'" in r["sql"]
                and r["confidence"] >= 90
            ),
        },
        {
            "name": "排序和限制",
            "input": {
                "table": "products",
                "columns": ["name", "price"],
                "order_by": ["price DESC"],
                "limit": 10,
            },
            "check": lambda r: (
                "ORDER BY price DESC" in r["sql"]
                and "LIMIT 10" in r["sql"]
                and r["confidence"] >= 90
            ),
        },
        {
            "name": "去重查询",
            "input": {"table": "events", "distinct": True, "columns": ["user_id"]},
            "check": lambda r: "SELECT DISTINCT user_id" in r["sql"],
        },
        {
            "name": "字符串输入",
            "input": "查询表 users 的列 [id, email]",
            "check": lambda r: (
                "FROM users" in r["sql"]
                and "id" in r["sql"]
                and "email" in r["sql"]
            ),
        },
        {
            "name": "空列默认星号",
            "input": {"table": "logs"},
            "check": lambda r: "SELECT * FROM logs" == r["sql"].rstrip(";"),
        },
        {
            "name": "分组查询",
            "input": {
                "table": "sales",
                "columns": ["region", "SUM(amount) as total"],
                "group_by": ["region"],
            },
            "check": lambda r: (
                "GROUP BY region" in r["sql"]
                and "SUM(amount) as total" in r["sql"]
            ),
        },
        {
            "name": "JOIN 查询",
            "input": {
                "table": "users",
                "columns": ["u.id", "o.amount"],
                "joins": ["JOIN orders o ON u.id = o.user_id"],
            },
            "check": lambda r: (
                "JOIN orders o ON u.id = o.user_id" in r["sql"]
            ),
        },
        {
            "name": "OFFSET 查询",
            "input": {"table": "items", "limit": 5, "offset": 10},
            "check": lambda r: "LIMIT 5 OFFSET 10" in r["sql"],
        },
    ]

    # 错误处理测试
    error_cases = [
        {"name": "空输入", "input": None, "expected_code": "E001"},
        {"name": "缺少表名", "input": {"columns": ["id"]}, "expected_code": "E002"},
        {"name": "非法表名", "input": {"table": "bad table!"}, "expected_code": "E003"},
        {"name": "非法列名", "input": {"table": "t", "columns": ["bad col"]}, "expected_code": "E003"},
    ]

    passed = 0
    failed = 0

    # 运行正常测试
    print("\n--- 正常功能测试 ---")
    for case in test_cases:
        try:
            result = process_input(case["input"])
            if case["check"](result):
                print(f"  [通过] {case['name']}")
                passed += 1
            else:
                print(f"  [失败] {case['name']} - 断言未通过")
                print(f"         生成的 SQL: {result['sql']}")
                failed += 1
        except Exception as exc:
            print(f"  [失败] {case['name']} - 意外异常: {exc}")
            failed += 1

    # 运行错误处理测试
    print("\n--- 错误处理测试 ---")
    for case in error_cases:
        try:
            process_input(case["input"])
            print(f"  [失败] {case['name']} - 未抛出预期异常")
            failed += 1
        except SQLBuilderError as exc:
            if exc.code == case["expected_code"]:
                print(f"  [通过] {case['name']} (错误码 {exc.code})")
                passed += 1
            else:
                print(f"  [失败] {case['name']} - 错误码 {exc.code} != {case['expected_code']}")
                failed += 1
        except Exception as exc:
            print(f"  [失败] {case['name']} - 非预期异常类型: {type(exc).__name__}")
            failed += 1

    # 输出汇总
    print("\n" + "=" * 60)
    print(f"自检完成: 通过 {passed} 项, 失败 {failed} 项")
    print("=" * 60)

    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------- #
# 命令行入口
# --------------------------------------------------------------------------- #
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="go-sqlbuilder 风格的 SQL 查询生成器（独立实现）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据，不依赖外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据，JSON 格式的字典或自然语言描述",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="以可读格式输出结果",
    )

    args = parser.parse_args()

    # 自检模式优先
    if args.selftest:
        return run_selftest()

    # 需要输入
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest 进行自检", file=sys.stderr)
        print("用法: python main.py --input '{\"table\": \"users\"}'", file=sys.stderr)
        print("       python main.py --selftest", file=sys.stderr)
        return 1

    try:
        # 尝试解析 JSON
        import json

        try:
            raw_input = json.loads(args.input)
        except json.JSONDecodeError:
            # 不是 JSON，按字符串处理
            raw_input = args.input

        result = process_input(raw_input)

        if args.pretty:
            import json as json_out

            print(json_out.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["sql"])
            print(f"置信度: {result['confidence']}% ({result['annotation']})")

        return 0

    except SQLBuilderError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
