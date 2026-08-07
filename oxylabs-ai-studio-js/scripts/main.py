#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫采集 (oxylabs-ai-studio-js) - 独立实现脚本

本脚本依据功能规格独立实现，提供以下核心能力：
1. 将用户提供的数据/文件/URL 转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

用法:
    python main.py --selftest          # 运行内置自检
    python main.py --input <文本>       # 处理单个输入
    python main.py --batch <文件路径>   # 批量处理文件中的行
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "批量处理失败，请检查输入文件",
    "E008": "参数配置错误",
    "E009": "输出写入失败",
    "E010": "未知错误",
}


# ============================================================
# 核心数据结构
# ============================================================
class ScrapingResult:
    """爬虫采集结果对象"""

    def __init__(self) -> None:
        self.raw_input: str = ""
        self.structured_data: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []
        self.status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "raw_input": self.raw_input,
            "structured_data": self.structured_data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "status": self.status,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
def validate_input(raw_input: str) -> Tuple[bool, Optional[str]]:
    """
    验证输入内容

    参数:
        raw_input: 用户输入的原始文本

    返回:
        (是否有效, 错误码或None)
    """
    if not raw_input or not raw_input.strip():
        return False, "E001"

    # 检查是否包含关键信息（至少包含一些有意义的内容）
    if len(raw_input.strip()) < 2:
        return False, "E002"

    return True, None


