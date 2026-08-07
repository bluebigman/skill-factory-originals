#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 智能家居仪表盘配置解析与可视化设计工具

功能概述：
    解析智能家居仪表盘配置（YAML/JSON/URL），提取结构化信息，
    并生成可视化方案建议。支持批量处理、置信度标注。

仅依据功能规格独立实现（clean-room）。
"""

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "配置文件格式不支持（仅支持 YAML/JSON/URL）",
    "E003": "配置文件内容无法解析",
    "E004": "配置文件结构不符合预期（缺少必要字段）",
    "E005": "批量处理时单个文件解析失败",
    "E006": "URL 访问失败",
    "E007": "内部逻辑错误（未预期分支）",
    "E008": "命令行参数错误",
    "E009": "输出写入失败",
    "E010": "自检测试失败",
}


def error_exit(code: str, message: str = "") -> None:
    """输出错误信息并以非零状态退出。"""
    desc = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"错误 [{code}] {desc}: {message}", file=sys.stderr)
    else:
        print(f"错误 [{code}] {desc}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------
def safe_json_loads(text: str):
    """安全解析 JSON 文本，失败返回 None。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def safe_yaml_loads(text: str):
    """极简 YAML 解析器（仅支持本技能所需子集）。

    支持：
        - 键值对（key: value）
        - 列表（- item）
        - 嵌套字典（缩进）
        - 注释（# 开头）
        - 引号字符串
    不支持：
        - 复杂锚点、多行字符串等高级特性
    """
    result = {}
    lines = text.splitlines()
    stack = []  # 维护 (缩进, 字典) 的栈

    for line in lines:
        # 去除注释（不在引号内）
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 简单处理引号内的 # 
        in_quote = False
        for i, ch in enumerate(line):
            if ch == '"' or ch == "'":
                in_quote = not in_quote
            if ch == "#" and not in_quote:
                line = line[:i]
                break

        indent = len(line) - len(line.lstrip())
        content = line.strip()

        if not content:
            continue

        # 列表项
        if content.startswith("- "):
            item = content[2:].strip()
            # 去掉引号
            if (item.startswith('"') and item.endswith('"')) or \
               (item.startswith("'") and item.endswith("'")):
                item = item[1:-1]
            # 找到当前缩进对应的父字典
            while stack and stack[-1][0] >= indent:
                stack.pop()
            if not stack:
                # 顶层列表
                result.setdefault("_top_list", []).append(item)
            else:
                parent = stack[-1][1]
                key = stack[-1][2]
                if key not in parent or not isinstance(parent[key], list):
                    parent[key] = []
                parent[key].append(item)
            continue

        # 键值对
        if ":" in content:
            key, _, value = content.partition(":")
            key = key.strip()
            value = value.strip()

            # 去掉引号
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            # 布尔和数字转换
            if value == "true":
                value = True
            elif value == "false":
                value = False
            elif value == "null" or value == "~":
                value = None
            else:
                try:
                    if "." in value:
                        value = float(value)
                    elif value:
                        value = int(value)
                except ValueError:
                    pass

            # 找到父字典
            while stack and stack[-1][0] >= indent:
                stack.pop()

            if not stack:
                parent = result
            else:
                parent = stack[-1][1]

            parent[key] = value
            stack.append((indent, parent, key))

    return result


def parse_config(text: str, source_type: str = "auto"):
    """解析配置文本为结构化数据。

    source_type: auto / yaml / json
    """
    if source_type == "auto":
        # 尝试 JSON 优先
        data = safe_json_loads(text)
        if data is not None:
            return data, "json"
        # 尝试 YAML
        data = safe_yaml_loads(text)
        if data:
            return data, "yaml"
        return None, "unknown"

    if source_type == "json":
        data = safe_json_loads(text)
        return data, "json"

    if source_type == "yaml":
        data = safe_yaml_loads(text)
        return data, "yaml"

    return None, "unknown"


def fetch_url_content(url: str):
    """从 URL 获取文本内容。"""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        error_exit("E006", f"无法访问 URL {url}: {exc}")


