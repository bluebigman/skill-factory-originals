#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqlw-mysql: MySQL 代码生成 / 查询包装 / 文本转换
=================================================
本脚本依据功能规格独立实现（clean-room），不包含任何既有代码。

能力概览：
    1. 输入解析          ：将 SQL 文本解析为结构化中间表示
    2. 关键信息识别      ：提取表名、字段名、连接条件、参数占位符
    3. 格式生成          ：按指定格式生成包装代码或文本源
    4. 置信度标注        ：对识别结果标注高/中/低置信度
    5. 批量与自定义      ：支持多查询输入与自定义输出模板

命令行用法：
    python scripts/main.py --selftest          # 离线自检（不读外部文件/不联网）
    python scripts/main.py --version           # 输出版本信息
    python scripts/main.py --help              # 显示帮助
    python scripts/main.py -q "SELECT ..."     # 解析单条 SQL
    python scripts/main.py -f file.sql -t py   # 批量解析文件并生成 Python 包装

错误码：
    E001 参数解析失败
    E002 输入 SQL 为空或非法
    E003 无法识别的 SQL 类型（非 SELECT/INSERT/UPDATE/DELETE）
    E004 输出格式不支持
    E005 文件读取失败
    E006 模板渲染失败
    E007 内部状态异常
    E008 输出写入失败
    E009 自检断言失败
    E010 未预期的运行时错误

版权与许可：
    MIT License (c) 2026 SkillForge Lab
    本脚本仅供学习参考，使用后果由使用者自行承担。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 版本与元数据
# ---------------------------------------------------------------------------
__version__ = "1.0.1"
SKILL_SLUG = "sqlw-mysql"
SKILL_NAME = "sqlw-mysql"
SKILL_DISPLAY_NAME = "MySQL 代码生成 查询包装 文本转换"
SKILL_DESCRIPTION = (
    "为 MySQL 数据库与查询生成包装代码或文本源，支持批量与自定义格式。"
)

# 支持的输出格式（目标语言 / 文本类型）
SUPPORTED_FORMATS = ("py", "java", "go", "js", "md", "json", "txt")

# 置信度等级
CONF_HIGH = "高"
CONF_MEDIUM = "中"
CONF_LOW = "低"


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class ParsedQuery:
    """单条 SQL 查询的结构化中间表示。"""
    raw_text: str
    query_type: str = "unknown"          # SELECT / INSERT / UPDATE / DELETE
    tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    where_conditions: List[str] = field(default_factory=list)
    join_conditions: List[str] = field(default_factory=list)
    placeholders: List[str] = field(default_factory=list)
    confidence: str = CONF_LOW

    def to_dict(self) -> Dict:
        """转为字典（用于 JSON 输出）。"""
        return asdict(self)


@dataclass
class GenerationResult:
    """一次格式生成的结果。"""
    format_name: str
    content: str
    query_count: int = 0
    confidence: str = CONF_LOW


