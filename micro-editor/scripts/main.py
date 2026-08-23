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
        """在当前光标位置插入文本（支持多行）

        单行插入：直接拼接到光标处，光标后移。
        多行插入：首段接在光标前半段之后，末段带上光标后半段，
        中间各段独立成行，光标停在末段行尾。
        """
        if not text:
            return
        parts = text.split("\n")
        line = self.lines[self.cursor_row]
        head, tail = line[:self.cursor_col], line[self.cursor_col:]

        # 单行插入：最常见路径
        if len(parts) == 1:
            self.lines[self.cursor_row] = head + parts[0] + tail
            self.cursor_col = len(head) + len(parts[0])
            return

        # 多行插入：首段留在当前行，末段承接原行剩余内容
        self.lines[self.cursor_row] = head + parts[0]
        last_idx = len(parts) - 1
        for i, part in enumerate(parts[1:], start=1):
            self.cursor_row += 1
            self.lines.insert(self.cursor_row, part + tail if i == last_idx else part)
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

    def write_document(self, doc: Document, dry_run: bool = False) -> None:
        """写入文档到输出文件。

        dry_run=True 时只做权限与路径校验，不落盘，供 --dry-run 预览使用。
        """
        parent = os.path.dirname(os.path.abspath(self.output_path)) or "."
        if not os.access(parent, os.W_OK):
            raise PermissionError(f"{ERR_WRITE_FAILED}: 无写入权限: {self.output_path}")
        # 写盘分支由 dry_run 统一控制：预览态只校验不落盘
        if not dry_run:
            try:
                with open(self.output_path, "w", encoding="utf-8") as f:
                    f.write(doc.to_text())
            except PermissionError:
                raise PermissionError(f"{ERR_WRITE_FAILED}: 无写入权限: {self.output_path}")
            except OSError as e:
                raise OSError(f"{ERR_WRITE_FAILED}: 写入失败: {e}")

    def diff_report(self, before: str, after: str, max_lines: int = 40) -> List[str]:
        """生成写盘前后的 diff 明细，供 --dry-run / --verbose 展示。

        返回统一 diff 格式的行列表；无变化时返回空列表。
        """
        import difflib

        lines = list(difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"a/{os.path.basename(self.input_path)}",
            tofile=f"b/{os.path.basename(self.output_path)}",
            lineterm="", n=1,
        ))
        if len(lines) > max_lines:
            lines = lines[:max_lines] + [f"... 其余 {len(lines) - max_lines} 行 diff 已省略"]
        return lines

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
        assert doc.cursor_col == 3, "插入后光标应在行尾"

        # 光标从行尾(3)左移 2 位到位置 1，再插入 X → "aXbc"
        doc.move_cursor(0, -2)
        assert doc.cursor_col == 1, "光标应位于位置 1"
        doc.insert_text("X")
        assert doc.to_text() == "aXbc", "中间插入应成功"
        assert doc.cursor_col == 2, "插入后光标应紧跟插入内容之后"

        # 光标在位置 2，删除其前一个字符即刚插入的 X → 复原为 abc
        doc.delete_char()
        assert doc.to_text() == "abc", "删除应成功"
        print("[SELFTEST] 插入/删除: PASS")

        # ---- 测试 2b: 多行插入（首段/中间段/末段拼接） ----
        doc = Document.from_text("HelloWorld")
        doc.move_cursor(0, 5)          # 光标移到 Hello 之后
        doc.insert_text("A\nB\nC")     # 期望: HelloA / B / CWorld
        assert doc.lines == ["HelloA", "B", "CWorld"], f"多行插入结果异常: {doc.lines}"
        assert doc.cursor_row == 2, "多行插入后应停在末段所在行"
        assert doc.cursor_col == 1, "多行插入后光标应在末段内容之后"
        print("[SELFTEST] 多行插入: PASS")

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

        # ---- 测试 9: dry-run 不落盘 ----
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write("alpha\nbeta")
            temp_path = tf.name
        try:
            processor = FileProcessor(temp_path)
            doc = processor.read_document()
            out_path = temp_path + "_dry.txt"
            processor.output_path = out_path
            processor.write_document(doc, dry_run=True)
            assert not os.path.exists(out_path), "dry-run 不应产生输出文件"
            processor.write_document(doc)
            assert os.path.exists(out_path), "去掉 dry-run 后应真正写入"
            os.unlink(out_path)
        finally:
            os.unlink(temp_path)
        print("[SELFTEST] dry-run 预览不落盘: PASS")

        # ---- 测试 10: diff 明细输出 ----
        processor = FileProcessor("a.txt", "b.txt")
        diff = processor.diff_report("x\ny", "x\nz")
        assert any(line.startswith("-y") for line in diff), "diff 应标出删除行"
        assert any(line.startswith("+z") for line in diff), "diff 应标出新增行"
        assert processor.diff_report("same", "same") == [], "无变化时 diff 应为空"
        print("[SELFTEST] diff 明细生成: PASS")

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
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式：只打印将要写入的 diff，不落盘")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="输出每步处理决策明细（读取编码、行数变化、diff 摘要）")

    args = parser.parse_args()

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
        before = doc.to_text()

        if args.verbose:
            print(f"[明细] 读取: {args.file}（{len(doc.lines)} 行，{len(before)} 字符）")
            print(f"[明细] 目标: {processor.output_path}")

        after = doc.to_text()
        diff = processor.diff_report(before, after)

        if args.dry_run:
            print("=== 预览模式（--dry-run，未写入任何文件）===")
            print(f"将写入: {processor.output_path}")
            print(f"行数: {len(doc.lines)}")
            if diff:
                print("--- diff 明细 ---")
                for line in diff:
                    print(line)
            else:
                print("内容无变化，实际执行时将原样写出")
            processor.write_document(doc, dry_run=True)
            print("提示: 确认无误后去掉 --dry-run 即可真正写入")
            return 0

        processor.write_document(doc)

        if args.verbose:
            if diff:
                print("[明细] 变更 diff:")
                for line in diff:
                    print(f"  {line}")
            else:
                print("[明细] 内容无变化，原样写出")

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
