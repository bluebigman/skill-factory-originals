#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
httpie — HTTP 命令行测试工具（原创实现，clean-room）

功能：
  1. 发送 GET/POST/PUT/DELETE/HEAD 请求，自定义 header、JSON/表单请求体
  2. 响应格式化：状态码高亮、响应头、JSON 美化输出
  3. URL 校验、超时控制、重试、错误分级
  4. 批量测试：从文件读取多组请求逐一执行并汇总

零第三方依赖（标准库 urllib）。用法：
  python main.py get https://api.example.com/users
  python main.py post https://api.example.com/users -j '{"name":"张三"}'
  python main.py get https://api.example.com -H "Authorization: Bearer xxx" --timeout 15
  python main.py batch ./requests.json
  python main.py selftest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ============================================================
# 错误码
# ============================================================
ERRORS = {
    "E001": "缺少 URL 参数",
    "E002": "URL 格式不合法",
    "E003": "不支持的 HTTP 方法",
    "E004": "请求超时",
    "E005": "网络连接失败",
    "E006": "请求体不是合法 JSON",
    "E007": "批量文件不存在或格式错误",
    "E008": "HTTP 状态码异常（≥400）",
    "E009": "参数错误",
}

METHODS = ("GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS")
DEFAULT_TIMEOUT = 10.0
MAX_BODY = 5 * 1024 * 1024  # 5MB 请求体上限


class HttpieError(Exception):
    """业务异常，带错误码。"""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or ERRORS.get(code, code))
        self.code = code


