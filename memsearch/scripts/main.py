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
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

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
        if not self.entry_id:
            # 基于内容生成稳定 ID（去重依据）
            raw = self.content.strip()
            self.entry_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        if not self.timestamp:
            self.timestamp = time.time()
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
                "saved_at": time.time(),
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
                    # URL 抓取（简化处理）
                    try:
                        import urllib.request

                        with urllib.request.urlopen(data, timeout=10) as resp:
                            content = resp.read().decode("utf-8", errors="ignore")
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
                # 批量摄入
                results = []
                success_count = 0
                for item in data:
                    if isinstance(item, str):
                        ok, eid, err = self.store.add_entry(item, source=source, tags=tags)
                    elif isinstance(item, dict) and "content" in item:
                        ok, eid, err = self.store.add_entry(
                            item["content"],
                            source=item.get("source", source),
                            tags=item.get("tags", tags),
                        )
                    else:
                        ok, eid, err = False, "", "E002"
                    if ok:
                        success_count += 1
                    results.append({"ok": ok, "entry_id": eid, "error": err})

                if success_count < len(results):
                    return make_error("E009", f"成功 {success_count}/{len(results)}")
                return make_success({"count": success_count, "results": results})

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

    def _is_file_path(self, text: str) -> bool:
        """更严格地判断是否为文件路径"""
        # 文本长度限制（文件路径通常不会太长）
        if len(text) > 200:
            return False
        
        # 文件路径通常包含特定模式
        # 检查是否包含换行符（多行文本不是文件路径）
        if '\n' in text:
            return False
            
        # 检查是否包含空格（文件路径通常无空格，除非是带空格的路径）
        # 但这里我们保守处理，如果包含空格且不是以 / 或 \ 开头，可能是普通文本
        if ' ' in text and not text.startswith(('C:\\', 'D:\\', '/', '~/')):
            return False
            
        # 包含文件扩展名或路径分隔符
        has_path_sep = '/' in text or '\\' in text
        has_extension = bool(re.search(r'\.[a-zA-Z]{1,5}$', text))
        
        # 纯文件名模式（如 data.txt）
        is_simple_file = bool(re.match(r'^[\w\-\.]+\.(txt|md|json|csv|log|dat)$', text))
        
        return has_path_sep or has_extension or is_simple_file

    def search(self, query: str, top_k: int = 5, mode: str = "semantic") -> Dict[str, Any]:
        """
        语义检索：支持 semantic（向量）和 keyword（关键词）两种模式
        """
        try:
            if mode == "semantic":
                results = self.store.search(query, top_k=top_k)
            elif mode == "keyword":
                results = self.store.keyword_search(query, top_k=top_k)
            else:
                return make_error("E001", f"不支持的检索模式: {mode}")

            return make_success({
                "query": query,
                "mode": mode,
                "count": len(results),
                "results": [r.to_dict() for r in results],
            })
        except Exception as e:
            return make_error("E007", str(e))

    def delete(self, entry_id: str) -> Dict[str, Any]:
        """删除指定记忆条目"""
        ok, err = self.store.delete_entry(entry_id)
        if not ok:
            return make_error("E008", err)
        return make_success({"deleted": entry_id})

    def list_all(self) -> Dict[str, Any]:
        """列出所有记忆"""
        entries = self.store.list_entries()
        return make_success({
            "count": len(entries),
            "entries": [e.to_dict() for e in entries],
        })

    def info(self) -> Dict[str, Any]:
        """返回技能信息与统计"""
        return make_success({
            "name": "memsearch",
            "version": "1.0.1",
            "displayName": "记忆检索 跨会话持久化 语义查询",
            "description": "基于Markdown与Milvus的统一记忆层，为AI代理提供持久化语义检索。",
            "stats": {
                "total_entries": self.store.count(),
                "storage_path": self.store.storage_path or "(内存模式)",
            },
        })

    def save(self, path: str = "") -> Dict[str, Any]:
        """持久化保存"""
        ok, err = self.store.save(path)
        if not ok:
            return make_error("E006", err)
        return make_success({"saved_to": path or self.store.storage_path})

    def load(self, path: str = "") -> Dict[str, Any]:
        """加载持久化数据"""
        ok, err = self.store.load(path)
        if not ok:
            return make_error("E003", err)
        return make_success({"loaded_from": path or self.store.storage_path})


# ============================================================
# 命令行接口
# ============================================================

