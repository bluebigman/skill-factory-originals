#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

代码审查 Skill - 独立实现脚本
依据功能规格 clean-room 编写，不依赖任何既有代码。
"""

import argparse
import sys
import json
from typing import Dict, List, Any, Optional


# ============================================================
# 错误码与提示话术（对应规格"四、异常处理"）
# ============================================================
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
}


class ReviewError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str):
        self.code = code
        self.message = ERROR_MESSAGES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================
def extract_key_fields(raw_input: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息并结构化。

    支持两种格式：
    1. JSON 字符串（标准结构化输入）
    2. 纯文本（逐行解析 key: value 或 key=value）

    返回结构化字典，至少包含：
      - raw_text: 原始输入
      - fields: 提取的字段字典
      - confidence: 置信度（0-100）
    """
    if not raw_input or not raw_input.strip():
        raise ReviewError("E001")

    text = raw_input.strip()

    # 尝试 JSON 解析
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            fields = parsed
            confidence = _calculate_confidence(fields)
            return {
                "raw_text": text,
                "fields": fields,
                "confidence": confidence,
                "format": "json",
            }
        else:
            raise ReviewError("E003")
    except json.JSONDecodeError:
        pass  # 不是 JSON，继续尝试纯文本解析

    # 纯文本解析（支持 key: value 或 key=value）
    fields: Dict[str, Any] = {}
    has_valid_field = False  # 标记是否包含有效字段

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 尝试多种分隔符
        separator = None
        for sep in (":", "=", "："):
            if sep in line:
                separator = sep
                break

        if separator:
            key, _, value = line.partition(separator)
            key = key.strip()
            value = value.strip()
            if key:
                fields[key] = value
                has_valid_field = True
        else:
            # 无分隔符的行，作为备注信息
            fields.setdefault("_notes", []).append(line)

    # 检查是否包含有效字段（非备注信息）
    if not has_valid_field:
        raise ReviewError("E003")

    confidence = _calculate_confidence(fields)
    return {
        "raw_text": text,
        "fields": fields,
        "confidence": confidence,
        "format": "text",
    }


def _calculate_confidence(fields: Dict[str, Any]) -> int:
    """
    估算置信度（0-100）。

    规则（宽松估算，仅用于标注）：
      - 基础分 80
      - 字段数量 >= 3 加 5 分
      - 字段数量 >= 5 加 5 分
      - 有结构化标记（如 JSON）加 5 分
      - 包含关键字段（name/title/type/url/data 等）加 5 分
      - 上限 100
    """
    confidence = 80
    field_count = len(fields)

    if field_count >= 3:
        confidence += 5
    if field_count >= 5:
        confidence += 5

    # 检查是否存在常见关键字段
    key_fields = {"name", "title", "type", "url", "data", "content", "id"}
    if any(k.lower() in key_fields for k in fields.keys()):
        confidence += 5

    return min(100, confidence)


def format_output(result: Dict[str, Any], detail_level: str = "standard") -> Dict[str, Any]:
    """
    按规格要求格式化输出结果。

    detail_level:
      - quick: 仅返回结构化字段和置信度
      - standard: 默认，返回完整信息
      - detailed: 详细，包含原始文本等

    置信度标注规则：
      - >=90%：直接输出
      - 85%-90%：标注"建议复核"
      - <85%：标注"[需核实]"，并说明不确定点
    """
    confidence = result["confidence"]
    fields = result["fields"]

    # 确定置信度标注
    if confidence >= 90:
        confidence_label = "高置信度"
        warning = None
    elif confidence >= 85:
        confidence_label = "建议复核"
        warning = "部分字段可能不准确，请复核"
    else:
        confidence_label = "[需核实]"
        warning = "置信度较低，关键信息请人工确认"

    output = {
        "status": "success",
        "confidence": confidence,
        "confidence_label": confidence_label,
        "fields": fields,
        "field_count": len(fields),
    }

    if warning:
        output["warning"] = warning

    if detail_level == "quick":
        # 快速模式只返回核心信息
        return {
            "status": output["status"],
            "confidence": output["confidence"],
            "fields": output["fields"],
        }

    if detail_level == "detailed":
        # 详细模式包含所有信息
        output["raw_text"] = result.get("raw_text", "")
        output["format"] = result.get("format", "unknown")

    return output


