#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e2m - 文档转 Markdown 格式转换与内容提取工具（独立实现）

本脚本根据功能规格独立编写，不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。
支持本地文件与 HTTP/HTTPS 链接的转换，以及内置样例的自检功能。
"""

import argparse
import html
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class ErrorCode:
    """错误码常量集合"""
    E001 = "E001: 输入路径或链接为空"
    E002 = "E002: 文件不存在或无法访问"
    E003 = "E003: 不支持的输入格式"
    E004 = "E004: 网络请求失败"
    E005 = "E005: 文件读取失败"
    E006 = "E006: 内容解析失败"
    E007 = "E007: 输出目录不存在或不可写"
    E008 = "E008: 音频转写需要网络服务，当前不可用"
    E009 = "E009: 输入参数无效"
    E010 = "E010: 未知内部错误"


# ---------------------------------------------------------------------------
# 支持的扩展名集合
# ---------------------------------------------------------------------------
SUPPORTED_TEXT_EXTS = {
    ".doc", ".docx", ".epub", ".html", ".htm", ".url",
    ".pdf", ".ppt", ".pptx", ".txt", ".md"
}
SUPPORTED_AUDIO_EXTS = {".mp3", ".m4a"}
SUPPORTED_EXTS = SUPPORTED_TEXT_EXTS | SUPPORTED_AUDIO_EXTS


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def _safe_strip(text: str) -> str:
    """安全去除首尾空白"""
    if not text:
        return ""
    return text.strip()


def _decode_bytes(data: bytes) -> str:
    """尝试多种编码解码字节数据"""
    for encoding in ("utf-8", "gbk", "latin-1", "utf-16"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    # 最后尝试忽略错误解码
    return data.decode("utf-8", errors="ignore")


def _parse_url_file(content: str) -> str:
    """解析 .url 文件，提取目标链接"""
    match = re.search(r"URL\s*=\s*(.+)", content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _clean_html_tags(text: str) -> str:
    """清理HTML标签"""
    # 移除所有HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码HTML实体
    text = html.unescape(text)
    return text


def _process_html_tables(html_content: str) -> str:
    """处理HTML表格，转换为Markdown表格格式"""
    def table_replacer(match):
        table_content = match.group(1)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, flags=re.DOTALL | re.IGNORECASE)
        if not rows:
            return match.group(0)
        
        markdown_rows = []
        for i, row in enumerate(rows):
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, flags=re.DOTALL | re.IGNORECASE)
            if not cells:
                continue
            cleaned_cells = [_clean_html_tags(cell).strip() for cell in cells]
            markdown_rows.append('| ' + ' | '.join(cleaned_cells) + ' |')
            
            # 添加表头分隔行
            if i == 0:
                markdown_rows.append('|' + '---|' * len(cells))
        
        return '\n' + '\n'.join(markdown_rows) + '\n'
    
    return re.sub(r'<table[^>]*>(.*?)</table>', table_replacer, html_content, flags=re.DOTALL | re.IGNORECASE)


def _html_to_markdown(html_content: str) -> str:
    """
    将 HTML 内容转换为简单 Markdown。
    提取标题、段落、列表、表格、链接等基本结构。
    """
    content = html_content

    # 去除 script 和 style 块
    content = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.DOTALL | re.IGNORECASE)

    # 提取 title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1)).strip() if title_match else ""

    # 处理表格
    content = _process_html_tables(content)

    # 处理标题
    for level in range(1, 7):
        pattern = rf"<h{level}[^>]*>(.*?)</h{level}>"
        def make_header_replacer(lvl):
            def replacer(m):
                text = _clean_html_tags(m.group(1)).strip()
                return f"\n{'#' * lvl} {text}\n"
            return replacer
        content = re.sub(
            pattern,
            make_header_replacer(level),
            content,
            flags=re.DOTALL | re.IGNORECASE
        )

    # 处理链接
    content = re.sub(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        lambda m: f"[{_clean_html_tags(m.group(2)).strip()}]({m.group(1).strip()})",
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # 处理图片
    content = re.sub(
        r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>',
        lambda m: f"![图片]({m.group(1).strip()})",
        content,
        flags=re.IGNORECASE
    )

    # 处理列表项
    content = re.sub(r"<li[^>]*>(.*?)</li>", lambda m: "- " + _clean_html_tags(m.group(1)).strip() + "\n",
                     content, flags=re.DOTALL | re.IGNORECASE)

    # 处理段落和换行
    content = re.sub(r"</p>", "\n\n", content, flags=re.IGNORECASE)
    content = re.sub(r"<br\s*/?>", "\n", content, flags=re.IGNORECASE)

    # 处理代码块
    content = re.sub(
        r"<pre[^>]*>(.*?)</pre>",
        lambda m: "\n
