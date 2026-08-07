#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2pdf-mermaid 技能实现脚本（clean-room 重写版）

本脚本根据功能规格独立实现，仅依赖 Python 标准库。
支持将 Markdown 文本转换为结构化数据（含 Mermaid 图表识别），
并提供 --selftest 离线自检功能。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# 错误码定义（E001-E010）
# =============================================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果不确定",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "文件操作失败",
    "E009": "数据解析失败",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# =============================================================================
# 数据模型
# =============================================================================
@dataclass
class ParseResult:
    """解析结果"""
    title: str = ""
    sections: List[Dict[str, Any]] = field(default_factory=list)
    mermaid_blocks: List[str] = field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class SkillOutput:
    """技能输出"""
    success: bool = False
    result: Optional[Dict[str, Any]] = None
    error_code: str = ""
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# 核心处理逻辑
# =============================================================================
class MarkdownParser:
    """
    Markdown 解析器：解析文本结构，识别标题、段落、列表、代码块等。
    不依赖第三方库，使用正则表达式进行基础解析。
    """

    # 标题正则：支持 1-6 级标题
    HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
    # 代码块起始（注意：这里使用三引号字符串来包含反引号）
    CODE_FENCE_RE = re.compile(r"^
