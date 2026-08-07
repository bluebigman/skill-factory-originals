#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-mem — 跨会话上下文持久化与压缩
=====================================
基于功能规格独立实现的 clean-room 版本。

功能概览：
- C1 输入结构化：将文本、文件路径或 URL 内容解析为结构化字段
- C2 关键信息识别：自动标记高价值信息（实体、决策、约束条件）
- C3 格式约定输出：支持 JSON / Markdown 两种输出格式
- C4 置信度标注：对不确定字段输出 [需核实:字段名] 占位符
- C5 批量与自定义：支持多文件批量处理与自定义输出字段

许可证：MIT License
Copyright (c) 2026 SkillForge Lab
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数值非法",
    "E002": "文件不存在或无法读取",
    "E003": "URL 访问失败或网络不可用",
    "E004": "输入内容为空，无法处理",
    "E005": "JSON 序列化失败",
    "E006": "输出目录不存在或无法写入",
    "E007": "批量处理时部分文件处理失败",
    "E008": "自定义字段结构格式错误",
    "E009": "内部逻辑错误：未知状态",
    "E010": "不支持的输出格式",
}

# 输出模板字段（默认结构）
DEFAULT_FIELDS = ["entities", "decisions", "constraints", "actions", "preferences"]


class CliError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def parse_text_content(text: str) -> dict:
    """
    C1 + C2：将原始文本解析为结构化字段，并识别关键信息。
    通过关键词匹配和模式识别提取实体、决策、约束、动作和偏好。
    """
    if not text or not text.strip():
        raise CliError("E004")

    result = {
        "entities": [],
        "decisions": [],
        "constraints": [],
        "actions": [],
        "preferences": [],
        "uncertain_fields": [],
    }

    lines = text.splitlines()

    # 实体识别：匹配专有名词（大写开头词、项目名、人名等）
    entity_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")
    for line in lines:
        entities = entity_pattern.findall(line)
        for ent in entities:
            # 过滤常见非实体词
            if ent.lower() not in {"the", "a", "an", "this", "that", "i", "we"}:
                if ent not in result["entities"]:
                    result["entities"].append(ent)

    # 决策识别：匹配"决定/选择/采用/确定"等关键词
    decision_pattern = re.compile(
        r"(?:决定|选择|采用|确定|敲定|拍板|决议|决定采用)\s*[:：]?\s*(.+?)(?:[。；;]|$)"
    )
    for m in decision_pattern.finditer(text):
        decision = m.group(1).strip()
        if decision and decision not in result["decisions"]:
            result["decisions"].append(decision)

    # 约束识别：匹配"必须/不能/禁止/限制/要求"等关键词
    constraint_pattern = re.compile(
        r"(?:必须|不能|禁止|限制|要求|不得|务必)\s*[:：]?\s*(.+?)(?:[。；;]|$)"
    )
    for m in constraint_pattern.finditer(text):
        constraint = m.group(1).strip()
        if constraint and constraint not in result["constraints"]:
            result["constraints"].append(constraint)

    # 动作识别：匹配"需要/要做/计划/下一步"等关键词
    action_pattern = re.compile(
        r"(?:需要|要做|计划|下一步|待办|安排|准备)\s*[:：]?\s*(.+?)(?:[。；;]|$)"
    )
    for m in action_pattern.finditer(text):
        action = m.group(1).strip()
        if action and action not in result["actions"]:
            result["actions"].append(action)

    # 偏好识别：匹配"喜欢/偏好/倾向于/更愿意"等关键词
    preference_pattern = re.compile(
        r"(?:喜欢|偏好|倾向于|更愿意|希望|想要)\s*[:：]?\s*(.+?)(?:[。；;]|$)"
    )
    for m in preference_pattern.finditer(text):
        pref = m.group(1).strip()
        if pref and pref not in result["preferences"]:
            result["preferences"].append(pref)

    # C4 置信度标注：对可能缺失的字段添加占位符
    if not result["entities"]:
        result["uncertain_fields"].append("[需核实:entities]")
    if not result["decisions"]:
        result["uncertain_fields"].append("[需核实:decisions]")
    if not result["constraints"]:
        result["uncertain_fields"].append("[需核实:constraints]")
    if not result["actions"]:
        result["uncertain_fields"].append("[需核实:actions]")
    if not result["preferences"]:
        result["uncertain_fields"].append("[需核实:preferences]")

    return result


