#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catacomb - 未命名工具（仅供学习与参考用途）

一个极简命令行工具，用于将用户提供的数据/文件/URL 转换为结构化结果。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法:
    python scripts/main.py <输入内容> [--format json|text] [--batch]
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
VERSION = "1.0.0"
DISCLAIMER = (
    "⚠️ 本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。\n"
    "涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，"
    "并由使用者自行承担决策后果。"
)

# 错误码对应话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：catacomb \"需要处理的内容\"",
    "E004": "这超出了本工具的能力范围，建议：简化输入或使用专业工具",
    "E005": "结果无法确定，建议：提供更多上下文信息后重试",
    "E006": "内部处理错误，请检查输入内容",
    "E007": "输出格式参数无效，仅支持 json 或 text",
    "E008": "批量模式要求输入为 JSON 数组格式",
    "E009": "文件读取失败，请检查文件路径和权限",
    "E010": "URL 解析失败（本工具不访问网络，仅做格式校验）",
}

# 置信度阈值
CONFIDENCE_HIGH = 90    # ≥90% 直接输出
CONFIDENCE_MEDIUM = 85  # 85%-90% 标注"建议复核"
# <85% 标注"[需核实]"

# 关键信息字段（用于结构化提取）
KEY_FIELDS = ["标题", "作者", "日期", "类别", "摘要", "关键词"]

# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------


def validate_input(raw_input: str) -> Optional[str]:
    """
    校验输入内容是否有效。

    参数:
        raw_input: 用户输入的原始字符串

    返回:
        有效时返回 None，无效时返回错误码
    """
    if raw_input is None or raw_input.strip() == "":
        return "E001"
    if len(raw_input.strip()) < 3:
        return "E003"
    return None


