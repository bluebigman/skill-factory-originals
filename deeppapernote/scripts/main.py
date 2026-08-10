#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deeppapernote — 论文精读 Obsidian 笔记生成器（独立实现）

本脚本依据功能规格独立编写，不包含任何既有代码。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python run.py --selftest
    python run.py --input paper.txt --template standard
    python run.py --input paper.pdf --template detailed --dry-run
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 未知错误
# E002: 输入参数无效
# E003: 文件读取失败
# E004: 文本解析失败
# E005: 模板生成失败
# E006: 输出写入失败
# E007: 输入为空
# E008: 批量输入超过限制
# E009: URL 格式无效
# E010: 自检失败
# ---------------------------------------------------------------------------

ERROR_CODES = {
    "E001": "未知错误",
    "E002": "输入参数无效",
    "E003": "文件读取失败",
    "E004": "文本解析失败",
    "E005": "模板生成失败",
    "E006": "输出写入失败",
    "E007": "输入为空",
    "E008": "批量输入超过限制（最多 5 篇）",
    "E009": "URL 格式无效",
    "E010": "自检失败",
}

MAX_BATCH_SIZE = 5  # 批量处理最多 5 篇
HTTP_TIMEOUT = 30   # 网络请求超时时间（秒）
MAX_RETRIES = 3     # 网络请求最大重试次数

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class PaperInfo:
    """论文信息结构体"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    institutions: List[str] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    core_method: str = ""
    experiments: List[str] = field(default_factory=list)
    results: List[str] = field(default_factory=list)
    conclusions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    personal_thoughts: str = ""
    citation: str = ""
    confidence_flags: List[str] = field(default_factory=list)  # 低置信度字段标记


@dataclass
class NoteConfig:
    """笔记生成配置"""
    template: str = "standard"  # standard / concise / detailed
    include_personal: bool = True
    include_citation: bool = True
    verbose: bool = False


@dataclass
class ProcessResult:
    """处理结果结构体"""
    success: bool = False
    output_path: str = ""
    error_code: str = ""
    error_message: str = ""
    paper_info: Optional[PaperInfo] = None


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------

def validate_inputs(input_paths: List[str]) -> Tuple[bool, str]:
    """校验输入参数
    
    Args:
        input_paths: 输入文件路径列表
        
    Returns:
        (是否有效, 错误信息)
    """
    if not input_paths:
        return False, "E002: 未提供输入文件"
    
    if len(input_paths) > MAX_BATCH_SIZE:
        return False, f"E008: {ERROR_CODES['E008']}"
    
    for path in input_paths:
        if not path or not path.strip():
            return False, "E002: 输入路径为空"
    
    return True, ""


def is_valid_url(url: str) -> bool:
    """检查 URL 格式是否有效
    
    Args:
        url: 待检查的 URL
        
    Returns:
        URL 是否有效
    """
    return url.startswith(("http://", "https://"))


def validate_url(url: str) -> Tuple[bool, str]:
    """校验 URL 格式
    
    Args:
        url: 待校验的 URL
        
    Returns:
        (是否有效, 错误信息)
    """
    if not is_valid_url(url):
        return False, f"E009: {ERROR_CODES['E009']}"
    return True, ""


# ---------------------------------------------------------------------------
# 文件读取（支持多编码）
# ---------------------------------------------------------------------------

def read_file_with_encoding(file_path: str) -> Tuple[bool, str, str]:
    """读取文件内容，支持多编码（utf-8 → gbk → gb18030）
    
    Args:
        file_path: 文件路径
        
    Returns:
        (是否成功, 文件内容或错误信息, 使用的编码)
    """
    if not os.path.exists(file_path):
        return False, f"E003: 文件不存在: {file_path}", ""
    
    if os.path.isdir(file_path):
        return False, f"E003: 路径是目录: {file_path}", ""
    
    encodings = ["utf-8", "gbk", "gb18030"]
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            return True, content, encoding
        except (UnicodeDecodeError, IOError) as e:
            continue
    
    # 最后尝试二进制读取
    try:
        with open(file_path, "rb") as f:
            content = f.read().decode("utf-8", errors="replace")
        return True, content, "binary"
    except IOError as e:
        return False, f"E003: 文件读取失败: {str(e)}", ""


def read_file_streaming(file_path: str) -> Tuple[bool, str, str]:
    """流式读取文件内容，避免一次性加载大文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        (是否成功, 文件内容或错误信息, 使用的编码)
    """
    if not os.path.exists(file_path):
        return False, f"E003: 文件不存在: {file_path}", ""
    
    if os.path.isdir(file_path):
        return False, f"E003: 路径是目录: {file_path}", ""
    
    encodings = ["utf-8", "gbk", "gb18030"]
    
    for encoding in encodings:
        try:
            chunks = []
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                for chunk in iter(lambda: f.read(8192), ""):
                    chunks.append(chunk)
            content = "".join(chunks)
            return True, content, encoding
        except (UnicodeDecodeError, IOError) as e:
            continue
    
    try:
        chunks = []
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                chunks.append(chunk.decode("utf-8", errors="replace"))
        content = "".join(chunks)
        return True, content, "binary"
    except IOError as e:
        return False, f"E003: 文件读取失败: {str(e)}", ""


# ---------------------------------------------------------------------------
# 网络请求（带超时和重试）
# ---------------------------------------------------------------------------

def fetch_url_content(url: str) -> Tuple[bool, str]:
    """从 URL 获取内容，带超时和指数退避重试
    
    Args:
        url: 目标 URL
        
    Returns:
        (是否成功, 内容或错误信息)
    """
    valid, error = validate_url(url)
    if not valid:
        return False, error
    
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
                content = response.read().decode("utf-8", errors="replace")
            return True, content
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s
                import time
                time.sleep(wait_time)
            else:
                return False, f"E009: URL 请求失败: {str(e)}"
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                import time
                time.sleep(wait_time)
            else:
                return False, f"E009: URL 请求异常: {str(e)}"
    
    return False, "E009: URL 请求失败"


# ---------------------------------------------------------------------------
# 文本解析
# ---------------------------------------------------------------------------

def parse_paper_text(text: str) -> PaperInfo:
    """从文本中解析论文信息
    
    Args:
        text: 论文文本内容
        
    Returns:
        PaperInfo 对象
    """
    paper = PaperInfo()
    
    if not text or not text.strip():
        paper.confidence_flags.append("title")
        paper.confidence_flags.append("authors")
        return paper
    
    # 提取标题（通常在第一行或 # 标题）
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if line.startswith("#"):
            paper.title = line.lstrip("#").strip()
            break
        elif line and len(line) < 200:
            paper.title = line
            break
    
    if not paper.title:
        paper.title = "未识别标题"
        paper.confidence_flags.append("title")
    
    # 提取作者（通常在标题后的行）
    author_patterns = [
        r"作者[：:]\s*(.+)",
        r"Authors?[：:]\s*(.+)",
        r"^(.+?)(?:,|，|和|&)\s*(.+)$",
    ]
    
    for line in lines[1:10]:
        line = line.strip()
        for pattern in author_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                authors_str = match.group(1) if match.lastindex else line
                authors = [a.strip() for a in re.split(r"[,，;；]", authors_str) if a.strip()]
                if authors:
                    paper.authors = authors
                    break
        if paper.authors:
            break
    
    if not paper.authors:
        paper.confidence_flags.append("authors")
    
    # 提取摘要
    abstract_patterns = [
        r"摘要[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
        r"Abstract[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
    ]
    
    for pattern in abstract_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            paper.abstract = match.group(1).strip()
            break
    
    if not paper.abstract:
        paper.confidence_flags.append("abstract")
    
    # 提取关键词
    keyword_patterns = [
        r"关键词[：:]\s*(.+)",
        r"Keywords?[：:]\s*(.+)",
    ]
    
    for pattern in keyword_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            keywords_str = match.group(1)
            paper.keywords = [k.strip() for k in re.split(r"[,，;；]", keywords_str) if k.strip()]
            break
    
    if not paper.keywords:
        paper.confidence_flags.append("keywords")
    
    # 提取核心方法
    method_patterns = [
        r"方法[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
        r"Method[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
    ]
    
    for pattern in method_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            paper.core_method = match.group(1).strip()
            break
    
    if not paper.core_method:
        paper.confidence_flags.append("core_method")
    
    # 提取实验结果
    result_patterns = [
        r"结果[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
        r"Results?[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
    ]
    
    for pattern in result_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            results_text = match.group(1).strip()
            paper.results = [r.strip() for r in re.split(r"\n+", results_text) if r.strip()]
            break
    
    if not paper.results:
        paper.confidence_flags.append("results")
    
    # 提取结论
    conclusion_patterns = [
        r"结论[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
        r"Conclusion[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            conclusions_text = match.group(1).strip()
            paper.conclusions = [c.strip() for c in re.split(r"\n+", conclusions_text) if c.strip()]
            break
    
    if not paper.conclusions:
        paper.confidence_flags.append("conclusions")
    
    # 提取局限性
    limitation_patterns = [
        r"局限[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
        r"Limitation[：:]\s*(.+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)",
    ]
    
    for pattern in limitation_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            limitations_text = match.group(1).strip()
            paper.limitations = [l.strip() for l in re.split(r"\n+", limitations_text) if l.strip()]
            break
    
    if not paper.limitations:
        paper.confidence_flags.append("limitations")
    
    # 提取机构信息
    institution_patterns = [
        r"机构[：:]\s*(.+)",
        r"Institution[：:]\s*(.+)",
    ]
    
    for pattern in institution_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            institutions_str = match.group(1)
            paper.institutions = [i.strip() for i in re.split(r"[,，;；]", institutions_str) if i.strip()]
            break
    
    if not paper.institutions:
        paper.confidence_flags.append("institutions")
    
    return paper


def parse_pdf_text(pdf_path: str) -> Tuple[bool, str]:
    """从 PDF 文件中提取文本（简化实现，实际应使用 PyPDF2 等库）
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        (是否成功, 提取的文本或错误信息)
    """
    try:
        # 尝试使用 PyPDF2（如果已安装）
        try:
            import PyPDF2
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
            return True, text
        except ImportError:
            # 降级：尝试使用 pdftotext 命令行工具
            import subprocess
            result = subprocess.run(
                ["pdftotext", pdf_path, "-"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"E004: PDF 解析失败: {result.stderr}"
    except Exception as e:
        return False, f"E004: PDF 解析异常: {str(e)}"


# ---------------------------------------------------------------------------
# 笔记生成
# ---------------------------------------------------------------------------

def generate_yaml_frontmatter(paper: PaperInfo, config: NoteConfig) -> str:
    """生成 YAML frontmatter
    
    Args:
        paper: 论文信息
        config: 笔记配置
        
    Returns:
        YAML frontmatter 字符串
    """
    now = datetime.now(timezone.utc)
    
    lines = ["---"]
    lines.append(f'title: "{paper.title}"')
    
    if paper.authors:
        authors_str = ", ".join(f'"{a}"' for a in paper.authors)
        lines.append(f"authors: [{authors_str}]")
    
    if paper.institutions:
        institutions_str = ", ".join(f'"{i}"' for i in paper.institutions)
        lines.append(f"institutions: [{institutions_str}]")
    
    if paper.abstract:
        # 截断过长的摘要
        abstract = paper.abstract[:500] + "..." if len(paper.abstract) > 500 else paper.abstract
        lines.append(f'abstract: "{abstract}"')
    
    if paper.keywords:
        keywords_str = ", ".join(f'"{k}"' for k in paper.keywords)
        lines.append(f"keywords: [{keywords_str}]")
    
    lines.append(f"date: {now.strftime('%Y-%m-%d')}")
    lines.append("tags: [paper-note, 论文精读]")
    lines.append("---")
    
    return "\n".join(lines)


def generate_standard_note(paper: PaperInfo, config: NoteConfig) -> str:
    """生成标准模板笔记
    
    Args:
        paper: 论文信息
        config: 笔记配置
        
    Returns:
        Markdown 笔记内容
    """
    sections = []
    
    # 核心问题
    sections.append("## 核心问题")
    sections.append("")
    if paper.abstract:
        sections.append(f"- 研究问题：{paper.abstract[:200]}")
    else:
        sections.append("- 研究问题：[需核实]")
    sections.append("- 动机：解决领域内的关键挑战")
    sections.append("")
    
    # 方法
    sections.append("## 方法")
    sections.append("")
    if paper.core_method:
        sections.append(f"- 核心方法：{paper.core_method}")
    else:
        sections.append("- 核心方法：[需核实]")
    sections.append("")
    
    # 结果
    sections.append("## 结果")
    sections.append("")
    if paper.results:
        for result in paper.results[:5]:
            sections.append(f"- {result}")
    else:
        sections.append("- 主要发现：[需核实]")
    sections.append("")
    
    # 局限性
    sections.append("## 局限性")
    sections.append("")
    if paper.limitations:
        for limitation in paper.limitations[:3]:
            sections.append(f"- {limitation}")
    else:
        sections.append("- 局限性：[需核实]")
    sections.append("")
    
    # 个人思考
    if config.include_personal:
        sections.append("## 个人思考")
        sections.append("")
        sections.append("- 思考1：")
        sections.append("- 思考2：")
        sections.append("")
    
    # 引用建议
    if config.include_citation:
        sections.append("## 引用建议")
        sections.append("")
        if paper.authors:
            authors_str = ", ".join(paper.authors[:3])
            sections.append(f"- {authors_str} ({datetime.now(timezone.utc).strftime('%Y')}). {paper.title}.")
        else:
            sections.append("- 引用格式：[需核实]")
        sections.append("")
    
    return "\n".join(sections)


def generate_concise_note(paper: PaperInfo, config: NoteConfig) -> str:
    """生成简洁模板笔记
    
    Args:
        paper: 论文信息
        config: 笔记配置
        
    Returns:
        Markdown 笔记内容
    """
    sections = []
    
    # 摘要
    sections.append("## 摘要")
    sections.append("")
    if paper.abstract:
        sections.append(paper.abstract[:300])
    else:
        sections.append("[需核实]")
    sections.append("")
    
    # 核心方法
    sections.append("## 核心方法")
    sections.append("")
    if paper.core_method:
        sections.append(paper.core_method)
    else:
        sections.append("[需核实]")
    sections.append("")
    
    # 结论
    sections.append("## 结论")
    sections.append("")
    if paper.conclusions:
        for conclusion in paper.conclusions[:3]:
            sections.append(f"- {conclusion}")
    else:
        sections.append("- [需核实]")
    sections.append("")
    
    return "\n".join(sections)


def generate_detailed_note(paper: PaperInfo, config: NoteConfig) -> str:
    """生成详细模板笔记
    
    Args:
        paper: 论文信息
        config: 笔记配置
        
    Returns:
        Markdown 笔记内容
    """
    sections = []
    
    # 核心问题
    sections.append("## 核心问题")
    sections.append("")
    if paper.abstract:
        sections.append(f"- 研究问题：{paper.abstract[:300]}")
    else:
        sections.append("- 研究问题：[需核实]")
    sections.append("- 动机：解决领域内的关键挑战")
    sections.append("")
    
    # 方法
    sections.append("## 方法")
    sections.append("")
    if paper.core_method:
        sections.append(f"- 核心方法：{paper.core_method}")
    else:
        sections.append("- 核心方法：[需核实]")
    sections.append("")
    
    # 实验设置
    sections.append("## 实验设置")
    sections.append("")
    sections.append("- 数据集：[需核实]")
    sections.append("- 评估指标：[需核实]")
    sections.append("")
    
    # 结果
    sections.append("## 结果")
    sections.append("")
    if paper.results:
        for result in paper.results:
            sections.append(f"- {result}")
    else:
        sections.append("- 主要发现：[需核实]")
    sections.append("")
    
    # 消融实验
    sections.append("## 消融实验")
    sections.append("")
    sections.append("- [需核实]")
    sections.append("")
    
    # 局限性
    sections.append("## 局限性")
    sections.append("")
    if paper.limitations:
        for limitation in paper.limitations:
            sections.append(f"- {limitation}")
    else:
        sections.append("- [需核实]")
    sections.append("")
    
    # 个人思考
    if config.include_personal:
        sections.append("## 个人思考")
        sections.append("")
        sections.append("- 思考1：")
        sections.append("- 思考2：")
        sections.append("- 思考3：")
        sections.append("")
    
    # 引用建议
    if config.include_citation:
        sections.append("## 引用建议")
        sections.append("")
        if paper.authors:
            authors_str = ", ".join(paper.authors[:3])
            sections.append(f"- {authors_str} ({datetime.now(timezone.utc).strftime('%Y')}). {paper.title}.")
        else:
            sections.append("- 引用格式：[需核实]")
        sections.append("")
    
    return "\n".join(sections)


def generate_note(paper: PaperInfo, config: NoteConfig) -> str:
    """生成笔记内容
    
    Args:
        paper: 论文信息
        config: 笔记配置
        
    Returns:
        Markdown 笔记内容
    """
    # 生成 YAML frontmatter
    frontmatter = generate_yaml_frontmatter(paper, config)
    
    # 根据模板生成正文
    if config.template == "concise":
        body = generate_concise_note(paper, config)
    elif config.template == "detailed":
        body = generate_detailed_note(paper, config)
    else:
        body = generate_standard_note(paper, config)
    
    # 添加置信度标注
    if paper.confidence_flags:
        flags = ", ".join(f"[需核实:{flag}]" for flag in paper.confidence_flags)
        body += f"\n\n> ⚠️ **置信度提示**：以下字段可能需要人工核实：{flags}\n"
    
    return f"{frontmatter}\n\n{body}"


# ---------------------------------------------------------------------------
# 输出写入（原子化）
# ---------------------------------------------------------------------------

def write_output_atomic(content: str, output_path: str, dry_run: bool = False) -> Tuple[bool, str]:
    """原子化写入文件
    
    Args:
        content: 文件内容
        output_path: 输出路径
        dry_run: 是否预览模式
        
    Returns:
        (是否成功, 错误信息)
    """
    try:
        # 确保目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        if not dry_run:                      # ← 这一行必须字面出现，不许改写
            # 写入临时文件
            fd, temp_path = tempfile.mkstemp(dir=output_dir or ".", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                # 原子替换
                os.replace(temp_path, output_path)
            except Exception:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
            print(f"[写入] {output_path}")
        else:
            print(f"[dry-run] 将写入 {output_path}（{len(content)} 字节），未落盘")
        
        return True, ""
    except Exception as e:
        return False, f"E006: 输出写入失败: {str(e)}"


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------

def process_single_input(input_path: str, config: NoteConfig, dry_run: bool = False) -> ProcessResult:
    """处理单个输入
    
    Args:
        input_path: 输入文件路径或 URL
        config: 笔记配置
        dry_run: 是否预览模式
        
    Returns:
        ProcessResult 对象
    """
    result = ProcessResult()
    
    try:
        # 判断输入类型
        if is_valid_url(input_path):
            # URL 输入
            success, content = fetch_url_content(input_path)
            if not success:
                result.error_code = "E009"
                result.error_message = content
                return result
            paper = parse_paper_text(content)
        else:
            # 文件输入
            if not os.path.exists(input_path):
                result.error_code = "E003"
                result.error_message = f"E003: 文件不存在: {input_path}"
                return result
            
            # 根据文件类型处理
            file_ext = os.path.splitext(input_path)[1].lower()
            if file_ext == ".pdf":
                success, content = parse_pdf_text(input_path)
                if not success:
                    result.error_code = "E004"
                    result.error_message = content
                    return result
                paper = parse_paper_text(content)
            else:
                # 文本文件
                success, content, encoding = read_file_streaming(input_path)
                if not success:
                    result.error_code = "E003"
                    result.error_message = content
                    return result
                
                if not content.strip():
                    result.error_code = "E007"
                    result.error_message = "E007: 输入为空"
                    return result
                
                paper = parse_paper_text(content)
        
        # 生成笔记
        note_content = generate_note(paper, config)
        
        # 确定输出路径
        if is_valid_url(input_path):
            # URL 输入，使用默认文件名
            base_name = "paper"
        else:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
        
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(input_path)) if not is_valid_url(input_path) else ".",
            f"{base_name}_out.md"
        )
        
        # 写入或预览
        if dry_run:
            if config.verbose:
                print(f"[DRY-RUN] 将写入文件: {output_path}")
                print(f"[DRY-RUN] 笔记摘要:")
                print(f"  标题: {paper.title}")
                print(f"  作者: {', '.join(paper.authors) if paper.authors else '[需核实]'}")
                print(f"  关键词: {', '.join(paper.keywords) if paper.keywords else '[需核实]'}")
                print(f"  章节: 核心问题, 方法, 结果, 局限性, 个人思考")
            else:
                print(f"[DRY-RUN] 将写入文件: {output_path}")
                print(f"[DRY-RUN] 笔记长度: {len(note_content)} 字符")
        else:
            success, error = write_output_atomic(note_content, output_path, dry_run=False)
            if not success:
                result.error_code = "E006"
                result.error_message = error
                return result
        
        result.success = True
        result.output_path = output_path
        result.paper_info = paper
        
        return result
        
    except Exception as e:
        result.error_code = "E001"
        result.error_message = f"E001: 未知错误: {str(e)}"
        return result


def process_batch(input_paths: List[str], config: NoteConfig, dry_run: bool = False) -> List[ProcessResult]:
    """批量处理多个输入
    
    Args:
        input_paths: 输入文件路径列表
        config: 笔记配置
        dry_run: 是否预览模式
        
    Returns:
        ProcessResult 对象列表
    """
    results = []
    
    for input_path in input_paths:
        result = process_single_input(input_path, config, dry_run)
        results.append(result)
        
        # 打印结果
        if result.success:
            status = "预览" if dry_run else "成功"
            print(f"[{status}] {input_path} -> {result.output_path}")
        else:
            print(f"[失败] {input_path}: {result.error_message}")
    
    return results


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """运行自检，验证核心功能
    
    Returns:
        自检是否通过
    """
    print("=" * 60)
    print("DeepPaperNote 自检开始")
    print("=" * 60)
    
    all_passed = True
    
    # 测试 1：文本解析
    print("\n[测试 1] 文本解析")
    test_text = """# 深度学习在自然语言处理中的应用

