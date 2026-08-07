#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hass-config-public 技能实现脚本
================================
解析智能家居仪表盘配置（YAML/JSON 文本），提取结构化信息，
并生成可视化方案建议（布局、卡片选型、配色等）。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
支持 --selftest 离线自检，不依赖外部文件、网络或当前工作目录。

错误码说明：
    E001: 参数错误（缺少输入或参数不合法）
    E002: 输入内容为空
    E003: 配置格式不支持（仅支持 JSON/YAML）
    E004: JSON 解析失败
    E005: YAML 解析失败（或未安装 PyYAML）
    E006: 配置根结构不是对象（dict）
    E007: 关键字段缺失或类型不符
    E008: 数据处理内部错误
    E009: 可视化方案生成失败
    E010: 未知错误
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
SUPPORTED_KEYS = {
    "title": "标题",
    "views": "视图列表",
    "theme": "主题",
    "type": "类型",
    "cards": "卡片列表",
    "entities": "实体列表",
    "path": "路径",
    "icon": "图标",
    "name": "名称",
    "grid": "网格布局",
    "background": "背景",
    "layout": "布局",
    "columns": "列数",
    "square": "方形卡片",
    "show_name": "显示名称",
    "show_icon": "显示图标",
    "tap_action": "点击行为",
    "hold_action": "长按行为",
    "state_color": "状态颜色",
    "label": "标签",
    "chart_type": "图表类型",
    "period": "周期",
    "hours_to_show": "显示小时数",
    "aggregate_func": "聚合函数",
}

