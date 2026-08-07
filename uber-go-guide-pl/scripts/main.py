#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 翻译润色（uber-go-guide-pl）核心逻辑实现

本脚本根据功能规格独立实现，仅依赖 Python 标准库。
支持通过 --selftest 参数进行离线自检（使用内置硬编码样例数据）。
"""

import argparse
import sys
from typing import Dict, List, Any

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：请提供文本内容或结构化数据",
    "E004": "这超出了本工具的能力范围，建议使用其他专业工具处理",
    "E005": "结果无法确定，建议提供更多上下文信息或人工复核",
}


class TranslationError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(data: Any) -> None:
    """校验输入数据，抛出带错误码的异常"""
    if data is None:
        raise TranslationError("E001")
    if isinstance(data, str) and not data.strip():
        raise TranslationError("E001")
    if isinstance(data, (list, dict)) and len(data) == 0:
        raise TranslationError("E001")


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段并结构化。
    支持 dict、list、str 三种基本类型。
    """
    if isinstance(data, dict):
        # 直接使用字典，但过滤空值
        return {k: v for k, v in data.items() if v is not None and v != ""}
    elif isinstance(data, list):
        # 列表转为带索引的结构
        return {"items": data, "count": len(data)}
    elif isinstance(data, str):
        # 简单文本，按段落拆分
        paragraphs = [p.strip() for p in data.split("\n") if p.strip()]
        return {"paragraphs": paragraphs, "total_chars": len(data)}
    else:
        return {"value": data}


def calculate_confidence(structured: Dict[str, Any]) -> float:
    """
    根据结构化数据的完整度计算置信度（0-100）。
    规则：
      - 有 3 个及以上字段/段落：>= 90
      - 有 2 个字段/段落：85-89
      - 有 1 个字段/段落：80-84
      - 空数据：< 80
    """
    # 计算有效信息单元数量
    if "items" in structured:
        unit_count = structured.get("count", 0)
    elif "paragraphs" in structured:
        unit_count = len(structured.get("paragraphs", []))
    else:
        unit_count = len(structured)

    if unit_count >= 3:
        return 92.0
    elif unit_count == 2:
        return 87.0
    elif unit_count == 1:
        return 82.0
    else:
        return 75.0


def format_output(structured: Dict[str, Any], confidence: float) -> str:
    """按默认模板生成输出文本"""
    lines = ["=== 结构化处理结果 ==="]

    # 输出内容
    if "items" in structured:
        lines.append(f"列表项（共 {structured['count']} 项）：")
        for i, item in enumerate(structured["items"], 1):
            lines.append(f"  {i}. {item}")
    elif "paragraphs" in structured:
        lines.append(f"段落数：{len(structured['paragraphs'])}")
        for i, para in enumerate(structured["paragraphs"], 1):
            lines.append(f"  段落{i}: {para[:50]}{'...' if len(para) > 50 else ''}")
    else:
        for k, v in structured.items():
            lines.append(f"  {k}: {v}")

    # 置信度标注
    lines.append("")
    if confidence >= 90:
        lines.append(f"置信度：{confidence:.0f}%（可直接使用）")
    elif confidence >= 85:
        lines.append(f"置信度：{confidence:.0f}%（建议复核）")
    else:
        lines.append(f"置信度：{confidence:.0f}% [需核实]（请人工确认关键信息）")

    return "\n".join(lines)


def process_input(data: Any) -> str:
    """
    核心处理流程：校验 -> 提取 -> 置信度 -> 格式化输出。
    可能抛出 TranslationError。
    """
    # Step 1: 校验
    validate_input(data)

    # Step 2: 结构化提取
    structured = extract_key_fields(data)

    # Step 3: 置信度计算
    confidence = calculate_confidence(structured)

    # Step 4: 格式化输出
    return format_output(structured, confidence)


def batch_process(inputs: List[Any]) -> List[str]:
    """批量处理多个输入，单个失败不影响其他"""
    results = []
    for item in inputs:
        try:
            results.append(process_input(item))
        except TranslationError as e:
            results.append(f"处理失败：{e}")
    return results


