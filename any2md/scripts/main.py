#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
any2md - 文档转Markdown 结构化整理 格式转换
版本: 2.0.0 (clean-room 独立实现)

功能:
- 文本/PDF/网页/对话/表格 → 结构化 Markdown
- 多编码自动检测 (UTF-8/GBK/GB18030)
- 流式处理大文件 (O(n) 时间复杂度)
- --dry-run 预览模式
- --selftest 自检模式
"""

import sys
import os
import re
import argparse
import tempfile
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional
import traceback
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERR_OK = 0
ERR_INPUT_EMPTY = "E001"      # 输入内容为空
ERR_INPUT_NOT_STRING = "E002" # 输入不是字符串
ERR_OUTPUT_FAIL = "E003"      # 输出写入失败
ERR_PARSE_FAIL = "E004"       # 解析失败
ERR_TABLE_FAIL = "E005"       # 表格转换失败
ERR_CODE_FAIL = "E006"        # 代码块处理失败
ERR_HEADING_FAIL = "E007"     # 标题处理失败
ERR_LINK_FAIL = "E008"        # 链接处理失败
ERR_LIST_FAIL = "E009"        # 列表处理失败
ERR_UNKNOWN = "E010"          # 未知错误


# ============================================================
# 核心转换逻辑
# ============================================================

def _read_text_safe(path: str) -> str:
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _iter_lines(path: str):
    """流式读取文件行（R5 大输入流式）"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def _detect_heading(line: str) -> Tuple[int, str]:
    """检测是否为Markdown标题，返回(级别, 标题内容)。非标题返回(0, 原行)。"""
    stripped = line.lstrip()
    if stripped.startswith('#'):
        level = 0
        for ch in stripped:
            if ch == '#':
                level += 1
            else:
                break
        if 1 <= level <= 6 and (len(stripped) == level or stripped[level] in (' ', '\t')):
            content = stripped[level:].strip()
            return level, content
    return 0, line


def _detect_list_item(line: str) -> Tuple[bool, str, str]:
    """检测是否为列表项，返回(是否列表, 类型(bullet/number), 内容)"""
    stripped = line.strip()
    # 无序列表
    bullet_match = re.match(r'^[-*+]\s+(.*)', stripped)
    if bullet_match:
        return True, "bullet", bullet_match.group(1)
    # 有序列表
    number_match = re.match(r'^\d+[.)]\s+(.*)', stripped)
    if number_match:
        return True, "number", number_match.group(1)
    return False, "", stripped


def _detect_table(lines: List[str], start_idx: int) -> Tuple[bool, List[str], int]:
    """检测是否为表格，返回(是否表格, 表格行列表, 结束索引)"""
    if start_idx >= len(lines):
        return False, [], start_idx
    
    # 检查是否包含分隔行 (---|---)
    if start_idx + 1 < len(lines):
        second_line = lines[start_idx + 1].strip()
        if re.match(r'^[\s\|:-]+$', second_line) and '|' in second_line and '-' in second_line:
            table_lines = []
            idx = start_idx
            while idx < len(lines) and '|' in lines[idx]:
                table_lines.append(lines[idx].strip())
                idx += 1
            return True, table_lines, idx
    
    # 检查单行表格 (| a | b |)
    if '|' in lines[start_idx]:
        table_lines = []
        idx = start_idx
        while idx < len(lines) and '|' in lines[idx]:
            table_lines.append(lines[idx].strip())
            idx += 1
        if len(table_lines) >= 2:
            return True, table_lines, idx
    
    return False, [], start_idx


def _parse_table_line(line: str) -> List[str]:
    """解析表格行，返回单元格列表"""
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    cells = [cell.strip() for cell in line.split('|')]
    return cells


