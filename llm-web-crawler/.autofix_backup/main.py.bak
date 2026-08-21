#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-web-crawler — 网页采集与结构化提取技能（独立实现）
=========================================================
根据功能规格独立开发的 clean-room 实现。
仅使用 Python 标准库，无第三方依赖。

功能：
1. 内容解析：从 HTML/文本中提取标题、作者、日期、正文
2. 关键信息识别：按字段定义抽取实体
3. 结构化转换：文本 -> JSON / CSV / Markdown 表格
4. 批量处理：多记录循环处理与合并
5. 置信度标注：不确定字段输出占位符标记

用法示例：
    python main.py --parse "<html>...</html>"
    python main.py --extract "招聘信息文本" --fields company,position
    python main.py --convert "产品描述" --format json
    python main.py --batch urls.txt
    python main.py --selftest

错误码说明：
    E001: 参数错误或缺少必要参数
    E002: 输入内容为空
    E003: HTML 解析失败
    E004: 字段定义无效
    E005: 输出格式不支持
    E006: 批量处理输入文件错误
    E007: URL 格式无效
    E008: 内部逻辑错误（不应发生）
    E009: 编码错误
    E010: 未知错误
"""

import argparse
import csv
import html.parser
import io
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误定义
# ============================================================

class CrawlerError(Exception):
    """技能基础异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def error_exit(code: str, message: str) -> None:
    """输出错误信息并退出。"""
    print(f"错误: [{code}] {message}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 数据模型
# ============================================================

@dataclass
class PageContent:
    """解析后的页面内容。"""
    title: str = ""
    author: str = ""
    publish_date: str = ""
    content: str = ""
    url: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        result = {
            "title": self.title or "[未提供]",
            "author": self.author or "[未提供]",
            "publish_date": self.publish_date or "[未提供]",
            "content": self.content,
            "url": self.url,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class ExtractionResult:
    """字段提取结果。"""
    fields: Dict[str, str] = field(default_factory=dict)
    confidence: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "fields": self.fields,
            "confidence": self.confidence,
        }


# ============================================================
# 内容解析器
# ============================================================

class _HTMLTextExtractor(html.parser.HTMLParser):
    """HTML 文本提取器（内部类）。"""
    SKIP_TAGS = {"script", "style", "noscript", "iframe", "svg"}
    BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._text_parts: List[str] = []
        self._skip_depth = 0
        self._block_stack: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag in self.BLOCK_TAGS and self._skip_depth == 0:
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in self.BLOCK_TAGS and self._skip_depth == 0:
            self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._text_parts.append(data)

    def get_text(self) -> str:
        """获取提取的纯文本。"""
        raw = "".join(self._text_parts)
        # 合并多个换行为单个，去除前后空白
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        return "\n".join(lines)


def extract_title_from_html(html_text: str) -> str:
    """从 HTML 中提取标题。"""
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    if match:
        # 去除内部标签
        title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        return title
    # 尝试 h1
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return ""


def extract_meta_from_html(html_text: str) -> Dict[str, str]:
    """从 HTML meta 标签提取元信息。"""
    meta: Dict[str, str] = {}
    # author
    match = re.search(r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']*)["\']', html_text, re.IGNORECASE)
    if match:
        meta["author"] = match.group(1).strip()
    # date (多种可能)
    for prop in ["article:published_time", "date", "pubdate", "publish_date"]:
        match = re.search(
            rf'<meta[^>]*(?:name|property)=["\']{prop}["\'][^>]*content=["\']([^"\']*)["\']',
            html_text, re.IGNORECASE
        )
        if match:
            meta["publish_date"] = match.group(1).strip()
            break
    # description
    match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html_text, re.IGNORECASE)
    if match:
        meta["description"] = match.group(1).strip()
    return meta


