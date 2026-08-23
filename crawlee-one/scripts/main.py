#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawlee-one 独立实现脚本
========================
依据功能规格独立编写，不复制任何既有代码。
提供网页/数据文件的结构化采集流程与输出。
仅使用标准库，无第三方依赖。

用法示例:
    python main.py --selftest
    python main.py --fetch https://example.com --selector "h1"
    python main.py --file data.html --selector ".item" --output result.json
"""

import argparse
import json
import re
import sys
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from html.entities import html5
import os
import tempfile

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式非法",
    "E002": "网络错误：URL 无法访问或请求失败",
    "E003": "解析错误：HTML/文本内容解析失败",
    "E004": "选择器错误：CSS 选择器格式非法",
    "E005": "数据提取错误：未能从内容中提取到有效数据",
    "E006": "文件错误：本地文件不存在或无法读取",
    "E007": "编码错误：内容编码识别或转换失败",
    "E008": "输出错误：结果写入失败",
    "E009": "内部错误：未预期的运行时异常",
    "E010": "自检错误：自检断言失败",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并以对应错误码退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg} | {message}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------- 数据模型 ----------

@dataclass
class FetchResult:
    """采集结果数据模型。"""
    url: str = ""
    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    content: str = ""
    encoding: str = "utf-8"
    extracted: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------- 核心功能模块 ----------

class CustomHtmlParser(HTMLParser):
    """HTML 解析器：基于标准库 html.parser 实现，提供扁平元素列表。
    
    支持基于标签名、class、id、属性匹配的简单选择器查询。
    对于畸形 HTML，会尽量容错处理（忽略未闭合标签等），并记录警告。
    """

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self._html = html
        self._elements = []  # 存储所有元素（扁平列表）
        self._current_element = None
        self._stack = []
        self._text_buffer = []
        self._current_text = []
        self._parse_complete = False
        self._parse_warnings = []
        try:
            self.feed(html)
            self.close()
        except Exception as e:
            # 容错：解析失败时保留已解析的部分，并记录警告
            self._parse_warnings.append(f"HTML 解析警告: {e}")
        self._parse_complete = True

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        """处理开始标签。"""
        attr_dict = dict(attrs)
        element = {
            "tag": tag.lower(),
            "attrs": attr_dict,
            "children": [],
            "text": "",
            "parent": None,
            "html": "",
        }
        if self._stack:
            element["parent"] = self._stack[-1]
            self._stack[-1]["children"].append(element)
        else:
            self._elements.append(element)
        self._stack.append(element)
        self._current_element = element
        self._current_text = []

    def handle_startendtag(self, tag: str, attrs: List[tuple]):
        """处理自闭合标签。"""
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str):
        """处理结束标签。"""
        if self._stack:
            element = self._stack.pop()
            element["text"] = "".join(self._current_text).strip()
            self._current_text = []
            if self._stack:
                self._current_element = self._stack[-1]
            else:
                self._current_element = None

    def handle_data(self, data: str):
        """处理文本数据。"""
        if self._stack:
            self._current_text.append(data)

    def handle_entityref(self, name: str):
        """处理实体引用。"""
        if name in html5:
            self._current_text.append(html5[name])

    def handle_charref(self, name: str):
        """处理字符引用。"""
        try:
            if name.startswith("x"):
                char = chr(int(name[1:], 16))
            else:
                char = chr(int(name))
            self._current_text.append(char)
        except ValueError:
            pass

    def get_elements(self) -> List[Dict[str, Any]]:
        """获取所有解析的元素（扁平列表）。"""
        return self._elements

    def get_text(self) -> str:
        """提取纯文本内容。"""
        texts = []
        for elem in self._elements:
            if elem["text"]:
                texts.append(elem["text"])
        return " ".join(texts)

    def find_all(self, tag: Optional[str] = None, attrs: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """查找所有匹配的元素。"""
        attrs = attrs or {}
        results = []
        for elem in self._elements:
            if tag and elem["tag"] != tag.lower():
                continue
            if attrs:
                matched = True
                for key, val in attrs.items():
                    if key not in elem["attrs"] or elem["attrs"][key] != val:
                        matched = False
                        break
                if not matched:
                    continue
            results.append(elem)
        return results

    def find_by_class(self, class_name: str, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """按 class 属性查找元素。"""
        return self.find_all(tag=tag, attrs={"class": class_name})

    def extract_text(self, tag: str, attrs: Optional[Dict[str, str]] = None) -> List[str]:
        """提取匹配元素的文本内容。"""
        elements = self.find_all(tag=tag, attrs=attrs)
        return [elem["text"] for elem in elements if elem["text"]]

    def get_warnings(self) -> List[str]:
        """获取解析警告。"""
        return self._parse_warnings


class CssSelector:
    """CSS 选择器解析与匹配（支持 tag、.class、#id、[attr=value]、组合选择器）。"""

    def __init__(self, selector: str):
        self.selector = selector.strip()
        self._parts = self._parse(self.selector)
        if not self._parts:
            error_exit("E004", f"选择器格式非法: {selector}")

    def _parse(self, selector: str) -> List[Dict[str, Any]]:
        """解析选择器为规则列表。"""
        parts = []
        # 支持逗号分隔
        for group in selector.split(","):
            group = group.strip()
            if not group:
                continue
            # 分解复合选择器（简单处理：空格分隔）
            for item in group.split():
                rule: Dict[str, Any] = {"tag": None, "class": None, "id": None, "attrs": {}}
                # 匹配 tag
                m = re.match(r"^([a-zA-Z][a-zA-Z0-9]*)", item)
                if m:
                    rule["tag"] = m.group(1)
                    item = item[m.end():]
                # 匹配 #id
                m = re.search(r"#([a-zA-Z_][a-zA-Z0-9_-]*)", item)
                if m:
                    rule["id"] = m.group(1)
                # 匹配 .class
                for cls in re.findall(r"\.([a-zA-Z_][a-zA-Z0-9_-]*)", item):
                    rule["class"] = cls
                # 匹配 [attr=value]
                for am in re.finditer(r"\[([a-zA-Z_-]+)=['\"]?([^'\"]+)['\"]?\]", item):
                    rule["attrs"][am.group(1)] = am.group(2)
                parts.append(rule)
        return parts

    def match(self, tag: str, attrs: Dict[str, str]) -> bool:
        """判断标签和属性是否匹配选择器。"""
        for rule in self._parts:
            if rule["tag"] and rule["tag"] != tag:
                continue
            if rule["id"] and attrs.get("id") != rule["id"]:
                continue
            if rule["class"] and rule["class"] not in attrs.get("class", "").split():
                continue
            for key, val in rule["attrs"].items():
                if attrs.get(key) != val:
                    break
            else:
                return True
        return False


