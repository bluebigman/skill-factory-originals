#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — illo-skill 独立实现脚本

依据功能规格（clean-room）全新编写，不复制任何既有代码。
提供插画方案生成的核心逻辑，并支持 --selftest 离线自检。
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入内容过短，无法提取有效视觉要素",
    "E002": "URL解析失败，请检查链接是否有效",
    "E003": "单次最多处理5篇文章，请分批提交",
    "E004": "风格描述存在冲突（如同时要求极简和繁复），请明确优先级",
    "E005": "未指定输出格式，默认使用Markdown表格+段落混排",
    "E006": "内部处理异常，请重试",
    "E007": "核心主题提取失败，请检查输入内容",
    "E008": "情绪基调识别异常，请提供更多上下文",
    "E009": "关键意象提取失败，请检查输入内容",
    "E010": "方案生成失败，请检查输入内容",
}

# 情绪基调关键词映射（用于文本分析）
MOOD_KEYWORDS = {
    "温暖": ["温暖", "温馨", "阳光", "柔和", "治愈"],
    "冷峻": ["冷", "冰", "孤独", "疏离", "沉默"],
    "幽默": ["幽默", "搞笑", "滑稽", "轻松", "趣味"],
    "沉重": ["沉重", "悲伤", "压抑", "痛苦", "绝望"],
    "平静": ["平静", "安宁", "静谧", "平和", "淡然"],
    "激昂": ["激昂", "振奋", "热血", "激情", "澎湃"],
}

# 抽象概念 → 视觉符号映射表（规格中示例的扩展）
CONCEPT_MAP = {
    "时间流逝": ["沙漏", "年轮", "褪色照片", "时钟指针"],
    "社会压力": ["重叠的日历", "拥挤的楼梯", "压缩的弹簧", "堆积的文件"],
    "孤独": ["空荡的房间", "单人的长椅", "飘落的树叶", "远处的灯火"],
    "希望": ["破土的新芽", "黎明的光线", "飞翔的鸟", "灯塔"],
    "回忆": ["旧信件", "泛黄的相册", "老式收音机", "斑驳的墙壁"],
    "成长": ["幼苗", "阶梯", "破茧", "年轮"],
    "离别": ["站台", "行李箱", "远去的车", "飘落的花瓣"],
    "重逢": ["拥抱", "交汇的河流", "重逢的站台", "并行的轨道"],
}

# 情绪 → 色彩策略映射
MOOD_COLOR = {
    "温暖": [("#F4A460", "主色"), ("#FFE4B5", "辅色"), ("#8B4513", "点缀")],
    "冷峻": [("#4682B4", "主色"), ("#B0C4DE", "辅色"), ("#2F4F4F", "点缀")],
    "幽默": [("#FFD700", "主色"), ("#FFA07A", "辅色"), ("#20B2AA", "点缀")],
    "沉重": [("#2F4F4F", "主色"), ("#696969", "辅色"), ("#000000", "点缀")],
    "平静": [("#87CEEB", "主色"), ("#F0F8FF", "辅色"), ("#A9A9A9", "点缀")],
    "激昂": [("#FF4500", "主色"), ("#FFD700", "辅色"), ("#8B0000", "点缀")],
    "中性": [("#A9A9A9", "主色"), ("#D3D3D3", "辅色"), ("#696969", "点缀")],
}

# 构图类型
COMPOSITION_TYPES = ["居中", "三分法", "对角线", "框架式"]


@dataclass
class ArticleInput:
    """输入文章数据类"""
    text: str
    style_preference: Optional[str] = None
    output_format: str = "markdown"


@dataclass
class ParsedContent:
    """解析后的内容数据类"""
    core_themes: List[str] = field(default_factory=list)
    mood: str = "中性"
    key_imagery: List[str] = field(default_factory=list)
    narrative_structure: str = "线性"
    confidence: Dict[str, float] = field(default_factory=dict)


@dataclass
class VisualPlan:
    """视觉方案数据类"""
    theme: str = ""
    composition: str = ""
    composition_ascii: str = ""
    colors: List[Tuple[str, str, int]] = field(default_factory=list)
    elements: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    style_ref: str = ""
    confidence_notes: List[str] = field(default_factory=list)


def validate_input(text: str) -> Optional[str]:
    """校验输入文本，返回错误码或 None"""
    if not text or len(text.strip()) < 50:
        return "E001"
    return None


