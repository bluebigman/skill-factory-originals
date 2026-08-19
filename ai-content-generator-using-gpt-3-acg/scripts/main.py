#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACG 结构化文本处理器 - 本地规则驱动的文本批处理与结构化提取引擎

将零散、非结构化的文本批量转换为结构化数据（JSON / Markdown / CSV），
支持自定义正则规则提取关键字段、置信度评分与低置信度标记。

纯 Python 标准库实现，无第三方依赖，不调用外部 AI API。
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 常量定义
# ============================================================

ERROR_CODES = {
    "E001": "输入文件不存在或无权限访问",
    "E002": "文件编码无法识别，请转换为 UTF-8 或使用 --encoding 指定",
    "E003": "规则文件格式错误或无法解析",
    "E004": "不支持的输出格式，可选 json/markdown/csv",
    "E005": "规则中未定义任何字段",
    "E006": "内存不足，请减小 --chunk-size",
    "E007": "输出目录不存在，请先创建或使用 --force 自动创建",
    "E008": "未知错误，请查看详细日志",
}

SUPPORTED_FORMATS = ["json", "markdown", "csv"]
SUPPORTED_ENCODINGS = ["utf-8", "gbk", "gb18030"]

# 默认提取规则（内置）
DEFAULT_RULES = {
    "fields": [
        {"name": "date", "pattern": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?", "description": "日期"},
        {"name": "phone", "pattern": r"1[3-9]\d{9}", "description": "手机号"},
        {"name": "amount", "pattern": r"(\d+(?:\.\d+)?)\s*(?:元|万元|人民币|RMB|CNY)", "description": "金额"},
        {"name": "email", "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "description": "邮箱"},
    ]
}

# 置信度阈值
CONFIDENCE_THRESHOLD = 0.5
CONFIDENCE_PENALTY = 0.7

# 版本信息
VERSION = "3.1.0"

# ============================================================
# 异常定义
# ============================================================

class ACGError(Exception):
    """ACG 基础异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class InputValidationError(ACGError):
    """输入校验异常"""
    pass


class FileProcessingError(ACGError):
    """文件处理异常"""
    pass


class RuleParsingError(ACGError):
    """规则解析异常"""
    pass


class OutputFormatError(ACGError):
    """输出格式异常"""
    pass


# ============================================================
# 工具函数
# ============================================================

def now_utc() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def safe_write(path: str, content: str, dry_run: bool = False) -> None:
    """
    原子化写入文件。先写临时文件，再替换目标文件。
    支持 dry-run 模式，只打印不写盘。
    """
    if dry_run:
        print(f"[DRY-RUN] 将写入文件: {path}")
        print(f"[DRY-RUN] 内容摘要: {content[:100]}...")
        return

    # 确保目录存在
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    # 原子写入
    fd, temp_path = tempfile.mkstemp(dir=Path(path).parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, path)
    except Exception as e:
        os.unlink(temp_path)
        raise FileProcessingError("E008", f"写入文件失败: {e}")


def read_file_with_encoding(filepath: str, encoding: Optional[str] = None) -> str:
    """
    读取文件内容，支持多编码。
    优先使用指定编码，否则尝试 utf-8 -> gbk -> gb18030。
    """
    if not os.path.exists(filepath):
        raise FileProcessingError("E001", f"文件不存在: {filepath}")

    encodings = [encoding] if encoding else ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise FileProcessingError("E002", f"读取文件失败: {e}")

    raise FileProcessingError("E002", f"无法识别文件编码: {filepath}")


def load_rules(rules_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载提取规则。
    如果未指定规则文件，使用默认规则。
    """
    if rules_path is None:
        return DEFAULT_RULES

    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
    except json.JSONDecodeError as e:
        raise RuleParsingError("E003", f"规则文件 JSON 解析失败: {e}")
    except Exception as e:
        raise RuleParsingError("E003", f"读取规则文件失败: {e}")

    if "fields" not in rules or not isinstance(rules["fields"], list):
        raise RuleParsingError("E003", "规则文件必须包含 fields 列表")

    if len(rules["fields"]) == 0:
        raise RuleParsingError("E005", "规则中未定义任何字段")

    return rules


# ============================================================
# 核心提取逻辑
# ============================================================

def extract_fields(text: str, rules: Dict[str, Any]) -> Dict[str, str]:
    """
    从文本中提取字段。
    返回提取到的字段字典。
    """
    fields = {}
    for field_def in rules["fields"]:
        name = field_def["name"]
        pattern = field_def["pattern"]
        match = re.search(pattern, text)
        if match:
            fields[name] = match.group(0)
    return fields


def calculate_confidence(fields: Dict[str, str], rules: Dict[str, Any]) -> float:
    """
    计算置信度。
    置信度 = 提取到的字段数 / 总字段数
    """
    total_fields = len(rules["fields"])
    if total_fields == 0:
        return 0.0
    return len(fields) / total_fields


def process_text(text: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理单条文本，返回结构化结果。
    """
    fields = extract_fields(text, rules)
    confidence = calculate_confidence(fields, rules)
    return {
        "raw_text": text,
        "fields": fields,
        "confidence": confidence,
    }


def process_file(
    input_path: str,
    output_path: str,
    output_format: str,
    rules: Dict[str, Any],
    min_confidence: float,
    dry_run: bool,
    verbose: bool,
    chunk_size: int,
) -> int:
    """
    处理整个文件。
    返回处理记录数。
    """
    # 读取文件
    content = read_file_with_encoding(input_path)

    # 分块处理
    lines = content.splitlines()
    records = []
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i:i + chunk_size]
        for line in chunk:
            if not line.strip():
                continue
            record = process_text(line, rules)
            if record["confidence"] >= min_confidence:
                records.append(record)
                if verbose:
                    print(f"[VERBOSE] 记录 {len(records)}: 提取到字段 {', '.join(record['fields'].keys())}")

    # 输出
    if output_format == "json":
        output_content = json.dumps(records, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        output_content = to_markdown(records)
    elif output_format == "csv":
        output_content = to_csv(records)
    else:
        raise OutputFormatError("E004", f"不支持的输出格式: {output_format}")

    # 写入文件
    safe_write(output_path, output_content, dry_run)

    if verbose:
        print(f"[VERBOSE] 共处理 {len(records)} 条记录")

    return len(records)


def to_markdown(records: List[Dict[str, Any]]) -> str:
    """
    将记录转换为 Markdown 表格。
    """
    if not records:
        return "| 字段 | 值 |\n|------|-----|\n"

    # 收集所有字段名
    all_fields = set()
    for record in records:
        all_fields.update(record["fields"].keys())

    # 构建表头
    header = ["raw_text"] + sorted(all_fields) + ["confidence"]
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    # 构建数据行
    for record in records:
        row = [record["raw_text"]]
        for field in sorted(all_fields):
            row.append(record["fields"].get(field, ""))
        row.append(str(record["confidence"]))
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def to_csv(records: List[Dict[str, Any]]) -> str:
    """
    将记录转换为 CSV 格式。
    """
    if not records:
        return ""

    # 收集所有字段名
    all_fields = set()
    for record in records:
        all_fields.update(record["fields"].keys())

    # 构建表头
    header = ["raw_text"] + sorted(all_fields) + ["confidence"]

    # 构建数据行
    rows = []
    for record in records:
        row = [record["raw_text"]]
        for field in sorted(all_fields):
            row.append(record["fields"].get(field, ""))
        row.append(str(record["confidence"]))
        rows.append(row)

    # 写入 CSV
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue()


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> int:
    """
    运行自检。
    验证核心功能是否正常。
    """
    print("[SELFTEST] 开始自检...")

    # 测试 1: 默认规则提取
    test_text = "2023-10-01 10:30:00 [INFO] 用户 13812345678 下单成功，金额 299.00 元。"
    rules = DEFAULT_RULES
    record = process_text(test_text, rules)
    assert "date" in record["fields"], "日期提取失败"
    assert "phone" in record["fields"], "手机号提取失败"
    assert "amount" in record["fields"], "金额提取失败"
    assert record["confidence"] > 0, "置信度计算失败"
    print("[SELFTEST] 默认规则提取测试通过")

    # 测试 2: 空输入处理
    empty_record = process_text("", rules)
    assert empty_record["fields"] == {}, "空输入应返回空字段"
    assert empty_record["confidence"] == 0, "空输入置信度应为 0"
    print("[SELFTEST] 空输入处理测试通过")

    # 测试 3: 编码处理
    test_file = tempfile.NamedTemporaryFile(mode="w", encoding="gbk", suffix=".txt", delete=False)
    test_file.write("测试文本 13812345678")
    test_file.close()
    content = read_file_with_encoding(test_file.name)
    assert "测试文本" in content, "GBK 编码读取失败"
    os.unlink(test_file.name)
    print("[SELFTEST] 编码处理测试通过")

    # 测试 4: 输出格式
    test_records = [{"raw_text": "test", "fields": {"phone": "13812345678"}, "confidence": 0.8}]
    md_output = to_markdown(test_records)
    assert "| raw_text |" in md_output, "Markdown 输出格式错误"
    csv_output = to_csv(test_records)
    assert "raw_text" in csv_output, "CSV 输出格式错误"
    print("[SELFTEST] 输出格式测试通过")

    # 测试 5: 文件处理
    test_input = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False)
    test_input.write("2023-10-01 10:30:00 [INFO] 用户 13812345678 下单成功，金额 299.00 元。\n")
    test_input.write("2023-10-01 10:31:00 [ERROR] 用户 13912345678 支付失败，请联系 support@example.com。\n")
    test_input.close()

    test_output = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    test_output.close()
    os.unlink(test_output.name)

    count = process_file(
        input_path=test_input.name,
        output_path=test_output.name,
        output_format="json",
        rules=rules,
        min_confidence=0.5,
        dry_run=False,
        verbose=False,
        chunk_size=100,
    )
    assert count == 2, f"文件处理失败，预期 2 条记录，实际 {count} 条"
    assert os.path.exists(test_output.name), "输出文件未生成"
    os.unlink(test_input.name)
    os.unlink(test_output.name)
    print("[SELFTEST] 文件处理测试通过")

    print("[OK] 环境正常，依赖库齐全")
    return 0


# ============================================================
# 主函数
# ============================================================

def main() -> int:
    """
    主入口函数。
    """
    global dry_run

    parser = argparse.ArgumentParser(
        description="ACG 结构化文本处理器 - 本地规则驱动的文本批处理与结构化提取引擎",
        epilog="示例: python main.py --input sample.txt --format json"
    )

    parser.add_argument("--input", "-i", type=str, help="输入文件路径")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（默认自动生成）")
    parser.add_argument("--format", "-f", type=str, choices=SUPPORTED_FORMATS, default="json", help="输出格式")
    parser.add_argument("--rules", "-r", type=str, help="自定义规则文件路径")
    parser.add_argument("--min-confidence", type=float, default=CONFIDENCE_THRESHOLD, help="最小置信度阈值")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志模式")
    parser.add_argument("--encoding", "-e", type=str, choices=SUPPORTED_ENCODINGS, help="输入文件编码")
    parser.add_argument("--chunk-size", type=int, default=100, help="分块处理大小")
    parser.add_argument("--force", action="store_true", help="自动创建输出目录")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"ACG 结构化文本处理器 v{VERSION}")

    args = parser.parse_args()

    # 设置全局 dry_run
    dry_run = args.dry_run

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 输入校验
    if not args.input:
        print("[ERROR] 必须指定 --input 参数", file=sys.stderr)
        return 1

    if not os.path.exists(args.input):
        print(f"[ERROR] {ERROR_CODES['E001']}: {args.input}", file=sys.stderr)
        return 1

    # 加载规则
    try:
        rules = load_rules(args.rules)
    except ACGError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    # 生成输出路径
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.with_suffix(f"_output.{args.format}"))

    # 检查输出目录
    output_dir = Path(output_path).parent
    if not output_dir.exists() and not args.force:
        print(f"[ERROR] {ERROR_CODES['E007']}: {output_dir}", file=sys.stderr)
        return 1

    # 处理文件
    try:
        count = process_file(
            input_path=args.input,
            output_path=output_path,
            output_format=args.format,
            rules=rules,
            min_confidence=args.min_confidence,
            dry_run=args.dry_run,
            verbose=args.verbose,
            chunk_size=args.chunk_size,
        )
    except ACGError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] {ERROR_CODES['E008']}: {e}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"[VERBOSE] 处理完成，共 {count} 条记录")
        print(f"[VERBOSE] 输出文件: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
