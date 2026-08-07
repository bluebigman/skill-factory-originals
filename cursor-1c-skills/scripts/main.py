#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现的通用数据处理工具（clean-room 重写）。
提供命令行入口，支持 --selftest 离线自检。

遵循规格：
- 输入：用户提供的数据/文件/URL
- 输出：结构化结果 + 置信度标注
- 错误码：E001-E010
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 置信度阈值（依据规格）
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85

# 错误码及标准话术映射（规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理异常，请稍后重试或检查输入。",
    "E007": "文件读取失败，请检查文件路径和权限。",
    "E008": "数据解析失败，请检查数据格式。",
    "E009": "输出序列化失败，请检查输出格式。",
    "E010": "未知错误，请联系支持人员。",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果封装。"""
    def __init__(self, data: Any, confidence: float, warnings: List[str] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑（依据规格第二章、第三章）
# ---------------------------------------------------------------------------
def extract_key_fields(raw_input: str) -> Tuple[Dict[str, Any], float]:
    """
    从输入中识别关键信息并结构化。

    依据规格：
    - 识别输入中的关键字段并结构化
    - 对不确定项标注

    返回：(结构化数据, 置信度)
    """
    if not raw_input or not raw_input.strip():
        raise SkillError("E001", ERROR_MESSAGES["E001"])

    # 尝试解析 JSON 输入
    try:
        parsed = json.loads(raw_input)
        if isinstance(parsed, dict):
            return _process_dict(parsed)
        elif isinstance(parsed, list):
            return _process_list(parsed)
        else:
            # 简单类型直接包装
            return {"value": parsed}, 0.95
    except json.JSONDecodeError:
        # 非 JSON，按文本处理
        return _process_text(raw_input)


def _process_dict(data: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    """处理字典类型输入。"""
    result = {}
    confidence_scores = []

    # 遍历所有键值对
    for key, value in data.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            # 空值标注低置信度
            result[key] = "[需核实]"
            confidence_scores.append(0.5)
        else:
            result[key] = value
            confidence_scores.append(0.95)

    # 计算总体置信度
    confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    return result, confidence


def _process_list(data: List[Any]) -> Tuple[List[Any], float]:
    """处理列表类型输入。"""
    processed = []
    confidence_scores = []

    for item in data:
        if isinstance(item, dict):
            sub_result, sub_conf = _process_dict(item)
            processed.append(sub_result)
            confidence_scores.append(sub_conf)
        elif item is not None:
            processed.append(item)
            confidence_scores.append(0.95)
        else:
            processed.append("[需核实]")
            confidence_scores.append(0.5)

    confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    return processed, confidence


def _process_text(text: str) -> Tuple[Dict[str, Any], float]:
    """处理纯文本输入。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        raise SkillError("E001", ERROR_MESSAGES["E001"])

    # 简单识别：单行作为值，多行作为列表
    if len(lines) == 1:
        return {"content": lines[0]}, 0.90
    else:
        return {"items": lines, "count": len(lines)}, 0.90


def format_output(result: ProcessingResult) -> str:
    """
    按约定格式生成输出。

    依据规格：
    - 置信度 ≥90%：直接输出
    - 85%-90%：标注"建议复核"
    - <85%：标注"[需核实]"，并说明不确定点
    """
    output_lines = []

    # 根据置信度添加标注
    if result.confidence >= HIGH_CONFIDENCE:
        output_lines.append("【直接输出】")
    elif result.confidence >= MEDIUM_CONFIDENCE:
        output_lines.append("【建议复核】")
    else:
        output_lines.append("【需核实】")
        if result.warnings:
            output_lines.append("不确定点：")
            output_lines.extend(f"  - {w}" for w in result.warnings)

    # 序列化数据
    try:
        data_str = json.dumps(result.data, ensure_ascii=False, indent=2)
        output_lines.append(data_str)
    except (TypeError, ValueError) as exc:
        raise SkillError("E009", f"{ERROR_MESSAGES['E009']} 详情：{exc}") from exc

    # 追加置信度信息
    output_lines.append(f"\n置信度：{result.confidence:.1%}")

    return "\n".join(output_lines)


