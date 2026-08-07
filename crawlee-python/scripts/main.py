#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawlee-python 技能独立实现
============================
基于功能规格的 clean-room 重写，仅使用标准库。

功能概览:
    - 从 URL、本地 HTML 文件或原始文本中提取结构化数据
    - 默认 schema: title, content, links, tables
    - 支持用户自定义字段映射
    - 支持批量 URL 处理（≤50个/批）
    - 输出格式: JSON / CSV / Markdown
    - 内置离线自检（--selftest），不依赖外部环境

错误码:
    E001: 参数解析错误
    E002: 输入源类型不支持
    E003: 文件读取失败
    E004: URL 请求失败
    E005: HTML 解析失败
    E006: 字段映射配置错误
    E007: 输出格式不支持
    E008: 数据校验失败
    E009: 超出输入限制（数量/大小/超时）
    E010: 内部未知错误

用法示例:
    python main.py --url https://example.com
    python main.py --file ./page.html
    python main.py --text "<html>...</html>"
    python main.py --url-list urls.txt --format csv
    python main.py --selftest
"""

import argparse
import csv
import html.parser
import io
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================
DEFAULT_SCHEMA = ["title", "content", "links", "tables"]
MAX_URLS_PER_BATCH = 50
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
MAX_TASK_TIMEOUT_SECONDS = 120
MAX_CRAWL_DEPTH = 3

# ============================================================
# 自定义异常
# ============================================================
class SkillError(Exception):
    """技能基础异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ============================================================
# HTML 解析器（基于标准库 html.parser）
# ============================================================
class SimpleHTMLParser(html.parser.HTMLParser):
    """
    轻量级 HTML 解析器，提取:
        - 标题 (title 标签)
        - 正文文本 (剔除 script/style)
        - 链接 (a 标签 href)
        - 表格数据 (table 结构)
    """

    def __init__(self):
        super().__init__()
        self.title: str = ""
        self.text_parts: List[str] = []
        self.links: List[Dict[str, str]] = []
        self.tables: List[List[List[str]]] = []
        self._current_table: Optional[List[List[str]]] = None
        self._current_row: Optional[List[str]] = None
        self._current_cell: Optional[str] = None
        self._in_title = False
        self._in_script = False
        self._in_style = False
        self._skip_depth = 0  # 用于跳过嵌套标签

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag in ("script", "style"):
            self._in_script = True
            self._skip_depth = 1
        elif tag == "a":
            href = attr_dict.get("href", "")
            if href:
                self.links.append({"text": "", "href": href})
        elif tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in ("td", "th") and self._current_row is not None:
            self._current_cell = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" or tag == "style":
            self._in_script = False
            self._skip_depth = 0
        elif tag == "a" and self.links:
            # 将收集到的文本赋给最后一个链接
            self.links[-1]["text"] = self.links[-1]["text"].strip()
        elif tag == "tr" and self._current_row is not None:
            if self._current_table is not None:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag in ("td", "th") and self._current_cell is not None:
            if self._current_row is not None:
                self._current_row.append(self._current_cell.strip())
            self._current_cell = None
        elif tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._in_script or self._in_style:
            return
        if self._in_title:
            self.title += data
            return
        # 收集正文文本（去除多余空白）
        cleaned = re.sub(r"\s+", " ", data).strip()
        if cleaned:
            self.text_parts.append(cleaned)
        # 链接文本
        if self.links and data.strip():
            self.links[-1]["text"] += data.strip()
        # 表格单元格
        if self._current_cell is not None:
            self._current_cell += data

    def get_content_text(self) -> str:
        """合并正文片段，保留段落间距。"""
        return "\n".join(self.text_parts)


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ExtractionResult:
    """单条提取结果。"""
    source: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    status: str = "success"
    error: Optional[str] = None


# ============================================================
# 核心处理器
# ============================================================
class DataExtractor:
    """负责从不同源提取结构化数据。"""

    def __init__(self, schema: Optional[List[str]] = None):
        self.schema = schema or DEFAULT_SCHEMA

    def extract_from_html(self, html_content: str, source: str) -> Dict[str, Any]:
        """从 HTML 字符串提取数据。"""
        try:
            parser = SimpleHTMLParser()
            parser.feed(html_content)
            parser.close()

            result: Dict[str, Any] = {}
            if "title" in self.schema:
                result["title"] = parser.title.strip()
            if "content" in self.schema:
                result["content"] = parser.get_content_text()
            if "links" in self.schema:
                result["links"] = parser.links
            if "tables" in self.schema:
                result["tables"] = parser.tables

            # 补充自定义字段（如有）
            for field_name in self.schema:
                if field_name not in result:
                    result[field_name] = None

            return result
        except Exception as exc:
            raise SkillError("E005", f"HTML 解析失败: {exc}") from exc

    def extract_from_text(self, text: str, source: str) -> Dict[str, Any]:
        """从纯文本提取数据（简单结构）。"""
        result: Dict[str, Any] = {}
        if "title" in self.schema:
            # 取第一行作为标题
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            result["title"] = lines[0] if lines else ""
        if "content" in self.schema:
            result["content"] = text
        if "links" in self.schema:
            # 从文本中提取 URL
            urls = re.findall(r"https?://[^\s]+", text)
            result["links"] = [{"text": url, "href": url} for url in urls]
        if "tables" in self.schema:
            result["tables"] = []  # 纯文本无表格
        return result


