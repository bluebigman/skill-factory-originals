#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schemr — 数据建模与结构转换工具（独立实现）

根据功能规格独立编写，不参考任何既有代码。
支持多源输入解析、关键信息识别、结构化输出生成、置信度标注。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：输入源为空或格式不正确",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "URL访问失败：网络请求错误或超时",
    "E004": "JSON解析失败：输入不是合法的JSON格式",
    "E005": "CSV解析失败：输入不是合法的CSV格式",
    "E006": "YAML解析失败：输入不是合法的YAML格式",
    "E007": "类型推断失败：无法识别字段类型",
    "E008": "Schema生成失败：内部处理异常",
    "E009": "输出写入失败：无法写入目标文件",
    "E010": "未知错误：未预期的异常",
}


class SchemrError(Exception):
    """schemr 自定义异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 编码探测与文件读取模块
# ============================================================

def detect_encoding(path: str) -> str:
    """
    探测文件编码，返回编码名称。
    依次尝试 utf-8, gbk, gb18030。
    不再使用 latin-1 作为兜底，避免编码探测不可靠。
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(path, encoding=enc, errors="strict") as f:
                f.read(1024)  # 读取前1KB测试
            return enc
        except (UnicodeDecodeError, OSError):
            continue
    # 如果所有编码都失败，尝试使用 chardet 或 charset-normalizer
    try:
        import chardet
        with open(path, "rb") as f:
            raw_data = f.read(4096)
        result = chardet.detect(raw_data)
        if result["encoding"] and result["confidence"] > 0.5:
            return result["encoding"]
    except ImportError:
        pass
    
    try:
        import charset_normalizer
        with open(path, "rb") as f:
            raw_data = f.read(4096)
        result = charset_normalizer.from_bytes(raw_data).best()
        if result and result.encoding:
            return result.encoding
    except ImportError:
        pass
    
    # 最后尝试 utf-8-sig（处理 BOM）
    try:
        with open(path, encoding="utf-8-sig", errors="strict") as f:
            f.read(1024)
        return "utf-8-sig"
    except (UnicodeDecodeError, OSError):
        pass
    
    # 默认返回 utf-8
    return "utf-8"


def _read_text_safe(path: str) -> str:
    """多编码安全读取，统一编码探测逻辑"""
    try:
        encoding = detect_encoding(path)
        with open(path, encoding=encoding, errors="strict") as f:
            return f.read()
    except FileNotFoundError:
        raise SchemrError("E002", f"文件不存在: {path}")
    except UnicodeDecodeError as exc:
        # 编码探测失败，尝试二进制读取降级
        try:
            with open(path, "rb") as f:
                return f.read().decode("utf-8", errors="replace")
        except OSError as exc2:
            raise SchemrError("E002", f"文件读取失败: {path} - {exc2}") from exc2
    except OSError as exc:
        raise SchemrError("E002", f"文件读取失败: {path} - {exc}") from exc


def _iter_lines(path: str, encoding: Optional[str] = None):
    """流式读取文件行，支持编码探测"""
    if encoding is None:
        encoding = detect_encoding(path)
    
    try:
        with open(path, encoding=encoding, errors="strict") as f:
            for line in f:
                yield line
    except FileNotFoundError:
        raise SchemrError("E002", f"文件不存在: {path}")
    except UnicodeDecodeError as exc:
        # 降级为二进制模式
        try:
            with open(path, "rb") as f:
                for line in f:
                    yield line.decode("utf-8", errors="replace")
        except OSError as exc2:
            raise SchemrError("E002", f"文件读取失败: {path} - {exc2}") from exc2
    except OSError as exc:
        raise SchemrError("E002", f"文件读取失败: {path} - {exc}") from exc


# ============================================================
# 类型推断模块
# ============================================================

def _merge_array_types(types: List[str]) -> str:
    """合并数组元素类型"""
    if not types:
        return "array"
    # 去重并统计
    type_counts = {}
    for t in types:
        type_counts[t] = type_counts.get(t, 0) + 1
    
    # 如果所有元素类型相同，返回该类型
    if len(type_counts) == 1:
        return list(type_counts.keys())[0]
    
    # 如果有 null 和其他类型，忽略 null
    if "null" in type_counts and len(type_counts) > 1:
        non_null_types = {k: v for k, v in type_counts.items() if k != "null"}
        if len(non_null_types) == 1:
            return list(non_null_types.keys())[0]
    
    # 混合类型，返回最频繁的类型
    return max(type_counts.items(), key=lambda x: x[1])[0]


