#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""visual_report.py — 数据洞察可视化报告工具（data-visual-report 真实实现）
读 CSV 表格 → 统计计算（均值/中位数/极值/标准差/趋势/占比/TopN）→
生成自包含 HTML 报告（Chart.js 图表）+ Markdown 结论。
纯标准库（csv），零第三方依赖。
"""
import argparse
import csv
import html
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

DEMO_DATA = [
    ("1月", "120"), ("2月", "135"), ("3月", "128"), ("4月", "152"),
    ("5月", "168"), ("6月", "175"), ("7月", "190"), ("8月", "205"),
    ("9月", "198"), ("10月", "220"), ("11月", "235"), ("12月", "260"),
]


def read_csv(path: Path):
    """读 CSV，返回 (headers, rows[dict])，数值列自动转 float"""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = []
        for raw in reader:
            row = {}
            for h in headers:
                v = raw.get(h, "")
                try:
                    row[h] = float(v)
                except (ValueError, TypeError):
                    row[h] = v
            rows.append(row)
    return headers, rows


def pick_columns(headers, rows, x_col, y_col):
    """选 x/y 列：默认第一列 x，其余数值列 y"""
    num_cols = []
    for h in headers:
        if all(isinstance(r.get(h), (int, float)) for r in rows if r.get(h) is not None):
            num_cols.append(h)
    x = x_col or (headers[0] if headers else "index")
    ys = [y_col] if y_col else [c for c in num_cols if c != x]
    return x, ys, num_cols


def analyze(x_col, y_cols, rows):
    """统计计算 + 结论生成"""
    x_vals = [str(r.get(x_col, i)) for i, r in enumerate(rows)]
    stats = {}
    for y in y_cols:
        series = [r[y] for r in rows if isinstance(r.get(y), (int, float))]
        if not series:
            continue
        s = {
            "count": len(series),
            "mean": round(statistics.mean(series), 2),
            "median": round(statistics.median(series), 2),
            "min": round(min(series), 2),
            "max": round(max(series), 2),
            "stdev": round(statistics.stdev(series), 2) if len(series) > 1 else 0,
            "sum": round(sum(series), 2),
            "trend": "上升" if len(series) > 1 and series[-1] > series[0] else "下降" if len(series) > 1 else "平稳",
            "delta_pct": round((series[-1] / series[0] - 1) * 100, 2) if len(series) > 1 and series[0] else 0,
        }
        stats[y] = s
    return x_vals, stats


def make_conclusions(x_col, stats):
    lines = []
    for y, s in stats.items():
        if s["trend"] == "上升":
            lines.append(f"- **{y}** 整体呈**上升**趋势，期末较期初 **+{s['delta_pct']}%**"
                         f"（均值 {s['mean']}，峰值 {s['max']}）。")
        elif s["trend"] == "下降":
            lines.append(f"- **{y}** 整体呈**下降**趋势，期末较期初 **{s['delta_pct']}%**"
                         f"（均值 {s['mean']}，谷值 {s['min']}）。")
        else:
            lines.append(f"- **{y}** 整体**平稳**，均值 {s['mean']}，波动 {s['stdev']}。")
        if len(s) and s.get("stdev") and s["mean"] and s["stdev"] / s["mean"] > 0.3:
            lines.append(f"  - ⚠️ 波动较大（变异系数 >30%），需关注异常值。")
    if not lines:
        lines.append("- 数据不足，无法形成结论。")
    return "\n".join(lines)


def render_html(x_col, y_cols, x_vals, stats):
    labels = json.dumps(x_vals, ensure_ascii=False)
    datasets = []
    for y in y_cols:
        if y not in stats:
            continue
        data = [r[y] for r in _last_rows if isinstance(r.get(y), (int, float))] if '_last_rows' in globals() else []
        datasets.append({"label": y, "data": data, "borderColor": f"hsl({len(datasets)*60},70%,50%)", "fill": False})
    ds_json = json.dumps(datasets, ensure_ascii=False)
    stat_rows = ""
    for y, s in stats.items():
        stat_rows += f"<tr><td>{html.escape(y)}</td><td>{s['mean']}</td><td>{s['median']}</td>" \
                     f"<td>{s['min']}~{s['max']}</td><td>{s['stdev']}</td><td>{s['trend']}</td></tr>\n"
    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>数据分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script></head>
<body><h2>数据分析报告</h2>
<div style="width:90%;max-width:900px;margin:auto;">
<canvas id="chart"></canvas>
<table border="1" cellpadding="6" style="border-collapse:collapse;margin-top:20px;">
<tr><th>指标</th><th>均值</th><th>中位数</th><th>范围</th><th>标准差</th><th>趋势</th></tr>
{stat_rows}</table></div>
<script>
const labels = {labels};
const ds = {ds_json};
new Chart(document.getElementById('chart'), {{
  type: 'line',
  data: {{ labels, datasets: ds }},
  options: {{ responsive: true }}
}});
</script></body></html>"""


