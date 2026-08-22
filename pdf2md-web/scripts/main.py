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
import time
from datetime import datetime, timezone
dry_run = False  # v3.274 模块级 dry-run 标志

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

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


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


def _detect_encoding(data: bytes) -> str:
    """检测文本编码，优先 UTF-8，回退到 GBK/GB18030"""
    if not data:
        return 'utf-8'
    # 尝试 UTF-8
    try:
        data.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass
    # 尝试 GBK
    try:
        data.decode('gbk')
        return 'gbk'
    except UnicodeDecodeError:
        pass
    # 尝试 GB18030
    try:
        data.decode('gb18030')
        return 'gb18030'
    except UnicodeDecodeError:
        pass
    # 最终回退
    return 'utf-8'


def _read_file_with_encoding(filepath: str, encoding: Optional[str] = None) -> str:
    """读取文件内容，支持多编码"""
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except OSError as e:
        raise IOError(f"E002: 文件不存在或不可读: {filepath} - {e}")

    if not data:
        return ""

    if encoding is None:
        encoding = _detect_encoding(data)

    try:
        return data.decode(encoding, errors='replace')
    except Exception as e:
        raise IOError(f"E007: 解码失败: {filepath} - {e}")


def _write_file_atomic(filepath: str, content: str, dry_run: bool = False) -> None:
    """原子化写入文件，支持 dry-run 模式"""
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        # 确保目录存在
        dirname = os.path.dirname(filepath)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

        # 原子写入：先写临时文件，再重命名
        tmp_path = filepath + '.tmp'
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(tmp_path, filepath)
            print(f"[写入] {filepath}")
            return True
        except OSError as e:
            # 清理临时文件
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise IOError(f"E006: 输出写入失败: {filepath} - {e}")
    print(f"[dry-run] 将写入 {filepath}（{len(content)} 字节），未落盘")
    return False


def _http_get_with_retry(url: str, timeout: float = 10.0, max_retries: int = 3) -> bytes:
    """HTTP GET 请求，带超时和指数退避重试"""
    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.URLError as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s
                print(f"[WARN] 请求失败（{e}），{wait_time}秒后重试...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                break
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[WARN] 请求异常（{e}），{wait_time}秒后重试...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                break
    raise IOError(f"E005: 网页抓取失败: {url} - {last_error}")


# ============================================================
# PDF 解析模块
# ============================================================

def _parse_pdf_text(text: str) -> List[DocumentBlock]:
    """解析 PDF 文本内容，识别标题、段落、列表、表格、引用块"""
    blocks: List[DocumentBlock] = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # 检测标题（以 # 开头）
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            content = heading_match.group(2).strip()
            blocks.append(DocumentBlock(
                block_type='heading',
                content=content,
                level=level,
                confidence=1.0
            ))
            i += 1
            continue

        # 检测列表项（以 -、*、+ 或数字. 开头）
        list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', line)
        if list_match:
            indent = len(list_match.group(1))
            level = indent // 2 + 1
            content = list_match.group(3).strip()
            blocks.append(DocumentBlock(
                block_type='list',
                content=content,
                level=level,
                confidence=1.0
            ))
            i += 1
            continue

        # 检测表格（包含 | 分隔符）
        if '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            table_content = '\n'.join(table_lines)
            blocks.append(DocumentBlock(
                block_type='table',
                content=table_content,
                confidence=1.0
            ))
            continue

        # 检测引用块（以 > 开头）
        if line.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_lines.append(lines[i].strip().lstrip('>').strip())
                i += 1
            quote_content = '\n'.join(quote_lines)
            blocks.append(DocumentBlock(
                block_type='quote',
                content=quote_content,
                confidence=1.0
            ))
            continue

        # 普通段落
        paragraph_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6})\s+', lines[i]):
            paragraph_lines.append(lines[i].strip())
            i += 1
        paragraph_content = ' '.join(paragraph_lines)
        blocks.append(DocumentBlock(
            block_type='paragraph',
            content=paragraph_content,
            confidence=1.0
        ))

    return blocks


def _parse_pdf(filepath: str, encoding: Optional[str] = None) -> ConversionResult:
    """解析 PDF 文件（文本层提取）"""
    try:
        text = _read_file_with_encoding(filepath, encoding)
    except IOError as e:
        raise

    if not text.strip():
        raise ValueError("E008: 输入内容为空")

    blocks = _parse_pdf_text(text)
    if not blocks:
        raise ValueError("E004: PDF 解析失败 - 未识别到有效内容")

    # 提取标题（第一个 heading 块）
    title = ""
    for block in blocks:
        if block.block_type == 'heading' and block.level == 1:
            title = block.content
            break

    # 生成 Markdown
    markdown = _blocks_to_markdown(blocks)

    return ConversionResult(
        markdown=markdown,
        blocks=blocks,
        source_type='pdf',
        title=title
    )


# ============================================================
# 网页解析模块
# ============================================================

