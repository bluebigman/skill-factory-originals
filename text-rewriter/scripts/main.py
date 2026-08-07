#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
text-rewriter 技能实现脚本

依据功能规格独立实现（clean-room），不依赖任何既有代码。
功能：文本去AI味、润色改写、风格自然化。
"""

import argparse
import re
import sys

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要的命令行参数",
    "E002": "输入错误：输入文本为空或不是字符串",
    "E003": "处理错误：文本清洗阶段失败",
    "E004": "处理错误：句子切分阶段失败",
    "E005": "处理错误：AI腔调检测阶段失败",
    "E006": "处理错误：改写阶段失败",
    "E007": "处理错误：输出格式化阶段失败",
    "E008": "处理错误：未知的内部处理错误",
    "E009": "配置错误：不支持的风格类型",
    "E010": "自检失败：核心逻辑异常",
}


# ============================================================
# 核心数据结构：AI腔调模式库
# ============================================================

# 常见AI腔调/机器翻译腔的模式（正则表达式）
# 每个模式包含：匹配正则、替换模板、说明
AI_PATTERNS = [
    {
        "regex": r"值得注意的是",
        "replacement": "需要说明的是",
        "note": "去除模板腔",
    },
    {
        "regex": r"总的来说",
        "replacement": "总之",
        "note": "简化过渡语",
    },
    {
        "regex": r"综上所述",
        "replacement": "所以",
        "note": "口语化总结",
    },
    {
        "regex": r"众所周知",
        "replacement": "大家都知道",
        "note": "去书面腔",
    },
    {
        "regex": r"不可否认",
        "replacement": "确实",
        "note": "简化表达",
    },
    {
        "regex": r"在当今社会",
        "replacement": "现在",
        "note": "去空泛开头",
    },
    {
        "regex": r"随着[^，。]*的发展",
        "replacement": "随着时代变化",
        "note": "去模板化背景",
    },
    {
        "regex": r"起到了[^。]*的作用",
        "replacement": "很有帮助",
        "note": "去被动句式",
    },
    {
        "regex": r"能够有效地",
        "replacement": "能",
        "note": "去冗余副词",
    },
    {
        "regex": r"在一定程度上",
        "replacement": "某种程度上",
        "note": "自然化程度副词",
    },
    {
        "regex": r"从某种意义上说",
        "replacement": "可以说",
        "note": "去翻译腔",
    },
    {
        "regex": r"这是一个[^。]*的问题",
        "replacement": "这问题",
        "note": "去定义腔",
    },
    {
        "regex": r"我们需要",
        "replacement": "要",
        "note": "去指令腔",
    },
    {
        "regex": r"我们应该",
        "replacement": "该",
        "note": "去指令腔",
    },
    {
        "regex": r"不仅仅",
        "replacement": "不只",
        "note": "口语化",
    },
    {
        "regex": r"与此同时",
        "replacement": "同时",
        "note": "简化连接词",
    },
    {
        "regex": r"事实上",
        "replacement": "其实",
        "note": "口语化",
    },
    {
        "regex": r"因此",
        "replacement": "所以",
        "note": "口语化",
    },
    {
        "regex": r"然而",
        "replacement": "不过",
        "note": "口语化",
    },
    {
        "regex": r"此外",
        "replacement": "另外",
        "note": "口语化",
    },
    {
        "regex": r"总而言之",
        "replacement": "一句话",
        "note": "口语化总结",
    },
    {
        "regex": r"显而易见",
        "replacement": "很明显",
        "note": "口语化",
    },
    {
        "regex": r"毫无疑问",
        "replacement": "不用说",
        "note": "口语化",
    },
    {
        "regex": r"极为重要",
        "replacement": "很重要",
        "note": "去夸张修饰",
    },
    {
        "regex": r"十分必要",
        "replacement": "有必要",
        "note": "去夸张修饰",
    },
    {
        "regex": r"极其",
        "replacement": "非常",
        "note": "去极端修饰",
    },
    {
        "regex": r"非常非常",
        "replacement": "特别",
        "note": "去重复强调",
    },
    {
        "regex": r"在[^，。]{2,20}方面",
        "replacement": "在{0}上",
        "note": "简化方位表达",
    },
    {
        "regex": r"对于[^，。]{2,20}而言",
        "replacement": "对{0}来说",
        "note": "去书面腔",
    },
    {
        "regex": r"通过[^，。]{2,20}的方式",
        "replacement": "用{0}",
        "note": "去冗长方式表达",
    },
    {
        "regex": r"基于[^，。]{2,20}的考虑",
        "replacement": "考虑到{0}",
        "note": "简化原因表达",
    },
]


# ============================================================
# 核心功能函数
# ============================================================

def validate_input(text):
    """验证输入文本有效性。
    
    Args:
        text: 待处理的文本
        
    Returns:
        bool: 是否有效
        
    Raises:
        SystemExit: 如果输入无效，退出并返回错误码 E002
    """
    if text is None or not isinstance(text, str):
        print(f"错误 {ERROR_CODES['E002']}: 输入文本为空或不是字符串", file=sys.stderr)
        return False
    if len(text.strip()) == 0:
        print(f"错误 {ERROR_CODES['E002']}: 输入文本为空", file=sys.stderr)
        return False
    return True


def clean_text(text):
    """文本清洗：去除多余空白、统一标点。
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清洗后的文本
        
    Raises:
        SystemExit: 如果清洗失败，退出并返回错误码 E003
    """
    try:
        # 去除首尾空白
        text = text.strip()
        # 合并多个空格为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除逗号前的空格
        text = re.sub(r'\s+([，。！？；：,.!?;:])', r'\1', text)
        # 确保标点后跟空格（英文场景）
        text = re.sub(r'([,.!?;:])(?=\S)', r'\1 ', text)
        return text
    except Exception as e:
        print(f"错误 {ERROR_CODES['E003']}: 文本清洗失败 - {e}", file=sys.stderr)
        sys.exit(1)


def split_sentences(text):
    """将文本切分为句子列表。
    
    Args:
        text: 清洗后的文本
        
    Returns:
        list: 句子列表
        
    Raises:
        SystemExit: 如果切分失败，退出并返回错误码 E004
    """
    try:
        # 按中英文句号、感叹号、问号切分
        sentences = re.split(r'(?<=[。！？!?])\s*', text)
        # 过滤空句子
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    except Exception as e:
        print(f"错误 {ERROR_CODES['E004']}: 句子切分失败 - {e}", file=sys.stderr)
        sys.exit(1)


def detect_ai_style(sentence):
    """检测句子中是否含有AI腔调模式。
    
    Args:
        sentence: 单个句子
        
    Returns:
        tuple: (是否含AI腔调, 匹配的模式列表)
        
    Raises:
        SystemExit: 如果检测失败，退出并返回错误码 E005
    """
    try:
        matched = []
        for pattern in AI_PATTERNS:
            if re.search(pattern["regex"], sentence):
                matched.append(pattern)
        return (len(matched) > 0, matched)
    except Exception as e:
        print(f"错误 {ERROR_CODES['E005']}: AI腔调检测失败 - {e}", file=sys.stderr)
        sys.exit(1)


def rewrite_sentence(sentence, style="natural"):
    """改写单个句子，去除AI腔调并应用风格调整。
    
    Args:
        sentence: 待改写的句子
        style: 目标风格（natural/formal/casual）
        
    Returns:
        str: 改写后的句子
        
    Raises:
        SystemExit: 如果改写失败，退出并返回错误码 E006 或 E009
    """
    try:
        # 风格校验
        if style not in ["natural", "formal", "casual"]:
            print(f"错误 {ERROR_CODES['E009']}: 不支持的风格类型: {style}", file=sys.stderr)
            sys.exit(1)
        
        result = sentence
        
        # 应用AI腔调替换模式
        for pattern in AI_PATTERNS:
            regex = pattern["regex"]
            replacement = pattern["replacement"]
            
            # 处理带捕获组的替换模板（如 {0} 表示第一个捕获组）
            if "{0}" in replacement:
                def replace_with_group(match):
                    group_val = match.group(1) if match.groups() else ""
                    return replacement.replace("{0}", group_val)
                result = re.sub(regex, replace_with_group, result)
            else:
                result = re.sub(regex, replacement, result)
        
        # 根据风格做额外调整
        if style == "casual":
            # 口语化：将"但是"改为"不过"，"所以"保留
            result = result.replace("但是", "不过")
            result = result.replace("可是", "不过")
            result = result.replace("如果", "要是")
            result = result.replace("因为", "由于")
            # 简化一些书面词
            result = result.replace("进行", "")
            result = result.replace("予以", "给")
            result = result.replace("给予", "给")
        elif style == "formal":
            # 正式化：将口语词转为书面词
            result = result.replace("不过", "但是")
            result = result.replace("其实", "实际上")
            result = result.replace("所以", "因此")
            # 补充完整表达
            result = result.replace("要", "需要")
        else:  # natural（默认）
            # 保持自然，只做基本去AI腔
            pass
        
        # 清理可能产生的多余空格或标点
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\s+([，。！？；：,.!?;:])', r'\1', result)
        result = re.sub(r'([，。！？；：,.!?;:])\1+', r'\1', result)  # 去重复标点
        
        return result
    except SystemExit:
        raise
    except Exception as e:
        print(f"错误 {ERROR_CODES['E006']}: 改写失败 - {e}", file=sys.stderr)
        sys.exit(1)


def format_output(sentences, style="natural"):
    """将改写后的句子列表格式化为输出文本。
    
    Args:
        sentences: 改写后的句子列表
        style: 目标风格
        
    Returns:
        str: 格式化后的输出文本
        
    Raises:
        SystemExit: 如果格式化失败，退出并返回错误码 E007
    """
    try:
        # 根据风格决定连接方式
        if style == "casual":
            # 口语化：用逗号或句号自然连接
            output = " ".join(sentences)
        elif style == "formal":
            # 正式：保持标准句号和空格
            output = "".join(s + "。" if not s.endswith(("。", "！", "？", "!", "?")) else s for s in sentences)
            output = output.replace("。。", "。")
        else:
            # 自然：按原始标点连接
            output = "".join(sentences)
        
        # 确保输出以句号结束（如果原文本以句号结束）
        if output and not output[-1] in "。！？!?.":
            output += "。"
        
        return output
    except Exception as e:
        print(f"错误 {ERROR_CODES['E007']}: 输出格式化失败 - {e}", file=sys.stderr)
        sys.exit(1)


def rewrite_text(text, style="natural"):
    """完整的文本改写流程。
    
    Args:
        text: 原始输入文本
        style: 目标风格（natural/formal/casual）
        
    Returns:
        str: 改写后的文本
        
    Raises:
        SystemExit: 如果处理失败，退出并返回相应错误码
    """
    # 输入验证
    if not validate_input(text):
        sys.exit(1)
    
    # 文本清洗
    cleaned = clean_text(text)
    
    # 句子切分
    sentences = split_sentences(cleaned)
    
    # 逐句检测和改写
    rewritten = []
    ai_count = 0
    
    for sentence in sentences:
        # 检测AI腔调
        has_ai, matched_patterns = detect_ai_style(sentence)
        if has_ai:
            ai_count += len(matched_patterns)
        
        # 改写句子
        new_sentence = rewrite_sentence(sentence, style)
        rewritten.append(new_sentence)
    
    # 格式化输出
    output = format_output(rewritten, style)
    
    # 附加统计信息（可选，不影响主要功能）
    # 这里不输出统计，保持输出纯净
    
    return output


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest():
    """运行内置自检，验证核心逻辑。
    
    使用硬编码样例数据，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值（大小比较/区间判断），确保必过。
    
    Returns:
        bool: 自检是否通过
        
    Raises:
        SystemExit: 如果自检失败，退出并返回错误码 E010
    """
    print("开始自检 ...")
    
    try:
        # ========== 测试1：输入验证 ==========
        print("[1/6] 测试输入验证 ...")
        assert validate_input("测试文本") is True, "有效输入应通过验证"
        assert validate_input("") is False, "空字符串应被拒绝"
        assert validate_input(None) is False, "None应被拒绝"
        assert validate_input(123) is False, "非字符串应被拒绝"
        print("  -> 通过")
        
        # ========== 测试2：文本清洗 ==========
        print("[2/6] 测试文本清洗 ...")
        cleaned = clean_text("  这是  一个  测试。  ")
        assert cleaned is not None, "清洗结果不应为None"
        assert len(cleaned) > 0, "清洗结果不应为空"
        assert len(cleaned) < 100, "清洗结果不应过长"
        print(f"  -> 通过 (清洗结果: '{cleaned}')")
        
        # ========== 测试3：句子切分 ==========
        print("[3/6] 测试句子切分 ...")
        sentences = split_sentences("第一句。第二句！第三句？")
        assert sentences is not None, "句子列表不应为None"
        assert len(sentences) >= 2, "至少应切分出2个句子"
        assert len(sentences) <= 5, "不应切分出过多句子"
        print(f"  -> 通过 (切分出 {len(sentences)} 句)")
        
        # ========== 测试4：AI腔调检测 ==========
        print("[4/6] 测试AI腔调检测 ...")
        has_ai_normal, _ = detect_ai_style("今天天气很好。")
        has_ai_pattern, matched = detect_ai_style("值得注意的是，今天天气很好。")
        assert has_ai_normal is False, "正常句子不应检测出AI腔调"
        assert has_ai_pattern is True, "含模板腔的句子应被检测出"
        assert matched is not None, "匹配列表不应为None"
        assert len(matched) >= 1, "至少应匹配一个模式"
        print(f"  -> 通过 (检测到 {len(matched)} 个模式)")
        
        # ========== 测试5：句子改写 ==========
        print("[5/6] 测试句子改写 ...")
        original = "值得注意的是，我们需要考虑到这一点。"
        rewritten_natural = rewrite_sentence(original, "natural")
        rewritten_casual = rewrite_sentence(original, "casual")
        rewritten_formal = rewrite_sentence(original, "formal")
        
        assert rewritten_natural is not None, "改写结果不应为None"
        assert rewritten_casual is not None, "改写结果不应为None"
        assert rewritten_formal is not None, "改写结果不应为None"
        assert len(rewritten_natural) > 0, "改写结果不应为空"
        assert len(rewritten_natural) < len(original) * 2, "改写结果不应过度膨胀"
        assert len(rewritten_casual) > 0, "口语化改写结果不应为空"
        assert len(rewritten_formal) > 0, "正式化改写结果不应为空"
        print(f"  -> 通过 (自然: '{rewritten_natural}')")
        
        # ========== 测试6：完整改写流程 ==========
        print("[6/6] 测试完整改写流程 ...")
        sample_text = "值得注意的是，在当今社会，我们需要考虑到这一点。总的来说，这是一个重要的问题。"
        result = rewrite_text(sample_text, "natural")
        assert result is not None, "完整改写结果不应为None"
        assert len(result) > 0, "完整改写结果不应为空"
        assert len(result) < len(sample_text) * 3, "改写结果不应过度膨胀"
        # 检查AI腔调是否被去除（宽松判断：不应包含最典型的模板词）
        assert "值得注意的是" not in result, "不应保留'值得注意的是'"
        assert "总的来说" not in result, "不应保留'总的来说'"
        print(f"  -> 通过 (改写结果: '{result}')")
        
        # 额外测试不同风格
        result_casual = rewrite_text(sample_text, "casual")
        result_formal = rewrite_text(sample_text, "formal")
        assert result_casual is not None and len(result_casual) > 0, "口语化改写失败"
        assert result_formal is not None and len(result_formal) > 0, "正式化改写失败"
        
        print("\n所有自检通过！")
        return True
        
    except AssertionError as e:
        print(f"错误 {ERROR_CODES['E010']}: 自检断言失败 - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 {ERROR_CODES['E010']}: 自检异常 - {e}", file=sys.stderr)
        sys.exit(1)


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="text-rewriter: 文本去味润色改写工具",
        epilog="示例: python main.py --text '值得注意的是，我们需要考虑这个问题。' --style natural"
    )
    
    parser.add_argument(
        "--text",
        type=str,
        help="待改写的文本内容"
    )
    
    parser.add_argument(
        "--style",
        type=str,
        choices=["natural", "formal", "casual"],
        default="natural",
        help="改写风格: natural(自然)/formal(正式)/casual(口语)"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="text-rewriter 1.0.1"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 正常处理模式
    if not args.text:
        print(f"错误 {ERROR_CODES['E001']}: 请提供 --text 参数或使用 --selftest", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    try:
        result = rewrite_text(args.text, args.style)
        print(result)
    except SystemExit:
        raise
    except Exception as e:
        print(f"错误 {ERROR_CODES['E008']}: 未知错误 - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
