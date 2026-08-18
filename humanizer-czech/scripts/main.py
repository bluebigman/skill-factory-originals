#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
humanizer-czech — 文本去AI味 规则化改写（捷克语适配）

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

# 默认单次处理上限（字符数），可通过 --max-chars 参数覆盖
DEFAULT_MAX_CHARS = 5000

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


def _validate_input(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> Tuple[int, str]:
    """校验输入文本，返回 (错误码, 错误信息) 或 (ERR_OK, "")"""
    if not isinstance(text, str):
        return ERR_INPUT_NOT_STRING, f"{ERR_INPUT_NOT_STRING}: 输入必须是字符串类型"
    if not text.strip():
        return ERR_INPUT_EMPTY, f"{ERR_INPUT_EMPTY}: 输入文本为空"
    if len(text) > max_chars:
        return ERR_INPUT_TOO_LONG, f"{ERR_INPUT_TOO_LONG}: 输入超过{max_chars}字符上限"
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
    """核心改写逻辑：去AI味，规则化润色"""
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


def _split_into_chunks(text: str, max_chars: int) -> List[str]:
    """按句子边界将长文本分块，每块不超过 max_chars 字符"""
    if len(text) <= max_chars:
        return [text]

    # 按句子边界（。！？）分割
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # 如果单个句子就超过限制，按字符硬切
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # 硬切长句子
            for i in range(0, len(sentence), max_chars):
                chunks.append(sentence[i:i+max_chars])
        elif len(current_chunk) + len(sentence) + 1 <= max_chars:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def humanize(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> Tuple[int, str]:
    """
    对外主函数：将输入文本进行去AI味改写。
    返回 (错误码, 结果文本或错误信息)
    """
    # 校验输入
    err_code, err_msg = _validate_input(text, max_chars)
    if err_code != ERR_OK:
        return err_code, err_msg

    try:
        # 按空行分段处理（支持多段）
        paragraphs = re.split(r"\n\s*\n", text)
        processed_paragraphs = []

        for para in paragraphs:
            if not para.strip():
                processed_paragraphs.append("")
                continue

            # 对每个段落，如果超长则分块处理
            chunks = _split_into_chunks(para, max_chars)
            processed_chunks = []
            for chunk in chunks:
                if chunk.strip():
                    processed_chunks.append(_humanize_text(chunk))
                else:
                    processed_chunks.append("")

            # 合并分块结果（用空格连接，保持语义连贯）
            processed_paragraphs.append(" ".join(processed_chunks))

        result = "\n\n".join(processed_paragraphs)
        return ERR_OK, result
    except Exception as e:
        return ERR_INTERNAL, f"{ERR_INTERNAL}: 处理失败: {str(e)}"


def _selftest() -> int:
    """离线自检：构造覆盖所有模式的样例，验证核心改写逻辑"""
    print("开始自检...")

    # 构造覆盖所有 MECHANICAL_PATTERNS 的样例
    mechanical_sample = (
        "Je důležité poznamenat, že tento produkt je dobrý. "
        "Je třeba zdůraznit, že kvalita je vysoká. "
        "V neposlední řadě je cena přijatelná. "
        "Celkově vzato je to dobrá volba. "
        "Je zřejmé, že spokojenost roste. "
        "Na základě výše uvedeného doporučuji nákup. "
        "Lze konstatovat, že služba je spolehlivá. "
        "Je nutné podotknout, že podpora je rychlá. "
        "V současné době je to nejlepší řešení. "
        "Je to velmi důležité rozhodnutí."
    )
    code_m, result_m = humanize(mechanical_sample)
    assert code_m == ERR_OK, f"机械表达测试失败: 错误码 {code_m}"
    
    # 验证所有机械表达都被替换
    mechanical_replacements = [
        "stojí za zmínku, že",
        "rozhodně platí, že",
        "a také",
        "zkrátka",
        "jak vidno",
        "z toho plyne",
        "dá se říct, že",
        "je dobré dodat, že",
        "momentálně",
        "podstatné",
    ]
    for replacement in mechanical_replacements:
        assert replacement in result_m, f"机械表达替换失败: 缺少 '{replacement}' 在: {result_m}"
    
    # 验证原机械表达已移除
    mechanical_originals = [
        "je důležité poznamenat",
        "je třeba zdůraznit",
        "v neposlední řadě",
        "celkově vzato",
        "je zřejmé",
        "na základě výše uvedeného",
        "lze konstatovat",
        "je nutné podotknout",
        "v současné době",
        "velmi důležité",
    ]
    for original in mechanical_originals:
        assert original.lower() not in result_m.lower(), f"机械表达未移除: '{original}' 仍在: {result_m}"
    
    print(f"  机械表达测试通过: {result_m[:100]}...")

    # 构造覆盖所有 AI_CONNECTORS 的样例
    connector_sample = (
        "Mám rád kávu, nicméně čaj je také dobrý. "
        "Avšak někdy dávám přednost vodě. "
        "Protože je to zdravější. "
        "Tudíž se cítím lépe. "
        "Proto doporučuji pít více vody."
    )
    code_c, result_c = humanize(connector_sample)
    assert code_c == ERR_OK, f"连接词测试失败: 错误码 {code_c}"
    
    # 验证所有连接词都被替换
    connector_replacements = ["ale", "neboť", "takže", "a tak"]
    for replacement in connector_replacements:
        assert replacement in result_c, f"连接词替换失败: 缺少 '{replacement}' 在: {result_c}"
    
    # 验证原连接词已移除
    connector_originals = ["nicméně", "avšak", "protože", "tudíž", "proto"]
    for original in connector_originals:
        assert original.lower() not in result_c.lower(), f"连接词未移除: '{original}' 仍在: {result_c}"
    
    print(f"  连接词测试通过: {result_c[:100]}...")

    # 构造覆盖所有 REDUNDANT_WORDS 的样例
    redundant_sample = (
        "Toto je velmi dobrý nápad. "
        "Opravdu to funguje. "
        "Skutečně to stojí za to. "
        "Jednoduše to uděláme. "
        "Rozhodně to zkusíme. "
        "Naprosto souhlasím. "
        "Zcela to chápu. "
        "Výrazně se to zlepšilo. "
        "Značně to pomohlo. "
        "Poměrně to stačí."
    )
    code_r, result_r = humanize(redundant_sample)
    assert code_r == ERR_OK, f"冗余词测试失败: 错误码 {code_r}"
    
    # 验证所有冗余词都被删除
    for word in REDUNDANT_WORDS:
        assert word.lower() not in result_r.lower(), f"冗余词未删除: '{word}' 仍在: {result_r}"
    
    print(f"  冗余词测试通过: {result_r[:100]}...")

    # 测试分块处理（超长文本）
    long_text = "Toto je testovací věta. " * 200  # 约 5000+ 字符
    code_l, result_l = humanize(long_text, max_chars=1000)  # 用小限制测试分块
    assert code_l == ERR_OK, f"分块测试失败: 错误码 {code_l}"
    assert len(result_l) > 0, "分块测试失败: 结果为空"
    assert "testovací" in result_l, "分块测试失败: 内容丢失"
    print(f"  分块测试通过: 输入{len(long_text)}字符 -> 输出{len(result_l)}字符")

    # 测试错误处理 - 空输入
    code_e1, _ = humanize("")
    assert code_e1 == ERR_INPUT_EMPTY, f"空输入测试失败: 应返回 {ERR_INPUT_EMPTY}"
    print(f"  空输入测试通过: 错误码 {code_e1}")

    # 测试错误处理 - 超长输入（超过配置限制）
    code_e2, _ = humanize("a" * 6000, max_chars=5000)
    assert code_e2 == ERR_INPUT_TOO_LONG, f"超长输入测试失败: 应返回 {ERR_INPUT_TOO_LONG}"
    print(f"  超长输入测试通过: 错误码 {code_e2}")

    # 测试错误处理 - 非字符串输入
    code_e3, _ = humanize(12345)  # type: ignore
    assert code_e3 == ERR_INPUT_NOT_STRING, f"非字符串测试失败: 应返回 {ERR_INPUT_NOT_STRING}"
    print(f"  非字符串测试通过: 错误码 {code_e3}")

    # 测试信息保留（核心事实不丢失）
    info_sample = "V roce 2023 bylo prodáno 1500 kusů za cenu 299 Kč."
    code_i, result_i = humanize(info_sample)
    assert code_i == ERR_OK, f"信息保留测试失败: 错误码 {code_i}"
    assert "2023" in result_i, f"信息保留测试失败: 年份丢失: {result_i}"
    assert "1500" in result_i, f"信息保留测试失败: 数字丢失: {result_i}"
    assert "299" in result_i, f"信息保留测试失败: 价格丢失: {result_i}"
    print(f"  信息保留测试通过: {result_i}")

    # 测试标点处理
    punct_sample = "Toto je věta bez koncového interpunkčního znaménka"
    code_p, result_p = humanize(punct_sample)
    assert code_p == ERR_OK, f"标点测试失败: 错误码 {code_p}"
    assert result_p.endswith("."), f"标点测试失败: 未添加句号: {result_p}"
    print(f"  标点测试通过: {result_p}")

    print("全部自检通过！")
    return ERR_OK


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="文本去AI味规则化改写（捷克语适配）",
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
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"单次处理最大字符数（默认: {DEFAULT_MAX_CHARS}，超长文本将自动分块）"
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
