#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章 Markdown 转换器 (wechat-article-for-ai)

独立实现脚本，依据功能规格从零编写（clean-room）。
支持将微信公众号文章链接转换为结构化 Markdown，包含批量处理与图片本地化能力。

用法示例:
    python main.py --url "https://mp.weixin.qq.com/s/example"
    python main.py --file urls.txt
    python main.py --selftest
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "URL 格式无效或为空",
    "E002": "非微信公众号域名，拒绝处理",
    "E003": "网络请求失败（连接错误、超时等）",
    "E004": "HTTP 状态码异常（非 200）",
    "E005": "页面内容解析失败（无法提取正文）",
    "E006": "图片下载失败",
    "E007": "输出目录创建失败",
    "E008": "批量处理时 URL 列表为空",
    "E009": "文件读取失败（批量 URL 文件不存在或不可读）",
    "E010": "内部逻辑错误（未预期的异常分支）",
}

# 微信公众号域名白名单
WECHAT_DOMAINS = (
    "mp.weixin.qq.com",
    "weixin.qq.com",
)

# 重试相关配置
MAX_RETRY = 3
RETRY_INTERVAL_SECONDS = 2

# 默认请求头，模拟浏览器访问
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Article:
    """文章数据模型"""
    url: str
    title: str = ""
    author: str = ""
    publish_time: str = ""
    content_html: str = ""
    content_markdown: str = ""
    images: List[str] = field(default_factory=list)  # 本地图片路径列表


@dataclass
class ConvertResult:
    """单篇文章转换结果"""
    article: Optional[Article] = None
    success: bool = False
    error_code: str = ""
    error_message: str = ""


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def is_wechat_url(url: str) -> bool:
    """判断是否为微信公众号文章链接"""
    if not url or not url.strip():
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
        host = parsed.netloc.lower()
        return any(host == d or host.endswith("." + d) for d in WECHAT_DOMAINS)
    except Exception:
        return False


def fetch_html(url: str, timeout: int = 15) -> str:
    """
    抓取网页 HTML 内容，带重试机制。
    
    返回:
        页面 HTML 字符串
        
    异常:
        抛出 RuntimeError，携带错误码 E003 或 E004
    """
    last_error = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.getcode()
                if status != 200:
                    raise RuntimeError(
                        f"HTTP {status}",
                        ERROR_CODES["E004"],
                    )
                # 尝试从响应头获取编码，默认 UTF-8
                charset = "utf-8"
                content_type = resp.headers.get("Content-Type", "")
                m = re.search(r"charset=([\w-]+)", content_type)
                if m:
                    charset = m.group(1)
                raw = resp.read()
                try:
                    return raw.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    return raw.decode("utf-8", errors="replace")
        except RuntimeError:
            raise  # 直接抛出 HTTP 错误
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRY:
                time.sleep(RETRY_INTERVAL_SECONDS)
    
    raise RuntimeError(
        f"网络请求失败: {last_error}",
        ERROR_CODES["E003"],
    )


def extract_json_from_script(html_text: str) -> Optional[Dict]:
    """
    从 HTML 中提取 var msg_title / var msg_desc 等变量。
    
    微信公众号文章页通常在 <script> 中嵌入 var 变量。
    这里用正则提取关键字段。
    """
    result = {}
    # 标题
    m = re.search(r'var\s+msg_title\s*=\s*["\'](.+?)["\']', html_text)
    if m:
        result["title"] = m.group(1)
    # 作者
    m = re.search(r'var\s+author\s*=\s*["\'](.+?)["\']', html_text)
    if m:
        result["author"] = m.group(1)
    # 发布时间
    m = re.search(r'var\s+ct\s*=\s*["\']?(\d+)["\']?', html_text)
    if m:
        ts = int(m.group(1))
        if ts > 0:
            import datetime
            result["publish_time"] = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    # 正文内容（HTML 片段）
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html_text, re.S)
    if m:
        result["content_html"] = m.group(1).strip()
    return result if result else None


def _strip_html(text: str) -> str:
    """去除 HTML 标签并解码实体"""
    if not text:
        return ""
    # 移除所有 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码 HTML 实体
    text = html.unescape(text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def html_to_markdown(html_fragment: str) -> str:
    """
    将 HTML 片段转换为 Markdown 文本。
    
    采用轻量级转换：处理标题、段落、列表、图片、链接、加粗、斜体等常见元素。
    非完整 HTML 解析器，但足以覆盖公众号文章的常见格式。
    """
    if not html_fragment:
        return ""
    
    text = html_fragment
    
    # 移除注释
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    
    # 处理图片：提取 src 与 alt
    def _img_repl(match):
        src = match.group(1) or ""
        alt = match.group(2) or ""
        return f"\n![{alt}]({src})\n"
    text = re.sub(r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\']', _img_repl, text)
    text = re.sub(r'<img[^>]*src=["\']([^"\']*)["\']', lambda m: f"\n![{m.group(1)}]({m.group(1)})\n", text)
    
    # 标题 h1-h6
    for level in range(6, 0, -1):
        text = re.sub(
            rf'<h{level}[^>]*>(.*?)</h{level}>',
            lambda m, l=level: "\n" + "#" * l + " " + _strip_html(m.group(1)) + "\n",
            text,
            flags=re.S,
        )
    
    # 段落
    text = re.sub(r'<p[^>]*>(.*?)</p>', lambda m: "\n" + _strip_html(m.group(1)) + "\n", text, flags=re.S)
    
    # 换行
    text = re.sub(r'<br\s*/?>', "\n", text)
    
    # 加粗 / 斜体
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', lambda m: "**" + _strip_html(m.group(1)) + "**", text, flags=re.S)
    text = re.sub(r'<b[^>]*>(.*?)</b>', lambda m: "**" + _strip_html(m.group(1)) + "**", text, flags=re.S)
    text = re.sub(r'<em[^>]*>(.*?)</em>', lambda m: "*" + _strip_html(m.group(1)) + "*", text, flags=re.S)
    text = re.sub(r'<i[^>]*>(.*?)</i>', lambda m: "*" + _strip_html(m.group(1)) + "*", text, flags=re.S)
    
    # 链接
    text = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        lambda m: f"[{_strip_html(m.group(2))}]({m.group(1)})",
        text,
        flags=re.S,
    )
    
    # 列表（简化处理，不做嵌套）
    def _li_repl(match):
        return "\n- " + _strip_html(match.group(1)).strip() + "\n"
    text = re.sub(r'<li[^>]*>(.*?)</li>', _li_repl, text, flags=re.S)
    
    # 代码块
    def _code_repl(match):
        code = match.group(1) or ""
        # 移除代码块内的 HTML 标签
        code = re.sub(r'<[^>]+>', '', code)
        # 解码 HTML 实体
        code = html.unescape(code)
        return "\n
