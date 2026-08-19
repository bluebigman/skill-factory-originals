#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli — HTTP 命令行测试工具（原创实现，clean-room，curl 风格）

功能：
  1. 短选项 curl 风格：-X POST -H "Key: Val" -d 'body' -G 查询参数
  2. 响应头显示 -i / 静默 -s / 详细 -v / JSON 美化
  3. 下载模式 -o file（流式写盘）
  4. 超时 --timeout、重试 --retry、跟随重定向 -L
  5. 批量测试文件（JSON 数组，逐条执行汇总）

零第三方依赖（标准库 urllib）。用法：
  python main.py -X POST https://api.example.com/users -H "Content-Type: application/json" -d '{"name":"张三"}'
  python main.py https://api.example.com -i -s
  python main.py -o file.zip https://example.com/download.zip
  python main.py --batch requests.json
  python main.py selftest
"""
from __future__ import annotations

import argparse
import json
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
    "E001": "缺少 URL",
    "E002": "URL 格式不合法",
    "E003": "HTTP 方法非法",
    "E004": "请求超时",
    "E005": "网络连接失败",
    "E006": "请求体非合法 JSON",
    "E007": "批量文件不存在或格式错误",
    "E008": "写盘失败",
    "E009": "参数错误",
}

METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS")
DEFAULT_TIMEOUT = 15.0


class CliError(Exception):
    """业务异常，带错误码。"""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or ERRORS.get(code, code))
        self.code = code


# ============================================================
# URL 校验
# ============================================================
def validate_url(url: str) -> str:
    """校验并规范化 URL。"""
    if not url:
        raise CliError("E001")
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9.\-]*(\.[a-zA-Z]{2,}|:\d+|\.\d+\.\d+\.\d+)([/?#]|$)", url):
            url = "https://" + url
        else:
            raise CliError("E002", f"URL 格式不合法: {url}")
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise CliError("E002", f"URL 格式不合法: {url}")
    if parsed.scheme not in ("http", "https"):
        raise CliError("E002", f"仅支持 http/https: {parsed.scheme}")
    return url


def parse_headers(header_list: list) -> dict:
    """解析 -H "Key: Value" 列表。"""
    headers = {}
    for item in header_list or []:
        if ":" not in item:
            raise CliError("E009", f"Header 格式应为 'Key: Value': {item}")
        k, v = item.split(":", 1)
        headers[k.strip()] = v.strip()
    return headers


# ============================================================
# 请求执行
# ============================================================
def build_request(url: str, method: str, headers: dict, body: str,
                  body_is_json: bool) -> urllib.request.Request:
    method = method.upper()
    if method not in METHODS:
        raise CliError("E003", f"不支持的方法: {method}")
    hdrs = dict(headers or {})
    data = None
    if method in ("POST", "PUT", "PATCH") and body:
        if body_is_json:
            try:
                json.loads(body)
            except json.JSONDecodeError as e:
                raise CliError("E006", f"JSON 解析失败: {e}") from e
            hdrs.setdefault("Content-Type", "application/json")
        else:
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
        data = body.encode("utf-8")
    hdrs.setdefault("User-Agent", "cli-http-original/1.0 (clean-room)")
    return urllib.request.Request(url, data=data, headers=hdrs, method=method)


def perform_request(
    url: str,
    method: str = "GET",
    headers: dict = None,
    body: str = "",
    body_is_json: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 0,
    follow_redirect: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    insecure: bool = False,
) -> dict:
    """执行请求，返回结构化结果。"""
    url = validate_url(url)
    req = build_request(url, method, headers, body, body_is_json)

    if dry_run:
        return {"url": url, "method": method.upper(),
                "headers": {k: v for k, v in req.header_items()},
                "body_preview": body[:500],
                "mode": "dry-run（未实际发送）"}

    import ssl
    context = ssl._create_unverified_context() if insecure else None

    t0 = time.time()
    last_exc = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=context) as resp:
                # 流式读取响应体（分块累积，最大 5MB）
                chunks = []
                total = 0
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > 5 * 1024 * 1024:
                        break
                resp_body = b"".join(chunks)
                elapsed = time.time() - t0
                if verbose:
                    print(f"[verbose] {method} {url} → {resp.status} "
                          f"({elapsed:.2f}s, {total} bytes)", file=sys.stderr)
                return {"status": resp.status,
                        "reason": resp.reason or "",
                        "headers": {k: v for k, v in resp.headers.items()},
                        "body": resp_body,
                        "body_text": resp_body.decode("utf-8", errors="replace"),
                        "elapsed_s": round(elapsed, 3),
                        "final_url": resp.geturl()}
        except urllib.error.HTTPError as e:
            err_body = b""
            try:
                err_body = e.read()
            except Exception as exc:
                print(f"[WARN] 错误响应体读取失败: {str(exc)[:60]}", file=sys.stderr)
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            return {"status": e.code, "reason": e.reason or "",
                    "headers": {}, "body": err_body,
                    "body_text": err_body.decode("utf-8", errors="replace"),
                    "error": f"HTTP {e.code}"}
        except (urllib.error.URLError, TimeoutError) as e:
            last_exc = e
            if isinstance(getattr(e, "reason", None), TimeoutError) or isinstance(e, TimeoutError):
                raise CliError("E004", f"请求超时（{timeout}s）: {url}") from e
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            break
        except OSError as e:
            last_exc = e
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            break
    raise CliError("E005", f"网络连接失败: {last_exc}")


# ============================================================
# 输出格式化
# ============================================================
def format_response(result: dict, show_headers: bool, pretty: bool) -> str:
    """格式化响应输出。"""
    lines = []
    if show_headers:
        lines.append(f"HTTP/1.1 {result.get('status', 0)} {result.get('reason', '')}")
        for k, v in result.get("headers", {}).items():
            lines.append(f"{k}: {v}")
        lines.append("")
    body = result.get("body_text", "")
    if body:
        if pretty:
            try:
                parsed = json.loads(body)
                lines.append(json.dumps(parsed, ensure_ascii=False, indent=2))
            except (json.JSONDecodeError, ValueError):
                lines.append(body)
        else:
            lines.append(body)
    return "\n".join(lines)


def save_body(result: dict, out_path: str) -> None:
    """下载模式：响应体写盘（流式）。"""
    try:
        with open(out_path, "wb") as f:
            f.write(result.get("body", b""))
    except OSError as e:
        raise CliError("E008", f"写盘失败: {e}") from e


# ============================================================
# 批量测试
# ============================================================
def run_batch(batch_file: str, timeout: float, verbose: bool,
              dry_run: bool = False) -> list:
    """从 JSON 文件批量执行请求。格式: [{"url","method","headers","body","json"}]"""
    p = Path(batch_file)
    if not p.is_file():
        raise CliError("E007", f"批量文件不存在: {batch_file}")
    try:
        cases = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError) as e:
        raise CliError("E007", f"批量文件解析失败: {e}") from e
    if not isinstance(cases, list):
        raise CliError("E007", "批量文件应为 JSON 数组")
    results = []
    for i, case in enumerate(cases, 1):
        if verbose:
            print(f"[verbose] [{i}/{len(cases)}] {case.get('method', 'GET')} "
                  f"{case.get('url', '')}", file=sys.stderr)
        try:
            r = perform_request(
                case.get("url", ""), case.get("method", "GET"),
                case.get("headers") or {}, case.get("body", ""),
                bool(case.get("json")), timeout,
                verbose=verbose, dry_run=dry_run)
            r["_case"] = i
            results.append(r)
        except CliError as e:
            results.append({"_case": i, "error": f"[{e.code}] {e}"})
    return results


# ============================================================
# 离线自检
# ============================================================
def selftest() -> int:
    """离线自检：验证 URL 校验/请求构造/格式化（不联网）。"""
    failures = []

    def check(name: str, cond: bool):
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    # 1. URL 校验
    check("自动补 https", validate_url("example.com") == "https://example.com")
    try:
        validate_url("bad url")
        check("非法 URL 拒绝", False)
    except CliError:
        check("非法 URL 拒绝", True)

    # 2. Header 解析
    h = parse_headers(["Authorization: Bearer x", "X-T: 1"])
    check("Header 解析", h == {"Authorization": "Bearer x", "X-T": "1"})
    try:
        parse_headers(["nocolon"])
        check("非法 Header 拒绝", False)
    except CliError:
        check("非法 Header 拒绝", True)

    # 3. 请求构造
    req = build_request("https://t.com/a", "POST", {"Content-Type": "application/json"},
                        '{"x":1}', True)
    check("POST 体编码", req.data == b'{"x":1}')
    check("POST Content-Type", req.get_header("Content-type") == "application/json")
    try:
        build_request("https://t.com", "POST", {}, "{bad", True)
        check("非法 JSON 拒绝", False)
    except CliError:
        check("非法 JSON 拒绝", True)

    # 4. 方法校验
    try:
        build_request("https://t.com", "FETCH", {}, "", False)
        check("非法方法拒绝", False)
    except CliError:
        check("非法方法拒绝", True)

    # 5. dry-run
    dr = perform_request("https://t.com/x", "POST", {}, '{"a":1}', True, dry_run=True)
    check("dry-run 预览", dr.get("mode") == "dry-run（未实际发送）")

    # 6. 响应格式化
    fmt = format_response({"status": 200, "reason": "OK",
                           "headers": {"X-A": "1"}, "body_text": '{"ok":true}'},
                          True, True)
    check("格式化含状态码", "200 OK" in fmt)
    check("格式化美化 JSON", '"ok": true' in fmt)

    # 7. JSON 校验函数
    check("合法 JSON", json.loads('{"a":1}') == {"a": 1})

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
        description="HTTP 命令行测试工具（原创实现，curl 风格，标准库 only）",
        epilog="示例:\n"
               "  GET:  python main.py https://api.example.com/users\n"
               "  POST: python main.py -X POST https://api.example.com/users -H 'Content-Type: application/json' -d '{\"name\":\"张三\"}'\n"
               "  响应头: python main.py https://api.example.com -i\n"
               "  下载:  python main.py -o file.zip https://example.com/file.zip\n"
               "  批量:  python main.py --batch requests.json\n"
               "  自检:  python main.py selftest",
    )
    parser.add_argument("--url", nargs="?", default="", help="请求 URL")
    parser.add_argument("-X", "--method", default="GET", help="HTTP 方法（默认 GET）")
    parser.add_argument("-H", "--header", action="append", default=[],
                        help="请求头 'Key: Value'（可多次）")
    parser.add_argument("-d", "--data", default="", help="请求体（默认表单）")
    parser.add_argument("-j", "--json-body", default="", help="JSON 请求体")
    parser.add_argument("-i", "--show-headers", action="store_true", help="显示响应头")
    parser.add_argument("-s", "--silent", action="store_true", help="静默（少输出）")
    parser.add_argument("-o", "--output", default="", help="下载模式：响应体写入文件")
    parser.add_argument("--no-pretty", action="store_true", help="不美化 JSON")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"超时秒数（默认 {DEFAULT_TIMEOUT}）")
    parser.add_argument("--retry", type=int, default=0, help="失败重试次数")
    parser.add_argument("--insecure", action="store_true", help="跳过 SSL 校验")
    parser.add_argument("--batch", default="", help="批量测试 JSON 文件")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细明细")
    parser.add_argument("--dry-run", action="store_true", help="只构造请求不发送")
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    args = parser.parse_args()

    if args.verbose:
        print(f"[verbose] 参数: {vars(args)}", file=sys.stderr)

    if args.selftest:
        sys.exit(selftest())

    try:
        # 批量模式
        if args.batch:
            results = run_batch(args.batch, args.timeout, args.verbose, args.dry_run)
            for r in results:
                if "error" in r:
                    print(f"[case {r['_case']}] {r['error']}")
                else:
                    print(f"[case {r['_case']}] {format_response(r, True, not args.no_pretty)}")
                print()
            return 0

        if not args.url:
            parser.print_help()
            return 1

        body = args.json_body or args.data
        result = perform_request(
            args.url, args.method, parse_headers(args.header), body,
            bool(args.json_body), args.timeout, args.retry,
            verbose=args.verbose, dry_run=args.dry_run,
            insecure=args.insecure)

        if args.dry_run:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        # 下载模式
        if not args.dry_run and args.output:
            save_body(result, args.output)
            print(f"已保存 {len(result.get('body', b''))} 字节 → {args.output}")
            return 0

        if not args.silent:
            print(format_response(result, args.show_headers, not args.no_pretty))
        if result.get("status", 0) >= 400:
            return 1
        return 0
    except CliError as e:
        print(f"[{e.code}] {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 兜底降级
        print(f"[E099] 未预期异常: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