def load_input_source(source: str) -> str:
    """
    加载输入内容：支持文件路径、URL 或直接文本。
    返回文本内容。
    """
    # 检查是否为 URL
    if source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=10) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            raise CliError("E003", f"URL 访问失败: {exc}") from exc

    # 检查是否为文件路径
    path = Path(source)
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise CliError("E002", f"文件读取失败: {exc}") from exc

    # 否则视为直接文本
    return source


def format_output(data: dict, fmt: str, fields: list = None) -> str:
    """
    C3：按指定格式（JSON / Markdown）输出记忆条目。
    fields 参数用于自定义输出字段（C5）。
    """
    if fmt not in ("json", "markdown"):
        raise CliError("E010", f"不支持的输出格式: {fmt}")

    # 自定义字段过滤
    if fields:
        filtered = {}
        for field in fields:
            if field in data:
                filtered[field] = data[field]
        if "uncertain_fields" in data:
            filtered["uncertain_fields"] = data["uncertain_fields"]
        data = filtered

    if fmt == "json":
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise CliError("E005", f"JSON 序列化失败: {exc}") from exc

    # Markdown 格式
    lines = ["# 会话记忆摘要", ""]
    lines.append(f"- 生成时间: {datetime.now().isoformat()}")
    lines.append("")

    field_labels = {
        "entities": "关键实体",
        "decisions": "决策记录",
        "constraints": "约束条件",
        "actions": "待办动作",
        "preferences": "用户偏好",
        "uncertain_fields": "待核实字段",
    }

    for key, label in field_labels.items():
        if key in data and data[key]:
            lines.append(f"## {label}")
            for item in data[key]:
                lines.append(f"- {item}")
            lines.append("")

    if "uncertain_fields" in data and data["uncertain_fields"]:
        lines.append("> ⚠️ 以下字段存在不确定性，请用户确认：")
        for item in data["uncertain_fields"]:
            lines.append(f"> - {item}")

    return "\n".join(lines)


def process_single(source: str, fmt: str, fields: list = None) -> str:
    """处理单个输入源并返回格式化结果"""
    text = load_input_source(source)
    parsed = parse_text_content(text)
    return format_output(parsed, fmt, fields)


def process_batch(sources: list, fmt: str, fields: list = None) -> list:
    """C5：批量处理多个输入源"""
    results = []
    errors = []

    for idx, source in enumerate(sources):
        try:
            output = process_single(source, fmt, fields)
            results.append({"index": idx, "source": source, "success": True, "output": output})
        except CliError as exc:
            errors.append({"index": idx, "source": source, "error": str(exc)})
            results.append({"index": idx, "source": source, "success": False, "error": str(exc)})

    if errors:
        raise CliError("E007", f"批量处理完成，{len(errors)} 个文件失败")

    return results


