#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
android-web-scraper 独立实现脚本
--------------------------------
根据功能规格 clean-room 重写，实现真实网络请求和HTML解析。
提供 --selftest 参数进行自检。

注意：本脚本支持桌面 Python 环境，并通过 Termux 兼容层支持安卓设备后台静默执行。
"""

import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 错误码定义
E001 = "E001: 参数错误"
E002 = "E002: 输入内容为空"
E003 = "E003: 输入格式不支持"
E004 = "E004: HTML 解析失败"
E005 = "E005: 字段提取失败"
E006 = "E006: 输出格式不支持"
E007 = "E007: 批量处理中断"
E008 = "E008: 内部逻辑错误"
E009 = "E009: 数据校验失败"
E010 = "E010: 未知异常"

# 网络请求配置
REQUEST_TIMEOUT = 10  # 秒
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # 秒
MAX_CONCURRENT = 5  # 批量并发数
CACHE_TTL = 3600  # 缓存有效期（秒）
REQUEST_INTERVAL = 0.5  # 请求间隔（秒）


# ------------------------------------------------------------
# 数据模型
# ------------------------------------------------------------
@dataclass
class ExtractedField:
    """提取出的字段"""
    name: str
    value: str
    confidence: str  # 高/中/低


@dataclass
class ParseResult:
    """解析结果"""
    title: str = ""
    content: str = ""
    time: str = ""
    author: str = ""
    url: str = ""
    fields: List[ExtractedField] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "title": self.title,
            "content": self.content,
            "time": self.time,
            "author": self.author,
            "url": self.url,
        }
        for f in self.fields:
            result[f.name] = {
                "value": f.value,
                "confidence": f.confidence,
            }
        return result


# ------------------------------------------------------------
# 缓存模块
# ------------------------------------------------------------
class DiskCache:
    """基于磁盘的简单缓存，使用 URL 哈希作为键"""

    def __init__(self, cache_dir: Optional[str] = None, ttl: int = CACHE_TTL):
        """初始化缓存

        Args:
            cache_dir: 缓存目录，默认使用系统临时目录
            ttl: 缓存有效期（秒）
        """
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "android-web-scraper-cache")
        self.cache_dir = cache_dir
        self.ttl = ttl
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, url: str) -> str:
        """获取缓存文件路径"""
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")

    def get(self, url: str) -> Optional[str]:
        """获取缓存内容

        Args:
            url: 请求的 URL

        Returns:
            Optional[str]: 缓存的内容，如果不存在或过期则返回 None
        """
        cache_path = self._get_cache_path(url)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # 检查过期时间
            cached_time = cache_data.get("timestamp", 0)
            if time.time() - cached_time > self.ttl:
                os.remove(cache_path)
                return None

            return cache_data.get("content")
        except (json.JSONDecodeError, KeyError, OSError):
            # 缓存损坏，删除并返回 None
            try:
                os.remove(cache_path)
            except OSError:
                pass
            return None

    def set(self, url: str, content: str) -> None:
        """设置缓存内容

        Args:
            url: 请求的 URL
            content: 要缓存的内容
        """
        cache_path = self._get_cache_path(url)
        cache_data = {
            "url": url,
            "content": content,
            "timestamp": time.time(),
        }
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)
        except OSError:
            # 缓存写入失败不影响主流程
            pass


# ------------------------------------------------------------
# 网络请求模块
# ------------------------------------------------------------
class NetworkFetcher:
    """网络请求处理器，支持重试退避、超时和缓存"""

    def __init__(self, timeout: int = REQUEST_TIMEOUT, max_retries: int = MAX_RETRIES,
                 cache: Optional[DiskCache] = None):
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache = cache if cache else DiskCache()
        self.last_request_time = 0.0

    def _rate_limit(self):
        """请求频率限制，确保请求间隔"""
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def fetch(self, url: str, use_cache: bool = True) -> str:
        """获取URL内容，带重试退避和缓存

        Args:
            url: 目标URL
            use_cache: 是否使用缓存

        Returns:
            str: 页面HTML内容

        Raises:
            RuntimeError: 请求失败
        """
        if not url:
            raise ValueError(E001)

        # 验证URL格式
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"不支持的URL协议: {parsed.scheme}")

        # 尝试从缓存获取
        if use_cache:
            cached_content = self.cache.get(url)
            if cached_content is not None:
                print(f"使用缓存: {url}")
                return cached_content

        last_error = None
        for attempt in range(self.max_retries):
            try:
                # 请求频率限制
                self._rate_limit()

                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                        "Connection": "keep-alive",
                    }
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                        raise ValueError(f"非HTML内容: {content_type}")
                    # 检测编码
                    charset = "utf-8"
                    if "charset=" in content_type:
                        charset = content_type.split("charset=")[-1].strip().strip('"').strip("'")
                    content = response.read().decode(charset, errors="replace")

                    # 写入缓存
                    if use_cache:
                        self.cache.set(url, content)

                    return content
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = RETRY_BACKOFF[attempt] if attempt < len(RETRY_BACKOFF) else RETRY_BACKOFF[-1]
                    print(f"请求失败(尝试{attempt+1}/{self.max_retries}): {e}, {wait_time}秒后重试...")
                    time.sleep(wait_time)

        # 请求失败时尝试返回缓存（降级策略）
        if use_cache:
            cached_content = self.cache.get(url)
            if cached_content is not None:
                print(f"请求失败，使用缓存降级: {url}")
                return cached_content

        raise RuntimeError(f"请求失败: {last_error}")


# ------------------------------------------------------------
# HTML 解析引擎（使用 html.parser 优先，回退到正则）
# ------------------------------------------------------------
class HtmlParser:
    """HTML 解析器 - 使用标准库 html.parser，回退到正则表达式"""

    # 常见标签正则（作为回退方案）
    TAG_PATTERN = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)([^>]*)>")
    CLOSE_TAG_PATTERN = re.compile(r"</([a-zA-Z][a-zA-Z0-9]*)>")
    COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
    SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
    STYLE_PATTERN = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)

    # 常用属性提取
    ATTR_PATTERN = re.compile(r'([a-zA-Z-]+)\s*=\s*["\']([^"\']*)["\']')

    def __init__(self, html_content: str):
        """初始化解析器

        Args:
            html_content: HTML 原始内容

        Raises:
            ValueError: 输入为空
        """
        if not html_content or not html_content.strip():
            raise ValueError(E002)
        self.raw_html = html_content
        self.clean_text = self._clean_html(html_content)

        # 使用 html.parser 构建 DOM 树
        self.dom = None
        try:
            from html.parser import HTMLParser

            class DOMBuilder(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.root = {"tag": "root", "attrs": {}, "children": [], "text": ""}
                    self.stack = [self.root]

                def handle_starttag(self, tag, attrs):
                    node = {"tag": tag, "attrs": dict(attrs), "children": [], "text": ""}
                    self.stack[-1]["children"].append(node)
                    self.stack.append(node)

                def handle_endtag(self, tag):
                    if len(self.stack) > 1:
                        self.stack.pop()

                def handle_data(self, data):
                    if data.strip():
                        self.stack[-1]["text"] += data.strip()

            builder = DOMBuilder()
            builder.feed(html_content)
            self.dom = builder.root
        except Exception:
            self.dom = None

    def _clean_html(self, html_content: str) -> str:
        """清理 HTML，去除脚本、样式、注释等"""
        text = self.COMMENT_PATTERN.sub("", html_content)
        text = self.SCRIPT_PATTERN.sub("", text)
        text = self.STYLE_PATTERN.sub("", text)
        return text

    def _find_all(self, node: Dict, tag: str) -> List[Dict]:
        """递归查找所有指定标签的节点"""
        results = []
        if node.get("tag") == tag:
            results.append(node)
        for child in node.get("children", []):
            results.extend(self._find_all(child, tag))
        return results

    def _get_text_recursive(self, node: Dict) -> str:
        """递归获取节点文本"""
        text = node.get("text", "")
        for child in node.get("children", []):
            text += " " + self._get_text_recursive(child)
        return text.strip()

    def get_text(self) -> str:
        """获取纯文本内容"""
        # 优先使用 DOM 树
        if self.dom is not None:
            try:
                text = self._get_text_recursive(self.dom)
                # 压缩空白
                lines = [line.strip() for line in text.split("\n")]
                return "\n".join([line for line in lines if line])
            except Exception:
                pass

        # 回退到正则
        text = self.clean_text
        # 替换块级标签为换行
        text = re.sub(r"<(br|p|div|li|h[1-6]|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
        # 移除剩余标签
        text = re.sub(r"<[^>]+>", "", text)
        # 反转义 HTML 实体
        text = html.unescape(text)
        # 压缩空白
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join([line for line in lines if line])
        return text

    def extract_title(self) -> str:
        """提取标题"""
        # 优先使用 DOM 树
        if self.dom is not None:
            try:
                # 尝试多种选择器
                title_nodes = self._find_all(self.dom, "title")
                if title_nodes and title_nodes[0].get("text"):
                    return title_nodes[0]["text"].strip()

                h1_nodes = self._find_all(self.dom, "h1")
                if h1_nodes and h1_nodes[0].get("text"):
                    return h1_nodes[0]["text"].strip()

                # meta og:title
                meta_nodes = self._find_all(self.dom, "meta")
                for meta in meta_nodes:
                    attrs = meta.get("attrs", {})
                    if attrs.get("property") == "og:title" and attrs.get("content"):
                        return attrs["content"].strip()
            except Exception:
                pass

        # 回退到正则
        # 优先取 <title> 标签
        title_match = re.search(r"<title[^>]*>(.*?)</title>", self.raw_html, re.DOTALL | re.IGNORECASE)
        if title_match:
            title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
            if title:
                return title

        # 其次取 <h1> 标签
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", self.raw_html, re.DOTALL | re.IGNORECASE)
        if h1_match:
            title = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()
            if title:
                return title

        # 最后取 meta og:title
        og_match = re.search(
            r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']',
            self.raw_html, re.IGNORECASE
        )
        if og_match:
            return og_match.group(1).strip()

        return ""

    def extract_links(self) -> List[Dict[str, str]]:
        """提取所有链接"""
        links = []

        # 优先使用 DOM 树
        if self.dom is not None:
            try:
                a_nodes = self._find_all(self.dom, "a")
                for a in a_nodes:
                    href = a.get("attrs", {}).get("href")
                    text = self._get_text_recursive(a)
                    if href and text:
                        links.append({"url": href.strip(), "text": text})
                return links
            except Exception:
                pass

        # 回退到正则
        for match in re.finditer(r"<a[^>]+href=[\"']([^\"']*)[\"'][^>]*>(.*?)</a>",
                                 self.raw_html, re.DOTALL | re.IGNORECASE):
            url = match.group(1).strip()
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if url and text:
                links.append({"url": url, "text": text})
        return links

    def extract_meta(self) -> Dict[str, str]:
        """提取 meta 信息"""
        metas = {}

        # 优先使用 DOM 树
        if self.dom is not None:
            try:
                meta_nodes = self._find_all(self.dom, "meta")
                for meta in meta_nodes:
                    attrs = meta.get("attrs", {})
                    name = attrs.get("name") or attrs.get("property")
                    content = attrs.get("content")
                    if name and content:
                        metas[name] = content
                return metas
            except Exception:
                pass

        # 回退到正则
        for match in re.finditer(r"<meta[^>]*>", self.raw_html, re.IGNORECASE):
            tag = match.group(0)
            attrs = dict(self.ATTR_PATTERN.findall(tag))
            if "name" in attrs and "content" in attrs:
                metas[attrs["name"]] = attrs["content"]
            elif "property" in attrs and "content" in attrs:
                metas[attrs["property"]] = attrs["content"]
        return metas

    def extract_by_pattern(self, pattern: str) -> List[str]:
        """按正则模式提取内容"""
        matches = re.findall(pattern, self.clean_text)
        return [m.strip() for m in matches if m and m.strip()]


class DataExtractor:
    """数据抽取器"""
