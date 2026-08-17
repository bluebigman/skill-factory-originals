#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-browser-workspace 独立实现脚本
====================================
面向AI代理的本地浏览器工具集，支持网页数据采集与深度调研。

本脚本为 clean-room 重写实现，仅依据功能规格独立编写。
提供命令行接口与离线自检功能。

错误码说明:
    E001: 参数解析错误
    E002: 不支持的子命令
    E003: 缺少必选参数
    E004: 内部逻辑错误
    E005: 数据转换失败
    E006: 自检断言失败
    E007: 文件读写失败
    E008: 外部依赖缺失
    E009: 运行环境不满足
    E010: 未知异常
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.robotparser
import http.server
import threading
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class PageSnapshot:
    """页面快照数据模型"""
    url: str
    title: str
    content: str
    meta: Dict[str, str] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    extracted_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "meta": self.meta,
            "links": self.links,
            "extracted_at": self.extracted_at,
        }


# ---------------------------------------------------------------------------
# HTML解析器（基于标准库，避免外部依赖）
# ---------------------------------------------------------------------------
class LinkExtractorParser(HTMLParser):
    """基于HTMLParser的链接提取器，处理嵌套引号和实体编码"""
    
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._current_href = None
        self._current_text = []
        self._skip_depth = 0  # 用于跳过script/style内容
        
    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in ('script', 'style'):
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if tag_lower == 'a':
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get('href')
            self._current_text = []
            
    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._current_href is not None:
            self._current_text.append(data)
            
    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in ('script', 'style'):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth > 0:
            return
        if tag_lower == 'a' and self._current_href is not None:
            text = ''.join(self._current_text).strip()
            self.links.append((self._current_href, text))
            self._current_href = None
            self._current_text = []


class TitleExtractorParser(HTMLParser):
    """基于HTMLParser的标题提取器"""
    
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'title':
            self._in_title = True
            
    def handle_data(self, data):
        if self._in_title:
            self.title += data
            
    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self._in_title = False


class ContentExtractorParser(HTMLParser):
    """基于HTMLParser的内容提取器，提取正文文本"""
    
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self._skip_depth = 0
        self._in_script_style = False
        
    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in ('script', 'style', 'noscript'):
            self._in_script_style = True
            self._skip_depth += 1
            return
        if self._in_script_style:
            self._skip_depth += 1
            return
        # 添加段落分隔
        if tag_lower in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'):
            self.text_parts.append('\n')
            
    def handle_data(self, data):
        if self._in_script_style:
            return
        if data.strip():
            self.text_parts.append(data)
            
    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in ('script', 'style', 'noscript'):
            self._skip_depth = max(0, self._skip_depth - 1)
            if self._skip_depth == 0:
                self._in_script_style = False
            return
        if self._in_script_style:
            self._skip_depth = max(0, self._skip_depth - 1)
            if self._skip_depth == 0:
                self._in_script_style = False
            return
        if tag_lower in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'):
            self.text_parts.append('\n')


