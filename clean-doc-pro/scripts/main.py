#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clear-empty-attributes — 命令行工具（原创实现，clean-room）
技能「clear-empty-attributes」的完整实现核心业务逻辑，提供 CLI 入口、参数化控制、自检与真实数据处理。
含真实业务实现与第三方依赖。
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any, Dict, List, Union

HERE = Path(__file__).resolve().parent
TRIGGERS = ["clear-empty-attributes"]



def _read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    """多编码安全读取（utf-8/gbk/gb18030 依次尝试，最后 replace 兜底）"""
    for _enc in encodings:
        try:
            with open(path, encoding=_enc, errors="replace") as _f:
                return _f.read()
        except (UnicodeDecodeError, OSError, LookupError):
            continue
    with open(path, encoding="utf-8", errors="replace") as _f:
        return _f.read()

def load_spec() -> str:
    # 资产池/发布目录均为 SKILL.md 在技能根目录、scripts/ 为其子目录，故读父目录
    p = HERE.parent / "SKILL.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def match_trigger(text: str):
    low = text.lower()
    return [t for t in TRIGGERS if t.lower() in low]


def clean_empty_attributes(data: Any) -> Any:
    """
    核心数据清洗函数：递归地将所有空字符串（""）转换为 None。
    支持 dict、list、tuple、set 等嵌套结构。
    """
    if isinstance(data, dict):
        return {k: clean_empty_attributes(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_empty_attributes(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(clean_empty_attributes(item) for item in data)
    elif isinstance(data, set):
        return {clean_empty_attributes(item) for item in data}
    elif data == "":
        return None
    else:
        return data


def clean_json_input(json_str: str) -> str:
    """
    将 JSON 字符串中的空字符串转换为 null，并返回 JSON 字符串。
    """
    try:
        data = json.loads(json_str)
        cleaned = clean_empty_attributes(data)
        return json.dumps(cleaned, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        raise ValueError(f"无效的 JSON 输入: {e}")


def selftest() -> int:
    # 测试触发词和 SKILL.md 可读性
    assert TRIGGERS, "触发器列表为空"
    assert load_spec().strip(), "SKILL.md 为空"
    print("  [OK] 触发器 %d 个" % len(TRIGGERS))
    print("  [OK] SKILL.md 可读")
    sample = " ".join(TRIGGERS[:1])
    got = match_trigger(sample)
    assert got, "触发匹配失败"
    print("  [OK] 触发匹配:", got)

    # 核心功能测试：空字符串转 None
    test_data = {
        "name": "test",
        "empty": "",
        "nested": {
            "a": "",
            "b": "value",
            "list": ["", "x", ""],
            "tuple": ("", "y"),
            "set": {"", "z"}
        },
        "num": 0,
        "none": None
    }
    expected = {
        "name": "test",
        "empty": None,
        "nested": {
            "a": None,
            "b": "value",
            "list": [None, "x", None],
            "tuple": (None, "y"),
            "set": {None, "z"}
        },
        "num": 0,
        "none": None
    }
    result = clean_empty_attributes(test_data)
    assert result == expected, f"核心转换失败: {result}"
    print("  [OK] 核心转换: 空字符串 → None")

    # 测试 JSON 输入输出
    json_input = '{"a": "", "b": {"c": "", "d": "x"}, "e": ["", 1]}'
    json_expected = '{\n  "a": null,\n  "b": {\n    "c": null,\n    "d": "x"\n  },\n  "e": [\n    null,\n    1\n  ]\n}'
    json_result = clean_json_input(json_input)
    assert json_result == json_expected, f"JSON 转换失败: {json_result}"
    print("  [OK] JSON 输入输出转换")

    print("== clear-empty-attributes 命令行工具自检通过 ✅ ==")
    return 0


def main():
    ap = argparse.ArgumentParser(description="clear-empty-attributes 命令行工具")
    ap.add_argument("--guide", action="store_true", help="打印能力速览")
    ap.add_argument("--match", default="", help="输入文本，匹配触发词")
    ap.add_argument("--clean", default="", help="输入 JSON 字符串，清洗空字符串为 null")
    ap.add_argument("--selftest", action="store_true", help="离线自检")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.clean:
        try:
            result = clean_json_input(args.clean)
            print(result)
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    if args.match:
        print("命中触发词:", match_trigger(args.match))
        return 0
    if args.guide:
        md = load_spec()
        print("\n".join(l for l in md.splitlines() if l.strip())[:40])
        return 0
    print("用法: python run.py --guide | --match 文本 | --clean JSON | --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
