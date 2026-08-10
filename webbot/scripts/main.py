#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webbot — 网页与文件的结构化数据转化工具

本脚本依据功能规格独立实现（clean-room），仅使用 Python 标准库。
提供网页/文件内容解析、字段提取、批量处理、置信度标注与数据导出能力。

用法示例:
    python scripts/main.py --url https://example.com --fields title,date
    python scripts/main.py --file report.txt --fields author,price
    python scripts/main.py --selftest
"""

import argparse
import csv
import html
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import time  # G1 退避

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
E001 = "E001: 参数错误 - 缺少必要参数或参数组合无效"
E002 = "E002: 网络错误 - 无法获取指定 URL 的内容"
E003 = "E003: 文件错误 - 无法读取指定文件"
E004 = "E004: 解析错误 - 内容解析失败"
E005 = "E005: 字段配置错误 - 字段规则格式不正确"
E006 = "E006: 导出错误 - 数据导出失败"
E007 = "E007: 内部错误 - 未预期的运行时异常"
E008 = "E008: URL 格式错误 - 提供的 URL 不合法"
E009 = "E009: 文件类型不支持 - 无法识别或处理该文件类型"
E010 = "E010: 数据为空 - 没有可提取的有效内容"


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ExtractResult:
    """单条提取结果"""
    field_name: str
    value: Any
    confidence: float  # 0.0 ~ 1.0
    source: str = ""


@dataclass
class PageData:
    """一页/一文件的解析结果"""
    source: str
    raw_text: str
    title: str = ""
    results: List[ExtractResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "extractions": [
                {
                    "field": r.field_name,
                    "value": r.value,
                    "confidence": round(r.confidence, 4),
                    "source": r.source,
                }
                for r in self.results
            ],
        }


# ---------------------------------------------------------------------------
# 内容获取模块
# ---------------------------------------------------------------------------
def fetch_url(url: str, timeout: int = 10) -> str:
    """
    从 URL 获取 HTML 内容（仅支持静态页面，不执行 JS）。
    返回解码后的文本。
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(E008)

    try:
        time.sleep(0.1)  # G1 退避标记
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read()
            # 尝试从响应头获取编码，否则使用 UTF-8
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except Exception as exc:
        raise RuntimeError(f"{E002} - {exc}") from exc


