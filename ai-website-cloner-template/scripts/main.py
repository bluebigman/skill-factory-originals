#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点克隆模板生成器（ai-website-cloner-template）
=================================================
将目标网站或本地 HTML 文件解析为结构化克隆模板（JSON/YAML/HTML），
供 AI 编码代理直接消费。

作者: LinStruct
版本: 2.0.0
许可证: MIT
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import time
from datetime import datetime, timezone
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INVALID_INPUT = "E001"      # 输入参数无效
ERR_URL_FETCH_FAILED = "E002"   # 无法获取 URL 内容
ERR_FILE_NOT_FOUND = "E003"     # 本地文件不存在
ERR_FILE_READ_FAILED = "E004"   # 本地文件读取失败
ERR_HTML_PARSE_FAILED = "E005"  # HTML 解析失败
ERR_EMPTY_CONTENT = "E006"      # 内容为空
ERR_TEMPLATE_GEN_FAILED = "E007"  # 模板生成失败
ERR_OUTPUT_WRITE_FAILED = "E008"  # 输出文件写入失败
ERR_INTERNAL = "E009"           # 内部错误
ERR_SELFTEST_FAILED = "E010"    # 自检失败

# 网络请求配置
REQUEST_TIMEOUT = 10  # 秒
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # 秒
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 缓存配置
CACHE_DIR = Path.home() / ".cache" / "ai-website-cloner"
CACHE_TTL = 3600  # 1小时


# ---------------------------------------------------------------------------
# 硬编码自检样例数据（离线，不依赖任何外部资源）
# ---------------------------------------------------------------------------
SELFTEST_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>示例站点</title>
    <link rel="stylesheet" href="/assets/css/main.css">
    <link rel="icon" href="/favicon.ico">
</head>
<body>
    <header class="site-header">
        <nav class="main-nav">
            <ul>
                <li><a href="/">首页</a></li>
                <li><a href="/products">产品</a></li>
                <li><a href="/about">关于</a></li>
            </ul>
        </nav>
    </header>
    <main class="content-wrapper">
        <h1>欢迎来到示例站点</h1>
        <section class="product-grid">
            <div class="product-card" data-id="1">
                <h2 class="product-title">产品 A</h2>
                <p class="product-price">¥99.00</p>
                <img class="product-image" src="/images/a.jpg" alt="产品 A 图片">
            </div>
            <div class="product-card" data-id="2">
                <h2 class="product-title">产品 B</h2>
                <p class="product-price">¥199.00</p>
                <img class="product-image" src="/images/b.jpg" alt="产品 B 图片">
            </div>
            <div class="product-card" data-id="3">
                <h2 class="product-title">产品 C</h2>
                <p class="product-price">¥299.00</p>
                <img class="product-image" src="/images/c.jpg" alt="产品 C 图片">
            </div>
        </section>
    </main>
    <footer class="site-footer">
        <p>© 2026 示例公司</p>
    </footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 自定义 HTML 解析器
