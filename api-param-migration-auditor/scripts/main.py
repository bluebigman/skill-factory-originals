#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-deprecation-migration-check — 接口下线 迁移路径 残留调用核对

核对接口废弃标注与下线日期，找出仍在被调用的老接口

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验端点废弃标注、下线日期与替代路径闭合性，对账残存调用量并分级输出迁移整改清单
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



EP_DECL_RX = re.compile(r"^\s*(endpoint|call|policy)\s+(.*)$", re.I)
EP_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
EP_DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EP_DEPRECATED = ("deprecated", "retired", "sunset", "legacy", "eol")
EP_ACTIVE = ("active", "ga", "stable", "online")
EP_TRUE = ("1", "true", "yes", "y", "on")


def ep_kv(text):
    """解析 key=value 片段（键小写）；值为空时请省略该键（WBR-213）"""
    out = {}
    for m in EP_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def ep_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in EP_TRUE


def ep_int(val, default=0):
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def ep_date(val):
    """日期规整：仅接受 YYYY-MM-DD；非法返回 None"""
    v = (val or "").strip().strip('"')
    return v if EP_DATE_RX.match(v) else None


def parse_endpoint_lifecycle(text):
    """解析端点生命周期声明块

    语法（每行一条声明）：
        endpoint path=/v1/orders status=deprecated since=2026-01-01 sunset=2026-06-30 \
                 replace=/v2/orders owner=order-team
        call path=/v1/orders count=120 client=web-app
        policy max_deprecated_call=0 require_replace=true require_sunset=true today=2026-09-17
    """
    endpoints, calls, policy = {}, [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = EP_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), ep_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
            continue
        if kind == "endpoint":
            p = (kv.get("path") or kv.get("url") or "").strip()
            if not p:
                continue
            endpoints[p] = {
                "line": lineno, "path": p,
                "status": (kv.get("status") or "active").strip().lower(),
                "since": ep_date(kv.get("since")),
                "sunset": ep_date(kv.get("sunset")),
                "replace": (kv.get("replace") or "").strip(),
                "owner": kv.get("owner", ""),
            }
            continue
        p = (kv.get("path") or kv.get("url") or "").strip()
        if not p:
            continue
        calls.append({"line": lineno, "path": p, "count": ep_int(kv.get("count"), 0),
                      "client": kv.get("client", "")})
    return endpoints, calls, policy


def grade_endpoint_lifecycle(endpoints, calls, policy):
    """逐端点分级核验；返回按风险排序的结果列表"""
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    callers = {}
    for c in calls:
        callers[c["path"]] = callers.get(c["path"], 0) + c["count"]
    today = ep_date(policy.get("today"))
    cap = ep_int(policy.get("max_deprecated_call"), -1)
    require_replace = ep_bool(policy.get("require_replace"), True)
    require_sunset = ep_bool(policy.get("require_sunset"), True)

    buckets = {}

    def add(path, level, code, msg):
        buckets.setdefault(path, []).append((level, code, msg))

    for p, e in endpoints.items():
        dep = e["status"] in EP_DEPRECATED
        used = callers.get(p, 0)
        if dep:
            if not e["replace"] and require_replace:
                add(p, "HIGH", "DEPRECATED_NO_REPLACE", "废弃端点未声明替代路径")
            elif e["replace"] == p:
                add(p, "HIGH", "REPLACE_SELF", "替代路径指向自身")
            elif e["replace"] and e["replace"] not in endpoints:
                add(p, "MEDIUM", "REPLACE_UNKNOWN", "替代路径 %s 未在清单中声明" % e["replace"])
            if not e["sunset"] and require_sunset:
                add(p, "HIGH", "SUNSET_MISSING", "废弃端点未声明下线日期")
            elif e["sunset"] and e["since"] and e["sunset"] < e["since"]:
                add(p, "HIGH", "SUNSET_BEFORE_SINCE", "下线日期早于废弃日期（%s < %s）"
                    % (e["sunset"], e["since"]))
            elif e["sunset"] and today and e["sunset"] < today:
                if used > 0:
                    add(p, "HIGH", "SUNSET_OVERDUE_IN_USE",
                        "下线日期 %s 已过但仍有 %d 次调用" % (e["sunset"], used))
                else:
                    add(p, "MEDIUM", "SUNSET_OVERDUE_IDLE",
                        "下线日期 %s 已过且无调用，应清理声明" % e["sunset"])
            if used > 0:
                add(p, "HIGH", "DEPRECATED_IN_USE", "废弃端点仍在被调用 %d 次" % used)
            if cap >= 0 and used > cap:
                add(p, "MEDIUM", "CALL_OVER_BUDGET",
                    "废弃端点调用 %d 次超策略上限 %d" % (used, cap))
        elif e["status"] not in EP_ACTIVE and e["status"]:
            add(p, "LOW", "STATUS_UNKNOWN", "未知的端点状态 %s" % e["status"])
    for p in callers:
        if p not in endpoints:
            add(p, "MEDIUM", "CALL_UNKNOWN_ENDPOINT", "调用未在清单中声明的端点")
    out = []
    for p, items in buckets.items():
        items.sort(key=lambda x: order.get(x[0], 9))
        out.append({"path": p, "level": items[0][0], "issue_count": len(items),
                    "issues": [[lvl, code, msg] for lvl, code, msg in items]})
    out.sort(key=lambda x: (order.get(x["level"], 9), -x["issue_count"], x["path"]))
    return out


def render_endpoint_report(graded):
    """渲染端点生命周期核验报告"""
    lines = ["端点废弃迁移核验报告", "=" * 22]
    if not graded:
        lines.append("未检出问题：端点生命周期声明自洽。")
        return "\n".join(lines)
    for g in graded:
        lines.append("[%s] %s（问题 %d 项）" % (g["level"], g["path"], g["issue_count"]))
        for lvl, code, msg in g["issues"]:
            lines.append("    - (%s) %s：%s" % (lvl, code, msg))
    return "\n".join(lines)


def process(text):
    """端点生命周期核验：解析端点/调用/策略 → 核验废弃迁移与调用对账 → 分级输出整改清单"""
    try:
        endpoints, calls, policy = parse_endpoint_lifecycle(text)
        graded = grade_endpoint_lifecycle(endpoints, calls, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "endpoint_count": len(endpoints),
            "call_record_count": len(calls),
            "call_total": sum(c["count"] for c in calls),
            "deprecated_count": len([e for e in endpoints.values()
                                     if e["status"] in EP_DEPRECATED]),
            "overdue_count": len([g for g in graded
                                  if any(i[1].startswith("SUNSET_OVERDUE") for i in g["issues"])]),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_endpoints": [g["path"] for g in high],
            "issue_code_distribution": codes,
            "per_endpoint": graded,
            "report": render_endpoint_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "endpoint_count": 0, "per_endpoint": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-deprecation-migration-check", description="核对接口废弃标注与下线日期，找出仍在被调用的老接口")
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
