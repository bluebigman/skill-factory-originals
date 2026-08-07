#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — superpowers 技能框架的独立实现

仅依据功能规格文档（clean-room）编写，不参考任何既有实现。
提供命令行接口与内置自检（--selftest）。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义（对应规格"四、异常处理"）
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",  # 具体缺失项由调用方拼接
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}


class SuperpowersError(Exception):
    """带错误码的业务异常"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心逻辑：结构化解析与置信度标注
# ---------------------------------------------------------------------------

# 可被识别的关键字段（规格 Step2：识别关键字段并结构化）
KNOWN_FIELDS = ("id", "name", "type", "value", "timestamp", "source")


def parse_input(raw: str) -> Tuple[Dict[str, Any], float]:
    """
    解析输入字符串，提取关键信息并计算置信度。

    规则（依据规格 Step2）：
      - 按行/逗号/分号分割片段
      - 片段若形如 "key=value" 或 "key:value" 则作为字段
      - 其余片段归入 "notes"
      - 置信度 = 已识别字段数 / 已知字段总数（宽松区间判断）

    返回 (结构化字典, 置信度 0~100)
    """
    if not raw or not raw.strip():
        raise SuperpowersError("E001")

    # 简单分片（不依赖正则，保持标准库与可读性）
    parts = []
    for sep in (",", ";", "\n", "|"):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            break
    if not parts:
        parts = [raw.strip()]

    result: Dict[str, Any] = {}
    notes: List[str] = []

    for part in parts:
        # 尝试 "key=value" 或 "key:value"
        key = value = None
        for sep in ("=", ":"):
            if sep in part:
                left, right = part.split(sep, 1)
                key = left.strip().lower()
                value = right.strip()
                break
        if key and key in KNOWN_FIELDS:
            result[key] = value
        else:
            notes.append(part)

    if notes:
        result["notes"] = notes

    # 置信度 = 已识别字段数 / 已知字段总数（宽松）
    recognized = sum(1 for k in KNOWN_FIELDS if k in result)
    confidence = round(recognized / len(KNOWN_FIELDS) * 100)

    return result, confidence


def format_output(data: Dict[str, Any], confidence: float) -> str:
    """
    按规格 Step3 格式化输出，并根据置信度添加标注：
      - >=90% 直接输出
      - 85~90% 标注"建议复核"
      - <85% 标注"[需核实]"
    """
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: {', '.join(value)}")
        else:
            lines.append(f"{key}: {value}")

    if confidence >= 90:
        label = ""
    elif confidence >= 85:
        label = " [建议复核]"
    else:
        label = " [需核实]"

    header = f"解析结果（置信度 {confidence}%）{label}"
    return header + "\n" + "\n".join(lines)


def process_input(raw: str) -> str:
    """完整处理流程：解析 -> 校验 -> 输出（规格 Step2/Step3）"""
    data, conf = parse_input(raw)

    # 关键信息缺失检查（规格 E002：至少要有 1 个已知字段或 notes）
    if not data:
        raise SuperpowersError("E002", ERROR_CODES["E002"] + "至少需要一个有效字段或备注")

    return format_output(data, conf)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# 使用内置硬编码样例，不读文件、不联网、不依赖目录
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """离线自检核心逻辑，宽阈值断言，任何环境可过。"""
    print("[selftest] 开始自检（内置样例，离线模式）...")

    # 样例1：完整字段输入，置信度应较高
    sample1 = "id=1001, name=测试项目, type=文档, value=示例内容, timestamp=2026-01-01, source=本地"
    try:
        data1, conf1 = parse_input(sample1)
        assert len(data1) >= 4, "样例1应识别至少4个字段"
        assert conf1 >= 80, f"样例1置信度应>=80，实际{conf1}"
        out1 = format_output(data1, conf1)
        assert "置信度" in out1, "输出应包含置信度标注"
        print(f"[selftest] 样例1通过（字段数={len(data1)}, 置信度={conf1}%）")
    except AssertionError as e:
        print(f"[selftest] 样例1失败: {e}")
        return 1
    except SuperpowersError as e:
        print(f"[selftest] 样例1异常: {e}")
        return 1

    # 样例2：空输入，应触发 E001
    try:
        parse_input("   ")
        print("[selftest] 样例2失败：空输入应报E001")
        return 1
    except SuperpowersError as e:
        assert e.code == "E001", f"错误码应为E001，实际{e.code}"
        print("[selftest] 样例2通过（空输入正确报E001）")

    # 样例3：低置信度输入（只有1个字段），应标注需核实
    sample3 = "id=42"
    try:
        data3, conf3 = parse_input(sample3)
        assert conf3 < 85, f"样例3置信度应<85，实际{conf3}"
        out3 = format_output(data3, conf3)
        assert "需核实" in out3, "低置信度应包含[需核实]标注"
        print(f"[selftest] 样例3通过（置信度={conf3}%，含需核实标注）")
    except AssertionError as e:
        print(f"[selftest] 样例3失败: {e}")
        return 1

    # 样例4：格式错误输入（无分隔符、无字段），应归入 notes 且不崩溃
    sample4 = "这是一段没有结构的文本内容"
    try:
        data4, conf4 = parse_input(sample4)
        assert "notes" in data4, "无结构输入应归入notes"
        assert conf4 == 0, f"无字段置信度应为0，实际{conf4}"
        print("[selftest] 样例4通过（无结构文本正确归入notes）")
    except AssertionError as e:
        print(f"[selftest] 样例4失败: {e}")
        return 1

    print("[selftest] 全部自检通过 ✅")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="superpowers 技能框架 — 独立实现",
        epilog="示例: python main.py 'id=1, name=测试' 或 python main.py --selftest",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="待处理的内容（用户提供的数据/文件/URL 的文本表示）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不依赖外部文件/网络）",
    )

    args = parser.parse_args(argv)

    if args.selftest:
        return _run_selftest()

    if not args.input:
        # 无输入且非 selftest：给出引导话术（E001）
        print(ERROR_CODES["E001"])
        return 1

    try:
        result = process_input(args.input)
        print(result)
        return 0
    except SuperpowersError as e:
        print(f"错误 {e.code}: {e.message}")
        return 1
    except Exception as e:  # 兜底（E010 通用错误）
        print(f"[E010] 未预期错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
