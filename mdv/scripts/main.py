#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mdv - 数据可视化技能核心处理脚本

本脚本依据功能规格独立实现（clean-room），仅使用标准库。
提供命令行接口，支持 --selftest 离线自检。

功能概述：
1. 解析用户输入的数据/文件/URL，识别关键信息并结构化
2. 按约定格式生成输出，标注置信度
3. 支持批量处理
4. 通过错误码体系报告异常

用法示例：
    python scripts/main.py --input "data1, data2, data3" --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术映射（依据规格"四、异常处理"）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
    # 内部补充错误码（规格未列出，但用于健壮性）
    "E006": "内部处理错误，请重试",
    "E007": "输出格式不支持，可选：text/json",
    "E008": "批量处理失败，请检查输入",
    "E009": "置信度计算异常",
    "E010": "参数解析错误",
}

# 默认输出字段结构
DEFAULT_FIELDS = ["content", "confidence", "flag"]

# 置信度阈值（依据规格"三、Step 2"）
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(raw_input: str) -> List[str]:
    """
    解析原始输入字符串，分割为独立的数据项。

    支持逗号、分号、换行作为分隔符。
    若输入为空，抛出 E001 错误。

    参数:
        raw_input: 用户提供的原始输入字符串

    返回:
        数据项列表

    异常:
        SystemExit: 若输入为空，以错误码 E001 退出
    """
    if not raw_input or not raw_input.strip():
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        sys.exit(1)

    # 统一分隔符：将分号和换行替换为逗号，然后按逗号分割
    normalized = raw_input.replace(";", ",").replace("\n", ",")
    items = [item.strip() for item in normalized.split(",")]
    # 过滤空字符串
    items = [item for item in items if item]

    if not items:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        sys.exit(1)

    return items


def analyze_item(item: str) -> Tuple[str, float, str]:
    """
    分析单个数据项，提取关键信息并计算置信度。

    规则：
    - 若包含 'http' 或 'www'，判定为 URL，置信度较高
    - 若包含文件扩展名（.csv, .json, .txt 等），判定为文件引用，置信度中等
    - 否则视为普通文本数据，置信度中等

    参数:
        item: 单个数据项字符串

    返回:
        (处理后的内容, 置信度, 标志)
        - 标志: 空字符串(正常) 或 "[需核实]"(低置信度)
    """
    content = item.strip()
    confidence = 0.0
    flag = ""

    # 识别 URL
    if "http://" in content or "https://" in content or "www." in content:
        # URL 类型，置信度较高
        confidence = 0.95
        # 提取域名作为关键信息（简化处理）
        flag = "url"

    # 识别文件路径
    elif any(ext in content.lower() for ext in [".csv", ".json", ".txt", ".md", ".html"]):
        # 文件引用，置信度中等偏高
        confidence = 0.88
        flag = "file"

    # 普通文本
    else:
        # 普通数据，置信度中等
        confidence = 0.85
        flag = "text"

    # 根据置信度设置标志
    if confidence < MEDIUM_CONFIDENCE:
        flag = f"[需核实] {flag}"
    elif confidence < HIGH_CONFIDENCE:
        flag = f"建议复核 {flag}"

    return content, confidence, flag


def process_batch(items: List[str]) -> List[Dict[str, Any]]:
    """
    批量处理数据项，生成结构化结果。

    参数:
        items: 数据项列表

    返回:
        结构化结果列表，每项包含 content/confidence/flag 字段
    """
    results = []
    for item in items:
        content, confidence, flag = analyze_item(item)
        results.append({
            "content": content,
            "confidence": confidence,
            "flag": flag,
        })
    return results


def format_output(results: List[Dict[str, Any]], output_format: str = "text") -> str:
    """
    按指定格式生成输出。

    参数:
        results: 结构化结果列表
        output_format: 输出格式，可选 "text" 或 "json"

    返回:
        格式化后的输出字符串

    异常:
        SystemExit: 若输出格式不支持，以错误码 E007 退出
    """
    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = []
        for i, res in enumerate(results, 1):
            conf_pct = int(res["confidence"] * 100)
            flag_str = f" ({res['flag']})" if res["flag"] else ""
            lines.append(f"{i}. {res['content']} — 置信度 {conf_pct}%{flag_str}")
        return "\n".join(lines)

    # 不支持的格式
    print(f"E007: {ERROR_MESSAGES['E007']}", file=sys.stderr)
    sys.exit(1)


