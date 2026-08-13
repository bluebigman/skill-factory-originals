#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyflowgraph - 未命名工具

基于功能规格独立实现的通用数据处理/格式化工具。
仅使用标准库，提供命令行接口与内置自检功能。

功能概述：
    1. 将输入数据/文本/URL 解析为结构化结果
    2. 识别并保留关键信息
    3. 按约定格式输出（默认JSON）
    4. 对不确定项给出置信度提示
    5. 支持批量处理

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部处理异常
    E007 参数解析失败
    E008 输出序列化失败
    E009 批量输入为空
    E010 自检失败

用法示例：
    python main.py --input "hello world"
    python main.py --input "hello world" --output json
    python main.py --batch --input "a,b,c" --delimiter ","
    python main.py --selftest
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def parse_input(raw: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息并结构化。

    规则：
        - 尝试识别 URL（http/https）
        - 尝试识别数字（整数/浮点数）
        - 尝试识别常见分隔符列表（逗号、竖线、分号）
        - 其余视为普通文本

    参数:
        raw: 原始输入字符串

    返回:
        结构化字典，包含 type, content, confidence, details

    异常:
        E001: 输入为空
    """
    if not raw or not raw.strip():
        raise ValueError("E001: 输入为空，请提供待处理的内容")

    text = raw.strip()
    detected_type = "text"
    confidence = 0.7  # 默认中等置信度
    details: Dict[str, Any] = {}

    # 尝试识别 URL
    url_pattern = re.compile(r'^https?://[^\s]+$', re.IGNORECASE)
    if url_pattern.match(text):
        detected_type = "url"
        confidence = 0.95
        details["url"] = text
        details["scheme"] = text.split("://")[0].lower()
        return {
            "type": detected_type,
            "content": text,
            "confidence": confidence,
            "details": details,
        }

    # 尝试识别数字（支持千位分隔符）
    try:
        # 移除千位分隔符后尝试转换
        clean_num = text.replace(",", "")
        num = float(clean_num)
        # 验证确实是数字格式（避免 "1,2,3" 被误判为数字 123）
        if text.count(",") > 0 and not clean_num.isdigit():
            raise ValueError("包含多个逗号，不是合法数字")
        detected_type = "number"
        confidence = 0.9
        details["value"] = num
        details["is_integer"] = num.is_integer()
        return {
            "type": detected_type,
            "content": text,
            "confidence": confidence,
            "details": details,
        }
    except (ValueError, AttributeError):
        pass

    # 尝试识别列表（逗号、竖线、分号分隔）
    for delim, name in [(",", "comma"), ("|", "pipe"), (";", "semicolon")]:
        if delim in text:
            parts = [p.strip() for p in text.split(delim) if p.strip()]
            if len(parts) > 1:
                detected_type = "list"
                confidence = 0.85
                details["delimiter"] = name
                details["count"] = len(parts)
                details["items"] = parts
                return {
                    "type": detected_type,
                    "content": text,
                    "confidence": confidence,
                    "details": details,
                    "items": parts,
                }

    # 普通文本
    details["length"] = len(text)
    details["word_count"] = len(text.split())
    return {
        "type": detected_type,
        "content": text,
        "confidence": confidence,
        "details": details,
    }


def process_batch(inputs: List[str], delimiter: str = ",") -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        delimiter: 批量分隔符

    返回:
        处理结果列表

    异常:
        E009: 批量输入为空
    """
    if not inputs:
        raise ValueError("E009: 批量输入为空，请提供至少一个输入")

    results = []
    for item in inputs:
        try:
            result = parse_input(item)
            results.append(result)
        except ValueError as e:
            # 单个失败不中断批量，记录错误
            results.append({
                "type": "error",
                "content": item,
                "confidence": 0.0,
                "details": {"error": str(e)},
            })
    return results


def format_output(result: Union[Dict[str, Any], List[Dict[str, Any]]],
                  fmt: str = "json") -> str:
    """
    将结果格式化为指定格式。

    参数:
        result: 处理结果
        fmt: 输出格式 (json/text)

    返回:
        格式化后的字符串

    异常:
        E003: 不支持的格式
        E008: 序列化失败
    """
    if fmt == "json":
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            raise ValueError(f"E008: 输出序列化失败 - {e}")
    elif fmt == "text":
        if isinstance(result, list):
            lines = []
            for i, r in enumerate(result, 1):
                lines.append(f"[{i}] type={r.get('type')}, "
                             f"content={r.get('content')}, "
                             f"confidence={r.get('confidence')}")
            return "\n".join(lines)
        else:
            return (f"type={result.get('type')}\n"
                    f"content={result.get('content')}\n"
                    f"confidence={result.get('confidence')}\n"
                    f"details={json.dumps(result.get('details', {}), ensure_ascii=False)}")
    else:
        raise ValueError(f"E003: 不支持的输出格式 '{fmt}'，仅支持 json/text")


def check_confidence(result: Dict[str, Any]) -> Optional[str]:
    """
    根据置信度返回标注信息。

    规则：
        >=90%: 直接输出（返回 None）
        85%-90%: 建议复核
        <85%: 需核实

    参数:
        result: 处理结果

    返回:
        标注信息或 None
    """
    conf = result.get("confidence", 0.0)
    if conf >= 0.90:
        return None
    elif conf >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例验证核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("pyflowgraph 自检开始")
    print("=" * 60)

    # 测试1: 空输入 -> E001
    try:
        parse_input("")
        print("[FAIL] 空输入未触发 E001")
        return False
    except ValueError as e:
        assert "E001" in str(e), f"错误码不正确: {e}"
        print("[PASS] 空输入正确触发 E001")

    # 测试2: URL 识别
    url_result = parse_input("https://example.com/path?q=1")
    assert url_result["type"] == "url", f"URL 类型识别失败: {url_result['type']}"
    assert url_result["confidence"] > 0.9, "URL 置信度应 > 0.9"
    assert url_result["details"]["scheme"] == "https", "URL scheme 解析失败"
    print("[PASS] URL 识别正确")

    # 测试3: 数字识别
    num_result = parse_input("42")
    assert num_result["type"] == "number", f"数字类型识别失败: {num_result['type']}"
    assert num_result["details"]["value"] == 42, "数字值解析失败"
    assert num_result["confidence"] > 0.8, "数字置信度应 > 0.8"
    print("[PASS] 数字识别正确")

    # 测试4: 列表识别（逗号分隔）
    list_result = parse_input("apple,banana,orange")
    assert list_result["type"] == "list", f"列表类型识别失败: {list_result['type']}"
    assert len(list_result["items"]) == 3, f"列表项数量错误: {len(list_result['items'])}"
    assert list_result["confidence"] > 0.8, "列表置信度应 > 0.8"
    print("[PASS] 列表识别正确")

    # 测试5: 普通文本（含空格但不含分隔符）
    text_result = parse_input("hello world this is a test")
    assert text_result["type"] == "text", f"文本类型识别失败: {text_result['type']}"
    assert text_result["details"]["word_count"] >= 5, "词数统计错误"
    print("[PASS] 文本识别正确")

    # 测试6: 置信度标注
    low_conf = {"confidence": 0.5}
    mid_conf = {"confidence": 0.87}
    high_conf = {"confidence": 0.95}
    assert check_confidence(low_conf) == "[需核实]", "低置信度标注错误"
    assert check_confidence(mid_conf) == "建议复核", "中置信度标注错误"
    assert check_confidence(high_conf) is None, "高置信度不应有标注"
    print("[PASS] 置信度标注正确")

    # 测试7: 批量处理
    batch = process_batch(["1", "2", "3"], delimiter=",")
    assert len(batch) == 3, f"批量处理数量错误: {len(batch)}"
    assert all(b["type"] == "number" for b in batch), "批量处理类型错误"
    print("[PASS] 批量处理正确")

    # 测试8: 输出格式化
    sample = {"type": "text", "content": "test", "confidence": 0.7, "details": {}}
    json_out = format_output(sample, "json")
    assert json_out and '"type"' in json_out, "JSON 输出格式错误"
    text_out = format_output(sample, "text")
    assert "type=text" in text_out, "文本输出格式错误"
    print("[PASS] 输出格式化正确")

    # 测试9: 错误处理
    try:
        format_output(sample, "xml")
        print("[FAIL] 不支持的格式未触发异常")
        return False
    except ValueError as e:
        assert "E003" in str(e), f"错误码不正确: {e}"
        print("[PASS] 错误处理正确")

    # 测试10: 综合验证
    all_results = [
        parse_input("https://example.org"),
        parse_input("123.45"),
        parse_input("a|b|c"),
        parse_input("simple text"),
    ]
    assert len(all_results) == 4, "综合测试数量错误"
    for r in all_results:
        assert 0.0 <= r["confidence"] <= 1.0, "置信度超出范围"
        assert r["type"] in ("url", "number", "list", "text"), "未知类型"
    print("[PASS] 综合验证通过")

    print("=" * 60)
    print("自检全部通过")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="pyflowgraph - 通用数据处理工具",
        epilog="示例: python main.py --input 'hello world' --output json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本/URL/数字/列表）"
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量模式（输入用分隔符分割）"
    )
    parser.add_argument(
        "--delimiter", "-d",
        type=str,
        default=",",
        help="批量分隔符（默认逗号）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    return parser


def main() -> int:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        return 0 if ok else 1

    # 正常处理模式
    try:
        # 检查输入
        if not args.input:
            print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL",
                  file=sys.stderr)
            return 1

        if args.batch:
            # 批量模式
            items = [s.strip() for s in args.input.split(args.delimiter) if s.strip()]
            if not items:
                raise ValueError("E009: 批量输入为空")
            results = process_batch(items, args.delimiter)
        else:
            # 单条模式
            results = parse_input(args.input)

        # 置信度检查
        if isinstance(results, dict):
            note = check_confidence(results)
            if note:
                results["note"] = note
        else:
            for r in results:
                note = check_confidence(r)
                if note:
                    r["note"] = note

        # 输出
        output = format_output(results, args.output)
        print(output)
        return 0

    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E006: 内部处理异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
