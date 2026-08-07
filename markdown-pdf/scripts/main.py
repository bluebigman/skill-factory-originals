#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-pdf: Markdown 转 PDF 转换器（独立实现）
版本: 1.0.1
许可: MIT

本脚本根据功能规格独立实现，仅使用 Python 标准库。
核心功能：
  1. 将 Markdown 文本、本地文件或远程 URL 转换为 PDF 文档。
  2. 支持批量输入、自定义输出命名、合并输出。
  3. 内置 --selftest 离线自检，不依赖外部文件或网络。
"""

import argparse
import html
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    0: "成功",
    "E001": "输入参数无效或缺失",
    "E002": "文件读取失败（不存在或无法访问）",
    "E003": "URL 访问失败或内容获取失败",
    "E004": "Markdown 解析失败（语法不支持或内容损坏）",
    "E005": "PDF 生成失败（渲染错误）",
    "E006": "输出路径无效或无法写入",
    "E007": "批量处理时部分输入失败",
    "E008": "加密或二进制文件不支持",
    "E009": "字体或资源加载失败",
    "E010": "未知内部错误",
}


class MarkdownPDFError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ConversionResult:
    """单次转换结果。"""

    source: str          # 输入来源描述
    output_path: str     # 输出文件路径
    success: bool        # 是否成功
    pages: int = 0       # 生成页数（估算）
    warnings: List[str] = field(default_factory=list)  # 置信度提示


@dataclass
class PDFConfig:
    """PDF 生成配置参数。"""

    page_width: float = 595.0      # A4 宽度（点）
    page_height: float = 842.0     # A4 高度（点）
    margin_top: float = 72.0       # 上边距（点）
    margin_bottom: float = 72.0    # 下边距（点）
    margin_left: float = 72.0      # 左边距（点）
    margin_right: float = 72.0     # 右边距（点）
    font_size: float = 12.0        # 正文字号（点）
    heading_font_size: float = 16.0  # 标题字号（点）
    line_height: float = 1.5       # 行高倍数
    output_dir: str = "output"     # 输出目录


# ---------------------------------------------------------------------------
# Markdown 解析器（轻量级，支持常见语法）
# ---------------------------------------------------------------------------
class MarkdownParser:
    """
    将 Markdown 文本解析为中间表示（块列表）。
    支持：标题、段落、代码块、表格、列表、引用、链接、图片、粗体、斜体、行内代码。
    不支持的语法会记录警告并尽力保留原文。
    """

    # 块级正则
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
    _CODE_BLOCK_RE = re.compile(r'^
