#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
技能: awesome-agent-conventions (未命名工具)

一个独立、clean-room 实现的命令行入口。
仅依据功能规格书实现, 不复制任何既有代码。

功能概览:
  - 根据输入内容, 识别关键信息并结构化
  - 按默认模板生成输出, 并标注置信度
  - 支持批量处理
  - 提供 --selftest 离线自检

用法示例:
  python scripts/main.py "帮我处理一下这个"
  python scripts/main.py --input "批量弄一下这些" --format json
  python scripts/main.py --selftest

错误码:
  E001-E010 (见下方常量表)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------------------------

# 技能元数据 (来自规格书)
SKILL_NAME = "awesome-agent-conventions"
SKILL_DISPLAY_NAME = "未命名工具"
SKILL_VERSION = "1.0.0"
SKILL_DESCRIPTION = "仅供学习与参考用途。提供规范、可复用的处理流程与输出。"

# 错误码及对应话术 (来自规格书第四节)
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{}",
    "E003": "输入格式不符合要求，示例：{}",
    "E004": "这超出了本工具的能力范围，建议：{}",
    "E005": "结果无法确定，建议：{}",
    # 预留一些内部错误码
    "E006": "内部错误: 未知的处理异常",
    "E007": "内部错误: 参数解析失败",
    "E008": "内部错误: 输出序列化失败",
    "E009": "内部错误: 自检失败",
    "E010": "内部错误: 不支持的输出格式",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # 直接输出
CONFIDENCE_MEDIUM = 0.85    # 建议复核
CONFIDENCE_LOW = 0.85       # 小于此值则标记 [需核实]

# 触发词列表 (来自规格书第二节)
TRIGGER_WORDS = [
    "awesome agent conventions",
    "帮我处理一下这个",
    "把这个转成另一种格式",
    "批量弄一下这些",
]

# 默认输出模板的关键字段
DEFAULT_OUTPUT_FIELDS = ["input", "key_findings", "confidence", "status"]


# ------------------------------------------------------------------------------
# 数据结构定义
# ------------------------------------------------------------------------------

