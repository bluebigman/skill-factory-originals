#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mdproof — Markdown 转 PDF 转换器（clean-room 独立实现）

功能：
- 将 Markdown 文本转换为排版规范的 PDF 文件
- 支持批量处理多个本地文件
- 内置格式校验（未闭合代码块、非法表格分隔符、URL 格式异常）
- 支持 --selftest 离线自检核心逻辑

错误码说明：
E001: 输入参数无效或缺失
E002: 文件读取失败
E003: 文件写入失败
E004: Markdown 解析失败
E005: PDF 生成失败
E006: URL 格式异常
E007: 代码块未闭合
E008: 表格分隔符非法
E009: 文件大小超限
E010: 内部未知错误
"""

import argparse
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码
ERR_INVALID_ARGS = "E001"
ERR_FILE_READ = "E002"
ERR_FILE_WRITE = "E003"
ERR_MD_PARSE = "E004"
ERR_PDF_GEN = "E005"
ERR_URL_FORMAT = "E006"
ERR_CODE_BLOCK = "E007"
ERR_TABLE_SEP = "E008"
ERR_SIZE_LIMIT = "E009"
ERR_UNKNOWN = "E010"

# 输入限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_BATCH_COUNT = 100

# 页面尺寸（点，1 英寸 = 72 点）
PAGE_SIZES = {
    "A4": (595.28, 841.89),
    "LETTER": (612.00, 792.00),
}

# 页边距（点）
MARGINS = {
    "窄": 36.0,    # 0.5 英寸
    "常规": 72.0,  # 1 英寸
    "宽": 108.0,   # 1.5 英寸
}

# 字体大小（点）
FONT_SIZES = {
    "h1": 24,
    "h2": 20,
    "h3": 16,
    "h4": 14,
    "h5": 12,
    "h6": 11,
    "body": 10,
    "code": 9,
    "small": 8,
}


# ============================================================
# 自定义异常
# ============================================================

class MdProofError(Exception):
    """mdproof 自定义异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 数据结构
# ============================================================

@dataclass
class Block:
    """Markdown 解析后的块元素"""
    type: str  # heading, paragraph, list, table, code, quote, hr, image
    content: str = ""
    level: int = 0
    items: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    header: List[str] = field(default_factory=list)
    language: str = ""
    url: str = ""
    alt: str = ""


@dataclass
class Document:
    """解析后的文档对象"""
    title: str = ""
    blocks: List[Block] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConversionOptions:
    """转换选项"""
    page_size: str = "A4"
    margin: str = "常规"
    font_name: str = "Helvetica"
    cover_page: bool = False
    header_text: str = ""
    footer_text: str = ""


# ============================================================
# Markdown 解析器（轻量级）
# ============================================================

class MarkdownParser:
    """
    轻量级 Markdown 解析器
    支持：标题、段落、列表（有序/无序/任务）、表格、代码块、引用块、粗斜体、行内代码、链接、图片
    """

    # URL 正则（宽松匹配）
    URL_PATTERN = re.compile(
        r'^(?:https?://|ftp://|file://|www\.)[^\s<>"\'()]+$',
        re.IGNORECASE
    )

    # 表格分隔行正则：| --- | :---: | ---: |
    TABLE_SEP_PATTERN = re.compile(
        r'^\s*\|?[\s:|-]+\|[\s:|-]*\|?\s*$'
    )

    def __init__(self, max_size: int = MAX_FILE_SIZE):
        self.max_size = max_size
        self.warnings: List[str] = []

    def parse(self, text: str) -> Document:
        """解析 Markdown 文本为文档对象"""
        doc = Document()
        lines = text.split('\n')

        # 检查文件大小（按字符数估算）
        if len(text.encode('utf-8')) > self.max_size:
            raise MdProofError(ERR_SIZE_LIMIT, f"输入内容超过 {self.max_size // (1024*1024)}MB 限制")

        # 去除 YAML frontmatter
        if lines and lines[0].strip() == '---':
            try:
                end_idx = lines.index('---', 1)
                # 尝试提取标题
                for line in lines[1:end_idx]:
                    if line.lower().startswith('title:'):
                        doc.title = line.split(':', 1)[1].strip().strip('"\'')
                        break
                lines = lines[end_idx + 1:]
            except ValueError:
                raise MdProofError(ERR_MD_PARSE, "YAML frontmatter 未正确闭合")

        # 逐行解析
        i = 0
        in_code_block = False
        code_lang = ""
        code_lines: List[str] = []
        in_quote_block = False
        quote_lines: List[str] = []
        list_items: List[str] = []
        list_type = ""
        table_rows: List[List[str]] = []
        table_header: List[str] = []
        in_table = False
        paragraph_lines: List[str] = []

        def flush_paragraph():
            """刷新当前段落"""
            nonlocal paragraph_lines
            if paragraph_lines:
                content = ' '.join(line.strip() for line in paragraph_lines if line.strip())
                if content:
                    doc.blocks.append(Block(type="paragraph", content=content))
                paragraph_lines = []

        def flush_list():
            """刷新当前列表"""
            nonlocal list_items, list_type
            if list_items:
                doc.blocks.append(Block(type="list", items=list_items, content=list_type))
                list_items = []
                list_type = ""

        def flush_table():
            """刷新当前表格"""
            nonlocal table_rows, table_header, in_table
            if in_table and table_rows:
                doc.blocks.append(Block(
                    type="table",
                    header=table_header,
                    rows=table_rows
                ))
            table_rows = []
            table_header = []
            in_table = False

        def flush_quote():
            """刷新当前引用块"""
            nonlocal quote_lines, in_quote_block
            if quote_lines:
                content = '\n'.join(quote_lines)
                doc.blocks.append(Block(type="quote", content=content))
                quote_lines = []
                in_quote_block = False

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # === 代码块处理 ===
            if in_code_block:
                if stripped.startswith('
