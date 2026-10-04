#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-cache-directive-auditor — 接口调试 缓存指令 自洽核验

接口调试 缓存指令 自洽核验处理工具

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验接口响应缓存指令的自洽性，检出敏感端点被声明公共可缓存、no-store 与 max_age 冲突、校验器缺失与 vary 缺位并分级输出
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



CCH_DECL_RX = re.compile(r"^\s*(endpoint|policy)\s+(.*)$", re.I)
CCH_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
CCH_TRUE = ("1", "true", "yes", "y", "on")
CCH_CACHE_MODES = ("public", "private", "no-store", "no-cache")
CCH_SENSITIVE_HINTS = ("me", "account", "user", "profile", "pay", "order", "auth",
                       "session", "token", "wallet", "bill")
CCH_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
CCH_MIN_AGE_FLOOR = 60


def cch25_kv(text):
    """解析 key=value 片段 → 字典"""
    out = {}
    for m in CCH_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def cch25_bool(val, default=False):
    """宽松布尔解析"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in CCH_TRUE


def cch25_int(val, default=0):
    """安全整数解析"""
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def cch25_sensitive(path, method):
    """判定端点是否承载用户态/鉴权态数据（用于"公共可缓存"风险判定）"""
    p = (path or "").lower()
    if (method or "").upper() in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    return any(h in p for h in CCH_SENSITIVE_HINTS)


def parse_cache_endpoints(text):
    """解析缓存声明块

    语法（每行一条声明，key=value 空格分隔）：
        endpoint path=/v1/orders method=GET cache=public max_age=600 etag=true vary=
        endpoint path=/v1/pay   method=POST cache=public max_age=3600 etag=false vary=
        policy forbid_public_for_sensitive=true require_etag_when_cacheable=true min_max_age=60
    """
    endpoints, policy = [], {}
    for raw in (text or "").splitlines():
        m = CCH_DECL_RX.match(raw)
        if not m:
            continue
        kind = m.group(1).lower()
        kv = cch25_kv(m.group(2))
        if kind == 'policy':
            policy.update(kv)
        elif kind == 'endpoint':
            endpoints.append({
                'path': kv.get('path') or '(未命名)',
                'method': (kv.get('method') or 'GET').upper(),
                'cache': (kv.get('cache') or 'no-store').lower(),
                'max_age': cch25_int(kv.get('max_age'), 0),
                'etag': cch25_bool(kv.get('etag'), False),
                'vary': kv.get('vary') or '',
            })
    return endpoints, policy


def audit_cache(endpoints, policy):
    """逐端点核验缓存指令自洽性 → (分级结果, 问题码计数)"""
    forbid_pub = cch25_bool(policy.get('forbid_public_for_sensitive'), True)
    require_etag = cch25_bool(policy.get('require_etag_when_cacheable'), True)
    min_age = cch25_int(policy.get('min_max_age'), CCH_MIN_AGE_FLOOR)
    graded, codes = [], {}
    for ep in endpoints:
        issues = []

        def add(level, code, msg):
            issues.append((level, code, msg))
            codes[code] = codes.get(code, 0) + 1

        sensitive = cch25_sensitive(ep['path'], ep['method'])
        cacheable = ep['cache'] in ('public', 'private')
        if ep['cache'] not in CCH_CACHE_MODES:
            add('HIGH', 'CACHE_MODE_INVALID', f"缓存模式非法：{ep['cache']}")
        if forbid_pub and ep['cache'] == 'public' and sensitive:
            add('HIGH', 'CACHE_PUBLIC_SENSITIVE',
                '承载用户态/鉴权态数据却声明公共可缓存，存在越权留存风险')
        if ep['cache'] == 'no-store' and ep['max_age'] > 0:
            add('HIGH', 'NOSTORE_WITH_MAXAGE',
                'no-store 与 max_age>0 互相矛盾，缓存语义不确定')
        if cacheable and require_etag and not ep['etag']:
            add('MEDIUM', 'ETAG_MISSING', '声明可缓存但未提供校验器（etag）')
        if cacheable and sensitive and not (ep['vary'] or '').strip():
            add('MEDIUM', 'VARY_MISSING', '可缓存且随身份变化，但未声明 vary 区分维度')
        if cacheable and 0 < ep['max_age'] < min_age:
            add('LOW', 'MAX_AGE_TOO_SHORT',
                f"max_age={ep['max_age']} 低于下限 {min_age}，缓存收益趋零")
        level = 'OK'
        for lv, _, _ in sorted(issues, key=lambda x: CCH_LEVEL_ORDER[x[0]]):
            level = lv
            break
        graded.append({'path': ep['path'], 'method': ep['method'], 'cache': ep['cache'],
                       'max_age': ep['max_age'], 'level': level,
                       'issue_count': len(issues), 'issues': issues})
    return graded, codes


def render_cache_report(graded, codes):
    """渲染缓存核验报告（Markdown）"""
    rows = []
    for g in graded:
        cs = ",".join(c for _, c, _ in g['issues']) or "-"
        rows.append([g['level'], g['path'], g['method'], g['cache'], g['max_age'], cs])
    table = render_markdown_table(rows, ["级别", "端点", "方法", "缓存", "max_age", "问题码"])
    high = [g['path'] for g in graded if g['level'] == 'HIGH']
    tail = [f"端点 {len(graded)} ｜ 高危 {len(high)} ｜ 问题码种类 {len(codes)}"]
    for g in graded:
        if g['level'] == 'HIGH':
            tail.append(f"- 高危：{g['method']} {g['path']} → " +
                        "；".join(m for _, _, m in g['issues'])[:80])
    return table + "\n\n" + "\n".join(tail)


def process(text):
    """缓存指令核验：解析端点与策略 → 逐项核验自洽性 → 分级输出"""
    try:
        endpoints, policy = parse_cache_endpoints(text)
        graded, codes = audit_cache(endpoints, policy)
        high = [g["path"] for g in graded if g["level"] == "HIGH"]
        return {
            "ok": True,
            "endpoint_count": len(endpoints),
            "cacheable_count": sum(1 for g in graded if g["cache"] in ("public", "private")),
            "high_risk_count": len(high),
            "high_risk_endpoints": high,
            "issue_codes": codes,
            "per_endpoint": graded,
            "report": render_cache_report(graded, codes),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "endpoint_count": 0, "per_endpoint": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-cache-directive-auditor", description="接口调试 缓存指令 自洽核验处理工具")
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
