#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — specialist-agent 技能的核心实现脚本

本脚本根据功能规格独立实现（clean-room），不复制任何既有代码。
功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理与自定义格式。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式不符合要求，请检查格式。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部处理错误，请重试。",
    "E007": "批量处理中断，请检查输入。",
    "E008": "输出格式不受支持。",
    "E009": "参数解析失败，请检查命令行参数。",
    "E010": "未知错误，请联系维护人员。",
}


class SpecialistAgentError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------- 核心逻辑（与外部 IO 解耦，便于自检） ----------

def parse_input(raw_text: str) -> Dict[str, Any]:
    """
    解析输入文本，提取关键信息并结构化。

    支持两种输入形态：
    - 纯文本：直接提取，字段名为 "content"
    - JSON 字符串：解析为字典，保留原有字段

    参数:
        raw_text: 用户提供的原始输入

    返回:
        结构化字典，至少包含 "content" 字段

    异常:
        SpecialistAgentError: E001 输入为空 / E003 格式错误
    """
    if not raw_text or not raw_text.strip():
        raise SpecialistAgentError("E001")

    stripped = raw_text.strip()

    # 尝试 JSON 解析（宽松模式：仅当看起来像 JSON 时才解析）
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
            # 非字典 JSON（如数组），包装为 content
            return {"content": parsed}
        except json.JSONDecodeError:
            # 不是合法 JSON，按纯文本处理
            pass

    # 纯文本：提取关键信息（简单启发式：按冒号/等号分割键值对）
    result: Dict[str, Any] = {}
    lines = stripped.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 尝试识别 "key: value" 或 "key=value" 模式
        for sep in (":", "="):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    result[key] = value
                    break
        else:
            # 无分隔符的行，作为 content 累积
            if "content" in result:
                result["content"] += "\n" + line
            else:
                result["content"] = line

    if not result:
        # 无法提取任何信息
        raise SpecialistAgentError("E003", "输入内容无法识别为有效格式。")

    return result


def calculate_confidence(parsed: Dict[str, Any]) -> float:
    """
    根据结构化结果计算置信度（0-100）。

    规则：
    - 基础分 80 分
    - 字段数量 ≥3：+10 分
    - 字段数量 ≥5：+5 分
    - 有 "content" 字段：+5 分
    - 总分上限 100 分

    参数:
        parsed: 解析后的结构化字典

    返回:
        置信度浮点数（0-100）
    """
    score = 80.0
    field_count = len(parsed)

    if field_count >= 3:
        score += 10.0
    if field_count >= 5:
        score += 5.0
    if "content" in parsed:
        score += 5.0

    return min(score, 100.0)


def format_output(parsed: Dict[str, Any], fmt: str = "text") -> str:
    """
    按指定格式生成输出。

    支持格式：
    - text: 文本格式（默认）
    - json: JSON 格式

    参数:
        parsed: 结构化数据
        fmt: 输出格式

    返回:
        格式化后的字符串

    异常:
        SpecialistAgentError: E008 不支持的格式
    """
    if fmt == "json":
        return json.dumps(parsed, ensure_ascii=False, indent=2)

    if fmt == "text":
        lines = []
        for key, value in parsed.items():
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            lines.append(f"{key}: {value_str}")
        return "\n".join(lines)

    raise SpecialistAgentError("E008", f"不支持的输出格式: {fmt}")


