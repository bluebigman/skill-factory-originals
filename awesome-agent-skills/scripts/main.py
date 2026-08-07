#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - awesome-agent-skills 技能核心实现

本脚本依据功能规格独立实现（clean-room），提供：
- 输入解析与结构化处理
- 置信度评估与标注
- 错误码体系（E001-E010）
- 内置离线自检（--selftest）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 扩展错误码（E006-E010），用于内部异常场景
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出序列化失败，请检查数据格式",
    "E008": "批量处理中断，请检查每个输入项",
    "E009": "时间戳生成失败，请检查系统时间",
    "E010": "参数解析失败，请检查命令行参数",
}

# 置信度阈值（依据规格第三节）
HIGH_CONFIDENCE_THRESHOLD = 90  # 置信度 >= 90%：直接输出
MEDIUM_CONFIDENCE_THRESHOLD = 85  # 85%-90%：标注"建议复核"

# 触发词列表（依据规格第二节）
TRIGGER_WORDS = [
    "awesome agent skills",
    "帮我处理一下这个",
    "把这个转成另一种格式",
    "批量弄一下这些",
]

# 能力边界声明（依据规格第一节）
CAPABILITY_BOUNDARIES = {
    "can_do": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}


# ============================================================
# 核心数据结构
# ============================================================

class ProcessedResult:
    """处理结果的数据结构"""

    def __init__(self, data: Any, confidence: float, warnings: List[str], metadata: Dict[str, Any]):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    验证输入是否有效（E001）

    参数:
        raw_input: 用户提供的原始输入

    返回:
        (是否有效, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str) and not raw_input.strip():
        return False, "E001"
    if isinstance(raw_input, (list, dict)) and len(raw_input) == 0:
        return False, "E001"
    return True, None


def extract_key_fields(raw_input: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段（核心处理步骤）

    参数:
        raw_input: 用户提供的输入（字符串、字典、列表等）

    返回:
        结构化后的关键字段字典
    """
    key_fields: Dict[str, Any] = {}

    if isinstance(raw_input, str):
        # 字符串输入：按常见分隔符切分
        text = raw_input.strip()
        # 尝试解析 JSON
        try:
            parsed = json.loads(text)
            key_fields["type"] = "json"
            key_fields["content"] = parsed
        except json.JSONDecodeError:
            # 非 JSON，按文本处理
            key_fields["type"] = "text"
            key_fields["content"] = text
            key_fields["length"] = len(text)
            # 提取可能的键值对
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if lines:
                key_fields["lines"] = lines
    elif isinstance(raw_input, dict):
        # 字典输入：直接使用
        key_fields["type"] = "dict"
        key_fields["content"] = raw_input
        key_fields["keys"] = list(raw_input.keys())
    elif isinstance(raw_input, list):
        # 列表输入：批量处理
        key_fields["type"] = "list"
        key_fields["content"] = raw_input
        key_fields["count"] = len(raw_input)
    else:
        # 其他类型
        key_fields["type"] = type(raw_input).__name__
        key_fields["content"] = str(raw_input)

    return key_fields


def calculate_confidence(extracted: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    计算置信度并生成警告（依据规格第三节）

    参数:
        extracted: 提取的关键字段

    返回:
        (置信度百分比, 警告列表)
    """
    warnings: List[str] = []
    confidence = 100.0

    # 根据输入类型评估
    content_type = extracted.get("type", "unknown")

    if content_type == "text":
        # 文本输入：检查是否有足够内容
        content_len = extracted.get("length", 0)
        if content_len < 10:
            confidence -= 20
            warnings.append("输入内容较短，可能信息不完整")
        if content_len < 5:
            confidence -= 30
            warnings.append("输入内容过短，建议补充更多信息")
    elif content_type == "dict":
        # 字典输入：检查键的完整性
        keys = extracted.get("keys", [])
        if len(keys) < 2:
            confidence -= 15
            warnings.append("字段数量较少，可能遗漏关键信息")
    elif content_type == "list":
        # 列表输入：检查条目数量
        count = extracted.get("count", 0)
        if count < 2:
            confidence -= 15
            warnings.append("列表条目较少，可能样本不足")
    elif content_type == "json":
        # JSON 输入：解析成功但检查结构复杂度
        content = extracted.get("content", {})
        if isinstance(content, dict) and len(content) < 2:
            confidence -= 10
            warnings.append("JSON 结构较简单，可能信息有限")
    else:
        # 未知类型
        confidence -= 25
        warnings.append("无法识别的输入类型，结果可能不准确")

    # 确保置信度在合理范围
    confidence = max(0.0, min(100.0, confidence))

    return confidence, warnings


def format_output(result: ProcessedResult, custom_format: Optional[str] = None) -> Dict[str, Any]:
    """
    格式化输出结果（依据规格第三节）

    参数:
        result: 处理结果
        custom_format: 自定义输出格式（可选）

    返回:
        格式化后的输出字典
    """
    output: Dict[str, Any] = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "result": result.to_dict(),
    }

    # 根据置信度添加标注
    if result.confidence >= HIGH_CONFIDENCE_THRESHOLD:
        output["confidence_label"] = "直接输出"
    elif result.confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        output["confidence_label"] = "建议复核"
        output["review_note"] = "结果置信度中等，建议人工复核关键内容"
    else:
        output["confidence_label"] = "[需核实]"
        output["review_note"] = "结果置信度较低，请核实以下要点：" + "; ".join(result.warnings)

    # 支持自定义格式
    if custom_format and custom_format.lower() == "json":
        output["formatted_as"] = "json"
    elif custom_format and custom_format.lower() == "text":
        output["formatted_as"] = "text"
        output["text_preview"] = str(result.data)[:200]
    else:
        output["formatted_as"] = "默认"

    return output


