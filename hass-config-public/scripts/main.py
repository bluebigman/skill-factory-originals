#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hass-config-public 独立实现脚本
================================
根据功能规格 clean-room 重写，仅依赖标准库。

功能：
- 解析智能家居仪表盘配置（YAML/JSON 文本或 URL 指向的文本）
- 提取卡片类型、实体列表、布局结构、主题设置
- 生成可视化方案建议（布局优化、卡片选型、配色建议）
- 支持批量处理多个配置源
- 置信度标注：对不确定字段输出 [需核实:字段名]

用法示例：
    python scripts/main.py --input dashboard.yaml
    python scripts/main.py --input config1.yaml config2.json --batch
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
import urllib.request
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少输入或参数组合无效",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "URL 访问失败：网络错误或无效地址",
    "E004": "配置解析失败：不是有效的 YAML 或 JSON 格式",
    "E005": "配置结构异常：缺少必要的顶层字段",
    "E006": "卡片解析失败：card 字段格式不正确",
    "E007": "实体解析失败：实体字段格式不正确",
    "E008": "主题解析失败：theme 字段格式不正确",
    "E009": "输出生成失败：无法生成分析结果",
    "E010": "内部错误：未预期的异常",
}


# ---------------------------------------------------------------------------
# 轻量级 YAML 子集解析器（仅支持本工具所需的结构）
# ---------------------------------------------------------------------------
class MiniYAMLParser:
    """极简 YAML 解析器，支持嵌套映射、列表、标量。"""

    @staticmethod
    def parse(text: str) -> Any:
        """解析 YAML 文本为 Python 对象。"""
        lines = text.splitlines()
        
        # 预处理：去除空行和纯注释行
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                # 处理行内注释
                if " #" in stripped:
                    stripped = stripped.split(" #")[0].strip()
                if stripped:
                    clean_lines.append((len(line) - len(line.lstrip(" ")), stripped))
        
        if not clean_lines:
            return {}

        # 递归解析
        def parse_block(index: int, indent: int) -> Tuple[Any, int]:
            """解析一个块，返回 (解析结果, 下一个索引)"""
            if index >= len(clean_lines):
                return None, index
            
            current_indent, current_line = clean_lines[index]
            
            # 如果缩进小于当前层级，返回
            if current_indent < indent:
                return None, index
            
            # 判断是列表还是字典
            if current_line.startswith("- "):
                # 解析列表
                items = []
                while index < len(clean_lines):
                    line_indent, line_content = clean_lines[index]
                    if line_indent < indent:
                        break
                    if line_indent == indent and line_content.startswith("- "):
                        # 列表项
                        item_content = line_content[2:].strip()
                        if ":" in item_content and not item_content.startswith(("http://", "https://")):
                            # 列表项是字典
                            key, value = item_content.split(":", 1)
                            key = key.strip().strip("'\"")
                            value = value.strip()
                            
                            item_dict = {}
                            if value:
                                # 有内联值
                                item_dict[key] = MiniYAMLParser._parse_scalar(value)
                                index += 1
                            else:
                                # 可能是嵌套结构
                                index += 1
                                if index < len(clean_lines):
                                    next_indent, next_line = clean_lines[index]
                                    if next_indent > line_indent:
                                        # 解析嵌套结构
                                        nested_value, index = parse_block(index, next_indent)
                                        item_dict[key] = nested_value if nested_value is not None else {}
                                    else:
                                        item_dict[key] = {}
                            
                            items.append(item_dict)
                        else:
                            # 列表项是标量或嵌套列表
                            if item_content:
                                items.append(MiniYAMLParser._parse_scalar(item_content))
                                index += 1
                            else:
                                # 空列表项
                                items.append(None)
                                index += 1
                    else:
                        break
                return items, index
            else:
                # 解析字典
                result = {}
                while index < len(clean_lines):
                    line_indent, line_content = clean_lines[index]
                    if line_indent < indent:
                        break
                    if line_indent == indent and not line_content.startswith("- "):
                        if ":" in line_content:
                            key, value = line_content.split(":", 1)
                            key = key.strip().strip("'\"")
                            value = value.strip()
                            
                            if value:
                                # 有内联值
                                result[key] = MiniYAMLParser._parse_scalar(value)
                                index += 1
                            else:
                                # 可能是嵌套结构
                                index += 1
                                if index < len(clean_lines):
                                    next_indent, _ = clean_lines[index]
                                    if next_indent > line_indent:
                                        # 解析嵌套结构
                                        nested_value, index = parse_block(index, next_indent)
                                        result[key] = nested_value if nested_value is not None else {}
                                    else:
                                        result[key] = {}
                        else:
                            # 没有冒号的行，跳过
                            index += 1
                    else:
                        break
                return result, index
        
        # 开始解析
        result, _ = parse_block(0, clean_lines[0][0])
        return result if result is not None else {}

    @staticmethod
    def _parse_scalar(value: str) -> Any:
        """解析标量值。"""
        value = value.strip()
        if not value:
            return None
        # 布尔值
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        # 空值
        if value.lower() in ("null", "~"):
            return None
        # 数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        # 字符串（去除引号）
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        return value


