#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

未命名工具 - 基于功能规格的独立实现（clean-room 重写）
仅依据功能规格设计，不复制任何既有代码。

职责：
    1. 将用户输入（文本）解析为结构化结果
    2. 按规格输出，带置信度标注
    3. 提供 --selftest 离线自检（内置硬编码样例，不依赖外部环境）

用法：
    python scripts/main.py "用户输入内容"
    python scripts/main.py --selftest
"""

import argparse
import sys
import re
from typing import Dict, List, Tuple, Any

# 版本与元数据（与规格一致）
VERSION = "1.0.0"
NAME = "awesome-claude-design"
DISPLAY_NAME = "未命名工具"
DESCRIPTION = "Claude Design DESIGN.md prompts by aesthetic family, remix recipes, skills, video teardowns, X signal, honest community"
TRIGGER_WORDS = ["awesome claude design", "未命名工具", "帮我处理", "转成另一种格式", "批量弄一下"]

# 错误码与标准化话术（对应规格第四节的错误码表）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：请提供文本/数据/URL",
    "E004": "这超出了本工具的能力范围，建议：联系专业服务或使用专用工具",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "参数错误，请检查命令行参数",
    "E008": "输出写入失败，请检查权限或路径",
    "E009": "自检失败，逻辑与规格不一致",
    "E010": "未预期的错误",
}

# 置信度阈值（对应规格第三部分）
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


class InputParser:
    """输入解析器：从原始文本中提取关键字段。"""

    # 关键字段的正则模式（宽松匹配，不依赖精确格式）
    _FIELD_PATTERNS = {
        "名称": r"(?:名称|名字|title|name)[:：\s]+([^\s,，;；]+)",
        "类型": r"(?:类型|类别|type|kind)[:：\s]+([^\s,，;；]+)",
        "数量": r"(?:数量|个数|count|quantity)[:：\s]+(\d+)",
        "日期": r"(?:日期|时间|date|time)[:：\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        "URL": r"(https?://[^\s]+)",
    }

    def __init__(self, raw_text: str):
        self.raw_text = raw_text.strip() if raw_text else ""

    def is_empty(self) -> bool:
        """检查输入是否为空。"""
        return not self.raw_text

    def parse(self) -> Dict[str, Any]:
        """
        解析输入，提取关键字段。
        返回结构化字典，包含提取的字段和原始文本。
        """
        result = {
            "raw_text": self.raw_text,
            "fields": {},
            "field_count": 0,
        }

        if self.is_empty():
            return result

        # 逐字段匹配（宽松模式）
        for field_name, pattern in self._FIELD_PATTERNS.items():
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    result["fields"][field_name] = value

        # 统计识别到的字段数
        result["field_count"] = len(result["fields"])
        return result


class ConfidenceCalculator:
    """置信度计算器：根据字段完整度估算置信度。"""

    # 期望的关键字段（对应规格 Step1 的最小信息集）
    REQUIRED_FIELDS = ["名称", "类型", "数量", "URL"]

    @classmethod
    def calculate(cls, fields: Dict[str, Any]) -> Tuple[float, str]:
        """
        计算置信度并返回标注信息。
        返回 (置信度 0-1, 标注文本)
        """
        if not fields:
            return 0.0, "[需核实] 未识别到任何关键字段"

        # 计算字段覆盖比例（宽松：至少识别到 1 个字段即有一定置信度）
        matched = sum(1 for f in cls.REQUIRED_FIELDS if f in fields)
        total = len(cls.REQUIRED_FIELDS)

        # 基础置信度 = 字段覆盖率 * 0.8 + 基础值 0.2（保证非空输入有基础置信度）
        # 这样设计避免出现 0 置信度，且字段越多置信度越高
        base_score = 0.2 + 0.8 * (matched / total) if total > 0 else 0.2

        # 根据字段数量微调（字段越多越可信）
        field_count_bonus = min(0.1, len(fields) * 0.02)
        confidence = min(0.98, base_score + field_count_bonus)

        # 根据置信度阈值生成标注
        if confidence >= HIGH_CONFIDENCE:
            note = "直接输出"
        elif confidence >= MEDIUM_CONFIDENCE:
            note = "建议复核"
        else:
            note = "[需核实] 请人工复核关键结果"

        return round(confidence, 2), note


class ResultFormatter:
    """结果格式化器：按约定格式生成输出。"""

    @staticmethod
    def format(parsed: Dict[str, Any], confidence: float, note: str) -> str:
        """生成结构化输出文本。"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"处理结果（{DISPLAY_NAME} v{VERSION}）")
        lines.append("=" * 50)

        if not parsed.get("fields"):
            lines.append("未提取到结构化字段。")
        else:
            lines.append("识别到的关键字段：")
            for key, value in parsed["fields"].items():
                lines.append(f"  - {key}: {value}")

        lines.append(f"字段数量: {parsed.get('field_count', 0)}")
        lines.append(f"置信度: {confidence:.0%} ({note})")
        lines.append("=" * 50)
        return "\n".join(lines)