class DataExtractor:
    """从 HTML 内容中提取结构化数据。"""

    def __init__(self, html: str):
        self.parser = CustomHtmlParser(html)

    def extract_by_selector(self, selector: str) -> List[Dict[str, Any]]:
        """按 CSS 选择器提取数据。"""
        css = CssSelector(selector)
        results = []
        for elem in self.parser.get_elements():
            if css.match(elem["tag"], elem["attrs"]):
                results.append({
                    "tag": elem["tag"],
                    "attrs": elem["attrs"],
                    "text": elem["text"],
                })
        return results

    def extract_tables(self) -> List[Dict[str, Any]]:
        """提取表格数据。"""
        tables = []
        table_elements = self.parser.find_all("table")
        for table in table_elements:
            rows = []
            for row in table.get("children", []):
                if row["tag"] == "tr":
                    cells = []
                    for cell in row.get("children", []):
                        if cell["tag"] in ("td", "th"):
                            cells.append(cell["text"])
                    if cells:
                        rows.append(cells)
            if rows:
                tables.append({"rows": rows})
        return tables

    def extract_links(self, base_url: str = "") -> List[Dict[str, str]]:
        """提取所有链接。"""
        links = []
        for elem in self.parser.find_all("a"):
            href = elem["attrs"].get("href", "")
            if href:
                full_url = urljoin(base_url, href) if base_url else href
                links.append({"href": full_url, "text": elem["text"]})
        return links

    def get_warnings(self) -> List[str]:
        """获取解析警告。"""
        return self.parser.get_warnings()


