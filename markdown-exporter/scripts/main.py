#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

markdown-exporter 技能的全新独立实现（clean-room）。
仅依据功能规格设计，不参考任何既有代码。

功能概要：
- 将用户提供的数据/文件内容解析为结构化结果
- 按约定格式输出 Markdown
- 支持批量处理与自定义模板
- 内置错误码体系 E001-E010
- 提供 --selftest 离线自检（硬编码样例，不访问网络/文件）

免责声明：本实现仅供学习与参考用途，不构成任何专业建议。
"""

import argparse
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "输入为空，请提供待处理的内容（数据/文件/URL）。",
    "E002": "关键信息缺失，请补充：输入来源、输出格式要求、期望完整度。",
    "E003": "输入格式不符合要求，请提供文本、JSON 或 Markdown 内容。",
    "E004": "超出本工具能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定，请提供更多上下文。",
    "E006": "内部解析错误，请检查输入内容的结构。",
    "E007": "输出格式不支持，请使用：md, json, txt。",
    "E008": "批量处理时发现空条目，已跳过。",
    "E009": "模板渲染失败，请检查模板占位符。",
    "E010": "未知错误，请查看日志或联系维护者。",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None) -> None:
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ParsedItem:
    """单条结构化结果。"""

    def __init__(self, content: str, source: str = "user", confidence: float = 1.0) -> None:
        self.content = content.strip()
        self.source = source
        self.confidence = confidence
        self.keywords: List[str] = []
        self.meta: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "keywords": self.keywords,
            "meta": self.meta,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw: str) -> List[str]:
    """解析输入内容，拆分为多个待处理条目。
    
    支持：
    - 纯文本：按空行或换行拆分
    - Markdown：按标题（#）拆分
    - JSON 数组：按数组元素拆分
    """
    if not raw or not raw.strip():
        raise SkillError("E001")

    text = raw.strip()

    # 尝试 JSON 解析
    if text.startswith("[") and text.endswith("]"):
        try:
            import json
            data = json.loads(text)
            if isinstance(data, list):
                items = [str(x) for x in data if str(x).strip()]
                if not items:
                    raise SkillError("E001")
                return items
        except json.JSONDecodeError:
            raise SkillError("E003")

    # Markdown 标题拆分
    if re.search(r"^#{1,6}\s+", text, re.MULTILINE):
        # 按标题分割
        parts = re.split(r"(?=^#{1,6}\s+)", text, flags=re.MULTILINE)
        items = [p.strip() for p in parts if p.strip()]
        if items:
            return items

    # 普通文本按段落拆分
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if paragraphs:
        return paragraphs

    # 单行文本
    return [text]


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """从文本中提取关键词（简单实现）。"""
    # 移除 Markdown 标记
    clean = re.sub(r"[#*_`>\[\]()!-]", " ", text)
    # 分词
    words = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", clean.lower())
    # 过滤停用词
    stopwords = {"的", "了", "和", "是", "在", "有", "我", "你", "他", "这", "那",
                 "the", "a", "an", "is", "are", "to", "of", "and", "for"}
    filtered = [w for w in words if w not in stopwords and len(w) > 1]
    # 去重保序
    seen = set()
    result = []
    for w in filtered:
        if w not in seen:
            seen.add(w)
            result.append(w)
        if len(result) >= max_keywords:
            break
    return result


def calculate_confidence(text: str) -> float:
    """基于文本长度和结构计算置信度。"""
    if not text:
        return 0.0
    length = len(text)
    if length < 10:
        return 0.7
    elif length < 50:
        return 0.85
    elif length < 200:
        return 0.92
    else:
        return 0.95


def process_item(raw_item: str, source: str = "user") -> ParsedItem:
    """处理单条输入，生成结构化结果。"""
    if not raw_item or not raw_item.strip():
        raise SkillError("E008")

    item = ParsedItem(content=raw_item, source=source)
    item.keywords = extract_keywords(item.content)
    item.confidence = calculate_confidence(item.content)
    item.meta["length"] = len(item.content)
    item.meta["has_code"] = "
