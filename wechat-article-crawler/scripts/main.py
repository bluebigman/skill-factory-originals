#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat-article-crawler - 微信公众号文章抓取与导出工具

功能：
- 解析微信公众号文章 URL，提取标题、作者、发布时间、正文内容
- 将正文转换为 Markdown 格式，保留标题层级、列表、引用、代码块
- 下载正文中的图片到本地，替换图片链接为本地路径（处理防盗链）
- 输出 JSON 结构化数据（含元信息、正文纯文本、Markdown 路径）
- 批量处理多个文章链接（最多 20 条/批次）

自检：
- 运行 `python scripts/main.py --selftest` 可离线执行核心逻辑自检，
  不读取外部文件、不依赖当前工作目录、不访问网络。
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError

# ---------- 错误码定义 ----------
# E001: 参数错误
# E002: URL 格式无效
# E003: 网络请求失败
# E004: HTML 解析失败
# E005: 图片下载失败
# E006: 文件写入失败
# E007: 批量数量超限
# E008: 文章内容为空
# E009: 域名不合法
# E010: 内部逻辑错误

# ---------- 常量定义 ----------
MAX_BATCH_SIZE = 20  # 每批次最大文章数
DEFAULT_TIMEOUT = 15  # 网络请求超时（秒）
WECHAT_HOSTS = ("mp.weixin.qq.com",)  # 合法公众号域名
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REFERER = "https://mp.weixin.qq.com/"


