#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context-mode 技能实现脚本

功能：
- 工具输出压缩：将冗长文本压缩为结构化摘要
- 会话记忆持久化：将关键信息写入会话记忆文件
- 关键信息提取：从原始数据中识别核心事实与数字
- 结构化格式输出：支持 Markdown 表格、键值对、JSON 三种格式
- 批量处理：支持多个输入源与自定义输出字段

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用级异常基类，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def err_invalid_input(msg: str) -> AppError:
    """E001：输入参数无效"""
    return AppError("E001", msg)


def err_file_read(msg: str) -> AppError:
    """E002：文件读取失败"""
    return AppError("E002", msg)


def err_file_write(msg: str) -> AppError:
    """E003：文件写入失败"""
    return AppError("E003", msg)


def err_unsupported_format(msg: str) -> AppError:
    """E004：不支持的输出格式"""
    return AppError("E004", msg)


def err_missing_field(msg: str) -> AppError:
    """E005：缺少必要字段"""
    return AppError("E005", msg)


def err_invalid_json(msg: str) -> AppError:
    """E006：JSON 解析失败"""
    return AppError("E006", msg)


def err_empty_input(msg: str) -> AppError:
    """E007：输入内容为空"""
    return AppError("E007", msg)


def err_memory_file(msg: str) -> AppError:
    """E008：会话记忆文件操作失败"""
    return AppError("E008", msg)


def err_batch_failed(msg: str) -> AppError:
    """E009：批量处理失败"""
    return AppError("E009", msg)


def err_internal(msg: str) -> AppError:
    """E010：内部未知错误"""
    return AppError("E010", msg)


# ============================================================
# 核心数据结构
# ============================================================
class CompressionResult:
    """压缩结果的数据结构。"""
    def __init__(self, original_size: int, compressed_size: int, lines: int, summary: str):
        self.original_size = original_size      # 原始字节数
        self.compressed_size = compressed_size  # 压缩后字节数
        self.lines = lines                      # 原始行数
        self.summary = summary                  # 压缩摘要文本
        self.created_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "lines": self.lines,
            "summary": self.summary,
            "created_at": self.created_at,
        }


