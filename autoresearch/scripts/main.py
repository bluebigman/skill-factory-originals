#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autoresearch - 单卡训练数据自动整理工具

本工具面向单GPU nanochat训练，自动完成数据采集、清洗与结构化整理。
支持多格式输入输出、置信度标注、批量处理与预览模式。

错误码说明:
    E001: 参数错误（无效的命令行参数）
    E002: 输入数据为空或格式不正确
    E003: 文件读取失败
    E004: 输出写入失败
    E005: 内部处理异常
    E006: 不支持的输出格式
    E007: 数据解析失败（无法从文本中提取有效信息）
    E008: 批量处理时某一条目处理失败
    E009: 配置错误（无效的配置参数）
    E010: 未预期的运行时错误

用法示例:
    python run.py --input ./raw_data --output ./processed
    python run.py --input ./raw_data --output ./processed --format csv
    python run.py --input ./raw_data --output ./processed --batch --format jsonl
    python run.py --input ./raw_data --output ./processed --dry-run --verbose
    python run.py --selftest
"""

import argparse
import json
import re
import sys
import tempfile
import os
import time
import concurrent.futures
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志

try:
    import pandas as pd
    import numpy as np
    import chardet
except ImportError:
    print("警告: 缺少依赖库，请运行 pip install pandas numpy chardet", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

VERSION = "2.0.0"

# 支持的输出格式
SUPPORTED_FORMATS = ("json", "jsonl", "csv")

# 默认输出字段
DEFAULT_FIELDS = ["instruction", "input", "output", "confidence", "needs_review", "source_file"]

# 字段占位符（信息缺失时使用）
PLACEHOLDER_TEMPLATE = "[需核实:{field}]"

# 解析正则表达式（用于关键信息提取）
PATTERN_QA = re.compile(
    r"(?:问|Q|问题|question|instruction)[：:\s]+(.+?)(?:答|A|答案|answer|output)[：:\s]+(.+)",
    re.IGNORECASE | re.DOTALL,
)
PATTERN_MD_HEADING = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
PATTERN_HTML_TAG = re.compile(r"<[^>]+>")
PATTERN_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
PATTERN_MD_BOLD = re.compile(r"\*\*([^*]+)\*\*")
PATTERN_MD_ITALIC = re.compile(r"\*([^*]+)\*")
PATTERN_MD_CODE = re.compile(r"`([^`]+)`")
PATTERN_WHITESPACE = re.compile(r"\s+")
PATTERN_SPECIAL_CHARS = re.compile(r"[^\w\s\u4e00-\u9fff，。！？、；：""''（）《》【】\-—…·]")

# 编码列表（按优先级排序）
ENCODINGS = ["utf-8", "gbk", "gb18030"]

# 网络请求配置
HTTP_TIMEOUT = 10
HTTP_MAX_RETRIES = 3
HTTP_BACKOFF_BASE = 2.0

# 文件大小限制
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


# ---------------------------------------------------------------------------
# 异常与错误处理
# ---------------------------------------------------------------------------

class AutoResearchError(Exception):
    """基础异常类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class ParameterError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E001", message)


class EmptyInputError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E002", message)


class FileReadError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E003", message)


class OutputWriteError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E004", message)


class InternalError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E005", message)


class UnsupportedFormatError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E006", message)


class ParseError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E007", message)


class BatchProcessError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E008", message)


class ConfigError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E009", message)


class RuntimeError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__("E010", message)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def get_utc_now() -> str:
    """获取 UTC 当前时间"""
    return datetime.now(timezone.utc).isoformat()


def safe_read_file(file_path: str) -> str:
    """安全读取文件，支持多编码"""
    try:
        # 先探测编码
        with open(file_path, "rb") as f:
            raw_data = f.read()
        
        detected = chardet.detect(raw_data)
        encodings = [detected["encoding"]] if detected["encoding"] else []
        encodings.extend(ENCODINGS)
        
        for enc in encodings:
            try:
                return raw_data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 最后尝试 replace 模式
        return raw_data.decode("utf-8", errors="replace")
    except FileNotFoundError:
        raise FileReadError(f"文件不存在: {file_path}")
    except PermissionError:
        raise FileReadError(f"权限不足: {file_path}")
    except Exception as e:
        raise FileReadError(f"读取失败: {file_path} - {str(e)}")


