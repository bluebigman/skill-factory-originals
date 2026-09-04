#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest.py — short-video-script-gen 自检契约（9 项断言）"""
import io
import os
import sys
import tempfile

base = os.path.dirname(os.path.abspath(__file__))
for p in (base, os.path.join(base, "scripts")):
    if os.path.isdir(p):
        sys.path.insert(0, p)
failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append("%s: %s" % (name, detail))
    print("%s %s" % ("PASS" if cond else "FAIL", name))


def test_import():
    try:
        import run as r
        assert callable(getattr(r, "main", None)), "缺少 main"
        assert callable(getattr(r, "dry_run", None)), "缺少 dry_run"
        assert callable(getattr(r, "read_text_safe", None)), "缺少 read_text_safe"
        check("模块契约齐全(main/dry_run/read_text_safe)", True)
    except Exception as e:  # noqa: BLE001
        check("模块契约齐全(main/dry_run/read_text_safe)", False, str(e))


def test_cli_generate():
    try:
        import run as r
        rc = r.main(["--topic", "办公室咖啡技巧", "--platform", "douyin",
                     "--duration", "30", "--style", "knowhow", "--seed", "7"])
        check("CLI 生成正常退出(rc=0)", rc == 0, "rc=%s" % rc)
    except Exception as e:  # noqa: BLE001
        check("CLI 生成正常退出(rc=0)", False, str(e))


def test_output_shape():
    try:
        import run as r
        import io as _io
        buf = _io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            r.main(["--topic", "露营装备避坑", "--platform", "xiaohongshu",
                    "--count", "2", "--json", "--seed", "1"])
        finally:
            sys.stdout = old
        import json
        payload = json.loads(buf.getvalue())
        items = payload.get("items", [])
        ok = len(items) == 2 and all(len(s["shots"]) >= 3 for s in items)
        check("JSON 输出结构(count=2, 每脚本≥3镜)", ok)
    except Exception as e:  # noqa: BLE001
        check("JSON 输出结构(count=2, 每脚本≥3镜)", False, str(e))


def test_dry_run_no_write():
    try:
        import run as r
        target = os.path.join(tempfile.mkdtemp(), "should_not_exist.md")
        r.main(["--topic", "测试", "--out", target, "--dry-run"])
        check("dry-run 不写盘", not os.path.exists(target))
    except Exception as e:  # noqa: BLE001
        check("dry-run 不写盘", False, str(e))


def test_write_out():
    try:
        import run as r
        d = tempfile.mkdtemp()
        target = os.path.join(d, "out.md")
        rc = r.main(["--topic", "测试", "--out", target])
        exists = os.path.exists(target) and os.path.getsize(target) > 0
        check("--out 正常写盘", rc == 0 and exists, "rc=%s exists=%s" % (rc, exists))
    except Exception as e:  # noqa: BLE001
        check("--out 正常写盘", False, str(e))


def test_encoding():
    try:
        import run as r
        tmp = os.path.join(tempfile.mkdtemp(), "lexicon.txt")
        with io.open(tmp, "w", encoding="gbk") as fh:
            fh.write(u"口语词库：哇塞 绝了 真香")
        content = r.read_text_safe(tmp)
        check("read_text_safe gbk 容错", u"真香" in content)
    except Exception as e:  # noqa: BLE001
        check("read_text_safe gbk 容错", False, str(e))


def test_compliance_block():
    try:
        import run as r
        import io as _io
        buf = _io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = r.main(["--topic", "包治百病的神药推荐"])
        finally:
            sys.stdout = old
        check("绝对化/医疗词拦截(rc=3)", rc == 3, "rc=%s out=%s" % (rc, buf.getvalue()[:80]))
    except Exception as e:  # noqa: BLE001
        check("绝对化/医疗词拦截(rc=3)", False, str(e))


def test_bad_args():
    try:
        import run as r
        rc = r.main([])  # 缺 topic
        check("缺参数报错(rc=2)", rc == 2, "rc=%s" % rc)
    except Exception as e:  # noqa: BLE001
        check("缺参数报错(rc=2)", False, str(e))


def test_selftest_flag():
    try:
        import run as r
        rc = r.main(["--selftest"])
        check("--selftest 自检通过(rc=0)", rc == 0, "rc=%s" % rc)
    except Exception as e:  # noqa: BLE001
        check("--selftest 自检通过(rc=0)", False, str(e))


if __name__ == "__main__":
    test_import()
    test_cli_generate()
    test_output_shape()
    test_dry_run_no_write()
    test_write_out()
    test_encoding()
    test_compliance_block()
    test_bad_args()
    test_selftest_flag()
    print("TOTAL: %d checks, %d failures" % (9, len(failures)))
    sys.exit(1 if failures else 0)
