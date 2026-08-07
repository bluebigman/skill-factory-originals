#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

面向微信公众号的 Markdown 排版与编辑工具（独立实现）。

本脚本仅依据功能规格文档进行 clean-room 重写，不包含任何既有代码。
支持多套主题、手机预览、一键复制正文到公众号后台。
提供 --selftest 参数进行离线自检（内置硬编码样例数据）。
"""

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议...",
    "E006": "内部错误：主题不存在",
    "E007": "内部错误：模板渲染失败",
    "E008": "内部错误：参数校验失败",
    "E009": "内部错误：数据解析失败",
    "E010": "内部错误：未知异常",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Article:
    """文章数据模型。"""

    title: str = ""
    author: str = ""
    content: str = ""  # 原始 Markdown 内容
    cover_image: str = ""  # 封面图 URL（可选）
    digest: str = ""  # 摘要（可选）
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormatResult:
    """格式化结果。"""

    html_content: str = ""  # 渲染后的 HTML
    plain_text: str = ""  # 纯文本版本
    word_count: int = 0
    theme_name: str = ""
    confidence: float = 1.0  # 置信度 0~1
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 主题定义（内置多套主题）
# ---------------------------------------------------------------------------
@dataclass
class Theme:
    """主题样式定义。"""

    name: str
    display_name: str
    css: str  # 注入到 HTML 的 CSS 样式
    font_family: str = "sans-serif"
    font_size: str = "16px"
    line_height: str = "1.75"
    color: str = "#333333"
    background: str = "#ffffff"
    link_color: str = "#576b95"
    code_bg: str = "#f7f7f7"
    quote_border: str = "#dfe2e5"
    heading_color: str = "#1a1a1a"
    meta: Dict[str, Any] = field(default_factory=dict)


# 内置主题注册表
THEMES: Dict[str, Theme] = {
    "default": Theme(
        name="default",
        display_name="默认简约",
        font_family="'Helvetica Neue', Arial, sans-serif",
        font_size="16px",
        line_height="1.75",
        color="#333333",
        background="#ffffff",
        link_color="#576b95",
        code_bg="#f7f7f7",
        quote_border="#dfe2e5",
        heading_color="#1a1a1a",
        css="""
        body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.75; color: #333; background: #fff; }
        h1, h2, h3, h4, h5, h6 { color: #1a1a1a; font-weight: 600; margin: 1.5em 0 0.8em; }
        h1 { font-size: 1.8em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
        h2 { font-size: 1.5em; }
        h3 { font-size: 1.3em; }
        a { color: #576b95; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { background: #f7f7f7; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; }
        pre { background: #f7f7f7; padding: 1em; border-radius: 5px; overflow-x: auto; }
        blockquote { border-left: 4px solid #dfe2e5; margin: 1em 0; padding: 0.5em 1em; color: #666; background: #fafafa; }
        img { max-width: 100%; height: auto; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
        th { background: #f5f5f5; }
        """,
    ),
    "wechat": Theme(
        name="wechat",
        display_name="微信风格",
        font_family="'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
        font_size="16px",
        line_height="1.75",
        color="#3f3f3f",
        background="#ffffff",
        link_color="#7a9c59",
        code_bg="#f2f2f2",
        quote_border="#d9d9d9",
        heading_color="#2c2c2c",
        css="""
        body { font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; font-size: 16px; line-height: 1.75; color: #3f3f3f; background: #fff; }
        h1, h2, h3, h4, h5, h6 { color: #2c2c2c; font-weight: 600; margin: 1.4em 0 0.8em; }
        h1 { font-size: 1.7em; border-bottom: 1px solid #e8e8e8; padding-bottom: 0.3em; }
        h2 { font-size: 1.45em; }
        h3 { font-size: 1.25em; }
        a { color: #7a9c59; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { background: #f2f2f2; padding: 0.2em 0.4em; border-radius: 3px; font-family: 'SF Mono', Consolas, monospace; }
        pre { background: #f8f8f8; padding: 1em; border-radius: 6px; overflow-x: auto; border: 1px solid #e8e8e8; }
        blockquote { border-left: 4px solid #d9d9d9; margin: 1em 0; padding: 0.6em 1em; color: #777; background: #fafafa; }
        img { max-width: 100%; height: auto; border-radius: 4px; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #e0e0e0; padding: 8px 12px; text-align: left; }
        th { background: #f7f7f7; font-weight: 600; }
        """,
    ),
    "clean": Theme(
        name="clean",
        display_name="极简清爽",
        font_family="'Inter', 'Helvetica Neue', Arial, sans-serif",
        font_size="15px",
        line_height="1.8",
        color="#444",
        background="#fefefe",
        link_color="#3498db",
        code_bg="#f0f0f0",
        quote_border="#bdc3c7",
        heading_color="#2c3e50",
        css="""
        body { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; font-size: 15px; line-height: 1.8; color: #444; background: #fefefe; }
        h1, h2, h3, h4, h5, h6 { color: #2c3e50; font-weight: 500; margin: 1.3em 0 0.7em; letter-spacing: -0.02em; }
        h1 { font-size: 1.8em; }
        h2 { font-size: 1.5em; }
        h3 { font-size: 1.3em; }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { background: #f0f0f0; padding: 0.15em 0.4em; border-radius: 2px; font-family: 'SF Mono', Consolas, monospace; font-size: 0.9em; }
        pre { background: #f8f9fa; padding: 1.2em; border-radius: 4px; overflow-x: auto; border: 1px solid #e9ecef; }
        blockquote { border-left: 3px solid #bdc3c7; margin: 1em 0; padding: 0.5em 1em; color: #666; background: #fafafa; }
        img { max-width: 100%; height: auto; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #dee2e6; padding: 8px 12px; text-align: left; }
        th { background: #f8f9fa; font-weight: 500; }
        """,
    ),
}


# ---------------------------------------------------------------------------
# Markdown 解析器（轻量级，支持常用语法）
# ---------------------------------------------------------------------------
class MarkdownParser:
    """轻量级 Markdown 解析器，将 Markdown 文本转换为 HTML。

    支持：标题、段落、粗体、斜体、行内代码、代码块、引用、列表、链接、图片、表格。
    不支持：脚注、任务列表、数学公式等高级语法。
    """

    # 正则表达式模式
    _HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    _BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
    _ITALIC_RE = re.compile(r"\*(.+?)\*")
    _CODE_INLINE_RE = re.compile(r"`([^`]+)`")
    _LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    _IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    _CODE_BLOCK_RE = re.compile(r"^
