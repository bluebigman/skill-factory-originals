#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filetomarkdown - 将多种文件类型转换为 Markdown 格式的独立实现脚本。

本脚本为 clean-room 实现，仅依据功能规格独立编写，不复制任何既有代码。
支持命令行与自检模式。
"""

import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件不存在",
    "E007": "文件读取失败",
    "E008": "不支持的输入类型",
    "E009": "内部处理错误",
    "E010": "参数错误",
}


class FileToMarkdownError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _detect_file_type(file_path: str) -> str:
    """根据文件扩展名推断文件类型。

    返回类型：text / office / pdf / archive / code / unknown
    """
    ext = Path(file_path).suffix.lower()
    text_exts = {".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml"}
    code_exts = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".sh", ".bat", ".ps1", ".sql", ".html", ".css", ".scss", ".less"}
    office_exts = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"}
    archive_exts = {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"}
    pdf_exts = {".pdf"}

    if ext in text_exts:
        return "text"
    if ext in code_exts:
        return "code"
    if ext in office_exts:
        return "office"
    if ext in archive_exts:
        return "archive"
    if ext in pdf_exts:
        return "pdf"
    return "unknown"


def _read_text_file(file_path: str) -> str:
    """读取文本文件内容，自动尝试常见编码。"""
    encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
    last_error = None
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except OSError as e:
            raise FileToMarkdownError("E007", f"读取文件失败: {e}") from e
    raise FileToMarkdownError("E007", f"无法解码文件内容，尝试了 {len(encodings)} 种编码")


def _read_binary_file(file_path: str) -> bytes:
    """读取二进制文件内容。"""
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except OSError as e:
        raise FileToMarkdownError("E007", f"读取文件失败: {e}") from e


def _csv_to_markdown_table(lines: list, delimiter: str) -> str:
    """将 CSV/TSV 行转换为 Markdown 表格。"""
    if not lines:
        return ""
    
    # 解析行数据
    rows = []
    for line in lines:
        if not line.strip():
            continue
        # 简单解析，不处理引号内的分隔符
        cells = [cell.strip() for cell in line.split(delimiter)]
        rows.append(cells)
    
    if not rows:
        return ""
    
    # 生成 Markdown 表格
    header = rows[0]
    table = ["| " + " | ".join(header) + " |"]
    table.append("| " + " | ".join(["---"] * len(header)) + " |")
    
    for row in rows[1:]:
        # 填充缺失的单元格
        while len(row) < len(header):
            row.append("")
        table.append("| " + " | ".join(row) + " |")
    
    return "\n".join(table)


def _convert_text_to_markdown(content: str, file_path: str) -> str:
    """将文本内容转换为 Markdown。

    纯文本直接包裹在代码块中，保留原始格式。
    """
    file_name = Path(file_path).name
    lines = content.splitlines()
    # 简单检测 CSV/TSV 并转换为表格
    if file_path.lower().endswith((".csv", ".tsv")):
        delimiter = "," if file_path.lower().endswith(".csv") else "\t"
        return _csv_to_markdown_table(lines, delimiter)
    # 简单的 Markdown 直接返回
    if file_path.lower().endswith((".md", ".markdown")):
        return content
    # 其他文本文件包裹在代码块中
    return f"