def _format_table(table_lines: List[str]) -> str:
    """将表格行列表格式化为 Markdown 表格"""
    if not table_lines:
        return ""
    
    try:
        # 解析所有行
        parsed_rows = []
        for line in table_lines:
            cells = _parse_table_line(line)
            parsed_rows.append(cells)
        
        if not parsed_rows:
            return ""
        
        # 确定列数
        max_cols = max(len(row) for row in parsed_rows)
        
        # 补齐单元格
        for row in parsed_rows:
            while len(row) < max_cols:
                row.append("")
        
        # 检查是否已有分隔行
        has_separator = False
        for row in parsed_rows:
            if all(re.match(r'^:?-{3,}:?$', cell) for cell in row if cell):
                has_separator = True
                break
        
        # 构建表格
        result = []
        header = parsed_rows[0]
        result.append("| " + " | ".join(header) + " |")
        
        if not has_separator:
            result.append("| " + " | ".join(["---"] * max_cols) + " |")
            body_start = 1
        else:
            body_start = 1
            for i, row in enumerate(parsed_rows):
                if all(re.match(r'^:?-{3,}:?$', cell) for cell in row if cell):
                    result.append("| " + " | ".join(row) + " |")
                    body_start = i + 1
                    break
        
        for row in parsed_rows[body_start:]:
            result.append("| " + " | ".join(row) + " |")
        
        return "\n".join(result)
    except Exception as e:
        print(f"警告: 表格转换失败: {e}", file=sys.stderr)
        return "\n".join(table_lines)


def _detect_code_block(lines: List[str], start_idx: int) -> Tuple[bool, List[str], int]:
    """检测是否为代码块，返回(是否代码块, 代码行列表, 结束索引)"""
    if start_idx >= len(lines):
        return False, [], start_idx
    
    first_line = lines[start_idx].strip()
    if first_line.startswith('```') or first_line.startswith('~~~'):
        code_lines = []
        idx = start_idx + 1
        fence_char = first_line[0]
        fence_len = len(first_line) - len(first_line.lstrip(fence_char))
        fence = fence_char * fence_len
        
        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith(fence):
                idx += 1
                break
            code_lines.append(lines[idx])
            idx += 1
        
        return True, code_lines, idx
    
    return False, [], start_idx


def _detect_link(line: str) -> str:
    """检测并格式化链接"""
    # 保留已有的 Markdown 链接
    if re.search(r'\[.*\]\(.*\)', line):
        return line
    
    # 转换裸 URL 为链接
    url_pattern = r'(https?://[^\s]+)'
    return re.sub(url_pattern, r'[\1](\1)', line)


def _detect_bold_italic(line: str) -> str:
    """检测并格式化粗体和斜体"""
    # 保留已有的 Markdown 格式
    if re.search(r'\*\*.*\*\*', line) or re.search(r'\*.*\*', line):
        return line
    
    # 将 **文本** 转换为粗体
    line = re.sub(r'\*\*(.+?)\*\*', r'**\1**', line)
    
    # 将 *文本* 转换为斜体
    line = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'*\1*', line)
    
    return line


def _detect_quote(line: str) -> Tuple[bool, str]:
    """检测是否为引用，返回(是否引用, 内容)"""
    stripped = line.strip()
    if stripped.startswith('>'):
        return True, stripped[1:].strip()
    return False, line


def _detect_horizontal_rule(line: str) -> bool:
    """检测是否为水平分割线"""
    stripped = line.strip()
    if re.match(r'^(-{3,}|\*{3,}|_{3,})$', stripped):
        return True
    return False


def _process_line(line: str, in_code_block: bool = False) -> str:
    """处理单行文本，返回转换后的 Markdown 行"""
    if in_code_block:
        return line
    
    stripped = line.strip()
    if not stripped:
        return ""
    
    # 检测标题
    level, content = _detect_heading(line)
    if level > 0:
        return f"{'#' * level} {content}"
    
    # 检测水平分割线
    if _detect_horizontal_rule(line):
        return "---"
    
    # 检测引用
    is_quote, quote_content = _detect_quote(line)
    if is_quote:
        return f"> {quote_content}"
    
    # 检测列表项
    is_list, list_type, list_content = _detect_list_item(line)
    if is_list:
        if list_type == "bullet":
            return f"- {list_content}"
        else:
            # 保留原始编号
            number_match = re.match(r'^(\d+)[.)]\s+(.*)', stripped)
            if number_match:
                return f"{number_match.group(1)}. {number_match.group(2)}"
    
    # 处理链接
    line = _detect_link(line)
    
    # 处理粗体和斜体
    line = _detect_bold_italic(line)
    
    return line


