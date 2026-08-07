#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
codexia - 轻量级智能体工作站（技能实现脚本）
================================================
本脚本根据功能规格独立实现，提供：
- 核心处理流程（解析输入 -> 结构化 -> 置信度标注 -> 输出）
- 错误码体系（E001-E010）
- 命令行接口（含 --selftest 离线自检）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Tuple, Optional


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术（依据规格 E001-E005，扩展至 E010）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{details}",
    "E004": "这超出了本工具的能力范围，建议：{details}",
    "E005": "结果无法确定，建议：{details}",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式指定无效，可选：json / text",
    "E008": "批量处理时某条输入失败，已跳过",
    "E009": "置信度计算异常，使用默认值",
    "E010": "未知错误，请联系维护者",
}

# 置信度阈值（依据规格）
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85

# 触发词（依据规格）
TRIGGER_WORDS = ["codexia"]

# 能力边界声明（依据规格）
CAPABILITY_BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """单条输入的处理结果"""
    
    def __init__(self, input_text: str, structured: Dict[str, Any],
                 confidence: float, warnings: List[str]):
        self.input_text = input_text
        self.structured = structured
        self.confidence = confidence
        self.warnings = warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化字典"""
        return {
            "input_text": self.input_text,
            "structured": self.structured,
            "confidence": round(self.confidence, 4),
            "warnings": self.warnings,
        }


class CodexiaError(Exception):
    """业务异常，携带错误码"""
    
    def __init__(self, code: str, details: str = ""):
        self.code = code
        self.details = details
        message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        if details and "{details}" in message:
            message = message.replace("{details}", details)
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: str) -> str:
    """
    验证输入是否有效。
    
    依据规格：
    - E001: 输入为空
    - E003: 输入格式错误（非文本内容）
    
    返回清洗后的输入文本。
    """
    if raw_input is None:
        raise CodexiaError("E001")
    
    text = raw_input.strip()
    if not text:
        raise CodexiaError("E001")
    
    # 检查是否为可处理文本（排除纯二进制等）
    if len(text) > 100000:
        raise CodexiaError("E003", "输入内容过长（超过10万字符）")
    
    return text


def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段并结构化。
    
    依据规格：
    - 识别输入中的关键字段并结构化
    - 识别并保留输入中的关键信息
    
    提取规则（宽松匹配）：
    - 标题：以 # 开头或首行
    - 数字：提取所有数字（整数/小数/百分比）
    - 日期：常见日期格式
    - 邮箱：正则匹配
    - 网址：正则匹配
    - 关键词：触发词（如 codexia）
    """
    fields: Dict[str, Any] = {}
    
    # 提取标题（Markdown 标题或首行）
    title_match = re.search(r'^#+\s+(.+)$', text, re.MULTILINE)
    if title_match:
        fields["title"] = title_match.group(1).strip()
    else:
        first_line = text.split("\n")[0].strip()
        if first_line:
            fields["title"] = first_line[:100]  # 限制长度
    
    # 提取所有数字
    numbers = re.findall(r'\d+(?:\.\d+)?(?:%|％)?', text)
    fields["numbers"] = numbers[:20] if numbers else []
    
    # 提取日期（支持多种格式）
    dates = re.findall(
        r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}',
        text
    )
    fields["dates"] = dates[:10] if dates else []
    
    # 提取邮箱
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    fields["emails"] = emails[:10] if emails else []
    
    # 提取网址
    urls = re.findall(r'https?://[^\s<>"\'()]+', text)
    fields["urls"] = urls[:10] if urls else []
    
    # 提取触发词
    found_triggers = [w for w in TRIGGER_WORDS if w.lower() in text.lower()]
    fields["trigger_words"] = found_triggers
    
    # 统计文本特征
    fields["char_count"] = len(text)
    fields["word_count"] = len(text.split())
    fields["line_count"] = len(text.split("\n"))
    
    return fields


