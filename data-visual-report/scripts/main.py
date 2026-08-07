#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data-visual-report: 数据洞察 · 图表报告自动生成

将表格数据自动转为带图表与结论的可视化分析报告。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例:
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py data.csv            # 生成报告
    python scripts/main.py data.json --format json
"""

import argparse
import csv
import json
import math
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入格式不支持（仅支持 csv/json/md）",
    "E003": "数据为空或缺少有效数据行",
    "E004": "数据列数不一致",
    "E005": "缺少表头或列名重复",
    "E006": "数值列无法解析为数字",
    "E007": "输出目录无法创建",
    "E008": "报告写入失败",
    "E009": "JSON 解析失败",
    "E010": "参数错误或内部逻辑异常",
}


class DataReportError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def load_data(file_path: str, fmt: str = "auto") -> list:
    """读取表格数据，返回字典列表（每行一个 dict，键为列名）。"""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise DataReportError("E001", f"文件不存在: {file_path}")

    if fmt == "auto":
        suffix = path.suffix.lower()
        if suffix == ".csv":
            fmt = "csv"
        elif suffix == ".json":
            fmt = "json"
        elif suffix in (".md", ".markdown"):
            fmt = "md"
        else:
            raise DataReportError("E002", f"不支持的文件后缀: {suffix}")

    try:
        if fmt == "csv":
            return _read_csv(path)
        elif fmt == "json":
            return _read_json(path)
        elif fmt == "md":
            return _read_markdown(path)
        else:
            raise DataReportError("E002")
    except DataReportError:
        raise
    except Exception as e:
        raise DataReportError("E009" if fmt == "json" else "E010", str(e))


def _read_csv(path: Path) -> list:
    """读取 CSV 文件。"""
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise DataReportError("E005", "CSV 缺少表头")
        # 检查列名重复
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise DataReportError("E005", "CSV 列名重复")
        rows = list(reader)
    if not rows:
        raise DataReportError("E003", "CSV 无数据行")
    return rows


def _read_json(path: Path) -> list:
    """读取 JSON 数组文件。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataReportError("E009", f"JSON 解析失败: {e}")
    
    if not isinstance(data, list):
        raise DataReportError("E009", "JSON 顶层必须是数组")
    if not data:
        raise DataReportError("E003", "JSON 数组为空")
    if not all(isinstance(row, dict) for row in data):
        raise DataReportError("E009", "JSON 数组元素必须是对象")
    return data


