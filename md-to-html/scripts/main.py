#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md-to-html 技能实现
-------------------
将 Markdown 文本转换为结构化 HTML。
支持文件读取、URL 抓取、批量转换与自定义样式。

仅依据功能规格独立实现（clean-room）。
"""

import argparse
import html
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少输入或参数无效",
    "E002": "文件不存在或无法读取",
    "E003": "URL 抓取失败或网络不可用",
    "E004": "Markdown 解析失败（内部错误）",
    "E005": "输出目录不可写",
    "E006": "批量处理时部分项目失败",
    "E007": "输入类型不支持",
    "E008": "HTML 模板渲染失败",
    "E009": "编码错误：无法解码输入",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ConversionResult:
    """单次转换的结果。"""
    source_name: str
    html_content: str
    success: bool = True
    error: Optional[str] = None


@dataclass
class ConversionOptions:
    """转换选项。"""
    with_css: bool = True
    css_class: str = "md-content"
    title: str = "Markdown 转换结果"
    lang: str = "zh-CN"
    standalone: bool = True  # True=完整 HTML 文档, False=仅片段


# ---------------------------------------------------------------------------
# Markdown 解析器（轻量级，覆盖常见语法）
# ---------------------------------------------------------------------------

class MarkdownParser:
    """
    轻量级 Markdown 解析器。
    支持：标题、段落、粗体、斜体、行内代码、代码块、链接、图片、
          无序列表、有序列表、引用、水平线、表格（基础）。
    不支持：嵌套表格、数学公式、HTML 内嵌（会转义）。
    """

    # 行级正则
    _HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
    _HR_RE = re.compile(r"^\s*([-*_])\s*\1\s*\1(?:\s*\1)*\s*$")
    _BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
    _CODE_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
    _TABLE_RE = re.compile(r"^\|(.+)\|\s*$")
    _TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|\s*$")
    _UNORDERED_LIST_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
    _ORDERED_LIST_RE = re.compile(r"^\s*\d+\.\s+(.*)$")

    # 行内正则
    _BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
    _ITALIC_RE = re.compile(r"\*(.+?)\*|_(.+?)_")
    _INLINE_CODE_RE = re.compile(r"`([^`]+)`")
    _LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    _IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def __init__(self):
        self._html_content = []
        self._in_code_block = False
        self._code_block_lang = ""
        self._code_block_content = []
        self._in_blockquote = False
        self._blockquote_content = []
        self._in_list = False
        self._list_type = None  # 'ul' or 'ol'
        self._list_items = []
        self._in_table = False
        self._table_headers = []
        self._table_rows = []
        self._current_table_row = []
        self._in_paragraph = False
        self._paragraph_content = []

    def parse(self, markdown_text: str) -> str:
        """解析 Markdown 文本并返回 HTML 字符串。"""
        self._reset_state()
        lines = markdown_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # 处理代码块
            if self._in_code_block:
                fence_match = self._CODE_FENCE_RE.match(line)
                if fence_match and fence_match.group(0).strip() == self._code_block_lang.strip():
                    # 代码块结束
                    self._close_code_block()
                    self._in_code_block = False
                    self._code_block_lang = ""
                    self._code_block_content = []
                else:
                    self._code_block_content.append(line)
                i += 1
                continue

            # 检查是否开始代码块
            fence_match = self._CODE_FENCE_RE.match(line)
            if fence_match:
                self._in_code_block = True
                self._code_block_lang = fence_match.group(0).strip()
                self._code_block_content = []
                i += 1
                continue

            # 处理空行
            if not line.strip():
                self._flush_paragraph()
                self._flush_blockquote()
                self._flush_list()
                self._flush_table()
                i += 1
                continue

            # 处理标题
            heading_match = self._HEADING_RE.match(line)
            if heading_match:
                self._flush_paragraph()
                self._flush_blockquote()
                self._flush_list()
                self._flush_table()
                level = len(heading_match.group(1))
                text = self._parse_inline(heading_match.group(2).strip())
                self._html_content.append(f"<h{level}>{text}</h{level}>")
                i += 1
                continue

            # 处理水平线
            if self._HR_RE.match(line):
                self._flush_paragraph()
                self._flush_blockquote()
                self._flush_list()
                self._flush_table()
                self._html_content.append("<hr />")
                i += 1
                continue

            # 处理引用
            blockquote_match = self._BLOCKQUOTE_RE.match(line)
            if blockquote_match:
                self._flush_paragraph()
                self._flush_list()
                self._flush_table()
                if not self._in_blockquote:
                    self._in_blockquote = True
                    self._blockquote_content = []
                self._blockquote_content.append(blockquote_match.group(1))
                i += 1
                continue

            # 处理表格
            if self._TABLE_RE.match(line):
                self._flush_paragraph()
                self._flush_blockquote()
                self._flush_list()
                if not self._in_table:
                    # 检查是否是表头
                    if i + 1 < len(lines) and self._TABLE_SEPARATOR_RE.match(lines[i+1].strip()):
                        self._in_table = True
                        self._table_headers = self._parse_table_row(line)
                        self._table_rows = []
                        i += 2  # 跳过表头和分隔行
                        continue
                    else:
                        # 不是表格，作为普通文本处理
                        pass
                else:
                    # 在表格中
                    if self._TABLE_RE.match(line):
                        self._table_rows.append(self._parse_table_row(line))
                        i += 1
                        continue
                    else:
                        # 表格结束
                        self._flush_table()
                        continue
            elif self._in_table:
                # 表格结束
                self._flush_table()
                continue

            # 处理列表
            ul_match = self._UNORDERED_LIST_RE.match(line)
            ol_match = self._ORDERED_LIST_RE.match(line)
            if ul_match or ol_match:
                self._flush_paragraph()
                self._flush_blockquote()
                self._flush_table()
                if not self._in_list:
                    self._in_list = True
                    self._list_type = 'ul' if ul_match else 'ol'
                    self._list_items = []
                elif (ul_match and self._list_type != 'ul') or (ol_match and self._list_type != 'ol'):
                    # 列表类型切换
                    self._flush_list()
                    self._in_list = True
                    self._list_type = 'ul' if ul_match else 'ol'
                    self._list_items = []
                item_text = (ul_match.group(1) if ul_match else ol_match.group(1)).strip()
                # 检查嵌套列表（简单处理，不递归）
                if item_text.startswith(('  ', '\t')):
                    item_text = item_text.strip()
                self._list_items.append(self._parse_inline(item_text))
                i += 1
                continue

            # 处理普通段落
            if not self._in_paragraph:
                self._flush_blockquote()
                self._flush_list()
                self._flush_table()
                self._in_paragraph = True
                self._paragraph_content = []
            self._paragraph_content.append(self._parse_inline(line.strip()))
            i += 1

        # 清理剩余状态
        self._flush_paragraph()
        self._flush_blockquote()
        self._flush_list()
        self._flush_table()
        self._close_code_block()

        return '\n'.join(self._html_content)

    def _parse_inline(self, text: str) -> str:
        """解析行内元素。"""
        # 先转义 HTML 特殊字符
        text = html.escape(text, quote=False)

        # 图片
        text = self._IMAGE_RE.sub(
            lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" />',
            text
        )
        # 链接
        text = self._LINK_RE.sub(
            lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
            text
        )
        # 行内代码
        text = self._INLINE_CODE_RE.sub(r'<code>\1</code>', text)
        # 粗体
        text = self._BOLD_RE.sub(r'<strong>\1\2</strong>', text)
        # 斜体
        text = self._ITALIC_RE.sub(r'<em>\1\2</em>', text)
        return text

    def _parse_table_row(self, line: str) -> List[str]:
        """解析表格行。"""
        cells = line.strip().strip('|').split('|')
        return [self._parse_inline(cell.strip()) for cell in cells]

    def _flush_paragraph(self):
        """结束并输出当前段落。"""
        if self._in_paragraph:
            self._html_content.append(f"<p>{' '.join(self._paragraph_content)}</p>")
            self._in_paragraph = False
            self._paragraph_content = []

    def _flush_blockquote(self):
        """结束并输出当前引用。"""
        if self._in_blockquote:
            content = '\n'.join(self._blockquote_content)
            inner_parser = MarkdownParser()
            inner_html = inner_parser.parse(content)
            self._html_content.append(f"<blockquote>{inner_html}</blockquote>")
            self._in_blockquote = False
            self._blockquote_content = []

    def _flush_list(self):
        """结束并输出当前列表。"""
        if self._in_list:
            tag = self._list_type
            items = ''.join(f"<li>{item}</li>" for item in self._list_items)
            self._html_content.append(f"<{tag}>{items}</{tag}>")
            self._in_list = False
            self._list_type = None
            self._list_items = []

    def _flush_table(self):
        """结束并输出当前表格。"""
        if self._in_table:
            table = ['<table>']
            if self._table_headers:
                table.append('<thead><tr>')
                for header in self._table_headers:
                    table.append(f'<th>{header}</th>')
                table.append('</tr></thead>')
            if self._table_rows:
                table.append('<tbody>')
                for row in self._table_rows:
                    table.append('<tr>')
                    for cell in row:
                        table.append(f'<td>{cell}</td>')
                    table.append('</tr>')
                table.append('</tbody>')
            table.append('</table>')
            self._html_content.append(''.join(table))
            self._in_table = False
            self._table_headers = []
            self._table_rows = []

    def _close_code_block(self):
        """结束并输出当前代码块。"""
        if self._in_code_block:
            lang = self._code_block_lang.lstrip('`~').strip() if self._code_block_lang else ''
            code = '\n'.join(self._code_block_content)
            code = html.escape(code)
            if lang:
                self._html_content.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
            else:
                self._html_content.append(f'<pre><code>{code}</code></pre>')
            self._in_code_block = False
            self._code_block_lang = ""
            self._code_block_content = []

    def _reset_state(self):
        """重置解析器状态。"""
        self._html_content = []
        self._in_code_block = False
        self._code_block_lang = ""
        self._code_block_content = []
        self._in_blockquote = False
        self._blockquote_content = []
        self._in_list = False
        self._list_type = None
        self._list_items = []
        self._in_table = False
        self._table_headers = []
        self._table_rows = []
        self._in_paragraph = False
        self._paragraph_content = []


# ---------------------------------------------------------------------------
# 转换器
# ---------------------------------------------------------------------------

class MarkdownToHTMLConverter:
    """Markdown 转 HTML 转换器。"""

    def __init__(self, options: Optional[ConversionOptions] = None):
        self.options = options or ConversionOptions()
        self.parser = MarkdownParser()

    def convert(self, markdown_text: str, source_name: str = "input.md") -> ConversionResult:
        """将 Markdown 文本转换为 HTML。"""
        try:
            html_body = self.parser.parse(markdown_text)
            if self.options.standalone:
                full_html = self._wrap_full_document(html_body)
            else:
                full_html = html_body
            return ConversionResult(
                source_name=source_name,
                html_content=full_html,
                success=True
            )
        except Exception as e:
            return ConversionResult(
                source_name=source_name,
                html_content="",
                success=False,
                error=f"[E004] Markdown 解析失败: {str(e)}"
            )

    def _wrap_full_document(self, body_html: str) -> str:
        """包装为完整 HTML 文档。"""
        css = ""
        if self.options.with_css:
            css = f"""
    <style>
        .{self.options.css_class} {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .{self.options.css_class} h1, .{self.options.css_class} h2, .{self.options.css_class} h3,
        .{self.options.css_class} h4, .{self.options.css_class} h5, .{self.options.css_class} h6 {{
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 600;
            line-height: 1.25;
        }}
        .{self.options.css_class} h1 {{ font-size: 2em; }}
        .{self.options.css_class} h2 {{ font-size: 1.5em; }}
        .{self.options.css_class} h3 {{ font-size: 1.25em; }}
        .{self.options.css_class} code {{
            background-color: #f6f8fa;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 85%;
        }}
        .{self.options.css_class} pre {{
            background-color: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow: auto;
        }}
        .{self.options.css_class} pre code {{
            background-color: transparent;
            padding: 0;
        }}
        .{self.options.css_class} blockquote {{
            margin: 0;
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
        }}
        .{self.options.css_class} table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        .{self.options.css_class} th, .{self.options.css_class} td {{
            border: 1px solid #dfe2e5;
            padding: 6px 13px;
        }}
        .{self.options.css_class} th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        .{self.options.css_class} ul, .{self.options.css_class} ol {{
            padding-left: 2em;
        }}
        .{self.options.css_class} hr {{
            height: 0.25em;
            padding: 0;
            margin: 24px 0;
            background-color: #e1e4e8;
            border: 0;
        }}
    </style>
"""

        return f"""<!DOCTYPE html>
<html lang="{self.options.lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(self.options.title)}</title>
{css}
</head>
<body>
    <div class="{self.options.css_class}">
{body_html}
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# 输入处理
# ---------------------------------------------------------------------------

def read_input(source: str) -> Tuple[str, str]:
    """读取输入源，返回 (内容, 来源名称)。"""
    if source == '-':
        # 从标准输入读取
        content = sys.stdin.read()
        return content, "stdin"
    elif source.startswith('http://') or source.startswith('https://'):
        # 从 URL 读取
        try:
            with urllib.request.urlopen(source, timeout=10) as response:
                content = response.read().decode('utf-8', errors='replace')
            return content, source
        except Exception as e:
            raise SkillError("E003", f"URL 抓取失败: {str(e)}")
    elif os.path.isfile(source):
        # 从文件读取
        try:
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, os.path.basename(source)
        except UnicodeDecodeError:
            raise SkillError("E009", f"无法解码文件 {source}")
        except Exception as e:
            raise SkillError("E002", f"无法读取文件 {source}: {str(e)}")
    else:
        raise SkillError("E002", f"文件不存在: {source}")


def write_output(content: str, output_path: Optional[str], source_name: str):
    """写入输出文件。"""
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已写入: {output_path}")
        except Exception as e:
            raise SkillError("E005", f"无法写入输出文件 {output_path}: {str(e)}")
    else:
        # 输出到标准输出
        print(content)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="将 Markdown 转换为 HTML",
        epilog="示例: md-to-html input.md -o output.html --no-css"
    )
    parser.add_argument(
        'input', nargs='?', help='输入文件路径、URL 或 "-" 从标准输入读取'
    )
    parser.add_argument(
        '-o', '--output', help='输出文件路径（默认输出到标准输出）'
    )
    parser.add_argument(
        '--no-css', action='store_true', help='不包含内嵌 CSS 样式'
    )
    parser.add_argument(
        '--css-class', default='md-content', help='自定义 CSS 类名（默认: md-content）'
    )
    parser.add_argument(
        '--title', default='Markdown 转换结果', help='HTML 文档标题'
    )
    parser.add_argument(
        '--lang', default='zh-CN', help='HTML 语言属性（默认: zh-CN）'
    )
    parser.add_argument(
        '--fragment', action='store_true', help='仅输出 HTML 片段，不包含完整文档'
    )
    parser.add_argument(
        '--batch', nargs='+', help='批量处理多个文件（空格分隔）'
    )
    parser.add_argument(
        '--output-dir', help='批量处理时的输出目录'
    )
    parser.add_argument(
        '--selftest', action='store_true', help='运行自测并退出'
    )

    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    try:
        if args.batch:
            # 批量处理
            results = []
            for file_path in args.batch:
                try:
                    content, source_name = read_input(file_path)
                    options = ConversionOptions(
                        with_css=not args.no_css,
                        css_class=args.css_class,
                        title=args.title,
                        lang=args.lang,
                        standalone=not args.fragment
                    )
                    converter = MarkdownToHTMLConverter(options)
                    result = converter.convert(content, source_name)
                    results.append(result)
                    if result.success:
                        print(f"✓ 转换成功: {file_path}")
                        if args.output_dir:
                            os.makedirs(args.output_dir, exist_ok=True)
                            output_file = os.path.join(
                                args.output_dir,
                                os.path.splitext(os.path.basename(file_path))[0] + '.html'
                            )
                            write_output(result.html_content, output_file, source_name)
                    else:
                        print(f"✗ 转换失败: {file_path} - {result.error}")
                except SkillError as e:
                    print(f"✗ 处理失败: {file_path} - {e}")
                    results.append(ConversionResult(
                        source_name=file_path,
                        html_content="",
                        success=False,
                        error=str(e)
                    ))

            failed = [r for r in results if not r.success]
            if failed:
                raise SkillError("E006", f"批量处理完成，{len(failed)} 个项目失败")
            return

        # 单个文件处理
        if not args.input:
            raise SkillError("E001", "缺少输入参数")

        content, source_name = read_input(args.input)
        options = ConversionOptions(
            with_css=not args.no_css,
            css_class=args.css_class,
            title=args.title,
            lang=args.lang,
            standalone=not args.fragment
        )
        converter = MarkdownToHTMLConverter(options)
        result = converter.convert(content, source_name)

        if result.success:
            write_output(result.html_content, args.output, source_name)
        else:
            raise SkillError("E004", result.error)

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 自测
# ---------------------------------------------------------------------------

def run_selftest():
    """运行自测，验证核心功能。"""
    print("运行自测...")

    # 测试用例
    test_cases = [
        {
            "name": "基础元素",
            "markdown": "# 标题\n\n这是**粗体**和*斜体*文本，还有`行内代码`。\n\n## 二级标题\n\n- 列表项 1\n- 列表项 2\n\n1. 有序项 1\n2. 有序项 2\n\n> 引用文本\n\n---\n\n[链接](https://example.com)\n\n![图片](image.png)",
            "checks": [
                ("<h1>", "包含 h1 标签"),
                ("<strong>", "包含粗体标签"),
                ("<em>", "包含斜体标签"),
                ("<code>", "包含行内代码标签"),
                ("<ul>", "包含无序列表标签"),
                ("<ol>", "包含有序列表标签"),
                ("<blockquote>", "包含引用标签"),
                ("<hr />", "包含水平线标签"),
                ('<a href="https://example.com">', "包含链接标签"),
                ('<img src="image.png"', "包含图片标签"),
            ]
        },
        {
            "name": "代码块",
            "markdown": "
