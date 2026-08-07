#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context-mode 技能独立实现脚本
版本: 1.0.2 (clean-room 实现)
功能: 压缩工具输出、持久化会话记忆、输出精简
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误或参数缺失",
    "E002": "输入数据为空或无效",
    "E003": "输入数据不是合法UTF-8文本",
    "E004": "JSON解析失败",
    "E005": "输出格式不受支持",
    "E006": "会话记忆文件写入失败",
    "E007": "会话记忆文件读取失败",
    "E008": "批量处理时某个输入项失败",
    "E009": "内部逻辑错误（不应发生）",
    "E010": "未知错误",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出程序"""
    err_msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        print(f"[ERROR] {code}: {err_msg} - {message}", file=sys.stderr)
    else:
        print(f"[ERROR] {code}: {err_msg}", file=sys.stderr)
    sys.exit(1)


@dataclass
class CompressionResult:
    """压缩结果数据类"""
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    original_lines: int = 0
    compressed_lines: int = 0
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    timestamp: str = ""


class TextCompressor:
    """文本压缩器：从长文本中提取核心信息"""
    
    # 需要保留的行类型（正则模式）
    IMPORTANT_PATTERNS = [
        r"(?i)^(error|fail|exception|fatal|critical)[:\s]",
        r"(?i)^(warning|warn)[:\s]",
        r"(?i)^(success|ok|pass|done)[:\s]",
        r"(?i)^(summary|result|output)[:\s]",
        r"(?i)^(test|suite|case)[:\s]",
        r"(?i)^(total|count|number)[:\s]",
        r"(?i)^(version|release|build)[:\s]",
        r"(?i)^(commit|branch|tag)[:\s]",
        r"^\s*[-*+]\s+\S+",  # 列表项
        r"^\s*\d+[.):]\s+\S+",  # 编号项
        r"(?i)^(info|debug|trace)[:\s]",  # 保留info级别日志
        r"^\s*File\s+\".+\",\s+line\s+\d+",  # 文件位置
        r"^\s*\w+Error:",  # 各种Error
    ]
    
    # 常见停用词
    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "if", "then", "else",
        "for", "with", "from", "this", "that", "these", "those",
        "是", "的", "了", "在", "和", "与", "及", "或", "为", "以",
        "to", "of", "in", "on", "at", "by", "be", "is", "are", "was",
        "it", "its", "as", "so", "such", "not", "no", "yes", "all",
        "will", "would", "can", "could", "should", "may", "might",
        "must", "shall", "do", "does", "did", "has", "have", "had",
    }
    
    def __init__(self, max_lines: int = 30, max_chars: int = 2000):
        self.max_lines = max_lines
        self.max_chars = max_chars
    
    def compress(self, text: str) -> CompressionResult:
        """压缩文本，返回结构化结果"""
        if not text or not text.strip():
            raise ValueError("输入文本为空")
        
        # 尝试解码（如果传入的是bytes则自动解码）
        if isinstance(text, bytes):
            try:
                text = text.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("无法解码为UTF-8")
        
        original_size = len(text.encode("utf-8"))
        original_lines = len(text.splitlines())
        
        # 提取重要行
        important_lines = self._extract_important_lines(text)
        
        # 提取关键词
        keywords = self._extract_keywords(text)
        
        # 生成摘要
        summary = self._generate_summary(text, important_lines)
        
        # 计算压缩后大小
        compressed_size = len(summary.encode("utf-8"))
        compressed_lines = len(summary.splitlines())
        
        # 计算压缩率
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
        
        return CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            original_lines=original_lines,
            compressed_lines=compressed_lines,
            summary=summary,
            keywords=keywords,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
    
    def _extract_important_lines(self, text: str) -> List[str]:
        """提取重要行"""
        lines = text.splitlines()
        important = []
        
        # 先处理所有行，收集重要行
        all_important = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # 检查是否匹配重要模式
            is_important = False
            for pattern in self.IMPORTANT_PATTERNS:
                if re.match(pattern, stripped):
                    is_important = True
                    break
            
            # 长度适中且包含数字的行也保留
            if not is_important and 10 <= len(stripped) <= 200 and re.search(r"\d", stripped):
                is_important = True
            
            # 包含关键字的行也保留
            if not is_important and any(kw in stripped.lower() for kw in ['build', 'test', 'error', 'fail']):
                is_important = True
            
            if is_important:
                all_important.append(stripped)
        
        # 如果重要行太多，截断
        if len(all_important) > self.max_lines:
            # 优先保留错误和警告
            error_lines = [l for l in all_important if re.match(r"(?i)^(error|fail|exception|fatal|critical)", l)]
            warning_lines = [l for l in all_important if re.match(r"(?i)^(warning|warn)", l)]
            other_lines = [l for l in all_important if l not in error_lines and l not in warning_lines]
            
            # 组合并截断
            important = (error_lines + warning_lines + other_lines)[:self.max_lines]
        else:
            important = all_important
        
        return important[:self.max_lines]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 分词
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_]*|\d+", text.lower())
        
        # 过滤停用词和过短的词
        filtered = [w for w in words if w not in self.STOP_WORDS and len(w) > 1]
        
        # 统计词频
        word_count: Dict[str, int] = {}
        for word in filtered:
            word_count[word] = word_count.get(word, 0) + 1
        
        # 按频率排序取前10
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:10]]
    
    def _generate_summary(self, text: str, important_lines: List[str]) -> str:
        """生成摘要文本"""
        if not important_lines:
            # 如果没有重要行，取前几行
            lines = text.splitlines()
            important_lines = [l.strip() for l in lines[:10] if l.strip()]
        
        # 构建摘要
        summary_lines = ["# 压缩摘要", f"# 原始: {len(text.splitlines())} 行, {len(text.encode('utf-8'))} 字节"]
        summary_lines.append(f"# 压缩: {len(important_lines)} 行")
        summary_lines.append("")
        
        for line in important_lines:
            # 截断超长行
            if len(line) > 200:
                line = line[:197] + "..."
            summary_lines.append(line)
        
        return "\n".join(summary_lines)


class SessionMemory:
    """会话记忆管理器：持久化关键信息到JSON文件"""
    
    def __init__(self, memory_file: str = ".context_memory.json"):
        self.memory_file = memory_file
        self.memory: Dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """从文件加载记忆"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.memory = json.load(f)
            except (json.JSONDecodeError, OSError):
                # 文件损坏时重新初始化
                self.memory = {}
    
    def save(self) -> None:
        """保存记忆到文件"""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except OSError:
            raise IOError("无法写入会话记忆文件")
    
    def set(self, key: str, value: Any) -> None:
        """设置记忆项"""
        self.memory[key] = {
            "value": value,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取记忆项"""
        if key in self.memory:
            return self.memory[key].get("value")
        return None
    
    def delete(self, key: str) -> bool:
        """删除记忆项"""
        if key in self.memory:
            del self.memory[key]
            return True
        return False
    
    def list_keys(self) -> List[str]:
        """列出所有记忆键"""
        return list(self.memory.keys())
    
    def clear(self) -> None:
        """清空所有记忆"""
        self.memory = {}


class OutputFormatter:
    """输出格式化器：支持多种输出格式"""
    
    @staticmethod
    def format(result: CompressionResult, fmt: str = "text") -> str:
        """格式化输出"""
        if fmt == "json":
            return json.dumps(asdict(result), ensure_ascii=False, indent=2)
        elif fmt == "table":
            return OutputFormatter._format_table(result)
        elif fmt == "text":
            return OutputFormatter._format_text(result)
        else:
            raise ValueError(f"不支持的输出格式: {fmt}")
    
    @staticmethod
    def _format_text(result: CompressionResult) -> str:
        """文本格式输出"""
        lines = [
            f"压缩率: {result.compression_ratio:.1f}%",
            f"原始: {result.original_lines} 行 / {result.original_size} 字节",
            f"压缩: {result.compressed_lines} 行 / {result.compressed_size} 字节",
            f"关键词: {', '.join(result.keywords[:5])}",
            "",
            "--- 摘要 ---",
            result.summary,
        ]
        return "\n".join(lines)
    
    @staticmethod
    def _format_table(result: CompressionResult) -> str:
        """表格格式输出"""
        rows = [
            ["指标", "原始", "压缩后", "压缩率"],
            ["行数", str(result.original_lines), str(result.compressed_lines), f"{result.compression_ratio:.1f}%"],
            ["大小", f"{result.original_size}B", f"{result.compressed_size}B", f"{result.compression_ratio:.1f}%"],
        ]
        
        # 计算列宽
        col_widths = [max(len(row[i]) for row in rows) + 2 for i in range(4)]
        
        # 构建表格
        table_lines = []
        for row in rows:
            line = "|".join(row[i].ljust(col_widths[i]) for i in range(4))
            table_lines.append(line)
            if row == rows[0]:
                table_lines.append("-" * len(line))
        
        table_lines.append("")
        table_lines.append(f"关键词: {', '.join(result.keywords[:5])}")
        table_lines.append("")
        table_lines.append("--- 摘要 ---")
        table_lines.append(result.summary)
        
        return "\n".join(table_lines)


def process_text(text: str, fmt: str = "text", max_lines: int = 30) -> str:
    """处理文本：压缩并格式化输出"""
    compressor = TextCompressor(max_lines=max_lines)
    result = compressor.compress(text)
    return OutputFormatter.format(result, fmt)


def process_batch(inputs: List[str], fmt: str = "text") -> str:
    """批量处理多个输入"""
    compressor = TextCompressor()
    results = []
    
    for i, text in enumerate(inputs):
        try:
            result = compressor.compress(text)
            results.append({
                "index": i + 1,
                "result": asdict(result),
            })
        except Exception as e:
            results.append({
                "index": i + 1,
                "error": str(e),
            })
    
    if fmt == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    output_lines = []
    for item in results:
        if "error" in item:
            output_lines.append(f"[批次 {item['index']}] 错误: {item['error']}")
        else:
            r = item["result"]
            output_lines.append(f"[批次 {item['index']}] 压缩率: {r['compression_ratio']:.1f}%")
    
    return "\n".join(output_lines)


def run_selftest() -> None:
    """内置自检：使用硬编码样例数据验证核心逻辑"""
    print("[SELFTEST] 开始离线自检...")
    
    # 测试样例（硬编码，不依赖外部文件）
    test_text = """
    INFO: Starting build process...
    ERROR: Failed to compile module 'core/utils.py'
    WARNING: Deprecated API used in line 42
    SUCCESS: Build completed in 3.2 seconds
    Total tests: 128, Passed: 125, Failed: 3
    Version: 2.1.0
    Commit: abc123def456
    Branch: main
    - Fixed memory leak in cache module
    - Updated dependencies
    - Added new API endpoint
    Error details:
    Traceback (most recent call last):
      File "main.py", line 45, in <module>
        raise ValueError("Invalid input")
    ValueError: Invalid input
    Some random debug output that should be filtered
    lorem ipsum dolor sit amet consectetur adipiscing elit
    """
    
    # 测试1: 文本压缩
    print("[SELFTEST] 测试文本压缩...")
    compressor = TextCompressor(max_lines=20)
    result = compressor.compress(test_text)
    
    # 宽松断言
    assert result.original_size > 0, "原始大小应大于0"
    assert result.original_lines > 0, "原始行数应大于0"
    assert result.compressed_size > 0, "压缩后大小应大于0"
    assert len(result.summary) > 0, "摘要不应为空"
    assert len(result.keywords) > 0, "应提取到关键词"
    assert result.compressed_lines <= result.original_lines, "压缩后行数不应超过原始行数"
    assert result.compressed_size < result.original_size, "压缩后大小应小于原始大小"
    assert result.compression_ratio > 30, "压缩率应大于30%"
    print(f"      压缩率: {result.compression_ratio:.1f}%, 关键词数: {len(result.keywords)}")
    
    # 测试2: 错误处理
    print("[SELFTEST] 测试错误处理...")
    try:
        compressor.compress("")
        assert False, "空输入应抛出异常"
    except ValueError:
        print("      空输入异常处理正常")
    
    # 测试3: 输出格式化
    print("[SELFTEST] 测试输出格式化...")
    text_fmt = OutputFormatter.format(result, "text")
    json_fmt = OutputFormatter.format(result, "json")
    table_fmt = OutputFormatter.format(result, "table")
    
    assert len(text_fmt) > 0, "文本格式输出不应为空"
    assert len(json_fmt) > 0, "JSON格式输出不应为空"
    assert len(table_fmt) > 0, "表格格式输出不应为空"
    
    # 验证JSON可解析
    json_data = json.loads(json_fmt)
    assert "original_size" in json_data, "JSON输出应包含original_size字段"
    assert "compression_ratio" in json_data, "JSON输出应包含compression_ratio字段"
    print("      三种格式输出正常")
    
    # 测试4: 会话记忆
    print("[SELFTEST] 测试会话记忆...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_file = os.path.join(tmpdir, "test_memory.json")
        memory = SessionMemory(memory_file)
        
        # 写入记忆
        memory.set("project_name", "test-project")
        memory.set("build_status", "success")
        memory.save()
        
        # 重新加载验证持久化
        memory2 = SessionMemory(memory_file)
        assert memory2.get("project_name") == "test-project", "记忆应正确持久化"
        assert memory2.get("build_status") == "success", "记忆应正确持久化"
        assert memory2.get("nonexistent") is None, "不存在记忆应返回None"
        
        # 删除记忆
        assert memory2.delete("project_name") == True, "删除存在的记忆应返回True"
        assert memory2.delete("nonexistent") == False, "删除不存在的记忆应返回False"
        print("      会话记忆读写正常")
    
    # 测试5: 批量处理
    print("[SELFTEST] 测试批量处理...")
    batch_inputs = [
        "Test log line 1\nError: something failed after 5 retries",
        "Build successful in 10 seconds\nAll 42 tests passed",
    ]
    batch_output = process_batch(batch_inputs, "json")
    batch_data = json.loads(batch_output)
    assert len(batch_data) == 2, "批量处理应返回2个结果"
    assert "result" in batch_data[0], "第一个批次项应包含result"
    assert "result" in batch_data[1], "第二个批次项应包含result"
    print("      批量处理正常")
    
    # 测试6: 边界情况
    print("[SELFTEST] 测试边界情况...")
    edge_text = "a" * 10  # 极短文本
    edge_result = compressor.compress(edge_text)
    assert edge_result.compressed_size > 0, "极短文本也应能压缩"
    
    edge_text2 = "\n".join([f"Line {i} with some content" for i in range(100)])
    edge_result2 = compressor.compress(edge_text2)
    assert edge_result2.compressed_lines > 0, "多行文本应能压缩"
    assert edge_result2.compressed_lines <= 20, "压缩后行数不应超过max_lines限制"
    print("      边界情况处理正常")
    
    print("[SELFTEST] 所有自检通过 ✓")


def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="上下文压缩与会话记忆工具 (context-mode v1.0.2)"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本文件路径（不指定则从stdin读取）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=30,
        help="压缩时保留的最大行数 (默认: 30)"
    )
    parser.add_argument(
        "--memory",
        type=str,
        default=".context_memory.json",
        help="会话记忆文件路径 (默认: .context_memory.json)"
    )
    parser.add_argument(
        "--memory-set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="设置会话记忆项"
    )
    parser.add_argument(
        "--memory-get",
        metavar="KEY",
        help="获取会话记忆项"
    )
    parser.add_argument(
        "--memory-list",
        action="store_true",
        help="列出所有会话记忆项"
    )
    parser.add_argument(
        "--memory-clear",
        action="store_true",
        help="清空所有会话记忆项"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件列表（逗号分隔）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        run_selftest()
        return
    
    # 处理会话记忆操作
    if args.memory_set or args.memory_get or args.memory_list or args.memory_clear:
        try:
            memory = SessionMemory(args.memory)
            
            if args.memory_set:
                key, value = args.memory_set
                memory.set(key, value)
                memory.save()
                print(f"已设置记忆: {key} = {value}")
            
            if args.memory_get:
                value = memory.get(args.memory_get)
                if value is not None:
                    print(f"{args.memory_get}: {value}")
                else:
                    print(f"记忆不存在: {args.memory_get}")
            
            if args.memory_list:
                keys = memory.list_keys()
                if keys:
                    print("会话记忆项:")
                    for key in keys:
                        print(f"  - {key}")
                else:
                    print("会话记忆为空")
            
            if args.memory_clear:
                memory.clear()
                memory.save()
                print("会话记忆已清空")
            
            return
        except IOError as e:
            error_exit("E006", str(e))
    
    # 批量处理
    if args.batch:
        try:
            file_paths = [p.strip() for p in args.batch.split(",")]
            texts = []
            for path in file_paths:
                if not os.path.exists(path):
                    error_exit("E001", f"文件不存在: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    texts.append(f.read())
            
            output = process_batch(texts, args.format)
            print(output)
            return
        except UnicodeDecodeError:
            error_exit("E003", "文件编码不是UTF-8")
        except Exception as e:
            error_exit("E008", str(e))
    
    # 读取输入
    try:
        if args.input:
            if not os.path.exists(args.input):
                error_exit("E001", f"文件不存在: {args.input}")
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            # 从stdin读取
            text = sys.stdin.read()
            if not text or not text.strip():
                error_exit("E002", "stdin没有输入数据")
    except UnicodeDecodeError:
        error_exit("E003", "输入文件编码不是UTF-8")
    except Exception as e:
        error_exit("E010", str(e))
    
    # 压缩处理
    try:
        output = process_text(text, args.format, args.max_lines)
        print(output)
    except ValueError as e:
        error_exit("E002", str(e))
    except Exception as e:
        error_exit("E010", str(e))


if __name__ == "__main__":
    main()
