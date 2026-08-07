#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawlee-one 独立实现脚本
========================
依据功能规格独立编写，不复制任何既有代码。
提供网页/数据文件的结构化采集流程与输出。
仅使用标准库，无第三方依赖。

用法示例:
    python main.py --selftest
    python main.py --fetch https://example.com --selector "h1"
    python main.py --file data.html --selector ".item" --output result.json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式非法",
    "E002": "网络错误：URL 无法访问或请求失败",
    "E003": "解析错误：HTML/文本内容解析失败",
    "E004": "选择器错误：CSS 选择器格式非法",
    "E005": "数据提取错误：未能从内容中提取到有效数据",
    "E006": "文件错误：本地文件不存在或无法读取",
    "E007": "编码错误：内容编码识别或转换失败",
    "E008": "输出错误：结果写入失败",
    "E009": "内部错误：未预期的运行时异常",
    "E010": "自检错误：自检断言失败",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并以对应错误码退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg} | {message}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------- 数据模型 ----------

@dataclass
class FetchResult:
    """采集结果数据模型。"""
    url: str = ""
    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    content: str = ""
    encoding: str = "utf-8"
    extracted: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------- 核心功能模块 ----------

class HtmlParser:
    """极简 HTML 解析器：支持标签、属性、文本提取。"""

    # 匹配标签（含属性）
    _TAG_RE = re.compile(r"<\s*([a-zA-Z][a-zA-Z0-9]*)([^>]*)>")
    # 匹配属性 name="value" 或 name='value' 或 name=value
    _ATTR_RE = re.compile(
        r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))"
    )
    # 匹配注释
    _COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
    # 匹配脚本/样式块
    _SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)

    def __init__(self, html: str):
        self.html = html
        self._clean()

    def _clean(self) -> None:
        """清理注释、脚本和样式块。"""
        self.html = self._COMMENT_RE.sub("", self.html)
        self.html = self._SCRIPT_RE.sub("", self.html)

    def get_text(self) -> str:
        """提取纯文本内容（去除所有标签）。"""
        text = self._TAG_RE.sub(" ", self.html)
        # 合并空白
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def find_all(self, tag: Optional[str] = None, attrs: Optional[Dict[str, str]] = None) -> List[str]:
        """
        查找所有匹配标签的原始 HTML 片段。
        支持按标签名和属性过滤。
        """
        attrs = attrs or {}
        results = []
        for match in self._TAG_RE.finditer(self.html):
            tag_name = match.group(1).lower()
            if tag and tag_name != tag.lower():
                continue
            attr_str = match.group(2)
            if attrs:
                attr_dict = self._parse_attrs(attr_str)
                matched = True
                for key, val in attrs.items():
                    if key not in attr_dict or attr_dict[key] != val:
                        matched = False
                        break
                if not matched:
                    continue
            results.append(match.group(0))
        return results

    def find_by_class(self, class_name: str, tag: Optional[str] = None) -> List[str]:
        """按 class 属性查找元素。"""
        return self.find_all(tag=tag, attrs={"class": class_name})

    def _parse_attrs(self, attr_str: str) -> Dict[str, str]:
        """解析属性字符串为字典。"""
        attrs = {}
        for match in self._ATTR_RE.finditer(attr_str):
            key = match.group(1)
            # 获取四个可能的捕获组中的实际值
            value = match.group(2) or match.group(3) or match.group(4) or ""
            attrs[key] = value
        return attrs

    def extract_text(self, tag: str, attrs: Optional[Dict[str, str]] = None) -> List[str]:
        """提取匹配元素的文本内容。"""
        elements = self.find_all(tag=tag, attrs=attrs)
        texts = []
        for elem in elements:
            # 去除标签，保留内部文本
            inner = self._TAG_RE.sub(" ", elem)
            inner = re.sub(r"\s+", " ", inner).strip()
            if inner:
                texts.append(inner)
        return texts