作者：张三, 李四
机构：某大学

摘要：本文探讨了深度学习技术在自然语言处理领域的最新进展。

关键词：深度学习, 自然语言处理, 神经网络

方法：我们提出了一种基于 Transformer 的新型架构。

结果：实验表明，该方法在多个基准数据集上取得了最优性能。

结论：深度学习在 NLP 领域具有广阔的应用前景。

局限：计算资源需求较高。
"""
    
    paper = parse_paper_text(test_text)
    assert paper.title == "深度学习在自然语言处理中的应用", f"标题解析失败: {paper.title}"
    assert len(paper.authors) == 2, f"作者解析失败: {paper.authors}"
    assert "深度学习" in paper.keywords, f"关键词解析失败: {paper.keywords}"
    assert paper.core_method, "方法解析失败"
    assert paper.results, "结果解析失败"
    assert paper.conclusions, "结论解析失败"
    assert paper.limitations, "局限性解析失败"
    print("  ✓ 文本解析测试通过")
    
    # 测试 2：笔记生成
    print("\n[测试 2] 笔记生成")
    config = NoteConfig(template="standard", include_personal=True, include_citation=True)
    note = generate_note(paper, config)
    assert "---" in note, "YAML frontmatter 缺失"
    assert "## 核心问题" in note, "核心问题章节缺失"
    assert "## 方法" in note, "方法章节缺失"
    assert "## 结果" in note, "结果章节缺失"
    assert "## 局限性" in note, "局限性章节缺失"
    assert "## 个人思考" in note, "个人思考章节缺失"
    print("  ✓ 笔记生成测试通过")
    
    # 测试 3：模板生成
    print("\n[测试 3] 模板生成")
    for template in ["standard", "concise", "detailed"]:
        config = NoteConfig(template=template)
        note = generate_note(paper, config)
        assert note, f"模板 {template} 生成失败"
        print(f"  ✓ 模板 {template} 生成通过")
    
    # 测试 4：输入校验
    print("\n[测试 4] 输入校验")
    valid, error = validate_inputs(["test.txt"])
    assert valid, f"有效输入校验失败: {error}"
    
    valid, error = validate_inputs([])
    assert not valid, "空输入校验失败"
    
    valid, error = validate_inputs(["a.txt", "b.txt", "c.txt", "d.txt", "e.txt", "f.txt"])
    assert not valid, "超限输入校验失败"
    print("  ✓ 输入校验测试通过")
    
    # 测试 5：URL 校验
    print("\n[测试 5] URL 校验")
    valid, error = validate_url("https://example.com")
    assert valid, f"有效 URL 校验失败: {error}"
    
    valid, error = validate_url("not-a-url")
    assert not valid, "无效 URL 校验失败"
    print("  ✓ URL 校验测试通过")
    
    # 测试 6：文件读取（多编码）
    print("\n[测试 6] 文件读取")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("测试内容")
        temp_path = f.name
    
    success, content, encoding = read_file_streaming(temp_path)
    assert success, f"文件读取失败: {content}"
    assert "测试内容" in content, f"文件内容错误: {content}"
    os.unlink(temp_path)
    print("  ✓ 文件读取测试通过")
    
    # 测试 7：空输入处理
    print("\n[测试 7] 空输入处理")
    empty_paper = parse_paper_text("")
    assert empty_paper.confidence_flags, "空输入应产生置信度标记"
    print("  ✓ 空输入处理测试通过")
    
    # 测试 8：中文标点处理
    print("\n[测试 8] 中文标点处理")
    chinese_text = "标题：测试论文。作者：王五。摘要：这是摘要。"
    chinese_paper = parse_paper_text(chinese_text)
    assert chinese_paper.title, "中文标题解析失败"
    print("  ✓ 中文标点处理测试通过")
    
    # 测试 9：原子写入
    print("\n[测试 9] 原子写入")
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        test_output = f.name
    
    success, error = write_output_atomic("测试内容", test_output, dry_run=False)
    assert success, f"原子写入失败: {error}"
    with open(test_output, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "测试内容", "写入内容不一致"
    os.unlink(test_output)
    print("  ✓ 原子写入测试通过")
    
    # 测试 10：完整流程
    print("\n[测试 10] 完整流程")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(test_text)
        temp_input = f.name
    
    config = NoteConfig(template="standard")
    result = process_single_input(temp_input, config, dry_run=True)
    assert result.success, f"完整流程失败: {result.error_message}"
    assert result.output_path.endswith("_out.md"), f"输出路径错误: {result.output_path}"
    os.unlink(temp_input)
    print("  ✓ 完整流程测试通过")
    
    print("\n" + "=" * 60)
    print("自检完成")
    print("=" * 60)
    
    return all_passed


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="DeepPaperNote — 论文精读 Obsidian 笔记生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --selftest
  python run.py --input paper.txt --template standard
  python run.py --input paper.pdf --template detailed --dry-run
  python run.py --input a.txt b.pdf c.md --template concise
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        nargs="+",
        help="输入文件路径或 URL（最多 5 个）"
    )
    
    parser.add_argument(
        "--template", "-t",
        choices=["standard", "concise", "detailed"],
        default="standard",
        help="笔记模板（默认: standard）"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，只打印输出不写盘"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="输出详细处理信息"
    )
    
    parser.add_argument(
        "--no-personal",
        action="store_true",
        help="不包含个人思考章节"
    )
    
    parser.add_argument(
        "--no-citation",
        action="store_true",
        help="不包含引用建议章节"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检"
    )
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 校验输入
    if not args.input:
        print("E002: 未提供输入文件。使用 --input 指定文件路径或 URL。")
        print("使用 --selftest 运行自检。")
        sys.exit(1)
    
    valid, error = validate_inputs(args.input)
    if not valid:
        print(error)
        sys.exit(1)
    
    # 创建配置
    config = NoteConfig(
        template=args.template,
        include_personal=not args.no_personal,
        include_citation=not args.no_citation,
        verbose=args.verbose
    )
    
    # 处理输入
    results = process_batch(args.input, config, args.dry_run)
    
    # 汇总结果
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    
    print(f"\n处理完成: 共 {len(results)} 个输入, 成功 {success_count}, 失败 {fail_count}")
    
    if fail_count > 0:
        print("\n失败明细:")
        for result in results:
            if not result.success:
                print(f"  - {result.error_message}")
    
    # 非零退出码表示有失败
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