def parse_html(html_text: str, url: str = "") -> PageContent:
    """解析 HTML 内容。"""
    if not html_text or not html_text.strip():
        raise CrawlerError("E002", "HTML 内容为空")
    try:
        extractor = _HTMLTextExtractor()
        extractor.feed(html_text)
        content_text = extractor.get_text()

        title = extract_title_from_html(html_text)
        meta = extract_meta_from_html(html_text)

        page = PageContent(
            title=title,
            author=meta.get("author", ""),
            publish_date=meta.get("publish_date", ""),
            content=content_text,
            url=url,
            metadata={k: v for k, v in meta.items() if k not in ("author", "publish_date")},
        )
        return page
    except CrawlerError:
        raise
    except Exception as exc:
        raise CrawlerError("E003", f"HTML 解析失败: {exc}") from exc


def parse_plain_text(text: str, url: str = "") -> PageContent:
    """解析纯文本内容。"""
    if not text or not text.strip():
        raise CrawlerError("E002", "文本内容为空")
    # 简单的标题猜测：第一行非空文本
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    title = lines[0] if lines else ""
    content = "\n".join(lines[1:]) if len(lines) > 1 else ""
    return PageContent(title=title, content=content, url=url)


def parse_content(raw_text: str, url: str = "", is_html: bool = False) -> PageContent:
    """根据内容类型自动解析。"""
    if not raw_text or not raw_text.strip():
        raise CrawlerError("E002", "输入内容为空")
    if is_html or "<html" in raw_text.lower() or "<body" in raw_text.lower():
        return parse_html(raw_text, url)
    return parse_plain_text(raw_text, url)


# ============================================================
# 关键信息提取
# ============================================================

# 常见字段的默认提取规则（正则表达式）
DEFAULT_FIELD_PATTERNS: Dict[str, str] = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "phone": r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
    "url": r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{4}[-/]\d{1,2}[-/]\d{1,2}",
    "price": r"(?:人民币|CNY|￥|¥|RMB)?\s*\d+(?:\.\d{1,2})?\s*(?:元|块|美元|USD)?",
    "ip_address": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
}

# 中文常见字段的上下文关键词
FIELD_CONTEXT_KEYWORDS: Dict[str, List[str]] = {
    "company": ["公司", "企业", "单位", "集团", "有限公司"],
    "position": ["职位", "岗位", "职务", "招聘"],
    "location": ["地点", "地址", "城市", "区域", "位置"],
    "salary": ["薪资", "工资", "薪酬", "待遇"],
    "name": ["姓名", "名字", "联系人"],
    "education": ["学历", "教育", "学位"],
    "experience": ["经验", "工作经历"],
}


def _extract_by_pattern(text: str, pattern: str) -> List[str]:
    """使用正则提取所有匹配项。"""
    try:
        return re.findall(pattern, text)
    except re.error:
        return []


def _extract_by_context(text: str, field_name: str) -> List[str]:
    """通过上下文关键词提取字段值。"""
    keywords = FIELD_CONTEXT_KEYWORDS.get(field_name.lower(), [])
    if not keywords:
        return []
    results = []
    for kw in keywords:
        # 查找关键词位置
        for match in re.finditer(re.escape(kw), text):
            start = match.start()
            # 取关键词后的一段文本（最多 50 字符）
            segment = text[start + len(kw):start + len(kw) + 50]
            # 取到标点或换行为止
            value = re.split(r"[。；;，,\n\r]", segment)[0].strip()
            if value and len(value) > 1 and not value.endswith(":"):
                results.append(value)
    return results


def extract_fields(text: str, fields: List[str]) -> ExtractionResult:
    """从文本中提取指定字段。"""
    if not text or not text.strip():
        raise CrawlerError("E002", "输入文本为空")
    if not fields:
        raise CrawlerError("E004", "字段列表为空")

    result = ExtractionResult()

    for field_name in fields:
        fname = field_name.strip().lower()
        if not fname:
            continue

        # 尝试默认正则模式
        values: List[str] = []
        if fname in DEFAULT_FIELD_PATTERNS:
            values = _extract_by_pattern(text, DEFAULT_FIELD_PATTERNS[fname])

        # 尝试上下文关键词提取
        if not values:
            values = _extract_by_context(text, fname)

        # 通用 fallback：字段名后跟冒号的值
        if not values:
            pattern = rf"{re.escape(field_name)}[\s:：]{{1,2}}([^\n\r;；，,]+)"
            values = re.findall(pattern, text, re.IGNORECASE)
            values = [v.strip() for v in values if v.strip()]

        # 去重保序
        unique_values: List[str] = []
        for v in values:
            v = v.strip()
            if v and v not in unique_values:
                unique_values.append(v)

        if unique_values:
            result.fields[fname] = unique_values[0]
            # 置信度：有多个候选时降低
            if len(unique_values) > 1:
                result.confidence[fname] = 0.6
            else:
                result.confidence[fname] = 0.9
        else:
            # 未找到，输出占位符
            result.fields[fname] = f"[需核实:{field_name}]"
            result.confidence[fname] = 0.0

    return result


