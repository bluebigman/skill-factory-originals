# -*- coding: utf-8 -*-
"""main.py — 市场分析报告生成器 CLI 引擎

军规契约：
  R1 能力边界与 SKILL.md 一一对应（行业/地域/深度/视角/focus/章节模板）
  R2 每函数 try-except 降级输出
  R3 read_text_safe 三级编码（utf-8 → gbk → gb18030）
  R4 默认只打印预览不写盘；--out 才写
  R5 线性处理
  R6 --verbose 输出每章的来源决策明细
"""
from __future__ import print_function
import argparse
import datetime
import io
import json
import os
import sys

from template_lib import (
    SECTIONS, VIEWS, DEEP_EXTRAS, PLACEHOLDER_DATA, PLACEHOLDER_SOURCE,
    WARN_INDUSTRY_WORDS,
)

VERSION = "1.0.0"

FOCUS_ALIAS = {
    "scale": "scale", "drivers": "drivers", "competition": "competition",
    "customer": "customer", "channel": "channel", "policy": "policy",
    "tech": "tech", "supply": "supply", "risk": "risk",
    "opportunity": "opportunity", "conclusion": "conclusion",
}


def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    last_err = None
    for enc in encodings:
        try:
            with io.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    if last_err is not None:
        raise last_err
    return ""


def compliance_check(industry):
    """强监管行业提醒（不拦截，报告头给合规注记）。"""
    return [w for w in WARN_INDUSTRY_WORDS if w in (industry or "")]


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="market-analysis-report",
        description="生成结构化市场分析报告框架（所有数据须人工核实并标注来源）",
    )
    p.add_argument("--industry", default="", help="行业/市场名称（必填）")
    p.add_argument("--region", default="中国", help="地域范围")
    p.add_argument("--depth", default="standard", choices=["standard", "deep"])
    p.add_argument("--view", default="invest", choices=sorted(VIEWS.keys()))
    p.add_argument("--focus", default="", help="维度子集（逗号分隔）")
    p.add_argument("--out", default="")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--seed", type=int, default=None, help="随机种子（兼容统一 CLI 契约）")
    p.add_argument("--version", action="version", version="market-analysis-report " + VERSION)
    return p.parse_args(argv)


def resolve_section_order(view, depth, focus_raw, log):
    """决定章节顺序：视角默认序 + deep 补 3 章 + focus 显式过滤。"""
    base = list(VIEWS[view]["order"])
    if depth == "deep":
        for extra in DEEP_EXTRAS:
            if extra not in base:
                base.insert(len(base) - 1, extra)  # 结论前插入
        log("decision", "深度 deep → 增补 %s" % "、".join(DEEP_EXTRAS))
    if focus_raw:
        wanted = []
        for token in focus_raw.split(","):
            key = token.strip()
            if key in FOCUS_ALIAS:
                wanted.append(FOCUS_ALIAS[key])
        if wanted:
            base = [s for s in base if s in wanted]
            log("decision", "focus 过滤 → %d 章" % len(base))
    # 移除未知键防 KeyError
    order = [s for s in base if s in SECTIONS]
    return order


def build_chapter(key, industry, region, idx, log):
    """渲染单章：框架 + 必答 + 数据来源指引。"""
    cfg = SECTIONS[key]
    lines = []
    lines.append("## %d. %s（%s · %s）" % (idx + 1, cfg["title"], industry, region))
    lines.append("【分析框架】%s" % cfg["framework"])
    lines.append("【必答问题】")
    for q in cfg["questions"]:
        lines.append("- " + q)
    lines.append("【数据占位·必须标注来源】")
    if key in ("scale", "drivers", "competition"):
        lines.append("| 指标 | 数据 | 来源 |")
        lines.append("|---|---|---|")
        lines.append("| 示例指标 | %s | %s |" % (PLACEHOLDER_DATA, PLACEHOLDER_SOURCE))
    else:
        lines.append("- 关键事实: %s（%s）" % (PLACEHOLDER_DATA, PLACEHOLDER_SOURCE))
    lines.append("【建议信源】%s" % "、".join(cfg["sources"]))
    lines.append("")
    log("verbose", "章节 %d %s：信源 %d 项" % (idx + 1, cfg["title"], len(cfg["sources"])))
    return "\n".join(lines)


