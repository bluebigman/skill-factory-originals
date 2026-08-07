#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Markdown 转 PDF 转换工具（独立实现）

本脚本依据功能规格独立编写（clean-room），不复制任何既有代码。
支持从文件、URL、标准输入读取 Markdown 内容，并转换为 PDF 文件。
"""

import argparse
import os
import re
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# 错误码定义
E001 = "E001: 输入源无效（文件不存在或 URL 无法访问）"
E002 = "E002: 未找到可用的 PDF 渲染后端（需安装 reportlab 或 weasyprint）"
E003 = "E004: 输出目录不存在或不可写"
E004 = "E005: Markdown 解析失败（内容为空或不合法）"
E005 = "E006: 批量处理时部分项目失败"
E006 = "E007: 命令行参数错误"
E007 = "E008: 临时文件操作失败"
E008 = "E009: 内部渲染错误"
E009 = "E010: 不支持的 URL 协议"
E010 = "E011: 网络请求超时或失败"


# ---------- 数据结构 ----------

@dataclass
class MarkdownItem:
    """单个 Markdown 源项目"""
    source: str            # 文件路径或 URL
    content: str = ""      # 读取到的原始内容
    title: str = ""        # 从内容中提取的标题（用于 PDF 元信息）
    is_url: bool = False


@dataclass
class ConversionResult:
    """单个转换结果"""
    source: str
    output_path: str
    success: bool
    error_code: Optional[str] = None
    page_count: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class RenderConfig:
    """PDF 渲染配置"""
    page_size: str = "A4"          # A4 / Letter / A5
    margin_top: int = 25           # 毫米
    margin_bottom: int = 25        # 毫米
    margin_left: int = 25          # 毫米
    margin_right: int = 25         # 毫米
    font_size: int = 11            # 正文字号（pt）
    title_font_size: int = 18      # 标题字号（pt）
    line_spacing: float = 1.5      # 行距倍数
    output_dir: str = "output"     # 输出目录
    output_prefix: str = "doc"     # 输出文件名前缀


# ---------- Markdown 解析 ----------

class MarkdownParser:
    """轻量级 Markdown 解析器（仅支持核心语法）"""

    # 块级元素正则
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
    _CODE_BLOCK_RE = re.compile(r'^
