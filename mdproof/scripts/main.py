#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mdproof — Markdown 转 PDF 文档转换与格式校验工具

本脚本为独立实现，仅依据功能规格编写。
支持 Markdown 内容解析、格式校验、PDF 生成与批量处理。
"""

import argparse
import hashlib
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 尝试导入第三方库（若未安装则降级为模拟模式）
try:
    import markdown  # pip install markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    import reportlab  # pip install reportlab
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ============================================================
# 错误码定义
# ============================================================
ERR_SUCCESS = 0          # 成功
ERR_INVALID_INPUT = "E001"   # 输入无效
ERR_FILE_NOT_FOUND = "E002"  # 文件不存在
ERR_IO_ERROR = "E003"        # 读写错误
ERR_URL_ERROR = "E004"       # URL 访问失败
ERR_PARSE_ERROR = "E005"     # Markdown 解析错误
ERR_VALIDATE_ERROR = "E006"  # 格式校验失败
ERR_PDF_ERROR = "E007"       # PDF 生成失败
ERR_BATCH_ERROR = "E008"     # 批处理错误
ERR_SIZE_ERROR = "E009"      # 文件大小超限
ERR_UNSUPPORTED = "E010"     # 不支持的操作


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ValidationResult:
    """格式校验结果"""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool = True
    output_path: Optional[str] = None
    error_code: str = ERR_SUCCESS
    error_message: str = ""
    validation: ValidationResult = field(default_factory=ValidationResult)


# ============================================================
# 常量配置
# ============================================================
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_BATCH_FILES = 100

PAGE_SIZES = {
    "A4": (21.0 * cm, 29.7 * cm),
    "LETTER": (21.6 * cm, 27.9 * cm),
}

MARGIN_OPTIONS = {
    "narrow": (1.27 * cm, 1.27 * cm, 1.27 * cm, 1.27 * cm),
    "normal": (2.54 * cm, 2.54 * cm, 2.54 * cm, 2.54 * cm),
    "wide": (3.81 * cm, 3.81 * cm, 3.81 * cm, 3.81 * cm),
}


# ============================================================
# Markdown 格式校验器
# ============================================================
class MarkdownValidator:
    """Markdown 格式校验器"""

    # 常见 URL 协议
    URL_PATTERN = re.compile(
        r'^(https?|ftp|file)://'  # 协议
        r'[^\s/$.?#].[^\s]*$', re.IGNORECASE
    )

    # 代码块标记
    CODE_FENCE = re.compile(r'^(`{3,}|~{3,})')

    # 表格分隔行
    TABLE_SEPARATOR = re.compile(r'^\s*\|?[\s:-]+\|[\s:|:-]*\|?\s*$')

    def validate(self, content: str) -> ValidationResult:
        """校验 Markdown 内容"""
        result = ValidationResult()
        lines = content.split('\n')

        # 检查代码块闭合
        self._check_code_blocks(lines, result)

        # 检查表格格式
        self._check_tables(lines, result)

        # 检查 URL 格式
        self._check_urls(content, result)

        # 检查 YAML frontmatter
        self._check_frontmatter(lines, result)

        result.valid = len(result.errors) == 0
        return result

    def _check_code_blocks(self, lines: List[str], result: ValidationResult) -> None:
        """检查代码块是否闭合"""
        in_block = False
        fence_char = None
        fence_len = 0

        for i, line in enumerate(lines, 1):
            match = self.CODE_FENCE.match(line)
            if match:
                current_fence = match.group(0)
                current_char = current_fence[0]
                current_len = len(current_fence)

                if not in_block:
                    # 开始新代码块
                    in_block = True
                    fence_char = current_char
                    fence_len = current_len
                elif current_char == fence_char and current_len >= fence_len:
                    # 闭合代码块
                    in_block = False
                    fence_char = None
                    fence_len = 0

        if in_block:
            result.errors.append(f"未闭合的代码块（起始于第 {i} 行附近）")

    def _check_tables(self, lines: List[str], result: ValidationResult) -> None:
        """检查表格分隔符格式"""
        i = 0
        while i < len(lines) - 1:
            # 查找可能的表头行（包含 | 符号）
            if '|' in lines[i]:
                # 检查下一行是否为分隔行
                next_line = lines[i + 1]
                if self.TABLE_SEPARATOR.match(next_line):
                    # 验证分隔符列数与表头一致
                    header_cols = self._count_columns(lines[i])
                    sep_cols = self._count_columns(next_line)
                    if header_cols != sep_cols:
                        result.errors.append(
                            f"表格列数不匹配：第 {i+1} 行表头有 {header_cols} 列，"
                            f"第 {i+2} 行分隔符有 {sep_cols} 列"
                        )
            i += 1

    def _count_columns(self, line: str) -> int:
        """统计表格列数"""
        # 去除首尾管道符后分割
        content = line.strip()
        if content.startswith('|'):
            content = content[1:]
        if content.endswith('|'):
            content = content[:-1]
        if not content.strip():
            return 0
        return len([c for c in content.split('|') if c.strip() or '|' in c])

    def _check_urls(self, content: str, result: ValidationResult) -> None:
        """检查 URL 格式"""
        # 匹配 Markdown 链接 [text](url)
        link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
        for match in link_pattern.finditer(content):
            url = match.group(2).strip()
            # 跳过相对路径和锚点
            if url.startswith('#') or url.startswith('/'):
                continue
            if not self.URL_PATTERN.match(url):
                result.warnings.append(f"URL 格式可能异常：{url}")

    def _check_frontmatter(self, lines: List[str], result: ValidationResult) -> None:
        """检查 YAML frontmatter"""
        if not lines:
            return
        first_line = lines[0].strip()
        if first_line == '---':
            # 查找结束标记
            end_idx = None
            for i in range(1, len(lines)):
                if lines[i].strip() == '---':
                    end_idx = i
                    break
            if end_idx is None:
                result.errors.append("YAML frontmatter 未闭合（缺少结束的 ---）")


# ============================================================
# Markdown 解析器
# ============================================================
class MarkdownParser:
    """Markdown 内容解析器"""

    def __init__(self):
        self._html_converter = None
        if HAS_MARKDOWN:
            self._html_converter = markdown.Markdown(
                extensions=['tables', 'fenced_code', 'codehilite']
            )

    def parse(self, content: str) -> str:
        """将 Markdown 解析为 HTML 字符串"""
        if self._html_converter:
            try:
                self._html_converter.reset()
                return self._html_converter.convert(content)
            except Exception as e:
                raise ValueError(f"Markdown 解析失败: {e}") from e
        else:
            # 降级：返回简单转义后的文本
            return self._simple_escape(content)

    def _simple_escape(self, content: str) -> str:
        """简单 HTML 转义（降级模式）"""
        import html
        escaped = html.escape(content)
        # 将换行转为 <br>
        escaped = escaped.replace('\n', '<br>\n')
        return f'<pre>{escaped}</pre>'


# ============================================================
# PDF 生成器
# ============================================================
class PDFGenerator:
    """PDF 文件生成器"""

    def __init__(self, page_size: str = "A4", margin: str = "normal"):
        self.page_size_name = page_size.upper()
        self.page_size = PAGE_SIZES.get(self.page_size_name, PAGE_SIZES["A4"])
        self.margin = MARGIN_OPTIONS.get(margin.lower(), MARGIN_OPTIONS["normal"])

    def generate(self, html_content: str, output_path: str) -> bool:
        """生成 PDF 文件"""
        if not HAS_REPORTLAB:
            # 降级：生成一个简单的文本 PDF
            return self._generate_simple_pdf(html_content, output_path)

        try:
            return self._generate_professional_pdf(html_content, output_path)
        except Exception as e:
            raise RuntimeError(f"PDF 生成失败: {e}") from e

    def _generate_professional_pdf(self, html_content: str, output_path: str) -> bool:
        """使用 reportlab 生成 PDF"""
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        )
        from reportlab.lib import colors

        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.page_size,
            leftMargin=self.margin[0],
            rightMargin=self.margin[1],
            topMargin=self.margin[2],
            bottomMargin=self.margin[3],
        )

        styles = getSampleStyleSheet()
        story = []

        # 解析 HTML 并生成 PDF 元素
        # 简化处理：提取标题、段落、代码块等
        elements = self._html_to_elements(html_content, styles)

        for element in elements:
            if isinstance(element, str):
                story.append(Paragraph(element, styles['Normal']))
            elif isinstance(element, tuple):
                text, style_name = element
                style = styles.get(style_name, styles['Normal'])
                story.append(Paragraph(text, style))
            else:
                story.append(element)
            story.append(Spacer(1, 6))

        doc.build(story)
        return True

    def _html_to_elements(self, html: str, styles) -> List:
        """将 HTML 转为 PDF 元素列表（简化实现）"""
        import re

        elements = []
        # 提取标题
        for match in re.finditer(r'<h([1-6])>(.*?)</h\1>', html, re.DOTALL):
            level = int(match.group(1))
            text = re.sub(r'<[^>]+>', '', match.group(2))
            style_name = f'Heading{level}'
            if style_name in styles:
                elements.append((text, style_name))

        # 提取段落
        for match in re.finditer(r'<p>(.*?)</p>', html, re.DOTALL):
            text = re.sub(r'<[^>]+>', '', match.group(1))
            if text.strip():
                elements.append(text)

        # 提取代码块
        for match in re.finditer(r'<pre><code[^>]*>(.*?)</code></pre>', html, re.DOTALL):
            text = match.group(1)
            elements.append((text, 'Code'))

        return elements

    def _generate_simple_pdf(self, content: str, output_path: str) -> bool:
        """生成简单文本 PDF（降级模式）"""
        try:
            # 使用最简方式生成可读的 PDF
            import html as html_module
            text = re.sub(r'<[^>]+>', '', content)
            text = html_module.unescape(text)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("%PDF-1.4\n")
                f.write("%\xe2\xe3\xcf\xd3\n")

                # 简单文本内容
                lines = text.split('\n')
                content_data = []
                for line in lines:
                    content_data.append(f"BT /F1 12 Tf 72 720 Td ({line}) Tj ET")

                objects = [
                    "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
                    "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
                    "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
                    f"4 0 obj << /Length {len('\\n'.join(content_data))} >> stream\n" + '\n'.join(content_data) + "\nendstream endobj",
                    "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
                ]

                xref_offset = 0
                for obj in objects:
                    f.write(obj + "\n")

                f.write("trailer << /Root 1 0 R >>\n")
                f.write("%%EOF\n")

            return True
        except Exception as e:
            raise RuntimeError(f"降级 PDF 生成失败: {e}") from e


# ============================================================
# 转换器主类
# ============================================================
class MarkdownConverter:
    """Markdown 转 PDF 转换器"""

    def __init__(self, page_size: str = "A4", margin: str = "normal"):
        self.validator = MarkdownValidator()
        self.parser = MarkdownParser()
        self.generator = PDFGenerator(page_size, margin)

    def convert_file(self, input_path: str, output_dir: Optional[str] = None,
                     output_name: Optional[str] = None) -> ConversionResult:
        """转换单个文件"""
        result = ConversionResult()

        try:
            # 检查文件存在
            if not os.path.exists(input_path):
                result.success = False
                result.error_code = ERR_FILE_NOT_FOUND
                result.error_message = f"文件不存在: {input_path}"
                return result

            # 检查文件大小
            file_size = os.path.getsize(input_path)
            if file_size > MAX_FILE_SIZE:
                result.success = False
                result.error_code = ERR_SIZE_ERROR
                result.error_message = f"文件大小 {file_size} 超过限制 {MAX_FILE_SIZE} 字节"
                return result

            # 读取文件
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 校验格式
            validation = self.validator.validate(content)
            result.validation = validation

            # 解析并转换
            html_content = self.parser.parse(content)

            # 确定输出路径
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_name or
                                           Path(input_path).stem + '.pdf')
            else:
                output_path = output_name or Path(input_path).stem + '.pdf'

            # 生成 PDF
            self.generator.generate(html_content, output_path)
            result.output_path = output_path

        except PermissionError as e:
            result.success = False
            result.error_code = ERR_IO_ERROR
            result.error_message = f"权限错误: {e}"
        except UnicodeDecodeError as e:
            result.success = False
            result.error_code = ERR_PARSE_ERROR
            result.error_message = f"文件编码错误: {e}"
        except Exception as e:
            result.success = False
            result.error_code = ERR_PDF_ERROR
            result.error_message = str(e)

        return result

    def convert_content(self, content: str, output_path: str) -> ConversionResult:
        """转换内容字符串"""
        result = ConversionResult()

        try:
            # 校验格式
            validation = self.validator.validate(content)
            result.validation = validation

            # 解析
            html_content = self.parser.parse(content)

            # 生成 PDF
            self.generator.generate(html_content, output_path)
            result.output_path = output_path

        except Exception as e:
            result.success = False
            result.error_code = ERR_PDF_ERROR
            result.error_message = str(e)

        return result

    def convert_url(self, url: str, output_path: str) -> ConversionResult:
        """从 URL 获取 Markdown 并转换"""
        result = ConversionResult()

        try:
            # 下载内容
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')

            # 转换内容
            return self.convert_content(content, output_path)

        except Exception as e:
            result.success = False
            result.error_code = ERR_URL_ERROR
            result.error_message = f"URL 访问失败: {e}"
            return result

    def convert_batch(self, input_paths: List[str], output_dir: str) -> List[ConversionResult]:
        """批量转换多个文件"""
        results = []

        if len(input_paths) > MAX_BATCH_FILES:
            results.append(ConversionResult(
                success=False,
                error_code=ERR_BATCH_ERROR,
                error_message=f"批处理文件数超过限制 {MAX_BATCH_FILES}"
            ))
            return results

        for path in input_paths:
            result = self.convert_file(path, output_dir)
            results.append(result)

        return results


# ============================================================
# 自检测试
# ============================================================
def run_selftest() -> int:
    """运行内置自检"""
    print("=" * 60)
    print("mdproof 自检开始")
    print("=" * 60)

    try:
        # 测试数据（硬编码，不依赖外部文件）
        test_content = """---
title: 测试文档
author: mdproof
---

# 标题一

这是一个**测试**段落，包含[链接](https://example.com)。

## 列表测试

- 项目一
- 项目二
- 项目三

## 表格测试

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A   | B   | C   |
| D   | E   | F   |

## 代码块测试
