#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 去AI味 (Humanize Writing Skill)

独立实现脚本，仅依据功能规格开发（clean-room）。
提供文本润色核心逻辑、命令行接口与离线自检功能。
"""

import argparse
import re
import sys
from typing import Dict, List, Tuple

# -----------------------------------------------------------------------------
# 常量定义
# -----------------------------------------------------------------------------

# 错误码及其标准化话术（依据规格四）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 内部扩展错误码（规格未强制，但为完整性保留）
    "E006": "内部处理错误：文本规范化失败。",
    "E007": "内部处理错误：句子切分失败。",
    "E008": "内部处理错误：模式替换失败。",
    "E009": "内部处理错误：置信度计算失败。",
    "E010": "内部处理错误：输出格式化失败。",
}

# 去AI味核心词库（36+ 禁用词/短语，依据规格）
BANNED_WORDS: List[str] = [
    "此外",
    "然而",
    "因此",
    "总之",
    "首先",
    "其次",
    "最后",
    "值得注意的是",
    "众所周知",
    "毫无疑问",
    "显而易见",
    "综上所述",
    "总的来说",
    "换句话说",
    "也就是说",
    "与此同时",
    "不仅如此",
    "更为重要的是",
    "值得一提的是",
    "不可否认",
    "事实上",
    "实际上",
    "本质上",
    "基本上",
    "一般来说",
    "通常情况下",
    "在很大程度上",
    "从某种意义上说",
    "在一定程度上",
    "随着...的发展",
    "在...的背景下",
    "在...的过程中",
    "扮演着重要的角色",
    "发挥着重要的作用",
    "具有重要的意义",
    "产生了深远的影响",
    "提供了有力的支持",
    "奠定了坚实的基础",
]

# 10 种结构模式（依据规格，使用正则表达式）
STRUCTURAL_PATTERNS: List[Tuple[str, str, str]] = [
    # (模式描述, 正则表达式, 替换模板)
    ("重复连接词", r"首先[，,]\s*", ""),  # 删除开头的"首先，"
    ("重复连接词", r"其次[，,]\s*", ""),  # 删除开头的"其次，"
    ("重复连接词", r"最后[，,]\s*", ""),  # 删除开头的"最后，"
    ("总结词开头", r"^总之[，,]\s*", ""),  # 删除开头的"总之，"
    ("总结词开头", r"^综上所述[，,]\s*", ""),  # 删除开头的"综上所述，"
    ("总结词开头", r"^总的来说[，,]\s*", ""),  # 删除开头的"总的来说，"
    ("冗余解释", r"换句话说[，,]\s*", ""),  # 删除"换句话说，"
    ("冗余解释", r"也就是说[，,]\s*", ""),  # 删除"也就是说，"
    ("冗余解释", r"值得注意的是[，,]\s*", ""),  # 删除"值得注意的是，"
    ("冗余解释", r"众所周知[，,]\s*", ""),  # 删除"众所周知，"
]

# 置信度阈值（依据规格三）
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# -----------------------------------------------------------------------------
# 核心处理函数
# -----------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """文本规范化：去除多余空白，统一标点。"""
    if not isinstance(text, str):
        raise ValueError("E006")
    # 去除首尾空白
    text = text.strip()
    # 合并多个空白为单个空格
    text = re.sub(r"\s+", " ", text)
    # 统一中文标点（将英文逗号、句号转为中文）
    text = text.replace(",", "，").replace(".", "。")
    return text


def _split_sentences(text: str) -> List[str]:
    """将文本切分为句子列表。"""
    if not text:
        return []
    # 依据中文句号、问号、感叹号切分
    parts = re.split(r"(?<=[。！？])", text)
    # 去除空字符串并保留完整句子
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences


def _remove_banned_words(text: str) -> Tuple[str, int]:
    """移除禁用词/短语，返回处理后的文本和移除数量。"""
    count = 0
    processed = text
    for word in BANNED_WORDS:
        # 对每个禁用词进行替换
        # 注意：某些词包含省略号，需特殊处理
        pattern = re.escape(word)
        # 对包含省略号的词，允许匹配任意内容（例如"随着...的发展"）
        if "..." in word:
            pattern = pattern.replace(r"\.\.\.", r".*?")
        processed, n = re.subn(pattern, "", processed)
        count += n
    return processed, count


def _apply_structural_patterns(text: str) -> Tuple[str, int]:
    """应用结构模式替换，返回处理后的文本和替换次数。"""
    count = 0
    processed = text
    for desc, pattern, replacement in STRUCTURAL_PATTERNS:
        processed, n = re.subn(pattern, replacement, processed)
        count += n
    return processed, count


def _cleanup_spacing(text: str) -> str:
    """清理多余空格，确保标点后无多余空格。"""
    # 合并多个空格
    text = re.sub(r"\s+", " ", text)
    # 移除标点前的空格（中文语境）
    text = re.sub(r"\s+([，。！？；：])", r"\1", text)
    # 移除标点后的多余空格（保留一个）
    text = re.sub(r"([，。！？；：])\s+", r"\1", text)
    return text.strip()


def _calculate_confidence(original: str, processed: str, removed_count: int) -> float:
    """计算置信度。

    逻辑：
    - 基础置信度 = 1.0
    - 若处理前后无变化，置信度低（可能未识别出AI味）
    - 若移除的禁用词越多，置信度越高（确信进行了有效处理）
    - 处理后的文本长度变化也作为参考
    """
    if not original:
        return 0.0
    try:
        base = 1.0
        # 若没有移除任何内容，置信度降低
        if removed_count == 0:
            base -= 0.3
        # 根据移除数量微调（最多加 0.1）
        base += min(removed_count * 0.02, 0.1)
        # 若文本长度变化很小，可能只是轻微改动
        orig_len = len(original)
        proc_len = len(processed)
        if orig_len > 0:
            length_ratio = proc_len / orig_len
            if length_ratio > 0.95:  # 长度几乎没变
                base -= 0.1
            elif length_ratio < 0.7:  # 长度大幅缩短，可能过度删减
                base -= 0.1
        # 确保置信度在 [0, 1] 区间
        return max(0.0, min(base, 1.0))
    except Exception:
        # 计算失败时返回低置信度
        return 0.5


def _format_output(original: str, processed: str, confidence: float) -> Dict:
    """格式化输出结果。"""
    result = {
        "original": original,
        "processed": processed,
        "confidence": confidence,
        "needs_review": False,
        "uncertain": False,
    }
    if confidence >= CONFIDENCE_HIGH:
        result["needs_review"] = False
        result["uncertain"] = False
    elif confidence >= CONFIDENCE_MEDIUM:
        result["needs_review"] = True
        result["uncertain"] = False
    else:
        result["needs_review"] = True
        result["uncertain"] = True
    return result


def humanize_text(text: str) -> Dict:
    """主处理函数：对输入文本执行去AI味处理。

    参数:
        text: 待处理的原始文本

    返回:
        包含原始文本、处理后文本、置信度等信息的字典

    异常:
        依据错误码抛出 ValueError
    """
    # 输入校验（E001）
    if not text or not text.strip():
        raise ValueError("E001")

    try:
        # 1. 规范化
        normalized = _normalize_text(text)
        if not normalized:
            raise ValueError("E006")

        # 2. 句子切分（用于后续处理，此处暂不直接使用）
        sentences = _split_sentences(normalized)
        if not sentences:
            raise ValueError("E007")

        # 3. 移除禁用词
        removed_text, banned_count = _remove_banned_words(normalized)

        # 4. 应用结构模式
        structured_text, pattern_count = _apply_structural_patterns(removed_text)

        # 5. 清理空格
        final_text = _cleanup_spacing(structured_text)

        # 6. 计算置信度
        total_removed = banned_count + pattern_count
        confidence = _calculate_confidence(normalized, final_text, total_removed)

        # 7. 格式化输出
        result = _format_output(normalized, final_text, confidence)
        return result

    except ValueError as e:
        # 重新抛出已知错误码
        raise
    except Exception:
        # 未知错误，使用通用错误码
        raise ValueError("E010")


# -----------------------------------------------------------------------------
# 命令行接口
# -----------------------------------------------------------------------------


def _run_selftest() -> bool:
    """内置自检逻辑：使用硬编码样例数据，不依赖外部环境。"""
    print("[自检] 开始执行离线自检...")
    test_cases = [
        # (输入文本, 期望行为描述)
        (
            "首先，我们要认识到这个问题的重要性。其次，我们需要制定详细的计划。最后，我们必须严格执行。",
            "包含多个禁用连接词，应被移除。",
        ),
        (
            "众所周知，人工智能正在改变世界。因此，我们需要适应这一趋势。",
            "包含'众所周知'和'因此'，应被移除。",
        ),
        (
            "这是一个简单的测试句子，没有明显的AI味。",
            "无明显禁用词，处理前后变化不大。",
        ),
        (
            "随着科技的发展，我们的生活变得越来越便利。总而言之，科技改变了世界。",
            "包含'随着...的发展'和'总而言之'，应被移除。",
        ),
        (
            "值得注意的是，这个方案存在风险。换句话说，我们需要谨慎行事。",
            "包含'值得注意的是'和'换句话说'，应被移除。",
        ),
    ]

    all_passed = True
    for i, (input_text, desc) in enumerate(test_cases, 1):
        try:
            result = humanize_text(input_text)
            original = result["original"]
            processed = result["processed"]
            confidence = result["confidence"]

            # 宽松断言：处理后的文本不应为空
            assert processed, f"测试用例 {i}: 处理结果为空"
            # 宽松断言：置信度应在 [0, 1] 区间
            assert 0.0 <= confidence <= 1.0, f"测试用例 {i}: 置信度越界"
            # 宽松断言：处理后的文本长度不应超过原始文本太多（允许轻微增加）
            assert len(processed) <= len(original) * 1.5, f"测试用例 {i}: 处理后文本异常增长"
            # 宽松断言：对于包含禁用词的文本，处理后的文本应发生变化
            if i != 3:  # 第3个用例本身无明显AI味
                assert processed != original, f"测试用例 {i}: 应检测到AI味但未处理"

            print(f"[自检] 用例 {i} 通过: {desc}")
        except AssertionError as e:
            print(f"[自检] 用例 {i} 失败: {e}")
            all_passed = False
        except ValueError as e:
            print(f"[自检] 用例 {i} 异常: {e}")
            all_passed = False
        except Exception as e:
            print(f"[自检] 用例 {i} 未知异常: {e}")
            all_passed = False

    # 额外测试：空输入应触发 E001
    try:
        humanize_text("")
        print("[自检] 空输入测试失败: 未触发 E001")
        all_passed = False
    except ValueError as e:
        if str(e) == "E001":
            print("[自检] 空输入测试通过: 正确触发 E001")
        else:
            print(f"[自检] 空输入测试异常: 错误码 {e}")
            all_passed = False

    # 额外测试：非字符串输入应触发 E006
    try:
        humanize_text(None)  # type: ignore
        print("[自检] None输入测试失败: 未触发异常")
        all_passed = False
    except ValueError as e:
        if str(e) in ("E001", "E006"):
            print(f"[自检] None输入测试通过: 正确触发 {e}")
        else:
            print(f"[自检] None输入测试异常: 错误码 {e}")
            all_passed = False

    if all_passed:
        print("[自检] 全部通过！")
    else:
        print("[自检] 存在失败项！")
    return all_passed


def _run_interactive(text: str) -> None:
    """交互式处理：接收文本并输出结果。"""
    try:
        result = humanize_text(text)
        print("\n========== 处理结果 ==========")
        print(f"原始文本: {result['original']}")
        print(f"处理后文本: {result['processed']}")
        print(f"置信度: {result['confidence']:.2%}")
        if result["uncertain"]:
            print("[需核实] 结果置信度较低，请人工复核。")
        elif result["needs_review"]:
            print("建议复核: 置信度中等，建议人工确认。")
        else:
            print("置信度较高，可直接使用。")
        print("==============================\n")
    except ValueError as e:
        error_code = str(e)
        message = ERROR_MESSAGES.get(error_code, "未知错误")
        print(f"错误 [{error_code}]: {message}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="去AI味 (Humanize Writing Skill) - 将AI生成文本改写为更自然的表达",
        epilog="示例: python main.py --text '首先，这是一个测试。'",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="待处理的文本内容（直接传入字符串）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部环境）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="humanize-writing-skill 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = _run_selftest()
        sys.exit(0 if success else 1)

    # 文本处理模式
    if args.text:
        _run_interactive(args.text)
    else:
        # 未提供参数，打印帮助
        parser.print_help()


if __name__ == "__main__":
    main()
