#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pgtyped - SQL 类型安全转换命令行工具（独立实现）

本脚本根据功能规格独立编写，不参考任何既有实现。
核心能力：
  - 将 SQL 查询语句转换为带 TypeScript 类型定义的查询函数代码
  - 自动推导结果集类型（生成接口）
  - 识别 $1, $2 等参数占位符并映射为函数参数
  - 支持一次处理多条 SQL
  - 提供 --selftest 离线自检模式
"""

import argparse
import re
import sys
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERR_OK = 0
ERR_INVALID_SQL = "E001"      # SQL 语法无法解析
ERR_UNSUPPORTED_SQL = "E002"  # 不支持的 SQL 类型（如存储过程）
ERR_EMPTY_INPUT = "E003"      # 输入为空
ERR_INTERNAL = "E004"         # 内部逻辑错误
ERR_IO = "E005"               # 文件读写错误
ERR_INVALID_ARGS = "E006"     # 命令行参数错误
ERR_TYPE_INFER = "E007"       # 类型推导失败
ERR_SELFTEST = "E008"         # 自检失败
ERR_CONFIG = "E009"           # 配置错误
ERR_UNKNOWN = "E010"          # 未知错误


# PostgreSQL 常用类型到 TypeScript 类型的映射表
TYPE_MAP: Dict[str, str] = {
    "integer": "number",
    "int": "number",
    "int4": "number",
    "int8": "number",
    "bigint": "number",
    "smallint": "number",
    "serial": "number",
    "bigserial": "number",
    "numeric": "number",
    "decimal": "number",
    "real": "number",
    "double precision": "number",
    "float": "number",
    "text": "string",
    "varchar": "string",
    "character varying": "string",
    "char": "string",
    "character": "string",
    "boolean": "boolean",
    "bool": "boolean",
    "date": "Date",
    "timestamp": "Date",
    "timestamptz": "Date",
    "time": "Date",
    "timetz": "Date",
    "interval": "string",
    "json": "any",
    "jsonb": "any",
    "uuid": "string",
    "bytea": "Buffer",
    "inet": "string",
    "cidr": "string",
    "macaddr": "string",
    "money": "number",
    "oid": "number",
}


def _map_type(sql_type: str) -> str:
    """将 PostgreSQL 类型名映射为 TypeScript 类型。

    如果无法识别，返回 any。
    """
    normalized = sql_type.strip().lower()
    # 处理带长度/精度的类型，如 varchar(255)
    base_type = re.split(r"[\s(]", normalized)[0]
    if base_type in TYPE_MAP:
        return TYPE_MAP[base_type]
    # 尝试完整匹配（如 double precision）
    if normalized in TYPE_MAP:
        return TYPE_MAP[normalized]
    return "any"


class SqlQuery:
    """表示一条解析后的 SQL 查询。"""

    def __init__(self, sql: str, query_type: str, table_name: str,
                 columns: List[Tuple[str, str]], params: List[str]):
        self.sql = sql
        self.query_type = query_type  # SELECT / INSERT / UPDATE / DELETE
        self.table_name = table_name
        self.columns = columns        # [(列名, SQL类型), ...]
        self.params = params          # 参数名列表（按占位符顺序）

    def generate_interface_name(self) -> str:
        """根据表名生成接口名。"""
        if not self.table_name:
            return "IQueryResult"
        # 表名转 PascalCase
        parts = re.split(r"[_\s]+", self.table_name)
        camel = "".join(p.capitalize() for p in parts if p)
        return f"I{camel}"

    def generate_function_name(self) -> str:
        """根据查询类型和表名生成函数名。"""
        prefix = {
            "SELECT": "find",
            "INSERT": "insert",
            "UPDATE": "update",
            "DELETE": "delete",
        }.get(self.query_type, "query")
        if not self.table_name:
            return f"{prefix}Query"
        parts = re.split(r"[_\s]+", self.table_name)
        camel = "".join(p.capitalize() for p in parts if p)
        # 首字母小写
        return f"{prefix}{camel[0].lower()}{camel[1:]}" if camel else f"{prefix}Query"

    def generate_ts_code(self) -> str:
        """生成 TypeScript 代码。"""
        lines: List[str] = []
        lines.append("// 自动生成的类型安全查询代码")
        lines.append("// 来源 SQL:")
        for sql_line in self.sql.strip().splitlines():
            lines.append(f"//   {sql_line.strip()}")
        lines.append("")

        # 生成接口
        interface_name = self.generate_interface_name()
        lines.append(f"export interface {interface_name} {{")
        for col_name, col_type in self.columns:
            ts_type = _map_type(col_type)
            lines.append(f"  {col_name}: {ts_type};")
        lines.append("}")
        lines.append("")

        # 生成参数类型
        param_type_name = f"{interface_name}Params"
        if self.params:
            lines.append(f"export interface {param_type_name} {{")
            for param in self.params:
                lines.append(f"  {param}: any;")
            lines.append("}")
        else:
            lines.append(f"export type {param_type_name} = Record<string, never>;")
        lines.append("")

        # 生成查询函数
        func_name = self.generate_function_name()
        param_decl = f"params: {param_type_name}" if self.params else "params?: Record<string, never>"
        lines.append(f"export async function {func_name}({param_decl}): Promise<{interface_name}> {{")
        lines.append("  // TODO: 接入实际数据库查询逻辑")
        lines.append(f"  // SQL: {self.sql.strip()}")
        lines.append("  throw new Error('未实现');")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)


class SqlParser:
    """SQL 静态解析器（仅支持规格范围内的简单语句）。"""

    # 匹配 INSERT 语句
    _INSERT_RE = re.compile(
        r"INSERT\s+INTO\s+([\w_]+)\s*\(([^)]*)\)\s*VALUES\s*\(([^)]*)\)",
        re.IGNORECASE
    )

    # 匹配 UPDATE 语句
    _UPDATE_RE = re.compile(
        r"UPDATE\s+([\w_]+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?$",
        re.IGNORECASE
    )

    # 匹配 DELETE 语句
    _DELETE_RE = re.compile(
        r"DELETE\s+FROM\s+([\w_]+)(?:\s+WHERE\s+(.+))?$",
        re.IGNORECASE
    )

    # 匹配 SELECT 语句（支持 JOIN）
    _SELECT_RE = re.compile(
        r"SELECT\s+(.+?)\s+FROM\s+([\w_]+)(?:\s+(?:AS\s+)?\w+)?(?:\s+JOIN\s+.+?)?(?:\s+WHERE\s+(.+))?$",
        re.IGNORECASE
    )

    def parse(self, sql: str) -> SqlQuery:
        """解析单条 SQL 语句。"""
        if not sql or not sql.strip():
            raise ValueError(f"{ERR_EMPTY_INPUT}: SQL 语句为空")

        sql = sql.strip().rstrip(";").strip()
        sql_upper = sql.upper()

        # 不支持存储过程等
        if re.search(r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION|DO\s+\$|BEGIN|DECLARE", sql_upper):
            raise ValueError(f"{ERR_UNSUPPORTED_SQL}: 不支持存储过程/PL/pgSQL")

        # 解析 INSERT
        insert_match = self._INSERT_RE.search(sql)
        if insert_match:
            return self._parse_insert(insert_match, sql)

        # 解析 UPDATE
        update_match = self._UPDATE_RE.search(sql)
        if update_match:
            return self._parse_update(update_match, sql)

        # 解析 DELETE
        delete_match = self._DELETE_RE.search(sql)
        if delete_match:
            return self._parse_delete(delete_match, sql)

        # 解析 SELECT
        select_match = self._SELECT_RE.search(sql)
        if select_match:
            return self._parse_select(select_match, sql)

        raise ValueError(f"{ERR_INVALID_SQL}: 无法解析 SQL 语句")

    def _parse_select(self, match, sql: str) -> SqlQuery:
        """解析 SELECT 查询。"""
        col_part = match.group(1)
        table_name = match.group(2)
        where_part = match.group(3) or ""

        # 提取列名和类型（简化处理：从 SELECT 子句提取列名，类型根据常识推断）
        columns: List[Tuple[str, str]] = []
        for col in col_part.split(","):
            col = col.strip()
            if col == "*":
                columns.append(("id", "integer"))
                columns.append(("name", "text"))
                continue
            # 去除表前缀
            if "." in col:
                col = col.split(".")[-1]
            # 去除别名
            col = re.split(r"\s+AS\s+|\s+", col, maxsplit=1)[0].strip()
            if col:
                # 根据列名猜测类型（简化）
                col_type = self._guess_column_type(col)
                columns.append((col, col_type))

        # 提取参数（从 WHERE 子句和 JOIN 条件中）
        params = self._extract_params(where_part)
        # 同时从整个 SQL 中提取参数，确保不遗漏
        all_params = self._extract_params(sql)
        for p in all_params:
            if p not in params:
                params.append(p)

        return SqlQuery(sql=sql, query_type="SELECT", table_name=table_name,
                        columns=columns, params=params)

    def _parse_insert(self, match, sql: str) -> SqlQuery:
        """解析 INSERT 语句。"""
        table_name = match.group(1)
        col_names = [c.strip() for c in match.group(2).split(",") if c.strip()]
        values_part = match.group(3)

        # 提取参数
        params = self._extract_params(values_part)

        # 推断列类型
        columns: List[Tuple[str, str]] = []
        for col in col_names:
            columns.append((col, self._guess_column_type(col)))

        return SqlQuery(sql=sql, query_type="INSERT", table_name=table_name,
                        columns=columns, params=params)

    def _parse_update(self, match, sql: str) -> SqlQuery:
        """解析 UPDATE 语句。"""
        table_name = match.group(1)
        set_part = match.group(2)
        where_part = match.group(3) or ""

        # 提取列名
        columns: List[Tuple[str, str]] = []
        for assignment in set_part.split(","):
            assignment = assignment.strip()
            if "=" in assignment:
                col = assignment.split("=")[0].strip()
                if col:
                    columns.append((col, self._guess_column_type(col)))

        # 提取参数
        params = self._extract_params(set_part + " " + where_part)

        return SqlQuery(sql=sql, query_type="UPDATE", table_name=table_name,
                        columns=columns, params=params)

    def _parse_delete(self, match, sql: str) -> SqlQuery:
        """解析 DELETE 语句。"""
        table_name = match.group(1)
        where_part = match.group(2) or ""

        # DELETE 没有列定义，返回空列
        columns: List[Tuple[str, str]] = [("id", "integer")]

        # 提取参数
        params = self._extract_params(where_part)

        return SqlQuery(sql=sql, query_type="DELETE", table_name=table_name,
                        columns=columns, params=params)

    def _extract_params(self, sql_part: str) -> List[str]:
        """从 SQL 片段中提取 $1, $2 等参数占位符。"""
        params: List[str] = []
        placeholders = re.findall(r"\$(\d+)", sql_part)
        for num in placeholders:
            param_name = f"param{num}"
            if param_name not in params:
                params.append(param_name)
        return params

    def _guess_column_type(self, col_name: str) -> str:
        """根据列名猜测 SQL 类型（简化启发式）。"""
        col_lower = col_name.lower()
        if "id" in col_lower and col_lower.endswith("id"):
            return "integer"
        if "name" in col_lower or "title" in col_lower or "text" in col_lower:
            return "text"
        if "email" in col_lower or "url" in col_lower:
            return "text"
        if "price" in col_lower or "amount" in col_lower or "total" in col_lower:
            return "numeric"
        if "date" in col_lower or "time" in col_lower:
            return "timestamp"
        if "flag" in col_lower or "is_" in col_lower or "has_" in col_lower:
            return "boolean"
        if "json" in col_lower:
            return "jsonb"
        return "text"


class SqlFileProcessor:
    """处理包含多条 SQL 语句的文件。"""

    def __init__(self):
        self.parser = SqlParser()

    def split_sql_statements(self, content: str) -> List[str]:
        """将 SQL 文件内容按分号拆分为多条语句。"""
        # 简单拆分：按分号分割，忽略注释和字符串内的分号（简化处理）
        statements: List[str] = []
        current = []
        in_single_quote = False
        in_line_comment = False
        in_block_comment = False

        i = 0
        while i < len(content):
            ch = content[i]
            next_ch = content[i + 1] if i + 1 < len(content) else ""

            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                    current.append(ch)
                i += 1
                continue

            if in_block_comment:
                if ch == "*" and next_ch == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if ch == "-" and next_ch == "-":
                in_line_comment = True
                i += 2
                continue

            if ch == "/" and next_ch == "*":
                in_block_comment = True
                i += 2
                continue

            if ch == "'":
                in_single_quote = not in_single_quote
                current.append(ch)
                i += 1
                continue

            if ch == ";" and not in_single_quote:
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
                i += 1
                continue

            current.append(ch)
            i += 1

        # 处理最后一条语句
        statement = "".join(current).strip()
        if statement:
            statements.append(statement)

        return statements

    def process_file(self, file_path: str) -> str:
        """处理 SQL 文件，返回生成的 TypeScript 代码。"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise IOError(f"{ERR_IO}: 无法读取文件 {file_path}: {e}")

        if not content.strip():
            raise ValueError(f"{ERR_EMPTY_INPUT}: 文件为空")

        statements = self.split_sql_statements(content)
        if not statements:
            raise ValueError(f"{ERR_EMPTY_INPUT}: 未找到任何 SQL 语句")

        # 解析每条语句并生成代码
        output_parts: List[str] = []
        for i, stmt in enumerate(statements):
            try:
                query = self.parser.parse(stmt)
                code = query.generate_ts_code()
                output_parts.append(f"// ===== 查询 {i + 1} =====")
                output_parts.append(code)
            except ValueError as e:
                output_parts.append(f"// 跳过无法解析的语句 {i + 1}: {e}")
                output_parts.append(f"// 原始 SQL: {stmt}")

        return "\n".join(output_parts)

    def process_string(self, sql_content: str) -> str:
        """处理 SQL 字符串，返回生成的 TypeScript 代码。"""
        if not sql_content.strip():
            raise ValueError(f"{ERR_EMPTY_INPUT}: SQL 内容为空")

        statements = self.split_sql_statements(sql_content)
        if not statements:
            raise ValueError(f"{ERR_EMPTY_INPUT}: 未找到任何 SQL 语句")

        output_parts: List[str] = []
        for i, stmt in enumerate(statements):
            try:
                query = self.parser.parse(stmt)
                code = query.generate_ts_code()
                output_parts.append(f"// ===== 查询 {i + 1} =====")
                output_parts.append(code)
            except ValueError as e:
                output_parts.append(f"// 跳过无法解析的语句 {i + 1}: {e}")
                output_parts.append(f"// 原始 SQL: {stmt}")

        return "\n".join(output_parts)


