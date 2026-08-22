#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uploadcolumn — 字段解析与结构化输出技能
========================================
依据功能规格独立实现（clean-room），不参考任何既有代码。

能力：
  - 从 CSV / JSON / TXT 文本中提取字段
  - 从 URL 获取内容并解析（支持超时、重试退避）
  - 批量处理多行记录，输出统一结构化结果
  - 字段映射（源列名 -> 目标字段名）
  - 置信度标注（high / medium / low）
  - 缺失字段输出 `[需核实:字段名]` 占位
  - 并行处理独立记录，提升批量性能

命令行用法：
  python scripts/main.py --selftest          # 离线自检（无外部依赖）
  python scripts/main.py --help              # 查看帮助

错误码：
  E001 参数错误
  E002 输入格式不支持
  E003 文件读取失败
  E004 数据解析失败
  E005 字段映射失败
  E006 输出序列化失败
  E007 网络请求失败
  E008 数据量超限
  E009 内部逻辑错误
  E010 未知错误
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Callable


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB 限制
MAX_URL_SIZE = 5 * 1024 * 1024  # URL 下载内容 5MB 限制
URL_TIMEOUT = 10  # 秒
URL_MAX_RETRIES = 3
URL_RETRY_BACKOFF = 1.0  # 初始退避秒数

SUPPORTED_FORMATS = {"csv", "json", "txt"}

# 常见字段别名映射（源列名 -> 目标字段名）
FIELD_ALIASES = {
    "user_name": "username",
    "userName": "username",
    "name": "username",
    "email_addr": "email",
    "emailAddress": "email",
    "mail": "email",
    "phone_num": "phone",
    "phoneNumber": "phone",
    "mobile": "phone",
    "contact": "phone",
    "first_name": "firstname",
    "firstName": "firstname",
    "last_name": "lastname",
    "lastName": "lastname",
}

# 目标字段及对应验证规则（正则）
TARGET_FIELDS = {
    "username": r"^[A-Za-z0-9_.\-]{2,50}$",
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "phone": r"^\+?[0-9\-\(\)\s]{6,20}$",
    "firstname": r"^[A-Za-z\u4e00-\u9fff\-]{1,50}$",
    "lastname": r"^[A-Za-z\u4e00-\u9fff\-]{1,50}$",
    "age": r"^\d{1,3}$",
    "city": r"^[A-Za-z\u4e00-\u9fff\- ]{1,100}$",
    "address": r"^.{5,200}$",
    "note": r"^.{0,500}$",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class FieldValue:
    """单个字段的值及置信度。"""

    def __init__(self, value: Any, confidence: str = "high"):
        self.value = value
        self.confidence = confidence  # high / medium / low

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "confidence": self.confidence}


class ParsedRecord:
    """一条解析后的结构化记录。"""

    def __init__(self, record_id: str = ""):
        self.record_id = record_id
        self.fields: Dict[str, FieldValue] = {}
        self.source_line: int = 0
        self.raw_data: Any = None

    def add_field(self, name: str, value: Any, confidence: str = "high") -> None:
        self.fields[name] = FieldValue(value, confidence)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "record_id": self.record_id,
            "source_line": self.source_line,
        }
        for name, fv in self.fields.items():
            result[name] = fv.to_dict()
        return result

    def to_flat_dict(self) -> Dict[str, Any]:
        """扁平化输出：字段名 -> 值（带占位符）。"""
        result = {"record_id": self.record_id}
        for name, fv in self.fields.items():
            result[name] = fv.value if fv.value is not None else f"[需核实:{name}]"
        return result


class ParseResult:
    """批量解析的整体结果。"""

    def __init__(self):
        self.records: List[ParsedRecord] = []
        self.errors: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {
            "total_records": 0,
            "success_records": 0,
            "failed_records": 0,
            "missing_fields": 0,
        }

    def add_record(self, record: ParsedRecord) -> None:
        self.records.append(record)
        self.statistics["total_records"] += 1
        self.statistics["success_records"] += 1

    def add_error(self, message: str, code: str = "E004", line: int = 0) -> None:
        self.errors.append({"code": code, "message": message, "line": line})
        self.statistics["failed_records"] += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistics": self.statistics,
            "errors": self.errors,
            "records": [r.to_dict() for r in self.records],
        }

    def to_flat_list(self) -> List[Dict[str, Any]]:
        return [r.to_flat_dict() for r in self.records]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def normalize_column_name(name: str) -> str:
    """标准化列名：去除空白、转为小写、替换常见分隔符。"""
    if not name:
        return ""
    name = name.strip().lower()
    name = re.sub(r"[\s\-\.]+", "_", name)
    return name


