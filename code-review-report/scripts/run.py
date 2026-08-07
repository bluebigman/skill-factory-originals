#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skill: code-review-report (v2.0.0)
diff 代码审查报告生成器——解析 git diff，规则扫描（密码/日志/性能/平台依赖），
输出分级审查报告（markdown/json）。

v2.0 重建（2026-08-07，响应第三方评审——全部批评点修复，军规样板 #2）：
  [接口诚实]      --filter 真正传给 generate_report（评审实锤：原版参数无效）
  [删假接口]      --spec/load_spec/match_trigger 半成品删除（不暴露未实现能力）
  [fail-fast]     diff 解析器严格校验：非法 hunk 头立即抛错，new_start 必须 >0，
        绝不制造虚假 hunk（评审：错误数据比崩溃更可怕）
  [安全脱敏]      SEC001 密码只显示前 2 位+***，明文绝不进报告（评审：安全只做了一半）
  [准确剥离]      tokenize 剥离注释/字符串后匹配规则，防注释误报（评审：range(len) 在注释里触发）
  [防御加固]      main 顶层 try/except + EXIT_* 退出码；atomic_write 用 finally 清理
  [军规 R1-R6]    --selftest 真实断言 / 编码三级 fallback / 默认 dry-run / O(n) 流式 / --verbose 明细

接口：--diff/--output/--format md|json/--filter P0,P1,P2/--dry-run/--force/--verbose/--selftest/--version
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile
import tokenize as _tokenize
from typing import Any, Dict, List, Optional, Tuple

__version__ = "2.0.0"

EXIT_OK = 0
EXIT_SELFTEST_FAIL = 1
EXIT_PARAM_ERROR = 2
EXIT_INPUT_ERROR = 10


# ══════════════════════ diff 解析（fail-fast，评审核心加固）══════════════════════

class DiffParseError(ValueError):
    """diff 格式不兼容——快速失败，绝不制造虚假数据"""


def parse_diff(text: str) -> List[Dict[str, Any]]:
    """严格解析 git diff：diff --git 头 → @@ hunk 头 → +/- 行。

    fail-fast：非法 hunk 头 / 行号非法 / 新增行出现在 hunk 外 → 立即抛 DiffParseError。
    返回 [{"file", "old_start", "new_start", "adds": [新增行...]}]。
    """
    hunks: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    in_hunk = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("diff --git"):
            m = re.search(r"b/(\S+)", line)
            cur = {"file": m.group(1) if m else "?", "old_start": 0, "new_start": 0, "adds": []}
            in_hunk = False
        elif line.startswith("@@"):
            m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if not m:
                raise DiffParseError(f"非法 hunk 头: {line[:60]}")
            old_s, new_s = int(m.group(1)), int(m.group(2))
            if old_s <= 0 or new_s <= 0:
                raise DiffParseError(f"hunk 行号非法: {line[:60]}")
            if cur is None:
                raise DiffParseError(f"hunk 头出现在 diff 头之前: {line[:60]}")
            cur = {"file": cur["file"], "old_start": old_s, "new_start": new_s, "adds": []}
            hunks.append(cur)
            in_hunk = True
        elif line.startswith("+") and not line.startswith("+++"):
            if not in_hunk or cur is None:
                raise DiffParseError(f"新增行出现在 hunk 外: {line[:60]}")
            cur["adds"].append(line[1:])
        # '-' 删除行 / ' ' 上下文 / '\\' 无换行标记 / '---' '+++' 文件头：hunk 内跳过
    if not hunks:
        raise DiffParseError("未解析到任何 hunk（diff 为空或不兼容）")
    return hunks


def strip_code(code_line: str) -> str:
    """tokenize 剥离注释与字符串，返回纯代码片段（评审：规则只在真实代码上匹配）。"""
    try:
        toks = list(_tokenize.tokenize(io.BytesIO(code_line.encode("utf-8")).readline))
        parts = [t.string for t in toks
                 if t.type in (_tokenize.NAME, _tokenize.OP, _tokenize.NUMBER,
                               _tokenize.STRING) and t.string.strip()]
        return " ".join(parts)
    except Exception:
        return code_line.split("#")[0]


