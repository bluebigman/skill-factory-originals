#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf2md-web 技能核心逻辑独立实现
================================
依据功能规格 clean-room 重写，仅使用标准库。

功能：
- PDF 文本层提取（简单文本模式，非扫描件 OCR）
- 网页正文抓取（静态 HTML，去除导航/广告噪音）
- 结构化 Markdown 输出（标题、列表、表格、引用块）
- 置信度标注（对可疑内容添加标记）
- 内置自检模式（--selftest），离线运行

错误码说明：
- E001: 参数错误
- E002: 文件不存在或不可读
- E003: 不支持的输入类型
- E004: PDF 解析失败
- E005: 网页抓取失败
- E006: 输出写入失败
- E007: 内部逻辑错误
- E008: 输入内容为空
- E009: 置信度计算异常
- E010: 未知异常

作者：墨羽工坊（clean-room 实现）
"""

import argparse
import html
import os
import re
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class DocumentBlock:
    """文档块：表示 Markdown 中的一个结构单元"""
    block_type: str          # 'heading', 'paragraph', 'list', 'table', 'quote'
    content: str             # 块内容（原始文本）
    level: int = 0           # 标题层级或列表层级
    confidence: float = 1.0  # 置信度 0~1
    metadata: dict = field(default_factory=dict)


@dataclass
class ConversionResult:
    """转换结果封装"""
    markdown: str                    # 最终 Markdown 文本
    blocks: List[DocumentBlock]      # 解析出的文档块
    source_type: str                 # 'pdf' 或 'web'
    title: str = ""                  # 文档标题
    warnings: List[str] = field(default_factory=list)  # 警告信息


# ============================================================
# 工具函数
# ============================================================

def _normalize_text(text: str) -> str:
    """规范化文本：去除多余空白、统一换行"""
    if not text:
        return ""
    # 将各种空白字符统一为空格
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 压缩连续空白（保留段落间的换行）
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    # 移除空行（后续会按需重建）
    lines = [line for line in lines if line]
    return '\n'.join(lines)


def _escape_markdown(text: str) -> str:
    """转义 Markdown 特殊字符（用于普通文本）"""
    special = r'\\`*_{}[]()#+-.!|>'
    result = []
    for ch in text:
        if ch in special:
            result.append('\\' + ch)
        else:
            result.append(ch)
    return ''.join(result)


def _estimate_confidence(text: str) -> float:
    """
    估算文本置信度（0~1）
    依据：文本长度、特殊字符比例、乱码检测等启发式规则
    返回 0~1 之间的浮点数
    """
    if not text:
        return 0.0

    confidence = 1.0
    length = len(text)

    # 文本过短可能信息不完整
    if length < 10:
        confidence -= 0.2

    # 检测乱码特征（如大量非 ASCII 字符）
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    if length > 0:
        non_ascii_ratio = non_ascii / length
        if non_ascii_ratio > 0.5:
            confidence -= 0.3

    # 检测异常重复字符（如 "aaaa"）
    if re.search(r'(.)\1{3,}', text):
        confidence -= 0.2

    # 检测字符集混乱（同时包含中日韩和拉丁特殊符号）
    if re.search(r'[\u4e00-\u9fff]', text) and re.search(r'[a-zA-Z]', text):
        # 中英混排是正常的，不扣分
        pass

    # 检测控制字符
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
        confidence -= 0.3

    # 检测无意义的重复模式（如 "asdf" 重复）
    # 检查是否有明显的重复子串
    if length >= 8:
        # 检查是否由少量字符重复组成
        unique_chars = set(text)
        if len(unique_chars) <= 4 and length >= 8:
            # 可能是无意义的重复文本
            confidence -= 0.3
        
        # 检查是否有重复的单词或短语
        words = text.lower().split()
        if len(words) >= 3:
            unique_words = set(words)
            if len(unique_words) <= 2:
                confidence -= 0.2

    # 检测是否为纯字母且无空格（可能是乱码）
    if re.match(r'^[a-zA-Z]+$', text) and length >= 10:
        # 纯字母长文本，无空格，可能是乱码
        confidence -= 0.1

    # 保证在 0~1 范围内
    return max(0.0, min(1.0, confidence))


def _parse_table(lines: List[str]) -> Optional[DocumentBlock]:
    """
    尝试将文本行解析为表格
    简单启发式：检测管道符 | 分隔的连续行
    """
    if not lines:
        return None

    table_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.count('|') >= 2:
            table_lines.append(stripped)
        elif table_lines:
            break  # 表格结束

    if len(table_lines) < 2:  # 至少需要表头和分隔行
        return None

    # 解析表格行
    rows = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.split('|')]
        # 去掉首尾的空单元格（因为行首行尾的 |）
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        rows.append(cells)

    # 检查是否为有效表格（每行列数一致）
    if len(rows) < 2:
        return None

    col_count = len(rows[0])
    for row in rows[1:]:
        if len(row) != col_count:
            return None

    # 检查第二行是否为分隔行（--- 或 :---: 等）
    sep_pattern = re.compile(r'^:?-{2,}:?$')
    if not all(sep_pattern.match(cell) for cell in rows[1]):
        return None

    # 构建 Markdown 表格
    md_lines = []
    for i, row in enumerate(rows):
        md_lines.append('| ' + ' | '.join(row) + ' |')
        if i == 0:
            # 生成分隔行
            sep_cells = ['---'] * col_count
            md_lines.append('| ' + ' | '.join(sep_cells) + ' |')

    block = DocumentBlock(
        block_type='table',
        content='\n'.join(md_lines),
        confidence=0.95
    )
    return block


def _parse_list(lines: List[str]) -> Optional[DocumentBlock]:
    """解析列表（支持有序和无序）"""
    if not lines:
        return None

    list_lines = []
    for line in lines:
        stripped = line.strip()
        # 无序列表：- * +
        if re.match(r'^[-*+]\s+', stripped):
            list_lines.append(stripped)
        # 有序列表：1. 2. 3.
        elif re.match(r'^\d+[.)]\s+', stripped):
            list_lines.append(stripped)
        else:
            if list_lines:
                break
            else:
                return None

    if not list_lines:
        return None

    block = DocumentBlock(
        block_type='list',
        content='\n'.join(list_lines),
        confidence=0.9
    )
    return block


def _parse_quote(lines: List[str]) -> Optional[DocumentBlock]:
    """解析引用块"""
    if not lines:
        return None

    quote_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('>'):
            quote_lines.append(stripped)
        else:
            if quote_lines:
                break
            else:
                return None

    if not quote_lines:
        return None

    block = DocumentBlock(
        block_type='quote',
        content='\n'.join(quote_lines),
        confidence=0.9
    )
    return block


def _parse_heading(line: str) -> Optional[DocumentBlock]:
    """解析标题"""
    stripped = line.strip()
    match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
    if match:
        level = len(match.group(1))
        content = match.group(2)
        return DocumentBlock(
            block_type='heading',
            content=content,
            level=level,
            confidence=1.0
        )
    return None


def _parse_paragraph(text: str) -> DocumentBlock:
    """创建段落块"""
    conf = _estimate_confidence(text)
    return DocumentBlock(
        block_type='paragraph',
        content=text,
        confidence=conf
    )


# ============================================================
# 核心转换逻辑
# ============================================================

def _convert_text_to_blocks(text: str) -> Tuple[List[DocumentBlock], List[str]]:
    """
    将纯文本转换为结构化文档块
    返回 (blocks, warnings)
    """
    blocks: List[DocumentBlock] = []
    warnings: List[str] = []

    normalized = _normalize_text(text)
    if not normalized:
        warnings.append("输入内容为空")
        return blocks, warnings

    lines = normalized.split('\n')
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i]
        stripped = line.strip()

        # 空行跳过
        if not stripped:
            i += 1
            continue

        # 标题
        heading = _parse_heading(line)
        if heading:
            blocks.append(heading)
            i += 1
            continue

        # 收集连续行用于判断块类型
        block_lines = [line]
        j = i + 1
        while j < total_lines:
            next_line = lines[j].strip()
            if not next_line:
                break
            # 如果遇到新标题，停止收集
            if _parse_heading(lines[j]):
                break
            block_lines.append(lines[j])
            j += 1

        # 尝试解析表格
        table = _parse_table(block_lines)
        if table:
            blocks.append(table)
            i = j
            continue

        # 尝试解析列表
        list_block = _parse_list(block_lines)
        if list_block:
            blocks.append(list_block)
            i = j
            continue

        # 尝试解析引用
        quote = _parse_quote(block_lines)
        if quote:
            blocks.append(quote)
            i = j
            continue

        # 普通段落
        para_text = '\n'.join(block_lines)
        blocks.append(_parse_paragraph(para_text))
        i = j

    return blocks, warnings


def _blocks_to_markdown(blocks: List[DocumentBlock]) -> str:
    """将文档块转换为 Markdown 文本"""
    md_parts = []

    for block in blocks:
        if block.block_type == 'heading':
            md_parts.append('#' * block.level + ' ' + block.content)
        elif block.block_type == 'paragraph':
            md_parts.append(block.content)
        elif block.block_type == 'list':
            md_parts.append(block.content)
        elif block.block_type == 'table':
            md_parts.append(block.content)
        elif block.block_type == 'quote':
            md_parts.append(block.content)
        else:
            md_parts.append(block.content)

        # 块之间加空行
        md_parts.append('')

    return '\n'.join(md_parts).strip()


def _apply_confidence_annotation(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
    """
    对低置信度内容添加标注
    置信度低于 0.7 的内容会添加 [置信度:XX%] 前缀
    """
    annotated = []
    for block in blocks:
        if block.confidence < 0.7 and block.block_type in ('paragraph', 'list', 'quote'):
            # 深拷贝避免修改原对象
            new_block = DocumentBlock(
                block_type=block.block_type,
                content=block.content,
                level=block.level,
                confidence=block.confidence,
                metadata=dict(block.metadata)
            )
            percent = int(block.confidence * 100)
            new_block.content = f"[置信度:{percent}%] {new_block.content}"
            annotated.append(new_block)
        else:
            annotated.append(block)
    return annotated


# ============================================================
# PDF 处理
# ============================================================

def _extract_pdf_text(filepath: str) -> str:
    """
    从 PDF 中提取文本层内容
    仅支持简单文本型 PDF（非扫描件）
    使用正则表达式从 PDF 原始内容中提取文本流
    """
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
    except FileNotFoundError:
        raise RuntimeError("E002: 文件不存在")
    except PermissionError:
        raise RuntimeError("E002: 文件不可读")

    if not content.startswith(b'%PDF'):
        raise RuntimeError("E003: 不是有效的 PDF 文件")

    # 检查是否加密
    if b'/Encrypt' in content:
        raise RuntimeError("E004: 加密 PDF 不支持解析")

    # 简单提取文本流
    # 查找所有文本操作符 (Tj, TJ)
    texts = []
    try:
        # 解码 PDF 内容（尝试多种编码）
        decoded = content.decode('latin-1')
    except UnicodeDecodeError:
        raise RuntimeError("E004: PDF 解码失败")

    # 提取括号内的文本
    # 处理 Tj 操作符: (text) Tj
    pattern_tj = re.compile(r'\(((?:[^()\\]|\\.)*)\)\s*Tj')
    # 处理 TJ 操作符: [(text) num (text)] TJ
    pattern_tj_array = re.compile(r'\[((?:[^\[\]\\]|\\.)*)\]\s*TJ')

    for match in pattern_tj.finditer(decoded):
        text = match.group(1)
        # 处理转义字符
        text = text.replace(r'\(', '(').replace(r'\)', ')')
        text = text.replace(r'\\', '\\')
        texts.append(text)

    for match in pattern_tj_array.finditer(decoded):
        array_content = match.group(1)
        # 提取数组中的文本字符串
        inner_pattern = re.compile(r'\(((?:[^()\\]|\\.)*)\)')
        for inner in inner_pattern.finditer(array_content):
            text = inner.group(1)
            text = text.replace(r'\(', '(').replace(r'\)', ')')
            text = text.replace(r'\\', '\\')
            texts.append(text)

    if not texts:
        raise RuntimeError("E004: 未能从 PDF 中提取到文本（可能为扫描件）")

    # 合并文本，用空格连接
    return ' '.join(texts)


def _convert_pdf(filepath: str) -> ConversionResult:
    """将 PDF 文件转换为 Markdown"""
    try:
        raw_text = _extract_pdf_text(filepath)
    except RuntimeError as e:
        raise

    blocks, warnings = _convert_text_to_blocks(raw_text)
    blocks = _apply_confidence_annotation(blocks)
    markdown = _blocks_to_markdown(blocks)

    # 尝试提取标题（第一个标题块）
    title = ""
    for block in blocks:
        if block.block_type == 'heading':
            title = block.content
            break

    return ConversionResult(
        markdown=markdown,
        blocks=blocks,
        source_type='pdf',
        title=title,
        warnings=warnings
    )


# ============================================================
# 网页处理
# ============================================================

def _fetch_webpage(url: str, timeout: int = 10) -> str:
    """抓取网页内容"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            # 尝试从响应头获取编码
            charset = resp.headers.get_content_charset()
            if charset:
                return content.decode(charset, errors='replace')
            # 默认 UTF-8
            return content.decode('utf-8', errors='replace')
    except urllib.error.URLError as e:
        raise RuntimeError(f"E005: 网页抓取失败 - {e.reason}")
    except Exception as e:
        raise RuntimeError(f"E005: 网页抓取失败 - {str(e)}")


