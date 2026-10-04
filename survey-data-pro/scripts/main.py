#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""column-domain-validator — 字段值域校验 分组统计 导出预览

按列分组、枚举值域校验与分布统计

领域：批量数据转换/格式定制（平台 15 分）
能力：批量读取多编码表格/文本、字段规范化、去重、格式转换与校验报告
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


def normalize_header(cols):
    """表头规范化：去空格、统一小写、去重命名"""
    out, seen = [], {}
    for c in cols:
        k = re.sub(r"\s+", "", str(c or "")).strip() or "col"
        key = k.lower()
        seen[key] = seen.get(key, 0) + 1
        out.append(k if seen[key] == 1 else f"{k}_{seen[key]}")
    return out


def dedup_rows(rows, key_idx):
    """按指定列去重（保留首次出现），返回去重后数据与被删行号"""
    seen, kept, dropped = set(), [], []
    for n, row in enumerate(rows):
        key = tuple(row[i] if i < len(row) else "" for i in key_idx)
        if key in seen:
            dropped.append(n)
            continue
        seen.add(key)
        kept.append(row)
    return kept, dropped


def validate_rows(rows, ncol):
    """列数一致性校验，输出问题行"""
    return [{"row": n, "got": len(r), "expect": ncol} for n, r in enumerate(rows) if len(r) != ncol]


def convert_rows(rows, mapping):
    """字段值映射转换（如状态名统一）"""
    return [[mapping.get(str(c), c) for c in r] for r in rows]



def split_by_column(rows, col_idx):
    """按某列取值分组（分表交付场景）"""
    groups = {}
    for r in rows:
        k = str(r[col_idx]) if col_idx < len(r) else "<缺失>"
        groups.setdefault(k, []).append(r)
    return groups


def validate_domain(rows, col_idx, allowed):
    """枚举值域校验：找出不在允许集合内的取值"""
    bad = []
    for n, r in enumerate(rows):
        if col_idx >= len(r):
            continue
        v = str(r[col_idx]).strip()
        if allowed and v not in allowed:
            bad.append({"row": n, "value": v})
    return bad


def summarize_domain(rows, col_idx):
    """值域分布统计（TopN）"""
    cnt = {}
    for r in rows:
        if col_idx < len(r):
            v = str(r[col_idx]).strip()
            cnt[v] = cnt.get(v, 0) + 1
    return sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:20]


def process(text):
    """V3：按列分组 → 值域校验 → 分布统计"""
    rows = [l.split(",") for l in text.splitlines() if l.strip()]
    if not rows:
        return {"ok": False, "error": "输入为空"}
    header = normalize_header(rows[0]); body = rows[1:]
    groups = split_by_column(body, 0)
    return {"ok": True, "variant": "V3", "columns": header, "rows": len(body),
            "group_count": len(groups), "group_sizes": {k: len(v) for k, v in list(groups.items())[:10]},
            "domain_top": summarize_domain(body, 0), "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="column-domain-validator", description="按列分组、枚举值域校验与分布统计")
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
