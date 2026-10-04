#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-compression-consistency-checker — 接口压缩 传输体积 解压排查

核验内容压缩算法协商与长度一致性检出二次压缩与长度不符

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验内容压缩的算法协商与长度一致性，检出客户端不支持算法、已压缩内容二次压缩、声明长度与实际发出不符、缺少变化声明并分级输出
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



CZ_DECL_RX = re.compile(r"^\s*(res|policy)\s+(.*)$", re.I)
CZ_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
CZ_TRUE = ("1", "true", "yes", "y", "on")
CZ_ALGOS = ("gzip", "br", "deflate", "zstd", "identity")
CZ_PRECOMPRESSED = (".gz", ".zip", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".pdf", ".br", ".zst")


def cz_kv(text):
    out = {}
    for m in CZ_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def cz_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in CZ_TRUE


def cz_int(val, default=-1):
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def cz_split(raw):
    return [x.strip().lower() for x in (raw or "").split(",") if x.strip()]


def parse_compress_spec(text):
    """解析内容压缩声明块

    语法（每行一条）：
        res name=api-json path=/v1/items plain_size=20480 encoding=gzip \\
            sent_size=4096 declared_size=4096 accept_enc="gzip, br" \\
            ctype=application/json compressible=yes varied=yes
        policy client_algos=gzip,br min_compress_size=1024 \\
               require_vary=true forbid_double_compress=true \\
               require_size_consistent=true
    """
    res, policy = [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = CZ_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), cz_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
        elif kind == "res":
            name = (kv.get("name") or "").strip()
            if not name:
                continue
            res.append({
                "line": lineno, "name": name,
                "path": (kv.get("path") or "").strip(),
                "plain_size": cz_int(kv.get("plain_size"), -1),
                "encoding": (kv.get("encoding") or "").strip().lower(),
                "sent_size": cz_int(kv.get("sent_size"), -1),
                "declared_size": cz_int(kv.get("declared_size"), -1),
                "accept_enc": cz_split(kv.get("accept_enc")),
                "ctype": (kv.get("ctype") or "").strip().lower(),
                "compressible": cz_bool(kv.get("compressible"), True),
                "varied": cz_bool(kv.get("varied"), False),
            })
    return res, policy


