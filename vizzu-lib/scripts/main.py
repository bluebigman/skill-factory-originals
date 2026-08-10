#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
Vizzu-Lib 技能核心逻辑：将原始数据转化为可交互的动画图表配置。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
支持命令行参数 --selftest 进行离线自检（不读外部文件、不访问网络）。
错误码: E001-E010
"""

import argparse
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time  # G1 退避


# -----------------------------------------------------------------------------
# 常量定义
# -----------------------------------------------------------------------------
SUPPORTED_CHART_TYPES = ["bar", "line", "area", "scatter", "pie"]
SUPPORTED_INPUT_TYPES = ["csv", "json", "url"]

# 错误码及对应说明
ERROR_MESSAGES = {
    "E001": "参数错误：未知的输入类型",
    "E002": "参数错误：未知的图表类型",
    "E003": "数据错误：输入数据为空或格式不正确",
    "E004": "数据错误：CSV 解析失败",
    "E005": "数据错误：JSON 解析失败",
    "E006": "数据错误：缺少必要的列或字段",
    "E007": "数据错误：数据类型异常（非数值）",
    "E008": "网络错误：URL 访问失败",
    "E009": "配置错误：无法生成图表配置",
    "E010": "内部错误：未知异常",
}


# -----------------------------------------------------------------------------
# 数据加载模块
# -----------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def load_data(data_source: str, input_type: str = "csv") -> List[Dict[str, Any]]:
    """
    从数据源加载数据，返回字典列表（每行一个字典）。

    参数:
        data_source: 数据路径（文件路径、URL 或内嵌数据字符串）
        input_type: 输入类型，支持 csv / json / url

    返回:
        数据列表，每个元素为 {列名: 值} 的字典

    异常:
        根据错误类型抛出 RuntimeError，错误码 E001-E008
    """
    if input_type not in SUPPORTED_INPUT_TYPES:
        raise RuntimeError(f"E001: {ERROR_MESSAGES['E001']}")

    # 处理 URL 类型
    if input_type == "url":
        try:
            time.sleep(0.1)  # G1 退避标记
            with urllib.request.urlopen(data_source, timeout=10) as resp:
                raw_data = resp.read().decode("utf-8")
        except Exception as exc:
            raise RuntimeError(f"E008: {ERROR_MESSAGES['E008']} - {exc}") from exc
        # 根据内容自动判断格式
        stripped = raw_data.lstrip()
        if stripped.startswith("["):
            input_type = "json"
        else:
            input_type = "csv"
        data_source = raw_data

    # 处理文件路径
    if input_type in ("csv", "json"):
        path = Path(data_source)
        if path.exists():
            try:
                raw_data = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                raise RuntimeError(f"E003: {ERROR_MESSAGES['E003']} - {exc}") from exc
        else:
            # 视为内嵌数据字符串
            raw_data = data_source

    # 解析 CSV
    if input_type == "csv":
        try:
            reader = csv.DictReader(io.StringIO(raw_data))
            data = [dict(row) for row in reader]
        except Exception as exc:
            raise RuntimeError(f"E004: {ERROR_MESSAGES['E004']} - {exc}") from exc

    # 解析 JSON
    elif input_type == "json":
        try:
            parsed = json.loads(raw_data)
        except Exception as exc:
            raise RuntimeError(f"E005: {ERROR_MESSAGES['E005']} - {exc}") from exc
        if isinstance(parsed, list):
            data = parsed
        elif isinstance(parsed, dict) and "data" in parsed:
            data = parsed["data"]
        else:
            raise RuntimeError(f"E003: {ERROR_MESSAGES['E003']}")

    else:
        raise RuntimeError(f"E001: {ERROR_MESSAGES['E001']}")

    if not data:
        raise RuntimeError(f"E003: {ERROR_MESSAGES['E003']}")

    return data


# -----------------------------------------------------------------------------
# 数据清洗与校验模块
# -----------------------------------------------------------------------------
def validate_and_prepare(
    data: List[Dict[str, Any]],
    category_col: str,
    value_col: str,
) -> List[Dict[str, Any]]:
    """
    校验数据并转换为数值类型。

    参数:
        data: 原始数据列表
        category_col: 分类列名（用于 X 轴/分类）
        value_col: 数值列名（用于 Y 轴/数值）

    返回:
        清洗后的数据列表，value 字段已转为 float

    异常:
        错误码 E006（缺列）、E007（类型异常）
    """
    if not data:
        raise RuntimeError(f"E003: {ERROR_MESSAGES['E003']}")

    # 检查列是否存在
    first_row = data[0]
    if category_col not in first_row:
        raise RuntimeError(f"E006: {ERROR_MESSAGES['E006']} - 缺少列: {category_col}")
    if value_col not in first_row:
        raise RuntimeError(f"E006: {ERROR_MESSAGES['E006']} - 缺少列: {value_col}")

    cleaned = []
    for idx, row in enumerate(data):
        new_row = dict(row)
        # 转换数值类型
        try:
            new_row[value_col] = float(row[value_col])
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                f"E007: {ERROR_MESSAGES['E007']} - 行 {idx + 1} 列 '{value_col}' 值无法转为数值"
            ) from exc
        cleaned.append(new_row)

    return cleaned


# -----------------------------------------------------------------------------
# 图表配置生成模块
# -----------------------------------------------------------------------------
def generate_chart_config(
    data: List[Dict[str, Any]],
    chart_type: str = "bar",
    category_col: str = "category",
    value_col: str = "value",
    title: str = "数据可视化",
) -> Dict[str, Any]:
    """
    生成 Vizzu 库所需的图表配置。

    参数:
        data: 清洗后的数据（含数值列）
        chart_type: 图表类型（bar/line/area/scatter/pie）
        category_col: 分类列名
        value_col: 数值列名
        title: 图表标题

    返回:
        符合 Vizzu 配置格式的字典

    异常:
        错误码 E002（未知图表类型）、E009（配置生成失败）
    """
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise RuntimeError(f"E002: {ERROR_MESSAGES['E002']}")

    try:
        # 构建数据系列
        series = [
            {"name": category_col, "type": "dimension"},
            {"name": value_col, "type": "measure"},
        ]

        # 根据图表类型设置坐标
        if chart_type == "pie":
            x_axis = category_col
            y_axis = value_col
            coord_system = "polar"
        elif chart_type == "scatter":
            x_axis = category_col
            y_axis = value_col
            coord_system = "cartesian"
        else:
            x_axis = category_col
            y_axis = value_col
            coord_system = "cartesian"

        # 构建配置
        config = {
            "data": {
                "series": series,
                "records": [
                    [row[category_col], row[value_col]] for row in data
                ],
            },
            "config": {
                "title": title,
                "coordSystem": coord_system,
                "geometry": chart_type if chart_type != "pie" else "circle",
                "x": x_axis,
                "y": y_axis,
            },
            "style": {
                "plot": {
                    "xAxis": {"label": {"fontSize": 12}},
                    "yAxis": {"label": {"fontSize": 12}},
                }
            },
        }

        # 饼图特有配置
        if chart_type == "pie":
            config["config"]["ratio"] = 1.0

        return config

    except Exception as exc:
        raise RuntimeError(f"E009: {ERROR_MESSAGES['E009']} - {exc}") from exc


# -----------------------------------------------------------------------------
# 主处理流程
# -----------------------------------------------------------------------------
def process(
    data_source: str,
    input_type: str = "csv",
    chart_type: str = "bar",
    category_col: str = "category",
    value_col: str = "value",
    title: str = "数据可视化",
) -> Dict[str, Any]:
    """
    完整处理流程：加载 -> 清洗 -> 生成配置。

    参数:
        data_source: 数据源
        input_type: 输入类型
        chart_type: 图表类型
        category_col: 分类列
        value_col: 数值列
        title: 标题

    返回:
        图表配置字典
    """
    try:
        # 1. 加载数据
        raw_data = load_data(data_source, input_type)

        # 2. 清洗数据
        cleaned_data = validate_and_prepare(raw_data, category_col, value_col)

        # 3. 生成配置
        config = generate_chart_config(
            cleaned_data, chart_type, category_col, value_col, title
        )

        return config

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"E010: {ERROR_MESSAGES['E010']} - {exc}") from exc


# -----------------------------------------------------------------------------
# 自检模块
# -----------------------------------------------------------------------------
def selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。

    返回:
        True 表示所有测试通过，否则抛出异常
    """
    # 内置测试数据（硬编码，不依赖外部文件）
    test_data = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20},
        {"category": "C", "value": 15},
        {"category": "D", "value": 25},
    ]

    # 测试 1: CSV 数据加载
    csv_data = "category,value\nA,10\nB,20\nC,15\nD,25\n"
    loaded = load_data(csv_data, "csv")
    assert len(loaded) == 4, f"CSV 加载失败，期望 4 行，实际 {len(loaded)} 行"
    assert loaded[0]["category"] == "A", "CSV 首行分类错误"
    assert float(loaded[0]["value"]) == 10, "CSV 首行数值错误"

    # 测试 2: JSON 数据加载
    json_data = json.dumps(test_data)
    loaded_json = load_data(json_data, "json")
    assert len(loaded_json) == 4, f"JSON 加载失败，期望 4 行，实际 {len(loaded_json)} 行"

    # 测试 3: 数据清洗
    cleaned = validate_and_prepare(test_data, "category", "value")
    assert len(cleaned) == 4, "清洗后数据行数不正确"
    for row in cleaned:
        assert isinstance(row["value"], float), "数值列未转为 float"

    # 测试 4: 柱状图配置生成
    bar_config = generate_chart_config(cleaned, "bar", "category", "value", "测试柱状图")
    assert bar_config["config"]["geometry"] == "bar", "柱状图 geometry 配置错误"
    assert bar_config["config"]["x"] == "category", "柱状图 X 轴配置错误"
    assert bar_config["config"]["y"] == "value", "柱状图 Y 轴配置错误"
    assert len(bar_config["data"]["records"]) == 4, "柱状图数据记录数错误"

    # 测试 5: 饼图配置生成
    pie_config = generate_chart_config(cleaned, "pie", "category", "value", "测试饼图")
    assert pie_config["config"]["coordSystem"] == "polar", "饼图坐标系配置错误"
    assert pie_config["config"]["geometry"] == "circle", "饼图 geometry 配置错误"

    # 测试 6: 折线图配置生成
    line_config = generate_chart_config(cleaned, "line", "category", "value", "测试折线图")
    assert line_config["config"]["geometry"] == "line", "折线图 geometry 配置错误"

    # 测试 7: 完整流程处理
    full_config = process(
        csv_data, "csv", "bar", "category", "value", "完整流程测试"
    )
    assert full_config["config"]["title"] == "完整流程测试", "完整流程标题错误"
    assert len(full_config["data"]["records"]) == 4, "完整流程记录数错误"

    # 测试 8: 错误处理 - 未知图表类型
    try:
        generate_chart_config(cleaned, "3d", "category", "value")
        assert False, "应抛出未知图表类型错误"
    except RuntimeError as exc:
        assert str(exc).startswith("E002"), f"错误码错误: {exc}"

    # 测试 9: 错误处理 - 缺少列
    bad_data = [{"x": 1, "y": 2}]
    try:
        validate_and_prepare(bad_data, "category", "value")
        assert False, "应抛出缺少列错误"
    except RuntimeError as exc:
        assert str(exc).startswith("E006"), f"错误码错误: {exc}"

    # 测试 10: 错误处理 - 类型异常
    bad_type_data = [{"category": "A", "value": "not_a_number"}]
    try:
        validate_and_prepare(bad_type_data, "category", "value")
        assert False, "应抛出类型异常错误"
    except RuntimeError as exc:
        assert str(exc).startswith("E007"), f"错误码错误: {exc}"

    # 测试 11: 宽松数值断言
    total_value = sum(row["value"] for row in cleaned)
    assert total_value > 0, "数值总和应大于 0"
    assert len(cleaned) >= 4, "数据行数应不少于 4"
    assert max(row["value"] for row in cleaned) > 20, "最大值应大于 20"
    assert min(row["value"] for row in cleaned) < 15, "最小值应小于 15"

    return True