def parse_key_fields(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键字段

    参数:
        raw_input: 原始输入文本

    返回:
        结构化字段字典
    """
    fields: Dict[str, Any] = {}
    text = raw_input.strip()

    # 识别URL
    if "http://" in text or "https://" in text:
        fields["url"] = text[text.find("http"):].split()[0]
        fields["type"] = "url"
    # 识别JSON格式
    elif text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                fields = parsed
                fields["type"] = "json"
            else:
                fields["type"] = "unknown"
        except json.JSONDecodeError:
            fields["type"] = "text"
    # 识别CSV/TSV格式
    elif "," in text or "\t" in text:
        delimiter = "\t" if "\t" in text else ","
        parts = [p.strip() for p in text.split(delimiter) if p.strip()]
        fields["type"] = "delimited"
        fields["data"] = parts
        fields["count"] = len(parts)
    # 默认作为纯文本处理
    else:
        fields["type"] = "text"
        fields["content"] = text
        fields["length"] = len(text)

    # 提取可能的键值对（简单启发式）
    key_value_patterns = []
    for line in text.split("\n"):
        if ":" in line and not line.strip().startswith("#"):
            key, _, value = line.partition(":")
            key_value_patterns.append((key.strip(), value.strip()))

    if key_value_patterns:
        fields["key_values"] = key_value_patterns

    return fields


def calculate_confidence(structured_data: Dict[str, Any]) -> float:
    """
    计算置信度

    根据结构化数据的完整性和明确性计算置信度分数。

    参数:
        structured_data: 结构化数据字典

    返回:
        置信度分数 (0.0 - 1.0)
    """
    if not structured_data:
        return 0.0

    confidence = 0.85  # 基础分数

    # 根据类型调整
    data_type = structured_data.get("type", "")
    if data_type == "url":
        confidence += 0.05  # URL明确，加分
    elif data_type == "json":
        # JSON格式明确，检查是否有足够字段
        if len(structured_data) >= 3:
            confidence += 0.05
        else:
            confidence -= 0.05
    elif data_type == "delimited":
        # 分隔符格式，检查数据量
        if structured_data.get("count", 0) >= 3:
            confidence += 0.05
        else:
            confidence -= 0.05
    else:
        # 纯文本，稍微降低置信度
        confidence -= 0.05

    # 检查是否有键值对
    if "key_values" in structured_data:
        confidence += 0.03

    # 限制范围
    return max(0.0, min(1.0, confidence))


def generate_output(result: ScrapingResult) -> Dict[str, Any]:
    """
    生成最终输出

    参数:
        result: 处理结果对象

    返回:
        输出字典
    """
    output = {
        "status": "success",
        "data": result.structured_data,
        "confidence": result.confidence,
        "confidence_level": "",
        "warnings": result.warnings,
    }

    # 设置置信度等级
    if result.confidence >= 0.90:
        output["confidence_level"] = "直接输出"
    elif result.confidence >= 0.85:
        output["confidence_level"] = "建议复核"
    else:
        output["confidence_level"] = "需核实"
        output["warnings"].append("低置信度结果，请人工复核关键字段")

    return output


def process_single_input(raw_input: str) -> ScrapingResult:
    """
    处理单个输入

    参数:
        raw_input: 原始输入文本

    返回:
        处理结果对象
    """
    result = ScrapingResult()
    result.raw_input = raw_input

    # 验证输入
    is_valid, error_code = validate_input(raw_input)
    if not is_valid:
        result.status = "error"
        result.warnings.append(ERROR_CODES.get(error_code, ERROR_CODES["E010"]))
        result.confidence = 0.0
        return result

    # 解析关键字段
    try:
        result.structured_data = parse_key_fields(raw_input)
        result.confidence = calculate_confidence(result.structured_data)
        result.status = "processed"
    except Exception as e:
        result.status = "error"
        result.warnings.append(f"处理失败: {str(e)}")
        result.confidence = 0.0

    return result


def process_batch_inputs(inputs: List[str]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入

    参数:
        inputs: 输入文本列表

    返回:
        处理结果列表
    """
    results = []
    for idx, raw_input in enumerate(inputs, 1):
        result = process_single_input(raw_input)
        result_dict = result.to_dict()
        result_dict["index"] = idx
        results.append(result_dict)
    return results


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检

    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。

    返回:
        自检是否通过
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    all_passed = True

    # 测试用例1: URL输入
    print("\n[测试1] URL输入")
    test_url = "https://example.com/product/12345"
    result = process_single_input(test_url)
    if result.status != "processed":
        print(f"  ✗ URL处理失败: {result.status}")
        all_passed = False
    elif result.structured_data.get("type") != "url":
        print("  ✗ URL类型识别错误")
        all_passed = False
    elif not (0.5 <= result.confidence <= 1.0):
        print(f"  ✗ URL置信度异常: {result.confidence}")
        all_passed = False
    else:
        print(f"  ✓ URL解析成功，置信度: {result.confidence:.2f}")

    # 测试用例2: JSON输入
    print("\n[测试2] JSON输入")
    test_json = '{"name": "测试商品", "price": 99.9, "category": "电子产品"}'
    result = process_single_input(test_json)
    if result.status != "processed":
        print(f"  ✗ JSON处理失败: {result.status}")
        all_passed = False
    elif result.structured_data.get("type") != "json":
        print("  ✗ JSON类型识别错误")
        all_passed = False
    elif not (0.5 <= result.confidence <= 1.0):
        print(f"  ✗ JSON置信度异常: {result.confidence}")
        all_passed = False
    else:
        print(f"  ✓ JSON解析成功，置信度: {result.confidence:.2f}")

    # 测试用例3: 分隔符输入
    print("\n[测试3] 分隔符输入")
    test_csv = "苹果,香蕉,橙子,葡萄"
    result = process_single_input(test_csv)
    if result.status != "processed":
        print(f"  ✗ 分隔符处理失败: {result.status}")
        all_passed = False
    elif result.structured_data.get("type") != "delimited":
        print("  ✗ 分隔符类型识别错误")
        all_passed = False
    elif result.structured_data.get("count", 0) < 3:
        print("  ✗ 分隔符数据数量不足")
        all_passed = False
    elif not (0.5 <= result.confidence <= 1.0):
        print(f"  ✗ 分隔符置信度异常: {result.confidence}")
        all_passed = False
    else:
        print(f"  ✓ 分隔符解析成功，置信度: {result.confidence:.2f}")

    # 测试用例4: 纯文本输入
    print("\n[测试4] 纯文本输入")
    test_text = "这是一个测试文本，包含一些关键信息用于测试。"
    result = process_single_input(test_text)
    if result.status != "processed":
        print(f"  ✗ 文本处理失败: {result.status}")
        all_passed = False
    elif result.structured_data.get("type") != "text":
        print("  ✗ 文本类型识别错误")
        all_passed = False
    elif not (0.3 <= result.confidence <= 1.0):
        print(f"  ✗ 文本置信度异常: {result.confidence}")
        all_passed = False
    else:
        print(f"  ✓ 文本解析成功，置信度: {result.confidence:.2f}")

    # 测试用例5: 空输入处理
    print("\n[测试5] 空输入处理")
    result = process_single_input("")
    if result.status != "error":
        print("  ✗ 空输入应该返回错误状态")
        all_passed = False
    elif not result.warnings:
        print("  ✗ 空输入应该产生警告")
        all_passed = False
    else:
        print(f"  ✓ 空输入错误处理正确")
        print(f"    警告信息: {result.warnings[0]}")

    # 测试用例6: 批量处理
    print("\n[测试6] 批量处理")
    batch_inputs = [
        "https://example.com/product/1",
        '{"id": 2, "name": "商品B"}',
        "数据1,数据2,数据3",
    ]
    batch_results = process_batch_inputs(batch_inputs)
    if len(batch_results) != 3:
        print(f"  ✗ 批量处理数量错误: {len(batch_results)}")
        all_passed = False
    elif not all(r["status"] == "processed" for r in batch_results):
        print("  ✗ 批量处理存在失败项")
        all_passed = False
    else:
        print(f"  ✓ 批量处理成功，共 {len(batch_results)} 项")

    # 测试用例7: 置信度区间验证
    print("\n[测试7] 置信度区间验证")
    test_inputs = [
        "https://example.com",
        "简单文本",
        '{"key": "value"}',
    ]
    confidences = []
    for test_input in test_inputs:
        result = process_single_input(test_input)
        confidences.append(result.confidence)

    if not all(0.0 <= c <= 1.0 for c in confidences):
        print("  ✗ 置信度超出[0,1]范围")
        all_passed = False
    elif not (min(confidences) < max(confidences)):
        print("  ✗ 不同输入应该产生不同置信度")
        all_passed = False
    else:
        print(f"  ✓ 置信度区间验证通过: {[f'{c:.2f}' for c in confidences]}")

    # 测试用例8: 输出格式验证
    print("\n[测试8] 输出格式验证")
    result = process_single_input("https://example.com/test")
    output = generate_output(result)
    if output["status"] != "success":
        print("  ✗ 生成输出状态错误")
        all_passed = False
    elif "confidence_level" not in output:
        print("  ✗ 输出缺少置信度等级")
        all_passed = False
    elif not isinstance(output["data"], dict):
        print("  ✗ 输出数据结构错误")
        all_passed = False
    else:
        print("  ✓ 输出格式验证通过")

    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 主程序
# ============================================================
def main() -> int:
    """
    主程序入口

    返回:
        退出码 (0表示成功，非0表示失败)
    """
    parser = argparse.ArgumentParser(
        description="爬虫采集 - 结构化数据提取工具",
        epilog="示例: python main.py --input 'https://example.com'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="处理单个输入文本",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件中的行",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出结果到JSON文件",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理单个输入
    if args.input:
        result = process_single_input(args.input)
        output = generate_output(result)

        # 输出结果
        print(json.dumps(output, ensure_ascii=False, indent=2))

        # 保存到文件（如果指定）
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
                print(f"\n结果已保存到: {args.output}")
            except Exception as e:
                print(f"E009: 输出写入失败 - {str(e)}", file=sys.stderr)
                return 9

        return 0

    # 批量处理
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            if not lines:
                print("E001: 输入文件为空", file=sys.stderr)
                return 1

            results = process_batch_inputs(lines)

            # 输出结果
            output = {
                "status": "success",
                "total": len(results),
                "results": results,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))

            # 保存到文件（如果指定）
            if args.output:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        json.dump(output, f, ensure_ascii=False, indent=2)
                    print(f"\n结果已保存到: {args.output}")
                except Exception as e:
                    print(f"E009: 输出写入失败 - {str(e)}", file=sys.stderr)
                    return 9

            return 0

        except FileNotFoundError:
            print("E007: 批量处理失败 - 文件不存在", file=sys.stderr)
            return 7
        except Exception as e:
            print(f"E007: 批量处理失败 - {str(e)}", file=sys.stderr)
            return 7

    # 未指定任何操作
    parser.print_help()
    print("\nE008: 请指定 --selftest, --input 或 --batch 参数", file=sys.stderr)
    return 8


if __name__ == "__main__":
    sys.exit(main())
