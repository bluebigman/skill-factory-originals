#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

数据可视化 Skill 的独立实现脚本（clean-room 重写）。
本脚本仅依据功能规格设计，不参考任何既有实现。

功能概述：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

错误码体系：
- E001: 输入为空
- E002: 关键信息缺失
- E003: 输入格式错误
- E004: 超出能力边界
- E005: 置信度过低
- E006: 内部处理异常
- E007: 参数解析失败
- E008: 输出生成失败
- E009: 批量处理中断
- E010: 未知错误

使用方式：
    python scripts/main.py --input "..." [--format json|text] [--batch]
    python scripts/main.py --selftest   # 离线自检
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与话术映射（依据规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出生成失败，请检查输出格式",
    "E009": "批量处理中断，请检查各项输入",
    "E010": "发生未知错误，请联系维护人员",
}

# 置信度阈值（依据规格第三节）
HIGH_CONFIDENCE_THRESHOLD = 0.90
MEDIUM_CONFIDENCE_THRESHOLD = 0.85

# 支持的可识别输入前缀
URL_PREFIXES = ("http://", "https://", "ftp://")
FILE_PREFIXES = ("file://", "./", "../", "/")


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果的数据结构"""

    def __init__(
        self,
        status: str = "success",
        data: Optional[Any] = None,
        confidence: float = 1.0,
        warnings: Optional[List[str]] = None,
        error_code: Optional[str] = None,
    ):
        self.status = status
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []
        self.error_code = error_code

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "status": self.status,
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "error_code": self.error_code,
        }

    def to_text(self) -> str:
        """转换为文本格式"""
        if self.status == "error":
            return f"[错误 {self.error_code}] {self._get_error_message()}"
        lines = [f"状态: {self.status}", f"置信度: {self.confidence:.0%}"]
        if self.warnings:
            lines.append("警告:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.data is not None:
            lines.append(f"数据: {self.data}")
        return "\n".join(lines)

    def _get_error_message(self) -> str:
        """获取错误消息"""
        if self.error_code and self.error_code in ERROR_MESSAGES:
            return ERROR_MESSAGES[self.error_code]
        return ERROR_MESSAGES["E010"]


# ============================================================
# 核心功能函数
# ============================================================

def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    验证输入是否有效

    Args:
        raw_input: 原始输入

    Returns:
        (是否有效, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str):
        if not raw_input.strip():
            return False, "E001"
    elif isinstance(raw_input, (list, tuple, dict)):
        if len(raw_input) == 0:
            return False, "E001"
    elif isinstance(raw_input, (int, float, bool)):
        # 数字类型和布尔类型也是有效输入
        pass
    else:
        return False, "E003"
    return True, None


def detect_input_type(raw_input: str) -> str:
    """
    检测输入类型

    Args:
        raw_input: 原始输入字符串

    Returns:
        输入类型: "url" / "file" / "text" / "structured"
    """
    if raw_input.startswith(URL_PREFIXES):
        return "url"
    if raw_input.startswith(FILE_PREFIXES):
        return "file"
    if raw_input.startswith(("{", "[")):
        return "structured"
    return "text"


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    提取输入中的关键字段

    Args:
        data: 输入数据

    Returns:
        结构化字段字典
    """
    if isinstance(data, dict):
        # 已经是结构化数据，直接返回
        return data
    elif isinstance(data, str):
        # 尝试解析 JSON
        try:
            parsed = json.loads(data)
            return extract_key_fields(parsed)
        except json.JSONDecodeError:
            # 非 JSON 文本，提取基本信息
            return {
                "content": data.strip(),
                "length": len(data.strip()),
                "type": "text",
            }
    elif isinstance(data, (list, tuple)):
        return {
            "items": list(data),
            "count": len(data),
            "type": "list",
        }
    elif isinstance(data, (int, float, bool)):
        return {
            "value": data,
            "type": "number" if isinstance(data, (int, float)) else "boolean",
        }
    else:
        return {
            "value": data,
            "type": type(data).__name__,
        }


def calculate_confidence(data: Any) -> Tuple[float, List[str]]:
    """
    计算处理结果的置信度

    Args:
        data: 处理后的数据

    Returns:
        (置信度, 警告列表)
    """
    warnings = []
    confidence = 1.0

    if isinstance(data, dict):
        # 检查是否有明显缺失
        if not data:
            confidence = 0.5
            warnings.append("数据为空，置信度较低")
        elif "type" in data and data["type"] == "text":
            # 纯文本处理，置信度中等
            confidence = 0.88
            warnings.append("文本数据可能包含未识别的关键信息")
        elif "type" in data and data["type"] == "number":
            # 数字类型，置信度较高
            confidence = 0.95
    elif isinstance(data, list):
        if len(data) == 0:
            confidence = 0.6
            warnings.append("列表为空，请确认输入")
    elif data is None:
        confidence = 0.0
        warnings.append("无法识别有效内容")

    # 根据警告数量调整置信度
    confidence -= len(warnings) * 0.05
    confidence = max(0.0, min(1.0, confidence))

    return confidence, warnings


