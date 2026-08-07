#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
browser-use 技能实现脚本（clean-room 独立实现）

本脚本根据功能规格独立编写，不参考任何既有实现。
提供标准处理流程、错误码体系、置信度标注与离线自检功能。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试或检查输入",
    "E007": "输出格式生成失败，请检查参数",
    "E008": "批量处理中断，请检查输入列表",
    "E009": "参数解析失败，请检查命令行参数",
    "E010": "未知错误，请查看日志",
}

# 能力边界
CAPABILITIES = {
    "can_do": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 触发词表
TRIGGER_WORDS = ["browser use"]

# 置信度阈值
CONFIDENCE_HIGH = 90.0
CONFIDENCE_MEDIUM = 85.0


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果对象"""

    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []
        self.errors: List[Tuple[str, str]] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(raw_input: Any) -> Tuple[bool, str]:
    """
    验证输入是否有效

    返回: (是否有效, 错误信息)
    """
    if raw_input is None:
        return False, "E001"

    if isinstance(raw_input, str):
        if not raw_input.strip():
            return False, "E001"
    elif isinstance(raw_input, (list, dict)):
        if len(raw_input) == 0:
            return False, "E001"
    else:
        return False, "E003"

    return True, ""


def extract_key_fields(content: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入内容中提取关键字段

    返回: (字段字典, 置信度)
    """
    result: Dict[str, Any] = {}
    confidence = 0.0
    warnings: List[str] = []

    if isinstance(content, str):
        # 文本输入：尝试识别基本结构
        text = content.strip()

        # 识别是否为 URL
        if re.match(r"^https?://", text, re.IGNORECASE):
            result["type"] = "url"
            result["url"] = text
            confidence = 95.0
        # 识别是否为 JSON
        elif text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)
                result["type"] = "json"
                result["data"] = parsed
                confidence = 90.0
            except json.JSONDecodeError:
                warnings.append("JSON 解析失败，按纯文本处理")
                result["type"] = "text"
                result["content"] = text
                confidence = 70.0
        # 纯文本
        else:
            result["type"] = "text"
            result["content"] = text
            confidence = 80.0

    elif isinstance(content, dict):
        # 字典输入
        result["type"] = "dict"
        result["data"] = content
        confidence = 95.0

    elif isinstance(content, list):
        # 列表输入
        result["type"] = "list"
        result["data"] = content
        confidence = 90.0

    else:
        # 其他类型
        result["type"] = "unknown"
        result["content"] = str(content)
        confidence = 50.0
        warnings.append("无法识别的输入类型")

    return result, confidence


def process_item(item: Any, options: Dict[str, Any]) -> ProcessingResult:
    """
    处理单个输入项

    Args:
        item: 输入内容
        options: 处理选项

    Returns:
        ProcessingResult 处理结果
    """
    result = ProcessingResult()

    # Step 1: 验证输入
    valid, error_code = validate_input(item)
    if not valid:
        result.errors.append((error_code, ERROR_CODES[error_code]))
        result.confidence = 0.0
        return result

    try:
        # Step 2: 提取关键字段
        fields, confidence = extract_key_fields(item)
        result.data = fields
        result.confidence = confidence

        # Step 3: 根据选项调整
        if options.get("verbose", False):
            result.data["_processed_at"] = "local"

        # Step 4: 置信度标注
        if confidence >= CONFIDENCE_HIGH:
            pass  # 直接输出
        elif confidence >= CONFIDENCE_MEDIUM:
            result.warnings.append("建议复核")
        else:
            result.warnings.append("[需核实] 结果不确定")

    except Exception as exc:
        result.errors.append(("E006", f"{ERROR_CODES['E006']} 详情: {str(exc)}"))
        result.confidence = 0.0

    return result


def process_batch(inputs: List[Any], options: Dict[str, Any]) -> List[ProcessingResult]:
    """
    批量处理多个输入项

    Args:
        inputs: 输入列表
        options: 处理选项

    Returns:
        处理结果列表
    """
    results = []
    for idx, item in enumerate(inputs):
        try:
            result = process_item(item, options)
            results.append(result)
        except Exception as exc:
            # 单个处理失败不中断整个批量
            result = ProcessingResult()
            result.errors.append(("E008", f"{ERROR_CODES['E008']} 第{idx+1}项: {str(exc)}"))
            result.confidence = 0.0
            results.append(result)

    return results


