#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit-event-coverage-auditor — 安全审计 事件覆盖 留痕完整性

核验审计留痕事件集覆盖度、留痕期与关键字段完整性

领域：安全审计/静态分析（平台 13 分双上榜）
能力：按基线事件集核验审计留痕的覆盖广度、留痕期达标情况与关键字段完整性，输出分级缺口清单与补齐顺序
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


RISK_PATTERNS = [
    ("硬编码密钥", re.compile(r"(?i)(api[_-]?key|secret|passwd|password|token)\s*=\s*[\"'][^\"']{8,}[\"']"), "HIGH"),
    ("弱随机源", re.compile(r"\brandom\.(random|randint|choice)\s*\("), "MEDIUM"),
    ("命令拼接", re.compile(r"(os\.system|subprocess\.(call|run|Popen))\s*\([^)]*\+|f[\"'][^\"']*\{"), "HIGH"),
    ("危险反序列化", re.compile(r"\b(pickle\.loads|yaml\.load)\s*\("), "HIGH"),
    ("裸 except", re.compile(r"except\s*:"), "LOW"),
    ("调试残留", re.compile(r"\b(print|console\.log)\s*\(.*(password|token|secret)"), "MEDIUM"),
]


def scan_source(text, path=""):
    """逐行匹配风险模式，返回分级发现"""
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rx, level in RISK_PATTERNS:
            if rx.search(line):
                findings.append({"file": path, "line": lineno, "rule": name,
                                 "level": level, "snippet": line.strip()[:120]})
    return findings


def grade(findings):
    """按最高风险级别给出总体评级"""
    order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    worst = max((order.get(f["level"], 0) for f in findings), default=0)
    return {3: "BLOCK", 2: "WARN", 1: "INFO", 0: "PASS"}[worst]


def scan_tree(root):
    """扫描目录下所有常见源码文件"""
    exts = (".py", ".js", ".ts", ".java", ".go", ".sh", ".yaml", ".yml", ".env")
    all_findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
        for fn in filenames:
            if not fn.endswith(exts):
                continue
            p = os.path.join(dirpath, fn)
            try:
                txt = read_text_safe(p)
            except Exception:
                continue
            all_findings += scan_source(txt, os.path.relpath(p, root))
    return all_findings



