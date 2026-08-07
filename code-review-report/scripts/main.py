#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
code-review-report 技能实现
===========================
解析 git diff，扫描硬编码密码、不安全日志、性能反模式与平台依赖，
输出分级审查报告（Markdown / JSON）。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。

用法示例:
    python scripts/main.py review.diff
    python scripts/main.py review.diff --format json --filter P1
    python scripts/main.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 输入文件不存在
# E002: 输入文件无法读取（权限/IO）
# E003: 输入文件编码无法识别
# E004: 输入内容不是有效 diff 格式
# E005: 输出目录不存在
# E006: 输出文件写入失败
# E007: 命令行参数非法
# E008: 内部规则引擎错误
# E009: JSON 序列化失败
# E010: 未知错误


class ReviewError(Exception):
    """技能运行期错误，携带错误码。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """一条审查发现。"""
    rule_id: str          # 规则标识，如 SEC-001
    severity: str         # P0 / P1 / P2
    file: str             # 涉及文件（diff 中的路径）
    line: int             # 行号（尽力提取，失败为 0）
    message: str          # 人类可读描述
    snippet: str = ""     # 命中代码片段（脱敏后）


@dataclass
class ReviewReport:
    """审查报告聚合。"""
    findings: List[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def by_severity(self, min_level: str = "P2") -> List[Finding]:
        """按严重级过滤，返回 >= min_level 的发现。"""
        order = {"P0": 0, "P1": 1, "P2": 2}
        min_rank = order.get(min_level.upper(), 2)
        return [f for f in self.findings if order.get(f.severity, 2) <= min_rank]

    def count(self, severity: Optional[str] = None) -> int:
        if severity is None:
            return len(self.findings)
        return sum(1 for f in self.findings if f.severity == severity)


# ---------------------------------------------------------------------------
# 编码检测与解码
# ---------------------------------------------------------------------------

def _detect_and_decode(data: bytes) -> str:
    """尝试多种编码解码，返回文本。失败抛 E003。"""
    # 优先 UTF-8（带或不带 BOM）
    if data.startswith(b'\xef\xbb\xbf'):
        try:
            return data.decode('utf-8-sig')
        except UnicodeDecodeError:
            pass

    for enc in ('utf-8', 'gbk', 'utf-16'):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    raise ReviewError("E003", "无法识别输入文件编码（支持 UTF-8 / GBK / UTF-16）")


# ---------------------------------------------------------------------------
# diff 解析
# ---------------------------------------------------------------------------

_DIFF_FILE_RE = re.compile(r'^\+\+\+\s+(.*?)(?:\t|$)', re.MULTILINE)
_DIFF_HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', re.MULTILINE)


def parse_diff(text: str) -> List[Dict[str, Any]]:
    """
    将 diff 文本解析为结构化块列表。

    返回格式:
    [
        {
            "file": "path/to/file.py",
            "hunks": [
                {"start_line": 12, "lines": ["+code...", " context...", ...]},
                ...
            ]
        },
        ...
    ]

    若无法识别任何文件头，抛 E004。
    """
    if not text.strip():
        raise ReviewError("E004", "输入内容为空，不是有效 diff")

    # 按 `+++` 切分文件
    sections = _split_by_file_header(text)
    if not sections:
        raise ReviewError("E004", "未找到 diff 文件头（+++）")

    result: List[Dict[str, Any]] = []
    for file_path, body in sections:
        file_path = file_path.strip()
        # 跳过 /dev/null 等特殊路径
        if not file_path or file_path == "/dev/null":
            continue

        hunks = _extract_hunks(body)
        if hunks:
            result.append({"file": file_path, "hunks": hunks})

    if not result:
        raise ReviewError("E004", "diff 中未包含可分析的文件变更")
    return result


def _split_by_file_header(text: str) -> List[Tuple[str, str]]:
    """按 `+++` 行切分，返回 (文件路径, 该文件后续内容)。"""
    lines = text.splitlines()
    sections: List[Tuple[str, str]] = []
    current_file: Optional[str] = None
    current_body: List[str] = []

    for line in lines:
        m = _DIFF_FILE_RE.match(line)
        if m:
            # 保存前一个文件
            if current_file is not None:
                sections.append((current_file, "\n".join(current_body)))
            current_file = m.group(1).strip()
            current_body = []
        else:
            if current_file is not None:
                current_body.append(line)

    if current_file is not None:
        sections.append((current_file, "\n".join(current_body)))
    return sections


def _extract_hunks(body: str) -> List[Dict[str, Any]]:
    """从文件主体中提取 hunk 块。"""
    hunks: List[Dict[str, Any]] = []
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        m = _DIFF_HUNK_RE.match(lines[i])
        if m:
            start_line = int(m.group(1))
            hunk_lines: List[str] = []
            i += 1
            # 收集直到下一个 hunk 或文件结束
            while i < len(lines) and not _DIFF_HUNK_RE.match(lines[i]):
                hunk_lines.append(lines[i])
                i += 1
            hunks.append({"start_line": start_line, "lines": hunk_lines})
        else:
            i += 1
    return hunks


def _iter_added_lines(hunk: Dict[str, Any]) -> Iterable[Tuple[int, str]]:
    """迭代 hunk 中新增行（以 + 开头），返回 (绝对行号, 行内容)。"""
    base = hunk["start_line"]
    offset = 0
    for raw in hunk["lines"]:
        if raw.startswith("+"):
            yield base + offset, raw[1:]  # 去掉 '+'
            offset += 1
        elif raw.startswith("-"):
            # 删除行不计入行号偏移
            pass
        else:
            # 上下文行，行号也递增
            offset += 1


# ---------------------------------------------------------------------------
# 规则引擎
# ---------------------------------------------------------------------------

# 规则定义: (rule_id, severity, 名称, 正则)
_RULES = [
    (
        "SEC-001", "P0", "硬编码密码",
        re.compile(
            r"(password|passwd|pwd|secret|token|api_key|apikey)\s*[:=]\s*['\"][^'\"]{4,}['\"]",
            re.IGNORECASE
        )
    ),
    (
        "SEC-002", "P1", "URL 中明文凭据",
        re.compile(r"(https?://)[^/\s:@]+:[^/\s:@]+@", re.IGNORECASE)
    ),
    (
        "LOG-001", "P1", "不安全日志（打印敏感信息）",
        re.compile(
            r"(print|console\.log|logger\.(info|debug|warn|error)|log\.info)\s*\([^)]*(password|secret|token|credit_card|ssn)",
            re.IGNORECASE
        )
    ),
    (
        "PERF-001", "P1", "性能反模式（循环内拼接字符串）",
        re.compile(r"for\s+.*:\s*$.*(\+=|concat|append).*str", re.IGNORECASE | re.DOTALL)
    ),
    (
        "PERF-002", "P2", "性能反模式（同步 IO 在循环内）",
        re.compile(r"for\s+.*:\s*$.*(read\(|write\(|open\(|readline\()", re.IGNORECASE | re.DOTALL)
    ),
    (
        "PLAT-001", "P1", "平台依赖（硬编码路径分隔符）",
        re.compile(r"['\"][A-Za-z]:\\[^'\"]*['\"]|['\"]/usr/|['\"]/etc/|['\"]C:\\", re.IGNORECASE)
    ),
    (
        "PLAT-002", "P2", "平台依赖（Windows 换行符）",
        re.compile(r"\\r\\n")
    ),
]


def _mask_secret(text: str) -> str:
    """对疑似密码打码：将引号内的长串内容替换为 ***。"""
    return re.sub(r"(['\"])([^'\"]{4,})(['\"])", r"\1***\3", text)


def run_rules(parsed_diff: List[Dict[str, Any]], mask: bool = True) -> ReviewReport:
    """对解析后的 diff 执行规则扫描。"""
    report = ReviewReport()
    for file_entry in parsed_diff:
        fpath = file_entry["file"]
        for hunk in file_entry["hunks"]:
            for line_no, content in _iter_added_lines(hunk):
                if not content.strip():
                    continue
                for rule_id, severity, name, pattern in _RULES:
                    try:
                        m = pattern.search(content)
                    except re.error as exc:
                        raise ReviewError("E008", f"规则 {rule_id} 正则错误: {exc}") from exc
                    if m:
                        snippet = content.strip()
                        if mask:
                            snippet = _mask_secret(snippet)
                        report.add(Finding(
                            rule_id=rule_id,
                            severity=severity,
                            file=fpath,
                            line=line_no,
                            message=f"{name}（规则 {rule_id}）",
                            snippet=snippet[:200],  # 截断防止过长
                        ))
    return report


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------

def render_markdown(report: ReviewReport, min_level: str = "P2") -> str:
    """渲染 Markdown 报告。"""
    findings = report.by_severity(min_level)
    lines: List[str] = []
    lines.append("# 代码变更审查报告\n")
    lines.append(f"**扫描时间**: 自动生成  |  **发现总数**: {len(findings)}\n")
    lines.append("## 汇总\n")
    lines.append("| 级别 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| P0（严重） | {report.count('P0')} |")
    lines.append(f"| P1（警告） | {report.count('P1')} |")
    lines.append(f"| P2（建议） | {report.count('P2')} |")
    lines.append("\n## 详细发现\n")

    if not findings:
        lines.append("> ✅ 未发现符合规则的问题。\n")
    else:
        for i, f in enumerate(findings, 1):
            lines.append(f"### {i}. [{f.severity}] {f.message}")
            lines.append(f"- **文件**: `{f.file}`")
            lines.append(f"- **行号**: {f.line}")
            lines.append(f"- **规则**: {f.rule_id}")
            if f.snippet:
                lines.append(f"- **代码**: `{f.snippet}`")
            lines.append("")
    return "\n".join(lines)


def render_json(report: ReviewReport, min_level: str = "P2") -> str:
    """渲染 JSON 报告。"""
    findings = report.by_severity(min_level)
    payload = {
        "summary": {
            "total": len(findings),
            "P0": report.count("P0"),
            "P1": report.count("P1"),
            "P2": report.count("P2"),
        },
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "file": f.file,
                "line": f.line,
                "message": f.message,
                "snippet": f.snippet,
            }
            for f in findings
        ],
    }
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise ReviewError("E009", f"JSON 序列化失败: {exc}") from exc


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def process_diff(text: str, fmt: str = "markdown", min_level: str = "P2",
                 mask: bool = True) -> str:
    """完整处理管线：解析 -> 扫描 -> 渲染。"""
    parsed = parse_diff(text)
    report = run_rules(parsed, mask=mask)
    if fmt == "json":
        return render_json(report, min_level)
    return render_markdown(report, min_level)


def run_selftest() -> None:
    """内置硬编码样例数据离线自检。不依赖外部文件、网络、工作目录。"""
    sample_diff = """diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -10,7 +10,8 @@ def login():
     username = "admin"
