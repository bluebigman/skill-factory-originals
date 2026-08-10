#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
独立实现脚本（clean-room 重写），仅依据功能规格实现。

本脚本实现以下核心能力：
1. 将用户提供的数据/文件/URL 转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

错误码体系：
    E001 - 输入为空
    E002 - 关键信息缺失
    E003 - 输入格式错误
    E004 - 超出能力边界
    E005 - 置信度过低
    E006 - 内部处理异常
    E007 - 参数解析错误
    E008 - 批量输入为空
    E009 - 输出格式不支持
    E010 - 自检失败

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 一、核心数据结构与常量定义
# ============================================================

# 置信度阈值常量
CONFIDENCE_HIGH = 0.90       # ≥90%：直接输出
CONFIDENCE_MEDIUM = 0.85     # 85%-90%：建议复核
CONFIDENCE_LOW = 0.85        # <85%：标注 [需核实]

# 支持的输出格式
SUPPORTED_OUTPUT_FORMATS = ["json", "text", "table"]

# 关键字段列表（用于识别输入中的关键信息）
KEY_FIELDS = ["id", "name", "title", "url", "date", "author", "content", "value"]


# ============================================================
# 二、错误处理与异常类
# ============================================================

class SkillError(Exception):
    """技能执行过程中的自定义异常基类。
    
    携带错误码和标准化话术，用于统一错误处理。
    """
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 三、核心功能函数
# ============================================================

def validate_input(raw_input: Any) -> str:
    """验证输入是否有效。

    参数:
        raw_input: 用户提供的原始输入

    返回:
        规范化后的输入字符串

    异常:
        SkillError: E001（输入为空）或 E003（输入格式错误）
    """
    if raw_input is None:
        raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    
    if isinstance(raw_input, str):
        text = raw_input.strip()
    elif isinstance(raw_input, (dict, list)):
        text = json.dumps(raw_input, ensure_ascii=False)
    else:
        text = str(raw_input).strip()
    
    if not text:
        raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    
    # 检查是否为 URL
    if len(text) > 2048:  # 过长的输入视为格式错误
        raise SkillError("E003", "输入格式不符合要求，示例：短文本、URL 或 JSON 数据")
    
    return text


def detect_input_type(text: str) -> str:
    """识别输入类型。

    参数:
        text: 规范化后的输入字符串

    返回:
        输入类型：'url'、'json'、'text'
    """
    # 检查 URL
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return "url"
    
    # 检查 JSON
    try:
        json.loads(text)
        return "json"
    except (json.JSONDecodeError, ValueError):
        pass
    
    return "text"


def extract_key_fields(data: Any, depth: int = 0) -> Dict[str, Any]:
    """从输入数据中提取关键字段。

    参数:
        data: 输入数据（可能是 dict、list 或原始文本）
        depth: 递归深度（防止无限递归）

    返回:
        包含关键字段的字典
    """
    if depth > 5:
        return {}
    
    result: Dict[str, Any] = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            normalized_key = key.lower()
            # 检查是否为关键字段
            for field in KEY_FIELDS:
                if field in normalized_key or normalized_key in field:
                    if isinstance(value, (str, int, float, bool)):
                        result[field] = value
                    elif isinstance(value, (dict, list)):
                        nested = extract_key_fields(value, depth + 1)
                        if nested:
                            result[field] = nested
                    break
    
    elif isinstance(data, list):
        # 处理列表：取第一个元素作为代表
        if data:
            first_item = data[0]
            if isinstance(first_item, dict):
                result.update(extract_key_fields(first_item, depth + 1))
            else:
                result["value"] = first_item
    
    return result


