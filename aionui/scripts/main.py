#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aionui 未命名工具 - 独立实现脚本
=================================
基于功能规格的 clean-room 实现，仅使用 Python 标准库。
支持命令行调用和 --selftest 离线自检。
"""

import argparse
import sys
import re
from typing import Dict, List, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class ErrorCode:
    """错误码常量定义"""
    E001_EMPTY_INPUT = "E001"
    E002_MISSING_INFO = "E002"
    E003_BAD_FORMAT = "E003"
    E004_OUT_OF_SCOPE = "E004"
    E005_LOW_CONFIDENCE = "E005"
    E006_INTERNAL = "E006"
    E007_OUTPUT_FAIL = "E007"
    E008_UNSUPPORTED = "E008"
    E009_EXTERNAL = "E009"
    E010_UNKNOWN = "E010"


ERROR_MESSAGES = {
    ErrorCode.E001_EMPTY_INPUT: "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    ErrorCode.E002_MISSING_INFO: "还缺少以下信息，请补充：",
    ErrorCode.E003_BAD_FORMAT: "输入格式不符合要求，示例：",
    ErrorCode.E004_OUT_OF_SCOPE: "这超出了本工具的能力范围，建议：",
    ErrorCode.E005_LOW_CONFIDENCE: "结果无法确定，建议：",
    ErrorCode.E006_INTERNAL: "内部处理错误，请重试",
    ErrorCode.E007_OUTPUT_FAIL: "输出生成失败，请检查参数",
    ErrorCode.E008_UNSUPPORTED: "不支持的输入类型或格式",
    ErrorCode.E009_EXTERNAL: "需要外部服务但未启用网络访问",
    ErrorCode.E010_UNKNOWN: "未知错误，请参考文档",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条处理结果"""
    def __init__(self, source: str, key_fields: Dict[str, Any], confidence: float, warnings: List[str] = None):
        self.source = source
        self.key_fields = key_fields
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "key_fields": self.key_fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class ProcessResult:
    """批量处理结果"""
    def __init__(self):
        self.items: List[ProcessedItem] = []
        self.errors: List[Tuple[str, str]] = []  # (错误码, 描述)

    def add_item(self, item: ProcessedItem) -> None:
        self.items.append(item)

    def add_error(self, code: str, message: str) -> None:
        self.errors.append((code, message))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _validate_input(raw_input: Any) -> Optional[str]:
    """校验输入，返回错误码或 None（通过）"""
    if raw_input is None:
        return ErrorCode.E001_EMPTY_INPUT
    if isinstance(raw_input, str) and not raw_input.strip():
        return ErrorCode.E001_EMPTY_INPUT
    if isinstance(raw_input, (list, tuple, dict)) and len(raw_input) == 0:
        return ErrorCode.E001_EMPTY_INPUT
    return None


