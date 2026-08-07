#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

一个独立的 schemr 工具实现。
根据功能规格，将用户提供的数据/文件/URL 转换为结构化结果，
并包含置信度标注、错误码处理、批量处理等能力。
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或联系管理员",
    "E007": "文件读取失败，请检查文件路径和权限",
    "E008": "URL 格式无效，请提供合法的 http/https 链接",
    "E009": "批量处理时出现错误，请检查每个输入项",
    "E010": "未识别的命令行参数，请使用 --help 查看帮助",
}


class SchemrError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def error_message(code: str, detail: str = "") -> str:
    """根据错误码生成标准化错误消息。"""
    base = ERROR_CODES.get(code, "未知错误")
    if detail:
        return f"[{code}] {base} {detail}"
    return f"[{code}] {base}"


def parse_input(raw: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息。

    支持：
    - JSON 字符串（自动识别）
    - 键值对格式（key: value 或 key=value）
    - 普通文本（提取关键词）

    返回结构化字典，包含原始内容、解析结果、置信度。
    """
    if not raw or not raw.strip():
        raise SchemrError("E001", "")

    raw = raw.strip()
    result: Dict[str, Any] = {}
    confidence = 0.0

    # 尝试解析 JSON
    if raw.startswith("{") and raw.endswith("}"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                result = data
                confidence = 0.95  # JSON 结构明确，置信度高
            else:
                raise SchemrError("E003", "JSON 顶层必须是对象")
        except json.JSONDecodeError:
            raise SchemrError("E003", "JSON 格式无效，请检查括号和引号")

    # 尝试解析键值对
    elif re.search(r"[:=]", raw):
        pairs = re.split(r"[,;]", raw)
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue
            # 支持 key: value 或 key=value
            match = re.match(r"^([^:=]+)[:=](.+)$", pair)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                result[key] = value
                confidence = 0.85  # 键值对格式明确，但可能有歧义
            else:
                confidence = 0.7  # 部分键值对无法解析

    # 普通文本：提取关键词
    else:
        # 提取可能的字段名（中文或英文单词）
        fields = re.findall(r"[\u4e00-\u9fa5]+|[a-zA-Z_][a-zA-Z0-9_]*", raw)
        if fields:
            result["content"] = raw
            result["keywords"] = fields
            confidence = 0.6  # 普通文本解析，置信度较低

    return {"raw": raw, "parsed": result, "confidence": confidence}


def validate_required_fields(data: Dict[str, Any], required: List[str]) -> List[str]:
    """检查必需字段是否齐全，返回缺失字段列表。"""
    missing = []
    parsed = data.get("parsed", {})
    for field in required:
        if field not in parsed or parsed[field] is None or parsed[field] == "":
            missing.append(field)
    return missing


def format_output(data: Dict[str, Any], format_type: str = "json") -> str:
    """
    按指定格式生成输出。

    支持格式：json, text, table
    """
    parsed = data.get("parsed", {})
    confidence = data.get("confidence", 0.0)

    # 置信度标注
    if confidence >= 0.9:
        level = "直接输出"
    elif confidence >= 0.85:
        level = "建议复核"
    else:
        level = "[需核实]"

    if format_type == "json":
        output = {
            "result": parsed,
            "confidence": confidence,
            "level": level,
            "source": data.get("raw", ""),
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    elif format_type == "text":
        lines = [f"置信度: {confidence:.0%} ({level})"]
        for key, value in parsed.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    elif format_type == "table":
        lines = ["| 字段 | 值 |", "|------|-----|"]
        for key, value in parsed.items():
            lines.append(f"| {key} | {value} |")
        lines.append(f"| 置信度 | {confidence:.0%} ({level}) |")
        return "\n".join(lines)

    else:
        raise SchemrError("E003", f"不支持的输出格式: {format_type}")


def process_single(input_text: str, required_fields: List[str], output_format: str) -> Dict[str, Any]:
    """处理单个输入项，返回处理结果。"""
    # Step 1: 解析输入
    data = parse_input(input_text)

    # Step 2: 检查必需字段
    missing = validate_required_fields(data, required_fields)
    if missing:
        raise SchemrError("E002", f"缺少字段: {', '.join(missing)}")

    # Step 3: 生成输出
    output = format_output(data, output_format)
    return {"status": "success", "output": output, "confidence": data["confidence"]}


def process_batch(inputs: List[str], required_fields: List[str], output_format: str) -> List[Dict[str, Any]]:
    """批量处理多个输入项。"""
    results = []
    for i, item in enumerate(inputs):
        try:
            result = process_single(item, required_fields, output_format)
            result["index"] = i
            results.append(result)
        except SchemrError as e:
            results.append({
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
                "index": i,
            })
    return results


def read_file(file_path: str) -> str:
    """读取文件内容。"""
    if not os.path.exists(file_path):
        raise SchemrError("E007", f"文件不存在: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise SchemrError("E007", f"读取失败: {str(e)}")


def is_valid_url(url: str) -> bool:
    """检查 URL 是否合法。"""
    return bool(re.match(r"^https?://", url))


def handle_url(url: str) -> Dict[str, Any]:
    """
    处理 URL 输入。
    注意：根据规格，本工具不访问网络，只做格式校验和占位处理。
    """
    if not is_valid_url(url):
        raise SchemrError("E008", f"无效 URL: {url}")

    # 根据规格，不访问网络，返回结构化占位结果
    return {
        "parsed": {
            "url": url,
            "note": "URL 已记录，但本工具不访问网络，请手动提供内容",
        },
        "confidence": 0.5,  # 低置信度，因为未实际获取内容
    }


def selftest() -> bool:
    """内置样例数据自检核心逻辑，不依赖外部文件/网络。"""
    test_cases = [
        # 正常 JSON 输入
        {
            "input": '{"name": "测试", "age": 25}',
            "required": ["name"],
            "format": "json",
            "expect_success": True,
        },
        # 键值对输入
        {
            "input": "name=张三, age=30",
            "required": ["name"],
            "format": "text",
            "expect_success": True,
        },
        # 空输入（应报 E001）
        {
            "input": "",
            "required": [],
            "format": "json",
            "expect_success": False,
            "expect_error": "E001",
        },
        # 缺少必需字段（应报 E002）
        {
            "input": '{"name": "测试"}',
            "required": ["name", "age"],
            "format": "json",
            "expect_success": False,
            "expect_error": "E002",
        },
        # 无效 JSON（应报 E003）
        {
            "input": "{invalid json}",
            "required": [],
            "format": "json",
            "expect_success": False,
            "expect_error": "E003",
        },
        # 批量处理
        {
            "input": ['{"a": 1}', '{"a": 2}', "bad input"],
            "required": ["a"],
            "format": "json",
            "batch": True,
            "expect_success": True,
        },
    ]

    passed = 0
    for i, case in enumerate(test_cases):
        try:
            if case.get("batch"):
                results = process_batch(case["input"], case.get("required", []), case["format"])
                # 批量处理中，即使有错误项也整体算成功（有错误项会被标记）
                success_count = sum(1 for r in results if r["status"] == "success")
                if success_count > 0:
                    passed += 1
                else:
                    print(f"自检用例 {i+1} 失败: 批量处理无成功项")
            else:
                result = process_single(case["input"], case.get("required", []), case["format"])
                if case["expect_success"]:
                    passed += 1
                else:
                    print(f"自检用例 {i+1} 失败: 预期失败但成功了")
        except SchemrError as e:
            if not case["expect_success"] and e.code == case.get("expect_error"):
                passed += 1
            else:
                print(f"自检用例 {i+1} 失败: 错误码 {e.code}，预期 {case.get('expect_error', '成功')}")

    # 测试 URL 处理
    try:
        url_result = handle_url("https://example.com")
        if url_result["confidence"] < 0.6:
            passed += 1
        else:
            print("自检用例 URL 失败: 置信度应低于 0.6")
    except SchemrError as e:
        print(f"自检用例 URL 失败: {e.code}")

    total = len(test_cases) + 1
    print(f"自检完成: {passed}/{total} 通过")
    return passed == total


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="schemr - 将数据转换为结构化结果的 DSL 工具",
        epilog="示例: python main.py --input '{\"name\": \"测试\"}' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容（数据/文件路径/URL）")
    parser.add_argument("--file", "-f", help="从文件读取输入")
    parser.add_argument("--url", "-u", help="输入 URL（仅校验，不访问网络）")
    parser.add_argument("--batch", "-b", nargs="+", help="批量输入多个内容")
    parser.add_argument("--format", "-t", choices=["json", "text", "table"], default="json", help="输出格式")
    parser.add_argument("--required", "-r", nargs="+", default=[], help="必需字段列表")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--output", "-o", help="输出到文件")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        return 0 if success else 1

    try:
        # 确定输入来源
        if args.batch:
            # 批量处理
            results = process_batch(args.batch, args.required, args.format)
            output = json.dumps(results, ensure_ascii=False, indent=2)
        elif args.file:
            # 从文件读取
            content = read_file(args.file)
            result = process_single(content, args.required, args.format)
            output = result["output"]
        elif args.url:
            # URL 处理
            data = handle_url(args.url)
            output = format_output(data, args.format)
        elif args.input:
            # 直接输入
            result = process_single(args.input, args.required, args.format)
            output = result["output"]
        else:
            # 无输入，交互模式
            print("请输入内容（支持数据/文件路径/URL），输入 'quit' 退出：")
            lines = []
            while True:
                line = input("> ")
                if line.strip().lower() == "quit":
                    break
                lines.append(line)
            if not lines:
                raise SchemrError("E001", "")
            content = "\n".join(lines)
            result = process_single(content, args.required, args.format)
            output = result["output"]

        # 输出结果
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"结果已写入: {args.output}")
        else:
            print(output)

        return 0

    except SchemrError as e:
        print(error_message(e.code, e.message), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 1
    except Exception as e:
        print(error_message("E006", str(e)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
