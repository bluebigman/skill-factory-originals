#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data-visual-report — 数据洞察可视化报告工具（v2.0.0）

读 CSV/JSON 表格 → 统计计算（均值/中位数/极值/标准差/趋势/占比/TopN）→
生成自包含 HTML 报告（Chart.js 图表）+ Markdown 结论。
纯标准库（csv/json/statistics），零第三方依赖。

用法示例：
    python run.py data.csv -o report.html
    python run.py data.csv --summary
    python run.py data.csv --format md -o report.md
    python run.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import statistics
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 常量定义
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_ROWS = 10000  # 最大行数
SUPPORTED_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1"]
DEFAULT_TOP_N = 10
CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"


class SkillError(Exception):
    """技能运行时错误，带错误码"""
    def __init__(self, message: str, error_code: str = "E000"):
        super().__init__(message)
        self.error_code = error_code


def utc_now() -> str:
    """返回 UTC 当前时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def detect_encoding(path: Path) -> str:
    """检测文件编码，优先 UTF-8，其次 GBK 等常见中文编码
    
    分块采样（前64KB+末尾64KB），避免全文件读取导致内存爆炸。
    """
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise SkillError(
            f"文件过大（{file_size / 1024 / 1024:.1f}MB），超过 {MAX_FILE_SIZE / 1024 / 1024:.0f}MB 限制",
            "E101"
        )
    
    # 采样前64KB和末尾64KB
    sample_size = min(64 * 1024, file_size)
    with open(path, "rb") as f:
        head = f.read(sample_size)
        f.seek(max(0, file_size - sample_size))
        tail = f.read(sample_size)
    sample = head + tail
    
    for encoding in SUPPORTED_ENCODINGS:
        try:
            sample.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
    raise SkillError(
        f"无法识别文件编码（尝试了 {', '.join(SUPPORTED_ENCODINGS)}）",
        "E102"
    )


def read_csv(path: Path, encoding: str) -> List[Dict[str, Any]]:
    """流式读取 CSV 文件，返回字典列表"""
    data: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= MAX_ROWS:
                    print(f"⚠️ 警告: 数据超过 {MAX_ROWS} 行，已截断", file=sys.stderr)
                    break
                # 清理字段名和值
                clean_row = {}
                for k, v in row.items():
                    if k is None:
                        continue
                    clean_key = k.strip()
                    clean_val = v.strip() if v else ""
                    clean_row[clean_key] = clean_val
                data.append(clean_row)
    except csv.Error as e:
        raise SkillError(f"CSV 解析错误: {e}", "E103") from e
    return data


def read_json(path: Path, encoding: str) -> List[Dict[str, Any]]:
    """读取 JSON 文件，返回字典列表"""
    try:
        with open(path, "r", encoding=encoding) as f:
            content = f.read()
        parsed = json.loads(content)
        if isinstance(parsed, list):
            data = parsed
        elif isinstance(parsed, dict):
            # 尝试常见包装格式
            for key in ["data", "rows", "items", "records"]:
                if key in parsed and isinstance(parsed[key], list):
                    data = parsed[key]
                    break
            else:
                # 单条记录包装为列表
                data = [parsed]
        else:
            raise SkillError("JSON 根节点必须是数组或对象", "E104")
        
        if len(data) > MAX_ROWS:
            print(f"⚠️ 警告: 数据超过 {MAX_ROWS} 行，已截断", file=sys.stderr)
            data = data[:MAX_ROWS]
        return data
    except json.JSONDecodeError as e:
        raise SkillError(f"JSON 解析错误: {e}", "E105") from e


def read_table_data(file_path: str) -> List[Dict[str, Any]]:
    """读取表格数据（支持 CSV/JSON），返回字典列表"""
    path = Path(file_path)
    if not path.exists():
        raise SkillError(f"输入文件不存在: {file_path}", "E106")
    
    encoding = detect_encoding(path)
    suffix = path.suffix.lower()
    
    if suffix == ".csv":
        return read_csv(path, encoding)
    elif suffix == ".json":
        return read_json(path, encoding)
    else:
        raise SkillError(f"不支持的文件格式: {suffix}（仅支持 .csv/.json）", "E107")


def is_numeric(value: Any) -> bool:
    """判断值是否为数值类型"""
    if value is None or value == "":
        return False
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def to_float(value: Any) -> float:
    """转换为浮点数，失败返回 NaN"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return float("nan")


