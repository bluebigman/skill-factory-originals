#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
micro-editor 终端文本编辑器 - 独立实现脚本
==========================================
依据功能规格独立重写，仅使用 Python 标准库。
提供基础编辑、搜索、行号显示、语法高亮占位等核心能力。

用法:
    python scripts/main.py <文件路径>            # 打开/编辑文件
    python scripts/main.py --selftest           # 离线自检核心逻辑
"""

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义 (E001-E010)
ERR_FILE_NOT_FOUND = "E001"      # 输入文件不存在
ERR_FILE_PERMISSION = "E002"     # 文件权限不足
ERR_INVALID_FORMAT = "E003"      # 文件格式不支持
ERR_WRITE_FAILED = "E004"        # 写入输出失败
ERR_INVALID_ARG = "E005"         # 命令行参数错误
ERR_INTERNAL = "E006"            # 内部逻辑错误
ERR_EMPTY_CONTENT = "E007"       # 内容为空
ERR_IO_TIMEOUT = "E008"          # IO 超时
ERR_RETRY_EXHAUSTED = "E009"     # 重试耗尽
ERR_SELFTEST_FAILED = "E010"     # 自检失败


# ============================================================
# 核心数据结构
# ============================================================

@dataclass
class Document:
    """文档模型：行列表 + 光标位置"""
    lines: List[str] = field(default_factory=lambda: [""])
    cursor_row: int = 0
    cursor_col: int = 0

    def current_line(self) -> str:
        """获取当前光标所在行"""
        if 0 <= self.cursor_row < len(self.lines):
            return self.lines[self.cursor_row]
        return ""

    def move_cursor(self, d_row: int, d_col: int) -> None:
        """移动光标，自动夹取边界"""
        new_row = max(0, min(self.cursor_row + d_row, len(self.lines) - 1))
        self.cursor_row = new_row
        line_len = len(self.lines[new_row])
        self.cursor_col = max(0, min(self.cursor_col + d_col, line_len))

    def insert_text(self, text: str) -> None:
        """在当前光标位置插入文本（支持多行）"""
        if not text:
            return
        # 拆分多行输入
        parts = text.split("\n")
        line = self.lines[self.cursor_row]
        # 第一段插入当前行
        self.lines[self.cursor_row] = line[:self.cursor_col] + parts[0] + line[self.cursor_col:]
        self.cursor_col += len(parts[0])
        # 后续段插入新行
        for part in parts[1:]:
            self.cursor_row += 1
            self.lines.insert(self.cursor_row, part + line[self.cursor_col:])
            self.cursor_col = len(part)

    def delete_char(self) -> bool:
        """删除光标前一个字符，返回是否执行了删除"""
        if self.cursor_col > 0:
            line = self.lines[self.cursor_row]
            self.lines[self.cursor_row] = line[:self.cursor_col - 1] + line[self.cursor_col:]
            self.cursor_col -= 1
            return True
        elif self.cursor_row > 0:
            # 合并到上一行
            prev_line = self.lines[self.cursor_row - 1]
            curr_line = self.lines[self.cursor_row]
            self.lines[self.cursor_row - 1] = prev_line + curr_line
            self.lines.pop(self.cursor_row)
            self.cursor_row -= 1
            self.cursor_col = len(prev_line)
            return True
        return False

    def find_next(self, query: str, start_row: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """从当前光标位置向后搜索，返回 (行, 列) 或 None"""
        if not query:
            return None
        start_row = start_row if start_row is not None else self.cursor_row
        for r in range(start_row, len(self.lines)):
            col = self.lines[r].find(query)
            if col >= 0:
                return (r, col)
        return None

    def to_text(self) -> str:
        """转为纯文本"""
        return "\n".join(self.lines)

    @classmethod
    def from_text(cls, text: str) -> "Document":
        """从文本创建文档"""
        lines = text.split("\n") if text else [""]
        return cls(lines=lines)


# ============================================================
# 文件操作与批处理
# ============================================================

class FileProcessor:
    """文件读写与批处理核心"""

    def __init__(self, input_path: str, output_path: Optional[str] = None):
        self.input_path = input_path
        self.output_path = output_path or self._default_output_path(input_path)
        self.processed_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.failures: List[Dict[str, str]] = []

    @staticmethod
    def _default_output_path(input_path: str) -> str:
        """生成默认输出路径（带 _out 后缀）"""
        base, ext = os.path.splitext(input_path)
        return f"{base}_out{ext}"

    def read_document(self) -> Document:
        """读取输入文件为文档"""
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"{ERR_FILE_NOT_FOUND}: 文件不存在: {self.input_path}")
        if not os.access(self.input_path, os.R_OK):
            raise PermissionError(f"{ERR_FILE_PERMISSION}: 无读取权限: {self.input_path}")
        try:
            with open(self.input_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试 GBK 编码
            try:
                with open(self.input_path, "r", encoding="gbk") as f:
                    content = f.read()
            except Exception:
                raise ValueError(f"{ERR_INVALID_FORMAT}: 无法解析文件编码: {self.input_path}")
        return Document.from_text(content)

    def write_document(self, doc: Document) -> None:
        """写入文档到输出文件"""
        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write(doc.to_text())
        except PermissionError:
            raise PermissionError(f"{ERR_WRITE_FAILED}: 无写入权限: {self.output_path}")
        except OSError as e:
            raise OSError(f"{ERR_WRITE_FAILED}: 写入失败: {e}")

    def process(self, transform=None) -> Document:
        """
        核心处理流程：
        1. 读取
        2. 应用变换（可选）
        3. 写入
        4. 计数统计
        """
        try:
            doc = self.read_document()
            if transform:
                doc = transform(doc)
            self.write_document(doc)
            self.processed_count += 1
            return doc
        except (FileNotFoundError, PermissionError, ValueError, OSError) as e:
            self.failed_count += 1
            self.failures.append({
                "file": self.input_path,
                "error": str(e)
            })
            raise

    def retry_process(self, transform=None, max_retries: int = 3) -> Document:
        """带重试的处理流程（幂等，可恢复错误重试）"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.process(transform)
            except (PermissionError, OSError) as e:
                last_error = e
                # 瞬时 IO 错误可重试
                if attempt < max_retries - 1:
                    continue
                raise
        raise RuntimeError(f"{ERR_RETRY_EXHAUSTED}: 重试 {max_retries} 次仍失败: {last_error}")


