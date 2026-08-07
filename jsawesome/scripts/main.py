#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jsawesome - Awesome JSON 技能实现脚本

功能概述：
    根据用户提供的数据/文件/URL，将其转换为结构化结果。
    支持批量处理、置信度标注、错误码体系（E001-E010）。

用法示例：
    python main.py --selftest          # 运行内置自检
    python main.py --input '{"a":1}'   # 处理输入数据
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 置信度阈值
CONF_HIGH = 0.90      # 高置信度阈值
CONF_MEDIUM = 0.85    # 中置信度阈值

# 错误码及对应标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：JSON 对象、JSON 数组、或文件路径",
    "E004": "这超出了本工具的能力范围，建议：仅处理结构化数据转换",
    "E005": "结果无法确定，建议：补充更多上下文信息后重试",
    "E006": "文件读取失败，请确认文件路径存在且具有读取权限",
    "E007": "JSON 解析失败，请确认输入是合法 JSON",
    "E008": "URL 处理失败，本工具不支持网络访问",
    "E009": "输出格式不支持，仅支持 json / text / compact",
    "E010": "内部处理异常，请检查输入数据或联系维护者",
}


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def make_error(code: str) -> Dict[str, Any]:
    """构造标准错误响应"""
    return {
        "status": "error",
        "error_code": code,
        "message": ERROR_MESSAGES.get(code, "未知错误"),
    }


def calc_confidence(data: Any) -> float:
    """
    计算置信度（0.0 ~ 1.0）。
    基于数据结构的完整性和可解析性进行估算。
    """
    if data is None:
        return 0.0
    if isinstance(data, (str, int, float, bool)):
        return 1.0
    if isinstance(data, dict):
        if not data:
            return 0.7
        # 基于字段数量和非空字段比例估算
        total = len(data)
        non_empty = sum(1 for v in data.values() if v is not None and v != "")
        return round(0.7 + 0.3 * (non_empty / total), 2)
    if isinstance(data, list):
        if not data:
            return 0.7
        return round(0.7 + 0.3 * min(1.0, len(data) / 10), 2)
    return 0.5


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    识别并提取输入中的关键字段，进行结构化整理。
    返回一个包含元信息和结构化数据的字典。
    """
    result: Dict[str, Any] = {
        "source_type": type(data).__name__,
        "structure": None,
        "field_count": 0,
        "items_count": 0,
    }

    if isinstance(data, dict):
        result["structure"] = "object"
        result["field_count"] = len(data)
        result["keys"] = list(data.keys())
        result["data"] = data
    elif isinstance(data, list):
        result["structure"] = "array"
        result["items_count"] = len(data)
        result["data"] = data
    else:
        result["structure"] = "scalar"
        result["data"] = data

    return result


def format_output(data: Any, fmt: str = "json") -> str:
    """
    按指定格式生成输出字符串。
    支持 json（默认，带缩进）、compact（紧凑）、text（纯文本）。
    """
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    elif fmt == "compact":
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    elif fmt == "text":
        # 纯文本格式：递归处理嵌套结构，输出关键字段内容
        return _format_text(data)
    else:
        raise ValueError(f"不支持的输出格式: {fmt}")


def _format_text(data: Any, indent: int = 0) -> str:
    """
    递归格式化数据为纯文本格式。
    对于字典，输出 "key: value" 格式；
    对于列表，输出 "- value" 格式；
    对于标量，直接输出值。
    """
    lines = []
    prefix = " " * indent
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key.startswith("_"):  # 跳过内部字段
                continue
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_format_text(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(_format_text(item, indent + 2))
            else:
                lines.append(f"{prefix}- {item}")
    else:
        lines.append(f"{prefix}{data}")
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心处理流程
# ---------------------------------------------------------------------------
def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    核心处理函数：解析输入、结构化、标注置信度、生成结果。

    参数：
        raw_input: 用户提供的原始输入（JSON 字符串或文件路径）
        output_format: 输出格式（json / compact / text）

    返回：
        标准结果字典，包含状态、结构化数据、置信度等。
    """
    # --- 输入校验 ---
    if raw_input is None or raw_input.strip() == "":
        return make_error("E001")

    # --- 尝试解析 JSON ---
    parsed_data = None
    try:
        parsed_data = json.loads(raw_input)
    except json.JSONDecodeError:
        # 如果不是合法 JSON，尝试作为文件路径处理
        file_content = None
        try:
            if os.path.isfile(raw_input):
                with open(raw_input, "r", encoding="utf-8") as f:
                    file_content = f.read()
            else:
                return make_error("E003")
        except OSError:
            return make_error("E006")

        # 解析文件内容
        try:
            parsed_data = json.loads(file_content)
        except json.JSONDecodeError:
            return make_error("E007")

    # --- 结构化处理 ---
    structured = extract_key_fields(parsed_data)

    # --- 置信度计算 ---
    confidence = calc_confidence(parsed_data)

    # --- 置信度标注 ---
    if confidence >= CONF_HIGH:
        confidence_label = "高"
        note = "直接输出"
    elif confidence >= CONF_MEDIUM:
        confidence_label = "中"
        note = "建议复核"
    else:
        confidence_label = "低"
        note = "[需核实] 请确认不确定项"

    # --- 组装结果 ---
    result: Dict[str, Any] = {
        "status": "success",
        "confidence": confidence,
        "confidence_label": confidence_label,
        "note": note,
        "structured": structured,
    }

    # --- 生成输出文本 ---
    try:
        result["output"] = format_output(result["structured"], output_format)
    except ValueError as e:
        # 输出格式不支持
        err = make_error("E009")
        err["detail"] = str(e)
        return err

    return result