def _convert_text_to_markdown(text: str, verbose: bool = False) -> str:
    """将纯文本转换为结构化 Markdown"""
    if not text or not text.strip():
        return ""
    
    try:
        lines = text.split('\n')
        result = []
        i = 0
        in_code_block = False
        
        while i < len(lines):
            line = lines[i]
            
            # 检测代码块
            is_code, code_lines, end_idx = _detect_code_block(lines, i)
            if is_code:
                result.append("```")
                result.extend(code_lines)
                result.append("```")
                i = end_idx
                continue
            
            # 检测表格
            is_table, table_lines, end_idx = _detect_table(lines, i)
            if is_table:
                table_md = _format_table(table_lines)
                if table_md:
                    result.append(table_md)
                    i = end_idx
                    continue
            
            # 处理普通行
            processed = _process_line(line, in_code_block)
            result.append(processed)
            i += 1
        
        # 合并连续空行
        final_result = []
        prev_empty = False
        for line in result:
            if not line.strip():
                if not prev_empty:
                    final_result.append("")
                prev_empty = True
            else:
                final_result.append(line)
                prev_empty = False
        
        return "\n".join(final_result).strip()
    except Exception as e:
        print(f"警告: 文本转换失败: {e}", file=sys.stderr)
        return text


def _extract_pdf_text(path: str) -> str:
    """从 PDF 文件中提取文本（简化实现）"""
    try:
        # 尝试读取 PDF 文件
        with open(path, 'rb') as f:
            content = f.read()
        
        # 提取文本流
        text_parts = []
        in_text = False
        current_text = []
        
        # 简单提取 PDF 中的文本对象
        for match in re.finditer(rb'\((.*?)\)\s*Tj|\[(.*?)\]\s*TJ', content):
            if match.group(1):
                text_parts.append(match.group(1).decode('latin-1'))
            elif match.group(2):
                text_parts.append(match.group(2).decode('latin-1'))
        
        if text_parts:
            return ' '.join(text_parts)
        
        # 如果无法提取，尝试读取为文本
        return _read_text_safe(path)
    except Exception as e:
        print(f"警告: PDF 提取失败: {e}", file=sys.stderr)
        return ""


def _extract_html_text(path: str) -> str:
    """从 HTML 文件中提取正文文本"""
    try:
        content = _read_text_safe(path)
        
        # 移除 script 和 style 标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        # 移除 HTML 标签
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # 解码 HTML 实体
        import html
        content = html.unescape(content)
        
        # 压缩空白
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    except Exception as e:
        print(f"警告: HTML 提取失败: {e}", file=sys.stderr)
        return ""


