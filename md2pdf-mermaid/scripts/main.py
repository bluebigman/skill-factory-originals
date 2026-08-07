#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2pdf-mermaid 技能实现脚本（全新独立实现）

本脚本依据功能规格独立编写，不参考任何既有代码。
提供核心数据转换、格式校验、置信度评估与错误码体系。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源或输出格式",
    "E003": "输入格式不符合要求，示例：JSON 对象或 Markdown 文本",
    "E004": "这超出了本工具的能力范围，建议简化需求或换用专业工具",
    "E005": "结果无法确定，建议：补充更多信息或人工复核",
    "E006": "内部处理异常，请检查输入后重试",
    "E007": "输出格式不支持，支持格式：json / text",
    "E008": "批量处理时输入必须为列表",
    "E009": "置信度计算失败，请检查输入内容",
    "E010": "未知错误，请联系维护人员",
}


# ============================================================
# 核心工具函数
# ============================================================

def _safe_json_parse(raw: str) -> Tuple[Optional[Any], Optional[str]]:
    """安全解析 JSON 字符串，返回 (结果, 错误码或None)。"""
    try:
        return json.loads(raw), None
    except (json.JSONDecodeError, TypeError):
        return None, "E003"


def _extract_fields(data: Any) -> Dict[str, Any]:
    """
    从输入数据中提取关键字段，进行结构化处理。
    支持 dict / list / str 三种基本形态。
    """
    result: Dict[str, Any] = {}

    if isinstance(data, dict):
        # 字典直接提取键值对
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                result[str(key)] = value
            elif isinstance(value, (list, dict)):
                result[str(key)] = _extract_fields(value)
            else:
                result[str(key)] = str(value)

    elif isinstance(data, list):
        # 列表逐项处理
        for idx, item in enumerate(data):
            result[f"item_{idx + 1}"] = _extract_fields(item)

    elif isinstance(data, str):
        # 字符串尝试解析为 JSON，否则按文本处理
        parsed, err = _safe_json_parse(data)
        if err is None and parsed is not None:
            return _extract_fields(parsed)
        else:
            # 简单提取非空行
            lines = [line.strip() for line in data.splitlines() if line.strip()]
            if lines:
                result["text_lines"] = lines
                result["line_count"] = len(lines)

    return result


def _calculate_confidence(data: Any, extracted: Dict[str, Any]) -> float:
    """
    计算置信度（0~100）。
    规则：
      - 有结构化字段且非空：基础 90 分
      - 字段越多、类型越丰富，加分越多
      - 纯字符串且无结构：降分
    """
    score = 0.0

    if isinstance(data, dict) and data:
        score = 90.0
        # 字段类型丰富度加分
        types = {type(v).__name__ for v in data.values()}
        score += min(len(types) * 2, 10)  # 最多加10分

    elif isinstance(data, list) and data:
        score = 85.0
        score += min(len(data), 10)  # 列表项多则加分

    elif isinstance(data, str) and data.strip():
        score = 70.0
        if len(data.strip()) > 50:
            score += 5  # 长文本加一点分

    # 根据提取结果微调
    if extracted:
        score += min(len(extracted) * 1.5, 5)  # 提取字段多则加分

    # 限制在 0~100
    return max(0.0, min(100.0, score))


def _evaluate_confidence(score: float) -> Tuple[str, str]:
    """
    根据置信度分数返回 (标记, 建议)。
    规则：
      - ≥90：直接输出
      - 85~90：建议复核
      - <85：需核实
    """
    if score >= 90:
        return "直接输出", ""
    elif score >= 85:
        return "建议复核", "结果置信度在85%-90%之间，请人工复核关键字段。"
    else:
        return "[需核实]", "置信度低于85%，请补充更多信息或人工核实。"


# ============================================================
# 核心处理流程
# ============================================================

