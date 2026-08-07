#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2pdfgo — Markdown 转 PDF 技能脚本（clean-room 独立实现）

本脚本仅依据功能规格编写，不参考任何既有代码。
提供 Markdown 文本解析、样式定制、批量转换入口，并支持离线自检。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入文件不存在或不可读",
    "E002": "参数错误：输出目录不可写",
    "E003": "解析错误：Markdown 语法无法解析",
    "E004": "样式错误：自定义样式格式不合法",
    "E005": "转换错误：PDF 生成失败",
    "E006": "批量错误：部分文件处理失败",
    "E007": "环境错误：缺少必要依赖库",
    "E008": "IO 错误：读写文件失败",
    "E009": "内部错误：未知异常",
    "E010": "自检错误：核心逻辑自检未通过",
}


@dataclass
class StyleConfig:
    """样式配置数据类"""
    font_size: int = 12
    font_family: str = "Helvetica"
    line_spacing: float = 1.5
    margin_top: int = 50
    margin_bottom: int = 50
    margin_left: int = 60
    margin_right: int = 60
    header_text: str = ""
    footer_text: str = ""
    color_heading: Tuple[int, int, int] = (30, 30, 30)
    color_body: Tuple[int, int, int] = (20, 20, 20)
    background_color: Optional[Tuple[int, int, int]] = None

    def to_dict(self) -> Dict:
        """转为字典（用于序列化）"""
        return {
            "font_size": self.font_size,
            "font_family": self.font_family,
            "line_spacing": self.line_spacing,
            "margin_top": self.margin_top,
            "margin_bottom": self.margin_bottom,
            "margin_left": self.margin_left,
            "margin_right": self.margin_right,
            "header_text": self.header_text,
            "footer_text": self.footer_text,
            "color_heading": list(self.color_heading),
            "color_body": list(self.color_body),
            "background_color": list(self.background_color) if self.background_color else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StyleConfig":
        """从字典构造"""
        return cls(
            font_size=int(data.get("font_size", 12)),
            font_family=str(data.get("font_family", "Helvetica")),
            line_spacing=float(data.get("line_spacing", 1.5)),
            margin_top=int(data.get("margin_top", 50)),
            margin_bottom=int(data.get("margin_bottom", 50)),
            margin_left=int(data.get("margin_left", 60)),
            margin_right=int(data.get("margin_right", 60)),
            header_text=str(data.get("header_text", "")),
            footer_text=str(data.get("footer_text", "")),
            color_heading=tuple(data.get("color_heading", [30, 30, 30])),
            color_body=tuple(data.get("color_body", [20, 20, 20])),
            background_color=tuple(data["background_color"]) if data.get("background_color") else None,
        )


@dataclass
class ParsedBlock:
    """解析后的 Markdown 块"""
    block_type: str  # heading, paragraph, code, list, quote, image, table
    content: str
    level: int = 0  # 标题级别 / 列表层级
    metadata: Dict = field(default_factory=dict)


class MarkdownParser:
    """Markdown 解析器（轻量实现，支持常用语法）"""

    # 标题正则： # 到 ######
    HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
    # 无序列表
    ULIST_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
    # 有序列表
    OLIST_RE = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
    # 引用
    QUOTE_RE = re.compile(r"^>\s?(.*)$")
    # 代码块开始（