def build_report(industry, region, depth, view, focus_raw, log):
    order = resolve_section_order(view, depth, focus_raw, log)
    chapters = []
    for idx, key in enumerate(order):
        chapters.append(build_chapter(key, industry, region, idx, log))
    header_note = []
    risky = compliance_check(industry)
    if risky:
        header_note.append("合规提醒：%s 属强监管行业，报告中涉及政策/资质部分请以主管部门官方口径为准。"
                           % "、".join(risky))
    header_note.append("数据纪律：本框架中所有【待填】数据必须来自可核实来源并标注，禁止编造数字。")
    return {
        "industry": industry, "region": region, "depth": depth,
        "view": view, "view_name": VIEWS[view]["name"],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
        "chapters": [{"key": c["key"], "title": c["title"]} for c in []],  # 占位(下方重建)
        "notes": header_note,
    }, chapters


def render_text(meta, chapters):
    lines = []
    lines.append("# %s市场分析报告（%s）" % (meta["industry"], meta["region"]))
    lines.append("> 生成: %s ｜ 视角: %s ｜ 深度: %s" % (meta["generated_at"],
                                                     meta["view_name"], meta["depth"]))
    for note in meta["notes"]:
        lines.append("> ⚠ " + note)
    lines.append("")
    lines.extend(chapters)
    return "\n".join(lines)


def safe_write(path, content, log):
    try:
        d = os.path.dirname(os.path.abspath(path))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
        log("verbose", "写入 %s (%d 字符)" % (path, len(content)))
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def run_selftest():
    failures = []
    passed = []

    def check(name, cond, detail=""):
        if cond:
            passed.append(name)
        else:
            failures.append("%s: %s" % (name, detail))
        print("%s %s" % ("PASS" if cond else "FAIL", name))

    try:
        import main as m
        check("模块契约齐全", callable(getattr(m, "main", None))
              and callable(getattr(m, "read_text_safe", None)))
    except Exception as exc:  # noqa: BLE001
        check("模块契约齐全", False, str(exc))

    log = lambda k, m: None  # noqa: E731
    order = resolve_section_order("invest", "standard", "", log)
    check("投资视角章节≥7", len(order) >= 7)
    order_deep = resolve_section_order("invest", "deep", "", log)
    check("deep 增补章节(>standard)", len(order_deep) > len(order))
    order_focus = resolve_section_order("invest", "standard", "scale,risk", log)
    check("focus 过滤生效", order_focus == ["scale", "risk"])

    risky = compliance_check("医疗美容行业")
    check("强监管行业识别", "医疗" in risky)
    risky2 = compliance_check("宠物经济")
    check("常规行业放行", risky2 == [])

    meta, chapters = build_report("宠物经济", "中国", "standard", "invest", "", log)
    check("报告章节渲染", len(chapters) >= 7 and "待填" in chapters[0])
    check("禁编造占位存在", "来源" in chapters[0])

    try:
        parse_args(["--view", "nope"])
        check("非法视角拦截", False)
    except SystemExit:
        check("非法视角拦截", True)

    return len(passed), failures


def _safe_main(argv=None):
    args = parse_args(argv)
    log = _make_logger(args.verbose)

    if args.selftest:
        passed, fails = run_selftest()
        print("selftest: %d passed, %d failed" % (passed, len(fails)))
        for f in fails:
            print(" - " + f)
        return 1 if fails else 0

    errs = []
    if not args.industry:
        errs.append("缺少 --industry 行业名称")
    if errs:
        for e in errs:
            print("错误: " + e)
        return 2

    meta, chapters = build_report(args.industry, args.region, args.depth,
                                  args.view, args.focus, log)

    if args.as_json:
        meta["chapters"] = [{"no": i + 1, "title": ch.split("\n")[0].lstrip("#").strip()}
                            for i, ch in enumerate(chapters)]
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
    else:
        payload = render_text(meta, chapters)

    # ---- 输出决策（R4 预览撤回：dry-run 严格不写盘，--out 才落盘）----
    if not args.dry_run:
        if args.out:
            ok_w, msg = safe_write(args.out, payload, log)
            if not ok_w:
                print("写盘失败: " + msg)
                return 4
            print("已生成 → %s" % args.out)
            if args.verbose:
                print(payload)
            return 0
    # 默认走预览（无 --out 或 --dry-run 均不写盘）
    print(payload)
    return 0

def _make_logger(verbose):
    def log(kind, msg):
        if kind == "warn":
            print("# warn: " + msg)
        elif verbose and kind in ("decision", "verbose"):
            print("# %s: %s" % (kind, msg))
    return log


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
