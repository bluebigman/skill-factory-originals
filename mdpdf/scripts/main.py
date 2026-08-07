#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mdpdf - Markdown 转 PDF 命令行工具（独立实现）

功能：
- 将 Markdown 文件或标准输入转换为 PDF
- 支持自定义 CSS 样式表
- 支持 --selftest 离线自检
- 支持 --version 查看版本

设计原则：
- 标准库优先，仅在需要时引入第三方库
- 使用错误码 E001-E010 标识错误类型
- 自检使用宽松阈值，确保在任何环境可运行
"""

import argparse
import sys
import os
import tempfile
import subprocess
import shutil
import re
from pathlib import Path
from urllib.parse import urlparse

# 版本号
VERSION = "1.0.1"

# 错误码定义
ERROR_CODES = {
    "E001": "输入文件不存在",
    "E002": "输入文件不是 Markdown 格式",
    "E003": "输出目录不存在",
    "E004": "无法写入输出文件",
    "E005": "转换引擎未安装",
    "E006": "样式表文件不存在",
    "E007": "URL 无法访问",
    "E008": "标准输入为空",
    "E009": "参数冲突",
    "E010": "未知错误",
}


class MDPDFError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def get_converter_engine():
    """
    检测可用的 PDF 转换引擎
    
    返回：
        (engine_name, command_template) 或 (None, None)
    """
    # 检测 wkhtmltopdf
    wkhtmltopdf_path = shutil.which("wkhtmltopdf")
    if wkhtmltopdf_path:
        return "wkhtmltopdf", wkhtmltopdf_path
    
    # 检测 Chromium/Chrome
    for browser in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        browser_path = shutil.which(browser)
        if browser_path:
            return "chromium", browser_path
    
    return None, None


def is_url(path_str):
    """判断是否为 URL"""
    parsed = urlparse(path_str)
    return parsed.scheme in ("http", "https")


def read_markdown_source(source):
    """
    读取 Markdown 源内容
    
    参数：
        source: 文件路径、URL 或 None（表示标准输入）
    
    返回：
        (markdown_text, source_name)
    """
    # 从标准输入读取
    if source is None:
        if sys.stdin.isatty():
            raise MDPDFError("E008")
        markdown_text = sys.stdin.read()
        if not markdown_text.strip():
            raise MDPDFError("E008")
        return markdown_text, "stdin"
    
    # 从 URL 读取
    if is_url(source):
        try:
            import urllib.request
            with urllib.request.urlopen(source, timeout=10) as response:
                markdown_text = response.read().decode("utf-8")
            return markdown_text, source
        except Exception:
            raise MDPDFError("E007", f"无法访问 URL: {source}")
    
    # 从文件读取
    file_path = Path(source)
    if not file_path.exists():
        raise MDPDFError("E001", f"文件不存在: {source}")
    
    if file_path.suffix.lower() not in (".md", ".markdown", ".mdown", ".mkd"):
        raise MDPDFError("E002", f"不支持的文件格式: {file_path.suffix}")
    
    try:
        markdown_text = file_path.read_text(encoding="utf-8")
    except Exception:
        raise MDPDFError("E010", f"无法读取文件: {source}")
    
    return markdown_text, str(file_path)


def read_style_sheet(style_path):
    """
    读取 CSS 样式表
    
    参数：
        style_path: 样式表路径
    
    返回：
        CSS 内容字符串
    """
    if style_path is None:
        return ""
    
    style_file = Path(style_path)
    if not style_file.exists():
        raise MDPDFError("E006", f"样式表不存在: {style_path}")
    
    try:
        return style_file.read_text(encoding="utf-8")
    except Exception:
        raise MDPDFError("E006", f"无法读取样式表: {style_path}")


def markdown_to_html(markdown_text):
    """
    将 Markdown 转换为 HTML（简化实现）
    
    这是核心转换逻辑，使用正则表达式处理常见 Markdown 语法。
    注意：这是简化实现，完整功能需要引入第三方库。
    
    参数：
        markdown_text: Markdown 源文本
    
    返回：
        HTML 字符串
    """
    html = markdown_text
    
    # 转义 HTML 特殊字符（避免注入）
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 处理代码块（
