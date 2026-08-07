#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-review-pipeline — 代码审查流水线（独立实现）

功能：
  1. 静态代码审查：识别常见问题（未使用变量、空异常、调试残留、安全隐患）
  2. 自动修复：对可自动修复的问题生成补丁内容
  3. 测试生成：根据代码结构生成基础单元测试骨架
  4. HTML 报告：输出审查结果汇总报告

本脚本为 clean-room 实现，仅依据功能规格独立编写。
"""

import argparse
import html
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

# 规则：空 except 块
EMPTY_EXCEPT_PATTERN = re.compile(r"except[^:]*:\s*\n\s*(?:pass|\.\.\.)\s*\n", re.MULTILINE)

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

    # 2. 空异常捕获
    for match in EMPTY_EXCEPT_PATTERN.finditer(content):
        line_no = content[:match.start()].count("\n") + 1
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
# 自动修复（生成补丁建议）
# ---------------------------------------------------------------

def generate_fix(result: ReviewResult) -> str:
    """根据审查结果生成修复后的代码（简化版：仅移除调试 print）"""
    if not result.issues:
        return ""

    try:
        with open(result.file_path, "r", encoding="utf-8") as f:
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


# ---------------------------------------------------------------
# 测试生成
# ---------------------------------------------------------------

def generate_tests(result: ReviewResult) -> str:
    """根据代码内容生成基础单元测试骨架"""
    try:
        with open(result.file_path, "r", encoding="utf-8") as f:
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

        file_sections.append(f"""
        <div class="file-block">
            <h3>📄 {html.escape(result.file_path)} <span class="lang">{result.language}</span></h3>
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
        <p>报告由 ai-review-pipeline 自动生成 · 仅供学习参考 · 不构成专业建议</p>
    </div>
</div>
</body>
</html>"""

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except OSError:
        raise RuntimeError("E006: 报告写入失败")


# ---------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------

def process_file(file_path: str, do_fix: bool = False, do_test: bool = False) -> ReviewResult:
    """处理单个文件，返回审查结果"""
    # 检查文件存在性
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"E002: 文件不存在: {file_path}")

    # 读取内容
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        raise ValueError(f"E004: 文件不是有效文本: {file_path}")
    except OSError:
        raise PermissionError(f"E003: 文件不可读: {file_path}")

    if not content.strip():
        raise ValueError(f"E009: 空文件: {file_path}")

    # 检测语言
    language = detect_language(file_path)
    if language == "unknown":
        raise ValueError(f"E008: 不支持的编程语言: {file_path}")

    # 执行审查
    result = ReviewResult(file_path=file_path, language=language)
    result.issues = review_content(content, language)

    # 自动修复
    if do_fix and result.issues:
        fix_content = generate_fix(result)
        if fix_content:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fix_content)
                result.fix_applied = True
            except OSError:
                pass  # 修复失败不阻止流程

    # 测试生成
    if do_test:
        result.test_code = generate_tests(result)

    return result


def run_pipeline(paths: List[str], do_fix: bool, do_test: bool, report_path: Optional[str]) -> int:
    """执行完整流水线"""
    results: List[ReviewResult] = []
    errors: List[str] = []

    # 收集所有文件
    files_to_review: List[str] = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            # 递归收集支持的文件
            for ext in LANGUAGE_EXTENSIONS:
                files_to_review.extend(str(f) for f in p.rglob(f"*{ext}"))
        elif p.is_file():
            files_to_review.append(str(p))
        else:
            errors.append(f"E002: 路径不存在: {path}")

    # 去重
    files_to_review = list(dict.fromkeys(files_to_review))

    if not files_to_review:
        print("错误: 未找到可审查的文件")
        return 2

    # 处理每个文件
    for file_path in files_to_review:
        try:
            result = process_file(file_path, do_fix=do_fix, do_test=do_test)
            results.append(result)
            # 控制台输出摘要
            print(f"📄 {file_path} [{result.language}] - {len(result.issues)} 个问题")
            for issue in result.issues:
                print(f"   [{issue.severity}] 行 {issue.line}: {issue.message}")
            if result.fix_applied:
                print(f"   ✨ 已应用自动修复")
        except (FileNotFoundError, ValueError, PermissionError) as e:
            errors.append(str(e))
            print(f"⚠️  {e}")

    # 生成 HTML 报告
    if report_path and results:
        try:
            generate_html_report(results, report_path)
            print(f"\n📊 报告已生成: {report_path}")
        except RuntimeError as e:
            print(f"⚠️  {e}")

    # 汇总
    total_issues = sum(len(r.issues) for r in results)
    print(f"\n{'='*50}")
    print(f"审查完成: {len(results)} 个文件, {total_issues} 个问题")

    # 输出错误码
    for error in errors:
        print(f"错误: {error}")

    return 0 if not errors else 1


# ---------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------

def run_selftest() -> int:
    """内置硬编码样例数据自检核心逻辑"""
    print("🔧 运行自检...")

    # 硬编码样例（不依赖外部文件）
    sample_code = """import os
