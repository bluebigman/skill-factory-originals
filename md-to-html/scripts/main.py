#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md-to-html 技能实现脚本

功能：将 Markdown 文本转换为结构化 HTML
支持：文本、文件、URL 输入；批量处理；自定义 CSS 类名
"""

import argparse
import html
import os
import re
import sys
import urllib.request
from pathlib import Path


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数",
    "E002": "文件读取失败：文件不存在或无权限",
    "E003": "URL 抓取失败：网络错误或资源不可达",
    "E004": "Markdown 解析错误：无效的输入格式",
    "E005": "HTML 生成错误：模板渲染失败",
    "E006": "批量处理错误：部分项目转换失败",
    "E007": "输出写入失败：目标路径不可写",
    "E008": "编码错误：不支持的字符编码",
    "E009": "安全错误：检测到不安全的输入内容",
    "E010": "内部错误：未预期的异常",
}


class MDToHTMLConverter:
    """Markdown 转 HTML 核心转换器"""

    def __init__(self, css_class_prefix="md"):
        """
        初始化转换器

        Args:
            css_class_prefix: CSS 类名前缀
        """
        self.prefix = css_class_prefix

    def _escape(self, text):
        """转义 HTML 特殊字符"""
        return html.escape(text, quote=False)

    def _inline(self, text):
        """处理行内 Markdown 语法（粗体、斜体、行内代码、链接）"""
        # 转义 HTML 特殊字符（但保留用于标记的字符）
        text = self._escape(text)

        # 行内代码
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

        # 粗体
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

        # 斜体
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)

        # 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

        return text

    def _handle_heading(self, line):
        """处理标题行"""
        match = re.match(r'^(#{1,6})\s+(.*)', line)
        if match:
            level = len(match.group(1))
            content = self._inline(match.group(2).strip())
            return f'<h{level} class="{self.prefix}-h{level}">{content}</h{level}>'
        return None

    def _handle_list_item(self, line, list_type):
        """处理列表项"""
        if list_type == 'ul':
            match = re.match(r'^\s*[-*+]\s+(.*)', line)
        else:
            match = re.match(r'^\s*\d+\.\s+(.*)', line)
        if match:
            content = self._inline(match.group(1).strip())
            return f'<li class="{self.prefix}-li">{content}</li>'
        return None

    def convert(self, markdown_text):
        """
        将 Markdown 文本转换为 HTML

        Args:
            markdown_text: Markdown 格式的字符串

        Returns:
            转换后的 HTML 字符串
        """
        if not markdown_text or not markdown_text.strip():
            raise ValueError("E004: 输入内容为空")

        # 按行处理
        lines = markdown_text.split("\n")
        html_lines = []
        in_code_block = False
        in_list = False
        list_type = None

        i = 0
        while i < len(lines):
            line = lines[i]

            # 代码块处理
            if line.strip().startswith("
