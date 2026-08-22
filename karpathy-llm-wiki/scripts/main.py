#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Karpathy LLM Wiki 知识库构建与结构化输出工具

独立实现（clean-room），仅依据功能规格编写。
功能：
  - 多源文本输入解析（文本、文件、URL）
  - 关键信息识别（实体、概念、关系、时间、数据指标）
  - 结构化输出（Markdown / JSON 知识条目）
  - 置信度标注（高/中/低，基于规则动态计算）
  - 批量合并处理（支持并发与缓存）
  - 内置自检（--selftest），离线运行，不读外部文件、不访问网络
"""

import argparse
import json
import os
import re
import sys
import tempfile
import hashlib
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 输入为空
# E002: 输入不是字符串
# E003: JSON 序列化失败
# E004: 输出目录不可写
# E005: 参数冲突
# E006: 内部逻辑错误（自检失败）
# E007: 不支持的文件类型
# E008: 文件读取失败
# E009: 输出格式不支持
# E010: 未知异常
# E011: URL 请求失败

ERROR_CODES = {
    "E001": "输入为空",
    "E002": "输入不是字符串",
    "E003": "JSON 序列化失败",
    "E004": "输出目录不可写",
    "E005": "参数冲突",
    "E006": "内部逻辑错误（自检失败）",
    "E007": "不支持的文件类型",
    "E008": "文件读取失败",
    "E009": "输出格式不支持",
    "E010": "未知异常",
    "E011": "URL 请求失败",
}


class SkillError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class KnowledgeEntry:
    """知识条目：一个结构化知识单元。"""

    def __init__(
        self,
        title: str,
        content: str,
        entities: Optional[List[str]] = None,
        concepts: Optional[List[str]] = None,
        relations: Optional[List[Dict[str, str]]] = None,
        timestamps: Optional[List[str]] = None,
        metrics: Optional[List[Dict[str, Any]]] = None,
        confidence: Optional[str] = None,
    ):
        self.title = title.strip()
        self.content = content.strip()
        self.entities = entities or []
        self.concepts = concepts or []
        self.relations = relations or []
        self.timestamps = timestamps or []
        self.metrics = metrics or []
        # 动态计算置信度，不依赖固定默认值
        self.confidence = confidence or _determine_confidence(self.content, self)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "title": self.title,
            "content": self.content,
            "entities": self.entities,
            "concepts": self.concepts,
            "relations": self.relations,
            "timestamps": self.timestamps,
            "metrics": self.metrics,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式。"""
        lines = [f"## {self.title}", "", self.content, ""]
        if self.entities:
            lines.append("**实体:** " + ", ".join(self.entities))
        if self.concepts:
            lines.append("**概念:** " + ", ".join(self.concepts))
        if self.relations:
            lines.append("**关系:**")
            for rel in self.relations:
                lines.append(
                    f"- {rel.get('from', '?')} --[{rel.get('type', '?')}]--> {rel.get('to', '?')}"
                )
        if self.timestamps:
            lines.append("**时间:** " + ", ".join(self.timestamps))
        if self.metrics:
            lines.append("**数据指标:**")
            for m in self.metrics:
                lines.append(
                    f"- {m.get('name', '?')}: {m.get('value', '?')} {m.get('unit', '')}"
                )
        lines.append(f"\n*置信度: {self.confidence}*\n")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML 解析器（用于 URL 内容提取）
# ---------------------------------------------------------------------------

class HTMLTextExtractor(HTMLParser):
    """提取 HTML 中的文本内容和标题。"""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._skip_tags = {"script", "style", "nav", "footer", "header"}

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self._skip_tags:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif self._skip_depth == 0:
            if data.strip():
                self.text_parts.append(data.strip())

    def get_text(self) -> str:
        return "\n".join(self.text_parts)


def extract_html_content(html: str) -> Tuple[str, str]:
    """从 HTML 中提取标题和正文文本。"""
    parser = HTMLTextExtractor()
    try:
        parser.feed(html)
    except Exception:
        # 解析失败时降级为纯文本
        return "", html
    return parser.title, parser.get_text()


