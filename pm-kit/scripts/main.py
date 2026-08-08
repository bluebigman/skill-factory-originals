#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm-kit 工具实现脚本
功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理和自定义格式。
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "JSON 解析失败，请检查输入格式",
    "E008": "URL 处理失败，本工具不访问网络",
    "E009": "输出格式不支持",
    "E010": "内部处理异常",
}


class PMKitError(Exception):
    """pm-kit 自定义异常类"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息并结构化。

    参数:
        raw_input: 原始输入字符串（JSON 格式或普通文本）

    返回:
        结构化数据字典

    异常:
        PMKitError: E001 输入为空, E003 格式错误, E007 JSON解析失败
    """
    if not raw_input or not raw_input.strip():
        raise PMKitError("E001")

    stripped = raw_input.strip()

    # 尝试解析为 JSON
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            return {"items": data}
        elif isinstance(data, str):
            # JSON 字符串但内容不是对象/数组，按文本处理
            return {"text": data}
        else:
            # JSON 数字、布尔值等，视为格式错误
            raise PMKitError("E003", "输入应为 JSON 对象或数组")
    except json.JSONDecodeError:
        # 非 JSON 格式，按文本处理
        # 但需要检查是否包含明显的 JSON 特征（如 { 或 [），如果是则报错
        if stripped.startswith('{') or stripped.startswith('['):
            # 尝试用 json.JSONDecoder 的 raw_decode 来进一步判断
            try:
                # 如果 raw_decode 能成功解析出至少一个有效 JSON 值，则说明是合法 JSON 前缀
                decoder = json.JSONDecoder()
                _, end = decoder.raw_decode(stripped)
                # 如果解析后还有剩余内容，说明格式有问题
                if end < len(stripped):
                    raise PMKitError("E007", "JSON 解析失败，请检查输入格式")
                # 如果完全解析成功，但上面 json.loads 失败了，说明是单个值（如数字、字符串等）
                # 这种情况已经在上面处理了，这里不会到达
                raise PMKitError("E007", "JSON 解析失败，请检查输入格式")
            except (json.JSONDecodeError, ValueError):
                raise PMKitError("E007", "JSON 解析失败，请检查输入格式")
            # 如果 raw_decode 成功且没有剩余内容，但 json.loads 失败，说明是单个 JSON 值（数字/字符串等）
            # 这种情况已经在上面处理了，这里不会到达
            raise PMKitError("E007", "JSON 解析失败，请检查输入格式")
        return {"text": stripped}


def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从输入数据中提取关键字段。

    参数:
        data: 结构化输入数据

    返回:
        包含关键字段的字典
    """
    result: Dict[str, Any] = {}

    # 识别常见关键字段
    key_fields = ["title", "name", "id", "date", "author", "content", "status", "priority"]
    for field in key_fields:
        if field in data:
            result[field] = data[field]

    # 处理嵌套结构
    if "items" in data and isinstance(data["items"], list):
        processed_items = []
        for item in data["items"]:
            if isinstance(item, dict):
                item_fields = {k: v for k, v in item.items() if k in key_fields}
                processed_items.append(item_fields if item_fields else item)
            else:
                processed_items.append(item)
        result["items"] = processed_items
        result["item_count"] = len(processed_items)

    # 处理文本输入
    if "text" in data:
        text = data["text"]
        result["text"] = text
        # 提取基本信息
        result["word_count"] = len(text.split())
        result["char_count"] = len(text)

    return result


def calculate_confidence(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    计算置信度并返回标注信息。

    参数:
        data: 提取的关键字段数据

    返回:
        (置信度百分比, 标注信息)
    """
    confidence = 90.0  # 默认基础置信度

    # 根据字段完整性调整置信度
    required_fields = ["title", "content"] if "title" in data or "content" in data else []
    if required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            confidence -= 10 * len(missing)

    # 根据数据量调整
    if "item_count" in data:
        if data["item_count"] > 10:
            confidence += 5
        elif data["item_count"] < 3:
            confidence -= 5

    if "text" in data and data.get("word_count", 0) < 10:
        confidence -= 10

    # 限制在合理范围
    confidence = max(60.0, min(98.0, confidence))

    # 生成标注
    if confidence >= 90:
        label = "直接输出"
    elif confidence >= 85:
        label = "建议复核"
    else:
        label = "[需核实]"

    return round(confidence, 1), label


