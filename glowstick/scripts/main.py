#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glowstick — 实时 OpenGL 绘图数据预处理工具（Clean-Room 重写版）

本脚本仅依据功能规格独立实现，不包含任何既有代码。
功能：解析原始数据 / 文件 / URL 输入，提取绘图所需字段，
      生成结构化图表描述（JSON），并输出置信度标注。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "输入类型不支持：仅支持 raw / file / url",
    "E003": "文件不存在或不可读",
    "E004": "URL 访问失败或超时",
    "E005": "数据解析失败：无法识别数值序列",
    "E006": "输出格式不支持：仅支持 json / yaml",
    "E007": "内部逻辑错误：字段映射规则无效",
    "E008": "批量处理失败：某一条数据解析异常",
    "E009": "自检失败：核心逻辑与预期不符",
    "E010": "未知错误",
}


def _fail(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并以对应错误码退出。"""
    msg = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
    print(f"[glowstick] 错误 {code}: {msg}", file=sys.stderr)
    sys.exit(int(code[1:]) if code[1:].isdigit() else 1)


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------

def _is_numeric(value: str) -> bool:
    """判断字符串是否为可转换为 float 的数值。"""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _looks_like_timestamp(value: str) -> bool:
    """宽松判断字符串是否像时间戳（支持常见格式）。"""
    if not isinstance(value, str):
        return False
    # ISO 格式 / 纯数字时间戳 / 常见日期分隔符
    patterns = [
        r"^\d{4}-\d{2}-\d{2}",
        r"^\d{4}/\d{2}/\d{2}",
        r"^\d{10}(\.\d+)?$",
        r"^\d{13}$",
    ]
    return any(re.match(p, value) for p in patterns)


def _extract_numeric_series(data: Any) -> List[float]:
    """
    从任意输入中提取数值序列。
    支持：嵌套列表、数字字符串、混合类型。
    """
    numbers: List[float] = []

    def _walk(obj: Any) -> None:
        if obj is None:
            return
        if isinstance(obj, (int, float)):
            if not isinstance(obj, bool):  # bool 是 int 子类，排除
                numbers.append(float(obj))
        elif isinstance(obj, str):
            s = obj.strip()
            if _is_numeric(s):
                numbers.append(float(s))
            else:
                # 尝试从字符串中提取所有数字（如 "12,34,56"）
                for token in re.split(r"[\s,;|]+", s):
                    if _is_numeric(token):
                        numbers.append(float(token))
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                _walk(item)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                _walk(key)
                _walk(value)

    _walk(data)
    return numbers


def _parse_raw_data(raw_text: str) -> Tuple[List[float], List[str], float]:
    """
    解析原始文本数据。
    返回：(数值序列, 标签列表, 置信度 0~1)
    """
    if not raw_text or not raw_text.strip():
        return [], [], 0.0

    lines = raw_text.strip().splitlines()
    numbers: List[float] = []
    labels: List[str] = []
    uncertain = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 尝试按常见分隔符切分
        parts = re.split(r"[\s,;|]+", line)
        # 如果整行是单个数值
        if len(parts) == 1 and _is_numeric(parts[0]):
            numbers.append(float(parts[0]))
            labels.append("")
        else:
            # 混合行：可能包含标签 + 数值
            numeric_parts = [p for p in parts if _is_numeric(p)]
            non_numeric = [p for p in parts if not _is_numeric(p)]
            if numeric_parts:
                numbers.extend(float(p) for p in numeric_parts)
                labels.extend(non_numeric)
                uncertain += 1  # 混合行存在歧义
            else:
                # 纯文本行：可能是标签
                labels.append(line)

    # 计算置信度：无歧义时 1.0，有混合行时降低
    total_lines = max(len(lines), 1)
    confidence = 1.0 - (uncertain / total_lines * 0.5)
    return numbers, labels, max(0.0, min(1.0, confidence))


def _parse_csv_file(file_path: str) -> Tuple[List[float], List[str], float]:
    """解析 CSV 文件，提取数值列。"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        _fail("E003", f"无法读取文件: {file_path}")

    if not content.strip():
        return [], [], 0.0

    try:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
    except csv.Error:
        return _parse_raw_data(content)  # 回退到通用解析

    if not rows:
        return [], [], 0.0

    # 尝试识别表头（首行包含非数值文本）
    header = rows[0]
    has_header = any(not _is_numeric(cell) for cell in header)

    data_rows = rows[1:] if has_header else rows
    numbers: List[float] = []
    labels: List[str] = []
    uncertain = 0

    for row in data_rows:
        for cell in row:
            cell = cell.strip()
            if _is_numeric(cell):
                numbers.append(float(cell))
            elif cell:
                labels.append(cell)
                uncertain += 1

    if not numbers:
        return [], [], 0.0

    # 置信度：有表头且数据规整时较高
    confidence = 0.9 if has_header else 0.7
    if uncertain > 0:
        confidence -= 0.1
    return numbers, labels, max(0.0, min(1.0, confidence))


def _fetch_url(url: str) -> str:
    """从 URL 获取文本内容。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "glowstick/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except Exception:
        _fail("E004", f"URL 访问失败: {url}")
    return ""


def parse_input(input_type: str, input_data: Any) -> Dict[str, Any]:
    """
    统一入口：解析输入数据。
    返回结构化图表描述字典。
    """
    numbers: List[float] = []
    labels: List[str] = []
    confidence = 0.0
    source_desc = ""

    if input_type == "raw":
        numbers, labels, confidence = _parse_raw_data(str(input_data))
        source_desc = "raw"
    elif input_type == "file":
        path = str(input_data)
        if not os.path.isfile(path):
            _fail("E003", f"文件不存在: {path}")
        # 根据扩展名选择解析方式
        if path.lower().endswith(".csv"):
            numbers, labels, confidence = _parse_csv_file(path)
        else:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            numbers, labels, confidence = _parse_raw_data(text)
        source_desc = os.path.basename(path)
    elif input_type == "url":
        text = _fetch_url(str(input_data))
        numbers, labels, confidence = _parse_raw_data(text)
        source_desc = str(input_data)
    else:
        _fail("E002", f"不支持的输入类型: {input_type}")

    if not numbers:
        _fail("E005", "未能从输入中提取到有效的数值序列")

    # 构建结构化输出
    result = {
        "meta": {
            "generator": "glowstick",
            "version": "1.0.2",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        "source": {
            "type": input_type,
            "description": source_desc,
        },
        "data": {
            "values": numbers,
            "count": len(numbers),
            "min": min(numbers),
            "max": max(numbers),
            "mean": sum(numbers) / len(numbers),
        },
        "labels": labels,
        "confidence": confidence,
    }

    # 如果存在时间戳样式的标签，标注出来
    timestamp_labels = [l for l in labels if _looks_like_timestamp(l)]
    if timestamp_labels:
        result["data"]["timestamps"] = timestamp_labels

    return result


# ---------------------------------------------------------------------------
# 输出格式处理
# ---------------------------------------------------------------------------

def format_output(data: Dict[str, Any], output_format: str) -> str:
    """将结果格式化为 JSON 或 YAML 字符串。"""
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "yaml":
        # 简单 YAML 序列化（仅支持基础类型）
        lines: List[str] = []

        def _dump(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        _dump(v, prefix + "  ")
                    else:
                        lines.append(f"{prefix}{k}: {v}")
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        _dump(item, prefix + "  ")
                    else:
                        lines.append(f"{prefix}- {item}")

        _dump(data)
        return "\n".join(lines)
    else:
        _fail("E006", f"不支持的输出格式: {output_format}")
        return ""


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def batch_process(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理多个输入项。"""
    results = []
    for idx, item in enumerate(items):
        try:
            input_type = item.get("type", "raw")
            input_data = item.get("data", "")
            result = parse_input(input_type, input_data)
            results.append(result)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"[glowstick] 警告 E008: 第 {idx + 1} 项处理失败: {exc}", file=sys.stderr)
            results.append({
                "error": "E008",
                "index": idx,
                "message": str(exc),
            })
    return results


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def selftest() -> int:
    """
    内置自检逻辑：使用硬编码样例数据验证核心功能。
    不读取外部文件、不访问网络、不依赖工作目录。
    """
    print("[glowstick] 开始自检...")

    # --- 测试 1: 原始数据解析 ---
    raw_sample = "1,2,3,4,5"
    result1 = parse_input("raw", raw_sample)
    assert len(result1["data"]["values"]) == 5, "原始数据解析数量错误"
    assert result1["data"]["min"] <= 1.0 + 1e-6, "最小值偏大"
    assert result1["data"]["max"] >= 5.0 - 1e-6, "最大值偏小"
    assert result1["confidence"] > 0.5, "置信度异常偏低"
    print("  [PASS] 原始数据解析")

    # --- 测试 2: 混合标签与数值 ---
    mixed_sample = "cpu 45.2\nmem 78.9\ndisk 12.3"
    result2 = parse_input("raw", mixed_sample)
    assert len(result2["data"]["values"]) == 3, "混合数据数值提取失败"
    assert len(result2["labels"]) == 3, "标签提取失败"
    assert result2["data"]["max"] > 50.0, "最大值应大于50"
    print("  [PASS] 混合标签解析")

    # --- 测试 3: JSON 输出 ---
    json_out = format_output(result1, "json")
    parsed = json.loads(json_out)
    assert parsed["data"]["count"] == 5, "JSON 输出数据数量错误"
    print("  [PASS] JSON 输出")

    # --- 测试 4: 时间戳识别 ---
    ts_sample = "2024-01-01 10.5\n2024-01-02 20.3"
    result4 = parse_input("raw", ts_sample)
    assert len(result4["data"]["values"]) == 2, "时间戳数据解析失败"
    assert "timestamps" in result4["data"], "未识别时间戳"
    print("  [PASS] 时间戳识别")

    # --- 测试 5: 批量处理 ---
    batch_items = [
        {"type": "raw", "data": "1,2,3"},
        {"type": "raw", "data": "4,5,6,7"},
    ]
    batch_results = batch_process(batch_items)
    assert len(batch_results) == 2, "批量处理数量错误"
    assert batch_results[0]["data"]["count"] == 3, "第一批数据解析错误"
    assert batch_results[1]["data"]["count"] == 4, "第二批数据解析错误"
    print("  [PASS] 批量处理")

    # --- 测试 6: 数值统计 ---
    stat_sample = "10\n20\n30\n40"
    result6 = parse_input("raw", stat_sample)
    assert result6["data"]["mean"] > 20.0, "均值计算偏小"
    assert result6["data"]["mean"] < 30.0, "均值计算偏大"
    assert result6["data"]["min"] == 10.0, "最小值错误"
    assert result6["data"]["max"] == 40.0, "最大值错误"
    print("  [PASS] 数值统计")

    # --- 测试 7: 空数据错误处理 ---
    try:
        parse_input("raw", "")
        print("  [FAIL] 空数据未触发错误")
        return 1
    except SystemExit as e:
        # 验证退出码为 5（E005 对应的数字）
        expected_code = 5
        actual_code = e.code if isinstance(e.code, int) else 1
        if actual_code != expected_code:
            print(f"  [FAIL] 空数据错误码不正确: 期望 {expected_code}, 实际 {actual_code}")
            return 1
        print("  [PASS] 错误处理")

    print("[glowstick] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="glowstick — 实时 OpenGL 绘图数据预处理工具",
        epilog="示例: python main.py --type raw --data '1,2,3,4' --format json",
    )
    parser.add_argument(
        "--type",
        choices=["raw", "file", "url"],
        default="raw",
        help="输入类型: raw(默认) / file / url",
    )
    parser.add_argument(
        "--data",
        help="输入数据：原始文本 / 文件路径 / URL",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
        help="输出格式: json(默认) / yaml",
    )
    parser.add_argument(
        "--batch",
        help="批量处理的 JSON 文件路径（包含 items 列表）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 批量处理模式
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                batch_data = json.load(f)
            items = batch_data.get("items", [])
            if not items:
                _fail("E001", "批量处理需要 items 列表")
            results = batch_process(items)
            print(format_output({"results": results}, args.format))
            return 0
        except FileNotFoundError:
            _fail("E003", f"批量文件不存在: {args.batch}")
        except json.JSONDecodeError:
            _fail("E005", f"批量文件 JSON 解析失败: {args.batch}")

    # 单条处理模式
    if not args.data:
        _fail("E001", "缺少 --data 参数（或使用 --selftest 运行自检）")

    try:
        result = parse_input(args.type, args.data)
        output = format_output(result, args.format)
        print(output)
        return 0
    except SystemExit:
        raise
    except Exception as exc:
        _fail("E010", f"未知错误: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
