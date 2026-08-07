#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data-visual-report 独立实现脚本
功能：将表格数据自动转为带图表与结论的可视化分析报告。
本脚本为 clean-room 实现，仅依据功能规格编写。
"""

import sys
import json
import math
import argparse
from datetime import datetime
from collections import Counter, OrderedDict


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或格式不正确",
    "E002": "数据列名缺失（需要 name/value 字段）",
    "E003": "数据值无法转换为数值",
    "E004": "数据行数不足，无法进行统计分析",
    "E005": "图表类型不支持",
    "E006": "输出目录无法创建或写入",
    "E007": "输入文件读取失败",
    "E008": "时间序列数据格式错误",
    "E009": "JSON 序列化失败",
    "E010": "内部计算错误（未知异常）",
}


def fail(code: str, message: str = "") -> None:
    """输出错误信息并退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        sys.stderr.write(f"[{code}] {msg}: {message}\n")
    else:
        sys.stderr.write(f"[{code}] {msg}\n")
    sys.exit(1)


# ============================================================
# 核心计算逻辑（纯函数，便于自检）
# ============================================================

def _to_number(value):
    """尝试将值转为 float，失败返回 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_data(data):
    """
    校验输入数据结构。
    期望格式: [{"name": "A", "value": 10}, ...]
    返回 (是否有效, 错误码或 None)
    """
    if not isinstance(data, list) or len(data) == 0:
        return False, "E001"
    if not isinstance(data[0], dict):
        return False, "E001"
    if "name" not in data[0] or "value" not in data[0]:
        return False, "E002"
    # 检查所有值可否转为数值
    for item in data:
        if not isinstance(item, dict) or "name" not in item or "value" not in item:
            return False, "E002"
        if _to_number(item["value"]) is None:
            return False, "E003"
    if len(data) < 2:
        return False, "E004"
    return True, None


def compute_stats(data):
    """
    计算核心统计指标。
    返回 dict: {total, mean, median, min, max, stddev, top3, bottom3, distribution}
    """
    values = [_to_number(item["value"]) for item in data]
    names = [item["name"] for item in data]

    total = sum(values)
    count = len(values)
    mean = total / count if count > 0 else 0.0

    # 中位数
    sorted_vals = sorted(values)
    mid = count // 2
    if count % 2 == 0:
        median = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    else:
        median = sorted_vals[mid]

    min_val = min(values)
    max_val = max(values)

    # 标准差（总体）
    if count > 0:
        variance = sum((v - mean) ** 2 for v in values) / count
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0

    # Top3 和 Bottom3（按值排序）
    paired = list(zip(names, values))
    paired_sorted = sorted(paired, key=lambda x: x[1], reverse=True)
    top3 = [{"name": n, "value": v} for n, v in paired_sorted[:3]]
    bottom3 = [{"name": n, "value": v} for n, v in paired_sorted[-3:][::-1]]

    # 分布（四等分）
    distribution = {}
    if count >= 4:
        quartiles = [sorted_vals[int(count * i / 4)] for i in range(1, 4)]
        ranges = [
            (float("-inf"), quartiles[0]),
            (quartiles[0], quartiles[1]),
            (quartiles[1], quartiles[2]),
            (quartiles[2], float("inf")),
        ]
        labels = ["Q1(低)", "Q2(中低)", "Q3(中高)", "Q4(高)"]
        for label, rng in zip(labels, ranges):
            distribution[label] = sum(1 for v in values if rng[0] <= v < rng[1] or (label == "Q4(高)" and v == max_val))
    else:
        distribution["全部"] = count

    return {
        "total": total,
        "count": count,
        "mean": mean,
        "median": median,
        "min": min_val,
        "max": max_val,
        "stddev": stddev,
        "top3": top3,
        "bottom3": bottom3,
        "distribution": distribution,
    }


def generate_conclusion(stats):
    """
    根据统计结果生成自然语言结论。
    使用宽松的规则，不依赖精确值。
    """
    lines = []
    lines.append(f"数据共包含 {stats['count']} 个条目，总值为 {stats['total']:.2f}。")
    lines.append(f"平均值约为 {stats['mean']:.2f}，中位数为 {stats['median']:.2f}。")

    # 对比均值和中位数判断分布形态
    diff_ratio = abs(stats["mean"] - stats["median"]) / (stats["mean"] + 1e-9)
    if diff_ratio > 0.2:
        lines.append("均值与中位数差异较大，数据可能存在偏态分布。")
    else:
        lines.append("均值与中位数较为接近，数据分布相对对称。")

    # 极差分析
    range_val = stats["max"] - stats["min"]
    if stats["mean"] > 1e-9 and range_val / stats["mean"] > 2:
        lines.append("数据极差较大，离散程度高。")
    else:
        lines.append("数据极差适中，离散程度可控。")

    # Top 项结论
    if stats["top3"]:
        top_names = "、".join(item["name"] for item in stats["top3"][:2])
        lines.append(f"排名靠前的项包括：{top_names} 等。")

    return " ".join(lines)


def generate_markdown_report(data, title="数据分析报告"):
    """
    生成 Markdown 格式的完整报告。
    """
    valid, err = validate_data(data)
    if not valid:
        fail(err)

    stats = compute_stats(data)
    conclusion = generate_conclusion(stats)

    # 构建表格
    table_rows = "\n".join(
        f"| {item['name']} | {_to_number(item['value']):.2f} |"
        for item in data
    )

    # 构建 TopN 表格
    top_rows = "\n".join(
        f"| {item['name']} | {item['value']:.2f} |"
        for item in stats["top3"]
    )

    # 分布表格
    dist_rows = "\n".join(
        f"| {k} | {v} |" for k, v in stats["distribution"].items()
    )

    report = f"""# {title}

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 数据概览

