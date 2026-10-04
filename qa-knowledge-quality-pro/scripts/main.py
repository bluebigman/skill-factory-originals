#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa-pair-extractor — 问答抽取 问答对 结构化整理

抽取文档问答对、归类问题类型并输出结构化问答库

领域：知识库/信息整理（平台 54 分第 2 名）
能力：抽取文档中的问答对、归类问题类型、去重并输出结构化问答库
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



QA_Q_RX = re.compile(r"^\s*(?:Q|问)\s*[:：]\s*(.+)$")
QA_A_RX = re.compile(r"^\s*(?:A|答)\s*[:：]\s*(.+)$")


def parse_qa_lines(text):
    """按 Q/A 与 问/答 前缀抽取问答对（支持续行答案）"""
    pairs, cur, pending = [], None, []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        mq = QA_Q_RX.match(line)
        ma = QA_A_RX.match(line)
        if mq:
            if cur and cur.get("answer"):
                pairs.append(cur)
            cur = {"question": mq.group(1).strip(), "answer": "", "q_line": lineno, "a_line": None}
        elif ma and cur is not None:
            cur["answer"] = ma.group(1).strip()
            cur["a_line"] = lineno
            pairs.append(cur)
            cur = None
        elif cur is not None and not cur.get("answer"):
            cur["answer"] = (cur["answer"] + " " + line).strip()
        else:
            pending.append({"line": lineno, "raw": line[:60]})
    if cur and cur.get("answer"):
        pairs.append(cur)
    return pairs, pending


def infer_question_type(question):
    """按疑问词归类问题类型（便于知识库分面）"""
    if re.search(r"如何|怎么|怎样|how", question, re.I):
        return "操作步骤"
    if re.search(r"为什么|为何|原因|why", question, re.I):
        return "原因分析"
    if re.search(r"是什么|什么是|含义|what", question, re.I):
        return "概念解释"
    if re.search(r"能否|是否|可以吗|能不能", question):
        return "可行性判断"
    return "其他"


def dedup_qa(pairs):
    """按问题主体去重（保留答案更完整的一条）"""
    best = {}
    for p in pairs:
        key = re.sub(r"[^\w\u4e00-\u9fff]", "", p["question"]).lower()
        if key not in best or len(p["answer"]) > len(best[key]["answer"]):
            best[key] = p
    return list(best.values())


def qa_statistics(pairs):
    """问答对统计：类型分布 / 平均答案长度 / 短答案占比"""
    types, lens = {}, []
    for p in pairs:
        t = infer_question_type(p["question"])
        types[t] = types.get(t, 0) + 1
        lens.append(len(p["answer"]))
    short = sum(1 for n in lens if n < 10)
    return {"count": len(pairs), "by_type": types,
            "avg_answer_len": round(sum(lens) / len(lens), 1) if lens else 0.0,
            "short_answer_pct": rate(short, len(lens))}


def process(text):
    """V3：问答对抽取 → 类型归类 → 去重与统计"""
    pairs, pending = parse_qa_lines(text)
    if not pairs:
        return {"ok": False, "error": "未抽取到问答对（需 Q/A 或 问/答 前缀）"}
    pairs = dedup_qa(pairs)
    stat = qa_statistics(pairs)
    return {"ok": True, "variant": "V3",
            "conclusion": f"抽取问答对 {stat['count']} 组，覆盖类型 {len(stat['by_type'])} 类",
            "stats": stat,
            "pairs": [{"question": p["question"], "answer": p["answer"][:120],
                       "type": infer_question_type(p["question"]), "q_line": p["q_line"]} for p in pairs[:20]],
            "unmatched_lines": pending[:10], "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="qa-pair-extractor", description="抽取文档问答对、归类问题类型并输出结构化问答库")
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
