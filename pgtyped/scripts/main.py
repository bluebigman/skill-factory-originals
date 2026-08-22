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
import os
import re
import sys
import tempfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

try:
    import sqlparse
    HAS_SQLPARSE = True
except ImportError:
    HAS_SQLPARSE = False

# 尝试导入 fcntl（Unix 平台）
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

dry_run = False  # v3.274 模块级 dry-run 标志

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


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    raise UnicodeDecodeError(
        f"无法以 utf-8/gbk/gb18030 编码读取文件 {path}，请检查文件编码"
    )


def _write_text_safe(path, content):
    """原子写入文件（临时文件 + os.replace）"""
    dir_name = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".pgtyped_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _iter_lines(path):
    """流式读取文件行，使用与 _read_text_safe 相同的编码回退逻辑"""
    content = _read_text_safe(path)
    for line in content.splitlines():
        yield line


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
    """SQL 静态解析器（支持简单语句，复杂语句使用 sqlparse 辅助）。"""

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

        # 尝试使用 sqlparse 解析复杂查询
        if HAS_SQLPARSE:
            try:
                return self._parse_with_sqlparse(sql)
            except Exception:
                pass

        raise ValueError(f"{ERR_INVALID_SQL}: 无法解析 SQL 语句")

    def _parse_with_sqlparse(self, sql: str) -> SqlQuery:
        """使用 sqlparse 解析复杂查询。"""
        import sqlparse
        parsed = sqlparse.parse(sql)
        if not parsed:
            raise ValueError(f"{ERR_INVALID_SQL}: 无法解析 SQL 语句")

        stmt = parsed[0]
        query_type = stmt.get_type().upper()
        table_name = ""
        columns: List[Tuple[str, str]] = []
        params: List[str] = []

        # 提取表名
        from_seen = False
        for token in stmt.tokens:
            if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
                from_seen = True
                continue
            if from_seen and token.ttype is sqlparse.tokens.Name:
                table_name = token.value
                break

        # 提取列名（简化处理）
        if query_type == "SELECT":
            select_part = str(stmt).split("FROM")[0] if "FROM" in str(stmt) else str(stmt)
            for col in select_part.replace("SELECT", "").split(","):
                col = col.strip()
                if col and col != "*":
                    # 去除表前缀和别名
                    col = re.sub(r"^[\w]+\.", "", col)
                    col = re.split(r"\s+AS\s+|\s+", col, maxsplit=1)[0].strip()
                    if col:
                        columns.append((col, self._guess_column_type(col)))

        # 提取参数
        params = self._extract_params(sql)

        return SqlQuery(sql=sql, query_type=query_type, table_name=table_name,
                        columns=columns, params=params)

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
        # 简单
