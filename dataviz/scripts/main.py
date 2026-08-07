#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dataviz - 演示汇报 数据图表 可视化设计辅助脚本

本脚本依据功能规格独立实现（clean-room），提供数据可视化设计相关的
辅助函数与自检逻辑。仅使用 Python 标准库。
"""

import argparse
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码定义（E001-E010）
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"      # 输入数据无效
ERR_EMPTY_DATA = "E002"         # 数据为空
ERR_INVALID_TYPE = "E003"       # 数据类型错误
ERR_INVALID_DIMENSION = "E004"  # 数据维度错误
ERR_INVALID_OPTION = "E005"     # 选项参数无效
ERR_CALC_FAILURE = "E006"       # 计算失败
ERR_INVALID_COLOR = "E007"      # 颜色值无效
ERR_INVALID_SCALE = "E008"      # 刻度/比例无效
ERR_SELFTEST_FAIL = "E009"      # 自检失败
ERR_UNKNOWN = "E010"            # 未知错误


# 内置颜色主题（供图表建议使用）
COLOR_THEMES: Dict[str, List[str]] = {
    "default": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
    "pastel": ["#aec6cf", "#ffb347", "#77dd77", "#f49ac2", "#b39eb5"],
    "vivid": ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231"],
}

# 图表类型支持的最小/最大数据系列数
CHART_SERIES_LIMITS: Dict[str, Tuple[int, int]] = {
    "bar": (1, 10),
    "line": (1, 10),
    "pie": (1, 1),
    "scatter": (2, 2),
    "heatmap": (1, 1),
}


# ---------------------------------------------------------------------------
# 核心辅助函数
# ---------------------------------------------------------------------------

def validate_numeric_list(data: Any, name: str = "data") -> List[float]:
    """
    校验输入是否为数值列表（或可转换为数值的列表）。

    参数:
        data: 待校验数据
        name: 数据名称（用于错误信息）

    返回:
        转换后的浮点数列表

    异常:
        SystemExit: 当数据无效时抛出，携带错误码
    """
    if data is None:
        print(f"[{ERR_INVALID_INPUT}] {name} 不能为空")
        sys.exit(ERR_INVALID_INPUT)

    if not isinstance(data, (list, tuple)):
        print(f"[{ERR_INVALID_TYPE}] {name} 必须是列表或元组")
        sys.exit(ERR_INVALID_TYPE)

    if len(data) == 0:
        print(f"[{ERR_EMPTY_DATA}] {name} 不能为空列表")
        sys.exit(ERR_EMPTY_DATA)

    result: List[float] = []
    for i, item in enumerate(data):
        try:
            val = float(item)
            if math.isnan(val) or math.isinf(val):
                raise ValueError("非有限数值")
            result.append(val)
        except (TypeError, ValueError):
            print(f"[{ERR_INVALID_TYPE}] {name}[{i}] 不是有效数值: {item!r}")
            sys.exit(ERR_INVALID_TYPE)

    return result


def validate_chart_type(chart_type: str) -> str:
    """
    校验图表类型是否受支持。

    参数:
        chart_type: 图表类型字符串

    返回:
        规范化后的图表类型

    异常:
        SystemExit: 当图表类型不支持时
    """
    if not isinstance(chart_type, str):
        print(f"[{ERR_INVALID_TYPE}] 图表类型必须是字符串")
        sys.exit(ERR_INVALID_TYPE)

    ct = chart_type.strip().lower()
    if ct not in CHART_SERIES_LIMITS:
        supported = ", ".join(CHART_SERIES_LIMITS.keys())
        print(f"[{ERR_INVALID_OPTION}] 不支持的图表类型: {chart_type}，支持: {supported}")
        sys.exit(ERR_INVALID_OPTION)

    return ct


def validate_series_count(chart_type: str, series_count: int) -> None:
    """
    校验数据系列数量是否符合图表类型要求。

    参数:
        chart_type: 图表类型
        series_count: 数据系列数量

    异常:
        SystemExit: 当系列数超出范围时
    """
    if chart_type not in CHART_SERIES_LIMITS:
        print(f"[{ERR_INVALID_OPTION}] 未知图表类型: {chart_type}")
        sys.exit(ERR_INVALID_OPTION)

    min_s, max_s = CHART_SERIES_LIMITS[chart_type]
    if not (min_s <= series_count <= max_s):
        print(
            f"[{ERR_INVALID_DIMENSION}] 图表 '{chart_type}' 需要 {min_s}-{max_s} 个数据系列，"
            f"实际提供 {series_count} 个"
        )
        sys.exit(ERR_INVALID_DIMENSION)


def suggest_chart_type(data: List[List[float]], purpose: str = "comparison") -> str:
    """
    根据数据特征和使用目的，建议合适的图表类型。

    参数:
        data: 二维数值数据（多个系列）
        purpose: 使用目的（comparison, trend, distribution, composition）

    返回:
        建议的图表类型字符串

    异常:
        SystemExit: 当输入无效时
    """
    # 校验输入
    if not isinstance(data, list) or len(data) == 0:
        print(f"[{ERR_EMPTY_DATA}] 数据不能为空")
        sys.exit(ERR_EMPTY_DATA)

    # 校验每个系列
    series_list = []
    for i, series in enumerate(data):
        series_list.append(validate_numeric_list(series, f"data[{i}]"))

    # 校验目的参数
    if not isinstance(purpose, str):
        print(f"[{ERR_INVALID_TYPE}] purpose 必须是字符串")
        sys.exit(ERR_INVALID_TYPE)

    purpose = purpose.strip().lower()
    valid_purposes = {"comparison", "trend", "distribution", "composition"}
    if purpose not in valid_purposes:
        print(f"[{ERR_INVALID_OPTION}] 无效目的: {purpose}，可选: {', '.join(valid_purposes)}")
        sys.exit(ERR_INVALID_OPTION)

    series_count = len(series_list)
    data_points = len(series_list[0]) if series_list else 0

    # 根据目的给出建议
    if purpose == "comparison":
        if series_count == 1:
            return "bar"
        else:
            return "line" if data_points > 3 else "bar"
    elif purpose == "trend":
        return "line"
    elif purpose == "distribution":
        if series_count == 1:
            return "bar"
        else:
            return "scatter"
    elif purpose == "composition":
        if series_count == 1:
            return "pie"
        else:
            return "bar"
    else:
        return "bar"


def compute_statistics(data: List[float]) -> Dict[str, float]:
    """
    计算一组数值的基本统计量。

    参数:
        data: 数值列表

    返回:
        包含 min, max, mean, median, std 的字典

    异常:
        SystemExit: 当计算失败时
    """
    try:
        values = validate_numeric_list(data, "data")

        n = len(values)
        if n == 0:
            print(f"[{ERR_EMPTY_DATA}] 数据为空，无法计算统计量")
            sys.exit(ERR_EMPTY_DATA)

        # 基础统计
        min_val = min(values)
        max_val = max(values)
        mean_val = sum(values) / n

        # 中位数
        sorted_vals = sorted(values)
        mid = n // 2
        if n % 2 == 0:
            median_val = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        else:
            median_val = sorted_vals[mid]

        # 标准差（总体标准差）
        variance = sum((x - mean_val) ** 2 for x in values) / n
        std_val = math.sqrt(variance)

        return {
            "min": min_val,
            "max": max_val,
            "mean": mean_val,
            "median": median_val,
            "std": std_val,
            "count": float(n),
        }
    except SystemExit:
        raise
    except Exception as e:
        print(f"[{ERR_CALC_FAILURE}] 统计计算失败: {e}")
        sys.exit(ERR_CALC_FAILURE)


def get_color_palette(theme: str = "default", count: int = 5) -> List[str]:
    """
    获取指定主题的颜色调色板。

    参数:
        theme: 主题名称
        count: 需要的颜色数量

    返回:
        颜色十六进制字符串列表

    异常:
        SystemExit: 当主题无效或数量超出时
    """
    if not isinstance(theme, str):
        print(f"[{ERR_INVALID_TYPE}] 主题名称必须是字符串")
        sys.exit(ERR_INVALID_TYPE)

    theme = theme.strip().lower()
    if theme not in COLOR_THEMES:
        available = ", ".join(COLOR_THEMES.keys())
        print(f"[{ERR_INVALID_OPTION}] 无效主题: {theme}，可选: {available}")
        sys.exit(ERR_INVALID_OPTION)

    if not isinstance(count, int) or count <= 0:
        print(f"[{ERR_INVALID_INPUT}] 颜色数量必须是正整数")
        sys.exit(ERR_INVALID_INPUT)

    palette = COLOR_THEMES[theme]

    # 如果需要的颜色多于调色板，循环重复
    result = []
    for i in range(count):
        result.append(palette[i % len(palette)])

    return result


def validate_color_hex(color: str) -> bool:
    """
    校验颜色是否为有效的十六进制颜色值。

    参数:
        color: 颜色字符串

    返回:
        是否为有效颜色
    """
    if not isinstance(color, str):
        return False

    color = color.strip()
    if not color.startswith("#"):
        return False

    hex_part = color[1:]
    if len(hex_part) not in (3, 6):
        return False

    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False


def format_data_table(data: List[List[float]], labels: Optional[List[str]] = None) -> str:
    """
    将数据格式化为表格字符串，便于展示。

    参数:
        data: 二维数据（行表示数据点，列表示系列）
        labels: 系列标签

    返回:
        格式化表格字符串

    异常:
        SystemExit: 当输入无效时
    """
    if not isinstance(data, list) or len(data) == 0:
        print(f"[{ERR_EMPTY_DATA}] 数据不能为空")
        sys.exit(ERR_EMPTY_DATA)

    # 校验所有行
    rows = []
    for i, row in enumerate(data):
        rows.append(validate_numeric_list(row, f"data[{i}]"))

    # 校验标签
    if labels is not None:
        if not isinstance(labels, list):
            print(f"[{ERR_INVALID_TYPE}] 标签必须是列表")
            sys.exit(ERR_INVALID_TYPE)
        if len(labels) != len(rows[0]):
            print(f"[{ERR_INVALID_DIMENSION}] 标签数量 ({len(labels)}) 与数据列数 ({len(rows[0])}) 不匹配")
            sys.exit(ERR_INVALID_DIMENSION)

    # 构建表格
    lines = []
    header = ["#"]
    if labels:
        header.extend(labels)
    else:
        header.extend([f"系列{j+1}" for j in range(len(rows[0]))])

    lines.append(" | ".join(header))
    lines.append("-" * len(" | ".join(header)))

    for i, row in enumerate(rows):
        row_str = [str(i + 1)]
        row_str.extend([f"{v:.2f}" for v in row])
        lines.append(" | ".join(row_str))

    return "\n".join(lines)


def generate_chart_recommendation(
    data: List[List[float]],
    purpose: str = "comparison",
    theme: str = "default",
) -> Dict[str, Any]:
    """
    生成完整的图表建议方案。

    参数:
        data: 二维数据
        purpose: 使用目的
        theme: 颜色主题

    返回:
        包含图表类型、颜色、统计信息和建议的字典

    异常:
        SystemExit: 当输入无效时
    """
    # 校验数据
    if not isinstance(data, list) or len(data) == 0:
        print(f"[{ERR_EMPTY_DATA}] 数据不能为空")
        sys.exit(ERR_EMPTY_DATA)

    series_list = []
    for i, series in enumerate(data):
        series_list.append(validate_numeric_list(series, f"data[{i}]"))

    # 建议图表类型
    chart_type = suggest_chart_type(series_list, purpose)

    # 校验系列数
    validate_series_count(chart_type, len(series_list))

    # 获取颜色
    colors = get_color_palette(theme, len(series_list))

    # 计算整体统计（使用第一个系列作为代表）
    stats = compute_statistics(series_list[0])

    # 构建建议结果
    recommendation = {
        "chart_type": chart_type,
        "purpose": purpose,
        "theme": theme,
        "colors": colors,
        "series_count": len(series_list),
        "statistics": stats,
        "notes": [],
    }

    # 添加补充建议
    if len(series_list) > 5:
        recommendation["notes"].append("数据系列较多，建议考虑分组展示或使用交互式图表")

    if stats["std"] > stats["mean"] * 0.5 and stats["mean"] != 0:
        recommendation["notes"].append("数据波动较大，建议标注异常值或使用对数刻度")

    if chart_type == "pie" and len(series_list[0]) > 6:
        recommendation["notes"].append("饼图扇区过多，建议合并小份额或改用条形图")

    return recommendation


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑正确性。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。

    返回:
        0 表示成功，非 0 表示失败
    """
    print("=" * 60)
    print("dataviz 自检开始")
    print("=" * 60)

    try:
        # --- 测试1: 数据校验 ---
        print("\n[测试1] 数据校验")
        valid_data = [1, 2, 3, 4, 5]
        result = validate_numeric_list(valid_data, "测试数据")
        assert len(result) == 5, "数据长度应为5"
        assert result[0] == 1.0, "第一个元素应为1.0"
        assert result[-1] == 5.0, "最后一个元素应为5.0"
        print("  ✓ 有效数据校验通过")

        # 无效数据应抛异常
        try:
            validate_numeric_list([1, "a", 3], "错误数据")
            print("  ✗ 应拒绝无效数据")
            return 1
        except SystemExit:
            print("  ✓ 无效数据正确拒绝")

        # --- 测试2: 图表类型建议 ---
        print("\n[测试2] 图表类型建议")
        single_series = [[10, 20, 30, 40]]
        multi_series = [[1, 2, 3], [4, 5, 6]]

        ct1 = suggest_chart_type(single_series, "comparison")
        assert ct1 == "bar", f"比较目的单系列应建议bar，实际: {ct1}"
        print(f"  ✓ 比较/单系列 → {ct1}")

        ct2 = suggest_chart_type(multi_series, "trend")
        assert ct2 == "line", f"趋势目的多系列应建议line，实际: {ct2}"
        print(f"  ✓ 趋势/多系列 → {ct2}")

        ct3 = suggest_chart_type(single_series, "composition")
        assert ct3 == "pie", f"构成目的单系列应建议pie，实际: {ct3}"
        print(f"  ✓ 构成/单系列 → {ct3}")

        ct4 = suggest_chart_type(multi_series, "distribution")
        assert ct4 == "scatter", f"分布目的多系列应建议scatter，实际: {ct4}"
        print(f"  ✓ 分布/多系列 → {ct4}")

        # --- 测试3: 统计计算 ---
        print("\n[测试3] 统计计算")
        test_data = [2, 4, 4, 4, 5, 5, 7, 9]
        stats = compute_statistics(test_data)

        assert stats["count"] == 8, f"计数应为8，实际: {stats['count']}"
        assert stats["min"] == 2, f"最小值应为2，实际: {stats['min']}"
        assert stats["max"] == 9, f"最大值应为9，实际: {stats['max']}"
        assert abs(stats["mean"] - 5.0) < 0.01, f"均值应接近5.0，实际: {stats['mean']}"
        assert abs(stats["median"] - 4.5) < 0.01, f"中位数应接近4.5，实际: {stats['median']}"
        assert stats["std"] > 0, f"标准差应为正，实际: {stats['std']}"
        print(f"  ✓ 统计量计算正确 (mean={stats['mean']:.2f}, median={stats['median']:.2f}, std={stats['std']:.2f})")

        # 空数据应报错
        try:
            compute_statistics([])
            print("  ✗ 空数据应报错")
            return 1
        except SystemExit:
            print("  ✓ 空数据正确拒绝")

        # --- 测试4: 颜色调色板 ---
        print("\n[测试4] 颜色调色板")
        colors = get_color_palette("default", 3)
        assert len(colors) == 3, f"应返回3个颜色，实际: {len(colors)}"
        for c in colors:
            assert validate_color_hex(c), f"无效颜色: {c}"
        print(f"  ✓ 默认主题颜色: {colors}")

        # 循环取色
        colors_many = get_color_palette("default", 7)
        assert len(colors_many) == 7, f"应返回7个颜色，实际: {len(colors_many)}"
        assert colors_many[5] == colors_many[0], "循环取色应重复"
        print(f"  ✓ 循环取色正确: {colors_many}")

        # 无效主题
        try:
            get_color_palette("nonexistent", 3)
            print("  ✗ 无效主题应报错")
            return 1
        except SystemExit:
            print("  ✓ 无效主题正确拒绝")

        # --- 测试5: 颜色校验 ---
        print("\n[测试5] 颜色校验")
        assert validate_color_hex("#fff") is True, "3位十六进制应有效"
        assert validate_color_hex("#ffffff") is True, "6位十六进制应有效"
        assert validate_color_hex("red") is False, "颜色名应无效"
        assert validate_color_hex("#gggggg") is False, "非十六进制字符应无效"
        assert validate_color_hex("") is False, "空字符串应无效"
        assert validate_color_hex(None) is False, "None应无效"
        print("  ✓ 颜色校验逻辑正确")

        # --- 测试6: 数据表格格式化 ---
        print("\n[测试6] 数据表格格式化")
        table_data = [[1, 2], [3, 4]]
        table = format_data_table(table_data, ["A", "B"])
        assert "A" in table and "B" in table, "表头应包含标签"
        assert "1.00" in table, "应包含格式化数值"
        assert "2.00" in table, "应包含格式化数值"
        print(f"  ✓ 表格格式化正确:\n{table}")

        # --- 测试7: 完整建议生成 ---
        print("\n[测试7] 完整建议生成")
        demo_data = [[12, 19, 15, 22, 30], [8, 12, 10, 15, 20]]
        rec = generate_chart_recommendation(demo_data, "trend", "pastel")

        assert rec["chart_type"] == "line", f"趋势建议应为line，实际: {rec['chart_type']}"
        assert len(rec["colors"]) == 2, f"应有2个颜色，实际: {len(rec['colors'])}"
        assert rec["statistics"]["count"] == 5, f"统计计数应为5，实际: {rec['statistics']['count']}"
        assert isinstance(rec["notes"], list), "建议说明应为列表"
        print(f"  ✓ 建议生成成功: 图表={rec['chart_type']}, 颜色={rec['colors']}")

        # --- 测试8: 系列数校验 ---
        print("\n[测试8] 系列数校验")
        try:
            validate_series_count("pie", 2)
            print("  ✗ 饼图多系列应报错")
            return 1
        except SystemExit:
            print("  ✓ 饼图系列数限制正确")

        try:
            validate_series_count("scatter", 1)
            print("  ✗ 散点图单系列应报错")
            return 1
        except SystemExit:
            print("  ✓ 散点图系列数限制正确")

        # --- 测试9: 边界情况 ---
        print("\n[测试9] 边界情况")
        # 单元素数据
        single = compute_statistics([42])
        assert single["mean"] == 42.0, "单元素均值应等于元素值"
        assert single["std"] == 0.0, "单元素标准差应为0"
        print("  ✓ 单元素数据处理正确")

        # 负数和零
        mixed = validate_numeric_list([-1, 0, 1])
        assert len(mixed) == 3 and mixed[0] == -1.0, "负数处理错误"
        print("  ✓ 负数处理正确")

        # 大数
        big = validate_numeric_list([1e10, 2e10])
        assert big[1] == 2e10, "大数处理错误"
        print("  ✓ 大数处理正确")

        # 小数
        small = validate_numeric_list([0.1, 0.2, 0.3])
        assert abs(small[0] - 0.1) < 1e-9, "小数处理错误"
        print("  ✓ 小数处理正确")

        # --- 测试10: 错误码覆盖 ---
        print("\n[测试10] 错误码覆盖")
        # E001 无效输入
        try:
            validate_numeric_list(None, "测试")
            return 1
        except SystemExit:
            pass

        # E002 空数据
        try:
            validate_numeric_list([], "测试")
            return 1
        except SystemExit:
            pass

        # E003 类型错误
        try:
            validate_numeric_list("abc", "测试")
            return 1
        except SystemExit:
            pass

        # E005 选项错误
        try:
            suggest_chart_type([[1]], "invalid_purpose")
            return 1
        except SystemExit:
            pass

        print("  ✓ 错误码覆盖完整")

        # ------------------------------------------------------------------
        # 所有测试通过
        # ------------------------------------------------------------------
        print("\n" + "=" * 60)
        print("✅ 所有自检测试通过！")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        print(f"[{ERR_SELFTEST_FAIL}] 断言失败")
        return 1
    except SystemExit as e:
        print(f"\n❌ 自检异常退出: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 自检发生未预期异常: {e}")
        print(f"[{ERR_UNKNOWN}] 未知错误")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    主入口函数，解析命令行参数并执行相应操作。
    """
    parser = argparse.ArgumentParser(
        description="dataviz - 数据可视化设计辅助工具",
        epilog="示例: python main.py --selftest",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="dataviz 1.0.1",
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="运行演示模式（展示示例数据）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 演示模式
    if args.demo:
        print("dataviz 演示模式")
        print("-" * 40)

        # 示例数据
        demo_data = [
            [12, 19, 15, 22, 30],
            [8, 12, 10, 15, 20],
        ]

        print("\n示例数据:")
        print(format_data_table(demo_data, ["产品A", "产品B"]))

        print("\n图表建议:")
        rec = generate_chart_recommendation(demo_data, "trend", "default")
        print(f"  推荐图表: {rec['chart_type']}")
        print(f"  颜色方案: {', '.join(rec['colors'])}")
        print(f"  统计信息: 均值={rec['statistics']['mean']:.2f}, "
              f"中位数={rec['statistics']['median']:.2f}")

        if rec["notes"]:
            print("\n补充建议:")
            for note in rec["notes"]:
                print(f"  • {note}")

        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
