#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autoscraper - 网页数据自动采集与结构化提取
==========================================
基于标准库实现，无第三方依赖。

功能概述：
    1. 单页抓取：给定 URL 和示例数据，提取结构化数据
    2. 批量抓取：从文件读取多个 URL，批量提取数据
    3. 规则学习：根据示例数据学习提取规则
    4. 多格式输出：支持 JSON、CSV、文本格式输出
    5. 预览模式：--dry-run 只显示不写盘
    6. 自检模式：--selftest 运行内置测试

错误码体系：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 文件读取失败
    E007: URL 格式无效
    E008: 批量处理中断
    E009: 输出写入失败
    E010: 未知内部错误

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ProcessingResult:
    """处理结果数据模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_input: Any = None


@dataclass
class FieldDefinition:
    """字段定义，用于描述期望提取的字段"""
    name: str
    aliases: List[str] = field(default_factory=list)
    required: bool = False
    type_hint: str = "string"  # string, number, boolean, date


# ============================================================
# 核心处理引擎
# ============================================================

class AutoScraperEngine:
    """
    核心处理引擎：负责解析输入、提取关键信息、生成结构化结果。

    设计原则：
    - 输入可以是字符串、字典、列表或包含文本的文件路径
    - 使用启发式规则识别关键信息，不依赖特定网站结构
    - 输出统一为字典结构，包含提取的字段和置信度
    """

    # 常见字段别名映射，用于识别关键信息
    COMMON_FIELD_ALIASES = {
        "标题": ["title", "标题", "题目", "headline", "name", "文章标题"],
        "作者": ["author", "作者", "creator", "writer", "by", "作者:"],
        "日期": ["date", "日期", "time", "发布时间", "publish_date", "created_at"],
        "价格": ["price", "价格", "售价", "现价", "原价", "amount"],
        "描述": ["description", "描述", "简介", "摘要", "summary", "content"],
        "链接": ["link", "链接", "url", "href", "source_url"],
        "图片": ["image", "图片", "img", "thumbnail", "pic"],
        "标签": ["tag", "标签", "keyword", "keywords", "分类"],
        "数量": ["count", "数量", "销量", "库存", "stock", "quantity"],
        "评分": ["rating", "评分", "score", "星级", "stars"],
    }

    # 常见 CSS 选择器模式，用于自动识别
    COMMON_SELECTOR_PATTERNS = {
        "标题": ["h1", "h2", "h3", ".title", ".headline", "[class*=title]"],
        "价格": [".price", "[class*=price]", "span.price", "del", "ins"],
        "日期": [".date", "time", "[class*=date]", ".publish-time"],
        "链接": ["a[href]", "[class*=link]", ".url"],
        "图片": ["img[src]", "[class*=image]", ".thumbnail"],
        "描述": [".description", "[class*=desc]", ".summary", "p"],
        "标签": [".tag", "[class*=tag]", ".keyword", ".label"],
    }

    def __init__(self, timeout: int = 30, retries: int = 3, user_agent: Optional[str] = None):
        """
        初始化引擎。

        Args:
            timeout: 网络请求超时时间（秒）
            retries: 网络请求重试次数
            user_agent: 自定义 User-Agent
        """
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self._session_cookies: Dict[str, str] = {}

    def extract_from_url(self, url: str, rules: Optional[Dict[str, str]] = None,
                         wanted_fields: Optional[List[str]] = None) -> ProcessingResult:
        """
        从 URL 提取结构化数据。

        Args:
            url: 目标 URL
            rules: 自定义 CSS 选择器规则 {字段名: 选择器}
            wanted_fields: 期望提取的字段名列表

        Returns:
            ProcessingResult 对象
        """
        try:
            # 校验 URL
            if not self._validate_url(url):
                return ProcessingResult(
                    success=False,
                    error_code="E007",
                    error_message=f"URL 格式无效: {url}"
                )

            # 获取页面内容
            html_content = self._fetch_url(url)
            if html_content is None:
                return ProcessingResult(
                    success=False,
                    error_code="E007",
                    error_message=f"无法访问 URL: {url}"
                )

            # 提取数据
            return self.extract_from_html(html_content, rules=rules, wanted_fields=wanted_fields)

        except Exception as e:
            return ProcessingResult(
                success=False,
                error_code="E010",
                error_message=f"未知错误: {str(e)}"
            )

    def extract_from_html(self, html: str, rules: Optional[Dict[str, str]] = None,
                          wanted_fields: Optional[List[str]] = None) -> ProcessingResult:
        """
        从 HTML 内容提取结构化数据。

        Args:
            html: HTML 内容
            rules: 自定义 CSS 选择器规则 {字段名: 选择器}
            wanted_fields: 期望提取的字段名列表

        Returns:
            ProcessingResult 对象
        """
        try:
            if not html or not html.strip():
                return ProcessingResult(
                    success=False,
                    error_code="E001",
                    error_message="HTML 内容为空"
                )

            # 清理 HTML
            html = self._clean_html(html)

            # 确定要提取的字段
            fields_to_extract = self._determine_fields(rules, wanted_fields)

            # 提取数据
            extracted_data: Dict[str, List[str]] = {}
            warnings: List[str] = []
            field_confidences: Dict[str, float] = {}

            for field_name, selector in fields_to_extract.items():
                values, confidence = self._extract_field(html, field_name, selector)
                if values:
                    extracted_data[field_name] = values
                    field_confidences[field_name] = confidence
                else:
                    warnings.append(f"字段 '{field_name}' 未提取到数据")
                    field_confidences[field_name] = 0.0

            # 计算总体置信度
            if fields_to_extract:
                overall_confidence = sum(field_confidences.values()) / len(fields_to_extract)
            else:
                overall_confidence = 0.0

            # 检查是否有占位符
            for field_name, values in extracted_data.items():
                for i, value in enumerate(values):
                    if "[需核实" in value:
                        warnings.append(f"字段 '{field_name}' 包含占位符")

            return ProcessingResult(
                success=True,
                data=extracted_data,
                confidence=overall_confidence,
                warnings=warnings
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                error_code="E010",
                error_message=f"提取失败: {str(e)}"
            )

    def extract_from_file(self, file_path: str, rules: Optional[Dict[str, str]] = None,
                          wanted_fields: Optional[List[str]] = None) -> ProcessingResult:
        """
        从文件提取数据（支持文本和 JSON 格式）。

        Args:
            file_path: 文件路径
            rules: 自定义 CSS 选择器规则
            wanted_fields: 期望提取的字段名列表

        Returns:
            ProcessingResult 对象
        """
        try:
            if not os.path.exists(file_path):
                return ProcessingResult(
                    success=False,
                    error_code="E006",
                    error_message=f"文件不存在: {file_path}"
                )

            # 读取文件内容
            content = self._read_file(file_path)
            if content is None:
                return ProcessingResult(
                    success=False,
                    error_code="E006",
                    error_message=f"无法读取文件: {file_path}"
                )

            # 尝试解析 JSON
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return ProcessingResult(
                        success=True,
                        data=data,
                        confidence=1.0,
                        raw_input=data
                    )
                elif isinstance(data, list):
                    return ProcessingResult(
                        success=True,
                        data={"items": data},
                        confidence=1.0,
                        raw_input=data
                    )
            except json.JSONDecodeError:
                pass

            # 作为文本处理
            return self.extract_from_text(content, rules=rules, wanted_fields=wanted_fields)

        except Exception as e:
            return ProcessingResult(
                success=False,
                error_code="E010",
                error_message=f"文件处理失败: {str(e)}"
            )

    def extract_from_text(self, text: str, rules: Optional[Dict[str, str]] = None,
                          wanted_fields: Optional[List[str]] = None) -> ProcessingResult:
        """
        从纯文本提取结构化数据。

        Args:
            text: 文本内容
            rules: 自定义提取规则
            wanted_fields: 期望提取的字段名列表

        Returns:
            ProcessingResult 对象
        """
        try:
            if not text or not text.strip():
                return ProcessingResult(
                    success=False,
                    error_code="E001",
                    error_message="文本内容为空"
                )

            # 确定要提取的字段
            fields_to_extract = self._determine_fields(rules, wanted_fields)

            # 提取数据
            extracted_data: Dict[str, List[str]] = {}
            warnings: List[str] = []
            field_confidences: Dict[str, float] = {}

            for field_name, pattern in fields_to_extract.items():
                values, confidence = self._extract_from_text(text, field_name, pattern)
                if values:
                    extracted_data[field_name] = values
                    field_confidences[field_name] = confidence
                else:
                    warnings.append(f"字段 '{field_name}' 未提取到数据")
                    field_confidences[field_name] = 0.0

            # 计算总体置信度
            if fields_to_extract:
                overall_confidence = sum(field_confidences.values()) / len(fields_to_extract)
            else:
                overall_confidence = 0.0

            return ProcessingResult(
                success=True,
                data=extracted_data,
                confidence=overall_confidence,
                warnings=warnings
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                error_code="E010",
                error_message=f"文本处理失败: {str(e)}"
            )

    def _determine_fields(self, rules: Optional[Dict[str, str]],
                          wanted_fields: Optional[List[str]]) -> Dict[str, str]:
        """
        确定要提取的字段和对应的选择器/模式。

        Args:
            rules: 自定义规则
            wanted_fields: 期望的字段名列表

        Returns:
            字段名到选择器/模式的映射
        """
        fields: Dict[str, str] = {}

        # 优先使用自定义规则
        if rules:
            for field_name, selector in rules.items():
                fields[field_name] = selector

        # 添加期望字段的默认选择器
        if wanted_fields:
            for field_name in wanted_fields:
                if field_name not in fields:
                    # 查找默认选择器
                    selector = self._find_default_selector(field_name)
                    if selector:
                        fields[field_name] = selector

        # 如果没有指定任何字段，使用默认字段
        if not fields:
            fields = {
                "标题": "h1, h2, h3, .title, [class*=title]",
                "描述": ".description, [class*=desc], .summary, p",
                "链接": "a[href]",
            }

        return fields

    def _find_default_selector(self, field_name: str) -> Optional[str]:
        """
        根据字段名查找默认选择器。

        Args:
            field_name: 字段名

        Returns:
            CSS 选择器或 None
        """
        # 检查别名映射
        for canonical_name, aliases in self.COMMON_FIELD_ALIASES.items():
            if field_name in aliases or field_name == canonical_name:
                patterns = self.COMMON_SELECTOR_PATTERNS.get(canonical_name, [])
                if patterns:
                    return ", ".join(patterns)

        # 尝试基于字段名生成选择器
        field_lower = field_name.lower()
        return f"[class*={field_lower}], [id*={field_lower}], .{field_lower}"

    def _extract_field(self, html: str, field_name: str, selector: str) -> Tuple[List[str], float]:
        """
        从 HTML 中提取指定字段。

        Args:
            html: HTML 内容
            field_name: 字段名
            selector: CSS 选择器

        Returns:
            (提取的值列表, 置信度)
        """
        try:
            # 使用正则表达式模拟 CSS 选择器（简化版）
            values = self._css_select(html, selector)

            if not values:
                return [], 0.0

            # 清理值
            cleaned_values = []
            for value in values:
                cleaned = self._clean_value(value)
                if cleaned:
                    cleaned_values.append(cleaned)

            if not cleaned_values:
                return [], 0.0

            # 计算置信度
            confidence = min(0.95, 0.5 + 0.1 * len(cleaned_values))

            return cleaned_values, confidence

        except Exception:
            return [], 0.0

    def _extract_from_text(self, text: str, field_name: str, pattern: str) -> Tuple[List[str], float]:
        """
        从纯文本中提取指定字段。

        Args:
            text: 文本内容
            field_name: 字段名
            pattern: 正则表达式模式

        Returns:
            (提取的值列表, 置信度)
        """
        try:
            # 尝试作为正则表达式使用
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                matches = regex.findall(text)
                if matches:
                    # 处理匹配结果
                    values = []
                    for match in matches:
                        if isinstance(match, tuple):
                            values.extend([m for m in match if m])
                        else:
                            values.append(match)
                    if values:
                        confidence = min(0.9, 0.5 + 0.1 * len(values))
                        return values[:10], confidence
            except re.error:
                pass

            # 尝试作为关键词搜索
            if pattern in text:
                # 提取包含关键词的句子
                sentences = re.split(r'[。！？!?]', text)
                values = [s.strip() for s in sentences if pattern in s]
                if values:
                    confidence = 0.6
                    return values[:10], confidence

            return [], 0.0

        except Exception:
            return [], 0.0

    def _css_select(self, html: str, selector: str) -> List[str]:
        """
        简化版 CSS 选择器实现。

        Args:
            html: HTML 内容
            selector: CSS 选择器

        Returns:
            匹配的元素文本列表
        """
        try:
            # 移除 script 和 style 标签内容
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

            # 解析选择器
            selectors = [s.strip() for s in selector.split(',')]
            results = []

            for sel in selectors:
                if not sel:
                    continue

                # 处理标签选择器
                if re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', sel):
                    pattern = rf'<{sel}[^>]*>(.*?)</{sel}>'
                    matches = re.findall(pattern, html, re.DOTALL)
                    results.extend(matches)
                # 处理类选择器
                elif sel.startswith('.'):
                    class_name = sel[1:]
                    pattern = rf'<[^>]*class="[^"]*{re.escape(class_name)}[^"]*"[^>]*>(.*?)</[^>]+>'
                    matches = re.findall(pattern, html, re.DOTALL)
                    results.extend(matches)
                # 处理 ID 选择器
                elif sel.startswith('#'):
                    id_name = sel[1:]
                    pattern = rf'<[^>]*id="[^"]*{re.escape(id_name)}[^"]*"[^>]*>(.*?)</[^>]+>'
                    matches = re.findall(pattern, html, re.DOTALL)
                    results.extend(matches)
                # 处理属性选择器
                elif '[' in sel and ']' in sel:
                    attr_match = re.search(r'\[([^\]]+)\]', sel)
                    if attr_match:
                        attr_expr = attr_match.group(1)
                        if '=' in attr_expr:
                            attr_name, attr_value = attr_expr.split('=', 1)
                            attr_name = attr_name.strip()
                            attr_value = attr_value.strip().strip('"').strip("'")
                            pattern = rf'<[^>]*{re.escape(attr_name)}="[^"]*{re.escape(attr_value)}[^"]*"[^>]*>(.*?)</[^>]+>'
                            matches = re.findall(pattern, html, re.DOTALL)
                            results.extend(matches)
                        else:
                            attr_name = attr_expr.strip()
                            pattern = rf'<[^>]*{re.escape(attr_name)}[^>]*>(.*?)</[^>]+>'
                            matches = re.findall(pattern, html, re.DOTALL)
                            results.extend(matches)
                # 处理组合选择器（简化）
                elif ' ' in sel:
                    parts = sel.split()
                    if len(parts) == 2:
                        parent_sel, child_sel = parts
                        # 简化处理：先找父元素，再找子元素
                        parent_matches = self._css_select(html, parent_sel)
                        for parent in parent_matches:
                            child_matches = self._css_select(parent, child_sel)
                            results.extend(child_matches)

            # 去重并清理
            seen = set()
            unique_results = []
            for r in results:
                cleaned = self._clean_value(r)
                if cleaned and cleaned not in seen:
                    seen.add(cleaned)
                    unique_results.append(cleaned)

            return unique_results[:20]

        except Exception:
            return []

    def _clean_value(self, value: str) -> Optional[str]:
        """
        清理提取的值。

        Args:
            value: 原始值

        Returns:
            清理后的值或 None
        """
        if not value:
            return None

        # 移除 HTML 标签
        value = re.sub(r'<[^>]+>', '', value)
        # 移除多余空白
        value = re.sub(r'\s+', ' ', value).strip()
        # 移除常见噪声
        value = value.replace('&nbsp;', ' ').replace('&amp;', '&')

        if not value or len(value) < 1:
            return None

        return value

    def _clean_html(self, html: str) -> str:
        """
        清理 HTML 内容。

        Args:
            html: 原始 HTML

        Returns:
            清理后的 HTML
        """
        # 移除注释
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        # 移除 script 和 style
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        return html

    def _validate_url(self, url: str) -> bool:
        """
        验证 URL 格式。

        Args:
            url: URL 字符串

        Returns:
            是否有效
        """
        try:
            result = urllib.parse.urlparse(url)
            return result.scheme in ('http', 'https') and bool(result.netloc)
        except Exception:
            return False

    def _fetch_url(self, url: str) -> Optional[str]:
        """
        获取 URL 内容，带重试和指数退避。

        Args:
            url: 目标 URL

        Returns:
            HTML 内容或 None
        """
        for attempt in range(self.retries):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    # 读取内容并尝试解码
                    content = response.read()
                    # 尝试多种编码
                    for encoding in ['utf-8', 'gbk', 'gb18030', 'latin-1']:
                        try:
                            return content.decode(encoding)
                        except (UnicodeDecodeError, LookupError):
                            continue
                    # 最后使用 replace 模式
                    return content.decode('utf-8', errors='replace')

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"警告: URL 返回 404: {url}", file=sys.stderr)
                    return None
                elif e.code == 403:
                    print(f"警告: URL 返回 403 (禁止访问): {url}", file=sys.stderr)
                    return None
                elif e.code == 429:
                    # 限流，等待后重试
                    wait_time = 2 ** attempt
                    print(f"警告: 触发限流，等待 {wait_time} 秒后重试", file=sys.stderr)
                    time.sleep(wait_time)
                else:
                    print(f"警告: HTTP 错误 {e.code}: {url}", file=sys.stderr)
                    if attempt < self.retries - 1:
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                    else:
                        return None

            except urllib.error.URLError as e:
                print(f"警告: URL 错误: {e.reason}", file=sys.stderr)
                if attempt < self.retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    return None

            except Exception as e:
                print(f"警告: 请求失败: {str(e)}", file=sys.stderr)
                if attempt < self.retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    return None

        return None

    def _read_file(self, file_path: str) -> Optional[str]:
        """
        读取文件内容，支持多种编码。

        Args:
            file_path: 文件路径

        Returns:
            文件内容或 None
        """
        try:
            # 尝试多种编码
            for encoding in ['utf-8', 'gbk', 'gb18030', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except (UnicodeDecodeError, LookupError):
                    continue
            # 最后使用 replace 模式
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            print(f"警告: 读取文件失败: {str(e)}", file=sys.stderr)
            return None


# ============================================================
# 输出格式化器
# ============================================================

class OutputFormatter:
    """输出格式化器，支持 JSON、CSV、文本格式"""

    @staticmethod
    def format_json(data: Dict[str, Any]) -> str:
        """格式化为 JSON 字符串"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def format_csv(data: Dict[str, Any]) -> str:
        """格式化为 CSV 字符串"""
        if not data or 'fields' not in data:
            return ""

        fields = data.get('fields', {})
        if not fields:
            return ""

        # 获取所有字段名
        field_names = list(fields.keys())
        if not field_names:
            return ""

        # 确定行数（取最大长度）
        max_rows = max(len(values) for values in fields.values())

        # 生成 CSV
        output = []
        output.append(','.join(field_names))

        for i in range(max_rows):
            row = []
            for field_name in field_names:
                values = fields.get(field_name, [])
                if i < len(values):
                    # 处理包含逗号的值
                    value = str(values[i])
                    if ',' in value or '"' in value:
                        value = '"' + value.replace('"', '""') + '"'
                    row.append(value)
                else:
                    row.append('')
            output.append(','.join(row))

        return '\n'.join(output)

    @staticmethod
    def format_text(data: Dict[str, Any]) -> str:
        """格式化为文本字符串"""
        if not data:
            return ""

        lines = []
        if 'url' in data:
            lines.append(f"URL: {data['url']}")
        if 'timestamp' in data:
            lines.append(f"时间: {data['timestamp']}")

        if 'fields' in data:
            lines.append("\n提取结果:")
            for field_name, values in data['fields'].items():
                lines.append(f"\n{field_name}:")
                for value in values:
                    lines.append(f"  - {value}")

        if 'confidence' in data:
            lines.append(f"\n置信度: {data['confidence']:.2%}")

        if 'warnings' in data and data['warnings']:
            lines.append("\n警告:")
            for warning in data['warnings']:
                lines.append(f"  - {warning}")

        return '\n'.join(lines)


