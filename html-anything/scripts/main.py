#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - html-anything 技能核心实现

功能概述：
    将数据（JSON/CSV/YAML/纯文本/Markdown）或 URL 转换为结构化 HTML，
    支持批量生成与自定义模板格式。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。

自检方式：
    python scripts/main.py --selftest
"""

import argparse
import csv
import html
import io
import json
import re
import sys
import urllib.request
from typing import Any, Dict, List, Optional, Union

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "文件解析失败：内容格式不符合预期",
    "E004": "URL访问失败：网络不可达或HTTP错误",
    "E005": "模板渲染失败：模板语法错误或变量缺失",
    "E006": "数据格式不支持：仅支持JSON/CSV/YAML/纯文本/Markdown",
    "E007": "批量生成失败：数据条目为空或结构异常",
    "E008": "HTML转义失败：特殊字符处理异常",
    "E009": "输出写入失败：无法写入目标文件",
    "E010": "内部逻辑错误：未知异常",
}

# 支持的输入格式
SUPPORTED_FORMATS = ("json", "csv", "yaml", "txt", "md", "markdown")


def _error(code: str, detail: str = "") -> str:
    """构造标准错误信息"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        msg = f"{msg}：{detail}"
    return f"[{code}] {msg}"


def _escape_html(text: Any) -> str:
    """HTML 转义，防止 XSS 与特殊字符破坏页面结构"""
    try:
        return html.escape(str(text), quote=True)
    except Exception as exc:
        raise ValueError(_error("E008", str(exc)))


def _read_text_file(filepath: str) -> str:
    """读取文本文件内容（支持 UTF-8 与常见编码回退）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # 回退到 GBK 编码尝试
        try:
            with open(filepath, "r", encoding="gbk") as f:
                return f.read()
        except Exception as exc:
            raise IOError(_error("E002", str(exc)))
    except Exception as exc:
        raise IOError(_error("E002", str(exc)))


def _parse_json(text: str) -> Any:
    """解析 JSON 字符串"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(_error("E003", f"JSON 解析失败: {exc}"))


def _parse_csv(text: str) -> List[Dict[str, str]]:
    """解析 CSV 字符串为字典列表（首行为表头）"""
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(row) for row in reader]
        if not rows:
            raise ValueError(_error("E003", "CSV 内容为空或缺少表头"))
        return rows
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(_error("E003", f"CSV 解析失败: {exc}"))


def _parse_yaml(text: str) -> Any:
    """解析 YAML 字符串（使用 PyYAML，若未安装则报错）"""
    try:
        import yaml  # pip install pyyaml
    except ImportError:
        raise ImportError(_error("E006", "缺少 PyYAML 库，请先安装：pip install pyyaml"))

    try:
        return yaml.safe_load(text)
    except Exception as exc:
        raise ValueError(_error("E003", f"YAML 解析失败: {exc}"))


def _parse_markdown(text: str) -> str:
    """将 Markdown 文本转换为简单 HTML（仅支持基础语法）"""
    lines = text.splitlines()
    html_parts: List[str] = []
    in_list = False
    in_code_block = False
    code_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        # 代码块开始/结束
        if stripped.startswith("