# ============================================================
# 编辑器核心功能
# ============================================================

class MicroEditor:
    """编辑器核心：提供编辑操作"""

    def __init__(self, doc: Optional[Document] = None):
        self.doc = doc or Document()
        self.search_history: List[str] = []

    def open(self, path: str) -> Document:
        """打开文件"""
        processor = FileProcessor(path)
        self.doc = processor.read_document()
        return self.doc

    def save(self, path: str) -> None:
        """保存到指定路径"""
        processor = FileProcessor(path)
        processor.doc = self.doc
        processor.write_document(self.doc)

    def insert(self, text: str) -> None:
        """插入文本"""
        self.doc.insert_text(text)

    def delete(self) -> bool:
        """删除字符"""
        return self.doc.delete_char()

    def find(self, query: str) -> Optional[Tuple[int, int]]:
        """查找下一个匹配"""
        self.search_history.append(query)
        return self.doc.find_next(query)

    def replace_all(self, old: str, new: str) -> int:
        """全局替换，返回替换次数"""
        count = 0
        for i, line in enumerate(self.doc.lines):
            if old in line:
                new_line = line.replace(old, new)
                # 统计替换次数
                count += line.count(old)
                self.doc.lines[i] = new_line
        return count

    def get_line_numbers(self) -> List[int]:
        """获取行号列表"""
        return list(range(1, len(self.doc.lines) + 1))

    def render_preview(self, max_lines: int = 20) -> str:
        """渲染预览（带行号）"""
        lines = self.doc.lines[:max_lines]
        width = len(str(len(lines)))
        rendered = []
        for i, line in enumerate(lines, 1):
            rendered.append(f"{i:>{width}} | {line}")
        return "\n".join(rendered)


# ============================================================
# 语法高亮（简化实现）
# ============================================================

# 简化关键词列表（支持 Python / JS / Java 等常见语言）
KEYWORDS = {
    "python": {"def", "class", "if", "else", "elif", "for", "while", "return", "import", "from", "try", "except"},
    "javascript": {"function", "const", "let", "var", "if", "else", "for", "while", "return", "import", "export"},
    "java": {"public", "private", "class", "void", "int", "String", "if", "else", "for", "while", "return"},
}

# ANSI 颜色码
COLOR_KEYWORD = "\033[36m"    # 青色
COLOR_STRING = "\033[32m"     # 绿色
COLOR_COMMENT = "\033[90m"    # 灰色
COLOR_RESET = "\033[0m"       # 重置


def highlight_line(line: str, language: str = "python") -> str:
    """简单的语法高亮（基于正则）"""
    if not line.strip():
        return line

    # 获取关键词集合
    keywords = KEYWORDS.get(language.lower(), set())

    # 高亮字符串（简单处理）
    result = line
    # 高亮关键词（使用正则边界）
    for kw in keywords:
        pattern = rf"\b{re.escape(kw)}\b"
        result = re.sub(pattern, f"{COLOR_KEYWORD}{kw}{COLOR_RESET}", result)

    # 高亮注释（# 开头）
    if "#" in result:
        idx = result.index("#")
        result = result[:idx] + COLOR_COMMENT + result[idx:] + COLOR_RESET

    return result


# ============================================================
# 命令行入口
# ============================================================

