#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - feishu-docx 技能独立实现（clean-room 重写）

本脚本仅依据功能规格独立编写，不复制任何既有代码。
提供 CLI 入口与 --selftest 离线自检。

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 参数解析失败
    E007 文件读取失败
    E008 输出写入失败
    E009 内部逻辑错误
    E010 未支持的调用方式
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------
# 核心数据模型与常量
# ------------------------------------------------------------

# 能力边界声明
CAPABILITY_BOUNDARY = {
    "能做": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "不做": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 错误码与标准化话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "参数解析失败，请检查命令行参数",
    "E007": "文件读取失败：{path}",
    "E008": "输出写入失败：{path}",
    "E009": "内部逻辑错误，请报告开发者",
    "E010": "未支持的调用方式，请使用 CLI 或 Python API",
}


def get_error_message(code: str, **kwargs: Any) -> str:
    """根据错误码返回标准化话术。"""
    template = ERROR_MESSAGES.get(code, "未知错误")
    return template.format(**kwargs) if kwargs else template


# ------------------------------------------------------------
# 核心逻辑：结构化处理
# ------------------------------------------------------------

def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否合法。

    返回：(是否合法, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str):
        if not raw_input.strip():
            return False, "E001"
    elif isinstance(raw_input, (list, dict)):
        if len(raw_input) == 0:
            return False, "E001"
    else:
        return False, "E003"
    return True, None


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段并结构化。

    支持：
        - 字符串：按文本处理，提取基本信息
        - 列表：批量处理每个元素
        - 字典：直接作为结构化数据
    """
    if isinstance(data, str):
        # 文本输入：提取基本信息
        text = data.strip()
        fields = {
            "type": "text",
            "content": text,
            "length": len(text),
            "word_count": len(text.split()),
        }
    elif isinstance(data, list):
        # 批量输入
        fields = {
            "type": "batch",
            "items": [extract_key_fields(item) for item in data],
            "count": len(data),
        }
    elif isinstance(data, dict):
        # 结构化输入
        fields = dict(data)
        fields.setdefault("type", "structured")
    else:
        fields = {"type": "unknown", "content": str(data)}
    return fields


def calculate_confidence(fields: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）。

    规则：
        - 完整结构化数据：高置信度
        - 文本内容：根据长度和完整性判断
        - 存在缺失字段：降低置信度
    """
    confidence = 90.0  # 基础置信度

    if fields.get("type") == "structured":
        # 结构化数据，字段越完整置信度越高
        known_keys = [k for k in fields.keys() if not k.startswith("_")]
        if len(known_keys) >= 5:
            confidence = 95.0
        elif len(known_keys) >= 3:
            confidence = 88.0
        else:
            confidence = 80.0
    elif fields.get("type") == "text":
        # 文本数据，长度越长置信度越高
        length = fields.get("length", 0)
        if length > 100:
            confidence = 92.0
        elif length > 20:
            confidence = 85.0
        else:
            confidence = 75.0
    elif fields.get("type") == "batch":
        # 批量数据，看完成度
        items = fields.get("items", [])
        if items:
            avg_conf = sum(calculate_confidence(item) for item in items) / len(items)
            confidence = avg_conf
        else:
            confidence = 50.0

    # 检查是否有明显缺失
    if not fields:
        confidence = 30.0

    return max(0.0, min(100.0, confidence))


def format_result(fields: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    按约定格式组织输出结果。

    置信度标注规则：
        >=90%：直接输出
        85%-90%：标注"建议复核"
        <85%：标注"[需核实]"
    """
    result = {
        "data": fields,
        "confidence": confidence,
    }

    if confidence >= 90:
        result["status"] = "直接输出"
    elif confidence >= 85:
        result["status"] = "建议复核"
    else:
        result["status"] = "[需核实]"
        # 标注不确定点
        result["uncertainties"] = ["输入信息不完整或模糊，请人工复核关键结果"]

    return result


def process_input(raw_input: Any) -> Dict[str, Any]:
    """
    核心处理流程：
        1. 校验输入
        2. 提取关键字段
        3. 计算置信度
        4. 格式化输出
    """
    # Step 1: 校验
    valid, error_code = validate_input(raw_input)
    if not valid:
        raise ValueError(error_code)

    # Step 2: 提取关键字段
    fields = extract_key_fields(raw_input)

    # Step 3: 计算置信度
    confidence = calculate_confidence(fields)

    # Step 4: 格式化输出
    result = format_result(fields, confidence)
    return result


def batch_process(inputs: List[Any]) -> List[Dict[str, Any]]:
    """批量处理多个输入。"""
    results = []
    for item in inputs:
        try:
            result = process_input(item)
            results.append(result)
        except ValueError as e:
            error_code = str(e)
            results.append({
                "error": error_code,
                "message": get_error_message(error_code),
                "data": None,
                "confidence": 0,
                "status": "处理失败",
            })
    return results


# ------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="feishu-docx 技能工具 - 结构化数据处理",
        epilog="示例：python main.py --input 'hello world' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的数据/文件路径/URL",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取输入",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="feishu-docx 1.0.0",
    )
    return parser.parse_args(argv)


def read_input_from_file(path: str) -> str:
    """从文件读取输入。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError) as e:
        raise ValueError(f"E007:{path}:{str(e)}")


def write_output(data: str, path: Optional[str]) -> None:
    """写入输出。"""
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
        except (IOError, OSError) as e:
            raise ValueError(f"E008:{path}:{str(e)}")
    else:
        print(data)


def format_output(result: Dict[str, Any], fmt: str) -> str:
    """按指定格式输出结果。"""
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        if "error" in result:
            lines.append(f"[错误] {result['error']}: {result['message']}")
        else:
            lines.append(f"状态: {result['status']}")
            lines.append(f"置信度: {result['confidence']:.1f}%")
            if "uncertainties" in result:
                for u in result["uncertainties"]:
                    lines.append(f"⚠️ {u}")
            lines.append("---")
            lines.append(json.dumps(result["data"], ensure_ascii=False, indent=2))
        return "\n".join(lines)
    elif fmt == "markdown":
        lines = []
        if "error" in result:
            lines.append(f"## ❌ 处理失败\n\n**错误码**: {result['error']}\n\n{result['message']}")
        else:
            lines.append(f"## 处理结果\n\n**状态**: {result['status']}\n\n**置信度**: {result['confidence']:.1f}%")
            if "uncertainties" in result:
                lines.append("\n### ⚠️ 需核实项\n")
                for u in result["uncertainties"]:
                    lines.append(f"- {u}")
            lines.append("\n### 数据\n")
            lines.append("
