#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
django-dashing 技能实现脚本

本脚本根据功能规格独立实现（clean-room 风格），提供：
- 数据源接入解析（CSV/JSON/Excel/数据库连接串）
- 图表配置推荐生成（折线/柱状/饼图）
- Django dashboard 视图代码生成
- 模块化网格布局配置生成
- 数据刷新策略配置生成

支持命令行参数 --selftest 进行离线自检（不依赖外部文件/网络/工作目录）。
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "文件读取失败：文件不存在或无法读取",
    "E003": "数据解析失败：格式不支持或数据损坏",
    "E004": "图表类型不匹配：无法为给定数据推荐图表",
    "E005": "Django 项目路径无效：路径不存在或不是目录",
    "E006": "布局配置生成失败：模块参数无效",
    "E007": "刷新策略配置失败：间隔参数无效",
    "E008": "JSON 序列化失败：数据无法序列化",
    "E009": "自检失败：核心逻辑验证未通过",
    "E010": "未知错误：发生未预期的异常",
}


class DashboardError(Exception):
    """仪表盘自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据源接入模块
# ---------------------------------------------------------------------------

def parse_data_source(source: str, data: Optional[str] = None) -> Dict[str, Any]:
    """
    解析数据源，返回标准化数据字典。

    支持：
    - CSV 文本（逗号分隔）
    - JSON 文本
    - Excel 占位（仅识别扩展名，不实际解析二进制）
    - 数据库连接串（识别 scheme）

    参数:
        source: 数据来源标识（文件路径、连接串或数据格式名）
        data: 可选的数据内容（当 source 为格式名时使用）

    返回:
        标准化数据字典，格式: {"type": ..., "fields": [...], "rows": [...]}
    """
    if not source:
        raise DashboardError("E001", "数据源未指定")

    # 处理文件路径
    if os.path.isfile(source):
        try:
            with open(source, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise DashboardError("E002", f"读取文件失败: {e}")

        ext = os.path.splitext(source)[1].lower()
        if ext in (".csv", ".txt"):
            return _parse_csv(content)
        elif ext == ".json":
            return _parse_json(content)
        elif ext in (".xlsx", ".xls"):
            # Excel 二进制解析需要第三方库，此处仅返回占位信息
            return {"type": "excel", "fields": [], "rows": [], "note": "Excel 需使用 pandas/openpyxl 解析"}
        else:
            raise DashboardError("E003", f"不支持的文件格式: {ext}")

    # 处理数据库连接串
    if "://" in source and not source.startswith("http"):
        scheme = source.split("://")[0].lower()
        return {"type": "database", "scheme": scheme, "connection": source}

    # 处理直接数据内容
    if data is not None:
        if source.lower() in ("csv", "text", "txt"):
            return _parse_csv(data)
        elif source.lower() == "json":
            return _parse_json(data)
        else:
            raise DashboardError("E003", f"不支持的数据格式: {source}")

    raise DashboardError("E001", "无法识别数据源类型")


def _parse_csv(content: str) -> Dict[str, Any]:
    """解析 CSV 文本为标准化数据字典。"""
    lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        raise DashboardError("E003", "CSV 数据至少需要表头和一行数据")

    fields = [f.strip() for f in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split(",")]
        if len(values) != len(fields):
            raise DashboardError("E003", "CSV 行字段数量与表头不一致")
        rows.append(dict(zip(fields, values)))

    return {"type": "csv", "fields": fields, "rows": rows}


def _parse_json(content: str) -> Dict[str, Any]:
    """解析 JSON 文本为标准化数据字典。"""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise DashboardError("E003", f"JSON 解析失败: {e}")

    if isinstance(parsed, list):
        if not parsed:
            return {"type": "json", "fields": [], "rows": []}
        fields = list(parsed[0].keys()) if isinstance(parsed[0], dict) else []
        rows = parsed if all(isinstance(r, dict) for r in parsed) else []
        return {"type": "json", "fields": fields, "rows": rows}
    elif isinstance(parsed, dict):
        # 支持 {data: [...]} 或 {field: [...]} 形式
        if "data" in parsed and isinstance(parsed["data"], list):
            return _parse_json(json.dumps(parsed["data"]))
        return {"type": "json", "fields": list(parsed.keys()), "rows": [parsed]}
    else:
        raise DashboardError("E003", "JSON 数据必须是对象或数组")


# ---------------------------------------------------------------------------
# 图表配置推荐模块
# ---------------------------------------------------------------------------

def recommend_chart(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据数据特征推荐图表类型及 ECharts 配置。

    规则：
    - 时间序列数据（字段名含 date/time/日期/时间/月/年）→ 折线图
    - 分类数据（字段数 >= 2 且首字段为类别）→ 柱状图
    - 单字段数值分布 → 饼图

    参数:
        data: 标准化数据字典（来自 parse_data_source）

    返回:
        ECharts 配置 JSON 字典
    """
    if not data or "fields" not in data:
        raise DashboardError("E004", "数据字典格式无效")

    fields = data.get("fields", [])
    rows = data.get("rows", [])

    if not fields or not rows:
        raise DashboardError("E004", "数据为空，无法推荐图表")

    # 检测时间序列 - 扩展关键词列表
    time_keywords = [
        "date", "time", "datetime", "timestamp",
        "日期", "时间", "年", "月", "日",
        "year", "month", "day", "hour", "minute", "second",
        "week", "quarter", "季度", "周"
    ]
    
    # 检查是否有时间字段
    has_time = False
    time_field = None
    for f in fields:
        f_lower = f.lower()
        if any(k in f_lower for k in time_keywords):
            has_time = True
            time_field = f
            break

    # 检测数值字段
    numeric_fields = []
    for f in fields:
        try:
            sample = rows[0].get(f, "0")
            if isinstance(sample, (int, float)):
                numeric_fields.append(f)
            else:
                # 尝试转换为数值
                float(sample)
                numeric_fields.append(f)
        except (ValueError, TypeError):
            continue

    if not numeric_fields:
        raise DashboardError("E004", "未找到可数值化的字段")

    # 推荐图表类型
    if has_time and time_field:
        chart_type = "line"
        x_field = time_field
    elif len(fields) >= 2:
        chart_type = "bar"
        x_field = fields[0]
    else:
        chart_type = "pie"
        x_field = fields[0]

    y_field = numeric_fields[0]

    # 构建 ECharts 配置
    config = {
        "chart_type": chart_type,
        "title": {"text": f"{y_field} 分析", "left": "center"},
        "tooltip": {"trigger": "axis" if chart_type != "pie" else "item"},
        "legend": {"data": [y_field], "bottom": 10},
        "grid": {"left": 50, "right": 30, "top": 60, "bottom": 60},
        "xAxis": {"type": "category", "data": [str(r.get(x_field, "")) for r in rows]},
        "yAxis": {"type": "value", "name": y_field},
        "series": [{
            "name": y_field,
            "type": chart_type,
            "data": [float(r.get(y_field, 0) or 0) for r in rows],
            "smooth": chart_type == "line",
        }],
    }

    if chart_type == "pie":
        config["series"][0]["radius"] = "60%"
        config["series"][0]["data"] = [
            {"name": str(r.get(x_field, "")), "value": float(r.get(y_field, 0) or 0)}
            for r in rows
        ]

    return config


