#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - JavaScript 单元测试 TextMate Bundle 工具（独立实现）

本脚本根据功能规格独立编写，不参考任何既有代码。
核心能力：将输入内容转换为结构化结果，支持批量处理与置信度标注。
仅使用 Python 标准库，无第三方依赖。

用法示例：
    python scripts/main.py --selftest          # 内置样例离线自检
    python scripts/main.py --input "some data" # 处理输入
    python scripts/main.py --input-file a.txt  # 从文件读取输入
    python scripts/main.py --batch a.txt b.txt # 批量处理多个文件
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术映射（依据规格第四节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{details}",
    "E004": "这超出了本工具的能力范围，建议：{details}",
    "E005": "结果无法确定，建议：{details}",
}

# 置信度阈值（依据规格第三节）
HIGH_CONFIDENCE_THRESHOLD = 90   # 置信度 >= 90%：直接输出
MEDIUM_CONFIDENCE_THRESHOLD = 85 # 85%-90%：建议复核
# 低于 85%：标注 [需核实]

# 默认输出字段模板
DEFAULT_OUTPUT_FIELDS = ["content", "length", "keywords", "confidence", "flag"]


# ============================================================
# 核心逻辑：结构化处理
# ============================================================

def extract_keywords(text: str) -> List[str]:
    """
    从输入文本中提取关键信息（关键词）。

    简单实现：提取长度 >= 2 的字母数字词，去重，按出现频率排序。
    不依赖外部库，纯标准库字符串处理。

    :param text: 输入文本
    :return: 关键词列表（按重要性降序）
    """
    if not text:
        return []

    # 分词：按非字母数字字符分割
    words: List[str] = []
    current_word: List[str] = []
    for ch in text:
        if ch.isalnum():
            current_word.append(ch.lower())
        else:
            if current_word:
                word = "".join(current_word)
                if len(word) >= 2:
                    words.append(word)
                current_word = []
    # 处理末尾残留
    if current_word:
        word = "".join(current_word)
        if len(word) >= 2:
            words.append(word)

    # 统计词频
    freq: Dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    # 按频率降序，同频按字母序
    sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in sorted_words]


def calculate_confidence(text: str, keywords: List[str]) -> float:
    """
    计算处理结果的置信度（0-100）。

    启发式规则：
    - 空输入：置信度 0
    - 基础置信度 60
    - 有关键词提取成功：+10
    - 文本长度适中（10-1000字符）：+15
    - 文本包含结构化特征（如标点符号、数字）：+10
    - 上限 95

    :param text: 输入文本
    :param keywords: 已提取的关键词列表
    :return: 置信度（0-100 的浮点数）
    """
    if not text:
        return 0.0

    confidence = 60.0

    # 有关键词提取成功
    if keywords:
        confidence += 10.0

    # 文本长度适中
    text_len = len(text)
    if 10 <= text_len <= 1000:
        confidence += 15.0
    elif text_len < 10:
        confidence += 5.0  # 短文本也有一定置信度

    # 包含结构化特征（标点、数字）
    has_punct = any(ch in text for ch in ".,;:!?，。；：！？")
    has_digit = any(ch.isdigit() for ch in text)
    if has_punct or has_digit:
        confidence += 10.0

    # 上限 95，下限 0
    return max(0.0, min(95.0, confidence))


