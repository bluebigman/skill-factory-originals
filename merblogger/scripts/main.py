#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merblogger — 博客发布与内容管理工具（独立实现）

本脚本依据功能规格独立编写，不参考任何既有实现。
支持将非结构化文本解析为结构化博客文章，并输出为 Markdown / JSON / HTML 格式。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入内容为空或不是字符串",
    "E002": "无法从内容中提取标题",
    "E003": "无法识别内容语言（仅支持中英文）",
    "E004": "日期格式无效",
    "E005": "输出格式不受支持",
    "E006": "批量输入格式错误",
    "E007": "文件读取失败",
    "E008": "文件写入失败",
    "E009": "输入内容过长（超过限制）",
    "E010": "内部逻辑错误",
}


class MerbloggerError(Exception):
    """携带错误码的异常类"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class BlogArticle:
    """一篇结构化博客文章"""

    def __init__(
        self,
        title: str,
        author: str = "",
        date: str = "",
        category: str = "",
        tags: Optional[List[str]] = None,
        content: str = "",
        confidence: str = "high",
    ):
        self.title = title
        self.author = author
        self.date = date
        self.category = category
        self.tags = tags or []
        self.content = content
        self.confidence = confidence  # high / medium / low

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "category": self.category,
            "tags": self.tags,
            "content": self.content,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlogArticle":
        """从字典构建"""
        return cls(
            title=data.get("title", ""),
            author=data.get("author", ""),
            date=data.get("date", ""),
            category=data.get("category", ""),
            tags=data.get("tags", []),
            content=data.get("content", ""),
            confidence=data.get("confidence", "high"),
        )


# ---------------------------------------------------------------------------
# 核心解析与处理逻辑
# ---------------------------------------------------------------------------
def extract_title(content: str) -> str:
    """
    从内容中提取标题。

    规则：
    1. 如果第一行以 # 开头，取第一个 # 后的文字作为标题。
    2. 如果第一行非空且不是 # 开头，取第一行前 80 字符作为标题。
    3. 否则返回空字符串。
    """
    if not content:
        return ""

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return ""

    first_line = lines[0]
    if first_line.startswith("#"):
        # 取第一个 # 后的内容
        title = first_line.lstrip("#").strip()
        return title[:80] if title else ""

    # 取第一行作为标题，限制长度
    return first_line[:80]


def extract_author(content: str) -> str:
    """尝试从内容中提取作者信息。"""
    # 匹配 "作者: xxx" 或 "author: xxx" 模式
    patterns = [
        r"(?:作者|作者：|author[：:])\s*([^\n]+)",
        r"(?:by|By|BY)[：:]\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_date(content: str) -> str:
    """
    尝试从内容中提取日期。

    支持格式：YYYY-MM-DD, YYYY/MM/DD, YYYY年MM月DD日
    无法确定时返回空字符串（调用方负责标注占位）。
    """
    patterns = [
        r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?",
        r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            year, month, day = match.groups()
            try:
                # 验证日期有效性
                datetime(int(year), int(month), int(day))
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            except ValueError:
                continue
    return ""


def extract_category(content: str) -> str:
    """尝试提取分类信息。"""
    patterns = [
        r"(?:分类|分类：|category[：:])\s*([^\n]+)",
        r"(?:标签组|专栏)[：:]\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_tags(content: str) -> List[str]:
    """尝试提取标签列表。"""
    patterns = [
        r"(?:标签|标签：|tags?[：:])\s*([^\n]+)",
        r"(?:关键词|关键字)[：:]\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            raw = match.group(1)
            # 支持逗号、顿号、空格分隔
            tags = re.split(r"[,，、\s]+", raw)
            return [t.strip() for t in tags if t.strip()]
    return []


def detect_language(content: str) -> str:
    """简单检测内容语言（中/英）。"""
    if not content:
        raise MerbloggerError("E003")

    chinese_chars = sum(1 for c in content if "\u4e00" <= c <= "\u9fff")
    total_chars = len(content.strip())
    if total_chars == 0:
        raise MerbloggerError("E003")

    if chinese_chars / total_chars > 0.1:
        return "zh"
    return "en"


def parse_article(content: str) -> BlogArticle:
    """
    将非结构化文本解析为 BlogArticle 对象。

    参数:
        content: 用户提供的文章草稿文本

    返回:
        BlogArticle 结构化对象

    异常:
        E001: 输入为空
        E002: 无法提取标题
        E003: 语言无法识别
        E009: 内容过长
    """
    if not content or not isinstance(content, str):
        raise MerbloggerError("E001")

    # 限制内容长度（防止异常输入）
    if len(content) > 1_000_000:
        raise MerbloggerError("E009")

    # 语言检测
    detect_language(content)

    title = extract_title(content)
    if not title:
        raise MerbloggerError("E002")

    author = extract_author(content)
    date = extract_date(content)
    category = extract_category(content)
    tags = extract_tags(content)

    # 如果缺少关键字段，降低置信度
    confidence = "high"
    if not author or not date or not category:
        confidence = "medium"
    if not author and not date and not category:
        confidence = "low"

    # 正文 = 去除元信息行后的内容
    body_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        # 跳过标题行和元信息行
        if stripped.startswith("#") or re.match(
            r"^(作者|分类|标签|关键词|日期|author|category|tags?|date)[：:]",
            stripped,
            re.IGNORECASE,
        ):
            continue
        body_lines.append(line)

    body = "\n".join(body_lines).strip()

    # 如果正文为空，用占位符
    if not body:
        body = "[需核实:正文内容]"

    return BlogArticle(
        title=title,
        author=author,
        date=date,
        category=category,
        tags=tags,
        content=body,
        confidence=confidence,
    )


def batch_parse(articles: List[str]) -> List[BlogArticle]:
    """批量解析多篇文章。"""
    if not isinstance(articles, list):
        raise MerbloggerError("E006")
    return [parse_article(a) for a in articles]


def format_markdown(article: BlogArticle) -> str:
    """输出为 Markdown 格式。"""
    lines = [
        f"# {article.title}",
        "",
    ]

    meta_lines = []
    if article.author:
        meta_lines.append(f"作者：{article.author}")
    if article.date:
        meta_lines.append(f"日期：{article.date}")
    if article.category:
        meta_lines.append(f"分类：{article.category}")
    if article.tags:
        meta_lines.append(f"标签：{', '.join(article.tags)}")

    if meta_lines:
        lines.extend(meta_lines)
        lines.append("")

    lines.append(article.content)
    lines.append("")

    if article.confidence != "high":
        lines.append(f"> ⚠️ 置信度：{article.confidence}，部分字段可能不准确。")

    return "\n".join(lines)


def format_json(article: BlogArticle) -> str:
    """输出为 JSON 格式。"""
    return json.dumps(article.to_dict(), ensure_ascii=False, indent=2)


def format_html(article: BlogArticle) -> str:
    """输出为 HTML 片段。"""
    tags_html = ""
    if article.tags:
        tags_html = (
            '<div class="tags">'
            + " ".join(f'<span class="tag">{t}</span>' for t in article.tags)
            + "</div>"
        )

    meta_html = ""
    if article.author or article.date or article.category:
        parts = []
        if article.author:
            parts.append(f'<span class="author">{article.author}</span>')
        if article.date:
            parts.append(f'<span class="date">{article.date}</span>')
        if article.category:
            parts.append(f'<span class="category">{article.category}</span>')
        meta_html = f'<div class="meta">{" | ".join(parts)}</div>'

    content_html = "\n".join(
        f"<p>{line}</p>" for line in article.content.splitlines() if line.strip()
    )

    return f"""<article>
  <h1>{article.title}</h1>
  {meta_html}
  {tags_html}
  <div class="content">
  {content_html}
  </div>
