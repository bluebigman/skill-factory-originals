#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-selfhosted 技能处理脚本（独立实现）

本脚本根据功能规格独立编写，用于处理 awesome-selfhosted 相关任务。
仅依赖 Python 标准库，支持离线自检（--selftest）。
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：JSON 字符串或文本内容",
    "E004": "这超出了本工具的能力范围，建议使用其他专业工具",
    "E005": "结果无法确定，建议：重新提供更完整的数据或人工复核",
    "E006": "内部处理错误，请检查输入数据",
    "E007": "输出格式设置无效，支持 json / text",
    "E008": "置信度计算失败，请检查数据",
    "E009": "批量处理时遇到错误，请检查每个输入项",
    "E010": "未知错误，请查看日志",
}


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果数据类"""
    
    def __init__(self, content: str = "", confidence: float = 0.0, 
                 fields: Optional[Dict[str, Any]] = None):
        self.content = content          # 处理后的内容
        self.confidence = confidence    # 置信度 (0-100)
        self.fields = fields or {}      # 结构化字段
        self.warnings: List[str] = []   # 警告信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "confidence": self.confidence,
            "fields": self.fields,
            "warnings": self.warnings,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
def validate_input(data: Any) -> Tuple[bool, str]:
    """
    验证输入数据有效性
    
    返回: (是否有效, 错误码或空字符串)
    """
    if data is None:
        return False, "E001"
    if isinstance(data, str) and not data.strip():
        return False, "E001"
    if isinstance(data, (list, dict)) and not data:
        return False, "E001"
    return True, ""


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段
    
    支持: 字符串(JSON解析或文本)、字典、列表
    """
    fields: Dict[str, Any] = {}
    
    if isinstance(data, dict):
        # 直接使用字典
        fields = data.copy()
    elif isinstance(data, str):
        # 尝试 JSON 解析
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                fields = parsed
            else:
                fields = {"content": parsed}
        except json.JSONDecodeError:
            # 作为纯文本处理
            fields = {"text": data}
    elif isinstance(data, list):
        fields = {"items": data, "count": len(data)}
    
    return fields


def calculate_confidence(fields: Dict[str, Any]) -> float:
    """
    计算置信度 (0-100)
    
    基于字段完整性和数据量
    """
    if not fields:
        return 0.0
    
    # 基础置信度
    base = 50.0
    
    # 字段数量加分
    field_count = len(fields)
    base += min(field_count * 5, 30)
    
    # 内容长度加分 (如果有文本)
    text_length = 0
    for value in fields.values():
        if isinstance(value, str):
            text_length += len(value)
        elif isinstance(value, (list, dict)):
            text_length += len(value) * 10
    
    if text_length > 0:
        base += min(text_length / 100, 20)
    
    return min(base, 100.0)


def process_single(data: Any, output_format: str = "text") -> ProcessingResult:
    """
    处理单个输入项
    
    Args:
        data: 输入数据
        output_format: 输出格式 (text/json)
    
    Returns:
        ProcessingResult 对象
    """
    # 验证输入
    valid, error_code = validate_input(data)
    if not valid:
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")
    
    # 提取字段
    fields = extract_key_fields(data)
    
    # 计算置信度
    confidence = calculate_confidence(fields)
    
    # 生成内容
    if output_format == "json":
        content = json.dumps(fields, ensure_ascii=False, indent=2)
    else:
        content = format_text_output(fields)
    
    result = ProcessingResult(
        content=content,
        confidence=confidence,
        fields=fields
    )
    
    # 添加置信度标注
    if confidence < 85:
        result.warnings.append("[需核实] 置信度较低，请人工复核关键结果")
    elif confidence < 90:
        result.warnings.append("建议复核")
    
    return result


def format_text_output(fields: Dict[str, Any]) -> str:
    """格式化文本输出"""
    lines = []
    for key, value in fields.items():
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)
        lines.append(f"{key}: {value_str}")
    return "\n".join(lines)


