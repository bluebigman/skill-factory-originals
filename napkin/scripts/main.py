#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
napkin - 未命名工具
A Claude Code skill that gives the agent persistent memory of its mistakes
via a per-repo markdown scratchpad.

本脚本为 clean-room 独立实现，仅依据功能规格编写。
支持 --selftest 离线自检，不依赖外部文件/网络/当前工作目录。
"""

import argparse
import sys
import json
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{'input': '...', 'output_format': 'json'}",
    "E004": "这超出了本工具的能力范围，建议：明确输入范围或使用其他专业工具",
    "E005": "结果无法确定，建议：补充更多信息或人工复核",
    "E006": "输入内容为空或仅包含空白字符",
    "E007": "输出格式不支持，支持格式：json / text / markdown",
    "E008": "置信度计算失败，请检查输入数据",
    "E009": "批量处理时出现错误，请检查每个输入项的格式",
    "E010": "内部逻辑错误，请报告此问题",
}


# ============================================================
# 核心数据结构
# ============================================================

class ProcessedResult:
    """处理结果的数据结构"""
    def __init__(self, content: Any, confidence: float, warnings: List[str] = None):
        self.content = content
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(raw_input: Any) -> Tuple[bool, str]:
    """
    校验输入是否有效
    返回: (是否有效, 错误码或空字符串)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str) and not raw_input.strip():
        return False, "E006"
    if isinstance(raw_input, (list, dict)) and len(raw_input) == 0:
        return False, "E006"
    return True, ""


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段
    支持：字符串、字典、列表
    """
    if isinstance(data, str):
        # 尝试解析 JSON 字符串
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return {"type": "json_object", "fields": parsed}
            elif isinstance(parsed, list):
                return {"type": "json_array", "items": parsed}
        except json.JSONDecodeError:
            pass
        return {"type": "text", "content": data.strip()}
    elif isinstance(data, dict):
        return {"type": "object", "fields": data}
    elif isinstance(data, list):
        return {"type": "array", "items": data}
    else:
        return {"type": "unknown", "content": str(data)}


def calculate_confidence(extracted: Dict[str, Any]) -> float:
    """
    计算置信度
    规则：
    - 结构化数据（dict/list）且字段完整：≥90%
    - 文本数据：根据长度和格式判断
    - 数据缺失：降低置信度
    """
    data_type = extracted.get("type", "unknown")
    confidence = 0.0

    if data_type == "object":
        fields = extracted.get("fields", {})
        if len(fields) >= 3:
            confidence = 0.95
        elif len(fields) >= 1:
            confidence = 0.88
        else:
            confidence = 0.70
    elif data_type == "array":
        items = extracted.get("items", [])
        if len(items) > 0:
            confidence = 0.92
        else:
            confidence = 0.60
    elif data_type == "json_object":
        fields = extracted.get("fields", {})
        if len(fields) >= 3:
            confidence = 0.96
        elif len(fields) >= 1:
            confidence = 0.89
        else:
            confidence = 0.72
    elif data_type == "json_array":
        items = extracted.get("items", [])
        if len(items) > 0:
            confidence = 0.93
        else:
            confidence = 0.65
    elif data_type == "text":
        content = extracted.get("content", "")
        if len(content) > 100:
            confidence = 0.85
        elif len(content) > 20:
            confidence = 0.75
        else:
            confidence = 0.50
    else:
        confidence = 0.40

    return min(max(confidence, 0.0), 1.0)


def format_output(result: ProcessedResult, output_format: str) -> str:
    """
    将结果格式化为指定格式
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        lines.append("处理结果: " + json.dumps(result.content, ensure_ascii=False))
        lines.append("置信度: {:.0%}".format(result.confidence))
        if result.warnings:
            lines.append("警告:")
            for w in result.warnings:
                lines.append("  - " + w)
        return "\n".join(lines)
    elif output_format == "markdown":
        lines = []
        lines.append("## 处理结果")
        lines.append("")
        lines.append("**置信度**: {:.0%}".format(result.confidence))
        if result.warnings:
            lines.append("")
            lines.append("**警告**:")
            for w in result.warnings:
                lines.append("- " + w)
        lines.append("")
        lines.append("**内容**:")
        lines.append("
