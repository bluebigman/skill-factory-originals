#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

CanvasXpress 数据分析与可视化技能 - 独立实现脚本
本脚本基于功能规格文档进行 clean-room 重写，不复制任何既有代码。

功能概览：
1. 数据文件解析（CSV / TSV / JSON）
2. URL 数据抓取（标准库 urllib，带超时和重试）
3. 图表类型推荐（基于数据维度与字段类型的启发式规则）
4. 审计追踪生成（记录数据加载、转换、绘图每一步操作，支持持久化）
5. 批量图表输出（生成独立 HTML 文件或合并报告）
6. dry-run 模式（跳过实际绘图，仅生成审计）

命令行用法：
    python main.py --input data.csv --output chart.html
    python main.py --selftest
    python main.py --input data.csv --dry-run --audit audit.txt

错误码说明：
    E001 - 参数错误
    E002 - 文件读取失败
    E003 - 文件格式不支持
    E004 - 数据解析失败
    E005 - URL 访问失败
    E006 - 图表类型推荐失败
    E007 - HTML 生成失败
    E008 - 审计日志写入失败
    E009 - 数据转换失败
    E010 - 内部未知错误
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 错误处理工具
# ============================================================

class SkillError(Exception):
    """技能自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _fail(code: str, message: str) -> None:
    """抛出带错误码的异常。"""
    raise SkillError(code, message)


# ============================================================
# 审计追踪模块
# ============================================================

class AuditLogger:
    """
    审计追踪记录器。
    记录数据加载、转换、绘图等每一步操作，输出可追溯的审计日志。
    """

    def __init__(self) -> None:
        self._entries: List[Dict[str, str]] = []

    def log(self, action: str, detail: str = "") -> None:
        """记录一条审计日志。"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "action": action,
            "detail": detail,
        }
        self._entries.append(entry)

    def get_entries(self) -> List[Dict[str, str]]:
        """返回全部审计日志条目。"""
        return list(self._entries)

    def to_text(self) -> str:
        """将审计日志格式化为纯文本。"""
        lines = ["=== 审计追踪日志 ==="]
        for i, entry in enumerate(self._entries, 1):
            lines.append(
                f"{i}. [{entry['timestamp']}] {entry['action']}"
                + (f" - {entry['detail']}" if entry["detail"] else "")
            )
        return "\n".join(lines)

    def write_to_file(self, filepath: str) -> None:
        """将审计日志写入文件。"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.to_text())
        except OSError as exc:
            _fail("E008", f"审计日志写入失败: {exc}")


# ============================================================
# 数据解析模块
# ============================================================

def _detect_delimiter(head_line: str) -> str:
    """根据首行内容猜测分隔符。"""
    if "\t" in head_line:
        return "\t"
    if "," in head_line:
        return ","
    if ";" in head_line:
        return ";"
    return ","  # 默认逗号


def parse_csv_text(text: str) -> Tuple[List[str], List[List[str]]]:
    """
    解析 CSV/TSV 文本数据。
    返回 (表头列表, 数据行列表)。
    """
    if not text.strip():
        _fail("E004", "数据内容为空")
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        _fail("E004", "数据内容为空")
    delimiter = _detect_delimiter(lines[0])
    try:
        reader = csv.reader(lines, delimiter=delimiter)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error as exc:
        _fail("E004", f"CSV 解析失败: {exc}")
    if not rows:
        _fail("E004", "未解析到有效数据行")
    header = rows[0]
    data = rows[1:]
    return header, data


def parse_json_text(text: str) -> Tuple[List[str], List[List[str]]]:
    """
    解析 JSON 文本数据。
    支持两种结构：
    1. {"header": [...], "data": [[...], ...]}
    2. [{"col1": val1, "col2": val2}, ...]（自动提取表头）
    """
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        _fail("E004", f"JSON 解析失败: {exc}")

    if isinstance(obj, dict) and "header" in obj and "data" in obj:
        header = [str(h) for h in obj["header"]]
        data = [[str(c) for c in row] for row in obj["data"]]
        return header, data

    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        header = list(obj[0].keys())
        data = [[str(row.get(col, "")) for col in header] for row in obj]
        return header, data

    _fail("E004", "JSON 结构不符合预期（需包含 header 和 data 字段）")


def load_data_from_text(text: str, fmt: str) -> Tuple[List[str], List[List[str]], str]:
    """
    从文本加载数据，自动识别格式。
    返回 (表头, 数据行, 实际使用的格式)。
    """
    fmt = fmt.lower().lstrip(".")
    if fmt in ("csv", "tsv", "txt"):
        header, data = parse_csv_text(text)
        return header, data, "csv"
    if fmt == "json":
        header, data = parse_json_text(text)
        return header, data, "json"
    _fail("E003", f"不支持的格式: {fmt}")


def load_data_from_file(filepath: str) -> Tuple[List[str], List[List[str]], str]:
    """
    从本地文件加载数据。
    根据扩展名判断格式。
    """
    if not os.path.isfile(filepath):
        _fail("E002", f"文件不存在: {filepath}")
    ext = os.path.splitext(filepath)[1].lower().lstrip(".")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as exc:
        _fail("E002", f"文件读取失败: {exc}")
    return load_data_from_text(text, ext)


def _fetch_url_with_retry(url: str, timeout: int = 10, max_retries: int = 3) -> str:
    """
    带超时和指数退避重试的 URL 抓取。
    返回解码后的文本内容。
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                time.sleep(wait_time)
    _fail("E005", f"URL 访问失败（已重试 {max_retries} 次）: {last_exc}")