# ============================================================
# 批量处理器
# ============================================================

class BatchProcessor:
    """批量处理多个 URL"""

    def __init__(self, engine: AutoScraperEngine):
        self.engine = engine

    def process_urls(self, urls: List[str], rules: Optional[Dict[str, str]] = None,
                     wanted_fields: Optional[List[str]] = None) -> ProcessingResult:
        """
        批量处理 URL 列表。

        Args:
            urls: URL 列表
            rules: 自定义规则
            wanted_fields: 期望字段

        Returns:
            ProcessingResult 对象
        """
        if not urls:
            return ProcessingResult(
                success=False,
                error_code="E001",
                error_message="URL 列表为空"
            )

        results = []
        warnings = []
        success_count = 0

        for i, url in enumerate(urls):
            try:
                print(f"处理 [{i+1}/{len(urls)}]: {url}", file=sys.stderr)
                result = self.engine.extract_from_url(url, rules=rules, wanted_fields=wanted_fields)

                if result.success:
                    success_count += 1
                    results.append({
                        "url": url,
                        "fields": result.data or {},
                        "confidence": result.confidence
                    })
                else:
                    warnings.append(f"URL {url} 处理失败: {result.error_message}")

            except Exception as e:
                warnings.append(f"URL {url} 处理异常: {str(e)}")

        # 计算总体置信度
        if results:
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
        else:
            avg_confidence = 0.0

        return ProcessingResult(
            success=success_count > 0,
            data={
                "results": results,
                "total": len(urls),
                "success_count": success_count,
                "failed_count": len(urls) - success_count
            },
            confidence=avg_confidence,
            warnings=warnings
        )

    def process_file(self, file_path: str, rules: Optional[Dict[str, str]] = None,
                     wanted_fields: Optional[List[str]] = None) -> ProcessingResult:
        """
        从文件读取 URL 列表并批量处理。

        Args:
            file_path: 文件路径（每行一个 URL）
            rules: 自定义规则
            wanted_fields: 期望字段

        Returns:
            ProcessingResult 对象
        """
        try:
            # 流式读取文件
            urls = []
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        urls.append(url)

            if not urls:
                return ProcessingResult(
                    success=False,
                    error_code="E001",
                    error_message="文件中没有有效的 URL"
                )

            return self.process_urls(urls, rules=rules, wanted_fields=wanted_fields)

        except FileNotFoundError:
            return ProcessingResult(
                success=False,
                error_code="E006",
                error_message=f"文件不存在: {file_path}"
            )
        except Exception as e:
            return ProcessingResult(
                success=False,
                error_code="E010",
                error_message=f"批量处理失败: {str(e)}"
            )


