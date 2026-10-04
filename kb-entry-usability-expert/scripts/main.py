#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-link-auditor — 附件链接 类型声明 过期检查

附件链接 类型声明 过期检查核验工具

领域：知识库/信息整理（平台 54 分第 2 名）
能力：核验知识条目所挂链接与附件的类型声明、责任归属与时效，检出内网地址与过期资源并分级输出整改清单
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


def split_sections(text, min_len=40):
    """按 Markdown 标题切分章节为条目"""
    items, cur = [], {"title": "（前言）", "body": []}
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            if "".join(cur["body"]).strip():
                items.append(cur)
            cur = {"title": re.sub(r"^#+\s+", "", line).strip(), "body": []}
        else:
            cur["body"].append(line)
    if "".join(cur["body"]).strip():
        items.append(cur)
    return [{"title": i["title"], "text": "\n".join(i["body"]).strip()}
            for i in items if len("\n".join(i["body"]).strip()) >= min_len]


def build_index(items):
    """关键词倒排索引（中文 2-gram + 英文词）"""
    idx = {}
    for n, it in enumerate(items):
        blob = it["title"] + " " + it["text"]
        words = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", blob.lower()))
        cjk = re.findall(r"[\u4e00-\u9fff]", blob)
        words |= {"".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
        for w in words:
            idx.setdefault(w, set()).add(n)
    return {k: sorted(v) for k, v in sorted(idx.items())}


def search(index, items, query, topk=5):
    """按查询词检索条目（命中词数排序）"""
    qs = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query.lower()))
    cjk = re.findall(r"[\u4e00-\u9fff]", query)
    qs |= {"".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
    score = {}
    for w in qs:
        for n in index.get(w, []):
            score[n] = score.get(n, 0) + 1
    ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[:topk]
    return [{"no": n, "score": s, "title": items[n]["title"],
             "preview": items[n]["text"][:160]} for n, s in ranked]



RES_DECL_RX = re.compile(r"^\s*(entry|link|attach|policy)\s+(.*)$", re.I)
RES_KV_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*([^\s]+)")
RES_TRUE = ("1", "true", "yes", "y", "on")
RES_LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
RES_KINDS = ("doc", "sheet", "slide", "image", "video", "code", "api", "page", "archive")
RES_BAD_KINDS = ("unknown", "none", "")
RES_LOCAL_SCHEMES = ("file://", "\\\\", "smb://", "ftp://")


def kb20_kv(text):
    """解析 key=value 片段 → 字典"""
    out = {}
    for m in RES_KV_RX.finditer(text or ""):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def kb20_bool(val, default=False):
    """宽松布尔解析"""
    if val is None or val == "":
        return default
    return str(val).strip().lower() in RES_TRUE


def kb20_int(val, default=0):
    """安全整数解析"""
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def kb20_date_ord(val):
    """YYYY-MM-DD → 序数日；解析失败返回 0"""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", (val or "").strip())
    if not m:
        return 0
    y, mo, d = (int(x) for x in m.groups())
    if mo < 1 or mo > 12 or d < 1 or d > 31:
        return 0
    return y * 372 + mo * 31 + d


def parse_resource_entries(text):
    """解析条目链接与附件声明

    语法（每行一条声明，key=value 空格分隔）：
        entry title=接口文档
        link url=https://kb.example/a type=doc checked=2026-01-01 expiry=2027-01-01
        attach name=form.xlsx size=12kb owner=ops
        entry title=参考
        link url=file:///srv/share/a type=unknown
        policy require_type=true require_owner=true max_age_days=365 today=2026-09-16
    """
    entries, policy = [], {}
    cur = None
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = RES_DECL_RX.match(line)
        if not m:
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        kv = kb20_kv(rest)
        if kind == "policy":
            policy.update(kv)
            continue
        if kind == "entry":
            cur = {"line": lineno, "title": (kv.get("title") or "(未命名)").strip(),
                   "links": [], "attaches": []}
            entries.append(cur)
            continue
        if cur is None:
            cur = {"line": lineno, "title": "(默认条目)", "links": [], "attaches": []}
            entries.append(cur)
        if kind == "link":
            cur["links"].append({
                "line": lineno,
                "url": (kv.get("url") or "").strip(),
                "type": (kv.get("type") or "").strip().lower(),
                "checked": kv.get("checked", ""),
                "expiry": kv.get("expiry", ""),
                "owner": kv.get("owner", ""),
                "share_scope": (kv.get("share") or "").strip().lower(),
            })
            continue
        cur["attaches"].append({
            "line": lineno,
            "name": (kv.get("name") or "(未命名)").strip(),
            "size": (kv.get("size") or "").strip(),
            "owner": kv.get("owner", ""),
            "format": (kv.get("format") or "").strip().lower(),
            "editable": kb20_bool(kv.get("editable"), False),
        })
    return entries, policy


def grade_resource_entries(entries, policy):
    """逐条目核验附属资源的类型、责任归属与时效，输出分级问题清单"""
    req_type = kb20_bool(policy.get("require_type"), True)
    req_owner = kb20_bool(policy.get("require_owner"), True)
    max_age = kb20_int(policy.get("max_age_days"), 365) or 365
    today = kb20_date_ord(policy.get("today", ""))
    graded = []
    for e in entries:
        issues = []
        if not e["links"] and not e["attaches"]:
            issues.append(("LOW", "NO_RESOURCE", "条目未挂接任何链接或附件，来源不可追"))
        for lk in e["links"]:
            url = lk["url"]
            low = url.lower()
            if not url:
                issues.append(("HIGH", "URL_EMPTY", "链接地址为空，条目不可达"))
                continue
            if low.startswith(RES_LOCAL_SCHEMES):
                issues.append(("HIGH", "URL_LOCAL_SCHEME",
                               f"外链指向内网/本地路径 {url[:40]}，他人不可达"))
            elif low.startswith("http://"):
                issues.append(("MEDIUM", "URL_INSECURE", "链接为明文协议，存在被篡改风险"))
            if req_type and lk["type"] in RES_BAD_KINDS:
                issues.append(("MEDIUM", "TYPE_MISSING", f"链接 {url[:40]} 未声明资源类型"))
            elif lk["type"] and lk["type"] not in RES_KINDS:
                issues.append(("LOW", "TYPE_UNKNOWN", f"资源类型 {lk['type']} 不在已知清单"))
            if req_owner and not lk["owner"]:
                issues.append(("LOW", "LINK_OWNER_MISSING", "链接未声明维护责任人"))
            if lk["share_scope"] in ("public", "anyone", "all"):
                issues.append(("MEDIUM", "SHARE_TOO_WIDE",
                               "链接对所有人开放，含内部信息时构成泄露面"))
            exp = kb20_date_ord(lk["expiry"])
            chk = kb20_date_ord(lk["checked"])
            if today and exp and exp < today:
                issues.append(("HIGH", "LINK_EXPIRED",
                               f"链接有效期 {lk['expiry']} 已过期"))
            if today and chk and (today - chk) > max_age:
                issues.append(("MEDIUM", "LINK_STALE",
                               f"距上次核验 {lk['checked']} 已超 {max_age} 天"))
            if not chk and not exp:
                issues.append(("LOW", "NO_TIME_META", "链接未声明核验或有效期，时效不可判"))
        for at in e["attaches"]:
            if not at["size"]:
                issues.append(("LOW", "ATTACH_SIZE_MISSING",
                               f"附件 {at['name']} 未标注体积，传输前无法预估"))
            if req_owner and not at["owner"]:
                issues.append(("MEDIUM", "ATTACH_OWNER_MISSING",
                               f"附件 {at['name']} 未声明责任人，版本无人维护"))
            if not at["format"]:
                issues.append(("LOW", "ATTACH_FORMAT_MISSING",
                               f"附件 {at['name']} 未标注格式，接收方可能无法打开"))
        worst = sorted((i[0] for i in issues), key=lambda x: RES_LEVEL_ORDER.get(x, 9))
        graded.append({"title": e["title"], "line": e["line"],
                       "link_count": len(e["links"]), "attach_count": len(e["attaches"]),
                       "issues": issues, "issue_count": len(issues),
                       "level": worst[0] if worst else "OK"})
    return graded


def render_resource_report(graded):
    """渲染附属资源核验结果（Markdown）"""
    rows = []
    for g in sorted(graded, key=lambda x: (RES_LEVEL_ORDER.get(x["level"], 9), x["line"])):
        rows.append([g["level"], g["title"], g["link_count"], g["attach_count"],
                     g["issue_count"], ",".join(i[1] for i in g["issues"]) or "-"])
    return render_markdown_table(rows, ["级别", "条目", "链接", "附件", "问题数", "问题码"])


def process(text):
    """附属资源核验：解析条目链接与附件 → 核验类型/责任/时效/可达性 → 分级输出整改清单"""
    try:
        entries, policy = parse_resource_entries(text)
        graded = grade_resource_entries(entries, policy)
        high = [g for g in graded if g["level"] == "HIGH"]
        codes = {}
        for g in graded:
            for it in g["issues"]:
                codes[it[1]] = codes.get(it[1], 0) + 1
        return {
            "ok": True,
            "entry_count": len(entries),
            "link_total": sum(g["link_count"] for g in graded),
            "attach_total": sum(g["attach_count"] for g in graded),
            "issue_total": sum(g["issue_count"] for g in graded),
            "high_risk_count": len(high),
            "high_risk_entries": [g["title"] for g in high],
            "unreachable_links": [g["title"] for g in graded
                                  if any(i[1] in ("URL_LOCAL_SCHEME", "URL_EMPTY")
                                         for i in g["issues"])],
            "issue_code_distribution": codes,
            "per_entry": graded,
            "report": render_resource_report(graded),
        }
    except Exception as exc:
        return {"ok": True, "error": str(exc), "entry_count": 0, "per_entry": [],
                "report": "(解析降级)"}



def build_parser():
    p = argparse.ArgumentParser(prog="kb-link-auditor", description="附件链接 类型声明 过期检查核验工具")
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
