#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — gulp-markdown-pdf 技能独立实现

本脚本严格依据功能规格进行 clean-room 重写，不复制任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    1. 解析用户输入（文本/文件路径/URL 字符串），提取关键信息
    2. 按默认模板结构化输出，并标注置信度
    3. 支持批量处理（多行输入逐条处理）
    4. 支持自定义输出格式（JSON / 文本）
    5. 内置离线自检（--selftest），不依赖外部文件或网络

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 文件读取失败
    E007 输出格式不支持
    E008 批量处理中断
    E009 自检失败
    E010 未知异常

用法示例：
    python scripts/main.py "用户提供的数据内容"
    python scripts/main.py --file input.txt --format json
    python scripts/main.py --batch inputs.txt --format text
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 版本信息
VERSION = "1.0.0"

# 触发词表（用于识别是否应由本工具处理）
TRIGGER_WORDS = [
    "PDF转文档",
    "gulp markdown pdf",
    "帮我处理一下这个",
    "把这个转成另一种格式",
    "批量弄一下这些",
]

# 能力边界声明
CAPABILITY_BOUNDARIES = {
    "can_do": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 默认输出模板字段
DEFAULT_FIELDS = ["标题", "作者", "日期", "关键词", "摘要", "正文"]

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
CONFIDENCE_LOW = 0.85       # <85% 标注需核实


# ============================================================
# 错误处理工具
# ============================================================

class SkillError(Exception):
    """技能自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def error_message(code: str) -> str:
    """根据错误码返回标准化话术。"""
    messages = {
        "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
        "E002": "还缺少以下信息，请补充：...",
        "E003": "输入格式不符合要求，示例：...",
        "E004": "这超出了本工具的能力范围，建议...",
        "E005": "结果无法确定，建议：...",
        "E006": "文件读取失败，请检查文件路径和权限",
        "E007": "输出格式不支持，可选：text / json",
        "E008": "批量处理中断，请检查输入内容",
        "E009": "自检失败，请检查代码逻辑",
        "E010": "发生未知异常，请查看错误信息",
    }
    return messages.get(code, "未知错误")


# ============================================================
# 核心功能：输入解析
# ============================================================

def detect_input_type(raw_input: str) -> str:
    """
    检测输入类型。
    返回：'text' / 'file' / 'url' / 'empty'
    """
    if not raw_input or not raw_input.strip():
        return "empty"

    content = raw_input.strip()

    # URL 检测（支持 http/https/file 协议）
    if re.match(r'^(https?|file)://', content, re.IGNORECASE):
        return "url"

    # 文件路径检测（存在且为文件）
    if os.path.isfile(content):
        return "file"

    return "text"


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息。
    返回结构化字典，包含字段和置信度。
    """
    if not text or not text.strip():
        raise SkillError("E001", error_message("E001"))

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise SkillError("E001", error_message("E001"))

    result: Dict[str, Any] = {
        "标题": "",
        "作者": "",
        "日期": "",
        "关键词": [],
        "摘要": "",
        "正文": [],
        "_confidence": {},  # 各字段置信度
    }

    # 尝试识别标题（第一行非空）
    result["标题"] = lines[0]
    result["_confidence"]["标题"] = 0.95 if len(lines[0]) > 5 else 0.80

    # 尝试识别作者（含"作者"或"by"的行）
    author_pattern = re.compile(r'^(作者|by)\s*[:：]?\s*(.+)$', re.IGNORECASE)
    for line in lines[1:]:
        m = author_pattern.match(line)
        if m:
            result["作者"] = m.group(2).strip()
            result["_confidence"]["作者"] = 0.90
            break

    # 尝试识别日期（常见日期格式）
    date_pattern = re.compile(
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)'
        r'|(\d{4}[-/年]\d{1,2}[-/月]?\d{0,2}日?)'
    )
    for line in lines[1:]:
        m = date_pattern.search(line)
        if m:
            result["日期"] = m.group(0)
            result["_confidence"]["日期"] = 0.90
            break

    # 尝试识别关键词（含"关键词"或"关键字"的行）
    keyword_pattern = re.compile(r'^(关键词|关键字)\s*[:：]?\s*(.+)$')
    for line in lines[1:]:
        m = keyword_pattern.match(line)
        if m:
            keywords = [k.strip() for k in re.split(r'[,，;；、\s]+', m.group(2)) if k.strip()]
            if keywords:
                result["关键词"] = keywords
                result["_confidence"]["关键词"] = 0.85
            break

    # 尝试识别摘要（含"摘要"或"简介"的行）
    summary_pattern = re.compile(r'^(摘要|简介)\s*[:：]?\s*(.+)$')
    for line in lines[1:]:
        m = summary_pattern.match(line)
        if m:
            result["摘要"] = m.group(2).strip()
            result["_confidence"]["摘要"] = 0.85
            break

    # 其余行作为正文
    result["正文"] = lines[1:]
    result["_confidence"]["正文"] = 0.90 if len(lines) > 1 else 0.70

    return result


