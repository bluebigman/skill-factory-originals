#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chart-pro: 数据可视化图表生成与美化工具

从表格数据自动生成专业图表，支持多类型、自定义样式与高清导出。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例:
    python main.py --data "月份,销量\\n1月,100\\n2月,150" --type bar --title "月度销量"
    python main.py --file data.csv --type line --dry-run
    python main.py --selftest
"""

import argparse
import csv
import io
import json
import math
import os
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# 尝试导入第三方库，若不可用则降级为文本模式
try:
    import matplotlib

    matplotlib.use("Agg")  # 无界面后端，适合脚本生成
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "数据格式无法解析，请提供 CSV/JSON 或表格文本",
    "E002": "未检测到有效数据行，数据为空",
    "E003": "各行数据列数不一致，请检查",
    "E004": "暂不支持该图表类型，可选：bar/line/pie/scatter/radar",
    "E005": "找不到指定文件，请确认路径",
    "E006": "数据超过 10,000 行，建议抽样或聚合",
    "E007": "未找到数值列，无法生成图表",
    "E008": "输入参数校验失败",
    "E009": "图表生成失败",
    "E010": "内部未知错误",
}

# 配色方案
COLOR_SCHEMES = {
    "商务蓝": ["#2E5BFF", "#4A7BFF", "#6B9AFF", "#8DB8FF", "#B0D0FF"],
    "暖阳橙": ["#FF8C00", "#FFA333", "#FFB966", "#FFD199", "#FFE8CC"],
    "森林绿": ["#2E8B57", "#3CB371", "#66CDAA", "#90EE90", "#C1E1C1"],
    "莫兰迪灰": ["#8B8B8B", "#A9A9A9", "#C0C0C0", "#D3D3D3", "#E8E8E8"],
    "马卡龙": ["#FFB5C5", "#FFDAB9", "#B5EAD7", "#C7CEEA", "#F5E6CC"],
}

DEFAULT_COLORS = COLOR_SCHEMES["商务蓝"]
MAX_ROWS = 10000  # 数据量上限


# ============================================================
# 输入校验模块
# ============================================================
def validate_chart_type(chart_type):
    """校验图表类型是否支持。"""
    supported = {"bar", "line", "pie", "scatter", "radar", "auto"}
    if chart_type is None or chart_type == "":
        return "auto"
    chart_type = chart_type.lower().strip()
    if chart_type not in supported:
        raise ValueError(f"E004:{ERROR_CODES['E004']}")
    return chart_type


def validate_color_scheme(scheme):
    """校验配色方案，返回颜色列表。"""
    if scheme is None or scheme == "":
        return DEFAULT_COLORS
    if scheme in COLOR_SCHEMES:
        return COLOR_SCHEMES[scheme]
    # 尝试解析自定义色值数组，如 "#FF0000,#00FF00,#0000FF"
    if scheme.startswith("#") or "," in scheme:
        colors = [c.strip() for c in scheme.split(",") if c.strip().startswith("#")]
        if len(colors) >= 2:
            return colors
    raise ValueError(f"E008:{ERROR_CODES['E008']} 未知配色方案: {scheme}")


def validate_output_format(fmt):
    """校验输出格式。"""
    if fmt is None or fmt == "":
        return "png"
    fmt = fmt.lower().strip()
    if fmt not in ("png", "svg"):
        raise ValueError(f"E008:{ERROR_CODES['E008']} 输出格式仅支持 PNG/SVG")
    return fmt


def validate_file_path(path):
    """校验文件路径，防止路径穿越。"""
    if path is None or path == "":
        raise ValueError(f"E005:{ERROR_CODES['E005']}")
    p = Path(path).resolve()
    # 白名单校验：仅允许当前目录及子目录
    cwd = Path.cwd().resolve()
    if not str(p).startswith(str(cwd)):
        raise ValueError(f"E008:{ERROR_CODES['E008']} 路径不在白名单内: {path}")
    if not p.exists():
        raise ValueError(f"E005:{ERROR_CODES['E005']} 文件不存在: {path}")
    if not p.is_file():
        raise ValueError(f"E005:{ERROR_CODES['E005']} 路径不是文件: {path}")
    return p


# ============================================================
# 数据解析模块
# ============================================================
def read_file_with_encoding(file_path):
    """多编码读取文件，utf-8 → gbk → gb18030 三级 fallback。"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, IOError):
            continue
    # 最后兜底：errors="replace"
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except IOError as e:
        raise ValueError(f"E005:{ERROR_CODES['E005']} 读取失败: {e}")


