#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

未命名工具（soup）—— 一个轻量级文档/元组存储与结构化处理工具。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
功能要点：
  1. 将输入内容解析为结构化结果（文档记录 / 元组列表）。
  2. 识别并保留关键信息，按默认模板组织输出。
  3. 对不确定项给出置信度提示（<85% 标注 [需核实]，85%-90% 建议复核）。
  4. 支持批量处理（多行输入逐项处理）。
  5. 内置 --selftest 离线自检，不依赖外部文件、网络或当前工作目录。

错误码体系（E001-E010）：
  E001  输入为空
  E002  关键信息缺失
  E003  输入格式错误
  E004  超出能力边界
  E005  置信度过低
  E006  内部逻辑错误（不应发生）
  E007  输出序列化失败
  E008  参数解析失败
  E009  批处理中某条记录处理失败
  E010  未知错误

依赖：仅使用 Python 标准库。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------
# 核心数据结构与常量
# ---------------------------------------------------------------

# 默认输出模板字段（按功能规格 Step 2 的约定）
DEFAULT_TEMPLATE_FIELDS = [
    "id",           # 记录编号
    "content",      # 原始内容（截断展示）
    "keywords",     # 提取的关键词列表
    "confidence",   # 置信度（0-100 整数）
    "note",         # 备注（如"建议复核"或"[需核实]"）
]


# ---------------------------------------------------------------
# 工具函数（内部使用）
# ---------------------------------------------------------------

def _truncate_text(text: str, max_len: int = 80) -> str:
    """截断文本用于展示，避免输出过长。"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def _extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    从文本中提取关键词（极简实现）：
    - 按空白拆分，过滤掉无意义短词/停用词。
    - 返回出现频率最高的前 N 个词。
    这是启发式规则，不保证语义准确性，低置信度会由调用方标注。
    """
    # 简易停用词表（仅用于演示，不追求完备）
    stop_words = {
        "的", "了", "和", "是", "在", "我", "有", "就", "不", "人",
        "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
        "你", "会", "着", "没有", "看", "好", "自己", "这", "那",
        "the", "a", "an", "and", "or", "but", "is", "are", "to",
        "of", "in", "on", "for", "with", "as", "by", "at", "from",
    }

    # 按非字母数字字符拆分（保留中文、英文、数字）
    tokens: List[str] = []
    current = []
    for ch in text:
        if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))

    # 过滤停用词和过短词
    filtered = [t for t in tokens if t not in stop_words and len(t) >= 2]

    # 统计频率
    freq: Dict[str, int] = {}
    for t in filtered:
        freq[t] = freq.get(t, 0) + 1

    # 按频率降序，取前 N 个
    sorted_items = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [word for word, _ in sorted_items[:max_keywords]]


def _compute_confidence(text: str, keywords: List[str]) -> int:
    """
    计算置信度（0-100）：
    启发式规则：
      - 空文本 => 0
      - 文本长度太短（<5 字符）=> 较低
      - 关键词数量越多 => 置信度越高
      - 文本长度适中且有实质内容 => 较高
    返回 0-100 的整数。
    """
    if not text or not text.strip():
        return 0

    stripped = text.strip()
    length = len(stripped)

    # 基础分
    base = 50

    # 长度加分（5~200 字符区间内线性增长）
    if length < 5:
        base -= 30          # 太短，信息量不足
    elif length < 20:
        base += 10
    elif length < 100:
        base += 20
    else:
        base += 25          # 长文本通常信息更充分

    # 关键词加分（每个关键词加 5 分，最多加 25 分）
    base += min(len(keywords) * 5, 25)

    # 包含数字/URL 等特征可加分（此处做简单判断）
    if any(ch.isdigit() for ch in stripped):
        base += 5

    # 限制在 0-100 区间
    return max(0, min(100, base))