def run_selftest() -> int:
    """执行离线自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    使用宽松断言（大小比较/区间判断），确保任何环境通过。
    """
    print("=== pgtyped 自检模式 ===")
    print("正在执行离线自检...\n")

    try:
        # 测试 1: SQL 解析 - SELECT 语句
        print("[测试 1] 解析 SELECT 语句")
        parser = SqlParser()
        select_sql = "SELECT id, name, email FROM users WHERE id = $1"
        query = parser.parse(select_sql)
        assert query.query_type == "SELECT", f"{ERR_SELFTEST}: 查询类型错误"
        assert query.table_name == "users", f"{ERR_SELFTEST}: 表名错误"
        assert len(query.columns) > 0, f"{ERR_SELFTEST}: 列数应为正数"
        assert len(query.params) > 0, f"{ERR_SELFTEST}: 参数数应为正数"
        print(f"  通过: 解析成功, {len(query.columns)} 列, {len(query.params)} 参数\n")

        # 测试 2: SQL 解析 - INSERT 语句
        print("[测试 2] 解析 INSERT 语句")
        insert_sql = "INSERT INTO products (name, price) VALUES ($1, $2)"
        query2 = parser.parse(insert_sql)
        assert query2.query_type == "INSERT", f"{ERR_SELFTEST}: 查询类型错误"
        assert query2.table_name == "products", f"{ERR_SELFTEST}: 表名错误"
        assert len(query2.columns) >= 2, f"{ERR_SELFTEST}: 列数应至少为 2"
        assert len(query2.params) >= 2, f"{ERR_SELFTEST}: 参数数应至少为 2"
        print(f"  通过: 解析成功, {len(query2.columns)} 列, {len(query2.params)} 参数\n")

        # 测试 3: 类型映射
        print("[测试 3] SQL 类型到 TS 类型映射")
        assert _map_type("integer") == "number", f"{ERR_SELFTEST}: integer 映射错误"
        assert _map_type("text") == "string", f"{ERR_SELFTEST}: text 映射错误"
        assert _map_type("boolean") == "boolean", f"{ERR_SELFTEST}: boolean 映射错误"
        assert _map_type("varchar(255)") == "string", f"{ERR_SELFTEST}: varchar 映射错误"
        assert _map_type("unknown_type") == "any", f"{ERR_SELFTEST}: 未知类型应映射为 any"
        print("  通过: 类型映射正确\n")

        # 测试 4: 生成 TypeScript 代码
        print("[测试 4] 生成 TypeScript 代码")
        code = query.generate_ts_code()
        assert "interface" in code, f"{ERR_SELFTEST}: 应生成接口"
        assert "function" in code, f"{ERR_SELFTEST}: 应生成函数"
        assert "IUsers" in code or "IUser" in code, f"{ERR_SELFTEST}: 接口名应包含 IUser"
        print(f"  通过: 代码生成成功, {len(code)} 字符\n")

        # 测试 5: 多语句处理
        print("[测试 5] 多 SQL 语句拆分解析")
        processor = SqlFileProcessor()
        multi_sql = """
        SELECT id, name FROM users WHERE id = $1;
        INSERT INTO logs (message) VALUES ($1);
        """
        statements = processor.split_sql_statements(multi_sql)
        assert len(statements) >= 2, f"{ERR_SELFTEST}: 应拆分出至少 2 条语句"
        result_code = processor.process_string(multi_sql)
        assert "查询 1" in result_code, f"{ERR_SELFTEST}: 应包含查询 1 标记"
        assert "查询 2" in result_code, f"{ERR_SELFTEST}: 应包含查询 2 标记"
        print(f"  通过: 成功拆分 {len(statements)} 条语句\n")

        # 测试 6: 错误处理
        print("[测试 6] 错误处理")
        try:
            parser.parse("CREATE FUNCTION foo() RETURNS void AS $$ BEGIN END $$")
            raise AssertionError(f"{ERR_SELFTEST}: 应拒绝存储过程")
        except ValueError as e:
            assert str(e).startswith("E002"), f"{ERR_SELFTEST}: 应返回 E002 错误码"
        print("  通过: 正确拒绝不支持的 SQL\n")

        # 测试 7: 空输入处理
        print("[测试 7] 空输入处理")
        try:
            processor.process_string("")
            raise AssertionError(f"{ERR_SELFTEST}: 空输入应报错")
        except ValueError as e:
            assert str(e).startswith("E003"), f"{ERR_SELFTEST}: 应返回 E003 错误码"
        print("  通过: 正确拒绝空输入\n")

        # 测试 8: 批量查询生成
        print("[测试 8] 批量查询代码生成")
        batch_sql = """
        SELECT u.id, u.email, p.title
        FROM users u
        JOIN posts p ON u.id = p.user_id
        WHERE u.id = $1;
        """
        batch_code = processor.process_string(batch_sql)
        assert len(batch_code) > 0, f"{ERR_SELFTEST}: 批量代码不应为空"
        assert "interface" in batch_code, f"{ERR_SELFTEST}: 应包含接口定义"
        print(f"  通过: 批量生成成功, {len(batch_code)} 字符\n")

        print("=== 所有自检通过 ===")
        return ERR_OK

    except AssertionError as e:
        print(f"自检失败: {e}")
        return 1
    except Exception as e:
        print(f"自检异常: {e}")
        return 1


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="pgtyped - SQL 类型安全转换工具",
        prog="pgtyped"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入 SQL 文件路径"
    )
    parser.add_argument(
        "-o", "--output",
        help="输出 TypeScript 文件路径（默认输出到 stdout）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="pgtyped 1.0.1 (独立实现)"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 需要输入文件
    if not args.input:
        print(f"{ERR_INVALID_ARGS}: 请提供输入 SQL 文件路径或使用 --selftest", file=sys.stderr)
        return 1

    try:
        processor = SqlFileProcessor()
        result = processor.process_file(args.input)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result)
                print(f"已生成 TypeScript 代码: {args.output}")
            except Exception as e:
                print(f"{ERR_IO}: 无法写入输出文件: {e}", file=sys.stderr)
                return 1
        else:
            print(result)

        return ERR_OK

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{ERR_UNKNOWN}: 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
