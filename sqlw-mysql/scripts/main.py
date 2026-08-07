#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqlw-mysql: MySQL 代码生成 / 查询包装 / 文本转换
================================================
独立实现版本（clean-room），仅依据功能规格编写。
提供命令行接口与内置离线自检（--selftest）。

作者: DataForge Studio
版本: 1.0.1
许可证: MIT
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERR_OK = 0
ERR_INPUT = "E001"       # 输入为空或格式错误
ERR_PARSE = "E002"       # SQL 解析失败
ERR_FORMAT = "E003"      # 输出格式不支持
ERR_TEMPLATE = "E004"    # 自定义模板错误
ERR_BATCH = "E005"       # 批量处理失败
ERR_SELFTEST = "E006"    # 自检失败
ERR_INTERNAL = "E007"    # 内部错误
ERR_FILE = "E008"        # 文件操作失败
ERR_ARGS = "E009"        # 参数错误
ERR_UNKNOWN = "E010"     # 未知错误


# ============================================================
# 数据结构
# ============================================================

@dataclass
class SqlQuery:
    """解析后的 SQL 查询中间表示"""
    raw_text: str
    query_type: str = "unknown"          # SELECT / INSERT / UPDATE / DELETE
    tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    where_conditions: List[str] = field(default_factory=list)
    placeholders: List[str] = field(default_factory=list)
    confidence: str = "低"               # 高 / 中 / 低

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 输出）"""
        return {
            "raw_text": self.raw_text,
            "query_type": self.query_type,
            "tables": self.tables,
            "columns": self.columns,
            "where_conditions": self.where_conditions,
            "placeholders": self.placeholders,
            "confidence": self.confidence,
        }


@dataclass
class GenerationResult:
    """生成结果"""
    query: SqlQuery
    output_text: str
    format_name: str
    success: bool = True
    error_code: str = ERR_OK


# ============================================================
# 核心功能：解析
# ============================================================

def parse_sql(sql_text: str) -> SqlQuery:
    """
    解析 MySQL SQL 查询文本为结构化中间表示。
    仅做文本层面的解析，不连接数据库。
    """
    if not sql_text or not sql_text.strip():
        raise ValueError(ERR_INPUT)

    raw = sql_text.strip()
    # 去除末尾分号
    if raw.endswith(";"):
        raw = raw[:-1]

    # 识别查询类型
    upper = raw.upper()
    query_type = "unknown"
    for kw in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        if upper.startswith(kw):
            query_type = kw.lower()
            break

    # 提取表名（简单正则：FROM / INTO / UPDATE 后的标识符）
    tables = []
    table_patterns = [
        r"\bFROM\s+([a-zA-Z_][\w]*)",
        r"\bINTO\s+([a-zA-Z_][\w]*)",
        r"\bUPDATE\s+([a-zA-Z_][\w]*)",
        r"\bJOIN\s+([a-zA-Z_][\w]*)",
    ]
    for pat in table_patterns:
        for m in re.finditer(pat, upper):
            tbl = m.group(1).lower()
            if tbl not in tables:
                tables.append(tbl)

    # 提取字段（SELECT 之后、FROM 之前的逗号分隔列表）
    columns = []
    if query_type == "select":
        select_match = re.search(r"SELECT\s+(.+?)\s+FROM", upper, re.IGNORECASE | re.DOTALL)
        if select_match:
            col_part = select_match.group(1).strip()
            # 处理 SELECT * 的情况
            if col_part == "*":
                columns = ["*"]
            else:
                # 按逗号分割，取每个字段的最后一个标识符（去除表前缀和别名）
                for item in col_part.split(","):
                    item = item.strip()
                    if item:
                        # 去除 AS 别名
                        item = re.sub(r"\s+AS\s+\w+", "", item, flags=re.IGNORECASE)
                        # 取最后一部分作为字段名
                        parts = item.split(".")
                        columns.append(parts[-1].strip())

    # 提取 WHERE 条件
    where_conditions = []
    where_match = re.search(r"\bWHERE\s+(.+?)(?:\bORDER\s+BY\b|\bLIMIT\b|\bGROUP\s+BY\b|$)", upper, re.IGNORECASE | re.DOTALL)
    if where_match:
        cond_str = where_match.group(1).strip()
        # 按 AND/OR 简单分割
        for cond in re.split(r"\s+(?:AND|OR)\s+", cond_str, flags=re.IGNORECASE):
            cond = cond.strip()
            if cond:
                where_conditions.append(cond)

    # 提取占位符
    placeholders = re.findall(r"\?|%s|:(\w+)", raw)
    placeholders = list(dict.fromkeys(placeholders))  # 去重保持顺序

    # 计算置信度
    confidence = "高"
    if not tables or not columns:
        confidence = "中"
    if not raw or len(raw) < 10:
        confidence = "低"

    return SqlQuery(
        raw_text=raw,
        query_type=query_type,
        tables=tables,
        columns=columns,
        where_conditions=where_conditions,
        placeholders=placeholders,
        confidence=confidence,
    )


# ============================================================
# 核心功能：格式生成
# ============================================================

def generate_python_wrapper(query: SqlQuery) -> str:
    """生成 Python MySQL 连接包装代码"""
    lines = []
    lines.append("import mysql.connector  # pip install mysql-connector-python")
    lines.append("")
    lines.append("")
    lines.append("def execute_query(connection, params=None):")
    lines.append("    \"\"\"执行预定义的 SQL 查询\"\"\"")
    lines.append("    cursor = connection.cursor()")
    lines.append("    try:")
    lines.append(f"        sql = {query.raw_text!r}")
    lines.append("        if params:")
    lines.append("            cursor.execute(sql, params)")
    lines.append("        else:")
    lines.append("            cursor.execute(sql)")
    lines.append("        if sql.strip().upper().startswith('SELECT'):")
    lines.append("            result = cursor.fetchall()")
    lines.append("        else:")
    lines.append("            connection.commit()")
    lines.append("            result = cursor.rowcount")
    lines.append("        return result")
    lines.append("    finally:")
    lines.append("        cursor.close()")
    lines.append("")
    lines.append("")
    lines.append("# 使用示例：")
    lines.append("# conn = mysql.connector.connect(host='localhost', user='root', password='***', database='test')")
    lines.append("# result = execute_query(conn, {'id': 1})")
    return "\n".join(lines)


def generate_markdown_doc(query: SqlQuery) -> str:
    """生成 Markdown 格式查询说明文档"""
    lines = []
    lines.append("# SQL 查询说明")
    lines.append("")
    lines.append(f"**查询类型**: `{query.query_type.upper()}`")
    lines.append(f"**置信度**: {query.confidence}")
    lines.append("")
    lines.append("## 涉及表")
    lines.append("")
    if query.tables:
        for t in query.tables:
            lines.append(f"- `{t}`")
    else:
        lines.append("- （未识别）")
    lines.append("")
    lines.append("## 查询字段")
    lines.append("")
    if query.columns:
        for c in query.columns:
            lines.append(f"- `{c}`")
    else:
        lines.append("- （未识别）")
    lines.append("")
    if query.where_conditions:
        lines.append("## 筛选条件")
        lines.append("")
        for w in query.where_conditions:
            lines.append(f"- `{w}`")
        lines.append("")
    if query.placeholders:
        lines.append("## 参数占位符")
        lines.append("")
        for p in query.placeholders:
            lines.append(f"- `{p}`")
        lines.append("")
    lines.append("## 原始 SQL")
    lines.append("")
    lines.append(f"
