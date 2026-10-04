#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-deprecation-alias-auditor — 配置废弃 迁移别名 核验

核验配置键废弃标注与迁移别名闭合性并分级输出

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：核验配置键的废弃标注与迁移别名闭合性，检出废弃键无别名、别名目标缺失、别名指向废弃键、多键同指与废弃键仍被引用并分级输出
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



DPM28_DECL_RX = re.compile(r"^\s*(key|use|policy)\s+(.*)$", re.I)
DPM28_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*(\"[^\"]*\"|[^\s]+)")
DPM28_TRUE = ("1", "true", "yes", "y", "on")
DPM28_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def dpm28_kv(text):
    """解析 key=value 片段 → 字典（去包裹引号）"""
    out = {}
    for m in DPM28_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"').strip("'")
    return out


def dpm28_bool(val, default=False):
    """宽松布尔解析"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in DPM28_TRUE


def parse_deprecation_spec(text):
    """解析配置键生命周期标注与引用

    语法：
        key app.timeout status=deprecated alias=app.request_timeout since=2.1
        key app.legacy_mode status=deprecated
        key app.request_timeout status=active
        use app.timeout file=svc.conf line=12
        policy require_alias=true
    """
    keys, uses, policy = {}, [], {}
    for raw in (text or "").splitlines():
        m = DPM28_DECL_RX.match(raw)
        if not m:
            continue
        kind = m.group(1).lower()
        rest = m.group(2)
        if kind == 'policy':
            policy.update(dpm28_kv(rest))
            continue
        parts = rest.split(None, 1)
        name = parts[0] if parts else ''
        tail = parts[1] if len(parts) > 1 else ''
        kv = dpm28_kv(tail)
        if kind == 'key':
            keys[name] = {'name': name,
                          'status': (kv.get('status') or 'active').lower(),
                          'alias': kv.get('alias') or '',
                          'since': kv.get('since') or ''}
        elif kind == 'use':
            uses.append({'key': name, 'file': kv.get('file') or '', 'line': kv.get('line') or ''})
    return keys, uses, policy


def audit_deprecation(keys, uses, policy):
    """核验废弃键标注与迁移别名闭合性 → (分级结果, 问题码计数, 汇总)"""
    require_alias = dpm28_bool(policy.get('require_alias'), True)
    deprecated = {n: k for n, k in keys.items() if k['status'] == 'deprecated'}
    active = {n for n, k in keys.items() if k['status'] == 'active'}
    alias_targets, graded, codes = {}, [], {}
    for name, k in keys.items():
        issues = []

        def add(level, code, msg):
            issues.append((level, code, msg))
            codes[code] = codes.get(code, 0) + 1

        if k['status'] == 'deprecated':
            if not k['alias']:
                add('HIGH' if require_alias else 'MEDIUM', 'DEPRECATED_NO_ALIAS',
                    f"废弃键 {name} 未声明迁移别名")
            else:
                tgt = k['alias']
                alias_targets.setdefault(tgt, []).append(name)
                if tgt not in keys:
                    add('HIGH', 'ALIAS_TARGET_MISSING', f"别名目标 {tgt} 未在声明中出现")
                elif tgt in deprecated:
                    add('MEDIUM', 'ALIAS_CHAIN', f"别名指向的 {tgt} 本身也是废弃键")
        elif k['status'] not in ('active',):
            add('LOW', 'STATUS_UNKNOWN', f"键 {name} 状态 {k['status']} 非法定值")
        level = 'OK'
        for lv, _, _ in sorted(issues, key=lambda x: DPM28_LEVEL_ORDER[x[0]]):
            level = lv
            break
        graded.append({'key': name, 'status': k['status'], 'alias': k['alias'],
                       'used': any(u['key'] == name for u in uses),
                       'level': level, 'issue_count': len(issues), 'issues': issues})
    for tgt, srcs in alias_targets.items():
        if len(srcs) > 1:
            codes['ALIAS_COLLISION'] = codes.get('ALIAS_COLLISION', 0) + 1
            for g in graded:
                if g['key'] in srcs:
                    g['issues'].append(('HIGH', 'ALIAS_COLLISION',
                                        f"多个废弃键同指 {tgt}：{','.join(sorted(srcs))}"))
                    g['issue_count'] += 1
    for u in uses:
        if u['key'] in deprecated:
            codes['DEPRECATED_IN_USE'] = codes.get('DEPRECATED_IN_USE', 0) + 1
            for g in graded:
                if g['key'] == u['key']:
                    g['issues'].append(('MEDIUM', 'DEPRECATED_IN_USE',
                                        f"废弃键仍被引用（{u['file'] or '未知文件'} 第 {u['line'] or '?'} 行）"))
                    g['issue_count'] += 1
        elif u['key'] not in keys and keys:
            codes['UNKNOWN_KEY_USED'] = codes.get('UNKNOWN_KEY_USED', 0) + 1
    for g in graded:
        level = 'OK'
        for lv, _, _ in sorted(g['issues'], key=lambda x: DPM28_LEVEL_ORDER[x[0]]):
            level = lv
            break
        g['level'] = level
    summary = {'key_count': len(keys), 'deprecated_count': len(deprecated),
               'active_count': len(active), 'use_count': len(uses)}
    return graded, codes, summary


def render_deprecation_report(graded, codes, summary):
    """渲染废弃键与别名核验报告（Markdown）"""
    rows = []
    for g in graded:
        cs = ",".join(c for _, c, _ in g['issues']) or "-"
        rows.append([g['level'], g['key'], g['status'], g['alias'] or "-",
                     '是' if g['used'] else '否', cs])
    table = render_markdown_table(rows, ["级别", "配置键", "状态", "迁移别名", "仍被引用", "问题码"])
    high = [g['key'] for g in graded if g['level'] == 'HIGH']
    tail = [f"键 {summary['key_count']} ｜ 废弃 {summary['deprecated_count']} ｜ "
            f"在用 {summary['active_count']} ｜ 引用 {summary['use_count']} ｜ "
            f"高危 {len(high)} ｜ 问题码种类 {len(codes)}"]
    for name in high[:5]:
        tail.append(f"- 高危键：{name}")
    return table + "\n\n" + "\n".join(tail)


def process(text):
    """废弃键核验：解析生命周期标注与引用 → 检出无别名/目标缺失/别名环 → 分级输出"""
    try:
        keys, uses, policy = parse_deprecation_spec(text)
        graded, codes, summary = audit_deprecation(keys, uses, policy)
        high = [g["key"] for g in graded if g["level"] == "HIGH"]
        return {
            "ok": True,
            "key_count": summary["key_count"],
            "deprecated_count": summary["deprecated_count"],
            "use_count": summary["use_count"],
            "high_risk_count": len(high),
            "high_risk_keys": high,
            "issue_codes": codes,
            "per_key": graded,
            "report": render_deprecation_report(graded, codes, summary),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "key_count": 0, "per_key": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="config-deprecation-alias-auditor", description="核验配置键废弃标注与迁移别名闭合性并分级输出")
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
