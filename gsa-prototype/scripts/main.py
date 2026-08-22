#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gsa-prototype: 搜索协议封装与跨域 JSON 转换工具

本脚本依据功能规格独立实现，仅使用 Python 标准库。
支持通过命令行将文本数据转换为统一的 JSON 结构化输出，
并附带离线自检模式（--selftest）。

错误码说明:
    E001: 参数解析错误
    E002: 输入文件无法读取
    E003: 输入数据为空或格式非法
    E004: 输出文件无法写入
    E005: 内部数据转换异常
    E006: 自检断言失败
    E007: 不支持的协议类型
    E008: 字段映射配置错误
    E009: 批量处理中断
    E010: 未知运行时错误
"""

import argparse
import json
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

# 默认输出 Schema 版本
SCHEMA_VERSION = "1.0.1"

# 支持的输入协议类型
SUPPORTED_PROTOCOLS = ["gsa", "json", "text"]

# 时间戳格式（ISO 8601 带时区）
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S+00:00"

# 跨域映射配置（字段名映射规则）
# 格式: {目标字段: [源字段候选列表]}
CROSS_DOMAIN_MAPPINGS = {
    "title": ["title", "标题", "name", "heading", "subject"],
    "link": ["link", "url", "href", "链接", "地址", "uri"],
    "summary": ["summary", "snippet", "description", "desc", "摘要", "描述", "content"],
    "timestamp": ["timestamp", "time", "date", "publish_time", "时间", "日期", "created_at"],
    "author": ["author", "creator", "作者", "创建者"],
    "category": ["category", "categories", "分类", "标签", "tags"],
    "score": ["score", "relevance", "相关度", "评分"],
}

# 字段类型映射（用于类型校验）
FIELD_TYPE_RULES = {
    "title": "string",
    "link": "string",
    "summary": "string",
    "timestamp": "string",
    "author": "string",
    "category": "array",
    "score": "number",
}

# GSA XML 命名空间
GSA_XML_NAMESPACES = {
    "gsa": "http://www.google.com/gsa/search",
    "rss": "http://purl.org/rss/1.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class GSAError(Exception):
    """自定义异常类，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _now_timestamp() -> str:
    """返回当前 UTC 时间戳字符串（ISO 8601 带时区）。"""
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数。"""
    try:
        result = float(value)
        # 限制在 0.0 ~ 1.0 之间
        return max(0.0, min(1.0, result))
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    """安全转换为字符串。"""
    if value is None:
        return default
    return str(value)


def _guess_field_type(value: Any) -> str:
    """根据值内容猜测字段类型。"""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, str):
        # 尝试识别时间戳
        if re.match(r"^\d{4}-\d{2}-\d{2}", value):
            return "datetime"
        # 尝试识别 URL
        if value.startswith(("http://", "https://")):
            return "url"
        return "string"
    return "unknown"


def _validate_field_type(field_name: str, value: Any) -> bool:
    """
    根据字段类型规则校验值是否符合预期类型。
    返回 True 表示校验通过，False 表示校验失败。
    """
    if field_name not in FIELD_TYPE_RULES:
        return True  # 未定义规则则通过

    expected_type = FIELD_TYPE_RULES[field_name]
    actual_type = _guess_field_type(value)

    # 类型兼容性检查
    if expected_type == "string":
        return actual_type in ("string", "datetime", "url")
    elif expected_type == "number":
        return actual_type == "number" or (isinstance(value, (int, float)) and not isinstance(value, bool))
    elif expected_type == "array":
        return actual_type == "array"
    return True


def _apply_cross_domain_mapping(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    应用跨域映射配置，将源字段映射到统一的目标字段。
    支持字段名映射、类型校验和默认值处理。
    """
    mapped = {}
    validation_errors = []

    for target_field, source_candidates in CROSS_DOMAIN_MAPPINGS.items():
        found_value = None
        source_field_used = None

        # 尝试从源字段候选列表中查找
        for source_field in source_candidates:
            if source_field in record and record[source_field] is not None:
                found_value = record[source_field]
                source_field_used = source_field
                break

        # 如果找到值，进行类型校验
        if found_value is not None:
            if not _validate_field_type(target_field, found_value):
                validation_errors.append(
                    f"字段 '{target_field}' 类型校验失败: 期望 {FIELD_TYPE_RULES[target_field]}, 实际 {_guess_field_type(found_value)}"
                )
                continue

            # 特殊处理：category 字段需要转换为数组
            if target_field == "category" and not isinstance(found_value, list):
                if isinstance(found_value, str):
                    found_value = [found_value]
                else:
                    found_value = [str(found_value)]

            # 特殊处理：score 字段需要转换为浮点数
            if target_field == "score":
                try:
                    found_value = float(found_value)
                except (TypeError, ValueError):
                    found_value = 0.0

            mapped[target_field] = found_value
        else:
            # 未找到值，使用默认值
            if target_field == "category":
                mapped[target_field] = []
            elif target_field == "score":
                mapped[target_field] = 0.0
            else:
                mapped[target_field] = ""

    # 如果存在校验错误，抛出异常
    if validation_errors:
        raise GSAError("E008", "; ".join(validation_errors))

    return mapped