def process_single_input(raw_input: Any) -> ProcessingResult:
    """
    处理单个输入

    Args:
        raw_input: 原始输入

    Returns:
        处理结果
    """
    # 1. 验证输入
    is_valid, error_code = validate_input(raw_input)
    if not is_valid:
        return ProcessingResult(
            status="error",
            error_code=error_code,
            confidence=0.0,
        )

    # 2. 识别输入类型（针对字符串输入）
    input_type = "unknown"
    if isinstance(raw_input, str):
        input_type = detect_input_type(raw_input)
    elif isinstance(raw_input, (int, float)):
        input_type = "number"
    elif isinstance(raw_input, bool):
        input_type = "boolean"
    elif isinstance(raw_input, (list, tuple)):
        input_type = "list"
    elif isinstance(raw_input, dict):
        input_type = "structured"

    # 3. 提取关键字段
    try:
        structured = extract_key_fields(raw_input)
    except Exception:
        return ProcessingResult(
            status="error",
            error_code="E006",
            confidence=0.0,
        )

    # 4. 计算置信度
    confidence, warnings = calculate_confidence(structured)

    # 5. 根据置信度给出提示
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        pass  # 直接输出
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        warnings.append("建议复核：结果置信度中等")
    else:
        warnings.append("[需核实] 结果置信度较低，请人工确认")

    # 6. 组装结果
    result_data = {
        "input_type": input_type,
        "structured_data": structured,
        "processed_at": "offline",  # 离线处理标记
    }

    return ProcessingResult(
        status="success",
        data=result_data,
        confidence=confidence,
        warnings=warnings,
    )


