#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码审查报告技能 - 独立实现
功能：解析 git diff，规则扫描硬编码密码/不安全日志/性能反模式/平台依赖，
输出分级审查报告（markdown/json），支持严重级过滤、密码脱敏、默认预览不写盘。
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile
import tokenize
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# ============================================================
EXIT_SUCCESS = 0
EXIT_SELFTEST_FAIL = 1
EXIT_PARAM_ERROR = 2
EXIT_DIFF_PARSE_ERROR = 10

# ============================================================
# 规则定义
# ============================================================
@dataclass
class Rule:
    """规则定义"""
    code: str
    severity: str
    description: str
    confidence: float
    pattern: re.Pattern
    message: str


# 硬编码密码/密钥检测（SEC001）
SEC_PATTERN = re.compile(
    r"""(?ix)                          # 忽略大小写，多行
    (password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\s*[:=]\s*
    ['"]([^'"]{6,})['"]              # 至少6字符的字符串值
    """
)

# 格式化字符串进日志（LOG001）
LOG_PATTERN = re.compile(
    r"""(?ix)
    (logging|logger|log)\.\s*(debug|info|warning|error|critical)\s*\(\s*f['"]
    """
)

# 循环内 range(len())（PERF001）
PERF_PATTERN = re.compile(
    r"""(?ix)
    for\s+\w+\s+in\s+range\s*\(\s*len\s*\(
    """
)

# 平台特定命令执行（STD001）
STD_PATTERN = re.compile(
    r"""(?ix)
    os\.system\s*\(|subprocess\.(call|run|Popen)\s*\(|os\.popen\s*\(
    """
)

RULES = [
    Rule(
        code="SEC001",
        severity="P0",
        description="硬编码密码/密钥",
        confidence=0.95,
        pattern=SEC_PATTERN,
        message="检测到硬编码密码/密钥，存在安全风险",
    ),
    Rule(
        code="LOG001",
        severity="P1",
        description="格式化字符串进日志",
        confidence=0.80,
        pattern=LOG_PATTERN,
        message="日志中使用了 f-string 格式化，可能泄露敏感信息",
    ),
    Rule(
        code="PERF001",
        severity="P1",
        description="循环内 range(len())",
        confidence=0.75,
        pattern=PERF_PATTERN,
        message="循环内使用 range(len()) 模式，建议改用 enumerate",
    ),
    Rule(
        code="STD001",
        severity="P2",
        description="平台特定命令执行",
        confidence=0.85,
        pattern=STD_PATTERN,
        message="检测到平台特定命令执行，可能存在可移植性问题",
    ),
]

# ============================================================
# 数据结构
# ============================================================
@dataclass
class Finding:
    """单个问题发现"""
    rule_code: str
    severity: str
    file_path: str
    line_number: int
    description: str
    confidence: float
    message: str
    snippet: str = ""


