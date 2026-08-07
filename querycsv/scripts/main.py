#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
querycsv — CSV 数据 SQL 查询与导出工具（独立实现）

功能：
  - 加载 CSV 文件（本地路径 / URL / 粘贴文本）
  - 对已加载数据执行基础 SQL 查询（SELECT / WHERE / GROUP BY / ORDER BY）
  - 导出结果为 CSV / JSON / Markdown
  - 字段类型自动推断（数值 / 日期 / 字符串）

仅依赖 Python 标准库，无第三方依赖。
运行方式：
  python scripts/main.py --selftest    # 离线自检
  python scripts/main.py --help        # 查看帮助
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from collections import OrderedDict
from datetime import datetime

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：无法读取指定 CSV 文件",
    "E003": "URL 读取失败：无法从指定 URL 获取数据",
    "E004": "CSV 解析失败：数据格式不符合 CSV 规范",
    "E005": "SQL 语法错误：无法解析查询语句",
    "E006": "字段不存在：查询中引用了不存在的列",
    "E007": "聚合函数使用错误：聚合函数位置或参数不正确",
    "E008": "导出失败：无法写入导出文件",
    "E009": "数据类型错误：数值转换或比较失败",
    "E010": "内部错误：未预期的运行时异常",
}


def err(code: str, message: str = "") -> None:
    """输出错误信息并以错误码退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {msg}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {msg}", file=sys.stderr)
    sys.exit(code)


class CSVTable:
    """CSV 数据表：存储数据、列名、类型信息"""

    def __init__(self, name: str, headers: list, rows: list):
        self.name = name
        self.headers = headers  # 列名列表
        self.rows = rows        # 数据行列表（每行为 dict）
        self.types = self._infer_types()

    def _infer_types(self) -> dict:
        """推断每列的数据类型：int / float / date / str"""
        types = {}
        for col in self.headers:
            col_type = "str"
            for row in self.rows:
                val = row.get(col, "")
                if val == "" or val is None:
                    continue
                # 尝试整数
                try:
                    int(val)
                    col_type = "int"
                    continue
                except (ValueError, TypeError):
                    pass
                # 尝试浮点数
                try:
                    float(val)
                    col_type = "float"
                    continue
                except (ValueError, TypeError):
                    pass
                # 尝试日期（支持常见格式）
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
                    try:
                        datetime.strptime(str(val), fmt)
                        col_type = "date"
                        break
                    except (ValueError, TypeError):
                        continue
                if col_type == "date":
                    continue
                # 默认字符串
                col_type = "str"
            types[col] = col_type
        return types

    def get_column(self, col: str) -> list:
        """获取指定列的所有值"""
        if col not in self.headers:
            err("E006", f"列 '{col}' 不存在于表 '{self.name}'")
        return [row.get(col, "") for row in self.rows]

    def get_columns(self) -> list:
        """返回所有列名"""
        return self.headers


class SQLParser:
    """简易 SQL 解析器（仅支持 SELECT 查询）"""

    # 正则表达式模式
    SELECT_RE = re.compile(
        r"^\s*SELECT\s+(.+?)\s+FROM\s+(\w+)"
        r"(?:\s+WHERE\s+(.+?))?"
        r"(?:\s+GROUP\s+BY\s+(.+?))?"
        r"(?:\s+ORDER\s+BY\s+(.+?))?"
        r"\s*;?\s*$",
        re.IGNORECASE | re.DOTALL,
    )

    # 聚合函数
    AGG_FUNCS = {"SUM", "AVG", "COUNT", "MAX", "MIN"}

    def __init__(self, tables: dict):
        """tables: {表名: CSVTable}"""
        self.tables = tables

    def parse(self, sql: str) -> dict:
        """解析 SQL 并返回查询计划"""
        match = self.SELECT_RE.match(sql)
        if not match:
            err("E005", f"无法解析 SQL: {sql}")

        select_part, table_name, where_part, group_part, order_part = match.groups()
        table_name = table_name.lower()

        if table_name not in self.tables:
            err("E006", f"表 '{table_name}' 未加载")

        table = self.tables[table_name]

        # 解析 SELECT 字段
        select_fields = self._parse_select(select_part.strip())
        # 解析 WHERE 条件
        where_cond = self._parse_where(where_part.strip()) if where_part else None
        # 解析 GROUP BY
        group_fields = self._parse_group_by(group_part.strip()) if group_part else []
        # 解析 ORDER BY
        order_fields = self._parse_order_by(order_part.strip()) if order_part else []

        return {
            "table": table,
            "select_fields": select_fields,
            "where_cond": where_cond,
            "group_fields": group_fields,
            "order_fields": order_fields,
        }

    def _parse_select(self, select_part: str) -> list:
        """解析 SELECT 字段，返回 [(字段名或聚合表达式, 别名)]"""
        fields = []
        # 按逗号分割，但跳过括号内的逗号（聚合函数参数）
        parts = self._split_commas(select_part)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 检查别名 AS
            alias = None
            as_match = re.search(r"\s+AS\s+(\w+)", part, re.IGNORECASE)
            if as_match:
                alias = as_match.group(1)
                part = part[: as_match.start()].strip()

            # 检查聚合函数
            agg_match = re.match(
                r"^(SUM|AVG|COUNT|MAX|MIN)\s*\(\s*(\*|\w+)\s*\)$",
                part,
                re.IGNORECASE,
            )
            if agg_match:
                func = agg_match.group(1).upper()
                arg = agg_match.group(2)
                fields.append((func, arg, alias or f"{func}_{arg}"))
            else:
                # 普通字段
                if not re.match(r"^[\w.]+$", part):
                    err("E005", f"无效的 SELECT 字段: {part}")
                fields.append(("FIELD", part, alias or part.split(".")[-1]))
        return fields

    def _parse_where(self, where_part: str) -> dict:
        """解析 WHERE 条件，返回 {field, op, value}"""
        # 支持 =, !=, >, <, >=, <=, LIKE
        op_pattern = r"(>=|<=|!=|<>|=|>|<|\s+LIKE\s+)"
        match = re.search(op_pattern, where_part, re.IGNORECASE)
        if not match:
            err("E005", f"无法解析 WHERE 条件: {where_part}")

        field = where_part[: match.start()].strip()
        op = match.group(1).strip().upper()
        value = where_part[match.end():].strip().strip("'\"")

        if op == "<>":
            op = "!="
        if op == "LIKE":
            op = "LIKE"

        return {"field": field, "op": op, "value": value}

    def _parse_group_by(self, group_part: str) -> list:
        """解析 GROUP BY 字段"""
        return [f.strip() for f in group_part.split(",") if f.strip()]

    def _parse_order_by(self, order_part: str) -> list:
        """解析 ORDER BY 字段，返回 [(字段, 升序?)]"""
        fields = []
        for f in order_part.split(","):
            f = f.strip()
            if not f:
                continue
            asc = True
            if re.search(r"\s+DESC\s*$", f, re.IGNORECASE):
                asc = False
                f = re.sub(r"\s+DESC\s*$", "", f, flags=re.IGNORECASE)
            elif re.search(r"\s+ASC\s*$", f, re.IGNORECASE):
                f = re.sub(r"\s+ASC\s*$", "", f, flags=re.IGNORECASE)
            fields.append((f.strip(), asc))
        return fields

    @staticmethod
    def _split_commas(s: str) -> list:
        """按逗号分割，忽略括号内的逗号"""
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


class QueryExecutor:
    """SQL 查询执行器"""

    def __init__(self, parser: SQLParser):
        self.parser = parser

    def execute(self, sql: str) -> "QueryResult":
        """执行查询并返回结果"""
        plan = self.parser.parse(sql)
        table = plan["table"]

        # 1. 筛选行（WHERE）
        rows = self._apply_where(table, plan["where_cond"])

        # 2. 分组（GROUP BY）
        if plan["group_fields"]:
            rows = self._apply_group_by(table, rows, plan["group_fields"], plan["select_fields"])
        else:
            # 无分组时，处理聚合函数（全局聚合）
            rows = self._apply_global_agg(table, rows, plan["select_fields"])

        # 3. 排序（ORDER BY）
        if plan["order_fields"]:
            rows = self._apply_order_by(table, rows, plan["order_fields"])

        # 4. 提取 SELECT 字段
        result_rows, headers = self._extract_fields(table, rows, plan["select_fields"])

        return QueryResult(headers, result_rows)

    def _apply_where(self, table: CSVTable, cond: dict) -> list:
        """应用 WHERE 条件过滤行"""
        if not cond:
            return table.rows

        field = cond["field"]
        op = cond["op"]
        value = cond["value"]

        if field not in table.headers:
            err("E006", f"WHERE 条件中的字段 '{field}' 不存在")

        col_type = table.types.get(field, "str")

        # 转换比较值类型
        try:
            if col_type == "int":
                value_cmp = int(value)
            elif col_type == "float":
                value_cmp = float(value)
            elif col_type == "date":
                value_cmp = self._parse_date(value)
            else:
                value_cmp = str(value)
        except (ValueError, TypeError):
            value_cmp = str(value)

        result = []
        for row in table.rows:
            raw_val = row.get(field, "")
            # 转换行值类型
            try:
                if col_type == "int":
                    row_val = int(raw_val)
                elif col_type == "float":
                    row_val = float(raw_val)
                elif col_type == "date":
                    row_val = self._parse_date(raw_val)
                else:
                    row_val = str(raw_val)
            except (ValueError, TypeError):
                row_val = str(raw_val)

            if self._compare(row_val, op, value_cmp):
                result.append(row)

        return result

    def _compare(self, left, op, right) -> bool:
        """执行比较操作"""
        try:
            if op == "=":
                return left == right
            elif op == "!=":
                return left != right
            elif op == ">":
                return left > right
            elif op == "<":
                return left < right
            elif op == ">=":
                return left >= right
            elif op == "<=":
                return left <= right
            elif op == "LIKE":
                # 简易 LIKE：% 通配符
                pattern = str(right).replace("%", ".*")
                return bool(re.match(f"^{pattern}$", str(left), re.IGNORECASE))
            else:
                err("E005", f"不支持的操作符: {op}")
        except TypeError:
            # 类型不匹配时尝试字符串比较
            return str(left) == str(right) if op == "=" else False

    def _apply_group_by(self, table: CSVTable, rows: list, group_fields: list, select_fields: list) -> list:
        """按字段分组并计算聚合"""
        # 验证分组字段存在
        for f in group_fields:
            if f not in table.headers:
                err("E006", f"GROUP BY 字段 '{f}' 不存在")

        # 分组
        groups = OrderedDict()
        for row in rows:
            key = tuple(str(row.get(f, "")) for f in group_fields)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        # 对每组计算聚合
        result = []
        for key, group_rows in groups.items():
            new_row = {}
            # 分组字段值
            for i, f in enumerate(group_fields):
                new_row[f] = group_rows[0].get(f, "")

            # 计算聚合
            for func, arg, alias in select_fields:
                if func == "FIELD":
                    # 非聚合字段（应已在分组字段中）
                    if arg not in group_fields:
                        err("E007", f"字段 '{arg}' 必须出现在 GROUP BY 中或使用聚合函数")
                    continue

                values = []
                if arg == "*":
                    values = [1] * len(group_rows)
                else:
                    if arg not in table.headers:
                        err("E006", f"聚合参数字段 '{arg}' 不存在")
                    for r in group_rows:
                        v = r.get(arg, "")
                        if v != "" and v is not None:
                            values.append(v)

                new_row[alias] = self._calc_agg(func, values, table.types.get(arg, "str"))

            result.append(new_row)

        return result

    def _apply_global_agg(self, table: CSVTable, rows: list, select_fields: list) -> list:
        """无 GROUP BY 时处理全局聚合"""
        has_agg = any(f[0] != "FIELD" for f in select_fields)

        if not has_agg:
            return rows

        # 全局聚合只返回一行
        new_row = {}
        for func, arg, alias in select_fields:
            if func == "FIELD":
                # 非聚合字段在全局聚合中无意义
                err("E007", f"字段 '{arg}' 在无 GROUP BY 时不能直接 SELECT（需聚合）")
                continue

            values = []
            if arg == "*":
                values = [1] * len(rows)
            else:
                if arg not in table.headers:
                    err("E006", f"聚合参数字段 '{arg}' 不存在")
                for r in rows:
                    v = r.get(arg, "")
                    if v != "" and v is not None:
                        values.append(v)

            new_row[alias] = self._calc_agg(func, values, table.types.get(arg, "str"))

        return [new_row] if new_row else []

    def _calc_agg(self, func: str, values: list, col_type: str) -> object:
        """计算聚合值"""
        if not values:
            return 0 if func == "COUNT" else ""

        try:
            if func == "COUNT":
                return len(values)
            elif func == "SUM":
                nums = [self._to_number(v, col_type) for v in values]
                return sum(nums)
            elif func == "AVG":
                nums = [self._to_number(v, col_type) for v in values]
                return sum(nums) / len(nums) if nums else 0
            elif func == "MAX":
                return max(values)
            elif func == "MIN":
                return min(values)
            else:
                err("E007", f"不支持的聚合函数: {func}")
        except (TypeError, ValueError):
            err("E009", f"聚合计算失败: {func}")

    def _to_number(self, val, col_type: str):
        """转换为数值"""
        if col_type == "int":
            return int(val)
        elif col_type == "float":
            return float(val)
        else:
            return float(val)

    def _apply_order_by(self, table: CSVTable, rows: list, order_fields: list) -> list:
        """应用排序"""
        def sort_key(row):
            keys = []
            for field, _ in order_fields:
                if field not in table.headers:
                    err("E006", f"ORDER BY 字段 '{field}' 不存在")
                val = row.get(field, "")
                col_type = table.types.get(field, "str")
                try:
                    if col_type == "int":
                        keys.append(int(val))
                    elif col_type == "float":
                        keys.append(float(val))
                    elif col_type == "date":
                        keys.append(self._parse_date(val))
                    else:
                        keys.append(str(val))
                except (ValueError, TypeError):
                    keys.append(str(val))
            return tuple(keys)

        # 多字段排序
        for field, asc in reversed(order_fields):
            col_type = table.types.get(field, "str")

            def key_func(row, f=field, t=col_type):
                val = row.get(f, "")
                try:
                    if t == "int":
                        return int(val)
                    elif t == "float":
                        return float(val)
                    elif t == "date":
                        return self._parse_date(val)
                    else:
                        return str(val)
                except (ValueError, TypeError):
                    return str(val)

            rows.sort(key=key_func, reverse=not asc)

        return rows

    def _extract_fields(self, table: CSVTable, rows: list, select_fields: list) -> tuple:
        """提取最终输出字段"""
        headers = []
        result = []

        for row in rows:
            new_row = {}
            for func, arg, alias in select_fields:
                if func == "FIELD":
                    # 普通字段
                    field_name = arg.split(".")[-1]
                    if field_name not in table.headers and field_name not in row:
                        err("E006", f"字段 '{arg}' 不存在")
                    val = row.get(field_name, row.get(arg, ""))
                    new_row[alias] = val
                else:
                    # 聚合结果
                    new_row[alias] = row.get(alias, "")
                if alias not in headers:
                    headers.append(alias)
            result.append(new_row)

        return result, headers

    @staticmethod
    def _parse_date(val):
        """解析日期字符串为 datetime 对象"""
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(val), fmt)
            except (ValueError, TypeError):
                continue
        return str(val)


class QueryResult:
    """查询结果容器"""

    def __init__(self, headers: list, rows: list):
        self.headers = headers
        self.rows = rows

    def to_csv(self) -> str:
        """导出为 CSV 字符串"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.headers)
        for row in self.rows:
            writer.writerow([row.get(h, "") for h in self.headers])
        return output.getvalue()

    def to_json(self) -> str:
        """导出为 JSON 字符串"""
        return json.dumps(self.rows, ensure_ascii=False, indent=2, default=str)

    def to_markdown(self) -> str:
        """导出为 Markdown 表格"""
        lines = []
        lines.append("| " + " | ".join(self.headers) + " |")
        lines.append("|" + "|".join(["---"] * len(self.headers)) + "|")
        for row in self.rows:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in self.headers) + " |")
        return "\n".join(lines)


