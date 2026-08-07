#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 微信公众号文章转 Markdown（独立实现）

本脚本依据功能规格独立编写，不参考任何既有实现。
提供命令行抓取与转换能力，并内置离线自检模式。
"""

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

# 错误码定义
ERR_OK = 0
ERR_INVALID_INPUT = "E001"      # 输入无效
ERR_URL_UNSUPPORTED = "E002"    # 不支持的 URL 域名
ERR_HTML_PARSE = "E003"         # HTML 解析失败
ERR_EMPTY_CONTENT = "E004"      # 内容为空
ERR_IMAGE_DOWNLOAD = "E005"     # 图片下载失败（预留）
ERR_BATCH_LIMIT = "E006"        # 批量数量超限
ERR_FILE_WRITE = "E007"         # 文件写入失败
ERR_NETWORK = "E008"            # 网络请求失败（预留）
ERR_CONFIG = "E009"             # 配置错误
ERR_INTERNAL = "E010"           # 内部未知错误


# ------------------------------------------------------------
# 数据模型
# ------------------------------------------------------------
@dataclass
class Article:
    """文章数据模型"""
    title: str = ""
    author: str = ""
    publish_time: str = ""
    content_md: str = ""
    images: List[str] = field(default_factory=list)
    source_url: str = ""
    toc: str = ""


# ------------------------------------------------------------
# 核心转换逻辑（纯函数，便于测试）
# ------------------------------------------------------------
def html_to_markdown(html_content: str) -> str:
    """
    将简单 HTML 片段转换为 Markdown 文本。
    支持：标题(h1-h4)、段落、列表(ul/ol/li)、粗体、斜体、链接、图片、引用、代码块、表格。
    不依赖任何第三方库，基于正则与字符串处理。
    """
    if not html_content or not html_content.strip():
        return ""

    text = html_content

    # 移除注释
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # 处理代码块（先保护，避免后续被误伤）
    code_blocks = []
    def _save_code_block(match):
        code_blocks.append(match.group(1))
        return f"\n
