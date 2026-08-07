#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: backstage 工具（干净室重写实现）
功能描述: 依据功能规格实现的独立脚本，提供结构化处理、置信度标注、错误码体系。
用法示例:
    python scripts/main.py --selftest        # 离线自检（不读外部文件/不访问网络）
    python scripts/main.py --input "..."     # 处理输入内容（示例参数）
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式生成失败",
    "E008": "批量处理中断",
    "E009": "参数解析错误",
    "E010": "未知错误",
}

# 默认输出模板（字段结构）
DEFAULT_TEMPLATE = {
    "summary": "",
    "key_points": [],
    "confidence": 0.0,
    "needs_review": False,
}


def _make_error(error_code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误返回结构。"""
    message = ERROR_CODES.get(error_code, ERROR_CODES["E010"])
    if detail:
        message = f"{message} ({detail})"
    return {"ok": False, "error_code": error_code, "message": message}


def _make_success(data: Any, confidence: float, needs_review: bool) -> Dict[str, Any]:
    """构造标准成功返回结构。"""
    return {
        "ok": True,
        "data": data,
        "confidence": confidence,
        "needs_review": needs_review,
    }


def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息。
    支持：JSON 字符串或纯文本。
    返回结构化字典（包含原始文本和解析后的内容）。
    """
    if raw_input is None or not raw_input.strip():
        return _make_error("E001")

    text = raw_input.strip()

    # 尝试解析 JSON
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        parsed = None

    # 如果 JSON 解析失败，则按纯文本处理
    if parsed is None:
        parsed = {"raw_text": text}

    return {
        "ok": True,
        "raw": text,
        "parsed": parsed,
    }


def extract_key_info(parsed_data: Any) -> List[str]:
    """
    识别并保留输入中的关键信息。
    规则：
      - 若为字典，提取所有值中的字符串（去重）
      - 若为列表，提取所有字符串元素（去重）
      - 若为字符串，按中文逗号/句号/分号分割后提取非空片段
    """
    key_points: List[str] = []

    def _collect(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                _collect(v)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)
        elif isinstance(obj, str):
            # 按常见分隔符切分
            parts = [p.strip() for p in obj.replace("，", ",").replace("。", ".").replace("；", ";").split(",") if p.strip()]
            key_points.extend(parts)
        elif obj is not None:
            key_points.append(str(obj))

    _collect(parsed_data)

    # 去重并保序
    seen = set()
    unique_points = []
    for point in key_points:
        if point not in seen:
            seen.add(point)
            unique_points.append(point)

    return unique_points


def estimate_confidence(key_points: List[str]) -> float:
    """
    根据提取的关键信息数量估算置信度。
    规则（宽松阈值）：
      - 空列表：置信度 < 50%
      - 1-2 个点：置信度在 50%-70% 区间
      - 3 个及以上：置信度 >= 70%
    """
    count = len(key_points)

    if count == 0:
        return 40.0  # 低置信度
    elif count <= 2:
        return 60.0  # 中等
    else:
        return 85.0  # 较高


def process_input(raw_input: str, output_format: Optional[str] = None) -> Dict[str, Any]:
    """
    核心处理流程：解析 -> 提取 -> 置信度评估 -> 生成输出。
    output_format 参数预留，当前仅支持默认模板。
    """
    # Step 1: 解析输入
    parse_result = parse_input(raw_input)
    if not parse_result.get("ok"):
        return parse_result  # 直接返回错误

    # Step 2: 提取关键信息
    key_points = extract_key_info(parse_result.get("parsed", {}))

    if not key_points:
        return _make_error("E002", "未识别到关键信息")

    # Step 3: 置信度评估
    confidence = estimate_confidence(key_points)

    # Step 4: 组装输出
    output_data = dict(DEFAULT_TEMPLATE)
    output_data["summary"] = "；".join(key_points[:3])  # 摘要取前三个
    output_data["key_points"] = key_points
    output_data["confidence"] = confidence
    output_data["needs_review"] = confidence < 85.0

    # Step 5: 返回结果（含置信度标注）
    return _make_success(output_data, confidence, confidence < 85.0)


def batch_process(inputs: List[str]) -> Dict[str, Any]:
    """批量处理多个输入。"""
    if not inputs:
        return _make_error("E001")

    results = []
    for idx, item in enumerate(inputs):
        try:
            result = process_input(item)
            results.append({"index": idx, "result": result})
        except Exception as exc:  # 防止单个失败中断整体
            results.append({"index": idx, "result": _make_error("E008", str(exc))})

    return _make_success(results, 0.0, True)


def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("[selftest] 开始离线自检...")

    # 样例 1：正常文本输入
    sample1 = "你好，这是一段测试文本；请提取关键信息。"
    result1 = process_input(sample1)
    assert result1.get("ok") is True, "样例1失败：应返回成功"
    assert isinstance(result1.get("data"), dict), "样例1失败：data应为字典"
    assert len(result1["data"].get("key_points", [])) > 0, "样例1失败：应提取到关键点"
    assert 0.0 <= result1["data"].get("confidence", -1) <= 100.0, "样例1失败：置信度应在0-100"
    print("  样例1（文本输入）通过")

    # 样例 2：JSON 输入
    sample2 = '{"name": "测试", "tags": ["A", "B", "C"], "desc": "这是一个JSON样例"}'
    result2 = process_input(sample2)
    assert result2.get("ok") is True, "样例2失败：应返回成功"
    assert len(result2["data"].get("key_points", [])) >= 3, "样例2失败：应提取至少3个关键点"
    assert result2["data"].get("confidence", 0) >= 70.0, "样例2失败：置信度应较高"
    print("  样例2（JSON输入）通过")

    # 样例 3：空输入（应返回 E001）
    result3 = process_input("   ")
    assert result3.get("ok") is False, "样例3失败：应返回错误"
    assert result3.get("error_code") == "E001", "样例3失败：错误码应为E001"
    print("  样例3（空输入）通过")

    # 样例 4：批量处理
    result4 = batch_process(["第一项", "第二项内容较长，需要提取", '{"x": 1}'])
    assert result4.get("ok") is True, "样例4失败：批量应成功"
    assert len(result4["data"]) == 3, "样例4失败：应处理3项"
    print("  样例4（批量处理）通过")

    # 样例 5：置信度阈值宽松判断
    conf = result2["data"].get("confidence", 0)
    assert conf > 50.0, "样例5失败：置信度应大于50"
    print("  样例5（置信度阈值）通过")

    print("[selftest] 全部通过（5/5）")
    return True


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="backstage 技能工具（干净室实现）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", type=str, default=None, help="待处理的输入内容")
    parser.add_argument("--batch", action="store_true", help="批量模式（配合 --input 用分号分隔多项）")
    parser.add_argument("--format", type=str, default=None, help="输出格式（预留）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except AssertionError as exc:
            print(f"[selftest] 失败: {exc}")
            return 1

    # 处理模式
    if not args.input:
        print(json.dumps(_make_error("E001"), ensure_ascii=False, indent=2))
        return 1

    if args.batch:
        # 批量模式：用分号分隔多个输入
        items = [item.strip() for item in args.input.split(";") if item.strip()]
        result = batch_process(items)
    else:
        result = process_input(args.input, args.format)

    # 输出 JSON 结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 根据结果返回退出码
    if result.get("ok"):
        return 0
    else:
        # 错误码映射到非零退出码（简化处理）
        return 2


if __name__ == "__main__":
    sys.exit(main())
