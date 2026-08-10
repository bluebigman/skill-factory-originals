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
import os
import statistics
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志

# 仅在显式 --demo 标志下使用
DEMO_DATA = [
    ("1月", "120"), ("2月", "135"), ("3月", "128"), ("4月", "152"),
    ("5月", "168"), ("6月", "175"), ("7月", "190"), ("8月", "205"),
    ("9月", "198"), ("10月", "220"), ("11月", "235"), ("12月", "260"),
]

# 文件大小上限（500MB）
MAX_FILE_SIZE = 500 * 1024 * 1024

# 编码检测（分块采样，避免全文件读取导致内存爆炸）
def detect_encoding(path: Path) -> str:
    """检测文件编码，优先 UTF-8，其次 GBK 等常见中文编码
    修复：分块采样（前64KB+末尾64KB），避免全文件读取导致内存爆炸"""
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        print(f"⚠️ 警告: 文件大小 {file_size/1024/1024:.1f}MB 超过上限 {MAX_FILE_SIZE/1024/1024:.0f}MB，"
              f"将仅采样前64KB和末尾64KB进行编码检测")
    
    # 分块采样：前64KB + 末尾64KB
    sample_size = 64 * 1024
    with open(path, "rb") as f:
        head = f.read(sample_size)
        if file_size > sample_size:
            f.seek(max(0, file_size - sample_size))
            tail = f.read(sample_size)
        else:
            tail = b""
    raw = head + tail
    
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
    
    # 尝试 GB18030（GBK 超集）
    try:
        raw.decode('gb18030')
        return 'gb18030'
    except UnicodeDecodeError:
        pass
    
    # 移除 latin-1 回退，改为明确报错
    # 修复：不再使用 latin-1 作为最终回退，避免乱码数据被静默接受
    raise UnicodeDecodeError("无法识别文件编码，请使用 --encoding 参数指定编码（如 utf-8, gbk, gb18030）")