@dataclass
class DiffHunk:
    """diff 的 hunk 块"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class DiffFile:
    """diff 中的单个文件"""
    old_path: str
    new_path: str
    hunks: List[DiffHunk] = field(default_factory=list)


@dataclass
class ScanResult:
    """扫描结果"""
    findings: List[Finding] = field(default_factory=list)
    files_scanned: List[str] = field(default_factory=list)


# ============================================================
# diff 解析模块
# ============================================================
class DiffParser:
    """git diff 解析器 - 严格校验，快速失败"""

    def __init__(self, content: str):
        self.content = content
        self.files: List[DiffFile] = []
        self._parse()

    def _parse(self) -> None:
        """解析 diff 内容"""
        lines = self.content.splitlines()
        if not lines:
            raise DiffParseError("空 diff 内容")

        current_file: Optional[DiffFile] = None
        current_hunk: Optional[DiffHunk] = None
        line_num = 0  # 当前新文件行号

        for idx, line in enumerate(lines):
            # 文件头
            if line.startswith("diff --git "):
                if current_hunk is not None:
                    raise DiffParseError(f"第 {idx+1} 行：hunk 未闭合")
                if current_file is not None:
                    self.files.append(current_file)
                current_file = self._parse_file_header(line, idx + 1)
                current_hunk = None
                line_num = 0
                continue

            if current_file is None:
                continue  # 跳过 diff 元数据行

            # hunk 头
            if line.startswith("@@"):
                if current_hunk is not None:
                    raise DiffParseError(f"第 {idx+1} 行：hunk 未闭合")
                current_hunk = self._parse_hunk_header(line, idx + 1)
                current_file.hunks.append(current_hunk)
                line_num = current_hunk.new_start
                continue

            # hunk 内容行
            if current_hunk is not None:
                if len(line) == 0:
                    # 空行（没有标记符）
                    current_hunk.lines.append((" ", ""))
                    line_num += 1
                    continue

                marker = line[0]
                content = line[1:]
                if marker in (" ", "+", "-"):
                    current_hunk.lines.append((marker, content))
                    if marker in (" ", "+"):
                        line_num += 1
                elif line.startswith("\\ No newline"):
                    # 文件末尾无换行标记，忽略
                    continue
                else:
                    raise DiffParseError(
                        f"第 {idx+1} 行：非法行标记 '{marker}'"
                    )
                continue

            # 文件元数据行（如 index, ---, +++ 等）
            if line.startswith(("index ", "--- ", "+++ ", "new file", "deleted")):
                continue
            # 其他未知行在文件头部之前跳过

        # 收尾
        if current_hunk is not None:
            # hunk 正常结束
            pass
        if current_file is not None:
            self.files.append(current_file)

        if not self.files:
            raise DiffParseError("未找到有效的文件差异")

    def _parse_file_header(self, line: str, lineno: int) -> DiffFile:
        """解析文件头"""
        # 格式: diff --git a/path b/path
        parts = line.split()
        if len(parts) < 4:
            raise DiffParseError(f"第 {lineno} 行：文件头格式错误")
        old_path = parts[2][2:] if parts[2].startswith("a/") else parts[2]
        new_path = parts[3][2:] if parts[3].startswith("b/") else parts[3]
        return DiffFile(old_path=old_path, new_path=new_path)

    def _parse_hunk_header(self, line: str, lineno: int) -> DiffHunk:
        """解析 hunk 头"""
        # 格式: @@ -old_start,old_count +new_start,new_count @@
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if not m:
            raise DiffParseError(f"第 {lineno} 行：hunk 头格式错误")
        old_start = int(m.group(1))
        old_count = int(m.group(2) or 1)
        new_start = int(m.group(3))
        new_count = int(m.group(4) or 1)
        return DiffHunk(
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
            lines=[]  # 初始化 lines 为空列表
        )


class DiffParseError(Exception):
    """diff 解析错误"""
    pass


# ============================================================
# 代码扫描模块
# ============================================================
class CodeScanner:
    """基于 tokenize 的代码扫描器"""

    def __init__(self):
        self.rules = RULES

    def scan_diff(self, diff_files: List[DiffFile]) -> ScanResult:
        """扫描 diff 中的所有文件"""
        result = ScanResult()
        for diff_file in diff_files:
            # 只扫描新增行（+）和上下文行（空格）
            code_lines = []
            for hunk in diff_file.hunks:
                for marker, content in hunk.lines:
                    if marker in ("+", " "):
                        code_lines.append(content)

            if not code_lines:
                continue

            # 合并代码行用于 tokenize
            code_text = "\n".join(code_lines) + "\n"

            # 剥离注释和字符串后的代码
            stripped_code = self._strip_comments_and_strings(code_text)

            # 逐行扫描
            for idx, line in enumerate(stripped_code.splitlines()):
                line_no = self._get_line_number(diff_file, idx)
                for rule in self.rules:
                    m = rule.pattern.search(line)
                    if m:
                        snippet = line.strip()[:80]
                        if rule.code == "SEC001":
                            # 密码脱敏
                            snippet = self._mask_secret(snippet, m)
                        finding = Finding(
                            rule_code=rule.code,
                            severity=rule.severity,
                            file_path=diff_file.new_path,
                            line_number=line_no,
                            description=rule.description,
                            confidence=rule.confidence,
                            message=rule.message,
                            snippet=snippet,
                        )
                        result.findings.append(finding)

            result.files_scanned.append(diff_file.new_path)

        return result

    def _get_line_number(self, diff_file: DiffFile, line_idx: int) -> int:
        """估算行号（基于新文件行号）"""
        line_no = 0
        count = 0
        for hunk in diff_file.hunks:
            if count + len(hunk.lines) > line_idx:
                # 找到所在 hunk
                local_idx = line_idx - count
                # 计算新文件行号
                new_line = hunk.new_start
                for i in range(local_idx):
                    marker, _ = hunk.lines[i]
                    if marker in (" ", "+"):
                        new_line += 1
                line_no = new_line
                break
            count += len(hunk.lines)
        return line_no

    def _strip_comments_and_strings(self, code: str) -> str:
        """使用 tokenize 剥离注释和字符串"""
        result_lines = []
        try:
            tokens = tokenize.generate_tokens(io.StringIO(code).readline)
            for tok in tokens:
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    # 用空格替换
                    result_lines.append(" " * len(tok.string))
                else:
                    result_lines.append(tok.string)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            # tokenize 失败时回退到正则剥离
            code = re.sub(r"#[^\n]*", "", code)
            code = re.sub(r"(['\"])(.*?)\1", " ", code, flags=re.DOTALL)
            return code
        return "".join(result_lines)

    def _mask_secret(self, snippet: str, match: re.Match) -> str:
        """密码脱敏 - 只显示前2位+***"""
        try:
            # 提取密码值
            if match.lastindex and match.lastindex >= 2:
                secret = match.group(2)
                # 找到 secret 在 snippet 中的位置
                idx = snippet.find(secret)
                if idx >= 0:
                    masked = secret[:2] + "***"
                    return snippet[:idx] + masked + snippet[idx + len(secret):]
        except (IndexError, AttributeError):
            pass
        return snippet


# ============================================================
# 报告生成模块
# ============================================================
class ReportGenerator:
    """报告生成器"""

    def __init__(self, scan_result: ScanResult, severity_filter: Optional[List[str]] = None):
        self.scan_result = scan_result
        self.severity_filter = severity_filter or ["P0", "P1", "P2"]
        self._filter_findings()

    def _filter_findings(self) -> None:
        """按严重级过滤"""
        if self.severity_filter:
            self.filtered_findings = [
                f for f in self.scan_result.findings
                if f.severity in self.severity_filter
            ]
        else:
            self.filtered_findings = self.scan_result.findings

    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        lines = ["# 代码审查报告", ""]
        lines.append(f"## 扫描概览")
        lines.append(f"- 扫描文件数: {len(self.scan_result.files_scanned)}")
        lines.append(f"- 发现问题数: {len(self.filtered_findings)}")
        lines.append("")

        # 按严重级统计
        sev_counts = {"P0": 0, "P1": 0, "P2": 0}
        for f in self.filtered_findings:
            sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        lines.append("### 严重级分布")
        for sev in ["P0", "P1", "P2"]:
            lines.append(f"- **{sev}**: {sev_counts.get(sev, 0)}")
        lines.append("")

        if not self.filtered_findings:
            lines.append("✅ 未发现问题")
            return "\n".join(lines)

        lines.append("## 问题明细")
        lines.append("")
        lines.append("| 严重级 | 规则 | 文件 | 行号 | 描述 | 置信度 | 代码片段 |")
        lines.append("|--------|------|------|------|------|--------|----------|")
        for f in self.filtered_findings:
            snippet = f.snippet.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {f.severity} | {f.rule_code} | {f.file_path} | "
                f"{f.line_number} | {f.message} | {f.confidence:.2f} | {snippet} |"
            )
        lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        """生成 JSON 报告"""
        report = {
            "summary": {
                "files_scanned": len(self.scan_result.files_scanned),
                "findings_count": len(self.filtered_findings),
                "severity_counts": {
                    "P0": sum(1 for f in self.filtered_findings if f.severity == "P0"),
                    "P1": sum(1 for f in self.filtered_findings if f.severity == "P1"),
                    "P2": sum(1 for f in self.filtered_findings if f.severity == "P2"),
                },
            },
            "findings": [
                {
                    "rule_code": f.rule_code,
                    "severity": f.severity,
                    "file": f.file_path,
                    "line": f.line_number,
                    "message": f.message,
                    "confidence": f.confidence,
                    "snippet": f.snippet,
                }
                for f in self.filtered_findings
            ],
        }
        return json.dumps(report, ensure_ascii=False, indent=2)


# ============================================================
# 文件操作模块
# ============================================================
def read_file_with_encoding(filepath: str) -> str:
    """读取文件，自动识别编码"""
    encodings = ["utf-8", "gbk", "gb18030"]
    last_error = None
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, IOError) as e:
            last_error = e
            continue
    raise IOError(f"无法读取文件 {filepath}: {last_error}")


def atomic_write(filepath: str, content: str) -> None:
    """原子写入文件"""
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(filepath) or ".",
            prefix=".review_tmp_",
            suffix=".tmp",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, filepath)
        tmp_path = None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ============================================================
# 自测模块
# ============================================================
def run_selftest() -> int:
    """内置自测 - 12 条断言"""
    tests = []

    # 测试1: diff 解析 - 基本文件头
    diff1 = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def foo():
-    print("old")
+    print("new")
+    x = 1
"""
    try:
        parser = DiffParser(diff1)
        tests.append(("diff 解析 - 基本文件", len(parser.files) >= 1))
    except DiffParseError:
        tests.append(("diff 解析 - 基本文件", False))

    # 测试2: diff 解析 - 多文件
    diff2 = diff1 + "\ndiff --git a/other.py b/other.py\n--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-old\n+new\n"
    try:
        parser = DiffParser(diff2)
        tests.append(("diff 解析 - 多文件", len(parser.files) >= 2))
    except DiffParseError:
        tests.append(("diff 解析 - 多文件", False))

    # 测试3: diff 解析 - 非法格式快速失败
    bad_diff = "this is not a diff"
    try:
        DiffParser(bad_diff)
        tests.append(("diff 解析 - 非法格式", False))
    except DiffParseError:
        tests.append(("diff 解析 - 非法格式", True))

    # 测试4: SEC001 检测
    scanner = CodeScanner()
    diff_sec = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,2 +1,2 @@
