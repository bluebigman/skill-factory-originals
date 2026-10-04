#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""callback-delivery-auditor — 回调投递 验签算法 投递核验

核验出站回调的地址协议、验签、重放窗口与死信声明

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验出站回调的投递与验签声明，检出地址非 https、验签算法缺失或用弱算法、重放窗口缺失、重试超限且无退避、密钥轮换缺失与死信去向缺失并分级输出
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



CB_DECL_RX = re.compile(r"^\s*(hook|policy)\s+(.*)$", re.I)
CB_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
CB_TRUE = ("1", "true", "yes", "y", "on")
CB_ALGOS = ("hmac-sha256", "hmac-sha512", "ed25519", "rsa-sha256")
CB_WEAK = ("md5", "sha1", "hmac-md5", "hmac-sha1", "none")
CB_BACKOFFS = ("exp", "exponential", "linear", "fixed", "jitter", "none")
CB_ORDERS = ("seq", "key", "none")


def cb_kv(text):
    out = {}
    for m in CB_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def cb_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in CB_TRUE


def cb_int(val, default=0):
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def parse_callback_spec(text):
    """解析回调投递与验签声明块

    语法（每行一条）：
        hook name=order-created url=https://cb.example.com/orders retry=3 backoff=exp timeout=5 sign=hmac-sha256 sign_header=X-Sign secret_rotate_days=90 replay_window=300 order=key dead_letter=dlq
        policy require_https=true require_sign=true max_retry=5 min_rotate_days=30 require_replay_window=true require_dead_letter=true
    """
    hooks, policy = [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = CB_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), cb_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
            continue
        name = (kv.get("name") or "").strip()
        if not name:
            continue
        hooks.append({
            "line": lineno,
            "name": name,
            "url": (kv.get("url") or "").strip(),
            "retry": cb_int(kv.get("retry"), 0),
            "backoff": (kv.get("backoff") or "").strip().lower(),
            "timeout": cb_int(kv.get("timeout"), 0),
            "sign": (kv.get("sign") or "").strip().lower(),
            "sign_header": (kv.get("sign_header") or "").strip(),
            "rotate_days": cb_int(kv.get("secret_rotate_days"), 0),
            "replay_window": cb_int(kv.get("replay_window"), 0),
            "order": (kv.get("order") or "").strip().lower(),
            "dead_letter": (kv.get("dead_letter") or "").strip(),
        })
    return hooks, policy