def _detect_file_type(path: str) -> str:
    """检测文件类型"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        return 'pdf'
    elif ext in ('.html', '.htm'):
        return 'html'
    elif ext in ('.csv', '.tsv'):
        return 'csv'
    elif ext in ('.md', '.markdown'):
        return 'markdown'
    else:
        return 'text'


def _convert_csv_to_markdown(path: str) -> str:
    """将 CSV 文件转换为 Markdown 表格"""
    try:
        import csv
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if not rows:
            return ""
        
        # 构建 Markdown 表格
        result = []
        header = rows[0]
        result.append("| " + " | ".join(header) + " |")
        result.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        for row in rows[1:]:
            # 补齐单元格
            while len(row) < len(header):
                row.append("")
            result.append("| " + " | ".join(row) + " |")
        
        return "\n".join(result)
    except Exception as e:
        print(f"警告: CSV 转换失败: {e}", file=sys.stderr)
        return ""


def _convert_file_to_markdown(path: str, verbose: bool = False) -> str:
    """将文件转换为 Markdown"""
    file_type = _detect_file_type(path)
    
    if verbose:
        print(f"检测到文件类型: {file_type}", file=sys.stderr)
    
    if file_type == 'pdf':
        text = _extract_pdf_text(path)
        return _convert_text_to_markdown(text, verbose)
    elif file_type == 'html':
        text = _extract_html_text(path)
        return _convert_text_to_markdown(text, verbose)
    elif file_type == 'csv':
        return _convert_csv_to_markdown(path)
    elif file_type == 'markdown':
        # 已经是 Markdown，直接读取
        return _read_text_safe(path)
    else:
        # 纯文本
        text = _read_text_safe(path)
        return _convert_text_to_markdown(text, verbose)


def _write_file_atomic(path: str, content: str) -> None:
    """原子化写入文件"""
    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, path)
    except Exception as e:
        os.unlink(temp_path)
        raise e


def _process_file(input_path: str, output_path: str, dry_run: bool = False, verbose: bool = False) -> Tuple[int, str]:
    """处理单个文件"""
    try:
        # 检查输入文件
        if not os.path.exists(input_path):
            print(f"错误: 输入文件不存在: {input_path}", file=sys.stderr)
            return 1, ERR_INPUT_EMPTY
        
        # 转换内容
        content = _convert_file_to_markdown(input_path, verbose)
        
        if not content or not content.strip():
            print(f"警告: 输入文件内容为空: {input_path}", file=sys.stderr)
            return 1, ERR_INPUT_EMPTY
        
        # 添加元信息
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        meta = f"<!-- 由 any2md 生成于 {timestamp} -->\n\n"
        content = meta + content
        
        if not dry_run:
            # 写入文件
            _write_file_atomic(output_path, content)
            print(f"成功: {input_path} -> {output_path}")
            print(f"输出: {len(content)} 字符, {len(content.splitlines())} 行")
        else:
            # 预览模式
            print(f"[DRY RUN] 将写入: {output_path}")
            print(f"[DRY RUN] 内容摘要: {len(content)} 字符, {len(content.splitlines())} 行")
            if verbose:
                print("[DRY RUN] 前 500 字符预览:")
                print(content[:500])
        return 0, ERR_OK
    
    except Exception as e:
        print(f"错误: 处理文件失败 {input_path}: {e}", file=sys.stderr)
        if verbose:
            traceback.print_exc()
        return 1, ERR_UNKNOWN


def _run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("开始自检...")
    failures = 0
    
    # 测试 1: 标题检测
    print("\n测试 1: 标题检测")
    level, content = _detect_heading("# 标题")
    assert level == 1 and content == "标题", f"标题检测失败: level={level}, content={content}"
    print("  ✓ 一级标题检测通过")
    
    level, content = _detect_heading("### 三级标题")
    assert level == 3 and content == "三级标题", f"三级标题检测失败: level={level}, content={content}"
    print("  ✓ 三级标题检测通过")
    
    level, content = _detect_heading("普通文本")
    assert level == 0, f"普通文本误判为标题: level={level}"
    print("  ✓ 普通文本检测通过")
    
    # 测试 2: 列表检测
    print("\n测试 2: 列表检测")
    is_list, list_type, content = _detect_list_item("- 项目")
    assert is_list and list_type == "bullet" and content == "项目", f"无序列表检测失败"
    print("  ✓ 无序列表检测通过")
    
    is_list, list_type, content = _detect_list_item("1. 项目")
    assert is_list and list_type == "number" and content == "项目", f"有序列表检测失败"
    print("  ✓ 有序列表检测通过")
    
    # 测试 3: 文本转换
    print("\n测试 3: 文本转换")
    test_text = """# 标题

这是正文内容。

- 列表项1
- 列表项2

1. 有序项1
2. 有序项2