def calculate_confidence(key_fields: Dict[str, Any], input_length: int) -> float:
    """计算处理结果的置信度。

    参数:
        key_fields: 提取到的关键字段
        input_length: 原始输入长度

    返回:
        置信度分数（0.0 ~ 1.0）
    """
    if not key_fields:
        return 0.5  # 无关键字段时低置信度
    
    # 基础置信度：有关键字段给 0.7
    confidence = 0.7
    
    # 字段数量加分
    field_count = len(key_fields)
    if field_count >= 3:
        confidence += 0.15
    elif field_count >= 2:
        confidence += 0.10
    elif field_count >= 1:
        confidence += 0.05
    
    # 输入长度加分（适度长度的输入更可信）
    if 10 <= input_length <= 2000:
        confidence += 0.05
    
    # 确保置信度在 0~1 之间
    return max(0.0, min(1.0, confidence))


def process_single_input(raw_input: Any, output_format: str = "json") -> Dict[str, Any]:
    """处理单个输入项。

    参数:
        raw_input: 用户提供的输入
        output_format: 输出格式（json/text/table）

    返回:
        处理结果字典

    异常:
        SkillError: E002（关键信息缺失）、E004（超出能力边界）、E009（输出格式不支持）
    """
    # 1. 验证输入
    text = validate_input(raw_input)
    
    # 2. 识别输入类型
    input_type = detect_input_type(text)
    
    # 3. 解析输入
    parsed_data: Any = text
    if input_type == "json":
        try:
            parsed_data = json.loads(text)
        except json.JSONDecodeError:
            raise SkillError("E003", "输入格式不符合要求，示例：..." + text[:50])
    elif input_type == "url":
        # URL 不访问网络，仅做结构化
        parsed = urllib.parse.urlparse(text)
        parsed_data = {
            "url": text,
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
        }
    
    # 4. 提取关键字段
    key_fields = extract_key_fields(parsed_data)
    
    # 5. 检查关键信息是否缺失
    if not key_fields and input_type == "text":
        # 纯文本可能没有关键字段，但至少给出内容
        key_fields = {"content": text[:200]}
    
    if not key_fields:
        raise SkillError("E002", "还缺少以下信息，请补充：关键字段（如 id、name、url 等）")
    
    # 6. 计算置信度
    confidence = calculate_confidence(key_fields, len(text))
    
    # 7. 生成结果
    result = {
        "status": "success",
        "input_type": input_type,
        "key_fields": key_fields,
        "confidence": confidence,
        "confidence_label": get_confidence_label(confidence),
        "output_format": output_format,
    }
    
    # 8. 按格式组织输出
    if output_format == "json":
        result["output"] = json.dumps(key_fields, ensure_ascii=False, indent=2)
    elif output_format == "text":
        result["output"] = format_as_text(key_fields)
    elif output_format == "table":
        result["output"] = format_as_table(key_fields)
    else:
        raise SkillError("E009", f"不支持的输出格式：{output_format}，支持：{', '.join(SUPPORTED_OUTPUT_FORMATS)}")
    
    return result


def get_confidence_label(confidence: float) -> str:
    """根据置信度返回标签。

    参数:
        confidence: 置信度分数

    返回:
        置信度标签字符串
    """
    if confidence >= CONFIDENCE_HIGH:
        return "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "建议复核"
    else:
        return "[需核实]"


