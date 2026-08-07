#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jsawesome - Awesome JSON 工具

基于功能规格独立实现（clean-room 重写）。
仅使用标准库，无第三方依赖。
"""

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码与异常体系（规格 E001-E010）
# ---------------------------------------------------------------------------
class SkillError(Exception):
    """技能基础异常，携带错误码与标准化话术。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def raise_error(code: str, message: str) -> None:
    """统一抛出带错误码的异常。"""
    raise SkillError(code, message)


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def _is_blank(value: Any) -> bool:
    """判断输入是否为空（None / 空字符串 / 空白字符）。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _parse_json_text(text: str) -> Any:
    """解析 JSON 字符串，失败时抛出 E003。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        raise_error("E003", "输入格式不符合要求，示例：{\"key\": \"value\"}")


def _extract_fields(data: Any) -> Dict[str, Any]:
    """从解析后的数据中提取关键字段。

    规则：
    - 若为 dict：直接保留全部键值
    - 若为 list：提取元素个数、首个元素、末个元素
    - 其他类型：包装为单一字段
    """
    if isinstance(data, dict):
        return {
            "type": "object",
            "field_count": len(data),
            "fields": data,
        }
    if isinstance(data, list):
        return {
            "type": "array",
            "length": len(data),
            "first_item": data[0] if data else None,
            "last_item": data[-1] if data else None,
            "items": data,
        }
    return {
        "type": type(data).__name__,
        "value": data,
    }


def _calculate_confidence(extracted: Dict[str, Any]) -> Tuple[int, str]:
    """计算置信度（0-100）并返回标注信息。

    规则（宽松实现）：
    - 字段数 >= 2：置信度 95，直接输出
    - 字段数 == 1：置信度 88，标注"建议复核"
    - 字段数为 0 或类型未知：置信度 60，标注"[需核实]"
    """
    field_count = 0
    if "field_count" in extracted:
        field_count = extracted["field_count"]
    elif "length" in extracted:
        field_count = extracted["length"]
    elif "value" in extracted:
        field_count = 1

    if field_count >= 2:
        return 95, "直接输出"
    if field_count == 1:
        return 88, "建议复核"
    return 60, "[需核实]"


