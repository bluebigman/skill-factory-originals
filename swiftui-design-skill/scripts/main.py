#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — swiftui-design-skill 独立实现

本脚本依据功能规格全新编写，不复制任何既有代码。
提供核心处理逻辑（结构化解析、置信度评估、错误码体系）及离线自检。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90       # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85     # 85%-90% 建议复核
# <85% 标注 [需核实]

# 默认输出模板字段
DEFAULT_FIELDS = ["input_source", "key_info", "output_format", "confidence"]


# ============================================================
# 核心数据结构
# ============================================================
class ProcessResult:
    """处理结果数据类"""
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.data = data or {}
        self.error_code = error_code
        self.error_message = error_message


# ============================================================
# 核心处理逻辑
# ============================================================
def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效
    返回: (是否有效, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str) and not raw_input.strip():
        return False, "E001"
    if isinstance(raw_input, (list, dict)) and len(raw_input) == 0:
        return False, "E001"
    return True, None


def extract_key_info(input_data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键信息
    - 字符串: 直接作为内容
    - 字典: 提取关键字段
    - 列表: 提取元素数量及首个元素
    """
    key_info = {}

    if isinstance(input_data, str):
        key_info["type"] = "text"
        key_info["content"] = input_data.strip()
        key_info["length"] = len(input_data.strip())
    elif isinstance(input_data, dict):
        key_info["type"] = "structured"
        key_info["fields"] = list(input_data.keys())
        key_info["field_count"] = len(input_data)
        # 提取常见关键字段
        for field in ["title", "name", "url", "file_path", "data"]:
            if field in input_data:
                key_info[field] = input_data[field]
        # 如果有内容字段，也计算长度
        if "data" in input_data and isinstance(input_data["data"], str):
            key_info["content_length"] = len(input_data["data"])
    elif isinstance(input_data, list):
        key_info["type"] = "list"
        key_info["item_count"] = len(input_data)
        if input_data:
            first_item = input_data[0]
            if isinstance(first_item, (str, dict)):
                key_info["first_item"] = first_item
    else:
        key_info["type"] = type(input_data).__name__
        key_info["content"] = str(input_data)
        key_info["length"] = len(str(input_data))

    return key_info


def calculate_confidence(key_info: Dict[str, Any]) -> float:
    """
    计算置信度
    规则:
    - 有明确类型和内容: 高置信度
    - 仅部分信息: 中等置信度
    - 信息模糊: 低置信度
    """
    score = 0.0

    # 基础分：有类型
    if "type" in key_info:
        score += 0.3

    # 内容分
    if "content" in key_info and key_info.get("content"):
        score += 0.4
    elif "fields" in key_info and key_info.get("fields"):
        # 结构化数据，有字段就有内容
        score += 0.3
        # 字段越多，置信度越高
        field_count = key_info.get("field_count", 0)
        if field_count >= 3:
            score += 0.2
        elif field_count >= 2:
            score += 0.15
        elif field_count >= 1:
            score += 0.1
    elif "item_count" in key_info and key_info.get("item_count", 0) > 0:
        score += 0.3
        # 列表项越多，置信度越高
        if key_info["item_count"] >= 3:
            score += 0.2
        elif key_info["item_count"] >= 2:
            score += 0.15

    # 长度/复杂度分
    if "length" in key_info and key_info.get("length", 0) > 10:
        score += 0.2
    elif "content_length" in key_info and key_info.get("content_length", 0) > 10:
        score += 0.2
    elif "field_count" in key_info and key_info.get("field_count", 0) >= 2:
        score += 0.2

    # 确保在 0-1 范围内
    return min(1.0, max(0.0, score))


def format_output(result_data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    格式化输出结果
    根据置信度添加标注
    """
    output = {
        "result": result_data,
        "confidence": round(confidence, 2),
        "confidence_level": "",
        "warning": "",
    }

    if confidence >= CONFIDENCE_HIGH:
        output["confidence_level"] = "high"
        output["warning"] = ""
    elif confidence >= CONFIDENCE_MEDIUM:
        output["confidence_level"] = "medium"
        output["warning"] = "建议复核"
    else:
        output["confidence_level"] = "low"
        output["warning"] = "[需核实] 结果无法确定，请人工复核"

    return output


def process_input(raw_input: Any, output_format: str = "json") -> ProcessResult:
    """
    核心处理流程
    1. 校验输入
    2. 提取关键信息
    3. 计算置信度
    4. 格式化输出
    """
    # Step 1: 校验输入
    is_valid, error_code = validate_input(raw_input)
    if not is_valid:
        return ProcessResult(
            success=False,
            error_code=error_code,
            error_message=ERROR_CODES.get(error_code, "未知错误"),
        )

    # Step 2: 提取关键信息
    key_info = extract_key_info(raw_input)

    # 检查关键信息是否充分
    if not key_info:
        return ProcessResult(
            success=False,
            error_code="E002",
            error_message=ERROR_CODES["E002"] + "缺少可识别的关键信息",
        )

    # Step 3: 计算置信度
    confidence = calculate_confidence(key_info)

    # 低置信度处理
    if confidence < CONFIDENCE_MEDIUM:
        return ProcessResult(
            success=False,
            error_code="E005",
            error_message=ERROR_CODES["E005"],
            data={"partial_result": key_info, "confidence": confidence},
        )

    # Step 4: 格式化输出
    output = format_output(key_info, confidence)

    # 根据输出格式调整
    if output_format == "json":
        return ProcessResult(success=True, data=output)
    elif output_format == "text":
        text_output = _format_as_text(key_info, confidence)
        return ProcessResult(success=True, data={"text": text_output})
    else:
        return ProcessResult(
            success=False,
            error_code="E003",
            error_message=ERROR_CODES["E003"] + f"不支持的输出格式: {output_format}",
        )


def _format_as_text(key_info: Dict[str, Any], confidence: float) -> str:
    """将结果格式化为纯文本"""
    lines = ["=== 处理结果 ==="]
    for key, value in key_info.items():
        lines.append(f"{key}: {value}")
    lines.append(f"置信度: {confidence:.0%}")
    if confidence < CONFIDENCE_HIGH:
        lines.append("建议复核")
    return "\n".join(lines)


# ============================================================
# 批量处理
# ============================================================
def batch_process(inputs: List[Any], output_format: str = "json") -> ProcessResult:
    """
    批量处理多个输入
    每个输入独立处理，结果汇总
    """
    if not inputs:
        return ProcessResult(
            success=False,
            error_code="E001",
            error_message=ERROR_CODES["E001"],
        )

    results = []
    for idx, item in enumerate(inputs):
        result = process_input(item, output_format)
        results.append({
            "index": idx,
            "success": result.success,
            "data": result.data if result.success else {"error": result.error_message},
        })

    return ProcessResult(success=True, data={"batch_results": results, "count": len(results)})


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑
    使用内置硬编码样例数据，不依赖外部环境
    """
    print("=== 开始自检 ===")
    all_passed = True

    # 测试用例 1: 正常文本输入
    print("\n[测试1] 正常文本输入")
    result = process_input("这是一个测试文本，用于验证核心处理逻辑是否正常工作", "json")
    assert result.success, f"测试1失败: {result.error_message}"
    assert result.data["confidence"] >= 0.8, f"测试1置信度异常: {result.data['confidence']}"
    print(f"  通过, 置信度: {result.data['confidence']}")

    # 测试用例 2: 结构化字典输入
    print("\n[测试2] 结构化字典输入")
    test_dict = {"title": "项目文档", "url": "https://example.com/doc", "data": "内容"}
    result = process_input(test_dict, "json")
    assert result.success, f"测试2失败: {result.error_message}"
    assert result.data["result"]["field_count"] >= 2, "字段提取异常"
    print(f"  通过, 字段数: {result.data['result']['field_count']}")

    # 测试用例 3: 空输入应报 E001
    print("\n[测试3] 空输入处理")
    result = process_input("", "json")
    assert not result.success, "测试3失败: 空输入应失败"
    assert result.error_code == "E001", f"错误码异常: {result.error_code}"
    print(f"  通过, 错误码: {result.error_code}")

    # 测试用例 4: 列表批量输入
    print("\n[测试4] 列表输入")
    test_list = ["第一项", "第二项", "第三项"]
    result = process_input(test_list, "json")
    assert result.success, f"测试4失败: {result.error_message}"
    assert result.data["result"]["item_count"] == 3, "列表项数异常"
    print(f"  通过, 项数: {result.data['result']['item_count']}")

    # 测试用例 5: 批量处理
    print("\n[测试5] 批量处理")
    batch = ["文本一", {"name": "对象二"}, ["列表三"]]
    result = batch_process(batch, "json")
    assert result.success, f"测试5失败: {result.error_message}"
    assert result.data["count"] == 3, "批量数量异常"
    print(f"  通过, 处理数量: {result.data['count']}")

    # 测试用例 6: 纯数字输入
    print("\n[测试6] 数字输入")
    result = process_input(12345, "json")
    assert result.success, f"测试6失败: {result.error_message}"
    print(f"  通过, 类型: {result.data['result']['type']}")

    # 测试用例 7: 低置信度场景
    print("\n[测试7] 低置信度处理")
    result = process_input("?", "json")
    # 单个字符置信度低，可能返回 E005 或成功但低置信度
    if result.success:
        assert result.data["confidence"] < 0.85, "置信度应低于阈值"
        print(f"  通过, 置信度: {result.data['confidence']}")
    else:
        assert result.error_code in ["E002", "E005"], f"错误码异常: {result.error_code}"
        print(f"  通过, 错误码: {result.error_code}")

    # 测试用例 8: 文本格式输出
    print("\n[测试8] 文本格式输出")
    result = process_input("测试文本格式输出功能", "text")
    assert result.success, f"测试8失败: {result.error_message}"
    assert "text" in result.data, "缺少文本输出"
    print(f"  通过, 输出长度: {len(result.data['text'])}")

    # 测试用例 9: 非法输出格式
    print("\n[测试9] 非法格式处理")
    result = process_input("测试内容", "xml")
    assert not result.success, "测试9失败: 应拒绝非法格式"
    assert result.error_code == "E003", f"错误码异常: {result.error_code}"
    print(f"  通过, 错误码: {result.error_code}")

    # 测试用例 10: URL 输入
    print("\n[测试10] URL 输入")
    result = process_input("https://example.com/data", "json")
    assert result.success, f"测试10失败: {result.error_message}"
    print(f"  通过, 内容长度: {result.data['result']['length']}")

    # 总结
    print("\n=== 自检完成 ===")
    if all_passed:
        print("✅ 全部测试通过")
    else:
        print("❌ 存在失败测试")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="swiftui-design-skill — 数据处理工具",
        epilog="示例: python main.py --input '文本内容' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的数据（文本、JSON字符串或文件路径）",
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
        type=str,
        help="批量处理，JSON数组格式",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 批量处理模式
    if args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                print("错误: batch 参数必须是 JSON 数组")
                return 1
            result = batch_process(batch_data, args.format)
        except json.JSONDecodeError:
            print("错误: batch 参数不是有效的 JSON")
            return 1
    # 单条处理模式
    elif args.input:
        result = process_input(args.input, args.format)
    else:
        print("错误: 请提供 --input 或 --batch 参数，或使用 --selftest")
        parser.print_help()
        return 1

    # 输出结果
    if result.success:
        if args.format == "json":
            print(json.dumps(result.data, ensure_ascii=False, indent=2))
        else:
            print(result.data.get("text", ""))
        return 0
    else:
        # 错误输出
        error_output = {
            "error_code": result.error_code,
            "error_message": result.error_message,
        }
        if result.data:
            error_output["partial_data"] = result.data
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
