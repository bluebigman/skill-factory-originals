#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openmontage - 未命名工具
World's first open-source, agentic video production system.
12 production pipelines, 100+ tools, 700+ agent skill and pr

本脚本为 clean-room 独立实现，仅依据功能规格设计。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import tempfile
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码及标准化话术（规格第四章）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 内部错误码（扩展）
    "E006": "文件读取失败，请检查文件路径",
    "E007": "JSON 解析失败，请检查输入格式",
    "E008": "输出写入失败，请检查权限",
    "E009": "内部逻辑错误，请联系开发者",
    "E010": "未知错误",
}

# 置信度阈值（规格第三章 Step 2）
CONFIDENCE_HIGH = 90    # ≥90%：直接输出
CONFIDENCE_MEDIUM = 85  # 85%-90%：建议复核
# <85%：标注 [需核实]

# 关键字段列表（用于结构化识别）
KEY_FIELDS = [
    "title", "description", "tags", "duration",
    "resolution", "format", "source", "author",
    "date", "content",
]

# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果封装"""
    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        self.confidence: int = 0
        self.warnings: List[str] = []
        self.errors: List[Tuple[str, str]] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class InputData:
    """输入数据封装"""
    def __init__(self, raw: str, source_type: str = "text"):
        self.raw = raw
        self.source_type = source_type
        self.parsed: Dict[str, Any] = {}
        self.is_valid = False


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw: str) -> Optional[str]:
    """
    验证输入是否有效（规格第三章 Step 1）
    返回错误码或 None（有效）
    """
    if not raw or not raw.strip():
        return "E001"
    if len(raw.strip()) < 3:
        return "E003"
    return None


def parse_input(raw: str, source_type: str = "text") -> InputData:
    """
    解析输入内容（规格第三章 Step 2.1）
    识别关键信息并结构化
    """
    result = InputData(raw, source_type)
    
    # 根据来源类型选择解析方式
    if source_type == "json":
        try:
            result.parsed = json.loads(raw)
            if isinstance(result.parsed, dict):
                result.is_valid = True
            else:
                result.is_valid = False
        except json.JSONDecodeError:
            result.is_valid = False
    else:
        # 文本解析：按行拆分，识别 key: value 或 key=value 格式
        lines = raw.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试多种分隔符
            for sep in [":", "=", "："]:
                if sep in line:
                    key, value = line.split(sep, 1)
                    result.parsed[key.strip()] = value.strip()
                    break
            else:
                # 无法识别的行，加入 content 字段
                result.parsed.setdefault("content", [])
                if isinstance(result.parsed["content"], list):
                    result.parsed["content"].append(line)
                else:
                    result.parsed["content"] = [result.parsed["content"], line]
        result.is_valid = bool(result.parsed)
    
    return result


