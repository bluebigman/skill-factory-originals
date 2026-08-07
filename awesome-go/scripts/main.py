#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: main.py
功能: 根据功能规格实现"未命名工具"技能的核心逻辑。
      提供命令行接口，支持 --selftest 参数进行离线自检。
设计原则: 仅依据功能规格独立实现（clean-room），标准库优先。
"""

import argparse
import sys
import json
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术映射（依据规格 E001-E005，预留扩展）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 预留内部错误码（规格未要求，但为完整性补充）
    "E006": "内部处理逻辑错误，请检查输入数据。",
    "E007": "输出序列化失败，请检查数据格式。",
    "E008": "命令行参数解析失败。",
    "E009": "自检流程出现异常。",
    "E010": "未知错误，请联系维护者。",
}

# 置信度阈值（依据规格 Step 2）
CONFIDENCE_HIGH = 0.90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 标注"建议复核"
# <85% 标注"[需核实]"

# 默认输出模板的字段顺序
DEFAULT_FIELD_ORDER = ["input", "status", "confidence", "message", "data"]


# ============================================================
# 核心数据结构与工具函数
# ============================================================

def build_error_response(error_code: str, details: str = "") -> Dict[str, Any]:
    """
    构建标准错误响应结构。
    :param error_code: 错误码（如 "E001"）
    :param details: 附加细节信息（可选）
    :return: 错误响应字典
    """
    if error_code not in ERROR_MESSAGES:
        error_code = "E010"  # 未知错误
    message = ERROR_MESSAGES[error_code]
    if details:
        message = f"{message} ({details})"
    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "confidence": 0.0,
        "data": None,
    }


def validate_input(data: Any) -> Optional[Dict[str, Any]]:
    """
    校验输入数据是否符合要求（规格 Step 1: 收集最小信息集）。
    :param data: 用户输入的数据
    :return: 如果校验失败返回错误响应，否则返回 None
    """
    # E001: 输入为空
    if data is None:
        return build_error_response("E001")
    # 字符串空判断
    if isinstance(data, str) and not data.strip():
        return build_error_response("E001")
    # 列表/字典空判断
    if isinstance(data, (list, dict)) and len(data) == 0:
        return build_error_response("E001")
    return None


def extract_key_fields(data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入中提取关键信息并结构化（规格 Step 2 核心流程）。
    这是一个通用处理函数，根据输入类型做基础解析。

    实际场景中，此函数应根据具体业务逻辑扩展。
    这里实现一个通用版本：将输入包装为结构化结果。

    :param data: 用户输入的数据（字符串、列表、字典等）
    :return: (结构化数据字典, 置信度分数)
    """
    # 初始化结果
    result: Dict[str, Any] = {}
    confidence = 0.9  # 默认高置信度

    if isinstance(data, str):
        # 字符串输入：尝试解析为 JSON，失败则作为纯文本
        try:
            parsed = json.loads(data)
            result["parsed_type"] = "json"
            result["parsed_content"] = parsed
            confidence = 0.95  # 成功解析 JSON 置信度高
        except (json.JSONDecodeError, TypeError):
            result["parsed_type"] = "text"
            result["parsed_content"] = data
            # 纯文本置信度稍低
            confidence = 0.88

    elif isinstance(data, dict):
        # 字典输入：直接使用并补充元信息
        result["parsed_type"] = "dict"
        result["parsed_content"] = data
        result["key_count"] = len(data)
        confidence = 0.93  # 结构化数据置信度较高

    elif isinstance(data, list):
        # 列表输入：统计元素数量
        result["parsed_type"] = "list"
        result["parsed_content"] = data
        result["item_count"] = len(data)
        confidence = 0.92

    else:
        # 其他类型（数字、布尔等）
        result["parsed_type"] = type(data).__name__
        result["parsed_content"] = data
        confidence = 0.85  # 简单类型置信度中等

    # 添加通用元信息
    result["input_type"] = type(data).__name__
    result["length"] = len(data) if hasattr(data, "__len__") else None

    return result, confidence