def atomic_write(file_path: str, content: str) -> None:
    """原子化写入文件"""
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        fd, tmp_path = tempfile.mkstemp(dir=dir_path or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, file_path)
        except Exception:
            os.unlink(tmp_path)
            raise
    except Exception as e:
        raise OutputWriteError(f"写入失败: {file_path} - {str(e)}")


def validate_path(path: str) -> str:
    """路径白名单校验，防止路径穿越"""
    p = Path(path).resolve()
    # 检查路径中是否包含 .. 或绝对路径穿越
    if ".." in path.split("/"):
        raise ParameterError(f"路径包含非法字符: {path}")
    return str(p)


def compute_hash(text: str) -> str:
    """计算文本哈希用于去重"""
    return hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()


def with_retry(func, *args, max_retries: int = HTTP_MAX_RETRIES, **kwargs):
    """带指数退避的重试机制"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = HTTP_BACKOFF_BASE ** attempt
            print(f"重试 {attempt + 1}/{max_retries}: {str(e)}，等待 {wait_time}s", file=sys.stderr)
            time.sleep(wait_time)
    return None


# ---------------------------------------------------------------------------
# 数据清洗模块
# ---------------------------------------------------------------------------

def clean_text(text: str, verbose: bool = False) -> str:
    """清洗文本：去除HTML标签、Markdown残留、特殊字符等"""
    original_len = len(text)
    
    # 去除 HTML 标签
    text = PATTERN_HTML_TAG.sub("", text)
    
    # 处理 Markdown 链接
    text = PATTERN_MD_LINK.sub(r"\1", text)
    
    # 处理 Markdown 加粗/斜体/代码
    text = PATTERN_MD_BOLD.sub(r"\1", text)
    text = PATTERN_MD_ITALIC.sub(r"\1", text)
    text = PATTERN_MD_CODE.sub(r"\1", text)
    
    # 去除特殊字符（保留中文标点）
    text = PATTERN_SPECIAL_CHARS.sub("", text)
    
    # 合并空白
    text = PATTERN_WHITESPACE.sub(" ", text)
    
    # 去除空行
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    
    if verbose:
        removed = original_len - len(text)
        print(f"清洗: 移除 {removed} 字符 ({original_len} -> {len(text)})", file=sys.stderr)
    
    return text


def deduplicate(records: List[Dict]) -> List[Dict]:
    """去重：基于 instruction+output 的哈希"""
    seen = set()
    result = []
    for record in records:
        key = compute_hash(f"{record.get('instruction', '')}|{record.get('output', '')}")
        if key not in seen:
            seen.add(key)
            result.append(record)
    return result


# ---------------------------------------------------------------------------
# 数据解析模块
# ---------------------------------------------------------------------------

def parse_qa_pairs(text: str, source_file: str = "") -> List[Dict]:
    """从文本中解析问答对"""
    records = []
    
    # 尝试匹配显式问答格式
    matches = PATTERN_QA.findall(text)
    for question, answer in matches:
        question = clean_text(question)
        answer = clean_text(answer)
        if question and answer:
            records.append({
                "instruction": question,
                "input": "",
                "output": answer,
                "confidence": 0.92,
                "needs_review": False,
                "source_file": source_file,
            })
    
    # 尝试匹配 Markdown 标题格式
    if not records:
        lines = text.splitlines()
        current_heading = None
        current_content = []
        
        for line in lines:
            heading_match = PATTERN_MD_HEADING.match(line.strip())
            if heading_match:
                if current_heading and current_content:
                    content = clean_text(" ".join(current_content))
                    if content:
                        records.append({
                            "instruction": clean_text(current_heading),
                            "input": "",
                            "output": content,
                            "confidence": 0.85,
                            "needs_review": False,
                            "source_file": source_file,
                        })
                current_heading = heading_match.group(1)
                current_content = []
            else:
                if current_heading:
                    current_content.append(line)
        
        # 处理最后一个标题
        if current_heading and current_content:
            content = clean_text(" ".join(current_content))
            if content:
                records.append({
                    "instruction": clean_text(current_heading),
                    "input": "",
                    "output": content,
                    "confidence": 0.85,
                    "needs_review": False,
                    "source_file": source_file,
                })
    
    # 如果还是没有记录，尝试按段落切分
    if not records:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i in range(0, len(paragraphs) - 1, 2):
            if i + 1 < len(paragraphs):
                records.append({
                    "instruction": clean_text(paragraphs[i]),
                    "input": "",
                    "output": clean_text(paragraphs[i + 1]),
                    "confidence": 0.7,
                    "needs_review": True,
                    "source_file": source_file,
                })
    
    return records


def parse_json_file(file_path: str) -> List[Dict]:
    """解析 JSON 文件"""
    content = safe_read_file(file_path)
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            raise ParseError(f"JSON 格式不正确: {file_path}")
    except json.JSONDecodeError as e:
        raise ParseError(f"JSON 解析失败: {file_path} - {str(e)}")


def parse_csv_file(file_path: str) -> List[Dict]:
    """解析 CSV 文件"""
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
        return df.to_dict("records")
    except Exception as e:
        raise ParseError(f"CSV 解析失败: {file_path} - {str(e)}")


def parse_file(file_path: str) -> List[Dict]:
    """根据文件扩展名解析文件"""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".json":
        return parse_json_file(file_path)
    elif ext == ".csv":
        return parse_csv_file(file_path)
    elif ext in (".txt", ".md", ".markdown"):
        content = safe_read_file(file_path)
        return parse_qa_pairs(content, source_file=os.path.basename(file_path))
    else:
        # 默认按文本处理
        content = safe_read_file(file_path)
        return parse_qa_pairs(content, source_file=os.path.basename(file_path))


# ---------------------------------------------------------------------------
# 置信度计算模块
# ---------------------------------------------------------------------------

def calculate_confidence(record: Dict) -> Tuple[float, bool]:
    """计算置信度并判断是否需要人工审核"""
    confidence = record.get("confidence", 0.5)
    
    # 检查字段完整性
    instruction = record.get("instruction", "")
    output = record.get("output", "")
    
    if not instruction or not output:
        confidence *= 0.5
    elif len(instruction) < 5 or len(output) < 10:
        confidence *= 0.8
    
    # 检查是否包含占位符
    if "[需核实" in instruction or "[需核实" in output:
        confidence *= 0.3
    
    # 检查文本质量
    if len(instruction) > 500 or len(output) > 2000:
        confidence *= 0.9
    
    needs_review = confidence < 0.6
    
    return round(min(confidence, 1.0), 2), needs_review


# ---------------------------------------------------------------------------
# 核心处理模块
# ---------------------------------------------------------------------------

def process_file(file_path: str, schema: Dict, min_confidence: float, dedupe: bool, verbose: bool = False) -> List[Dict]:
    """处理单个文件"""
    try:
        if verbose:
            print(f"处理文件: {file_path}", file=sys.stderr)
        
        records = parse_file(file_path)
        
        # 应用 schema 映射
        if schema:
            mapped_records = []
            for record in records:
                mapped = {}
                for target, source in schema.items():
                    if source in record:
                        mapped[target] = record[source]
                    else:
                        mapped[target] = PLACEHOLDER_TEMPLATE.format(field=target)
                mapped["source_file"] = os.path.basename(file_path)
                mapped_records.append(mapped)
            records = mapped_records
        
        # 计算置信度
        for record in records:
            confidence, needs_review = calculate_confidence(record)
            record["confidence"] = confidence
            record["needs_review"] = needs_review
        
        # 去重
        if dedupe:
            records = deduplicate(records)
        
        if verbose:
            print(f"  解析到 {len(records)} 条记录", file=sys.stderr)
        
        return records
    except AutoResearchError as e:
        print(f"警告: {e.message}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"警告: 处理文件 {file_path} 时出错: {str(e)}", file=sys.stderr)
        return []


def process_directory(input_dir: str, schema: Dict, min_confidence: float, dedupe: bool, batch: bool, verbose: bool = False) -> List[Dict]:
    """处理目录下的所有文件"""
    all_records = []
    
    try:
        files = []
        for root, dirs, filenames in os.walk(input_dir):
            for filename in filenames:
                if filename.endswith((".txt", ".md", ".markdown", ".json", ".csv")):
                    file_path = os.path.join(root, filename)
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_FILE_SIZE:
                        print(f"警告: 文件 {file_path} 超过 500MB，跳过", file=sys.stderr)
                        continue
                    files.append(file_path)
        
        if not files:
            raise EmptyInputError(f"目录 {input_dir} 中没有找到支持的文本文件")
        
        if batch and len(files) > 1:
            # 批量模式：多线程并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(files))) as executor:
                future_to_file = {
                    executor.submit(process_file, f, schema, min_confidence, dedupe, verbose): f
                    for f in files
                }
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        records = future.result()
                        all_records.extend(records)
                    except Exception as e:
                        print(f"警告: 处理文件 {file_path} 失败: {str(e)}", file=sys.stderr)
        else:
            # 单文件模式
            for file_path in files:
                records = process_file(file_path, schema, min_confidence, dedupe, verbose)
                all_records.extend(records)
        
        # 全局去重
        if dedupe:
            all_records = deduplicate(all_records)
        
        return all_records
    except AutoResearchError:
        raise
    except Exception as e:
        raise InternalError(f"处理目录失败: {str(e)}")


# ---------------------------------------------------------------------------
# 输出模块
# ---------------------------------------------------------------------------

def format_output(records: List[Dict], output_format: str) -> str:
    """格式化输出内容"""
    if output_format == "json":
        return json.dumps(records, ensure_ascii=False, indent=2)
    elif output_format == "jsonl":
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    elif output_format == "csv":
        if not records:
            return ""
        df = pd.DataFrame(records)
        return df.to_csv(index=False)
    else:
        raise UnsupportedFormatError(f"不支持的输出格式: {output_format}")


def write_output(records: List[Dict], output_path: str, output_format: str, dry_run: bool = False, verbose: bool = False) -> None:
    """写入输出文件"""
    content = format_output(records, output_format)
    
    if output_format == "json":
        filename = "processed_data.json"
    elif output_format == "jsonl":
        filename = "processed_data.jsonl"
    else:
        filename = "processed_data.csv"
    
    full_path = os.path.join(output_path, filename)
    
    if not dry_run:
        atomic_write(full_path, content)
        print(f"已写入: {full_path} ({len(records)} 条记录)")
    else:
        print(f"[DRY RUN] 将写入: {full_path}")
        print(f"[DRY RUN] 记录数: {len(records)}")
        if verbose:
            print(f"[DRY RUN] 内容预览:\n{content[:500]}...")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("autoresearch 自检开始")
    print("=" * 60)
    
    failures = 0
    
    # 测试 1: 文本清洗
    print("\n[测试 1] 文本清洗")
    try:
        test_text = "<p>这是**加粗**文本，包含[链接](http://example.com)和`代码`。</p>"
        cleaned = clean_text(test_text)
        assert "加粗" in cleaned, "清洗后应保留加粗文本"
        assert "链接" in cleaned, "清洗后应保留链接文本"
        assert "<" not in cleaned, "清洗后不应包含HTML标签"
        assert "**" not in cleaned, "清洗后不应包含Markdown加粗标记"
        print("  ✓ 文本清洗测试通过")
    except AssertionError as e:
        print(f"  ✗ 文本清洗测试失败: {str(e)}")
        failures += 1
    
    # 测试 2: 问答对解析
    print("\n[测试 2] 问答对解析")
    try:
        test_text = """问：什么是注意力机制？