def _extract_web_content(html_content: str) -> str:
    """
    从 HTML 中提取正文内容
    简单实现：移除 script/style/nav 等标签，提取文本
    """
    # 移除不需要的标签
    content = html_content

    # 移除 script 和 style
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<footer[^>]*>.*?</footer>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<header[^>]*>.*?</header>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # 将块级标签转换为换行
    content = re.sub(r'<(p|div|h[1-6]|li|tr|br)[^>]*>', '\n', content, flags=re.IGNORECASE)

    # 移除所有其他标签
    content = re.sub(r'<[^>]+>', '', content)

    # 解码 HTML 实体
    content = html.unescape(content)

    # 规范化文本
    return _normalize_text(content)


def _convert_web(url: str) -> ConversionResult:
    """将网页转换为 Markdown"""
    try:
        html_content = _fetch_webpage(url)
        raw_text = _extract_web_content(html_content)
    except RuntimeError as e:
        raise

    if not raw_text:
        raise RuntimeError("E008: 网页内容为空")

    blocks, warnings = _convert_text_to_blocks(raw_text)
    blocks = _apply_confidence_annotation(blocks)
    markdown = _blocks_to_markdown(blocks)

    # 尝试从 HTML 提取标题
    title = ""
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = html.unescape(title_match.group(1)).strip()

    return ConversionResult(
        markdown=markdown,
        blocks=blocks,
        source_type='web',
        title=title,
        warnings=warnings
    )