# ============================================================
# 自定义 HTML 解析器：提取正文结构化内容
# ============================================================
class ArticleHTMLParser(HTMLParser):
    """解析公众号文章 HTML，提取标题、作者、发布时间、正文结构。"""

    # 块级标签（用于 Markdown 换行）
    BLOCK_TAGS = {
        "p", "div", "section", "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li", "blockquote", "pre", "br", "hr",
    }
    # 标题标签
    HEADING_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.author = ""
        self.publish_time = ""
        self.blocks = []          # 结构化块列表
        self.current_block = None  # 当前正在构建的块
        self.in_body = False       # 是否在正文区域
        self.in_script = False
        self.in_style = False
        self.body_depth = 0
        self._in_title = False
        self._in_author = False
        self._in_time = False
        self._in_pre = False
        self._link_href = ""       # 当前链接的 href
        self._img_src = ""         # 当前图片的 src
        self._img_alt = ""
        self._list_type = None     # 当前列表类型（ul/ol）
        self._list_stack = []      # 列表嵌套栈

    def _start_block(self, tag):
        """开始一个新的块，结束当前块。"""
        self._end_block()
        self.current_block = {"type": "text", "content": [], "tag": tag}
        if tag in self.HEADING_TAGS:
            self.current_block["type"] = "heading"
            self.current_block["level"] = tag
        elif tag == "blockquote":
            self.current_block["type"] = "quote"
        elif tag == "pre":
            self.current_block["type"] = "code"
            self._in_pre = True
        elif tag in ("ul", "ol"):
            self.current_block["type"] = "list"
            self.current_block["list_type"] = tag
            self.current_block["items"] = []
            self._list_stack.append(tag)
        elif tag == "li":
            # 列表项：追加到父列表块
            self._end_block()
            self.current_block = {"type": "list_item", "content": []}
        elif tag == "img":
            self.current_block = {"type": "image", "src": "", "alt": ""}
        elif tag == "hr":
            self.current_block = {"type": "hr"}

    def _end_block(self):
        """结束当前块，将其加入 blocks 列表。"""
        if self.current_block is None:
            return
        block = self.current_block
        # 清理空文本块
        if block["type"] == "text" and not block["content"]:
            self.current_block = None
            return
        # 清理空列表
        if block["type"] == "list" and not block.get("items"):
            self.current_block = None
            return
        # 清理空列表项
        if block["type"] == "list_item" and not block["content"]:
            self.current_block = None
            return
        self.blocks.append(block)
        self.current_block = None

    def handle_starttag(self, tag, attrs):
        """处理开始标签。"""
        attrs_dict = dict(attrs)

        # 进入正文区域判断
        if tag == "div" and "rich_media_content" in attrs_dict.get("class", ""):
            self.in_body = True
            self.body_depth = 1
            return
        if self.in_body and tag == "div":
            self.body_depth += 1

        # 跳过 script/style
        if tag == "script":
            self._in_script = True
            return
        if tag == "style":
            self._in_style = True
            return

        # 提取标题
        if tag == "h1" and "rich_media_title" in attrs_dict.get("class", ""):
            self._in_title = True
            return
        # 提取作者
        if tag == "a" and "rich_media_meta_nickname" in attrs_dict.get("class", ""):
            self._in_author = True
            return
        # 提取发布时间
        if tag == "em" and "rich_media_meta_text" in attrs_dict.get("class", ""):
            self._in_time = True
            return

        # 记录链接和图片
        if tag == "a":
            self._link_href = attrs_dict.get("href", "")
        if tag == "img":
            self._img_src = attrs_dict.get("data-src", attrs_dict.get("src", ""))
            self._img_alt = attrs_dict.get("alt", "")

        # 正文内的块级标签处理
        if self.in_body and not self._in_script and not self._in_style:
            if tag in self.BLOCK_TAGS:
                self._start_block(tag)

    def handle_endtag(self, tag):
        """处理结束标签。"""
        if tag == "script":
            self._in_script = False
            return
        if tag == "style":
            self._in_style = False
            return

        if tag == "div" and self.in_body:
            self.body_depth -= 1
            if self.body_depth <= 0:
                self.in_body = False
                self._end_block()
            return

        if tag == "h1" and self._in_title:
            self._in_title = False
            return
        if tag == "a" and self._in_author:
            self._in_author = False
            return
        if tag == "em" and self._in_time:
            self._in_time = False
            return

        if tag == "pre":
            self._in_pre = False

        # 结束块级标签
        if self.in_body and tag in self.BLOCK_TAGS:
            if tag == "li":
                # 将列表项加入父列表
                self._end_block()
                if self.blocks and self.blocks[-1]["type"] == "list":
                    # 将刚结束的列表项内容加入列表
                    pass
            else:
                self._end_block()
            # 处理列表结束
            if tag in ("ul", "ol") and self._list_stack:
                self._list_stack.pop()

    def handle_data(self, data):
        """处理文本数据。"""
        # 提取标题文本
        if self._in_title:
            self.title += data.strip()
            return
        # 提取作者
        if self._in_author:
            self.author += data.strip()
            return
        # 提取发布时间
        if self._in_time:
            self.publish_time += data.strip()
            return

        # 跳过 script/style 内容
        if self._in_script or self._in_style:
            return

        # 正文内容处理
        if not self.in_body:
            return

        text = data.strip()
        if not text:
            return

        if self.current_block is None:
            # 没有块时，创建文本块
            self.current_block = {"type": "text", "content": [], "tag": "p"}
            self.current_block["content"].append(text)
        elif self.current_block["type"] == "text":
            self.current_block["content"].append(text)
        elif self.current_block["type"] == "heading":
            self.current_block["content"].append(text)
        elif self.current_block["type"] == "quote":
            self.current_block["content"].append(text)
        elif self.current_block["type"] == "code":
            self.current_block.setdefault("content", []).append(text)
        elif self.current_block["type"] == "list_item":
            self.current_block["content"].append(text)
        elif self.current_block["type"] == "image":
            pass  # 图片不需要文本

    def handle_startendtag(self, tag, attrs):
        """处理自闭合标签（如 img, br, hr）。"""
        attrs_dict = dict(attrs)
        if tag == "img" and self.in_body:
            self._end_block()
            self.current_block = {
                "type": "image",
                "src": attrs_dict.get("data-src", attrs_dict.get("src", "")),
                "alt": attrs_dict.get("alt", ""),
            }
            self._end_block()
        elif tag == "br" and self.in_body:
            self._end_block()
            self.current_block = {"type": "text", "content": ["\n"], "tag": "br"}
            self._end_block()
        elif tag == "hr" and self.in_body:
            self._end_block()
            self.current_block = {"type": "hr"}
            self._end_block()

    def get_structured_data(self):
        """获取解析后的结构化数据。"""
        self._end_block()
        return {
            "title": self.title.strip(),
            "author": self.author.strip(),
            "publish_time": self.publish_time.strip(),
            "blocks": self.blocks,
        }