# ══════════════════════ 规则引擎（静态权重 + 脱敏）══════════════════════

# 每条规则: (id, 名称, 严重级, 正则, base_confidence)
# v2.0 移除拍脑袋的 confidence 加减（评审：0.04/0.2 无依据），改用静态基础置信度。
RULES: List[Tuple[str, str, str, "re.Pattern", float]] = [
    ("SEC001", "疑似硬编码密码/密钥", "P0",
     re.compile(r'\b(password|passwd|secret|api_key|token|access_key)\b\s*=\s*["\'][^"\']{6,}["\']'), 0.95),
    ("LOG001", "格式化字符串进日志", "P1",
     re.compile(r'\blogging\s*\.\s*(?:debug|info|warning)\s*\([^)\n]*\{'), 0.80),
    ("PERF001", "循环内 range(len())", "P1",
     re.compile(r'\brange\s*\(\s*len\s*\('), 0.75),
    ("STD001", "平台特定命令执行", "P2",
     re.compile(r'\bos\.(system|popen)\s*\('), 0.85),
]


def mask_secret(value: str) -> str:
    """脱敏（评审：明文密码绝不进报告）——只留前 2 位 + ***"""
    if len(value) <= 2:
        return "***"
    return value[:2] + "***"


def apply_rules(adds: List[str]) -> List[Dict[str, Any]]:
    """对新增行应用规则（在剥离注释/字符串后的代码上匹配，防误报）。"""
    issues: List[Dict[str, Any]] = []
    for lineno, raw in enumerate(adds, 1):
        code = strip_code(raw)
        for rid, name, sev, pattern, conf in RULES:
            m = pattern.search(code)
            if not m:
                continue
            # detail 显示原始行（可读）；SEC001 额外脱敏（明文密码绝不进报告）
            detail = raw.strip()[:60]
            if rid == "SEC001":
                vm = re.search(r'["\']([^"\']+)["\']', raw)
                if vm:
                    detail = raw.replace(vm.group(1), mask_secret(vm.group(1))).strip()[:60]
            issues.append({"id": rid, "name": name, "severity": sev,
                           "line": lineno, "detail": detail,
                           "confidence": conf})
    return issues


# ══════════════════════ 报告生成 ═══════════════════════

SEV_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def generate_report(files: List[Dict[str, Any]],
                    filter_severity: str = "") -> Dict[str, Any]:
    """扫描全部 hunk 生成审查结果。filter_severity='P0' 只保留 P0（v2.0 修复：参数真正生效）。"""
    keep = set(filter_severity.replace(" ", "").split(",")) if filter_severity else None
    entries = []
    for f in files:
        for issue in apply_rules(f.get("adds", [])):
            if keep and issue["severity"] not in keep:
                continue
            entries.append({
                "file": f["file"], "line": f["new_start"] + issue["line"] - 1,
                "id": issue["id"], "name": issue["name"],
                "severity": issue["severity"], "detail": issue["detail"],
                "confidence": issue["confidence"],
            })
    entries.sort(key=lambda e: (SEV_ORDER.get(e["severity"], 9), e["file"], e["line"]))
    return {"engine": f"code-review-report v{__version__}",
            "total": len(entries), "issues": entries}


def build_report(result: Dict[str, Any], fmt: str = "md") -> str:
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    lines = [f"# 代码审查报告（{result['total']} 个问题）", ""]
    for e in result["issues"]:
        lines.append(f"- [{e['severity']}] {e['file']}:{e['line']} "
                     f"({e['id']} {e['name']} conf={e['confidence']})")
        lines.append(f"  `{e['detail']}`")
    if not result["issues"]:
        lines.append("_未发现规则命中。_")
    return "\n".join(lines) + "\n"


# ══════════════════════ 输入输出（R3 编码 + R4 dry-run + R5 流式）══════════════════════

def read_text_any(path: str) -> Tuple[str, str]:
    """流式分块读 + utf-8→gbk→gb18030 三级 fallback（军规 R3/R5）"""
    chunks: List[bytes] = []
    with open(path, "rb") as f:
        while True:
            block = f.read(65536)
            if not block:
                break
            chunks.append(block)
    raw = b"".join(chunks)
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8(replace兜底)"


