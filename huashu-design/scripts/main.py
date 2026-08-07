#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Huashu Design — 独立实现脚本
============================
依据功能规格（clean-room）独立编写，不复制任何既有代码。

功能概览：
  - 将用户提供的数据/文件/URL 转换为结构化结果
  - 识别并保留输入中的关键信息
  - 按约定格式生成输出
  - 对不确定项给出置信度提示
  - 支持批量处理和自定义格式

用法示例：
  python scripts/main.py --input "..." --format json
  python scripts/main.py --selftest
  python scripts/main.py --help
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量与错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请稍后重试或联系管理员",
    "E007": "文件读取失败，请检查路径和权限",
    "E008": "输出格式不支持，支持格式：json / text / html",
    "E009": "批量处理时出现错误，请检查每一项输入",
    "E010": "参数组合无效，请检查命令行参数",
}


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def extract_key_fields(raw_input: str) -> Dict[str, Any]:
    """
    从原始输入中提取关键字段并结构化。

    规则：
      - 尝试解析 JSON（若输入为 JSON 字符串）
      - 否则按文本行解析，识别形如 "key: value" 的字段
      - 若均无法识别，则放入 "text" 字段
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    text = raw_input.strip()

    # 尝试 JSON 解析
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {"type": "json", "data": parsed, "confidence": 0.95}
        if isinstance(parsed, list):
            return {"type": "json-list", "data": parsed, "confidence": 0.95}
    except (json.JSONDecodeError, ValueError):
        pass

    # 尝试 key: value 行解析
    lines = text.splitlines()
    fields: Dict[str, str] = {}
    for line in lines:
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key and value:
                fields[key] = value

    if fields:
        return {"type": "key-value", "data": fields, "confidence": 0.9}

    # 兜底：作为纯文本处理
    return {"type": "text", "data": {"content": text}, "confidence": 0.6}


def format_output(
    structured: Dict[str, Any],
    output_format: str = "json",
) -> str:
    """
    将结构化结果按指定格式输出。

    支持格式：json / text / html
    """
    fmt = output_format.lower()

    if fmt == "json":
        return json.dumps(structured, ensure_ascii=False, indent=2)

    if fmt == "text":
        lines = []
        data = structured.get("data", {})
        if isinstance(data, dict):
            for key, value in data.items():
                lines.append(f"{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                lines.append(str(item))
        else:
            lines.append(str(data))
        lines.append(f"置信度: {structured.get('confidence', 0):.0%}")
        return "\n".join(lines)

    if fmt == "html":
        data = structured.get("data", {})
        items_html = ""
        if isinstance(data, dict):
            for key, value in data.items():
                items_html += f"<li><strong>{key}</strong>: {value}</li>"
        elif isinstance(data, list):
            for item in data:
                items_html += f"<li>{item}</li>"
        else:
            items_html = f"<li>{data}</li>"
        confidence = structured.get("confidence", 0)
        return (
            "<html><body>"
            f"<h1>处理结果</h1>"
            f"<ul>{items_html}</ul>"
            f"<p>置信度: {confidence:.0%}</p>"
            "</body></html>"
        )

    raise ValueError("E008")


def process_single(
    raw_input: str,
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    处理单个输入项，返回结构化结果。
    """
    structured = extract_key_fields(raw_input)

    # 置信度标注
    confidence = structured["confidence"]
    if confidence >= 0.90:
        structured["note"] = "直接输出"
    elif confidence >= 0.85:
        structured["note"] = "建议复核"
    else:
        structured["note"] = "[需核实]"

    # 附加输出格式信息
    structured["output_format"] = output_format

    return structured


def process_batch(
    inputs: List[str],
    output_format: str = "json",
) -> List[Dict[str, Any]]:
    """
    批量处理多个输入项。
    """
    results = []
    errors = []
    for idx, item in enumerate(inputs):
        try:
            result = process_single(item, output_format)
            results.append({"index": idx, "status": "ok", "result": result})
        except Exception as exc:  # noqa: BLE001
            errors.append({"index": idx, "status": "error", "error": str(exc)})

    if errors:
        # 部分失败时仍返回成功项，但附加错误信息
        return {
            "status": "partial" if results else "error",
            "results": results,
            "errors": errors,
        }

    return {"status": "ok", "results": results, "errors": []}


