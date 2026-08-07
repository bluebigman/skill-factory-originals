#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能名称: bestbuy-web-scraper-gpus (爬虫采集)
版本: 1.1.0
描述: 独立实现脚本，仅依据功能规格构建。
      核心能力：将输入内容转换为结构化结果，识别关键信息，
      按约定格式输出，并对不确定项给出置信度提示。
      注意：本脚本不访问网络，不读取外部文件（除用户显式传入外）。
"""

import argparse
import sys
import json
from typing import Dict, List, Any, Tuple


# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "输出格式错误",
    "E008": "参数错误",
    "E009": "数据解析失败",
    "E010": "未知错误",
}


def make_error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误响应结构。"""
    return {
        "ok": False,
        "error_code": code,
        "error_message": ERROR_CODES.get(code, "未知错误"),
        "detail": detail,
    }


def make_success(data: Any, confidence: float = 1.0, note: str = "") -> Dict[str, Any]:
    """构造标准成功响应结构。"""
    return {
        "ok": True,
        "data": data,
        "confidence": confidence,
        "note": note,
    }


# ---------------------------------------------------------------------------
# 核心逻辑：输入解析与结构化
# ---------------------------------------------------------------------------
def parse_input(raw_input: Any) -> Tuple[bool, Any, str]:
    """
    解析输入内容，识别关键信息并结构化。

    参数:
        raw_input: 用户提供的原始输入（字符串、字典、列表等）

    返回:
        (是否成功, 解析后的结构化数据, 错误码或空字符串)
    """
    if raw_input is None:
        return False, None, "E001"

    # 处理字符串输入：尝试解析 JSON，否则按纯文本处理
    if isinstance(raw_input, str):
        text = raw_input.strip()
        if not text:
            return False, None, "E001"
        try:
            # 尝试解析 JSON 结构化数据
            parsed = json.loads(text)
            return _validate_structured(parsed)
        except json.JSONDecodeError:
            # 非 JSON，按纯文本处理
            return _parse_plain_text(text)

    # 处理字典/列表输入
    if isinstance(raw_input, (dict, list)):
        return _validate_structured(raw_input)

    return False, None, "E003"


def _validate_structured(data: Any) -> Tuple[bool, Any, str]:
    """验证并规范化结构化输入。"""
    if isinstance(data, dict):
        # 检查是否有足够的有效字段
        if len(data) == 0:
            return False, None, "E002"
        # 过滤空值字段
        cleaned = {k: v for k, v in data.items() if v is not None and v != ""}
        if not cleaned:
            return False, None, "E002"
        return True, cleaned, ""
    elif isinstance(data, list):
        if len(data) == 0:
            return False, None, "E002"
        valid_items = []
        for item in data:
            if item is None or item == "":
                continue
            valid_items.append(item)
        if not valid_items:
            return False, None, "E002"
        return True, valid_items, ""
    return False, None, "E003"


