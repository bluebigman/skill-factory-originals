#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sql-code-generator 独立实现脚本
功能：将自然语言需求转化为规范SQL语句（仅生成，不执行）
"""

import re
import sys
import argparse
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空或仅包含空白字符",
    "E002": "未识别的SQL操作类型（仅支持 SELECT/INSERT/UPDATE/DELETE）",
    "E003": "缺少表名",
    "E004": "SELECT 语句缺少查询字段",
    "E005": "INSERT 语句缺少字段或值",
    "E006": "UPDATE 语句缺少 SET 子句",
    "E007": "DELETE 语句缺少 WHERE 条件",
    "E008": "JOIN 语句缺少关联条件",
    "E009": "子查询格式错误",
    "E010": "内部处理异常",
}


# ---------------------------------------------------------------------------
# 核心数据结构：关键词映射表
# ---------------------------------------------------------------------------
# 操作类型识别关键词
OPERATION_KEYWORDS = {
    "select": "SELECT",
    "查询": "SELECT",
    "查": "SELECT",
    "insert": "INSERT",
    "插入": "INSERT",
    "新增": "INSERT",
    "update": "UPDATE",
    "更新": "UPDATE",
    "修改": "UPDATE",
    "delete": "DELETE",
    "删除": "DELETE",
    "移除": "DELETE",
}

# 常见 SQL 关键词（用于清洗和识别）
SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES",
    "UPDATE", "SET", "DELETE", "JOIN", "ON", "GROUP BY",
    "ORDER BY", "HAVING", "LIMIT", "AND", "OR", "NOT", "NULL",
    "AS", "DISTINCT", "COUNT", "SUM", "AVG", "MAX", "MIN",
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _clean_input(text: str) -> str:
    """清洗输入文本：去除多余空白和特殊符号"""
    if not text or not text.strip():
        return ""
    # 统一空格、去除首尾空白
    cleaned = re.sub(r"\s+", " ", text.strip())
    # 移除可能的 Markdown 代码块标记
    cleaned = cleaned.replace("