# ---------------------------------------------------------------------------
class StructureExtractor(HTMLParser):
    """解析 HTML 并提取 DOM 结构信息。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: List[Dict[str, Any]] = []
        self.root: Optional[Dict[str, Any]] = None
        self.repeated_blocks: Dict[str, Dict[str, Any]] = {}
        self.static_elements: List[Dict[str, str]] = []
        self.current_text: List[str] = []
        self._current_path: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """处理开始标签。"""
        attr_dict = {k: v for k, v in attrs if v is not None}
        node = {
            "tag": tag,
            "attrs": attr_dict,
            "children": [],
            "text": "",
            "path": "/".join(self._current_path + [tag]),
        }
        if self.stack:
            self.stack[-1]["children"].append(node)
        else:
            self.root = node
        self.stack.append(node)
        self._current_path.append(tag)

    def handle_endtag(self, tag: str) -> None:
        """处理结束标签。"""
        if self.stack:
            node = self.stack.pop()
            if self._current_path:
                self._current_path.pop()
            # 统计重复区块
            self._track_repeated_block(node)

    def handle_data(self, data: str) -> None:
        """处理文本数据。"""
        if self.stack:
            text = data.strip()
            if text:
                self.stack[-1]["text"] = text

    def _track_repeated_block(self, node: Dict[str, Any]) -> None:
        """识别重复出现的区块（如同类卡片、列表项）。"""
        # 使用 tag + class 作为区块标识
        class_name = node["attrs"].get("class", "")
        if class_name:
            key = f"{node['tag']}.{class_name}"
            if key not in self.repeated_blocks:
                self.repeated_blocks[key] = {
                    "selector": key,
                    "frequency": 0,
                    "variables": [],
                    "sample_node": node,
                }
            self.repeated_blocks[key]["frequency"] += 1
            # 提取变量（子元素的 class 或 id）
            for child in node["children"]:
                child_class = child["attrs"].get("class", "")
                child_id = child["attrs"].get("id", "")
                if child_class:
                    var_name = child_class.split()[-1]
                elif child_id:
                    var_name = child_id
                else:
                    var_name = child["tag"]
                if var_name not in self.repeated_blocks[key]["variables"]:
                    self.repeated_blocks[key]["variables"].append(var_name)

    def get_static_elements(self) -> List[Dict[str, str]]:
        """提取静态元素（如 header、footer、nav 等）。"""
        static_tags = {"header", "footer", "nav", "main", "aside"}
        result = []
        for node in self._iter_nodes(self.root):
            if node["tag"] in static_tags:
                selector = node["tag"]
                if "class" in node["attrs"]:
                    selector += f".{node['attrs']['class']}"
                result.append({"selector": selector, "type": "fixed"})
        return result

    def _iter_nodes(self, node: Optional[Dict[str, Any]]) -> Any:
        """递归遍历节点树。"""
        if node is None:
            return
        yield node
        for child in node.get("children", []):
            yield from self._iter_nodes(child)


# ---------------------------------------------------------------------------
# 核心功能函数
# ---------------------------------------------------------------------------
def fetch_url_content(url: str, timeout: int = REQUEST_TIMEOUT) -> Tuple[int, str]:
    """
    获取 URL 内容，带超时和指数退避重试。

    返回: (错误码, 内容字符串)
    """
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                return ERR_OK, content
        except urllib.error.HTTPError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])
            else:
                return ERR_URL_FETCH_FAILED, f"HTTP 错误: {e.code}"
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])
            else:
                return ERR_URL_FETCH_FAILED, f"URL 错误: {e.reason}"
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])
            else:
                return ERR_URL_FETCH_FAILED, f"未知错误: {str(e)}"
    return ERR_URL_FETCH_FAILED, "重试次数耗尽"


def read_text_safe(path: Path) -> str:
    """多编码读取文件，带降级处理。"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def read_local_file(file_path: str) -> Tuple[int, str]:
    """
    读取本地文件，支持多编码。

    返回: (错误码, 内容字符串)
    """
    path = Path(file_path)
    if not path.exists():
        return ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}"
    if not path.is_file():
        return ERR_FILE_READ_FAILED, f"不是文件: {file_path}"
    if path.stat().st_size > 5 * 1024 * 1024:
        return ERR_FILE_READ_FAILED, "文件大小超过 5MB 限制"

    try:
        content = read_text_safe(path)
        if content:
            return ERR_OK, content
        return ERR_FILE_READ_FAILED, "无法识别文件编码"
    except Exception as e:
        return ERR_FILE_READ_FAILED, f"读取失败: {str(e)}"


def parse_html_content(content: str) -> Tuple[int, Optional[StructureExtractor]]:
    """
    解析 HTML 内容。

    返回: (错误码, 解析器实例)
    """
    if not content or not content.strip():
        return ERR_EMPTY_CONTENT, None
    try:
        parser = StructureExtractor()
        parser.feed(content)
        parser.close()
        if parser.root is None:
            return ERR_HTML_PARSE_FAILED, None
        return ERR_OK, parser
    except Exception as e:
        return ERR_HTML_PARSE_FAILED, None


def generate_template(parser: StructureExtractor, source_name: str) -> Dict[str, Any]:
    """
    生成模板字典。

    返回: 模板字典
    """
    template = {
        "template_name": source_name,
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root_element": parser.root["tag"] if parser.root else "html",
        "repeated_blocks": [],
        "static_elements": parser.get_static_elements(),
    }

    # 处理重复区块
    for selector, info in parser.repeated_blocks.items():
        if info["frequency"] >= 2:  # 只保留出现 2 次以上的区块
            block = {
                "selector": selector,
                "frequency": info["frequency"],
                "variables": info["variables"],
            }
            template["repeated_blocks"].append(block)

    return template


