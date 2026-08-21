#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-powered-seo-content-generator - 独立实现脚本
================================================
依据功能规格从零编写，不参考任何既有代码。

功能：
- 从种子概念生成关键词地图（主词/长尾词/问题词）
- 生成内容大纲（H2/H3 层级）
- 生成 SEO 正文草稿
- 生成标题与元描述候选
- 支持 --selftest 离线自检

错误码：
E001 参数错误
E002 输入为空
E003 种子概念数量超限
E004 文件读取失败
E005 文件大小超限
E006 关键词生成失败
E007 大纲生成失败
E008 正文生成失败
E009 元数据生成失败
E010 自检失败
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class KeywordCluster:
    """关键词聚类结果"""
    primary: List[str] = field(default_factory=list)       # 主词
    long_tail: List[str] = field(default_factory=list)     # 长尾词
    question: List[str] = field(default_factory=list)      # 问题词


@dataclass
class OutlineNode:
    """大纲节点"""
    level: int                                          # 1=H1, 2=H2, 3=H3
    text: str
    children: List["OutlineNode"] = field(default_factory=list)


@dataclass
class ContentPackage:
    """完整内容包"""
    seed: str
    keywords: KeywordCluster
    outline: List[OutlineNode]
    body: str
    titles: List[str]
    meta_descriptions: List[str]
    confidence: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------

