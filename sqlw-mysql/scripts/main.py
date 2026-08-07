#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqlw-mysql: MySQL 代码生成 / 查询包装 / 文本转换工具

本脚本依据功能规格独立实现（clean-room），不依赖任何既有代码。
支持将 MySQL 查询文本解析为结构化中间表示，并生成多种目标语言的包装代码。

用法示例:
    python scripts/main.py --selftest          # 离线自检（推荐）
    python scripts/main.py --version           # 显示版本信息
    python scripts/main.py --help              # 显示帮助
    python scripts/main.py "SELECT * FROM users WHERE id = ?"
    python scripts/main.py --format python "SELECT name FROM t WHERE age > 18"
    python scripts/main.py --lang java --template custom "SELECT 1"

错误码说明:
    E001: 参数解析失败
    E002: 输入内容为空
    E003: 无法识别的 SQL 语句类型
    E004: 无法提取表名
    E005: 无法提取字段列表
    E006: 不支持的目标语言
    E007: 模板渲染失败
    E008: 内部状态异常
    E009: 输出写入失败
    E010: 未知错误
"""

import argparse
import json
import re
import sys
import textwrap
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 版本与元数据
# ---------------------------------------------------------------------------
__version__ = "1.0.1"
SKILL_NAME = "sqlw-mysql"
DISPLAY_NAME = "MySQL 代码生成 查询包装 文本转换"
DESCRIPTION = "为 MySQL 数据库与查询生成包装代码或文本源，支持批量与自定义格式。"
LICENSE = "MIT"
COPYRIGHT = "© 2026 SkillForge Lab. All rights reserved."


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class ParsedQuery:
    """SQL 查询的结构化中间表示"""
    raw_text: str
    query_type: str                    # SELECT / INSERT / UPDATE / DELETE / 其他
    table_names: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    placeholders: List[str] = field(default_factory=list)
    where_clause: str = ""
    confidence: str = "低"             # 高 / 中 / 低
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典（用于 JSON 序列化）"""
        return asdict(self)


@dataclass
class GenerationResult:
    """生成结果"""
    language: str
    content: str
    confidence: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------
