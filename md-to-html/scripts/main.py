#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md-to-html 技能实现脚本

功能：将 Markdown 文本转换为结构化 HTML 网页。
支持：文本转换、文件转换、URL 抓取转换、批量处理、自定义输出格式。
自检：通过 --selftest 参数运行内置硬编码样例，离线验证核心逻辑。

错误码：
    E001 - 参数解析错误
    E002 - 输入读取失败（文件不存在或不可读）
    E003 - URL 抓取失败（网络错误或非 Markdown 内容）
    E004 - Markdown 解析错误（语法无法识别）
    E005 - HTML 生成错误（模板渲染失败）
    E006 - 批量处理中断（部分文件失败）
    E007 - 输出写入失败
    E008 - 无效的输入类型（既不是文本也不是文件路径）
    E009 - 编码错误（文件编码无法识别）
    E010 - 自检失败（核心逻辑异常）
"""

import argparse
import html
import os
import re
import sys
import urllib.request
from typing import Dict, List, Optional, Tuple

# 版本信息
__version__ = "1.0.1"
__author__ = "LinguaForge"


# ============================================================
# 核心工具函数
# ============================================================

def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符，防止注入"""
    return html.escape(text, quote=True)


def _strip_code_fence(line: str) -> str:
    """去除代码围栏标记"""
    return line.strip().lstrip("`~").strip()


def _is_code_fence(line: str, fence_char: str = "`") -> bool:
    """判断是否为代码围栏起始行"""
    stripped = line.strip()
    return stripped.startswith(fence_char * 3)


def _is_heading(line: str) -> bool:
    """判断是否为标题行"""
    return bool(re.match(r"^#{1,6}\s", line.strip()))


def _parse_heading(line: str) -> Tuple[int, str]:
    """解析标题级别和内容"""
    stripped = line.strip()
    level = 0
    for ch in stripped:
        if ch == "#":
            level += 1
        else:
            break
    content = stripped[level:].strip()
    return level, content


def _is_unordered_list_item(line: str) -> bool:
    """判断是否为无序列表项"""
    return bool(re.match(r"^[\s]*[-*+]\s+", line))


def _is_ordered_list_item(line: str) -> bool:
    """判断是否为有序列表项"""
    return bool(re.match(r"^[\s]*\d+[.)]\s+", line))


def _parse_list_item(line: str) -> Tuple[str, str]:
    """解析列表项，返回类型和内容"""
    stripped = line.strip()
    if stripped.startswith(("-", "*", "+")):
        content = stripped[1:].strip()
        return "ul", content
    else:
        # 有序列表
        match = re.match(r"^(\d+)[.)]\s+(.*)", stripped)
        if match:
            return "ol", match.group(2)
    return "ul", stripped


def _is_blockquote(line: str) -> bool:
    """判断是否为引用块"""
    return line.strip().startswith(">")


def _is_horizontal_rule(line: str) -> bool:
    """判断是否为水平分割线"""
    stripped = line.strip()
    return bool(re.match(r"^([-*_]\s*){3,}$", stripped))


def _is_table_separator(line: str) -> bool:
    """判断是否为表格分隔行"""
    stripped = line.strip()
    return bool(re.match(r"^[\s|:-\s]+$", stripped)) and "-" in stripped


def _parse_inline_elements(text: str) -> str:
    """
    解析行内元素：粗体、斜体、行内代码、链接、图片
    
    注意：此实现为简化版，仅处理常见场景
    """
    result = text
    
    # 行内代码（先处理，避免代码内的标记被误解析）
    result = re.sub(r"`([^`]+)`", r"<code>\1</code>", result)
    
    # 图片 ![alt](url)
    result = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" />', result)
    
    # 链接 [text](url)
    result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', result)
    
    # 粗体 **text** 或 __text__
    result = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", result)
    result = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", result)
    
    # 斜体 *text* 或 _text_
    result = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", result)
    result = re.sub(r"_([^_]+)_", r"<em>\1</em>", result)
    
    return result