def apply_confidence_rule(confidence: float) -> Dict[str, str]:
    """
    根据置信度应用输出规则（规格 Step 2 第 3 点）。
    :param confidence: 置信度分数 (0~1)
    :return: 包含状态和标注信息的字典
    """
    if confidence >= CONFIDENCE_HIGH:
        return {"status": "success", "note": ""}
    elif confidence >= CONFIDENCE_MEDIUM:
        return {"status": "review", "note": "建议复核"}
    else:
        return {"status": "verify", "note": "[需核实]"}


def format_output(input_data: Any, structured: Dict[str, Any],
                  confidence: float) -> Dict[str, Any]:
    """
    按默认模板组织输出（规格 Step 3）。
    :param input_data: 原始输入
    :param structured: 结构化后的数据
    :param confidence: 置信度
    :return: 标准输出字典
    """
    rule = apply_confidence_rule(confidence)

    # 构建输出结构
    output = {
        "input": input_data,
        "status": rule["status"],
        "confidence": round(confidence, 4),
        "message": rule["note"],
        "data": structured,
    }

    # 按默认字段顺序重排（保证输出一致性）
    ordered_output = {key: output[key] for key in DEFAULT_FIELD_ORDER}
    return ordered_output


def process_input(data: Any) -> Dict[str, Any]:
    """
    标准处理流程入口（规格 Step 2 + Step 3）。
    :param data: 用户输入
    :return: 标准输出字典
    """
    # Step 2.1: 输入校验
    validation_error = validate_input(data)
    if validation_error:
        return validation_error

    # Step 2.2: 核心处理
    structured, confidence = extract_key_fields(data)

    # Step 3: 输出与校验
    output = format_output(data, structured, confidence)

    # 添加置信度标注检查
    if output["status"] == "verify":
        # 低置信度时补充说明（规格 E005）
        output["message"] = f"{output['message']} 结果无法确定，建议：人工复核输入数据。"

    return output


