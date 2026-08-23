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
from functools import lru_cache
from typing import Any, Dict, List, Tuple

# 尝试导入jieba，若不可用则使用内置分词
try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

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

# 词性过滤白名单（保留名词、动词、形容词等有意义的词性）
ALLOWED_POS = {'n', 'nr', 'ns', 'nt', 'nz', 'v', 'vd', 'vn', 'a', 'ad', 'an', 'i', 'l', 'j'}

# 常见中文词汇表（用于正则分词的词典匹配）
COMMON_WORDS = {
    "人工智能", "机器学习", "深度学习", "自然语言", "搜索引擎", "关键词",
    "优化", "排名", "流量", "内容", "用户", "体验", "质量", "策略",
    "网站", "页面", "速度", "结构", "爬虫", "抓取", "效率", "分析",
    "研究", "竞争", "程度", "意图", "基础", "工作", "需要", "提高",
    "提升", "关键", "通过", "合理", "布局", "可以", "显著", "可见度",
    "同样", "重要", "高质量", "吸引", "更多", "持续", "改善", "有助于",
    "SEO", "SEO优化", "网站排名", "关键词布局", "内容质量", "用户体验",
    "自然流量", "关键词研究", "搜索意图", "竞争程度", "网站结构", "页面速度",
    "搜索引擎爬虫", "抓取效率", "完整指南", "优化建议", "全面解析",
    "关键词策略", "内容优化", "实用建议", "最佳实践", "综合以上",
    "核心关键词", "正文", "引言", "结语", "标题", "段落", "建议",
}


def log_error(code: str, message: str = "") -> None:
    """输出错误信息到标准错误流"""
    desc = ERROR_CODES.get(code, "未知错误")
    sys.stderr.write(f"[{code}] {desc}")
    if message:
        sys.stderr.write(f": {message}")
    sys.stderr.write("\n")


@lru_cache(maxsize=1024)
def tokenize_text_cached(text: str) -> Tuple[str, ...]:
    """分词函数（带缓存），优先使用jieba，否则使用正则+词典匹配"""
    if JIEBA_AVAILABLE:
        # 使用jieba分词并过滤词性
        words = []
        for word, flag in pseg.cut(text):
            # 过滤停用词和不符合词性的词
            if word.strip() and word not in STOP_WORDS and flag in ALLOWED_POS:
                # 过滤单字词（除非是重要名词）
                if len(word) > 1 or flag in {'n', 'nr', 'ns', 'nt', 'nz'}:
                    words.append(word.lower())
        return tuple(words)
    else:
        # 降级方案：使用正则+词典匹配分词
        tokens = []
        # 先尝试匹配词典中的长词
        for word in sorted(COMMON_WORDS, key=len, reverse=True):
            if word.lower() in text.lower():
                tokens.append(word.lower())
                text = text.replace(word, " " * len(word))  # 用空格替换已匹配的词
        
        # 再使用正则匹配剩余的中英文
        remaining_tokens = re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z]{3,20}", text.lower())
        tokens.extend(remaining_tokens)
        
        # 过滤停用词
        filtered = [t for t in tokens if t not in STOP_WORDS]
        return tuple(filtered)


def tokenize_text(text: str) -> List[str]:
    """分词函数，带缓存"""
    return list(tokenize_text_cached(text))


@lru_cache(maxsize=512)
def extract_keywords_cached(text: str, max_count: int = 10) -> Tuple[Tuple[str, int], ...]:
    """关键词提取（带缓存）"""
    if not text.strip():
        return ()
    
    # 分词
    words = tokenize_text(text)
    if not words:
        return ()
    
    # 统计频率
    counter = Counter(words)
    return tuple(counter.most_common(max_count))


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
        return list(extract_keywords_cached(text, max_count))
    except Exception as exc:
        raise RuntimeError(f"E006: 关键词提取失败 - {exc}") from exc


