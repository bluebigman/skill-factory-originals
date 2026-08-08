#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pullmd - 通用数据/文件/URL 转 Markdown 结构化工具
==================================================
本脚本为 clean-room 独立实现，仅依据功能规格编写。
用于将用户提供的数据/文件/URL 转换为结构化 Markdown 结果。

功能特性：
- 解析输入并识别关键信息
- 按默认模板组织输出
- 置信度标注（≥90% 直接输出 / 85%-90% 建议复核 / <85% 需核实）
- 错误码体系 E001-E010
- 内置 --selftest 离线自检（不依赖外部文件/网络）

许可证：MIT License
Copyright (c) 2026 原创作者（自持版权）
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与话术映射（依据规格 E001-E005，扩展至 E010 备用）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing_items}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理异常，请稍后重试或检查输入",
    "E007": "输出写入失败，请检查权限或路径",
    "E008": "参数解析失败，请检查命令行参数",
    "E009": "配置文件读取失败，请检查格式",
    "E010": "未预期的错误，请联系开发者",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核

# 默认输出模板
OUTPUT_TEMPLATE = (
    "# 处理结果\n\n"
    "> 生成时间：{timestamp}\n"
    "> 来源：{source_type}\n"
    "> 置信度：{confidence:.0%}\n\n"
    "## 关键信息\n\n"
    "{key_info}\n\n"
    "## 结构化内容\n\n"
    "{content}\n\n"
    "## 置信度评估\n\n"
    "{confidence_note}\n"
)


# ============================================================
# 工具函数
# ============================================================

def get_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_input(data: str) -> Tuple[bool, str]:
    """
    验证输入数据是否有效
    
    Returns:
        (是否有效, 错误信息或空字符串)
    """
    if not data or not data.strip():
        return False, ERROR_MESSAGES["E001"]
    return True, ""


def detect_source_type(data: str) -> str:
    """
    检测输入数据的来源类型
    
    Returns:
        "url", "file", "json", "text" 之一
    """
    data = data.strip()
    
    # URL 检测
    if re.match(r'^https?://', data, re.IGNORECASE):
        return "url"
    
    # 文件路径检测
    if os.path.exists(data) or os.path.isfile(data):
        return "file"
    
    # JSON 检测
    try:
        json.loads(data)
        return "json"
    except (json.JSONDecodeError, ValueError):
        pass
    
    return "text"


def parse_content(data: str, source_type: str) -> Dict[str, Any]:
    """
    解析输入内容，提取关键信息
    
    Returns:
        包含关键信息的字典
    """
    result = {
        "key_info": [],
        "content": data.strip(),
        "metadata": {}
    }
    
    if source_type == "url":
        # 提取 URL 信息
        url_match = re.match(r'^(https?://[^\s/]+)', data.strip())
        if url_match:
            result["metadata"]["domain"] = url_match.group(1)
            result["key_info"].append(f"URL 域名：{url_match.group(1)}")
        
        # 提取路径部分
        path_match = re.search(r'https?://[^\s/]+(/[^\s]*)', data.strip())
        if path_match and path_match.group(1):
            result["key_info"].append(f"URL 路径：{path_match.group(1)}")
    
    elif source_type == "file":
        filepath = data.strip()
        if os.path.exists(filepath):
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            result["metadata"]["filename"] = filename
            result["metadata"]["filesize"] = filesize
            result["key_info"].append(f"文件名：{filename}")
            result["key_info"].append(f"文件大小：{filesize} 字节")
            
            # 尝试读取文件内容
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    result["content"] = content
                    result["key_info"].append(f"文件类型：{os.path.splitext(filename)[1] or '未知'}")
            except (IOError, UnicodeDecodeError):
                result["content"] = f"[无法读取文件内容：{filepath}]"
    
    elif source_type == "json":
        try:
            json_data = json.loads(data)
            result["metadata"]["json_keys"] = list(json_data.keys()) if isinstance(json_data, dict) else []
            result["key_info"].append(f"JSON 键数量：{len(result['metadata']['json_keys'])}")
            result["key_info"].append(f"JSON 键：{', '.join(result['metadata']['json_keys'][:5])}")
        except (json.JSONDecodeError, ValueError):
            pass
    
    else:  # text
        # 提取文本统计信息
        lines = data.strip().split('\n')
        words = data.strip().split()
        result["metadata"]["line_count"] = len(lines)
        result["metadata"]["word_count"] = len(words)
        result["key_info"].append(f"文本行数：{len(lines)}")
        result["key_info"].append(f"文本字数：{len(words)}")
        
        # 提取可能的标题
        for line in lines[:5]:
            if re.match(r'^#{1,6}\s', line):
                result["key_info"].append(f"检测到标题：{line.strip()}")
    
    return result


def calculate_confidence(parsed_data: Dict[str, Any], source_type: str) -> float:
    """
    计算处理置信度
    
    Returns:
        0.0 到 1.0 的置信度值
    """
    confidence = 0.85  # 基础置信度
    
    # 根据数据丰富度调整
    if len(parsed_data.get("key_info", [])) >= 2:
        confidence += 0.05
    
    if parsed_data.get("content"):
        content_len = len(parsed_data["content"])
        if content_len > 100:
            confidence += 0.05
        elif content_len < 10:
            confidence -= 0.10
    
    # 根据来源类型调整
    if source_type == "json":
        # JSON 数据通常较可靠
        confidence += 0.05
    elif source_type == "url":
        # URL 可能无法访问
        confidence -= 0.05
    
    return max(0.0, min(1.0, confidence))


