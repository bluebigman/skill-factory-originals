#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - agent-ready-repo 技能核心实现

基于功能规格的 clean-room 独立实现。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常
    E007: 参数解析异常
    E008: 自检断言失败
    E009: 未知错误
    E010: 配置错误
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 常量定义
# ============================================================

# 版权与许可证信息（依据规格）
COPYRIGHT_HOLDER = "原创作者（自持版权）"
SOURCE_PROJECT = "original"
LICENSE = "MIT"
VERSION = "1.0.0"
AUTHOR = "skill-factory-auto"
SLUG = "agent-ready-repo"
NAME = "agent-ready-repo"
DISPLAY_NAME = "未命名工具"

# 能力边界声明（依据规格）
CAPABILITIES = [
    "将用户提供的数据/文件/URL 转换为结构化结果",
    "识别并保留输入中的关键信息",
    "按约定格式生成输出",
    "对不确定项给出置信度提示",
    "支持批量处理和自定义格式",
]

BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]

# 触发词表（依据规格）
TRIGGER_WORDS = ["agent ready repo"]

# 置信度阈值（依据规格）
CONFIDENCE_HIGH = 0.90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
CONFIDENCE_LOW = 0.85       # <85% 标注 [需核实]

# 错误码与话术映射（依据规格）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 可识别的关键字段（内部定义）
KEY_FIELDS = ["id", "name", "type", "content", "url", "date", "author", "tags"]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果的数据结构。"""

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
    ):
        self.data = data if data is not None else {}
        self.confidence = max(0.0, min(1.0, confidence))
        self.warnings = warnings if warnings is not None else []
        self.errors = errors if errors is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    验证输入是否有效。

    返回：(是否有效, 错误码或 None)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str):
        if not raw_input.strip():
            return False, "E001"
    elif isinstance(raw_input, (list, tuple)):
        if len(raw_input) == 0:
            return False, "E001"
        if all(not str(item).strip() for item in raw_input):
            return False, "E001"
    elif isinstance(raw_input, dict):
        if len(raw_input) == 0:
            return False, "E001"
    else:
        # 其他类型（数字、布尔等）视为有效
        pass
    return True, None


def extract_key_fields(input_data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段。

    支持以下输入形式：
        - 字符串：尝试解析 JSON，否则按文本处理
        - 字典：直接提取已知字段
        - 列表：逐项处理
        - 其他：转为字符串表示
    """
    result: Dict[str, Any] = {}
    warnings: List[str] = []

    if isinstance(input_data, dict):
        # 字典输入：提取已知字段
        for field in KEY_FIELDS:
            if field in input_data:
                result[field] = input_data[field]
        # 保留其他字段
        for key, value in input_data.items():
            if key not in result:
                result[key] = value
    elif isinstance(input_data, str):
        # 字符串输入：尝试解析 JSON
        try:
            parsed = json.loads(input_data)
            if isinstance(parsed, dict):
                result = extract_key_fields(parsed)
            else:
                result["content"] = input_data
                result["type"] = "text"
        except json.JSONDecodeError:
            # 不是 JSON，按纯文本处理
            result["content"] = input_data
            result["type"] = "text"
            # 尝试提取 URL
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, input_data)
            if urls:
                result["url"] = urls[0]
                result["type"] = "url"
    elif isinstance(input_data, (list, tuple)):
        # 列表输入：逐项处理
        items = []
        for item in input_data:
            item_result = extract_key_fields(item)
            items.append(item_result)
        result["items"] = items
        result["type"] = "list"
        result["count"] = len(items)
    else:
        # 其他类型
        result["content"] = str(input_data)
        result["type"] = type(input_data).__name__

    return result


