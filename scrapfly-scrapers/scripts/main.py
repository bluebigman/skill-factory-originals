#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 网页采集、数据抽取、结构化输出（独立实现）

本脚本依据功能规格从零实现，不参考任何既有代码。
提供网页正文解析、字段抽取、结构化输出与离线自检能力。
"""

import argparse
import csv
import html
import io
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 输入参数无效
# E002: URL 格式非法
# E003: 输入内容为空
# E004: HTML 解析失败
# E005: 字段抽取异常
# E006: 输出格式不支持
# E007: 批量数量超限
# E008: 文件读取失败
# E009: JSON 序列化失败
# E010: 内部逻辑错误
# ---------------------------------------------------------------------------

# 单次最多处理的 URL 数量（规格要求）
MAX_BATCH_SIZE = 200

# 置信度阈值（低于此值标记为需核实）
CONFIDENCE_THRESHOLD = 0.6


@dataclass
class ExtractedField:
    """单个抽取字段的结果。"""
    name: str
    value: Any
    confidence: float


@dataclass
class PageResult:
    """单个页面的结构化抽取结果。"""
    url: str
    fields: Dict[str, Any] = field(default_factory=dict)
    confidences: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为带置信度标注的字典。"""
        result: Dict[str, Any] = {}
        for name, value in self.fields.items():
            conf = self.confidences.get(name, 0.0)
            if conf < CONFIDENCE_THRESHOLD:
                # 低置信度字段加标注
                result[f"[需核实:{name}]"] = value
            else:
                result[name] = value
            # 附置信度属性
            result[f"{name}_confidence"] = conf
        return result


