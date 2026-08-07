#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PretzelAI 技能核心实现（独立重写版）

功能：将数据、文件或URL转化为结构化洞察与可视化结果。
本脚本仅依据功能规格独立实现，不包含任何既有代码。

用法示例：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --input sample.csv  # 处理本地文件
"""

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ========== 错误码定义 ==========
ERROR_CODES = {
    "E001": "输入为空或缺少必要参数",
    "E002": "文件不存在或无法读取",
    "E003": "URL 无法访问或请求失败",
    "E004": "数据格式无法解析（非 CSV/JSON/Excel）",
    "E005": "输出格式不支持（仅支持 json/markdown）",
    "E006": "字段提取失败，字段不存在",
    "E007": "批量处理时单个项目失败",
    "E008": "置信度计算异常",
    "E009": "内部逻辑错误（不应发生）",
    "E010": "无效的操作模式",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误码并退出"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    print(f"[错误] {code}: {msg}", file=sys.stderr)
    sys.exit(1)


# ========== 数据解析模块 ==========

def parse_csv_text(text: str) -> List[Dict[str, str]]:
    """解析 CSV 文本为字典列表"""
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_json_text(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为字典列表"""
    data = json.loads(text)
    # 支持单个对象或对象列表
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    raise ValueError("JSON 顶层必须是对象或对象数组")


def parse_text_data(content: str, file_ext: str = "") -> List[Dict[str, Any]]:
    """根据扩展名或内容自动解析数据"""
    ext = file_ext.lower()
    if ext == ".csv" or (not ext and content.lstrip().startswith(("Name,", "id,", "日期,"))):
        return parse_csv_text(content)
    if ext == ".json" or (not ext and content.lstrip().startswith(("{", "["))):
        return parse_json_text(content)
    # 尝试按行解析为简单结构
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("空内容")
    return [{"line": line, "index": idx} for idx, line in enumerate(lines)]


# ========== 核心分析模块 ==========

def analyze_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """对记录列表执行核心分析，返回结构化洞察"""
    if not records:
        raise ValueError("记录列表为空")

    result: Dict[str, Any] = {
        "record_count": len(records),
        "fields": [],
        "field_stats": {},
        "summary": "",
        "confidence": "高",
    }

    # 收集字段信息
    all_keys: set = set()
    for rec in records:
        all_keys.update(rec.keys())

    result["fields"] = sorted(all_keys)

    # 字段统计
    for field in result["fields"]:
        values = [rec.get(field) for rec in records if rec.get(field) is not None]
        if not values:
            result["field_stats"][field] = {"non_null": 0, "unique": 0, "type": "unknown"}
            continue

        # 类型判断
        value_type = "string"
        numeric_count = 0
        for v in values:
            try:
                float(str(v).replace(",", ""))
                numeric_count += 1
            except (ValueError, TypeError):
                pass

        if numeric_count == len(values):
            value_type = "numeric"
        elif all(isinstance(v, (int, float)) for v in values):
            value_type = "numeric"
        elif all(isinstance(v, str) for v in values):
            value_type = "string"

        # 数值统计
        stats: Dict[str, Any] = {
            "non_null": len(values),
            "unique": len(set(values)),
            "type": value_type,
        }

        if value_type == "numeric":
            try:
                numeric_values = [float(str(v).replace(",", "")) for v in values]
                stats["min"] = min(numeric_values)
                stats["max"] = max(numeric_values)
                stats["avg"] = sum(numeric_values) / len(numeric_values)
            except (ValueError, ZeroDivisionError):
                pass

        result["field_stats"][field] = stats

    # 生成摘要
    result["summary"] = (
        f"共 {len(records)} 条记录，{len(result['fields'])} 个字段。"
        f"主要字段：{', '.join(result['fields'][:5])}"
    )

    # 置信度评估
    completeness = sum(
        1 for f in result["fields"]
        if result["field_stats"][f]["non_null"] > 0
    ) / max(len(result["fields"]), 1)

    if completeness < 0.5:
        result["confidence"] = "低"
        result["confidence_reason"] = "大量字段为空，数据完整性不足"
    elif completeness < 0.8:
        result["confidence"] = "中"
        result["confidence_reason"] = "部分字段存在缺失"
    else:
        result["confidence"] = "高"
        result["confidence_reason"] = "数据完整性良好"

    return result


