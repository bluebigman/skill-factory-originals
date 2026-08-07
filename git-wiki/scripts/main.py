#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-wiki: 文档速建 Git 驱动 Wiki 引擎
=====================================
将零散文档快速转化为 Git 版本控制的轻量 Wiki 站点。

功能特性:
- 内容结构化: 解析 Markdown/纯文本为标题、段落、列表等
- 关键信息提取: 识别标题、日期、标签等元数据
- 格式规范化: 统一输出为 Markdown 语法
- 批量处理: 支持多个文件/目录输入
- 自定义输出: 可指定输出目录、命名规则、首页格式

用法示例:
    python main.py --input ./docs --output ./wiki
    python main.py --input file1.md file2.txt --output ./wiki
    python main.py --selftest

错误码:
    E001: 输入路径不存在
    E002: URL 不可访问
    E003: 文件编码不支持
    E004: 输出目录无写入权限
    E005: 批量处理中部分失败
    E006: 输入参数无效
    E007: 文件读取失败
    E008: 内容解析失败
    E009: 输出文件写入失败
    E010: 内部逻辑错误
"""

import argparse
import hashlib
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

DEFAULT_OUTPUT_DIR = "./wiki/"
DEFAULT_INDEX_NAME = "_index.md"
DEFAULT_SEPARATOR = "-"
GENERATED_MARK = "<!-- generated-by: git-wiki -->"
FRONTMATTER_DELIMITER = "---"
TITLE_PLACEHOLDER = "[需核实:标题]"
SUMMARY_MAX_LEN = 50  # 首页简介最大字符数

# 标题正则: 匹配 # 至 ######
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
# 双链正则: [[页面名]] 或 [[页面名|显示文本]]
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
# 普通 Markdown 链接: [文本](相对路径)
MD_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# YAML frontmatter 模式
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
# 非法文件名字符（Windows/Linux 通用保守集）
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


# ============================================================
# 数据模型
# ============================================================

class WikiPage:
    """单个 Wiki 页面数据模型"""
    
    def __init__(self, title: str = "", source: str = "", content: str = ""):
        self.title = title
        self.source = source
        self.content = content
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.tags: List[str] = []
        self.summary: str = ""
        self.filename: str = ""
        self.warnings: List[str] = []
    
    def to_markdown(self) -> str:
        """将页面数据序列化为 Markdown 文件内容"""
        lines = []
        # YAML frontmatter
        lines.append(FRONTMATTER_DELIMITER)
        lines.append(f"title: \"{self._escape_yaml(self.title)}\"")
        lines.append(f"source: \"{self._escape_yaml(self.source)}\"")
        lines.append(f"date: \"{self.date}\"")
        if self.tags:
            tags_str = ", ".join(f"\"{t}\"" for t in self.tags)
            lines.append(f"tags: [{tags_str}]")
        lines.append(FRONTMATTER_DELIMITER)
        lines.append("")
        # 正文内容
        lines.append(self.content)
        lines.append("")
        # 生成标记
        lines.append(GENERATED_MARK)
        return "\n".join(lines)
    
    @staticmethod
    def _escape_yaml(value: str) -> str:
        """转义 YAML 字符串中的特殊字符"""
        return value.replace("\\", "\\\\").replace("\"", "\\\"")


class ProcessingReport:
    """处理结果报告"""
    
    def __init__(self):
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.success_files: List[str] = []
        self.failed_files: List[str] = []
        self.skipped_files: List[str] = []
        self.warnings: List[str] = []
    
    def add_success(self, filename: str):
        self.success_count += 1
        self.success_files.append(filename)
    
    def add_failure(self, filename: str, reason: str = ""):
        self.failed_count += 1
        self.failed_files.append(f"{filename}" + (f" ({reason})" if reason else ""))
    
    def add_skipped(self, filename: str, reason: str = ""):
        self.skipped_count += 1
        self.skipped_files.append(f"{filename}" + (f" ({reason})" if reason else ""))
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def to_string(self) -> str:
        """生成报告文本"""
        lines = []
        lines.append("=" * 50)
        lines.append("处理报告")
        lines.append("=" * 50)
        lines.append(f"成功: {self.success_count} 个")
        lines.append(f"失败: {self.failed_count} 个")
        lines.append(f"跳过: {self.skipped_count} 个")
        
        if self.failed_files:
            lines.append("\n失败清单:")
            for f in self.failed_files:
                lines.append(f"  - {f}")
        
        if self.skipped_files:
            lines.append("\n跳过清单:")
            for f in self.skipped_files:
                lines.append(f"  - {f}")
        
        if self.warnings:
            lines.append("\n警告:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        
        lines.append("=" * 50)
        return "\n".join(lines)


# ============================================================
# 核心处理逻辑
# ============================================================

class WikiProcessor:
    """Wiki 处理核心引擎"""
    
    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR,
                 index_name: str = DEFAULT_INDEX_NAME,
                 separator: str = DEFAULT_SEPARATOR):
        self.output_dir = output_dir
        self.index_name = index_name
        self.separator = separator
        self.pages: List[WikiPage] = []
        self.report = ProcessingReport()
    
    def process_inputs(self, inputs: List[str]) -> ProcessingReport:
        """处理输入列表（文件/目录路径）"""
        if not inputs:
            raise ValueError("E006: 未提供任何输入源")
        
        for input_path in inputs:
            path = Path(input_path)
            if not path.exists():
                self.report.add_failure(str(path), "E001-路径不存在")
                continue
            
            if path.is_file():
                self._process_file(path)
            elif path.is_dir():
                self._process_directory(path)
            else:
                self.report.add_failure(str(path), "E001-不支持的路径类型")
        
        # 生成首页索引
        if self.pages:
            self._generate_index()
        
        return self.report
    
    def _process_directory(self, directory: Path):
        """处理目录下的所有文本文件"""
        try:
            files = sorted([f for f in directory.iterdir() if f.is_file()])
            for file in files:
                self._process_file(file)
        except PermissionError:
            self.report.add_failure(str(directory), "E004-目录无读取权限")
    
    def _process_file(self, file_path: Path):
        """处理单个文件"""
        # 跳过隐藏文件和非文本文件
        if file_path.name.startswith("."):
            self.report.add_skipped(str(file_path), "隐藏文件")
            return
        
        # 检查扩展名
        ext = file_path.suffix.lower()
        if ext not in (".md", ".markdown", ".txt", ".text", ""):
            self.report.add_skipped(str(file_path), f"不支持的扩展名 {ext}")
            return
        
        try:
            # 读取文件内容
            content = self._read_file(file_path)
            
            # 解析生成 Wiki 页面
            page = self._parse_content(content, str(file_path))
            
            # 生成文件名
            page.filename = self._generate_filename(page.title)
            
            # 写入输出文件
            self._write_page(page)
            
            self.pages.append(page)
            self.report.add_success(page.filename)
            
        except UnicodeDecodeError:
            self.report.add_failure(str(file_path), "E003-编码不支持，请转换为 UTF-8")
        except PermissionError:
            self.report.add_failure(str(file_path), "E004-无写入权限")
        except Exception as e:
            self.report.add_failure(str(file_path), f"E007-读取失败: {str(e)}")
    
    def _read_file(self, file_path: Path) -> str:
        """读取文件内容，尝试多种编码"""
        # 优先尝试 UTF-8
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # 尝试其他常见编码
            for encoding in ("gbk", "latin-1", "utf-16"):
                try:
                    return file_path.read_text(encoding=encoding)
                except (UnicodeDecodeError, UnicodeError):
                    continue
            raise UnicodeDecodeError("utf-8", file_path.read_bytes(), 0, 1, "无法解码")
    
    def _parse_content(self, content: str, source: str) -> WikiPage:
        """解析内容生成 WikiPage 对象"""
        page = WikiPage(source=source)
        
        # 提取 YAML frontmatter
        frontmatter_match = FRONTMATTER_PATTERN.match(content)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            fm_data = self._parse_frontmatter(fm_text)
            page.title = fm_data.get("title", "")
            page.date = fm_data.get("date", page.date)
            if "tags" in fm_data:
                page.tags = fm_data["tags"]
            # 移除 frontmatter
            content = content[frontmatter_match.end():]
        
        # 如果标题为空，从内容首行标题提取
        if not page.title:
            page.title = self._extract_title(content, source)
        
        # 提取摘要（正文首段前50字）
        page.summary = self._extract_summary(content)
        
        # 转换 Wiki 链接
        content = self._convert_wikilinks(content)
        
        # 清理内容（规范化空白等）
        content = self._clean_content(content)
        
        page.content = content
        return page
    
    def _parse_frontmatter(self, fm_text: str) -> Dict:
        """解析 YAML frontmatter"""
        data: Dict = {}
        for line in fm_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                if key == "tags":
                    # 解析标签列表
                    tags = value.strip("[]").split(",")
                    data[key] = [t.strip().strip("'\"") for t in tags if t.strip()]
                else:
                    data[key] = value
        return data
    
    def _extract_title(self, content: str, source: str) -> str:
        """从内容或文件名提取标题"""
        # 尝试从内容首行标题提取
        heading_match = HEADING_PATTERN.search(content)
        if heading_match:
            return heading_match.group(2).strip()
        
        # 从文件名提取
        filename = Path(source).stem
        if filename and filename != "README":
            # 清理文件名，去除日期前缀等
            cleaned = re.sub(r"^\d{4}-\d{2}-\d{2}-?", "", filename)
            cleaned = cleaned.replace("_", " ").replace("-", " ").strip()
            if cleaned:
                return cleaned
        
        # 无法确定标题
        return TITLE_PLACEHOLDER
    
    def _extract_summary(self, content: str) -> str:
        """提取内容摘要（首段前50字）"""
        # 移除代码块
        text = re.sub(r'