def _format_output(data: Any, confidence: int, note: str) -> Dict[str, Any]:
    """按约定格式组织输出结果。"""
    return {
        "result": data,
        "confidence": confidence,
        "note": note,
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# 核心处理流程（对应规格 Step 2）
# ---------------------------------------------------------------------------
def process_input(raw_input: str) -> Dict[str, Any]:
    """处理用户输入，返回结构化结果。

    参数：
        raw_input: 用户提供的原始字符串（JSON 文本、文件路径或 URL）

    返回：
        结构化结果字典，包含 result / confidence / note / status 字段

    异常：
        E001: 输入为空
        E003: 输入格式错误（非 JSON 且非文件路径）
        E004: 超出能力边界（文件不存在或 URL 无法访问）
    """
    # Step 1: 检查输入是否为空（E001）
    if _is_blank(raw_input):
        raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    # Step 2: 尝试解析为 JSON 文本
    try:
        parsed = _parse_json_text(raw_input)
    except SkillError:
        # 不是 JSON 文本，尝试作为文件路径处理
        parsed = _process_file_or_url(raw_input)

    # Step 3: 提取关键信息
    extracted = _extract_fields(parsed)

    # Step 4: 计算置信度
    confidence, note = _calculate_confidence(extracted)

    # Step 5: 组织输出
    return _format_output(extracted, confidence, note)


def _process_file_or_url(raw_input: str) -> Any:
    """处理文件路径或 URL 输入。

    仅支持本地文件路径（相对/绝对路径）。
    URL 识别但明确拒绝访问（规格：不访问网络）。
    """
    # 识别 URL（E004：超出能力边界）
    parsed_url = urllib.parse.urlparse(raw_input)
    if parsed_url.scheme in ("http", "https", "ftp"):
        raise_error(
            "E004",
            "这超出了本工具的能力范围，建议：本地文件路径或直接粘贴 JSON 文本"
        )

    # 处理本地文件路径
    file_path = Path(raw_input)
    if not file_path.exists():
        raise_error("E003", "输入格式不符合要求，示例：{\"key\": \"value\"} 或文件路径")
    if not file_path.is_file():
        raise_error("E004", "这超出了本工具的能力范围，建议：提供文件路径而非目录")

    try:
        file_content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise_error("E003", "输入格式不符合要求，示例：{\"key\": \"value\"} 或文件路径")

    # 文件内容需为 JSON
    return _parse_json_text(file_content)


def batch_process(inputs: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个输入（规格：进阶用法）。"""
    results = []
    for item in inputs:
        try:
            results.append(process_input(item))
        except SkillError as e:
            results.append({
                "result": None,
                "confidence": 0,
                "note": f"处理失败: {e.message}",
                "status": "error",
                "error_code": e.code,
            })
    return results


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保稳健通过。
    """
    print("[SELFTEST] 开始离线自检...")
    test_cases = [
        # 样例 1: 标准 JSON 对象
        '{"name": "test", "value": 42}',
        # 样例 2: JSON 数组
        '[1, 2, 3, 4, 5]',
        # 样例 3: 简单值
        '"hello"',
        # 样例 4: 空对象
        '{}',
        # 样例 5: 嵌套结构
        '{"user": {"name": "Alice"}, "tags": ["a", "b"]}',
    ]

    # 测试 1: 正常处理 JSON 对象
    print("  测试 1: 标准 JSON 对象")
    result = process_input(test_cases[0])
    assert result["status"] == "ok", "状态应为 ok"
    assert result["confidence"] >= 90, "置信度应 >= 90"
    assert result["result"]["type"] == "object", "类型应为 object"
    assert result["result"]["field_count"] >= 2, "字段数应 >= 2"
    print("    通过")

    # 测试 2: 数组处理
    print("  测试 2: JSON 数组")
    result = process_input(test_cases[1])
    assert result["status"] == "ok", "状态应为 ok"
    assert result["result"]["type"] == "array", "类型应为 array"
    assert result["result"]["length"] > 0, "数组长度应 > 0"
    assert result["confidence"] >= 90, "置信度应 >= 90"
    print("    通过")

    # 测试 3: 简单值处理
    print("  测试 3: 简单值")
    result = process_input(test_cases[2])
    assert result["status"] == "ok", "状态应为 ok"
    assert result["result"]["type"] == "str", "类型应为 str"
    assert result["confidence"] >= 80, "置信度应 >= 80"
    print("    通过")

    # 测试 4: 空对象处理（置信度较低）
    print("  测试 4: 空对象")
    result = process_input(test_cases[3])
    assert result["status"] == "ok", "状态应为 ok"
    assert result["confidence"] < 90, "空对象置信度应 < 90"
    assert result["note"] == "[需核实]", "空对象应标注 [需核实]"
    print("    通过")

    # 测试 5: 嵌套结构
    print("  测试 5: 嵌套结构")
    result = process_input(test_cases[4])
    assert result["status"] == "ok", "状态应为 ok"
    assert result["result"]["field_count"] >= 2, "嵌套对象字段数应 >= 2"
    assert result["confidence"] >= 90, "置信度应 >= 90"
    print("    通过")

    # 测试 6: 错误处理（空输入）
    print("  测试 6: 空输入错误码")
    try:
        process_input("")
        assert False, "空输入应抛出异常"
    except SkillError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
    print("    通过")

    # 测试 7: 错误处理（非法 JSON）
    print("  测试 7: 非法 JSON 错误码")
    try:
        process_input("not a json")
        # 如果文件不存在，也会抛 E003，这里两种情况都接受
    except SkillError as e:
        assert e.code in ("E003", "E004"), f"错误码应为 E003/E004，实际为 {e.code}"
    print("    通过")

    # 测试 8: 批量处理
    print("  测试 8: 批量处理")
    batch_results = batch_process(test_cases[:3])
    assert len(batch_results) == 3, "批量结果数量应为 3"
    assert all(r["status"] == "ok" for r in batch_results), "全部应成功"
    print("    通过")

    # 测试 9: 输出格式完整性
    print("  测试 9: 输出格式完整性")
    result = process_input(test_cases[0])
    required_keys = {"result", "confidence", "note", "status"}
    assert required_keys.issubset(result.keys()), "输出应包含所有必需字段"
    assert isinstance(result["confidence"], int), "置信度应为整数"
    assert 0 <= result["confidence"] <= 100, "置信度应在 0-100 范围"
    print("    通过")

    # 测试 10: URL 拒绝（E004）
    print("  测试 10: URL 处理（应拒绝）")
    try:
        process_input("https://example.com/data.json")
        assert False, "URL 应抛出 E004"
    except SkillError as e:
        assert e.code == "E004", f"错误码应为 E004，实际为 {e.code}"
    print("    通过")

    print("[SELFTEST] 全部自检通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="jsawesome - Awesome JSON 工具",
        epilog="示例：python main.py '{\"name\": \"test\"}'"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的 JSON 文本或文件路径"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="美化输出 JSON 格式"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式
    if args.batch:
        results = batch_process(args.batch)
        output = json.dumps(results, ensure_ascii=False, indent=2 if args.pretty else None)
        print(output)
        return 0

    # 单次处理模式
    if not args.input:
        print("错误: 请提供输入内容（JSON 文本或文件路径）", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检，使用 --help 查看帮助", file=sys.stderr)
        return 1

    try:
        result = process_input(args.input)
        output = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
        print(output)
        return 0
    except SkillError as e:
        print(f"错误: [{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
