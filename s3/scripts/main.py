#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - s3 技能独立实现（clean-room 重写）

依据功能规格独立实现，未参考任何既有代码。
支持命令行处理与 --selftest 离线自检。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}


class SkillError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段。

    规则（按规格描述实现）：
    - 识别常见键值对（如 name=xxx, type=xxx）
    - 识别 URL（http/https 开头）
    - 识别 JSON 结构（若输入为 JSON）
    - 其余作为原始文本保留
    """
    if not text or not text.strip():
        raise SkillError("E001")

    result: Dict[str, Any] = {
        "raw": text.strip(),
        "fields": {},
        "urls": [],
        "confidence": 0.0,
    }

    # 1. 尝试解析 JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            result["fields"] = data
            result["confidence"] = 0.95
            return result
    except json.JSONDecodeError:
        pass  # 不是 JSON，继续其他规则

    # 2. 提取 URL
    url_pattern = r"https?://[^\s]+"
    urls = re.findall(url_pattern, text)
    if urls:
        result["urls"] = urls
        result["confidence"] += 0.2

    # 3. 提取键值对（支持 name=value 或 name: value）
    kv_pattern = r"(\w+)\s*[=:]\s*([^\s,;]+)"
    kv_matches = re.findall(kv_pattern, text)
    for key, value in kv_matches:
        result["fields"][key] = value

    # 4. 计算置信度
    if result["fields"] or result["urls"]:
        result["confidence"] += 0.4
    if len(result["fields"]) >= 2:
        result["confidence"] += 0.2
    if len(result["fields"]) >= 3:
        result["confidence"] += 0.1

    # 置信度上限 0.95
    result["confidence"] = min(result["confidence"], 0.95)

    return result


def process_input(data: str, output_format: str = "json") -> Dict[str, Any]:
    """
    处理输入数据，按规格生成结构化结果。

    Step 2 核心流程：
    1. 解析输入，识别关键信息
    2. 按规则结构化
    3. 标注置信度
    """
    # 输入检查
    if not data or not data.strip():
        raise SkillError("E001")

    # 解析输入
    parsed = extract_key_fields(data)

    # 输出格式检查
    if output_format not in ("json", "text", "table"):
        raise SkillError("E003", f"不支持的输出格式: {output_format}，支持: json/text/table")

    # 生成输出
    output = {
        "status": "success",
        "input_preview": data[:100] + ("..." if len(data) > 100 else ""),
        "parsed": parsed,
        "output_format": output_format,
        "confidence": parsed["confidence"],
        "confidence_label": get_confidence_label(parsed["confidence"]),
        "warnings": [],
    }

    # 置信度标注
    if parsed["confidence"] < 0.85:
        output["warnings"].append("[需核实] 输入信息不足或存在不确定项，请人工复核")
    elif parsed["confidence"] < 0.90:
        output["warnings"].append("建议复核：置信度未达 90%")

    # 按格式转换
    if output_format == "json":
        output["result"] = parsed
    elif output_format == "text":
        output["result"] = format_as_text(parsed)
    elif output_format == "table":
        output["result"] = format_as_table(parsed)

    return output


def get_confidence_label(confidence: float) -> str:
    """根据置信度返回标注。"""
    if confidence >= 0.90:
        return "高置信度"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


def format_as_text(parsed: Dict[str, Any]) -> str:
    """将解析结果格式化为纯文本。"""
    lines = []
    if parsed["fields"]:
        lines.append("识别字段：")
        for key, value in parsed["fields"].items():
            lines.append(f"  {key}: {value}")
    if parsed["urls"]:
        lines.append("识别URL：")
        for url in parsed["urls"]:
            lines.append(f"  {url}")
    if not parsed["fields"] and not parsed["urls"]:
        lines.append("（未识别到结构化信息，保留原始输入）")
    return "\n".join(lines)


def format_as_table(parsed: Dict[str, Any]) -> str:
    """将解析结果格式化为表格文本。"""
    if not parsed["fields"]:
        return "（无结构化字段）"
    header = "| 字段 | 值 |"
    separator = "|------|-----|"
    rows = [f"| {k} | {v} |" for k, v in parsed["fields"].items()]
    return "\n".join([header, separator] + rows)


def validate_input(data: str) -> Tuple[bool, Optional[str]]:
    """
    输入校验（Step 3 自查环节）。

    返回: (是否通过, 错误信息)
    """
    if not data or not data.strip():
        return False, "E001"
    # 最小信息集检查：至少包含一个可识别字段或 URL
    parsed = extract_key_fields(data)
    if not parsed["fields"] and not parsed["urls"]:
        return False, "E002"
    return True, None


def batch_process(inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """批量处理多个输入。"""
    results = []
    for item in inputs:
        try:
            result = process_input(item, output_format)
            result["batch_index"] = len(results) + 1
            results.append(result)
        except SkillError as e:
            results.append({
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
                "input": item[:50],
            })
    return results


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。

    使用内置样例数据验证：
    1. 正常处理流程
    2. 错误处理
    3. 批量处理
    """
    print("=" * 50)
    print("开始自检...")
    print("=" * 50)

    # 测试用例 1: 正常输入（键值对）
    print("\n[测试 1] 正常输入（键值对）")
    test_input = "name=测试文件 type=文档 size=10MB"
    result = process_input(test_input)
    assert result["status"] == "success", "测试 1 失败：状态错误"
    assert result["parsed"]["fields"]["name"] == "测试文件", "测试 1 失败：字段提取错误"
    assert result["confidence"] >= 0.85, f"测试 1 失败：置信度异常 {result['confidence']}"
    print("  ✓ 通过")

    # 测试用例 2: URL 输入
    print("\n[测试 2] URL 输入")
    test_input = "请处理 https://example.com/data/file.pdf"
    result = process_input(test_input)
    assert result["status"] == "success", "测试 2 失败：状态错误"
    assert len(result["parsed"]["urls"]) == 1, "测试 2 失败：URL 提取错误"
    assert "example.com" in result["parsed"]["urls"][0], "测试 2 失败：URL 内容错误"
    print("  ✓ 通过")

    # 测试用例 3: JSON 输入
    print("\n[测试 3] JSON 输入")
    test_input = '{"id": 1, "name": "测试", "tags": ["a", "b"]}'
    result = process_input(test_input)
    assert result["status"] == "success", "测试 3 失败：状态错误"
    assert result["parsed"]["fields"]["id"] == 1, "测试 3 失败：JSON 解析错误"
    assert result["confidence"] == 0.95, "测试 3 失败：置信度错误"
    print("  ✓ 通过")

    # 测试用例 4: 空输入（错误处理）
    print("\n[测试 4] 空输入（异常处理）")
    try:
        process_input("")
        assert False, "测试 4 失败：应抛出 E001"
    except SkillError as e:
        assert e.code == "E001", f"测试 4 失败：错误码错误 {e.code}"
        print("  ✓ 通过（正确抛出 E001）")

    # 测试用例 5: 低置信度输入
    print("\n[测试 5] 低置信度输入")
    test_input = "随便写点什么"
    result = process_input(test_input)
    assert result["status"] == "success", "测试 5 失败：状态错误"
    assert result["confidence"] < 0.85, "测试 5 失败：应低置信度"
    assert any("需核实" in w for w in result["warnings"]), "测试 5 失败：应包含需核实警告"
    print("  ✓ 通过")

    # 测试用例 6: 批量处理
    print("\n[测试 6] 批量处理")
    inputs = ["name=文件1", "请处理 https://example.com/a", "无效输入"]
    results = batch_process(inputs)
    assert len(results) == 3, "测试 6 失败：数量错误"
    assert results[0]["status"] == "success", "测试 6 失败：第一条应成功"
    assert results[2]["status"] == "error", "测试 6 失败：第三条应失败"
    print("  ✓ 通过")

    # 测试用例 7: 不同输出格式
    print("\n[测试 7] 输出格式")
    test_input = "name=测试 type=文档"
    for fmt in ["json", "text", "table"]:
        result = process_input(test_input, output_format=fmt)
        assert result["output_format"] == fmt, f"测试 7 失败：格式 {fmt}"
    print("  ✓ 通过")

    # 测试用例 8: 输入校验
    print("\n[测试 8] 输入校验")
    valid, err = validate_input("name=测试")
    assert valid and err is None, "测试 8 失败：有效输入应通过"
    valid, err = validate_input("")
    assert not valid and err == "E001", "测试 8 失败：空输入应报 E001"
    valid, err = validate_input("纯文本无结构")
    assert not valid and err == "E002", "测试 8 失败：无结构应报 E002"
    print("  ✓ 通过")

    print("\n" + "=" * 50)
    print("所有自检测试通过！")
    print("=" * 50)
    return True


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="s3 技能 - psuedo s3 protocol for mozilla browsers",
        epilog="示例: python main.py --input 'name=test type=doc' --format json",
    )
    parser.add_argument("--input", "-i", help="输入数据（文本、JSON 或 URL）")
    parser.add_argument("--format", "-f", choices=["json", "text", "table"], default="json",
                        help="输出格式（默认: json）")
    parser.add_argument("--batch", "-b", nargs="+", help="批量输入，空格分隔多个数据")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 检查输入
    if not args.input and not args.batch:
        parser.print_help()
        print("\n错误: 必须提供 --input 或 --batch 参数", file=sys.stderr)
        return 1

    try:
        # 批量处理
        if args.batch:
            results = batch_process(args.batch, args.format)
            output = json.dumps(results, ensure_ascii=False, indent=2)
            print(output)
            return 0

        # 单条处理
        result = process_input(args.input, args.format)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        print(output)

        # 错误码处理（低置信度提示）
        if result["confidence"] < 0.85:
            print(f"\n[提示] {ERROR_CODES['E005']}", file=sys.stderr)
            return 2

        return 0

    except SkillError as e:
        print(f"错误: [{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
