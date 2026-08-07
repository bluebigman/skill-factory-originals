#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — nima0011 代码审查技能的核心实现脚本

本脚本依据功能规格独立实现（clean-room），仅使用 Python 标准库。
提供命令行入口，支持 --selftest 离线自检，以及基础处理流程。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
SKILL_NAME = "nima0011"
SKILL_DISPLAY_NAME = "代码审查"
SKILL_VERSION = "1.0.0"

# 错误码与标准化话术（依据规格文档第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试或检查输入。",
    "E007": "输出序列化失败，请检查数据格式。",
    "E008": "命令行参数解析失败。",
    "E009": "自检执行过程中发生未预期错误。",
    "E010": "未知错误发生。",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ReviewItem:
    """表示一条审查结果项。"""

    def __init__(self, field: str, status: str, note: str, confidence: float):
        self.field = field
        self.status = status  # 例如: "ok", "warning", "error", "unknown"
        self.note = note
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化。"""
        return {
            "field": self.field,
            "status": self.status,
            "note": self.note,
            "confidence": self.confidence,
        }


class ReviewResult:
    """表示一次完整的审查输出。"""

    def __init__(self, source: str, items: Optional[List[ReviewItem]] = None):
        self.source = source
        self.items = items if items is not None else []
        self.overall_confidence = 0.0

    def add_item(self, item: ReviewItem) -> None:
        """添加一条审查项。"""
        self.items.append(item)
        self._recalculate_confidence()

    def _recalculate_confidence(self) -> None:
        """重新计算整体置信度（简单平均）。"""
        if not self.items:
            self.overall_confidence = 0.0
            return
        total = sum(item.confidence for item in self.items)
        self.overall_confidence = total / len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化。"""
        return {
            "source": self.source,
            "overall_confidence": self.overall_confidence,
            "items": [item.to_dict() for item in self.items],
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    检查输入是否合法。

    返回: (是否合法, 错误码或 None)
    """
    if raw_input is None or (isinstance(raw_input, str) and raw_input.strip() == ""):
        return False, "E001"
    if not isinstance(raw_input, (str, dict, list)):
        return False, "E003"
    return True, None


def extract_key_info(raw_input: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入中提取关键信息。

    本实现为示例性逻辑，实际场景可按需扩展。
    返回: (提取的关键信息字典, 提取置信度)
    """
    if isinstance(raw_input, dict):
        # 字典输入：直接保留键值
        return raw_input, 0.95
    elif isinstance(raw_input, list):
        # 列表输入：为每个元素创建字段
        extracted = {}
        for i, item in enumerate(raw_input):
            field_name = f"item_{i+1}"
            extracted[field_name] = item
        extracted["total_count"] = len(raw_input)
        return extracted, 0.90
    else:
        # 字符串输入：简单识别
        text = raw_input.strip()
        if not text:
            return {}, 0.0
        # 假设文本本身是描述，提取非空内容
        return {"content": text, "length": len(text)}, 0.80


def analyze_input(extracted: Dict[str, Any]) -> List[ReviewItem]:
    """
    对提取的信息进行审查分析，生成审查项。

    返回: 审查项列表
    """
    items: List[ReviewItem] = []
    for key, value in extracted.items():
        # 示例审查规则：检查值是否为空
        if value is None or (isinstance(value, str) and value.strip() == ""):
            items.append(
                ReviewItem(
                    field=str(key),
                    status="error",
                    note="字段值为空，请检查输入内容",
                    confidence=0.85,
                )
            )
        else:
            # 非空字段，标记为正常
            status = "ok"
            note = "字段已正常识别"
            confidence = 0.95
            
            # 特殊处理 total_count 字段
            if key == "total_count":
                note = f"共识别 {value} 个列表元素"
                confidence = 0.92
            
            items.append(
                ReviewItem(
                    field=str(key),
                    status=status,
                    note=note,
                    confidence=confidence,
                )
            )
    return items


def generate_output(result: ReviewResult) -> str:
    """
    将审查结果格式化为可读文本输出。
    """
    lines: List[str] = []
    lines.append(f"【{SKILL_DISPLAY_NAME}】处理完成")
    lines.append(f"输入来源: {result.source}")
    lines.append(f"整体置信度: {result.overall_confidence:.1%}")
    lines.append("")

    for idx, item in enumerate(result.items, 1):
        lines.append(f"{idx}. 字段 [{item.field}]")
        lines.append(f"   状态: {item.status}")
        lines.append(f"   说明: {item.note}")
        lines.append(f"   置信度: {item.confidence:.1%}")
        lines.append("")

    # 置信度标注
    if result.overall_confidence >= CONFIDENCE_HIGH:
        lines.append("结论: 置信度较高，可直接使用")
    elif result.overall_confidence >= CONFIDENCE_MEDIUM:
        lines.append("结论: 置信度中等，建议复核")
    else:
        lines.append("结论: [需核实] 置信度较低，请人工确认")

    return "\n".join(lines)


def process_input(raw_input: Any) -> Tuple[bool, str, Optional[str]]:
    """
    完整处理流程入口。

    返回: (是否成功, 输出文本或错误信息, 错误码或 None)
    """
    # Step 1: 输入校验
    valid, err_code = validate_input(raw_input)
    if not valid:
        return False, ERROR_MESSAGES.get(err_code or "E010", "未知错误"), err_code

    # Step 2: 提取关键信息
    extracted, extract_confidence = extract_key_info(raw_input)
    if extract_confidence < CONFIDENCE_MEDIUM:
        # 提取置信度过低
        return (
            False,
            ERROR_MESSAGES["E005"] + " 输入内容过于模糊，无法可靠提取关键信息。",
            "E005",
        )

    # Step 3: 审查分析
    review_items = analyze_input(extracted)

    # Step 4: 组装结果
    source_desc = (
        raw_input if isinstance(raw_input, str) else json.dumps(raw_input, ensure_ascii=False)
    )
    result = ReviewResult(source=source_desc)
    for item in review_items:
        result.add_item(item)

    # Step 5: 生成输出
    output_text = generate_output(result)
    return True, output_text, None


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑，不依赖外部文件或网络。

    使用内置硬编码样例数据，断言采用宽松阈值。
    返回: 0 表示自检通过，非 0 表示失败
    """
    print("开始自检...")

    # 测试用例 1: 正常字典输入
    sample_dict = {
        "name": "测试项目",
        "description": "这是一个用于自检的示例项目",
        "version": "1.0.0",
    }
    ok, output, err_code = process_input(sample_dict)
    assert ok, f"测试用例1失败: {err_code}"
    assert isinstance(output, str) and len(output) > 0, "测试用例1输出为空"
    assert "测试项目" in output, "测试用例1输出缺少关键内容"
    print("测试用例 1 (字典输入) 通过")

    # 测试用例 2: 空输入（应返回 E001）
    ok, _, err_code = process_input("")
    assert not ok, "测试用例2应失败"
    assert err_code == "E001", f"测试用例2错误码应为 E001，实际 {err_code}"
    print("测试用例 2 (空输入) 通过")

    # 测试用例 3: 列表输入
    sample_list = ["item1", "item2", "item3"]
    ok, output, err_code = process_input(sample_list)
    assert ok, f"测试用例3失败: {err_code}"
    assert "item1" in output, "测试用例3输出缺少列表内容"
    assert "item2" in output, "测试用例3输出缺少列表内容"
    assert "item3" in output, "测试用例3输出缺少列表内容"
    print("测试用例 3 (列表输入) 通过")

    # 测试用例 4: 字符串输入
    sample_text = "这是需要审查的文本内容"
    ok, output, err_code = process_input(sample_text)
    assert ok, f"测试用例4失败: {err_code}"
    assert "这是需要审查的文本内容" in output, "测试用例4输出缺少文本内容"
    print("测试用例 4 (字符串输入) 通过")

    # 测试用例 5: 错误输入类型（应返回 E003）
    ok, _, err_code = process_input(12345)
    assert not ok, "测试用例5应失败"
    assert err_code == "E003", f"测试用例5错误码应为 E003，实际 {err_code}"
    print("测试用例 5 (非法类型输入) 通过")

    # 测试用例 6: 置信度计算（宽松验证）
    result = ReviewResult(source="test")
    result.add_item(ReviewItem("field1", "ok", "note1", 0.90))
    result.add_item(ReviewItem("field2", "ok", "note2", 0.80))
    # 整体置信度应为 (0.90 + 0.80) / 2 = 0.85
    assert result.overall_confidence >= 0.80, "置信度计算偏低"
    assert result.overall_confidence <= 0.90, "置信度计算偏高"
    print("测试用例 6 (置信度计算) 通过")

    # 测试用例 7: 错误码映射完整性
    for code in ["E001", "E002", "E003", "E004", "E005", "E010"]:
        assert code in ERROR_MESSAGES, f"错误码 {code} 缺失"
        assert len(ERROR_MESSAGES[code]) > 0, f"错误码 {code} 话术为空"
    print("测试用例 7 (错误码映射) 通过")

    print("所有自检用例均通过!")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_DISPLAY_NAME} (技能: {SKILL_NAME}) — 离线处理与自检工具"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（字符串、JSON 等）。若不提供，则进入交互模式。",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="执行内置离线自检，验证核心逻辑",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} {SKILL_VERSION}",
    )
    return parser


def main() -> int:
    """程序主入口。"""
    parser = build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 在 --help/--version 时会抛出 SystemExit(0)
        if e.code != 0:
            print("E008: 命令行参数解析失败", file=sys.stderr)
        return e.code if isinstance(e.code, int) else 1

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as ae:
            print(f"E009: 自检断言失败: {ae}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"E009: 自检执行异常: {e}", file=sys.stderr)
            return 1

    # 处理输入
    if args.input is not None:
        # 尝试解析 JSON
        raw_input: Any = args.input
        try:
            raw_input = json.loads(args.input)
        except json.JSONDecodeError:
            # 不是 JSON，按字符串处理
            pass

        ok, output, err_code = process_input(raw_input)
        if ok:
            print(output)
            return 0
        else:
            print(f"{err_code}: {output}", file=sys.stderr)
            return 1
    else:
        # 交互模式
        print("请输入待处理的内容（输入空行结束）：")
        lines = []
        try:
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
        except EOFError:
            pass

        if not lines:
            print("E001: " + ERROR_MESSAGES["E001"], file=sys.stderr)
            return 1

        user_input = "\n".join(lines)
        try:
            raw_input = json.loads(user_input)
        except json.JSONDecodeError:
            raw_input = user_input

        ok, output, err_code = process_input(raw_input)
        if ok:
            print(output)
            return 0
        else:
            print(f"{err_code}: {output}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
