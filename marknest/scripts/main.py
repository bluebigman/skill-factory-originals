#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
marknest — 文档结构化转换 Skill 独立实现脚本

本脚本依据《marknest 功能规格》独立设计（clean-room），
实现核心逻辑：文档/链接 → 规范化、可复用的结构化输出。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python scripts/main.py --selftest              # 离线自检
    python scripts/main.py --input sample.md       # 转换本地文件
    python scripts/main.py --url https://example.com  # 转换链接(需网络)
    python scripts/main.py --text "Hello World"    # 直接转换文本
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time
from datetime import datetime, timezone
from html.parser import HTMLParser

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
_base_timeout = 10  # 基础超时时间（秒）

class _RetryableError(Exception):
    """可重试的网络错误（5xx 或网络异常）。"""
    pass

class _NonRetryableError(Exception):
    """不可重试的错误（4xx 或协议错误）。"""
    pass

def _retry_request(fn, *args, **kwargs):
    """
    带重试退避的请求封装（G1 生产门禁）。
    
    区分网络错误与 HTTP 错误码：
    - 4xx 错误不重试，直接抛出
    - 5xx 错误重试，最多 _max_retry 次
    - 网络异常（超时、连接错误）重试
    - 最终失败抛出原始异常
    
    参数:
        fn: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数
    
    返回:
        函数执行结果
    
    异常:
        最终失败时抛出原始异常
    """
    last_exc = None
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except _NonRetryableError:
            # 4xx 错误不重试，直接抛出
            raise
        except (_RetryableError, urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_exc = exc
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise
        except Exception as exc:
            # 其他异常不重试
            raise
    raise last_exc if last_exc else RuntimeError("Unexpected retry failure")


# ============================================================
# 常量定义
# ============================================================
SKILL_NAME = "marknest"
SKILL_VERSION = "1.0.3"
SKILL_DISPLAY = "文档转换 结构化整理 信息提取"
SKILL_DESCRIPTION = "将文件或链接转为规范、可复用的结构化输出。"

# 错误码定义
ERR_OK = 0
ERR_INPUT_EMPTY = "E001"        # 输入为空
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_FILE_READ = "E003"          # 文件读取失败
ERR_URL_FETCH = "E004"          # URL 获取失败
ERR_PARSE = "E005"              # 内容解析失败
ERR_UNSUPPORTED = "E006"        # 不支持的输入类型
ERR_INTERNAL = "E007"           # 内部错误
ERR_CONFIG = "E008"             # 配置错误
ERR_ARGS = "E009"               # 命令行参数错误
ERR_SELFTEST = "E010"           # 自检失败

# 支持的文件扩展名（文本类）
SUPPORTED_EXT = {".md", ".markdown", ".txt", ".text", ".rst", ".html", ".htm"}

# 自检用内置样例数据（硬编码，不读外部文件）
SELFTEST_SAMPLE = """\
# 项目周报

## 本周完成

- 完成登录模块重构
- 修复支付流程 Bug #1234
- 编写单元测试 50 个

## 下周计划

1. 部署到生产环境
2. 性能优化

> 备注：需要协调运维团队
"""

# 自检用 URL（真实网络请求，用于验证远程能力）
SELFTEST_URL = "https://example.com"


# ============================================================
# 核心数据结构
# ============================================================
class MarkNestError(Exception):
    """marknest 统一异常类，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ============================================================
# HTML 解析器（基于标准库 html.parser）
# ============================================================
class _HTMLContentParser(HTMLParser):
    """基于 html.parser 的 HTML 内容提取器。"""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.links = []
        self.headings = []
        self._current_tag = None
        self._current_attrs = {}
        self._skip_depth = 0
        self._in_script = False
        self._in_style = False
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag
        self._current_attrs = attrs_dict
        
        if tag in ('script', 'style'):
            self._in_script = True
            return
        
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            self.headings.append({'level': level, 'title': ''})
        
        if tag == 'a' and 'href' in attrs_dict:
            self.links.append({'title': '', 'url': attrs_dict['href']})
    
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._in_script = False
            return
        
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') and self.headings:
            # 标题结束，清理标题文本
            self.headings[-1]['title'] = self.headings[-1]['title'].strip()
    
    def handle_data(self, data):
        if self._in_script or self._in_style:
            return
        
        if data.strip():
            self.text_parts.append(data.strip())
            
            # 更新当前标题
            if self._current_tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') and self.headings:
                self.headings[-1]['title'] += data.strip()
            
            # 更新当前链接
            if self._current_tag == 'a' and self.links:
                self.links[-1]['title'] += data.strip()
    
    def get_text(self) -> str:
        """获取提取的纯文本内容。"""
        return '\n'.join(self.text_parts)


def _parse_html_content(html_text: str) -> Dict[str, Any]:
    """
    使用标准库 html.parser 解析 HTML 内容。
    
    参数:
        html_text: HTML 文本
    
    返回:
        包含提取内容的字典
    """
    parser = _HTMLContentParser()
    try:
        parser.feed(html_text)
    except Exception as exc:
        raise MarkNestError(ERR_PARSE, f"HTML 解析失败: {exc}") from exc
    
    return {
        'text': parser.get_text(),
        'headings': parser.headings,
        'links': parser.links,
    }


# ============================================================
# 工具函数
# ============================================================
def _safe_str(value: Any) -> str:
    """安全转换为字符串。"""
    if value is None:
        return ""
    return str(value)


def _strip_markdown_symbols(text: str) -> str:
    """去除 Markdown 标记符号，保留纯文本内容。"""
    # 移除标题符号
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 移除列表符号
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    # 移除有序列表数字
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
    # 移除引用符号
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    # 移除行内代码标记
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # 移除加粗/斜体标记
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    # 移除链接标记 [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 移除图片标记 ![alt](url) → alt
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _detect_format(text: str) -> str:
    """检测文本格式类型。"""
    if re.search(r"^#{1,6}\s+", text, flags=re.MULTILINE):
        return "markdown"
    if re.search(r"<html|<!DOCTYPE", text, flags=re.IGNORECASE):
        return "html"
    return "plain"


def _extract_title(text: str) -> str:
    """提取文档标题。"""
    # 优先找第一个 Markdown 标题
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    if match:
        return _safe_str(match.group(1)).strip()
    # 其次找 HTML 标题
    match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _safe_str(match.group(1)).strip()
    # 再找第一个非空行
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith(">"):
            return line[:100]
    return "未命名文档"


def _extract_headings(text: str) -> List[Dict[str, Any]]:
    """提取文档标题结构。"""
    headings = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            title = _safe_str(match.group(2)).strip()
            headings.append({"level": level, "title": title})
    return headings


def _extract_list_items(text: str) -> List[str]:
    """提取文档中的列表项。"""
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            item = re.sub(r"^[-*+]\s+", "", stripped)
            item = re.sub(r"^\d+[.)]\s+", "", item)
            items.append(_strip_markdown_symbols(item))
    return items


def _extract_links(text: str) -> List[Dict[str, str]]:
    """提取文档中的链接。"""
    links = []
    pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    for match in re.finditer(pattern, text):
        title = _safe_str(match.group(1)).strip()
        url = _safe_str(match.group(2)).strip()
        if url and not url.startswith("#"):
            links.append({"title": title, "url": url})
    # 也提取裸 URL
    url_pattern = r"https?://[^\s<>\"']+"
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        # 避免重复
        if not any(item["url"] == url for item in links):
            links.append({"title": url, "url": url})
    return links


def _count_words(text: str) -> int:
    """统计纯文本字数（中英文混合）。"""
    cleaned = _strip_markdown_symbols(text)
    # 中文字符和英文单词分别计数
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", cleaned))
    english_words = len(re.findall(r"[a-zA-Z0-9]+(?:['-][a-zA-Z0-9]+)*", cleaned))
    return chinese_chars + english_words


def _estimate_reading_time(word_count: int) -> int:
    """估算阅读时间（分钟），中文约 300 字/分钟，英文约 200 词/分钟。"""
    if word_count <= 0:
        return 0
    # 取较保守的估计
    minutes = max(1, round(word_count / 250))
    return minutes


# ============================================================
# 核心转换逻辑
# ============================================================
def convert_text(text: str, source: str = "text") -> Dict[str, Any]:
    """
    将文本转换为规范化结构化输出。

    参数:
        text: 原始文本内容
        source: 来源类型 ("text" / "file" / "url")

    返回:
        结构化字典，包含元数据、内容分析、提取结果等

    异常:
        MarkNestError: 当输入为空时抛出 E001
    """
    if not text or not text.strip():
        raise MarkNestError(ERR_INPUT_EMPTY, "输入内容为空，无法转换")

    # 检测格式
    fmt = _detect_format(text)

    # 根据格式提取内容
    if fmt == "html":
        html_data = _parse_html_content(text)
        # 使用 HTML 解析结果
        title = _extract_title(text)
        headings = html_data['headings'] if html_data['headings'] else _extract_headings(text)
        list_items = _extract_list_items(html_data['text'])
        links = html_data['links'] if html_data['links'] else _extract_links(text)
        content_text = html_data['text']
    else:
        # Markdown 或纯文本
        title = _extract_title(text)
        headings = _extract_headings(text)
        list_items = _extract_list_items(text)
        links = _extract_links(text)
        content_text = text

    word_count = _count_words(content_text)
    reading_time = _estimate_reading_time(word_count)

    # 统计段落数
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content_text) if p.strip()]
    paragraph_count = len(paragraphs)

    # 提取关键词（简单统计高频词）
    keywords = _extract_keywords(content_text, top_n=5)

    # 构建规范化输出结构
    result = {
        "schema_version": "1.0",
        "skill": {
            "name": SKILL_NAME,
            "version": SKILL_VERSION,
            "display_name": SKILL_DISPLAY,
            "description": SKILL_DESCRIPTION,
        },
        "meta": {
            "source_type": source,
            "format": fmt,
            "converted_at": datetime.now(timezone.utc).isoformat(),
            "processor": "marknest-cleanroom-impl",
        },
        "content": {
            "title": title,
            "word_count": word_count,
            "reading_time_minutes": reading_time,
            "paragraph_count": paragraph_count,
            "headings": headings,
            "list_items": list_items,
            "links": links,
            "keywords": keywords,
        },
        "summary": {
            "title": title,
            "excerpt": _generate_excerpt(content_text, max_length=200),
            "structure_type": "document",
        },
    }

    return result


def _extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """提取关键词（基于词频的简单实现）。"""
    cleaned = _strip_markdown_symbols(text).lower()
    # 中文分词简化处理：按字分割（2-4字组合）
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", cleaned)
    chinese_words = []
    for i in range(len(chinese_chars) - 1):
        chinese_words.append(chinese_chars[i] + chinese_chars[i + 1])

    # 英文单词
    english_words = re.findall(r"[a-zA-Z]{3,}", cleaned)

    # 合并统计
    all_words = chinese_words + english_words
    stopwords = {"的", "了", "是", "在", "和", "与", "及", "或", "the", "and", "for", "with", "this", "that"}

    word_count: Dict[str, int] = {}
    for word in all_words:
        if word in stopwords or len(word) < 2:
            continue
        word_count[word] = word_count.get(word, 0) + 1

    # 按频率排序取前 N
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_n]]


def _generate_excerpt(text: str, max_length: int = 200) -> str:
    """生成文档摘要。"""
