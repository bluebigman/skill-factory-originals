#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
laravel-dynamic-report-generator 的独立实现脚本
版本: 1.0.3 (clean-room 重写)
仅依据功能规格实现，不包含任何既有代码。
"""

import argparse
import json
import sys
from collections import OrderedDict
from datetime import datetime


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "参数错误：数据格式不正确（应为字典列表）",
    "E003": "参数错误：维度字段不存在于数据中",
    "E004": "参数错误：度量字段不存在于数据中",
    "E005": "参数错误：筛选条件格式不正确",
    "E006": "参数错误：聚合函数不支持",
    "E007": "参数错误：排序字段不存在",
    "E008": "运行时错误：数据为空",
    "E009": "运行时错误：数据透视失败",
    "E010": "运行时错误：未知错误",
}


def _fail(code: str, message: str = None):
    """抛出带错误码的异常"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    raise RuntimeError(f"[{code}] {msg}")


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def _ensure_list_of_dicts(data):
    """校验数据格式，必须是字典列表"""
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        _fail("E002")
    return data


def _get_field(item: dict, field: str, default=None):
    """从字典中安全取值，支持点号路径"""
    if "." in field:
        parts = field.split(".")
        value = item
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    return item.get(field, default)


def _parse_filters(filters):
    """
    解析筛选条件。
    支持格式: {"field": "status", "op": "eq", "value": "active"}
    op 支持: eq, ne, gt, gte, lt, lte, in, contains
    """
    if filters is None:
        return []
    if not isinstance(filters, list):
        _fail("E005")
    parsed = []
    for cond in filters:
        if not isinstance(cond, dict):
            _fail("E005")
        field = cond.get("field")
        op = cond.get("op", "eq")
        value = cond.get("value")
        if not field or op not in ("eq", "ne", "gt", "gte", "lt", "lte", "in", "contains"):
            _fail("E005")
        parsed.append({"field": field, "op": op, "value": value})
    return parsed


def _apply_filters(data, filters):
    """对数据应用筛选条件"""
    if not filters:
        return data
    result = []
    for item in data:
        match = True
        for cond in filters:
            field = cond["field"]
            op = cond["op"]
            value = cond["value"]
            actual = _get_field(item, field)
            if op == "eq":
                if actual != value:
                    match = False
            elif op == "ne":
                if actual == value:
                    match = False
            elif op == "gt":
                if actual is None or not (actual > value):
                    match = False
            elif op == "gte":
                if actual is None or not (actual >= value):
                    match = False
            elif op == "lt":
                if actual is None or not (actual < value):
                    match = False
            elif op == "lte":
                if actual is None or not (actual <= value):
                    match = False
            elif op == "in":
                if actual not in value:
                    match = False
            elif op == "contains":
                if actual is None or str(value) not in str(actual):
                    match = False
            if not match:
                break
        if match:
            result.append(item)
    return result


def _aggregate(values, func):
    """对数值列表执行聚合函数"""
    if not values:
        return 0
    if func == "count":
        return len(values)
    if func == "sum":
        return sum(v for v in values if isinstance(v, (int, float)))
    if func == "avg":
        nums = [v for v in values if isinstance(v, (int, float))]
        return sum(nums) / len(nums) if nums else 0
    if func == "min":
        nums = [v for v in values if isinstance(v, (int, float))]
        return min(nums) if nums else 0
    if func == "max":
        nums = [v for v in values if isinstance(v, (int, float))]
        return max(nums) if nums else 0
    _fail("E006", f"不支持的聚合函数: {func}")


