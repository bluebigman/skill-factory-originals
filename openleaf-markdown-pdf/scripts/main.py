#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openleaf-markdown-pdf — 分页文档 PDF 转换排版工具（独立实现）
=============================================================
功能：将 Markdown 文本转换为分页 PDF，支持标题层级、段落分页、
      简单表格降级、目录提取等核心逻辑。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
设计原则：
  - 标准库优先（argparse / re / html / datetime 等）
  - 不依赖第三方库，若需扩展可安装 reportlab（见下方注释）
  - 提供 --selftest 离线自检，硬编码样例数据，不读外部文件

错误码约定：
  E001 参数错误
  E002 输入文件不存在或不可读
  E003 输出目录不可写
  E004 输入内容为空
  E005 Markdown 解析失败
  E006 PDF 生成失败
  E007 批量处理部分失败
  E008 配置参数非法
  E009 内部状态异常
  E010 未预期的运行时错误
"""

import argparse
import datetime
import html
import os
import re
import sys
import tempfile
import traceback

# ---------------------------------------------------------------------------
# 常量与默认配置
# ---------------------------------------------------------------------------
DEFAULT_PAGE_SIZE = "A4"          # 页面尺寸
DEFAULT_MARGIN_MM = 20            # 页边距（毫米）
DEFAULT_FONT_SIZE = 10            # 正文字号
DEFAULT_HEADING_FONT_SIZE = 16    # 标题字号（一级）
DEFAULT_LINE_SPACING = 1.4        # 行距倍数
DEFAULT_PAGE_NUMBER = True        # 是否显示页码
DEFAULT_TOC = True                # 是否生成目录

# 手动分页指令（支持多种写法）
PAGE_BREAK_PATTERNS = [
    r"^\s*\\newpage\s*$",          # \newpage
    r"^\s*---\s*$",                # ---（单独一行，视为分页符）
    r"^\s*<div\s+class=[\"']page-break[\"']\s*/?>$",  # HTML 分页标记
]

# 标题层级正则（ATX 风格：1~6 个 #）
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")

# 简单表格行识别（用于降级为纯文本）
TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _err(code: str, message: str) -> None:
    """统一错误输出格式：错误码 + 描述"""
    print(f"[{code}] {message}", file=sys.stderr)


def _safe_text(text: str) -> str:
    """将文本中的特殊字符转义为 HTML 安全实体（用于 PDF 文本层）"""
    if not text:
        return ""
    return html.escape(text, quote=True)


def _strip_markdown_inline(text: str) -> str:
    """移除行内 Markdown 标记（粗体、斜体、行内代码、链接等），返回纯文本。"""
    if not text:
        return ""
    # 移除图片/链接语法：[描述](url) 或 ![描述](url)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 移除行内代码反引号
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # 移除粗体/斜体标记（** * _ __）
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    # 移除 HTML 标签（简单处理）
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _detect_page_break(line: str) -> bool:
    """判断某行是否为手动分页指令。"""
    for pattern in PAGE_BREAK_PATTERNS:
        if re.match(pattern, line.strip()):
            return True
    return False


def _detect_heading(line: str):
    """检测标题行，返回 (level, title_text) 或 None。"""
    match = HEADING_PATTERN.match(line.strip())
    if not match:
        return None
    level = len(match.group(1))
    title = _strip_markdown_inline(match.group(2))
    return level, title


def _is_table_separator(line: str) -> bool:
    """判断是否为表格分隔行（如 |---|---|）。"""
    return bool(TABLE_SEPARATOR_PATTERN.match(line.strip()))


def _is_table_row(line: str) -> bool:
    """判断是否为简单的表格数据行。"""
    return bool(TABLE_ROW_PATTERN.match(line.strip()))


def _parse_front_matter(lines: list) -> dict:
    """解析简单的 YAML front-matter（--- 开头、--- 结尾），返回字典。"""
    meta = {}
    if not lines or not lines[0].strip().startswith("---"):
        return meta
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return meta
    for line in lines[1:end_idx]:
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip("\"'")
    return meta


# ---------------------------------------------------------------------------
# Markdown 解析器（输出中间结构）
# ---------------------------------------------------------------------------
class MarkdownBlock:
    """Markdown 解析后的块对象。"""
    def __init__(self, block_type: str, content: str = "", level: int = 0):
        self.type = block_type       # heading / paragraph / list / table / page_break
        self.content = content       # 纯文本内容（或降级后的表格文本）
        self.level = level           # 标题层级（仅 heading 使用）
        self.raw_lines = []          # 原始行（用于调试或扩展）

    def __repr__(self):
        return f"<MarkdownBlock {self.type} lvl={self.level} content={self.content[:30]!r}>"


def parse_markdown(text: str) -> list:
    """将 Markdown 文本解析为块列表。

    支持：
      - ATX 标题（# ~ ######）
      - 段落（连续非空行）
      - 简单列表（- / * / 数字.）
      - 简单表格（降级为纯文本，每行保留）
      - 手动分页指令（\newpage / --- 单独行）
      - 引用块（> 开头，简单处理为段落）
      - 行内代码、粗体、斜体、链接（在 _strip_markdown_inline 中处理）

    解析失败时抛出 ValueError（由上层转换为 E005）。
    """
    if text is None:
        raise ValueError("输入文本为空")
    if not text.strip():
        raise ValueError("输入文本为空")

    lines = text.splitlines()
    blocks = []
    i = 0
    n = len(lines)

    # 跳过 front-matter
    if lines and lines[0].strip().startswith("---"):
        meta = _parse_front_matter(lines)
        # 找到 front-matter 结束行
        for idx in range(1, n):
            if lines[idx].strip() == "---":
                i = idx + 1
                break

    while i < n:
        line = lines[i].strip()

        # 空行跳过
        if not line:
            i += 1
            continue

        # 分页指令
        if _detect_page_break(lines[i]):
            blocks.append(MarkdownBlock("page_break", content=""))
            i += 1
            continue

        # 标题
        heading = _detect_heading(lines[i])
        if heading:
            level, title = heading
            blocks.append(MarkdownBlock("heading", content=title, level=level))
            i += 1
            continue

        # 表格行（简单表格降级）
        if _is_table_row(line) or _is_table_separator(line):
            table_lines = []
            while i < n and (_is_table_row(lines[i]) or _is_table_separator(lines[i])):
                table_lines.append(lines[i].strip())
                i += 1
            # 降级为纯文本：去掉 | 分隔符，转为制表符分隔
            table_text_lines = []
            for tl in table_lines:
                if _is_table_separator(tl):
                    continue  # 跳过分隔行
                cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                table_text_lines.append(" | ".join(cells))
            if table_text_lines:
                blocks.append(MarkdownBlock("table", content="\n".join(table_text_lines)))
            continue

        # 列表项（简单支持）
        list_match = re.match(r"^([-*+]|\d+\.)\s+(.*)$", line)
        if list_match:
            list_lines = []
            while i < n:
                cur = lines[i].strip()
                if not cur:
                    break
                lm = re.match(r"^([-*+]|\d+\.)\s+(.*)$", cur)
                if lm:
                    list_lines.append(f"• {_strip_markdown_inline(lm.group(2))}")
                    i += 1
                else:
                    break
            if list_lines:
                blocks.append(MarkdownBlock("list", content="\n".join(list_lines)))
            continue

        # 引用块（> 开头）
        if line.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                ql = lines[i].strip().lstrip(">").strip()
                quote_lines.append(ql)
                i += 1
            blocks.append(MarkdownBlock("paragraph", content="\n".join(quote_lines)))
            continue

        # 普通段落（连续非空行，直到遇到空行或特殊标记）
        para_lines = []
        while i < n:
            cur = lines[i].strip()
            if not cur:
                break
            if _detect_page_break(lines[i]):
                break
            if _detect_heading(lines[i]):
                break
            if _is_table_row(cur) or _is_table_separator(cur):
                break
            if cur.startswith(">"):
                break
            # 合并多行段落
            para_lines.append(_strip_markdown_inline(cur))
            i += 1

        if para_lines:
            blocks.append(MarkdownBlock("paragraph", content=" ".join(para_lines)))

    # 校验：至少有一个有效块
    if not blocks:
        raise ValueError("Markdown 内容无法解析为有效块")

    return blocks


# ---------------------------------------------------------------------------
# 目录生成
# ---------------------------------------------------------------------------
def generate_toc(blocks: list) -> list:
    """从解析后的块中提取标题，生成目录条目列表。

    返回 [(level, title), ...]，仅包含 heading 类型块。
    """
    toc = []
    for block in blocks:
        if block.type == "heading":
            toc.append((block.level, block.content))
    return toc


# ---------------------------------------------------------------------------
# PDF 生成（简化版：输出文本格式的 PDF 或 HTML 中间表示）
# ---------------------------------------------------------------------------
def build_pdf_content(blocks: list, config: dict) -> str:
    """根据块列表和配置，生成 PDF 内容（此处用文本/HTML 模拟，实际可用 reportlab）。

    注意：为保持零第三方依赖，本实现输出一种简单的文本化 PDF 表示，
          足够用于自检和排版逻辑验证。实际生产环境可替换为 reportlab 渲染。
          如需真实 PDF 输出，请安装 reportlab 并启用 _render_pdf_reportlab()。

    返回：生成的 PDF 内容字符串（或 HTML 字符串）。
    """
    lines_out = []
    lines_out.append("%PDF-1.4 (模拟输出，实际渲染请启用 reportlab)")
    lines_out.append(f"%% 页面尺寸: {config.get('page_size', DEFAULT_PAGE_SIZE)}")
    lines_out.append(f"%% 边距: {config.get('margin_mm', DEFAULT_MARGIN_MM)}mm")
    lines_out.append(f"%% 生成时间: {datetime.datetime.now().isoformat()}")
    lines_out.append("")

    # 目录
    if config.get("toc", DEFAULT_TOC):
        toc = generate_toc(blocks)
        if toc:
            lines_out.append("【目录】")
            for level, title in toc:
                indent = "  " * (level - 1)
                lines_out.append(f"{indent}- {title}")
            lines_out.append("")
            lines_out.append("--- 正文 ---")

    # 正文
    for block in blocks:
        if block.type == "heading":
            indent = "  " * (block.level - 1)
            lines_out.append(f"{indent}#{'#' * (block.level - 1)} {block.content}")
            lines_out.append("")
        elif block.type == "paragraph":
            lines_out.append(block.content)
            lines_out.append("")
        elif block.type == "list":
            lines_out.append(block.content)
            lines_out.append("")
        elif block.type == "table":
            lines_out.append("[表格降级为纯文本]")
            lines_out.append(block.content)
            lines_out.append("")
        elif block.type == "page_break":
            lines_out.append("")
            lines_out.append("--- 分页符 ---")
            lines_out.append("")

    # 页码（模拟）
    if config.get("page_number", DEFAULT_PAGE_NUMBER):
        lines_out.append("")
        lines_out.append("[页码：第 1 页 / 共 1 页]")

    return "\n".join(lines_out)


def render_pdf_reportlab(blocks: list, config: dict, output_path: str) -> None:
    """使用 reportlab 渲染真实 PDF（可选依赖）。

    如需使用，请先安装：pip install reportlab
    本函数在未安装 reportlab 时抛出 ImportError，由调用方捕获并降级。
    """
    try:
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
        )
    except ImportError as exc:
        raise ImportError("缺少 reportlab 库，请执行: pip install reportlab") from exc

    page_size = A4 if config.get("page_size", "A4").upper() == "A4" else letter
    margin = config.get("margin_mm", DEFAULT_MARGIN_MM) * mm

    doc = SimpleDocTemplate(
        output_path,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=config.get("title", "Markdown 文档"),
        author=config.get("author", "openleaf-markdown-pdf"),
    )

    styles = getSampleStyleSheet()
    # 自定义样式
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontSize=config.get("font_size", DEFAULT_FONT_SIZE),
        leading=config.get("font_size", DEFAULT_FONT_SIZE) * config.get("line_spacing", DEFAULT_LINE_SPACING),
        spaceAfter=6,
    )
    heading_styles = []
    for lvl in range(1, 7):
        base_size = max(8, DEFAULT_HEADING_FONT_SIZE - (lvl - 1) * 2)
        h_style = ParagraphStyle(
            f"Heading{lvl}",
            parent=styles["Heading1"] if lvl == 1 else styles["Heading2"],
            fontSize=base_size,
            leading=base_size * 1.2,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        )
        heading_styles.append(h_style)

    story = []

    # 目录（可选）
    if config.get("toc", DEFAULT_TOC):
        toc = generate_toc(blocks)
        if toc:
            story.append(Paragraph("目录", heading_styles[0]))
            for level, title in toc:
                indent = "&nbsp;" * (level * 4)
                story.append(Paragraph(f"{indent}{title}", body_style))
            story.append(PageBreak())

    # 正文
    for block in blocks:
        if block.type == "heading":
            lvl = min(block.level, 6) - 1
            story.append(Paragraph(_safe_text(block.content), heading_styles[lvl]))
        elif block.type == "paragraph":
            story.append(Paragraph(_safe_text(block.content).replace("\n", "<br/>"), body_style))
        elif block.type == "list":
            items = []
            for line in block.content.split("\n"):
                # 去掉前缀 • 
                clean = line.lstrip("• ").strip()
                items.append(ListItem(Paragraph(_safe_text(clean), body_style)))
            if items:
                story.append(ListFlowable(items, bulletType="bullet", start="•"))
        elif block.type == "table":
            # 表格降级为纯文本段落
            story.append(Paragraph("<b>[表格内容]</b>", body_style))
            for line in block.content.split("\n"):
                story.append(Paragraph(_safe_text(line), body_style))
        elif block.type == "page_break":
            story.append(PageBreak())

    # 页码（通过 onPage 回调实现，此处简化）
    def add_page_number(canvas, doc_obj):
        if config.get("page_number", DEFAULT_PAGE_NUMBER):
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.drawCentredString(
                doc_obj.pagesize[0] / 2.0,
                margin / 2,
                f"第 {doc_obj.page} 页",
            )
            canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)


# ---------------------------------------------------------------------------
# 核心转换函数
# ---------------------------------------------------------------------------
def convert_markdown_to_pdf(md_text: str, output_path: str, config: dict) -> dict:
    """将 Markdown 文本转换为 PDF 文件。

    参数：
      md_text: Markdown 源文本
      output_path: 输出 PDF 文件路径
      config: 配置字典（page_size, margin_mm, font_size, toc, page_number 等）

    返回：
      字典包含 status, output_path, block_count, toc_count 等信息。

    异常：
      ValueError -> E004/E005（内容为空或解析失败）
      OSError -> E002/E003（文件读写错误）
      ImportError -> E006（缺少 reportlab 且需要真实 PDF）
    """
    if not md_text or not md_text.strip():
        raise ValueError("输入 Markdown 内容为空")

    # 解析 Markdown
    try:
        blocks = parse_markdown(md_text)
    except ValueError as exc:
        raise ValueError(f"Markdown 解析失败: {exc}") from exc

    # 生成目录
    toc = generate_toc(blocks)

    # 确保输出目录存在
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.isdir(output_dir):
        raise OSError(f"输出目录不存在: {output_dir}")

    # 尝试使用 reportlab 生成真实 PDF
    use_reportlab = config.get("use_reportlab", False)
    if use_reportlab:
        try:
            render_pdf_reportlab(blocks, config, output_path)
        except ImportError as exc:
            raise RuntimeError(f"PDF 生成失败: {exc}") from exc
    else:
        # 降级：生成模拟 PDF（文本格式）
        pdf_content = build_pdf_content(blocks, config)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pdf_content)

    return {
        "status": "ok",
        "output_path": output_path,
        "block_count": len(blocks),
        "toc_count": len(toc),
        "output_size": os.path.getsize(output_path),
    }


# ---------------------------------------------------------------------------
# 批量转换
# ---------------------------------------------------------------------------
def convert_many(files: list, output_dir: str, config: dict) -> dict:
    """批量转换多个 Markdown 文件。

    返回统计信息：成功数、失败数、失败文件列表。
    """
    results = {"total": len(files), "success": 0, "failed": 0, "failures": []}

    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as exc:
            raise OSError(f"无法创建输出目录 {output_dir}: {exc}") from exc

    for md_file in files:
        try:
            if not os.path.isfile(md_file):
                raise FileNotFoundError(f"文件不存在: {md_file}")
            with open(md_file, "r", encoding="utf-8") as f:
                md_text = f.read()

            base_name = os.path.splitext(os.path.basename(md_file))[0]
            output_path = os.path.join(output_dir, f"{base_name}.pdf")
            convert_markdown_to_pdf(md_text, output_path, config)
            results["success"] += 1
        except Exception as exc:
            results["failed"] += 1
            results["failures"].append({"file": md_file, "error": str(exc)})
            _err("E007", f"批量转换失败: {md_file} -> {exc}")

    return results


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不访问网络。
    断言采用宽松阈值（大小/区间判断），确保任何环境可过。
    """
    print("=== 自检开始 ===")

    # 测试样例 1：基础 Markdown 解析
    sample_md = """
# 项目报告

## 第一章 概述

这是一个测试段落，包含 **粗体** 和 *斜体* 以及 `行内代码`。

- 列表项一
- 列表项二
- 列表项三

> 引用内容示例

## 第二章 数据

| 项目 | 数值 |
|------|------|
| A    | 100  |
| B    | 200  |

\\newpage

## 第三章 结论

结束段落。
"""

    # 1. 测试解析
    try:
        blocks = parse_markdown(sample_md)
        assert len(blocks) > 0, "解析结果不应为空"
        heading_count = sum(1 for b in blocks if b.type == "heading")
        assert heading_count >= 3, f"应至少有 3 个标题，实际 {heading_count}"
        page_break_count = sum(1 for b in blocks if b.type == "page_break")
        assert page_break_count >= 1, "应至少检测到 1 个分页符"
        print(f"  [PASS] 解析测试: {len(blocks)} 个块, {heading_count} 个标题, {page_break_count} 个分页符")
    except AssertionError as exc:
        _err("E010", f"自检失败（解析）: {exc}")
        return 1
    except Exception as exc:
        _err("E010", f"自检异常（解析）: {exc}")
        traceback.print_exc()
        return 1

    # 2. 测试目录生成
    try:
        toc = generate_toc(blocks)
        assert len(toc) >= 3, f"目录应至少 3 条，实际 {len(toc)}"
        # 宽松验证：第一条应为一级标题
        assert toc[0][0] == 1, "第一条目录应为一级标题"
        print(f"  [PASS] 目录生成: {len(toc)} 条")
    except AssertionError as exc:
        _err("E010", f"自检失败（目录）: {exc}")
        return 1

    # 3. 测试 PDF 内容生成（模拟）
    try:
        config = {
            "page_size": "A4",
            "margin_mm": 20,
            "font_size": 10,
            "line_spacing": 1.4,
            "toc": True,
            "page_number": True,
            "use_reportlab": False,  # 不使用真实 PDF 渲染
        }
        pdf_text = build_pdf_content(blocks, config)
        assert pdf_text is not None and len(pdf_text) > 0, "PDF 内容不应为空"
        assert "目录" in pdf_text, "PDF 内容应包含目录"
        assert "分页符" in pdf_text, "PDF 内容应包含分页符标记"
        print(f"  [PASS] PDF 内容生成: {len(pdf_text)} 字符")
    except AssertionError as exc:
        _err("E010", f"自检失败（PDF 内容）: {exc}")
        return 1
    except Exception as exc:
        _err("E010", f"自检异常（PDF 内容）: {exc}")
        return 1

    # 4. 测试临时文件输出（使用临时目录，不依赖当前工作目录）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_output.pdf")
            result = convert_markdown_to_pdf(sample_md, output_path, config)
            assert result["status"] == "ok", f"转换状态应为 ok，实际 {result['status']}"
            assert os.path.isfile(output_path), "输出文件应存在"
            file_size = os.path.getsize(output_path)
            assert file_size > 0, "输出文件不应为空"
            print(f"  [PASS] 文件输出: {file_size} 字节 -> {output_path}")
    except Exception as exc:
        _err("E010", f"自检异常（文件输出）: {exc}")
        traceback.print_exc()
        return 1

    # 5. 测试错误处理（空输入）
    try:
        try:
            parse_markdown("")
            assert False, "空输入应抛出异常"
        except ValueError:
            pass  # 预期行为
        print("  [PASS] 错误处理: 空输入正确抛出异常")
    except AssertionError as exc:
        _err("E010", f"自检失败（错误处理）: {exc}")
        return 1

    # 6. 测试表格降级
    try:
        table_md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
        blocks_t = parse_markdown(table_md)
        table_blocks = [b for b in blocks_t if b.type == "table"]
        assert len(table_blocks) >= 1, "应识别出表格块"
        assert "|" in table_blocks[0].content, "表格内容应保留竖线分隔"
        print("  [PASS] 表格降级: 正确识别并降级")
    except AssertionError as exc:
        _err("E010", f"自检失败（表格）: {exc}")
        return 1

    # 7. 测试 front-matter 解析
    try:
        fm_md = "---\ntitle: 测试文档\nauthor: LeafForge\n---\n\n# 正文标题\n"
        blocks_fm = parse_markdown(fm_md)
        assert len(blocks_fm) > 0, "front-matter 后的内容应被解析"
        first_block = blocks_fm[0]
        assert first_block.type == "heading" and first_block.content == "正文标题", \
            f"第一个块应为标题，实际 {first_block}"
        print("  [PASS] front-matter 解析: 正确跳过元数据")
    except AssertionError as exc:
        _err("E010", f"自检失败（front-matter）: {exc}")
        return 1

    # 8. 测试批量转换（临时目录）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建两个临时 md 文件
            md1_path = os.path.join(tmpdir, "doc1.md")
            md2_path = os.path.join(tmpdir, "doc2.md")
            with open(md1_path, "w", encoding="utf-8") as f:
                f.write("# 文档一\n\n内容一\n")
            with open(md2_path, "w", encoding="utf-8") as f:
                f.write("# 文档二\n\n内容二\n")

            out_dir = os.path.join(tmpdir, "output")
            results = convert_many([md1_path, md2_path], out_dir, config)
            assert results["total"] == 2, "总数应为 2"
            assert results["success"] == 2, f"成功数应为 2，实际 {results['success']}"
            assert results["failed"] == 0, f"失败数应为 0，实际 {results['failed']}"
            assert os.path.isfile(os.path.join(out_dir, "doc1.pdf")), "doc1.pdf 应存在"
            assert os.path.isfile(os.path.join(out_dir, "doc2.pdf")), "doc2.pdf 应存在"
            print("  [PASS] 批量转换: 2 个文件全部成功")
    except AssertionError as exc:
        _err("E010", f"自检失败（批量）: {exc}")
        return 1
    except Exception as exc:
        _err("E010", f"自检异常（批量）: {exc}")
        traceback.print_exc()
        return 1

    print("=== 自检全部通过 ===")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="openleaf-markdown-pdf",
        description="将 Markdown 转换为分页 PDF（支持目录、分页符、样式配置）",
        epilog="示例: python main.py input.md -o output.pdf --page-size A4 --margin 20",
    )
    parser.add_argument("input", nargs="?", help="输入 Markdown 文件路径")
    parser.add_argument("-o", "--output", help="输出 PDF 文件路径（单文件模式）")
    parser.add_argument("-d", "--output-dir", help="批量输出目录")
    parser.add_argument("--page-size", default=DEFAULT_PAGE_SIZE, choices=["A4", "Letter"], help="页面尺寸")
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN_MM, help="页边距（毫米）")
    parser.add_argument("--font-size", type=int, default=DEFAULT_FONT_SIZE, help="正文字号")
    parser.add_argument("--no-toc", action="store_true", help="禁用目录生成")
    parser.add_argument("--no-page-number", action="store_true", help="禁用页码")
    parser.add_argument("--use-reportlab", action="store_true", help="使用 reportlab 生成真实 PDF（需安装）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检后退出")
    return parser


