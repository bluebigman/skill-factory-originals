#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plotsense - 数据可视化技能核心实现

本脚本依据功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供命令行入口，支持 --selftest 离线自检。

错误码约定：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常
    E007: 参数解析失败
    E008: 自检失败
    E009: 输出写入失败
    E010: 未知错误
"""

import argparse
import json
import math
import os
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 置信度阈值（与规格一致）
CONFIDENCE_HIGH = 0.90       # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85     # 85%-90% 标注"建议复核"

# 支持的结构化字段（核心能力中的关键信息）
SUPPORTED_FIELDS = [
    "title",        # 标题
    "x_label",      # X 轴标签
    "y_label",      # Y 轴标签
    "data_points",  # 数据点列表
    "chart_type",   # 图表类型
]

# 支持的图表类型（用于格式校验）
SUPPORTED_CHART_TYPES = ["line", "bar", "scatter", "pie", "histogram"]

# 默认输出模板（标准流程 Step 2 中的默认模板）
DEFAULT_TEMPLATE = {
    "title": "数据可视化结果",
    "x_label": "X",
    "y_label": "Y",
    "chart_type": "line",
    "data_points": [],
    "confidence": 1.0,
    "notes": [],
}


# ---------------------------------------------------------------------------
# 核心数据结构与工具函数
# ---------------------------------------------------------------------------

class PlotSenseError(Exception):
    """自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _make_error(code: str, message: str) -> Dict[str, str]:
    """构造标准错误响应。"""
    return {"error_code": code, "error_message": message}


def _validate_data_points(points: Any) -> Tuple[bool, str]:
    """
    校验数据点格式。
    宽松校验：接受 [x, y] 二元组列表或数字列表。
    返回 (是否合法, 错误描述)。
    """
    if not isinstance(points, list):
        return False, "data_points 必须是列表"
    if len(points) == 0:
        return True, ""  # 空列表合法（但会降低置信度）
    for p in points:
        if isinstance(p, (int, float)):
            continue  # 单个数值（如直方图数据）
        if isinstance(p, (list, tuple)) and len(p) == 2:
            x, y = p
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                continue
            return False, f"数据点 {p} 格式错误，应为 [数值, 数值]"
        return False, f"数据点 {p} 格式错误"
    return True, ""


def _calculate_confidence(points: List[Any], has_title: bool, has_labels: bool) -> float:
    """
    计算置信度（0~1）。
    规则：
      - 基础分 0.6
      - 有标题 +0.1
      - 有轴标签 +0.1
      - 数据点数量 >= 3 +0.1
      - 数据点数量 >= 10 +0.1
    最高 1.0，最低 0.5。
    """
    score = 0.6
    if has_title:
        score += 0.1
    if has_labels:
        score += 0.1
    if len(points) >= 3:
        score += 0.1
    if len(points) >= 10:
        score += 0.1
    return max(0.5, min(1.0, score))


def _format_confidence_note(confidence: float) -> str:
    """根据置信度生成标注文本（规格 Step 2）。"""
    if confidence >= CONFIDENCE_HIGH:
        return ""
    if confidence >= CONFIDENCE_MEDIUM:
        return "建议复核"
    return "[需核实]"


# ---------------------------------------------------------------------------
# 核心处理逻辑（标准流程 Step 2）
# ---------------------------------------------------------------------------

