#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jina-cli — 网页内容转文本工具（全新独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
支持 URL 内容提取、本地文件解析、批量处理、格式自定义、自检与版本查询。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# 版本信息
VERSION = "1.0.1"

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：未提供任何输入",
    "E002": "参数错误：不支持的输出格式",
    "E003": "文件读取失败：文件不存在或无法读取",
    "E004": "URL 请求失败：网络错误或 HTTP 错误",
    "E005": "URL 请求失败：URL 格式无效",
    "E006": "内容解析失败：无法从输入中提取文本",
    "E007": "批量处理失败：部分输入处理出错",
    "E008": "自检失败：核心逻辑验证未通过",
    "E009": "运行时错误：未知异常",
    "E010": "参数错误：输入类型无法识别",
}


def get_error_message(code: str) -> str:
    """根据错误码返回错误描述"""
    return ERROR_CODES.get(code, "未知错误")


def extract_text_from_html(html_content: str) -> str:
    """
    从 HTML 内容中提取纯文本。
    去除脚本、样式、标签，保留文本内容。
    """
    if not html_content:
        return ""
    
    # 移除 script 和 style 块
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除 HTML 注释
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.DOTALL)
    
    # 将标签替换为空格（保留文本内容）
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 解码常见 HTML 实体
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<')
    text = text.replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    
    # 规范化空白：多个空格、换行、制表符合并为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 清理首尾空白
    return text.strip()


def extract_text_from_markdown(md_content: str) -> str:
    """
    从 Markdown 内容中提取纯文本。
    去除标记符号，保留文本内容。
    """
    if not md_content:
        return ""
    
    # 移除代码块
    text = re.sub(r'
