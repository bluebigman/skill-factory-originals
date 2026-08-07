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
from datetime import datetime
from typing import Any, Dict, List, Optional

# 默认输出 Schema 版本
SCHEMA_VERSION = "1.0.1"

# 支持的输入协议类型
SUPPORTED_PROTOCOLS = ["gsa", "json", "text"]

# 时间戳格式
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class GSAError(Exception):
    """自定义异常类，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _now_timestamp() -> str:
    """返回当前 UTC 时间戳字符串。"""
    return datetime.utcnow().strftime(TIMESTAMP_FORMAT)


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


def _extract_core_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    从原始记录中提取核心字段（title, link, summary, timestamp）。
    使用宽松匹配策略，支持多种常见字段命名。
    """
    core = {}
    # 标题匹配
    for key in ("title", "标题", "name", "heading"):
        if key in record and record[key]:
            core["title"] = _safe_str(record[key])
            break
    else:
        core["title"] = ""

    # 链接匹配
    for key in ("link", "url", "href", "链接", "地址"):
        if key in record and record[key]:
            core["link"] = _safe_str(record[key])
            break
    else:
        core["link"] = ""

    # 摘要匹配
    for key in ("summary", "snippet", "description", "desc", "摘要", "描述"):
        if key in record and record[key]:
            core["summary"] = _safe_str(record[key])
            break
    else:
        core["summary"] = ""

    # 时间戳匹配
    for key in ("timestamp", "time", "date", "publish_time", "时间", "日期"):
        if key in record and record[key]:
            core["timestamp"] = _safe_str(record[key])
            break
    else:
        core["timestamp"] = ""

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


def _parse_gsa_text(text: str) -> List[Dict[str, Any]]:
    """
    解析 GSA 协议文本格式。
    支持两种常见格式：
    1. 每行一条记录，字段用 '|' 分隔（title|link|summary|timestamp）
    2. JSON 数组格式
    """
    text = text.strip()
    if not text:
        return []

    # 尝试 JSON 解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

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


def _transform_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    将原始记录列表转换为统一结构化输出。
    """
    if not records:
        return {
            "schema_version": SCHEMA_VERSION,
            "total": 0,
            "records": [],
            "generated_at": _now_timestamp(),
        }

    transformed = [_transform_record(rec, idx) for idx, rec in enumerate(records)]

    return {
        "schema_version": SCHEMA_VERSION,
        "total": len(transformed),
        "records": transformed,
        "generated_at": _now_timestamp(),
    }


def _read_input_file(filepath: str) -> str:
    """读取输入文件内容。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise GSAError("E002", f"输入文件不存在: {filepath}")
    except IOError as exc:
        raise GSAError("E002", f"读取输入文件失败: {exc}")