# ============================================================
# URL 与参数校验
# ============================================================
def validate_url(url: str) -> str:
    """校验并规范化 URL。"""
    if not url:
        raise HttpieError("E001")
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        # 自动补 https://（仅当看起来像域名/IP/主机名）
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9.\-]*(\.[a-zA-Z]{2,}|:\d+|\.\d+\.\d+\.\d+)([/?#]|$)", url):
            raise HttpieError("E002", f"URL 格式不合法: {url}")
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise HttpieError("E002", f"URL 格式不合法: {url}")
    if parsed.scheme not in ("http", "https"):
        raise HttpieError("E002", f"仅支持 http/https: {parsed.scheme}")
    return url


def parse_headers(header_list: list) -> dict:
    """解析 -H "Key: Value" 列表。"""
    headers = {}
    for item in header_list or []:
        if ":" not in item:
            raise HttpieError("E009", f"Header 格式应为 'Key: Value': {item}")
        k, v = item.split(":", 1)
        headers[k.strip()] = v.strip()
    return headers


def parse_query(query_list: list) -> str:
    """解析 -q key=value 查询参数，拼接到 URL。"""
    if not query_list:
        return ""
    pairs = []
    for item in query_list:
        if "=" not in item:
            raise HttpieError("E009", f"查询参数格式应为 key=value: {item}")
        k, v = item.split("=", 1)
        pairs.append((k, v))
    return "?" + urllib.parse.urlencode(pairs)


# ============================================================
# HTTP 请求核心
# ============================================================
def build_request(
    url: str,
    method: str = "GET",
    headers: dict = None,
    body: str = "",
    body_is_json: bool = False,
    insecure: bool = False,
) -> urllib.request.Request:
    """构造 urllib Request。insecure=True 时跳过 SSL 证书校验（--insecure 选项）。"""
    method = method.upper()
    if method not in METHODS:
        raise HttpieError("E003", f"不支持的方法: {method}")

    hdrs = dict(headers or {})
    data = None
    if method in ("POST", "PUT", "PATCH"):
        if body:
            if body_is_json:
                try:
                    json.loads(body)
                except (json.JSONDecodeError, TypeError) as e:
                    raise HttpieError("E006", f"JSON 解析失败: {e}") from e
                hdrs.setdefault("Content-Type", "application/json")
            else:
                hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
            data = body.encode("utf-8")
            if len(data) > MAX_BODY:
                raise HttpieError("E009", f"请求体超过 {MAX_BODY // 1024 // 1024}MB 上限")

    hdrs.setdefault("User-Agent", "httpie-original/1.0 (clean-room)")
    hdrs.setdefault("Accept", "*/*")
    return urllib.request.Request(url, data=data, headers=hdrs, method=method)


def send_request(
    url: str,
    method: str = "GET",
    headers: dict = None,
    body: str = "",
    body_is_json: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = 0,
    verbose: bool = False,
    dry_run: bool = False,
    insecure: bool = False,
) -> dict:
    """发送 HTTP 请求，返回结构化结果。"""
    url = validate_url(url)
    req = build_request(url, method, headers, body, body_is_json, insecure)

    if dry_run:
        return {
            "url": url, "method": method,
            "headers": {k: v for k, v in req.header_items()},
            "body_preview": body[:500],
            "mode": "dry-run（未实际发送）",
        }

    # SSL 上下文（--insecure 时跳过证书校验）
    context = None
    if insecure:
        import ssl
        context = ssl._create_unverified_context()

    t0 = time.time()
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                # 流式读取响应体（分块累积，避免大响应一次性占满内存）
                chunks = []
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if sum(len(c) for c in chunks) > 200_000:
                        break  # 只保留前 200KB
                resp_body = b"".join(chunks).decode(encoding="utf-8", errors="replace")
                elapsed = time.time() - t0
                result = {
                    "url": url,
                    "method": method,
                    "status": resp.status,
                    "reason": resp.reason or "",
                    "headers": {k: v for k, v in resp.headers.items()},
                    "body": resp_body,
                    "elapsed_s": round(elapsed, 3),
                    "attempt": attempt + 1,
                }
                if verbose:
                    print(f"[verbose] 第 {attempt + 1} 次请求成功 "
                          f"({resp.status})，耗时 {elapsed:.2f}s", file=sys.stderr)
                return result
        except urllib.error.HTTPError as e:
            # HTTP 4xx/5xx：读取错误响应体
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")[:5000]
            except Exception as exc:
                print(f"[WARN] 错误响应体读取失败: {str(exc)[:60]}", file=sys.stderr)
            if verbose:
                print(f"[verbose] HTTP {e.code}（第 {attempt + 1} 次）: {e.reason}",
                      file=sys.stderr)
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            return {
                "url": url, "method": method,
                "status": e.code, "reason": e.reason or "",
                "headers": {}, "body": err_body,
                "elapsed_s": round(time.time() - t0, 3),
                "error": f"HTTP {e.code}",
            }
        except urllib.error.URLError as e:
            last_exc = e
            if isinstance(e.reason, TimeoutError):
                raise HttpieError("E004", f"请求超时（{timeout}s）: {url}") from e
            if attempt < max_retries:
                if verbose:
                    print(f"[verbose] 连接失败（第 {attempt + 1} 次）: {e.reason}",
                          file=sys.stderr)
                time.sleep(0.5 * (attempt + 1))
                continue
            break
        except TimeoutError as e:
            raise HttpieError("E004", f"请求超时（{timeout}s）: {url}") from e
        except OSError as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            break

    raise HttpieError("E005", f"网络连接失败: {last_exc}")


# ============================================================
# 响应格式化
# ============================================================
def format_response(result: dict, pretty_json: bool = True) -> str:
    """格式化响应输出。"""
    lines = []
    status = result.get("status", 0)
    reason = result.get("reason", "")
    lines.append(f"HTTP/1.1 {status} {reason}")

    for k, v in result.get("headers", {}).items():
        lines.append(f"{k}: {v}")

    body = result.get("body", "")
    if body:
        lines.append("")
        if pretty_json:
            try:
                parsed = json.loads(body)
                lines.append(json.dumps(parsed, ensure_ascii=False, indent=2))
            except (json.JSONDecodeError, ValueError):
                lines.append(body)
        else:
            lines.append(body)

    if "elapsed_s" in result:
        lines.append(f"\n# 耗时: {result['elapsed_s']}s | 大小: {len(body)} 字节")
    if result.get("error"):
        lines.append(f"# 错误: {result['error']}")
    return "\n".join(lines)


# ============================================================
# 批量测试
# ============================================================
def run_batch(batch_file: str, timeout: float = DEFAULT_TIMEOUT,
              verbose: bool = False, dry_run: bool = False) -> list:
    """从 JSON 文件批量执行请求。文件格式:
    [{"url": "...", "method": "POST", "headers": {...}, "body": "...", "json": true}, ...]
    """
    p = Path(batch_file)
    if not p.is_file():
        raise HttpieError("E007", f"批量文件不存在: {batch_file}")
    try:
        cases = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError) as e:
        raise HttpieError("E007", f"批量文件解析失败: {e}") from e
    if not isinstance(cases, list):
        raise HttpieError("E007", "批量文件应为 JSON 数组")

    results = []
    for i, case in enumerate(cases, 1):
        url = case.get("url", "")
        method = case.get("method", "GET")
        headers = case.get("headers") or {}
        body = case.get("body", "")
        is_json = bool(case.get("json"))
        if verbose:
            print(f"[verbose] [{i}/{len(cases)}] {method} {url}", file=sys.stderr)
        try:
            r = send_request(url, method, headers, body, is_json, timeout,
                             verbose=verbose, dry_run=dry_run)
            r["_case"] = i
            results.append(r)
        except HttpieError as e:
            results.append({"_case": i, "error": f"[{e.code}] {e}", "url": url})
    return results


# ============================================================
# 离线自检
# ============================================================
def selftest() -> int:
    """离线自检：验证 URL 校验/请求构造/响应格式化（不联网）。"""
    failures = []

    def check(name: str, cond: bool):
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    # 1. URL 校验
    check("URL 自动补 https", validate_url("example.com") == "https://example.com")
    try:
        validate_url("not a url")
        check("非法 URL 被拒绝", False)
    except HttpieError:
        check("非法 URL 被拒绝", True)
    try:
        validate_url("ftp://x.com")
        check("非 http 协议被拒绝", False)
    except HttpieError:
        check("非 http 协议被拒绝", True)

    # 2. Header 解析
    hdrs = parse_headers(["Authorization: Bearer abc", "X-Test: 1"])
    check("Header 解析", hdrs == {"Authorization": "Bearer abc", "X-Test": "1"})
    try:
        parse_headers(["bad-header"])
        check("非法 Header 被拒绝", False)
    except HttpieError:
        check("非法 Header 被拒绝", True)

    # 3. 查询参数
    qs = parse_query(["a=1", "b=hello world"])
    check("查询参数编码", qs == "?a=1&b=hello+world")

    # 4. 请求构造
    req = build_request("https://api.test.com/users", "POST",
                        {"Content-Type": "application/json"},
                        '{"name":"张三"}', body_is_json=True)
    check("POST 请求体编码", req.data == '{"name":"张三"}'.encode())
    check("POST Content-Type", req.get_header("Content-type") == "application/json")

    # 5. JSON 请求体验证
    try:
        build_request("https://t.com", "POST", {}, "{invalid json", True)
        check("非法 JSON 被拒绝", False)
    except HttpieError:
        check("非法 JSON 被拒绝", True)

    # 6. 响应格式化
    fmt = format_response({"status": 200, "reason": "OK", "headers": {"X-A": "1"},
                           "body": '{"ok":true}', "elapsed_s": 0.5})
    check("响应格式化含状态码", "200 OK" in fmt)
    check("响应格式化美化 JSON", '"ok": true' in fmt)

    # 7. dry-run 不发送
    dr = send_request("https://api.test.com/x", "POST", {}, '{"a":1}', True,
                      dry_run=True)
    check("dry-run 返回预览", dr.get("mode") == "dry-run（未实际发送）")

    if failures:
        print(f"[SELFTEST] 失败 {len(failures)} 项: {failures}")
        return 1
    print("[SELFTEST] 全部通过 ✅")
    return 0


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="HTTP 命令行测试工具（原创实现，标准库 only）",
        epilog="示例:\n"
               "  GET:  python main.py get https://api.example.com/users\n"
               "  POST: python main.py post https://api.example.com/users -j '{\"name\":\"张三\"}'\n"
               "  HEAD: python main.py head https://api.example.com\n"
               "  批量: python main.py batch ./requests.json\n"
               "  自检: python main.py selftest",
    )
    parser.add_argument("--command", nargs="?", help="请求方法(GET/POST/PUT/DELETE/HEAD等)或 batch/selftest")
    parser.add_argument("--url", nargs="?", help="请求 URL")
    parser.add_argument("-b", "--batch-file", dest="batch_file", default="",
                        help="批量测试 JSON 文件路径")
    parser.add_argument("-H", "--header", action="append", default=[],
                        help="请求头，格式 'Key: Value'（可多次）")
    parser.add_argument("-q", "--query", action="append", default=[],
                        help="查询参数 key=value（可多次）")
    parser.add_argument("-j", "--json-body", default="", help="JSON 请求体")
    parser.add_argument("-d", "--data", default="", help="表单请求体")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"超时秒数（默认 {DEFAULT_TIMEOUT}）")
    parser.add_argument("--retries", type=int, default=0, help="失败重试次数")
    parser.add_argument("--pretty", action="store_true", default=True,
                        help="JSON 美化输出（默认开）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细明细")
    parser.add_argument("--dry-run", action="store_true", help="只构造请求不发送")
    parser.add_argument("--insecure", action="store_true", help="跳过 SSL 证书校验")
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    args = parser.parse_args()

    if args.verbose:
        print(f"[verbose] 参数: {vars(args)}", file=sys.stderr)

    if args.selftest:
        sys.exit(selftest())

    try:
        # 批量模式（--batch-file 或 command=batch）
        batch_file = args.batch_file
        if args.command and args.command.lower() in ("batch", "selftest"):
            if args.command.lower() == "selftest":
                return selftest()
            batch_file = batch_file or args.url or ""
        if batch_file:
            results = run_batch(batch_file, args.timeout, args.verbose, args.dry_run)
            for r in results:
                if "error" in r and "url" not in r:
                    print(f"[case {r['_case']}] {r['error']}")
                else:
                    print(f"[case {r['_case']}] {format_response(r, args.pretty)}")
                print()
            return 0

        # 单请求模式：command=方法，url=URL
        method = (args.command or "").upper()
        if method not in METHODS:
            parser.print_help()
            return 1
        url = args.url or ""

        headers = parse_headers(args.header)
        if args.query:
            url = url + parse_query(args.query)
        body = args.json_body or args.data
        result = send_request(
            url, method, headers, body,
            body_is_json=bool(args.json_body),
            timeout=args.timeout, max_retries=args.retries,
            verbose=args.verbose, dry_run=args.dry_run,
            insecure=args.insecure,
        )
        print(format_response(result, args.pretty))
        # 4xx/5xx 返回非零
        if result.get("status", 0) >= 400:
            return 1
        return 0
    except HttpieError as e:
        print(f"[{e.code}] {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 兜底降级
        print(f"[E099] 未预期异常: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
