#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context-mode 技能实现脚本

功能：
- 工具输出压缩：将冗长文本压缩为结构化摘要
- 会话记忆持久化：将关键信息写入会话记忆文件
- 关键信息提取：从原始数据中识别核心事实与数字
- 结构化格式输出：支持 Markdown 表格、键值对、JSON 三种格式
- 批量处理：支持多个输入源与自定义输出字段

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用级异常基类，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def err_invalid_input(msg: str) -> AppError:
    """E001：输入参数无效"""
    return AppError("E001", msg)


def err_file_read(msg: str) -> AppError:
    """E002：文件读取失败"""
    return AppError("E002", msg)


def err_file_write(msg: str) -> AppError:
    """E003：文件写入失败"""
    return AppError("E003", msg)


def err_unsupported_format(msg: str) -> AppError:
    """E004：不支持的输出格式"""
    return AppError("E004", msg)


def err_missing_field(msg: str) -> AppError:
    """E005：缺少必要字段"""
    return AppError("E005", msg)


def err_invalid_json(msg: str) -> AppError:
    """E006：JSON 解析失败"""
    return AppError("E006", msg)


def err_empty_input(msg: str) -> AppError:
    """E007：输入内容为空"""
    return AppError("E007", msg)


def err_memory_file(msg: str) -> AppError:
    """E008：会话记忆文件操作失败"""
    return AppError("E008", msg)


def err_batch_failed(msg: str) -> AppError:
    """E009：批量处理失败"""
    return AppError("E009", msg)


def err_internal(msg: str) -> AppError:
    """E010：内部未知错误"""
    return AppError("E010", msg)


# ============================================================
# 核心数据结构
# ============================================================
class CompressionResult:
    """压缩结果的数据结构。"""
    def __init__(self, original_size: int, compressed_size: int, lines: int, summary: str):
        self.original_size = original_size      # 原始字节数
        self.compressed_size = compressed_size  # 压缩后字节数
        self.lines = lines                      # 原始行数
        self.summary = summary                  # 压缩摘要文本
        self.created_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "lines": self.lines,
            "summary": self.summary,
            "created_at": self.created_at,
        }


