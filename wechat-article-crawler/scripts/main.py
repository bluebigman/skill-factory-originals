#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

微信公众号文章抓取与导出 —— 独立实现（clean-room）
依据功能规格独立编写，未参考任何既有代码。

功能概要：
    1. 解析公众号文章 URL，提取标题、作者、发布时间、正文内容
    2. 将正文转换为 Markdown 格式，保留标题层级、列表、引用、代码块
    3. 下载正文中的图片到本地，替换图片链接为本地路径（绕过防盗链）
    4. 输出 JSON 结构化数据（含元信息、正文纯文本、Markdown 路径）
    5. 批量处理多个文章链接（最多 20 条/批次）

用法示例：
    python scripts/main.py https://mp.weixin.qq.com/s/xxx -o output_dir
    python scripts/main.py --selftest

错误码：
    E001 参数错误
    E002 URL 格式无效
    E003 网络请求失败
    E004 页面解析失败
    E005 图片下载失败
    E006 文件写入失败
    E007 批量数量超限
    E008 输入为空
    E009 内部逻辑错误
    E010 输出目录创建失败
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
MAX_BATCH_SIZE = 20          # 每批次最多处理的文章数
DEFAULT_TIMEOUT = 15         # 网络请求超时（秒）
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REFERER_HEADER = "https://mp.weixin.qq.com/"


# ---------------------------------------------------------------------------
# 错误处理辅助
# ---------------------------------------------------------------------------
class SkillError(Exception):
    """技能统一异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def fail(code: str, message: str) -> None:
    """抛出带错误码的异常。"""
    raise SkillError(code, message)


# ---------------------------------------------------------------------------
# HTML 解析器（基于标准库 html.parser）
# ---------------------------------------------------------------------------
class ArticleHTMLParser(HTMLParser):
    """
    解析公众号文章 HTML，提取：
      - 标题（<h1 class="rich_media_title"> 或 <title>）
      - 作者（<a id="js_name"> 或 meta 标签）
      - 发布时间（<em id="publish_time"> 或 meta 标签）
      - 正文 HTML（<div id="js_content">）
      - 正文中的图片链接（<img> 的 data-src 或 src）
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: Optional[str] = None
        self.author: Optional[str] = None
        self.publish_time: Optional[str] = None
        self.content_html_parts: List[str] = []
        self.image_urls: List[str] = []

        # 内部状态
        self._in_title_tag = False
        self._in_author_tag = False
        self._in_time_tag = False
        self._in_content_div = False
        self._content_depth = 0
        self._current_tag = ""
        self._current_attrs: Dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        # 标题
        if tag == "h1" and "rich_media_title" in attr_dict.get("class", ""):
            self._in_title_tag = True
            self._current_tag = "title"
        elif tag == "title" and self.title is None:
            self._in_title_tag = True
            self._current_tag = "title"

        # 作者
        if tag == "a" and attr_dict.get("id") == "js_name":
            self._in_author_tag = True
            self._current_tag = "author"

        # 发布时间
        if tag == "em" and attr_dict.get("id") == "publish_time":
            self._in_time_tag = True
            self._current_tag = "time"

        # 正文区域
        if tag == "div" and attr_dict.get("id") == "js_content":
            self._in_content_div = True
            self._content_depth = 1
            self._current_tag = "content"
            self.content_html_parts.append("<div>")
            return

        # 在正文内记录标签
        if self._in_content_div:
            self._content_depth += 1
            self.content_html_parts.append(self._build_tag(tag, attrs, closing=False))

        # 图片收集（在正文内）
        if self._in_content_div and tag == "img":
            src = attr_dict.get("data-src") or attr_dict.get("src") or ""
            if src:
                self.image_urls.append(src)

    def handle_endtag(self, tag: str) -> None:
        if self._in_content_div:
            self._content_depth -= 1
            self.content_html_parts.append(f"</{tag}>")
            if self._content_depth <= 0:
                self._in_content_div = False
                self._content_depth = 0
                self.content_html_parts.append("</div>")

        if tag == "h1" and self._in_title_tag:
            self._in_title_tag = False
        elif tag == "title" and self._in_title_tag:
            self._in_title_tag = False
        elif tag == "a" and self._in_author_tag:
            self._in_author_tag = False
        elif tag == "em" and self._in_time_tag:
            self._in_time_tag = False

    def handle_data(self, data: str) -> None:
        # 标题文本
        if self._in_title_tag and self._current_tag == "title":
            text = data.strip()
            if text and self.title is None:
                self.title = text

        # 作者文本
        if self._in_author_tag and self._current_tag == "author":
            text = data.strip()
            if text:
                self.author = text

        # 发布时间文本
        if self._in_time_tag and self._current_tag == "time":
            text = data.strip()
            if text:
                self.publish_time = text

        # 正文内容
        if self._in_content_div:
            self.content_html_parts.append(data)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        # 自闭合标签（如 <img/>、<br/>）
        if self._in_content_div:
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            self.content_html_parts.append(self._build_tag(tag, attrs, closing=True))
            if tag == "img":
                src = attr_dict.get("data-src") or attr_dict.get("src") or ""
                if src:
                    self.image_urls.append(src)

    @staticmethod
    def _build_tag(tag: str, attrs: List[Tuple[str, Optional[str]]], closing: bool = False) -> str:
        """将标签及属性序列化为字符串。"""
        attr_str = ""
        for k, v in attrs:
            if v is None:
                attr_str += f' {k}=""'
            else:
                # 简单转义引号
                safe_v = v.replace('"', '&quot;')
                attr_str += f' {k}="{safe_v}"'
        if closing:
            return f"<{tag}{attr_str}/>"
        return f"<{tag}{attr_str}>"

    def get_content_html(self) -> str:
        """返回正文 HTML 字符串。"""
        return "".join(self.content_html_parts)


