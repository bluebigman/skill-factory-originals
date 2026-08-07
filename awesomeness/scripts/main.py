#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesomeness — Rails 组件速查与代码片段检索工具

本脚本根据功能规格独立实现，提供以下能力：
1. 将零散的 Rails 代码片段、组件说明或仓库链接转化为结构化速查卡片
2. 输出带置信度标注的检索结果，便于后续查阅与集成
3. 内置离线自检模式（--selftest），不依赖外部文件或网络

仅使用 Python 标准库实现。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入格式不正确（应为 JSON 字符串或字典）",
    "E003": "缺少必填字段（slug、name、description 至少其一）",
    "E004": "输入内容不是有效的 Rails 相关文本",
    "E005": "置信度计算失败（内部错误）",
    "E006": "输出序列化失败",
    "E007": "自检断言失败",
    "E008": "不支持的参数组合",
    "E009": "内部逻辑异常",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class RailsComponent:
    """Rails 组件速查卡片"""
    slug: str
    name: str
    description: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    snippets: List[str] = field(default_factory=list)
    source_url: str = ""
    confidence: float = 0.0
    raw_input: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ============================================================
# 核心逻辑：Rails 内容识别与解析
# ============================================================
# Rails 相关关键词，用于内容识别
RAILS_KEYWORDS = [
    "rails", "ruby", "gem", "activerecord", "activesupport", "actionpack",
    "actionview", "actionmailer", "activejob", "actioncable", "activestorage",
    "railties", "migration", "model", "controller", "view", "helper",
    "concern", "serializer", "callback", "association", "validates",
    "before_action", "after_action", "render", "redirect_to", "params",
    "strong_parameters", "turbo", "stimulus", "hotwire", "erb", "slim",
    "haml", "rspec", "factory_bot", "devise", "pundit", "cancancan",
    "sidekiq", "redis", "postgresql", "mysql", "sqlite", "bundle",
    "rake", "routes", "config", "db", "schema", "asset_pipeline",
    "webpacker", "importmap", "sprockets", "turbolinks", "puma", "unicorn",
]

# 组件分类关键词映射
CATEGORY_KEYWORDS = {
    "model": ["activerecord", "model", "migration", "association", "validates", "scope", "enum"],
    "controller": ["controller", "before_action", "after_action", "render", "redirect_to", "params"],
    "view": ["view", "erb", "slim", "haml", "partial", "helper", "layout"],
    "routing": ["routes", "resource", "namespace", "root", "match", "get", "post", "put", "patch", "delete"],
    "config": ["config", "environment", "initializer", "application.rb", "database.yml"],
    "security": ["devise", "pundit", "cancancan", "authentication", "authorization", "strong_parameters"],
    "performance": ["cache", "index", "eager_load", "includes", "preload", "counter_cache"],
    "testing": ["rspec", "factory_bot", "test", "spec", "minitest"],
    "jobs": ["activejob", "sidekiq", "worker", "queue", "async"],
    "api": ["api", "serializer", "json", "jbuilder", "rabl"],
}


def validate_input(data: Any) -> Dict[str, Any]:
    """
    验证并规范化输入数据
    
    支持输入：
    - 字符串（JSON 格式）
    - 字典对象
    
    返回规范化后的字典。
    """
    if data is None:
        raise SkillError("E001")
    
    if isinstance(data, str):
        # 尝试解析 JSON
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            # 不是 JSON，尝试作为纯文本处理
            parsed = {"raw_text": data}
    elif isinstance(data, dict):
        parsed = data
    else:
        raise SkillError("E002")
    
    # 检查必填字段
    has_required = any(k in parsed for k in ["slug", "name", "description", "raw_text", "content"])
    if not has_required:
        raise SkillError("E003")
    
    return parsed


def is_rails_related(text: str) -> bool:
    """判断文本是否与 Rails 相关"""
    if not text or not text.strip():
        return False
    
    lowered = text.lower()
    # 统计关键词命中数
    hits = sum(1 for kw in RAILS_KEYWORDS if kw.lower() in lowered)
    return hits >= 1


def detect_category(text: str) -> str:
    """根据文本内容检测组件分类"""
    lowered = text.lower()
    best_category = "general"
    best_score = 0
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lowered)
        if score > best_score:
            best_score = score
            best_category = category
    
    return best_category


def extract_tags(text: str, limit: int = 5) -> List[str]:
    """从文本中提取标签（简单关键词匹配）"""
    lowered = text.lower()
    tags = []
    
    for kw in RAILS_KEYWORDS:
        if kw.lower() in lowered and kw not in tags:
            tags.append(kw)
        if len(tags) >= limit:
            break
    
    return tags


def extract_snippets(text: str, max_snippets: int = 3) -> List[str]:
    """从文本中提取代码片段（以代码块形式存在的内容）"""
    snippets = []
    
    # 匹配代码块（
