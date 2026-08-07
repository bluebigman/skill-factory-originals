#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autoresearch - 学术调研资料整理与信息结构化工具

本模块依据功能规格独立实现（clean-room），将用户提供的文本资料解析为
结构化结果，支持批量处理与置信度标注。

功能概述:
    - 输入文本解析为结构化条目
    - 自动提取关键信息（标题、作者、时间、数值等）
    - 置信度标注（高/中/低）
    - 批量处理多条输入
    - 输出格式支持 Markdown 与 JSON

错误码说明:
    E001: 参数错误（无效的命令行参数）
    E002: 输入数据为空或格式不正确
    E003: 文件读取失败
    E004: 输出写入失败
    E005: 内部处理异常
    E006: 不支持的输出格式
    E007: 数据解析失败（无法从文本中提取有效信息）
    E008: 批量处理时某一条目处理失败
    E009: 配置错误（无效的配置参数）
    E010: 未预期的运行时错误

用法示例:
    python main.py --input "某研究论文的文本内容" --format json
    python main.py --file input.txt --format markdown
    python main.py --selftest
"""

import argparse
import json
import re
import sys
import tempfile
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 支持的输出格式
SUPPORTED_FORMATS = ("json", "markdown")

# 默认输出字段
DEFAULT_FIELDS = ["title", "author", "date", "keywords", "summary", "confidence"]

# 字段占位符（信息缺失时使用）
PLACEHOLDER_TEMPLATE = "[需核实:{field}]"

# 解析正则表达式（用于关键信息提取）
PATTERN_TITLE = re.compile(r"(?:标题|题目|title)[：:\s]+(.+)", re.IGNORECASE)
PATTERN_AUTHOR = re.compile(r"(?:作者|作者[:：]|author)[：:\s]+(.+)", re.IGNORECASE)
PATTERN_DATE = re.compile(
    r"(?:日期|时间|date)[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    re.IGNORECASE,
)
PATTERN_KEYWORDS = re.compile(r"(?:关键词|关键字|keywords)[：:\s]+(.+)", re.IGNORECASE)
PATTERN_SENTENCE = re.compile(r"([^。！？\n]+[。！？])")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


class ResearchItem:
    """单条研究资料的结构化表示。"""

    def __init__(
        self,
        raw_text: str,
        title: str = "",
        author: str = "",
        date: str = "",
        keywords: List[str] = None,
        summary: str = "",
        confidence: str = CONFIDENCE_LOW,
    ) -> None:
        """
        初始化研究条目。

        Args:
            raw_text: 原始输入文本
            title: 提取的标题
            author: 提取的作者
            date: 提取的日期
            keywords: 提取的关键词列表
            summary: 生成的摘要
            confidence: 整体置信度（高/中/低）
        """
        self.raw_text = raw_text.strip()
        self.title = title or self._extract_title()
        self.author = author or self._extract_author()
        self.date = date or self._extract_date()
        self.keywords = keywords or self._extract_keywords()
        self.summary = summary or self._generate_summary()
        self.confidence = self._assess_confidence()

    def _extract_title(self) -> str:
        """从原始文本中提取标题。"""
        match = PATTERN_TITLE.search(self.raw_text)
        if match:
            return match.group(1).strip()
        # 若无显式标题，取第一句作为标题
        first_sentence = PATTERN_SENTENCE.search(self.raw_text)
        if first_sentence:
            return first_sentence.group(1).strip()[:50]
        # 取前 30 个字符作为标题
        return self.raw_text[:30] if self.raw_text else ""

    def _extract_author(self) -> str:
        """从原始文本中提取作者。"""
        match = PATTERN_AUTHOR.search(self.raw_text)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_date(self) -> str:
        """从原始文本中提取日期。"""
        match = PATTERN_DATE.search(self.raw_text)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_keywords(self) -> List[str]:
        """从原始文本中提取关键词。"""
        match = PATTERN_KEYWORDS.search(self.raw_text)
        if match:
            raw_keywords = match.group(1).strip()
            # 支持逗号、顿号、分号分隔
            keywords = re.split(r"[,，、;；]", raw_keywords)
            return [kw.strip() for kw in keywords if kw.strip()]
        return []

    def _generate_summary(self) -> str:
        """生成摘要（取前 2-3 个句子）。"""
        sentences = PATTERN_SENTENCE.findall(self.raw_text)
        if not sentences:
            return self.raw_text[:100]
        # 取前 3 个句子作为摘要
        summary = "".join(sentences[:3]).strip()
        return summary[:200]

    def _assess_confidence(self) -> str:
        """
        评估整体置信度。

        规则：
            - 高：标题、作者、日期、关键词均存在
            - 中：标题和至少一项其他信息存在
            - 低：仅标题或信息缺失
        """
        has_title = bool(self.title)
        has_author = bool(self.author)
        has_date = bool(self.date)
        has_keywords = bool(self.keywords)

        if has_title and has_author and has_date and has_keywords:
            return CONFIDENCE_HIGH
        if has_title and (has_author or has_date or has_keywords):
            return CONFIDENCE_MEDIUM
        return CONFIDENCE_LOW

    def to_dict(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        转换为字典。

        Args:
            fields: 需要输出的字段列表，None 表示输出所有字段

        Returns:
            结构化字典
        """
        if fields is None:
            fields = DEFAULT_FIELDS

        data: Dict[str, Any] = {}
        for field in fields:
            if field == "title":
                data["title"] = self.title or PLACEHOLDER_TEMPLATE.format(field="标题")
            elif field == "author":
                data["author"] = self.author or PLACEHOLDER_TEMPLATE.format(field="作者")
            elif field == "date":
                data["date"] = self.date or PLACEHOLDER_TEMPLATE.format(field="日期")
            elif field == "keywords":
                data["keywords"] = self.keywords or [PLACEHOLDER_TEMPLATE.format(field="关键词")]
            elif field == "summary":
                data["summary"] = self.summary or PLACEHOLDER_TEMPLATE.format(field="摘要")
            elif field == "confidence":
                data["confidence"] = self.confidence
            else:
                # 未知字段：尝试从原始文本中提取
                data[field] = self._extract_custom_field(field)
        return data

    def _extract_custom_field(self, field: str) -> str:
        """从原始文本中提取自定义字段（简单模式匹配）。"""
        pattern = re.compile(rf"{field}[：:\s]+(.+)", re.IGNORECASE)
        match = pattern.search(self.raw_text)
        if match:
            return match.group(1).strip()
        return PLACEHOLDER_TEMPLATE.format(field=field)

    def __repr__(self) -> str:
        return f"ResearchItem(title={self.title!r}, confidence={self.confidence!r})"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------