# ---------------------------------------------------------------------------
# 核心分析逻辑
# ---------------------------------------------------------------------------
def analyze_entities(config):
    """提取实体列表及统计信息。"""
    entities = []

    def _walk(obj):
        if isinstance(obj, dict):
            # 直接实体字段
            if "entity" in obj and isinstance(obj["entity"], str):
                entities.append(obj["entity"])
            # entities 列表
            if "entities" in obj and isinstance(obj["entities"], list):
                for ent in obj["entities"]:
                    if isinstance(ent, str):
                        entities.append(ent)
                    elif isinstance(ent, dict) and "entity" in ent:
                        entities.append(ent["entity"])
            # 递归
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(config)

    # 去重并统计
    entity_counter = Counter(entities)
    unique_entities = list(entity_counter.keys())
    return unique_entities, entity_counter


def analyze_card_types(config):
    """统计卡片类型分布。"""
    card_types = []

    def _walk(obj):
        if isinstance(obj, dict):
            if "type" in obj and isinstance(obj["type"], str):
                card_types.append(obj["type"])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(config)
    return Counter(card_types)


def analyze_layout(config):
    """分析布局结构。"""
    layout_info = {
        "has_grid": False,
        "has_panel": False,
        "has_sections": False,
        "view_count": 0,
        "card_count": 0,
    }

    # 视图数量
    if isinstance(config, dict):
        if "views" in config and isinstance(config["views"], list):
            layout_info["view_count"] = len(config["views"])
            # 遍历视图内容
            for view in config["views"]:
                if isinstance(view, dict):
                    if "cards" in view:
                        layout_info["card_count"] += len(view["cards"])
                    if "type" in view:
                        if view["type"] == "panel":
                            layout_info["has_panel"] = True
                        if view["type"] == "sections":
                            layout_info["has_sections"] = True
        # 顶层卡片
        if "cards" in config and isinstance(config["cards"], list):
            layout_info["card_count"] += len(config["cards"])

    # 检测 grid 类型
    def _detect_grid(obj):
        if isinstance(obj, dict):
            if obj.get("type") == "grid":
                layout_info["has_grid"] = True
            for v in obj.values():
                _detect_grid(v)
        elif isinstance(obj, list):
            for item in obj:
                _detect_grid(item)

    _detect_grid(config)
    return layout_info


def analyze_theme(config):
    """分析主题设置。"""
    theme_info = {
        "theme_name": None,
        "has_dark_mode": False,
        "has_custom_colors": False,
        "background": None,
    }

    if isinstance(config, dict):
        # 顶层主题
        if "theme" in config:
            theme_info["theme_name"] = config["theme"]

        # 背景
        if "background" in config:
            theme_info["background"] = config["background"]

        # 检测暗色模式相关
        theme_text = json.dumps(config).lower()
        if "dark" in theme_text or "night" in theme_text:
            theme_info["has_dark_mode"] = True

        # 自定义颜色检测
        if "color" in theme_text or "colour" in theme_text:
            theme_info["has_custom_colors"] = True

    return theme_info


def generate_visualization_suggestions(config):
    """生成可视化方案建议。"""
    suggestions = []
    card_types = analyze_card_types(config)
    layout_info = analyze_layout(config)

    # 卡片类型建议
    if "entities" in card_types or "entity" in card_types:
        suggestions.append("检测到实体卡片，建议使用 `glance` 卡片展示关键实体状态，"
                           "或使用 `entities` 卡片分组管理。")

    if "history-graph" in card_types or "history" in card_types:
        suggestions.append("检测到历史图表卡片，建议结合 `statistics-graph` 展示长期趋势。")

    if "map" in card_types:
        suggestions.append("检测到地图卡片，建议调整缩放级别和主题色以提升可读性。")

    if "gauge" in card_types:
        suggestions.append("检测到仪表盘卡片，建议统一量程和单位，保持视觉一致性。")

    # 布局建议
    if layout_info["view_count"] == 0:
        suggestions.append("未检测到视图（views）配置，建议按功能区域划分多个视图。")
    elif layout_info["view_count"] > 5:
        suggestions.append(f"视图数量较多（{layout_info['view_count']} 个），"
                           "建议合并相似视图或使用子视图组织。")

    if not layout_info["has_grid"] and layout_info["card_count"] > 4:
        suggestions.append("卡片数量较多且未使用 grid 布局，建议使用 `grid` 卡片"
                           "进行网格化排列，提升空间利用率。")

    if not layout_info["has_sections"]:
        suggestions.append("未使用 sections 视图，建议考虑 sections 布局实现更灵活的响应式设计。")

    # 主题建议
    theme_info = analyze_theme(config)
    if not theme_info["theme_name"]:
        suggestions.append("未设置主题，建议配置统一的主题名称以保持风格一致。")
    if not theme_info["has_dark_mode"]:
        suggestions.append("未检测到暗色模式配置，建议在主题中增加 dark 变体以适配夜间使用。")

    # 通用建议
    suggestions.append("建议为常用操作添加快捷按钮，减少页面跳转。")
    suggestions.append("建议定期检查实体状态，移除失效实体以提升加载性能。")

    # 返回前 5 条建议
    return suggestions[:5]