def detect_column_types(data: List[Dict[str, Any]]) -> Dict[str, str]:
    """检测每列的数据类型：numeric / categorical / datetime / text"""
    if not data:
        return {}
    
    col_types: Dict[str, str] = {}
    for col in data[0].keys():
        values = [row.get(col, "") for row in data if row.get(col, "") != ""]
        if not values:
            col_types[col] = "text"
            continue
        
        # 数值检测
        numeric_count = sum(1 for v in values if is_numeric(v))
        if numeric_count / len(values) > 0.8:
            col_types[col] = "numeric"
            continue
        
        # 日期检测
        date_count = 0
        for v in values[:100]:  # 采样前100个
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
                date_count += 1
            except (ValueError, AttributeError):
                pass
        if date_count / min(len(values), 100) > 0.8:
            col_types[col] = "datetime"
            continue
        
        # 分类检测
        unique_count = len(set(values))
        if unique_count <= 20:
            col_types[col] = "categorical"
        else:
            col_types[col] = "text"
    
    return col_types


def compute_statistics(data: List[Dict[str, Any]], numeric_cols: List[str]) -> Dict[str, Dict[str, float]]:
    """计算数值列的统计指标"""
    stats: Dict[str, Dict[str, float]] = {}
    for col in numeric_cols:
        values = [to_float(row.get(col)) for row in data if is_numeric(row.get(col))]
        if not values:
            continue
        
        col_stats = {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "missing": sum(1 for row in data if not is_numeric(row.get(col))),
        }
        stats[col] = col_stats
    return stats


def detect_trend(data: List[Dict[str, Any]], time_col: str, value_col: str) -> Dict[str, Any]:
    """检测时间序列趋势（线性回归斜率）"""
    x_vals: List[float] = []
    y_vals: List[float] = []
    
    for i, row in enumerate(data):
        if is_numeric(row.get(value_col)):
            x_vals.append(float(i))
            y_vals.append(to_float(row.get(value_col)))
    
    if len(x_vals) < 3:
        return {"trend": "insufficient_data", "slope": 0.0, "description": "数据量不足，无法判断趋势"}
    
    # 简单线性回归
    n = len(x_vals)
    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)
    
    if denominator == 0:
        slope = 0.0
    else:
        slope = numerator / denominator
    
    # 判断趋势
    if slope > 0.05:
        trend = "上升"
        desc = f"整体呈上升趋势（斜率 {slope:.3f}）"
    elif slope < -0.05:
        trend = "下降"
        desc = f"整体呈下降趋势（斜率 {slope:.3f}）"
    else:
        trend = "平稳"
        desc = f"整体趋势平稳（斜率 {slope:.3f}）"
    
    # 波动性检测
    if len(y_vals) >= 5:
        stdev = statistics.stdev(y_vals)
        mean = statistics.mean(y_vals)
        cv = stdev / mean if mean != 0 else 0
        if cv > 0.3:
            desc += "，波动较大"
        elif cv < 0.1:
            desc += "，波动较小"
    
    return {"trend": trend, "slope": slope, "description": desc}


def compute_top_n(data: List[Dict[str, Any]], value_col: str, n: int = DEFAULT_TOP_N) -> List[Dict[str, Any]]:
    """计算 TopN 排行"""
    # 按数值排序
    sorted_data = sorted(
        [row for row in data if is_numeric(row.get(value_col))],
        key=lambda r: to_float(r.get(value_col)),
        reverse=True
    )
    return sorted_data[:n]


def compute_distribution(data: List[Dict[str, Any]], cat_col: str, value_col: str) -> List[Dict[str, Any]]:
    """计算分类占比分布"""
    dist: Dict[str, float] = {}
    for row in data:
        cat = row.get(cat_col, "未知")
        val = to_float(row.get(value_col, 0))
        dist[cat] = dist.get(cat, 0) + val
    
    total = sum(dist.values())
    if total == 0:
        return []
    
    result = [
        {"category": cat, "value": val, "percentage": val / total * 100}
        for cat, val in sorted(dist.items(), key=lambda x: x[1], reverse=True)
    ]
    return result


