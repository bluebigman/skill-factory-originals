#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-website-cloner-template 独立实现脚本

功能：将网站 URL、HTML 文件或纯文本内容转换为结构化克隆模板（Markdown 格式）。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

用法示例：
    python scripts/main.py --url https://example.com
    python scripts/main.py --file ./page.html
    python scripts/main.py --text "<html>...</html>"
    python scripts/main.py --selftest
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 错误码定义
# E001: 输入源无效或为空
# E002: 文件不存在或无法读取
# E003: URL 格式非法
# E004: 网络请求失败（本脚本不实际发起请求，仅保留错误码定义）
# E005: HTML 解析失败
# E006: 模板生成失败
# E007: 参数冲突（同时指定了多个输入源）
# E008: 输出目录不可写
# E009: 内部逻辑错误（断言失败等）
# E010: 未知错误

# 版本信息
VERSION = "1.0.1"
SLUG = "ai-website-cloner-template"
DISPLAY_NAME = "网站克隆 模板生成 一键复制"


@dataclass
class PageStructure:
    """页面结构数据类"""
    title: str = ""
    meta_description: str = ""
    headings: List[Dict[str, str]] = field(default_factory=list)
    nav_links: List[Dict[str, str]] = field(default_factory=list)
    main_content: str = ""
    footer_text: str = ""
    forms: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    raw_text: str = ""
    source_type: str = "unknown"  # url, file, text


class HTMLParser:
    """轻量级 HTML 解析器（仅解析静态 HTML，不执行 JS）"""

    # 常见标签正则
    TAG_PATTERN = re.compile(r"<(\w+)([^>]*)>([\s\S]*?)</\1>", re.IGNORECASE)
    SELF_CLOSING_TAG_PATTERN = re.compile(r"<(\w+)([^>]*?)/?>", re.IGNORECASE)
    COMMENT_PATTERN = re.compile(r"<!--[\s\S]*?-->")
    SCRIPT_STYLE_PATTERN = re.compile(r"<(script|style)[^>]*>[\s\S]*?</\1>", re.IGNORECASE)

    @classmethod
    def clean_html(cls, html: str) -> str:
        """移除注释、脚本和样式"""
        html = cls.COMMENT_PATTERN.sub("", html)
        html = cls.SCRIPT_STYLE_PATTERN.sub("", html)
        return html

    @classmethod
    def extract_title(cls, html: str) -> str:
        """提取页面标题"""
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # 回退：提取第一个 h1
        match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @classmethod
    def extract_meta_description(cls, html: str) -> str:
        """提取 meta description"""
        match = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        # 尝试反向属性顺序
        match = re.search(
            r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']',
            html,
            re.IGNORECASE,
        )
        return match.group(1).strip() if match else ""

    @classmethod
    def extract_headings(cls, html: str) -> List[Dict[str, str]]:
        """提取标题结构 (h1-h6)"""
        headings = []
        for level in range(1, 7):
            pattern = re.compile(
                rf"<h{level}[^>]*>([\s\S]*?)</h{level}>", re.IGNORECASE
            )
            for match in pattern.finditer(html):
                text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
                if text:
                    headings.append({"level": f"h{level}", "text": text})
        return headings

    @classmethod
    def extract_links(cls, html: str, base_url: str = "") -> List[Dict[str, str]]:
        """提取所有链接"""
        links = []
        anchor_pattern = re.compile(
            r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>([\s\S]*?)</a>', re.IGNORECASE
        )
        for match in anchor_pattern.finditer(html):
            href = match.group(1).strip()
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                links.append({"href": href, "text": text or href})
        return links

    @classmethod
    def extract_nav_links(cls, html: str, base_url: str = "") -> List[Dict[str, str]]:
        """提取导航链接（nav 标签内的链接）"""
        nav_pattern = re.compile(r"<nav[^>]*>([\s\S]*?)</nav>", re.IGNORECASE)
        nav_match = nav_pattern.search(html)
        if nav_match:
            return cls.extract_links(nav_match.group(1), base_url)
        return []

    @classmethod
    def extract_main_content(cls, html: str) -> str:
        """提取主内容区文本"""
        # 优先提取 main 标签
        main_pattern = re.compile(r"<main[^>]*>([\s\S]*?)</main>", re.IGNORECASE)
        match = main_pattern.search(html)
        if match:
            content = match.group(1)
        else:
            # 回退：提取 body 中的内容
            body_pattern = re.compile(r"<body[^>]*>([\s\S]*?)</body>", re.IGNORECASE)
            match = body_pattern.search(html)
            content = match.group(1) if match else html

        # 清理标签，保留文本
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:2000]  # 限制长度

    @classmethod
    def extract_footer(cls, html: str) -> str:
        """提取页脚文本"""
        footer_pattern = re.compile(r"<footer[^>]*>([\s\S]*?)</footer>", re.IGNORECASE)
        match = footer_pattern.search(html)
        if match:
            text = re.sub(r"<[^>]+>", " ", match.group(1))
            return re.sub(r"\s+", " ", text).strip()
        return ""

    @classmethod
    def extract_forms(cls, html: str) -> List[Dict[str, Any]]:
        """提取表单信息"""
        forms = []
        form_pattern = re.compile(r"<form[^>]*>([\s\S]*?)</form>", re.IGNORECASE)
        for form_match in form_pattern.finditer(html):
            form_html = form_match.group(1)
            form_info: Dict[str, Any] = {"action": "", "method": "GET", "fields": []}

            # 提取 form 属性
            attrs = re.search(r'<form[^>]*action=["\']([^"\']*)["\']', form_match.group(0), re.IGNORECASE)
            if attrs:
                form_info["action"] = attrs.group(1)
            attrs = re.search(r'<form[^>]*method=["\']([^"\']*)["\']', form_match.group(0), re.IGNORECASE)
            if attrs:
                form_info["method"] = attrs.group(1).upper()

            # 提取输入字段
            input_pattern = re.compile(
                r'<input[^>]*type=["\']([^"\']*)["\'][^>]*name=["\']([^"\']*)["\']',
                re.IGNORECASE,
            )
            for input_match in input_pattern.finditer(form_html):
                form_info["fields"].append(
                    {"type": input_match.group(1), "name": input_match.group(2)}
                )

            forms.append(form_info)
        return forms

    @classmethod
    def extract_images(cls, html: str) -> List[Dict[str, str]]:
        """提取图片信息"""
        images = []
        img_pattern = re.compile(
            r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\']',
            re.IGNORECASE,
        )
        for match in img_pattern.finditer(html):
            images.append({"src": match.group(1), "alt": match.group(2)})
        return images


class TemplateGenerator:
    """模板生成器"""

    @staticmethod
    def generate_markdown(structure: PageStructure) -> str:
        """生成 Markdown 格式的克隆模板"""
        try:
            lines = []
            lines.append(f"# 网站克隆模板: {structure.title or '未命名页面'}")
            lines.append("")
            lines.append(f"> 技能: {DISPLAY_NAME} (v{VERSION})")
            lines.append(f"> 来源类型: {structure.source_type}")
            lines.append("")

            # 基本信息
            lines.append("## 页面基本信息")
            lines.append("")
            lines.append(f"- **标题**: {structure.title or '[需核实:标题]'}")
            lines.append(
                f"- **描述**: {structure.meta_description or '[需核实:描述]'}"
            )
            lines.append("")
            lines.append("置信度: 中 (0.7)")
            lines.append("")

            # 页面结构树
            lines.append("## 页面结构树")
            lines.append("")
            lines.append("
