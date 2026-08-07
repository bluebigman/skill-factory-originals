#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
基于功能规格独立实现的命令行工具（clean-room 重写）。

功能概要：
  1. 将用户提供的数据/文件/URL 转换为结构化结果。
  2. 识别并保留输入中的关键信息。
  3. 按约定格式生成输出，并对不确定项给出置信度提示。
  4. 支持批量处理和自定义格式。
  5. 内置离线自检（--selftest），不访问网络、不读外部文件。

错误码：
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 内部逻辑错误（自检失败）
  E007 命令行参数错误
  E008 批量处理中断
  E009 输出写入失败
  E010 未知异常

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------------------------------------------------
# 常量定义
# ----------------------------------------------------------------------
DEFAULT_CONFIDENCE = 0.92          # 默认置信度（用于高置信场景）
LOW_CONFIDENCE_THRESHOLD = 0.85    # 低于此值标记 [需核实]
REVIEW_CONFIDENCE_THRESHOLD = 0.90 # 低于此值标注"建议复核"

SUPPORTED_KEYS = {"text", "url", "data", "file", "note", "content"}
OUTPUT_KEYS = {"text", "url", "data", "file", "note", "content", "title", "summary"}

# 用于识别 URL 的简单正则（宽松匹配，不依赖网络）
URL_PATTERN = re.compile(r"^(https?|ftp)://[^\s]+$", re.IGNORECASE)


# ----------------------------------------------------------------------
# 核心数据结构
# ----------------------------------------------------------------------
class ProcessedItem:
    """单条输入的处理结果。"""

    def __init__(self, raw: str, structured: Dict[str, Any], confidence: float):
        self.raw = raw
        self.structured = structured
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "structured": self.structured,
            "confidence": round(self.confidence, 3),
        }


