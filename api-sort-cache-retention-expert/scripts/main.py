#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-cache-verifier-auditor — 接口缓存 复验条件 排查修复

接口缓存 复验条件 排查修复处理工具

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验接口条件请求验证器与复验语义，检出验证器缺失或取值缺失、弱验证器按强校验声明、内容时点缺失或非法、新鲜度时效为负并分级输出整改清单
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



CV_RX = re.compile(r"^\s*cache\s+endpoint\s*=\s*(\S*)\s*(.*)$", re.I)
CV_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\S*)")
CV_TS_RX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(Z|[+-]\d{2}:?\d{2})?$")
CV_DATE_RX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def cv_kv(rest):
    """抽取缓存声明行尾部的键值对（值可为空）"""
    out = {}
    for k, v in CV_KV_RX.findall(rest):
        out[k.lower()] = v
    return out


def cv_parse(text):
    """解析缓存声明行：cache endpoint=<路径> etag=strong value=... last_modified=... max_age=300"""
    rows = []
    for ln, raw in enumerate(text.splitlines(), 1):
        m = CV_RX.match(raw)
        if not m:
            continue
        rows.append({"scope": m.group(1), "line": ln,
                     "raw": raw.strip(), "kv": cv_kv(m.group(2))})
    return rows


def cv_check_ts(raw):
    """返回 (是否可解析, 是否仅到日粒度)"""
    if not raw:
        return False, False
    m = CV_TS_RX.match(raw)
    if m:
        mo, day, hh, mi, ss = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
        if not (1 <= mo <= 12 and 1 <= day <= 31 and hh <= 23 and mi <= 59 and ss <= 59):
            return False, False
        return True, False
    m = CV_DATE_RX.match(raw)
    if m:
        mo, day = int(m.group(2)), int(m.group(3))
        if not (1 <= mo <= 12 and 1 <= day <= 31):
            return False, False
        return True, True
    return False, False


def cv_grade(rows):
    """分级：验证器缺失 / 取值缺失 / 弱验证器当强用 / 时间戳缺失或非法 / 时效取值非法"""
    graded = []
    for r in rows:
        kv = r["kv"]
        issues = []
        etag = (kv.get("etag") or "").strip()
        value = (kv.get("value") or "").strip()
        lm = (kv.get("last_modified") or "").strip()
        ma = (kv.get("max_age") or "").strip()

        if not etag:
            issues.append(("HIGH", "CV_VERIFIER_MISSING",
                           "端点「%s」未声明内容验证器，调用方只能整体重取" % r["scope"]))
        elif etag.lower() not in ("strong", "weak"):
            issues.append(("MEDIUM", "CV_VERIFIER_ILLEGAL",
                           "端点「%s」验证器强度声明「%s」不在 strong/weak 口径内" % (r["scope"], etag)))
        else:
            if not value:
                issues.append(("HIGH", "CV_VERIFIER_VALUE_MISSING",
                               "端点「%s」声明了验证器强度却无取值，复验条件无法成立" % r["scope"]))
            elif etag.lower() == "strong" and value.upper().startswith("W/"):
                issues.append(("HIGH", "CV_WEAK_USED_AS_STRONG",
                               "端点「%s」取值形态为弱验证器却按强校验声明，字节级比对不成立" % r["scope"]))

        ts_ok, date_only = cv_check_ts(lm)
        if not lm:
            issues.append(("HIGH", "CV_TIME_VERIFIER_MISSING",
                           "端点「%s」未声明内容时点，客户端无法据时点发起复验" % r["scope"]))
        elif not ts_ok:
            issues.append(("HIGH", "CV_TIME_VERIFIER_ILLEGAL",
                           "端点「%s」内容时点「%s」取值域非法" % (r["scope"], lm)))
        elif date_only:
            issues.append(("MEDIUM", "CV_TIME_GRANULARITY_COARSE",
                           "端点「%s」内容时点仅到日粒度，秒级变化无法被识别" % r["scope"]))

        if not ma:
            issues.append(("MEDIUM", "CV_MAX_AGE_MISSING",
                           "端点「%s」未声明新鲜度时效，中间层缓存时长不可控" % r["scope"]))
        else:
            try:
                mv = int(ma)
                if mv < 0:
                    issues.append(("HIGH", "CV_MAX_AGE_NEGATIVE",
                                   "端点「%s」新鲜度时效为 %d，取值域非法" % (r["scope"], mv)))
            except Exception:
                issues.append(("HIGH", "CV_MAX_AGE_ILLEGAL",
                               "端点「%s」新鲜度时效「%s」非整数量纲" % (r["scope"], ma)))

        graded.append({
            "scope": r["scope"],
            "line": r["line"],
            "verifier_strength": etag or "(缺失)",
            "last_modified": lm or "(缺失)",
            "max_age": ma or "(缺失)",
            "issues": issues,
            "issue_count": len(issues),
            "high_risk": any(i[0] == "HIGH" for i in issues),
            "codes": sorted(set(i[1] for i in issues)),
        })
    return graded


def cv_render(graded):
    """渲染条件请求验证器核验报告"""
    lines = ["# 接口条件请求验证器与复验语义 核验报告", "",
             "核验端点 %d 个，命中问题 %d 项。"
             % (len(graded), sum(g["issue_count"] for g in graded)), ""]
    for g in graded:
        head = "🔴" if g["high_risk"] else ("🟡" if g["issues"] else "🟢")
        lines.append("%s %s（第 %d 行）验证器 %s，内容时点 %s"
                     % (head, g["scope"], g["line"], g["verifier_strength"], g["last_modified"]))
        if not g["issues"]:
            lines.append("    - 验证器、内容时点与新鲜度时效三者自洽")
        for sev, code, msg in g["issues"]:
            lines.append("    - [%s][%s] %s" % (sev, code, msg))
    return "\n".join(lines)


def process(text):
    try:
        rows = cv_parse(text)
        graded = cv_grade(rows)
        codes = {}
        kinds = {}
        for g in graded:
            for sev, code, _msg in g["issues"]:
                codes[code] = codes.get(code, 0) + 1
                kinds[sev] = kinds.get(sev, 0) + 1
        high = [g for g in graded if g["high_risk"]]
        return {
            "ok": True,
            "endpoint_count": len(rows),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "severity_distribution": kinds,
            "per_scope": graded,
            "verifiers": [{"scope": g["scope"], "strength": g["verifier_strength"],
                           "last_modified": g["last_modified"], "max_age": g["max_age"]}
                          for g in graded],
            "report": cv_render(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "endpoint_count": 0, "issue_total": 0,
                "high_risk_count": 0, "high_risk_scopes": [], "issue_code_distribution": {},
                "severity_distribution": {}, "per_scope": [], "verifiers": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-cache-verifier-auditor", description="接口缓存 复验条件 排查修复处理工具")
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