def parse_csv_text(text):
    """解析 CSV 文本为二维列表。"""
    if not text or not text.strip():
        raise ValueError(f"E002:{ERROR_CODES['E002']}")
    try:
        reader = csv.reader(io.StringIO(text))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error as e:
        raise ValueError(f"E001:{ERROR_CODES['E001']} CSV 解析失败: {e}")
    if not rows:
        raise ValueError(f"E002:{ERROR_CODES['E002']}")
    return rows


def parse_json_text(text):
    """解析 JSON 文本为二维列表。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"E001:{ERROR_CODES['E001']} JSON 解析失败: {e}")
    # 支持 [["a",1],["b",2]] 或 [{"name":"a","value":1}]
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], list):
            return [list(row) for row in data]
        elif isinstance(data[0], dict):
            keys = list(data[0].keys())
            rows = [keys]
            for item in data:
                rows.append([str(item.get(k, "")) for k in keys])
            return rows
    raise ValueError(f"E001:{ERROR_CODES['E001']} JSON 格式不支持")


def parse_data_input(data_text, file_path=None):
    """解析数据输入，支持文本或文件。"""
    if file_path:
        p = validate_file_path(file_path)
        text = read_file_with_encoding(p)
        # 根据扩展名选择解析器
        suffix = p.suffix.lower()
        if suffix == ".json":
            return parse_json_text(text)
        else:
            return parse_csv_text(text)
    if data_text:
        # 尝试 JSON 或 CSV
        stripped = data_text.strip()
        if stripped.startswith("["):
            try:
                return parse_json_text(stripped)
            except ValueError:
                pass
        return parse_csv_text(stripped)
    raise ValueError(f"E002:{ERROR_CODES['E002']}")


def validate_data_rows(rows):
    """校验数据行：列数一致、非空、行数限制。"""
    if not rows:
        raise ValueError(f"E002:{ERROR_CODES['E002']}")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"E006:{ERROR_CODES['E006']}")
    # 列数一致性检查
    col_count = len(rows[0])
    for i, row in enumerate(rows):
        if len(row) != col_count:
            raise ValueError(f"E003:{ERROR_CODES['E003']} 第 {i + 1} 行列数不一致")
    return True


def extract_numeric_columns(rows):
    """提取数值列索引，返回 (类别列索引, 数值列索引列表)。"""
    if len(rows) < 2:
        raise ValueError(f"E002:{ERROR_CODES['E002']}")
    header = rows[0]
    numeric_cols = []
    for col_idx in range(1, len(header)):
        is_numeric = True
        for row in rows[1:]:
            try:
                float(row[col_idx])
            except (ValueError, IndexError):
                is_numeric = False
                break
        if is_numeric:
            numeric_cols.append(col_idx)
    if not numeric_cols:
        raise ValueError(f"E007:{ERROR_CODES['E007']}")
    # 类别列：第一列
    cat_col = 0
    return cat_col, numeric_cols


# ============================================================
# 自动选型模块
# ============================================================
def auto_select_chart_type(rows, cat_col, num_cols):
    """根据数据特征自动推荐图表类型。"""
    header = rows[0]
    cat_values = [row[cat_col] for row in rows[1:]]
    # 时间序列检测（年份/月份）
    date_pattern = re.compile(r"^\d{4}[-/]\d{1,2}([-/]\d{1,2})?$|^\d{4}年")
    if cat_values and all(date_pattern.match(str(v)) for v in cat_values[:5]):
        return "line"
    # 占比分析（总和=100）
    if num_cols:
        col = num_cols[0]
        values = []
        for row in rows[1:]:
            try:
                values.append(float(row[col]))
            except (ValueError, IndexError):
                continue
        if values and abs(sum(values) - 100.0) < 1.0:
            return "pie"
    # 分类对比（≤7 类）
    if len(cat_values) <= 7:
        return "bar"
    # 多维评价（≥3 维度）
    if len(num_cols) >= 3:
        return "radar"
    # 两变量相关性
    if len(num_cols) == 2:
        return "scatter"
    return "bar"


# ============================================================
# 图表生成模块（核心逻辑）
# ============================================================
def prepare_chart_data(rows, cat_col, num_cols):
    """准备图表数据，返回 (类别列表, 数值列表列表)。"""
    categories = []
    series = [[] for _ in num_cols]
    for row in rows[1:]:
        categories.append(str(row[cat_col]))
        for i, col in enumerate(num_cols):
            try:
                series[i].append(float(row[col]))
            except (ValueError, IndexError):
                series[i].append(0.0)
    return categories, series


def generate_bar_chart(ax, categories, series, colors, title, xlabel, ylabel):
    """生成柱状图。"""
    x = range(len(categories))
    width = 0.8 / max(len(series), 1)
    for i, s in enumerate(series):
        offset = (i - len(series) / 2) * width + width / 2
        ax.bar([xi + offset for xi in x], s, width=width, label=f"系列{i + 1}", color=colors[i % len(colors)])
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()


def generate_line_chart(ax, categories, series, colors, title, xlabel, ylabel):
    """生成折线图。"""
    x = range(len(categories))
    for i, s in enumerate(series):
        ax.plot(list(x), s, marker="o", label=f"系列{i + 1}", color=colors[i % len(colors)])
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)


def generate_pie_chart(ax, categories, series, colors, title, xlabel, ylabel):
    """生成饼图。"""
    # 合并占比 < 3% 的类别为"其他"
    s = series[0]
    total = sum(s)
    if total <= 0:
        raise ValueError(f"E009:{ERROR_CODES['E009']} 饼图数据总和必须大于 0")
    merged_cats = []
    merged_vals = []
    other_val = 0.0
    for i, v in enumerate(s):
        if v / total < 0.03 and len(merged_cats) < 7:
            other_val += v
        else:
            merged_cats.append(categories[i])
            merged_vals.append(v)
    if other_val > 0:
        merged_cats.append("其他")
        merged_vals.append(other_val)
    ax.pie(merged_vals, labels=merged_cats, autopct="%1.1f%%", colors=colors[: len(merged_cats)])
    ax.set_title(title)


def generate_scatter_chart(ax, categories, series, colors, title, xlabel, ylabel):
    """生成散点图。"""
    if len(series) < 2:
        raise ValueError(f"E009:{ERROR_CODES['E009']} 散点图需要至少两个数值列")
    x_vals = series[0]
    y_vals = series[1]
    ax.scatter(x_vals, y_vals, c=colors[0], alpha=0.7)
    # 添加趋势线
    if HAS_NUMPY and len(x_vals) > 1:
        try:
            z = np.polyfit(x_vals, y_vals, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(x_vals), max(x_vals), 50)
            ax.plot(x_line, p(x_line), "r--", alpha=0.6)
        except Exception:
            pass
    ax.set_title(title)
    ax.set_xlabel(xlabel or "X 轴")
    ax.set_ylabel(ylabel or "Y 轴")
    ax.grid(True, alpha=0.3)


def generate_radar_chart(ax, categories, series, colors, title, xlabel, ylabel):
    """生成雷达图。"""
    if len(series) < 1:
        raise ValueError(f"E009:{ERROR_CODES['E009']} 雷达图需要至少一个数值列")
    # 雷达图使用类别作为维度
    labels = categories
    num_vars = len(labels)
    if num_vars < 3:
        raise ValueError(f"E009:{ERROR_CODES['E009']} 雷达图至少需要 3 个维度")
    angles = [n / float(num_vars) * 2 * math.pi for n in range(num_vars)]
    angles += angles[:1]
    for i, s in enumerate(series):
        values = s + s[:1]
        ax.plot(angles, values, "o-", linewidth=2, label=f"系列{i + 1}", color=colors[i % len(colors)])
        ax.fill(angles, values, alpha=0.25, color=colors[i % len(colors)])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_title(title)
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.0))


def generate_chart(rows, chart_type, title, xlabel, ylabel, colors, output_format):
    """生成图表，返回输出文件路径。"""
    cat_col, num_cols = extract_numeric_columns(rows)
    if chart_type == "auto":
        chart_type = auto_select_chart_type(rows, cat_col, num_cols)
    categories, series = prepare_chart_data(rows, cat_col, num_cols)

    if not HAS_MATPLOTLIB:
        # 降级：生成文本描述文件
        return generate_text_fallback(rows, chart_type, title, categories, series)

    fig, ax = plt.subplots(figsize=(10, 6))
    try:
        if chart_type == "bar":
            generate_bar_chart(ax, categories, series, colors, title, xlabel, ylabel)
        elif chart_type == "line":
            generate_line_chart(ax, categories, series, colors, title, xlabel, ylabel)
        elif chart_type == "pie":
            generate_pie_chart(ax, categories, series, colors, title, xlabel, ylabel)
        elif chart_type == "scatter":
            generate_scatter_chart(ax, categories, series, colors, title, xlabel, ylabel)
        elif chart_type == "radar":
            # 雷达图需要极坐标
            fig.clear()
            ax = fig.add_subplot(111, projection="polar")
            generate_radar_chart(ax, categories, series, colors, title, xlabel, ylabel)
        else:
            raise ValueError(f"E004:{ERROR_CODES['E004']}")
    except ValueError:
        plt.close(fig)
        raise
    except Exception as e:
        plt.close(fig)
        raise ValueError(f"E009:{ERROR_CODES['E009']} {e}")

    # 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "svg" if output_format == "svg" else "png"
    output_path = f"chart_{timestamp}.{suffix}"
    try:
        if output_format == "png":
            fig.savefig(output_path, dpi=300, bbox_inches="tight")
        else:
            fig.savefig(output_path, format="svg", bbox_inches="tight")
    except Exception as e:
        plt.close(fig)
        raise ValueError(f"E009:{ERROR_CODES['E009']} 保存失败: {e}")
    plt.close(fig)
    return output_path


def generate_text_fallback(rows, chart_type, title, categories, series):
    """无 matplotlib 时的文本降级输出。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"chart_{timestamp}.txt"
    lines = []
    lines.append(f"图表类型: {chart_type}")
    lines.append(f"标题: {title or '无'}")
    lines.append("数据预览:")
    for i, cat in enumerate(categories[:10]):
        vals = ", ".join(f"{s[i]:.2f}" for s in series)
        lines.append(f"  {cat}: {vals}")
    if len(categories) > 10:
        lines.append(f"  ... 共 {len(categories)} 条")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path