class SessionMemory:
    """会话记忆的持久化存储。"""
    def __init__(self, filepath: Optional[str] = None):
        # 默认使用临时目录下的记忆文件，保证任何环境可运行
        if filepath is None:
            tmp_dir = tempfile.gettempdir()
            filepath = os.path.join(tmp_dir, "context_mode_memory.json")
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self) -> None:
        """确保记忆文件存在且是合法 JSON。"""
        try:
            if not os.path.exists(self.filepath):
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump({"entries": []}, f, ensure_ascii=False, indent=2)
            else:
                # 验证现有文件是否为合法 JSON
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "entries" not in data:
                    raise ValueError("记忆文件格式不正确")
        except (OSError, ValueError) as e:
            raise err_memory_file(f"无法初始化记忆文件 {self.filepath}: {e}")

    def add_entry(self, key: str, content: str) -> None:
        """添加一条记忆记录。"""
        if not key or not content:
            raise err_invalid_input("记忆的键和内容不能为空")
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["entries"].append({
                "key": key,
                "content": content,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise err_memory_file(f"写入记忆文件失败: {e}")

    def get_entry(self, key: str) -> Optional[Dict[str, Any]]:
        """按键获取记忆记录。"""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data["entries"]:
                if entry["key"] == key:
                    return entry
            return None
        except OSError as e:
            raise err_memory_file(f"读取记忆文件失败: {e}")

    def list_keys(self) -> List[str]:
        """列出所有记忆键。"""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [entry["key"] for entry in data["entries"]]
        except OSError as e:
            raise err_memory_file(f"读取记忆文件失败: {e}")


# ============================================================
# 核心逻辑：文本压缩与信息提取
# ============================================================
class TextCompressor:
    """文本压缩器，负责将冗长文本转为结构化摘要。"""

    # 常见的无意义行（日志噪音、重复分隔线等）
    NOISE_PATTERNS = [
        r"^\s*[-=_*#]{3,}\s*$",       # 纯分隔线
        r"^\s*$",                      # 空行
        r"^\s*(INFO|DEBUG|TRACE)\s*:", # 低级别日志前缀
    ]

    # 关键信息识别模式（数字、错误、警告、结论等）
    KEY_PATTERNS = [
        (r"error|exception|failed|失败|错误", "错误信息"),
        (r"warning|warn|警告", "警告信息"),
        (r"\b\d{1,3}(,\d{3})*(\.\d+)?\b", "数字"),
        (r"success|成功|完成|passed|通过", "成功信息"),
        (r"conclusion|结论|result|结果", "结论"),
    ]

    def __init__(self, max_lines: int = 30):
        self.max_lines = max_lines

    def compress(self, text: str) -> CompressionResult:
        """压缩文本，返回结构化结果。"""
        if not text or not text.strip():
            raise err_empty_input("输入文本为空，无法压缩")

        original_size = len(text.encode("utf-8"))
        lines = text.splitlines()
        line_count = len(lines)

        # 过滤噪音行
        meaningful_lines = self._filter_noise(lines)

        # 提取关键信息
        key_info = self._extract_key_info(text)

        # 生成摘要
        summary = self._build_summary(meaningful_lines, key_info)

        compressed_size = len(summary.encode("utf-8"))

        return CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            lines=line_count,
            summary=summary,
        )

    def _filter_noise(self, lines: List[str]) -> List[str]:
        """过滤噪音行，保留有意义的行。"""
        result = []
        for line in lines:
            is_noise = False
            for pattern in self.NOISE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    is_noise = True
                    break
            if not is_noise:
                result.append(line.strip())
        return result

    def _extract_key_info(self, text: str) -> Dict[str, List[str]]:
        """提取关键信息，按类别分组。"""
        info: Dict[str, List[str]] = {}
        for pattern, category in self.KEY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # 去重并限制数量
                unique = list(dict.fromkeys(matches))[:5]
                info[category] = unique
        return info

    def _build_summary(self, lines: List[str], key_info: Dict[str, List[str]]) -> str:
        """构建压缩摘要文本。"""
        parts = []

        # 统计信息
        total_lines = len(lines)
        parts.append(f"有效内容行数：{total_lines}")

        # 关键信息摘要
        if key_info:
            parts.append("关键信息：")
            for category, items in key_info.items():
                items_str = "、".join(items[:3])
                parts.append(f"  - {category}: {items_str}")

        # 保留前若干行有意义内容
        if lines:
            parts.append("内容预览：")
            preview_lines = lines[:self.max_lines]
            for line in preview_lines:
                # 截断过长的行
                if len(line) > 100:
                    line = line[:97] + "..."
                parts.append(f"  {line}")

            if len(lines) > self.max_lines:
                parts.append(f"  ... 共省略 {len(lines) - self.max_lines} 行")

        return "\n".join(parts)


# ============================================================
# 结构化输出格式化
# ============================================================
class OutputFormatter:
    """将压缩结果格式化为指定格式。"""

    @staticmethod
    def format(result: CompressionResult, fmt: str = "markdown") -> str:
        """按指定格式输出。"""
        fmt = fmt.lower()
        if fmt == "markdown":
            return OutputFormatter._to_markdown(result)
        elif fmt == "json":
            return OutputFormatter._to_json(result)
        elif fmt == "kv":
            return OutputFormatter._to_kv(result)
        else:
            raise err_unsupported_format(f"不支持的输出格式：{fmt}")

    @staticmethod
    def _to_markdown(result: CompressionResult) -> str:
        """Markdown 表格格式。"""
        lines = [
            "| 项目 | 值 |",
            "|------|-----|",
            f"| 原始大小 | {result.original_size} 字节 |",
            f"| 压缩后大小 | {result.compressed_size} 字节 |",
            f"| 压缩率 | {OutputFormatter._ratio(result.original_size, result.compressed_size)}% |",
            f"| 原始行数 | {result.lines} |",
            "",
            "## 压缩摘要",
            "",
        ]
        # 添加摘要内容（每行前加缩进）
        for line in result.summary.split("\n"):
            lines.append(f"  {line}")
        return "\n".join(lines)

    @staticmethod
    def _to_json(result: CompressionResult) -> str:
        """JSON 格式输出。"""
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def _to_kv(result: CompressionResult) -> str:
        """键值对格式输出。"""
        kv_lines = [
            f"original_size={result.original_size}",
            f"compressed_size={result.compressed_size}",
            f"ratio={OutputFormatter._ratio(result.original_size, result.compressed_size)}%",
            f"lines={result.lines}",
            f"created_at={result.created_at}",
            "summary=",
        ]
        # 摘要内容缩进
        for line in result.summary.split("\n"):
            kv_lines.append(f"  {line}")
        return "\n".join(kv_lines)

    @staticmethod
    def _ratio(original: int, compressed: int) -> float:
        """计算压缩率。"""
        if original == 0:
            return 0.0
        return round((1 - compressed / original) * 100, 1)


# ============================================================
# 批量处理
# ============================================================
class BatchProcessor:
    """批量处理多个输入源。"""

    @staticmethod
    def process(inputs: List[str], fmt: str = "markdown", max_lines: int = 30) -> List[Dict[str, Any]]:
        """处理多个输入，返回结果列表。"""
        results = []
        compressor = TextCompressor(max_lines=max_lines)

        for i, input_text in enumerate(inputs):
            try:
                result = compressor.compress(input_text)
                formatted = OutputFormatter.format(result, fmt)
                results.append({
                    "index": i,
                    "success": True,
                    "output": formatted,
                    "meta": result.to_dict(),
                })
            except AppError as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": e.message,
                    "output": None,
                    "meta": None,
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": f"未知错误: {str(e)}",
                    "output": None,
                    "meta": None,
                })

        return results