def is_url(text: str) -> bool:
    """判断输入是否为 URL 格式（仅格式校验，不访问网络）。"""
    text = text.strip()
    return text.startswith(("http://", "https://", "ftp://"))


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息。

    参数:
        text: 输入文本

    返回:
        包含关键字段的字典
    """
    # 简单分词统计
    words = text.replace("\n", " ").split()
    word_count = len(words)
    char_count = len(text)

    # 识别可能的标题（第一行或第一个句号前的内容）
    first_line = text.strip().split("\n")[0][:50] if text.strip() else ""
    title = first_line if first_line else "未命名内容"

    # 简单关键词提取（基于词频）
    freq: Dict[str, int] = {}
    for word in words:
        clean_word = word.strip("，。！？、；：,.!?;:()（）\"'")
        if len(clean_word) >= 2:
            freq[clean_word] = freq.get(clean_word, 0) + 1
    keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
    keyword_list = [k for k, _ in keywords]

    # 检测日期（简单正则）
    import re
    date_match = re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?", text)
    date_str = date_match.group(0) if date_match else "未识别"

    return {
        "标题": title,
        "作者": "未识别",
        "日期": date_str,
        "类别": "通用",
        "摘要": text[:100] + ("..." if len(text) > 100 else ""),
        "关键词": keyword_list,
        "_统计": {"词数": word_count, "字符数": char_count},
    }


def calculate_confidence(info: Dict[str, Any]) -> int:
    """
    计算置信度（0-100）。

    参数:
        info: 提取的信息字典

    返回:
        置信度整数
    """
    score = 50  # 基础分

    # 信息完整度加分
    filled = sum(1 for k in KEY_FIELDS if info.get(k) and info.get(k) != "未识别")
    score += filled * 8

    # 内容充实度加分
    if info.get("_统计", {}).get("词数", 0) >= 10:
        score += 10
    if info.get("_统计", {}).get("字符数", 0) >= 50:
        score += 5

    # 关键词丰富度
    if len(info.get("关键词", [])) >= 3:
        score += 5

    # 日期识别成功加分
    if info.get("日期") != "未识别":
        score += 5

    return min(score, 98)  # 上限 98，留出不确定性


def format_output(
    info: Dict[str, Any], confidence: int, output_format: str = "json"
) -> str:
    """
    按指定格式生成输出。

    参数:
        info: 信息字典
        confidence: 置信度
        output_format: 输出格式（json/text）

    返回:
        格式化后的字符串

    异常:
        ValueError: 如果输出格式无效
    """
    # 验证输出格式
    if output_format not in ["json", "text"]:
        raise ValueError(f"E007: {ERROR_MESSAGES['E007']}")

    # 确定置信度标注
    if confidence >= CONFIDENCE_HIGH:
        flag = "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        flag = "建议复核"
    else:
        flag = "[需核实]"

    result = dict(info)
    result["置信度"] = confidence
    result["置信度标注"] = flag

    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        lines = [f"标题: {info.get('标题', '')}"]
        lines.append(f"作者: {info.get('作者', '未识别')}")
        lines.append(f"日期: {info.get('日期', '未识别')}")
        lines.append(f"类别: {info.get('类别', '通用')}")
        lines.append(f"摘要: {info.get('摘要', '')}")
        lines.append(f"关键词: {', '.join(info.get('关键词', []))}")
        lines.append(f"置信度: {confidence}% ({flag})")
        return "\n".join(lines)


def process_single(input_text: str, output_format: str = "json") -> str:
    """
    处理单个输入。

    参数:
        input_text: 输入文本
        output_format: 输出格式

    返回:
        处理结果字符串

    异常:
        ValueError: 如果输入或输出格式无效
    """
    # 校验输入
    error_code = validate_input(input_text)
    if error_code:
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")

    # 校验输出格式
    if output_format not in ["json", "text"]:
        raise ValueError(f"E007: {ERROR_MESSAGES['E007']}")

    # URL 校验（不访问网络）
    if is_url(input_text):
        # 仅做格式校验，不实际访问
        if not input_text.startswith(("http://", "https://")):
            raise ValueError(f"E010: {ERROR_MESSAGES['E010']}")

    # 提取关键信息
    info = extract_key_info(input_text)

    # 计算置信度
    confidence = calculate_confidence(info)

    # 生成输出
    return format_output(info, confidence, output_format)


def process_batch(input_text: str, output_format: str = "json") -> str:
    """
    批量处理多个输入。

    参数:
        input_text: JSON 数组格式的输入
        output_format: 输出格式

    返回:
        处理结果字符串

    异常:
        ValueError: 如果输入不是有效的 JSON 数组
    """
    try:
        items = json.loads(input_text)
        if not isinstance(items, list):
            raise ValueError(f"E008: {ERROR_MESSAGES['E008']}")
    except json.JSONDecodeError:
        raise ValueError(f"E008: {ERROR_MESSAGES['E008']}")

    results = []
    for item in items:
        try:
            result = process_single(str(item), output_format)
            results.append({"输入": str(item), "结果": result})
        except ValueError as e:
            results.append({"输入": str(item), "错误": str(e)})

    return json.dumps(results, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------


def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。

    返回:
        True 表示全部通过
    """
    print("=" * 60)
    print(f"catacomb 自检程序 v{VERSION}")
    print("=" * 60)

    # 测试样例（硬编码，不读外部文件）
    test_cases = [
        {
            "name": "基本输入测试",
            "input": "深度学习是机器学习的一个分支，它使用多层神经网络进行特征学习。"
                     "本篇文章介绍深度学习在图像识别中的应用。",
            "format": "json",
        },
        {
            "name": "短输入测试",
            "input": "你好世界",
            "format": "text",
        },
        {
            "name": "URL 格式测试",
            "input": "https://example.com/article/12345",
            "format": "json",
        },
    ]

    # 错误处理测试
    error_cases = [
        {"input": "", "expected_error": "E001"},
        {"input": "ab", "expected_error": "E003"},
    ]

    all_passed = True

    # 测试正常处理
    print("\n[1] 正常处理测试")
    for i, case in enumerate(test_cases, 1):
        try:
            result = process_single(case["input"], case["format"])
            # 宽松断言：结果非空，包含关键内容
            assert len(result) > 0, "结果不能为空"
            assert "置信度" in result or "置信度:" in result, "必须包含置信度"
            print(f"  ✓ 测试 {i} ({case['name']}) 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 测试 {i} ({case['name']}) 失败: {e}")

    # 测试错误处理
    print("\n[2] 错误处理测试")
    for i, case in enumerate(error_cases, 1):
        try:
            process_single(case["input"])
            all_passed = False
            print(f"  ✗ 错误测试 {i} 未触发预期错误")
        except ValueError as e:
            error_code = str(e).split(":")[0]
            if error_code == case["expected_error"]:
                print(f"  ✓ 错误测试 {i} 通过（{error_code}）")
            else:
                all_passed = False
                print(f"  ✗ 错误测试 {i} 错误码不符: 期望 {case['expected_error']}, 实际 {error_code}")

    # 测试置信度计算
    print("\n[3] 置信度计算测试")
    info1 = extract_key_info("这是一段测试文本，用于验证置信度计算逻辑是否正确。")
    conf1 = calculate_confidence(info1)
    assert 0 <= conf1 <= 100, "置信度必须在 0-100 之间"
    print(f"  ✓ 置信度范围测试通过（当前值: {conf1}）")

    # 测试批量处理
    print("\n[4] 批量处理测试")
    batch_input = json.dumps(["第一条测试数据", "第二条测试数据"])
    try:
        batch_result = process_batch(batch_input)
        assert len(batch_result) > 0, "批量结果不能为空"
        print("  ✓ 批量处理测试通过")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 批量处理测试失败: {e}")

    # 测试非法批量输入
    try:
        process_batch("不是JSON格式")
        all_passed = False
        print("  ✗ 非法批量输入测试未触发错误")
    except ValueError:
        print("  ✓ 非法批量输入测试通过")

    # 测试输出格式
    print("\n[5] 输出格式测试")
    sample = "测试文本内容，包含足够的字数来验证格式输出功能。"
    for fmt in ["json", "text"]:
        try:
            result = process_single(sample, fmt)
            assert len(result) > 0, f"{fmt} 格式输出不能为空"
            print(f"  ✓ {fmt} 格式输出测试通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ {fmt} 格式输出测试失败: {e}")

    # 测试非法格式参数
    try:
        process_single(sample, "invalid_format")
        all_passed = False
        print("  ✗ 非法格式参数测试未触发错误")
    except ValueError as e:
        if "E007" in str(e):
            print("  ✓ 非法格式参数测试通过")
        else:
            all_passed = False
            print(f"  ✗ 非法格式参数测试错误码不符: {e}")

    # 汇总结果
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有自检测试通过")
    else:
        print("❌ 存在自检失败项")
    print("=" * 60)

    return all_passed


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="catacomb - 未命名工具（仅供学习与参考用途）",
        epilog=DISCLAIMER,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的内容（数据/文本/URL）",
    )
    parser.add_argument(
        "--format",
        default="json",
        help="输出格式（默认: json，可选: json/text）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为 JSON 数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"catacomb v{VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        if sys.stdin.isatty():
            # 交互模式：提示用户输入
            print("请输入待处理的内容（Ctrl+D 结束）：")
            try:
                input_lines = sys.stdin.read().strip()
            except KeyboardInterrupt:
                print("\n用户取消操作")
                return 1
        else:
            # 管道模式：从 stdin 读取
            input_lines = sys.stdin.read().strip()

        if not input_lines:
            print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
            return 1
    else:
        input_lines = args.input

    try:
        if args.batch:
            result = process_batch(input_lines, args.format)
        else:
            result = process_single(input_lines, args.format)
        print(result)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E006: {ERROR_MESSAGES['E006']} - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
