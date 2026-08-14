#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章链接转 Markdown 本地归档工具
功能规格版本: 1.0.2
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import uuid
from datetime import timezone

_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"

ERROR_CODES = {
    "E001": "参数错误：未提供文章链接",
    "E002": "参数错误：链接格式无效",
    "E003": "网络错误：无法访问目标链接",
    "E004": "抓取错误：未找到文章正文内容",
    "E005": "解析错误：无法解析文章元数据",
    "E006": "文件错误：无法写入输出文件",
    "E007": "配置错误：输出目录不存在或不可写",
    "E008": "数据错误：抓取内容为空",
    "E009": "运行时错误：未预期的异常",
    "E010": "自检错误：内置自检未通过",
}


def _read_text_safe(path):
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def _err(code: str, message: str = "") -> str:
    base = ERROR_CODES.get(code, "未知错误")
    if message:
        return f"[{code}] {base}: {message}"
    return f"[{code}] {base}"


class ArticleData:
    def __init__(self, url: str):
        self.url = url
        self.title = ""
        self.author = ""
        self.content_html = ""
        self.publish_date = ""
        self.fetch_time = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def to_markdown(self) -> str:
        lines = ["---"]
        lines.append(f'title: "{self.title}"')
        lines.append(f'author: "{self.author}"')
        lines.append(f'source: "{self.url}"')
        lines.append(f'fetch_time: "{self.fetch_time}"')
        lines.append(f'publish_date: "{self.publish_date}"')
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")
        if self.author:
            lines.append(f"> 作者：{self.author}")
            lines.append("")
        if self.publish_date:
            lines.append(f"> 发布时间：{self.publish_date}")
            lines.append("")
        lines.append(f"> 来源：[原文链接]({self.url})")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(self._html_to_markdown(self.content_html))
        return "\n".join(lines)

    def _html_to_markdown(self, html_content: str) -> str:
        if not html_content:
            return ""

        text = html_content

        for i in range(1, 7):
            text = re.sub(rf'<h{i}[^>]*>', f'{"#" * i} ', text, flags=re.IGNORECASE)
            text = re.sub(rf'</h{i}>', '\n\n', text, flags=re.IGNORECASE)

        text = re.sub(r'<p[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)

        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<hr\s*/?>', '\n---\n', text, flags=re.IGNORECASE)

        def img_replacer(match):
            src = match.group(1)
            alt = match.group(2) or "图片"
            return f"![{alt}]({src})"

        text = re.sub(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*>',
                      img_replacer, text, flags=re.IGNORECASE)
        text = re.sub(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>',
                      lambda m: f"![图片]({m.group(1)})", text, flags=re.IGNORECASE)

        def link_replacer(match):
            href = match.group(1)
            link_text = match.group(2)
            return f"[{link_text}]({href})"

        text = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                      link_replacer, text, flags=re.IGNORECASE | re.DOTALL)

        text = re.sub(r'<ul[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ul>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<ol[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ol>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '- ', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)

        text = re.sub(r'<blockquote[^>]*>', '\n> ', text, flags=re.IGNORECASE)
        text = re.sub(r'</blockquote>', '\n', text, flags=re.IGNORECASE)

        text = re.sub(r'<pre[^>]*><code[^>]*>', '\n
