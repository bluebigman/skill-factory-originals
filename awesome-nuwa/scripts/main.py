#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — awesome-nuwa 技能核心逻辑独立实现（clean-room）

本脚本依据功能规格独立编写，不复制任何既有实现。
提供命令行处理入口与离线自检（--selftest）能力。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码与标准化话术（依据规格定义）
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试或检查输入。",
    "E007": "不支持的输出格式，请选择：json / text。",
    "E008": "批量输入必须为列表。",
    "E009": "输入内容类型不受支持。",
    "E010": "自检过程出现异常，请检查代码。",
}


# ---------------------------------------------------------------------------
# 核心数据模型与常量
# ---------------------------------------------------------------------------
SUPPORTED_INPUT_TYPES = (str, dict, list)

# 置信度阈值（依据规格定义）
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ---------------------------------------------------------------------------
# 核心功能：内容解析与结构化
# ---------------------------------------------------------------------------
def parse_input(content: Any) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    解析用户输入，识别关键信息并结构化。

    参数:
        content: 用户提供的数据/文件路径/URL 字符串，或已解析的字典/列表。

    返回:
        (是否成功, 结构化结果或None, 错误码或None)
    """
    # E001: 输入为空
    if content is None or (isinstance(content, str) and not content.strip()):
        return False, None, "E001"

    # E009: 不支持的输入类型
    if not isinstance(content, SUPPORTED_INPUT_TYPES):
        return False, None, "E009"

    # 字符串：尝试按 JSON 解析，失败则作为纯文本处理
    if isinstance(content, str):
        text = content.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, (dict, list)):
                return _structure_parsed(parsed)
            # 简单字符串值，构建基础结构
            return _structure_text(text)
        except json.JSONDecodeError:
            return _structure_text(text)

    # 字典或列表：直接结构化
    return _structure_parsed(content)


def _structure_text(text: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """将纯文本转为结构化结果。"""
    if not text:
        return False, None, "E001"
    result = {
        "type": "text",
        "content": text,
        "key_fields": _extract_key_fields(text),
        "confidence": _estimate_confidence(text),
    }
    return True, result, None


def _structure_parsed(data: Any) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """将已解析的 JSON 数据转为结构化结果。"""
    if isinstance(data, dict):
        key_fields = {k: v for k, v in data.items() if _is_primitive(v)}
        result = {
            "type": "structured",
            "content": data,
            "key_fields": key_fields,
            "confidence": _estimate_confidence(data),
        }
        return True, result, None
    elif isinstance(data, list):
        # 批量输入处理
        if not data:
            return False, None, "E001"
        return True, {"type": "batch", "items": data, "count": len(data)}, None
    else:
        return False, None, "E009"


def _is_primitive(value: Any) -> bool:
    """判断是否为原始类型（可作为关键字段）。"""
    return isinstance(value, (str, int, float, bool)) or value is None


def _extract_key_fields(text: str) -> Dict[str, Any]:
    """从文本中提取可能的关键信息（简易启发式）。"""
    fields = {}
    # 尝试提取常见键值对模式：key: value 或 key=value
    lines = text.splitlines()
    for line in lines[:10]:  # 仅检查前10行，避免过度处理
        for sep in (":", "="):
            if sep in line:
                parts = line.split(sep, 1)
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value and len(key) < 30:
                    fields[key] = value
                break
    return fields


def _estimate_confidence(data: Any) -> float:
    """
    估算处理结果的置信度（0.0 - 1.0）。

    规则（依据规格）：
    - 结构化数据且字段完整：高置信度
    - 纯文本：中等置信度
    - 数据稀疏或模糊：低置信度
    """
    if isinstance(data, dict):
        if not data:
            return 0.5
        # 有明确键值对的，置信度较高
        primitive_count = sum(1 for v in data.values() if _is_primitive(v))
        ratio = primitive_count / max(len(data), 1)
        return min(0.95, 0.70 + ratio * 0.25)
    elif isinstance(data, str):
        # 文本长度作为置信度参考
        length = len(data.strip())
        if length < 10:
            return 0.6
        elif length < 100:
            return 0.8
        return 0.9
    elif isinstance(data, list):
        return 0.85 if data else 0.5
    return 0.5


# ---------------------------------------------------------------------------
# 核心功能：输出生成与置信度标注
# ---------------------------------------------------------------------------
def generate_output(structured: Dict[str, Any], output_format: str = "json") -> Tuple[bool, Any, Optional[str]]:
    """
    按约定格式生成输出，并标注置信度。

    参数:
        structured: parse_input 返回的结构化结果。
        output_format: "json" 或 "text"。

    返回:
        (是否成功, 输出内容, 错误码或None)
    """
    if not structured:
        return False, None, "E006"

    confidence = structured.get("confidence", 0.0)
    level = _confidence_level(confidence)

    # 组装输出结果
    output_payload = {
        "status": "success",
        "result": structured,
        "confidence": confidence,
        "confidence_level": level,
    }

    # 低置信度标注
    if confidence < MEDIUM_CONFIDENCE:
        output_payload["warning"] = "[需核实] 结果置信度较低，请人工复核关键内容。"

    if output_format == "json":
        return True, output_payload, None
    elif output_format == "text":
        return True, _format_as_text(output_payload), None
    else:
        return False, None, "E007"


def _confidence_level(confidence: float) -> str:
    """根据置信度返回级别描述。"""
    if confidence >= HIGH_CONFIDENCE:
        return "高置信度"
    elif confidence >= MEDIUM_CONFIDENCE:
        return "建议复核"
    else:
        return "需核实"


def _format_as_text(payload: Dict[str, Any]) -> str:
    """将输出负载格式化为可读文本。"""
    result = payload.get("result", {})
    lines = []
    lines.append("=== 处理结果 ===")
    lines.append(f"类型: {result.get('type', 'unknown')}")
    lines.append(f"置信度: {payload.get('confidence', 0):.1%} ({payload.get('confidence_level', '')})")

    key_fields = result.get("key_fields", {})
    if key_fields:
        lines.append("关键字段:")
        for k, v in key_fields.items():
            lines.append(f"  {k}: {v}")

    if payload.get("warning"):
        lines.append(f"⚠️ {payload['warning']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心功能：批量处理
# ---------------------------------------------------------------------------
def process_batch(items: List[Any], output_format: str = "json") -> Tuple[bool, Any, Optional[str]]:
    """
    批量处理多个输入项。

    参数:
        items: 待处理的输入列表。
        output_format: 输出格式。

    返回:
        (是否成功, 批量结果, 错误码或None)
    """
    if not isinstance(items, list):
        return False, None, "E008"

    results = []
    all_success = True

    for idx, item in enumerate(items):
        success, structured, err = parse_input(item)
        if not success:
            results.append({
                "index": idx,
                "status": "error",
                "error": err,
                "message": ERROR_MESSAGES.get(err, "未知错误"),
            })
            all_success = False
            continue

        ok, output, out_err = generate_output(structured, output_format)
        if not ok:
            results.append({
                "index": idx,
                "status": "error",
                "error": out_err,
                "message": ERROR_MESSAGES.get(out_err, "未知错误"),
            })
            all_success = False
            continue

        results.append({
            "index": idx,
            "status": "success",
            "output": output,
        })

    batch_result = {
        "type": "batch_result",
        "total": len(items),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "error_count": sum(1 for r in results if r["status"] == "error"),
        "items": results,
    }

    return all_success, batch_result, None


# ---------------------------------------------------------------------------
# 核心功能：标准流程编排
# ---------------------------------------------------------------------------
def process_input(content: Any, output_format: str = "json") -> Tuple[bool, Any, Optional[str]]:
    """
    标准处理流程入口（对应规格 Step 2: 执行核心流程）。

    参数:
        content: 用户输入。
        output_format: 输出格式（json/text）。

    返回:
        (是否成功, 输出内容, 错误码或None)
    """
    # Step 2.1: 解析输入
    success, structured, err = parse_input(content)
    if not success:
        return False, None, err

    # 批量类型走批量流程
    if structured.get("type") == "batch":
        return process_batch(structured.get("items", []), output_format)

    # Step 2.2: 生成输出
    return generate_output(structured, output_format)


# ---------------------------------------------------------------------------
# 命令行处理
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """
    命令行入口。

    参数:
        argv: 命令行参数列表（默认使用 sys.argv[1:]）。

    返回:
        退出码（0 成功，非 0 失败）。
    """
    parser = argparse.ArgumentParser(
        description="awesome-nuwa 技能核心逻辑 — 将输入内容结构化并输出",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的内容（JSON字符串或纯文本）。未提供时从 stdin 读取。",
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
        help="运行离线自检（使用内置硬编码样例数据，不依赖外部资源）",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 获取输入内容
    content = args.input
    if content is None:
        # 从 stdin 读取
        content = sys.stdin.read().strip()
        if not content:
            print(json.dumps({
                "status": "error",
                "error": "E001",
                "message": ERROR_MESSAGES["E001"],
            }, ensure_ascii=False))
            return 1

    # 尝试解析 JSON（如果看起来像 JSON）
    if content.strip().startswith(("{", "[")):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            pass  # 保持原样，按纯文本处理

    # 执行标准流程
    success, output, err = process_input(content, args.format)

    if not success:
        print(json.dumps({
            "status": "error",
            "error": err,
            "message": ERROR_MESSAGES.get(err, "未知错误"),
        }, ensure_ascii=False))
        return 1

    # 输出结果
    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    else:
        print(output)

    return 0


# ---------------------------------------------------------------------------
# 离线自检（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    运行内置硬编码样例数据的离线自检。

    自检内容覆盖规格中的核心能力：
    - 文本输入处理
    - JSON 输入处理
    - 批量输入处理
    - 置信度标注
    - 错误处理（E001 空输入）

    断言采用宽松阈值（大小比较/区间判断），确保稳健。

    返回:
        0 表示全部通过，非 0 表示存在失败。
    """
    print("=== awesome-nuwa 自检开始 ===")
    failures = 0

    # ---- 测试 1: 纯文本输入 ----
    print("\n[测试 1] 纯文本输入处理")
    try:
        success, result, err = process_input("姓名: 张三\n年龄: 30\n职业: 工程师", "json")
        assert success, f"文本处理应成功，但失败: {err}"
        assert result["status"] == "success", "状态应为 success"
        assert "result" in result, "结果应包含 result 字段"
        assert result["confidence"] > 0.5, "文本置信度应大于 0.5"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 测试 2: JSON 字典输入 ----
    print("\n[测试 2] JSON 字典输入")
    try:
        data = {"name": "李四", "age": 25, "city": "北京", "active": True}
        success, result, err = process_input(data, "json")
        assert success, f"JSON处理应成功，但失败: {err}"
        assert result["result"]["type"] == "structured", "类型应为 structured"
        assert "name" in result["result"]["key_fields"], "应提取 name 字段"
        assert result["confidence"] >= 0.7, "结构化数据置信度应较高"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 测试 3: 批量输入 ----
    print("\n[测试 3] 批量输入")
    try:
        items = ["简单文本", {"key": "value"}, "另一条记录"]
        success, result, err = process_input(items, "json")
        assert success, f"批量处理应成功，但失败: {err}"
        assert result["type"] == "batch_result", "应为批量结果类型"
        assert result["total"] == 3, "总数应为 3"
        assert result["success_count"] == 3, "全部应成功"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 测试 4: 置信度级别 ----
    print("\n[测试 4] 置信度级别")
    try:
        # 高置信度：完整结构化数据
        _, high_result, _ = process_input({"a": 1, "b": 2, "c": 3}, "json")
        high_conf = high_result["confidence"]
        assert high_conf >= 0.7, f"高置信度应 >= 0.7，实际: {high_conf}"

        # 低置信度：极短文本
        _, low_result, _ = process_input("x", "json")
        low_conf = low_result["confidence"]
        assert low_conf < 0.7, f"短文本置信度应 < 0.7，实际: {low_conf}"

        # 级别判断
        assert high_result["confidence_level"] in ("高置信度", "建议复核"), "置信度级别不合法"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 测试 5: 错误处理 E001（空输入） ----
    print("\n[测试 5] 空输入错误处理")
    try:
        success, _, err = process_input("", "json")
        assert not success, "空输入应失败"
        assert err == "E001", f"应为 E001，实际: {err}"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 测试 6: 错误处理 E007（不支持的输出格式） ----
    print("\n[测试 6] 不支持的输出格式")
    try:
        success, _, err = process_input("测试内容", "xml")
        assert not success, "不支持格式应失败"
        assert err == "E007", f"应为 E007，实际: {err}"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 测试 7: 文本输出格式 ----
    print("\n[测试 7] 文本输出格式")
    try:
        success, result, err = process_input("测试: 内容", "text")
        assert success, f"文本输出应成功，但失败: {err}"
        assert isinstance(result, str), "文本输出应为字符串"
        assert "处理结果" in result, "应包含结果标题"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 测试 8: 错误消息完整性 ----
    print("\n[测试 8] 错误消息完整性")
    try:
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
            assert ERROR_MESSAGES[code].strip(), f"错误码 {code} 消息为空"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1

    # ---- 汇总 ----
    print("\n" + "=" * 40)
    if failures == 0:
        print("✅ 全部自检通过！")
        return 0
    else:
        print(f"❌ {failures} 项自检失败！")
        return 1


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
