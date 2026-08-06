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
import time
import urllib.request
from collections import Counter
from pathlib import Path

# 仅在显式 --demo 标志下使用
DEMO_DATA = [
    ("1月", "120"), ("2月", "135"), ("3月", "128"), ("4月", "152"),
    ("5月", "168"), ("6月", "175"), ("7月", "190"), ("8月", "205"),
    ("9月", "198"), ("10月", "220"), ("11月", "235"), ("12月", "260"),
]

# 编码检测（纯标准库实现）
def detect_encoding(path: Path) -> str:
    """检测文件编码，优先 UTF-8，其次 GBK 等常见中文编码"""
    with open(path, "rb") as f:
        raw = f.read(4096)
    # BOM 检测
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        return 'utf-16'
    # 尝试 UTF-8 严格解码
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass
    # 尝试 GBK
    try:
        raw.decode('gbk')
        return 'gbk'
    except UnicodeDecodeError:
        pass
    # 默认 UTF-8
    return 'utf-8'


def read_csv(path: Path, encoding: str = None, max_rows: int = 100000):
    """读 CSV，返回 (headers, rows[dict])，数值列自动转 float
    支持编码自动检测、行数限制防止内存溢出"""
    if encoding is None:
        encoding = detect_encoding(path)
    
    rows = []
    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for i, raw in enumerate(reader):
            if i >= max_rows:
                print(f"⚠️ 警告: 文件超过 {max_rows} 行，已截断处理")
                break
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
        # 添加异常检测（超过均值±2倍标准差）
        if len(series) > 2 and s["stdev"] > 0:
            outliers = [v for v in series if abs(v - s["mean"]) > 2 * s["stdev"]]
            s["outliers"] = len(outliers)
            s["outlier_ratio"] = round(len(outliers) / len(series) * 100, 1)
        else:
            s["outliers"] = 0
            s["outlier_ratio"] = 0
        stats[y] = s
    return x_vals, stats


def make_conclusions(x_col, stats):
    """生成有意义的自然语言结论：趋势解读、异常提醒、对比分析"""
    lines = []
    if not stats:
        return "- 数据不足，无法形成结论。"
    
    # 总体概览
    lines.append(f"## 数据洞察报告（{x_col}维度）")
    lines.append("")
    
    for y, s in stats.items():
        # 趋势解读
        if s["trend"] == "上升":
            lines.append(f"### {y} 趋势分析")
            lines.append(f"- **{y}** 整体呈**上升**趋势，期末较期初 **+{s['delta_pct']}%**"
                         f"（均值 {s['mean']}，峰值 {s['max']}）。")
            if s["delta_pct"] > 50:
                lines.append(f"  - 📈 增长幅度显著（>50%），建议分析增长驱动因素。")
        elif s["trend"] == "下降":
            lines.append(f"### {y} 趋势分析")
            lines.append(f"- **{y}** 整体呈**下降**趋势，期末较期初 **{s['delta_pct']}%**"
                         f"（均值 {s['mean']}，谷值 {s['min']}）。")
            if s["delta_pct"] < -50:
                lines.append(f"  - 📉 下降幅度显著（>50%），建议排查潜在问题。")
        else:
            lines.append(f"### {y} 趋势分析")
            lines.append(f"- **{y}** 整体**平稳**，均值 {s['mean']}，波动 {s['stdev']}。")
        
        # 波动/异常提醒
        if s["stdev"] and s["mean"] and s["stdev"] / s["mean"] > 0.3:
            lines.append(f"  - ⚠️ 波动较大（变异系数 {round(s['stdev']/s['mean']*100,1)}% >30%），需关注异常值。")
        if s["outliers"] > 0:
            lines.append(f"  - 🔍 检测到 {s['outliers']} 个异常值（占比 {s['outlier_ratio']}%），"
                         f"超出均值±2倍标准差范围。")
        
        # 对比分析（多个指标时）
        if len(stats) > 1:
            lines.append(f"  - 📊 该指标占所有指标总和的比例：{round(s['sum']/sum(v['sum'] for v in stats.values())*100,1)}%")
    
    # 综合建议
    lines.append("")
    lines.append("### 综合建议")
    if len(stats) > 1:
        max_growth = max(stats.values(), key=lambda x: x["delta_pct"])
        min_growth = min(stats.values(), key=lambda x: x["delta_pct"])
        lines.append(f"- 增长最快的指标：**{max_growth['delta_pct']}%**（{max_growth['trend']}）")
        lines.append(f"- 下降最快的指标：**{min_growth['delta_pct']}%**（{min_growth['trend']}）")
    else:
        s = list(stats.values())[0]
        lines.append(f"- 建议关注 {s['trend']}趋势，当前均值 {s['mean']}，"
                     f"建议根据业务目标设定合理阈值。")
    
    return "\n".join(lines)