def _extract_core_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    从原始记录中提取核心字段（title, link, summary, timestamp）。
    使用跨域映射配置进行字段映射。
    """
    # 应用跨域映射
    mapped = _apply_cross_domain_mapping(record)

    # 提取核心字段
    core = {
        "title": mapped.get("title", ""),
        "link": mapped.get("link", ""),
        "summary": mapped.get("summary", ""),
        "timestamp": mapped.get("timestamp", ""),
    }

    return core


def _build_confidence(record: Dict[str, Any], core: Dict[str, Any]) -> Dict[str, float]:
    """
    为每条记录构建置信度评分（0.0 ~ 1.0）。
    评分规则：字段存在且非空则加分，否则不加。
    """
    total_score = 0.0
    fields_count = 0

    # 核心字段权重
    weights = {
        "title": 0.4,
        "link": 0.3,
        "summary": 0.2,
        "timestamp": 0.1,
    }

    for field, weight in weights.items():
        fields_count += weight
        if core.get(field):
            total_score += weight

    # 额外字段加分（最多 0.1）
    extra_keys = [k for k in record.keys() if k not in core]
    if extra_keys:
        total_score += min(0.1, 0.05 * len(extra_keys))

    # 归一化到 0.0 ~ 1.0
    if fields_count > 0:
        base_score = total_score / fields_count
    else:
        base_score = 0.0

    # 附加原始字段数量影响
    record_count = len(record)
    if record_count > 0:
        base_score = min(1.0, base_score + 0.05 * min(record_count, 5))

    return {
        "overall": _safe_float(base_score),
        "title": _safe_float(1.0 if core.get("title") else 0.0),
        "link": _safe_float(1.0 if core.get("link") else 0.0),
        "summary": _safe_float(1.0 if core.get("summary") else 0.0),
        "timestamp": _safe_float(1.0 if core.get("timestamp") else 0.0),
    }


def _transform_record(record: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    将单条原始记录转换为统一 Schema 结构。
    """
    core = _extract_core_fields(record)
    confidence = _build_confidence(record, core)

    # 保留原始非核心字段
    extra_fields = {}
    for key, value in record.items():
        if key not in core:
            extra_fields[key] = value

    return {
        "id": index + 1,
        "schema_version": SCHEMA_VERSION,
        "source": "gsa-prototype",
        "extracted_at": _now_timestamp(),
        "data": {
            "title": core["title"],
            "link": core["link"],
            "summary": core["summary"],
            "timestamp": core["timestamp"],
            "extra": extra_fields,
        },
        "confidence": confidence,
        "field_types": {k: _guess_field_type(v) for k, v in core.items()},
    }


def _parse_gsa_xml(xml_text: str) -> List[Dict[str, Any]]:
    """
    解析 GSA XML 协议格式。
    支持标准 GSA XML 响应结构（<GSP> 根元素）。
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise GSAError("E003", f"GSA XML 解析失败: {exc}")

    records = []
    # 查找所有 RES 元素下的 R 元素（GSA 标准结构）
    for res in root.findall(".//RES"):
        for r in res.findall("R"):
            record = {}
            # 提取标题
            title_elem = r.find("T")
            if title_elem is not None and title_elem.text:
                record["title"] = title_elem.text.strip()

            # 提取链接
            link_elem = r.find("U")
            if link_elem is not None and link_elem.text:
                record["link"] = link_elem.text.strip()

            # 提取摘要
            snippet_elem = r.find("S")
            if snippet_elem is not None and snippet_elem.text:
                record["summary"] = snippet_elem.text.strip()

            # 提取时间戳（如果有）
            date_elem = r.find("FS")
            if date_elem is not None and date_elem.text:
                record["timestamp"] = date_elem.text.strip()

            # 提取其他属性
            for attr in r.findall("MT"):
                if attr.get("N") and attr.get("V"):
                    record[attr.get("N")] = attr.get("V")

            if record:
                records.append(record)

    return records


def _parse_gsa_json(json_text: str) -> List[Dict[str, Any]]:
    """
    解析 GSA JSON 协议格式。
    支持标准 GSA JSON 响应结构。
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise GSAError("E003", f"GSA JSON 解析失败: {exc}")

    records = []
    # 标准 GSA JSON 结构: {"results": [...]} 或直接数组
    if isinstance(data, dict):
        # 尝试多种可能的键名
        for key in ["results", "items", "data", "records"]:
            if key in data and isinstance(data[key], list):
                records = [item for item in data[key] if isinstance(item, dict)]
                break
        else:
            # 如果找不到标准键，尝试将整个对象作为单条记录
            if any(k in data for k in ["title", "link", "url", "summary"]):
                records = [data]
    elif isinstance(data, list):
        records = [item for item in data if isinstance(item, dict)]

    return records