class SessionMemory:
    """会话记忆的持久化存储。"""
    def __init__(self, filepath: Optional[str] = None):
        # 默认使用临时目录下的记忆文件，保证任何环境可运行
        if filepath is None:
            tmp_dir = tempfile.gettempdir()
            filepath = os.path.join(tmp_dir, "context_mode_memory.json")
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self) -> None:
        """确保记忆文件存在且是合法 JSON。"""
        try:
            if not os.path.exists(self.filepath):
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump({"entries": []}, f, ensure_ascii=False, indent=2)
            else:
                # 验证现有文件是否为合法 JSON
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "entries" not in data:
                    raise ValueError("记忆文件格式不正确")
        except (OSError, ValueError) as e:
            raise err_memory_file(f"无法初始化记忆文件 {self.filepath}: {e}")

    def add_entry(self, key: str, content: str) -> None:
        """添加一条记忆记录。"""
        if not key or not content:
            raise err_invalid_input("记忆的键和内容不能为空")
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["entries"].append({
                "key": key,
                "content": content,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise err_memory_file(f"写入记忆文件失败: {e}")

    def get_entry(self, key: str) -> Optional[Dict[str, Any]]:
        """按键获取记忆记录。"""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data["entries"]:
                if entry["key"] == key:
                    return entry
            return None
        except OSError as e:
            raise err_memory_file(f"读取记忆文件失败: {e}")

    def list_keys(self) -> List[str]:
        """列出所有记忆键。"""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [entry["key"] for entry in data["entries"]]
        except OSError as e:
            raise err_memory_file(f"读取记忆文件失败: {e}")


# ============================================================
# 核心逻辑：文本压缩与信息提取
# ============================================================
class TextCompressor:
    """文本压缩器，负责将冗长文本转为结构化摘要。"""

    # 常见的无意义行（日志噪音、重复分隔线等）
    NOISE_PATTERNS = [
        r"^\s*[-=_*#]{3,}\s*$",       # 纯分隔线
        r"^\s*$",                      # 空行
        r"^\s*(INFO|DEBUG|TRACE)\s*:", # 低级别日志前缀
    ]

    # 关键信息识别模式（数字、错误、警告、结论等）
    KEY_PATTERNS = [
        (r"error|exception|failed|失败|错误", "错误信息"),
        (r"warning|warn|警告", "警告信息"),
        (r"\b\d{1,3}(,\d{3})*(\.\d+)?\b", "数字"),
        (r"success|成功|完成|passed|通过", "成功信息"),
        (r"conclusion|结论|result|结果", "结论"),
    ]

    def __init__(self, max_lines: int = 30):
        self.max_lines = max_lines

    def compress(self, text: str) -> CompressionResult:
        """压缩文本，返回结构化结果。"""
        if not text or not text.strip():
            raise err_empty_input("输入文本为空，无法压缩")

        original_size = len(text.encode("utf-8"))
        lines = text.splitlines()
        line_count = len(lines)

        # 过滤噪音行
        meaningful_lines = self._filter_noise(lines)

        # 提取关键信息
        key_info = self._extract_key_info(text)

        # 生成摘要
        summary = self._build_summary(meaningful_lines, key_info)

        compressed_size = len(summary.encode("utf-8"))

        return CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            lines=line_count,
            summary=summary,
        )

    def _filter_noise(self, lines: List[str]) -> List[str]:
        """过滤噪音行，保留有意义的行。"""
        result = []
        for line in lines:
            is_noise = False
            for pattern in self.NOISE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    is_noise = True
                    break
            if not is_noise:
                result.append(line.strip())
        return result

    def _extract_key_info(self, text: str) -> Dict[str, List[str]]:
        """提取关键信息，按类别分组。"""
        info: Dict[str, List[str]] = {}
        for pattern, category in self.KEY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # 去重并限制数量
                unique = list(dict.fromkeys(matches))[:5]
                info[category] = unique
        return info

    def _build_summary(self, lines: List[str], key_info: Dict[str, List[str]]) -> str:
        """构建压缩摘要文本。"""
        parts = []

        # 统计信息
        total_lines = len(lines)
        parts.append(f"有效内容行数：{total_lines}")

        # 关键信息摘要
        if key_info:
            parts.append("关键信息：")
            for category, items in key_info.items():
                items_str = "、".join(items[:3])
                parts.append(f"  - {category}: {items_str}")

        # 保留前若干行有意义内容
        if lines:
            parts.append("内容预览：")
            preview_lines = lines[:self.max_lines]
            for line in preview_lines:
                # 截断过长的行
                if len(line) > 100:
                    line = line[:97] + "..."
                parts.append(f"  {line}")

            if len(lines) > self.max_lines:
                parts.append(f"  ... 共省略 {len(lines) - self.max_lines} 行")

        return "\n".join(parts)


# ============================================================
# 结构化输出格式化
# ============================================================
class OutputFormatter:
    """将压缩结果格式化为指定格式。"""

    @staticmethod
    def format(result: CompressionResult, fmt: str = "markdown") -> str:
        """按指定格式输出。"""
        fmt = fmt.lower()
        if fmt == "markdown":
            return OutputFormatter._to_markdown(result)
        elif fmt == "json":
            return OutputFormatter._to_json(result)
        elif fmt == "kv":
            return OutputFormatter._to_kv(result)
        else:
            raise err_unsupported_format(f"不支持的输出格式：{fmt}")

    @staticmethod
    def _to_markdown(result: CompressionResult) -> str:
        """Markdown 表格格式。"""
        lines = [
            "| 项目 | 值 |",
            "|------|-----|",
            f"| 原始大小 | {result.original_size} 字节 |",
            f"| 压缩后大小 | {result.compressed_size} 字节 |",
            f"| 压缩率 | {OutputFormatter._ratio(result.original_size, result.compressed_size)}% |",
            f"| 原始行数 | {result.lines} |",
            "",
            "## 压缩摘要",
            "",
            "