-    password = "old_pass"
+    password = "S3cr3t!Pass"
+    print("password:", password)
     # 业务逻辑
@@ -30,6 +31,7 @@ def process():
     result = ""
     for i in range(10):
         result = result + str(i)  # 循环拼接
+    path = "C:\\\\temp\\\\file.txt"
     return result
"""

    # 1) 解析
    parsed = parse_diff(sample_diff)
    assert len(parsed) >= 1, "E001: 应至少解析出一个文件"
    assert any("example.py" in p["file"] for p in parsed), "E002: 文件名解析错误"

    # 2) 规则扫描（宽松断言：数量应 > 0，且包含 P0）
    report = run_rules(parsed, mask=True)
    assert report.count() > 0, "E003: 样例应至少命中一条规则"
    assert report.count("P0") >= 1, "E004: 样例应命中至少一条 P0（硬编码密码）"

    # 3) 输出管线（不抛异常即通过）
    md = render_markdown(report)
    assert "审查报告" in md, "E005: Markdown 应包含标题"
    assert "SEC-001" in md, "E006: Markdown 应包含规则编号"

    js = render_json(report)
    data = json.loads(js)
    assert data["summary"]["total"] > 0, "E007: JSON 汇总应有发现"
    assert len(data["findings"]) > 0, "E008: JSON findings 非空"

    # 4) 过滤功能
    filtered = report.by_severity("P1")
    assert len(filtered) >= 1, "E009: P1 过滤后应仍有结果"

    # 5) 脱敏验证
    for f in report.findings:
        if "password" in f.snippet.lower():
            assert "S3cr3t" not in f.snippet, "E010: 密码应被脱敏"

    print("[selftest] 全部通过 ✅")


def _read_input(path_str: str) -> str:
    """读取输入文件，支持 - 表示 stdin。"""
    if path_str == "-":
        data = sys.stdin.buffer.read()
        return _detect_and_decode(data)

    p = Path(path_str)
    if not p.exists():
        raise ReviewError("E001", f"输入文件不存在: {path_str}")
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise ReviewError("E002", f"无法读取文件 {path_str}: {exc}") from exc
    return _detect_and_decode(raw)


def _write_output(content: str, path_str: Optional[str], force: bool) -> None:
    """写输出文件；若未指定或非 force，仅打印到 stdout。"""
    if path_str is None or not force:
        print(content)
        return

    p = Path(path_str)
    parent = p.parent
    if parent and not parent.exists():
        raise ReviewError("E005", f"输出目录不存在: {parent}")
    try:
        p.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ReviewError("E006", f"写入输出文件失败: {exc}") from exc


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="code-review-report",
        description="解析 git diff，扫描风险并输出分级报告",
    )
    parser.add_argument("input", nargs="?", help="diff 文件路径（- 表示 stdin）")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="输出格式（默认 markdown）")
    parser.add_argument("--filter", default="P2",
                        help="最低严重级过滤（P0/P1/P2，默认 P2 表示全部）")
    parser.add_argument("--force", action="store_true",
                        help="允许写输出文件（默认仅打印）")
    parser.add_argument("--output", "-o", help="输出文件路径（需配合 --force）")
    parser.add_argument("--no-mask", action="store_true",
                        help="关闭密码脱敏（默认开启）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检并退出")

    args = parser.parse_args(argv)

    try:
        if args.selftest:
            run_selftest()
            return 0

        if not args.input:
            raise ReviewError("E007", "缺少输入文件参数（或使用 --selftest）")

        # 校验 filter 参数
        if args.filter.upper() not in ("P0", "P1", "P2"):
            raise ReviewError("E007", f"非法 --filter 值: {args.filter}（应为 P0/P1/P2）")

        text = _read_input(args.input)
        report_text = process_diff(
            text,
            fmt=args.format,
            min_level=args.filter.upper(),
            mask=not args.no_mask,
        )
        _write_output(report_text, args.output, args.force)
        return 0

    except ReviewError as exc:
        print(f"[错误 {exc.code}] {exc.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("[中断] 用户取消操作", file=sys.stderr)
        return 130
    except Exception as exc:  # 兜底
        print(f"[错误 E010] 未预期异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
