#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc-section-tree — 文档切分 目录树 层级梳理

解析文档标题层级、生成缩进目录树并统计结构问题

领域：知识库/信息整理（平台 54 分第 2 名）
能力：解析文档标题层级、生成缩进目录树、统计章节结构与跳级问题
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



HEADING_RX = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_outline(text):
    """解析 Markdown 标题层级为扁平大纲（含行号与层级）"""
    items = []
    for lineno, line in enumerate(text.splitlines(), 1):
        m = HEADING_RX.match(line.strip())
        if m:
            items.append({"line": lineno, "level": len(m.group(1)), "title": m.group(2).strip()})
    return items


def outline_tree(items):
    """扁平大纲 → 嵌套目录树（按层级归并）"""
    root, stack = [], []
    for it in items:
        node = {"title": it["title"], "level": it["level"], "line": it["line"], "children": []}
        while stack and stack[-1]["level"] >= it["level"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            root.append(node)
        stack.append(node)
    return root


def render_outline(tree, depth=0, lines=None):
    """目录树 → 缩进文本（供交付文档直接粘贴）"""
    lines = [] if lines is None else lines
    for node in tree:
        lines.append("  " * depth + f"- {node['title']}  (第{node['line']}行)")
        render_outline(node["children"], depth + 1, lines)
    return lines


def outline_stats(items):
    """层级统计：条目数 / 最大深度 / 各层数量"""
    depth = {}
    for it in items:
        depth[it["level"]] = depth.get(it["level"], 0) + 1
    return {"section_count": len(items),
            "max_depth": max(depth) if depth else 0,
            "by_level": {f"H{k}": v for k, v in sorted(depth.items())}}


def find_orphan_sections(items):
    """层级跳变检测（如 H2 直接跳到 H4）——结构问题提示"""
    out, prev = [], 0
    for it in items:
        if prev and it["level"] > prev + 1:
            out.append(f"第 {it['line']} 行：{prev} 级直接跳到 {it['level']} 级（{it['title']}）")
        prev = it["level"]
    return out


def process(text):
    """V1：标题解析 → 目录树 → 结构统计与跳级提示"""
    items = parse_outline(text)
    if not items:
        return {"ok": False, "error": "未识别到标题结构（需 Markdown 标题行）"}
    tree = outline_tree(items)
    stats = outline_stats(items)
    return {"ok": True, "variant": "V1",
            "conclusion": f"识别 {stats['section_count']} 个章节，最大层级 H{stats['max_depth']}",
            "stats": stats, "outline": render_outline(tree)[:60],
            "level_jumps": find_orphan_sections(items), "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="doc-section-tree", description="解析文档标题层级、生成缩进目录树并统计结构问题")
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