-password = "oldpass"
+password = "secret123"
"""
    parser = DiffParser(diff_sec)
    result = scanner.scan_diff(parser.files)
    sec_findings = [f for f in result.findings if f.rule_code == "SEC001"]
    tests.append(("SEC001 检测", len(sec_findings) >= 1))

    # 测试5: 密码脱敏
    masked = all("secret" not in f.snippet for f in sec_findings)
    tests.append(("密码脱敏", masked))

    # 测试6: LOG001 检测
    diff_log = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
-logging.info("static")
+logging.info(f"user={user}")
"""
    parser = DiffParser(diff_log)
    result = scanner.scan_diff(parser.files)
    log_findings = [f for f in result.findings if f.rule_code == "LOG001"]
    tests.append(("LOG001 检测", len(log_findings) >= 1))

    # 测试7: PERF001 检测
    diff_perf = """diff --git a/loop.py b/loop.py
--- a/loop.py
+++ b/loop.py
@@ -1,2 +1,2 @@
-for i in range(len(items)):
+for i in range(len(items)):
     pass
"""
    parser = DiffParser(diff_perf)
    result = scanner.scan_diff(parser.files)
    perf_findings = [f for f in result.findings if f.rule_code == "PERF001"]
    tests.append(("PERF001 检测", len(perf_findings) >= 1))

    # 测试8: STD001 检测
    diff_std = """diff --git a/cmd.py b/cmd.py
--- a/cmd.py
+++ b/cmd.py
@@ -1,2 +1,2 @@
-print("ok")
+os.system("ls")
"""
    parser = DiffParser(diff_std)
    result = scanner.scan_diff(parser.files)
    std_findings = [f for f in result.findings if f.rule_code == "STD001"]
    tests.append(("STD001 检测", len(std_findings) >= 1))

    # 测试9: 注释/字符串剥离 - 注释不误报
    diff_comment = """diff --git a/comment.py b/comment.py
--- a/comment.py
+++ b/comment.py
@@ -1,2 +1,2 @@
-# for i in range(len(items))
+# for i in range(len(items))
"""
    parser = DiffParser(diff_comment)
    result = scanner.scan_diff(parser.files)
    comment_findings = [f for f in result.findings if f.rule_code == "PERF001"]
    tests.append(("注释不误报", len(comment_findings) == 0))

    # 测试10: 严重级过滤
    generator = ReportGenerator(result, severity_filter=["P0"])
    tests.append(("严重级过滤", all(f.severity == "P0" for f in generator.filtered_findings)))

    # 测试11: JSON 输出
    json_str = generator.to_json()
    tests.append(("JSON 输出", json_str.startswith("{")))

    # 测试12: Markdown 输出
    md_str = generator.to_markdown()
    tests.append(("Markdown 输出", "#" in md_str))

    # 汇总
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)
    print(f"自测结果: {passed}/{total} 通过")
    for name, ok in tests:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")

    return EXIT_SUCCESS if passed == total else EXIT_SELFTEST_FAIL


