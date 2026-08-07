#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-pdf 技能独立实现脚本

基于功能规格独立编写（clean-room），不复制任何既有代码。
提供 Markdown 转 PDF 的核心能力：文件转换、URL 转换、批量处理、样式控制、目录生成。

仅依赖标准库，selftest 使用内置硬编码样例离线自检。
"""

import argparse
import hashlib
import html
import os
import re
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# E001: 参数错误
# E002: 文件不存在
# E003: 文件读取失败
# E004: 文件写入失败
# E005: URL 访问失败
# E006: Markdown 解析失败
# E007: PDF 生成失败
# E008: 批量处理部分失败
# E009: 目录生成失败
# E010: 未知错误
# ============================================================


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ConversionOptions:
    """转换选项配置"""
    page_size: str = "A4"           # 页面大小
    font_size: int = 12             # 字体大小（pt）
    margin_top: int = 25            # 上边距（mm）
    margin_bottom: int = 25         # 下边距（mm）
    margin_left: int = 25           # 左边距（mm）
    margin_right: int = 25          # 右边距（mm）
    header_text: str = ""           # 页眉文本
    footer_text: str = ""           # 页脚文本
    generate_toc: bool = True       # 是否生成目录
    font_family: str = "sans-serif" # 字体族


@dataclass
class ConversionResult:
    """转换结果"""
    source: str                     # 源（文件路径或 URL）
    output_path: str                # 输出 PDF 路径
    success: bool                   # 是否成功
    error_code: Optional[str] = None  # 错误码
    error_message: Optional[str] = None  # 错误信息
    page_count: int = 0             # 页数
    toc_entries: List[Tuple[int, str, int]] = field(default_factory=list)  # 目录条目 (级别, 标题, 页码)


# ============================================================
# Markdown 解析器（极简实现，仅支持规格所需核心语法）
# ============================================================
class MarkdownParser:
    """极简 Markdown 解析器：支持标题、段落、列表、代码块、表格、引用、粗体斜体等"""

    # 块级元素正则
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
    _CODE_FENCE_RE = re.compile(r'^
