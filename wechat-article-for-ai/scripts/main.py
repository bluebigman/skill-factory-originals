#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat-article-for-ai - 公众号文章 Markdown 转换器
=================================================
将微信公众号文章链接转为结构化 Markdown，支持批量处理与图片本地化。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --url "https://mp.weixin.qq.com/s/example"
    python scripts/main.py --file urls.txt --output ./output --local-images

错误码说明:
    E001: 参数解析错误
    E002: 输入文件不存在或不可读
    E003: 输出目录创建失败
    E004: URL 格式不合法
    E005: 非微信公众号域名
    E006: 网络请求失败（重试耗尽）
    E007: 下载图片失败
    E008: 写入文件失败
    E009: HTML 解析失败
    E010: 自检失败
"""

import argparse
import html
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Article:
    """一篇文章的数据结构"""
    url: str
    title: str = ""
    author: str = ""
    publish_time: str = ""
    content_html: str = ""
    images: List[str] = field(default_factory=list)  # 原始图片 URL 列表
    success: bool = False
    error_code: Optional[str] = None
    error_msg: str = ""


@dataclass
class ConversionResult:
    """一次转换的结果"""
    articles: List[Article] = field(default_factory=list)
    output_dir: str = ""
    total: int = 0
    succeeded: int = 0
    failed: int = 0


# ============================================================
# 常量定义
# ============================================================

WECHAT_DOMAIN = "mp.weixin.qq.com"
DEFAULT_TIMEOUT = 15          # 网络超时（秒）
MAX_RETRIES = 3               # 最大重试次数
RETRY_INTERVAL = 2            # 重试间隔（秒）
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 自检用硬编码样例数据（不读外部文件、不访问网络）
SELFTEST_SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="示例文章标题" />
    <meta property="og:author" content="示例作者" />
    <meta property="og:release_date" content="2026-01-15" />
</head>
<body>
    <div id="js_content">
        <p>这是第一段正文内容。</p>
        <img src="https://mmbiz.qpic.cn/mmbiz_jpg/example1/640" />
        <p>这是第二段，包含 <strong>加粗</strong> 和 <a href="https://example.com">链接</a>。</p>
        <img src="https://mmbiz.qpic.cn/mmbiz_png/example2/640" />
    </div>
</body>
</html>
"""

SELFTEST_SAMPLE_URL = "https://mp.weixin.qq.com/s/selftest_sample_123456"


# ============================================================
# 核心逻辑：HTML 解析与 Markdown 转换
# ============================================================

class HtmlToMarkdownConverter:
    """将微信文章 HTML 转换为 Markdown 文本"""

    def __init__(self, base_url: str = "", local_image_dir: str = ""):
        self.base_url = base_url
        self.local_image_dir = local_image_dir
        self.image_urls: List[str] = []

    def convert(self, html_content: str) -> Tuple[str, List[str]]:
        """
        将 HTML 字符串转换为 Markdown。
        返回: (markdown文本, 图片URL列表)
        """
        self.image_urls = []
        if not html_content or not html_content.strip():
            return "", []

        # 去除 script 和 style 块
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 提取正文区域（简化处理：取 js_content 或 body）
        body_match = re.search(r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>', text, flags=re.DOTALL | re.IGNORECASE)
        if body_match:
            text = body_match.group(1)
        else:
            body_match = re.search(r'<body[^>]*>(.*?)</body>', text, flags=re.DOTALL | re.IGNORECASE)
            if body_match:
                text = body_match.group(1)

        # 逐块处理
        lines: List[str] = []
        # 按块级元素分割
        blocks = re.split(r'(<(?:p|div|h[1-6]|li|blockquote|pre|table|br)[^>]*>)', text, flags=re.IGNORECASE)

        for block in blocks:
            stripped = block.strip()
            if not stripped:
                continue

            # 块级标签开始
            tag_match = re.match(r'<(/?)(p|div|h[1-6]|li|blockquote|pre|table|br)[^>]*>', stripped, flags=re.IGNORECASE)
            if tag_match:
                tag = tag_match.group(2).lower()
                closing = tag_match.group(1) == '/'
                if tag == 'br':
                    lines.append('  \n')  # Markdown 换行
                elif tag == 'h1':
                    lines.append('\n# ')
                elif tag == 'h2':
                    lines.append('\n## ')
                elif tag == 'h3':
                    lines.append('\n### ')
                elif tag == 'h4':
                    lines.append('\n#### ')
                elif tag == 'h5':
                    lines.append('\n##### ')
                elif tag == 'h6':
                    lines.append('\n###### ')
                elif tag == 'li' and not closing:
                    lines.append('\n- ')
                elif tag == 'blockquote' and not closing:
                    lines.append('\n> ')
                elif tag == 'pre' and not closing:
                    lines.append('\n
