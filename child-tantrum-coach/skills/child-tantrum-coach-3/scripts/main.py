# -*- coding: utf-8 -*-
"""幼儿情绪 · child-tantrum-coach

分级型实现 · 管道式（步骤串行，每步独立可测）
契约：能力边界见 config.json；不提供专业诊断/法律/投资意见。
"""
import argparse
import io
import json
import os
import re
import sys

VERSION = "3.0.0-DIVERSIFIED_V3"
CFG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
LADDERS = [['前置知识', '认知负荷'], ['练习设计'], ['反馈机制', '迁移应用']]


def load_cfg():
    with io.open(CFG, encoding="utf-8") as f:
        return json.load(f)


def step_normalize(text):
    """第 1 步：归一化（全半角、空白、大小写）"""
    if not text:
        return ""
    t = text.replace("\u3000", " ").strip()
    t = re.sub(r"\s+", " ", t)
    return t.lower()


def step_extract(text, cfg):
    """第 2 步：抽取候选（规则 when + 关键词）"""
    if not text:
        return []
    hits = []
    for r in cfg.get("rules") or []:
        w = (r.get("when") or "").strip()
        if w and w.lower() in text:
            hits.append(("rule", w, r.get("then") or ""))
    for k in cfg.get("keywords") or []:
        t = (k.get("term") or "").strip()
        if t and t.lower() in text:
            hits.append(("kw", t, ""))
    return hits


def step_score(hits, cfg):
    """第 3 步：打分（难度）—— 规则命中权重高于关键词"""
    scored = []
    for kind, term, then in hits:
        base = 0.7 if kind == "rule" else 0.45
        bonus = 0.15 if len(term) >= 4 else 0.0
        scored.append({"kind": kind, "term": term, "then": then,
                       "score": round(min(1.0, base + bonus), 3)})
    return sorted(scored, key=lambda x: (-x["score"], x["term"]))


def step_render(text, scored, cfg):
    """第 4 步：三态渲染"""
    if not text:
        return {"state": "empty", "ladder": 0, "items": [],
                "next": ["请提供待分析内容"]}
    if not scored:
        return {"state": "unknown", "ladder": 1, "items": [],
                "next": ["补充背景：前置知识", "明确目标：认知负荷"]}
    ladder = 3
    return {"state": "ok", "ladder": ladder,
            "items": scored[:6],
            "next": ["核对 练习设计", "记录 反馈机制"]}


def run(text, cfg=None):
    cfg = cfg or load_cfg()
    t = step_normalize(text)
    hits = step_extract(t, cfg)
    scored = step_score(hits, cfg)
    return step_render(t, scored, cfg)


def _prerequisite(text):
    """前置知识识别"""
    marks = ["基础", "前置", "预备", "先修", "入门"]
    return [m for m in marks if m in text]


def _cognitive_load(text):
    """认知负荷粗估：新概念数 / 句长"""
    concepts = len(set(w for w in ("概念", "定义", "原理", "公式", "模型") if w in text))
    avg_len = (len(text) / max(1, text.count("。"))) if text else 0
    return {"新概念": concepts, "均句长": round(avg_len, 1),
            "负荷": "高" if concepts >= 3 or avg_len > 60 else "低"}


def _practice_design(text):
    """练习设计"""
    if any(w in text for w in ("练习", "习题", "案例", "作业")):
        return "有练习"
    return "无练习（建议补）"


def _feedback_loop(text):
    """反馈机制"""
    if any(w in text for w in ("反馈", "批改", "答案", "解析")):
        return "有反馈"
    return "无反馈"


def _transfer(text):
    """迁移应用"""
    if any(w in text for w in ("应用", "迁移", "举一反三", "实战")):
        return "有迁移设计"
    return "无迁移设计"
def _safe_div(a, b, nd=4):
    """安全除法（防零除/类型错）"""
    try:
        b = float(b)
        if b == 0:
            return None
        return round(float(a) / b, nd)
    except (TypeError, ValueError):
        return None


def _clamp(v, lo=0.0, hi=1.0):
    """把值夹到区间内"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def _ratio_str(n, d):
    """比率百分比字符串（None 安全）"""
    r = _safe_div(n, d)
    return "—" if r is None else ("%.1f%%" % (r * 100))


def _split_sentences(text):
    """中英文分句（不用正则回溯，稳）"""
    out, buf = [], []
    for ch in text or "":
        buf.append(ch)
        if ch in "。！？!?;；\n":
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
    if buf:
        s = "".join(buf).strip()
        if s:
            out.append(s)
    return out


def _term_freq(text, min_len=2):
    """中文字符 n-gram 词频（2-3 字），用于近义覆盖判断"""
    from collections import Counter
    flat = "".join(ch for ch in (text or "") if "\u4e00" <= ch <= "\u9fff")
    cnt = Counter()
    for n in (2, 3):
        for i in range(max(0, len(flat) - n + 1)):
            w = flat[i:i + n]
            if len(w) == n:
                cnt[w] += 1
    return {w: c for w, c in cnt.items() if c >= 1}


def _overlap_ratio(a, b):
    """两段文本的 2-gram 重叠率（同义近义也能命中）"""
    fa, fb = _term_freq(a), _term_freq(b)
    if not fa or not fb:
        return 0.0
    inter = set(fa) & set(fb)
    return round(len(inter) / max(1, len(set(fa))), 4)


def _dedup_keep_order(items):
    """去重保序"""
    seen, out = set(), []
    for x in items:
        k = x if isinstance(x, (str, int, float)) else repr(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def _truncate(text, limit=8000):
    """超长截断并标注（不静默丢）"""
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "…[已截断，原长 %d]" % len(text)


def _encoding_chain(raw_bytes):
    """编码降级链：utf-8 → gbk → gb18030"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw_bytes.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw_bytes.decode("utf-8", "ignore"), "utf-8(ignore)"


def _coverage_report(text, dims):
    """维度覆盖报告（哪些讲到、哪些没讲）"""
    hit = [d for d in dims if d and d in (text or "")]
    miss = [d for d in dims if d and d not in (text or "")]
    return {"hit": hit, "miss": miss,
            "ratio": round(len(hit) / max(1, len(dims)), 3)}


def selftest():
    cfg = load_cfg()
    fails = []
    cases = [("", "empty"), ("完全无关的一句话", "unknown"),
             (" ".join(k.get("term", "") for k in (cfg.get("keywords") or [])[:2]), "ok")]
    for text, want in cases:
        got = run(text, cfg).get("state")
        if got != want:
            fails.append("输入 %r 期望 %s 实得 %s" % (text[:12], want, got))
    # 边界：超长输入不崩
    try:
        run("x" * 30000, cfg)
    except Exception as e:
        fails.append("超长输入崩溃：%s" % type(e).__name__)
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(prog="child-tantrum-coach")
    ap.add_argument("--text", default="")
    ap.add_argument("--input", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        f = selftest()
        print("SELFTEST " + ("FAIL " + "; ".join(f) if f else "PASS"))
        return 0 if not f else 1
    text = a.text or a.input
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    r = run(text)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("[分级] 状态=%s 层级=%s" % (r["state"], r["ladder"]))
        for it in r["items"]:
            print("  - %s（%.2f）%s" % (it["term"], it["score"], it["then"]))
        for n in r["next"]:
            print("  → " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
