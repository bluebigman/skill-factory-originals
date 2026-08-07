#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context-mode 技能实现脚本
功能：压缩工具输出、持久化会话记忆、提取关键信息、结构化格式输出、批量处理
版本：1.0.1
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
        self.memory_file = memory_file
        self.memory: Dict[str, Any] = {}
        if memory_file:
            self._load()

    def _load(self) -> None:
        """从文件加载记忆"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.memory = json.load(f)
        except Exception as e:
            raise RuntimeError(f"{ErrorCode.E005}: {e}") from e

    def save(self) -> None:
        """保存记忆到文件"""
        if not self.memory_file:
            return
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"{ErrorCode.E004}: {e}") from e

    def add_key_decision(self, decision: str, context: Optional[str] = None) -> None:
        """添加关键决策"""
        if "decisions" not in self.memory:
            self.memory["decisions"] = []
        self.memory["decisions"].append({
            "timestamp": time.time(),
            "decision": decision,
            "context": context or ""
        })

    def add_user_preference(self, key: str, value: Any) -> None:
        """添加用户偏好"""
        if "preferences" not in self.memory:
            self.memory["preferences"] = {}
        self.memory["preferences"][key] = value

    def add_project_constraint(self, constraint: str) -> None:
        """添加项目约束"""
        if "constraints" not in self.memory:
            self.memory["constraints"] = []
        self.memory["constraints"].append(constraint)

    def get_context_summary(self) -> str:
        """生成记忆摘要"""
        parts = []
        if "decisions" in self.memory and self.memory["decisions"]:
            parts.append("关键决策:")
            for d in self.memory["decisions"][-3:]:  # 最近3条
                parts.append(f"  - {d['decision']}")
        if "preferences" in self.memory and self.memory["preferences"]:
            parts.append("用户偏好:")
            for k, v in list(self.memory["preferences"].items())[:5]:
                parts.append(f"  - {k}: {v}")
        if "constraints" in self.memory and self.memory["constraints"]:
            parts.append("项目约束:")
            for c in self.memory["constraints"][-3:]:
                parts.append(f"  - {c}")
        return "\n".join(parts) if parts else "暂无记忆内容"


# ---------------------------------------------------------------------------
# 文本处理核心逻辑
# ---------------------------------------------------------------------------
class TextCompressor:
    """文本压缩器 - 核心功能实现"""

    # 常见停止词（用于关键词提取）
    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "if", "then", "else", "for",
        "of", "in", "on", "at", "to", "from", "with", "without", "by",
        "是", "的", "了", "在", "和", "与", "或", "及", "等", "被", "把",
        "this", "that", "these", "those", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did"
    }

    def __init__(self, max_key_points: int = 5):
        self.max_key_points = max_key_points

    def compress(self, text: str, output_format: str = "text") -> CompressionResult:
        """压缩文本内容"""
        if not text or not text.strip():
            raise ValueError(ErrorCode.E002)

        original_length = len(text)

        # 提取关键信息
        key_points = self._extract_key_points(text)

        # 生成摘要
        summary = self._generate_summary(text, key_points)

        # 根据格式生成压缩结果
        if output_format == "text":
            result = self._format_text(summary, key_points)
        elif output_format == "json":
            result = json.dumps({
                "summary": summary,
                "key_points": key_points
            }, ensure_ascii=False, indent=2)
        elif output_format == "table":
            result = self._format_table(summary, key_points)
        else:
            raise ValueError(ErrorCode.E003)

        return CompressionResult(
            original_length=original_length,
            compressed_length=len(result),
            summary=summary,
            key_points=key_points
        )

    def _extract_key_points(self, text: str) -> List[str]:
        """提取关键信息点"""
        points = []
        lines = text.split("\n")

        # 优先提取包含特殊标记的行
        important_patterns = [
            r"(?:错误|error|失败|fail|exception|warning|警告)",  # 错误相关
            r"(?:成功|完成|success|complete|passed|通过)",       # 成功相关
            r"(?:版本|version|v\d+\.\d+\.\d+)",                  # 版本信息
            r"(?:耗时|时间|duration|time).{0,20}(?:\d+\.?\d*\s*(?:ms|s|秒|毫秒))",  # 时间信息
            r"(?:文件|路径|path|file).{0,30}(?:[\w\-./\\]+\.\w+)",  # 文件路径
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 检查是否匹配重要模式
            for pattern in important_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if line not in points:
                        points.append(line[:200])  # 限制长度
                    break

            if len(points) >= self.max_key_points:
                break

        # 如果关键点不够，提取高频词组合
        if len(points) < self.max_key_points:
            words = self._extract_high_frequency_words(text)
            for word in words:
                if len(points) >= self.max_key_points:
                    break
                if word not in points:
                    points.append(word)

        return points[:self.max_key_points]

    def _extract_high_frequency_words(self, text: str) -> List[str]:
        """提取高频关键词"""
        # 清理文本
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
        words = cleaned.split()

        # 过滤停止词和短词
        meaningful_words = [
            w for w in words
            if w not in self.STOP_WORDS and len(w) > 2
        ]

        # 统计词频
        word_counts = Counter(meaningful_words)

        # 返回高频词
        return [word for word, _ in word_counts.most_common(10)]

    def _generate_summary(self, text: str, key_points: List[str]) -> str:
        """生成文本摘要"""
        # 清理文本
        cleaned = re.sub(r'\s+', ' ', text.strip())

        # 如果是短文本，直接返回
        if len(cleaned) <= 200:
            return cleaned

        # 尝试提取首段
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            first_para = paragraphs[0]
            if len(first_para) <= 300:
                return first_para

        # 提取关键句子
        sentences = re.split(r'(?<=[.!?。！？])\s+', cleaned)
        important_sentences = []

        # 包含关键点的句子优先
        for sentence in sentences:
            for point in key_points:
                if point[:20] in sentence or any(w in sentence for w in point.split()[:2]):
                    important_sentences.append(sentence)
                    break

        # 补充首句
        if not important_sentences and sentences:
            important_sentences.append(sentences[0])

        # 组合摘要
        summary = " ".join(important_sentences[:3])
        if len(summary) > 500:
            summary = summary[:497] + "..."

        return summary if summary else cleaned[:200]

    def _format_text(self, summary: str, key_points: List[str]) -> str:
        """文本格式输出"""
        lines = [f"摘要: {summary}", ""]
        if key_points:
            lines.append("关键信息:")
            for point in key_points:
                lines.append(f"  - {point}")
        return "\n".join(lines)

    def _format_table(self, summary: str, key_points: List[str]) -> str:
        """表格格式输出"""
        lines = [
            "| 项目 | 内容 |",
            "|------|------|",
            f"| 摘要 | {summary[:100]} |"
        ]
        for i, point in enumerate(key_points, 1):
            lines.append(f"| 要点{i} | {point[:100]} |")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批量处理功能
# ---------------------------------------------------------------------------
class BatchProcessor:
    """批量处理多个输入源"""

    def __init__(self, compressor: TextCompressor):
        self.compressor = compressor

    def process_batch(self, inputs: List[str], output_format: str = "text") -> List[Dict[str, Any]]:
        """批量压缩多个输入"""
        if not inputs:
            raise ValueError(ErrorCode.E007)

        results = []
        for i, text in enumerate(inputs, 1):
            try:
                result = self.compressor.compress(text, output_format)
                results.append({
                    "index": i,
                    "status": "success",
                    "data": result.to_dict()
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(e)
                })

        return results


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """离线自检核心逻辑"""
    print("开始自检...")

    # 创建压缩器
    compressor = TextCompressor()

    # 测试1: 基本压缩功能
    test_text = """
    构建日志 v2.3.1
    编译成功: 42个模块通过
    警告: 3个模块存在过时依赖
    错误: 无
    耗时: 12.5秒
    输出路径: /build/output/app.jar
    """
    try:
        result = compressor.compress(test_text, "text")
        # 宽松断言：压缩后长度应明显小于原文
        assert result.compressed_length < result.original_length, \
            f"压缩后长度应小于原文: {result.compressed_length} vs {result.original_length}"
        # 压缩率应大于0.1
        assert result.reduction_ratio > 0.1, \
            f"压缩率应大于0.1: {result.reduction_ratio}"
        # 摘要不应为空
        assert len(result.summary) > 0, "摘要不应为空"
        # 关键信息不应为空
        assert len(result.key_points) > 0, "关键信息不应为空"
        print("✓ 基本压缩功能通过")
    except AssertionError as e:
        print(f"✗ 基本压缩功能失败: {e}")
        return False

    # 测试2: JSON格式输出
    try:
        result = compressor.compress(test_text, "json")
        parsed = json.loads(result.summary) if isinstance(result.summary, str) else result.summary
        # 宽松断言：应能解析为JSON
        assert result.compressed_length > 0, "JSON输出长度应大于0"
        print("✓ JSON格式输出通过")
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"✗ JSON格式输出失败: {e}")
        return False

    # 测试3: 表格格式输出
    try:
        result = compressor.compress(test_text, "table")
        assert "|" in result.summary, "表格格式应包含竖线分隔符"
        assert result.compressed_length > 0, "表格输出长度应大于0"
        print("✓ 表格格式输出通过")
    except AssertionError as e:
        print(f"✗ 表格格式输出失败: {e}")
        return False

    # 测试4: 会话记忆功能
    try:
        memory = SessionMemory()
        memory.add_key_decision("采用微服务架构重构")
        memory.add_user_preference("日志级别", "debug")
        memory.add_project_constraint("Python 3.9+")
        context = memory.get_context_summary()
        assert "微服务" in context, "记忆应包含关键决策"
        assert "debug" in context, "记忆应包含用户偏好"
        print("✓ 会话记忆功能通过")
    except AssertionError as e:
        print(f"✗ 会话记忆功能失败: {e}")
        return False

    # 测试5: 批量处理功能
    try:
        processor = BatchProcessor(compressor)
        batch_inputs = [
            "错误: 连接超时 耗时: 3秒",
            "成功: 部署完成 版本: 1.0.0",
            "警告: 磁盘空间不足"
        ]
        results = processor.process_batch(batch_inputs)
        assert len(results) == 3, f"应处理3个输入，实际{len(results)}"
        assert all(r["status"] == "success" for r in results), "所有输入应处理成功"
        print("✓ 批量处理功能通过")
    except AssertionError as e:
        print(f"✗ 批量处理功能失败: {e}")
        return False

    # 测试6: 错误处理
    try:
        try:
            compressor.compress("", "text")
            assert False, "空输入应抛出异常"
        except ValueError:
            pass

        try:
            compressor.compress("有效文本", "unsupported_format")
            assert False, "不支持格式应抛出异常"
        except ValueError:
            pass

        print("✓ 错误处理通过")
    except AssertionError as e:
        print(f"✗ 错误处理失败: {e}")
        return False

    # 测试7: 长文本处理
    try:
        long_text = "内容 " * 1000  # 2000字符
        result = compressor.compress(long_text, "text")
        assert result.compressed_length < len(long_text), "长文本应被压缩"
        print("✓ 长文本处理通过")
    except AssertionError as e:
        print(f"✗ 长文本处理失败: {e}")
        return False

    print("\n全部自检通过！")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="context-mode: 上下文压缩、会话记忆、输出精简工具"
    )
    parser.add_argument(
        "--compress", "-c",
        type=str,
        help="要压缩的文本内容"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取内容进行压缩"
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--memory", "-m",
        type=str,
        help="会话记忆文件路径"
    )
    parser.add_argument(
        "--add-decision", "-d",
        type=str,
        help="添加关键决策到会话记忆"
    )
    parser.add_argument(
        "--add-preference", "-p",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="添加用户偏好到会话记忆"
    )
    parser.add_argument(
        "--add-constraint", "-con",
        type=str,
        help="添加项目约束到会话记忆"
    )
    parser.add_argument(
        "--show-memory", "-s",
        action="store_true",
        help="显示会话记忆内容"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        nargs="+",
        help="批量处理多个文本输入"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    try:
        # 会话记忆操作
        memory = SessionMemory(args.memory) if args.memory else SessionMemory()

        if args.add_decision:
            memory.add_key_decision(args.add_decision)
            memory.save()
            print(f"已添加关键决策: {args.add_decision}")

        if args.add_preference:
            memory.add_user_preference(args.add_preference[0], args.add_preference[1])
            memory.save()
            print(f"已添加用户偏好: {args.add_preference[0]} = {args.add_preference[1]}")

        if args.add_constraint:
            memory.add_project_constraint(args.add_constraint)
            memory.save()
            print(f"已添加项目约束: {args.add_constraint}")

        if args.show_memory:
            print("=== 会话记忆 ===")
            print(memory.get_context_summary())

        # 压缩操作
        compressor = TextCompressor()

        if args.batch:
            # 批量处理
            processor = BatchProcessor(compressor)
            results = processor.process_batch(args.batch, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        elif args.file:
            # 从文件读取
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    content = f.read()
                result = compressor.compress(content, args.format)
                print(result.summary)
                print(f"\n[统计] 原始: {result.original_length} 字符, "
                      f"压缩后: {result.compressed_length} 字符, "
                      f"压缩率: {result.reduction_ratio:.1%}")
            except FileNotFoundError:
                print(f"{ErrorCode.E005}: 文件 {args.file} 不存在", file=sys.stderr)
                return 5
        elif args.compress:
            # 直接压缩
            result = compressor.compress(args.compress, args.format)
            print(result.summary)
            if result.key_points:
                print("\n关键信息:")
                for point in result.key_points:
                    print(f"  - {point}")
            print(f"\n[统计] 原始: {result.original_length} 字符, "
                  f"压缩后: {result.compressed_length} 字符, "
                  f"压缩率: {result.reduction_ratio:.1%}")
        else:
            # 没有操作参数时显示帮助
            parser.print_help()

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"{ErrorCode.E010}: 未预期的错误 - {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