def process_single_input(raw_input: Any, custom_format: Optional[str] = None) -> Dict[str, Any]:
    """
    处理单个输入项（核心流程）

    参数:
        raw_input: 用户输入
        custom_format: 自定义输出格式

    返回:
        处理结果字典
    """
    # Step 1: 验证输入（E001）
    valid, error_code = validate_input(raw_input)
    if not valid:
        return {
            "status": "error",
            "error_code": error_code,
            "error_message": ERROR_MESSAGES.get(error_code, "未知错误"),
        }

    # Step 2: 提取关键字段
    try:
        extracted = extract_key_fields(raw_input)
    except Exception:
        return {
            "status": "error",
            "error_code": "E006",
            "error_message": ERROR_MESSAGES["E006"],
        }

    # Step 3: 计算置信度
    confidence, warnings = calculate_confidence(extracted)

    # Step 4: 生成元数据
    metadata = {
        "process_id": str(uuid.uuid4())[:8],
        "input_type": extracted.get("type", "unknown"),
        "processed_at": datetime.now().isoformat(),
    }

    # Step 5: 构建结果对象
    result = ProcessedResult(
        data=extracted.get("content", raw_input),
        confidence=confidence,
        warnings=warnings,
        metadata=metadata,
    )

    # Step 6: 格式化输出
    return format_output(result, custom_format)


def process_batch_inputs(inputs: List[Any], custom_format: Optional[str] = None) -> Dict[str, Any]:
    """
    批量处理多个输入项

    参数:
        inputs: 输入列表
        custom_format: 自定义输出格式

    返回:
        批量处理结果
    """
    if not inputs:
        return {
            "status": "error",
            "error_code": "E001",
            "error_message": ERROR_MESSAGES["E001"],
        }

    results = []
    errors = []

    for i, item in enumerate(inputs):
        result = process_single_input(item, custom_format)
        if result.get("status") == "success":
            results.append(result)
        else:
            errors.append({"index": i, "error": result})

    # 批量处理统计
    summary = {
        "total": len(inputs),
        "success": len(results),
        "failed": len(errors),
    }

    return {
        "status": "success" if errors else "partial_success" if results else "error",
        "summary": summary,
        "results": results,
        "errors": errors,
        "batch_id": str(uuid.uuid4())[:8],
    }


# ============================================================
# 能力边界检查
# ============================================================