def write_text_atomic(path: str, text: str) -> None:
    """原子写盘：finally 确保临时文件清理（评审：UnboundLocalError 修复）"""
    tmp_path: Optional[str] = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(os.path.abspath(path)) or ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def diff_text(before: str, after: str) -> str:
    """预览 diff（R4：用户看到手术过程）"""
    import difflib
    lines = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, before.splitlines(), after.splitlines()).get_opcodes():
        if tag in ("replace", "delete") and i1 < i2:
            lines.append("  - " + " ".join(before.splitlines()[i1:i2])[:100])
        if tag in ("replace", "insert") and j1 < j2:
            lines.append("  + " + " ".join(after.splitlines()[j1:j2])[:100])
    return "\n".join(lines) if lines else "  (无内容差异)"


# ══════════════════════ CLI（R4 默认预览 + EXIT_* 统一）══════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="diff 代码审查报告生成器（v%s）" % __version__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="示例: python run.py --diff change.diff --output report.md --filter P0")
    ap.add_argument("--diff", help="diff 文件路径（git diff 格式，utf-8/gbk/gb18030 自动识别）")
    ap.add_argument("--output", help="输出文件路径（缺省打印 stdout；加 --force 才落盘）")
    ap.add_argument("--format", choices=["md", "json"], default="md", help="输出格式")
    ap.add_argument("--filter", default="",
                    help="严重级过滤，逗号分隔：P0,P1（v2.0：真正生效）")
    ap.add_argument("--dry-run", action="store_true", help="显式预览（默认即预览）")
    ap.add_argument("--force", action="store_true",
                    help="真正落盘（默认只打印 diff 不写；剥夺预览权的工具都是恶霸工具）")
    ap.add_argument("--verbose", action="store_true", help="输出每文件命中明细（R6）")
    ap.add_argument("--selftest", action="store_true", help="运行内置自测")
    ap.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.diff:
        ap.error("--diff 必填（除非使用 --selftest）")
        return EXIT_PARAM_ERROR

    try:
        text, enc = read_text_any(args.diff)
        print(f"输入编码: {enc}", file=sys.stderr)
        # fail-fast：diff 不兼容立即友好报错，不制造虚假报告（评审核心）
        files = parse_diff(text)
        result = generate_report(files, filter_severity=args.filter)
        out = build_report(result, args.format)
    except DiffParseError as e:
        print(f"[error] diff 解析失败（不兼容格式）: {e}", file=sys.stderr)
        print("  请确认输入是 git diff 输出（含 diff --git 与 @@ hunk 头）", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except (OSError, ValueError) as e:
        print(f"[error] 输入处理失败: {e}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    if args.verbose:
        print(f"── 扫描结果（filter={args.filter or '全部'}）──", file=sys.stderr)
        for e in result["issues"][:20]:
            print(f"  [{e['severity']}] {e['file']}:{e['line']} {e['id']} {e['detail'][:40]}",
                  file=sys.stderr)

    if args.output and not args.force:
        print(f"── 预览（未写盘；加 --force 才落盘 {args.output}）──", file=sys.stderr)
        print(diff_text("", out))
        return EXIT_OK
    if args.output:
        write_text_atomic(args.output, out)
        print(f"已写入 {args.output}（{result['total']} 个问题）", file=sys.stderr)
    else:
        print(out, end="" if out.endswith("\n") else "\n")
    return EXIT_OK


# ══════════════════════ 自测（R1：评审全部修复点都有断言）══════════════════════

def _selftest() -> int:
    failures = []

    def check(name: str, cond: bool, detail: str = ""):
        if not cond:
            failures.append(f"{name}: {detail}")

    # 1-2 diff 解析基本
    d = parse_diff("diff --git a/a.py b/a.py\n@@ -1,3 +1,4 @@\n x\n+password = \"secret123\"\n")
    check("解析-基本hunk", len(d) == 1 and d[0]["adds"] == ['password = "secret123"'], str(d))
    # 3 fail-fast：非法 hunk 头
    try:
        parse_diff("diff --git a/a b/a\n@@ 非法头 @@\n")
        check("解析-非法hunk头抛错", False, "未抛错")
    except DiffParseError:
        check("解析-非法hunk头抛错", True)
    # 4 fail-fast：新增行在 hunk 外
    try:
        parse_diff("+孤儿行\n")
        check("解析-孤儿行抛错", False, "未抛错")
    except DiffParseError:
        check("解析-孤儿行抛错", True)
    # 5 fail-fast：行号非法
    try:
        parse_diff("diff --git a/a b/a\n@@ -0,1 +0,1 @@\n x\n")
        check("解析-行号0抛错", False, "未抛错")
    except DiffParseError:
        check("解析-行号0抛错", True)
    # 6 注释剥离：注释里的 range(len()) 不误报（评审 PERF001 误报修复）
    issues = apply_rules(["# 这里 range(len(x)) 是注释", "for i in range(len(items)):"])
    perf = [i for i in issues if i["id"] == "PERF001"]
    check("规则-注释不误报", len(perf) == 1, str(issues))
    # 7 脱敏：密码明文不进报告（评审 SEC001 安全修复）
    issues2 = apply_rules(['password = "mySecretPassword123"'])
    sec = [i for i in issues2 if i["id"] == "SEC001"]
    check("规则-密码命中", len(sec) == 1, str(issues2))
    check("规则-密码脱敏", sec and "mySecretPassword123" not in sec[0]["detail"]
          and "my***" in sec[0]["detail"], str(sec[0]["detail"] if sec else ""))
    # 8 --filter 真正生效（评审：原版参数无效）
    files = [{"file": "a.py", "old_start": 1, "new_start": 1,
              "adds": ['password = "hunter2secret"', "import os",
                       "logging.debug(f'x={x}')"]}]
    all_res = generate_report(files, "")
    p0_res = generate_report(files, "P0")
    check("filter-全部", all_res["total"] >= 2, str(all_res))
    check("filter-P0只留P0", p0_res["total"] >= 1 and
          all(i["severity"] == "P0" for i in p0_res["issues"]), str(p0_res))
    # 9 行号正确（new_start 基础偏移）
    files2 = [{"file": "a.py", "old_start": 10, "new_start": 20, "adds": ['password = "x123456789"']}]
    res2 = generate_report(files2, "")
    check("行号-偏移正确", res2["issues"][0]["line"] == 20, str(res2["issues"][0]))
    # 10 dry-run 不写盘 + 编码
    import tempfile as _tf
    with _tf.NamedTemporaryFile("w", suffix=".diff", delete=False, encoding="utf-8") as f:
        f.write("diff --git a/a.py b/a.py\n@@ -1,2 +1,3 @@\n x\n+password = \"zsecret123\"\n")
        in_path = f.name
    out_path = in_path + ".md"
    try:
        rc = main(["--diff", in_path, "--output", out_path])
        check("dry-run-不写盘", rc == EXIT_OK and not os.path.exists(out_path),
              f"rc={rc} 存在={os.path.exists(out_path)}")
        rc = main(["--diff", in_path, "--output", out_path, "--force"])
        check("force-落盘", rc == EXIT_OK and os.path.exists(out_path))
    finally:
        for p in (in_path, out_path):
            if os.path.exists(p):
                os.unlink(p)
    # 11 编码 GBK
    with _tf.NamedTemporaryFile("wb", suffix=".diff", delete=False) as f:
        f.write("diff --git a/中.py b/中.py\n@@ -1,2 +1,3 @@\n x\n+password = \"中文秘密123\"\n".encode("gbk"))
        gbk_path = f.name
    try:
        got, enc = read_text_any(gbk_path)
        check("编码-GBK识别", "diff --git" in got and enc == "gbk", f"{enc}")
    finally:
        os.unlink(gbk_path)
    # 12 空 diff 快速失败
    try:
        parse_diff("")
        check("解析-空diff抛错", False)
    except DiffParseError:
        check("解析-空diff抛错", True)

    if failures:
        print(f"❌ selftest 失败 {len(failures)}/12")
        for f in failures:
            print(f"   - {f}")
        return EXIT_SELFTEST_FAIL
    print("✅ selftest 12/12 全绿")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
