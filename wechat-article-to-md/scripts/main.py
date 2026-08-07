#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 微信公众号文章转 Markdown 工具（独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
功能：抓取微信公众号文章，提取标题/作者/发布时间/正文，
      将正文中的图片替换为本地相对路径引用，并下载图片到 images/ 目录。
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
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INVALID_URL = "E001"       # URL 格式不合法
ERR_FETCH_FAILED = "E002"      # 网络请求失败
ERR_PARSE_FAILED = "E003"      # 页面解析失败
ERR_IMG_DOWNLOAD = "E004"      # 图片下载失败
ERR_OUTPUT_WRITE = "E005"      # 输出文件写入失败
ERR_NO_CONTENT = "E006"        # 未提取到正文内容
ERR_UNSUPPORTED_DOMAIN = "E007"  # 非微信公众号域名
ERR_INVALID_ARGS = "E008"      # 命令行参数错误
ERR_IO_ERROR = "E009"          # 文件系统操作失败
ERR_UNKNOWN = "E010"           # 未知错误


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class Article:
    """文章数据模型"""
    title: str = ""
    author: str = ""
    publish_time: str = ""
    content_html: str = ""
    images: List[str] = field(default_factory=list)  # 原始图片 URL 列表


@dataclass
class ConversionResult:
    """转换结果"""
    article: Optional[Article] = None
    markdown: str = ""
    image_map: Dict[str, str] = field(default_factory=dict)  # 原始URL -> 本地路径
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心逻辑（纯函数，便于测试）
# ---------------------------------------------------------------------------
def is_valid_wechat_url(url: str) -> bool:
    """检查是否为合法的微信公众号文章 URL"""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    # 微信公众号文章域名：mp.weixin.qq.com
    if parsed.netloc and "mp.weixin.qq.com" not in parsed.netloc:
        return False
    # 路径必须包含 /s/ 或 /s? 形式
    if "/s/" not in parsed.path and "/s" != parsed.path:
        return False
    return True


def fetch_html(url: str, timeout: int = 15) -> str:
    """抓取网页 HTML 内容"""
    if not is_valid_wechat_url(url):
        raise ValueError(ERR_INVALID_URL)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            # 尝试检测编码
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(charset, errors="replace")
            except LookupError:
                return raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{ERR_FETCH_FAILED}: HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"{ERR_FETCH_FAILED}: {e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"{ERR_FETCH_FAILED}: {str(e)}") from e


def extract_article(html_text: str) -> Article:
    """
    从 HTML 中提取文章信息。
    使用正则表达式解析，不依赖第三方 HTML 解析库。
    """
    if not html_text or len(html_text) < 100:
        raise RuntimeError(ERR_PARSE_FAILED)

    article = Article()

    # 提取标题：优先 og:title meta，其次 <h1> 或 <title>
    title_match = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        html_text, re.IGNORECASE
    )
    if not title_match:
        title_match = re.search(
            r'<h1[^>]*>(.*?)</h1>', html_text, re.DOTALL | re.IGNORECASE
        )
    if not title_match:
        title_match = re.search(
            r'<title[^>]*>(.*?)</title>', html_text, re.DOTALL | re.IGNORECASE
        )
    if title_match:
        article.title = html.unescape(re.sub(r'<[^>]+>', '', title_match.group(1))).strip()

    # 提取作者
    author_match = re.search(
        r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']*)["\']',
        html_text, re.IGNORECASE
    )
    if not author_match:
        author_match = re.search(
            r'var\s+author\s*=\s*["\']([^"\']*)["\']', html_text
        )
    if not author_match:
        author_match = re.search(
            r'id=["\']js_name["\'][^>]*>\s*([^<]+?)\s*<', html_text
        )
    if author_match:
        article.author = html.unescape(author_match.group(1)).strip()

    # 提取发布时间
    time_match = re.search(
        r'var\s+publish_time\s*=\s*["\']([^"\']*)["\']', html_text
    )
    if not time_match:
        time_match = re.search(
            r'id=["\']publish_time["\'][^>]*>\s*([^<]+?)\s*<', html_text
        )
    if not time_match:
        time_match = re.search(
            r'createTime\s*[:=]\s*["\']?([0-9-]{8,})', html_text
        )
    if time_match:
        article.publish_time = html.unescape(time_match.group(1)).strip()

    # 提取正文区域
    content_match = re.search(
        r'<div[^>]+id=["\']js_content["\'][^>]*>(.*?)</div>\s*<script',
        html_text, re.DOTALL | re.IGNORECASE
    )
    if not content_match:
        content_match = re.search(
            r'<div[^>]+class=["\'][^"\']*rich_media_content[^"\']*["\'][^>]*>(.*?)</div>',
            html_text, re.DOTALL | re.IGNORECASE
        )
    if not content_match:
        # 兜底：尝试找最大的文本块
        content_match = re.search(
            r'<div[^>]+class=["\'][^"\']*rich_media_area_primary[^"\']*["\'][^>]*>(.*?)</div>',
            html_text, re.DOTALL | re.IGNORECASE
        )
    if content_match:
        article.content_html = content_match.group(1).strip()
    else:
        # 如果实在找不到正文，尝试提取 body 内所有文本
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_text, re.DOTALL | re.IGNORECASE)
        if body_match:
            article.content_html = body_match.group(1).strip()

    # 提取所有图片 URL
    img_urls = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']', article.content_html, re.IGNORECASE
    )
    # 过滤 data: URI 和空值
    article.images = [
        u for u in img_urls
        if u and not u.startswith("data:") and u.startswith("http")
    ]

    if not article.title and not article.content_html:
        raise RuntimeError(ERR_NO_CONTENT)

    return article