# ---------------------------------------------------------------------------
# HTML 转 Markdown 转换器
# ---------------------------------------------------------------------------
class HTMLToMarkdown:
    """
    将 HTML 片段转换为 Markdown。
    支持：标题(h1-h6)、段落、粗体、斜体、链接、图片、列表(ul/ol/li)、引用、代码块。
    """

    # 块级标签（转换后需要换行）
    BLOCK_TAGS = {
        "p", "div", "section", "blockquote", "pre", "ul", "ol",
        "h1", "h2", "h3", "h4", "h5", "h6", "hr", "table",
    }

    def __init__(self, image_map: Optional[Dict[str, str]] = None):
        """
        :param image_map: 原始图片 URL -> 本地路径 的映射，用于替换图片链接
        """
        self.image_map = image_map or {}

    def convert(self, html: str) -> str:
        """将 HTML 字符串转换为 Markdown。"""
        # 使用标准库 HTMLParser 逐标签处理
        converter = _MDConverter(self.image_map)
        converter.feed(html)
        return converter.get_markdown()


class _MDConverter(HTMLParser):
    """内部转换器，基于 HTMLParser 实现状态机。"""

    def __init__(self, image_map: Dict[str, str]):
        super().__init__(convert_charrefs=True)
        self.image_map = image_map
        self._lines: List[str] = []
        self._current_line = ""
        self._list_stack: List[str] = []      # 列表类型栈：ul / ol
        self._list_index: List[int] = []      # 有序列表计数
        self._in_pre = False
        self._pre_content: List[str] = []
        self._in_blockquote = False
        self._link_href: Optional[str] = None
        self._skip_newline = False

    def get_markdown(self) -> str:
        # 处理剩余行
        if self._current_line.strip():
            self._lines.append(self._current_line.rstrip())
        # 合并空白行（最多连续一个空行）
        result_lines: List[str] = []
        blank_count = 0
        for line in self._lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 1:
                    result_lines.append("")
            else:
                blank_count = 0
                result_lines.append(line)
        return "\n".join(result_lines).strip() + "\n"

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        # 代码块
        if tag == "pre":
            self._in_pre = True
            self._pre_content = []
            return
        if tag == "code" and self._in_pre:
            return  # 忽略 code 标签本身

        # 引用
        if tag == "blockquote":
            self._in_blockquote = True
            self._flush_line()
            return

        # 标题
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush_line()
            level = int(tag[1])
            self._current_line += "#" * level + " "
            return

        # 列表
        if tag == "ul":
            self._list_stack.append("ul")
            self._flush_line()
            return
        if tag == "ol":
            self._list_stack.append("ol")
            self._list_index.append(1)
            self._flush_line()
            return
        if tag == "li":
            self._flush_line()
            if self._list_stack:
                list_type = self._list_stack[-1]
                if list_type == "ul":
                    prefix = "- "
                else:
                    idx = self._list_index[-1]
                    prefix = f"{idx}. "
                    self._list_index[-1] = idx + 1
                indent = "  " * (len(self._list_stack) - 1)
                self._current_line += indent + prefix
            return

        # 分隔线
        if tag == "hr":
            self._flush_line()
            self._lines.append("---")
            return

        # 图片
        if tag == "img":
            src = attr_dict.get("data-src") or attr_dict.get("src") or ""
            alt = attr_dict.get("alt", "")
            local_path = self.image_map.get(src, src)
            self._current_line += f"![{alt}]({local_path})"
            return

        # 链接
        if tag == "a":
            href = attr_dict.get("href", "")
            self._current_line += "["
            self._link_href = href
            return

        # 行内样式
        if tag in ("strong", "b"):
            self._current_line += "**"
            return
        if tag in ("em", "i"):
            self._current_line += "*"
            return
        if tag == "br":
            self._flush_line()
            return

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre":
            self._in_pre = False
            code_text = "".join(self._pre_content).strip()
            self._flush_line()
            self._lines.append("