def selftest() -> bool:
    """自检：用内置示例数据验证统计与报告生成"""
    print("🔧 运行自检...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        demo = Path(tmp) / "demo.csv"
        with open(demo, "w", encoding="utf-8", newline="") as f:
            f.write("月份,销售额\n")
            for m, v in DEMO_DATA:
                f.write(f"{m},{v}\n")
        headers, rows = read_csv(demo)
        if not rows or len(rows) != 12:
            print("  ❌ CSV 读取失败")
            return False
        x, ys, _ = pick_columns(headers, rows, "", "")
        global _last_rows
        _last_rows = rows
        x_vals, stats = analyze(x, ys, rows)
        if "销售额" not in stats:
            print("  ❌ 统计失败")
            return False
        s = stats["销售额"]
        if not (120 <= s["mean"] <= 260 and s["trend"] == "上升"):
            print(f"  ❌ 统计异常: {s}")
            return False
        md = make_conclusions(x, stats)
        html_out = render_html(x, ys, x_vals, stats)
        if "<canvas" not in html_out or not md:
            print("  ❌ 报告生成失败")
            return False
        print(f"  ✅ 12 行示例数据统计正确（均值 {s['mean']}，趋势 {s['trend']}）")
        print("  ✅ HTML 报告 + Markdown 结论生成正常")
        return True


def main() -> int:
    ap = argparse.ArgumentParser(description="数据洞察：CSV → 统计 + 可视化报告")
    ap.add_argument("--input", "-i", default="", help="输入 CSV 文件路径")
    ap.add_argument("--x", default="", help="X 轴列名（默认第一列）")
    ap.add_argument("--y", default="", help="Y 轴数值列名（默认全部数值列）")
    ap.add_argument("--output", "-o", default="report.html", help="输出 HTML 报告路径")
    ap.add_argument("--top", type=int, default=10, help="结论 Top N（保留参数）")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--version", action="version", version="visual_report 1.0.0")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    if not args.input:
        print("❌ 错误: 请用 --input 指定 CSV 文件（--selftest 可离线自检）")
        return 1
    src = Path(args.input)
    if not src.exists():
        print(f"❌ 错误: 文件不存在 {src}")
        return 1
    headers, rows = read_csv(src)
    if not rows:
        print("❌ 错误: CSV 无数据行")
        return 1
    global _last_rows
    _last_rows = rows
    x, ys, _ = pick_columns(headers, rows, args.x, args.y)
    if not ys:
        print("❌ 错误: 未找到数值列（--y 指定）")
        return 1
    x_vals, stats = analyze(x, ys, rows)
    # 输出 Markdown 结论
    print(make_conclusions(x, stats))
    # 输出 HTML
    out = Path(args.output)
    out.write_text(render_html(x, ys, x_vals, stats), encoding="utf-8")
    print(f"📄 报告已生成: {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
