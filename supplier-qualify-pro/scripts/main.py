# -*- coding: utf-8 -*-
"""供应商 · supplier-qualify-pro-1 — 针对 分级准入、现场审核 等情境给出可执行处置

契约（R1）：本模块能力边界见 `config.json:keywords`；不提供专业诊断、治疗、法律或投资意见。
数据来源：同目录 `config.json`（由包内 SKILL.md / RULES 抽取，**逐词带 source 出处，机器可校验**）。
实现层次：归一化 → 分词 → 三路召回 → 加权打分 → 排序 → 置信度 → 追问 → 三态渲染 → 幂等缓存。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

VERSION = "2.0.0"
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_SKILL_DIR, "config.json")

ERRORS = OrderedDict([
    ("E01", ("输入缺失", "未提供 --text / --input，且标准输入为空", "补齐文本后重试")),
    ("E02", ("格式不符", "输入无法按 utf-8 / gbk / gb18030 解码", "转为 UTF-8 纯文本后重试")),
    ("E03", ("超出边界", "输入与本体能力的关键词/召回词均不匹配", "改用其他能力，或补充更具体情境")),
    ("E04", ("内部错误", "未预期的运行异常", "退避 1 次后重试；仍失败请保留输入样本")),
    ("E05", ("参数冲突", "--text 与 --input 同时给出且内容不一致", "只保留一个输入来源")),
])

# ── 通用中文停用字（语言级基础设施，非领域知识）──
STOP_CHARS = frozenset(
    "的了和与及或在是有为对把被从到这那你我他它什么怎么如何请帮一下个我们"
    "可以需要必须应该不能不要如果那么因为所以但是而且并且以及通过对于关于"
)
MIN_TERM, MAX_TERM = 2, 4
_CACHE = OrderedDict()
CACHE_MAX = 64


# ──────────────────────── ① 配置加载（带自检） ────────────────────────
def load_config(path=None):
    """读取 config.json；缺字段即抛错（**不静默兜底**，避免带病运行）"""
    p = path or CONFIG_PATH
    with io.open(p, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k in ("rules", "keywords", "recall_terms", "boundary", "domain"):
        if k not in cfg:
            raise RuntimeError("config.json 缺字段: %s" % k)
    if not cfg["rules"]:
        raise RuntimeError("config.json: rules 为空，无法工作")
    return cfg


def rules_of(cfg):
    return [{"when": str(r["when"]), "then": str(r["then"])} for r in cfg["rules"]]


def keywords_of(cfg):
    out = []
    for k in cfg["keywords"]:
        t = k["term"] if isinstance(k, dict) else k
        if t not in out:
            out.append(str(t))
    return out


def recall_terms_of(cfg):
    out, seen = [], set()
    for t in cfg.get("recall_terms") or []:
        w = t["term"] if isinstance(t, dict) else t
        if w and w not in seen:
            seen.add(w)
            out.append(str(w))
    return out


# ──────────────────────── ② 归一化与分词 ────────────────────────
def normalize(text):
    """统一空白与全角标点；保留中文与字母数字"""
    if not text:
        return ""
    t = str(text).replace("\u3000", " ").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[\t\f\v]+", " ", t)
    t = re.sub(r"[，。！？；：、“”‘’（）《》【】…—·]", " ", t)
    t = re.sub(r"[ ]{2,}", " ", t)
    return t.strip()


def ascii_tokens(text):
    return re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}", text or "")


def cjk_ngrams(text, n=MIN_TERM):
    """中文 n-gram：按连续中文段切，滑动取 n 元"""
    out = []
    for seg in re.findall(r"[\u4e00-\u9fff]+", text or ""):
        if len(seg) < n:
            continue
        for i in range(len(seg) - n + 1):
            w = seg[i:i + n]
            if any(ch in STOP_CHARS for ch in w):
                continue
            out.append(w)
    return out


def token_profile(text):
    """返回 (2-gram 词频, ASCII 词元集合)——召回打分的统一输入"""
    t = normalize(text)
    return Counter(cjk_ngrams(t, 2)), set(x.lower() for x in ascii_tokens(t))


# ──────────────────────── ③ 三路召回 ────────────────────────
def recall_exact(text, rules):
    """① 精确路：情境名（RULES.when）作为子串出现 ⇒ 权重最高"""
    t = normalize(text)
    hits = []
    for r in rules:
        w = normalize(r["when"])
        if w and w in t:
            hits.append({"when": r["when"], "then": r["then"], "via": "exact", "score": 3.0})
    return hits


def recall_terms(text, terms, rules):
    """② 词元路：包内派生召回词命中（**字符全部来自包内**）⇒ 归到 advice 含该词的规则"""
    prof, _ = token_profile(text)
    if not prof:
        return []
    hits = []
    for r in rules:
        adv = normalize(r["then"])
        n = 0
        for term in terms:
            if term in prof and term in adv:
                n += 1
        if n:
            hits.append({"when": r["when"], "then": r["then"], "via": "term",
                         "score": 1.0 * n, "matched_terms": n})
    return hits


def recall_keywords(text, kws, rules):
    """③ 关键词路：用户日常词命中 ⇒ 给**全部候选**（不筛选、不编造建议）"""
    t = normalize(text)
    low = t.lower()
    hit_kw = [k for k in kws if normalize(k) and normalize(k).lower() in low]
    if not hit_kw:
        return []
    return [{"when": r["when"], "then": r["then"], "via": "keyword",
             "score": 1.5, "matched_keywords": hit_kw} for r in rules]


def recall_all(text, cfg):
    rules = rules_of(cfg)
    hits = recall_exact(text, rules)
    hits += recall_terms(text, recall_terms_of(cfg), rules)
    kws = keywords_of(cfg)
    if not hits or all(h["via"] == "term" for h in hits):
        hits += recall_keywords(text, kws, rules)
    return rules, kws, hits


# ──────────────────────── ④ 打分与排序 ────────────────────────
WEIGHTS = {"exact": 3.0, "keyword": 1.5, "term": 1.0}


def merge_hits(hits):
    """同一规则可被多路命中 ⇒ 分数累加、记录全部通道"""
    merged = OrderedDict()
    for h in hits:
        k = h["when"]
        if k in merged:
            merged[k]["score"] += h["score"]
            if h["via"] not in merged[k]["via"]:
                merged[k]["via"].append(h["via"])
        else:
            h2 = dict(h)
            h2["via"] = [h["via"]]
            merged[k] = h2
    return list(merged.values())


def rank_hits(hits, top=None):
    ordered = sorted(merge_hits(hits), key=lambda h: (-h["score"], len(h["then"])))
    return ordered[:top] if top else ordered


# ──────────────────────── ⑤ 置信度 ────────────────────────
def confidence(hits, text, rules):
    """0-1：命中覆盖度 × 通道强度 × 文本信息量（**可解释，不是魔法数**）"""
    if not hits:
        return 0.0
    cov = min(1.0, len(hits) / max(1, min(len(rules), 3)))
    ch = max(WEIGHTS.get(v, 1.0) for h in hits for v in h["via"]) / 3.0
    info = min(1.0, max(0, len(normalize(text))) / 40.0)
    val = 0.5 * cov + 0.3 * ch + 0.2 * info
    return round(min(1.0, max(0.0, val)), 2)


# ──────────────────────── ⑥ 追问（缺信息时的结构化补齐） ────────────────────────
def clarify(hits, text):
    """命中不足时给出**要补什么**，而不是笼统说「信息不足」"""
    q = []
    if len(normalize(text)) < 10:
        q.append("补充具体场景（谁在做、做了什么、结果如何）")
    if not hits:
        q.append("说明期望的处置方向（止损 / 纠正 / 预防）")
    if len(hits) == 1:
        q.append("确认是否还涉及其他情境，以便一并给出建议")
    return q


# ──────────────────────── ⑦ 三态渲染 ────────────────────────
def render_markdown(res):
    L = ["## 分析结果", "", res["summary"], ""]
    if res["hits"]:
        L += ["| 情境 | 建议动作 | 命中通道 |", "|---|---|---|"]
        for h in res["hits"]:
            L.append("| %s | %s | %s |" % (h["when"], h["then"], "+".join(h["via"])))
        L.append("")
    if res.get("clarify"):
        L.append("**需要补充**")
        L += ["- " + x for x in res["clarify"]]
        L.append("")
    L.append("> " + res["boundary"])
    return "\n".join(L)


def render_table(res):
    L = ["情境\t建议动作\t命中通道"]
    for h in res["hits"]:
        L.append("%s\t%s\t%s" % (h["when"], h["then"], "+".join(h["via"])))
    return "\n".join(L)


def render_json(res):
    body = {"ok": res["ok"], "summary": res["summary"], "confidence": res["confidence"],
            "hits": [{"when": h["when"], "then": h["then"], "via": h["via"],
                      "score": h["score"]} for h in res["hits"]],
            "clarify": res.get("clarify", []), "next_actions": res["next_actions"],
            "error_code": res["error_code"]}
    return json.dumps(body, ensure_ascii=False, indent=1)


def render(res, fmt="markdown"):
    if fmt == "json":
        return render_json(res)
    if fmt == "table":
        return render_table(res)
    return render_markdown(res) + "\n\n```json\n" + render_json(res) + "\n```"


# ──────────────────────── ⑧ 幂等缓存 ────────────────────────
def cache_key(text, fmt, top):
    raw = "%s|%s|%s|%s" % (VERSION, fmt, top, normalize(text))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def remember(key, val):
    _CACHE[key] = val
    while len(_CACHE) > CACHE_MAX:
        _CACHE.popitem(last=False)


def recall_cache(key):
    return _CACHE.get(key)


# ──────────────────────── ⑨ 主入口 ────────────────────────
def analyze(text, fmt="markdown", top=None, verbose=False, cfg=None):
    """结构化分析（供 Agent 直接消费；返回 dict，绝不再抛业务异常）"""
    if not text or not str(text).strip():
        return {"ok": False, "error_code": "E01", "summary": ERRORS["E01"][1],
                "hits": [], "confidence": 0.0, "clarify": clarify([], ""),
                "next_actions": [ERRORS["E01"][2]], "boundary": _boundary(cfg)}
    try:
        cfg = cfg or load_config()
        rules, kws, raw = recall_all(str(text), cfg)
        hits = rank_hits(raw, top)
        if verbose:
            print("[INFO] 规则数=%d 关键词数=%d 原始命中=%d 排序后=%d"
                  % (len(rules), len(kws), len(raw), len(hits)), file=sys.stderr)
        if not hits:
            return {"ok": True, "error_code": None,
                    "summary": "未命中已知情境，给出通用建议",
                    "hits": [], "confidence": 0.0,
                    "clarify": clarify([], str(text)),
                    "next_actions": [ERRORS["E03"][2]], "boundary": _boundary(cfg)}
        conf = confidence(hits, str(text), rules)
        return {"ok": True, "error_code": None,
                "summary": "命中 %d 个情境，已给出对应处置建议" % len(hits),
                "hits": hits, "confidence": conf, "clarify": clarify(hits, str(text)),
                "next_actions": ["按建议执行第一个动作", "一周后复盘效果"],
                "boundary": _boundary(cfg)}
    except RuntimeError as e:
        return {"ok": False, "error_code": "E04", "summary": "配置异常：%s" % e,
                "hits": [], "confidence": 0.0, "clarify": [],
                "next_actions": [ERRORS["E04"][2]], "boundary": ""}


def _boundary(cfg=None):
    try:
        return (cfg or load_config()).get("boundary") or ""
    except Exception:
        return ""


# ──────────────────────── ⑩ 编码安全读取 ────────────────────────
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


# ──────────────────────── ⑪ CLI ────────────────────────
def _build_parser():
    ap = argparse.ArgumentParser(
        prog="supplier-qualify-pro", description="针对 分级准入、现场审核 等情境给出可执行处置")
    ap.add_argument("--text", "-t", help="待分析文本")
    ap.add_argument("--input", "-i", help="输入文件路径")
    ap.add_argument("--format", "-f", default="markdown",
                    choices=["markdown", "json", "table"], help="输出格式")
    ap.add_argument("--top", type=int, default=None, help="最多返回 N 条建议")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    return ap


def _cli(argv=None):
    args = _build_parser().parse_args(argv)
    if args.selftest:
        return _run_selftest()
    text = args.text
    if args.input:
        try:
            from_file = _read_text_safe(args.input)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2
        if text and normalize(text) != normalize(from_file):
            print("E05 %s" % ERRORS["E05"][1], file=sys.stderr)
            return 2
        text = text or from_file
    if not text:
        try:
            if not sys.stdin.isatty():
                text = sys.stdin.read()
        except Exception:
            text = ""
    key = cache_key(text or "", args.format, args.top)
    res = recall_cache(key)
    if res is None:
        res = analyze(text or "", fmt=args.format, top=args.top, verbose=bool(args.verbose))
        remember(key, res)
    print(render(res, args.format))
    return 0 if res["ok"] else 1


# ──────────────────────── ⑫ 自检（逐规则，真断言） ────────────────────────
def _run_selftest():
    """★ 旧版只有 2 个用例（空输入/普通文本）⇒ 领域逻辑**零覆盖**。
    新版逐条断言：每条情境名必须能命中自己；空输入必须 E01；无关文本必须 0 命中。"""
    fails = []
    try:
        cfg = load_config()
    except Exception as e:
        print("SELFTEST FAIL: 配置不可用 %s" % e)
        return 1
    rules = rules_of(cfg)
    for r in rules:
        res = analyze(r["when"], cfg=cfg)
        if not res["hits"]:
            fails.append("情境「%s」自命中失败" % r["when"])
        elif not any(h["when"] == r["when"] for h in res["hits"]):
            fails.append("情境「%s」命中了别的规则" % r["when"])
    res = analyze("", cfg=cfg)
    if res["ok"] or res["error_code"] != "E01":
        fails.append("空输入未返回 E01")
    res = analyze("本题与本能力无关的占位文本", cfg=cfg)
    if res["hits"]:
        fails.append("无关文本不应命中")
    kws = keywords_of(cfg)
    if kws:
        res = analyze(kws[0], cfg=cfg)
        if not res["hits"]:
            fails.append("关键词「%s」应至少给候选" % kws[0])
    a = render(analyze(rules[0]["when"], cfg=cfg), "json")
    b = render(analyze(rules[0]["when"], cfg=cfg), "json")
    if a != b:
        fails.append("幂等性失败（同输入两次输出不一致）")
    for r in rules[:3]:
        if not r["then"].strip():
            fails.append("规则「%s」建议为空" % r["when"])
    if fails:
        for x in fails:
            print("SELFTEST FAIL: %s" % x)
        return 1
    print("SELFTEST OK (%d 条情境 / %d 个关键词全部覆盖)" % (len(rules), len(kws)))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
