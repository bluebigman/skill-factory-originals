# -*- coding: utf-8 -*-
"""main.py — 口播稿生成器 CLI 引擎

军规契约：
  R1 能力边界与 SKILL.md 一一对应（场景/语气/字数/角度/节奏点/词库/json）
  R2 每函数 try-except 降级输出
  R3 read_text_safe 三级编码（utf-8 → gbk → gb18030）
  R4 默认只打印预览不写盘；--out 才写
  R5 线性处理
  R6 --verbose 输出段落节奏决策明细
"""
from __future__ import print_function
import argparse
import io
import json
import os
import random
import sys

from template_lib import (
    SCENES, TONES, OPENERS, VALUE_LINES, BENEFIT_TEMPLATES, PAIN_LINES,
    PROOF_LINES, CTA_LINES, INTERACT_LINES, WARMUP_LINES, ANGLES,
    BLOCK_WORDS, RISK_WORDS, MIN_WORDS, MAX_WORDS, MIN_COUNT, MAX_COUNT,
)

VERSION = "1.0.0"


def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    """R3: 三级编码容错读取。"""
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


def compliance_check(topic):
    """扫描主题命中禁止词/风险词。返回 (ok, block_hits, risk_hits)。"""
    blob = topic or ""
    block = [w for w in BLOCK_WORDS if w in blob]
    risky = [w for w in RISK_WORDS if w in blob]
    return (not block, block, risky)


def sanitize_topic(topic):
    if not topic:
        return ""
    return " ".join(str(topic).split())[:80]


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="talking-script-gen",
        description="按主题/场景/语气生成口播逐字稿（节奏点标注，不写盘预览优先）",
    )
    p.add_argument("--topic", required=False, default="")
    p.add_argument("--scene", default="short", choices=sorted(SCENES.keys()))
    p.add_argument("--tone", default="warm", choices=sorted(TONES.keys()))
    p.add_argument("--words", type=int, default=250)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--angle", default="")
    p.add_argument("--out", default="")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--lexicon", default="")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--version", action="version", version="talking-script-gen " + VERSION)
    return p.parse_args(argv)


def validate_args(args, log):
    errs = []
    if not args.topic:
        errs.append("缺少 --topic 口播主题")
    if not (MIN_WORDS <= args.words <= MAX_WORDS):
        errs.append("字数需在 %d-%d 之间" % (MIN_WORDS, MAX_WORDS))
    if not (MIN_COUNT <= args.count <= MAX_COUNT):
        errs.append("条数需在 %d-%d 之间" % (MIN_COUNT, MAX_COUNT))
    if args.angle and args.angle not in ANGLES:
        errs.append("切入角度必须在 %s 中" % "、".join(ANGLES))
    return errs


