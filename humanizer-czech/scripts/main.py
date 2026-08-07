#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
humanizer-czech — 文本去AI味 自然化改写（捷克语适配）

独立实现脚本，仅依据功能规格编写。
支持命令行调用与 --selftest 离线自检。
"""

import argparse
import re
import sys
from typing import List, Tuple

# 错误码定义
ERR_OK = 0
ERR_INPUT_EMPTY = "E001"
ERR_INPUT_TOO_LONG = "E002"
ERR_INPUT_NOT_STRING = "E003"
ERR_OUTPUT_FAILED = "E004"
ERR_INTERNAL = "E005"
ERR_SELFTEST_FAILED = "E006"
ERR_UNKNOWN_ARG = "E007"
ERR_FILE_READ = "E008"
ERR_FILE_WRITE = "E009"
ERR_INVALID_CONFIG = "E010"

# 单次处理上限（字符数）
MAX_CHARS = 5000

# 捷克语常见机械表达模式（用于去AI味）
MECHANICAL_PATTERNS = [
    (re.compile(r"\bje důležité poznamenat, že\b", re.IGNORECASE), "stojí za zmínku, že"),
    (re.compile(r"\bje třeba zdůraznit, že\b", re.IGNORECASE), "rozhodně platí, že"),
    (re.compile(r"\bv neposlední řadě\b", re.IGNORECASE), "a také"),
    (re.compile(r"\bcelkově vzato\b", re.IGNORECASE), "zkrátka"),
    (re.compile(r"\bje zřejmé, že\b", re.IGNORECASE), "jak vidno"),
    (re.compile(r"\bna základě výše uvedeného\b", re.IGNORECASE), "z toho plyne"),
    (re.compile(r"\blze konstatovat, že\b", re.IGNORECASE), "dá se říct, že"),
    (re.compile(r"\bje nutné podotknout, že\b", re.IGNORECASE), "je dobré dodat, že"),
    (re.compile(r"\bv současné době\b", re.IGNORECASE), "momentálně"),
    (re.compile(r"\bvelmi důležité\b", re.IGNORECASE), "podstatné"),
]

# 捷克语常见AI风格冗余词（可安全删除）
REDUNDANT_WORDS = [
    "velmi", "opravdu", "skutečně", "jednoduše", "rozhodně",
    "naprosto", "zcela", "výrazně", "značně", "poměrně",
]

# 捷克语常见AI式连接词（可替换为更自然的表达）
AI_CONNECTORS = [
    (re.compile(r"\bnicméně\b", re.IGNORECASE), "ale"),
    (re.compile(r"\bavšak\b", re.IGNORECASE), "ale"),
    (re.compile(r"\bprotože\b", re.IGNORECASE), "neboť"),
    (re.compile(r"\btudíž\b", re.IGNORECASE), "takže"),
    (re.compile(r"\bproto\b", re.IGNORECASE), "a tak"),
]


def _validate_input(text: str) -> Tuple[int, str]:
    """校验输入文本，返回 (错误码, 错误信息) 或 (ERR_OK, "")"""
    if not isinstance(text, str):
        return ERR_INPUT_NOT_STRING, f"{ERR_INPUT_NOT_STRING}: 输入必须是字符串类型"
    if not text.strip():
        return ERR_INPUT_EMPTY, f"{ERR_INPUT_EMPTY}: 输入文本为空"
    if len(text) > MAX_CHARS:
        return ERR_INPUT_TOO_LONG, f"{ERR_INPUT_TOO_LONG}: 输入超过{MAX_CHARS}字符上限"
    return ERR_OK, ""


def _apply_patterns(text: str, patterns: List[Tuple[re.Pattern, str]]) -> str:
    """应用正则替换模式"""
    result = text
    for pattern, replacement in patterns:
        result = pattern.sub(replacement, result)
    return result


def _remove_redundant_words(text: str) -> str:
    """删除冗余修饰词（保留上下文语义）"""
    words = text.split()
    filtered = []
    for word in words:
        # 去除标点符号后检查是否冗余词
        clean = re.sub(r"[^a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]", "", word)
        if clean.lower() in REDUNDANT_WORDS:
            # 保留可能的标点（如句号、逗号）
            punct = re.sub(r"[a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]", "", word)
            if punct:
                filtered.append(punct)
            continue
        filtered.append(word)
    return " ".join(filtered)


def _humanize_text(text: str) -> str:
    """核心改写逻辑：去AI味，自然化"""
    result = text

    # 1. 替换机械表达
    result = _apply_patterns(result, MECHANICAL_PATTERNS)

    # 2. 替换AI式连接词
    result = _apply_patterns(result, AI_CONNECTORS)

    # 3. 删除冗余修饰词
    result = _remove_redundant_words(result)

    # 4. 清理多余空格和标点前空格
    result = re.sub(r"\s+", " ", result)
    result = re.sub(r"\s+([,.;:!?])", r"\1", result)

    # 5. 确保句子以句号结尾（若原文本有结尾标点则保留）
    if result and not re.search(r"[.!?]$", result.strip()):
        result = result.strip() + "."

    return result.strip()


def humanize(text: str) -> Tuple[int, str]:
    """
    对外主函数：将输入文本进行去AI味改写。
    返回 (错误码, 结果文本或错误信息)
    """
    # 校验输入
    err_code, err_msg = _validate_input(text)
    if err_code != ERR_OK:
        return err_code, err_msg

    try:
        # 按空行分段处理（支持多段）
        paragraphs = re.split(r"\n\s*\n", text)
        processed = []
        for para in paragraphs:
            if para.strip():
                processed.append(_humanize_text(para))
            else:
                processed.append("")

        result = "\n\n".join(processed)
        return ERR_OK, result
    except Exception as e:
        return ERR_INTERNAL, f"{ERR_INTERNAL}: 处理失败: {str(e)}"


def _selftest() -> int:
    """离线自检：使用内置硬编码样例验证核心逻辑"""
    print("开始自检...")

    # 测试用例1：机械表达替换
    sample1 = "Je důležité poznamenat, že tento produkt je velmi dobrý."
    code1, result1 = humanize(sample1)
    assert code1 == ERR_OK, f"测试1失败: 错误码 {code1}"
    assert "stojí za zmínku" in result1, f"测试1失败: 未替换机械表达: {result1}"
    assert "velmi" not in result1, f"测试1失败: 未删除冗余词: {result1}"
    print(f"  测试1通过: {result1}")

    # 测试用例2：AI式连接词替换
    sample2 = "Mám rád kávu, nicméně čaj je také dobrý."
    code2, result2 = humanize(sample2)
    assert code2 == ERR_OK, f"测试2失败: 错误码 {code2}"
    assert "ale" in result2, f"测试2失败: 未替换连接词: {result2}"
    assert "nicméně" not in result2, f"测试2失败: 连接词未移除: {result2}"
    print(f"  测试2通过: {result2}")

    # 测试用例3：多段文本处理
    sample3 = "První odstavec.\n\nDruhý odstavec s velmi dlouhým textem."
    code3, result3 = humanize(sample3)
    assert code3 == ERR_OK, f"测试3失败: 错误码 {code3}"
    assert "\n\n" in result3, f"测试3失败: 段落分隔丢失: {result3}"
    assert len(result3.split("\n\n")) == 2, f"测试3失败: 段落数量不对: {result3}"
    print(f"  测试3通过: 段落数={len(result3.split(chr(10)+chr(10)))}")

    # 测试用例4：错误处理 - 空输入
    code4, _ = humanize("")
    assert code4 == ERR_INPUT_EMPTY, f"测试4失败: 空输入应返回 {ERR_INPUT_EMPTY}"
    print(f"  测试4通过: 空输入错误码 {code4}")

    # 测试用例5：错误处理 - 超长输入
    long_text = "a" * (MAX_CHARS + 1)
    code5, _ = humanize(long_text)
    assert code5 == ERR_INPUT_TOO_LONG, f"测试5失败: 超长输入应返回 {ERR_INPUT_TOO_LONG}"
    print(f"  测试5通过: 超长输入错误码 {code5}")

    # 测试用例6：非字符串输入
    code6, _ = humanize(12345)  # type: ignore
    assert code6 == ERR_INPUT_NOT_STRING, f"测试6失败: 非字符串应返回 {ERR_INPUT_NOT_STRING}"
    print(f"  测试6通过: 非字符串错误码 {code6}")

    # 测试用例7：信息保留（核心事实不丢失）
    sample7 = "V roce 2023 bylo prodáno 1500 kusů za cenu 299 Kč."
    code7, result7 = humanize(sample7)
    assert code7 == ERR_OK, f"测试7失败: 错误码 {code7}"
    assert "2023" in result7, f"测试7失败: 年份丢失: {result7}"
    assert "1500" in result7, f"测试7失败: 数字丢失: {result7}"
    assert "299" in result7, f"测试7失败: 价格丢失: {result7}"
    print(f"  测试7通过: 信息保留: {result7}")

    # 测试用例8：标点处理
    sample8 = "Toto je věta bez koncového interpunkčního znaménka"
    code8, result8 = humanize(sample8)
    assert code8 == ERR_OK, f"测试8失败: 错误码 {code8}"
    assert result8.endswith("."), f"测试8失败: 未添加句号: {result8}"
    print(f"  测试8通过: 标点处理: {result8}")

    print("全部自检通过！")
    return ERR_OK


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="文本去AI味自然化改写（捷克语适配）",
        epilog="示例: python main.py --text 'Je důležité poznamenat, že tento text je velmi umělý.'"
    )
    parser.add_argument(
        "--text", "-t",
        type=str,
        help="待改写的文本（直接传入）"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取文本（UTF-8编码）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="将结果写入文件（UTF-8编码）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件、不访问网络）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            result = _selftest()
            return result
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 获取输入
    if args.text:
        input_text = args.text
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception as e:
            print(f"{ERR_FILE_READ}: 读取文件失败: {e}", file=sys.stderr)
            return 1
    else:
        # 从标准输入读取
        print("请输入要改写的文本（Ctrl+D结束）:")
        input_text = sys.stdin.read()

    # 执行改写
    code, result = humanize(input_text)
    if code != ERR_OK:
        print(f"错误: {result}", file=sys.stderr)
        return 1

    # 输出结果
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"结果已写入: {args.output}")
        except Exception as e:
            print(f"{ERR_FILE_WRITE}: 写入文件失败: {e}", file=sys.stderr)
            return 1
    else:
        print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
