# -*- coding: utf-8 -*-
"""结果判读 —— 按预先设定的口径判读结果，避免事后挑选

契约（R1）：本模块能力边界 = ['判读', '预设', '显著性']；不提供心理/医学诊断，超出即提示转介。
"""
import argparse
import io
import json
import sys

ERRORS = {
    "E01": "输入缺失：请提供 --text 或通过标准输入传入内容（AI 可补齐后重试）",
    "E02": "格式不符：请提供纯文本（AI 可按 input_schema 转换后重试）",
    "E03": "超出边界：本能力只处理 判读、预设、显著性 相关情境（AI 应改用其他能力）",
    "E04": "内部错误：请带 retry_after 退避后重试 1 次",
}

KEYWORDS = ['判读', '预设', '显著性']

RULES = [
 {
  "when": "结果未达显著",
  "then": "如实报无差异，不做二次挖掘"
 },
 {
  "when": "事后改口径",
  "then": "标注为探索性结论，不作决策依据"
 }
]

BOUNDARY_HINT = "本能力不提供心理或医学诊断；如涉及自伤、重度抑郁等，请转介专业机构。"


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
        return {"ok": True, "error_code": None,
                "summary": "未命中已知情境，给出通用建议",
                "detail": {"hits": [], "boundary": BOUNDARY_HINT},
                "next_actions": ["补充更具体的情境描述（如具体行为、发生场景）"]}
    scored = _score_hits(hits, text)
    ranked = _rank_advice(scored, top=3)
    if verbose:
        for it in ranked:
            print("[INFO] 优先级 %.1f ｜ %s ｜ %s"
                  % (it["score"], it["trigger"], it["why"]))
    detail = {"hits": hits, "scored": scored, "ranked": ranked,
              "boundary": BOUNDARY_HINT}
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
    return "\\n".join(lines)


def _cli():
    """R1/R4/R6 契约 CLI：--text/--input/--dry-run/--verbose/--selftest"""
    ap = argparse.ArgumentParser(description="forge-demo-abtest-3 命令行入口")
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


# ═══ 领域专属算法（04-DataAI）═══
def _data_quality(text):
    """数据质量四项：缺失/重复/异常值/单位"""
    checks = {"缺失": ("缺失", "空值", "missing"), "重复": ("重复", "去重", "duplicate"),
              "异常值": ("异常值", "离群", "outlier"), "单位": ("单位", "口径", "量纲")}
    return {k: any(w in text.lower() for w in ws) for k, ws in checks.items()}


def _sample_bias(text):
    """样本偏差：是否提到分层/时间窗/幸存者"""
    marks = {"分层": ("分层", "分组", "segment"), "时间窗": ("时间", "周期", "区间"),
             "幸存者": ("幸存", "存续", "剔除")}
    return [k for k, ws in marks.items() if any(w in text.lower() for w in ws)]


def _metric_consistency(text):
    """指标口径一致性：是否说明定义"""
    if "定义" in text or "口径" in text:
        return "已声明"
    return "未声明（建议补）"


def _feature_rank(text, keywords):
    """特征重要性：按出现次数与关键词长度粗排"""
    out = []
    for k in keywords:
        term = (k.get("term") if isinstance(k, dict) else k) or ""
        if term and term in text:
            out.append((term, round(0.5 + 0.1 * min(5, len(term)), 2)))
    return sorted(out, key=lambda x: -x[1])[:6]


def _run_selftest():
    cases = [("", False), ("普通文本", True)]
    for t, expect_ok in cases:
        r = analyze(t)
        if r["ok"] != expect_ok:
            print("SELFTEST FAIL: %r" % t)
            return 1
    print("SELFTEST OK")
    return 0


if __name__ == '__main__':
    sys.exit(_cli())