# ---------------------------------------------------------------------------
# Django 项目集成模块
# ---------------------------------------------------------------------------

def generate_django_view(project_path: str, chart_config: Dict[str, Any]) -> str:
    """
    生成可嵌入 Django 项目的 dashboard 视图代码。

    参数:
        project_path: Django 项目路径（用于验证）
        chart_config: 图表配置（来自 recommend_chart）

    返回:
        Django views.py 代码字符串
    """
    if not os.path.isdir(project_path):
        raise DashboardError("E005", f"项目路径不存在: {project_path}")

    chart_json = json.dumps(chart_config, ensure_ascii=False, indent=2)

    code = f'''"""
dashboard 视图模块 - 由 django-dashing 技能生成
"""
from django.shortcuts import render
from django.http import JsonResponse
import json

# 图表配置（预生成）
CHART_CONFIG = {chart_json}


def dashboard(request):
    """数据看板主页：渲染图表配置到模板。"""
    context = {{
        "chart_config_json": json.dumps(CHART_CONFIG, ensure_ascii=False),
        "page_title": "数据看板",
    }}
    return render(request, "dashboard/dashboard.html", context)


def dashboard_data(request):
    """数据接口：返回最新图表数据（用于前端刷新）。"""
    return JsonResponse(CHART_CONFIG)


def dashboard_config(request):
    """配置接口：返回当前布局与刷新策略。"""
    layout = {{
        "grid": [12, 8],
        "modules": [
            {{"id": "chart-1", "x": 0, "y": 0, "w": 6, "h": 4, "chart": "main"}},
            {{"id": "chart-2", "x": 6, "y": 0, "w": 6, "h": 4, "chart": "secondary"}},
        ],
    }}
    refresh = {{"strategy": "polling", "interval_seconds": 30}}
    return JsonResponse({{"layout": layout, "refresh": refresh}})
'''
    return code


