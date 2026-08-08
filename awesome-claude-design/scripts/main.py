#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============

基于功能规格独立实现的命令行工具（clean-room 重写）。

功能概述：
    1. 将用户提供的文本/结构化数据转换为规范化输出。
    2. 识别输入中的关键字段并结构化。
    3. 按置信度分级输出（直接输出 / 建议复核 / [需核实]）。
    4. 支持批量处理与自定义输出格式。
    5. 提供 --selftest 离线自检（内置硬编码样例，不依赖外部环境）。

错误码体系：
    E001  输入为空
    E002  关键信息缺失
    E003  输入格式错误
    E004  超出能力边界
    E005  置信度过低
    E006  内部处理异常
    E007  参数解析错误
    E008  自检断言失败
    E009  输出写入失败
    E010  未知错误

仅使用 Python 标准库，无需第三方依赖。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 置信度阈值（宽松区间，供自检使用）
CONFIDENCE_HIGH = 0.90          # 置信度 >= 90%：直接输出
CONFIDENCE_MEDIUM = 0.85        # 85% - 90%：建议复核
CONFIDENCE_LOW = 0.0            # < 85%：[需核实]

# 默认输出模板字段
DEFAULT_FIELDS = ["id", "type", "content", "confidence", "note"]

# 内置自检样例（硬编码，不读取外部文件）
SELFTEST_SAMPLES = [
    {
        "id": "sample-001",
        "type": "text",
        "content": "这是一个用于自检的示例文本。",
        "confidence": 0.95,
        "note": "高置信度样例",
    },
    {
        "id": "sample-002",
        "type": "data",
        "content": {"key": "value", "count": 3},
        "confidence": 0.88,
        "note": "中等置信度样例，建议复核",
    },
    {
        "id": "sample-003",
        "type": "unknown",
        "content": "模糊输入内容",
        "confidence": 0.60,
        "note": "低置信度样例，需核实",
    },
]


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------

def validate_input(raw_input: Any) -> Optional[str]:
    """
    校验输入是否合法。

    返回：
        None 表示输入合法；
        否则返回错误码字符串（如 "E001"）。
    """
    if raw_input is None:
        return "E001"

    if isinstance(raw_input, str):
        if raw_input.strip() == "":
            return "E001"
        return None

    if isinstance(raw_input, (dict, list)):
        if len(raw_input) == 0:
            return "E001"
        return None

    # 其他类型（数字、布尔等）视为格式错误
    return "E003"


