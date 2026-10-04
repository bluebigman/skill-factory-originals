#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api-body-mapper — 接口调试 字段映射 嵌套请求体

把点号路径与数组下标的扁平键值对映射为嵌套请求体，检测重复赋值与数组空洞

领域：接口/API 调试（平台下载量 932 断层第一）
能力：将点号路径与数组下标的扁平键值对映射为嵌套请求体、检测重复赋值与数组空洞
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



SEGMENT_RE = re.compile(r"^([^\[\]]*)((?:\[\d+\])*)$")
INDEX_RE = re.compile(r"\[(\d+)\]")


def parse_flat_pairs(text):
    """解析 key=value 行；key 支持点号路径与数组下标

    示例：
        user.name=张三
        user.tags[0]=vip
        order.items[1].sku=A-100
    """
    pairs = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        pairs.append({"line": lineno, "path": key.strip(), "value": val.strip()})
    return pairs


def split_path(path):
    """把点号路径拆成 token 序列：[('key', 名) | ('idx', 整数)]"""
    tokens = []
    for part in path.split("."):
        if not part:
            continue
        m = SEGMENT_RE.match(part)
        if not m:
            tokens.append(("key", part))
            continue
        head, idxs = m.group(1), m.group(2)
        if head:
            tokens.append(("key", head))
        for idx in INDEX_RE.findall(idxs):
            tokens.append(("idx", int(idx)))
    return tokens


def assign_path(root, tokens, value, path):
    """按 token 序列写入嵌套结构，返回冲突说明（无冲突返回 None）"""
    cur = root
    for i, (kind, name) in enumerate(tokens):
        last = (i == len(tokens) - 1)
        if kind == "key":
            if last:
                if isinstance(cur, dict) and name in cur and cur[name] != value:
                    return "%s 重复赋值：%r → %r" % (path, cur[name], value)
                if isinstance(cur, dict):
                    cur[name] = value
                return None
            if not isinstance(cur, dict):
                return "%s 路径冲突：期望对象，实际为 %r" % (path, type(cur).__name__)
            if name not in cur or not isinstance(cur[name], (dict, list)):
                cur[name] = {} if tokens[i + 1][0] == "key" else []
            cur = cur[name]
        else:
            if not isinstance(cur, list):
                return "%s 下标路径与已有对象冲突" % path
            while len(cur) <= name:
                cur.append(None)
            if last:
                if cur[name] not in (None, value):
                    return "%s 下标 %d 重复赋值" % (path, name)
                cur[name] = value
                return None
            if not isinstance(cur[name], (dict, list)):
                cur[name] = {} if tokens[i + 1][0] == "key" else []
            cur = cur[name]
    return None


def to_nested(pairs):
    """批量转换为嵌套结构，并收集冲突与数组空洞"""
    root, conflicts = {}, []
    for p in pairs:
        tokens = split_path(p["path"])
        if not tokens:
            conflicts.append({"line": p["line"], "path": p["path"], "msg": "路径为空"})
            continue
        if tokens[-1][0] == "idx":
            conflicts.append({"line": p["line"], "path": p["path"], "msg": "路径以数组下标结尾"})
            continue
        msg = assign_path(root, tokens, p["value"], p["path"])
        if msg:
            conflicts.append({"line": p["line"], "path": p["path"], "msg": msg})
    return root, conflicts


def find_holes(node, path="", out=None):
    """定位数组空洞（下标不连续处），便于调用方补齐"""
    out = [] if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            find_holes(v, path + ("." if path else "") + str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if v is None:
                out.append({"path": path + "[%d]" % i, "msg": "数组元素缺失"})
            else:
                find_holes(v, path + "[%d]" % i, out)
    return out


def depth_of(node, depth=0):
    """最大嵌套深度"""
    if isinstance(node, dict):
        return max([depth] + [depth_of(v, depth + 1) for v in node.values()])
    if isinstance(node, list):
        return max([depth] + [depth_of(v, depth + 1) for v in node])
    return depth


def count_leaves(node):
    """叶子字段计数"""
    if isinstance(node, dict):
        return sum(count_leaves(v) for v in node.values()) if node else 0
    if isinstance(node, list):
        return sum(count_leaves(v) for v in node) if node else 0
    return 1


def render_nested(node, indent=2, level=0):
    """嵌套结构预览（JSON 文本，供直接粘贴到请求体）"""
    return json.dumps(node, ensure_ascii=False, indent=indent)


def process(text):
    """V9：扁平键值对 → 路径解析 → 嵌套请求体 → 冲突与空洞体检"""
    pairs = parse_flat_pairs(text)
    if not pairs:
        return {"ok": False, "error": "未识别到 key=value 行（示例：user.tags[0]=vip）",
                "variant": "V9"}
    nested, conflicts = to_nested(pairs)
    holes = find_holes(nested)
    hard = [c for c in conflicts if "重复赋值" in c["msg"] or "冲突" in c["msg"]]
    return {"ok": not hard and not holes, "variant": "V9",
            "conclusion": "{} 个扁平字段 → {} 层嵌套 / {} 个叶子字段；冲突 {} 项、空洞 {} 项".format(
                len(pairs), depth_of(nested), count_leaves(nested), len(conflicts), len(holes)),
            "input_count": len(pairs),
            "max_depth": depth_of(nested),
            "leaf_count": count_leaves(nested),
            "top_level_keys": sorted(nested.keys()),
            "conflicts": conflicts,
            "holes": holes,
            "nested_body": nested,
            "body_preview": render_nested(nested),
            "next_action": "无冲突可直接作为请求体提交；有冲突须先确认字段归属（对象还是数组）",
            "content_id": stable_id(text)}



def build_parser():
    p = argparse.ArgumentParser(prog="api-body-mapper", description="把点号路径与数组下标的扁平键值对映射为嵌套请求体，检测重复赋值与数组空洞")
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