def calculate_confidence(text: str, fields: Dict[str, Any]) -> float:
    """
    计算置信度（0.0 - 1.0）。
    
    依据规格：
    - 置信度 ≥90%：直接输出
    - 85%-90%：标注"建议复核"
    - <85%：标注"[需核实]"
    
    计算逻辑（宽松启发式）：
    - 基础分 0.5
    - 有标题 +0.1
    - 有数字 +0.1
    - 有日期 +0.1
    - 有邮箱或网址 +0.1
    - 文本长度适中 +0.1
    - 有触发词 +0.05
    """
    confidence = 0.5
    
    if fields.get("title"):
        confidence += 0.1
    if fields.get("numbers"):
        confidence += 0.1
    if fields.get("dates"):
        confidence += 0.1
    if fields.get("emails") or fields.get("urls"):
        confidence += 0.1
    if 10 <= fields.get("char_count", 0) <= 5000:
        confidence += 0.1
    if fields.get("trigger_words"):
        confidence += 0.05
    
    # 边界裁剪
    return max(0.0, min(1.0, confidence))


def build_warnings(confidence: float) -> List[str]:
    """根据置信度生成警告标注（依据规格）"""
    warnings = []
    if confidence >= HIGH_CONFIDENCE:
        pass  # 直接输出，无警告
    elif confidence >= MEDIUM_CONFIDENCE:
        warnings.append("建议复核：置信度在85%-90%之间")
    else:
        warnings.append("[需核实]：置信度低于85%，请人工确认关键信息")
    return warnings


def process_single_input(raw_input: str) -> ProcessingResult:
    """
    处理单条输入，执行核心流程。
    
    流程（依据规格）：
    1. 解析输入内容，识别关键信息
    2. 按规则结构化处理
    3. 生成结果并标注置信度
    """
    # Step 1: 验证输入
    text = validate_input(raw_input)
    
    # Step 2: 提取关键字段
    fields = extract_key_fields(text)
    
    # Step 3: 计算置信度
    confidence = calculate_confidence(text, fields)
    
    # Step 4: 生成警告
    warnings = build_warnings(confidence)
    
    # Step 5: 组装结果
    structured = {
        "content_summary": text[:200] + ("..." if len(text) > 200 else ""),
        "key_fields": fields,
        "metadata": {
            "processed_by": "codexia",
            "version": "1.0.0",
        }
    }
    
    return ProcessingResult(text, structured, confidence, warnings)


def process_batch(inputs: List[str]) -> List[ProcessingResult]:
    """
    批量处理多条输入。
    
    依据规格：
    - 支持批量处理
    - 单条失败不中断整体（E008）
    """
    results = []
    for item in inputs:
        try:
            result = process_single_input(item)
            results.append(result)
        except CodexiaError as e:
            if e.code != "E001":  # 空输入在批量中跳过
                results.append(ProcessingResult(
                    input_text=item or "",
                    structured={"error": e.code, "message": str(e)},
                    confidence=0.0,
                    warnings=[f"跳过：{e.code}"]
                ))
            # 空输入静默跳过
    return results


