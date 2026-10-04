#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-near-dup-merger — 重复条目 相似合并 去重整理

切分知识条目、按内容指纹聚类并归并近重复条目

领域：知识库/信息整理（平台 54 分第 2 名）
能力：切分知识条目、按内容指纹聚类、归并近重复条目并选举代表条目
本实现完全离线，不发起网络调用、不读写用户隐私数据。
"""
import argparse, json, os, re, sys

# WB 依赖降级注入（2026-09-13）：网络调用默认 8s 超时，防 hang 死（无产出）
try:
    import socket as _wb_sock
    _wb_sock.setdefaulttimeout(8)
except Exception:
    pass


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



def entry_tokens(text):
    """条目指纹：英文词 + 中文 2-gram"""
    s = str(text or "").lower()
    words = set(re.findall(r"[a-z][a-z0-9_-]{1,}", s))
    cjk = re.findall(r"[\u4e00-\u9fff]", s)
    words |= {"".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
    return words


def jaccard(a, b):
    """集合 Jaccard 相似度"""
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 3)


def parse_entries(text):
    """条目解析：按空行或标题切分，返回条目正文与指纹"""
    blocks, cur = [], []
    for line in text.splitlines():
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if re.match(r"^#{1,6}\s+", line.strip()) and cur:
            blocks.append(cur)
            cur = [line]
            continue
        cur.append(line)
    if cur:
        blocks.append(cur)
    entries = []
    for n, blk in enumerate(blocks, 1):
        body = " ".join(x.strip() for x in blk).strip()
        if not body:
            continue
        title = re.sub(r"^#+\s*", "", blk[0].strip())[:40] or f"条目{n}"
        entries.append({"no": n, "title": title, "body": body, "tokens": entry_tokens(body)})
    return entries


def cluster_entries(entries, threshold=0.5):
    """按相似度聚类，组内保留信息最完整的一条为代表"""
    clusters, used = [], set()
    for i, e in enumerate(entries):
        if i in used:
            continue
        grp = [i]
        for j in range(i + 1, len(entries)):
            if j in used:
                continue
            if jaccard(e["tokens"], entries[j]["tokens"]) >= threshold:
                grp.append(j)
                used.add(j)
        used.add(i)
        members = [entries[k] for k in grp]
        rep = max(members, key=lambda m: len(m["body"]))
        clusters.append({"representative": rep["title"], "size": len(members),
                         "members": [m["title"] for m in members],
                         "max_similarity": max((jaccard(rep["tokens"], m["tokens"]) for m in members), default=1.0)})
    return clusters


def process(text):
    """V6：条目切分 → 相似度聚类 → 重复归并与代表条目选举"""
    entries = parse_entries(text)
    if not entries:
        return {"ok": False, "error": "输入为空或无有效条目"}
    clusters = cluster_entries(entries)
    dup = [c for c in clusters if c["size"] > 1]
    return {"ok": True, "variant": "V6",
            "conclusion": f"切分 {len(entries)} 条，聚为 {len(clusters)} 组，其中重复组 {len(dup)} 个",
            "entry_count": len(entries), "cluster_count": len(clusters),
            "duplicate_groups": len(dup), "removed": len(entries) - len(clusters),
            "groups": [f"{c['representative']}（{c['size']} 条：{'、'.join(c['members'][:5])}）" for c in dup[:8]],
            "kept": [c["representative"] for c in clusters][:20], "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="kb-near-dup-merger", description="切分知识条目、按内容指纹聚类并归并近重复条目")
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