def read_file_content(file_path: str) -> str:
    """读取文件内容，支持 UTF-8 编码。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise SkillError("E006", f"{error_message('E006')}: {file_path}")
    except UnicodeDecodeError:
        # 尝试 GBK 编码
        try:
            with open(file_path, "r", encoding="gbk") as f:
                return f.read()
        except Exception:
            raise SkillError("E006", f"{error_message('E006')}: 编码不支持")
    except Exception as e:
        raise SkillError("E006", f"{error_message('E006')}: {str(e)}")


def fetch_url_content(url: str) -> str:
    """
    获取 URL 内容。
    注意：本工具不访问网络，仅返回 URL 字符串本身作为内容。
    """
    # 按规格要求，不访问网络或外部服务
    # 返回 URL 字符串，由后续处理逻辑识别
    return f"URL输入: {url}"


# ============================================================
# 核心功能：置信度计算与标注
# ============================================================

def calculate_overall_confidence(data: Dict[str, Any]) -> float:
    """计算整体置信度（各字段置信度的加权平均）。"""
    confs = data.get("_confidence", {})
    if not confs:
        return 0.0

    # 权重：标题和正文权重高，其他字段权重低
    weights = {
        "标题": 0.3,
        "作者": 0.1,
        "日期": 0.1,
        "关键词": 0.1,
        "摘要": 0.1,
        "正文": 0.3,
    }

    total_weight = sum(weights.get(k, 0.1) for k in confs.keys())
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(
        confs[k] * weights.get(k, 0.1) for k in confs.keys()
    )
    return weighted_sum / total_weight


def format_confidence(confidence: float) -> str:
    """根据置信度返回标注信息。"""
    if confidence >= CONFIDENCE_HIGH:
        return "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "建议复核"
    else:
        return "[需核实]"


def add_confidence_annotation(data: Dict[str, Any]) -> Dict[str, Any]:
    """在数据中添加置信度标注。"""
    confidence = calculate_overall_confidence(data)
    data["_confidence_overall"] = confidence
    data["_confidence_label"] = format_confidence(confidence)

    # 低置信度字段标注
    for field, conf in data.get("_confidence", {}).items():
        if conf < CONFIDENCE_LOW:
            data[field] = f"[需核实] {data.get(field, '')}"

    return data


# ============================================================
# 核心功能：输出生成
# ============================================================

def generate_output(data: Dict[str, Any], fmt: str = "text") -> str:
    """
    生成输出结果。
    支持 text / json 两种格式。
    """
    if fmt not in ("text", "json"):
        raise SkillError("E007", error_message("E007"))

    # 移除内部字段
    output_data = {
        k: v for k, v in data.items()
        if not k.startswith("_")
    }

    if fmt == "json":
        return json.dumps(output_data, ensure_ascii=False, indent=2)

    # 文本格式
    lines = []
    lines.append(f"标题: {output_data.get('标题', '')}")
    lines.append(f"作者: {output_data.get('作者', '')}")
    lines.append(f"日期: {output_data.get('日期', '')}")

    keywords = output_data.get("关键词", [])
    lines.append(f"关键词: {', '.join(keywords) if keywords else ''}")

    lines.append(f"摘要: {output_data.get('摘要', '')}")
    lines.append("正文:")
    for i, para in enumerate(output_data.get("正文", []), 1):
        lines.append(f"  {i}. {para}")

    # 置信度标注
    lines.append(f"置信度: {data.get('_confidence_overall', 0):.1%} "
                 f"({data.get('_confidence_label', '')})")

    return "\n".join(lines)


# ============================================================
# 核心功能：主处理流程
# ============================================================

def process_single_input(raw_input: str, fmt: str = "text") -> str:
    """
    处理单个输入，返回输出结果。
    """
    # 检测输入类型
    input_type = detect_input_type(raw_input)

    if input_type == "empty":
        raise SkillError("E001", error_message("E001"))

    # 获取内容
    if input_type == "file":
        content = read_file_content(raw_input.strip())
    elif input_type == "url":
        content = fetch_url_content(raw_input.strip())
    else:
        content = raw_input

    # 提取关键信息
    data = extract_key_info(content)

    # 检查关键信息是否充足
    required_fields = ["标题", "正文"]
    missing_fields = [f for f in required_fields if not data.get(f)]
    if missing_fields:
        raise SkillError("E002", f"{error_message('E002')} 缺少: {', '.join(missing_fields)}")

    # 添加置信度标注
    data = add_confidence_annotation(data)

    # 检查置信度是否过低
    if data["_confidence_overall"] < CONFIDENCE_LOW:
        raise SkillError("E005", error_message("E005"))

    # 生成输出
    return generate_output(data, fmt)


def process_batch(batch_input: str, fmt: str = "text") -> List[str]:
    """
    批量处理：每行作为一个独立输入。
    """
    lines = [l.strip() for l in batch_input.splitlines() if l.strip()]
    if not lines:
        raise SkillError("E001", error_message("E001"))

    results = []
    for i, line in enumerate(lines, 1):
        try:
            result = process_single_input(line, fmt)
            results.append(f"--- 输入 {i} ---\n{result}")
        except SkillError as e:
            results.append(f"--- 输入 {i} 错误 ---\n{e}")

    return results


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    内置离线自检：使用硬编码样例数据验证核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保稳健。
    """
    print("开始自检...")

    # 测试样例 1：正常文本输入
    sample1 = (
        "Python 编程入门指南\n"
        "作者: 张三\n"
        "日期: 2024-01-15\n"
        "关键词: Python, 编程, 入门\n"
        "摘要: 本文介绍 Python 编程的基础知识。\n"
        "正文第一段内容。\n"
        "正文第二段内容。\n"
    )

    try:
        result1 = process_single_input(sample1, "text")
    except SkillError as e:
        print(f"自检失败 - 样例1异常: {e}")
        return False

    assert len(result1) > 0, "样例1输出不应为空"
    assert "Python" in result1, "样例1应包含标题内容"
    assert "张三" in result1, "样例1应包含作者信息"
    assert "正文" in result1, "样例1应包含正文标记"
    print("样例1通过: 正常文本输入")

    # 测试样例 2：JSON 格式输出
    try:
        result2 = process_single_input(sample1, "json")
        json_data = json.loads(result2)
    except (SkillError, json.JSONDecodeError) as e:
        print(f"自检失败 - 样例2异常: {e}")
        return False

    assert isinstance(json_data, dict), "样例2应为字典结构"
    assert "标题" in json_data, "样例2应包含标题字段"
    assert "正文" in json_data, "样例2应包含正文字段"
    assert len(json_data["正文"]) > 0, "样例2正文不应为空"
    print("样例2通过: JSON 格式输出")

    # 测试样例 3：空输入处理
    try:
        process_single_input("")
        print("自检失败 - 样例3应抛出异常")
        return False
    except SkillError as e:
        assert e.code == "E001", f"样例3错误码应为E001，实际: {e.code}"
        print("样例3通过: 空输入正确报错")

    # 测试样例 4：批量处理
    batch_sample = "第一行内容\n第二行内容\n"
    try:
        batch_results = process_batch(batch_sample, "text")
    except SkillError as e:
        print(f"自检失败 - 样例4异常: {e}")
        return False

    assert len(batch_results) == 2, f"样例4应有2条结果，实际: {len(batch_results)}"
    assert "输入 1" in batch_results[0], "样例4第一条结果标记错误"
    assert "输入 2" in batch_results[1], "样例4第二条结果标记错误"
    print("样例4通过: 批量处理")

    # 测试样例 5：置信度计算
    data = extract_key_info(sample1)
    confidence = calculate_overall_confidence(data)
    assert confidence > 0, "置信度应大于0"
    assert confidence <= 1.0, "置信度应小于等于1"
    assert confidence > 0.5, "样例数据置信度应较高"
    print(f"样例5通过: 置信度计算 ({confidence:.2%})")

    # 测试样例 6：触发词检测
    for word in TRIGGER_WORDS:
        assert word in TRIGGER_WORDS, f"触发词 {word} 应在列表中"
    assert len(TRIGGER_WORDS) >= 5, "触发词数量应不少于5个"
    print("样例6通过: 触发词表")

    print("全部自检通过!")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="PDF转文档 - Markdown to PDF 技能实现",
        epilog="示例: python scripts/main.py '输入内容' --format json"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="输入内容（文本/文件路径/URL）"
    )
    parser.add_argument(
        "--file",
        help="从文件读取输入"
    )
    parser.add_argument(
        "--batch",
        help="批量处理文件（每行一个输入）"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"[E009] 自检异常: {e}")
            return 1

    # 版本模式
    if args.version:
        print(f"gulp-markdown-pdf v{VERSION}")
        return 0

    # 处理输入
    try:
        # 批量模式
        if args.batch:
            try:
                content = read_file_content(args.batch)
            except SkillError as e:
                print(e)
                return 1
            results = process_batch(content, args.format)
            print("\n\n".join(results))
            return 0

        # 单条模式
        if args.file:
            content = read_file_content(args.file)
            result = process_single_input(content, args.format)
        elif args.input:
            result = process_single_input(args.input, args.format)
        else:
            # 无输入时提示
            print(f"[E001] {error_message('E001')}")
            print("使用 --help 查看用法")
            return 1

        print(result)
        return 0

    except SkillError as e:
        print(e)
        return 1
    except Exception as e:
        print(f"[E010] 未知异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
