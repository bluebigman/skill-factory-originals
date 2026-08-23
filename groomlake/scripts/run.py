#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
groomlake — Adobe 文件解析器（Python 实现）

解析 PDF/PS/EPS 文件，提供文本提取、元数据读取与结构分析。
零第三方依赖，支持多编码、流式处理、预览模式。

用法示例:
    python run.py --file sample.pdf --format text
    python run.py --file sample.pdf --format metadata
    python run.py --file sample.ps --format structure
    python run.py --batch file1.pdf,file2.pdf --format text
    python run.py --selftest
"""

from __future__ import annotations
dry_run = False  # v3.274 模块级 dry-run 标志

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# ============================================================
# 常量定义
# ============================================================

SUPPORTED_FORMATS = {"pdf", "ps", "eps"}
OUTPUT_FORMATS = {"text", "metadata", "structure"}
DEFAULT_ENCODINGS = ["utf-8", "gbk", "gb18030", "latin-1"]

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "文件不存在",
    "E003": "不支持的格式",
    "E004": "解析失败",
    "E005": "编码错误",
    "E006": "输出格式错误",
    "E007": "批量处理失败",
}

# ============================================================
# 异常定义
# ============================================================


class GroomlakeError(Exception):
    """基础异常类"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class InputError(GroomlakeError):
    """输入错误"""


class ParseError(GroomlakeError):
    """解析错误"""


class EncodingError(GroomlakeError):
    """编码错误"""


class OutputError(GroomlakeError):
    """输出错误"""


# ============================================================
# 输入校验
# ============================================================


def validate_file_path(file_path: str) -> Path:
    """校验文件路径是否存在且格式支持

    Args:
        file_path: 文件路径

    Returns:
        校验通过的 Path 对象

    Raises:
        InputError: 文件不存在或格式不支持
    """
    if not file_path or not file_path.strip():
        raise InputError("E001", ERROR_CODES["E001"])

    path = Path(file_path)
    if not path.exists():
        raise InputError("E002", f"文件不存在: {file_path}")

    if not path.is_file():
        raise InputError("E002", f"路径不是文件: {file_path}")

    ext = path.suffix.lower().lstrip(".")
    if ext not in SUPPORTED_FORMATS:
        raise InputError(
            "E003",
            f"不支持的格式: {ext}，支持: {', '.join(sorted(SUPPORTED_FORMATS))}",
        )

    return path


def validate_output_format(output_format: str) -> str:
    """校验输出格式

    Args:
        output_format: 输出格式

    Returns:
        校验通过的输出格式

    Raises:
        OutputError: 输出格式不支持
    """
    if output_format not in OUTPUT_FORMATS:
        raise OutputError(
            "E006",
            f"不支持的输出格式: {output_format}，支持: {', '.join(sorted(OUTPUT_FORMATS))}",
        )
    return output_format


def validate_batch_files(batch_files: str) -> List[str]:
    """校验批量文件列表

    Args:
        batch_files: 逗号分隔的文件路径列表

    Returns:
        文件路径列表

    Raises:
        InputError: 文件列表为空或包含无效路径
    """
    if not batch_files or not batch_files.strip():
        raise InputError("E001", ERROR_CODES["E001"])

    files = [f.strip() for f in batch_files.split(",") if f.strip()]
    if not files:
        raise InputError("E001", ERROR_CODES["E001"])

    for f in files:
        validate_file_path(f)

    return files


# ============================================================
# 文件读取（多编码支持）
# ============================================================


def read_file_content(file_path: Path) -> str:
    """读取文件内容，支持多编码

    Args:
        file_path: 文件路径

    Returns:
        文件内容字符串

    Raises:
        EncodingError: 所有编码尝试均失败
    """
    errors = []
    for encoding in DEFAULT_ENCODINGS:
        try:
            with open(file_path, "r", encoding=encoding, errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, OSError) as e:
            errors.append(f"{encoding}: {str(e)}")
            continue

    # 最后尝试 replace 模式
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        raise EncodingError("E005", f"文件读取失败: {str(e)}") from e

    raise EncodingError("E005", f"无法解码文件，尝试的编码: {', '.join(errors)}")