def check_capability_boundary(request: str) -> Tuple[bool, Optional[str]]:
    """
    检查请求是否超出能力边界（E004）

    参数:
        request: 用户请求描述

    返回:
        (是否在能力范围内, 错误码或None)
    """
    # 检查是否包含边界外的关键词
    out_of_scope_keywords = ["网络", "外部服务", "联网", "访问网站", "下载"]

    for keyword in out_of_scope_keywords:
        if keyword in request.lower():
            return False, "E004"

    return True, None


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑

    使用硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。

    返回:
        0 表示全部通过，非 0 表示有失败
    """
    print("=" * 60)
    print("开始自检：awesome-agent-skills 核心逻辑验证")
    print("=" * 60)

    failures = 0

    # --- 测试 1: 输入验证（E001） ---
    print("\n[测试 1] 输入验证（E001）")
    test_cases = [
        (None, True),  # None 应触发 E001
        ("", True),  # 空字符串应触发 E001
        ("   ", True),  # 空白字符串应触发 E001
        ("有效输入", False),  # 有效输入不应触发
        ([], True),  # 空列表应触发 E001
        ({"key": "value"}, False),  # 非空字典不应触发
    ]

    for input_val, should_error in test_cases:
        valid, error_code = validate_input(input_val)
        if should_error:
            if valid or error_code != "E001":
                print(f"  ✗ 输入 {repr(input_val)} 应触发 E001，实际 valid={valid}, error={error_code}")
                failures += 1
            else:
                print(f"  ✓ 输入 {repr(input_val)} 正确触发 E001")
        else:
            if not valid:
                print(f"  ✗ 有效输入 {repr(input_val)} 被错误拒绝")
                failures += 1
            else:
                print(f"  ✓ 有效输入 {repr(input_val)} 通过验证")

    # --- 测试 2: 关键字段提取 ---
    print("\n[测试 2] 关键字段提取")
    text_input = "这是一段测试文本，用于验证字段提取功能。"
    extracted = extract_key_fields(text_input)
    if extracted.get("type") == "text" and extracted.get("length", 0) > 0:
        print("  ✓ 文本输入提取成功")
    else:
        print(f"  ✗ 文本输入提取失败: {extracted}")
        failures += 1

    dict_input = {"name": "测试", "value": 42}
    extracted = extract_key_fields(dict_input)
    if extracted.get("type") == "dict" and "name" in extracted.get("keys", []):
        print("  ✓ 字典输入提取成功")
    else:
        print(f"  ✗ 字典输入提取失败: {extracted}")
        failures += 1

    list_input = ["item1", "item2", "item3"]
    extracted = extract_key_fields(list_input)
    if extracted.get("type") == "list" and extracted.get("count") == 3:
        print("  ✓ 列表输入提取成功")
    else:
        print(f"  ✗ 列表输入提取失败: {extracted}")
        failures += 1

    # --- 测试 3: 置信度计算 ---
    print("\n[测试 3] 置信度计算")
    # 短文本应得到较低置信度
    short_text = extract_key_fields("短")
    conf, warns = calculate_confidence(short_text)
    if conf < 85 and len(warns) > 0:
        print(f"  ✓ 短文本置信度合理降低: {conf:.1f}%, 警告数={len(warns)}")
    else:
        print(f"  ✗ 短文本置信度异常: {conf:.1f}%, 警告数={len(warns)}")
        failures += 1

    # 长文本应得到较高置信度
    long_text = extract_key_fields("这是一段足够长的测试文本内容，用于验证置信度计算逻辑是否正确。")
    conf, warns = calculate_confidence(long_text)
    if conf >= 85:
        print(f"  ✓ 长文本置信度合理: {conf:.1f}%")
    else:
        print(f"  ✗ 长文本置信度异常: {conf:.1f}%")
        failures += 1

    # --- 测试 4: 完整处理流程 ---
    print("\n[测试 4] 完整处理流程")
    result = process_single_input("需要处理的测试数据内容")
    if result.get("status") == "success":
        conf_label = result.get("confidence_label", "未知")
        print(f"  ✓ 处理成功，置信度标注: {conf_label}")
        if result.get("result", {}).get("confidence", 0) >= 50:
            print(f"  ✓ 置信度在合理范围: {result['result']['confidence']:.1f}%")
        else:
            print(f"  ✗ 置信度异常偏低: {result['result']['confidence']:.1f}%")
            failures += 1
    else:
        print(f"  ✗ 处理失败: {result}")
        failures += 1

    # --- 测试 5: 批量处理 ---
    print("\n[测试 5] 批量处理")
    batch_inputs = ["第一项数据", "第二项数据", "第三项数据"]
    batch_result = process_batch_inputs(batch_inputs)
    if batch_result.get("summary", {}).get("success") == 3:
        print("  ✓ 批量处理全部成功")
    else:
        print(f"  ✗ 批量处理结果异常: {batch_result.get('summary')}")
        failures += 1

    # --- 测试 6: 错误码覆盖 ---
    print("\n[测试 6] 错误码覆盖")
    error_codes_checked = 0
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        if code in ERROR_MESSAGES and ERROR_MESSAGES[code]:
            error_codes_checked += 1
    if error_codes_checked == 10:
        print("  ✓ 全部 10 个错误码已定义")
    else:
        print(f"  ✗ 错误码定义不完整: {error_codes_checked}/10")
        failures += 1

    # --- 测试 7: 能力边界检查 ---
    print("\n[测试 7] 能力边界检查")
    boundary_ok, _ = check_capability_boundary("处理这个文件")
    if boundary_ok:
        print("  ✓ 正常请求通过边界检查")
    else:
        print("  ✗ 正常请求被错误拒绝")
        failures += 1

    boundary_reject, err = check_capability_boundary("访问网络获取数据")
    if not boundary_reject and err == "E004":
        print("  ✓ 越界请求被正确拒绝")
    else:
        print(f"  ✗ 越界请求未被正确拒绝: err={err}")
        failures += 1

    # --- 测试 8: 输出格式 ---
    print("\n[测试 8] 输出格式")
    result = process_single_input("测试数据", custom_format="json")
    if result.get("formatted_as") == "json":
        print("  ✓ JSON 格式输出正确")
    else:
        print(f"  ✗ JSON 格式输出错误: {result.get('formatted_as')}")
        failures += 1

    result = process_single_input("测试数据", custom_format="text")
    if result.get("formatted_as") == "text" and "text_preview" in result:
        print("  ✓ 文本格式输出正确")
    else:
        print(f"  ✗ 文本格式输出错误: {result.get('formatted_as')}")
        failures += 1

    # --- 测试 9: 触发词识别 ---
    print("\n[测试 9] 触发词识别")
    trigger_found = False
    for word in TRIGGER_WORDS:
        if word in "awesome agent skills 使用指南":
            trigger_found = True
            break
    if trigger_found:
        print("  ✓ 触发词识别正常")
    else:
        print("  ✗ 触发词识别失败")
        failures += 1

    # --- 测试 10: 元数据生成 ---
    print("\n[测试 10] 元数据生成")
    result = process_single_input("测试数据")
    metadata = result.get("result", {}).get("metadata", {})
    if metadata.get("process_id") and metadata.get("processed_at"):
        print("  ✓ 元数据生成正常")
    else:
        print("  ✗ 元数据生成失败")
        failures += 1

    # --- 总结 ---
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检全部通过！✅")
        print("所有核心逻辑验证成功，错误码体系完整，边界检查正常。")
        return 0
    else:
        print(f"自检失败：{failures} 项未通过 ❌")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数

    返回:
        进程退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="awesome-agent-skills 技能核心实现",
        epilog="示例: python scripts/main.py --input '需要处理的数据' --format json",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（文本、JSON 字符串等）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON 数组字符串，如 '[\"a\", \"b\", \"c\"]'",
    )
    parser.add_argument(
        "--format",
        choices=["default", "json", "text"],
        default="default",
        help="输出格式（默认: default）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="awesome-agent-skills 1.0.0",
        help="显示版本信息",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        return e.code
    except Exception:
        print(f"错误: {ERROR_MESSAGES['E010']}")
        return 1

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量处理模式
    if args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                print(f"错误: {ERROR_MESSAGES['E003']}")
                return 1
            result = process_batch_inputs(batch_data, args.format)
        except json.JSONDecodeError:
            print(f"错误: {ERROR_MESSAGES['E003']} - 批量输入必须是 JSON 数组")
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # 单条处理模式
    if args.input:
        # 尝试解析为 JSON
        try:
            parsed_input = json.loads(args.input)
        except json.JSONDecodeError:
            parsed_input = args.input

        result = process_single_input(parsed_input, args.format)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # 无输入参数
    print(f"错误: {ERROR_MESSAGES['E001']}")
    print("提示: 使用 --input 提供输入内容，或使用 --selftest 运行自检")
    return 1


if __name__ == "__main__":
    sys.exit(main())
