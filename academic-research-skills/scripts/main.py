#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学术研究技能（academic-research-skills）核心实现脚本。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
提供资料结构化转换、关键信息识别、格式输出、置信度标注等核心能力。
"""

import argparse
import csv
import io
import json
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, quote_plus

# ---------------------------------------------------------------------------
# 错误码定义（E001-E012）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入内容为空或无效",
    "E002": "不支持的输出格式（仅支持 markdown/json/csv）",
    "E003": "输入内容不是有效文本",
    "E004": "字段结构定义无效",
    "E005": "批量处理时输入列表为空",
    "E006": "自定义模板格式错误",
    "E007": "置信度标注值超出范围（应为0-1）",
    "E008": "内部逻辑错误：数据转换失败",
    "E009": "参数解析错误",
    "E010": "未知运行时错误",
    "E011": "网络请求失败（重试后仍失败）",
    "E012": "批量处理部分失败",
}


class AcademicSkillError(Exception):
    """技能运行期异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ResearchCard:
    """结构化研究资料卡片。"""

    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    abstract: str = ""
    conclusion: str = ""
    limitations: List[str] = field(default_factory=list)
    confidence: float = 0.8  # 置信度 0-1
    source: str = ""
    raw_text: str = ""
    created_at: str = ""  # ISO 8601 UTC 时间戳

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON/CSV 输出）。"""
        return asdict(self)


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------
def _read_text_safe(path: str) -> str:
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _iter_lines(path: str):
    """流式读取文件行（用于大文件）"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def _validate_text(text: str) -> str:
    """校验输入文本，返回去除首尾空白后的内容。"""
    if text is None:
        raise AcademicSkillError("E001")
    if not isinstance(text, str):
        raise AcademicSkillError("E003")
    cleaned = text.strip()
    if not cleaned:
        raise AcademicSkillError("E001")
    return cleaned


def _split_sentences(text: str) -> List[str]:
    """将文本按句号、问号、感叹号切分为句子列表。"""
    parts = re.split(r"(?<=[。！？!?])\s*", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_keywords(text: str, max_count: int = 8) -> List[str]:
    """
    从文本中提取候选关键词。
    策略：
    1. 优先提取引号内词语
    2. 中文：按字符 bigram 频率统计
    3. 英文：按单词频率统计（过滤停用词）
    4. 降级：提取高频字符/单词
    """
    # 尝试提取引号内内容
    quoted = re.findall(r'[""「『]([^""」』]+)[""」』]', text)
    if quoted:
        result = []
        for q in quoted:
            q_clean = q.strip()
            if 2 <= len(q_clean) <= 20 and q_clean not in result:
                result.append(q_clean)
            if len(result) >= max_count:
                break
        if result:
            return result

    # 中文处理：提取连续2-4个中文字符作为候选词
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    if len(chinese_chars) > 10:
        bigrams = {}
        for i in range(len(chinese_chars) - 1):
            bg = chinese_chars[i] + chinese_chars[i + 1]
            bigrams[bg] = bigrams.get(bg, 0) + 1
        # 排序取高频
        sorted_bg = sorted(bigrams.items(), key=lambda x: x[1], reverse=True)
        keywords = [bg for bg, _ in sorted_bg[:max_count] if len(bg) == 2]
        # 过滤纯标点或无意义词
        stop_chars = set("的了是在和与及等或与")
        keywords = [k for k in keywords if not any(c in stop_chars for c in k)]
        if keywords:
            return keywords[:max_count]

    # 英文处理
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower())
    stop_words = {
        "the", "and", "for", "with", "that", "this", "from", "are",
        "was", "were", "has", "have", "been", "will", "can", "could",
        "should", "would", "may", "might", "must", "not", "but", "all",
        "any", "each", "few", "more", "most", "other", "some", "such",
        "than", "too", "very", "just", "about", "into", "over", "after",
        "before", "between", "under", "again", "further", "then", "once",
    }
    freq = {}
    for w in words:
        if w not in stop_words:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    if sorted_words:
        return [w for w, _ in sorted_words[:max_count]]

    # 降级：提取高频字符（中文单字）
    if chinese_chars:
        char_freq = {}
        for c in chinese_chars:
            if c not in stop_chars:
                char_freq[c] = char_freq.get(c, 0) + 1
        sorted_chars = sorted(char_freq.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in sorted_chars[:max_count]]

    # 最后降级：返回空列表
    return []


