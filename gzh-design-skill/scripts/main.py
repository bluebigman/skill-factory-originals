#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gzh-design-skill 主题生成器（clean-room 独立实现）

依据功能规格独立编写，将 Markdown 文本转换为适合公众号编辑器的 HTML。
包含 6 套内置主题 + 简单主题生成器 + 双关卡校验。
仅使用标准库，支持 --selftest 离线自检。

用法:
    python main.py --selftest
    python main.py --input sample.md --theme default --output result.html
"""

import argparse
import html
import re
import sys
import tempfile
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查 Markdown 语法。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "主题名称无效，请使用内置主题或生成器。",
    "E007": "输出文件写入失败，请检查权限或路径。",
    "E008": "命令行参数冲突或缺失。",
    "E009": "自检失败，核心逻辑异常。",
    "E010": "未知错误，请查看日志。",
}


def fail(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg} {message}"
    print(f"[{code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Theme:
    """主题定义。"""
    name: str
    display_name: str
    background: str          # 背景色
    text_color: str          # 正文颜色
    heading_color: str       # 标题颜色
    accent_color: str        # 强调色
    font_family: str         # 字体族
    border_style: str        # 边框风格
    border_radius: int       # 圆角像素


@dataclass
class MarkdownBlock:
    """Markdown 块级元素。"""
    type: str                # heading / paragraph / list / quote / code / hr
    level: int = 0           # 标题级别
    content: str = ""        # 文本内容
    items: List[str] = field(default_factory=list)  # 列表项


@dataclass
class ConversionResult:
    """转换结果。"""
    html: str
    confidence: float        # 置信度 0~1
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 内置主题库（6 套）
# ---------------------------------------------------------------------------
BUILTIN_THEMES: Dict[str, Theme] = {
    "default": Theme(
        name="default",
        display_name="默认简洁",
        background="#ffffff",
        text_color="#333333",
        heading_color="#1a1a1a",
        accent_color="#2d8cf0",
        font_family="'Helvetica Neue', Arial, sans-serif",
        border_style="1px solid #e8e8e8",
        border_radius=8,
    ),
    "warm": Theme(
        name="warm",
        display_name="暖阳橙",
        background="#fffaf0",
        text_color="#5c4a3a",
        heading_color="#c2571b",
        accent_color="#e67e22",
        font_family="'Georgia', 'Times New Roman', serif",
        border_style="1px solid #f0dcc8",
        border_radius=12,
    ),
    "cool": Theme(
        name="cool",
        display_name="清凉蓝",
        background="#f0f7ff",
        text_color="#2c3e50",
        heading_color="#1a5276",
        accent_color="#2980b9",
        font_family="'Segoe UI', 'PingFang SC', sans-serif",
        border_style="1px solid #c5d9e8",
        border_radius=6,
    ),
    "forest": Theme(
        name="forest",
        display_name="森林绿",
        background="#f5faf5",
        text_color="#2d3e2d",
        heading_color="#1e6b3a",
        accent_color="#27ae60",
        font_family="'Trebuchet MS', sans-serif",
        border_style="1px solid #c8e0c8",
        border_radius=10,
    ),
    "night": Theme(
        name="night",
        display_name="暗夜紫",
        background="#2d2d3d",
        text_color="#e0e0e8",
        heading_color="#b39ddb",
        accent_color="#7e57c2",
        font_family="'Consolas', 'Courier New', monospace",
        border_style="1px solid #4a4a5a",
        border_radius=4,
    ),
    "paper": Theme(
        name="paper",
        display_name="复古纸",
        background="#fdf6e3",
        text_color="#4a3f2f",
        heading_color="#8b5e3c",
        accent_color="#b58900",
        font_family="'KaiTi', 'STKaiti', serif",
        border_style="1px solid #d8c8a8",
        border_radius=2,
    ),
}


# ---------------------------------------------------------------------------
# Markdown 解析器（轻量实现）
# ---------------------------------------------------------------------------
class MarkdownParser:
    """极简 Markdown 解析器，支持标题/段落/列表/引用/代码/分隔线。"""

    def __init__(self, text: str):
        self.text = text
        self.lines = text.split("\n")

    def parse(self) -> List[MarkdownBlock]:
        """解析文本为块级元素列表。"""
        blocks: List[MarkdownBlock] = []
        i = 0
        while i < len(self.lines):
            line = self.lines[i].rstrip()

            # 跳过空行
            if not line.strip():
                i += 1
                continue

            # 标题
            if re.match(r"^#{1,6}\s+", line):
                match = re.match(r"^(#{1,6})\s+(.*)", line)
                level = len(match.group(1))
                content = match.group(2).strip()
                blocks.append(MarkdownBlock(type="heading", level=level, content=content))
                i += 1
                continue

            # 分隔线
            if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip()):
                blocks.append(MarkdownBlock(type="hr"))
                i += 1
                continue

            # 引用
            if line.lstrip().startswith(">"):
                quote_lines = []
                while i < len(self.lines) and self.lines[i].lstrip().startswith(">"):
                    quote_lines.append(self.lines[i].lstrip()[1:].strip())
                    i += 1
                blocks.append(MarkdownBlock(type="quote", content=" ".join(quote_lines)))
                continue

            # 代码块
            if line.strip().startswith("