答：注意力机制是一种让模型关注输入序列中重要部分的技术。

问：什么是Transformer？
答：Transformer是一种基于自注意力机制的神经网络架构。"""
        records = parse_qa_pairs(test_text, "test.md")
        assert len(records) == 1, f"应解析出 1 条记录，实际 {len(records)}"
        assert records[0]["instruction"] == "什么是注意力机制？", "第一条记录的 instruction 不正确"
        assert "注意力机制" in records[0]["output"], "第一条记录的 output 不正确"
        print(f"  ✓ 问答对解析测试通过 ({len(records)} 条记录)")
    except AssertionError as e:
        print(f"  ✗ 问答对解析测试失败: {str(e)}")
        failures += 1
    
    # 测试 3: Markdown 标题解析
    print("\n[测试 3] Markdown 标题解析")
    try:
        test_text = """## 什么是注意力机制？
注意力机制是一种让模型关注输入序列中重要部分的技术。

## 什么是Transformer？
Transformer是一种基于自注意力机制的神经网络架构。"""
        records = parse_qa_pairs(test_text, "test.md")
        assert len(records) == 2, f"应解析出 2 条记录，实际 {len(records)}"
        assert records[0]["instruction"] == "什么是注意力机制？", "第一条记录的 instruction 不正确"
        print(f"  ✓ Markdown 标题解析测试通过 ({len(records)} 条记录)")
    except AssertionError as e:
        print(f"  ✗ Markdown 标题解析测试失败: {str(e)}")
        failures += 1
    
    # 测试 4: 置信度计算
    print("\n[测试 4] 置信度计算")
    try:
        good_record = {
            "instruction": "什么是注意力机制？",
            "output": "注意力机制是一种让模型关注输入序列中重要部分的技术。",
            "confidence": 0.9,
        }
        confidence, needs_review = calculate_confidence(good_record)
        assert confidence >= 0.6, f"高质量记录置信度应 >= 0.6，实际 {confidence}"
        assert not needs_review, "高质量记录不应需要审核"
        
        bad_record = {
            "instruction": "",
            "output": "",
            "confidence": 0.5,
        }
        confidence, needs_review = calculate_confidence(bad_record)
        assert confidence < 0.6, f"低质量记录置信度应 < 0.6，实际 {confidence}"
        assert needs_review, "低质量记录应需要审核"
        print("  ✓ 置信度计算测试通过")
    except AssertionError as e:
        print(f"  ✗ 置信度计算测试失败: {str(e)}")
        failures += 1
    
    # 测试 5: 去重
    print("\n[测试 5] 去重")
    try:
        records = [
            {"instruction": "问题1", "output": "答案1", "confidence": 0.9},
            {"instruction": "问题1", "output": "答案1", "confidence": 0.9},
            {"instruction": "问题2", "output": "答案2", "confidence": 0.9},
        ]
        deduped = deduplicate(records)
        assert len(deduped) == 2, f"去重后应剩 2 条记录，实际 {len(deduped)}"
        print(f"  ✓ 去重测试通过 ({len(deduped)} 条记录)")
    except AssertionError as e:
        print(f"  ✗ 去重测试失败: {str(e)}")
        failures += 1
    
    # 测试 6: 空输入处理
    print("\n[测试 6] 空输入处理")
    try:
        records = parse_qa_pairs("", "empty.md")
        assert len(records) == 0, f"空输入应返回 0 条记录，实际 {len(records)}"
        print("  ✓ 空输入处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 空输入处理测试失败: {str(e)}")
        failures += 1
    
    # 测试 7: 中文标点处理
    print("\n[测试 7] 中文标点处理")
    try:
        test_text = "问：你好，世界！\n答：你好！这是测试。"
        records = parse_qa_pairs(test_text, "test.md")
        assert len(records) == 1, f"应解析出 1 条记录，实际 {len(records)}"
        assert "你好" in records[0]["instruction"], "instruction 应包含中文"
        print("  ✓ 中文标点处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 中文标点处理测试失败: {str(e)}")
        failures += 1
    
    # 测试 8: 编码处理
    print("\n[测试 8] 编码处理")
    try:
        # 创建临时 GBK 编码文件
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write("问：测试编码\n答：这是GBK编码测试。".encode("gbk"))
            tmp_path = f.name
        
        try:
            content = safe_read_file(tmp_path)
            assert "测试编码" in content, "应能正确读取 GBK 编码文件"
            print("  ✓ 编码处理测试通过")
        finally:
            os.unlink(tmp_path)
    except AssertionError as e:
        print(f"  ✗ 编码处理测试失败: {str(e)}")
        failures += 1
    
    # 测试 9: 完整流程
    print("\n[测试 9] 完整流程")
    try:
        # 创建临时测试数据
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)
            
            # 创建测试文件
            test_file = os.path.join(input_dir, "test.md")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("""## 什么是注意力机制？