def analyze_config_full(config):
    """完整分析配置，返回结构化结果。"""
    result = {
        "summary": {},
        "entities": [],
        "card_types": {},
        "layout": {},
        "theme": {},
        "suggestions": [],
        "warnings": [],
    }

    # 基本信息
    if isinstance(config, dict):
        result["summary"]["title"] = config.get("title", config.get("name", "未命名仪表盘"))
        result["summary"]["description"] = config.get("description", "")
    else:
        result["summary"]["title"] = "未命名仪表盘"
        result["summary"]["description"] = ""

    # 实体分析
    entities, entity_counter = analyze_entities(config)
    result["entities"] = entities
    result["summary"]["entity_count"] = len(entities)

    # 卡片类型
    card_counter = analyze_card_types(config)
    result["card_types"] = dict(card_counter.most_common())
    result["summary"]["card_type_count"] = len(card_counter)

    # 布局分析
    result["layout"] = analyze_layout(config)
    result["summary"]["view_count"] = result["layout"]["view_count"]
    result["summary"]["card_count"] = result["layout"]["card_count"]

    # 主题分析
    result["theme"] = analyze_theme(config)

    # 建议
    result["suggestions"] = generate_visualization_suggestions(config)

    # 置信度标注（对不确定字段）
    if not result["summary"]["title"]:
        result["warnings"].append("[需核实:title] 未找到仪表盘标题")

    if not result["entities"]:
        result["warnings"].append("[需核实:entities] 未提取到任何实体")

    if not result["card_types"]:
        result["warnings"].append("[需核实:card_types] 未识别到卡片类型")

    return result


# ---------------------------------------------------------------------------
# 处理函数
# ---------------------------------------------------------------------------
def process_config_text(text: str, source_name: str = "config"):
    """处理单个配置文本。"""
    config, fmt = parse_config(text)

    if config is None:
        error_exit("E003", f"无法解析 {source_name}")

    result = analyze_config_full(config)
    result["source"] = source_name
    result["format"] = fmt
    return result


def process_file(filepath: str):
    """处理配置文件。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as exc:
        error_exit("E001", f"读取文件失败 {filepath}: {exc}")

    return process_config_text(text, filepath)


def process_url(url: str):
    """处理 URL 配置。"""
    text = fetch_url_content(url)
    return process_config_text(text, url)


def process_input(source: str):
    """根据输入类型处理（文件/URL/原始文本）。"""
    # URL 检测
    if source.startswith(("http://", "https://")):
        return process_url(source)

    # 文件检测
    if source.endswith((".yaml", ".yml", ".json")):
        try:
            return process_file(source)
        except SystemExit:
            raise
        except Exception:
            # 不是有效文件路径，尝试作为原始文本处理
            pass

    # 原始文本
    return process_config_text(source, "stdin")


def format_output(result):
    """格式化输出结果。"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"📊 仪表盘分析报告: {result['summary']['title']}")
    lines.append("=" * 60)

    # 摘要
    lines.append("\n【摘要】")
    lines.append(f"  格式: {result.get('format', 'unknown')}")
    lines.append(f"  实体数量: {result['summary']['entity_count']}")
    lines.append(f"  卡片类型数: {result['summary']['card_type_count']}")
    lines.append(f"  视图数量: {result['summary']['view_count']}")
    lines.append(f"  卡片总数: {result['summary']['card_count']}")

    # 实体列表
    if result["entities"]:
        lines.append("\n【实体列表】")
        for ent in result["entities"][:20]:  # 最多显示 20 个
            lines.append(f"  - {ent}")
        if len(result["entities"]) > 20:
            lines.append(f"  ... 等 {len(result['entities'])} 个实体")

    # 卡片类型
    if result["card_types"]:
        lines.append("\n【卡片类型分布】")
        for ctype, count in list(result["card_types"].items())[:10]:
            lines.append(f"  {ctype}: {count}")

    # 布局
    lines.append("\n【布局分析】")
    layout = result["layout"]
    lines.append(f"  使用 Grid: {'是' if layout['has_grid'] else '否'}")
    lines.append(f"  使用 Panel: {'是' if layout['has_panel'] else '否'}")
    lines.append(f"  使用 Sections: {'是' if layout['has_sections'] else '否'}")

    # 主题
    lines.append("\n【主题分析】")
    theme = result["theme"]
    lines.append(f"  主题名称: {theme['theme_name'] or '未设置'}")
    lines.append(f"  暗色模式: {'是' if theme['has_dark_mode'] else '否'}")
    lines.append(f"  自定义颜色: {'是' if theme['has_custom_colors'] else '否'}")

    # 建议
    if result["suggestions"]:
        lines.append("\n【可视化建议】")
        for i, sug in enumerate(result["suggestions"], 1):
            lines.append(f"  {i}. {sug}")

    # 警告
    if result["warnings"]:
        lines.append("\n【警告/需核实】")
        for warn in result["warnings"]:
            lines.append(f"  ⚠️ {warn}")

    lines.append("\n" + "=" * 60)
    lines.append("分析完成。以上建议仅供参考，请结合实际环境验证。")
    lines.append("=" * 60)

    return "\n".join(lines)