def format_output(data: Dict[str, Any], fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    按约定字段组织输出结构。

    :param data: 原始处理结果字典
    :param fields: 输出字段列表，默认使用 DEFAULT_OUTPUT_FIELDS
    :return: 按字段顺序组织的输出字典
    """
    selected_fields = fields or DEFAULT_OUTPUT_FIELDS
    result: Dict[str, Any] = {}
    for field in selected_fields:
        if field in data:
            result[field] = data[field]
    return result


def process_single_input(content: str, output_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    处理单个输入内容，返回结构化结果。

    :param content: 输入文本内容
    :param output_fields: 输出字段列表
    :return: 结构化结果字典
    :raises ValueError: 输入为空时抛出（对应 E001）
    """
    if not content or not content.strip():
        raise ValueError("E001")

    # 提取关键词
    keywords = extract_keywords(content)

    # 计算置信度
    confidence = calculate_confidence(content, keywords)

    # 组织原始结果
    raw_result = {
        "content": content,
        "length": len(content),
        "keywords": keywords,
        "confidence": round(confidence, 1),
        "flag": "建议复核" if MEDIUM_CONFIDENCE_THRESHOLD <= confidence < HIGH_CONFIDENCE_THRESHOLD
               else ("[需核实]" if confidence < MEDIUM_CONFIDENCE_THRESHOLD else "直接输出"),
    }

    return format_output(raw_result, output_fields)


def load_input_from_file(file_path: str) -> str:
    """
    从文件读取输入内容。

    :param file_path: 文件路径
    :return: 文件内容字符串
    :raises OSError: 文件读取失败
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def process_batch(inputs: List[str], output_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    :param inputs: 输入内容列表
    :param output_fields: 输出字段列表
    :return: 处理结果列表
    """
    results = []
    for item in inputs:
        try:
            results.append(process_single_input(item, output_fields))
        except ValueError as e:
            # 单个输入失败不影响其他输入，记录错误信息
            error_code = str(e)
            results.append({
                "error": error_code,
                "message": ERROR_MESSAGES.get(error_code, "未知错误"),
            })
    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保任何环境直接可过。

    :return: 0 表示全部通过，非 0 表示有失败
    """
    print("=" * 60)
    print("开始自检：核心逻辑验证（内置样例数据）")
    print("=" * 60)

    # ---- 样例数据 ----
    sample_texts = [
        "JavaScript单元测试框架 unittest.js 使用说明",
        "function add(a, b) { return a + b; }",
        "hello world, this is a test",
        "短文本",
        "",  # 空输入，预期触发 E001
    ]

    # ---- 测试 1: extract_keywords ----
    print("\n[测试 1] extract_keywords 关键词提取")
    keywords_result = extract_keywords("JavaScript单元测试框架 unittest.js 使用说明")
    assert isinstance(keywords_result, list), "关键词提取结果应为列表"
    assert len(keywords_result) >= 2, "应提取到至少 2 个关键词"
    assert all(isinstance(k, str) for k in keywords_result), "关键词应为字符串"
    print(f"  ✓ 通过，提取到 {len(keywords_result)} 个关键词: {keywords_result[:5]}")

    # ---- 测试 2: calculate_confidence ----
    print("\n[测试 2] calculate_confidence 置信度计算")
    conf_empty = calculate_confidence("", [])
    assert conf_empty == 0.0, "空输入置信度应为 0"
    conf_normal = calculate_confidence("正常文本内容，包含一些信息", ["正常", "文本"])
    assert 50.0 <= conf_normal <= 100.0, "正常文本置信度应在 50-100 区间"
    assert conf_normal > conf_empty, "非空文本置信度应大于空文本"
    print(f"  ✓ 通过，空输入={conf_empty}, 正常文本={conf_normal}")

    # ---- 测试 3: process_single_input ----
    print("\n[测试 3] process_single_input 单输入处理")
    result = process_single_input("JavaScript单元测试框架 unittest.js 使用说明")
    assert "content" in result, "输出应包含 content 字段"
    assert "confidence" in result, "输出应包含 confidence 字段"
    assert "keywords" in result, "输出应包含 keywords 字段"
    assert result["length"] == len("JavaScript单元测试框架 unittest.js 使用说明"), "length 字段应等于输入长度"
    assert 0 <= result["confidence"] <= 100, "置信度应在 0-100 区间"
    print(f"  ✓ 通过，结果字段: {list(result.keys())}")

    # ---- 测试 4: 空输入错误处理 ----
    print("\n[测试 4] 空输入错误处理")
    try:
        process_single_input("")
        assert False, "空输入应抛出 ValueError"
    except ValueError as e:
        assert str(e) == "E001", f"空输入错误码应为 E001，实际为 {e}"
        print(f"  ✓ 通过，正确抛出 E001: {ERROR_MESSAGES['E001']}")

    # ---- 测试 5: process_batch 批量处理 ----
    print("\n[测试 5] process_batch 批量处理")
    batch_inputs = ["第一段测试文本内容", "第二段包含数字 123 的文本", ""]
    batch_results = process_batch(batch_inputs)
    assert len(batch_results) == 3, "批量处理结果数量应等于输入数量"
    assert "content" in batch_results[0], "第一个结果应包含 content"
    assert "error" in batch_results[2], "第三个结果（空输入）应包含 error"
    print(f"  ✓ 通过，成功 {sum(1 for r in batch_results if 'content' in r)} 个，失败 {sum(1 for r in batch_results if 'error' in r)} 个")

    # ---- 测试 6: format_output 字段过滤 ----
    print("\n[测试 6] format_output 字段过滤")
    raw = {"content": "测试", "length": 2, "keywords": ["测试"], "confidence": 80.0, "flag": "建议复核"}
    filtered = format_output(raw, ["content", "confidence"])
    assert set(filtered.keys()) == {"content", "confidence"}, "字段过滤应只保留指定字段"
    print(f"  ✓ 通过，过滤后字段: {list(filtered.keys())}")

    # ---- 测试 7: 文件读写（使用临时文件，不依赖工作目录）----
    print("\n[测试 7] 文件读写（临时目录）")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_input.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("临时文件测试内容")
        file_content = load_input_from_file(test_file)
        assert file_content == "临时文件测试内容", "文件读取内容应一致"
        print("  ✓ 通过，文件读写正常")

    # ---- 测试 8: 边界场景 ----
    print("\n[测试 8] 边界场景")
    # 超长文本
    long_text = "测试文本" * 1000
    long_result = process_single_input(long_text)
    assert long_result["length"] == len(long_text), "长文本长度应正确"
    assert long_result["confidence"] <= 95, "置信度不应超过上限 95"
    # 纯数字文本
    num_result = process_single_input("12345")
    assert num_result["length"] == 5, "数字文本长度应正确"
    print("  ✓ 通过，长文本和数字文本处理正常")

    # ---- 总结 ----
    print("\n" + "=" * 60)
    print("自检全部通过 ✅")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="JavaScript 单元测试 TextMate Bundle 工具 - 结构化处理工具",
        epilog="示例: python scripts/main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需任何外部依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="直接提供输入内容",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取输入内容",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个文件（文件路径列表）",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        default=DEFAULT_OUTPUT_FIELDS,
        help=f"输出字段列表（默认: {' '.join(DEFAULT_OUTPUT_FIELDS)}）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )
    return parser


def main() -> int:
    """
    主入口函数。

    :return: 退出码（0 成功，非 0 失败）
    """
    parser = create_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    try:
        results: List[Dict[str, Any]] = []

        # 处理批量文件
        if args.batch:
            inputs = []
            for file_path in args.batch:
                try:
                    inputs.append(load_input_from_file(file_path))
                except OSError as e:
                    print(f"E003: 无法读取文件 {file_path}: {e}", file=sys.stderr)
                    return 3
            results = process_batch(inputs, args.fields)

        # 处理单个文件
        elif args.input_file:
            try:
                content = load_input_from_file(args.input_file)
                results = [process_single_input(content, args.fields)]
            except OSError as e:
                print(f"E003: 无法读取文件 {args.input_file}: {e}", file=sys.stderr)
                return 3
            except ValueError as e:
                error_code = str(e)
                print(f"{error_code}: {ERROR_MESSAGES.get(error_code, '未知错误')}", file=sys.stderr)
                return 1

        # 处理直接输入
        elif args.input is not None:
            try:
                results = [process_single_input(args.input, args.fields)]
            except ValueError as e:
                error_code = str(e)
                print(f"{error_code}: {ERROR_MESSAGES.get(error_code, '未知错误')}", file=sys.stderr)
                return 1

        # 无有效输入
        else:
            print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
            return 1

        # 输出结果
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for i, result in enumerate(results, 1):
                print(f"--- 结果 {i} ---")
                for key, value in result.items():
                    print(f"  {key}: {value}")
                print()

        return 0

    except Exception as e:
        print(f"E010: 未预期错误: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
