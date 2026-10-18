# -*- coding: utf-8 -*-
"""场景叙事 · scene-narrative-pro

打磨型实现 · 类封装式（Domain / Analyzer / Report 三层对象）
契约：能力边界见 config.json；不提供专业诊断/法律/投资意见。
"""
import argparse
import io
import json
import os
import re
import sys

VERSION = "3.0.0-DIVERSIFIED_V3"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_FILE = os.path.join(BASE_DIR, "config.json")
CHECKPOINTS = [0, 1, 2, 3]


class Domain(object):
    """领域对象：承载规则与关键词"""

    def __init__(self, raw):
        self.raw = raw or {}
        self.rules = [r for r in (self.raw.get("rules") or [])
                      if (r.get("when") or "").strip()]
        self.keywords = [k for k in (self.raw.get("keywords") or [])
                         if (k.get("term") or "").strip()]
        self.boundary = self.raw.get("boundary") or ""

    @classmethod
    def load(cls, path=None):
        try:
            with io.open(path or CFG_FILE, encoding="utf-8") as f:
                return cls(json.load(f))
        except Exception:
            return cls({})

    def size(self):
        return len(self.rules) + len(self.keywords)


class Analyzer(object):
    """分析器：对文本做 打磨"""

    def __init__(self, domain):
        self.domain = domain

    def _clean(self, s):
        if not s:
            return ""
        s = s.replace("\u3000", " ")
        s = re.sub(r"\s+", " ", s).strip()
        return s.lower()

    def probe(self, text):
        t = self._clean(text)
        found = []
        for r in self.domain.rules:
            w = self._clean(r.get("when") or "")
            if w and w in t:
                found.append({"level": "rule", "key": w,
                              "action": r.get("then") or "", "w": 1.0})
        for k in self.domain.keywords:
            w = self._clean(k.get("term") or "")
            if w and w in t:
                found.append({"level": "kw", "key": w, "action": "", "w": 0.6})
        return found

    def weigh(self, items):
        seen, out = set(), []
        for it in items:
            if it["key"] in seen:
                continue
            seen.add(it["key"])
            it["final"] = round(it["w"] * (1.0 if len(it["key"]) > 3 else 0.8), 3)
            out.append(it)
        out.sort(key=lambda x: -x["final"])
        return out


class Report(object):
    """结果对象"""

    def __init__(self, state, cp, items, advice):
        self.state = state
        self.checkpoint = cp
        self.items = items
        self.advice = advice

    def as_dict(self):
        return {"state": self.state, "checkpoint": self.checkpoint,
                 "items": self.items, "advice": self.advice}


def build_report(domain, text):
    a = Analyzer(domain)
    if not (text or "").strip():
        return Report("empty", 0, [], ["请提供待打磨的内容"])
    items = a.weigh(a.probe(text))
    if not items:
        return Report("unknown", 1, [],
                      ["补充 标题钩子", "说明 结构层次"])
    return Report("ok", 3, items[:6],
                  ["复核 语言风格", "归档 信息密度"])


def _hook_score(text):
    """标题钩子强度：疑问/数字/对比/悬念"""
    s = 0
    if "？" in text or "?" in text:
        s += 2
    if any(c.isdigit() for c in text):
        s += 1
    if any(w in text for w in ("但是", "却", "反而", "对比")):
        s += 2
    if any(w in text for w in ("为什么", "如何", "怎么")):
        s += 1
    return min(10, s)


def _structure_depth(text):
    """结构层次：标题层级数"""
    levels = set()
    for ln in text.splitlines():
        m = ln.strip()
        if m.startswith("#"):
            levels.add(len(m) - len(m.lstrip("#")))
    return len(levels)


def _info_density(text):
    """信息密度：非空白字符占比"""
    if not text:
        return 0.0
    nz = len([c for c in text if not c.isspace()])
    return round(nz / len(text), 3)


def _cta_scan(text):
    """行动号召识别"""
    cta = ["点击", "关注", "评论", "私信", "购买", "领取", "报名", "下载"]
    return [c for c in cta if c in text]
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
    dom = Domain.load()
    fails = []
    if build_report(dom, "").state != "empty":
        fails.append("空输入状态错")
    if build_report(dom, "qqq 无关联内容 qqq").state != "unknown":
        fails.append("无关输入状态错")
    if dom.size() == 0:
        fails.append("领域对象为空（config 读取失败）")
    try:
        build_report(dom, "z" * 26000)
    except Exception as e:
        fails.append("超长崩溃 %s" % type(e).__name__)
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scene-narrative-pro")
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
    dom = Domain.load()
    rep = build_report(dom, text)
    if a.json:
        print(json.dumps(rep.as_dict(), ensure_ascii=False, indent=1))
    else:
        print("[打磨] %s ｜ 检查点 %s" % (rep.state, rep.checkpoint))
        for it in rep.items:
            print("  - %s (%.2f) %s" % (it["key"], it["final"], it["action"]))
        for ad in rep.advice:
            print("  → " + ad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