def batch_process(inputs: List[Any]) -> Dict[str, Any]:
    """
    批量处理多个输入（规格"进阶用法"）。
    :param inputs: 输入列表
    :return: 批量处理结果
    """
    # 校验输入
    if not inputs:
        return build_error_response("E001", "批量输入为空")

    results = []
    for idx, item in enumerate(inputs):
        result = process_input(item)
        # 为每条结果添加序号
        result["index"] = idx + 1
        results.append(result)

    # 汇总统计
    success_count = sum(1 for r in results if r["status"] == "success")
    review_count = sum(1 for r in results if r["status"] == "review")
    verify_count = sum(1 for r in results if r["status"] == "verify")

    return {
        "status": "success",
        "confidence": 0.95,
        "message": f"批量处理完成：共 {len(results)} 条，成功 {success_count} 条，建议复核 {review_count} 条，需核实 {verify_count} 条",
        "data": {
            "total": len(results),
            "success_count": success_count,
            "review_count": review_count,
            "verify_count": verify_count,
            "results": results,
        },
    }


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑（不访问网络、不读外部文件）。
    使用内置硬编码样例数据，宽松阈值断言。
    :return: True 表示全部通过，否则抛出异常
    """
    print("[SELFTEST] 开始自检...")

    # 测试用例 1: 正常字符串输入
    print("[SELFTEST] 用例 1: 字符串输入")
    result1 = process_input("hello world")
    assert result1["status"] in ("success", "review", "verify"), \
        f"状态值异常: {result1['status']}"
    assert 0 <= result1["confidence"] <= 1, "置信度不在 [0,1] 区间"
    assert "data" in result1, "输出缺少 data 字段"
    assert result1["data"]["parsed_type"] in ("text", "json"), \
        f"解析类型异常: {result1['data']['parsed_type']}"
    print(f"  [OK] 状态={result1['status']}, 置信度={result1['confidence']}")

    # 测试用例 2: 字典输入
    print("[SELFTEST] 用例 2: 字典输入")
    dict_input = {"name": "test", "value": 123, "tags": ["a", "b"]}
    result2 = process_input(dict_input)
    assert result2["status"] in ("success", "review", "verify"), \
        f"状态值异常: {result2['status']}"
    assert result2["data"]["parsed_type"] == "dict", "字典类型解析错误"
    assert result2["data"]["key_count"] >= 2, "字典键数量异常"
    print(f"  [OK] 键数量={result2['data']['key_count']}")

    # 测试用例 3: 列表输入（批量场景）
    print("[SELFTEST] 用例 3: 列表输入")
    list_input = [1, 2, 3, 4, 5]
    result3 = process_input(list_input)
    assert result3["data"]["parsed_type"] == "list", "列表类型解析错误"
    assert result3["data"]["item_count"] == 5, "列表长度异常"
    print(f"  [OK] 元素数量={result3['data']['item_count']}")

    # 测试用例 4: JSON 字符串输入
    print("[SELFTEST] 用例 4: JSON 字符串输入")
    json_str = '{"key": "value", "num": 42}'
    result4 = process_input(json_str)
    assert result4["data"]["parsed_type"] == "json", "JSON 解析错误"
    assert result4["data"]["parsed_content"]["num"] == 42, "JSON 内容解析错误"
    print(f"  [OK] JSON 解析成功")

    # 测试用例 5: 空输入错误处理（E001）
    print("[SELFTEST] 用例 5: 空输入错误处理")
    result5 = process_input(None)
    assert result5["status"] == "error", "空输入应返回错误状态"
    assert result5["error_code"] == "E001", "错误码应为 E001"
    print(f"  [OK] 错误码={result5['error_code']}")

    # 测试用例 6: 批量处理
    print("[SELFTEST] 用例 6: 批量处理")
    batch_input = ["item1", {"key": "value"}, [1, 2, 3], None]
    batch_result = batch_process(batch_input)
    assert batch_result["status"] == "success", "批量处理应成功"
    assert batch_result["data"]["total"] >= 3, "批量总数异常"
    assert batch_result["data"]["success_count"] >= 0, "成功数不能为负"
    print(f"  [OK] 批量总数={batch_result['data']['total']}")

    # 测试用例 7: 置信度规则
    print("[SELFTEST] 用例 7: 置信度规则")
    rule_high = apply_confidence_rule(0.95)
    assert rule_high["status"] == "success", "高置信度应为 success"
    rule_medium = apply_confidence_rule(0.87)
    assert rule_medium["status"] == "review", "中置信度应为 review"
    rule_low = apply_confidence_rule(0.80)
    assert rule_low["status"] == "verify", "低置信度应为 verify"
    print(f"  [OK] 阈值判断正确")

    # 测试用例 8: 错误响应结构
    print("[SELFTEST] 用例 8: 错误响应结构")
    err = build_error_response("E003", "测试细节")
    assert err["status"] == "error", "错误响应状态应为 error"
    assert err["error_code"] == "E003", "错误码不正确"
    assert "测试细节" in err["message"], "错误细节未包含"
    print(f"  [OK] 错误码={err['error_code']}")

    print("[SELFTEST] 全部测试通过 ✔")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数。
    :return: 退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="未命名工具 - 通用数据处理技能",
        epilog="示例: python main.py --input 'hello' 或 python main.py --selftest"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（字符串形式，可包含 JSON）"
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量输入多个数据项，以空格分隔"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"[SELFTEST] 断言失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[SELFTEST] 异常: {e}", file=sys.stderr)
            return 1

    # 批量模式
    if args.batch:
        try:
            result = batch_process(args.batch)
        except Exception as e:
            result = build_error_response("E010", str(e))
    # 单条模式
    elif args.input is not None:
        try:
            # 尝试解析 JSON 字符串
            try:
                data = json.loads(args.input)
            except json.JSONDecodeError:
                data = args.input
            result = process_input(data)
        except Exception as e:
            result = build_error_response("E010", str(e))
    else:
        # 未提供输入
        result = build_error_response("E001")
        result["message"] += " 请使用 --input 或 --batch 参数提供数据。"

    # 输出
    if args.output_format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        # 简单文本输出
        print(f"状态: {result.get('status', 'unknown')}")
        print(f"消息: {result.get('message', '')}")
        if "confidence" in result:
            print(f"置信度: {result['confidence']}")
        if "data" in result and result["data"]:
            print(f"数据: {json.dumps(result['data'], ensure_ascii=False, default=str)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
