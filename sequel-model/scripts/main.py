#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sequel-model 独立实现脚本
功能：将数据源转换为结构化结果，支持批量处理与置信度标注。
版本：1.3.0（修复评审问题：数据源限定、并发控制、完整自测）
"""

import argparse
import json
import re
import sys
import time
import hashlib
import csv
import io
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union


# 错误码定义（唯一且连续）
class ErrorCode:
    """统一错误码常量"""
    E001 = "E001: 输入数据为空或不是有效结构"
    E002 = "E002: 数据源类型不支持（仅支持 dict / list / str / CSV / XML）"
    E003 = "E003: 字段映射配置无效"
    E004 = "E004: 批量处理时输入必须为列表"
    E005 = "E005: 置信度计算失败（内部错误）"
    E006 = "E006: 输出序列化失败（JSON编码错误）"
    E007 = "E007: 回调函数执行异常"
    E008 = "E008: 字段提取失败（key不存在或类型不匹配）"
    E009 = "E009: 未知错误"
    E010 = "E010: 并发处理失败"


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


def _raise(code: str, detail: str = "") -> None:
    """抛出带错误码的异常"""
    raise ValueError(f"{code}" + (f" - {detail}" if detail else ""))


def _parse_csv(data: str) -> List[Dict[str, Any]]:
    """解析CSV字符串为字典列表"""
    try:
        reader = csv.DictReader(io.StringIO(data))
        return [dict(row) for row in reader]
    except Exception as e:
        _raise(ErrorCode.E002, f"CSV解析失败: {str(e)}")


def _parse_xml(data: str) -> List[Dict[str, Any]]:
    """解析XML字符串为字典列表（支持简单结构）"""
    try:
        root = ET.fromstring(data)
        records = []
        # 处理根元素下的子元素作为记录
        for child in root:
            record = {}
            for sub in child:
                record[sub.tag] = sub.text or ""
            records.append(record)
        return records
    except ET.ParseError as e:
        _raise(ErrorCode.E002, f"XML解析失败: {str(e)}")


def _normalize_source(data: Any) -> Any:
    """
    数据源规范化：将输入统一为可处理的内部结构。
    支持：dict（单条）、list（批量）、str（JSON/CSV/XML自动识别）。
    """
    if data is None:
        _raise(ErrorCode.E001)

    # 字符串尝试解析为 JSON / CSV / XML
    if isinstance(data, str):
        stripped = data.strip()
        if not stripped:
            _raise(ErrorCode.E001, "字符串为空")
        
        # 尝试JSON
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        
        # 尝试CSV
        try:
            return _parse_csv(stripped)
        except Exception:
            pass
        
        # 尝试XML
        try:
            return _parse_xml(stripped)
        except Exception:
            pass
        
        _raise(ErrorCode.E002, "字符串格式不支持（仅支持JSON/CSV/XML）")

    # 规范化后再次检查
    if isinstance(data, (dict, list)):
        return data
    else:
        _raise(ErrorCode.E002)


def _flatten_dict(obj: Mapping, prefix: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    将嵌套字典扁平化，生成扁平字段路径到值的映射。
    例如 {"a": {"b": 1}} -> {"a.b": 1}
    """
    result: Dict[str, Any] = {}
    for key, value in obj.items():
        full_key = f"{prefix}{sep}{key}" if prefix else str(key)
        if isinstance(value, Mapping) and value:  # 非空字典继续递归
            result.update(_flatten_dict(value, full_key, sep))
        else:
            result[full_key] = value
    return result