# ============================================================
# 解读说明生成模块
# ============================================================
def generate_insights(rows, cat_col, num_cols):
    """生成数据解读说明，返回要点列表。"""
    insights = []
    categories = [str(row[cat_col]) for row in rows[1:]]
    for col in num_cols[:2]:  # 最多分析前两列数值
        values = []
        for row in rows[1:]:
            try:
                values.append(float(row[col]))
            except (ValueError, IndexError):
                values.append(0.0)
        if not values:
            continue
        max_val = max(values)
        min_val = min(values)
        avg_val = sum(values) / len(values)
        max_idx = values.index(max_val)
        min_idx = values.index(min_val)
        insights.append(f"最大值 {max_val:.2f} 出现在 {categories[max_idx]}")
        insights.append(f"最小值 {min_val:.2f} 出现在 {categories[min_idx]}")
        insights.append(f"平均值 {avg_val:.2f}")
        # 环比增长
        if len(values) >= 2 and values[-2] != 0:
            growth = (values[-1] - values[-2]) / abs(values[-2]) * 100
            insights.append(f"末段环比增长 {growth:.1f}%")
    return insights[:5]  # 最多 5 条


# ============================================================
# 输出格式化模块
# ============================================================
def format_output(output_path, insights, verbose=False, dry=False):
    """格式化输出结果。"""
    lines = []
    lines.append(f"[输出文件] {output_path}")
    lines.append("[数据解读]")
    for insight in insights:
        lines.append(f"  - {insight}")
    if dry:
        lines.append("[模拟模式] 未实际写盘，以上为预览结果")
    if verbose:
        lines.append("[详细过程] 图表生成完成，类型与参数已应用")
    return "\n".join(lines)