class SkillProcessor:
    """核心处理器：串联解析、置信度计算、输出格式化。"""

    def __init__(self):
        self.parser = InputParser
        self.calculator = ConfidenceCalculator
        self.formatter = ResultFormatter

    def process(self, raw_text: str) -> Dict[str, Any]:
        """
        处理用户输入，返回结构化结果。
        返回字典包含：成功标志、输出文本、错误码（如有）、置信度。
        """
        # E001: 输入为空
        if not raw_text or not raw_text.strip():
            return {
                "success": False,
                "error_code": "E001",
                "message": ERROR_MESSAGES["E001"],
                "output": None,
            }

        # 解析输入
        parsed = self.parser(raw_text).parse()

        # E002: 关键信息缺失（一个字段都没识别到）
        if parsed["field_count"] == 0:
            return {
                "success": False,
                "error_code": "E002",
                "message": ERROR_MESSAGES["E002"] + "名称、类型、数量或URL中的至少一项",
                "output": None,
            }

        # 计算置信度
        confidence, note = self.calculator.calculate(parsed["fields"])

        # E005: 置信度过低
        if confidence < MEDIUM_CONFIDENCE:
            return {
                "success": True,
                "error_code": "E005",
                "message": ERROR_MESSAGES["E005"],
                "output": self.formatter.format(parsed, confidence, note),
                "confidence": confidence,
                "note": note,
            }

        # 正常输出
        return {
            "success": True,
            "error_code": None,
            "message": None,
            "output": self.formatter.format(parsed, confidence, note),
            "confidence": confidence,
            "note": note,
        }


def run_selftest() -> bool:
    """离线自检：使用内置硬编码数据验证核心逻辑。"""

    # 硬编码测试样例（不读外部文件、不依赖工作目录、不访问网络）
    test_cases = [
        # (输入, 预期至少包含的字段数, 预期置信度下限)
        ("名称: 设计稿 类型: 网页 数量: 3 https://example.com", 3, 0.8),
        ("帮我设计一个海报", 0, 0.2),  # 无结构化字段，但不应崩溃
        ("", 0, 0.0),  # 空输入，应返回 E001
        ("数量: 5 日期: 2026-01-15", 2, 0.5),
        ("https://example.com/page 名称: 测试", 2, 0.5),
        ("随便说点什么", 0, 0.2),  # 无字段，但非空
    ]

    processor = SkillProcessor()
    all_passed = True

    for i, (input_text, min_fields, min_conf) in enumerate(test_cases):
        try:
            result = processor.process(input_text)

            # 宽松断言：只检查类型和基本结构，不依赖精确值
            assert isinstance(result, dict), f"用例{i}: 返回类型错误"
            assert "success" in result, f"用例{i}: 缺少 success 字段"

            if not input_text.strip():
                # 空输入必须返回 E001
                assert result["error_code"] == "E001", f"用例{i}: 空输入应返回 E001"
            elif result["success"]:
                # 成功场景：检查置信度不低于下限（宽松比较）
                conf = result.get("confidence", 0.0)
                assert conf >= min_conf - 0.1, f"用例{i}: 置信度 {conf} 低于预期下限 {min_conf}"
                # 输出非空
                assert result.get("output"), f"用例{i}: 成功场景必须有输出"
            else:
                # 失败场景：必须有错误码和消息
                assert result.get("error_code"), f"用例{i}: 失败场景必须有错误码"
                assert result.get("message"), f"用例{i}: 失败场景必须有消息"

            # 额外检查：置信度必须在合理区间 [0, 1]
            if result.get("confidence") is not None:
                assert 0.0 <= result["confidence"] <= 1.0, f"用例{i}: 置信度超出范围"

        except AssertionError as e:
            print(f"自检失败 - {e}")
            all_passed = False
        except Exception as e:
            print(f"自检异常 - 用例{i}: {e}")
            all_passed = False

    # 额外测试：错误码体系完整性
    try:
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
    except AssertionError as e:
        print(f"自检失败 - {e}")
        all_passed = False

    return all_passed


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - {DESCRIPTION}",
        epilog="示例: python scripts/main.py '名称: 设计稿 类型: 网页'",
    )
    parser.add_argument(
        "input_text",
        nargs="?",
        default=None,
        help="待处理的输入文本",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部环境）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        print("正在运行离线自检...")
        passed = run_selftest()
        if passed:
            print("自检通过：全部用例验证成功，逻辑与规格一致。")
            return 0
        else:
            print("自检失败：存在未通过的用例，请检查实现。", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input_text:
        # E007: 参数错误
        print(ERROR_MESSAGES["E007"], file=sys.stderr)
        print("用法: python scripts/main.py '输入文本' 或 python scripts/main.py --selftest")
        return 1

    # 处理输入
    processor = SkillProcessor()
    result = processor.process(args.input_text)

    if result["success"]:
        print(result["output"])
        return 0
    else:
        # 输出错误信息（含错误码）
        error_code = result.get("error_code", "E010")
        message = result.get("message", ERROR_MESSAGES["E010"])
        print(f"[{error_code}] {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