def output_result(result, output_file=None):
    """输出结果到文件或标准输出。"""
    text = format_output(result)
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"结果已写入: {output_file}")
        except Exception as exc:
            error_exit("E009", f"写入文件失败: {exc}")
    else:
        print(text)


def batch_process(sources, output_dir=None):
    """批量处理多个配置。"""
    results = []
    for i, source in enumerate(sources, 1):
        print(f"\n[{i}/{len(sources)}] 处理: {source}", file=sys.stderr)
        try:
            result = process_input(source)
            results.append(result)
            output_result(result)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"错误 [E005] 批量处理失败: {source} - {exc}", file=sys.stderr)
            results.append({"error": str(exc), "source": source})

    return results


# ---------------------------------------------------------------------------
# 自检测试
# ---------------------------------------------------------------------------
def selftest():
    """内置硬编码样例数据离线自检核心逻辑。"""
    print("🔍 运行自检测试...")

    # 硬编码测试配置（不依赖外部文件）
    test_config = {
        "title": "我的智能家居",
        "views": [
            {
                "title": "客厅",
                "type": "sections",
                "cards": [
                    {"type": "entities", "entities": ["light.living_room", "switch.tv"]},
                    {"type": "gauge", "entity": "sensor.temperature"},
                    {"type": "history-graph", "entities": ["sensor.humidity"]},
                ],
            },
            {
                "title": "卧室",
                "type": "panel",
                "cards": [
                    {"type": "glance", "entities": ["light.bedroom", "switch.fan"]},
                ],
            },
        ],
        "theme": "dark_theme",
        "background": "var(--background)",
    }

    # 文本格式测试
    test_json = json.dumps(test_config)

    # 测试 1: JSON 解析
    config, fmt = parse_config(test_json, "json")
    assert config is not None, "JSON 解析失败"
    assert fmt == "json", f"格式识别错误: {fmt}"
    assert config["title"] == "我的智能家居", "标题解析错误"
    assert len(config["views"]) == 2, "视图数量错误"
    print("  ✅ JSON 解析测试通过")

    # 测试 2: 实体提取
    entities, counter = analyze_entities(config)
    assert len(entities) >= 4, f"实体提取数量不足: {len(entities)}"
    assert "light.living_room" in entities, "缺少 living_room 灯光实体"
    assert "sensor.temperature" in entities, "缺少温度传感器"
    assert counter["light.living_room"] == 1, "实体计数错误"
    print(f"  ✅ 实体提取测试通过 ({len(entities)} 个实体)")

    # 测试 3: 卡片类型统计
    card_counter = analyze_card_types(config)
    assert "entities" in card_counter, "缺少 entities 卡片类型"
    assert "gauge" in card_counter, "缺少 gauge 卡片类型"
    assert card_counter["entities"] >= 1, "entities 卡片计数错误"
    print(f"  ✅ 卡片类型统计测试通过 ({len(card_counter)} 种类型)")

    # 测试 4: 布局分析
    layout = analyze_layout(config)
    assert layout["view_count"] == 2, f"视图数量错误: {layout['view_count']}"
    assert layout["card_count"] >= 4, f"卡片数量错误: {layout['card_count']}"
    assert layout["has_sections"] is True, "未检测到 sections 布局"
    assert layout["has_panel"] is True, "未检测到 panel 布局"
    print("  ✅ 布局分析测试通过")

    # 测试 5: 主题分析
    theme = analyze_theme(config)
    assert theme["theme_name"] == "dark_theme", f"主题名称错误: {theme['theme_name']}"
    assert theme["has_dark_mode"] is True, "未检测到暗色模式"
    assert theme["background"] is not None, "背景未检测"
    print("  ✅ 主题分析测试通过")

    # 测试 6: 完整分析
    full_result = analyze_config_full(config)
    assert full_result["summary"]["entity_count"] >= 4, "完整分析实体数错误"
    assert full_result["summary"]["view_count"] == 2, "完整分析视图数错误"
    assert len(full_result["suggestions"]) >= 1, "未生成建议"
    assert len(full_result["suggestions"]) <= 5, "建议数量超出限制"
    print(f"  ✅ 完整分析测试通过 ({len(full_result['suggestions'])} 条建议)")

    # 测试 7: 建议生成
    suggestions = generate_visualization_suggestions(config)
    assert len(suggestions) >= 1, "建议生成为空"
    assert len(suggestions) <= 5, "建议数量过多"
    print(f"  ✅ 建议生成测试通过 ({len(suggestions)} 条建议)")

    # 测试 8: 简易 YAML 解析
    test_yaml = """
title: 测试面板
views:
  - title: 首页
    cards:
      - type: entities
        entities:
          - light.test
          - switch.test
"""
    yaml_config, yaml_fmt = parse_config(test_yaml, "yaml")
    assert yaml_config is not None, "YAML 解析失败"
    assert yaml_fmt == "yaml", "YAML 格式识别错误"
    assert yaml_config.get("title") == "测试面板", "YAML 标题错误"
    assert len(yaml_config.get("views", [])) == 1, "YAML 视图数量错误"
    print("  ✅ YAML 解析测试通过")

    # 测试 9: 宽松断言 - 数值范围
    assert 0 <= layout["view_count"] <= 10, "视图数量超出合理范围"
    assert 0 <= layout["card_count"] <= 100, "卡片数量超出合理范围"
    assert 0 <= len(entities) <= 1000, "实体数量超出合理范围"
    print("  ✅ 数值范围断言测试通过")

    # 测试 10: 错误处理测试
    bad_config = None
    try:
        process_config_text("not valid content{{{", "bad_config")
        assert False, "应抛出解析错误"
    except SystemExit:
        print("  ✅ 错误处理测试通过")

    print("\n🎉 所有自检测试通过！")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="智能家居仪表盘配置解析与可视化设计工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s config.yaml                    # 解析 YAML 文件
  %(prog)s dashboard.json                 # 解析 JSON 文件
  %(prog)s https://example.com/config     # 从 URL 获取配置
  %(prog)s --selftest                     # 运行自检测试
  %(prog)s -o report.txt config.yaml      # 输出到文件
  %(prog)s -b config1.yaml config2.json   # 批量处理
        """,
    )
    parser.add_argument(
        "sources",
        nargs="*",
        help="配置文件路径、URL 或原始配置文本",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检测试",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="将结果写入文件",
    )
    parser.add_argument(
        "-b", "--batch",
        action="store_true",
        help="批量处理模式（处理所有输入源）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )

    args = parser.parse_args()

    # 自检测试模式
    if args.selftest:
        try:
            selftest()
            return 0
        except AssertionError as exc:
            error_exit("E010", f"自检测试失败: {exc}")
        except Exception as exc:
            error_exit("E010", f"自检测试异常: {exc}")

    # 检查输入
    if not args.sources:
        error_exit("E008", "请提供配置文件路径、URL 或配置文本。使用 --help 查看帮助。")

    # 批量处理
    if args.batch or len(args.sources) > 1:
        batch_process(args.sources, args.output)
        return 0

    # 单文件处理
    try:
        result = process_input(args.sources[0])

        if args.json:
            # JSON 输出
            json_output = json.dumps(result, ensure_ascii=False, indent=2)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(json_output)
                print(f"JSON 结果已写入: {args.output}")
            else:
                print(json_output)
        else:
            output_result(result, args.output)

        return 0

    except SystemExit:
        raise
    except Exception as exc:
        error_exit("E007", f"未预期错误: {exc}")


if __name__ == "__main__":
    sys.exit(main())
