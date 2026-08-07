#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - feishu-docx 技能核心逻辑（全新独立实现）

本脚本依据功能规格独立编写，不包含任何既有代码。
提供离线自检（--selftest）能力，使用内置硬编码样例数据。
错误码体系：E001-E010
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "参数解析失败",
    "E008": "输出序列化失败",
    "E009": "自检数据异常",
    "E010": "未知错误",
}

CONFIDENCE_HIGH = 90      # 置信度 >= 90：直接输出
CONFIDENCE_MEDIUM = 85    # 85-90：建议复核
# 低于 85：标注 [需核实]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessResult:
    """处理结果封装"""

    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        error_code: Optional[str] = None,
        message: str = "",
    ):
        self.success = success
        self.data = data if data is not None else {}
        self.confidence = confidence
        self.error_code = error_code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "confidence": self.confidence,
            "error_code": self.error_code,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# 核心功能实现
# ---------------------------------------------------------------------------
def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效。

    返回: (是否有效, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"

    # 处理字符串输入
    if isinstance(raw_input, str):
        if not raw_input.strip():
            return False, "E001"
        return True, None

    # 处理字典/列表输入
    if isinstance(raw_input, (dict, list)):
        if len(raw_input) == 0:
            return False, "E001"
        return True, None

    # 其他类型视为无效
    return False, "E003"


def extract_key_fields(raw_input: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段并结构化。

    支持的输入形式：
    - 字符串：按行解析，识别 "key: value" 模式
    - 字典：直接使用
    - 列表：逐项处理
    """
    result: Dict[str, Any] = {}

    if isinstance(raw_input, dict):
        # 字典输入直接使用
        result = dict(raw_input)
    elif isinstance(raw_input, list):
        # 列表输入，尝试解析每项
        for idx, item in enumerate(raw_input):
            if isinstance(item, dict):
                result[f"item_{idx}"] = item
            else:
                result[f"item_{idx}"] = str(item)
    elif isinstance(raw_input, str):
        # 字符串输入，按行解析 key: value
        for line in raw_input.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip()
            else:
                # 无冒号的行，作为普通文本
                result.setdefault("text", []).append(line)

    return result


def calculate_confidence(data: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）。

    规则：
    - 有数据：基础 80 分
    - 字段数量 >= 3：+10 分
    - 字段数量 >= 5：+5 分
    - 有 text 字段：+3 分
    - 上限 100
    """
    if not data:
        return 0.0

    confidence = 80.0

    field_count = len(data)
    if field_count >= 3:
        confidence += 10.0
    if field_count >= 5:
        confidence += 5.0

    if "text" in data:
        confidence += 3.0

    return min(confidence, 100.0)


def format_confidence_label(confidence: float) -> str:
    """
    根据置信度生成标注。
    """
    if confidence >= CONFIDENCE_HIGH:
        return "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "建议复核"
    else:
        return "[需核实]"


def process_input(raw_input: Any) -> ProcessResult:
    """
    核心处理流程。

    Step 1: 校验输入
    Step 2: 提取关键字段
    Step 3: 计算置信度并标注
    """
    # Step 1: 输入校验
    is_valid, error_code = validate_input(raw_input)
    if not is_valid:
        return ProcessResult(
            success=False,
            error_code=error_code,
            message=ERROR_CODES.get(error_code, ERROR_CODES["E010"]),
        )

    # Step 2: 提取关键字段
    try:
        extracted = extract_key_fields(raw_input)
    except Exception as e:
        return ProcessResult(
            success=False,
            error_code="E006",
            message=f"{ERROR_CODES['E006']}: {str(e)}",
        )

    # Step 3: 计算置信度
    confidence = calculate_confidence(extracted)
    label = format_confidence_label(confidence)

    # 组装输出
    output_data = {
        "structured": extracted,
        "confidence": confidence,
        "confidence_label": label,
    }

    # 低置信度处理
    if confidence < CONFIDENCE_MEDIUM:
        output_data["warning"] = "结果无法确定，建议人工复核"
        return ProcessResult(
            success=True,
            data=output_data,
            confidence=confidence,
            error_code="E005",
            message=ERROR_CODES["E005"],
        )

    return ProcessResult(
        success=True,
        data=output_data,
        confidence=confidence,
        message="处理成功",
    )


def batch_process(inputs: List[Any]) -> List[ProcessResult]:
    """
    批量处理多个输入。
    """
    results = []
    for item in inputs:
        results.append(process_input(item))
    return results


def format_output(result: ProcessResult, output_format: str = "json") -> str:
    """
    格式化输出结果。

    支持格式：json, text
    """
    try:
        if output_format == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        elif output_format == "text":
            lines = []
            if result.success:
                lines.append(f"处理结果: 成功")
                lines.append(f"置信度: {result.confidence:.1f}% ({result.message})")
                if result.data:
                    lines.append("结构化数据:")
                    for key, value in result.data.items():
                        if key == "structured":
                            for k, v in value.items():
                                lines.append(f"  {k}: {v}")
                        elif key == "confidence_label":
                            lines.append(f"  标注: {value}")
                        elif key == "warning":
                            lines.append(f"  警告: {value}")
            else:
                lines.append(f"处理结果: 失败")
                lines.append(f"错误码: {result.error_code}")
                lines.append(f"错误信息: {result.message}")
            return "\n".join(lines)
        else:
            return json.dumps(result.to_dict(), ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "E008", "message": ERROR_CODES["E008"]})


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不依赖外部文件或网络。
    使用宽松阈值进行断言，确保稳健。
    """
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 测试用例 1: 正常字符串输入
    print("\n[测试1] 字符串输入")
    test_input_1 = "标题: 项目报告\n作者: 张三\n日期: 2026-01-01\n内容: 这是测试内容"
    result_1 = process_input(test_input_1)
    assert result_1.success, f"测试1失败: {result_1.message}"
    assert result_1.confidence > 0, "测试1失败: 置信度应为正数"
    assert len(result_1.data.get("structured", {})) >= 3, "测试1失败: 应提取至少3个字段"
    print(f"  ✓ 通过 (置信度: {result_1.confidence:.1f}%)")

    # 测试用例 2: 字典输入
    print("\n[测试2] 字典输入")
    test_input_2 = {"name": "测试", "type": "doc", "size": 1024, "tags": ["a", "b"]}
    result_2 = process_input(test_input_2)
    assert result_2.success, f"测试2失败: {result_2.message}"
    assert result_2.confidence >= 80, "测试2失败: 置信度应>=80"
    print(f"  ✓ 通过 (置信度: {result_2.confidence:.1f}%)")

    # 测试用例 3: 空输入
    print("\n[测试3] 空输入")
    result_3 = process_input("")
    assert not result_3.success, "测试3失败: 空输入应失败"
    assert result_3.error_code == "E001", f"测试3失败: 错误码应为E001, 实际{result_3.error_code}"
    print(f"  ✓ 通过 (错误码: {result_3.error_code})")

    # 测试用例 4: 批量处理
    print("\n[测试4] 批量处理")
    test_inputs = [
        {"key1": "value1", "key2": "value2", "key3": "value3"},
        "简单文本输入",
        "",
    ]
    batch_results = batch_process(test_inputs)
    assert len(batch_results) == 3, "测试4失败: 应返回3个结果"
    assert batch_results[0].success, "测试4失败: 第一个输入应成功"
    assert not batch_results[2].success, "测试4失败: 第三个输入应失败"
    print("  ✓ 通过")

    # 测试用例 5: 置信度标注
    print("\n[测试5] 置信度标注")
    label_high = format_confidence_label(95.0)
    label_medium = format_confidence_label(87.0)
    label_low = format_confidence_label(70.0)
    assert label_high == "直接输出", "测试5失败: 高置信度标注错误"
    assert label_medium == "建议复核", "测试5失败: 中置信度标注错误"
    assert label_low == "[需核实]", "测试5失败: 低置信度标注错误"
    print("  ✓ 通过")

    # 测试用例 6: 输出格式化
    print("\n[测试6] 输出格式化")
    test_result = ProcessResult(
        success=True,
        data={"structured": {"a": 1}, "confidence": 90.0, "confidence_label": "直接输出"},
        confidence=90.0,
        message="测试",
    )
    json_output = format_output(test_result, "json")
    text_output = format_output(test_result, "text")
    assert "success" in json_output, "测试6失败: JSON输出缺少success字段"
    assert "处理结果" in text_output, "测试6失败: 文本输出缺少处理结果"
    print("  ✓ 通过")

    # 测试用例 7: 错误码体系
    print("\n[测试7] 错误码体系")
    assert len(ERROR_CODES) == 10, "测试7失败: 应有10个错误码"
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"测试7失败: 缺少错误码{code}"
    print("  ✓ 通过")

    print("\n" + "=" * 60)
    print("所有自检通过!")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    命令行主入口。

    支持参数：
    --input: 输入内容（字符串）
    --file: 输入文件路径
    --format: 输出格式（json/text）
    --selftest: 运行自检
    """
    parser = argparse.ArgumentParser(
        description="feishu-docx 技能核心逻辑",
        epilog="示例: python main.py --input '标题: 测试' --format json",
    )
    parser.add_argument("--input", type=str, help="输入内容（字符串）")
    parser.add_argument("--file", type=str, help="输入文件路径")
    parser.add_argument("--format", type=str, choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 内部错误
        print(json.dumps({
            "success": False,
            "error_code": "E007",
            "message": ERROR_CODES["E007"],
        }, ensure_ascii=False))
        return 1

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 正常处理模式
    try:
        # 收集输入
        raw_input = None
        if args.input:
            raw_input = args.input
        elif args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except Exception as e:
                print(json.dumps({
                    "success": False,
                    "error_code": "E006",
                    "message": f"文件读取失败: {str(e)}",
                }, ensure_ascii=False))
                return 1
        else:
            # 无输入时，尝试从标准输入读取
            if not sys.stdin.isatty():
                raw_input = sys.stdin.read().strip()
            else:
                print(json.dumps({
                    "success": False,
                    "error_code": "E001",
                    "message": ERROR_CODES["E001"],
                }, ensure_ascii=False))
                return 1

        # 处理输入
        result = process_input(raw_input)
        output = format_output(result, args.format)
        print(output)

        return 0 if result.success else 1

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error_code": "E006",
            "message": f"处理异常: {str(e)}",
        }, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