def parse_text(text: str, fields: Optional[List[str]] = None) -> ResearchItem:
    """
    将单条文本解析为结构化研究条目。

    Args:
        text: 输入文本
        fields: 输出字段列表（用于验证）

    Returns:
        ResearchItem 实例

    Raises:
        ValueError: 当输入文本为空或过短时
    """
    if not text or not text.strip():
        raise ValueError("输入文本为空")

    if len(text.strip()) < 5:
        raise ValueError("输入文本过短，无法提取有效信息")

    item = ResearchItem(text)
    return item


def parse_batch(texts: List[str], fields: Optional[List[str]] = None) -> List[ResearchItem]:
    """
    批量解析多条文本。

    Args:
        texts: 输入文本列表
        fields: 输出字段列表

    Returns:
        ResearchItem 列表

    Raises:
        ValueError: 当输入列表为空时
    """
    if not texts:
        raise ValueError("输入列表为空")

    results = []
    for text in texts:
        try:
            item = parse_text(text, fields)
            results.append(item)
        except ValueError as exc:
            # 单条失败不影响整体，跳过并记录
            results.append(
                ResearchItem(
                    text if text else "",
                    title="[解析失败]",
                    summary=str(exc),
                    confidence=CONFIDENCE_LOW,
                )
            )
    return results


def to_json(items: Union[ResearchItem, List[ResearchItem]], fields: Optional[List[str]] = None) -> str:
    """
    将研究条目转换为 JSON 字符串。

    Args:
        items: 单个条目或条目列表
        fields: 输出字段列表

    Returns:
        JSON 格式的字符串
    """
    if isinstance(items, ResearchItem):
        data = items.to_dict(fields)
    else:
        data = [item.to_dict(fields) for item in items]

    return json.dumps(data, ensure_ascii=False, indent=2)


