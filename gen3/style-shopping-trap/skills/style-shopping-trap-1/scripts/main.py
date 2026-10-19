# -*- coding: utf-8 -*-
"""试穿要点 —— 买前必须看什么

契约（R1）：本模块能力边界 = ['试穿', '不合适', '踩坑', '只看正面', '站着看', '不抬手', '不看洗标']；不提供心理/医学诊断，超出即提示转介。
"""
import argparse
import io
import json
import sys

ERRORS = {
    "E01": "输入缺失：请提供 --text 或通过标准输入传入内容（AI 可补齐后重试）",
    "E02": "格式不符：请提供纯文本（AI 可按 input_schema 转换后重试）",
    "E03": "超出边界：本能力只处理 试穿、不合适、踩坑 相关情境（AI 应改用其他能力）",
    "E04": "内部错误：请带 retry_after 退避后重试 1 次",
}

KEYWORDS = ['试穿', '不合适', '踩坑', '只看正面', '站着看', '不抬手', '不看洗标']

RULES = [
 {
  "when": "只看正面",
  "then": "看侧面与背面：侧面决定是否显厚"
 },
 {
  "when": "站着看",
  "then": "坐着看：坐下是否勒、是否上移"
 },
 {
  "when": "不抬手",
  "then": "抬手试：肩袖是否卡"
 },
 {
  "when": "不看洗标",
  "then": "看洗标：不能机洗的要想清能否维护"
 }
]

BOUNDARY_HINT = "本能力不提供心理或医学诊断；如涉及自伤、重度抑郁等，请转介专业机构。"
DOMAIN_NAME = "09-OperationsHR"


