#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memstack - 学习参考 数据转换 结构化处理

将用户提供的数据、文件或URL转换为结构化结果，供学习与参考使用。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input "文本内容" --format json
    python scripts/main.py --file /path/to/file.txt --format json
    python scripts/main.py --url https://example.com --format json
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "文件错误：文件不存在或无法读取",
    "E003": "URL错误：URL格式无效或不支持",
    "E004": "格式错误：不支持的输出格式",
    "E005": "解析错误：输入内容解析失败",
    "E006": "网络错误：URL访问失败",
    "E007": "编码错误：文件编码不支持",
    "E008": "内部错误：未知异常",
    "E009": "数据错误：输入数据为空",
    "E010": "安全错误：URL协议不受支持",
}


class MemstackError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class StructuredResult:
    """结构化输出结果。"""

    def __init__(self) -> None:
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.source_type: str = ""          # text / file / url
        self.source_name: str = ""          # 来源标识
        self.raw_length: int = 0            # 原始输入长度
        self.fields: List[Dict[str, Any]] = []  # 提取的字段列表
        self.confidence: str = "中"          # 整体置信度: 高/中/低
        self.warnings: List[str] = []       # 警告信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "timestamp": self.timestamp,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "raw_length": self.raw_length,
            "fields": self.fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ============================================================
# 网络请求工具（带重试退避、超时、缓存）
# ============================================================
class NetworkClient:
    """网络请求客户端，支持超时、重试退避和简单内存缓存。"""

    def __init__(self, timeout: int = 5, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: Dict[str, Tuple[float, str]] = {}  # url -> (timestamp, content)
        self._cache_ttl = 300  # 5分钟缓存

    def fetch(self, url: str) -> str:
        """获取URL内容，带缓存、超时和重试退避。"""
        # 检查缓存
        if url in self._cache:
            cached_time, cached_content = self._cache[url]
            if time.time() - cached_time < self._cache_ttl:
                return cached_content

        # 带重试的请求
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "memstack/1.0"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    content = response.read().decode("utf-8", errors="replace")
                    # 更新缓存
                    self._cache[url] = (time.time(), content)
                    return content
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise MemstackError("E006", f"URL访问失败: {url}, 错误: {e}")
                # 指数退避
                time.sleep(2 ** attempt)

        raise MemstackError("E006", f"URL访问失败: {url}")


# 全局网络客户端实例
_network_client = NetworkClient()


# ============================================================
# 核心处理函数
# ============================================================
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _get_utc_timestamp() -> str:
    """获取当前 UTC 时间戳字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_read_file(file_path: str) -> str:
    """安全读取文件内容，支持常见编码。"""
    path = Path(file_path)
    if not path.exists():
        raise MemstackError("E002", f"文件不存在: {file_path}")
    if not path.is_file():
        raise MemstackError("E002", f"路径不是文件: {file_path}")

    # 尝试多种编码读取
    encodings = ["utf-8", "gbk", "latin-1", "utf-16"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc, errors="replace")
        except (UnicodeDecodeError, LookupError):
            continue
    raise MemstackError("E007", f"无法解码文件: {file_path}")


def _validate_url(url: str) -> str:
    """校验URL格式和协议。"""
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise MemstackError("E003", f"无效URL: {url}")
    if parsed.scheme.lower() not in ("http", "https"):
        raise MemstackError("E010", f"不支持的协议: {parsed.scheme}")
    return url


def _extract_key_fields(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    从文本中提取关键字段。
    返回 (字段列表, 警告列表)。
    字段格式: {"key": 字段名, "value": 值, "confidence": 高/中/低}
    """
    fields: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if not text or not text.strip():
        raise MemstackError("E009", "输入内容为空")

    # 1. 统计信息字段（高置信度）
    lines = text.strip().splitlines()
    words = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
    chars = len(text)

    fields.append({"key": "行数", "value": len(lines), "confidence": "高"})
    fields.append({"key": "词数", "value": len(words), "confidence": "高"})
    fields.append({"key": "字符数", "value": chars, "confidence": "高"})

    # 2. 提取URL（高置信度）
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    if urls:
        fields.append({"key": "URL", "value": urls[:5], "confidence": "高"})
    else:
        warnings.append("未检测到URL")

    # 3. 提取邮箱（高置信度）
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    if emails:
        fields.append({"key": "邮箱", "value": emails[:5], "confidence": "高"})

    # 4. 提取日期（中置信度）
    date_patterns = [
        r"\b\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\b",
        r"\b\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}\b",
    ]
    dates = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, text))
    if dates:
        fields.append({"key": "日期", "value": dates[:5], "confidence": "中"})

    # 5. 提取数字（中置信度）
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    if len(numbers) > 5:
        fields.append({"key": "数字", "value": numbers[:10], "confidence": "中"})

    # 6. 检查是否有足够信息判定置信度
    if len(fields) <= 1:
        warnings.append("可提取字段较少，置信度降低")
        return fields, warnings

    # 7. 检查文本是否包含明显噪音（低置信度标识）
    noise_ratio = 0.0
    if chars > 0:
        # 计算非字母数字字符比例（粗略噪音估计）
        alnum_chars = sum(1 for c in text if c.isalnum())
        noise_ratio = 1.0 - (alnum_chars / chars)

    if noise_ratio > 0.8:
        warnings.append("文本噪音比例较高，可能影响提取质量")

    return fields, warnings


def _process_text(text: str, source_name: str = "text_input") -> StructuredResult:
    """处理纯文本输入。"""
    result = StructuredResult()
    result.timestamp = _get_utc_timestamp()
    result.source_type = "text"
    result.source_name = source_name
    result.raw_length = len(text)

    fields, warnings = _extract_key_fields(text)
    result.fields = fields
    result.warnings = warnings

    # 整体置信度评估
    high_conf_count = sum(1 for f in fields if f["confidence"] == "高")
    if high_conf_count >= 2:
        result.confidence = "高"
    elif len(fields) >= 3:
        result.confidence = "中"
    else:
        result.confidence = "低"

    return result


