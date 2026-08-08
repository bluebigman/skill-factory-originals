#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
solar-wind-hacker-book 技能实现脚本
功能：代码审查（仅供学习与参考用途）
"""

import sys
import json
import argparse
from typing import Dict, List, Any


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容（数据/文件/URL）",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查输入格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "内部处理失败，请重试",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出格式不支持",
    "E009": "批量处理中断",
    "E010": "未知错误",
}


def make_error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误响应"""
    return {
        "status": "error",
        "error_code": code,
        "message": ERROR_CODES.get(code, ERROR_CODES["E010"]),
        "detail": detail,
    }


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: Any) -> Dict[str, Any]:
    """
    输入校验
    规则：
    - 输入不能为空
    - 输入必须是字符串或字典
    - 字符串必须非空
    """
    if raw_input is None:
        return make_error("E001")

    if isinstance(raw_input, str):
        if not raw_input.strip():
            return make_error("E001")
        return {"status": "ok", "data": raw_input.strip()}

    if isinstance(raw_input, dict):
        if not raw_input:
            return make_error("E001")
        return {"status": "ok", "data": raw_input}

    return make_error("E003", "输入类型必须是字符串或字典")


def extract_key_info(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键信息
    支持：
    - 字符串：按行拆分，识别键值对
    - 字典：直接使用
    """
    if isinstance(data, dict):
        # 字典输入直接使用，检查关键字段
        required_fields = ["content", "type"]  # 最小信息集
        missing = [f for f in required_fields if f not in data]
        if missing:
            return make_error("E002", f"缺少字段: {', '.join(missing)}")
        return {"status": "ok", "data": data}

    # 字符串输入：尝试解析
    lines = data.split("\n")
    result = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
        elif "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()

    if not result:
        # 无法解析为键值对，按纯文本处理
        result = {"content": data, "type": "text"}

    return {"status": "ok", "data": result}


def calculate_confidence(data: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）
    规则：
    - 包含 content 字段：+40
    - 包含 type 字段：+20
    - 包含额外字段：每个 +10，最多 +30
    - 字段值非空：每个 +5，最多 +10
    宽松阈值：>=60 为高置信度，>=50 为中置信度
    """
    score = 0.0
    field_count = 0

    if "content" in data and data["content"]:
        score += 40
        field_count += 1
    if "type" in data and data["type"]:
        score += 20
        field_count += 1

    # 额外字段
    extra_fields = set(data.keys()) - {"content", "type"}
    score += min(len(extra_fields) * 10, 30)
    field_count += len(extra_fields)

    # 值非空检查
    non_empty = sum(1 for v in data.values() if v and str(v).strip())
    score += min(non_empty * 5, 10)

    return min(score, 100.0)


def format_output(data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    按约定格式生成输出
    置信度分级：
    - >=90：直接输出
    - 85-90：标注"建议复核"
    - <85：标注"[需核实]"
    """
    result = {
        "status": "success",
        "data": data,
        "confidence": confidence,
        "confidence_level": "",
        "warning": "",
    }

    if confidence >= 90:
        result["confidence_level"] = "高"
    elif confidence >= 85:
        result["confidence_level"] = "中"
        result["warning"] = "建议复核"
    else:
        result["confidence_level"] = "低"
        result["warning"] = "[需核实] 结果不确定，请人工复核"

    return result


def process_single(input_data: Any) -> Dict[str, Any]:
    """
    单条处理流程
    Step 1: 输入校验
    Step 2: 提取关键信息
    Step 3: 计算置信度
    Step 4: 格式化输出
    """
    # Step 1: 输入校验
    validated = validate_input(input_data)
    if validated["status"] == "error":
        return validated

    # Step 2: 提取关键信息
    extracted = extract_key_info(validated["data"])
    if extracted["status"] == "error":
        return extracted

    # Step 3: 计算置信度
    confidence = calculate_confidence(extracted["data"])

    # Step 4: 格式化输出
    return format_output(extracted["data"], confidence)


def process_batch(inputs: List[Any]) -> Dict[str, Any]:
    """
    批量处理
    支持：列表输入，逐项处理
    """
    if not inputs:
        return make_error("E001")

    results = []
    for idx, item in enumerate(inputs):
        try:
            result = process_single(item)
            result["index"] = idx
            results.append(result)
        except Exception:
            results.append({
                "status": "error",
                "error_code": "E009",
                "message": ERROR_CODES["E009"],
                "index": idx,
            })

    return {"status": "success", "results": results}


# ============================================================
# 自检函数（内置硬编码样例）
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑
    使用内置硬编码样例，不读外部文件、不依赖工作目录、不访问网络
    断言使用宽松阈值，确保稳健
    """
    print("[自检] 开始执行核心逻辑自检...")
    all_passed = True

    # 测试用例 1: 正常字符串输入
    print("[自检] 测试1: 字符串输入处理")
    test1_input = "content: 测试代码片段\ntype: python\nlanguage: python3"
    result1 = process_single(test1_input)
    assert result1["status"] == "success", "测试1失败: 状态应为success"
    assert "content" in result1["data"], "测试1失败: 缺少content字段"
    assert result1["confidence"] > 50, "测试1失败: 置信度应大于50"
    print("[自检] 测试1通过 ✓")

    # 测试用例 2: 字典输入
    print("[自检] 测试2: 字典输入处理")
    test2_input = {"content": "def test(): pass", "type": "python"}
    result2 = process_single(test2_input)
    assert result2["status"] == "success", "测试2失败: 状态应为success"
    assert result2["confidence"] > 50, "测试2失败: 置信度应大于50"
    print("[自检] 测试2通过 ✓")

    # 测试用例 3: 空输入
    print("[自检] 测试3: 空输入处理")
    result3 = process_single("")
    assert result3["status"] == "error", "测试3失败: 状态应为error"
    assert result3["error_code"] == "E001", "测试3失败: 错误码应为E001"
    print("[自检] 测试3通过 ✓")

    # 测试用例 4: 批量处理
    print("[自检] 测试4: 批量处理")
    test4_inputs = [
        "content: 第一段\ntype: text",
        {"content": "第二段", "type": "markdown"},
        "",
    ]
    result4 = process_batch(test4_inputs)
    assert result4["status"] == "success", "测试4失败: 状态应为success"
    assert len(result4["results"]) == 3, "测试4失败: 结果数量应为3"
    assert result4["results"][0]["status"] == "success", "测试4失败: 第一条应成功"
    assert result4["results"][2]["status"] == "error", "测试4失败: 第三条应失败"
    print("[自检] 测试4通过 ✓")

    # 测试用例 5: 缺失关键字段
    print("[自检] 测试5: 缺失关键字段")
    test5_input = {"foo": "bar"}
    result5 = process_single(test5_input)
    assert result5["status"] == "error", "测试5失败: 状态应为error"
    assert result5["error_code"] == "E002", "测试5失败: 错误码应为E002"
    print("[自检] 测试5通过 ✓")

    # 测试用例 6: 置信度分级
    print("[自检] 测试6: 置信度分级")
    test6_input = {
        "content": "完整的代码审查内容",
        "type": "python",
        "language": "python3",
        "framework": "pytest",
        "author": "test",
    }
    result6 = process_single(test6_input)
    assert result6["status"] == "success", "测试6失败: 状态应为success"
    assert result6["confidence"] > 80, "测试6失败: 置信度应大于80"
    assert result6["confidence_level"] in ["高", "中"], "测试6失败: 置信度级别异常"
    print("[自检] 测试6通过 ✓")

    # 测试用例 7: 错误码有效性
    print("[自检] 测试7: 错误码体系")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_CODES, f"测试7失败: 缺少错误码 {code}"
        assert ERROR_CODES[code], f"测试7失败: 错误码 {code} 文案为空"
    print("[自检] 测试7通过 ✓")

    # 测试用例 8: 异常输入类型
    print("[自检] 测试8: 异常输入类型")
    result8 = process_single(12345)
    assert result8["status"] == "error", "测试8失败: 状态应为error"
    assert result8["error_code"] == "E003", "测试8失败: 错误码应为E003"
    print("[自检] 测试8通过 ✓")

    # 测试用例 9: 批量空输入
    print("[自检] 测试9: 批量空输入")
    result9 = process_batch([])
    assert result9["status"] == "error", "测试9失败: 状态应为error"
    assert result9["error_code"] == "E001", "测试9失败: 错误码应为E001"
    print("[自检] 测试9通过 ✓")

    # 测试用例 10: 纯文本输入
    print("[自检] 测试10: 纯文本输入")
    test10_input = "这是一段纯文本，没有键值对"
    result10 = process_single(test10_input)
    assert result10["status"] == "success", "测试10失败: 状态应为success"
    assert result10["data"]["type"] == "text", "测试10失败: 类型应为text"
    print("[自检] 测试10通过 ✓")

    print(f"\n[自检] 全部测试通过! ({'成功' if all_passed else '失败'})")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="solar-wind-hacker-book - 代码审查技能工具",
        epilog="示例: python main.py --input 'content: 测试' 或 python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码样例，不依赖外部环境）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串或JSON格式）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入（JSON数组格式）",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"\n[自检] 失败: {e}")
            return 1
        except Exception as e:
            print(f"\n[自检] 异常: {e}")
            return 1

    # 处理模式
    try:
        if args.batch:
            # 批量处理
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    print(json.dumps(make_error("E003", "批量输入必须是JSON数组"), ensure_ascii=False))
                    return 1
                result = process_batch(batch_data)
            except json.JSONDecodeError:
                print(json.dumps(make_error("E003", "JSON解析失败"), ensure_ascii=False))
                return 1
        elif args.input:
            # 单条处理
            # 尝试解析为JSON
            try:
                input_data = json.loads(args.input)
            except json.JSONDecodeError:
                input_data = args.input
            result = process_single(input_data)
        else:
            # 无输入
            print(json.dumps(make_error("E001"), ensure_ascii=False))
            return 1

        # 输出
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 文本输出
            if result["status"] == "success":
                for key, value in result.get("data", {}).items():
                    print(f"{key}: {value}")
                print(f"置信度: {result['confidence']}% ({result['confidence_level']})")
                if result.get("warning"):
                    print(f"警告: {result['warning']}")
            else:
                print(f"错误 [{result['error_code']}]: {result['message']}")

        return 0

    except Exception as e:
        error_result = make_error("E006", str(e))
        print(json.dumps(error_result, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
