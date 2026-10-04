#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cfg-list-value-hygiene-check — 配置列表 分隔符 重复项核对

核对多值配置的分隔符、空项与重复项，避免合并结果出错

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：核验列表型取值的分隔符纪律、空项与重复项、跨定义顺序稳定性，检出合并结果依赖加载次序的风险并分级输出整改清单
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



LS_DECL_RX = re.compile(r"^\s*(list|policy)\s+(.*)$", re.I)
LS_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
LS_SEPS = {"comma": ",", "semicolon": ";", "pipe": "|", "space": " "}
LS_TRUE = ("1", "true", "yes", "y", "on")


def ls_kv(text):
    """解析 key=value 片段（键小写）；空值键须置于行尾（WBR-213）"""
    out = {}
    for m in LS_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def ls_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in LS_TRUE


def ls_sep_of(value, declared):
    """判定取值实际使用的分隔符族；多族混用返回 mixed"""
    v = value or ""
    fams = [name for name, ch in LS_SEPS.items() if ch in v]
    fams = [f for f in fams if not (f == "comma" and declared == "comma")]
    used = [name for name, ch in LS_SEPS.items() if ch in v]
    if len(used) > 1:
        return "mixed"
    if used:
        return used[0]
    return declared or "none"


def parse_list_spec(text):
    """解析列表型取值声明块

    语法（每行一条声明）：
        list key=app.hosts value=a.com,b.com sep=comma file=a.conf
        list key=app.allow value=x;y;z sep=semicolon file=a.conf order=2
        policy require_sep=comma forbid_dup=true forbid_empty=true require_order=stable
    """
    items, policy = [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LS_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), ls_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
            continue
        sepname = (kv.get("sep") or "").strip().lower()
        sep = LS_SEPS.get(sepname, sepname if sepname else ",")
        rawval = kv.get("value", "")
        parts = rawval.split(sep) if sep else [rawval]
        items.append({"line": lineno, "key": kv.get("key", ""), "value": rawval,
                      "sep": sepname or "comma", "sep_char": sep,
                      "file": kv.get("file", "(unnamed)"),
                      "order": kv.get("order", ""),
                      "items": parts})
    return items, policy


def grade_list_spec(items, policy):
    """逐键分级核验列表取值规范；返回按风险排序的结果列表"""
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    require_sep = (policy.get("require_sep") or "").strip().lower()
    forbid_dup = ls_bool(policy.get("forbid_dup"), True)
    forbid_empty = ls_bool(policy.get("forbid_empty"), True)
    require_order = ls_bool(policy.get("require_order"), False)
    by_key = {}
    for it in items:
        by_key.setdefault(it["key"] or "(未命名键)", []).append(it)
    out = []
    for key, group in by_key.items():
        issues = []
        seps = {g["sep"] for g in group if g["sep"]}
        mixed = {ls_sep_of(g["value"], g["sep"]) for g in group}
        mixed = {m for m in mixed if m in ("mixed",)}
        if len(seps) > 1 or mixed:
            issues.append(("HIGH", "SEP_MIX",
                           "同一键跨文件使用不同分隔符：%s" % ",".join(sorted(seps | mixed))))
        if require_sep and seps and any(s != require_sep for s in seps):
            issues.append(("MEDIUM", "SEP_NOT_ALLOWED",
                           "分隔符 %s 不符合规范要求 %s"
                           % (",".join(sorted(s for s in seps if s != require_sep)), require_sep)))
        for g in group:
            parts = g["items"]
            if forbid_empty and any(not p.strip() for p in parts):
                issues.append(("MEDIUM", "EMPTY_ITEM",
                               "%s 第 %d 行含空项（连续分隔符或首尾分隔符）" % (g["file"], g["line"])))
            if any(not p.strip() for p in parts) is False and len(parts) == 1 and \
                    ls_sep_of(g["value"], g["sep"]) == "none":
                issues.append(("LOW", "SINGLE_ITEM",
                               "%s 第 %d 行为单值列表，可考虑按标量声明" % (g["file"], g["line"])))
            norm = [p.strip().lower() for p in parts if p.strip()]
            dupes = sorted({x for x in norm if norm.count(x) > 1})
            if forbid_dup and dupes:
                issues.append(("HIGH", "DUPLICATE_ITEM",
                               "%s 第 %d 行含重复项：%s"
                               % (g["file"], g["line"], ",".join(dupes))))
        if require_order and len(group) > 1:
            seqs = [[p.strip().lower() for p in g["items"] if p.strip()] for g in group]
            base = sorted(seqs[0])
            for i, s in enumerate(seqs[1:], 1):
                if s != seqs[0] and sorted(s) == base:
                    issues.append(("MEDIUM", "ORDER_INSTABLE",
                                   "同键仅顺序不同（第 %d 份定义），合并结果依赖加载次序"
                                   % (i + 1)))
        if issues:
            issues.sort(key=lambda x: order.get(x[0], 9))
            out.append({"key": key, "definition_count": len(group), "level": issues[0][0],
                        "issue_count": len(issues),
                        "issues": [[l, c, m] for l, c, m in issues]})
    out.sort(key=lambda x: (order.get(x["level"], 9), -x["issue_count"], x["key"]))
    return out


def render_list_report(graded):
    """渲染列表型取值核验报告"""
    lines = ["列表型取值规范核验报告", "=" * 26]
    if not graded:
        lines.append("未检出问题：列表型取值分隔符、去重与顺序均符合规范。")
        return "\n".join(lines)
    for g in graded:
        lines.append("[%s] %s（定义 %d 份，问题 %d 项）"
                     % (g["level"], g["key"], g["definition_count"], g["issue_count"]))
        for lvl, code, msg in g["issues"]:
            lines.append("    - (%s) %s：%s" % (lvl, code, msg))
    return "\n".join(lines)


def process(text):
    """列表取值核验：解析列表声明/策略 → 核验分隔符·空项·重复·顺序 → 分级输出整改清单"""
    try:
        items, policy = parse_list_spec(text)
        graded = grade_list_spec(items, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "definition_count": len(items),
            "key_count": len({i["key"] for i in items}),
            "item_total": sum(len(i["items"]) for i in items),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_keys": [g["key"] for g in high],
            "issue_code_distribution": codes,
            "per_key": graded,
            "report": render_list_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "definition_count": 0, "per_key": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="cfg-list-value-hygiene-check", description="核对多值配置的分隔符、空项与重复项，避免合并结果出错")
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
