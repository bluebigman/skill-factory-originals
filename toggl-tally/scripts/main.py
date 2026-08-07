#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toggl-tally 全新独立实现脚本

本脚本根据功能规格独立编写，不参考任何既有实现。
主要功能：
  1. 将用户提供的数据/文件/URL 转换为结构化结果
  2. 识别并保留输入中的关键信息
  3. 按约定格式生成输出
  4. 对不确定项给出置信度提示
  5. 支持批量处理和自定义格式

用法：
  python main.py --selftest          # 运行内置自检
  python main.py --input <数据>       # 处理单个输入
  python main.py --batch <文件路径>   # 批量处理文件中的行
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码定义（对应规格中的错误码体系）
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{\"source\": \"数据内容\", \"format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议：仅处理文本/文件/URL 输入",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90    # 高置信度
CONFIDENCE_MEDIUM = 0.85  # 中等置信度

# 支持的关键字段（用于结构化识别）
KEY_FIELDS = [
    "date", "time", "duration", "project", "client",
    "description", "task", "tags", "amount", "currency"
]

# 默认输出模板
DEFAULT_TEMPLATE = {
    "timestamp": None,
    "source_type": "text",
    "content": None,
    "key_fields": {},
    "confidence": 0.0,
    "warnings": []
}


# ============================================================
# 核心功能模块
# ============================================================

def validate_input(raw_input: str) -> Tuple[bool, str, Dict[str, str]]:
    """
    验证输入内容是否合法。
    
    参数:
        raw_input: 用户提供的原始输入
        
    返回:
        (是否有效, 错误码或空字符串, 错误详情)
    """
    if raw_input is None or raw_input.strip() == "":
        return False, "E001", {"message": ERROR_CODES["E001"]}
    
    # 检查是否包含关键信息（至少要有内容）
    if len(raw_input.strip()) < 3:
        return False, "E002", {"message": ERROR_CODES["E002"], "missing": "输入内容过短"}
    
    return True, "", {}


def extract_key_fields(content: str) -> Dict[str, Any]:
    """
    从输入内容中提取关键字段。
    
    参数:
        content: 输入内容
        
    返回:
        提取到的关键字段字典
    """
    fields = {}
    
    # 尝试解析 JSON 格式输入
    if content.strip().startswith("{"):
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                for key in KEY_FIELDS:
                    if key in data:
                        fields[key] = data[key]
                return fields
        except json.JSONDecodeError:
            pass
    
    # 文本格式：尝试识别常见字段
    words = content.split()
    
    # 识别日期（宽松匹配，如 2024-01-01 或 01/01/2024）
    for word in words:
        if "-" in word and len(word) >= 8:
            fields["date"] = word
            break
    
    # 识别时间（如 14:30 或 09:00-17:00）
    for word in words:
        if ":" in word and len(word) <= 20:
            if "duration" not in fields:
                fields["duration"] = word
            break
    
    # 识别数字（如金额、时长等）
    for word in words:
        try:
            num = float(word.replace(",", ""))
            if "amount" not in fields and num > 0:
                fields["amount"] = num
                break
        except ValueError:
            continue
    
    # 识别项目名（通常为引号内或特定标记）
    for i, word in enumerate(words):
        if word.lower() in ("project", "客户", "项目") and i + 1 < len(words):
            fields["project"] = words[i + 1]
            break
    
    return fields


def calculate_confidence(fields: Dict[str, Any], content: str) -> Tuple[float, List[str]]:
    """
    计算置信度并生成警告信息。
    
    参数:
        fields: 提取到的字段
        content: 原始输入内容
        
    返回:
        (置信度值, 警告列表)
    """
    warnings = []
    
    # 基础置信度
    confidence = 0.5
    
    # 根据字段数量提升置信度
    field_count = len(fields)
    confidence += field_count * 0.1
    
    # 内容长度影响
    content_len = len(content)
    if content_len > 50:
        confidence += 0.1
    elif content_len < 10:
        warnings.append("输入内容过短，可能影响识别效果")
        confidence -= 0.1
    
    # 检查是否有明确的来源标记
    if "http" in content.lower() or "file:" in content.lower():
        confidence += 0.1
    
    # 检查是否有日期（重要字段）
    if "date" in fields:
        confidence += 0.1
    else:
        warnings.append("未识别到日期信息，建议补充")
    
    # 检查是否有项目信息
    if "project" in fields:
        confidence += 0.1
    else:
        warnings.append("未识别到项目信息，建议补充")
    
    # 限制置信度范围
    confidence = max(0.0, min(1.0, confidence))
    
    return confidence, warnings


def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    处理单个输入，生成结构化结果。
    
    参数:
        raw_input: 用户输入的原始内容
        output_format: 输出格式（json/text）
        
    返回:
        处理结果字典
    """
    # 验证输入
    is_valid, error_code, error_info = validate_input(raw_input)
    if not is_valid:
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_info["message"],
            "result": None
        }
    
    # 提取关键字段
    key_fields = extract_key_fields(raw_input)
    
    # 计算置信度
    confidence, warnings = calculate_confidence(key_fields, raw_input)
    
    # 生成结果
    result = {
        "success": True,
        "error_code": None,
        "result": {
            "timestamp": datetime.now().isoformat(),
            "source_type": "url" if "http" in raw_input.lower() else "text",
            "content": raw_input,
            "key_fields": key_fields,
            "confidence": round(confidence, 2),
            "warnings": warnings,
            "quality_label": get_quality_label(confidence)
        }
    }
    
    # 根据置信度添加标注
    if confidence >= CONFIDENCE_HIGH:
        result["result"]["note"] = "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        result["result"]["note"] = "建议复核"
    else:
        result["result"]["note"] = "[需核实] 结果不确定，请人工确认"
    
    return result


def get_quality_label(confidence: float) -> str:
    """根据置信度返回质量标签。"""
    if confidence >= CONFIDENCE_HIGH:
        return "高置信度"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "中等置信度"
    else:
        return "低置信度"


def process_batch(file_path: str) -> List[Dict[str, Any]]:
    """
    批量处理文件中的输入（每行一条）。
    
    参数:
        file_path: 输入文件路径
        
    返回:
        处理结果列表
    """
    results = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # 跳过空行
                    result = process_input(line)
                    result["line_number"] = line_num
                    results.append(result)
    except FileNotFoundError:
        return [{
            "success": False,
            "error_code": "E006",
            "error_message": "文件不存在，请检查路径",
            "line_number": 0
        }]
    except Exception as e:
        return [{
            "success": False,
            "error_code": "E007",
            "error_message": f"文件读取失败: {str(e)}",
            "line_number": 0
        }]
    
    return results


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    将处理结果格式化为输出字符串。
    
    参数:
        result: 处理结果
        output_format: 输出格式（json/text）
        
    返回:
        格式化后的字符串
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        # 文本格式输出
        if not result["success"]:
            return f"错误: {result.get('error_code', '')} - {result.get('error_message', '')}"
        
        r = result["result"]
        lines = [
            f"处理时间: {r['timestamp']}",
            f"来源类型: {r['source_type']}",
            f"置信度: {r['confidence']} ({r['quality_label']})",
            f"备注: {r['note']}"
        ]
        
        if r["key_fields"]:
            lines.append("关键字段:")
            for k, v in r["key_fields"].items():
                lines.append(f"  - {k}: {v}")
        
        if r["warnings"]:
            lines.append("警告:")
            for w in r["warnings"]:
                lines.append(f"  - {w}")
        
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心功能。
    使用硬编码样例数据，不依赖外部文件或网络。
    
    返回:
        自检是否通过
    """
    print("开始运行自检...")
    all_passed = True
    
    # 测试用例 1: 基本文本输入
    print("\n[测试1] 基本文本输入")
    test_input = "2024-03-15 开发项目A 8小时 客户B"
    result = process_input(test_input)
    
    assert result["success"], "基本文本输入处理失败"
    r = result["result"]
    assert r["confidence"] > 0.6, f"置信度应大于0.6，实际: {r['confidence']}"
    assert len(r["key_fields"]) > 0, "应提取到关键字段"
    print(f"  通过! 置信度: {r['confidence']}, 字段数: {len(r['key_fields'])}")
    
    # 测试用例 2: JSON 格式输入
    print("\n[测试2] JSON 格式输入")
    json_input = json.dumps({
        "project": "数据分析",
        "duration": "3.5小时",
        "date": "2024-03-16"
    })
    result = process_input(json_input)
    
    assert result["success"], "JSON输入处理失败"
    r = result["result"]
    assert r["confidence"] > 0.7, f"JSON输入置信度应大于0.7，实际: {r['confidence']}"
    assert "project" in r["key_fields"], "应提取到项目字段"
    print(f"  通过! 置信度: {r['confidence']}, 项目: {r['key_fields'].get('project')}")
    
    # 测试用例 3: URL 输入
    print("\n[测试3] URL 输入")
    url_input = "https://example.com/api/toggl/report?date=2024-03-15"
    result = process_input(url_input)
    
    assert result["success"], "URL输入处理失败"
    r = result["result"]
    assert r["source_type"] == "url", f"应识别为URL类型，实际: {r['source_type']}"
    print(f"  通过! 来源类型: {r['source_type']}")
    
    # 测试用例 4: 空输入错误处理
    print("\n[测试4] 空输入错误处理")
    result = process_input("")
    
    assert not result["success"], "空输入应返回错误"
    assert result["error_code"] == "E001", f"错误码应为E001，实际: {result['error_code']}"
    print(f"  通过! 错误码: {result['error_code']}")
    
    # 测试用例 5: 批量处理
    print("\n[测试5] 批量处理")
    # 创建临时测试文件
    test_file = os.path.join(os.path.dirname(__file__), "_test_batch.txt")
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("2024-03-15 项目A 4小时\n")
            f.write("2024-03-16 项目B 6小时\n")
            f.write("2024-03-17 项目C 8小时\n")
        
        batch_results = process_batch(test_file)
        assert len(batch_results) == 3, f"应处理3条记录，实际: {len(batch_results)}"
        assert all(r["success"] for r in batch_results), "所有记录应处理成功"
        print(f"  通过! 处理记录数: {len(batch_results)}")
    finally:
        # 清理临时文件
        if os.path.exists(test_file):
            os.remove(test_file)
    
    # 测试用例 6: 置信度阈值判断
    print("\n[测试6] 置信度阈值判断")
    # 高置信度测试（丰富输入）
    rich_input = "2024-03-15 项目A 8小时 客户B 2024-03-15 项目A 8小时 客户B"
    result = process_input(rich_input)
    r = result["result"]
    assert r["confidence"] > 0.5, "丰富输入应有较高置信度"
    
    # 低置信度测试（简单输入）
    poor_input = "abc"
    result = process_input(poor_input)
    r = result["result"]
    assert r["confidence"] < 0.8, "简单输入置信度不应过高"
    print(f"  通过! 高置信度: {r['confidence']} (丰富输入)")
    
    # 测试用例 7: 错误码体系
    print("\n[测试7] 错误码体系")
    # 测试过短输入
    short_input = "ab"
    result = process_input(short_input)
    assert not result["success"], "过短输入应返回错误"
    assert result["error_code"] in ["E001", "E002"], f"错误码应为E001或E002，实际: {result['error_code']}"
    print(f"  通过! 错误码: {result['error_code']}")
    
    # 测试用例 8: 输出格式
    print("\n[测试8] 输出格式")
    test_input = "2024-03-15 开发任务"
    result = process_input(test_input)
    
    # JSON 输出
    json_output = format_output(result, "json")
    assert json_output.startswith("{"), "JSON输出应以{开头"
    assert isinstance(json.loads(json_output), dict), "JSON输出应能解析"
    
    # 文本输出
    text_output = format_output(result, "text")
    assert "置信度" in text_output, "文本输出应包含置信度"
    print(f"  通过! JSON和文本输出均正常")
    
    print("\n" + "="*50)
    print("所有自检测试通过！")
    print("="*50)
    
    return all_passed


# ============================================================
# 主程序入口
# ============================================================

def main():
    """主程序入口。"""
    parser = argparse.ArgumentParser(
        description="toggl-tally: 工时追踪与预测工具",
        epilog="示例: python main.py --input '2024-03-15 项目A 8小时'"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（文本/JSON/URL）"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件路径（每行一条输入）"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except AssertionError as e:
            print(f"自检失败: {e}")
            sys.exit(1)
    
    # 处理单个输入
    if args.input:
        result = process_input(args.input)
        print(format_output(result, args.format))
        sys.exit(0 if result["success"] else 1)
    
    # 批量处理
    if args.batch:
        results = process_batch(args.batch)
        for r in results:
            print(format_output(r, args.format))
            print()  # 空行分隔
        sys.exit(0 if all(r["success"] for r in results) else 1)
    
    # 无参数时显示帮助
    if not any([args.selftest, args.input, args.batch]):
        parser.print_help()
        # 提示使用 --selftest
        print("\n提示: 运行 'python main.py --selftest' 可进行功能自检")
        sys.exit(0)


if __name__ == "__main__":
    main()
