#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
基于功能规格独立实现（clean-room）的 awesome-agent-conventions 技能脚本。

提供：
- 核心处理流程（解析输入 -> 结构化 -> 置信度标注 -> 输出）
- 错误码体系（E001-E010）
- 离线自检（--selftest），使用内置硬编码样例，不依赖外部资源。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码与标准化话术（依据功能规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 扩展错误码（E006-E010），用于更细粒度的内部错误处理
    "E006": "内部处理错误：无法解析输入内容。",
    "E007": "内部处理错误：输出格式化失败。",
    "E008": "内部处理错误：置信度计算异常。",
    "E009": "内部处理错误：未知的输入来源类型。",
    "E010": "内部处理错误：批量处理中断。",
}

# 置信度阈值（依据功能规格第三节 Step 2）
CONFIDENCE_HIGH = 0.90      # 直接输出
CONFIDENCE_MEDIUM = 0.85    # 建议复核

# 支持的输入来源类型（用于校验）
SUPPORTED_SOURCE_TYPES = ("data", "file", "url")

# 默认输出字段模板（依据功能规格第三节 Step 3）
DEFAULT_OUTPUT_FIELDS = ["content", "confidence", "warning"]


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------

def error_message(code: str) -> str:
    """根据错误码返回标准化话术。未知错误码返回通用提示。"""
    return ERROR_MESSAGES.get(code, f"未知错误码: {code}")


def validate_input(input_data: Optional[Any]) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效。
    返回 (是否有效, 错误码或None)。
    """
    if input_data is None:
        return False, "E001"
    if isinstance(input_data, str) and not input_data.strip():
        return False, "E001"
    if isinstance(input_data, (list, tuple, dict)) and len(input_data) == 0:
        return False, "E001"
    return True, None


def extract_key_info(input_data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键信息。
    支持字符串、字典、列表（批量）。
    返回结构化字典。
    """
    if isinstance(input_data, str):
        # 简单字符串：去除首尾空白
        return {"raw_text": input_data.strip(), "type": "string"}
    elif isinstance(input_data, dict):
        # 字典：直接保留，并标记类型
        return {"data": input_data, "type": "dict"}
    elif isinstance(input_data, list):
        # 列表：视为批量数据，逐项提取
        items = [extract_key_info(item) for item in input_data]
        return {"items": items, "type": "list", "count": len(items)}
    else:
        # 其他类型：转为字符串
        return {"raw_text": str(input_data), "type": "unknown"}


def calculate_confidence(structured_data: Dict[str, Any]) -> float:
    """
    基于结构化数据计算置信度。
    规则（宽松启发式）：
    - 字符串非空且长度>0：基础置信度 0.95
    - 字典包含键且值非空：0.92
    - 列表非空：0.90
    - 未知类型：0.80
    返回 0.0 ~ 1.0 之间的浮点数。
    """
    data_type = structured_data.get("type", "unknown")
    if data_type == "string":
        raw = structured_data.get("raw_text", "")
        return 0.95 if len(raw) > 0 else 0.80
    elif data_type == "dict":
        data = structured_data.get("data", {})
        non_empty_keys = sum(1 for v in data.values() if v is not None and v != "")
        total_keys = len(data)
        if total_keys == 0:
            return 0.80
        return 0.90 + 0.05 * (non_empty_keys / total_keys)
    elif data_type == "list":
        count = structured_data.get("count", 0)
        return 0.90 if count > 0 else 0.80
    else:
        return 0.80


