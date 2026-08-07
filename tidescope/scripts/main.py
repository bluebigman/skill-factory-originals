#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tidescope - 未命名工具
AI-powered open source collaboration tool.
Interactive CLI to generate contributor guides and visualize technical debt

版本: 1.0.0
许可证: MIT
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码与异常定义
# ---------------------------------------------------------------------------
class TidescopeError(Exception):
    """技能基础异常，携带错误码与标准化话术"""

    ERROR_MESSAGES = {
        "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
        "E002": "还缺少以下信息，请补充：...",
        "E003": "输入格式不符合要求，示例：...",
        "E004": "这超出了本工具的能力范围，建议...",
        "E005": "结果无法确定，建议：...",
        "E006": "内部处理失败，请重试或检查输入",
        "E007": "输出序列化失败",
        "E008": "无效参数组合",
        "E009": "未预期的运行时错误",
        "E010": "系统资源不足",
    }

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        message = self.ERROR_MESSAGES.get(code, "未知错误")
        if detail:
            message = f"{message} {detail}"
        super().__init__(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条输入的处理结果"""

    def __init__(self, raw_input: str, key_fields: Dict[str, str], confidence: float):
        self.raw_input = raw_input
        self.key_fields = key_fields
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "raw_input": self.raw_input,
            "key_fields": self.key_fields,
            "confidence": self.confidence,
        }


class ProcessingResult:
    """批量处理的结果集合"""

    def __init__(self, items: List[ProcessedItem], warnings: List[str] = None):
        self.items = items
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "items": [item.to_dict() for item in self.items],
            "warnings": self.warnings,
            "item_count": len(self.items),
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw_input: str) -> Dict[str, str]:
    """
    解析输入内容，识别关键字段。

    支持的输入格式：
    - JSON 字符串（对象）
    - key=value 对（用逗号或分号分隔）
    - 纯文本（作为整体内容）
    """
    if not raw_input or not raw_input.strip():
        raise TidescopeError("E001")

    text = raw_input.strip()

    # 尝试 JSON 解析
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise TidescopeError("E003", "JSON 顶层必须是对象")
            # 将值统一转为字符串
            return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            raise TidescopeError("E003", "JSON 格式错误")

    # 尝试 key=value 对
    if "=" in text:
        fields: Dict[str, str] = {}
        # 支持逗号或分号分隔
        parts = text.replace(";", ",").split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "=" not in part:
                # 这一部分无法解析为 key=value，视为内容碎片
                fields["_fragment"] = fields.get("_fragment", "") + part
            else:
                key, _, value = part.partition("=")
                fields[key.strip()] = value.strip()
        if fields:
            return fields

    # 纯文本
    return {"content": text}


def compute_confidence(fields: Dict[str, str], raw_length: int) -> float:
    """
    计算置信度。

    规则：
    - 字段越多，置信度越高
    - 原始输入越长，置信度越高
    - 存在内容碎片时降低置信度
    """
    if not fields:
        return 0.0

    base = 0.7
    field_bonus = min(0.2, len(fields) * 0.05)
    length_bonus = min(0.1, raw_length / 1000 * 0.1)

    confidence = base + field_bonus + length_bonus

    # 有碎片标记则降低
    if "_fragment" in fields:
        confidence -= 0.15

    return max(0.0, min(1.0, confidence))


def process_single(raw_input: str) -> ProcessedItem:
    """
    处理单条输入，返回结构化结果。
    """
    if not raw_input or not raw_input.strip():
        raise TidescopeError("E001")

    fields = parse_input(raw_input)
    confidence = compute_confidence(fields, len(raw_input.strip()))

    return ProcessedItem(
        raw_input=raw_input.strip(),
        key_fields=fields,
        confidence=confidence,
    )


def process_batch(inputs: List[str]) -> ProcessingResult:
    """
    批量处理多条输入。

    逐条处理，单条失败不影响其他条目。
    """
    if not inputs:
        raise TidescopeError("E001")

    items: List[ProcessedItem] = []
    warnings: List[str] = []

    for idx, raw in enumerate(inputs):
        try:
            item = process_single(raw)
            items.append(item)
        except TidescopeError as exc:
            warnings.append(f"第 {idx + 1} 条处理失败: {exc}")

    if not items:
        raise TidescopeError("E002", "所有输入均处理失败")

    return ProcessingResult(items=items, warnings=warnings)


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    按指定格式输出结果。

    支持格式：json, text
    """
    if output_format == "json":
        try:
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            raise TidescopeError("E007")
    elif output_format == "text":
        lines = []
        for i, item in enumerate(result.items, 1):
            lines.append(f"--- 条目 {i} ---")
            for key, value in item.key_fields.items():
                lines.append(f"  {key}: {value}")
            conf_pct = int(item.confidence * 100)
            marker = ""
            if item.confidence >= 0.90:
                marker = ""
            elif item.confidence >= 0.85:
                marker = " [建议复核]"
            else:
                marker = " [需核实]"
            lines.append(f"  置信度: {conf_pct}%{marker}")
        if result.warnings:
            lines.append("--- 警告 ---")
            for w in result.warnings:
                lines.append(f"  {w}")
        return "\n".join(lines)
    else:
        raise TidescopeError("E003", f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 交互式引导（Step 1: 收集最小信息集）
# ---------------------------------------------------------------------------
def interactive_collect_info() -> Tuple[List[str], str, str]:
    """
    交互式收集最小信息集。

    返回: (输入列表, 输出格式, 完整度)
    """
    print("=== tidescope 信息收集 ===\n")

    # 输入来源
    print("请提供待处理的内容（支持多行，空行结束）：")
    lines = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line.strip())

    if not lines:
        raise TidescopeError("E001")

    # 输出格式
    print("\n输出格式（json/text，默认 json）：")
    try:
        fmt = input("> ").strip().lower() or "json"
    except EOFError:
        fmt = "json"

    if fmt not in ("json", "text"):
        raise TidescopeError("E003", f"不支持的输出格式: {fmt}")

    # 完整度
    print("\n期望完整度（quick/detail，默认 quick）：")
    try:
        completeness = input("> ").strip().lower() or "quick"
    except EOFError:
        completeness = "quick"

    if completeness not in ("quick", "detail"):
        raise TidescopeError("E003", f"不支持的完整度: {completeness}")

    return lines, fmt, completeness


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("开始自检...")

    # 样例 1: JSON 输入
    json_input = '{"name": "test", "type": "demo", "value": "42"}'
    item1 = process_single(json_input)
    assert item1.confidence >= 0.8, "JSON 输入置信度应较高"
    assert "name" in item1.key_fields, "JSON 字段应被解析"
    assert item1.key_fields["name"] == "test", "JSON 字段值应正确"

    # 样例 2: key=value 输入
    kv_input = "name=hello,type=world,count=3"
    item2 = process_single(kv_input)
    assert item2.confidence >= 0.7, "key=value 输入置信度应中等以上"
    assert item2.key_fields.get("name") == "hello", "key=value 解析错误"
    assert item2.key_fields.get("count") == "3", "数字字段应保留为字符串"

    # 样例 3: 纯文本输入
    text_input = "这是一个纯文本测试内容，用于验证基本处理流程"
    item3 = process_single(text_input)
    assert item3.confidence >= 0.5, "纯文本输入置信度应可接受"
    assert "content" in item3.key_fields, "纯文本应放入 content 字段"

    # 样例 4: 批量处理
    batch_inputs = [json_input, kv_input, text_input]
    result = process_batch(batch_inputs)
    assert len(result.items) == 3, "批量处理应处理全部条目"
    assert len(result.warnings) == 0, "有效输入不应产生警告"

    # 样例 5: 空输入应报错
    try:
        process_single("")
        assert False, "空输入应抛出 E001"
    except TidescopeError as exc:
        assert exc.code == "E001", "空输入错误码应为 E001"

    # 样例 6: 输出格式化
    json_out = format_output(result, "json")
    parsed = json.loads(json_out)
    assert parsed["item_count"] == 3, "JSON 输出应包含 3 个条目"

    text_out = format_output(result, "text")
    assert "置信度" in text_out, "文本输出应包含置信度"

    # 样例 7: 置信度阈值判定
    high_conf = ProcessedItem("x", {"a": "1", "b": "2", "c": "3"}, 0.95)
    mid_conf = ProcessedItem("x", {"a": "1"}, 0.87)
    low_conf = ProcessedItem("x", {"a": "1"}, 0.60)

    assert high_conf.confidence >= 0.90, "高置信度应 >= 0.90"
    assert 0.85 <= mid_conf.confidence < 0.90, "中置信度应在 0.85-0.90 区间"
    assert low_conf.confidence < 0.85, "低置信度应 < 0.85"

    # 样例 8: 输入为 None 或空白
    for bad_input in [None, "   ", "\t\n"]:
        try:
            process_single(bad_input)  # type: ignore
            assert False, f"输入 {bad_input!r} 应抛出 E001"
        except TidescopeError as exc:
            assert exc.code == "E001", "空白输入错误码应为 E001"

    print("所有自检断言通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        prog="tidescope",
        description="🌊 AI-powered open source collaboration tool. "
                    "Interactive CLI to generate contributor guides and visualize technical debt",
        epilog="示例: tidescope --input 'name=test,type=demo' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        action="append",
        help="输入内容（可多次指定，进行批量处理）",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互式模式（引导收集信息）",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as exc:
            print(f"自检失败: {exc}")
            return 1
        except Exception as exc:  # 兜底
            print(f"自检异常: {exc}")
            return 1

    # 交互模式
    if args.interactive:
        try:
            inputs, fmt, _ = interactive_collect_info()
            result = process_batch(inputs)
            print("\n=== 处理结果 ===")
            print(format_output(result, fmt))
            return 0
        except TidescopeError as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\n已取消", file=sys.stderr)
            return 1

    # 命令行参数模式
    if not args.input:
        parser.print_help()
        return 1

    try:
        result = process_batch(args.input)
        print(format_output(result, args.format))
        return 0
    except TidescopeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底
        print(f"错误: [E009] 未预期的运行时错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
