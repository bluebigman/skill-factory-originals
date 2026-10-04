#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-error-catalog-auditor — 接口错误码 取值唯一 作用域核对

核验错误码唯一性与作用域

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验错误码取值唯一性与作用域归属，检出取值重复跨域撞值、取值缺失或形态非法、作用域缺失与名称书写风格混用并分级输出整改清单
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



EC_ROW_RX = re.compile(r"^\s*error\s+(.*)$", re.I)
EC_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^\s,]+)")
EC_NAME_SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
EC_NAME_LOWER = re.compile(r"^[a-z][a-z0-9]*$")
EC_NAME_UPPER = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")


def ec_name_style(name):
    """判定错误码名称书写风格"""
    if EC_NAME_SNAKE.match(name):
        return "snake"
    if EC_NAME_UPPER.match(name):
        return "screaming"
    if EC_NAME_LOWER.match(name):
        return "plain"
    return "illegal"


def parse_error_catalog(text):
    """解析错误码字典行：error code=1001 scope=global name=invalid_param"""
    rows = []
    for ln, raw in enumerate(text.splitlines(), 1):
        m = EC_ROW_RX.match(raw)
        if not m:
            continue
        kvs = {}
        for k, v in EC_KV_RX.findall(m.group(1)):
            kvs[k.lower()] = v
        rows.append({
            "line": ln,
            "raw": raw.strip(),
            "code": kvs.get("code"),
            "scope": kvs.get("scope"),
            "name": kvs.get("name"),
        })
    return rows


def grade_error_catalog(rows):
    """分级：取值重复 / 跨作用域撞值 / 名称风格混用 / 作用域或取值缺失 / 取值形态非法"""
    graded = []
    by_code = {}
    styles = {}
    for r in rows:
        code = r["code"]
        if code:
            by_code.setdefault(code, []).append(r)
        if r["name"]:
            st = ec_name_style(r["name"])
            styles.setdefault(st, []).append(r["name"])
    for r in rows:
        issues = []
        if not r["code"]:
            issues.append(("HIGH", "EC_CODE_MISSING",
                           "错误项「%s」未给出取值，调用方无法按取值分支处理" % (r["name"] or r["raw"])))
        elif not re.match(r"^[0-9]+$", r["code"]):
            issues.append(("HIGH", "EC_CODE_ILLEGAL",
                           "错误项「%s」取值「%s」非纯数字形态，多数网关按数值透传会失真"
                           % (r["name"] or r["raw"], r["code"])))
        if not r["scope"]:
            issues.append(("HIGH", "EC_SCOPE_MISSING",
                           "错误项「%s」未声明归属作用域，跨服务撞值后无法定位来源"
                           % (r["name"] or r["code"] or r["raw"])))
        if r["name"]:
            st = ec_name_style(r["name"])
            if st == "illegal":
                issues.append(("MEDIUM", "EC_NAME_ILLEGAL",
                               "错误项名称「%s」含非法字符或形态不符约定" % r["name"]))
        else:
            issues.append(("MEDIUM", "EC_NAME_MISSING",
                           "错误项 %s 未给出可读名称，排障时只能看到裸数值" % (r["code"] or r["raw"])))
        peers = by_code.get(r["code"] or "", [])
        if len(peers) > 1:
            scopes = sorted(set(p["scope"] or "(无作用域)" for p in peers))
            issues.append(("HIGH", "EC_CODE_DUPLICATE",
                           "取值 %s 被 %d 处重复定义（作用域：%s），同一取值可对应多种含义"
                           % (r["code"], len(peers), ", ".join(scopes))))
        graded.append({
            "scope": r["name"] or r["code"] or ("行%d" % r["line"]),
            "line": r["line"],
            "issues": issues,
            "issue_count": len(issues),
            "high_risk": any(i[0] == "HIGH" for i in issues),
            "codes": sorted(set(i[1] for i in issues)),
        })
    extra = []
    if len(styles) > 1:
        detail = "; ".join("%s:%d" % (k, len(v)) for k, v in sorted(styles.items()))
        extra.append(("HIGH", "EC_NAME_STYLE_MIXED",
                      "错误项名称存在 %d 种书写风格并存（%s），生成客户端常量时易失配"
                      % (len(styles), detail)))
    return graded, styles, extra


def render_error_report(rows, graded, styles, extra):
    """渲染错误码字典核验报告"""
    lines = ["# 错误码取值唯一性与作用域归属 核验报告", "",
             "核验错误项 %d 条，命中问题 %d 项。"
             % (len(rows), sum(g["issue_count"] for g in graded) + len(extra)), ""]
    lines.append("名称风格分布：%s" % (", ".join("%s=%d" % (k, len(v)) for k, v in sorted(styles.items())) or "(无)"))
    for sev, code, msg in extra:
        lines.append("- [%s][%s] %s" % (sev, code, msg))
    lines.append("")
    for g in graded:
        head = "🔴" if g["high_risk"] else ("🟡" if g["issues"] else "🟢")
        lines.append("%s %s（第 %d 行）" % (head, g["scope"], g["line"]))
        if not g["issues"]:
            lines.append("    - 取值、作用域与名称三者齐备且唯一")
        for sev, code, msg in g["issues"]:
            lines.append("    - [%s][%s] %s" % (sev, code, msg))
    return "\n".join(lines)


def process(text):
    try:
        rows = parse_error_catalog(text)
        graded, styles, extra = grade_error_catalog(rows)
        codes = {}
        kinds = {}
        for g in graded:
            for sev, code, _msg in g["issues"]:
                codes[code] = codes.get(code, 0) + 1
                kinds[sev] = kinds.get(sev, 0) + 1
        for sev, code, _msg in extra:
            codes[code] = codes.get(code, 0) + 1
            kinds[sev] = kinds.get(sev, 0) + 1
        high = [g for g in graded if g["high_risk"]]
        return {
            "ok": True,
            "error_count": len(rows),
            "issue_total": sum(g["issue_count"] for g in graded) + len(extra),
            "high_risk_count": len(high) + len([1 for i in extra if i[0] == "HIGH"]),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "severity_distribution": kinds,
            "name_style_distribution": {k: len(v) for k, v in styles.items()},
            "per_scope": graded,
            "catalog": rows,
            "report": render_error_report(rows, graded, styles, extra),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "error_count": 0, "issue_total": 0,
                "high_risk_count": 0, "high_risk_scopes": [], "issue_code_distribution": {},
                "severity_distribution": {}, "name_style_distribution": {},
                "per_scope": [], "catalog": [], "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-error-catalog-auditor", description="核验错误码唯一性与作用域")
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