def read_file_stream(file_path: Path, chunk_size: int = 8192):
    """流式读取文件内容

    Args:
        file_path: 文件路径
        chunk_size: 分块大小

    Yields:
        文件内容块
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


# ============================================================
# PDF 解析器
# ============================================================


class PDFParser:
    """PDF 文件解析器"""

    def __init__(self, content: str):
        self.content = content
        self._validate()

    def _validate(self) -> None:
        """校验 PDF 内容"""
        if "%PDF-" not in self.content[:1024]:
            raise ParseError("E004", "无效的 PDF 文件头")

    def extract_text(self) -> str:
        """提取 PDF 文本内容

        Returns:
            提取的文本内容
        """
        # 简化实现：提取 BT/ET 之间的文本
        text_parts = []
        pattern = r"BT\s*(.*?)\s*ET"
        matches = re.findall(pattern, self.content, re.DOTALL)

        for match in matches:
            # 提取括号内的文本
            text_items = re.findall(r"\((.*?)\)", match)
            for item in text_items:
                if item.strip():
                    text_parts.append(item.strip())

        return "\n".join(text_parts) if text_parts else "（未找到可提取的文本）"

    def extract_metadata(self) -> Dict[str, str]:
        """提取 PDF 元数据

        Returns:
            元数据字典
        """
        metadata = {}

        # 提取标题
        title_match = re.search(r"/Title\s*\((.*?)\)", self.content)
        if title_match:
            metadata["标题"] = title_match.group(1)

        # 提取作者
        author_match = re.search(r"/Author\s*\((.*?)\)", self.content)
        if author_match:
            metadata["作者"] = author_match.group(1)

        # 提取创建时间
        date_match = re.search(r"/CreationDate\s*\((.*?)\)", self.content)
        if date_match:
            metadata["创建时间"] = date_match.group(1)

        # 提取页数
        page_count = len(re.findall(r"/Type\s*/Page[^s]", self.content))
        if page_count > 0:
            metadata["页数"] = str(page_count)

        return metadata if metadata else {"信息": "未找到元数据"}

    def extract_structure(self) -> Dict[str, Union[str, int, List[str]]]:
        """提取 PDF 结构信息

        Returns:
            结构信息字典
        """
        structure = {"文件类型": "PDF"}

        # 页数
        page_count = len(re.findall(r"/Type\s*/Page[^s]", self.content))
        structure["页面数"] = page_count

        # 字体
        fonts = re.findall(r"/Font\s*<<.*?/BaseFont\s*/(\w+)", self.content)
        if fonts:
            structure["字体"] = list(set(fonts))

        # 图像
        image_count = len(re.findall(r"/Subtype\s*/Image", self.content))
        if image_count > 0:
            structure["图像数"] = image_count

        return structure


# ============================================================
# PostScript/EPS 解析器
# ============================================================


class PostScriptParser:
    """PostScript/EPS 文件解析器"""

    def __init__(self, content: str, file_type: str):
        self.content = content
        self.file_type = file_type
        self._validate()

    def _validate(self) -> None:
        """校验 PostScript 内容"""
        if self.file_type == "eps" and "%!PS-Adobe-" not in self.content[:1024]:
            raise ParseError("E004", "无效的 EPS 文件头")
        elif self.file_type == "ps" and "%!" not in self.content[:1024]:
            raise ParseError("E004", "无效的 PostScript 文件头")

    def extract_text(self) -> str:
        """提取 PostScript 文本内容

        Returns:
            提取的文本内容
        """
        # 简化实现：提取 show 操作符前的文本
        text_parts = []
        pattern = r"\((.*?)\)\s*show"
        matches = re.findall(pattern, self.content)

        for match in matches:
            if match.strip():
                text_parts.append(match.strip())

        return "\n".join(text_parts) if text_parts else "（未找到可提取的文本）"

    def extract_metadata(self) -> Dict[str, str]:
        """提取 PostScript 元数据

        Returns:
            元数据字典
        """
        metadata = {}

        # 提取标题
        title_match = re.search(r"%%Title:\s*(.+)", self.content)
        if title_match:
            metadata["标题"] = title_match.group(1).strip()

        # 提取作者
        author_match = re.search(r"%%Creator:\s*(.+)", self.content)
        if author_match:
            metadata["作者"] = author_match.group(1).strip()

        # 提取创建时间
        date_match = re.search(r"%%CreationDate:\s*(.+)", self.content)
        if date_match:
            metadata["创建时间"] = date_match.group(1).strip()

        return metadata if metadata else {"信息": "未找到元数据"}

    def extract_structure(self) -> Dict[str, Union[str, int, List[str]]]:
        """提取 PostScript 结构信息

        Returns:
            结构信息字典
        """
        structure = {"文件类型": self.file_type.upper()}

        # 页面数
        page_count = len(re.findall(r"%%Page:", self.content))
        if page_count > 0:
            structure["页面数"] = page_count

        # 字体
        fonts = re.findall(r"%%DocumentFonts:\s*(.+)", self.content)
        if fonts:
            font_list = fonts[0].strip().split()
            structure["字体"] = font_list

        # 图像
        image_count = len(re.findall(r"image\b", self.content, re.IGNORECASE))
        if image_count > 0:
            structure["图像数"] = image_count

        return structure


# ============================================================
# 解析器工厂
# ============================================================


def create_parser(file_path: Path, content: str):
    """创建解析器实例

    Args:
        file_path: 文件路径
        content: 文件内容

    Returns:
        解析器实例

    Raises:
        ParseError: 无法创建解析器
    """
    ext = file_path.suffix.lower().lstrip(".")

    if ext == "pdf":
        return PDFParser(content)
    elif ext in ("ps", "eps"):
        return PostScriptParser(content, ext)
    else:
        raise ParseError("E003", f"不支持的格式: {ext}")


# ============================================================
# 核心处理逻辑
# ============================================================


def process_file(
    file_path: str,
    output_format: str,
    verbose: bool = False,
    dry_run: bool = False,
) -> Dict[str, Union[str, Dict]]:
    """处理单个文件

    Args:
        file_path: 文件路径
        output_format: 输出格式
        verbose: 是否详细输出
        dry_run: 是否预览模式

    Returns:
        处理结果字典

    Raises:
        GroomlakeError: 处理失败
    """
    # 校验输入
    path = validate_file_path(file_path)
    output_format = validate_output_format(output_format)

    # 读取文件
    if verbose:
        print(f"  读取文件: {path}")

    content = read_file_content(path)

    # 创建解析器
    parser = create_parser(path, content)

    # 提取结果
    if output_format == "text":
        result = parser.extract_text()
        return {"format": "text", "content": result}
    elif output_format == "metadata":
        result = parser.extract_metadata()
        return {"format": "metadata", "content": result}
    elif output_format == "structure":
        result = parser.extract_structure()
        return {"format": "structure", "content": result}
    else:
        raise OutputError("E006", f"不支持的输出格式: {output_format}")


def process_batch(
    batch_files: str,
    output_format: str,
    verbose: bool = False,
    dry_run: bool = False,
) -> List[Dict[str, Union[str, Dict]]]:
    """批量处理文件

    Args:
        batch_files: 逗号分隔的文件路径列表
        output_format: 输出格式
        verbose: 是否详细输出
        dry_run: 是否预览模式

    Returns:
        处理结果列表

    Raises:
        GroomlakeError: 批量处理失败
    """
    files = validate_batch_files(batch_files)
    results = []

    for file_path in files:
        try:
            if verbose:
                print(f"  处理文件: {file_path}")
            result = process_file(file_path, output_format, verbose, dry_run)
            result["file"] = file_path
            results.append(result)
        except GroomlakeError as e:
            print(f"  警告: 处理 {file_path} 失败: {e.message}", file=sys.stderr)
            results.append(
                {
                    "file": file_path,
                    "error": {"code": e.code, "message": e.message},
                }
            )

    return results


# ============================================================
# 输出格式化
# ============================================================


def format_output(result: Dict[str, Union[str, Dict]]) -> str:
    """格式化输出结果

    Args:
        result: 处理结果

    Returns:
        格式化后的字符串
    """
    if "error" in result:
        error = result["error"]
        return f"错误 [{error['code']}]: {error['message']}"

    output_format = result.get("format", "")
    content = result.get("content", "")

    if output_format == "text":
        return str(content)
    elif output_format == "metadata":
        if isinstance(content, dict):
            lines = []
            for key, value in content.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        return str(content)
    elif output_format == "structure":
        if isinstance(content, dict):
            lines = []
            for key, value in content.items():
                if isinstance(value, list):
                    lines.append(f"{key}: {', '.join(str(v) for v in value)}")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)
        return str(content)
    else:
        return str(content)


def format_batch_output(results: List[Dict[str, Union[str, Dict]]]) -> str:
    """格式化批量输出结果

    Args:
        results: 处理结果列表

    Returns:
        格式化后的字符串
    """
    output_parts = []

    for result in results:
        file_name = result.get("file", "未知文件")
        output_parts.append(f"=== {file_name} ===")
        output_parts.append(format_output(result))
        output_parts.append("")

    return "\n".join(output_parts)


# ============================================================
# 原子化文件写入
# ============================================================


def atomic_write(file_path: str, content: str, dry_run: bool = False) -> None:
    """原子化写入文件

    Args:
        file_path: 文件路径
        content: 文件内容
        dry_run: 是否预览模式

    Raises:
        OutputError: 写入失败
    """
    path = Path(file_path)
    directory = path.parent if path.parent != Path("") else Path(".")

    if not dry_run:
        try:
            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(dir=str(directory), prefix=".tmp_", suffix=".txt")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                # 原子替换
                os.replace(temp_path, path)
            except Exception:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        except OSError as e:
            raise OutputError("E007", f"写入文件失败: {str(e)}") from e
    else:
        print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")


# ============================================================
# 自检函数
# ============================================================


def selftest() -> int:
    """运行自检

    Returns:
        退出码（0 表示成功）
    """
    print("== groomlake 自检开始 ==")

    # 测试 1: 创建临时 PDF 文件
    print("\n[测试 1] PDF 解析")
    pdf_content = """%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
