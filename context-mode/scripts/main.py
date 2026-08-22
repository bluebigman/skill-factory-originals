#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context-mode 技能实现脚本
功能：压缩工具输出、持久化会话记忆、提取关键信息、结构化格式输出、批量处理
版本：2.0.0
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class ErrorCode:
    E001 = "E001: 参数错误"
    E002 = "E002: 输入内容为空"
    E003 = "E003: 不支持的输出格式"
    E004 = "E004: 记忆文件写入失败"
    E005 = "E005: 记忆文件读取失败"
    E006 = "E006: 无效的JSON输入"
    E007 = "E007: 批量处理输入为空"
    E008 = "E008: 自定义字段配置错误"
    E009 = "E009: 输入内容不是UTF-8文本"
    E010 = "E010: 内部逻辑错误"


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class CompressionResult:
    """压缩结果对象"""
    def __init__(self, original_length: int, compressed_length: int, summary: str, key_points: List[str]):
        self.original_length = original_length
        self.compressed_length = compressed_length
        self.summary = summary
        self.key_points = key_points

    @property
    def reduction_ratio(self) -> float:
        """计算压缩率"""
        if self.original_length == 0:
            return 0.0
        return (self.original_length - self.compressed_length) / self.original_length

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_length": self.original_length,
            "compressed_length": self.compressed_length,
            "reduction_ratio": round(self.reduction_ratio, 4),
            "summary": self.summary,
            "key_points": self.key_points,
        }


class SessionMemory:
    """会话记忆管理器"""
    def __init__(self, memory_file: Optional[str] = None):
        self.memory_file = memory_file or os.environ.get(
            "CONTEXT_MODE_MEMORY_FILE",
            str(Path.home() / ".context_mode_memory.json")
        )

    def load(self) -> List[str]:
        """加载记忆列表"""
        try:
            if not os.path.exists(self.memory_file):
                return []
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            print(f"警告: 记忆文件读取失败: {e}", file=sys.stderr)
            return []

    def save(self, text: str) -> bool:
        """保存一条记忆"""
        try:
            memories = self.load()
            memories.append(text)
            # 原子写入
            tmp_file = self.memory_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self.memory_file)
            return True
        except Exception as e:
            print(f"错误: 记忆文件写入失败: {e}", file=sys.stderr)
            return False


