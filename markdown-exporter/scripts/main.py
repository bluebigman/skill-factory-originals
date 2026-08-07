#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-exporter 技能实现脚本

本脚本根据功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供 Markdown 内容的结构化解析、转换与导出能力，并内置离线自检。
"""

import argparse
import csv
import html
import io
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件写入失败",
    "E007": "不支持的输出格式",
    "E008": "URL 访问被拒绝（离线模式）",
    "E009": "内部处理异常",
    "E010": "参数校验失败",
}


class SkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class MarkdownDocument:
    """解析后的 Markdown 文档结构"""
    raw_text: str
    title: str = ""
    headings: List[Dict[str, Any]] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    lists: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    blockquotes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化"""
        return {
            "title": self.title,
            "headings": self.headings,
            "paragraphs": self.paragraphs,
            "code_blocks": self.code_blocks,
            "lists": self.lists,
            "tables": self.tables,
            "links": self.links,
            "images": self.images,
            "blockquotes": self.blockquotes,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "char_count": len(self.raw_text),
        }


# ============================================================
# Markdown 解析器（核心逻辑）
# ============================================================
class MarkdownParser:
    """将 Markdown 文本解析为结构化文档"""

    # 常用正则表达式
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
    _CODE_FENCE_RE = re.compile(r'^(`{3,}|~{3,})\s*([\w+-]*)\s*$')
    _CODE_INLINE_RE = re.compile(r'`([^`]+)`')
    _LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    _IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    _LIST_ITEM_RE = re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.+)$')
    _BLOCKQUOTE_RE = re.compile(r'^>\s?(.*)$')
    _TABLE_ROW_RE = re.compile(r'^\|(.+)\|$')
    _TABLE_SEPARATOR_RE = re.compile(r'^[\s|:-]+$')
    _HORIZONTAL_RULE_RE = re.compile(r'^(-{3,}|\*{3,}|_{3,})$')

    def parse(self, text: str) -> MarkdownDocument:
        """解析 Markdown 文本为结构化文档"""
        if not text or not text.strip():
            raise SkillError("E001", "输入文本为空")

        doc = MarkdownDocument(raw_text=text)
        lines = text.split('\n')
        i = 0
        in_code_block = False
        code_block_lang = ""
        code_block_lines = []
        current_list = None
        current_list_indent = -1

        while i < len(lines):
            line = lines[i]
            
            # 处理代码块
            if not in_code_block:
                code_fence_match = self._CODE_FENCE_RE.match(line.strip())
                if code_fence_match:
                    in_code_block = True
                    code_block_lang = code_fence_match.group(2) or ""
                    code_block_lines = []
                    i += 1
                    continue
            else:
                code_fence_match = self._CODE_FENCE_RE.match(line.strip())
                if code_fence_match:
                    # 代码块结束
                    in_code_block = False
                    doc.code_blocks.append({
                        "language": code_block_lang,
                        "code": '\n'.join(code_block_lines)
                    })
                    code_block_lines = []
                    code_block_lang = ""
                    i += 1
                    continue
                else:
                    code_block_lines.append(line)
                    i += 1
                    continue

            # 跳过空行
            if not line.strip():
                if current_list is not None:
                    current_list = None
                    current_list_indent = -1
                i += 1
                continue

            # 处理标题
            heading_match = self._HEADING_RE.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                doc.headings.append({
                    "level": level,
                    "text": title_text,
                    "anchor": self._generate_anchor(title_text)
                })
                if level == 1 and not doc.title:
                    doc.title = title_text
                i += 1
                continue

            # 处理水平分割线
            if self._HORIZONTAL_RULE_RE.match(line.strip()):
                i += 1
                continue

            # 处理表格
            if self._TABLE_ROW_RE.match(line):
                table_result = self._parse_table(lines, i)
                if table_result:
                    table, new_i = table_result
                    doc.tables.append(table)
                    i = new_i
                    continue

            # 处理列表
            list_match = self._LIST_ITEM_RE.match(line)
            if list_match:
                indent = len(list_match.group(1)) if list_match.group(1) else 0
                if current_list is None or indent != current_list_indent:
                    current_list = {
                        "type": "ordered" if list_match.group(2).rstrip('.').isdigit() else "unordered",
                        "items": []
                    }
                    current_list_indent = indent
                    doc.lists.append(current_list)
                
                item_text = list_match.group(3).strip()
                current_list["items"].append(item_text)
                i += 1
                continue

            # 处理引用
            quote_match = self._BLOCKQUOTE_RE.match(line)
            if quote_match:
                doc.blockquotes.append(quote_match.group(1))
                i += 1
                continue

            # 处理内联代码、链接、图片
            processed_line = line
            
            # 提取图片
            for img_match in self._IMAGE_RE.finditer(processed_line):
                doc.images.append({
                    "alt": img_match.group(1),
                    "url": img_match.group(2)
                })
            
            # 提取链接
            for link_match in self._LINK_RE.finditer(processed_line):
                doc.links.append({
                    "text": link_match.group(1),
                    "url": link_match.group(2)
                })

            # 移除图片和链接标记，保留文本内容
            processed_line = self._IMAGE_RE.sub(r'\1', processed_line)
            processed_line = self._LINK_RE.sub(r'\1', processed_line)
            processed_line = self._CODE_INLINE_RE.sub(r'\1', processed_line)
            
            if processed_line.strip():
                doc.paragraphs.append(processed_line.strip())

            i += 1

        # 处理未闭合的代码块
        if in_code_block and code_block_lines:
            doc.code_blocks.append({
                "language": code_block_lang,
                "code": '\n'.join(code_block_lines)
            })
            doc.warnings.append("检测到未闭合的代码块，已自动处理")

        # 提取元数据（YAML front matter）
        doc.metadata = self._extract_metadata(text)
        
        # 计算置信度
        doc.confidence = self._calculate_confidence(doc)

        return doc

    def _generate_anchor(self, text: str) -> str:
        """生成标题锚点"""
        # 转换为小写，替换空格为连字符，移除特殊字符
        anchor = text.lower()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor

    def _parse_table(self, lines: List[str], start_idx: int) -> Optional[Tuple[Dict[str, Any], int]]:
        """解析表格"""
        if start_idx + 1 >= len(lines):
            return None

        header_line = lines[start_idx]
        separator_line = lines[start_idx + 1]

        # 检查第二行是否是分隔行
        if not self._TABLE_SEPARATOR_RE.match(separator_line.strip()):
            return None

        # 解析表头
        headers = [cell.strip() for cell in header_line.strip('|').split('|')]
        
        # 解析数据行
        rows = []
        i = start_idx + 2
        while i < len(lines) and self._TABLE_ROW_RE.match(lines[i]):
            row_cells = [cell.strip() for cell in lines[i].strip('|').split('|')]
            # 确保行长度与表头一致
            if len(row_cells) == len(headers):
                rows.append(row_cells)
            i += 1

        return {
            "headers": headers,
            "rows": rows
        }, i

    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """提取 YAML front matter 元数据"""
        metadata = {}
        lines = text.split('\n')
        
        if lines and lines[0].strip() == '---':
            i = 1
            while i < len(lines) and lines[i].strip() != '---':
                line = lines[i].strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
                i += 1

        return metadata

    def _calculate_confidence(self, doc: MarkdownDocument) -> float:
        """计算解析置信度"""
        confidence = 1.0
        
        # 如果有警告，降低置信度
        if doc.warnings:
            confidence -= 0.1 * len(doc.warnings)
        
        # 如果文档为空，置信度低
        if not doc.headings and not doc.paragraphs and not doc.code_blocks:
            confidence = 0.3
        
        return max(0.1, min(1.0, confidence))


