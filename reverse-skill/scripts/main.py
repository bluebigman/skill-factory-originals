#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reverse-skill 独立实现脚本
===========================
依据功能规格 clean-room 重写，不复制任何既有代码。

功能概述：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

仅使用 Python 标准库，无第三方依赖。

用法示例：
    python scripts/main.py --input "hello world" --format json
    python scripts/main.py --selftest
    python scripts/main.py --batch "a,b,c" --format text
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码及标准化话术（依据规格第四部分）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：文本、URL、文件路径或逗号分隔的批量数据",
    "E004": "这超出了本工具的能力范围，建议使用专用工具或咨询专业人士",
    "E005": "结果无法确定，建议：提供更多上下文信息或人工复核",
    "E006": "内部处理错误，请重试或联系管理员",
    "E007": "输出格式不支持，支持格式：text / json / csv",
    "E008": "批量输入解析失败，请检查分隔符",
    "E009": "文件读取失败，请检查路径和权限",
    "E010": "参数组合错误，请检查命令行参数",
}

# 支持的输出格式
SUPPORTED_FORMATS = ("text", "json", "csv")

# 置信度阈值（依据规格第三部分）
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85

# 关键信息字段（依据规格功能描述）
KEY_FIELDS = ("input_source", "content_type", "content_length", "timestamp")


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(data: Any) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效。

    参数:
        data: 用户输入的内容

    返回:
        (是否有效, 错误码或None)
    """
    if data is None:
        return False, "E001"
    if isinstance(data, str) and not data.strip():
        return False, "E001"
    if isinstance(data, (list, tuple, dict)) and len(data) == 0:
        return False, "E001"
    return True, None


def detect_content_type(content: str) -> str:
    """
    识别输入内容的类型。

    参数:
        content: 输入字符串

    返回:
        内容类型描述
    """
    content = content.strip().lower()

    # URL 检测
    if content.startswith(("http://", "https://", "ftp://")):
        return "url"

    # 文件路径检测
    if content.startswith(("/", "./", "../", "~/")) or "\\" in content:
        if os.path.exists(content):
            return "file"
        return "file_path"

    # JSON 检测
    if content.startswith(("{", "[")):
        try:
            json.loads(content)
            return "json"
        except json.JSONDecodeError:
            pass

    # 数字检测
    try:
        float(content)
        return "number"
    except ValueError:
        pass

    # 布尔检测
    if content in ("true", "false"):
        return "boolean"

    # 默认视为文本
    return "text"


def extract_key_info(content: str) -> Dict[str, Any]:
    """
    从输入内容中提取关键信息。

    参数:
        content: 输入字符串

    返回:
        包含关键信息的字典
    """
    content_type = detect_content_type(content)
    info: Dict[str, Any] = {
        "content_type": content_type,
        "content_length": len(content),
        "is_empty": len(content.strip()) == 0,
        "has_url": "://" in content,
        "has_email": "@" in content and "." in content.split("@")[-1],
        "has_number": any(char.isdigit() for char in content),
        "word_count": len(content.split()),
        "line_count": len(content.splitlines()),
    }

    # 提取 URL
    if info["has_url"]:
        start = content.find("://")
        if start >= 0:
            end = content.find(" ", start)
            if end == -1:
                end = len(content)
            info["url"] = content[start - 4:end]  # 包含协议部分

    # 提取邮箱
    if info["has_email"]:
        import re
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(email_pattern, content)
        if match:
            info["email"] = match.group(0)

    return info


def calculate_confidence(content: str, info: Dict[str, Any]) -> float:
    """
    计算处理结果的置信度。

    参数:
        content: 原始输入
        info: 提取的信息

    返回:
        置信度分数 (0.0 - 1.0)
    """
    score = 0.5  # 基础分

    # 内容非空加分
    if not info["is_empty"]:
        score += 0.2

    # 内容类型明确加分
    if info["content_type"] != "text":
        score += 0.1

    # 有结构化特征加分
    if info["has_url"] or info["has_email"] or info["has_number"]:
        score += 0.1

    # 内容长度适中加分（不太短也不太长的更可靠）
    if 5 <= info["content_length"] <= 1000:
        score += 0.1

    return min(score, 1.0)


def format_confidence(score: float) -> str:
    """
    根据置信度生成标注文本。

    参数:
        score: 置信度分数

    返回:
        标注字符串
    """
    if score >= HIGH_CONFIDENCE:
        return "高置信度"
    elif score >= MEDIUM_CONFIDENCE:
        return "建议复核"
    else:
        return "[需核实]"


def build_result(content: str, output_format: str = "text") -> Dict[str, Any]:
    """
    构建结构化处理结果。

    参数:
        content: 输入内容
        output_format: 输出格式

    返回:
        结果字典
    """
    # 校验输入
    valid, error_code = validate_input(content)
    if not valid:
        return {
            "success": False,
            "error_code": error_code,
            "error_message": ERROR_MESSAGES[error_code],
        }

    # 提取信息
    info = extract_key_info(content)
    confidence = calculate_confidence(content, info)

    # 构建结果
    result = {
        "success": True,
        "data": {
            "input": content,
            "key_info": info,
            "processed": True,
        },
        "confidence": {
            "score": round(confidence, 2),
            "label": format_confidence(confidence),
        },
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "skill": "reverse-skill",
        },
    }

    return result


def format_output(result: Dict[str, Any], output_format: str = "text") -> str:
    """
    将结果格式化为指定格式的字符串。

    参数:
        result: 结果字典
        output_format: 输出格式

    返回:
        格式化后的字符串
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    if output_format == "csv":
        if not result.get("success"):
            return f"error_code,error_message\n{result.get('error_code')},{result.get('error_message')}"
        info = result["data"]["key_info"]
        lines = ["field,value"]
        for key, value in info.items():
            lines.append(f"{key},{value}")
        lines.append(f"confidence,{result['confidence']['score']}")
        lines.append(f"confidence_label,{result['confidence']['label']}")
        return "\n".join(lines)

    # text 格式
    if not result.get("success"):
        return f"错误: {result.get('error_code')} - {result.get('error_message')}"

    lines = [
        "=" * 50,
        "处理结果",
        "=" * 50,
        f"输入内容: {result['data']['input'][:100]}{'...' if len(result['data']['input']) > 100 else ''}",
        f"内容类型: {result['data']['key_info']['content_type']}",
        f"内容长度: {result['data']['key_info']['content_length']} 字符",
        f"词数: {result['data']['key_info']['word_count']}",
        f"行数: {result['data']['key_info']['line_count']}",
        "-" * 50,
        f"置信度: {result['confidence']['score']:.0%} ({result['confidence']['label']})",
        f"处理时间: {result['metadata']['timestamp']}",
        "=" * 50,
    ]
    return "\n".join(lines)


