#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obsidian-skills — 笔记自动化与知识库构建工具

功能概述：
    将任意数据、文件或URL转换为结构化Obsidian笔记，
    支持YAML frontmatter生成、元数据提取、置信度标注与批量处理。

用法示例：
    python main.py --input sample.txt --output notes/
    python main.py --selftest
"""

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数值无效",
    "E002": "文件读取失败：文件不存在、无权限或无法解码",
    "E003": "文件写入失败：目标目录不可写或磁盘空间不足",
    "E004": "URL访问失败：网络不可达、超时或返回非200状态",
    "E005": "数据解析失败：无法从输入中提取有效内容",
    "E006": "模板渲染失败：模板语法错误或变量缺失",
    "E007": "批量处理中断：某个文件处理失败导致整体中止",
    "E008": "自检失败：核心逻辑验证未通过",
    "E009": "不支持的输入类型：无法识别的文件格式或URL协议",
    "E010": "内部错误：未预期的异常发生",
}


def fail(code: str, message: str = "") -> None:
    """抛出带错误码的异常。"""
    detail = ERROR_CODES.get(code, "未知错误")
    if message:
        raise RuntimeError(f"[{code}] {detail}: {message}")
    raise RuntimeError(f"[{code}] {detail}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class Note:
    """表示一篇Obsidian笔记。"""

    def __init__(
        self,
        title: str = "",
        content: str = "",
        frontmatter: Optional[Dict[str, Any]] = None,
        source: str = "",
    ):
        self.title = title.strip() or "未命名笔记"
        self.content = content.strip()
        self.frontmatter = frontmatter or {}
        self.source = source

    def to_markdown(self) -> str:
        """将笔记渲染为带YAML frontmatter的Markdown字符串。"""
        lines = ["---"]
        # 确保标题始终存在
        fm = dict(self.frontmatter)
        fm.setdefault("title", self.title)
        fm.setdefault("created", datetime.date.today().isoformat())
        fm.setdefault("source", self.source)

        for key, value in fm.items():
            if isinstance(value, (list, tuple)):
                # 列表渲染为YAML数组
                items = "[" + ", ".join(f'"{str(v)}"' for v in value) + "]"
                lines.append(f"{key}: {items}")
            elif isinstance(value, bool):
                lines.append(f"{key}: {'true' if value else 'false'}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            else:
                # 字符串，进行必要的转义
                safe_value = str(value).replace('"', '\\"')
                lines.append(f'{key}: "{safe_value}"')

        lines.append("---")
        lines.append("")
        lines.append(self.content)
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Note(title={self.title!r}, content_len={len(self.content)})"


# ---------------------------------------------------------------------------
# 输入处理模块
# ---------------------------------------------------------------------------
def read_text_file(path: str) -> str:
    """读取文本文件内容。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        fail("E002", f"文件不存在: {path}")
    except PermissionError:
        fail("E002", f"无读取权限: {path}")
    except UnicodeDecodeError:
        fail("E002", f"文件不是有效的UTF-8文本: {path}")
    except Exception as e:
        fail("E010", f"读取文件异常: {e}")


def fetch_url(url: str, timeout: int = 10) -> str:
    """从URL获取文本内容。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "obsidian-skills/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                fail("E004", f"HTTP状态码 {resp.status}")
            # 尝试按UTF-8解码，失败则用replace
            raw = resp.read()
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        fail("E004", f"URL请求失败: {e.reason}")
    except TimeoutError:
        fail("E004", "请求超时")
    except Exception as e:
        fail("E010", f"URL处理异常: {e}")


def parse_csv_data(text: str) -> List[Dict[str, str]]:
    """解析CSV文本为字典列表。"""
    try:
        reader = csv.DictReader(text.splitlines())
        rows = [dict(row) for row in reader]
        if not rows:
            fail("E005", "CSV内容为空")
        return rows
    except Exception as e:
        fail("E005", f"CSV解析失败: {e}")


def parse_json_data(text: str) -> Any:
    """解析JSON文本。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        fail("E005", f"JSON解析失败: {e}")


