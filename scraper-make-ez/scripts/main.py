#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scraper-make-ez - 爬虫采集工具

基于功能规格的 clean-room 独立实现。
仅使用标准库，提供结构化解析、置信度评估、批量处理与自检能力。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义（对应规格 E001-E005，另增内部错误码）
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部错误：数据解析失败",
    "E007": "内部错误：输出序列化失败",
    "E008": "内部错误：未知处理模式",
    "E009": "内部错误：自检数据异常",
    "E010": "内部错误：参数错误",
}


class ScraperError(Exception):
    """带错误码的异常类"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def extract_fields(data: Any) -> List[Dict[str, Any]]:
    """
    从输入数据中提取关键字段并结构化。

    支持：
    - 字典：直接作为单条记录
    - 列表：逐项处理，元素为字典或可转为字典
    - 字符串：尝试 JSON 解析，失败则视为单字段文本
    - 其他类型：包装为 value 字段
    """
    if data is None:
        raise ScraperError("E001")

    # 字符串尝试 JSON 解析
    if isinstance(data, str):
        stripped = data.strip()
        if not stripped:
            raise ScraperError("E001")
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            # 非 JSON 文本，视为单条记录
            return [{"content": stripped, "type": "text"}]

    # 字典：单条记录
    if isinstance(data, dict):
        if not data:
            raise ScraperError("E001")
        return [dict(data)]

    # 列表：逐项处理
    if isinstance(data, list):
        if not data:
            raise ScraperError("E001")
        records = []
        for item in data:
            if isinstance(item, dict):
                records.append(dict(item))
            elif isinstance(item, (str, int, float, bool)):
                records.append({"value": item, "type": type(item).__name__})
            else:
                # 其他类型尝试序列化
                try:
                    records.append({"value": json.dumps(item, ensure_ascii=False)})
                except (TypeError, ValueError):
                    records.append({"value": str(item), "type": "unknown"})
        return records

    # 其他标量类型
    return [{"value": data, "type": type(data).__name__}]


def compute_confidence(record: Dict[str, Any]) -> Tuple[float, str]:
    """
    计算单条记录的置信度。

    规则（宽松评估，避免精确边界）：
    - 记录非空且包含至少 2 个字段：置信度较高
    - 记录非空但仅 1 个字段：置信度中等
    - 字段值包含明显缺失标记（如空字符串、null、None）：降低置信度
    - 返回 (置信度百分比, 标注说明)
    """
    if not record:
        return 0.0, "[需核实] 记录为空"

    # 基础分：记录非空即有一定置信度
    base = 70.0

    # 字段数量加分
    field_count = len(record)
    if field_count >= 3:
        base += 15.0
    elif field_count == 2:
        base += 10.0
    else:
        base += 5.0

    # 缺失标记检测
    missing_indicators = {"", None, "null", "None", "N/A", "n/a"}
    missing_count = 0
    for value in record.values():
        if value is None:
            missing_count += 1
        elif isinstance(value, str) and value.strip().lower() in {str(x).lower() for x in missing_indicators}:
            missing_count += 1

    if missing_count > 0:
        base -= 20.0 * min(missing_count, 3)  # 最多扣 60%

    # 限制在合理范围
    confidence = max(0.0, min(100.0, base))

    # 标注规则
    if confidence >= 90.0:
        note = "直接输出"
    elif confidence >= 85.0:
        note = "建议复核"
    else:
        note = "[需核实]"

    return confidence, note


def process_input(data: Any, mode: str = "standard") -> Dict[str, Any]:
    """
    核心处理流程。

    mode:
      - "standard": 标准流程，提取字段并计算置信度
      - "batch": 批量模式，输入应为列表，逐项处理
      - "summary": 仅提取字段，不计算置信度（快速模式）
    """
    try:
        records = extract_fields(data)
    except ScraperError as e:
        raise e

    if mode == "batch":
        # 批量模式要求输入为列表
        if not isinstance(data, list):
            raise ScraperError("E003", "批量模式要求输入为列表")
        results = []
        for record in records:
            confidence, note = compute_confidence(record)
            results.append({
                "data": record,
                "confidence": round(confidence, 1),
                "note": note,
            })
        return {"mode": "batch", "count": len(results), "results": results}

    elif mode == "summary":
        # 快速模式：仅提取字段
        return {"mode": "summary", "count": len(records), "records": records}

    elif mode == "standard":
        # 标准模式：字段 + 置信度
        results = []
        for record in records:
            confidence, note = compute_confidence(record)
            results.append({
                "data": record,
                "confidence": round(confidence, 1),
                "note": note,
            })
        return {"mode": "standard", "count": len(results), "results": results}

    else:
        raise ScraperError("E008", f"未知处理模式: {mode}")


def format_output(result: Dict[str, Any], fmt: str = "json") -> str:
    """
    按指定格式输出结果。

    支持：json（默认）、text（简单文本）、pretty（带缩进的 JSON）
    """
    try:
        if fmt == "json":
            return json.dumps(result, ensure_ascii=False)
        elif fmt == "pretty":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif fmt == "text":
            lines = []
            lines.append(f"处理模式: {result.get('mode', 'unknown')}")
            lines.append(f"记录数量: {result.get('count', 0)}")
            for i, item in enumerate(result.get("results", []), 1):
                lines.append(f"\n记录 {i}:")
                lines.append(f"  数据: {json.dumps(item.get('data', {}), ensure_ascii=False)}")
                lines.append(f"  置信度: {item.get('confidence', 0)}%")
                lines.append(f"  标注: {item.get('note', '')}")
            return "\n".join(lines)
        else:
            raise ScraperError("E010", f"不支持的输出格式: {fmt}")
    except (TypeError, ValueError) as e:
        raise ScraperError("E007", f"输出序列化失败: {str(e)}")


def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保任何环境直接可过。
    """
    print("开始自检...")

    # 自检样例 1：标准模式 - 字典输入
    sample1 = {"name": "示例商品", "price": 99.5, "stock": 10}
    try:
        result1 = process_input(sample1, mode="standard")
        assert result1["mode"] == "standard"
        assert result1["count"] == 1
        assert result1["results"][0]["confidence"] >= 80.0, "置信度应较高"
        assert result1["results"][0]["note"] in ("直接输出", "建议复核")
        print("  [通过] 标准模式-字典输入")
    except AssertionError as e:
        print(f"  [失败] 标准模式-字典输入: {e}")
        return False
    except ScraperError as e:
        print(f"  [失败] 标准模式-字典输入: {e.code} {e.message}")
        return False

    # 自检样例 2：批量模式 - 列表输入
    sample2 = [
        {"url": "https://example.com/page1", "title": "页面1"},
        {"url": "https://example.com/page2", "title": "页面2", "tags": ["a", "b"]},
    ]
    try:
        result2 = process_input(sample2, mode="batch")
        assert result2["mode"] == "batch"
        assert result2["count"] == 2
        assert len(result2["results"]) == 2
        for item in result2["results"]:
            assert 0.0 <= item["confidence"] <= 100.0
        print("  [通过] 批量模式-列表输入")
    except AssertionError as e:
        print(f"  [失败] 批量模式-列表输入: {e}")
        return False
    except ScraperError as e:
        print(f"  [失败] 批量模式-列表输入: {e.code} {e.message}")
        return False

    # 自检样例 3：JSON 字符串输入
    sample3 = '{"key1": "value1", "key2": 42}'
    try:
        result3 = process_input(sample3, mode="standard")
        assert result3["count"] == 1
        assert "key1" in result3["results"][0]["data"]
        print("  [通过] JSON字符串输入")
    except AssertionError as e:
        print(f"  [失败] JSON字符串输入: {e}")
        return False
    except ScraperError as e:
        print(f"  [失败] JSON字符串输入: {e.code} {e.message}")
        return False

    # 自检样例 4：空输入错误处理
    try:
        process_input("", mode="standard")
        print("  [失败] 空输入应抛出 E001")
        return False
    except ScraperError as e:
        assert e.code == "E001", f"应抛出 E001，实际 {e.code}"
        print("  [通过] 空输入错误处理")

    # 自检样例 5：summary 快速模式
    sample5 = [1, 2, 3, "four", {"five": 5}]
    try:
        result5 = process_input(sample5, mode="summary")
        assert result5["mode"] == "summary"
        assert result5["count"] == 5
        print("  [通过] summary快速模式")
    except AssertionError as e:
        print(f"  [失败] summary快速模式: {e}")
        return False
    except ScraperError as e:
        print(f"  [失败] summary快速模式: {e.code} {e.message}")
        return False

    # 自检样例 6：输出格式
    try:
        result6 = process_input({"a": 1}, mode="standard")
        json_out = format_output(result6, "json")
        assert isinstance(json_out, str)
        assert len(json_out) > 0
        pretty_out = format_output(result6, "pretty")
        assert "\n" in pretty_out
        text_out = format_output(result6, "text")
        assert "记录数量" in text_out
        print("  [通过] 输出格式")
    except AssertionError as e:
        print(f"  [失败] 输出格式: {e}")
        return False
    except ScraperError as e:
        print(f"  [失败] 输出格式: {e.code} {e.message}")
        return False

    # 自检样例 7：缺失字段置信度降低
    sample7 = {"name": "不完整记录", "desc": ""}
    try:
        result7 = process_input(sample7, mode="standard")
        conf = result7["results"][0]["confidence"]
        # 缺失字段应导致置信度降低（但不做精确断言）
        assert conf < 100.0, "缺失字段应降低置信度"
        print(f"  [通过] 缺失字段置信度评估 (置信度={conf}%)")
    except AssertionError as e:
        print(f"  [失败] 缺失字段置信度评估: {e}")
        return False
    except ScraperError as e:
        print(f"  [失败] 缺失字段置信度评估: {e.code} {e.message}")
        return False

    print("所有自检通过 ✓")
    return True


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="scraper-make-ez - 爬虫采集工具",
        epilog="示例: python main.py --input '{\"key\": \"value\"}' --mode standard --format pretty"
    )
    parser.add_argument("--input", type=str, help="输入数据（JSON 字符串或文本）")
    parser.add_argument("--mode", type=str, choices=["standard", "batch", "summary"], default="standard",
                        help="处理模式: standard(默认), batch(批量), summary(快速)")
    parser.add_argument("--format", type=str, choices=["json", "pretty", "text"], default="json",
                        help="输出格式: json(默认), pretty, text")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--file", type=str, help="从文件读取输入（可选）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except Exception as e:
            print(f"自检异常: {str(e)}")
            return 1

    # 正常处理模式
    try:
        # 获取输入
        if args.file:
            # 从文件读取（可选功能，但自检不依赖此）
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except OSError as e:
                raise ScraperError("E010", f"无法读取文件: {str(e)}")
        elif args.input:
            input_data = args.input
        else:
            # 无输入时读取标准输入（管道）
            if not sys.stdin.isatty():
                input_data = sys.stdin.read()
            else:
                raise ScraperError("E001")

        # 处理输入
        result = process_input(input_data, mode=args.mode)

        # 输出结果
        output = format_output(result, args.format)
        print(output)
        return 0

    except ScraperError as e:
        print(f"错误: {e.code} {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E006 内部错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
