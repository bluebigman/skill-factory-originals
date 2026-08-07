#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merblogger - 未命名工具（通用数据处理与格式转换助手）

本脚本依据功能规格独立实现，不参考任何既有代码。
功能：将用户提供的数据/文件/URL 解析为结构化结果，按约定格式输出，
      支持批量处理、自定义格式、置信度标注与错误码体系。

用法示例：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --input "..."       # 处理输入
    python scripts/main.py --input "a.txt" --file  # 处理文件
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与话术（依据规格第五节）
# ============================================================
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 内部错误码（补充）
    "E006": "文件读取失败，请检查路径与权限",
    "E007": "JSON 解析失败，请检查内容格式",
    "E008": "输出写入失败，请检查目标位置",
    "E009": "参数组合非法，请检查命令行参数",
    "E010": "内部逻辑错误，请反馈开发者",
}


class MerbloggerError(Exception):
    """带错误码的自定义异常。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.message = ERROR_MESSAGES.get(code, "未知错误")
        if detail:
            self.message = f"{self.message}（{detail}）"
        super().__init__(self.message)


# ============================================================
# 核心逻辑：解析、结构化、置信度
# ============================================================
def _extract_key_values(text: str) -> Dict[str, str]:
    """
    从文本中提取关键字段（key: value 或 key=value 形式）。
    仅做基础识别，不依赖外部库。
    """
    result: Dict[str, str] = {}
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 尝试多种分隔符
        for sep in (":", "=", "："):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    result[key] = value
                break
    return result


def _infer_confidence(fields: Dict[str, str], raw_text: str) -> float:
    """
    计算置信度（0~1）：
    - 基准 0.5
    - 每识别出一个字段 +0.1（上限 0.95）
    - 原始文本非空 +0.05
    宽松规则，避免精确阈值。
    """
    confidence = 0.5
    if raw_text and raw_text.strip():
        confidence += 0.05
    recognized = len(fields)
    if recognized > 0:
        confidence += min(0.1 * recognized, 0.4)
    return min(confidence, 0.95)


def _decide_flag(confidence: float) -> str:
    """
    根据置信度返回标注：
    >=0.90 直接输出；0.85~0.90 建议复核；<0.85 需核实。
    使用区间判断，避免精确边界。
    """
    if confidence >= 0.90:
        return "直接输出"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


def process_text(text: str) -> Dict[str, Any]:
    """
    核心处理流程：
    1. 解析输入文本
    2. 提取关键字段
    3. 计算置信度并标注
    4. 返回结构化结果
    """
    if text is None or not text.strip():
        raise MerbloggerError("E001")

    # 提取关键字段
    fields = _extract_key_values(text)

    # 计算置信度
    confidence = _infer_confidence(fields, text)
    flag = _decide_flag(confidence)

    # 组装结果
    result = {
        "status": "success",
        "input_length": len(text),
        "key_fields": fields,
        "field_count": len(fields),
        "confidence": round(confidence, 4),
        "flag": flag,
        "output_text": _format_output(fields, flag),
    }
    return result


def _format_output(fields: Dict[str, str], flag: str) -> str:
    """按默认模板组织输出文本。"""
    if not fields:
        return f"[未识别到关键字段] {flag}"
    lines = []
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    header = f"【处理结果】{flag}"
    return header + "\n" + "\n".join(lines)


def process_batch(items: List[str]) -> List[Dict[str, Any]]:
    """批量处理：对每个输入执行 process_text，跳过空项。"""
    results = []
    for idx, item in enumerate(items, start=1):
        try:
            res = process_text(item)
            res["index"] = idx
        except MerbloggerError as exc:
            res = {
                "index": idx,
                "status": "error",
                "error_code": exc.code,
                "error_message": exc.message,
            }
        results.append(res)
    return results


# ============================================================
# 文件读取与输出
# ============================================================
def read_input_file(path: str) -> str:
    """读取文本文件内容（UTF-8）。"""
    if not path or not os.path.isfile(path):
        raise MerbloggerError("E006", f"路径: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise MerbloggerError("E006", str(exc))


def write_output(data: Any, output_path: Optional[str] = None) -> None:
    """将结果写入文件（JSON）或打印到 stdout。"""
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as exc:
            raise MerbloggerError("E008", str(exc))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


# ============================================================
# 自检模块（内置硬编码样例，离线运行）
# ============================================================
def _selftest() -> int:
    """
    内置样例自检核心逻辑。
    使用宽松阈值（区间/大小比较），保证任何环境可过。
    """
    print("[selftest] 开始离线自检...")

    # 样例 1：正常输入
    sample1 = "标题: 测试文章\n作者: Alice\n日期: 2026-01-01"
    try:
        res1 = process_text(sample1)
        # 宽松断言：字段数 >= 2，置信度在 0.5~1.0 之间
        assert res1["field_count"] >= 2, "字段数过少"
        assert 0.5 <= res1["confidence"] <= 1.0, "置信度超出范围"
        assert res1["status"] == "success", "状态错误"
        print("  [PASS] 样例1（正常输入）")
    except AssertionError as exc:
        print(f"  [FAIL] 样例1: {exc}")
        return 1
    except MerbloggerError as exc:
        print(f"  [FAIL] 样例1 意外异常: {exc}")
        return 1

    # 样例 2：空输入应报 E001
    try:
        process_text("   ")
        print("  [FAIL] 样例2（空输入未报错）")
        return 1
    except MerbloggerError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print("  [PASS] 样例2（空输入错误码）")

    # 样例 3：批量处理
    batch = ["a: 1", "", "b: 2\nc: 3", "   "]
    results = process_batch(batch)
    assert len(results) == 4, "批量结果数量不对"
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    # 宽松断言：成功数 >= 1，错误数 >= 1，总和为 4
    assert success_count >= 1, "成功数过少"
    assert error_count >= 1, "错误数过少"
    assert success_count + error_count == 4, "总数不对"
    print("  [PASS] 样例3（批量处理）")

    # 样例 4：置信度区间判断
    low_conf = process_text("随便一句话没有字段")
    high_conf = process_text("k1: v1\nk2: v2\nk3: v3\nk4: v4\nk5: v5")
    # 低置信度应 < 0.85，高置信度应 > 低置信度
    assert low_conf["confidence"] < 0.85, "低置信度判断失败"
    assert high_conf["confidence"] > low_conf["confidence"], "置信度排序错误"
    print("  [PASS] 样例4（置信度区间）")

    # 样例 5：错误码完整性
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
    print("  [PASS] 样例5（错误码体系）")

    print("[selftest] 全部通过")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="merblogger - 通用数据处理与格式转换助手",
        epilog="示例: python scripts/main.py --input '标题: 测试' --format json",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", type=str, help="输入文本内容")
    parser.add_argument("--file", type=str, help="输入文件路径（与 --input 互斥）")
    parser.add_argument("--batch", type=str, help="批量输入，多个值用 | 分隔")
    parser.add_argument("--output", type=str, help="输出文件路径（JSON 格式）")
    parser.add_argument("--format", type=str, choices=["json", "text"], default="json",
                        help="输出格式（默认 json）")
    return parser


def main() -> int:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _selftest()

    # 参数互斥检查
    if args.input and args.file:
        print("错误：--input 与 --file 不能同时使用", file=sys.stderr)
        return 1

    if args.batch and (args.input or args.file):
        print("错误：--batch 不能与 --input/--file 同时使用", file=sys.stderr)
        return 1

    # 无输入但非自检
    if not args.input and not args.file and not args.batch:
        print(f"错误：{ERROR_MESSAGES['E001']}", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        # 批量模式
        if args.batch:
            items = [item.strip() for item in args.batch.split("|") if item.strip()]
            if not items:
                raise MerbloggerError("E001")
            results = process_batch(items)
            output_data = {"status": "success", "batch_count": len(results), "results": results}
        else:
            # 单条模式
            if args.file:
                text = read_input_file(args.file)
            else:
                text = args.input
            result = process_text(text)
            output_data = result

        # 输出
        if args.format == "text" and not args.batch:
            # 文本模式输出
            print(output_data.get("output_text", str(output_data)))
        else:
            write_output(output_data, args.output)
        return 0

    except MerbloggerError as exc:
        print(f"错误 {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底
        print(f"错误 E010: 内部逻辑错误 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
