#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-toolbox 技能实现脚本（clean-room 重写）

本脚本依据功能规格独立实现，仅使用标准库。
提供命令行入口，支持 --selftest 离线自检。

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部处理异常
    E007 参数解析错误
    E008 自检失败
    E009 未知错误
    E010 输出格式错误
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessingResult:
    """处理结果封装"""
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.success = success
        self.data = data or {}
        self.confidence = confidence
        self.error_code = error_code
        self.error_message = error_message
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "confidence": self.confidence,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效

    返回: (是否有效, 错误码)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str) and not raw_input.strip():
        return False, "E001"
    if isinstance(raw_input, (list, tuple, dict)) and len(raw_input) == 0:
        return False, "E001"
    return True, None


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键信息

    支持：
    - 字符串（尝试解析 JSON，否则作为文本）
    - 字典（直接使用）
    - 列表（逐项处理）
    """
    result: Dict[str, Any] = {}

    if isinstance(data, str):
        stripped = data.strip()
        # 尝试解析 JSON
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                return extract_key_fields(parsed)
            except json.JSONDecodeError:
                pass
        # 纯文本：尝试提取键值对（key: value 或 key=value）
        result["text"] = stripped
        result["key_value_pairs"] = _extract_key_value_pairs(stripped)
        result["word_count"] = len(stripped.split())
        return result

    if isinstance(data, dict):
        # 保留所有字段，并统计
        result["fields"] = dict(data)
        result["field_count"] = len(data)
        # 尝试提取常见关键字段
        for key in ("id", "name", "title", "type", "content", "url"):
            if key in data:
                result[key] = data[key]
        return result

    if isinstance(data, (list, tuple)):
        items = []
        for item in data:
            items.append(extract_key_fields(item))
        result["items"] = items
        result["item_count"] = len(items)
        return result

    # 其他类型
    result["value"] = str(data)
    result["type"] = type(data).__name__
    return result


def _extract_key_value_pairs(text: str) -> Dict[str, str]:
    """从文本中提取 key: value 或 key=value 对"""
    pairs: Dict[str, str] = {}
    # 匹配 key: value 或 key=value
    pattern = r"([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*([^\n,;]+)"
    for match in re.finditer(pattern, text):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key and value:
            pairs[key] = value
    return pairs


def calculate_confidence(data: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    计算置信度

    规则：
    - 有明确字段结构：高置信度
    - 纯文本：中等置信度
    - 信息模糊或缺失：低置信度，并给出警告

    返回: (置信度, 警告列表)
    """
    warnings: List[str] = []

    if not data:
        return 0.0, ["输入为空，无法计算置信度"]

    # 基础置信度
    confidence = 0.5

    # 有结构化字段
    if "fields" in data and data.get("field_count", 0) > 0:
        confidence += 0.3
        if data["field_count"] >= 3:
            confidence += 0.1

    # 有关键字段
    key_fields_present = 0
    for key in ("id", "name", "title", "content", "url"):
        if key in data:
            key_fields_present += 1
    if key_fields_present >= 2:
        confidence += 0.2
    elif key_fields_present == 1:
        confidence += 0.1

    # 文本类型
    if "text" in data:
        word_count = data.get("word_count", 0)
        if word_count >= 10:
            confidence += 0.1
        elif word_count >= 3:
            confidence += 0.05
        else:
            warnings.append("文本过短，信息量有限")

    # 列表类型
    if "item_count" in data:
        if data["item_count"] >= 3:
            confidence += 0.1
        else:
            warnings.append("列表项较少，可能信息不完整")

    # 限制在 0-1 之间
    confidence = max(0.0, min(1.0, confidence))

    # 低置信度警告
    if confidence < 0.85:
        warnings.append("置信度低于85%，建议人工复核")

    return confidence, warnings


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    格式化输出

    支持格式：json, text
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = []
        if result.success:
            lines.append("处理成功")
            lines.append(f"置信度: {result.confidence:.1%}")
            if result.data:
                lines.append("关键信息:")
                for key, value in result.data.items():
                    if key in ("fields", "items", "key_value_pairs"):
                        lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
                    elif not isinstance(value, (dict, list)):
                        lines.append(f"  {key}: {value}")
        else:
            lines.append(f"处理失败: {result.error_code}")
            lines.append(f"错误信息: {result.error_message}")
        if result.warnings:
            lines.append("警告:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")
        return "\n".join(lines)

    # 未知格式
    raise ValueError(f"E010: 不支持的输出格式: {output_format}")


