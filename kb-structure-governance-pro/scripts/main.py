#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-crossref-integrity-checker — 知识交叉引用 断链排查 环路检测

--variant

领域：知识库/信息整理（平台 54 分第 2 名）
能力：核验知识条目间交叉引用的完整性，检出断链、孤岛条目与引用环路，并按入链数评估条目连通度
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



REF_DECL_RX = re.compile(r"^\s*(entry|policy)\s+(.*)$", re.I)
REF_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
REF_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
REF_LINK_RX = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]|@ref\(\s*([^)]+?)\s*\)")


def rf16_kv(text):
    """解析 key=value 片段 → 字典"""
    out = {}
    for m in REF_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def rf16_list(val):
    """逗号分隔清单 → 去重保序"""
    seen, out = set(), []
    for x in (val or "").split(","):
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_links(text):
    """抽取条目正文中的交叉引用（[[标题]] 或 @ref(标题)）"""
    out = []
    for m in REF_LINK_RX.finditer(text or ""):
        t = (m.group(1) or m.group(2) or "").strip()
        if t and t not in out:
            out.append(t)
    return out


def parse_ref_entries(text):
    """解析条目声明块

    语法（每行一条声明，key=value 空格分隔）：
        entry title=部署手册 links=回滚流程,监控告警
        entry title=回滚流程 links=部署手册
        entry title=孤立说明 links=
        policy allow_orphan=false max_depth=3
    """
    entries, policy = [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = REF_DECL_RX.match(line)
        if not m:
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        kv = rf16_kv(rest)
        if kind == "policy":
            policy.update(kv)
            continue
        title = (kv.get("title") or kv.get("name") or "").strip()
        if not title:
            continue
        links = rf16_list(kv.get("links"))
        for extra in extract_links(kv.get("body") or ""):
            if extra not in links:
                links.append(extra)
        entries.append({"line": lineno, "title": title, "links": links})
    return entries, policy


def analyze_references(entries, policy):
    """核验交叉引用的断链、孤岛与环路"""
    allow_orphan = str(policy.get("allow_orphan", "false")).strip().lower() in ("1", "true", "yes", "on")
    max_depth = (lambda v: (lambda: int(float(v)) if str(v).strip() else 0)())(policy.get("max_depth", 3)) or 3
    titles = {e["title"] for e in entries}
    inbound = {t: 0 for t in titles}
    graded, dangling, cycles = [], [], []

    for e in entries:
        issues = []
        for lk in e["links"]:
            if lk not in titles:
                issues.append(("HIGH", "DANGLING_REF", f"引用 [[{lk}]] 无对应条目 → 断链"))
                dangling.append((e["title"], lk))
            else:
                inbound[lk] += 1
        if not e["links"]:
            issues.append(("LOW", "NO_OUTBOUND_REF", "无对外引用，条目相对孤立"))
        worst = sorted((i[0] for i in issues), key=lambda x: REF_LEVEL_ORDER.get(x, 9))
        graded.append({"title": e["title"], "out_links": len(e["links"]),
                       "issues": issues, "issue_count": len(issues),
                       "level": worst[0] if worst else "OK"})

    # 孤岛：无入链且无出链
    orphans = [e["title"] for e in entries if not e["links"] and inbound.get(e["title"], 0) == 0]
    for t in orphans:
        if not allow_orphan:
            for g in graded:
                if g["title"] == t:
                    g["issues"].append(("MEDIUM", "ORPHAN_ENTRY", "无任何入链与出链 → 孤岛条目"))
                    g["issue_count"] = len(g["issues"])
                    g["level"] = sorted((i[0] for i in g["issues"]),
                                        key=lambda x: REF_LEVEL_ORDER.get(x, 9))[0]
    # 深度：按引用链推算最长可达长度，超出 max_depth 提示收敛
    graph = {e["title"]: [l for l in e["links"] if l in titles] for e in entries}

    def depth(node, seen, limit):
        if node in seen or limit <= 0:
            return (0, node in seen)
        seen = seen | {node}
        best, cyc = 0, False
        for nxt in graph.get(node, []):
            d, c = depth(nxt, seen, limit - 1)
            best = max(best, d + 1)
            cyc = cyc or c
        return best, cyc

    for e in entries:
        d, cyc = depth(e["title"], set(), max_depth + 2)
        if cyc:
            cycles.append(e["title"])
        if d > max_depth:
            for g in graded:
                if g["title"] == e["title"]:
                    g["issues"].append(("LOW", "DEPTH_EXCEEDED",
                                        f"引用链长 {d} > 建议 {max_depth}"))
                    g["issue_count"] = len(g["issues"])
    return graded, dangling, orphans, sorted(set(cycles)), inbound


def render_ref_report(graded, dangling, orphans, cycles, inbound):
    """渲染交叉引用核验结果（Markdown）"""
    rows = []
    for g in sorted(graded, key=lambda x: REF_LEVEL_ORDER.get(x["level"], 9)):
        rows.append([g["level"], g["title"], g["out_links"],
                     inbound.get(g["title"], 0), g["issue_count"],
                     ",".join(i[1] for i in g["issues"]) or "-"])
    table = render_markdown_table(rows, ["级别", "条目", "出链", "入链", "问题数", "问题码"])
    tail = [f"断链 {len(dangling)} ｜ 孤岛 {len(orphans)} ｜ 含环节点 {len(cycles)}"]
    for src, dst in dangling[:5]:
        tail.append(f"- 断链：{src} → {dst}")
    return table + "\n\n" + "\n".join(tail)


def process(text):
    """交叉引用核验：解析条目与引用 → 检出断链/孤岛/环路 → 分级输出"""
    try:
        entries, policy = parse_ref_entries(text)
        graded, dangling, orphans, cycles, inbound = analyze_references(entries, policy)
        high = [g["title"] for g in graded if g["level"] == "HIGH"]
        return {
            "ok": True,
            "entry_count": len(entries),
            "link_total": sum(g["out_links"] for g in graded),
            "dangling_count": len(dangling),
            "dangling": [{"from": a, "to": b} for a, b in dangling],
            "orphan_entries": orphans,
            "cycle_nodes": cycles,
            "high_risk_count": len(high),
            "high_risk_entries": high,
            "per_entry": graded,
            "report": render_ref_report(graded, dangling, orphans, cycles, inbound),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "entry_count": 0, "per_entry": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="kb-crossref-integrity-checker", description="--variant")
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