# ============================================================
# 输入处理器
# ============================================================
class InputHandler:
    """处理不同类型的输入源。"""

    @staticmethod
    def read_local_file(file_path: str) -> str:
        """读取本地文件，支持 HTML 和纯文本。"""
        try:
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE_BYTES:
                raise SkillError("E009", f"文件大小 {file_size} 超过限制 {MAX_FILE_SIZE_BYTES} 字节")
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError as exc:
            raise SkillError("E003", f"文件读取失败: {exc}") from exc

    @staticmethod
    def fetch_url(url: str, timeout: int = 30) -> str:
        """从 URL 获取内容。"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # 限制读取大小
                content = resp.read(MAX_FILE_SIZE_BYTES + 1)
                if len(content) > MAX_FILE_SIZE_BYTES:
                    raise SkillError("E009", f"URL 内容超过 {MAX_FILE_SIZE_BYTES} 字节限制")
                # 尝试解码
                charset = resp.headers.get_content_charset() or "utf-8"
                return content.decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            raise SkillError("E004", f"URL 请求失败 (HTTP {exc.code}): {url}") from exc
        except urllib.error.URLError as exc:
            raise SkillError("E004", f"URL 请求失败: {url} - {exc.reason}") from exc
        except Exception as exc:
            raise SkillError("E004", f"URL 请求异常: {url} - {exc}") from exc

    @staticmethod
    def read_url_list(file_path: str) -> List[str]:
        """从文件读取 URL 列表。"""
        content = InputHandler.read_local_file(file_path)
        urls = [line.strip() for line in content.splitlines() if line.strip()]
        if len(urls) > MAX_URLS_PER_BATCH:
            raise SkillError("E009", f"URL 数量 {len(urls)} 超过限制 {MAX_URLS_PER_BATCH}")
        return urls


# ============================================================
# 输出格式化器
# ============================================================
class OutputFormatter:
    """将结果格式化为不同输出格式。"""

    @staticmethod
    def to_json(results: List[ExtractionResult]) -> str:
        """转换为 JSON 字符串。"""
        payload = [
            {
                "source": r.source,
                "data": r.data,
                "timestamp": r.timestamp,
                "status": r.status,
                "error": r.error,
            }
            for r in results
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(results: List[ExtractionResult]) -> str:
        """转换为 CSV 字符串。"""
        if not results:
            return ""
        # 收集所有可能的字段
        all_fields = set()
        for r in results:
            all_fields.update(r.data.keys())
        all_fields = sorted(all_fields)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["source", "status"] + all_fields)
        for r in results:
            row = [r.source, r.status]
            for field in all_fields:
                val = r.data.get(field, "")
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                row.append(val)
            writer.writerow(row)
        return output.getvalue()

    @staticmethod
    def to_markdown(results: List[ExtractionResult]) -> str:
        """转换为 Markdown 表格。"""
        if not results:
            return "_无数据_"
        # 收集字段
        all_fields = set()
        for r in results:
            all_fields.update(r.data.keys())
        all_fields = sorted(all_fields)

        lines = ["| 来源 | 状态 | " + " | ".join(all_fields) + " |"]
        lines.append("|------|------|" + "|".join(["------"] * len(all_fields)) + "|")
        for r in results:
            cells = [r.source, r.status]
            for field in all_fields:
                val = r.data.get(field, "")
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                cells.append(str(val).replace("|", "\\|"))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)


# ============================================================
# 主处理流程
# ============================================================
class CrawleeSkill:
    """技能主入口，协调各部分。"""

    def __init__(self, schema: Optional[List[str]] = None):
        self.extractor = DataExtractor(schema)
        self.input_handler = InputHandler()
        self.formatter = OutputFormatter()

    @staticmethod
    def is_html_content(content: str) -> bool:
        """检测内容是否为 HTML。"""
        # 检查是否有 HTML 标签
        content_lower = content.lower()
        html_markers = [
            "<html", "<head", "<body", "<div", "<p", "<span", 
            "<table", "<a ", "<title", "<h1", "<h2", "<h3",
            "<!doctype html", "<br", "<img", "<ul", "<ol", "<li"
        ]
        return any(marker in content_lower for marker in html_markers)

    def process_input(
        self,
        source_type: str,
        source_value: str,
        timeout: int = 30,
    ) -> List[ExtractionResult]:
        """处理单个或多个输入源。

        Args:
            source_type: "url", "file", "text", "url_list"
            source_value: 对应的值
            timeout: 超时时间（秒）

        Returns:
            提取结果列表
        """
        results: List[ExtractionResult] = []
        start_time = time.time()

        try:
            if source_type == "url":
                # 单 URL
                content = self.input_handler.fetch_url(source_value, timeout)
                data = self.extractor.extract_from_html(content, source_value)
                results.append(ExtractionResult(source=source_value, data=data))

            elif source_type == "file":
                # 本地文件
                content = self.input_handler.read_local_file(source_value)
                if source_value.lower().endswith((".html", ".htm")) or self.is_html_content(content):
                    data = self.extractor.extract_from_html(content, source_value)
                else:
                    data = self.extractor.extract_from_text(content, source_value)
                results.append(ExtractionResult(source=source_value, data=data))

            elif source_type == "text":
                # 直接文本，检测是否为 HTML
                if self.is_html_content(source_value):
                    data = self.extractor.extract_from_html(source_value, "inline-text")
                else:
                    data = self.extractor.extract_from_text(source_value, "inline-text")
                results.append(ExtractionResult(source="inline-text", data=data))

            elif source_type == "url_list":
                # URL 列表文件
                urls = self.input_handler.read_url_list(source_value)
                for url in urls:
                    # 检查总超时
                    if time.time() - start_time > MAX_TASK_TIMEOUT_SECONDS:
                        results.append(
                            ExtractionResult(
                                source=url,
                                data={},
                                status="timeout",
                                error="任务总超时",
                            )
                        )
                        break
                    try:
                        content = self.input_handler.fetch_url(url, timeout)
                        data = self.extractor.extract_from_html(content, url)
                        results.append(ExtractionResult(source=url, data=data))
                    except SkillError as exc:
                        results.append(
                            ExtractionResult(
                                source=url,
                                data={},
                                status="error",
                                error=str(exc),
                            )
                        )
            else:
                raise SkillError("E002", f"不支持的输入源类型: {source_type}")

        except SkillError:
            raise
        except Exception as exc:
            raise SkillError("E010", f"内部未知错误: {exc}") from exc

        return results

    def run(
        self,
        source_type: str,
        source_value: str,
        output_format: str = "json",
        timeout: int = 30,
    ) -> str:
        """执行完整流程，返回格式化输出。"""
        results = self.process_input(source_type, source_value, timeout)

        if output_format == "json":
            return self.formatter.to_json(results)
        elif output_format == "csv":
            return self.formatter.to_csv(results)
        elif output_format == "markdown":
            return self.formatter.to_markdown(results)
        else:
            raise SkillError("E007", f"不支持的输出格式: {output_format}")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用硬编码样例数据，不读外部文件、不访问网络。
    """
    print("=" * 60)
    print("crawlee-python 技能自检")
    print("=" * 60)

    # 硬编码 HTML 样例
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试页面标题</title>
        <style>body { color: red; }</style>
    </head>
    <body>
        <h1>欢迎</h1>
        <p>这是一段测试正文内容，包含一些文字。</p>
        <p>第二段正文，用于验证内容提取。</p>
        <a href="https://example.com/page1">链接一</a>
        <a href="https://example.com/page2">链接二</a>
        <table>
            <tr><th>姓名</th><th>年龄</th></tr>
            <tr><td>张三</td><td>25</td></tr>
            <tr><td>李四</td><td>30</td></tr>
        </table>
        <script>var x = 1;</script>
    </body>
    </html>
    """

    # 测试 1: HTML 解析
    print("\n[测试 1] HTML 解析")
    try:
        extractor = DataExtractor()
        data = extractor.extract_from_html(sample_html, "selftest-html")
        assert data["title"] == "测试页面标题", f"标题提取失败: {data['title']}"
        assert "测试正文内容" in data["content"], "正文提取失败"
        assert len(data["links"]) >= 2, "链接提取数量不足"
        assert len(data["tables"]) >= 1, "表格提取失败"
        assert len(data["tables"][0]) >= 3, "表格行数不足"
        print("  ✓ 标题、正文、链接、表格提取正常")
        print(f"    标题: {data['title']}")
        print(f"    正文长度: {len(data['content'])} 字符")
        print(f"    链接数: {len(data['links'])}")
        print(f"    表格行数: {len(data['tables'][0])}")
    except AssertionError as exc:
        print(f"  ✗ 断言失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # 测试 2: 纯文本解析
    print("\n[测试 2] 纯文本解析")
    try:
        sample_text = "这是标题行\n这是正文内容，包含网址 https://example.com/test"
        data = extractor.extract_from_text(sample_text, "selftest-text")
        assert data["title"] == "这是标题行", f"标题提取失败: {data['title']}"
        assert len(data["links"]) >= 1, "URL 提取失败"
        print("  ✓ 纯文本解析正常")
        print(f"    标题: {data['title']}")
        print(f"    链接数: {len(data['links'])}")
    except AssertionError as exc:
        print(f"  ✗ 断言失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # 测试 3: 输出格式化
    print("\n[测试 3] 输出格式化")
    try:
        results = [
            ExtractionResult(
                source="test-source",
                data={"title": "测试", "content": "内容", "links": [], "tables": []},
            )
        ]
        formatter = OutputFormatter()
        json_out = formatter.to_json(results)
        csv_out = formatter.to_csv(results)
        md_out = formatter.to_markdown(results)
        assert json_out, "JSON 输出为空"
        assert "测试" in csv_out, "CSV 输出异常"
        assert "测试" in md_out, "Markdown 输出异常"
        print("  ✓ JSON/CSV/Markdown 格式化正常")
        print(f"    JSON 长度: {len(json_out)}")
        print(f"    CSV 长度: {len(csv_out)}")
        print(f"    MD 长度: {len(md_out)}")
    except AssertionError as exc:
        print(f"  ✗ 断言失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # 测试 4: 端到端流程
    print("\n[测试 4] 端到端流程")
    try:
        skill = CrawleeSkill()
        output = skill.run("text", sample_html, "json")
        parsed = json.loads(output)
        assert len(parsed) == 1, "结果数量不对"
        assert parsed[0]["status"] == "success", "处理状态不对"
        assert parsed[0]["data"]["title"] == "测试页面标题", "标题提取失败"
        print("  ✓ 端到端 JSON 输出正常")
    except AssertionError as exc:
        print(f"  ✗ 断言失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # 测试 5: 错误处理
    print("\n[测试 5] 错误处理")
    try:
        # 不支持的输入类型
        try:
            skill.run("invalid_type", "value", "json")
            print("  ✗ 未捕获不支持的输入类型")
            return 1
        except SkillError as exc:
            assert exc.code == "E002", f"错误码不对: {exc.code}"
            print(f"  ✓ 正确捕获 E002: {exc.message}")

        # 不存在的文件
        try:
            skill.run("file", "/nonexistent/path/file.html", "json")
            print("  ✗ 未捕获文件不存在")
            return 1
        except SkillError as exc:
            assert exc.code == "E003", f"错误码不对: {exc.code}"
            print(f"  ✓ 正确捕获 E003: {exc.message}")

        # 不支持的输出格式
        try:
            skill.run("text", "hello", "xml")
            print("  ✗ 未捕获不支持的输出格式")
            return 1
        except SkillError as exc:
            assert exc.code == "E007", f"错误码不对: {exc.code}"
            print(f"  ✓ 正确捕获 E007: {exc.message}")
    except AssertionError as exc:
        print(f"  ✗ 断言失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    print("\n" + "=" * 60)
    print("所有自检通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="crawlee-python 网页采集与结构化输出技能",
        epilog="示例: python main.py --url https://example.com --format json",
    )
    parser.add_argument("--url", help="要抓取的单个 URL")
    parser.add_argument("--file", help="本地 HTML/文本文件路径")
    parser.add_argument("--text", help="直接传入 HTML 或文本内容")
    parser.add_argument("--url-list", help="包含 URL 列表的文件路径")
    parser.add_argument(
        "--format",
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="请求超时秒数 (默认: 30)")
    parser.add_argument(
        "--schema",
        nargs="+",
        default=DEFAULT_SCHEMA,
        help=f"自定义字段 schema (默认: {DEFAULT_SCHEMA})",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入参数
    input_count = sum(
        1 for v in [args.url, args.file, args.text, args.url_list] if v is not None
    )
    if input_count != 1:
        print("错误: 必须且只能指定一种输入源 (--url / --file / --text / --url-list)")
        return 1

    try:
        skill = CrawleeSkill(schema=args.schema)

        if args.url:
            output = skill.run("url", args.url, args.format, args.timeout)
        elif args.file:
            output = skill.run("file", args.file, args.format, args.timeout)
        elif args.text:
            output = skill.run("text", args.text, args.format, args.timeout)
        elif args.url_list:
            output = skill.run("url_list", args.url_list, args.format, args.timeout)
        else:
            print("错误: 未指定输入源")
            return 1

        print(output)
        return 0

    except SkillError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