def to_markdown(items: Union[ResearchItem, List[ResearchItem]], fields: Optional[List[str]] = None) -> str:
    """
    将研究条目转换为 Markdown 表格。

    Args:
        items: 单个条目或条目列表
        fields: 输出字段列表

    Returns:
        Markdown 格式的字符串
    """
    if fields is None:
        fields = DEFAULT_FIELDS

    if isinstance(items, ResearchItem):
        items = [items]

    # 生成表头
    header = "| " + " | ".join(fields) + " |"
    separator = "|" + "|".join(["---"] * len(fields)) + "|"

    # 生成数据行
    rows = []
    for item in items:
        data = item.to_dict(fields)
        row_values = []
        for field in fields:
            value = data.get(field, "")
            if isinstance(value, list):
                value = ", ".join(value)
            # 转义 Markdown 特殊字符
            value = str(value).replace("|", "\\|").replace("\n", " ")
            row_values.append(value)
        rows.append("| " + " | ".join(row_values) + " |")

    # 组合 Markdown 表格
    markdown_table = "\n".join([header, separator] + rows)
    return markdown_table


def process_input(
    input_text: Optional[str] = None,
    input_file: Optional[str] = None,
    output_format: str = "json",
    fields: Optional[List[str]] = None,
) -> str:
    """
    处理输入并生成结构化输出。

    Args:
        input_text: 直接输入的文本
        input_file: 输入文件路径
        output_format: 输出格式（json 或 markdown）
        fields: 输出字段列表

    Returns:
        结构化结果字符串

    Raises:
        ValueError: 参数错误或处理失败
        FileNotFoundError: 文件不存在
        IOError: 文件读取失败
    """
    # 参数校验
    if not input_text and not input_file:
        raise ValueError("必须提供 input_text 或 input_file 之一")

    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(f"不支持的输出格式: {output_format}，支持: {SUPPORTED_FORMATS}")

    # 读取输入
    if input_file:
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {input_file}")
        except IOError as exc:
            raise IOError(f"文件读取失败: {exc}")
    else:
        content = input_text or ""

    # 按空行或换行分割为多条（支持批量）
    # 简单策略：若包含明显的分隔符（如多个段落），按段落分割
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        # 批量处理
        items = parse_batch(paragraphs, fields)
    else:
        # 单条处理
        try:
            item = parse_text(content, fields)
            items = item
        except ValueError as exc:
            raise ValueError(f"输入解析失败: {exc}")

    # 生成输出
    if output_format == "json":
        return to_json(items, fields)
    else:
        return to_markdown(items, fields)


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------