def extract_metadata_from_text(text: str, source: str = "") -> Dict[str, Any]:
    """从原始文本中提取基础元数据。"""
    meta: Dict[str, Any] = {}

    # 提取标题（首个# 标题或第一行）
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if title_match:
        meta["title"] = title_match.group(1).strip()
    else:
        first_line = text.strip().split("\n")[0][:80] if text.strip() else "未命名"
        meta["title"] = first_line

    # 提取日期（YYYY-MM-DD格式）
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if date_match:
        meta["date"] = date_match.group(0)

    # 提取标签（#tag形式）
    tags = re.findall(r"#([a-zA-Z0-9_\-\u4e00-\u9fff]+)", text)
    if tags:
        # 去重并限制数量
        unique_tags = list(dict.fromkeys(tags))[:10]
        meta["tags"] = unique_tags

    # 提取邮箱
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if emails:
        meta["emails"] = list(dict.fromkeys(emails))[:5]

    # 提取URL
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    if urls:
        meta["urls"] = list(dict.fromkeys(urls))[:5]

    meta["source"] = source or "unknown"
    meta["char_count"] = len(text)

    return meta


def sanitize_filename(name: str) -> str:
    """将字符串转为安全的文件名。"""
    # 移除非法字符
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    # 移除控制字符
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    # 去除首尾空白和点
    name = name.strip().strip(".")
    # 限制长度
    if len(name) > 80:
        name = name[:80]
    return name or "未命名笔记"


# ---------------------------------------------------------------------------
# 笔记构建模块
# ---------------------------------------------------------------------------
def build_note_from_text(
    text: str,
    source: str = "",
    template: Optional[Dict[str, str]] = None,
) -> Note:
    """从纯文本构建笔记。"""
    meta = extract_metadata_from_text(text, source)
    title = meta.pop("title", "未命名笔记")

    # 构建正文
    content_parts = []

    # 核心内容（去除已有标题行以避免重复）
    body = re.sub(r"^#\s+.+\n?", "", text, count=1, flags=re.MULTILINE).strip()
    if body:
        content_parts.append(body)

    # 附加元数据区块
    if meta:
        content_parts.append("")
        content_parts.append("## 元数据")
        for key, value in meta.items():
            if isinstance(value, list):
                content_parts.append(f"- {key}: {', '.join(str(v) for v in value)}")
            else:
                content_parts.append(f"- {key}: {value}")

    content = "\n".join(content_parts).strip()

    # 构建frontmatter
    frontmatter = {
        "title": title,
        "source": source or "unknown",
        "created": datetime.date.today().isoformat(),
    }
    if "tags" in meta:
        frontmatter["tags"] = meta["tags"]
    if "date" in meta:
        frontmatter["date"] = meta["date"]

    return Note(title=title, content=content, frontmatter=frontmatter, source=source)


def build_note_from_csv(
    csv_text: str,
    source: str = "",
) -> List[Note]:
    """从CSV数据构建多条笔记（每行一条）。"""
    rows = parse_csv_data(csv_text)
    notes = []

    for idx, row in enumerate(rows):
        # 尝试找到标题列
        title_col = None
        for col in row.keys():
            if col and ("标题" in col or "title" in col.lower()):
                title_col = col
                break
        if title_col is None and row:
            title_col = list(row.keys())[0]

        # 提取标签列
        tags = []
        for col, val in row.items():
            if col and ("标签" in col or "tag" in col.lower()):
                tags = [t.strip() for t in val.split(",") if t.strip()]
                break

        # 构建内容
        content_lines = []
        for col, val in row.items():
            if val and col != title_col:
                content_lines.append(f"**{col}**: {val}")
        content = "\n".join(content_lines)

        title = row.get(title_col, f"记录{idx+1}") if title_col else f"记录{idx+1}"

        frontmatter = {
            "title": title,
            "source": source,
            "created": datetime.date.today().isoformat(),
        }
        if tags:
            frontmatter["tags"] = tags

        notes.append(
            Note(
                title=title,
                content=content,
                frontmatter=frontmatter,
                source=source,
            )
        )

    return notes


def build_note_from_json(
    json_text: str,
    source: str = "",
) -> Note:
    """从JSON数据构建笔记。"""
    data = parse_json_data(json_text)

    if isinstance(data, dict):
        title = str(data.get("title", data.get("name", "JSON数据")))
        # 移除已用于标题的字段
        content_data = {k: v for k, v in data.items() if k not in ("title", "name")}

        # 格式化内容
        content_lines = []
        for key, value in content_data.items():
            if isinstance(value, (dict, list)):
                content_lines.append(f"### {key}")
                content_lines.append(f"
