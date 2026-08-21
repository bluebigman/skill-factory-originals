#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data-visual-report 技能实现脚本（Clean-Room 独立实现）

功能：
- 将表格数据（CSV/JSON）自动转为带图表与结论的可视化分析报告
- 支持趋势分析、占比统计、TopN排行、数据洞察、报表生成
- 提供 --selftest 离线自检模式（内置硬编码样例数据，不依赖外部环境）

错误码说明：
- E001: 参数解析错误
- E002: 输入文件不存在或不可读
- E003: 数据格式不支持（仅支持 CSV/JSON）
- E004: CSV 解析失败
- E005: JSON 解析失败
- E006: 数据为空或缺少必要字段
- E007: 数值列不存在或无法转换为数值
- E008: 报告生成失败（写入异常）
- E009: 自检断言失败
- E010: 未知内部错误

仅使用 Python 标准库，无需第三方依赖。
"""

import argparse
import csv
import json
import os
import sys
import tempfile
from datetime import timezone, datetime
from typing import Any, Dict, List, Optional
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 核心数据结构与常量
# ============================================================

SUPPORTED_FORMATS = (".csv", ".json")


class DataReportError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ============================================================
# 数据加载模块（CSV / JSON）
# ============================================================

def load_data(file_path: str) -> List[Dict[str, Any]]:
    """
    从文件加载表格数据，支持 CSV 和 JSON 格式。

    参数:
        file_path: 输入文件路径（.csv 或 .json）

    返回:
        列表，每个元素为一行记录的字典

    异常:
        E002: 文件不存在或不可读
        E003: 文件格式不支持
        E004: CSV 解析失败
        E005: JSON 解析失败
        E006: 数据为空
    """
    if not os.path.isfile(file_path):
        raise DataReportError("E002", f"文件不存在或不可读: {file_path}")
    if not os.access(file_path, os.R_OK):
        raise DataReportError("E002", f"文件无读取权限: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise DataReportError("E003", f"不支持的文件格式: {ext}（仅支持 {SUPPORTED_FORMATS}）")

    try:
        if ext == ".csv":
            data = _load_csv(file_path)
        else:  # .json
            data = _load_json(file_path)
    except DataReportError:
        raise
    except Exception as exc:
        raise DataReportError("E010", f"读取文件时发生未知错误: {exc}")

    if not data:
        raise DataReportError("E006", "数据为空，无法生成报告")

    return data


def _load_csv(file_path: str) -> List[Dict[str, Any]]:
    """内部：解析 CSV 文件"""
    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            # 跳过完全空的行
            rows = [row for row in reader if any(v.strip() for v in row.values())]
            return rows
    except csv.Error as exc:
        raise DataReportError("E004", f"CSV 解析失败: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise DataReportError("E004", f"CSV 编码解析失败（请确保 UTF-8 编码）: {exc}") from exc


def _load_json(file_path: str) -> List[Dict[str, Any]]:
    """内部：解析 JSON 文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise DataReportError("E005", f"JSON 解析失败: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise DataReportError("E005", f"JSON 编码解析失败: {exc}") from exc

    # 支持两种结构：顶层列表 或 顶层对象包含列表字段
    if isinstance(raw, list):
        data = raw
    elif isinstance(raw, dict):
        # 尝试常见的列表字段名
        for key in ("data", "rows", "records", "items"):
            if key in raw and isinstance(raw[key], list):
                data = raw[key]
                break
        else:
            # 如果对象本身是单行记录，包装成列表
            data = [raw]
    else:
        raise DataReportError("E005", "JSON 顶层结构必须是对象或数组")

    # 过滤非字典元素
    data = [item for item in data if isinstance(item, dict)]
    return data


# ============================================================
# 数据分析模块
# ============================================================

def analyze_data(data: List[Dict[str, Any]], value_col: str, category_col: Optional[str] = None) -> Dict[str, Any]:
    """
    对数据进行统计分析。

    参数:
        data: 行记录列表
        value_col: 数值列名
        category_col: 分类列名（可选，用于占比统计）

    返回:
        包含统计结果的字典

    异常:
        E006: 数据为空
        E007: 数值列不存在或无法转换
    """
    if not data:
        raise DataReportError("E006", "数据为空，无法分析")

    # 校验数值列存在
    if value_col not in data[0]:
        raise DataReportError("E007", f"数值列 '{value_col}' 不存在于数据中")

    # 提取数值
    values: List[float] = []
    valid_rows = []
    for row in data:
        try:
            val = float(row[value_col])
            values.append(val)
            valid_rows.append(row)
        except (ValueError, TypeError):
            continue  # 跳过无法转换的行

    if not values:
        raise DataReportError("E007", f"数值列 '{value_col}' 中没有有效的数值数据")

    # 基础统计
    total = sum(values)
    count = len(values)
    avg = total / count
    max_val = max(values)
    min_val = min(values)

    # 排序后的数值（用于中位数等）
    sorted_vals = sorted(values)
    if count % 2 == 1:
        median = sorted_vals[count // 2]
    else:
        median = (sorted_vals[count // 2 - 1] + sorted_vals[count // 2]) / 2

    # 标准差（样本标准差，n-1）
    if count > 1:
        variance = sum((v - avg) ** 2 for v in values) / (count - 1)
        stddev = variance ** 0.5
    else:
        stddev = 0.0

    # 趋势分析（按行顺序）
    trend = "平稳"
    if count >= 3:
        first_half = sum(values[: count // 2]) / (count // 2)
        second_half = sum(values[count // 2:]) / (count - count // 2)
        if second_half > first_half * 1.1:
            trend = "上升"
        elif second_half < first_half * 0.9:
            trend = "下降"

    # TopN 排行（默认 Top 5）
    top_n = 5
    sorted_rows = sorted(valid_rows, key=lambda r: float(r[value_col]), reverse=True)
    top_rows = sorted_rows[:top_n]

    # 占比统计（按分类列）
    category_stats: Dict[str, Dict[str, Any]] = {}
    if category_col and category_col in data[0]:
        cat_totals: Dict[str, float] = {}
        for row in valid_rows:
            cat = str(row.get(category_col, "未知"))
            cat_totals[cat] = cat_totals.get(cat, 0.0) + float(row[value_col])
        for cat, cat_total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            category_stats[cat] = {
                "value": cat_total,
                "percentage": cat_total / total if total > 0 else 0.0,
            }

    # 构建结果
    result = {
        "total": total,
        "count": count,
        "average": avg,
        "max": max_val,
        "min": min_val,
        "median": median,
        "stddev": stddev,
        "trend": trend,
        "top_rows": [
            {**row, value_col: float(row[value_col])} for row in top_rows
        ],
        "category_stats": category_stats,
        "value_col": value_col,
        "category_col": category_col,
    }

    return result


# ============================================================
# 报告生成模块（纯文本 / Markdown / HTML）
# ============================================================

def generate_report(
    data: List[Dict[str, Any]],
    value_col: str,
    category_col: Optional[str] = None,
    title: str = "数据洞察报告",
    output_format: str = "text",
) -> str:
    """
    生成可视化分析报告文本。

    参数:
        data: 行记录列表
        value_col: 数值列名
        category_col: 分类列名（可选）
        title: 报告标题
        output_format: 输出格式（text / markdown / html）

    返回:
        报告文本字符串
    """
    analysis = analyze_data(data, value_col, category_col)

    if output_format == "markdown":
        return _render_markdown(analysis, title)
    elif output_format == "html":
        return _render_html(analysis, title)
    else:
        return _render_text(analysis, title)


def _render_text(analysis: Dict[str, Any], title: str) -> str:
    """渲染纯文本报告"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  {title}")
    lines.append(f"  生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)

    vc = analysis["value_col"]
    lines.append(f"\n【数据概况】")
    lines.append(f"  记录数: {analysis['count']}")
    lines.append(f"  数值列: {vc}")

    lines.append(f"\n【核心指标】")
    lines.append(f"  总和: {analysis['total']:.2f}")
    lines.append(f"  平均值: {analysis['average']:.2f}")
    lines.append(f"  中位数: {analysis['median']:.2f}")
    lines.append(f"  最大值: {analysis['max']:.2f}")
    lines.append(f"  最小值: {analysis['min']:.2f}")
    lines.append(f"  标准差: {analysis['stddev']:.2f}")

    lines.append(f"\n【趋势判断】")
    lines.append(f"  整体趋势: {analysis['trend']}")

    lines.append(f"\n【Top 5 排行】")
    for i, row in enumerate(analysis["top_rows"], 1):
        val = row[vc]
        # 显示主键（第一个非数值字段）
        key = next((k for k in row.keys() if k != vc), "记录")
        label = row.get(key, f"第{i}条")
        lines.append(f"  {i}. {label}: {val:.2f}")

    if analysis["category_stats"]:
        lines.append(f"\n【占比统计（按 {analysis['category_col']}）】")
        for cat, stat in analysis["category_stats"].items():
            bar_len = int(stat["percentage"] * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            lines.append(f"  {cat:<20} {stat['percentage']*100:>6.1f}%  {bar}")

    lines.append("\n" + "=" * 60)
    lines.append("  报告生成完毕（纯文本格式）")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown(analysis: Dict[str, Any], title: str) -> str:
    """渲染 Markdown 报告"""
    lines = []
    lines.append(f"# {title}")
    lines.append(f"\n> 生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    vc = analysis["value_col"]
    lines.append("## 📊 数据概况")
    lines.append(f"- 记录数: **{analysis['count']}**")
    lines.append(f"- 数值列: `{vc}`")
    lines.append("")

    lines.append("## 📈 核心指标")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总和 | {analysis['total']:.2f} |")
    lines.append(f"| 平均值 | {analysis['average']:.2f} |")
    lines.append(f"| 中位数 | {analysis['median']:.2f} |")
    lines.append(f"| 最大值 | {analysis['max']:.2f} |")
    lines.append(f"| 最小值 | {analysis['min']:.2f} |")
    lines.append(f"| 标准差 | {analysis['stddev']:.2f} |")
    lines.append("")

    lines.append("## 🔍 趋势判断")
    lines.append(f"整体趋势: **{analysis['trend']}**")
    lines.append("")

    lines.append("## 🏆 Top 5 排行")
    lines.append("| 排名 | 记录 | 数值 |")
    lines.append("|------|------|------|")
    for i, row in enumerate(analysis["top_rows"], 1):
        key = next((k for k in row.keys() if k != vc), "记录")
        label = row.get(key, f"第{i}条")
        lines.append(f"| {i} | {label} | {row[vc]:.2f} |")
    lines.append("")

    if analysis["category_stats"]:
        lines.append(f"## 🧩 占比统计（按 {analysis['category_col']}）")
        lines.append("| 类别 | 数值 | 占比 |")
        lines.append("|------|------|------|")
        for cat, stat in analysis["category_stats"].items():
            lines.append(f"| {cat} | {stat['value']:.2f} | {stat['percentage']*100:.1f}% |")
        lines.append("")

    lines.append("---")
    lines.append("*报告由 data-visual-report 技能自动生成*")
    return "\n".join(lines)


def _render_html(analysis: Dict[str, Any], title: str) -> str:
    """渲染 HTML 报告（带简单 CSS 样式）"""
    vc = analysis["value_col"]
    top_rows_html = ""
    for i, row in enumerate(analysis["top_rows"], 1):
        key = next((k for k in row.keys() if k != vc), "记录")
        label = row.get(key, f"第{i}条")
        top_rows_html += (
            f"<tr><td>{i}</td><td>{label}</td><td>{row[vc]:.2f}</td></tr>"
        )

    cat_html = ""
    if analysis["category_stats"]:
        for cat, stat in analysis["category_stats"].items():
            cat_html += (
                f"<tr><td>{cat}</td><td>{stat['value']:.2f}</td>"
                f"<td>{stat['percentage']*100:.1f}%</td></tr>"
            )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 40px; background: #f9f9f9; }}
.container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
h2 {{ color: #34495e; margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
th, td {{ padding: 10px 15px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
th {{ background: #3498db; color: #fff; }}
tr:hover {{ background: #f5f5f5; }}
.meta {{ color: #7f8c8d; font-size: 14px; }}
.trend {{ font-size: 20px; font-weight: bold; color: #e74c3c; }}
</style>
</head>
<body>
<div class="container">
<h1>📊 {title}</h1>
<p class="meta">生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} | 记录数: {analysis['count']} | 数值列: <code>{vc}</code></p>

<h2>📈 核心指标</h2>
<table>
<tr><th>指标</th><th>数值</th></tr>
<tr><td>总和</td><td>{analysis['total']:.2f}</td></tr>
<tr><td>平均值</td><td>{analysis['average']:.2f}</td></tr>
<tr><td>中位数</td><td>{analysis['median']:.2f}</td></tr>
<tr><td>最大值</td><td>{analysis['max']:.2f}</td></tr>
<tr><td>最小值</td><td>{analysis['min']:.2f}</td></tr>
<tr><td>标准差</td><td>{analysis['stddev']:.2f}</td></tr>
</table>

<h2>🔍 趋势判断</h2>
<p class="trend">整体趋势: {analysis['trend']}</p>

<h2>🏆 Top 5 排行</h2>
<table>
<tr><th>排名</th><th>记录</th><th>数值</th></tr>
{top_rows_html}
</table>
"""

    if analysis["category_stats"]:
        html += f"""
<h2>🧩 占比统计（按 {analysis['category_col']}）</h2>
<table>
<tr><th>类别</th><th>数值</th><th>占比</th></tr>
{cat_html}
</table>
"""

    html += """
<p style="text-align:center; color:#95a5a6; margin-top:40px; font-size:12px;">
报告由 data-visual-report 技能自动生成
</p>
</div>
</body>
</html>"""
    return html


# ============================================================
# 文件输出模块
# ============================================================

def write_report(report: str, output_path: str) -> None:
    """
    将报告写入文件。

    参数:
        report: 报告文本
        output_path: 输出文件路径

    异常:
        E008: 写入失败
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
    except OSError as exc:
        raise DataReportError("E008", f"报告写入失败: {exc}") from exc


# ============================================================
# 命令行入口
# ============================================================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="数据洞察 · 图表报告自动生成（Clean-Room 独立实现）",
        epilog="示例: python main.py input.csv -v 销售额 -c 地区 -o report.md -f markdown",
    )
    parser.add_argument("--input", nargs="?", help="输入数据文件（CSV/JSON）")
    # -v 不再设为必选，因为 --selftest 模式不需要
    parser.add_argument("-v", "--value-col", help="数值列名")
    parser.add_argument("-c", "--category-col", help="分类列名（可选，用于占比统计）")
    parser.add_argument("-t", "--title", default="数据洞察报告", help="报告标题")
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("-f", "--format", choices=["text", "markdown", "html"], default="text", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    return parser.parse_args(argv)


def run_selftest() -> int:
    """
    离线自检：使用内置硬编码样例数据验证核心逻辑。
    不读外部文件、不依赖工作目录、不访问网络。
    """
    print("🔍 开始自检 data-visual-report ...")

    # ---- 硬编码样例数据 ----
    sample_data = [
        {"月份": "1月", "销售额": 120, "地区": "华东"},
        {"月份": "2月", "销售额": 150, "地区": "华东"},
        {"月份": "3月", "销售额": 135, "地区": "华北"},
        {"月份": "4月", "销售额": 180, "地区": "华北"},
        {"月份": "5月", "销售额": 160, "地区": "华南"},
        {"月份": "6月", "销售额": 210, "地区": "华南"},
    ]
    value_col = "销售额"
    category_col = "地区"

    # ---- 测试1: 数据分析 ----
    try:
        analysis = analyze_data(sample_data, value_col, category_col)
        assert analysis["count"] == 6, "记录数应为6"
        assert analysis["total"] > 900, "总和应大于900"
        assert analysis["total"] < 1000, "总和应小于1000"
        assert analysis["average"] > 150, "平均值应大于150"
        assert analysis["average"] < 170, "平均值应小于170"
        assert analysis["max"] == 210, "最大值应为210"
        assert analysis["min"] == 120, "最小值应为120"
        assert analysis["median"] > 150, "中位数应大于150"
        assert analysis["median"] < 160, "中位数应小于160"
        assert analysis["stddev"] > 25, "标准差应大于25"
        assert analysis["stddev"] < 40, "标准差应小于40"
        assert analysis["trend"] in ("上升", "下降", "平稳"), "趋势值非法"
        assert len(analysis["top_rows"]) == 5, "Top5应有5条"
        assert len(analysis["category_stats"]) == 3, "应有3个分类"
        # 占比总和约等于1
        total_pct = sum(s["percentage"] for s in analysis["category_stats"].values())
        assert 0.99 < total_pct < 1.01, "占比总和应接近1"
        print("  ✅ 数据分析逻辑正常")
    except AssertionError as exc:
        print(f"  ❌ 数据分析断言失败: {exc}")
        return 9  # E009

    # ---- 测试2: 报告生成 ----
    try:
        text_report = generate_report(sample_data, value_col, category_col, "自检报告", "text")
        assert "自检报告" in text_report, "文本报告应包含标题"
        assert "总和" in text_report, "文本报告应包含指标"
        assert "Top 5" in text_report, "文本报告应包含排行"

        md_report = generate_report(sample_data, value_col, category_col, "自检报告", "markdown")
        assert md_report.startswith("# "), "Markdown报告应以#开头"
        assert "| 指标 | 数值 |" in md_report, "Markdown报告应包含表格"

        html_report = generate_report(sample_data, value_col, category_col, "自检报告", "html")
        assert "<html" in html_report, "HTML报告应包含html标签"
        assert "<table" in html_report, "HTML报告应包含表格"
        print("  ✅ 报告生成逻辑正常")
    except AssertionError as exc:
        print(f"  ❌ 报告生成断言失败: {exc}")
        return 9  # E009

    # ---- 测试3: 异常处理 ----
    try:
        # 空数据
        try:
            analyze_data([], value_col)
            print("  ❌ 空数据未抛异常")
            return 9
        except DataReportError as exc:
            assert exc.code == "E006", f"空数据错误码应为E006，实际{exc.code}"
        print("  ✅ 空数据异常处理正常")

        # 缺失数值列
        try:
            analyze_data([{"a": 1}], "不存在的列")
            print("  ❌ 缺失列未抛异常")
            return 9
        except DataReportError as exc:
            assert exc.code == "E007", f"缺失列错误码应为E007，实际{exc.code}"
        print("  ✅ 缺失列异常处理正常")
    except AssertionError as exc:
        print(f"  ❌ 异常处理断言失败: {exc}")
        return 9

    # ---- 测试4: 临时文件读写 ----
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写 CSV
            csv_path = os.path.join(tmpdir, "test.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("月份,销售额,地区\n1月,100,华东\n2月,200,华北\n")
            loaded = load_data(csv_path)
            assert len(loaded) == 2, "CSV应加载2行"
            assert float(loaded[0]["销售额"]) == 100, "CSV数值解析错误"

            # 写 JSON
            json_path = os.path.join(tmpdir, "test.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(sample_data, f, ensure_ascii=False)
            loaded = load_data(json_path)
            assert len(loaded) == 6, "JSON应加载6行"

            # 写报告
            out_path = os.path.join(tmpdir, "report.md")
            write_report(md_report, out_path)
            assert os.path.isfile(out_path), "报告文件应存在"
            with open(out_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "自检报告" in content, "报告内容应包含标题"
        print("  ✅ 文件读写逻辑正常")
    except AssertionError as exc:
        print(f"  ❌ 文件读写断言失败: {exc}")
        return 9
    except Exception as exc:
        print(f"  ❌ 文件读写异常: {exc}")
        return 9

    print("\n🎉 全部自检通过！")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    try:
        args = parse_args(argv)

        # 自检模式 - 优先处理，不需要其他参数
        if args.selftest:
            return run_selftest()

        # 正常模式 - 此时需要验证必选参数
        if not args.input:
            print("错误: 缺少输入文件参数", file=sys.stderr)
            print("用法: python main.py <input> -v <value_col> [options]", file=sys.stderr)
            return 1  # E001

        if not args.value_col:
            print("错误: 缺少数值列参数 (-v/--value-col)", file=sys.stderr)
            print("用法: python main.py <input> -v <value_col> [options]", file=sys.stderr)
            return 1  # E001

        # 加载数据
        data = load_data(args.input)

        # 生成报告
        report = generate_report(
            data,
            args.value_col,
            args.category_col,
            args.title,
            args.format,
        )

        # 输出报告
        if args.output:
            write_report(report, args.output)
            print(f"✅ 报告已生成: {args.output}")
        else:
            print(report)

        return 0

    except DataReportError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return int(exc.code[1:])  # E001-E010 对应返回码 1-10
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"错误: [E010] 未知错误: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
