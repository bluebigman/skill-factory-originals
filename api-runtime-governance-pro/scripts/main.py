#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-media-negotiator — 接口媒质类型 编码核验

核验接口请求响应媒质类型与字符编码声明

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验接口请求/响应的媒质类型与字符编码声明是否自洽，检出形态与声明不符、字符集缺失、协商回落风险并分级输出整改清单
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



MEDIA_DECL_RX = re.compile(r"^\s*(endpoint|policy)\s+(.*)$", re.I)
MEDIA_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
MEDIA_TRUE = ("1", "true", "yes", "y", "on")
MEDIA_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

# 请求体形态 → 应当声明的媒质类型（用于检出"声明与形态两张皮"）
MEDIA_SHAPE_CT = {
    "json": "application/json",
    "form": "application/x-www-form-urlencoded",
    "multipart": "multipart/form-data",
    "text": "text/plain",
    "xml": "application/xml",
}
# 媒质类型 → 是否可承载字符集参数（结构化类型通常要求显式 charset）
MEDIA_TEXTUAL = ("application/json", "application/xml", "text/plain", "text/csv",
                 "application/x-www-form-urlencoded", "application/problem+json")
MEDIA_JSON_FAMILY = ("application/json", "application/problem+json",
                     "application/merge-patch+json", "application/vnd.api+json")


