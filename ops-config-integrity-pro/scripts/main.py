#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-comment-coverage-checker — 配置注释 覆盖率 占位注释

核验配置键注释覆盖率与注释有效性、检出未注释键与无归属注释

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：核验配置键的注释覆盖率与注释有效性，检出未注释键、无归属注释与占位注释
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


DIRECTIVE_RE = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s+(.+?);\s*$", re.I)
BLOCK_RE = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*\{?\s*$", re.I)


def parse_config(text):
    """解析类 Nginx 配置：抽出块与指令（忽略注释与空行）"""
    blocks, directives = [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        mb = BLOCK_RE.match(line)
        if mb:
            blocks.append({"line": lineno, "name": mb.group(1)})
            continue
        md = DIRECTIVE_RE.match(line)
        if md:
            directives.append({"line": lineno, "key": md.group(1), "value": md.group(2).strip()})
    return {"blocks": blocks, "directives": directives}


def find_duplicates(parsed):
    """同一作用域内重复指令检测（后者覆盖前者 → 常见故障源）"""
    seen, dups = {}, []
    for d in parsed["directives"]:
        k = d["key"].lower()
        if k in seen:
            dups.append({"key": k, "first_line": seen[k], "dup_line": d["line"]})
        else:
            seen[k] = d["line"]
    return dups


def summarize(parsed):
    """按指令名聚合统计"""
    agg = {}
    for d in parsed["directives"]:
        agg.setdefault(d["key"].lower(), []).append(d["value"])
    return {k: {"count": len(v), "values": v[:5]} for k, v in sorted(agg.items())}


def check_conflicts(parsed):
    """语义冲突检查：互斥指令同时出现（如 listen 端口重复、ssl 与明文并存）"""
    issues = []
    keys = {d["key"].lower() for d in parsed["directives"]}
    pairs = [("proxy_pass", "root"), ("ssl_certificate", "listen")]
    for a, b in pairs:
        if a in keys and b in keys:
            issues.append({"level": "MEDIUM", "msg": f"{a} 与 {b} 同时出现，需确认作用域"})
    ports = [d["value"].split()[0].rstrip(";") for d in parsed["directives"]
             if d["key"].lower() == "listen" and d["value"].split()]
    dup_ports = sorted({p for p in ports if ports.count(p) > 1})
    for p in dup_ports:
        issues.append({"level": "HIGH", "msg": f"listen 端口重复：{p}"})
    return issues


def render_config_report(parsed, dups, issues):
    """渲染配置体检报告（结论在前）"""
    rows = [[k, v["count"], ", ".join(str(x) for x in v["values"][:3])]
            for k, v in summarize(parsed).items()]
    return {
        "ok": not [i for i in issues if i["level"] == "HIGH"],
        "conclusion": "配置结构清晰、无高危冲突" if not issues else f"发现 {len(issues)} 项待确认",
        "counts": {"blocks": len(parsed["blocks"]), "directives": len(parsed["directives"]),
                   "duplicates": len(dups), "issues": len(issues)},
        "duplicate_directives": dups,
        "conflicts": issues,
        "directive_table_md": render_markdown_table(rows, ["指令", "出现次数", "示例值"]),
        "next_action": "按重复指令清单逐项合并" if dups else "无重复项，可进入下一步变更评审",
    }



CMT_ENTRY_RX = re.compile(r"^\s*([#;]+)\s*(.*)$")
CMT_KV_RX = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.\-]*)\s*[:=]\s*(.*?)\s*;?\s*$")
CMT_NGINX_RX = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(\S+)\s*;\s*$")
CMT_PLACEHOLDER = ("待补", "未填", "xxx", "xxx", "示例", "temp", "tbd", "n/a")
CMT_MIN_LEN = 4