| 指标 | 数值 |
|------|------|
| 条目数 | {stats['count']} |
| 总和 | {stats['total']:.2f} |
| 平均值 | {stats['mean']:.2f} |
| 中位数 | {stats['median']:.2f} |
| 最小值 | {stats['min']:.2f} |
| 最大值 | {stats['max']:.2f} |
| 标准差 | {stats['stddev']:.2f} |

## 数据明细

| 名称 | 数值 |
|------|------|
{table_rows}

## Top 3 排行

| 名称 | 数值 |
|------|------|
{top_rows}

## 分布情况

| 区间 | 数量 |
|------|------|
{dist_rows}

## 结论

{conclusion}

## 图表建议

- **柱状图**：适合展示各条目数值对比
- **饼图**：适合展示占比分布（当条目数较少时）
- **折线图**：适合展示趋势变化（若数据有序）

---
*本报告由 data-visual-report Skill 自动生成（v1.0.1）*
"""
    return report


def generate_json_report(data):
    """
    生成 JSON 格式的结构化报告。
    """
    valid, err = validate_data(data)
    if not valid:
        fail(err)

    stats = compute_stats(data)
    report = {
        "meta": {
            "skill": "data-visual-report",
            "version": "1.0.1",
            "generated_at": datetime.now().isoformat(),
        },
        "stats": {
            "count": stats["count"],
            "total": round(stats["total"], 4),
            "mean": round(stats["mean"], 4),
            "median": round(stats["median"], 4),
            "min": round(stats["min"], 4),
            "max": round(stats["max"], 4),
            "stddev": round(stats["stddev"], 4),
        },
        "top3": [{"name": i["name"], "value": round(i["value"], 4)} for i in stats["top3"]],
        "bottom3": [{"name": i["name"], "value": round(i["value"], 4)} for i in stats["bottom3"]],
        "distribution": {k: v for k, v in stats["distribution"].items()},
        "conclusion": generate_conclusion(stats),
    }
    try:
        return json.dumps(report, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        fail("E009")


# ============================================================
# 图表生成（简易 ASCII 图表，无需第三方库）
# ============================================================

def generate_ascii_bar_chart(data, width=40):
    """
    生成简易 ASCII 柱状图。
    """
    valid, err = validate_data(data)
    if not valid:
        fail(err)

    values = [_to_number(item["value"]) for item in data]
    names = [item["name"] for item in data]
    max_val = max(values) if max(values) > 0 else 1

    lines = []
    lines.append("简易柱状图：")
    lines.append("")
    
    for name, value in zip(names, values):
        bar_length = int((value / max_val) * width)
        bar = "#" * bar_length
        lines.append(f"{name:>10} | {bar} {value:.2f}")
    
    lines.append("")
    lines.append(f"图例：每个 # 代表 {max_val / width:.2f} 单位")
    
    return "\n".join(lines)


# ============================================================
# 主程序入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="数据可视化报告生成工具")
    parser.add_argument("--input", "-i", type=str, help="输入数据文件（JSON格式）")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--format", "-f", choices=["markdown", "json", "chart"], default="markdown", help="输出格式")
    parser.add_argument("--title", "-t", type=str, default="数据分析报告", help="报告标题")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    if args.selftest:
        run_selftest()
        return
    
    if not args.input:
        fail("E001", "请提供输入文件路径")
    
    # 读取输入数据
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        fail("E007", f"文件 {args.input} 不存在")
    except json.JSONDecodeError:
        fail("E001", "输入文件不是有效的JSON格式")
    
    # 校验数据
    valid, err = validate_data(data)
    if not valid:
        fail(err)
    
    # 生成报告
    if args.format == "markdown":
        report = generate_markdown_report(data, args.title)
    elif args.format == "json":
        report = generate_json_report(data)
    elif args.format == "chart":
        report = generate_ascii_bar_chart(data)
    else:
        fail("E005", f"不支持的格式: {args.format}")
    
    # 输出
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"报告已保存到: {args.output}")
        except (IOError, OSError):
            fail("E006", f"无法写入文件 {args.output}")
    else:
        print(report)


def run_selftest():
    """运行自检测试。"""
    print("=" * 50)
    print("data-visual-report 自检开始")
    print("=" * 50)
    
    # 测试数据
    test_data = [
        {"name": "A", "value": 10},
        {"name": "B", "value": 20},
        {"name": "C", "value": 15},
        {"name": "D", "value": 30},
        {"name": "E", "value": 25},
    ]
    
    # 测试1: 数据校验
    print("\n[测试1] 数据校验")
    valid, err = validate_data(test_data)
    assert valid, f"数据校验失败: {err}"
    print("  ✓ 有效数据校验通过")
    
    # 测试2: 无效数据
    print("\n[测试2] 无效数据检测")
    invalid_data = []
    valid, err = validate_data(invalid_data)
    assert not valid and err == "E001", f"空数据应返回E001，实际: {err}"
    print("  ✓ 空数据检测通过")
    
    invalid_data = [{"name": "A"}]
    valid, err = validate_data(invalid_data)
    assert not valid and err == "E002", f"缺少value字段应返回E002，实际: {err}"
    print("  ✓ 缺少字段检测通过")
    
    invalid_data = [{"name": "A", "value": "abc"}]
    valid, err = validate_data(invalid_data)
    assert not valid and err == "E003", f"非数值应返回E003，实际: {err}"
    print("  ✓ 非数值检测通过")
    
    # 测试3: 统计计算
    print("\n[测试3] 统计计算")
    stats = compute_stats(test_data)
    assert stats["count"] == 5, f"条目数错误: {stats['count']}"
    assert stats["total"] == 100, f"总和错误: {stats['total']}"
    assert stats["mean"] == 20, f"平均值错误: {stats['mean']}"
    assert stats["median"] == 20, f"中位数错误: {stats['median']}"
    assert stats["min"] == 10, f"最小值错误: {stats['min']}"
    assert stats["max"] == 30, f"最大值错误: {stats['max']}"
    print("  ✓ 基本统计计算通过")
    
    # 测试4: Top3 和 Bottom3
    print("\n[测试4] Top3 和 Bottom3")
    assert len(stats["top3"]) == 3, f"Top3 数量错误: {len(stats['top3'])}"
    assert stats["top3"][0]["name"] == "D", f"Top1 错误: {stats['top3'][0]['name']}"
    assert stats["bottom3"][0]["name"] == "A", f"Bottom1 错误: {stats['bottom3'][0]['name']}"
    print("  ✓ Top3/Bottom3 计算通过")
    
    # 测试5: Markdown 报告生成
    print("\n[测试5] Markdown 报告生成")
    md_report = generate_markdown_report(test_data, "测试报告")
    assert "# 测试报告" in md_report, "Markdown 报告缺少标题"
    assert "## 数据概览" in md_report, "Markdown 报告缺少概览"
    assert "## 结论" in md_report, "Markdown 报告缺少结论"
    print("  ✓ Markdown 报告生成通过")
    
    # 测试6: JSON 报告生成
    print("\n[测试6] JSON 报告生成")
    json_report = generate_json_report(test_data)
    parsed = json.loads(json_report)
    assert "meta" in parsed and "stats" in parsed, "JSON 报告结构错误"
    assert parsed["stats"]["count"] == 5, "JSON 报告统计错误"
    print("  ✓ JSON 报告生成通过")
    
    # 测试7: ASCII 图表生成
    print("\n[测试7] ASCII 图表生成")
    chart = generate_ascii_bar_chart(test_data)
    assert "简易柱状图" in chart, "图表缺少标题"
    assert "A" in chart and "E" in chart, "图表缺少数据项"
    print("  ✓ ASCII 图表生成通过")
    
    # 测试8: 错误处理
    print("\n[测试8] 错误处理")
    try:
        generate_markdown_report([])
        assert False, "空数据应抛出错误"
    except SystemExit as e:
        assert e.code == 1, f"错误退出码应为1，实际: {e.code}"
    print("  ✓ 错误处理通过")
    
    print("\n" + "=" * 50)
    print("所有自检测试通过！")
    print("=" * 50)


if __name__ == "__main__":
    main()