def _parse_table(lines: List[str], start_idx: int) -> Tuple[str, int]:
    """
    解析表格，返回 (HTML表格字符串, 结束索引)
    
    表格格式：
    | 列1 | 列2 |
    |-----|-----|
    | 数据 | 数据 |
    """
    if start_idx >= len(lines):
        return "", start_idx
    
    # 表头行
    header_line = lines[start_idx].strip()
    if not header_line.startswith("|") or not header_line.endswith("|"):
        return "", start_idx
    
    header_cells = [cell.strip() for cell in header_line.strip("|").split("|")]
    
    # 检查下一行是否为分隔行
    if start_idx + 1 >= len(lines):
        return "", start_idx
    
    if not _is_table_separator(lines[start_idx + 1]):
        return "", start_idx
    
    # 解析数据行
    rows = []
    idx = start_idx + 2
    while idx < len(lines):
        line = lines[idx].strip()
        if not line.startswith("|") or not line.endswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
        idx += 1
    
    # 生成 HTML
    html_table = ["<table>", "<thead><tr>"]
    for cell in header_cells:
        html_table.append(f"<th>{_parse_inline_elements(cell)}</th>")
    html_table.append("</tr></thead>")
    
    if rows:
        html_table.append("<tbody>")
        for row in rows:
            html_table.append("<tr>")
            for cell in row:
                html_table.append(f"<td>{_parse_inline_elements(cell)}</td>")
            html_table.append("</tr>")
        html_table.append("</tbody>")
    
    html_table.append("</table>")
    return "\n".join(html_table), idx


# ============================================================
# Markdown 解析器
# ============================================================

def markdown_to_html(markdown_text: str) -> str:
    """
    将 Markdown 文本转换为 HTML
    
    支持：标题、段落、列表、引用、代码块、表格、水平线、行内样式
    不支持：数学公式、图片本地化、复杂嵌套表格
    """
    if not markdown_text or not markdown_text.strip():
        return "<p></p>"
    
    lines = markdown_text.split("\n")
    html_parts: List[str] = []
    idx = 0
    
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        
        # 空行
        if not stripped:
            idx += 1
            continue
        
        # 代码块（围栏式）
        if _is_code_fence(line):
            fence_char = line.strip()[0]
            code_lines = []
            idx += 1
            while idx < len(lines) and not _is_code_fence(lines[idx], fence_char):
                code_lines.append(lines[idx])
                idx += 1
            idx += 1  # 跳过结束围栏
            code_text = "\n".join(code_lines)
            html_parts.append(f"<pre><code>{_escape_html(code_text)}</code></pre>")
            continue
        
        # 标题
        if _is_heading(line):
            level, content = _parse_heading(line)
            content_html = _parse_inline_elements(content)
            html_parts.append(f"<h{level}>{content_html}</h{level}>")
            idx += 1
            continue
        
        # 水平分割线
        if _is_horizontal_rule(line):
            html_parts.append("<hr />")
            idx += 1
            continue
        
        # 引用块
        if _is_blockquote(line):
            quote_lines = []
            while idx < len(lines) and _is_blockquote(lines[idx]):
                quote_content = lines[idx].strip()
                if quote_content.startswith(">"):
                    quote_content = quote_content[1:].strip()
                quote_lines.append(quote_content)
                idx += 1
            quote_text = "\n".join(quote_lines)
            # 递归解析引用内容
            inner_html = markdown_to_html(quote_text)
            html_parts.append(f"<blockquote>{inner_html}</blockquote>")
            continue
        
        # 表格
        if line.strip().startswith("|") and idx + 1 < len(lines) and _is_table_separator(lines[idx + 1]):
            table_html, idx = _parse_table(lines, idx)
            if table_html:
                html_parts.append(table_html)
                continue
            else:
                idx += 1
                continue
        
        # 无序列表
        if _is_unordered_list_item(line):
            list_items = []
            while idx < len(lines) and _is_unordered_list_item(lines[idx]):
                _, content = _parse_list_item(lines[idx])
                list_items.append(f"<li>{_parse_inline_elements(content)}</li>")
                idx += 1
            html_parts.append(f"<ul>{''.join(list_items)}</ul>")
            continue
        
        # 有序列表
        if _is_ordered_list_item(line):
            list_items = []
            while idx < len(lines) and _is_ordered_list_item(lines[idx]):
                _, content = _parse_list_item(lines[idx])
                list_items.append(f"<li>{_parse_inline_elements(content)}</li>")
                idx += 1
            html_parts.append(f"<ol>{''.join(list_items)}</ol>")
            continue
        
        # 段落（累积直到空行或特殊标记）
        para_lines = []
        while idx < len(lines):
            current = lines[idx].strip()
            if not current:
                break
            if _is_heading(current) or _is_code_fence(current) or _is_horizontal_rule(current):
                break
            if _is_unordered_list_item(current) or _is_ordered_list_item(current):
                break
            if _is_blockquote(current):
                break
            if current.startswith("|") and idx + 1 < len(lines) and _is_table_separator(lines[idx + 1]):
                break
            para_lines.append(current)
            idx += 1
        
        if para_lines:
            para_text = " ".join(para_lines)
            para_html = _parse_inline_elements(para_text)
            html_parts.append(f"<p>{para_html}</p>")
            continue
        
        # 无法识别的行，按段落处理
        html_parts.append(f"<p>{_escape_html(stripped)}</p>")
        idx += 1
    
    return "\n".join(html_parts)


