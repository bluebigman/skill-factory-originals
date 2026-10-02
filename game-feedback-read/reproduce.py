#!/usr/bin/env python3
"""可复现性验证脚本 —— 在冻结环境下校验内容哈希与 Merkle 根是否一致。

用法：
  python reproduce.py          # 校验当前内容与 manifest/merkle 是否一致
  python reproduce.py --llm    # （可选）重新调用 LLM 生成并对比 hash，需 API Key
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
merkle_expected = (HERE / "merkle_root").read_text(encoding="utf-8").strip()


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ok = True
    md = (HERE / "SKILL.md").read_bytes()
    mp = (HERE / "scripts" / "main.py").read_bytes()
    for label, got, want in [
        ("SKILL.md", h(md), manifest["outputs"]["skill_md_sha256"]),
        ("scripts/main.py", h(mp), manifest["outputs"]["main_py_sha256"]),
    ]:
        same = got == want
        ok &= same
        print(("  ✅ " if same else "  🔴 ") + f"{label} sha256 {'一致' if same else '不一致'}")
    leaves = [h(md), h(mp), h(json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8"))]
    while len(leaves) > 1:
        nxt = []
        for i in range(0, len(leaves), 2):
            a = leaves[i]
            b = leaves[i + 1] if i + 1 < len(leaves) else a
            nxt.append(h((a + b).encode("utf-8")))
        leaves = nxt
    same = leaves[0] == merkle_expected
    ok &= same
    print(("  ✅ " if same else "  🔴 ") + f"merkle_root {'一致' if same else '不一致'}")
    print("\n可复现性验证:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
