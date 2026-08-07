#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2pdfgo — Markdown 转 PDF 转换器

技能功能规格实现脚本：
- 支持 Markdown 文本、文件路径或 URL 输入
- 支持默认/紧凑/正式三种样式模板
- 支持自定义页边距、正文字号
- 支持批量模式
- 提供 --selftest 离线自检

仅使用标准库实现，核心转换逻辑不依赖第三方库。
实际 PDF 渲染需要 reportlab，已通过可选导入处理。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入参数无效或缺失",
    "E002": "输入文件不存在或无法读取",
    "E003": "输入 URL 无法访问或下载失败",
    "E004": "输出目录不存在或无法写入",
    "E005": "Markdown 解析失败",
    "E006": "PDF 渲染失败",
    "E007": "批量模式输入配置错误",
    "E008": "样式模板不存在",
    "E009": "参数类型或取值范围错误",
    "E010": "内部逻辑错误（未知异常）",
}


class Md2PdfError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ConversionOptions:
    """转换参数配置"""

    input_source: str
    output_path: str = "output.pdf"
    style: str = "default"
    margin: float = 20.0
    fontsize: int = 11
    batch: bool = False


@dataclass
class MarkdownBlock:
    """Markdown 解析后的块结构"""

    block_type: str  # heading, paragraph, code, list, quote, table
    level: int = 0  # 标题级别
    content: str = ""
    items: List[str] = field(default_factory=list)  # 列表项
    rows: List[List[str]] = field(default_factory=list)  # 表格行
    language: str = ""  # 代码块语言


# ---------------------------------------------------------------------------
# Markdown 解析器
# ---------------------------------------------------------------------------
class MarkdownParser:
    """简单的 Markdown 解析器，提取块级结构"""

    # 行内格式正则（粗体、斜体、行内代码）
    INLINE_PATTERNS = [
        (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
        (re.compile(r"\*(.+?)\*"), r"<i>\1</i>"),
        (re.compile(r"`(.+?)`"), r"<code>\1</code>"),
        (re.compile(r"\[(.+?)\]\((.+?)\)"), r'<a href="\2">\1</a>'),
    ]

    @classmethod
    def parse(cls, markdown_text: str) -> List[MarkdownBlock]:
        """解析 Markdown 文本为块结构列表"""
        if not markdown_text or not markdown_text.strip():
            raise Md2PdfError("E005", "Markdown 内容为空")

        lines = markdown_text.splitlines()
        blocks: List[MarkdownBlock] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i].rstrip()

            # 空行跳过
            if not line.strip():
                i += 1
                continue

            # 代码块（