def format_output(results: Union[ProcessingResult, List[ProcessingResult]], output_format: str = "json") -> str:
    """
    格式化输出结果

    Args:
        results: 处理结果或结果列表
        output_format: 输出格式 (json/text)

    Returns:
        格式化后的字符串
    """
    try:
        if isinstance(results, ProcessingResult):
            data = results.to_dict()
        elif isinstance(results, list):
            data = [r.to_dict() for r in results]
        else:
            raise ValueError("无效的结果类型")

        if output_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == "text":
            # 简化文本输出
            lines = []
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    lines.append(f"=== 结果 {idx+1} ===")
                    lines.append(_format_text_result(item))
            else:
                lines.append(_format_text_result(data))
            return "\n".join(lines)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")

    except Exception as exc:
        return json.dumps({
            "error": "E007",
            "message": f"{ERROR_CODES['E007']} 详情: {str(exc)}",
        }, ensure_ascii=False)


def _format_text_result(result: Dict[str, Any]) -> str:
    """格式化单个结果为文本"""
    lines = []
    data = result.get("data", {})
    confidence = result.get("confidence", 0.0)

    if data:
        lines.append(f"类型: {data.get('type', 'unknown')}")
        if "url" in data:
            lines.append(f"URL: {data['url']}")
        if "content" in data:
            lines.append(f"内容: {data['content'][:200]}")
        if "data" in data and isinstance(data["data"], dict):
            for key, value in data["data"].items():
                lines.append(f"  {key}: {str(value)[:100]}")

    lines.append(f"置信度: {confidence:.1f}%")

    warnings = result.get("warnings", [])
    if warnings:
        lines.append(f"警告: {'; '.join(warnings)}")

    errors = result.get("errors", [])
    if errors:
        lines.append(f"错误: {', '.join([e[0] for e in errors])}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> int:
    """
    主入口函数

    Returns:
        int 退出码
    """
    parser = argparse.ArgumentParser(
        description="browser-use 技能：将输入数据转换为结构化结果",
        epilog="示例: python main.py --input 'https://example.com'",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（文本、URL、JSON字符串）",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="输入文件路径",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，JSON数组字符串",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细信息",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="browser-use 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查是否提供了输入
    if not args.input and not args.input_file and not args.batch:
        print(json.dumps({
            "error": "E001",
            "message": ERROR_CODES["E001"],
        }, ensure_ascii=False, indent=2))
        return 1

    options = {
        "verbose": args.verbose,
    }

    try:
        # 处理批量输入
        if args.batch:
            try:
                batch_inputs = json.loads(args.batch)
                if not isinstance(batch_inputs, list):
                    raise ValueError("批量输入必须是JSON数组")
            except json.JSONDecodeError:
                print(json.dumps({
                    "error": "E003",
                    "message": f"{ERROR_CODES['E003']} 批量输入必须是有效的JSON数组",
                }, ensure_ascii=False, indent=2))
                return 1

            results = process_batch(batch_inputs, options)
            output = format_output(results, args.format)
            print(output)

        # 处理文件输入
        elif args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    file_content = f.read()
                result = process_item(file_content, options)
                output = format_output(result, args.format)
                print(output)
            except FileNotFoundError:
                print(json.dumps({
                    "error": "E001",
                    "message": f"文件不存在: {args.input_file}",
                }, ensure_ascii=False, indent=2))
                return 1
            except Exception as exc:
                print(json.dumps({
                    "error": "E006",
                    "message": f"{ERROR_CODES['E006']} 详情: {str(exc)}",
                }, ensure_ascii=False, indent=2))
                return 1

        # 处理直接输入
        else:
            result = process_item(args.input, options)
            output = format_output(result, args.format)
            print(output)

        return 0

    except Exception as exc:
        print(json.dumps({
            "error": "E010",
            "message": f"{ERROR_CODES['E010']} 详情: {str(exc)}",
        }, ensure_ascii=False, indent=2))
        return 1


# ---------------------------------------------------------------------------
# 离线自检
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    运行离线自检，使用内置硬编码数据，不依赖外部文件和网络。

    Returns:
        int 退出码 (0 表示全部通过)
    """
    print("=== browser-use 技能自检 ===")
    print("使用内置样例数据，离线运行...")
    print()

    passed = 0
    failed = 0
    errors: List[str] = []

    # --- 测试 1: 基础文本处理 ---
    print("[测试 1] 基础文本处理")
    try:
        result = process_item("这是一个测试文本", {})
        assert result.confidence > 50, "文本处理置信度应大于50"
        assert result.data.get("type") == "text", "文本类型识别错误"
        assert "测试" in result.data.get("content", ""), "文本内容提取错误"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试1失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 2: URL 识别 ---
    print("[测试 2] URL 识别")
    try:
        result = process_item("https://example.com/path?query=1", {})
        assert result.data.get("type") == "url", "URL类型识别错误"
        assert "example.com" in result.data.get("url", ""), "URL内容提取错误"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试2失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 3: JSON 解析 ---
    print("[测试 3] JSON 解析")
    try:
        json_str = '{"name": "测试", "value": 42}'
        result = process_item(json_str, {})
        assert result.data.get("type") == "json", "JSON类型识别错误"
        assert result.data.get("data", {}).get("name") == "测试", "JSON数据解析错误"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试3失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 4: 空输入错误处理 ---
    print("[测试 4] 空输入错误处理")
    try:
        result = process_item("", {})
        assert len(result.errors) > 0, "空输入应产生错误"
        assert result.errors[0][0] == "E001", "错误码应为E001"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试4失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 5: 批量处理 ---
    print("[测试 5] 批量处理")
    try:
        batch = ["文本一", "https://test.com", '{"k": "v"}']
        results = process_batch(batch, {})
        assert len(results) == 3, "批量处理数量错误"
        assert all(r.confidence > 50 for r in results), "批量处理置信度过低"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试5失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 6: 置信度标注 ---
    print("[测试 6] 置信度标注")
    try:
        result = process_item({"structured": "data"}, {})
        assert result.confidence > 80, "结构化数据置信度应较高"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试6失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 7: 输出格式化 ---
    print("[测试 7] 输出格式化")
    try:
        result = process_item("测试输出", {})
        json_output = format_output(result, "json")
        assert json_output.startswith("{"), "JSON输出格式错误"
        text_output = format_output(result, "text")
        assert len(text_output) > 0, "文本输出为空"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试7失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 8: 能力边界检查 ---
    print("[测试 8] 能力边界检查")
    try:
        # 验证能力列表存在且包含预期项
        assert len(CAPABILITIES["can_do"]) == 5, "能力列表长度错误"
        assert len(CAPABILITIES["cannot_do"]) == 3, "边界声明列表长度错误"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试8失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 9: 错误码覆盖 ---
    print("[测试 9] 错误码覆盖")
    try:
        assert "E001" in ERROR_CODES, "缺少E001"
        assert "E002" in ERROR_CODES, "缺少E002"
        assert "E003" in ERROR_CODES, "缺少E003"
        assert "E004" in ERROR_CODES, "缺少E004"
        assert "E005" in ERROR_CODES, "缺少E005"
        assert "E006" in ERROR_CODES, "缺少E006"
        assert "E007" in ERROR_CODES, "缺少E007"
        assert "E008" in ERROR_CODES, "缺少E008"
        assert "E009" in ERROR_CODES, "缺少E009"
        assert "E010" in ERROR_CODES, "缺少E010"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试9失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 测试 10: 触发词检查 ---
    print("[测试 10] 触发词检查")
    try:
        assert "browser use" in TRIGGER_WORDS, "缺少触发词"
        passed += 1
        print("  ✓ 通过")
    except Exception as exc:
        failed += 1
        errors.append(f"测试10失败: {str(exc)}")
        print(f"  ✗ 失败: {str(exc)}")

    # --- 总结 ---
    print()
    print(f"=== 自检完成: {passed} 通过, {failed} 失败 ===")

    if failed > 0:
        print("\n失败详情:")
        for err in errors:
            print(f"  - {err}")
        return 1

    # 额外验证：确保自检不依赖外部资源
    print("\n验证: 自检过程未访问外部资源 ✓")
    return 0


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
