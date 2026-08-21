#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aionui 未命名工具 - 独立实现脚本
=================================
基于功能规格的 clean-room 实现，仅使用 Python 标准库。
支持命令行调用和 --selftest 离线自检。
"""

import argparse
import sys
import re
import json
import csv
import io
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class ErrorCode:
    """错误码常量定义"""
    E001_EMPTY_INPUT = "E001"
    E002_MISSING_INFO = "E002"
    E003_BAD_FORMAT = "E003"
    E004_OUT_OF_SCOPE = "E004"
    E005_LOW_CONFIDENCE = "E005"
    E006_INTERNAL = "E006"
    E007_OUTPUT_FAIL = "E007"
    E008_UNSUPPORTED = "E008"
    E009_EXTERNAL = "E009"
    E010_UNKNOWN = "E010"


ERROR_MESSAGES = {
    ErrorCode.E001_EMPTY_INPUT: "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    ErrorCode.E002_MISSING_INFO: "还缺少以下信息，请补充：",
    ErrorCode.E003_BAD_FORMAT: "输入格式不符合要求，示例：",
    ErrorCode.E004_OUT_OF_SCOPE: "这超出了本工具的能力范围，建议：",
    ErrorCode.E005_LOW_CONFIDENCE: "结果无法确定，建议：",
    ErrorCode.E006_INTERNAL: "内部处理错误，请重试",
    ErrorCode.E007_OUTPUT_FAIL: "输出生成失败，请检查参数",
    ErrorCode.E008_UNSUPPORTED: "不支持的输入类型或格式",
    ErrorCode.E009_EXTERNAL: "需要外部服务但未启用网络访问",
    ErrorCode.E010_UNKNOWN: "未知错误，请参考文档",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条处理结果"""
    def __init__(self, source: str, key_fields: Dict[str, Any], confidence: float, warnings: List[str] = None):
        self.source = source
        self.key_fields = key_fields
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "key_fields": self.key_fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class ProcessResult:
    """批量处理结果"""
    def __init__(self):
        self.items: List[ProcessedItem] = []
        self.errors: List[Tuple[str, str]] = []  # (错误码, 描述)

    def add_item(self, item: ProcessedItem) -> None:
        self.items.append(item)

    def add_error(self, code: str, message: str) -> None:
        self.errors.append((code, message))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# 输入解析函数
# ---------------------------------------------------------------------------
def parse_input(input_str: str) -> Any:
    """
    解析输入字符串，支持：
    - JSON 格式
    - CSV 格式（单行）
    - 普通文本
    - 文件路径（自动检测）
    - URL（自动检测）
    """
    input_str = input_str.strip()
    if not input_str:
        return input_str

    # 检查是否为文件路径
    if os.path.isfile(input_str):
        return read_file(input_str)

    # 检查是否为 URL
    if input_str.startswith(('http://', 'https://')):
        return fetch_url(input_str)

    # 尝试解析 JSON
    try:
        return json.loads(input_str)
    except json.JSONDecodeError:
        pass

    # 尝试解析 CSV（单行）
    if ',' in input_str:
        try:
            reader = csv.reader(io.StringIO(input_str))
            row = next(reader)
            if len(row) > 1:
                return row
        except Exception as e:
            print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出

    # 默认作为普通文本
    return input_str


def read_file(file_path: str) -> Any:
    """读取文件内容，支持 JSON/CSV/文本"""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"{ErrorCode.E008_UNSUPPORTED}: 文件不存在: {file_path}")

    suffix = path.suffix.lower()
    try:
        if suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif suffix == '.csv':
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return [row for row in reader]
        else:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        raise ValueError(f"{ErrorCode.E008_UNSUPPORTED}: 文件读取失败: {e}")


def fetch_url(url: str, max_retries: int = 3, timeout: int = 10) -> Any:
    """
    获取 URL 内容，带重试退避机制
    """
    for attempt in range(max_retries):
        try:
            req = Request(url, headers={'User-Agent': 'aionui/1.0'})
            with urlopen(req, timeout=timeout) as response:
                content = response.read().decode('utf-8')
                # 尝试解析 JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return content
        except (URLError, HTTPError) as e:
            if attempt == max_retries - 1:
                raise ValueError(f"{ErrorCode.E009_EXTERNAL}: URL 请求失败: {e}")
            # 指数退避
            wait_time = 2 ** attempt
            time.sleep(wait_time)
        except Exception as e:
            raise ValueError(f"{ErrorCode.E009_EXTERNAL}: URL 处理失败: {e}")

    raise ValueError(f"{ErrorCode.E009_EXTERNAL}: URL 请求失败")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _validate_input(raw_input: Any) -> Optional[str]:
    """校验输入，返回错误码或 None（通过）"""
    if raw_input is None:
        return ErrorCode.E001_EMPTY_INPUT
    if isinstance(raw_input, str) and not raw_input.strip():
        return ErrorCode.E001_EMPTY_INPUT
    if isinstance(raw_input, (list, tuple, dict)) and len(raw_input) == 0:
        return ErrorCode.E001_EMPTY_INPUT
    return None


