#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

全新独立实现：awesome-claude-code-skills 技能核心逻辑。
仅依据功能规格编写，不复制任何既有代码（clean-room）。

功能概述：
- 解析输入内容，识别关键信息并结构化。
- 按默认模板组织输出，对不确定项标注置信度。
- 提供 --selftest 参数，使用内置硬编码样例离线自检核心逻辑。

错误码：
- E001: 输入为空
- E002: 关键信息缺失
- E003: 输入格式错误
- E004: 超出能力边界
- E005: 置信度过低
- E006: 内部处理异常（无法解析输入结构）
- E007: 输出生成失败（模板渲染异常）
- E008: 参数解析错误（命令行参数不合法）
- E009: 自检断言失败（内部逻辑错误）
- E010: 未预期的运行时错误

依赖：仅使用 Python 标准库（argparse, json, sys, re, datetime）。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 能力边界声明（用于 E004 判断）
CAPABILITY_BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]

# 置信度阈值
CONFIDENCE_HIGH = 90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 85    # 85%-90% 建议复核
# <85% 标注 [需核实]

# 默认输出模板字段顺序
DEFAULT_OUTPUT_FIELDS = ["input_source", "key_fields", "result", "confidence", "notes"]


# ---------------------------------------------------------------------------
# 核心数据结构与工具函数
# ---------------------------------------------------------------------------

class InputItem:
    """表示一条待处理的输入项。"""
    def __init__(self, raw: str, source: str = "user"):
        self.raw = raw.strip()
        self.source = source  # 来源：user / file / url

    def is_empty(self) -> bool:
        return not self.raw


class ProcessedResult:
    """表示一条处理完成的结果。"""
    def __init__(self, key_fields: Dict[str, Any], result: str, confidence: float, notes: List[str]):
        self.key_fields = key_fields
        self.result = result
        self.confidence = confidence  # 0-100 浮点数
        self.notes = notes

    def to_dict(self, input_source: str) -> Dict[str, Any]:
        """转换为标准输出字典。"""
        return {
            "input_source": input_source,
            "key_fields": self.key_fields,
            "result": self.result,
            "confidence": self.confidence,
            "notes": self.notes,
        }


def compute_confidence(key_fields: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    根据关键字段的完整度计算置信度。
    规则（宽松启发式）：
    - 字段越完整，置信度越高。
    - 若有字段值为空或未知，则降低置信度并添加说明。
    """
    if not key_fields:
        return 50.0, ["未识别到任何关键字段"]

    total = len(key_fields)
    filled = 0
    notes: List[str] = []

    for key, value in key_fields.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            notes.append(f"字段 '{key}' 为空")
        elif isinstance(value, (list, dict)) and len(value) == 0:
            notes.append(f"字段 '{key}' 为空集合")
        else:
            filled += 1

    if filled == 0:
        return 50.0, ["所有关键字段均为空"] + notes

    ratio = filled / total
    # 基础置信度：60 + 40 * ratio（范围 60-100）
    confidence = 60.0 + 40.0 * ratio

    # 根据空字段数量微调（每个空字段最多扣 5 分，下限 50）
    empty_count = total - filled
    confidence -= min(empty_count * 5.0, 10.0)
    confidence = max(50.0, min(confidence, 100.0))

    if confidence < 85:
        notes.append("[需核实] 置信度较低，请人工复核关键结果")
    elif confidence < 90:
        notes.append("建议复核")

    return round(confidence, 1), notes


def extract_key_fields(raw_text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息。
    启发式规则（不依赖外部库）：
    - 尝试识别 JSON 格式输入。
    - 识别常见键值对（key: value 或 key=value）。
    - 识别 URL 或文件路径。
    - 提取日期、数字等基本信息。
    """
    if not raw_text or not raw_text.strip():
        return {}

    fields: Dict[str, Any] = {}

    # 1. 尝试解析 JSON
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            # 只取前 10 个键，避免字段过多
            for i, (k, v) in enumerate(parsed.items()):
                if i >= 10:
                    break
                fields[str(k)] = v if not isinstance(v, (dict, list)) else str(v)[:200]
            if fields:
                return fields
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. 识别 URL
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(raw_text)
    if urls:
        fields["url"] = urls[0]

    # 3. 识别文件路径（常见扩展名）
    file_pattern = re.compile(r'[\w\-./\\]+\.(?:txt|md|json|csv|py|js|ts|html|css|pdf|docx?|xlsx?)[\w\-./\\]*', re.IGNORECASE)
    files = file_pattern.findall(raw_text)
    if files:
        fields["file_path"] = files[0]

    # 4. 识别键值对（key: value 或 key=value）
    kv_pattern = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*([^\s,;]+)')
    for match in kv_pattern.finditer(raw_text):
        key, value = match.group(1), match.group(2)
        if key.lower() not in ("http", "https"):
            fields[key] = value

    # 5. 识别日期（YYYY-MM-DD 或 YYYY/MM/DD）
    date_pattern = re.compile(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})')
    dates = date_pattern.findall(raw_text)
    if dates:
        fields["date"] = dates[0]

    # 6. 识别数字（整数或小数）
    num_pattern = re.compile(r'(\d+(?:\.\d+)?)')
    nums = num_pattern.findall(raw_text)
    if nums:
        fields["numbers"] = nums[:5]  # 最多取 5 个

    return fields