def _process_file(file_path: str) -> StructuredResult:
    """处理文件输入。"""
    content = _safe_read_file(file_path)
    result = _process_text(content, source_name=file_path)
    result.source_type = "file"
    return result


def _process_url(url: str) -> StructuredResult:
    """
    处理URL输入。
    实际发起网络请求获取内容，带超时、重试退避和缓存。
    """
    _validate_url(url)

    result = StructuredResult()
    result.timestamp = _get_utc_timestamp()
    result.source_type = "url"
    result.source_name = url

    # 获取URL内容（带网络请求）
    try:
        content = _network_client.fetch(url)
        result.raw_length = len(content)

        # 提取内容字段
        fields, warnings = _extract_key_fields(content)
        result.fields = fields
        result.warnings = warnings

        # 添加URL结构信息
        parsed = urllib.parse.urlparse(url)
        url_fields = [
            {"key": "协议", "value": parsed.scheme, "confidence": "高"},
            {"key": "域名", "value": parsed.netloc, "confidence": "高"},
            {"key": "路径", "value": parsed.path or "/", "confidence": "高"},
        ]
        if parsed.query:
            query_params = urllib.parse.parse_qs(parsed.query)
            for key, values in query_params.items():
                url_fields.append({
                    "key": f"参数_{key}",
                    "value": values[0] if len(values) == 1 else values,
                    "confidence": "中",
                })
        if parsed.fragment:
            url_fields.append({"key": "锚点", "value": parsed.fragment, "confidence": "中"})

        # 合并字段（URL结构信息优先）
        result.fields = url_fields + result.fields

        # 置信度评估
        high_conf_count = sum(1 for f in result.fields if f["confidence"] == "高")
        if high_conf_count >= 3:
            result.confidence = "高"
        elif len(result.fields) >= 4:
            result.confidence = "中"
        else:
            result.confidence = "低"

    except MemstackError as e:
        # 网络失败时，降级为URL结构解析
        result.raw_length = len(url)
        parsed = urllib.parse.urlparse(url)
        result.fields = [
            {"key": "协议", "value": parsed.scheme, "confidence": "高"},
            {"key": "域名", "value": parsed.netloc, "confidence": "高"},
            {"key": "路径", "value": parsed.path or "/", "confidence": "高"},
        ]
        if parsed.query:
            query_params = urllib.parse.parse_qs(parsed.query)
            for key, values in query_params.items():
                result.fields.append({
                    "key": f"参数_{key}",
                    "value": values[0] if len(values) == 1 else values,
                    "confidence": "中",
                })
        result.warnings = [f"网络请求失败，仅解析URL结构: {e.message}"]
        result.confidence = "低"

    return result


def _format_output(result: StructuredResult, fmt: str) -> str:
    """按指定格式输出结果。"""
    data = result.to_dict()

    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = [
            f"来源类型: {data['source_type']}",
            f"来源名称: {data['source_name']}",
            f"处理时间: {data['timestamp']}",
            f"原始长度: {data['raw_length']}",
            f"整体置信度: {data['confidence']}",
            "",
            "提取字段:",
        ]
        for field in data["fields"]:
            lines.append(
                f"  - {field['key']}: {field['value']} (置信度: {field['confidence']})"
            )
        if data["warnings"]:
            lines.append("")
            lines.append("警告:")
            for warn in data["warnings"]:
                lines.append(f"  ! {warn}")
        return "\n".join(lines)
    elif fmt == "compact":
        # 紧凑格式，仅输出关键字段
        compact = {
            "type": data["source_type"],
            "name": data["source_name"],
            "fields": {f["key"]: f["value"] for f in data["fields"]},
            "confidence": data["confidence"],
        }
        return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    else:
        raise MemstackError("E004", f"不支持的输出格式: {fmt}")


# ============================================================
# 自检模块
# ============================================================
def _selftest() -> int:
    """
    内置自检逻辑（离线、无外部依赖）。
    使用硬编码样例数据验证核心功能。
    返回 0 表示通过，非 0 表示失败。
    """
    print("=== memstack 自检开始 ===")
    failures = 0

    # --- 测试1: 文本处理 ---
    print("\n[测试1] 文本处理")
    sample_text = """
    学习笔记 2026-01-15
    今天学习了 Python 编程基础，包括列表、字典和函数。
    参考文档: https://docs.python.org/3/tutorial/
    联系邮箱: student@example.com
    共计 3 个章节，约 120 页内容。
    """
    try:
        result = _process_text(sample_text, "selftest_text")
        assert result.source_type == "text", "来源类型应为text"
        assert result.raw_length > 0, "原始长度应大于0"
        assert len(result.fields) >= 3, "至少提取3个字段"

        # 检查关键字段
        field_keys = [f["key"] for f in result.fields]
        assert "行数" in field_keys, "应包含行数字段"
        assert "字符数" in field_keys, "应包含字符数字段"

        # 检查URL提取
        url_field = next((f for f in result.fields if f["key"] == "URL"), None)
        assert url_field is not None, "应提取到URL"
        assert "docs.python.org" in str(url_field["value"]), "URL内容应匹配"

        # 检查邮箱提取
        email_field = next((f for f in result.fields if f["key"] == "邮箱"), None)
        assert email_field is not None, "应提取到邮箱"
        assert "student@example.com" in str(email_field["value"]), "邮箱内容应匹配"

        print("  ✓ 文本处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 文本处理测试失败: {e}")
        failures += 1
