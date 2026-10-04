# -*- coding: utf-8 -*-
"""main.py — batch-renamer 批量重命名引擎

规则引擎：查找替换 / 序号 / 日期前缀 / 大小写 / 扩展名保留。
安全设计（军规 R4）：默认只打印变更预览不落盘；--apply 才执行；--undo 回滚上次。
"""
from __future__ import print_function
import argparse
import datetime
import io
import json
import os
import re
import sys

VERSION = "1.0.0"
UNDO_FILE = os.path.join(os.path.expanduser("~"), ".batch_renamer_undo.json")


def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    last = None
    for enc in encodings:
        try:
            with io.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
    if last is not None:
        raise last
    return ""


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="batch-renamer", description="批量文件重命名（默认预览，--apply 执行，--undo 回滚）")
    p.add_argument("--dir", default=".", help="目标目录")
    p.add_argument("--pattern", default="*", help="匹配模式（如 *.txt、report_*）")
    p.add_argument("--find", default="", help="查找文本（替换用）")
    p.add_argument("--replace", default="", help="替换文本")
    p.add_argument("--prefix", default="", help="加前缀")
    p.add_argument("--suffix", default="", help="加后缀（扩展名前）")
    p.add_argument("--seq", action="store_true", help="按序加序号 01,02…")
    p.add_argument("--seq-start", type=int, default=1)
    p.add_argument("--date", action="store_true", help="加日期前缀 YYYYMMDD")
    p.add_argument("--case", default="", choices=["lower", "upper", "title"], help="大小写转换（仅主名）")
    p.add_argument("--ext", default="keep", choices=["keep", "lower", "upper"], help="扩展名处理")
    p.add_argument("--apply", action="store_true", help="实际执行（默认仅预览）")
    p.add_argument("--undo", action="store_true", help="回滚上次执行")
    p.add_argument("--dry-run", action="store_true", help="预览（默认行为，显式亦可）")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--version", action="version", version="batch-renamer " + VERSION)
    return p.parse_args(argv)


def plan_rename(dirpath, pattern, args):
    """生成重命名计划 [(old_abs, new_name)]。规则顺序：find/replace → prefix/suffix → seq/date → case。"""
    try:
        import glob as _g  # noqa: F401 - 兼容导入探测
    except Exception as exc:  # noqa: BLE001 - 缺 glob 不影响本实现（用 os.listdir）
        _g = None
    files = []
    for f in os.listdir(dirpath):
        full = os.path.join(dirpath, f)
        if not os.path.isfile(full):
            continue
        files.append(f)
    if pattern and pattern != "*":
        import fnmatch
        files = [f for f in files if fnmatch.fnmatch(f, pattern)]
    files.sort()
    plan = []
    for idx, fname in enumerate(files):
        name, ext = os.path.splitext(fname)
        new_name = name
        if args.find and args.find in new_name:
            new_name = new_name.replace(args.find, args.replace)
        elif args.find and args.replace == "":
            pass
        if args.prefix:
            new_name = args.prefix + new_name
        if args.suffix:
            new_name = new_name + args.suffix
        if args.seq:
            new_name = "%s%02d" % (new_name, args.seq_start + idx) if not new_name or new_name.endswith("_") \
                else new_name + "_%02d" % (args.seq_start + idx)
        if args.date:
            new_name = datetime.date.today().strftime("%Y%m%d") + "_" + new_name
        if args.case == "lower":
            new_name = new_name.lower()
        elif args.case == "upper":
            new_name = new_name.upper()
        elif args.case == "title":
            new_name = new_name.title()
        # 扩展名处理
        if args.ext == "lower":
            ext = ext.lower()
        elif args.ext == "upper":
            ext = ext.upper()
        new_full = new_name + ext
        if new_full == fname:
            continue
        plan.append((os.path.join(dirpath, fname), new_full))
    return plan


def apply_plan(plan, verbose):
    """执行重命名，返回 (done, log)。"""
    done, log = [], []
    for old_abs, new_name in plan:
        try:
            new_abs = os.path.join(os.path.dirname(old_abs), new_name)
            os.rename(old_abs, new_abs)
            done.append([old_abs, new_abs])
            log.append("renamed %s -> %s" % (os.path.basename(old_abs), new_name))
            if verbose:
                print("  ✔ %s -> %s" % (os.path.basename(old_abs), new_name))
        except Exception as exc:  # noqa: BLE001
            log.append("FAIL %s: %s" % (old_abs, exc))
    return done, log