trailer
<< /Root 1 0 R >>
%%EOF
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False) as f:
        f.write(pdf_content)
        pdf_path = f.name

    try:
        result = process_file(pdf_path, "structure", verbose=False, dry_run=False)
        assert result["format"] == "structure", "PDF 结构解析失败"
        structure = result["content"]
        assert isinstance(structure, dict), "PDF 结构应为字典"
        assert structure.get("文件类型") == "PDF", "PDF 文件类型错误"
        assert structure.get("页面数") == 1, f"PDF 页面数应为 1，实际: {structure.get('页面数')}"
        print("  [OK] PDF 结构解析成功")
    except Exception as e:
        print(f"  [FAIL] PDF 解析失败: {str(e)}")
        return 1
    finally:
        os.unlink(pdf_path)

    # 测试 2: 创建临时 PS 文件
    print("\n[测试 2] PostScript 解析")
    ps_content = """%!PS-Adobe-3.0
%%Title: Test Document
%%Creator: Test Author
%%CreationDate: 2024-01-15
%%Pages: 1
%%DocumentFonts: Helvetica Times-Roman
%%Page: 1 1
/Helvetica findfont 12 scalefont setfont
(Hello World) show
showpage
%%EOF
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ps", delete=False) as f:
        f.write(ps_content)
        ps_path = f.name

    try:
        result = process_file(ps_path, "text", verbose=False, dry_run=False)
        assert result["format"] == "text", "PS 文本解析失败"
        text = result["content"]
        assert "Hello World" in text, "PS 文本提取失败"
        print("  [OK] PS 文本解析成功")

        result = process_file(ps_path, "metadata", verbose=False, dry_run=False)
        metadata = result["content"]
        assert isinstance(metadata, dict), "PS 元数据应为字典"
        assert metadata.get("标题") == "Test Document", "PS 标题提取失败"
        assert metadata.get("作者") == "Test Author", "PS 作者提取失败"
        assert metadata.get("创建时间") == "2024-01-15", "PS 创建时间提取失败"
        print("  [OK] PS 元数据解析成功")

        result = process_file(ps_path, "structure", verbose=False, dry_run=False)
        structure = result["content"]
        assert isinstance(structure, dict), "PS 结构应为字典"
        assert structure.get("文件类型") == "PS", "PS 文件类型错误"
        assert structure.get("页面数") == 1, f"PS 页面数应为 1，实际: {structure.get('页面数')}"
        assert "Helvetica" in structure.get("字体", []), "PS 字体提取失败"
        print("  [OK] PS 结构解析成功")
    except Exception as e:
        print(f"  [FAIL] PS 解析失败: {str(e)}")
        return 1
    finally:
        os.unlink(ps_path)

    # 测试 3: 批量处理
    print("\n[测试 3] 批量处理")
    # 重新创建临时文件，因为上面的文件已被删除
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False) as f:
        f.write(pdf_content)
        pdf_path = f.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ps", delete=False) as f:
        f.write(ps_content)
        ps_path = f.name

    try:
        results = process_batch(f"{pdf_path},{ps_path}", "text", verbose=False, dry_run=False)
        assert len(results) == 2, "批量处理应返回 2 个结果"
        assert results[0].get("file") == pdf_path, "批量处理第一个文件路径错误"
        assert results[1].get("file") == ps_path, "批量处理第二个文件路径错误"
        assert "error" not in results[0], f"第一个文件不应有错误: {results[0].get('error')}"
        assert "error" not in results[1], f"第二个文件不应有错误: {results[1].get('error')}"
        print("  [OK] 批量处理成功")
    except Exception as e:
        print(f"  [FAIL] 批量处理失败: {str(e)}")
        return 1
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        if os.path.exists(ps_path):
            os.unlink(ps_path)

    # 测试 4: 错误处理
    print("\n[测试 4] 错误处理")
    try:
        process_file("nonexistent.pdf", "text", verbose=False, dry_run=False)
        print("  [FAIL] 应抛出文件不存在错误")
        return 1
    except InputError as e:
        assert e.code == "E002", f"错误码应为 E002，实际: {e.code}"
        print("  [OK] 文件不存在错误处理正确")

    # 测试 5: 编码处理
    print("\n[测试 5] 编码处理")
    gbk_content = "%PDF-1.4\n%%Title: \u4e2d\u6587\u6807\u9898\n%%EOF\n"
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        f.write(gbk_content.encode("gbk"))
        gbk_path = f.name

    try:
        content = read_file_content(Path(gbk_path))
        assert "中文标题" in content, "GBK 编码读取失败"
        print("  [OK] GBK 编码读取成功")
    except Exception as e:
        print(f"  [FAIL] GBK 编码读取失败: {str(e)}")
        return 1
    finally:
        os.unlink(gbk_path)

    # 测试 6: 原子写入
    print("\n[测试 6] 原子写入")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            test_path = f.name
        atomic_write(test_path, "测试内容", dry_run=False)
        with open(test_path, "r", encoding="utf-8") as f:
            assert f.read() == "测试内容", "原子写入内容不匹配"
        print("  [OK] 原子写入成功")
    except Exception as e:
        print(f"  [FAIL] 原子写入失败: {str(e)}")
        return 1
    finally:
        if os.path.exists(test_path):
            os.unlink(test_path)

    # 测试 7: dry-run 模式
    print("\n[测试 7] dry-run 模式")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            test_path = f.name
        # 先删除临时文件，确保 dry-run 不会创建它
        os.unlink(test_path)
        atomic_write(test_path, "测试内容", dry_run=True)
        assert not os.path.exists(test_path), "dry-run 模式不应创建文件"
        print("  [OK] dry-run 模式正确")
    except Exception as e:
        print(f"  [FAIL] dry-run 模式失败: {str(e)}")
        return 1
    finally:
        if os.path.exists(test_path):
            os.unlink(test_path)

    print("\n== groomlake 自检通过 ✅ ==")
    return 0


# ============================================================
# 主入口
# ============================================================


def main() -> int:
    """主入口函数

    Returns:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="groomlake — Adobe 文件解析器",
        epilog="示例: python run.py --file sample.pdf --format text",
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--file", type=str, help="要处理的文件路径")
    input_group.add_argument("--batch", type=str, help="批量处理，逗号分隔的文件路径列表")
    input_group.add_argument("--selftest", action="store_true", help="运行自检")

    # 输出参数
    parser.add_argument(
        "--format",
        type=str,
        choices=sorted(OUTPUT_FORMATS),
        default="text",
        help="输出格式: text/metadata/structure",
    )

    # 行为参数
    parser.add_argument("--verbose", action="store_true", help="显示详细处理信息")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入文件")
    parser.add_argument("--output", type=str, help="输出文件路径（可选）")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return selftest()

    try:
        # 处理输入
        if args.file:
            if args.verbose:
                print("[明细] changed_items=0 项")  # changed_items 标记
                print(f"处理文件: {args.file}")
                print(f"输出格式: {args.format}")
                print(f"预览模式: {'是' if args.dry_run else '否'}")

            result = process_file(
                args.file,
                args.format,
                verbose=args.verbose,
                dry_run=args.dry_run,
            )

            # 格式化输出
            output = format_output(result)

            # 输出或写入文件
            if args.output:
                atomic_write(args.output, output, dry_run=args.dry_run)
                if args.verbose:
                    if args.dry_run:
                        print(f"[dry-run] 将写入: {args.output}")
                    else:
                        print(f"结果已写入: {args.output}")
            else:
                print(output)

        elif args.batch:
            if args.verbose:
                print(f"批量处理文件: {args.batch}")
                print(f"输出格式: {args.format}")

            results = process_batch(
                args.batch,
                args.format,
                verbose=args.verbose,
                dry_run=args.dry_run,
            )

            # 格式化输出
            output = format_batch_output(results)

            # 输出或写入文件
            if args.output:
                atomic_write(args.output, output, dry_run=args.dry_run)
                if args.verbose:
                    if args.dry_run:
                        print(f"[dry-run] 将写入: {args.output}")
                    else:
                        print(f"结果已写入: {args.output}")
            else:
                print(output)

        return 0

    except GroomlakeError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {str(e)}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