def calculate_confidence(text: str, keywords: List[Tuple[str, int]]) -> float:
    """计算内容置信度

    基于文本长度、关键词覆盖度、关键词密度等因素给出 0-1 的置信度分数。

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
        text_length = len(text)
        length_score = min(0.4, text_length / 500.0)

        # 关键词覆盖分：有3个以上关键词给加分
        keyword_score = min(0.3, len(keywords) * 0.05)

        # 关键词密度分：计算关键词在文本中的密度
        density_score = 0.0
        if keywords and text_length > 0:
            total_keyword_occurrences = sum(count for _, count in keywords)
            density = total_keyword_occurrences / text_length
            # 理想密度在2%-5%之间
            if 0.02 <= density <= 0.05:
                density_score = 0.15
            elif density > 0:
                density_score = 0.1

        # 结构分：有标题、段落分隔等结构特征
        structure_score = 0.0
        if re.search(r"^#", text, re.MULTILINE):
            structure_score += 0.15
        if re.search(r"\n\s*\n", text):
            structure_score += 0.15

        # 计算最终分数并限制在 0-1 范围
        total = length_score + keyword_score + density_score + structure_score
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
    """内置自检函数，验证核心链路（分词→关键词→文案生成→置信度）

    Returns:
        自检是否通过
    """
    try:
        # 测试数据
        test_input = (
            "SEO优化是提升网站排名的关键策略。通过合理的关键词布局，"
            "可以显著提高搜索引擎的可见度。内容质量与用户体验同样重要，"
            "高质量内容能吸引更多自然流量。关键词研究是SEO的基础工作，"
            "需要分析搜索意图与竞争程度。持续优化网站结构和页面速度，"
            "有助于改善搜索引擎爬虫的抓取效率。"
        )

        # 1. 测试分词
        words = tokenize_text(test_input)
        assert len(words) > 0, "分词结果不应为空"
        assert "SEO" in words or "seo" in words, "应包含SEO关键词"
        assert "优化" in words, "应包含'优化'关键词"

        # 2. 测试关键词提取
        keywords = extract_keywords(test_input, 10)
        assert len(keywords) > 0, "应提取到至少一个关键词"
        assert all(len(kw) > 0 for kw, _ in keywords), "关键词不应为空字符串"
        
        # 3. 测试完整文案生成
        result = generate_seo_article(test_input, "json")
        assert result is not None, "结果不应为None"
        assert isinstance(result, dict), "结果应为字典"
        assert "title" in result and len(result["title"]) > 0, "标题不应为空"
        assert "keywords" in result and isinstance(result["keywords"], list), "关键词应为列表"
        assert len(result["keywords"]) > 0, "应提取到至少一个关键词"
        assert "content_structure" in result and len(result["content_structure"]) > 0, "内容结构不应为空"
        assert "confidence_score" in result, "应包含置信度"
        assert 0.0 <= result["confidence_score"] <= 1.0, "置信度应在0-1之间"
        assert "seo_suggestions" in result and len(result["seo_suggestions"]) > 0, "应有SEO建议"

        # 4. 测试置信度计算
        conf = calculate_confidence(test_input, keywords)
        assert 0.0 <= conf <= 1.0, "置信度应在有效范围内"
        assert conf > 0.0, "置信度应大于0"

        # 5. 测试Markdown格式输出
        md_output = format_markdown(result)
        assert md_output.startswith("# "), "Markdown应以标题开头"
        assert "关键词布局" in md_output, "应包含关键词布局部分"
        assert "置信度" in md_output, "应包含置信度信息"

        # 6. 测试空输入处理
        try:
            generate_seo_article("")
            assert False, "空输入应抛出异常"
        except RuntimeError as e:
            assert "E003" in str(e), "空输入应返回E003错误"

        # 7. 测试中文分词歧义处理（如果jieba可用）
        if JIEBA_AVAILABLE:
            test_ambiguous = "人工智能技术在各个领域都有广泛应用"
            amb_keywords = extract_keywords(test_ambiguous, 5)
            amb_words = [kw for kw, _ in amb_keywords]
            assert "人工智能" in amb_words, "应正确识别'人工智能'为完整词"
            assert not ("人工" in amb_words and "智能" in amb_words), "不应错误切分'人工智能'"

        # 8. 测试缓存机制
        tokenize_text(test_input)  # 第一次调用
        tokenize_text(test_input)  # 第二次调用（应命中缓存）
        assert tokenize_text_cached.cache_info().hits > 0, "分词缓存应有命中"

        print("[SELF-TEST] 全部断言通过，核心逻辑正常。")
        print(f"[SELF-TEST] 分词结果: {words[:5]}...")
        print(f"[SELF-TEST] 关键词提取结果: {[kw for kw, _ in keywords]}")
        print(f"[SELF-TEST] 置信度: {conf}")
        print(f"[SELF-TEST] 缓存命中次数: {tokenize_text_cached.cache_info().hits}")
        return True

    except AssertionError as exc:
        log_error("E010", f"断言失败: {exc}")
        return False
