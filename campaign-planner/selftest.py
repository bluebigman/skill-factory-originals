#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest.py — campaign-planner 自检契约（9 项断言）"""
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
        ok = (callable(getattr(r, "main", None))
              and callable(getattr(r, "dry_run", None))
              and callable(getattr(r, "read_text_safe", None)))
        check("模块契约齐全(main/dry_run/read_text_safe)", ok)
    except Exception as e:
        check("模块契约齐全(main/dry_run/read_text_safe)", False, str(e))


def test_cli_generate():
    try:
        import run as r
        rc = r.main(["--topic", "测试主题内容", "--seed", "5"])
        check("CLI 生成正常退出(rc=0)", rc == 0, "rc=%s" % rc)
    except Exception as e:
        check("CLI 生成正常退出(rc=0)", False, str(e))


def test_output_shape():
    try:
        import run as r
        import json as _json
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            r.main(["--topic", "结构化输出测试", "--json", "--seed", "1"])
        finally:
            sys.stdout = old
        payload = _json.loads(buf.getvalue())
        items = payload.get("items", [])
        ok = len(items) == 1 and len(items[0].get("paras", [])) >= 3
        check("JSON 输出结构(≥3段)", ok)
    except Exception as e:
        check("JSON 输出结构(≥3段)", False, str(e))


def test_dry_run_no_write():
    try:
        import run as r
        target = os.path.join(tempfile.mkdtemp(), "nope.md")
        r.main(["--topic", "测试", "--out", target, "--dry-run"])
        check("dry-run 不写盘", not os.path.exists(target))
    except Exception as e:
        check("dry-run 不写盘", False, str(e))


def test_write_out():
    try:
        import run as r
        d = tempfile.mkdtemp()
        target = os.path.join(d, "out.md")
        rc = r.main(["--topic", "落盘测试", "--out", target])
        check("--out 正常写盘", rc == 0 and os.path.exists(target)
              and os.path.getsize(target) > 0)
    except Exception as e:
        check("--out 正常写盘", False, str(e))


def test_encoding():
    try:
        import run as r
        tmp = os.path.join(tempfile.mkdtemp(), "in.txt")
        with io.open(tmp, "w", encoding="gbk") as fh:
            fh.write(u"输入编码测试")
        content = r.read_text_safe(tmp)
        check("read_text_safe gbk 容错", u"输入编码测试" in content)
    except Exception as e:
        check("read_text_safe gbk 容错", False, str(e))


def test_input_file():
    try:
        import run as r
        tmp = os.path.join(tempfile.mkdtemp(), "in.txt")
        with io.open(tmp, "w", encoding="utf-8") as fh:
            fh.write(u"文件输入测试内容")
        rc = r.main(["--input", tmp])
        check("--input 文件输入(rc=0)", rc == 0, "rc=%s" % rc)
    except Exception as e:
        check("--input 文件输入(rc=0)", False, str(e))


def test_bad_args():
    try:
        import run as r
        rc = r.main([])  # 缺输入
        check("缺输入报错(rc=2)", rc == 2, "rc=%s" % rc)
    except Exception as e:
        check("缺输入报错(rc=2)", False, str(e))


def test_selftest_flag():
    try:
        import run as r
        rc = r.main(["--selftest"])
        check("--selftest 自检通过(rc=0)", rc == 0, "rc=%s" % rc)
    except Exception as e:
        check("--selftest 自检通过(rc=0)", False, str(e))


if __name__ == "__main__":
    test_import()
    test_cli_generate()
    test_output_shape()
    test_dry_run_no_write()
    test_write_out()
    test_encoding()
    test_input_file()
    test_bad_args()
    test_selftest_flag()
    print("TOTAL: 9 checks, %d failures" % len(failures))
    sys.exit(1 if failures else 0)