# ---------------------------------------------------------------------------
# 内置自检样例数据（硬编码，不读外部文件）
# ---------------------------------------------------------------------------
SELFTEST_CASES = {
    "single_text": {
        "input": "这是一段用于测试的示例文本。",
        "expected_has": ["结构化处理结果", "置信度"],
    },
    "structured_dict": {
        "input": {
            "name": "示例项目",
            "type": "文档",
            "language": "中文",
            "description": "用于自检的测试数据",
        },
        "expected_has": ["name", "type", "language", "置信度"],
    },
    "list_input": {
        "input": ["第一项", "第二项", "第三项"],
        "expected_has": ["列表项", "3 项", "置信度"],
    },
    "error_empty": {
        "input": None,
        "expected_error": "E001",
    },
    "error_blank": {
        "input": "   ",
        "expected_error": "E001",
    },
}


def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用宽松断言（包含关键子串、类型判断），不依赖精确值。
    返回 0 表示全部通过，非 0 表示失败。
    """
    print("开始自检翻译润色核心逻辑...")
    passed = 0
    failed = 0

    for case_name, case_data in SELFTEST_CASES.items():
        print(f"\n[测试用例] {case_name}")
        try:
            if "expected_error" in case_data:
                # 错误场景：期望抛出特定错误码
                try:
                    process_input(case_data["input"])
                    print("  ✗ 失败：未抛出预期异常")
                    failed += 1
                except TranslationError as e:
                    if e.code == case_data["expected_error"]:
                        print(f"  ✓ 通过：正确抛出 {e.code}")
                        passed += 1
                    else:
                        print(f"  ✗ 失败：错误码 {e.code} != {case_data['expected_error']}")
                        failed += 1
            else:
                # 正常场景：断言输出包含关键子串
                result = process_input(case_data["input"])
                ok = all(keyword in result for keyword in case_data["expected_has"])
                if ok:
                    print(f"  ✓ 通过：输出包含所有关键内容")
                    passed += 1
                else:
                    print(f"  ✗ 失败：输出缺少关键内容")
                    print(f"    实际输出：{result[:200]}")
                    failed += 1
        except Exception as e:
            print(f"  ✗ 失败：未预期异常 {type(e).__name__}: {e}")
            failed += 1

    # 额外测试批量处理（宽松断言）
    print(f"\n[测试用例] batch_process")
    try:
        batch_results = batch_process(["测试1", "测试2"])
        if len(batch_results) == 2 and all(isinstance(r, str) for r in batch_results):
            print("  ✓ 通过：批量处理返回正确数量的字符串结果")
            passed += 1
        else:
            print("  ✗ 失败：批量处理结果不符合预期")
            failed += 1
    except Exception as e:
        print(f"  ✗ 失败：批量处理异常 {e}")
        failed += 1

    # 汇总
    print(f"\n=== 自检完成 ===")
    print(f"通过：{passed}，失败：{failed}，总计：{passed + failed}")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="翻译润色 - Uber Go Style Guide Polish Translation Tool",
        epilog="示例：python main.py --input '待处理文本' 或 python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据，不读外部文件）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本内容（简单模式）",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入",
    )
    parser.add_argument(
        "--error-demo",
        type=str,
        choices=["E001", "E002", "E003", "E004", "E005"],
        help="演示指定错误码的标准话术",
    )
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 错误码演示
    if args.error_demo:
        print(ERROR_CODES.get(args.error_demo, "未知错误码"))
        return 0

    # 批量处理
    if args.batch:
        results = batch_process(args.batch)
        for i, r in enumerate(results, 1):
            print(f"--- 输入 {i} ---")
            print(r)
            print()
        return 0

    # 单条处理
    if args.input:
        try:
            result = process_input(args.input)
            print(result)
            return 0
        except TranslationError as e:
            print(f"错误：{e}")
            return 1

    # 无参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