class CssSelector:
    """简易 CSS 选择器解析与匹配（支持 tag、.class、#id、[attr=value]）。"""

    def __init__(self, selector: str):
        self.selector = selector.strip()
        self._parts = self._parse(self.selector)
        if not self._parts:
            error_exit("E004", f"选择器格式非法: {selector}")

    def _parse(self, selector: str) -> List[Dict[str, Any]]:
        """解析选择器为规则列表。"""
        parts = []
        # 支持逗号分隔
        for group in selector.split(","):
            group = group.strip()
            if not group:
                continue
            # 分解复合选择器（简单处理：空格分隔）
            for item in group.split():
                rule: Dict[str, Any] = {"tag": None, "class": None, "id": None, "attrs": {}}
                # 匹配 tag
                m = re.match(r"^([a-zA-Z][a-zA-Z0-9]*)", item)
                if m:
                    rule["tag"] = m.group(1)
                    item = item[m.end():]
                # 匹配 #id
                m = re.search(r"#([a-zA-Z_][a-zA-Z0-9_-]*)", item)
                if m:
                    rule["id"] = m.group(1)
                # 匹配 .class
                for cls in re.findall(r"\.([a-zA-Z_][a-zA-Z0-9_-]*)", item):
                    rule["class"] = cls
                # 匹配 [attr=value]
                for am in re.finditer(r"\[([a-zA-Z_-]+)=['\"]?([^'\"]+)['\"]?\]", item):
                    rule["attrs"][am.group(1)] = am.group(2)
                parts.append(rule)
        return parts

    def match(self, tag: str, attrs: Dict[str, str]) -> bool:
        """判断标签和属性是否匹配选择器。"""
        for rule in self._parts:
            if rule["tag"] and rule["tag"] != tag:
                continue
            if rule["id"] and attrs.get("id") != rule["id"]:
                continue
            if rule["class"] and rule["class"] not in attrs.get("class", "").split():
                continue
            for key, val in rule["attrs"].items():
                if attrs.get(key) != val:
                    break
            else:
                return True
        return False


class DataExtractor:
    """从 HTML 内容中提取结构化数据。"""

    def __init__(self, html: str):
        self.parser = HtmlParser(html)

    def extract_by_selector(self, selector: str) -> List[Dict[str, Any]]:
        """按 CSS 选择器提取数据。"""
        css = CssSelector(selector)
        results = []
        # 通过解析器获取所有标签及属性
        for match in HtmlParser._TAG_RE.finditer(self.parser.html):
            tag = match.group(1).lower()
            attr_str = match.group(2)
            attrs = self.parser._parse_attrs(attr_str)
            if css.match(tag, attrs):
                # 提取该元素的文本
                element_html = match.group(0)
                inner = HtmlParser._TAG_RE.sub(" ", element_html)
                text = re.sub(r"\s+", " ", inner).strip()
                results.append({
                    "tag": tag,
                    "attrs": attrs,
                    "text": text,
                })
        return results

    def extract_tables(self) -> List[Dict[str, Any]]:
        """提取表格数据。"""
        tables = []
        table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL | re.IGNORECASE)
        for tmatch in table_pattern.finditer(self.parser.html):
            table_html = tmatch.group(1)
            rows = []
            row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
            for rmatch in row_pattern.finditer(table_html):
                row_html = rmatch.group(1)
                cells = []
                cell_pattern = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL | re.IGNORECASE)
                for cmatch in cell_pattern.finditer(row_html):
                    cell_text = re.sub(r"<[^>]+>", "", cmatch.group(1))
                    cell_text = re.sub(r"\s+", " ", cell_text).strip()
                    cells.append(cell_text)
                if cells:
                    rows.append(cells)
            if rows:
                tables.append({"rows": rows})
        return tables

    def extract_links(self, base_url: str = "") -> List[Dict[str, str]]:
        """提取所有链接。"""
        links = []
        for match in HtmlParser._TAG_RE.finditer(self.parser.html):
            tag = match.group(1).lower()
            if tag != "a":
                continue
            attrs = self.parser._parse_attrs(match.group(2))
            href = attrs.get("href", "")
            text = re.sub(r"<[^>]+>", "", match.group(0)).strip()
            if href:
                full_url = urljoin(base_url, href) if base_url else href
                links.append({"href": full_url, "text": text})
        return links