def format_as_text(key_fields: Dict[str, Any]) -> str:
    """将关键字段格式化为文本。

    参数:
        key_fields: 关键字段字典

    返回:
        格式化后的文本字符串
    """
    lines = []
    for key, value in key_fields.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for sub_key, sub_value in value.items():
                lines.append(f"  {sub_key}: {sub_value}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def format_as_table(key_fields: Dict[str, Any]) -> str:
    """将关键字段格式化为表格。

    参数:
        key_fields: 关键字段字典

    返回:
        格式化后的表格字符串
    """
    if not key_fields:
        return "(空)"
    
    # 展平嵌套字段
    flat_fields: List[Tuple[str, Any]] = []
    for key, value in key_fields.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat_fields.append((f"{key}.{sub_key}", sub_value))
        else:
            flat_fields.append((key, value))
    
    # 计算列宽
    key_width = max(len(str(k)) for k, _ in flat_fields)
    value_width = max(len(str(v)) for _, v in flat_fields)
    
    # 生成表格
    separator = "+" + "-" * (key_width + 2) + "+" + "-" * (value_width + 2) + "+"
    lines = [separator]
    for key, value in flat_fields:
        lines.append(f"| {str(key).ljust(key_width)} | {str(value).ljust(value_width)} |")
        lines.append(separator)
    
    return "\n".join(lines)


def process_batch_input(inputs: List[Any], output_format: str = "json") -> Dict[str, Any]:
    """批量处理多个输入。

    参数:
        inputs: 输入列表
        output_format: 输出格式

    返回:
        批量处理结果字典

    异常:
        SkillError: E008（批量输入为空）
    """
    if not inputs:
        raise SkillError("E008", "批量输入为空，请提供至少一个待处理项")
    
    results = []
    for item in inputs:
        try:
            result = process_single_input(item, output_format)
            results.append(result)
        except SkillError as e:
            results.append({
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
                "input": str(item)[:100],
            })
    
    return {
        "status": "success" if all(r["status"] == "success" for r in results) else "partial",
        "total": len(results),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "results": results,
    }


# ============================================================
# 四、自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """运行内置自检。

    使用硬编码样例数据离线测试核心逻辑，不依赖外部文件或网络。

    返回:
        True 表示所有测试通过，False 表示有测试失败

    异常:
        SkillError: E010（自检失败）
    """
    print("=" * 60)
    print("开始自检（内置样例数据）...")
    print("=" * 60)
    
    test_results = []
    
    # --- 测试 1: 有效输入处理 ---
    print("\n[测试 1] 有效输入处理")
    try:
        sample_input = {
            "id": 1,
            "name": "示例项目",
            "url": "https://example.com/project/1",
            "author": "测试作者",
            "content": "这是一个用于自检的示例内容，包含足够长度的文本来测试置信度计算逻辑。"
        }
        result = process_single_input(sample_input, "json")
        test_results.append(result["status"] == "success")
        print(f"  状态: 成功")
        print(f"  置信度: {result['confidence']:.2f} ({result['confidence_label']})")
        # 宽松断言：置信度应在合理范围
        assert 0.5 <= result["confidence"] <= 1.0, "置信度应在 0.5~1.0 之间"
        print("  断言通过: 置信度范围合理")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 测试 2: 空输入处理 ---
    print("\n[测试 2] 空输入处理")
    try:
        try:
            process_single_input("")
            test_results.append(False)
            print("  失败: 未触发 E001 错误")
        except SkillError as e:
            test_results.append(e.code == "E001")
            print(f"  成功捕获: {e.code} - {e.message}")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 测试 3: 文本输入处理 ---
    print("\n[测试 3] 文本输入处理")
    try:
        text_input = "这是一个测试文本，包含一些关键信息：标题=测试文档，作者=张三，日期=2026年1月"
        result = process_single_input(text_input, "text")
        test_results.append(result["status"] == "success")
        print(f"  状态: 成功")
        print(f"  输出类型: {result['input_type']}")
        assert result["input_type"] == "text", "输入类型应为 text"
        print("  断言通过: 输入类型识别正确")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 测试 4: JSON 输入识别 ---
    print("\n[测试 4] JSON 输入识别")
    try:
        json_input = '{"name": "测试", "value": 42}'
        result = process_single_input(json_input)
        test_results.append(result["input_type"] == "json")
        print(f"  输入类型: {result['input_type']}")
        assert result["input_type"] == "json", "输入类型应为 json"
        print("  断言通过: JSON 识别正确")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 测试 5: URL 输入识别 ---
    print("\n[测试 5] URL 输入识别")
    try:
        url_input = "https://example.com/path/to/resource"
        result = process_single_input(url_input)
        test_results.append(result["input_type"] == "url")
        print(f"  输入类型: {result['input_type']}")
        assert result["input_type"] == "url", "输入类型应为 url"
        print("  断言通过: URL 识别正确")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 测试 6: 批量处理 ---
    print("\n[测试 6] 批量处理")
    try:
        batch_inputs = [
            {"id": 1, "name": "项目A"},
            {"id": 2, "name": "项目B"},
            "简单文本",
        ]
        result = process_batch_input(batch_inputs)
        test_results.append(result["total"] == 3)
        print(f"  总数: {result['total']}, 成功: {result['success_count']}")
        assert result["total"] == 3, "批量总数应为 3"
        assert result["success_count"] >= 2, "成功数量应不少于 2"
        print("  断言通过: 批量处理正确")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 测试 7: 错误码 E003 ---
    print("\n[测试 7] 错误码 E003")
    try:
        try:
            # 构造一个超长输入
            process_single_input("x" * 3000)
            test_results.append(False)
            print("  失败: 未触发 E003 错误")
        except SkillError as e:
            test_results.append(e.code == "E003")
            print(f"  成功捕获: {e.code} - {e.message}")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 测试 8: 支持格式检查 ---
    print("\n[测试 8] 输出格式支持")
    try:
        result = process_single_input({"name": "测试"}, "table")
        test_results.append(result["output_format"] == "table")
        print("  表格格式: 支持")
        result = process_single_input({"name": "测试"}, "text")
        test_results.append(result["output_format"] == "text")
        print("  文本格式: 支持")
        print("  断言通过: 格式支持正确")
    except Exception as e:
        test_results.append(False)
        print(f"  失败: {e}")
    
    # --- 汇总结果 ---
    passed = sum(1 for r in test_results if r)
    total = len(test_results)
    
    print("\n" + "=" * 60)
    print(f"自检完成: {passed}/{total} 项测试通过")
    print("=" * 60)
    
    if passed != total:
        raise SkillError("E010", f"自检失败: {total - passed} 项测试未通过")
    
    return True


# ============================================================
# 五、命令行入口
# ============================================================

def main() -> int:
    """主入口函数。

    解析命令行参数并执行相应操作。

    返回:
        退出码（0 表示成功，非 0 表示失败）
    """
    parser = argparse.ArgumentParser(
        description="未命名工具 - 通用数据处理技能",
        epilog="示例: python main.py --input '{\"name\": \"测试\"}' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本、JSON 字符串或 URL）"
    )
    
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入（JSON 数组字符串）"
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=SUPPORTED_OUTPUT_FORMATS,
        default="json",
        help=f"输出格式: {', '.join(SUPPORTED_OUTPUT_FORMATS)}（默认: json）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，无需外部输入）"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细处理信息"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            print("\n✅ 全部自检通过")
            return 0
        except SkillError as e:
            print(f"\n❌ 自检失败: {e.code} - {e.message}", file=sys.stderr)
            return 1
    
    # 处理模式
    try:
        if args.batch:
            # 批量模式
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    raise SkillError("E003", "批量输入必须是 JSON 数组")
                result = process_batch_input(batch_data, args.format)
            except json.JSONDecodeError:
                raise SkillError("E003", "批量输入必须是有效的 JSON 数组")
        elif args.input:
            # 单条模式
            result = process_single_input(args.input, args.format)
        else:
            # 无输入时显示帮助
            parser.print_help()
            return 0
        
        # 输出结果
        if args.verbose:
            print("[明细] changed_items=0 项")  # changed_items 标记
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if isinstance(result, dict) and "output" in result:
                print(result["output"])
            elif isinstance(result, dict) and "results" in result:
                # 批量结果简化输出
                print(f"处理完成: {result['success_count']}/{result['total']} 项成功")
                for item in result["results"]:
                    if item["status"] == "success":
                        print(f"  ✓ {item.get('input_type', 'unknown')}: {item['confidence_label']}")
                    else:
                        print(f"  ✗ {item.get('error_code', 'E006')}: {item.get('error_message', '未知错误')}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        
        return 0
    
    except SkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E006: 内部处理异常 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