AUDIT_BASE_EVENTS = {
    "login_success": ["actor", "ip", "result"],
    "login_fail": ["actor", "ip", "reason"],
    "perm_change": ["actor", "target", "before", "after"],
    "config_change": ["actor", "key", "before", "after"],
    "data_export": ["actor", "scope", "volume"],
    "cred_rotate": ["actor", "cred", "window"],
}
AUDIT_EVENT_RX = re.compile(r"^\s*event\s+(.*)$", re.I)
AUDIT_POLICY_RX = re.compile(r"^\s*policy\s+(.*)$", re.I)
AUDIT_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
AUDIT_TRUE = ("1", "true", "yes", "y", "on")
AUDIT_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def au13_kv(text):
    """把 key=value 片段解析成字典（值缺失时留空串）"""
    out = {}
    for m in AUDIT_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def au13_bool(val, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in AUDIT_TRUE


def au13_int(val, default=0):
    try:
        return int(str(val).strip())
    except Exception:
        return default


def parse_audit_declarations(text):
    """解析审计声明块

    语法（每行一条声明，key=value 空格分隔）：
        event  name=login_success logged=true retention_days=180 fields=actor,ip,result
        event  name=perm_change   logged=false retention_days=90  fields=actor,target
        policy min_retention_days=180 immutable=true now=2026-09-13
    """
    events, policy, lineno_map = [], {}, {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        mp = AUDIT_POLICY_RX.match(line)
        if mp:
            policy.update(au13_kv(mp.group(1)))
            continue
        me = AUDIT_EVENT_RX.match(line)
        if me:
            kv = au13_kv(me.group(1))
            name = (kv.get("name") or "").strip()
            if not name:
                continue
            fields = [f.strip() for f in (kv.get("fields") or "").split(",") if f.strip()]
            events.append({
                "name": name,
                "line": lineno,
                "logged": au13_bool(kv.get("logged"), True),
                "retention_days": au13_int(kv.get("retention_days"), 0),
                "fields": fields,
                "immutable": au13_bool(kv.get("immutable"), False),
                "owner": kv.get("owner", ""),
            })
            lineno_map[name] = lineno
    return events, policy


def detect_event_mentions(text):
    """无声明块时的兜底：按基线事件名在正文中的出现情况推断已覆盖事件"""
    low = text.lower()
    hit = []
    for name in AUDIT_BASE_EVENTS:
        if name in low or name.replace("_", " ") in low:
            hit.append(name)
    return hit


def grade_audit_coverage(events, policy):
    """审计事件覆盖与留痕分级"""
    min_ret = au13_int(policy.get("min_retention_days"), 180)
    immutable_required = au13_bool(policy.get("immutable"), False)
    declared_names = [e["name"] for e in events]
    covered = [n for n in declared_names if n in AUDIT_BASE_EVENTS]
    missing = [n for n in AUDIT_BASE_EVENTS if n not in covered]
    per_event, level_count = [], {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for e in events:
        issues = []
        if not e["logged"]:
            issues.append({"level": "HIGH", "code": "NOT_LOGGED", "msg": "声明为未留痕"})
        if e["retention_days"] and e["retention_days"] < min_ret:
            gap = min_ret - e["retention_days"]
            lv = "HIGH" if gap >= min_ret // 2 else "MEDIUM"
            issues.append({"level": lv, "code": "RETENTION_SHORT",
                           "msg": "留痕期 {} 天，低于基线 {} 天（差 {}）".format(
                               e["retention_days"], min_ret, gap)})
        if not e["retention_days"]:
            issues.append({"level": "MEDIUM", "code": "RETENTION_UNKNOWN",
                           "msg": "未声明留痕期"})
        if immutable_required and not e["immutable"]:
            issues.append({"level": "MEDIUM", "code": "NOT_IMMUTABLE",
                           "msg": "基线要求不可改写，但该事件未声明"})
        base_fields = AUDIT_BASE_EVENTS.get(e["name"], [])
        lost = [f for f in base_fields if f not in e["fields"]]
        if lost:
            lv = "HIGH" if len(lost) >= 2 else "MEDIUM"
            issues.append({"level": lv, "code": "FIELD_GAP",
                           "msg": "缺关键字段 " + ",".join(lost)})
        if not e["fields"]:
            issues.append({"level": "LOW", "code": "FIELD_EMPTY", "msg": "未声明字段清单"})
        for it in issues:
            level_count[it["level"]] += 1
        worst = min((AUDIT_LEVEL_ORDER[i["level"]] for i in issues), default=9)
        per_event.append({"name": e["name"], "line": e["line"],
                          "level": ("OK" if worst == 9 else
                                    ["HIGH", "MEDIUM", "LOW"][worst]),
                          "issues": issues})
    return {"covered": covered, "missing": missing, "per_event": per_event,
            "level_count": level_count, "min_retention": min_ret,
            "immutable_required": immutable_required}


def render_audit_report(graded):
    rows = []
    for item in graded["per_event"]:
        codes = ",".join(i["code"] for i in item["issues"]) or "-"
        msgs = "；".join(i["msg"] for i in item["issues"]) or "无问题"
        rows.append([item["name"], item["line"], item["level"], codes, msgs])
    if not rows:
        rows = [["-", "-", "-", "-", "未声明任何审计事件"]]
    return render_markdown_table(rows, ["事件名", "行号", "级别", "问题码", "说明"])


def process(text):
    """V13：解析审计事件声明 → 覆盖度/留痕期/字段完整性体检 → 分级缺口清单"""
    events, policy = parse_audit_declarations(text)
    if not events:
        mentioned = detect_event_mentions(text)
        missing = [n for n in AUDIT_BASE_EVENTS if n not in mentioned]
        return {"ok": True, "variant": "V13", "declared_count": 0,
                "mentioned_events": mentioned, "mentioned_count": len(mentioned),
                "missing_events": missing,
                "note": "未识别到 event 声明行；已按基线事件名在正文中的出现情况推断覆盖",
                "coverage_rate": rate(len(mentioned), len(AUDIT_BASE_EVENTS)),
                "report_table": render_markdown_table(
                    [["-", "-", "-", "-", "未声明审计事件，需按模板补齐声明块"]],
                    ["事件名", "行号", "级别", "问题码", "说明"]),
                "next_action": "按 event name=<基线事件> logged=true retention_days=<N> fields=<a,b,c> 补齐声明后复跑",
                "content_id": stable_id(text)}
    graded = grade_audit_coverage(events, policy)
    hard = [p["name"] for p in graded["per_event"] if p["level"] == "HIGH"]
    return {"ok": True, "variant": "V13",
            "declared_count": len(events),
            "covered_count": len(graded["covered"]),
            "coverage_rate": rate(len(graded["covered"]), len(AUDIT_BASE_EVENTS)),
            "missing_events": graded["missing"],
            "min_retention_days": graded["min_retention"],
            "level_count": graded["level_count"],
            "hard_events": hard,
            "conclusion": "已声明 {} 类事件；基线覆盖 {}/{}；高危事件 {} 项，中危 {} 项，低危 {} 项".format(
                len(events), len(graded["covered"]), len(AUDIT_BASE_EVENTS),
                graded["level_count"].get("HIGH", 0),
                graded["level_count"].get("MEDIUM", 0),
                graded["level_count"].get("LOW", 0)),
            "per_event": graded["per_event"],
            "report_table": render_audit_report(graded),
            "next_action": "先补未声明的高危事件留痕与关键字段，再核对留痕期是否达到基线",
            "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="audit-event-coverage-auditor", description="核验审计留痕事件集覆盖度、留痕期与关键字段完整性")
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
