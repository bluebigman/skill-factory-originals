#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------- 类型映射 ----------
type_map = {
    "bug": "bugfix",
    "修复": "bugfix",
    "fix": "bugfix",
    "feature": "feature",
    "功能": "feature",
    "feat": "feature",
    "refactor": "refactor",
    "重构": "refactor",
    "docs": "docs",
    "文档": "docs",
    "test": "test",
    "测试": "test",
    "chore": "chore",
    "杂务": "chore",
    "perf": "perf",
    "性能": "perf",
    "style": "style",
    "格式": "style",
    "build": "build",
    "构建": "build",
    "ci": "ci",
    "持续集成": "ci",
    "revert": "revert",
    "回滚": "revert",
    "merge": "merge",
    "合并": "merge",
    "release": "release",
    "发布": "release",
    "other": "other",
    "其他": "other",
}

# ---------- 辅助函数 ----------
def normalize_type(raw_type: str) -> str:
    """将原始类型字符串映射为规范类型，若无法映射则返回 'other'。"""
    if not raw_type:
        return "other"
    key = raw_type.strip().lower()
    # 直接匹配
    if key in type_map:
        return type_map[key]
    # 尝试模糊匹配（包含关系）
    for k, v in type_map.items():
        if k in key or key in k:
            return v
    return "other"


def parse_commit_message(message: str) -> Dict:
    """
    解析提交信息，返回结构化字典。
    支持 Conventional Commits 格式：type(scope): subject
    也支持简单文本。
    """
    result = {
        "type": "other",
        "scope": None,
        "subject": "",
        "body": "",
        "breaking": False,
        "conventional": False,
        "raw": message,
    }
    if not message:
        return result

    lines = message.strip().split("\n")
    first_line = lines[0].strip()

    # 尝试匹配 conventional commit
    # 格式: type(scope)!: subject 或 type: subject
    pattern = r"^([a-zA-Z\u4e00-\u9fa5]+)(?:\(([^)]+)\))?(!)?:\s*(.+)$"
    match = re.match(pattern, first_line)
    if match:
        raw_type = match.group(1)
        scope = match.group(2)
        breaking_marker = match.group(3)
        subject = match.group(4).strip()
        result["type"] = normalize_type(raw_type)
        result["scope"] = scope
        result["subject"] = subject
        result["breaking"] = bool(breaking_marker) or "BREAKING CHANGE" in message
        result["conventional"] = True
    else:
        # 简单文本，尝试从开头提取类型词
        words = first_line.split()
        if words:
            candidate = words[0].rstrip(":")
            result["type"] = normalize_type(candidate)
            # 移除类型前缀
            if candidate.lower() in type_map or candidate in type_map:
                result["subject"] = " ".join(words[1:]).strip()
            else:
                result["subject"] = first_line
        else:
            result["subject"] = first_line

    # 提取 body（从第二行开始）
    if len(lines) > 1:
        body_lines = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped:
                body_lines.append(stripped)
        result["body"] = "\n".join(body_lines)

    return result


def generate_conventional_commit(parsed: Dict) -> str:
    """根据解析结果生成 Conventional Commits 格式的提交信息。"""
    type_str = parsed["type"]
    scope_str = f"({parsed['scope']})" if parsed.get("scope") else ""
    breaking_str = "!" if parsed.get("breaking") else ""
    subject = parsed.get("subject", "").strip()
    if not subject:
        subject = "update"
    header = f"{type_str}{scope_str}{breaking_str}: {subject}"

    body = parsed.get("body", "").strip()
    if body:
        return f"{header}\n\n{body}"
    return header


def analyze_commit(commit: Dict) -> Dict:
    """对单个提交进行分析，返回分析结果。"""
    parsed = parse_commit_message(commit.get("message", ""))
    analysis = {
        "type": parsed["type"],
        "scope": parsed["scope"],
        "subject": parsed["subject"],
        "breaking": parsed["breaking"],
        "has_body": bool(parsed["body"]),
        "body_length": len(parsed["body"]),
        "conventional": parsed["conventional"],
        "suggested": generate_conventional_commit(parsed),
    }
    return analysis


def process_commits(commits: List[Dict]) -> List[Dict]:
    """处理提交列表，返回分析结果列表。"""
    results = []
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        analysis = analyze_commit(commit)
        analysis["original"] = commit
        results.append(analysis)
    return results


def format_output(results: List[Dict], format_type: str = "text") -> str:
    """根据指定格式输出结果。"""
    if format_type == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    elif format_type == "table":
        lines = []
        lines.append("| # | Type | Scope | Subject | Breaking | Conventional |")
        lines.append("|---|------|-------|---------|----------|--------------|")
        for idx, r in enumerate(results, 1):
            scope = r.get("scope") or "-"
            subject = r.get("subject", "")[:50]
            breaking = "Yes" if r.get("breaking") else "No"
            conv = "Yes" if r.get("conventional") else "No"
            lines.append(f"| {idx} | {r['type']} | {scope} | {subject} | {breaking} | {conv} |")
        return "\n".join(lines)
    else:  # text
        lines = []
        for idx, r in enumerate(results, 1):
            lines.append(f"Commit #{idx}:")
            lines.append(f"  Type: {r['type']}")
            if r.get("scope"):
                lines.append(f"  Scope: {r['scope']}")
            lines.append(f"  Subject: {r['subject']}")
            lines.append(f"  Breaking: {'Yes' if r.get('breaking') else 'No'}")
            lines.append(f"  Conventional: {'Yes' if r.get('conventional') else 'No'}")
            if r.get("has_body"):
                lines.append(f"  Body length: {r['body_length']} chars")
            lines.append(f"  Suggested: {r['suggested']}")
            lines.append("")
        return "\n".join(lines).strip()