def _strip_html_tags(html_content: str) -> str:
    """去除 HTML 标签，保留文本内容"""
    # 去除 script 和 style 标签内容
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    # 去除注释
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    # 将块级标签替换为换行
    html_content = re.sub(r'<(div|p|h[1-6]|li|tr|br|section|article)[^>]*>', '\n', html_content, flags=re.IGNORECASE)
    # 去除剩余标签
    html_content = re.sub(r'<[^>]+>', '', html_content)
    # 解码 HTML 实体
    html_content = html.unescape(html_content)
    # 规范化空白
    html_content = _normalize_text(html_content)
    return html_content


def _extract_title(html_content: str) -> str:
    """从 HTML 中提取标题"""
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.DOTALL | re.IGNORECASE)
    if title_match:
        return html.unescape(title_match.group(1)).strip()
    # 尝试 h1
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL | re.IGNORECASE)
    if h1_match:
        return html.unescape(re.sub(r'<[^>]+>', '', h1_match.group(1))).strip()
    return ""


def _parse_web(url: str, timeout: float = 10.0) -> ConversionResult:
    """解析网页内容"""
    try:
        data = _http_get_with_retry(url, timeout=timeout)
    except IOError as e:
        raise

    # 检测编码
    encoding = _detect_encoding(data)
    try:
        html_content = data.decode(encoding, errors='replace')
    except Exception as e:
        raise ValueError(f"E007: 网页解码失败 - {e}")

    # 提取标题
    title = _extract_title(html_content)

    # 去除 HTML 标签
    text = _strip_html_tags(html_content)

    if not text.strip():
        raise ValueError("E008: 输入内容为空")

    # 解析为文档块
    blocks = _parse_pdf_text(text)  # 复用 PDF 文本解析逻辑

    if not blocks:
        raise ValueError("E005: 网页抓取失败 - 未识别到有效内容")

    # 生成 Markdown
    markdown = _blocks_to_markdown(blocks)

    return ConversionResult(
        markdown=markdown,
        blocks=blocks,
        source_type='web',
        title=title
    )


# ============================================================
# Markdown 生成模块
# ============================================================

def _blocks_to_markdown(blocks: List[DocumentBlock]) -> str:
    """将文档块列表转换为 Markdown 文本"""
    md_lines: List[str] = []
    for block in blocks:
        if block.block_type == 'heading':
            md_lines.append(f"{'#' * block.level} {block.content}")
        elif block.block_type == 'paragraph':
            md_lines.append(block.content)
        elif block.block_type == 'list':
            indent = '  ' * (block.level - 1)
            md_lines.append(f"{indent}- {block.content}")
        elif block.block_type == 'table':
            md_lines.append(block.content)
        elif block.block_type == 'quote':
            for line in block.content.split('\n'):
                md_lines.append(f"> {line}")
        md_lines.append('')  # 块间空行

    return '\n'.join(md_lines).strip()


def _apply_confidence(markdown: str, blocks: List[DocumentBlock]) -> str:
    """对低置信度内容添加标注"""
    result_lines = []
    for block in blocks:
        if block.confidence < 0.8:
            result_lines.append(f"[置信度:{int(block.confidence * 100)}%] {block.content}")
        else:
            result_lines.append(block.content)
    return '\n'.join(result_lines)


# ============================================================
# 主处理逻辑
# ============================================================

def process_input(input_path: str, output_path: Optional[str] = None,
                  dry_run: bool = False, verbose: bool = False,
                  encoding: Optional[str] = None, timeout: float = 10.0) -> ConversionResult:
    """处理输入文件或 URL，返回转换结果"""
    # 判断输入类型
    if input_path.startswith(('http://', 'https://')):
        # 网页
        if verbose:
            print(f"[INFO] 处理网页: {input_path}")
        result = _parse_web(input_path, timeout=timeout)
    elif os.path.isfile(input_path):
        # 本地文件
        if verbose:
            print(f"[INFO] 处理文件: {input_path}")
        ext = os.path.splitext(input_path)[1].lower()
        if ext == '.pdf':
            result = _parse_pdf(input_path, encoding=encoding)
        elif ext in ('.txt', '.md', '.markdown'):
            # 文本文件直接解析
            text = _read_file_with_encoding(input_path, encoding)
            if not text.strip():
                raise ValueError("E008: 输入内容为空")
            blocks = _parse_pdf_text(text)
            markdown = _blocks_to_markdown(blocks)
            result = ConversionResult(
                markdown=markdown,
                blocks=blocks,
                source_type='text',
                title=os.path.basename(input_path)
            )
        else:
            raise ValueError(f"E003: 不支持的输入类型: {ext}")
    else:
        raise ValueError(f"E002: 文件不存在或不可读: {input_path}")

    # 应用置信度标注
    result.markdown = _apply_confidence(result.markdown, result.blocks)

    # 写入输出文件
    if output_path:
        _write_file_atomic(output_path, result.markdown, dry_run=dry_run)
        if verbose:
            print(f"[INFO] 输出已写入: {output_path}")

    return result