class CSVLoader:
    """CSV 加载器：支持文件路径、URL、文本"""

    @staticmethod
    def load(source: str, table_name: str = "csv_data") -> CSVTable:
        """加载 CSV 数据"""
        data = CSVLoader._read_source(source)
        try:
            reader = csv.DictReader(io.StringIO(data))
            headers = reader.fieldnames or []
            rows = [dict(row) for row in reader]
        except csv.Error as e:
            err("E004", str(e))

        if not headers:
            err("E004", "CSV 文件没有列名")

        return CSVTable(table_name, headers, rows)

    @staticmethod
    def _read_source(source: str) -> str:
        """读取数据源内容"""
        # 检查是否为 URL
        if source.startswith(("http://", "https://")):
            try:
                with urllib.request.urlopen(source, timeout=10) as resp:
                    return resp.read().decode("utf-8")
            except Exception as e:
                err("E003", str(e))

        # 检查是否为文件路径
        if "\n" not in source and "\r" not in source:
            try:
                with open(source, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                # 不是文件，当作文本处理
                pass
            except Exception as e:
                err("E002", str(e))

        # 当作文本处理
        return source


def run_selftest():
    """离线自检核心逻辑"""
    print("=" * 60)
    print("QueryCSV 自检程序")
    print("=" * 60)

    # 硬编码测试数据
    csv_text = """name,age,score,department
Alice,25,85.5,Engineering
Bob,30,92.0,Engineering
Charlie,22,78.5,Sales
Diana,28,88.0,Sales
Eve,35,95.5,Engineering
Frank,26,72.0,HR"""

    print("\n[1] 加载 CSV 数据...")
    table = CSVLoader.load(csv_text, "employees")
    print(f"    表名: {table.name}")
    print(f"    列: {table.headers}")
    print(f"    行数: {len(table.rows)}")
    assert len(table.rows) == 6, "数据行数应为 6"
    assert "name" in table.headers, "缺少 name 列"
    assert table.types.get("age") == "int", "age 应为整数类型"
    assert table.types.get("score") == "float", "score 应为浮点类型"
    print("    ✓ 加载成功")

    print("\n[2] 测试 WHERE 过滤...")
    parser = SQLParser({"employees": table})
    executor = QueryExecutor(parser)

    result = executor.execute("SELECT name, age FROM employees WHERE age > 25")
    print(f"    age > 25 结果: {len(result.rows)} 行")
    assert len(result.rows) >= 3, "age > 25 应至少有 3 行"
    for row in result.rows:
        assert int(row["age"]) > 25, f"age 应大于 25: {row}"
    print("    ✓ WHERE 过滤正确")

    print("\n[3] 测试 GROUP BY 聚合...")
    result = executor.execute(
        "SELECT department, COUNT(*) AS cnt, AVG(score) AS avg_score "
        "FROM employees GROUP BY department"
    )
    print(f"    分组数: {len(result.rows)}")
    assert len(result.rows) >= 3, "应有至少 3 个部门"
    for row in result.rows:
        assert int(row["cnt"]) >= 1, f"每组至少 1 人: {row}"
        assert float(row["avg_score"]) > 0, f"平均分应大于 0: {row}"
    print("    ✓ GROUP BY 聚合正确")

    print("\n[4] 测试 ORDER BY 排序...")
    result = executor.execute("SELECT name, score FROM employees ORDER BY score DESC")
    print(f"    排序结果: {len(result.rows)} 行")
    assert len(result.rows) == 6, "排序后应有 6 行"
    scores = [float(r["score"]) for r in result.rows]
    assert scores == sorted(scores, reverse=True), "分数应降序排列"
    print("    ✓ ORDER BY 排序正确")

    print("\n[5] 测试导出功能...")
    result = executor.execute("SELECT name, department FROM employees")
    csv_out = result.to_csv()
    json_out = result.to_json()
    md_out = result.to_markdown()
    assert "name" in csv_out, "CSV 导出应包含列名"
    assert json.loads(json_out), "JSON 导出应可解析"
    assert "|" in md_out, "Markdown 导出应包含表格符号"
    print("    ✓ 导出功能正常")

    print("\n[6] 测试类型推断...")
    assert table.types["age"] == "int", "age 类型应为 int"
    assert table.types["score"] == "float", "score 类型应为 float"
    assert table.types["name"] == "str", "name 类型应为 str"
    print("    ✓ 类型推断正确")

    print("\n[7] 测试复杂查询（组合条件）...")
    result = executor.execute(
        "SELECT department, SUM(age) AS total_age, MAX(score) AS max_score "
        "FROM employees WHERE age >= 25 GROUP BY department "
        "ORDER BY total_age DESC"
    )
    print(f"    复杂查询结果: {len(result.rows)} 行")
    assert len(result.rows) >= 2, "复杂查询应返回至少 2 行"
    for row in result.rows:
        assert int(row["total_age"]) > 0, "总年龄应大于 0"
        assert float(row["max_score"]) > 0, "最高分应大于 0"
    print("    ✓ 复杂查询正确")

    print("\n[8] 测试错误处理...")
    try:
        executor.execute("SELECT nonexistent FROM employees")
        print("    ✗ 应抛出字段不存在错误")
        return False
    except SystemExit as e:
        assert e.code == "E006", "应返回 E006 错误码"
        print("    ✓ 字段不存在错误正确（E006）")

    # 测试 WHERE 中不存在的字段
    try:
        executor.execute("SELECT name FROM employees WHERE nonexistent > 25")
        print("    ✗ 应抛出 WHERE 字段不存在错误")
        return False
    except SystemExit as e:
        assert e.code == "E006", "应返回 E006 错误码"
        print("    ✓ WHERE 字段不存在错误正确（E006）")

    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return True


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="QueryCSV — CSV 数据 SQL 查询与导出工具",
        epilog="示例: python scripts/main.py data.csv 'SELECT * FROM t WHERE age > 25' -o result.csv",
    )
    parser.add_argument("csv", nargs="?", help="CSV 文件路径、URL 或文本")
    parser.add_argument("sql", nargs="?", help="SQL 查询语句")
    parser.add_argument("--table", default="t", help="表名（默认: t）")
    parser.add_argument("-o", "--output", help="导出文件路径")
    parser.add_argument("--format", choices=["csv", "json", "markdown"], default="csv", help="导出格式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    if not args.csv or not args.sql:
        parser.print_help()
        err("E001", "需要提供 CSV 数据源和 SQL 查询")

    # 加载数据
    table = CSVLoader.load(args.csv, args.table)

    # 执行查询
    parser = SQLParser({args.table: table})
    executor = QueryExecutor(parser)
    result = executor.execute(args.sql)

    # 导出结果
    if args.format == "csv":
        output = result.to_csv()
    elif args.format == "json":
        output = result.to_json()
    elif args.format == "markdown":
        output = result.to_markdown()
    else:
        err("E001", f"不支持的导出格式: {args.format}")

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"结果已导出到: {args.output}")
        except Exception as e:
            err("E008", str(e))
    else:
        print(output)


if __name__ == "__main__":
    main()
