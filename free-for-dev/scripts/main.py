#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现的 free-for-dev 技能脚本。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    1. 将用户提供的数据（文本/结构化内容）解析为结构化结果
    2. 识别并保留关键信息
    3. 按约定格式输出，并给出置信度标注
    4. 支持批量处理
    5. 包含 --selftest 离线自检模式（内置硬编码样例，不依赖外部环境）

错误码：
    E001 - 输入为空
    E002 - 关键信息缺失
    E003 - 输入格式错误
    E004 - 超出能力边界
    E005 - 置信度过低
    E006 - 内部处理异常
    E007 - 参数解析错误
    E008 - 批量处理中断
    E009 - 输出格式化失败
    E010 - 未知错误

运行方式：
    python scripts/main.py --selftest
    python scripts/main.py --input "文本内容" [--batch]
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 默认输出模板（字段结构）
DEFAULT_OUTPUT_TEMPLATE: Dict[str, str] = {
    "summary": "概要信息",
    "details": "详细信息",
    "confidence": "置信度"
}

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 0.90
MEDIUM_CONFIDENCE_THRESHOLD = 0.85

# 错误码与标准化话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "批量处理中断，请检查输入数据",
    "E009": "输出格式化失败，请检查输出模板",
    "E010": "发生未知错误，请联系管理员"
}


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息并结构化。

    参数:
        raw_input: 用户提供的原始输入文本

    返回:
        结构化字典，包含解析出的关键字段

    异常:
        E001: 输入为空
        E003: 输入格式错误（无法识别为有效内容）
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    # 尝试解析 JSON 格式输入
    try:
        parsed = json.loads(raw_input)
        if isinstance(parsed, dict):
            return {"type": "json", "data": parsed}
        elif isinstance(parsed, list):
            return {"type": "list", "data": parsed}
    except json.JSONDecodeError:
        pass

    # 尝试解析键值对格式（如 "key1=value1; key2=value2"）
    if "=" in raw_input:
        fields: Dict[str, str] = {}
        for item in raw_input.replace(";", ",").split(","):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                fields[key.strip()] = value.strip()
        if fields:
            return {"type": "keyvalue", "data": fields}

    # 普通文本格式
    lines = [line.strip() for line in raw_input.strip().splitlines() if line.strip()]
    if lines:
        return {"type": "text", "data": lines}

    # 无法识别的格式
    raise ValueError("E003")


