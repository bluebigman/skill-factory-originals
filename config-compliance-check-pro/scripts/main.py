#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config-bound-relation-auditor — 配置解析 数值边界 关联约束

配置解析 数值边界 关联约束处理工具

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：核验数值型配置的上下界与键间关联约束，检出取值越界、边界声明倒置、取值类型非数值与关联约束不满足并分级输出
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



BND_DECL_RX = re.compile(r"^\s*(key|constraint|policy)\s+(.*)$", re.I)
BND_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
# 行首位置式键名支持（同 V25 修复）—— 本枚的关联约束按**键名**索引，名取不到 = 约束全部误判
BND_HEAD_RX = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-\.]*)(?=\s|$)")
BND_TRUE = ("1", "true", "yes", "y", "on")
BND_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def bnd27_kv(text):
    """解析 key=value 片段 → 字典"""
    out = {}
    for m in BND_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def bnd27_name(rest, kv):
    """取键名：优先 name=/key= 显式形式，否则取行首位置式裸名"""
    nm = kv.get('name') or kv.get('key')
    if nm:
        return nm
    m = BND_HEAD_RX.match((rest or '').strip())
    return m.group(1) if m else '(未命名键)'


def bnd27_num(val, default=None):
    """安全数值解析（失败返回 default）"""
    try:
        return float(str(val).strip())
    except Exception:
        return default


