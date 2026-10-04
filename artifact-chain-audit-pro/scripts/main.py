#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""artifact-provenance-verifier — 构建产物 来源追溯 签名核验

核验产物来源地址、内容摘要与署名、输出追溯缺口与分级整改清单

领域：安全审计/静态分析（平台 13 分双上榜）
能力：核验构建产物的来源地址、内容摘要、署名与版本锁定情况，输出追溯缺口与分级整改清单
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



ART_LINE_RX = re.compile(r"^\s*artifact\b(.*)$", re.I)
ART_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-]*)\s*=\s*([^\s]+)")
ART_UNPINNED = ("latest", "dev", "main", "master", "*", "head", "snapshot")
ART_WEAK_DIGEST = ("md5", "sha1", "crc32")
ART_HEX_RX = re.compile(r"^[0-9a-f]{32,64}$")


def parse_artifacts(text):
    """解析构建产物清单行"""
    items = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        m = ART_LINE_RX.match(raw)
        if not m:
            continue
        f = {}
        for k, v in ART_KV_RX.findall(m.group(1)):
            f[k.lower()] = v.strip("\"'")
        items.append({"line": lineno,
                      "name": f.get("name") or f.get("file") or "-",
                      "version": f.get("version", ""),
                      "source": f.get("source") or f.get("url") or "",
                      "sha256": (f.get("sha256") or f.get("digest") or "").lower(),
                      "digest_algo": (f.get("algo") or f.get("digest_algo") or "").lower(),
                      "signer": f.get("signer") or f.get("signed_by") or "",
                      "license": f.get("license", "")})
    return items


def verify_artifact(a):
    """单产物的来源与摘要核验"""
    issues = []
    if not a["source"]:
        issues.append({"level": "HIGH", "item": "来源缺失",
                       "detail": a["name"] + " 未声明 source 来源地址，无法追溯产出位置"})
    else:
        low = a["source"].lower()
        if not low.startswith("https://"):
            issues.append({"level": "MEDIUM", "item": "传输方式",
                           "detail": a["name"] + " 来源使用非 https 地址：" + a["source"]})
    if not a["sha256"]:
        issues.append({"level": "HIGH", "item": "摘要缺失",
                       "detail": a["name"] + " 未提供内容摘要，无法校验完整性"})
    elif not ART_HEX_RX.match(a["sha256"]):
        issues.append({"level": "MEDIUM", "item": "摘要格式",
                       "detail": a["name"] + " 摘要非 32-64 位十六进制：" + a["sha256"]})
    if a["digest_algo"] in ART_WEAK_DIGEST:
        issues.append({"level": "HIGH", "item": "摘要强度",
                       "detail": a["name"] + " 使用 " + a["digest_algo"] +
                                 " 摘要，须换用 sha256 及以上"})
    if not a["signer"]:
        issues.append({"level": "MEDIUM", "item": "署名缺失",
                       "detail": a["name"] + " 未声明 signer 署名主体，无法确认产出方"})
    ver = (a["version"] or "").lower()
    if not ver:
        issues.append({"level": "MEDIUM", "item": "版本未锁定",
                       "detail": a["name"] + " 未声明 version"})
    elif ver in ART_UNPINNED:
        issues.append({"level": "MEDIUM", "item": "版本未锁定",
                       "detail": a["name"] + " 版本取浮动值 " + a["version"] +
                                 "，同一构建不可复现"})
    if not a["license"]:
        issues.append({"level": "LOW", "item": "许可未标注",
                       "detail": a["name"] + " 未声明 license，分发前须补齐"})
    return issues


def artifact_priority(artifacts):
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    rows = []
    for a in artifacts:
        for it in a["issues"]:
            rows.append((a["line"], a["name"], it["level"], it["item"], it["detail"]))
    return sorted(rows, key=lambda r: (order.get(r[2], 3), r[0]))


def process(text):
    """V11：产物清单解析 → 来源/摘要/署名核验 → 追溯缺口汇总"""
    artifacts = parse_artifacts(text)
    for a in artifacts:
        a["issues"] = verify_artifact(a)
    rows = artifact_priority(artifacts)
    total = len(rows)
    high = len([r for r in rows if r[2] == "HIGH"])
    gaps = [a["name"] for a in artifacts if not a["sha256"] or not a["source"]]
    if artifacts:
        conclusion = "核验产物 {0} 个，命中问题 {1} 项（高危 {2} 项），追溯缺口产物 {3} 个".format(
            len(artifacts), total, high, len(gaps))
    else:
        conclusion = ("未识别到 artifact 声明行（示例：artifact name=app.tgz version=1.2.3 "
                      "source=https://dl.example.com/app.tgz sha256=<64位十六进制> "
                      "algo=sha256 signer=release-bot license=MIT）")
    return {"ok": True, "variant": "V11", "conclusion": conclusion,
            "artifact_count": len(artifacts), "issue_count": total,
            "high_risk_count": high, "trust_gaps": gaps,
            "findings": [{"line": r[0], "artifact": r[1], "level": r[2],
                          "item": r[3], "detail": r[4]} for r in rows]}



def build_parser():
    p = argparse.ArgumentParser(prog="artifact-provenance-verifier", description="核验产物来源地址、内容摘要与署名、输出追溯缺口与分级整改清单")
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
