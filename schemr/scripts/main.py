#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schemr - 未命名工具
一个将用户提供的数据/文件/URL 转换为结构化结果的 DSL 工具。
本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：需为文本、JSON 文件路径或 URL",
    "E004": "这超出了本工具的能力范围，建议：仅处理文本/文件/URL 的结构化转换",
    "E005": "结果无法确定，建议：检查输入内容或补充更多信息",
}

# 默认输出模板
DEFAULT_TEMPLATE = {
    "title": "结构化结果",
    "fields": [],
    "confidence": 0.0,
    "notes": [],
}


class SchemrError(Exception):
    """自定义异常，携带错误码和消息"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _validate_input(raw_input: str) -> str:
    """校验输入，返回解析后的内容"""
    if not raw_input or not raw_input.strip():
        raise SchemrError("E001")

    # 判断是否为 URL
    parsed = urllib.parse.urlparse(raw_input)
    if parsed.scheme in ("http", "https"):
        # 不访问网络，仅标记
        return raw_input

    # 判断是否为文件路径
    path = Path(raw_input)
    if path.exists() and path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise SchemrError("E003", f"文件读取失败: {exc}") from exc

    # 否则视为纯文本内容
    return raw_input


def _extract_key_fields(content: str) -> Tuple[List[Dict[str, Any]], float]:
    """
    从内容中提取关键字段并结构化。
    返回 (字段列表, 置信度)
    """
    content = content.strip()
    if not content:
        raise SchemrError("E001")

    # 尝试解析 JSON 输入
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            fields = [{"key": k, "value": v, "confidence": 0.95} for k, v in data.items()]
            return fields, 0.95
        elif isinstance(data, list):
            fields = [{"item": item, "confidence": 0.92} for item in data]
            return fields, 0.92
    except json.JSONDecodeError:
        pass

    # 尝试解析键值对格式（每行 "key: value"）
    lines = content.splitlines()
    fields = []
    valid_lines = 0
    total_lines = len(lines)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ":" in line or "：" in line:
            key, _, value = line.partition(":" if ":" in line else "：")
            fields.append({"key": key.strip(), "value": value.strip(), "confidence": 0.85})
            valid_lines += 1
        elif line:
            # 无分隔符的行，作为普通文本项
            fields.append({"text": line, "confidence": 0.70})
            valid_lines += 1

    if not fields:
        raise SchemrError("E003")

    # 计算置信度
    ratio = valid_lines / total_lines if total_lines > 0 else 0
    confidence = 0.85 if ratio >= 0.8 else (0.70 if ratio >= 0.5 else 0.50)

    return fields, confidence


def _format_output(fields: List[Dict[str, Any]], confidence: float, output_format: str) -> Dict[str, Any]:
    """按指定格式组织输出"""
    result = {
        "fields": fields,
        "confidence": confidence,
        "notes": [],
    }

    # 置信度标注
    if confidence >= 0.90:
        result["notes"].append("置信度 ≥90%：直接输出")
    elif confidence >= 0.85:
        result["notes"].append("建议复核")
        result["warning"] = "建议复核"
    else:
        result["notes"].append("[需核实] 以下字段可能不准确")
        result["warning"] = "[需核实]"

    # 自定义输出格式（简单支持 JSON 和 文本）
    if output_format == "json":
        return result
    elif output_format == "text":
        # 文本格式返回特殊标记，由调用方处理
        result["output_format"] = "text"
        return result
    else:
        # 默认 JSON
        return result


def process_input(
    raw_input: str,
    output_format: str = "json",
    completeness: str = "detailed",
) -> Dict[str, Any]:
    """
    核心处理流程
    """
    # Step 1: 校验输入
    content = _validate_input(raw_input)

    # Step 2: 提取关键信息
    fields, confidence = _extract_key_fields(content)

    # Step 3: 组织输出
    result = _format_output(fields, confidence, output_format)

    # 完整度处理
    if completeness == "quick":
        # 快速骨架：只保留字段名
        result["fields"] = [{"key": f.get("key", f.get("text", "")), "value": "..."} for f in fields]
        result["notes"].append("快速骨架模式")
    elif completeness == "detailed":
        result["notes"].append("详细成品模式")

    return result


def _run_selftest() -> bool:
    """离线自检核心逻辑"""
    test_cases = [
        # (输入, 期望字段数, 最低置信度)
        ('{"name": "test", "age": 25}', 2, 0.90),
        ("名称: 示例\n数量: 100\n备注: 测试数据", 3, 0.70),
        ("单行文本内容", 1, 0.50),
        ("", 0, 0.0),  # 应触发 E001
    ]

    for idx, (input_str, expected_fields, min_confidence) in enumerate(test_cases, 1):
        try:
            result = process_input(input_str)
            if input_str == "":
                print(f"用例 {idx}: 失败（应报错但未报错）")
                return False
            actual_fields = len(result["fields"])
            actual_confidence = result["confidence"]
            if actual_fields < expected_fields:
                print(f"用例 {idx}: 字段数不足，期望 ≥{expected_fields}，实际 {actual_fields}")
                return False
            if actual_confidence < min_confidence:
                print(f"用例 {idx}: 置信度过低，期望 ≥{min_confidence}，实际 {actual_confidence}")
                return False
            print(f"用例 {idx}: 通过")
        except SchemrError as exc:
            if input_str == "" and exc.code == "E001":
                print(f"用例 {idx}: 通过（正确触发 E001）")
            else:
                print(f"用例 {idx}: 失败 - {exc}")
                return False

    # 测试错误码
    try:
        process_input("")
        print("错误码测试: 失败（未触发异常）")
        return False
    except SchemrError as exc:
        if exc.code == "E001":
            print("错误码测试: 通过（E001）")
        else:
            print(f"错误码测试: 失败（错误码 {exc.code}）")
            return False

    print("\n全部自检用例通过 ✅")
    return True


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="schemr - 结构化数据转换工具",
        epilog="示例: python main.py '名称: 测试' --format json --completeness detailed",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="",
        help="输入内容：文本、文件路径或 URL",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--completeness",
        choices=["quick", "detailed"],
        default="detailed",
        help="完整度：快速骨架或详细成品（默认: detailed）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args()

    if args.selftest:
        success = _run_selftest()
        return 0 if success else 1

    try:
        result = process_input(args.input, args.format, args.completeness)
    except SchemrError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    # 输出结果
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 文本格式输出
        for field in result["fields"]:
            key = field.get("key", field.get("text", ""))
            value = field.get("value", field.get("item", ""))
            print(f"{key}: {value}")
        if result.get("warning"):
            print(f"\n⚠️ {result['warning']}")
        for note in result.get("notes", []):
            print(f"📝 {note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
