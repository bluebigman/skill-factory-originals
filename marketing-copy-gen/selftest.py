#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest.py — marketing-copy-gen 自检契约（9 项断言）"""
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
    except Exception as e:  # noqa: BLE001
        check("模块契约齐全(main/dry_run/read_text_safe)", False, str(e))


def test_cli_generate():
    try:
        import run as r
        rc = r.main(["--product", "便携榨汁杯", "--points", "30秒出汁|USB充电|可拆洗",
                     "--tone", "young", "--seed", "7"])
        check("CLI 生成正常退出(rc=0)", rc == 0, "rc=%s" % rc)
    except Exception as e:  # noqa: BLE001
        check("CLI 生成正常退出(rc=0)", False, str(e))


def test_output_shape():
    try:
        import run as r
        import json as _json
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            r.main(["--product", "降噪耳机", "--points", "主动降噪|40小时续航",
                    "--json", "--seed", "1"])
        finally:
            sys.stdout = old
        payload = _json.loads(buf.getvalue())
        sets = payload.get("sets", [])
        ok = len(sets) == 1 and len(sets[0]) >= 5
        check("JSON 输出结构(全渠道≥5类)", ok)
    except Exception as e:  # noqa: BLE001
        check("JSON 输出结构(全渠道≥5类)", False, str(e))


def test_dry_run_no_write():
    try:
        import run as r
        target = os.path.join(tempfile.mkdtemp(), "nope.txt")
        r.main(["--product", "测试", "--points", "a|b", "--out", target, "--dry-run"])
        check("dry-run 不写盘", not os.path.exists(target))
    except Exception as e:  # noqa: BLE001
        check("dry-run 不写盘", False, str(e))


def test_write_out():
    try:
        import run as r
        d = tempfile.mkdtemp()
        target = os.path.join(d, "out.txt")
        rc = r.main(["--product", "测试", "--points", "a|b", "--out", target])
        check("--out 正常写盘", rc == 0 and os.path.exists(target)
              and os.path.getsize(target) > 0)
    except Exception as e:  # noqa: BLE001
        check("--out 正常写盘", False, str(e))


def test_encoding():
    try:
        import run as r
        tmp = os.path.join(tempfile.mkdtemp(), "lex.txt")
        with io.open(tmp, "w", encoding="gbk") as fh:
            fh.write(u"卖点词库 新鲜直达")
        content = r.read_text_safe(tmp)
        check("read_text_safe gbk 容错", u"新鲜直达" in content)
    except Exception as e:  # noqa: BLE001
        check("read_text_safe gbk 容错", False, str(e))


def test_compliance_block():
    try:
        import run as r
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = r.main(["--product", "全网销量" + "第一的耳机", "--points", "降噪|续航"])
        finally:
            sys.stdout = old
        check("绝对化用语拦截(rc=3)", rc == 3, "rc=%s" % rc)
    except Exception as e:  # noqa: BLE001
        check("绝对化用语拦截(rc=3)", False, str(e))


def test_bad_args():
    try:
        import run as r
        rc = r.main(["--product", "耳机"])  # 缺卖点
        check("缺卖点报错(rc=2)", rc == 2, "rc=%s" % rc)
    except Exception as e:  # noqa: BLE001
        check("缺卖点报错(rc=2)", False, str(e))


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
    print("TOTAL: 9 checks, %d failures" % len(failures))
    sys.exit(1 if failures else 0)