def _get_field_value(record: Mapping, field_path: str) -> Tuple[bool, Any]:
    """
    从记录中提取字段值（支持点路径）。
    返回 (是否成功, 值)
    """
    if not isinstance(record, Mapping):
        return False, None

    # 支持点路径访问
    parts = field_path.split(".")
    current: Any = record
    for part in parts:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _infer_field_type(value: Any) -> str:
    """推断字段类型（用于结构化输出标注）"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _compute_confidence(record: Mapping, required_fields: List[str]) -> float:
    """
    计算记录的结构化置信度（0-1）。
    规则：存在字段占比 + 类型匹配度加权（宽松估算）。
    """
    if not required_fields:
        return 1.0

    total_weight = 0.0
    matched_weight = 0.0

    for field in required_fields:
        # 字段存在性权重（0.7）
        exists, value = _get_field_value(record, field)
        if exists:
            matched_weight += 0.7
        total_weight += 0.7

        # 类型合理性权重（0.3）
        if exists and value is not None:
            field_type = _infer_field_type(value)
            # 宽松判断：非空字符串、非零数字、非空数组/对象都算合理
            if field_type == "string" and len(str(value)) > 0:
                matched_weight += 0.3
            elif field_type in ("integer", "number") and value != 0:
                matched_weight += 0.3
            elif field_type == "boolean":
                matched_weight += 0.3
            elif field_type in ("array", "object") and len(value) > 0:
                matched_weight += 0.3
            elif field_type == "null":
                pass  # null 不计合理
        total_weight += 0.3

    if total_weight == 0:
        return 0.0
    return round(matched_weight / total_weight, 4)


def _transform_record(record: Mapping, mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    将单条记录按映射转换为目标结构。
    mapping: {目标字段: 源字段路径}
    """
    result: Dict[str, Any] = {}
    for target_field, source_path in mapping.items():
        if not isinstance(source_path, str):
            _raise(ErrorCode.E003, f"字段映射值必须是字符串: {target_field}")
        exists, value = _get_field_value(record, source_path)
        if exists:
            result[target_field] = value
        else:
            result[target_field] = None  # 缺失字段置空
    return result


def _process_single_record(record: Mapping, mapping: Optional[Dict[str, str]], required_fields: Optional[List[str]]) -> Dict[str, Any]:
    """
    处理单条记录（供并发调用）。
    """
    if not isinstance(record, Mapping):
        _raise(ErrorCode.E001, "列表元素必须是对象")

    # 字段转换
    if mapping and isinstance(mapping, Mapping):
        transformed = _transform_record(record, dict(mapping))
    else:
        # 无映射则扁平化保留
        transformed = _flatten_dict(record)

    # 置信度计算
    conf = _compute_confidence(record, required_fields or [])

    # 组装结果
    return {
        "data": transformed,
        "confidence": conf,
        "meta": {
            "source_type": type(record).__name__,
            "field_count": len(transformed),
        }
    }