class HtmlParser:
    """轻量级 HTML 解析器（仅依赖标准库）。"""

    # 常见标签及其在文本中的分隔符
    BLOCK_TAGS = {
        "p", "div", "section", "article", "h1", "h2", "h3",
        "h4", "h5", "h6", "li", "br", "tr", "table", "ul", "ol",
    }
    SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self, html_text: str, base_url: str = ""):
        self.raw = html_text
        self.base_url = base_url
        self._parse_error: Optional[str] = None

    def extract_text(self) -> str:
        """提取纯文本内容。"""
        try:
            text = self._strip_tags(self.raw)
            # 规范化空白
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)
        except Exception as exc:  # pragma: no cover
            self._parse_error = str(exc)
            return ""

    def extract_links(self) -> List[str]:
        """提取页面中的链接。"""
        links: List[str] = []
        try:
            pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\']', re.IGNORECASE)
            for match in pattern.finditer(self.raw):
                href = match.group(1).strip()
                if href and not href.startswith(("#", "javascript:", "mailto:")):
                    if self.base_url:
                        href = urljoin(self.base_url, href)
                    links.append(href)
        except Exception:
            pass
        return links

    def extract_meta(self) -> Dict[str, str]:
        """提取 meta 标签中的信息。"""
        meta_info: Dict[str, str] = {}
        try:
            pattern = re.compile(
                r'<meta\s+[^>]*(?:name|property)=["\']([^"\']+)["\']\s+'
                r'content=["\']([^"\']*)["\']',
                re.IGNORECASE,
            )
            for match in pattern.finditer(self.raw):
                key = match.group(1).lower()
                value = match.group(2)
                if key and value and key not in meta_info:
                    meta_info[key] = value
        except Exception:
            pass
        return meta_info

    def extract_images(self) -> List[str]:
        """提取图片链接。"""
        images: List[str] = []
        try:
            pattern = re.compile(r'<img\s+[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE)
            for match in pattern.finditer(self.raw):
                src = match.group(1).strip()
                if src:
                    if self.base_url and not src.startswith(("http://", "https://", "data:")):
                        src = urljoin(self.base_url, src)
                    images.append(src)
        except Exception:
            pass
        return images

    def _strip_tags(self, content: str) -> str:
        """去除 HTML 标签，保留文本。"""
        # 移除注释
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        # 跳过不需要的标签内容
        for tag in self.SKIP_TAGS:
            pattern = re.compile(rf"<{tag}[^>]*>.*?</{tag}>", re.DOTALL | re.IGNORECASE)
            content = pattern.sub(" ", content)
        # 块级标签替换为换行
        for tag in self.BLOCK_TAGS:
            pattern = re.compile(rf"</?{tag}[^>]*>", re.IGNORECASE)
            content = pattern.sub("\n", content)
        # 其余标签去除
        content = re.sub(r"<[^>]+>", "", content)
        # 解码 HTML 实体
        content = html.unescape(content)
        return content


class FieldExtractor:
    """从解析后的页面中抽取结构化字段。"""

    # 通用字段的启发式规则
    TITLE_PATTERNS = [
        r"<title[^>]*>([^<]+)</title>",
        r'<h1[^>]*>([^<]+)</h1>',
        r'<meta\s+property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
    ]

    AUTHOR_PATTERNS = [
        r'<meta\s+name=["\']author["\'][^>]*content=["\']([^"\']+)["\']',
        r'<a[^>]*rel=["\']author["\'][^>]*>([^<]+)</a>',
        r'(?:作者|by|author)[：:\s]*([^\n<]{2,30})',
    ]

    DATE_PATTERNS = [
        r'<meta\s+(?:name|property)=["\'](?:date|article:published_time)["\'][^>]*content=["\']([^"\']+)["\']',
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
        r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)',
    ]

    def __init__(self, html_text: str, base_url: str = ""):
        self.raw = html_text
        self.base_url = base_url
        self.parser = HtmlParser(html_text, base_url)

    def extract_all(self) -> PageResult:
        """抽取全部通用字段。"""
        result = PageResult(url=self.base_url or "inline")
        try:
            # 标题
            title, title_conf = self._extract_title()
            result.fields["title"] = title
            result.confidences["title"] = title_conf

            # 正文
            text = self.parser.extract_text()
            if text:
                result.fields["content"] = text[:5000]  # 限制长度
                result.confidences["content"] = 0.9 if len(text) > 100 else 0.5
            else:
                result.fields["content"] = ""
                result.confidences["content"] = 0.0

            # 作者
            author, author_conf = self._extract_author()
            result.fields["author"] = author
            result.confidences["author"] = author_conf

            # 发布时间
            pub_date, date_conf = self._extract_date()
            result.fields["published_time"] = pub_date
            result.confidences["published_time"] = date_conf

            # 主图
            images = self.parser.extract_images()
            result.fields["main_image"] = images[0] if images else ""
            result.confidences["main_image"] = 0.7 if images else 0.0

            # 分页链接
            links = self.parser.extract_links()
            result.fields["paginated_links"] = links[:20]
            result.confidences["paginated_links"] = 0.6 if links else 0.0

            # 元信息
            meta = self.parser.extract_meta()
            result.fields["meta"] = meta
            result.confidences["meta"] = 0.5 if meta else 0.0

            # 低置信度警告
            for name, conf in result.confidences.items():
                if conf < CONFIDENCE_THRESHOLD:
                    result.warnings.append(f"[需核实:{name}]")

        except Exception as exc:
            result.warnings.append(f"抽取异常: {exc}")
        return result

    def _extract_title(self) -> tuple[str, float]:
        """抽取标题。"""
        for pattern in self.TITLE_PATTERNS:
            match = re.search(pattern, self.raw, re.IGNORECASE | re.DOTALL)
            if match:
                title = html.unescape(match.group(1)).strip()
                if title:
                    # 置信度：h1 最高，title 次之，og:title 再次
                    conf = 0.9 if "h1" in pattern else (0.8 if "title" in pattern else 0.7)
                    return title, conf
        return "", 0.0

    def _extract_author(self) -> tuple[str, float]:
        """抽取作者。"""
        for pattern in self.AUTHOR_PATTERNS:
            match = re.search(pattern, self.raw, re.IGNORECASE | re.DOTALL)
            if match:
                author = html.unescape(match.group(1)).strip()
                if author:
                    return author, 0.8
        return "", 0.0

    def _extract_date(self) -> tuple[str, float]:
        """抽取发布时间。"""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, self.raw, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                if date_str:
                    return date_str, 0.8
        return "", 0.0