def _extract_year(text: str) -> Optional[int]:
    """从文本中提取四位年份（1900-2100区间）。"""
    # 匹配带"年"字的模式优先
    matches_with_year = re.findall(r'(19|20)\d{2}年', text)
    if matches_with_year:
        year_str = matches_with_year[0].replace('年', '')
        year = int(year_str)
        if 1900 <= year <= 2100:
            return year

    # 匹配所有4位数字
    matches_all = re.findall(r'\b(19|20)\d{2}\b', text)
    for m in matches_all:
        year = int(m)
        if 1900 <= year <= 2100:
            return year

    return None


def _extract_authors(text: str) -> List[str]:
    """从文本中提取作者信息（启发式）。"""
    # 常见模式：中文“作者：张三、李四”或英文 “Author: John Smith”
    patterns = [
        r"作者[：:]\s*([^\n。；;]+)",
        r"author[s]?[:：]\s*([^\n。；;]+)",
        r"by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:,\s*[A-Z][a-z]+)*)",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            # 按逗号、顿号、and 切分
            parts = re.split(r"[,，、]|\s+and\s+", raw)
            authors = [p.strip() for p in parts if p.strip()]
            # 过滤明显不是人名的内容
            authors = [a for a in authors if len(a) >= 2 and not a.isdigit()]
            if authors:
                return authors[:5]  # 最多返回5个
    return []


def _extract_conclusion(text: str) -> str:
    """提取结论部分（启发式）。"""
    # 查找“结论”、“总结”、“conclusion”等关键词后的内容
    patterns = [
        r"(?:结论|总结|结语)[：:]\s*([^\n]+)",
        r"(?:conclusion|summary)[:：]\s*([^\n]+)",
        r"(?:总之|综上所述|因此)[，,]\s*([^\n。]+)",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    # 备选：返回最后一句
    sentences = _split_sentences(text)
    if sentences:
        return sentences[-1]
    return ""


def _extract_limitations(text: str) -> List[str]:
    """提取局限性说明（启发式）。"""
    limitations = []
    patterns = [
        r"(?:局限|不足|限制)[：:]\s*([^\n。]+)",
        r"(?:limitation[s]?|drawback[s]?|weakness[es]?)[:：]\s*([^\n。]+)",
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            clean = m.strip()
            if clean and clean not in limitations:
                limitations.append(clean)
    # 如果没找到，尝试找包含“局限”或“不足”的句子
    if not limitations:
        for sentence in _split_sentences(text):
            if any(word in sentence for word in ["局限", "不足", "限制", "limitation", "drawback"]):
                limitations.append(sentence.strip())
                if len(limitations) >= 3:
                    break
    return limitations[:5]


def _calculate_confidence(card: ResearchCard) -> float:
    """
    基于提取完整度计算置信度（0-1）。
    规则：
    - 标题存在 +0.3
    - 作者存在 +0.2
    - 年份存在 +0.15
    - 关键词存在 +0.15
    - 摘要存在 +0.1
    - 结论存在 +0.1
    基础分 0.2，最高 1.0
    """
    score = 0.2
    if card.title:
        score += 0.3
    if card.authors:
        score += 0.2
    if card.year is not None:
        score += 0.15
    if card.keywords:
        score += 0.15
    if card.abstract:
        score += 0.1
    if card.conclusion:
        score += 0.1
    return min(1.0, score)


def structure_text(text: str, source: str = "") -> ResearchCard:
    """
    将原始文本转换为结构化 ResearchCard。
    这是核心转换逻辑。
    """
    cleaned = _validate_text(text)

    # 提取标题：取第一行或第一个句子（截断）
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    title = ""
    if lines:
        first_line = lines[0]
        # 如果第一行太长，截断
        title = first_line[:80] if len(first_line) > 80 else first_line

    # 提取摘要：取第二行或第二个句子（启发式）
    abstract = ""
    if len(lines) > 1:
        abstract = lines[1][:200] if len(lines[1]) > 200 else lines[1]
    elif len(_split_sentences(cleaned)) > 1:
        abstract = _split_sentences(cleaned)[1][:200]

    card = ResearchCard(
        title=title,
        authors=_extract_authors(cleaned),
        year=_extract_year(cleaned),
        keywords=_extract_keywords(cleaned),
        abstract=abstract,
        conclusion=_extract_conclusion(cleaned),
        limitations=_extract_limitations(cleaned),
        confidence=0.8,  # 默认置信度（启发式提取，非精确）
        source=source,
        raw_text=cleaned,
    )
    # 基于提取完整度重新计算置信度
    card.confidence = _calculate_confidence(card)
    return card


def _process_single_item(item: Dict[str, str]) -> Tuple[Optional[ResearchCard], Optional[str]]:
    """处理单个批量项，返回 (结果, 错误信息)。"""
    try:
        text = item.get("text", "")
        source = item.get("source", "")
        card = structure_text(text, source)
        return card, None
    except AcademicSkillError as e:
        return None, f"处理项失败: {e}"
    except Exception as e:
        return None, f"处理项发生未知错误: {e}"


def batch_structure(items: List[Dict[str, str]], max_workers: int = 4) -> List[ResearchCard]:
    """
    批量处理多个输入，支持并发和错误隔离。
    items 为 [{"text": "...", "source": "..."}] 格式。
    单条失败不会中断整个批次，失败项会被跳过并记录。
    """
    if not items:
        raise AcademicSkillError("E005")

    results: List[ResearchCard] = []
    errors: List[str] = []
    lock = threading.Lock()

    def process_item(item: Dict[str, str]) -> Tuple[Optional[ResearchCard], Optional[str]]:
        return _process_single_item(item)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(process_item, item): item for item in items}
        for future in as_completed(future_to_item):
            card, error = future.result()
            with lock:
                if card is not None:
                    results.append(card)
                if error:
                    errors.append(error)

    # 如果全部失败，抛出异常
    if not results and errors:
        raise AcademicSkillError("E012", f"批量处理全部失败: {'; '.join(errors[:3])}")

    # 如果有部分失败，打印警告
    if errors:
        print(f"[WARN] 批量处理部分失败: {len(errors)}/{len(items)} 项失败", file=sys.stderr)
        for err in errors[:5]:
            print(f"  - {err}", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# 网络检索功能（能力：检索）
# ---------------------------------------------------------------------------
def _http_get_with_retry(url: str, timeout: float = 10.0, max_retries: int = 3) -> str:
    """
    带重试退避和超时的 HTTP GET 请求。
    使用标准库 urllib 实现，避免额外依赖。
    """
    import urllib.request
    import urllib.error

    if not url.startswith(("http://", "https://")):
        raise AcademicSkillError("E011", f"无效的URL: {url}")

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AcademicResearchSkill/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    raise urllib.error.HTTPError(url, response.status, "HTTP Error", response.headers, None)
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise AcademicSkillError("E011", f"请求失败（重试{max_retries}次）: {e}")
            # 指数退避
            wait_time = 2 ** attempt
            time.sleep(wait_time)
        except Exception as e:
            raise AcademicSkillError("E011", f"请求异常: {e}")

    raise AcademicSkillError("E011", "请求失败")


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    网络检索功能（简化实现）。
    使用 DuckDuckGo HTML 搜索作为后端（无需 API key）。
    注意：这是简化实现，实际生产环境应使用专业搜索 API。
    """
    if not query or not query.strip():
        raise AcademicSkillError("E001")

    # 构建搜索 URL