def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式生成输出。

    参数:
        data: 处理后的数据
        output_format: 输出格式（json/text/markdown）

    返回:
        格式化后的输出字符串

    异常:
        PMKitError: E009 不支持的输出格式
    """
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        for key, value in data.items():
            if key == "items" and isinstance(value, list):
                lines.append(f"{key}:")
                for i, item in enumerate(value, 1):
                    lines.append(f"  {i}. {item}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    elif output_format == "markdown":
        md_lines = ["# 处理结果", ""]
        for key, value in data.items():
            if key == "items" and isinstance(value, list):
                md_lines.append(f"## {key}")
                for i, item in enumerate(value, 1):
                    md_lines.append(f"{i}. {item}")
                md_lines.append("")
            else:
                md_lines.append(f"**{key}**: {value}")
                md_lines.append("")
        return "\n".join(md_lines)
    else:
        raise PMKitError("E009", f"不支持的输出格式: {output_format}")


def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    主处理流程：解析输入 → 提取关键信息 → 计算置信度 → 生成输出。

    参数:
        raw_input: 原始输入
        output_format: 输出格式

    返回:
        处理结果字典
    """
    # Step 1: 解析输入
    data = parse_input(raw_input)

    # Step 2: 提取关键字段
    result = extract_key_fields(data)

    # Step 3: 计算置信度
    confidence, label = calculate_confidence(result)
    result["confidence"] = confidence
    result["confidence_label"] = label

    # Step 4: 生成输出
    try:
        output = format_output(result, output_format)
        result["output"] = output
    except PMKitError as e:
        # 输出格式错误时回退到 JSON
        result["output"] = format_output(result, "json")
        result["format_error"] = e.error_code

    return result


