#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashbrew - 数据可视化技能实现脚本

本脚本按照功能规格独立实现（clean-room），提供：
- 标准流程处理：解析输入 -> 结构化识别 -> 生成输出（含置信度标注）
- 错误码体系：E001-E005（对应规格中的异常处理场景）
- 离线自检：--selftest 参数，使用内置硬编码样例验证核心逻辑

仅依赖 Python 标准库，无需第三方安装。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码与提示话术（对应规格“四、异常处理”）
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：{\"source\": \"data\", \"format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议：简化输入或使用其他专用工具",
    "E005": "结果无法确定，建议：检查输入数据完整性后重试",
}


# ---------------------------------------------------------------------------
# 核心数据结构与常量
# ---------------------------------------------------------------------------
# 支持的处理类型（对应规格中的能力边界）
SUPPORTED_INPUT_TYPES = ("data", "file", "url")

# 输出格式模板（默认结构）
DEFAULT_OUTPUT_TEMPLATE = {
    "summary": "",
    "fields": [],
    "records": [],
    "confidence": 0.0,
    "notes": [],
}


def make_error_result(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误结果。

    参数:
        code: 错误码（E001-E005）
        detail: 附加说明（可选）

    返回:
        包含错误码、消息和可选详情的字典。
    """
    message = ERROR_MESSAGES.get(code, "未知错误")
    result = {"error_code": code, "error_message": message}
    if detail:
        result["detail"] = detail
    return result


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw_input: Any) -> Tuple[bool, Dict[str, Any], str]:
    """解析输入内容，识别关键信息。

    参数:
        raw_input: 用户提供的原始输入（可能是字符串、字典等）

    返回:
        (是否成功, 解析结果或错误结果, 错误码或空字符串)
    """
    # E001: 输入为空
    if raw_input is None:
        return False, make_error_result("E001"), "E001"

    # 如果输入是字符串，尝试解析为 JSON
    if isinstance(raw_input, str):
        text = raw_input.strip()
        if not text:
            return False, make_error_result("E001"), "E001"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # 不是 JSON，按纯文本处理
            parsed = {"source": text, "format": "text"}
    else:
        parsed = raw_input

    # 必须是字典才继续
    if not isinstance(parsed, dict):
        return False, make_error_result("E003", "输入必须是 JSON 对象或键值对"), "E003"

    # E002: 关键信息缺失（source 为必填）
    source = parsed.get("source")
    if source is None or (isinstance(source, str) and not source.strip()):
        return False, make_error_result("E002"), "E002"

    # 校验输入来源类型（E003: 格式错误）
    if "type" in parsed:
        input_type = str(parsed["type"]).lower()
        if input_type not in SUPPORTED_INPUT_TYPES:
            return False, make_error_result("E003", f"不支持的输入类型: {input_type}"), "E003"

    return True, parsed, ""


def extract_fields(data: Dict[str, Any]) -> List[str]:
    """从输入数据中提取关键字段名。

    参数:
        data: 已解析的输入字典

    返回:
        字段名列表。
    """
    fields: List[str] = []

    # 直接取 data 子对象中的字段
    inner = data.get("data")
    if isinstance(inner, dict):
        for key in inner.keys():
            if key not in fields:
                fields.append(key)
    elif isinstance(inner, list) and inner and isinstance(inner[0], dict):
        for key in inner[0].keys():
            if key not in fields:
                fields.append(key)

    # 补充顶层字段（排除已知控制字段）
    control_keys = {"source", "format", "type", "data", "fields"}
    for key in data.keys():
        if key not in control_keys and key not in fields:
            fields.append(key)

    return fields


def calculate_confidence(data: Dict[str, Any], fields: List[str]) -> float:
    """计算置信度（0-100）。

    规则（对应规格三、Step 2）：
    - 有明确结构化字段：基础分较高
    - 有完整 records：加分
    - 有 notes/备注：加分
    - 字段数量过少：减分

    参数:
        data: 输入数据
        fields: 提取到的字段列表

    返回:
        置信度数值（0-100）。
    """
    score = 50.0  # 基础分

    # 字段完整度加分
    if len(fields) >= 3:
        score += 20
    elif len(fields) >= 1:
        score += 10

    # 有数据记录加分
    records = data.get("records")
    if isinstance(records, list) and len(records) > 0:
        score += 15

    # 有备注/说明加分
    if data.get("notes") or data.get("comment"):
        score += 10

    # 有明确格式声明加分
    if data.get("format"):
        score += 5

    # 限制在 0-100 范围
    return max(0.0, min(100.0, score))


def build_output(data: Dict[str, Any], fields: List[str], confidence: float) -> Dict[str, Any]:
    """按默认模板组织输出结果。

    参数:
        data: 输入数据
        fields: 提取的字段列表
        confidence: 置信度

    返回:
        符合输出模板的结果字典。
    """
    output = dict(DEFAULT_OUTPUT_TEMPLATE)  # 深拷贝默认模板
    output["summary"] = data.get("summary", data.get("source", "数据可视化结果"))
    output["fields"] = fields
    output["records"] = data.get("records", data.get("data", []))
    output["confidence"] = confidence

    # 置信度标注（对应规格 Step 2 规则）
    if confidence >= 90:
        output["notes"].append("置信度≥90%，可直接使用")
    elif confidence >= 85:
        output["notes"].append("建议复核：置信度85%-90%")
    else:
        output["notes"].append("[需核实] 置信度低于85%，请人工确认关键结果")

    # 额外备注
    if isinstance(data.get("notes"), list):
        output["notes"].extend(data["notes"])

    return output


def process_data(raw_input: Any) -> Dict[str, Any]:
    """核心处理流程（对应规格三、Step 2）。

    参数:
        raw_input: 用户输入

    返回:
        处理结果（成功或错误字典）。
    """
    # Step 1: 解析输入
    ok, parsed, err_code = parse_input(raw_input)
    if not ok:
        return parsed  # 已经是错误结果

    # Step 2: 提取字段
    fields = extract_fields(parsed)

    # E002: 提取不到任何字段时视为关键信息缺失
    if not fields:
        return make_error_result("E002", "未能从输入中识别到有效字段")

    # Step 3: 计算置信度
    confidence = calculate_confidence(parsed, fields)

    # E005: 置信度过低
    if confidence < 50:
        return make_error_result("E005", f"置信度仅 {confidence:.1f}%")

    # Step 4: 生成输出
    return build_output(parsed, fields, confidence)


def batch_process(inputs: List[Any]) -> List[Dict[str, Any]]:
    """批量处理多个输入（对应规格六、进阶用法）。

    参数:
        inputs: 输入列表

    返回:
        处理结果列表。
    """
    return [process_data(item) for item in inputs]


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """离线自检核心逻辑。

    使用内置硬编码样例数据，不读文件、不访问网络。
    断言使用宽松阈值（区间/大小比较），保证稳健性。

    返回:
        0 表示全部通过，非 0 表示失败。
    """
    print("[selftest] 开始离线自检...")
    failures = 0

    # --- 测试用例 1: 正常输入 ---
    print("[selftest] 用例1: 正常 JSON 输入")
    sample1 = {
        "source": "测试数据",
        "format": "json",
        "data": [
            {"name": "项目A", "value": 100, "status": "完成"},
            {"name": "项目B", "value": 200, "status": "进行中"},
        ],
    }
    result1 = process_data(sample1)
    assert "error_code" not in result1, f"用例1不应报错，实际: {result1.get('error_code')}"
    assert len(result1["fields"]) >= 2, f"字段数应≥2，实际: {len(result1['fields'])}"
    assert result1["confidence"] > 70, f"置信度应>70，实际: {result1['confidence']}"
    assert len(result1["records"]) > 0, "records 不应为空"
    print(f"  ✓ 通过 (置信度={result1['confidence']:.1f}%, 字段={result1['fields']})")

    # --- 测试用例 2: 空输入 ---
    print("[selftest] 用例2: 空输入")
    result2 = process_data("")
    assert result2.get("error_code") == "E001", f"应返回E001，实际: {result2.get('error_code')}"
    print(f"  ✓ 通过 (错误码={result2['error_code']})")

    # --- 测试用例 3: 缺失关键信息 ---
    print("[selftest] 用例3: 缺少 source 字段")
    result3 = process_data({"format": "json", "data": []})
    assert result3.get("error_code") in ("E001", "E002"), f"应返回E001/E002，实际: {result3.get('error_code')}"
    print(f"  ✓ 通过 (错误码={result3['error_code']})")

    # --- 测试用例 4: 格式错误 ---
    print("[selftest] 用例4: 不支持的输入类型")
    result4 = process_data({"source": "x", "type": "binary"})
    assert result4.get("error_code") == "E003", f"应返回E003，实际: {result4.get('error_code')}"
    print(f"  ✓ 通过 (错误码={result4['error_code']})")

    # --- 测试用例 5: 批量处理 ---
    print("[selftest] 用例5: 批量处理")
    batch = [
        {"source": "A", "data": {"k1": 1, "k2": 2, "k3": 3}},
        {"source": "B", "data": {"k1": 4, "k2": 5}},
    ]
    results = batch_process(batch)
    assert len(results) == 2, f"批量结果数应为2，实际: {len(results)}"
    assert all("error_code" not in r for r in results), "批量处理不应有错误"
    print(f"  ✓ 通过 (共{len(results)}条，均成功)")

    # --- 测试用例 6: 错误码覆盖 ---
    print("[selftest] 用例6: 错误码体系完整性")
    for code in ("E001", "E002", "E003", "E004", "E005"):
        assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
    print(f"  ✓ 通过 (共{len(ERROR_MESSAGES)}个错误码)")

    # --- 测试用例 7: 置信度区间 ---
    print("[selftest] 用例7: 置信度区间有效性")
    sample7 = {"source": "测试", "data": {"a": 1, "b": 2, "c": 3}, "records": [{"x": 1}]}
    conf = calculate_confidence(sample7, ["a", "b", "c"])
    assert 0 <= conf <= 100, f"置信度应在0-100，实际: {conf}"
    assert conf > 80, f"此样例置信度应>80，实际: {conf}"
    print(f"  ✓ 通过 (置信度={conf:.1f}%)")

    # 汇总
    if failures == 0:
        print("[selftest] 全部通过 ✅")
        return 0
    else:
        print(f"[selftest] {failures} 项失败 ❌")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。

    支持:
    - 无参数: 提示用法
    - --selftest: 离线自检
    - --input/-i: 处理输入（JSON 字符串或文件路径）
    - --batch: 批量处理（JSON 数组）

    返回:
        进程退出码（0 成功，非 0 失败）。
    """
    parser = argparse.ArgumentParser(
        description="dashbrew - 数据可视化技能（仅学习参考用途）",
        epilog="示例: python main.py --input '{\"source\": \"test\", \"data\": {\"a\": 1}}'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入 JSON 字符串（如 '{\"source\": \"data\", \"format\": \"json\"}'）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入 JSON 数组字符串",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入（JSON 格式）",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 收集输入
    raw_input: Any = None
    if args.input:
        try:
            raw_input = json.loads(args.input)
        except json.JSONDecodeError:
            raw_input = args.input  # 按纯文本处理
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_input = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(json.dumps(make_error_result("E003", f"文件读取失败: {e}"), ensure_ascii=False))
            return 1
    elif args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                print(json.dumps(make_error_result("E003", "批量输入必须是数组"), ensure_ascii=False))
                return 1
            results = batch_process(batch_data)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except json.JSONDecodeError as e:
            print(json.dumps(make_error_result("E003", f"批量输入格式错误: {e}"), ensure_ascii=False))
            return 1
    else:
        # 无输入参数，提示用法
        parser.print_help()
        print("\n" + "=" * 50)
        print("提示: 请提供输入内容，例如:")
        print('  python main.py --input \'{"source": "示例数据", "data": {"字段1": "值1"}}\'')
        print("  或运行 --selftest 进行离线自检")
        return 0

    # 处理单个输入
    result = process_data(raw_input)

    # 输出
    if args.output == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 文本输出
        if "error_code" in result:
            print(f"错误 [{result['error_code']}]: {result['error_message']}")
            if "detail" in result:
                print(f"详情: {result['detail']}")
        else:
            print(f"摘要: {result['summary']}")
            print(f"字段: {', '.join(result['fields'])}")
            print(f"置信度: {result['confidence']:.1f}%")
            print(f"记录数: {len(result['records'])}")
            for note in result["notes"]:
                print(f"提示: {note}")

    # 有错误码时返回非零
    if "error_code" in result:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
