#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

主题生成 Skill 的独立实现（clean-room 重写）。
依据功能规格独立设计，不复制任何既有代码。

功能：
  - 将 Markdown 文本解析为结构化块（标题、段落、列表、引用、代码块）。
  - 应用 6 套内置主题模板，生成适合公众号粘贴的 HTML 片段。
  - 双关卡校验：结构完整性与内容非空性。
  - 内置 --selftest 自检模式，使用硬编码样例数据离线验证核心逻辑。

错误码：
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 内部解析错误
  E007 主题不存在
  E008 HTML 生成失败
  E009 校验失败
  E010 未知错误

依赖：仅 Python 标准库（argparse, re, html, sys, json）。
"""

import argparse
import html
import json
import re
import sys
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 6 套精选主题的样式配置（主题名 -> CSS 片段）
THEMES: Dict[str, str] = {
    "default": """
        <style>
            .gzh-body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.75; color: #333; padding: 16px; }
            .gzh-body h1, .gzh-body h2, .gzh-body h3 { font-weight: 600; margin-top: 1.5em; margin-bottom: 0.5em; }
            .gzh-body h1 { font-size: 1.6em; border-bottom: 2px solid #2c3e50; padding-bottom: 0.3em; }
            .gzh-body h2 { font-size: 1.3em; border-left: 4px solid #3498db; padding-left: 0.5em; }
            .gzh-body h3 { font-size: 1.1em; }
            .gzh-body p { margin: 0.8em 0; }
            .gzh-body blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #666; background: #f9f9f9; }
            .gzh-body code { background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.9em; }
            .gzh-body pre { background: #f6f8fa; padding: 1em; border-radius: 6px; overflow-x: auto; }
            .gzh-body pre code { background: none; padding: 0; }
            .gzh-body ul, .gzh-body ol { padding-left: 1.5em; margin: 0.5em 0; }
            .gzh-body li { margin: 0.3em 0; }
        </style>
    """,
    "minimal": """
        <style>
            .gzh-body { font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #222; padding: 12px; }
            .gzh-body h1, .gzh-body h2, .gzh-body h3 { font-weight: 500; margin: 1.2em 0 0.4em; }
            .gzh-body h1 { font-size: 1.5em; }
            .gzh-body h2 { font-size: 1.25em; }
            .gzh-body h3 { font-size: 1.05em; }
            .gzh-body p { margin: 0.6em 0; }
            .gzh-body blockquote { border-left: 3px solid #ccc; margin: 0.8em 0; padding: 0.4em 0.8em; color: #555; }
            .gzh-body code { background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 2px; }
            .gzh-body pre { background: #f5f5f5; padding: 0.8em; border-radius: 4px; }
            .gzh-body ul, .gzh-body ol { padding-left: 1.5em; }
        </style>
    """,
    "elegant": """
        <style>
            .gzh-body { font-family: 'Georgia', 'Times New Roman', serif; line-height: 1.8; color: #444; padding: 20px; }
            .gzh-body h1, .gzh-body h2, .gzh-body h3 { font-weight: 400; margin: 1.5em 0 0.5em; }
            .gzh-body h1 { font-size: 1.7em; letter-spacing: 0.02em; }
            .gzh-body h2 { font-size: 1.35em; }
            .gzh-body h3 { font-size: 1.1em; }
            .gzh-body p { margin: 0.7em 0; text-align: justify; }
            .gzh-body blockquote { border-left: 2px solid #8B7355; margin: 0.8em 0; padding: 0.5em 1em; color: #666; font-style: italic; }
            .gzh-body code { background: #fafafa; padding: 0.2em 0.4em; border: 1px solid #eee; border-radius: 3px; }
            .gzh-body pre { background: #fafafa; padding: 1em; border: 1px solid #eee; border-radius: 4px; }
            .gzh-body ul, .gzh-body ol { padding-left: 1.5em; }
        </style>
    """,
    "tech": """
        <style>
            .gzh-body { font-family: 'SF Mono', 'Consolas', 'Courier New', monospace; line-height: 1.7; color: #2c3e50; padding: 16px; background: #fdfdfd; }
            .gzh-body h1, .gzh-body h2, .gzh-body h3 { font-weight: 700; margin: 1.4em 0 0.4em; }
            .gzh-body h1 { font-size: 1.5em; color: #e74c3c; }
            .gzh-body h2 { font-size: 1.25em; color: #e67e22; }
            .gzh-body h3 { font-size: 1.05em; color: #3498db; }
            .gzh-body p { margin: 0.6em 0; }
            .gzh-body blockquote { border-left: 4px solid #3498db; margin: 0.8em 0; padding: 0.5em 1em; background: #f0f6fb; color: #34495e; }
            .gzh-body code { background: #ecf0f1; padding: 0.2em 0.4em; border-radius: 3px; color: #c0392b; }
            .gzh-body pre { background: #2c3e50; padding: 1em; border-radius: 6px; color: #ecf0f1; }
            .gzh-body pre code { background: none; color: #ecf0f1; }
            .gzh-body ul, .gzh-body ol { padding-left: 1.5em; }
        </style>
    """,
    "news": """
        <style>
            .gzh-body { font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; line-height: 1.7; color: #333; padding: 16px; }
            .gzh-body h1, .gzh-body h2, .gzh-body h3 { font-weight: 700; margin: 1.2em 0 0.4em; }
            .gzh-body h1 { font-size: 1.6em; border-bottom: 3px solid #d33; padding-bottom: 0.3em; }
            .gzh-body h2 { font-size: 1.3em; background: #f8f8f8; padding: 0.3em 0.6em; border-left: 4px solid #d33; }
            .gzh-body h3 { font-size: 1.1em; }
            .gzh-body p { margin: 0.6em 0; }
            .gzh-body blockquote { border-left: 4px solid #ddd; margin: 0.8em 0; padding: 0.5em 1em; background: #fafafa; color: #555; }
            .gzh-body code { background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }
            .gzh-body pre { background: #f8f8f8; padding: 1em; border-radius: 4px; border: 1px solid #eee; }
            .gzh-body ul, .gzh-body ol { padding-left: 1.5em; }
        </style>
    """,
    "fancy": """
        <style>
            .gzh-body { font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; line-height: 1.8; color: #333; padding: 20px; background: linear-gradient(135deg, #fef9f4 0%, #fdf0e6 100%); border-radius: 8px; }
            .gzh-body h1, .gzh-body h2, .gzh-body h3 { font-weight: 600; margin: 1.3em 0 0.4em; }
            .gzh-body h1 { font-size: 1.6em; color: #c0392b; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
            .gzh-body h2 { font-size: 1.3em; color: #e67e22; }
            .gzh-body h3 { font-size: 1.1em; color: #8e44ad; }
            .gzh-body p { margin: 0.6em 0; }
            .gzh-body blockquote { border-left: 4px solid #e74c3c; margin: 0.8em 0; padding: 0.5em 1em; background: #fff5f5; border-radius: 0 4px 4px 0; }
            .gzh-body code { background: #fff; padding: 0.2em 0.4em; border-radius: 3px; border: 1px solid #f0e0d0; }
            .gzh-body pre { background: #fff; padding: 1em; border-radius: 6px; border: 1px solid #f0e0d0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .gzh-body ul, .gzh-body ol { padding-left: 1.5em; }
        </style>
    """,
}


# ---------------------------------------------------------------------------
# 核心数据结构与解析函数
# ---------------------------------------------------------------------------

# 块类型枚举
BLOCK_TYPES = {
    "heading": "heading",
    "paragraph": "paragraph",
    "list": "list",
    "quote": "quote",
    "code": "code",
}


def parse_markdown(text: str) -> List[Dict]:
    """
    将 Markdown 文本解析为结构化块列表。

    参数:
        text: 原始 Markdown 字符串

    返回:
        块列表，每个块是包含 type 和 content 的字典。
        可能抛出 ValueError (E003) 或 RuntimeError (E006)。
    """
    if not text or not text.strip():
        raise ValueError("E001: 输入为空")

    lines = text.splitlines()
    blocks: List[Dict] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].rstrip()

        # 空行跳过
        if not line.strip():
            i += 1
            continue

        # 代码块（以