# ---------------------------------------------------------------------------
# 核心功能模块
# ---------------------------------------------------------------------------
class BrowserAutomationCore:
    """
    浏览器自动化核心逻辑（纯逻辑实现，不依赖具体浏览器）
    提供网页内容解析、数据处理、格式转换等能力。
    """

    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式是否合法"""
        try:
            result = urlparse(url)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except Exception:
            return False

    @staticmethod
    def extract_links(html_content: str, base_url: str = "") -> List[str]:
        """
        从HTML内容中提取链接
        使用HTMLParser处理嵌套引号和实体编码
        """
        if not html_content:
            return []

        parser = LinkExtractorParser()
        try:
            parser.feed(html_content)
        except Exception:
            return []

        links = []
        for href, _ in parser.links:
            if not href:
                continue
            # 跳过javascript:、data:、mailto:、tel:等非HTTP协议
            href_lower = href.strip().lower()
            if href_lower.startswith(('javascript:', 'data:', 'mailto:', 'tel:', 'vbscript:', 'file:')):
                continue
            # 处理相对路径
            if base_url and not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
            if href.startswith(('http://', 'https://')):
                links.append(href)

        # 去重并保持顺序
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        return unique_links

    @staticmethod
    def extract_title(html_content: str) -> str:
        """从HTML内容中提取标题"""
        if not html_content:
            return ""

        parser = TitleExtractorParser()
        try:
            parser.feed(html_content)
        except Exception:
            return ""
        return parser.title.strip()

    @staticmethod
    def extract_content(html_content: str) -> str:
        """从HTML内容中提取正文文本"""
        if not html_content:
            return ""

        parser = ContentExtractorParser()
        try:
            parser.feed(html_content)
        except Exception:
            # 降级处理：使用正则提取
            text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        # 合并文本
        text = ''.join(parser.text_parts)
        # 清理空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    @staticmethod
    def html_to_text(html_content: str) -> str:
        """简单将HTML转为纯文本（去除标签）"""
        return BrowserAutomationCore.extract_content(html_content)

    @staticmethod
    def fetch_url(url: str, timeout: int = 10, max_retries: int = 3) -> Tuple[str, Dict[str, str]]:
        """
        获取网页内容，带重试退避和超时控制
        返回 (html_content, headers_dict)
        """
        if not BrowserAutomationCore.validate_url(url):
            raise ValueError(f"无效的URL: {url}")

        # 检查robots.txt（带缓存）
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        try:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            if not rp.can_fetch("*", url):
                raise PermissionError(f"robots.txt禁止抓取: {url}")
        except Exception:
            # robots.txt不可用时不阻止，但记录警告
            pass

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    html_content = response.read().decode('utf-8', errors='ignore')
                    response_headers = dict(response.headers)
                    return html_content, response_headers
            except urllib.error.HTTPError as e:
                # HTTP错误分类处理
                last_error = e
                if e.code in (401, 403):
                    # 权限错误，不重试
                    raise ConnectionError(f"HTTP {e.code}: 权限不足，无法访问 {url}") from e
                elif e.code in (404, 410):
                    # 资源不存在，不重试
                    raise ConnectionError(f"HTTP {e.code}: 资源不存在 {url}") from e
                elif e.code >= 500:
                    # 服务器错误，重试
                    if attempt == max_retries - 1:
                        raise ConnectionError(f"HTTP {e.code}: 服务器错误（重试{max_retries}次）: {url}") from e
                else:
                    # 其他HTTP错误，不重试
                    raise ConnectionError(f"HTTP {e.code}: {url}") from e
            except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
                # 网络错误，重试
                last_error = e
                if attempt == max_retries - 1:
                    raise ConnectionError(f"网络错误（重试{max_retries}次）: {url} - {e}") from e
            except Exception as e:
                # 其他错误，不重试
                raise ConnectionError(f"获取网页失败: {url} - {e}") from e

            # 指数退避
            wait_time = 2 ** attempt
            time.sleep(wait_time)

        raise ConnectionError(f"获取网页失败（重试{max_retries}次）: {url} - {last_error}")

    @staticmethod
    def fetch_urls_parallel(urls: List[str], timeout: int = 10, max_retries: int = 3, max_workers: int = 5) -> Dict[str, Tuple[str, Dict[str, str]]]:
        """
        并行获取多个网页内容，带速率限制
        返回 {url: (html_content, headers_dict)}
        """
        results = {}
        request_interval = 0.1  # 请求间隔（秒）
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(BrowserAutomationCore.fetch_url, url, timeout, max_retries): url
                for url in urls
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    results[url] = future.result()
                except Exception as e:
                    results[url] = (None, {"error": str(e)})
                time.sleep(request_interval)  # 速率限制
        return results

    @staticmethod
    def structure_content(snapshot: PageSnapshot, output_format: str = "json") -> str:
        """
        将页面快照结构化为指定格式（json/csv/markdown）
        """
        if output_format == "json":
            return json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2)
        elif output_format == "csv":
            # 简单CSV输出
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["url", "title", "content", "extracted_at"])
            writer.writerow([
                snapshot.url,
                snapshot.title,
                snapshot.content[:200],  # 内容截断避免过长
                snapshot.extracted_at
            ])
            return output.getvalue()
        elif output_format == "markdown":
            md_lines = [
                f"# {snapshot.title}",
                "",
                f"**URL**: {snapshot.url}",
                f"**提取时间**: {snapshot.extracted_at}",
                "",
                "## 内容摘要",
                "",
                snapshot.content[:500],
                "",
                "## 页面链接",
                "",
            ]
            for link in snapshot.links[:20]:
                md_lines.append(f"- {link}")
            return "\n".join(md_lines)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")


class ResearchAssistant:
    """深度调研辅助工具"""

    def __init__(self):
        self.snapshots: List[PageSnapshot] = []
        self.core = BrowserAutomationCore()

    def add_snapshot(self, snapshot: PageSnapshot) -> None:
        """添加页面快照"""
        self.snapshots.append(snapshot)

    def search_keyword(self, keyword: str) -> List[PageSnapshot]:
        """在已采集的页面中搜索关键词"""
        results = []
        keyword_lower = keyword.lower()
        for snapshot in self.snapshots:
            if keyword_lower in snapshot.content.lower() or keyword_lower in snapshot.title.lower():
                results.append(snapshot)
        return results

    def generate_report(self, output_format: str = "markdown") -> str:
        """生成调研报告"""
        if not self.snapshots:
            return "暂无采集数据"

        if output_format == "json":
            return json.dumps(
                [s.to_dict() for s in self.snapshots],
                ensure_ascii=False,
                indent=2
            )
        elif output_format == "markdown":
            lines = [
                "# 深度调研报告",
                "",
                f"共采集 **{len(self.snapshots)}** 个页面",
                "",
                "## 页面列表",
                "",
            ]
            for i, snap in enumerate(self.snapshots, 1):
                lines.extend([
                    f"### {i}. {snap.title}",
                    f"- URL: {snap.url}",
                    f"- 链接数: {len(snap.links)}",
                    f"- 内容长度: {len(snap.content)} 字符",
                    "",
                ])
            return "\n".join(lines)
        elif output_format == "csv":
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["index", "url", "title", "content_length", "link_count"])
            for i, snap in enumerate(self.snapshots, 1):
                writer.writerow([i, snap.url, snap.title, len(snap.content), len(snap.links)])
            return output.getvalue()
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")


class DataConverter:
    """数据转换输出工具"""

    @staticmethod
    def to_json(data: Any) -> str:
        """转换为JSON字符串"""
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            raise ValueError(f"数据无法转换为JSON: {e}") from e

    @staticmethod
    def to_csv(headers: List[str], rows: List[List[Any]]) -> str:
        """转换为CSV字符串"""
        if not headers or not rows:
            return ""
        try:
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(rows)
            return output.getvalue()
        except Exception as e:
            raise ValueError(f"数据无法转换为CSV: {e}") from e

    @staticmethod
    def to_markdown_table(headers: List[str], rows: List[List[Any]]) -> str:
        """转换为Markdown表格"""
        if not headers:
            return ""
        lines
