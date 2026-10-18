# -*- coding: utf-8 -*-
"""文档可达性核查 · doc-accessibility-check

拆解型实现 · 表驱动式（一张策略表 + 通用解释器，新增能力只改表）
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
            return {"state": "unknown", "rows": [], "hint": "未匹配任何需求项"}
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


def _role_matrix(text):
    """角色×场景矩阵：识别需求涉及哪些用户角色"""
    roles = {"决策者": ("决定", "批准", "拍板"), "使用者": ("使用", "操作", "上手"),
             "维护者": ("维护", "配置", "部署"), "受益者": ("受益", "价值", "收益")}
    hit = {}
    for role, kws in roles.items():
        for k in kws:
            if k in text:
                hit.setdefault(role, []).append(k)
    return hit


def _pain_point_rank(text):
    """痛点强度排序：出现频次 × 情绪词权重"""
    weight = {"痛点": 3, "麻烦": 2, "困难": 2, "卡": 1, "慢": 1, "错": 1}
    score = 0
    for w, v in weight.items():
        score += text.count(w) * v
    return min(10, score)


def _alternative_scan(text):
    """替代方案识别：用户现在是怎么凑合解决的"""
    alts = ["手动", "excel", "表格", "脚本", "人工", "外包", "现成工具"]
    return [a for a in alts if a in text]
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
    ap = argparse.ArgumentParser(prog="doc-accessibility-check")
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
        print("[拆解] %s ｜ %s" % (r["state"], r.get("hint", "")))
        for row in r["rows"][:8]:
            print("  (%s) %s %s" % (row["stage"], row["term"], row["then"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
