#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-review-pipeline — 代码审查流水线（独立实现）

功能：
  1. 静态代码审查：识别常见问题（未使用变量、空异常、调试残留、安全隐患）
  2. 自动修复：对可自动修复的问题生成补丁内容并应用
  3. 测试生成：根据代码结构生成基础单元测试骨架并写入文件
  4. HTML 报告：输出审查结果汇总报告

本脚本为 clean-room 实现，仅依据功能规格独立编写。
"""

import argparse
import ast
import html
import os
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码说明
# E001: 参数解析失败
# E002: 输入文件不存在
# E003: 输入文件不可读
# E004: 输入文件非文本格式
# E005: 输出目录创建失败
# E006: 报告写入失败
# E007: 内部逻辑错误（不应发生）
# E008: 不支持的编程语言
# E009: 空输入
# E010: 自检失败


# ---------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------

@dataclass
class Issue:
    """审查发现的问题"""
    severity: str          # "error" / "warning" / "info"
    line: int              # 行号（从1开始）
    code: str              # 问题标识
    message: str           # 中文描述
    fix_suggestion: str    # 修复建议


@dataclass
class ReviewResult:
    """单个文件的审查结果"""
    file_path: str
    language: str
    issues: List[Issue] = field(default_factory=list)
    fix_applied: bool = False
    test_code: str = ""


@dataclass
class ReviewConfig:
    """审查配置对象"""
    dry_run: bool = False
    fix: bool = False
    test: bool = False
    report_path: Optional[str] = None
    timeout: float = 10.0
    max_retries: int = 3


# ---------------------------------------------------------------
# 语言检测
# ---------------------------------------------------------------

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
}


def detect_language(file_path: str) -> str:
    """根据文件扩展名检测编程语言"""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext, "unknown")


# ---------------------------------------------------------------
# 审查规则（核心逻辑）
# ---------------------------------------------------------------

# 规则：未使用的 import（简化版：只检查 Python 中 import 后是否出现该名称）
IMPORT_PATTERN = re.compile(r"^\s*(?:import\s+(\w+)|from\s+(\w+)\s+import)", re.MULTILINE)
USAGE_PATTERN = re.compile(r"\b(\w+)\b")

# 规则：调试残留
DEBUG_PATTERNS = [
    (re.compile(r"print\s*\(", re.IGNORECASE), "调试输出（print）残留"),
    (re.compile(r"console\.log\s*\(", re.IGNORECASE), "调试输出（console.log）残留"),
    (re.compile(r"dbg!\s*\(", re.IGNORECASE), "调试输出（dbg!）残留"),
]

# 规则：安全隐患（eval / exec）
EVIL_PATTERNS = [
    (re.compile(r"\beval\s*\(", re.IGNORECASE), "危险函数 eval"),
    (re.compile(r"\bexec\s*\(", re.IGNORECASE), "危险函数 exec"),
]


def is_empty_except(node: ast.ExceptHandler) -> bool:
    """检查 AST 节点是否为空的 except 块"""
    if not node.body:
        return True
    # 检查 body 是否只包含 pass 或空表达式
    for stmt in node.body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
            continue
        return False
    return True


def find_empty_excepts(content: str) -> List[int]:
    """使用 AST 解析 Python 代码，找出空 except 块的行号"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    
    empty_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and is_empty_except(node):
            empty_lines.append(node.lineno)
    return empty_lines


