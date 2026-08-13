#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 微信文章转 Markdown 内容萃取工具

本脚本根据功能规格独立实现，仅依赖 Python 标准库。
支持从微信公众号文章 HTML 中提取标题、作者、正文并转换为 Markdown。
提供 --selftest 参数进行离线自检。
"""

import argparse
import html
import re
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

# 错误码定义
ERR_OK = 0
ERR_INVALID_URL = "E001"       # URL 格式无效或非微信域名
ERR_FETCH_FAILED = "E002"      # 网络请求失败
ERR_PARSE_FAILED = "E003"      # HTML 解析失败
ERR_NO_CONTENT = "E004"        # 未找到正文内容
ERR_NO_TITLE = "E005"          # 未找到标题
ERR_NO_AUTHOR = "E006"         # 未找到作者
ERR_IMAGE_PROCESS = "E007"     # 图片处理失败
ERR_OUTPUT_FAILED = "E008"     # 输出写入失败
ERR_INVALID_INPUT = "E009"     # 输入参数无效
ERR_UNKNOWN = "E010"           # 未知错误


class WeChatArticleParser:
    """微信公众号文章 HTML 解析器，提取结构化内容并转换为 Markdown。"""

    # 微信文章域名白名单
    WECHAT_DOMAINS = ("mp.weixin.qq.com",)

    def __init__(self, html_content: str, base_url: str = ""):
        """
        初始化解析器。

        Args:
            html_content: 文章页面的 HTML 源码
            base_url: 基础 URL，用于拼接相对路径的图片链接
        """
        self.html_content = html_content
        self.base_url = base_url
        self.parsed_data: Dict = {}

    def _normalize_url(self, url: str) -> str:
        """规范化 URL，将相对路径转为绝对路径。"""
        if not url:
            return ""
        if url.startswith("//"):
            # 协议相对 URL
            return "https:" + url
        if url.startswith(("http://", "https://")):
            return url
        # 相对路径，使用 base_url 拼接
        return urljoin(self.base_url, url)

    def _clean_text(self, text: str) -> str:
        """清理文本，去除多余空白和 HTML 标签。"""
        if not text:
            return ""
        # 去除 HTML 标签
        text = re.sub(r"<[^>]+>", "", text)
        # 解码 HTML 实体
        text = html.unescape(text)
        # 合并空白字符
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def extract_title(self) -> str:
        """
        提取文章标题。

        优先从 og:title meta 标签获取，其次从 h1 标签获取。

        Returns:
            文章标题字符串
        """
        # 尝试 og:title
        match = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            self.html_content,
            re.IGNORECASE,
        )
        if match:
            return self._clean_text(match.group(1))

        # 尝试 h1 标签
        match = re.search(r"<h1[^>]*>(.*?)</h1>", self.html_content, re.IGNORECASE | re.DOTALL)
        if match:
            return self._clean_text(match.group(1))

        # 尝试 title 标签
        match = re.search(r"<title[^>]*>(.*?)</title>", self.html_content, re.IGNORECASE | re.DOTALL)
        if match:
            return self._clean_text(match.group(1))

        return ""

    def extract_author(self) -> str:
        """
        提取文章作者。

        优先从 meta 标签获取，其次从页面特定区域获取。

        Returns:
            作者名字符串
        """
        # 尝试 meta author
        match = re.search(
            r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)["\']',
            self.html_content,
            re.IGNORECASE,
        )
        if match:
            return self._clean_text(match.group(1))

        # 尝试 og:article:author
        match = re.search(
            r'<meta[^>]+property=["\']og:article:author["\'][^>]+content=["\']([^"\']+)["\']',
            self.html_content,
            re.IGNORECASE,
        )
        if match:
            return self._clean_text(match.group(1))

        # 尝试常见公众号作者区域（id 或 class 包含 author）
        match = re.search(
            r'<(?:div|span|p)[^>]*(?:id|class)=["\'][^"\']*author[^"\']*["\'][^>]*>(.*?)</(?:div|span|p)>',
            self.html_content,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return self._clean_text(match.group(1))

        return ""

    def _extract_images_from_block(self, block_html: str) -> List[str]:
        """从 HTML 块中提取图片 URL 列表。"""
        images = []
        for img_match in re.finditer(r"<img[^>]+src=[\"\']([^\"\']+)[\"\']", block_html, re.IGNORECASE):
            img_url = self._normalize_url(img_match.group(1))
            if img_url:
                images.append(img_url)
        return images

    def _convert_block_to_markdown(self, block_html: str) -> Tuple[str, List[str]]:
        """
        将单个 HTML 块转换为 Markdown。

        Returns:
            (markdown文本, 图片URL列表)
        """
        markdown_lines = []
        images = []

        block = block_html.strip()
        if not block:
            return "", []

        # 提取块内图片
        images = self._extract_images_from_block(block)

        # 处理标题标签
        for level in range(1, 7):
            # 简化处理：将 h1-h6 转为对应 Markdown 标题
            pattern = re.compile(
                rf"<h{level}[^>]*>(.*?)</h{level}>",
                re.IGNORECASE | re.DOTALL,
            )
            for match in pattern.finditer(block):
                text = self._clean_text(match.group(1))
                if text:
                    markdown_lines.append(f"{'#' * level} {text}")

        # 处理段落
        for match in re.finditer(r"<p[^>]*>(.*?)</p>", block, re.IGNORECASE | re.DOTALL):
            text = self._clean_text(match.group(1))
            if text:
                # 处理加粗和斜体
                text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.IGNORECASE)
                text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.IGNORECASE)
                text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.IGNORECASE)
                text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.IGNORECASE)
                # 处理行内链接
                text = re.sub(
                    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                    r"[\2](\1)",
                    text,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                markdown_lines.append(text)

        # 处理列表（简化）
        for match in re.finditer(r"<li[^>]*>(.*?)</li>", block, re.IGNORECASE | re.DOTALL):
            text = self._clean_text(match.group(1))
            if text:
                markdown_lines.append(f"- {text}")

        # 处理代码块
        for match in re.finditer(
            r"<pre[^>]*>(?:<code[^>]*>)?(.*?)(?:</code>)?</pre>",
            block,
            re.IGNORECASE | re.DOTALL,
        ):
            code = self._clean_text(match.group(1))
            if code:
                markdown_lines.append("")
                markdown_lines.append("