# ============================================================
# 文件写入器（原子写入）
# ============================================================

class FileWriter:
    """文件写入器，支持原子写入"""

    @staticmethod
    def atomic_write(file_path: str, content: str, dry_run: bool = False) -> bool:
        """
        原子写入文件。

        Args:
            file_path: 文件路径
            content: 文件内容
            dry_run: 预览模式，不写盘

        Returns:
            是否成功
        """
        if not dry_run:
            temp_path = f"{file_path}.tmp"
            try:
                # 写入临时文件
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())

                # 原子替换
                os.replace(temp_path, file_path)
                print(f"[写入] {file_path}")
                return True

            except Exception as e:
                print(f"警告: 写入文件失败: {str(e)}", file=sys.stderr)
                # 清理临时文件
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
                return False
        else:
            print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")
            return False


# ============================================================
# 自检模块
# ============================================================

class SelfTest:
    """自检模块，验证核心功能"""

    @staticmethod
    def run() -> bool:
        """
        运行自检。

        Returns:
            是否全部通过
        """
        print("开始自检...")
        all_passed = True

        # 测试 1: 从 HTML 提取数据
        print("\n测试 1: 从 HTML 提取数据")
        try:
            engine = AutoScraperEngine()
            html = """
            <html>
                <body>
                    <h1>测试标题</h1>
                    <div class="price">¥299</div>
                    <div class="price">¥459</div>
                    <p class="description">这是一个测试描述</p>
                </body>
            </html>
            """
            result = engine.extract_from_html(html, rules={"标题": "h1", "价格": ".price"})
            assert result.success, f"提取失败: {result.error_message}"
            assert result.data is not None, "数据为空"
            assert "标题" in result.data, "缺少标题字段"
            assert "价格" in result.data, "缺少价格字段"
            assert len(result.data["价格"]) == 2, f"价格数量错误: {len(result.data['价格'])}"
            assert result.confidence > 0.5, f"置信度太低: {result.confidence}"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 2: 从文本提取数据
        print("\n测试 2: 从文本提取数据")
        try:
            engine = AutoScraperEngine()
            text = """
            商品标题: 测试商品A
            价格: ¥299
            商品标题: 测试商品B
            价格: ¥459
            """
            result = engine.extract_from_text(text, rules={"标题": r"商品标题:\s*(.+)"})
            assert result.success, f"提取失败: {result.error_message}"
            assert result.data is not None, "数据为空"
            assert "标题" in result.data, "缺少标题字段"
            assert len(result.data["标题"]) >= 2, f"标题数量错误: {len(result.data['标题'])}"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 3: URL 验证
        print("\n测试 3: URL 验证")
        try:
            engine = AutoScraperEngine()
            assert engine._validate_url("https://example.com"), "有效 URL 验证失败"
            assert engine._validate_url("http://example.com/path?query=1"), "带参数 URL 验证失败"
            assert not engine._validate_url("not-a-url"), "无效 URL 验证失败"
            assert not engine._validate_url("ftp://example.com"), "非 HTTP URL 验证失败"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 4: 输出格式化
        print("\n测试 4: 输出格式化")
        try:
            formatter = OutputFormatter()
            data = {
                "url": "https://example.com",
                "fields": {"标题": ["测试"], "价格": ["¥299"]},
                "confidence": 0.9
            }

            json_str = formatter.format_json(data)
            assert json_str, "JSON 格式化失败"
            parsed = json.loads(json_str)
            assert parsed["url"] == "https://example.com", "JSON 解析失败"

            csv_str = formatter.format_csv(data)
            assert "标题,价格" in csv_str, "CSV 格式化失败"
            assert "测试,¥299" in csv_str, "CSV 内容错误"

            text_str = formatter.format_text(data)
            assert "URL:" in text_str, "文本格式化失败"
            assert "置信度:" in text_str, "文本缺少置信度"

            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 5: 文件写入
        print("\n测试 5: 文件写入")
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                temp_path = f.name

            success = FileWriter.atomic_write(temp_path, "测试内容")
            assert success, "文件写入失败"

            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "测试内容", "文件内容错误"

            os.remove(temp_path)
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 6: 批量处理
        print("\n测试 6: 批量处理")
        try:
            engine = AutoScraperEngine()
            processor = BatchProcessor(engine)
            result = processor.process_urls(["https://example.com", "https://example.org"])
            assert result.success, f"批量处理失败: {result.error_message}"
            assert result.data is not None, "批量处理数据为空"
            assert "total" in result.data, "缺少 total 字段"
            assert result.data["total"] == 2, f"总数错误: {result.data['total']}"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 7: 空输入处理
        print("\n测试 7: 空输入处理")
        try:
            engine = AutoScraperEngine()
            result = engine.extract_from_html("")
            assert not result.success, "空 HTML 应该失败"
            assert result.error_code == "E001", f"错误码错误: {result.error_code}"

            result = engine.extract_from_text("")
            assert not result.success, "空文本应该失败"
            assert result.error_code == "E001", f"错误码错误: {result.error_code}"

            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 8: 编码处理
        print("\n测试 8: 编码处理")
        try:
            engine = AutoScraperEngine()
            # 测试 GBK 编码
            gbk_text = "测试中文".encode('gbk')
            html = f"<html><body><h1>{gbk_text.decode('gbk')}</h1></body></html>"
            result = engine.extract_from_html(html, rules={"标题": "h1"})
            assert result.success, f"GBK 编码处理失败: {result.error_message}"
            assert result.data and "标题" in result.data, "GBK 编码提取失败"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 9: 超长输入
        print("\n测试 9: 超长输入")
        try:
            engine = AutoScraperEngine()
            # 生成 10000 个字符的 HTML
            long_html = "<html><body>" + "<p>测试内容</p>" * 1000 + "</body></html>"
            result = engine.extract_from_html(long_html, rules={"描述": "p"})
            assert result.success, f"超长输入处理失败: {result.error_message}"
            assert result.data and "描述" in result.data, "超长输入提取失败"
            assert len(result.data["描述"]) > 0, "超长输入提取结果为空"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 10: 中文标点
        print("\n测试 10: 中文标点")
        try:
            engine = AutoScraperEngine()
            html = "<html><body><h1>测试：标题，带标点！</h1></body></html>"
            result = engine.extract_from_html(html, rules={"标题": "h1"})
            assert result.success, f"中文标点处理失败: {result.error_message}"
            assert result.data and "标题" in result.data, "中文标点提取失败"
            assert "测试" in result.data["标题"][0], "中文标点内容错误"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 11: 文件读取（多编码）
        print("\n测试 11: 文件读取（多编码）")
        try:
            import tempfile
            engine = AutoScraperEngine()

            # 测试 UTF-8
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
                f.write("UTF-8 测试内容")
                utf8_path = f.name
            content = engine._read_file(utf8_path)
            assert content == "UTF-8 测试内容", f"UTF-8 读取失败: {content}"
            os.remove(utf8_path)

            # 测试 GBK
            with open(utf8_path, 'wb') as f:
                f.write("GBK 测试内容".encode('gbk'))
            content = engine._read_file(utf8_path)
            assert content == "GBK 测试内容", f"GBK 读取失败: {content}"
            os.remove(utf8_path)

            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 12: 字段别名
        print("\n测试 12: 字段别名")
        try:
            engine = AutoScraperEngine()
            # 测试 "标题" 的别名 "title"
            selector = engine._find_default_selector("title")
            assert selector, "字段别名查找失败"
            assert "h1" in selector, f"别名选择器错误: {selector}"

            # 测试 "价格" 的别名 "price"
            selector = engine._find_default_selector("price")
            assert selector, "价格别名查找失败"
            assert "price" in selector, f"价格选择器错误: {selector}"

            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 13: 批量文件处理
        print("\n测试 13: 批量文件处理")
        try:
            import tempfile
            engine = AutoScraperEngine()
            processor = BatchProcessor(engine)

            # 创建 URL 列表文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("https://example.com\n")
                f.write("https://example.org\n")
                f.write("# 注释行\n")
                f.write("\n")
                f.write("https://example.net\n")
                urls_path = f.name

            result = processor.process_file(urls_path)
            assert result.success, f"批量文件处理失败: {result.error_message}"
            assert result.data is not None, "批量文件处理数据为空"
            assert result.data["total"] == 3, f"URL 数量错误: {result.data['total']}"
            os.remove(urls_path)

            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 14: 时间戳格式
        print("\n测试 14: 时间戳格式")
        try:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).isoformat()
            assert timestamp.endswith("+00:00"), f"时间戳格式错误: {timestamp}"
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 15: 异常处理
        print("\n测试 15: 异常处理")
        try:
            engine = AutoScraperEngine()
            # 无效 URL
            result = engine.extract_from_url("not-a-url")
            assert not result.success, "无效 URL 应该失败"
            assert result.error_code == "E007", f"错误码错误: {result.error_code}"

            # 不存在的文件
            result = engine.extract_from_file("/nonexistent/file.txt")
            assert not result.success, "不存在的文件应该失败"
            assert result.error_code == "E006", f"错误码错误: {result.error_code}"

            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        # 测试 16: dry-run 模式
        print("\n测试 16: dry-run 模式")
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                temp_path = f.name

            # 先删除文件，确保不存在
            if os.path.exists(temp_path):
                os.remove(temp_path)

            # dry-run 模式不写盘
            success = FileWriter.atomic_write(temp_path, "测试内容", dry_run=True)
            assert not success, "dry-run 模式应该返回 False"
            assert not os.path.exists(temp_path), "dry-run 模式不应该写盘"

            # 正常模式写盘
            success = FileWriter.atomic_write(temp_path, "测试内容")
            assert success, "正常模式写入失败"
            assert os.path.exists(temp_path), "正常模式应该写盘"

            os.remove(temp_path)
            print("  ✓ 通过")
        except AssertionError as e:
            print(f"  ✗ 失败: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_passed = False

        print(f"\n自检完成: {'全部通过' if all_passed else '存在失败项'}")
        return all_passed


# ============================================================
# 命令行入口
# ============================================================

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="autoscraper - 网页数据自动采集与结构化提取工具",
        epilog="示例:\n"
               "  python run.py --url https://example.com --want 标题 --want 价格\n"
               "  python run.py --url https://example.com --rules '{\"标题\": \"h1\"}'\n"
               "  python run.py --input urls.txt --want 标题 --output results.json\n"
               "  python run.py --selftest"
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--url", help="目标 URL")
    input_group.add_argument("--input", help="输入文件路径（URL 列表或数据文件）")
    input_group.add_argument("--selftest", action="store_true", help="运行自检")

    # 提取参数
    parser.add_argument("--want", action="append", dest="wanted_fields",
                        help="期望提取的字段名（可多次指定）")
    parser.add_argument("--rules", help="自定义规则 JSON 字符串，如 '{\"标题\": \"h1\"}'")

    # 输出参数
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--format", choices=["json", "csv", "text"], default="json",
                        help="输出格式（默认: json）")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式，只显示不写盘")

    # 网络参数
    parser.add_argument("--timeout", type=int, default=30,
                        help="网络请求超时时间（秒，默认: 30）")
    parser.add_argument("--retries", type=int, default=3,
                        help="网络请求重试次数（默认: 3）")
    parser.add_argument("--user-agent", help="自定义 User-Agent")

    # 其他参数
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="输出详细决策信息")

    return parser


