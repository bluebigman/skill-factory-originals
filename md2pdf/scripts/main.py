#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2pdf - Markdown 转 PDF 转换器（clean-room 实现）

本脚本仅依据功能规格独立实现，用于将 Markdown 文本转换为
结构化的 PDF 文档（基于文本布局描述，不依赖外部库）。

主要功能：
1. 解析 Markdown 基础语法（标题、段落、列表、代码块、引用、粗体/斜体）
2. 生成 PDF 内容流（PDF 1.4 格式）
3. 提供 --selftest 离线自检模式

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 文件读取失败
    E007: 文件写入失败
    E008: 参数解析失败
    E009: 内部状态错误
    E010: 未支持的 Markdown 语法

依赖：仅 Python 标准库（无需 pip install）
"""

import argparse
import os
import re
import sys
import zlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与消息映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "文件写入失败，请检查输出路径和权限",
    "E008": "参数解析失败，请检查命令行参数",
    "E009": "内部状态错误，请报告开发者",
    "E010": "未支持的 Markdown 语法，请简化输入",
}

# PDF 页面尺寸（A4，单位：点，1pt = 1/72 英寸）
PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89
MARGIN_LEFT = 50.0
MARGIN_RIGHT = 50.0
MARGIN_TOP = 50.0
MARGIN_BOTTOM = 50.0
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

# 字体设置（PDF 标准字体）
FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"
FONT_SIZE_BODY = 10.0
FONT_SIZE_H1 = 20.0
FONT_SIZE_H2 = 16.0
FONT_SIZE_H3 = 13.0
LINE_HEIGHT_BODY = 14.0
LINE_HEIGHT_HEADING = 1.5  # 相对于字体大小的倍数


# ============================================================
# 数据结构
# ============================================================

class MarkdownElement:
    """Markdown 解析后的元素基类"""
    def __init__(self, element_type: str, content: str, level: int = 0):
        self.element_type = element_type  # heading / paragraph / list / code / quote
        self.content = content
        self.level = level  # 标题级别或列表层级


class PDFDocument:
    """PDF 文档构建器（文本布局描述）"""
    
    def __init__(self):
        self.objects: List[bytes] = []
        self.pages: List[List[Tuple[float, float, str, str, float]]] = []
        self.current_page: List[Tuple[float, float, str, str, float]] = []
        self.current_y: float = PAGE_HEIGHT - MARGIN_TOP
        
    def _add_object(self, data: bytes) -> int:
        """添加对象并返回对象编号"""
        self.objects.append(data)
        return len(self.objects)
    
    def add_text(self, x: float, y: float, text: str, font: str = FONT_NAME, size: float = FONT_SIZE_BODY) -> None:
        """添加文本到当前页面"""
        # 检查是否需要换页
        if y < MARGIN_BOTTOM + LINE_HEIGHT_BODY:
            self._new_page()
            y = self.current_y
        self.current_page.append((x, y, text, font, size))
        self.current_y = y - LINE_HEIGHT_BODY
    
    def _new_page(self) -> None:
        """创建新页面"""
        if self.current_page:
            self.pages.append(self.current_page)
        self.current_page = []
        self.current_y = PAGE_HEIGHT - MARGIN_TOP
    
    def _build_page_content(self, page_items: List[Tuple[float, float, str, str, float]]) -> bytes:
        """构建页面内容流"""
        content_parts = ["BT"]
        for x, y, text, font, size in page_items:
            # 转义 PDF 特殊字符
            escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content_parts.append(f"/{font} {size:.1f} Tf")
            content_parts.append(f"1 0 0 1 {x:.1f} {y:.1f} Tm")
            content_parts.append(f"({escaped_text}) Tj")
        content_parts.append("ET")
        content = "\n".join(content_parts).encode("latin-1", errors="replace")
        return zlib.compress(content)
    
    def build(self) -> bytes:
        """构建完整 PDF 文件"""
        # 完成最后一页
        if self.current_page:
            self.pages.append(self.current_page)
        
        # 构建对象
        object_map: List[Tuple[int, int]] = []  # (对象编号, 偏移量)
        pdf_parts = ["%PDF-1.4"]
        
        # 辅助函数：添加对象
        def add_obj(data: bytes) -> int:
            obj_num = len(object_map) + 1
            object_map.append((obj_num, 0))  # 偏移量稍后填充
            pdf_parts.append(f"{obj_num} 0 obj")
            pdf_parts.append(data.decode("latin-1", errors="replace"))
            pdf_parts.append("endobj")
            return obj_num
        
        # 1. 目录对象
        catalog_data = "<< /Type /Catalog /Pages 2 0 R >>"
        add_obj(catalog_data.encode("latin-1"))
        
        # 2. 页面树对象
        page_count = len(self.pages)
        page_refs = " ".join([f"{i+3} 0 R" for i in range(page_count)])
        pages_data = f"<< /Type /Pages /Kids [{page_refs}] /Count {page_count} >>"
        add_obj(pages_data.encode("latin-1"))
        
        # 3. 页面对象
        page_obj_nums = []
        for page_items in self.pages:
            content = self._build_page_content(page_items)
            content_obj_num = len(object_map) + 1 + len(page_obj_nums) * 2
            # 内容流对象
            content_ref = content_obj_num
            # 页面对象
            page_data = (
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH:.1f} {PAGE_HEIGHT:.1f}] "
                f"/Resources << /Font << /{FONT_NAME} {content_obj_num+1} 0 R "
                f"/{FONT_NAME_BOLD} {content_obj_num+2} 0 R >> >> "
                f"/Contents {content_ref} 0 R >>"
            )
            page_obj_num = add_obj(page_data.encode("latin-1"))
            page_obj_nums.append(page_obj_num)
            # 内容流对象
            add_obj(content)
            # 字体对象
            font_data = f"<< /Type /Font /Subtype /Type1 /BaseFont /{FONT_NAME} >>"
            add_obj(font_data.encode("latin-1"))
            font_bold_data = f"<< /Type /Font /Subtype /Type1 /BaseFont /{FONT_NAME_BOLD} >>"
            add_obj(font_bold_data.encode("latin-1"))
        
        # 计算 xref 表
        xref_offset = 0
        pdf_content = "\n".join(pdf_parts).encode("latin-1", errors="replace")
        
        # 由于我们动态构建，需要重新计算偏移量
        # 简化处理：使用流式构建
        final_parts = []
        current_offset = 0
        xref_entries = []
        
        final_parts.append(b"%PDF-1.4\n")
        current_offset += len(b"%PDF-1.4\n")
        
        # 重新构建对象
        obj_num = 1
        for data in [catalog_data.encode("latin-1"), pages_data.encode("latin-1")]:
            xref_entries.append((obj_num, current_offset))
            obj_str = f"{obj_num} 0 obj\n".encode("latin-1")
            final_parts.append(obj_str)
            current_offset += len(obj_str)
            final_parts.append(data + b"\n")
            current_offset += len(data) + 1
            final_parts.append(b"endobj\n")
            current_offset += len(b"endobj\n")
            obj_num += 1
        
        # 页面对象和内容流
        for i, page_items in enumerate(self.pages):
            content = self._build_page_content(page_items)
            content_obj_num = obj_num + 1
            font_obj_num = content_obj_num + 1
            font_bold_obj_num = content_obj_num + 2
            
            # 页面对象
            page_data = (
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH:.1f} {PAGE_HEIGHT:.1f}] "
                f"/Resources << /Font << /{FONT_NAME} {font_obj_num} 0 R "
                f"/{FONT_NAME_BOLD} {font_bold_obj_num} 0 R >> >> "
                f"/Contents {content_obj_num} 0 R >>"
            ).encode("latin-1")
            xref_entries.append((obj_num, current_offset))
            obj_str = f"{obj_num} 0 obj\n".encode("latin-1")
            final_parts.append(obj_str)
            current_offset += len(obj_str)
            final_parts.append(page_data + b"\n")
            current_offset += len(page_data) + 1
            final_parts.append(b"endobj\n")
            current_offset += len(b"endobj\n")
            obj_num += 1
            
            # 内容流对象
            xref_entries.append((obj_num, current_offset))
            obj_str = f"{obj_num} 0 obj\n".encode("latin-1")
            final_parts.append(obj_str)
            current_offset += len(obj_str)
            final_parts.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n")
            current_offset += len(b"<< /Length ") + len(str(len(content)).encode()) + len(b" >>\nstream\n")
            final_parts.append(content + b"\nendstream\n")
            current_offset += len(content) + len(b"\nendstream\n")
            final_parts.append(b"endobj\n")
            current_offset += len(b"endobj\n")
            obj_num += 1
            
            # 字体对象
            for font_data in [
                f"<< /Type /Font /Subtype /Type1 /BaseFont /{FONT_NAME} >>".encode("latin-1"),
                f"<< /Type /Font /Subtype /Type1 /BaseFont /{FONT_NAME_BOLD} >>".encode("latin-1")
            ]:
                xref_entries.append((obj_num, current_offset))
                obj_str = f"{obj_num} 0 obj\n".encode("latin-1")
                final_parts.append(obj_str)
                current_offset += len(obj_str)
                final_parts.append(font_data + b"\n")
                current_offset += len(font_data) + 1
                final_parts.append(b"endobj\n")
                current_offset += len(b"endobj\n")
                obj_num += 1
        
        # xref 表
        xref_offset = current_offset
        xref_table = f"xref\n0 {obj_num+1}\n".encode("latin-1")
        final_parts.append(xref_table)
        current_offset += len(xref_table)
        
        final_parts.append(b"0000000000 65535 f \n")
        current_offset += len(b"0000000000 65535 f \n")
        
        for _, offset in xref_entries:
            entry = f"{offset:010d} 00000 n \n".encode("latin-1")
            final_parts.append(entry)
            current_offset += len(entry)
        
        # trailer
        trailer = f"trailer\n<< /Size {obj_num+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
        final_parts.append(trailer)
        
        return b"".join(final_parts)


# ============================================================
# Markdown 解析器
# ============================================================

class MarkdownParser:
    """Markdown 文本解析器"""
    
    def __init__(self, text: str):
        self.text = text
        self.lines = text.split("\n")
        self.elements: List[MarkdownElement] = []
    
    def parse(self) -> List[MarkdownElement]:
        """解析 Markdown 文本为元素列表"""
        if not self.text.strip():
            raise ValueError("E001")
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.strip()
            
            # 空行跳过
            if not stripped:
                i += 1
                continue
            
            # 标题
            heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2).strip()
                self.elements.append(MarkdownElement("heading", content, level))
                i += 1
                continue
            
            # 代码块
            if stripped.startswith("
