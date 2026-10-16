#!/usr/bin/env python3
"""可复现性验证脚本 —— 校验本目录内容的 Merkle 根是否与 merkle_root 一致。

★ 算法与 `_reseal_merkle.py` 的 `merkle_of()` **逐字一致**（2026-10-16 对齐）：
  · 取 `os.walk` 下**全部文件**，排除 `merkle_root` / `prev_hash` / `README.md`
  · 各文件 sha256 → **排序** → 逐层两两拼接再 sha256，直至单根
  （注：本脚本文本模式写入时曾致 CRLF 化而毁链，故仓库已锁 `.gitattributes = * -text`）

用法：
  python reproduce.py          # 校验（退出码 0=一致 / 1=不一致）
"""
from __future__ import annotations
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXCL = ("merkle_root", "prev_hash", "README.md")


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def merkle_of(d: str) -> str:
    files = [p for p in (os.path.join(dp, f) for dp, _, fs in os.walk(d) for f in fs)
             if os.path.basename(p) not in EXCL]
    leaves = sorted(h(open(f, "rb").read()) for f in files)
    while len(leaves) > 1:
        nxt = []
        for i in range(0, len(leaves), 2):
            nxt.append(h((leaves[i] + leaves[i + 1]).encode())
                       if i + 1 < len(leaves) else leaves[i])
        leaves = nxt
    return leaves[0] if leaves else ""


def main() -> int:
    mp = os.path.join(HERE, "merkle_root")
    if not os.path.isfile(mp):
        print("  🔴 缺 merkle_root")
        return 1
    want = open(mp, encoding="utf-8").read().strip()
    got = merkle_of(HERE)
    same = got == want
    print(("  ✅ " if same else "  🔴 ") + "merkle_root %s" % ("一致" if same else "不一致"))
    if not same:
        print("     期望: %s" % want)
        print("     实算: %s" % got)
    print("\n可复现性验证:", "PASS" if same else "FAIL")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())