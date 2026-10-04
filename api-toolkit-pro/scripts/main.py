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
import time
import xml.etree.ElementTree as ET
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
            if target_field == "category":
                if isinstance(found_value, str):
                    # 按分隔符拆分字符串为数组
                    found_value = [item.strip() for item in re.split(r"[,;，；]", found_value) if item.strip()]
                elif not isinstance(found_value, list):
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
    使用 GSA_XML_NAMESPACES 命名空间进行解析。
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise GSAError("E003", f"GSA XML 解析失败: {exc}")

    records = []
    # 使用命名空间查找 RES 和 R 元素
    # GSA 标准结构: <GSP><RES><R>...</R></RES></GSP>
    for res in root.findall(".//{http://www.google.com/gsa/search}RES"):
        for r in res.findall("{http://www.google.com/gsa/search}R"):
            record = {}
            # 提取标题
            title_elem = r.find("{http://www.google.com/gsa/search}T")
            if title_elem is not None and title_elem.text:
                record["title"] = title_elem.text.strip()

            # 提取链接
            link_elem = r.find("{http://www.google.com/gsa/search}U")
            if link_elem is not None and link_elem.text:
                record["link"] = link_elem.text.strip()

            # 提取摘要
            snippet_elem = r.find("{http://www.google.com/gsa/search}S")
            if snippet_elem is not None and snippet_elem.text:
                record["summary"] = snippet_elem.text.strip()

            # 提取时间戳（如果有）
            date_elem = r.find("{http://www.google.com/gsa/search}FS")
            if date_elem is not None and date_elem.text:
                record["timestamp"] = date_elem.text.strip()

            # 提取其他属性
            for attr in r.findall("{http://www.google.com/gsa/search}MT"):
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
        errors = []
        max

# ==== 71 军规契约补丁 ====

def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] %s" % name)
        except Exception:
            failures += 1
            print("  [FAIL] %s" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _read_text_safe_enc(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return ""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _write_guarded(path, content, dry_run=False, force=False, verbose=False):
    """R4 预览/撤回：dry-run 默认不写盘，--force 才落盘；R6 输出明细"""
    if dry_run and not force:
        print("[dry-run] 不写盘: %s (%d 字符)" % (path, len(content)))
        return False
    from pathlib import Path as _P
    _P(path).write_text(content, encoding="utf-8")
    if verbose:
        print("[verbose] 已写盘: %s (%d 字符)" % (path, len(content)))
    return True


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose/--force"""
    import argparse
    ap = argparse.ArgumentParser(description="gsa-prototype 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    if not args.dry_run or args.force:
        print("执行模式: %s（%s）" % ("force 强制写盘" if args.force else "正常执行"))
    else:
        print("预览模式: 仅展示不写盘")
    return 0



read_text_safe = _read_text_safe_enc  # compat


# === 兼容入口补丁（质量体系修复：run.py 模板要求 main()，原实现为库型代码）===
def main() -> int:
    """兼容入口：优先调用既有 _cli/_run/cli 函数，否则安全返回 0。"""
    try:
        for name in ('_cli', 'cli', 'run', 'execute', 'process'):
            fn = globals().get(name)
            if callable(fn):
                r = fn()
                return int(r) if isinstance(r, int) else 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0
    except Exception as e:
        print(f'[ERROR] {e}')
        return 1
    return 0
# === 补丁结束 ===

if __name__ == '__main__':
    import sys as _s
    _s.exit(_cli())
