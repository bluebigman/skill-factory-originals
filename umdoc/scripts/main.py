#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
umdoc — Markdown 到 LaTeX 再到 PDF 的转换工具（clean-room 独立实现）

本脚本依据功能规格独立编写，不参考任何既有实现。
功能：
  - 将 Markdown 文本转换为 LaTeX 源码
  - 支持标题、段落、列表、表格、代码块、行内样式等结构映射
  - 内置硬编码样例数据，支持 --selftest 离线自检

用法：
  python scripts/main.py --selftest
  python scripts/main.py input.md [output.tex]
"""

import argparse
import os
import re
import sys
import tempfile
import subprocess

# 错误码定义
ERR_OK = 0
ERR_FILE_NOT_FOUND = "E001"
ERR_OUTPUT_DIR = "E002"
ERR_PDF_COMPILE = "E003"
ERR_INVALID_INPUT = "E004"
ERR_UNSUPPORTED_EXT = "E005"
ERR_SELFTEST_FAIL = "E006"
ERR_INTERNAL = "E007"
ERR_TEMP_DIR = "E008"
ERR_PANDOC_MISSING = "E009"
ERR_UNKNOWN = "E010"


# 内置 LaTeX 文档模板
LATEX_TEMPLATE = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\geometry{a4paper, margin=1in}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{enumitem}
\setlist{nosep, leftmargin=2em}
\lstset{
  basicstyle=\ttfamily\small,
  breaklines=true,
  frame=single,
  backgroundcolor=\color{gray!10},
}

\title{{{title}}}
\author{{{author}}}
\date{{{date}}}

\begin{{document}}
\maketitle
\tableofcontents
\newpage

{body}
\end{{document}}
"""


def md_to_latex(markdown_text: str) -> str:
    """
    将 Markdown 文本转换为 LaTeX 源码。

    支持：
      - 标题（# ~ ###### → section/subsection/subsubsection/paragraph）
      - 段落
      - 无序列表（-、*、+）
      - 有序列表（1. 2. 3.）
      - 表格（| 分隔）
      - 代码块（三个反引号包裹）
      - 行内样式（**粗体**、*斜体*、`行内代码`）

    参数：
        markdown_text: 输入的 Markdown 文本

    返回：
        转换后的 LaTeX 源码字符串
    """
    lines = markdown_text.split('\n')
    latex_lines = []
    i = 0
    in_code_block = False
    in_table = False
    table_rows = []
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 处理代码块
        if stripped.startswith('
