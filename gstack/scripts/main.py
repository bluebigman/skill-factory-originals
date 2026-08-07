#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gstack - 未命名工具
基于功能规格独立实现（clean-room），不包含任何既有代码。
"""

import sys
import json
import argparse
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码常量
# ============================================================
ERR_INPUT_EMPTY = "E001"
ERR_KEY_INFO_MISSING = "E002"
ERR_INPUT_FORMAT = "E003"
ERR_OUT_OF_SCOPE = "E004"
ERR_LOW_CONFIDENCE = "E005"
ERR_INTERNAL = "E006"
ERR_UNSUPPORTED = "E007"
ERR_CONFIG = "E008"
ERR_OUTPUT = "E009"
ERR_UNKNOWN = "E010"

# ============================================================
# 错误消息映射
# ============================================================
ERROR_MESSAGES = {
    ERR_INPUT_EMPTY: "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    ERR_KEY_INFO_MISSING: "还缺少以下信息，请补充：",
    ERR_INPUT_FORMAT: "输入格式不符合要求，示例：",
    ERR_OUT_OF_SCOPE: "这超出了本工具的能力范围，建议：",
    ERR_LOW_CONFIDENCE: "结果无法确定，建议：",
    ERR_INTERNAL: "内部错误，请重试",
    ERR_UNSUPPORTED: "不支持的输入类型",
    ERR_CONFIG: "配置错误",
    ERR_OUTPUT: "输出生成失败",
    ERR_UNKNOWN: "未知错误",
}


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果对象"""

    def __init__(self, data: Any = None, confidence: float = 1.0, warnings: Optional[List[str]] = None):
        self.data = data
        self.confidence = confidence  # 0.0 ~ 1.0
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心处理函数
# ============================================================
def extract_key_fields(content: str) -> Tuple[Dict[str, Any], float]:
    """
    从输入文本中提取关键字段。
    根据规格，识别输入中的关键信息并结构化。

    返回: (结构化字段字典, 置信度)
    """
    if not content or not content.strip():
        raise ValueError(ERR_INPUT_EMPTY)

    # 按行拆分
    lines = [line.strip() for line in content.strip().split("\n") if line.strip()]

    result: Dict[str, Any] = {}
    recognized = 0
    total = len(lines)

    for line in lines:
        # 尝试识别 "key: value" 格式
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            value = parts[1].strip()
            result[key] = value
            recognized += 1
        elif "=" in line:
            parts = line.split("=", 1)
            key = parts[0].strip().lower()
            value = parts[1].strip()
            result[key] = value
            recognized += 1
        else:
            # 无法识别的行，放入 general 字段
            if "general" not in result:
                result["general"] = []
            result["general"].append(line)
            recognized += 0.5  # 部分识别

    # 计算置信度
    if total == 0:
        confidence = 0.0
    else:
        confidence = recognized / total

    return result, confidence


def format_output(data: Dict[str, Any], fmt: str = "json") -> str:
    """
    按指定格式生成输出。
    支持的格式: json, text, key_value
    """
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "text":
        if not data:
            return ""
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(value)}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    elif fmt == "key_value":
        if not data:
            return ""
        return "\n".join(f"{key}={value}" for key, value in data.items())
    else:
        raise ValueError(ERR_UNSUPPORTED)


