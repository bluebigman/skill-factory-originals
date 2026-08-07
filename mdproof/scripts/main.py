#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mdproof — Markdown 转 PDF 排版校验工具（clean-room 独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
仅使用 Python 标准库，无第三方依赖。

主要功能：
1. Markdown 基础格式校验（标题层级、链接、图片路径）
2. 排版规范检查（标题层级跳级、代码块闭合、表格格式）
3. 生成简易 PDF 输出（基于文本布局的极简 PDF 生成器）
4. 批量处理（最多 50 个文件/批次）
5. 内置自检模式（--selftest）

用法示例：
    python scripts/main.py input.md                    # 转换单个文件
    python scripts/main.py a.md b.md c.md              # 批量转换
    python scripts/main.py --check input.md            # 仅校验不转换
    python scripts/main.py --selftest                  # 运行内置自检
"""

import argparse
import os
import re
import sys
import zlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ──────────────────────────── 错误码定义 ────────────────────────────
# E001: 文件不存在
# E002: 文件读取失败
# E003: 文件写入失败
# E004: 不支持的文件格式
# E005: Markdown 语法错误（标题层级跳级）
# E006: Markdown 语法错误（代码块未闭合）
# E007: Markdown 语法错误（表格格式异常）
# E008: 链接格式错误
# E009: 图片路径异常
# E010: 批量处理超过限制

# ──────────────────────────── 常量定义 ────────────────────────────
MAX_BATCH_SIZE = 50  # 最大批量处理文件数
MAX_TITLE_LEVEL = 6  # 最大标题层级（Markdown 规范）
DEFAULT_FONT_SIZE = 12  # 默认字号
DEFAULT_MARGIN = 72  # 默认页边距（磅值，1英寸=72磅）
PAGE_WIDTH = 612  # Letter 纸宽度（磅）
PAGE_HEIGHT = 792  # Letter 纸高度（磅）
LINE_HEIGHT = 14  # 行高（磅）


class MDProofError(Exception):
    """mdproof 自定义异常类"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ──────────────────────────── 工具函数 ────────────────────────────

def read_file(filepath: str) -> str:
    """读取文件内容，返回字符串。

    参数:
        filepath: 文件路径

    返回:
        文件内容字符串

    异常:
        MDProofError: E001 文件不存在 / E002 读取失败
    """
    path = Path(filepath)
    if not path.exists():
        raise MDProofError("E001", f"文件不存在: {filepath}")
    if not path.is_file():
        raise MDProofError("E001", f"路径不是文件: {filepath}")
    try:
        # 尝试 UTF-8 编码读取
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # 回退到 GBK 编码
        try:
            return path.read_text(encoding="gbk")
        except Exception as exc:
            raise MDProofError("E002", f"文件读取失败（编码不支持）: {filepath}") from exc
    except Exception as exc:
        raise MDProofError("E002", f"文件读取失败: {filepath}") from exc


def write_file(filepath: str, content: bytes) -> None:
    """写入二进制内容到文件。

    参数:
        filepath: 文件路径
        content: 二进制内容

    异常:
        MDProofError: E003 写入失败
    """
    try:
        with open(filepath, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise MDProofError("E003", f"文件写入失败: {filepath}") from exc


def extract_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """提取 YAML frontmatter（如果存在）。

    参数:
        content: Markdown 原始内容

    返回:
        (frontmatter_dict, 去除 frontmatter 后的内容)
    """
    # 检查是否以 --- 开头
    if not content.startswith("---"):
        return {}, content

    # 查找第二个 --- 的位置
    lines = content.split("\n")
    if len(lines) < 3:
        return {}, content

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, content

    # 解析 frontmatter 中的键值对
    frontmatter = {}
    for line in lines[1:end_idx]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    # 返回 frontmatter 和剩余内容
    remaining = "\n".join(lines[end_idx + 1:])
    return frontmatter, remaining


def parse_title_level(line: str) -> Optional[int]:
    """解析标题层级。

    参数:
        line: 一行文本

    返回:
        标题层级（1-6），如果不是标题返回 None
    """
    match = re.match(r"^(#{1,6})\s+(.+)", line)
    if match:
        return len(match.group(1))
    return None


def check_title_hierarchy(lines: List[str]) -> List[str]:
    """检查标题层级是否跳级。

    参数:
        lines: Markdown 行列表

    返回:
        错误信息列表
    """
    errors = []
    last_level = 0  # 0 表示还没有标题

    for idx, line in enumerate(lines, 1):
        level = parse_title_level(line)
        if level is None:
            continue

        # 第一个标题可以是任意级别
        if last_level == 0:
            last_level = level
            continue

        # 检查是否跳级
        if level > last_level + 1:
            errors.append(
                f"E005: 第 {idx} 行标题层级跳级（{last_level} → {level}），"
                f"建议使用层级 {last_level + 1}"
            )

        last_level = level

    return errors


def check_code_blocks(lines: List[str]) -> List[str]:
    """检查代码块是否闭合。

    参数:
        lines: Markdown 行列表

    返回:
        错误信息列表
    """
    errors = []
    in_code_block = False
    fence_char = ""
    fence_len = 0
    block_start = 0

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()

        # 检查是否为围栏（
