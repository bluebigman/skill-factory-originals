#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

依据功能规格独立实现（clean-room）：
将用户输入的数据、文件或链接，按规范转换为结构化结果并输出。
仅使用 Python 标准库，无第三方依赖。

用法示例：
    python scripts/main.py --input "hello world" --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# ------------------------------------------------------------
# 错误码定义（E001-E010）
# ------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "输入格式错误：无法解析输入内容",
    "E003": "文件读取失败：文件不存在或不可读",
    "E004": "URL 格式错误：无法识别链接",
    "E005": "输出格式错误：不支持的输出格式",
    "E006": "批量处理失败：某条记录处理出错",
    "E007": "敏感信息检测：拒绝处理包含敏感字段的内容",
    "E008": "内部逻辑错误：数据转换异常",
    "E009": "自检失败：核心逻辑验证未通过",
    "E010": "未知错误：未预期的异常",
}

# 敏感字段关键词（用于 E007 检测）
SENSITIVE_KEYWORDS = [
    "password", "passwd", "secret", "api_key", "apikey",
    "token", "private_key", "credential", "密码", "密钥", "令牌",
]

# 置信度标注（高/中/低）
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"


def raise_error(code: str, message: str = "") -> None:
    """抛出带错误码的异常。"""
    default_msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    full_msg = f"[{code}] {message or default_msg}"
    raise RuntimeError(full_msg)


# ------------------------------------------------------------
# 核心逻辑：输入解析、信息提取、结构化输出
# ------------------------------------------------------------
def detect_sensitive_info(text: str) -> bool:
    """检测输入中是否包含敏感信息关键词。"""
    lower_text = text.lower()
    for kw in SENSITIVE_KEYWORDS:
        if kw.lower() in lower_text:
            return True
    return False


def parse_input_text(text: str) -> dict:
    """
    解析输入文本，提取关键信息。

    返回结构：
    {
        "raw_text": 原始输入,
        "char_count": 字符数,
        "word_count": 单词数（按空白分割）,
        "line_count": 行数,
        "has_url": 是否包含 URL,
        "has_email": 是否包含邮箱,
        "language_hint": 语言提示（中/英/混合/未知）,
        "keywords": 关键词列表（长度>3的词）,
        "confidence": 置信度,
    }
    """
    if not text or not text.strip():
        raise_error("E002", "输入内容为空")

    # 敏感信息检测
    if detect_sensitive_info(text):
        raise_error("E007", "检测到敏感信息关键词，已拒绝处理")

    # 基础统计
    char_count = len(text)
    words = re.findall(r"\S+", text)
    word_count = len(words)
    line_count = text.count("\n") + 1

    # URL 检测
    url_pattern = r"https?://[^\s]+"
    has_url = bool(re.search(url_pattern, text))

    # 邮箱检测
    email_pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
    has_email = bool(re.search(email_pattern, text))

    # 语言提示（简单判断：中文字符比例）
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    chinese_ratio = len(chinese_chars) / max(char_count, 1)
    if chinese_ratio > 0.5:
        language_hint = "中文"
    elif chinese_ratio < 0.1:
        language_hint = "英文"
    elif chinese_ratio > 0.0:
        language_hint = "混合"
    else:
        language_hint = "未知"

    # 关键词提取（长度大于3的单词或连续中文）
    keywords = []
    for w in words:
        clean = w.strip(".,;:!?()[]{}'\"")
        if len(clean) > 3 and clean not in keywords:
            keywords.append(clean)
    for c in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if c not in keywords:
            keywords.append(c)
    keywords = keywords[:10]  # 最多取10个

    # 置信度：根据输入完整度给出
    if char_count > 100 and word_count > 10:
        confidence = CONFIDENCE_HIGH
    elif char_count > 30 and word_count > 3:
        confidence = CONFIDENCE_MEDIUM
    else:
        confidence = CONFIDENCE_LOW

    return {
        "raw_text": text,
        "char_count": char_count,
        "word_count": word_count,
        "line_count": line_count,
        "has_url": has_url,
        "has_email": has_email,
        "language_hint": language_hint,
        "keywords": keywords,
        "confidence": confidence,
    }


def parse_input_file(file_path: str) -> dict:
    """从文件读取内容并解析。"""
    try:
        path = Path(file_path)
        if not path.is_file():
            raise_error("E003", f"文件不存在: {file_path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return parse_input_text(content)
    except RuntimeError:
        raise
    except Exception as e:
        raise_error("E003", f"读取文件失败: {str(e)}")


def parse_input_url(url: str) -> dict:
    """解析 URL 链接（仅验证格式，不访问网络）。"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise_error("E004", f"无效 URL: {url}")
        # 不访问网络，仅返回 URL 的元信息
        return {
            "url": url,
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path or "/",
            "query": parsed.query,
            "confidence": CONFIDENCE_HIGH,
            "note": "URL 未访问，仅做格式验证",
        }
    except RuntimeError:
        raise
    except Exception as e:
        raise_error("E004", f"URL 解析失败: {str(e)}")


def process_batch(items: list, output_format: str = "json") -> list:
    """批量处理多条输入记录。"""
    results = []
    for idx, item in enumerate(items):
        try:
            if isinstance(item, dict):
                # 已结构化数据
                results.append(item)
            else:
                text = str(item)
                if text.startswith(("http://", "https://")):
                    results.append(parse_input_url(text))
                elif Path(text).is_file():
                    results.append(parse_input_file(text))
                else:
                    results.append(parse_input_text(text))
        except RuntimeError as e:
            # 单条失败不中断，记录错误信息
            results.append({
                "error": str(e),
                "index": idx,
                "raw": str(item),
                "confidence": CONFIDENCE_LOW,
            })
    return results


def format_output(data, output_format: str) -> str:
    """将数据转为指定格式输出。"""
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        return _to_markdown(data)
    else:
        raise_error("E005", f"不支持的输出格式: {output_format}")


def _to_markdown(data) -> str:
    """将结构化数据转为 Markdown 表格。"""
    lines = []
    if isinstance(data, dict):
        lines.append("| 字段 | 值 |")
        lines.append("|------|-----|")
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            # 防止表格格式破坏
            value_str = value_str.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {key} | {value_str} |")
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            keys = list(data[0].keys())
            lines.append("| " + " | ".join(keys) + " |")
            lines.append("|" + "---|" * len(keys))
            for item in data:
                row = []
                for k in keys:
                    v = item.get(k, "")
                    if isinstance(v, (list, dict)):
                        v = json.dumps(v, ensure_ascii=False)
                    row.append(str(v).replace("|", "\\|").replace("\n", " "))
                lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append("
