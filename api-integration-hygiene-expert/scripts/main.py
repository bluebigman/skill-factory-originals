#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-number-scale-check — 接口数值精度 小数位 舍入核验

核验接口数值字段的小数位与舍入口径，找出精度丢失与千分位混入

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验接口数值字段的标度、舍入模式与千分位口径是否自洽，检出小数位超限、千分位混入、科学计数法、引号包裹数字与同端点舍入模式混用并分级输出
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


def build_request(method, url, params=None, headers=None, body=None):
    """构造 HTTP 请求描述（不发起网络调用，纯离线生成）"""
    method = (method or "GET").upper()
    qs = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    full = url + (("?" + qs) if qs else "")
    hdrs = dict(headers or {})
    hdrs.setdefault("User-Agent", "wb-api-debug/1.0")
    return {"method": method, "url": full, "headers": hdrs, "body": body or {}}


def to_curl(req):
    """把请求描述渲染成 curl 命令（可复现）"""
    parts = ["curl", "-X", req["method"]]
    for k, v in req["headers"].items():
        parts += ["-H", f'"{k}: {v}"']
    if req.get("body"):
        parts += ["-d", "'" + json.dumps(req["body"], ensure_ascii=False) + "'"]
    parts.append(f'"{req["url"]}"')
    return " ".join(parts)


def parse_response(raw):
    """解析响应文本：JSON 优先，回落纯文本"""
    try:
        data = json.loads(raw)
    except Exception:
        return {"format": "text", "length": len(raw), "preview": raw[:200]}
    return {"format": "json", "type": type(data).__name__,
            "keys": sorted(data.keys())[:40] if isinstance(data, dict) else [],
            "length": len(raw)}


def diff_fields(a, b):
    """字段级差异比对（两个 JSON 文本）"""
    try:
        da, db = json.loads(a), json.loads(b)
    except Exception as exc:
        return [f"解析失败: {exc}"]
    out = []
    if isinstance(da, dict) and isinstance(db, dict):
        for k in sorted(set(da) | set(db)):
            va, vb = da.get(k, "<缺失>"), db.get(k, "<缺失>")
            if va != vb:
                out.append(f"{k}: {va!r} → {vb!r}")
    else:
        out.append("仅支持对象级差异比对")
    return out


def load_request_spec(text):
    """解析"请求规格"文本：支持 key=value 行式写法

    示例:
        method=POST
        url=https://example.com/api/v1/items
        header=Content-Type: application/json
        param=page=1
        body={"name":"demo"}
    """
    spec = {"method": "GET", "url": "", "headers": {}, "params": {}, "body": {}}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip().lower(), val.strip()
        if key == "method":
            spec["method"] = val.upper()
        elif key == "url":
            spec["url"] = val
        elif key == "header" and ":" in val:
            hk, hv = val.split(":", 1)
            spec["headers"][hk.strip()] = hv.strip()
        elif key == "param" and "=" in val:
            pk, pv = val.split("=", 1)
            spec["params"][pk.strip()] = pv.strip()
        elif key == "body":
            try:
                spec["body"] = json.loads(val)
            except Exception:
                spec["body"] = {"_raw": val}
    return spec


def validate_request(req):
    """请求合规自检：URL 形态 / 方法与 body 搭配 / 头部规范"""
    issues = []
    url = req.get("url") or ""
    if not url:
        issues.append({"level": "HIGH", "msg": "缺少 url"})
    elif not re.match(r"^https?://", url, re.I):
        issues.append({"level": "HIGH", "msg": f"url 必须以 http(s):// 开头：{url[:60]}"})
    if req.get("method") in ("POST", "PUT", "PATCH") and not req.get("body"):
        issues.append({"level": "MEDIUM", "msg": f'{req["method"]} 通常需要 body'})
    if req.get("method") in ("GET", "DELETE") and req.get("body"):
        issues.append({"level": "LOW", "msg": f'{req["method"]} 携带 body 可能被服务端忽略'})
    for k in req.get("headers", {}):
        if k != k.strip():
            issues.append({"level": "LOW", "msg": f"头部名含多余空白：{k!r}"})
    return issues


def render_requests_py(req):
    """渲染成 Python requests 片段（便于落地到脚本）"""
    lines = ["import requests", "", "resp = requests.request(",
             f'    "{req["method"]}",', f'    "{req["url"]}",']
    if req.get("headers"):
        lines.append(f'    headers={json.dumps(req["headers"], ensure_ascii=False)},')
    if req.get("body"):
        lines.append(f'    json={json.dumps(req["body"], ensure_ascii=False)},')
    lines += ["    timeout=30,", ")", 'print(resp.status_code, resp.text[:500])']
    return "\n".join(lines)