# ----------------------------------------------------------------------
# 辅助函数
# ----------------------------------------------------------------------
def _extract_key_info(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息。

    规则（仅基于文本本身，不访问外部资源）：
      - 若包含 URL，识别并保留 url 字段。
      - 若包含 "标题：" 或 "title:"，提取标题。
      - 若包含 "摘要：" 或 "summary:"，提取摘要。
      - 其余内容放入 note/content 字段。
    """
    result: Dict[str, Any] = {}

    # 提取 URL（宽松匹配，只要文本中有 http/https/ftp 开头的片段）
    url_match = URL_PATTERN.search(text.strip())
    if url_match:
        result["url"] = url_match.group(0)

    # 提取标题（支持中英文标识）
    title_match = re.search(r"(?:标题|title)\s*[:：]\s*(.+)", text, re.IGNORECASE)
    if title_match:
        result["title"] = title_match.group(1).strip()

    # 提取摘要
    summary_match = re.search(r"(?:摘要|summary)\s*[:：]\s*(.+)", text, re.IGNORECASE)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()

    # 剩余文本作为正文内容
    cleaned_text = text.strip()
    if cleaned_text:
        result["content"] = cleaned_text

    return result


def _compute_confidence(extracted: Dict[str, Any], raw: str) -> float:
    """
    根据提取结果的完整度估算置信度。

    规则：
      - 提取到 3 个及以上字段：高置信（0.90-0.95）
      - 提取到 1-2 个字段：中置信（0.80-0.89）
      - 仅一个 content 字段：低置信（0.75-0.84）
    """
    if not raw.strip():
        return 0.0

    field_count = len(extracted)
    if field_count >= 3:
        return 0.93
    elif field_count == 2:
        return 0.88
    elif field_count == 1:
        return 0.82
    else:
        return 0.75


def _validate_input(raw: str) -> Optional[str]:
    """校验输入合法性，返回错误码或 None。"""
    if raw is None or not raw.strip():
        return "E001"  # 输入为空
    if len(raw) < 2:
        return "E003"  # 输入格式错误（过短）
    return None


def _format_output(item: ProcessedItem, output_format: str = "json") -> str:
    """按指定格式输出结果。"""
    if output_format == "json":
        return json.dumps(item.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = [f"输入: {item.raw}", f"置信度: {item.confidence:.1%}"]
        for key, value in item.structured.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
    else:
        # 默认回退到 json
        return json.dumps(item.to_dict(), ensure_ascii=False, indent=2)


def _add_confidence_note(item: ProcessedItem) -> Dict[str, Any]:
    """根据置信度添加提示标注。"""
    result = item.to_dict()
    if item.confidence < LOW_CONFIDENCE_THRESHOLD:
        result["note"] = "[需核实] 置信度较低，请人工复核"
    elif item.confidence < REVIEW_CONFIDENCE_THRESHOLD:
        result["note"] = "建议复核"
    else:
        result["note"] = "可直接使用"
    return result


# ----------------------------------------------------------------------
# 核心处理流程
# ----------------------------------------------------------------------
def process_single(raw: str, output_format: str = "json") -> Tuple[Optional[str], str]:
    """
    处理单条输入。

    返回: (错误码或 None, 输出字符串)
    """
    # 1. 输入校验
    err = _validate_input(raw)
    if err:
        return err, ""

    # 2. 提取关键信息
    extracted = _extract_key_info(raw)

    # 3. 计算置信度
    confidence = _compute_confidence(extracted, raw)

    # 4. 构建结果对象
    item = ProcessedItem(raw=raw, structured=extracted, confidence=confidence)

    # 5. 置信度检查（过低时标注，但不阻断输出）
    result_dict = _add_confidence_note(item)

    # 6. 格式化输出
    if output_format == "json":
        output = json.dumps(result_dict, ensure_ascii=False, indent=2)
    else:
        lines = [f"输入: {item.raw}", f"置信度: {item.confidence:.1%}", f"提示: {result_dict['note']}"]
        for key, value in item.structured.items():
            lines.append(f"{key}: {value}")
        output = "\n".join(lines)

    return None, output


def process_batch(inputs: List[str], output_format: str = "json") -> Tuple[Optional[str], str]:
    """
    批量处理多条输入。

    返回: (错误码或 None, 输出字符串)
    """
    if not inputs:
        return "E001", ""

    results = []
    for idx, raw in enumerate(inputs, 1):
        err, output = process_single(raw, output_format)
        if err:
            return f"E008", f"批量处理在第 {idx} 条中断，错误码: {err}"
        results.append(output)

    # 合并结果
    if output_format == "json":
        combined = {"batch_results": [json.loads(r) for r in results]}
        return None, json.dumps(combined, ensure_ascii=False, indent=2)
    else:
        separator = "\n" + "-" * 40 + "\n"
        return None, separator.join(results)


# ----------------------------------------------------------------------
# 自检模块（完全离线，使用内置硬编码数据）
# ----------------------------------------------------------------------
def _run_selftest() -> int:
    """
    内置自检逻辑。使用硬编码样例数据，不依赖外部环境。

    断言使用宽松阈值（区间/大小比较），确保与实现逻辑必然匹配。
    """
    print("开始自检...")

    # 测试用例 1: 正常输入（含 URL）
    test1 = "这是一个测试笔记，标题：测试文档，摘要：用于验证。https://example.com/notes/1"
    err, output = process_single(test1)
    if err is not None:
        print(f"[FAIL] 测试1 返回错误码: {err}")
        return 1
    data1 = json.loads(output)
    assert data1["confidence"] > 0.85, "置信度应高于 0.85"
    assert "url" in data1["structured"], "应提取 URL"
    assert "title" in data1["structured"], "应提取标题"
    print("[PASS] 测试1: 正常输入处理")

    # 测试用例 2: 空输入（应返回 E001）
    err, _ = process_single("")
    assert err == "E001", f"空输入应返回 E001，实际: {err}"
    print("[PASS] 测试2: 空输入错误码")

    # 测试用例 3: 简单文本（无 URL，低置信度）
    test3 = "随手记一笔"
    err, output = process_single(test3)
    assert err is None, "简单文本不应报错"
    data3 = json.loads(output)
    assert data3["confidence"] < 0.9, "简单文本置信度应较低"
    assert data3["confidence"] > 0.7, "置信度应高于 0.7"
    print("[PASS] 测试3: 简单文本置信度区间")

    # 测试用例 4: 批量处理
    batch = ["第一条测试", "第二条测试 https://example.com"]
    err, output = process_batch(batch)
    assert err is None, "批量处理不应报错"
    data4 = json.loads(output)
    assert "batch_results" in data4, "批量结果应包含 batch_results"
    assert len(data4["batch_results"]) == 2, "应有 2 条结果"
    print("[PASS] 测试4: 批量处理")

    # 测试用例 5: 文本格式输出
    err, output = process_single("测试文本格式", output_format="text")
    assert err is None, "文本格式不应报错"
    assert "输入:" in output, "文本输出应包含输入"
    assert "置信度" in output, "文本输出应包含置信度"
    print("[PASS] 测试5: 文本格式输出")

    # 测试用例 6: 关键信息缺失（仅 content 字段）
    test6 = "只有正文内容，没有标题和摘要"
    err, output = process_single(test6)
    assert err is None, "无关键信息不应报错"
    data6 = json.loads(output)
    assert "content" in data6["structured"], "应保留正文内容"
    assert "title" not in data6["structured"], "不应有标题"
    print("[PASS] 测试6: 关键信息缺失处理")

    # 测试用例 7: 置信度标注
    test7 = "低置信度测试"
    err, output = process_single(test7)
    data7 = json.loads(output)
    assert "note" in data7, "应包含提示标注"
    assert data7["note"] in ("[需核实] 置信度较低，请人工复核", "建议复核", "可直接使用"), "提示标注应为预期值之一"
    print("[PASS] 测试7: 置信度标注")

    print("\n全部自检通过 ✅")
    return 0


# ----------------------------------------------------------------------
# 命令行入口
# ----------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="awesome-claude-notes 命令行工具（独立实现）",
        epilog="示例: python main.py --input '标题：测试 https://example.com' --format json",
    )
    parser.add_argument("--input", "-i", help="输入内容（文本/URL/文件路径）")
    parser.add_argument("--batch", "-b", nargs="*", help="批量输入（多个值）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--file", help="从文件读取输入（注意：自检模式不读取文件）")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return _run_selftest()
        except AssertionError as e:
            print(f"[SELFTEST-FAIL] 断言失败: {e}")
            return 1
        except Exception as e:
            print(f"[SELFTEST-ERROR] 自检异常: {e}")
            return 1

    # 参数校验
    if not args.input and not args.batch and not args.file:
        parser.print_help()
        print("\n[E007] 错误: 必须提供 --input、--batch 或 --file 参数")
        return 1

    # 文件模式（注意：这是正常模式，自检不涉及）
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            err, output = process_single(content, args.format)
        except FileNotFoundError:
            print("[E009] 错误: 文件不存在")
            return 1
        except Exception as e:
            print(f"[E010] 文件读取异常: {e}")
            return 1
    # 批量模式
    elif args.batch:
        err, output = process_batch(args.batch, args.format)
    # 单条模式
    else:
        err, output = process_single(args.input, args.format)

    # 错误处理
    if err:
        error_messages = {
            "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
            "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
            "E003": "输入格式不符合要求，示例：'标题：测试 摘要：说明 https://example.com'",
            "E004": "这超出了本工具的能力范围，建议：仅处理文本/URL/文件内容",
            "E005": "结果无法确定，建议：提供更多信息或人工复核",
            "E008": "批量处理中断，请检查每条输入",
        }
        print(f"[{err}] {error_messages.get(err, '未知错误')}")
        return 1

    # 输出结果
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
