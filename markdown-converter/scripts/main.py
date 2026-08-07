#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-converter 技能独立实现（clean-room）
功能：将文本数据、本地文件或URL转换为结构化Markdown结果，
      保留关键信息并标注置信度。
版本：1.0.1
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# ============================================================
# 错误码定义
# E001: 参数错误
# E002: 文件不存在
# E003: 文件读取失败
# E004: URL 访问失败
# E005: 不支持的输入类型
# E006: 内容解析失败
# E007: 输出写入失败
# E008: 内部逻辑错误
# E009: 无效的元数据
# E010: 自检失败
# ============================================================

class MarkdownConverterError(Exception):
    """技能统一异常类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class MarkdownConverter:
    """
    核心转换器：将各类输入转换为结构化 Markdown。
    支持输入类型：文本字符串、本地文件路径、URL。
    """

    # 支持的本地文件扩展名
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".text"}

    def __init__(self, include_confidence: bool = True, include_metadata: bool = True):
        self.include_confidence = include_confidence
        self.include_metadata = include_metadata

    # --------------------------------------------------------
    # 公开接口
    # --------------------------------------------------------
    def convert(self, source: str, source_type: str = "auto") -> str:
        """
        将输入转换为 Markdown。
        source_type: auto / text / file / url
        """
        try:
            content, meta = self._load_source(source, source_type)
            md_body = self._parse_content(content)
            return self._assemble_output(md_body, meta)
        except MarkdownConverterError:
            raise
        except Exception as exc:
            raise MarkdownConverterError("E008", f"内部处理失败: {exc}") from exc

    def convert_batch(self, sources: list) -> list:
        """批量转换多个输入，返回 Markdown 列表"""
        results = []
        for src in sources:
            try:
                results.append(self.convert(src))
            except MarkdownConverterError as exc:
                results.append(f"> ⚠️ 转换失败: {exc.code} - {exc.message}\n")
        return results

    # --------------------------------------------------------
    # 输入加载
    # --------------------------------------------------------
    def _load_source(self, source: str, source_type: str) -> tuple:
        """加载源数据，返回 (内容文本, 元数据字典)"""
        source_type = (source_type or "auto").lower()
        meta = {
            "source": source[:200] if source else "",
            "type": source_type,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "char_count": 0,
            "line_count": 0,
        }

        # 自动检测类型
        if source_type == "auto":
            source_type = self._detect_type(source)

        # 按类型加载
        if source_type == "text":
            content = source
            meta["type"] = "text"
        elif source_type == "file":
            content, meta["file_path"] = self._load_file(source)
            meta["type"] = "file"
        elif source_type == "url":
            content = self._load_url(source)
            meta["type"] = "url"
            meta["url"] = source
        else:
            raise MarkdownConverterError("E005", f"不支持的输入类型: {source_type}")

        # 基础统计
        meta["char_count"] = len(content)
        meta["line_count"] = content.count("\n") + 1
        return content, meta

    def _detect_type(self, source: str) -> str:
        """自动检测输入类型"""
        # URL 检测
        if source.startswith(("http://", "https://")):
            return "url"
        # 文件路径检测
        if self._is_valid_file_path(source):
            return "file"
        # 默认按文本处理
        return "text"

    def _is_valid_file_path(self, path: str) -> bool:
        """检查是否为有效文件路径"""
        if len(path) > 500 or "\n" in path:
            return False
        p = Path(path)
        # 检查扩展名
        if p.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False
        # 检查是否存在
        return p.exists() and p.is_file()

    def _load_file(self, path: str) -> tuple:
        """读取本地文件"""
        p = Path(path)
        if not p.exists():
            raise MarkdownConverterError("E002", f"文件不存在: {path}")
        if not p.is_file():
            raise MarkdownConverterError("E002", f"不是文件: {path}")
        try:
            # 尝试 UTF-8，失败则尝试 GBK
            try:
                content = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = p.read_text(encoding="gbk", errors="replace")
            return content, str(p.resolve())
        except OSError as exc:
            raise MarkdownConverterError("E003", f"文件读取失败: {exc}") from exc

    def _load_url(self, url: str) -> str:
        """获取 URL 内容"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
                # 尝试解码
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except Exception as exc:
            raise MarkdownConverterError("E004", f"URL 访问失败: {exc}") from exc

    # --------------------------------------------------------
    # 内容解析（核心逻辑）
    # --------------------------------------------------------
    def _parse_content(self, content: str) -> str:
        """
        将纯文本解析为结构化 Markdown。
        规则：
        - 以 # 开头的行视为标题
        - 以 - 或 * 开头的行视为无序列表
        - 以数字. 开头的行视为有序列表
        - 以 | 分隔的行视为表格
        - 以