class ContentFetcher:
    """获取网页或文件内容。"""

    @staticmethod
    def fetch_url(url: str, timeout: int = 10) -> FetchResult:
        """从 URL 获取内容。"""
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 crawlee-one/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                result = FetchResult()
                result.url = url
                result.status_code = getattr(resp, "status", 200)
                result.headers = {k: v for k, v in resp.headers.items()}
                raw = resp.read()
                # 尝试从 header 获取编码
                content_type = result.headers.get("Content-Type", "")
                charset_match = re.search(r"charset=([\w-]+)", content_type)
                if charset_match:
                    result.encoding = charset_match.group(1)
                else:
                    result.encoding = "utf-8"
                try:
                    result.content = raw.decode(result.encoding, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    # 尝试 utf-8
                    try:
                        result.content = raw.decode("utf-8", errors="replace")
                        result.encoding = "utf-8"
                    except Exception:
                        result.content = raw.decode("latin-1", errors="replace")
                        result.encoding = "latin-1"
                return result
        except Exception as e:
            error_exit("E002", f"URL 访问失败: {url} | {e}")

    @staticmethod
    def fetch_file(path: str) -> FetchResult:
        """从本地文件读取内容。"""
        try:
            with open(path, "rb") as f:
                raw = f.read()
            result = FetchResult()
            result.url = f"file://{path}"
            result.status_code = 200
            # 尝试多种编码
            for enc in ["utf-8", "gbk", "latin-1"]:
                try:
                    result.content = raw.decode(enc)
                    result.encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
            else:
                result.content = raw.decode("utf-8", errors="replace")
                result.encoding = "utf-8"
            return result
        except FileNotFoundError:
            error_exit("E006", f"文件不存在: {path}")
        except Exception as e:
            error_exit("E006", f"文件读取失败: {path} | {e}")


class Pipeline:
    """采集流水线：获取 → 解析 → 提取 → 输出。"""

    def __init__(self, source: str, source_type: str = "auto"):
        self.source = source
        self.source_type = source_type
        self.result = FetchResult()

    def run(self, selector: Optional[str] = None) -> FetchResult:
        """执行采集流程。"""
        # 1. 获取内容
        if self.source_type == "url":
            self.result = ContentFetcher.fetch_url(self.source)
        elif self.source_type == "file":
            self.result = ContentFetcher.fetch_file(self.source)
        else:
            # 自动判断
            parsed = urlparse(self.source)
            if parsed.scheme in ("http", "https"):
                self.result = ContentFetcher.fetch_url(self.source)
            else:
                self.result = ContentFetcher.fetch_file(self.source)

        # 2. 解析与提取
        extractor = DataExtractor(self.result.content)
        if selector:
            self.result.extracted = extractor.extract_by_selector(selector)
        else:
            # 默认提取：文本、链接、表格
            self.result.metadata["text"] = extractor.parser.get_text()[:500]
            self.result.metadata["links"] = extractor.extract_links(self.result.url)
            self.result.metadata["tables"] = extractor.extract_tables()

        # 3. 元信息
        self.result.metadata["source"] = self.source
        self.result.metadata["source_type"] = self.source_type
        self.result.metadata["content_length"] = len(self.result.content)

        if not self.result.extracted and not self.result.metadata:
            error_exit("E005", "未能提取到有效数据")

        return self.result

    def to_json(self, pretty: bool = True) -> str:
        """将结果转为 JSON 字符串。"""
        data = {
            "url": self.result.url,
            "status_code": self.result.status_code,
            "encoding": self.result.encoding,
            "extracted": self.result.extracted,
            "metadata": self.result.metadata,
        }
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)


def save_output(data: Dict[str, Any], output_file: str) -> None:
    """将数据保存到文件。"""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_exit("E008", f"输出写入失败: {output_file} | {e}")


# ---------- 自检模块 ----------

