#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gitgo - Git 自动化命令行工具（独立实现）

功能：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

本脚本仅依据功能规格独立实现，不复制任何既有代码。
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 版本信息
VERSION = "1.0.0"
TOOL_NAME = "gitgo"

# 错误码与话术映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议",
    "E005": "结果无法确定，建议：",
    "E006": "输入内容无法解析为有效数据",
    "E007": "输出格式不支持",
    "E008": "批量处理时出现错误，已中止",
    "E009": "文件读取失败",
    "E010": "内部处理异常",
}

# 置信度阈值
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果数据结构"""
    
    def __init__(self, data: Any = None, confidence: int = 100, 
                 warnings: List[str] = None, metadata: Dict = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(data: Any) -> Tuple[bool, str]:
    """
    验证输入是否有效
    
    参数:
        data: 用户输入的数据
        
    返回:
        (是否有效, 错误信息)
    """
    if data is None:
        return False, "E001"
    
    if isinstance(data, str):
        if not data.strip():
            return False, "E001"
    elif isinstance(data, (list, dict)):
        if len(data) == 0:
            return False, "E001"
    else:
        return False, "E003"
    
    return True, ""


def extract_key_info(data: Any) -> Dict:
    """
    从输入中提取关键信息
    
    参数:
        data: 输入数据（字符串、列表、字典）
        
    返回:
        提取的关键信息字典
    """
    result = {
        "type": type(data).__name__,
        "size": 0,
        "content": None,
        "key_fields": {},
        "confidence": 100,
        "warnings": [],
    }
    
    if isinstance(data, str):
        # 字符串输入
        result["size"] = len(data)
        result["content"] = data.strip()
        
        # 检测是否为 URL
        if re.match(r'^https?://', data.strip()):
            result["key_fields"]["url"] = data.strip()
            result["key_fields"]["format"] = "url"
        # 检测是否为 JSON
        elif data.strip().startswith(('{', '[')):
            try:
                parsed = json.loads(data)
                result["key_fields"]["format"] = "json"
                result["content"] = parsed
                result["key_fields"]["structure"] = type(parsed).__name__
            except json.JSONDecodeError:
                result["warnings"].append("输入看似 JSON 但无法解析")
                result["confidence"] = 80
        # 视为普通文本
        else:
            result["key_fields"]["format"] = "text"
            # 提取可能的键值对
            lines = data.strip().split('\n')
            for line in lines[:10]:  # 最多检查前10行
                if ':' in line:
                    key, _, value = line.partition(':')
                    result["key_fields"][key.strip()] = value.strip()
    
    elif isinstance(data, list):
        result["size"] = len(data)
        result["content"] = data
        result["key_fields"]["format"] = "list"
        result["key_fields"]["items"] = len(data)
        
        # 检查列表元素类型一致性
        if data:
            first_type = type(data[0]).__name__
            all_same = all(type(item).__name__ == first_type for item in data)
            if not all_same:
                result["warnings"].append("列表元素类型不一致")
                result["confidence"] = 85
    
    elif isinstance(data, dict):
        result["size"] = len(data)
        result["content"] = data
        result["key_fields"]["format"] = "dict"
        result["key_fields"]["keys"] = list(data.keys())
    
    return result


def process_batch(items: List[Any]) -> ProcessingResult:
    """
    批量处理多个输入
    
    参数:
        items: 输入项列表
        
    返回:
        处理结果
    """
    results = []
    warnings = []
    
    for i, item in enumerate(items):
        try:
            valid, err_code = validate_input(item)
            if not valid:
                warnings.append(f"第 {i+1} 项无效: {ERROR_MESSAGES[err_code]}")
                continue
            
            info = extract_key_info(item)
            results.append({
                "index": i + 1,
                "info": info,
            })
        except Exception as e:
            warnings.append(f"第 {i+1} 项处理异常: {str(e)}")
    
    # 计算整体置信度
    if results:
        avg_confidence = sum(r["info"]["confidence"] for r in results) / len(results)
    else:
        avg_confidence = 0
    
    return ProcessingResult(
        data=results,
        confidence=int(avg_confidence),
        warnings=warnings,
        metadata={"batch_size": len(items), "success_count": len(results)}
    )


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    格式化输出结果
    
    参数:
        result: 处理结果
        output_format: 输出格式（json/text）
        
    返回:
        格式化后的字符串
    """
    if output_format == "json":
        return result.to_json()
    elif output_format == "text":
        lines = []
        if isinstance(result.data, list):
            for item in result.data:
                if isinstance(item, dict) and "info" in item:
                    info = item["info"]
                    lines.append(f"项 {item['index']}:")
                    lines.append(f"  类型: {info.get('type', 'unknown')}")
                    lines.append(f"  格式: {info.get('key_fields', {}).get('format', 'unknown')}")
                    if info.get("key_fields", {}).get("url"):
                        lines.append(f"  URL: {info['key_fields']['url']}")
                    if info.get("key_fields", {}).get("items") is not None:
                        lines.append(f"  项目数: {info['key_fields']['items']}")
        else:
            lines.append(f"类型: {result.data.get('type', 'unknown')}")
            lines.append(f"格式: {result.data.get('key_fields', {}).get('format', 'unknown')}")
        
        lines.append(f"置信度: {result.confidence}%")
        if result.warnings:
            lines.append("警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)
    else:
        raise ValueError(f"E007: 不支持的输出格式: {output_format}")


# ============================================================
# 主处理函数
# ============================================================

def main_process(input_data: Any, output_format: str = "json") -> ProcessingResult:
    """
    主处理流程
    
    参数:
        input_data: 输入数据
        output_format: 输出格式
        
    返回:
        处理结果
    """
    # Step 1: 验证输入
    valid, err_code = validate_input(input_data)
    if not valid:
        return ProcessingResult(
            data=None,
            confidence=0,
            warnings=[ERROR_MESSAGES[err_code]],
            metadata={"error": err_code}
        )
    
    # Step 2: 批量处理
    if isinstance(input_data, list) and len(input_data) > 1:
        result = process_batch(input_data)
    else:
        # 单条处理
        info = extract_key_info(input_data)
        result = ProcessingResult(
            data=info,
            confidence=info["confidence"],
            warnings=info["warnings"],
            metadata={"processed_at": datetime.now().isoformat()}
        )
    
    # Step 3: 置信度标注
    if result.confidence >= HIGH_CONFIDENCE:
        pass  # 直接输出
    elif result.confidence >= MEDIUM_CONFIDENCE:
        result.warnings.append("建议复核")
    else:
        result.warnings.append("[需核实] 结果不确定，请人工确认")
    
    return result


# ============================================================
# 自测函数
# ============================================================

def run_selftest() -> bool:
    """
    执行内置自测，验证核心逻辑
    
    返回:
        True 表示测试通过
    """
    print(f"{TOOL_NAME} 自测开始...")
    all_passed = True
    
    # 测试 1: 空输入处理
    print("测试 1: 空输入处理")
    result = main_process(None)
    assert result.confidence == 0, "空输入应该返回置信度 0"
    assert result.metadata.get("error") == "E001", "空输入应该返回 E001"
    print("  ✓ 通过")
    
    # 测试 2: 文本输入处理
    print("测试 2: 文本输入处理")
    text_input = "name: test\nvalue: 123"
    result = main_process(text_input)
    assert result.confidence > 50, "有效输入置信度应大于 50"
    assert result.data["key_fields"].get("name") == "test", "应提取 name 字段"
    print("  ✓ 通过")
    
    # 测试 3: JSON 输入处理
    print("测试 3: JSON 输入处理")
    json_input = '{"name": "test", "value": 123}'
    result = main_process(json_input)
    assert result.confidence > 80, "JSON 输入置信度应较高"
    assert result.data["key_fields"].get("format") == "json", "应识别 JSON 格式"
    print("  ✓ 通过")
    
    # 测试 4: 列表批量处理
    print("测试 4: 列表批量处理")
    list_input = ["item1", "item2", "item3"]
    result = main_process(list_input)
    assert result.data is not None, "列表处理应返回数据"
    assert result.confidence > 50, "批量处理置信度应大于 50"
    print("  ✓ 通过")
    
    # 测试 5: URL 识别
    print("测试 5: URL 识别")
    url_input = "https://example.com/test"
    result = main_process(url_input)
    assert result.data["key_fields"].get("url") == url_input, "应识别 URL"
    assert result.data["key_fields"].get("format") == "url", "应标记为 URL 格式"
    print("  ✓ 通过")
    
    # 测试 6: 输出格式验证
    print("测试 6: 输出格式验证")
    result = main_process("test data")
    json_output = format_output(result, "json")
    assert json_output.startswith("{"), "JSON 输出应以 { 开头"
    text_output = format_output(result, "text")
    assert "置信度" in text_output, "文本输出应包含置信度"
    print("  ✓ 通过")
    
    # 测试 7: 错误码验证
    print("测试 7: 错误码验证")
    assert "E001" in ERROR_MESSAGES, "应包含 E001"
    assert "E002" in ERROR_MESSAGES, "应包含 E002"
    assert "E003" in ERROR_MESSAGES, "应包含 E003"
    assert "E004" in ERROR_MESSAGES, "应包含 E004"
    assert "E005" in ERROR_MESSAGES, "应包含 E005"
    print("  ✓ 通过")
    
    # 测试 8: 字典输入处理
    print("测试 8: 字典输入处理")
    dict_input = {"key1": "value1", "key2": "value2"}
    result = main_process(dict_input)
    assert result.data["key_fields"].get("format") == "dict", "应识别字典格式"
    assert "key1" in result.data["key_fields"].get("keys", []), "应提取键名"
    print("  ✓ 通过")
    
    # 测试 9: 复杂嵌套列表
    print("测试 9: 复杂嵌套列表")
    complex_list = ["simple", {"nested": "dict"}, ["list", "inside"]]
    result = main_process(complex_list)
    assert result.confidence > 0, "复杂输入应返回置信度"
    print("  ✓ 通过")
    
    # 测试 10: 长文本处理
    print("测试 10: 长文本处理")
    long_text = "line1: value1\nline2: value2\n"
    long_text += "line3: value3\n" * 10  # 总长度超过 10 行
    result = main_process(long_text)
    assert result.data["size"] > 50, "长文本应正确统计大小"
    print("  ✓ 通过")
    
    print("=" * 50)
    print("所有自测通过！")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description=f"{TOOL_NAME} - Git 自动化命令行工具 v{VERSION}",
        epilog="示例: python main.py --input 'data.txt' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        help="输入数据（字符串、JSON、文件路径或 URL）"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入为多行）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"{TOOL_NAME} {VERSION}"
    )
    
    args = parser.parse_args()
    
    # 运行自测
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"自测失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"自测异常: {e}")
            sys.exit(1)
    
    # 无输入参数时显示帮助
    if not args.input:
        parser.print_help()
        sys.exit(0)
    
    # 处理输入
    try:
        # 检查是否为文件路径
        input_data = args.input
        if os.path.isfile(input_data):
            try:
                with open(input_data, 'r', encoding='utf-8') as f:
                    input_data = f.read()
            except Exception as e:
                print(f"E009: 文件读取失败 - {e}")
                sys.exit(1)
        
        # 批量处理模式
        if args.batch and isinstance(input_data, str):
            items = input_data.strip().split('\n')
            input_data = items
        
        # 尝试解析 JSON
        if isinstance(input_data, str) and input_data.strip().startswith(('{', '[')):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError:
                pass  # 保持字符串处理
        
        # 执行主处理
        result = main_process(input_data, args.format)
        
        # 输出结果
        try:
            output = format_output(result, args.format)
            print(output)
        except ValueError as e:
            print(f"E007: {e}")
            sys.exit(1)
        
        # 根据置信度设置退出码
        if result.confidence < MEDIUM_CONFIDENCE:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"E010: 内部处理异常 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