def load_data_from_url(url: str) -> Tuple[List[str], List[List[str]], str]:
    """
    从公开 URL 加载数据。
    自动判断格式。
    """
    text = _fetch_url_with_retry(url)
    # 根据 URL 后缀猜测格式，默认尝试 CSV
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in ("json",):
        fmt = "json"
    else:
        fmt = "csv"
    return load_data_from_text(text, fmt)


# ============================================================
# 图表类型推荐模块
# ============================================================

def recommend_chart_type(
    header: List[str], data: List[List[str]], goal: str = "auto"
) -> Dict[str, Any]:
    """
    根据数据维度、字段类型、分析目标，推荐合适的图表类型。
    返回包含推荐结果和理由的字典。
    """
    if not header or not data:
        _fail("E006", "数据为空，无法推荐图表类型")

    n_cols = len(header)
    n_rows = len(data)

    # 简单字段类型判断：尝试将第一列数据转为数值
    numeric_count = 0
    sample_size = min(50, len(data))
    for row in data[:sample_size]:
        try:
            float(row[0])
            numeric_count += 1
        except (ValueError, IndexError):
            pass
    first_col_numeric = numeric_count > max(1, sample_size * 0.5)

    # 启发式推荐规则
    if n_cols == 2 and first_col_numeric:
        chart_type = "scatter"
        reason = "两列数据且第一列为数值，适合散点图展示变量关系"
    elif n_cols == 2 and not first_col_numeric:
        chart_type = "bar"
        reason = "两列数据且第一列为类别，适合柱状图比较类别值"
    elif n_cols >= 3 and n_rows < 30:
        chart_type = "heatmap"
        reason = "多列且行数较少，适合热力图展示数据矩阵"
    elif n_cols >= 3 and n_rows >= 30:
        chart_type = "boxplot"
        reason = "多列且行数较多，适合箱线图展示分布"
    else:
        chart_type = "bar"
        reason = "默认推荐柱状图"

    # 根据分析目标微调
    if goal == "correlation" and n_cols >= 3:
        chart_type = "heatmap"
        reason = "分析相关性，推荐热力图"
    elif goal == "distribution" and n_rows >= 10:
        chart_type = "boxplot"
        reason = "分析分布，推荐箱线图"
    elif goal == "comparison":
        chart_type = "bar"
        reason = "进行对比，推荐柱状图"

    return {
        "chart_type": chart_type,
        "reason": reason,
        "dimensions": {"columns": n_cols, "rows": n_rows},
        "first_col_numeric": first_col_numeric,
    }


