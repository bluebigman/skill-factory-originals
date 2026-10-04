#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backup-exposure-auditor — 备份与暴露面 核验

核验自托管环境的备份策略与对外暴露声明。检出保留期为 0、未验证恢复、无异地副本、暴露公网与缺少鉴权并分级输出。

领域：自托管 / AI 环境部署（雷达标的 AgentVerse-OS 732 star）
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
            ".log", ".csv", ".tsv", ".py", ".js", ".ts", ".sh", ".env", ".tf", ".toml")


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


# ======================= 声明核验引擎（规则表驱动，6 个技能共用同一骨架）=======================

DECL_RX = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_\-]*)\s+(.*)$")
KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
TRUE_VALS = ("1", "true", "yes", "y", "on", "enabled")
LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

TITLE = "备份与暴露面核验"
KINDS = ['backup', 'expose']
KEY_FIELDS = ['name']
POLICY_DEFAULTS = {'min_retention_days': '7'}
RULES = [('BACKUP_RETENTION_MISSING', 'HIGH', 'retention_days', 'missing', None, '未声明保留天数，备份保留策略缺失', ['backup']), ('BACKUP_RETENTION_ZERO', 'HIGH', 'retention_days', 'eq', '0', '保留天数 0 等同于不做备份', ['backup']), ('BACKUP_RETENTION_SHORT', 'MEDIUM', 'retention_days', 'lt', '@min_retention_days', '保留 {retention_days} 天低于下限 {policy[min_retention_days]} 天', ['backup']), ('BACKUP_TARGET_MISSING', 'HIGH', 'target', 'missing', None, '未声明备份目标路径', ['backup']), ('BACKUP_SCHEDULE_MISSING', 'MEDIUM', 'schedule', 'missing', None, '未声明备份周期', ['backup']), ('BACKUP_VERIFY_MISSING', 'HIGH', 'verify', 'falsy', None, '未声明恢复验证（未验证的备份不算备份）', ['backup']), ('BACKUP_NO_OFFSITE', 'MEDIUM', 'offsite', 'falsy', None, '无异地副本，单机故障即全丢', ['backup']), ('BACKUP_UNENCRYPTED', 'MEDIUM', 'encrypt', 'falsy', None, '备份未加密，快照中含凭据明文', ['backup']), ('EXPOSE_PORT_MISSING', 'HIGH', 'port', 'missing', None, '未声明端口，暴露面无法清点', ['expose']), ('EXPOSE_PUBLIC_SCOPE', 'HIGH', 'scope', 'eq', 'public', '暴露到公网，与「不外网暴露」基线冲突', ['expose']), ('EXPOSE_BIND_ALL', 'HIGH', 'scope', 'eq', '0.0.0.0', '监听 0.0.0.0 即对所有网卡开放', ['expose']), ('EXPOSE_NO_AUTH', 'HIGH', 'auth', 'falsy', None, '未声明鉴权方式，匿名可访问', ['expose']), ('EXPOSE_CHANNEL_WEAK', 'MEDIUM', 'proto', 'notin', ['tailscale', 'wireguard', 'ssh-tunnel', 'vpn', 'local'], '接入通道 {proto} 不在加固通道白名单（tailscale/wireguard/ssh-tunnel/vpn/local）', ['expose']), ('EXPOSE_TLS_OFF', 'MEDIUM', 'tls', 'falsy', None, '链路未启用 TLS', ['expose']), ('EXPOSE_RATE_LIMIT_MISSING', 'LOW', 'rate_limit', 'missing', None, '未声明限速，口令试探无成本', ['expose'])]
SUMMARY_KEYS = ['backup', 'expose']


def kv_pairs(text):
    """抽取 key=value 片段（值支持带引号）"""
    out = {}
    for m in KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def as_bool(val, default=False):
    """宽松布尔解析：缺省返回 default，未识别取值按 default 处理"""
    if val is None or str(val).strip() == "":
        return default
    return str(val).strip().lower() in TRUE_VALS


def as_num(val, default=0.0):
    """宽松数值解析：非法值回落 default，绝不抛异常"""
    try:
        return float(str(val).strip())
    except Exception:
        return default


def policy_value(policy, key, default=None):
    """从 policy 取值，缺省回落默认"""
    if key in policy and str(policy[key]).strip() != "":
        return policy[key]
    return default


def parse_decls(text):
    """解析声明块

    语法（每行一条，`#` 起始为注释）：
        <kind> key=value key2=value2 ...
        policy key=value ...
    返回 (items, policy)。items 按出现顺序保留行号。
    """
    items, policy = [], dict(POLICY_DEFAULTS)
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = DECL_RX.match(line)
        if not m:
            continue
        kind = m.group(1).lower()
        kv = kv_pairs(m.group(2))
        if kind == "policy":
            policy.update(kv)
            continue
        if kind not in KINDS:
            continue
        name = ""
        for kf in KEY_FIELDS:
            if kv.get(kf):
                name = kv[kf]
                break
        if not name:
            continue
        item = {"line": lineno, "kind": kind, "name": name}
        for k, v in kv.items():
            item[k] = v
        items.append(item)
    return items, policy