def process_batch(inputs: List[str], output_format: str = "text") -> str:
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        output_format: 输出格式

    返回:
        批量处理结果
    """
    results = []
    for i, item in enumerate(inputs, 1):
        result = build_result(item, output_format)
        result["metadata"]["batch_index"] = i
        results.append(result)

    if output_format == "json":
        return json.dumps({"batch_results": results}, ensure_ascii=False, indent=2)

    lines = [f"批量处理结果 (共 {len(results)} 项)", "=" * 50]
    for i, result in enumerate(results, 1):
        lines.append(f"\n--- 第 {i} 项 ---")
        lines.append(format_output(result, "text"))
    return "\n".join(lines)


# ============================================================
# 自测功能
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。

    返回:
        0 表示全部通过，1 表示有失败
    """
    print("开始自检...")
    failures = 0

    # ---- 测试用例 1: 基本文本输入 ----
    print("\n[测试 1] 基本文本输入")
    result = build_result("hello world this is a test")
    if result["success"]:
        assert result["data"]["key_info"]["content_type"] == "text", "内容类型应为 text"
        assert result["data"]["key_info"]["word_count"] >= 5, "词数应不少于 5"
        assert result["confidence"]["score"] > 0.5, "置信度应大于 0.5"
        print("  ✓ 通过")
    else:
        print("  ✗ 失败: 处理失败")
        failures += 1

    # ---- 测试用例 2: URL 输入 ----
    print("\n[测试 2] URL 输入")
    result = build_result("https://example.com/path?query=1")
    if result["success"]:
        assert result["data"]["key_info"]["content_type"] == "url", "内容类型应为 url"
        assert result["data"]["key_info"]["has_url"] is True, "应检测到 URL"
        print("  ✓ 通过")
    else:
        print("  ✗ 失败: 处理失败")
        failures += 1

    # ---- 测试用例 3: 空输入 ----
    print("\n[测试 3] 空输入")
    result = build_result("   ")
    if not result["success"]:
        assert result["error_code"] == "E001", "错误码应为 E001"
        print("  ✓ 通过")
    else:
        print("  ✗ 失败: 空输入应处理失败")
        failures += 1

    # ---- 测试用例 4: JSON 输入 ----
    print("\n[测试 4] JSON 输入")
    json_input = '{"name": "test", "value": 42}'
    result = build_result(json_input)
    if result["success"]:
        assert result["data"]["key_info"]["content_type"] == "json", "内容类型应为 json"
        print("  ✓ 通过")
    else:
        print("  ✗ 失败: JSON 处理失败")
        failures += 1

    # ---- 测试用例 5: 批量处理 ----
    print("\n[测试 5] 批量处理")
    batch_data = ["first item", "second item with more text", "https://example.com"]
    batch_result = process_batch(batch_data, "json")
    parsed = json.loads(batch_result)
    assert len(parsed["batch_results"]) == 3, "应有 3 个批量结果"
    print("  ✓ 通过")

    # ---- 测试用例 6: 输出格式 ----
    print("\n[测试 6] 输出格式")
    result = build_result("test content")
    text_output = format_output(result, "text")
    json_output = format_output(result, "json")
    csv_output = format_output(result, "csv")
    assert "处理结果" in text_output, "文本输出应包含标题"
    assert json.loads(json_output)["success"] is True, "JSON 输出应可解析"
    assert "field,value" in csv_output, "CSV 输出应包含表头"
    print("  ✓ 通过")

    # ---- 测试用例 7: 错误码 ----
    print("\n[测试 7] 错误码")
    assert ERROR_MESSAGES["E001"] != "", "E001 消息不应为空"
    assert ERROR_MESSAGES["E005"] != "", "E005 消息不应为空"
    assert "E001" in ERROR_MESSAGES, "应包含 E001"
    print("  ✓ 通过")

    # ---- 测试用例 8: 置信度阈值 ----
    print("\n[测试 8] 置信度阈值")
    high_conf = format_confidence(0.95)
    med_conf = format_confidence(0.87)
    low_conf = format_confidence(0.70)
    assert high_conf == "高置信度", "0.95 应为高置信度"
    assert med_conf == "建议复核", "0.87 应为建议复核"
    assert low_conf == "[需核实]", "0.70 应为需核实"
    print("  ✓ 通过")

    # ---- 测试用例 9: 数字输入 ----
    print("\n[测试 9] 数字输入")
    result = build_result("12345")
    if result["success"]:
        assert result["data"]["key_info"]["content_type"] == "number", "内容类型应为 number"
        assert result["data"]["key_info"]["has_number"] is True, "应检测到数字"
        print("  ✓ 通过")
    else:
        print("  ✗ 失败: 数字处理失败")
        failures += 1

    # ---- 测试用例 10: 长文本输入 ----
    print("\n[测试 10] 长文本输入")
    long_text = "word " * 100
    result = build_result(long_text)
    if result["success"]:
        assert result["data"]["key_info"]["word_count"] >= 50, "长文本词数应较多"
        assert result["confidence"]["score"] > 0.5, "长文本置信度应较高"
        print("  ✓ 通过")
    else:
        print("  ✗ 失败: 长文本处理失败")
        failures += 1

    # ---- 汇总 ----
    print("\n" + "=" * 50)
    if failures == 0:
        print("自检完成: 全部通过 ✓")
        return 0
    else:
        print(f"自检完成: {failures} 项失败 ✗")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。

    返回:
        解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="reverse-skill: 将输入转换为结构化结果",
        epilog="示例: python main.py --input 'hello' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本、URL、文件路径）",
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入，用逗号分隔",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=SUPPORTED_FORMATS,
        default="text",
        help=f"输出格式 (默认: text, 可选: {', '.join(SUPPORTED_FORMATS)})",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入",
    )
    return parser.parse_args()