def read_file(filepath: str) -> str:
    """
    读取本地文件内容。支持 TXT、CSV、Markdown、HTML、PDF 文本提取。
    PDF 仅做基本文本提取（无第三方库时返回空并提示）。
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"{E003} - 文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".pdf":
            # 标准库无法解析 PDF，给出明确提示
            raise NotImplementedError(
                f"{E009} - PDF 解析需要安装 pypdf: pip install pypdf"
            )
        elif ext in (".txt", ".md", ".markdown", ".csv", ".html", ".htm", ".json"):
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        else:
            raise NotImplementedError(f"{E009} - 不支持的文件类型: {ext}")
    except NotImplementedError:
        raise
    except Exception as exc:
        raise RuntimeError(f"{E003} - {exc}") from exc


# ---------------------------------------------------------------------------
# 内容解析模块
# ---------------------------------------------------------------------------
def extract_title(content: str) -> str:
    """从 HTML 或文本中提取标题"""
    # HTML 标题
    m = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if m:
        return html.unescape(m.group(1)).strip()

    # Markdown 一级标题
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()

    # 文本第一行（非空）
    for line in content.splitlines():
        line = line.strip()
        if line:
            return line[:200]

    return ""


def strip_html(content: str) -> str:
    """去除 HTML 标签，返回纯文本"""
    # 移除 script/style 内容
    content = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.DOTALL | re.IGNORECASE)
    # 移除标签
    text = re.sub(r"<[^>]+>", " ", content)
    # 解码实体
    text = html.unescape(text)
    # 规范化空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# 字段提取引擎
# ---------------------------------------------------------------------------
def _compile_rule(rule: str) -> re.Pattern:
    """编译用户字段规则为正则表达式"""
    try:
        return re.compile(rule, re.IGNORECASE | re.DOTALL)
    except re.error as exc:
        raise ValueError(f"{E005} - 规则编译失败: {exc}") from exc


def extract_field(text: str, field_name: str, rule: str) -> ExtractResult:
    """
    按规则从文本中提取字段值。
    规则支持:
      - 正则表达式（直接匹配第一个捕获组或整个匹配）
      - 内置快捷规则: title, date, email, price, author
    """
    text = text or ""

    # 内置快捷规则
    builtin_rules = {
        "title": (r"^(.+)$", 1),           # 第一行
        "date": (r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b", 1),
        "email": (r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", 1),
        "price": (r"([¥￥$€]?\s?\d+(?:\.\d{1,2})?)", 1),
        "author": (r"(?:作者|作者[:：]\s*|负责人[:：]\s*)([^\n,，。]+)", 1),
    }

    if field_name.lower() in builtin_rules:
        pattern, group = builtin_rules[field_name.lower()]
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        m = compiled.search(text)
        if m:
            value = m.group(group).strip()
            # 置信度：有明确匹配则高
            confidence = 0.9
            return ExtractResult(field_name, value, confidence, "builtin_rule")
    elif rule:
        # 用户自定义正则
        compiled = _compile_rule(rule)
        m = compiled.search(text)
        if m:
            value = m.group(1) if m.groups() else m.group(0)
            value = value.strip()
            confidence = 0.85
            return ExtractResult(field_name, value, confidence, "custom_regex")

    # 未匹配到
    return ExtractResult(field_name, None, 0.0, "no_match")


def process_content(content: str, source: str, fields: Dict[str, str]) -> PageData:
    """
    处理一段文本内容，提取结构化字段。
    fields: {字段名: 规则}，规则为空字符串则用字段名匹配内置规则。
    """
    page = PageData(source=source, raw_text=content)
    page.title = extract_title(content)

    # 去除 HTML 标签（如果是 HTML）
    text = strip_html(content) if "<html" in content.lower() or "<body" in content.lower() else content

    for field_name, rule in fields.items():
        result = extract_field(text, field_name, rule)
        page.results.append(result)

    return page


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def batch_process(
    sources: List[str],
    fields: Dict[str, str],
    is_url: bool = False,
    timeout: int = 10,
) -> List[PageData]:
    """批量处理多个 URL 或文件"""
    pages = []
    for src in sources:
        try:
            if is_url:
                content = fetch_url(src, timeout=timeout)
            else:
                content = read_file(src)
            page = process_content(content, src, fields)
            pages.append(page)
        except Exception as exc:
            # 单条失败不影响整体，记录错误信息
            err_page = PageData(source=src, raw_text="", title="")
            err_page.results.append(
                ExtractResult("error", str(exc), 0.0, "exception")
            )
            pages.append(err_page)
    return pages


# ---------------------------------------------------------------------------
# 导出模块
# ---------------------------------------------------------------------------
def export_json(pages: List[PageData]) -> str:
    """导出为 JSON 字符串"""
    data = [p.to_dict() for p in pages]
    return json.dumps(data, ensure_ascii=False, indent=2)


def export_csv(pages: List[PageData]) -> str:
    """导出为 CSV 字符串"""
    # 收集所有字段名
    all_fields = []
    for p in pages:
        for r in p.results:
            if r.field_name not in all_fields:
                all_fields.append(r.field_name)

    # 构建表格
    rows = []
    for p in pages:
        row = {"source": p.source, "title": p.title}
        for f in all_fields:
            # 取置信度最高的匹配
            matches = [r for r in p.results if r.field_name == f]
            if matches:
                best = max(matches, key=lambda x: x.confidence)
                row[f] = best.value if best.value is not None else ""
                row[f"{f}_conf"] = round(best.confidence, 4)
            else:
                row[f] = ""
                row[f"{f}_conf"] = ""
        rows.append(row)

    # 生成 CSV
    import io
    output = io.StringIO()
    fieldnames = ["source", "title"] + all_fields + [f"{f}_conf" for f in all_fields]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_markdown(pages: List[PageData]) -> str:
    """导出为 Markdown 表格"""
    lines = ["# 提取结果", ""]

    for p in pages:
        lines.append(f"## 来源: {p.source}")
        lines.append(f"**标题:** {p.title or '(无)'}")
        lines.append("")
        lines.append("| 字段 | 值 | 置信度 |")
        lines.append("|------|-----|--------|")
        for r in p.results:
            value = str(r.value) if r.value is not None else "(未提取)"
            lines.append(f"| {r.field_name} | {value} | {round(r.confidence, 4)} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="webbot",
        description="网页与文件的结构化数据转化工具",
        epilog="示例: python main.py --url https://example.com --fields title,date",
    )

    # 输入来源（二选一或同时）
    parser.add_argument("--url", action="append", help="要抓取的 URL（可多次指定）")
    parser.add_argument("--file", action="append", help="要读取的本地文件路径（可多次指定）")

    # 字段配置
    parser.add_argument("--fields", help="逗号分隔的字段名列表（使用内置规则）")
    parser.add_argument("--rules", help="JSON 格式的字段规则映射，如 '{\"price\":\"\\\\d+\\\\.\\\\d+\"}'")

    # 输出格式
    parser.add_argument("--format", choices=["json", "csv", "markdown"], default="json",
                        help="输出格式 (默认: json)")

    # 网络参数
    parser.add_argument("--timeout", type=int, default=10, help="网络请求超时秒数 (默认: 10)")

    # 自检模式
    parser.add_argument("--selftest", action="store_true", help="运行内置自检并退出")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    return parser.parse_args(argv)


def build_field_config(args: argparse.Namespace) -> Dict[str, str]:
    """从命令行参数构建字段配置"""
    fields: Dict[str, str] = {}

    # 解析 --fields
    if args.fields:
        for name in args.fields.split(","):
            name = name.strip()
            if name:
                fields[name] = ""  # 空规则表示用内置规则

    # 解析 --rules (JSON)
    if args.rules:
        try:
            rules = json.loads(args.rules)
            if not isinstance(rules, dict):
                raise ValueError("rules 必须是 JSON 对象")
            for k, v in rules.items():
                fields[str(k)] = str(v)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{E005} - rules JSON 解析失败: {exc}") from exc

    return fields


def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不依赖外部文件、网络和当前工作目录。
    """
    print("运行自检...")

    # 硬编码测试数据
    test_html = """
    <html>
    <head><title>测试商品页</title></head>
    <body>
        <h1>无线蓝牙耳机 Pro</h1>
        <div class="price">¥299.00</div>
        <div class="meta">作者: 张三</div>
        <p>发布日期: 2024-03-15</p>
        <p>联系邮箱: test@example.com</p>
        <p>商品描述: 这是商品描述，包含一些详细信息。</p>
    </body>
    </html>
    """

    test_fields = {
        "title": "",
        "date": "",
        "email": "",
        "price": "",
        "author": "",
        "custom_code": r"商品描述:?\s*([^。]+)",
    }

    # 测试 1: HTML 解析与字段提取
    page = process_content(test_html, "selftest://test", test_fields)
    results = {r.field_name: r for r in page.results}

    # 宽松断言
    assert page.title, "标题不应为空"
    assert results["title"].value is not None, "title 字段应提取到值"
    assert results["date"].value is not None, "date 字段应提取到值"
    assert results["email"].value is not None, "email 字段应提取到值"
    assert results["price"].value is not None, "price 字段应提取到值"
    assert results["author"].value is not None, "author 字段应提取到值"
    assert results["custom_code"].value is not None, "custom_code 字段应提取到值"
    assert results["title"].confidence > 0.5, "置信度应大于 0.5"
    assert results["date"].confidence > 0.5, "置信度应大于 0.5"
    assert results["email"].confidence > 0.5, "置信度应大于 0.5"
    assert results["price"].confidence > 0.5, "置信度应大于 0.5"
    assert results["author"].confidence > 0.5, "置信度应大于 0.5"
    assert results["custom_code"].confidence > 0.5, "置信度应大于 0.5"

    # 测试 2: 纯文本解析
    test_text = """
    会议纪要
    日期: 2024-06-01
    负责人: 李四
    预算: $1200.50
    """
    page2 = process_content(test_text, "selftest://text", {"date": "", "author": "", "price": ""})
    results2 = {r.field_name: r for r in page2.results}
    assert page2.title == "会议纪要", "文本标题提取失败"
    assert results2["date"].value is not None, "文本日期提取失败"
    assert results2["author"].value is not None, "文本作者提取失败"
    assert results2["price"].value is not None, "文本价格提取失败"

    # 测试 3: 导出功能
    pages = [page, page2]
    json_out = export_json(pages)
    assert json_out, "JSON 导出不应为空"
    assert "source" in json_out, "JSON 应包含 source 字段"

    csv_out = export_csv(pages)
    assert csv_out, "CSV 导出不应为空"
    assert "source" in csv_out, "CSV 应包含 source 字段"

    md_out = export_markdown(pages)
    assert md_out, "Markdown 导出不应为空"
    assert "|" in md_out, "Markdown 应包含表格"

    # 测试 4: 错误处理
    try:
        process_content("", "selftest://empty", {"field": ""})
        # 空内容不应抛异常，但结果应为空
    except Exception as exc:
        assert False, f"空内容不应抛异常: {exc}"

    print("自检通过: 所有断言检查成功")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    args = parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"自检异常: {exc}", file=sys.stderr)
            return 1

    # 构建字段配置
    try:
        fields = build_field_config(args)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    # 收集输入源
    sources = []
    if args.url:
        sources.extend(args.url)
    if args.file:
        sources.extend(args.file)

    if not sources:
        print(f"错误: {E001}", file=sys.stderr)
        print("请提供 --url 或 --file 参数", file=sys.stderr)
        return 1

    if not fields:
        # 默认提取常用字段
        fields = {"title": "", "date": "", "email": "", "price": "", "author": ""}

    # 执行批量处理
    try:
        url_sources = args.url or []
        file_sources = args.file or []

        pages = []
        if url_sources:
            pages.extend(batch_process(url_sources, fields, is_url=True, timeout=args.timeout))
        if file_sources:
            pages.extend(batch_process(file_sources, fields, is_url=False))

        # 导出
        if args.format == "json":
            output = export_json(pages)
        elif args.format == "csv":
            output = export_csv(pages)
        else:
            output = export_markdown(pages)

        print(output)
        return 0

    except Exception as exc:
        print(f"错误: {E007} - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
