#!/usr/bin/env python3
"""run.py — 入口（转发至 scripts/main.py）"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    import io
    last = None
    for enc in encodings:
        try:
            with io.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last

def main(argv=None):
    import main as _impl
    return _impl.main(argv)

def dry_run(argv=None):
    import main as _impl
    return _impl.dry_run(argv)

if __name__ == "__main__":
    sys.exit(main())