# ---------------------------------------------------------------------------
# 核心解析器
# ---------------------------------------------------------------------------
class MySQLQueryParser:
    """
    MySQL 查询文本解析器。
    仅做词法与轻量语法分析，不连接数据库、不校验 SQL 语义。
    """

    # 常见 SQL 关键字（用于类型识别）
    TYPE_KEYWORDS = {
        "select": "SELECT",
        "insert": "INSERT",
        "update": "UPDATE",
        "delete": "DELETE",
    }

    # 占位符模式：? 或 :name 或 %s
    PLACEHOLDER_RE = re.compile(r"(\?|:[a-zA-Z_][a-zA-Z0-9_]*|%s)")

    # 表名提取（简单启发式：FROM/JOIN/INTO/UPDATE 后跟标识符）
    TABLE_RE = re.compile(
        r"\b(?:from|join|into|update)\s+([`\"\[]?[a-zA-Z_][a-zA-Z0-9_]*[`\"\]]?)",
        re.IGNORECASE,
    )

    # 列名提取（SELECT 后到 FROM 前的逗号分隔片段）
    COLUMN_RE = re.compile(
        r"select\s+(.+?)\s+from", re.IGNORECASE | re.DOTALL
    )

    # WHERE 条件提取
    WHERE_RE = re.compile(
        r"\bwhere\s+(.+?)(?:\b(group|order|limit)\b|$)",
        re.IGNORECASE | re.DOTALL,
    )

    # JOIN 条件提取
    JOIN_RE = re.compile(
        r"\b(?:left|right|inner|outer|cross)?\s*join\s+.+?\s+on\s+(.+?)"
        r"(?:\b(?:where|group|order|limit)\b|$)",
        re.IGNORECASE | re.DOTALL,
    )

    def parse(self, sql_text: str) -> ParsedQuery:
        """
        解析单条 SQL 文本，返回结构化表示。
        若输入为空或无法识别类型，抛出 ValueError（错误码 E002/E003）。
        """
        if not sql_text or not sql_text.strip():
            raise ValueError("E002: 输入 SQL 为空或非法")

        # 去除首尾空白与末尾分号
        cleaned = sql_text.strip().rstrip(";").strip()
        if not cleaned:
            raise ValueError("E002: 输入 SQL 为空或非法")

        # 识别查询类型
        first_word = cleaned.split(None, 1)[0].lower()
        qtype = self.TYPE_KEYWORDS.get(first_word)
        if qtype is None:
            raise ValueError(
                f"E003: 无法识别的 SQL 类型（非 SELECT/INSERT/UPDATE/DELETE）: {first_word}"
            )

        # 提取表名
        tables = self._extract_tables(cleaned)

        # 提取列名（仅 SELECT 有意义）
        columns = self._extract_columns(cleaned, qtype)

        # 提取 WHERE 条件
        where_conds = self._extract_where(cleaned)

        # 提取 JOIN 条件
        join_conds = self._extract_joins(cleaned)

        # 提取占位符
        placeholders = self._extract_placeholders(cleaned)

        # 置信度评估
        confidence = self._evaluate_confidence(
            qtype, tables, columns, where_conds, placeholders
        )

        return ParsedQuery(
            raw_text=sql_text.strip(),
            query_type=qtype,
            tables=tables,
            columns=columns,
            where_conditions=where_conds,
            join_conditions=join_conds,
            placeholders=placeholders,
            confidence=confidence,
        )

    # -- 内部辅助方法 ------------------------------------------------------
    def _extract_tables(self, sql: str) -> List[str]:
        """提取表名（去重、保留顺序）。"""
        tables = []
        for m in self.TABLE_RE.finditer(sql):
            name = m.group(1).strip("`\"[]")
            if name and name not in tables:
                tables.append(name)
        return tables

    def _extract_columns(self, sql: str, qtype: str) -> List[str]:
        """提取列名（仅 SELECT 提取，其余返回空列表）。"""
        if qtype != "SELECT":
            return []
        m = self.COLUMN_RE.search(sql)
        if not m:
            return []
        raw = m.group(1)
        # 按逗号切分，去除函数调用/表达式中的逗号干扰（简单处理）
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        cols = []
        for part in parts:
            # 取最后一个标识符作为列名（处理 t.name 或 COUNT(*) 等情况）
            tokens = re.findall(r"[`\"\[]?[a-zA-Z_][a-zA-Z0-9_]*[`\"\]]?", part)
            if tokens:
                # 跳过函数名（如 COUNT、SUM、MAX、MIN、AVG）
                if tokens[-1].lower() in (
                    "count",
                    "sum",
                    "max",
                    "min",
                    "avg",
                    "distinct",
                ):
                    continue
                col = tokens[-1].strip("`\"[]")
                if col and col not in cols:
                    cols.append(col)
        return cols

    def _extract_where(self, sql: str) -> List[str]:
        """提取 WHERE 子句条件（按 AND/OR 切分为列表）。"""
        m = self.WHERE_RE.search(sql)
        if not m:
            return []
        cond_text = m.group(1).strip()
        # 简单切分 AND/OR（不处理嵌套括号）
        parts = re.split(r"\b(?:and|or)\b", cond_text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def _extract_joins(self, sql: str) -> List[str]:
        """提取 JOIN ON 条件。"""
        conds = []
        for m in self.JOIN_RE.finditer(sql):
            cond = m.group(1).strip()
            if cond and cond not in conds:
                conds.append(cond)
        return conds

    def _extract_placeholders(self, sql: str) -> List[str]:
        """提取参数占位符。"""
        return list(dict.fromkeys(self.PLACEHOLDER_RE.findall(sql)))

    def _evaluate_confidence(
        self,
        qtype: str,
        tables: List[str],
        columns: List[str],
        where_conds: List[str],
        placeholders: List[str],
    ) -> str:
        """
        置信度评估规则：
            - 高：SELECT + 至少 1 表 + 至少 1 列
            - 中：SELECT + 表但无列，或非 SELECT + 表
            - 低：无表或无有效结构
        """
        if not tables:
            return CONF_LOW
        if qtype == "SELECT" and columns:
            return CONF_HIGH
        if qtype == "SELECT" and not columns:
            return CONF_MEDIUM
        # INSERT/UPDATE/DELETE
        if tables:
            return CONF_MEDIUM
        return CONF_LOW


# ---------------------------------------------------------------------------
# 代码 / 文本生成器
# ---------------------------------------------------------------------------
class CodeGenerator:
    """
    根据解析结果生成目标语言包装代码或文本。
    支持格式：py / java / go / js / md / json / txt
    """

    def __init__(self, parser: MySQLQueryParser):
        self.parser = parser

    def generate(
        self, parsed_list: List[ParsedQuery], fmt: str, template: Optional[str] = None
    ) -> GenerationResult:
        """
        生成指定格式的输出。
        template 为自定义模板（含 {content} 占位符），仅在 fmt='txt' 时使用。
        """
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"E004: 不支持的输出格式: {fmt}")

        if fmt == "py":
            content = self._gen_python(parsed_list)
        elif fmt == "java":
            content = self._gen_java(parsed_list)
        elif fmt == "go":
            content = self._gen_go(parsed_list)
        elif fmt == "js":
            content = self._gen_javascript(parsed_list)
        elif fmt == "md":
            content = self._gen_markdown(parsed_list)
        elif fmt == "json":
            content = self._gen_json(parsed_list)
        elif fmt == "txt":
            content = self._gen_text(parsed_list, template)
        else:
            raise ValueError(f"E004: 不支持的输出格式: {fmt}")

        # 整体置信度取所有查询的最低值
        overall_conf = (
            min((p.confidence for p in parsed_list), key=lambda c: c)
            if parsed_list
            else CONF_LOW
        )

        return GenerationResult(
            format_name=fmt,
            content=content,
            query_count=len(parsed_list),
            confidence=overall_conf,
        )

    # -- 各格式生成实现 ----------------------------------------------------
    def _gen_python(self, queries: List[ParsedQuery]) -> str:
        """生成 Python MySQL 包装代码（使用 mysql-connector-python 风格）。"""
        lines = [
            "# -*- coding: utf-8 -*-",
            "# 由 sqlw-mysql 自动生成（仅供学习参考）",
            "# pip install mysql-connector-python",
            "",
            "import mysql.connector",
            "",
            "",
            "def execute_query(cursor, sql, params=None):",
            "    \"\"\"执行查询并返回结果。\"\"\"",
            "    cursor.execute(sql, params or ())",
            "    return cursor.fetchall()",
            "",
            "",
            "# 预定义查询语句",
        ]
        for i, q in enumerate(queries, 1):
            lines.append(f"QUERY_{i} = {q.raw_text!r}")
            lines.append(f"QUERY_{i}_TYPE = {q.query_type!r}")
            lines.append(f"QUERY_{i}_TABLES = {q.tables!r}")
            if q.placeholders:
                lines.append(f"QUERY_{i}_PARAMS = {q.placeholders!r}")
            lines.append("")
        lines.append("")
        lines.append("def main():")
        lines.append("    # 示例连接（需根据实际环境修改）")
        lines.append("    conn = mysql.connector.connect(")
        lines.append("        host='localhost',")
        lines.append("        user='your_user',")
        lines.append("        password='your_password',")
        lines.append("        database='your_db'")
        lines.append("    )")
        lines.append("    cursor = conn.cursor()")
        lines.append("    try:")
        lines.append("        for name in dir():" )
        lines.append("            if name.startswith('QUERY_') and not name.endswith(('_TYPE', '_TABLES', '_PARAMS')):")
        lines.append("                sql = globals()[name]")
        lines.append("                print(f'执行 {name}: {sql}')")
        lines.append("    finally:")
        lines.append("        cursor.close()")
        lines.append("        conn.close()")
        lines.append("")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    main()")
        return "\n".join(lines)

    def _gen_java(self, queries: List[ParsedQuery]) -> str:
        """生成 Java JDBC 包装代码。"""
        lines = [
            "// 由 sqlw-mysql 自动生成（仅供学习参考）",
            "import java.sql.*;",
            "",
            "public class SqlwMysqlGenerated {",
            "",
            "    private static final String URL = \"jdbc:mysql://localhost:3306/your_db\";",
            "    private static final String USER = \"your_user\";",
            "    private static final String PASSWORD = \"your_password\";",
            "",
            "    public static void main(String[] args) {",
            "        try (Connection conn = DriverManager.getConnection(URL, USER, PASSWORD)) {",
        ]
        # 为每个查询生成一个方法
        for i, q in enumerate(queries, 1):
            method_name = f"query{i}"
            lines.append(f"            // 查询 {i}: {q.query_type} on {q.tables}")
            lines.append(f"            String sql{i} = \"{self._escape_java(q.raw_text)}\";")
            lines.append(f"            try (PreparedStatement ps = conn.prepareStatement(sql{i})) {{")
            lines.append(f"                // TODO: 设置参数")
            lines.append(f"                try (ResultSet rs = ps.executeQuery()) {{")
            lines.append(f"                    // TODO: 处理结果集")
            lines.append(f"                }}")
            lines.append(f"            }} catch (SQLException e) {{")
            lines.append(f"                e.printStackTrace();")
            lines.append(f"            }}")
            lines.append("")
        lines.append("        } catch (SQLException e) {")
        lines.append("            e.printStackTrace();")
        lines.append("        }")
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)

    def _gen_go(self, queries: List[ParsedQuery]) -> str:
        """生成 Go database/sql 包装代码。"""
        lines = [
            "// 由 sqlw-mysql 自动生成（仅供学习参考）",
            "package main",
            "",
            "import (",
            "    \"database/sql\"",
            "    \"fmt\"",
            "    _ \"github.com/go-sql-driver/mysql\"",
            ")",
            "",
            "func main() {",
            "    // 连接示例（需根据实际环境修改）",
            "    db, err := sql.Open(\"mysql\", \"user:password@tcp(localhost:3306)/dbname\")",
            "    if err != nil {",
            "        panic(err)",
            "    }",
            "    defer db.Close()",
            "",
        ]
        for i, q in enumerate(queries, 1):
            lines.append(f"    // 查询 {i}: {q.query_type} on {q.tables}")
            lines.append(f"    sql{i} := `{q.raw_text}`")
            lines.append(f"    rows{i}, err := db.Query(sql{i})")
            lines.append(f"    if err != nil {{")
            lines.append(f"        fmt.Println(\"查询 {i} 错误:\", err)")
            lines.append(f"        continue")
            lines.append(f"    }}")
            lines.append(f"    defer rows{i}.Close()")
            lines.append(f"    // TODO: 遍历 rows{i}")
            lines.append("")
        lines.append("}")
        return "\n".join(lines)

    def _gen_javascript(self, queries: List[ParsedQuery]) -> str:
        """生成 Node.js mysql2 包装代码。"""
        lines = [
            "// 由 sqlw-mysql 自动生成（仅供学习参考）",
            "// npm install mysql2",
            "const mysql = require('mysql2/promise');",
            "",
            "async function main() {",
            "  const conn = await mysql.createConnection({",
            "    host: 'localhost',",
            "    user: 'your_user',",
            "    password: 'your_password',",
            "    database: 'your_db'",
            "  });",
            "",
        ]
        for i, q in enumerate(queries, 1):
            lines.append(f"  // 查询 {i}: {q.query_type} on {q.tables}")
            lines.append(f"  const sql{i} = `{q.raw_text}`;")
            lines.append(f"  const [rows{i}] = await conn.execute(sql{i});")
            lines.append(f"  console.log(rows{i});")
            lines.append("")
        lines.append("  await conn.end();")
        lines.append("}")
        lines.append("")
        lines.append("main().catch(console.error);")
        return "\n".join(lines)

    def _gen_markdown(self, queries: List[ParsedQuery]) -> str:
        """生成 Markdown 格式的查询说明文档。"""
        lines = [
            "# SQL 查询说明文档",
            "",
            f"> 由 sqlw-mysql 自动生成，共 {len(queries)} 条查询。",
            "",
        ]
        for i, q in enumerate(queries, 1):
            lines.append(f"## 查询 {i}")
            lines.append("")
            lines.append("| 属性 | 值 |")
            lines.append("|------|-----|")
            lines.append(f"| 类型 | {q.query_type} |")
            lines.append(f"| 表 | {', '.join(q.tables) if q.tables else 'N/A'} |")
            lines.append(f"| 列 | {', '.join(q.columns) if q.columns else 'N/A'} |")
            lines.append(f"| 置信度 | {q.confidence} |")
            if q.where_conditions:
                lines.append(f"| WHERE | {'; '.join(q.where_conditions)} |")
            if q.join_conditions:
                lines.append(f"| JOIN | {'; '.join(q.join_conditions)} |")
            if q.placeholders:
                lines.append(f"| 占位符 | {', '.join(q.placeholders)} |")
            lines.append("")
            lines.append("