def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    不读取外部文件、不访问网络、不依赖工作目录
    """
    print("[selftest] 开始自检...")
    ms = MemSearch()

    # ---- 测试 1: 数据摄入 ----
    print("[selftest] 测试数据摄入...")
    test_data = [
        "张三在2024年3月15日召开了项目启动会议，讨论了AI记忆系统架构设计。",
        "李四的邮箱是 zhangsan@example.com，电话是 123-4567-8901。",
        "项目计划在Q3完成beta版本，目标用户是AI开发者社区。",
        "记忆检索系统需要支持跨会话持久化和语义相似度查询。",
        "Milvus是开源的向量数据库，适合处理大规模向量检索任务。",
        "Python的dataclass模块可以简化数据模型定义，提升代码可读性。",
        "2024年6月1日，团队决定采用微服务架构重构现有系统。",
        "用户反馈：语义检索准确率需要提升，尤其是长尾查询场景。",
    ]
    ingest_count = 0
    for item in test_data:
        result = ms.ingest(item, source="selftest")
        if result["ok"]:
            ingest_count += 1
        else:
            print(f"  [警告] 摄入失败: {result}")
    # 断言：至少成功 7/8
    assert ingest_count >= 7, f"摄入成功率过低: {ingest_count}/8"
    print(f"  [通过] 摄入 {ingest_count} 条")

    # ---- 测试 2: 去重 ----
    print("[selftest] 测试去重...")
    result = ms.ingest(test_data[0], source="selftest_dup")
    # 重复内容不应新增
    assert ms.store.count() == ingest_count, f"去重失败: {ms.store.count()} != {ingest_count}"
    print("  [通过] 去重正常")

    # ---- 测试 3: 语义检索 ----
    print("[selftest] 测试语义检索...")
    result = ms.search("向量数据库检索", top_k=3)
    assert result["ok"], f"检索失败: {result}"
    results = result["data"]["results"]
    assert len(results) > 0, "检索结果为空"
    # 宽松断言：结果数不超过请求数
    assert len(results) <= 3, f"返回数量超限: {len(results)}"
    # 分数应在合理范围
    for r in results:
        assert 0.0 <= r["score"] <= 1.0, f"分数越界: {r['score']}"
    print(f"  [通过] 检索到 {len(results)} 条结果")

    # ---- 测试 4: 关键词检索 ----
    print("[selftest] 测试关键词检索...")
    result = ms.search("Python", top_k=5, mode="keyword")
    assert result["ok"], f"关键词检索失败: {result}"
    kw_results = result["data"]["results"]
    assert len(kw_results) > 0, "关键词检索结果为空"
    print(f"  [通过] 关键词检索到 {len(kw_results)} 条结果")

    # ---- 测试 5: 删除 ----
    print("[selftest] 测试删除...")
    all_entries = ms.list_all()["data"]["entries"]
    if all_entries:
        target_id = all_entries[0]["entry_id"]
        result = ms.delete(target_id)
        assert result["ok"], f"删除失败: {result}"
        # 验证条目确实被删除
        assert ms.store.get_entry(target_id) is None, "删除后条目仍存在"
        print(f"  [通过] 删除条目 {target_id}")

    # ---- 测试 6: 实体与标签提取 ----
    print("[selftest] 测试信息提取...")
    result = ms.ingest("联系王五（wangwu@test.com）关于2024年8月的技术评审会议。", source="selftest_extract")
    assert result["ok"], f"摄入失败: {result}"
    entry = result["data"]["entry"]
    assert len(entry["entities"]) > 0, "未提取到实体"
    assert len(entry["tags"]) > 0, "未提取到标签"
    print(f"  [通过] 实体: {entry['entities'][:3]}, 标签: {entry['tags'][:3]}")

    # ---- 测试 7: 持久化 ----
    print("[selftest] 测试持久化...")
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "mem_test.json")
        result = ms.save(save_path)
        assert result["ok"], f"保存失败: {result}"

        # 新建实例加载
        ms2 = MemSearch()
        result = ms2.load(save_path)
        assert result["ok"], f"加载失败: {result}"
        assert ms2.store.count() == ms.store.count(), f"加载数量不一致: {ms2.store.count()} != {ms.store.count()}"
        print("  [通过] 保存/加载正常")

    # ---- 测试 8: 错误处理 ----
    print("[selftest] 测试错误处理...")
    result = ms.search("", top_k=5)
    # 空查询可能返回空结果或错误，但不应该崩溃
    assert "error" not in result or result["error"]["code"] in ["E001", "E007"], f"意外错误: {result}"
    print("  [通过] 错误处理正常")

    print("\n[selftest] 全部自检通过 ✓")
    return 0


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="memsearch — 跨会话持久化记忆检索",
        prog="memsearch",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部资源）",
    )
    parser.add_argument(
        "--ingest",
        type=str,
        help="摄入文本内容",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件摄入内容",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="语义检索查询",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        help="关键词检索查询",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="检索返回条数（默认 5）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有记忆条目",
    )
    parser.add_argument(
        "--delete",
        type=str,
        help="删除指定 ID 的记忆条目",
    )
    parser.add_argument(
        "--save",
        type=str,
        help="保存记忆库到指定路径",
    )
    parser.add_argument(
        "--load",
        type=str,
        help="从指定路径加载记忆库",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="显示技能信息",
    )
    parser.add_argument(
        "--storage",
        type=str,
        default="",
        help="记忆库存储路径（默认内存模式）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"[selftest] 失败: {e}")
            return 1
        except Exception as e:
            print(f"[selftest] 异常: {e}")
            return 1

    # 正常模式
    ms = MemSearch(args.storage)

    # 加载已有数据
    if args.storage:
        ms.load(args.storage)

    # 处理命令
    if args.ingest:
        result = ms.ingest(args.ingest)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            result = ms.ingest(content, source=f"file:{args.file}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(json.dumps(make_error("E003", str(e)), ensure_ascii=False, indent=2))

    if args.search:
        result = ms.search(args.search, top_k=args.top_k, mode="semantic")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.keyword:
        result = ms.search(args.keyword, top_k=args.top_k, mode="keyword")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.list:
        result = ms.list_all()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.delete:
        result = ms.delete(args.delete)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.save:
        result = ms.save(args.save)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.load:
        result = ms.load(args.load)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.info:
        result = ms.info()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 保存数据（如果指定了存储路径）
    if args.storage and not args.selftest:
        ms.save(args.storage)

    # 如果没有执行任何操作，打印帮助
    if not any([args.ingest, args.file, args.search, args.keyword, args.list, args.delete, args.save, args.load, args.info]):
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