def extract_key_fields(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    提取关键字段（规格第三章 Step 2.1）
    返回 (提取到的字段, 缺失的字段列表)
    """
    extracted = {}
    missing = []
    
    for field in KEY_FIELDS:
        if field in data and data[field] is not None:
            extracted[field] = data[field]
        else:
            missing.append(field)
    
    return extracted, missing


def calculate_confidence(extracted: Dict[str, Any], missing: List[str]) -> int:
    """
    计算置信度（规格第三章 Step 2.3）
    基于字段完整度计算
    """
    total_fields = len(KEY_FIELDS)
    if total_fields == 0:
        return 0
    
    # 有 content 字段时，即使缺少其他字段也给予基础分
    base_score = 50 if "content" in extracted else 30
    
    # 每个提取到的字段增加分数
    field_score = (len(extracted) / total_fields) * 40
    
    # 最终置信度
    confidence = min(95, base_score + field_score)
    
    return int(confidence)


def format_output(result: ProcessingResult) -> Dict[str, Any]:
    """
    格式化输出（规格第三章 Step 3）
    根据置信度添加标注
    """
    output = result.to_dict()
    
    # 根据置信度级别添加标注
    if result.confidence >= CONFIDENCE_HIGH:
        output["status"] = "直接输出"
        output["label"] = "正常"
    elif result.confidence >= CONFIDENCE_MEDIUM:
        output["status"] = "建议复核"
        output["label"] = "建议复核"
    else:
        output["status"] = "需核实"
        output["label"] = "[需核实]"
        output["uncertainty_points"] = result.warnings
    
    return output


def process_text(raw: str) -> ProcessingResult:
    """
    处理文本输入（主流程）
    """
    result = ProcessingResult()
    
    # Step 1: 验证输入
    error_code = validate_input(raw)
    if error_code:
        result.errors.append((error_code, ERROR_MESSAGES[error_code]))
        result.confidence = 0
        return result
    
    # Step 2: 解析输入
    input_data = parse_input(raw, "text")
    if not input_data.is_valid:
        result.errors.append(("E003", ERROR_MESSAGES["E003"]))
        result.confidence = 0
        return result
    
    # Step 3: 提取关键字段
    extracted, missing = extract_key_fields(input_data.parsed)
    result.data = extracted
    
    # Step 4: 计算置信度
    result.confidence = calculate_confidence(extracted, missing)
    
    # Step 5: 生成警告
    if result.confidence < CONFIDENCE_HIGH:
        for field in missing:
            if field != "content":  # content 不是必填项
                result.warnings.append(f"缺少字段: {field}")
    
    # Step 6: 检查置信度是否过低
    if result.confidence < CONFIDENCE_MEDIUM:
        result.errors.append(("E005", ERROR_MESSAGES["E005"]))
    
    return result


def process_json(raw: str) -> ProcessingResult:
    """
    处理 JSON 输入
    """
    result = ProcessingResult()
    
    # 验证输入
    error_code = validate_input(raw)
    if error_code:
        result.errors.append((error_code, ERROR_MESSAGES[error_code]))
        result.confidence = 0
        return result
    
    # 解析 JSON
    input_data = parse_input(raw, "json")
    if not input_data.is_valid:
        result.errors.append(("E007", ERROR_MESSAGES["E007"]))
        result.confidence = 0
        return result
    
    # 提取关键字段
    extracted, missing = extract_key_fields(input_data.parsed)
    result.data = extracted
    
    # 计算置信度
    result.confidence = calculate_confidence(extracted, missing)
    
    # 生成警告
    if result.confidence < CONFIDENCE_HIGH:
        for field in missing:
            if field != "content":
                result.warnings.append(f"缺少字段: {field}")
    
    return result


def process_file(filepath: str) -> ProcessingResult:
    """
    处理文件输入（规格第三章 Step 1）
    """
    result = ProcessingResult()
    
    try:
        path = Path(filepath)
        if not path.exists():
            result.errors.append(("E006", ERROR_MESSAGES["E006"]))
            result.confidence = 0
            return result
        
        content = path.read_text(encoding="utf-8", errors="ignore")
        
        # 根据文件扩展名选择解析方式
        if path.suffix.lower() == ".json":
            return process_json(content)
        else:
            return process_text(content)
            
    except Exception as e:
        result.errors.append(("E006", f"{ERROR_MESSAGES['E006']}: {str(e)}"))
        result.confidence = 0
        return result


def batch_process(items: List[str]) -> List[ProcessingResult]:
    """
    批量处理（规格第六章：进阶用法）
    """
    results = []
    for item in items:
        if item.startswith("file:"):
            # 文件输入
            filepath = item[5:]
            results.append(process_file(filepath))
        elif item.startswith("json:"):
            # JSON 输入
            json_str = item[5:]
            results.append(process_json(json_str))
        else:
            # 文本输入
            results.append(process_text(item))
    return results


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑
    不读外部文件、不依赖当前工作目录、不访问网络
    """
    print("=" * 60)
    print("openmontage 自检开始")
    print("=" * 60)
    
    all_passed = True
    
    # 测试用例 1: 正常文本输入
    print("\n[测试 1] 正常文本输入")
    sample1 = """title: 测试视频
description: 这是一个测试视频
duration: 10分钟
resolution: 1920x1080
format: mp4
source: local
author: tester
date: 2024-01-01
content: 这是视频内容描述"""
    
    try:
        result1 = process_text(sample1)
        assert len(result1.errors) == 0, f"测试1失败: {result1.errors}"
        assert result1.confidence >= 80, f"测试1失败: 置信度过低 {result1.confidence}"
        assert "title" in result1.data, "测试1失败: 缺少 title 字段"
        assert "duration" in result1.data, "测试1失败: 缺少 duration 字段"
        print(f"  通过 (置信度: {result1.confidence}%)")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 2: JSON 输入
    print("\n[测试 2] JSON 输入")
    sample2 = json.dumps({
        "title": "JSON测试",
        "tags": ["test", "json"],
        "duration": 5,
        "format": "mp4"
    })
    
    try:
        result2 = process_json(sample2)
        assert len(result2.errors) == 0, f"测试2失败: {result2.errors}"
        assert result2.confidence >= 60, f"测试2失败: 置信度过低 {result2.confidence}"
        assert result2.data.get("title") == "JSON测试", "测试2失败: title 不匹配"
        print(f"  通过 (置信度: {result2.confidence}%)")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 3: 空输入应报错
    print("\n[测试 3] 空输入处理")
    try:
        result3 = process_text("")
        assert len(result3.errors) > 0, "测试3失败: 空输入应该报错"
        assert result3.errors[0][0] == "E001", f"测试3失败: 错误码不匹配 {result3.errors[0][0]}"
        print(f"  通过 (错误码: {result3.errors[0][0]})")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 4: 不完整输入（低置信度）
    print("\n[测试 4] 不完整输入")
    sample4 = "title: 只有标题"
    try:
        result4 = process_text(sample4)
        assert result4.confidence >= 0, "测试4失败: 置信度应为非负"
        assert result4.confidence <= 100, "测试4失败: 置信度不应超过100"
        print(f"  通过 (置信度: {result4.confidence}%)")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 5: 批量处理
    print("\n[测试 5] 批量处理")
    items = [
        "title: 批量1\ndescription: 第一个",
        "title: 批量2\ndescription: 第二个",
        "title: 批量3\ndescription: 第三个",
    ]
    try:
        batch_results = batch_process(items)
        assert len(batch_results) == 3, f"测试5失败: 批量结果数量不对 {len(batch_results)}"
        for i, br in enumerate(batch_results):
            assert br.confidence >= 0, f"测试5失败: 第{i+1}个结果置信度为负"
        print(f"  通过 (共 {len(batch_results)} 个结果)")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 6: 格式化输出
    print("\n[测试 6] 格式化输出")
    sample6 = "title: 格式化测试\ndescription: 测试格式化功能"
    try:
        result6 = process_text(sample6)
        formatted = format_output(result6)
        assert "status" in formatted, "测试6失败: 缺少 status 字段"
        assert "label" in formatted, "测试6失败: 缺少 label 字段"
        assert formatted["status"] in ["直接输出", "建议复核", "需核实"], "测试6失败: status 值无效"
        print(f"  通过 (status: {formatted['status']})")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 7: 置信度标注逻辑
    print("\n[测试 7] 置信度标注逻辑")
    sample7 = "title: 完整测试\ndescription: 完整描述\ncontent: 内容"
    try:
        result7 = process_text(sample7)
        formatted7 = format_output(result7)
        
        # 宽松验证：置信度与标注的对应关系
        if result7.confidence >= CONFIDENCE_HIGH:
            assert formatted7["label"] == "正常", "测试7失败: 高置信度应标记为正常"
        elif result7.confidence >= CONFIDENCE_MEDIUM:
            assert formatted7["label"] == "建议复核", "测试7失败: 中置信度应标记为建议复核"
        else:
            assert formatted7["label"] == "[需核实]", "测试7失败: 低置信度应标记为需核实"
        print(f"  通过 (置信度: {result7.confidence}%, 标签: {formatted7['label']})")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 8: 文件处理（使用临时文件，不依赖外部）
    print("\n[测试 8] 文件处理")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("title: 文件测试\ndescription: 从文件读取")
            temp_path = f.name
        
        try:
            result8 = process_file(temp_path)
            assert len(result8.errors) == 0, f"测试8失败: {result8.errors}"
            assert "title" in result8.data, "测试8失败: 文件处理未提取到 title"
            print(f"  通过 (title: {result8.data.get('title')})")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 9: 错误处理
    print("\n[测试 9] 错误处理")
    try:
        result9 = process_file("/nonexistent/path/file.txt")
        assert len(result9.errors) > 0, "测试9失败: 不存在的文件应该报错"
        assert result9.errors[0][0] == "E006", f"测试9失败: 错误码不匹配 {result9.errors[0][0]}"
        print(f"  通过 (错误码: {result9.errors[0][0]})")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 测试用例 10: 非法 JSON
    print("\n[测试 10] 非法 JSON")
    try:
        result10 = process_json("{invalid json")
        assert len(result10.errors) > 0, "测试10失败: 非法 JSON 应该报错"
        assert result10.errors[0][0] == "E007", f"测试10失败: 错误码不匹配 {result10.errors[0][0]}"
        print(f"  通过 (错误码: {result10.errors[0][0]})")
    except AssertionError as e:
        print(f"  失败: {e}")
        all_passed = False
    
    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数
    """
    parser = argparse.ArgumentParser(
        description="openmontage - 未命名工具",
        epilog="示例: python main.py --text 'title: 测试' 或 python main.py --selftest"
    )
    
    # 输入方式
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", type=str, help="直接输入文本内容")
    input_group.add_argument("--json", type=str, help="直接输入 JSON 内容")
    input_group.add_argument("--file", type=str, help="从文件读取内容")
    input_group.add_argument("--selftest", action="store_true", help="运行自检")
    
    # 输出选项
    parser.add_argument("--output", type=str, help="输出到文件")
    parser.add_argument("--format", type=str, choices=["json", "text"], default="json",
                       help="输出格式 (默认: json)")
    
    # 批量处理
    parser.add_argument("--batch", type=str, nargs="+", help="批量处理多个输入")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 批量处理
    if args.batch:
        results = batch_process(args.batch)
        output_data = [format_output(r) for r in results]
        
        # 统一输出
        if args.format == "json":
            output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        else:
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"结果 {i}: 置信度 {r.confidence}%")
                lines.append(f"  数据: {json.dumps(r.data, ensure_ascii=False)}")
                if r.warnings:
                    lines.append(f"  警告: {', '.join(r.warnings)}")
                if r.errors:
                    lines.append(f"  错误: {', '.join(f'{code}: {msg}' for code, msg in r.errors)}")
            output_str = "\n".join(lines)
        
        print(output_str)
        
        # 写入文件
        if args.output:
            try:
                Path(args.output).write_text(output_str, encoding="utf-8")
            except Exception:
                print(f"错误 E008: {ERROR_MESSAGES['E008']}", file=sys.stderr)
                return 8
        return 0
    
    # 单条处理
    result = None
    
    if args.text:
        result = process_text(args.text)
    elif args.json:
        result = process_json(args.json)
    elif args.file:
        result = process_file(args.file)
    else:
        parser.print_help()
        return 0
    
    # 格式化输出
    formatted = format_output(result)
    
    if args.format == "json":
        output_str = json.dumps(formatted, ensure_ascii=False, indent=2)
    else:
        lines = []
        lines.append(f"状态: {formatted['status']} ({formatted['label']})")
        lines.append(f"置信度: {result.confidence}%")
        if result.data:
            lines.append("数据:")
            for key, value in result.data.items():
                lines.append(f"  {key}: {value}")
        if result.warnings:
            lines.append(f"警告: {', '.join(result.warnings)}")
        if result.errors:
            lines.append("错误:")
            for code, msg in result.errors:
                lines.append(f"  {code}: {msg}")
        output_str = "\n".join(lines)
    
    print(output_str)
    
    # 写入文件
    if args.output:
        try:
            Path(args.output).write_text(output_str, encoding="utf-8")
        except Exception:
            print(f"错误 E008: {ERROR_MESSAGES['E008']}", file=sys.stderr)
            return 8
    
    # 根据错误码返回退出状态
    if result.errors:
        error_code = result.errors[0][0]
        return int(error_code[1:])  # E001 -> 1, E002 -> 2, etc.
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