def extract_core_themes(text: str) -> Tuple[List[str], float]:
    """
    提取核心主题（1-3个关键词）
    返回 (主题列表, 置信度)
    """
    # 简单分词：取长度>2的中文词作为近似
    words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
    if not words:
        return [], 0.0

    # 词频统计
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    # 按频率排序取前3
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]
    themes = [w for w, _ in sorted_words if len(w) >= 2]

    # 置信度：基于文本长度和词频稳定性
    confidence = min(0.90, 0.60 + len(themes) * 0.10)
    return themes, confidence


def detect_mood(text: str) -> Tuple[str, float]:
    """
    检测情绪基调
    返回 (情绪, 置信度)
    """
    mood_scores = {}
    for mood, keywords in MOOD_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            mood_scores[mood] = score

    if not mood_scores:
        return "中性", 0.40

    # 取最高分情绪
    best_mood = max(mood_scores, key=mood_scores.get)
    # 置信度：基于匹配关键词数量和文本长度
    total_matches = sum(mood_scores.values())
    confidence = min(0.90, 0.50 + total_matches * 0.08)
    return best_mood, confidence


def extract_key_imagery(text: str) -> Tuple[List[str], float]:
    """
    提取关键意象（名词性元素）
    返回 (意象列表, 置信度)
    """
    # 从概念映射中检查是否包含抽象概念
    found_concepts = []
    for concept, symbols in CONCEPT_MAP.items():
        if concept in text:
            found_concepts.extend(symbols)

    # 提取文本中的具象名词（简单启发式：特定后缀词）
    concrete_nouns = re.findall(r'[\u4e00-\u9fff]{2,}(?:的|之)?(?:雨|风|花|树|山|水|光|影|门|窗|路|桥|灯|书|信|钟|鸟|鱼|船|车)', text)
    concrete_nouns = list(set(concrete_nouns))[:5]

    imagery = list(set(found_concepts + concrete_nouns))
    if not imagery:
        return [], 0.30

    confidence = min(0.85, 0.50 + len(imagery) * 0.06)
    return imagery, confidence


def detect_narrative_structure(text: str) -> Tuple[str, float]:
    """
    检测叙事结构
    返回 (结构类型, 置信度)
    """
    # 基于文本特征简单判断
    if re.search(r'(首先|然后|接着|最后)', text):
        return "线性", 0.70
    elif re.search(r'(虽然|但是|然而|却)', text):
        return "对比", 0.65
    elif re.search(r'(越来越|逐渐|渐渐)', text):
        return "递进", 0.65
    elif re.search(r'(始终|一直|反复|不断)', text):
        return "循环", 0.60
    return "线性", 0.50


def map_concept_to_symbol(concept: str) -> List[str]:
    """将抽象概念映射为视觉符号"""
    for key, symbols in CONCEPT_MAP.items():
        if key in concept:
            return symbols
    # 默认返回概念本身作为符号
    return [concept]


def choose_composition(mood: str, confidence: float) -> Tuple[str, str]:
    """
    基于情绪选择构图类型
    返回 (构图描述, ASCII示意)
    """
    # 简单规则：不同情绪映射不同构图
    comp_map = {
        "温暖": ("居中", "      ┌─────────┐\n      │  主体   │\n      │         │\n      └─────────┘"),
        "冷峻": ("三分法", "┌─────┬─────┬─────┐\n│ 留白 │ 主体 │ 留白 │\n│     │     │     │\n└─────┴─────┴─────┘"),
        "幽默": ("对角线", "┌─────────────┐\n│  主体 ↘      │\n│      ↘       │\n│       ↘      │\n└─────────────┘"),
        "沉重": ("框架式", "┌─────────────┐\n│ ┌─────────┐ │\n│ │  主体   │ │\n│ └─────────┘ │\n└─────────────┘"),
        "平静": ("三分法", "┌─────┬─────┬─────┐\n│ 留白 │ 主体 │ 留白 │\n│     │     │     │\n└─────┴─────┴─────┘"),
        "激昂": ("对角线", "┌─────────────┐\n│      ↗      │\n│   ↗         │\n│ ↗   主体    │\n└─────────────┘"),
        "中性": ("居中", "      ┌─────────┐\n      │  主体   │\n      │         │\n      └─────────┘"),
    }
    comp_type, ascii_art = comp_map.get(mood, comp_map["中性"])
    return comp_type, ascii_art