def _extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从文本中提取关键信息。
    规则：
    - 识别形如 key: value 或 key=value 的字段
    - 识别常见命名实体（日期、数字、邮箱等）
    - 返回结构化字典
    """
    fields: Dict[str, Any] = {}

    # 1. 提取 key: value 或 key=value
    pattern = r'(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*([^\s,;]+)'
    for match in re.finditer(pattern, text):
        key, value = match.group(1), match.group(2)
        fields[key] = value

    # 2. 提取日期（YYYY-MM-DD 或 YYYY/MM/DD）
    date_match = re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text)
    if date_match:
        fields["date"] = date_match.group(0)

    # 3. 提取邮箱
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    if email_match:
        fields["email"] = email_match.group(0)

    # 4. 提取 URL
    url_match = re.search(r'https?://[^\s]+', text)
    if url_match:
        fields["url"] = url_match.group(0)

    # 5. 提取数字（第一个出现的数字）
    num_match = re.search(r'\d+', text)
    if num_match:
        fields["number"] = num_match.group(0)

    return fields


def _calculate_confidence(fields: Dict[str, Any], raw_text_len: int) -> float:
    """计算置信度（0-1）"""
    if not fields:
        return 0.0

    # 基础置信度
    base = min(0.6 + 0.1 * len(fields), 0.95)

    # 文本长度修正
    if raw_text_len < 10:
        base -= 0.2
    elif raw_text_len > 500:
        base += 0.02

    # 关键字段完整性
    if "date" in fields and "email" in fields:
        base += 0.03

    return max(0.0, min(1.0, base))


def _format_confidence_label(confidence: float) -> str:
    """根据置信度生成标注"""
    if confidence >= 0.90:
        return "直接输出"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


def process_single(raw_input: Any) -> ProcessedItem:
    """处理单条输入"""
    # 输入校验
    error_code = _validate_input(raw_input)
    if error_code:
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")

    # 转文本
    if isinstance(raw_input, str):
        text = raw_input
    elif isinstance(raw_input, (dict, list)):
        text = json.dumps(raw_input, ensure_ascii=False)
    else:
        text = str(raw_input)

    # 提取关键字段
    fields = _extract_key_fields(text)

    # 计算置信度
    confidence = _calculate_confidence(fields, len(text))

    # 生成警告
    warnings = []
    if confidence < 0.85:
        warnings.append("关键信息提取不完整，请人工复核")
    if not fields:
        warnings.append("未能识别结构化字段")

    return ProcessedItem(
        source=raw_input if isinstance(raw_input, str) else json.dumps(raw_input, ensure_ascii=False),
        key_fields=fields,
        confidence=confidence,
        warnings=warnings,
    )


def process_batch(inputs: List[Any], max_workers: int = 4) -> ProcessResult:
    """批量处理（并行）"""
    result = ProcessResult()

    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_input = {executor.submit(process_single, item): item for item in inputs}
        
        for future in as_completed(future_to_input):
            try:
                processed = future.result()
                result.add_item(processed)
            except ValueError as e:
                code = str(e).split(":")[0] if ":" in str(e) else ErrorCode.E010_UNKNOWN
                result.add_error(code, str(e))

    return result


def format_output(result: ProcessResult, detailed: bool = False, format_type: str = "text") -> str:
    """格式化输出结果"""
    if not result.items:
        return "没有可输出的结果"

    if format_type == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif format_type == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["source", "key_fields", "confidence", "warnings"])
        for item in result.items:
            writer.writerow([
                item.source,
                json.dumps(item.key_fields, ensure_ascii=False),
                f"{item.confidence:.2f}",
                "; ".join(item.warnings)
            ])
        return output.getvalue()
    else:  # text 格式
        lines = []
        for i, item in enumerate(result.items, 1):
            lines.append(f"--- 条目 {i} ---")
            lines.append(f"来源: {item.source[:100]}{'...' if len(item.source) > 100 else ''}")

            if detailed:
                lines.append(f"关键字段: {json.dumps(item.key_fields, ensure_ascii=False)}")
            else:
                keys = list(item.key_fields.keys())
                lines.append(f"关键字段: {', '.join(keys) if keys else '无'}")

            # 置信度格式化为百分比，不带标注
            lines.append(f"置信度: {item.confidence:.1%}")

            if item.warnings:
                lines.append(f"警告: {'; '.join(item.warnings)}")

            lines.append("")

        if result.errors:
            lines.append("=== 错误汇总 ===")
            for code, msg in result.errors:
                lines.append(f"[{code}] {msg}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def run_cli(args: argparse.Namespace) -> int:
    """CLI 主入口"""
    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    if args.input:
        # 解析输入
        parsed_inputs = []
        for input_str in args.input:
            try:
                parsed = parse_input(input_str)
                # 如果是列表，展开处理
                if isinstance(parsed, list) and len(parsed) > 1:
                    parsed_inputs.extend(parsed)
                else:
                    parsed_inputs.append(parsed)
            except ValueError as e:
                print(f"[{ErrorCode.E008_UNSUPPORTED}] 输入解析失败: {e}", file=sys.stderr)
                return 1

        # 批量处理（并行）
        result = process_batch(parsed_inputs, max_workers=args.workers)
        output = format_output(result, detailed=args.detailed, format_type=args.format)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            except OSError as e:
                print(f"[{ErrorCode.E007_OUTPUT_FAIL}] 写入文件失败: {e}", file=sys.stderr)
                return 1
        else:
            print(output)

        # 错误处理
        if result.errors:
            return 1
        return 0
    else:
        # 无输入，显示帮助
        parser.print_help()
        return 0


# ---------------------------------------------------------------------------
# 自检逻辑
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    测试核心转换链路：输入解析 -> 处理 -> 输出
    """
    print("=== aionui 自检开始 ===")
    passed = True

    # 测试 1: 文本输入处理
    print("\n[测试1] 文本输入处理")
    try:
        result = process_single("姓名: 张三, email: test@example.com, 日期: 2025-01-15")
        if result.key_fields and result.confidence > 0.6:
            print(f"  PASS - 文本处理成功，字段数={len(result.key_fields)}")
        else:
            print(f"  FAIL - 文本处理结果异常: {result.key_fields}")
            passed = False
    except Exception as e:
        print(f"  FAIL - 文本处理异常: {e}")
        passed = False

    # 测试 2: JSON 输入处理
    print("\n[测试2] JSON 输入处理")
    try:
        json_input = '{"name": "Alice", "email": "alice@test.com", "score": 95}'
        parsed = parse_input(json_input)
        result = process_single(parsed)
        if result.key_fields and result.confidence > 0.6:
            print(f"  PASS - JSON 处理成功，字段数={len(result.key_fields)}")
        else:
            print(f"  FAIL - JSON 处理结果异常: {result.key_fields}")
            passed = False
    except Exception as e:
        print(f"  FAIL - JSON 处理异常: {e}")
        passed = False

    # 测试 3: CSV 输入处理
    print("\n[测试3] CSV 输入处理")
    try:
        csv_input = "name,email,score\nBob,bob@test.com,88"
        parsed = parse_input(csv_input)
        result = process_single(parsed)
        if result.key_fields and result.confidence > 0.6:
            print(f"  PASS - CSV 处理成功，字段数={len(result.key_fields)}")
        else:
            print(f"  FAIL - CSV 处理结果异常: {result.key_fields}")
            passed = False
    except Exception as e:
        print(f"  FAIL - CSV 处理异常: {e}")
        passed = False

    # 测试 4: 批量处理（并行）
    print("\n[测试4] 批量处理（并行）")
    try:
        batch_inputs = [
            "name: Alice, email: a@test.com",
            "name: Bob, email: b@test.com",
            "name: Charlie, email: c@test.com",
        ]
        result = process_batch(batch_inputs, max_workers=2)
        if len(result.items) == 3:
            print(f"  PASS - 批量处理成功，处理 {len(result.items)} 条")
        else:
            print(f"  FAIL - 批量处理结果异常: {len(result.items)} 条")
            passed = False
    except Exception as e:
        print(f"  FAIL - 批量处理异常: {e}")