# ============================================================
# 主入口
# ============================================================

def _run_selftest() -> int:
    """
    内置自检逻辑
    使用硬编码样例数据，不依赖外部文件或网络
    """
    print("=" * 60)
    print("pdf2md-web 自检模式")
    print("=" * 60)

    # 测试数据 1：包含标题、段落、列表、表格的文本
    test_text_1 = """
# 项目报告

## 概述
这是一个测试文档，用于验证核心转换逻辑。

## 关键数据

| 项目 | 数值 | 备注 |
|------|------|------|
| 营收 | 100万 | 同比增长 20% |
| 成本 | 60万 | 占比 60% |

## 要点列表
- 第一点：完成核心模块开发
- 第二点：通过单元测试
- 第三点：部署到生产环境

## 引用
> 注意：以上数据仅为测试样例。
"""

    # 测试数据 2：简单 PDF 模拟文本
    test_text_2 = "PDF 文本提取测试 这是从 PDF 中提取的内容 包含多个段落"

    # 测试 1：文本转块
    print("\n[测试 1] 文本转文档块")
    blocks1, warnings1 = _convert_text_to_blocks(test_text_1)
    assert len(blocks1) > 0, "E007: 文本转块失败 - 未生成任何块"
    assert any(b.block_type == 'heading' for b in blocks1), "E007: 未识别到标题"
    assert any(b.block_type == 'table' for b in blocks1), "E007: 未识别到表格"
    assert any(b.block_type == 'list' for b in blocks1), "E007: 未识别到列表"
    assert any(b.block_type == 'quote' for b in blocks1), "E007: 未识别到引用"
    print(f"  ✓ 成功生成 {len(blocks1)} 个块")
    print(f"  ✓ 块类型: {set(b.block_type for b in blocks1)}")

    # 测试 2：Markdown 生成
    print("\n[测试 2] Markdown 生成")
    md1 = _blocks_to_markdown(blocks1)
    assert len(md1) > 0, "E007: Markdown 生成失败"
    assert '#' in md1, "E007: Markdown 缺少标题标记"
    assert '|' in md1, "E007: Markdown 缺少表格标记"
    print(f"  ✓ Markdown 长度: {len(md1)} 字符")
    print(f"  ✓ 包含表格语法: {'|' in md1}")

    # 测试 3：置信度计算
    print("\n[测试 3] 置信度计算")
    conf_normal = _estimate_confidence("这是一个正常的测试文本内容")
    conf_garbage = _estimate_confidence("asdfasdfasdfasdfasdf")
    conf_short = _estimate_confidence("短")
    conf_repeat = _estimate_confidence("哈哈哈哈哈哈")
    
    assert conf_normal > 0.5, f"E009: 正常文本置信度应高于 0.5, 实际为 {conf_normal}"
    assert conf_garbage < conf_normal, f"E009: 乱码文本置信度应低于正常文本, garbage={conf_garbage}, normal={conf_normal}"
    assert conf_short < conf_normal, f"E009: 短文本置信度应低于正常文本, short={conf_short}, normal={conf_normal}"
    assert conf_repeat < conf_normal, f"E009: 重复文本置信度应低于正常文本, repeat={conf_repeat}, normal={conf_normal}"
    
    print(f"  ✓ 正常文本置信度: {conf_normal:.2f}")
    print(f"  ✓ 乱码文本置信度: {conf_garbage:.2f}")
    print(f"  ✓ 短文本置信度: {conf_short:.2f}")
    print(f"  ✓ 重复文本置信度: {conf_repeat:.2f}")

    # 测试 4：置信度标注
    print("\n[测试 4] 置信度标注")
    test_blocks = [
        DocumentBlock(block_type='paragraph', content='正常内容', confidence=0.9),
        DocumentBlock(block_type='paragraph', content='模糊内容', confidence=0.5),
    ]
    annotated = _apply_confidence_annotation(test_blocks)
    assert '[置信度' in annotated[1].content, "E007: 低置信度内容未标注"
    assert '[置信度' not in annotated[0].content, "E007: 高置信度内容不应标注"
    print(f"  ✓ 低置信度块已标注: {annotated[1].content}")
    print(f"  ✓ 高置信度块未标注: {annotated[0].content}")

    # 测试 5：网页内容提取（模拟 HTML）
    print("\n[测试 5] 网页内容提取")
    test_html = """
    <html>
    <head><title>测试网页</title></head>
    <body>
        <nav>导航链接</nav>
        <div class="content">
            <h1>文章标题</h1>
            <p>这是正文第一段。</p>
            <p>这是正文第二段。</p>
        </div>
        <footer>页脚内容</footer>
    </body>
    </html>
    """
    extracted = _extract_web_content(test_html)
    assert '导航链接' not in extracted, "E007: 导航内容未移除"
    assert '页脚内容' not in extracted, "E007: 页脚内容未移除"
    assert '文章标题' in extracted, "E007: 正文内容丢失"
    assert '正文第一段' in extracted, "E007: 正文内容丢失"
    print(f"  ✓ 提取内容长度: {len(extracted)} 字符")
    print(f"  ✓ 噪音已移除: {'导航链接' not in extracted}")

    # 测试 6：PDF 文本提取（模拟 PDF 内容）
    print("\n[测试 6] PDF 文本提取（模拟）")
    # 创建一个临时模拟 PDF 内容（仅用于测试解析逻辑）
    # 实际不会写文件，直接测试文本提取的正则逻辑
    mock_pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nBT\n(Hello PDF) Tj\nET\nBT\n[(World) 10 (Test)] TJ\nET\n%%EOF'
    try:
        decoded = mock_pdf_content.decode('latin-1')
        # 复用提取逻辑
        texts = []
        pattern_tj = re.compile(r'\(((?:[^()\\]|\\.)*)\)\s*Tj')
        pattern_tj_array = re.compile(r'\[((?:[^\[\]\\]|\\.)*)\]\s*TJ')
        for match in pattern_tj.finditer(decoded):
            texts.append(match.group(1))
        for match in pattern_tj_array.finditer(decoded):
            inner_pattern = re.compile(r'\(((?:[^()\\]|\\.)*)\)')
            for inner in inner_pattern.finditer(match.group(1)):
                texts.append(inner.group(1))
        assert len(texts) >= 2, "E007: PDF 文本提取失败"
        combined = ' '.join(texts)
        assert 'Hello' in combined and 'World' in combined, "E007: PDF 文本内容不正确"
        print(f"  ✓ 提取到 {len(texts)} 个文本片段")
        print(f"  ✓ 合并内容: {combined}")
    except Exception as e:
        print(f"  ✗ PDF 提取测试失败: {e}")
        return 1

    # 测试 7：错误处理
    print("\n[测试 7] 错误处理")
    try:
        # 测试不存在的文件
        _extract_pdf_text('/nonexistent/file.pdf')
        assert False, "E002: 应抛出文件不存在错误"
    except RuntimeError as e:
        assert str(e).startswith("E002"), f"错误码不正确: {e}"
        print(f"  ✓ 文件不存在错误: {e}")

    # 测试 8：空输入
    print("\n[测试 8] 空输入处理")
    blocks_empty, _ = _convert_text_to_blocks("")
    assert len(blocks_empty) == 0, "E007: 空输入应返回空块列表"
    print(f"  ✓ 空输入返回空块: {len(blocks_empty)} 个块")

    # 测试 9：综合转换（模拟完整流程）
    print("\n[测试 9] 完整转换流程")
    blocks_full, _ = _convert_text_to_blocks(test_text_1)
    blocks_full = _apply_confidence_annotation(blocks_full)
    md_full = _blocks_to_markdown(blocks_full)
    assert len(md_full) > 100, "E007: 完整转换结果过短"
    assert md_full.count('#') >= 3, "E007: 缺少多个标题"
    print(f"  ✓ 完整 Markdown 长度: {len(md_full)} 字符")
    print(f"  ✓ 标题数量: {md_full.count('#')}")

    # 测试 10：边界情况
    print("\n[测试 10] 边界情况")
    # 非常长的文本
    long_text = "测试文本 " * 1000
    blocks_long, _ = _convert_text_to_blocks(long_text)
    assert len(blocks_long) > 0, "E007: 长文本处理失败"
    print(f"  ✓ 长文本处理成功: {len(blocks_long)} 个块")

    # 特殊字符
    special_text = "特殊字符: <>&\"'`*_[]()#+-.!|"
    blocks_special, _ = _convert_text_to_blocks(special_text)
    assert len(blocks_special) > 0, "E007: 特殊字符处理失败"
    print(f"  ✓ 特殊字符处理成功")

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return 0