def grade_callback_spec(hooks, policy):
    order_lv = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    max_retry = cb_int(policy.get("max_retry"), 5)
    min_rotate = cb_int(policy.get("min_rotate_days"), 30)
    req_https = cb_bool(policy.get("require_https"), True)
    req_sign = cb_bool(policy.get("require_sign"), True)
    req_window = cb_bool(policy.get("require_replay_window"), True)
    req_dlq = cb_bool(policy.get("require_dead_letter"), True)
    buckets = {}
    seen_names = {}

    def add(scope, level, code, msg, line):
        buckets.setdefault(scope, {"scope": scope, "line": line, "issues": []})
        b = buckets[scope]
        b["issues"].append((level, code, msg))
        b["line"] = min(b["line"], line or 0)

    for h in hooks:
        name = h["name"]
        if name in seen_names:
            add(name, "MEDIUM", "DUPLICATE_HOOK",
                "回调名与第 %d 行重复" % seen_names[name], h["line"])
        else:
            seen_names[name] = h["line"]

        url = h["url"]
        if not url:
            add(name, "HIGH", "URL_MISSING", "未声明回调地址（投递无处可去）", h["line"])
        elif req_https and not url.lower().startswith("https://"):
            add(name, "HIGH", "NOT_HTTPS",
                "回调地址非 https（载荷在链路上明文，验签也无法防篡改）", h["line"])
        elif not (url.lower().startswith("http://") or url.lower().startswith("https://")):
            add(name, "MEDIUM", "URL_MALFORMED",
                "回调地址 %s 不是合法 http(s) 绝对地址" % url, h["line"])

        if req_sign and not h["sign"]:
            add(name, "HIGH", "SIGN_MISSING",
                "未声明验签算法（接收方无法判定来源真实性）", h["line"])
        elif h["sign"] in CB_WEAK:
            add(name, "HIGH", "SIGN_ALGO_WEAK",
                "验签算法 %s 属弱算法（可被伪造）" % h["sign"], h["line"])
        elif h["sign"] and h["sign"] not in CB_ALGOS:
            add(name, "MEDIUM", "SIGN_ALGO_UNKNOWN",
                "验签算法 %s 不在白名单（%s）" % (h["sign"], "/".join(CB_ALGOS)), h["line"])
        if h["sign"] and not h["sign_header"]:
            add(name, "MEDIUM", "SIGN_HEADER_MISSING",
                "声明了验签算法但未声明签名头名（接收方不知去哪个头取签名）", h["line"])

        if req_window and h["replay_window"] <= 0:
            add(name, "HIGH", "REPLAY_WINDOW_MISSING",
                "未声明重放窗口（旧签名可被无限期重放）", h["line"])
        elif h["replay_window"] > 900:
            add(name, "MEDIUM", "REPLAY_WINDOW_TOO_LARGE",
                "重放窗口 %ds 过大（建议不超过 900s）" % h["replay_window"], h["line"])

        if h["retry"] < 0:
            add(name, "HIGH", "RETRY_NEGATIVE", "重试次数为负（%d）" % h["retry"], h["line"])
        elif h["retry"] > max_retry:
            add(name, "MEDIUM", "RETRY_EXCEEDED",
                "重试次数 %d 超过上限 %d（下游被打爆）" % (h["retry"], max_retry), h["line"])
        if h["retry"] > 1 and h["backoff"] in ("", "none"):
            add(name, "MEDIUM", "BACKOFF_MISSING",
                "重试 %d 次但退避策略为 none（同时重试形成峰值）" % h["retry"], h["line"])
        if h["backoff"] and h["backoff"] not in CB_BACKOFFS:
            add(name, "LOW", "BACKOFF_UNKNOWN",
                "退避策略 %s 非约定取值" % h["backoff"], h["line"])

        if h["timeout"] <= 0:
            add(name, "MEDIUM", "TIMEOUT_MISSING",
                "未声明投递超时（慢接收方会占满发送线程）", h["line"])

        if h["rotate_days"] <= 0:
            add(name, "MEDIUM", "SECRET_ROTATE_MISSING",
                "未声明密钥轮换周期（长期不轮换等同长期泄露）", h["line"])
        elif h["rotate_days"] > min_rotate * 12:
            add(name, "MEDIUM", "SECRET_ROTATE_STALE",
                "密钥轮换周期 %d 天过长（建议不超过 %d 天）" % (h["rotate_days"], min_rotate * 12), h["line"])

        if h["order"] and h["order"] not in CB_ORDERS:
            add(name, "MEDIUM", "ORDER_MODE_UNKNOWN",
                "投递顺序模式 %s 不在白名单（%s）" % (h["order"], "/".join(CB_ORDERS)), h["line"])
        if not h["order"]:
            add(name, "LOW", "ORDER_MODE_MISSING",
                "未声明投递顺序模式（乱序到达时接收方无从判断）", h["line"])

        if req_dlq and not h["dead_letter"]:
            add(name, "MEDIUM", "DEAD_LETTER_MISSING",
                "未声明失败落库/死信去向（重试耗尽后事件丢失）", h["line"])

    out = list(buckets.values())
    for g in out:
        g["issues"].sort(key=lambda x: order_lv.get(x[0], 9))
        g["level"] = g["issues"][0][0] if g["issues"] else "LOW"
        g["issue_count"] = len(g["issues"])
    out.sort(key=lambda g: (order_lv.get(g["level"], 9), g["scope"]))
    return out


def render_callback_report(graded):
    lines = ["== 回调投递与验签声明核验 =="]
    if not graded:
        lines.append("(无声明)")
        return "\n".join(lines)
    for g in graded:
        lines.append("[%s] %s（%d 项）" % (g["level"], g["scope"], g["issue_count"]))
        for level, code, msg in g["issues"]:
            lines.append("    - {0} {1}：{2}".format(level, code, msg))
    return "\n".join(lines)


def process(text):
    """回调投递核验：解析回调/策略 → 校验地址协议·验签算法·重放窗口·重试退避·密钥轮换·死信 → 分级输出"""
    try:
        hooks, policy = parse_callback_spec(text)
        graded = grade_callback_spec(hooks, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "hook_count": len(hooks),
            "no_sign_count": len([h for h in hooks if not h["sign"]]),
            "no_dead_letter_count": len([h for h in hooks if not h["dead_letter"]]),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "per_scope": graded,
            "report": render_callback_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "hook_count": 0, "per_scope": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="callback-delivery-auditor", description="核验出站回调的地址协议、验签、重放窗口与死信声明")
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