def _parse_plain_text(text: str) -> Tuple[bool, Any, str]:
    """
    解析纯文本输入，提取关键信息。

    规则：
    - 按行拆分，每行作为一个条目
    - 尝试识别 "键: 值" 格式
    - 无明显结构的按纯文本条目处理
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False, None, "E002"

    structured_items = []
    for line in lines:
        # 尝试识别 "键: 值" 或 "键=值" 格式
        for sep in (":", "="):
            if sep in line:
                parts = line.split(sep, 1)
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value:
                    structured_items.append({"key": key, "value": value})
                    break
        else:
            # 无键值结构，按纯文本条目处理
            structured_items.append({"text": line})

    if not structured_items:
        return False, None, "E002"

    return True, structured_items, ""


# ---------------------------------------------------------------------------
# 核心逻辑：置信度评估
# ---------------------------------------------------------------------------
def evaluate_confidence(data: Any) -> Tuple[float, str]:
    """
    评估结构化数据的置信度。

    规则：
    - 结构化字段完整（有键值对且非空）：≥90%
    - 有部分空字段或结构松散：85%-90%
    - 纯文本无结构：<85%
    """
    if isinstance(data, dict):
        total_fields = len(data)
        if total_fields == 0:
            return 0.0, "无有效字段"
        # 计算非空字段占比
        non_empty = sum(1 for v in data.values() if v is not None and v != "")
        ratio = non_empty / total_fields
        if ratio >= 0.9:
            return 0.92, ""
        elif ratio >= 0.7:
            return 0.87, "建议复核"
        else:
            return 0.80, "部分字段缺失"

    elif isinstance(data, list):
        if len(data) == 0:
            return 0.0, "空列表"
        # 检查列表元素的完整性
        valid_count = sum(1 for item in data if item is not None and item != "")
        ratio = valid_count / len(data)
        if ratio >= 0.9:
            return 0.90, ""
        elif ratio >= 0.7:
            return 0.86, "部分条目为空"
        else:
            return 0.78, "多数条目为空"

    return 0.80, "非结构化数据"


# ---------------------------------------------------------------------------
# 核心逻辑：输出生成
# ---------------------------------------------------------------------------
def generate_output(data: Any, confidence: float, note: str) -> Dict[str, Any]:
    """
    按约定格式生成输出结果。

    输出结构：
    {
        "ok": true,
        "data": <结构化数据>,
        "confidence": <置信度 0-1>,
        "confidence_label": "高/中/低",
        "note": "补充说明",
        "requires_review": bool
    }
    """
    # 置信度标签（修正边界条件）
    if confidence >= 0.90:
        label = "高"
        requires_review = False
    elif confidence >= 0.85:
        label = "中"
        requires_review = True
    else:
        label = "低"
        requires_review = True

    result = {
        "ok": True,
        "data": data,
        "confidence": round(confidence, 2),
        "confidence_label": label,
        "note": note,
        "requires_review": requires_review,
    }

    # 低置信度时添加提示
    if confidence < 0.85:
        result["warning"] = "[需核实] 结果置信度较低，请人工复核关键信息。"

    return result


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_input(raw_input: Any) -> Dict[str, Any]:
    """
    标准处理流程：
    1. 解析输入
    2. 评估置信度
    3. 生成输出
    """
    # Step 1: 解析输入
    ok, parsed_data, error_code = parse_input(raw_input)
    if not ok:
        return make_error(error_code)

    # Step 2: 评估置信度
    confidence, note = evaluate_confidence(parsed_data)

    # Step 3: 生成输出
    return generate_output(parsed_data, confidence, note)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def process_batch(items: List[Any]) -> Dict[str, Any]:
    """
    批量处理多个输入项。

    参数:
        items: 输入项列表

    返回:
        批量处理结果
    """
    if not items:
        return make_error("E001")

    results = []
    for idx, item in enumerate(items):
        result = process_input(item)
        result["index"] = idx + 1
        results.append(result)

    # 统计批量处理概况
    success_count = sum(1 for r in results if r.get("ok"))
    total_count = len(results)

    return make_success(
        {
            "total": total_count,
            "success": success_count,
            "failed": total_count - success_count,
            "results": results,
        },
        confidence=success_count / total_count if total_count > 0 else 0,
    )


# ---------------------------------------------------------------------------
# 内置自检数据与测试
# ---------------------------------------------------------------------------
def _selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据离线验证核心逻辑。

    验证点：
    1. 正常结构化输入处理
    2. 纯文本输入处理
    3. 空输入错误处理
    4. 批量处理
    5. 置信度评估逻辑
    """
    print("[SELFTEST] 开始内置自检...")
    all_passed = True

    # 测试用例 1: 正常结构化输入（字典）
    print("[SELFTEST] 测试1: 结构化字典输入")
    test1_input = {"product": "RTX 3080 Ti", "price": 1199, "stock": "in_stock"}
    result1 = process_input(test1_input)
    assert result1.get("ok") is True, "结构化输入应返回 ok=True"
    assert "data" in result1, "结果应包含 data 字段"
    assert result1.get("confidence", 0) >= 0.85, "完整字典置信度应 >= 0.85"
    print("[SELFTEST] 测试1通过")

    # 测试用例 2: JSON 字符串输入
    print("[SELFTEST] 测试2: JSON 字符串输入")
    test2_input = json.dumps({"name": "测试商品", "sku": "ABC123"})
    result2 = process_input(test2_input)
    assert result2.get("ok") is True, "JSON 字符串应解析成功"
    assert result2["data"]["name"] == "测试商品", "应正确解析 name 字段"
    print("[SELFTEST] 测试2通过")

    # 测试用例 3: 纯文本输入
    print("[SELFTEST] 测试3: 纯文本输入")
    test3_input = "产品: RTX 3080\n价格: 999\n库存: 有货"
    result3 = process_input(test3_input)
    assert result3.get("ok") is True, "纯文本应解析成功"
    assert len(result3["data"]) == 3, "应解析出3个键值对"
    print("[SELFTEST] 测试3通过")

    # 测试用例 4: 空输入错误处理
    print("[SELFTEST] 测试4: 空输入错误")
    result4 = process_input("")
    assert result4.get("ok") is False, "空输入应返回 ok=False"
    assert result4.get("error_code") == "E001", "空输入应返回 E001"
    print("[SELFTEST] 测试4通过")

    # 测试用例 5: 批量处理
    print("[SELFTEST] 测试5: 批量处理")
    batch_input = [
        {"item": "GPU1", "price": 1500},
        {"item": "GPU2", "price": 1200},
        "纯文本条目",
        "",
    ]
    result5 = process_batch(batch_input)
    assert result5.get("ok") is True, "批量处理应成功"
    assert result5["data"]["total"] == 4, "应处理4个条目"
    assert result5["data"]["success"] == 3, "应成功3个条目（空条目失败）"
    assert result5["data"]["failed"] == 1, "应失败1个条目"
    print("[SELFTEST] 测试5通过")

    # 测试用例 6: 置信度分级
    print("[SELFTEST] 测试6: 置信度分级")
    
    # 高置信度（完整数据，所有字段非空）
    high_conf_input = {"a": 1, "b": 2, "c": 3}
    high_conf = process_input(high_conf_input)
    print(f"  完整字典数据置信度: {high_conf['confidence']}, 标签: {high_conf['confidence_label']}")
    assert high_conf["confidence"] >= 0.9, "完整数据置信度应 >= 0.9"
    assert high_conf["confidence_label"] == "高", "完整数据置信度标签应为高"
    
    # 中置信度（部分字段为空）
    mid_conf_input = {"a": 1, "b": "", "c": None}
    mid_conf = process_input(mid_conf_input)
    print(f"  稀疏字典数据置信度: {mid_conf['confidence']}, 标签: {mid_conf['confidence_label']}")
    assert 0.85 <= mid_conf["confidence"] < 0.9, "稀疏数据置信度应在 0.85-0.9 之间"
    assert mid_conf["confidence_label"] == "中", "稀疏数据置信度标签应为中"
    
    # 低置信度（纯文本无结构）
    low_conf_input = "一些没有结构的纯文本内容"
    low_conf = process_input(low_conf_input)
    print(f"  纯文本数据置信度: {low_conf['confidence']}, 标签: {low_conf['confidence_label']}")
    assert low_conf["confidence"] < 0.85, "纯文本置信度应 < 0.85"
    assert low_conf["confidence_label"] == "低", "纯文本置信度标签应为低"
    
    print("[SELFTEST] 测试6通过")

    # 测试用例 7: 错误码体系
    print("[SELFTEST] 测试7: 错误码")
    assert process_input(None).get("error_code") == "E001"
    assert process_input([]).get("error_code") == "E002"
    assert process_input(12345).get("error_code") == "E003"
    print("[SELFTEST] 测试7通过")

    # 测试用例 8: 输出格式完整性
    print("[SELFTEST] 测试8: 输出格式")
    result8 = process_input({"key": "value"})
    for field in ["ok", "data", "confidence", "confidence_label", "note", "requires_review"]:
        assert field in result8, f"输出缺少字段: {field}"
    print("[SELFTEST] 测试8通过")

    # 测试用例 9: 批量处理边界
    print("[SELFTEST] 测试9: 批量处理边界")
    assert process_batch([]).get("error_code") == "E001", "空批量应返回 E001"
    single_batch = process_batch(["单条"])
    assert single_batch["data"]["total"] == 1, "单条批量应处理1条"
    print("[SELFTEST] 测试9通过")

    # 测试用例 10: 异常输入处理
    print("[SELFTEST] 测试10: 异常输入")
    # 数字输入
    assert process_input(42).get("error_code") == "E003", "数字输入应返回 E003"
    # 布尔输入
    assert process_input(True).get("error_code") == "E003", "布尔输入应返回 E003"
    print("[SELFTEST] 测试10通过")

    print("[SELFTEST] 全部测试通过！")
    return all_passed


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="爬虫采集 - 输入内容结构化处理工具"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码数据，不访问外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（JSON 字符串或纯文本）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入（JSON 数组）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        passed = _selftest()
        return 0 if passed else 1

    # 处理输入
    if args.batch:
        # 批量处理模式
        try:
            items = json.loads(args.batch)
            if not isinstance(items, list):
                print(json.dumps(make_error("E003", "批量输入应为 JSON 数组"), ensure_ascii=False))
                return 1
            result = process_batch(items)
        except json.JSONDecodeError:
            print(json.dumps(make_error("E009", "批量输入 JSON 解析失败"), ensure_ascii=False))
            return 1
    elif args.input:
        # 单条处理模式
        result = process_input(args.input)
    else:
        # 无输入参数
        print(json.dumps(make_error("E001"), ensure_ascii=False))
        return 1

    # 输出结果
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 文本格式输出
        if result.get("ok"):
            print(f"处理成功 | 置信度: {result.get('confidence', 0):.0%}")
            print(f"数据: {json.dumps(result.get('data', {}), ensure_ascii=False)}")
            if result.get("requires_review"):
                print("⚠️ 建议复核")
        else:
            print(f"处理失败 | 错误码: {result.get('error_code', 'E010')}")
            print(f"详情: {result.get('detail', '')}")

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