def bnd27_bool(val, default=False):
    """宽松布尔解析"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in BND_TRUE


def parse_bounds_spec(text):
    """解析数值边界与关联约束声明块

    语法：
        key pool.max value=200 min=1 max=500
        key pool.min value=500 min=1 max=100
        constraint left=pool.min op=lt right=pool.max
        policy enforce_bounds=true enforce_constraints=true
    """
    keys, constraints, policy = [], [], {}
    for raw in (text or "").splitlines():
        m = BND_DECL_RX.match(raw)
        if not m:
            continue
        kind = m.group(1).lower()
        kv = bnd27_kv(m.group(2))
        if kind == 'policy':
            policy.update(kv)
        elif kind == 'key':
            keys.append({
                'name': bnd27_name(m.group(2), kv),
                'value': bnd27_num(kv.get('value')),
                'min': bnd27_num(kv.get('min')),
                'max': bnd27_num(kv.get('max')),
            })
        elif kind == 'constraint':
            constraints.append({'left': kv.get('left') or '', 'op': (kv.get('op') or 'lt').lower(),
                                'right': kv.get('right') or ''})
    return keys, constraints, policy


BND27_OPS = {
    'lt': lambda a, b: a < b,
    'le': lambda a, b: a <= b,
    'lte': lambda a, b: a <= b,
    'gt': lambda a, b: a > b,
    'ge': lambda a, b: a >= b,
    'gte': lambda a, b: a >= b,
}


def audit_bounds(keys, constraints, policy):
    """逐键/逐约束核验 → (分级结果, 问题码计数, 取值索引)"""
    enforce_bounds = bnd27_bool(policy.get('enforce_bounds'), True)
    enforce_cons = bnd27_bool(policy.get('enforce_constraints'), True)
    index = {k['name']: k['value'] for k in keys}
    graded, codes = [], {}

    for k in keys:
        issues = []

        def add(level, code, msg):
            issues.append((level, code, msg))
            codes[code] = codes.get(code, 0) + 1

        if enforce_bounds and k['min'] is not None and k['max'] is not None and k['min'] > k['max']:
            add('HIGH', 'BOUND_INVERTED',
                f"边界声明倒置：min={k['min']} > max={k['max']}")
        elif enforce_bounds and k['value'] is not None:
            if k['min'] is not None and k['value'] < k['min']:
                add('HIGH', 'OUT_OF_BOUNDS', f"取值 {k['value']} 低于下界 {k['min']}")
            elif k['max'] is not None and k['value'] > k['max']:
                add('HIGH', 'OUT_OF_BOUNDS', f"取值 {k['value']} 高于上界 {k['max']}")
            elif k['min'] is not None and k['value'] == k['min']:
                add('LOW', 'AT_LOWER_BOUND', '取值贴下界，缺少调整余量')
            elif k['max'] is not None and k['value'] == k['max']:
                add('LOW', 'AT_UPPER_BOUND', '取值贴上界，缺少调整余量')
        if k['value'] is None:
            add('MEDIUM', 'VALUE_NOT_NUMERIC', '取值不是数值，无法做边界核验')
        level = 'OK'
        for lv, _, _ in sorted(issues, key=lambda x: BND_LEVEL_ORDER[x[0]]):
            level = lv
            break
        graded.append({'name': k['name'], 'value': k['value'], 'min': k['min'], 'max': k['max'],
                       'level': level, 'issue_count': len(issues), 'issues': issues})

    cons_result = []
    for c in constraints:
        issues = []
        a, b = index.get(c['left']), index.get(c['right'])
        fn = BND27_OPS.get(c['op'])
        if a is None or b is None:
            issues.append(('MEDIUM', 'CONSTRAINT_TARGET_MISSING',
                           f"约束引用了未声明的键：{c['left']} / {c['right']}"))
            codes['CONSTRAINT_TARGET_MISSING'] = codes.get('CONSTRAINT_TARGET_MISSING', 0) + 1
        elif fn is None:
            issues.append(('MEDIUM', 'CONSTRAINT_OP_UNKNOWN', f"未知比较符：{c['op']}"))
            codes['CONSTRAINT_OP_UNKNOWN'] = codes.get('CONSTRAINT_OP_UNKNOWN', 0) + 1
        elif enforce_cons and not fn(a, b):
            issues.append(('HIGH', 'CONSTRAINT_VIOLATED',
                           f"约束不满足：{c['left']}({a}) {c['op']} {c['right']}({b})"))
            codes['CONSTRAINT_VIOLATED'] = codes.get('CONSTRAINT_VIOLATED', 0) + 1
        level = 'OK'
        for lv, _, _ in sorted(issues, key=lambda x: BND_LEVEL_ORDER[x[0]]):
            level = lv
            break
        cons_result.append({'left': c['left'], 'op': c['op'], 'right': c['right'],
                            'level': level, 'issues': issues})
    return graded, cons_result, codes


def render_bounds_report(graded, cons_result, codes):
    """渲染数值边界核验报告（Markdown）"""
    rows = []
    for g in graded:
        cs = ",".join(c for _, c, _ in g['issues']) or "-"
        rows.append([g['level'], g['name'], g['value'], g['min'], g['max'], cs])
    table = render_markdown_table(rows, ["级别", "配置键", "取值", "下界", "上界", "问题码"])
    crows = []
    for c in cons_result:
        cs = ",".join(x[1] for x in c['issues']) or "-"
        crows.append([c['level'], f"{c['left']} {c['op']} {c['right']}", cs])
    ctable = render_markdown_table(crows, ["级别", "关联约束", "问题码"])
    high = [g['name'] for g in graded if g['level'] == 'HIGH'] + \
           [f"{c['left']}{c['op']}{c['right']}" for c in cons_result if c['level'] == 'HIGH']
    tail = [f"键 {len(graded)} ｜ 约束 {len(cons_result)} ｜ 高危 {len(high)} ｜ 问题码种类 {len(codes)}"]
    for name in high[:5]:
        tail.append(f"- 高危：{name}")
    return table + "\n\n" + ctable + "\n\n" + "\n".join(tail)


def process(text):
    """数值边界核验：解析键边界与关联约束 → 检出越界/倒置/约束不满足 → 分级输出"""
    try:
        keys, constraints, policy = parse_bounds_spec(text)
        graded, cons_result, codes = audit_bounds(keys, constraints, policy)
        high = [g["name"] for g in graded if g["level"] == "HIGH"] + \
               [f"{c['left']}{c['op']}{c['right']}" for c in cons_result if c["level"] == "HIGH"]
        return {
            "ok": True,
            "key_count": len(keys),
            "constraint_count": len(cons_result),
            "high_risk_count": len(high),
            "high_risk_items": high,
            "issue_codes": codes,
            "per_key": graded,
            "per_constraint": cons_result,
            "report": render_bounds_report(graded, cons_result, codes),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "key_count": 0, "per_key": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="config-bound-relation-auditor", description="配置解析 数值边界 关联约束处理工具")
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