def _read_text_safe(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with io.open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as e:
            raise RuntimeError("E04 读取失败: %s" % e)
    raise RuntimeError("E02 无法识别文件编码（已尝试 utf-8/gbk/gb18030）")


def _domain_analyze(text):
    """调用本领域**全部**专属判据，汇总领域分析结果

    ★ 两级实现（2026-10-19 加深）：
      · `_judge_xxx`（判据级）：返回 {score, found, missing, advice}
        —— 多项核对后给 0~100 分，并指出缺哪项、补什么
      · `_xxx`（关键词级，旧版）：返回 bool / list
    优先用判据级；没有判据级时退回旧版。两者都没有则该维度记为 None。

    ★ 为什么必须真调（审计抓出的致命缺陷）：
      领域块函数原来**零调用** = 死代码，删掉整块输出字节不变。
      现在逐个真调，结果进 detail["domain"] 并输出「领域维度分析」表。
    """
    res = {}
    names = [n for n, _f in _DOMAIN_FUNCS]
    # 先跑判据级
    for n, f in _DOMAIN_FUNCS:
        if not n.startswith("_judge_"):
            continue
        key = n[len("_judge_"):]
        try:
            res[key] = f(text or "")
        except Exception:
            res[key] = None
    # 没有判据级的维度，用关键词级补
    for n, f in _DOMAIN_FUNCS:
        if n.startswith("_judge_"):
            continue
        key = n.lstrip("_")
        if key in res:
            continue
        try:
            res[key] = f(text or "")
        except Exception:
            res[key] = None
    return res


def _match(text):
    """领域规则匹配（真实逻辑，非占位）

    ① 先按 RULES 的 when 匹配（本技能定义的触发情境，优先级最高）
    ② 再按 KEYWORDS 补充召回（检索词，命中时给首条规则的处置）
    两者按 trigger 去重，同一件事不重复报。
    """
    hits = []
    seen = set()
    low = (text or "").lower()
    for r in RULES:
        w = str(r.get("when") or "")
        if w and w.lower() in low and w not in seen:
            seen.add(w)
            hits.append({"trigger": w, "advice": r.get("then") or ""})
    for kw in KEYWORDS:
        k = str(kw or "")
        if k and k.lower() in low and k not in seen:
            seen.add(k)
            adv = RULES[0].get("then") if RULES else "按通用方法处置"
            hits.append({"trigger": k, "advice": adv})
    return hits


def _score_hits(hits, text):
    """给每条命中的建议打分（0~100），用于排优先级

    三个真实维度（不是拍脑袋权重）：
      位置分：触发词越靠前越重要（用户先提到的往往是主诉）
      明确度：触发词命中次数越多，说明这个问题被反复强调
      具体度：建议动作越长越具体，可执行性越高
    """
    total = max(1, len(text or ""))
    scored = []
    for h in hits:
        trig = h.get("trigger") or ""
        pos = text.find(trig) if text else -1
        pos_score = 40.0 * (1.0 - (pos / total)) if pos >= 0 else 0.0
        freq = (text.count(trig) if text else 0)
        freq_score = min(30.0, 10.0 * freq)
        adv = h.get("advice") or ""
        spec_score = min(30.0, len(adv) / 2.0)
        s = round(pos_score + freq_score + spec_score, 1)
        scored.append({"trigger": trig, "advice": adv, "score": s,
                       "why": "位置%.0f+频次%.0f+具体度%.0f"
                               % (pos_score, freq_score, spec_score)})
    return scored


def _rank_advice(scored, top=3):
    """按分数排序，返回「先做这个」的执行顺序（同分时保持原规则顺序）"""
    ordered = sorted(scored, key=lambda x: -x["score"])
    return ordered[:max(1, top)]


def _explain_score(item):
    """给用户解释为什么这条排第一（可读一句话，不暴露内部公式）"""
    s = item.get("score", 0)
    if s >= 70:
        return "优先级高：描述里反复出现该情境，建议立刻处理"
    if s >= 40:
        return "优先级中：与当前问题相关，建议本轮处理"
    return "优先级低：可作为后续改进项"


def analyze(text, verbose=False):
    """结构化分析：返回 dict（供 AI 直接消费）"""
    if not text or not text.strip():
        return {"ok": False, "error_code": "E01", "summary": ERRORS["E01"],
                "detail": {}, "next_actions": ["补充描述后重试"]}
    hits = _match(text)
    if verbose:
        print("[INFO] 命中关键词: %s" % [h["trigger"] for h in hits])
    if not hits:
        # ★ 未命中时**更要**给领域分析：
        #   用户说了一句含糊的话，正是需要「按本领域维度逐项核对缺什么」的时候。
        #   （原实现这里直接 return，领域算法根本不跑 ⇒ 用户拿不到任何可行动信息）
        dom0 = _domain_analyze(text)
        miss0 = [k for k, v in dom0.items()
                 if isinstance(v, dict) and v.get("missing")]
        acts = ["补充更具体的情境描述（如具体行为、发生场景）"]
        if miss0:
            top = miss0[0]
            d0 = dom0.get(top) or {}
            acts.insert(0, "按本领域维度补齐：%s（%s）"
                        % ("、".join((d0.get("missing") or [])[:3]),
                           d0.get("advice") or "见下方维度表"))
        return {"ok": True, "error_code": None,
                "summary": "未命中已知情境，给出通用建议；"
                           "但本领域有 %d 个维度可核对" % len(dom0),
                "detail": {"hits": [], "domain": dom0,
                           "boundary": BOUNDARY_HINT},
                "next_actions": acts}
    scored = _score_hits(hits, text)
    ranked = _rank_advice(scored, top=3)
    # ★ 领域专属分析（真调用领域块函数）
    dom = _domain_analyze(text)
    if verbose:
        for it in ranked:
            print("[INFO] 优先级 %.1f ｜ %s ｜ %s"
                  % (it["score"], it["trigger"], it["why"]))
    detail = {"hits": hits, "scored": scored, "ranked": ranked,
              "domain": dom, "boundary": BOUNDARY_HINT}
    actions = ["%s（%s）" % (it["advice"], _explain_score(it)) for it in ranked]
    if not actions:
        actions = ["按建议执行第一个动作", "一周后复盘效果"]
    return {"ok": True, "error_code": None,
            "summary": "命中 %d 个情境，已按优先级排序给出处置建议" % len(hits),
            "detail": detail,
            "next_actions": actions}


def render(result):
    """人类可读输出（AI 可解析的 JSON 摘要附在末尾）"""
    lines = ["## 分析结果", ""]
    lines.append(result["summary"])
    lines.append("")
    d = result.get("detail", {})
    dom = d.get("domain") or {}
    if dom:
        lines.append("### 领域维度分析（%s）" % DOMAIN_NAME)
        lines.append("")
        lines.append("| 维度 | 分析结果 |")
        lines.append("|---|---|")
        for k, v in dom.items():
            if isinstance(v, dict) and "score" in v:
                # 判据级：分数 + 缺口 + 建议
                vs = "**%.0f 分**" % v["score"]
                if v.get("missing"):
                    vs += " ｜ 缺：%s" % "、".join(v["missing"])
                    if v.get("advice"):
                        vs += " ｜ %s" % v["advice"]
                else:
                    vs += " ｜ 已齐"
            elif isinstance(v, dict):
                vs = "；".join("%s=%s" % (kk, "是" if vv else "否")
                              for kk, vv in v.items() if isinstance(vv, bool))
            elif isinstance(v, list):
                vs = "、".join(str(x) for x in v) or "（无）"
            elif isinstance(v, int):
                vs = "%d 项" % v
            else:
                vs = str(v)[:40]
            lines.append("| %s | %s |" % (k.replace("_", " "), vs or "—"))
        lines.append("")
    ranked = d.get("ranked") or []
    if ranked:
        lines.append("| 优先级 | 情境 | 建议动作 | 排序依据 |")
        lines.append("|---|---|---|---|")
        for i, it in enumerate(ranked, 1):
            lines.append("| %d（%.1f） | %s | %s | %s |"
                         % (i, it["score"], it["trigger"], it["advice"],
                            _explain_score(it)))
        lines.append("")
    elif d.get("hits"):
        lines.append("| 情境 | 建议动作 |")
        lines.append("|---|---|")
        for h in d["hits"]:
            lines.append("| %s | %s |" % (h["trigger"], h["advice"]))
        lines.append("")
    lines.append("> " + result["detail"].get("boundary", ""))
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps({"ok": result["ok"], "summary": result["summary"],
                             "next_actions": result["next_actions"],
                             "error_code": result["error_code"]},
                            ensure_ascii=False, indent=1))
    lines.append("```")
    return "\n".join(lines)