def read_commits_from_file(filepath: str) -> List[Dict]:
    """从文件读取提交数据，支持 JSON 或纯文本格式。"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    content = path.read_text(encoding="utf-8")
    content = content.strip()
    if not content:
        return []

    # 尝试解析为 JSON
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            if "commits" in data:
                return data["commits"]
            else:
                return [data]
    except json.JSONDecodeError:
        pass

    # 按行解析为纯文本提交
    commits = []
    current_msg = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            if current_msg:
                commits.append({"message": "\n".join(current_msg)})
                current_msg = []
        else:
            current_msg.append(stripped)
    if current_msg:
        commits.append({"message": "\n".join(current_msg)})
    return commits


def write_output(content: str, output_file: Optional[str] = None) -> None:
    """将内容写入文件或标准输出。"""
    if output_file:
        if not dry_run or getattr(args, "force", False):
            Path(output_file).write_text(content, encoding="utf-8")
    else:
        print(content)


def run_selftest() -> bool:
    """运行自测，验证核心功能。"""
    test_cases = [
        {
            "message": "fix: correct login bug",
            "expected_type": "bugfix",
            "expected_conv": True,
        },
        {
            "message": "feat(api): add new endpoint",
            "expected_type": "feature",
            "expected_conv": True,
        },
        {
            "message": "修复登录问题",
            "expected_type": "bugfix",
            "expected_conv": False,
        },
        {
            "message": "docs: update README",
            "expected_type": "docs",
            "expected_conv": True,
        },
        {
            "message": "refactor!: change internal API",
            "expected_type": "refactor",
            "expected_conv": True,
            "expected_breaking": True,
        },
        {
            "message": "普通提交信息",
            "expected_type": "other",
            "expected_conv": False,
        },
    ]

    all_passed = True
    for i, case in enumerate(test_cases, 1):
        parsed = parse_commit_message(case["message"])
        if parsed["type"] != case["expected_type"]:
            print(f"Test {i} FAILED: type mismatch. Expected {case['expected_type']}, got {parsed['type']}")
            all_passed = False
        if parsed["conventional"] != case["expected_conv"]:
            print(f"Test {i} FAILED: conventional mismatch. Expected {case['expected_conv']}, got {parsed['conventional']}")
            all_passed = False
        if case.get("expected_breaking") and not parsed["breaking"]:
            print(f"Test {i} FAILED: breaking mismatch. Expected True, got False")
            all_passed = False

    # 测试 generate_conventional_commit
    parsed = parse_commit_message("fix: correct bug")
    generated = generate_conventional_commit(parsed)
    if generated != "bugfix: correct bug":
        print(f"Test generate FAILED: expected 'bugfix: correct bug', got '{generated}'")
        all_passed = False

    # 测试 normalize_type
    if normalize_type("bug") != "bugfix":
        print("Test normalize FAILED: 'bug' should map to 'bugfix'")
        all_passed = False
    if normalize_type("unknown_type") != "other":
        print("Test normalize FAILED: unknown should map to 'other'")
        all_passed = False

    if all_passed:
        print("All selftests passed.")
        return True
    else:
        print("Some selftests failed.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="FlowState CLI - 分析提交信息并生成 Conventional Commits 建议",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        nargs="?",
        help="输入文件路径（JSON 或纯文本），若不提供则从标准输入读取",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径，若不提供则输出到标准输出",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测并退出",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="flowstatecli 1.0.0",
    )

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 读取输入
    if args.input:
        try:
            commits = read_commits_from_file(args.input)
        except Exception as e:
            print(f"Error reading input: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 从标准输入读取
        content = sys.stdin.read().strip()
        if not content:
            print("No input provided.", file=sys.stderr)
            sys.exit(1)
        # 尝试 JSON
        try:
            data = json.loads(content)
            if isinstance(data, list):
                commits = data
            elif isinstance(data, dict):
                commits = data.get("commits", [data])
            else:
                commits = []
        except json.JSONDecodeError:
            # 按纯文本解析
            commits = []
            current_msg = []
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped:
                    if current_msg:
                        commits.append({"message": "\n".join(current_msg)})
                        current_msg = []
                else:
                    current_msg.append(stripped)
            if current_msg:
                commits.append({"message": "\n".join(current_msg)})

    if not commits:
        print("No commits found.", file=sys.stderr)
        sys.exit(1)

    # 处理
    results = process_commits(commits)
    output = format_output(results, args.format)

    # 输出
    try:
        write_output(output, args.output)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
