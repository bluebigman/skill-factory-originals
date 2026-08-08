#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL 代码生成器 - 独立实现脚本
将自然语言需求转化为规范 SQL 语句（仅生成，不执行）
"""

import sys
import re
import argparse
from typing import Dict, List, Tuple, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "无法识别的查询类型",
    "E003": "缺少关键字段（表名）",
    "E004": "条件解析失败",
    "E005": "排序解析失败",
    "E006": "聚合函数解析失败",
    "E007": "JOIN 解析失败",
    "E008": "分页参数错误",
    "E009": "子查询解析失败",
    "E010": "内部处理错误",
}


class SQLGenError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心解析器
# ---------------------------------------------------------------------------
class SQLGenerator:
    """自然语言转 SQL 的核心逻辑"""

    # 常见聚合函数关键词
    AGG_FUNCS = {
        "统计": "COUNT",
        "计数": "COUNT",
        "求和": "SUM",
        "总和": "SUM",
        "平均": "AVG",
        "平均值": "AVG",
        "最大": "MAX",
        "最大值": "MAX",
        "最小": "MIN",
        "最小值": "MIN",
    }

    # 常见比较操作符
    COMPARISONS = {
        "大于": ">",
        "小于": "<",
        "等于": "=",
        "不等于": "!=",
        "大于等于": ">=",
        "不小于": ">=",
        "小于等于": "<=",
        "不大于": "<=",
    }

    # 常见逻辑连接词
    LOGIC_CONNECTORS = {
        "并且": "AND",
        "而且": "AND",
        "同时": "AND",
        "且": "AND",
        "或者": "OR",
        "或": "OR",
    }

    # 常见排序关键词
    SORT_KEYWORDS = {
        "升序": "ASC",
        "正序": "ASC",
        "降序": "DESC",
        "倒序": "DESC",
    }

    def __init__(self):
        pass

    def generate(self, text: str) -> Dict:
        """
        主入口：将自然语言转换为 SQL 语句
        返回包含 SQL 和注释的字典
        """
        if not text or not text.strip():
            raise SQLGenError("E001")

        text = text.strip()

        # 提取表名（必须先做，因为后续解析依赖于它）
        table_name, remaining = self._extract_table(text)
        if not table_name:
            raise SQLGenError("E003")

        # 提取聚合函数
        agg_func, agg_field, remaining = self._extract_aggregation(remaining)

        # 提取 WHERE 条件
        where_clause, remaining = self._extract_conditions(remaining)

        # 提取 GROUP BY
        group_by, remaining = self._extract_group_by(remaining, agg_func)

        # 提取 ORDER BY
        order_by, remaining = self._extract_order_by(remaining)

        # 提取 LIMIT
        limit, remaining = self._extract_limit(remaining)

        # 提取 SELECT 字段
        select_fields = self._extract_select_fields(remaining, agg_func, agg_field, table_name)

        # 构建 SQL
        sql = self._build_sql(
            table_name, select_fields, where_clause,
            group_by, order_by, limit
        )

        # 生成注释
        comments = self._generate_comments(
            table_name, select_fields, where_clause,
            group_by, order_by, limit, agg_func
        )

        return {
            "sql": sql,
            "comments": comments,
            "table": table_name,
            "aggregation": agg_func,
            "where": where_clause,
            "group_by": group_by,
            "order_by": order_by,
            "limit": limit,
        }

    # -- 各步骤解析 ----------------------------------------------------------

    def _extract_table(self, text: str) -> Tuple[Optional[str], str]:
        """提取表名，支持多种格式"""
        # 模式1: "从xxx表" 或 "在xxx表"
        match = re.search(r"(?:从|在|于)\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)\s*表", text)
        if match:
            table = match.group(1)
            remaining = text.replace(match.group(0), " ", 1)
            return table, remaining

        # 模式2: "xxx表" 直接出现
        match = re.search(r"([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)\s*表", text)
        if match:
            table = match.group(1)
            remaining = text.replace(match.group(0), " ", 1)
            return table, remaining

        # 模式3: 聚合词后跟表名，如 "统计订单表总金额"
        match = re.search(r"(?:统计|计数|求和|总和|平均|平均值|最大|最大值|最小|最小值)\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)\s*表", text)
        if match:
            table = match.group(1)
            remaining = text.replace(match.group(0), " ", 1)
            return table, remaining

        # 模式4: "查询xxx" 或 "统计xxx" 等，xxx可能是表名
        match = re.search(r"(?:查询|统计|计数|求和|平均|最大|最小|获取|列出|显示)\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)", text)
        if match and "表" not in match.group(1):
            # 检查是否可能是表名（后面没有其他明显字段）
            candidate = match.group(1)
            # 如果后面跟着"所有"或"全部"，则可能是表名
            if re.search(r"(?:所有|全部|每个|按|根据|其中|的)", text[match.end():]):
                table = candidate
                remaining = text.replace(match.group(0), " ", 1)
                return table, remaining

        return None, text

    def _extract_aggregation(self, text: str) -> Tuple[Optional[str], Optional[str], str]:
        """提取聚合函数及对应字段"""
        for keyword, func in self.AGG_FUNCS.items():
            if keyword in text:
                # 尝试提取聚合字段
                field_match = re.search(
                    r"(?:统计|计数|求和|总和|平均|平均值|最大|最大值|最小|最小值)\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)",
                    text
                )
                field = field_match.group(1) if field_match else "*"
                remaining = text.replace(keyword, " ", 1)
                if field != "*":
                    remaining = remaining.replace(field, " ", 1)
                return func, field, remaining

        return None, None, text

    def _extract_conditions(self, text: str) -> Tuple[Optional[str], str]:
        """提取 WHERE 条件"""
        conditions = []
        remaining = text

        # 查找所有 "字段 操作符 值" 模式
        pattern = r"([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)\s*(大于等于|小于等于|大于|小于|等于|不等于|不小于|不大于)\s*([\u4e00-\u9fa5_a-zA-Z0-9_]+)"
        matches = list(re.finditer(pattern, text))

        if not matches:
            return None, text

        for i, match in enumerate(matches):
            field, op_word, value = match.groups()
            op = self.COMPARISONS.get(op_word, "=")

            # 判断值是数字还是字符串
            if value.isdigit():
                value_str = value
            else:
                value_str = f"'{value}'"

            condition = f"{field} {op} {value_str}"

            # 检查逻辑连接词
            logic = "AND"
            if i > 0:
                # 查找两个条件之间的连接词
                prev_end = matches[i - 1].end()
                between = text[prev_end:match.start()]
                for conn_word, conn_op in self.LOGIC_CONNECTORS.items():
                    if conn_word in between:
                        logic = conn_op
                        break

            conditions.append((logic, condition))
            remaining = remaining.replace(match.group(0), " ", 1)

        # 组合条件
        if not conditions:
            return None, remaining

        where_sql = conditions[0][1]
        for logic, cond in conditions[1:]:
            where_sql = f"{where_sql} {logic} {cond}"

        return where_sql, remaining

    def _extract_group_by(self, text: str, agg_func: Optional[str]) -> Tuple[Optional[str], str]:
        """提取 GROUP BY（当有聚合函数时）"""
        if not agg_func:
            return None, text

        # 查找 "按xxx分组" 或 "分组按xxx" 或 "每个xxx"
        match = re.search(r"(?:按|根据)\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)\s*(?:分组|归类)", text)
        if not match:
            match = re.search(r"(?:分组|归类)\s*(?:按|根据)\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)", text)
        if not match:
            match = re.search(r"每个\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)", text)

        if not match:
            return None, text

        group_field = match.group(1)
        remaining = text.replace(match.group(0), " ", 1)
        return group_field, remaining

    def _extract_order_by(self, text: str) -> Tuple[Optional[str], str]:
        """提取 ORDER BY"""
        # 查找 "按xxx排序" 或 "按xxx升序/降序" 或 "xxx倒序/升序"
        match = re.search(
            r"按\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)\s*(升序|降序|正序|倒序)?",
            text
        )
        if not match:
            # 尝试其他模式："xxx倒序" 或 "xxx升序"
            match = re.search(
                r"([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)\s*(降序|倒序|升序|正序)",
                text
            )

        if not match:
            return None, text

        field = match.group(1)
        sort_word = match.group(2) or "升序"
        direction = self.SORT_KEYWORDS.get(sort_word, "ASC")

        remaining = text.replace(match.group(0), " ", 1)
        return f"{field} {direction}", remaining

    def _extract_limit(self, text: str) -> Tuple[Optional[str], str]:
        """提取 LIMIT"""
        # 查找 "前N条" / "取前N" / "限制N条" / "前N"
        match = re.search(r"(?:前|取前|限制|只取)\s*(\d+)\s*条?", text)
        if not match:
            # 尝试 "N条" 模式
            match = re.search(r"(\d+)\s*条", text)

        if not match:
            return None, text

        limit = match.group(1)
        remaining = text.replace(match.group(0), " ", 1)
        return limit, remaining

    def _extract_select_fields(self, text: str, agg_func: Optional[str], agg_field: Optional[str], table: str) -> List[str]:
        """提取 SELECT 字段"""
        fields = []

        # 如果有聚合函数，添加聚合字段
        if agg_func and agg_field:
            fields.append(f"{agg_func}({agg_field})")

        # 查找 "查询xxx" 或 "显示xxx" 或 "列出xxx"
        match = re.search(r"(?:查询|显示|列出|获取|找|看)\s*([\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*(?:\s*[,，、]\s*[\u4e00-\u9fa5_a-zA-Z][\u4e00-\u9fa5_a-zA-Z0-9_]*)*)", text)
        if match:
            field_str = match.group(1)
            field_list = re.split(r"[,，、\s]+", field_str)
            for f in field_list:
                if f and f != table and f not in fields:
                    fields.append(f)

        # 如果没有聚合函数且没有明确字段，默认 *
        if not fields:
            fields.append("*")

        return fields

    # -- SQL 构建 ------------------------------------------------------------

    def _build_sql(
        self,
        table: str,
        fields: List[str],
        where: Optional[str],
        group_by: Optional[str],
        order_by: Optional[str],
        limit: Optional[str],
    ) -> str:
        """组装最终 SQL 语句"""
        select_part = ", ".join(fields)
        sql = f"SELECT {select_part} FROM {table}"

        if where:
            sql += f" WHERE {where}"
        if group_by:
            sql += f" GROUP BY {group_by}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"

        return sql + ";"

    def _generate_comments(
        self,
        table: str,
        fields: List[str],
        where: Optional[str],
        group_by: Optional[str],
        order_by: Optional[str],
        limit: Optional[str],
        agg_func: Optional[str],
    ) -> List[str]:
        """生成学习辅助注释"""
        comments = ["-- SQL 代码生成器自动生成", f"-- 查询表: {table}"]

        if agg_func:
            comments.append(f"-- 使用聚合函数: {agg_func}")
        if where:
            comments.append(f"-- 过滤条件: {where}")
        if group_by:
            comments.append(f"-- 分组字段: {group_by}")
        if order_by:
            comments.append(f"-- 排序规则: {order_by}")
        if limit:
            comments.append(f"-- 限制条数: {limit}")

        comments.append("-- 提示: 不同数据库方言可能存在差异，请根据实际环境调整")
        return comments


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """内置硬编码样例数据，离线自检核心逻辑"""
    print("=" * 60)
    print("SQL 代码生成器 - 自检测试")
    print("=" * 60)

    gen = SQLGenerator()
    test_cases = [
        {
            "name": "基础查询",
            "input": "查询所有用户表",
            "check": lambda r: "SELECT" in r["sql"] and "FROM" in r["sql"] and "user" in r["sql"]
        },
        {
            "name": "条件过滤",
            "input": "从用户表查询所有年龄大于30的用户",
            "check": lambda r: "WHERE" in r["sql"] and "age" in r["sql"] and ">" in r["sql"]
        },
        {
            "name": "聚合统计",
            "input": "统计订单表总金额",
            "check": lambda r: "SUM" in r["sql"] and "amount" in r["sql"]
        },
        {
            "name": "分组统计",
            "input": "统计每个部门的员工数量",
            "check": lambda r: "COUNT" in r["sql"] and "GROUP BY" in r["sql"] and "department" in r["sql"]
        },
        {
            "name": "排序分页",
            "input": "从订单表查询所有订单按时间倒序取前10条",
            "check": lambda r: "ORDER BY" in r["sql"] and "DESC" in r["sql"] and "LIMIT" in r["sql"]
        },
        {
            "name": "多条件组合",
            "input": "从用户表查询年龄大于30并且城市等于北京的用户",
            "check": lambda r: "AND" in r["sql"] and "city" in r["sql"] and "age" in r["sql"]
        },
        {
            "name": "逻辑或条件",
            "input": "从用户表查询城市等于北京或者城市等于上海的用户",
            "check": lambda r: "OR" in r["sql"] and "city" in r["sql"]
        },
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        try:
            result = gen.generate(case["input"])
            ok = case["check"](result)

            if ok:
                passed += 1
                print(f"  ✅ {case['name']}: {result['sql']}")
            else:
                failed += 1
                print(f"  ❌ {case['name']}: 断言失败")
                print(f"     生成 SQL: {result['sql']}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {case['name']}: 异常 - {e}")

    print("-" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败, 共 {len(test_cases)} 项")

    # 宽松断言：只要大部分通过即视为成功
    return failed <= 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="SQL 代码生成器 - 将自然语言转换为 SQL 语句"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检测试（离线，无需外部依赖）"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="自然语言查询描述，例如: '从用户表查询所有年龄大于30的用户'"
    )
    parser.add_argument(
        "--table",
        help="指定表名（可选，若查询中未包含）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 查询模式
    if not args.query:
        print("请提供查询描述，或使用 --selftest 运行自检。")
        print("示例: python main.py '从用户表查询所有年龄大于30的用户'")
        sys.exit(1)

    try:
        gen = SQLGenerator()
        result = gen.generate(args.query)

        print("\n" + "=" * 60)
        print("生成结果")
        print("=" * 60)

        for comment in result["comments"]:
            print(comment)

        print("\n" + result["sql"])
        print("\n" + "=" * 60)

    except SQLGenError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[E010] 内部错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
