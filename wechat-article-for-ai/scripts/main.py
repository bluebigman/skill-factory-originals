#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat-article-for-ai - 公众号文章转Markdown内容提取工具
版本: 1.0.1
"""

import argparse
import html
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：输入URL格式无效",
    "E002": "参数错误：无法解析命令行参数",
    "E003": "网络错误：请求目标URL失败",
    "E004": "解析错误：无法从HTML中提取文章内容",
    "E005": "图片错误：图片下载失败",
    "E006": "文件错误：输出目录创建失败",
    "E007": "文件错误：写入文件失败",
    "E008": "运行时错误：未预期的异常",
    "E009": "参数错误：--selftest与--version不能同时使用",
    "E010": "参数错误：未提供有效的URL或操作标志",
}


# ============================================================
# 数据结构
# ============================================================
@dataclass
class Article:
    """文章数据模型"""
    url: str
    title: str = ""
    author: str = ""
    publish_time: str = ""
    content_html: str = ""
    content_markdown: str = ""
    images: List[str] = field(default_factory=list)


# ============================================================
# 核心工具函数
# ============================================================
def validate_url(url: str) -> bool:
    """验证是否为有效的微信公众号文章URL"""
    pattern = r"^https?://mp\.weixin\.qq\.com/s/[\w-]+"
    return bool(re.match(pattern, url.strip()))


def extract_meta(html_content: str) -> Tuple[str, str, str]:
    """
    从HTML中提取标题、作者、发布时间
    返回: (标题, 作者, 发布时间)
    """
    title = ""
    author = ""
    publish_time = ""

    # 提取标题
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL)
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
    if not title:
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()

    # 提取作者
    author_match = re.search(r'var\s+(?:author|nickname)\s*=\s*["\']([^"\']+)["\']', html_content)
    if author_match:
        author = author_match.group(1).strip()

    # 提取发布时间
    time_match = re.search(r'var\s+publish_time\s*=\s*["\']([^"\']+)["\']', html_content)
    if time_match:
        publish_time = time_match.group(1).strip()

    return title, author, publish_time


def extract_content_html(html_content: str) -> str:
    """
    从HTML中提取正文内容
    去除脚本、样式、隐藏元素
    """
    # 定位正文区域
    content_match = re.search(r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>', html_content, re.DOTALL)
    if not content_match:
        content_match = re.search(r'<div[^>]*class=["\'][^"\']*rich_media_content[^"\']*["\'][^>]*>(.*?)</div>', html_content, re.DOTALL)
    if not content_match:
        return ""

    content = content_match.group(1)

    # 移除脚本和样式
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)

    # 移除隐藏元素
    content = re.sub(r'<[^>]+style=["\'][^"\']*display:\s*none[^"\']*["\'][^>]*>.*?</[^>]+>', '', content, flags=re.DOTALL)

    return content.strip()


def html_to_markdown(html_content: str, image_paths: Optional[Dict[str, str]] = None) -> str:
    """
    将HTML正文转换为Markdown格式
    """
    if not html_content:
        return ""

    md_content = html_content

    # 处理图片（先处理，避免被其他规则干扰）
    def replace_img(match):
        img_tag = match.group(0)
        src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag)

        src = src_match.group(1) if src_match else ""
        alt = alt_match.group(1) if alt_match else "图片"

        # 如果提供了图片路径映射，使用本地路径
        if image_paths and src in image_paths:
            src = image_paths[src]

        return f"![{alt}]({src})"

    md_content = re.sub(r'<img[^>]+>', replace_img, md_content)

    # 处理代码块
    def replace_code_block(match):
        code_content = match.group(1)
        # 去除HTML标签，保留文本内容
        code_text = re.sub(r'<[^>]+>', '', code_content)
        # 反转义HTML实体
        code_text = html.unescape(code_text)
        return "\n
