#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seo-article-generator 独立实现脚本
----------------------------------
基于功能规格的 clean-room 实现，提供关键词解析、内容结构生成等核心能力。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --keyword "2025年家庭储能电池选购指南"
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数缺失或格式错误",
    "E002": "关键词为空",
    "E003": "关键词长度超出限制",
    "E004": "URL 格式无效",
    "E005": "文档解析失败",
    "E006": "文章结构生成失败",
    "E007": "批量处理输入无效",
    "E008": "内部逻辑错误",
    "E009": "输出写入失败",
    "E010": "未知错误",
}


@dataclass
class KeywordAnalysis:
    """关键词解析结果"""
    raw_keyword: str
    core_topic: str = ""
    search_intent: str = ""
    target_audience: str = ""
    sub_keywords: List[str] = field(default_factory=list)


@dataclass
class ArticleOutline:
    """文章大纲结构"""
    title: str = ""
    h1: str = ""
    h2_sections: List[str] = field(default_factory=list)
    h3_subsections: Dict[str, List[str]] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)


class SEOArticleGenerator:
    """SEO 文章生成器核心类"""

    # 搜索意图关键词模式
    INTENT_PATTERNS = {
        "对比": ["对比", "比较", "vs", "哪个好", "区别"],
        "选购": ["选购", "推荐", "指南", "怎么选", "购买"],
        "教程": ["教程", "怎么", "如何", "步骤", "方法"],
        "资讯": ["新闻", "最新", "趋势", "报告", "分析"],
    }

    # 受众关键词模式
    AUDIENCE_PATTERNS = {
        "户主/家庭用户": ["家庭", "家用", "户主", "住宅"],
        "DIY爱好者": ["DIY", "自制", "自己动手"],
        "企业采购": ["企业", "商用", "采购", "公司"],
        "专业人士": ["工程师", "专业", "行业"],
    }

    # 常见停用词（用于主题提取）
    STOP_WORDS = {"的", "了", "和", "是", "在", "有", "与", "及", "或", "年", "月", "日"}

    def __init__(self, max_keyword_length: int = 100):
        self.max_keyword_length = max_keyword_length

    def analyze_keyword(self, keyword: str) -> KeywordAnalysis:
        """解析关键词，提取核心主题、搜索意图和目标受众"""
        if not keyword or not keyword.strip():
            raise ValueError("E002: 关键词为空")

        keyword = keyword.strip()
        if len(keyword) > self.max_keyword_length:
            raise ValueError(f"E003: 关键词长度超出限制（最大{self.max_keyword_length}字符）")

        # 提取核心主题：去除停用词和意图词
        core_terms = []
        for char in keyword:
            if char not in self.STOP_WORDS and char.isalnum():
                core_terms.append(char)

        # 简单主题提取：取第一个有意义的词段
        core_topic = self._extract_core_topic(keyword)

        # 识别搜索意图
        search_intent = self._detect_intent(keyword)

        # 识别目标受众
        target_audience = self._detect_audience(keyword)

        # 生成子关键词
        sub_keywords = self._generate_sub_keywords(keyword, core_topic)

        return KeywordAnalysis(
            raw_keyword=keyword,
            core_topic=core_topic,
            search_intent=search_intent,
            target_audience=target_audience,
            sub_keywords=sub_keywords,
        )

    def _extract_core_topic(self, keyword: str) -> str:
        """从关键词中提取核心主题"""
        # 移除常见意图词
        intent_words = []
        for words in self.INTENT_PATTERNS.values():
            intent_words.extend(words)

        cleaned = keyword
        for word in intent_words:
            cleaned = cleaned.replace(word, "")

        # 移除停用词
        for word in self.STOP_WORDS:
            cleaned = cleaned.replace(word, "")

        # 取第一个有意义的片段（长度>=2）
        parts = [p for p in re.split(r'[\s,，。；;、]+', cleaned) if len(p) >= 2]
        if parts:
            return parts[0]
        return keyword[:10]  # 兜底

    def _detect_intent(self, keyword: str) -> str:
        """检测搜索意图"""
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in keyword:
                    return intent
        return "综合"  # 默认意图

    def _detect_audience(self, keyword: str) -> str:
        """检测目标受众"""
        for audience, patterns in self.AUDIENCE_PATTERNS.items():
            for pattern in patterns:
                if pattern in keyword:
                    return audience
        return "通用人群"  # 默认受众

    def _generate_sub_keywords(self, keyword: str, core_topic: str) -> List[str]:
        """生成相关子关键词"""
        sub_keywords = []
        intent = self._detect_intent(keyword)

        # 基于核心主题生成扩展
        if core_topic:
            sub_keywords.append(f"{core_topic} 优缺点")
            sub_keywords.append(f"{core_topic} 价格")
            sub_keywords.append(f"{core_topic} 品牌推荐")

        # 基于意图生成
        if intent == "对比":
            sub_keywords.append(f"{core_topic} 对比评测")
        elif intent == "选购":
            sub_keywords.append(f"{core_topic} 选购技巧")
        elif intent == "教程":
            sub_keywords.append(f"{core_topic} 使用教程")

        # 去重并限制数量
        unique_keywords = []
        for kw in sub_keywords:
            if kw not in unique_keywords:
                unique_keywords.append(kw)
            if len(unique_keywords) >= 5:
                break

        return unique_keywords

    def generate_outline(self, keyword: str) -> ArticleOutline:
        """根据关键词生成文章大纲"""
        try:
            analysis = self.analyze_keyword(keyword)

            # 生成标题
            title = self._generate_title(analysis)

            # 生成 H1
            h1 = analysis.core_topic if analysis.core_topic else keyword

            # 生成 H2 段落
            h2_sections = self._generate_h2_sections(analysis)

            # 生成 H3 子段落
            h3_subsections = self._generate_h3_subsections(h2_sections)

            # 标记缺失字段
            missing = self._identify_missing_fields(analysis)

            return ArticleOutline(
                title=title,
                h1=h1,
                h2_sections=h2_sections,
                h3_subsections=h3_subsections,
                missing_fields=missing,
            )
        except ValueError as e:
            raise ValueError(f"E006: 文章结构生成失败 - {str(e)}")
        except Exception as e:
            raise RuntimeError(f"E008: 内部逻辑错误 - {str(e)}")

    def _generate_title(self, analysis: KeywordAnalysis) -> str:
        """生成文章标题"""
        topic = analysis.core_topic
        intent = analysis.search_intent

        if intent == "对比":
            return f"{topic}全面对比：优缺点与选购建议"
        elif intent == "选购":
            return f"{topic}选购指南：{analysis.target_audience}必看"
        elif intent == "教程":
            return f"{topic}完全教程：从入门到精通"
        else:
            return f"{topic}最新趋势与深度分析"

    def _generate_h2_sections(self, analysis: KeywordAnalysis) -> List[str]:
        """生成 H2 章节列表"""
        topic = analysis.core_topic
        intent = analysis.search_intent

        sections = [
            f"什么是{topic}？",
            f"{topic}的核心优势",
            f"如何选择适合的{topic}",
        ]

        if intent == "对比":
            sections.append(f"{topic}主流品牌对比")
        elif intent == "教程":
            sections.append(f"{topic}实战操作步骤")

        sections.append(f"{topic}常见问题与解答")
        return sections

    def _generate_h3_subsections(self, h2_sections: List[str]) -> Dict[str, List[str]]:
        """为每个 H2 生成 H3 子段落"""
        h3_map = {}
        for section in h2_sections:
            # 根据章节类型生成子段落
            if "什么是" in section:
                h3_map[section] = ["定义与概述", "核心特点", "应用场景"]
            elif "优势" in section:
                h3_map[section] = ["性能优势", "成本优势", "用户体验"]
            elif "选择" in section:
                h3_map[section] = ["关键因素", "预算考虑", "品牌参考"]
            elif "对比" in section:
                h3_map[section] = ["规格对比", "性能对比", "价格对比"]
            elif "操作" in section:
                h3_map[section] = ["准备工作", "执行步骤", "注意事项"]
            else:
                h3_map[section] = ["常见问题", "解决方案", "专家建议"]

        return h3_map

    def _identify_missing_fields(self, analysis: KeywordAnalysis) -> List[str]:
        """识别缺失的信息字段"""
        missing = []
        if not analysis.core_topic:
            missing.append("核心主题")
        if not analysis.search_intent:
            missing.append("搜索意图")
        if not analysis.target_audience:
            missing.append("目标受众")
        return missing

    def format_outline(self, outline: ArticleOutline) -> str:
        """将大纲格式化为可读文本"""
        lines = []
        lines.append(f"# {outline.title}")
        lines.append("")
        lines.append(f"## {outline.h1}")
        lines.append("")

        for h2 in outline.h2_sections:
            lines.append(f"### {h2}")
            for h3 in outline.h3_subsections.get(h2, []):
                lines.append(f"#### {h3}")
            lines.append("")

        if outline.missing_fields:
            lines.append("---")
            lines.append("**缺失字段提醒：**")
            for field_name in outline.missing_fields:
                lines.append(f"- [需核实:{field_name}]")

        return "\n".join(lines)


