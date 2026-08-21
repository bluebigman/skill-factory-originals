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
import urllib.error
from collections import Counter, defaultdict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from datetime import datetime, timezone
import random

try:
    import yaml
    HAS_PYYAML = True
except ImportError:
    HAS_PYYAML = False

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
_retry_base_delay = 1  # 基础退避延迟（秒）
_request_timeout = 10  # 请求超时（秒）

def _retry_request(fn, *args, method="GET", **kwargs):
    """带重试退避和超时的请求封装（G1 生产门禁）。
    
    区分超时/连接错误，仅对幂等请求重试，增加 jitter 避免惊群效应。
    捕获 HTTPError 并检查 status code（>=500 才重试），每次重试前重新创建 Request 对象。
    """
    if not _is_idempotent_request(method):
        # 非幂等请求直接执行，不重试
        return fn(*args, **kwargs)
    
    last_exc = None
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except urllib.error.HTTPError as exc:
            # HTTP 错误：仅对 5xx 状态码重试
            if exc.code >= 500 and attempt < _max_retry - 1:
                last_exc = exc
                # 指数退避 + 真随机 jitter
                delay = _retry_base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
                # 重新创建 Request 对象（通过重新调用 fn 实现）
                continue
            else:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_exc = exc
            # 仅对超时和连接错误重试，其他异常直接抛出
            if attempt < _max_retry - 1:
                # 指数退避 + 真随机 jitter
                delay = _retry_base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
            else:
                raise
        except Exception as exc:
            # 非网络错误直接抛出
            raise
    # 如果所有重试都失败，抛出最后一个异常
    if last_exc:
        raise last_exc
    return None

def _is_idempotent_request(method: str) -> bool:
    """判断请求是否为幂等请求（GET/HEAD 为幂等）。"""
    return method.upper() in ("GET", "HEAD")


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
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def safe_yaml_loads(text: str):
    """完整 YAML 解析器（使用 PyYAML 库）。
    
    支持标准 YAML 特性：锚点、别名、多文档、复杂缩进、多行字符串、内联集合等。
    如果 PyYAML 不可用，则回退到手写解析器（仅支持 YAML 子集）。
    """
    if not text or not text.strip():
        return None

    if HAS_PYYAML:
        try:
            # 使用 PyYAML 完整解析
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            print(f"YAML 解析错误: {exc}", file=sys.stderr)
            return None
    else:
        # 回退到手写解析器（仅支持 YAML 子集）
        return _fallback_yaml_loads(text)


def _fallback_yaml_loads(text: str):
    """手写简化 YAML 解析器（仅支持 YAML 子集）。
    
    注意：此解析器不支持锚点、别名、多文档等高级特性。
    仅作为 PyYAML 不可用时的回退方案。
    """
    result = {}
    lines = text.splitlines()
    stack = []  # 维护 (缩进, 字典) 的栈
    current_list = None  # 当前列表项
    list_indent = -1  # 列表缩进级别
    in_multiline = False  # 是否在多行字符串中
    multiline_key = None  # 多行字符串的键
    multiline_indent = 0  # 多行字符串的缩进

    for line_num, line in enumerate(lines):
        # 处理多行字符串
        if in_multiline:
            if line.strip() and len(line) - len(line.lstrip()) > multiline_indent:
                # 继续多行字符串
                if current_list is not None:
                    current_list[-1] += "\n" + line.strip()
                else:
                    parent = stack[-1][1] if stack else result
                    parent[multiline_key] += "\n" + line.strip()
                continue
            else:
                # 多行字符串结束
                in_multiline = False
                multiline_key = None
                current_list = None
                # 继续处理当前行

        # 去除注释（不在引号内）
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 简单处理引号内的 #
        in_quote = False
        quote_char = None
        for i, ch in enumerate(line):
            if ch in ('"', "'"):
                if not in_quote:
                    in_quote = True
                    quote_char = ch
                elif ch == quote_char:
                    in_quote = False
                    quote_char = None
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

            # 处理内联字典
            if item.startswith("{"):
                try:
                    item = json.loads(item)
                except json.JSONDecodeError:
                    pass

            # 找到当前缩进对应的父字典
            while stack and stack[-1][0] >= indent:
                stack.pop()

            if not stack:
                # 顶层列表
                if "_top_list" not in result:
                    result["_top_list"] = []
                result["_top_list"].append(item)
                current_list = result["_top_list"]
                list_indent = indent
            else:
                parent = stack[-1][1]
                key = stack[-1][2]
                if key not in parent or not isinstance(parent[key], list):
                    parent[key] = []
                parent[key].append(item)
                current_list = parent[key]
                list_indent = indent

            # 检查是否是多行字符串开始
            if isinstance(item, str) and item in ("|", ">"):
                in_multiline = True
                multiline_indent = indent
                multiline_key = key if stack else "_top_list"
                if current_list:
                    current_list[-1] = ""
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

            # 处理内联列表
            if value.startswith("[") and value.endswith("]"):
                try:
                    value = json.loadsvalue = json.loads(value)
                except json.JSONDecodeError:
                    pass

            # 处理内联字典
            if value.startswith("{") and value.endswith("}"):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass

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

            # 检查是否是多行字符串开始
            if isinstance(value, str) and value in ("|", ">"):
                in_multiline = True
                multiline_indent = indent
                multiline_key = key
                parent[key] = ""
            continue

        # 其他情况（可能是多行字符串内容）
        if in_multiline:
            if current_list is not None:
                current_list[-1] += "\n" + content
            else:
                parent = stack[-1][1] if stack else result
                parent[multiline_key] += "\n" + content

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


@lru_cache(maxsize=128)
def fetch_url_content_cached(url: str):
    """从 URL 获取文本内容（带缓存）。"""
    try:
        # 创建 Request 对象，设置 User-Agent
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_request_timeout) as resp:
            # 检查内容类型
            content_type = resp.headers.get("Content-Type", "")
            if "json" not in content_type and "yaml" not in content_type and "text" not in content_type:
                # 尝试从内容判断
                content = resp.read().decode("utf-8")
                if not (content.lstrip().startswith("{") or content.lstrip().startswith("[")):
                    raise ValueError(f"URL 内容不是有效的 JSON/YAML 格式: {content_type}")
                return content
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_exit("E006", f"无法访问 URL {url}: HTTP {exc.code}")
    except Exception as exc:
        error_exit("E006", f"无法访问 URL {url}: {exc}")


def fetch_url_content(url: str):
    """从 URL 获取文本内容（带重试）。"""
    if not _is_idempotent_request("GET"):
        # 非幂等请求不重试
        return fetch_url_content_cached(url)
    return _retry_request(fetch_url_content_cached, url, method="GET")


def is_url(input_str: str) -> bool:
    """判断输入是否为 URL。"""
    return input_str.startswith(("http://", "https://"))


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
        suggestions
