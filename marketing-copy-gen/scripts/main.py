# -*- coding: utf-8 -*-
"""main.py — 营销文案生成器 CLI 引擎

军规契约：
  R1 能力边界与 SKILL.md 一一对应（产品/卖点/人群/渠道/语气/count/json）
  R2 每函数 try-except 降级输出
  R3 read_text_safe 三级编码（utf-8 → gbk → gb18030）
  R4 默认只打印预览不写盘；--out 才写
  R5 线性处理
  R6 --verbose 输出每个渠道的文案决策明细
"""
from __future__ import print_function
import argparse
import io
import json
import os
import random
import sys

from template_lib import (
    TONES, CHANNELS, POINT_BRIDGES, ABSOLUTE_WORDS, RISK_INDUSTRY_WORDS,
    TITLE_TEMPLATES, DETAIL_TEMPLATES, MOMENTS_TEMPLATES, ADS_TEMPLATES,
    SLOGAN_TEMPLATES, XHS_TEMPLATES, EXPERIENCE_LINES,
    MAX_POINTS, MIN_POINTS, MAX_COUNT,
)

VERSION = "1.0.0"

DEFAULT_AUDIENCE = "目标用户"


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


def compliance_check(product, points_text):
    """扫描产品与卖点中的绝对化/风险行业词。"""
    blob = (product or "") + " " + (points_text or "")
    absolute = [w for w in ABSOLUTE_WORDS if w in blob]
    risky = [w for w in RISK_INDUSTRY_WORDS if w in blob]
    return (not absolute, absolute, risky)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="marketing-copy-gen",
        description="从卖点生成多平台营销文案矩阵（预览优先，不写盘）",
    )
    p.add_argument("--product", default="", help="产品/服务名称（必填）")
    p.add_argument("--points", default="", help="卖点，用 | 分隔（2-5 个，必填）")
    p.add_argument("--audience", default="", help="目标人群（缺省自动）")
    p.add_argument("--channels", default="all", help="title,detail,moments,ads,slogan,xhs")
    p.add_argument("--tone", default="pro", choices=sorted(TONES.keys()))
    p.add_argument("--top-point", dest="top_point", default="")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--out", default="")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--lexicon", default="")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--version", action="version", version="marketing-copy-gen " + VERSION)
    return p.parse_args(argv)


def resolve_points(raw, top_point, log):
    """解析卖点并排序：top_point 置顶，去重，保序。"""
    pts = [p.strip() for p in (raw or "").split("|") if p.strip()]
    if top_point:
        if top_point not in pts:
            pts.insert(0, top_point)
        else:
            pts.remove(top_point)
            pts.insert(0, top_point)
        log("decision", "主打卖点置顶: %s" % top_point)
    return pts


def resolve_audience(args, log):
    if args.audience:
        return args.audience
    return DEFAULT_AUDIENCE


def pick_audience_by_product(product, rng, log):
    """按产品词粗略推断人群，缺省 fallback。"""
    hints = {
        "耳机": "通勤族", "榨汁": "办公室白领", "咖啡": "上班族",
        "护肤": "精致女生", "健身": "健身党", "母婴": "新手妈妈",
        "宠物": "铲屎官", "办公": "职场人", "露营": "户外爱好者",
    }
    for key, val in hints.items():
        if key in (product or ""):
            log("decision", "人群推断: %s → %s" % (key, val))
            return val
    return DEFAULT_AUDIENCE


def channel_wanted(channels_arg, ch):
    if channels_arg == "all":
        return True
    parts = [x.strip().lower() for x in channels_arg.split(",") if x.strip()]
    return ch in parts