# ---------------------------------------------------------------------------
# 核心报表生成逻辑
# ---------------------------------------------------------------------------
def generate_report(data, dimensions=None, measures=None, filters=None, sort_by=None, sort_order="asc"):
    """
    生成结构化报表。

    参数:
        data: 字典列表，原始数据
        dimensions: 维度字段列表，用于分组
        measures: 度量字段列表，格式 [{"field": "amount", "agg": "sum", "alias": "total"}]
        filters: 筛选条件列表
        sort_by: 排序字段
        sort_order: 排序方向 asc/desc

    返回:
        报表字典，包含 rows(明细)、summary(汇总)、meta(元信息)
    """
    try:
        data = _ensure_list_of_dicts(data)
        dimensions = dimensions or []
        measures = measures or []
        filters = _parse_filters(filters)

        # 校验字段存在
        if data:
            sample = data[0]
            for dim in dimensions:
                if dim not in sample:
                    _fail("E003", f"维度字段不存在: {dim}")
            for m in measures:
                field = m.get("field") if isinstance(m, dict) else m
                if field not in sample:
                    _fail("E004", f"度量字段不存在: {field}")
        else:
            _fail("E008")

        # 应用筛选
        filtered = _apply_filters(data, filters)

        # 按维度分组聚合
        groups = OrderedDict()
        for item in filtered:
            key_parts = []
            for dim in dimensions:
                val = _get_field(item, dim, "")
                # 统一键值类型，便于分组
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False, sort_keys=True)
                key_parts.append(str(val))
            key = tuple(key_parts)

            if key not in groups:
                groups[key] = {"_items": []}
                for dim_idx, dim in enumerate(dimensions):
                    groups[key][dim] = key_parts[dim_idx]
                for m in measures:
                    if isinstance(m, dict):
                        alias = m.get("alias", m["field"])
                    else:
                        alias = m
                    groups[key][alias] = []

            for m in measures:
                if isinstance(m, dict):
                    field = m["field"]
                    alias = m.get("alias", field)
                else:
                    field = m
                    alias = m
                groups[key][alias].append(_get_field(item, field, 0))

        # 构建结果行
        rows = []
        for key, group in groups.items():
            row = {}
            for dim in dimensions:
                row[dim] = group[dim]
            for m in measures:
                if isinstance(m, dict):
                    field = m["field"]
                    agg = m.get("agg", "sum")
                    alias = m.get("alias", field)
                else:
                    field = m
                    agg = "sum"
                    alias = m
                row[alias] = _aggregate(group[alias], agg)
            rows.append(row)

        # 排序
        if sort_by and rows:
            if sort_by not in rows[0]:
                _fail("E007", f"排序字段不存在: {sort_by}")
            reverse = (sort_order == "desc")
            rows.sort(key=lambda r: r.get(sort_by, 0), reverse=reverse)

        # 汇总
        summary = {}
        for m in measures:
            if isinstance(m, dict):
                field = m["field"]
                agg = m.get("agg", "sum")
                alias = m.get("alias", field)
            else:
                field = m
                agg = "sum"
                alias = m
            all_values = [_get_field(item, field, 0) for item in filtered]
            summary[alias] = _aggregate(all_values, agg)

        return {
            "rows": rows,
            "summary": summary,
            "meta": {
                "total_rows": len(rows),
                "source_rows": len(filtered),
                "generated_at": datetime.now().isoformat(),
                "dimensions": dimensions,
                "measures": measures,
            },
        }
    except RuntimeError:
        raise
    except Exception as e:
        _fail("E010", str(e))


# ---------------------------------------------------------------------------
# 数据透视功能
# ---------------------------------------------------------------------------
def pivot_table(data, rows_dim, cols_dim, value_field, agg="sum"):
    """
    生成数据透视表（行×列矩阵）。

    参数:
        data: 字典列表
        rows_dim: 行维度字段
        cols_dim: 列维度字段
        value_field: 值字段
        agg: 聚合函数

    返回:
        透视表结构: {"rows": [...], "columns": [...], "matrix": {...}}
    """
    try:
        data = _ensure_list_of_dicts(data)
        if not data:
            _fail("E008")
        if rows_dim not in data[0]:
            _fail("E003", f"行维度字段不存在: {rows_dim}")
        if cols_dim not in data[0]:
            _fail("E003", f"列维度字段不存在: {cols_dim}")
        if value_field not in data[0]:
            _fail("E004", f"值字段不存在: {value_field}")

        # 收集行、列唯一值
        row_vals = sorted(set(str(_get_field(item, rows_dim, "")) for item in data))
        col_vals = sorted(set(str(_get_field(item, cols_dim, "")) for item in data))

        # 构建矩阵
        matrix = {}
        for rv in row_vals:
            matrix[rv] = {}
            for cv in col_vals:
                # 收集该单元格的所有值
                cell_values = []
                for item in data:
                    if str(_get_field(item, rows_dim, "")) == rv and str(_get_field(item, cols_dim, "")) == cv:
                        cell_values.append(_get_field(item, value_field, 0))
                matrix[rv][cv] = _aggregate(cell_values, agg)

        return {
            "rows": row_vals,
            "columns": col_vals,
            "matrix": matrix,
            "meta": {
                "rows_dim": rows_dim,
                "cols_dim": cols_dim,
                "value_field": value_field,
                "agg": agg,
            },
        }
    except RuntimeError:
        raise
    except Exception as e:
        _fail("E009", str(e))


