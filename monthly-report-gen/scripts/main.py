# -*- coding: utf-8 -*-
"""main.py — 月度工作报告生成器 CLI 引擎（规则模板生成器）

军规契约：
  R1 能力边界与 SKILL.md 一一对应
  R2 每函数 try-except 降级输出
  R3 read_text_safe 三级编码（utf-8 → gbk → gb18030）
  R4 默认只打印预览不写盘；--out 才写（if not args.dry_run 字面控制）
  R5 线性处理
  R6 --verbose 输出段落决策明细
"""
from __future__ import print_function
import argparse
import io
import json
import os
import random
import sys

from template_lib import (SCENE_OPTIONS, STRUCTURE, TEMPLATES,
                          BLOCK_WORDS, RISK_WORDS, MIN_COUNT, MAX_COUNT)

VERSION = "1.0.0"
NAME = "月度工作报告生成器"


def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    last_err = None
    for enc in encodings:
        try:
            with io.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception as exc:  # noqa: BLE001 - 连续尝试不同编码
            last_err = exc
    if last_err is not None:
        raise last_err
    return ""


def compliance_check(text):
    blob = text or ""
    block = [w for w in BLOCK_WORDS if w in blob]
    risky = [w for w in RISK_WORDS if w in blob]
    return (not block, block, risky)


def sanitize(text):
    if not text:
        return ""
    return " ".join(str(text).split())[:4000]


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="monthly-report-gen",
        description="按本月工作要点生成完成、进展、问题与下月计划四段式月报。（离线模板引擎，不写盘预览优先）",
    )
    p.add_argument("--topic", default="", help="主题/内容（必填一：topic 或 input）")
    p.add_argument("--input", default="", help="输入文件路径（多编码容错；与 topic 二选一）")
    p.add_argument("--tone", default="pro", choices=sorted(SCENE_OPTIONS.keys()))
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--out", default="")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--version", action="version", version="monthly-report-gen " + VERSION)
    return p.parse_args(argv)


def validate_args(args, log):
    errs = []
    if not args.topic and not args.input:
        errs.append("缺少输入：--topic <内容> 或 --input <文件> 至少一项")
    if args.topic and args.input:
        errs.append("--topic 与 --input 二选一")
    if not (MIN_COUNT <= args.count <= MAX_COUNT):
        errs.append("变体数需在 %d-%d 之间" % (MIN_COUNT, MAX_COUNT))
    return errs


def fill_tpl(tpl, ctx):
    """填充模板占位符 {x}，缺 key 保留占位（由用户补全）。"""
    out = tpl
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def render_beat(beat, spec_ctx, rng, log):
    pool = TEMPLATES.get(beat) or ["（{beat} 段落占位）"]
    tpl = rng.choice(pool)
    # 特殊占位：序号类 {i} 用段落下标
    return tpl


def build_doc(topic, scene_val, idx, rng, log):
    total_ratio = sum(r for _b, r in STRUCTURE)
    paras = []
    beat_idx = 0
    for b, ratio in STRUCTURE:
        beat_idx += 1
        base = TEMPLATES.get(b) or []
        if not base:
            continue
        tpl = rng.choice(base)
        ctx = {"topic": topic, "scene": scene_val, "i": beat_idx, "n": len(STRUCTURE),
               "beat": b, "slogan": "让每一次投入都有回报"}
        text = fill_tpl(tpl, ctx)
        # 面向不同资产做上下文补全（通用词元）
        text = text.replace("{t}", topic).replace("{a}", "示例行动项（请按实际补全）")
        text = text.replace("{o}", "待指定").replace("{d}", "待定").replace("{r}", "已达成（请核对）")
        text = text.replace("{c}", "达成一致（详见记录）").replace("{pct}", "70%")
        text = text.replace("{e}", "本月内").replace("{p}", "待补全要点").replace("{pr}", "高")
        text = text.replace("{m}", "提前同步相关方").replace("{q}", "方法比速度更重要。")
        text = text.replace("{orig}", topic).replace("{new}", "（改写结果示例，正式输出按规则逐段处理）")
        text = text.replace("{t1}", "从0到1：{topic}的完整路径".format(topic=topic))
        text = text.replace("{t2}", "{topic}，为什么现在值得关注".format(topic=topic))
        text = text.replace("{t3}", "关于{topic}的三个真相".format(topic=topic))
        text = text.replace("{point}", "持续性与方法").replace("{kw}", "场景词")
        text = text.replace("{seg}", "开场破冰").replace("{amt}", "¥2,000").replace("{p1}", "蓄水期")
        text = text.replace("{p2}", "爆发期").replace("{p3}", "复盘期").replace("{v}", "1,000+")
        text = text.replace("{month}", "本月").replace("{pr}", "高")
        # 标题类特殊处理：title 资产直接产出多条标题
        if b == "titles":
            text = "\n".join(fill_tpl(tpl, {"t": t}) for t in rng.sample(
                ["{topic}的3个隐藏真相", "{topic}避坑指南：新手必看", "为什么{topic}值得你花10分钟", "我试了1个月{topic}，说点实话",
                 "{topic}这样做，效率翻倍", "别踩{topic}的5个坑", "{topic}入门到进阶", "关于{topic}，90%的人理解错了",
                 "{topic}｜一次讲透", "收藏！{topic}超全整理", "{topic}复盘：哪些钱白花了", "{topic}的底层逻辑"], 3))
            text = text.format(topic=topic)
        paras.append({"beat": b, "text": text})
        log("verbose", "节拍 %s → 模板 %d 字" % (b, len(text)))
    return {"topic": topic, "scene": scene_val, "paras": paras,
            "note": "模板框架输出，事实数据请按实际补全"}


