#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sec-data-classification-auditor — 数据分级 流转标注 降级存储

--variant

领域：安全审计/静态分析（平台 13 分双上榜）
能力：核验字段分级标注完整性与跨域流转的加密、掩码与责任方要求，定位未分级字段与明文外流路径并分级输出
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



DATA_DECL_RX = re.compile(r"^\s*(field|flow|policy)\s+(.*)$", re.I)
DATA_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
DATA_TRUE = ("1", "true", "yes", "y", "on")
DATA_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
DATA_LEVELS = ("L1", "L2", "L3", "L4")          # L1 公开 → L4 最敏感
DATA_LEVEL_NUM = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
DATA_PUBLIC_SINKS = ("public_api", "cdn", "export", "log", "third_party")


def da17_kv(text):
    """解析 key=value 片段 → 字典"""
    out = {}
    for m in DATA_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def da17_bool(val, default=False):
    """宽松布尔解析"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in DATA_TRUE


def da17_list(val):
    """逗号分隔清单 → 去重保序"""
    seen, out = set(), []
    for x in (val or "").split(","):
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_data_declarations(text):
    """解析数据分级与流转声明块

    语法（每行一条声明，key=value 空格分隔）：
        field name=idCard level=L4 owner=risk domain=pii
        field name=nickname level=L1
        flow from=order to=warehouse fields=idCard,phone sink=internal encrypted=true
        flow from=order to=bi_report fields=idCard sink=export encrypted=false masked=false
        policy min_encrypt_level=L3 require_owner=true
    """
    fields, flows, policy = [], [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = DATA_DECL_RX.match(line)
        if not m:
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        kv = da17_kv(rest)
        if kind == "policy":
            policy.update(kv)
        elif kind == "flow":
            flows.append({
                "line": lineno,
                "from": (kv.get("from") or "").strip(),
                "to": (kv.get("to") or "").strip(),
                "fields": da17_list(kv.get("fields")),
                "sink": (kv.get("sink") or "internal").strip().lower(),
                "encrypted": da17_bool(kv.get("encrypted"), False),
                "masked": da17_bool(kv.get("masked"), False),
            })
        else:
            lvl = (kv.get("level") or "").strip().upper()
            fields.append({
                "line": lineno,
                "name": (kv.get("name") or "").strip(),
                "level": lvl,
                "declared_level": lvl,
                "owner": kv.get("owner", ""),
                "domain": kv.get("domain", ""),
            })
    return fields, flows, policy


def grade_data_flow(fields, flows, policy):
    """核验字段分级标注完整性与跨域流转的加密/掩码/责任方要求"""
    min_enc = (policy.get("min_encrypt_level") or "L3").strip().upper()
    need_owner = da17_bool(policy.get("require_owner"), True)
    index = {f["name"]: f for f in fields if f["name"]}
    graded, flow_issues = [], []

    for f in fields:
        issues = []
        if f["level"] not in DATA_LEVELS:
            issues.append(("HIGH", "LEVEL_INVALID", f"分级 {f['declared_level'] or '(空)'} 不在 L1-L4 之内"))
        if need_owner and not f["owner"]:
            issues.append(("MEDIUM", "OWNER_MISSING", "未标注责任方，分级无兜底人"))
        if not f["domain"]:
            issues.append(("LOW", "DOMAIN_MISSING", "未标注所属域，跨域判断缺依据"))
        worst = sorted((i[0] for i in issues), key=lambda x: DATA_LEVEL_ORDER.get(x, 9))
        graded.append({"name": f["name"] or "(未命名)", "level": f["level"] or "-",
                       "owner": f["owner"], "issues": issues, "issue_count": len(issues),
                       "level_flag": worst[0] if worst else "OK"})

    for fl in flows:
        issues = []
        max_level, unknown = 0, []
        for fn in fl["fields"]:
            meta = index.get(fn)
            if meta is None:
                unknown.append(fn)
                continue
            max_level = max(max_level, DATA_LEVEL_NUM.get(meta["level"], 0))
        if unknown:
            issues.append(("MEDIUM", "FLOW_FIELD_UNKNOWN",
                           "流转引用了未分级字段：" + ",".join(unknown)))
        need_enc = max_level >= DATA_LEVEL_NUM.get(min_enc, 3)
        if need_enc and not fl["encrypted"]:
            issues.append(("HIGH", "FLOW_PLAINTEXT",
                           f"含 L{max_level} 字段但未声明加密传输"))
        if fl["sink"] in DATA_PUBLIC_SINKS and max_level >= 3 and not fl["masked"]:
            issues.append(("HIGH", "SINK_UNMASKED",
                           f"流向 {fl['sink']} 且含 L{max_level} 字段但未声明掩码"))
        if fl["sink"] in DATA_PUBLIC_SINKS and fl["to"] and not fl["to"] in ("", "-"):
            issues.append(("LOW", "SINK_EXTERNAL_NOTE",
                           f"流向 {fl['sink']} 属对外面，须确认接收方已签署处理约定"))
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        worst = sorted((i[0] for i in issues), key=lambda x: order.get(x, 9))
        flow_issues.append({"route": f"{fl['from']} → {fl['to']}", "sink": fl["sink"],
                            "max_level": f"L{max_level}" if max_level else "-",
                            "issues": issues, "issue_count": len(issues),
                            "level_flag": worst[0] if worst else "OK"})

    # 覆盖：已分级字段占流转引用字段的比例
    referenced = {fn for fl in flows for fn in fl["fields"]}
    covered = [fn for fn in referenced if fn in index]
    return graded, flow_issues, referenced, covered


def render_data_report(graded, flow_issues):
    """渲染数据分级与流转核验结果（Markdown）"""
    rows = []
    for g in sorted(graded, key=lambda x: DATA_LEVEL_ORDER.get(x["level_flag"], 9)):
        rows.append([g["level_flag"], g["name"], g["level"], g["owner"] or "-",
                     ",".join(i[1] for i in g["issues"]) or "-"])
    table = render_markdown_table(rows, ["级别", "字段", "分级", "责任方", "问题码"])
    frows = []
    for f in sorted(flow_issues, key=lambda x: DATA_LEVEL_ORDER.get(x["level_flag"], 9)):
        frows.append([f["level_flag"], f["route"], f["sink"], f["max_level"],
                      ",".join(i[1] for i in f["issues"]) or "-"])
    ftable = render_markdown_table(frows, ["级别", "流转路径", "出口", "最高分级", "问题码"])
    return table + "\n\n" + ftable


def process(text):
    """数据分级流转核验：解析字段分级与流转声明 → 核验加密/掩码/责任方 → 分级输出"""
    try:
        fields, flows, policy = parse_data_declarations(text)
        graded, flow_issues, referenced, covered = grade_data_flow(fields, flows, policy)
        high = [g["name"] for g in graded if g["level_flag"] == "HIGH"]
        unlabeled = [f for f in referenced if f not in {x["name"] for x in fields}]
        return {
            "ok": True,
            "field_count": len(fields),
            "flow_count": len(flows),
            "level_distribution": {lv: sum(1 for g in graded if g["level"] == lv) for lv in DATA_LEVELS},
            "unlabeled_referenced_fields": unlabeled,
            "flow_coverage_pct": rate(len(covered), len(referenced)),
            "high_risk_fields": high,
            "flow_high_risk": [f["route"] for f in flow_issues if f["level_flag"] == "HIGH"],
            "per_field": graded,
            "per_flow": flow_issues,
            "report": render_data_report(graded, flow_issues),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "field_count": 0, "per_field": [], "per_flow": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="sec-data-classification-auditor", description="--variant")
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
