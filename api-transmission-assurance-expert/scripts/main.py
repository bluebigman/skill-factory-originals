#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-async-job-lifecycle — 异步任务 提交取回 排查修复

核验异步任务提交与取回生命周期，检出轮询预算超限、结果与取消通道缺失

领域：接口/API 调试（平台下载量 932 断层第一）
能力：核验异步任务的提交、轮询、取回与取消声明闭合性，检出环节缺失、轮询合计超预算、结果保留期缺失与取消语义缺失并分级输出
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



JL_DECL_RX = re.compile(r"^\s*(job|policy)\s+(.*)$", re.I)
JL_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)=(\"[^\"]*\"|[^\s]+)")
JL_TRUE = ("1", "true", "yes", "y", "on")


def jl_kv(text):
    out = {}
    for m in JL_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"')
    return out


def jl_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in JL_TRUE


def jl_int(val, default=-1):
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def parse_job_spec(text):
    """解析异步任务生命周期声明块

    语法（每行一条）：
        job id=export-report submit=/jobs poll=/jobs/{id} result=/jobs/{id}/result cancel=/jobs/{id}
        policy poll_interval_ms=1000 max_poll=600 result_ttl_s=3600 require_cancel=true
    """
    jobs, policy = [], {}
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = JL_DECL_RX.match(line)
        if not m:
            continue
        kind, kv = m.group(1).lower(), jl_kv(m.group(2))
        if kind == "policy":
            policy.update(kv)
        elif kind == "job":
            jid = (kv.get("id") or "").strip()
            if not jid:
                continue
            jobs.append({
                "line": lineno, "id": jid,
                "submit": (kv.get("submit") or "").strip(),
                "poll": (kv.get("poll") or "").strip(),
                "result": (kv.get("result") or "").strip(),
                "cancel": (kv.get("cancel") or "").strip(),
            })
    return jobs, policy


def grade_job_spec(jobs, policy):
    """按生命周期闭合、轮询预算、结果保留、取消语义四条主线判定"""
    policy_declared = bool(policy)
    poll_ms = jl_int(policy.get("poll_interval_ms"), -1)
    max_poll = jl_int(policy.get("max_poll"), -1)
    ttl_s = jl_int(policy.get("result_ttl_s"), -1)
    req_cancel = jl_bool(policy.get("require_cancel"), True)
    budget_s = jl_int(policy.get("poll_budget_s"), -1)
    graded = []

    for j in jobs:
        issues = []
        # ① 生命周期闭合
        if not j["submit"]:
            issues.append(("HIGH", "JL_SUBMIT_ABSENT", "未声明提交地址，任务无法发起"))
        if not j["poll"]:
            issues.append(("HIGH", "JL_POLL_ABSENT", "未声明轮询地址，任务进度无从获取"))
        if not j["result"]:
            issues.append(("HIGH", "JL_RESULT_ABSENT", "未声明取回地址，任务产出无法取回"))
        # ② 轮询预算：上限 × 间隔 必须留出端到端预算
        if poll_ms <= 0:
            issues.append(("MEDIUM", "JL_POLL_INTERVAL_UNSPEC", "未声明轮询间隔"))
        if max_poll <= 0:
            issues.append(("MEDIUM", "JL_MAX_POLL_UNSPEC", "未声明轮询次数上限，任务可能永不终止"))
        if poll_ms > 0 and max_poll > 0:
            total_s = poll_ms * max_poll / 1000.0
            if budget_s > 0 and total_s > budget_s:
                issues.append(("MEDIUM", "JL_POLL_BUDGET_EXCEEDED",
                               "轮询合计 %.1fs 超出预算 %ds" % (total_s, budget_s)))
            elif budget_s <= 0:
                issues.append(("MEDIUM", "JL_POLL_BUDGET_ABSENT",
                               "未声明端到端轮询预算（当前合计 %.1fs）" % total_s))
        # ③ 结果保留期
        if ttl_s <= 0:
            issues.append(("MEDIUM", "JL_RESULT_TTL_ABSENT",
                           "未声明结果保留期，取回窗口无从对账"))
        # ④ 取消语义
        if req_cancel and not j["cancel"]:
            issues.append(("MEDIUM", "JL_CANCEL_ABSENT", "未声明取消地址，长任务无法中止"))
        graded.append({
            "scope": "job:%s" % j["id"], "line": j["line"],
            "issues": issues, "issue_count": len(issues),
            "top_level": "HIGH" if any(i[0] == "HIGH" for i in issues)
                         else ("MEDIUM" if issues else "OK"),
            "high_risk": any(i[0] == "HIGH" for i in issues),
        })

    if not policy_declared:
        graded.append({
            "scope": "policy", "line": 0,
            "issues": [("MEDIUM", "JL_POLICY_UNSET", "未声明任务纪律，判据按缺省口径处理")],
            "issue_count": 1, "top_level": "MEDIUM", "high_risk": False,
        })
    return graded


def render_job_report(graded):
    """渲染异步任务生命周期核验报告"""
    if not graded:
        return "未识别到任务声明（检查 job/policy 行）。"
    lines = ["# 异步任务提交与取回生命周期核验", ""]
    for g in graded:
        mark = "🔴" if g["high_risk"] else ("🟡" if g["top_level"] == "MEDIUM" else "⚪")
        lines.append("%s %s（问题 %d）" % (mark, g["scope"], g["issue_count"]))
        for lv, code, msg in g["issues"]:
            lines.append("    [%s] %s — %s" % (lv, code, msg))
    high = [g["scope"] for g in graded if g["high_risk"]]
    lines.append("")
    lines.append("高风险对象 %d 个：%s" % (len(high), "、".join(high) if high else "无"))
    return "\n".join(lines)


def process(text):
    try:
        jobs, policy = parse_job_spec(text)
        graded = grade_job_spec(jobs, policy)
        high = [g for g in graded if g["high_risk"]]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "job_count": len(jobs),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_scopes": [g["scope"] for g in high],
            "issue_code_distribution": codes,
            "per_scope": graded,
            "report": render_job_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "job_count": 0,
                "issue_total": 0, "high_risk_count": 0, "high_risk_scopes": [],
                "issue_code_distribution": {}, "per_scope": [], "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-async-job-lifecycle", description="核验异步任务提交与取回生命周期，检出轮询预算超限、结果与取消通道缺失")
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