def batch_process(inputs: List[str], output_format: str = "json") -> Dict[str, Any]:
    """
    批量处理多个输入，按同一规则逐项处理。

    参数：
        inputs: 输入字符串列表
        output_format: 输出格式

    返回：
        包含批量结果的字典。
    """
    if not inputs:
        return make_error("E001")

    results = []
    for idx, item in enumerate(inputs):
        single_result = process_input(item, output_format)
        single_result["index"] = idx + 1
        results.append(single_result)

    return {
        "status": "success",
        "batch_size": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置自检函数：使用硬编码样例数据离线验证核心逻辑。
    不依赖外部文件、当前工作目录、网络等。
    使用宽松阈值（大小比较/区间判断），确保断言稳健。
    """
    print("开始运行自检...")

    # --- 测试用例 1：合法 JSON 对象 ---
    test_input_1 = '{"name": "测试", "age": 30, "city": "北京"}'
    result_1 = process_input(test_input_1, "json")
    assert result_1["status"] == "success", "用例1：状态应为 success"
    assert result_1["confidence"] >= 0.8, "用例1：置信度应 >= 0.8"
    assert result_1["structured"]["structure"] == "object", "用例1：结构应为 object"
    assert result_1["structured"]["field_count"] >= 2, "用例1：字段数应 >= 2"
    print("用例1（JSON对象）通过 ✓")

    # --- 测试用例 2：JSON 数组 ---
    test_input_2 = '[{"id": 1}, {"id": 2}, {"id": 3}]'
    result_2 = process_input(test_input_2, "compact")
    assert result_2["status"] == "success", "用例2：状态应为 success"
    assert result_2["structured"]["structure"] == "array", "用例2：结构应为 array"
    assert result_2["structured"]["items_count"] >= 1, "用例2：数组长度应 >= 1"
    print("用例2（JSON数组）通过 ✓")

    # --- 测试用例 3：空输入 → E001 ---
    result_3 = process_input("")
    assert result_3["status"] == "error", "用例3：状态应为 error"
    assert result_3["error_code"] == "E001", "用例3：错误码应为 E001"
    print("用例3（空输入）通过 ✓")

    # --- 测试用例 4：非法 JSON → E003 或 E007 ---
    result_4 = process_input("这不是JSON内容")
    assert result_4["status"] == "error", "用例4：状态应为 error"
    assert result_4["error_code"] in ("E003", "E007"), "用例4：错误码应为 E003 或 E007"
    print("用例4（非法输入）通过 ✓")

    # --- 测试用例 5：标量输入 ---
    result_5 = process_input("42")
    assert result_5["status"] == "success", "用例5：状态应为 success"
    assert result_5["structured"]["structure"] == "scalar", "用例5：结构应为 scalar"
    print("用例5（标量输入）通过 ✓")

    # --- 测试用例 6：批量处理 ---
    batch_inputs = ['{"a": 1}', '[1, 2, 3]', '{"b": 2}']
    batch_result = batch_process(batch_inputs, "json")
    assert batch_result["status"] == "success", "用例6：批量状态应为 success"
    assert batch_result["batch_size"] == 3, "用例6：批量大小应为 3"
    assert len(batch_result["results"]) == 3, "用例6：结果数量应为 3"
    print("用例6（批量处理）通过 ✓")

    # --- 测试用例 7：输出格式 ---
    result_7 = process_input('{"x": 1, "y": 2}', "text")
    assert result_7["status"] == "success", "用例7：状态应为 success"
    assert "x: 1" in result_7["output"], "用例7：文本输出应包含字段内容"
    assert "y: 2" in result_7["output"], "用例7：文本输出应包含所有字段内容"
    print("用例7（文本输出格式）通过 ✓")

    # --- 测试用例 8：置信度标注 ---
    # 空对象置信度应低于非空对象
    empty_conf = calc_confidence({})
    non_empty_conf = calc_confidence({"a": 1, "b": 2, "c": 3})
    assert empty_conf < non_empty_conf, "用例8：空对象置信度应低于非空对象"
    print("用例8（置信度计算）通过 ✓")

    # --- 测试用例 9：错误码完整性 ---
    assert "E001" in ERROR_MESSAGES, "用例9：错误码 E001 应存在"
    assert "E010" in ERROR_MESSAGES, "用例9：错误码 E010 应存在"
    assert len(ERROR_MESSAGES) >= 5, "用例9：错误码数量应 >= 5"
    print("用例9（错误码体系）通过 ✓")

    # --- 测试用例 10：URL 输入拒绝 ---
    result_10 = process_input("https://example.com/data.json")
    assert result_10["status"] == "error", "用例10：URL 应被拒绝"
    assert result_10["error_code"] in ("E003", "E007", "E008"), "用例10：应返回相关错误码"
    print("用例10（URL 拒绝）通过 ✓")

    print("\n全部自检用例通过 ✓")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="jsawesome - Awesome JSON 技能实现",
        epilog="示例: python main.py --input '{\"key\": \"value\"}' --format json",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，不依赖外部环境",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON 字符串或文件路径）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "compact", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入用逗号分隔多个 JSON）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1

    # 正常处理模式
    if not args.input:
        print(ERROR_MESSAGES["E001"])
        return 1

    try:
        if args.batch:
            # 批量模式：按逗号分隔
            inputs = [item.strip() for item in args.input.split(",") if item.strip()]
            result = batch_process(inputs, args.format)
        else:
            # 单条处理
            result = process_input(args.input, args.format)

        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0

    except Exception as e:
        # 兜底异常捕获
        err = make_error("E010")
        err["detail"] = str(e)
        print(json.dumps(err, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