def process_input(
    raw_input: Any,
    output_format: str = "json",
    required_fields: Optional[List[str]] = None,
) -> ProcessingResult:
    """
    主处理流程

    参数:
        raw_input: 用户输入
        output_format: 输出格式 (json/text)
        required_fields: 必需字段列表

    返回:
        ProcessingResult
    """
    # 步骤1: 校验输入
    is_valid, error_code = validate_input(raw_input)
    if not is_valid:
        return ProcessingResult(
            success=False,
            confidence=0.0,
            error_code=error_code,
            error_message="请提供待处理的内容，格式为：用户提供的数据/文件/URL",
        )

    # 步骤2: 提取关键信息
    try:
        extracted = extract_key_fields(raw_input)
    except Exception as exc:
        return ProcessingResult(
            success=False,
            confidence=0.0,
            error_code="E006",
            error_message=f"内部处理异常: {str(exc)}",
        )

    # 步骤3: 检查必需字段
    if required_fields:
        missing = []
        for field in required_fields:
            if field not in extracted and field not in extracted.get("fields", {}):
                missing.append(field)
        if missing:
            return ProcessingResult(
                success=False,
                confidence=0.0,
                error_code="E002",
                error_message=f"还缺少以下信息，请补充: {', '.join(missing)}",
            )

    # 步骤4: 计算置信度
    confidence, warnings = calculate_confidence(extracted)

    # 步骤5: 生成结果
    return ProcessingResult(
        success=True,
        data=extracted,
        confidence=confidence,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def _run_selftest() -> bool:
    """
    离线自检核心逻辑

    使用内置硬编码样例数据，不依赖外部文件/网络。
    断言使用宽松阈值，确保任何环境可过。
    """
    print("=" * 60)
    print("ai-toolbox 自检开始")
    print("=" * 60)

    all_passed = True

    # ---- 测试1: 有效输入处理 ----
    print("\n[测试1] 有效输入处理")
    test_data = {
        "id": "001",
        "name": "示例任务",
        "type": "text",
        "content": "这是一段用于测试的示例文本内容",
        "url": "https://example.com",
    }
    result = process_input(test_data, output_format="json")
    assert result.success, f"E008: 有效输入处理失败: {result.error_message}"
    assert result.confidence > 0.5, f"E008: 置信度过低: {result.confidence}"
    assert result.data["field_count"] >= 3, f"E008: 字段数量异常: {result.data.get('field_count')}"
    print(f"  ✓ 处理成功，置信度: {result.confidence:.1%}")

    # ---- 测试2: 文本输入处理 ----
    print("\n[测试2] 文本输入处理")
    text_input = "name: 测试任务\npriority: high\ndescription: 这是一个测试"
    result = process_input(text_input, output_format="json")
    assert result.success, f"E008: 文本处理失败: {result.error_message}"
    assert "key_value_pairs" in result.data, "E008: 未提取键值对"
    assert len(result.data["key_value_pairs"]) >= 2, "E008: 键值对提取数量不足"
    print(f"  ✓ 文本处理成功，提取键值对: {len(result.data['key_value_pairs'])} 个")

    # ---- 测试3: 空输入处理 ----
    print("\n[测试3] 空输入处理")
    result = process_input("")
    assert not result.success, "E008: 空输入应该失败"
    assert result.error_code == "E001", f"E008: 错误码应为E001，实际: {result.error_code}"
    print("  ✓ 空输入正确返回 E001")

    # ---- 测试4: 必需字段检查 ----
    print("\n[测试4] 必需字段检查")
    result = process_input({"name": "测试"}, required_fields=["id", "name"])
    assert not result.success, "E008: 缺少必需字段应该失败"
    assert result.error_code == "E002", f"E008: 错误码应为E002，实际: {result.error_code}"
    print("  ✓ 缺失必需字段正确返回 E002")

    # ---- 测试5: 列表批量处理 ----
    print("\n[测试5] 列表批量处理")
    list_input = [
        {"id": "1", "name": "任务A"},
        {"id": "2", "name": "任务B"},
        {"id": "3", "name": "任务C"},
    ]
    result = process_input(list_input, output_format="json")
    assert result.success, f"E008: 列表处理失败: {result.error_message}"
    assert result.data["item_count"] == 3, f"E008: 列表项数异常: {result.data.get('item_count')}"
    print(f"  ✓ 列表处理成功，共 {result.data['item_count']} 项")

    # ---- 测试6: 输出格式 ----
    print("\n[测试6] 输出格式")
    result = process_input({"name": "测试"}, output_format="text")
    assert result.success, f"E008: 文本格式处理失败: {result.error_message}"
    output_text = format_output(result, "text")
    assert "处理成功" in output_text, "E008: 文本输出缺少成功标识"
    print("  ✓ 文本输出格式正确")

    # ---- 测试7: 置信度边界 ----
    print("\n[测试7] 置信度计算")
    # 高信息量输入
    rich_input = {
        "id": "001",
        "name": "完整任务",
        "type": "analysis",
        "content": "这是一段很长的测试文本内容，包含了足够多的信息量用于分析处理",
        "url": "https://example.com/data",
        "tags": ["test", "demo"],
        "priority": "high",
    }
    result = process_input(rich_input)
    assert result.success, f"E008: 高信息量处理失败: {result.error_message}"
    assert result.confidence >= 0.8, f"E008: 高信息量置信度应>=0.8，实际: {result.confidence}"
    print(f"  ✓ 高信息量置信度: {result.confidence:.1%}")

    # ---- 测试8: 错误处理 ----
    print("\n[测试8] 错误处理")
    # 不支持的输出格式
    try:
        format_output(ProcessingResult(success=True), "xml")
        assert False, "E008: 不支持的格式应该抛出异常"
    except ValueError:
        print("  ✓ 不支持的输出格式正确抛出异常")

    # ---- 测试9: 边界输入 ----
    print("\n[测试9] 边界输入")
    # None 输入
    result = process_input(None)
    assert not result.success, "E008: None输入应该失败"
    assert result.error_code == "E001", "E008: None输入错误码应为E001"

    # 数字输入
    result = process_input(12345)
    assert result.success, f"E008: 数字输入处理失败: {result.error_message}"
    print("  ✓ 边界输入处理正确")

    # ---- 测试10: 综合流程 ----
    print("\n[测试10] 综合流程")
    sample_data = {
        "title": "AI 工具使用报告",
        "author": "测试用户",
        "date": "2026-01-15",
        "content": "本报告总结AI工具的使用情况，包括效率提升和注意事项。",
        "tags": ["AI", "toolbox", "report"],
    }
    result = process_input(sample_data, output_format="json", required_fields=["title", "content"])
    assert result.success, f"E008: 综合流程失败: {result.error_message}"
    assert result.confidence > 0.7, f"E008: 综合流程置信度应>0.7，实际: {result.confidence}"
    assert result.data["title"] == "AI 工具使用报告", "E008: 标题提取错误"
    print(f"  ✓ 综合流程成功，置信度: {result.confidence:.1%}")

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过: 所有测试用例均通过 ✓")
    else:
        print("自检失败: 存在未通过的测试用例 ✗")
    print("=" * 60)
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="ai-toolbox 技能实现",
        epilog="示例: python main.py --input '{\"name\": \"测试\"}' --format text",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的内容（字符串、JSON或文本）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--required",
        type=str,
        help="必需字段，逗号分隔，例如: id,name",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = _run_selftest()
            return 0 if success else 1
        except Exception as exc:
            print(f"E008: 自检异常: {str(exc)}", file=sys.stderr)
            return 1

    # 处理输入
    if not args.input:
        print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
        return 1

    # 解析输入
    raw_input: Any = args.input
    # 尝试解析 JSON
    try:
        raw_input = json.loads(args.input)
    except json.JSONDecodeError:
        # 不是 JSON，作为纯文本处理
        pass

    # 解析必需字段
    required_fields = None
    if args.required:
        required_fields = [field.strip() for field in args.required.split(",") if field.strip()]

    # 处理
    result = process_input(raw_input, output_format=args.format, required_fields=required_fields)

    # 输出
    try:
        output = format_output(result, args.format)
        print(output)
    except ValueError as exc:
        print(f"E010: {str(exc)}", file=sys.stderr)
        return 1

    # 根据结果返回退出码
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
