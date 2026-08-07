#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点克隆模板生成器（ai-website-cloner-template）
=================================================
将目标网站或本地 HTML 文件解析为结构化克隆模板（JSON），
供 AI 编码代理直接消费。

作者: 林墨
版本: 1.0.2
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
        <nav class="nav-bar">
            <ul>
                <li><a href="/">首页</a></li>
                <li><a href="/about">关于</a></li>
                <li><a href="/contact">联系</a></li>
            </ul>
        </nav>
    </header>
    <main id="main-content">
        <section class="hero-section">
            <h1>欢迎光临</h1>
            <p>这是一个示例页面，用于自检。</p>
            <img src="/images/banner.jpg" alt="横幅">
        </section>
        <section class="features">
            <div class="feature-card">
                <h2>特性一</h2>
                <p>描述文字。</p>
            </div>
            <div class="feature-card">
                <h2>特性二</h2>
                <p>描述文字。</p>
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
# HTML 解析器（基于标准库 html.parser）
# ---------------------------------------------------------------------------
class StructureExtractor(HTMLParser):
    """提取 HTML 的 DOM 结构、标签、类名、资源引用等关键信息。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: Set[str] = set()               # 所有出现的标签名
        self.classes: Set[str] = set()            # 所有出现的类名
        self.ids: Set[str] = set()                # 所有出现的 id
        self.attributes: Set[str] = set()         # 所有出现的属性名
        self.links: List[str] = []                # 外部资源链接（css/js/img）
        self.text_content: List[str] = []         # 页面文本内容（非空）
        self.dom_tree: List[Dict[str, Any]] = []  # DOM 树（简化）
        self._stack: List[Dict[str, Any]] = []    # 解析栈

    def handle_starttag(
        self, tag: str, attrs: List[Tuple[str, Optional[str]]]
    ) -> None:
        """处理开始标签。"""
        self.tags.add(tag)
        attr_dict: Dict[str, str] = {}
        for key, value in attrs:
            self.attributes.add(key)
            attr_dict[key] = value if value is not None else ""
            if key == "class" and value:
                self.classes.update(value.split())
            elif key == "id" and value:
                self.ids.add(value)
            elif key == "href" and value:
                self.links.append(value)
            elif key == "src" and value:
                self.links.append(value)

        node: Dict[str, Any] = {
            "tag": tag,
            "attrs": attr_dict,
            "children": [],
        }
        if self._stack:
            self._stack[-1]["children"].append(node)
        else:
            self.dom_tree.append(node)
        self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        """处理结束标签。"""
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        """处理文本数据。"""
        text = data.strip()
        if text:
            self.text_content.append(text)


def extract_structure(html_content: str) -> Dict[str, Any]:
    """从 HTML 内容中提取结构化信息。"""
    parser = StructureExtractor()
    try:
        parser.feed(html_content)
        parser.close()
    except Exception as exc:
        raise RuntimeError(f"{ERR_HTML_PARSE_FAILED}: HTML 解析失败: {exc}") from exc

    return {
        "tags": sorted(parser.tags),
        "classes": sorted(parser.classes),
        "ids": sorted(parser.ids),
        "attributes": sorted(parser.attributes),
        "resources": sorted(set(parser.links)),
        "text_snippets": parser.text_content[:50],  # 最多保存 50 条文本片段
        "dom_tree": parser.dom_tree,
        "node_count": _count_nodes(parser.dom_tree),
    }


def _count_nodes(tree: List[Dict[str, Any]]) -> int:
    """递归统计 DOM 节点数量。"""
    count = 0
    for node in tree:
        count += 1
        count += _count_nodes(node.get("children", []))
    return count


# ---------------------------------------------------------------------------
# 模板生成核心逻辑
# ---------------------------------------------------------------------------
def build_template(
    source: str,
    content: str,
    source_type: str = "url",
) -> Dict[str, Any]:
    """
    根据原始内容生成结构化克隆模板。

    参数:
        source: 来源标识（URL 或文件路径）
        content: 原始 HTML 内容
        source_type: 来源类型（"url" 或 "file"）

    返回:
        结构化模板字典
    """
    if not content or not content.strip():
        raise ValueError(f"{ERR_EMPTY_CONTENT}: 内容为空，无法生成模板")

    # 提取结构
    structure = extract_structure(content)

    # 生成内容哈希（用于标识）
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    # 推断布局框架类型（简单启发式）
    layout_framework = _detect_framework(structure["tags"], structure["classes"])

    # 推断响应式布局
    responsive = _detect_responsive(structure["tags"], structure["attributes"])

    # 构建模板
    template: Dict[str, Any] = {
        "template_meta": {
            "version": "1.0.2",
            "source": source,
            "source_type": source_type,
            "content_hash": content_hash,
            "generated_by": "ai-website-cloner-template",
        },
        "page": {
            "title": _extract_title(content),
            "language": _extract_language(content),
        },
        "structure": {
            "node_count": structure["node_count"],
            "tags": structure["tags"],
            "classes": structure["classes"],
            "ids": structure["ids"],
            "attributes": structure["attributes"],
            "dom_tree": structure["dom_tree"],
        },
        "style_variables": _extract_style_variables(content),
        "resources": {
            "links": structure["resources"],
            "count": len(structure["resources"]),
        },
        "layout": {
            "framework": layout_framework,
            "responsive": responsive,
        },
        "text_content": structure["text_snippets"],
    }

    return template


def _extract_title(html_content: str) -> str:
    """提取页面标题。"""
    match = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_language(html_content: str) -> str:
    """提取页面语言。"""
    match = re.search(r'<html[^>]*lang=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    return match.group(1) if match else ""


def _detect_framework(tags: List[str], classes: List[str]) -> str:
    """通过标签和类名推断前端框架。"""
    tag_set = set(tags)
    class_set = set(classes)

    # React/Vue 常见特征
    if any(c.startswith("react") for c in class_set):
        return "react"
    if any(c.startswith("vue") for c in class_set):
        return "vue"
    if any(c.startswith("ng-") for c in class_set):
        return "angular"

    # 静态站点常见特征
    if "main" in tag_set and "section" in tag_set and "article" in tag_set:
        return "static-html"

    return "unknown"


def _detect_responsive(tags: List[str], attributes: List[str]) -> bool:
    """检测是否为响应式布局。"""
    # 检查是否有 viewport meta 或响应式相关属性
    return "viewport" in attributes or "media" in attributes


def _extract_style_variables(html_content: str) -> Dict[str, str]:
    """提取 CSS 变量（简化实现）。"""
    variables: Dict[str, str] = {}
    # 查找 :root 或选择器中的 --var-name: value 模式
    pattern = r"--([a-zA-Z0-9_-]+)\s*:\s*([^;}\n]+)"
    for match in re.finditer(pattern, html_content):
        var_name = match.group(1).strip()
        var_value = match.group(2).strip()
        if var_name and var_value:
            variables[var_name] = var_value
    return variables


# ---------------------------------------------------------------------------
# 输入获取
# ---------------------------------------------------------------------------
def fetch_url_content(url: str) -> str:
    """从 URL 获取 HTML 内容。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            data = response.read()
            return data.decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{ERR_URL_FETCH_FAILED}: 无法获取 URL 内容: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"{ERR_URL_FETCH_FAILED}: URL 访问异常: {exc}") from exc