def md22_kv(text):
    """解析 key=value 片段 → 字典（值缺失留空串）"""
    out = {}
    for m in MEDIA_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def md22_bool(val, default=False):
    """宽松布尔解析（缺省值可控）"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in MEDIA_TRUE


def md22_norm_ct(val):
    """归一化媒质类型：去参数、小写、去空白"""
    ct = (val or "").strip().lower()
    if not ct:
        return ""
    if ";" in ct:
        ct = ct.split(";", 1)[0].strip()
    return ct


def parse_media_declarations(text):
    """解析媒质类型声明块

    语法（每行一条声明，key=value 空格分隔）：
        endpoint method=POST path=/v1/orders content_type=application/json
                 body=json accept=application/json response_type=application/json charset=utf-8
        policy charset_required=true json_only=false allow_wildcard=false
    """
    endpoints, policy = [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = MEDIA_DECL_RX.match(line)
        if not m:
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        kv = md22_kv(rest)
        if kind == "policy":
            policy.update(kv)
            continue
        ct = md22_norm_ct(kv.get("content_type") or kv.get("ct"))
        resp = md22_norm_ct(kv.get("response_type") or kv.get("resp_ct"))
        accept = md22_norm_ct(kv.get("accept"))
        endpoints.append({
            "line": lineno,
            "method": (kv.get("method") or "GET").upper(),
            "path": kv.get("path") or kv.get("url") or "",
            "content_type": ct,
            "response_type": resp,
            "accept": accept,
            "charset": (kv.get("charset") or "").strip().lower(),
            "body_shape": (kv.get("body") or kv.get("body_shape") or "").strip().lower(),
            "owner": kv.get("owner", ""),
        })
    return endpoints, policy


def grade_media_negotiation(endpoints, policy):
    """逐端点核验媒质类型/编码声明的自洽性与合规性，输出分级问题清单"""
    require_charset = md22_bool(policy.get("charset_required"), True)
    json_only = md22_bool(policy.get("json_only"), False)
    allow_wildcard = md22_bool(policy.get("allow_wildcard"), False)
    graded = []
    for ep in endpoints:
        issues = []
        ct, shape, resp = ep["content_type"], ep["body_shape"], ep["response_type"]
        if not ct:
            issues.append(("HIGH", "CT_MISSING", "未声明请求媒质类型，接收方无法据此选择解析器"))
        else:
            if "*/*" in ct and not allow_wildcard:
                issues.append(("MEDIUM", "CT_WILDCARD", f"媒质类型使用通配 {ct}，解析行为不确定"))
            if json_only and ct and ct not in MEDIA_JSON_FAMILY:
                issues.append(("MEDIUM", "CT_NON_JSON", f"策略要求结构化类型，实际为 {ct}"))
            if shape and shape in MEDIA_SHAPE_CT:
                expect = MEDIA_SHAPE_CT[shape]
                same_family = (ct == expect) or (shape == "json" and ct in MEDIA_JSON_FAMILY)
                if not same_family:
                    issues.append(("HIGH", "CT_SHAPE_MISMATCH",
                                   f"请求体形态 {shape} 与声明类型 {ct} 不符（应为 {expect}）"))
            elif shape and shape not in MEDIA_SHAPE_CT:
                issues.append(("LOW", "SHAPE_UNKNOWN", f"请求体形态 {shape} 未登记，无法交叉校验"))
        if ct in MEDIA_TEXTUAL and require_charset and not ep["charset"]:
            issues.append(("MEDIUM", "CHARSET_MISSING", f"{ct} 未声明字符集，跨区域传输易出现乱码"))
        if ep["charset"] and ep["charset"] not in ("utf-8", "utf8", "utf-16", "gbk", "gb18030"):
            issues.append(("LOW", "CHARSET_UNCOMMON", f"字符集 {ep['charset']} 非主流取值，需双端确认"))
        if ep["accept"] and resp and ep["accept"] != resp and "*/*" not in ep["accept"]:
            issues.append(("MEDIUM", "ACCEPT_RESP_MISMATCH",
                           f"客户端期望 {ep['accept']} 与实际响应类型 {resp} 不一致，易触发协商回落"))
        if not resp:
            issues.append(("LOW", "RESP_CT_MISSING", "未声明响应媒质类型，客户端无法静态断言解析路径"))
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        worst = sorted((i[0] for i in issues), key=lambda x: order.get(x, 9))
        graded.append({
            "method": ep["method"], "path": ep["path"], "owner": ep["owner"],
            "content_type": ct or "(未声明)", "charset": ep["charset"] or "-",
            "issues": issues, "issue_count": len(issues),
            "level": worst[0] if worst else "OK",
        })
    return graded


def render_media_report(graded):
    """渲染媒质类型核验结果（Markdown）"""
    rows = []
    for g in sorted(graded, key=lambda x: MEDIA_LEVEL_ORDER.get(x["level"], 9)):
        codes = ",".join(i[1] for i in g["issues"]) or "-"
        rows.append([g["level"], f"{g['method']} {g['path']}", g["content_type"],
                     g["charset"], g["issue_count"], codes])
    return render_markdown_table(rows, ["级别", "端点", "请求类型", "字符集", "问题数", "问题码"])


def process(text):
    """媒质类型谈判核验：解析端点声明 → 逐条自洽性体检 → 分级输出整改清单"""
    try:
        endpoints, policy = parse_media_declarations(text)
        graded = grade_media_negotiation(endpoints, policy)
        total_issues = sum(g["issue_count"] for g in graded)
        high = [g for g in graded if g["level"] == "HIGH"]
        pairs = {}
        for g in graded:
            key = g["content_type"]
            pairs[key] = pairs.get(key, 0) + 1
        content_types = re.findall(r"content_type=([^\s]+)", text or "", re.I)
        return {
            "ok": True,
            "endpoint_count": len(endpoints),
            "content_type_declared": len(content_types),
            "issue_total": total_issues,
            "high_risk_count": len(high),
            "high_risk_endpoints": [f"{g['method']} {g['path']}" for g in high],
            "content_type_distribution": pairs,
            "per_endpoint": graded,
            "charset_missing": [g["path"] for g in graded if g["charset"] == "-"],
            "report": render_media_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "endpoint_count": 0, "issue_total": 0,
                "per_endpoint": [], "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-media-negotiator", description="核验接口请求响应媒质类型与字符编码声明")
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