def extract_key_insights(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """提取关键洞察：频次、异常值、时间戳等"""
    insights: Dict[str, Any] = {
        "top_values": {},
        "timestamps": [],
        "error_codes": [],
    }

    if not records:
        return insights

    # 找出可能的类别字段并统计频次
    sample_rec = records[0]
    for field, value in sample_rec.items():
        if isinstance(value, str) and len(value) < 50:
            counter = Counter(str(rec.get(field, "")) for rec in records if rec.get(field))
            if counter:
                insights["top_values"][field] = counter.most_common(5)

    # 查找时间戳字段（常见命名）
    for rec in records:
        for field in rec:
            if any(key in field.lower() for key in ["time", "date", "时间", "日期"]):
                val = rec.get(field)
                if val:
                    insights["timestamps"].append(str(val))
                    break

    # 查找错误码（常见模式）
    for rec in records:
        for field, value in rec.items():
            if any(key in field.lower() for key in ["error", "code", "错误", "码"]):
                if value:
                    insights["error_codes"].append(str(value))
                    break

    return insights


def format_output(analysis: Dict[str, Any], output_format: str = "json") -> str:
    """按指定格式输出结果"""
    if output_format == "json":
        return json.dumps(analysis, ensure_ascii=False, indent=2)

    if output_format == "markdown":
        lines = ["# 数据洞察报告", ""]
        lines.append(f"**记录数**: {analysis.get('record_count', 0)}")
        lines.append(f"**字段数**: {len(analysis.get('fields', []))}")
        lines.append(f"**置信度**: {analysis.get('confidence', '未知')}")
        lines.append("")
        lines.append("## 字段统计")
        lines.append("")
        lines.append("| 字段 | 非空数 | 唯一值 | 类型 |")
        lines.append("|------|--------|--------|------|")
        for field, stats in analysis.get("field_stats", {}).items():
            lines.append(
                f"| {field} | {stats.get('non_null', 0)} | "
                f"{stats.get('unique', 0)} | {stats.get('type', '?')} |"
            )
        lines.append("")
        lines.append(f"## 摘要")
        lines.append("")
        lines.append(analysis.get("summary", ""))
        return "\n".join(lines)

    raise ValueError(f"不支持的输出格式: {output_format}")


# ========== 数据加载模块 ==========

def load_from_file(file_path: str) -> List[Dict[str, Any]]:
    """从本地文件加载数据"""
    if not os.path.isfile(file_path):
        error_exit("E002", f"文件不存在: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ext = os.path.splitext(file_path)[1]
        return parse_text_data(content, ext)
    except Exception as e:
        error_exit("E004", f"文件解析失败: {str(e)}")


def load_from_url(url: str) -> List[Dict[str, Any]]:
    """从 URL 加载数据"""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            content = resp.read().decode("utf-8")
        return parse_text_data(content)
    except Exception as e:
        error_exit("E003", f"URL 请求失败: {str(e)}")


def load_from_text(text: str) -> List[Dict[str, Any]]:
    """从文本加载数据"""
    try:
        return parse_text_data(text)
    except Exception as e:
        error_exit("E004", f"文本解析失败: {str(e)}")


# ========== 批量处理模块 ==========

def batch_process(items: List[Dict[str, Any]], output_format: str = "json") -> List[Dict[str, Any]]:
    """批量处理多个数据源"""
    results = []
    for idx, item in enumerate(items):
        try:
            source = item.get("source", "")
            if source.startswith("http://") or source.startswith("https://"):
                records = load_from_url(source)
            elif os.path.isfile(source):
                records = load_from_file(source)
            else:
                records = load_from_text(source)

            analysis = analyze_records(records)
            insights = extract_key_insights(records)
            analysis["insights"] = insights
            results.append({
                "index": idx,
                "source": source,
                "result": analysis,
                "status": "success",
            })
        except Exception as e:
            results.append({
                "index": idx,
                "source": item.get("source", ""),
                "status": "failed",
                "error": str(e),
            })

    return results


# ========== 自检模块 ==========

def run_selftest() -> None:
    """离线自检核心逻辑，不依赖外部文件或网络"""
    print("=" * 60)
    print("PretzelAI 自检开始")
    print("=" * 60)

    # ---- 测试1: CSV 解析 ----
    print("\n[1/5] CSV 解析测试...")
    csv_text = """姓名,年龄,城市,分数
张三,25,北京,85.5
李四,30,上海,92.0
王五,28,广州,78.5"""
    records = parse_csv_text(csv_text)
    assert len(records) == 3, "CSV 解析记录数错误"
    assert records[0]["姓名"] == "张三", "CSV 字段值错误"
    print("  ✓ CSV 解析通过")

    # ---- 测试2: JSON 解析 ----
    print("\n[2/5] JSON 解析测试...")
    json_text = '[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]'
    records = parse_json_text(json_text)
    assert len(records) == 2, "JSON 解析记录数错误"
    assert records[1]["name"] == "B", "JSON 字段值错误"
    print("  ✓ JSON 解析通过")

    # ---- 测试3: 核心分析 ----
    print("\n[3/5] 核心分析测试...")
    test_records = [
        {"date": "2024-01-01", "value": 10, "category": "A", "error_code": "E001"},
        {"date": "2024-01-02", "value": 20, "category": "B", "error_code": "E002"},
        {"date": "2024-01-03", "value": 30, "category": "A", "error_code": "E001"},
        {"date": "2024-01-04", "value": 40, "category": "C", "error_code": "E003"},
    ]
    analysis = analyze_records(test_records)
    assert analysis["record_count"] == 4, "记录数统计错误"
    assert len(analysis["fields"]) >= 4, "字段数统计错误"
    assert analysis["confidence"] in ["高", "中", "低"], "置信度等级错误"
    # 宽松断言：平均值应在合理范围
    value_stats = analysis["field_stats"].get("value", {})
    if "avg" in value_stats:
        assert 10 <= value_stats["avg"] <= 40, "平均值超出合理范围"
    print("  ✓ 核心分析通过")

    # ---- 测试4: 洞察提取 ----
    print("\n[4/5] 洞察提取测试...")
    insights = extract_key_insights(test_records)
    assert "top_values" in insights, "缺少 top_values"
    assert "error_codes" in insights, "缺少 error_codes"
    assert len(insights["error_codes"]) > 0, "错误码提取为空"
    assert len(insights["timestamps"]) > 0, "时间戳提取为空"
    print("  ✓ 洞察提取通过")

    # ---- 测试5: 输出格式化 ----
    print("\n[5/5] 输出格式化测试...")
    json_output = format_output(analysis, "json")
    parsed_back = json.loads(json_output)
    assert parsed_back["record_count"] == 4, "JSON 输出回读错误"

    md_output = format_output(analysis, "markdown")
    assert "# 数据洞察报告" in md_output, "Markdown 输出缺少标题"
    assert "| 字段 |" in md_output, "Markdown 输出缺少表格"
    print("  ✓ 输出格式化通过")

    # ---- 批量处理测试 ----
    print("\n[附加] 批量处理测试...")
    batch_items = [
        {"source": csv_text},
        {"source": json_text},
    ]
    batch_results = batch_process(batch_items)
    assert len(batch_results) == 2, "批量处理数量错误"
    assert all(item["status"] == "success" for item in batch_results), "批量处理有失败项"
    print("  ✓ 批量处理通过")

    print("\n" + "=" * 60)
    print("✅ 所有自检通过！")
    print("=" * 60)


# ========== 主入口 ==========

def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="PretzelAI - 数据探索与可视化分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --selftest                     # 运行自检
  python main.py --input data.csv               # 处理CSV文件
  python main.py --input data.json --format md  # 处理JSON并输出Markdown
  python main.py --text "a,b\\n1,2\\n3,4"        # 处理文本
  python main.py --url https://example.com/data.json  # 处理URL
        """,
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--url", type=str, help="输入URL")
    parser.add_argument("--text", type=str, help="直接输入文本数据")
    parser.add_argument("--format", type=str, default="json", choices=["json", "markdown"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--batch", type=str, help="批量处理JSON文件（包含source数组）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 批量模式
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                batch_data = json.load(f)
            items = batch_data.get("items", batch_data if isinstance(batch_data, list) else [])
            results = batch_process(items, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        except FileNotFoundError:
            error_exit("E002", f"批量文件不存在: {args.batch}")
        except json.JSONDecodeError:
            error_exit("E004", "批量文件不是有效JSON")
        return

    # 单条处理模式
    try:
        if args.input:
            records = load_from_file(args.input)
        elif args.url:
            records = load_from_url(args.url)
        elif args.text:
            records = load_from_text(args.text)
        else:
            error_exit("E001", "请提供 --input、--url、--text 或 --selftest 参数")

        analysis = analyze_records(records)
        insights = extract_key_insights(records)
        analysis["insights"] = insights

        output = format_output(analysis, args.format)
        print(output)

    except ValueError as e:
        error_exit("E004", str(e))
    except Exception as e:
        error_exit("E009", f"未预期错误: {str(e)}")


if __name__ == "__main__":
    main()
