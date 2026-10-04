#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""infra-permission-audit — 容器配置 权限面 暴露端口核验

检查容器与基础设施配置的特权与挂载权限面问题

领域：安全审计/静态分析（平台 13 分双上榜）
能力：检查容器与基础设施配置的特权、网络与挂载权限面、输出分级整改清单
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



INFRA_CHECKS = [
    ("特权容器", re.compile(r"privileged\s*[:=]\s*true", re.I), "HIGH", "关闭特权模式，按需授予单一内核能力"),
    ("宿主机网络", re.compile(r"network_mode\s*[:=]\s*[\"']?host", re.I), "HIGH", "改用独立网络并显式声明端口映射"),
    ("运行时套接字挂载", re.compile(r"/var/run/docker\.sock"), "HIGH", "移除运行时套接字挂载，改用受限代理"),
    ("全地址监听", re.compile(r"0\.0\.0\.0:(\d+)"), "MEDIUM", "限定监听地址或经反向代理收敛入口"),
    ("以特权用户运行", re.compile(r"(?i)^\s*user\s*[:=]\s*[\"']?(root|0)[\"']?\s*$"), "MEDIUM", "改为非特权用户并设置只读根文件系统"),
    ("宿主机路径挂载", re.compile(r"(hostPath|/etc/|/root/)"), "MEDIUM", "改用命名卷并限定读写范围"),
    ("调试入口开启", re.compile(r"(?i)(debug|admin)\s*[:=]\s*true"), "LOW", "生产配置关闭调试入口"),
]

PORT_RX = re.compile(r"[\"']?(\d{2,5}):(\d{2,5})[\"']?")


def scan_infra(text):
    """逐行匹配基础设施配置的权限面问题"""
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rx, level, fix in INFRA_CHECKS:
            if rx.search(line):
                findings.append({"line": lineno, "item": name, "level": level,
                                 "fix": fix, "snippet": line.strip()[:100]})
    return findings


def infra_rating(findings):
    """按最高级别给出总体结论"""
    weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    worst = max((weights.get(f["level"], 0) for f in findings), default=0)
    return {3: "BLOCK", 2: "WARN", 1: "INFO", 0: "PASS"}[worst]


def exposed_ports(text):
    """抽取端口映射并标记是否绑定到全地址"""
    out = []
    for m in PORT_RX.finditer(text):
        window = text[max(0, m.start() - 40):m.start()]
        out.append({"host": m.group(1), "container": m.group(2),
                    "wildcard": "0.0.0.0" in window})
    return out


def infra_fix_plan(findings):
    """整改清单：按级别排序、同项去重"""
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    seen, plan = set(), []
    for f in sorted(findings, key=lambda x: (order.get(x["level"], 3), x["line"])):
        if f["item"] in seen:
            continue
        seen.add(f["item"])
        plan.append(f"【{f['level']}】{f['item']}（第 {f['line']} 行）→ {f['fix']}")
    return plan


def process(text):
    """V5：基础设施配置权限面检查 → 评级 → 整改清单"""
    findings = scan_infra(text)
    rating = infra_rating(findings)
    ports = exposed_ports(text)
    return {"ok": bool(text.strip()), "variant": "V5",
            "conclusion": f"命中 {len(findings)} 项权限面问题，总体评级 {rating}",
            "rating": rating, "finding_count": len(findings),
            "findings": [f"第 {f['line']} 行【{f['level']}】{f['item']}" for f in findings[:12]],
            "ports": ports, "fix_plan": infra_fix_plan(findings), "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="infra-permission-audit", description="检查容器与基础设施配置的特权与挂载权限面问题")
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