def process_batch_input(inputs: List[Any]) -> ProcessingResult:
    """
    批量处理输入

    Args:
        inputs: 输入列表

    Returns:
        处理结果
    """
    if not inputs:
        return ProcessingResult(
            status="error",
            error_code="E001",
            confidence=0.0,
        )

    results = []
    all_warnings = []

    for idx, item in enumerate(inputs):
        result = process_single_input(item)
        if result.status == "error":
            # 批量处理中遇到错误，记录并继续
            all_warnings.append(f"第 {idx + 1} 项处理失败: {result.error_code}")
            results.append(result.to_dict())
            continue
        results.append(result.to_dict())
        all_warnings.extend(result.warnings)

    # 计算整体置信度
    avg_confidence = sum(r["confidence"] for r in results) / len(results) if results else 0.0

    return ProcessingResult(
        status="success" if avg_confidence >= MEDIUM_CONFIDENCE_THRESHOLD else "warning",
        data={"batch_results": results, "total": len(results)},
        confidence=avg_confidence,
        warnings=all_warnings,
    )


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    格式化输出

    Args:
        result: 处理结果
        output_format: 输出格式 (json/text)

    Returns:
        格式化后的字符串
    """
    try:
        if output_format == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        else:
            return result.to_text()
    except Exception:
        return f"[错误 E008] {ERROR_MESSAGES['E008']}"


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检

    使用硬编码样例数据，不读取外部文件、不访问网络。

    Returns:
        自检是否通过
    """
    print("=" * 60)
    print("Preswald Skill 自检程序")
    print("=" * 60)

    all_passed = True

    # 测试用例 1: 有效文本输入
    print("\n[测试 1] 有效文本输入")
    test_input = "这是一个测试数据集，包含销售数据：产品A 100件，产品B 200件"
    result = process_single_input(test_input)
    print(f"  状态: {result.status}")
    print(f"  置信度: {result.confidence:.2f}")
    assert result.status == "success", "有效输入应返回成功状态"
    assert result.confidence > 0.5, "有效输入的置信度应大于 0.5"
    assert result.data is not None, "结果不应为空"
    print("  ✅ 通过")

    # 测试用例 2: JSON 结构化输入
    print("\n[测试 2] JSON 结构化输入")
    test_json = '{"name": "测试项目", "value": 42, "tags": ["a", "b"]}'
    result = process_single_input(test_json)
    print(f"  状态: {result.status}")
    assert result.status == "success", "JSON 输入应处理成功"
    assert "structured_data" in result.data, "应包含结构化数据"
    print("  ✅ 通过")

    # 测试用例 3: 空输入（应返回 E001）
    print("\n[测试 3] 空输入错误处理")
    result = process_single_input("")
    print(f"  状态: {result.status}, 错误码: {result.error_code}")
    assert result.status == "error", "空输入应返回错误状态"
    assert result.error_code == "E001", "空输入应返回 E001"
    print("  ✅ 通过")

    # 测试用例 4: 批量输入
    print("\n[测试 4] 批量输入处理")
    batch_input = ["数据1", "数据2", "数据3"]
    result = process_batch_input(batch_input)
    print(f"  状态: {result.status}, 置信度: {result.confidence:.2f}")
    assert result.status == "success" or result.status == "warning", "批量处理应返回成功或警告"
    assert result.data["total"] == 3, "应处理全部 3 项输入"
    print("  ✅ 通过")

    # 测试用例 5: 置信度计算
    print("\n[测试 5] 置信度计算")
    conf, warnings = calculate_confidence({"content": "测试", "type": "text"})
    print(f"  置信度: {conf:.2f}, 警告数: {len(warnings)}")
    assert 0.0 <= conf <= 1.0, "置信度应在 0-1 之间"
    assert len(warnings) > 0, "文本类型应产生警告"
    print("  ✅ 通过")

    # 测试用例 6: 错误消息映射
    print("\n[测试 6] 错误消息映射")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        msg = ERROR_MESSAGES.get(code, "")
        assert len(msg) > 0, f"错误码 {code} 应有对应消息"
    print("  所有错误码均有对应消息")
    print("  ✅ 通过")

    # 测试用例 7: 输入类型检测
    print("\n[测试 7] 输入类型检测")
    assert detect_input_type("http://example.com") == "url", "URL 识别失败"
    assert detect_input_type("./data.csv") == "file", "文件路径识别失败"
    assert detect_input_type('{"key": "value"}') == "structured", "JSON 识别失败"
    assert detect_input_type("普通文本") == "text", "文本识别失败"
    print("  所有类型检测通过")
    print("  ✅ 通过")

    # 测试用例 8: 输出格式化
    print("\n[测试 8] 输出格式化")
    test_result = ProcessingResult(status="success", data={"test": True}, confidence=0.95)
    json_output = format_output(test_result, "json")
    text_output = format_output(test_result, "text")
    assert "test" in json_output, "JSON 输出应包含数据"
    assert "置信度" in text_output, "文本输出应包含置信度"
    print("  ✅ 通过")

    # 测试用例 9: 边界情况 - None 输入
    print("\n[测试 9] None 输入处理")
    result = process_single_input(None)
    assert result.status == "error", "None 输入应返回错误"
    assert result.error_code == "E001", "None 输入应返回 E001"
    print("  ✅ 通过")

    # 测试用例 10: 数字输入
    print("\n[测试 10] 数字输入处理")
    result = process_single_input(12345)
    print(f"  状态: {result.status}")
    assert result.status == "success", "数字输入应处理成功"
    assert "structured_data" in result.data, "数字输入应被结构化"
    assert result.data["input_type"] == "number", "数字输入类型应为 number"
    print("  ✅ 通过")

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("所有自检测试通过 ✅")
    else:
        print("存在失败的测试 ❌")
    print("=" * 60)

    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主函数

    Returns:
        退出码 (0 表示成功，非 0 表示失败)
    """
    parser = argparse.ArgumentParser(
        description="Preswald 数据可视化 Skill - 独立实现",
        epilog="示例: python scripts/main.py --input '数据内容' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的数据/文件路径/URL",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入为 JSON 数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序",
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse 会调用 sys.exit，这里捕获以便返回错误码
        return 2

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 正常处理模式
    if not args.input:
        print(f"[错误 E001] {ERROR_MESSAGES['E001']}")
        return 1

    try:
        if args.batch:
            # 批量模式：尝试解析 JSON 数组
            try:
                batch_data = json.loads(args.input)
                if not isinstance(batch_data, list):
                    print(f"[错误 E003] {ERROR_MESSAGES['E003']} 批量模式需要 JSON 数组")
                    return 1
                result = process_batch_input(batch_data)
            except json.JSONDecodeError:
                print(f"[错误 E003] {ERROR_MESSAGES['E003']} 批量模式需要有效的 JSON 数组")
                return 1
        else:
            # 单条模式
            result = process_single_input(args.input)

        # 输出结果
        output = format_output(result, args.format)
        print(output)

        # 根据结果状态返回退出码
        if result.status == "error":
            return 1
        return 0

    except Exception as e:
        print(f"[错误 E010] {ERROR_MESSAGES['E010']}: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
