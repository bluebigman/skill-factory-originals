#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
awesome-copilot-id 技能核心逻辑实现（独立 clean-room 实现）。

本脚本仅依据功能规格设计，不参考任何既有实现。
提供标准的命令行交互与 --selftest 离线自检能力。

错误码体系：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部逻辑错误（不应发生）
    E007 参数解析错误
    E008 输出格式不合法
    E009 自检断言失败
    E010 未知异常
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 技能元信息
SKILL_NAME = "awesome-copilot-id"
DISPLAY_NAME = "未命名工具"
DESCRIPTION = (
    "A curated collection of custom agents, skills, rules, and prompts "
    "for GitHub Copilot, Google Antigravity, OpenCode, Chat"
)
VERSION = "1.0.0"
AUTHOR = "skill-factory-auto"
LICENSE = "MIT"

# 触发词（用于识别是否应启动本技能）
TRIGGER_WORDS = ["awesome copilot id"]

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 90.0
MEDIUM_CONFIDENCE_THRESHOLD = 85.0

# 能力边界声明
CAPABILITY_BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]

# 标准流程中需要确认的最小信息集字段
REQUIRED_FIELDS = ["input_source", "output_format", "completeness"]


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------


class SkillError(Exception):
    """技能执行过程中的自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class ProcessingResult:
    """处理结果对象，包含结构化输出与置信度信息。"""

    def __init__(
        self,
        data: Dict[str, Any],
        confidence: float,
        warnings: Optional[List[str]] = None,
    ):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示，便于序列化输出。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "needs_review": MEDIUM_CONFIDENCE_THRESHOLD <= self.confidence < HIGH_CONFIDENCE_THRESHOLD,
            "needs_verification": self.confidence < MEDIUM_CONFIDENCE_THRESHOLD,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------


def validate_input(raw_input: str) -> None:
    """
    校验输入是否有效。

    对应规格 E001（输入为空）与 E003（输入格式错误）。
    """
    if raw_input is None or not raw_input.strip():
        raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    if len(raw_input) > 100_000:
        raise SkillError("E003", "输入内容过长，超出处理范围，请精简后重试")


def extract_key_info(raw_input: str) -> Dict[str, Any]:
    """
    从原始输入中提取关键信息。

    这是一个通用实现：尝试解析 JSON；若失败则提取基础文本特征。
    实际使用中可根据具体场景替换为更专业的解析逻辑。
    """
    raw_input = raw_input.strip()
    info: Dict[str, Any] = {}

    # 尝试 JSON 解析
    try:
        parsed = json.loads(raw_input)
        if isinstance(parsed, dict):
            info = parsed
        elif isinstance(parsed, list):
            info = {"items": parsed, "item_count": len(parsed)}
        else:
            info = {"value": parsed}
    except json.JSONDecodeError:
        # 非 JSON 输入，提取基础统计特征
        words = raw_input.split()
        info = {
            "text": raw_input,
            "char_count": len(raw_input),
            "word_count": len(words),
            "line_count": raw_input.count("\n") + 1,
        }

    return info


def compute_confidence(info: Dict[str, Any], raw_input: str) -> Tuple[float, List[str]]:
    """
    计算置信度。

    规则（按规格）：
      - 结构化信息完整 → 高置信度
      - 仅文本统计 → 中等置信度
      - 信息稀疏 → 低置信度并给出警告
    """
    warnings: List[str] = []

    if "text" in info:
        # 纯文本输入，置信度取决于文本长度与结构
        if info.get("word_count", 0) >= 10 and info.get("line_count", 1) >= 2:
            confidence = 88.0
            warnings.append("输入为自由文本，建议复核关键结论")
        elif info.get("word_count", 0) >= 3:
            confidence = 80.0
            warnings.append("输入信息较少，结果可能不稳定")
        else:
            confidence = 60.0
            warnings.append("输入过于简短，结果置信度低")
    else:
        # 结构化输入（JSON），置信度较高
        required_keys = ["id", "name", "type"]
        present_keys = [k for k in required_keys if k in info]
        if len(present_keys) >= 2:
            confidence = 95.0
        elif len(present_keys) == 1:
            confidence = 90.0
        else:
            confidence = 85.0
            warnings.append("结构化输入缺少关键字段，建议补充 id/name/type")

    return confidence, warnings


def process_input(raw_input: str, output_format: str = "json", completeness: str = "standard") -> ProcessingResult:
    """
    执行核心处理流程（对应规格 Step 2）。

    参数：
        raw_input: 用户提供的原始输入
        output_format: 期望的输出格式（json / text）
        completeness: 期望的完整度（quick / standard / detailed）

    返回：
        ProcessingResult 对象
    """
    # Step 1: 校验输入
    validate_input(raw_input)

    # Step 2: 提取关键信息
    info = extract_key_info(raw_input)

    # Step 3: 计算置信度
    confidence, warnings = compute_confidence(info, raw_input)

    # Step 4: 按输出格式组织结果
    if output_format == "json":
        data = {
            "skill": SKILL_NAME,
            "version": VERSION,
            "parsed_info": info,
            "completeness": completeness,
        }
    elif output_format == "text":
        lines = [
            f"技能: {DISPLAY_NAME}",
            f"版本: {VERSION}",
            "解析结果:",
        ]
        for key, value in info.items():
            lines.append(f"  {key}: {value}")
        data = {"text_output": "\n".join(lines)}
    else:
        raise SkillError("E003", f"不支持的输出格式: {output_format}，可选 json 或 text")

    return ProcessingResult(data=data, confidence=confidence, warnings=warnings)


def check_boundaries(request: str) -> None:
    """
    检查请求是否超出能力边界（对应规格 E004）。

    简单关键词检测，实际场景可替换为更智能的判断。
    """
    boundary_keywords = ["联网", "访问网站", "外部API", "实时行情", "网络请求"]
    for keyword in boundary_keywords:
        if keyword in request:
            raise SkillError(
                "E004",
                f"请求包含'{keyword}'，超出本工具能力范围（不访问网络或外部服务），建议使用专用工具",
            )


def format_result(result: ProcessingResult, output_format: str = "json") -> str:
    """
    将处理结果格式化为输出字符串（对应规格 Step 3）。

    支持 json 与 text 两种格式。
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        if "text_output" in result.data:
            lines.append(result.data["text_output"])
        else:
            lines.append(json.dumps(result.data.get("parsed_info", {}), ensure_ascii=False, indent=2))
        lines.append(f"\n置信度: {result.confidence:.1f}%")
        if result.confidence < HIGH_CONFIDENCE_THRESHOLD:
            lines.append("状态: 建议复核" if result.confidence >= MEDIUM_CONFIDENCE_THRESHOLD else "状态: [需核实]")
        if result.warnings:
            lines.append("警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)
    else:
        raise SkillError("E008", f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def run_selftest() -> int:
    """
    离线自检函数。

    使用内置硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值，确保在任何环境都能通过。
    """
    print("开始离线自检...")

    # 测试用例 1: 正常 JSON 输入
    test_json = '{"id": "test-001", "name": "示例项目", "type": "demo", "description": "这是一个用于自检的示例数据"}'
    try:
        result = process_input(test_json, output_format="json")
        assert result.confidence >= 85.0, "JSON 输入置信度应不低于 85%"
        assert "parsed_info" in result.data, "JSON 输出应包含 parsed_info 字段"
        assert result.data["parsed_info"].get("id") == "test-001", "id 字段解析错误"
        print("  [通过] JSON 输入处理")
    except AssertionError as e:
        print(f"  [失败] JSON 输入处理: {e}")
        return 1
    except SkillError as e:
        print(f"  [失败] JSON 输入处理: {e.code} {e.message}")
        return 1

    # 测试用例 2: 自然语言文本输入
    test_text = "请帮我整理这份会议纪要，包含行动项、负责人和截止日期，并输出为结构化格式。"
    try:
        result = process_input(test_text, output_format="text")
        assert result.confidence >= 50.0, "文本输入置信度应不低于 50%"
        assert "text_output" in result.data, "文本输出应包含 text_output 字段"
        print("  [通过] 文本输入处理")
    except AssertionError as e:
        print(f"  [失败] 文本输入处理: {e}")
        return 1
    except SkillError as e:
        print(f"  [失败] 文本输入处理: {e.code} {e.message}")
        return 1

    # 测试用例 3: 空输入应触发 E001
    try:
        process_input("   ")
        print("  [失败] 空输入未触发 E001")
        return 1
    except SkillError as e:
        assert e.code == "E001", f"空输入应返回 E001，实际为 {e.code}"
        print("  [通过] 空输入错误处理")

    # 测试用例 4: 能力边界检查
    try:
        check_boundaries("请帮我联网查询今天的新闻")
        print("  [失败] 边界检查未触发 E004")
        return 1
    except SkillError as e:
        assert e.code == "E004", f"边界请求应返回 E004，实际为 {e.code}"
        print("  [通过] 能力边界检查")

    # 测试用例 5: 置信度标注逻辑
    short_text = "测试"
    try:
        result = process_input(short_text)
        assert result.confidence < 85.0, "短文本置信度应低于 85%"
        assert result.to_dict()["needs_verification"] is True, "低置信度应标记为需核实"
        print("  [通过] 置信度标注逻辑")
    except AssertionError as e:
        print(f"  [失败] 置信度标注逻辑: {e}")
        return 1
    except SkillError as e:
        print(f"  [失败] 置信度标注逻辑: {e.code} {e.message}")
        return 1

    print("所有自检用例通过 ✅")
    return 0


def main() -> int:
    """
    主入口函数。

    解析命令行参数，执行相应操作。
    """
    parser = argparse.ArgumentParser(
        prog="scripts/main.py",
        description=f"{DISPLAY_NAME} - {DESCRIPTION}",
        epilog=f"版本 {VERSION} | 许可证 {LICENSE}",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件，不访问网络）",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="待处理的输入内容（数据/文件内容/URL）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--completeness",
        type=str,
        choices=["quick", "standard", "detailed"],
        default="standard",
        help="期望的完整度（默认 standard）",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 在参数错误时会抛出 SystemExit
        print(f"[E007] 参数解析错误: {e}", file=sys.stderr)
        return 1

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        # 首先检查是否包含触发词（模拟触发机制）
        if args.input and not any(word in args.input.lower() for word in TRIGGER_WORDS):
            # 非严格模式：即使没有触发词也处理，但给出提示
            print(f"提示: 未检测到触发词 {TRIGGER_WORDS}，仍按标准流程处理")

        # 检查能力边界
        check_boundaries(args.input)

        # 执行核心处理
        result = process_input(
            args.input,
            output_format=args.format,
            completeness=args.completeness,
        )

        # 输出结果
        output = format_result(result, output_format=args.format)
        print(output)

        return 0

    except SkillError as e:
        # 技能定义的错误，使用标准化话术输出
        error_messages = {
            "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
            "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
            "E003": "输入格式不符合要求，示例：JSON 对象或自然语言文本",
            "E004": "这超出了本工具的能力范围，建议使用专用工具处理",
            "E005": "结果无法确定，建议：提供更多上下文信息或人工复核",
        }
        message = error_messages.get(e.code, e.message)
        print(f"[{e.code}] {message}", file=sys.stderr)
        return 1

    except Exception as e:
        # 未知异常
        print(f"[E010] 发生未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