注意力机制是一种让模型关注输入序列中重要部分的技术。

## 什么是Transformer？
Transformer是一种基于自注意力机制的神经网络架构。""")
            
            # 运行处理
            records = process_directory(input_dir, None, 0.6, True, False, False)
            assert len(records) == 2, f"应处理出 2 条记录，实际 {len(records)}"
            
            # 测试输出
            output_content = format_output(records, "json")
            assert "instruction" in output_content, "JSON 输出应包含 instruction 字段"
            
            # 测试写入
            write_output(records, output_dir, "json", dry_run=False, verbose=False)
            output_file = os.path.join(output_dir, "processed_data.json")
            assert os.path.exists(output_file), "输出文件应存在"
            
            print(f"  ✓ 完整流程测试通过 ({len(records)} 条记录)")
    except AssertionError as e:
        print(f"  ✗ 完整流程测试失败: {str(e)}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 完整流程测试异常: {str(e)}")
        failures += 1
    
    # 测试 10: Dry-run 模式
    print("\n[测试 10] Dry-run 模式")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)
            
            test_file = os.path.join(input_dir, "test.md")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("问：测试\n答：这是测试内容。")
            
            records = process_directory(input_dir, None, 0.6, True, False, False)
            write_output(records, output_dir, "json", dry_run=True, verbose=False)
            
            # 验证没有实际写入
            assert not os.path.exists(os.path.join(output_dir, "processed_data.json")), "Dry-run 不应写入文件"
            print("  ✓ Dry-run 模式测试通过")
    except AssertionError as e:
        print(f"  ✗ Dry-run 模式测试失败: {str(e)}")
        failures += 1
    except Exception as e:
        print(f"  ✗ Dry-run 模式测试异常: {str(e)}")
        failures += 1
    
    # 汇总
    print("\n" + "=" * 60)
    if failures == 0:
        print("所有测试通过！")
        return 0
    else:
        print(f"{failures} 个测试失败！")
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="autoresearch - 单卡训练数据自动整理工具",
        epilog="示例: python run.py --input ./raw_data --output ./processed"
    )
    
    parser.add_argument("--input", type=str, help="输入目录或文件路径")
    parser.add_argument("--output", type=str, default="./processed", help="输出目录")
    parser.add_argument("--format", type=str, default="json", choices=SUPPORTED_FORMATS, help="输出格式")
    parser.add_argument("--schema", type=json.loads, help="自定义字段映射 (JSON格式)")
    parser.add_argument("--dedupe", action="store_true", default=True, help="启用去重")
    parser.add_argument("--no-dedupe", dest="dedupe", action="store_false", help="禁用去重")
    parser.add_argument("--min-confidence", type=float, default=0.6, help="置信度阈值")
    parser.add_argument("--batch", action="store_true", help="批量模式（多文件并行处理）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，只打印不写盘")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理信息")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="store_true", help="显示版本号")
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    if args.version:
        print(f"autoresearch v{VERSION}")
        return 0
    
    if args.selftest:
        return run_selftest()
    
    # 参数校验
    if not args.input:
        print("错误: 必须指定 --input 参数", file=sys.stderr)
        parser.print_help()
        return 1
    
    if args.min_confidence < 0 or args.min_confidence > 1:
        print("错误: --min-confidence 必须在 0 到 1 之间", file=sys.stderr)
        return 1
    
    try:
        input_path = validate_path(args.input)
        output_path = validate_path(args.output)
        
        # 检查输入路径
        if not os.path.exists(input_path):
            raise ParameterError(f"输入路径不存在: {input_path}")
        
        # 处理输入
        if os.path.isfile(input_path):
            records = process_file(input_path, args.schema, args.min_confidence, args.dedupe, args.verbose)
        elif os.path.isdir(input_path):
            records = process_directory(input_path, args.schema, args.min_confidence, args.dedupe, args.batch, args.verbose)
        else:
            raise ParameterError(f"无效的输入路径: {input_path}")
        
        if not records:
            print("警告: 未解析到任何有效记录", file=sys.stderr)
            return 0
        
        # 写入输出
        write_output(records, output_path, args.format, args.dry_run, args.verbose)
        
        return 0
    except AutoResearchError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期的错误: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
