#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
umdoc — Markdown 转 LaTeX 再转 PDF 的自动化工具（clean-room 独立实现）

本脚本仅依据功能规格重新实现，不包含任何既有代码。
支持命令行调用，提供 --selftest 离线自检能力。
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "文件不存在或无法读取",
    "E002": "输出目录无法创建",
    "E003": "LaTeX 编译失败",
    "E004": "输入参数无效",
    "E005": "Markdown 解析失败",
    "E006": "LaTeX 模板加载失败",
    "E007": "输出文件写入失败",
    "E008": "PDF 生成失败",
    "E009": "批量处理中断",
    "E010": "未知错误",
}

# 内置 LaTeX 模板
LATEX_TEMPLATE = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\geometry{a4paper, margin=2.5cm}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{hyperref}
\hypersetup{{
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue,
}}

\title{{{title}}}
\author{{{author}}}
\date{{\today}}

\begin{{document}}

\maketitle

{content}

\end{{document}}
"""


class UmdocError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


def _escape_latex(text: str) -> str:
    """转义 LaTeX 特殊字符。"""
    # 注意：反斜杠和花括号需要最先处理，避免二次转义
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
        "%": r"\%",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    result = text
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    return result


def _parse_inline(text: str) -> str:
    """解析行内 Markdown 语法（粗体、斜体、行内代码）。"""
    # 行内代码（最优先处理，避免内部内容被误解析）
    text = re.sub(r"`([^`]+)`", lambda m: r"\texttt{" + _escape_latex(m.group(1)) + "}", text)

    # 粗体 **text** 或 __text__
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: r"\textbf{" + m.group(1) + "}", text)
    text = re.sub(r"__([^_]+)__", lambda m: r"\textbf{" + m.group(1) + "}", text)

    # 斜体 *text* 或 _text_
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: r"\textit{" + m.group(1) + "}", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", lambda m: r"\textit{" + m.group(1) + "}", text)

    # 行内链接 [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: r"\href{" + m.group(2) + "}{" + m.group(1) + "}", text)

    # 转义剩余特殊字符
    return _escape_latex(text)


def _parse_table(lines: list) -> str:
    """解析 Markdown 表格为 LaTeX tabular 环境。"""
    if len(lines) < 2:
        return ""

    # 分割表头
    header_cells = [cell.strip() for cell in lines[0].strip("|").split("|")]
    # 跳过分隔行（|---|）
    data_rows = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        data_rows.append(cells)

    num_cols = len(header_cells)
    col_spec = "l" * num_cols

    latex_lines = []
    latex_lines.append(r"\begin{tabular}{" + col_spec + r"}")
    latex_lines.append(r"\toprule")
    latex_lines.append(" & ".join(_parse_inline(cell) for cell in header_cells) + r" \\")
    latex_lines.append(r"\midrule")
    for row in data_rows:
        # 补齐列数
        while len(row) < num_cols:
            row.append("")
        latex_lines.append(" & ".join(_parse_inline(cell) for cell in row[:num_cols]) + r" \\")
    latex_lines.append(r"\bottomrule")
    latex_lines.append(r"\end{tabular}")

    return "\n".join(latex_lines)


def markdown_to_latex(markdown_text: str) -> str:
    """
    将 Markdown 文本转换为 LaTeX 源码。

    参数:
        markdown_text: Markdown 格式的文本内容

    返回:
        LaTeX 源码字符串

    异常:
        UmdocError: 当解析失败时抛出 E005
    """
    try:
        lines = markdown_text.splitlines()
        latex_parts = []
        i = 0
        in_code_block = False
        code_buffer = []
        in_table = False
        table_buffer = []

        while i < len(lines):
            line = lines[i].rstrip()

            # 代码块处理
            if line.strip().startswith("
