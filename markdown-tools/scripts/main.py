#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-tools 独立实现脚本
============================
依据功能规格 clean-room 重写，仅使用 Python 标准库。

功能概览：
    1. 从纯文本/HTML/CSV 等来源提取 Markdown 结构化元素（标题、列表、代码块、表格、链接）。
    2. 将提取结果渲染为多种风格的 Markdown 输出（GitHub 风格、学术风格、简洁风格）。
    3. 对解析不确定的内容输出置信度等级。
    4. 支持批量处理多个文本片段。
    5. 提供 --selftest 离线自检，使用内置硬编码样例，不访问外部资源。

错误码定义：
    E001 - 输入参数缺失或类型错误
    E002 - 输入内容为空
    E003 - 不支持的输入来源类型
    E004 - 模板风格不支持
    E005 - 批量处理输入格式错误
    E006 - 内部解析逻辑异常
    E007 - 输出渲染异常
    E008 - 自检数据损坏（内部错误）
    E009 - 文件操作失败（保留，当前未使用）
    E010 - 未知异常

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input "## 标题" --style github
"""

import argparse
import csv
import html
import io
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class MarkdownElement:
    """Markdown 结构化元素的统一表示。"""
    kind: str                 # 元素类型: heading / list / code / table / link / paragraph
    content: str = ""         # 主要内容（文本）
    level: int = 0            # 标题层级（heading 使用）
    items: List[str] = field(default_factory=list)   # 列表项（list 使用）
    code_lines: List[str] = field(default_factory=list)  # 代码行（code 使用）
    rows: List[List[str]] = field(default_factory=list)  # 表格行（table 使用）
    url: str = ""             # 链接地址（link 使用）
    confidence: float = 1.0   # 置信度 0.0 ~ 1.0


@dataclass
class ParseResult:
    """解析结果，包含元素列表和整体置信度。"""
    elements: List[MarkdownElement] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class RenderOptions:
    """渲染选项。"""
    style: str = "github"     # github / academic / plain
    include_confidence: bool = False


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------

class MarkdownParser:
    """
    将原始文本解析为 MarkdownElement 列表。
    不执行代码、不解密、不做语义判断，仅做格式识别。
    """

    # 识别行首标题的正则
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')

    # 识别无序列表项
    _ULIST_RE = re.compile(r'^[\s]*[-*+]\s+(.+)$')

    # 识别有序列表项
    _OLIST_RE = re.compile(r'^[\s]*\d+[.)]\s+(.+)$')

    # 识别代码块起始（
