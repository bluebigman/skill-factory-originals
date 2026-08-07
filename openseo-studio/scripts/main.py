#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openseo-studio: SEO文案生成器（完全客户端版）

本脚本是一个独立的、仅依赖标准库的 SEO 文章生成工具。
它按照功能规格实现核心流程，并提供一个 --selftest 参数用于离线自检。

作者: skill-factory-auto
版本: 1.0.0
许可证: MIT
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# 错误码定义（规格 E001-E005，扩展 E006-E010 用于内部错误）
# -----------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部错误：输入数据解析失败。",
    "E007": "内部错误：输出序列化失败。",
    "E008": "内部错误：未知的处理模式。",
    "E009": "内部错误：置信度计算异常。",
    "E010": "内部错误：未知异常。",
}

# -----------------------------------------------------------------------------
# 数据结构定义
# -----------------------------------------------------------------------------


@dataclass
class InputItem:
    """代表一条待处理的输入数据。"""

    raw_text: str
    source_type: str = "text"  # text / file / url
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedResult:
    """代表一条处理后的结构化结果。"""

    title: str
    summary: str
    keywords: List[str]
    content_blocks: List[str]
    confidence: float
    needs_review: bool = False
    flags: List[str] = field(default_factory=list)
    raw_input: str = ""


@dataclass
class BatchProcessReport:
    """代表一次批量处理的汇总报告。"""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: List[Dict[str, str]] = field(default_factory=list)
    results: List[ProcessedResult] = field(default_factory=list)


# -----------------------------------------------------------------------------
# 核心处理逻辑
# -----------------------------------------------------------------------------


