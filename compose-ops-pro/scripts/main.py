#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose-service-verifier — 编排依赖 服务核验 端口冲突

解析 compose 服务块，核验依赖缺失、依赖环与端口冲突

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：解析 Nginx/邮件/网络/仓库等配置文本，抽取关键指令、做重复与冲突检查、输出结构化清单
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



SERVICE_RE = re.compile(r"^\s{2}([A-Za-z0-9_\-]+):\s*$")
SECTION_RE = re.compile(r"^\s{4,}(ports|depends_on|environment):\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^\s{6,}-\s*(.+)$")
IMAGE_RE = re.compile(r"^\s{4,}image:\s*(.+)$")


def strip_quotes(value):
    """去掉配置值两端的引号（单引号或双引号）"""
    v = (value or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def parse_service_blocks(text):
    """解析 compose 风格服务块（缩进感知，纯离线实现，不依赖 yaml 库）"""
    services, cur, section = {}, None, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        ms = SERVICE_RE.match(line)
        if ms and not line.startswith("   "):
            cur = ms.group(1)
            services[cur] = {"image": None, "ports": [], "depends_on": [], "environment": []}
            section = None
            continue
        if cur is None:
            continue
        mimg = IMAGE_RE.match(line)
        if mimg:
            services[cur]["image"] = strip_quotes(mimg.group(1))
            continue
        msec = SECTION_RE.match(line)
        if msec:
            section = msec.group(1)
            rest = msec.group(2).strip()
            if rest.startswith("[") and rest.endswith("]"):
                services[cur][section].extend(
                    strip_quotes(v) for v in rest[1:-1].split(",") if v.strip())
            continue
        mli = LIST_ITEM_RE.match(line)
        if mli and section:
            services[cur][section].append(strip_quotes(mli.group(1)))
    return services


def detect_missing_deps(services):
    """依赖了未定义的服务：编排启动即失败的头号原因"""
    issues = []
    for name, cfg in services.items():
        for dep in cfg.get("depends_on", []):
            if dep not in services:
                issues.append({"level": "HIGH", "service": name,
                               "msg": "依赖的服务不存在：{}".format(dep)})
    return issues


def detect_dep_cycles(services):
    """依赖环检测（DFS 三色标记）"""
    color, cycles = {}, []

    def walk(node, stack):
        color[node] = 1
        for dep in services.get(node, {}).get("depends_on", []):
            if dep not in services:
                continue
            if color.get(dep, 0) == 1:
                cycles.append(stack[stack.index(dep):] + [dep] if dep in stack else stack + [dep])
            elif color.get(dep, 0) == 0:
                walk(dep, stack + [dep])
        color[node] = 2

    for name in list(services):
        if color.get(name, 0) == 0:
            walk(name, [name])
    return cycles


def collect_port_bindings(services):
    """宿主端口占用表 + 冲突检测（同一宿主端口被两个服务占用）"""
    binding, conflicts = {}, []
    for name, cfg in services.items():
        for spec in cfg.get("ports", []):
            host = spec.split(":")[0]
            if host in binding and binding[host] != name:
                conflicts.append({"level": "HIGH", "port": host,
                                  "services": sorted([binding[host], name])})
            binding[host] = name
    return binding, conflicts


def render_service_report(services, issues, cycles, binding):
    """编排体检报告：结论在前，明细在后"""
    rows = [[n, c.get("image") or "(未声明)", len(c.get("ports", [])),
             ",".join(c.get("depends_on", [])) or "-"]
            for n, c in sorted(services.items())]
    return {
        "ok": not issues and not cycles,
        "conclusion": "服务依赖闭合、端口无冲突" if not issues and not cycles
                      else "发现 {} 项依赖问题、{} 个依赖环".format(len(issues), len(cycles)),
        "service_count": len(services),
        "services": {n: {"image": c.get("image"), "ports": c.get("ports"),
                         "depends_on": c.get("depends_on")} for n, c in sorted(services.items())},
        "port_binding": binding,
        "dependency_issues": issues,
        "cycles": cycles,
        "service_table_md": render_markdown_table(
            rows, ["服务", "镜像", "端口数", "依赖"]),
        "next_action": "补齐缺失依赖或去掉多余依赖后重新校验" if issues or cycles
                       else "依赖闭合，可进入部署变更评审",
    }


def process(text):
    """V4：服务块解析 → 依赖缺失/环 → 端口冲突 → 编排体检报告"""
    services = parse_service_blocks(text)
    if not services:
        return {"ok": False, "error": "未解析到服务块（需 services 下两空格缩进块）", "variant": "V4"}
    issues = detect_missing_deps(services)
    cycles = detect_dep_cycles(services)
    binding, conflicts = collect_port_bindings(services)
    out = render_service_report(services, issues + conflicts, cycles, binding)
    out["variant"] = "V4"
    out["content_id"] = stable_id(text)
    return out



def build_parser():
    p = argparse.ArgumentParser(prog="compose-service-verifier", description="解析 compose 服务块，核验依赖缺失、依赖环与端口冲突")
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