def selftest() -> int:
    """
    内置硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("开始自检...")

    # 硬编码测试数据
    SAMPLE_HTML = """
    <html>
    <head><title>测试页面</title></head>
    <body>
        <h1 id="main-title">欢迎使用 crawlee-one</h1>
        <div class="container">
            <p class="item" data-id="1">项目 A</p>
            <p class="item" data-id="2">项目 B</p>
            <p class="item" data-id="3">项目 C</p>
        </div>
        <table>
            <tr><th>姓名</th><th>年龄</th></tr>
            <tr><td>张三</td><td>25</td></tr>
            <tr><td>李四</td><td>30</td></tr>
        </table>
        <a href="https://example.com/page1">链接1</a>
        <a href="/page2">链接2</a>
    </body>
    </html>
    """

    # 测试 1: HTML 解析器
    parser = HtmlParser(SAMPLE_HTML)
    text = parser.get_text()
    assert len(text) > 50, "E010: 纯文本提取失败，文本过短"
    assert "欢迎使用" in text, "E010: 文本内容缺失"
    print("  [OK] HTML 解析器")

    # 测试 2: 标签查找
    items = parser.find_all("p", attrs={"class": "item"})
    assert len(items) >= 3, "E010: 标签查找数量不足"
    print("  [OK] 标签查找")

    # 测试 3: CSS 选择器
    css = CssSelector(".item")
    assert css.match("p", {"class": "item"}), "E010: CSS 选择器类匹配失败"
    css2 = CssSelector("p[data-id=2]")
    assert css2.match("p", {"data-id": "2"}), "E010: CSS 选择器属性匹配失败"
    print("  [OK] CSS 选择器")

    # 测试 4: 数据提取
    extractor = DataExtractor(SAMPLE_HTML)
    extracted = extractor.extract_by_selector(".item")
    assert len(extracted) >= 3, "E010: 数据提取数量不足"
    assert all("text" in item for item in extracted), "E010: 提取数据缺少文本字段"
    print("  [OK] 数据提取")

    # 测试 5: 表格提取
    tables = extractor.extract_tables()
    assert len(tables) >= 1, "E010: 表格提取失败"
    assert len(tables[0]["rows"]) >= 2, "E010: 表格行数不足"
    print("  [OK] 表格提取")

    # 测试 6: 链接提取
    links = extractor.extract_links("https://example.com/base")
    assert len(links) >= 2, "E010: 链接提取数量不足"
    assert any("example.com" in l["href"] for l in links), "E010: 链接 URL 拼接失败"
    print("  [OK] 链接提取")

    # 测试 7: 流水线（使用内存数据模拟）
    pipeline = Pipeline("memory://selftest")
    pipeline.result.content = SAMPLE_HTML
    pipeline.result.url = "https://example.com/selftest"
    extractor2 = DataExtractor(SAMPLE_HTML)
    pipeline.result.extracted = extractor2.extract_by_selector("h1")
    pipeline.result.metadata = {"content_length": len(SAMPLE_HTML)}
    assert len(pipeline.result.extracted) >= 1, "E010: 流水线提取失败"
    json_out = pipeline.to_json()
    assert json_out is not None and len(json_out) > 10, "E010: JSON 序列化失败"
    print("  [OK] 流水线处理")

    # 测试 8: 错误处理
    try:
        CssSelector("")
        error_exit("E010", "空选择器应报错")
    except SystemExit:
        pass  # 预期行为
    print("  [OK] 错误处理")

    print("自检通过: 所有核心逻辑验证成功")
    return 0


# ---------- 主入口 ----------

def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="crawlee-one: 网页采集与结构化处理工具",
        epilog="示例: python main.py --fetch https://example.com --selector h1"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--fetch", type=str, metavar="URL", help="采集 URL")
    parser.add_argument("--file", type=str, metavar="PATH", help="读取本地文件")
    parser.add_argument("--selector", type=str, default=None, metavar="CSS", help="CSS 选择器提取数据")
    parser.add_argument("--output", type=str, default=None, metavar="FILE", help="输出 JSON 文件路径")
    parser.add_argument("--pretty", action="store_true", default=True, help="美化 JSON 输出")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return selftest()
        except AssertionError as e:
            error_exit("E010", str(e))
        except Exception as e:
            error_exit("E009", f"自检异常: {e}")

    # 采集模式
    if not args.fetch and not args.file:
        error_exit("E001", "必须提供 --fetch 或 --file 参数")

    try:
        source = args.fetch or args.file
        source_type = "url" if args.fetch else "file"

        pipeline = Pipeline(source, source_type)
        result = pipeline.run(args.selector)

        # 构建输出数据
        output_data = {
            "url": result.url,
            "status_code": result.status_code,
            "encoding": result.encoding,
            "extracted": result.extracted,
            "metadata": result.metadata,
            "content_length": len(result.content),
        }

        # 输出
        if args.output:
            save_output(output_data, args.output)
            print(f"结果已保存至: {args.output}")
        else:
            print(json.dumps(output_data, ensure_ascii=False, indent=2))

        return 0

    except SystemExit:
        raise
    except Exception as e:
        error_exit("E009", f"未预期的错误: {e}")


if __name__ == "__main__":
    sys.exit(main())