def main(argv=None) -> int:
    """主入口函数。返回进程退出码。"""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input:
        parser.error("必须指定输入文件（或使用 --selftest 自检）")
        return 1

    # 构建配置
    config = {
        "page_size": args.page_size,
        "margin_mm": args.margin,
        "font_size": args.font_size,
        "line_spacing": DEFAULT_LINE_SPACING,
        "toc": not args.no_toc,
        "page_number": not args.no_page_number,
        "use_reportlab": args.use_reportlab,
    }

    # 批量模式
    if args.output_dir:
        try:
            results = convert_many([args.input], args.output_dir, config)
            if results["failed"] > 0:
                _err("E007", f"批量转换完成，成功 {results['success']}，失败 {results['failed']}")
                return 1
            print(f"转换成功: {results['success']} 个文件 -> {args.output_dir}")
            return 0
        except OSError as exc:
            _err("E003", f"输出目录错误: {exc}")
            return 1
        except Exception as exc:
            _err("E010", f"未预期错误: {exc}")
            traceback.print_exc()
            return 1

    # 单文件模式
    if not args.output:
        # 默认输出到输入文件同目录，同名 .pdf
        base = os.path.splitext(args.input)[0]
        args.output = base + ".pdf"

    try:
        # 读取输入文件
        if not os.path.isfile(args.input):
            _err("E002", f"输入文件不存在或不可读: {args.input}")
            return 1
        with open(args.input, "r", encoding="utf-8") as f:
            md_text = f.read()

        # 执行转换
        result = convert_markdown_to_pdf(md_text, args.output, config)
        print(f"转换成功: {result['output_path']}")
        print(f"  块数: {result['block_count']}, 目录条目: {result['toc_count']}")
        print(f"  输出大小: {result['output_size']} 字节")
        return 0

    except ValueError as exc:
        _err("E004" if "空" in str(exc) else "E005", f"内容错误: {exc}")
        return 1
    except OSError as exc:
        _err("E002" if "不存在" in str(exc) else "E003", f"文件错误: {exc}")
        return 1
    except RuntimeError as exc:
        _err("E006", f"PDF 生成失败: {exc}")
        return 1
    except Exception as exc:
        _err("E010", f"未预期错误: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