def batch_process(inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        output_format: 输出格式

    返回:
        处理结果列表
    """
    results = []
    for i, raw_input in enumerate(inputs, 1):
        try:
            result = process_input(raw_input, output_format)
            result["batch_index"] = i
            results.append(result)
        except PMKitError as e:
            results.append({
                "batch_index": i,
                "error": e.error_code,
                "error_message": e.message,
                "raw_input": raw_input
            })
    return results


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据验证核心功能。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("开始自检...")
    
    # 测试用例 1: 基本 JSON 输入
    test_input_1 = json.dumps({
        "title": "测试项目",
        "content": "这是一个测试内容",
        "priority": "high",
        "date": "2026-01-01"
    })
    
    try:
        result = process_input(test_input_1)
        assert result.get("title") == "测试项目", "标题提取失败"
        assert result.get("content") == "这是一个测试内容", "内容提取失败"
        assert result.get("priority") == "high", "优先级提取失败"
        assert result.get("confidence", 0) >= 80, "置信度应不低于 80"
        assert "output" in result, "缺少输出字段"
        print("测试用例 1 (基本JSON输入) 通过 ✓")
    except AssertionError as e:
        print(f"测试用例 1 失败: {e}")
        return False
    except PMKitError as e:
        print(f"测试用例 1 异常: {e}")
        return False
    
    # 测试用例 2: 批量输入
    test_inputs = [
        json.dumps({"title": "任务A", "status": "进行中"}),
        json.dumps({"title": "任务B", "status": "已完成"}),
        "普通文本输入测试"
    ]
    
    try:
        batch_results = batch_process(test_inputs)
        assert len(batch_results) == 3, "批量处理数量错误"
        assert all("batch_index" in r for r in batch_results), "缺少批次索引"
        assert all(r.get("title") or r.get("text") for r in batch_results), "批量处理内容异常"
        print("测试用例 2 (批量输入) 通过 ✓")
    except AssertionError as e:
        print(f"测试用例 2 失败: {e}")
        return False
    except PMKitError as e:
        print(f"测试用例 2 异常: {e}")
        return False
    
    # 测试用例 3: 错误处理
    try:
        # 空输入
        process_input("")
        print("测试用例 3 失败: 空输入未抛出异常")
        return False
    except PMKitError as e:
        assert e.error_code == "E001", f"错误码应为 E001，实际为 {e.error_code}"
    
    try:
        # 无效 JSON（以 { 开头但格式错误）
        process_input("这不是JSON{{{")
        print("测试用例 3 失败: 无效JSON未抛出异常")
        return False
    except PMKitError as e:
        assert e.error_code in ("E003", "E007"), f"错误码应为 E003 或 E007，实际为 {e.error_code}"
    
    print("测试用例 3 (错误处理) 通过 ✓")
    
    # 测试用例 4: 输出格式
    try:
        test_data = {"title": "格式测试", "content": "测试内容"}
        result_json = process_input(json.dumps(test_data), "json")
        result_text = process_input(json.dumps(test_data), "text")
        result_md = process_input(json.dumps(test_data), "markdown")
        
        assert "{" in result_json.get("output", ""), "JSON 格式错误"
        assert "title" in result_text.get("output", ""), "文本格式错误"
        assert "#" in result_md.get("output", ""), "Markdown 格式错误"
        print("测试用例 4 (输出格式) 通过 ✓")
    except AssertionError as e:
        print(f"测试用例 4 失败: {e}")
        return False
    except PMKitError as e:
        print(f"测试用例 4 异常: {e}")
        return False
    
    # 测试用例 5: 置信度计算
    try:
        # 完整数据 - 高置信度
        complete_data = {"title": "完整项目", "content": "详细内容描述", "author": "张三"}
        result = process_input(json.dumps(complete_data))
        assert result.get("confidence", 0) >= 85, "完整数据置信度应较高"
        
        # 不完整数据 - 较低置信度
        incomplete_data = {"title": "只有标题"}
        result2 = process_input(json.dumps(incomplete_data))
        assert result2.get("confidence", 100) <= 90, "不完整数据置信度应较低"
        
        print("测试用例 5 (置信度计算) 通过 ✓")
    except AssertionError as e:
        print(f"测试用例 5 失败: {e}")
        return False
    except PMKitError as e:
        print(f"测试用例 5 异常: {e}")
        return False
    
    print("\n所有自检测试通过 ✓")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数。

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="pm-kit 工具：将用户提供的数据/文件/URL 转换为结构化结果",
        epilog="示例: python main.py --input '{\"title\": \"测试\"}' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容（JSON 字符串或文本）")
    parser.add_argument("--file", "-f", help="从文件读取输入")
    parser.add_argument("--format", "-fmt", default="json", choices=["json", "text", "markdown"],
                        help="输出格式（默认: json）")
    parser.add_argument("--batch", "-b", help="批量处理文件（每行一个输入）")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version="pm-kit 1.0.0")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 收集输入
    raw_input = None
    
    if args.input:
        raw_input = args.input
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except (IOError, OSError) as e:
            print(f"[E006] 文件读取失败: {e}", file=sys.stderr)
            return 1
    elif args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                inputs = [line.strip() for line in f if line.strip()]
            results = batch_process(inputs, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except (IOError, OSError) as e:
            print(f"[E006] 文件读取失败: {e}", file=sys.stderr)
            return 1
    else:
        # 没有输入参数时，尝试从 stdin 读取
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
        else:
            print("请提供输入内容。使用 --help 查看帮助。", file=sys.stderr)
            print(ERROR_CODES["E001"], file=sys.stderr)
            return 1
    
    # 处理输入
    try:
        result = process_input(raw_input, args.format)
        print(result.get("output", json.dumps(result, ensure_ascii=False, indent=2)))
        return 0
    except PMKitError as e:
        print(f"[{e.error_code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 内部处理异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