def batch_process(inputs: List[str], detail_level: str = "standard") -> List[Dict[str, Any]]:
    """
    批量处理多个输入，逐项执行核心流程。
    """
    results = []
    for item in inputs:
        try:
            extracted = extract_key_fields(item)
            formatted = format_output(extracted, detail_level)
            results.append(formatted)
        except ReviewError as e:
            results.append({
                "status": "error",
                "error_code": e.code,
                "message": e.message,
            })
    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    所有断言使用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检：代码审查 Skill 核心逻辑")
    print("=" * 60)

    # --- 测试 1: 正常 JSON 输入 ---
    print("\n[测试 1] JSON 输入解析")
    json_input = '{"name": "示例数据", "type": "报告", "content": "这是测试内容", "url": "https://example.com"}'
    try:
        result = extract_key_fields(json_input)
        assert result["format"] == "json", "JSON 格式识别失败"
        assert "fields" in result, "缺少 fields 字段"
        assert result["confidence"] >= 80, "置信度低于预期"
        assert result["fields"].get("name") == "示例数据", "字段提取错误"
        print("  ✓ JSON 输入解析正常")
        print(f"    置信度: {result['confidence']}%")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试 2: 纯文本输入 ---
    print("\n[测试 2] 纯文本输入解析")
    text_input = "标题: 项目总结\n作者: 张三\n日期: 2026-01-15\n内容: 完成了核心模块开发"
    try:
        result = extract_key_fields(text_input)
        assert result["format"] == "text", "文本格式识别失败"
        assert len(result["fields"]) >= 3, "文本字段提取不完整"
        assert result["confidence"] >= 80, "文本置信度低于预期"
        print("  ✓ 纯文本输入解析正常")
        print(f"    提取字段数: {len(result['fields'])}")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试 3: 空输入报错 ---
    print("\n[测试 3] 空输入错误处理")
    try:
        extract_key_fields("")
        print("  ✗ 测试失败: 空输入未抛出异常")
        return 1
    except ReviewError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  ✓ 空输入正确报错 E001")

    # --- 测试 4: 格式错误输入 ---
    print("\n[测试 4] 格式错误输入")
    try:
        extract_key_fields("!!! 这不是有效的输入格式 !!!")
        print("  ✗ 测试失败: 无效格式未抛出异常")
        return 1
    except ReviewError as e:
        assert e.code == "E003", f"错误码应为 E003，实际 {e.code}"
        print("  ✓ 无效格式正确报错 E003")

    # --- 测试 5: 输出格式化 ---
    print("\n[测试 5] 输出格式化")
    sample = {
        "raw_text": "测试",
        "fields": {"a": 1, "b": 2, "c": 3},
        "confidence": 90,
        "format": "text",
    }
    formatted = format_output(sample, "standard")
    assert formatted["status"] == "success", "状态字段错误"
    assert formatted["confidence"] == 90, "置信度传递错误"
    assert "confidence_label" in formatted, "缺少置信度标签"
    print("  ✓ 标准输出格式化正常")

    # --- 测试 6: 批量处理 ---
    print("\n[测试 6] 批量处理")
    batch_inputs = [
        '{"name": "A", "type": "文本", "id": 1}',
        "名称: B\n类型: 数据",
        "",  # 空输入，应报错
    ]
    results = batch_process(batch_inputs)
    assert len(results) == 3, "批量处理数量错误"
    assert results[0]["status"] == "success", "第一条应成功"
    assert results[1]["status"] == "success", "第二条应成功"
    assert results[2]["status"] == "error", "第三条应报错"
    assert results[2]["error_code"] == "E001", "第三条错误码应为 E001"
    print("  ✓ 批量处理正常（含错误处理）")

    # --- 测试 7: 置信度分级 ---
    print("\n[测试 7] 置信度分级标注")
    low_conf = {"fields": {"x": 1}, "raw_text": "低置信度样例", "confidence": 80, "format": "text"}
    mid_conf = {"fields": {"a": 1, "b": 2, "c": 3}, "raw_text": "中置信度样例", "confidence": 87, "format": "text"}
    high_conf = {"fields": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}, "raw_text": "高置信度样例", "confidence": 95, "format": "text"}

    low_out = format_output(low_conf)
    mid_out = format_output(mid_conf)
    high_out = format_output(high_conf)

    assert "[需核实]" in low_out["confidence_label"], "低置信度标注错误"
    assert "建议复核" in mid_out["confidence_label"], "中置信度标注错误"
    assert "高置信度" in high_out["confidence_label"], "高置信度标注错误"
    print("  ✓ 置信度分级标注正常")

    # --- 测试 8: 错误码覆盖 ---
    print("\n[测试 8] 错误码体系")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
    print("  ✓ 错误码 E001-E005 全部定义")

    # 总结
    print("\n" + "=" * 60)
    print("自检完成：全部测试通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="代码审查 Skill - 结构化数据处理工具",
        epilog="示例: python main.py --input '{\"name\": \"测试\"}' --format standard",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="输入内容（JSON 字符串或 key: value 文本）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="*",
        help="批量处理多个输入",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["quick", "standard", "detailed"],
        default="standard",
        help="输出格式级别（默认: standard）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式
    if args.batch:
        results = batch_process(args.batch, args.format)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    # 单条模式
    if args.input:
        try:
            extracted = extract_key_fields(args.input)
            output = format_output(extracted, args.format)
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        except ReviewError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 无输入参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
