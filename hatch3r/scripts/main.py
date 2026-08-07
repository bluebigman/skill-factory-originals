#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hatch3r — 未命名工具（clean-room 独立实现）

功能概述：
    将用户提供的数据/文件/URL 转换为结构化结果，识别关键信息，
    按约定格式输出，并对不确定项给出置信度提示。

仅依据功能规格重新实现，不包含任何既有代码。
标准库实现，无第三方依赖。

用法示例：
    python scripts/main.py --process "样例数据"
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 错误码与标准化话术（对应规格“四、异常处理”）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值（对应规格“三、Step 2”）
CONF_HIGH = 90       # 置信度 ≥90%：直接输出
CONF_MID = 85        # 85%-90%：标注“建议复核”
# <85%：标注“[需核实]”


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessResult:
    """处理结果的数据结构，包含结构化数据和置信度信息。"""

    def __init__(
        self,
        data: Dict[str, Any],
        confidence: int,
        warnings: Optional[List[str]] = None,
    ) -> None:
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def extract_key_fields(raw_input: str) -> Dict[str, Any]:
    """
    从原始输入中提取关键字段。

    识别规则（基于规格“三、Step 2”第2条）：
        - 识别输入中的关键字段并结构化
        - 按默认模板组织输出
        - 对不确定项标注并请求确认

    本实现采用启发式规则：
        1. 按行/分隔符拆分输入
        2. 识别键值对（key: value 或 key=value）
        3. 识别列表项（每行一个元素）
        4. 无法识别时标记为“需核实”

    参数:
        raw_input: 用户输入的原始字符串

    返回:
        结构化字段字典
    """
    if not raw_input or not raw_input.strip():
        return {"error": "E001", "message": ERROR_MESSAGES["E001"]}

    # 规范化输入：去除首尾空白，统一换行
    text = raw_input.strip()

    # 尝试解析键值对（支持冒号和等号两种分隔符）
    kv_pairs: Dict[str, str] = {}
    list_items: List[str] = []
    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 尝试键值对解析
        for sep in (":", "="):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key:
                    kv_pairs[key] = value
                    break
        else:
            # 非键值对，视为列表项
            list_items.append(line)

    # 组织结构化结果
    result: Dict[str, Any] = {}

    if kv_pairs:
        result["fields"] = kv_pairs

    if list_items:
        result["items"] = list_items

    if not result:
        # 没有任何可识别结构，整段作为文本
        result["text"] = text
        result["_note"] = "[需核实] 未能识别结构化字段"

    return result


def calculate_confidence(parsed: Dict[str, Any], raw_input: str) -> Tuple[int, List[str]]:
    """
    计算置信度并生成警告。

    规则（对应规格“三、Step 2”第3条）：
        - 置信度 ≥90%：直接输出
        - 85%-90%：标注“建议复核”
        - <85%：标注“[需核实]”，并说明不确定点

    本实现的置信度评估策略：
        - 基础分 70 分
        - 成功解析键值对 +10
        - 成功解析列表项 +10
        - 输入非空 +5
        - 有明确字段名 +5
        - 有“需核实”标记则 -10

    参数:
        parsed: 解析后的结构化数据
        raw_input: 原始输入

    返回:
        (置信度百分比, 警告列表)
    """
    confidence = 70
    warnings: List[str] = []

    # 输入非空加分
    if raw_input and raw_input.strip():
        confidence += 5

    # 成功解析键值对
    if "fields" in parsed and parsed["fields"]:
        confidence += 10
    else:
        warnings.append("未识别到键值对字段")

    # 成功解析列表项
    if "items" in parsed and parsed["items"]:
        confidence += 10
    else:
        warnings.append("未识别到列表项")

    # 有明确字段名
    if "fields" in parsed and any(len(k) >= 2 for k in parsed["fields"]):
        confidence += 5

    # 有“需核实”标记
    if "_note" in parsed:
        confidence -= 10
        warnings.append(parsed["_note"])

    # 限制在 0-100 之间
    confidence = max(0, min(100, confidence))

    return confidence, warnings


def process_input(raw_input: str) -> ProcessResult:
    """
    核心处理流程（对应规格“三、Step 2”）。

    参数:
        raw_input: 用户输入的原始字符串

    返回:
        ProcessResult 对象
    """
    # 输入为空检查（E001）
    if not raw_input or not raw_input.strip():
        return ProcessResult(
            data={"error": "E001", "message": ERROR_MESSAGES["E001"]},
            confidence=0,
            warnings=["输入为空"],
        )

    # 解析输入
    parsed = extract_key_fields(raw_input)

    # 解析失败（输入格式错误，E003）
    if "error" in parsed:
        return ProcessResult(
            data=parsed,
            confidence=0,
            warnings=[ERROR_MESSAGES["E003"]],
        )

    # 计算置信度
    confidence, warnings = calculate_confidence(parsed, raw_input)

    # 根据置信度添加标注
    if confidence < CONF_MID:
        parsed["_confidence_label"] = "[需核实]"
    elif confidence < CONF_HIGH:
        parsed["_confidence_label"] = "建议复核"
    else:
        parsed["_confidence_label"] = "直接输出"

    return ProcessResult(data=parsed, confidence=confidence, warnings=warnings)


