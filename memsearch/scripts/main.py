#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memsearch — 跨会话持久化记忆检索（Clean-Room 重写实现）

基于功能规格独立实现，不参考任何既有代码。
提供数据摄入、关键信息提取、语义检索、置信度标注等核心能力。
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import tempfile
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# 全局 dry-run 标志（通过命令行参数或环境变量控制）
dry_run = False

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数类型不正确",
    "E002": "输入数据为空或格式不合法",
    "E003": "文件读取失败",
    "E004": "URL 抓取失败（网络不可达或响应异常）",
    "E005": "向量化失败：特征提取异常",
    "E006": "记忆库写入失败",
    "E007": "记忆库查询失败",
    "E008": "删除操作失败：条件不明确或 ID 不存在",
    "E009": "批量处理中断：部分条目处理失败",
    "E010": "内部状态异常：未预期的错误",
}


def make_error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误返回结构"""
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": ERROR_CODES.get(code, "未知错误"),
            "detail": detail,
        },
    }


def make_success(data: Any = None) -> Dict[str, Any]:
    """构造标准成功返回结构"""
    return {"ok": True, "data": data}


# ============================================================
# 数据模型
# ============================================================

@dataclass
class MemoryEntry:
    """记忆条目数据模型"""
    content: str
    entry_id: str = ""
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    source: str = ""
    confidence: float = 0.0

    def __post_init__(self):
        # 输入验证：content 不能为空
        if not self.content or not self.content.strip():
            raise ValueError("content 不能为空")
        
        if not self.entry_id:
            # 基于内容生成稳定 ID（去重依据）
            raw = self.content.strip()
            self.entry_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        if not self.timestamp:
            # 使用 UTC 时间戳
            self.timestamp = datetime.now(timezone.utc).timestamp()
        if not self.confidence:
            # 默认置信度：基于内容长度给出基础值
            length_factor = min(1.0, len(self.content) / 200.0)
            self.confidence = round(0.5 + 0.4 * length_factor, 4)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """检索结果条目"""
    entry: MemoryEntry
    score: float  # 相似度 0~1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry": self.entry.to_dict(),
            "score": round(self.score, 4),
            "confidence": round(self.entry.confidence, 4),
        }


# ============================================================
# 核心算法：特征提取与相似度计算
# ============================================================

class TextVectorizer:
    """
    轻量级文本向量化器（基于字符 n-gram 哈希）
    不依赖第三方库，纯标准库实现。
    """

    def __init__(self, dim: int = 256, ngram: int = 3):
        self.dim = dim
        self.ngram = ngram

    def vectorize(self, text: str) -> List[float]:
        """将文本转换为固定维度向量（L2 归一化）"""
        if not text or not text.strip():
            return [0.0] * self.dim

        # 预处理：统一小写、去除多余空白
        normalized = re.sub(r"\s+", " ", text.strip().lower())

        # 生成 n-gram 特征
        features = []
        if len(normalized) <= self.ngram:
            features.append(normalized)
        else:
            for i in range(len(normalized) - self.ngram + 1):
                features.append(normalized[i : i + self.ngram])

        # 哈希到向量空间
        vec = [0.0] * self.dim
        for feat in features:
            digest = hashlib.md5(feat.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign

        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """计算两个向量的余弦相似度（0~1）"""
        if len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        # 向量已归一化，直接返回点积
        return max(0.0, min(1.0, dot))


class KeywordExtractor:
    """关键词/实体提取器（基于规则）"""

    # 常见实体模式（简化版）
    ENTITY_PATTERNS = [
        (r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", "person_or_org"),  # 人名/组织名
        (r"\b\d{4}-\d{2}-\d{2}\b", "date"),
        (r"\b\d{1,2}:\d{2}\b", "time"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
        (r"\bhttps?://[^\s]+", "url"),
        (r"\b\d{3}-\d{3,4}-\d{4}\b", "phone"),
    ]

    # 停用词（英文）
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "if", "then", "else",
        "for", "while", "with", "without", "from", "to", "of", "in",
        "on", "at", "by", "is", "are", "was", "were", "be", "been",
        "this", "that", "these", "those", "it", "its",
    }

    def extract_entities(self, text: str) -> List[str]:
        """提取文本中的命名实体"""
        entities = []
        for pattern, etype in self.ENTITY_PATTERNS:
            for match in re.finditer(pattern, text):
                value = match.group()
                if value not in entities:
                    entities.append(f"{value} ({etype})")
        return entities[:10]  # 最多 10 个

    def extract_tags(self, text: str) -> List[str]:
        """提取主题标签（高频词）"""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        freq: Dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        # 按频率排序，取前 5 个
        sorted_words = sorted(freq.items(), key=lambda x: -x[1])
        return [w for w, _ in sorted_words[:5]]


class MemoryStore:
    """
    记忆存储层（基于结构化 JSON 文件）
    实际生产环境可替换为 Milvus + 文件系统，此处提供纯标准库实现。
    """

    def __init__(self, storage_path: str = ""):
        self.storage_path = storage_path
        self.entries: Dict[str, MemoryEntry] = {}
        self.vectorizer = TextVectorizer()
        self.keyword_extractor = KeywordExtractor()
        self._vector_cache: Dict[str, List[float]] = {}

    # ---- 存储操作 ----

    def add_entry(self, content: str, source: str = "", tags: Optional[List[str]] = None) -> Tuple[bool, str, str]:
        """添加记忆条目，返回 (是否新增, entry_id, 错误码或空串)"""
        if not content or not content.strip():
            return False, "", "E002"

        try:
            entry = MemoryEntry(
                content=content.strip(),
                source=source,
                tags=tags or [],
            )
            # 提取关键信息
            entry.entities = self.keyword_extractor.extract_entities(entry.content)
            if not entry.tags:
                entry.tags = self.keyword_extractor.extract_tags(entry.content)

            # 去重检查
            if entry.entry_id in self.entries:
                return False, entry.entry_id, ""

            self.entries[entry.entry_id] = entry
            self._vector_cache[entry.entry_id] = self.vectorizer.vectorize(entry.content)
            return True, entry.entry_id, ""
        except Exception as e:
            return False, "", f"E006: {str(e)}"

    def delete_entry(self, entry_id: str) -> Tuple[bool, str]:
        """删除记忆条目"""
        if not entry_id:
            return False, "E008"
        if entry_id not in self.entries:
            return False, "E008"
        del self.entries[entry_id]
        self._vector_cache.pop(entry_id, None)
        return True, ""

    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """获取单条记忆"""
        return self.entries.get(entry_id)

    def list_entries(self) -> List[MemoryEntry]:
        """列出所有记忆"""
        return list(self.entries.values())

    def count(self) -> int:
        """记忆条目数量"""
        return len(self.entries)

    # ---- 检索操作 ----

    def search(self, query: str, top_k: int = 5, min_score: float = 0.1) -> List[SearchResult]:
        """语义检索：返回按相似度排序的结果列表"""
        if not query or not query.strip():
            return []

        query_vec = self.vectorizer.vectorize(query)
        results: List[SearchResult] = []

        for entry_id, entry in self.entries.items():
            # 获取缓存向量，如无则重新计算
            vec = self._vector_cache.get(entry_id)
            if vec is None:
                vec = self.vectorizer.vectorize(entry.content)
                self._vector_cache[entry_id] = vec
            score = self.vectorizer.cosine_similarity(query_vec, vec)
            if score >= min_score:
                results.append(SearchResult(entry=entry, score=score))

        # 按分数降序排列
        results.sort(key=lambda r: -r.score)
        return results[:top_k]

    def keyword_search(self, keyword: str, top_k: int = 5) -> List[SearchResult]:
        """关键词检索：基于内容包含匹配"""
        if not keyword:
            return []
        keyword_lower = keyword.lower()
        results = []
        for entry in self.entries.values():
            if keyword_lower in entry.content.lower():
                # 简单匹配分数：基于位置和频率
                occurrences = entry.content.lower().count(keyword_lower)
                score = min(1.0, 0.3 + 0.1 * occurrences)
                results.append(SearchResult(entry=entry, score=score))
        results.sort(key=lambda r: -r.score)
        return results[:top_k]

    # ---- 持久化 ----

    def save(self, path: str = "") -> Tuple[bool, str]:
        """保存记忆库到 JSON 文件"""
        target = path or self.storage_path
        if not target:
            return False, "E006: 未指定存储路径"

        try:
            data = {
                "version": "1.0.1",
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "entries": [e.to_dict() for e in self.entries.values()],
            }
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True, ""
        except Exception as e:
            return False, f"E006: {str(e)}"

    def load(self, path: str = "") -> Tuple[bool, str]:
        """从 JSON 文件加载记忆库"""
        target = path or self.storage_path
        if not target:
            return False, "E003: 未指定加载路径"

        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.entries.clear()
            self._vector_cache.clear()
            for item in data.get("entries", []):
                entry = MemoryEntry(
                    content=item["content"],
                    entry_id=item.get("entry_id", ""),
                    tags=item.get("tags", []),
                    entities=item.get("entities", []),
                    timestamp=item.get("timestamp", 0.0),
                    source=item.get("source", ""),
                    confidence=item.get("confidence", 0.0),
                )
                self.entries[entry.entry_id] = entry
                self._vector_cache[entry.entry_id] = self.vectorizer.vectorize(entry.content)
            return True, ""
        except FileNotFoundError:
            return False, "E003: 文件不存在"
        except Exception as e:
            return False, f"E003: {str(e)}"


# ============================================================
# 网络请求工具（带重试、退避、超时）
# ============================================================

def fetch_url_with_retry(url: str, max_retries: int = 3, timeout: int = 10) -> str:
    """
    带重试和指数退避的 URL 抓取
    """
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "memsearch/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            if attempt == max_retries - 1:
                raise
            # 指数退避
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    raise RuntimeError(f"URL 抓取失败: {url}")


# ============================================================
# 高层 API
# ============================================================

class MemSearch:
    """memsearch 技能主入口"""

    def __init__(self, storage_path: str = ""):
        self.store = MemoryStore(storage_path)

    def ingest(self, data: Any, source: str = "user_input", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        数据摄入：接受字符串、文件路径或 URL
        返回结构化结果
        """
        try:
            # 类型判断与内容提取
            content = ""
            if isinstance(data, str):
                # 判断是否为 URL
                if data.startswith("http://") or data.startswith("https://"):
                    # URL 抓取（带重试和超时）
                    try:
                        content = fetch_url_with_retry(data, max_retries=3, timeout=10)
                        source = f"url:{data}"
                    except Exception as e:
                        return make_error("E004", str(e))
                # 判断是否为文件路径（更严格的条件）
                elif self._is_file_path(data):
                    try:
                        with open(data, "r", encoding="utf-8") as f:
                            content = f.read()
                        source = f"file:{data}"
                    except Exception as e:
                        return make_error("E003", str(e))
                else:
                    # 直接文本
                    content = data
            elif isinstance(data, dict) and "content" in data:
                content = data["content"]
                source = data.get("source", source)
                tags = data.get("tags", tags)
            elif isinstance(data, list):
                # 批量摄入（并发处理）
                return self._batch_ingest(data, source, tags)

            if not content or not content.strip():
                return make_error("E002")

            ok, eid, err = self.store.add_entry(content, source=source, tags=tags)
            if not ok and err:
                return make_error(err.split(":")[0] if ":" in err else "E006", err)

            entry = self.store.get_entry(eid)
            if entry is None:
                return make_error("E010", "条目写入后无法读取")

            return make_success({
                "entry_id": eid,
                "is_new": ok,
                "entry": entry.to_dict(),
                "tags": entry.tags,
                "entities": entry.entities,
                "confidence": entry.confidence,
            })
        except Exception as e:
            return make_error("E010", str(e))

    def _batch_ingest(self, items: List[Any], source: str, tags: Optional[List[str]]) -> Dict[str, Any]:
        """
        批量摄入：使用线程池并发处理
        """
        results = []
        success_count = 0

        def process_item(item):
            if isinstance(item, str):
                return self.store