def read_file_content(file_path: str) -> str:
    """读取本地文件内容。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{ERR_FILE_NOT_FOUND}: 文件不存在: {file_path}")
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"{ERR_FILE_READ_FAILED}: 文件读取失败: {exc}") from exc


# ---------------------------------------------------------------------------
# 输出处理
# ---------------------------------------------------------------------------
def save_template(template: Dict[str, Any], output_path: str) -> None:
    """将模板保存为 JSON 文件。"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        raise RuntimeError(f"{ERR_OUTPUT_WRITE_FAILED}: 输出文件写入失败: {exc}") from exc


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    使用内置硬编码数据执行离线自检。
    不读取外部文件、不访问网络、不依赖当前工作目录。
    """
    print("开始自检...")

    try:
        # 1. 使用硬编码 HTML 生成模板
        template = build_template(
            source="selftest://example.com",
            content=SELFTEST_HTML,
            source_type="selftest",
        )

        # 2. 验证模板基本结构
        assert "template_meta" in template, "模板缺少 template_meta"
        assert "page" in template, "模板缺少 page"
        assert "structure" in template, "模板缺少 structure"
        assert "resources" in template, "模板缺少 resources"
        assert "layout" in template, "模板缺少 layout"

        # 3. 验证页面信息
        page = template["page"]
        assert page.get("title") == "示例站点", f"标题提取错误: {page.get('title')}"
        assert page.get("language") == "zh-CN", f"语言提取错误: {page.get('language')}"

        # 4. 验证结构信息（宽松断言）
        structure = template["structure"]
        assert structure["node_count"] > 0, "DOM 节点数量应为正数"
        assert "html" in structure["tags"], "缺少 html 标签"
        assert "body" in structure["tags"], "缺少 body 标签"
        assert "header" in structure["tags"], "缺少 header 标签"
        assert "footer" in structure["tags"], "缺少 footer 标签"
        assert "site-header" in structure["classes"], "缺少 site-header 类"
        assert "site-footer" in structure["classes"], "缺少 site-footer 类"
        assert "main-content" in structure["ids"], "缺少 main-content id"

        # 5. 验证资源提取（宽松断言）
        resources = template["resources"]
        assert resources["count"] >= 3, f"资源数量应>=3，实际: {resources['count']}"
        assert any("css" in r for r in resources["links"]), "缺少 CSS 资源"
        assert any("img" in r or "image" in r for r in resources["links"]), "缺少图片资源"

        # 6. 验证文本内容
        text_content = template["text_content"]
        assert len(text_content) > 0, "文本内容不应为空"
        assert any("欢迎" in t for t in text_content), "缺少预期文本内容"

        # 7. 验证布局信息
        layout = template["layout"]
        assert layout["framework"] in ("static-html", "unknown"), f"框架检测异常: {layout['framework']}"
        assert layout["responsive"] is True, "应检测到响应式布局"

        # 8. 验证 DOM 树
        dom_tree = structure["dom_tree"]
        assert len(dom_tree) > 0, "DOM 树不应为空"
        assert dom_tree[0]["tag"] == "html", "DOM 树根节点应为 html"

        print("✅ 自检全部通过！")
        return True

    except AssertionError as exc:
        print(f"❌ 自检失败: {exc}")
        return False
    except Exception as exc:
        print(f"❌ 自检异常: {exc}")
        return False


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="站点克隆模板生成器 - 将网站或 HTML 文件转换为结构化克隆模板",
        epilog="示例: python main.py --url https://example.com -o template.json",
    )
    parser.add_argument("--url", type=str, help="目标网站 URL")
    parser.add_argument("--file", type=str, help="本地 HTML 文件路径")
    parser.add_argument("-o", "--output", type=str, default="template.json", help="输出 JSON 文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.2")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数校验
    if not args.url and not args.file:
        print(f"错误 [{ERR_INVALID_INPUT}]: 必须指定 --url 或 --file 参数")
        parser.print_help()
        return 1

    if args.url and args.file:
        print(f"错误 [{ERR_INVALID_INPUT}]: --url 和 --file 不能同时使用")
        return 1

    try:
        # 获取输入内容
        if args.url:
            print(f"正在获取 URL: {args.url}")
            content = fetch_url_content(args.url)
            source_type = "url"
            source = args.url
        else:
            print(f"正在读取文件: {args.file}")
            content = read_file_content(args.file)
            source_type = "file"
            source = args.file

        # 生成模板
        print("正在生成模板...")
        template = build_template(source=source, content=content, source_type=source_type)

        # 保存输出
        save_template(template, args.output)
        print(f"✅ 模板已生成: {args.output}")

        # 输出摘要
        structure = template["structure"]
        resources = template["resources"]
        print(f"   节点数: {structure['node_count']}")
        print(f"   标签数: {len(structure['tags'])}")
        print(f"   类名数: {len(structure['classes'])}")
        print(f"   资源数: {resources['count']}")
        print(f"   布局框架: {template['layout']['framework']}")
        print(f"   响应式: {'是' if template['layout']['responsive'] else '否'}")

        return 0

    except FileNotFoundError as exc:
        print(f"错误: {exc}")
        return 1
    except RuntimeError as exc:
        print(f"错误: {exc}")
        return 1
    except Exception as exc:
        print(f"错误 [{ERR_INTERNAL}]: 发生未预期的异常: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
