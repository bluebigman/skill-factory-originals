#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jina-cli 独立实现脚本（clean-room 重写）

功能：将 URL 或本地文件内容转换为结构化文本（纯文本 / Markdown / JSON）。
仅依据功能规格实现，不参考任何既有代码。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --version
    python scripts/main.py --format json https://example.com
    python scripts/main.py ./notes.txt
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

# 版本号
VERSION = "1.0.1"

# 错误码定义
ERR_OK = 0
ERR_INVALID_ARGS = "E001"
ERR_URL_FETCH = "E002"
ERR_FILE_READ = "E003"
ERR_UNSUPPORTED_FORMAT = "E004"
ERR_NETWORK_UNAVAILABLE = "E005"
ERR_INVALID_URL = "E006"
ERR_EMPTY_INPUT = "E007"
ERR_OUTPUT_WRITE = "E008"
ERR_INTERNAL = "E009"
ERR_SELFTEST_FAIL = "E010"


def log_error(code: str, message: str) -> int:
    """输出错误信息到 stderr，返回错误码。"""
    print(f"[错误 {code}] {message}", file=sys.stderr)
    return 1


def is_valid_url(text: str) -> bool:
    """粗略判断字符串是否为合法 HTTP(S) URL。"""
    if not text or len(text) < 8:
        return False
    # 仅检查前缀和基本结构，不做过细校验
    return text.startswith("http://") or text.startswith("https://")


def extract_text_from_html(html_content: str) -> str:
    """
    从 HTML 内容中提取纯文本（简易实现）。
    仅做基础标签剥离和空白整理，不执行 JS。
    """
    if not html_content:
        return ""

    # 移除 script / style 块
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html_content)

    # 将常见块级标签替换为换行
    text = re.sub(r"(?i)</?(p|div|h[1-6]|li|br|tr|section|article)[^>]*>", "\n", text)

    # 移除其余所有标签
    text = re.sub(r"<[^>]+>", " ", text)

    # 解码常见 HTML 实体
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    # 整理空白：多行合并，行内多余空格压缩
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


def html_to_markdown(html_content: str) -> str:
    """
    将 HTML 转换为简易 Markdown。
    保留标题、链接、列表等基本结构。
    """
    if not html_content:
        return ""

    text = html_content

    # 提取标题
    for level in range(1, 7):
        pattern = rf"(?is)<h{level}[^>]*>(.*?)</h{level}>"
        text = re.sub(pattern, lambda m: "\n" + "#" * level + " " +
                       re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n", text)

    # 提取链接
    text = re.sub(r'(?is)<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                  lambda m: f"[{re.sub(r'<[^>]+>', '', m.group(2)).strip()}]({m.group(1)})",
                  text)

    # 提取图片
    text = re.sub(r'(?is)<img[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*)["\']',
                  lambda m: f"![{m.group(2)}]({m.group(1)})", text)

    # 列表项
    text = re.sub(r"(?is)<li[^>]*>(.*?)</li>", lambda m: "- " +
                  re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n", text)

    # 代码块
    text = re.sub(r"(?is)<pre[^>]*><code[^>]*>(.*?)</code></pre>",
                  lambda m: "\n
