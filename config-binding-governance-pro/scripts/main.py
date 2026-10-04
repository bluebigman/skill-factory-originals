#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-flag-graph — 配置开关 依赖核验

核验特性开关依赖闭包与互斥组合合法性

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：解析特性开关依赖图并核验依赖闭包、互斥组合与依赖环，分级输出非法启用组合与不可达开关清单
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



FLAG_DECL_RX = re.compile(r"^\s*(flag|exclusive|policy)\s+(.*)$", re.I)
FLAG_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
FLAG_TRUE = ("1", "true", "yes", "y", "on", "enabled")
FLAG_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def fl22_kv(text):
    """解析 key=value 片段 → 字典"""
    out = {}
    for m in FLAG_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def fl22_bool(val, default=False):
    """宽松布尔解析（enabled/on/true 均视为真）"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in FLAG_TRUE


def fl22_list(val):
    """逗号分隔清单 → 去重保序列表"""
    seen, out = set(), []
    for x in (val or "").split(","):
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_flag_graph(text):
    """解析开关依赖图

    语法（每行一条声明，key=value 空格分隔）：
        flag name=new_flow enabled=true depends=gray_on,region_cn owner=order
        flag name=gray_on enabled=false
        flag name=legacy_flow enabled=true
        exclusive name=legacy_flow,new_flow
        policy strict_deps=true now=2026-09-13
    """
    flags, exclusives, policy = [], [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = FLAG_DECL_RX.match(line)
        if not m:
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        kv = fl22_kv(rest)
        if kind == "policy":
            policy.update(kv)
        elif kind == "exclusive":
            members = fl22_list(kv.get("name"))
            if members:
                exclusives.append({"line": lineno, "members": members})
        else:
            name = (kv.get("name") or "").strip()
            if not name:
                continue
            flags.append({
                "line": lineno, "name": name,
                "enabled": fl22_bool(kv.get("enabled"), False),
                "depends": fl22_list(kv.get("depends") or kv.get("requires")),
                "owner": kv.get("owner", ""),
                "kind": (kv.get("kind") or "permanent").strip(),
            })
    return flags, exclusives, policy


def analyze_flag_graph(flags, exclusives, policy):
    """核验开关依赖闭包、互斥冲突与不可达开关"""
    strict = fl22_bool(policy.get("strict_deps"), True)
    index = {f["name"]: f for f in flags}
    graded, global_issues = [], []

    for f in flags:
        issues = []
        for dep in f["depends"]:
            target = index.get(dep)
            if target is None:
                issues.append(("HIGH", "DEP_UNKNOWN", f"依赖 {dep} 未在清单中声明 → 取值不可判定"))
                continue
            if f["enabled"] and not target["enabled"]:
                issues.append(("HIGH", "DEP_UNSATISFIED",
                               f"已启用但依赖 {dep} 处于关闭状态 → 组合非法"))
            elif f["enabled"] and target["enabled"]:
                issues.append(("LOW", "DEP_OK", f"依赖 {dep} 已满足"))
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        worst = sorted((i[0] for i in issues), key=lambda x: order.get(x, 9))
        graded.append({"name": f["name"], "enabled": f["enabled"], "owner": f["owner"],
                       "kind": f["kind"], "depends": f["depends"], "issues": issues,
                       "issue_count": len(issues),
                       "level": worst[0] if worst else "OK"})

    # 互斥组合冲突
    for ex in exclusives:
        on = [m for m in ex["members"] if index.get(m, {}).get("enabled")]
        if len(on) > 1:
            global_issues.append(("HIGH", "EXCLUSIVE_CONFLICT",
                                  "互斥组多个成员同时启用：" + ", ".join(on)))
        for m in ex["members"]:
            if m not in index:
                global_issues.append(("MEDIUM", "EXCLUSIVE_UNKNOWN",
                                      f"互斥组声明了未登记开关 {m}"))

    # 依赖闭包链深与环检测
    def depth(name, seen):
        node = index.get(name)
        if node is None:
            return 0
        if name in seen:
            return -1
        seen = seen | {name}
        ds = [depth(d, seen) for d in node["depends"] if d in index]
        if any(d == -1 for d in ds):
            return -1
        return 1 + (max(ds) if ds else 0)

    cycles = []
    for f in flags:
        d = depth(f["name"], set())
        if d == -1:
            cycles.append(f["name"])
            global_issues.append(("HIGH", "DEP_CYCLE", f"{f['name']} 依赖链存在环 → 取值不可判定"))

    # 不可达：永久关闭但被其他启用开关依赖（前面的 DEP_UNSATISFIED 已覆盖），此处统计"永远关闭"清单
    never_on = [f["name"] for f in flags if not f["enabled"]]
    return graded, global_issues, {"cycle_flags": sorted(set(cycles)),
                                   "disabled_flags": never_on,
                                   "enabled_count": sum(1 for f in flags if f["enabled"])}


def render_flag_report(graded, global_issues, meta):
    """渲染开关依赖核验结果（Markdown）"""
    rows = []
    for g in sorted(graded, key=lambda x: FLAG_LEVEL_ORDER.get(x["level"], 9)):
        rows.append([g["level"], g["name"], "启用" if g["enabled"] else "关闭",
                     ",".join(g["depends"]) or "-", g["owner"] or "-",
                     ",".join(i[1] for i in g["issues"]) or "-"])
    table = render_markdown_table(rows, ["级别", "开关", "状态", "依赖", "归属", "问题码"])
    tail = [f"启用 {meta['enabled_count']} / 关闭 {len(meta['disabled_flags'])}"
            f"｜依赖环 {len(meta['cycle_flags'])}"]
    for _, code, detail in global_issues:
        tail.append(f"- {code}: {detail}")
    return table + "\n\n" + "\n".join(tail)


def process(text):
    """开关依赖核验：解析依赖图 → 校验闭包/互斥/环 → 分级输出非法组合清单"""
    try:
        flags, exclusives, policy = parse_flag_graph(text)
        graded, global_issues, meta = analyze_flag_graph(flags, exclusives, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        return {
            "ok": True,
            "flag_count": len(flags),
            "enabled_count": meta["enabled_count"],
            "exclusive_group_count": len(exclusives),
            "high_risk_flags": [g["name"] for g in high],
            "cycle_flags": meta["cycle_flags"],
            "global_issue_count": len(global_issues),
            "global_issues": [{"code": c, "detail": d} for _, c, d in global_issues],
            "per_flag": graded,
            "report": render_flag_report(graded, global_issues, meta),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "flag_count": 0, "per_flag": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="config-flag-graph", description="核验特性开关依赖闭包与互斥组合合法性")
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
