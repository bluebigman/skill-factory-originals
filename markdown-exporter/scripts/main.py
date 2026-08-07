#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

markdown-exporter 技能的核心实现脚本（clean-room 独立实现）。

本脚本根据功能规格实现一个 Markdown 转换/导出工具的核心逻辑，
支持将 Markdown 文本转换为多种目标格式的"结构化中间表示"，
并提供命令行入口与离线自检（--selftest）功能。

设计原则：
- 仅使用 Python 标准库。
- 所有核心逻辑均为独立实现，不依赖任何第三方库。
- 通过错误码（E001-E010）进行标准化错误处理。
- 提供 --selftest 参数，使用内置样例数据进行离线自检。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES: Dict[str, str] = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "不支持的输出格式",
    "E008": "命令行参数错误",
    "E009": "自检失败",
    "E010": "未知错误",
}


class MarkdownExporterError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, error_code: str, message: Optional[str] = None):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------
class DocumentBlock:
    """表示 Markdown 文档中的一个块级元素。"""

    def __init__(self, block_type: str, content: str, level: int = 0, meta: Optional[Dict[str, Any]] = None):
        self.block_type = block_type  # 如 heading, paragraph, list_item, code, table, quote
        self.content = content
        self.level = level  # 用于标题级别、列表嵌套层级
        self.meta = meta or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化。"""
        return {
            "type": self.block_type,
            "content": self.content,
            "level": self.level,
            "meta": self.meta,
        }


class ParsedDocument:
    """解析后的文档结构。"""

    def __init__(self, title: str = "", blocks: Optional[List[DocumentBlock]] = None):
        self.title = title
        self.blocks = blocks or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "title": self.title,
            "blocks": [b.to_dict() for b in self.blocks],
            "block_count": len(self.blocks),
        }


# ---------------------------------------------------------------------------
# Markdown 解析器（核心逻辑之一）
# ---------------------------------------------------------------------------
class MarkdownParser:
    """
    将 Markdown 文本解析为 ParsedDocument。

    支持的元素：标题、段落、列表（有序/无序）、代码块、引用、表格、分隔线。
    解析规则为简化实现，不追求完整 Markdown 规范，但覆盖常见用法。
    """

    # 行级正则表达式
    _HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
    _CODE_FENCE_RE = re.compile(r"^