def generate_color_scheme(mood: str, confidence: float) -> List[Tuple[str, str, int]]:
    """
    生成色彩方案
    返回 [(角色, 色值, 占比), ...]
    """
    colors = MOOD_COLOR.get(mood, MOOD_COLOR["中性"])
    # 占比固定：主色60%，辅色30%，点缀10%
    ratios = [60, 30, 10]
    result = []
    for i, (hex_val, role) in enumerate(colors):
        result.append((role, hex_val, ratios[i]))
    return result


def generate_style_reference(mood: str, style_preference: Optional[str]) -> str:
    """生成风格参考描述"""
    if style_preference:
        return f"以{style_preference}为主导风格，结合{mood}的情绪基调，强调叙事性与编辑感。"

    # 默认风格描述
    style_map = {
        "温暖": "暖色调的编辑插画风格，注重光影层次与柔和质感，线条流畅而富有温度。",
        "冷峻": "冷色调的极简编辑风格，大量留白与硬朗线条，营造疏离而理性的视觉感受。",
        "幽默": "明快活泼的编辑插画风格，夸张的造型与跳跃的色彩，充满趣味性表达。",
        "沉重": "深色调的写实编辑风格，厚重的笔触与低饱和色彩，传达沉静而深刻的情感。",
        "平静": "淡雅清新的编辑插画风格，轻柔的过渡与均衡的构图，营造宁静平和的氛围。",
        "激昂": "高饱和度的表现主义编辑风格，动态的线条与强烈的色彩对比，充满张力。",
        "中性": "中性编辑风格，均衡的构图与克制的用色，注重信息传达与版式秩序。",
    }
    return style_map.get(mood, style_map["中性"])


def generate_visual_plan(parsed: ParsedContent, style_preference: Optional[str]) -> VisualPlan:
    """生成视觉方案"""
    plan = VisualPlan()

    # 主题提炼
    if parsed.core_themes:
        plan.theme = "、".join(parsed.core_themes[:3])
    else:
        plan.theme = "[需核实:核心主题]"

    # 构图
    comp_type, ascii_art = choose_composition(parsed.mood, parsed.confidence.get("mood", 0.0))
    plan.composition = f"采用{comp_type}构图，强调视觉平衡与叙事引导。"
    plan.composition_ascii = ascii_art

    # 色彩
    plan.colors = generate_color_scheme(parsed.mood, parsed.confidence.get("mood", 0.0))

    # 元素清单
    if parsed.key_imagery:
        main_elements = parsed.key_imagery[:2]
        aux_elements = parsed.key_imagery[2:4] if len(parsed.key_imagery) > 2 else ["留白"]
        bg_elements = ["背景渐变"] if parsed.key_imagery else ["[需核实:关键意象]"]

        plan.elements = {
            "主元素": ("、".join(main_elements), "高" if parsed.confidence.get("imagery", 0) >= 0.85 else "中"),
            "辅助元素": ("、".join(aux_elements), "中"),
            "背景元素": ("、".join(bg_elements), "低"),
        }
    else:
        plan.elements = {
            "主元素": ("[需核实:关键意象]", "低"),
            "辅助元素": ("[需核实:关键意象]", "低"),
            "背景元素": ("[需核实:关键意象]", "低"),
        }

    # 风格参考
    plan.style_ref = generate_style_reference(parsed.mood, style_preference)

    # 置信度标注
    for key, conf in parsed.confidence.items():
        if conf < 0.60:
            plan.confidence_notes.append(f"[需核实:{key}] 置信度低于60%，建议人工确认。")
        elif conf < 0.85:
            plan.confidence_notes.append(f"[基于上下文推断] {key}置信度{int(conf*100)}%。")

    return plan


def format_output(plan: VisualPlan) -> str:
    """将方案格式化为 Markdown 输出"""
    lines = []
    lines.append(f"## 插画方案：{plan.theme}")
    lines.append("")
    lines.append("### 主题提炼")
    lines.append(f"{plan.theme}——通过视觉元素传达核心叙事。")
    lines.append("")
    lines.append("### 构图描述")
    lines.append(plan.composition)
    
    if plan.composition_ascii:
        lines.append("")
        lines.append("