# ============================================================
# 导出器
# ============================================================
class MarkdownExporter:
    """将解析后的 Markdown 文档导出为各种格式"""

    @staticmethod
    def to_json(doc: MarkdownDocument) -> str:
        """导出为 JSON"""
        return json.dumps(doc.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def to_html(doc: MarkdownDocument) -> str:
        """导出为 HTML"""
        html_parts = ['<!DOCTYPE html>', '<html>', '<head>', '<meta charset="UTF-8">']
        if doc.title:
            html_parts.append(f'<title>{html.escape(doc.title)}</title>')
        html_parts.extend(['</head>', '<body>'])

        # 标题
        for heading in doc.headings:
            level = heading['level']
            text = html.escape(heading['text'])
            html_parts.append(f'<h{level}>{text}</h{level}>')

        # 段落
        for para in doc.paragraphs:
            html_parts.append(f'<p>{html.escape(para)}</p>')

        # 代码块
        for code_block in doc.code_blocks:
            code = html.escape(code_block['code'])
            lang = html.escape(code_block['language']) if code_block['language'] else ''
            html_parts.append(f'<pre><code class="language-{lang}">{code}</code></pre>')

        # 列表
        for lst in doc.lists:
            tag = 'ol' if lst['type'] == 'ordered' else 'ul'
            html_parts.append(f'<{tag}>')
            for item in lst['items']:
                html_parts.append(f'<li>{html.escape(item)}</li>')
            html_parts.append(f'</{tag}>')

        # 表格
        for table in doc.tables:
            html_parts.append('<table>')
            html_parts.append('<thead><tr>')
            for header in table['headers']:
                html_parts.append(f'<th>{html.escape(header)}</th>')
            html_parts.append('</tr></thead>')
            html_parts.append('<tbody>')
            for row in table['rows']:
                html_parts.append('<tr>')
                for cell in row:
                    html_parts.append(f'<td>{html.escape(cell)}</td>')
                html_parts.append('</tr>')
            html_parts.append('</tbody></table>')

        # 引用
        for quote in doc.blockquotes:
            html_parts.append(f'<blockquote>{html.escape(quote)}</blockquote>')

        # 图片
        for img in doc.images:
            html_parts.append(f'<img src="{html.escape(img["url"])}" alt="{html.escape(img["alt"])}">')

        html_parts.extend(['</body>', '</html>'])
        return '\n'.join(html_parts)

    @staticmethod
    def to_csv(doc: MarkdownDocument) -> str:
        """导出为 CSV（表格数据）"""
        output = io.StringIO()
        writer = csv.writer(output)

        for table in doc.tables:
            writer.writerow(table['headers'])
            for row in table['rows']:
                writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def to_markdown(doc: MarkdownDocument) -> str:
        """导出为结构化 Markdown"""
        parts = []

        # 元数据
        if doc.metadata:
            parts.append('---')
            for key, value in doc.metadata.items():
                parts.append(f'{key}: {value}')
            parts.append('---')
            parts.append('')

        # 标题
        if doc.title:
            parts.append(f'# {doc.title}')
            parts.append('')

        # 段落
        for para in doc.paragraphs:
            parts.append(para)
            parts.append('')

        # 代码块
        for code_block in doc.code_blocks:
            lang = code_block['language'] or ''
            parts.append(f'