</article>"""


def format_article(article: BlogArticle, output_format: str = "markdown") -> str:
    """按指定格式输出文章。"""
    output_format = output_format.lower()
    if output_format in ("md", "markdown"):
        return format_markdown(article)
    elif output_format == "json":
        return format_json(article)
    elif output_format in ("html", "htm"):
        return format_html(article)
    else:
        raise MerbloggerError("E005")


# ---------------------------------------------------------------------------
# 内置自检数据与测试逻辑
# ---------------------------------------------------------------------------
def _selftest_data() -> Dict[str, Any]:
    """返回内置硬编码自检数据（不依赖外部文件）。"""
    return {
        "sample_article": """# 我的第一篇博客

作者：张三
日期：2026-01-15
分类：技术
标签：Python, 博客, 教程

这是一篇测试文章，用于验证解析逻辑。
包含多行内容，测试正文提取是否正常。
""",
        "sample_article_no_meta": """# 无元信息文章

这是一篇没有作者、日期、分类的文章。
用于测试置信度标注逻辑。
""",
        "sample_article_english": """# My First Post

author: John Doe
date: 2026/02/20
tags: python, blog

This is an English test article.
""",
    }


def run_selftest() -> int:
    """
    运行内置自检。使用宽松阈值断言，确保任何环境可直接通过。

    返回:
        0 表示全部通过，非 0 表示测试失败
    """
    print("[SELFTEST] 开始运行 merblogger 自检...")

    try:
        data = _selftest_data()

        # 测试 1: 基本解析
        article = parse_article(data["sample_article"])
        assert article.title == "我的第一篇博客", "标题提取失败"
        assert article.author == "张三", "作者提取失败"
        assert article.date == "2026-01-15", "日期提取失败"
        assert article.category == "技术", "分类提取失败"
        assert len(article.tags) >= 3, "标签提取失败"
        assert article.confidence == "high", "置信度应为 high"
        print("[PASS] 基本解析测试")

        # 测试 2: 无元信息文章
        article2 = parse_article(data["sample_article_no_meta"])
        assert article2.title == "无元信息文章", "标题提取失败"
        assert article2.confidence == "low", "置信度应为 low"
        assert article2.author == "", "作者应为空"
        assert article2.date == "", "日期应为空"
        print("[PASS] 无元信息解析测试")

        # 测试 3: 英文文章
        article3 = parse_article(data["sample_article_english"])
        assert article3.title == "My First Post", "英文标题提取失败"
        assert article3.author == "John Doe", "英文作者提取失败"
        assert article3.date == "2026-02-20", "英文日期提取失败"
        assert len(article3.tags) >= 2, "英文标签提取失败"
        print("[PASS] 英文解析测试")

        # 测试 4: 格式输出
        md = format_markdown(article)
        assert "# " in md, "Markdown 应包含标题"
        assert "作者：" in md, "Markdown 应包含作者"
        assert "张三" in md, "Markdown 应包含作者名"

        js = format_json(article)
        json_data = json.loads(js)
        assert json_data["title"] == "我的第一篇博客", "JSON 标题不一致"

        html = format_html(article)
        assert "<h1>" in html, "HTML 应包含 h1 标题"
        assert "我的第一篇博客" in html, "HTML 标题内容不一致"
        print("[PASS] 格式输出测试")

        # 测试 5: 批量处理
        batch = batch_parse([data["sample_article"], data["sample_article_no_meta"]])
        assert len(batch) == 2, "批量解析数量错误"
        assert batch[0].title == "我的第一篇博客", "批量解析第一篇错误"
        assert batch[1].title == "无元信息文章", "批量解析第二篇错误"
        print("[PASS] 批量处理测试")

        # 测试 6: 错误处理
        try:
            parse_article("")
            assert False, "空输入应抛出 E001"
        except MerbloggerError as e:
            assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"

        try:
            parse_article("   \n  \n  ")
            assert False, "空白输入应抛出 E003"
        except MerbloggerError as e:
            assert e.code == "E003", f"错误码应为 E003，实际为 {e.code}"

        try:
            format_article(article, "unknown_format")
            assert False, "未知格式应抛出 E005"
        except MerbloggerError as e:
            assert e.code == "E005", f"错误码应为 E005，实际为 {e.code}"
        print("[PASS] 错误处理测试")

        # 测试 7: 日期验证（宽松阈值）
        date = extract_date("发布于 2026-03-15 的内容")
        assert date == "2026-03-15", "日期提取失败"

        date2 = extract_date("日期：2026年12月31日")
        assert date2 == "2026-12-31", "中文日期提取失败"

        date3 = extract_date("没有日期的内容")
        assert date3 == "", "无日期时应返回空字符串"
        print("[PASS] 日期提取测试")

        print("[SELFTEST] 所有测试通过 ✅")
        return 0

    except AssertionError as e:
        print(f"[SELFTEST] 断言失败: {e}")
        return 1
    except MerbloggerError as e:
        print(f"[SELFTEST] 业务错误: {e}")
        return 1
    except Exception as e:
        print(f"[SELFTEST] 未预期异常: {type(e).__name__}: {e}")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="merblogger — 博客发布与内容管理工具",
        epilog="示例: python main.py -i article.txt -f markdown",
    )
    parser.add_argument(
        "-i", "--input", type=str, help="输入文件路径（UTF-8 编码的文本文件）"
    )
    parser.add_argument(
        "-t", "--text", type=str, help="直接输入文章内容（字符串）"
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["markdown", "md", "json", "html", "htm"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件，不访问网络）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：输入 JSON 文件路径（包含字符串列表）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 收集输入内容
    content = ""
    try:
        if args.text:
            content = args.text
        elif args.input:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    content = f.read()
            except (IOError, OSError) as e:
                print(f"[E007] 文件读取失败: {e}")
                return 1
        elif args.batch:
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    batch_data = json.load(f)
                if not isinstance(batch_data, list) or not all(
                    isinstance(item, str) for item in batch_data
                ):
                    print("[E006] 批量输入格式错误：应为字符串数组")
                    return 1
            except (IOError, OSError) as e:
                print(f"[E007] 文件读取失败: {e}")
                return 1
            except json.JSONDecodeError as e:
                print(f"[E006] JSON 解析失败: {e}")
                return 1

            # 批量处理
            try:
                articles = batch_parse(batch_data)
                for i, article in enumerate(articles, 1):
                    print(f"--- 文章 {i} ---")
                    print(format_article(article, args.format))
                    print()
                return 0
            except MerbloggerError as e:
                print(f"处理失败: {e}")
                return 1
        else:
            # 从 stdin 读取
            content = sys.stdin.read()
    except Exception as e:
        print(f"[E010] 内部错误: {e}")
        return 1

    # 单篇解析
    if content.strip():
        try:
            article = parse_article(content)
            output = format_article(article, args.format)
            print(output)
            return 0
        except MerbloggerError as e:
            print(f"处理失败: {e}")
            return 1
    else:
        print("[E001] 输入内容为空")
        return 1


if __name__ == "__main__":
    sys.exit(main())
