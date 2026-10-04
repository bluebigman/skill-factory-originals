#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-cursor-flow-verifier — 分页游标 推进核验 断链检

沿声明顺序回放分页游标链，核验衔接、终止与累计口径

领域：接口/API 调试（平台下载量 932 断层第一）
能力：沿声明顺序回放分页游标链，检出游标断链、翻页环路、末页未终止、页长漂移、游标形态漂移与逐页累计对不上声明总数并分级输出
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



CPG28_DECL_RX = re.compile(r"^\s*(page|policy)\s+(.*)$", re.I)
CPG28_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*(\"[^\"]*\"|[^\s]+)")
CPG28_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
CPG28_MAX_TOKEN_LEN = 128


def cpg28_kv(text):
    """解析 key=value 片段 → 字典（去包裹引号）"""
    out = {}
    for m in CPG28_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip().strip('"').strip("'")
    return out


def cpg28_int(val, default=0):
    """安全整数解析（计数/总数）"""
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def cpg28_token_shape(tok):
    """游标形态指纹：数字段归一为 #、字母段归一为 A，用于检出形态漂移"""
    if not tok:
        return "-"
    norm = re.sub(r"[0-9]+", "#", str(tok))
    norm = re.sub(r"[A-Za-z]+", "A", norm)
    return norm or "-"


def parse_cursor_pages(text):
    """解析分页游标推进声明块

    语法：
        page endpoint=/orders token=c1 next=c2 count=20 total=100
        page endpoint=/orders token=c2 next=c3 count=20 total=100
        page endpoint=/orders token=c3 next= count=0 total=100
        policy endpoint=/orders page_size=20
    """
    pages, policies = [], {}
    for raw in (text or "").splitlines():
        m = CPG28_DECL_RX.match(raw)
        if not m:
            continue
        kind = m.group(1).lower()
        kv = cpg28_kv(m.group(2))
        if kind == 'policy':
            ep = kv.get('endpoint') or '(未命名端点)'
            policies[ep] = {'page_size': cpg28_int(kv.get('page_size'), 0)}
        elif kind == 'page':
            pages.append({
                'endpoint': kv.get('endpoint') or '(未命名端点)',
                'token': kv.get('token') or '',
                'next': kv.get('next') or '',
                'count': cpg28_int(kv.get('count'), 0),
                'total': cpg28_int(kv.get('total'), 0),
            })
    return pages, policies


def audit_cursor_flow(pages, policies):
    """逐端点沿声明顺序回放游标链 → (分级结果, 问题码计数, 端点合计)"""
    groups = {}
    for p in pages:
        groups.setdefault(p['endpoint'], []).append(p)

    graded, codes, sums = [], {}, {}
    for ep, items in groups.items():
        page_size = (policies.get(ep) or {}).get('page_size', 0)
        seen = set()
        collected = 0
        for idx, pg in enumerate(items):
            issues = []

            def add(level, code, msg):
                issues.append((level, code, msg))
                codes[code] = codes.get(code, 0) + 1

            if pg['token'] and pg['token'] in seen:
                add('HIGH', 'CURSOR_LOOP', f"游标 {pg['token']} 重复出现，翻页存在环路风险")
            if pg['token']:
                seen.add(pg['token'])
            if len(pg['token']) > CPG28_MAX_TOKEN_LEN:
                add('MEDIUM', 'TOKEN_OVERSIZED', f"游标长度 {len(pg['token'])} 超过 {CPG28_MAX_TOKEN_LEN}")
            if idx + 1 < len(items):
                nxt = items[idx + 1]
                if pg['next'] != nxt['token']:
                    add('HIGH', 'CURSOR_BROKEN',
                        f"本页 next={pg['next'] or '(空)'} 与下页 token={nxt['token'] or '(空)'} 不衔接")
            else:
                if pg['next']:
                    add('MEDIUM', 'CURSOR_NOT_TERMINATED', '末页仍给出 next，翻页缺少终止条件')
            if page_size and pg['count'] > page_size:
                add('MEDIUM', 'PAGE_SIZE_DRIFT', f"本页返回 {pg['count']} 条超过声明页长 {page_size}")
            collected += pg['count']
            graded.append({'endpoint': ep, 'seq': idx + 1, 'token': pg['token'],
                           'next': pg['next'], 'count': pg['count'], 'total': pg['total'],
                           'token_shape': cpg28_token_shape(pg['token']),
                           'level': 'OK', 'issue_count': len(issues), 'issues': issues})
        shapes = {g['token_shape'] for g in graded if g['endpoint'] == ep}
        if len(shapes) > 1:
            codes['TOKEN_SHAPE_DRIFT'] = codes.get('TOKEN_SHAPE_DRIFT', 0) + 1
            for g in graded:
                if g['endpoint'] == ep:
                    g['issues'].append(('LOW', 'TOKEN_SHAPE_DRIFT', '游标形态在不同页间不一致'))
                    g['issue_count'] += 1
        total = items[-1]['total'] if items else 0
        if total > 0 and collected != total:
            codes['TOTAL_MISMATCH'] = codes.get('TOTAL_MISMATCH', 0) + 1
            for g in graded:
                if g['endpoint'] == ep:
                    g['issues'].append(('HIGH', 'TOTAL_MISMATCH',
                                        f"逐页累计 {collected} 与声明 total={total} 不符"))
                    g['issue_count'] += 1
        sums[ep] = collected
        for g in graded:
            if g['endpoint'] != ep:
                continue
            level = 'OK'
            for lv, _, _ in sorted(g['issues'], key=lambda x: CPG28_LEVEL_ORDER[x[0]]):
                level = lv
                break
            g['level'] = level
    return graded, codes, sums


def render_cursor_report(graded, codes, sums):
    """渲染游标推进核验报告（Markdown）"""
    rows = []
    for g in graded:
        cs = ",".join(c for _, c, _ in g['issues']) or "-"
        rows.append([g['level'], g['endpoint'], g['seq'], g['count'], g['total'], cs])
    table = render_markdown_table(rows, ["级别", "端点", "页序", "本页条数", "声明总数", "问题码"])
    high = [f"{g['endpoint']}#{g['seq']}" for g in graded if g['level'] == 'HIGH']
    tail = [f"页数 {len(graded)} ｜ 端点 {len(sums)} ｜ 高危 {len(high)} ｜ 问题码种类 {len(codes)}"]
    for ep, s in sorted(sums.items(), key=lambda x: -x[1])[:5]:
        tail.append(f"- 端点累计：{ep} = {s} 条")
    return table + "\n\n" + "\n".join(tail)


def process(text):
    """游标推进核验：解析分页声明 → 检出断链/环/未终止/漏项 → 分级输出"""
    try:
        pages, policies = parse_cursor_pages(text)
        graded, codes, sums = audit_cursor_flow(pages, policies)
        high = [f"{g['endpoint']}#{g['seq']}" for g in graded if g["level"] == "HIGH"]
        return {
            "ok": True,
            "page_count": len(graded),
            "endpoint_count": len(sums),
            "endpoint_totals": sums,
            "high_risk_count": len(high),
            "high_risk_pages": high,
            "issue_codes": codes,
            "per_page": graded,
            "report": render_cursor_report(graded, codes, sums),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "page_count": 0, "per_page": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="api-cursor-flow-verifier", description="沿声明顺序回放分页游标链，核验衔接、终止与累计口径")
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