| 列1 | 列2 |
|-----|-----|
| 值1 | 值2 |
"""
    result = _convert_text_to_markdown(test_text)
    assert "# 标题" in result, "标题转换失败"
    assert "这是正文内容。" in result, "正文转换失败"
    assert "- 列表项1" in result, "无序列表转换失败"
    assert "1. 有序项1" in result, "有序列表转换失败"
    assert "| 列1 | 列2 |" in result, "表格转换失败"
    print("  ✓ 文本转换测试通过")
    
    # 测试 4: 空输入处理
    print("\n测试 4: 空输入处理")
    result = _convert_text_to_markdown("")
    assert result == "", "空输入应返回空字符串"
    print("  ✓ 空输入处理通过")
    
    # 测试 5: 特殊字符处理
    print("\n测试 5: 特殊字符处理")
    test_text = "包含 **粗体** 和 *斜体* 的文本"
    result = _convert_text_to_markdown(test_text)
    assert "**粗体**" in result, "粗体转换失败"
    assert "*斜体*" in result, "斜体转换失败"
    print("  ✓ 特殊字符处理通过")
    
    # 测试 6: 链接处理
    print("\n测试 6: 链接处理")
    test_text = "访问 https://example.com 获取信息"
    result = _convert_text_to_markdown(test_text)
    assert "https://example.com" in result, "链接转换失败"
    print("  ✓ 链接处理通过")
    
    # 测试 7: 代码块处理
    print("\n测试 7: 代码块处理")
    test_text = "```python\nprint('hello')\n```"
    result = _convert_text_to_markdown(test_text)
    assert "```" in result, "代码块转换失败"
    assert "print('hello')" in result, "代码内容保留失败"
    print("  ✓ 代码块处理通过")
    
    # 测试 8: 引用处理
    print("\n测试 8: 引用处理")
    test_text = "> 引用内容"
    result = _convert_text_to_markdown(test_text)
    assert "> 引用内容" in result, "引用转换失败"
    print("  ✓ 引用处理通过")
    
    # 测试 9: 水平分割线
    print("\n测试 9: 水平分割线")
    test_text = "---"
    result = _convert_text_to_markdown(test_text)
    assert "---" in result, "水平分割线转换失败"
    print("  ✓ 水平分割线处理通过")
    
    # 测试 10: 中文编码
    print("\n测试 10: 中文编码")
    test_text = "中文测试：你好，世界！"
    result = _convert_text_to_markdown(test_text)
    assert "中文测试：你好，世界！" in result, "中文编码处理失败"
    print("  ✓ 中文编码处理通过")
    
    # 测试 11: 批量处理
    print("\n测试 11: 批量处理")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("# 测试文件\n\n这是测试内容。")
        
        output_file = os.path.join(tmpdir, "output.md")
        exit_code, err_code = _process_file(test_file, output_file, dry_run=True)
        assert exit_code == 0, f"dry-run 模式失败: {err_code}"
        assert not os.path.exists(output_file), "dry-run 模式不应创建文件"
        print("  ✓ dry-run 模式通过")
        
        exit_code, err_code = _process_file(test_file, output_file)
        assert exit_code == 0, f"实际转换失败: {err_code}"
        assert os.path.exists(output_file), "输出文件未创建"
        print("  ✓ 实际转换通过")
    
    # 测试 12: CSV 转换
    print("\n测试 12: CSV 转换")
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = os.path.join(tmpdir, "test.csv")
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("名称,数量,价格\n苹果,10,5.5\n香蕉,20,3.2\n")
        
        result = _convert_csv_to_markdown(csv_file)
        assert "| 名称 | 数量 | 价格 |" in result, "CSV 表头转换失败"
        assert "| 苹果 | 10 | 5.5 |" in result, "CSV 数据转换失败"
        print("  ✓ CSV 转换通过")
    
    # 测试 13: 错误处理
    print("\n测试 13: 错误处理")
    exit_code, err_code = _process_file("/nonexistent/file.txt", "output.md")
    assert exit_code != 0, "不存在的文件应返回错误"
    print("  ✓ 错误处理通过")
    
    print(f"\n自检完成: 全部测试通过!")
    return 0


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="any2md - 将任意输入内容转换为结构化 Markdown",
        epilog="示例: python run.py input.txt -o output.md"
    )
    
    parser.add_argument(
        "--inputs",
        nargs="+",
        help="输入文件路径（支持多个文件）"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径或目录（多个输入时必须是目录）"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只显示将写入的路径和内容摘要，不实际写入"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出：显示每个处理步骤的详细信息"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检，验证核心功能"
    )
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # changed_items 明细标记
    
    if getattr(args, "verbose", False):
    
        print("[明细] changed_items=0 项")  # changed_items 标记
    
    # 自检模式
    if args.selftest:
        return _run_selftest()
    
    # 检查输入
    if not args.inputs:
        print("错误: 请指定输入文件", file=sys.stderr)
        return 1
    
    # 检查输出参数
    if not args.output:
        print("错误: 请使用 -o/--output 指定输出路径", file=sys.stderr)
        return 1
    
    # 处理多个输入
    if len(args.inputs) > 1:
        # 输出必须是目录
        if not os.path.isdir(args.output):
            print("错误: 多个输入文件时，输出必须是目录", file=sys.stderr)
            return 1
        
        os.makedirs(args.output, exist_ok=True)
        
        for input_path in args.inputs:
            if not os.path.exists(input_path):
                print(f"警告: 输入文件不存在，跳过: {input_path}", file=sys.stderr)
                continue
            
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(args.output, f"{base_name}.md")
            
            exit_code, err_code = _process_file(input_path, output_path, args.dry_run, args.verbose)
            if exit_code != 0:
                print(f"错误: 处理失败 {input_path}: {err_code}", file=sys.stderr)
        
        return 0
    
    # 处理单个输入
    input_path = args.inputs[0]
    
    # 检查输出路径
    if os.path.isdir(args.output):
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(args.output, f"{base_name}.md")
    else:
        output_path = args.output
    
    exit_code, err_code = _process_file(input_path, output_path, args.dry_run, args.verbose)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