# ============================================================
# 自测函数
# ============================================================
def run_selftest() -> bool:
    """运行自测，验证核心功能。"""
    print("=" * 50)
    print("开始自测...")
    print("=" * 50)

    try:
        # 测试 1：文本压缩
        print("\n[测试 1] 文本压缩")
        compressor = TextCompressor(max_lines=5)
        sample_text = """INFO: Starting application
        =====================
        Server started successfully on port 8080
        Connected to database: mysql://localhost:3306/app
        Processed 1234 requests in 5.6 seconds
        Warning: high memory usage detected
        Error: connection timeout to external API
        All systems operational
        =====================
        Shutdown complete"""
        result = compressor.compress(sample_text)
        assert result.original_size > 0, "原始大小应为正数"
        assert result.lines == 10, f"行数应为 10，实际为 {result.lines}"
        assert "关键信息" in result.summary, "摘要应包含关键信息"
        print(f"  ✓ 压缩成功：{result.original_size} -> {result.compressed_size} 字节")
        print(f"  ✓ 压缩率：{OutputFormatter._ratio(result.original_size, result.compressed_size)}%")

        # 测试 2：格式输出
        print("\n[测试 2] 格式输出")
        md_output = OutputFormatter.format(result, "markdown")
        assert "| 项目 | 值 |" in md_output, "Markdown 应包含表格头"
        print(f"  ✓ Markdown 输出成功，长度 {len(md_output)} 字符")

        json_output = OutputFormatter.format(result, "json")
        json_data = json.loads(json_output)
        assert json_data["original_size"] == result.original_size, "JSON 原始大小不匹配"
        print(f"  ✓ JSON 输出成功，长度 {len(json_output)} 字符")

        kv_output = OutputFormatter.format(result, "kv")
        assert "original_size=" in kv_output, "KV 应包含原始大小"
        print(f"  ✓ KV 输出成功，长度 {len(kv_output)} 字符")

        # 测试 3：会话记忆
        print("\n[测试 3] 会话记忆")
        memory = SessionMemory()
        memory.add_entry("test_key", "测试内容")
        entry = memory.get_entry("test_key")
        assert entry is not None, "应能获取记忆条目"
        assert entry["content"] == "测试内容", "记忆内容不匹配"
        keys = memory.list_keys()
        assert "test_key" in keys, "应包含测试键"
        print(f"  ✓ 记忆写入/读取成功，当前键数：{len(keys)}")

        # 测试 4：批量处理
        print("\n[测试 4] 批量处理")
        batch_inputs = ["第一段文本内容", "第二段包含错误信息的文本"]
        results = BatchProcessor.process(batch_inputs, fmt="json")
        assert len(results) == 2, f"应处理 2 个输入，实际 {len(results)}"
        assert all(r["success"] for r in results), "所有处理应成功"
        print(f"  ✓ 批量处理成功，处理 {len(results)} 个输入")

        # 测试 5：错误处理
        print("\n[测试 5] 错误处理")
        try:
            compressor.compress("")
            assert False, "空输入应抛出异常"
        except AppError as e:
            assert e.code == "E007", f"错误码应为 E007，实际为 {e.code}"
            print(f"  ✓ 空输入错误处理正确：{e.code}")

        try:
            OutputFormatter.format(result, "xml")
            assert False, "不支持的格式应抛出异常"
        except AppError as e:
            assert e.code == "E004", f"错误码应为 E004，实际为 {e.code}"
            print(f"  ✓ 不支持的格式错误处理正确：{e.code}")

        # 测试 6：关键信息提取
        print("\n[测试 6] 关键信息提取")
        info_text = "系统运行正常，处理了 1234 个请求，发现 2 个错误：连接超时和资源不足"
        info_result = compressor._extract_key_info(info_text)
        assert "数字" in info_result, "应提取到数字"
        assert "错误信息" in info_result, "应提取到错误信息"
        print(f"  ✓ 关键信息提取成功：{list(info_result.keys())}")

        print("\n" + "=" * 50)
        print("所有自测通过！")
        print("=" * 50)
        return True

    except AssertionError as e:
        print(f"\n✗ 自测失败：{str(e)}")
        return False
    except Exception as e:
        print(f"\n✗ 自测异常：{str(e)}")
        return False


