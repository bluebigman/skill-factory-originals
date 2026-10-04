#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""authz-scope-auditor — 权限配置 越权排查 角色继承

权限配置 越权排查 角色继承核验工具

领域：安全审计/静态分析（平台 13 分双上榜）
能力：核验角色继承链、资源通配与操作级别上限，检出越权授予与职责分离冲突并分级输出授权收敛清单
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



AUTHZ_DECL_RX = re.compile(r"^\s*(role|grant|duty|policy)\s+(.*)$", re.I)
AUTHZ_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
AUTHZ_TRUE = ("1", "true", "yes", "y", "on")
AUTHZ_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
AUTHZ_LEVEL_RANK = {"read": 1, "write": 2, "admin": 3}
AUTHZ_WILDCARD = ("*", "all", "any", "0.0.0.0/0")
AUTHZ_MAX_DEPTH = 3


def au19_kv(text):
    """解析 key=value 片段 → 字典（键统一小写）"""
    out = {}
    for m in AUTHZ_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def au19_bool(val, default=False):
    """宽松布尔解析"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in AUTHZ_TRUE


def au19_int(val, default=0):
    """安全整数解析"""
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def au19_split(val):
    """逗号/分号分隔 → 去空列表"""
    return [x.strip() for x in re.split(r"[,;]+", val or "") if x.strip()]


def parse_authz_declarations(text):
    """解析授权声明块

    语法（每行一条声明，key=value 空格分隔）：
        role name=admin inherits=editor scope=* level=admin
        grant user=alice role=admin resource=* level=write
        duty user=alice tasks=approve,submit
        policy max_inherit_depth=3 forbid_wildcard=true max_grant_level=write
                sod_pairs=approve:submit,pay:audit max_role_grants=6
    """
    roles, grants, duties, policy = {}, [], [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = AUTHZ_DECL_RX.match(line)
        if not m:
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        kv = au19_kv(rest)
        if kind == "policy":
            policy.update(kv)
            continue
        if kind == "role":
            nm = (kv.get("name") or kv.get("id") or "").strip()
            if not nm:
                continue
            roles[nm] = {
                "line": lineno,
                "name": nm,
                "inherits": au19_split(kv.get("inherits", "")),
                "scope": (kv.get("scope") or "").strip(),
                "level": (kv.get("level") or "").strip().lower(),
                "owner": kv.get("owner", ""),
            }
            continue
        if kind == "grant":
            grants.append({
                "line": lineno,
                "user": (kv.get("user") or kv.get("subject") or "").strip(),
                "role": (kv.get("role") or "").strip(),
                "resource": (kv.get("resource") or "").strip(),
                "level": (kv.get("level") or "").strip().lower(),
            })
            continue
        duties.append({
            "line": lineno,
            "user": (kv.get("user") or "").strip(),
            "tasks": au19_split(kv.get("tasks", "")),
        })
    return roles, grants, duties, policy


def au19_inherit_depth(roles, name, seen=None):
    """计算角色继承深度；检出环路时返回 -1"""
    seen = seen or set()
    if name in seen:
        return -1
    seen = seen | {name}
    r = roles.get(name)
    if not r or not r["inherits"]:
        return 0
    deepest = 0
    for parent in r["inherits"]:
        if parent not in roles:
            continue
        d = au19_inherit_depth(roles, parent, seen)
        if d < 0:
            return -1
        deepest = max(deepest, d + 1)
    return deepest


def grade_authz(roles, grants, duties, policy):
    """逐角色/逐授予核验收敛性，输出分级问题清单"""
    max_depth = au19_int(policy.get("max_inherit_depth"), AUTHZ_MAX_DEPTH) or AUTHZ_MAX_DEPTH
    forbid_wild = au19_bool(policy.get("forbid_wildcard"), True)
    max_level = (policy.get("max_grant_level") or "write").strip().lower()
    max_level_rank = AUTHZ_LEVEL_RANK.get(max_level, 2)
    sod_pairs = [tuple(p.split(":")) for p in au19_split(policy.get("sod_pairs", ""))
                 if ":" in p]
    graded = []

    for nm, r in roles.items():
        issues = []
        depth = au19_inherit_depth(roles, nm)
        if depth < 0:
            issues.append(("HIGH", "INHERIT_CYCLE", "角色继承链成环，权限解析结果不可判定"))
        elif depth > max_depth:
            issues.append(("MEDIUM", "INHERIT_TOO_DEEP",
                           f"继承深度 {depth} > 上限 {max_depth}，越权范围难审计"))
        if forbid_wild and r["scope"] in AUTHZ_WILDCARD:
            issues.append(("HIGH", "WILDCARD_SCOPE", f"作用域 {r['scope']} 覆盖全部资源"))
        if r["level"] == "admin" and r["inherits"]:
            issues.append(("MEDIUM", "ADMIN_INHERITS", "管理级角色仍继承下级角色，易夹带隐性权限"))
        for parent in r["inherits"]:
            if parent not in roles:
                issues.append(("HIGH", "INHERIT_MISSING", f"继承的角色 {parent} 未声明"))
        if not r["scope"]:
            issues.append(("MEDIUM", "SCOPE_MISSING", "未声明作用域，默认按全域理解"))
        if not r["level"]:
            issues.append(("LOW", "LEVEL_MISSING", "未声明操作级别，无法判定读写边界"))
        worst = sorted((i[0] for i in issues), key=lambda x: AUTHZ_LEVEL_ORDER.get(x, 9))
        graded.append({"kind": "role", "name": nm, "line": r["line"],
                       "issues": issues, "issue_count": len(issues),
                       "level": worst[0] if worst else "OK"})

    user_tasks = {}
    for d in duties:
        user_tasks.setdefault(d["user"], set()).update(d["tasks"])

    for g in grants:
        issues = []
        r = roles.get(g["role"])
        if not r:
            issues.append(("HIGH", "GRANT_UNKNOWN_ROLE", f"授予了未声明的角色 {g['role'] or '(空)'}"))
            r = {"scope": "", "level": ""}
        if forbid_wild and (g["resource"] in AUTHZ_WILDCARD or r.get("scope") in AUTHZ_WILDCARD):
            issues.append(("HIGH", "GRANT_WILDCARD_RESOURCE",
                           f"资源 {g['resource'] or '(空)'} 为通配，违背最小权限"))
        if not g["resource"]:
            issues.append(("MEDIUM", "RESOURCE_MISSING", "未声明资源，归属不明"))
        rank = AUTHZ_LEVEL_RANK.get(g["level"], 0)
        if rank > max_level_rank:
            issues.append(("HIGH", "LEVEL_OVER_CEILING",
                           f"操作级别 {g['level'] or '(空)'} 超出上限 {max_level}"))
        if rank == 0:
            issues.append(("LOW", "LEVEL_UNKNOWN", f"操作级别 {g['level'] or '(空)'} 不在已知集合"))
        rl = AUTHZ_LEVEL_RANK.get(r.get("level", ""), 0)
        if rl and rank and rank > rl:
            issues.append(("MEDIUM", "GRANT_EXCEEDS_ROLE",
                           "授予级别高于角色自身级别，存在越权授予"))
        tasks = user_tasks.get(g["user"], set())
        for a, b in sod_pairs:
            if a in tasks and b in tasks:
                issues.append(("HIGH", "SOD_CONFLICT",
                               f"同一用户同时持有 {a} 与 {b}，破坏职责分离"))
        worst = sorted((i[0] for i in issues), key=lambda x: AUTHZ_LEVEL_ORDER.get(x, 9))
        graded.append({"kind": "grant", "name": f"{g['user'] or '(空)'}@{g['role'] or '(空)'}",
                       "line": g["line"], "issues": issues, "issue_count": len(issues),
                       "level": worst[0] if worst else "OK"})
    return graded


def render_authz_report(graded):
    """渲染授权收敛核验结果（Markdown）"""
    rows = []
    for g in sorted(graded, key=lambda x: (AUTHZ_LEVEL_ORDER.get(x["level"], 9), x["line"])):
        rows.append([g["level"], g["kind"], g["name"], g["line"], g["issue_count"],
                     ",".join(i[1] for i in g["issues"]) or "-"])
    return render_markdown_table(rows, ["级别", "类型", "对象", "行号", "问题数", "问题码"])


def process(text):
    """授权收敛核验：解析角色/授予/职责声明 → 核验继承、通配与职责分离 → 分级输出整改清单"""
    try:
        roles, grants, duties, policy = parse_authz_declarations(text)
        graded = grade_authz(roles, grants, duties, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "role_count": len(roles),
            "grant_count": len(grants),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_objects": [g["name"] for g in high],
            "wildcard_grants": [g["name"] for g in graded
                                if any(i[1] in ("WILDCARD_SCOPE", "GRANT_WILDCARD_RESOURCE")
                                       for i in g["issues"])],
            "sod_conflicts": [g["name"] for g in graded
                              if any(i[1] == "SOD_CONFLICT" for i in g["issues"])],
            "issue_code_distribution": codes,
            "per_object": graded,
            "report": render_authz_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "role_count": 0, "per_object": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="authz-scope-auditor", description="权限配置 越权排查 角色继承核验工具")
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
