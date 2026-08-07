#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
html-anything 技能实现脚本
功能：将数据/文件/URL转换为结构化HTML，支持批量与自定义格式。
仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import csv
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：无法读取指定文件",
    "E003": "URL访问失败：无法获取URL内容",
    "E004": "数据解析失败：无法解析输入数据格式",
    "E005": "HTML生成失败：模板或数据格式不匹配",
    "E006": "输出写入失败：无法写入输出文件",
    "E007": "批量处理失败：批量输入中某项处理出错",
    "E008": "模板错误：自定义模板格式不正确",
    "E009": "数据类型不支持：无法处理该类型输入",
    "E010": "内部错误：未预期的运行时异常",
}


class HtmlAnythingError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _escape_text(value: Any) -> str:
    """转义文本内容，防止HTML注入"""
    return html.escape(str(value), quote=True)


def _detect_file_type(file_path: str) -> str:
    """根据文件扩展名检测数据类型"""
    ext = Path(file_path).suffix.lower()
    if ext in (".csv", ".tsv"):
        return "csv"
    elif ext == ".json":
        return "json"
    elif ext == ".md":
        return "markdown"
    elif ext == ".txt":
        return "text"
    else:
        return "text"


def _parse_csv(content: str, delimiter: str = ",") -> List[Dict[str, str]]:
    """解析CSV内容为字典列表"""
    reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
    return [dict(row) for row in reader]


def _parse_json(content: str) -> Any:
    """解析JSON内容"""
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise HtmlAnythingError("E004", f"JSON解析失败: {e}") from e


def _parse_markdown(content: str) -> str:
    """简易Markdown转HTML（仅支持最常用的语法）"""
    lines = content.splitlines()
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # 标题
        if stripped.startswith("### "):
            html_lines.append(f"<h3>{_escape_text(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{_escape_text(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html_lines.append(f"<h1>{_escape_text(stripped[2:])}</h1>")
        # 列表项
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_escape_text(stripped[2:])}</li>")
        # 有序列表
        elif re.match(r"^\d+\.\s", stripped):
            if not in_list:
                html_lines.append("<ol>")
                in_list = True
            html_lines.append(f"<li>{_escape_text(re.sub(r'^\d+\.\s', '', stripped))}</li>")
        # 引用
        elif stripped.startswith("> "):
            html_lines.append(f"<blockquote>{_escape_text(stripped[2:])}</blockquote>")
        # 代码块
        elif stripped.startswith("
