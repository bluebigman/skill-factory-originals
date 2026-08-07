#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — SEO文案生成器（clean-room 独立实现）

本脚本基于功能规格独立编写，不复制任何既有代码。
提供核心的 SEO 文章生成逻辑，支持命令行调用与离线自检。

依赖：仅标准库（无需 pip install）
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import Counter


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容（数据/文件内容/URL 文本）。",
    "E002": "关键信息缺失，请补充：标题或正文关键字。",
    "E003": "输入格式错误，示例：JSON 对象或 '标题|正文' 格式。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定，请提供更多上下文。",
    "E006": "内部处理异常，请检查输入数据。",
    "E007": "参数错误，请检查命令行参数。",
    "E008": "输出写入失败。",
    "E009": "批量处理时单条数据失败。",
    "E010": "未知错误。",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ArticleInput:
    """输入数据模型"""
    title: str = ""
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.title.strip() or self.content.strip())


@dataclass
class ArticleResult:
    """输出结果模型"""
    title: str = ""
    meta_description: str = ""
    body: str = ""
    keywords: List[str] = field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "meta_description": self.meta_description,
            "body": self.body,
            "keywords": self.keywords,
            "confidence": round(self.confidence, 2),
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心解析与生成逻辑
# ---------------------------------------------------------------------------
class SEOArticleGenerator:
    """SEO 文章生成器核心类"""

    def __init__(self) -> None:
        # 停用词表（用于关键词提取）
        self._stopwords = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "么",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "to", "of", "in", "that", "it", "for", "on", "with", "as",
            "and", "or", "but", "not", "no", "so", "if", "then", "than",
        }

    # -- 输入解析 ----------------------------------------------------------
    def parse_input(self, raw_text: str) -> ArticleInput:
        """
        解析输入文本。
        支持三种格式：
          1. JSON 字符串：{"title": "...", "content": "...", "keywords": [...]}
          2. 普通文本：第一行为标题，其余为正文内容
          3. 管道分隔格式：标题|正文
        """
        if not raw_text or not raw_text.strip():
            raise ValueError(ERROR_CODES["E001"])

        text = raw_text.strip()

        # 尝试 JSON 解析
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if not isinstance(data, dict):
                    raise ValueError(ERROR_CODES["E003"])
                return ArticleInput(
                    title=str(data.get("title", "")),
                    content=str(data.get("content", "")),
                    keywords=[str(k) for k in data.get("keywords", [])],
                    extra=data.get("extra", {}),
                )
            except json.JSONDecodeError:
                raise ValueError(ERROR_CODES["E003"])

        # 尝试管道分隔格式
        if "|" in text:
            parts = text.split("|", 1)
            title = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            return ArticleInput(title=title, content=content)

        # 普通文本格式：第一行标题，其余正文
        lines = text.splitlines()
        title = lines[0].strip() if lines else ""
        content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        return ArticleInput(title=title, content=content)

    # -- 关键词提取 --------------------------------------------------------
    def extract_keywords(self, text: str, limit: int = 5) -> List[str]:
        """从文本中提取关键词（基于词频统计，去除停用词）"""
        if not text:
            return []

        # 中文分词（提取2-4字的中文词）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        # 英文单词提取
        english_words = re.findall(r'[a-zA-Z]{3,}', text.lower())

        # 统计词频
        word_count = Counter()
        for word in chinese_words + english_words:
            word_lower = word.lower()
            if word_lower not in self._stopwords:
                word_count[word] += 1

        # 按词频排序，取前 N 个
        sorted_words = word_count.most_common(limit)
        return [word for word, _ in sorted_words]

    # -- 置信度计算 --------------------------------------------------------
    def calculate_confidence(self, article_input: ArticleInput) -> tuple[float, List[str]]:
        """
        计算置信度（0-100）及警告信息。
        规则：
          - 有标题且长度≥5：+40 分
          - 有正文且长度≥50：+40 分
          - 有关键词：+20 分
          - 标题过短/正文过短：降低置信度
        """
        confidence = 0.0
        warnings: List[str] = []

        # 标题评估
        title_len = len(article_input.title.strip())
        if title_len >= 5:
            confidence += 40
        elif title_len > 0:
            confidence += 15
            warnings.append("标题过短，建议补充更多信息")

        # 正文评估
        content_len = len(article_input.content.strip())
        if content_len >= 50:
            confidence += 40
        elif content_len > 0:
            confidence += 10
            warnings.append("正文内容较少，建议补充更多细节")
        else:
            warnings.append("缺少正文内容")

        # 关键词评估
        if article_input.keywords:
            confidence += 20
        else:
            # 尝试从内容提取
            extracted = self.extract_keywords(article_input.content)
            if extracted:
                confidence += 10
                warnings.append("关键词由系统提取，建议人工确认")

        # 完整性检查
        if not article_input.title.strip():
            warnings.append("缺少标题")
        if not article_input.content.strip():
            warnings.append("缺少正文")

        return min(confidence, 100), warnings

    # -- 正文生成 ----------------------------------------------------------
    def generate_body(self, article_input: ArticleInput) -> str:
        """根据输入生成 SEO 文章正文"""
        content = article_input.content.strip()
        keywords = article_input.keywords or self.extract_keywords(content)

        # 构建段落
        paragraphs: List[str] = []

        # 引言段落
        intro = f"本文将围绕“{article_input.title}”展开讨论"
        if keywords:
            intro += f"，重点关注{'、'.join(keywords[:3])}等关键词"
        intro += "，为读者提供有价值的参考信息。"
        paragraphs.append(intro)

        # 正文段落（基于输入内容拆分）
        if content:
            # 按句号拆分，合并为段落
            sentences = re.split(r'[。！？!?]', content)
            current_para = ""
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if len(current_para) + len(sent) > 100:
                    if current_para:
                        paragraphs.append(current_para + "。")
                    current_para = sent
                else:
                    current_para += sent + "。"
            if current_para:
                paragraphs.append(current_para)
        else:
            # 如果没有正文，生成一些基于标题的内容
            title_words = self.extract_keywords(article_input.title, limit=3)
            if title_words:
                paragraphs.append(f"在当今数字化时代，{title_words[0]}已成为人们关注的焦点。")
                paragraphs.append("本文将深入探讨这一主题，为您带来全面的分析和见解。")

        # 总结段落
        summary = "综上所述"
        if keywords:
            summary += f"，围绕{'、'.join(keywords[:2])}的核心内容已进行梳理"
        summary += "。如需进一步探讨或有其他问题，欢迎继续交流。"
        paragraphs.append(summary)

        return "\n\n".join(paragraphs)

    # -- 元描述生成 --------------------------------------------------------
    def generate_meta_description(self, article_input: ArticleInput) -> str:
        """生成 SEO 元描述"""
        title = article_input.title.strip()
        keywords = article_input.keywords or self.extract_keywords(article_input.content)

        if title and keywords:
            return f"{title}——深入解析{'、'.join(keywords[:3])}等关键要点，提供实用信息与专业视角。"
        elif title:
            return f"{title}——为您提供全面、专业的资讯内容。"
        else:
            return "本文提供专业的资讯内容，涵盖多个关键主题。"

    # -- 主流程 ------------------------------------------------------------
    def generate(self, raw_input: str) -> ArticleResult:
        """
        主生成流程：
        1. 解析输入
        2. 校验关键信息
        3. 生成内容
        4. 计算置信度
        """
        # 解析输入
        article_input = self.parse_input(raw_input)

        # 校验关键信息
        if not article_input.title.strip():
            raise ValueError(ERROR_CODES["E002"])

        # 生成内容
        result = ArticleResult()
        result.title = article_input.title.strip()
        result.meta_description = self.generate_meta_description(article_input)
        result.body = self.generate_body(article_input)

        # 关键词处理
        if article_input.keywords:
            result.keywords = article_input.keywords
        else:
            result.keywords = self.extract_keywords(article_input.content)

        # 置信度
        result.confidence, result.warnings = self.calculate_confidence(article_input)

        return result

    # -- 批量处理 ----------------------------------------------------------
    def generate_batch(self, raw_inputs: List[str]) -> List[Dict[str, Any]]:
        """批量处理多个输入"""
        results = []
        for i, raw in enumerate(raw_inputs):
            try:
                result = self.generate(raw)
                results.append(result.to_dict())
            except ValueError as e:
                # 单条失败不影响其他
                results.append({
                    "error": str(e),
                    "index": i,
                    "confidence": 0,
                })
        return results


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读取外部文件、不依赖工作目录、不访问网络。
    """
    print("[SELFTEST] 开始自检...")
    generator = SEOArticleGenerator()

    # 测试样例 1：完整输入
    sample1 = {
        "title": "Python 编程入门指南",
        "content": "Python 是一种简单易学的编程语言，适合初学者入门。"
                   "它拥有丰富的库和框架，可以用于数据分析、人工智能、Web 开发等多个领域。"
                   "本文介绍 Python 的基础语法和常用工具，帮助读者快速上手。",
        "keywords": ["Python", "编程", "入门"],
    }
    raw1 = json.dumps(sample1, ensure_ascii=False)

    try:
        result1 = generator.generate(raw1)
        # 宽松断言：只检查存在性和大致范围
        assert result1.title == "Python 编程入门指南", "标题解析失败"
        assert len(result1.body) > 50, "正文生成过短"
        assert len(result1.keywords) > 0, "关键词提取失败"
        assert result1.confidence > 50, "置信度计算异常偏低"
        print("[SELFTEST] 样例1（完整输入）通过 ✓")
    except AssertionError as e:
        print(f"[SELFTEST] 样例1失败: {e}")
        return 1
    except ValueError as e:
        print(f"[SELFTEST] 样例1异常: {e}")
        return 1

    # 测试样例 2：纯文本输入
    raw2 = "SEO优化实践技巧\n搜索引擎优化是提升网站流量的重要手段。"
    try:
        result2 = generator.generate(raw2)
        assert result2.title == "SEO优化实践技巧", "纯文本标题解析失败"
        assert result2.confidence >= 0, "置信度应为非负数"
        print("[SELFTEST] 样例2（纯文本输入）通过 ✓")
    except AssertionError as e:
        print(f"[SELFTEST] 样例2失败: {e}")
        return 1
    except ValueError as e:
        print(f"[SELFTEST] 样例2异常: {e}")
        return 1

    # 测试样例 3：管道分隔格式
    raw3 = "Web开发技术|这是一段关于Web开发的技术介绍文本，包含前端和后端的内容。"
    try:
        result3 = generator.generate(raw3)
        assert result3.title == "Web开发技术", "管道分隔格式标题解析失败"
        assert result3.confidence > 0, "置信度应为正数"
        print("[SELFTEST] 样例3（管道分隔格式）通过 ✓")
    except AssertionError as e:
        print(f"[SELFTEST] 样例3失败: {e}")
        return 1
    except ValueError as e:
        print(f"[SELFTEST] 样例3异常: {e}")
        return 1

    # 测试样例 4：错误处理（空输入）
    try:
        generator.generate("")
        print("[SELFTEST] 样例4失败：空输入未抛出异常")
        return 1
    except ValueError as e:
        assert "E001" in str(e), "错误码不正确"
        print("[SELFTEST] 样例4（空输入错误处理）通过 ✓")

    # 测试样例 5：批量处理
    batch_inputs = [
        json.dumps(sample1, ensure_ascii=False),
        "简单标题\n简单正文内容",
        "",  # 应失败
    ]
    try:
        batch_results = generator.generate_batch(batch_inputs)
        assert len(batch_results) == 3, "批量结果数量不对"
        # 前两条应成功，第三条应失败
        assert "error" not in batch_results[0], "第一条批量处理失败"
        assert "error" not in batch_results[1], "第二条批量处理失败"
        assert "error" in batch_results[2], "第三条应包含错误"
        print("[SELFTEST] 样例5（批量处理）通过 ✓")
    except Exception as e:
        print(f"[SELFTEST] 样例5异常: {e}")
        return 1

    # 测试样例 6：关键词提取
    try:
        keywords = generator.extract_keywords("Python 是优秀的编程语言，Python 社区活跃", limit=3)
        assert len(keywords) > 0, "关键词提取为空"
        print("[SELFTEST] 样例6（关键词提取）通过 ✓")
    except AssertionError as e:
        print(f"[SELFTEST] 样例6失败: {e}")
        return 1

    # 测试样例 7：缺少标题的错误处理
    try:
        generator.generate(json.dumps({"content": "只有正文内容"}))
        print("[SELFTEST] 样例7失败：缺少标题未抛出异常")
        return 1
    except ValueError as e:
        assert "E002" in str(e), "错误码不正确"
        print("[SELFTEST] 样例7（缺少标题错误处理）通过 ✓")

    # 测试样例 8：基本功能完整性
    try:
        result = generator.generate("测试标题\n这是测试正文内容。包含足够多的文字用于测试。")
        assert result.title == "测试标题"
        assert result.meta_description, "元描述应为非空"
        assert result.body, "正文应为非空"
        assert isinstance(result.keywords, list), "关键词应为列表"
        assert isinstance(result.confidence, float), "置信度应为浮点数"
        print("[SELFTEST] 样例8（功能完整性）通过 ✓")
    except AssertionError as e:
        print(f"[SELFTEST] 样例8失败: {e}")
        return 1

    print("[SELFTEST] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SEO文案生成器 - 基于输入的标题和内容生成 SEO 文章",
        epilog="示例: python main.py --input '标题|正文内容' 或 --input '{\"title\":\"...\",\"content\":\"...\"}'"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容，支持 JSON 字符串、'标题|正文' 格式或纯文本"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，输入 JSON 数组字符串"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（可选，默认输出到 stdout）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input and not args.batch:
        print(f"[错误] {ERROR_CODES['E007']}", file=sys.stderr)
        print("请使用 --input 或 --batch 提供输入内容，或使用 --selftest 运行自检。", file=sys.stderr)
        return 1

    generator = SEOArticleGenerator()

    try:
        # 批量模式
        if args.batch:
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    raise ValueError("批量输入应为 JSON 数组")
            except json.JSONDecodeError:
                print(f"[错误] {ERROR_CODES['E003']}", file=sys.stderr)
                return 1

            results = generator.generate_batch([str(item) for item in batch_data])
            output_text = json.dumps(results, ensure_ascii=False, indent=2)

        # 单条模式
        else:
            result = generator.generate(args.input)
            output_text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_text)
                print(f"结果已写入: {args.output}")
            except OSError:
                print(f"[错误] {ERROR_CODES['E008']}", file=sys.stderr)
                return 1
        else:
            print(output_text)

        return 0

    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[错误] {ERROR_CODES['E010']}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
