#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
umdoc — Markdown 转 LaTeX 再转 PDF 的自动化工具（clean-room 独立实现）

本脚本仅依据功能规格独立编写，不参考任何既有代码。
支持命令行转换单个/多个 Markdown 文件，并内置离线自检模式。
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入文件不存在或不可读",
    "E002": "输出目录无法创建",
    "E003": "Markdown 内容为空",
    "E004": "LaTeX 编译失败（未安装引擎或引擎报错）",
    "E005": "PDF 文件未生成",
    "E006": "参数解析错误",
    "E007": "自检断言失败",
    "E008": "文件写入失败",
    "E009": "系统命令执行异常",
    "E010": "未知错误",
}


def err_exit(code: str, message: str = "") -> None:
    """按错误码输出信息并退出。"""
    text = ERROR_CODES.get(code, "未知错误")
    if message:
        text = f"{text}: {message}"
    print(f"[umdoc] 错误 {code}: {text}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Markdown -> LaTeX 转换核心逻辑
# ---------------------------------------------------------------------------

def escape_latex(text: str) -> str:
    """转义 LaTeX 特殊字符（保留常见 Markdown 标记的处理交给上层）。"""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def inline_convert(text: str) -> str:
    """
    转换行内 Markdown 标记为 LaTeX 命令：
    - **粗体** -> \\textbf{}
    - *斜体* -> \\textit{}
    - `行内代码` -> \\texttt{}
    - [文本](链接) -> \\href{链接}{文本}
    """
    # 先处理行内代码，避免其中的标记被误转换
    code_placeholders = {}

    def _save_code(match):
        idx = f"@@CODE{len(code_placeholders)}@@"
        code_placeholders[idx] = r"\texttt{" + escape_latex(match.group(1)) + "}"
        return idx

    text = re.sub(r"`([^`]+)`", _save_code, text)

    # 链接 [文本](链接)
    def _link_repl(match):
        label = inline_convert(match.group(1))
        url = match.group(2)
        return r"\href{" + escape_latex(url) + "}{" + label + "}"

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link_repl, text)

    # 粗体 **text** 或 __text__
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"__([^_]+)__", r"\\textbf{\1}", text)

    # 斜体 *text* 或 _text_
    text = re.sub(r"\*([^*\n]+)\*", r"\\textit{\1}", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\\textit{\1}", text)

    # 恢复代码占位符
    for key, value in code_placeholders.items():
        text = text.replace(key, value)

    return text


def convert_table(lines: list) -> str:
    """将 Markdown 表格（含分隔行）转换为 LaTeX tabular 环境。"""
    if not lines:
        return ""

    header = [c.strip() for c in lines[0].strip("|").split("|")]
    # 跳过分隔行（如 |---|:---:|）
    body = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        body.append(cells)

    col_count = len(header)
    col_spec = "|" + "|".join(["l"] * col_count) + "|"

    tex = ["\\begin{table}[h]", "\\centering", "\\begin{tabular}{" + col_spec + "}", "\\hline"]
    tex.append(" & ".join(inline_convert(c) for c in header) + " \\\\")
    tex.append("\\hline")
    for row in body:
        tex.append(" & ".join(inline_convert(c) for c in row) + " \\\\")
        tex.append("\\hline")
    tex.append("\\end{tabular}")
    tex.append("\\end{table}")
    return "\n".join(tex)


def convert_code_block(content: str, lang: str = "") -> str:
    """将代码块内容包装为 LaTeX 等宽字体段落。"""
    lines = content.rstrip("\n").split("\n")
    escaped = [escape_latex(line) for line in lines]
    body = " \\\\\n".join(escaped)
    return "\\begin{verbatim}\n" + "\n".join(lines) + "\n\\end{verbatim}"


def md_to_latex(md_text: str) -> str:
    """
    将 Markdown 文本转换为 LaTeX 源码。
    支持：标题、段落、列表、表格、代码块、引用、分隔线、行内样式。
    """
    if not md_text or not md_text.strip():
        return ""

    lines = md_text.split("\n")
    tex_lines = []
    i = 0
    in_code_block = False
    code_buffer = []
    code_lang = ""

    while i < len(lines):
        line = lines[i]

        # 代码块开始/结束
        if line.strip().startswith("