class SQLParser:
    """MySQL 查询解析器（正则表达式为主，轻量实现）"""

    # 常用 MySQL 关键字
    _KEYWORDS = {
        "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES",
        "UPDATE", "SET", "DELETE", "JOIN", "LEFT", "RIGHT", "INNER",
        "OUTER", "ON", "GROUP", "BY", "ORDER", "HAVING", "LIMIT",
        "OFFSET", "AND", "OR", "NOT", "NULL", "AS", "DISTINCT",
        "UNION", "ALL", "CASE", "WHEN", "THEN", "ELSE", "END",
        "EXISTS", "IN", "BETWEEN", "LIKE", "IS", "ASC", "DESC"
    }

    # 简单占位符匹配：? 或 :name 或 %s
    _PLACEHOLDER_RE = re.compile(r"(\?|:[a-zA-Z_][a-zA-Z0-9_]*|%s)")

    # 表名提取（用于 FROM / JOIN / INTO / UPDATE 子句）
    _TABLE_RE = re.compile(
        r"(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+"
        r"`?([a-zA-Z_][a-zA-Z0-9_]*)"           # 表名（可能带反引号）
        r"`?(?:\s+(?:AS\s+)?[a-zA-Z_][a-zA-Z0-9_]*)?",  # 可选别名
        re.IGNORECASE
    )

    # 字段提取（SELECT 子句中的逗号分隔字段）
    _SELECT_COLUMNS_RE = re.compile(
        r"SELECT\s+(.+?)\s+FROM",
        re.IGNORECASE | re.DOTALL
    )

    # WHERE 子句提取
    _WHERE_RE = re.compile(r"WHERE\s+(.+?)(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$)",
                           re.IGNORECASE | re.DOTALL)

    # 常见聚合函数（用于识别字段）
    _AGG_FUNCS = {"COUNT", "SUM", "AVG", "MIN", "MAX"}

    # 字段名模式（字母开头，可含数字和下划线，可选表名前缀）
    _COLUMN_NAME_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*$")

    def parse(self, sql_text: str) -> ParsedQuery:
        """解析 SQL 文本，返回结构化表示"""
        if not sql_text or not sql_text.strip():
            raise ValueError("E002: 输入内容为空")

        raw = sql_text.strip()
        # 去除末尾分号
        if raw.endswith(";"):
            raw = raw[:-1].strip()

        # 识别查询类型
        query_type = self._detect_query_type(raw)
        if query_type == "未知":
            raise ValueError(f"E003: 无法识别的 SQL 语句类型: {raw[:50]}...")

        # 提取表名
        tables = self._extract_tables(raw)
        if not tables:
            raise ValueError(f"E004: 无法提取表名: {raw[:50]}...")

        # 提取字段
        columns = self._extract_columns(raw, query_type)
        if not columns:
            raise ValueError(f"E005: 无法提取字段列表: {raw[:50]}...")

        # 提取占位符
        placeholders = self._extract_placeholders(raw)

        # 提取 WHERE 子句
        where_clause = self._extract_where(raw)

        # 计算置信度
        confidence, warnings = self._assess_confidence(
            raw, query_type, tables, columns, placeholders
        )

        return ParsedQuery(
            raw_text=raw,
            query_type=query_type,
            table_names=tables,
            columns=columns,
            placeholders=placeholders,
            where_clause=where_clause,
            confidence=confidence,
            warnings=warnings
        )

    def _detect_query_type(self, sql: str) -> str:
        """识别 SQL 查询类型"""
        first_word = sql.split()[0].upper() if sql.split() else ""
        if first_word == "SELECT":
            return "SELECT"
        elif first_word == "INSERT":
            return "INSERT"
        elif first_word == "UPDATE":
            return "UPDATE"
        elif first_word == "DELETE":
            return "DELETE"
        elif first_word == "CREATE":
            return "CREATE"
        elif first_word == "ALTER":
            return "ALTER"
        elif first_word == "DROP":
            return "DROP"
        else:
            return "未知"

    def _extract_tables(self, sql: str) -> List[str]:
        """提取表名（去重，保持顺序）"""
        tables = []
        seen = set()
        for match in self._TABLE_RE.finditer(sql):
            table = match.group(1)
            if table and table.upper() not in seen:
                tables.append(table)
                seen.add(table.upper())
        return tables

    def _extract_columns(self, sql: str, query_type: str) -> List[str]:
        """提取字段名列表"""
        columns = []

        if query_type == "SELECT":
            # 从 SELECT 子句中提取
            match = self._SELECT_COLUMNS_RE.search(sql)
            if match:
                select_part = match.group(1)
                # 分割逗号，处理嵌套（简单处理）
                parts = self._split_top_level(select_part, ",")
                for part in parts:
                    col = self._clean_column_name(part)
                    if col and col.upper() != "DISTINCT":
                        columns.append(col)
        elif query_type == "INSERT":
            # INSERT INTO table (col1, col2) VALUES ...
            in_paren = re.search(r"\((.*?)\)\s*(?:VALUES|SELECT)", sql, re.IGNORECASE)
            if in_paren:
                parts = self._split_top_level(in_paren.group(1), ",")
                for part in parts:
                    col = part.strip().strip("`")
                    if col:
                        columns.append(col)
        elif query_type == "UPDATE":
            # UPDATE table SET col1 = val1, col2 = val2 WHERE ...
            set_match = re.search(r"SET\s+(.+?)(?:WHERE|$)", sql, re.IGNORECASE | re.DOTALL)
            if set_match:
                parts = self._split_top_level(set_match.group(1), ",")
                for part in parts:
                    col = part.split("=")[0].strip().strip("`")
                    if col:
                        columns.append(col)
        elif query_type == "DELETE":
            # DELETE FROM table WHERE ...
            # 通常没有字段列表，使用 * 作为占位
            columns = ["*"]
        else:
            # 其他类型（CREATE / ALTER / DROP），尝试从括号中提取
            in_paren = re.search(r"\((.*?)\)", sql, re.DOTALL)
            if in_paren:
                parts = self._split_top_level(in_paren.group(1), ",")
                for part in parts:
                    first_word = part.strip().split()[0].strip("`")
                    if first_word and first_word.upper() not in self._KEYWORDS:
                        columns.append(first_word)

        # 去重（保持顺序）
        result = []
        seen = set()
        for col in columns:
            key = col.upper()
            if key not in seen:
                result.append(col)
                seen.add(key)

        return result

    def _extract_placeholders(self, sql: str) -> List[str]:
        """提取参数占位符"""
        return self._PLACEHOLDER_RE.findall(sql)

    def _extract_where(self, sql: str) -> str:
        """提取 WHERE 子句内容"""
        match = self._WHERE_RE.search(sql)
        if match:
            return match.group(1).strip()
        return ""

    def _split_top_level(self, text: str, delimiter: str) -> List[str]:
        """按分隔符分割，忽略括号内的内容"""
        parts = []
        depth = 0
        current = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in "([{":
                depth += 1
                current.append(ch)
            elif ch in ")]}":
                depth -= 1
                current.append(ch)
            elif ch == delimiter and depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
            i += 1
        if current:
            parts.append("".join(current).strip())
        return [p for p in parts if p]

    def _clean_column_name(self, part: str) -> str:
        """清理字段名：去除别名、函数包裹等"""
        part = part.strip()
        if not part:
            return ""

        # 去除 AS 别名
        as_match = re.search(r"\s+AS\s+([a-zA-Z_][a-zA-Z0-9_]*)$", part, re.IGNORECASE)
        if as_match:
            part = part[:part.lower().rfind(" as ")].strip()

        # 去除表名前缀（如 t.name -> name）
        if "." in part:
            part = part.split(".")[-1].strip()

        # 去除反引号
        part = part.strip("`")

        # 如果包含函数调用，提取内部字段
        func_match = re.search(r"([A-Z_]+)\((.*?)\)", part, re.IGNORECASE)
        if func_match:
            func_name = func_match.group(1).upper()
            inner = func_match.group(2).strip()
            if func_name in self._AGG_FUNCS and inner:
                # 聚合函数内部可能包含字段
                if inner == "*":
                    return f"{func_name}(*)"
                # 递归清理内部字段
                cleaned_inner = self._clean_column_name(inner)
                if cleaned_inner:
                    return f"{func_name}({cleaned_inner})"
            return ""

        # 最终验证：必须是合法字段名
        if self._COLUMN_NAME_RE.match(part):
            return part
        return ""

    def _assess_confidence(self, sql: str, query_type: str,
                           tables: List[str], columns: List[str],
                           placeholders: List[str]) -> Tuple[str, List[str]]:
        """评估解析置信度"""
        warnings = []
        score = 0

        # 基本规则
        if query_type in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            score += 3
        else:
            score += 1
            warnings.append("非标准 DML 语句，解析可能不完整")

        if len(tables) >= 1:
            score += 2
        else:
            warnings.append("未识别到表名")

        if len(columns) >= 1:
            score += 2
        else:
            warnings.append("未识别到字段")

        if placeholders:
            score += 1
            warnings.append(f"检测到 {len(placeholders)} 个参数占位符")

        # 复杂查询降置信度
        if "JOIN" in sql.upper():
            score -= 1
            warnings.append("包含 JOIN，表关系可能复杂")
        if "SUBQUERY" in sql.upper() or "SELECT" in sql.upper().replace("SELECT", "", 1):
            score -= 1
            warnings.append("可能包含子查询")

        # 确定置信度等级
        if score >= 7:
            confidence = "高"
        elif score >= 4:
            confidence = "中"
        else:
            confidence = "低"

        return confidence, warnings