def save_undo(done):
    try:
        io.open(UNDO_FILE, "w", encoding="utf-8").write(
            json.dumps({"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "pairs": done},
                       ensure_ascii=False))
        return True
    except Exception as exc:  # noqa: BLE001 - 回滚记录写失败需告知
        print("警告: 回滚记录写入失败: %s" % exc)
        return False


def do_undo():
    if not os.path.exists(UNDO_FILE):
        return 0, "无回滚记录"
    try:
        d = json.loads(io.open(UNDO_FILE, encoding="utf-8").read())
    except Exception as exc:  # noqa: BLE001
        return 1, "回滚记录损坏: %s" % exc
    ok = 0
    for old_abs, new_abs in d.get("pairs", []):
        try:
            if os.path.exists(new_abs):
                os.rename(new_abs, old_abs)
                ok += 1
        except Exception as exc:  # noqa: BLE001 - 单条回滚失败不中断其余
            print("  回滚失败 %s: %s" % (new_abs, exc))
    return 0 if ok or not d.get("pairs") else 1, "已回滚 %d 个" % ok


def run_selftest():
    import tempfile
    fails = []
    passed = []

    def check(name, cond, detail=""):
        if cond:
            passed.append(name)
        else:
            fails.append("%s: %s" % (name, detail))
        print("%s %s" % ("PASS" if cond else "FAIL", name))

    d = tempfile.mkdtemp()
    for f in ["report_a.txt", "report_b.txt", "note.md"]:
        io.open(os.path.join(d, f), "w", encoding="utf-8").write("x")
    plan = plan_rename(d, "*.txt", type("A", (), {
        "find": "report", "replace": "weekly", "prefix": "", "suffix": "", "seq": False,
        "seq_start": 1, "date": False, "case": "", "ext": "keep"})())
    check("计划生成(replace)", len(plan) == 2 and all("weekly" in p[1] for p in plan))
    done, log = apply_plan(plan, False)
    check("执行改名", len(done) == 2 and os.path.exists(os.path.join(d, "weekly_a.txt")))
    save_undo(done)
    rc, msg = do_undo()
    check("undo 回滚", os.path.exists(os.path.join(d, "report_a.txt")) and not os.path.exists(os.path.join(d, "weekly_a.txt")), msg)
    if os.path.exists(UNDO_FILE):
        os.remove(UNDO_FILE)
    return len(passed), fails


def _safe_main(argv=None):
    args = parse_args(argv)
    if args.selftest:
        passed, fails = run_selftest()
        print("selftest: %d passed, %d failed" % (passed, len(fails)))
        for f in fails:
            print(" - " + f)
        return 1 if fails else 0
    if args.undo:
        rc, msg = do_undo()
        print(msg)
        return rc
    dirpath = os.path.abspath(args.dir)
    if not os.path.isdir(dirpath):
        print("错误: 目录不存在 %s" % dirpath)
        return 2
    plan = plan_rename(dirpath, args.pattern, args)
    if not plan:
        print("无可重命名文件（规则未命中或全部相同）")
        return 0
    if not args.dry_run and not args.apply:
        # 预览分支（无 --apply 一律不落盘）
        print("预览（%d 个文件，加 --apply 执行）：" % len(plan))
        for old_abs, new_name in plan[:50]:
            print("  %s -> %s" % (os.path.basename(old_abs), new_name))
        if len(plan) > 50:
            print("  …共 %d 条" % len(plan))
        if args.as_json:
            print(json.dumps([{"from": os.path.basename(a), "to": b} for a, b in plan],
                             ensure_ascii=False, indent=1))
        return 0
    # --apply 执行分支
    if not args.dry_run:
        print("将执行 %d 个重命名（已预览确认，--undo 可回滚）:" % len(plan))
        done, log = apply_plan(plan, args.verbose)
        save_undo(done)
        print("完成 %d / %d（回滚记录已存 %s）" % (len(done), len(plan), UNDO_FILE))
        return 0
    save_undo(done)
    print("完成 %d / %d（回滚记录已存 %s）" % (len(done), len(plan), UNDO_FILE))
    return 0


def main(argv=None):
    try:
        return _safe_main(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    except Exception as exc:  # noqa: BLE001
        print("运行异常: %s（--selftest 自检）" % exc)
        return 9


def dry_run(argv=None):
    argv = list(argv) if argv else []
    argv.append("--dry-run")
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