def _parse_gsa_text(text: str) -> List[Dict[str, Any]]:
    """
    解析 GSA 协议文本格式。
    支持三种格式：
    1. GSA XML 格式（<GSP> 根元素）
    2. GSA JSON 格式
    3. 行分隔格式（title|link|summary|timestamp）
    """
    text = text.strip()
    if not text:
        return []

    # 尝试 XML 解析（GSA 标准 XML 响应）
    if text.lstrip().startswith("<"):
        try:
            records = _parse_gsa_xml(text)
            if records:
                return records
        except GSAError:
            pass  # 不是有效的 GSA XML，继续尝试其他格式

    # 尝试 JSON 解析（GSA JSON 响应）
    if text.lstrip().startswith(("{", "[")):
        try:
            records = _parse_gsa_json(text)
            if records:
                return records
        except GSAError:
            pass  # 不是有效的 GSA JSON，继续尝试其他格式

    # 尝试行分隔格式
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 用 | 分隔字段
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 1:
            record = {
                "title": parts[0] if len(parts) > 0 else "",
                "link": parts[1] if len(parts) > 1 else "",
                "summary": parts[2] if len(parts) > 2 else "",
                "timestamp": parts[3] if len(parts) > 3 else "",
            }
            records.append(record)

    return records


def _parse_json_input(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 格式输入。"""
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []
    except json.JSONDecodeError as exc:
        raise GSAError("E003", f"JSON 解析失败: {exc}")


def _parse_text_input(text: str) -> List[Dict[str, Any]]:
    """解析纯文本格式输入，每行作为一条记录。"""
    records = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            records.append({"text": line})
    return records


def _parse_input(text: str, protocol: str) -> List[Dict[str, Any]]:
    """根据协议类型解析输入数据。"""
    protocol = protocol.lower()
    if protocol not in SUPPORTED_PROTOCOLS:
        raise GSAError("E007", f"不支持的协议类型: {protocol}")

    if protocol == "gsa":
        return _parse_gsa_text(text)
    if protocol == "json":
        return _parse_json_input(text)
    if protocol == "text":
        return _parse_text_input(text)

    return []


@lru_cache(maxsize=128)
def _transform_record_cached(record_tuple: Tuple[Tuple[str, Any], ...], index: int) -> Dict[str, Any]:
    """
    带缓存的单条记录转换函数。
    使用元组作为缓存键，因为字典不可哈希。
    """
    record = dict(record_tuple)
    return _transform_record(record, index)


def _transform_data(records: List[Dict[str, Any]], use_parallel: bool = True) -> Dict[str, Any]:
    """
    将原始记录列表转换为统一结构化输出。
    支持并行处理和缓存优化。
    """
    if not records:
        return {
            "schema_version": SCHEMA_VERSION,
            "total": 0,
            "records": [],
            "generated_at": _now_timestamp(),
        }

    if use_parallel and len(records) > 1:
        # 并行处理批量记录
        transformed = []
        with ThreadPoolExecutor(max_workers=min(8, len(records))) as executor:
            # 将记录转换为可哈希的元组形式用于缓存
            record_tuples = [tuple(sorted(rec.items())) for rec in records]
            future_to_index = {
                executor.submit(_transform_record_cached, rec_tuple, idx): idx
                for idx, rec_tuple in enumerate(record_tuples)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    transformed.append((idx, result))
                except Exception as exc:
                    raise GSA