# ============================================================
# 主流程模块
# ============================================================
def run_pipeline(args):
    """执行主流程：解析数据 → 校验 → 生成图表 → 输出。"""
    # 1. 解析数据
    rows = parse_data_input(args.data, args.file)
    # 2. 校验数据
    validate_data_rows(rows)
    # 3. 校验参数
    chart_type = validate_chart_type(args.type)
    colors = validate_color_scheme(args.color)
    output_format = validate_output_format(args.format)
    # 4. 提取数值列
    cat_col, num_cols = extract_numeric_columns(rows)
    # 5. 自动选型
    if chart_type == "auto":
        chart_type = auto_select_chart_type(rows, cat_col, num_cols)
    # 6. 生成图表
    output_path = generate_chart(rows, chart_type, args.title, args.xlabel, args.ylabel, colors, output_format)
    # 7. 生成解读
    insights = generate_insights(rows, cat_col, num_cols)
    # 8. 输出
    result = format_output(output_path, insights, args.verbose, args.dry_run)
    return result


# ============================================================
# 自检模块（selftest）
# ============================================================
def run_selftest():
    """内置硬编码样例数据离线自检核心逻辑。"""
    print("[SELFTEST] 开始自检...")
    errors = []

    # 测试 1: CSV 解析 + 柱状图
    try:
        csv_data = "月份,销量\n1月,100\n2月,150\n3月,200\n4月,180"
        rows = parse_csv_text(csv_data)
        validate_data_rows(rows)
        cat_col, num_cols = extract_numeric_columns(rows)
        assert len(rows) == 5, "CSV 应解析出 5 行"
        assert len(num_cols) == 1, "应检测到 1 个数值列"
        chart_type = auto_select_chart_type(rows, cat_col, num_cols)
        assert chart_type in ("bar", "line"), f"自动选型结果异常: {chart_type}"
        print("  [PASS] CSV 解析与自动选型")
    except Exception as e:
        errors.append(f"CSV 解析测试失败: {e}")
        print(f"  [FAIL] {e}")

    # 测试 2: JSON 解析
    try:
        json_data = '[["产品","销量"],["A",10],["B",20],["C",30]]'
        rows = parse_json_text(json_data)
        assert len(rows) == 4, "JSON 应解析出 4 行"
        print("  [PASS] JSON 解析")
    except Exception as e:
        errors.append(f"JSON 解析测试失败: {e}")
        print(f"  [FAIL] {e}")

    # 测试 3: 空输入处理
    try:
        parse_csv_text("")
        errors.append("空输入应抛出 E002")
        print("  [FAIL] 空输入未抛出异常")
    except ValueError as e:
        assert "E002" in str(e), f"错误码应为 E002: {e}"
        print("  [PASS] 空输入错误处理")

    # 测试 4: 列数不一致
    try:
        bad_data = "a,b,c\n1,2\n3,4,5"
        rows = parse_csv_text(bad_data)
        validate_data_rows(rows)
        errors.append("列数不一致应抛出 E003")
        print("  [FAIL] 列数不一致未抛出异常")
    except ValueError as e:
        assert "E003" in str(e), f"错误码应为 E003: {e}"
        print("  [PASS] 列数不一致错误处理")

    # 测试 5: 中文标点与编码
    try:
        chinese_data = "季度,营收（万元）\n第一季度,100\n第二季度,150\n第三季度,200"
        rows = parse_csv_text(chinese_data)
        assert len(rows) == 4, "中文数据解析失败"
        print("  [PASS] 中文标点数据解析")
    except Exception as e:
        errors.append(f"中文数据解析失败: {e}")
        print(f"  [FAIL] {e}")

    # 测试 6: 超长输入（性能 O(n) 验证）
    try:
        long_data = "x,y\n" + "\n".join(f"{i},{i*2}" for i in range(5000))
        start = time.time()
        rows = parse_csv_text(long_data)
        validate_data_rows(rows)
        elapsed = time.time() - start
        assert len(rows) == 5001, "超长数据解析行数错误"
        assert elapsed < 5.0, f"解析耗时过长: {elapsed:.2f}s"
        print(f"  [PASS] 超长输入处理 ({elapsed:.2f}s)")
    except Exception as e:
        errors.append(f"超长输入测试失败: {e}")
        print(f"  [FAIL] {e}")

    # 测试 7: 解读生成
    try:
        data = "月份,销量\n1月,100\n2月,150\n3月,200"
        rows = parse_csv_text(data)
        cat_col, num_cols = extract_numeric_columns(rows)
        insights = generate_insights(rows, cat_col, num_cols)
        assert len(insights) >= 3, f"解读应至少 3 条，实际 {len(insights)}"
        print("  [PASS] 解读生成")
    except Exception as e:
        errors.append(f"解读生成失败: {e}")
        print(f"  [FAIL] {e}")

    # 测试 8: 图表生成（若 matplotlib 可用）
    if HAS_MATPLOTLIB:
        try:
            data = "月份,销量\n1月,100\n2月,150\n3月,200"
            rows = parse_csv_text(data)
            output = generate_chart(rows, "bar", "测试标题", "月份", "销量", DEFAULT_COLORS, "png")
            assert os.path.exists(output), "图表文件未生成"
            os.remove(output)
            print("  [PASS] 图表生成")
        except Exception as e:
            errors.append(f"图表生成失败: {e}")
            print(f"  [FAIL] {e}")
    else:
        print("  [SKIP] matplotlib 不可用，跳过图表生成测试")

    # 测试 9: 错误码覆盖
    try:
        validate_chart_type("invalid_type")
        errors.append("非法图表类型应抛出 E004")
        print("  [FAIL] 非法图表类型未抛出异常")
    except ValueError as e:
        assert "E004" in str(e), f"错误码应为 E004: {e}"
        print("  [PASS] 非法图表类型错误处理")

    # 测试 10: 文件路径校验
    try:
        validate_file_path("/etc/passwd")
        errors.append("路径穿越应被拦截")
        print("  [FAIL] 路径穿越未拦截")
    except ValueError as e:
        assert "E008" in str(e) or "E005" in str(e), f"错误码异常: {e}"
        print("  [PASS] 路径穿越拦截")

    # 汇总
    if errors:
        print(f"\n[SELFTEST] 失败 {len(errors)} 项:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n[SELFTEST] 全部通过 ✓")
        return True