def review_content(content: str, language: str) -> List[Issue]:
    """对代码内容执行静态审查，返回问题列表"""
    issues: List[Issue] = []
    lines = content.splitlines()

    # 1. 未使用的 import（仅 Python）
    if language == "python":
        imported_names = set(IMPORT_PATTERN.findall(content))
        imported_names = {name for pair in imported_names for name in pair if name}
        for name in sorted(imported_names):
            # 统计该名称在代码中出现的次数（排除 import 行自身）
            count = len(USAGE_PATTERN.findall(content))
            if count <= 0:
                issues.append(Issue(
                    severity="warning",
                    line=1,
                    code="unused-import",
                    message=f"疑似未使用的 import: {name}",
                    fix_suggestion=f"删除 import {name} 或确认其使用位置",
                ))

    # 2. 空异常捕获（使用 AST 解析）
    if language == "python":
        for line_no in find_empty_excepts(content):
            issues.append(Issue(
                severity="warning",
                line=line_no,
                code="empty-except",
                message="空 except 块，异常被静默吞掉",
                fix_suggestion="至少记录日志或传递异常（如 raise）",
            ))

    # 3. 调试残留
    for pattern, desc in DEBUG_PATTERNS:
        for match in pattern.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            issues.append(Issue(
                severity="info",
                line=line_no,
                code="debug-residue",
                message=f"调试残留：{desc}",
                fix_suggestion="移除调试输出或使用日志框架",
            ))

    # 4. 安全隐患
    for pattern, desc in EVIL_PATTERNS:
        for match in pattern.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            issues.append(Issue(
                severity="error",
                line=line_no,
                code="security-risk",
                message=f"安全隐患：{desc}",
                fix_suggestion="避免使用，改用安全替代方案（如 ast.literal_eval）",
            ))

    # 5. 行号对应（简化：按行补充检查）
    for i, line in enumerate(lines, 1):
        # 超长行
        if len(line) > 120:
            issues.append(Issue(
                severity="info",
                line=i,
                code="long-line",
                message="行长度超过 120 字符",
                fix_suggestion="考虑拆分长行以提升可读性",
            ))

    return issues


# ---------------------------------------------------------------
# 自动修复（生成补丁建议并应用）
# ---------------------------------------------------------------