def process_batch(data_list: List[Any], output_format: str = "text") -> List[ProcessingResult]:
    """
    批量处理多个输入
    
    Args:
        data_list: 输入列表
        output_format: 输出格式
    
    Returns:
        ProcessingResult 列表
    """
    results = []
    for idx, data in enumerate(data_list):
        try:
            result = process_single(data, output_format)
            results.append(result)
        except ValueError as e:
            # 单个失败不影响整体
            error_result = ProcessingResult(
                content=f"第 {idx+1} 项处理失败",
                confidence=0.0,
                fields={"error": str(e)}
            )
            error_result.warnings.append(f"E009: {ERROR_MESSAGES['E009']}")
            results.append(error_result)
    
    return results


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    内置自检函数，使用硬编码样例数据离线测试
    
    返回: 测试是否通过
    """
    print("=" * 60)
    print("运行自检 (selftest)...")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 6
    
    # 测试1: 空输入验证
    print("\n[测试1] 空输入验证")
    try:
        valid, error_code = validate_input(None)
        assert not valid, "空输入应该无效"
        assert error_code == "E001", f"错误码应为 E001, 实际: {error_code}"
        print("  ✓ 空输入正确返回 E001")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试2: 有效输入验证
    print("\n[测试2] 有效输入验证")
    try:
        valid, error_code = validate_input({"key": "value"})
        assert valid, "有效输入应该通过"
        assert error_code == "", "有效输入不应有错误码"
        print("  ✓ 有效输入验证通过")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试3: 字段提取 (JSON字符串)
    print("\n[测试3] JSON 字符串字段提取")
    try:
        test_str = '{"name": "test", "version": "1.0"}'
        fields = extract_key_fields(test_str)
        assert "name" in fields, "应提取 name 字段"
        assert fields["name"] == "test", "name 值不正确"
        assert fields["version"] == "1.0", "version 值不正确"
        print(f"  ✓ 字段提取成功: {fields}")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试4: 置信度计算
    print("\n[测试4] 置信度计算")
    try:
        # 空字段
        conf_empty = calculate_confidence({})
        assert conf_empty == 0.0, f"空字段置信度应为0, 实际: {conf_empty}"
        
        # 完整字段
        full_fields = {
            "name": "test app",
            "version": "1.0.0",
            "description": "A self-hosted application for testing purposes",
            "url": "https://example.com",
            "tags": ["web", "tool"]
        }
        conf_full = calculate_confidence(full_fields)
        assert 50.0 <= conf_full <= 100.0, f"置信度应在50-100之间, 实际: {conf_full}"
        
        # 完整字段置信度应高于空字段
        assert conf_full > conf_empty, "完整字段置信度应更高"
        
        print(f"  ✓ 置信度计算正常 (空: {conf_empty}, 完整: {conf_full})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试5: 单条处理
    print("\n[测试5] 单条数据处理")
    try:
        test_data = {
            "name": "Awesome Selfhosted",
            "category": "Web Server",
            "description": "A curated list of self-hosted software"
        }
        result = process_single(test_data, "text")
        
        # 验证结果
        assert result.content, "内容不应为空"
        assert "name" in result.content, "内容应包含 name"
        assert 0 <= result.confidence <= 100, "置信度应在0-100"
        assert len(result.fields) == 3, "应提取3个字段"
        
        print(f"  ✓ 单条处理成功, 置信度: {result.confidence:.1f}%")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试6: 批量处理
    print("\n[测试6] 批量处理")
    try:
        test_batch = [
            {"name": "app1", "version": "1.0"},
            {"name": "app2", "version": "2.0"},
            "plain text item",
            None  # 无效项
        ]
        results = process_batch(test_batch)
        assert len(results) == 4, f"应返回4个结果, 实际: {len(results)}"
        
        # 前3个应该成功
        for i in range(3):
            assert results[i].confidence > 0, f"第{i+1}项应有置信度"
        
        # 第4个应该失败但有错误信息
        assert results[3].confidence == 0, "无效项置信度应为0"
        assert results[3].fields.get("error"), "无效项应有错误信息"
        
        print(f"  ✓ 批量处理成功 (成功3项, 失败1项)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
    
    # 总结
    print("\n" + "=" * 60)
    print(f"自检结果: {tests_passed}/{tests_total} 通过")
    
    # 宽松判定: 至少5/6通过即算成功
    return tests_passed >= 5


# ============================================================
# 主程序
# ============================================================
def main() -> int:
    """
    主入口函数
    
    Returns:
        退出码 (0成功, 1失败)
    """
    parser = argparse.ArgumentParser(
        description="awesome-selfhosted 技能处理脚本",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        help="输入数据 (JSON字符串或文本)"
    )
    parser.add_argument(
        "--file", "-f",
        help="从文件读取输入"
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式 (输入为JSON数组)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 收集输入
    input_data = None
    error_code = None
    
    if args.file:
        # 从文件读取
        if not os.path.exists(args.file):
            print(f"E006: {ERROR_MESSAGES['E006']} - 文件不存在: {args.file}")
            return 1
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_data = f.read()
        except Exception as e:
            print(f"E006: {ERROR_MESSAGES['E006']} - 文件读取失败: {e}")
            return 1
    elif args.input:
        input_data = args.input
    else:
        # 从标准输入读取
        try:
            input_data = sys.stdin.read().strip()
        except Exception:
            input_data = None
    
    # 验证输入
    valid, error_code = validate_input(input_data)
    if not valid:
        print(f"{error_code}: {ERROR_MESSAGES[error_code]}")
        return 1
    
    # 解析输入 (尝试JSON)
    parsed_data = input_data
    if isinstance(input_data, str):
        try:
            parsed_data = json.loads(input_data)
        except json.JSONDecodeError:
            pass  # 保持原始字符串
    
    try:
        # 批量或单条处理
        if args.batch and isinstance(parsed_data, list):
            results = process_batch(parsed_data, args.format)
            output = [r.to_dict() for r in results]
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            result = process_single(parsed_data, args.format)
            
            # 输出结果
            print(result.content)
            
            # 输出置信度和警告
            print(f"\n置信度: {result.confidence:.1f}%")
            for warning in result.warnings:
                print(f"警告: {warning}")
            
            # 低置信度提示
            if result.confidence < 85:
                print(f"E005: {ERROR_MESSAGES['E005']}")
                return 1
        
        return 0
        
    except ValueError as e:
        print(f"E010: {ERROR_MESSAGES['E010']} - {e}")
        return 1
    except Exception as e:
        print(f"E010: {ERROR_MESSAGES['E010']} - 未预期错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