def generate_conclusions(
    stats: Dict[str, Dict[str, float]],
    trends: Dict[str, Dict[str, Any]],
    top_n: Dict[str, List[Dict[str, Any]]],
    distributions: Dict[str, List[Dict[str, Any]]],
) -> List[str]:
    """生成分析结论"""
    conclusions: List[str] = []
    
    # 统计结论
    for col, s in stats.items():
        conclusions.append(
            f"{col}: 共 {s['count']} 条有效数据，均值 {s['mean']:.2f}，"
            f"中位数 {s['median']:.2f}，标准差 {s['stdev']:.2f}，"
            f"范围 [{s['min']:.2f}, {s['max']:.2f}]"
        )
    
    # 趋势结论
    for col, t in trends.items():
        conclusions.append(f"{col} 趋势: {t['description']}")
    
    # TopN 结论
    for col, items in top_n.items():
        if items:
            top_item = items[0]
            conclusions.append(f"{col} Top1: {top_item.get(list(top_item.keys())[0], '未知')} "
                             f"({top_item.get(col, '')})")
    
    # 分布结论
    for col, dist in distributions.items():
        if dist:
            top_cat = dist[0]
            conclusions.append(
                f"{col} 占比最高: {top_cat['category']} ({top_cat['percentage']:.1f}%)"
            )
    
    return conclusions


