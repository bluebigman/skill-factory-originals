#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
未命名工具 — 独立实现脚本

依据功能规格（skills）独立编写，clean-room 实现。
仅依赖 Python 标准库，无第三方依赖。

功能概览：
  - 将输入数据/文件/URL 解析为结构化结果
  - 识别并保留关键信息
  - 按默认或自定义格式输出
  - 标注置信度（≥90% 直接输出 / 85-90% 建议复核 / <85% 需核实）
  - 支持批量处理
  - 内置 --selftest 离线自检

错误码：
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 文件读取失败
  E007 输出写入失败
  E008 未知命令/参数错误
  E009 URL 格式无效
  E010 内部处理异常
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

DEFAULT_OUTPUT_FIELDS = ["input_type", "content", "key_info", "confidence", "note"]

# 置信度阈值
CONFIDENCE_HIGH = 90     # ≥90% 直接输出
CONFIDENCE_MEDIUM = 85   # 85-90% 建议复核
# <85% 需核实

# 错误码 → 标准化话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "文件读取失败，请检查文件路径和权限。",
    "E007": "输出写入失败，请检查输出路径和权限。",
    "E008": "未知命令或参数错误，请使用 --help 查看帮助。",
    "E009": "URL 格式无效，请提供合法的 http/https 链接。",
    "E010": "内部处理异常，请重试或检查输入。",
}


# ============================================================
# 错误处理辅助
# ============================================================

