#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
werss-cli: 公众号文章获取与 Markdown 转换工具（独立实现）

本脚本依据功能规格独立编写（clean-room），不参考任何既有实现。
核心能力:
  1. 从 WeRSS API 拉取公众号文章列表/详情
  2. 将文章内容转换为 Markdown 格式
  3. 支持增量同步（基于文章发布时间）
  4. 提供离线自检模式（--selftest）

错误码:
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 网络请求失败
  E007 API 返回异常
  E008 文件读写失败
  E009 参数校验失败
  E010 内部逻辑错误

仅使用 Python 标准库实现，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
DEFAULT_API_BASE = "https://werss.example.com/api"  # 默认 API 地址（示例）
DEFAULT_LIMIT = 20          # 默认拉取条数
DEFAULT_SYNC_FILE = ".werss_sync_state.json"  # 增量同步状态文件
HTTP_TIMEOUT = 15           # 网络超时（秒）

# 文章内容中可能包含的 HTML 标签映射（用于转换为 Markdown）
HTML_TAG_MAP = {
    "h1": "# ",
    "h2": "## ",
    "h3": "### ",
    "h4": "#### ",
    "h5": "##### ",
    "h6": "###### ",
    "p": "",
    "br": "\n",
    "strong": "**",
    "b": "**",
    "em": "*",
    "i": "*",
    "code": "`",
    "blockquote": "> ",
    "hr": "\n---\n",
}


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    """将字符串转换为安全的文件名。"""
    # 移除非法字符，保留中文、字母、数字、下划线、连字符
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", name)
    # 去除首尾的点和空格
    cleaned = cleaned.strip(". ")
    # 如果为空则使用默认名称
    return cleaned or "untitled"


def _extract_text_from_html(html: str) -> str:
    """
    从 HTML 片段中提取纯文本（用于生成摘要）。
    简易实现：去除标签、解码实体。
    """
    # 移除 script/style 内容
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # 替换 <br> 和 </p> 为换行
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    # 移除其余 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码常见 HTML 实体
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
    text = text.replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    # 合并多个空白为单个空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _html_to_markdown(html: str) -> str:
    """
    将 HTML 内容转换为 Markdown 格式。
    简易转换器：处理常见标签，保留代码块和列表。
    """
    if not html:
        return ""

    # 处理代码块（pre > code）
    def _replace_code_block(match: re.Match) -> str:
        code_content = match.group(1)
        # 去除多余缩进
        lines = [line.strip() for line in code_content.splitlines()]
        return "\n