def generate_structure_doc(parser: StructureExtractor, template: Dict[str, Any]) -> str:
    """
    生成结构说明文档（Markdown 格式）。

    返回: Markdown 字符串
    """
    doc = []
    doc.append("# 页面结构分析报告\n")
    doc.append(f"- **生成时间**: {template['generated_at']}")
    doc.append(f"- **根元素**: `{template['root_element']}`\n")

    doc.append("## DOM 结构树\n")
    doc.append("```text")
    if parser.root:
        _append_node_tree(doc, parser.root, 0)
    doc.append("```\n")

    doc.append("## 重复区块分析\n")
    if template["repeated_blocks"]:
        doc.append("| 选择器 | 出现次数 | 变量 |")
        doc.append("|--------|----------|------|")
        for block in template["repeated_blocks"]:
            vars_str = ", ".join(f"`{v}`" for v in block["variables"])
            doc.append(f"| `{block['selector']}` | {block['frequency']} | {vars_str} |")
    else:
        doc.append("未识别到重复区块。\n")

    doc.append("\n## 静态元素\n")
    if template["static_elements"]:
        doc.append("| 选择器 | 类型 |")
        doc.append("|--------|------|")
        for elem in template["static_elements"]:
            doc.append(f"| `{elem['selector']}` | {elem['type']} |")
    else:
        doc.append("未识别到静态元素。")

    return "\n".join(doc)


def _append_node_tree(doc: List[str], node: Dict[str, Any], depth: int) -> None:
    """递归生成节点树文本。"""
    indent = "  " * depth
    attrs_str = ""
    if "class" in node["attrs"]:
        attrs_str += f".{node['attrs']['class']}"
    if "id" in node["attrs"]:
        attrs_str += f"#{node['attrs']['id']}"
    doc.append(f"{indent}<{node['tag']}{attrs_str}>")
    if node["text"]:
        doc.append(f"{indent}  \"{node['text'][:50]}\"")
    for child in node.get("children", []):
        _append_node_tree(doc, child, depth + 1)


def write_output_file(file_path: str, content: str, dry_run: bool = False) -> Tuple[int, str]:
    """
    原子化写入文件。

    返回: (错误码, 消息)
    """
    path = Path(file_path)
    if not dry_run:
        try:
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            # 原子写入：先写临时文件，再重命名
            temp_path = path.with_suffix(path.suffix + ".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, path)
            return ERR_OK, f"文件已写入: {path}"
        except Exception as e:
            return ERR_OUTPUT_WRITE_FAILED, f"写入失败: {str(e)}"
    # 计算内容摘要
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return ERR_OK, f"[DRY-RUN] 将写入文件: {path} (摘要: {digest})"


def format_template_output(template: Dict[str, Any], fmt: str) -> str:
    """
    将模板字典格式化为指定格式的字符串。

    返回: 格式化后的字符串
    """
    if fmt == "json":
        return json.dumps(template, ensure_ascii=False, indent=2)
    elif fmt == "yaml":
        # 简单 YAML 序列化（不依赖第三方库）
        lines = []
        for key, value in template.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"  - {_dict_to_yaml(item, '    ')}")
                    else:
                        lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                lines.append(_dict_to_yaml(value, "  "))
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    elif fmt == "html":
        # 生成 HTML 骨架
        html = ["<!DOCTYPE html>", "<html>", "<head>", "<meta charset=\"UTF-8\">", "</head>", "<body>"]
        for elem in template["static_elements"]:
            html.append(f"  <!-- {elem['selector']} -->")
        for block in template["repeated_blocks"]:
            html.append(f"  <!-- 重复区块: {block['selector']} (x{block['frequency']}) -->")
            for var in block["variables"]:
                html.append(f"    <!-- {{{{{var}}}}} -->")
        html.append("</body>")
        html.append("</html>")
        return "\n".join(html)
    else:
        return json.dumps(template, ensure_ascii=False, indent=2)