# ---------------------------------------------------------------------------
# 代码生成器
# ---------------------------------------------------------------------------
class CodeGenerator:
    """为不同语言生成 MySQL 包装代码"""

    # 支持的语言及其文件扩展名
    SUPPORTED_LANGS = {
        "python": ".py",
        "java": ".java",
        "go": ".go",
        "node": ".js",
        "javascript": ".js",
        "markdown": ".md",
        "json": ".json",
    }

    def generate(self, parsed: ParsedQuery, language: str,
                 template: Optional[str] = None) -> GenerationResult:
        """生成指定语言的包装代码"""
        lang = language.lower()
        if lang not in self.SUPPORTED_LANGS:
            raise ValueError(f"E006: 不支持的目标语言: {language}")

        # 如果提供了自定义模板，使用模板渲染
        if template:
            try:
                content = self._render_template(template, parsed)
            except Exception as e:
                raise ValueError(f"E007: 模板渲染失败: {str(e)}")
        else:
            # 使用内置生成器
            generator_map = {
                "python": self._gen_python,
                "java": self._gen_java,
                "go": self._gen_go,
                "node": self._gen_node,
                "javascript": self._gen_node,
                "markdown": self._gen_markdown,
                "json": self._gen_json,
            }
            content = generator_map[lang](parsed)

        return GenerationResult(
            language=lang,
            content=content,
            confidence=parsed.confidence,
            warnings=parsed.warnings
        )

    def _render_template(self, template: str, parsed: ParsedQuery) -> str:
        """简单模板渲染：支持 {table}、{columns}、{placeholders} 等占位符"""
        result = template
        result = result.replace("{query_type}", parsed.query_type)
        result = result.replace("{table}", parsed.table_names[0] if parsed.table_names else "")
        result = result.replace("{tables}", ", ".join(parsed.table_names))
        result = result.replace("{columns}", ", ".join(parsed.columns))
        result = result.replace("{placeholders}", ", ".join(parsed.placeholders))
        result = result.replace("{where}", parsed.where_clause)
        result = result.replace("{raw_sql}", parsed.raw_text)
        result = result.replace("{confidence}", parsed.confidence)
        return result

    def _gen_python(self, p: ParsedQuery) -> str:
        """生成 Python 包装代码"""
        table = p.table_names[0] if p.table_names else "table"
        cols = ", ".join(f"'{c}'" for c in p.columns)
        placeholders = p.placeholders if p.placeholders else ["?"]

        code = textwrap.dedent(f'''\
        # 自动生成的 MySQL 查询包装代码
        # 表: {table}
        # 查询类型: {p.query_type}
        # 置信度: {p.confidence}

        import mysql.connector  # pip install mysql-connector-python

        def query_{table}(cursor, {", ".join(f"param_{i}" for i in range(len(placeholders)))}):
            \"\"\"执行 {p.query_type} 查询\"\"\"
            sql = """{p.raw_text}"""
            params = ({", ".join(f"param_{i}" for i in range(len(placeholders)))},)
            cursor.execute(sql, params)
            return cursor.fetchall()

        # 使用示例:
        # conn = mysql.connector.connect(host="localhost", user="root", password="", database="mydb")
        # cursor = conn.cursor()
        # results = query_{table}(cursor, param_0)
        # for row in results:
        #     print(row)
        ''')
        return code

    def _gen_java(self, p: ParsedQuery) -> str:
        """生成 Java 包装代码"""
        table = p.table_names[0] if p.table_names else "Table"
        class_name = f"{table.capitalize()}Query"
        placeholders = p.placeholders if p.placeholders else ["?"]

        params_str = ", ".join(f"Object param{i}" for i in range(len(placeholders)))

        code = textwrap.dedent(f'''\
        // 自动生成的 MySQL 查询包装代码
        // 表: {table}
        // 查询类型: {p.query_type}
        // 置信度: {p.confidence}

        import java.sql.*;

        public class {class_name} {{
            // SQL 语句
            private static final String SQL = "{p.raw_text.replace(chr(34), chr(92) + chr(34))}";

            public static ResultSet execute(Connection conn, {params_str}) throws SQLException {{
                PreparedStatement ps = conn.prepareStatement(SQL);
                {self._java_set_params(len(placeholders))}
                return ps.executeQuery();
            }}

            // 使用示例:
            // Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/mydb", "root", "");
            // ResultSet rs = {class_name}.execute(conn, param0);
        }}
        ''')
        return code

    def _java_set_params(self, count: int) -> str:
        """生成 Java 参数设置代码"""
        lines = []
        for i in range(count):
            lines.append(f"                ps.setObject({i + 1}, param{i});")
        return "\n".join(lines) if lines else "                // 无参数"

    def _gen_go(self, p: ParsedQuery) -> str:
        """生成 Go 包装代码"""
        table = p.table_names[0] if p.table_names else "table"
        placeholders = p.placeholders if p.placeholders else ["?"]

        code = textwrap.dedent(f'''\
        // 自动生成的 MySQL 查询包装代码
        // 表: {table}
        // 查询类型: {p.query_type}
        // 置信度: {p.confidence}

        package main

        import (
            "database/sql"
            _ "github.com/go-sql-driver/mysql" // go get github.com/go-sql-driver/mysql
        )

        const querySQL = `{p.raw_text}`

        func query{table.capitalize()}(db *sql.DB, args ...interface{{}}) (*sql.Rows, error) {{
            rows, err := db.Query(querySQL, args...)
            if err != nil {{
                return nil, err
            }}
            return rows, nil
        }}

        // 使用示例:
        // db, _ := sql.Open("mysql", "root:password@tcp(127.0.0.1:3306)/mydb")
        // rows, err := query{table.capitalize()}(db, param0)
        // defer rows.Close()
        ''')
        return code

    def _gen_node(self, p: ParsedQuery) -> str:
        """生成 Node.js 包装代码"""
        table = p.table_names[0] if p.table_names else "table"
        placeholders = p.placeholders if p.placeholders else ["?"]

        code = textwrap.dedent(f'''\
        // 自动生成的 MySQL 查询包装代码
        // 表: {table}
        // 查询类型: {p.query_type}
        // 置信度: {p.confidence}

        const mysql = require('mysql2/promise');  // npm install mysql2

        async function query{table.capitalize()}(connection, params = []) {{
            const sql = `{p.raw_text}`;
            const [rows] = await connection.execute(sql, params);
            return rows;
        }}

        // 使用示例:
        // const conn = await mysql.createConnection({{host: 'localhost', user: 'root', password: '', database: 'mydb'}});
        // const results = await query{table.capitalize()}(conn, [param0]);
        ''')
        return code

    def _gen_markdown(self, p: ParsedQuery) -> str:
        """生成 Markdown 文档"""
        table = p.table_names[0] if p.table_names else "table"

        code = textwrap.dedent(f'''\
        # 查询文档: {table}

        | 属性 | 值 |
        |------|-----|
        | 查询类型 | {p.query_type} |
        | 涉及表 | {", ".join(p.table_names)} |
        | 字段 | {", ".join(p.columns)} |
        | 参数占位符 | {", ".join(p.placeholders) if p.placeholders else "无"} |
        | 置信度 | {p.confidence} |

        ## SQL 原文