class OutputFormatter:
    """将结果格式化为不同输出。"""

    @staticmethod
    def to_json(results: List[PageResult]) -> str:
        """转换为 JSON 字符串。"""
        try:
            data = [r.to_dict() for r in results]
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise RuntimeError(f"E009: JSON 序列化失败 - {exc}")

    @staticmethod
    def to_csv(results: List[PageResult]) -> str:
        """转换为 CSV 字符串。"""
        if not results:
            return ""
        # 收集所有字段名
        all_fields: List[str] = []
        for r in results:
            for name in r.fields.keys():
                if name not in all_fields:
                    all_fields.append(name)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["url"] + all_fields)
        for r in results:
            row = [r.url]
            for f in all_fields:
                value = r.fields.get(f, "")
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                row.append(value)
            writer.writerow(row)
        return output.getvalue()

    @staticmethod
    def to_markdown(results: List[PageResult]) -> str:
        """转换为 Markdown 表格。"""
        if not results:
            return "无数据"
        lines = ["| URL | 标题 | 置信度 |", "|-----|------|--------|"]
        for r in results:
            title = str(r.fields.get("title", ""))[:30]
            conf = r.confidences.get("title", 0.0)
            lines.append(f"| {r.url} | {title} | {conf:.2f} |")
        return "\n".join(lines)


def process_html(html_text: str, source_url: str = "") -> PageResult:
    """处理单个 HTML 内容，返回结构化结果。"""
    if not html_text or not html_text.strip():
        raise ValueError("E003: 输入内容为空")
    extractor = FieldExtractor(html_text, source_url)
    return extractor.extract_all()


def process_batch(html_texts: List[str], urls: Optional[List[str]] = None) -> List[PageResult]:
    """批量处理 HTML 内容。"""
    if len(html_texts) > MAX_BATCH_SIZE:
        raise ValueError(f"E007: 批量数量超限，最多 {MAX_BATCH_SIZE} 个")
    if urls is None:
        urls = [""] * len(html_texts)
    if len(urls) != len(html_texts):
        raise ValueError("E001: URL 列表长度与内容不匹配")
    results = []
    for text, url in zip(html_texts, urls):
        try:
            results.append(process_html(text, url))
        except Exception as exc:
            # 单个失败不影响整体
            results.append(PageResult(url=url, warnings=[str(exc)]))
    return results


def validate_url(url: str) -> bool:
    """校验 URL 格式。"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def read_file(path: str) -> str:
    """读取本地文件。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        raise ValueError(f"E008: 文件读取失败 - {exc}")