def calculate_confidence(input_data: Any, extracted: Dict[str, Any]) -> float:
    """
    计算置信度。

    规则（依据规格）：
        - 输入完整且提取成功：高置信度
        - 部分字段缺失：中等置信度
        - 无法提取有效信息：低置信度
    """
    if not extracted:
        return 0.0

    # 基础置信度
    confidence = 0.9

    # 根据输入类型调整
    if isinstance(input_data, str):
        if len(input_data.strip()) < 10:
            confidence -= 0.1  # 输入过短
    elif isinstance(input_data, dict):
        # 字典输入：根据字段覆盖率调整
        filled_fields = sum(1 for field in KEY_FIELDS if field in input_data)
        if filled_fields == 0:
            confidence -= 0.2
        elif filled_fields <= 2:
            confidence -= 0.1
    elif isinstance(input_data, (list, tuple)):
        # 列表输入：根据项数调整
        if len(input_data) == 1:
            confidence -= 0.05
    else:
        confidence -= 0.1  # 非常规类型

    # 检查是否有足够内容
    has_content = any(
        key in extracted for key in ["content", "items", "url", "name"]
    )
    if not has_content:
        confidence -= 0.2

    return max(0.0, min(1.0, confidence))


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    按指定格式格式化输出结果。

    支持格式：json, text
    """
    if output_format == "json":
        return result.to_json()
    elif output_format == "text":
        lines = []
        # 数据部分
        if result.data:
            lines.append("=== 处理结果 ===")
            for key, value in result.data.items():
                lines.append(f"{key}: {value}")
        # 置信度
        confidence_pct = int(result.confidence * 100)
        lines.append(f"\n置信度: {confidence_pct}%")
        # 警告
        if result.warnings:
            lines.append("\n警告:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")
        # 置信度标注（依据规格）
        if result.confidence >= CONFIDENCE_HIGH:
            pass  # 直接输出
        elif result.confidence >= CONFIDENCE_MEDIUM:
            lines.append("\n[建议复核]")
        else:
            lines.append("\n[需核实]")
        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")


def process_single(input_data: Any, output_format: str = "json") -> ProcessingResult:
    """
    处理单个输入项。
    """
    # Step 1: 验证输入
    valid, error_code = validate_input(input_data)
    if not valid:
        result = ProcessingResult(
            data={"error": error_code},
            confidence=0.0,
            errors=[error_code],
        )
        return result

    # Step 2: 提取关键字段
    extracted = extract_key_fields(input_data)

    # Step 3: 计算置信度
    confidence = calculate_confidence(input_data, extracted)

    # Step 4: 生成结果
    warnings = []
    if confidence < CONFIDENCE_MEDIUM:
        warnings.append("输入信息不完整，结果可能不准确")

    result = ProcessingResult(
        data=extracted,
        confidence=confidence,
        warnings=warnings,
    )

    return result


def process_batch(input_list: List[Any], output_format: str = "json") -> ProcessingResult:
    """
    批量处理多个输入项。
    """
    # 验证批量输入
    valid, error_code = validate_input(input_list)
    if not valid:
        return ProcessingResult(
            data={"error": error_code},
            confidence=0.0,
            errors=[error_code],
        )

    # 逐项处理
    items = []
    total_confidence = 0.0
    warnings = []

    for i, item in enumerate(input_list):
        item_result = process_single(item, output_format)
        items.append(item_result.to_dict())
        total_confidence += item_result.confidence
        warnings.extend(item_result.warnings)

    # 计算平均置信度
    avg_confidence = total_confidence / len(input_list) if input_list else 0.0

    result = ProcessingResult(
        data={
            "type": "batch",
            "count": len(input_list),
            "items": items,
        },
        confidence=avg_confidence,
        warnings=warnings,
    )

    return result


def process_input(input_data: Any, output_format: str = "json") -> ProcessingResult:
    """
    统一入口：处理用户输入。

    支持单个输入或批量输入（列表）。
    """
    # 检查是否超出能力边界
    if isinstance(input_data, bytes):
        # 二进制数据不在支持范围内
        return ProcessingResult(
            data={"error": "E004"},
            confidence=0.0,
            errors=["E004"],
        )

    # 判断是单个输入还是批量输入
    if isinstance(input_data, list) and len(input_data) > 1:
        return process_batch(input_data, output_format)
    elif isinstance(input_data, list) and len(input_data) == 1:
        return process_single(input_data[0], output_format)
    else:
        return process_single(input_data, output_format)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    内置自检功能。使用硬编码样例数据离线验证核心逻辑。

    返回：True 表示自检通过，False 表示失败。
    """
    print("开始自检...")
    all_passed = True

    # 测试用例 1: 有效的单条文本输入
    print("\n[测试 1] 单条文本输入")
    test_input = "这是一个测试内容，包含一些关键信息"
    try:
        result = process_input(test_input)
        assert result.confidence > 0.5, "置信度应大于 0.5"
        assert "content" in result.data, "应提取到 content 字段"
        assert result.confidence > 0.5, "置信度应大于 0.5"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 2: 有效的字典输入
    print("\n[测试 2] 字典输入")
    test_dict = {
        "name": "测试项目",
        "type": "document",
        "content": "项目说明文档",
        "author": "张三",
    }
    try:
        result = process_input(test_dict)
        assert result.confidence > 0.5, "置信度应大于 0.5"
        assert result.data.get("name") == "测试项目", "应保留 name 字段"
        assert result.data.get("type") == "document", "应保留 type 字段"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 3: JSON 字符串输入
    print("\n[测试 3] JSON 字符串输入")
    test_json = '{"name": "JSON项目", "content": "JSON内容", "tags": ["测试", "json"]}'
    try:
        result = process_input(test_json)
        assert result.confidence > 0.5, "置信度应大于 0.5"
        assert "name" in result.data, "应解析出 name 字段"
        assert "tags" in result.data, "应解析出 tags 字段"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 4: URL 文本输入
    print("\n[测试 4] URL 文本输入")
    test_url = "请查看 https://example.com/page 这个链接"
    try:
        result = process_input(test_url)
        assert result.confidence > 0.5, "置信度应大于 0.5"
        assert "url" in result.data, "应提取出 url 字段"
        assert "url" in result.data, "应提取出 url 字段"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 5: 批量输入
    print("\n[测试 5] 批量输入")
    test_batch = [
        "第一条文本",
        {"name": "项目A", "content": "内容A"},
        "https://example.org/doc",
    ]
    try:
        result = process_input(test_batch)
        assert result.confidence > 0.5, "批量处理置信度应大于 0.5"
        assert result.data.get("type") == "batch", "应识别为批量处理"
        assert result.data.get("count") == 3, "应包含 3 个条目"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 6: 空输入（错误码 E001）
    print("\n[测试 6] 空输入处理")
    try:
        result = process_input("")
        assert result.confidence < 0.5, "空输入置信度应较低"
        assert result.errors, "应包含错误信息"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 7: 输出格式化
    print("\n[测试 7] 输出格式化")
    test_data = {"name": "格式化测试", "content": "测试内容"}
    try:
        result = process_input(test_data)
        json_output = format_output(result, "json")
        assert isinstance(json_output, str), "JSON 输出应为字符串"
        assert '"name"' in json_output, "JSON 输出应包含 name 字段"

        text_output = format_output(result, "text")
        assert isinstance(text_output, str), "文本输出应为字符串"
        assert "格式化测试" in text_output, "文本输出应包含数据内容"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 8: 置信度阈值判断
    print("\n[测试 8] 置信度阈值判断")
    try:
        # 高置信度输入
        high_conf_input = {
            "name": "完整项目",
            "type": "document",
            "content": "完整的内容描述",
            "author": "作者",
            "date": "2026-01-01",
            "tags": ["tag1", "tag2"],
        }
        high_result = process_input(high_conf_input)
        assert high_result.confidence > 0.5, "完整输入置信度应较高"

        # 低置信度输入
        low_result = process_input("短")
        assert low_result.confidence > 0.0, "即使短输入也应有正置信度"

        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 9: 边界情况 - 超出能力范围
    print("\n[测试 9] 超出能力范围")
    try:
        # 二进制数据不在支持范围内
        result = process_input(b"\x00\x01\x02")
        assert result.data.get("error") == "E004", "应返回 E004 错误码"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 10: 错误码映射
    print("\n[测试 10] 错误码映射")
    try:
        assert "E001" in ERROR_MESSAGES, "E001 应存在"
        assert "E002" in ERROR_MESSAGES, "E002 应存在"
        assert "E003" in ERROR_MESSAGES, "E003 应存在"
        assert "E004" in ERROR_MESSAGES, "E004 应存在"
        assert "E005" in ERROR_MESSAGES, "E005 应存在"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 总结
    print("\n" + "=" * 40)
    if all_passed:
        print("自检全部通过 ✓")
        return True
    else:
        print("自检存在失败项 ✗")
        return False


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数。
    """
    parser = argparse.ArgumentParser(
        description="agent-ready-repo 技能实现 - 将输入转换为结构化结果",
        epilog="示例: python main.py --input '待处理内容' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的内容（文本、JSON 字符串或 URL）",
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
        help="运行内置自检，验证核心逻辑",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息",
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        return 0
    except Exception:
        print("参数解析失败", file=sys.stderr)
        return 7  # E007

    # 显示版本信息
    if args.version:
        print(f"agent-ready-repo v{VERSION}")
        print(f"作者: {AUTHOR}")
        print(f"许可证: {LICENSE}")
        return 0

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 8  # E008

    # 处理输入
    if not args.input:
        # 尝试从标准输入读取
        if not sys.stdin.isatty():
            input_data = sys.stdin.read().strip()
            if not input_data:
                print(ERROR_MESSAGES["E001"], file=sys.stderr)
                return 1  # E001
        else:
            print(ERROR_MESSAGES["E001"], file=sys.stderr)
            return 1  # E001
    else:
        input_data = args.input

    # 尝试解析 JSON 输入（如果是 JSON 格式）
    try:
        if input_data.strip().startswith(("{", "[")):
            parsed_input = json.loads(input_data)
        else:
            parsed_input = input_data
    except json.JSONDecodeError:
        parsed_input = input_data

    # 处理输入
    try:
        result = process_input(parsed_input, args.format)
        output = format_output(result, args.format)
        print(output)
        return 0
    except ValueError as e:
        print(f"E003: {e}", file=sys.stderr)
        return 3  # E003
    except Exception as e:
        print(f"E006: 内部处理异常 - {e}", file=sys.stderr)
        return 6  # E006


if __name__ == "__main__":
    sys.exit(main())
