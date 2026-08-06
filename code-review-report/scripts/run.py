#!/usr/bin/env python3
"""Skill: code-review-report - Generate a code review report from a diff."""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ========== 常量定义 ==========
VERSION = "2.0.0"
EXIT_SUCCESS = 0
EXIT_PARAM_ERROR = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_PARSE_ERROR = 3
EXIT_INTERNAL_ERROR = 4

# 严重级别
SEVERITY_LEVELS = ["P0", "P1", "P2", "P3"]

# 内置规则集（简化示例，实际规则更复杂）
BUILTIN_RULES = [
    {
        "id": "SEC001",
        "pattern": r"(?i)(password|secret|token)\s*=\s*['\"][^'\"]+['\"]",
        "severity": "P0",
        "message": "检测到硬编码敏感信息",
        "confidence": 0.95,
    },
    {
        "id": "LOG001",
        "pattern": r"(?i)(console\.log|print)\s*\(",
        "severity": "P2",
        "message": "检测到调试输出",
        "confidence": 0.85,
    },
    {
        "id": "PERF001",
        "pattern": r"(?i)(for\s+.*in\s+range\(len\()",
        "severity": "P2",
        "message": "建议使用 enumerate 替代 range(len())",
        "confidence": 0.80,
    },
    {
        "id": "STD001",
        "pattern": r"(?i)(\t+)",
        "severity": "P3",
        "message": "检测到制表符缩进，建议使用空格",
        "confidence": 0.90,
    },
]