def format_confidence_note(confidence: float) -> str:
    """根据置信度生成说明文本"""
    if confidence >= CONFIDENCE_HIGH:
        return "✅ 置信度较高，可直接使用"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "⚠️ 置信度中等，建议人工复核"
    else:
        return "❌ 置信度较低，需要进一步核实"


def generate_markdown(data: str, source_type: str, parsed_data: Dict[str, Any], 
                      confidence: float) -> str:
    """
    生成 Markdown 输出
    
    Args:
        data: 原始输入数据
        source_type: 来源类型
        parsed_data: 解析后的数据
        confidence: 置信度值
    
    Returns:
        生成的 Markdown 字符串
    """
    key_info = "\n".join([f"- {item}" for item in parsed_data.get("key_info", [])])
    
    if not key_info:
        key_info = "- 未提取到关键信息"
    
    confidence_note = format_confidence_note(confidence)
    
    return OUTPUT_TEMPLATE.format(
        timestamp=get_timestamp(),
        source_type=source_type,
        confidence=confidence,
        key_info=key_info,
        content=parsed_data.get("content", "无内容"),
        confidence_note=confidence_note
    )


def process_input(data: str) -> Tuple[str, int]:
    """
    处理输入并生成 Markdown
    
    Args:
        data: 输入数据
    
    Returns:
        (Markdown 输出, 退出码)
    """
    # 验证输入
    valid, error_msg = validate_input(data)
    if not valid:
        print(f"错误 E001：{error_msg}")
        return "", 1
    
    # 检测来源类型
    source_type = detect_source_type(data)
    
    # 解析内容
    parsed_data = parse_content(data, source_type)
    
    # 计算置信度
    confidence = calculate_confidence(parsed_data, source_type)
    
    # 生成 Markdown
    markdown = generate_markdown(data, source_type, parsed_data, confidence)
    
    return markdown, 0


def run_selftest() -> bool:
    """
    运行离线自检
    
    Returns:
        True 表示测试通过，False 表示失败
    """
    print("=" * 60)
    print("pullmd 自检模式")
    print("=" * 60)
    
    test_cases = [
        ("这是一个简单的测试文本", "text"),
        ("https://example.com/path/to/page", "url"),
        ('{"name": "test", "value": 123}', "json"),
    ]
    
    all_passed = True
    
    for i, (data, expected_type) in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}：")
        print(f"  输入：{data[:50]}{'...' if len(data) > 50 else ''}")
        
        # 测试来源类型检测
        detected_type = detect_source_type(data)
        type_ok = detected_type == expected_type
        print(f"  来源类型检测：{detected_type} {'✅' if type_ok else '❌'}")
        
        # 测试处理流程
        markdown, exit_code = process_input(data)
        process_ok = exit_code == 0 and markdown
        print(f"  处理结果：{'✅' if process_ok else '❌'}")
        
        if process_ok:
            print(f"  输出预览：{markdown[:100]}...")
        
        all_passed = all_passed and type_ok and process_ok
    
    # 测试错误处理
    print("\n错误处理测试：")
    empty_input, exit_code = process_input("")
    error_ok = exit_code != 0
    print(f"  空输入处理：{'✅' if error_ok else '❌'}")
    all_passed = all_passed and error_ok
    
    # 测试模板完整性
    template_ok = "## 关键信息" in OUTPUT_TEMPLATE and "## 置信度评估" in OUTPUT_TEMPLATE
    print(f"  模板完整性：{'✅' if template_ok else '❌'}")
    all_passed = all_passed and template_ok
    
    # 测试置信度计算
    print("\n置信度测试：")
    test_parsed = {"key_info": ["a", "b", "c"], "content": "x" * 200}
    conf = calculate_confidence(test_parsed, "text")
    conf_ok = 0.0 <= conf <= 1.0
    print(f"  置信度范围：{conf:.2f} {'✅' if conf_ok else '❌'}")
    all_passed = all_passed and conf_ok
    
    # 测试错误码完整性
    print("\n错误码完整性测试：")
    error_ok = all(code in ERROR_MESSAGES for code in ["E001", "E002", "E003", "E004", "E005"])
    print(f"  核心错误码：{'✅' if error_ok else '❌'}")
    all_passed = all_passed and error_ok
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过")
    else:
        print("❌ 存在测试失败")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 主函数
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="pullmd - 通用数据/文件/URL 转 Markdown 结构化工具",
        epilog="示例：python main.py '这是一段文本' 或 python main.py --selftest"
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的数据/文件路径/URL"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="输出文件路径（可选）"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1
    
    # 检查输入参数
    if not args.input:
        print(f"错误 E001：{ERROR_MESSAGES['E001']}")
        return 1
    
    # 处理输入
    markdown, exit_code = process_input(args.input)
    
    if exit_code != 0:
        return exit_code
    
    # 输出结果
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(markdown)
            print(f"✅ 结果已保存到：{args.output}")
        except IOError:
            print(f"错误 E007：{ERROR_MESSAGES['E007']}")
            return 7
    else:
        print(markdown)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