def _read_markdown(path: Path) -> list:
    """读取 Markdown 表格（简单解析）。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    table_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
    if len(table_lines) < 2:
        raise DataReportError("E003", "Markdown 表格行不足")

    # 解析表头
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    if len(header) != len(set(header)):
        raise DataReportError("E005", "Markdown 表头重复")

    rows = []
    for line in table_lines[2:]:  # 跳过表头与分隔行
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(header):
            raise DataReportError("E004", f"Markdown 行列数不一致: {line}")
        rows.append(dict(zip(header, cells)))
    if not rows:
        raise DataReportError("E003", "Markdown 无数据行")
    return rows


def clean_data(rows: list) -> dict:
    """数据清洗：统一列名、去除空行、识别数值列。"""
    if not rows:
        raise DataReportError("E003", "输入数据为空")

    # 统一列名：去空格、转小写
    cleaned = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            if v is None:
                continue
            key = str(k).strip().lower().replace(" ", "_")
            new_row[key] = str(v).strip() if v is not None else ""
        if any(new_row.values()):  # 至少有一个非空值
            cleaned.append(new_row)

    if not cleaned:
        raise DataReportError("E003", "清洗后无有效数据")

    # 获取所有列名（并集）
    all_cols = []
    seen = set()
    for row in cleaned:
        for k in row:
            if k not in seen:
                seen.add(k)
                all_cols.append(k)
    if not all_cols:
        raise DataReportError("E005", "无法识别数据列")

    # 识别数值列（尝试转换）
    numeric_cols = []
    for col in all_cols:
        values = []
        for row in cleaned:
            v = row.get(col)
            if v is None or v == "":
                continue
            try:
                values.append(float(v))
            except ValueError:
                break
        else:
            if values:  # 至少有一个可转换的值
                numeric_cols.append(col)

    return {
        "columns": all_cols,
        "numeric_columns": numeric_cols,
        "rows": cleaned,
    }


def compute_metrics(cleaned: dict) -> dict:
    """计算核心指标：总数、均值、最值、TopN、分布等。"""
    rows = cleaned["rows"]
    numeric_cols = cleaned["numeric_columns"]
    total_rows = len(rows)

    metrics = {
        "total_rows": total_rows,
        "columns": cleaned["columns"],
        "numeric_columns": numeric_cols,
        "column_stats": {},
        "topn": {},
        "distribution": {},
    }

    # 各列统计
    for col in cleaned["columns"]:
        values = [row.get(col) for row in rows if row.get(col) not in (None, "")]
        if not values:
            continue
        # 尝试数值统计
        try:
            num_values = [float(v) for v in values]
            stats = {
                "count": len(num_values),
                "mean": sum(num_values) / len(num_values),
                "min": min(num_values),
                "max": max(num_values),
                "sum": sum(num_values),
            }
            if len(num_values) > 1:
                variance = sum((x - stats["mean"]) ** 2 for x in num_values) / len(num_values)
                stats["stddev"] = math.sqrt(variance)
            else:
                stats["stddev"] = 0.0
            metrics["column_stats"][col] = stats
        except ValueError:
            # 非数值列：统计频次
            counter = Counter(values)
            metrics["column_stats"][col] = {
                "count": len(values),
                "unique": len(counter),
                "top": counter.most_common(1)[0][0] if counter else None,
            }
            # 分布（取前 5 个）
            metrics["distribution"][col] = counter.most_common(5)

    # TopN（对第一个数值列取 Top 5）
    if numeric_cols:
        col = numeric_cols[0]
        # 安全排序，处理可能的转换错误
        def get_numeric_value(row):
            try:
                return float(row.get(col, 0) or 0)
            except (ValueError, TypeError):
                return 0
        
        sorted_rows = sorted(rows, key=get_numeric_value, reverse=True)
        metrics["topn"][col] = [
            {"rank": i + 1, "value": row.get(col), "row": row}
            for i, row in enumerate(sorted_rows[:5])
        ]

    return metrics


def recommend_chart(metrics: dict) -> dict:
    """推荐图表类型。"""
    numeric_cols = metrics["numeric_columns"]
    total = metrics["total_rows"]

    if not numeric_cols:
        return {"type": "table", "reason": "无数值列，仅适合表格展示"}

    col = numeric_cols[0]
    stats = metrics["column_stats"].get(col, {})

    # 判断是否适合饼图（分类少）
    if len(numeric_cols) == 1 and total <= 10:
        return {"type": "pie", "column": col, "reason": "数据量小且单数值列，适合饼图展示占比"}

    # 判断时间序列（列名含 date/time/年/月）
    lower_col = col.lower()
    if any(k in lower_col for k in ["date", "time", "年", "月", "日"]):
        return {"type": "line", "column": col, "reason": "检测到时间相关列，适合折线图展示趋势"}

    # 默认柱状图
    if total > 10:
        return {"type": "bar", "column": col, "reason": "数据量较大，适合柱状图对比"}

    return {"type": "bar", "column": col, "reason": "默认推荐柱状图"}


def generate_conclusions(metrics: dict, chart: dict) -> list:
    """生成文字结论。"""
    conclusions = []
    total = metrics["total_rows"]
    conclusions.append(f"本次分析共包含 {total} 条数据记录。")

    for col, stats in metrics["column_stats"].items():
        if "mean" in stats:
            conclusions.append(
                f"列「{col}」均值约为 {stats['mean']:.2f}，"
                f"取值范围 [{stats['min']:.2f}, {stats['max']:.2f}]。"
            )
        elif "unique" in stats:
            conclusions.append(
                f"列「{col}」共有 {stats['unique']} 个不同取值，"
                f"最常见的是「{stats['top']}」。"
            )

    if metrics["topn"]:
        col = list(metrics["topn"].keys())[0]
        top_items = metrics["topn"][col]
        conclusions.append(
            f"列「{col}」Top3 为: "
            + ", ".join(f"{item['value']}" for item in top_items[:3])
        )

    conclusions.append(f"推荐图表: {chart['type']}（{chart['reason']}）")
    return conclusions


def render_report(metrics: dict, chart: dict, conclusions: list) -> str:
    """生成 Markdown 格式报告。"""
    lines = []
    lines.append("# 数据可视化分析报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**数据行数**: {metrics['total_rows']}")
    lines.append("")

    # 图表说明
    lines.append("## 图表推荐")
    lines.append(f"- 类型: **{chart['type']}**")
    lines.append(f"- 原因: {chart['reason']}")
    lines.append("")

    # 数据概览
    lines.append("## 数据概览")
    lines.append("| 列名 | 类型 | 统计信息 |")
    lines.append("|------|------|----------|")
    for col in metrics["columns"]:
        stats = metrics["column_stats"].get(col, {})
        if "mean" in stats:
            info = f"均值={stats['mean']:.2f}, 范围[{stats['min']:.2f}, {stats['max']:.2f}]"
        elif "unique" in stats:
            info = f"唯一值={stats['unique']}, 最常见={stats['top']}"
        else:
            info = "无数据"
        col_type = "数值" if col in metrics["numeric_columns"] else "分类"
        lines.append(f"| {col} | {col_type} | {info} |")
    lines.append("")

    # TopN
    if metrics["topn"]:
        lines.append("## TopN 排行")
        col = list(metrics["topn"].keys())[0]
        lines.append(f"基于列「{col}」: ")
        lines.append("")
        lines.append("| 排名 | 数值 |")
        lines.append("|------|------|")
        for item in metrics["topn"][col]:
            lines.append(f"| {item['rank']} | {item['value']} |")
        lines.append("")

    # 结论
    lines.append("## 分析结论")
    for c in conclusions:
        lines.append(f"- {c}")
    lines.append("")

    # 原始数据摘要
    lines.append("## 数据预览（前 5 行）")
    lines.append("")
    for i, row in enumerate(metrics["rows"][:5]):
        lines.append(f"**行 {i+1}**: " + ", ".join(f"{k}={v}" for k, v in row.items()))
        lines.append("")

    return "\n".join(lines)


def generate_report(rows: list, output_path: str = None) -> str:
    """完整报告生成流程。"""
    try:
        cleaned = clean_data(rows)
        metrics = compute_metrics(cleaned)
        chart = recommend_chart(metrics)
        conclusions = generate_conclusions(metrics, chart)
        report = render_report(metrics, chart, conclusions)
    except DataReportError:
        raise
    except Exception as e:
        raise DataReportError("E010", f"报告生成失败: {e}")

    if output_path:
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except OSError as e:
                    raise DataReportError("E007", f"无法创建输出目录: {e}")
            Path(output_path).write_text(report, encoding="utf-8")
        except DataReportError:
            raise
        except OSError as e:
            raise DataReportError("E008", f"报告写入失败: {e}")
    return report


def selftest() -> None:
    """离线自检核心逻辑，使用硬编码样例数据。"""
    print("开始自检...")

    # 硬编码样例数据
    sample_rows = [
        {"月份": "2024-01", "销售额": "120", "利润": "30", "地区": "华北"},
        {"月份": "2024-02", "销售额": "150", "利润": "40", "地区": "华北"},
        {"月份": "2024-03", "销售额": "130", "利润": "35", "地区": "华东"},
        {"月份": "2024-04", "销售额": "180", "利润": "50", "地区": "华东"},
        {"月份": "2024-05", "销售额": "200", "利润": "60", "地区": "华南"},
        {"月份": "2024-06", "销售额": "170", "利润": "45", "地区": "华南"},
    ]

    # 测试1: 数据清洗
    try:
        cleaned = clean_data(sample_rows)
        assert len(cleaned["rows"]) == 6, "清洗后行数应为 6"
        assert "销售额" in cleaned["numeric_columns"], "销售额应为数值列"
        print("  ✓ 数据清洗正常")
    except (AssertionError, DataReportError) as e:
        print(f"  ✗ 数据清洗失败: {e}")
        raise

    # 测试2: 指标计算
    try:
        metrics = compute_metrics(cleaned)
        assert metrics["total_rows"] == 6, "总行数应为 6"
        assert "销售额" in metrics["column_stats"], "销售额统计应存在"
        sales_stats = metrics["column_stats"]["销售额"]
        # 宽松阈值: 均值应在 100-200 之间
        assert 100 < sales_stats["mean"] < 200, f"销售额均值应在 100-200 之间, 实际 {sales_stats['mean']}"
        assert sales_stats["max"] > sales_stats["min"], "最大值应大于最小值"
        print("  ✓ 指标计算正常")
    except (AssertionError, DataReportError) as e:
        print(f"  ✗ 指标计算失败: {e}")
        raise

    # 测试3: 图表推荐
    try:
        chart = recommend_chart(metrics)
        assert chart["type"] in ("bar", "line", "pie", "table"), "图表类型不合法"
        assert chart["reason"], "图表推荐应包含原因"
        print(f"  ✓ 图表推荐正常: {chart['type']}")
    except (AssertionError, DataReportError) as e:
        print(f"  ✗ 图表推荐失败: {e}")
        raise

    # 测试4: 结论生成
    try:
        conclusions = generate_conclusions(metrics, chart)
        assert len(conclusions) >= 3, "应生成至少 3 条结论"
        assert any("均值" in c for c in conclusions), "结论应包含均值信息"
        print("  ✓ 结论生成正常")
    except (AssertionError, DataReportError) as e:
        print(f"  ✗ 结论生成失败: {e}")
        raise

    # 测试5: 报告渲染
    try:
        report = render_report(metrics, chart, conclusions)
        assert report.startswith("# 数据可视化分析报告"), "报告标题错误"
        assert "## 图表推荐" in report, "报告应包含图表推荐"
        assert "## 分析结论" in report, "报告应包含分析结论"
        print("  ✓ 报告渲染正常")
    except (AssertionError, DataReportError) as e:
        print(f"  ✗ 报告渲染失败: {e}")
        raise

    # 测试6: 完整流程（通过临时文件验证输出）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "report.md")
            report = generate_report(sample_rows, output_file)
            assert os.path.exists(output_file), "报告文件应生成"
            file_size = os.path.getsize(output_file)
            assert file_size > 100, f"报告文件应大于 100 字节, 实际 {file_size}"
            print("  ✓ 完整流程正常")
    except (AssertionError, DataReportError) as e:
        print(f"  ✗ 完整流程失败: {e}")
        raise

    # 测试7: 错误处理
    try:
        clean_data([])
        raise AssertionError("空数据应抛出 E003")
    except DataReportError as e:
        assert e.code == "E003", f"错误码应为 E003, 实际 {e.code}"
    except AssertionError as e:
        print(f"  ✗ 错误处理失败: {e}")
        raise
    print("  ✓ 错误处理正常")

    # 测试8: JSON 解析错误处理
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json')
            tmp_file = f.name
        try:
            load_data(tmp_file, "json")
            raise AssertionError("无效 JSON 应抛出 E009")
        except DataReportError as e:
            assert e.code == "E009", f"错误码应为 E009, 实际 {e.code}"
        finally:
            os.unlink(tmp_file)
        print("  ✓ JSON 错误处理正常")
    except (AssertionError, DataReportError) as e:
        print(f"  ✗ JSON 错误处理失败: {e}")
        raise

    print("\n✅ 所有自检通过！")


def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="数据可视化报告生成工具",
        epilog="示例: python scripts/main.py data.csv -o report.md"
    )
    parser.add_argument("input", nargs="?", help="输入数据文件 (csv/json/md)")
    parser.add_argument("-o", "--output", help="输出报告路径 (Markdown)")
    parser.add_argument("--format", choices=["auto", "csv", "json", "md"], default="auto",
                        help="输入格式 (默认 auto 根据扩展名)")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    if args.selftest:
        selftest()
        return 0

    if not args.input:
        print("错误: 请指定输入文件或使用 --selftest", file=sys.stderr)
        return 1

    try:
        rows = load_data(args.input, args.format)
        report = generate_report(rows, args.output)
        if args.output:
            print(f"✅ 报告已生成: {args.output}")
        else:
            print(report)
        return 0
    except DataReportError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