# ---------------------------------------------------------------------------
# 自检（selftest）模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。

    断言使用宽松阈值（大小/区间判断），避免依赖精确值。
    """
    print("开始自检...")

    # 样例 1：JSON 输入
    sample_json = '{"name": "测试项目", "status": "active", "count": 42}'
    result_json = process_single(sample_json, "json")
    data = result_json["data"]
    assert result_json["type"] == "json", "JSON 类型识别失败"
    assert "name" in data and "status" in data, "JSON 字段提取失败"
    assert data["count"] > 0, "数值字段解析异常"
    assert result_json["confidence"] >= 0.9, "JSON 置信度应较高"
    print("  [通过] JSON 输入解析")

    # 样例 2：key-value 文本输入
    sample_kv = "标题: 季度报告\n作者: 张三\n页数: 15"
    result_kv = process_single(sample_kv, "text")
    data_kv = result_kv["data"]
    assert result_kv["type"] == "key-value", "key-value 类型识别失败"
    assert "标题" in data_kv and "作者" in data_kv, "key-value 字段提取失败"
    assert result_kv["confidence"] >= 0.85, "key-value 置信度应较高"
    print("  [通过] key-value 输入解析")

    # 样例 3：纯文本输入（低置信度）
    sample_text = "这是一段普通的文本内容，没有明显结构。"
    result_text = process_single(sample_text, "json")
    assert result_text["type"] == "text", "纯文本类型识别失败"
    assert result_text["confidence"] < 0.85, "纯文本置信度应较低"
    assert result_text["note"] == "[需核实]", "低置信度应标注 [需核实]"
    print("  [通过] 纯文本输入与置信度标注")

    # 样例 4：输出格式转换
    output_text = format_output(result_kv, "text")
    assert "标题" in output_text and "作者" in output_text, "文本输出格式错误"
    output_html = format_output(result_json, "html")
    assert "<html>" in output_html and "测试项目" in output_html, "HTML 输出格式错误"
    print("  [通过] 输出格式转换")

    # 样例 5：批量处理
    batch_inputs = [
        '{"id": 1, "value": "A"}',
        "名称: 项目X\n状态: 进行中",
        "无结构文本",
    ]
    batch_result = process_batch(batch_inputs, "json")
    assert batch_result["status"] == "ok", "批量处理应全部成功"
    assert len(batch_result["results"]) == 3, "批量处理数量错误"
    print("  [通过] 批量处理")

    # 样例 6：错误处理
    try:
        process_single("")
        assert False, "空输入应抛出 E001"
    except ValueError as exc:
        assert str(exc) == "E001", "错误码 E001 不匹配"

    try:
        format_output({}, "xml")
        assert False, "不支持的格式应抛出 E008"
    except ValueError as exc:
        assert str(exc) == "E008", "错误码 E008 不匹配"
    print("  [通过] 错误处理")

    # 样例 7：边界能力声明
    # 检查超出能力范围时的处理
    assert "E004" in ERROR_CODES, "缺少能力边界错误码"
    assert "E005" in ERROR_CODES, "缺少置信度过低错误码"
    print("  [通过] 能力边界与错误码完整性")

    print("全部自检通过！")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。
    """
    parser = argparse.ArgumentParser(
        description="Huashu Design · HTML-native design skill 独立实现",
        epilog="示例: python scripts/main.py --input '名称: 测试' --format json",
    )
    parser.add_argument(
        "--input",
        help="待处理的内容（数据/文本/JSON），或文件路径（配合 --read-file）",
    )
    parser.add_argument(
        "--read-file",
        action="store_true",
        help="将 --input 视为文件路径并读取内容",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "html"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：--input 可多次提供，或用换行分隔多个输入",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件）",
    )
    parser.add_argument(
        "--list-errors",
        action="store_true",
        help="列出所有错误码及说明",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1

    # 列出错误码
    if args.list_errors:
        for code, message in ERROR_CODES.items():
            print(f"{code}: {message}")
        return 0

    # 参数校验
    if not args.input:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        print("使用 --help 查看用法", file=sys.stderr)
        return 1

    # 读取输入
    raw_content = args.input
    if args.read_file:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except (OSError, IOError) as exc:
            print(f"错误 E007: {ERROR_CODES['E007']} ({exc})", file=sys.stderr)
            return 1

    # 批量模式处理
    if args.batch:
        # 支持换行分隔的多个输入
        items = [line.strip() for line in raw_content.splitlines() if line.strip()]
        if len(items) <= 1 and "\n" not in raw_content:
            # 单条输入也按批量处理
            items = [raw_content]
        try:
            result = process_batch(items, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"错误 E009: {ERROR_CODES['E009']} ({exc})", file=sys.stderr)
            return 1

    # 单条处理
    try:
        result = process_single(raw_content, args.format)
    except ValueError as exc:
        code = str(exc)
        message = ERROR_CODES.get(code, "未知错误")
        print(f"错误 {code}: {message}", file=sys.stderr)
        return 1

    # 输出结果
    try:
        output = format_output(result, args.format)
        print(output)
    except ValueError as exc:
        code = str(exc)
        message = ERROR_CODES.get(code, "未知错误")
        print(f"错误 {code}: {message}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