class SEOContentGenerator:
    """SEO 内容生成器主类"""

    MAX_SEEDS = 5
    MAX_FILE_SIZE = 500 * 1024  # 500KB

    # 停用词（用于关键词清洗）
    STOP_WORDS = {
        "的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它",
        "我们", "你们", "他们", "这个", "那个", "这些", "那些", "一个", "一种",
        "以及", "或者", "因为", "所以", "但是", "如果", "虽然", "然后", "这样",
        "那样", "什么", "怎么", "如何", "为什么", "the", "a", "an", "and",
        "or", "but", "if", "because", "so", "then", "with", "for", "of",
        "to", "in", "on", "at", "by", "from", "as", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "can", "could", "should", "may", "might",
    }

    # 问题词前缀
    QUESTION_PREFIXES = ["如何", "怎么", "什么", "为什么", "哪些", "是否", "能否", "怎样"]

    # 连接词（用于生成长尾词）
    TAIL_CONNECTORS = ["最佳", "推荐", "教程", "技巧", "方法", "步骤", "价格", "评测", "对比", "指南"]

    def __init__(self) -> None:
        """初始化"""
        self._word_freq: Counter = Counter()

    # ------------------------------------------------------------------
    # 关键词生成
    # ------------------------------------------------------------------

    def generate_keywords(self, seed: str) -> KeywordCluster:
        """
        从种子概念生成关键词聚类

        参数:
            seed: 种子概念文本

        返回:
            KeywordCluster 对象

        错误:
            E002 输入为空
            E006 生成失败
        """
        if not seed or not seed.strip():
            raise ValueError("E002: 种子概念不能为空")

        try:
            # 清洗种子文本
            cleaned = self._clean_text(seed)
            if not cleaned:
                raise ValueError("E006: 关键词生成失败 - 无法从种子提取有效关键词")

            # 提取核心词
            core_words = self._extract_core_words(cleaned)

            # 主词：核心词 + 种子本身
            primary = list(dict.fromkeys([cleaned] + core_words))[:5]

            # 长尾词：核心词 + 连接词组合
            long_tail = []
            for word in core_words:
                for connector in self.TAIL_CONNECTORS:
                    tail_word = f"{word}{connector}"
                    if tail_word not in long_tail:
                        long_tail.append(tail_word)
                # 加种子+词组合
                combo = f"{cleaned}{word}"
                if combo not in long_tail:
                    long_tail.append(combo)

            # 问题词
            question = []
            for prefix in self.QUESTION_PREFIXES:
                for word in core_words[:3]:
                    q = f"{prefix}{word}"
                    if q not in question:
                        question.append(q)
                # 种子本身的问题形式
                q_seed = f"{prefix}{cleaned}"
                if q_seed not in question:
                    question.append(q_seed)

            # 限制数量
            long_tail = long_tail[:15]
            question = question[:10]

            return KeywordCluster(
                primary=primary[:5],
                long_tail=long_tail[:15],
                question=question[:10],
            )

        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"E006: 关键词生成失败 - {exc}") from exc

    # ------------------------------------------------------------------
    # 大纲生成
    # ------------------------------------------------------------------

    def generate_outline(self, seed: str, keywords: KeywordCluster) -> List[OutlineNode]:
        """
        基于关键词聚类生成内容大纲

        参数:
            seed: 种子概念
            keywords: 关键词聚类

        返回:
            大纲节点列表（H2/H3 层级）

        错误:
            E007 大纲生成失败
        """
        try:
            if not keywords.primary:
                raise ValueError("E007: 大纲生成失败 - 缺少主关键词")

            main_word = keywords.primary[0]
            outline: List[OutlineNode] = []

            # H1 标题
            h1 = OutlineNode(level=1, text=f"{main_word}全面指南")

            # H2 节点
            h2_intro = OutlineNode(level=2, text=f"什么是{main_word}")
            h2_benefits = OutlineNode(level=2, text=f"{main_word}的核心价值与优势")
            h2_howto = OutlineNode(level=2, text=f"如何有效使用{main_word}")
            h2_tips = OutlineNode(level=2, text=f"{main_word}的最佳实践与技巧")
            h2_faq = OutlineNode(level=2, text=f"关于{main_word}的常见问题")
            h2_conclusion = OutlineNode(level=2, text=f"总结：{main_word}的未来展望")

            # 为 H2 添加 H3 子节点
            h2_intro.children = [
                OutlineNode(level=3, text=f"{main_word}的基本概念"),
                OutlineNode(level=3, text=f"{main_word}的发展历程"),
            ]

            h2_benefits.children = [
                OutlineNode(level=3, text=f"{main_word}带来的核心收益"),
                OutlineNode(level=3, text=f"{main_word}的适用场景"),
            ]

            h2_howto.children = [
                OutlineNode(level=3, text=f"开始使用{main_word}的步骤"),
                OutlineNode(level=3, text=f"{main_word}的高级用法"),
            ]

            h2_tips.children = [
                OutlineNode(level=3, text=f"提升{main_word}效果的技巧"),
                OutlineNode(level=3, text=f"避免{main_word}常见误区"),
            ]

            if keywords.question:
                h2_faq.children = [
                    OutlineNode(level=3, text=q) for q in keywords.question[:4]
                ]
            else:
                h2_faq.children = [
                    OutlineNode(level=3, text=f"{main_word}常见问题解答"),
                ]

            # 组装大纲
            outline = [h1, h2_intro, h2_benefits, h2_howto, h2_tips, h2_faq, h2_conclusion]
            return outline

        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"E007: 大纲生成失败 - {exc}") from exc

    # ------------------------------------------------------------------
    # 正文生成
    # ------------------------------------------------------------------

    def generate_body(self, seed: str, keywords: KeywordCluster, outline: List[OutlineNode]) -> str:
        """
        根据大纲生成 SEO 正文草稿

        参数:
            seed: 种子概念
            keywords: 关键词聚类
            outline: 大纲节点

        返回:
            正文 Markdown 文本

        错误:
            E008 正文生成失败
        """
        try:
            if not outline:
                raise ValueError("E008: 正文生成失败 - 大纲为空")

            main_word = keywords.primary[0] if keywords.primary else seed
            sections: List[str] = []

            # 遍历大纲生成内容
            for node in outline:
                if node.level == 1:
                    # H1 标题
                    sections.append(f"# {node.text}\n")
                    sections.append(
                        f"在当今竞争激烈的数字环境中，{main_word}已成为不可忽视的重要主题。"
                        f"本文将深入探讨{main_word}的各个方面，为您提供全面、实用的指导。\n"
                    )
                elif node.level == 2:
                    sections.append(f"## {node.text}\n")
                    # 为每个 H2 生成段落内容
                    paragraph = self._generate_paragraph(node.text, main_word, keywords)
                    sections.append(paragraph + "\n")

                    # 生成 H3 子节点内容
                    for child in node.children:
                        sections.append(f"### {child.text}\n")
                        child_para = self._generate_paragraph(child.text, main_word, keywords)
                        sections.append(child_para + "\n")

            # 添加关键词自然融入的提示
            sections.append("---\n")
            sections.append("*本文由 AI 辅助生成，仅供参考学习使用。*\n")

            return "\n".join(sections)

        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"E008: 正文生成失败 - {exc}") from exc

    def _generate_paragraph(self, topic: str, main_word: str, keywords: KeywordCluster) -> str:
        """生成单个段落的内容"""
        # 从关键词中提取相关词汇
        related_terms = []
        if keywords.long_tail:
            related_terms.extend(keywords.long_tail[:3])
        if keywords.question:
            related_terms.extend(keywords.question[:2])

        # 构建段落
        paragraph = (
            f"关于{topic}，首先需要明确的是，{main_word}在实践中的应用价值不容低估。"
            f"通过系统化的方法和持续优化，您能够充分发掘{main_word}的潜力。"
        )

        if related_terms:
            terms_text = "、".join(related_terms)
            paragraph += f"在实际操作中，{terms_text}等概念都与之密切相关。"
            paragraph += f"掌握这些要点，将帮助您更好地理解和运用{main_word}。"

        paragraph += (
            f"值得注意的是，{main_word}并非一成不变，而是随着行业发展和用户需求不断演进。"
            f"持续关注最新动态，灵活调整策略，才能在竞争中保持优势。"
        )

        return paragraph

    # ------------------------------------------------------------------
    # 元数据生成
    # ------------------------------------------------------------------

    def generate_metadata(self, seed: str, keywords: KeywordCluster) -> Tuple[List[str], List[str]]:
        """
        生成标题和元描述候选

        参数:
            seed: 种子概念
            keywords: 关键词聚类

        返回:
            (标题列表, 元描述列表)

        错误:
            E009 元数据生成失败
        """
        try:
            main_word = keywords.primary[0] if keywords.primary else seed
            titles: List[str] = []
            descriptions: List[str] = []

            # 标题模板
            title_templates = [
                f"{main_word}全面指南：从入门到精通",
                f"2026年{main_word}最新攻略，看完你就懂了",
                f"{main_word}怎么选？资深专家为你解读",
                f"一文读懂{main_word}：核心要点全解析",
                f"{main_word}实战教程：快速上手必备",
            ]
            titles = title_templates

            # 元描述模板
            desc_templates = [
                f"深入解析{main_word}的核心概念、应用场景与实操技巧。无论你是新手还是专家，都能从中获得有价值的见解。",
                f"探索{main_word}的方方面面，涵盖基础知识、进阶方法和常见问题。帮助你快速掌握{main_word}的精髓。",
                f"系统梳理{main_word}的关键知识点，提供实用的操作建议和最佳实践。立即阅读，开启你的{main_word}学习之旅。",
                f"从零开始学习{main_word}，本指南将为你提供清晰的路径和实用的工具。适合所有希望深入了解{main_word}的读者。",
                f"{main_word}深度解析：理解核心原理，掌握实操技巧，规避常见误区。一篇文章解决你的所有疑问。",
            ]
            descriptions = desc_templates

            return titles, descriptions

        except Exception as exc:
            raise ValueError(f"E009: 元数据生成失败 - {exc}") from exc

    # ------------------------------------------------------------------
    # 完整内容包生成
    # ------------------------------------------------------------------

    def generate_full_package(self, seed: str) -> ContentPackage:
        """
        生成完整的内容包

        参数:
            seed: 种子概念

        返回:
            ContentPackage 对象

        错误:
            可能抛出 E002/E006/E007/E008/E009
        """
        # 生成关键词
        keywords = self.generate_keywords(seed)

        # 生成大纲
        outline = self.generate_outline(seed, keywords)

        # 生成正文
        body = self.generate_body(seed, keywords, outline)

        # 生成元数据
        titles, descriptions = self.generate_metadata(seed, keywords)

        # 置信度标注
        confidence = {
            "factual_data": "低 - 未进行事实核查",
            "timeliness": "中 - 基于通用知识生成",
            "external_refs": "低 - 无外部引用",
        }

        return ContentPackage(
            seed=seed,
            keywords=keywords,
            outline=outline,
            body=body,
            titles=titles,
            meta_descriptions=descriptions,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # 文件处理（规格中提到但非核心）
    # ------------------------------------------------------------------

    def read_reference_file(self, file_path: str) -> str:
        """
        读取参考文件内容（.txt/.md/.csv）

        参数:
            file_path: 文件路径

        返回:
            文件内容文本

        错误:
            E004 文件读取失败
            E005 文件大小超限
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise ValueError(f"E004: 文件不存在 - {file_path}")

            file_size = path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"E005: 文件大小 {file_size} 超过限制 {self.MAX_FILE_SIZE} 字节"
                )

            suffix = path.suffix.lower()
            if suffix not in (".txt", ".md", ".csv"):
                raise ValueError(f"E004: 不支持的文件类型 - {suffix}")

            return path.read_text(encoding="utf-8", errors="replace")

        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"E004: 文件读取失败 - {exc}") from exc

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """清洗文本：去除多余空白和特殊字符"""
        text = re.sub(r"\s+", " ", text.strip())
        text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text)
        return text.strip()

    def _extract_core_words(self, text: str) -> List[str]:
        """
        从文本中提取核心词汇

        策略：按空格/逗号拆分，过滤停用词，统计词频
        """
        # 拆分：中文按字符、英文按单词
        parts = re.split(r"[\s,，、;；]+", text)
        words = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part in self.STOP_WORDS:
                continue
            words.append(part)

        # 如果没有提取到词，直接将整体作为核心词
        if not words:
            words = [text]

        # 去重并限制数量
        unique_words = list(dict.fromkeys(words))
        return unique_words[:8]


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    离线自检核心逻辑

    使用硬编码样例数据，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值（大小比较/区间判断），确保稳健。

    返回:
        True 表示通过

    错误:
        E010 自检失败
    """
    print("=" * 60)
    print("开始自检...")
    print("=" * 60)

    generator = SEOContentGenerator()

    # 测试样例
    test_seeds = ["SEO优化", "内容营销", "关键词研究"]

    try:
        # 测试 1: 关键词生成
        print("\n[测试 1] 关键词生成")
        for seed in test_seeds:
            kw = generator.generate_keywords(seed)
            assert len(kw.primary) > 0, f"主词为空: {seed}"
            assert len(kw.long_tail) > 0, f"长尾词为空: {seed}"
            assert len(kw.question) > 0, f"问题词为空: {seed}"
            assert len(kw.primary) <= 5, f"主词数量超限: {len(kw.primary)}"
            assert len(kw.long_tail) <= 15, f"长尾词数量超限: {len(kw.long_tail)}"
            assert len(kw.question) <= 10, f"问题词数量超限: {len(kw.question)}"
            print(f"  ✓ {seed}: 主词={len(kw.primary)}, 长尾词={len(kw.long_tail)}, 问题词={len(kw.question)}")

        # 测试 2: 大纲生成
        print("\n[测试 2] 大纲生成")
        for seed in test_seeds:
            kw = generator.generate_keywords(seed)
            outline = generator.generate_outline(seed, kw)
            assert len(outline) >= 3, f"大纲节点太少: {len(outline)}"
            assert outline[0].level == 1, "第一个节点应为 H1"
            h2_count = sum(1 for n in outline if n.level == 2)
            assert h2_count >= 3, f"H2 节点太少: {h2_count}"
            print(f"  ✓ {seed}: 节点数={len(outline)}, H2数={h2_count}")

        # 测试 3: 正文生成
        print("\n[测试 3] 正文生成")
        for seed in test_seeds:
            kw = generator.generate_keywords(seed)
            outline = generator.generate_outline(seed, kw)
            body = generator.generate_body(seed, kw, outline)
            assert len(body) > 100, f"正文太短: {len(body)} 字符"
            assert "#" in body, "正文缺少 Markdown 标题标记"
            assert seed in body or kw.primary[0] in body, "正文未包含核心关键词"
            print(f"  ✓ {seed}: 长度={len(body)} 字符")

        # 测试 4: 元数据生成
        print("\n[测试 4] 元数据生成")
        for seed in test_seeds:
            kw = generator.generate_keywords(seed)
            titles, descriptions = generator.generate_metadata(seed, kw)
            assert len(titles) >= 3, f"标题数量不足: {len(titles)}"
            assert len(descriptions) >= 3, f"描述数量不足: {len(descriptions)}"
            assert all(len(t) > 5 for t in titles), "存在过短标题"
            assert all(len(d) > 20 for d in descriptions), "存在过短描述"
            print(f"  ✓ {seed}: 标题={len(titles)}个, 描述={len(descriptions)}个")

        # 测试 5: 完整内容包
        print("\n[测试 5] 完整内容包")
        for seed in test_seeds:
            pkg = generator.generate_full_package(seed)
            assert pkg.seed == seed, "种子概念不匹配"
            assert len(pkg.keywords.primary) > 0, "关键词为空"
            assert len(pkg.outline) > 0, "大纲为空"
            assert len(pkg.body) > 200, "正文过短"
            assert len(pkg.titles) > 0, "标题为空"
            assert len(pkg.meta_descriptions) > 0, "描述为空"
            assert "confidence" in asdict(pkg), "缺少置信度信息"
            print(f"  ✓ {seed}: 内容包完整")

        # 测试 6: 错误处理
        print("\n[测试 6] 错误处理")
        try:
            generator.generate_keywords("")
            raise AssertionError("空输入未抛出异常")
        except ValueError as e:
            assert str(e).startswith("E002"), f"错误码错误: {e}"
            print("  ✓ 空输入正确抛出 E002")

        try:
            generator.generate_keywords("   ")
            raise AssertionError("空白输入未抛出异常")
        except ValueError as e:
            assert str(e).startswith("E002"), f"错误码错误: {e}"
            print("  ✓ 空白输入正确抛出 E002")

        # 测试 7: 中文/英文混合处理
        print("\n[测试 7] 多语言处理")
        mixed_seed = "SEO content marketing 策略"
        kw = generator.generate_keywords(mixed_seed)
        assert len(kw.primary) > 0, "混合语言关键词生成失败"
        print(f"  ✓ 混合语言输入: {mixed_seed} -> 主词={kw.primary[:2]}")

        # 测试 8: 批量处理（最多5个种子）
        print("\n[测试 8] 批量处理")
        batch_seeds = ["产品A", "产品B", "产品C", "产品D", "产品E"]
        assert len(batch_seeds) <= generator.MAX_SEEDS, "批量数量超限"
        for seed in batch_seeds:
            pkg = generator.generate_full_package(seed)
            assert pkg.seed == seed, f"批量处理失败: {seed}"
        print(f"  ✓ 批量处理 {len(batch_seeds)} 个种子成功")

        print("\n" + "=" * 60)
        print("✅ 所有自检通过！")
        print("=" * 60)
        return True

    except AssertionError as exc:
        print(f"\n❌ 自检失败: {exc}")
        raise ValueError(f"E010: 自检失败 - {exc}") from exc
    except Exception as exc:
        print(f"\n❌ 自检异常: {exc}")
        raise ValueError(f"E010: 自检异常 - {exc}") from exc


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="AI 驱动的 SEO 内容生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --seed "SEO优化"                    # 生成单个内容包
  %(prog)s --seed "产品A" --seed "产品B"       # 批量生成
  %(prog)s --seed "SEO" --output result.json   # 输出到文件
  %(prog)s --selftest                          # 运行自检
        """,
    )

    parser.add_argument(
        "--seed",
        action="append",
        dest="seeds",
        help="种子概念（可多次指定，最多 5 个）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（JSON 格式）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ai-powered-seo-content-generator 1.0.1",
    )

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except ValueError as exc:
            print(f"错误: {exc}")
            return 10

    # 正常模式
    if not args.seeds:
        parser.print_help()
        return 1

    # 检查种子数量
    if len(args.seeds) > SEOContentGenerator.MAX_SEEDS:
        print(f"错误: E003 - 种子概念数量 {len(args.seeds)} 超过限制 {SEOContentGenerator.MAX_SEEDS}")
        return 3

    generator = SEOContentGenerator()

    try:
        results = []
        for seed in args.seeds:
            print(f"\n正在生成内容包: {seed}")
            pkg = generator.generate_full_package(seed)

            # 输出摘要
            print(f"  关键词: {len(pkg.keywords.primary)} 主词, {len(pkg.keywords.long_tail)} 长尾词, {len(pkg.keywords.question)} 问题词")
            print(f"  大纲: {len(pkg.outline)} 个节点")
            print(f"  正文: {len(pkg.body)} 字符")
            print(f"  标题: {len(pkg.titles)} 个, 描述: {len(pkg.meta_descriptions)} 个")

            # 转换为字典
            result = asdict(pkg)
            results.append(result)

        # 输出结果
        if args.output:
            output_path = Path(args.output)
            if not dry_run or getattr(args, "force", False):
                output_path.write_text(
                json.dumps(results, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"\n结果已保存到: {output_path}")
        else:
            print("\n" + "=" * 60)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            print("=" * 60)

        return 0

    except ValueError as exc:
        print(f"错误: {exc}")
        return 1
    except Exception as exc:
        print(f"错误: 未预期的异常 - {exc}")
        return 99


if __name__ == "__main__":
    sys.exit(main())
