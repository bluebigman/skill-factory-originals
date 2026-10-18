#!/usr/bin/env python3
"""run.py — CLI 入口（标准封装器，转发 scripts/main.py）"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import main as _impl

main = getattr(_impl, "_cli", None) or getattr(_impl, "main", None)
run_selftest = getattr(_impl, "run_selftest", None)

if __name__ == "__main__":
    sys.exit(main())