def process_input(input_data: str, output_format: str = "json") -> ProcessingResult:
    """
    标准处理流程：
    1. 解析输入内容，识别关键信息
    2. 结构化处理
    3. 生成结果并标注置信度
    """
    # Step 1: 检查输入
    if not input_data or not input_data.strip():
        raise ValueError(ERR_INPUT_EMPTY)

    # Step 2: 执行核心流程
    fields, confidence = extract_key_fields(input_data)

    warnings = []
    if confidence < 0.85:
        warnings.append("[需核实] 部分内容无法完全识别，请人工复核")
    elif confidence < 0.90:
        warnings.append("建议复核：识别完整度不足")

    # 检查关键信息
    if not fields:
        warnings.append("未识别到结构化字段")

    # Step 3: 生成输出
    try:
        output = format_output(fields, output_format)
    except ValueError as e:
        raise ValueError(f"{ERR_OUTPUT}: 不支持的输出格式 {output_format}") from e

    result = ProcessingResult(data=output, confidence=confidence, warnings=warnings)
    return result


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("gstack 自检开始")
    print("=" * 60)

    test_cases = [
        {
            "name": "基本解析测试",
            "input": "name: test\nage: 25\ncity: Beijing",
            "expect_confidence_gt": 0.8,
            "expect_has_field": ["name", "age", "city"],
        },
        {
            "name": "空输入测试",
            "input": "",
            "expect_error": ERR_INPUT_EMPTY,
        },
        {
            "name": "混合格式测试",
            "input": "title: 项目报告\nversion=1.0\n这是一行无法解析的内容",
            "expect_confidence_gt": 0.5,
            "expect_has_field": ["title", "version", "general"],
        },
        {
            "name": "JSON 输出测试",
            "input": "key1: value1\nkey2: value2",
            "expect_confidence_gt": 0.8,
            "expect_valid_json": True,
        },
        {
            "name": "边界输入测试",
            "input": "   ",
            "expect_error": ERR_INPUT_EMPTY,
        },
    ]

    all_passed = True

    for i, case in enumerate(test_cases, 1):
        print(f"\n[测试 {i}] {case['name']}")
        try:
            if case.get("expect_error"):
                # 期望抛出错误的测试
                try:
                    process_input(case["input"])
                    print("  ✗ 失败：期望抛出错误，但未抛出")
                    all_passed = False
                except ValueError as e:
                    error_code = str(e)
                    if error_code == case["expect_error"]:
                        print(f"  ✓ 正确抛出错误 {error_code}")
                    else:
                        print(f"  ✗ 错误码不匹配：期望 {case['expect_error']}，实际 {error_code}")
                        all_passed = False
            else:
                # 正常处理测试
                result = process_input(case["input"])

                # 检查置信度
                if result.confidence > case.get("expect_confidence_gt", 0.5):
                    print(f"  ✓ 置信度合理: {result.confidence:.2f}")
                else:
                    print(f"  ✗ 置信度偏低: {result.confidence:.2f}")
                    all_passed = False

                # 检查字段
                if case.get("expect_has_field"):
                    # 重新解析输入以检查字段（因为 process_input 返回的是格式化字符串）
                    fields, _ = extract_key_fields(case["input"])
                    for field in case["expect_has_field"]:
                        if field in fields:
                            print(f"  ✓ 字段存在: {field}")
                        else:
                            print(f"  ✗ 字段缺失: {field}")
                            all_passed = False

                # 检查 JSON 输出
                if case.get("expect_valid_json"):
                    try:
                        json.loads(result.data)
                        print("  ✓ 输出为有效 JSON")
                    except json.JSONDecodeError:
                        print("  ✗ 输出不是有效 JSON")
                        all_passed = False

        except Exception as e:
            print(f"  ✗ 意外异常: {e}")
            all_passed = False

    # 输出格式测试
    print("\n[测试 输出格式]")
    test_data = {"name": "test", "age": "25"}
    for fmt in ["json", "text", "key_value"]:
        try:
            output = format_output(test_data, fmt)
            if output:
                print(f"  ✓ 格式 {fmt} 生成成功")
            else:
                print(f"  ✗ 格式 {fmt} 生成为空")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 格式 {fmt} 生成失败: {e}")
            all_passed = False

    # 错误码测试
    print("\n[测试 错误码]")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        if code in ERROR_MESSAGES:
            print(f"  ✓ 错误码 {code} 存在且有消息")
        else:
            print(f"  ✗ 错误码 {code} 缺失")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="gstack - 未命名工具（依据功能规格独立实现）",
        epilog="示例: python main.py --input 'name: test' --format json",
    )
    parser.add_argument("--input", "-i", type=str, help="输入内容（用户提供的数据/文件/URL）")
    parser.add_argument("--format", "-f", type=str, default="json", choices=["json", "text", "key_value"], help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print(f"错误 {ERR_INPUT_EMPTY}: {ERROR_MESSAGES[ERR_INPUT_EMPTY]}", file=sys.stderr)
        return 1

    try:
        result = process_input(args.input, args.format)

        # 输出结果
        print(result.data)

        # 输出警告
        for warning in result.warnings:
            print(f"提示: {warning}", file=sys.stderr)

        return 0

    except ValueError as e:
        error_code = str(e)
        if error_code in ERROR_MESSAGES:
            print(f"错误 {error_code}: {ERROR_MESSAGES[error_code]}", file=sys.stderr)
        else:
            print(f"错误 {ERR_UNKNOWN}: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 {ERR_INTERNAL}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