# ============================================================
# 主入口
# ============================================================
def main():
    """主函数，处理命令行参数。"""
    parser = argparse.ArgumentParser(
        description="context-mode 技能：文本压缩、记忆持久化、信息提取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", "-i", type=str, help="输入文本或文件路径")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径（与 --input 二选一）")
    parser.add_argument("--format", "-fmt", type=str, default="markdown",
                        choices=["markdown", "json", "kv"],
                        help="输出格式（默认：markdown）")
    parser.add_argument("--max-lines", type=int, default=30,
                        help="摘要最大行数（默认：30）")
    parser.add_argument("--memory-file", type=str,
                        help="会话记忆文件路径（默认：系统临时目录）")
    parser.add_argument("--memory-add", nargs=2, metavar=("KEY", "CONTENT"),
                        help="添加记忆条目：--memory-add 键 内容")
    parser.add_argument("--memory-get", type=str, metavar="KEY",
                        help="获取记忆条目：--memory-get 键")
    parser.add_argument("--memory-list", action="store_true",
                        help="列出所有记忆键")
    parser.add_argument("--batch", type=str, nargs="+",
                        help="批量处理多个输入（空格分隔）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行自测")

    args = parser.parse_args()

    # 运行自测
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    try:
        # 记忆操作
        if args.memory_add:
            memory = SessionMemory(args.memory_file)
            memory.add_entry(args.memory_add[0], args.memory_add[1])
            print(json.dumps({"success": True, "message": "记忆已添加"}, ensure_ascii=False))
            return

        if args.memory_get:
            memory = SessionMemory(args.memory_file)
            entry = memory.get_entry(args.memory_get)
            if entry:
                print(json.dumps(entry, ensure_ascii=False, indent=2))
            else:
                print(json.dumps({"success": False, "message": f"未找到键 '{args.memory_get}'"}, ensure_ascii=False))
            return

        if args.memory_list:
            memory = SessionMemory(args.memory_file)
            keys = memory.list_keys()
            print(json.dumps({"keys": keys}, ensure_ascii=False, indent=2))
            return

        # 批量处理
        if args.batch:
            results = BatchProcessor.process(args.batch, fmt=args.format, max_lines=args.max_lines)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return

        # 获取输入内容
        input_text = ""
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    input_text = f.read()
            except OSError as e:
                raise err_file_read(f"无法读取文件 {args.file}: {e}")
        elif args.input:
            # 如果是文件路径则读取，否则作为文本
            if os.path.isfile(args.input):
                try:
                    with open(args.input, "r", encoding="utf-8") as f:
                        input_text = f.read()
                except OSError as e:
                    raise err_file_read(f"无法读取文件 {args.input}: {e}")
            else:
                input_text = args.input
        else:
            # 从标准输入读取
            if not sys.stdin.isatty():
                input_text = sys.stdin.read()

        if not input_text:
            raise err_invalid_input("请通过 --input、--file 或标准输入提供内容")

        # 执行压缩
        compressor = TextCompressor(max_lines=args.max_lines)
        result = compressor.compress(input_text)
        output = OutputFormatter.format(result, args.format)
        print(output)

    except AppError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 [E010]: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