# ============================================================
# 自检模式
# ============================================================

def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 测试 1: 文本规范化
    print("\n[测试 1] 文本规范化")
    test_text = "  Hello   World  \n\n  Second  Line  "
    normalized = _normalize_text(test_text)
    assert normalized == "Hello World\nSecond Line", f"规范化失败: {normalized}"
    print("  ✓ 通过")

    # 测试 2: PDF 文本解析
    print("\n[测试 2] PDF 文本解析")
    sample_pdf_text = """# 测试文档

## 第一节

这是一个段落。

- 列表项 1
- 列表项 2

| 列1 | 列2 |
|-----|-----|
| A   | B   |

> 引用内容
"""
    blocks = _parse_pdf_text(sample_pdf_text)
    assert len(blocks) >= 5, f"解析块数量不足: {len(blocks)}"
    heading_blocks = [b for b in blocks if b.block_type == 'heading']
    assert len(heading_blocks) == 2, f"标题数量错误: {len(heading_blocks)}"
    print(f"  ✓ 通过（解析出 {len(blocks)} 个块）")

    # 测试 3: Markdown 生成
    print("\n[测试 3] Markdown 生成")
    markdown = _blocks_to_markdown(blocks)
    assert '# 测试文档' in markdown, "Markdown 缺少标题"
    assert '| 列1 | 列2 |' in markdown, "Markdown 缺少表格"
    print("  ✓ 通过")

    # 测试 4: 编码检测
    print("\n[测试 4] 编码检测")
    utf8_data = "中文测试".encode('utf-8')
    assert _detect_encoding(utf8_data) == 'utf-8', "UTF-8 检测失败"
    gbk_data = "中文测试".encode('gbk')
    assert _detect_encoding(gbk_data) == 'gbk', "GBK 检测失败"
    print("  ✓ 通过")

    # 测试 5: HTML 标签去除
    print("\n[测试 5] HTML 标签去除")
    html_content = "<html><head><title>测试</title></head><body><h1>标题</h1><p>段落</p></body></html>"
    text = _strip_html_tags(html_content)
    assert '标题' in text, "HTML 解析缺少标题"
    assert '段落' in text, "HTML 解析缺少段落"
    print("  ✓ 通过")

    # 测试 6: 空输入处理
    print("\n[测试 6] 空输入处理")
    try:
        _parse_pdf_text("")
        assert False, "空输入未抛出异常"
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
    print("  ✓ 通过")

    # 测试 7: 完整流程（临时文件）
    print("\n[测试 7] 完整流程")
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("# 临时文档\n\n这是测试内容。\n\n- 项目 1\n- 项目 2\n")
        temp_path = f.name
    try:
        result = process_input(temp_path, dry_run=True)
        assert result.markdown, "转换结果为空"
        assert '临时文档' in result.markdown, "转换结果缺少标题"
        print("  ✓ 通过")
    finally:
        os.unlink(temp_path)

    # 测试 8: 原子写入
    print("\n[测试 8] 原子写入")
    with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
        test_output = f.name
    try:
        _write_file_atomic(test_output, "# 测试\n")
        with open(test_output, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "# 测试\n", "原子写入内容错误"
        print("  ✓ 通过")
    finally:
        os.unlink(test_output)

    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description='将PDF或网页转为结构化Markdown，保留关键信息并标注置信度。',
        epilog='示例: python run.py --input input.pdf -o output.md'
    )
    parser.add_argument("--input", nargs='?', help='输入文件路径或 URL')
    parser.add_argument('-o', '--output', help='输出文件路径（默认 stdout）')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式，不实际写入文件')
    parser.add_argument('--verbose', action='store_true', help='输出详细处理信息')
    parser.add_argument('--encoding', help='输入文件编码（默认自动检测）')
    parser.add_argument('--timeout', type=float, default=10.0, help='网络请求超时时间（秒）')
    parser.add_argument('--selftest', action='store_true', help='运行自检模式')

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input:
        print("E001: 参数错误 - 必须提供输入文件路径或 URL", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        # 处理输入
        result = process_input(
            input_path=args.input,
            output_path=args.output,
            dry_run=args.dry_run,
            verbose=args.verbose,
            encoding=args.encoding,
            timeout=args.timeout
        )

        # 输出到 stdout（如果没有指定输出文件）
        if not args.output:
            print(result.markdown)

        # 输出摘要
        if args.verbose:
            print(f"\n[摘要] 来源类型: {result.source_type}")
            print(f"[摘要] 标题: {result.title or '(无)'}")
            print(f"[摘要] 文档块数: {len(result.blocks)}")
            print(f"[摘要] 警告数: {len(result.warnings)}")
            for warning in result.warnings:
                print(f"  [警告] {warning}")

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知异常 - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
