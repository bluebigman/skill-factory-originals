#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-flag-expiry-auditor — 运维配置 临时开关 到期清理核验

核验临时开关与灰度键的存活期限，按 TTL 推算逾期项并输出清理优先级清单

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：核验临时开关与灰度键的存活期限、按 TTL 推算逾期与临近到期项并输出清理优先级清单
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



FLAG_LINE_RX = re.compile(r"^\s*key\b(.*)$", re.I)
FLAG_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-]*)\s*=\s*([^\s]+)")
FLAG_KINDS = ("temp", "gray", "permanent")
DEFAULT_TTL_DAYS = 30


def flag_days_between(start, end):
    """按 YYYY-MM-DD 计算天数差；解析失败返回 None"""
    import datetime as _dt
    try:
        a = _dt.datetime.strptime(start.strip()[:10], "%Y-%m-%d")
        b = _dt.datetime.strptime(end.strip()[:10], "%Y-%m-%d")
        return (b - a).days
    except Exception:
        return None


def parse_flag_manifest(text):
    """解析开关清单

    语法：
        key name=feature.new_flow value=on kind=temp owner=order-team
            created=2026-03-01 ttl_days=30 now=2026-09-13
    """
    flags, now = [], ""
    for lineno, raw in enumerate(text.splitlines(), 1):
        m = FLAG_LINE_RX.match(raw.strip())
        if not m:
            continue
        item = {"line": lineno, "name": "", "value": "", "kind": "permanent",
                "owner": "", "created": "", "ttl_days": 0, "now": "",
                "scope": "global"}
        for k, v in FLAG_KV_RX.findall(m.group(1)):
            k, v = k.lower(), v.strip("\"'")
            if k == "name":
                item["name"] = v
            elif k in ("value", "val"):
                item["value"] = v
            elif k in ("kind", "type"):
                item["kind"] = v.lower()
            elif k in ("owner", "team"):
                item["owner"] = v
            elif k in ("created", "created_at", "since"):
                item["created"] = v
            elif k in ("ttl_days", "ttl"):
                try:
                    item["ttl_days"] = int(v)
                except Exception:
                    item["ttl_days"] = 0
            elif k in ("now", "today", "check_at"):
                item["now"] = v
                now = v
        if item["name"]:
            flags.append(item)
    return flags, now


def audit_flag(flag, now):
    """单条开关的到期体检"""
    if flag["kind"] == "permanent":
        return {"name": flag["name"], "kind": flag["kind"], "status": "permanent",
                "level": "LOW", "age_days": None, "left_days": None,
                "detail": "长期键：不参与到期清理"}
    if not flag["created"] or not flag["now"]:
        return {"name": flag["name"], "kind": flag["kind"], "status": "unmanaged",
                "level": "MED", "age_days": None, "left_days": None,
                "detail": "缺 created/now：无法判定到期，建议补登记"}
    ttl = flag["ttl_days"] or DEFAULT_TTL_DAYS
    age = flag_days_between(flag["created"], flag["now"])
    if age is None:
        return {"name": flag["name"], "kind": flag["kind"], "status": "unmanaged",
                "level": "MED", "age_days": None, "left_days": None,
                "detail": "created 日期格式非法（需 YYYY-MM-DD）"}
    left = ttl - age
    if left < 0:
        status, level = "expired", "HIGH"
        detail = "已逾期 %d 天未清理（TTL %d 天）" % (-left, ttl)
    elif left <= 7:
        status, level = "expiring", "MED"
        detail = "剩余 %d 天到期" % left
    else:
        status, level = "active", "LOW"
        detail = "剩余 %d 天" % left
    if not flag["owner"]:
        level = "HIGH" if status in ("expired", "expiring") else level
        detail = detail + "；未登记责任方"
    return {"name": flag["name"], "kind": flag["kind"], "status": status,
            "level": level, "age_days": age, "left_days": left, "detail": detail}


def render_flag_report(items, kind_stats):
    """渲染开关到期清单 + 类型分布"""
    rows = []
    for it in sorted(items, key=lambda x: (x["left_days"] is None, x["left_days"] or 0)):
        rows.append([it["name"], it["kind"], it["status"], it["level"],
                     "-" if it["left_days"] is None else str(it["left_days"]),
                     it["detail"]])
    if not rows:
        rows = [["-", "-", "-", "-", "-", "未识别到开关条目"]]
    table = render_markdown_table(rows, ["开关键", "类型", "状态", "级别",
                                         "剩余天数", "说明"])
    if kind_stats:
        lines = ["", "### 类型分布", ""]
        lines.append(render_markdown_table(
            [[k, str(v)] for k, v in sorted(kind_stats.items())], ["类型", "数量"]))
        table = table + "\n" + "\n".join(lines)
    return table


def process(text):
    """V21：解析开关清单 → 计算到期与逾期 → 清理清单 + 类型分布"""
    flags, now = parse_flag_manifest(text)
    if not flags:
        return {"ok": True, "variant": "V21", "flag_count": 0,
                "note": "未识别到开关条目（需 key name=... 行）",
                "items": [], "report_table": "", "content_id": stable_id(text)}
    items = [audit_flag(f, now) for f in flags]
    kind_stats = {}
    for f in flags:
        kind_stats[f["kind"]] = kind_stats.get(f["kind"], 0) + 1
    expired = [i for i in items if i["status"] == "expired"]
    expiring = [i for i in items if i["status"] == "expiring"]
    unmanaged = [i for i in items if i["status"] == "unmanaged"]
    temporary = [i for i in flags if i["kind"] in ("temp", "gray")]
    return {"ok": True, "variant": "V21",
            "flag_count": len(flags),
            "temporary_count": len(temporary),
            "expired_count": len(expired),
            "expiring_count": len(expiring),
            "unmanaged_count": len(unmanaged),
            "kinds": kind_stats,
            "conclusion": "开关 {} 个（临时/灰度 {}）；已逾期 {} 个；7 天内到期 {} 个；无法判定 {} 个".format(
                len(flags), len(temporary), len(expired), len(expiring), len(unmanaged)),
            "expired": [i["name"] for i in expired],
            "expiring": [i["name"] for i in expiring],
            "cleanup_plan": ["先关停并移除 " + n
                             for n in [i["name"] for i in expired][:10]],
            "items": items,
            "report_table": render_flag_report(items, kind_stats),
            "next_action": "逾期开关当班关停下线；7 天内到期的排入本周清理窗口；无法判定项补登记",
            "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="config-flag-expiry-auditor", description="核验临时开关与灰度键的存活期限，按 TTL 推算逾期项并输出清理优先级清单")
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
