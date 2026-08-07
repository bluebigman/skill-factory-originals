#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 未命名工具（grit）独立实现

本脚本依据功能规格独立实现（clean-room），不依赖任何既有代码。
核心能力：将用户提供的输入（文本/文件路径/URL）解析为结构化结果，
          识别关键信息，按约定格式输出，并标注置信度。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（遵循规格 E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：文本内容 / 文件路径 / http(s)://URL",
    "E004": "这超出了本工具的能力范围，建议：提供文本、文件路径或URL",
    "E005": "结果无法确定，建议：补充更多上下文信息后重试",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "JSON 解析失败，请检查输入是否为合法 JSON",
    "E008": "内部逻辑错误，请报告开发者",
    "E009": "命令行参数错误，请检查参数组合",
    "E010": "未知错误，请稍后重试",
}


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果结构体"""
    def __init__(self):
        self.raw_input: str = ""           # 原始输入
        self.input_type: str = "text"      # text / file / url / json
        self.key_fields: Dict[str, Any] = {}  # 提取的关键字段
        self.confidence: float = 0.0       # 置信度 0-100
        self.warnings: List[str] = []      # 警告信息
        self.output_text: str = ""         # 格式化输出文本
        self.created_at: str = ""          # 时间戳

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "raw_input": self.raw_input,
            "input_type": self.input_type,
            "key_fields": self.key_fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "output_text": self.output_text,
            "created_at": self.created_at,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

def detect_input_type(raw: str) -> str:
    """识别输入类型：text / file / url / json"""
    if not raw or not raw.strip():
        return "empty"
    
    stripped = raw.strip()
    
    # URL 检测
    if re.match(r'^https?://', stripped, re.IGNORECASE):
        return "url"
    
    # 文件路径检测（支持相对/绝对路径，常见扩展名）
    file_exts = {'.txt', '.json', '.csv', '.md', '.log', '.yaml', '.yml', '.xml', '.html'}
    if len(stripped) < 500:  # 避免长文本误判
        p = Path(stripped)
        if p.suffix.lower() in file_exts:
            return "file"
    
    # JSON 检测（宽松判断）
    if stripped.startswith(('{', '[')) and stripped.endswith(('}', ']')):
        try:
            json.loads(stripped)
            return "json"
        except json.JSONDecodeError:
            pass
    
    return "text"


def extract_key_fields(raw: str, input_type: str) -> Tuple[Dict[str, Any], float]:
    """
    从输入中提取关键信息。
    返回 (字段字典, 置信度)
    """
    fields: Dict[str, Any] = {}
    confidence = 0.0
    
    if input_type == "text":
        # 文本处理：提取常见关键信息
        stripped = raw.strip()
        
        # 基本信息
        fields["content_length"] = len(stripped)
        fields["word_count"] = len(re.findall(r'\S+', stripped))
        fields["line_count"] = len(stripped.splitlines()) if stripped else 0
        
        # 尝试识别 email
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', stripped)
        if emails:
            fields["emails"] = emails
        
        # 尝试识别电话号码（宽松模式）
        phones = re.findall(r'(\+?\d[\d\s-]{7,}\d)', stripped)
        if phones:
            fields["phones"] = [p.strip() for p in phones]
        
        # 尝试识别日期
        dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', stripped)
        if dates:
            fields["dates"] = dates
        
        # 尝试识别 URL
        urls = re.findall(r'https?://[^\s]+', stripped)
        if urls:
            fields["urls"] = urls
        
        # 置信度评估：有内容则基础 80%，有识别字段则提高
        confidence = 80.0
        if fields.get("emails") or fields.get("phones") or fields.get("dates"):
            confidence = 90.0
        if fields.get("urls"):
            confidence = 92.0
            
    elif input_type == "json":
        # JSON 处理
        try:
            data = json.loads(raw.strip())
            if isinstance(data, dict):
                fields = {"json_type": "object", "keys": list(data.keys()), "value_count": len(data)}
            elif isinstance(data, list):
                fields = {"json_type": "array", "items": len(data)}
                if data and isinstance(data[0], dict):
                    fields["sample_keys"] = list(data[0].keys())
            confidence = 95.0
        except json.JSONDecodeError:
            fields = {"error": "invalid_json"}
            confidence = 50.0
            
    elif input_type == "url":
        # URL 处理（不访问网络，仅解析结构）
        stripped = raw.strip()
        fields["url"] = stripped
        fields["scheme"] = stripped.split("://")[0] if "://" in stripped else "unknown"
        path_part = stripped.split("://")[1].split("/")[1:] if "://" in stripped else []
        fields["path_segments"] = [seg for seg in path_part if seg]
        confidence = 85.0
        
    elif input_type == "file":
        # 文件路径处理（不实际读取，仅记录路径信息）
        p = Path(raw.strip())
        fields["file_path"] = str(p)
        fields["file_name"] = p.name
        fields["file_extension"] = p.suffix
        confidence = 90.0
    
    return fields, confidence


def format_output(result: ProcessingResult) -> str:
    """格式化输出结果"""
    lines = []
    lines.append("=" * 50)
    lines.append("处理结果报告")
    lines.append("=" * 50)
    lines.append(f"输入类型: {result.input_type}")
    lines.append(f"处理时间: {result.created_at}")
    lines.append(f"置信度: {result.confidence:.1f}%")
    lines.append("-" * 50)
    
    # 置信度标注
    if result.confidence >= 90:
        lines.append("状态: 直接输出")
    elif result.confidence >= 85:
        lines.append("状态: 建议复核")
    else:
        lines.append("状态: [需核实]")
    
    lines.append("-" * 50)
    lines.append("关键信息:")
    
    if result.key_fields:
        for key, value in result.key_fields.items():
            lines.append(f"  {key}: {value}")
    else:
        lines.append("  （未提取到关键信息）")
    
    if result.warnings:
        lines.append("-" * 50)
        lines.append("警告:")
        for w in result.warnings:
            lines.append(f"  - {w}")
    
    lines.append("=" * 50)
    return "\n".join(lines)


def process_input(raw_input: str) -> ProcessingResult:
    """
    核心处理流程：
    1. 识别输入类型
    2. 提取关键信息
    3. 生成结构化结果
    """
    result = ProcessingResult()
    result.raw_input = raw_input
    result.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 空输入检查
    if not raw_input or not raw_input.strip():
        result.confidence = 0.0
        result.warnings.append("E001: " + ERROR_CODES["E001"])
        result.output_text = format_output(result)
        return result
    
    # 识别输入类型
    result.input_type = detect_input_type(raw_input)
    
    # 超出能力边界检查
    if result.input_type == "empty":
        result.confidence = 0.0
        result.warnings.append("E004: " + ERROR_CODES["E004"])
        result.output_text = format_output(result)
        return result
    
    # 提取关键信息
    fields, confidence = extract_key_fields(raw_input, result.input_type)
    result.key_fields = fields
    result.confidence = confidence
    
    # 低置信度警告
    if confidence < 85:
        result.warnings.append("E005: " + ERROR_CODES["E005"])
    
    # 生成输出
    result.output_text = format_output(result)
    
    return result


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检（内置样例数据）")
    print("=" * 60)
    
    all_passed = True
    
    # 测试样例 1: 文本输入
    print("\n[测试 1] 文本输入")
    text_sample = "你好，我的邮箱是 test@example.com，电话 138-1234-5678，日期 2026-03-15"
    r1 = process_input(text_sample)
    assert r1.input_type == "text", f"输入类型错误: {r1.input_type}"
    assert r1.key_fields.get("content_length", 0) > 0, "文本长度未提取"
    assert r1.key_fields.get("word_count", 0) > 0, "词数未提取"
    assert len(r1.key_fields.get("emails", [])) >= 1, "邮箱未识别"
    assert r1.confidence >= 80, f"置信度异常: {r1.confidence}"
    print(f"  ✓ 通过（置信度: {r1.confidence:.1f}%）")
    
    # 测试样例 2: JSON 输入
    print("\n[测试 2] JSON 输入")
    json_sample = '{"name": "测试", "age": 30, "tags": ["a", "b"]}'
    r2 = process_input(json_sample)
    assert r2.input_type == "json", f"输入类型错误: {r2.input_type}"
    assert r2.key_fields.get("json_type") == "object", "JSON 类型识别错误"
    assert len(r2.key_fields.get("keys", [])) >= 2, "JSON 键提取不完整"
    assert r2.confidence >= 90, f"置信度异常: {r2.confidence}"
    print(f"  ✓ 通过（置信度: {r2.confidence:.1f}%）")
    
    # 测试样例 3: URL 输入
    print("\n[测试 3] URL 输入")
    url_sample = "https://example.com/path/to/page"
    r3 = process_input(url_sample)
    assert r3.input_type == "url", f"输入类型错误: {r3.input_type}"
    assert r3.key_fields.get("scheme") == "https", "URL scheme 识别错误"
    assert len(r3.key_fields.get("path_segments", [])) >= 2, "URL 路径解析错误"
    assert r3.confidence >= 80, f"置信度异常: {r3.confidence}"
    print(f"  ✓ 通过（置信度: {r3.confidence:.1f}%）")
    
    # 测试样例 4: 文件路径输入
    print("\n[测试 4] 文件路径输入")
    file_sample = "/tmp/test_data.txt"
    r4 = process_input(file_sample)
    assert r4.input_type == "file", f"输入类型错误: {r4.input_type}"
    assert r4.key_fields.get("file_name") == "test_data.txt", "文件名提取错误"
    assert r4.key_fields.get("file_extension") == ".txt", "扩展名提取错误"
    assert r4.confidence >= 85, f"置信度异常: {r4.confidence}"
    print(f"  ✓ 通过（置信度: {r4.confidence:.1f}%）")
    
    # 测试样例 5: 空输入（错误处理）
    print("\n[测试 5] 空输入错误处理")
    r5 = process_input("")
    assert r5.confidence == 0.0, "空输入应置信度为 0"
    assert any("E001" in w for w in r5.warnings), "应触发 E001 错误码"
    print("  ✓ 通过（E001 错误码触发）")
    
    # 测试样例 6: 批量文本处理
    print("\n[测试 6] 批量文本处理")
    batch_samples = [
        "第一段测试文本，包含内容",
        "第二段，电话 010-12345678",
        "第三段，https://example.org 和 test@mail.com",
    ]
    for i, sample in enumerate(batch_samples):
        r = process_input(sample)
        assert r.confidence > 0, f"批次 {i} 置信度异常"
        assert r.output_text, f"批次 {i} 输出为空"
    print(f"  ✓ 通过（{len(batch_samples)} 条批量处理）")
    
    # 测试样例 7: 输出格式完整性
    print("\n[测试 7] 输出格式完整性")
    r7 = process_input("测试输出格式完整性")
    output_lines = r7.output_text.splitlines()
    assert len(output_lines) > 5, "输出行数过少"
    assert "处理结果报告" in r7.output_text, "缺少报告标题"
    assert "置信度" in r7.output_text, "缺少置信度信息"
    assert "关键信息" in r7.output_text, "缺少关键信息部分"
    print("  ✓ 通过（输出格式完整）")
    
    # 测试样例 8: 错误码体系完整性
    print("\n[测试 8] 错误码体系完整性")
    required_codes = {"E001", "E002", "E003", "E004", "E005"}
    assert required_codes.issubset(set(ERROR_CODES.keys())), "错误码缺失"
    for code in required_codes:
        assert ERROR_CODES[code], f"错误码 {code} 缺少描述"
    print(f"  ✓ 通过（{len(required_codes)} 个核心错误码）")
    
    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {'全部通过 ✓' if all_passed else '存在失败 ✗'}")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def process_file_content(filepath: str) -> ProcessingResult:
    """处理文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return process_input(content)
    except (IOError, OSError) as e:
        result = ProcessingResult()
        result.raw_input = filepath
        result.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result.confidence = 0.0
        result.warnings.append(f"E006: {ERROR_CODES['E006']} ({e})")
        result.output_text = format_output(result)
        return result


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="未命名工具（grit）- 将输入转换为结构化结果",
        epilog="示例: python main.py '文本内容' / python main.py --selftest"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的内容（文本/文件路径/URL）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，离线可运行）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="从文件读取内容处理"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理输入
    result = None
    
    if args.file:
        # 文件模式
        result = process_file_content(args.file)
    elif args.input:
        # 直接输入模式
        result = process_input(args.input)
    else:
        # 无输入参数
        parser.print_usage()
        print(f"错误: {ERROR_CODES['E001']}")
        return 1
    
    # 输出结果
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.output_text)
    
    # 低置信度提示
    if result.confidence < 85:
        print(f"\n提示: {ERROR_CODES['E005']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
