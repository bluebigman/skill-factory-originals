#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev-motivation-cli 独立实现脚本

面向开发者的命令行激励工具，提供规范化的数据转换与输出流程。
本脚本为 clean-room 实现，仅依据功能规格独立编写。
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_SUCCESS = 0
ERR_INVALID_ARGS = "E001"       # 参数错误
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_FILE_READ = "E003"          # 文件读取失败
ERR_FILE_WRITE = "E004"         # 文件写入失败
ERR_INVALID_FORMAT = "E005"     # 输入格式不支持
ERR_PARSE_FAILED = "E006"       # 解析失败
ERR_NETWORK = "E007"            # 网络请求失败
ERR_OUTPUT_FAILED = "E008"      # 输出失败
ERR_INTERNAL = "E009"           # 内部错误
ERR_SELFTEST = "E010"           # 自检失败


# ============================================================
# 常量定义
# ============================================================
SUPPORTED_EXTENSIONS = {".txt", ".json", ".csv", ".md"}
SUPPORTED_OUTPUT_FORMATS = {"markdown", "json"}
DATE_PATTERN = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


# ============================================================
# 工具函数
# ============================================================
def format_error(code: str, message: str) -> str:
    """格式化错误信息"""
    return f"[{code}] {message}"


def normalize_date(text: str) -> str:
    """规范化日期格式为 YYYY-MM-DD"""
    match = DATE_PATTERN.search(text)
    if not match:
        return text
    date_str = match.group()
    # 统一分隔符为 '-'
    date_str = date_str.replace("/", "-")
    parts = date_str.split("-")
    if len(parts) == 3:
        year, month, day = parts
        month = month.zfill(2)
        day = day.zfill(2)
        return f"{year}-{month}-{day}"
    return text


def normalize_number(text: str) -> str:
    """规范化数字格式，去掉多余的前导零"""
    match = NUMBER_PATTERN.search(text)
    if not match:
        return text
    num_str = match.group()
    try:
        if "." in num_str:
            num_val = float(num_str)
            # 保留最多2位小数
            return f"{num_val:.2f}".rstrip("0").rstrip(".")
        else:
            num_val = int(num_str)
            return str(num_val)
    except (ValueError, OverflowError):
        return text


def extract_key_fields(text: str) -> Dict[str, str]:
    """从文本中提取关键字段（日期、数字、代码片段等）"""
    fields = {}
    # 提取日期
    date_match = DATE_PATTERN.search(text)
    if date_match:
        fields["date"] = normalize_date(date_match.group())
    # 提取数字
    num_match = NUMBER_PATTERN.search(text)
    if num_match:
        fields["number"] = normalize_number(num_match.group())
    # 提取代码片段（简单识别包含花括号或分号的行）
    code_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if "{" in stripped or ";" in stripped or "def " in stripped:
            code_lines.append(stripped)
    if code_lines:
        fields["code_snippet"] = "\n".join(code_lines[:3])  # 最多取3行
    return fields


def confidence_placeholder(field_name: str) -> str:
    """生成置信度占位符"""
    return f"[需核实:{field_name}]"


def parse_text_content(content: str) -> Dict[str, Any]:
    """解析纯文本内容为结构化数据"""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    title = lines[0] if lines else "未命名文档"
    body_lines = lines[1:] if len(lines) > 1 else []
    
    result = {
        "title": title,
        "content": "\n".join(body_lines),
        "line_count": len(lines),
        "char_count": len(content),
        "extracted_fields": extract_key_fields(content),
        "source_type": "text",
    }
    return result


