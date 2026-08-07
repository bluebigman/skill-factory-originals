#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calais — 配套执行器（原创实现，clean-room）
技能「calais」的轻量辅助脚本：解析同目录 SKILL.md，提供 CLI 入口、触发词匹配、能力速览。
零第三方依赖。
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRIGGERS = ["calais"]


def load_spec() -> str:
    # 资产池/发布目录均为 SKILL.md 在技能根目录、scripts/ 为其子目录，故读父目录
    p = HERE.parent / "SKILL.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def match_trigger(text: str):
    low = text.lower()
    return [t for t in TRIGGERS if t.lower() in low]


def selftest() -> int:
    assert TRIGGERS, "触发器列表为空"
    assert load_spec().strip(), "SKILL.md 为空"
    print("  [OK] 触发器 %d 个" % len(TRIGGERS))
    print("  [OK] SKILL.md 可读")
    sample = " ".join(TRIGGERS[:1])
    got = match_trigger(sample)
    assert got, "触发匹配失败"
    print("  [OK] 触发匹配:", got)
    print("== calais 配套执行器自检通过 ✅ ==")
    return 0


def main():
    ap = argparse.ArgumentParser(description="calais 配套执行器")
    ap.add_argument("--guide", action="store_true", help="打印能力速览")
    ap.add_argument("--match", default="", help="输入文本，匹配触发词")
    ap.add_argument("--selftest", action="store_true", help="离线自检")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.match:
        print("命中触发词:", match_trigger(args.match))
        return 0
    if args.guide:
        md = load_spec()
        print("\n".join(l for l in md.splitlines() if l.strip())[:40])
        return 0
    print("用法: python run.py --guide | --match 文本 | --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