# ============================================================
# HTML 生成模块
# ============================================================

def generate_html(
    header: List[str],
    data: List[List[str]],
    chart_type: str,
    title: str = "CanvasXpress 可视化结果",
) -> str:
    """
    生成包含交互式图表的 HTML 内容。
    使用 CanvasXpress 的 CDN 库（静态交互：悬停提示、缩放、框选）。
    """
    try:
        # 将数据转为 JSON 字符串（供前端使用）
        json_data = json.dumps(data, ensure_ascii=False)
        json_header = json.dumps(header, ensure_ascii=False)

        # 根据图表类型调整配置
        if chart_type == "scatter":
            graph_config = "scatter"
        elif chart_type == "bar":
            graph_config = "bar"
        elif chart_type == "heatmap":
            graph_config = "heatmap"
        elif chart_type == "boxplot":
            graph_config = "boxplot"
        else:
            graph_config = "bar"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!-- CanvasXpress 核心库（CDN） -->
    <link rel="stylesheet" href="https://cdn.canvasxpress.org/css/canvasXpress.min.css" type="text/css"/>
    <script src="https://cdn.canvasxpress.org/js/canvasXpress.min.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f7fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        #chart {{ width: 100%; height: 500px; }}
        .info {{ color: #7f8c8d; font-size: 14px; margin-top: 15px; }}
        .badge {{ display: inline-block; background: #3498db; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div><span class="badge">{chart_type}</span> <span class="info">数据维度: {len(header)} 列 × {len(data)} 行</span></div>
        <div id="chart"></div>
        <div class="info">此图表由 CanvasXpress 技能生成（静态交互：悬停提示、缩放、框选）</div>
    </div>
    <script>
        // 初始化 CanvasXpress 图表
        var data = {json_data};
        var header = {json_header};
        var chart = new CanvasXpress({{
            renderTo: 'chart',
            data: {{
                y: data,
                x: header.map(function(_, i) {{ return 'X' + (i + 1); }}),
                type: '{graph_config}'
            }},
            config: {{
                title: '{title}',
                xAxis: {{ title: header[0] }},
                yAxis: {{ title: '值' }},
                theme: 'CanvasXpress',
                graphType: '{graph_config}'
            }}
        }});
    </script>
</body>
</html>"""
        return html
    except Exception as exc:
        _fail("E007", f"HTML 生成失败: {exc}")


def write_html_file(html: str, output_path: str) -> None:
    """将 HTML 内容写入文件。"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
    except OSError as exc:
        _fail("E007", f"HTML 文件写入失败: {exc}")


def generate_combined_report(
    sections: List[Tuple[str, str]]
) -> str:
    """
    生成合并报告 HTML（多图表）。
    sections: [(标题, HTML片段), ...]
    """
    parts = []
    for title, html_fragment in sections:
        parts.append(f"<h2>{title}</h2>")
        parts.append(html_fragment)
    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>CanvasXpress 合并报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f7fa; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .section {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1, h2 {{ color: #2c3e50; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>CanvasXpress 批量图表报告</h1>
        {body}
    </div>
</body>
</html>"""


# ============================================================
# 数据转换与处理模块
# ============================================================

def transpose_data(header: List[str], data: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
    """转置数据（行列互换）。"""
    if not data:
        _fail("E009", "数据为空，无法转置")
    max_len = max(len(row) for row in data)
    new_header = ["字段"] + [f"样本{i+1}" for i in range(len(data))]
    new_data = []
    for i in range(max_len):
        row = []
        for j in range(len(data)):
            row.append(data[j][i] if i < len(data[j]) else "")
        new_data.append(row)
    return new_header, new_data


def filter_rows(
    header: List[str], data: List[List[str]], column_idx: int, keyword: str
) -> Tuple[List[str], List[List[str]]]:
    """按关键字过滤行。"""
    if column_idx < 0 or column_idx >= len(header):
        _fail("E009", f"列索引 {column_idx} 超出范围")
    filtered = [row for row in data if row[column_idx] == keyword]
    return header