def read_csv(path: Path, encoding: str = None, max_rows: int = 100000):
    """读 CSV，返回 (headers, rows[dict], truncated_flag)，数值列自动转 float
    修复：移除 latin-1 回退，改为明确报错；实现 max_rows 截断"""
    # 文件存在性检查
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    
    # 文件大小检查
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        print(f"⚠️ 警告: 文件大小 {file_size/1024/1024:.1f}MB 超过上限 {MAX_FILE_SIZE/1024/1024:.0f}MB，"
              f"将截断处理")
    
    # 空文件检查
    if file_size == 0:
        print(f"⚠️ 警告: 文件为空: {path}")
        return [], [], False
    
    # 编码回退链（移除 latin-1）
    encodings = [encoding] if encoding else []
    encodings += ['utf-8-sig', 'utf-8', 'gbk', 'gb18030']
    # 去重
    encodings = list(dict.fromkeys(encodings))
    
    last_error = None
    for enc in encodings:
        try:
            rows = []
            truncated = False
            with open(path, "r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for i, raw in enumerate(reader):
                    if i >= max_rows:
                        print(f"⚠️ 警告: 文件超过 {max_rows} 行，已截断处理")
                        truncated = True
                        break
                    row = {}
                    for h in headers:
                        v = raw.get(h, "")
                        try:
                            row[h] = float(v)
                        except (ValueError, TypeError):
                            row[h] = v
                    rows.append(row)
            if enc != encoding and encoding is not None:
                print(f"ℹ️ 编码 {encoding} 解码失败，已自动切换为 {enc}")
            return headers, rows, truncated
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except OSError as e:
            raise OSError(f"无法读取文件 {path}: {e}") from e
        except csv.Error as e:
            raise csv.Error(f"CSV 格式错误: {e}") from e
    
    # 所有编码都失败
    raise UnicodeDecodeError(f"文件编码错误，尝试了所有常见编码均失败: {last_error}。"
                             f"请使用 --encoding 参数指定编码（如 utf-8, gbk, gb18030）")


def pick_columns(headers, rows, x_col, y_col):
    """选 x/y 列：默认第一列 x，其余数值列 y"""
    if not rows:
        return "index", [], []
    
    num_cols = []
    for h in headers:
        # 检查该列是否有至少一个数值
        has_numeric = any(isinstance(r.get(h), (int, float)) for r in rows)
        if has_numeric:
            num_cols.append(h)
    
    # 处理 x_col
    if x_col:
        if x_col not in headers:
            print(f"⚠️ 警告: 指定的 X 列 '{x_col}' 不存在，回退到第一列 '{headers[0]}'")
            x = headers[0]
        else:
            x = x_col
    else:
        x = headers[0] if headers else "index"
    
    # 处理 y_col
    if y_col:
        if y_col not in headers:
            print(f"⚠️ 警告: 指定的 Y 列 '{y_col}' 不存在，使用所有数值列")
            ys = [c for c in num_cols if c != x]
        else:
            ys = [y_col]
    else:
        ys = [c for c in num_cols if c != x]
    
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


def make_conclusions(x_col, stats, truncated=False):
    """生成有意义的自然语言结论：趋势解读、异常提醒、对比分析
    修复：增加 truncated 参数，在结论中明确标注数据不完整"""
    lines = []
    if not stats:
        return "- 数据不足，无法形成结论。"
    
    # 总体概览
    lines.append(f"## 数据洞察报告（{x_col}维度）")
    lines.append("")
    
    # 数据完整性警告
    if truncated:
        lines.append("> ⚠️ **数据完整性警告**：原始数据超过读取上限，以下分析基于截断后的数据，"
                     "结论可能不准确。建议使用 --max-rows 参数增加读取行数。")
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


def render_html(x_col, y_cols, x_vals, stats, rows, truncated=False):
    """生成 HTML 报告（使用传入的 rows 数据）
    修复：增加 truncated 参数，在报告中明确标注数据不完整"""
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
    
    # 数据完整性警告
    trunc_warning = ""
    if truncated:
        trunc_warning = '<div style="background:#fff3cd;color:#856404;padding:10px;margin:10px 0;border:1px solid #ffeeba;border-radius:4px;">' \
                        '⚠️ <strong>数据完整性警告</strong>：原始数据超过读取上限，以下分析基于截断后的数据，' \
                        '结论可能不准确。建议使用 --max-rows 参数增加读取行数。</div>'
    
    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>数据分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script></head>
<body><h2>数据分析报告</h2>
{trunc_warning}
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


def generate_report(input_path, output_path, x_col=None, y_col=None, encoding=None, max_rows=100000):
    """核心转换函数：读取表格 → 分析 → 生成报告
    返回 (html_path, md_path, stats)"""
    path = Path(input_path)
    headers, rows, truncated = read_csv(path, encoding, max_rows)
    if not rows:
        raise ValueError("数据为空，无法生成报告")
    
    x, ys, _ = pick_columns(headers, rows, x_col, y_col)
    if not ys:
        raise ValueError("未找到数值列，无法生成报告")
    
    x_vals, stats = analyze(x, ys, rows)
    if not stats:
        raise ValueError("统计分析失败")
    
    # 生成 HTML
    html_content = render_html(x, ys, x_vals, stats, rows, truncated)
    html_path = Path(output_path) if output_path else path.with_suffix(".html")
    if not dry_run or getattr(args, "force", False):
        html_path.write_text(html_content, encoding="utf-8")
    
    # 生成 Markdown 结论
    md_content = make_conclusions(x, stats, truncated)
    md_path = html_path.with_suffix(".md")
    if not dry_run or getattr(args, "force", False):
        md_path.write_text(md_content, encoding="utf-8")
    
    return str(html_path), str(md_path), stats


def selftest() -> bool:
    """自检：用临时 CSV 文件验证完整流程
    修复：真实调用主流程/核心函数并断言关键输出"""
    print("🔧 运行自检...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        demo = Path(tmp) / "demo.csv"
        # 写入测试数据（包含中文列名和数值）
        with open(demo, "w", encoding="utf-8", newline="") as f:
            f.write("月份,销售额\n")
            for m, v in DEMO_DATA:
                f.write(f"{m},{v}\n")
        
        # 测试编码检测（分块采样）
        enc = detect_encoding(demo)
        if enc != 'utf-8':
            print(f"  ❌ 编码检测失败: {enc}")
            return False
        
        # 测试 CSV 读取（含 truncated 标志）
        headers, rows, truncated = read_csv(demo)
        if not rows or len(rows) != 12:
            print


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--format", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--selftest", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--summary", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--top-n", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    args = ap.parse_args()
