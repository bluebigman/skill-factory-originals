#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-bilingual-pairing — 知识库 中英对照 配对核验

核验中英条目成对完整性与术语表一对多冲突

领域：知识库/信息整理（平台 54 分第 2 名）
能力：核验中英条目的成对完整性与术语表一对多冲突，定位缺侧条目并输出对齐清单
本实现完全离线，不发起网络调用、不读写用户隐私数据。
"""
import argparse, json, os, re, sys

VERSION = "1.0.0"


def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030", "latin-1")):
    """多编码容错读取（utf-8 → gbk → gb18030 → latin-1 → replace 兜底）"""
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except Exception:
            break
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_json(path, obj):
    """写结构化结果（目录不存在则创建）"""
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


TEXT_EXT = (".txt", ".md", ".json", ".yaml", ".yml", ".conf", ".cfg", ".ini",
            ".log", ".csv", ".tsv", ".py", ".js", ".ts", ".sh", ".env")


def iter_input_files(path):
    """输入路径展开：单文件原样返回；目录则递归收集常见文本文件（跳过依赖目录）"""
    if os.path.isfile(path):
        return [path]
    out = []
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in
                       (".git", "node_modules", "__pycache__", ".venv", "dist", "build")]
        for fn in sorted(filenames):
            if fn.endswith(TEXT_EXT):
                out.append(os.path.join(dirpath, fn))
    return out


def chunk_lines(lines, size=200):
    """按固定行数切块（大文件分批处理用，防内存峰值）"""
    size = max(1, int(size))
    for i in range(0, len(lines), size):
        yield lines[i:i + size]


def render_markdown_table(rows, headers):
    """把二维数据渲染成 Markdown 表格"""
    if not rows:
        return "（无数据）"
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def stable_id(text, length=12):
    """内容稳定短标识（用于去重与引用，非加密用途）"""
    import hashlib
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def rate(numerator, denominator, digits=2):
    """安全百分比计算（分母为 0 返回 0.0）"""
    if not denominator:
        return 0.0
    return round(numerator * 100.0 / denominator, digits)


def split_sections(text, min_len=40):
    """按 Markdown 标题切分章节为条目"""
    items, cur = [], {"title": "（前言）", "body": []}
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            if "".join(cur["body"]).strip():
                items.append(cur)
            cur = {"title": re.sub(r"^#+\s+", "", line).strip(), "body": []}
        else:
            cur["body"].append(line)
    if "".join(cur["body"]).strip():
        items.append(cur)
    return [{"title": i["title"], "text": "\n".join(i["body"]).strip()}
            for i in items if len("\n".join(i["body"]).strip()) >= min_len]


def build_index(items):
    """关键词倒排索引（中文 2-gram + 英文词）"""
    idx = {}
    for n, it in enumerate(items):
        blob = it["title"] + " " + it["text"]
        words = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", blob.lower()))
        cjk = re.findall(r"[\u4e00-\u9fff]", blob)
        words |= {"".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
        for w in words:
            idx.setdefault(w, set()).add(n)
    return {k: sorted(v) for k, v in sorted(idx.items())}


def search(index, items, query, topk=5):
    """按查询词检索条目（命中词数排序）"""
    qs = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query.lower()))
    cjk = re.findall(r"[\u4e00-\u9fff]", query)
    qs |= {"".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
    score = {}
    for w in qs:
        for n in index.get(w, []):
            score[n] = score.get(n, 0) + 1
    ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[:topk]
    return [{"no": n, "score": s, "title": items[n]["title"],
             "preview": items[n]["text"][:160]} for n, s in ranked]



KBP_PAIR_RX = re.compile(r"^\s*pair\s+(.*)$", re.I)
KBP_TERM_RX = re.compile(r"^\s*term\s+(.*)$", re.I)
KBP_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*(\S+)")
KBP_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
KBP_LATIN_RX = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")


def kbp_kv(text):
    out = {}
    for m in KBP_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def parse_bilingual_records(text):
    """解析双语配对声明

    语法：
        pair key=deploy-guide zh=部署手册 en=deployment-guide
        term zh=灰度 en=gray
    说明：中文/英文含空格时用下划线连接，脚本会自动还原为空格。
    """
    pairs, terms = [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        mp = KBP_PAIR_RX.match(line)
        if mp:
            kv = kbp_kv(mp.group(1))
            key = (kv.get("key") or "").strip()
            if not key:
                continue
            pairs.append({"key": key, "line": lineno,
                          "zh": kv.get("zh", "").replace("_", " ").strip(),
                          "en": kv.get("en", "").replace("_", " ").strip()})
            continue
        mt = KBP_TERM_RX.match(line)
        if mt:
            kv = kbp_kv(mt.group(1))
            zh = kv.get("zh", "").replace("_", " ").strip()
            en = kv.get("en", "").replace("_", " ").strip()
            if zh or en:
                terms.append({"zh": zh, "en": en, "line": lineno})
    return pairs, terms


def grade_bilingual(pairs, terms):
    """配对分级：缺侧 / 键重复 / 术语一一对应冲突"""
    issues_all, level_count = [], {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    seen_key, dup_key = {}, []
    per_pair = []
    for p in pairs:
        issues = []
        if p["key"] in seen_key:
            dup_key.append(p["key"])
            issues.append({"level": "HIGH", "code": "DUP_KEY", "msg": "配对键重复"})
        seen_key[p["key"]] = p
        if not p["zh"]:
            issues.append({"level": "HIGH", "code": "NO_ZH", "msg": "缺中文侧"})
        if not p["en"]:
            issues.append({"level": "HIGH", "code": "NO_EN", "msg": "缺英文侧"})
        if p["zh"] and p["en"] and not KBP_LATIN_RX.search(p["en"]):
            issues.append({"level": "MEDIUM", "code": "EN_NOT_LATIN",
                           "msg": "英文侧未含拉丁词，疑似占位"})
        for it in issues:
            level_count[it["level"]] += 1
        worst = min((KBP_LEVEL_ORDER[i["level"]] for i in issues), default=9)
        per_pair.append({"key": p["key"], "zh": p["zh"], "en": p["en"],
                         "level": ("OK" if worst == 9 else ["HIGH", "MEDIUM", "LOW"][worst]),
                         "issues": issues})
    zh_map, en_map, term_issues = {}, {}, []
    for t in terms:
        if t["zh"]:
            zh_map.setdefault(t["zh"], set()).add(t["en"])
        if t["en"]:
            en_map.setdefault(t["en"], set()).add(t["zh"])
    for zh, ens in zh_map.items():
        if len(ens) > 1:
            term_issues.append({"level": "MEDIUM", "code": "ZH_MULTI_EN",
                                "msg": "同一中文词对应多个英文写法：{}".format(zh)})
    for en, zhs in en_map.items():
        if len(zhs) > 1:
            term_issues.append({"level": "HIGH", "code": "EN_MULTI_ZH",
                                "msg": "同一英文写法对应多个中文词：{}".format(en)})
    for it in term_issues:
        level_count[it["level"]] += 1
    return {"per_pair": per_pair, "dup_key": dup_key, "term_issues": term_issues,
            "level_count": level_count, "term_total": len(terms),
            "zh_map": {k: sorted(v) for k, v in zh_map.items()},
            "en_map": {k: sorted(v) for k, v in en_map.items()}}


def render_bilingual_report(graded):
    rows = []
    for p in graded["per_pair"]:
        codes = ",".join(i["code"] for i in p["issues"]) or "-"
        msgs = "；".join(i["msg"] for i in p["issues"]) or "配对完整"
        rows.append([p["key"], p["zh"] or "（缺）", p["en"] or "（缺）", p["level"], codes, msgs])
    if not rows:
        rows = [["-", "-", "-", "-", "-", "未识别到配对声明"]]
    table = render_markdown_table(rows, ["配对键", "中文侧", "英文侧", "级别", "问题码", "说明"])
    trows = [[i["code"], i["msg"]] for i in graded["term_issues"]]
    if not trows:
        trows = [["-", "术语表无对应冲突"]]
    return table + "\n\n" + render_markdown_table(trows, ["术语问题码", "说明"])


def process(text):
    """V15：解析双语配对与术语表 → 缺侧/重复键/术语对应冲突分级 → 对齐清单"""
    pairs, terms = parse_bilingual_records(text)
    if not pairs and not terms:
        return {"ok": True, "variant": "V15", "pair_count": 0, "term_count": 0,
                "note": "未识别到双语声明（可用 pair key=... zh=... en=... 与 term zh=... en=... 声明；含空格时用下划线连接）",
                "level_count": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "report_table": render_markdown_table(
                    [["-", "-", "-", "-", "-", "未识别到配对声明"]],
                    ["配对键", "中文侧", "英文侧", "级别", "问题码", "说明"]),
                "next_action": "先补 pair/term 声明行，再复跑配对核验",
                "content_id": stable_id(text)}
    graded = grade_bilingual(pairs, terms)
    total = len(graded["per_pair"])
    ok_pairs = [p for p in graded["per_pair"] if p["level"] == "OK"]
    return {"ok": True, "variant": "V15",
            "pair_count": total, "term_count": graded["term_total"],
            "aligned_count": len(ok_pairs),
            "aligned_rate": rate(len(ok_pairs), total) if total else 0.0,
            "no_zh": [p["key"] for p in graded["per_pair"] if not p["zh"]],
            "no_en": [p["key"] for p in graded["per_pair"] if not p["en"]],
            "dup_keys": graded["dup_key"],
            "term_issues": graded["term_issues"],
            "level_count": graded["level_count"],
            "conclusion": "配对 {} 组；完整 {} 组（{}%）；缺中文 {} / 缺英文 {}；术语冲突 {} 项".format(
                total, len(ok_pairs), rate(len(ok_pairs), total) if total else 0.0,
                sum(1 for p in graded["per_pair"] if not p["zh"]),
                sum(1 for p in graded["per_pair"] if not p["en"]),
                len(graded["term_issues"])),
            "per_pair": graded["per_pair"],
            "report_table": render_bilingual_report(graded),
            "next_action": "先补齐缺侧条目，再统一术语表中一对多的写法（同一英文写法只保留一个中文对应）",
            "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="kb-bilingual-pairing", description="核验中英条目成对完整性与术语表一对多冲突")
    p.add_argument("--input", "-i", required=False, help="输入文件路径（文本/配置/源码）")
    p.add_argument("--out", "-o", default="out/result.json", help="结果输出路径（JSON）")
    p.add_argument("--dry-run", action="store_true", help="预览模式：只打印计划，不写盘")
    p.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.dry_run:
        print("[dry-run] 将读取:", args.input or "(stdin)")
        print("[dry-run] 将输出:", args.out)
        return 0
    if args.input and os.path.isfile(args.input):
        text = read_text_safe(args.input)
    else:
        text = sys.stdin.read()
    try:
        result = process(text)
    except Exception as exc:            # 异常降级：不抛出，转结构化错误
        result = {"ok": False, "error": str(exc)}
    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False)[:800])
        return 0
    write_json(args.out, result)
    print(json.dumps({"ok": result.get("ok", True), "out": args.out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
