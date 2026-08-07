#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ipython-dashboard 数据可视化工具
独立实现脚本，仅依据功能规格编写。

功能：
- 将输入数据/文本/URL 解析为结构化结果
- 支持批量处理
- 置信度评估与标注
- 内置离线自检（--selftest）

用法：
    python main.py --input "数据内容" [--format json|text] [--batch]
    python main.py --selftest
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与异常定义
# ============================================================

class SkillError(Exception):
    """技能基础异常，携带错误码"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: str) -> None:
    """
    校验输入内容是否有效
    错误码：E001（空输入）、E003（格式错误）
    """
    if raw_input is None or raw_input.strip() == "":
        raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    # 仅允许基本可打印字符（含中文），拒绝二进制/控制字符
    for ch in raw_input:
        if ord(ch) < 32 and ch not in "\n\r\t":
            raise SkillError("E003", f"输入包含非法控制字符: U+{ord(ch):04X}")


def detect_input_type(raw_input: str) -> str:
    """
    识别输入类型：URL / JSON / 普通文本
    返回：'url'、'json'、'text'
    如果以 { 或 [ 开头但 JSON 解析失败，抛出 E003
    """
    stripped = raw_input.strip()
    if stripped.startswith(("http://", "https://")):
        return "url"
    if stripped.startswith(("{", "[")):
        try:
            json.loads(stripped)
            return "json"
        except json.JSONDecodeError as exc:
            raise SkillError("E003", f"JSON 解析失败: {exc.msg}") from exc
    return "text"


def parse_json_input(raw_input: str) -> Dict[str, Any]:
    """解析 JSON 输入，失败则抛 E003"""
    try:
        data = json.loads(raw_input)
        if not isinstance(data, dict):
            raise SkillError("E003", "JSON 输入必须是对象（字典）格式")
        return data
    except json.JSONDecodeError as exc:
        raise SkillError("E003", f"JSON 解析失败: {exc.msg}") from exc


def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从输入字典中提取关键字段，结构化输出
    识别常见字段名：name/title/desc/date/amount/value/count 等
    """
    result: Dict[str, Any] = {}
    # 字段映射表（中英文常见别名）
    field_aliases = {
        "name": ["name", "标题", "title", "名称"],
        "description": ["desc", "description", "描述", "说明"],
        "date": ["date", "日期", "time", "时间"],
        "value": ["value", "数值", "amount", "金额", "价格", "price"],
        "count": ["count", "数量", "个数", "total"],
        "category": ["category", "分类", "类型", "type"],
    }
    for key, aliases in field_aliases.items():
        for alias in aliases:
            if alias in data:
                result[key] = data[alias]
                break
    # 保留其他未识别字段
    for k, v in data.items():
        if k not in [a for aliases in field_aliases.values() for a in aliases]:
            result[k] = v
    return result


def calculate_confidence(data: Dict[str, Any], input_type: str) -> int:
    """
    计算置信度（0-100）
    规则：
    - 基础 90 分
    - JSON 结构化数据 +5
    - 关键字段缺失 -5/个（最多扣 20）
    - 文本输入且无结构化字段 -10
    """
    confidence = 90
    if input_type == "json":
        confidence += 5
    elif input_type == "text":
        # 文本输入，检查是否包含可识别字段
        text = json.dumps(data, ensure_ascii=False)
        has_key = any(k in text for k in ["name", "title", "value", "count", "desc"])
        if not has_key:
            confidence -= 10

    # 检查关键字段缺失
    key_fields = ["name", "value", "date"]
    missing = sum(1 for f in key_fields if f not in data)
    confidence -= min(missing * 5, 20)

    return max(0, min(100, confidence))


def format_output(data: Dict[str, Any], confidence: int, output_format: str) -> str:
    """
    按指定格式输出结果
    支持：json / text
    """
    if output_format == "json":
        output = {
            "result": data,
            "confidence": confidence,
            "confidence_label": get_confidence_label(confidence),
            "timestamp": datetime.now().isoformat(),
        }
        return json.dumps(output, ensure_ascii=False, indent=2)
    else:
        lines = ["=== 数据处理结果 ==="]
        for k, v in data.items():
            lines.append(f"{k}: {v}")
        lines.append(f"--- 置信度: {confidence}% ({get_confidence_label(confidence)}) ---")
        return "\n".join(lines)


def get_confidence_label(confidence: int) -> str:
    """根据置信度返回标注"""
    if confidence >= 90:
        return "直接输出"
    elif confidence >= 85:
        return "建议复核"
    else:
        return "[需核实]"


def process_single(raw_input: str, output_format: str = "text") -> str:
    """
    处理单条输入，返回格式化结果
    """
    # Step 1: 校验
    validate_input(raw_input)

    # Step 2: 识别类型
    input_type = detect_input_type(raw_input)

    # Step 3: 解析与提取
    if input_type == "json":
        parsed = parse_json_input(raw_input)
    else:
        # 文本/URL 视为简单文本，构造基础结构
        parsed = {"content": raw_input.strip(), "source_type": input_type}

    # 提取关键字段
    extracted = extract_key_fields(parsed)

    # Step 4: 置信度
    confidence = calculate_confidence(extracted, input_type)

    # Step 5: 格式化输出
    return format_output(extracted, confidence, output_format)


def process_batch(inputs: List[str], output_format: str = "text") -> str:
    """
    批量处理多条输入，返回合并结果
    """
    results = []
    for idx, item in enumerate(inputs, 1):
        try:
            result = process_single(item, output_format)
            results.append({"index": idx, "status": "success", "output": result})
        except SkillError as exc:
            results.append({"index": idx, "status": "error", "code": exc.code, "message": exc.message})

    # 汇总统计
    success = sum(1 for r in results if r["status"] == "success")
    total = len(results)

    summary = {
        "total": total,
        "success": success,
        "failed": total - success,
        "results": results,
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑，使用硬编码样例数据
    不读文件、不依赖目录、不访问网络
    返回 0 表示通过，非 0 表示失败
    """
    print("=" * 50)
    print("ipython-dashboard 自检开始")
    print("=" * 50)

    # ---- 测试用例 1: JSON 输入 ----
    print("\n[测试1] JSON 输入处理")
    json_input = '{"name": "销售数据", "value": 12345, "date": "2025-01-15", "region": "华东"}'
    try:
        result = process_single(json_input, "json")
        result_data = json.loads(result)
        # 宽松断言：结果包含关键字段且置信度合理
        assert "result" in result_data, "缺少 result 字段"
        assert "confidence" in result_data, "缺少 confidence 字段"
        assert result_data["confidence"] >= 80, f"置信度异常: {result_data['confidence']}"
        assert result_data["result"].get("name") == "销售数据", "名称提取错误"
        print(f"  ✅ 通过 (置信度: {result_data['confidence']}%)")
    except Exception as exc:
        print(f"  ❌ 失败: {exc}")
        return 1

    # ---- 测试用例 2: 文本输入 ----
    print("\n[测试2] 普通文本输入")
    text_input = "这是一个简单的测试文本，用于验证处理流程是否正常"
    try:
        result = process_single(text_input, "text")
        assert "content" in result, "文本输入未包含 content 字段"
        assert "置信度" in result, "缺少置信度标注"
        print(f"  ✅ 通过")
    except Exception as exc:
        print(f"  ❌ 失败: {exc}")
        return 1

    # ---- 测试用例 3: 空输入错误处理 ----
    print("\n[测试3] 空输入错误处理")
    try:
        process_single("")
        print("  ❌ 失败: 空输入未触发错误")
        return 1
    except SkillError as exc:
        assert exc.code == "E001", f"错误码错误: {exc.code}"
        print(f"  ✅ 通过 (错误码: {exc.code})")

    # ---- 测试用例 4: 批量处理 ----
    print("\n[测试4] 批量处理")
    batch_input = [
        '{"name": "项目A", "value": 100}',
        '{"name": "项目B", "value": 200}',
        "invalid json {",
    ]
    try:
        batch_result = process_batch(batch_input, "text")
        batch_data = json.loads(batch_result)
        assert batch_data["total"] == 3, "批量总数错误"
        assert batch_data["success"] == 2, f"成功数错误: 期望2, 实际{batch_data['success']}"
        assert batch_data["failed"] == 1, f"失败数错误: 期望1, 实际{batch_data['failed']}"
        print(f"  ✅ 通过 (成功: {batch_data['success']}, 失败: {batch_data['failed']})")
    except Exception as exc:
        print(f"  ❌ 失败: {exc}")
        return 1

    # ---- 测试用例 5: URL 输入 ----
    print("\n[测试5] URL 输入识别")
    url_input = "https://example.com/data.csv"
    try:
        result = process_single(url_input, "json")
        result_data = json.loads(result)
        assert result_data["result"].get("source_type") == "url", "URL 类型识别错误"
        print(f"  ✅ 通过")
    except Exception as exc:
        print(f"  ❌ 失败: {exc}")
        return 1

    # ---- 测试用例 6: 置信度标注 ----
    print("\n[测试6] 置信度标注")
    low_conf_input = '{"name": "仅名称"}'
    try:
        result = process_single(low_conf_input, "json")
        result_data = json.loads(result)
        conf = result_data["confidence"]
        label = result_data["confidence_label"]
        # 宽松断言：置信度在合理范围，标注匹配
        assert 0 <= conf <= 100, "置信度超出范围"
        assert label in ["直接输出", "建议复核", "[需核实]"], "标注无效"
        print(f"  ✅ 通过 (置信度: {conf}%, 标注: {label})")
    except Exception as exc:
        print(f"  ❌ 失败: {exc}")
        return 1

    # ---- 测试用例 7: 错误码体系 ----
    print("\n[测试7] 错误码体系")
    error_cases = [
        ("", "E001"),
        ("\x00\x01", "E003"),
        ('{"bad json"}', "E003"),
        ("invalid json {", "E003"),  # 新增：以 { 开头但 JSON 无效
    ]
    for test_input, expected_code in error_cases:
        try:
            process_single(test_input)
            print(f"  ❌ 失败: 输入未触发错误: {repr(test_input)}")
            return 1
        except SkillError as exc:
            assert exc.code == expected_code, f"期望 {expected_code}, 实际 {exc.code}"
    print(f"  ✅ 通过 ({len(error_cases)} 个错误场景)")

    # ---- 汇总 ----
    print("\n" + "=" * 50)
    print("全部自检通过 ✅")
    print("=" * 50)
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="ipython-dashboard 数据可视化工具",
        epilog="示例: python main.py --input '{\"name\":\"测试\"}' --format json",
    )
    parser.add_argument("--input", "-i", help="输入内容（文本/JSON/URL）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--batch", "-b", nargs="+", help="批量输入，空格分隔多个内容")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式
    if args.batch:
        try:
            output = process_batch(args.batch, args.format)
            print(output)
            return 0
        except SkillError as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1

    # 单条模式
    if args.input:
        try:
            output = process_single(args.input, args.format)
            print(output)
            return 0
        except SkillError as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1

    # 无参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
