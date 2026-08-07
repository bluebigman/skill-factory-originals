#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-claude-code-toolkit 独立实现脚本

依据功能规格 clean-room 重写，仅使用标准库。
提供命令行核心处理流程与离线自检功能。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
# 错误码与标准化话术映射（依据规格）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",  # 实际使用时需逐项追加
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 内部使用的附加错误码
    "E006": "内部处理异常，请检查输入数据",
    "E007": "输出序列化失败",
    "E008": "参数解析错误",
    "E009": "自检数据异常",
    "E010": "未预期的运行时错误",
}

# 置信度阈值（依据规格）
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85

# 关键信息字段（依据规格 Step 1）
REQUIRED_FIELDS = ["input_source", "output_format", "completeness"]


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果的数据结构"""

    def __init__(self, data: Any, confidence: float, warnings: Optional[List[str]] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings if warnings is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典结构"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "confidence_label": self._get_confidence_label(),
            "warnings": self.warnings,
        }

    def _get_confidence_label(self) -> str:
        """根据置信度生成标注标签（依据规格 Step 2.3）"""
        if self.confidence >= HIGH_CONFIDENCE:
            return "直接输出"
        elif self.confidence >= MEDIUM_CONFIDENCE:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 核心逻辑函数
# ============================================================
def validate_input(raw_input: Any) -> Optional[str]:
    """
    验证输入是否有效（对应 E001: 输入为空）

    返回错误码；无错误返回 None
    """
    if raw_input is None:
        return "E001"
    if isinstance(raw_input, str) and not raw_input.strip():
        return "E001"
    if isinstance(raw_input, (list, tuple, dict)) and len(raw_input) == 0:
        return "E001"
    return None


def extract_key_fields(input_data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入中提取关键信息并结构化（对应 Step 2.1）

    返回 (结构化字段字典, 置信度)
    """
    fields: Dict[str, Any] = {}
    confidence = 100.0

    if isinstance(input_data, str):
        # 简单文本输入：尝试识别常见键值对
        text = input_data.strip()
        if not text:
            return fields, 0.0

        # 尝试解析 JSON
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                fields = parsed
                confidence = 95.0
            else:
                fields = {"content": parsed}
                confidence = 90.0
        except json.JSONDecodeError:
            # 非 JSON 文本，按行解析键值对
            for line in text.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    fields[key.strip()] = value.strip()
                elif "=" in line:
                    key, _, value = line.partition("=")
                    fields[key.strip()] = value.strip()

            if fields:
                confidence = 80.0
            else:
                # 无法识别的纯文本
                fields = {"content": text}
                confidence = 60.0

    elif isinstance(input_data, dict):
        # 字典输入直接使用
        fields = dict(input_data)
        confidence = 95.0

    elif isinstance(input_data, (list, tuple)):
        # 列表输入：尝试结构化
        if all(isinstance(item, dict) for item in input_data):
            fields = {"items": list(input_data)}
            confidence = 88.0
        else:
            fields = {"items": list(input_data)}
            confidence = 75.0
    else:
        # 其他类型
        fields = {"value": input_data}
        confidence = 50.0

    return fields, confidence


def check_required_fields(fields: Dict[str, Any]) -> List[str]:
    """
    检查关键信息是否完整（对应 E002: 关键信息缺失）

    返回缺失字段列表
    """
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in fields or fields[field] is None or fields[field] == "":
            missing.append(field)
    return missing


def format_output(fields: Dict[str, Any], confidence: float) -> Tuple[Dict[str, Any], float]:
    """
    按默认模板组织输出（对应 Step 2.2）

    返回 (输出字典, 最终置信度)
    """
    # 默认输出模板
    output = {
        "processed": True,
        "fields_count": len(fields),
        "structured_fields": fields,
        "summary": f"成功处理 {len(fields)} 个字段",
    }

    # 根据字段数量调整置信度
    final_confidence = confidence
    if len(fields) == 0:
        final_confidence = min(final_confidence, 50.0)

    return output, final_confidence