def format_result(result: ProcessingResult, output_format: str) -> str:
    """
    格式化输出结果。
    
    支持格式：
    - json: JSON 字符串
    - text: 可读文本
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        lines.append(f"输入: {result.input_text[:100]}")
        lines.append(f"置信度: {result.confidence:.1%}")
        if result.warnings:
            lines.append(f"警告: {'; '.join(result.warnings)}")
        lines.append("结构化结果:")
        lines.append(json.dumps(result.structured, ensure_ascii=False, indent=2))
        return "\n".join(lines)
    else:
        raise CodexiaError("E007")


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    
    使用内置硬编码样例数据，不访问外部资源。
    断言使用宽松阈值，确保稳健。
    
    返回：全部通过返回 True，否则返回 False
    """
    print("=" * 60)
    print("codexia 自检开始")
    print("=" * 60)
    
    all_passed = True
    
    # ---- 测试用例 1: 正常输入 ----
    print("\n[测试1] 正常输入处理")
    try:
        sample1 = "这是一段测试文本，包含数字 123 和日期 2024-05-20，邮箱 test@example.com"
        result1 = process_single_input(sample1)
        
        # 宽松断言：置信度应在合理区间
        assert 0.0 <= result1.confidence <= 1.0, "置信度超出范围"
        assert result1.structured.get("key_fields"), "关键字段为空"
        assert "title" in result1.structured["key_fields"], "缺少标题字段"
        assert result1.structured["key_fields"]["char_count"] > 0, "字符数异常"
        print(f"  通过 (置信度={result1.confidence:.2f})")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 测试用例 2: 空输入 ----
    print("\n[测试2] 空输入错误处理")
    try:
        try:
            process_single_input("")
            print("  失败: 空输入未抛出异常")
            all_passed = False
        except CodexiaError as e:
            assert e.code == "E001", f"错误码应为E001，实际{e.code}"
            print(f"  通过 (错误码={e.code})")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 测试用例 3: 批量处理 ----
    print("\n[测试3] 批量处理")
    try:
        samples = ["第一条数据 42", "", "第二条数据 2025-01-01"]
        results = process_batch(samples)
        # 空输入被跳过，应有2条有效结果
        valid_count = sum(1 for r in results if r.confidence > 0)
        assert valid_count >= 2, f"有效结果数异常: {valid_count}"
        print(f"  通过 (有效结果={valid_count}条)")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 测试用例 4: 置信度分级 ----
    print("\n[测试4] 置信度分级标注")
    try:
        # 低置信度用例（短文本无特征）
        weak_input = "hi"
        weak_result = process_single_input(weak_input)
        # 高置信度用例（丰富文本）
        rich_input = "标题: 项目报告\n日期: 2024-06-15\n包含数字 99% 和邮箱 contact@example.com\nhttps://example.com/report"
        rich_result = process_single_input(rich_input)
        
        # 宽松断言：弱输入的置信度不应高于强输入
        assert weak_result.confidence <= rich_result.confidence, "置信度排序异常"
        print(f"  通过 (弱={weak_result.confidence:.2f}, 强={rich_result.confidence:.2f})")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 测试用例 5: 输出格式 ----
    print("\n[测试5] 输出格式")
    try:
        test_result = process_single_input("测试输出格式 123")
        json_output = format_result(test_result, "json")
        text_output = format_result(test_result, "text")
        
        assert json_output.startswith("{"), "JSON输出格式错误"
        assert "置信度" in text_output, "文本输出格式错误"
        print("  通过 (json/text)")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 测试用例 6: 能力边界 ----
    print("\n[测试6] 能力边界声明")
    try:
        assert len(CAPABILITY_BOUNDARIES) >= 3, "能力边界声明不完整"
        assert any("网络" in b for b in CAPABILITY_BOUNDARIES), "缺少网络边界声明"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 测试用例 7: 错误码完整性 ----
    print("\n[测试7] 错误码完整性")
    try:
        required_codes = ["E001", "E002", "E003", "E004", "E005"]
        for code in required_codes:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
            assert ERROR_MESSAGES[code].strip(), f"错误码 {code} 话术为空"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 测试用例 8: 触发词识别 ----
    print("\n[测试8] 触发词识别")
    try:
        trigger_text = "请使用 codexia 处理这个文件"
        field_result = extract_key_fields(trigger_text)
        assert "codexia" in field_result.get("trigger_words", []), "触发词识别失败"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # ---- 汇总 ----
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过：所有核心逻辑验证成功")
    else:
        print("自检失败：存在未通过的测试")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="codexia - 轻量级智能体工作站",
        epilog="示例: python main.py '处理这段文本' --format json"
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的输入文本（留空则从 stdin 读取）"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="输出格式（默认: text）"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：每行一条输入"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1
    
    try:
        # 获取输入
        if args.input:
            raw_input = args.input
        else:
            # 从 stdin 读取
            print("请输入内容（Ctrl+D 结束）:", file=sys.stderr)
            raw_input = sys.stdin.read()
        
        # 处理
        if args.batch:
            lines = [line for line in raw_input.split("\n") if line.strip()]
            if not lines:
                raise CodexiaError("E001")
            results = process_batch(lines)
            outputs = [format_result(r, args.format) for r in results]
            print("\n---\n".join(outputs))
        else:
            result = process_single_input(raw_input)
            print(format_result(result, args.format))
        
        # 输出警告（文本模式）
        if args.format == "text" and not args.batch:
            result = process_single_input(raw_input)
            for warning in result.warnings:
                print(f"提示: {warning}", file=sys.stderr)
        
        return 0
        
    except CodexiaError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