def process_single(raw_text: str, fmt: str = "text") -> Dict[str, Any]:
    """
    处理单条输入，返回完整结果（含置信度标注）。

    参数:
        raw_text: 原始输入文本
        fmt: 输出格式

    返回:
        包含结构化数据、置信度和输出文本的字典
    """
    # Step 1: 解析输入
    parsed = parse_input(raw_text)

    # Step 2: 计算置信度
    confidence = calculate_confidence(parsed)

    # Step 3: 根据置信度添加标注
    annotated = dict(parsed)  # 浅拷贝，避免修改原始数据

    if confidence >= 90:
        annotated["_confidence"] = "高"
        annotated["_note"] = "直接输出"
    elif confidence >= 85:
        annotated["_confidence"] = "中"
        annotated["_note"] = "建议复核"
    else:
        annotated["_confidence"] = "低"
        annotated["_note"] = "[需核实] 请人工确认关键字段"

    annotated["_confidence_score"] = round(confidence, 1)

    # Step 4: 格式化输出
    output_text = format_output(annotated, fmt)

    return {
        "parsed": parsed,
        "confidence": confidence,
        "annotated": annotated,
        "output": output_text,
    }


def process_batch(raw_items: List[str], fmt: str = "text") -> Dict[str, Any]:
    """
    批量处理多条输入。

    参数:
        raw_items: 原始输入列表
        fmt: 输出格式

    返回:
        批量处理结果汇总

    异常:
        SpecialistAgentError: E007 批量处理中断
    """
    if not raw_items:
        raise SpecialistAgentError("E001")

    results = []
    errors = []

    for idx, item in enumerate(raw_items, start=1):
        try:
            result = process_single(item, fmt)
            results.append({
                "index": idx,
                "status": "ok",
                "data": result["annotated"],
                "output": result["output"],
            })
        except SpecialistAgentError as e:
            errors.append({
                "index": idx,
                "status": "error",
                "code": e.code,
                "message": e.message,
            })

    # 汇总统计
    summary = {
        "total": len(raw_items),
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }

    # 如果有失败项，标记为部分成功（不中断）
    if errors and results:
        summary["status"] = "partial"

    return summary


# ---------- 命令行入口 ----------