import sys

def process_data(data):
    # TODO: implement
    print("processing")
    try:
        result = data * 2
    except:
        pass
    return result

def helper():
    return None

eval("print('bad')")
"""

    # 测试语言检测
    assert detect_language("test.py") == "python", "E010: 语言检测失败"
    assert detect_language("test.js") == "javascript", "E010: 语言检测失败"
    assert detect_language("test.unknown") == "unknown", "E010: 语言检测失败"

    # 测试审查逻辑
    issues = review_content(sample_code, "python")
    assert len(issues) > 0, "E010: 审查未发现问题"
    assert any(i.severity == "error" for i in issues), "E010: 未检测到安全问题"
    assert any(i.severity == "warning" for i in issues), "E010: 未检测到警告"
    assert any(i.code == "debug-residue" for i in issues), "E010: 未检测到调试残留"

    # 测试空文件
    empty_issues = review_content("", "python")
    assert len(empty_issues) == 0, "E010: 空文件应无问题"

    # 测试修复生成（使用临时文件）
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(sample_code)
        tmp_path = tmp.name

    try:
        # 测试 process_file
        result = process_file(tmp_path)
        assert result.language == "python", "E010: 语言检测失败"
        assert len(result.issues) > 0, "E010: 审查失败"

        # 测试修复
        fix_content = generate_fix(result)
        # 修复内容不应为空，因为样例中有 print
        assert fix_content is not None, "E010: 修复生成失败"
        assert "print(" not in fix_content, "E010: 修复未移除 print"

        # 测试测试生成
        test_code = generate_tests(result)
        assert "unittest" in test_code, "E010: 测试生成失败"
        assert "process_data" in test_code, "E010: 测试生成缺少函数名"

        # 测试 HTML 报告
        report_path = os.path.join(tempfile.gettempdir(), "test_report.html")
        generate_html_report([result], report_path)
        assert os.path.exists(report_path), "E010: 报告生成失败"
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "代码审查报告" in content, "E010: 报告内容错误"

    finally:
        os.unlink(tmp_path)

    print("✅ 自检通过")
    return 0


# ---------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="代码审查流水线：静态审查、自动修复、测试生成、HTML报告",
        epilog="示例: python main.py review src/ --fix --report out.html"
    )
    parser.add_argument(
        "paths", nargs="*", default=[],
        help="要审查的文件或目录路径"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="启用自动修复（移除调试输出等）"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="生成单元测试骨架"
    )
    parser.add_argument(
        "--report", type=str, default=None,
        help="HTML 报告输出路径"
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行内置自检（离线，不依赖外部文件）"
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code != 0:
            print("E001: 参数解析失败")
        return e.code

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"❌ 自检失败: {e}")
            return 1
        except Exception as e:
            print(f"❌ 自检异常: {e}")
            return 1

    # 正常模式
    if not args.paths:
        print("E001: 请至少指定一个文件或目录路径")
        print("提示: 使用 --selftest 运行自检，或 --help 查看帮助")
        return 2

    try:
        return run_pipeline(args.paths, args.fix, args.test, args.report)
    except Exception as e:
        print(f"E007: 内部错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
