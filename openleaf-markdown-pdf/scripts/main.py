#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openleaf-markdown-pdf — 分页文档 PDF 转换排版工具
=================================================
将 Markdown 文本转换为分页 PDF 文档，支持目录生成、分页控制、样式定制。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
错误码说明:
    E001: 参数解析失败
    E002: 输入文件不存在或不可读
    E003: 输出目录创建失败
    E004: Markdown 解析失败
    E005: PDF 生成失败
    E006: 样式配置无效
    E007: 批量处理失败
    E008: 目录生成失败
    E009: 分页符处理失败
    E010: 自检失败
"""

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class StyleConfig:
    """样式配置"""
    font_size: int = 12
    font_name: str = "Helvetica"
    page_margin: int = 40  # 点（pt）
    header_text: str = ""
    footer_text: str = ""
    show_page_number: bool = True
    line_spacing: float = 1.5


@dataclass
class MarkdownBlock:
    """Markdown 块"""
    type: str  # heading1, heading2, heading3, paragraph, list_item, code, pagebreak, hr
    content: str = ""
    level: int = 0
    indent: int = 0


@dataclass
class ParsedDocument:
    """解析后的文档"""
    title: str = ""
    blocks: List[MarkdownBlock] = field(default_factory=list)
    headings: List[Tuple[int, str, int]] = field(default_factory=list)  # (level, text, block_index)


# ============================================================
# Markdown 解析器（纯标准库实现）
# ============================================================

class MarkdownParser:
    """Markdown 解析器"""
    
    # 分页符模式
    PAGE_BREAK_PATTERNS = [
        r"^\s*\\newpage\s*$",      # \newpage
        r"^\s*---\s*$",            # ---（单独一行）
        r'^\s*<div\s+class="page-break"\s*/?>\s*$',  # HTML 分页
    ]
    
    def parse(self, text: str) -> ParsedDocument:
        """解析 Markdown 文本"""
        doc = ParsedDocument()
        lines = text.split("\n")
        block_index = 0
        in_code_block = False
        code_buffer = []
        
        for line in lines:
            stripped = line.strip()
            
            # 代码块处理
            if stripped.startswith('