def run_selftest() -> int:
    """
    离线自检：使用硬编码样例验证核心逻辑。
    不读取外部文件、不访问网络、不依赖当前目录。
    """
    try:
        print("[SELFTEST] 开始自检...")

        # ---- 测试 1: Document 基本操作 ----
        doc = Document.from_text("hello world\nsecond line\nthird line")
        assert len(doc.lines) == 3, "行数应为 3"
        assert doc.current_line() == "hello world", "当前行应为第一行"
        doc.move_cursor(1, 0)
        assert doc.current_line() == "second line", "当前行应为第二行"
        print("[SELFTEST] Document 基本操作: PASS")

        # ---- 测试 2: 插入与删除 ----
        doc = Document()
        doc.insert_text("abc")
        assert doc.to_text() == "abc", "插入文本应成功"
        doc.move_cursor(0, 1)
        doc.insert_text("X")
        assert doc.to_text() == "aXbc", "中间插入应成功"
        
        # 修正：光标应该在插入的字符之后（位置2），删除应该删掉"X"
        # 但当前光标在位置2，需要先移动到位置1来删除"X"
        doc.move_cursor(0, -1)  # 移动到位置1（"X"之前）
        doc.delete_char()
        assert doc.to_text() == "abc", "删除应成功"
        print("[SELFTEST] 插入/删除: PASS")

        # ---- 测试 3: 搜索 ----
        doc = Document.from_text("apple\nbanana\ncherry")
        result = doc.find_next("banana")
        assert result is not None, "应找到 banana"
        assert result[0] == 1, "banana 应在第 1 行"
        assert doc.find_next("grape") is None, "不应找到 grape"
        print("[SELFTEST] 搜索功能: PASS")

        # ---- 测试 4: 替换 ----
        editor = MicroEditor(Document.from_text("foo bar foo"))
        count = editor.replace_all("foo", "baz")
        assert count == 2, "应替换 2 次"
        assert editor.doc.to_text() == "baz bar baz", "替换结果应正确"
        print("[SELFTEST] 替换功能: PASS")

        # ---- 测试 5: 文件处理（使用临时文件） ----
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write("test content\nline2")
            temp_path = tf.name
        try:
            processor = FileProcessor(temp_path)
            doc = processor.read_document()
            assert len(doc.lines) == 2, "临时文件应有 2 行"
            # 写入测试
            out_path = temp_path + "_out.txt"
            processor.output_path = out_path
            processor.write_document(doc)
            assert os.path.exists(out_path), "输出文件应存在"
            # 验证内容
            with open(out_path, "r") as f:
                content = f.read()
            assert "test content" in content, "输出内容应包含原文本"
            # 清理
            os.unlink(out_path)
        finally:
            os.unlink(temp_path)
        print("[SELFTEST] 文件处理: PASS")

        # ---- 测试 6: 语法高亮 ----
        highlighted = highlight_line("def foo(): pass", "python")
        assert "\033[" in highlighted, "高亮应包含 ANSI 码"
        print("[SELFTEST] 语法高亮: PASS")

        # ---- 测试 7: 行号渲染 ----
        editor = MicroEditor(Document.from_text("a\nb\nc"))
        preview = editor.render_preview()
        assert "1 | a" in preview, "预览应包含行号"
        assert "3 | c" in preview, "预览应包含最后一行"
        print("[SELFTEST] 预览渲染: PASS")

        # ---- 测试 8: 边界情况 ----
        doc = Document()
        assert doc.to_text() == "", "空文档应为空字符串"
        doc.move_cursor(-100, -100)
        assert doc.cursor_row == 0 and doc.cursor_col == 0, "光标应夹取到边界"
        print("[SELFTEST] 边界情况: PASS")

        print("[SELFTEST] 全部自检通过 ✓")
        return 0

    except AssertionError as e:
        print(f"[SELFTEST] 断言失败: {e}")
        print(f"[SELFTEST] 错误码: {ERR_SELFTEST_FAILED}")
        return 1
    except Exception as e:
        print(f"[SELFTEST] 未预期异常: {e}")
        print(f"[SELFTEST] 错误码: {ERR_SELFTEST_FAILED}")
        return 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="micro-editor 终端文本编辑器",
        epilog="示例: python scripts/main.py file.txt"
    )
    parser.add_argument("--file", nargs="?", help="要编辑的文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--preview", action="store_true", help="显示预览后退出")
    parser.add_argument("--lang", default="python", help="语法高亮语言")
    parser.add_argument("--output", "-o", help="输出文件路径（默认带 _out 后缀）")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 需要文件参数
    if not args.file:
        print(f"{ERR_INVALID_ARG}: 缺少文件参数，使用 --help 查看帮助", file=sys.stderr)
        return 1

    # 文件不存在检查
    if not os.path.exists(args.file):
        print(f"{ERR_FILE_NOT_FOUND}: 文件不存在: {args.file}", file=sys.stderr)
        return 1

    try:
        # 创建编辑器实例
        editor = MicroEditor()

        if args.preview:
            # 预览模式
            editor.open(args.file)
            print(editor.render_preview())
            return 0

        # 批处理模式（读取 + 写入）
        processor = FileProcessor(args.file, args.output)
        doc = processor.read_document()
        processor.write_document(doc)

        # 统计信息
        print(f"处理完成: {args.file}")
        print(f"输出文件: {processor.output_path}")
        print(f"行数: {len(doc.lines)}")
        print(f"状态: 成功 (1) / 跳过 (0) / 失败 (0)")

        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{ERR_INTERNAL}: 未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
