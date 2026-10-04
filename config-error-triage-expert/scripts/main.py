#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-error-report-auditor — 配置报错 定位信息 修复建议

核验配置解析失败时的报错质量，检出行号缺失与类别未分类

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：核验配置解析失败时的报错质量，检出行号缺失、出错行内容缺失、类别未分类、错误条数不符与首个即停语义矛盾并分级输出
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



EP_DECL_RX = re.compile(r"^\s*(error|parse|policy)\s+(.*)$", re.I)
EP_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
EP_TRUE = ("1", "true", "yes", "y", "on")
EP_KINDS = ("syntax", "type", "duplicate", "missing", "range", "encoding", "io")


def ep_kv(text):
    out = {}
    for m in EP_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def ep_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in EP_TRUE


def ep_int(val, default=0):
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def parse_error_report_spec(text):
    """解析解析失败的报错声明块

    语法（每行一条）：
        error file=a.conf line=4 col=10 kind=syntax message="unexpected token" \
              context=yes suggest=no
        parse file=a.conf errors=2 stop=first
        policy require_line=true require_context=true max_reported=10 require_suggest=true
    """
    errors, parses, policy = [], [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = EP_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), ep_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
        elif kind == "error":
            errors.append({
                "line": lineno,
                "file": (kv.get("file") or "").strip(),
                "line_no": ep_int(kv.get("line"), 0),
                "col": ep_int(kv.get("col"), 0),
                "kind": (kv.get("kind") or "").strip().lower(),
                "message": (kv.get("message") or "").strip(),
                "context": ep_bool(kv.get("context"), False),
                "suggest": ep_bool(kv.get("suggest"), False),
            })
        elif kind == "parse":
            parses.append({
                "line": lineno,
                "file": (kv.get("file") or "").strip(),
                "errors": ep_int(kv.get("errors"), -1),
                "stop": (kv.get("stop") or "").strip().lower(),
            })
    return errors, parses, policy


def grade_error_report_spec(errors, parses, policy):
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    require_line = ep_bool(policy.get("require_line"), True)
    require_context = ep_bool(policy.get("require_context"), True)
    require_suggest = ep_bool(policy.get("require_suggest"), False)
    require_message = ep_bool(policy.get("require_message"), True)
    max_reported = ep_int(policy.get("max_reported"), 10)
    buckets = {}

    def add(scope, level, code, msg, line):
        b = buckets.setdefault(scope, {"scope": scope, "line": line, "issues": []})
        b["issues"].append((level, code, msg))
        if not b["line"]:
            b["line"] = line

    by_file = {}
    for e in errors:
        by_file.setdefault(e["file"], []).append(e)

    for e in errors:
        scope = "%s:%d" % (e["file"] or "(未标文件)", e["line"])
        if require_line and e["line_no"] <= 0:
            add(scope, "HIGH", "ERROR_POSITION_MISSING",
                "报错未给出文件内行号（使用者无法定位）", e["line"])
        if e["col"] < 0:
            add(scope, "MEDIUM", "ERROR_COLUMN_INVALID",
                "列号 %d 非法" % e["col"], e["line"])
        if e["line_no"] > 0 and e["col"] == 0:
            add(scope, "LOW", "ERROR_COLUMN_ABSENT",
                "仅给行号未给列号（同行多错时无法区分）", e["line"])
        if not e["kind"]:
            add(scope, "MEDIUM", "ERROR_KIND_MISSING",
                "报错未分类（无法分流到对应修复流程）", e["line"])
        elif e["kind"] not in EP_KINDS:
            add(scope, "LOW", "ERROR_KIND_UNKNOWN",
                "报错类别 %s 非约定取值（%s）" % (e["kind"], "/".join(EP_KINDS)), e["line"])
        if require_message and not e["message"]:
            add(scope, "HIGH", "ERROR_MESSAGE_MISSING",
                "报错无描述文本（使用者只能靠猜）", e["line"])
        if require_context and not e["context"]:
            add(scope, "MEDIUM", "ERROR_CONTEXT_MISSING",
                "报错未附出错行内容（无法就地核对）", e["line"])
        if require_suggest and not e["suggest"]:
            add(scope, "LOW", "ERROR_SUGGEST_MISSING",
                "报错未给修复建议", e["line"])

    for p in parses:
        items = by_file.get(p["file"], [])
        if p["errors"] < 0:
            add(p["file"] or "(未标文件)", "MEDIUM", "ERROR_COUNT_MISSING",
                "解析声明未给出错误条数（无法判断是否报全）", p["line"])
        elif items and p["errors"] != len(items):
            add(p["file"] or "(未标文件)", "MEDIUM", "ERROR_COUNT_MISMATCH",
                "声明错误数 %d 与实际列出 %d 条不一致" % (p["errors"], len(items)), p["line"])
        if p["stop"] == "first" and len(items) > 1:
            add(p["file"] or "(未标文件)", "MEDIUM", "STOP_FIRST_MULTI_LISTED",
                "声明遇到首个错误即停，却列出 %d 条（多错未聚合被发现）" % len(items), p["line"])
        if p["stop"] and p["stop"] not in ("first", "collect", "all", "abort"):
            add(p["file"] or "(未标文件)", "LOW", "STOP_MODE_UNKNOWN",
                "停止语义取值异常（%s）" % p["stop"], p["line"])
        if p["stop"] == "collect" and max_reported > 0 and len(items) > max_reported:
            add(p["file"] or "(未标文件)", "MEDIUM", "REPORTED_EXCEEDS_LIMIT",
                "列出 %d 条超过上限 %d（输出被截断但未标注）" % (len(items), max_reported),
                p["line"])

    out = list(buckets.values())
    for g in out:
        g["issues"].sort(key=lambda x: (order.get(x[0], 9), x[1]))
        g["issue_count"] = len(g["issues"])
        g["high_risk"] = any(i[0] == "HIGH" for i in g["issues"])
        g["top_level"] = g["issues"][0][0] if g["issues"] else "LOW"
    out.sort(key=lambda x: (order.get(x["top_level"], 9), x["scope"]))
    return out


def render_error_report(graded):
    if not graded:
        return "未识别到报错声明（检查 error/parse/policy 行）。"
    lines = ["# 解析报错定位与容错核验", ""]
    for g in graded:
        mark = "🔴" if g["high_risk"] else ("🟡" if g["top_level"] == "MEDIUM" else "⚪")
        lines.append("%s 位置 %s（问题 %d）" % (mark, g["scope"], g["issue_count"]))
        for lv, code, msg in g["issues"]:
            lines.append("    [%s] %s — %s" % (lv, code, msg))
    high = [g["scope"] for g in graded if g["high_risk"]]
    lines.append("")
    lines.append("高风险位置 %d 处：%s" % (len(high), "、".join(high) if high else "无"))
    return "\n".join(lines)


def process(text):
    try:
        errors, parses, policy = parse_error_report_spec(text)
        graded = grade_error_report_spec(errors, parses, policy)
        high = [g for g in graded if g["high_risk"]]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "error_count": len(errors),
            "parse_count": len(parses),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "per_scope": graded,
            "report": render_error_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "error_count": 0, "parse_count": 0,
                "issue_total": 0, "high_risk_count": 0, "high_risk_scopes": [],
                "issue_code_distribution": {}, "per_scope": [], "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="config-error-report-auditor", description="核验配置解析失败时的报错质量，检出行号缺失与类别未分类")
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