# ---------------------------------------------------------------------------
# 文本解析与信息抽取
# ---------------------------------------------------------------------------

# 实体识别：常见专有名词（大写开头词、引号内术语）
_ENTITY_PATTERN = re.compile(
    r"(?<![A-Za-z])([A-Z][a-zA-Z]{2,}(?:\s[A-Z][a-zA-Z]{2,}){0,3})"
)

# 时间识别：年份、日期
_TIME_PATTERN = re.compile(
    r"(?:19|20)\d{2}(?:[-/年]\d{1,2}(?:[-/月]\d{1,2}日?)?)?"
)

# 数据指标：数字 + 单位
_METRIC_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(%|万|亿|元|美元|人|次|篇|个|GB|MB|TB|ms|秒|分钟|小时)"
)

# 概念词：常见技术/领域术语（简化版）
_CONCEPT_KEYWORDS = [
    "架构", "模型", "算法", "系统", "框架", "协议", "数据库", "网络",
    "机器学习", "深度学习", "知识库", "接口", "API", "分布式", "缓存",
    "索引", "检索", "生成", "推理", "训练", "推理", "向量", "嵌入",
]

# 来源可靠性权重（用于置信度计算）
_SOURCE_RELIABILITY = {
    "官方文档": 0.9,
    "学术论文": 0.85,
    "技术博客": 0.7,
    "社区讨论": 0.5,
    "未知": 0.3,
}


def _extract_entities(text: str) -> List[str]:
    """提取实体（专有名词）。"""
    found = _ENTITY_PATTERN.findall(text)
    # 过滤掉常见非实体词
    stop_words = {"The", "This", "That", "These", "Those", "And", "But", "For", "With"}
    result = []
    for item in found:
        if item in stop_words:
            continue
        if item not in result:
            result.append(item)
    return result[:10]  # 最多返回 10 个


def _extract_timestamps(text: str) -> List[str]:
    """提取时间信息。"""
    return list(dict.fromkeys(_TIME_PATTERN.findall(text)))[:5]


def _extract_metrics(text: str) -> List[Dict[str, Any]]:
    """提取数据指标。"""
    result = []
    for match in _METRIC_PATTERN.findall(text):
        value, unit = match
        item = {"name": "指标", "value": value, "unit": unit}
        if item not in result:
            result.append(item)
    return result[:8]


def _extract_concepts(text: str) -> List[str]:
    """提取概念（基于关键词匹配）。"""
    found = []
    for kw in _CONCEPT_KEYWORDS:
        if kw in text and kw not in found:
            found.append(kw)
    return found[:8]


def _extract_relations(text: str) -> List[Dict[str, str]]:
    """提取简单关系（基于模式匹配：A 的 B / A 是 B / A 包含 B）。"""
    relations = []
    patterns = [
        re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,20})的([\u4e00-\u9fa5A-Za-z]{2,20})"),
        re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,20})(?:是|为)([\u4e00-\u9fa5A-Za-z]{2,20})"),
        re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,20})(?:包含|包括|含有)([\u4e00-\u9fa5A-Za-z]{2,20})"),
    ]
    for pat in patterns:
        for m in pat.finditer(text):
            rel = {"from": m.group(1), "type": "关联", "to": m.group(2)}
            if rel not in relations:
                relations.append(rel)
    return relations[:5]


def _determine_confidence(text: str, entry: KnowledgeEntry, source: str = "未知") -> str:
    """基于规则和统计的置信度评估函数。

    评分因素：
    - 文本长度（内容充实度）
    - 实体密度（信息丰富度）
    - 概念数量（领域覆盖度）
    - 时间/指标存在（数据完整度）
    - 来源可靠性（外部输入）
    """
    score = 0.0

    # 1. 文本长度评分（0-1分）
    text_len = len(entry.content)
    if text_len > 200:
        score += 1.0
    elif text_len > 100:
        score += 0.7
    elif text_len > 50:
        score += 0.4
    else:
        score += 0.1

    # 2. 实体密度评分（0-1分）
    entity_density = len(entry.entities) / max(1, text_len / 100)
    score += min(1.0, entity_density * 0.5)

    # 3. 概念数量评分（0-1分）
    concept_score = min(1.0, len(entry.concepts) / 3)
    score += concept_score * 0.5

    # 4. 时间/指标存在评分（0-1分）
    data_completeness = 0.0
    if entry.timestamps:
        data_completeness += 0.5
    if entry.metrics:
        data_completeness += 0.5
    score += data_completeness

    # 5. 来源可靠性评分（0-1分）
    source_score = _SOURCE_RELIABILITY.get(source, 0.3)
    score += source_score

    # 归一化到 0-1 范围
    max_score = 5.0
    normalized = score / max_score

    # 映射到高/中/低
    if normalized >= 0.7:
        return "高"
    elif normalized >= 0.4:
        return "中"
    else:
        return "低"