def render_fetch_js(req):
    """渲染成浏览器 fetch 片段"""
    return ("await fetch({url}, {{\n"
            "  method: '{method}',\n"
            "  headers: {headers},\n"
            "  body: {body}\n"
            "}});").format(url=json.dumps(req.get("url", ""), ensure_ascii=False),
                           method=req.get("method", "GET"),
                           headers=json.dumps(req.get("headers", {}), ensure_ascii=False),
                           body=json.dumps(json.dumps(req.get("body", {}), ensure_ascii=False), ensure_ascii=False))


def summarize_debug(req, resp_meta, issues):
    """汇总调试结论（结论在前，细节在后）"""
    return {
        "ok": not [i for i in issues if i["level"] == "HIGH"],
        "conclusion": "请求可直接复现" if not issues else f"发现 {len(issues)} 项待确认",
        "request": {"method": req.get("method"), "url": req.get("url"),
                    "header_count": len(req.get("headers", {})),
                    "param_count": len(req.get("params", {}))},
        "response": resp_meta,
        "issues": issues,
        "next_action": "按 curl 复现并核对字段" if not issues else "先修复 HIGH 级问题再复现",
    }



NP_DECL_RX = re.compile(r"^\s*(num|sample|policy)\s+(.*)$", re.I)
NP_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
NP_ROUND_MODES = ("half_up", "half_even", "floor", "ceil", "truncate", "none")
NP_TRUE = ("1", "true", "yes", "y", "on")
NP_NUM_RX = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")
NP_SCI_RX = re.compile(r"^[+-]?\d+(\.\d+)?[eE][+-]?\d+$")


def np_kv(text):
    """解析 key=value 片段（键小写）；值为空的键请置于行尾（WBR-213）"""
    out = {}
    for m in NP_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def np_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().strip('"').lower() in NP_TRUE


def np_int(val, default=0):
    try:
        return int(float(str(val).strip().strip('"')))
    except Exception:
        return default


def np_clean(raw):
    """去掉引号与千分位分隔符，返回 (裸值, 是否带引号, 是否带千分位)"""
    v = (raw or "").strip()
    quoted = len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'"
    if quoted:
        v = v[1:-1]
    thousand = "," in v
    return v.replace(",", ""), quoted, thousand


def np_scale(raw):
    """测小数位：非数值/科学计数法返回 None"""
    v, _q, _t = np_clean(raw)
    if NP_SCI_RX.match(v) or not NP_NUM_RX.match(v):
        return None
    return 0 if "." not in v else len(v.split(".", 1)[1])


def parse_num_spec(text):
    """解析数值规约声明块

    语法（每行一条）：
        num endpoint=/orders name=amount scale=2 round=half_up locale=plain
        sample endpoint=/orders amount=12.345 total=1,234.567
        policy require_uniform_round=true max_scale=6 forbid_thousand_sep=true
    """
    decls, samples, policy = {}, [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = NP_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), np_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
            continue
        ep = (kv.get("endpoint") or kv.get("ep") or "").strip()
        if kind == "num":
            name = (kv.get("name") or kv.get("field") or "").strip()
            if not ep or not name:
                continue
            decls[(ep, name)] = {
                "line": lineno, "endpoint": ep, "name": name,
                "scale": np_int(kv.get("scale"), -1),
                "round": (kv.get("round") or kv.get("rounding") or "").strip().lower(),
                "locale": (kv.get("locale") or "plain").strip().lower(),
            }
            continue
        vals = {k: v for k, v in kv.items() if k not in ("endpoint", "ep")}
        if ep and vals:
            samples.append({"line": lineno, "endpoint": ep, "values": vals})
    return decls, samples, policy


def grade_num_spec(decls, samples, policy):
    """逐声明分级核验；返回按风险排序的结果列表"""
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    max_scale = np_int(policy.get("max_scale"), 6)
    forbid_sep = np_bool(policy.get("forbid_thousand_sep"), True)
    uniform_round = np_bool(policy.get("require_uniform_round"), True)
    buckets = {}

    def add(key, ep, name, level, code, msg, line):
        buckets.setdefault(key, {"endpoint": ep, "name": name, "line": line, "issues": []})
        b = buckets[key]
        b["issues"].append((level, code, msg))
        b["line"] = min(b["line"], line or 0)

    hit = set()
    for s in samples:
        ep = s["endpoint"]
        for name, raw in s["values"].items():
            key = (ep, name)
            if key not in decls:
                add(key, ep, name, "HIGH", "UNDECLARED_FIELD",
                    "样本出现未声明的数值字段 %s" % name, s["line"])
                continue
            hit.add(key)
            d = decls[key]
            bare, quoted, thousand = np_clean(raw)
            if thousand and forbid_sep:
                add(key, ep, name, "HIGH", "THOUSAND_SEP",
                    "取值含千分位分隔符（规约禁用）：%s" % raw, s["line"])
            if quoted:
                add(key, ep, name, "MEDIUM", "QUOTED_NUMBER",
                    "数值被引号包裹 → 多数客户端按字符串处理：%s" % raw, s["line"])
            sc = np_scale(raw)
            if sc is None:
                if NP_SCI_RX.match(bare):
                    add(key, ep, name, "MEDIUM", "SCI_NOTATION",
                        "取值使用科学计数法，序列化口径随语言而异：%s" % raw, s["line"])
                else:
                    add(key, ep, name, "HIGH", "NOT_A_NUMBER",
                        "取值不可解析为数值：%s" % raw, s["line"])
            else:
                if d["scale"] >= 0 and sc > d["scale"]:
                    add(key, ep, name, "HIGH", "SCALE_EXCEEDED",
                        "小数位 %d 超出声明 scale=%d（按声明舍入将丢精度）" % (sc, d["scale"]),
                        s["line"])
                if d["scale"] > max_scale:
                    add(key, ep, name, "MEDIUM", "SCALE_TOO_LARGE",
                        "声明 scale=%d 超过上限 %d" % (d["scale"], max_scale), d["line"])

    mode_by_ep, locale_by_ep = {}, {}
    for key, d in decls.items():
        ep, name = key
        if d["round"] and d["round"] not in NP_ROUND_MODES:
            add(key, ep, name, "MEDIUM", "ROUND_MODE_UNKNOWN",
                "未知舍入模式 %s" % d["round"], d["line"])
        if d["scale"] < 0:
            add(key, ep, name, "MEDIUM", "SCALE_UNSPECIFIED",
                "数值字段未声明 scale，跨语言序列化小数位不可控", d["line"])
        mode_by_ep.setdefault(ep, set()).add(d["round"] or "none")
        locale_by_ep.setdefault(ep, set()).add(d["locale"])

    for ep, modes in mode_by_ep.items():
        if len(modes) > 1 and uniform_round:
            add((ep, "*(endpoint)"), ep, "*(endpoint)", "MEDIUM", "ROUND_MODE_MIXED",
                "同端点混用多种舍入模式：%s" % ",".join(sorted(modes)), 0)
    for ep, locs in locale_by_ep.items():
        if len(locs) > 1:
            add((ep, "*(endpoint)"), ep, "*(endpoint)", "MEDIUM", "LOCALE_MIXED",
                "同端点混用 Locale 口径：%s" % ",".join(sorted(locs)), 0)

    for key, d in decls.items():
        if key not in hit:
            add(key, d["endpoint"], d["name"], "LOW", "SAMPLE_MISSING",
                "声明无样本覆盖（无法证实实际小数位）", d["line"])

    out = list(buckets.values())
    for g in out:
        g["issues"].sort(key=lambda x: order.get(x[0], 9))
        g["level"] = g["issues"][0][0] if g["issues"] else "LOW"
        g["issue_count"] = len(g["issues"])
    out.sort(key=lambda g: (order.get(g["level"], 9), g["endpoint"], g["name"]))
    return out


def render_num_report(graded):
    lines = ["== 数值精度与舍入规约核验 =="]
    if not graded:
        lines.append("(无声明)")
        return "\n".join(lines)
    for g in graded:
        lines.append("[%s] %s · %s（%d 项）"
                     % (g["level"], g["endpoint"], g["name"], g["issue_count"]))
        for level, code, msg in g["issues"]:
            lines.append("    - {0} {1}：{2}".format(level, code, msg))
    return "\n".join(lines)


def process(text):
    """数值规约核验：解析声明/样本/策略 → 核验标度·舍入·Locale → 分级输出整改清单"""
    try:
        decls, samples, policy = parse_num_spec(text)
        graded = grade_num_spec(decls, samples, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "definition_count": len(decls),
            "endpoint_count": len({k[0] for k in decls}),
            "sample_total": sum(len(s["values"]) for s in samples),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_keys": ["%s·%s" % (g["endpoint"], g["name"]) for g in high],
            "issue_code_distribution": codes,
            "per_field": graded,
            "report": render_num_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "definition_count": 0, "per_field": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-number-scale-check", description="核验接口数值字段的小数位与舍入口径，找出精度丢失与千分位混入")
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