def parse_json_content(content: str) -> Dict[str, Any]:
    """解析 JSON 内容为结构化数据"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(format_error(ERR_PARSE_FAILED, f"JSON 解析失败: {e}"))
    
    if isinstance(data, dict):
        return {
            "title": str(data.get("title", data.get("name", "未命名"))),
            "content": json.dumps(data, ensure_ascii=False, indent=2),
            "data": data,
            "source_type": "json",
            "extracted_fields": extract_key_fields(json.dumps(data, ensure_ascii=False)),
        }
    elif isinstance(data, list):
        return {
            "title": f"列表数据（{len(data)} 项）",
            "content": json.dumps(data, ensure_ascii=False, indent=2),
            "data": data,
            "source_type": "json",
            "extracted_fields": {"item_count": str(len(data))},
        }
    else:
        return {
            "title": "JSON 标量数据",
            "content": str(data),
            "data": data,
            "source_type": "json",
            "extracted_fields": {},
        }


def parse_csv_content(content: str) -> Dict[str, Any]:
    """解析 CSV 内容为结构化数据"""
    try:
        reader = csv.DictReader(content.splitlines())
        rows = list(reader)
    except Exception as e:
        raise ValueError(format_error(ERR_PARSE_FAILED, f"CSV 解析失败: {e}"))
    
    if not rows:
        return {
            "title": "空 CSV 数据",
            "content": content,
            "data": [],
            "source_type": "csv",
            "extracted_fields": {},
        }
    
    fieldnames = list(rows[0].keys())
    return {
        "title": f"CSV 数据（{len(rows)} 行）",
        "content": content,
        "data": rows,
        "columns": fieldnames,
        "row_count": len(rows),
        "source_type": "csv",
        "extracted_fields": {"row_count": str(len(rows)), "columns": ", ".join(fieldnames)},
    }


def parse_markdown_content(content: str) -> Dict[str, Any]:
    """解析 Markdown 内容为结构化数据"""
    lines = content.splitlines()
    title = "未命名文档"
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    
    # 提取标题结构
    headings = []
    for line in lines:
        if re.match(r"^#{1,6}\s+", line):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            headings.append({"level": level, "text": text})
    
    return {
        "title": title,
        "content": content,
        "headings": headings,
        "line_count": len(lines),
        "source_type": "markdown",
        "extracted_fields": {
            "heading_count": str(len(headings)),
            "first_heading": headings[0]["text"] if headings else "无",
        },
    }


def parse_content(content: str, file_ext: str = ".txt") -> Dict[str, Any]:
    """根据文件扩展名解析内容"""
    ext = file_ext.lower()
    if ext == ".json":
        return parse_json_content(content)
    elif ext == ".csv":
        return parse_csv_content(content)
    elif ext == ".md":
        return parse_markdown_content(content)
    elif ext == ".txt":
        return parse_text_content(content)
    else:
        raise ValueError(format_error(ERR_INVALID_FORMAT, f"不支持的文件格式: {ext}"))


def read_source(source: str) -> Tuple[str, str]:
    """
    读取数据源内容
    返回 (内容, 扩展名)
    """
    # 检查是否为 URL
    if source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            # 从 URL 猜测扩展名
            path = urllib.request.urlparse(source).path
            ext = Path(path).suffix or ".txt"
            return content, ext
        except Exception as e:
            raise ValueError(format_error(ERR_NETWORK, f"网络请求失败: {e}"))
    
    # 检查是否为文件路径
    if os.path.isfile(source):
        ext = Path(source).suffix or ".txt"
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(format_error(ERR_INVALID_FORMAT, f"不支持的文件格式: {ext}"))
        try:
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return content, ext
        except Exception as e:
            raise ValueError(format_error(ERR_FILE_READ, f"文件读取失败: {e}"))
    
    # 否则视为直接文本输入
    return source, ".txt"


def format_markdown_output(data: Dict[str, Any]) -> str:
    """格式化输出为 Markdown"""
    lines = []
    lines.append(f"# {data.get('title', '未命名')}")
    lines.append("")
    lines.append(f"> 来源类型: {data.get('source_type', '未知')}")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 输出提取的关键字段
    extracted = data.get("extracted_fields", {})
    if extracted:
        lines.append("## 提取的关键字段")
        lines.append("")
        lines.append("| 字段 | 值 |")
        lines.append("|------|-----|")
        for key, value in extracted.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
    
    # 输出内容主体
    lines.append("## 内容")
    lines.append("")
    content = data.get("content", "")
    if content:
        lines.append("
