#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dep-version-auditor — 依赖清单 版本风险 升级规划

解析依赖清单与版本约束、比对风险版本并输出升级清单

领域：安全审计/静态分析（平台 13 分双上榜）
能力：解析依赖清单与版本约束、比对已知风险版本、输出分级升级清单
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



VERSION_RISK = {
    "urllib3": ("1.26.18", "早期版本存在已公开的传输层问题"),
    "requests": ("2.31.0", "早期版本存在已公开的请求处理问题"),
    "pyyaml": ("5.4", "早期版本存在已公开的解析处理问题"),
    "lodash": ("4.17.21", "早期版本存在已公开的对象合并问题"),
    "log4j": ("2.17.2", "早期版本存在已公开的解析处理问题"),
    "django": ("3.2.25", "早期版本存在已公开的输入处理问题"),
    "flask": ("2.3.2", "早期版本存在已公开的会话处理问题"),
}

SPEC_RX = re.compile(r"^([A-Za-z0-9_.\-]+)(==|>=|<=|~=|\^|>|<)?([0-9][0-9A-Za-z.\-]*)?")


def version_tuple(value):
    """版本号 → 可比较元组（只取数字段）"""
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(p) for p in parts[:4]) if parts else (0,)


def compare_version(left, right):
    """版本比较：left 小于 right 返回 -1，相等 0，大于 1"""
    a, b = version_tuple(left), version_tuple(right)
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return -1 if a < b else (1 if a > b else 0)


def parse_manifest(text):
    """解析依赖清单：每行『名称 运算符 版本』，兼容 requirements 与 yaml 风格"""
    rows, unparsed = [], []
    for lineno, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = SPEC_RX.match(s.replace(":", "==").replace(" ", "").replace("\t", ""))
        if not m or not m.group(1):
            unparsed.append({"line": lineno, "raw": s[:60]})
            continue
        rows.append({"name": m.group(1), "op": m.group(2) or "",
                     "version": m.group(3) or "", "line": lineno})
    return rows, unparsed


def rank_dependency_risk(rows):
    """逐项判定：低于已知安全线判 HIGH；浮动或缺失版本判 MEDIUM/LOW"""
    out = []
    for r in rows:
        safe, reason = VERSION_RISK.get(r["name"].lower(), ("", ""))
        if safe and r["version"] and compare_version(r["version"], safe) < 0:
            out.append({**r, "level": "HIGH", "reason": reason, "safe_from": safe})
        elif not r["version"]:
            out.append({**r, "level": "MEDIUM" if r["op"] else "LOW",
                        "reason": "未锁定版本，构建结果不可复现" if r["op"] else "缺少版本号，无法核对",
                        "safe_from": safe})
    return out


def process(text):
    """V3：依赖解析 → 版本比对 → 风险分级与升级清单"""
    rows, unparsed = parse_manifest(text)
    if not rows:
        return {"ok": False, "error": "未解析到依赖项（需『名称 运算符 版本』格式）"}
    risky = rank_dependency_risk(rows)
    high = [x for x in risky if x["level"] == "HIGH"]
    plan = [f"{i}. {r['name']} {r['op']}{r['version']} → 升级到 ≥{r['safe_from'] or '最新稳定版'}（{r['reason']}）"
            for i, r in enumerate(high[:10], 1)]
    return {"ok": True, "variant": "V3",
            "conclusion": f"解析 {len(rows)} 项依赖，命中风险 {len(risky)} 项（HIGH {len(high)}）",
            "package_count": len(rows), "risk_count": len(risky), "high_count": len(high),
            "risky": [f"{r['name']}{r['op']}{r['version']}｜{r['level']}｜{r['reason']}" for r in risky[:12]],
            "unparsed": unparsed[:10], "upgrade_plan": plan, "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="dep-version-auditor", description="解析依赖清单与版本约束、比对风险版本并输出升级清单")
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