# ============================================================
# 结构化转换
# ============================================================

def convert_to_json(data: Any, pretty: bool = True) -> str:
    """转换为 JSON 字符串。"""
    try:
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise CrawlerError("E005", f"JSON 转换失败: {exc}") from exc


def convert_to_csv(rows: List[Dict[str, Any]]) -> str:
    """转换为 CSV 字符串。"""
    if not rows:
        return ""
    try:
        output = io.StringIO()
        # 获取所有键（保持顺序）
        all_keys: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in all_keys:
                    all_keys.append(key)
        writer = csv.DictWriter(output, fieldnames=all_keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return output.getvalue()
    except Exception as exc:
        raise CrawlerError("E005", f"CSV 转换失败: {exc}") from exc


def convert_to_markdown(rows: List[Dict[str, Any]]) -> str:
    """转换为 Markdown 表格。"""
    if not rows:
        return ""
    try:
        all_keys: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in all_keys:
                    all_keys.append(key)

        lines = []
        # 表头
        lines.append("| " + " | ".join(all_keys) + " |")
        # 分隔行
        lines.append("|" + "|".join([" --- "] * len(all_keys)) + "|")
        # 数据行
        for row in rows:
            values = [str(row.get(key, "")) for key in all_keys]
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)
    except Exception as exc:
        raise CrawlerError("E005", f"Markdown 转换失败: {exc}") from exc


def convert_data(data: Any, output_format: str) -> str:
    """按指定格式转换数据。"""
    fmt = output_format.lower().strip()
    if fmt == "json":
        return convert_to_json(data)
    elif fmt == "csv":
        if not isinstance(data, list):
            data = [data]
        return convert_to_csv(data)
    elif fmt == "markdown" or fmt == "md":
        if not isinstance(data, list):
            data = [data]
        return convert_to_markdown(data)
    else:
        raise CrawlerError("E005", f"不支持的输出格式: {output_format}")


# ============================================================
# 批量处理
# ============================================================

