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
VERSION = "2.1.0"
EXIT_SUCCESS = 0
EXIT_PARAM_ERROR = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_PARSE_ERROR = 3
EXIT_INTERNAL_ERROR = 4

# 严重级别
SEVERITY_LEVELS = ["P0", "P1", "P2", "P3"]

# 内置规则集（基于正则的代码风格扫描）
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
        "pattern": r"(?i)for\s+\w+\s+in\s+range\(len\(",
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
    """解析 unified diff 文本，返回变更块列表。

    支持标准 git diff 格式，对非标准格式进行容错处理。
    对 hunk 头进行严格解析，格式错误时抛出明确异常。
    """
    if not diff_text or not diff_text.strip():
        raise ValueError("Diff 内容为空")

    files = []
    current_file = None
    current_hunk = None

    lines = diff_text.splitlines()
    for line in lines:
        if line.startswith("diff --git"):
            # 保存上一个文件
            if current_file:
                if current_hunk:
                    current_file["hunks"].append(current_hunk)
                    current_hunk = None
                files.append(current_file)
            current_file = {"path": "", "hunks": []}
            # 提取文件路径
            match = re.search(r"diff --git a/(\S+) b/(\S+)", line)
            if match:
                current_file["path"] = match.group(2)
            else:
                # 尝试其他格式
                match = re.search(r"diff --git (\S+) (\S+)", line)
                if match:
                    current_file["path"] = match.group(2)
        elif line.startswith("Index:") and current_file is None:
            # SVN 格式
            current_file = {"path": "", "hunks": []}
            match = re.search(r"Index:\s+(.+)", line)
            if match:
                current_file["path"] = match.group(1).strip()
        elif line.startswith("===") and current_file is None:
            # 其他格式
            current_file = {"path": "unknown", "hunks": []}
        elif line.startswith("@@") and current_file:
            # 保存上一个 hunk
            if current_hunk:
                current_file["hunks"].append(current_hunk)
            # 严格解析 hunk 头
            match = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match:
                current_hunk = {
                    "old_start": int(match.group(1)),
                    "new_start": int(match.group(2)),
                    "lines": [],
                }
            else:
                # 格式错误，抛出明确异常
                raise ValueError(f"无法解析 hunk 头: {line}")
        elif current_hunk is not None:
            current_hunk["lines"].append(line)
        elif current_file is not None and not line.startswith(("---", "+++")):
            # 非标准格式，尝试作为普通行处理
            if current_hunk is None:
                current_hunk = {"old_start": 0, "new_start": 0, "lines": []}
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
    """对单行应用规则，返回匹配的问题列表。

    对 SEC001 规则增加上下文过滤，跳过注释行。
    """
    issues = []
    stripped_line = line.strip()
    
    for rule in BUILTIN_RULES:
        # SEC001 规则：跳过注释行（# 或 // 开头）
        if rule["id"] == "SEC001":
            if stripped_line.startswith("#") or stripped_line.startswith("//"):
                continue
        
        if re.search(rule["pattern"], line):
            # 动态计算 confidence
            confidence = rule["confidence"]
            # 根据匹配位置调整 confidence
            if rule["id"] == "SEC001":
                # 硬编码密码在赋值语句中，置信度较高
                if "=" in line and not line.strip().startswith(("#", "//")):
                    confidence = min(0.99, confidence + 0.04)
                else:
                    confidence = max(0.5, confidence - 0.2)
            
            issue = {
                "rule_id": rule["id"],
                "severity": rule["severity"],
                "message": rule["message"],
                "confidence": confidence,
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

    # 测试 1: 解析标准 git diff
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
        print("✓ 标准 diff 解析测试通过")
    except Exception as e:
        print(f"✗ 标准 diff 解析测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 2: 解析非标准 diff（无 diff --git 前缀）
    test_diff_svn = """Index: test.py
===================================================================
--- test.py (revision 1)
+++ test.py (working copy)
@@ -1,3 +1,4 @@
 def main():
-    print("old")
+    print("new")
     return 0
"""
    try:
        files_svn = parse_diff(test_diff_svn)
        assert len(files_svn) == 1, "应解析出 1 个文件"
        assert files_svn[0]["path"] == "test.py", "SVN 文件路径解析错误"
        assert len(files_svn[0]["hunks"]) == 1, "应解析出 1 个 hunk"
        print("✓ 非标准 diff 解析测试通过")
    except Exception as e:
        print(f"✗ 非标准 diff 解析测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 3: 规则匹配（含 PERF001 实际匹配）
    try:
        issues = analyze_diff(files)
        assert len(issues) >= 3, f"应至少发现 3 个问题，实际 {len(issues)}"
        severities = [i["severity"] for i in issues]
        assert "P0" in severities, "应包含 P0 级别问题"
        assert "P2" in severities, "应包含 P2 级别问题"
        
        # 验证 PERF001 规则实际触发
        perf_issues = [i for i in issues if i["rule_id"] == "PERF001"]
        assert len(perf_issues) == 1, f"PERF001 应触发 1 次，实际 {len(perf_issues)}"
        assert perf_issues[0]["line"] == 6, f"PERF001 应在第 6 行，实际 {perf_issues[0]['line']}"
        print("✓ 规则匹配测试通过（含 PERF001 实际匹配）")
    except Exception as e:
        print(f"✗ 规则匹配测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 4: 报告生成
    try:
        report = generate_report(files, issues)
        assert "# 代码审查报告" in report, "报告标题缺失"
        assert "变更摘要" in report, "变更摘要缺失"
        assert "问题清单" in report, "问题清单缺失"
        assert "PERF001" in report, "PERF001 问题应出现在报告中"
        print("✓ 报告生成测试通过")
    except Exception as e:
        print(f"✗ 报告生成测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 5: 原子写入
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

    # 测试 6: 过滤功能
    try:
        filtered_report = generate_report(files, issues, filter_severity="P0")
        assert "P1" not in filtered_report, "P1 问题不应出现在过滤后的报告中"
        assert "P0" in filtered_report, "P0 问题应出现在过滤后的报告中"
        assert "PERF001" not in filtered_report, "PERF001 不应出现在 P0 过滤报告中"
        print("✓ 过滤功能测试通过")
    except Exception as e:
        print(f"✗ 过滤功能测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 7: 空 diff 处理
    try:
        parse_diff("")
        print("✗ 空 diff 应抛出异常")
        return EXIT_INTERNAL_ERROR
    except ValueError:
        print("✓ 空 diff 处理测试通过")
    except Exception as e:
        print(f"✗ 空 diff 处理测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 8: 主流程集成测试（通过 main 函数）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试 diff 文件
            diff_file = Path(tmpdir) / "test.diff"
            diff_file.write_text(test_diff, encoding="utf-8")
            
            # 创建输出文件路径
            output_file = Path(tmpdir) / "report.md"
            
            # 调用主函数
            exit_code = main([
                "--diff", str(diff_file),
                "--output", str(output_file),
            ])
            
            assert exit_code == EXIT_SUCCESS, f"主函数应返回 0，实际 {exit_code}"
            assert output_file.exists(), "输出文件应存在"
            
            # 验证报告内容
            report_content = output_file.read_text(encoding="utf-8")
            assert "# 代码审查报告" in report_content, "报告标题缺失"
            assert "PERF001" in report_content, "PERF001 问题应出现在报告中"
            print("✓ 主流程集成测试通过")
    except Exception as e:
        print(f"✗ 主流程集成测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试 9: 无效 hunk 头处理
    try:
        invalid_diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ invalid hunk header @@
+print("test")
"""
        parse_diff(invalid_diff)
        print("✗ 无效 hunk 头应抛出异常")
        return EXIT_INTERNAL_ERROR
    except ValueError as e:
        print(f"✓ 无效 hunk 头处理测试通过: {e}")
    except Exception as e:
        print(f"✗ 无效 hunk 头处理测试失败: {e}")
        return EXIT_INTERNAL_ERROR

    # 测试
