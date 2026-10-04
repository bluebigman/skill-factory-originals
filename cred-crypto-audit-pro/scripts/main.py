#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cred-exposure-scanner — 凭据泄露 密钥暴露 明文扫描

扫描源码与配置中的明文凭据、脱敏后按级别输出整改清单

领域：安全审计/静态分析（平台 13 分双上榜）
能力：扫描源码与配置中的明文凭据与密钥、脱敏后按风险级别输出整改清单
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



CRED_RULES = [
    ("云访问密钥", re.compile(r"\b(A3T[A-Z0-9]|AKIA|ASIA)[A-Z0-9]{12,}\b"), "HIGH"),
    ("私钥文件头", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "HIGH"),
    ("访问令牌赋值", re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key)\b\s*[:=]\s*[\"'][^\"']{8,}[\"']"), "HIGH"),
    ("口令赋值", re.compile(r"(?i)\b(passwd|password|pwd|passphrase)\b\s*[:=]\s*[\"'][^\"']{6,}[\"']"), "HIGH"),
    ("连接串内嵌凭据", re.compile(r"(?i)(mysql|postgres|postgresql|redis|mongodb)://[^:\s/]+:[^@\s/]+@"), "HIGH"),
    ("疑似占位凭据", re.compile(r"(?i)\b(token|secret|key)\b\s*[:=]\s*[\"'](test|demo|dev|example|changeme)[^\"']*[\"']"), "MEDIUM"),
]


def mask_secret(value, keep=2):
    """凭据脱敏：仅保留首尾少量字符，中间以星号替代（输出可安全归档）"""
    s = str(value or "")
    if len(s) <= keep * 2:
        return "*" * len(s)
    return s[:keep] + "*" * max(3, len(s) - keep * 2) + s[-keep:]


def extract_credential(text):
    """逐行抽取凭据候选，只保留脱敏后的形式（不落原值）"""
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rx, level in CRED_RULES:
            m = rx.search(line)
            if not m:
                continue
            raw = m.group(0)
            hit = re.search(r"[\"']([^\"']{6,})[\"']", raw)
            secret = hit.group(1) if hit else raw
            out.append({"line": lineno, "kind": name, "level": level,
                        "masked": mask_secret(secret), "column": m.start() + 1})
    return out


def summarize_credentials(items):
    """按类型与级别汇总（供交付报告直接引用）"""
    by_kind, by_level = {}, {}
    for it in items:
        by_kind[it["kind"]] = by_kind.get(it["kind"], 0) + 1
        by_level[it["level"]] = by_level.get(it["level"], 0) + 1
    return {"by_kind": by_kind, "by_level": by_level}


def credential_remediation(items):
    """按级别排序的整改顺序（先高危）"""
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    ranked = sorted(items, key=lambda x: (order.get(x["level"], 3), x["line"]))
    plan = []
    for i, it in enumerate(ranked[:10], 1):
        plan.append(f"{i}. 第 {it['line']} 行【{it['kind']}｜{it['level']}】→ 移入环境变量或密钥托管，并轮换已暴露值")
    return plan


def process(text):
    """V1：凭据候选抽取 → 脱敏 → 分级整改清单"""
    items = extract_credential(text)
    stat = summarize_credentials(items)
    conclusion = (f"发现 {len(items)} 处凭据候选，其中 HIGH {stat['by_level'].get('HIGH', 0)} 处"
                  if items else "未发现明文凭据候选")
    return {"ok": True, "variant": "V1", "conclusion": conclusion,
            "finding_count": len(items), "by_kind": stat["by_kind"], "by_level": stat["by_level"],
            "masked_samples": [it["masked"] + f"（第{it['line']}行/{it['kind']}）" for it in items[:8]],
            "remediation": credential_remediation(items), "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="cred-exposure-scanner", description="扫描源码与配置中的明文凭据、脱敏后按级别输出整改清单")
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