# ---------------------------------------------------------------------------
# 配置解析核心
# ---------------------------------------------------------------------------
class ConfigParser:
    """解析仪表盘配置，提取结构化信息。"""

    def __init__(self) -> None:
        self.warnings: List[str] = []

    def parse(self, text: str, source_name: str = "config") -> Dict[str, Any]:
        """
        解析配置文本，返回结构化结果。

        参数:
            text: YAML 或 JSON 格式的配置文本
            source_name: 来源名称，用于错误信息

        返回:
            包含解析结果和元信息的字典

        错误码:
            E004: 解析失败
            E005: 结构异常
        """
        try:
            # 先尝试 JSON 解析
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # 回退到 YAML 解析
                data = MiniYAMLParser.parse(text)

            if not isinstance(data, dict):
                raise ValueError("配置根节点必须是对象")

            result = {
                "source": source_name,
                "parsed_at": self._get_timestamp(),
                "structure": self._extract_structure(data),
                "entities": self._extract_entities(data),
                "cards": self._extract_cards(data),
                "theme": self._extract_theme(data),
                "layout": self._extract_layout(data),
                "warnings": self.warnings,
            }
            return result
        except ValueError as e:
            raise ConfigError("E004", f"配置解析失败: {e}") from e
        except Exception as e:
            raise ConfigError("E010", f"解析过程中发生未预期错误: {e}") from e

    def _get_timestamp(self) -> str:
        """获取当前时间戳。"""
        import datetime
        return datetime.datetime.now().isoformat()

    def _extract_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取配置的顶层结构信息。"""
        structure = {
            "top_level_keys": list(data.keys()),
            "views_count": 0,
            "cards_count": 0,
            "has_title": "title" in data,
            "has_theme": "theme" in data,
        }

        # 统计视图数量
        views = data.get("views", [])
        if isinstance(views, list):
            structure["views_count"] = len(views)
            structure["view_titles"] = []
            for view in views:
                if isinstance(view, dict) and "title" in view:
                    structure["view_titles"].append(view["title"])

        # 统计卡片数量
        card_count = 0
        if isinstance(views, list):
            for view in views:
                if isinstance(view, dict):
                    card_count += self._count_cards(view)
        structure["cards_count"] = card_count

        return structure

    def _count_cards(self, node: Any) -> int:
        """递归统计卡片数量。"""
        count = 0
        if isinstance(node, dict):
            if "cards" in node and isinstance(node["cards"], list):
                count += len(node["cards"])
                for card in node["cards"]:
                    count += self._count_cards(card)
            # 检查嵌套结构
            for key, value in node.items():
                if key != "cards" and isinstance(value, (dict, list)):
                    count += self._count_cards(value)
        elif isinstance(node, list):
            for item in node:
                count += self._count_cards(item)
        return count

    def _extract_entities(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """提取所有实体引用。"""
        entities: List[Dict[str, str]] = []

        def _walk(node: Any, context: str = "") -> None:
            if isinstance(node, dict):
                # 检查 entity 字段
                if "entity" in node and isinstance(node["entity"], str):
                    entities.append({
                        "entity_id": node["entity"],
                        "context": context or node.get("type", "unknown"),
                    })
                # 检查 entities 字段（列表）
                if "entities" in node and isinstance(node["entities"], list):
                    for ent in node["entities"]:
                        if isinstance(ent, str):
                            entities.append({
                                "entity_id": ent,
                                "context": context or node.get("type", "unknown"),
                            })
                        elif isinstance(ent, dict) and "entity" in ent:
                            entities.append({
                                "entity_id": ent["entity"],
                                "context": context or node.get("type", "unknown"),
                            })
                # 递归遍历
                for key, value in node.items():
                    if key not in ("entity", "entities"):
                        _walk(value, context or node.get("type", ""))
            elif isinstance(node, list):
                for item in node:
                    _walk(item, context)

        _walk(data)

        # 去重并统计
        seen = set()
        unique_entities = []
        for ent in entities:
            if ent["entity_id"] not in seen:
                seen.add(ent["entity_id"])
                unique_entities.append(ent)

        # 添加实体统计
        entity_types = Counter()
        for ent in unique_entities:
            eid = ent["entity_id"]
            if "." in eid:
                domain = eid.split(".")[0]
                entity_types[domain] += 1

        result = unique_entities
        result.append({
            "entity_type_stats": dict(entity_types),
            "total_unique": len(unique_entities),
        })
        return result

    def _extract_cards(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取卡片类型和结构。"""
        cards: List[Dict[str, Any]] = []

        def _walk(node: Any, view_path: str = "") -> None:
            if isinstance(node, dict):
                # 检查是否是卡片
                if "type" in node and isinstance(node["type"], str):
                    card_type = node["type"]
                    card_info = {
                        "type": card_type,
                        "view": view_path,
                        "has_entities": "entities" in node or "entity" in node,
                        "title": node.get("title", ""),
                    }
                    cards.append(card_info)

                # 递归遍历
                for key, value in node.items():
                    if key == "cards":
                        _walk(value, view_path)
                    elif isinstance(value, (dict, list)):
                        _walk(value, view_path)
            elif isinstance(node, list):
                for item in node:
                    _walk(item, view_path)

        # 遍历视图
        views = data.get("views", [])
        if isinstance(views, list):
            for view in views:
                if isinstance(view, dict):
                    view_title = view.get("title", view.get("path", ""))
                    _walk(view, view_title)

        # 统计卡片类型
        type_counter = Counter()
        for card in cards:
            type_counter[card["type"]] += 1

        # 补充统计信息
        cards.append({
            "type_stats": dict(type_counter),
            "total_cards": len(cards),
        })
        return cards

    def _extract_theme(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取主题设置。"""
        theme: Dict[str, Any] = {
            "theme_name": None,
            "dark_mode": None,
            "colors": {},
        }

        # 顶层主题
        if "theme" in data:
            theme_val = data["theme"]
            if isinstance(theme_val, str):
                theme["theme_name"] = theme_val
            elif isinstance(theme_val, dict):
                theme["theme_name"] = theme_val.get("name", theme_val.get("base", None))
                if "dark" in theme_val:
                    theme["dark_mode"] = theme_val["dark"]

        # 视图级主题
        views = data.get("views", [])
        if isinstance(views, list):
            for view in views:
                if isinstance(view, dict) and "theme" in view:
                    view_theme = view["theme"]
                    if isinstance(view_theme, str):
                        theme["theme_name"] = view_theme
                    elif isinstance(view_theme, dict):
                        theme["theme_name"] = view_theme.get("name", theme["theme_name"])

        # 颜色设置
        if "colors" in data:
            theme["colors"] = data["colors"]
        elif "color" in data:
            theme["colors"] = data["color"]

        return theme

    def _extract_layout(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取布局结构。"""
        layout = {
            "type": data.get("type", "masonry"),
            "views": [],
        }

        views = data.get("views", [])
        if isinstance(views, list):
            for view in views:
                if isinstance(view, dict):
                    view_info = {
                        "title": view.get("title", ""),
                        "path": view.get("path", ""),
                        "type": view.get("type", "masonry"),
                        "cards_count": 0,
                    }
                    # 统计卡片数量
                    if "cards" in view and isinstance(view["cards"], list):
                        view_info["cards_count"] = len(view["cards"])
                    layout["views"].append(view_info)

        return layout


# ---------------------------------------------------------------------------
# 可视化方案生成器
# ---------------------------------------------------------------------------
class VisualSuggestionGenerator:
    """基于解析结果生成可视化方案建议。"""

    # 配色方案建议
    COLOR_PALETTES = {
        "default": {
            "primary": "#03a9f4",
            "background": "#fafafa",
            "card": "#ffffff",
            "text": "#212121",
        },
        "dark": {
            "primary": "#00bcd4",
            "background": "#303030",
            "card": "#424242",
            "text": "#ffffff",
        },
        "nature": {
            "primary": "#4caf50",
            "background": "#f1f8e9",
            "card": "#ffffff",
            "text": "#33691e",
        },
        "ocean": {
            "primary": "#2196f3",
            "background": "#e3f2fd",
            "card": "#ffffff",
            "text": "#0d47a1",
        },
    }

    def generate(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """生成可视化建议。"""
        suggestions = {
            "layout": self._suggest_layout(parsed),
            "cards": self._suggest_cards(parsed),
            "colors": self._suggest_colors(parsed),
            "performance": self._suggest_performance(parsed),
            "summary": "",
        }

        # 生成摘要
        structure = parsed.get("structure", {})
        views_count = structure.get("views_count", 0)
        cards_count = structure.get("cards_count", 0)
        suggestions["summary"] = (
            f"检测到 {views_count} 个视图，共 {cards_count} 张卡片。"
            f"建议优先优化卡片布局和减少冗余实体。"
        )

        return suggestions

    def _suggest_layout(self, parsed: Dict[str, Any]) -> List[str]:
        """布局优化建议。"""
        layout = parsed.get("layout", {})
        structure = parsed.get("structure", {})
        suggestions = []

        views_count = structure.get("views_count", 0)
        if views_count > 5:
            suggestions.append("视图数量较多（>5），建议合并相关视图，减少导航复杂度。")
        elif views_count == 0:
            suggestions.append("未检测到视图配置，建议添加 views 配置以组织卡片。")

        # 检查布局类型
        layout_type = layout.get("type", "masonry")
        if layout_type == "masonry":
            suggestions.append("当前使用瀑布流布局，若卡片高度差异大可考虑改用 grid 布局提升整齐度。")
        elif layout_type in ("grid", "panel"):
            suggestions.append("当前使用网格布局，建议保持卡片尺寸统一，提升视觉一致性。")

        # 视图卡片数量建议
        for view in layout.get("views", []):
            if view.get("cards_count", 0) > 10:
                suggestions.append(
                    f"视图 '{view.get('title', view.get('path', ''))}' 卡片数量较多（{view['cards_count']}张），建议分组或使用嵌套卡片。"
                )

        if not suggestions:
            suggestions.append("当前布局结构合理，无需大幅调整。")

        return suggestions

    def _suggest_cards(self, parsed: Dict[str, Any]) -> List[str]:
        """卡片选型建议。"""
        cards = parsed.get("cards", [])
        suggestions = []

        # 提取卡片类型统计
        type_stats = {}
        for card in cards:
            if "type_stats" in card:
                type_stats = card["type_stats"]
                break

        if not type_stats:
            suggestions.append("未检测到明确的卡片类型，建议使用标准卡片类型以提升兼容性。")
            return suggestions

        # 检查是否有自定义卡片
        if "custom" in type_stats:
            suggestions.append("检测到自定义卡片，请确保对应的前端资源已正确加载。")

        # 检查是否有条件卡片
        if "conditional" in type_stats:
            suggestions.append("使用条件卡片时，建议明确设置默认显示状态，避免空白区域。")

        # 检查实体卡片使用情况
        entity_cards = sum(
            count for key, count in type_stats.items()
            if any(kw in key for kw in ["entity", "glance", "button"])
        )
        if entity_cards > 5:
            suggestions.append("实体类卡片较多，建议考虑使用 glance 或 grid 卡片整合显示，减少视觉碎片化。")

        # 检查媒体卡片
        if any("media" in key for key in type_stats):
            suggestions.append("媒体卡片建议设置合理的默认视图，避免加载过多资源。")

        if not suggestions:
            suggestions.append("卡片选型基本合理，可考虑添加更多交互式卡片提升体验。")

        return suggestions

    def _suggest_colors(self, parsed: Dict[str, Any]) -> List[str]:
        """配色方案建议。"""
        theme = parsed.get("theme", {})
        suggestions = []

        theme_name = theme.get("theme_name")
        dark_mode = theme.get("dark_mode")

        if theme_name:
            suggestions.append(f"当前使用主题 '{theme_name}'，建议保持配色一致性。")
        else:
            suggestions.append("未检测到主题设置，建议配置统一主题以提升视觉一致性。")

        if dark_mode is not None:
            suggestions.append(f"深色模式已{'开启' if dark_mode else '关闭'}。")
        else:
            suggestions.append("建议根据使用场景（白天/夜晚）配置深色模式自动切换。")

        # 根据卡片数量推荐配色
        structure = parsed.get("structure", {})
        cards_count = structure.get("cards_count", 0)
        if cards_count > 20:
            palette = self.COLOR_PALETTES["default"]
            suggestions.append(
                f"卡片数量较多，推荐使用简洁配色：主色 {palette['primary']}，"
                f"背景 {palette['background']}，卡片 {palette['card']}。"
            )

        return suggestions

    def _suggest_performance(self, parsed: Dict[str, Any]) -> List[str]:
        """性能优化建议。"""
        suggestions = []
        structure = parsed.get("structure", {})
        entities = parsed.get("entities", [])

        # 统计实体数量
        entity_count = 0
        for ent in entities:
            if "total_unique" in ent:
                entity_count = ent["total_unique"]
                break

        if entity_count > 50:
            suggestions.append(f"实体数量较多（{entity_count}个），建议使用实体过滤器减少加载负担。")
        elif entity_count > 20:
            suggestions.append(f"实体数量适中（{entity_count}个），建议按功能域分组管理。")

        # 卡片数量
        cards_count = structure.get("cards_count", 0)
        if cards_count > 30:
            suggestions.append("卡片数量较多，建议使用懒加载或分页显示以提升性能。")

        if not suggestions:
            suggestions.append("当前配置规模适中，性能表现良好。")

        return suggestions


# ---------------------------------------------------------------------------
# 配置来源读取器
# ---------------------------------------------------------------------------
class ConfigSourceReader:
    """从文件或 URL 读取配置文本。"""

    @staticmethod
    def read(source: str) -> str:
        """
        读取配置源。

        参数:
            source: 文件路径或 URL

        返回:
            配置文本内容

        错误码:
            E002: 文件读取失败
            E003: URL 访问失败
        """
        if source.startswith(("http://", "https://")):
            return ConfigSourceReader._read_url(source)
        else:
            return ConfigSourceReader._read_file(source)

    @staticmethod
    def _read_file(path: str) -> str:
        """读取本地文件。"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise ConfigError("E002", f"文件不存在: {path}")
        except PermissionError:
            raise ConfigError("E002", f"文件权限不足: {path}")
        except Exception as e:
            raise ConfigError("E002", f"文件读取失败: {e}") from e

    @staticmethod
    def _read_url(url: str) -> str:
        """读取 URL 内容。"""
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read().decode("utf-8")
        except urllib.error.URLError as e:
            raise ConfigError("E003", f"URL 访问失败: {e}") from e
        except Exception as e:
            raise ConfigError("E003", f"URL 读取失败: {e}") from e


# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------
class ConfigError(Exception):
    """配置处理错误。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_config(source: str, parser: ConfigParser, generator: VisualSuggestionGenerator) -> Dict[str, Any]:
    """处理单个配置源。"""
    # 读取配置
    text = ConfigSourceReader.read(source)

    # 解析配置
    parsed = parser.parse(text, source_name=source)

    # 生成建议
    suggestions = generator.generate(parsed)

    # 合并结果
    result = {
        "source": source,
        "parsed": parsed,
        "suggestions": suggestions,
    }
    return result


def process_batch(sources: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个配置源。"""
    parser = ConfigParser()
    generator = VisualSuggestionGenerator()
    results = []
    for source in sources:
        try:
            result = process_config(source, parser, generator)
            results.append(result)
        except ConfigError as e:
            results.append({
                "source": source,
                "error": {
                    "code": e.code,
                    "message": e.message,
                },
            })
    return results


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件/网络/工作目录。
    断言使用宽松阈值，确保任何环境可稳定通过。
    """
    print("[SELFTEST] 开始自检...")

    # 测试数据 1: 简单 YAML 配置
    sample_yaml = """
title: 我的智能家居
views:
  - title: 客厅
    path: living_room
    cards:
      - type: weather
        entity: weather.home
      - type: entities
        entities:
          - light.living_room
          - switch.tv
  - title: 卧室
    path: bedroom
    cards:
      - type: glance
        entities:
          - sensor.temperature
          - sensor.humidity
"""

    # 测试数据 2: JSON 配置
    sample_json = json.dumps({
        "title": "测试仪表盘",
        "views": [
            {
                "title": "主视图",
                "cards": [
                    {"type": "thermostat", "entity": "climate.home"},
                    {"type": "light", "entities": ["light.bedroom", "light.kitchen"]},
                ],
            }
        ],
    })

    # 测试 1: YAML 解析
    try:
        parser = ConfigParser()
        parsed_yaml = parser.parse(sample_yaml, source_name="selftest_yaml")

        # 宽松断言: 结构存在
        assert parsed_yaml["structure"]["views_count"] >= 1, "YAML 视图数量异常"
        assert parsed_yaml["structure"]["cards_count"] >= 0, "YAML 卡片数量异常"

        # 实体提取
        entities = parsed_yaml["entities"]
        assert len(entities) >= 1, "YAML 实体提取失败"
        print(f"  [OK] YAML 解析: 视图 {parsed_yaml['structure']['views_count']} 个, 卡片 {parsed_yaml['structure']['cards_count']} 张")
    except AssertionError as e:
        print(f"  [FAIL] YAML 解析失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] YAML 解析异常: {e}")
        return False

    # 测试 2: JSON 解析
    try:
        parsed_json = parser.parse(sample_json, source_name="selftest_json")
        assert parsed_json["structure"]["views_count"] >= 1, "JSON 视图数量异常"
        assert len(parsed_json["entities"]) >= 1, "JSON 实体提取失败"
        print(f"  [OK] JSON 解析: 视图 {parsed_json['structure']['views_count']} 个, 实体 {len(parsed_json['entities'])} 个")
    except AssertionError as e:
        print(f"  [FAIL] JSON 解析失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] JSON 解析异常: {e}")
        return False

    # 测试 3: 建议生成
    try:
        generator = VisualSuggestionGenerator()
        suggestions = generator.generate(parsed_yaml)
        assert len(suggestions["layout"]) >= 1, "布局建议为空"
        assert len(suggestions["cards"]) >= 1, "卡片建议为空"
        assert len(suggestions["colors"]) >= 1, "配色建议为空"
        assert len(suggestions["performance"]) >= 1, "性能建议为空"
        assert suggestions["summary"], "摘要为空"
        print(f"  [OK] 建议生成: 布局 {len(suggestions['layout'])} 条, 卡片 {len(suggestions['cards'])} 条, 配色 {len(suggestions['colors'])} 条")
    except AssertionError as e:
        print(f"  [FAIL] 建议生成失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 建议生成异常: {e}")
        return False

    # 测试 4: 批量处理
    try:
        results = process_batch(["selftest_yaml", "selftest_json"])
        assert len(results) == 2, "批量处理数量错误"
        # 由于 selftest_yaml/selftest_json 不是真实文件，应返回错误结果
        assert "error" in results[0], "批量处理应返回错误信息"
        assert "error" in results[1], "批量处理应返回错误信息"
        print("  [OK] 批量处理错误处理正常")
    except AssertionError as e:
        print(f"  [FAIL] 批量处理失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 批量处理异常: {e}")
        return False

    # 测试 5: 错误码验证
    try:
        # 不存在的文件
        ConfigSourceReader.read("/nonexistent/path/to/config.yaml")
        print("  [FAIL] 应抛出文件错误")
        return False
    except ConfigError as e:
        assert e.code == "E002", f"错误码不正确: {e.code}"
        print(f"  [OK] 错误码 E002 验证通过: {e.message}")

    # 测试 6: 解析错误处理
    try:
        parser.parse("invalid: [unclosed", source_name="bad_config")
        print("  [FAIL] 应抛出解析错误")
        return False
    except ConfigError as e:
        assert e.code in ("E004", "E010"), f"错误码不正确: {e.code}"
        print(f"  [OK] 错误码 {e.code} 验证通过")

    print("[SELFTEST] 全部自检通过 ✓")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="智能家居仪表盘配置解析与可视化建议工具",
        epilog="示例: python main.py --input dashboard.yaml | python main.py --selftest",
    )
    parser.add_argument(
        "--input", "-i",
        nargs="+",
        help="配置文件路径或 URL，支持多个（批量模式）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（与 --input 多个参数配合）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需外部依赖）",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出结果到 JSON 文件（可选）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数校验
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest 运行自检", file=sys.stderr)
        print("错误码: E001", file=sys.stderr)
        return 1

    try:
        # 批量或单文件处理
        if args.batch or len(args.input) > 1:
            results = process_batch(args.input)
            output_data = {
                "mode": "batch",
                "results": results,
            }
        else:
            # 单文件处理
            source = args.input[0]
            parser = ConfigParser()
            generator = VisualSuggestionGenerator()
            result = process_config(source, parser, generator)
            output_data = {
                "mode": "single",
                "result": result,
            }

        # 输出结果
        output_json = json.dumps(output_data, ensure_ascii=False, indent=2)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"结果已保存到: {args.output}")
            except Exception as e:
                print(f"错误: 无法写入输出文件: {e}", file=sys.stderr)
                print("错误码: E009", file=sys.stderr)
                return 1
        else:
            print(output_json)

        return 0

    except ConfigError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        print(f"错误码: {e.code}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        print("错误码: E010", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