def extract_key_info(structured_input: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    """
    从结构化输入中提取关键信息，并计算置信度。

    参数:
        structured_input: parse_input 返回的结构化数据

    返回:
        (关键信息字典, 置信度浮点数 0~1)
    """
    input_type = structured_input.get("type", "")
    data = structured_input.get("data", {})

    key_info: Dict[str, Any] = {}
    confidence = 0.0

    if input_type == "json" and isinstance(data, dict):
        # 从 JSON 中提取字段
        key_info = {k: v for k, v in data.items() if v is not None}
        confidence = min(0.95, 0.5 + 0.05 * len(key_info))

    elif input_type == "keyvalue" and isinstance(data, dict):
        key_info = dict(data)
        confidence = min(0.90, 0.5 + 0.04 * len(key_info))

    elif input_type == "text" and isinstance(data, list):
        # 从文本行中提取信息
        key_info = {"lines": data, "count": len(data)}
        confidence = min(0.85, 0.4 + 0.03 * len(data))

    elif input_type == "list" and isinstance(data, list):
        key_info = {"items": data, "count": len(data)}
        confidence = min(0.88, 0.45 + 0.04 * len(data))

    else:
        confidence = 0.3

    return key_info, confidence


def generate_output(key_info: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    按默认模板生成输出结果，并标注置信度。

    参数:
        key_info: 提取的关键信息
        confidence: 置信度 (0~1)

    返回:
        格式化输出字典
    """
    output = {
        "summary": f"共识别到 {len(key_info)} 个关键字段",
        "details": key_info,
        "confidence": confidence
    }

    # 根据置信度添加标注
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        output["note"] = "高置信度，可直接使用"
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        output["note"] = "建议复核"
    else:
        output["note"] = "[需核实] 请人工确认关键结果"

    return output


def process_single_input(raw_input: str) -> Dict[str, Any]:
    """
    处理单个输入，执行完整流程。

    参数:
        raw_input: 原始输入文本

    返回:
        处理结果字典

    异常:
        E001-E005: 各种错误码
    """
    try:
        # Step 1: 解析输入
        structured = parse_input(raw_input)

        # Step 2: 提取关键信息
        key_info, confidence = extract_key_info(structured)

        # 检查关键信息是否过少
        if not key_info:
            raise ValueError("E002")

        # 检查置信度
        if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
            # 低置信度但仍可输出，加标注
            pass

        # Step 3: 生成输出
        result = generate_output(key_info, confidence)
        return result

    except ValueError as e:
        error_code = str(e)
        if error_code in ERROR_MESSAGES:
            raise ValueError(error_code)
        raise ValueError("E006")
    except Exception:
        raise ValueError("E010")


def process_batch_input(inputs: List[str]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入文本列表

    返回:
        处理结果列表

    异常:
        E008: 批量处理中断
    """
    results = []
    try:
        for i, raw_input in enumerate(inputs, 1):
            try:
                result = process_single_input(raw_input)
                result["batch_index"] = i
                results.append(result)
            except ValueError as e:
                error_code = str(e)
                results.append({
                    "batch_index": i,
                    "error": error_code,
                    "error_message": ERROR_MESSAGES.get(error_code, "未知错误")
                })
    except Exception:
        raise ValueError("E008")

    return results


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("=" * 60)
    print("free-for-dev 技能自检")
    print("=" * 60)

    # 测试用例 1: JSON 输入
    print("\n[测试1] JSON 输入处理")
    json_input = '{"name": "test-project", "type": "web", "tier": "free"}'
    try:
        result = process_single_input(json_input)
        # 宽松断言：结果应为字典，包含关键字段
        assert isinstance(result, dict), "结果不是字典"
        assert "summary" in result, "缺少 summary 字段"
        assert "details" in result, "缺少 details 字段"
        assert "confidence" in result, "缺少 confidence 字段"
        # 置信度应在合理区间
        assert 0 <= result["confidence"] <= 1, "置信度超出范围"
        print("  ✓ 通过")

        # 验证关键信息被保留
        details = result["details"]
        assert details.get("name") == "test-project", "name 字段未保留"
        assert details.get("tier") == "free", "tier 字段未保留"
        print("  ✓ 关键信息保留正确")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 2: 键值对输入
    print("\n[测试2] 键值对输入处理")
    kv_input = "name=myapp; region=us-east-1; plan=hobby"
    try:
        result = process_single_input(kv_input)
        assert isinstance(result, dict), "结果不是字典"
        assert result["confidence"] > 0.5, "置信度过低"
        details = result["details"]
        assert details.get("plan") == "hobby", "plan 字段未保留"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 3: 文本输入
    print("\n[测试3] 文本输入处理")
    text_input = "第一行内容\n第二行内容\n第三行内容"
    try:
        result = process_single_input(text_input)
        assert isinstance(result, dict), "结果不是字典"
        details = result["details"]
        assert "count" in details, "缺少 count 字段"
        assert details["count"] >= 2, "行数统计不正确"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 4: 空输入错误处理
    print("\n[测试4] 空输入错误处理")
    try:
        process_single_input("")
        print("  ✗ 失败: 未抛出 E001 错误")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码不正确: {e}"
        print("  ✓ 正确抛出 E001")

    # 测试用例 5: 批量处理
    print("\n[测试5] 批量处理")
    batch_inputs = [
        '{"a": 1, "b": 2}',
        "key1=val1",
        "普通文本行",
        ""  # 空输入应产生错误记录但不中断
    ]
    try:
        results = process_batch_input(batch_inputs)
        assert len(results) == 4, "批量处理结果数量不正确"
        # 检查错误记录
        error_items = [r for r in results if "error" in r]
        assert len(error_items) >= 1, "未捕获空输入错误"
        print(f"  ✓ 通过 (共 {len(results)} 条，其中 {len(error_items)} 条错误)")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 6: 置信度标注逻辑
    print("\n[测试6] 置信度标注逻辑")
    try:
        # 高置信度场景
        high_conf_input = '{"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9}'
        result = process_single_input(high_conf_input)
        assert result["confidence"] >= 0.9, "高置信度场景置信度未达到阈值"
        assert "高置信度" in result["note"], "高置信度标注缺失"
        print("  ✓ 高置信度标注正确")

        # 低置信度场景
        low_conf_input = "短文本"
        result = process_single_input(low_conf_input)
        assert result["confidence"] < 0.85, "低置信度场景置信度未低于阈值"
        assert "需核实" in result["note"], "低置信度标注缺失"
        print("  ✓ 低置信度标注正确")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 7: 错误码完整性
    print("\n[测试7] 错误码完整性")
    required_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    missing_codes = [code for code in required_codes if code not in ERROR_MESSAGES]
    assert not missing_codes, f"缺失错误码: {missing_codes}"
    print(f"  ✓ 全部 {len(required_codes)} 个错误码已定义")

    # 测试用例 8: 输出格式一致性
    print("\n[测试8] 输出格式一致性")
    sample_inputs = [
        '{"x": 1}',
        "y=2",
        "多行\n文本"
    ]
    try:
        for sample in sample_inputs:
            result = process_single_input(sample)
            # 所有输出应包含标准字段
            for field in DEFAULT_OUTPUT_TEMPLATE:
                assert field in result, f"输出缺少字段 {field}"
        print("  ✓ 所有输出包含标准字段")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    主入口函数。

    返回:
        退出码 (0 表示成功，非 0 表示失败)
    """
    parser = argparse.ArgumentParser(
        description="free-for-dev 技能 - 数据解析与结构化处理工具",
        epilog="错误码说明: " + ", ".join(f"{k}={v}" for k, v in ERROR_MESSAGES.items())
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部环境）"
    )

    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入文本"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入使用分号分隔多个数据项）"
    )

    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"自检过程发生异常: {e}")
            return 1

    # 处理模式
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}")
        print("提示: 使用 --input 参数提供输入，或使用 --selftest 运行自检")
        return 1

    try:
        if args.batch:
            # 批量处理：分号分隔
            inputs = [item.strip() for item in args.input.split(";") if item.strip()]
            if not inputs:
                raise ValueError("E001")

            results = process_batch_input(inputs)
            if args.output == "json":
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for i, result in enumerate(results, 1):
                    print(f"--- 结果 {i} ---")
                    if "error" in result:
                        print(f"错误: {result['error']} - {result['error_message']}")
                    else:
                        print(f"概要: {result['summary']}")
                        print(f"置信度: {result['confidence']:.2%}")
                        print(f"备注: {result['note']}")
                        print(f"详情: {json.dumps(result['details'], ensure_ascii=False)}")
        else:
            # 单条处理
            result = process_single_input(args.input)
            if args.output == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"概要: {result['summary']}")
                print(f"置信度: {result['confidence']:.2%}")
                print(f"备注: {result['note']}")
                print(f"详情: {json.dumps(result['details'], ensure_ascii=False, indent=2)}")

        return 0

    except ValueError as e:
        error_code = str(e)
        error_message = ERROR_MESSAGES.get(error_code, "未知错误")
        print(f"错误 {error_code}: {error_message}")
        return 1
    except Exception as e:
        print(f"错误 E010: {ERROR_MESSAGES['E010']} ({str(e)})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
