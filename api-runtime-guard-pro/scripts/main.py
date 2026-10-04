#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-batch-throttle-planner — 接口调试 批量调用 并发节流编排

推算批量调用的配额窗口与节流间隔，按耗时预算给出拆窗与退避计划

领域：接口/API 调试（平台下载量 932 断层第一）
能力：推算批量调用的配额窗口与节流间隔、评估并发吞吐下的总耗时、按预算给出拆窗与退避计划
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



BATCH_LINE_RX = re.compile(r"^\s*batch\b(.*)$", re.I)
BATCH_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-]*)\s*=\s*([^\s]+)")


def v21_int(val, default=0):
    """自包含整数解析（WBR-085：禁引用 V19 的同名工具，防单变体注入时 NameError）"""
    try:
        return int(str(val).strip())
    except Exception:
        return default


def parse_batch_plan(text):
    """解析批量调用规格

    语法（每行一个批次）：
        batch name=全量回填 total=12000 rate_limit=600 window=60 concurrency=8
              avg_ms=180 budget_ms=120000
    """
    batches = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        m = BATCH_LINE_RX.match(raw.strip())
        if not m:
            continue
        item = {"line": lineno, "name": "", "total": 0, "rate_limit": 0,
                "window": 60, "concurrency": 1, "avg_ms": 100, "budget_ms": 0,
                "retry_ratio": 0.0}
        for k, v in BATCH_KV_RX.findall(m.group(1)):
            k, v = k.lower(), v.strip("\"'")
            if k == "name":
                item["name"] = v
            elif k in ("total", "count"):
                item["total"] = v21_int(v)
            elif k in ("rate_limit", "limit", "quota"):
                item["rate_limit"] = v21_int(v)
            elif k in ("window", "window_s", "period"):
                item["window"] = v21_int(v, 60) or 60
            elif k in ("concurrency", "workers", "parallel"):
                item["concurrency"] = max(1, v21_int(v, 1))
            elif k in ("avg_ms", "latency_ms", "p50_ms"):
                item["avg_ms"] = max(1, v21_int(v, 100))
            elif k in ("budget_ms", "deadline_ms", "slo_ms"):
                item["budget_ms"] = v21_int(v)
            elif k in ("retry_ratio", "retry"):
                try:
                    item["retry_ratio"] = float(str(v).rstrip("%")) / (100.0 if "%" in str(v) else 1.0)
                except Exception:
                    item["retry_ratio"] = 0.0
        if item["name"] or item["total"]:
            batches.append(item)
    return batches


def plan_batch(item):
    """单批次编排推算：配额窗口数 / 节流间隔 / 吞吐上限 / 总耗时 / 预算结论"""
    total = item["total"]
    quota_windows = 0
    interval_ms = 0
    if item["rate_limit"] > 0:
        quota_windows = (total + item["rate_limit"] - 1) // item["rate_limit"]
        interval_ms = int(round(item["window"] * 1000.0 / item["rate_limit"]))
    quota_ms = quota_windows * item["window"] * 1000
    per_req_ms = item["avg_ms"] * (1.0 + max(0.0, item["retry_ratio"]))
    throughput_ms = int(round(total * per_req_ms / max(1, item["concurrency"])))
    effective_ms = max(quota_ms, throughput_ms)
    binding = "配额" if quota_ms >= throughput_ms else "并发"
    over_budget = bool(item["budget_ms"]) and effective_ms > item["budget_ms"]
    suggest_conc = item["concurrency"]
    if binding == "并发" and item["avg_ms"] > 0:
        need = int(round(total * per_req_ms / max(1, item["budget_ms"] or effective_ms)))
        suggest_conc = max(item["concurrency"], need)
    elif binding == "配额" and over_budget:
        suggest_conc = item["concurrency"]
    backoff_ms = interval_ms * 2 if interval_ms else 1000
    return {"name": item["name"] or "(未命名批次)", "total": total,
            "quota_windows": quota_windows, "interval_ms": interval_ms,
            "quota_ms": quota_ms, "throughput_ms": throughput_ms,
            "effective_ms": effective_ms, "binding": binding,
            "budget_ms": item["budget_ms"], "over_budget": over_budget,
            "suggest_concurrency": suggest_conc,
            "backoff_ms_on_429": backoff_ms,
            "retry_ratio": item["retry_ratio"]}


def render_batch_plan(plans):
    """渲染批量节流编排表"""
    rows = []
    for p in plans:
        rows.append([p["name"], str(p["total"]),
                     "%d 窗 / 间隔 %dms" % (p["quota_windows"], p["interval_ms"]),
                     "%.1fs" % (p["throughput_ms"] / 1000.0),
                     "%.1fs" % (p["effective_ms"] / 1000.0), p["binding"],
                     "超预算" if p["over_budget"] else "预算内",
                     str(p["suggest_concurrency"])])
    if not rows:
        rows = [["-", "0", "-", "-", "-", "-", "-", "-"]]
    return render_markdown_table(rows, ["批次", "总量", "配额节奏", "并发吞吐",
                                        "预计总耗时", "约束方", "预算", "建议并发"])


def process(text):
    """V21：解析批量调用规格 → 推算节流节奏与并发吞吐 → 预算结论 + 退避计划"""
    batches = parse_batch_plan(text)
    if not batches:
        return {"ok": True, "variant": "V21", "batch_count": 0,
                "note": "未识别到批量调用规格（需 batch 开头行）",
                "plans": [], "report_table": "", "content_id": stable_id(text)}
    plans = [plan_batch(b) for b in batches]
    over = [p for p in plans if p["over_budget"]]
    quota_bound = [p for p in plans if p["binding"] == "配额"]
    return {"ok": True, "variant": "V21",
            "batch_count": len(plans),
            "over_budget_count": len(over),
            "quota_bound_count": len(quota_bound),
            "conclusion": "批次 {} 个；超预算 {} 个；受配额约束 {} 个；最长预计 {:.1f}s".format(
                len(plans), len(over), len(quota_bound),
                max(p["effective_ms"] for p in plans) / 1000.0),
            "over_budget_batches": [p["name"] for p in over],
            "plans": plans,
            "report_table": render_batch_plan(plans),
            "next_action": "超预算批次先申请配额上调或拆窗执行，再按建议并发复核总耗时",
            "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="api-batch-throttle-planner", description="推算批量调用的配额窗口与节流间隔，按耗时预算给出拆窗与退避计划")
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