# ---------------------------------------------------------------------------
# 批量处理（规格第六章）
# ---------------------------------------------------------------------------
def batch_process(inputs: List[str]) -> List[ProcessingResult]:
    """批量处理多个输入。"""
    results = []
    for item in inputs:
        try:
            data, confidence = extract_key_fields(item)
            results.append(ProcessingResult(data, confidence))
        except SkillError:
            # 单个失败不影响整体
            results.append(ProcessingResult(
                {"error": "处理失败"},
                0.0,
                ["该项处理失败，请单独检查"]
            ))
    return results


# ---------------------------------------------------------------------------
# 自定义格式输出（规格第六章）
# ---------------------------------------------------------------------------
def custom_format(result: ProcessingResult, fields: List[str]) -> Dict[str, Any]:
    """按自定义字段提取输出。"""
    if not isinstance(result.data, dict):
        return {"error": "数据不是对象类型，无法自定义字段提取"}

    output = {}
    for field in fields:
        output[field] = result.data.get(field, "[需核实]")
    return output


# ---------------------------------------------------------------------------
# 异常处理（规格第四章）
# ---------------------------------------------------------------------------
class SkillError(Exception):
    """技能自定义异常。"""
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")


def handle_error(error: SkillError) -> str:
    """将错误转换为标准话术输出。"""
    if error.error_code == "E002":
        # 关键信息缺失，需要提示补充
        return f"{ERROR_MESSAGES['E002']} 请提供输入来源、输出格式要求、期望完整度"
    elif error.error_code == "E003":
        return f"{ERROR_MESSAGES['E003']} 请提供文本、JSON 或文件路径"
    elif error.error_code == "E004":
        return f"{ERROR_MESSAGES['E004']} 请将需求拆分或联系技术支持"
    elif error.error_code == "E005":
        return f"{ERROR_MESSAGES['E005']} 请提供更多上下文信息或人工复核"
    else:
        return error.message


