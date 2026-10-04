#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-change-impact-mapper — 配置变更 影响面 执行顺序

由变更键反查引用服务与文件、评估影响面并按爆炸半径输出变更执行顺序

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：由变更键反查引用它的服务与文件，评估影响面并按爆炸半径输出变更执行顺序
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



IMP_CHANGE_RX = re.compile(r"^\s*change\b(.*)$", re.I)
IMP_REF_RX = re.compile(r"^\s*ref\b(.*)$", re.I)
IMP_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-]*)\s*=\s*([^\s]+)")
IMP_SEVERE_RX = re.compile(
    r"(?i)timeout|port|host|secret|password|token|pwd|key|pool|replica|threads|memory|url|addr|dsn")


def parse_change_set(text):
    """解析变更键声明与引用关系声明"""
    changes, refs = [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        mc = IMP_CHANGE_RX.match(raw)
        if mc:
            f = {}
            for k, v in IMP_KV_RX.findall(mc.group(1)):
                f[k.lower()] = v.strip("\"'")
            key = f.get("key") or f.get("name")
            if key:
                changes.append({"line": lineno, "key": key,
                                "old": f.get("old", ""), "new": f.get("new", "")})
            continue
        mr = IMP_REF_RX.match(raw)
        if mr:
            f = {}
            for k, v in IMP_KV_RX.findall(mr.group(1)):
                f[k.lower()] = v.strip("\"'")
            key = f.get("key") or f.get("name")
            if key:
                refs.append({"line": lineno, "key": key,
                             "service": f.get("service") or f.get("svc") or "-",
                             "file": f.get("file") or "-",
                             "usage": f.get("usage") or ""})
    return changes, refs


def impact_of(change, refs):
    """单变更键的影响面评估"""
    key = change["key"]
    own = [r for r in refs if r["key"] == key]
    services = sorted({r["service"] for r in own if r["service"] != "-"})
    files = sorted({r["file"] for r in own if r["file"] != "-"})
    severe = bool(IMP_SEVERE_RX.search(key))
    if not own:
        level, hint = "LOW", "无引用记录：改前须确认该键是否已被废弃，避免改了个死键"
    elif len(services) >= 3 or severe:
        level, hint = "HIGH", "高危键（牵连服务多或属关键配置），须先备份并在低峰执行"
    elif len(services) == 2:
        level, hint = "MEDIUM", "影响两个服务，须同步通知服务负责人"
    else:
        level, hint = "LOW", "影响面单一，可直接执行并复核生效值"
    return {"key": key, "old": change["old"], "new": change["new"],
            "ref_count": len(own), "services": services, "files": files,
            "severe": severe, "level": level, "hint": hint}


def order_by_blast(impacts):
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(impacts, key=lambda x: (order.get(x["level"], 3), -x["ref_count"], x["key"]))


def process(text):
    """V16：变更集解析 → 引用面映射 → 按影响面排序输出执行顺序"""
    changes, refs = parse_change_set(text)
    impacts = [impact_of(c, refs) for c in changes]
    impacts = order_by_blast(impacts)
    all_services = sorted({s for i in impacts for s in i["services"]})
    high = len([i for i in impacts if i["level"] == "HIGH"])
    dead = [i["key"] for i in impacts if i["ref_count"] == 0]
    if changes:
        conclusion = "变更键 {0} 个，牵连服务 {1} 个，高危 {2} 个，无引用键 {3} 个".format(
            len(changes), len(all_services), high, len(dead))
    else:
        conclusion = ("未识别到 change 声明行（示例：change key=server.timeout old=30 new=60；"
                      "ref key=server.timeout service=orders-api file=app.yaml）")
    return {"ok": True, "variant": "V16", "conclusion": conclusion,
            "change_count": len(changes), "ref_count": len(refs),
            "high_risk_count": high, "services": all_services,
            "unreferenced_keys": dead,
            "execution_order": [{"key": i["key"], "level": i["level"],
                                 "ref_count": i["ref_count"], "hint": i["hint"]}
                                for i in impacts]}



def build_parser():
    p = argparse.ArgumentParser(prog="config-change-impact-mapper", description="由变更键反查引用服务与文件、评估影响面并按爆炸半径输出变更执行顺序")
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