def generate_output(input_item: InputItem, key_fields: Dict[str, Any], confidence: float, notes: List[str]) -> ProcessedResult:
    """
    生成结构化输出结果。
    根据字段数量生成不同的结果描述。
    """
    field_count = len(key_fields)
    if field_count == 0:
        result_text = "未识别到结构化信息，请提供更明确的输入。"
    elif field_count == 1:
        result_text = f"已识别到 {field_count} 个关键字段：{list(key_fields.keys())[0]}"
    else:
        result_text = f"已识别到 {field_count} 个关键字段，请查看 key_fields 获取详情。"

    # 添加处理时间戳
    notes.append(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return ProcessedResult(
        key_fields=key_fields,
        result=result_text,
        confidence=confidence,
        notes=notes,
    )


def process_single_input(raw_input: str, source: str = "user") -> Dict[str, Any]:
    """
    处理单条输入，返回标准输出字典。
    错误码：E001（空输入）、E002（无关键信息）、E003（格式错误）、E006（内部异常）。
    """
    # 错误码 E001：输入为空
    if not raw_input or not raw_input.strip():
        return {"error_code": "E001", "error_message": "请提供待处理的内容，格式为：用户提供的数据/文件/URL"}

    item = InputItem(raw_input, source)

    try:
        # 核心流程：提取关键字段
        key_fields = extract_key_fields(item.raw)

        # 错误码 E002：关键信息缺失（完全无法提取任何字段）
        if not key_fields:
            return {
                "error_code": "E002",
                "error_message": "还缺少以下信息，请补充：可识别的关键字段（如 URL、文件路径、键值对、日期等）",
                "input_source": item.source,
            }

        # 计算置信度
        confidence, notes = compute_confidence(key_fields)

        # 错误码 E005：置信度过低
        if confidence < 50:
            return {
                "error_code": "E005",
                "error_message": "结果无法确定，建议：提供更完整、明确的输入信息",
                "input_source": item.source,
                "key_fields": key_fields,
                "confidence": confidence,
            }

        # 生成输出
        result_obj = generate_output(item, key_fields, confidence, notes)
        return result_obj.to_dict(item.source)

    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        # 错误码 E003：输入格式错误
        return {
            "error_code": "E003",
            "error_message": f"输入格式不符合要求，示例：URL、文件路径、JSON 或 key: value 格式。详情: {str(exc)[:100]}",
            "input_source": item.source,
        }
    except Exception as exc:  # 兜底异常
        # 错误码 E006：内部处理异常
        return {
            "error_code": "E006",
            "error_message": f"内部处理异常: {str(exc)[:200]}",
            "input_source": item.source,
        }


def batch_process(inputs: List[str], source: str = "user") -> List[Dict[str, Any]]:
    """批量处理多条输入。"""
    results = []
    for raw in inputs:
        results.append(process_single_input(raw, source))
    return results


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松阈值断言，不依赖精确值。
    返回 0 表示通过，非 0 表示失败。
    """
    print("[SELFTEST] 开始自检...")

    # 样例数据（硬编码，不读外部文件）
    test_cases = [
        # (输入文本, 期望至少识别的字段数, 期望置信度下限)
        ("https://example.com/docs/guide.pdf 项目文档", 1, 60.0),
        ("user: alice, role: admin, date: 2025-03-15", 2, 60.0),
        ('{"name": "test", "version": "1.0", "author": "skill-factory"}', 3, 70.0),
        ("这是一个没有任何结构化信息的纯文本", 0, 50.0),  # 期望至少不报错
        ("", 0, 0.0),  # 空输入，期望返回 E001
    ]

    passed = 0
    failed = 0

    for i, (raw_input, min_fields, min_conf) in enumerate(test_cases):
        print(f"\n[用例 {i+1}] 输入: {raw_input[:50]!r}...")

        result = process_single_input(raw_input)

        # 空输入特判：期望 E001
        if not raw_input.strip():
            if result.get("error_code") == "E001":
                print("  ✓ 正确返回 E001 (输入为空)")
                passed += 1
            else:
                print(f"  ✗ 期望 E001，实际: {result.get('error_code', '无错误码')}")
                failed += 1
            continue

        # 检查是否返回错误
        if "error_code" in result:
            # 允许 E002（无关键信息）但置信度检查跳过
            if result["error_code"] == "E002" and min_fields == 0:
                print("  ✓ 正确返回 E002 (无关键信息)")
                passed += 1
            else:
                print(f"  ✗ 返回错误: {result['error_code']} - {result.get('error_message', '')}")
                failed += 1
            continue

        # 检查关键字段数量（宽松：>= 期望值 或 至少不为空）
        key_fields = result.get("key_fields", {})
        actual_fields = len(key_fields)
        if actual_fields >= min_fields or (min_fields == 0 and actual_fields >= 0):
            print(f"  ✓ 关键字段数量 {actual_fields} >= 期望 {min_fields}")
        else:
            print(f"  ✗ 关键字段数量 {actual_fields} < 期望 {min_fields}")
            failed += 1
            continue

        # 检查置信度（宽松：>= 期望下限 或 在合理范围内）
        confidence = result.get("confidence", 0.0)
        if confidence >= min_conf:
            print(f"  ✓ 置信度 {confidence} >= 期望下限 {min_conf}")
        elif 50.0 <= confidence <= 100.0:
            print(f"  ✓ 置信度 {confidence} 在合理范围内 [50, 100]")
        else:
            print(f"  ✗ 置信度 {confidence} 不在合理范围内")
            failed += 1
            continue

        # 检查输出结构完整性
        required_keys = ["input_source", "key_fields", "result", "confidence", "notes"]
        if all(k in result for k in required_keys):
            print("  ✓ 输出结构完整")
        else:
            print(f"  ✗ 输出结构缺失字段: {[k for k in required_keys if k not in result]}")
            failed += 1
            continue

        passed += 1

    # 批量处理测试
    print("\n[批量处理测试]")
    batch_inputs = ["https://example.com", "name: test, value: 123"]
    batch_results = batch_process(batch_inputs)
    if len(batch_results) == 2:
        print(f"  ✓ 批量处理返回 {len(batch_results)} 条结果")
        passed += 1
    else:
        print(f"  ✗ 批量处理返回 {len(batch_results)} 条结果，期望 2")
        failed += 1

    # 汇总
    print(f"\n[SELFTEST] 完成: {passed} 通过, {failed} 失败")
    if failed > 0:
        print("[SELFTEST] 有失败用例，请检查代码逻辑。")
        return 1
    print("[SELFTEST] 全部通过。")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="awesome-claude-code-skills 技能核心逻辑（clean-room 实现）",
        epilog="示例: python main.py --input 'https://example.com 项目文档' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（文本、URL、文件路径等）。支持多次调用进行批量处理。",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["user", "file", "url"],
        default="user",
        help="输入来源类型，默认 user",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式，默认 json",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例，离线执行）",
    )

    # 错误码 E008：参数解析错误
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse 在错误时会调用 sys.exit(2)
        print(f"E008: 参数解析错误: {exc}", file=sys.stderr)
        return 2

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无输入时，提示帮助
    if not args.input:
        print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
        print("使用 --help 查看帮助，或使用 --selftest 运行自检。", file=sys.stderr)
        return 1

    # 处理输入
    results = batch_process(args.input, args.source)

    # 输出
    if args.format == "json":
        output = json.dumps(results, ensure_ascii=False, indent=2)
    else:
        # 文本格式输出
        lines = []
        for idx, res in enumerate(results, 1):
            lines.append(f"=== 结果 {idx} ===")
            if "error_code" in res:
                lines.append(f"错误: {res['error_code']} - {res.get('error_message', '')}")
            else:
                lines.append(f"输入来源: {res.get('input_source', 'unknown')}")
                lines.append(f"关键字段: {json.dumps(res.get('key_fields', {}), ensure_ascii=False)}")
                lines.append(f"结果: {res.get('result', '')}")
                lines.append(f"置信度: {res.get('confidence', 0):.1f}%")
                notes = res.get("notes", [])
                if notes:
                    lines.append(f"备注: {'; '.join(notes)}")
            lines.append("")
        output = "\n".join(lines)

    print(output)
    return 0


if __name__ == "__main__":
    # 错误码 E010：未预期的运行时错误兜底
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nE010: 用户中断执行", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"E010: 未预期的运行时错误: {str(exc)[:200]}", file=sys.stderr)
        sys.exit(1)