def clean_inline(text: str) -> str:
    """清理内联 HTML 标签，保留文本内容"""
    if not text:
        return ""
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解压 HTML 实体
    text = html.unescape(text)
    return text.strip()


def html_to_markdown(html_text: str, image_map: Dict[str, str] = None) -> str:
    """
    将 HTML 正文转换为 Markdown。
    支持：标题、段落、加粗、斜体、引用、代码块、图片、链接、列表。
    """
    if not html_text:
        return ""

    text = html_text
    image_map = image_map or {}

    # 1. 处理图片：替换为 Markdown 格式
    def replace_img(match):
        src = match.group(1)
        alt = match.group(2) or ""
        if src in image_map:
            local_path = image_map[src]
            return f"![{alt}]({local_path})"
        return f"![{alt}]({src})"

    # 处理 src 在 alt 前的图片
    text = re.sub(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*)["\']',
        replace_img, text, flags=re.IGNORECASE
    )
    # 处理 alt 在 src 前的图片
    text = re.sub(
        r'<img[^>]+alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']+)["\']',
        lambda m: f"![{m.group(1)}]({image_map.get(m.group(2), m.group(2))})",
        text, flags=re.IGNORECASE
    )
    # 处理无 alt 的图片
    text = re.sub(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        lambda m: f"![image]({image_map.get(m.group(1), m.group(1))})",
        text, flags=re.IGNORECASE
    )

    # 2. 移除 script/style
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 3. 替换常见标签
    # 标题
    for level in range(1, 7):
        pattern = r'<h' + str(level) + r'[^>]*>(.*?)</h' + str(level) + r'>'
        text = re.sub(
            pattern,
            lambda m, l=level: "\n" + "#" * l + " " + clean_inline(m.group(1)) + "\n",
            text, flags=re.DOTALL | re.IGNORECASE
        )
    
    # 加粗
    text = re.sub(
        r'<(strong|b)[^>]*>(.*?)</\1>',
        lambda m: f"**{clean_inline(m.group(2))}**",
        text, flags=re.DOTALL | re.IGNORECASE
    )
    # 斜体
    text = re.sub(
        r'<(em|i)[^>]*>(.*?)</\1>',
        lambda m: f"*{clean_inline(m.group(2))}*",
        text, flags=re.DOTALL | re.IGNORECASE
    )
    # 引用
    text = re.sub(
        r'<blockquote[^>]*>(.*?)</blockquote>',
        lambda m: "\n> " + clean_inline(m.group(1)).replace("\n", "\n> ") + "\n",
        text, flags=re.DOTALL | re.IGNORECASE
    )
    # 代码块
    text = re.sub(
        r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
        lambda m: "\n
