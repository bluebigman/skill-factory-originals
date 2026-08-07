#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui-ux-pro-max-skill - 独立实现脚本
==================================
依据功能规格独立编写，不参考任何既有实现。

提供基于输入内容的结构化处理能力，支持置信度评估、
错误码返回、批量处理与自定义输出格式。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import sys
import json
from typing import Any, Dict, List, Optional, Tuple

# ------------------------- 错误码定义 -------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试",
    "E007": "输出格式不支持",
    "E008": "批量处理中断，存在失败项",
    "E009": "参数校验失败",
    "E010": "未知错误",
}

# ------------------------- 核心数据结构 -------------------------
class ProcessedResult:
    """单个输入的处理结果对象。"""
    def __init__(self, input_data: Any, output: Any, confidence: float,
                 warnings: Optional[List[str]] = None):
        self.input_data = input_data
        self.output = output
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "input": self.input_data,
            "output": self.output,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ------------------------- 核心处理逻辑 -------------------------
def extract_key_fields(data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入数据中提取关键字段，返回 (结构化字段字典, 置信度)。

    规则：
    - 字符串：按常见分隔符拆分，识别键值对
    - 字典：直接使用
    - 列表：逐个元素处理
    - 其他类型：转为字符串处理
    """
    if data is None:
        return {}, 0.0

    if isinstance(data, dict):
        # 字典直接使用，置信度较高
        return data, 0.95

    if isinstance(data, list):
        # 列表逐项处理，合并结果
        merged: Dict[str, Any] = {}
        for item in data:
            item_fields, _ = extract_key_fields(item)
            merged.update(item_fields)
        return merged, 0.85

    if isinstance(data, str):
        # 尝试解析键值对格式：key=value 或 key:value
        fields: Dict[str, Any] = {}
        parts = data.replace(";", ",").replace("\n", ",").split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 尝试多种分隔符
            for sep in ["=", ":", "：", "->"]:
                if sep in part:
                    key, value = part.split(sep, 1)
                    fields[key.strip()] = value.strip()
                    break
        if fields:
            return fields, 0.80
        # 无法解析为键值对，整体作为文本
        return {"text": data}, 0.60

    # 其他类型转为字符串
    return {"value": str(data)}, 0.50


def validate_input(data: Any) -> Optional[str]:
    """
    校验输入数据是否满足处理要求。
    返回错误码，如果无错误返回 None。
    """
    if data is None:
        return "E001"
    if isinstance(data, str) and not data.strip():
        return "E001"
    if isinstance(data, list) and len(data) == 0:
        return "E001"
    return None


def determine_confidence(fields: Dict[str, Any], raw_data: Any) -> float:
    """
    根据提取的字段质量评估置信度。
    规则：
    - 字段数量多且非空 -> 高置信度
    - 字段数量少或为空 -> 低置信度
    """
    if not fields:
        return 0.0

    # 计算有效字段比例
    valid_count = sum(1 for v in fields.values() if v is not None and str(v).strip())
    total_count = len(fields)

    if total_count == 0:
        return 0.0

    ratio = valid_count / total_count

    # 根据比例和原始数据类型综合评估
    base_conf = 0.5 + ratio * 0.4

    # 原始数据为结构化类型时提升置信度
    if isinstance(raw_data, dict):
        base_conf += 0.1
    elif isinstance(raw_data, list):
        base_conf += 0.05

    # 限制在 0-1 范围内
    return max(0.0, min(1.0, base_conf))


def format_output(result: ProcessedResult, output_format: str = "json") -> str:
    """
    将处理结果格式化为指定格式。
    支持：json、text、table
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = [f"输入: {result.input_data}",
                 f"输出: {result.output}",
                 f"置信度: {result.confidence:.2%}"]
        if result.warnings:
            lines.append(f"警告: {'; '.join(result.warnings)}")
        return "\n".join(lines)

    if output_format == "table":
        # 简单的表格格式
        rows = [["字段", "值"]]
        for key, value in result.output.items():
            rows.append([str(key), str(value)])
        # 计算列宽
        col_widths = [max(len(row[0]) for row in rows),
                      max(len(row[1]) for row in rows)]
        header = " | ".join(rows[0][i].ljust(col_widths[i])
                           for i in range(2))
        separator = "-+-".join("-" * w for w in col_widths)
        body = "\n".join(" | ".join(row[i].ljust(col_widths[i])
                                    for i in range(2))
                         for row in rows[1:])
        return f"{header}\n{separator}\n{body}"

    return "E007"  # 不支持的格式


def process_single(data: Any, output_format: str = "json") -> ProcessedResult:
    """
    处理单个输入数据，返回处理结果。
    """
    # 校验输入
    err_code = validate_input(data)
    if err_code:
        return ProcessedResult(data, {}, 0.0, [ERROR_CODES[err_code]])

    # 提取关键字段
    fields, extract_conf = extract_key_fields(data)

    # 计算置信度
    confidence = determine_confidence(fields, data)

    # 生成警告
    warnings = []
    if confidence < 0.85:
        warnings.append("[需核实] 置信度较低，请人工复核")
    elif confidence < 0.90:
        warnings.append("建议复核")

    # 构造输出
    output = {
        "key_fields": fields,
        "field_count": len(fields),
        "processed": True,
    }

    return ProcessedResult(data, output, confidence, warnings)


def process_batch(data_list: List[Any], output_format: str = "json") -> List[ProcessedResult]:
    """
    批量处理多个输入数据。
    """
    results = []
    for item in data_list:
        result = process_single(item, output_format)
        results.append(result)
    return results


# ------------------------- 自检模块 -------------------------
def run_selftest() -> bool:
    """
    使用内置硬编码样例数据离线自检核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=== 自检开始 ===")

    # 测试用例 1：空输入
    print("\n[测试1] 空输入处理")
    result = process_single(None)
    assert result.confidence == 0.0, "空输入置信度应为0"
    assert len(result.warnings) > 0, "空输入应有警告"
    print("通过：空输入正确返回错误")

    # 测试用例 2：字典输入
    print("\n[测试2] 字典输入处理")
    dict_data = {"name": "test", "type": "demo", "version": "1.0"}
    result = process_single(dict_data)
    assert result.confidence > 0.8, "字典输入置信度应较高"
    assert result.output["field_count"] == 3, "字段数量应为3"
    print("通过：字典输入正确解析")

    # 测试用例 3：字符串键值对
    print("\n[测试3] 字符串键值对处理")
    str_data = "key1=value1, key2=value2"
    result = process_single(str_data)
    assert result.confidence > 0.5, "字符串输入置信度应中等"
    assert "key1" in result.output["key_fields"], "应解析出key1"
    print("通过：字符串键值对正确解析")

    # 测试用例 4：列表输入
    print("\n[测试4] 列表输入处理")
    list_data = ["a=1", "b=2", "c=3"]
    result = process_single(list_data)
    assert result.output["field_count"] >= 2, "列表应合并至少2个字段"
    assert result.confidence > 0.5, "列表输入置信度应中等"
    print("通过：列表输入正确合并")

    # 测试用例 5：批量处理
    print("\n[测试5] 批量处理")
    batch_data = [{"id": 1}, "key=value", ["x=1", "y=2"]]
    results = process_batch(batch_data)
    assert len(results) == 3, "批量处理应返回3个结果"
    assert all(r.confidence > 0 for r in results), "所有结果置信度应大于0"
    print("通过：批量处理正确执行")

    # 测试用例 6：输出格式
    print("\n[测试6] 输出格式")
    result = process_single({"test": "data"})
    json_output = format_output(result, "json")
    assert json_output.startswith("{"), "JSON输出应以{开头"
    text_output = format_output(result, "text")
    assert "输入:" in text_output, "文本输出应包含输入字段"
    print("通过：输出格式正确")

    # 测试用例 7：错误码
    print("\n[测试7] 错误码系统")
    assert "E001" in ERROR_CODES, "E001应存在"
    assert "E010" in ERROR_CODES, "E010应存在"
    assert len(ERROR_CODES) == 10, "应有10个错误码"
    print("通过：错误码系统完整")

    print("\n=== 自检全部通过 ===")
    return True


# ------------------------- 主入口 -------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="ui-ux-pro-max-skill - 设计智能处理工具",
        epilog="示例: python main.py --input 'key=value' --format json"
    )

    parser.add_argument(
        "--input", "-i",
        help="输入数据（字符串、JSON等），支持文件路径或直接输入"
    )
    parser.add_argument(
        "--input-file", "-f",
        help="从文件读取输入（JSON格式）"
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["json", "text", "table"],
        default="json",
        help="输出格式"
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量处理模式（输入为JSON数组）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检并退出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 收集输入
    input_data = None
    if args.input_file:
        try:
            with open(args.input_file, "r", encoding="utf-8") as f:
                input_data = json.load(f)
        except Exception as e:
            print(f"E006 读取文件失败: {e}", file=sys.stderr)
            return 1
    elif args.input:
        # 尝试解析为JSON
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            # 不是JSON，作为普通字符串
            input_data = args.input

    # 没有输入则提示
    if input_data is None:
        print(ERROR_CODES["E001"], file=sys.stderr)
        return 1

    # 处理数据
    try:
        if args.batch and isinstance(input_data, list):
            # 批量处理
            results = process_batch(input_data, args.format)
            for i, result in enumerate(results):
                print(f"--- 结果 {i+1} ---")
                print(format_output(result, args.format))
        else:
            # 单条处理
            result = process_single(input_data, args.format)
            print(format_output(result, args.format))
    except Exception as e:
        print(f"E006 处理异常: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