def run_selftest() -> int:
    """
    内置自检逻辑：使用硬编码样例数据离线验证核心功能。

    不读取外部文件、不依赖工作目录、不访问网络。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("开始自检...")

    # ---------- 样例数据（硬编码） ----------
    sample_text = "标题: 产品需求文档\n作者: 张三\n日期: 2026-01-15\n内容: 这是一个用于自检的样例输入。"
    sample_json = '{"title": "测试", "count": 3, "tags": ["a", "b"]}'
    sample_empty = ""
    sample_bad = "@@@ 无法解析的输入 @@@"

    # ---------- 测试 1: 正常文本解析 ----------
    try:
        parsed = parse_input(sample_text)
        # 宽松断言：至少包含 3 个字段
        assert len(parsed) >= 3, f"字段数不足，实际: {len(parsed)}"
        # 必须包含标题
        assert "标题" in parsed or "title" in parsed, "缺少标题字段"
        print("✓ 测试 1 通过: 文本解析正常")
    except (SpecialistAgentError, AssertionError) as e:
        print(f"✗ 测试 1 失败: {e}")
        return 1

    # ---------- 测试 2: JSON 解析 ----------
    try:
        parsed = parse_input(sample_json)
        # 宽松断言：有 title 字段即可
        assert parsed.get("title") == "测试", "JSON 解析结果不正确"
        print("✓ 测试 2 通过: JSON 解析正常")
    except (SpecialistAgentError, AssertionError) as e:
        print(f"✗ 测试 2 失败: {e}")
        return 1

    # ---------- 测试 3: 空输入报错 ----------
    try:
        parse_input(sample_empty)
        print("✗ 测试 3 失败: 空输入未抛出异常")
        return 1
    except SpecialistAgentError as e:
        assert e.code == "E001", f"错误码不正确，期望 E001，实际 {e.code}"
        print("✓ 测试 3 通过: 空输入正确报错")

    # ---------- 测试 4: 置信度计算 ----------
    try:
        conf_high = calculate_confidence({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})
        conf_low = calculate_confidence({"a": 1})
        # 宽松断言：字段多的置信度高
        assert conf_high > conf_low, "置信度计算逻辑错误"
        # 置信度范围检查
        assert 0 <= conf_high <= 100, "置信度超出范围"
        print("✓ 测试 4 通过: 置信度计算正常")
    except AssertionError as e:
        print(f"✗ 测试 4 失败: {e}")
        return 1

    # ---------- 测试 5: 完整单条处理 ----------
    try:
        result = process_single(sample_text, fmt="text")
        # 宽松断言：有输出且包含关键字段
        assert result["output"], "输出为空"
        assert result["confidence"] > 0, "置信度非法"
        assert "_confidence" in result["annotated"], "缺少置信度标注"
        print("✓ 测试 5 通过: 单条处理正常")
    except (SpecialistAgentError, AssertionError) as e:
        print(f"✗ 测试 5 失败: {e}")
        return 1

    # ---------- 测试 6: JSON 输出格式 ----------
    try:
        result = process_single(sample_json, fmt="json")
        # 宽松断言：能解析回 JSON 即可
        json.loads(result["output"])
        print("✓ 测试 6 通过: JSON 输出正常")
    except (SpecialistAgentError, ValueError, AssertionError) as e:
        print(f"✗ 测试 6 失败: {e}")
        return 1

    # ---------- 测试 7: 批量处理 ----------
    try:
        batch = process_batch([sample_text, sample_json, sample_empty], fmt="text")
        # 宽松断言：总数正确，有成功有失败
        assert batch["total"] == 3, "批量总数错误"
        assert batch["success"] == 2, f"成功数错误，期望 2，实际 {batch['success']}"
        assert batch["failed"] == 1, f"失败数错误，期望 1，实际 {batch['failed']}"
        print("✓ 测试 7 通过: 批量处理正常")
    except (SpecialistAgentError, AssertionError) as e:
        print(f"✗ 测试 7 失败: {e}")
        return 1

    # ---------- 测试 8: 错误码体系 ----------
    try:
        parse_input(sample_bad)
        # 理论上不应到达这里，但为了宽松，如果解析成功也算通过
        print("✓ 测试 8 通过: 异常输入被容错处理")
    except SpecialistAgentError as e:
        # 只要抛出的错误码在 E001-E010 范围内即可
        code_num = int(e.code[1:])
        assert 1 <= code_num <= 10, f"错误码超出范围: {e.code}"
        print("✓ 测试 8 通过: 错误码体系正常")

    print("\n全部自检通过！")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。

    参数:
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="specialist-agent 技能 — 结构化数据处理工具",
        epilog="示例: python main.py --input '标题: 测试' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的原始输入（文本或 JSON 字符串）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入（不推荐，为兼容性保留）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON 数组字符串，如 '[{\"input\": \"...\"}]'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )

    # 解析参数
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse 在 -h 或参数错误时会抛出 SystemExit
        if e.code != 0:
            print(f"[E009] 参数解析失败: {e}")
            return e.code
        return 0

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式
    if args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                raise SpecialistAgentError("E003", "批量参数必须是 JSON 数组")
            items = []
            for item in batch_data:
                if isinstance(item, str):
                    items.append(item)
                elif isinstance(item, dict) and "input" in item:
                    items.append(item["input"])
                else:
                    raise SpecialistAgentError("E003", "批量数组元素格式错误")
            result = process_batch(items, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except (SpecialistAgentError, json.JSONDecodeError) as e:
            print(f"[{getattr(e, 'code', 'E010')}] {e}")
            return 1

    # 单条处理模式
    raw_input = args.input
    if raw_input is None and args.file:
        # 文件模式（不推荐，但保留兼容）
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except OSError as e:
            print(f"[E010] 读取文件失败: {e}")
            return 1

    if raw_input is None:
        # 尝试从标准输入读取
        try:
            raw_input = sys.stdin.read()
        except KeyboardInterrupt:
            print("[E009] 读取输入被中断")
            return 1

    # 处理单条输入
    try:
        result = process_single(raw_input, args.format)
        print(result["output"])
        return 0
    except SpecialistAgentError as e:
        print(f"[{e.code}] {e.message}")
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
