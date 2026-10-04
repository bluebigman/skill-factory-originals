#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dep-baseline-auditor — 依赖基线 组件比对 升级排序

解析依赖清单并与安全基线比对，输出待升级组件与升级顺序

领域：安全审计/静态分析（平台 13 分双上榜）
能力：解析依赖清单并与安全基线比对，输出待升级组件与升级顺序
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



DEP_SPEC_RX = [
    re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([0-9][0-9A-Za-z.\-]*)"),
    re.compile(r"[\"']([A-Za-z0-9_.\-]+)[\"']\s*:\s*[\"']\^?~?([0-9][0-9A-Za-z.\-]*)[\"']"),
    re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*:\s*([0-9][0-9A-Za-z.\-]*)\s*$"),
]

DEP_RISK_RULES = [
    ("requests", "2.32.0", "旧版本存在凭据经跨域重定向泄露的缺陷"),
    ("urllib3", "2.2.2", "旧版本代理环境变量与重定向处理存在缺陷"),
    ("jinja2", "3.1.4", "旧版本沙箱属性链可达"),
    ("cryptography", "42.0.7", "旧版本部分后端密钥处理存在缺陷"),
    ("pyyaml", "6.0.1", "全加载接口旧版本存在反序列化面"),
    ("lodash", "4.17.21", "原型污染修复基线"),
    ("axios", "1.7.4", "服务端请求伪造防护基线"),
    ("log4j-core", "2.17.1", "远程代码执行修复基线"),
]


def version_tuple(v):
    """版本号 → 可比较四元组（非数字段截断，缺位补 0）"""
    parts = []
    for seg in str(v or "").split("."):
        num = ""
        for ch in seg:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    parts = (parts + [0, 0, 0, 0])[:4]
    return tuple(parts)


def older_than(cur, base):
    return version_tuple(cur) < version_tuple(base)


def parse_dependencies(text):
    """从锁文件/依赖清单抽取 包名→版本（三格式兼容，同名取最低版本）"""
    found = {}
    for line in (text or "").splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith("#"):
            continue
        for rx in DEP_SPEC_RX:
            m = rx.search(line)
            if not m:
                continue
            name, ver = m.group(1).lower(), m.group(2)
            if name not in found or older_than(ver, found[name]):
                found[name] = ver
            break
    return found


def assess_dependency_risk(deps):
    """与内置安全基线比对，输出需升级项（含缺口说明）"""
    risks = []
    for name, base, why in DEP_RISK_RULES:
        cur = deps.get(name)
        if cur is None or not older_than(cur, base):
            continue
        risks.append({"pkg": name, "current": cur, "baseline": base, "reason": why})
    return sorted(risks, key=lambda x: x["pkg"])


def dependency_upgrade_plan(risks):
    """按包名字典序给出升级顺序（同批次可并行）"""
    return ["{0}. {1} {2} → ≥{3}：{4}".format(i, r["pkg"], r["current"], r["baseline"], r["reason"])
            for i, r in enumerate(risks[:10], 1)]


def process(text):
    """V7：依赖清单解析 → 安全基线比对 → 升级顺序"""
    deps = parse_dependencies(text)
    risks = assess_dependency_risk(deps)
    plan = dependency_upgrade_plan(risks)
    conclusion = ("解析依赖 {0} 个，{1} 个低于安全基线，须按序升级".format(len(deps), len(risks))
                  if risks else "解析依赖 {0} 个，未命中安全基线风险".format(len(deps)))
    return {"ok": True, "variant": "V7", "conclusion": conclusion,
            "dependency_count": len(deps), "risks": risks, "upgrade_plan": plan}



def build_parser():
    p = argparse.ArgumentParser(prog="dep-baseline-auditor", description="解析依赖清单并与安全基线比对，输出待升级组件与升级顺序")
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
