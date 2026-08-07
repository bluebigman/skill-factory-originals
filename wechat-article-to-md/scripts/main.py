#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
微信公众号文章 Markdown 转换器（独立实现）

本脚本依据功能规格独立实现，不复制任何既有代码。
核心能力：解析公众号文章 HTML/文本，提取标题、作者、正文，转换为 Markdown，
并支持图片下载占位与本地化处理。

仅依赖 Python 标准库。
"""

import argparse
import html
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容（数据/文件/URL）",
    "E002": "关键信息缺失（标题或正文为空），无法生成有效 Markdown",
    "E003": "输入格式错误，无法解析为有效的公众号文章内容",
    "E004": "超出能力边界：不支持的输入类型或操作",
    "E005": "置信度过低：内容疑似不完整或非公众号文章，请人工复核",
    "E006": "文件读取失败：无法读取指定文件",
    "E007": "文件写入失败：无法写入输出文件",
    "E008": "网络请求失败：无法获取 URL 内容",
    "E009": "图片下载失败：无法下载指定图片",
    "E010": "参数错误：命令行参数不合法",
}


class WeChatArticleError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class Article:
    """文章数据模型"""

    def __init__(self):
        self.title: str = ""
        self.author: str = ""
        self.content_html: str = ""       # 原始 HTML 正文
        self.content_text: str = ""       # 纯文本正文
        self.images: List[str] = []       # 图片 URL 列表
        self.confidence: float = 0.0      # 置信度 0-100
        self.source: str = ""             # 来源标识（URL/文件名/手动输入）

    def to_markdown(self, image_dir: Optional[str] = None) -> str:
        """将文章转换为 Markdown 文本"""
        lines: List[str] = []

        # 标题
        if self.title:
            lines.append(f"# {self.title}")
            lines.append("")

        # 作者与来源
        meta_parts = []
        if self.author:
            meta_parts.append(f"**作者：** {self.author}")
        if self.source:
            meta_parts.append(f"**来源：** {self.source}")
        if meta_parts:
            lines.append(" | ".join(meta_parts))
            lines.append("")

        lines.append("---")
        lines.append("")

        # 正文（优先用 HTML 转 Markdown，否则用纯文本）
        if self.content_html:
            md_body = html_to_markdown(self.content_html, image_dir)
            lines.append(md_body)
        else:
            lines.append(self.content_text)

        # 置信度标注
        if self.confidence < 85:
            lines.append("")
            lines.append("---")
            lines.append(f"> ⚠️ **[需核实]** 内容置信度仅为 {self.confidence:.0f}%，请人工复核关键信息。")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML 解析与转换
# ---------------------------------------------------------------------------

def html_to_markdown(html_content: str, image_dir: Optional[str] = None) -> str:
    """
    将 HTML 正文转换为 Markdown 格式。
    支持常见标签：p, br, strong, em, h1-h6, blockquote, ul/ol/li, img, a, pre/code
    """
    # 移除脚本和样式
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)

    # 处理代码块（先保护）
    code_blocks: List[str] = []
    def _save_code(match):
        code_blocks.append(match.group(1))
        return f"@@CODEBLOCK{len(code_blocks)-1}@@"
    text = re.sub(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", _save_code, text, flags=re.S | re.I)
    text = re.sub(r"<code[^>]*>(.*?)</code>", _save_code, text, flags=re.S | re.I)

    # 图片
    def _img_repl(match):
        src = match.group(1) or ""
        alt = match.group(2) or ""
        if not src:
            return ""
        if image_dir:
            # 尝试下载图片（失败则保留原 URL）
            local_path = download_image(src, image_dir)
            if local_path:
                return f"![{alt}]({local_path})"
        return f"![{alt}]({src})"
    text = re.sub(r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\']', _img_repl, text, flags=re.I)
    text = re.sub(r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']*)["\']', 
                  lambda m: f"![{m.group(1)}]({m.group(2)})", text, flags=re.I)
    text = re.sub(r'<img[^>]*src=["\']([^"\']*)["\']', lambda m: f"![图片]({m.group(1)})", text, flags=re.I)

    # 标题
    for level in range(1, 7):
        text = re.sub(
            rf"<h{level}[^>]*>(.*?)</h{level}>",
            lambda m, l=level: "\n" + "#" * l + " " + clean_inline(m.group(1)) + "\n",
            text,
            flags=re.S | re.I,
        )

    # 段落和换行
    text = re.sub(r"<br\s*/?>", "\n\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<p[^>]*>", "", text, flags=re.I)

    # 引用
    text = re.sub(
        r"<blockquote[^>]*>(.*?)</blockquote>",
        lambda m: "\n".join("> " + line for line in m.group(1).strip().split("\n")) + "\n",
        text,
        flags=re.S | re.I,
    )

    # 列表
    text = re.sub(r"<ul[^>]*>(.*?)</ul>", lambda m: "\n" + parse_list(m.group(1), "ul") + "\n", text, flags=re.S | re.I)
    text = re.sub(r"<ol[^>]*>(.*?)</ol>", lambda m: "\n" + parse_list(m.group(1), "ol") + "\n", text, flags=re.S | re.I)

    # 链接
    text = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        lambda m: f"[{clean_inline(m.group(2))}]({m.group(1)})",
        text,
        flags=re.S | re.I,
    )

    # 粗体/斜体
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", lambda m: f"**{clean_inline(m.group(1))}**", text, flags=re.S | re.I)
    text = re.sub(r"<b[^>]*>(.*?)</b>", lambda m: f"**{clean_inline(m.group(1))}**", text, flags=re.S | re.I)
    text = re.sub(r"<em[^>]*>(.*?)</em>", lambda m: f"*{clean_inline(m.group(1))}*", text, flags=re.S | re.I)
    text = re.sub(r"<i[^>]*>(.*?)</i>", lambda m: f"*{clean_inline(m.group(1))}*", text, flags=re.S | re.I)

    # 水平线
    text = re.sub(r"<hr\s*/?>", "\n\n---\n\n", text, flags=re.I)

    # 移除剩余 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)

    # 恢复代码块
    def _restore_code(match):
        idx = int(match.group(1))
        return "\n
