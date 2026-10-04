#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc-readability-grader — 文档可读性 句长 段落评分

按句长与段长给文档逐段可读性打分、输出评级与改写优先级短板

领域：知识库/信息整理（平台 54 分第 2 名）
能力：按句长/长句率/段长/缩写密度给文档逐段可读性打分，输出评级与改写优先级短板
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



RD_SENT_SPLIT_RX = re.compile(r"[。！？!?；;]+")
RD_HEADING_RX = re.compile(r"^(#{1,6})\s+(.*)$")
RD_ACRONYM_RX = re.compile(r"\b[A-Z][A-Z0-9]{1,7}\b")
RD_LONG_SENT = 60
RD_LONG_PARA = 400


def parse_paragraphs(text):
    """按空行切段，标注标题行与正文段"""
    paras, buf, start = [], [], 0
    lines = text.splitlines()
    for idx, raw in enumerate(lines, 1):
        if raw.strip():
            if not buf:
                start = idx
            buf.append(raw.strip())
            continue
        if buf:
            paras.append({"line": start, "text": "\n".join(buf), "kind": "body"})
            buf = []
    if buf:
        paras.append({"line": start, "text": "\n".join(buf), "kind": "body"})
    for p in paras:
        p["kind"] = "heading" if RD_HEADING_RX.match(p["text"].splitlines()[0]) else "body"
    return paras


def score_paragraph(p):
    """单段可读性打分（100 分制，扣分项可解释）"""
    text = p["text"]
    plain = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    plain = re.sub(r"[*_`>\-|]+", " ", plain)
    chars = len(re.sub(r"\s", "", plain))
    sentences = [s for s in RD_SENT_SPLIT_RX.split(plain) if s.strip()]
    n_sent = max(1, len(sentences))
    avg_sent = round(chars / n_sent, 1) if chars else 0.0
    long_sent = len([s for s in sentences if len(re.sub(r"\s", "", s)) > RD_LONG_SENT])
    acronyms = len(RD_ACRONYM_RX.findall(plain))
    penalties = []
    if avg_sent > 45:
        penalties.append(("平均句长 %.1f 字，超过 45 字" % avg_sent, 18))
    elif avg_sent > 35:
        penalties.append(("平均句长 %.1f 字偏长" % avg_sent, 8))
    if long_sent:
        penalties.append(("超长句 %d 句，须断句" % long_sent, min(20, long_sent * 5)))
    if chars > RD_LONG_PARA:
        penalties.append(("整段 %d 字过长，须拆分为多段" % chars, 12))
    if chars and acronyms * 18 > chars:
        penalties.append(("缩写密度偏高（%d 处缩写 / %d 字）" % (acronyms, chars), 10))
    score = 100 - sum(p for _, p in penalties)
    return {"line": p["line"], "chars": chars, "sentences": n_sent,
            "avg_sentence_len": avg_sent, "long_sentence_count": long_sent,
            "acronym_count": acronyms, "score": max(0, score),
            "penalties": [{"reason": r, "deduct": d} for r, d in penalties],
            "kind": p["kind"]}


def readability_grade(avg_score):
    if avg_score >= 85:
        return "优", "结构清晰、句长适中，可直接入库"
    if avg_score >= 70:
        return "良", "存在少量长句/长段，建议按扣分项局部改写"
    return "待改", "长句长段密集，须先拆分再入库，否则检索命中后阅读成本过高"


def process(text):
    """V11：段落切分 → 逐段可读性打分 → 短板定位与改写优先级"""
    paras = parse_paragraphs(text)
    scored = [score_paragraph(p) for p in paras]
    body = [s for s in scored if s["kind"] != "heading"]
    total = len(body)
    avg = round(sum(s["score"] for s in body) / total, 1) if total else 0.0
    grade, advice = readability_grade(avg)
    hotspots = sorted(body, key=lambda s: (s["score"], -s["chars"]))[:5]
    chars_total = sum(s["chars"] for s in body)
    if total:
        conclusion = "正文段 {0} 段 / {1} 字，平均可读性 {2} 分（{3}）——{4}".format(
            total, chars_total, avg, grade, advice)
    else:
        conclusion = "未识别到正文段落（输入需为 Markdown 或纯文本，段间以空行分隔）"
    return {"ok": True, "variant": "V11", "conclusion": conclusion,
            "paragraph_count": total, "char_count": chars_total,
            "avg_score": avg, "grade": grade, "advice": advice,
            "hotspots": [{"line": h["line"], "score": h["score"], "chars": h["chars"],
                          "reasons": [p["reason"] for p in h["penalties"]]}
                         for h in hotspots if h["penalties"]],
            "paragraph_scores": scored}



def build_parser():
    p = argparse.ArgumentParser(prog="doc-readability-grader", description="按句长与段长给文档逐段可读性打分、输出评级与改写优先级短板")
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