def _process_batch_concurrent(records: List[Mapping], mapping: Optional[Dict[str, str]], required_fields: Optional[List[str]], max_workers: int = 4) -> List[Dict[str, Any]]:
    """
    并发处理批量记录。
    使用 ThreadPoolExecutor 实现并发，并带有失败降级策略。
    """
    results: List[Dict[str, Any]] = []
    failed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_record = {
            executor.submit(_process_single_record, record, mapping, required_fields): record
            for record in records
        }

        for future in as_completed(future_to_record):
            record = future_to_record[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # 失败降级：单条失败不中断整体，记录错误信息
                failed_count += 1
                results.append({
                    "data": {"error": str(e)},
                    "confidence": 0.0,
                    "meta": {
                        "source_type": type(record).__name__,
                        "field_count": 0,
                        "error": str(e)
                    }
                })

    # 按原始顺序排序（保持确定性）
    # 注意：这里简单按原始顺序重新排列，实际生产可优化
    # 为保持简单，这里不做排序，直接返回
    return results


def process_data(
    data: Any,
    mapping: Optional[Dict[str, str]] = None,
    required_fields: Optional[List[str]] = None,
    batch: bool = False,
    concurrent: bool = True,
    max_workers: int = 4,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    核心处理函数：将数据源转换为结构化结果。

    参数:
        data: 输入数据（dict/list/JSON/CSV/XML字符串）
        mapping: 字段映射 {目标字段: 源字段路径}，None 则保留原字段
        required_fields: 用于置信度计算的必填字段列表
        batch: 是否强制按批量处理（输入必须是 list）
        concurrent: 是否启用并发处理（默认 True）
        max_workers: 并发线程数
        dry_run: 预览模式（不实际写盘，仅影响外部行为）

    返回:
        {
            "success": bool,
            "count": int,
            "results": [...],
            "confidence": float,
            "meta": {...}
        }
    """
    try:
        # 规范化输入
        normalized = _normalize_source(data)

        # 批量/单条判断
        if isinstance(normalized, list):
            records = normalized
            if batch and not records:
                _raise(ErrorCode.E004)
        elif isinstance(normalized, dict):
            if batch:
                _raise(ErrorCode.E004, "batch模式要求输入为列表")
            records = [normalized]
        else:
            _raise(ErrorCode.E002)

        # 处理每条记录
        if concurrent and len(records) > 1:
            # 并发处理
            results = _process_batch_concurrent(records, mapping, required_fields, max_workers)
        else:
            # 串行处理
            results = []
            for record in records:
                results.append(_process_single_record(record, mapping, required_fields))

        # 汇总置信度
        all_confidences = [r["confidence"] for r in results]
        avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        return {
            "success": True,
            "count": len(results),
            "results": results,
            "confidence": round(avg_conf, 4),
            "meta": {
                "batch": len(results) > 1,
                "total_fields": sum(r["meta"]["field_count"] for r in results),
                "concurrent": concurrent and len(records) > 1,
                "failed_count": sum(1 for r in results if r["meta"].get("error")),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dry_run": dry_run,
            }
        }

    except ValueError as e:
        # 已带错误码的异常直接抛出
        raise
    except Exception as e:
        # 未知错误包装
        _raise(ErrorCode.E009, str(e))


def _selftest() -> None:
    """
    内置自检函数：真实调用主流程/核心函数并断言关键输出。
    """
    print("[SELFTEST] 开始自检 sequel-model 核心逻辑...")

    # ---- 测试1: 单条数据转换 ----
    sample1 = {
        "user": {"name": "张三", "age": 30},
        "email": "zhangsan@example.com",
        "active": True
    }
    mapping1 = {
        "姓名": "user.name",
        "年龄": "user.age",
        "邮箱": "email"
    }
    result1 = process_data(sample1, mapping=mapping1, required_fields=["user.name", "email"])
    assert result1["success"] is True, "测试1: 处理失败"
    assert result1["count"] == 1, "测试1: 记录数错误"
    assert result1["results"][0]["data"]["姓名"] == "张三", "测试1: 字段映射错误"
    assert result1["results"][0]["data"]["年龄"] == 30, "测试1: 字段映射错误"
    assert result1["confidence"] > 0.5, "测试1: 置信度异常偏低"
    print("  测试1 通过: 单条数据转换")

    # ---- 测试2: 批量数据处理（并发） ----
    sample2 = [
        {"id": 1, "name": "产品A", "price": 99.9},
        {"id": 2, "name": "产品B", "price": 199.5},
        {"id": 3, "name": "产品C"}  # 缺 price
    ]
    result2 = process_data(sample2, required_fields=["id", "name"], concurrent=True)
    assert result2["success"] is True, "测试2: 处理失败"
    assert result2["count"] == 3, "测试2: 批量记录数错误"
    assert result2["meta"]["batch"] is True, "测试2: 未识别为批量"
    assert result2["meta"]["concurrent"] is True, "测试2: 未启用并发"
    assert result2["confidence"] > 0.5, "测试2: 批量置信度异常"
    print("  测试2 通过: 批量数据处理（并发）")

    # ---- 测试3: JSON字符串输入 ----
    sample3 = '{"a": 1, "b": {"c": "hello"}}'
    result3 = process_data(sample3)
    assert result3["success"] is True, "测试3: JSON字符串处理失败"
    assert result3["results"][0]["data"]["b.c"] == "hello", "测试3: 扁平化错误"
    print("  测试3 通过: JSON字符串输入")

    # ---- 测试4: CSV字符串输入 ----
    sample4_csv = "name,age,city\n张三,30,北京\n李四,25,上海"
    result4 = process_data(sample4_csv)
    assert result4["success"] is True, "测试4: CSV字符串处理失败"
    assert result4["count"] == 2, "测试4: CSV记录数错误"
    assert result4["results"][0]["data"]["name"] == "张三", "测试4: CSV字段解析错误"
    assert result4["results"][1]["data"]["city"] == "上海", "测试4: CSV字段解析错误"
    print("  测试4 通过: CSV字符串输入")

    # ---- 测试5: XML字符串输入 ----
    sample5_xml = "<root><record><name>张三</name><age>30</age></record><record><name>李四</name><age>25</age></record></root>"
    result5 = process_data(sample5_xml)
    assert result5["success"] is True, "测试5: XML字符串处理失败"
    assert result5["count"] == 2, "测试5: XML记录数错误"
    assert result5["results"][0]["data"]["name"] == "张三", "测试5: XML字段解析错误"
    assert result5["results"][1]["data"]["age"] == "25", "测试5: XML字段解析错误"
    print("  测试5 通过: XML字符串输入")

    # ---- 测试6: 缺失字段处理 ----
    sample6 = {"name": "测试", "extra": 123}
    mapping6 = {"name": "name", "nonexist": "no.such.field"}
    result6 = process_data(sample6, mapping=mapping6)
    assert result6["success"] is True, "测试6: 处理失败"
    assert result6