def map_column_to_target(column_name: str) -> str:
    """将源列名映射到目标字段名。"""
    normalized = normalize_column_name(column_name)
    if normalized in FIELD_ALIASES:
        return FIELD_ALIASES[normalized]
    # 直接匹配目标字段
    if normalized in TARGET_FIELDS:
        return normalized
    # 尝试部分匹配
    for target in TARGET_FIELDS:
        if target in normalized or normalized in target:
            return target
    return normalized  # 未映射则保留原列名


def validate_field_value(field_name: str, value: Any) -> Tuple[bool, str]:
    """验证字段值是否符合目标字段规则。返回 (是否有效, 置信度)。"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return False, "low"

    pattern = TARGET_FIELDS.get(field_name)
    if not pattern:
        return True, "medium"  # 无规则字段默认 medium

    str_value = str(value).strip()
    if re.match(pattern, str_value):
        return True, "high"
    return False, "low"


def make_placeholder(field_name: str) -> str:
    """生成缺失字段占位符。"""
    return f"[需核实:{field_name}]"


# ---------------------------------------------------------------------------
# 解析器类
# ---------------------------------------------------------------------------
class CSVProcessor:
    """CSV 文本解析。"""

    def __init__(self, delimiter: str = ","):
        self.delimiter = delimiter

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """将 CSV 文本解析为字典列表。"""
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=self.delimiter)
            records = []
            for row in reader:
                records.append(dict(row))
            return records
        except Exception as exc:
            raise ValueError(f"CSV 解析失败: {exc}") from exc


class JSONProcessor:
    """JSON 文本解析。"""

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """将 JSON 文本解析为字典列表。"""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON 解析失败: {exc}") from exc

        if isinstance(data, dict):
            # 单条记录
            return [data]
        if isinstance(data, list):
            # 多条记录
            result = []
            for item in data:
                if isinstance(item, dict):
                    result.append(item)
                else:
                    raise ValueError(f"JSON 列表中存在非对象元素: {type(item)}")
            return result
        raise ValueError(f"不支持的 JSON 顶层类型: {type(data)}")


class TXTProcessor:
    """TXT 文本解析（按行，支持 key: value 格式）。"""

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """将 TXT 文本解析为字典列表。支持：
        1. 每行一个 key: value 对
        2. 空行分隔多条记录
        """
        records: List[Dict[str, Any]] = []
        current_record: Dict[str, Any] = {}

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                # 空行分隔记录
                if current_record:
                    records.append(current_record)
                    current_record = {}
                continue

            # 尝试解析 key: value
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if key:
                    current_record[key] = value
                    continue

            # 尝试解析 key = value
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip()
                if key:
                    current_record[key] = value
                    continue

            # 无法解析的行，作为 note 字段
            current_record.setdefault("note", "")
            current_record["note"] += stripped + " "

        if current_record:
            records.append(current_record)

        return records


def get_processor(format_type: str):
    """根据格式返回对应的处理器实例。"""
    format_type = format_type.lower().lstrip(".")
    if format_type == "csv":
        return CSVProcessor()
    if format_type == "json":
        return JSONProcessor()
    if format_type == "txt":
        return TXTProcessor()
    raise ValueError(f"不支持的输入格式: {format_type}")


# ---------------------------------------------------------------------------
# URL 下载函数（带重试退避和超时）
# ---------------------------------------------------------------------------
def fetch_url_content(url: str, timeout: int = URL_TIMEOUT, max_retries: int = URL_MAX_RETRIES) -> str:
    """
    从 URL 下载内容，带超时和重试退避机制。
    
    参数:
        url: 目标 URL
        timeout: 超时秒数
        max_retries: 最大重试次数
    
    返回:
        下载的文本内容
    
    异常:
        ValueError: 下载失败或内容超限
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "uploadcolumn/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read(MAX_URL_SIZE + 1)
                if len(content) > MAX_URL_SIZE:
                    raise ValueError(f"URL 内容超过 {MAX_URL_SIZE} 字节限制")
                return content.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP 错误 {exc.code}: {exc.reason}"
        except urllib.error.URLError as exc:
            last_error = f"URL 错误: {exc.reason}"
        except TimeoutError:
            last_error = f"请求超时（{timeout}秒）"
        except ValueError as exc:
            last_error = str(exc)
            break  # 内容超限不重试
        except Exception as exc:
            last_error = f"未知错误: {exc}"
        
        if attempt < max_retries - 1:
            backoff = URL_RETRY_BACKOFF * (2 ** attempt)
            print(f"  重试 {attempt + 1}/{max_retries}，等待 {backoff:.1f} 秒...", file=sys.stderr)
            time.sleep(backoff)
    
    raise ValueError(f"URL 下载失败: {last_error}")


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------
def detect_format(content: str) -> str:
    """自动检测内容格式。"""
    stripped = content.lstrip()
    if stripped.startswith("{"):
        return "json"
    if stripped.startswith("["):
        return "json"
    if content.splitlines() and "," in content.splitlines()[0]:
        return "csv"
    return "txt"