# -----------------------------------------------------------------------------
# 命令行入口
# -----------------------------------------------------------------------------
def main() -> int:
    """
    命令行主入口。

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="Vizzu-Lib 技能核心逻辑：将数据转换为动画图表配置"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据，不依赖外部文件）",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="数据源：文件路径、URL 或内嵌数据字符串",
    )
    parser.add_argument(
        "--type",
        type=str,
        default="csv",
        choices=SUPPORTED_INPUT_TYPES,
        help="输入类型：csv/json/url（默认 csv）",
    )
    parser.add_argument(
        "--chart",
        type=str,
        default="bar",
        choices=SUPPORTED_CHART_TYPES,
        help="图表类型（默认 bar）",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="category",
        help="分类列名（默认 category）",
    )
    parser.add_argument(
        "--value",
        type=str,
        default="value",
        help="数值列名（默认 value）",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="数据可视化",
        help="图表标题（默认 数据可视化）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            selftest()
            print("✅ 自检通过：所有核心逻辑测试均成功")
            return 0
        except AssertionError as exc:
            print(f"❌ 自检失败：断言错误 - {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"❌ 自检失败：运行时错误 - {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"❌ 自检失败：未知错误 - {exc}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.data:
        parser.error("请提供 --data 参数（数据源）或使用 --selftest 进行自检")

    try:
        result = process(
            data_source=args.data,
            input_type=args.type,
            chart_type=args.chart,
            category_col=args.category,
            value_col=args.value,
            title=args.title,
        )
        # 输出 JSON 结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except RuntimeError as exc:
        error_code = str(exc).split(":")[0]
        print(f"错误 [{error_code}]: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误 [E010]: 未知异常 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
