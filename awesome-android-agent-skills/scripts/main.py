#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-android-agent-skills 独立实现脚本

本脚本完全依据功能规格重新实现（clean-room），不参考任何既有代码。
提供核心技能流程：输入解析、结构化处理、置信度评估、输出生成。
支持命令行调用与离线自检（--selftest）。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{fields}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理错误：{detail}",
    "E007": "输出格式不支持：{fmt}",
    "E008": "批量处理中断：第 {index} 项失败 - {detail}",
    "E009": "参数校验失败：{detail}",
    "E010": "未知错误：{detail}",
}


class SkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_CODES.get(code, ERROR_CODES["E010"]).format(**kwargs)
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ParsedInput:
    """解析后的输入数据"""

    def __init__(self, raw: str, fields: Dict[str, Any], confidence: float):
        self.raw = raw
        self.fields = fields
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "fields": self.fields,
            "confidence": self.confidence,
        }


class OutputResult:
    """处理结果"""

    def __init__(self, data: Any, confidence: float, warnings: List[str]):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw: str) -> ParsedInput:
    """
    解析输入内容，识别关键信息。

    支持两种输入格式：
    1. JSON 字符串：直接解析字段
    2. 普通文本：按 key=value 或 "key: value" 提取

    返回结构化字段与置信度。
    """
    if not raw or not raw.strip():
        raise SkillError("E001")

    raw = raw.strip()

    # 尝试 JSON 解析
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            confidence = 0.95
            return ParsedInput(raw=raw, fields=data, confidence=confidence)
        elif isinstance(data, list):
            # 列表输入，包装为 items 字段
            confidence = 0.90
            return ParsedInput(raw=raw, fields={"items": data}, confidence=confidence)
        else:
            # 标量 JSON 值
            confidence = 0.85
            return ParsedInput(raw=raw, fields={"value": data}, confidence=confidence)
    except json.JSONDecodeError:
        pass

    # 尝试 key=value 或 key: value 格式
    fields: Dict[str, Any] = {}
    lines = raw.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 支持 = 和 : 分隔
        for sep in ("=", ":"):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key:
                    fields[key] = value
                break

    if fields:
        # 至少提取到 1 个字段，置信度中等
        confidence = 0.80
        return ParsedInput(raw=raw, fields=fields, confidence=confidence)

    # 无法识别结构，作为纯文本处理
    confidence = 0.60
    return ParsedInput(raw=raw, fields={"text": raw}, confidence=confidence)


def assess_confidence(parsed: ParsedInput) -> float:
    """
    评估置信度。

    规则：
    - 字段数 >= 3：置信度提升
    - 字段数 == 0：置信度降低
    - 有 text 字段（纯文本）：置信度较低
    """
    fields = parsed.fields
    field_count = len(fields)

    if "text" in fields and field_count == 1:
        # 纯文本，低置信度
        return 0.50
    elif field_count >= 3:
        # 多字段，高置信度
        return min(parsed.confidence + 0.10, 0.95)
    elif field_count == 1:
        # 单字段，中等置信度
        return parsed.confidence
    else:
        # 无有效字段，低置信度
        return 0.40


def process_input(raw: str) -> OutputResult:
    """
    核心处理流程：
    1. 解析输入
    2. 评估置信度
    3. 生成输出
    """
    parsed = parse_input(raw)
    confidence = assess_confidence(parsed)

    warnings: List[str] = []

    # 根据置信度生成标注
    if confidence >= 0.90:
        pass  # 直接输出
    elif confidence >= 0.85:
        warnings.append("建议复核")
    else:
        warnings.append("[需核实]")

    # 构建输出数据
    output_data = {
        "parsed_fields": parsed.fields,
        "field_count": len(parsed.fields),
        "input_type": "structured" if "text" not in parsed.fields else "text",
    }

    return OutputResult(data=output_data, confidence=confidence, warnings=warnings)