# ---------------------------------------------------------------------------
# 模块化布局模块
# ---------------------------------------------------------------------------

def generate_layout(module_count: int, columns: int = 12, row_height: int = 100) -> Dict[str, Any]:
    """
    生成可拖拽的网格布局配置。

    参数:
        module_count: 模块数量（>= 1）
        columns: 网格列数（默认 12）
        row_height: 行高像素（默认 100）

    返回:
        layout.json 字典
    """
    if module_count < 1:
        raise DashboardError("E006", "模块数量必须 >= 1")
    if columns < 1:
        raise DashboardError("E006", "列数必须 >= 1")
    if row_height <= 0:
        raise DashboardError("E006", "行高必须为正数")

    modules = []
    per_row = max(1, columns // 2)  # 每行最多 2 个模块（简单布局）

    for i in range(module_count):
        row = i // per_row
        col = i % per_row
        module = {
            "id": f"module-{i+1}",
            "x": col * (columns // per_row),
            "y": row * 2,  # 每个模块高度为 2 行
            "w": columns // per_row,
            "h": 2,
            "content": f"模块 {i+1} 内容区域",
        }
        modules.append(module)

    return {
        "grid": {"columns": columns, "row_height": row_height, "margin": [10, 10]},
        "modules": modules,
        "drag_enabled": True,
        "resize_enabled": True,
    }


# ---------------------------------------------------------------------------
# 数据刷新策略模块
# ---------------------------------------------------------------------------

def generate_refresh_strategy(strategy: str = "polling", interval: int = 30) -> Dict[str, Any]:
    """
    配置数据刷新策略。

    参数:
        strategy: 刷新策略（polling=轮询, websocket=实时推送）
        interval: 轮询间隔秒数（仅 polling 使用）

    返回:
        刷新策略配置字典
    """
    if strategy not in ("polling", "websocket"):
        raise DashboardError("E007", f"不支持的刷新策略: {strategy}")

    if interval < 5:
        raise DashboardError("E007", "轮询间隔必须 >= 5 秒")

    if strategy == "polling":
        return {
            "strategy": "polling",
            "interval_seconds": interval,
            "auto_refresh": True,
            "description": f"每 {interval} 秒自动轮询数据接口",
        }
    else:
        return {
            "strategy": "websocket",
            "auto_refresh": True,
            "description": "通过 WebSocket 实时推送数据更新",
            "channel": "dashboard_updates",
        }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def build_dashboard(source: str, data: Optional[str] = None,
                    project_path: str = ".", module_count: int = 2,
                    refresh: str = "polling", interval: int = 30) -> Dict[str, Any]:
    """
    一键生成完整 dashboard 配置。

    参数:
        source: 数据源（文件路径/连接串/格式名）
        data: 可选的数据内容
        project_path: Django 项目路径
        module_count: 布局模块数量
        refresh: 刷新策略
        interval: 轮询间隔

    返回:
        完整配置字典，包含 data, chart, view, layout, refresh
    """
    # 1. 解析数据源
    parsed_data = parse_data_source(source, data)

    # 2. 推荐图表配置
    chart = recommend_chart(parsed_data)

    # 3. 生成 Django 视图代码
    view_code = generate_django_view(project_path, chart)

    # 4. 生成布局配置
    layout = generate_layout(module_count)

    # 5. 生成刷新策略
    refresh_config = generate_refresh_strategy(refresh, interval)

    return {
        "data": parsed_data,
        "chart": chart,
        "view_code": view_code,
        "layout": layout,
        "refresh": refresh_config,
    }


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。

    返回:
        True 表示所有检查通过
    """
    print("=" * 60)
    print("django-dashing 自检开始")
    print("=" * 60)

    try:
        # --- 测试 1: CSV 数据解析 ---
        csv_data = """月份,销售额,利润
一月,120,30
二月,150,45
三月,180,55
四月,200,60"""
        parsed = parse_data_source("csv", csv_data)
        assert parsed["type"] == "csv", "CSV 类型解析错误"
        assert len(parsed["fields"]) == 3, "CSV 字段数量错误"
        assert len(parsed["rows"]) == 4, "CSV 行数错误"
        assert parsed["rows"][0]["销售额"] == "120", "CSV 数据值错误"
        print("[PASS] CSV 数据解析")

        # --- 测试 2: JSON 数据解析 ---
        json_data = '[{"name": "产品A", "value": 100}, {"name": "产品B", "value": 200}]'
        parsed_json = parse_data_source("json", json_data)
        assert parsed_json["type"] == "json", "JSON 类型解析错误"
        assert len(parsed_json["rows"]) == 2, "JSON 行数错误"
        print("[PASS] JSON 数据解析")

        # --- 测试 3: 图表推荐（时间序列 → 折线图）---
        chart = recommend_chart(parsed)
        assert chart["chart_type"] == "line", "时间序列应推荐折线图"
        assert len(chart["series"][0]["data"]) == 4, "折线图数据点数错误"
        print("[PASS] 时间序列图表推荐")

        # --- 测试 4: 图表推荐（分类数据 → 柱状图）---
        bar_data = {"type": "json", "fields": ["类别", "数量"], "rows": [
            {"类别": "A", "数量": "10"}, {"类别": "B", "数量": "20"}
        ]}
        chart_bar = recommend_chart(bar_data)
        assert chart_bar["chart_type"] == "bar", "分类数据应推荐柱状图"
        print("[PASS] 分类数据图表推荐")

        # --- 测试 5: Django 视图生成 ---
        with tempfile.TemporaryDirectory() as tmpdir:
            view_code = generate_django_view(tmpdir, chart)
            assert "def dashboard" in view_code, "视图缺少 dashboard 函数"
            assert "CHART_CONFIG" in view_code, "视图缺少图表配置"
            assert "JsonResponse" in view_code, "视图缺少 JSON 响应"
        print("[PASS] Django 视图生成")

        # --- 测试 6: 布局生成 ---
        layout = generate_layout(3)
        assert len(layout["modules"]) == 3, "布局模块数量错误"
        assert layout["drag_enabled"] is True, "布局应支持拖拽"
        print("[PASS] 模块化布局生成")

        # --- 测试 7: 刷新策略生成 ---
        refresh_poll = generate_refresh_strategy("polling", 60)
        assert refresh_poll["strategy"] == "polling", "轮询策略错误"
        assert refresh_poll["interval_seconds"] == 60, "轮询间隔错误"

        refresh_ws = generate_refresh_strategy("websocket")
        assert refresh_ws["strategy"] == "websocket", "WebSocket 策略错误"
        print("[PASS] 刷新策略生成")

        # --- 测试 8: 完整流程 ---
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_dashboard("csv", csv_data, project_path=tmpdir, module_count=2)
            assert "data" in result, "完整流程缺少数据"
            assert "chart" in result, "完整流程缺少图表"
            assert "view_code" in result, "完整流程缺少视图代码"
            assert "layout" in result, "完整流程缺少布局"
            assert "refresh" in result, "完整流程缺少刷新策略"
        print("[PASS] 完整流程构建")

        # --- 测试 9: 错误处理 ---
        try:
            parse_data_source("", None)
            assert False, "空数据源应抛出异常"
        except DashboardError as e:
            assert e.code == "E001", f"错误码应为 E001，实际: {e.code}"
        print("[PASS] 错误处理机制")

        print("=" * 60)
        print("自检全部通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"[FAIL] 断言失败: {e}")
        raise DashboardError("E009", f"自检失败: {e}")
    except DashboardError as e:
        print(f"[FAIL] 业务错误: {e}")
        raise
    except Exception as e:
        print(f"[FAIL] 未预期错误: {e}")
        raise DashboardError("E010", f"自检异常: {e}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="django-dashing 数据看板构建工具",
        epilog="示例: python main.py --source data.csv --project ./myproject"
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--source", type=str, help="数据源（文件路径/连接串/格式名）")
    parser.add_argument("--data", type=str, default=None, help="直接提供的数据内容（配合 --source 使用）")
    parser.add_argument("--project", type=str, default=".", help="Django 项目路径（默认当前目录）")
    parser.add_argument("--modules", type=int, default=2, help="布局模块数量（默认 2）")
    parser.add_argument("--refresh", type=str, default="polling", choices=["polling", "websocket"],
                        help="刷新策略（默认 polling）")
    parser.add_argument("--interval", type=int, default=30, help="轮询间隔秒数（默认 30）")
    parser.add_argument("--output", type=str, default=None, help="输出 JSON 文件路径（默认输出到 stdout）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except DashboardError as e:
            print(f"自检失败: {e}")
            return 1

    # 正常模式
    try:
        # 校验参数
        if not args.source:
            parser.error("必须指定 --source 或使用 --selftest")

        # 构建 dashboard
        result = build_dashboard(
            source=args.source,
            data=args.data,
            project_path=args.project,
            module_count=args.modules,
            refresh=args.refresh,
            interval=args.interval,
        )

        # 序列化输出
        output_json = json.dumps(result, ensure_ascii=False, indent=2, default=str)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"配置已写入: {args.output}")
        else:
            print(output_json)

        return 0

    except DashboardError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