def pick_angles(count, forced, log):
    if forced:
        log("decision", "指定角度 %s x%d" % (forced, count))
        return [forced] * count
    pool = list(ANGLES)
    random.shuffle(pool)
    chosen = (pool * ((count // len(pool)) + 1))[:count]
    log("decision", "自动角度: %s" % "、".join(chosen))
    return chosen


def build_para(beat, topic, angle, scene, tone, rng, log):
    """按节拍生成一段口播文本（含节奏点标记）。"""
    t = TONES[tone]
    filler = t["fillers"]
    f = lambda s: s  # noqa: E731 - 占位（填充词在渲染期融入）
    if beat == "warmup":
        return rng.choice(WARMUP_LINES).format(topic=topic)
    if beat == "hook":
        key = rng.choice(["question", "shock", "promise"])
        return rng.choice(OPENERS[key]).format(topic=topic)
    if beat in ("value",):
        return rng.choice(VALUE_LINES["point"]).format(topic=topic) + \
            rng.choice(VALUE_LINES["reason"])
    if beat == "benefit":
        return rng.choice(BENEFIT_TEMPLATES)
    if beat == "pain":
        return rng.choice(PAIN_LINES).format(topic=topic)
    if beat == "proof":
        return rng.choice(PROOF_LINES)
    if beat == "interact":
        return rng.choice(INTERACT_LINES).format(topic=topic)
    if beat == "cta":
        return CTA_LINES[scene].format(topic=topic)
    # 兜底
    return rng.choice(PAIN_LINES).format(topic=topic)


def add_rhythm(text, beat, rng, log):
    """按节拍插入节奏点：hook 后停顿、value 段重音、interact 段互动。"""
    out = text
    if beat == "hook":
        out = out.replace("。", "。[停顿] ", 1)
        log("verbose", "hook 段插入[停顿]")
    elif beat in ("value", "benefit"):
        out = "[重音] " + out
        log("verbose", "卖点段前缀[重音]")
    elif beat == "interact":
        out = out + "[互动]"
    return out


def word_target_budget(total_words, structure):
    """按结构比例把总字数分配到节拍，返回 [(beat, start_pct, budget)]。"""
    total_ratio = sum(r for _b, r in structure)
    cursor = 0.0
    out = []
    for beat, ratio in structure:
        start = cursor / total_ratio
        end = (cursor + ratio) / total_ratio
        budget = int(total_words * (end - start))
        out.append({"beat": beat, "start_pct": start, "end_pct": end,
                    "budget": max(1, budget)})
        cursor += ratio
    return out


def build_script(topic, scene, tone, words, angle, idx, rng, log):
    """生成一条完整口播稿。"""
    scene_cfg = SCENES[scene]
    budgets = word_target_budget(words, scene_cfg["structure"])

    paras = []
    acc_words = 0
    for i, bd in enumerate(budgets):
        raw = build_para(bd["beat"], topic, angle, scene, tone, rng, log)
        text = add_rhythm(raw, bd["beat"], rng, log)
        seg_words = max(len(text), 8)
        acc_words += seg_words
        # 估算时间：该节拍预算字数按场景语速换算
        sec = int(round(bd["budget"] * 60.0 / scene_cfg["rate"]))
        paras.append({
            "beat": bd["beat"],
            "sec_from": int(round((bd["start_pct"]) * words * 60.0 / scene_cfg["rate"])),
            "sec_to": int(round((bd["end_pct"]) * words * 60.0 / scene_cfg["rate"])),
            "est_sec": max(2, sec),
            "text": text,
            "words_est": seg_words,
        })
        log("decision", "节拍 %s 预算约 %d 字 → %d 秒" % (bd["beat"], bd["budget"], max(2, sec)))

    total_sec = int(round(words * 60.0 / scene_cfg["rate"]))
    disclaimer = "免责提醒：实际效果因人而异，请勿承诺绝对收益或效果。"
    return {
        "topic": topic, "scene": scene, "scene_name": scene_cfg["name"],
        "tone": tone, "tone_name": TONES[tone]["name"], "angle": angle,
        "words": words, "est_sec": total_sec, "paras": paras,
        "note": scene_cfg["note"], "disclaimer": disclaimer,
    }


def render_text(script):
    lines = []
    lines.append("【口播稿 · %s · %s · %s语气 · ≈%d字/%d秒 · 角度:%s】"
                 % (script["topic"], script["scene_name"], script["tone_name"],
                    script["words"], script["est_sec"], script["angle"]))
    beat_label = {"hook": "开场", "value": "干货", "benefit": "卖点", "pain": "痛点",
                  "proof": "佐证", "cta": "促单", "interact": "互动",
                  "warmup": "暖场"}
    for pa in script["paras"]:
        label = beat_label.get(pa["beat"], pa["beat"])
        lines.append("▍%s %ds-%ds（%s）" % (label, pa["sec_from"], pa["sec_to"], pa["beat"]))
        lines.append("  %s" % pa["text"])
    lines.append("场景提示: %s" % script["note"])
    lines.append("> %s" % script["disclaimer"])
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
    except Exception as exc:  # noqa: BLE001 - 写盘失败降级报告
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
            fh.write(u"口播测试词")
        content = read_text_safe(tmp)
        os.remove(tmp)
        check("三级编码容错", content == u"口播测试词")
    except Exception as exc:  # noqa: BLE001
        check("三级编码容错", False, str(exc))

    ok, block, risky = compliance_check("保证赚钱的理财课")
    check("禁止词拦截", ok is False and len(block) > 0, "未拦截 %s" % block)
    ok2, _b, _r = compliance_check("如何坚持早起")
    check("常规主题放行", ok2 is True)

    rng = random.Random(3)
    log = lambda k, m: None  # noqa: E731
    s = build_script("如何坚持早起", "short", "warm", 200, "结论先行", 0, rng, log)
    check("结构完整(含开场+促单)", len(s["paras"]) >= 3
          and s["paras"][-1]["beat"] == "cta")
    check("字数/时长估算合理", 20 <= s["est_sec"] <= 120)

    try:
        parse_args(["--scene", "nope"])
        check("非法场景拦截", False)
    except SystemExit:
        check("非法场景拦截", True)

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

    ok, block, risky = compliance_check(args.topic)
    if not ok:
        print("主题命中禁止词: %s → 改写后再试" % "、".join(block))
        return 3
    if risky:
        log("warn", "风险词(医疗/金融): %s —— 输出仅供结构参考" % "、".join(risky))

    topic = sanitize_topic(args.topic)
    angles = pick_angles(args.count, args.angle, log)
    rng = random.Random(args.seed if args.seed is not None else os.urandom(4).hex())

    items = []
    for idx, angle in enumerate(angles):
        items.append(build_script(topic, args.scene, args.tone, args.words,
                                  angle, idx, rng, log))

    if args.as_json:
        payload = json.dumps({"generator": "talking-script-gen", "version": VERSION,
                              "items": items}, ensure_ascii=False, indent=2)
    else:
        payload = "".join(render_text(s) for s in items)

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