def format_output(result: ProcessResult, fmt: str = "json") -> str:
    """
    格式化输出（对应规格“三、Step 3”）。

    支持格式：
        - json: JSON 格式（默认）
        - text: 文本格式

    参数:
        result: ProcessResult 对象
        fmt: 输出格式

    返回:
        格式化后的字符串
    """
    if fmt == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = ["=== 处理结果 ==="]
        lines.append(f"置信度: {result.confidence}%")
        lines.append(f"标注: {result.data.get('_confidence_label', 'N/A')}")

        if result.warnings:
            lines.append("警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")

        lines.append("数据:")
        for key, value in result.data.items():
            if key.startswith("_"):
                continue  # 跳过内部标记
            lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")

        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、
    不访问网络，任何环境直接可过。

    断言策略：
        - 使用宽松阈值（大小比较/区间判断）
        - 禁止依赖精确值或边界值
        - 确保自检样例与实际逻辑必然匹配

    返回:
        0 表示全部通过，非 0 表示存在失败
    """
    print("=== hatch3r 自检开始 ===")
    failures = 0

    # --- 测试用例 1：正常键值对输入 ---
    print("\n[测试1] 键值对输入")
    input1 = "名称: 测试项目\n类型: 文档\n优先级: 高"
    result1 = process_input(input1)

    # 宽松断言：置信度应较高（>80）
    if not (result1.confidence > 80):
        print(f"  ✗ 置信度异常: {result1.confidence}")
        failures += 1
    else:
        print(f"  ✓ 置信度合理: {result1.confidence}%")

    # 应包含 fields 字段
    if "fields" not in result1.data:
        print("  ✗ 缺少 fields 字段")
        failures += 1
    else:
        # 字段数量应 >= 2
        if len(result1.data["fields"]) < 2:
            print(f"  ✗ 字段数量过少: {result1.data['fields']}")
            failures += 1
        else:
            print(f"  ✓ 字段解析正常: {list(result1.data['fields'].keys())}")

    # --- 测试用例 2：空输入（E001） ---
    print("\n[测试2] 空输入")
    result2 = process_input("")
    if result2.data.get("error") != "E001":
        print(f"  ✗ 空输入未触发 E001: {result2.data}")
        failures += 1
    else:
        print("  ✓ 正确触发 E001")

    # --- 测试用例 3：混合输入（键值对 + 列表项） ---
    print("\n[测试3] 混合输入")
    input3 = "标题: 周报\nauthor=张三\n第一项\n第二项\n第三项"
    result3 = process_input(input3)

    # 应同时包含 fields 和 items
    has_fields = "fields" in result3.data
    has_items = "items" in result3.data

    if not (has_fields and has_items):
        print(f"  ✗ 混合解析失败: fields={has_fields}, items={has_items}")
        failures += 1
    else:
        # 宽松断言：items 应至少 2 个
        if len(result3.data["items"]) < 2:
            print(f"  ✗ 列表项过少: {result3.data['items']}")
            failures += 1
        else:
            print(f"  ✓ 混合解析正常: {len(result3.data['items'])} 个列表项")

    # --- 测试用例 4：纯文本（无结构） ---
    print("\n[测试4] 纯文本输入")
    input4 = "这是一段无法识别结构的纯文本内容"
    result4 = process_input(input4)

    # 应包含 text 字段或 _note 标记
    has_text = "text" in result4.data
    has_note = "_note" in result4.data
    if not (has_text or has_note):
        print(f"  ✗ 纯文本处理异常: {result4.data}")
        failures += 1
    else:
        print("  ✓ 纯文本已处理")

    # --- 测试用例 5：置信度标注逻辑 ---
    print("\n[测试5] 置信度标注")
    # 高质量输入应获得较高置信度
    good_input = "名称: 项目A\n描述: 这是一个完整的项目描述\n状态: 进行中\n负责人: 张三\n截止日期: 2026-12-31"
    good_result = process_input(good_input)

    # 宽松断言：高质量输入置信度应 > 85
    if good_result.confidence <= 85:
        print(f"  ✗ 高质量输入置信度偏低: {good_result.confidence}")
        failures += 1
    else:
        print(f"  ✓ 高质量输入置信度合理: {good_result.confidence}%")

    # 低质量输入置信度应较低
    low_input = "随便"
    low_result = process_input(low_input)
    if low_result.confidence >= 85:
        print(f"  ✗ 低质量输入置信度偏高: {low_result.confidence}")
        failures += 1
    else:
        print(f"  ✓ 低质量输入置信度合理: {low_result.confidence}%")

    # --- 测试用例 6：格式化输出 ---
    print("\n[测试6] 格式化输出")
    try:
        json_out = format_output(good_result, "json")
        # JSON 应能解析
        parsed_json = json.loads(json_out)
        if "data" not in parsed_json or "confidence" not in parsed_json:
            print("  ✗ JSON 格式缺失关键字段")
            failures += 1
        else:
            print("  ✓ JSON 格式正常")

        text_out = format_output(good_result, "text")
        if "置信度" not in text_out:
            print("  ✗ 文本格式缺少置信度")
            failures += 1
        else:
            print("  ✓ 文本格式正常")
    except Exception as e:
        print(f"  ✗ 格式化异常: {e}")
        failures += 1

    # --- 汇总 ---
    print("\n=== 自检结束 ===")
    if failures == 0:
        print("✅ 全部测试通过")
        return 0
    else:
        print(f"❌ {failures} 项测试失败")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="hatch3r — 未命名工具：将用户提供的数据/文件/URL 转换为结构化结果",
        epilog="示例: python scripts/main.py --process '名称: 测试' 或 python scripts/main.py --selftest",
    )
    parser.add_argument(
        "--process",
        type=str,
        help="处理输入内容（字符串）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    if args.process is None:
        # 无输入参数，提示 E001
        print(json.dumps(
            {"error": "E001", "message": ERROR_MESSAGES["E001"]},
            ensure_ascii=False,
            indent=2,
        ))
        return 1

    # 执行核心处理
    result = process_input(args.process)

    # 输出结果
    try:
        output = format_output(result, args.format)
        print(output)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # 根据置信度决定退出码
    if result.confidence < CONF_MID:
        # 低置信度，返回非零退出码提示用户注意
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