def format_output(structured_data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    根据置信度生成最终输出字典（包含内容、置信度、警告信息）。
    """
    # 提取内容主体
    if structured_data.get("type") == "string":
        content = structured_data.get("raw_text", "")
    elif structured_data.get("type") == "dict":
        content = structured_data.get("data", {})
    elif structured_data.get("type") == "list":
        content = structured_data.get("items", [])
    else:
        content = structured_data.get("raw_text", "")

    # 生成警告信息
    warning = ""
    if confidence < CONFIDENCE_MEDIUM:
        warning = "[需核实] 置信度低于85%，请人工复核关键结果。"
    elif confidence < CONFIDENCE_HIGH:
        warning = "建议复核：置信度在85%-90%之间。"

    return {
        "content": content,
        "confidence": round(confidence, 4),
        "warning": warning,
    }


def process_single_input(input_data: Any) -> Dict[str, Any]:
    """
    处理单个输入项，返回结构化结果。
    这是核心流程的入口。
    """
    try:
        # Step 1: 校验输入
        valid, err_code = validate_input(input_data)
        if not valid:
            # 输入为空或无效，返回错误信息
            return {
                "success": False,
                "error_code": err_code,
                "error_message": error_message(err_code or "E001"),
            }

        # Step 2: 提取关键信息
        structured = extract_key_info(input_data)

        # Step 3: 计算置信度
        confidence = calculate_confidence(structured)

        # Step 4: 格式化输出
        output = format_output(structured, confidence)

        # 添加成功标志
        output["success"] = True
        return output
    except Exception as e:
        # 捕获所有异常，返回内部错误
        return {
            "success": False,
            "error_code": "E006",
            "error_message": f"{error_message('E006')} 详细信息: {str(e)}",
        }


def process_batch_input(input_list: List[Any]) -> Dict[str, Any]:
    """
    批量处理输入列表，逐项调用 process_single_input。
    返回汇总结果。
    """
    if not isinstance(input_list, list) or len(input_list) == 0:
        return {
            "success": False,
            "error_code": "E001",
            "error_message": error_message("E001"),
        }

    try:
        results = []
        for item in input_list:
            results.append(process_single_input(item))

        # 汇总统计（宽松统计，不依赖精确值）
        success_count = sum(1 for r in results if r.get("success"))
        total_count = len(results)

        return {
            "success": True,
            "batch_size": total_count,
            "processed": success_count,
            "results": results,
            "summary": f"批量处理完成：成功 {success_count}/{total_count} 项。",
        }
    except Exception as e:
        # 批量处理中断
        return {
            "success": False,
            "error_code": "E010",
            "error_message": f"{error_message('E010')} 详细信息: {str(e)}",
        }


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    返回 0 表示全部通过，非 0 表示失败。
    """
    print("开始离线自检...")

    try:
        # 样例 1：有效字符串输入
        sample_str = "这是一个测试输入，用于验证核心流程。"
        result = process_single_input(sample_str)
        assert result.get("success") is True, "字符串输入处理失败"
        assert "content" in result and "confidence" in result, "输出缺少必要字段"
        # 宽松阈值：置信度应大于 0.8（不依赖精确值）
        assert result["confidence"] > 0.8, f"置信度过低: {result['confidence']}"
        print("  [PASS] 字符串输入处理")

        # 样例 2：有效字典输入
        sample_dict = {"name": "test", "value": 123, "note": "some data"}
        result = process_single_input(sample_dict)
        assert result.get("success") is True, "字典输入处理失败"
        assert result["confidence"] > 0.8, f"字典置信度过低: {result['confidence']}"
        print("  [PASS] 字典输入处理")

        # 样例 3：空输入（应返回 E001）
        result = process_single_input(None)
        assert result.get("success") is False, "空输入应处理失败"
        assert result.get("error_code") == "E001", f"期望 E001，实际 {result.get('error_code')}"
        print("  [PASS] 空输入错误处理")

        # 样例 4：空字符串（应返回 E001）
        result = process_single_input("   ")
        assert result.get("success") is False, "空字符串应处理失败"
        assert result.get("error_code") == "E001", f"期望 E001，实际 {result.get('error_code')}"
        print("  [PASS] 空字符串错误处理")

        # 样例 5：批量处理
        batch = ["项目A", {"key": "value"}, "", None]
        result = process_batch_input(batch)
        assert result.get("success") is True, "批量处理失败"
        assert result.get("batch_size") == 4, f"批量大小错误: {result.get('batch_size')}"
        # 宽松断言：成功数应大于等于 2（因为前两项有效）
        assert result.get("processed") >= 2, f"批量成功数异常: {result.get('processed')}"
        print("  [PASS] 批量处理")

        # 样例 6：错误码映射完整性（检查 E001-E010 必须存在）
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
        print("  [PASS] 错误码映射完整性")

        # 样例 7：置信度边界（低置信度应产生警告）
        low_conf_input = {"a": "", "b": "", "c": ""}  # 所有值空
        result = process_single_input(low_conf_input)
        # 空值字典置信度应低于 0.85，产生警告
        assert result["confidence"] < 0.85, f"低置信度未生效: {result['confidence']}"
        assert result.get("warning", "") != "", "低置信度应产生警告信息"
        print("  [PASS] 低置信度警告")

        # 样例 8：中等置信度（部分值非空）
        medium_conf_input = {"a": "value", "b": "", "c": ""}  # 1/3 非空
        result = process_single_input(medium_conf_input)
        assert result["confidence"] >= 0.85, f"中等置信度异常: {result['confidence']}"
        assert result.get("warning", "") != "", "中等置信度应产生警告"
        print("  [PASS] 中等置信度警告")

        # 样例 9：高置信度（所有值非空）
        high_conf_input = {"a": "value1", "b": "value2", "c": "value3"}
        result = process_single_input(high_conf_input)
        assert result["confidence"] >= 0.90, f"高置信度异常: {result['confidence']}"
        assert result.get("warning", "") == "", "高置信度不应产生警告"
        print("  [PASS] 高置信度无警告")

        print("所有自检样例通过！")
        return 0
    except AssertionError as e:
        print(f"  [FAIL] {str(e)}")
        return 1
    except Exception as e:
        print(f"  [ERROR] 自检过程发生异常: {str(e)}")
        return 1


# ---------------------------------------------------------------------------
# 主程序入口
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """
    命令行入口。
    支持：
    - 无参数：打印帮助信息
    - --selftest：运行离线自检
    - --input <内容>：处理单个输入
    - --batch <内容1> <内容2> ...：批量处理
    """
    parser = argparse.ArgumentParser(
        description="awesome-agent-conventions 技能核心处理脚本",
        epilog="示例: python main.py --input '待处理内容'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="处理单个输入内容",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入内容",
    )
    parser.add_argument(
        "--source-type",
        type=str,
        choices=SUPPORTED_SOURCE_TYPES,
        default="data",
        help="输入来源类型（默认 data）",
    )

    args = parser.parse_args(argv)

    # 运行自检
    if args.selftest:
        return run_selftest()

    # 处理单个输入
    if args.input is not None:
        result = process_single_input(args.input)
        if result.get("success"):
            print(f"处理结果: {result['content']}")
            print(f"置信度: {result['confidence']:.2%}")
            if result.get("warning"):
                print(f"警告: {result['warning']}")
            return 0
        else:
            print(f"错误 [{result.get('error_code')}]: {result.get('error_message')}")
            return 1

    # 批量处理
    if args.batch is not None:
        # 将命令行参数转换为列表
        input_list = list(args.batch)
        result = process_batch_input(input_list)
        if result.get("success"):
            print(result.get("summary", "批量处理完成"))
            # 打印每个结果
            for i, item in enumerate(result.get("results", []), 1):
                status = "成功" if item.get("success") else f"失败({item.get('error_code')})"
                print(f"  [{i}] {status}")
            return 0
        else:
            print(f"错误 [{result.get('error_code')}]: {result.get('error_message')}")
            return 1

    # 无参数：打印帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