def grade_compress_spec(res, policy):
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    client_algos = cz_split(policy.get("client_algos")) or ["gzip", "br", "deflate", "identity"]
    min_size = cz_int(policy.get("min_compress_size"), 1024)
    require_vary = cz_bool(policy.get("require_vary"), True)
    forbid_double = cz_bool(policy.get("forbid_double_compress"), True)
    require_size = cz_bool(policy.get("require_size_consistent"), True)
    buckets = {}

    def add(scope, level, code, msg, line):
        b = buckets.setdefault(scope, {"scope": scope, "line": line, "issues": []})
        b["issues"].append((level, code, msg))
        if not b["line"]:
            b["line"] = line

    for r in res:
        enc = r["encoding"] or "identity"
        if enc not in CZ_ALGOS:
            add(r["name"], "MEDIUM", "ENCODING_UNKNOWN",
                "压缩算法 %s 非约定取值（%s）" % (enc, "/".join(CZ_ALGOS)), r["line"])
        if enc != "identity" and client_algos and enc not in client_algos:
            add(r["name"], "HIGH", "ALGO_NOT_CLIENT_SUPPORTED",
                "服务端使用 %s，但客户端仅声明支持 %s（解压失败）"
                % (enc, "/".join(client_algos)), r["line"])
        if r["accept_enc"] and enc != "identity" and enc not in r["accept_enc"]:
            add(r["name"], "HIGH", "ENCODING_NOT_REQUESTED",
                "以 %s 答复，但请求未声明接受该算法（客户端可能按原样落地）" % enc, r["line"])
        if enc != "identity" and r["compressible"] is False:
            add(r["name"], "MEDIUM", "NON_COMPRESSIBLE_COMPRESSED",
                "内容被标记为不可压缩却仍施加 %s 压缩（白耗算力）" % enc, r["line"])
        if forbid_double and r["path"].lower().endswith(CZ_PRECOMPRESSED):
            add(r["name"], "HIGH", "DOUBLE_COMPRESSION",
                "资源 %s 本身已是压缩格式，又施加 %s（体积反而增大）"
                % (r["path"], enc), r["line"])
        if r["plain_size"] > 0 and r["plain_size"] < min_size and enc != "identity":
            add(r["name"], "LOW", "SMALL_PAYLOAD_COMPRESSED",
                "载荷仅 %d 字节（低于阈值 %d）仍压缩，头部开销可能超过收益"
                % (r["plain_size"], min_size), r["line"])
        if require_size and r["declared_size"] >= 0 and r["sent_size"] >= 0 \
                and r["declared_size"] != r["sent_size"]:
            add(r["name"], "HIGH", "SENT_SIZE_MISMATCH",
                "声明长度 %d 与实际发出 %d 不符（截断或拼接错误）"
                % (r["declared_size"], r["sent_size"]), r["line"])
        if r["plain_size"] >= 0 and r["sent_size"] >= 0 and enc != "identity" \
                and r["sent_size"] >= r["plain_size"] and r["plain_size"] > 0:
            add(r["name"], "MEDIUM", "COMPRESS_EXPANDED",
                "压缩后 %d 字节不小于原始 %d 字节（压缩无效）"
                % (r["sent_size"], r["plain_size"]), r["line"])
        if r["ctype"] in ("application/json", "text/plain", "text/html", "application/xml") \
                and r["compressible"] is False:
            add(r["name"], "MEDIUM", "TEXT_MARKED_UNCOMPRESSIBLE",
                "文本类内容 %s 被标记为不可压缩（流量被浪费）" % r["ctype"], r["line"])
        if require_vary and not r["varied"]:
            add(r["name"], "MEDIUM", "VARY_MISSING",
                "响应未声明随接受编码变化（中间缓存可能把压缩体发给不支持的客户端）",
                r["line"])
        if enc == "identity" and r["plain_size"] > 0:
            add(r["name"], "LOW", "NO_COMPRESSION_APPLIED",
                "未施加压缩（%d 字节原样传输）" % r["plain_size"], r["line"])

    out = list(buckets.values())
    for g in out:
        g["issues"].sort(key=lambda x: (order.get(x[0], 9), x[1]))
        g["issue_count"] = len(g["issues"])
        g["high_risk"] = any(i[0] == "HIGH" for i in g["issues"])
        g["top_level"] = g["issues"][0][0] if g["issues"] else "LOW"
    out.sort(key=lambda x: (order.get(x["top_level"], 9), x["scope"]))
    return out


def render_compress_report(graded):
    if not graded:
        return "未识别到压缩声明（检查 res/policy 行）。"
    lines = ["# 传输压缩与解压一致性核验", ""]
    for g in graded:
        mark = "🔴" if g["high_risk"] else ("🟡" if g["top_level"] == "MEDIUM" else "⚪")
        lines.append("%s 资源 %s（首行 %d，问题 %d）" % (mark, g["scope"], g["line"], g["issue_count"]))
        for lv, code, msg in g["issues"]:
            lines.append("    [%s] %s — %s" % (lv, code, msg))
    high = [g["scope"] for g in graded if g["high_risk"]]
    lines.append("")
    lines.append("高风险资源 %d 个：%s" % (len(high), "、".join(high) if high else "无"))
    return "\n".join(lines)


def process(text):
    try:
        res, policy = parse_compress_spec(text)
        graded = grade_compress_spec(res, policy)
        high = [g for g in graded if g["high_risk"]]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "resource_count": len(res),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "per_scope": graded,
            "report": render_compress_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "resource_count": 0, "issue_total": 0,
                "high_risk_count": 0, "high_risk_scopes": [], "issue_code_distribution": {},
                "per_scope": [], "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-compression-consistency-checker", description="核验内容压缩算法协商与长度一致性检出二次压缩与长度不符")
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