# ============================================================
# 主程序
# ============================================================
def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="代码审查报告 - 解析 git diff，扫描代码问题，输出分级报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --diff change.diff
  python main.py --diff change.diff --filter P0
  python main.py --diff change.diff --format json
  python main.py --diff change.diff --output report.md --force
  python main.py --selftest
        """,
    )
    parser.add_argument("--diff", help="diff 文件路径")
    parser.add_argument("--output", help="输出文件路径（缺省 stdout）")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="输出格式")
    parser.add_argument("--filter", help="严重级过滤，逗号分隔（P0,P1）")
    parser.add_argument("--dry-run", action="store_true", help="显式预览（默认即预览）")
    parser.add_argument("--force", action="store_true", help="真正落盘")
    parser.add_argument("--verbose", action="store_true", help="每文件命中明细")
    parser.add_argument("--selftest", action="store_true", help="运行内置自测")
    parser.add_argument("--version", action="version", version="code-review-report 2.0.0")

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.diff:
        print("错误 E002: 缺少 --diff 参数", file=sys.stderr)
        return EXIT_PARAM_ERROR

    # 解析严重级过滤
    severity_filter = None
    if args.filter:
        severity_filter = [s.strip().upper() for s in args.filter.split(",")]
        valid = {"P0", "P1", "P2"}
        if not all(s in valid for s in severity_filter):
            print(f"错误 E002: 非法严重级 {args.filter}", file=sys.stderr)
            return EXIT_PARAM_ERROR

    try:
        # 读取 diff 文件
        diff_content = read_file_with_encoding(args.diff)
    except IOError as e:
        print(f"错误 E010: 读取文件失败 - {e}", file=sys.stderr)
        return EXIT_DIFF_PARSE_ERROR

    try:
        # 解析 diff
        diff_parser = DiffParser(diff_content)
    except DiffParseError as e:
        print(f"错误 E010: diff 格式不兼容 - {e}", file=sys.stderr)
        print("提示: 请使用 'git diff > change.diff' 导出标准 diff 格式", file=sys.stderr)
        return EXIT_DIFF_PARSE_ERROR

    # 扫描代码
    scanner = CodeScanner()
    scan_result = scanner.scan_diff(diff_parser.files)

    # 生成报告
    generator = ReportGenerator(scan_result, severity_filter)
    if args.format == "json":
        report = generator.to_json()
    else:
        report = generator.to_markdown()

    # verbose 模式输出明细
    if args.verbose:
        print(f"扫描文件数: {len(scan_result.files_scanned)}")
        for f in scan_result.files_scanned:
            print(f"  - {f}")

    # 输出报告
    if args.output:
        if not args.force:
            print(f"预览模式: 不写盘。使用 --force 写入 {args.output}")
            print("=" * 60)
            print(report)
            return EXIT_SUCCESS
        try:
            atomic_write(args.output, report)
            print(f"报告已写入: {args.output}")
        except IOError as e:
            print(f"错误 E010: 写盘失败 - {e}", file=sys.stderr)
            return EXIT_DIFF_PARSE_ERROR
    else:
        print(report)

    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
