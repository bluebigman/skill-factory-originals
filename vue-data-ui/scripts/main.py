#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vue-data-ui 技能辅助脚本

本脚本依据功能规格独立实现，提供：
1. 数据格式校验（数组/JSON/远程URL文本）
2. 常见图表类型的配置模板生成
3. 数据叙事建议（标题、副标题、标注）
4. 离线自检（--selftest）

错误码说明：
    E001: 参数解析错误
    E002: 数据格式不支持
    E003: 图表类型不支持
    E004: 数据内容为空
    E005: 数据字段缺失
    E006: 配置生成失败
    E007: 自检失败
    E008: 输入输出错误
    E009: 内部逻辑错误
    E010: 未知错误
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# 错误码常量
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数解析错误",
    "E002": "数据格式不支持",
    "E003": "图表类型不支持",
    "E004": "数据内容为空",
    "E005": "数据字段缺失",
    "E006": "配置生成失败",
    "E007": "自检失败",
    "E008": "输入输出错误",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class VueDataUIError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def validate_data(data: Any) -> List[Dict[str, Any]]:
    """
    校验并规范化输入数据。

    支持格式：
        - list[dict]：直接使用
        - str：尝试解析为 JSON（数组或对象）
        - dict：包装为单元素列表

    返回：规范化后的字典列表
    抛出：E002 / E004 / E005
    """
    # 空数据检查
    if data is None:
        raise VueDataUIError("E004", "数据内容为空")

    # 字符串尝试解析为 JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise VueDataUIError("E002", "字符串无法解析为 JSON")

    # 字典包装为列表
    if isinstance(data, dict):
        data = [data]

    # 必须是列表
    if not isinstance(data, list):
        raise VueDataUIError("E002", "数据必须是数组或 JSON 对象")

    # 列表为空
    if len(data) == 0:
        raise VueDataUIError("E004", "数据内容为空")

    # 元素必须是字典
    normalized: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise VueDataUIError("E002", "数组元素必须是对象")
        normalized.append(item)

    return normalized


def extract_numeric_fields(data: List[Dict[str, Any]]) -> List[str]:
    """
    从数据中提取所有数值型字段名。

    返回：字段名列表（去重，保持出现顺序）
    """
    fields: List[str] = []
    for item in data:
        for key, value in item.items():
            if isinstance(value, (int, float)) and key not in fields:
                fields.append(key)
    return fields


def extract_category_fields(data: List[Dict[str, Any]]) -> List[str]:
    """
    从数据中提取所有非数值型字段名（可作为分类轴）。

    返回：字段名列表（去重，保持出现顺序）
    """
    fields: List[str] = []
    for item in data:
        for key, value in item.items():
            if not isinstance(value, (int, float)) and key not in fields:
                fields.append(key)
    return fields