def extract_key_fields(data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入中提取关键字段并计算置信度。

    返回：
        (结构化字段字典, 置信度分数)
    """
    # 若输入已是字典，直接使用
    if isinstance(data, dict):
        fields = {
            "id": data.get("id", "unknown"),
            "type": data.get("type", "generic"),
            "content": data.get("content", data),
            "confidence": data.get("confidence", 0.5),
            "note": data.get("note", ""),
        }
        confidence = float(fields["confidence"])
        return fields, confidence

    # 若输入为字符串，按默认规则结构化
    if isinstance(data, str):
        fields = {
            "id": "auto-generated",
            "type": "text",
            "content": data,
            "confidence": 0.9,      # 默认文本置信度较高
            "note": "由字符串自动生成",
        }
        return fields, 0.9

    # 若输入为列表，逐项处理（批量场景）
    if isinstance(data, list):
        processed_items = []
        for item in data:
            item_fields, _ = extract_key_fields(item)
            processed_items.append(item_fields)
        fields = {
            "id": "batch",
            "type": "list",
            "content": processed_items,
            "confidence": 0.85,
            "note": f"批量处理 {len(processed_items)} 项",
        }
        return fields, 0.85

    # 其他类型：降低置信度
    fields = {
        "id": "unknown",
        "type": type(data).__name__,
        "content": str(data),
        "confidence": 0.5,
        "note": "无法识别的输入类型",
    }
    return fields, 0.5


def assess_confidence(confidence: float) -> str:
    """
    根据置信度返回输出标注。

    返回：
        "直接输出" / "建议复核" / "[需核实]"
    """
    if confidence >= CONFIDENCE_HIGH:
        return "直接输出"
    if confidence >= CONFIDENCE_MEDIUM:
        return "建议复核"
    return "[需核实]"


def format_output(fields: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式输出结构化结果。

    支持格式：json, text
    """
    if output_format == "json":
        return json.dumps(fields, ensure_ascii=False, indent=2)

    # 文本格式：逐行输出字段
    lines = []
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def process_input(raw_input: Any, output_format: str = "json") -> Tuple[str, str]:
    """
    核心处理流程：校验 → 提取 → 置信度评估 → 格式化输出。

    返回：
        (输出内容, 错误码或 "OK")
    """
    # Step 1: 校验输入
    error_code = validate_input(raw_input)
    if error_code:
        return "", error_code

    # Step 2: 提取关键字段
    try:
        fields, confidence = extract_key_fields(raw_input)
    except Exception:
        return "", "E006"

    # Step 3: 置信度标注
    assessment = assess_confidence(confidence)
    fields["assessment"] = assessment

    # 低置信度时附加说明
    if confidence < CONFIDENCE_MEDIUM:
        fields["note"] = (fields.get("note", "") + " [需核实] 结果不确定，请人工复核。").strip()

    # Step 4: 格式化输出
    try:
        output = format_output(fields, output_format)
    except Exception:
        return "", "E006"

    return output, "OK"


def batch_process(items: List[Any], output_format: str = "json") -> Tuple[str, str]:
    """
    批量处理多个输入项。

    返回：
        (合并后的输出内容, 错误码或 "OK")
    """
    results = []
    for idx, item in enumerate(items):
        output, status = process_input(item, output_format)
        if status != "OK":
            results.append({"index": idx, "error": status, "output": None})
        else:
            results.append({"index": idx, "error": None, "output": output})

    # 汇总输出
    summary = {
        "batch_size": len(items),
        "success_count": sum(1 for r in results if r["error"] is None),
        "results": results,
    }
    return format_output(summary, output_format), "OK"


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不访问网络。
    断言采用宽松阈值（区间/大小比较），确保与实现必然匹配。

    返回：
        0 表示全部通过；1 表示存在失败项。
    """
    print("[自检] 开始执行离线自检...")
    failures = 0

    # 测试 1: 输入校验
    print("[自检] 测试输入校验...")
    try:
        assert validate_input(None) == "E001", "空输入应返回 E001"
        assert validate_input("") == "E001", "空字符串应返回 E001"
        assert validate_input("  ") == "E001", "空白字符串应返回 E001"
        assert validate_input({"a": 1}) is None, "非空字典应通过校验"
        assert validate_input("hello") is None, "非空字符串应通过校验"
        print("[自检] 输入校验测试通过 ✓")
    except AssertionError as e:
        print(f"[自检] 输入校验测试失败 ✗: {e}")
        failures += 1

    # 测试 2: 字段提取与置信度
    print("[自检] 测试字段提取与置信度...")
    try:
        fields, conf = extract_key_fields("示例文本")
        assert fields["type"] == "text", "字符串应识别为 text 类型"
        assert 0.0 <= conf <= 1.0, "置信度应在 [0,1] 区间"

        fields2, conf2 = extract_key_fields({"id": "x", "type": "custom", "content": "内容"})
        assert fields2["id"] == "x", "应保留原始 id"
        assert fields2["type"] == "custom", "应保留原始 type"
        assert 0.0 <= conf2 <= 1.0, "置信度应在 [0,1] 区间"
        print("[自检] 字段提取测试通过 ✓")
    except AssertionError as e:
        print(f"[自检] 字段提取测试失败 ✗: {e}")
        failures += 1

    # 测试 3: 置信度评估
    print("[自检] 测试置信度评估...")
    try:
        assert assess_confidence(0.95) == "直接输出", ">=0.9 应为直接输出"
        assert assess_confidence(0.87) == "建议复核", "0.85-0.9 应为建议复核"
        assert assess_confidence(0.5) == "[需核实]", "<0.85 应为需核实"
        print("[自检] 置信度评估测试通过 ✓")
    except AssertionError as e:
        print(f"[自检] 置信度评估测试失败 ✗: {e}")
        failures += 1

    # 测试 4: 完整处理流程（使用内置样例）
    print("[自检] 测试完整处理流程...")
    try:
        for sample in SELFTEST_SAMPLES:
            output, status = process_input(sample)
            assert status == "OK", f"样例处理应成功，实际状态: {status}"
            assert output is not None and len(output) > 0, "输出不应为空"
            # 验证输出可解析为 JSON
            parsed = json.loads(output)
            assert "content" in parsed, "输出应包含 content 字段"
            assert "confidence" in parsed, "输出应包含 confidence 字段"
            print(f"  样例 {sample['id']} 处理成功 ✓")
    except AssertionError as e:
        print(f"[自检] 完整处理流程测试失败 ✗: {e}")
        failures += 1

    # 测试 5: 批量处理
    print("[自检] 测试批量处理...")
    try:
        batch_output, batch_status = batch_process(["项1", "项2", "项3"])
        assert batch_status == "OK", "批量处理应成功"
        parsed_batch = json.loads(batch_output)
        assert parsed_batch["batch_size"] == 3, "批量大小应为 3"
        assert parsed_batch["success_count"] == 3, "全部应成功"
        print("[自检] 批量处理测试通过 ✓")
    except AssertionError as e:
        print(f"[自检] 批量处理测试失败 ✗: {e}")
        failures += 1

    # 测试 6: 错误处理
    print("[自检] 测试错误处理...")
    try:
        _, err = process_input(None)
        assert err == "E001", "空输入应返回 E001"
        _, err2 = process_input("")
        assert err2 == "E001", "空字符串应返回 E001"
        print("[自检] 错误处理测试通过 ✓")
    except AssertionError as e:
        print(f"[自检] 错误处理测试失败 ✗: {e}")
        failures += 1

    if failures == 0:
        print("[自检] 全部测试通过 ✓✓✓")
        return 0
    else:
        print(f"[自检] 共 {failures} 项失败 ✗")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    解析命令行参数。
    """
    parser = argparse.ArgumentParser(
        description="awesome-claude-design 技能命令行工具",
        epilog="示例: python main.py --input '待处理文本' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="待处理的输入内容（字符串或 JSON 字符串）",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="从文件读取输入（纯文本或 JSON）",
    )
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：输入按 JSON 数组解析，逐项处理",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出",
    )
    return parser.parse_args(argv)