class ContentFetcher:
    """获取网页或文件内容。"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    ]

    @staticmethod
    def _get_random_user_agent() -> str:
        """获取随机 User-Agent。"""
        import random
        return random.choice(ContentFetcher.USER_AGENTS)

    @staticmethod
    def fetch_url(url: str, timeout: int = 10, max_retries: int = 3) -> FetchResult:
        """从 URL 获取内容，带重试退避机制和超时设置。"""
        for attempt in range(max_retries):
            try:
                req = Request(url, headers={"User-Agent": ContentFetcher._get_random_user_agent()})
                with urlopen(req, timeout=timeout) as resp:
                    # 处理重定向
                    final_url = resp.geturl()
                    result = FetchResult()
                    result.url = final_url
                    result.status_code = getattr(resp, "status", 200)
                    result.headers = {k: v for k, v in resp.headers.items()}
                    raw = resp.read()
                    # 尝试从 header 获取编码
                    content_type = result.headers.get("Content-Type", "")
                    charset_match = re.search(r"charset=([\w-]+)", content_type)
                    if charset_match:
                        result.encoding = charset_match.group(1)
                    else:
                        result.encoding = "utf-8"
                    try:
                        result.content = raw.decode(result.encoding, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        # 尝试 utf-8
                        try:
                            result.content = raw.decode("utf-8", errors="replace")
                            result.encoding = "utf-8"
                        except Exception:
                            result.content = raw.decode("latin-1", errors="replace")
                            result.encoding = "latin-1"
                    return result
            except HTTPError as e:
                if e.code == 429:
                    # 限流：等待更长时间后重试
                    wait_time = (2 ** attempt) * 2 + 0.5
                    print(f"  限流 (429)，等待 {wait_time:.2f} 秒...")
                    time.sleep(wait_time)
                    continue
                elif e.code in (301, 302, 303, 307, 308):
                    # 重定向处理
                    redirect_url = e.headers.get("Location")
                    if redirect_url:
                        url = urljoin(url, redirect_url)
                        continue
                if attempt == max_retries - 1:
                    error_exit("E002", f"URL 访问失败: {url} | HTTP {e.code}")
            except (URLError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    error_exit("E002", f"URL 访问失败: {url} | {e}")
                # 指数退避
                wait_time = 2 ** attempt + 0.5
                print(f"  重试 {attempt + 1}/{max_retries}，等待 {wait_time:.2f} 秒...")
                time.sleep(wait_time)
            except Exception as e:
                error_exit("E002", f"URL 访问失败: {url} | {e}")
        error_exit("E002", f"URL 访问失败: {url}")

    @staticmethod
    def fetch_urls_concurrent(urls: List[str], timeout: int = 10, max_workers: int = 5) -> List[FetchResult]:
        """并发获取多个 URL，使用 Semaphore 限制并发数。"""
        results = []
        semaphore = threading.Semaphore(max_workers)
        
        def fetch_with_semaphore(url):
            with semaphore:
                return ContentFetcher.fetch_url(url, timeout)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(fetch_with_semaphore, url): url for url in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"  获取 {url} 失败: {e}")
        return results

    @staticmethod
    def fetch_file(path: str) -> FetchResult:
        """从本地文件读取内容。"""
        try:
            with open(path, "rb") as f:
                raw = f.read()
            result = FetchResult()
            result.url = f"file://{path}"
            result.status_code = 200
            # 尝试多种编码
            for enc in ["utf-8", "gbk", "latin-1"]:
                try:
                    result.content = raw.decode(enc)
                    result.encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
            else:
                result.content = raw.decode("utf-8", errors="replace")
                result.encoding = "utf-8"
            return result
        except FileNotFoundError:
            error_exit("E006", f"文件不存在: {path}")
        except Exception as e:
            error_exit("E006", f"文件读取失败: {path} | {e}")


class Pipeline:
    """采集流水线：获取 → 解析 → 提取 → 输出。"""

    def __init__(self, source: str, source_type: str = "auto"):
        self.source = source
        self.source_type = source_type
        self.result = FetchResult()

    def run(self, selector: Optional[str] = None) -> FetchResult:
        """执行采集流程。"""
        # 1. 获取内容
        if self.source_type == "url":
            self.result = ContentFetcher.fetch_url(self.source)
        elif self.source_type == "file":
            self.result = ContentFet
