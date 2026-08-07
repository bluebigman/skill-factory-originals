#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openseo-studio — SEO文案内容优化与关键词策略工具

本脚本为 clean-room 独立实现，仅依据功能规格文档编写。
支持批量处理、关键词提取、SEO评分与置信度标注。
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入数据格式错误",
    "E002": "缺少必要字段",
    "E003": "文本长度超出限制",
    "E004": "关键词列表为空",
    "E005": "批量处理失败",
    "E006": "输出序列化错误",
    "E007": "参数解析错误",
    "E008": "内部逻辑错误",
    "E009": "置信度计算异常",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class SEOItem:
    """单条SEO处理结果。"""
    title: str = ""
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    score: float = 0.0
    confidence: float = 0.0
    suggestions: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典，便于序列化。"""
        return {
            "title": self.title,
            "content": self.content,
            "keywords": self.keywords,
            "score": round(self.score, 2),
            "confidence": round(self.confidence, 2),
            "suggestions": self.suggestions,
            "extra": self.extra,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class SEOProcessor:
    """SEO内容分析与优化处理器。"""

    # 常见停用词（中英文混合，用于关键词过滤）
    STOP_WORDS = {
        "的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它",
        "这", "那", "与", "就", "又", "很", "都", "而", "及", "或",
        "a", "an", "the", "and", "or", "but", "of", "to", "for", "with",
        "on", "at", "in", "by", "from", "as", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
    }

    # 中文分词辅助：简单的二元/三元组提取
    CHINESE_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")

    def __init__(self, max_text_length: int = 10000):
        """
        初始化处理器。

        Args:
            max_text_length: 单条文本最大字符数，超过则报E003。
        """
        self.max_text_length = max_text_length

    # ------------------------------------------------------------------
    # 文本处理基础方法
    # ------------------------------------------------------------------
    def _validate_input(self, data: Dict[str, Any]) -> None:
        """校验输入数据结构。"""
        if not isinstance(data, dict):
            raise SkillError("E001", "输入必须是字典对象")
        if "content" not in data or not data.get("content"):
            raise SkillError("E002", "缺少 content 字段或内容为空")
        if len(str(data["content"])) > self.max_text_length:
            raise SkillError("E003", f"内容长度超过限制 {self.max_text_length} 字符")

    def _extract_words(self, text: str) -> List[str]:
        """
        从文本中提取候选词（英文按空格拆分，中文按连续字符块）。

        Args:
            text: 输入文本

        Returns:
            候选词列表（已小写化）
        """
        # 英文单词提取
        english_words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-']{1,}", text.lower())

        # 中文连续字符块（2-6字）
        chinese_blocks = []
        chinese_chars = self.CHINESE_CHAR_RE.findall(text)
        if len(chinese_chars) >= 2:
            # 提取连续的中文字符串
            chinese_str = "".join(chinese_chars)
            for length in range(2, min(7, len(chinese_str) + 1)):
                for i in range(len(chinese_str) - length + 1):
                    block = chinese_str[i:i + length]
                    if block not in self.STOP_WORDS:
                        chinese_blocks.append(block)

        return english_words + chinese_blocks

    def _filter_keywords(self, words: List[str], min_freq: int = 2) -> List[str]:
        """
        过滤停用词并统计词频，返回高频词。

        Args:
            words: 候选词列表
            min_freq: 最小出现次数

        Returns:
            过滤后的关键词列表
        """
        # 过滤停用词和单字符
        filtered = [
            w for w in words
            if w not in self.STOP_WORDS and len(w) > 1
        ]
        counter = Counter(filtered)
        # 按频率降序，再按词长降序（长词通常更有信息量）
        sorted_words = sorted(
            counter.items(),
            key=lambda x: (x[1], len(x[0])),
            reverse=True
        )
        # 返回出现次数达到阈值的词
        result = [word for word, freq in sorted_words if freq >= min_freq]
        return result[:20]  # 最多返回20个关键词

    # ------------------------------------------------------------------
    # 评分与置信度
    # ------------------------------------------------------------------
    def _calculate_score(self, content: str, keywords: List[str]) -> float:
        """
        计算SEO评分（0-100）。

        评分维度：
        - 内容长度（0-30分）
        - 关键词密度（0-40分）
        - 标题/结构（0-30分）

        Args:
            content: 文本内容
            keywords: 关键词列表

        Returns:
            评分（0-100）
        """
        if not content:
            return 0.0

        score = 0.0
        content_len = len(content)

        # 1. 内容长度评分（0-30）
        if content_len >= 2000:
            score += 30
        elif content_len >= 1000:
            score += 25
        elif content_len >= 500:
            score += 18
        elif content_len >= 200:
            score += 12
        elif content_len >= 50:
            score += 6
        else:
            score += 2

        # 2. 关键词密度评分（0-40）
        if keywords:
            content_lower = content.lower()
            total_freq = 0
            for kw in keywords:
                # 简单统计关键词出现次数
                total_freq += content_lower.count(kw.lower())
            # 密度 = 总出现次数 / 文本长度 * 1000（每千字出现次数）
            density = total_freq / max(content_len / 1000, 1)
            if 5 <= density <= 20:
                score += 40  # 理想密度
            elif 2 <= density < 5 or 20 < density <= 30:
                score += 25  # 可接受范围
            elif density > 0:
                score += 10  # 有出现但密度不合适
            else:
                score += 0  # 无关键词出现

        # 3. 结构评分（0-30）
        # 检查是否有多段落（换行）
        paragraphs = [p for p in content.split("\n") if p.strip()]
        if len(paragraphs) >= 3:
            score += 10
        elif len(paragraphs) >= 2:
            score += 6
        else:
            score += 2

        # 检查是否有标题样式（# 开头）
        if re.search(r"^#{1,3}\s", content, re.MULTILINE):
            score += 10

        # 检查是否有列表（- 或 * 开头）
        if re.search(r"^[-*]\s", content, re.MULTILINE):
            score += 5

        # 检查是否有加粗或强调（** 或 __）
        if re.search(r"(\*\*|__)", content):
            score += 5

        return min(score, 100.0)

    def _calculate_confidence(self, score: float, content_len: int, keyword_count: int) -> float:
        """
        计算置信度（0-1）。

        置信度基于：
        - 内容长度充足度
        - 关键词覆盖度
        - 评分本身的稳定性

        Args:
            score: SEO评分
            content_len: 内容长度
            keyword_count: 关键词数量

        Returns:
            置信度（0-1）
        """
        try:
            # 内容充足度因子（0-1）
            length_factor = min(content_len / 1500, 1.0)

            # 关键词覆盖因子（0-1）
            keyword_factor = min(keyword_count / 10, 1.0)

            # 评分稳定因子（评分越高，置信度越高，但非线性）
            score_factor = min(score / 80, 1.0)

            # 综合计算，权重略有不同
            confidence = 0.4 * length_factor + 0.35 * keyword_factor + 0.25 * score_factor

            # 确保在0-1之间
            return max(0.0, min(confidence, 1.0))
        except Exception as exc:
            raise SkillError("E009", f"置信度计算失败: {exc}") from exc

    def _generate_suggestions(self, score: float, content: str, keywords: List[str]) -> List[str]:
        """
        根据评分生成优化建议。

        Args:
            score: SEO评分
            content: 文本内容
            keywords: 关键词列表

        Returns:
            建议列表
        """
        suggestions = []
        content_len = len(content)

        # 长度建议
        if content_len < 500:
            suggestions.append("内容长度不足500字，建议扩充至1000字以上以提升SEO效果")
        elif content_len < 1000:
            suggestions.append("内容长度适中，建议补充更多细节至1500字左右")

        # 关键词建议
        if not keywords:
            suggestions.append("未检测到有效关键词，建议在内容中自然融入目标关键词")
        elif len(keywords) < 3:
            suggestions.append("关键词数量偏少，建议增加长尾关键词的覆盖")
        else:
            suggestions.append(f"检测到 {len(keywords)} 个关键词，密度合理")

        # 结构建议
        if not re.search(r"^#{1,3}\s", content, re.MULTILINE):
            suggestions.append("建议使用Markdown标题（#）来组织内容结构")
        if not re.search(r"^[-*]\s", content, re.MULTILINE):
            suggestions.append("建议使用列表（- 或 *）来呈现要点信息")
        if not re.search(r"(\*\*|__)", content):
            suggestions.append("建议使用加粗（**文本**）来强调重要信息")

        # 评分建议
        if score < 50:
            suggestions.append("整体评分偏低，建议全面优化内容质量和关键词布局")
        elif score < 75:
            suggestions.append("评分良好，可进一步优化关键词密度和内容结构")

        return suggestions[:6]  # 最多6条建议

    # ------------------------------------------------------------------
    # 对外主接口
    # ------------------------------------------------------------------
    def process_item(self, data: Dict[str, Any]) -> SEOItem:
        """
        处理单条数据。

        Args:
            data: 包含 title, content, keywords 等字段的字典

        Returns:
            SEOItem 处理结果
        """
        self._validate_input(data)

        title = str(data.get("title", ""))
        content = str(data["content"])
        user_keywords = data.get("keywords", [])

        # 提取自动关键词
        words = self._extract_words(content)
        auto_keywords = self._filter_keywords(words, min_freq=2)

        # 合并用户提供的关键词
        if isinstance(user_keywords, list):
            cleaned_user_kw = [str(k).strip() for k in user_keywords if str(k).strip()]
            all_keywords = list(dict.fromkeys(cleaned_user_kw + auto_keywords))
        else:
            all_keywords = auto_keywords

        if not all_keywords:
            raise SkillError("E004", "未提取到有效关键词，请提供关键词或增加文本内容")

        # 计算评分与置信度
        score = self._calculate_score(content, all_keywords)
        confidence = self._calculate_confidence(score, len(content), len(all_keywords))
        suggestions = self._generate_suggestions(score, content, all_keywords)

        # 构建额外信息
        extra = {
            "content_length": len(content),
            "auto_keywords_found": len(auto_keywords),
            "user_keywords_provided": len(cleaned_user_kw) if isinstance(user_keywords, list) else 0,
            "processing_version": "1.0.1",
        }

        return SEOItem(
            title=title,
            content=content,
            keywords=all_keywords,
            score=score,
            confidence=confidence,
            suggestions=suggestions,
            extra=extra,
        )

    def process_batch(self, items: List[Dict[str, Any]]) -> List[SEOItem]:
        """
        批量处理多条数据。

        Args:
            items: 数据字典列表

        Returns:
            SEOItem 列表
        """
        results = []
        errors = []
        for idx, item in enumerate(items):
            try:
                result = self.process_item(item)
                results.append(result)
            except SkillError as exc:
                errors.append({"index": idx, "code": exc.code, "message": exc.message})
            except Exception as exc:
                errors.append({"index": idx, "code": "E010", "message": str(exc)})

        if errors:
            raise SkillError("E005", f"批量处理完成，但 {len(errors)} 条失败: {errors[:3]}")

        return results


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    Returns:
        0 表示成功，非0表示失败
    """
    print("=" * 60)
    print("openseo-studio 自检开始")
    print("=" * 60)

    processor = SEOProcessor()

    # 硬编码测试数据（不依赖外部文件）
    test_items = [
        {
            "title": "SEO优化入门指南",
            "content": (
                "# SEO优化入门指南\n\n"
                "SEO是搜索引擎优化的缩写，是提升网站排名的关键方法。\n"
                "**关键词研究**是SEO的基础，需要找到用户搜索频率高的词。\n\n"
                "- 内容质量是SEO的核心\n"
                "- 外链建设可以提升权重\n"
                "- 技术优化改善爬虫抓取\n\n"
                "SEO优化需要持续投入，包括内容更新、链接建设、性能优化等。\n"
                "好的SEO策略应该结合用户意图和搜索引擎算法。\n"
                "SEO优化是一个长期过程，需要耐心和数据分析能力。\n"
                "通过SEO优化，可以显著提升网站的自然流量。\n"
                "SEO优化需要关注关键词密度、内容结构和用户体验。\n"
                "持续产出高质量内容，SEO效果会逐渐显现。"
            ),
            "keywords": ["SEO优化", "关键词研究"],
        },
        {
            "title": "Python编程基础",
            "content": (
                "Python是一种简洁优雅的编程语言。\n"
                "Python语法简单，适合初学者入门。\n"
                "Python拥有丰富的第三方库，如numpy、pandas等。\n"
                "Python在数据分析、人工智能领域应用广泛。\n"
                "学习Python需要掌握基础语法、函数、类和模块。\n"
                "Python社区活跃，文档完善，学习资源丰富。\n"
                "Python的列表推导式和生成器让代码更简洁。\n"
                "Python支持面向对象和函数式编程范式。\n"
                "Python的异常处理机制让程序更健壮。\n"
                "Python的虚拟环境管理依赖非常方便。"
            ),
            "keywords": [],
        },
    ]

    try:
        # 测试单条处理
        print("\n[1/4] 测试单条处理...")
        single_result = processor.process_item(test_items[0])
        assert single_result.score > 50, f"评分应大于50，实际: {single_result.score}"
        assert 0.0 <= single_result.confidence <= 1.0, "置信度应在0-1之间"
        assert len(single_result.keywords) >= 2, "关键词数量应不少于2个"
        assert len(single_result.suggestions) > 0, "应有优化建议"
        print(f"  ✓ 单条处理通过 (评分: {single_result.score:.1f}, 置信度: {single_result.confidence:.2f})")

        # 测试批量处理
        print("[2/4] 测试批量处理...")
        batch_results = processor.process_batch(test_items)
        assert len(batch_results) == 2, "应返回2条结果"
        assert all(r.score > 0 for r in batch_results), "所有评分应大于0"
        print(f"  ✓ 批量处理通过 ({len(batch_results)} 条)")

        # 测试关键词提取
        print("[3/4] 测试关键词提取...")
        words = processor._extract_words(test_items[0]["content"])
        assert len(words) > 5, "应提取到多个候选词"
        filtered = processor._filter_keywords(words, min_freq=1)
        assert len(filtered) > 0, "过滤后应有关键词"
        print(f"  ✓ 关键词提取通过 (提取 {len(words)} 个候选词)")

        # 测试错误处理
        print("[4/4] 测试错误处理...")
        error_tests = [
            ({"content": ""}, "E002"),
            ({"content": "x" * 20000}, "E003"),
            ({"content": "短文本"}, "E004"),
        ]
        for bad_data, expected_code in error_tests:
            try:
                processor.process_item(bad_data)
                assert False, f"应抛出异常 {expected_code}"
            except SkillError as exc:
                assert exc.code == expected_code, f"错误码应为 {expected_code}，实际 {exc.code}"
        print("  ✓ 错误处理通过")

    except AssertionError as exc:
        print(f"\n✗ 自检失败: {exc}")
        return 1
    except SkillError as exc:
        print(f"\n✗ 自检失败: [{exc.code}] {exc.message}")
        return 1
    except Exception as exc:
        print(f"\n✗ 自检失败: 未知错误 {exc}")
        return 1

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="openseo-studio — SEO文案内容优化与关键词策略工具",
        prog="openseo-studio",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，无需外部依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入JSON文件路径（含 items 数组）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出JSON文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "--max-text-length",
        type=int,
        default=10000,
        help="单条文本最大长度（默认10000）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 需要输入文件
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest 自检")
        return 2

    try:
        # 读取输入
        with open(args.input, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        items = raw_data if isinstance(raw_data, list) else raw_data.get("items", [])
        if not items:
            raise SkillError("E002", "输入数据中缺少 items 数组")

        # 处理数据
        processor = SEOProcessor(max_text_length=args.max_text_length)
        results = processor.process_batch(items)

        # 构建输出
        output_data = {
            "success": True,
            "total": len(results),
            "results": [r.to_dict() for r in results],
        }

        # 输出
        output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
        else:
            print(output_str)

        return 0

    except SkillError as exc:
        print(f"错误: [{exc.code}] {exc.message}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"错误: [E006] JSON解析失败: {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"错误: [E001] 文件不存在: {exc}")
        return 1
    except Exception as exc:
        print(f"错误: [E010] 未知错误: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