class SkillError(Exception):
    """技能异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "未知错误")
        super().__init__(f"{code}: {self.message}")


def raise_error(code: str, detail: Optional[str] = None) -> None:
    """抛出标准错误。"""
    if detail:
        raise SkillError(code, f"{ERROR_MESSAGES.get(code, '未知错误')} {detail}")
    raise SkillError(code)


# ============================================================
# 核心逻辑：输入解析与结构化
# ============================================================

def detect_input_type(raw_input: str) -> str:
    """
    识别输入类型：url / file / text
    返回类型字符串。
    """
    if not raw_input or not raw_input.strip():
        raise_error("E001")

    stripped = raw_input.strip()

    # URL 检测（http/https）
    if stripped.lower().startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(stripped)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return "url"
        raise_error("E009")

    # 文件路径检测（存在且是文件）
    if os.path.isfile(stripped):
        return "file"

    # 默认按文本处理
    return "text"


def extract_key_info(content: str) -> List[str]:
    """
    从文本中提取关键信息（简单启发式）：
      - 邮箱
      - 电话号码
      - 日期（YYYY-MM-DD / YYYY/MM/DD）
      - 大写字母缩写（2-6 位）
      - 数字金额（含货币符号）
    返回关键信息列表。
    """
    key_items: List[str] = []

    # 邮箱
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
    key_items.extend(emails)

    # 电话号码（简单匹配：+86 或 1xx-xxxx-xxxx 或连续数字）
    phones = re.findall(r"(?:\+?86[- ]?)?1[3-9]\d{9}", content.replace("-", "").replace(" ", ""))
    key_items.extend(phones)

    # 日期
    dates = re.findall(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", content)
    key_items.extend(dates)

    # 大写缩写（2-6 位）
    acronyms = re.findall(r"\b[A-Z]{2,6}\b", content)
    key_items.extend(acronyms)

    # 金额
    amounts = re.findall(r"(?:￥|¥|\$|€|£)\s?\d+(?:\.\d{1,2})?", content)
    key_items.extend(amounts)

    # 去重并保留顺序
    seen = set()
    unique_items = []
    for item in key_items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)

    return unique_items


def compute_confidence(content: str, key_info: List[str]) -> Tuple[int, Optional[str]]:
    """
    计算置信度（0-100）。
    规则：
      - 内容非空且 key_info 非空：90 分以上
      - 内容非空但 key_info 为空：86 分（建议复核）
      - 内容过短（<5 字符）：80 分（需核实）
    返回 (置信度, 备注)
    """
    if not content or not content.strip():
        return 0, "输入内容为空"

    content_len = len(content.strip())

    if content_len < 5:
        return 80, "内容过短，关键信息可能不完整"

    if key_info:
        # 有关键信息，置信度较高
        return 92, None
    else:
        # 无关键信息，但内容非空
        return 86, "未提取到明确关键信息，建议人工复核"


def process_single_input(raw_input: str, custom_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    处理单个输入，返回结构化结果字典。
    """
    try:
        input_type = detect_input_type(raw_input)
    except SkillError:
        raise

    # 根据类型获取内容
    if input_type == "file":
        try:
            with open(raw_input.strip(), "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            raise_error("E006", f"路径: {raw_input.strip()}")
    elif input_type == "url":
        # 能力边界：不访问网络，直接标注
        raise_error("E004", "本工具不访问网络或外部服务，无法处理 URL 内容。请下载后作为文件或文本输入。")
    else:  # text
        content = raw_input.strip()

    # 提取关键信息
    key_info = extract_key_info(content)

    # 置信度
    confidence, note = compute_confidence(content, key_info)

    # 组装结果
    result: Dict[str, Any] = {
        "input_type": input_type,
        "content": content,
        "key_info": key_info,
        "confidence": confidence,
        "note": note or "",
    }

    # 按自定义字段过滤（如果指定）
    if custom_fields:
        filtered = {}
        for field in custom_fields:
            if field in result:
                filtered[field] = result[field]
        return filtered

    return result


def process_batch(inputs: List[str], custom_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。
    任一输入出错时，记录错误并继续处理其余输入。
    """
    results = []
    for item in inputs:
        try:
            result = process_single_input(item, custom_fields)
            results.append({"status": "ok", "data": result})
        except SkillError as e:
            results.append({"status": "error", "code": e.code, "message": e.message})
    return results


# ============================================================
# 输出格式化
# ============================================================

def format_output(results: Any, output_format: str = "json") -> str:
    """
    将结果格式化为指定格式输出。
    支持：json / text
    """
    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    elif output_format == "text":
        return format_as_text(results)
    else:
        raise_error("E003", f"不支持的输出格式: {output_format}")


def format_as_text(results: Any) -> str:
    """将结果格式化为可读文本。"""
    lines = []

    if isinstance(results, list):
        for idx, item in enumerate(results, 1):
            lines.append(f"[{idx}]")
            if isinstance(item, dict):
                if item.get("status") == "error":
                    lines.append(f"  错误: {item.get('code')} - {item.get('message')}")
                else:
                    data = item.get("data", {})
                    lines.append(f"  类型: {data.get('input_type', 'N/A')}")
                    lines.append(f"  内容: {str(data.get('content', ''))[:100]}")
                    lines.append(f"  关键信息: {', '.join(data.get('key_info', [])) or '无'}")
                    lines.append(f"  置信度: {data.get('confidence', 0)}%")
                    if data.get("note"):
                        lines.append(f"  备注: {data['note']}")
            else:
                lines.append(f"  {item}")
    elif isinstance(results, dict):
        for key, value in results.items():
            lines.append(f"{key}: {value}")
    else:
        lines.append(str(results))

    return "\n".join(lines)


# ============================================================
# 主流程
# ============================================================

def run_pipeline(args: argparse.Namespace) -> int:
    """
    标准流程：
      1. 收集输入
      2. 执行核心处理
      3. 输出与校验
    """
    # Step 1: 输入收集
    if args.input:
        inputs = args.input
    elif args.file:
        # 从文件读取每行作为一个输入
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                inputs = [line.strip() for line in f if line.strip()]
        except OSError:
            raise_error("E006", f"路径: {args.file}")
    else:
        raise_error("E001")

    # 检查关键信息（输入列表非空）
    if not inputs:
        raise_error("E002", "输入列表为空")

    # Step 2: 核心处理
    custom_fields = args.fields if args.fields else None

    if args.batch:
        results = process_batch(inputs, custom_fields)
    else:
        # 单条处理模式：只取第一个输入
        try:
            result = process_single_input(inputs[0], custom_fields)
            results = [{"status": "ok", "data": result}]
        except SkillError as e:
            # 单条模式遇到错误直接返回错误信息
            print(f"{e.code}: {e.message}", file=sys.stderr)
            return 1

    # Step 3: 输出
    output_text = format_output(results, args.output_format)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
        except OSError:
            raise_error("E007", f"路径: {args.output}")
    else:
        print(output_text)

    return 0


# ============================================================
# 自检（selftest）
# ============================================================

def selftest() -> int:
    """
    内置离线自检，验证核心逻辑正确性。
    不依赖外部文件/网络。
    """
    print("=== 自检开始 ===")

    # 测试 1: detect_input_type
    assert detect_input_type("hello world") == "text", "文本类型检测失败"
    assert detect_input_type("https://example.com") == "url", "URL 类型检测失败"
    print("[PASS] detect_input_type")

    # 测试 2: extract_key_info
    sample_text = "联系 test@example.com 或 13812345678，日期 2024-01-15，金额 $99.99"
    keys = extract_key_info(sample_text)
    assert "test@example.com" in keys, "邮箱提取失败"
    assert "13812345678" in keys, "电话提取失败"
    assert "2024-01-15" in keys, "日期提取失败"
    assert "$99.99" in keys, "金额提取失败"
    print("[PASS] extract_key_info")

    # 测试 3: compute_confidence
    conf, note = compute_confidence("这是一段足够长的测试文本内容", ["test"])
    assert conf >= 90, "高置信度判定失败"
    conf2, _ = compute_confidence("短", [])
    assert conf2 < 85, "低置信度判定失败"
    print("[PASS] compute_confidence")

    # 测试 4: process_single_input（文本）
    result = process_single_input("联系 test@example.com 或 13812345678")
    assert result["input_type"] == "text"
    assert result["confidence"] >= 85
    assert len(result["key_info"]) >= 2
    print("[PASS] process_single_input (text)")

    # 测试 5: process_single_input（空输入 → E001）
    try:
        process_single_input("")
        assert False, "空输入应报 E001"
    except SkillError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
    print("[PASS] 空输入 E001")

    # 测试 6: process_single_input（URL → E004）
    try:
        process_single_input("https://example.com")
        assert False, "URL 应报 E004"
    except SkillError as e:
        assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"
    print("[PASS] URL 边界 E004")

    # 测试 7: process_batch 批量
    batch_inputs = ["第一段内容 test@example.com", "第二段 13911112222", ""]
    batch_results = process_batch(batch_inputs)
    assert len(batch_results) == 3
    assert batch_results[0]["status"] == "ok"
    assert batch_results[2]["status"] == "error"
    assert batch_results[2]["code"] == "E001"
    print("[PASS] process_batch")

    # 测试 8: format_output
    json_str = format_output([{"a": 1}], "json")
    assert json.loads(json_str)[0]["a"] == 1
    text_str = format_output([{"status": "ok", "data": {"input_type": "text", "content": "x", "key_info": [], "confidence": 86, "note": ""}}], "text")
    assert "置信度: 86%" in text_str
    print("[PASS] format_output")

    print("=== 全部自检通过 ===")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="未命名工具 — 将输入数据/文件/URL 转换为结构化结果",
        epilog="示例: python main.py -i '联系 test@example.com' --format json"
    )

    # 输入参数（互斥组）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-i", "--input", nargs="+", help="输入内容（可多个，空格分隔）")
    input_group.add_argument("-f", "--file", help="从文件读取输入，每行一个")
    parser.add_argument("-b", "--batch", action="store_true", help="批量模式（处理所有输入）")
    parser.add_argument("--fields", nargs="+", help="自定义输出字段，如 content key_info")
    parser.add_argument("--format", dest="output_format", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("-o", "--output", help="输出到文件（默认 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    try:
        if args.selftest:
            return selftest()
        return run_pipeline(args)
    except SkillError as e:
        print(f"{e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:  # 兜底异常
        print(f"E010: 内部处理异常 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