def parse_rules(rules_str: Optional[str]) -> Optional[Dict[str, str]]:
    """
    解析规则 JSON 字符串。

    Args:
        rules_str: 规则 JSON 字符串

    Returns:
        规则字典或 None
    """
    if not rules_str:
        return None

    try:
        rules = json.loads(rules_str)
        if not isinstance(rules, dict):
            print("警告: 规则必须是 JSON 对象", file=sys.stderr)
            return None
        return rules
    except json.JSONDecodeError as e:
        print(f"警告: 规则 JSON 解析失败: {e}", file=sys.stderr)
        return None


def main() -> int:
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = SelfTest.run()
        return 0 if success else 1

    # 解析规则
    rules = parse_rules(args.rules)

    # 创建引擎
    engine = AutoScraperEngine(
        timeout=args.timeout,
        retries=args.retries,
        user_agent=args.user_agent
    )

    # 处理输入
    result: ProcessingResult
    if args.url:
        if args.verbose:
            print(f"处理 URL: {args.url}", file=sys.stderr)
        result = engine.extract_from_url(args.url, rules=rules, wanted_fields=args.wanted_fields)
    elif args.input:
        if args.verbose:
            print(f"处理文件: {args.input}", file=sys.stderr)
        # 检查文件是 URL 列表还是数据文件
        try:
            with open(args.input, 'r', encoding='utf-8', errors='replace') as f:
                first_line = f.readline().strip()
            if first_line.startswith('http://') or first_line.startswith('https://'):
                # URL 列表文件
                processor = BatchProcessor(engine)
                result = processor.process_file(args.input, rules=rules, wanted_fields=args.wanted_fields)
            else:
                # 数据文件
                result = engine.extract_from_file(args.input, rules=rules, wanted_fields=args.wanted_fields)
        except Exception as e:
            result = ProcessingResult(
                success=False,
                error_code="E006",
                error_message=f"文件处理失败: {str(e)}"
            )
    else:
        parser.error("必须指定 --url 或 --input")

    # 处理结果
    if not result.success:
        print(f"错误 [{result.error_code}]: {result.error_message}", file=sys.stderr)
        return 1

    # 构建输出数据
    output_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": result.data or {},
        "confidence": result.confidence,
        "warnings": result.warnings
    }

    if args.url:
        output_data["url"] = args.url
    elif args.input:
        output_data["input"] = args.input

    # 格式化输出
    formatter = OutputFormatter()
    if args.format == "json":
        output_str = formatter.format_json(output_data)
    elif args.format == "csv":
        output_str = formatter.format_csv(output_data)
    else:
        output_str = formatter.format_text(output_data)

    # 输出
    if args.dry_run:
        # 预览模式，不写盘
        print("=== 预览模式（不写盘）===")
        print(output_str)
        if args.output:
            print(f"\n[预览] 将写入文件: {args.output}")
        return 0

    if args.output:
        # 写入文件
        success = FileWriter.atomic_write(args.output, output_str, dry_run=args.dry_run)
        if not success:
            print(f"错误 [E009]: 无法写入文件: {args.output}", file=sys.stderr)
            return 1
        if args.verbose:
            print(f"已写入文件: {args.output}", file=sys.stderr)
    else:
        # 输出到 stdout
        print(output_str)

    # 输出警告
    if result.warnings and args.verbose:
        print("\n警告:", file=sys.stderr)
        for warning in result.warnings:
            print(f"  - {warning}", file=sys.stderr)

    # R6 可解释输出：verbose 模式下输出明细
    if args.verbose:
        changed_items = []
        skipped = 0
        if result.data:
            for field_name, values in result.data.items():
                for value in values:
                    changed_items.append({
                        "name": field_name,
                        "before": "未提取",
                        "after": value
                    })
        if result.warnings:
            skipped = len(result.warnings)
        for idx, item in enumerate(changed_items, 1):
            print(f"[明细] {idx}. {item['name']}: {item['before']} -> {item['after']}")
        print(f"[汇总] changed={len(changed_items)} 项，skipped={skipped} 项")

    return 0


if __name__ == "__main__":
    sys.exit(main())