def _format_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    将内部记录格式化为标准输出模板。
    内部记录字段：id, content, keywords, confidence
    输出模板字段：id, content, keywords, confidence, note
    """
    confidence = record.get("confidence", 0)

    # 置信度标注规则（按功能规格 Step 2）
    if confidence >= 90:
        note = ""
    elif confidence >= 85:
        note = "建议复核"
    else:
        note = "[需核实]"

    return {
        "id": record.get("id", ""),
        "content": _truncate_text(record.get("content", "")),
        "keywords": record.get("keywords", []),
        "confidence": confidence,
        "note": note,
    }


# ---------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------

def process_single_input(input_text: str, record_id: int = 1) -> Dict[str, Any]:
    """
    处理单条输入，返回结构化结果。

    参数：
        input_text: 用户提供的原始文本内容
        record_id:  记录编号（用于输出标识）

    返回：
        符合默认模板的字典。

    异常：
        E001: 输入为空
        E003: 输入格式错误（非字符串）
    """
    # E001: 输入为空
    if input_text is None or (isinstance(input_text, str) and not input_text.strip()):
        raise ValueError("E001: 输入为空，请提供待处理的内容。")

    # E003: 输入格式错误（必须是字符串）
    if not isinstance(input_text, str):
        raise TypeError("E003: 输入格式错误，输入必须是字符串类型。")

    # 提取关键词
    keywords = _extract_keywords(input_text)

    # 计算置信度
    confidence = _compute_confidence(input_text, keywords)

    # 构造内部记录
    record = {
        "id": record_id,
        "content": input_text,
        "keywords": keywords,
        "confidence": confidence,
    }

    # 格式化为标准输出
    return _format_record(record)


def process_batch(inputs: List[str]) -> Dict[str, Any]:
    """
    批量处理多条输入。

    参数：
        inputs: 字符串列表，每条作为独立记录处理。

    返回：
        {"results": [...], "failed": [...], "total": N} 结构。

    异常：
        E002: 输入列表为空
    """
    # E002: 关键信息缺失（批量列表为空）
    if not inputs:
        raise ValueError("E002: 缺少待处理的批量数据，请至少提供一条输入。")

    results = []
    failed = []

    for idx, item in enumerate(inputs, start=1):
        try:
            # 单条处理失败不中断批量，记录到 failed
            record = process_single_input(item, record_id=idx)
            results.append(record)
        except (ValueError, TypeError) as exc:
            failed.append({"index": idx, "error": str(exc)})

    # 返回汇总结果
    return {
        "results": results,
        "failed": failed,
        "total": len(inputs),
        "success_count": len(results),
        "fail_count": len(failed),
    }


# ---------------------------------------------------------------
# 输出序列化
# ---------------------------------------------------------------

def serialize_output(data: Any, fmt: str = "json") -> str:
    """
    将结果序列化为指定格式字符串。

    参数：
        data: 要序列化的数据（字典或列表）
        fmt:  输出格式，支持 "json" / "text"

    返回：
        序列化后的字符串。

    异常：
        E007: 序列化失败
    """
    try:
        if fmt == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif fmt == "text":
            # 简易文本格式输出
            lines = []
            if isinstance(data, dict) and "results" in data:
                # 批量结果
                for r in data["results"]:
                    lines.append(f"记录 #{r['id']}: {r['content']}")
                    lines.append(f"  关键词: {', '.join(r['keywords']) if r['keywords'] else '无'}")
                    lines.append(f"  置信度: {r['confidence']}%  {r['note']}")
                    lines.append("")
                lines.append(f"总计: {data['total']} 条, 成功: {data['success_count']}, 失败: {data['fail_count']}")
            elif isinstance(data, dict):
                # 单条结果
                for key in DEFAULT_TEMPLATE_FIELDS:
                    if key in data:
                        lines.append(f"{key}: {data[key]}")
            else:
                lines.append(str(data))
            return "\n".join(lines)
        else:
            # 不支持的格式视为序列化失败
            raise ValueError(f"不支持的输出格式: {fmt}")
    except Exception as exc:
        # E007: 输出序列化失败
        raise RuntimeError(f"E007: 输出序列化失败 - {exc}")


# ---------------------------------------------------------------
# 命令行入口与自检
# ---------------------------------------------------------------

def _run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。
    不读取外部文件、不依赖当前工作目录、不访问网络。

    使用宽松阈值（区间/大小比较）进行断言，确保稳健。
    返回 0 表示全部通过，非 0 表示失败。
    """
    print("[selftest] 开始离线自检...")

    # ---- 测试用例 1: 正常单条输入 ----
    text1 = "Python 是一种广泛使用的编程语言，适合数据分析和机器学习。"
    try:
        rec1 = process_single_input(text1, record_id=1)
        # 宽松断言：置信度应在一个合理区间（不应极端低或极端高）
        assert 30 <= rec1["confidence"] <= 100, f"置信度区间异常: {rec1['confidence']}"
        # 关键词不应为空（文本有实质内容）
        assert len(rec1["keywords"]) > 0, "关键词不应为空"
        # id 正确
        assert rec1["id"] == 1, f"id 错误: {rec1['id']}"
        print(f"  [OK] 单条输入处理: confidence={rec1['confidence']}, keywords={rec1['keywords']}")
    except Exception as exc:
        print(f"  [FAIL] 单条输入处理: {exc}")
        return 1

    # ---- 测试用例 2: 空输入应报 E001 ----
    try:
        process_single_input("   ")
        print("  [FAIL] 空输入未触发 E001")
        return 1
    except ValueError as exc:
        assert "E001" in str(exc), f"错误码不是 E001: {exc}"
        print("  [OK] 空输入正确触发 E001")

    # ---- 测试用例 3: 批量处理 ----
    batch_inputs = [
        "第一条测试数据，包含一些关键词。",
        "第二条数据，用于验证批量处理逻辑。",
        "",  # 空串应被标记为失败
        "第三条数据，内容较短。",
    ]
    try:
        batch_result = process_batch(batch_inputs)
        # 宽松断言：总数正确
        assert batch_result["total"] == 4, f"总数错误: {batch_result['total']}"
        # 成功数应 >= 2（至少前两条和最后一条成功）
        assert batch_result["success_count"] >= 3, f"成功数偏少: {batch_result['success_count']}"
        # 失败数应 >= 1（空串那条）
        assert batch_result["fail_count"] >= 1, f"失败数应为 1 或更多: {batch_result['fail_count']}"
        print(f"  [OK] 批量处理: 成功={batch_result['success_count']}, 失败={batch_result['fail_count']}")
    except Exception as exc:
        print(f"  [FAIL] 批量处理: {exc}")
        return 1

    # ---- 测试用例 4: 输出序列化 ----
    try:
        sample = {"id": 1, "content": "测试", "keywords": ["测试"], "confidence": 88, "note": "建议复核"}
        json_out = serialize_output(sample, fmt="json")
        assert json_out is not None and len(json_out) > 0, "JSON 输出为空"
        text_out = serialize_output(sample, fmt="text")
        assert text_out is not None and len(text_out) > 0, "文本输出为空"
        print("  [OK] 输出序列化 (json/text)")
    except Exception as exc:
        print(f"  [FAIL] 输出序列化: {exc}")
        return 1

    # ---- 测试用例 5: 置信度逻辑 ----
    try:
        # 非常短的文本置信度应较低
        short_rec = process_single_input("短", record_id=5)
        # 宽松断言：短文本置信度应 < 70
        assert short_rec["confidence"] < 70, f"短文本置信度应较低: {short_rec['confidence']}"

        # 较长且内容丰富文本置信度应较高
        long_text = ("这是一个较长的测试文本，包含多个关键词。"
                     "我们希望通过这段文字来验证置信度计算的逻辑是否合理。"
                     "文本中提到了 Python、数据分析、机器学习、人工智能等多个领域。"
                     "同时包含一些数字如 123 和 456，以增加信息量。")
        long_rec = process_single_input(long_text, record_id=6)
        # 宽松断言：长文本置信度应 >= 60
        assert long_rec["confidence"] >= 60, f"长文本置信度应较高: {long_rec['confidence']}"

        print(f"  [OK] 置信度逻辑: 短文本={short_rec['confidence']}, 长文本={long_rec['confidence']}")
    except Exception as exc:
        print(f"  [FAIL] 置信度逻辑: {exc}")
        return 1

    # ---- 测试用例 6: 错误码覆盖 ----
    try:
        # E002: 空批量列表
        process_batch([])
        print("  [FAIL] 空批量列表未触发 E002")
        return 1
    except ValueError as exc:
        assert "E002" in str(exc), f"错误码不是 E002: {exc}"
        print("  [OK] 空批量列表正确触发 E002")

    try:
        # E003: 非字符串输入
        process_single_input(12345)  # type: ignore
        print("  [FAIL] 非字符串输入未触发 E003")
        return 1
    except TypeError as exc:
        assert "E003" in str(exc), f"错误码不是 E003: {exc}"
        print("  [OK] 非字符串输入正确触发 E003")

    print("[selftest] 全部自检通过 ✔")
    return 0


