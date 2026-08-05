#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码审查 · 差异分析 · 质量报告
=============================
解析统一 diff 格式的文本，定位逻辑、安全、性能与规范问题，
输出 P0/P1/P2/P3 四级问题清单和变更摘要。

用法示例:
    python run.py --input diff.txt --output report.txt
    python run.py --input diff.txt --output report.json --format json
    python run.py --selftest
    python run.py --version
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# ============================================================
# 核心业务：diff 解析
# ============================================================

def parse_diff(text: str) -> dict:
    """
    解析 unified diff 格式文本，提取文件变更信息。
    返回结构:
    {
        "files": [
            {
                "old_path": "a/src/main.py",
                "new_path": "b/src/main.py",
                "hunks": [
                    {
                        "old_start": 10, "old_count": 5,
                        "new_start": 10, "new_count": 7,
                        "lines": [
                            {"type": "context", "content": "..."},
                            {"type": "add", "content": "..."},
                            {"type": "del", "content": "..."},
                        ]
                    }
                ]
            }
        ]
    }
    """
    result = {"files": []}
    current_file = None
    current_hunk = None

    for line in text.splitlines():
        # 文件头: --- a/xxx 或 +++ b/xxx
        if line.startswith("--- ") or line.startswith("+++ "):
            if current_file and current_hunk:
                current_file["hunks"].append(current_hunk)
                current_hunk = None
            if current_file:
                result["files"].append(current_file)
                current_file = None

            if line.startswith("--- "):
                current_file = {
                    "old_path": line[4:].strip(),
                    "new_path": "",
                    "hunks": []
                }
            elif line.startswith("+++ ") and current_file:
                current_file["new_path"] = line[4:].strip()
            continue

        # hunk 头: @@ -10,5 +10,7 @@
        if line.startswith("@@"):
            if current_file and current_hunk:
                current_file["hunks"].append(current_hunk)
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if match and current_file:
                current_hunk = {
                    "old_start": int(match.group(1)),
                    "old_count": int(match.group(2) or 1),
                    "new_start": int(match.group(3)),
                    "new_count": int(match.group(4) or 1),
                    "lines": []
                }
            continue

        # 普通行
        if current_file and current_hunk:
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk["lines"].append({"type": "add", "content": line[1:]})
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk["lines"].append({"type": "del", "content": line[1:]})
            else:
                current_hunk["lines"].append({"type": "context", "content": line[1:] if line.startswith(" ") else line})

    # 收尾
    if current_file and current_hunk:
        current_file["hunks"].append(current_hunk)
    if current_file:
        result["files"].append(current_file)

    return result


# ============================================================
# 核心业务：问题检测
# ============================================================

