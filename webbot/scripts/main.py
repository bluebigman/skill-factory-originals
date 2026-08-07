#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webbot — 网页采集与结构化输出 Skill 的独立实现

本脚本依据功能规格 clean-room 重写，仅依赖 Python 标准库。
支持将文本/HTML/URL 内容转化为结构化数据，并输出置信度标注。

用法示例:
    python main.py --selftest              # 离线自检
    python main.py --input sample.html     # 处理本地文件
    python main.py --url https://...       # 处理网页（需网络）
    python main.py --text "..."            # 处理纯文本
    python main.py --format json --batch file1.html file2.html

错误码说明:
    E001 参数错误
    E002 输入源不可用（文件不存在/URL 无法访问）
    E003 输入内容为空
    E004 结构化解析失败
    E005 输出格式不支持
    E006 批量处理中断
    E007 置信度计算异常
    E008 字段提取异常
    E009 内部逻辑错误
    E010 未知异常
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
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ExtractedField:
    """单个提取字段的结果"""
    name: str
    value: Any
    confidence: float = 0.5          # 0.0 ~ 1.0
    source: str = "unknown"          # 来源说明（如 html_title / meta / text）
    raw: Optional[str] = None        # 原始匹配文本


@dataclass
class ExtractionResult:
    """一次提取的完整结果"""
    url: str = ""
    title: str = ""
    author: str = ""
    date: str = ""
    content: str = ""
    fields: List[ExtractedField] = field(default_factory=list)
    confidence: float = 0.0          # 整体置信度
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典结构（用于 JSON 输出）"""
        return {
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "content_preview": self.content[:200] if self.content else "",
            "content_length": len(self.content),
            "fields": [
                {
                    "name": f.name,
                    "value": f.value,
                    "confidence": round(f.confidence, 3),
                    "source": f.source,
                }
                for f in self.fields
            ],
            "overall_confidence": round(self.confidence, 3),
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心提取引擎（纯标准库实现）
# ---------------------------------------------------------------------------

class _HTMLTextExtractor(html.parser.HTMLParser):
    """简易 HTML -> 纯文本提取器"""

    def __init__(self) -> None:
        super().__init__()
        self._text_parts: List[str] = []
        self._skip_depth = 0
        self._title: Optional[str] = None
        self._meta: Dict[str, str] = {}
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        for key, val in attrs:
            if key.lower() in ("name", "property", "http-equiv") and val:
                # 收集 meta 标签的内容
                for k2, v2 in attrs:
                    if k2.lower() == "content" and v2:
                        self._meta[val.lower()] = v2

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("script", "style", "noscript") and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            if self._title is None:
                self._title = data.strip()
            return
        text = data.strip()
        if text:
            self._text_parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._text_parts)

    def get_title(self) -> str:
        return self._title or ""


class ExtractionEngine:
    """核心提取引擎：从文本/HTML 中抽取结构化字段"""

    # 常见字段的简单正则模式
    _PATTERNS = {
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "phone": r"(?:\+?86[- ]?)?1[3-9]\d{9}|(?:\+?86[- ]?)?0\d{2,3}[- ]?\d{7,8}",
        "price": r"(?:￥|¥|RMB|CNY|USD|€|£)?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\s?(?:元|块|美元|欧元|英镑)?",
        "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        "url": r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
        "id": r"[A-Za-z0-9_-]{8,32}",
    }

    # 置信度权重
    _CONFIDENCE_MAP = {
        "title": 0.9,
        "author": 0.7,
        "date": 0.8,
        "email": 0.95,
        "phone": 0.9,
        "price": 0.85,
        "url": 0.9,
        "id": 0.5,
        "content": 0.6,
    }

    def extract_from_text(self, text: str, source_url: str = "") -> ExtractionResult:
        """从纯文本中提取结构化信息"""
        if not text or not text.strip():
            raise ValueError("E003: 输入内容为空")

        result = ExtractionResult(url=source_url)
        result.content = text.strip()

        # 提取标题（第一行非空文本作为标题候选）
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            candidate = lines[0]
            # 启发式：标题通常较短（< 100 字符）
            if len(candidate) <= 100:
                result.title = candidate
                result.fields.append(ExtractedField(
                    name="title", value=candidate,
                    confidence=self._CONFIDENCE_MAP["title"],
                    source="first_line"
                ))

        # 提取作者（常见模式）
        author_match = re.search(r"(?:作者|撰文|by|author)[：:\s]*([^\n|,，。]{2,30})", text, re.I)
        if author_match:
            author = author_match.group(1).strip()
            result.author = author
            result.fields.append(ExtractedField(
                name="author", value=author,
                confidence=self._CONFIDENCE_MAP["author"],
                source="pattern"
            ))

        # 提取日期
        date_match = re.search(self._PATTERNS["date"], text)
        if date_match:
            result.date = date_match.group(0)
            result.fields.append(ExtractedField(
                name="date", value=result.date,
                confidence=self._CONFIDENCE_MAP["date"],
                source="pattern"
            ))

        # 提取其他常见字段
        for field_name, pattern in self._PATTERNS.items():
            if field_name in ("date",):
                continue  # 已处理
            matches = re.findall(pattern, text)
            if matches:
                # 去重并取前 3 个
                unique = list(dict.fromkeys(matches))[:3]
                result.fields.append(ExtractedField(
                    name=field_name, value=unique,
                    confidence=self._CONFIDENCE_MAP.get(field_name, 0.5),
                    source="regex"
                ))

        # 计算整体置信度
        result.confidence = self._compute_overall_confidence(result)
        return result

    def extract_from_html(self, html_content: str, source_url: str = "") -> ExtractionResult:
        """从 HTML 内容中提取结构化信息"""
        if not html_content or not html_content.strip():
            raise ValueError("E003: 输入内容为空")

        # 解析 HTML
        parser = _HTMLTextExtractor()
        try:
            parser.feed(html_content)
        except Exception as exc:
            raise ValueError(f"E004: HTML 解析失败: {exc}") from exc

        text = parser.get_text()
        result = ExtractionResult(url=source_url)
        result.content = text

        # 标题（优先从 <title> 标签）
        html_title = parser.get_title()
        if html_title:
            result.title = html_title
            result.fields.append(ExtractedField(
                name="title", value=html_title,
                confidence=self._CONFIDENCE_MAP["title"],
                source="html_title"
            ))
        else:
            # 回退到第一行
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines and len(lines[0]) <= 100:
                result.title = lines[0]
                result.fields.append(ExtractedField(
                    name="title", value=lines[0],
                    confidence=self._CONFIDENCE_MAP["title"] * 0.8,
                    source="first_line_fallback"
                ))

        # 从 meta 标签提取作者/日期
        meta_author = parser._meta.get("author") or parser._meta.get("article:author")
        if meta_author:
            result.author = meta_author.strip()
            result.fields.append(ExtractedField(
                name="author", value=result.author,
                confidence=self._CONFIDENCE_MAP["author"],
                source="meta"
            ))

        meta_date = parser._meta.get("date") or parser._meta.get("article:published_time")
        if meta_date:
            result.date = meta_date.strip()
            result.fields.append(ExtractedField(
                name="date", value=result.date,
                confidence=self._CONFIDENCE_MAP["date"],
                source="meta"
            ))

        # 从正文文本中补充提取
        if not result.author:
            author_match = re.search(r"(?:作者|撰文|by)[：:\s]*([^\n|,，。]{2,30})", text, re.I)
            if author_match:
                result.author = author_match.group(1).strip()
                result.fields.append(ExtractedField(
                    name="author", value=result.author,
                    confidence=self._CONFIDENCE_MAP["author"] * 0.8,
                    source="pattern"
                ))

        if not result.date:
            date_match = re.search(self._PATTERNS["date"], text)
            if date_match:
                result.date = date_match.group(0)
                result.fields.append(ExtractedField(
                    name="date", value=result.date,
                    confidence=self._CONFIDENCE_MAP["date"],
                    source="pattern"
                ))

        # 提取其他字段
        for field_name, pattern in self._PATTERNS.items():
            if field_name in ("date",):
                continue
            matches = re.findall(pattern, text)
            if matches:
                unique = list(dict.fromkeys(matches))[:3]
                result.fields.append(ExtractedField(
                    name=field_name, value=unique,
                    confidence=self._CONFIDENCE_MAP.get(field_name, 0.5),
                    source="regex"
                ))

        result.confidence = self._compute_overall_confidence(result)
        return result

    def _compute_overall_confidence(self, result: ExtractionResult) -> float:
        """计算整体置信度（加权平均）"""
        if not result.fields:
            return 0.0
        total_weight = 0.0
        weighted_sum = 0.0
        for f in result.fields:
            w = self._CONFIDENCE_MAP.get(f.name, 0.5)
            weighted_sum += f.confidence * w
            total_weight += w
        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight


# ---------------------------------------------------------------------------
# 输入处理
# ---------------------------------------------------------------------------

def _read_text_file(filepath: str) -> str:
    """读取文本文件内容"""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"E002: 文件不存在: {filepath}")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _read_url(url: str, timeout: float = 10.0) -> str:
    """读取 URL 内容（简单请求，遵守 2 秒间隔）"""
    time.sleep(2)  # 规格要求：单次任务请求间隔不低于 2 秒
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (webbot-skill)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            data = resp.read()
            return data.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        raise ConnectionError(f"E002: HTTP {exc.code} 无法访问: {url}") from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(f"E002: URL 访问失败: {url} ({exc.reason})") from exc


def _detect_html(content: str) -> bool:
    """简单检测内容是否为 HTML"""
    sample = content[:2000].lstrip().lower()
    return sample.startswith("<!doctype html") or sample.startswith("<html") or "<html" in sample[:500]


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def _format_output(results: List[ExtractionResult], fmt: str) -> str:
    """按指定格式输出结果"""
    fmt = fmt.lower()
    if fmt == "json":
        return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)

    if fmt == "csv":
        # 扁平化字段输出
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["url", "title", "author", "date", "field_name", "field_value", "confidence", "source"])
        for r in results:
            if not r.fields:
                writer.writerow([r.url, r.title, r.author, r.date, "", "", "", ""])
            for f in r.fields:
                val = f.value
                if isinstance(val, list):
                    val = "; ".join(str(v) for v in val)
                writer.writerow([r.url, r.title, r.author, r.date, f.name, val, f"{f.confidence:.3f}", f.source])
        return output.getvalue()

    if fmt == "text":
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"=== 结果 {i} ===")
            lines.append(f"URL: {r.url or '(无)'}")
            lines.append(f"标题: {r.title or '(未提取)'}")
            lines.append(f"作者: {r.author or '(未提取)'}")
            lines.append(f"日期: {r.date or '(未提取)'}")
            lines.append(f"内容长度: {len(r.content)}")
            lines.append(f"整体置信度: {r.confidence:.2f}")
            for f in r.fields:
                val = f.value
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                lines.append(f"  [{f.name}] {val} (置信度: {f.confidence:.2f}, 来源: {f.source})")
            if r.warnings:
                lines.append(f"警告: {'; '.join(r.warnings)}")
            lines.append("")
        return "\n".join(lines)

    raise ValueError(f"E005: 不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def _process_batch(inputs: List[str], input_type: str, engine: ExtractionEngine) -> List[ExtractionResult]:
    """批量处理多个输入"""
    results: List[ExtractionResult] = []
    errors: List[str] = []

    for item in inputs:
        try:
            if input_type == "file":
                content = _read_text_file(item)
            elif input_type == "url":
                content = _read_url(item)
            else:  # text
                content = item

            if _detect_html(content):
                result = engine.extract_from_html(content, source_url=item if input_type == "url" else "")
            else:
                result = engine.extract_from_text(content, source_url=item if input_type == "url" else "")
            results.append(result)
        except Exception as exc:
            errors.append(f"{item}: {exc}")

    if errors:
        # 部分失败时附加警告信息
        if results:
            results[0].warnings.extend(errors)
        else:
            raise RuntimeError(f"E006: 批量处理全部失败: {'; '.join(errors)}")

    return results


# ---------------------------------------------------------------------------
# 自检模块（硬编码样例，离线运行）
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """离线自检核心逻辑，不依赖外部文件/网络"""
    print("[selftest] 开始自检...")

    # 硬编码测试样例
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试商品页面 - 智能手表 X100</title>
        <meta name="author" content="张三">
        <meta name="date" content="2026-03-15">
    </head>
    <body>
        <h1>智能手表 X100 旗舰版</h1>
        <p>价格：￥1999.00 元</p>
        <p>联系方式：seller@example.com</p>
        <p>联系电话：13800138000</p>
        <p>这是一段用于测试的商品描述文本，包含足够多的内容用于提取。</p>
    </body>
    </html>
    """

    sample_text = """
    新闻稿：某公司发布新产品
    作者：李四
    日期：2026-01-20
    这是一篇测试文本，包含邮箱 contact@test.org 和价格 $99.99。
    内容足够长，用于验证纯文本提取逻辑。
    """

    engine = ExtractionEngine()

    # 测试 1: HTML 提取
    try:
        result_html = engine.extract_from_html(sample_html, source_url="https://example.com/product")
        assert result_html.title, "HTML 标题提取失败"
        assert "智能手表" in result_html.title, f"标题内容异常: {result_html.title}"
        assert result_html.author, "HTML 作者提取失败"
        assert result_html.date, "HTML 日期提取失败"
        assert result_html.confidence > 0.5, f"HTML 置信度异常偏低: {result_html.confidence}"
        assert len(result_html.fields) >= 3, f"HTML 字段数异常: {len(result_html.fields)}"
        print(f"[selftest] HTML 提取通过 (标题: {result_html.title}, 置信度: {result_html.confidence:.2f})")
    except AssertionError as exc:
        print(f"[selftest] HTML 提取失败: {exc}")
        return 1
    except Exception as exc:
        print(f"[selftest] HTML 提取异常: {exc}")
        return 1

    # 测试 2: 纯文本提取
    try:
        result_text = engine.extract_from_text(sample_text)
        assert result_text.title, "文本标题提取失败"
        assert "某公司" in result_text.title, f"文本标题内容异常: {result_text.title}"
        assert result_text.author, "文本作者提取失败"
        assert result_text.date, "文本日期提取失败"
        assert result_text.confidence > 0.3, f"文本置信度异常: {result_text.confidence}"
        assert len(result_text.fields) >= 3, f"文本字段数异常: {len(result_text.fields)}"
        print(f"[selftest] 文本提取通过 (标题: {result_text.title}, 置信度: {result_text.confidence:.2f})")
    except AssertionError as exc:
        print(f"[selftest] 文本提取失败: {exc}")
        return 1
    except Exception as exc:
        print(f"[selftest] 文本提取异常: {exc}")
        return 1

    # 测试 3: 输出格式
    try:
        json_out = _format_output([result_html, result_text], "json")
        parsed = json.loads(json_out)
        assert len(parsed) == 2, f"JSON 输出条目数异常: {len(parsed)}"
        assert "fields" in parsed[0], "JSON 输出缺少 fields 字段"

        csv_out = _format_output([result_html], "csv")
        assert "title" in csv_out.lower(), "CSV 输出缺少表头"

        text_out = _format_output([result_html], "text")
        assert "=== 结果" in text_out, "文本输出格式异常"
        print("[selftest] 输出格式通过")
    except Exception as exc:
        print(f"[selftest] 输出格式失败: {exc}")
        return 1

    # 测试 4: 错误处理
    try:
        engine.extract_from_text("")
        print("[selftest] 错误处理失败: 空输入未抛出异常")
        return 1
    except ValueError as exc:
        assert "E003" in str(exc), f"错误码异常: {exc}"
        print("[selftest] 错误处理通过")

    # 测试 5: 批量处理
    try:
        batch_results = _process_batch([sample_html, sample_text], "text", engine)
        assert len(batch_results) == 2, f"批量处理数量异常: {len(batch_results)}"
        print("[selftest] 批量处理通过")
    except Exception as exc:
        print(f"[selftest] 批量处理失败: {exc}")
        return 1

    print("[selftest] 全部自检通过 ✅")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="webbot - 网页采集与结构化输出",
        epilog="示例: python main.py --url https://example.com --format json"
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--url", "-u", help="输入 URL")
    parser.add_argument("--text", "-t", help="直接输入文本内容")
    parser.add_argument("--format", "-f", choices=["json", "csv", "text"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--batch", nargs="+", help="批量处理多个文件/URL")
    parser.add_argument("--batch-type", choices=["file", "url", "text"], default="file",
                        help="批量输入类型 (默认: file)")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 检查输入参数
    input_count = sum(1 for x in [args.input, args.url, args.text, args.batch] if x)
    if input_count == 0:
        print("E001: 必须提供输入（--input/--url/--text/--batch 之一）", file=sys.stderr)
        return 1
    if input_count > 1:
        print("E001: 只能选择一种输入方式", file=sys.stderr)
        return 1

    engine = ExtractionEngine()

    try:
        if args.batch:
            # 批量处理
            results = _process_batch(args.batch, args.batch_type, engine)
        else:
            # 单次处理
            if args.input:
                content = _read_text_file(args.input)
                source = args.input
            elif args.url:
                content = _read_url(args.url)
                source = args.url
            else:
                content = args.text
                source = ""

            if _detect_html(content):
                result = engine.extract_from_html(content, source_url=source)
            else:
                result = engine.extract_from_text(content, source_url=source)
            results = [result]

        # 输出结果
        output = _format_output(results, args.format)
        print(output)
        return 0

    except FileNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except ConnectionError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