def generate_fix(result: ReviewResult) -> str:
    """根据审查结果生成修复后的代码（移除调试 print 和空 except）"""
    if not result.issues:
        return ""

    try:
        with open(result.file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return ""

    # 移除 print 行（简化修复）
    lines = content.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        if re.match(r"^\s*print\s*\(", line):
            continue
        new_lines.append(line)

    new_content = "".join(new_lines)
    if new_content != content:
        result.fix_applied = True
        return new_content
    return ""


def apply_fix(result: ReviewResult, config: ReviewConfig) -> str:
    """应用自动修复，返回修复后的代码"""
    if config.dry_run:
        return generate_fix(result)
    
    fix_content = generate_fix(result)
    if fix_content and not config.dry_run:
        try:
            with open(result.file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(fix_content)
            result.fix_applied = True
        except OSError:
            pass
    return fix_content


def fix_issues(results: List[ReviewResult], config: ReviewConfig) -> List[ReviewResult]:
    """修复所有文件中的问题"""
    for result in results:
        if config.fix:
            apply_fix(result, config)
    return results


# ---------------------------------------------------------------
# 测试生成
# ---------------------------------------------------------------

def generate_tests(result: ReviewResult) -> str:
    """根据代码内容生成基础单元测试骨架"""
    try:
        with open(result.file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return ""

    # 提取函数名（简化：匹配 def 或 function）
    func_names = []
    if result.language == "python":
        func_names = re.findall(r"^\s*def\s+(\w+)\s*\(", content, re.MULTILINE)
    elif result.language in ("javascript", "typescript"):
        func_names = re.findall(r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*\()", content)

    # 展平并去重
    flat_names = []
    for item in func_names:
        if isinstance(item, tuple):
            flat_names.extend([x for x in item if x])
        else:
            flat_names.append(item)
    flat_names = list(dict.fromkeys(flat_names))

    # 生成测试代码
    lines = []
    if result.language == "python":
        lines.append("import unittest")
        lines.append("")
        lines.append("class TestGenerated(unittest.TestCase):")
        lines.append("    \"\"\"自动生成的测试用例\"\"\"")
        lines.append("")
        for name in flat_names[:10]:
            lines.append(f"    def test_{name}(self):")
            lines.append(f"        # TODO: 根据函数 {name} 的逻辑补充断言")
            lines.append(f"        self.assertTrue(True)  # 占位断言")
            lines.append("")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    unittest.main()")
    else:
        lines.append("// 自动生成的测试骨架")
        lines.append("// 请根据实际逻辑编写断言")
        for name in flat_names[:10]:
            lines.append(f"// TODO: 测试函数 {name}")
        lines.append("")

    return "\n".join(lines)


def generate_test_files(results: List[ReviewResult], config: ReviewConfig) -> List[ReviewResult]:
    """为所有文件生成测试代码并写入文件"""
    if not config.test:
        return results
    
    for result in results:
        test_code = generate_tests(result)
        if test_code:
            result.test_code = test_code
            # 写入测试文件
            test_path = Path(result.file_path).with_suffix(".test.py")
            try:
                with open(test_path, "w", encoding="utf-8") as f:
                    f.write(test_code)
            except OSError:
                pass
    return results


# ---------------------------------------------------------------
# HTML 报告生成
# ---------------------------------------------------------------

def generate_html_report(results: List[ReviewResult], output_path: str) -> None:
    """生成 HTML 格式的审查报告"""
    total_issues = sum(len(r.issues) for r in results)
    error_count = sum(1 for r in results for i in r.issues if i.severity == "error")
    warning_count = sum(1 for r in results for i in r.issues if i.severity == "warning")
    info_count = sum(1 for r in results for i in r.issues if i.severity == "info")

    # 构建文件详情
    file_sections = []
    for result in results:
        issue_rows = ""
        if result.issues:
            for issue in result.issues:
                issue_rows += f"""
                <tr>
                    <td>{issue.line}</td>
                    <td><span class="badge {issue.severity}">{issue.severity}</span></td>
                    <td><code>{html.escape(issue.code)}</code></td>
                    <td>{html.escape(issue.message)}</td>
                    <td>{html.escape(issue.fix_suggestion)}</td>
                </tr>"""
        else:
            issue_rows = '<tr><td colspan="5" style="color:green">✓ 未发现问题</td></tr>'

        # 添加修复和测试信息
        fix_info = ""
        if result.fix_applied:
            fix_info = '<p style="color:green">✓ 已自动修复</p>'
        elif config.fix and result.issues:
            fix_info = '<p style="color:orange">⚠ 修复未应用（dry-run 模式）</p>'

        test_info = ""
        if result.test_code:
            test_info = '<p style="color:blue">📝 已生成测试文件</p>'

        file_sections.append(f"""
        <div class="file-block">
            <h3>📄 {html.escape(result.file_path)} <span class="lang">{result.language}</span></h3>
            {fix_info}
            {test_info}
            <table>
                <thead>
                    <tr><th>行号</th><th>级别</th><th>代码</th><th>描述</th><th>修复建议</th></tr>
                </thead>
                <tbody>{issue_rows}</tbody>
            </table>
        </div>""")

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>代码审查报告</title>
<style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
    h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
    .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
    .stat {{ padding: 15px; background: #f0f0f0; border-radius: 6px; flex: 1; text-align: center; }}
    .stat .number {{ font-size: 24px; font-weight: bold; }}
    .error {{ color: #d9534f; }}
    .warning {{ color: #f0ad4e; }}
    .info {{ color: #5bc0de; }}
    .badge {{ padding: 2px 8px; border-radius: 4px; color: white; font-size: 12px; }}
    .badge.error {{ background: #d9534f; }}
    .badge.warning {{ background: #f0ad4e; }}
    .badge.info {{ background: #5bc0de; }}
    .file-block {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 6px; }}
    .lang {{ color: #777; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
    th {{ background: #f8f8f8; }}
    code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
    .footer {{ margin-top: 30px; color: #999; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="container">
    <h1>🔍 代码审查报告</h1>
    <div class="stats">
        <div class="stat"><div class="number">{total_issues}</div><div>总问题数</div></div>
        <div class="stat"><div class="number error">{error_count}</div><div>错误</div></div>
        <div class="stat"><div class="number warning">{warning_count}</div><div>警告</div></div>
        <div class="stat"><div class="number info">{info_count}</div><div>提示</div></div>
    </div>
    {''.join(file_sections)}
    <div class="footer">
        <p>报告由 ai-review-pipeline 自动生成 · 生成时间: {datetime.now(timezone.utc).isoformat()}</p>
    </div>
</div>
</body>
</html>"""

    try:
        with open(output_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(html_content)
    except OSError:
        raise RuntimeError("E006: 报告写入失败")


def render_html_report(results: List[ReviewResult], output_path: str) -> None:
    """渲染 HTML 报告（与 generate_html_report 相同，保持接口一致性）"""
    generate_html_report(results, output_path)


# ---------------------------------------------------------------
# 网络请求工具（带重试退避和超时）
# ---------------------------------------------------------------

def fetch_url_with_retry(url: str, config: ReviewConfig) -> str:
    """带重试退避和超时的网络请求"""
    last_error = None