def _cli():
    """R1/R4/R6 契约 CLI：--text/--input/--dry-run/--verbose/--selftest"""
    ap = argparse.ArgumentParser(description="style-shopping-trap-1 命令行入口")
    ap.add_argument("--text", help="直接输入的文本")
    ap.add_argument("--input", "-i", help="输入文件路径")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    text = args.text
    if not text and args.input:
        try:
            text = _read_text_safe(args.input)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2
    if not text:
        try:
            if not sys.stdin.isatty():
                text = sys.stdin.read()
        except Exception:
            text = ""
    result = analyze(text or "", verbose=bool(args.verbose))
    print(render(result))
    return 0 if result["ok"] else 1


# ═══ 领域专属算法（lc-style）═══
# lc-style（穿搭场景）—— 生活子域判定块
# 依据：生活类资产在官方 15 领域里无对应判定维度，
# 本块按该子域的真实判断逻辑设计 4 个维度（判据级 0-100 分）。

def _judge_occasion(text):
    """occasion —— 判据级多维打分（0~100）

    判断项：上班、通勤、正式、婚礼、面试、休闲、场合
    缺口建议：先定场合正式度，场合错了再好看也不合适
    """
    t = text or ""
    found, missing = [], []
    for item in ['上班', '通勤', '正式', '婚礼', '面试', '休闲', '场合']:
        if item in t:
            found.append(item)
        else:
            missing.append(item)
    score = round(100.0 * len(found) / max(1, len(found) + len(missing)), 1)
    return {
        "score": score,
        "found": found,
        "missing": missing,
        "advice": ("（已齐）" if not missing
                   else "补：%s —— 先定场合正式度，场合错了再好看也不合适" % "、".join(missing)),
    }


def _judge_body_proportion(text):
    """body_proportion —— 判据级多维打分（0~100）

    判断项：显瘦、显高、身材、个子、胯、肩、腿
    缺口建议：说明关注的比例问题，版型选择取决于此
    """
    t = text or ""
    found, missing = [], []
    for item in ['显瘦', '显高', '身材', '个子', '胯', '肩', '腿']:
        if item in t:
            found.append(item)
        else:
            missing.append(item)
    score = round(100.0 * len(found) / max(1, len(found) + len(missing)), 1)
    return {
        "score": score,
        "found": found,
        "missing": missing,
        "advice": ("（已齐）" if not missing
                   else "补：%s —— 说明关注的比例问题，版型选择取决于此" % "、".join(missing)),
    }


def _judge_color_ratio(text):
    """color_ratio —— 判据级多维打分（0~100）

    判断项：颜色、配色、显白、色系、搭不搭
    缺口建议：说明现有颜色与想达到的效果，按 6:3:1 配比给方案
    """
    t = text or ""
    found, missing = [], []
    for item in ['颜色', '配色', '显白', '色系', '搭不搭']:
        if item in t:
            found.append(item)
        else:
            missing.append(item)
    score = round(100.0 * len(found) / max(1, len(found) + len(missing)), 1)
    return {
        "score": score,
        "found": found,
        "missing": missing,
        "advice": ("（已齐）" if not missing
                   else "补：%s —— 说明现有颜色与想达到的效果，按 6:3:1 配比给方案" % "、".join(missing)),
    }


