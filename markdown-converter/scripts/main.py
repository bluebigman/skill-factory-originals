#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-converter 技能实现脚本
版本: 1.0.1
功能: 将文本/本地文件/URL内容转换为结构化Markdown输出，保留关键信息并标注置信度。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "文件读取失败",
    "E004": "URL访问失败",
    "E005": "URL内容为空",
    "E006": "输入内容为空",
    "E007": "内容解析失败",
    "E008": "输出写入失败",
    "E009": "内部逻辑错误",
    "E010": "不支持的输入类型",
}

# ============================================================
# 数据模型
# ============================================================

@dataclass
class ConversionResult:
    """转换结果数据模型"""
    title: str = ""
    content: str = ""
    confidence: float = 0.0
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Block:
    """内容块数据模型"""
    type: str  # heading, paragraph, list, table, code, quote, link
    level: int = 0
    text: str = ""
    items: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    language: str = ""
    url: str = ""
    confidence: float = 1.0


# ============================================================
# 核心处理逻辑
# ============================================================

class MarkdownConverter:
    """Markdown转换器主类"""

    def __init__(self) -> None:
        self.blocks: List[Block] = []
        self.warnings: List[str] = []

    def convert_text(self, text: str, title: str = "") -> ConversionResult:
        """将纯文本转为结构化Markdown"""
        if not text or not text.strip():
            raise ValueError(ERROR_CODES["E006"])

        self.blocks = []
        self.warnings = []
        lines = text.splitlines()

        try:
            self._parse_lines(lines)
        except Exception as e:
            raise ValueError(f"{ERROR_CODES['E007']}: {str(e)}")

        result = ConversionResult(
            title=title or self._extract_title(lines),
            content=self._render_markdown(),
            confidence=self._calculate_confidence(),
            source_type="text",
            metadata={
                "line_count": len(lines),
                "block_count": len(self.blocks),
                "char_count": len(text),
            },
            warnings=self.warnings,
        )
        return result

    def convert_file(self, filepath: str) -> ConversionResult:
        """将本地文件转为结构化Markdown"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(ERROR_CODES["E002"])

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise IOError(f"{ERROR_CODES['E003']}: {str(e)}")

        result = self.convert_text(content, title=os.path.basename(filepath))
        result.source_type = "file"
        result.metadata["filepath"] = filepath
        return result

    def convert_url(self, url: str) -> ConversionResult:
        """将URL内容转为结构化Markdown"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise ConnectionError(f"{ERROR_CODES['E004']}: {str(e)}")

        if not content or not content.strip():
            raise ValueError(ERROR_CODES["E005"])

        result = self.convert_text(content, title=url)
        result.source_type = "url"
        result.metadata["url"] = url
        return result

    # ------------------------------------------------------------
    # 内部解析方法
    # ------------------------------------------------------------

    def _parse_lines(self, lines: List[str]) -> None:
        """解析文本行，识别Markdown结构"""
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # 空行跳过
            if not line.strip():
                i += 1
                continue

            # 代码块检测（围栏式）
            if line.strip().startswith("