# ============================================================
# CLI 入口
# ============================================================
def main():
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="chart-pro: 数据可视化图表生成工具",
        epilog="示例: python main.py --data '月份,销量\\n1月,100' --type bar",
    )
    parser.add_argument("--data", type=str, help="表格数据文本（CSV 或 JSON 格式）")
    parser.add_argument("--file", type=str, help="数据文件路径（CSV/JSON）")
    parser.add_argument("--type", type=str, default="auto", help="图表类型: bar/line/pie/scatter/radar/auto")
    parser.add_argument("--title", type=str, default="", help="图表标题")
    parser.add_argument("--xlabel", type=str, default="", help="X 轴名称")
    parser.add_argument("--ylabel", type=str, default="", help="Y 轴名称")
    parser.add_argument("--color", type=str, default="商务蓝", help="配色方案: 商务蓝/暖阳橙/森林绿/莫兰迪灰/马卡龙/自定义色值")
    parser.add_argument("--format", type=str, default="png", help="输出格式: png/svg")
    parser.add_argument("--dry-run", action="store_true", help="模拟模式，不实际写盘")
    parser.add_argument("--force", action="store_true", help="强制写盘（配合 --dry-run 使用）")
    parser.add_argument("--verbose", action="store_true", help="输出详细过程")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常模式
    try:
        # 参数校验
        if not args.data and not args.file:
            raise ValueError(f"E008:{ERROR_CODES['E008']} 必须提供 --data 或 --file")
        if args.dry_run and not args.force:
            print("[模拟模式] 仅预览，不写盘。加 --force 实际执行。")
            # 模拟执行：解析但不生成文件
            rows = parse_data_input(args.data, args.file)
            validate_data_rows(rows)
            chart_type = validate_chart_type(args.type)
            colors = validate_color_scheme(args.color)
            output_format = validate_output_format(args.format)
            cat_col, num_cols = extract_numeric_columns(rows)
            if chart_type == "auto":
                chart_type = auto_select_chart_type(rows, cat_col, num_cols)
            insights = generate_insights(rows, cat_col, num_cols)
            print(format_output(f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}", insights, args.verbose, True))
        else:
            result = run_pipeline(args)
            print(result)
    except ValueError as e:
        # 业务逻辑错误（警告级别）
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # 系统级异常（耻辱级别）
        import traceback
        print(f"[系统错误] E010:{ERROR_CODES['E010']}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
