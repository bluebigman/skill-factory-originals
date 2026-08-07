#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm-claude-skills 独立实现脚本

本脚本根据功能规格独立编写，不参考任何既有实现。
提供核心的结构化转换、置信度评估、批量处理能力，
并内置 --selftest 离线自检。

作者: 独立实现
版本: 1.0.0
许可证: MIT
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：JSON对象、CSV文本或URL链接",
    "E004": "这超出了本工具的能力范围，建议使用专业工具或咨询专家",
    "E005": "结果无法确定，建议：提供更多上下文信息或人工复核",
    "E006": "内部处理异常，请检查输入数据是否包含非法字符",
    "E007": "输出格式不支持，当前支持：json、text、csv",
    "E008": "批量处理时出现错误，请检查每个条目的格式",
    "E009": "置信度评估失败，输入数据不足以进行可靠分析",
    "E010": "未知错误，请稍后重试或联系维护者",
}


class SkillError(Exception):
    """技能执行异常，携带错误码"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        msg = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        if detail:
            msg = f"{msg} ({detail})"
        super().__init__(msg)


# ============================================================
# 核心功能：结构化转换
# ============================================================

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析用户输入，识别关键信息并结构化。

    支持：
    - JSON 字符串（对象或数组）
    - 简单键值对文本（key: value 每行一个）
    - URL 链接（仅识别，不访问网络）

    参数:
        raw_input: 用户提供的原始输入

    返回:
        结构化字典，包含解析后的数据和元信息

    异常:
        SkillError: E001 输入为空; E003 输入格式错误
    """
    if not raw_input or not raw_input.strip():
        raise SkillError("E001")

    text = raw_input.strip()

    # 尝试 JSON 解析
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            return {
                "type": "json",
                "data": data,
                "fields": _extract_fields(data),
                "confidence": _assess_confidence(data),
            }
        except json.JSONDecodeError:
            raise SkillError("E003", "JSON 格式不正确")

    # 尝试键值对解析
    if ":" in text and "\n" in text:
        try:
            kv_data = {}
            for line in text.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    kv_data[key.strip()] = value.strip()
            if kv_data:
                return {
                    "type": "key-value",
                    "data": kv_data,
                    "fields": list(kv_data.keys()),
                    "confidence": _assess_confidence(kv_data),
                }
        except Exception:
            raise SkillError("E003", "键值对解析失败")

    # URL 识别（仅标记，不访问）
    if text.startswith(("http://", "https://")):
        return {
            "type": "url",
            "data": {"url": text},
            "fields": ["url"],
            "confidence": 0.5,
            "note": "[需核实] URL 内容未获取，仅识别链接本身",
        }

    # 普通文本
    return {
        "type": "text",
        "data": {"content": text},
        "fields": ["content"],
        "confidence": _assess_confidence({"content": text}),
    }


def _extract_fields(data: Any) -> List[str]:
    """从解析后的数据中提取字段名"""
    if isinstance(data, dict):
        return list(data.keys())
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return list(data[0].keys())
    if isinstance(data, list):
        return [f"item_{i}" for i in range(len(data))]
    return ["value"]


def _assess_confidence(data: Any) -> float:
    """
    评估解析结果的置信度（0.0 ~ 1.0）

    规则：
    - 数据为空或 None: 0.0
    - 字典/列表有内容: 0.9 以上
    - 结构复杂（嵌套）: 降低置信度
    """
    if data is None:
        return 0.0

    if isinstance(data, dict):
        if not data:
            return 0.3
        # 有嵌套结构则降低置信度
        has_nested = any(isinstance(v, (dict, list)) for v in data.values())
        base = 0.95 if not has_nested else 0.85
        return base

    if isinstance(data, list):
        if not data:
            return 0.3
        return min(0.95, 0.8 + len(data) * 0.05)

    if isinstance(data, str):
        return 0.9 if data.strip() else 0.2

    return 0.8


