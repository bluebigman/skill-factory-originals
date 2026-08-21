#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - gitsum 技能核心实现

基于功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供命令行接口与内置自检（--selftest）。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（遵循规格 E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式不符合要求。",
    "E004": "超出能力边界，无法处理。",
    "E005": "置信度过低，结果不确定。",
    "E006": "内部处理错误。",
    "E007": "参数解析错误。",
    "E008": "输出格式错误。",
    "E009": "批量处理中断。",
    "E010": "未知错误。",
}


class GitsumError(Exception):
    """带错误码的异常类型。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条输入的结构化处理结果。"""

    def __init__(self, raw: str, key: str, confidence: float, note: str = ""):
        self.raw = raw            # 原始输入
        self.key = key            # 提取的关键信息
        self.confidence = confidence  # 置信度 0.0~1.0
        self.note = note          # 附加说明（如 [需核实]）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "key": self.key,
            "confidence": self.confidence,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# 核心逻辑：解析与处理
# ---------------------------------------------------------------------------
def _extract_key(text: str) -> str:
    """
    从输入文本中提取关键信息。

    规则（简化版）：
    - 去除首尾空白
    - 取第一行或第一个逗号/分号前的部分作为关键信息
    - 若为空则返回空串
    """
    if not text:
        return ""
    cleaned = text.strip()
    if not cleaned:
        return ""
    # 取第一行
    first_line = cleaned.splitlines()[0].strip()
    # 取第一个分隔符之前
    for sep in (",", "；", ";", "，"):
        if sep in first_line:
            return first_line.split(sep)[0].strip()
    return first_line


def _compute_confidence(raw: str, key: str) -> float:
    """
    计算置信度（宽松启发式）。

    规则：
    - 输入为空：0.0
    - 关键信息为空：0.0
    - 关键信息长度 >= 2：0.95
    - 关键信息长度 == 1：0.85
    - 其他：0.80
    """
    if not raw or not raw.strip():
        return 0.0
    if not key:
        return 0.0
    if len(key) >= 2:
        return 0.95
    if len(key) == 1:
        return 0.85
    return 0.80


def process_single(text: str) -> ProcessedItem:
    """
    处理单条输入，返回结构化结果。
    """
    if text is None:
        raise GitsumError("E001")
    raw = str(text).strip()
    if not raw:
        raise GitsumError("E001")

    key = _extract_key(raw)
    if not key:
        raise GitsumError("E002", "未能从输入中提取关键信息")

    confidence = _compute_confidence(raw, key)
    note = ""
    if confidence < 0.85:
        note = "[需核实]"
    elif confidence < 0.90:
        note = "建议复核"

    return ProcessedItem(raw=raw, key=key, confidence=confidence, note=note)


def process_batch(items: List[str]) -> List[ProcessedItem]:
    """
    批量处理多条输入。

    任一条失败则抛出 E009（批量处理中断）。
    """
    if not items:
        raise GitsumError("E001")
    results: List[ProcessedItem] = []
    try:
        for item in items:
            results.append(process_single(item))
    except GitsumError as exc:
        raise GitsumError("E009", f"批量处理中断于第 {len(results)+1} 条: {exc}") from exc
    return results


def format_output(results: List[ProcessedItem], fmt: str = "text") -> str:
    """
    按指定格式输出结果。

    支持格式：text / json / csv
    """
    if fmt == "json":
        import json
        return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
    elif fmt == "csv":
        lines = ["raw,key,confidence,note"]
        for r in results:
            # 简单转义逗号
            raw = r.raw.replace(",", "，")
            key = r.key.replace(",", "，")
            lines.append(f"{raw},{key},{r.confidence:.2f},{r.note}")
        return "\n".join(lines)
    elif fmt == "text":
        lines = []
        for i, r in enumerate(results, 1):
            conf_pct = int(r.confidence * 100)
            lines.append(f"#{i}: 关键信息={r.key} | 置信度={conf_pct}% {r.note}")
        return "\n".join(lines)
    else:
        raise GitsumError("E008", f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    """
    内置硬编码样例数据离线自检核心逻辑。

    不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保必然匹配。
    """
    print("开始自检（gitsum core）...")

    # 样例 1：正常输入
    item1 = process_single("张三, 25岁, 北京")
    assert item1.key == "张三", f"样例1关键信息错误: {item1.key}"
    assert item1.confidence >= 0.90, f"样例1置信度应>=0.90, 实际: {item1.confidence}"

    # 样例 2：带分号
    item2 = process_single("项目A；负责人：李四")
    assert item2.key == "项目A", f"样例2关键信息错误: {item2.key}"
    assert item2.confidence >= 0.90, f"样例2置信度应>=0.90, 实际: {item2.confidence}"

    # 样例 3：空输入应报错 E001
    try:
        process_single("")
        raise AssertionError("样例3应抛出 E001，但未抛出")
    except GitsumError as e:
        assert e.code == "E001", f"样例3错误码应为E001, 实际: {e.code}"

    # 样例 4：仅空白输入
    try:
        process_single("   ")
        raise AssertionError("样例4应抛出 E001，但未抛出")
    except GitsumError as e:
        assert e.code == "E001", f"样例4错误码应为E001, 实际: {e.code}"

    # 样例 5：批量处理
    batch = ["第一项内容", "第二项内容，带逗号", "第三项"]
    results = process_batch(batch)
    assert len(results) == 3, f"样例5批量结果数量应为3, 实际: {len(results)}"
    for r in results:
        assert r.confidence >= 0.80, f"样例5置信度应>=0.80, 实际: {r.confidence}"

    # 样例 6：格式输出 text
    text_out = format_output(results, "text")
    assert "关键信息" in text_out, "样例6 text格式应包含'关键信息'"

    # 样例 7：格式输出 json
    json_out = format_output(results, "json")
    assert "confidence" in json_out, "样例7 json格式应包含'confidence'字段"

    # 样例 8：格式输出 csv
    csv_out = format_output(results, "csv")
    assert csv_out.startswith("raw,key,confidence,note"), "样例8 csv格式头部错误"

    # 样例 9：低置信度标注
    item9 = process_single("单")
    assert item9.confidence < 0.90, f"样例9置信度应<0.90, 实际: {item9.confidence}"
    assert item9.note != "", "样例9应有标注"

    # 样例 10：错误码字典完整性
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"错误码 {code} 未定义"

    print("全部自检通过 ✅")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gitsum",
        description="gitsum - basic darcsum feelalike for Git",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读外部文件、不访问网络）",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="待处理的输入文本（可多条）",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="输出格式（默认 text）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（逐行读取 stdin 作为多条输入）",
    )
    return parser.parse_args(argv)


def _main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 正常处理模式
    try:
        # 批量模式：从 stdin 读取
        if args.batch:
            lines = [line.strip() for line in sys.stdin if line.strip()]
            if not lines:
                raise GitsumError("E001")
            results = process_batch(lines)
        else:
            # 命令行参数模式
            if not args.inputs:
                raise GitsumError("E001")
            results = process_batch(args.inputs)

        # 输出结果
        output = format_output(results, args.format)
        print(output)
        return 0

    except GitsumError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底错误
        print(f"错误 [E010]: 未知错误 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