# 安全风险模式
SECURITY_PATTERNS = [
    (r"eval\s*\(", "P0", "使用 eval 执行动态代码，存在代码注入风险"),
    (r"exec\s*\(", "P0", "使用 exec 执行动态代码，存在代码注入风险"),
    (r"os\.system\s*\(", "P1", "使用 os.system 执行系统命令，建议使用 subprocess 并校验参数"),
    (r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True", "P1", "shell=True 存在命令注入风险，建议使用参数列表形式"),
    (r"pickle\.loads?\s*\(", "P1", "反序列化不可信数据可能导致任意代码执行"),
    (r"yaml\.load\s*\([^)]*Loader\s*=\s*yaml\.(FullLoader|SafeLoader)", "P2", "yaml.load 需使用 SafeLoader"),
    (r"sqlite3\.connect\s*\([^)]*\)", "P2", "数据库连接需检查 SQL 注入风险"),
    (r"requests\.(get|post)\s*\([^)]*verify\s*=\s*False", "P1", "关闭 SSL 验证存在中间人攻击风险"),
    (r"md5\s*\(", "P2", "MD5 算法已不安全，建议使用 SHA-256"),
    (r"sha1\s*\(", "P2", "SHA-1 算法已不安全，建议使用 SHA-256"),
]

# 性能问题模式
PERFORMANCE_PATTERNS = [
    (r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(", "P2", "建议使用 enumerate 替代 range(len())"),
    (r"\.append\s*\(\s*[^)]*\)\s*$", "P3", "循环内 append 可考虑列表推导式"),
    (r"while\s+True", "P2", "无限循环需确保有退出条件"),
    (r"time\.sleep\s*\(\s*0\.\d+\s*\)", "P3", "短 sleep 可能影响性能"),
    (r"\.read\s*\(\s*\)\s*$", "P2", "一次性读取大文件可能内存不足，建议分块读取"),
]

# 规范问题模式
STYLE_PATTERNS = [
    (r"print\s*\(", "P3", "生产代码建议使用日志模块而非 print"),
    (r"except\s*:", "P2", "裸 except 会捕获所有异常，建议指定异常类型"),
    (r"except\s+Exception\s*:", "P3", "捕获 Exception 过于宽泛，建议精确捕获"),
    (r"TODO|FIXME|HACK", "P3", "存在待办标记，需确认是否遗留"),
    (r"if\s+[^:]+:\s*$", "P3", "检查 if 语句是否有对应 else 分支"),
    (r"global\s+\w+", "P2", "使用全局变量增加耦合，建议通过参数传递"),
]


def detect_issues(parsed_diff: dict) -> list:
    """
    对解析后的 diff 执行四维检查（逻辑/安全/性能/规范）。
    返回问题列表，每项包含: 文件、行号、级别、类别、描述。
    """
    issues = []
    line_no = 0

    for file_info in parsed_diff["files"]:
        file_path = file_info["new_path"] or file_info["old_path"]
        for hunk in file_info["hunks"]:
            current_line = hunk["new_start"]
            for line_info in hunk["lines"]:
                content = line_info["content"]
                line_type = line_info["type"]

                # 只检查新增和修改的行
                if line_type in ("add", "context"):
                    # 安全检查
                    for pattern, level, desc in SECURITY_PATTERNS:
                        if re.search(pattern, content):
                            issues.append({
                                "file": file_path,
                                "line": current_line,
                                "level": level,
                                "category": "安全",
                                "desc": desc,
                                "code": content.strip()[:80]
                            })

                    # 性能检查
                    for pattern, level, desc in PERFORMANCE_PATTERNS:
                        if re.search(pattern, content):
                            issues.append({
                                "file": file_path,
                                "line": current_line,
                                "level": level,
                                "category": "性能",
                                "desc": desc,
                                "code": content.strip()[:80]
                            })

                    # 规范检查
                    for pattern, level, desc in STYLE_PATTERNS:
                        if re.search(pattern, content):
                            issues.append({
                                "file": file_path,
                                "line": current_line,
                                "level": level,
                                "category": "规范",
                                "desc": desc,
                                "code": content.strip()[:80]
                            })

                    # 逻辑检查：检测明显的逻辑问题
                    if "==" in content and "=" in content.replace("==", ""):
                        issues.append({
                            "file": file_path,
                            "line": current_line,
                            "level": "P1",
                            "category": "逻辑",
                            "desc": "疑似赋值与比较混淆，检查是否应为 == 或 =",
                            "code": content.strip()[:80]
                        })

                    if re.search(r"return\s+None\s*$", content) and "def " in content:
                        issues.append({
                            "file": file_path,
                            "line": current_line,
                            "level": "P3",
                            "category": "逻辑",
                            "desc": "函数显式返回 None，可省略 return 语句",
                            "code": content.strip()[:80]
                        })

                if line_type != "del":
                    current_line += 1

    return issues


# ============================================================
# 核心业务：报告生成
# ============================================================

def generate_summary(parsed_diff: dict, issues: list) -> dict:
    """生成变更摘要"""
    files = parsed_diff["files"]
    total_add = sum(
        sum(1 for l in h["lines"] if l["type"] == "add")
        for f in files for h in f["hunks"]
    )
    total_del = sum(
        sum(1 for l in h["lines"] if l["type"] == "del")
        for f in files for h in f["hunks"]
    )

    level_counter = Counter(i["level"] for i in issues)
    category_counter = Counter(i["category"] for i in issues)

    return {
        "文件数": len(files),
        "新增行数": total_add,
        "删除行数": total_del,
        "问题总数": len(issues),
        "问题分级": dict(level_counter),
        "问题分类": dict(category_counter),
        "文件列表": [f["new_path"] or f["old_path"] for f in files],
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def format_report(parsed_diff: dict, issues: list, summary: dict, fmt: str = "text") -> str:
    """格式化输出报告"""
    if fmt == "json":
        return json.dumps({
            "summary": summary,
            "issues": issues
        }, ensure_ascii=False, indent=2)

    # 文本格式
    lines = []
    lines.append("=" * 60)
    lines.append("代码审查报告")
    lines.append("=" * 60)
    lines.append(f"生成时间: {summary['生成时间']}")
    lines.append(f"涉及文件: {summary['文件数']} 个")
    lines.append(f"变更统计: +{summary['新增行数']} / -{summary['删除行数']}")
    lines.append(f"问题总数: {summary['问题总数']}")
    lines.append("")

    # 问题分级统计
    lines.append("【问题统计】")
    for level in ["P0", "P1", "P2", "P3"]:
        count = summary["问题分级"].get(level, 0)
        lines.append(f"  {level}: {count} 个")
    lines.append("")

    # 问题详情
    if issues:
        lines.append("【问题详情】")
        for i, issue in enumerate(issues, 1):
            lines.append(f"\n{i}. [{issue['level']}] {issue['category']}问题")
            lines.append(f"   文件: {issue['file']}")
            lines.append(f"   行号: {issue['line']}")
            lines.append(f"   描述: {issue['desc']}")
            lines.append(f"   代码: {issue['code']}")
    else:
        lines.append("\n未发现明显问题。")

    # 变更文件列表
    lines.append("\n【变更文件】")
    for f in summary["文件列表"]:
        lines.append(f"  - {f}")

    return "\n".join(lines)


# ============================================================
# 自检函数
# ============================================================

def selftest() -> bool:
    """自检函数：验证核心功能是否正常"""
    print("运行自检...")

    # 测试 diff 解析
    test_diff = """--- a/test.py
+++ b/test.py
@@ -1,5 +1,7 @@
 def main():
-    print("old")
+    eval("print('new')")
+    import os
+    os.system("ls")
     return None
"""
    parsed = parse_diff(test_diff)
    assert len(parsed["files"]) == 1, "文件解析失败"
    assert parsed["files"][0]["new_path"] == "b/test.py", "路径解析失败"
    assert len(parsed["files"][0]["hunks"]) == 1, "hunk 解析失败"
    print("✓ diff 解析正常")

    # 测试问题检测
    issues = detect_issues(parsed)
    assert len(issues) >= 3, f"问题检测失败，仅发现 {len(issues)} 个问题"
    levels = [i["level"] for i in issues]
    assert "P0" in levels, "未检测到 P0 级别问题"
    assert "P1" in levels, "未检测到 P1 级别问题"
    print(f"✓ 问题检测正常，发现 {len(issues)} 个问题")

    # 测试报告生成
    summary = generate_summary(parsed, issues)
    report = format_report(parsed, issues, summary, "text")
    assert "代码审查报告" in report, "文本报告生成失败"
    report_json = format_report(parsed, issues, summary, "json")
    assert json.loads(report_json), "JSON 报告生成失败"
    print("✓ 报告生成正常")

    # 测试边界情况
    empty_diff = parse_diff("")
    assert empty_diff["files"] == [], "空 diff 解析失败"
    print("✓ 边界情况处理正常")

    print("✓ 所有自检通过")
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="代码审查 · 差异分析 · 质量报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python run.py --input diff.txt --output report.txt
  python run.py --input diff.txt --output report.json --format json
  python run.py --selftest
  python run.py --version
"""
    )
    parser.add_argument("--input", "-i", help="输入 diff 文件路径（或使用 stdin）")
    parser.add_argument("--output", "-o", help="输出报告文件路径（默认 stdout）")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text",
                        help="输出格式（默认 text）")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", "-v", action="store_true", help="显示版本信息")

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print("code-review-report v1.0.0")
        return 0

    # 自检模式
    if args.selftest:
        try:
            selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    # 读取输入
    try:
        if args.input:
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
                return 1
            diff_text = input_path.read_text(encoding="utf-8")
        else:
            print("提示: 未指定 --input，从标准输入读取 diff 内容（Ctrl+D 结束）...")
            diff_text = sys.stdin.read()
    except Exception as e:
        print(f"错误: 读取输入失败: {e}", file=sys.stderr)
        return 1

    # 解析 diff
    parsed = parse_diff(diff_text)
    if not parsed["files"]:
        print("错误: 无法识别 diff 格式，请提供 unified diff 格式的文本", file=sys.stderr)
        return 1

    # 检测问题
    issues = detect_issues(parsed)

    # 生成摘要
    summary = generate_summary(parsed, issues)

    # 格式化报告
    report = format_report(parsed, issues, summary, args.format)

    # 输出
    try:
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report, encoding="utf-8")
            print(f"报告已写入: {output_path}")
        else:
            print(report)
    except Exception as e:
        print(f"错误: 写入输出失败: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