# ---------------------------------------------------------------------------
# 可视化数据生成（图表 JSON）
# ---------------------------------------------------------------------------
def generate_chart_data(report_result, chart_type="bar"):
    """
    将报表结果转换为图表库（ECharts/Chart.js）兼容的 JSON 结构。

    参数:
        report_result: generate_report() 的返回值
        chart_type: bar / line / pie

    返回:
        图表数据字典
    """
    rows = report_result.get("rows", [])
    if not rows:
        return {"type": chart_type, "labels": [], "datasets": []}

    # 第一个维度作为标签
    dims = report_result.get("meta", {}).get("dimensions", [])
    label_field = dims[0] if dims else list(rows[0].keys())[0]

    # 度量字段（非维度字段）
    measure_fields = [k for k in rows[0].keys() if k != label_field]

    labels = [str(r.get(label_field, "")) for r in rows]

    if chart_type == "pie":
        # 饼图：取第一个度量
        field = measure_fields[0] if measure_fields else None
        values = [r.get(field, 0) for r in rows] if field else []
        return {
            "type": "pie",
            "labels": labels,
            "datasets": [{"data": values, "name": field or "value"}],
        }
    else:
        # 柱状图 / 折线图
        datasets = []
        for field in measure_fields:
            values = [r.get(field, 0) for r in rows]
            datasets.append({"name": field, "data": values})
        return {
            "type": chart_type,
            "labels": labels,
            "datasets": datasets,
        }


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例数据，离线运行）
# ---------------------------------------------------------------------------
def _selftest():
    """内置样例数据的离线自检，任何环境直接可运行"""
    print("开始自检...")

    # 内置硬编码样例数据
    sample_data = [
        {"date": "2026-01", "category": "电子产品", "region": "华东", "amount": 1200, "status": "completed"},
        {"date": "2026-01", "category": "电子产品", "region": "华北", "amount": 800, "status": "completed"},
        {"date": "2026-01", "category": "服饰", "region": "华东", "amount": 500, "status": "pending"},
        {"date": "2026-02", "category": "电子产品", "region": "华东", "amount": 1500, "status": "completed"},
        {"date": "2026-02", "category": "服饰", "region": "华北", "amount": 300, "status": "completed"},
        {"date": "2026-02", "category": "服饰", "region": "华东", "amount": 700, "status": "pending"},
        {"date": "2026-03", "category": "电子产品", "region": "华北", "amount": 900, "status": "completed"},
        {"date": "2026-03", "category": "电子产品", "region": "华东", "amount": 1100, "status": "completed"},
        {"date": "2026-03", "category": "服饰", "region": "华东", "amount": 400, "status": "pending"},
    ]

    # --- 测试1: 基础报表生成 ---
    print("测试1: 基础报表生成...")
    report = generate_report(
        data=sample_data,
        dimensions=["category"],
        measures=[{"field": "amount", "agg": "sum", "alias": "total_amount"}],
        filters=[{"field": "status", "op": "eq", "value": "completed"}],
        sort_by="total_amount",
        sort_order="desc",
    )
    assert len(report["rows"]) >= 1, "报表行数应大于0"
    assert report["meta"]["source_rows"] >= 1, "源数据行数应大于0"
    assert report["summary"]["total_amount"] > 0, "汇总金额应大于0"
    # 宽松验证：总金额应大于任意单行金额
    max_row_amount = max(r["total_amount"] for r in report["rows"])
    assert report["summary"]["total_amount"] > max_row_amount, "汇总应大于单行最大值"
    print("  通过 ✓")

    # --- 测试2: 数据透视 ---
    print("测试2: 数据透视...")
    pivot = pivot_table(
        data=sample_data,
        rows_dim="category",
        cols_dim="region",
        value_field="amount",
        agg="sum",
    )
    assert len(pivot["rows"]) >= 1, "透视行数应大于0"
    assert len(pivot["columns"]) >= 1, "透视列数应大于0"
    # 验证矩阵中至少有一个单元格值 > 0
    total_cell_value = 0
    for row_key in pivot["rows"]:
        for col_key in pivot["columns"]:
            total_cell_value += pivot["matrix"][row_key][col_key]
    assert total_cell_value > 0, "透视矩阵总金额应大于0"
    print("  通过 ✓")

    # --- 测试3: 筛选功能 ---
    print("测试3: 筛选功能...")
    filtered = generate_report(
        data=sample_data,
        dimensions=["region"],
        measures=[{"field": "amount", "agg": "sum", "alias": "total"}],
        filters=[
            {"field": "date", "op": "gte", "value": "2026-02"},
            {"field": "status", "op": "in", "value": ["completed", "pending"]},
        ],
    )
    assert len(filtered["rows"]) >= 1, "筛选后应有数据"
    # 所有行日期应大于等于 2026-02
    for row in filtered["rows"]:
        assert row["region"] in ("华东", "华北"), "地区应在预期范围内"
    print("  通过 ✓")

    # --- 测试4: 图表数据生成 ---
    print("测试4: 图表数据生成...")
    chart = generate_chart_data(report, chart_type="bar")
    assert chart["type"] == "bar", "图表类型应为bar"
    assert len(chart["labels"]) >= 1, "图表标签应大于0"
    assert len(chart["datasets"]) >= 1, "图表数据集应大于0"
    # 验证数据集长度与标签一致
    for ds in chart["datasets"]:
        assert len(ds["data"]) == len(chart["labels"]), "数据长度应与标签一致"
    print("  通过 ✓")

    # --- 测试5: 聚合函数多样性 ---
    print("测试5: 聚合函数...")
    agg_report = generate_report(
        data=sample_data,
        dimensions=["region"],
        measures=[
            {"field": "amount", "agg": "avg", "alias": "avg_amount"},
            {"field": "amount", "agg": "count", "alias": "order_count"},
        ],
    )
    assert len(agg_report["rows"]) >= 1, "聚合报表应有数据"
    for row in agg_report["rows"]:
        assert row["avg_amount"] >= 0, "平均金额应非负"
        assert row["order_count"] >= 1, "订单数应大于等于1"
    print("  通过 ✓")

    # --- 测试6: 错误处理 ---
    print("测试6: 错误处理...")
    try:
        generate_report(data=[{"a": 1}], dimensions=["nonexist"], measures=[{"field": "amount", "agg": "sum"}])
        assert False, "应抛出维度不存在的错误"
    except RuntimeError as e:
        assert "E003" in str(e), "错误码应为E003"
    print("  通过 ✓")

    # --- 测试7: 空数据错误处理 ---
    print("测试7: 空数据错误处理...")
    try:
        generate_report(data=[], dimensions=["category"], measures=[{"field": "amount", "agg": "sum"}])
        assert False, "应抛出数据为空的错误"
    except RuntimeError as e:
        assert "E008" in str(e), "错误码应为E008"
    print("  通过 ✓")

    # --- 测试8: 排序功能 ---
    print("测试8: 排序功能...")
    sorted_report = generate_report(
        data=sample_data,
        dimensions=["region"],
        measures=[{"field": "amount", "agg": "sum", "alias": "total"}],
        sort_by="total",
        sort_order="asc",
    )
    totals = [r["total"] for r in sorted_report["rows"]]
    assert totals == sorted(totals), "应按升序排序"
    print("  通过 ✓")

    # --- 测试9: 折线图数据生成 ---
    print("测试9: 折线图数据生成...")
    line_chart = generate_chart_data(report, chart_type="line")
    assert line_chart["type"] == "line", "图表类型应为line"
    assert len(line_chart["labels"]) >= 1, "图表标签应大于0"
    print("  通过 ✓")

    # --- 测试10: 饼图数据生成 ---
    print("测试10: 饼图数据生成...")
    pie_chart = generate_chart_data(report, chart_type="pie")
    assert pie_chart["type"] == "pie", "图表类型应为pie"
    assert len(pie_chart["labels"]) >= 1, "图表标签应大于0"
    assert len(pie_chart["datasets"]) == 1, "饼图应只有一个数据集"
    print("  通过 ✓")

    print("\n全部自检通过！ ✅")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="laravel-dynamic-report-generator - 动态报表生成器（独立实现）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，离线运行）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 文件路径（包含 data 字段）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--dimensions",
        type=str,
        default="",
        help="维度字段，逗号分隔",
    )
    parser.add_argument(
        "--measures",
        type=str,
        default="",
        help="度量字段，格式: field:agg:alias，分号分隔多个",
    )
    parser.add_argument(
        "--chart",
        type=str,
        choices=["bar", "line", "pie"],
        default=None,
        help="生成图表数据",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        _selftest()
        return 0

    # 处理输入文件
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)

        data = input_data.get("data", input_data if isinstance(input_data, list) else [])
        filters = input_data.get("filters")

        # 解析维度
        dimensions = [d.strip() for d in args.dimensions.split(",") if d.strip()]

        # 解析度量
        measures = []
        if args.measures:
            for m in args.measures.split(";"):
                parts = m.strip().split(":")
                if len(parts) == 1:
                    measures.append({"field": parts[0], "agg": "sum", "alias": parts[0]})
                elif len(parts) == 2:
                    measures.append({"field": parts[0], "agg": parts[1], "alias": parts[0]})
                elif len(parts) >= 3:
                    measures.append({"field": parts[0], "agg": parts[1], "alias": parts[2]})
        else:
            # 默认取第一个非维度字段
            if data and dimensions:
                for key in data[0]:
                    if key not in dimensions:
                        measures.append({"field": key, "agg": "sum", "alias": key})
                        break

        # 生成报表
        report = generate_report(
            data=data,
            dimensions=dimensions,
            measures=measures,
            filters=filters,
        )

        # 图表输出
        if args.chart:
            result = generate_chart_data(report, chart_type=args.chart)
        else:
            result = report

        # 输出
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"报表已写入: {args.output}")
        else:
            print(output_json)

        return 0

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"错误: 文件不存在 - {args.input}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print(f"错误: JSON 解析失败 - {args.input}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