def run_selftest() -> bool:
    """内置自检函数，使用硬编码样例数据验证核心逻辑"""
    print("=" * 60)
    print("开始自检 (selftest)...")
    print("=" * 60)

    # 创建生成器实例
    generator = SEOArticleGenerator()

    # 测试样例 1: 对比类关键词
    print("\n[测试1] 对比类关键词解析")
    kw1 = "2025年家庭储能电池选购指南"
    try:
        analysis1 = generator.analyze_keyword(kw1)
        # 宽松断言：核心主题非空
        assert len(analysis1.core_topic) > 0, "核心主题不能为空"
        # 宽松断言：意图识别为选购或对比
        assert analysis1.search_intent in ["选购", "对比", "综合"], "意图识别异常"
        # 宽松断言：子关键词数量合理
        assert 1 <= len(analysis1.sub_keywords) <= 8, "子关键词数量异常"
        print(f"  ✓ 关键词解析成功: 主题={analysis1.core_topic}, 意图={analysis1.search_intent}")
    except Exception as e:
        print(f"  ✗ 测试1失败: {e}")
        return False

    # 测试样例 2: 教程类关键词
    print("\n[测试2] 教程类关键词解析")
    kw2 = "如何搭建个人博客网站"
    try:
        analysis2 = generator.analyze_keyword(kw2)
        assert analysis2.core_topic, "核心主题不能为空"
        assert analysis2.search_intent in ["教程", "综合"], "意图识别异常"
        print(f"  ✓ 关键词解析成功: 主题={analysis2.core_topic}, 意图={analysis2.search_intent}")
    except Exception as e:
        print(f"  ✗ 测试2失败: {e}")
        return False

    # 测试样例 3: 文章大纲生成
    print("\n[测试3] 文章大纲生成")
    try:
        outline = generator.generate_outline(kw1)
        # 宽松断言：标题非空
        assert len(outline.title) > 0, "标题不能为空"
        # 宽松断言：H1 非空
        assert len(outline.h1) > 0, "H1 不能为空"
        # 宽松断言：H2 章节数量合理
        assert 3 <= len(outline.h2_sections) <= 8, "H2 章节数量异常"
        # 宽松断言：每个 H2 都有 H3 子段落
        for h2 in outline.h2_sections:
            assert len(outline.h3_subsections.get(h2, [])) > 0, f"H2 '{h2}' 缺少H3子段落"
        print(f"  ✓ 大纲生成成功: 标题={outline.title}")
        print(f"    包含 {len(outline.h2_sections)} 个H2章节")
    except Exception as e:
        print(f"  ✗ 测试3失败: {e}")
        return False

    # 测试样例 4: 格式输出
    print("\n[测试4] 大纲格式化输出")
    try:
        outline = generator.generate_outline(kw2)
        formatted = generator.format_outline(outline)
        # 宽松断言：输出文本非空且包含标题
        assert len(formatted) > 50, "格式化输出过短"
        assert outline.title in formatted, "标题未出现在输出中"
        print(f"  ✓ 格式化输出成功，文本长度={len(formatted)}字符")
    except Exception as e:
        print(f"  ✗ 测试4失败: {e}")
        return False

    # 测试样例 5: 错误处理
    print("\n[测试5] 错误处理验证")
    try:
        # 空关键词应抛出异常
        generator.analyze_keyword("")
        print("  ✗ 测试5失败: 空关键词未抛出异常")
        return False
    except ValueError as e:
        assert "E002" in str(e), "错误码不正确"
        print(f"  ✓ 空关键词错误处理正确: {e}")

    try:
        # 超长关键词应抛出异常
        generator.analyze_keyword("长" * 200)
        print("  ✗ 测试5失败: 超长关键词未抛出异常")
        return False
    except ValueError as e:
        assert "E003" in str(e), "错误码不正确"
        print(f"  ✓ 超长关键词错误处理正确: {e}")

    # 测试样例 6: 批量处理
    print("\n[测试6] 批量处理验证")
    keywords = ["SEO优化技巧", "内容营销策略", "关键词研究工具"]
    try:
        outlines = []
        for kw in keywords:
            outline = generator.generate_outline(kw)
            outlines.append(outline)
        assert len(outlines) == len(keywords), "批量处理数量不匹配"
        for i, outline in enumerate(outlines):
            assert len(outline.title) > 0, f"第{i+1}个大纲标题为空"
        print(f"  ✓ 批量处理成功，共生成 {len(outlines)} 个大纲")
    except Exception as e:
        print(f"  ✗ 测试6失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("自检全部通过！")
    print("=" * 60)
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SEO文章生成器 - 基于关键词生成文章大纲",
        epilog="示例: python scripts/main.py --keyword '2025年家庭储能电池选购指南'"
    )
    parser.add_argument(
        "--keyword",
        type=str,
        help="要分析的关键词",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，默认输出到终端）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 关键词模式
    if not args.keyword:
        print("E001: 参数缺失，请提供 --keyword 或使用 --selftest")
        sys.exit(1)

    try:
        # 创建生成器
        generator = SEOArticleGenerator()

        # 生成大纲
        outline = generator.generate_outline(args.keyword)

        # 格式化输出
        formatted = generator.format_outline(outline)

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(formatted)
                print(f"大纲已保存到: {args.output}")
            except Exception as e:
                print(f"E009: 输出写入失败 - {e}")
                sys.exit(1)
        else:
            print(formatted)

    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"E010: 未知错误 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