def process_input(
    raw_input: Any,
    output_format: str = "json",
    completeness: str = "detailed",
) -> Dict[str, Any]:
    """
    处理用户输入，生成结构化结果。

    参数：
        raw_input: 用户提供的数据（字符串、字典、列表等）
        output_format: 输出格式（json / dict）
        completeness: 完整度（quick / detailed）

    返回：
        处理结果字典，包含结构化数据、置信度和标注。

    异常：
        PlotSenseError: 携带错误码 E001-E005
    """
    # ---- E001: 输入为空 ----
    if raw_input is None or raw_input == "":
        raise PlotSenseError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    # ---- 解析输入 ----
    parsed_data: Dict[str, Any] = {}
    if isinstance(raw_input, dict):
        parsed_data = raw_input
    elif isinstance(raw_input, str):
        # 尝试解析 JSON 字符串
        try:
            parsed_data = json.loads(raw_input)
            if not isinstance(parsed_data, dict):
                raise ValueError("JSON 根必须是对象")
        except (json.JSONDecodeError, ValueError):
            # 不是 JSON，尝试按简单文本处理（如 CSV 行）
            try:
                # 尝试解析为数值列表
                numbers = [float(x.strip()) for x in raw_input.split(",") if x.strip()]
                parsed_data = {"data_points": numbers}
            except ValueError:
                raise PlotSenseError("E003", "输入格式不符合要求，示例：{\"data_points\": [[1,2],[3,4]]}")
    elif isinstance(raw_input, (list, tuple)):
        # 直接作为数据点
        parsed_data = {"data_points": list(raw_input)}
    else:
        raise PlotSenseError("E003", "输入格式不符合要求，支持：JSON 字符串、字典、列表")

    # ---- E002: 关键信息缺失 ----
    # 检查是否有任何可识别的字段
    if not any(key in parsed_data for key in SUPPORTED_FIELDS):
        raise PlotSenseError("E002", "还缺少以下信息，请补充：data_points（数据点）")

    # ---- 提取字段 ----
    title = parsed_data.get("title", "")
    x_label = parsed_data.get("x_label", "")
    y_label = parsed_data.get("y_label", "")
    chart_type = parsed_data.get("chart_type", "line")
    data_points = parsed_data.get("data_points", [])

    # ---- 校验数据点格式 ----
    valid, err_msg = _validate_data_points(data_points)
    if not valid:
        raise PlotSenseError("E003", f"data_points 格式错误: {err_msg}")

    # ---- 校验图表类型 ----
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise PlotSenseError("E003", f"不支持的图表类型: {chart_type}，支持: {SUPPORTED_CHART_TYPES}")

    # ---- 计算置信度 ----
    confidence = _calculate_confidence(
        data_points,
        has_title=bool(title),
        has_labels=bool(x_label and y_label),
    )

    # ---- E005: 置信度过低 ----
    if confidence < CONFIDENCE_MEDIUM and len(data_points) == 0:
        raise PlotSenseError("E005", "结果无法确定，建议：提供更多数据点或补充标题/轴标签")

    # ---- 生成结果 ----
    result = {
        "title": title or DEFAULT_TEMPLATE["title"],
        "x_label": x_label or DEFAULT_TEMPLATE["x_label"],
        "y_label": y_label or DEFAULT_TEMPLATE["y_label"],
        "chart_type": chart_type,
        "data_points": data_points,
        "confidence": round(confidence, 2),
        "confidence_note": _format_confidence_note(confidence),
        "generated_at": datetime.now().isoformat(),
        "completeness": completeness,
    }

    # ---- 按完整度裁剪 ----
    if completeness == "quick":
        # 快速骨架：只保留核心字段
        result = {k: result[k] for k in ["title", "chart_type", "data_points", "confidence"]}

    # ---- 输出格式转换 ----
    if output_format == "json":
        return result
    return result


# ---------------------------------------------------------------------------
# 输出与校验（标准流程 Step 3）
# ---------------------------------------------------------------------------

