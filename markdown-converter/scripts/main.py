#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Markdown 转换工具（PDF转文档）

功能概述：
    将 Markdown 文本转换为 HTML，并支持将 HTML 进一步封装为简易 PDF（文本型）。
    内置语法高亮（针对常见代码块语言），并提供命令行接口。

设计原则：
    - 仅使用 Python 标准库（无需第三方依赖）。
    - 独立实现，不复制任何既有代码。
    - 提供 --selftest 参数进行离线自检（硬编码样例，不依赖外部环境）。

错误码体系：
    E001 输入为空
    E002 关键信息缺失（如未指定输出格式）
    E003 输入格式错误（如 Markdown 语法无法解析）
    E004 超出能力边界（如不支持的转换类型）
    E005 置信度过低（结果不确定）
    E006 文件读取失败
    E007 文件写入失败
    E008 参数解析失败
    E009 内部逻辑错误（不应发生）
    E010 自检失败（仅用于 --selftest 返回值）

用法示例：
    python scripts/main.py input.md -o output.html
    python scripts/main.py input.md -o output.pdf
    python scripts/main.py --selftest
"""

import argparse
import html
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------
SUPPORTED_OUTPUTS = ("html", "pdf")  # 支持的输出格式
SUPPORTED_LANGUAGES = ("python", "javascript", "java", "c", "cpp", "bash", "json", "text")

# 简易语法高亮关键词表（仅用于演示，不追求完整）
HIGHLIGHT_KEYWORDS = {
    "python": {"def", "return", "import", "from", "class", "if", "else", "elif", "for", "while", "try", "except", "finally", "with", "as", "pass", "break", "continue", "lambda", "yield", "global", "nonlocal"},
    "javascript": {"function", "const", "let", "var", "return", "if", "else", "for", "while", "class", "import", "export", "default", "new", "this", "typeof", "instanceof"},
    "java": {"public", "private", "protected", "class", "interface", "void", "int", "String", "boolean", "if", "else", "for", "while", "return", "new", "import", "package", "static", "final"},
    "c": {"include", "define", "int", "char", "float", "double", "void", "if", "else", "for", "while", "return", "struct", "typedef", "enum", "union"},
    "cpp": {"include", "define", "int", "char", "float", "double", "void", "if", "else", "for", "while", "return", "class", "public", "private", "protected", "namespace", "using", "template", "typename"},
    "bash": {"if", "then", "else", "fi", "for", "while", "do", "done", "case", "esac", "function", "return", "echo", "export", "local", "read", "set", "unset"},
    "json": {"true", "false", "null"},
    "text": set(),
}


# ---------------------------------------------------------------------------
# 核心转换函数
# ---------------------------------------------------------------------------
def markdown_to_html(md_text: str) -> str:
    """
    将 Markdown 文本转换为 HTML。

    支持的元素：
        - 标题（# 到 ######）
        - 段落
        - 行内代码（`code`）
        - 代码块（