def process_input(raw_input: str, output_format: str = "text") -> str:
    """
    处理用户输入的主流程。

    参数:
        raw_input: 原始输入字符串
        output_format: 输出格式

    返回:
        处理结果字符串
    """
    # Step 1: 解析输入
    items = parse_input(raw_input)

    # Step 2: 核心处理
    results = process_batch(items)

    # Step 3: 输出与校验
    return format_output(results, output_format)


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、
    不访问网络。任何环境直接可过。

    断言使用宽松阈值（大小比较/区间判断），避免精确值依赖。

    返回:
        0 表示全部通过，1 表示存在失败
    """
    print("开始自检...")

    # 测试用例 1: 解析输入（正常情况）
    test_input = "apple, banana; orange\nhttp://example.com, data.csv"
    items = parse_input(test_input)
    assert len(items) == 5, f"解析数量错误: {len(items)}"
    assert "apple" in items, "缺少 apple"
    assert "http://example.com" in items, "缺少 URL"
    print("  [通过] 输入解析")

    # 测试用例 2: 解析输入（空输入，应触发 E001）
    try:
        parse_input("")
        # 若未抛出异常，则失败
        assert False, "空输入未触发错误"
    except SystemExit as e:
        assert e.code == 1, f"错误退出码异常: {e.code}"
    print("  [通过] 空输入错误处理")

    # 测试用例 3: 单条分析 - URL 类型
    content, confidence, flag = analyze_item("https://example.com/page")
    assert "example.com" in content, "URL 内容处理异常"
    assert confidence > 0.9, "URL 置信度应大于 0.9"
    assert flag == "url", f"URL 标志异常: {flag}"
    print("  [通过] URL 分析")

    # 测试用例 4: 单条分析 - 文件类型
    content, confidence, flag = analyze_item("report.csv")
    assert "report.csv" in content, "文件内容处理异常"
    assert 0.8 < confidence < 0.95, "文件置信度应在 0.8-0.95 之间"
    assert "file" in flag, f"文件标志异常: {flag}"
    print("  [通过] 文件分析")

    # 测试用例 5: 单条分析 - 普通文本
    content, confidence, flag = analyze_item("hello world")
    assert "hello world" in content, "文本内容处理异常"
    assert 0.8 < confidence <= 0.9, "文本置信度应在 0.8-0.9 之间"
    assert "text" in flag, f"文本标志异常: {flag}"
    print("  [通过] 文本分析")

    # 测试用例 6: 批量处理
    test_items = ["data1", "http://example.com", "file.csv"]
    results = process_batch(test_items)
    assert len(results) == 3, f"批量结果数量错误: {len(results)}"
    for res in results:
        assert "content" in res, "缺少 content 字段"
        assert "confidence" in res, "缺少 confidence 字段"
        assert "flag" in res, "缺少 flag 字段"
        assert 0 <= res["confidence"] <= 1, "置信度超出范围"
    print("  [通过] 批量处理")

    # 测试用例 7: 格式输出 - JSON
    test_results = [{"content": "test", "confidence": 0.9, "flag": ""}]
    json_out = format_output(test_results, "json")
    parsed = json.loads(json_out)
    assert len(parsed) == 1, "JSON 输出解析异常"
    assert parsed[0]["content"] == "test", "JSON 内容异常"
    print("  [通过] JSON 输出")

    # 测试用例 8: 格式输出 - 文本
    text_out = format_output(test_results, "text")
    assert "test" in text_out, "文本输出缺少内容"
    assert "90%" in text_out, "文本输出缺少置信度"
    print("  [通过] 文本输出")

    # 测试用例 9: 完整流程
    full_output = process_input("hello, http://example.com", "text")
    assert "hello" in full_output, "完整流程输出异常"
    assert "example.com" in full_output, "完整流程缺少 URL"
    print("  [通过] 完整流程")

    # 测试用例 10: 批量输入处理
    batch_output = process_input("item1; item2\nitem3", "json")
    batch_data = json.loads(batch_output)
    assert len(batch_data) == 3, f"批量输入 JSON 数量错误: {len(batch_data)}"
    print("  [通过] 批量输入")

    print("所有自检通过！")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数。

    返回:
        退出码，0 表示成功，非 0 表示失败
    """
    parser = argparse.ArgumentParser(
        description="mdv - 数据可视化技能核心处理脚本",
        epilog="示例: python scripts/main.py --input 'data1, data2' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的数据内容（支持逗号/分号/换行分隔）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )

    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        args = parser.parse_args()
    except SystemExit as e:
        # 参数解析失败
        print(f"E010: {ERROR_MESSAGES['E010']}", file=sys.stderr)
        return e.code or 1

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        # 缺少必要输入
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    try:
        output = process_input(args.input, args.format)
        print(output)
        return 0
    except SystemExit as e:
        # 内部错误处理已打印错误信息
        return e.code or 1
    except Exception as e:
        # 未预期异常
        print(f"E006: {ERROR_MESSAGES['E006']} ({e})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