def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件或网络。

    Returns:
        True 表示自检通过，否则抛出异常
    """
    print("=" * 60)
    print("autoresearch 自检开始")
    print("=" * 60)

    # 测试样例数据（硬编码，不依赖外部）
    sample_texts = [
        "标题：人工智能在医疗影像诊断中的应用研究\n"
        "作者：张三\n"
        "日期：2024年3月15日\n"
        "关键词：深度学习, 医学影像, 诊断\n"
        "本文探讨了深度学习技术在医疗影像诊断中的最新进展。"
        "研究结果表明，基于卷积神经网络的模型在多种疾病检测中表现出色。"
        "该技术有望在未来大幅提升诊断效率和准确性。",

        "标题：区块链技术在供应链管理中的应用\n"
        "作者：李四、王五\n"
        "日期：2023年11月\n"
        "关键词：区块链；供应链；追溯\n"
        "本文分析了区块链技术在供应链管理中的潜在应用场景。"
        "通过分布式账本技术，可以实现产品全生命周期的透明追溯。"
        "研究指出该技术仍面临扩展性和隐私保护等挑战。",

        "这是一段没有明确结构的文本，仅包含一些描述性内容。"
        "其中提到了一些关于数据分析和机器学习的讨论。"
        "但缺少明确的标题、作者和日期信息。",
    ]

    # 测试 1: 单条解析
    print("\n[测试 1] 单条文本解析")
    try:
        item = parse_text(sample_texts[0])
        assert item.title, "标题不应为空"
        assert item.author, "作者不应为空"
        assert item.date, "日期不应为空"
        assert len(item.keywords) >= 2, "关键词数量应至少为 2"
        assert item.confidence == CONFIDENCE_HIGH, "置信度应为高"
        print("  通过：单条解析成功")
        print(f"  标题: {item.title}")
        print(f"  作者: {item.author}")
        print(f"  日期: {item.date}")
        print(f"  关键词: {item.keywords}")
        print(f"  置信度: {item.confidence}")
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return False

    # 测试 2: 批量解析
    print("\n[测试 2] 批量文本解析")
    try:
        items = parse_batch(sample_texts)
        assert len(items) == 3, "应解析出 3 条结果"
        assert items[0].confidence == CONFIDENCE_HIGH, "第一条置信度应为高"
        assert items[2].confidence == CONFIDENCE_LOW, "第三条置信度应为低"
        print("  通过：批量解析成功")
        print(f"  条目数: {len(items)}")
        print(f"  各条置信度: {[item.confidence for item in items]}")
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return False

    # 测试 3: JSON 输出
    print("\n[测试 3] JSON 输出")
    try:
        json_str = to_json(items)
        json_data = json.loads(json_str)
        assert isinstance(json_data, list), "JSON 应为列表"
        assert len(json_data) == 3, "JSON 列表长度应为 3"
        assert "title" in json_data[0], "应包含 title 字段"
        print("  通过：JSON 输出有效")
        print(f"  输出长度: {len(json_str)} 字符")
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"  失败：{exc}")
        return False

    # 测试 4: Markdown 输出
    print("\n[测试 4] Markdown 输出")
    try:
        md_str = to_markdown(items)
        assert "|" in md_str, "Markdown 应包含表格"
        assert "---" in md_str, "Markdown 应包含分隔线"
        print("  通过：Markdown 输出有效")
        print(f"  输出长度: {len(md_str)} 字符")
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return False

    # 测试 5: 自定义字段
    print("\n[测试 5] 自定义字段输出")
    try:
        custom_fields = ["title", "author", "confidence"]
        item_dict = items[0].to_dict(custom_fields)
        assert set(item_dict.keys()) == set(custom_fields), "字段集合应匹配"
        print("  通过：自定义字段输出正常")
        print(f"  字段: {list(item_dict.keys())}")
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return False

    # 测试 6: 占位符处理
    print("\n[测试 6] 信息缺失占位符")
    try:
        item_dict = items[2].to_dict()
        # 第三条缺少作者和日期，应生成占位符
        assert item_dict["author"].startswith("[需核实"), "作者应使用占位符"
        assert item_dict["date"].startswith("[需核实"), "日期应使用占位符"
        print("  通过：占位符生成正确")
        print(f"  作者占位: {item_dict['author']}")
        print(f"  日期占位: {item_dict['date']}")
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return False

    # 测试 7: 完整处理流程
    print("\n[测试 7] 完整处理流程")
    try:
        # 使用临时文件测试文件输入（使用系统临时目录，不依赖当前工作目录）
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write(sample_texts[0])
            tmp_path = tmp.name

        try:
            result = process_input(input_file=tmp_path, output_format="json")
            result_data = json.loads(result)
            assert isinstance(result_data, dict), "单条输入应返回单个对象"
            assert result_data["title"], "标题不应为空"
            print("  通过：文件输入处理成功")
            print(f"  标题: {result_data['title']}")
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except (AssertionError, json.JSONDecodeError, Exception) as exc:
        print(f"  失败：{exc}")
        return False

    # 测试 8: 错误处理
    print("\n[测试 8] 错误处理")
    try:
        # 空输入
        try:
            parse_text("")
            print("  失败：空输入应抛出异常")
            return False
        except ValueError:
            pass

        # 无效格式
        try:
            process_input(input_text="测试内容", output_format="xml")
            print("  失败：无效格式应抛出异常")
            return False
        except ValueError:
            pass

        # 无输入
        try:
            process_input()
            print("  失败：无输入应抛出异常")
            return False
        except ValueError:
            pass

        print("  通过：错误处理正常")
    except Exception as exc:
        print(f"  失败：{exc}")
        return False

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main() -> int:
    """
    命令行主入口。

    Returns:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="autoresearch - 学术调研资料整理与信息结构化工具",
        epilog="示例: python main.py --input '文本内容' --format json",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="直接输入的文本内容",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="输入文件路径（支持批量处理，按空行分隔）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=SUPPORTED_FORMATS,
        default="json",
        help=f"输出格式（默认: json，支持: {', '.join(SUPPORTED_FORMATS)}）",
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="输出字段列表，逗号分隔（默认: title,author,date,keywords,summary,confidence）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部数据）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as exc:
            print(f"自检执行异常: {exc}")
            return 1

    # 正常处理模式
    try:
        # 解析字段
        fields = None
        if args.fields:
            fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 处理输入
        result = process_input(
            input_text=args.input,
            input_file=args.file,
            output_format=args.format,
            fields=fields,
        )

        # 输出结果
        print(result)
        return 0

    except FileNotFoundError as exc:
        print(f"错误 E003: {exc}")
        return 3
    except ValueError as exc:
        print(f"错误 E001: {exc}")
        return 1
    except IOError as exc:
        print(f"错误 E004: {exc}")
        return 4
    except Exception as exc:
        print(f"错误 E010: 未预期错误 - {exc}")
        return 10


if __name__ == "__main__":
    sys.exit(main())
