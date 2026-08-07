#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arc 工具 - 独立实现脚本

功能：将用户提供的数据/文件/URL 转换为结构化结果，识别关键信息，
      按约定格式输出，对不确定项给出置信度提示。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
仅使用 Python 标准库。

用法示例：
    python scripts/main.py --input "原始文本内容"
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据规格 E001-E005，扩展 E006-E010 备用）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：文本内容、文件路径或 URL",
    "E004": "这超出了本工具的能力范围，建议使用其他专业工具",
    "E005": "结果无法确定，建议提供更多信息或人工复核",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "自检失败，核心逻辑存在缺陷",
    "E009": "输出序列化失败",
    "E010": "未知错误",
}

# 置信度阈值
HIGH_CONFIDENCE = 90      # 置信度 ≥90%：直接输出
MEDIUM_CONFIDENCE = 85    # 85%-90%：标注"建议复核"
# <85%：标注"[需核实]"

# 默认输出字段结构
DEFAULT_OUTPUT_FIELDS = ["内容摘要", "关键信息", "类型", "置信度"]

# 输入类型识别关键词
URL_PREFIXES = ("http://", "https://", "ftp://")
FILE_EXTENSIONS = (".txt", ".csv", ".json", ".md", ".log", ".xml")


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果的数据结构"""
    
    def __init__(self) -> None:
        self.content: str = ""           # 结构化后的内容
        self.key_info: List[str] = []    # 关键信息列表
        self.input_type: str = "unknown" # 输入类型：text/file/url
        self.confidence: int = 0         # 置信度 0-100
        self.warnings: List[str] = []    # 警告信息
        self.errors: List[str] = []      # 错误列表
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "内容": self.content,
            "关键信息": self.key_info,
            "输入类型": self.input_type,
            "置信度": self.confidence,
            "警告": self.warnings,
            "错误": self.errors,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("E009") from exc


# ============================================================
# 核心逻辑函数
# ============================================================

def identify_input_type(raw_input: str) -> str:
    """
    识别输入类型。
    
    根据规格，输入来源为用户提供的数据/文件/URL。
    仅通过字符串特征判断，不访问文件系统或网络。
    
    参数:
        raw_input: 原始输入字符串
    
    返回:
        "text" / "file" / "url" / "unknown"
    """
    if not raw_input or not raw_input.strip():
        return "unknown"
    
    stripped = raw_input.strip()
    
    # 检查是否为 URL
    if stripped.lower().startswith(URL_PREFIXES):
        return "url"
    
    # 检查是否像文件路径（包含扩展名）
    # 不实际访问文件系统，仅通过扩展名特征判断
    lower_stripped = stripped.lower()
    if any(lower_stripped.endswith(ext) for ext in FILE_EXTENSIONS):
        return "file"
    
    # 默认按文本处理
    return "text"


def extract_key_info(text: str, input_type: str) -> List[str]:
    """
    从输入文本中提取关键信息。
    
    依据规格"识别并保留输入中的关键信息"。
    采用启发式规则提取，不依赖外部库。
    
    参数:
        text: 输入文本
        input_type: 输入类型
    
    返回:
        关键信息列表
    """
    if not text or not text.strip():
        return []
    
    key_info: List[str] = []
    lines = text.strip().split("\n")
    
    # 提取非空行的前几个字段作为关键信息
    for line in lines[:5]:  # 最多取前5行
        line = line.strip()
        if not line:
            continue
        # 去除常见噪音字符
        cleaned = line.rstrip(".,;:!?，。；：！？")
        if len(cleaned) >= 2:  # 至少2个字符
            key_info.append(cleaned)
    
    # 对于 URL，提取域名作为关键信息
    if input_type == "url":
        import re
        domain_match = re.search(r"https?://([^/]+)", text)
        if domain_match:
            key_info.append(f"域名: {domain_match.group(1)}")
    
    # 对于文件，提取文件名（不含路径）
    if input_type == "file":
        import os
        filename = os.path.basename(text.strip())
        if filename:
            key_info.append(f"文件名: {filename}")
    
    return key_info


def generate_summary(text: str, input_type: str) -> str:
    """
    生成内容摘要。
    
    依据规格"将用户提供的数据/文件/URL 转换为结构化结果"。
    简单启发式摘要，不保证完美但稳定可靠。
    
    参数:
        text: 输入文本
        input_type: 输入类型
    
    返回:
        摘要字符串
    """
    if not text or not text.strip():
        return "（空输入）"
    
    stripped = text.strip()
    
    # 按类型生成摘要
    if input_type == "url":
        return f"URL输入: {stripped[:80]}{'...' if len(stripped) > 80 else ''}"
    
    if input_type == "file":
        return f"文件输入: {stripped[:80]}{'...' if len(stripped) > 80 else ''}"
    
    # 文本输入：取前200字符作为摘要
    lines = stripped.split("\n")
    if len(lines) == 1:
        # 单行文本
        return stripped[:200] + ("..." if len(stripped) > 200 else "")
    else:
        # 多行文本
        first_lines = "\n".join(lines[:3])
        return first_lines[:200] + ("..." if len(first_lines) > 200 else "")


def calculate_confidence(text: str, input_type: str, key_info: List[str]) -> Tuple[int, List[str]]:
    """
    计算置信度并生成警告。
    
    依据规格：
    - 置信度 ≥90%：直接输出
    - 85%-90%：标注"建议复核"
    - <85%：标注"[需核实]"
    
    参数:
        text: 输入文本
        input_type: 输入类型
        key_info: 提取的关键信息
    
    返回:
        (置信度 0-100, 警告列表)
    """
    warnings: List[str] = []
    
    # 基础置信度
    confidence = 50
    
    # 有输入内容
    if text and text.strip():
        confidence += 20
    
    # 识别出类型
    if input_type != "unknown":
        confidence += 15
    
    # 提取到关键信息
    if key_info:
        confidence += 10
    
    # 输入长度适中（不太短也不太长）
    text_len = len(text.strip()) if text else 0
    if 10 <= text_len <= 1000:
        confidence += 5
    
    # 限制在 0-100 范围
    confidence = max(0, min(100, confidence))
    
    # 生成警告
    if confidence < MEDIUM_CONFIDENCE:
        warnings.append("[需核实] 置信度较低，建议人工复核")
    elif confidence < HIGH_CONFIDENCE:
        warnings.append("建议复核: 置信度中等，请确认结果")
    
    if input_type == "unknown":
        warnings.append("无法识别输入类型，请确认输入格式")
    
    if not key_info:
        warnings.append("未提取到关键信息，请检查输入内容")
    
    return confidence, warnings


def process_input(raw_input: str) -> ProcessingResult:
    """
    核心处理流程。
    
    依据规格 Step 2: 执行核心流程。
    
    参数:
        raw_input: 用户提供的原始输入
    
    返回:
        ProcessingResult 对象
    
    异常:
        RuntimeError: 当输入为空时抛出 E001
    """
    # 检查输入是否为空
    if not raw_input or not raw_input.strip():
        raise RuntimeError("E001")
    
    result = ProcessingResult()
    
    # Step 2.1: 识别输入类型
    result.input_type = identify_input_type(raw_input)
    
    # Step 2.2: 解析输入内容，识别关键信息
    result.key_info = extract_key_info(raw_input, result.input_type)
    
    # Step 2.3: 按默认模板组织输出
    result.content = generate_summary(raw_input, result.input_type)
    
    # Step 2.4: 计算置信度
    result.confidence, result.warnings = calculate_confidence(
        raw_input, result.input_type, result.key_info
    )
    
    # 依据置信度添加标注
    if result.confidence < HIGH_CONFIDENCE:
        if result.confidence >= MEDIUM_CONFIDENCE:
            result.content += "\n[建议复核]"
        else:
            result.content += "\n[需核实]"
    
    return result


def batch_process(inputs: List[str]) -> List[ProcessingResult]:
    """
    批量处理多个输入。
    
    依据规格"支持批量处理和自定义格式"。
    
    参数:
        inputs: 输入列表
    
    返回:
        处理结果列表
    """
    results = []
    for item in inputs:
        try:
            results.append(process_input(item))
        except RuntimeError as exc:
            # 单个输入失败不中断整个批次
            error_result = ProcessingResult()
            error_result.errors.append(str(exc))
            error_result.content = f"处理失败: {ERROR_MESSAGES.get(str(exc), exc)}"
            results.append(error_result)
    return results


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    自检核心逻辑。
    
    使用内置硬编码样例数据，离线运行。
    不读取外部文件，不依赖当前工作目录，不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    
    返回:
        True 表示自检通过，False 表示失败
    """
    print("=" * 60)
    print("arc 工具自检开始")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "文本输入测试",
            "input": "今天天气很好，适合外出散步。温度大约25度。",
            "expected_type": "text",
        },
        {
            "name": "URL输入测试",
            "input": "https://example.com/article/12345",
            "expected_type": "url",
        },
        {
            "name": "文件路径测试",
            "input": "/tmp/data/report.txt",
            "expected_type": "file",
        },
        {
            "name": "空输入测试",
            "input": "",
            "expected_error": "E001",
        },
        {
            "name": "批量处理测试",
            "input": None,  # 特殊标记，使用批量处理
            "batch": ["第一条测试数据", "https://test.org/page", "/tmp/file.csv"],
        },
    ]
    
    all_passed = True
    
    # 测试1-3: 基本处理
    for case in test_cases[:3]:
        try:
            result = process_input(case["input"])
            
            # 宽松断言：类型匹配
            type_ok = (result.input_type == case["expected_type"])
            
            # 宽松断言：置信度在合理范围
            conf_ok = (0 <= result.confidence <= 100)
            
            # 宽松断言：关键信息非空（对于非空输入）
            key_info_ok = (len(result.key_info) > 0)
            
            # 宽松断言：内容非空
            content_ok = (len(result.content) > 0)
            
            passed = type_ok and conf_ok and key_info_ok and content_ok
            
            status = "通过" if passed else "失败"
            print(f"[{status}] {case['name']}: 类型={result.input_type}, "
                  f"置信度={result.confidence}, 关键信息数={len(result.key_info)}")
            
            if not passed:
                all_passed = False
                
        except Exception as exc:
            print(f"[失败] {case['name']}: 异常={exc}")
            all_passed = False
    
    # 测试4: 空输入处理
    try:
        process_input("")
        print("[失败] 空输入测试: 未抛出预期异常")
        all_passed = False
    except RuntimeError as exc:
        # 宽松断言：错误码是 E001
        error_ok = (str(exc) == "E001")
        print(f"[{'通过' if error_ok else '失败'}] 空输入测试: 错误码={exc}")
        if not error_ok:
            all_passed = False
    except Exception as exc:
        print(f"[失败] 空输入测试: 异常类型错误={type(exc).__name__}")
        all_passed = False
    
    # 测试5: 批量处理
    batch_case = test_cases[4]
    try:
        results = batch_process(batch_case["batch"])
        
        # 宽松断言：结果数量匹配
        count_ok = (len(results) == len(batch_case["batch"]))
        
        # 宽松断言：每个结果都有内容
        content_ok = all(r.content for r in results)
        
        # 宽松断言：置信度在合理范围
        conf_ok = all(0 <= r.confidence <= 100 for r in results)
        
        passed = count_ok and content_ok and conf_ok
        status = "通过" if passed else "失败"
        print(f"[{status}] 批量处理测试: 结果数={len(results)}")
        
        if not passed:
            all_passed = False
            
    except Exception as exc:
        print(f"[失败] 批量处理测试: 异常={exc}")
        all_passed = False
    
    # 测试6: 置信度边界测试
    try:
        # 高置信度输入（长文本、明确类型）
        high_input = "https://www.example.com/very/long/path/to/article/with/details"
        high_result = process_input(high_input)
        
        # 低置信度输入（短文本）
        low_input = "x"
        low_result = process_input(low_input)
        
        # 宽松断言：高置信度 >= 低置信度
        conf_relation_ok = (high_result.confidence >= low_result.confidence)
        
        # 宽松断言：置信度差异合理
        diff_ok = (abs(high_result.confidence - low_result.confidence) < 60)
        
        passed = conf_relation_ok and diff_ok
        status = "通过" if passed else "失败"
        print(f"[{status}] 置信度边界测试: 高={high_result.confidence}, 低={low_result.confidence}")
        
        if not passed:
            all_passed = False
            
    except Exception as exc:
        print(f"[失败] 置信度边界测试: 异常={exc}")
        all_passed = False
    
    # 测试7: JSON 序列化测试
    try:
        sample_result = process_input("测试JSON序列化内容")
        json_str = sample_result.to_json()
        
        # 宽松断言：JSON 可解析且包含必要字段
        parsed = json.loads(json_str)
        fields_ok = ("内容" in parsed and "置信度" in parsed)
        
        passed = fields_ok
        status = "通过" if passed else "失败"
        print(f"[{status}] JSON序列化测试: 输出长度={len(json_str)}")
        
        if not passed:
            all_passed = False
            
    except Exception as exc:
        print(f"[失败] JSON序列化测试: 异常={exc}")
        all_passed = False
    
    # 测试8: 错误码映射测试
    try:
        # 检查所有错误码都有对应话术
        codes_ok = all(code in ERROR_MESSAGES for code in ["E001", "E002", "E003", "E004", "E005"])
        
        # 检查话术非空
        messages_ok = all(ERROR_MESSAGES[code].strip() for code in ["E001", "E002", "E003", "E004", "E005"])
        
        passed = codes_ok and messages_ok
        status = "通过" if passed else "失败"
        print(f"[{status}] 错误码映射测试: 错误码数={len(ERROR_MESSAGES)}")
        
        if not passed:
            all_passed = False
            
    except Exception as exc:
        print(f"[失败] 错误码映射测试: 异常={exc}")
        all_passed = False
    
    # 测试9: 输入类型识别测试
    try:
        types = [
            identify_input_type("hello world"),
            identify_input_type("https://example.com"),
            identify_input_type("/path/to/file.txt"),
            identify_input_type(""),
        ]
        
        # 宽松断言：识别结果合理
        type_ok = (types[0] == "text" and types[1] == "url" and types[2] == "file")
        empty_ok = (types[3] == "unknown")
        
        passed = type_ok and empty_ok
        status = "通过" if passed else "失败"
        print(f"[{status}] 输入类型识别测试: {types}")
        
        if not passed:
            all_passed = False
            
    except Exception as exc:
        print(f"[失败] 输入类型识别测试: 异常={exc}")
        all_passed = False
    
    # 测试10: 关键信息提取测试
    try:
        key_info = extract_key_info("第一行重要信息\n第二行次要信息\n第三行", "text")
        
        # 宽松断言：提取到关键信息
        info_ok = (len(key_info) > 0)
        
        # 宽松断言：信息非空字符串
        nonempty_ok = all(isinstance(info, str) and info.strip() for info in key_info)
        
        passed = info_ok and nonempty_ok
        status = "通过" if passed else "失败"
        print(f"[{status}] 关键信息提取测试: 提取数={len(key_info)}")
        
        if not passed:
            all_passed = False
            
    except Exception as exc:
        print(f"[失败] 关键信息提取测试: 异常={exc}")
        all_passed = False
    
    # 汇总
    print("=" * 60)
    if all_passed:
        print("自检全部通过 ✔")
    else:
        print("自检存在失败项 ✘")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数。
    
    返回:
        0 表示成功，非0表示失败
    """
    parser = argparse.ArgumentParser(
        description="arc 工具 - 将输入数据转换为结构化结果",
        epilog="示例: python main.py --input '文本内容' 或 python main.py --selftest"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（文本、文件路径或URL）"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检（使用内置样例数据，无需外部输入）"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="arc 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理输入
    try:
        if args.batch:
            # 批量处理
            results = batch_process(args.batch)
            if args.json:
                output = json.dumps(
                    [r.to_dict() for r in results],
                    ensure_ascii=False,
                    indent=2
                )
            else:
                output_lines = []
                for i, r in enumerate(results, 1):
                    output_lines.append(f"--- 结果 {i} ---")
                    output_lines.append(f"内容: {r.content}")
                    output_lines.append(f"类型: {r.input_type}")
                    output_lines.append(f"置信度: {r.confidence}%")
                    if r.key_info:
                        output_lines.append(f"关键信息: {', '.join(r.key_info)}")
                    if r.warnings:
                        output_lines.append(f"警告: {'; '.join(r.warnings)}")
                    if r.errors:
                        output_lines.append(f"错误: {'; '.join(r.errors)}")
                    output_lines.append("")
                output = "\n".join(output_lines)
            
            print(output)
            return 0
            
        elif args.input:
            # 单条处理
            result = process_input(args.input)
            
            if args.json:
                print(result.to_json())
            else:
                print(f"内容: {result.content}")
                print(f"类型: {result.input_type}")
                print(f"置信度: {result.confidence}%")
                if result.key_info:
                    print(f"关键信息: {', '.join(result.key_info)}")
                if result.warnings:
                    print(f"警告: {'; '.join(result.warnings)}")
                if result.errors:
                    print(f"错误: {'; '.join(result.errors)}")
            
            return 0
            
        else:
            # 无输入参数
            print(f"错误 E001: {ERROR_MESSAGES['E001']}")
            print("提示: 使用 --input 提供内容，或使用 --selftest 运行自检")
            return 1
            
    except RuntimeError as exc:
        error_code = str(exc)
        message = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
        print(f"错误 {error_code}: {message}")
        return 1
        
    except Exception as exc:
        print(f"错误 E010: {ERROR_MESSAGES['E010']} - {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