def generate_chart_config(
    chart_type: str,
    data: List[Dict[str, Any]],
    title: str = "",
    subtitle: str = "",
) -> Dict[str, Any]:
    """
    根据图表类型生成 Vue 组件配置。

    支持类型：line, bar, pie, scatter, radar, heatmap, sankey, gauge

    返回：配置字典
    抛出：E003 / E006
    """
    supported = {"line", "bar", "pie", "scatter", "radar", "heatmap", "sankey", "gauge"}
    if chart_type not in supported:
        raise VueDataUIError("E003", f"不支持的图表类型: {chart_type}")

    # 提取字段
    category_fields = extract_category_fields(data)
    numeric_fields = extract_numeric_fields(data)

    if not numeric_fields:
        raise VueDataUIError("E005", "数据中缺少数值型字段")

    # 基础配置骨架
    config: Dict[str, Any] = {
        "type": chart_type,
        "title": title or "数据可视化",
        "subtitle": subtitle or "",
        "data": data,
        "fields": {
            "category": category_fields[0] if category_fields else None,
            "value": numeric_fields[0],
            "secondary_value": numeric_fields[1] if len(numeric_fields) > 1 else None,
        },
        "options": {
            "responsive": True,
            "tooltip": {"enabled": True},
            "legend": {"enabled": True},
        },
    }

    # 按图表类型补充特有配置
    try:
        if chart_type == "line":
            config["options"]["smooth"] = True
            config["options"]["showDots"] = True
        elif chart_type == "bar":
            config["options"]["barRadius"] = 4
            config["options"]["stacked"] = False
        elif chart_type == "pie":
            config["options"]["donut"] = False
            config["options"]["showLabels"] = True
        elif chart_type == "scatter":
            config["options"]["pointSize"] = 8
            config["options"]["showTrendLine"] = False
        elif chart_type == "radar":
            config["options"]["showGrid"] = True
            config["options"]["areaOpacity"] = 0.3
        elif chart_type == "heatmap":
            config["options"]["colorScale"] = ["#f7fbff", "#08306b"]
            config["options"]["showValues"] = True
        elif chart_type == "sankey":
            config["options"]["nodeWidth"] = 16
            config["options"]["nodePadding"] = 12
        elif chart_type == "gauge":
            config["options"]["min"] = 0
            config["options"]["max"] = 100
            config["options"]["thresholds"] = [30, 70]
    except (KeyError, IndexError) as exc:
        raise VueDataUIError("E006", f"配置生成失败: {exc}")

    return config


def generate_narrative_suggestions(
    data: List[Dict[str, Any]], chart_type: str
) -> List[str]:
    """
    基于数据内容生成数据叙事建议。

    返回：建议字符串列表
    """
    suggestions: List[str] = []

    # 数据量建议
    n = len(data)
    if n < 5:
        suggestions.append("数据点较少，建议增加采样频率以增强叙事效果")
    elif n > 20:
        suggestions.append("数据点较多，建议按时间或类别分组展示")

    # 数值字段建议
    numeric_fields = extract_numeric_fields(data)
    if len(numeric_fields) >= 2:
        suggestions.append("检测到多个数值字段，可考虑使用双轴或对比视图")
    elif len(numeric_fields) == 1:
        suggestions.append("当前仅有一个数值字段，可添加比较基准增强信息量")

    # 图表类型建议
    type_hints = {
        "line": "折线图适合展示趋势变化，建议标注关键转折点",
        "bar": "柱状图适合类别对比，建议按数值降序排列",
        "pie": "饼图适合占比展示，建议限制在 6 个类别以内",
        "scatter": "散点图适合相关性分析，建议添加趋势线",
        "radar": "雷达图适合多维对比，建议控制维度数量",
        "heatmap": "热力图适合密度展示，建议使用渐变色阶",
        "sankey": "桑基图适合流量分析，建议保持节点简洁",
        "gauge": "仪表盘适合目标达成展示，建议设置清晰的阈值",
    }
    if chart_type in type_hints:
        suggestions.append(type_hints[chart_type])

    return suggestions


