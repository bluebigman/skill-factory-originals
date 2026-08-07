#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
litedoc — 本地文档智能解析与格式转换

纯本地 PDF 转 Markdown 工具，数据不出设备。
本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import List, Optional


# ============================================================
# 错误码定义
# ============================================================
class LiteDocError(Exception):
    """litedoc 基础异常类，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ParseResult:
    """单个文件的解析结果。"""

    source: str          # 来源（文件名或 URL）
    content: str         # 提取的纯文本内容
    title: Optional[str] = None   # 识别出的标题
    headings: List[str] = None    # 标题层级列表
    lists: List[str] = None       # 列表项
    tables: List[str] = None      # 表格文本
    code_blocks: List[str] = None # 代码块

    def __post_init__(self):
        if self.headings is None:
            self.headings = []
        if self.lists is None:
            self.lists = []
        if self.tables is None:
            self.tables = []
        if self.code_blocks is None:
            self.code_blocks = []


# ============================================================
# 核心解析逻辑（纯函数，便于测试）
# ============================================================
def extract_text_from_pdf(file_path: str) -> str:
    """
    从 PDF 文件中提取文本内容。

    仅支持文本型 PDF。若文件不存在或无法解析，抛出 LiteDocError。
    """
    if not os.path.isfile(file_path):
        raise LiteDocError("E001", f"文件不存在: {file_path}")

    # 检查文件头是否为 PDF
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
    except OSError as e:
        raise LiteDocError("E002", f"无法读取文件: {e}")

    if header != b"%PDF-":
        raise LiteDocError("E003", "不是有效的 PDF 文件")

    # 尝试使用标准库解析（纯文本提取）
    # 注意：标准库没有 PDF 解析器，这里使用简单的文本扫描方式
    # 实际生产环境可替换为 pdfminer 等库（见注释）
    # pip install pdfminer.six
    try:
        # 尝试用 pdfminer（如果已安装）
        from pdfminer.high_level import extract_text  # type: ignore
        return extract_text(file_path)
    except ImportError:
        # 回退到简单二进制扫描（仅用于演示）
        try:
            with open(file_path, "rb", errors="ignore") as f:
                data = f.read()
            # 提取可打印 ASCII 和常见 Unicode 字符
            text_parts = []
            current = []
            for byte in data:
                if 32 <= byte < 127 or byte in (10, 13, 9):
                    current.append(chr(byte))
                else:
                    if current:
                        text_parts.append("".join(current))
                        current = []
            if current:
                text_parts.append("".join(current))
            raw_text = "\n".join(text_parts)
            # 过滤掉明显是二进制的内容
            cleaned = re.sub(r'[^\x20-\x7E\n\r\t]', '', raw_text)
            if len(cleaned.strip()) < 10:
                raise LiteDocError("E004", "PDF 中未提取到有效文本（可能为扫描版）")
            return cleaned
        except LiteDocError:
            raise
        except Exception as e:
            raise LiteDocError("E005", f"PDF 解析失败: {e}")


def fetch_url_content(url: str) -> str:
    """
    从 URL 抓取文本内容（模拟实现）。

    真实实现应使用 requests 等库，此处仅做格式校验。
    """
    if not url.startswith(("http://", "https://")):
        raise LiteDocError("E006", f"无效的 URL: {url}")
    # 模拟返回内容（实际会发起网络请求）
    # pip install requests
    return f"模拟内容: {url}"


def analyze_structure(text: str) -> dict:
    """
    分析文本结构，识别标题、列表、表格、代码块等元素。

    返回包含 headings / lists / tables / code_blocks 的字典。
    """
    lines = text.splitlines()
    headings = []
    lists = []
    tables = []
    code_blocks = []
    in_code_block = False
    code_buffer = []

    for line in lines:
        stripped = line.strip()

        # 代码块检测（