# ---------------------------------------------------------------------------
# 缓存与并发支持
# ---------------------------------------------------------------------------

class DiskCache:
    """简单的磁盘缓存实现，用于批量处理结果缓存。"""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "karpathy_llm_wiki_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        """根据 key 生成缓存文件路径。"""
        hash_key = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    def get(self, key: str) -> Optional[str]:
        """从缓存获取数据。"""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return f.read()
            except (OSError, IOError):
                return None
        return None

    def set(self, key: str, value: str) -> None:
        """写入缓存。"""
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(value)
        except (OSError, IOError):
            pass  # 缓存写入失败不影响主流程


@lru_cache(maxsize=128)
def _cached_parse(text: str, title: str) -> str:
    """带缓存的文本解析，返回 JSON 字符串。"""
    entries = parse_text_to_entries(text, title=title or None)
    return json.dumps([e.to_dict() for e in entries], ensure_ascii=False)


def _process_single_document(doc: Dict[str, str], output_format: str) -> Optional[str]:
    """处理单个文档（供并发调用）。"""
    try:
        title = doc.get("title", "")
        content = doc.get("content", "")
        if not content:
            return None

        # 使用缓存键
        cache_key = f"{title}:{content[:100]}:{output_format}"
        cache = DiskCache()
        cached = cache.get(cache_key)
        if cached:
            return cached

        # 解析并生成输出
        entries = parse_text_to_entries(content, title=title or None)
        output = generate_output(entries, output_format)

        # 写入缓存
        cache.set(cache_key, output)
        return output
    except Exception:
        # 失败降级：跳过错误条目继续处理
        return None


def process_batch(documents: List[Dict[str, str]], output_format: str = "markdown", max_workers: int = 4) -> List[str]:
    """批量处理文档，使用线程池并发执行。

    参数:
        documents: 文档列表，每个文档为 {"title": str, "content": str}
        output_format: 输出格式 ("markdown" 或 "json")
        max_workers: 最大并发数

    返回:
        处理后的输出字符串列表
    """
    if not documents:
        return []

    results: List[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_doc = {
            executor.submit(_process_single_document, doc, output_format): doc
            for doc in documents
        }

        # 按完成顺序收集结果
        for future in as_completed(future_to_doc):
            result = future.result()
            if result is not None:
                results.append(result)

    return results


# ---------------------------------------------------------------------------
# URL 处理函数
# ---------------------------------------------------------------------------

def fetch_url_content(url: str, timeout: int = 10, max_retries: int = 3) -> Tuple[str, str]:
    """获取 URL 内容，支持超时、重试和错误处理。

    返回 (标题, 正文文本)
    """
    if not url.startswith(("http://", "https://")):
        raise SkillError("E011", f"不支持的 URL 协议: {url}")

    retry_delay = 1.0  # 初始重试延迟（秒）
    last_error = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 检查响应状态
                if response.status != 200:
                    raise urllib.error.URLError(f"HTTP {response.status}")

                # 读取内容
                content_type = response.headers.get("Content-Type", "")
                if "html" in content_type.lower():
                    html_content = response.read().decode("utf-8", errors="ignore")
                    title, text = extract_html_content(html_content)
                    return title, text
                else:
                    # 非 HTML 内容，直接作为纯文本处理
                    text = response.read().decode("utf-8", errors="ignore")
                    return "", text

        except urllib.error.URLError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
                continue
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay
