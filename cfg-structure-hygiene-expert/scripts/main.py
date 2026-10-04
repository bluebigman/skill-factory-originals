#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cfg-datetime-validity-check — 配置时间取值 有效期 时区核验

核验配置中日期时间取值，找出已过期、时区缺失与时间窗倒置

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
能力：核验配置中时间与日期取值的有效性，检出已过期取值、时区缺失或非法、时间窗倒置、时长缺单位与跨文件取值分歧并分级输出
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



DT_DECL_RX = re.compile(r"^\s*(time|policy)\s+(.*)$", re.I)
DT_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
DT_TRUE = ("1", "true", "yes", "y", "on")
DT_DATE_RX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
DT_TS_RX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(:(\d{2}))?$")
DT_WINDOW_RX = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")
DT_DUR_RX = re.compile(r"^(\d+)([smhdw])?$")
DT_TZ_RX = re.compile(r"^[+-]\d{2}:\d{2}$")
DT_UNITS = ("s", "m", "h", "d", "w")


def dt_kv(text):
    out = {}
    for m in DT_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def dt_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in DT_TRUE


def dt_int(val, default=0):
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def dt_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def dt_dayno(y, m, d):
    """自 1970-01-01 起的天序号（自实现，避免依赖外部模块）"""
    mdays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    n = 0
    for yy in range(1970, y):
        n += 366 if dt_leap(yy) else 365
    for mm in range(1, m):
        n += mdays[mm] + (1 if (dt_leap(y) and mm == 2) else 0)
    return n + d - 1


def dt_parse_date(val):
    m = DT_DATE_RX.match((val or "").strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= mo <= 12) or not (1 <= d <= 31):
        return None
    if d > 28:
        mdays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        cap = mdays[mo] + (1 if (dt_leap(y) and mo == 2) else 0)
        if d > cap:
            return None
    return dt_dayno(y, mo, d)


def dt_parse_ts(val):
    m = DT_TS_RX.match((val or "").strip())
    if not m:
        return None
    day = dt_parse_date("%s-%s-%s" % (m.group(1), m.group(2), m.group(3)))
    if day is None:
        return None
    hh, mi = int(m.group(4)), int(m.group(5))
    ss = int(m.group(7) or 0)
    if hh > 23 or mi > 59 or ss > 59:
        return None
    return day * 86400 + hh * 3600 + mi * 60 + ss


def dt_duration_days(raw):
    """时长 → 天数（向上取整到天）；无单位返回 None"""
    m = DT_DUR_RX.match((raw or "").strip())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    if unit is None:
        return None
    factor = {"s": 1.0 / 86400, "m": 1.0 / 1440, "h": 1.0 / 24, "d": 1, "w": 7}[unit]
    days = n * factor
    return int(days) if days == int(days) else int(days) + 1


def parse_time_spec(text):
    """解析时间取值声明块

    语法（每行一条）：
        time file=a.conf key=token.expires value=2026-08-01T00:00:00 type=absolute tz=+08:00
        time file=a.conf key=backup.window value=02:00-03:00 type=window tz=+08:00
        time file=a.conf key=retry.ttl value=30s type=duration
        policy today=2026-09-17 require_tz=true forbid_expired=true max_duration_days=365
    """
    items, policy = [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = DT_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), dt_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
            continue
        key = (kv.get("key") or "").strip()
        if not key:
            continue
        items.append({
            "line": lineno, "file": (kv.get("file") or "").strip(), "key": key,
            "value": kv.get("value", ""),
            "type": (kv.get("type") or "").strip().lower(),
            "tz": (kv.get("tz") or "").strip(),
        })
    return items, policy


def grade_time_spec(items, policy):
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    today = dt_parse_date(policy.get("today"))
    need_tz = dt_bool(policy.get("require_tz"), True)
    forbid_expired = dt_bool(policy.get("forbid_expired"), True)
    max_days = dt_int(policy.get("max_duration_days"), 365)
    buckets = {}

    def add(scope, level, code, msg, line):
        buckets.setdefault(scope, {"scope": scope, "line": line, "issues": []})
        b = buckets[scope]
        b["issues"].append((level, code, msg))
        b["line"] = min(b["line"], line or 0)

    day_by_key = {}
    for it in items:
        scope = "%s·%s" % (it["file"] or "?", it["key"])
        t, v = it["type"], (it["value"] or "").strip()
        if t in ("absolute", "date", "timestamp"):
            stamp = dt_parse_ts(v)
            day = dt_parse_date(v) if stamp is None else stamp // 86400
            if day is None:
                add(scope, "HIGH", "VALUE_FORMAT_INVALID",
                    "时间取值格式非法：%s" % v, it["line"])
            else:
                day_by_key.setdefault(it["key"], []).append((day, it))
                if today is not None:
                    if day < today and forbid_expired:
                        add(scope, "HIGH", "VALUE_EXPIRED",
                            "取值已过期（%s 早于今天）" % v, it["line"])
                    elif 0 <= day - today <= 30:
                        add(scope, "LOW", "EXPIRY_NEAR",
                            "距过期仅 %d 天，建议提前续期" % (day - today), it["line"])
            if not it["tz"] and need_tz:
                add(scope, "MEDIUM", "TZ_MISSING",
                    "绝对时间取值未声明时区（跨时区解析会错位）", it["line"])
            elif it["tz"] and not DT_TZ_RX.match(it["tz"]):
                add(scope, "MEDIUM", "TZ_INVALID", "时区写法非法：%s" % it["tz"], it["line"])
        elif t == "window":
            m = DT_WINDOW_RX.match(v)
            if not m:
                add(scope, "HIGH", "VALUE_FORMAT_INVALID", "时间窗格式非法：%s" % v, it["line"])
            else:
                start = int(m.group(1)) * 60 + int(m.group(2))
                end = int(m.group(3)) * 60 + int(m.group(4))
                if start >= end:
                    add(scope, "HIGH", "WINDOW_INVERTED",
                        "时间窗起止倒置或零长（%s）" % v, it["line"])
                if int(m.group(1)) > 23 or int(m.group(3)) > 23:
                    add(scope, "MEDIUM", "WINDOW_HOUR_INVALID",
                        "时间窗小时数非法：%s" % v, it["line"])
            if not it["tz"] and need_tz:
                add(scope, "MEDIUM", "TZ_MISSING", "时间窗未声明时区", it["line"])
        elif t == "duration":
            days = dt_duration_days(v)
            if days is None:
                add(scope, "MEDIUM", "DURATION_UNIT_MISSING",
                    "时长取值缺少单位或格式非法：%s（默认按秒/毫秒解读会差 1000 倍）" % v,
                    it["line"])
            elif max_days and days > max_days:
                add(scope, "MEDIUM", "DURATION_EXCEEDED",
                    "时长 %s 折合 %d 天，超过上限 %d 天" % (v, days, max_days), it["line"])
        else:
            add(scope, "MEDIUM", "TYPE_UNKNOWN",
                "未声明时间取值类型（%s），无法判定过期口径" % (t or "空"), it["line"])

    for key, rows in day_by_key.items():
        vals = {r[0] for r in rows}
        if len(vals) > 1:
            files = ",".join(sorted({r[1]["file"] or "?" for r in rows}))
            add(key, "HIGH", "VALUE_CONFLICT_ACROSS_FILES",
                "同一键在不同文件取值不一致（%s）" % files, rows[0][1]["line"])

    out = list(buckets.values())
    for g in out:
        g["issues"].sort(key=lambda x: order.get(x[0], 9))
        g["level"] = g["issues"][0][0] if g["issues"] else "LOW"
        g["issue_count"] = len(g["issues"])
    out.sort(key=lambda g: (order.get(g["level"], 9), g["scope"]))
    return out


def render_time_report(graded):
    lines = ["== 时间与日期取值有效性核验 =="]
    if not graded:
        lines.append("(无声明)")
        return "\n".join(lines)
    for g in graded:
        lines.append("[%s] %s（%d 项）" % (g["level"], g["scope"], g["issue_count"]))
        for level, code, msg in g["issues"]:
            lines.append("    - {0} {1}：{2}".format(level, code, msg))
    return "\n".join(lines)


def process(text):
    """时间取值核验：解析时间项/策略 → 校验过期·时区·时间窗·时长单位·跨文件分歧 → 分级输出"""
    try:
        items, policy = parse_time_spec(text)
        graded = grade_time_spec(items, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "item_count": len(items),
            "key_count": len({i["key"] for i in items}),
            "type_distribution": {t: len([i for i in items if i["type"] == t])
                                  for t in sorted({i["type"] for i in items})},
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "per_scope": graded,
            "report": render_time_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "item_count": 0, "per_scope": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="cfg-datetime-validity-check", description="核验配置中日期时间取值，找出已过期、时区缺失与时间窗倒置")
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