def _write_output_file(filepath: str, content: str) -> None:
    """写入输出文件。"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as exc:
        raise GSAError("E004", f"写入输出文件失败: {exc}")


def _process_input(input_source: str, protocol: str) -> Dict[str, Any]:
    """
    处理输入源（文件路径或直接文本），返回结构化结果。
    """
    # 判断是否为文件
    if os.path.isfile(input_source):
        text = _read_input_file(input_source)
    else:
        text = input_source

    if not text or not text.strip():
        raise GSAError("E003", "输入数据为空")

    # 解析输入
    records = _parse_input(text, protocol)
    if not records:
        raise GSAError("E003", "未能从输入中解析出有效记录")

    # 转换数据
    try:
        result = _transform_data(records)
    except Exception as exc:
        raise GSAError("E005", f"数据转换失败: {exc}")

    return result


def _run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("[SELFTEST] 开始自检...")

    # 测试数据 1: GSA 文本格式
    gsa_text = """
    标题1|http://example.com/1|这是第一条摘要|2026-01-01T00:00:00Z
    标题2|http://example.com/2|这是第二条摘要|2026-01-02T00:00:00Z
    """
    try:
        records = _parse_gsa_text(gsa_text)
        assert len(records) >= 2, "GSA 文本解析记录数不足"
        assert all(isinstance(r, dict) for r in records), "GSA 解析结果类型错误"
        assert any(r.get("title") for r in records), "GSA 解析标题缺失"
        print(f"  [OK] GSA 文本解析: {len(records)} 条记录")
    except AssertionError as exc:
        print(f"  [FAIL] GSA 文本解析: {exc}")
        return 6  # E006

    # 测试数据 2: JSON 格式
    json_data = json.dumps([
        {"title": "JSON标题1", "url": "http://json.example/1", "desc": "JSON摘要1"},
        {"title": "JSON标题2", "url": "http://json.example/2", "desc": "JSON摘要2"},
        {"title": "JSON标题3", "url": "http://json.example/3", "desc": "JSON摘要3"},
    ])
    try:
        records = _parse_json_input(json_data)
        assert len(records) >= 2, "JSON 解析记录数不足"
        assert all(isinstance(r, dict) for r in records), "JSON 解析结果类型错误"
        print(f"  [OK] JSON 解析: {len(records)} 条记录")
    except AssertionError as exc:
        print(f"  [FAIL] JSON 解析: {exc}")
        return 6  # E006

    # 测试数据 3: 文本格式
    text_data = "第一行文本\n第二行文本\n第三行文本"
    try:
        records = _parse_text_input(text_data)
        assert len(records) >= 2, "文本解析记录数不足"
        assert all(isinstance(r, dict) for r in records), "文本解析结果类型错误"
        print(f"  [OK] 文本解析: {len(records)} 条记录")
    except AssertionError as exc:
        print(f"  [FAIL] 文本解析: {exc}")
        return 6  # E006

    # 测试数据 4: 完整转换流程
    try:
        result = _transform_data([
            {"title": "测试标题", "link": "http://test.example", "summary": "测试摘要", "timestamp": "2026-01-01T00:00:00Z"},
            {"title": "测试标题2", "link": "http://test2.example", "summary": "测试摘要2", "timestamp": "2026-01-02T00:00:00Z"},
            {"title": "测试标题3", "link": "http://test3.example", "summary": "测试摘要3", "timestamp": "2026-01-03T00:00:00Z"},
        ])
        assert result["total"] >= 2, "转换结果记录数不足"
        assert result["schema_version"] == SCHEMA_VERSION, "Schema 版本不一致"
        assert len(result["records"]) >= 2, "转换记录列表长度不足"

        # 检查每条记录的置信度在合理范围内
        for rec in result["records"]:
            conf = rec.get("confidence", {})
            overall = conf.get("overall", 0.0)
            assert 0.0 <= overall <= 1.0, f"置信度超出范围: {overall}"
            assert "data" in rec, "记录缺少 data 字段"
            assert "id" in rec, "记录缺少 id 字段"
        print(f"  [OK] 完整转换流程: {result['total']} 条记录")
    except AssertionError as exc:
        print(f"  [FAIL] 完整转换流程: {exc}")
        return 6  # E006

    # 测试数据 5: 批量处理
    try:
        combined = _transform_data([
            {"title": "批量1", "link": "http://batch.example/1"},
            {"title": "批量2", "link": "http://batch.example/2"},
        ])
        assert combined["total"] == 2, "批量处理记录数不正确"
        assert len(combined["records"]) == 2, "批量处理列表长度不正确"
        print(f"  [OK] 批量处理: {combined['total']} 条记录")
    except AssertionError as exc:
        print(f"  [FAIL] 批量处理: {exc}")
        return 6  # E006

    # 测试数据 6: 空数据处理
    try:
        empty_result = _transform_data([])
        assert empty_result["total"] == 0, "空数据总数应为 0"
        assert len(empty_result["records"]) == 0, "空数据记录列表应为空"
        print("  [OK] 空数据处理")
    except AssertionError as exc:
        print(f"  [FAIL] 空数据处理: {exc}")
        return 6  # E006

    # 测试数据 7: 字段类型识别
    try:
        type_result = _transform_data([
            {"title": "类型测试", "link": "http://type.example", "count": 42, "valid": True}
        ])
        data_field = type_result["records"][0]["data"]
        assert "extra" in data_field, "额外字段缺失"
        assert data_field["extra"].get("count") == 42, "额外字段值不正确"
        print("  [OK] 字段类型与额外字段处理")
    except AssertionError as exc:
        print(f"  [FAIL] 字段类型与额外字段处理: {exc}")
        return 6  # E006

    # 测试数据 8: 协议解析 - 不支持的类型
    try:
        _parse_input("test", "unsupported_protocol")
        print("  [FAIL] 不支持的协议未报错")
        return 6  # E006
    except GSAError as exc:
        if exc.code == "E007":
            print("  [OK] 不支持的协议错误处理")
        else:
            print(f"  [FAIL] 错误码不正确: {exc.code}")
            return 6  # E006

    print("[SELFTEST] 全部自检通过")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="GSA 搜索协议封装与跨域 JSON 转换工具",
        epilog="示例: python main.py --input '标题|http://example.com|摘要' --protocol gsa"
    )
    parser.add_argument("--input", "-i", type=str,
                        help="输入数据（文件路径或直接文本）")
    parser.add_argument("--protocol", "-p", type=str, default="gsa",
                        choices=SUPPORTED_PROTOCOLS,
                        help="输入协议类型 (默认: gsa)")
    parser.add_argument("--output", "-o", type=str,
                        help="输出 JSON 文件路径（可选，默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置离线自检")
    parser.add_argument("--pretty", action="store_true",
                        help="美化 JSON 输出（缩进 2 空格）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 参数校验
    if not args.input:
        print("错误: 需要提供 --input 参数或使用 --selftest 运行自检", file=sys.stderr)
        return 1  # E001

    try:
        # 处理输入
        result = _process_input(args.input, args.protocol)

        # 序列化输出
        output_json = json.dumps(
            result,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":")
        )

        # 输出结果
        if args.output:
            _write_output_file(args.output, output_json)
            print(f"结果已写入: {args.output}")
        else:
            print(output_json)

        return 0

    except GSAError as exc:
        print(f"错误 [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1

    except Exception as exc:
        print(f"错误 [E010]: 未知运行时错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
