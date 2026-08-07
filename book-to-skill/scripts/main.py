#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
book-to-skill: 书籍转技能 知识提炼 结构化输出
================================================
将书籍、文档或链接转化为结构化技能包，供学习与参考使用。

版本: 1.0.1
许可证: MIT
作者: 知汇工坊
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------
# 常量定义
# --------------------------------------------
APP_NAME = "book-to-skill"
APP_VERSION = "1.0.1"
ERROR_PREFIX = "E"

# 错误码定义
ERR_OK = 0
ERR_INPUT_EMPTY = 1       # E001 输入为空
ERR_INPUT_TYPE = 2        # E002 输入类型不支持
ERR_FILE_NOT_FOUND = 3    # E003 文件不存在
ERR_FILE_READ = 4         # E004 文件读取失败
ERR_URL_INVALID = 5       # E005 URL 格式无效
ERR_PARSE_FAIL = 6        # E006 解析失败
ERR_OUTPUT_WRITE = 7      # E007 输出写入失败
ERR_INTERNAL = 8          # E008 内部错误
ERR_SELFTEST = 9          # E009 自检失败
ERR_INVALID_ARGS = 10     # E010 参数无效

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}

# 置信度阈值
HIGH_CONFIDENCE = 0.85
MEDIUM_CONFIDENCE = 0.60


# --------------------------------------------
# 数据结构定义
# --------------------------------------------
@dataclass
class ExtractedItem:
    """抽取的信息项"""
    content: str
    confidence: float
    source: str = "unknown"
    category: str = "general"


@dataclass
class SkillOutput:
    """技能输出结构"""
    title: str
    summary: str
    items: List[ExtractedItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = APP_VERSION


# --------------------------------------------
# 核心处理逻辑
# --------------------------------------------
class TextProcessor:
    """文本处理核心类"""

    def __init__(self) -> None:
        self._stopwords = {
            "的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它",
            "这", "那", "就", "都", "而", "及", "与", "或", "一个", "没有",
            "我们", "他们", "你们", "这个", "那个", "这些", "那些",
            "the", "a", "an", "and", "or", "but", "is", "are", "was",
            "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "can", "could",
            "should", "may", "might", "must", "shall", "of", "in",
            "on", "at", "to", "for", "with", "by", "from", "up",
            "about", "into", "through", "during", "before", "after",
            "above", "below", "between", "out", "off", "over", "under"
        }
        self._patterns = {
            "heading": re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE),
            "bullet": re.compile(r"^[-*+]\s+(.+)$", re.MULTILINE),
            "number": re.compile(r"^\d+[.)]\s+(.+)$", re.MULTILINE),
            "url": re.compile(r"https?://[^\s]+", re.IGNORECASE),
            "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
            "date": re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"),
            "quote": re.compile(r"^>\s*(.+)$", re.MULTILINE),
        }

    def clean_text(self, text: str) -> str:
        """清理文本：去除多余空白、控制字符"""
        if not text:
            return ""
        # 去除控制字符
        text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\n\r\t")
        # 统一换行
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 压缩多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行尾空白
        lines = [line.rstrip() for line in text.split("\n")]
        return "\n".join(lines).strip()

    def extract_heading(self, text: str) -> str:
        """提取标题（第一个一级/二级标题）"""
        matches = self._patterns["heading"].findall(text)
        for m in matches:
            m = m.strip()
            # 排除常见无效标题
            if len(m) > 1 and not m.startswith("