def run_selftest() -> bool:
    """离线自检核心逻辑（不依赖外部环境）。"""
    print("开始自检...")

    # 内置硬编码样例数据
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试文章标题示例</title>
        <meta name="author" content="测试作者">
        <meta property="article:published_time" content="2024-01-15T10:30:00">
        <meta property="og:title" content="测试文章标题示例">
        <meta property="og:image" content="https://example.com/main.jpg">
    </head>
    <body>
        <h1>测试文章标题示例</h1>
        <p>这是第一段测试正文内容，用于验证文本抽取是否正常工作。</p>
        <p>这是第二段测试正文内容，包含一些额外信息。</p>
        <a href="/page/2">下一页</a>
        <a href="/page/3">第三页</a>
        <img src="https://example.com/img1.jpg">
        <img src="/img2.jpg">
        <script>var fake = "should not appear";</script>
        <style>.css { color: red; }</style>
    </body>
    </html>
    """

    # 测试 1: HTML 解析
    parser = HtmlParser(sample_html, "https://example.com/article")
    text = parser.extract_text()
    assert "测试文章标题示例" in text, "标题未出现在文本中"
    assert "should not appear" not in text, "script 内容不应出现在文本中"
    assert "color: red" not in text, "style 内容不应出现在文本中"
    print("  [PASS] HTML 文本抽取")

    # 测试 2: 链接抽取
    links = parser.extract_links()
    assert len(links) >= 2, f"应至少抽取 2 个链接，实际 {len(links)}"
    assert any("page/2" in link for link in links), "未找到分页链接"
    print("  [PASS] 链接抽取")

    # 测试 3: 图片抽取
    images = parser.extract_images()
    assert len(images) >= 2, f"应至少抽取 2 张图片，实际 {len(images)}"
    assert any("main.jpg" in img for img in images), "未找到主图"
    print("  [PASS] 图片抽取")

    # 测试 4: 字段抽取
    result = process_html(sample_html, "https://example.com/article")
    assert result.fields.get("title") == "测试文章标题示例", "标题抽取错误"
    assert result.fields.get("author") == "测试作者", "作者抽取错误"
    assert "2024" in result.fields.get("published_time", ""), "时间抽取错误"
    assert len(result.fields.get("content", "")) > 50, "正文抽取过短"
    print("  [PASS] 字段抽取")

    # 测试 5: 置信度
    assert result.confidences.get("title", 0) > 0.5, "标题置信度应较高"
    assert result.confidences.get("content", 0) > 0.5, "正文置信度应较高"
    print("  [PASS] 置信度计算")

    # 测试 6: 批量处理
    results = process_batch([sample_html, sample_html], ["https://a.com", "https://b.com"])
    assert len(results) == 2, "批量处理数量错误"
    assert all(r.fields.get("title") for r in results), "批量处理结果缺失"
    print("  [PASS] 批量处理")

    # 测试 7: 输出格式
    json_out = OutputFormatter.to_json(results)
    assert '"title"' in json_out, "JSON 输出缺少标题字段"
    csv_out = OutputFormatter.to_csv(results)
    assert "url" in csv_out, "CSV 输出缺少表头"
    md_out = OutputFormatter.to_markdown(results)
    assert "|" in md_out, "Markdown 输出格式错误"
    print("  [PASS] 输出格式化")

    # 测试 8: 边界情况
    empty_result = process_html("<html><body><p>简短</p></body></html>")
    assert empty_result.warnings, "简短内容应有低置信度警告"
    print("  [PASS] 边界情况处理")

    # 测试 9: URL 校验
    assert validate_url("https://example.com"), "合法 URL 校验失败"
    assert not validate_url("not-a-url"), "非法 URL 未被拒绝"
    print("  [PASS] URL 校验")

    # 测试 10: 错误处理
    try:
        process_html("")
        assert False, "空输入应报错"
    except ValueError as exc:
        assert "E003" in str(exc), f"错误码错误: {exc}"
    print("  [PASS] 错误处理")

    print("自检全部通过！")
    return True


def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="网页采集与结构化数据抽取工具",
        epilog="示例: python main.py --html '<html>...</html>' --url https://example.com --format json",
    )
    parser.add_argument("--html", type=str, help="HTML 内容字符串")
    parser.add_argument("--file", type=str, help="HTML 文件路径")
    parser.add_argument("--url", type=str, default="", help="源 URL（用于相对链接解析）")
    parser.add_argument("--format", type=str, choices=["json", "csv", "markdown"], default="json", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--batch-file", type=str, help="批量处理：每行一个 HTML 文件路径的列表文件")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    try:
        results: List[PageResult] = []

        # 批量处理模式
        if args.batch_file:
            try:
                with open(args.batch_file, "r", encoding="utf-8") as f:
                    paths = [line.strip() for line in f if line.strip()]
            except Exception as exc:
                print(f"E008: 批量文件读取失败 - {exc}", file=sys.stderr)
                sys.exit(1)

            html_texts = []
            for path in paths:
                try:
                    html_texts.append(read_file(path))
                except ValueError as exc:
                    print(f"警告: {exc}", file=sys.stderr)
                    html_texts.append("")
            results = process_batch(html_texts)

        # 单文件模式
        elif args.file:
            html_text = read_file(args.file)
            results = [process_html(html_text, args.url)]

        # 直接 HTML 字符串模式
        elif args.html:
            results = [process_html(args.html, args.url)]

        else:
            parser.print_help()
            sys.exit(0)

        # 输出
        if args.format == "json":
            print(OutputFormatter.to_json(results))
        elif args.format == "csv":
            print(OutputFormatter.to_csv(results))
        elif args.format == "markdown":
            print(OutputFormatter.to_markdown(results))
        else:
            raise ValueError(f"E006: 不支持的输出格式: {args.format}")

    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"E010: 内部错误 - {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