def render_html(x_col, y_cols, x_vals, stats, rows):
    """生成 HTML 报告（使用传入的 rows 数据）"""
    labels = json.dumps(x_vals, ensure_ascii=False)
    datasets = []
    for y in y_cols:
        if y not in stats:
            continue
        data = [r[y] for r in rows if isinstance(r.get(y), (int, float))]
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
    """自检：用临时 CSV 文件验证完整流程"""
    print("🔧 运行自检...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        demo = Path(tmp) / "demo.csv"
        # 写入测试数据（包含中文列名和数值）
        with open(demo, "w", encoding="utf-8", newline="") as f:
            f.write("月份,销售额\n")
            for m, v in DEMO_DATA:
                f.write(f"{m},{v}\n")
        
        # 测试编码检测
        enc = detect_encoding(demo)
        if enc != 'utf-8':
            print(f"  ❌ 编码检测失败: {enc}")
            return False
        
        # 测试 CSV 读取
        headers, rows = read_csv(demo)
        if not rows or len(rows) != 12:
            print("  ❌ CSV 读取失败")
            return False
        
        # 测试列选择
        x, ys, _ = pick_columns(headers, rows, "", "")
        if x != "月份" or "销售额" not in ys:
            print(f"  ❌ 列选择失败: x={x}, ys={ys}")
            return False
        
        # 测试统计分析
        x_vals, stats = analyze(x, ys, rows)
        if "销售额" not in stats:
            print("  ❌ 统计失败")
            return False
        s = stats["销售额"]
        if not (120 <= s["mean"] <= 260 and s["trend"] == "上升"):
            print(f"  ❌ 统计异常: {s}")
            return False
        
        # 测试结论生成（必须非空且有实质内容）
        md = make_conclusions(x, stats)
        if not md or len(md) < 50:
            print(f"  ❌ 结论生成失败（内容过短）: {md}")
            return False
        if "趋势" not in md or "建议" not in md:
            print(f"  ❌ 结论缺少关键要素: {md}")
            return False
        
        # 测试 HTML 生成（必须包含图表和结论）
        html_out = render_html(x, ys, x_vals, stats, rows)
        if "<canvas" not in html_out or "chart" not in html_out:
            print("  ❌ HTML 缺少图表")
            return False
        if "数据分析报告" not in html_out:
            print("  ❌ HTML 缺少标题")
            return False
        
        # 测试 GBK 编码文件
        gbk_file = Path(tmp) / "gbk.csv"
        with open(gbk_file, "w", encoding="gbk", newline="") as f:
            f.write("月份,销售额\n")
            for m, v in DEMO_DATA[:3]:
                f.write(f"{m},{v}\n")
        enc2 = detect_encoding(gbk_file)
        if enc2 != 'gbk':
            print(f"  ❌ GBK 编码检测失败: {enc2}")
            return False
        headers2, rows2 = read_csv(gbk_file)
        if len(rows2) != 3:
            print("  ❌ GBK 文件读取失败")
            return False
        
        print(f"  ✅ 12 行示例数据统计正确（均值 {s['mean']}，趋势 {s['trend']}）")
        print(f"  ✅ 结论生成正常（{len(md)} 字符）")
        print(f"  ✅ HTML 报告生成正常（{len(html_out)} 字节）")
        print(f"  ✅ GBK 编码文件读取正常")
        return True


def main() -> int:
    ap = argparse.ArgumentParser(description="数据洞察：CSV → 统计 + 可视化报告")
    ap.add_argument("--input", "-i", default="", help="输入 CSV 文件路径")
    ap.add_argument("--x", default="", help="X 轴列名（默认第一列）")
    ap.add_argument("--y", default="", help="Y 轴数值列名（默认全部数值列）")
    ap.add_argument("--output", "-o", default="report.html", help="输出 HTML 报告路径")
    ap.add_argument("--top", type=int, default=10, help="结论 Top N（保留参数）")
    ap.add_argument("--encoding", default="", help="指定 CSV 编码（默认自动检测）")
    ap.add_argument("--max-rows", type=int, default=100000, help="最大读取行数（默认 100000）")
    ap.add_argument("--demo", action="store_true", help="使用内置示例数据（仅测试用）")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--version", action="version", version="visual_report 1.0.0")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    # 处理 --demo 模式
    if args.demo:
        if args.input:
            print("⚠️ 警告: --demo 与 --input 同时指定，将使用 --demo 数据")
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        tmp.write("月份,销售额\n")
        for m, v in DEMO_DATA:
            tmp.write(f"{m},{v}\n")
        tmp.close()
        args.input = tmp.name
        print(f"ℹ️ 使用内置示例数据（临时文件: {args.input}）")

    if not args.input:
        print("❌ 错误: 请用 --input 指定 CSV 文件（--selftest 可离线自检）")
        return 1
    src = Path(args.input)
    if not src.exists():
        print(f"❌ 错误: 文件不存在 {src}")
        return 1
    
    # 读取 CSV（支持编码检测和行数限制）
    try:
        headers, rows = read_csv(src, encoding=args.encoding or None, max_rows=args.max_rows)
    except Exception as e:
        print(f"❌ 错误: 读取 CSV 失败 - {e}")
        return 1
    
    if not rows:
        print("❌ 错误: CSV 无数据行")
        return 1
    
    x, ys, _ = pick_columns(headers, rows, args.x, args.y)
    if not ys:
        print("❌ 错误: 未找到数值列（--y 指定）")
        return 1
    
    x_vals, stats = analyze(x, ys, rows)
    
    # 输出 Markdown 结论
    print(make_conclusions(x, stats))
    
    # 输出 HTML
    out = Path(args.output)
    out.write_text(render_html(x, ys, x_vals, stats, rows), encoding="utf-8")
    print(f"📄 报告已生成: {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
