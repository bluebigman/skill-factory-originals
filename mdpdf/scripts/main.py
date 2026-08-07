#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mdpdf - Markdown 转 PDF 命令行工具（clean-room 独立实现）

功能：
- 将 Markdown 文件、标准输入或 URL 内容转换为 PDF
- 支持自定义 CSS 样式表
- 内置 --selftest 离线自检

错误码：
E001 参数解析错误
E002 输入文件不存在或不可读
E003 输出目录不可写
E004 样式表文件不存在或不可读
E005 无法从 URL 获取内容
E006 PDF 转换引擎不可用
E007 转换过程中发生异常
E008 输入内容为空
E009 不支持的文件类型
E010 内部逻辑错误（自检失败）
"""

import argparse
import os
import sys
import tempfile
import subprocess
import urllib.request
import shutil
import re

# 版本号
VERSION = "1.0.1"

# 支持的输入源类型
SOURCE_FILE = "file"
SOURCE_STDIN = "stdin"
SOURCE_URL = "url"


def error_exit(code: str, message: str) -> None:
    """输出错误信息并退出程序"""
    print(f"错误 [{code}]: {message}", file=sys.stderr)
    sys.exit(1)


def read_markdown_file(filepath: str) -> str:
    """从本地文件读取 Markdown 内容"""
    if not os.path.isfile(filepath):
        error_exit("E002", f"输入文件不存在或不可读: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError) as e:
        error_exit("E002", f"读取文件失败: {filepath} ({e})")


def read_stdin() -> str:
    """从标准输入读取 Markdown 内容"""
    try:
        return sys.stdin.read()
    except (IOError, OSError) as e:
        error_exit("E008", f"读取标准输入失败: {e}")


def read_url(url: str) -> str:
    """从 URL 获取 Markdown 内容"""
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        error_exit("E005", f"无法从 URL 获取内容: {url} ({e})")


def read_css_file(css_path: str) -> str:
    """读取 CSS 样式表文件"""
    if not os.path.isfile(css_path):
        error_exit("E004", f"样式表文件不存在或不可读: {css_path}")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError) as e:
        error_exit("E004", f"读取样式表失败: {css_path} ({e})")


def detect_source_type(input_arg: str) -> str:
    """检测输入源类型：文件、stdin 或 URL"""
    if input_arg is None or input_arg == "-":
        return SOURCE_STDIN
    if input_arg.startswith(("http://", "https://")):
        return SOURCE_URL
    return SOURCE_FILE


def get_markdown_content(input_arg: str) -> str:
    """根据输入参数获取 Markdown 内容"""
    source_type = detect_source_type(input_arg)
    if source_type == SOURCE_FILE:
        return read_markdown_file(input_arg)
    elif source_type == SOURCE_URL:
        return read_url(input_arg)
    else:
        return read_stdin()


def find_pdf_engine() -> str:
    """查找可用的 PDF 转换引擎（wkhtmltopdf 或 Chromium）"""
    # 优先使用 wkhtmltopdf
    wkhtmltopdf = shutil.which("wkhtmltopdf")
    if wkhtmltopdf:
        return "wkhtmltopdf"

    # 尝试 Chromium / Chrome
    for candidate in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        path = shutil.which(candidate)
        if path:
            return path

    return ""


def wrap_html(markdown_text: str, css_text: str) -> str:
    """将 Markdown 内容包装为 HTML（简单转换，仅处理基础语法）"""
    # 简单的 Markdown 转 HTML（仅供演示，完整转换应由引擎完成）
    # 这里只做基本转义和段落处理
    html_parts = []
    lines = markdown_text.splitlines()
    in_code_block = False
    code_buffer = []

    for line in lines:
        # 代码块检测
        if line.strip().startswith("