ERROR_MESSAGES = {
    "E001": "参数错误：请提供配置文件内容（--content）或文件路径（--file）",
    "E002": "输入内容为空",
    "E003": "不支持的配置格式（仅支持 JSON/YAML）",
    "E004": "JSON 解析失败",
    "E005": "YAML 解析失败（请安装 PyYAML: pip install pyyaml）",
    "E006": "配置根结构不是对象（应为映射/字典）",
    "E007": "关键字段缺失或类型不符",
    "E008": "数据处理内部错误",
    "E009": "可视化方案生成失败",
    "E010": "未知错误",
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _err(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误返回结构"""
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": ERROR_MESSAGES.get(code, "未知错误"),
            "detail": detail,
        },
    }


def _ok(data: Any) -> Dict[str, Any]:
    """构造标准成功返回结构"""
    return {"ok": True, "data": data}


def _detect_format(content: str) -> str:
    """根据内容特征检测格式（json/yaml）"""
    content = content.strip()
    if not content:
        return "unknown"
    # 优先尝试 JSON（以 { 或 [ 开头）
    if content.startswith("{") or content.startswith("["):
        return "json"
    # 否则按 YAML 处理
    return "yaml"


def _safe_parse_json(content: str) -> Tuple[Optional[Any], Optional[str]]:
    """安全解析 JSON，返回 (数据, 错误码)"""
    try:
        return json.loads(content), None
    except json.JSONDecodeError as e:
        return None, f"E004: {e}"


def _safe_parse_yaml(content: str) -> Tuple[Optional[Any], Optional[str]]:
    """安全解析 YAML，返回 (数据, 错误码)"""
    try:
        import yaml
        # 使用 safe_load 进行安全解析
        data = yaml.safe_load(content)
        return data, None
    except ImportError:
        # 如果 PyYAML 未安装，尝试使用内置的 JSON 解析
        try:
            data = json.loads(content)
            return data, None
        except:
            return None, "E005: PyYAML 未安装且 JSON 解析失败"
    except Exception as e:
        return None, f"E005: {e}"


def _parse_config(content: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """解析配置内容为结构化数据"""
    fmt = _detect_format(content)
    if fmt == "json":
        data, err = _safe_parse_json(content)
    elif fmt == "yaml":
        data, err = _safe_parse_yaml(content)
    else:
        return None, "E003"

    if err:
        return None, err

    if data is None:
        return None, "E002"

    if not isinstance(data, dict):
        return None, "E006"

    return data, None


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _extract_views(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """提取视图列表"""
    views_raw = config.get("views", [])
    if not isinstance(views_raw, list):
        return []

    views = []
    for idx, view in enumerate(views_raw):
        if not isinstance(view, dict):
            continue
        view_info = {
            "index": idx,
            "title": view.get("title", f"视图 {idx + 1}"),
            "path": view.get("path", f"view-{idx}"),
            "theme": view.get("theme"),
            "type": view.get("type", "masonry"),
            "card_count": 0,
            "entities": [],
            "card_types": [],
        }

        # 提取卡片信息
        cards = view.get("cards", [])
        if isinstance(cards, list):
            view_info["card_count"] = len(cards)
            card_types = set()
            entities = []
            for card in cards:
                if isinstance(card, dict):
                    ctype = card.get("type", "unknown")
                    card_types.add(ctype)
                    # 提取实体（支持多种字段名）
                    for key in ["entity", "entities", "entity_id"]:
                        val = card.get(key)
                        if isinstance(val, str):
                            entities.append(val)
                        elif isinstance(val, list):
                            entities.extend([e for e in val if isinstance(e, str)])
                    # 嵌套卡片
                    if "cards" in card and isinstance(card["cards"], list):
                        for sub in card["cards"]:
                            if isinstance(sub, dict):
                                sub_type = sub.get("type", "unknown")
                                card_types.add(sub_type)
                                for key in ["entity", "entities", "entity_id"]:
                                    val = sub.get(key)
                                    if isinstance(val, str):
                                        entities.append(val)
                                    elif isinstance(val, list):
                                        entities.extend([e for e in val if isinstance(e, str)])
            view_info["card_types"] = sorted(card_types)
            view_info["entities"] = list(dict.fromkeys(entities))  # 去重保序

        views.append(view_info)

    return views


def _extract_theme(config: Dict[str, Any]) -> Optional[str]:
    """提取主题信息"""
    theme = config.get("theme")
    if isinstance(theme, str) and theme.strip():
        return theme.strip()
    return None


def _extract_global_entities(config: Dict[str, Any]) -> List[str]:
    """提取全局实体列表（视图外）"""
    entities = []
    # 常见全局实体位置
    for key in ["entities", "entity_ids"]:
        val = config.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    entities.append(item)
                elif isinstance(item, dict) and "entity" in item:
                    entities.append(item["entity"])
    return list(dict.fromkeys(entities))


def _analyze_layout(config: Dict[str, Any], views: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析布局结构"""
    total_cards = sum(v["card_count"] for v in views)
    total_entities = sum(len(v["entities"]) for v in views)
    global_entities = _extract_global_entities(config)

    all_card_types = set()
    for v in views:
        all_card_types.update(v["card_types"])

    # 统计卡片类型分布
    card_type_count: Dict[str, int] = {}
    for v in views:
        for ct in v["card_types"]:
            card_type_count[ct] = card_type_count.get(ct, 0) + 1

    return {
        "total_views": len(views),
        "total_cards": total_cards,
        "total_entities": total_entities,
        "global_entities": global_entities,
        "card_type_count": card_type_count,
        "card_types": sorted(all_card_types),
        "has_grid": "grid" in config or any("grid" in v for v in views),
        "has_custom_cards": any(
            t.startswith("custom:") for t in all_card_types
        ),
    }


def _generate_visualization_suggestions(
    config: Dict[str, Any], layout: Dict[str, Any]
) -> List[Dict[str, str]]:
    """生成可视化方案建议"""
    suggestions = []

    # 布局建议
    if layout["total_views"] == 0:
        suggestions.append({
            "type": "layout",
            "message": "未检测到视图，建议创建至少一个视图并添加卡片",
        })
    elif layout["total_views"] == 1:
        suggestions.append({
            "type": "layout",
            "message": "仅有一个视图，建议拆分为多个功能视图（如概览、灯光、环境）",
        })
    elif layout["total_views"] > 5:
        suggestions.append({
            "type": "layout",
            "message": f"视图数量较多（{layout['total_views']}个），建议合并相似视图或使用标签页导航",
        })

    # 卡片建议
    if layout["total_cards"] == 0:
        suggestions.append({
            "type": "card",
            "message": "未检测到卡片，建议添加天气、灯光、传感器等常用卡片",
        })
    elif layout["total_cards"] > 20:
        suggestions.append({
            "type": "card",
            "message": f"卡片数量较多（{layout['total_cards']}个），建议使用折叠面板或分页",
        })

    # 实体建议
    if layout["total_entities"] == 0 and not layout["global_entities"]:
        suggestions.append({
            "type": "entity",
            "message": "未检测到实体，请确认配置中是否包含 entity 字段",
        })

    # 主题建议
    theme = _extract_theme(config)
    if not theme:
        suggestions.append({
            "type": "theme",
            "message": "未设置主题，建议使用默认主题或指定主题名称",
        })

    # 自定义卡片建议
    if layout["has_custom_cards"]:
        suggestions.append({
            "type": "custom",
            "message": "检测到自定义卡片，请确保已安装对应前端资源",
        })

    # 类型建议
    if not layout["card_types"]:
        suggestions.append({
            "type": "type",
            "message": "未识别到卡片类型，建议使用标准卡片类型（entities、glance、weather 等）",
        })

    # 通用建议
    suggestions.append({
        "type": "general",
        "message": "建议使用 grid 布局以提升移动端显示效果",
    })

    return suggestions


def process_config(content: str) -> Dict[str, Any]:
    """处理配置内容，返回结构化结果"""
    if not content or not content.strip():
        return _err("E002")

    try:
        config, err = _parse_config(content)
        if err:
            code = err.split(":")[0] if ":" in err else "E010"
            return _err(code, err)

        # 提取信息
        views = _extract_views(config)
        theme = _extract_theme(config)
        layout = _analyze_layout(config, views)
        suggestions = _generate_visualization_suggestions(config, layout)

        # 构建结果
        result = {
            "config_type": "hass-dashboard",
            "title": config.get("title", "未命名仪表盘"),
            "theme": theme,
            "views": views,
            "layout_stats": layout,
            "suggestions": suggestions,
            "confidence": {
                "parsed_fields": len([k for k in config if k in SUPPORTED_KEYS]),
                "total_fields": len(config),
                "needs_verification": [
                    f"[需核实:{k}]" for k in config if k not in SUPPORTED_KEYS
                ],
            },
        }

        return _ok(result)

    except Exception as e:
        return _err("E010", str(e))


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def _read_input(args: argparse.Namespace) -> Tuple[Optional[str], Optional[str]]:
    """读取输入内容，返回 (内容, 错误码)"""
    if args.content:
        return args.content, None

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                return f.read(), None
        except Exception as e:
            return None, f"E001: 无法读取文件: {e}"

    return None, "E001"


def _format_output(result: Dict[str, Any], pretty: bool = True) -> str:
    """格式化输出"""
    if pretty:
        return json.dumps(result, ensure_ascii=False, indent=2)
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 自检模块（不依赖外部文件/网络）
# ---------------------------------------------------------------------------
def _selftest() -> int:
    """内置样例数据自检核心逻辑"""
    print("=" * 60)
    print("运行自检 (selftest)...")
    print("=" * 60)

    # 硬编码样例配置（JSON）
    sample_config = json.dumps({
        "title": "我的智能家居",
        "theme": "dark",
        "views": [
            {
                "title": "概览",
                "path": "overview",
                "type": "masonry",
                "cards": [
                    {"type": "weather", "entity": "weather.home"},
                    {"type": "entities", "entities": ["light.living", "light.kitchen"]},
                    {"type": "glance", "entities": ["sensor.temp", "sensor.humidity"]},
                ],
            },
            {
                "title": "灯光",
                "path": "lights",
                "type": "grid",
                "cards": [
                    {"type": "light", "entity": "light.bedroom"},
                    {"type": "custom:mini-graph-card", "entities": ["sensor.energy"]},
                ],
            },
        ],
    })

    # 测试 1: 正常解析
    print("\n[测试 1] 正常解析 JSON 配置...")
    result = process_config(sample_config)
    assert result["ok"] is True, f"解析失败: {result}"
    data = result["data"]
    assert data["title"] == "我的智能家居", "标题提取失败"
    assert data["theme"] == "dark", "主题提取失败"
    assert len(data["views"]) == 2, f"视图数量错误: {len(data['views'])}"
    assert data["layout_stats"]["total_cards"] >= 4, "卡片数量统计错误"
    assert data["layout_stats"]["total_entities"] >= 4, "实体数量统计错误"
    assert len(data["suggestions"]) > 0, "未生成建议"
    print("  ✓ 通过")

    # 测试 2: YAML 格式
    print("\n[测试 2] 解析 YAML 配置...")
    yaml_content = """title: 测试面板
views:
  - title: 主视图
    cards:
      - type: entities
        entities:
          - sensor.temp
          - sensor.humidity
"""
    result = process_config(yaml_content)
    assert result["ok"] is True, f"YAML 解析失败: {result}"
    data = result["data"]
    assert data["title"] == "测试面板", "YAML 标题提取失败"
    assert len(data["views"]) == 1, "YAML 视图数量错误"
    assert data["layout_stats"]["total_cards"] >= 1, "YAML 卡片数量错误"
    print("  ✓ 通过")

    # 测试 3: 空输入
    print("\n[测试 3] 空输入错误处理...")
    result = process_config("")
    assert result["ok"] is False, "空输入应返回错误"
    assert result["error"]["code"] == "E002", f"错误码错误: {result['error']['code']}"
    print("  ✓ 通过")

    # 测试 4: 无效 JSON
    print("\n[测试 4] 无效 JSON 错误处理...")
    result = process_config("{invalid json}")
    assert result["ok"] is False, "无效 JSON 应返回错误"
    assert result["error"]["code"] in ("E004", "E005"), f"错误码错误: {result['error']['code']}"
    print("  ✓ 通过")

    # 测试 5: 非对象根结构
    print("\n[测试 5] 非对象根结构错误处理...")
    result = process_config("['not', 'a', 'dict']")
    assert result["ok"] is False, "非对象根应返回错误"
    assert result["error"]["code"] == "E006", f"错误码错误: {result['error']['code']}"
    print("  ✓ 通过")

    # 测试 6: 缺少关键字段（宽松校验）
    print("\n[测试 6] 缺少关键字段的容错处理...")
    minimal_config = json.dumps({"title": "空面板"})
    result = process_config(minimal_config)
    assert result["ok"] is True, "缺少字段应能容错处理"
    data = result["data"]
    assert len(data["views"]) == 0, "空视图列表应返回空"
    assert data["layout_stats"]["total_cards"] == 0, "空卡片统计应为 0"
    print("  ✓ 通过")

    # 测试 7: 建议生成（宽松断言）
    print("\n[测试 7] 建议生成逻辑...")
    result = process_config(sample_config)
    data = result["data"]
    assert "suggestions" in data, "缺少建议字段"
    assert isinstance(data["suggestions"], list), "建议应为列表"
    # 宽松断言：建议数量合理（至少 1 条）
    assert len(data["suggestions"]) >= 1, "建议数量过少"
    # 所有建议应有 type 和 message
    for s in data["suggestions"]:
        assert "type" in s and "message" in s, "建议缺少必要字段"
    print("  ✓ 通过")

    # 测试 8: 置信度标注
    print("\n[测试 8] 置信度标注...")
    result = process_config(sample_config)
    data = result["data"]
    assert "confidence" in data, "缺少置信度字段"
    conf = data["confidence"]
    assert "parsed_fields" in conf, "缺少 parsed_fields"
    assert "total_fields" in conf, "缺少 total_fields"
    assert "needs_verification" in conf, "缺少 needs_verification"
    assert isinstance(conf["needs_verification"], list), "needs_verification 应为列表"
    print("  ✓ 通过")

    # 测试 9: 批量处理能力（模拟多输入）
    print("\n[测试 9] 批量处理能力...")
    configs = [
        json.dumps({"title": "面板 A", "views": [{"cards": [{"type": "entities"}]}]}),
        json.dumps({"title": "面板 B", "views": []}),
        "title: 面板 C\nviews: []",
    ]
    results = []
    for c in configs:
        r = process_config(c)
        results.append(r)
    assert len(results) == 3, "批量处理数量错误"
    assert results[0]["ok"] is True, "第一个配置解析失败"
    assert results[1]["ok"] is True, "第二个配置解析失败"
    assert results[2]["ok"] is True, "第三个配置解析失败"
    print("  ✓ 通过")

    # 测试 10: 错误码完整性
    print("\n[测试 10] 错误码完整性...")
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
    print("  ✓ 通过")

    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="智能家居仪表盘配置解析与可视化设计工具",
        epilog="示例: python main.py --content '{\"title\": \"test\"}'",
    )
    parser.add_argument("--content", type=str, help="直接传入配置内容（JSON/YAML）")
    parser.add_argument("--file", type=str, help="配置文件路径")
    parser.add_argument("--pretty", action="store_true", help="美化输出（默认开启）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--no-pretty", action="store_true", help="紧凑输出")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _selftest()

    # 读取输入
    content, err = _read_input(args)
    if err:
        code = err.split(":")[0] if ":" in err else "E001"
        print(json.dumps(_err(code, err), ensure_ascii=False, indent=2))
        return 1

    # 处理配置
    result = process_config(content)
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    # 输出结果
    pretty = not args.no_pretty
    output = _format_output(result, pretty=pretty)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