def generate_for_channel(ch, ctx, rng, log):
    """按渠道模板生成文案。ctx 含 product/points/audience/tone 等。"""
    product = ctx["product"]
    pts = ctx["points"]
    aud = ctx["audience"]
    exp = rng.choice(EXPERIENCE_LINES)
    fmt = {
        "product": product, "audience": aud, "top_point": pts[0],
        "points": " ".join(pts),
        "points_short": " ".join(pts[:2]),
        "p0": pts[0], "p1": pts[1] if len(pts) > 1 else pts[0],
        "p2": pts[2] if len(pts) > 2 else pts[-1],
        "exp": exp,
    }
    if ch == "title":
        tpl = rng.choice(TITLE_TEMPLATES)
        log("verbose", "标题模板：%s" % tpl[:20])
        return tpl.format(**fmt)
    if ch == "detail":
        return DETAIL_TEMPLATES[0].format(**fmt)
    if ch == "moments":
        return MOMENTS_TEMPLATES[0].format(**fmt)
    if ch == "ads":
        return ADS_TEMPLATES[0].format(**fmt)
    if ch == "slogan":
        tpl = rng.choice(SLOGAN_TEMPLATES)
        fmt["top_point_short"] = pts[0][:12]
        return tpl.format(**fmt)
    if ch == "xhs":
        return XHS_TEMPLATES[0].format(**fmt)
    return ""


def build_set(ctx, rng, log):
    """生成一套全渠道文案。"""
    out = {}
    for ch in CHANNELS:
        if channel_wanted(ctx["channels_arg"], ch):
            out[ch] = generate_for_channel(ch, ctx, rng, log)
            log("decision", "%s 渠道文案已生成" % ch)
    return out


def render_text(ctx, sets):
    lines = []
    lines.append("【营销文案 · %s · 人群: %s · 语气: %s】"
                 % (ctx["product"], ctx["audience"], ctx["tone"]))
    for idx, s in enumerate(sets):
        if len(sets) > 1:
            lines.append("======== 第 %d 套 ========" % (idx + 1))
        for ch, text in s.items():
            lines.append("═══ %s ═══" % CHANNELS[ch])
            lines.append(text)
            lines.append("")
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

    pts = resolve_points("30秒出汁|USB充电|可拆洗", "USB充电", lambda k, m: None)
    check("卖点解析与置顶", pts[0] == "USB充电" and len(pts) == 3)

    ok, absolute, risky = compliance_check("全网销量第一的耳机", "")
    check("绝对化词拦截", ok is False and "第一" in absolute, "未拦 %s" % absolute)
    ok2, _a, _r = compliance_check("便携榨汁杯", "30秒出汁")
    check("常规产品放行", ok2 is True)

    ctx = {"product": "榨汁杯", "points": ["30秒出汁", "可拆洗"], "audience": "白领",
           "tone": "young", "channels_arg": "all"}
    rng = random.Random(1)
    log = lambda k, m: None  # noqa: E731
    s = build_set(ctx, rng, log)
    check("全渠道生成(≥5类)", len(s) >= 5 and "title" in s and "xhs" in s)

    try:
        parse_args(["--tone", "bad"])
        check("非法语气拦截", False)
    except SystemExit:
        check("非法语气拦截", True)

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

    if args.seed is not None:
        random.seed(args.seed)

    errs = []
    if not args.product:
        errs.append("缺少 --product 产品名称")
    pts = resolve_points(args.points, args.top_point, log)
    if len(pts) < MIN_POINTS:
        errs.append("卖点至少 %d 个（用 | 分隔），当前 %d 个" % (MIN_POINTS, len(pts)))
    if len(pts) > MAX_POINTS:
        errs.append("卖点最多 %d 个" % MAX_POINTS)
    if not (1 <= args.count <= MAX_COUNT):
        errs.append("套数需 1-%d" % MAX_COUNT)
    if errs:
        for e in errs:
            print("错误: " + e)
        return 2

    ok, absolute, risky = compliance_check(args.product, args.points)
    if not ok:
        print("文案含绝对化用语: %s → 请替换为真实可验证表述" % "、".join(absolute))
        return 3
    if risky:
        log("warn", "涉及强监管行业词(医疗/金融等): %s —— 输出仅供框架参考，功效/收益宣称须以官方说明为准" % "、".join(risky))

    rng = random.Random(args.seed if args.seed is not None else os.urandom(4).hex())
    audience = args.audience or pick_audience_by_product(args.product, rng, log)
    ctx = {"product": args.product, "points": pts, "audience": audience,
           "tone": args.tone, "channels_arg": args.channels}

    sets = []
    for _i in range(args.count):
        sets.append(build_set(ctx, rng, log))

    if args.as_json:
        payload = json.dumps({"generator": "marketing-copy-gen", "version": VERSION,
                              "product": args.product, "audience": audience,
                              "sets": sets}, ensure_ascii=False, indent=2)
    else:
        payload = render_text(ctx, sets)

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