def read_file(filepath: str) -> str:
    """
    读取文件内容。

    参数:
        filepath: 文件路径

    返回:
        文件内容字符串
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError) as e:
        raise RuntimeError(f"E009: {ERROR_MESSAGES['E009']} - {e}")


def main() -> int:
    """
    主入口函数。

    返回:
        退出码 (0 成功, 1 失败)
    """
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查参数组合
    input_count = sum([
        1 if args.input else 0,
        1 if args.batch else 0,
        1 if args.file else 0,
    ])
    if input_count == 0:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1
    if input_count > 1:
        print(f"E010: {ERROR_MESSAGES['E010']} - 只能指定 --input/--batch/--file 之一", file=sys.stderr)
        return 1

    try:
        # 处理不同输入模式
        if args.file:
            content = read_file(args.file)
            result = build_result(content, args.format)
            print(format_output(result, args.format))

        elif args.batch:
            items = [item.strip() for item in args.batch.split(",") if item.strip()]
            if not items:
                print(f"E008: {ERROR_MESSAGES['E008']}", file=sys.stderr)
                return 1
            print(process_batch(items, args.format))

        else:  # args.input
            result = build_result(args.input, args.format)
            print(format_output(result, args.format))

        return 0

    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E006: {ERROR_MESSAGES['E006']} - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
