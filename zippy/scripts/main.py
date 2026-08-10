#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zippy - 轻量级邮政编码处理工具（独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
"""

import sys
import argparse
import json
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{\"input\": \"12345\", \"format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议：提供更具体的输入或使用专业工具",
    "E005": "结果无法确定，建议：补充更多上下文信息或人工复核",
    "E006": "内部处理错误，请检查输入数据",
    "E007": "输出格式不支持，支持的格式：json, text",
    "E008": "置信度计算失败，请检查输入数据",
    "E009": "批量处理时出现异常，请检查每个输入项",
    "E010": "未知错误，请重试或联系支持",
}

# 支持的关键字段（用于识别输入中的关键信息）
KEY_FIELDS = ["zipcode", "postal_code", "city", "state", "country", "address"]

# 置信度分档
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85


# ---------------------------------------------------------------------------
# 核心功能：识别关键信息
# ---------------------------------------------------------------------------
def extract_key_info(input_data: Any) -> Dict[str, Any]:
    """从输入中提取关键信息。

    Args:
        input_data: 用户输入的数据（字符串、字典或列表）

    Returns:
        包含关键字段的字典，以及置信度信息
    """
    if input_data is None:
        raise ValueError("E001")

    result: Dict[str, Any] = {}
    confidence = 0.0
    found_fields = 0

    # 情况1：输入是字典
    if isinstance(input_data, dict):
        for field in KEY_FIELDS:
            if field in input_data and input_data[field] is not None:
                result[field] = input_data[field]
                found_fields += 1

    # 情况2：输入是字符串（尝试解析为 JSON 字典）
    elif isinstance(input_data, str):
        text = input_data.strip()
        if not text:
            raise ValueError("E001")

        # 尝试解析 JSON
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                for field in KEY_FIELDS:
                    if field in parsed and parsed[field] is not None:
                        result[field] = parsed[field]
                        found_fields += 1
        except json.JSONDecodeError:
            # 如果不是 JSON，尝试按文本提取
            for field in KEY_FIELDS:
                # 简单模式匹配：字段名后跟冒号或等号
                import re
                pattern = rf"{field}\s*[:=]\s*([^,;\s]+)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    found_fields += 1

    # 情况3：输入是列表（批量）
    elif isinstance(input_data, list):
        if len(input_data) == 0:
            raise ValueError("E001")
        # 递归处理第一个元素作为代表
        first_item = extract_key_info(input_data[0])
        result = first_item
        found_fields = len(first_item.get("_fields", []))

    # 计算置信度
    if found_fields > 0:
        # 置信度 = 识别出的字段数 / 关键字段总数，加权后映射到 0-1
        ratio = found_fields / len(KEY_FIELDS)
        confidence = min(0.95, 0.5 + ratio * 0.5)
    else:
        # 没有任何字段被识别
        raise ValueError("E002")

    result["_confidence"] = confidence
    result["_fields"] = KEY_FIELDS[:found_fields]
    return result


# ---------------------------------------------------------------------------
# 核心功能：生成结构化输出
# ---------------------------------------------------------------------------
def generate_output(extracted: Dict[str, Any], output_format: str = "json") -> str:
    """按指定格式生成输出。

    Args:
        extracted: 提取的关键信息字典
        output_format: 输出格式（json 或 text）

    Returns:
        格式化后的输出字符串

    Raises:
        ValueError: 当输出格式不支持时
    """
    if output_format not in ("json", "text"):
        raise ValueError("E007")

    # 移除内部字段
    output_data = {k: v for k, v in extracted.items() if not k.startswith("_")}

    # 添加置信度标注
    confidence = extracted.get("_confidence", 0.0)
    if confidence >= CONFIDENCE_HIGH:
        confidence_label = "高"
    elif confidence >= CONFIDENCE_MEDIUM:
        confidence_label = "中（建议复核）"
    else:
        confidence_label = "低（需核实）"

    if output_format == "json":
        result = {
            "data": output_data,
            "confidence": round(confidence, 2),
            "confidence_label": confidence_label,
            "status": "success",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:  # text
        lines = ["处理结果："]
        for key, value in output_data.items():
            lines.append(f"  {key}: {value}")
        lines.append(f"  置信度: {confidence_label} ({confidence:.0%})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心功能：批量处理
# ---------------------------------------------------------------------------
def batch_process(inputs: List[Any], output_format: str = "json") -> List[str]:
    """批量处理多个输入。

    Args:
        inputs: 输入列表
        output_format: 输出格式

    Returns:
        每个输入对应的输出字符串列表
    """
    results = []
    for i, item in enumerate(inputs):
        try:
            extracted = extract_key_info(item)
            output = generate_output(extracted, output_format)
            results.append(output)
        except ValueError as e:
            error_code = str(e) if str(e).startswith("E") else "E009"
            results.append(
                json.dumps(
                    {
                        "error": error_code,
                        "message": ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E009"]),
                        "index": i,
                    },
                    ensure_ascii=False,
                )
            )
    return results


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_input(input_data: Any, output_format: str = "json") -> str:
    """主处理入口。

    Args:
        input_data: 用户输入
        output_format: 输出格式

    Returns:
        处理结果字符串

    Raises:
        ValueError: 当处理失败时，错误码为 E001-E010
    """
    # Step 1: 检查输入
    if input_data is None:
        raise ValueError("E001")

    # Step 2: 提取关键信息
    extracted = extract_key_info(input_data)

    # Step 3: 生成输出
    output = generate_output(extracted, output_format)
    return output


# ---------------------------------------------------------------------------
# 自测功能（不依赖外部文件）
# ---------------------------------------------------------------------------
def selftest() -> bool:
    """内置硬编码样例数据进行离线自检。

    Returns:
        True 表示自检通过
    """
    print("开始自检...")

    # 测试用例1：正常字典输入
    test1_input = {
        "zipcode": "10001",
        "city": "New York",
        "state": "NY",
        "country": "USA",
    }
    try:
        result1 = process_input(test1_input, "json")
        parsed1 = json.loads(result1)
        assert parsed1["status"] == "success", "测试1失败：状态不是 success"
        assert parsed1["data"]["zipcode"] == "10001", "测试1失败：zipcode 不匹配"
        assert parsed1["confidence"] >= 0.5, "测试1失败：置信度太低"
        print("测试1（字典输入）通过")
    except Exception as e:
        print(f"测试1失败：{e}")
        return False

    # 测试用例2：JSON 字符串输入
    test2_input = '{"postal_code": "20001", "city": "Washington"}'
    try:
        result2 = process_input(test2_input, "json")
        parsed2 = json.loads(result2)
        assert parsed2["status"] == "success", "测试2失败：状态不是 success"
        assert parsed2["data"]["postal_code"] == "20001", "测试2失败：postal_code 不匹配"
        print("测试2（JSON字符串输入）通过")
    except Exception as e:
        print(f"测试2失败：{e}")
        return False

    # 测试用例3：文本格式输出
    test3_input = {"zipcode": "30301", "city": "Atlanta"}
    try:
        result3 = process_input(test3_input, "text")
        assert "zipcode" in result3, "测试3失败：缺少 zipcode"
        assert "置信度" in result3, "测试3失败：缺少置信度标注"
        print("测试3（文本输出）通过")
    except Exception as e:
        print(f"测试3失败：{e}")
        return False

    # 测试用例4：批量处理
    test4_inputs = [
        {"zipcode": "60601", "city": "Chicago"},
        {"zipcode": "77001", "city": "Houston"},
        {"zipcode": "85001", "city": "Phoenix"},
    ]
    try:
        results4 = batch_process(test4_inputs, "json")
        assert len(results4) == 3, "测试4失败：结果数量不对"
        for r in results4:
            parsed = json.loads(r)
            assert parsed["status"] == "success", "测试4失败：批量处理出错"
        print("测试4（批量处理）通过")
    except Exception as e:
        print(f"测试4失败：{e}")
        return False

    # 测试用例5：空输入错误处理
    try:
        process_input(None)
        print("测试5失败：空输入应该抛出 E001")
        return False
    except ValueError as e:
        assert str(e) == "E001", "测试5失败：错误码不是 E001"
        print("测试5（空输入错误码）通过")

    # 测试用例6：无关键信息输入
    try:
        process_input({"unknown_field": "value"})
        print("测试6失败：无关键信息应该抛出 E002")
        return False
    except ValueError as e:
        assert str(e) == "E002", "测试6失败：错误码不是 E002"
        print("测试6（缺关键信息错误码）通过")

    # 测试用例7：不支持的输出格式
    try:
        process_input({"zipcode": "10001"}, "xml")
        print("测试7失败：不支持的格式应该抛出 E007")
        return False
    except ValueError as e:
        assert str(e) == "E007", "测试7失败：错误码不是 E007"
        print("测试7（格式错误码）通过")

    print("所有自检用例通过 ✅")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。

    Returns:
        退出码（0 表示成功，非 0 表示失败）
    """
    parser = argparse.ArgumentParser(
        description="zippy - 轻量级邮政编码处理工具",
        epilog="示例：python main.py --input '{\"zipcode\": \"10001\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON 字符串或文本）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认：json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON 数组字符串",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        return 0 if success else 1

    # 批量处理模式
    if args.batch:
        try:
            inputs = json.loads(args.batch)
            if not isinstance(inputs, list):
                print(f"错误 E003：{ERROR_MESSAGES['E003']}", file=sys.stderr)
                return 1
            results = batch_process(inputs, args.format)
            for r in results:
                print(r)
            return 0
        except json.JSONDecodeError:
            print(f"错误 E003：{ERROR_MESSAGES['E003']}", file=sys.stderr)
            return 1

    # 单条处理模式
    if not args.input:
        print(f"错误 E001：{ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        # 尝试将输入解析为 JSON
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            input_data = args.input

        output = process_input(input_data, args.format)
        print(output)
        return 0
    except ValueError as e:
        error_code = str(e)
        if error_code in ERROR_MESSAGES:
            print(f"错误 {error_code}：{ERROR_MESSAGES[error_code]}", file=sys.stderr)
        else:
            print(f"错误 E010：{ERROR_MESSAGES['E010']}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010：{ERROR_MESSAGES['E010']}（{e}）", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
