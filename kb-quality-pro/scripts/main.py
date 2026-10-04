#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-dup-cluster — 知识条目 相似聚类 合并建议

对知识条目做归一化相似聚类，输出重复簇与合并建议

领域：知识库/信息整理（平台 54 分第 2 名）
能力：对知识条目做归一化相似聚类，输出重复簇与合并建议
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



NORM_STRIP_RX = re.compile(r"[\s\u3000，。、；：！？（）()《》〈〉\"'’“”·\-—_/\\|\[\]{}*#>]+")


def normalize_entry(s):
    """归一化：去标点空白 + 小写（仅用于比对，不改原条目）"""
    return NORM_STRIP_RX.sub("", str(s or "")).lower()


def bigrams(s):
    """二元组集合（长度 1 时退化为单元素集合）"""
    if not s:
        return set()
    if len(s) == 1:
        return {s}
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def cluster_duplicate_entries(entries, threshold=0.72):
    """归一化 + 二元组 Jaccard 聚类，仅返回组内 ≥2 条的重复簇"""
    norm = [normalize_entry(e) for e in entries]
    grams = [bigrams(n) for n in norm]
    used, clusters = set(), []
    for i in range(len(entries)):
        if i in used or not norm[i]:
            continue
        group = [i]
        for j in range(i + 1, len(entries)):
            if j in used or not norm[j]:
                continue
            if jaccard(grams[i], grams[j]) >= threshold:
                group.append(j)
        if len(group) < 2:
            continue
        used.update(group)
        clusters.append({
            "canonical": entries[group[0]],
            "members": [{"line": k + 1, "text": entries[k],
                         "similarity": round(jaccard(grams[i], grams[k]), 3)} for k in group],
        })
    return clusters


def merge_advice(clusters):
    """按成员数降序给出合并建议（保留信息量最大的一条）"""
    ranked = sorted(clusters, key=lambda c: -len(c["members"]))
    out = []
    for i, c in enumerate(ranked[:10], 1):
        keep = max(c["members"], key=lambda m: len(m["text"]))
        out.append("{0}. 保留第 {1} 行（信息量最大），合并其余 {2} 条并补来源".format(
            i, keep["line"], len(c["members"]) - 1))
    return out


def process(text):
    """V7：条目归一化 → 相似聚类 → 合并建议"""
    entries = [l.strip() for l in (text or "").splitlines() if l.strip()]
    clusters = cluster_duplicate_entries(entries)
    advice = merge_advice(clusters)
    dup_n = sum(len(c["members"]) for c in clusters)
    conclusion = ("检测 {0} 条条目，{1} 个重复簇涉及 {2} 条".format(len(entries), len(clusters), dup_n)
                  if clusters else "检测 {0} 条条目，无重复簇".format(len(entries)))
    return {"ok": True, "variant": "V7", "conclusion": conclusion,
            "entry_count": len(entries), "clusters": clusters, "merge_advice": advice}



def build_parser():
    p = argparse.ArgumentParser(prog="kb-dup-cluster", description="对知识条目做归一化相似聚类，输出重复簇与合并建议")
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
