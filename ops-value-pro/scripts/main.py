#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-include-auditor — 运维配置 包含链 加载顺序

抽取配置包含指令、还原加载顺序、检测重复加载与通配遮蔽、审计相对路径加载风险

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：抽取配置包含指令、还原加载顺序、检测重复加载与通配遮蔽、审计相对路径加载风险
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



INCLUDE_RE = re.compile(r"^\s*include\s+([^;]+);", re.I)
SOURCE_RE = re.compile(r"^\s*(?:source|import|\\.)\\s+(\\S+)")
OPTIONAL_RE = re.compile(r"^\\s*include\\s+optional\\s+([^;]+);", re.I)


def collect_includes(text):
    """按出现顺序收集 include/source 目标（保留行号、形态与可选标记）"""
    out = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        optional = False
        m = OPTIONAL_RE.match(line)
        if m:
            optional = True
        else:
            m = INCLUDE_RE.match(line) or SOURCE_RE.match(line)
        if not m:
            continue
        target = m.group(1).strip().strip('"').strip("'")
        if not target:
            continue
        out.append({"line": lineno, "target": target,
                    "optional": optional,
                    "is_glob": bool(re.search(r"[*?\\[]", target)),
                    "is_abs": target.startswith("/"),
                    "kind": "通配" if re.search(r"[*?\\[]", target) else "显式"})
    return out


def build_load_plan(includes):
    """还原加载顺序：重复加载 / 遮蔽关系 / 顺序风险"""
    order, seen, dup, shadow = [], {}, [], []
    for it in includes:
        t = it["target"]
        if t in seen:
            dup.append({"target": t, "first_line": seen[t]["line"], "again_line": it["line"],
                        "msg": "同一目标被加载两次，后者可能覆盖前者"})
            continue
        seen[t] = it
        order.append({"seq": len(order) + 1, "target": t, "line": it["line"],
                      "kind": it["kind"], "optional": it["optional"]})
    for i, a in enumerate(order):
        if not a["kind"] == "通配":
            continue
        prefix = a["target"].rsplit("/", 1)[0] if "/" in a["target"] else ""
        for b in order[i + 1:]:
            if prefix and b["target"].startswith(prefix) and b["kind"] == "显式":
                shadow.append({"glob_line": a["line"], "explicit_line": b["line"],
                               "explicit": b["target"],
                               "msg": "通配加载在前、同名显式加载在后，后者可能被前者的默认值覆盖"})
    return order, dup, shadow


def group_by_prefix(includes):
    """按目录前缀分组统计（判断配置分散度）"""
    groups = {}
    for it in includes:
        t = it["target"]
        prefix = t.rsplit("/", 1)[0] if "/" in t else "(无目录前缀)"
        groups.setdefault(prefix, []).append(t)
    return {k: {"count": len(v), "samples": v[:3]} for k, v in
            sorted(groups.items(), key=lambda kv: -len(kv[1]))}


def relative_warnings(includes):
    """相对路径告警：相对路径的加载基准依赖启动目录，易出事故"""
    out = []
    for it in includes:
        if not it["is_abs"] and not it["is_glob"] and not it["optional"]:
            out.append({"line": it["line"], "target": it["target"],
                        "level": "MEDIUM",
                        "msg": "相对路径加载，基准随启动目录变化，建议改绝对路径"})
        elif not it["is_abs"] and it["is_glob"] and not it["optional"]:
            out.append({"line": it["line"], "target": it["target"],
                        "level": "LOW",
                        "msg": "通配加载未标 optional，目录为空时会导致启动失败"})
    return out


def render_load_plan_md(order):
    """加载顺序一览表"""
    if not order:
        return "（无包含指令）"
    rows = [[i["seq"], i["line"], i["target"], i["kind"], "是" if i["optional"] else "否"]
            for i in order]
    return render_markdown_table(rows, ["序号", "行号", "目标", "形态", "可选"])


def process(text):
    """V8：包含指令抽取 → 加载顺序还原 → 重复/遮蔽/相对路径体检"""
    includes = collect_includes(text)
    if not includes:
        return {"ok": False, "error": "未发现 include/source 指令（示例：include /etc/app/base.conf;）",
                "variant": "V8"}
    order, dup, shadow = build_load_plan(includes)
    rel = relative_warnings(includes)
    issues = dup + shadow + rel
    high = [i for i in issues if i.get("level") == "HIGH"]
    return {"ok": not high, "variant": "V8",
            "conclusion": "共 {} 条包含指令（去重后 {} 个目标）；重复 {}、遮蔽 {}、路径风险 {}".format(
                len(includes), len(order), len(dup), len(shadow), len(rel)),
            "include_count": len(includes),
            "unique_target_count": len(order),
            "duplicate_count": len(dup),
            "shadow_count": len(shadow),
            "optional_count": len([i for i in includes if i["optional"]]),
            "glob_count": len([i for i in includes if i["is_glob"]]),
            "load_order": order,
            "duplicates": dup,
            "shadowing": shadow,
            "path_issues": rel,
            "groups": group_by_prefix(includes),
            "load_plan_md": render_load_plan_md(order),
            "next_action": "先消除重复加载，再把通配从前移到后，最后统一为绝对路径",
            "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="config-include-auditor", description="抽取配置包含指令、还原加载顺序、检测重复加载与通配遮蔽、审计相对路径加载风险")
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
