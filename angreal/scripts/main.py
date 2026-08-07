#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
angreal - 任务自动化与项目模板工具（独立实现）

功能概述：
- 解析用户输入，识别关键信息并结构化
- 支持批量处理多个输入
- 按置信度分级标注输出
- 提供命令行接口与离线自检功能

本脚本仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与话术映射（E001-E010）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{\"input\": \"数据内容\", \"format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议使用专业工具处理",
    "E005": "结果无法确定，建议：提供更多上下文信息或人工复核",
    "E006": "批量处理时出现异常，请检查每个输入项的格式",
    "E007": "输出格式不支持，支持的格式：json、text",
    "E008": "置信度计算失败，请检查输入内容",
    "E009": "内部处理错误，请重试或联系管理员",
    "E010": "无法识别的命令参数，请使用 --help 查看帮助",
}

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 85

# 支持的输出格式
SUPPORTED_FORMATS = ["json", "text"]

# 关键信息字段的关键词映射（用于识别）
FIELD_KEYWORDS: Dict[str, List[str]] = {
    "name": ["name", "名称", "姓名"],
    "type": ["type", "类型"],
    "date": ["date", "日期", "time"],
    "amount": ["amount", "金额", "数量", "price", "价格"],
    "status": ["status", "状态"],
    "description": ["description", "描述", "备注"],
}


# ============================================================
# 核心工具函数
# ============================================================

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，尝试识别 JSON 格式或普通文本。

    参数:
        raw_input: 原始输入字符串

    返回:
        解析后的字典，包含 input 字段和 format 字段

    异常:
        ValueError: 当输入无法解析时抛出
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    # 尝试 JSON 解析
    try:
        parsed = json.loads(raw_input)
        if isinstance(parsed, dict):
            return parsed
        elif isinstance(parsed, list):
            return {"data": parsed, "format": "json"}
        else:
            return {"data": parsed, "format": "json"}
    except json.JSONDecodeError:
        # 不是 JSON，按纯文本处理
        pass

    # 尝试 key=value 格式（如 "name=test type=task"）
    kv_pattern = re.compile(r'(\w+)\s*=\s*([^,\s]+)')
    matches = kv_pattern.findall(raw_input)
    if matches:
        result = {k: v for k, v in matches}
        result["format"] = "kv"
        return result

    # 纯文本格式
    return {"input": raw_input.strip(), "format": "text"}


def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从输入数据中提取关键字段。

    参数:
        data: 输入数据字典

    返回:
        提取到的关键字段字典
    """
    extracted: Dict[str, Any] = {}
    
    for field, keywords in FIELD_KEYWORDS.items():
        # 直接匹配字段名
        if field in data:
            extracted[field] = data[field]
            continue
        
        # 通过关键词匹配
        for key, value in data.items():
            key_lower = str(key).lower()
            for keyword in keywords:
                if keyword.lower() in key_lower:
                    extracted[field] = value
                    break
            if field in extracted:
                break
    
    # 补充置信度评估
    if extracted:
        extracted["_confidence"] = calculate_confidence(extracted, data)
    
    return extracted


def calculate_confidence(extracted: Dict[str, Any], original: Dict[str, Any]) -> int:
    """
    计算提取结果的置信度（0-100）。

    参数:
        extracted: 提取的字段
        original: 原始数据

    返回:
        置信度分数（整数）
    """
    if not original:
        return 0
    
    # 计算字段覆盖率
    total_fields = len(original)
    extracted_fields = len(extracted) - 1  # 减去 _confidence 自身
    
    if total_fields == 0:
        return 50  # 无字段时给予中等置信度
    
    coverage = extracted_fields / total_fields
    
    # 根据覆盖率计算置信度
    if coverage >= 0.8:
        return 95
    elif coverage >= 0.6:
        return 88
    elif coverage >= 0.4:
        return 82
    elif coverage >= 0.2:
        return 75
    else:
        return 60


def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式输出结果。

    参数:
        data: 处理后的数据
        output_format: 输出格式（json 或 text）

    返回:
        格式化后的字符串

    异常:
        ValueError: 不支持的输出格式
    """
    if output_format not in SUPPORTED_FORMATS:
        raise ValueError("E007")
    
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    else:
        # 文本格式
        lines = []
        for key, value in data.items():
            if key.startswith("_"):
                continue
            lines.append(f"{key}: {value}")
        return "\n".join(lines)