def _extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从文本中提取关键信息。
    规则：
    - 识别形如 key: value 或 key=value 的字段
    - 识别常见命名实体（日期、数字、邮箱等）
    - 返回结构化字典
    """
    fields: Dict[str, Any] = {}

    # 1. 提取 key: value 或 key=value
    pattern = r'(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*([^\s,;]+)'
    for match in re.finditer(pattern, text):
        key, value = match.group(1), match.group(2)
        fields[key] = value

    # 2. 提取日期（YYYY-MM-DD 或 YYYY/MM/DD）
    date_match = re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text)
    if date_match:
        fields["date"] = date_match.group(0)

    # 3. 提取邮箱
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    if email_match:
        fields["email"] = email_match.group(0)

    # 4. 提取 URL
    url_match = re.search(r'https?://[^\s]+', text)
    if url_match:
        fields["url"] = url_match.group(0)

    # 5. 提取数字（第一个出现的数字）
    num_match = re.search(r'\d+', text)
    if num_match:
        fields["number"] = num_match.group(0)

    return fields


def _calculate_confidence(fields: Dict[str, Any], raw_text_len: int) -> float:
    """计算置信度（0-1）"""
    if not fields:
        return 0.0

    # 基础置信度
    base = min(0.6 + 0.1 * len(fields), 0.95)

    # 文本长度修正
    if raw_text_len < 10:
        base -= 0.2
    elif raw_text_len > 500:
        base += 0.02

    # 关键字段完整性
    if "date" in fields and "email" in fields:
        base += 0.03

    return max(0.0, min(1.0, base))


def _format_confidence_label(confidence: float) -> str:
    """根据置信度生成标注"""
    if confidence >= 0.90:
        return "直接输出"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


def process_single(raw_input: Any) -> ProcessedItem:
    """处理单条输入"""
    # 输入校验
    error_code = _validate_input(raw_input)
    if error_code:
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")

    # 转文本
    if isinstance(raw_input, str):
        text = raw_input
    elif isinstance(raw_input, (dict, list)):
        text = str(raw_input)
    else:
        text = str(raw_input)

    # 提取关键字段
    fields = _extract_key_fields(text)

    # 计算置信度
    confidence = _calculate_confidence(fields, len(text))

    # 生成警告
    warnings = []
    if confidence < 0.85:
        warnings.append("关键信息提取不完整，请人工复核")
    if not fields:
        warnings.append("未能识别结构化字段")

    return ProcessedItem(
        source=raw_input if isinstance(raw_input, str) else str(raw_input),
        key_fields=fields,
        confidence=confidence,
        warnings=warnings,
    )


def process_batch(inputs: List[Any]) -> ProcessResult:
    """批量处理"""
    result = ProcessResult()

    for item in inputs:
        try:
            processed = process_single(item)
            result.add_item(processed)
        except ValueError as e:
            code = str(e).split(":")[0] if ":" in str(e) else ErrorCode.E010_UNKNOWN
            result.add_error(code, str(e))

    return result


def format_output(result: ProcessResult, detailed: bool = False) -> str:
    """格式化输出结果"""
    if not result.items:
        return "没有可输出的结果"

    lines = []
    for i, item in enumerate(result.items, 1):
        lines.append(f"--- 条目 {i} ---")
        lines.append(f"来源: {item.source[:100]}{'...' if len(item.source) > 100 else ''}")

        if detailed:
            lines.append(f"关键字段: {item.key_fields}")
        else:
            keys = list(item.key_fields.keys())
            lines.append(f"识别字段: {', '.join(keys) if keys else '无'}")

        label = _format_confidence_label(item.confidence)
        lines.append(f"置信度: {item.confidence:.1%} ({label})")

        if item.warnings:
            lines.append(f"警告: {'; '.join(item.warnings)}")

        lines.append("")

    if result.errors:
        lines.append("=== 错误汇总 ===")
        for code, msg in result.errors:
            lines.append(f"[{code}] {msg}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def run_cli(args: argparse.Namespace) -> int:
    """CLI 主入口"""
    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    if args.input:
        # 支持多输入
        inputs = args.input
        result = process_batch(inputs)
        output = format_output(result, detailed=args.detailed)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            except OSError as e:
                print(f"[{ErrorCode.E007_OUTPUT_FAIL}] 写入文件失败: {e}", file=sys.stderr)
                return 1
        else:
            print(output)

        # 错误处理
        if result.errors:
            return 1
        return 0
    else:
        # 无输入，显示帮助
        parser.print_help()
        return 0


# ---------------------------------------------------------------------------
# 自检逻辑（硬编码样例，不依赖外部文件）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用硬编码样例，不读取外部文件，不访问网络。
    """
    test_cases = [
        # (输入, 期望至少识别字段数, 期望置信度下限)
        ("姓名: 张三, email: test@example.com, 日期: 2025-01-15", 3, 0.6),
        ("user=alice, score=85, url=https://example.com", 3, 0.6),
        ("简单文本没有结构化内容", 0, 0.0),
        ("联系 admin@test.org 或拨打 12345", 1, 0.4),
        ({"name": "test", "value": 42}, 0, 0.4),  # dict 输入
        ("", 0, 0.0),  # 空输入
    ]

    print("=== aionui 自检开始 ===")
    passed = True

    # 测试 1: 单条处理
    print("\n[测试1] 单条处理")
    for i, (input_data, min_fields, min_conf) in enumerate(test_cases[:4], 1):
        try:
            result = process_single(input_data)
            field_count = len(result.key_fields)
            conf_ok = result.confidence >= min_conf
            fields_ok = field_count >= min_fields

            status = "PASS" if (conf_ok and fields_ok) else "FAIL"
            if status == "FAIL":
                passed = False

            print(f"  用例{i}: {status} - 字段数={field_count}(需≥{min_fields}), "
                  f"置信度={result.confidence:.2f}(需≥{min_conf})")
        except ValueError as e:
            if i == len(test_cases) - 1:  # 空输入应该报错
                print(f"  用例{i}: PASS - 正确拒绝空输入")
            else:
                print(f"  用例{i}: FAIL - 意外错误: {e}")
                passed = False

    # 测试 2: 空输入处理
    print("\n[测试2] 空输入")
    try:
        process_single("")
        print("  FAIL - 空输入应抛出错误")
        passed = False
    except ValueError as e:
        code = str(e).split(":")[0]
        if code == ErrorCode.E001_EMPTY_INPUT:
            print(f"  PASS - 正确返回 {code}")
        else:
            print(f"  FAIL - 错误码不正确: {code}")
            passed = False

    # 测试 3: 批量处理
    print("\n[测试3] 批量处理")
    batch = ["name: Alice, email: a@b.com", "简单文本", "key=value"]
    result = process_batch(batch)
    if len(result.items) == 3:
        print(f"  PASS - 批量处理 {len(result.items)} 条")
    else:
        print(f"  FAIL - 期望3条，实际 {len(result.items)}")
        passed = False

    # 测试 4: 置信度计算
    print("\n[测试4] 置信度计算")
    high_conf = _calculate_confidence({"a": "1", "b": "2", "c": "3"}, 100)
    low_conf = _calculate_confidence({}, 5)
    if high_conf > 0.7 and low_conf < 0.3:
        print(f"  PASS - 高置信度={high_conf:.2f}, 低置信度={low_conf:.2f}")
    else:
        print(f"  FAIL - 置信度异常: 高={high_conf:.2f}, 低={low_conf:.2f}")
        passed = False

    # 测试 5: 字段提取
    print("\n[测试5] 字段提取")
    fields = _extract_key_fields("date: 2024-06-01, email: test@test.com, url: https://example.com")
    if "date" in fields and "email" in fields and "url" in fields:
        print(f"  PASS - 提取到 {len(fields)} 个字段: {list(fields.keys())}")
    else:
        print(f"  FAIL - 字段提取不完整: {fields}")
        passed = False

    # 测试 6: 错误码完整性
    print("\n[测试6] 错误码")
    all_codes = [getattr(ErrorCode, attr) for attr in dir(ErrorCode) if attr.startswith("E")]
    if len(all_codes) == 10 and all(code in ERROR_MESSAGES for code in all_codes):
        print(f"  PASS - 10个错误码全部定义")
    else:
        print(f"  FAIL - 错误码不完整")
        passed = False

    # 测试 7: 输出格式化
    print("\n[测试7] 输出格式化")
    sample_item = ProcessedItem("测试", {"key": "value"}, 0.9, [])
    sample_result = ProcessResult()
    sample_result.add_item(sample_item)
    output = format_output(sample_result)
    if "置信度" in output and "关键字段" in output:
        print("  PASS - 输出格式正确")
    else:
        print(f"  FAIL - 输出格式异常: {output}")
        passed = False

    # 总结
    print("\n=== 自检结束 ===")
    if passed:
        print("全部测试通过 ✅")
        return 0
    else:
        print("存在失败项 ❌")
        return 1


# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------
def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    global parser
    parser = argparse.ArgumentParser(
        description="aionui 未命名工具 - 数据/文本结构化处理",
        epilog="示例: python main.py --input '姓名: 张三, email: test@example.com' --detailed",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        help="输入内容（支持多条，空格分隔）",
    )
    parser.add_argument(
        "--output",
        help="输出文件路径（可选，默认输出到 stdout）",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="显示详细字段信息",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件）",
    )
    return parser


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主函数"""
    global parser
    parser = create_parser()
    args = parser.parse_args()

    try:
        return run_cli(args)
    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[{ErrorCode.E006_INTERNAL}] 内部错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
