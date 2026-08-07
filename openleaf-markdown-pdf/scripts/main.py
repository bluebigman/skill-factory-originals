#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openleaf-markdown-pdf — 分页文档 PDF 转换排版工具（clean-room 独立实现）

功能概述：
    将 Markdown 文本转换为适合正式文档的分页 PDF 文件。
    支持分页控制、页眉页脚、页码、字体边距设置、目录生成与批量转换。

设计原则：
    - 仅依据功能规格独立实现，不参考任何既有代码。
    - 标准库优先，第三方库仅在必要时使用并注明安装命令。
    - 提供 --selftest 参数，使用内置硬编码样例离线自检核心逻辑。

错误码约定：
    E001 参数解析错误
    E002 输入文件不存在或不可读
    E003 输出目录创建失败
    E004 Markdown 解析失败
    E005 PDF 生成失败
    E006 批量转换部分失败
    E007 目录生成失败
    E008 样式配置无效
    E009 分页符处理失败
    E010 未知内部错误
"""

import argparse
import hashlib
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 一、数据模型与配置
# ============================================================

@dataclass
class DocumentStyle:
    """文档样式配置"""
    font_family: str = "SimSun"           # 中文字体
    font_size: int = 12                   # 正文字号（pt）
    line_spacing: float = 1.5             # 行距倍数
    margin_top: int = 25                  # 上边距（mm）
    margin_bottom: int = 25               # 下边距（mm）
    margin_left: int = 30                 # 左边距（mm）
    margin_right: int = 30                # 右边距（mm）
    header_text: str = ""                 # 页眉内容
    footer_text: str = ""                 # 页脚内容
    show_page_number: bool = True         # 是否显示页码
    page_number_format: str = "第 {n} 页" # 页码格式

    def validate(self) -> Tuple[bool, str]:
        """校验样式配置是否合法"""
        if self.font_size < 8 or self.font_size > 32:
            return False, "字体大小应在 8-32pt 之间"
        if self.line_spacing < 1.0 or self.line_spacing > 3.0:
            return False, "行距倍数应在 1.0-3.0 之间"
        if min(self.margin_top, self.margin_bottom,
               self.margin_left, self.margin_right) < 10:
            return False, "页边距不能小于 10mm"
        if max(self.margin_top, self.margin_bottom,
               self.margin_left, self.margin_right) > 50:
            return False, "页边距不能大于 50mm"
        return True, "OK"


@dataclass
class DocumentContent:
    """解析后的文档内容"""
    title: str = ""                       # 文档标题
    headings: List[Tuple[int, str]] = field(default_factory=list)  # (级别, 标题)
    blocks: List[Dict] = field(default_factory=list)  # 内容块列表
    page_breaks: List[int] = field(default_factory=list)  # 分页位置（块索引）


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool = False
    output_path: str = ""
    page_count: int = 0
    error_code: str = ""
    error_message: str = ""


# ============================================================
# 二、Markdown 解析器（纯文本处理，不依赖第三方库）
# ============================================================

class MarkdownParser:
    """
    轻量级 Markdown 解析器。
    支持：标题、段落、列表、引用、代码块、水平线、分页符。
    复杂表格降级为纯文本；不支持的语法原样保留。
    """

    # 分页符模式：\newpage 或 单独一行的 ---
    PAGE_BREAK_PATTERNS = [
        re.compile(r'^\s*\\newpage\s*$'),
        re.compile(r'^\s*---\s*$'),
    ]

    def __init__(self, markdown_text: str):
        self.raw_text = markdown_text
        self.lines = markdown_text.split('\n')
        self.content = DocumentContent()

    def parse(self) -> DocumentContent:
        """解析 Markdown 文本为结构化内容"""
        try:
            self._extract_title()
            self._parse_blocks()
            self._collect_headings()
            self._find_page_breaks()
            return self.content
        except Exception as exc:
            raise ValueError(f"Markdown 解析失败: {exc}") from exc

    def _extract_title(self) -> None:
        """提取文档标题（第一个一级标题）"""
        for line in self.lines:
            stripped = line.strip()
            if stripped.startswith('# '):
                self.content.title = stripped[2:].strip()
                return

    def _parse_blocks(self) -> None:
        """将文本解析为内容块列表"""
        blocks: List[Dict] = []
        current_block: Optional[Dict] = None
        in_code_block = False
        code_lang = ""

        for line in self.lines:
            stripped = line.strip()

            # 代码块开始/结束
            if stripped.startswith('
