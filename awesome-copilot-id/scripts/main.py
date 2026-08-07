#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-copilot-id 技能实现脚本
仅供学习与参考用途，不构成任何专业建议。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与话术映射（依据功能规格）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：",
}

# 置信度阈值（依据功能规格）
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 默认输出模板字段
DEFAULT_FIELDS = ["关键信息", "结构化结果", "置信度"]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果的数据结构"""
    
    def __init__(self, data: Dict[str, Any], confidence: float, warnings: Optional[List[str]] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings
        }


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(raw_input: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    解析输入内容，识别关键信息
    
    参数:
        raw_input: 原始输入字符串
        
    返回:
        (解析结果, 错误码或None)
    """
    # 检查输入是否为空
    if not raw_input or not raw_input.strip():
        return None, "E001"
    
    # 尝试解析为 JSON
    try:
        parsed = json.loads(raw_input)
        if isinstance(parsed, dict):
            return parsed, None
        elif isinstance(parsed, list):
            # 列表包装为字典
            return {"items": parsed}, None
        else:
            return None, "E003"
    except json.JSONDecodeError:
        # 非 JSON 格式，尝试键值对解析
        return _parse_key_value(raw_input)


def _parse_key_value(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    解析键值对格式的输入
    支持格式: key1=value1, key2=value2 或 key1: value1; key2: value2
    """
    result: Dict[str, Any] = {}
    
    # 尝试多种分隔符
    patterns = [
        r'(\w+)\s*=\s*([^,;]+)',
        r'(\w+)\s*:\s*([^,;]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            for key, value in matches:
                result[key.strip()] = value.strip()
            break
    
    if not result:
        # 无法识别格式，返回错误
        return None, "E003"
    
    return result, None


def extract_key_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    识别输入中的关键信息并结构化
    
    参数:
        data: 解析后的输入数据
        
    返回:
        结构化后的关键信息
    """
    structured: Dict[str, Any] = {}
    
    # 遍历所有字段，识别关键信息
    for key, value in data.items():
        # 处理嵌套字典
        if isinstance(value, dict):
            structured[key] = extract_key_info(value)
        # 处理列表
        elif isinstance(value, list):
            structured[key] = [_extract_item_info(item) for item in value]
        # 处理基本类型
        else:
            structured[key] = _normalize_value(value)
    
    return structured


def _extract_item_info(item: Any) -> Any:
    """提取单个列表项的信息"""
    if isinstance(item, dict):
        return extract_key_info(item)
    elif isinstance(item, (str, int, float, bool)):
        return _normalize_value(item)
    else:
        return str(item)


def _normalize_value(value: Any) -> Any:
    """规范化值，去除多余空白等"""
    if isinstance(value, str):
        return value.strip()
    return value


def calculate_confidence(data: Dict[str, Any], warnings: List[str]) -> float:
    """
    计算置信度（依据功能规格）
    
    规则:
    - 数据完整且无警告: ≥90%
    - 有少量不确定项: 85%-90%
    - 大量不确定项: <85%
    """
    if not data:
        return 0.0
    
    # 基础置信度
    base = 0.95
    
    # 根据警告数量降低置信度
    warning_penalty = len(warnings) * 0.05
    
    # 根据字段数量评估完整性
    field_count = len(data)
    if field_count < 3:
        base -= 0.05  # 字段太少，降低置信度
    
    confidence = max(0.0, min(1.0, base - warning_penalty))
    return confidence


def identify_uncertainties(data: Dict[str, Any]) -> List[str]:
    """
    识别不确定项
    
    返回:
        不确定项的说明列表
    """
    uncertainties: List[str] = []
    
    for key, value in data.items():
        # 空值或 None 视为不确定
        if value is None or value == "":
            uncertainties.append(f"字段 '{key}' 为空值")
        # 过长的字符串可能包含噪声
        elif isinstance(value, str) and len(value) > 500:
            uncertainties.append(f"字段 '{key}' 内容过长，可能存在冗余信息")
        # 嵌套结构深度过深
        elif isinstance(value, dict) and len(value) > 10:
            uncertainties.append(f"字段 '{key}' 嵌套层级过深")
    
    return uncertainties


def format_output(result: ProcessingResult, custom_format: Optional[str] = None) -> str:
    """
    按格式生成输出
    
    参数:
        result: 处理结果
        custom_format: 自定义输出格式（可选）
        
    返回:
        格式化后的输出字符串
    """
    # 根据置信度添加标注
    if result.confidence >= CONFIDENCE_HIGH:
        confidence_label = "高置信度"
    elif result.confidence >= CONFIDENCE_MEDIUM:
        confidence_label = "建议复核"
    else:
        confidence_label = "[需核实]"
    
    # 构建输出
    output_lines = []
    
    # 自定义格式处理
    if custom_format:
        try:
            # 尝试用 JSON 格式输出
            if custom_format.lower() == "json":
                return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
            elif custom_format.lower() == "text":
                output_lines.append(f"置信度: {result.confidence:.2%} ({confidence_label})")
                for key, value in result.data.items():
                    output_lines.append(f"{key}: {value}")
                return "\n".join(output_lines)
        except Exception:
            # 自定义格式解析失败，使用默认格式
            pass
    
    # 默认格式输出
    output_lines.append(f"处理结果 (置信度: {result.confidence:.2%} - {confidence_label})")
    output_lines.append("=" * 50)
    
    for key, value in result.data.items():
        output_lines.append(f"[{key}]")
        output_lines.append(f"  {value}")
    
    # 添加警告信息
    if result.warnings:
        output_lines.append("-" * 50)
        output_lines.append("警告信息:")
        for warning in result.warnings:
            output_lines.append(f"  ⚠ {warning}")
    
    # 添加免责声明
    output_lines.append("-" * 50)
    output_lines.append("⚠ 本内容仅供一般信息参考，不构成专业建议。")
    output_lines.append("   涉及专业决策时，请务必咨询持证专业人士。")
    
    return "\n".join(output_lines)


def validate_result(result: ProcessingResult) -> Tuple[bool, Optional[str]]:
    """
    校验处理结果
    
    返回:
        (是否通过, 错误码或None)
    """
    # 检查结果是否为空
    if not result.data:
        return False, "E002"
    
    # 检查置信度是否过低
    if result.confidence < CONFIDENCE_MEDIUM:
        return False, "E005"
    
    return True, None


# ============================================================
# 主处理流程
# ============================================================

def process_input(raw_input: str, output_format: Optional[str] = None) -> Tuple[ProcessingResult, Optional[str]]:
    """
    执行标准处理流程
    
    参数:
        raw_input: 原始输入
        output_format: 期望的输出格式
        
    返回:
        (处理结果, 错误码或None)
    """
    # Step 1: 解析输入
    parsed_data, error = parse_input(raw_input)
    if error:
        return ProcessingResult({}, 0.0), error
    
    # Step 2: 识别关键信息
    structured_data = extract_key_info(parsed_data)
    
    # 识别不确定项
    uncertainties = identify_uncertainties(structured_data)
    
    # 计算置信度
    confidence = calculate_confidence(structured_data, uncertainties)
    
    # 构建处理结果
    result = ProcessingResult(structured_data, confidence, uncertainties)
    
    # Step 3: 校验结果
    valid, validation_error = validate_result(result)
    if not valid:
        return result, validation_error
    
    return result, None


def batch_process(inputs: List[str], output_format: Optional[str] = None) -> List[Tuple[ProcessingResult, Optional[str]]]:
    """
    批量处理多个输入
    
    参数:
        inputs: 输入列表
        output_format: 输出格式
        
    返回:
        处理结果列表
    """
    results = []
    for raw_input in inputs:
        result, error = process_input(raw_input, output_format)
        results.append((result, error))
    return results


# ============================================================
# 自测模块
# ============================================================

def run_selftest() -> bool:
    """
    内置自测逻辑，使用硬编码样例数据离线验证核心功能
    
    返回:
        True 表示全部通过，False 表示存在失败项
    """
    print("=" * 60)
    print("开始运行自测...")
    print("=" * 60)
    
    all_passed = True
    
    # 测试 1: 解析 JSON 输入
    print("\n[测试 1] JSON 输入解析")
    json_input = '{"name": "测试项目", "type": "文档", "size": 1024}'
    parsed, error = parse_input(json_input)
    assert error is None, f"JSON 解析失败: {error}"
    assert parsed is not None and len(parsed) >= 3, "JSON 解析结果字段不足"
    print("  ✓ JSON 输入解析通过")
    
    # 测试 2: 键值对输入解析
    print("\n[测试 2] 键值对输入解析")
    kv_input = "name=测试, type=文档, size=1024"
    parsed, error = parse_input(kv_input)
    assert error is None, f"键值对解析失败: {error}"
    assert parsed is not None and "name" in parsed, "键值对解析缺少关键字段"
    print("  ✓ 键值对输入解析通过")
    
    # 测试 3: 空输入错误处理
    print("\n[测试 3] 空输入错误处理")
    parsed, error = parse_input("")
    assert error == "E001", f"空输入应返回 E001，实际: {error}"
    print("  ✓ 空输入错误处理通过")
    
    # 测试 4: 格式错误处理
    print("\n[测试 4] 格式错误处理")
    parsed, error = parse_input("!!!invalid!!!")
    assert error == "E003", f"格式错误应返回 E003，实际: {error}"
    print("  ✓ 格式错误处理通过")
    
    # 测试 5: 关键信息提取
    print("\n[测试 5] 关键信息提取")
    test_data = {"name": "  测试项目  ", "tags": ["a", "b", "c"], "meta": {"version": "1.0"}}
    structured = extract_key_info(test_data)
    assert structured["name"] == "测试项目", "字符串未去除空白"
    assert len(structured["tags"]) == 3, "列表处理错误"
    assert structured["meta"]["version"] == "1.0", "嵌套字典处理错误"
    print("  ✓ 关键信息提取通过")
    
    # 测试 6: 置信度计算
    print("\n[测试 6] 置信度计算")
    complete_data = {"field1": "value1", "field2": "value2", "field3": "value3"}
    conf = calculate_confidence(complete_data, [])
    assert conf > 0.85, f"完整数据置信度应大于 0.85，实际: {conf}"
    
    incomplete_data = {"field1": "value1"}
    conf_low = calculate_confidence(incomplete_data, ["字段缺失"])
    assert conf_low < conf, "不完整数据置信度应低于完整数据"
    print("  ✓ 置信度计算通过")
    
    # 测试 7: 不确定项识别
    print("\n[测试 7] 不确定项识别")
    uncertain_data = {"empty": "", "normal": "value", "long": "x" * 600}
    uncertainties = identify_uncertainties(uncertain_data)
    assert len(uncertainties) >= 2, "应识别出至少 2 个不确定项"
    print("  ✓ 不确定项识别通过")
    
    # 测试 8: 完整处理流程
    print("\n[测试 8] 完整处理流程")
    result, error = process_input('{"title": "测试", "content": "内容", "author": "作者"}')
    assert error is None, f"处理流程失败: {error}"
    assert result.confidence > 0.5, "置信度应大于 0.5"
    assert len(result.data) == 3, "处理结果字段数应为 3"
    print("  ✓ 完整处理流程通过")
    
    # 测试 9: 批量处理
    print("\n[测试 9] 批量处理")
    inputs = [
        '{"item1": "a", "item2": "b"}',
        "key1=value1, key2=value2",
        "invalid input format"
    ]
    results = batch_process(inputs)
    assert len(results) == 3, "批量处理数量错误"
    success_count = sum(1 for _, err in results if err is None)
    assert success_count >= 2, "批量处理成功率应不低于 2/3"
    print("  ✓ 批量处理通过")
    
    # 测试 10: 输出格式化
    print("\n[测试 10] 输出格式化")
    test_result = ProcessingResult({"name": "测试"}, 0.95, [])
    formatted = format_output(test_result)
    assert "测试" in formatted, "输出应包含数据内容"
    assert "置信度" in formatted, "输出应包含置信度信息"
    
    json_output = format_output(test_result, "json")
    parsed_json = json.loads(json_output)
    assert parsed_json["confidence"] > 0.9, "JSON 输出置信度应大于 0.9"
    print("  ✓ 输出格式化通过")
    
    # 测试 11: 错误码覆盖
    print("\n[测试 11] 错误码覆盖")
    test_cases = [
        ("", "E001"),  # 空输入
        ("invalid format", "E003"),  # 格式错误
    ]
    for test_input, expected_error in test_cases:
        _, error = process_input(test_input)
        assert error == expected_error, f"期望 {expected_error}，实际 {error}"
    print("  ✓ 错误码覆盖通过")
    
    # 测试 12: 免责声明包含
    print("\n[测试 12] 免责声明包含")
    result, _ = process_input('{"data": "test"}')
    output = format_output(result)
    assert "仅供一般信息参考" in output, "输出应包含免责声明"
    print("  ✓ 免责声明包含通过")
    
    print("\n" + "=" * 60)
    print("所有自测通过！")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="awesome-copilot-id 技能处理工具",
        epilog="仅供学习与参考用途，不构成专业建议。"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（JSON 或 key=value 格式）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，多个输入用分号(;)分隔"
    )
    
    args = parser.parse_args()
    
    # 运行自测
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自测失败: {e}")
            return 1
        except Exception as e:
            print(f"自测异常: {e}")
            return 1
    
    # 批量处理模式
    if args.batch:
        inputs = [item.strip() for item in args.batch.split(";") if item.strip()]
        results = batch_process(inputs, args.format)
        for idx, (result, error) in enumerate(results, 1):
            print(f"\n--- 输入 {idx} ---")
            if error:
                print(f"错误 [{error}]: {ERROR_MESSAGES.get(error, '未知错误')}")
            else:
                print(format_output(result, args.format))
        return 0
    
    # 单条处理模式
    if args.input:
        result, error = process_input(args.input, args.format)
        if error:
            print(f"错误 [{error}]: {ERROR_MESSAGES.get(error, '未知错误')}")
            return 1
        print(format_output(result, args.format))
        return 0
    
    # 无输入参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