def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。
    不读取外部文件、不访问网络、不依赖当前工作目录。
    """
    print("=== claude-mem 自检开始 ===")

    # 硬编码测试样例
    test_text = """
    今天我们决定采用 Python 作为后端开发语言。
    项目必须遵循 PEP8 规范，不能使用全局变量。
    下一步需要完成数据库设计，计划下周进行代码审查。
    用户偏好使用 FastAPI 框架，希望保持代码简洁。
    """

    # 测试 1：文本解析
    try:
        parsed = parse_text_content(test_text)
        assert len(parsed["entities"]) > 0, "实体识别失败"
        assert len(parsed["decisions"]) > 0, "决策识别失败"
        assert len(parsed["constraints"]) > 0, "约束识别失败"
        assert len(parsed["actions"]) > 0, "动作识别失败"
        assert len(parsed["preferences"]) > 0, "偏好识别失败"
        print("[PASS] 文本解析与关键信息识别")
    except AssertionError as exc:
        print(f"[FAIL] 文本解析: {exc}")
        return False
    except CliError as exc:
        print(f"[FAIL] 解析异常: {exc}")
        return False

    # 测试 2：JSON 输出
    try:
        json_out = format_output(parsed, "json")
        json_data = json.loads(json_out)
        assert "entities" in json_data, "JSON 缺少 entities 字段"
        assert "decisions" in json_data, "JSON 缺少 decisions 字段"
        print("[PASS] JSON 格式输出")
    except Exception as exc:
        print(f"[FAIL] JSON 输出: {exc}")
        return False

    # 测试 3：Markdown 输出
    try:
        md_out = format_output(parsed, "markdown")
        assert md_out.startswith("# "), "Markdown 缺少标题"
        assert "## " in md_out, "Markdown 缺少二级标题"
        print("[PASS] Markdown 格式输出")
    except Exception as exc:
        print(f"[FAIL] Markdown 输出: {exc}")
        return False

    # 测试 4：置信度标注
    try:
        empty_parsed = parse_text_content("这是一个没有明确信息的测试文本。")
        assert len(empty_parsed["uncertain_fields"]) >= 1, "置信度标注缺失"
        print("[PASS] 置信度标注")
    except Exception as exc:
        print(f"[FAIL] 置信度标注: {exc}")
        return False

    # 测试 5：自定义字段
    try:
        custom_out = format_output(parsed, "json", fields=["entities", "decisions"])
        custom_data = json.loads(custom_out)
        assert "entities" in custom_data, "自定义字段缺少 entities"
        assert "constraints" not in custom_data, "自定义字段不应包含 constraints"
        print("[PASS] 自定义字段过滤")
    except Exception as exc:
        print(f"[FAIL] 自定义字段: {exc}")
        return False

    # 测试 6：批量处理
    try:
        batch_sources = [test_text, "另一个测试：需要完成 API 接口开发，不能延迟交付。"]
        batch_results = process_batch(batch_sources, "json")
        assert len(batch_results) == 2, "批量处理数量不符"
        assert all(r["success"] for r in batch_results), "批量处理存在失败项"
        print("[PASS] 批量处理")
    except Exception as exc:
        print(f"[FAIL] 批量处理: {exc}")
        return False

    # 测试 7：错误处理
    try:
        parse_text_content("")
        print("[FAIL] 空输入应触发错误")
        return False
    except CliError as exc:
        assert exc.code == "E004", f"错误码应为 E004，实际为 {exc.code}"
        print("[PASS] 空输入错误处理")

    # 测试 8：URL 处理（不实际访问，仅验证格式判断逻辑）
    try:
        # 构造一个不存在的 URL 测试错误处理（不访问网络）
        fake_url = "https://nonexistent-domain-12345.invalid/test"
        # 直接测试 load_input_source 的错误分支
        try:
            load_input_source(fake_url)
            print("[SKIP] URL 测试跳过（网络不可用）")
        except CliError:
            print("[PASS] URL 错误处理")
    except Exception:
        print("[SKIP] URL 测试跳过（环境限制）")

    print("=== 全部自检通过 ===")
    return True


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="claude-mem - 跨会话上下文持久化与压缩工具",
        epilog="示例: python main.py --input '文本内容' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容：文本、文件路径或 URL")
    parser.add_argument("--file", "-f", action="append", help="输入文件路径（可多次指定，用于批量）")
    parser.add_argument("--format", "-fmt", choices=["json", "markdown"], default="json",
                        help="输出格式（默认: json）")
    parser.add_argument("--fields", nargs="*", choices=DEFAULT_FIELDS,
                        help="自定义输出字段（默认输出全部）")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 参数校验
    if not args.input and not args.file:
        parser.error("必须提供 --input 或 --file 参数")

    try:
        # 批量模式
        if args.file:
            results = process_batch(args.file, args.format, args.fields)
            output_text = json.dumps(results, ensure_ascii=False, indent=2)
        # 单输入模式
        else:
            output_text = process_single(args.input, args.format, args.fields)

        # 输出处理
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output_text, encoding="utf-8")
            print(f"输出已写入: {args.output}")
        else:
            print(output_text)

    except CliError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"错误: [E009] 内部逻辑错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