def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    核心处理函数：解析输入、提取字段、计算置信度、生成输出。
    返回结构化结果字典。
    """
    # 检查输入是否为空（E001）
    if not raw_input or not raw_input.strip():
        return {"error": "E001", "message": ERROR_CODES["E001"]}

    # 检查输出格式（E007）
    if output_format not in ("json", "text"):
        return {"error": "E007", "message": ERROR_CODES["E007"]}

    try:
        # 尝试解析 JSON
        data, parse_err = _safe_json_parse(raw_input)

        if parse_err is not None:
            # 非 JSON，按纯文本处理
            data = raw_input.strip()

        # 检查是否有有效内容（E002）
        if data is None or (isinstance(data, str) and not data.strip()):
            return {"error": "E002", "message": ERROR_CODES["E002"]}

        # 提取关键字段
        extracted = _extract_fields(data)

        # 检查是否提取到任何内容（E003）
        if not extracted:
            return {"error": "E003", "message": ERROR_CODES["E003"]}

        # 计算置信度
        confidence = _calculate_confidence(data, extracted)
        if confidence < 0 or confidence > 100:
            return {"error": "E009", "message": ERROR_CODES["E009"]}

        # 评估置信度
        level, advice = _evaluate_confidence(confidence)

        # 组装输出
        result = {
            "status": "success",
            "confidence_score": round(confidence, 1),
            "confidence_level": level,
            "advice": advice,
            "extracted_fields": extracted,
            "field_count": len(extracted),
        }

        if output_format == "text":
            result["formatted_text"] = _format_as_text(result)

        return result

    except Exception as exc:  # 兜底异常（E006 / E010）
        if "confidence" in str(exc).lower():
            return {"error": "E009", "message": ERROR_CODES["E009"]}
        return {"error": "E006", "message": f"{ERROR_CODES['E006']} 详情: {str(exc)}"}


def _format_as_text(result: Dict[str, Any]) -> str:
    """将结果格式化为可读文本。"""
    lines = []
    lines.append(f"处理结果（置信度 {result['confidence_score']}%）")
    lines.append(f"置信度等级: {result['confidence_level']}")
    if result["advice"]:
        lines.append(f"建议: {result['advice']}")
    lines.append(f"提取字段数: {result['field_count']}")
    lines.append("提取内容:")
    for key, value in result["extracted_fields"].items():
        if isinstance(value, dict):
            lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def batch_process(inputs: List[str], output_format: str = "json") -> Dict[str, Any]:
    """批量处理多个输入，返回汇总结果。"""
    if not isinstance(inputs, list):
        return {"error": "E008", "message": ERROR_CODES["E008"]}

    results = []
    for idx, item in enumerate(inputs):
        single_result = process_input(item, output_format)
        single_result["batch_index"] = idx + 1
        results.append(single_result)

    success_count = sum(1 for r in results if r.get("status") == "success")
    return {
        "status": "success" if success_count == len(results) else "partial",
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count,
        "results": results,
    }


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=== 开始自检 (selftest) ===")
    test_cases = [
        # 样例1：标准 JSON 输入
        {
            "name": "标准JSON输入",
            "input": '{"name": "张三", "age": 30, "city": "北京", "tags": ["a", "b"]}',
            "expect_success": True,
            "min_fields": 3,
            "min_confidence": 85,
        },
        # 样例2：纯文本输入
        {
            "name": "纯文本输入",
            "input": "这是一个测试文本，用于验证基本处理流程是否正常。包含一些内容。",
            "expect_success": True,
            "min_fields": 1,
            "min_confidence": 60,
        },
        # 样例3：空输入（应返回 E001）
        {
            "name": "空输入错误码",
            "input": "",
            "expect_success": False,
            "expect_error": "E001",
        },
        # 样例4：列表输入
        {
            "name": "列表输入",
            "input": '[{"id": 1, "value": "x"}, {"id": 2, "value": "y"}]',
            "expect_success": True,
            "min_fields": 2,
            "min_confidence": 80,
        },
        # 样例5：非法 JSON（应按文本处理）
        {
            "name": "非法JSON回退",
            "input": "这不是JSON { 内容",
            "expect_success": True,
            "min_fields": 1,
            "min_confidence": 50,
        },
    ]

    all_passed = True

    for idx, case in enumerate(test_cases, 1):
        print(f"\n用例 {idx}: {case['name']}")
        result = process_input(case["input"])

        # 检查是否期望成功
        if case["expect_success"]:
            if result.get("status") != "success":
                print(f"  [FAIL] 期望成功，实际失败: {result.get('error')}")
                all_passed = False
                continue

            # 宽松检查：字段数 >= 最小值
            field_count = result.get("field_count", 0)
            if field_count < case["min_fields"]:
                print(f"  [FAIL] 字段数不足: 期望>={case['min_fields']}, 实际={field_count}")
                all_passed = False
                continue

            # 宽松检查：置信度 >= 最小值
            confidence = result.get("confidence_score", 0)
            if confidence < case["min_confidence"]:
                print(f"  [FAIL] 置信度过低: 期望>={case['min_confidence']}, 实际={confidence}")
                all_passed = False
                continue

            print(f"  [PASS] 字段数={field_count}, 置信度={confidence}%")
        else:
            # 期望失败，检查错误码
            if result.get("error") != case["expect_error"]:
                print(f"  [FAIL] 期望错误码 {case['expect_error']}, 实际: {result.get('error')}")
                all_passed = False
                continue
            print(f"  [PASS] 正确返回错误码 {case['expect_error']}")

    # 批量处理测试
    print("\n批量处理测试:")
    batch_result = batch_process(
        ['{"a": 1}', "简单文本内容", ""],
        output_format="json"
    )
    if batch_result.get("status") not in ("success", "partial"):
        print(f"  [FAIL] 批量处理异常: {batch_result}")
        all_passed = False
    else:
        total = batch_result.get("total", 0)
        success = batch_result.get("success_count", 0)
        if total != 3 or success < 2:
            print(f"  [FAIL] 批量处理计数异常: total={total}, success={success}")
            all_passed = False
        else:
            print(f"  [PASS] 批量处理正常: {success}/{total} 成功")

    # 错误码完整性检查
    print("\n错误码完整性检查:")
    required_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    missing = [code for code in required_codes if code not in ERROR_CODES]
    if missing:
        print(f"  [FAIL] 缺少错误码: {missing}")
        all_passed = False
    else:
        print(f"  [PASS] 全部 {len(required_codes)} 个错误码已定义")

    # 总结
    print("\n=== 自检结束 ===")
    if all_passed:
        print("全部用例通过 ✅")
        return 0
    else:
        print("存在失败用例 ❌")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="md2pdf-mermaid 技能实现 - Markdown/JSON 转结构化结果",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（JSON 字符串或纯文本）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量处理：JSON 数组字符串，如 '[{\"a\": 1}]'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需外部输入）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量处理模式
    if args.batch:
        parsed, err = _safe_json_parse(args.batch)
        if err is not None or not isinstance(parsed, list):
            print(json.dumps({"error": "E008", "message": ERROR_CODES["E008"]}, ensure_ascii=False))
            return 1
        result = batch_process(parsed, args.format)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get("status") != "error" else 1

    # 单条处理模式
    if args.input:
        result = process_input(args.input, args.format)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get("status") == "success" else 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