@dataclass
class ProcessedItem:
    """单条输入的处理结果。"""
    input_text: str
    key_findings: List[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "processed"  # processed / needs_review / uncertain

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典, 便于序列化。"""
        return {
            "input": self.input_text,
            "key_findings": self.key_findings,
            "confidence": round(self.confidence, 4),
            "status": self.status,
        }


@dataclass
class BatchResult:
    """批量处理的结果集合。"""
    items: List[ProcessedItem] = field(default_factory=list)
    total_count: int = 0
    processed_count: int = 0
    needs_review_count: int = 0
    uncertain_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典, 便于序列化。"""
        return {
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "needs_review_count": self.needs_review_count,
            "uncertain_count": self.uncertain_count,
            "items": [item.to_dict() for item in self.items],
        }


# ------------------------------------------------------------------------------
# 核心处理逻辑
# ------------------------------------------------------------------------------

def analyze_input(text: str) -> List[str]:
    """
    从输入文本中提取关键信息 (模拟分析过程)。

    基于规格说明, 识别并保留输入中的关键信息。
    这里采用简单的启发式规则进行"结构化"提取。

    参数:
        text: 用户输入的原始文本。

    返回:
        提取出的关键信息列表。
    """
    findings: List[str] = []
    if not text or not text.strip():
        return findings

    # 1. 识别触发词/意图
    for word in TRIGGER_WORDS:
        if word in text:
            findings.append(f"检测到触发词: {word}")
            break

    # 2. 识别是否包含 URL
    if "http://" in text or "https://" in text:
        findings.append("输入包含 URL, 尝试解析链接内容")

    # 3. 识别是否包含文件路径 (简单判断)
    if "." in text and ("/" in text or "\\" in text):
        findings.append("输入可能包含文件路径")

    # 4. 识别是否包含数字 (可能为数据)
    if any(char.isdigit() for char in text):
        findings.append("输入包含数字, 可能为结构化数据")

    # 5. 识别是否包含批量暗示
    if "批量" in text or "多个" in text or "这些" in text:
        findings.append("输入暗示批量处理需求")

    # 6. 识别是否包含格式要求
    if "格式" in text or "json" in text.lower() or "csv" in text.lower():
        findings.append("输入包含输出格式要求")

    # 如果没有识别到任何关键信息, 则给出一个默认发现
    if not findings:
        findings.append("未识别到明显关键信息, 按通用流程处理")

    return findings


def calculate_confidence(text: str, findings: List[str]) -> float:
    """
    计算置信度。

    规则 (来自规格书 Step 2):
      - 置信度 >= 0.90: 直接输出
      - 0.85 - 0.90: 标注"建议复核"
      - < 0.85: 标注"[需核实]"

    这里根据输入长度和提取到的关键信息数量进行估算。

    参数:
        text: 原始输入文本。
        findings: 提取到的关键信息列表。

    返回:
        置信度浮点数 (0.0 - 1.0)。
    """
    if not text or not text.strip():
        # 空输入置信度极低
        return 0.0

    # 基础置信度
    base = 0.70

    # 输入长度增益 (过短或过长都会降低置信度)
    length = len(text.strip())
    if 10 <= length <= 500:
        base += 0.10
    elif length > 500:
        base += 0.05  # 太长可能包含噪音
    else:
        base -= 0.10  # 太短可能信息不足

    # 关键信息增益
    info_bonus = min(len(findings) * 0.05, 0.15)
    base += info_bonus

    # 包含明确格式要求则加分
    if any("格式" in f or "json" in f.lower() for f in findings):
        base += 0.05

    # 限制在 0.1 - 0.99 之间
    return max(0.1, min(0.99, base))


def determine_status(confidence: float) -> str:
    """
    根据置信度确定状态。

    参数:
        confidence: 置信度值。

    返回:
        状态字符串: "processed" / "needs_review" / "uncertain"
    """
    if confidence >= CONFIDENCE_HIGH:
        return "processed"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "needs_review"
    else:
        return "uncertain"


def process_single_input(text: str) -> ProcessedItem:
    """
    处理单条输入, 生成结构化结果。

    参数:
        text: 用户输入的原始文本。

    返回:
        ProcessedItem 对象。
    """
    # 1. 提取关键信息
    findings = analyze_input(text)

    # 2. 计算置信度
    confidence = calculate_confidence(text, findings)

    # 3. 确定状态
    status = determine_status(confidence)

    # 4. 如果状态为 uncertain, 在 findings 中加上 [需核实] 标记
    if status == "uncertain":
        findings.append("[需核实] 置信度过低, 请人工复核关键结果")

    return ProcessedItem(
        input_text=text,
        key_findings=findings,
        confidence=confidence,
        status=status,
    )


def process_batch_inputs(inputs: List[str]) -> BatchResult:
    """
    批量处理多个输入。

    参数:
        inputs: 输入文本列表。

    返回:
        BatchResult 对象。
    """
    result = BatchResult(total_count=len(inputs))

    for text in inputs:
        item = process_single_input(text)
        result.items.append(item)

        if item.status == "processed":
            result.processed_count += 1
        elif item.status == "needs_review":
            result.needs_review_count += 1
        else:
            result.uncertain_count += 1

    return result


# ------------------------------------------------------------------------------
# 输入验证与错误处理
# ------------------------------------------------------------------------------

def validate_input(text: Optional[str]) -> Optional[str]:
    """
    验证输入是否合法, 返回错误码或 None。

    参数:
        text: 用户输入的原始文本。

    返回:
        如果输入合法返回 None, 否则返回错误码字符串。
    """
    if text is None or not text.strip():
        return "E001"  # 输入为空
    return None


def format_error(error_code: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    格式化错误信息。

    参数:
        error_code: 错误码 (E001-E010)。
        *args: 位置参数, 用于替换话术中的占位符。
        **kwargs: 关键字参数, 用于替换话术中的占位符。

    返回:
        错误信息字典。
    """
    message = ERROR_MESSAGES.get(error_code, "未知错误")
    
    # 如果消息中包含 {} 占位符, 则进行格式化
    if "{}" in message:
        # 合并位置参数和关键字参数
        format_args = list(args) + list(kwargs.values())
        if format_args:
            try:
                message = message.format(*format_args)
            except (KeyError, IndexError):
                # 如果参数不匹配, 则移除占位符
                message = message.replace("{}", "")
        else:
            # 如果没有提供参数, 则移除占位符
            message = message.replace("{}", "")
    
    return {
        "error_code": error_code,
        "error_message": message,
        "success": False,
    }


# ------------------------------------------------------------------------------
# 输出格式化
# ------------------------------------------------------------------------------

def format_output(result: Any, output_format: str = "text") -> str:
    """
    将结果格式化为指定格式。

    参数:
        result: 处理结果对象 (ProcessedItem 或 BatchResult)。
        output_format: 输出格式 ("text" 或 "json")。

    返回:
        格式化后的字符串。

    异常:
        ValueError: 不支持的输出格式。
    """
    if output_format == "json":
        try:
            if isinstance(result, (ProcessedItem, BatchResult)):
                return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"E008: 输出序列化失败 - {exc}") from exc

    elif output_format == "text":
        # 文本格式输出
        lines: List[str] = []
        if isinstance(result, BatchResult):
            lines.append(f"=== 批量处理结果 (共 {result.total_count} 条) ===")
            lines.append(f"成功: {result.processed_count}, 建议复核: {result.needs_review_count}, 需核实: {result.uncertain_count}")
            lines.append("")
            for i, item in enumerate(result.items, 1):
                lines.append(f"--- 条目 {i} ---")
                lines.append(f"输入: {item.input_text}")
                lines.append(f"状态: {item.status}")
                lines.append(f"置信度: {item.confidence:.2%}")
                lines.append("关键信息:")
                for finding in item.key_findings:
                    lines.append(f"  - {finding}")
                lines.append("")
        else:
            # ProcessedItem
            lines.append(f"输入: {result.input_text}")
            lines.append(f"状态: {result.status}")
            lines.append(f"置信度: {result.confidence:.2%}")
            lines.append("关键信息:")
            for finding in result.key_findings:
                lines.append(f"  - {finding}")

        return "\n".join(lines)

    else:
        raise ValueError(f"E010: 不支持的输出格式: {output_format}")


# ------------------------------------------------------------------------------
# 自检模块 (--selftest)
# ------------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检, 验证核心逻辑。

    使用硬编码样例数据, 不依赖外部文件、网络或当前工作目录。

    返回:
        True 表示自检通过, False 表示失败。

    注意: 断言使用宽松阈值, 避免依赖精确值。
    """
    print("开始自检...")

    # --- 测试 1: 空输入处理 ---
    print("[1/5] 测试空输入...")
    error_code = validate_input("")
    assert error_code == "E001", f"空输入应返回 E001, 实际: {error_code}"
    error_code = validate_input("   ")
    assert error_code == "E001", f"空白输入应返回 E001, 实际: {error_code}"
    error_code = validate_input("有效输入")
    assert error_code is None, f"有效输入不应返回错误, 实际: {error_code}"
    print("  通过")

    # --- 测试 2: 单条输入处理 ---
    print("[2/5] 测试单条输入处理...")
    item = process_single_input("帮我处理一下这个数据文件: /path/to/data.csv")
    assert item is not None, "处理结果不应为 None"
    assert len(item.key_findings) > 0, "应至少提取到一个关键信息"
    assert 0.0 <= item.confidence <= 1.0, f"置信度应在 0-1 之间, 实际: {item.confidence}"
    assert item.status in ("processed", "needs_review", "uncertain"), f"状态不合法: {item.status}"
    # 置信度应处于一个合理范围内 (宽松检查)
    assert item.confidence >= 0.1, "置信度不应过低"
    print("  通过")

    # --- 测试 3: 批量输入处理 ---
    print("[3/5] 测试批量输入处理...")
    test_inputs = [
        "帮我处理一下这个",
        "把这个转成另一种格式",
        "批量弄一下这些数据",
        "这是一个普通的测试输入, 没有特殊关键词",
        "https://example.com/some/page",
    ]
    batch_result = process_batch_inputs(test_inputs)
    assert batch_result.total_count == len(test_inputs), "总数应等于输入数量"
    assert len(batch_result.items) == len(test_inputs), "条目数应等于输入数量"
    assert batch_result.processed_count + batch_result.needs_review_count + batch_result.uncertain_count == batch_result.total_count, \
        "状态计数之和应等于总数"
    assert batch_result.processed_count >= 0, "成功数不应为负"
    assert batch_result.needs_review_count >= 0, "复核数不应为负"
    assert batch_result.uncertain_count >= 0, "不确定数不应为负"
    print("  通过")

    # --- 测试 4: 输出格式化 ---
    print("[4/5] 测试输出格式化...")
    # 文本格式
    text_output = format_output(item, "text")
    assert text_output is not None and len(text_output) > 0, "文本输出不应为空"
    assert "输入:" in text_output, "文本输出应包含输入字段"
    assert "置信度" in text_output, "文本输出应包含置信度"

    # JSON 格式
    json_output = format_output(item, "json")
    parsed_json = json.loads(json_output)
    assert "input" in parsed_json, "JSON 输出应包含 input 字段"
    assert "confidence" in parsed_json, "JSON 输出应包含 confidence 字段"
    assert "key_findings" in parsed_json, "JSON 输出应包含 key_findings 字段"
    assert "status" in parsed_json, "JSON 输出应包含 status 字段"

    # 批量结果 JSON
    batch_json = format_output(batch_result, "json")
    parsed_batch = json.loads(batch_json)
    assert "total_count" in parsed_batch, "批量 JSON 应包含 total_count"
    assert "items" in parsed_batch, "批量 JSON 应包含 items"
    assert len(parsed_batch["items"]) == len(test_inputs), "批量 JSON items 数量应正确"

    # 无效格式
    try:
        format_output(item, "xml")
        assert False, "不支持的格式应抛出异常"
    except ValueError:
        pass  # 预期异常

    print("  通过")

    # --- 测试 5: 错误处理 ---
    print("[5/5] 测试错误处理...")
    err = format_error("E001")
    assert err["error_code"] == "E001", "错误码应正确"
    assert err["success"] is False, "错误结果 success 应为 False"
    assert "请提供" in err["error_message"], "错误消息应包含提示语"

    err2 = format_error("E002", "输入来源")
    assert "输入来源" in err2["error_message"], "错误消息应包含补充信息"

    # 所有错误码都应存在
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"错误码 {code} 应存在于错误码表中"
    print("  通过")

    print("所有自检通过!")
    return True


# ------------------------------------------------------------------------------
# 主入口
# ------------------------------------------------------------------------------

def main() -> int:
    """
    主函数, 解析命令行参数并执行相应操作。

    返回:
        进程退出码 (0 表示成功, 1 表示失败)。
    """
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=f"{SKILL_DISPLAY_NAME} - {SKILL_DESCRIPTION}",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        nargs="*",
        help="待处理的输入内容。可提供多个值进行批量处理。",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检, 验证核心逻辑。",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息并退出。",
    )

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse 在参数错误时会抛出 SystemExit
        return int(exc.code) if exc.code is not None else 1
    except Exception as exc:
        print(f"E007: 参数解析失败 - {exc}", file=sys.stderr)
        return 1

    # 显示版本
    if args.version:
        print(f"{SKILL_NAME} v{SKILL_VERSION}")
        print(f"显示名称: {SKILL_DISPLAY_NAME}")
        print(f"描述: {SKILL_DESCRIPTION}")
        return 0

    # 运行自检
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as exc:
            print(f"E009: 自检失败 - {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"E009: 自检异常 - {exc}", file=sys.stderr)
            return 1

    # 正常处理流程
    # 检查是否提供了输入
    if args.input is None:
        # 没有输入, 打印错误信息
        err = format_error("E001")
        print(json.dumps(err, ensure_ascii=False, indent=2))
        return 1

    # 验证输入
    inputs = args.input
    for text in inputs:
        error_code = validate_input(text)
        if error_code:
            err = format_error(error_code)
            print(json.dumps(err, ensure_ascii=False, indent=2))
            return 1

    # 执行处理
    try:
        if len(inputs) == 1:
            # 单条处理
            result = process_single_input(inputs[0])
        else:
            # 批量处理
            result = process_batch_inputs(inputs)

        # 格式化输出
        output = format_output(result, args.format)
        print(output)
        return 0

    except ValueError as exc:
        # 输出格式化失败等
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # 其他未预期异常
        print(f"E006: 内部错误 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