def generate_html_report(
    data: List[Dict[str, Any]],
    stats: Dict[str, Dict[str, float]],
    trends: Dict[str, Dict[str, Any]],
    top_n: Dict[str, List[Dict[str, Any]]],
    distributions: Dict[str, List[Dict[str, Any]]],
    conclusions: List[str],
    col_types: Dict[str, str],
) -> str:
    """生成自包含 HTML 报告"""
    # 准备图表数据
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    cat_cols = [c for c, t in col_types.items() if t == "categorical"]
    
    # 折线图数据（第一个数值列）
    line_chart_data = ""
    if numeric_cols:
        col = numeric_cols[0]
        labels = [str(i + 1) for i in range(len(data))]
        values = [to_float(row.get(col, 0)) for row in data]
        line_chart_data = f"""
        <canvas id="lineChart"></canvas>
        <script>
        new Chart(document.getElementById('lineChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: '{html.escape(col)}',
                    data: {json.dumps(values)},
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }}]
            }},
            options: {{ responsive: true }}
        }});
        </script>
        """
    
    # 饼图数据（第一个分类列）
    pie_chart_data = ""
    if cat_cols and distributions.get(cat_cols[0]):
        col = cat_cols[0]
        dist = distributions[col]
        labels = [d["category"] for d in dist[:10]]
        values = [d["value"] for d in dist[:10]]
        pie_chart_data = f"""
        <canvas id="pieChart"></canvas>
        <script>
        new Chart(document.getElementById('pieChart'), {{
            type: 'pie',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    data: {json.dumps(values)},
                    backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                                     '#FF9F40', '#FF6384', '#C9CBFF', '#FF6384', '#36A2EB']
                }}]
            }},
            options: {{ responsive: true }}
        }});
        </script>
        """
    
    # 统计表格
    stats_table = ""
    if stats:
        rows = []
        for col, s in stats.items():
            rows.append(
                f"<tr><td>{html.escape(col)}</td><td>{s['count']}</td>"
                f"<td>{s['mean']:.2f}</td><td>{s['median']:.2f}</td>"
                f"<td>{s['stdev']:.2f}</td><td>{s['min']:.2f}</td>"
                f"<td>{s['max']:.2f}</td><td>{s['missing']}</td></tr>"
            )
        stats_table = f"""
        <h2>统计摘要</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse">
            <tr><th>字段</th><th>计数</th><th>均值</th><th>中位数</th>
                <th>标准差</th><th>最小值</th><th>最大值</th><th>缺失值</th></tr>
            {''.join(rows)}
        </table>
        """
    
    # TopN 表格
    topn_table = ""
    if top_n:
        sections = []
        for col, items in top_n.items():
            if not items:
                continue
            rows = []
            for i, item in enumerate(items, 1):
                label_col = [c for c in item.keys() if c != col][0] if len(item) > 1 else "项目"
                label = item.get(label_col, "未知")
                value = item.get(col, "")
                rows.append(f"<tr><td>{i}</td><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>")
            sections.append(f"""
            <h3>Top {len(items)}: {html.escape(col)}</h3>
            <table border="1" cellpadding="8" style="border-collapse:collapse">
                <tr><th>排名</th><th>项目</th><th>数值</th></tr>
                {''.join(rows)}
            </table>
            """)
        topn_table = f"<h2>TopN 排行</h2>{''.join(sections)}"
    
    # 结论
    conclusions_html = ""
    if conclusions:
        items = "".join(f"<li>{html.escape(c)}</li>" for c in conclusions)
        conclusions_html = f"<h2>分析结论</h2><ul>{items}</ul>"
    
    # 数据预览
    preview_rows = []
    for row in data[:10]:
        cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in row.values())
        preview_rows.append(f"<tr>{cells}</tr>")
    headers = "".join(f"<th>{html.escape(str(k))}</th>" for k in data[0].keys()) if data else ""
    preview_table = f"""
    <h2>数据预览（前 10 行）</h2>
    <table border="1" cellpadding="8" style="border-collapse:collapse">
        <tr>{headers}</tr>
        {''.join(preview_rows)}
    </table>
    """
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据洞察报告</title>
    <script src="{CHART_JS_CDN}"></script>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ width: 100%; margin-bottom: 20px; }}
        th {{ background-color: #f2f2f2; }}
        .chart-container {{ max-width: 800px; margin: 20px auto; }}
    </style>
</head>
<body>
    <h1>数据洞察报告</h1>
    <p>生成时间: {utc_now()}</p>
    <p>数据行数: {len(data)}</p>
    
    {stats_table}
    
    <div class="chart-container">
        {line_chart_data}
    </div>
    
    <div class="chart-container">
        {pie_chart_data}
    </div>
    
    {topn_table}
    {conclusions_html}
    {preview_table}
</body>
</html>"""
    
    return html_content


def generate_markdown_report(
    data: List[Dict[str, Any]],
    stats: Dict[str, Dict[str, float]],
    trends: Dict[str, Dict[str, Any]],
    top_n: Dict[str, List[Dict[str, Any]]],
    distributions: Dict[str, List[Dict[str, Any]]],
    conclusions: List[str],
    col_types: Dict[str, str],
) -> str:
    """生成 Markdown 格式报告"""
    lines = [
        "# 数据洞察报告",
        "",
        f"- 生成时间: {utc_now()}",
        f"- 数据行数: {len(data)}",
        "",
    ]
    
    # 统计摘要
    if stats:
        lines.append("## 统计摘要")
        lines.append("")
        lines.append("| 字段 | 计数 | 均值 | 中位数 | 标准差 | 最小值 | 最大值 | 缺失值 |")
        lines.append("|------|------|------|--------|--------|--------|--------|--------|")
        for col, s in stats.items():
            lines.append(
                f"| {col} | {s['count']} | {s['mean']:.2f} | {s['median']:.2f} | "
                f"{s['stdev']:.2f} | {s['min']:.2f} | {s['max']:.2f} | {s['missing']} |"
            )
        lines.append("")
    
    # 趋势
    if trends:
        lines.append("## 趋势分析")
        lines.append("")
        for col, t in trends.items():
            lines.append(f"- **{col}**: {t['description']}")
        lines.append("")
    
    # TopN
    if top_n:
        lines.append("## TopN 排行")
        lines.append("")
        for col, items in top_n.items():
            if not items:
                continue
            lines.append(f"### {col}")
            lines.append("")
            lines.append("| 排名 | 项目 | 数值 |")
            lines.append("|------|------|------|")
            for i, item in enumerate(items, 1):
                label_col = [c for c in item.keys() if c != col][0] if len(item) > 1 else "项目"
                label = item.get(label_col, "未知")
                value = item.get(col, "")
                lines.append(f"| {i} | {label} | {value} |")
            lines.append("")
    
    # 分布
    if distributions:
        lines.append("## 占比分布")
        lines.append("")
        for col, dist in distributions.items():
            if not dist:
                continue
            lines.append(f"### {col}")
            lines.append("")
            lines.append("| 类别 | 数值 | 占比 |")
            lines.append("|------|------|------|")
            for d in dist[:10]:
                lines.append(f"| {d['category']} | {d['value']:.2f} | {d['percentage']:.1f}% |")
            lines.append("")
    
    # 结论
    if conclusions:
        lines.append("## 分析结论")
        lines.append("")
        for c in conclusions:
            lines.append(f"- {c}")
        lines.append("")
    
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    """原子化写入文件（先写临时文件再重命名）"""
    temp_fd, temp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, path)
    except Exception:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def save(path: Path, data: str, dry_run: bool = False) -> bool:
    """保存报告文件，支持 dry-run 模式"""
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


def run_analysis(
    data: List[Dict[str, Any]],
    top_n: int = DEFAULT_TOP_N,
    verbose: bool = False,
) -> Dict[str, Any]:
    """执行完整分析流程"""
    if not data:
        raise SkillError("输入数据为空", "E201")
    
    if verbose:
        print(f"📊 数据加载完成: {len(data)} 行", file=sys.stderr)
    
    # 检测列类型
    col_types = detect_column_types(data)
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    cat_cols = [c for c, t in col_types.items() if t == "categorical"]
    datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
    
    if not numeric_cols:
        raise SkillError("至少需要 1 列数值字段", "E202")
    
    if verbose:
        print(f"🔍 检测到数值列: {numeric_cols}", file=sys.stderr)
        print(f"🔍 检测到分类列: {cat_cols}", file=sys.stderr)
    
    # 计算统计指标
    stats = compute_statistics(data, numeric_cols)
    
    # 趋势分析（使用第一个时间列和第一个数值列）
    trends: Dict[str, Dict[str, Any]] = {}
    if datetime_cols and numeric_cols:
        time_col = datetime_cols[0]
        value_col = numeric_cols[0]
        trends[value_col] = detect_trend(data, time_col, value_col)
    
    # TopN 排行
    top_n_result: Dict[str, List[Dict[str, Any]]] = {}
    for col in numeric_cols:
        top_n_result[col] = compute_top_n(data, col, top_n)
    
    # 占比分布
    distributions: Dict[str, List[Dict[str, Any]]] = {}
    for col in cat_cols:
        if numeric_cols:
            distributions[col] = compute_distribution(data, col, numeric_cols[0])
    
    # 生成结论
    conclusions = generate_conclusions(stats, trends, top_n_result, distributions)
    
    return {
        "col_types": col_types,
        "stats": stats,
        "trends": trends,
        "top_n": top_n_result,
        "distributions": distributions,
        "conclusions": conclusions,
        "row_count": len(data),
    }


def print_summary(result: Dict[str, Any]) -> None:
    """打印统计摘要到终端"""
    print("\n" + "=" * 60)
    print("📊 数据洞察摘要")
    print("=" * 60)
    print(f"数据行数: {result['row_count']}")
    
    if result["stats"]:
        print("\n📈 统计指标:")
        for col, s in result["stats"].items():
            print(f"  {col}:")
            print(f"    计数: {s['count']}, 均值: {s['mean']:.2f}, 中位数: {s['median']:.2f}")
            print(f"    标准差: {s['stdev']:.2f}, 范围: [{s['min']:.2f}, {s['max']:.2f}]")
            if s["missing"] > 0:
                print(f"    ⚠️ 缺失值: {s['missing']}")
    
    if result["trends"]:
        print("\n📉 趋势分析:")
        for col, t in result["trends"].items():
            print(f"  {col}: {t['description']}")
    
    if result["top_n"]:
        print("\n🏆 TopN 排行:")
        for col, items in result["top_n"].items():
            if items:
                label_col = [c for c in items[0].keys() if c != col][0] if len(items[0]) > 1 else "项目"
                print(f"  {col} Top1: {items[0].get(label_col, '未知')} = {items[0].get(col, '')}")
    
    if result["conclusions"]:
        print("\n💡 分析结论:")
        for c in result["conclusions"]:
            print(f"  - {c}")
    
    print("\n" + "=" * 60)


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("🔍 运行自检...")
    failures = 0
    
    # 测试数据
    test_data = [
        {"月份": "1月", "销售额": "120", "地区": "华东"},
        {"月份": "2月", "销售额": "135", "地区": "华东"},
        {"月份": "3月", "销售额": "128", "地区": "华北"},
        {"月份": "4月", "销售额": "152", "地区": "华北"},
        {"月份": "5月", "销售额": "168", "地区": "华南"},
        {"月份": "6月", "销售额": "175", "地区": "华南"},
    ]
    
    # 测试1: 列类型检测
    print("  测试1: 列类型检测...")
    col_types = detect_column_types(test_data)
    assert col_types.get("销售额") == "numeric", f"销售额应为 numeric, 实际: {col_types.get('销售额')}"
    assert col_types.get("月份") in ("categorical", "text"), f"月份应为 categorical/text, 实际: {col_types.get('月份')}"
    print("    ✅ 通过")
    
    # 测试2: 统计计算
    print("  测试2: 统计计算...")
    stats = compute_statistics(test_data, ["销售额"])
    assert "销售额" in stats, "统计结果应包含销售额"
    assert stats["销售额"]["count"] == 6, f"计数应为 6, 实际: {stats['销售额']['count']}"
    assert 100 < stats["销售额"]["mean"] < 200, f"均值应在 100-200 之间, 实际: {stats['销售额']['mean']}"
    print("    ✅ 通过")
    
    # 测试3: TopN
    print("  测试3: TopN 排行...")
    top3 = compute_top_n(test_data, "销售额", 3)
    assert len(top3) == 3, f"Top3 应返回 3 条, 实际: {len(top3)}"
    assert to_float(top3[0]["销售额"]) == 175, f"Top1 应为 175, 实际: {top3[0]['销售额']}"
    print("    ✅ 通过")
    
    # 测试4: 分布计算
    print("  测试4: 占比分布...")
    dist = compute_distribution(test_data, "地区", "销售额")
    assert len(dist) == 3, f"应有 3 个地区, 实际: {len(dist)}"
    total_pct = sum(d["percentage"] for d in dist)
    assert abs(total_pct - 100) < 0.01, f"占比总和应为 100%, 实际: {total_pct:.2f}%"
    print("    ✅ 通过")
    
    # 测试5: 完整分析流程
    print("  测试5: 完整分析流程...")
    result = run_analysis(test_data, top_n=3)
    assert result["row_count"] == 6, f"行数应为 6, 实际: {result['row_count']}"
    assert "销售额" in result["stats"], "统计应包含销售额"
    assert len(result["conclusions"]) > 0, "应生成结论"
    print("    ✅ 通过")
    
    # 测试6: 报告生成
    print("  测试6: 报告生成...")
    html_report = generate_html_report(
        test_data, result["stats"], result["trends"],
        result["top_n"], result["distributions"],
        result["conclusions"], result["col_types"]
    )
    assert "<!DOCTYPE html>" in html_report, "HTML 报告应包含 DOCTYPE"
    assert "Chart" in html_report, "HTML 报告应包含 Chart.js"
    print("    ✅ 通过")
    
    md_report = generate_markdown_report(
        test_data, result["stats"], result["trends"],
        result["top_n"], result["distributions"],
        result["conclusions"], result["col_types"]
    )
    assert "# 数据洞察报告" in md_report, "Markdown 报告应包含标题"
    print("    ✅ 通过")
    
    # 测试7: 空数据错误处理
    print("  测试7: 空数据错误处理...")
    try:
        run_analysis([])
        print("    ❌ 失败: 空数据应抛出异常")
        failures += 1
    except SkillError as e:
        assert e.error_code == "E201", f"错误码应为 E201, 实际: {e.error_code}"
        print("    ✅ 通过")
    
    # 测试8: 文件读取
    print("  测试8: 文件读取...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("月份,销售额,地区\n1月,120,华东\n2月,135,华北\n")
        temp_path = f.name
    try:
        data = read_table_data(temp_path)
        assert len(data) == 2, f"应读取 2 行, 实际: {len(data)}"
        print("    ✅ 通过")
    finally:
        os.unlink(temp_path)
    
    # 测试9: 编码检测
    print("  测试9: 编码检测...")
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        f.write("名称,数值\n测试,123\n".encode("gbk"))
        temp_path = f.name
    try:
        encoding = detect_encoding(Path(temp_path))
        assert encoding in ("gbk", "gb18030"), f"应检测为 gbk/gb18030, 实际: {encoding}"
        print("    ✅ 通过")
    finally:
        os.unlink(temp_path)
    
    # 测试10: dry-run 不写盘
    print("  测试10: dry-run 不写盘...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("月份,销售额\n1月,120\n2月,135\n")
        temp_path = f.name
    try:
        output_path = Path(tempfile.mkdtemp()) / "test_report.html"
        # 模拟 dry-run
        result = run_analysis(read_table_data(temp_path))
        html_report = generate_html_report(
            result["data"] if "data" in result else read_table_data(temp_path),
            result["stats"], result["trends"],
            result["top_n"], result["distributions"],
            result["conclusions"], result["col_types"]
        )
        # 使用 save 函数测试 dry-run
        saved = save(output_path, html_report, dry_run=True)
        assert not saved, "dry-run 不应返回 True"
        assert not output_path.exists(), "dry-run 不应写文件"
        print("    ✅ 通过")
    finally:
        os.unlink(temp_path)
    
    # 测试11: save 函数实际写入
    print("  测试11: save 函数实际写入...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("月份,销售额\n1月,120\n2月,135\n")
        temp_path = f.name
    try:
        output_path = Path(tempfile.mkdtemp()) / "test_report.html"
        result = run_analysis(read_table_data(temp_path))
        html_report = generate_html_report(
            result["data"] if "data" in result else read_table_data(temp_path),
            result["stats"], result["trends"],
            result["top_n"], result["distributions"],
            result["conclusions"], result["col_types"]
        )
        saved = save(output_path, html_report, dry_run=False)
        assert saved, "save 应返回 True"
        assert output_path.exists(), "save 应写入文件"
        print("    ✅ 通过")
    finally:
        os.unlink(temp_path)
    
    if failures == 0:
        print("\n🎉 全部自检通过!")
        return 0
    else:
        print(f"\n❌ {failures} 项自检失败")
        return 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="数据洞察可视化报告工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python run.py data.csv -o report.html    生成 HTML 报告
  python run.py data.csv --summary         查看统计摘要
  python run.py data.csv --format md       生成 Markdown 报告
  python run.py --selftest                 运行自检
        """
    )
    parser.add_argument("--input", nargs="?", help="输入 CSV/JSON 文件路径")
    parser.add_argument("-o", "--output", help="输出报告文件路径")
    parser.add_argument("--format", choices=["html", "md"], default="html", help="输出格式")
    parser.add_argument("--summary", action="store_true", help="仅打印统计摘要")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help=f"TopN 数量（默认 {DEFAULT_TOP_N}）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理信息")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    if args.selftest:
        return run_selftest()
    
    if not args.input:
        parser.print_help()
        return 1
    
    try:
        # 读取数据
        data = read_table_data(args.input)
        
        # 执行分析
        result = run_analysis(data, top_n=args.top_n, verbose=args.verbose)
        
        # 打印摘要
        if args.summary or args.verbose:
            print_summary(result)
        
        # 生成报告
        if args.output:
            if args.format == "html":
                report = generate_html_report(
                    data, result["stats"], result["trends"],
                    result["top_n"], result["distributions"],
                    result["conclusions"], result["col_types"]
                )
            else:
                report = generate_markdown_report(
                    data, result["stats"], result["trends"],
                    result["top_n"], result["distributions"],
                    result["conclusions"], result["col_types"]
                )
            
            output_path = Path(args.output)
            # 确保父目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用 save 函数统一处理 dry-run 和实际写入
            saved = save(output_path, report, dry_run=args.dry_run)
            
            if args.verbose and args.dry_run:
                # 打印详细修改明细（R6 可解释输出）
                print(f"[明细] 报告文件: {output_path}")
                print(f"[明细] 报告格式: {args.format}")
                print(f"[明细] 报告大小: {len(report)} 字节")
                print(f"[明细] 数据行数: {len(data)}")
                print(f"[明细] 统计字段: {list(result['stats'].keys())}")
                print(f"[明细] 趋势字段: {list(result['trends'].keys())}")
                print(f"[明细] TopN 字段: {list(result['top_n'].keys())}")
                print(f"[明细] 分布字段: {list(result['distributions'].keys())}")
                print(f"[汇总] changed=1 项，skipped=0 项")
            elif args.verbose and not args.dry_run:
                print(f"[明细] 报告文件: {output_path}")
                print(f"[明细] 报告格式: {args.format}")
                print(f"[明细] 报告大小: {len(report)} 字节")
                print(f"[明细] 数据行数: {len(data)}")
                print(f"[明细] 统计字段: {list(result['stats'].keys())}")
                print(f"[明细] 趋势字段: {list(result['trends'].keys())}")
                print(f"[明细] TopN 字段: {list(result['top_n'].keys())}")
                print(f"[明细] 分布字段: {list(result['distributions'].keys())}")
                print(f"[汇总] changed=1 项，skipped=0 项")
            
            if not saved and not args.dry_run:
                print(f"✅ 报告已生成: {output_path}")
        elif not args.summary:
            print_summary(result)
            print("💡 提示: 使用 -o 参数指定输出文件路径")
        
        return 0
    
    except SkillError as e:
        print(f"❌ 错误 [{e.error_code}]: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 未预期错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