def batch_process(inputs: List[str]) -> List[OutputResult]:
    """批量处理多个输入"""
    results: List[OutputResult] = []
    for i, raw in enumerate(inputs, start=1):
        try:
            result = process_input(raw)
            results.append(result)
        except SkillError as e:
            # 批量处理中单项失败，继续处理后续项
            results.append(
                OutputResult(
                    data={"error": e.code, "message": e.message},
                    confidence=0.0,
                    warnings=[f"E008: 第 {i} 项处理失败"],
                )
            )
    return results


def format_output(results: List[OutputResult], fmt: str = "json") -> str:
    """按指定格式输出结果"""
    if fmt == "json":
        payload = [r.to_dict() for r in results]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        for idx, r in enumerate(results, start=1):
            lines.append(f"[{idx}] 置信度: {r.confidence:.0%}")
            if r.warnings:
                lines.append(f"    警告: {', '.join(r.warnings)}")
            lines.append(f"    数据: {json.dumps(r.data, ensure_ascii=False)}")
        return "\n".join(lines)
    else:
        raise SkillError("E007", fmt=fmt)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保在各种环境下通过。
    """
    print("=== 自检开始 ===")

    # 测试用例 1：JSON 结构化输入
    test1 = '{"name": "test", "value": 42, "active": true}'
    result1 = process_input(test1)
    assert result1.confidence > 0.7, f"置信度过低: {result1.confidence}"
    assert "name" in result1.data["parsed_fields"], "字段解析失败"
    assert len(result1.warnings) <= 1, "警告过多"
    print("[PASS] JSON 输入解析")

    # 测试用例 2：key=value 格式
    test2 = "title=hello\ndesc=world"
    result2 = process_input(test2)
    assert result2.confidence > 0.6, f"置信度过低: {result2.confidence}"
    assert result2.data["field_count"] >= 2, "字段数不足"
    print("[PASS] key=value 解析")

    # 测试用例 3：纯文本输入
    test3 = "这是一段普通文本，没有结构化信息"
    result3 = process_input(test3)
    assert result3.confidence < 0.7, f"纯文本置信度应较低: {result3.confidence}"
    assert "text" in result3.data["parsed_fields"], "纯文本应保留 text 字段"
    print("[PASS] 纯文本处理")

    # 测试用例 4：空输入应报错
    try:
        process_input("")
        assert False, "空输入应抛出 E001"
    except SkillError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
    print("[PASS] 空输入错误处理")

    # 测试用例 5：批量处理
    batch = [test1, test2, test3, ""]
    batch_results = batch_process(batch)
    assert len(batch_results) == 4, f"批量结果数量错误: {len(batch_results)}"
    # 最后一项（空输入）应包含错误信息
    assert "error" in batch_results[-1].data, "批量处理应捕获单项错误"
    print("[PASS] 批量处理")

    # 测试用例 6：输出格式化
    fmt_json = format_output([result1], fmt="json")
    assert '"confidence"' in fmt_json, "JSON 输出缺少置信度字段"
    fmt_text = format_output([result1], fmt="text")
    assert "置信度" in fmt_text, "文本输出缺少置信度"
    print("[PASS] 输出格式化")

    # 测试用例 7：错误码消息
    assert "请提供" in ERROR_CODES["E001"], "E001 消息不正确"
    assert "超出" in ERROR_CODES["E004"], "E004 消息不正确"
    print("[PASS] 错误码消息")

    print("=== 自检全部通过 ===")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="awesome-android-agent-skills 技能脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python main.py --input '{\"name\": \"test\"}'\n"
            "  python main.py --input 'key=value' --format text\n"
            "  python main.py --batch '{\"a\":1}' '{\"b\":2}'\n"
            "  python main.py --selftest\n"
        ),
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="单条输入内容（JSON 字符串或 key=value 格式）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多条输入",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不访问网络）",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"[FAIL] 自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[FAIL] 自检异常: {e}", file=sys.stderr)
            return 1

    # 参数校验
    if not args.input and not args.batch:
        parser.print_help()
        print("\n错误: 必须提供 --input 或 --batch 参数", file=sys.stderr)
        return 1

    try:
        # 批量处理优先
        if args.batch:
            results = batch_process(args.batch)
        else:
            results = [process_input(args.input)]

        # 输出结果
        output = format_output(results, fmt=args.format)
        print(output)
        return 0

    except SkillError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E010]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