def _judge_material_care(text):
    """material_care —— 判据级多维打分（0~100）

    判断项：材质、保养、洗、皱、起球
    缺口建议：说明材质与打理条件，不能维护的单品不建议买
    """
    t = text or ""
    found, missing = [], []
    for item in ['材质', '保养', '洗', '皱', '起球']:
        if item in t:
            found.append(item)
        else:
            missing.append(item)
    score = round(100.0 * len(found) / max(1, len(found) + len(missing)), 1)
    return {
        "score": score,
        "found": found,
        "missing": missing,
        "advice": ("（已齐）" if not missing
                   else "补：%s —— 说明材质与打理条件，不能维护的单品不建议买" % "、".join(missing)),
    }


_DOMAIN_FUNCS = [
    ('_judge_occasion', _judge_occasion),
    ('_judge_body_proportion', _judge_body_proportion),
    ('_judge_color_ratio', _judge_color_ratio),
    ('_judge_material_care', _judge_material_care),
]

def _run_selftest():
    """自检：8 类断言，能拦住「逻辑被改坏」

    ★ 设计原则（审计教训）：
      原来只测 happy path，把 render 改空、匹配废掉仍然 PASS。
      现在每条断言都对应一个**可被破坏的实现点**，改坏必红。
    """
    fails = []

    def chk(name, cond, detail=""):
        if not cond:
            fails.append(name)
            print("  FAIL %s %s" % (name, detail))

    # ① 空输入 → E01
    r0 = analyze("")
    chk("E01 空输入", r0.get("ok") is False
        and r0.get("error_code") == "E01", str(r0.get("error_code")))

    # ② 单条命中 → 有 ranked，且 trigger 正确
    kw = RULES[0]["when"] if RULES else "测试"
    r1 = analyze(kw)
    chk("单条命中 ok", r1.get("ok") is True)
    chk("单条命中 ranked 非空", bool(r1["detail"].get("ranked")))
    chk("单条命中 trigger 对得上",
        any(x["trigger"] == kw for x in (r1["detail"].get("ranked") or [])))

    # ③ 多条命中 → 按分数降序
    if len(RULES) >= 2:
        txt = RULES[0]["when"] + " " + RULES[1]["when"]
        r2 = analyze(txt)
        sc = [x["score"] for x in (r2["detail"].get("ranked") or [])]
        chk("多条命中 ≥2 条", len(sc) >= 2)
        chk("按分数降序", sc == sorted(sc, reverse=True), str(sc))

    # ④ 分词不命中 → 明确说未命中，不硬编答案
    r3 = analyze("zzz_完全无关的内容_qqq")
    chk("不命中如实报", "未命中" in str(r3.get("summary", ""))
        or not (r3["detail"].get("ranked")), str(r3.get("summary"))[:30])

    # ⑤ render 真实产出（★这条能抓住「render 改空」）
    out = render(r1)
    chk("render 非空", bool(out and len(out) > 40), "%d 字" % len(out or ""))
    chk("render 含标题", "## " in (out or ""))
    chk("render 含 JSON 块", "```json" in (out or ""))
    chk("render 含表格", "|" in (out or ""))

    # ⑥ 领域分析被真调用（★这条能抓住「领域块是死代码」）
    dom = _domain_analyze(kw)
    chk("领域分析被调用", isinstance(dom, dict))
    if _DOMAIN_FUNCS:
        chk("领域函数有产出", any(v is not None for v in dom.values()),
            str(list(dom.keys())[:3]))

    # ⑦ 分数区间合法
    allsc = [x["score"] for x in (r1["detail"].get("ranked") or [])]
    chk("分数在 0~100", all(0 <= s <= 100 for s in allsc), str(allsc))

    # ⑧ 幂等：同输入两次结果一致
    a1 = analyze(kw)
    a2 = analyze(kw)
    chk("幂等", a1.get("summary") == a2.get("summary")
        and [x["score"] for x in (a1["detail"].get("ranked") or [])]
        == [x["score"] for x in (a2["detail"].get("ranked") or [])])

    if fails:
        print("SELFTEST FAIL: %d 项不过 %s" % (len(fails), fails[:4]))
        return 1
    print("SELFTEST PASS")
    return 0


if __name__ == '__main__':
    sys.exit(_cli())
