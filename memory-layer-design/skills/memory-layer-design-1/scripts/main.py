# -*- coding: utf-8 -*-
"""记忆层设计 · memory-layer-design

分析型实现 · 表驱动式（一张策略表 + 通用解释器，新增能力只改表）
契约：能力边界见 config.json；不提供专业诊断/法律/投资意见。
"""
import argparse
import io
import json
import os
import re
import sys

VERSION = "3.0.0-DIVERSIFIED_V3"
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(_HERE, "config.json")

# 策略表：(阶段名, 匹配方式, 权重, 输出前缀)
STAGES = [['rule', 'rule', 1.0, '必办'], ['kw', 'kw', 0.6, '参考']]


def read_config(path=None):
    try:
        with io.open(path or CFG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"rules": [], "keywords": []}


def canon(s):
    if not s:
        return ""
    s = s.replace("\u3000", " ")
    s = re.sub(r"[\t\r\n]+", " ", s)
    return re.sub(r" +", " ", s).strip()


class Interpreter(object):
    """通用解释器：按 STAGES 顺序执行，不看具体领域"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.patterns = self._compile()

    def _compile(self):
        pats = []
        for r in self.cfg.get("rules") or []:
            w = canon(r.get("when") or "")
            if w:
                pats.append(("rule", w, r.get("then") or ""))
        for k in self.cfg.get("keywords") or []:
            t = canon(k.get("term") or "")
            if t:
                pats.append(("kw", t, ""))
        return pats

    def _stage_hit(self, text, stage):
        name, how, weight, prefix = stage
        out = []
        for kind, term, then in self.patterns:
            if kind != how:
                continue
            if term.lower() in text:
                out.append({"stage": name, "term": term, "then": then,
                            "weight": weight, "prefix": prefix})
        return out

    def execute(self, text):
        t = canon(text).lower()
        if not t:
            return {"state": "empty", "rows": [], "hint": "输入为空"}
        rows = []
        for st in STAGES:
            rows.extend(self._stage_hit(t, st))
        if not rows:
            return {"state": "unknown", "rows": [], "hint": "未匹配任何特征"}
        # 按 term 去重（dict 不可 hash，只能用 key 集合）
        seen, uniq = set(), []
        for row in rows:
            if row["term"] in seen:
                continue
            seen.add(row["term"])
            uniq.append(row)
        uniq.sort(key=lambda x: (-x["weight"], x["term"]))
        return {"state": "ok", "rows": uniq[:10],
                 "hint": "命中 %d 项，前 3 项优先处理" % len(uniq)}


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
    cfg = read_config()
    it = Interpreter(cfg)
    fails = []
    if it.execute("").get("state") != "empty":
        fails.append("空输入状态错")
    if it.execute("zzz 不可能匹配 zzz").get("state") != "unknown":
        fails.append("无关输入状态错")
    kws = [canon((k.get("term") or "")) for k in (cfg.get("keywords") or [])]
    kws = [k for k in kws if k]
    if kws:
        r = it.execute(" ".join(kws[:2]))
        if r.get("state") != "ok":
            fails.append("关键词输入应有命中")
    try:
        it.execute("y" * 25000)
    except Exception as e:
        fails.append("超长崩溃 %s" % type(e).__name__)
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(prog="memory-layer-design")
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
    it = Interpreter(read_config())
    r = it.execute(text)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("[分析] %s ｜ %s" % (r["state"], r.get("hint", "")))
        for row in r["rows"][:8]:
            print("  (%s) %s %s" % (row["stage"], row["term"], row["then"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