# ============================================================
# HTML 文档生成
# ============================================================

def generate_html_document(content_html: str, title: str = "Markdown 转换结果", css: Optional[str] = None) -> str:
    """
    生成完整的 HTML 文档
    
    Args:
        content_html: 已转换的 HTML 内容
        title: 页面标题
        css: 自定义 CSS 样式（为 None 时使用默认样式）
    
    Returns:
        完整的 HTML 文档字符串
    """
    if css is None:
        css = """
        body {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        pre {
            background-color: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
        }
        code {
            background-color: #f6f8fa;
            padding: 2px 4px;
            border-radius: 3px;
        }
        pre code {
            background-color: transparent;
            padding: 0;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f6f8fa;
        }
        blockquote {
            border-left: 4px solid #ddd;
            margin: 16px 0;
            padding: 8px 16px;
            color: #666;
        }
        img {
            max-width: 100%;
        }
        """
    
    title_escaped = _escape_html(title)
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_escaped}</title>
    <style>
{css}
    </style>
</head>
<body>
{content_html}
</body>
</html>"""


# ============================================================
# 输入处理函数
# ============================================================

def process_text(text: str, title: str = "Markdown 转换结果", css: Optional[str] = None) -> str:
    """处理文本输入，返回完整 HTML 文档"""
    try:
        content_html = markdown_to_html(text)
        return generate_html_document(content_html, title, css)
    except Exception as e:
        raise RuntimeError(f"E004: Markdown 解析失败 - {str(e)}")


def process_file(file_path: str, title: str = "Markdown 转换结果", css: Optional[str] = None) -> str:
    """处理文件输入，返回完整 HTML 文档"""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"E002: 文件不存在或不可读 - {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError:
        raise UnicodeError(f"E009: 文件编码无法识别 - {file_path}")
    except IOError as e:
        raise IOError(f"E002: 文件读取失败 - {file_path}: {str(e)}")
    
    return process_text(text, title, css)


def process_url(url: str, title: str = "Markdown 转换结果", css: Optional[str] = None) -> str:
    """处理 URL 输入，返回完整 HTML 文档"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise ConnectionError(f"E003: URL 抓取失败 - {url}: {str(e)}")
    
    return process_text(content, title, css)


def process_batch(inputs: List[str], titles: Optional[List[str]] = None, css: Optional[str] = None) -> List[str]:
    """
    批量处理多个输入
    
    Args:
        inputs: 输入列表，可以是文本、文件路径或 URL
        titles: 可选的标题列表
        css: 自定义 CSS
    
    Returns:
        HTML 文档列表
    
    Raises:
        RuntimeError: 如果所有输入都失败
    """
    results = []
    errors = []
    
    for i, input_item in enumerate(inputs):
        title = f"文档 {i+1}" if not titles else titles[i]
        try:
            if input_item.startswith(("http://", "https://")):
                results.append(process_url(input_item, title, css))
            elif os.path.isfile(input_item):
                results.append(process_file(input_item, title, css))
            else:
                # 默认为文本输入
                results.append(process_text(input_item, title, css))
        except Exception as e:
            errors.append(f"项目 {i+1} ({input_item}): {str(e)}")
    
    if errors and not results:
        raise RuntimeError(f"E006: 批量处理失败 - {'; '.join(errors)}")
    
    return results


# ============================================================
# 命令行接口
# ============================================================

def run_selftest() -> int:
    """
    运行自检程序，使用内置硬编码样例验证核心逻辑
    
    返回 0 表示成功，非 0 表示失败
    """
    print("开始自检...")
    
    try:
        # 测试样例 1: 基础 Markdown（使用单行字符串避免三引号问题）
        sample_md = (
            "# 标题测试\n\n"
            "这是一个**粗体**和*斜体*的段落。\n\n"
            "## 二级标题\n\n"
            "- 列表项一\n"
            "- 列表项二\n\n"
            "1. 有序项一\n"
            "2. 有序项二\n\n"
            "> 这是一段引用\n\n"
            "
