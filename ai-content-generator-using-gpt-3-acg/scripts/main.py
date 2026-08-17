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

def utc_now() -> str:
    """返回 UTC 当前时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def safe_read_file(file_path: str, encoding: Optional[str] = None) -> str:
    """
    安全读取文件内容，支持多编码 fallback。
    优先使用指定编码，否则尝试 utf-8 → gbk → gb18030。
    """
    encodings = [encoding] if encoding else ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise FileProcessingError("E001", ERROR_CODES["E001"])
        except PermissionError:
            raise FileProcessingError("E001", ERROR_CODES["E001"])
    raise FileProcessingError("E002", ERROR_CODES["E002"])


def safe_write_file(file_path: str, content: str, encoding: str = "utf-8") -> None:
    """原子化写入文件，避免写入中断导致文件损坏"""
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path) or ".")
    try:
        with os.fdopen(temp_fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception as e:
        os.unlink(temp_path)
        raise FileProcessingError("E008", f"写入文件失败: {e}")


def validate_input_file(file_path: str) -> None:
    """校验输入文件是否存在且可读"""
    if not os.path.isfile(file_path):
        raise InputValidationError("E001", ERROR_CODES["E001"])
    if not os.access(file_path, os.R_OK):
        raise InputValidationError("E001", ERROR_CODES["E001"])


def validate_output_dir(output_path: str, force: bool = False) -> None:
    """校验输出目录是否存在，必要时创建"""
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        if force:
            os.makedirs(out_dir, exist_ok=True)
        else:
            raise InputValidationError("E007", ERROR_CODES["E007"])


def load_rules(rules_path: Optional[str]) -> Dict[str, Any]:
    """加载自定义规则，若未指定则使用默认规则"""
    if rules_path is None:
        return DEFAULT_RULES
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        if "fields" not in rules or not isinstance(rules["fields"], list) or len(rules["fields"]) == 0:
            raise RuleParsingError("E005", ERROR_CODES["E005"])
        return rules
    except json.JSONDecodeError:
        raise RuleParsingError("E003", ERROR_CODES["E003"])
    except FileNotFoundError:
        raise RuleParsingError("E003", ERROR_CODES["E003"])


def compile_patterns(rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    """预编译正则表达式，提高匹配效率"""
    compiled = []
    for field in rules["fields"]:
        try:
            compiled.append({
                "name": field["name"],
                "pattern": re.compile(field["pattern"]),
                "description": field.get("description", ""),
            })
        except re.error as e:
            raise RuleParsingError("E003", f"规则 {field['name']} 正则错误: {e}")
    return compiled


# ============================================================
# 核心提取逻辑
# ============================================================

def extract_fields(text: str, compiled_rules: List[Dict[str, Any]]) -> Dict[str, str]:
    """从文本中提取所有规则匹配的字段"""
    fields = {}
    for rule in compiled_rules:
        match = rule["pattern"].search(text)
        if match:
            fields[rule["name"]] = match.group(0)
    return fields


def calculate_confidence(text: str, fields: Dict[str, str], compiled_rules: List[Dict[str, Any]]) -> float:
    """
    计算置信度：
    - 基础分 = 匹配字段数 / 总字段数
    - 若文本长度 < 10，惩罚 0.7
    """
    if not compiled_rules:
        return 0.0
    base_score = len(fields) / len(compiled_rules)
    if len(text.strip()) < 10:
        base_score *= CONFIDENCE_PENALTY
    return round(min(base_score, 1.0), 2)


def process_text(text: str, compiled_rules: List[Dict[str, Any]], min_confidence: float = 0.0) -> Dict[str, Any]:
    """处理单条文本，返回结构化结果"""
    fields = extract_fields(text, compiled_rules)
    confidence = calculate_confidence(text, fields, compiled_rules)
    result = {
        "raw_text": text.strip(),
        "fields": fields,
        "confidence": confidence,
    }
    if confidence < min_confidence:
        result["low_confidence"] = True
    return result


def process_file_stream(file_path: str, compiled_rules: List[Dict[str, Any]], chunk_size: int = 1000) -> List[Dict[str, Any]]:
    """
    流式处理文件，按行读取并分块处理。
    返回所有记录列表。
    """
    results = []
    buffer = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                buffer.append(line)
                if len(buffer) >= chunk_size:
                    chunk_text = "".join(buffer)
                    results.append(process_text(chunk_text, compiled_rules))
                    buffer = []
            if buffer:
                chunk_text = "".join(buffer)
                results.append(process_text(chunk_text, compiled_rules))
    except UnicodeDecodeError:
        # 尝试 GBK 编码
        try:
            with open(file_path, "r", encoding="gbk") as f:
                for line in f:
                    buffer.append(line)
                    if len(buffer) >= chunk_size:
                        chunk_text = "".join(buffer)
                        results.append(process_text(chunk_text, compiled_rules))
                        buffer = []
                if buffer:
                    chunk_text = "".join(buffer)
                    results.append(process_text(chunk_text, compiled_rules))
        except Exception as e:
            raise FileProcessingError("E002", ERROR_CODES["E002"])
    except Exception as e:
        raise FileProcessingError("E008", f"读取文件失败: {e}")
    return results


# ============================================================
# 输出格式化
# ============================================================

def format_json(results: List[Dict[str, Any]]) -> str:
    """格式化 JSON 输出"""
    return json.dumps(results, ensure_ascii=False, indent=2)


def format_markdown(results: List[Dict[str, Any]]) -> str:
    """格式化 Markdown 表格输出"""
    if not results:
        return "| 字段 | 值 |\n|------|-----|\n"
    # 收集所有字段名
    all_fields = set()
    for r in results:
        all_fields.update(r["fields"].keys())
    all_fields = sorted(all_fields)
    
    lines = ["| 原始文本 | " + " | ".join(all_fields) + " | 置信度 |"]
    lines.append("|----------|" + "|".join(["------"] * len(all_fields)) + "|--------|")
    for r in results:
        row = [r["raw_text"].replace("|", "\\|")[:50]]
        for field in all_fields:
            row.append(r["fields"].get(field, ""))
        row.append(str(r["confidence"]))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def format_csv(results: List[Dict[str, Any]]) -> str:
    """格式化 CSV 输出"""
    if not results:
        return ""
    all_fields = set()
    for r in results:
        all_fields.update(r["fields"].keys())
    all_fields = sorted(all_fields)
    
    output = []
    header = ["raw_text"] + all_fields + ["confidence"]
    output.append(",".join(header))
    for r in results:
        row = [r["raw_text"].replace(",", " ")]
        for field in all_fields:
            row.append(r["fields"].get(field, ""))
        row.append(str(r["confidence"]))
        output.append(",".join(row))
    return "\n".join(output)


def write_output(file_path: str, content: str, dry_run: bool = False) -> None:
    """写入输出文件，支持 dry-run 模式"""
    if dry_run:
        print(f"[DRY-RUN] 将写入文件: {file_path}")
        print(f"[DRY-RUN] 内容摘要: {content[:100]}...")
        return
    safe_write_file(file_path, content)


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("[SELFTEST] 开始自检...")
    
    # 测试 1: 默认规则提取
    test_text = "2023-10-01 用户 13812345678 消费 299.00 元，联系 support@example.com"
    compiled_rules = compile_patterns(DEFAULT_RULES)
    result = process_text(test_text, compiled_rules)
    assert "date" in result["fields"], "日期提取失败"
    assert "phone" in result["fields"], "手机号提取失败"
    assert "amount" in result["fields"], "金额提取失败"
    assert "email" in result["fields"], "邮箱提取失败"
    assert result["confidence"] > 0.5, "置信度计算异常"
    print("[SELFTEST] 字段提取测试通过")
    
    # 测试 2: 空输入处理
    empty_result = process_text("", compiled_rules)
    assert empty_result["fields"] == {}, "空输入应返回空字段"
    assert empty_result["confidence"] == 0.0, "空输入置信度应为 0"
    print("[SELFTEST] 空输入测试通过")
    
    # 测试 3: 编码处理
    test_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    test_file.write("测试文本 13812345678")
    test_file.close()
    try:
        content = safe_read_file(test_file.name)
        assert "测试" in content, "UTF-8 读取失败"
    finally:
        os.unlink(test_file.name)
    print("[SELFTEST] 编码处理测试通过")
    
    # 测试 4: 输出格式
    test_results = [{"raw_text": "test", "fields": {"phone": "13812345678"}, "confidence": 0.8}]
    json_out = format_json(test_results)
    assert "13812345678" in json_out, "JSON 输出异常"
    md_out = format_markdown(test_results)
    assert "13812345678" in md_out, "Markdown 输出异常"
    csv_out = format_csv(test_results)
    assert "13812345678" in csv_out, "CSV 输出异常"
    print("[SELFTEST] 输出格式测试通过")
    
    # 测试 5: 文件流式处理
    test_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    for i in range(10):
        test_file.write(f"2023-10-01 用户 1381234567{i} 消费 {i}.00 元\n")
    test_file.close()
    try:
        results = process_file_stream(test_file.name, compiled_rules, chunk_size=3)
        assert len(results) >= 4, f"流式处理结果数量异常: {len(results)}"
    finally:
        os.unlink(test_file.name)
    print("[SELFTEST] 流式处理测试通过")
    
    print("[OK] 环境正常，依赖库齐全")
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """CLI 主入口"""
    global dry_run
    
    parser = argparse.ArgumentParser(
        description="ACG 结构化文本处理器 - 本地规则驱动的文本批处理与结构化提取引擎",
        epilog=f"版本 {VERSION} | MIT License"
    )
    parser.add_argument("--input", "-i", type=str, help="输入文件路径")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（默认自动生成）")
    parser.add_argument("--format", "-f", type=str, choices=SUPPORTED_FORMATS, default="json", help="输出格式")
    parser.add_argument("--rules", "-r", type=str, help="自定义规则文件路径")
    parser.add_argument("--min-confidence", type=float, default=0.0, help="最低置信度阈值")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    parser.add_argument("--encoding", type=str, choices=SUPPORTED_ENCODINGS, help="输入文件编码")
    parser.add_argument("--chunk-size", type=int, default=1000, help="分块大小（行数）")
    parser.add_argument("--force", action="store_true", help="自动创建输出目录")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 参数校验
    if not args.input:
        print("[E001] 必须指定 --input 参数", file=sys.stderr)
        return 1
    
    # 设置全局 dry-run
    dry_run = args.dry_run
    
    try:
        # 校验输入文件
        validate_input_file(args.input)
        
        # 加载规则
        rules = load_rules(args.rules)
        compiled_rules = compile_patterns(rules)
        
        # 处理文件
        results = process_file_stream(args.input, compiled_rules, args.chunk_size)
        
        # 过滤低置信度
        if args.min_confidence > 0:
            results = [r for r in results if r["confidence"] >= args.min_confidence]
        
        # 生成输出
        if args.format == "json":
            content = format_json(results)
        elif args.format == "markdown":
            content = format_markdown(results)
        elif args.format == "csv":
            content = format_csv(results)
        else:
            raise OutputFormatError("E004", ERROR_CODES["E004"])
        
        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            base = os.path.splitext(args.input)[0]
            output_path = f"{base}_output.{args.format}"
        
        # 校验输出目录
        validate_output_dir(output_path, args.force)
        
        # 写入输出
        write_output(output_path, content, args.dry_run)
        
        if args.verbose:
            print(f"[VERBOSE] 处理完成: {len(results)} 条记录")
            for i, r in enumerate(results[:5], 1):
                print(f"[VERBOSE] 记录 {i}: 提取到字段 {', '.join(r['fields'].keys())}")
        
        if not args.dry_run:
            print(f"[OK] 输出已写入: {output_path}")
        
        return 0
        
    except ACGError as e:
        print(f"[{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E008] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
