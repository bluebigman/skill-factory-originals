#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - SEO文案生成器（Clean Room 独立实现）

依据功能规格独立开发，不参考任何既有代码。
功能：将输入文本转为结构化SEO文案，包含关键词布局与置信度标注。
"""

import argparse
import json
import re
import sys
from collections import Counter
from typing import Any, Dict, List, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入文件无法读取",
    "E003": "输入内容为空",
    "E004": "输出文件无法写入",
    "E005": "JSON序列化失败",
    "E006": "关键词提取失败",
    "E007": "置信度计算失败",
    "E008": "内部逻辑错误",
    "E009": "不支持的输出格式",
    "E010": "自检失败",
}

# 中文停用词（精简版）
STOP_WORDS = {
    "的", "了", "和", "是", "在", "与", "及", "或", "一个", "没有",
    "我们", "你们", "他们", "这个", "那个", "这些", "那些", "之", "以",
    "而", "但", "并", "且", "其", "中", "上", "下", "不", "也", "很",
    "都", "会", "能", "可以", "要", "让", "被", "把", "对", "从",
    "the", "a", "an", "and", "or", "but", "if", "while", "of", "in",
    "on", "at", "to", "for", "with", "by", "as", "is", "are", "was",
}


def log_error(code: str, message: str = "") -> None:
    """输出错误信息到标准错误流"""
    desc = ERROR_CODES.get(code, "未知错误")
    sys.stderr.write(f"[{code}] {desc}")
    if message:
        sys.stderr.write(f": {message}")
    sys.stderr.write("\n")


def extract_keywords(text: str, max_count: int = 10) -> List[Tuple[str, int]]:
    """从文本中提取关键词及其出现频率

    Args:
        text: 输入文本
        max_count: 最大返回关键词数量

    Returns:
        关键词及频率列表 [(keyword, count), ...]

    Raises:
        RuntimeError: 当提取失败时抛出，错误码 E006
    """
    try:
        # 分词：简单按非字母数字字符切分，保留中英文
        tokens = re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z]{3,20}", text.lower())
        if not tokens:
            return []

        # 过滤停用词
        filtered = [t for t in tokens if t not in STOP_WORDS]

        # 统计频率
        counter = Counter(filtered)
        return counter.most_common(max_count)
    except Exception as exc:
        raise RuntimeError(f"E006: 关键词提取失败 - {exc}") from exc


def calculate_confidence(text: str, keywords: List[Tuple[str, int]]) -> float:
    """计算内容置信度

    基于文本长度、关键词覆盖度等因素给出 0-1 的置信度分数。

    Args:
        text: 输入文本
        keywords: 关键词列表

    Returns:
        置信度分数 (0.0 - 1.0)

    Raises:
        RuntimeError: 计算失败时抛出，错误码 E007
    """
    try:
        if not text.strip():
            return 0.0

        # 基础分：文本长度（100字以上给基础分）
        length_score = min(0.4, len(text) / 500.0)

        # 关键词覆盖分：有3个以上关键词给加分
        keyword_score = min(0.3, len(keywords) * 0.05)

        # 结构分：有标题、段落分隔等结构特征
        structure_score = 0.0
        if re.search(r"^#", text, re.MULTILINE):
            structure_score += 0.15
        if re.search(r"\n\s*\n", text):
            structure_score += 0.15

        # 计算最终分数并限制在 0-1 范围
        total = length_score + keyword_score + structure_score
        return round(min(1.0, total), 2)
    except Exception as exc:
        raise RuntimeError(f"E007: 置信度计算失败 - {exc}") from exc


def build_article_structure(text: str, keywords: List[Tuple[str, int]]) -> Dict[str, Any]:
    """构建结构化SEO文案框架

    Args:
        text: 输入原始文本
        keywords: 提取的关键词列表

    Returns:
        结构化文案字典

    Raises:
        RuntimeError: 构建失败时抛出，错误码 E008
    """
    try:
        # 清理文本：去除多余空白
        clean_text = re.sub(r"\s+", " ", text.strip())

        # 提取核心关键词（取前3个）
        core_keywords = [kw for kw, _ in keywords[:3]]

        # 生成标题（基于核心关键词）
        if core_keywords:
            title = f"{core_keywords[0]} - 完整指南与优化建议"
        else:
            title = "SEO文案优化指南"

        # 生成段落（按句子拆分，最多5段）
        sentences = re.split(r"[。！？!?]", clean_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        paragraphs = []
        if sentences:
            # 引言：第一句
            intro = sentences[0]
            paragraphs.append({"type": "引言", "content": intro})

            # 正文：中间句子
            body = "。".join(sentences[1:4]) if len(sentences) > 1 else "围绕核心关键词展开详细论述，提供实用建议与最佳实践。"
            paragraphs.append({"type": "正文", "content": body})

            # 结语：最后一句或默认
            conclusion = sentences[-1] if len(sentences) > 3 else "综合以上分析，持续优化内容质量与关键词布局是提升SEO效果的关键。"
            paragraphs.append({"type": "结语", "content": conclusion})

        # 构建结构
        structure = {
            "title": title,
            "meta_description": f"关于{core_keywords[0] if core_keywords else 'SEO'}的全面解析，涵盖关键词策略、内容优化与实用建议。",
            "keywords": [{"word": kw, "count": cnt} for kw, cnt in keywords],
            "content_structure": paragraphs,
            "seo_suggestions": [
                "确保标题包含核心关键词且长度适中",
                "在正文前100字内自然融入主要关键词",
                "使用小标题（H2/H3）拆分长段落",
                "保持关键词密度在2%-5%之间",
                "添加内链指向相关文章或产品页",
            ],
        }
        return structure
    except Exception as exc:
        raise RuntimeError(f"E008: 构建文章结构失败 - {exc}") from exc


def generate_seo_article(input_text: str, output_format: str = "json") -> Dict[str, Any]:
    """生成完整SEO文案

    Args:
        input_text: 输入原始文本
        output_format: 输出格式（json/markdown）

    Returns:
        包含结构化文案和元信息的字典

    Raises:
        RuntimeError: 各步骤失败时抛出对应错误码
    """
    # 输入校验
    if not input_text or not input_text.strip():
        raise RuntimeError("E003: 输入内容为空")

    # 提取关键词
    keywords = extract_keywords(input_text)

    # 计算置信度
    confidence = calculate_confidence(input_text, keywords)

    # 构建结构
    article = build_article_structure(input_text, keywords)

    # 组装完整结果
    result = {
        "title": article["title"],
        "meta_description": article["meta_description"],
        "keywords": article["keywords"],
        "content_structure": article["content_structure"],
        "seo_suggestions": article["seo_suggestions"],
        "confidence_score": confidence,
        "raw_word_count": len(input_text.split()),
        "format": output_format,
    }

    return result


def format_markdown(article: Dict[str, Any]) -> str:
    """将结果格式化为 Markdown 文本"""
    lines = []
    lines.append(f"# {article['title']}")
    lines.append("")
    lines.append(f"> {article['meta_description']}")
    lines.append("")
    lines.append("## 关键词布局")
    lines.append("")
    lines.append("| 关键词 | 出现次数 |")
    lines.append("|--------|----------|")
    for kw in article["keywords"]:
        lines.append(f"| {kw['word']} | {kw['count']} |")
    lines.append("")
    lines.append("## 内容结构")
    lines.append("")
    for section in article["content_structure"]:
        lines.append(f"### {section['type']}")
        lines.append("")
        lines.append(section["content"])
        lines.append("")
    lines.append("## SEO建议")
    lines.append("")
    for i, suggestion in enumerate(article["seo_suggestions"], 1):
        lines.append(f"{i}. {suggestion}")
    lines.append("")
    lines.append(f"**置信度评分**: {article['confidence_score']:.2f}")
    return "\n".join(lines)


def run_selftest() -> bool:
    """内置自检函数，使用硬编码样例数据验证核心逻辑

    Returns:
        自检是否通过
    """
    try:
        # 硬编码测试数据
        test_input = (
            "SEO优化是提升网站排名的关键策略。通过合理的关键词布局，"
            "可以显著提高搜索引擎的可见度。内容质量与用户体验同样重要，"
            "高质量内容能吸引更多自然流量。关键词研究是SEO的基础工作，"
            "需要分析搜索意图与竞争程度。持续优化网站结构和页面速度，"
            "有助于改善搜索引擎爬虫的抓取效率。"
        )

        # 执行核心流程
        result = generate_seo_article(test_input, "json")

        # 宽松断言：验证结构合理性而非精确值
        assert result is not None, "结果不应为None"
        assert isinstance(result, dict), "结果应为字典"
        assert "title" in result and len(result["title"]) > 0, "标题不应为空"
        assert "keywords" in result and isinstance(result["keywords"], list), "关键词应为列表"
        assert len(result["keywords"]) > 0, "应提取到至少一个关键词"
        assert "content_structure" in result and len(result["content_structure"]) > 0, "内容结构不应为空"
        assert "confidence_score" in result, "应包含置信度"
        assert 0.0 <= result["confidence_score"] <= 1.0, "置信度应在0-1之间"
        assert "seo_suggestions" in result and len(result["seo_suggestions"]) > 0, "应有SEO建议"

        # 验证 Markdown 格式
        md_output = format_markdown(result)
        assert md_output.startswith("# "), "Markdown应以标题开头"
        assert "关键词布局" in md_output, "应包含关键词布局部分"
        assert "置信度" in md_output, "应包含置信度信息"

        # 验证关键词提取
        keywords = extract_keywords(test_input, 5)
        assert len(keywords) > 0, "应提取到关键词"
        assert all(len(kw) > 0 for kw, _ in keywords), "关键词不应为空字符串"

        # 验证置信度计算
        conf = calculate_confidence(test_input, keywords)
        assert 0.0 <= conf <= 1.0, "置信度应在有效范围内"

        print("[SELF-TEST] 全部断言通过，核心逻辑正常。")
        return True

    except AssertionError as exc:
        log_error("E010", f"断言失败: {exc}")
        return False
    except Exception as exc:
        log_error("E010", f"自检异常: {exc}")
        return False


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SEO文案生成器 - 将输入文本转为结构化SEO文案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="输入文件路径（包含原始文本）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径（默认输出到stdout）",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）",
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        return 1
    except Exception as exc:
        log_error("E001", str(exc))
        return 1

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 正常模式：需要输入文件
    if not args.input_file:
        log_error("E002", "未指定输入文件")
        parser.print_help()
        return 1

    # 读取输入文件
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            input_text = f.read()
    except FileNotFoundError:
        log_error("E002", f"文件不存在: {args.input_file}")
        return 1
    except Exception as exc:
        log_error("E002", f"读取失败: {exc}")
        return 1

    # 生成文案
    try:
        result = generate_seo_article(input_text, args.format)

        # 格式化输出
        if args.format == "markdown":
            output_text = format_markdown(result)
        else:
            output_text = json.dumps(result, ensure_ascii=False, indent=2)

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_text)
                print(f"结果已写入: {args.output}")
            except Exception as exc:
                log_error("E004", f"写入失败: {exc}")
                return 1
        else:
            print(output_text)

        return 0

    except RuntimeError as exc:
        # 提取错误码
        code = str(exc).split(":")[0]
        if code in ERROR_CODES:
            log_error(code, str(exc))
        else:
            log_error("E008", str(exc))
        return 1
    except Exception as exc:
        log_error("E008", f"未预期错误: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