def parse_content(
    content: str,
    format_type: str = "auto",
    field_mapping: Optional[Dict[str, str]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    parallel: bool = True,
    max_workers: int = 4,
) -> ParseResult:
    """
    解析文本内容为结构化记录。

    参数:
        content: 输入文本
        format_type: 输入格式（auto/csv/json/txt）
        field_mapping: 自定义字段映射 {源列名: 目标字段名}
        progress_callback: 进度回调函数 (processed, total)
        parallel: 是否并行处理记录
        max_workers: 并行工作线程数

    返回:
        ParseResult 对象
    """
    result = ParseResult()

    # 检查输入大小
    if len(content.encode("utf-8")) > MAX_INPUT_SIZE:
        result.add_error("输入内容超过 10MB 限制", "E008")
        return result

    # 自动检测格式
    if format_type == "auto" or not format_type:
        format_type = detect_format(content)

    if format_type not in SUPPORTED_FORMATS:
        result.add_error(f"不支持的格式: {format_type}", "E002")
        return result

    # 获取处理器
    try:
        processor = get_processor(format_type)
    except ValueError as exc:
        result.add_error(str(exc), "E002")
        return result

    # 解析
    try:
        raw_records = processor.parse(content)
    except ValueError as exc:
        result.add_error(str(exc), "E004")
        return result

    if not raw_records:
        result.add_error("输入内容为空或无法解析出记录", "E004")
        return result

    # 逐条处理（串行或并行）
    total = len(raw_records)
    processed = 0

    if parallel and total > 1:
        # 并行处理
        with ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
            future_to_idx = {}
            for idx, raw_record in enumerate(raw_records):
                future = executor.submit(
                    process_single_record_wrapper,
                    idx,
                    raw_record,
                    field_mapping
                )
                future_to_idx[future] = idx

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    record = future.result()
                    if record is not None:
                        result.add_record(record)
                    else:
                        result.add_error(f"记录 {idx + 1} 处理失败", "E009", idx + 1)
                except Exception as exc:
                    result.add_error(f"记录 {idx + 1} 处理失败: {exc}", "E009", idx + 1)
                
                processed += 1
                if progress_callback:
                    progress_callback(processed, total)
    else:
        # 串行处理
        for idx, raw_record in enumerate(raw_records):
            try:
                record = ParsedRecord(record_id=f"rec_{idx + 1}")
                record.source_line = idx + 1
                record.raw_data = raw_record
                process_single_record(record, raw_record, field_mapping)
                result.add_record(record)
            except Exception as exc:
                result.add_error(f"记录 {idx + 1} 处理失败: {exc}", "E009", idx + 1)
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total)

    return result


def process_single_record_wrapper(idx: int, raw_record: Dict[str, Any], field_mapping: Optional[Dict[str, str]]) -> Optional[ParsedRecord]:
    """并行处理包装函数。"""
    try:
        record = ParsedRecord(record_id=f"rec_{idx + 1}")
        record.source_line = idx + 1
        record.raw_data = raw_record
        process_single_record(record, raw_record, field_mapping)
        return record
    except Exception:
        return None


def process_single_record(
    record: ParsedRecord,
    raw_record: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
) -> None:
    """处理单条记录，执行字段映射和验证。"""
    if not isinstance(raw_record, dict):
        raise ValueError(f"记录不是字典类型: {type(raw_record)}")

    # 构建映射表（默认使用内置别名映射）
    mapping: Dict[str, str] = {}