def utc_now() -> str:
    """返回 UTC 当前时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子化写入文本文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def parse_diff(diff_text: str) -> List[Dict[str, Any]]:
    """解析 unified diff 文本，返回变更块列表。"""
    if not diff_text or not diff_text.strip():
        raise ValueError("Diff 内容为空")

    files = []
    current_file = None
    current_hunk = None

    lines = diff_text.splitlines()
    for line in lines:
        if line.startswith("diff --git"):
            if current_file:
                files.append(current_file)
            current_file = {"path": "", "hunks": []}
            # 提取文件路径
            match = re.search(r"diff --git a/(\S+) b/(\S+)", line)
            if match:
                current_file["path"] = match.group(2)
        elif line.startswith("@@") and current_file:
            if current_hunk:
                current_file["hunks"].append(current_hunk)
            # 解析 hunk 头
            match = re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match:
                current_hunk = {
                    "old_start": int(match.group(1)),
                    "new_start": int(match.group(2)),
                    "lines": [],
                }
            else:
                current_hunk = {"old_start": 0, "new_start": 0, "lines": []}
        elif current_hunk is not None:
            current_hunk["lines"].append(line)

    # 处理最后一个文件
    if current_file:
        if current_hunk:
            current_file["hunks"].append(current_hunk)
        files.append(current_file)

    if not files:
        raise ValueError("无法解析 diff 格式")

    return files


def apply_rules(line: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """对单行应用规则，返回匹配的问题列表。"""
    issues = []
    for rule in BUILTIN_RULES:
        if re.search(rule["pattern"], line):
            issue = {
                "rule_id": rule["id"],
                "severity": rule["severity"],
                "message": rule["message"],
                "confidence": rule["confidence"],
                "line": context.get("line_number", 0),
                "file": context.get("file_path", ""),
                "content": line.strip(),
            }
            issues.append(issue)
    return issues


def analyze_diff(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """分析 diff 文件列表，返回所有问题。"""
    all_issues = []
    for file_info in files:
        file_path = file_info.get("path", "")
        for hunk in file_info.get("hunks", []):
            new_line_num = hunk.get("new_start", 0)
            for line in hunk.get("lines", []):
                if line.startswith("+") and not line.startswith("+++"):
                    # 只分析新增行
                    context = {
                        "file_path": file_path,
                        "line_number": new_line_num,
                    }
                    issues = apply_rules(line[1:], context)
                    all_issues.extend(issues)
                    new_line_num += 1
                elif line.startswith("-") and not line.startswith("---"):
                    # 删除行不增加行号
                    pass
                elif line.startswith(" "):
                    # 上下文行
                    new_line_num += 1
    return all_issues


def generate_report(
    files: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    filter_severity: Optional[str] = None,
) -> str:
    """生成 Markdown 格式报告。"""
    lines = []
    lines.append("# 代码审查报告")
    lines.append("")
    lines.append(f"**生成时间:** {utc_now()}")
    lines.append(f"**分析文件数:** {len(files)}")
    lines.append(f"**发现问题数:** {len(issues)}")
    lines.append("")

    # 变更摘要
    lines.append("## 变更摘要")
    lines.append("")
    for file_info in files:
        path = file_info.get("path", "未知文件")
        hunk_count = len(file_info.get("hunks", []))
        lines.append(f"- **{path}** ({hunk_count} 个变更块)")
    lines.append("")

    # 问题清单
    lines.append("## 问题清单")
    lines.append("")

    if not issues:
        lines.append("未发现任何问题。")
    else:
        # 按严重级别分组
        for severity in SEVERITY_LEVELS:
            severity_issues = [i for i in issues if i["severity"] == severity]
            if filter_severity and severity != filter_severity:
                continue
            if severity_issues:
                lines.append(f"### {severity} 级别问题")
                lines.append("")
                for issue in severity_issues:
                    confidence_label = "高" if issue["confidence"] >= 0.9 else "中" if issue["confidence"] >= 0.7 else "低"
                    lines.append(f"- **{issue['rule_id']}** [{confidence_label}置信] {issue['message']}")
                    lines.append(f"  - 文件: `{issue['file']}` 行号: {issue['line']}")
                    lines.append(f"  - 内容: `{issue['content']}`")
                    lines.append("")

    lines.append("---")
    lines.append("*Generated by code-review-report skill v" + VERSION + "*")
    return "\n".join(lines)


def load_spec(spec_path: str) -> Dict[str, Any]:
    """加载并解析 JSON spec 文件。"""
    path = Path(spec_path)
    if not path.exists():
        raise FileNotFoundError(f"Spec 文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def match_trigger(spec: Dict[str, Any], trigger: str) -> bool:
    """检查 trigger 是否匹配 spec 的触发条件。"""
    spec_trigger = spec.get("trigger", "")
    return spec_trigger == trigger


def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("开始自检...")

    # 测试 1: 解析 diff
    test_diff = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,5 +1,7 @@
 def main():
-    print("old")
+    password = "secret123"
+    print("new")
+    for i in range(len(items)):
+        pass
     return 0
"""
    try:
        files = parse_diff(test_diff)
        assert len(files) == 1, "应解析出 1 个文件"
        assert files[0]["path"] == "test.py", "文件路径解析错误"
        assert len(files[0]["hunks"]) == 1, "应解析出 1 个 hunk"
        print("✓ diff 解析测试通过")
    except Exception as e:
        print(f"✗ diff 解析测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 2: 规则匹配
    try:
        issues = analyze_diff(files)
        assert len(issues) >= 3, f"应至少发现 3 个问题，实际 {len(issues)}"
        severities = [i["severity"] for i in issues]
        assert "P0" in severities, "应包含 P0 级别问题"
        assert "P2" in severities, "应包含 P2 级别问题"
        print("✓ 规则匹配测试通过")
    except Exception as e:
        print(f"✗ 规则匹配测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 3: 报告生成
    try:
        report = generate_report(files, issues)
        assert "# 代码审查报告" in report, "报告标题缺失"
        assert "变更摘要" in report, "变更摘要缺失"
        assert "问题清单" in report, "问题清单缺失"
        print("✓ 报告生成测试通过")
    except Exception as e:
        print(f"✗ 报告生成测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 4: 原子写入
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_report.md"
            atomic_write_text(test_file, "# Test Report")
            assert test_file.exists(), "文件未创建"
            content = test_file.read_text(encoding="utf-8")
            assert content == "# Test Report", "文件内容错误"
        print("✓ 原子写入测试通过")
    except Exception as e:
        print(f"✗ 原子写入测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 5: 过滤功能
    try:
        filtered_report = generate_report(files, issues, filter_severity="P0")
        assert "P1" not in filtered_report, "P1 问题不应出现在过滤后的报告中"
        assert "P0" in filtered_report, "P0 问题应出现在过滤后的报告中"
        print("✓ 过滤功能测试通过")
    except Exception as e:
        print(f"✗ 过滤功能测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    print("所有自检通过!")
    return EXIT_SUCCESS


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="代码审查差异分析工具 - 解析 diff 并生成质量报告"
    )
    parser.add_argument(
        "--diff",
        type=str,
        help="diff 文本内容或文件路径",
    )
    parser.add_argument(
        "--filter",
        type=str,
        choices=SEVERITY_LEVELS,
        help="按严重级别过滤报告",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出报告到文件",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"code-review-report v{VERSION}",
    )

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.diff:
        print("错误: 必须提供 --diff 参数", file=sys.stderr)
        parser.print_help()
        return EXIT_PARAM_ERROR

    # 读取 diff 内容
    try:
        diff_path = Path(args.diff)
        if diff_path.exists():
            diff_text = diff_path.read_text(encoding="utf-8")
        else:
            diff_text = args.diff
    except Exception as e:
        print(f"错误: 无法读取 diff: {e}", file=sys.stderr)
        return EXIT_FILE_NOT_FOUND

    # 解析 diff
    try:
        files = parse_diff(diff_text)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return EXIT_PARSE_ERROR
    except Exception as e:
        print(f"错误: 解析失败: {e}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    # 分析问题
    try:
        issues = analyze_diff(files)
    except Exception as e:
        print(f"错误: 分析失败: {e}", file=sys.stderr)
        return EXIT_INTERNAL_ERROR

    # 生成报告
    try:
        report = generate_report(files, issues, args.filter)
    except Exception as e:
        print(f"错误: 报告生成失败: {e}", file=sys.stderr)
        return EXIT_INTERNAL_ERROR

    # 输出报告
    if args.output:
        try:
            atomic_write_text(Path(args.output), report)
            print(f"报告已保存到: {args.output}")
        except Exception as e:
            print(f"错误: 无法保存报告: {e}", file=sys.stderr)
            return EXIT_INTERNAL_ERROR
    else:
        print(report)

    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