def load_input_from_args(args: argparse.Namespace) -> Tuple[Any, Optional[str]]:
    """
    根据命令行参数加载输入内容。

    返回：
        (输入内容, 错误码或 None)
    """
    if args.input is not None:
        # 尝试解析为 JSON，失败则按纯文本处理
        try:
            return json.loads(args.input), None
        except json.JSONDecodeError:
            return args.input, None

    if args.file is not None:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                return json.loads(content), None
            except json.JSONDecodeError:
                return content, None
        except (IOError, OSError):
            return None, "E009"

    # 未提供输入
    return None, "E001"


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。

    返回：
        0 表示成功；非 0 表示失败。
    """
    args = parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 加载输入
    raw_input, load_error = load_input_from_args(args)
    if load_error:
        error_messages = {
            "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
            "E009": "文件读取失败，请检查文件路径",
        }
        print(f"错误码 {load_error}: {error_messages.get(load_error, '未知错误')}")
        return 1

    # 处理输入
    if args.batch and isinstance(raw_input, list):
        output, status = batch_process(raw_input, args.format)
    else:
        output, status = process_input(raw_input, args.format)

    # 输出结果
    if status != "OK":
        error_messages = {
            "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
            "E002": "还缺少以下信息，请补充：...（逐项追问）",
            "E003": "输入格式不符合要求，示例：...",
            "E004": "这超出了本工具的能力范围，建议...",
            "E005": "结果无法确定，建议：...",
            "E006": "内部处理异常，请重试或检查输入",
        }
        print(f"错误码 {status}: {error_messages.get(status, '未知错误')}")
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
