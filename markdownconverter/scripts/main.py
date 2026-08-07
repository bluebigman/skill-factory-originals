#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Markdown 格式转换工具（独立实现）

功能：
    1. 将 Markdown 文本/文件转换为 HTML
    2. 支持批量处理（通过 glob 匹配）
    3. 支持自定义 CSS 样式
    4. 保留目录结构输出
    5. 提供命令行接口与自检模式

设计原则：
    - 仅使用 Python 标准库
    - 不依赖任何第三方库
    - 核心逻辑（markdown → HTML）完全独立实现
    - 错误处理使用统一错误码 E001-E010
"""

import argparse
import glob
import html
import os
import re
import sys
from pathlib import Path

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文件不存在",
    "E002": "输出目录无法创建",
    "E003": "输入文件读取失败",
    "E004": "输出文件写入失败",
    "E005": "不支持的输出格式（仅支持 html）",
    "E006": "批量模式未匹配到任何文件",
    "E007": "无效的正则表达式",
    "E008": "无效的 CSS 样式",
    "E009": "输入输出路径相同",
    "E010": "未知错误",
}


class MarkdownConverterError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# Markdown 解析器（核心逻辑）
# ============================================================
class MarkdownParser:
    """
    Markdown → HTML 转换器

    支持语法：
        - 标题（# ~ ######）
        - 粗体、斜体、行内代码
        - 链接、图片
        - 无序列表、有序列表
        - 引用块
        - 代码块（围栏式）
        - 水平线
        - 段落
    """

    # 行内格式编译好的正则
    _INLINE_PATTERNS = [
        # 粗体 **text** 或 __text__
        (re.compile(r"\*\*(.+?)\*\*|__(.+?)__"), lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>"),
        # 斜体 *text* 或 _text_
        (re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)|(?<!_)_([^_]+?)_(?!_)"), lambda m: f"<em>{m.group(1) or m.group(2)}</em>"),
        # 行内代码 `code`
        (re.compile(r"`([^`]+)`"), lambda m: f"<code>{html.escape(m.group(1))}</code>"),
        # 图片 ![alt](url)
        (re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)"), lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}">'),
        # 链接 [text](url)
        (re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"), lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>'),
    ]

    def __init__(self):
        """初始化解析器"""
        self._block_patterns = [
            # 围栏代码块
            (re.compile(r"^