def infer_type(value: Any) -> str:
    """
    推断单个值的类型。
    返回类型字符串：string / integer / number / boolean / null / array / object
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        # 尝试识别日期字符串（宽松判断：包含常见日期分隔符且长度合理）
        if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value):
            return "date"
        # 尝试识别时间字符串
        if re.search(r"\d{1,2}:\d{2}(:\d{2})?", value):
            return "time"
        return "string"
    if isinstance(value, list):
        # 递归推断数组元素类型
        if len(value) == 0:
            return "array"
        element_types = [infer_type(item) for item in value]
        merged_type = _merge_array_types(element_types)
        return f"array<{merged_type}>" if merged_type != "array" else "array"
    if isinstance(value, dict):
        # 递归推断对象属性类型
        if len(value) == 0:
            return "object"
        field_types = {}
        for key, val in value.items():
            field_types[key] = infer_type(val)
        # 返回对象类型描述
        return f"object({','.join(f'{k}:{v}' for k, v in sorted(field_types.items()))})"
    return "string"


def infer_field_types(records: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    从一组记录中推断每个字段的类型。
    多个记录时取出现最多的类型作为最终类型。
    """
    field_types: Dict[str, Dict[str, int]] = {}

    for record in records:
        if not isinstance(record, dict):
            continue
        for key, value in record.items():
            if key not in field_types:
                field_types[key] = {}
            type_name = infer_type(value)
            field_types[key][type_name] = field_types[key].get(type_name, 0) + 1

    result: Dict[str, str] = {}
    for field, type_counts in field_types.items():
        if not type_counts:
            result[field] = "unknown"
            continue
        # 选择出现次数最多的类型
        best_type = max(type_counts.items(), key=lambda x: x[1])[0]
        result[field] = best_type

    return result


# ============================================================
# 置信度计算模块
# ============================================================

def compute_confidence(field: str, type_name: str, sample_count: int, total_count: int) -> float:
    """
    计算字段识别的置信度（0.0 ~ 1.0）。
    规则：
    - 字段名符合常见命名规范（小写、下划线、驼峰）时加分
    - 样本覆盖率高时加分
    - 类型为常见类型（string/integer/number/boolean）时加分
    - 类型为 unknown 时降低置信度
    """
    confidence = 0.5  # 基础置信度

    # 字段名规范加分
    if re.match(r"^[a-z][a-z0-9_]*$", field) or re.match(r"^[a-z][a-zA-Z0-9]*$", field):
        confidence += 0.2

    # 样本覆盖率加分
    coverage = sample_count / max(total_count, 1)
    confidence += coverage * 0.2

    # 常见类型加分
    if type_name in ("string", "integer", "number", "boolean"):
        confidence += 0.1

    # unknown 类型降低置信度
    if type_name == "unknown":
        confidence -= 0.3

    return min(max(confidence, 0.0), 1.0)


# ============================================================
# Schema 生成模块
# ============================================================

def build_schema(
    data: Union[Dict[str, Any], List[Any]],
    source_name: str = "input",
) -> Dict[str, Any]:
    """
    根据输入数据构建结构化 Schema 文档。
    支持 dict 或 list[dict] 形式的输入。
    """
    try:
        # 统一转换为记录列表
        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, list):
            records = [item for item in data if isinstance(item, dict)]
            if not records and data:
                # 非对象数组，生成通用数组 schema
                return {
                    "schema_version": "1.0",
                    "source": source_name,
                    "type": "array",
                    "items": {"type": infer_type(data[0])},
                    "confidence": 0.8,
                    "field_count": 1,
                }
        else:
            # 标量输入
            return {
                "schema_version": "1.0",
                "source": source_name,
                "type": infer_type(data),
                "confidence": 0.9,
                "field_count": 0,
            }

        if not records:
            return {
                "schema_version": "1.0",
                "source": source_name,
                "type": "object",
                "fields": [],
                "confidence": 0.5,
                "field_count": 0,
            }

        # 推断字段类型
        field_types = infer_field_types(records)

        # 构建字段列表
        fields = []
        total_records = len(records)

        for field_name in field_types:
            type_name = field_types[field_name]
            # 统计该字段在多少条记录中出现
            sample_count = sum(1 for r in records if isinstance(r, dict) and field_name in r)
            confidence = compute_confidence(field_name, type_name, sample_count, total_records)

            fields.append({
                "name": field_name,
                "type": type_name,
                "required": sample_count == total_records,
                "confidence": round(confidence, 2),
                "sample_count": sample_count,
            })

        # 计算整体置信度（所有字段置信度的平均值）
        overall_confidence = (
            sum(f["confidence"] for f in fields) / len(fields) if fields else 0.5
        )

        return {
            "schema_version": "1.0",
            "source": source_name,
            "type": "object",
            "fields": fields,
            "field_count": len(fields),
            "record_count": total_records,
            "confidence": round(overall_confidence, 2),
        }

    except SchemrError:
        raise
    except Exception as exc:
        raise SchemrError("E008", f"Schema生成失败: {exc}") from exc