def batch_process(items: List[str], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """批量处理多个文本/URL。"""
    results = []
    for item in items:
        try:
            # 尝试作为 URL 处理
            if item.startswith(("http://", "https://")):
                # 注意：本实现不实际访问网络，仅做格式校验
                parsed = urllib.parse.urlparse(item)
                if not parsed.netloc:
                    raise CrawlerError("E007", f"无效 URL: {item}")
                # 模拟：将 URL 作为文本处理
                page = parse_plain_text(f"URL: {item}\n内容: [静态模式，未实际抓取]", item)
                results.append(page.to_dict())
            else:
                # 作为纯文本处理
                page = parse_plain_text(item)
                if fields:
                    extraction = extract_fields(item, fields)
                    result = page.to_dict()
                    result["extracted"] = extraction.to_dict()
                    results.append(result)
                else:
                    results.append(page.to_dict())
        except CrawlerError as exc:
            results.append({"error": exc.code, "message": exc.message, "input": item[:100]})
    return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> None:
    """运行内置自检，验证核心逻辑。"""
    print("=== 自检开始 ===")
    errors: List[str] = []

    # --- 测试 1: 解析 HTML ---
    try:
        sample_html = """<html>
<head>
  <title>测试文章标题</title>
  <meta name="author" content="张三">
  <meta property="article:published_time" content="2026-01-15">
</head>
<body>
  <h1>测试文章标题</h1>
  <div class="content">
    <p>这是第一段正文内容。</p>
    <p>这是第二段正文内容，包含 <b>加粗</b> 文本。</p>
  </div>
</body>
</html>"""
        page = parse_html(sample_html)
        assert page.title == "测试文章标题", f"标题提取失败: {page.title}"
        assert page.author == "张三", f"作者提取失败: {page.author}"
        assert "2026-01-15" in page.publish_date, f"日期提取失败: {page.publish_date}"
        assert "第一段正文内容" in page.content, "正文内容缺失"
        assert "加粗" in page.content, "正文中应包含加粗文本"
        print("[通过] HTML 解析")
    except Exception as exc:
        errors.append(f"HTML 解析测试失败: {exc}")
        print(f"[失败] HTML 解析: {exc}")

    # --- 测试 2: 纯文本解析 ---
    try:
        sample_text = """这是一段测试文本
第二行内容
第三行内容"""
        page = parse_plain_text(sample_text)
        assert page.title == "这是一段测试文本", f"标题提取失败: {page.title}"
        assert "第二行" in page.content, "正文提取失败"
        print("[通过] 纯文本解析")
    except Exception as exc:
        errors.append(f"纯文本解析测试失败: {exc}")
        print(f"[失败] 纯文本解析: {exc}")

    # --- 测试 3: 字段提取 ---
    try:
        sample_recruit = """某科技有限公司招聘高级Python工程师
工作地点：北京市海淀区中关村
薪资待遇：25000-40000元/月
联系方式：hr@example.com 电话：010-12345678"""
        extraction = extract_fields(sample_recruit, ["company", "location", "salary", "email"])
        fields = extraction.fields
        assert "company" in fields, "公司字段缺失"
        assert "location" in fields, "地点字段缺失"
        assert "salary" in fields, "薪资字段缺失"
        assert "email" in fields, "邮箱字段缺失"
        assert "@" in fields["email"], "邮箱格式不正确"
        assert "北京" in fields["location"], "地点提取不准确"
        print(f"[通过] 字段提取: {fields}")
    except Exception as exc:
        errors.append(f"字段提取测试失败: {exc}")
        print(f"[失败] 字段提取: {exc}")

    # --- 测试 4: 结构化转换 ---
    try:
        test_data = [{"name": "产品A", "price": 100, "spec": "标准版"},
                     {"name": "产品B", "price": 200, "spec": "高级版"}]
        json_str = convert_to_json(test_data)
        assert json_str.startswith("["), "JSON 格式错误"
        assert "产品A" in json_str, "JSON 内容缺失"

        csv_str = convert_to_csv(test_data)
        assert "name" in csv_str, "CSV 表头缺失"
        assert "产品A" in csv_str, "CSV 内容缺失"

        md_str = convert_to_markdown(test_data)
        assert "|" in md_str, "Markdown 表格格式错误"
        assert "产品B" in md_str, "Markdown 内容缺失"
        print("[通过] 结构化转换")
    except Exception as exc:
        errors.append(f"结构化转换测试失败: {exc}")
        print(f"[失败] 结构化转换: {exc}")

    # --- 测试 5: 批量处理 ---
    try:
        items = ["第一条测试数据", "第二条测试数据"]
        results = batch_process(items)
        assert len(results) == 2, f"批量处理数量错误: {len(results)}"
        assert results[0].get("title"), "批量处理结果缺少标题"
        print("[通过] 批量处理")
    except Exception as exc:
        errors.append(f"批量处理测试失败: {exc}")
        print(f"[失败] 批量处理: {exc}")

    # --- 测试 6: 置信度标注 ---
    try:
        extraction = extract_fields("这是一段没有邮箱的文本", ["email"])
        assert "需核实" in extraction.fields["email"], "未找到字段应输出占位符"
        assert extraction.confidence["email"] == 0.0, "置信度应为 0"
        print("[通过] 置信度标注")
    except Exception as exc:
        errors.append(f"置信度标注测试失败: {exc}")
        print(f"[失败] 置信度标注: {exc}")

    # --- 汇总 ---
    if errors:
        print(f"\n=== 自检失败: {len(errors)} 项错误 ===")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n=== 自检全部通过 ===")


# ============================================================
# 命令行入口
# ============================================================

def main() -> None:
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="llm-web-crawler — 网页采集与结构化提取工具",
        epilog="示例: python main.py --parse '<html>...</html>' | python main.py --selftest"
    )

    # 输入来源
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--html", type=str, help="HTML 内容字符串")
    input_group.add_argument("--text", type=str, help="纯文本内容字符串")
    input_group.add_argument("--file", type=str, help="从文件读取内容")
    input_group.add_argument("--url", type=str, help="URL（仅校验格式，不实际抓取）")

    # 操作类型
    parser.add_argument("--parse", action="store_true", help="解析内容")
    parser.add_argument("--extract", action="store_true", help="提取字段")
    parser.add_argument("--convert", action="store_true", help="结构化转换")
    parser.add_argument("--batch", action="store_true", help="批量处理")

    # 参数
    parser.add_argument("--fields", type=str, help="要提取的字段，逗号分隔")
    parser.add_argument("--format", type=str, choices=["json", "csv", "markdown", "md"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--batch-file", type=str, help="批量处理输入文件（每行一条）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 检查是否有输入
    if not (args.html or args.text or args.file or args.url or args.batch_file):
        error_exit("E001", "请提供输入: --html, --text, --file, --url 或 --batch-file")

    # 读取输入
    raw_content = ""
    source_url = ""
    try:
        if args.html:
            raw_content = args.html
        elif args.text:
            raw_content = args.text
        elif args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    raw_content = f.read()
            except FileNotFoundError:
                error_exit("E006", f"文件不存在: {args.file}")
            except UnicodeDecodeError:
                error_exit("E009", f"文件编码错误: {args.file}")
        elif args.url:
            source_url = args.url
            parsed = urllib.parse.urlparse(args.url)
            if not parsed.scheme or not parsed.netloc:
                error_exit("E007", f"无效 URL: {args.url}")
            raw_content = f"URL: {args.url}\n[静态模式] 未执行实际网络抓取，仅提供 URL 元信息。"
    except CrawlerError as exc:
        error_exit(exc.code, exc.message)
    except Exception as exc:
        error_exit("E010", f"未知错误: {exc}")

    if not raw_content.strip():
        error_exit("E002", "输入内容为空")

    # 解析字段列表
    field_list: Optional[List[str]] = None
    if args.fields:
        field_list = [f.strip() for f in args.fields.split(",") if f.strip()]
        if not field_list:
            error_exit("E004", "字段列表为空")

    # 执行操作
    try:
        # 批量模式
        if args.batch or args.batch_file:
            items: List[str] = []
            if args.batch_file:
                try:
                    with open(args.batch_file, "r", encoding="utf-8") as f:
                        items = [line.strip() for line in f if line.strip()]
                except FileNotFoundError:
                    error_exit("E006", f"批量文件不存在: {args.batch_file}")
                except UnicodeDecodeError:
                    error_exit("E009", f"批量文件编码错误: {args.batch_file}")
            else:
                items = [raw_content]

            if not items:
                error_exit("E002", "批量输入为空")

            results = batch_process(items, field_list)
            output = convert_data(results, args.format)
            print(output)
            return

        # 解析模式
        if args.parse:
            is_html = bool(args.html)
            page = parse_content(raw_content, source_url, is_html)
            output = convert_data(page.to_dict(), args.format)
            print(output)
            return

        # 提取模式
        if args.extract:
            if not field_list:
                error_exit("E004", "提取模式需要 --fields 参数")
            extraction = extract_fields(raw_content, field_list)
            output = convert_data(extraction.to_dict(), args.format)
            print(output)
            return

        # 转换模式
        if args.convert:
            # 尝试解析为结构化数据
            page = parse_content(raw_content, source_url, bool(args.html))
            data = page.to_dict()
            output = convert_data(data, args.format)
            print(output)
            return

        # 未指定操作
        error_exit("E001", "请指定操作: --parse, --extract, --convert 或 --batch")

    except CrawlerError as exc:
        error_exit(exc.code, exc.message)
    except Exception as exc:
        error_exit("E010", f"未知错误: {exc}")


if __name__ == "__main__":
    main()