def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式输出结果

    参数:
        data: 结构化数据
        output_format: json / text / csv

    返回:
        格式化后的字符串

    异常:
        SkillError: E007 不支持的输出格式
    """
    fmt = output_format.lower().strip()

    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    if fmt == "text":
        lines = []
        for key, value in data.get("data", {}).items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    if fmt == "csv":
        import csv
        import io

        output = io.StringIO()
        field_data = data.get("data", {})

        if isinstance(field_data, list) and field_data:
            # 列表数据，假设是字典列表
            writer = csv.DictWriter(output, fieldnames=field_data[0].keys())
            writer.writeheader()
            writer.writerows(field_data)
        elif isinstance(field_data, dict):
            writer = csv.writer(output)
            writer.writerow(field_data.keys())
            writer.writerow(field_data.values())
        else:
            raise SkillError("E007", "CSV 输出需要字典或字典列表数据")
        return output.getvalue()

    raise SkillError("E007", f"不支持的格式: {output_format}")


def process_batch(items: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """
    批量处理多个输入

    参数:
        items: 输入列表
        output_format: 输出格式

    返回:
        处理结果列表

    异常:
        SkillError: E008 批量处理失败
    """
    results = []
    for idx, item in enumerate(items):
        try:
            parsed = parse_input(item)
            results.append({
                "index": idx,
                "status": "success",
                "result": parsed,
            })
        except SkillError as e:
            results.append({
                "index": idx,
                "status": "error",
                "error_code": e.code,
                "error_message": str(e),
            })

    # 如果全部失败，抛出批量错误
    if results and all(r["status"] == "error" for r in results):
        raise SkillError("E008", "所有条目均处理失败")

    return results


# ============================================================
# 主流程
# ============================================================

def run_pipeline(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    执行标准处理流程

    1. 解析输入
    2. 评估置信度
    3. 生成输出

    参数:
        raw_input: 原始输入
        output_format: 输出格式

    返回:
        处理结果字典
    """
    # Step 1: 解析输入
    parsed = parse_input(raw_input)

    # Step 2: 置信度评估与标注
    confidence = parsed.get("confidence", 0.0)
    if confidence >= 0.9:
        level = "直接输出"
    elif confidence >= 0.85:
        level = "建议复核"
        parsed["warning"] = "建议复核：置信度在85%-90%之间"
    else:
        level = "需核实"
        parsed["warning"] = "[需核实] 置信度低于85%，请人工确认关键信息"

    parsed["confidence_level"] = level

    # Step 3: 格式化输出
    try:
        formatted = format_output(parsed, output_format)
    except SkillError:
        # 回退到 JSON 输出
        formatted = format_output(parsed, "json")

    return {
        "success": True,
        "parsed_data": parsed,
        "output": formatted,
        "confidence": confidence,
        "confidence_level": level,
    }


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑，使用内置硬编码数据。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("=" * 60)
    print("开始离线自检 (--selftest)")
    print("=" * 60)

    failures = 0
    checks = 0

    # --- 测试 1: 错误码存在性 ---
    print("\n[1/6] 错误码定义检查...")
    checks += 1
    expected_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    missing = [code for code in expected_codes if code not in ERROR_MESSAGES]
    if missing:
        print(f"  ✗ 缺少错误码: {missing}")
        failures += 1
    else:
        print("  ✓ 全部 10 个错误码已定义")
    print(f"  (检查项 {checks}/{checks})")

    # --- 测试 2: JSON 解析 ---
    print("\n[2/6] JSON 解析测试...")
    checks += 1
    sample_json = '{"name": "测试项目", "status": "active", "items": [1, 2, 3]}'
    try:
        result = parse_input(sample_json)
        assert result["type"] == "json", "类型应为 json"
        assert "name" in result["data"], "应包含 name 字段"
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        print("  ✓ JSON 解析正常")
        print(f"    字段: {result['fields']}, 置信度: {result['confidence']:.2f}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        failures += 1
    except SkillError as e:
        print(f"  ✗ 解析异常: {e}")
        failures += 1
    print(f"  (检查项 {checks}/{checks})")

    # --- 测试 3: 键值对解析 ---
    print("\n[3/6] 键值对解析测试...")
    checks += 1
    sample_kv = "name: 测试\nage: 25\nrole: developer"
    try:
        result = parse_input(sample_kv)
        assert result["type"] == "key-value", "类型应为 key-value"
        assert result["data"]["name"] == "测试", "name 值应为 测试"
        assert len(result["fields"]) >= 3, "应至少 3 个字段"
        print("  ✓ 键值对解析正常")
        print(f"    字段: {result['fields']}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        failures += 1
    except SkillError as e:
        print(f"  ✗ 解析异常: {e}")
        failures += 1
    print(f"  (检查项 {checks}/{checks})")

    # --- 测试 4: 格式输出 ---
    print("\n[4/6] 格式输出测试...")
    checks += 1
    sample_data = {"type": "json", "data": {"key": "value"}, "fields": ["key"], "confidence": 0.95}
    try:
        json_out = format_output(sample_data, "json")
        assert '"key"' in json_out, "JSON 输出应包含 key"
        text_out = format_output(sample_data, "text")
        assert "key: value" in text_out, "文本输出应包含 key: value"
        print("  ✓ JSON 和文本输出正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        failures += 1
    except SkillError as e:
        print(f"  ✗ 输出异常: {e}")
        failures += 1
    print(f"  (检查项 {checks}/{checks})")

    # --- 测试 5: 错误处理 ---
    print("\n[5/6] 错误处理测试...")
    checks += 1
    try:
        parse_input("")
        print("  ✗ 空输入应该抛出 E001")
        failures += 1
    except SkillError as e:
        if e.code == "E001":
            print("  ✓ 空输入正确抛出 E001")
        else:
            print(f"  ✗ 错误码不正确: {e.code}")
            failures += 1

    try:
        format_output({"data": {}}, "unsupported")
        print("  ✗ 不支持的格式应该抛出 E007")
        failures += 1
    except SkillError as e:
        if e.code == "E007":
            print("  ✓ 不支持的格式正确抛出 E007")
        else:
            print(f"  ✗ 错误码不正确: {e.code}")
            failures += 1
    print(f"  (检查项 {checks}/{checks})")

    # --- 测试 6: 完整流程 ---
    print("\n[6/6] 完整流程测试...")
    checks += 1
    try:
        result = run_pipeline('{"title": "测试文档", "content": "这是一段测试内容"}', "json")
        assert result["success"] is True, "流程应成功"
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        assert "title" in result["output"], "输出应包含 title"
        print("  ✓ 完整流程执行正常")
        print(f"    置信度: {result['confidence']:.2f}, 级别: {result['confidence_level']}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        failures += 1
    except SkillError as e:
        print(f"  ✗ 流程异常: {e}")
        failures += 1
    print(f"  (检查项 {checks}/{checks})")

    # --- 汇总 ---
    print("\n" + "=" * 60)
    print(f"自检完成: {checks - failures}/{checks} 项通过, {failures} 项失败")
    print("=" * 60)

    return 0 if failures == 0 else 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="pm-claude-skills 独立实现 - 结构化数据转换工具",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（JSON、键值对文本或URL）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=["json", "text", "csv"],
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，输入为 JSON 数组字符串"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式
    if args.batch:
        try:
            items = json.loads(args.batch)
            if not isinstance(items, list):
                raise SkillError("E003", "批量输入需要 JSON 数组")
            results = process_batch([str(i) for i in items], args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except SkillError as e:
            print(f"错误 [{e.code}]: {e}", file=sys.stderr)
            return 1
        except json.JSONDecodeError:
            print("错误 [E003]: 批量输入不是有效的 JSON 数组", file=sys.stderr)
            return 1

    # 单条模式
    if args.input:
        try:
            result = run_pipeline(args.input, args.format)
            print(result["output"])
            if result["confidence"] < 0.85:
                print(f"\n警告: {result.get('warning', '')}", file=sys.stderr)
            return 0
        except SkillError as e:
            print(f"错误 [{e.code}]: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 [E010]: 未知异常: {e}", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