# ============================================================
# 输入解析模块
# ============================================================

def parse_json_text(text: str) -> Any:
    """解析 JSON 文本"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemrError("E004", f"JSON解析失败: {exc}") from exc


def parse_csv_text(text: str) -> List[Dict[str, Any]]:
    """解析 CSV 文本为字典列表"""
    import csv
    import io

    try:
        reader = csv.DictReader(io.StringIO(text))
        records = []
        for row in reader:
            # 转换空字符串为 None
            cleaned = {}
            for key, value in row.items():
                if value == "":
                    cleaned[key] = None
                else:
                    # 尝试转换为数字
                    try:
                        cleaned[key] = int(value)
                    except (ValueError, TypeError):
                        try:
                            cleaned[key] = float(value)
                        except (ValueError, TypeError):
                            cleaned[key] = value
            records.append(cleaned)
        return records
    except Exception as exc:
        raise SchemrError("E005", f"CSV解析失败: {exc}") from exc


def parse_yaml_text(text: str) -> Any:
    """解析 YAML 文本（需要 PyYAML）"""
    try:
        import yaml  # pip install pyyaml
    except ImportError:
        raise SchemrError("E006", "YAML解析需要安装 PyYAML: pip install pyyaml")

    try:
        return yaml.safe_load(text)
    except Exception as exc:
        raise SchemrError("E006", f"YAML解析失败: {exc}") from exc


def load_from_file(file_path: str) -> Any:
    """从文件加载数据，根据扩展名自动选择解析器"""
    if not os.path.exists(file_path):
        raise SchemrError("E002", f"文件不存在: {file_path}")

    try:
        content = _read_text_safe(file_path)
    except SchemrError:
        raise
    except Exception as exc:
        raise SchemrError("E002", f"文件读取失败: {exc}") from exc

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".json",):
        return parse_json_text(content)
    elif ext in (".csv",):
        return parse_csv_text(content)
    elif ext in (".yaml", ".yml"):
        return parse_yaml_text(content)
    else:
        # 默认尝试 JSON
        return parse_json_text(content)


def fetch_url_with_retry(url: str, max_retries: int = 3, timeout: int = 10) -> str:
    """
    从 URL 获取内容，带重试退避和超时。
    使用 datetime.now(timezone.utc) 记录时间戳。
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "schemr/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 记录请求时间（UTC）
                request_time = datetime.now(timezone.utc).isoformat()
                content = response.read().decode("utf-8", errors="strict")
                # 可以在这里记录 request_time 到日志，但这里简化处理
                return content
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                # 指数退避：1s, 2s, 4s
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            continue
    
    raise SchemrError("E003", f"URL访问失败: {url} - {last_error}")


def fetch_urls_concurrently(urls: List[str], max_workers: int = 5) -> Dict[str, str]:
    """
    并发获取多个 URL 的内容。
    返回 {url: content} 字典，失败项不包含在结果中。
    """
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch_url_with_retry, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content = future.result()
                results[url] = content
            except SchemrError:
                # 单个 URL 失败不影响其他 URL
                continue
    return results


def parse_input_source(source: str) -> Any:
    """
    解析输入源。
    支持：
    - 直接 JSON 文本（以 { 或 [ 开头）
    - 文件路径（存在且可读）
    - URL（http/https 开头）
    - YAML 文本
    """
    source = source.strip()
    if not source:
        raise SchemrError("E001", "输入源为空")

    # 判断是否为文件路径