def process_input(raw_input: Any) -> ProcessingResult:
    """
    标准处理流程（对应 Step 2 核心流程）

    参数:
        raw_input: 用户提供的原始输入

    返回:
        ProcessingResult 对象
    """
    # Step 2.1: 验证输入
    error_code = validate_input(raw_input)
    if error_code:
        return ProcessingResult(
            data={"error": error_code, "message": ERROR_MESSAGES[error_code]},
            confidence=0.0,
            warnings=[ERROR_MESSAGES[error_code]],
        )

    # Step 2.2: 提取关键信息
    fields, extract_confidence = extract_key_fields(raw_input)

    # Step 2.3: 检查关键字段完整性
    missing_fields = check_required_fields(fields)
    warnings = []
    if missing_fields:
        # 不直接返回错误，但给出警告
        warnings.append(f"缺少关键字段: {', '.join(missing_fields)}")
        # 降低置信度
        extract_confidence = min(extract_confidence, 70.0)

    # Step 2.4: 格式化输出
    output, final_confidence = format_output(fields, extract_confidence)

    # Step 2.5: 附加警告信息
    if warnings:
        output["warnings"] = warnings

    return ProcessingResult(data=output, confidence=final_confidence, warnings=warnings)


def process_batch(inputs: List[Any]) -> ProcessingResult:
    """
    批量处理输入（对应进阶用法：批量处理）

    参数:
        inputs: 输入列表

    返回:
        ProcessingResult 对象
    """
    if not inputs:
        return ProcessingResult(
            data={"error": "E001", "message": ERROR_MESSAGES["E001"]},
            confidence=0.0,
            warnings=[ERROR_MESSAGES["E001"]],
        )

    results = []
    total_confidence = 0.0
    all_warnings = []

    for item in inputs:
        result = process_input(item)
        results.append(result.to_dict())
        total_confidence += result.confidence
        all_warnings.extend(result.warnings)

    # 计算平均置信度
    avg_confidence = total_confidence / len(inputs) if inputs else 0.0

    output = {
        "batch_size": len(inputs),
        "results": results,
        "summary": f"批量处理完成，共 {len(inputs)} 项",
    }

    return ProcessingResult(data=output, confidence=avg_confidence, warnings=all_warnings)


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑（--selftest 参数触发）

    使用内置硬编码数据，不依赖外部文件、网络或工作目录。

    返回:
        True 表示全部通过，False 表示存在失败
    """
    print("=" * 60)
    print("开始自检 (Self-Test)")
    print("=" * 60)

    all_passed = True

    # 测试 1: 空输入处理（应返回 E001）
    print("\n[测试 1] 空输入处理")
    result = process_input(None)
    data = result.data
    if isinstance(data, dict) and data.get("error") == "E001":
        print("  ✓ 空输入正确返回 E001")
    else:
        print("  ✗ 空输入未正确返回 E001")
        all_passed = False

    # 测试 2: 有效文本输入
    print("\n[测试 2] 有效文本输入")
    sample_text = "input_source: 测试数据\noutput_format: json\ncompleteness: 完整"
    result = process_input(sample_text)
    if result.confidence > 50.0:
        print(f"  ✓ 文本处理置信度合理: {result.confidence:.1f}")
    else:
        print(f"  ✗ 文本处理置信度异常: {result.confidence:.1f}")
        all_passed = False

    # 测试 3: JSON 输入
    print("\n[测试 3] JSON 输入")
    sample_json = json.dumps({
        "input_source": "url",
        "output_format": "markdown",
        "completeness": "详细",
        "extra_field": "测试"
    })
    result = process_input(sample_json)
    if result.confidence > 70.0:
        print(f"  ✓ JSON 处理置信度合理: {result.confidence:.1f}")
    else:
        print(f"  ✗ JSON 处理置信度异常: {result.confidence:.1f}")
        all_passed = False

    # 测试 4: 字典输入
    print("\n[测试 4] 字典输入")
    sample_dict = {"input_source": "文件", "output_format": "txt", "completeness": "骨架"}
    result = process_input(sample_dict)
    if result.confidence > 70.0:
        print(f"  ✓ 字典处理置信度合理: {result.confidence:.1f}")
    else:
        print(f"  ✗ 字典处理置信度异常: {result.confidence:.1f}")
        all_passed = False

    # 测试 5: 批量处理
    print("\n[测试 5] 批量处理")
    batch_input = ["测试一", {"input_source": "url", "output_format": "md", "completeness": "完整"}]
    result = process_batch(batch_input)
    if result.data.get("batch_size") == 2:
        print("  ✓ 批量处理数量正确")
    else:
        print("  ✗ 批量处理数量异常")
        all_passed = False

    # 测试 6: 置信度标签逻辑
    print("\n[测试 6] 置信度标签")
    test_cases = [
        (95.0, "直接输出"),
        (87.0, "建议复核"),
        (80.0, "[需核实]"),
    ]
    for conf, expected_label in test_cases:
        result = ProcessingResult(data={}, confidence=conf)
        label = result._get_confidence_label()
        if label == expected_label:
            print(f"  ✓ 置信度 {conf}% → {label}")
        else:
            print(f"  ✗ 置信度 {conf}% → {label} (期望 {expected_label})")
            all_passed = False

    # 测试 7: 错误码完整性
    print("\n[测试 7] 错误码完整性")
    expected_codes = ["E001", "E002", "E003", "E004", "E005"]
    for code in expected_codes:
        if code in ERROR_MESSAGES and ERROR_MESSAGES[code]:
            print(f"  ✓ 错误码 {code} 存在")
        else:
            print(f"  ✗ 错误码 {code} 缺失")
            all_passed = False

    # 测试 8: 关键字段检查
    print("\n[测试 8] 关键字段检查")
    incomplete_fields = {"input_source": "test"}
    missing = check_required_fields(incomplete_fields)
    if len(missing) == 2:
        print(f"  ✓ 正确识别缺失字段: {missing}")
    else:
        print(f"  ✗ 缺失字段识别异常: {missing}")
        all_passed = False

    # 测试 9: 输出序列化
    print("\n[测试 9] 输出序列化")
    result = process_input(sample_dict)
    try:
        serialized = json.dumps(result.to_dict(), ensure_ascii=False)
        if serialized:
            print("  ✓ 输出可正常序列化为 JSON")
        else:
            print("  ✗ 序列化结果为空")
            all_passed = False
    except (TypeError, ValueError) as e:
        print(f"  ✗ 序列化失败: {e}")
        all_passed = False

    # 测试 10: 边界情况 - 列表输入
    print("\n[测试 10] 边界情况 - 列表输入")
    result = process_input([1, 2, 3])
    if result.confidence > 50.0:
        print(f"  ✓ 列表处理置信度合理: {result.confidence:.1f}")
    else:
        print(f"  ✗ 列表处理置信度异常: {result.confidence:.1f}")
        all_passed = False

    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """
    命令行主入口

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="awesome-claude-code-toolkit - 未命名工具处理脚本",
        epilog="示例: python main.py --input 'input_source: test' --format json",
    )

    # 输入参数
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（文本、JSON 字符串等）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入（JSON 数组字符串）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # 参数解析失败
        print(f"E008: 参数解析错误 - {e}")
        return 1

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 处理模式
    try:
        if args.batch:
            # 批量处理模式
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    print("E003: 批量输入必须是 JSON 数组")
                    return 1
                result = process_batch(batch_data)
            except json.JSONDecodeError:
                print("E003: 批量输入 JSON 解析失败")
                return 1
        else:
            # 单条处理模式
            if not args.input:
                print(f"E001: {ERROR_MESSAGES['E001']}")
                return 1
            result = process_input(args.input)

        # 输出结果
        if args.format == "json":
            try:
                output = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
                print(output)
            except (TypeError, ValueError) as e:
                print(f"E007: 输出序列化失败 - {e}")
                return 1
        else:
            # 文本格式输出
            print(f"处理结果: {result.data}")
            print(f"置信度: {result.confidence:.1f}%")
            if result.warnings:
                print(f"警告: {result.warnings}")

        return 0

    except Exception as e:
        # 未预期错误
        print(f"E010: 未预期的运行时错误 - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
