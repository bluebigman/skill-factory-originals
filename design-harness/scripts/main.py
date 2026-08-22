#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
design-harness 技能实现脚本
===========================
功能：将设计稿或需求转化为可验证的前端原型，提供结构化输出与置信度提示。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例：
    python scripts/main.py --help
    python scripts/main.py --selftest
    python scripts/main.py --input design.json --output proto.html --format html
    python scripts/main.py --input design.json --output report.json --format json
"""

import argparse
import json
import os
import sys
import tempfile
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入 JSON 格式非法",
    "E003": "输入数据结构不完整（缺少必需字段）",
    "E004": "不支持的输出格式",
    "E005": "输出目录不可写",
    "E006": "内部逻辑错误（未知组件类型）",
    "E007": "参数冲突（如 --input 与 --selftest 同时使用）",
    "E008": "数据字段类型错误",
    "E009": "自检失败",
    "E010": "未捕获的运行时异常",
}


def fail(code: str, message: str) -> None:
    """打印错误并退出。"""
    sys.stderr.write(f"[{code}] {message}\n")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class DesignComponent:
    """设计稿中的单个组件。"""
    type: str                 # 组件类型：button / input / text / image / container
    label: str = ""           # 组件名称或文本内容
    x: int = 0                # 横坐标（px）
    y: int = 0                # 纵坐标（px）
    width: int = 100          # 宽度（px）
    height: int = 40          # 高度（px）
    color: str = "#333333"    # 主色
    font_size: int = 14       # 字号（px）
    interactive: bool = False # 是否为交互组件
    action: str = ""          # 交互动作描述（如 "跳转到详情页"）


@dataclass
class DesignDocument:
    """一份完整的结构化设计稿。"""
    title: str = "未命名设计"
    width: int = 375          # 画布宽度（px）
    height: int = 812         # 画布高度（px）
    components: List[DesignComponent] = field(default_factory=list)
    breakpoints: List[int] = field(default_factory=lambda: [375, 768, 1024])  # 响应式断点


# ---------------------------------------------------------------------------
# 核心逻辑：设计稿解析
# ---------------------------------------------------------------------------
def parse_design_data(data: Dict[str, Any]) -> DesignDocument:
    """
    将原始 JSON 数据解析为 DesignDocument 对象。
    期望输入格式：
    {
        "title": "登录页",
        "width": 375,
        "height": 812,
        "components": [
            {"type": "button", "label": "登录", "x": 20, "y": 300, "width": 200, "height": 48, "interactive": true, "action": "提交表单"}
        ]
    }
    """
    if not isinstance(data, dict):
        fail("E008", "顶层数据必须是 JSON 对象")

    # 必需字段检查 - 显式检查 title、width、height、components
    required_fields = ["title", "width", "height", "components"]
    for field_name in required_fields:
        if field_name not in data:
            fail("E003", f"缺少必需字段 '{field_name}'")

    # 字段类型检查
    if not isinstance(data["title"], str):
        fail("E008", "'title' 字段必须是字符串")
    if not isinstance(data["width"], (int, float)) or data["width"] <= 0:
        fail("E008", "'width' 字段必须是正数")
    if not isinstance(data["height"], (int, float)) or data["height"] <= 0:
        fail("E008", "'height' 字段必须是正数")
    if not isinstance(data["components"], list):
        fail("E008", "'components' 字段必须是列表")

    doc = DesignDocument(
        title=str(data["title"]),
        width=int(data["width"]),
        height=int(data["height"]),
    )

    # 解析断点（可选）
    if "breakpoints" in data:
        try:
            doc.breakpoints = [int(b) for b in data["breakpoints"]]
        except (TypeError, ValueError):
            fail("E008", "'breakpoints' 字段必须是整数列表")

    # 解析组件列表
    comp_list = data["components"]
    for item in comp_list:
        if not isinstance(item, dict):
            fail("E008", "组件必须是 JSON 对象")

        ctype = item.get("type", "")
        if ctype not in ("button", "input", "text", "image", "container"):
            fail("E006", f"未知组件类型: {ctype}")

        # 组件字段类型检查
        for field_name in ["x", "y", "width", "height", "font_size"]:
            if field_name in item and not isinstance(item[field_name], (int, float)):
                fail("E008", f"组件字段 '{field_name}' 必须是数字")

        comp = DesignComponent(
            type=ctype,
            label=str(item.get("label", "")),
            x=int(item.get("x", 0)),
            y=int(item.get("y", 0)),
            width=int(item.get("width", 100)),
            height=int(item.get("height", 40)),
            color=str(item.get("color", "#333333")),
            font_size=int(item.get("font_size", 14)),
            interactive=bool(item.get("interactive", False)),
            action=str(item.get("action", "")),
        )
        doc.components.append(comp)

    return doc


# ---------------------------------------------------------------------------
# 核心逻辑：前端代码生成
# ---------------------------------------------------------------------------
def generate_html(doc: DesignDocument) -> str:
    """将 DesignDocument 转换为 HTML 原型代码。"""
    lines: List[str] = []
    lines.append("<!DOCTYPE html>")
    lines.append('<html lang="zh-CN">')
    lines.append("<head>")
    lines.append('  <meta charset="UTF-8">')
    lines.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append(f"  <title>{doc.title}</title>")
    lines.append("  <style>")
    lines.append("    * { box-sizing: border-box; margin: 0; padding: 0; }")
    lines.append(f"    body {{ font-family: 'PingFang SC', 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5; }}")
    lines.append(f"    .design-canvas {{ width: {doc.width}px; min-height: {doc.height}px; margin: 0 auto; background: #ffffff; position: relative; }}")
    lines.append("    /* 响应式适配建议 */")
    for i, bp in enumerate(doc.breakpoints):
        if i == 0:
            continue  # 最小断点不写媒体查询
        lines.append(f"    @media (min-width: {bp}px) {{ .design-canvas {{ width: {bp}px; }} }}")
    lines.append("  </style>")
    lines.append("</head>")
    lines.append("<body>")
    lines.append(f'  <div class="design-canvas" data-title="{doc.title}" data-width="{doc.width}" data-height="{doc.height}">')

    # 为每个组件生成对应 HTML 元素
    for comp in doc.components:
        style_attrs = (
            f"position:absolute; "
            f"left:{comp.x}px; top:{comp.y}px; "
            f"width:{comp.width}px; height:{comp.height}px; "
            f"font-size:{comp.font_size}px; "
            f"color:{comp.color}; "
        )

        if comp.type == "button":
            bg_color = comp.color if comp.color.startswith("#") else "#4A90D9"
            style_attrs += (
                f"background:{bg_color}; color:#fff; border:none; border-radius:6px; "
                f"display:flex; align-items:center; justify-content:center; cursor:pointer;"
            )
            lines.append(
                f'    <div data-component="button" data-label="{comp.label}" '
                f'data-action="{comp.action}" style="{style_attrs}">{comp.label}</div>'
            )
        elif comp.type == "input":
            lines.append(
                f'    <input type="text" placeholder="{comp.label}" '
                f'data-component="input" style="{style_attrs}border:1px solid #ccc; border-radius:4px; padding:0 8px;">'
            )
        elif comp.type == "text":
            lines.append(
                f'    <div data-component="text" style="{style_attrs}">{comp.label}</div>'
            )
        elif comp.type == "image":
            lines.append(
                f'    <div data-component="image" data-label="{comp.label}" '
                f'style="{style_attrs}background:#eee; border:1px dashed #aaa; '
                f'display:flex; align-items:center; justify-content:center; color:#999;">'
                f'🖼️ {comp.label}</div>'
            )
        elif comp.type == "container":
            lines.append(
                f'    <div data-component="container" data-label="{comp.label}" '
                f'style="{style_attrs}background:{comp.color}; border:1px solid #ddd; border-radius:8px;"></div>'
            )
        else:
            fail("E006", f"无法生成未知组件类型: {comp.type}")

    lines.append("  </div>")
    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines)


def generate_css(doc: DesignDocument) -> str:
    """生成独立的 CSS 样式文件内容。"""
    lines: List[str] = []
    lines.append(f"/* {doc.title} - 原型样式 */")
    lines.append("* { box-sizing: border-box; margin: 0; padding: 0; }")
    lines.append("body { font-family: 'PingFang SC', sans-serif; background: #f0f0f0; }")
    lines.append(f".design-canvas {{ width: {doc.width}px; min-height: {doc.height}px; margin: 0 auto; background: #fff; position: relative; }}")
    lines.append("[data-component='button'] { display: flex; align-items: center; justify-content: center; cursor: pointer; border: none; border-radius: 6px; color: #fff; }")
    lines.append("[data-component='input'] { border: 1px solid #ccc; border-radius: 4px; padding: 0 8px; }")
    lines.append("[data-component='image'] { background: #eee; border: 1px dashed #aaa; display: flex; align-items: center; justify-content: center; color: #999; }")
    lines.append("[data-component='container'] { border: 1px solid #ddd; border-radius: 8px; }")
    for i, bp in enumerate(doc.breakpoints):
        if i == 0:
            continue
        lines.append(f"@media (min-width: {bp}px) {{ .design-canvas {{ width: {bp}px; }} }}")
    return "\n".join(lines)


def generate_js(doc: DesignDocument) -> str:
    """生成交互逻辑标注 JS 文件内容。"""
    lines: List[str] = []
    lines.append("// 交互逻辑标注 - 由 design-harness 生成")
    lines.append("// 此文件仅包含交互点标注，不包含真实业务逻辑")
    lines.append("(function() {")
    lines.append("  const interactions = [];")
    for comp in doc.components:
        if comp.interactive:
            lines.append(f"  interactions.push({{ component: '{comp.label}', type: '{comp.type}', action: '{comp.action}' }});")
    lines.append("  window.__designInteractions = interactions;")
    lines.append("  console.log('[design-harness] 已标注 ' + interactions.length + ' 个交互点');")
    lines.append("})();")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心逻辑：验证与置信度评估
# ---------------------------------------------------------------------------
def validate_prototype(doc: DesignDocument) -> Dict[str, Any]:
    """
    验证设计稿的完整性和可生成性，返回验证结果和置信度评分。
    置信度评分基于字段完整性、组件类型合法性和交互定义完整性。
    """
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "checks": {}
    }

    # 检查1: 画布尺寸
    if doc.width <= 0 or doc.height <= 0:
        validation_results["valid"] = False
        validation_results["errors"].append("画布尺寸必须为正数")
    else:
        validation_results["checks"]["canvas_size"] = "通过"

    # 检查2: 组件数量
    if len(doc.components) == 0:
        validation_results["valid"] = False
        validation_results["errors"].append("设计稿中没有任何组件")
    else:
        validation_results["checks"]["component_count"] = f"{len(doc.components)} 个组件"

    # 检查3: 组件类型合法性
    valid_types = {"button", "input", "text", "image", "container"}
    for i, comp in enumerate(doc.components):
        if comp.type not in valid_types:
            validation_results["valid"] = False
            validation_results["errors"].append(f"组件 #{i} 类型非法: {comp.type}")
        else:
            # 检查坐标是否在画布内
            if comp.x < 0 or comp.y < 0 or comp.x + comp.width > doc.width or comp.y + comp.height > doc.height:
                validation_results["warnings"].append(f"组件 '{comp.label}' 超出画布边界")

    # 检查4: 交互组件定义
    interactive_components = [c for c in doc.components if c.interactive]
    for comp in interactive_components:
        if not comp.action:
            validation_results["warnings"].append(f"交互组件 '{comp.label}' 未定义动作")

    # 计算置信度评分（0-100）
    score = 100.0
    deductions = 0.0

    # 字段完整性检查
    total_fields = 0
    filled_fields = 0
    for comp in doc.components:
        fields = ["type", "label", "x", "y", "width", "height", "color", "font_size"]
        for field_name in fields:
            total_fields += 1
            value = getattr(comp, field_name)
            if value not in (None, "", 0, False):
                filled_fields += 1

    if total_fields > 0:
        field_completeness = filled_fields / total_fields
        deductions += (1 - field_completeness) * 20  # 字段完整性占20分

    # 交互定义完整性
    if interactive_components:
        defined_actions = sum(1 for c in interactive_components if c.action)
        action_completeness = defined_actions / len(interactive_components)
        deductions += (1 - action_completeness) * 15  # 交互定义占15分

    # 画布利用率
    if doc.components:
        used_area = sum(c.width * c.height for c in doc.components)
        canvas_area = doc.width * doc.height
        if canvas_area > 0:
            utilization = min(used_area / canvas_area, 1.0)
            if utilization < 0.1:
                deductions += 5  # 画布利用率过低扣5分

    # 警告扣分
    deductions += len(validation_results["warnings"]) * 2  # 每个警告扣2分

    # 错误扣分
    if not validation_results["valid"]:
        deductions += 30  # 无效设计直接扣30分

    score = max(0, min(100, 100 - deductions))
    validation_results["confidence_score"] = round(score, 1)

    return validation_results


def generate_json_report(doc: DesignDocument, validation: Dict[str, Any]) -> Dict[str, Any]:
    """生成结构化 JSON 报告。"""
    report = {
        "title": doc.title,
        "canvas": {
            "width": doc.width,
            "height": doc.height,
            "breakpoints": doc.breakpoints
        },
        "components": {
            "total": len(doc.components),
            "interactive": sum(1 for c in doc.components if c.interactive),
            "types": {}
        },
        "validation": validation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "design-harness",
        "version": "1.0.2"
    }

    # 统计组件类型
    for comp in doc.components:
        if comp.type not in report["components"]["types"]:
            report["components"]["types"][comp.type] = 0
        report["components"]["types"][comp.type] += 1

    return report


def export_design(doc: DesignDocument, output_dir: str, fmt: str) -> Dict[str, str]:
    """
    将 DesignDocument 导出为指定格式的文件。
    返回生成的文件路径字典。
    """
    os.makedirs(output_dir, exist_ok=True)
    generated: Dict[str, str] = {}

    # 验证设计稿
    validation = validate_prototype(doc)

    if fmt == "html":
        html_content = generate_html(doc)
        html