def render_text(doc, scene_label):
    lines = []
    lines.append("【%s · %s】" % (NAME, scene_label))
    for pa in doc["paras"]:
        lines.append(pa["text"])
        lines.append("")
    lines.append("> " + doc["note"])
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
    except Exception as exc:  # noqa: BLE001 - 写盘失败降级
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

    try:
        tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_enc.txt")
        with io.open(tmp, "w", encoding="gbk") as fh:
            fh.write(u"编码容错测试词")
        content = read_text_safe(tmp)
        os.remove(tmp)
        check("三级编码容错", content == u"编码容错测试词")
    except Exception as exc:  # noqa: BLE001
        check("三级编码容错", False, str(exc))

    if BLOCK_WORDS:
        ok, block, risky = compliance_check(BLOCK_WORDS[0] + "示例文本")
        check("禁止词拦截", ok is False and len(block) > 0, "未拦截 %s" % block)
    ok2, _b, _r = compliance_check("常规测试内容")
    check("常规输入放行", ok2 is True)

    rng = random.Random(3)
    log = lambda k, m: None  # noqa: E731
    d = build_doc("测试主题", list(SCENE_OPTIONS.keys())[0], 0, rng, log)
    check("文档结构完整(≥3段)", len(d["paras"]) >= 3 and len(d["paras"][0]["text"]) > 0)

    try:
        parse_args(["--tone", "bad_opt"])
        check("非法模式拦截", False)
    except SystemExit:
        check("非法模式拦截", True)

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

    errs = validate_args(args, log)
    if errs:
        for e in errs:
            print("错误: " + e)
        return 2

    # 输入解析：topic 或文件
    raw = args.topic
    if args.input:
        try:
            raw = read_text_safe(args.input)
        except Exception as exc:  # noqa: BLE001
            print("读文件失败: %s（支持 utf-8/gbk/gb18030）" % exc)
            return 5
    raw = sanitize(raw)
    ok, block, risky = compliance_check(raw)
    if not ok:
        print("输入命中禁止词: %s → 改写后再试" % "、".join(block))
        return 3
    if risky:
        log("warn", "风险词: %s —— 输出仅供结构参考" % "、".join(risky))

    rng = random.Random(args.seed if args.seed is not None else os.urandom(4).hex())
    docs = []
    for idx in range(args.count):
        docs.append(build_doc(raw, args.tone, idx, rng, log))

    scene_label = SCENE_OPTIONS.get(args.tone, args.tone)
    if args.as_json:
        payload = json.dumps({"generator": "monthly-report-gen", "version": VERSION,
                              "items": docs}, ensure_ascii=False, indent=2)
    else:
        payload = "".join(render_text(d, scene_label) for d in docs)

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
    except Exception as exc:  # noqa: BLE001 - 顶层兜底
        print("运行异常: %s（--selftest 自检）" % exc)
        return 9


def dry_run(argv=None):
    argv = list(argv) if argv else []
    argv.append("--dry-run")
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
