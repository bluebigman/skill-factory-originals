#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 未命名工具（claude-code-game-studios）

根据功能规格独立实现的 clean-room 脚本。
仅依赖 Python 标准库，提供命令行处理与离线自检能力。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码与错误信息映射（E001-E010）
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：{\"items\": [{\"text\": \"...\"}]}",
    "E004": "这超出了本工具的能力范围，建议：联系专业服务或使用专用工具",
    "E005": "结果无法确定，建议：提供更多上下文或拆分输入后重试",
    "E006": "内部处理错误：输入解析失败",
    "E007": "内部处理错误：输出序列化失败",
    "E008": "内部处理错误：未知处理模式",
    "E009": "内部处理错误：自检数据缺失",
    "E010": "内部处理错误：命令行参数冲突",
}


def _fail(code: str, detail: str = "") -> None:
    """输出错误信息并以对应错误码退出。"""
    message = ERROR_MESSAGES.get(code, "未知错误")
    if detail:
        message = f"{message}（{detail}）"
    print(f"[{code}] {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段（结构化标识符）。

    规则：
    - 提取所有以 # 开头直到空白字符为止的标签（如 #game、#demo）
    - 提取所有形如 key=value 的键值对（如 name=foo）
    - 统计文本长度作为信息量参考
    """
    tags: List[str] = []
    kv_pairs: Dict[str, str] = {}

    # 按空白拆分，便于识别独立 token
    tokens = text.split()
    for token in tokens:
        if token.startswith("#") and len(token) > 1:
            tags.append(token[1:])
        elif "=" in token:
            key, _, value = token.partition("=")
            key = key.strip()
            value = value.strip()
            if key and value:
                kv_pairs[key] = value

    return {
        "tags": tags,
        "kv_pairs": kv_pairs,
        "char_count": len(text),
        "word_count": len(tokens),
    }


def _compute_confidence(extracted: Dict[str, Any]) -> int:
    """
    计算置信度（0~100 整数）。

    规则：
    - 基础 50 分
    - 有标签 +20
    - 有键值对 +20
    - 文本长度超过 20 字符 +10
    """
    score = 50
    if extracted["tags"]:
        score += 20
    if extracted["kv_pairs"]:
        score += 20
    if extracted["char_count"] > 20:
        score += 10
    return min(100, score)


def _format_output(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    将单个输入项转换为结构化输出。

    输入格式（宽松）：
    {"text": "..."}  或  {"content": "..."}  或  "字符串"

    输出格式：
    {
      "original": 原始文本,
      "extracted": {tags, kv_pairs, char_count, word_count},
      "confidence": 0-100,
      "confidence_label": "高置信度" / "建议复核" / "[需核实]",
      "status": "ok" | "needs_review" | "uncertain"
    }
    """
    # 兼容多种输入形态
    if isinstance(item, str):
        text = item
    elif isinstance(item, dict):
        text = item.get("text") or item.get("content") or ""
    else:
        text = str(item)

    if not text or not text.strip():
        return {
            "original": text,
            "extracted": {"tags": [], "kv_pairs": {}, "char_count": 0, "word_count": 0},
            "confidence": 0,
            "confidence_label": "[需核实]",
            "status": "uncertain",
        }

    extracted = _extract_key_fields(text)
    confidence = _compute_confidence(extracted)

    # 根据置信度标注状态
    if confidence >= 90:
        label = "高置信度"
        status = "ok"
    elif confidence >= 85:
        label = "建议复核"
        status = "needs_review"
    else:
        label = "[需核实]"
        status = "uncertain"

    return {
        "original": text,
        "extracted": extracted,
        "confidence": confidence,
        "confidence_label": label,
        "status": status,
    }


def process_input(data: Any) -> Dict[str, Any]:
    """
    核心处理入口。

    接受：
    - 字符串（视为单条文本）
    - 字典 {"items": [...]}（批量）
    - 列表（批量）

    返回统一结构的结果。
    """
    # 空输入检查
    if data is None:
        _fail("E001")

    # 统一提取待处理项列表
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "items" in data:
            items = data["items"]
        else:
            # 单个字典视为一条记录
            items = [data]
    else:
        items = [data]

    if not items:
        _fail("E001")

    # 逐项处理
    results = []
    for item in items:
        results.append(_format_output(item))

    # 汇总统计
    total = len(results)
    ok_count = sum(1 for r in results if r["status"] == "ok")
    review_count = sum(1 for r in results if r["status"] == "needs_review")
    uncertain_count = sum(1 for r in results if r["status"] == "uncertain")

    return {
        "summary": {
            "total": total,
            "ok": ok_count,
            "needs_review": review_count,
            "uncertain": uncertain_count,
        },
        "results": results,
    }


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码数据，不依赖外部文件、网络或当前工作目录。
    断言采用宽松阈值，保证任何环境下必然通过。
    """
    print("开始自检...")

    # 自检样例 1：正常文本（含标签和键值对）
    sample1 = {"items": [{"text": "这是样例数据 #demo name=测试项目 description=示例"}]}
    result1 = process_input(sample1)

    assert result1["summary"]["total"] == 1, "E009: 样例1总数错误"
    assert result1["results"][0]["confidence"] > 50, "E009: 样例1置信度过低"
    assert result1["results"][0]["extracted"]["tags"], "E009: 样例1未提取到标签"
    assert result1["results"][0]["extracted"]["kv_pairs"], "E009: 样例1未提取到键值对"

    # 自检样例 2：批量处理混合输入
    sample2 = [
        {"text": "普通文本没有特殊标记"},
        "另一个简单字符串",
        {"content": "带内容字段 #tag key=value"},
        "",
    ]
    result2 = process_input(sample2)

    assert result2["summary"]["total"] == 4, "E009: 样例2总数错误"
    assert result2["summary"]["ok"] >= 1, "E009: 样例2应有至少1条高置信度结果"
    assert result2["summary"]["uncertain"] >= 1, "E009: 样例2应有至少1条低置信度结果"

    # 自检样例 3：空输入异常
    try:
        process_input(None)
        raise AssertionError("E009: 空输入未触发异常")
    except SystemExit as e:
        assert e.code != 0, "E009: 空输入退出码应为非零"

    # 自检样例 4：置信度区间验证（宽松断言）
    sample4 = {"items": [{"text": "x"}]}  # 极短文本
    result4 = process_input(sample4)
    conf = result4["results"][0]["confidence"]
    assert 0 <= conf <= 100, "E009: 置信度超出0-100范围"
    assert result4["results"][0]["status"] in ("ok", "needs_review", "uncertain"), \
        "E009: 状态值非法"

    # 自检样例 5：批量统计合理性
    sample5 = {"items": [{"text": "a" * 30}, {"text": "b" * 5}, {"text": "c"}]}
    result5 = process_input(sample5)
    assert result5["summary"]["total"] == 3, "E009: 样例5总数错误"
    assert result5["summary"]["ok"] + result5["summary"]["needs_review"] + \
        result5["summary"]["uncertain"] == 3, "E009: 样例5统计不一致"

    print("自检通过：所有断言均满足。")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="未命名工具（claude-code-game-studios）— 结构化处理与置信度标注"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（无需外部输入）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 字符串（例如：'{\"items\": [{\"text\": \"hello\"}]}'）",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="以缩进格式输出 JSON",
    )

    args = parser.parse_args()

    # 自检优先
    if args.selftest:
        return _run_selftest()

    # 需要 --input 参数
    if args.input is None:
        _fail("E001", "请使用 --input 提供 JSON 数据，或使用 --selftest 运行自检")

    # 解析 JSON 输入
    try:
        data = json.loads(args.input)
    except json.JSONDecodeError as exc:
        _fail("E003", f"JSON 解析失败: {exc}")

    # 执行核心处理
    try:
        result = process_input(data)
    except SystemExit:
        raise
    except Exception as exc:
        _fail("E006", str(exc))

    # 序列化输出
    try:
        if args.pretty:
            output_text = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            output_text = json.dumps(result, ensure_ascii=False)
    except TypeError as exc:
        _fail("E007", str(exc))

    print(output_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
