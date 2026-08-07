#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-exporter 技能实现脚本

本脚本根据功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供 Markdown 内容的结构化解析、转换与导出能力，并内置离线自检。
"""

import argparse
import csv
import html
import io
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件写入失败",
    "E007": "不支持的输出格式",
    "E008": "URL 访问被拒绝（离线模式）",
    "E009": "内部处理异常",
    "E010": "参数校验失败",
}


class SkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class MarkdownDocument:
    """解析后的 Markdown 文档结构"""
    raw_text: str
    title: str = ""
    headings: List[Dict[str, Any]] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    lists: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    blockquotes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化"""
        return {
            "title": self.title,
            "headings": self.headings,
            "paragraphs": self.paragraphs,
            "code_blocks": self.code_blocks,
            "lists": self.lists,
            "tables": self.tables,
            "links": self.links,
            "images": self.images,
            "blockquotes": self.blockquotes,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "char_count": len(self.raw_text),
        }


# ============================================================
# Markdown 解析器（核心逻辑）
# ============================================================
class MarkdownParser:
    """将 Markdown 文本解析为结构化文档"""

    # 常用正则表达式
    _HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
    _CODE_FENCE_RE = re.compile(r"^
