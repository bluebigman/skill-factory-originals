#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
any2md — 文档转 Markdown 结构化处理工具

根据功能规格独立实现（clean-room），将任意输入内容转换为结构化 Markdown，
保留关键信息并标注置信度。
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

# 错误码定义
ERROR_CODES = {
    "E001": "输入内容为空",
    "E002": "输入类型不支持",
    "E003": "文件读取失败",
    "E004": "URL 解析失败",
    "E005": "Markdown 生成失败",
    "E006": "JSON 序列化失败",
    "E007": "参数解析失败",
    "E008": "自检失败",
    "E009": "输出写入失败",
    "E010": "未知错误",
}


class Any2MDError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


class InputParser:
    """输入解析器：识别并解析多种来源的输入"""

    @staticmethod
    def parse_text(text: str) -> dict:
        """解析纯文本输入"""
        if not text or not text.strip():
            raise Any2MDError("E001")
        return {
            "type": "text",
            "content": text,
            "source": "direct_input",
        }

    @staticmethod
    def parse_file(filepath: str) -> dict:
        """解析文件输入（支持 TXT/MD 等文本文件）"""
        if not os.path.isfile(filepath):
            raise Any2MDError("E003", f"文件不存在: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise Any2MDError("E003", f"读取失败: {e}")
        if not content.strip():
            raise Any2MDError("E001", f"文件内容为空: {filepath}")
        return {
            "type": "file",
            "content": content,
            "source": filepath,
        }

    @staticmethod
    def parse_url(url: str) -> dict:
        """解析 URL 输入（仅验证格式，不实际访问网络）"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError("URL 格式无效")
        except Exception as e:
            raise Any2MDError("E004", f"URL 解析失败: {e}")
        # 注意：根据规格，不主动访问网络，仅记录 URL
        return {
            "type": "url",
            "content": url,
            "source": url,
        }


class MarkdownBuilder:
    """Markdown 结构化构建器"""

    # 行内格式标记
    INLINE_PATTERNS = [
        (r"\*\*(.+?)\*\*", "strong"),
        (r"`(.+?)`", "code"),
        (r"\[(.+?)\]\((.+?)\)", "link"),
    ]

    def __init__(self):
        self.lines = []
        self.stats = {
            "headings": 0,
            "paragraphs": 0,
            "lists": 0,
            "tables": 0,
            "code_blocks": 0,
            "quotes": 0,
            "uncertain_items": 0,
        }

    def add_heading(self, text: str, level: int = 1) -> None:
        """添加标题"""
        level = max(1, min(6, level))
        self.lines.append(f"{'#' * level} {text}")
        self.stats["headings"] += 1

    def add_paragraph(self, text: str) -> None:
        """添加段落"""
        if text.strip():
            self.lines.append(text.strip())
            self.lines.append("")
            self.stats["paragraphs"] += 1

    def add_list(self, items: list, ordered: bool = False) -> None:
        """添加列表"""
        if not items:
            return
        for i, item in enumerate(items, 1):
            if ordered:
                self.lines.append(f"{i}. {item}")
            else:
                self.lines.append(f"- {item}")
        self.lines.append("")
        self.stats["lists"] += 1

    def add_table(self, headers: list, rows: list) -> None:
        """添加表格"""
        if not headers or not rows:
            return
        # 表头
        self.lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        # 分隔行
        self.lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        # 数据行
        for row in rows:
            # 确保行长度与表头一致
            padded = list(row) + [""] * (len(headers) - len(row))
            self.lines.append("| " + " | ".join(str(c) for c in padded[:len(headers)]) + " |")
        self.lines.append("")
        self.stats["tables"] += 1

    def add_code_block(self, code: str, language: str = "") -> None:
        """添加代码块"""
        self.lines.append(f"