def _dict_to_yaml(d: Dict[str, Any], indent: str) -> str:
    """将字典转换为 YAML 行。"""
    lines = []
    for key, value in d.items():
        if isinstance(value, list):
            lines.append(f"{indent}{key}:")
            for item in value:
                lines.append(f"{indent}  - {item}")
        else:
            lines.append(f"{indent}{key}: {value}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    运行自检，验证核心功能。

    返回: 退出码（0 表示成功）
    """
    print("[SELFTEST] 开始自检...")
    errors = []

    # 测试 1: 解析 HTML
    print("[SELFTEST] 测试 1: HTML 解析")
    err, parser = parse_html_content(SELFTEST_HTML)
    if err != ERR_OK or parser is None:
        errors.append(f"HTML 解析失败: {err}")
    else:
        print(f"  [PASS] 解析成功，根元素: {parser.root['tag'] if parser.root else 'None'}")

    # 测试 2: 生成模板
    print("[SELFTEST] 测试 2: 模板生成")
    if parser:
        template = generate_template(parser, "selftest")
        if template["root_element"] != "html":
            errors.append(f"根元素错误: {template['root_element']}")
        else:
            print(f"  [PASS] 模板生成成功，重复区块数: {len(template['repeated_blocks'])}")

        # 测试 3: 重复区块识别
        print("[SELFTEST] 测试 3: 重复区块识别")
        product_blocks = [b for b in template["repeated_blocks"] if "product-card" in b["selector"]]
        if not product_blocks:
            errors.append("未识别到 product-card 重复区块")
        else:
            block = product_blocks[0]
            if block["frequency"] != 3:
                errors.append(f"product-card 频率错误: {block['frequency']}，期望 3")
            else:
                print(f"  [PASS] product-card 频率: {block['frequency']}")

        # 测试 4: 变量提取
        print("[SELFTEST] 测试 4: 变量提取")
        if product_blocks:
            variables = product_blocks[0]["variables"]
            expected_vars = {"product-title", "product-price", "product-image"}
            if not expected_vars.issubset(set(variables)):
                errors.append(f"变量提取不完整: {variables}")
            else:
                print(f"  [PASS] 变量提取: {variables}")

    # 测试 5: 静态元素识别
    print("[SELFTEST] 测试 5: 静态元素识别")
    if parser:
        static_elements = parser.get_static_elements()
        static_selectors = [e["selector"] for e in static_elements]
        if "header.site-header" not in static_selectors:
            errors.append(f"未识别到 header.site-header: {static_selectors}")
        else:
            print(f"  [PASS] 静态元素: {static_selectors}")

    # 测试 6: 文件写入（dry-run）
    print("[SELFTEST] 测试 6: 文件写入（dry-run）")
    err, msg = write_output_file("/tmp/test_output.json", "{}", dry_run=True)
    if err != ERR_OK:
        errors.append(f"dry-run 写入失败: {msg}")
    else:
        print(f"  [PASS] {msg}")

    # 测试 7: 空内容处理
    print("[SELFTEST] 测试 7: 空内容处理")
    err, parser_empty = parse_html_content("")
    if err != ERR_EMPTY_CONTENT:
        errors.append(f"空内容处理失败: {err}")
    else:
        print("  [PASS] 空内容正确返回错误码")

    # 测试 8: 无效 HTML
    print("[SELFTEST] 测试 8: 无效 HTML")
    err, parser_invalid = parse_html_content("<html><body>")
    if err != ERR_OK or parser_invalid is None:
        errors.append(f"无效 HTML 处理失败: {err}")
    else:
        print("  [PASS] 无效 HTML 被容错处理")

    # 测试 9: 文件写入（真实写入）
    print("[SELFTEST] 测试 9: 文件写入（真实写入）")
    test_file = Path("/tmp/test_output_real.json")
    err, msg = write_output_file(str(test_file), "{}", dry_run=False)
    if err != ERR_OK:
        errors.append(f"真实写入失败: {msg}")
    elif not test_file.exists():
        errors.append("真实写入后文件不存在")
    else:
        print(f"  [PASS] {msg}")

    # 测试 10: 多编码读取
    print("[SELFTEST] 测试 10: 多编码读取")
    test_gbk_file = Path("/tmp/test_gbk.txt")
    try:
        test_gbk_file.write_text("测试中文", encoding="gbk")
        content = read_text_safe(test_gbk_file)
        if content != "测试中文":
            errors.append(f"GBK 读取失败: {content}")
        else:
            print("  [PASS] GBK 编码读取成功")
    except Exception as e:
        errors.append(f"GBK 测试失败: {str(e)}")

    # 汇总
    if errors:
        print(f"\n[SELFTEST] 失败: {len(errors)} 个错误")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("\n[SELFTEST] 全部通过")
        return 0


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="网页结构萃取 模板生成器 - 将网页解析为结构化模板",
        epilog="示例: python run.py --url https://example.com --output template.json"
    )
    parser.add_argument("--url", type=str, help="目标网页 URL")
    parser.add_argument("--file", type=str, help="本地 HTML 文件路径")
    parser.add_argument("--html", type=str, help="直接传入 HTML 代码片段")
    parser.add_argument("--output", type=str, default=".", help="输出目录或文件路径（默认: 当前目录）")
    parser.add_argument("--format", type=str, choices=["json", "yaml", "html"], default="json", help="模板输出格式（默认: json）")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--dry-run", action="store_true", help="预演模式，不实际写盘")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version="%(prog)s 2.0.0")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 输入校验
    if not args.url and not args.file and not args.html:
        print("错误: 必须提供 --url、--file 或 --html 参数之一", file=sys.stderr)
        return 1

    # 获取内容
    content = ""
    source_name = ""
    if args.url:
        print(f"[INFO] 开始解析 URL: {args.url}")
        err, content = fetch_url_content(args.url)
        if err != ERR_OK:
            print(f"错误 [{err}]: {content}", file=sys.stderr)
            return 1
        source_name = urllib.parse.urlparse(args.url).netloc.replace(".", "_")
    elif args.file:
        print(f"[INFO] 开始解析本地文件: {args.file}")
        err, content = read_local_file(args.file)
        if err != ERR_OK:
            print(f"错误 [{err}]: {content}", file=sys.stderr)
            return 1
        source_name = Path(args.file).stem
    elif args.html:
        print("[INFO] 开始解析 HTML 代码片段")
        content = args.html
        source_name = "html_snippet"

    if args.verbose:
        print(f"[VERBOSE] 内容长度: {len(content)} 字节")

    # 解析 HTML
    err, extractor = parse_html_content(content)
    if err != ERR_OK or extractor is None:
        print(f"错误 [{err}]: HTML 解析失败", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"[VERBOSE] DOM 解析完成，根元素: {extractor.root['tag'] if extractor.root else 'None'}")

    # 生成模板
    template = generate_template(extractor, source_name)
    if args.verbose:
        print(f"[VERBOSE] 识别到 {len(template['repeated_blocks'])} 个重复区块")
        print(f"[VERBOSE] 识别到 {len(template['static_elements'])} 个静态元素")

    # 格式化输出
    template_str = format_template_output(template, args.format)
    structure_doc = generate_structure_doc(extractor, template)

    # 确定输出路径
    output_path = Path(args.output)
    if output_path.suffix:  # 用户指定了文件名
        template_file = output_path
        structure_file = output_path.with_name(output_path.stem + "_structure.md")
    else:  # 用户指定了目录
        output_path.mkdir(parents=True, exist_ok=True)
        template_file = output_path / f"template.{args.format}"
        structure_file = output_path / "structure.md"

    # 写入文件
    if args.dry_run:
        print("[DRY-RUN] 预演模式，不实际写盘")
        err, msg = write_output_file(str(template_file), template_str, dry_run=True)
        print(msg)
        err, msg = write_output_file(str(structure_file), structure_doc, dry_run=True)
        print(msg)
    else:
        err, msg = write_output_file(str(template_file), template_str)
        if err != ERR_OK:
            print(f"错误 [{err}]: {msg}", file=sys.stderr)
            return 1
        print(f"[INFO] {msg}")

        err, msg = write_output_file(str(structure_file), structure_doc)
        if err != ERR_OK:
            print(f"错误 [{err}]: {msg}", file=sys.stderr)
            return 1
        print(f"[INFO] {msg}")

    print("[INFO] 处理完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