def process_single_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    处理单个输入项。

    参数:
        raw_input: 原始输入
        output_format: 输出格式

    返回:
        处理结果字典
    """
    try:
        # 1. 解析输入
        parsed = parse_input(raw_input)
        
        # 2. 提取关键字段
        extracted = extract_key_fields(parsed)
        
        # 3. 构建输出结果
        result = {
            "status": "success",
            "data": extracted,
            "format": output_format,
        }
        
        # 4. 置信度标注
        confidence = extracted.get("_confidence", 50)
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            result["confidence_level"] = "high"
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            result["confidence_level"] = "medium"
            result["warning"] = "建议复核"
        else:
            result["confidence_level"] = "low"
            result["warning"] = "[需核实]"
            result["uncertain_points"] = "部分字段无法确认，请提供更多信息"
        
        return result
        
    except ValueError as e:
        error_code = str(e)
        return {
            "status": "error",
            "error_code": error_code,
            "message": ERROR_MESSAGES.get(error_code, "未知错误"),
        }
    except Exception:
        return {
            "status": "error",
            "error_code": "E009",
            "message": ERROR_MESSAGES["E009"],
        }


def batch_process(inputs: List[str], output_format: str = "json") -> Dict[str, Any]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        output_format: 输出格式

    返回:
        批量处理结果
    """
    if not inputs:
        return {
            "status": "error",
            "error_code": "E001",
            "message": ERROR_MESSAGES["E001"],
        }
    
    results = []
    error_count = 0
    
    for i, input_item in enumerate(inputs, 1):
        result = process_single_input(input_item, output_format)
        result["index"] = i
        if result["status"] == "error":
            error_count += 1
        results.append(result)
    
    return {
        "status": "success" if error_count == 0 else "partial",
        "total": len(inputs),
        "success_count": len(inputs) - error_count,
        "error_count": error_count,
        "results": results,
    }


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心功能。

    使用硬编码样例数据，不依赖外部文件或网络。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("=" * 50)
    print("angreal 自检开始")
    print("=" * 50)
    
    all_passed = True
    
    # 测试用例 1: JSON 输入解析
    print("\n[测试 1] JSON 输入解析")
    try:
        json_input = '{"name": "测试项目", "type": "task", "date": "2026-01-01"}'
        parsed = parse_input(json_input)
        assert parsed.get("name") == "测试项目", "JSON 解析失败"
        print("  ✓ JSON 解析正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 2: 纯文本输入解析
    print("\n[测试 2] 纯文本输入解析")
    try:
        text_input = "这是一个测试文本输入"
        parsed = parse_input(text_input)
        assert parsed.get("format") == "text", "文本格式识别失败"
        print("  ✓ 文本解析正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 3: 关键字段提取
    print("\n[测试 3] 关键字段提取")
    try:
        data = {"name": "测试", "type": "task", "amount": 100}
        extracted = extract_key_fields(data)
        assert "name" in extracted, "缺少 name 字段"
        assert "type" in extracted, "缺少 type 字段"
        assert "amount" in extracted, "缺少 amount 字段"
        assert "_confidence" in extracted, "缺少置信度"
        assert 0 <= extracted["_confidence"] <= 100, "置信度范围错误"
        print("  ✓ 字段提取正常")
        print(f"  ✓ 置信度: {extracted['_confidence']}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 4: 置信度分级
    print("\n[测试 4] 置信度分级")
    try:
        # 高置信度情况
        high_conf_data = {"name": "a", "type": "b", "date": "c", "amount": 1}
        high_conf = calculate_confidence(extract_key_fields(high_conf_data), high_conf_data)
        assert high_conf >= 85, f"高置信度期望 >=85，实际 {high_conf}"
        
        # 低置信度情况
        low_conf_data = {"unknown_field": "x"}
        low_conf = calculate_confidence(extract_key_fields(low_conf_data), low_conf_data)
        assert low_conf < 85, f"低置信度期望 <85，实际 {low_conf}"
        
        print(f"  ✓ 高置信度: {high_conf}")
        print(f"  ✓ 低置信度: {low_conf}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 5: 单输入处理
    print("\n[测试 5] 单输入处理")
    try:
        result = process_single_input('{"name": "测试项目"}')
        assert result["status"] == "success", "处理失败"
        assert "data" in result, "缺少 data 字段"
        assert "confidence_level" in result, "缺少置信度等级"
        print("  ✓ 单输入处理正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 6: 批量处理
    print("\n[测试 6] 批量处理")
    try:
        inputs = [
            '{"name": "项目1", "type": "task"}',
            '{"name": "项目2", "type": "bug"}',
            "简单的文本输入",
        ]
        result = batch_process(inputs)
        assert result["status"] == "success", "批量处理失败"
        assert result["total"] == 3, "总数错误"
        assert result["success_count"] == 3, "成功数错误"
        print("  ✓ 批量处理正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 7: 错误处理
    print("\n[测试 7] 错误处理")
    try:
        # 空输入
        result = process_single_input("")
        assert result["status"] == "error", "空输入应报错"
        assert result["error_code"] == "E001", "错误码应为 E001"
        
        # 不支持的格式
        try:
            format_output({}, "xml")
            assert False, "应抛出 E007 错误"
        except ValueError as e:
            assert str(e) == "E007", "错误码应为 E007"
        
        print("  ✓ 错误处理正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 8: 输出格式
    print("\n[测试 8] 输出格式")
    try:
        data = {"name": "测试", "value": 123}
        
        # JSON 格式
        json_output = format_output(data, "json")
        parsed_json = json.loads(json_output)
        assert parsed_json["name"] == "测试", "JSON 输出错误"
        
        # 文本格式
        text_output = format_output(data, "text")
        assert "name: 测试" in text_output, "文本输出错误"
        
        print("  ✓ 输出格式正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 汇总结果
    print("\n" + "=" * 50)
    if all_passed:
        print("自检通过：所有测试用例均正常")
    else:
        print("自检失败：存在未通过的测试用例")
    print("=" * 50)
    
    return all_passed


# ============================================================
# 主函数
# ============================================================

def main() -> int:
    """
    主入口函数。

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="angreal - 任务自动化与项目模板工具",
        epilog="示例: python main.py --input '{\"name\": \"测试\"}' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本或 JSON 格式）"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        nargs="+",
        help="批量输入多个内容"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=SUPPORTED_FORMATS,
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1
    
    # 批量处理模式
    if args.batch:
        result = batch_process(args.batch, args.format)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "success" else 1
    
    # 单输入模式
    if args.input:
        result = process_single_input(args.input, args.format)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "success" else 1
    
    # 无输入时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
