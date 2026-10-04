#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc-section-indexer — 文档章节 切分索引 检索

把长文档切成结构化章节并建立可检索索引

领域：知识库/信息整理（平台 54 分第 2 名）
能力：批量读取文档、切分为结构化条目、建立关键词索引、支持按词检索与摘要输出
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



# ─────────────── 文档章节索引（真实领域实现）───────────────
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#{0,}\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{1,}")
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "you", "your", "can", "will", "have", "has", "had", "not", "but", "all",
    "any", "use", "using", "used", "how", "what", "when", "into", "out",
}


def mark_code_regions(lines):
    """标记每行是否处于围栏代码块内（代码块内的 # 不是标题）"""
    marked, in_fence, token = [], False, ""
    for raw in lines:
        m = FENCE_RE.match(raw)
        if m:
            tok = m.group(1)
            if not in_fence:
                in_fence, token = True, tok
            elif tok == token:
                in_fence, token = False, ""
            marked.append((raw, True))
            continue
        marked.append((raw, in_fence))
    return marked


def parse_sections(text, min_chars=15):
    """按标题层级切分章节，补全 path（父级 > 子级），记录行号区间

    与"按长度硬切"的区别：保留文档原有语义边界，输出可直接引用的章节树。
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    marked = mark_code_regions(lines)
    heads = []
    for n, (raw, in_code) in enumerate(marked):
        if in_code:
            continue
        m = HEADING_RE.match(raw)
        if m and m.group(2).strip():
            heads.append({"line": n, "level": len(m.group(1)), "title": m.group(2).strip()})

    if not heads:
        body = text.strip()
        if len(body) < min_chars:
            return []
        return [{"no": 0, "level": 1, "title": "（全文）", "path": "（全文）",
                 "start_line": 0, "end_line": len(lines), "text": body}]

    sections = []
    for i, h in enumerate(heads):
        end = heads[i + 1]["line"] if i + 1 < len(heads) else len(lines)
        if i + 1 < len(heads):
            # 同级或更高级标题才算真正的边界；把下级标题内容并入当前章节正文
            j = i + 1
            while j < len(heads) and heads[j]["level"] > h["level"]:
                j += 1
            end = heads[j]["line"] if j < len(heads) else len(lines)
        body = "\n".join(lines[h["line"] + 1:end]).strip()
        sections.append({"no": len(sections), "level": h["level"], "title": h["title"],
                         "start_line": h["line"] + 1, "end_line": end, "body": body})

    stack = []
    for s in sections:
        while stack and stack[-1]["level"] >= s["level"]:
            stack.pop()
        stack.append(s)
        s["path"] = " > ".join(x["title"] for x in stack)

    out = []
    for s in sections:
        if len(s["body"]) < min_chars and not s["body"]:
            continue
        out.append({"no": len(out), "level": s["level"], "title": s["title"],
                    "path": s["path"], "start_line": s["start_line"],
                    "end_line": s["end_line"], "text": s["body"]})
    return out


def tokenize(text):
    """中英混合分词：英文词根 + 中文 2-gram（无需词典，离线可用）"""
    low = text.lower()
    terms = {w for w in WORD_RE.findall(low) if w not in STOPWORDS and len(w) >= 2}
    chars = CJK_RE.findall(low)
    terms |= {"".join(chars[i:i + 2]) for i in range(max(0, len(chars) - 1))}
    return terms


def build_index(sections):
    """倒排索引：term → 出现的章节编号集合"""
    idx = {}
    for s in sections:
        for t in tokenize(s["title"] + " " + s["text"]):
            idx.setdefault(t, set()).add(s["no"])
    return {k: sorted(v) for k, v in idx.items()}


def score_sections(sections, index, query, topk=5):
    """检索打分：命中词数 × (1 + 标题权重) ÷ √长度（长文不天然占优）"""
    qterms = tokenize(query)
    hits = {}
    for t in qterms:
        for n in index.get(t, []):
            hits[n] = hits.get(n, 0) + 1.0
    ranked = []
    for n, base in hits.items():
        s = sections[n]
        title_bonus = 0.6 if qterms & tokenize(s["title"]) else 0.0
        length_norm = max(1.0, (len(s["text"]) ** 0.5) / 6.0)
        ranked.append({"no": n, "score": round((base + title_bonus) / length_norm, 4),
                       "title": s["title"], "path": s["path"],
                       "matched_terms": sorted(qterms & tokenize(s["title"] + " " + s["text"]))[:8],
                       "preview": re.sub(r"\s+", " ", s["text"])[:140]})
    ranked.sort(key=lambda x: (-x["score"], x["no"]))
    return ranked[:topk]


def analyze_structure(sections):
    """结构体检：层级分布 / 空章节 / 跳级 / 超长章节"""
    issues = []
    levels = [s["level"] for s in sections]
    dist = {}
    for lv in levels:
        dist[str(lv)] = dist.get(str(lv), 0) + 1
    for i, s in enumerate(sections):
        if not s["text"].strip():
            issues.append({"level": "LOW", "msg": f'章节「{s["title"]}」正文为空'})
        elif len(s["text"]) > 4000:
            issues.append({"level": "LOW",
                           "msg": f'章节「{s["title"]}」正文 {len(s["text"])} 字，建议拆分'})
        if i and s["level"] - sections[i - 1]["level"] > 1:
            issues.append({"level": "MEDIUM",
                           "msg": f'标题层级跳级：第 {s["start_line"]} 行 从 H{sections[i - 1]["level"]} 跳到 H{s["level"]}'})
    return {"level_distribution": dist, "issues": issues,
            "max_level": max(levels) if levels else 0}


def render_toc(sections):
    """渲染目录（按层级缩进）"""
    if not sections:
        return "（无章节）"
    return "\n".join(f'{"  " * (s["level"] - 1)}- {s["title"]}（L{s["start_line"]}-{s["end_line"]}）'
                     for s in sections)


def render_section_table(sections, limit=40):
    """章节清单表格：层级 / 标题 / 字数 / 行号区间"""
    rows = [[s["level"], s["title"][:40], len(s["text"]), f'{s["start_line"]}-{s["end_line"]}']
            for s in sections[:limit]]
    return render_markdown_table(rows, ["层级", "标题", "字数", "行号"])


def process(text):
    """主处理流程：切分章节 → 结构体检 → 建索引 → 输出可检索知识单元"""
    if not text or not text.strip():
        return {"ok": False, "error": "输入为空，无法切分章节"}
    sections = parse_sections(text)
    if not sections:
        return {"ok": False, "error": "未解析出任何章节（内容过短或无正文）"}
    index = build_index(sections)
    structure = analyze_structure(sections)
    total_chars = sum(len(s["text"]) for s in sections)
    top_terms = sorted(index.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:20]
    return {
        "ok": True,
        "conclusion": f'共切分 {len(sections)} 个章节，建立 {len(index)} 个索引词，结构问题 {len(structure["issues"])} 项',
        "section_count": len(sections),
        "total_chars": total_chars,
        "avg_section_chars": round(total_chars / len(sections), 1),
        "index_terms": len(index),
        "level_distribution": structure["level_distribution"],
        "issues": structure["issues"][:20],
        "toc_md": render_toc(sections),
        "section_table_md": render_section_table(sections),
        "top_terms": [{"term": t, "section_count": len(v)} for t, v in top_terms],
        "sections": [{"no": s["no"], "level": s["level"], "title": s["title"],
                      "path": s["path"], "chars": len(s["text"]),
                      "lines": f'{s["start_line"]}-{s["end_line"]}',
                      "preview": re.sub(r"\s+", " ", s["text"])[:120]} for s in sections[:200]],
        "next_action": "按 issues 修订标题层级后重新索引" if structure["issues"] else "结构清晰，可直接按 TOC 引用章节",
        "content_id": stable_id(text),
    }


def build_parser():
    p = argparse.ArgumentParser(prog="doc-section-indexer", description="把长文档切成结构化章节并建立可检索索引")
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