# ---------------------------------------------------------------------------
# 核心功能函数
# ---------------------------------------------------------------------------
def read_file_with_encoding(filepath: str) -> str:
    """读取文件，自动处理多编码"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise FileNotFoundError(f"E001: 参数错误 - 输入文件不存在: {filepath}")
    # 最后尝试 replace 模式
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def compress_text(text: str, max_key_points: int = 10) -> CompressionResult:
    """压缩文本为结构化摘要"""
    if not text or not text.strip():
        return CompressionResult(0, 0, "空输入", [])

    lines = text.splitlines()
    total_lines = len(lines)

    # 统计日志级别
    level_counter = Counter()
    error_lines = []
    for line in lines:
        for level in ["ERROR", "WARN", "INFO", "DEBUG", "FATAL"]:
            if level in line.upper():
                level_counter[level] += 1
                if level in ["ERROR", "FATAL"]:
                    error_lines.append(line)
                break

    # 提取关键信息
    key_points = []
    if error_lines:
        key_points.append(f"发现 {len(error_lines)} 条错误/致命日志")
        for err in error_lines[:3]:
            key_points.append(f"错误: {err.strip()[:100]}")

    if level_counter:
        level_summary = ", ".join(f"{k}: {v}条" for k, v in level_counter.most_common())
        key_points.append(f"日志级别统计: {level_summary}")

    # 生成摘要
    summary_parts = [f"共 {total_lines} 行"]
    if level_counter:
        summary_parts.append(f"主要级别: {level_counter.most_common(1)[0][0]}")
    summary = "；".join(summary_parts)

    # 计算压缩后长度（模拟压缩后的文本长度）
    compressed_text = summary + " | " + " | ".join(key_points)
    compressed_length = len(compressed_text)

    return CompressionResult(len(text), compressed_length, summary, key_points[:max_key_points])


def extract_key_info(text: str, keywords: List[str], context_lines: int = 0) -> Dict[str, Any]:
    """提取包含关键词的行及上下文"""
    if not text or not keywords:
        return {"matches": [], "total_matches": 0}

    lines = text.splitlines()
    matches = []
    for i, line in enumerate(lines):
        if any(kw.lower() in line.lower() for kw in keywords):
            match_entry = {
                "line_number": i + 1,
                "content": line.strip(),
                "context": []
            }
            # 添加上下文
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            for j in range(start, end):
                if j != i:
                    match_entry["context"].append({
                        "line_number": j + 1,
                        "content": lines[j].strip()
                    })
            matches.append(match_entry)

    return {"matches": matches, "total_matches": len(matches)}


def format_output(result: Any, fmt: str = "md") -> str:
    """格式化输出"""
    if fmt == "json":
        if isinstance(result, CompressionResult):
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "kv":
        if isinstance(result, CompressionResult):
            d = result.to_dict()
            return "\n".join(f"{k}: {v}" for k, v in d.items())
        elif isinstance(result, dict):
            return "\n".join(f"{k}: {v}" for k, v in result.items())
        return str(result)
    else:  # md
        if isinstance(result, CompressionResult):
            lines = [
                "# 压缩摘要",
                "",
                f"- 原始长度: {result.original_length} 字符",
                f"- 压缩后长度: {result.compressed_length} 字符",
                f"- 压缩率: {result.reduction_ratio * 100:.1f}%",
                "",
                "## 关键信息",
            ]
            for point in result.key_points:
                lines.append(f"- {point}")
            return "\n".join(lines)
        elif isinstance(result, dict) and "matches" in result:
            lines = ["# 关键信息提取结果", ""]
            lines.append(f"共找到 {result['total_matches']} 条匹配")
            for m in result["matches"]:
                lines.append(f"\n### 行 {m['line_number']}")
                lines.append(f"内容: {m['content']}")
                if m["context"]:
                    lines.append("上下文:")
                    for ctx in m["context"]:
                        lines.append(f"  行 {ctx['line_number']}: {ctx['content']}")
            return "\n".join(lines)
        return str(result)


def atomic_write(filepath: str, content: str) -> bool:
    """原子写入文件"""
    try:
        tmp_file = filepath + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_file, filepath)
        return True
    except Exception as e:
        print(f"错误: 写入文件失败: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def batch_process(directory: str, output_dir: str, fmt: str = "md", dry_run: bool = False) -> Dict[str, Any]:
    """批量处理目录下的所有 .log 和 .txt 文件"""
    if not os.path.isdir(directory):
        raise ValueError(f"E001: 参数错误 - 目录不存在: {directory}")

    os.makedirs(output_dir, exist_ok=True)
    results = {"total": 0, "success": 0, "skipped": 0, "failed": 0, "failures": []}

    for filepath in sorted(Path(directory).glob("*")):
        if filepath.suffix.lower() not in [".log", ".txt", ".json", ".md"]:
            results["skipped"] += 1
            continue

        results["total"] += 1
        try:
            content = read_file_with_encoding(str(filepath))
            if not content.strip():
                results["skipped"] += 1
                continue

            result = compress_text(content)
            output_content = format_output(result, fmt)
            output_file = Path(output_dir) / f"{filepath.stem}_out.{fmt}"

            if dry_run:
                print(f"[DRY-RUN] 将写入: {output_file}")
                print(f"[DRY-RUN] 内容摘要: {result.summary}")
            else:
                if atomic_write(str(output_file), output_content):
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["failures"].append({"file": str(filepath), "reason": "写入失败"})
        except Exception as e:
            results["failed"] += 1
            results["failures"].append({"file": str(filepath), "reason": str(e)})

    return results


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行自检，验证核心功能"""
    print("开始自检...")
    all_passed = True

    # 测试1: 压缩功能
    print("\n[测试1] 压缩功能")
    test_text = """2026-08-11 10:00:01 INFO Starting application
2026-08-11 10:00:02 DEBUG Loading config
2026-08-11 10:00:03 ERROR Failed to connect to database: timeout
2026-08-11 10:00:04 WARN Retrying connection (attempt 1/3)
2026-08-11 10:00:05 INFO Connection established"""
    result = compress_text(test_text)
    assert result.original_length > 0, "原始长度应为正数"
    assert result.compressed_length > 0, "压缩后长度应为正数"
    assert result.reduction_ratio > 0, "压缩率应为正数"
    assert len(result.key_points) > 0, "应有关键信息"
    print(f"  通过: 压缩率 {result.reduction_ratio * 100:.1f}%")
    print(f"  关键信息: {result.key_points}")

    # 测试2: 空输入
    print("\n[测试2] 空输入处理")
    result = compress_text("")
    assert result.original_length == 0, "空输入原始长度应为0"
    assert result.summary == "空输入", "空输入摘要应为'空输入'"
    print("  通过: 空输入正确处理")

    # 测试3: 关键信息提取
    print("\n[测试3] 关键信息提取")
    extract_result = extract_key_info(test_text, ["ERROR", "WARN"], context_lines=1)
    assert extract_result["total_matches"] == 2, f"应找到2条匹配，实际{extract_result['total_matches']}"
    assert len(extract_result["matches"][0]["context"]) > 0, "应有上下文"
    print(f"  通过: 找到 {extract_result['total_matches']} 条匹配")

    # 测试4: 记忆功能
    print("\n[测试4] 会话记忆")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    memory = SessionMemory(tmp_path)
    assert memory.save("测试记忆1"), "保存记忆应成功"
    assert memory.save("测试记忆2"), "保存记忆应成功"
    memories = memory.load()
    assert len(memories) == 2, f"应加载2条记忆，实际{len(memories)}"
    assert memories[0] == "测试记忆1", "第一条记忆内容不符"
    os.unlink(tmp_path)
    print("  通过: 记忆保存和加载正常")

    # 测试5: 格式输出
    print("\n[测试5] 格式输出")
    md_output = format_output(result, "md")
    assert "压缩摘要" in md_output, "Markdown输出应包含标题"
    json_output = format_output(result, "json")
    json_data = json.loads(json_output)
    assert "original_length" in json_data, "JSON输出应包含original_length"
    kv_output = format_output(result, "kv")
    assert "original_length:" in kv_output, "KV输出应包含original_length"
    print("  通过: 三种格式输出正常")

    # 测试6: 批量处理（dry-run）
    print("\n[测试6] 批量处理 dry-run")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_file = Path(tmpdir) / "test.log"
        if not dry_run:
            test_file.write_text(test_text, encoding="utf-8")
        out_dir = Path(tmpdir) / "out"
        results = batch_process(tmpdir, str(out_dir), dry_run=True)
        assert results["total"] == 1, f"应处理1个文件，实际{results['total']}"
        assert not (out_dir / "test_out.md").exists(), "dry-run不应写文件"
    print("  通过: dry-run 不写盘")

    # 测试7: 编码处理
    print("\n[测试7] 编码处理")
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
    # 写入 GBK 编码
    with open(tmp_path, "w", encoding="gbk") as f:
        f.write("测试中文内容\n第二行")
    content = read_file_with_encoding(tmp_path)
    assert "测试中文内容" in content, "GBK编码读取失败"
    os.unlink(tmp_path)
    print("  通过: GBK编码正确读取")

    print("\n" + "=" * 40)
    if all_passed:
        print("所有自检通过 ✓")
        return True
    else:
        print("存在失败项 ✗")
        return False


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="context-mode: 上下文压缩与会话记忆工具")
    parser.add_argument("--command", choices=["compress", "batch", "memory", "extract", "selftest"],
                        help="要执行的命令")
    parser.add_argument("-i", "--input", help="输入文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-d", "--dir", help="批量处理目录")
    parser.add_argument("--key", help="提取关键词（逗号分隔）")
    parser.add_argument("--context", type=int, default=0, help="提取时上下文行数")
    parser.add_argument("--format", choices=["md", "json", "kv"], default="md", help="输出格式")
    parser.add_argument("--dry-run", action="store_true", help="试运行不写盘")
    parser.add_argument("--verbose", action="store_true", help="详细模式")
    parser.add_argument("--save", help="保存记忆内容")
    parser.add_argument("--load", action="store_true", help="加载记忆")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.command == "selftest" or args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 压缩命令
    if args.command == "compress":
        if not args.input:
            print(f"错误: {ErrorCode.E001} - 缺少输入文件", file=sys.stderr)
            sys.exit(1)
        try:
            content = read_file_with_encoding(args.input)
            result = compress_text(content)
            output_content = format_output(result, args.format)

            if args.dry_run:
                print(f"[DRY-RUN] 将写入: {args.output or 'stdout'}")
                print(f"[DRY-RUN] 压缩率: {result.reduction_ratio * 100:.1f}%")
                print(f"[DRY-RUN] 摘要: {result.summary}")
                if args.verbose:
                    print("\n[DRY-RUN] 完整输出预览:")
                    print(output_content)
            else:
                if args.output:
                    if atomic_write(args.output, output_content):
                        print(f"压缩完成: {args.input} -> {args.output}")
                        print(f"压缩率: {result.reduction_ratio * 100:.1f}%")
                    else:
                        print(f"错误: {ErrorCode.E004}", file=sys.stderr)
                        sys.exit(1)
                else:
                    print(output_content)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

    # 批量命令
    elif args.command == "batch":
        if not args.dir:
            print(f"错误: {ErrorCode.E001} - 缺少目录参数", file=sys.stderr)
            sys.exit(1)
        try:
            output_dir = args.output or "./output"
            results = batch_process(args.dir, output_dir, args.format, args.dry_run)
            print(f"处理完成: {results['total']} 个文件")
            print(f"成功: {results['success']}, 跳过: {results['skipped']}, 失败: {results['failed']}")
            if results["failures"]:
                print("\n失败明细:")
                for failure in results["failures"]:
                    print(f"  - {failure['file']}: {failure['reason']}")
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

    # 记忆命令
    elif args.command == "memory":
        memory = SessionMemory()
        if args.save:
            if memory.save(args.save):
                print(f"已保存记忆: {args.save}")
            else:
                print(f"错误: {ErrorCode.E004}", file=sys.stderr)
                sys.exit(1)
        elif args.load:
            memories = memory.load()
            if memories:
                print("加载记忆:")
                for i, m in enumerate(memories, 1):
                    print(f"{i}. {m}")
            else:
                print("暂无记忆")
        else:
            print(f"错误: {ErrorCode.E001} - 需要 --save 或 --load", file=sys.stderr)
            sys.exit(1)

    # 提取命令
    elif args.command == "extract":
        if not args.input or not args.key:
            print(f"错误: {ErrorCode.E001} - 需要输入文件和关键词", file=sys.stderr)
            sys.exit(1)
        try:
            content = read_file_with_encoding(args.input)
            keywords = [k.strip() for k in args.key.split(",")]
            result = extract_key_info(content, keywords, args.context)
            output_content = format_output(result, args.format)

            if args.dry_run:
                print(f"[DRY-RUN] 将输出 {result['total_matches']} 条匹配")
                if args.verbose:
                    print(output_content)
            else:
                print(output_content)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