def parse_config_entries(text):
    """逐行分类：comment / key / section / blank"""
    entries = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip():
            entries.append({"line": lineno, "kind": "blank", "key": "", "value": "", "text": ""})
            continue
        m = CMT_ENTRY_RX.match(line)
        if m:
            entries.append({"line": lineno, "kind": "comment", "key": "",
                            "value": "", "text": m.group(2).strip()})
            continue
        if re.match(r"^\s*\[[^\]]+\]\s*$", line):
            entries.append({"line": lineno, "kind": "section", "key": "",
                            "value": "", "text": line.strip()})
            continue
        m = CMT_KV_RX.match(line) or CMT_NGINX_RX.match(line)
        if m:
            entries.append({"line": lineno, "kind": "key", "key": m.group(1),
                            "value": (m.group(2) or "").strip(), "text": line.strip()})
            continue
        entries.append({"line": lineno, "kind": "other", "key": "",
                        "value": "", "text": line.strip()})
    return entries


def comment_coverage(entries):
    """覆盖率与注释质量：被注释键 / 未注释键 / 无归属注释 / 占位注释"""
    commented, uncommented, orphans, weak = [], [], [], []
    last_comment = None
    for e in entries:
        if e["kind"] == "comment":
            last_comment = e
            continue
        if e["kind"] == "key":
            if last_comment is not None:
                commented.append({"line": e["line"], "key": e["key"],
                                  "comment": last_comment["text"],
                                  "comment_line": last_comment["line"]})
                low = last_comment["text"].lower()
                if len(last_comment["text"]) < CMT_MIN_LEN or any(
                        p in low for p in CMT_PLACEHOLDER):
                    weak.append({"line": last_comment["line"], "key": e["key"],
                                 "comment": last_comment["text"],
                                 "detail": "注释过短或为占位文本，未说明取值含义"})
            else:
                uncommented.append({"line": e["line"], "key": e["key"],
                                    "detail": "该键无紧邻注释"})
            last_comment = None
            continue
        if e["kind"] in ("section", "blank", "other") and last_comment is not None:
            orphans.append({"line": last_comment["line"], "comment": last_comment["text"],
                            "detail": "注释后未见配置键，疑为残留或无归属"})
            last_comment = None
    if last_comment is not None:
        orphans.append({"line": last_comment["line"], "comment": last_comment["text"],
                        "detail": "文件末尾注释无归属"})
    total = len(commented) + len(uncommented)
    return {"total_keys": total, "commented": commented, "uncommented": uncommented,
            "orphan_comments": orphans, "weak_comments": weak}


def process(text):
    """V14：配置逐行分类 → 注释覆盖率与注释质量核验"""
    entries = parse_config_entries(text)
    cov = comment_coverage(entries)
    total = cov["total_keys"]
    pct = rate(len(cov["commented"]), total) if total else 0.0
    issues = []
    for u in cov["uncommented"]:
        issues.append({"level": "MEDIUM", "line": u["line"], "item": "未注释键",
                       "detail": u["key"] + "：" + u["detail"]})
    for o in cov["orphan_comments"]:
        issues.append({"level": "LOW", "line": o["line"], "item": "无归属注释",
                       "detail": o["comment"] + "：" + o["detail"]})
    for w in cov["weak_comments"]:
        issues.append({"level": "LOW", "line": w["line"], "item": "占位注释",
                       "detail": w["key"] + "：" + w["detail"]})
    if total:
        conclusion = "配置键 {0} 个，注释覆盖 {1} 个（{2}%），无归属注释 {3} 条，占位注释 {4} 条".format(
            total, len(cov["commented"]), pct, len(cov["orphan_comments"]),
            len(cov["weak_comments"]))
    else:
        conclusion = "未识别到配置键行（示例：server.timeout = 30  # 上游超时秒数）"
    return {"ok": True, "variant": "V14", "conclusion": conclusion,
            "key_count": total, "commented_count": len(cov["commented"]),
            "coverage_pct": pct, "orphan_count": len(cov["orphan_comments"]),
            "weak_count": len(cov["weak_comments"]), "issues": issues,
            "uncommented_keys": [u["key"] for u in cov["uncommented"]]}



def build_parser():
    p = argparse.ArgumentParser(prog="config-comment-coverage-checker", description="核验配置键注释覆盖率与注释有效性、检出未注释键与无归属注释")
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