def _run_conversion(input_path: str, output_path: Optional[str] = None) -> int:
    """
    执行实际转换
    根据输入路径判断类型（.pdf 或 URL）
    """
    try:
        # 判断输入类型
        if input_path.startswith(('http://', 'https://')):
            print(f"正在抓取网页: {input_path}")
            result = _convert_web(input_path)
        elif input_path.lower().endswith('.pdf'):
            print(f"正在解析 PDF: {input_path}")
            result = _convert_pdf(input_path)
        else:
            print(f"错误: 不支持的文件类型: {input_path}", file=sys.stderr)
            return 3

        # 输出结果
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)
                print(f"已保存到: {output_path}")
            except IOError as e:
                print(f"E006: 输出写入失败 - {e}", file=sys.stderr)
                return 6
        else:
            print(result.markdown)

        # 打印统计信息
        print(f"\n--- 转换统计 ---")
        print(f"来源类型: {result.source_type}")
        print(f"文档标题: {result.title or '(未识别)'}")
        print(f"文档块数: {len(result.blocks)}")
        print(f"Markdown 长度: {len(result.markdown)} 字符")
        if result.warnings:
            print(f"警告 ({len(result.warnings)}):")
            for w in result.warnings:
                print(f"  - {w}")

        return 0

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        error_code = e.args[0][:4] if e.args else "E010"
        return int(error_code[1:]) if error_code[1:].isdigit() else 10
    except Exception as e:
        print(f"E010: 未知异常 - {e}", file=sys.stderr)
        return 10


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="pdf2md-web: 将 PDF 或网页转换为结构化 Markdown",
        epilog="示例: python main.py report.pdf -o output.md"
    )
    parser.add_argument(
        'input',
        nargs='?',
        help='输入文件路径（.pdf）或网页 URL'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出 Markdown 文件路径（默认输出到标准输出）'
    )
    parser.add_argument(
        '--selftest',
        action='store_true',
        help='运行内置自检测试（离线，无需外部依赖）'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='pdf2md-web 1.0.3 (clean-room implementation)'
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 正常模式
    if not args.input:
        parser.print_help()
        print("\nE001: 必须提供输入文件或 URL（或使用 --selftest）", file=sys.stderr)
        return 1

    return _run_conversion(args.input, args.output)


if __name__ == '__main__':
    sys.exit(main())
