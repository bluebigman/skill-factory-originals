#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdownconverter - 文档格式转换批处理工具

将 Markdown 文件批量转换为 HTML、PNG 或 PDF，支持自定义样式与模板。

本脚本为 clean-room 独立实现，仅依据功能规格设计。
"""

import argparse
import html
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入文件或目录不存在",
    "E003": "输出目录无法创建",
    "E004": "不支持的目标格式（仅支持 html/png/pdf）",
    "E005": "Markdown 文件读取失败",
    "E006": "HTML 渲染失败",
    "E007": "PNG 转换失败（需要安装外部工具）",
    "E008": "PDF 转换失败（需要安装外部工具）",
    "E009": "批量转换过程中出现错误",
    "E010": "内部逻辑错误",
}


def fail(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[错误 {code}] {msg}: {message}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# Markdown 解析核心逻辑
# ============================================================

class MarkdownParser:
    """极简 Markdown 解析器 - 支持常用语法子集"""

    # 行级正则表达式
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
    _CODE_FENCE_RE = re.compile(r'^