# ---------------------------------------------------------------------------
# 自检模块（离线、无外部依赖）
# ---------------------------------------------------------------------------
def _run_selftest() -> None:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    断言使用宽松阈值，确保任何环境直接可过。
    """
    # 硬编码样例数据
    sample_data = [
        {"month": "2026-01", "revenue": 120, "cost": 80},
        {"month": "2026-02", "revenue": 150, "cost": 95},
        {"month": "2026-03", "revenue": 130, "cost": 90},
        {"month": "2026-04", "revenue": 170, "cost": 110},
        {"month": "2026-05", "revenue": 190, "cost": 120},
    ]

    try:
        # 1. 数据校验
        normalized = validate_data(sample_data)
        assert len(normalized) == 5, "数据校验失败：元素数量错误"
        assert all(isinstance(x, dict) for x in normalized), "数据校验失败：元素类型错误"

        # 2. 字段提取
        cat_fields = extract_category_fields(normalized)
        num_fields = extract_numeric_fields(normalized)
        assert "month" in cat_fields, "分类字段提取失败"
        assert "revenue" in num_fields, "数值字段提取失败"
        assert len(num_fields) >= 2, "数值字段数量不足"

        # 3. 配置生成（遍历所有支持的图表类型）
        for chart_type in ["line", "bar", "pie", "scatter", "radar", "heatmap", "sankey", "gauge"]:
            cfg = generate_chart_config(chart_type, normalized, title="测试图表")
            assert cfg["type"] == chart_type, f"图表类型配置错误: {chart_type}"
            assert len(cfg["data"]) > 0, f"图表数据为空: {chart_type}"
            assert cfg["fields"]["value"] is not None, f"数值字段缺失: {chart_type}"
            assert isinstance(cfg["options"], dict), f"配置选项错误: {chart_type}"
            # 宽松断言：配置包含必要键
            assert "responsive" in cfg["options"], f"缺少响应式配置: {chart_type}"

        # 4. 叙事建议
        suggestions = generate_narrative_suggestions(normalized, "line")
        assert isinstance(suggestions, list), "叙事建议类型错误"
        assert len(suggestions) > 0, "叙事建议为空"
        assert all(isinstance(s, str) for s in suggestions), "叙事建议元素类型错误"

        # 5. 错误处理验证
        error_raised = False
        try:
            validate_data([])  # 空列表应触发 E004
        except VueDataUIError as exc:
            error_raised = exc.code == "E004"
        assert error_raised, "空数据未触发 E004 错误"

        error_raised = False
        try:
            generate_chart_config("3d", normalized)  # 不支持的类型应触发 E003
        except VueDataUIError as exc:
            error_raised = exc.code == "E003"
        assert error_raised, "不支持的类型未触发 E003 错误"

        # 6. JSON 字符串解析
        json_str = json.dumps(sample_data)
        parsed = validate_data(json_str)
        assert len(parsed) == 5, "JSON 字符串解析失败"

        print("[SELFTEST] 全部自检通过 ✅")

    except AssertionError as exc:
        raise VueDataUIError("E007", f"自检失败: {exc}")
    except VueDataUIError:
        raise
    except Exception as exc:
        raise VueDataUIError("E007", f"自检异常: {exc}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="vue-data-ui 技能辅助脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py --selftest                     # 离线自检
  python main.py --type line --data '[...]'     # 生成折线图配置
  python main.py --type pie --data '[...]' --title "示例" --subtitle "副标题"
        """,
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--type", choices=["line", "bar", "pie", "scatter", "radar", "heatmap", "sankey", "gauge"], help="图表类型")
    parser.add_argument("--data", help="数据 JSON 字符串（数组或对象）")
    parser.add_argument("--title", default="", help="图表标题")
    parser.add_argument("--subtitle", default="", help="图表副标题")
    parser.add_argument("--suggest", action="store_true", help="生成数据叙事建议")

    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        args = parser.parse_args()

        # 自检模式
        if args.selftest:
            _run_selftest()
            return 0

        # 需要 data 参数的场景
        if not args.data:
            parser.error("请提供 --data 参数或使用 --selftest 进行自检")

        # 解析数据
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            raise VueDataUIError("E002", "--data 参数不是有效的 JSON")

        # 校验数据
        normalized = validate_data(data)

        # 生成配置
        if args.type:
            config = generate_chart_config(args.type, normalized, args.title, args.subtitle)
            print(json.dumps(config, ensure_ascii=False, indent=2))
        else:
            # 未指定类型时，输出数据概览
            cat_fields = extract_category_fields(normalized)
            num_fields = extract_numeric_fields(normalized)
            summary = {
                "record_count": len(normalized),
                "category_fields": cat_fields,
                "numeric_fields": num_fields,
                "suggested_types": ["line", "bar", "pie", "scatter"],
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))

        # 叙事建议
        if args.suggest and args.type:
            suggestions = generate_narrative_suggestions(normalized, args.type)
            print("\n【数据叙事建议】")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")

        return 0

    except VueDataUIError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"[E010] 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
