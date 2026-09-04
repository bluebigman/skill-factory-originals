#!/usr/bin/env python3
"""run.py — 入口（转发至 scripts/main.py）"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    """三级编码容错读取（军规 R3）。"""
    import io
    last = None
    for enc in encodings:
        try:
            with io.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception as e:  # noqa: BLE001 - 编码降级需连续尝试
            last = e
    raise last

def main(argv=None):
    import main as _impl
    return _impl.main(argv)

def dry_run(argv=None):
    """dry-run 预览：只展示将写入内容，不写盘。"""
    import main as _impl
    return _impl.dry_run(argv)

if __name__ == "__main__":
    sys.exit(main())