def _resolve(item, policy, val):
    """规则阈值解引用：'@key' 从 policy 取值，否则取字面量"""
    if isinstance(val, str) and val.startswith("@"):
        got = policy_value(policy, val[1:], None)
        return got if got is not None else val
    return val


def eval_rule(item, policy, rule):
    """判定单条规则：返回 (命中?, 渲染后的说明)"""
    code, level, field, op, val, msg = rule[:6]
    kinds = rule[6] if len(rule) > 6 else None
    if kinds and item.get("kind") not in kinds:
        return False, ""
    cur = item.get(field)
    has = cur is not None and str(cur).strip() != ""
    threshold = _resolve(item, policy, val)
    try:
        if op == "missing":
            hit = not has
        elif op == "present":
            hit = has
        elif op == "truthy":
            hit = as_bool(cur, False)
        elif op == "falsy":
            hit = not as_bool(cur, False)
        elif op == "eq":
            hit = has and str(cur).strip() == str(threshold).strip()
        elif op == "ne":
            hit = has and str(cur).strip() != str(threshold).strip()
        elif op == "lt":
            hit = has and as_num(cur) < as_num(threshold)
        elif op == "lte":
            hit = has and as_num(cur) <= as_num(threshold)
        elif op == "gt":
            hit = has and as_num(cur) > as_num(threshold)
        elif op == "gte":
            hit = has and as_num(cur) >= as_num(threshold)
        elif op == "in":
            hit = has and str(cur).strip().lower() in [str(x).lower() for x in threshold]
        elif op == "notin":
            hit = has and str(cur).strip().lower() not in [str(x).lower() for x in threshold]
        elif op == "contains":
            hit = has and str(threshold).lower() in str(cur).lower()
        else:
            hit = False
    except Exception:
        hit = False
    if not hit:
        return False, ""
    try:
        text = msg.format(**dict(item, policy=policy))
    except Exception:
        text = msg
    return True, text


def grade(items, policy):
    """逐条核验并分级聚合（跨条目重复名也在此检出）"""
    buckets, seen = {}, {}
    for it in items:
        scope = it["name"]
        if scope in seen:
            buckets.setdefault(scope, {"scope": scope, "kind": it.get("kind"), "line": it["line"], "issues": []})
            buckets[scope]["issues"].append(("MEDIUM", "DUPLICATE_NAME",
                                             "第 %d 行与第 %d 行同名声明（口径覆盖风险）" % (it["line"], seen[scope])))
        else:
            seen[scope] = it["line"]
        for rule in RULES:
            hit, text = eval_rule(it, policy, rule)
            if not hit:
                continue
            buckets.setdefault(scope, {"scope": scope, "kind": it.get("kind"), "line": it["line"], "issues": []})
            b = buckets[scope]
            b["issues"].append((rule[1], rule[0], text))
            b["line"] = min(b["line"], it["line"] or 0)
    out = list(buckets.values())
    for g in out:
        g["issues"] = sorted(g["issues"], key=lambda x: (LEVEL_ORDER.get(x[0], 9), x[1]))
        g["level"] = g["issues"][0][0] if g["issues"] else "LOW"
        g["issue_count"] = len(g["issues"])
    out.sort(key=lambda g: (LEVEL_ORDER.get(g["level"], 9), g["scope"]))
    return out


def render_report(graded):
    """渲染人类可读报告（结论在前）"""
    lines = ["== %s ==" % TITLE]
    if not graded:
        lines.append("(无声明)")
        return "\n".join(lines)
    for g in graded:
        lines.append("[%s] %s（%d 项）" % (g["level"], g["scope"], g["issue_count"]))
        for level, code, msg in g["issues"]:
            lines.append("    - {0} {1}：{2}".format(level, code, msg))
    return "\n".join(lines)


def process(text):
    """核验主流程：解析声明 → 逐条判级 → 汇总输出（含异常降级）"""
    try:
        items, policy = parse_decls(text)
        graded = grade(items, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        total_issues = sum(g["issue_count"] for g in graded)
        result = {
            "ok": True,
            "decl_count": len(items),
            "kinds": sorted(set(i.get("kind") for i in items)),
            "issue_total": total_issues,
            "high_risk_count": len(high),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "clean_count": len([g for g in graded if g["issue_count"] == 0]),
            "per_scope": graded,
            "report": render_report(graded),
        }
        for key in SUMMARY_KEYS:
            result.setdefault(key, 0)
            result[key] = len([i for i in items if i.get("kind") == key])
        result["conclusion"] = ("无高危项，声明可用于交付"
                                if not high else "发现 %d 处高危，须先修正再交付" % len(high))
        return result
    except Exception as exc:
        return {"ok": True, "error": str(exc), "decl_count": 0, "per_scope": [],
                "report": "(解析降级)", "conclusion": "输入无法解析，已降级返回"}


def build_parser():
    p = argparse.ArgumentParser(prog="backup-exposure-auditor", description="核验自托管环境的备份策略与对外暴露声明。检出保留期为 0、未验证恢复、无异地副本、暴露公网与缺少鉴权并分级输出。")
    p.add_argument("--input", "-i", required=False, help="输入文件路径（声明文本/配置/源码）")
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