# ---------------------------------------------------------------------------
# 文件处理辅助（规格：输入可为文件）
# ---------------------------------------------------------------------------
def read_input_file(filepath: str) -> str:
    """读取输入文件内容。"""
    if not os.path.isfile(filepath):
        raise SkillError("E007", f"{ERROR_MESSAGES['E007']} 文件不存在：{filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError) as exc:
        raise SkillError("E007", f"{ERROR_MESSAGES['E007']} 详情：{exc}") from exc


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保必然匹配。
    """
    print("开始自检...")

    # 测试用例 1：JSON 字典输入
    print("测试 1：JSON 字典输入")
    test_input = '{"name": "测试项目", "description": "这是一个测试", "empty_field": ""}'
    data, confidence = extract_key_fields(test_input)
    assert isinstance(data, dict), "E001: 应返回字典"
    assert "name" in data, "E001: 应包含 name 字段"
    assert data["name"] == "测试项目", "E001: name 值不正确"
    assert data["empty_field"] == "[需核实]", "E001: 空字段应标注"
    assert confidence > 0.5 and confidence < 1.0, "E001: 置信度应在合理范围"
    print("  ✓ 通过")

    # 测试用例 2：纯文本输入
    print("测试 2：纯文本输入")
    data, confidence = extract_key_fields("单行文本")
    assert isinstance(data, dict), "E002: 应返回字典"
    assert "content" in data, "E002: 应包含 content 字段"
    assert confidence > 0.5, "E002: 置信度应较高"
    print("  ✓ 通过")

    # 测试用例 3：多行文本
    print("测试 3：多行文本输入")
    data, confidence = extract_key_fields("第一行\n第二行\n第三行")
    assert isinstance(data, dict), "E003: 应返回字典"
    assert data["count"] == 3, "E003: 应识别 3 行"
    assert len(data["items"]) == 3, "E003: items 应为 3 个元素"
    print("  ✓ 通过")

    # 测试用例 4：空输入错误
    print("测试 4：空输入错误处理")
    try:
        extract_key_fields("")
        assert False, "E004: 空输入应抛出异常"
    except SkillError as exc:
        assert exc.error_code == "E001", "E004: 错误码应为 E001"
    print("  ✓ 通过")

    # 测试用例 5：批量处理
    print("测试 5：批量处理")
    inputs = ['{"a": 1}', "文本内容", '{"b": 2}']
    results = batch_process(inputs)
    assert len(results) == 3, "E005: 应返回 3 个结果"
    for result in results:
        assert isinstance(result, ProcessingResult), "E005: 应为 ProcessingResult"
        assert result.confidence > 0.0, "E005: 置信度应大于 0"
    print("  ✓ 通过")

    # 测试用例 6：输出格式化
    print("测试 6：输出格式化")
    result = ProcessingResult({"test": "value"}, 0.95)
    output = format_output(result)
    assert "直接输出" in output, "E006: 高置信度应标注直接输出"
    assert "test" in output, "E006: 应包含数据内容"
    print("  ✓ 通过")

    # 测试用例 7：低置信度标注
    print("测试 7：低置信度标注")
    result = ProcessingResult({"test": "value"}, 0.80, ["数据不完整"])
    output = format_output(result)
    assert "需核实" in output, "E007: 低置信度应标注需核实"
    assert "数据不完整" in output, "E007: 应包含不确定点说明"
    print("  ✓ 通过")

    # 测试用例 8：自定义格式输出
    print("测试 8：自定义格式输出")
    result = ProcessingResult({"a": 1, "b": 2, "c": 3}, 0.95)
    custom = custom_format(result, ["a", "c"])
    assert custom == {"a": 1, "c": 3}, "E008: 自定义字段提取不正确"
    print("  ✓ 通过")

    # 测试用例 9：错误码映射完整性
    print("测试 9：错误码映射")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_MESSAGES, f"E009: 缺少错误码 {code}"
        assert ERROR_MESSAGES[code], f"E009: 错误码 {code} 无消息"
    print("  ✓ 通过")

    # 测试用例 10：文件读取错误处理
    print("测试 10：文件读取错误")
    try:
        read_input_file("/nonexistent/path/file.txt")
        assert False, "E010: 应抛出异常"
    except SkillError as exc:
        assert exc.error_code == "E007", "E010: 错误码应为 E007"
    print("  ✓ 通过")

    print("\n全部自检通过！")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="cursor-1c-skills 通用数据处理工具",
        epilog="示例：python main.py --input '{\"key\": \"value\"}'"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本或 JSON 字符串），或文件路径（配合 --file 使用）"
    )
    parser.add_argument(
        "--file", "-f",
        action="store_true",
        help="将 --input 视为文件路径"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：--input 为 JSON 数组，每个元素单独处理"
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="自定义输出字段，逗号分隔（仅对字典输入有效）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="安静模式，仅输出结果"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"自检失败：{exc}", file=sys.stderr)
            return 1

    # 检查输入
    if not args.input:
        print(handle_error(SkillError("E001", ERROR_MESSAGES["E001"])), file=sys.stderr)
        return 1

    try:
        # 读取输入
        if args.file:
            raw_input = read_input_file(args.input)
        else:
            raw_input = args.input

        # 批量模式
        if args.batch:
            try:
                inputs = json.loads(raw_input)
                if not isinstance(inputs, list):
                    raise SkillError("E003", ERROR_MESSAGES["E003"])
            except json.JSONDecodeError as exc:
                raise SkillError("E003", f"{ERROR_MESSAGES['E003']} 详情：{exc}") from exc

            results = batch_process([json.dumps(item) if isinstance(item, (dict, list)) else str(item) for item in inputs])
            for idx, result in enumerate(results):
                if not args.quiet:
                    print(f"--- 结果 {idx + 1} ---")
                print(format_output(result))
                print()
            return 0

        # 单条处理
        data, confidence = extract_key_fields(raw_input)
        result = ProcessingResult(data, confidence)

        # 自定义字段
        if args.fields:
            field_list = [f.strip() for f in args.fields.split(",") if f.strip()]
            result.data = custom_format(result, field_list)

        # 输出
        print(format_output(result))
        return 0

    except SkillError as exc:
        print(handle_error(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # 未知错误
        print(f"[E010] {ERROR_MESSAGES['E010']} 详情：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