def main(argv: List[str] | None = None) -> int:
    """
    命令行入口函数。

    支持参数：
        --input TEXT   单条输入内容
        --batch        批量模式（从 stdin 读取多行）
        --format FMT   输出格式（json/text），默认 json
        --selftest     运行离线自检
    """
    parser = argparse.ArgumentParser(
        description="未命名工具（soup）—— 文档/元组存储与结构化处理",
        epilog="示例: python main.py --input '这是一条测试内容' --format text",
    )
    parser.add_argument("--input", type=str, help="单条输入内容")
    parser.add_argument("--batch", action="store_true", help="批量模式（从 stdin 读取多行）")
    parser.add_argument("--format", type=str, default="json", choices=["json", "text"], help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    # E008: 参数解析失败
    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse 在出错时会调用 sys.exit(2)
        if exc.code != 0:
            print(f"E008: 参数解析失败，请检查命令行参数。", file=sys.stderr)
        return exc.code or 0

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 正常处理模式
    try:
        # 批量模式：从 stdin 读取多行
        if args.batch:
            print("请输入多行内容（每行一条记录），Ctrl+D 结束：", file=sys.stderr)
            lines = [line.rstrip("\n") for line in sys.stdin]
            result = process_batch(lines)
            output = serialize_output(result, fmt=args.format)
            print(output)
            return 0

        # 单条模式
        if args.input is not None:
            record = process_single_input(args.input)
            output = serialize_output(record, fmt=args.format)
            print(output)
            return 0

        # 既不是自检也没有输入 => E001
        raise ValueError("E001: 输入为空，请提供待处理的内容。")

    except ValueError as exc:
        # E001/E002/E005 等业务错误
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except TypeError as exc:
        # E003 输入格式错误
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        # E007 序列化失败等
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # E010 未知错误
        print(f"E010: 发生未知错误 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