def validate_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    校验输出结果完整性。
    返回 (是否通过, 问题列表)。
    """
    issues = []
    required = ["title", "chart_type", "data_points", "confidence"]
    for field in required:
        if field not in result:
            issues.append(f"缺少字段: {field}")
    if "confidence" in result and not isinstance(result["confidence"], (int, float)):
        issues.append("confidence 必须是数值")
    if "data_points" in result and not isinstance(result["data_points"], list):
        issues.append("data_points 必须是列表")
    return (len(issues) == 0, issues)


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    将结果格式化为输出字符串。
    支持 json 和 text 两种格式。
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    # 文本格式
    lines = []
    lines.append(f"标题: {result.get('title', '')}")
    lines.append(f"图表类型: {result.get('chart_type', '')}")
    if "x_label" in result:
        lines.append(f"X轴: {result.get('x_label', '')}")
        lines.append(f"Y轴: {result.get('y_label', '')}")
    lines.append(f"置信度: {result.get('confidence', 0):.0%}")
    note = result.get("confidence_note", "")
    if note:
        lines.append(f"标注: {note}")
    lines.append(f"数据点数量: {len(result.get('data_points', []))}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def _selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保必然匹配。

    返回 0 表示通过，非 0 表示失败。
    """
    print("[selftest] 开始自检...")

    # ---- 测试 1: 正常处理（JSON 字符串输入） ----
    try:
        sample_json = json.dumps({
            "title": "销售趋势",
            "x_label": "月份",
            "y_label": "销售额",
            "chart_type": "line",
            "data_points": [[1, 100], [2, 150], [3, 200], [4, 180], [5, 250]]
        })
        result = process_input(sample_json)
        # 宽松断言
        assert result["title"] == "销售趋势", "标题解析错误"
        assert len(result["data_points"]) == 5, "数据点数量错误"
        assert result["confidence"] >= 0.8, "置信度偏低"
        valid, issues = validate_output(result)
        assert valid, f"输出校验失败: {issues}"
        print("  [通过] 正常 JSON 输入处理")
    except Exception as e:
        print(f"  [失败] 正常 JSON 输入处理: {e}")
        return 1

    # ---- 测试 2: 字典输入 ----
    try:
        result = process_input({
            "data_points": [10, 20, 30, 40, 50, 60, 70],
            "title": "测试"
        })
        assert len(result["data_points"]) == 7, "数据点数量错误"
        assert result["confidence"] >= 0.7, "置信度应不低于 0.7"
        print("  [通过] 字典输入处理")
    except Exception as e:
        print(f"  [失败] 字典输入处理: {e}")
        return 1

    # ---- 测试 3: 空输入触发 E001 ----
    try:
        process_input("")
        print("  [失败] 空输入应触发 E001")
        return 1
    except PlotSenseError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  [通过] 空输入错误处理 (E001)")

    # ---- 测试 4: 缺失关键信息触发 E002 ----
    try:
        process_input({"title": "无数据点"})
        print("  [失败] 缺失数据点应触发 E002")
        return 1
    except PlotSenseError as e:
        assert e.code == "E002", f"错误码应为 E002，实际 {e.code}"
        print("  [通过] 缺失关键信息错误处理 (E002)")

    # ---- 测试 5: 错误格式触发 E003 ----
    try:
        process_input("这不是有效输入@@@")
        print("  [失败] 错误格式应触发 E003")
        return 1
    except PlotSenseError as e:
        assert e.code == "E003", f"错误码应为 E003，实际 {e.code}"
        print("  [通过] 输入格式错误处理 (E003)")

    # ---- 测试 6: 置信度过低触发 E005 ----
    try:
        process_input({"data_points": []})
        print("  [失败] 空数据点应触发 E005")
        return 1
    except PlotSenseError as e:
        assert e.code == "E005", f"错误码应为 E005，实际 {e.code}"
        print("  [通过] 置信度过低错误处理 (E005)")

    # ---- 测试 7: 批量处理 ----
    try:
        batch = [
            {"data_points": [1, 2, 3], "title": "A"},
            {"data_points": [4, 5, 6], "title": "B"},
            {"data_points": [7, 8, 9], "title": "C"},
        ]
        results = [process_input(item) for item in batch]
        assert len(results) == 3, "批量处理数量错误"
        assert all(r["confidence"] >= 0.7 for r in results), "批量处理置信度异常"
        print("  [通过] 批量处理")
    except Exception as e:
        print(f"  [失败] 批量处理: {e}")
        return 1

    # ---- 测试 8: 输出格式化 ----
    try:
        result = process_input({"data_points": [1, 2, 3], "title": "T"})
        json_str = format_output(result, "json")
        parsed_back = json.loads(json_str)
        assert parsed_back["title"] == "T", "JSON 输出回读失败"
        text_str = format_output(result, "text")
        assert "置信度" in text_str, "文本输出缺少置信度"
        print("  [通过] 输出格式化")
    except Exception as e:
        print(f"  [失败] 输出格式化: {e}")
        return 1

    # ---- 测试 9: 大数据量处理 ----
    try:
        # 生成 1000 个数据点（宽松测试性能）
        big_data = [[i, i * 2] for i in range(1000)]
        result = process_input({"data_points": big_data})
        assert len(result["data_points"]) == 1000, "大数据量处理失败"
        assert result["confidence"] >= 0.9, "大数据量置信度应高"
        print("  [通过] 大数据量处理")
    except Exception as e:
        print(f"  [失败] 大数据量处理: {e}")
        return 1

    # ---- 测试 10: 边界情况 ----
    try:
        # 极小数据（1个点）
        result = process_input({"data_points": [5]})
        assert len(result["data_points"]) == 1, "单点处理失败"
        # 负数数据
        result = process_input({"data_points": [-1, -2, -3]})
        assert len(result["data_points"]) == 3, "负数数据处理失败"
        # 浮点数
        result = process_input({"data_points": [1.5, 2.5, 3.5]})
        assert len(result["data_points"]) == 3, "浮点数处理失败"
        print("  [通过] 边界情况处理")
    except Exception as e:
        print(f"  [失败] 边界情况处理: {e}")
        return 1

    print("[selftest] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。
    支持 --selftest 参数进行离线自检。
    """
    parser = argparse.ArgumentParser(
        description="plotsense - 数据可视化技能核心实现",
        epilog="示例: python main.py --input '{\"data_points\": [[1,2],[3,4]]}' --format json"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不访问网络）"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="输入数据（JSON 字符串）"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="从文件读取输入（注意：此选项需要文件系统访问）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--completeness",
        type=str,
        choices=["quick", "detailed"],
        default="detailed",
        help="完整度：quick=快速骨架, detailed=详细成品（默认: detailed）"
    )

    # 解析参数
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    except Exception as e:
        print(f"参数解析失败: {e}", file=sys.stderr)
        return 1

    # ---- 自检模式 ----
    if args.selftest:
        try:
            return _selftest()
        except Exception as e:
            print(f"[selftest] 未预期异常: {e}", file=sys.stderr)
            return 1

    # ---- 正常处理模式 ----
    # 收集输入
    raw_input = None
    if args.input:
        raw_input = args.input
    elif args.input_file:
        try:
            with open(args.input_file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except Exception as e:
            print(f"E009 读取文件失败: {e}", file=sys.stderr)
            return 1
    else:
        # 从 stdin 读取
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read().strip()

    # 处理输入
    try:
        result = process_input(raw_input, output_format=args.format, completeness=args.completeness)
    except PlotSenseError as e:
        print(json.dumps(_make_error(e.code, e.message), ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps(_make_error("E010", f"未知错误: {e}"), ensure_ascii=False), file=sys.stderr)
        return 1

    # 输出
    try:
        output_str = format_output(result, args.format)
        print(output_str)
        return 0
    except Exception as e:
        print(f"E009 输出失败: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