# ============================================================
# 核心功能模块
# ============================================================
class WechatArticleCrawler:
    """微信公众号文章抓取与导出主类。"""

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.images_dir = "images"  # 图片保存目录名

    # ---------- URL 校验 ----------
    def validate_url(self, url):
        """校验 URL 是否为合法的微信公众号文章链接。
        
        返回: (is_valid, error_msg)
        """
        if not url or not isinstance(url, str):
            return False, "URL 不能为空"
        if len(url) > 2048:
            return False, "URL 过长"
        try:
            parsed = urlparse(url)
        except Exception:
            return False, "URL 解析失败"
        if parsed.scheme not in ("http", "https"):
            return False, "仅支持 http/https 协议"
        if parsed.netloc not in WECHAT_HOSTS:
            return False, f"非微信公众号域名: {parsed.netloc}"
        if not parsed.path:
            return False, "URL 缺少路径"
        return True, ""

    # ---------- 网络请求 ----------
    def fetch_html(self, url):
        """获取文章 HTML 内容。
        
        返回: (html_content, error_code)
        """
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": REFERER,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                # 检查状态码
                if resp.status != 200:
                    return None, "E003"
                # 读取内容并尝试解码
                raw_data = resp.read()
                # 先尝试 UTF-8
                try:
                    html = raw_data.decode("utf-8")
                except UnicodeDecodeError:
                    # 回退到 GBK
                    try:
                        html = raw_data.decode("gbk")
                    except UnicodeDecodeError:
                        return None, "E003"
                return html, ""
        except URLError:
            return None, "E003"
        except Exception:
            return None, "E003"

    # ---------- 解析 ----------
    def parse_html(self, html):
        """解析 HTML，提取结构化数据。
        
        返回: (structured_data, error_code)
        """
        if not html or not html.strip():
            return None, "E004"
        try:
            parser = ArticleHTMLParser()
            parser.feed(html)
            parser.close()
            data = parser.get_structured_data()
            if not data["title"] and not data["blocks"]:
                return None, "E008"
            return data, ""
        except Exception:
            return None, "E004"

    # ---------- 图片处理 ----------
    def _download_image(self, img_url, save_dir, index):
        """下载单张图片，返回本地路径。
        
        返回: (local_path, error_code)
        """
        if not img_url:
            return "", "E005"
        try:
            # 构造请求头（带 Referer 绕过防盗链）
            headers = {
                "User-Agent": USER_AGENT,
                "Referer": REFERER,
            }
            req = Request(img_url, headers=headers)
            with urlopen(req, timeout=self.timeout) as resp:
                img_data = resp.read()
                # 从 URL 提取扩展名
                ext = os.path.splitext(urlparse(img_url).path)[1]
                if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
                    ext = ".jpg"  # 默认扩展名
                # 生成文件名
                filename = f"img_{index}{ext}"
                filepath = os.path.join(save_dir, filename)
                # 写入文件
                with open(filepath, "wb") as f:
                    f.write(img_data)
                return filepath, ""
        except Exception:
            return "", "E005"

    def process_images(self, blocks, save_dir):
        """处理正文中的图片，下载到本地并替换链接。
        
        返回: (处理后的 blocks, 图片数量, 错误列表)
        """
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except OSError:
                return blocks, 0, ["E006"]

        img_count = 0
        errors = []
        for i, block in enumerate(blocks):
            if block.get("type") == "image" and block.get("src"):
                local_path, err = self._download_image(block["src"], save_dir, i)
                if err:
                    errors.append(f"图片下载失败: {block['src'][:50]}...")
                else:
                    block["local_path"] = local_path
                    img_count += 1
        return blocks, img_count, errors

    # ---------- Markdown 转换 ----------
    def _get_heading_prefix(self, level):
        """根据标题级别生成 Markdown 前缀。"""
        mapping = {
            "h1": "#",
            "h2": "##",
            "h3": "###",
            "h4": "####",
            "h5": "#####",
            "h6": "######",
        }
        return mapping.get(level, "##")

    def blocks_to_markdown(self, blocks):
        """将结构化块转换为 Markdown 文本。"""
        md_lines = []
        for block in blocks:
            btype = block.get("type", "text")
            if btype == "heading":
                level = block.get("level", "h2")
                prefix = self._get_heading_prefix(level)
                content = " ".join(block.get("content", []))
                md_lines.append(f"{prefix} {content}")
                md_lines.append("")  # 标题后空行
            elif btype == "quote":
                content = " ".join(block.get("content", []))
                md_lines.append(f"> {content}")
                md_lines.append("")
            elif btype == "code":
                content = "\n".join(block.get("content", []))
                md_lines.append("
