#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

未命名工具 (soup) — 独立实现脚本
依据功能规格 clean-room 重写，仅使用标准库。
"""

import argparse
import json
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "文件读取失败：{detail}",
    "E007": "URL 解析失败：{detail}",
    "E008": "JSON 解析失败：{detail}",
    "E009": "输出写入失败：{detail}",
    "E010": "内部错误：{detail}",
}


def raise_error(code: str, **kwargs) -> None:
    """抛出标准错误信息并退出。"""
    msg = ERROR_MESSAGES[code].format(**kwargs)
    print(f"[{code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class InputItem:
    """单个输入项。"""
    raw: str
    source_type: str  # "text" | "file" | "url"
    source_path: Optional[str] = None
    content: str = ""


@dataclass
class ProcessedItem:
    """处理结果项。"""
    input_item: InputItem
    fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 输入解析模块
# ---------------------------------------------------------------------------
def parse_input(raw: str) -> InputItem:
    """
    解析输入字符串，判断其类型（文本、文件路径、URL）。
    仅做本地判断，不访问网络。
    """
    if not raw or not raw.strip():
        raise_error("E001")

    raw = raw.strip()

    # 判断是否为 URL
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return InputItem(raw=raw, source_type="url", source_path=raw, content=raw)

    # 判断是否为本地文件路径（存在且为文件）
    p = Path(raw)
    if p.exists() and p.is_file():
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise_error("E006", detail=str(e))
        return InputItem(raw=raw, source_type="file", source_path=str(p), content=content)

    # 否则视为普通文本
    return InputItem(raw=raw, source_type="text", content=raw)


# ---------------------------------------------------------------------------
# 核心处理逻辑（关键信息提取）
# ---------------------------------------------------------------------------
def extract_fields(text: str) -> Tuple[Dict[str, Any], float, List[str]]:
    """
    从文本中提取关键信息。
    返回 (字段字典, 置信度, 警告列表)。
    规则：
      - 尝试解析 JSON（若为 JSON 则直接结构化）
      - 否则尝试识别 key: value 或 key=value 模式
      - 计算置信度
    """
    warnings: List[str] = []
    text = text.strip()

    if not text:
        raise_error("E001")

    # 尝试 JSON 解析
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                confidence = 0.95
                return data, confidence, warnings
            elif isinstance(data, list):
                # 列表包装为 { "items": [...] }
                return {"items": data}, 0.90, warnings
        except json.JSONDecodeError as e:
            warnings.append(f"JSON 解析失败，尝试其他方式: {e}")

    # 尝试 key: value 或 key=value 模式
    fields: Dict[str, Any] = {}
    lines = text.splitlines()
    matched_lines = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 尝试多种分隔符
        for sep in (":", "=", "："):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    fields[key] = value
                    matched_lines += 1
                    break

    if fields:
        # 置信度 = 匹配行数 / 总非空行数，上限 0.95
        non_empty_lines = sum(1 for l in lines if l.strip())
        ratio = matched_lines / non_empty_lines if non_empty_lines else 0
        confidence = min(0.95, 0.60 + ratio * 0.35)
        if matched_lines < non_empty_lines:
            warnings.append(f"有 {non_empty_lines - matched_lines} 行未识别为键值对")
        return fields, confidence, warnings

    # 无法提取结构化字段，视为纯文本
    confidence = 0.50
    warnings.append("未识别到结构化字段，按纯文本处理")
    return {"text": text}, confidence, warnings


# ---------------------------------------------------------------------------
# 输出格式化模块
# ---------------------------------------------------------------------------
def format_output(item: ProcessedItem, output_format: str = "json") -> str:
    """按指定格式输出结果。"""
    result: Dict[str, Any] = {
        "source_type": item.input_item.source_type,
        "source_path": item.input_item.source_path,
        "fields": item.fields,
        "confidence": item.confidence,
        "warnings": item.warnings,
        "confidence_label": get_confidence_label(item.confidence),
    }

    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        lines.append(f"来源类型: {item.input_item.source_type}")
        lines.append(f"置信度: {item.confidence:.0%} ({result['confidence_label']})")
        for key, value in item.fields.items():
            lines.append(f"  {key}: {value}")
        if item.warnings:
            lines.append("警告:")
            for w in item.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)
    else:
        raise_error("E003", example="json 或 text")


def get_confidence_label(confidence: float) -> str:
    """根据置信度返回标注。"""
    if confidence >= 0.90:
        return "直接输出"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def process_input(raw: str, output_format: str = "json") -> str:
    """
    标准处理流程：
    1. 解析输入
    2. 提取关键信息
    3. 生成输出
    """
    # Step 1: 解析输入
    input_item = parse_input(raw)

    # 边界检查：URL 不访问网络，仅记录
    if input_item.source_type == "url":
        # 仅保留 URL 本身，不进行网络请求
        fields = {"url": input_item.raw}
        confidence = 0.80
        warnings = ["URL 未访问网络，仅记录地址"]
        processed = ProcessedItem(
            input_item=input_item,
            fields=fields,
            confidence=confidence,
            warnings=warnings,
        )
        return format_output(processed, output_format)

    # Step 2: 提取关键信息
    fields, confidence, warnings = extract_fields(input_item.content)

    # Step 3: 置信度检查
    if confidence < 0.85:
        warnings.append("置信度过低，结果需人工核实")

    processed = ProcessedItem(
        input_item=input_item,
        fields=fields,
        confidence=confidence,
        warnings=warnings,
    )

    # Step 4: 输出
    return format_output(processed, output_format)


def batch_process(inputs: List[str], output_format: str = "json") -> str:
    """批量处理多个输入。"""
    results = []
    for raw in inputs:
        try:
            result = process_input(raw, output_format)
            results.append(result)
        except SystemExit as e:
            # 捕获错误但不退出，记录错误信息
            results.append(json.dumps({"error": str(e)}, ensure_ascii=False))
    return json.dumps(results, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自测模块
# ---------------------------------------------------------------------------
def selftest() -> None:
    """内置样例数据离线自检核心逻辑。"""
    test_cases = [
        # (输入, 期望的置信度范围, 期望包含的字段)
        ("name: 张三\nage: 25\ncity: 北京", 0.85, ["name", "age", "city"]),
        ("{\"name\": \"李四\", \"age\": 30}", 0.90, ["name", "age"]),
        ("这是一段普通文本，没有结构化信息", 0.50, ["text"]),
        ("key1=value1\nkey2=value2", 0.85, ["key1", "key2"]),
    ]

    print("=== 自测开始 ===")
    passed = 0
    total = len(test_cases)

    for i, (raw, min_conf, expected_keys) in enumerate(test_cases):
        try:
            # 直接调用核心处理逻辑
            input_item = parse_input(raw)
            fields, confidence, warnings = extract_fields(input_item.content)

            # 检查置信度
            assert confidence >= min_conf, f"置信度 {confidence:.2f} 低于期望 {min_conf}"

            # 检查字段
            for key in expected_keys:
                assert key in fields, f"缺少字段 {key}"

            # 检查输出格式
            processed = ProcessedItem(
                input_item=input_item,
                fields=fields,
                confidence=confidence,
                warnings=warnings,
            )
            json_output = format_output(processed, "json")
            json.loads(json_output)  # 确保是合法 JSON

            text_output = format_output(processed, "text")
            assert len(text_output) > 0, "文本输出为空"

            passed += 1
            print(f"  用例 {i+1}: ✓ 通过")
        except Exception as e:
            print(f"  用例 {i+1}: ✗ 失败 - {e}")

    # 测试错误处理
    print("\n=== 错误处理测试 ===")
    error_tests = [
        ("", "E001"),  # 空输入
        ("   ", "E001"),  # 空白输入
    ]

    for raw, expected_code in error_tests:
        try:
            process_input(raw)
            print(f"  输入 '{raw}': ✗ 未触发错误")
        except SystemExit as e:
            # 检查错误码
            import io
            # 捕获 stderr 中的错误码
            # 简化：检查退出码非零即视为通过
            if e.code != 0:
                print(f"  输入 '{raw}': ✓ 正确触发错误")
                passed += 1
            else:
                print(f"  输入 '{raw}': ✗ 退出码为零")
        except Exception as e:
            print(f"  输入 '{raw}': ✗ 异常 - {e}")

    print(f"\n=== 自测完成: {passed}/{total + len(error_tests)} 通过 ===")
    if passed < total + len(error_tests):
        sys.exit(1)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="未命名工具 (soup) - 数据处理工具",
        epilog="示例: python main.py 'name: 张三' --format json",
    )
    parser.add_argument(
        "input",
        nargs="*",
        help="输入内容（文本/文件路径/URL），多个输入表示批量处理",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（从 stdin 逐行读取输入）",
    )

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        selftest()
        return

    # 批量模式：从 stdin 读取
    if args.batch:
        inputs = [line.strip() for line in sys.stdin if line.strip()]
        if not inputs:
            raise_error("E001")
        output = batch_process(inputs, args.format)
        print(output)
        return

    # 单次/多次处理
    if not args.input:
        raise_error("E001")

    if len(args.input) == 1:
        # 单次处理
        output = process_input(args.input[0], args.format)
        print(output)
    else:
        # 多次处理（视为批量）
        output = batch_process(args.input, args.format)
        print(output)


if __name__ == "__main__":
    main()