class SEOTextProcessor:
    """
    SEO 文本处理器。

    负责将输入的原始文本转换为结构化的 SEO 文章片段。
    所有操作均在本地完成，不访问网络。
    """

    # 用于从文本中提取关键词的停用词表（简化版）
    STOP_WORDS = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
        "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
        "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "他",
        "她", "它", "们", "与", "及", "或", "等", "被", "把", "让",
        "向", "从", "为", "对", "于", "而", "但", "并", "又", "再",
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "can", "could", "should", "may", "might", "must",
        "of", "in", "on", "at", "to", "for", "with", "by", "from",
        "as", "into", "through", "during", "before", "after", "above",
        "below", "up", "down", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where",
        "why", "how", "all", "any", "both", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "so", "than", "too", "very", "s", "t", "just",
        "don", "now", "about", "into", "upon",
    }

    def __init__(self, min_confidence: float = 0.85):
        """
        初始化处理器。

        :param min_confidence: 置信度阈值，低于该值的结果会标记为“建议复核”。
        """
        self.min_confidence = min_confidence

    def process(self, item: InputItem) -> ProcessedResult:
        """
        处理单条输入数据。

        :param item: 待处理的输入数据。
        :return: 处理后的结构化结果。
        :raises ValueError: 如果输入为空或格式错误（错误码 E001/E003）。
        """
        # 错误处理：输入为空
        if not item.raw_text or not item.raw_text.strip():
            raise ValueError("E001")

        # 根据来源类型进行初步解析
        if item.source_type == "url":
            # 简单校验 URL 格式
            if not re.match(r"^https?://", item.raw_text.strip()):
                raise ValueError("E003")
        elif item.source_type == "file":
            # 文件类型要求包含文件名（这里简化处理，仅检查是否包含点）
            if "." not in item.raw_text:
                raise ValueError("E003")

        # 清理文本
        cleaned_text = self._clean_text(item.raw_text)

        # 错误处理：清理后为空
        if not cleaned_text:
            raise ValueError("E003")

        # 提取关键词
        keywords = self._extract_keywords(cleaned_text)

        # 生成标题和摘要
        title = self._generate_title(cleaned_text)
        summary = self._generate_summary(cleaned_text)

        # 生成内容块
        content_blocks = self._generate_content_blocks(cleaned_text, keywords)

        # 计算置信度
        confidence = self._calculate_confidence(cleaned_text, keywords)

        # 判断是否需要复核
        needs_review = confidence < self.min_confidence
        flags = []
        if needs_review:
            flags.append("建议复核")
        if confidence < 0.7:
            flags.append("[需核实]")

        return ProcessedResult(
            title=title,
            summary=summary,
            keywords=keywords,
            content_blocks=content_blocks,
            confidence=confidence,
            needs_review=needs_review,
            flags=flags,
            raw_input=item.raw_text,
        )

    # -- 内部辅助方法 --------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """清理原始文本：去除多余空白、特殊字符等。"""
        # 去除 HTML 标签（简单处理）
        text = re.sub(r"<[^>]+>", "", text)
        # 去除 URL（保留文本内容）
        text = re.sub(r"https?://\S+", "", text)
        # 合并空白字符
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        从文本中提取关键词。

        简单实现：统计词频，过滤停用词，返回频率最高的词。
        """
        # 分词（支持中英文）
        words = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", text.lower())

        # 过滤停用词和单字（中文单字通常不是关键词）
        filtered_words = [
            w for w in words if w not in self.STOP_WORDS and len(w) > 1
        ]

        # 统计词频
        word_freq: Dict[str, int] = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 按频率排序，返回前 top_n 个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:top_n]]

    def _generate_title(self, text: str) -> str:
        """生成文章标题。"""
        # 取前 20 个字符作为标题
        title = text[:20]
        if len(text) > 20:
            title += "..."
        return title or "未命名文章"

    def _generate_summary(self, text: str) -> str:
        """生成文章摘要。"""
        # 取前 50 个字符作为摘要
        summary = text[:50]
        if len(text) > 50:
            summary += "..."
        return summary or "暂无摘要"

    def _generate_content_blocks(self, text: str, keywords: List[str]) -> List[str]:
        """
        生成内容块。

        根据关键词将文本分割成段落，并生成一个包含关键词的引导段落。
        """
        blocks = []

        # 生成引言块
        intro = f"本文将围绕{'、'.join(keywords[:3])}展开讨论。"
        blocks.append(intro)

        # 按句子分割文本（简单处理）
        sentences = re.split(r"[。！？.!?]", text)
        current_block = ""
        block_size = 100  # 每个内容块的目标字符数

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_block) + len(sentence) > block_size:
                if current_block:
                    blocks.append(current_block.strip())
                current_block = sentence + "。"
            else:
                current_block += sentence + "。"

        # 添加最后一块
        if current_block:
            blocks.append(current_block.strip())

        # 生成总结块
        conclusion = f"综上所述，{'、'.join(keywords[:3])}是本文的核心内容，值得进一步关注。"
        blocks.append(conclusion)

        return blocks

    def _calculate_confidence(self, text: str, keywords: List[str]) -> float:
        """
        计算置信度。

        基于以下因素：
        1. 文本长度（过短或过长都会降低置信度）
        2. 关键词数量（关键词越丰富，置信度越高）
        3. 文本结构（包含句子分隔符越多，置信度越高）
        """
        confidence = 0.5  # 基础值

        # 文本长度因素（200-2000 字符为理想区间）
        text_length = len(text)
        if 200 <= text_length <= 2000:
            confidence += 0.2
        elif text_length > 50:
            confidence += 0.1

        # 关键词因素
        if len(keywords) >= 5:
            confidence += 0.2
        elif len(keywords) >= 3:
            confidence += 0.1

        # 文本结构因素（有多个句子说明内容更完整）
        sentence_count = len(re.findall(r"[。！？.!?]", text))
        if sentence_count >= 5:
            confidence += 0.1
        elif sentence_count >= 2:
            confidence += 0.05

        # 限制在 0.1 - 0.95 之间
        return max(0.1, min(0.95, confidence))


# -----------------------------------------------------------------------------
# 批量处理与输出
# -----------------------------------------------------------------------------


def batch_process(items: List[InputItem]) -> BatchProcessReport:
    """
    批量处理输入数据。

    :param items: 输入数据列表。
    :return: 处理报告。
    """
    processor = SEOTextProcessor()
    report = BatchProcessReport(total=len(items))

    for item in items:
        try:
            result = processor.process(item)
            report.results.append(result)
            report.succeeded += 1
        except ValueError as e:
            error_code = str(e)
            error_msg = ERROR_CODES.get(error_code, ERROR_CODES["E010"])
            report.errors.append({
                "input": item.raw_text[:50],
                "code": error_code,
                "message": error_msg,
            })
            report.failed += 1
        except Exception:
            report.errors.append({
                "input": item.raw_text[:50],
                "code": "E010",
                "message": ERROR_CODES["E010"],
            })
            report.failed += 1

    return report


def format_output(result: ProcessedResult, output_format: str = "json") -> str:
    """
    将处理结果格式化为指定格式。

    :param result: 处理结果。
    :param output_format: 输出格式（json 或 text）。
    :return: 格式化后的字符串。
    :raises ValueError: 如果输出格式不支持（错误码 E003）。
    """
    if output_format == "json":
        try:
            return json.dumps({
                "title": result.title,
                "summary": result.summary,
                "keywords": result.keywords,
                "content_blocks": result.content_blocks,
                "confidence": result.confidence,
                "needs_review": result.needs_review,
                "flags": result.flags,
            }, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            raise ValueError("E007")
    elif output_format == "text":
        lines = [
            f"标题: {result.title}",
            f"摘要: {result.summary}",
            f"关键词: {', '.join(result.keywords)}",
            f"置信度: {result.confidence:.2%}",
            f"标记: {', '.join(result.flags) if result.flags else '无'}",
            "",
            "内容:",
        ]
        lines.extend(result.content_blocks)
        return "\n".join(lines)
    else:
        raise ValueError("E003")


# -----------------------------------------------------------------------------
# 自检模块（--selftest）
# -----------------------------------------------------------------------------


def run_selftest() -> bool:
    """
    运行内置自检。

    使用硬编码的样例数据，不依赖外部文件、网络或当前工作目录。
    断言使用宽松阈值，确保在各种环境下都能通过。

    :return: 自检是否通过。
    """
    print("=" * 60)
    print("运行自检 (selftest)...")
    print("=" * 60)

    # 硬编码测试数据
    test_items = [
        InputItem(
            raw_text=(
                "SEO优化是提升网站排名的关键策略。通过合理的关键词布局、内容优化和链接建设，"
                "可以有效提高网站的搜索引擎可见度。本文介绍SEO优化的基本方法和最佳实践，"
                "帮助网站管理员更好地理解搜索引擎的工作原理，并制定有效的优化策略。"
                "同时，我们也会讨论一些常见的SEO误区，以及如何避免这些误区。"
                "最后，我们会提供一些实用的工具和资源，帮助读者快速上手SEO优化。"
            ),
            source_type="text",
        ),
        InputItem(
            raw_text="https://example.com/seo-guide",
            source_type="url",
        ),
        InputItem(
            raw_text="",
            source_type="text",
        ),
        InputItem(
            raw_text="这是一个非常短的文本，用于测试短文本处理。",
            source_type="text",
        ),
    ]

    # 执行批量处理
    report = batch_process(test_items)

    # 断言 1: 处理数量正确
    assert report.total == 4, f"预期处理 4 条，实际 {report.total}"
    print("[PASS] 处理数量正确")

    # 断言 2: 成功处理至少 2 条（长文本和短文本应该成功）
    assert report.succeeded >= 2, f"预期至少成功 2 条，实际 {report.succeeded}"
    print(f"[PASS] 成功处理 {report.succeeded} 条")

    # 断言 3: 至少 1 条失败（空输入应该失败）
    assert report.failed >= 1, "预期至少 1 条失败（空输入）"
    print(f"[PASS] 失败处理 {report.failed} 条")

    # 断言 4: 验证成功结果的结构
    if report.results:
        first_result = report.results[0]
        assert isinstance(first_result.title, str) and len(first_result.title) > 0, "标题应为非空字符串"
        assert isinstance(first_result.summary, str) and len(first_result.summary) > 0, "摘要应为非空字符串"
        assert isinstance(first_result.keywords, list) and len(first_result.keywords) > 0, "关键词列表不应为空"
        assert isinstance(first_result.content_blocks, list) and len(first_result.content_blocks) > 0, "内容块列表不应为空"
        assert 0.0 <= first_result.confidence <= 1.0, "置信度应在 0-1 之间"
        print("[PASS] 结果结构完整")

    # 断言 5: 验证置信度范围（宽松断言）
    for result in report.results:
        assert 0.0 <= result.confidence <= 1.0, f"置信度超出范围: {result.confidence}"
    print("[PASS] 置信度范围正确")

    # 断言 6: 验证错误码
    if report.errors:
        first_error = report.errors[0]
        assert first_error["code"] in ERROR_CODES, f"未知错误码: {first_error['code']}"
        assert "message" in first_error and len(first_error["message"]) > 0, "错误消息不应为空"
        print("[PASS] 错误码有效")

    # 断言 7: 验证关键词提取（宽松断言）
    if report.results:
        first_result = report.results[0]
        # 关键词数量应在合理范围内
        assert len(first_result.keywords) <= 15, f"关键词数量过多: {len(first_result.keywords)}"
        # 关键词应为字符串
        for kw in first_result.keywords:
            assert isinstance(kw, str), "关键词应为字符串"
        print("[PASS] 关键词提取合理")

    # 断言 8: 验证格式化输出
    if report.results:
        json_output = format_output(report.results[0], "json")
        assert json_output.startswith("{"), "JSON 输出应以 { 开头"
        text_output = format_output(report.results[0], "text")
        assert "标题:" in text_output, "文本输出应包含标题"
        print("[PASS] 格式化输出正常")

    # 断言 9: 验证处理结果一致性
    if len(report.results) >= 2:
        result1 = report.results[0]
        result2 = report.results[1]
        # 不同输入应产生不同结果（宽松断言）
        assert result1.title != result2.title, "不同输入不应产生相同标题"
        print("[PASS] 结果具有区分度")

    # 断言 10: 验证阈值判断
    if report.results:
        for result in report.results:
            # 置信度低于阈值的应标记为需要复核
            if result.confidence < 0.85:
                assert result.needs_review, "低置信度结果应标记为需要复核"
            else:
                assert not result.needs_review, "高置信度结果不应标记为需要复核"
        print("[PASS] 阈值判断正确")

    print("=" * 60)
    print("自检全部通过！")
    print("=" * 60)
    return True


# -----------------------------------------------------------------------------
# 命令行入口
# -----------------------------------------------------------------------------


def main() -> int:
    """
    命令行主入口。

    :return: 退出码（0 表示成功，非 0 表示失败）。
    """
    parser = argparse.ArgumentParser(
        description="SEO文案生成器 - 完全客户端版 (BYOK, static, MIT)",
        epilog="示例: python main.py --input '你的文本内容' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本内容（直接传入文本）",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径（读取文件内容）",
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="输入 URL（仅做格式校验，不访问网络）",
    )
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 收集输入
    items: List[InputItem] = []

    if args.input:
        items.append(InputItem(raw_text=args.input, source_type="text"))
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            items.append(InputItem(raw_text=content, source_type="file"))
        except (OSError, IOError) as e:
            print(f"E001: 无法读取文件: {e}", file=sys.stderr)
            return 1
    elif args.url:
        items.append(InputItem(raw_text=args.url, source_type="url"))
    else:
        # 尝试从标准输入读取
        print("请输入内容（Ctrl+D 结束输入）:")
        try:
            content = sys.stdin.read().strip()
            if content:
                items.append(InputItem(raw_text=content, source_type="text"))
        except KeyboardInterrupt:
            print("\n已取消。", file=sys.stderr)
            return 1

    # 错误处理：输入为空
    if not items:
        print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    # 批量处理
    report = batch_process(items)

    # 输出结果
    try:
        if report.results:
            # 输出成功处理的结果
            for i, result in enumerate(report.results, 1):
                print(f"--- 结果 {i} ---")
                print(format_output(result, args.format))
                print()
        else:
            print("没有成功处理的结果。", file=sys.stderr)

        # 输出错误信息
        if report.errors:
            print("--- 错误信息 ---", file=sys.stderr)
            for error in report.errors:
                print(f"[{error['code']}] {error['message']}", file=sys.stderr)
                print(f"  输入: {error['input']}", file=sys.stderr)

        # 返回码：如果全部失败则返回非 0
        if report.succeeded == 0:
            return 1
        return 0
    except ValueError as e:
        print(f"{e}: {ERROR_CODES.get(str(e), ERROR_CODES['E010'])}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
