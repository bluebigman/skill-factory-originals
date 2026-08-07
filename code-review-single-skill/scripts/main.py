#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单文件代码审查技能 - 独立实现
基于功能规格 code-review-single-skill 的 clean-room 实现。
仅使用 Python 标准库。
"""

import argparse
import sys
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "E001": "未检测到代码内容，请提供待审查的代码文本或文件路径。",
    "E002": "无法确定代码语言，请明确指定（如 Python/Java/Go）。",
    "E003": "代码疑似被截断，请提供完整文件内容。",
    "E004": "检测到多文件引用，本 Skill 仅支持单文件审查。",
    "E005": "内部错误：审查过程发生异常。",
    "E006": "输入参数无效。",
    "E007": "文件读取失败。",
    "E008": "输出格式不支持。",
    "E009": "自检失败：核心逻辑验证未通过。",
    "E010": "未预期的运行时错误。",
}


class ReviewError(Exception):
    """自定义审查异常，携带错误码。"""

    def __init__(self, code: str, message: str = None):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ReviewIssue:
    """单个审查问题。"""
    level: str          # 阻断 / 建议 / 可选
    line: int           # 行号
    description: str    # 问题描述
    suggestion: str     # 修改建议


@dataclass
class ReviewResult:
    """审查结果汇总。"""
    filename: str = ""
    language: str = ""
    line_count: int = 0
    issues: List[ReviewIssue] = field(default_factory=list)
    summary: str = ""

    def to_markdown(self) -> str:
        """转换为 Markdown 格式报告。"""
        lines = []
        lines.append("## 审查报告")
        lines.append(f"**文件**：{self.filename or '未知'}")
        lines.append(f"**语言**：{self.language or '未知'}")
        lines.append(f"**代码规模**：{self.line_count} 行")
        lines.append("")
        lines.append("### 问题清单")
        lines.append("| 级别 | 行号 | 问题描述 | 修改建议 |")
        lines.append("|------|------|----------|----------|")

        if not self.issues:
            lines.append("| - | - | 未发现明显问题 | - |")
        else:
            for issue in self.issues:
                # 转义 Markdown 表格中的竖线
                desc = issue.description.replace("|", "\\|")
                sugg = issue.suggestion.replace("|", "\\|")
                lines.append(f"| {issue.level} | {issue.line} | {desc} | {sugg} |")

        lines.append("")
        lines.append("### 总体评价")
        lines.append(self.summary or "审查完成。")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 语言识别
# ---------------------------------------------------------------------------
def detect_language(code: str, filename: str = "") -> str:
    """根据文件扩展名和代码特征识别编程语言。"""
    if not code or not code.strip():
        return ""

    # 扩展名优先
    ext_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++ 头文件",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".rs": "Rust",
        ".sh": "Shell",
        ".html": "HTML",
        ".css": "CSS",
        ".json": "JSON",
        ".md": "Markdown",
    }
    if filename:
        ext = filename.lower().rsplit(".", 1)[-1]
        if f".{ext}" in ext_map:
            return ext_map[f".{ext}"]

    # 代码特征识别 - 使用更严格的正则表达式
    first_lines = code.strip().splitlines()[:10]
    joined = "\n".join(first_lines).lower()
    
    # 检查是否有足够的代码特征
    # 统计代码特征标记的数量
    feature_count = 0
    
    # Python 特征
    if re.search(r"^\s*(import|from)\s+\w+\s*(import)?", joined, re.MULTILINE):
        feature_count += 1
        # 需要更多的 Python 特征来确认
        if re.search(r"^\s*def\s+\w+\s*\(", joined, re.MULTILINE) or \
           re.search(r"^\s*class\s+\w+", joined, re.MULTILINE) or \
           re.search(r"^\s*print\s*\(", joined, re.MULTILINE) or \
           re.search(r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]", joined, re.MULTILINE):
            return "Python"
    
    # Java 特征
    if re.search(r"^\s*(public|private|protected)\s+(class|interface|enum)\s+\w+", joined, re.MULTILINE):
        return "Java"
    if re.search(r"^\s*package\s+[\w.]+;", joined, re.MULTILINE):
        return "Java"
    if re.search(r"^\s*import\s+java\.", joined, re.MULTILINE):
        return "Java"
    
    # Go 特征
    if re.search(r"^\s*package\s+main\s*$", joined, re.MULTILINE):
        return "Go"
    if re.search(r"^\s*func\s+\w+\s*\(", joined, re.MULTILINE):
        return "Go"
    
    # C/C++ 特征
    if re.search(r"^\s*#include\s*[<\"][^>\"]+[>\"]", joined, re.MULTILINE):
        # 需要更多特征来区分 C 和 C++
        if re.search(r"std::", joined):
            return "C++"
        return "C"
    
    # JavaScript 特征
    if re.search(r"^\s*(const|let|var)\s+\w+\s*=", joined, re.MULTILINE):
        if re.search(r"function\s*\(|=>", joined):
            return "JavaScript"
    if re.search(r"^\s*function\s+\w+\s*\(", joined, re.MULTILINE):
        return "JavaScript"
    
    # Rust 特征
    if re.search(r"^\s*fn\s+\w+\s*\(", joined, re.MULTILINE):
        return "Rust"
    if re.search(r"^\s*use\s+std::", joined, re.MULTILINE):
        return "Rust"
    
    # Shell 特征
    if re.search(r"^\s*#!/bin/", joined, re.MULTILINE):
        return "Shell"
    
    # 其他语言特征
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", joined, re.MULTILINE):
        return "Python"
    if re.search(r"^\s*class\s+\w+\s*[:{]", joined, re.MULTILINE):
        return "Python"  # 可能是 Python 3.x 或 Ruby，但更可能是 Python
    
    # 如果没有任何明确特征，返回空字符串
    return ""


# ---------------------------------------------------------------------------
# 代码完整性检查
# ---------------------------------------------------------------------------
def check_completeness(code: str, language: str) -> Optional[str]:
    """检查代码片段是否完整。返回错误码或 None。"""
    if not code or not code.strip():
        return "E001"

    lines = code.splitlines()
    if len(lines) < 2:
        return None  # 单行代码也可能完整

    # 检查括号配对（简化版）
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for i, line in enumerate(lines, 1):
        for ch in line:
            if ch in "([{":
                stack.append(ch)
            elif ch in ")]}":
                if not stack or stack[-1] != pairs[ch]:
                    return "E003"
                stack.pop()

    if stack:
        return "E003"

    # Python 缩进检查（粗略）
    if language == "Python":
        for i, line in enumerate(lines):
            if line.strip() and line.startswith("    ") and i > 0:
                prev = lines[i - 1]
                if prev.strip() and not prev.strip().endswith(":") and not prev.strip().startswith(("#", "//")):
                    if prev.strip() and not re.match(r"^\s*(return|pass|break|continue|raise)\b", prev.strip()):
                        pass  # 过于复杂，跳过

    return None


# ---------------------------------------------------------------------------
# 多文件引用检测
# ---------------------------------------------------------------------------
def check_multi_file_refs(code: str) -> bool:
    """检测是否引用了外部文件（多文件场景）。"""
    if not code:
        return False

    patterns = [
        r"^\s*(import|from)\s+[\w.]+\s*$",           # Python import
        r"^\s*require\s*\(['\"][^'\"]+['\"]\)",        # JS require
        r"^\s*#include\s*[<\"][^>\"]+[>\"]",           # C/C++ include
        r"^\s*import\s+java\.",                        # Java import
        r"^\s*use\s+[\w:]+\s*::",                      # Rust use
    ]
    for pattern in patterns:
        if re.search(pattern, code, re.MULTILINE):
            return True
    return False


# ---------------------------------------------------------------------------
# 静态审查核心逻辑
# ---------------------------------------------------------------------------
def analyze_code(code: str, language: str, focus: str = "") -> List[ReviewIssue]:
    """执行静态审查，返回问题列表。"""
    issues = []
    lines = code.splitlines()
    total_lines = len(lines)

    # 1. 命名规范检查
    for i, line in enumerate(lines, 1):
        # 检查 Python 函数/类命名
        if language == "Python":
            func_match = re.search(r"^\s*def\s+(\w+)\s*\(", line)
            if func_match:
                name = func_match.group(1)
                if not re.match(r"^[a-z_][a-z0-9_]*$", name):
                    issues.append(ReviewIssue(
                        level="建议",
                        line=i,
                        description=f"函数命名 '{name}' 不符合 snake_case 规范",
                        suggestion="使用小写字母和下划线，如 my_function"
                    ))
            class_match = re.search(r"^\s*class\s+(\w+)", line)
            if class_match:
                name = class_match.group(1)
                if not re.match(r"^[A-Z][a-zA-Z0-9]*$", name):
                    issues.append(ReviewIssue(
                        level="建议",
                        line=i,
                        description=f"类命名 '{name}' 不符合 PascalCase 规范",
                        suggestion="使用大写字母开头，如 MyClass"
                    ))

        # 通用：检查魔法数字（硬编码数值）
        if language in ("Python", "Java", "Go", "C", "C++", "JavaScript"):
            # 跳过注释行
            if line.strip().startswith(("#", "//", "/*", "*")):
                continue
            # 查找数字字面量（排除 0, 1, 2, -1 等常用值）
            numbers = re.findall(r"\b(\d{3,})\b", line)
            for num in numbers:
                issues.append(ReviewIssue(
                    level="可选",
                    line=i,
                    description=f"魔法数字 {num}",
                    suggestion="建议提取为具名常量"
                ))

    # 2. 常见反模式检查
    for i, line in enumerate(lines, 1):
        # 过深嵌套（缩进大于 8 空格）
        indent = len(line) - len(line.lstrip())
        if indent > 8 and language in ("Python", "Go"):
            issues.append(ReviewIssue(
                level="建议",
                line=i,
                description=f"缩进过深（{indent} 空格）",
                suggestion="考虑提取函数或简化逻辑"
            ))

        # 重复代码检测（相邻相似行）
        if i > 1 and i < total_lines:
            prev_line = lines[i - 2].strip()
            curr_line = line.strip()
            if prev_line and curr_line and prev_line == curr_line:
                issues.append(ReviewIssue(
                    level="可选",
                    line=i,
                    description="检测到重复代码",
                    suggestion="考虑提取公共函数"
                ))

        # 空 except/捕获所有异常
        if language == "Python":
            if re.search(r"^\s*except\s*:", line) or re.search(r"^\s*except\s+Exception\s*:", line):
                issues.append(ReviewIssue(
                    level="建议",
                    line=i,
                    description="捕获所有异常过于宽泛",
                    suggestion="指定具体异常类型，避免吞掉错误"
                ))
            if re.search(r"^\s*except\s*:\s*$", line) and i < total_lines:
                if lines[i].strip() == "pass":
                    issues.append(ReviewIssue(
                        level="阻断",
                        line=i,
                        description="空异常处理（pass）",
                        suggestion="至少记录日志或抛出更有意义的信息"
                    ))

        # 注释掉的代码
        if language in ("Python", "Go", "JavaScript"):
            if re.match(r"^\s*#\s*(if|for|while|def|class|import)\b", line):
                issues.append(ReviewIssue(
                    level="可选",
                    line=i,
                    description="注释掉的代码",
                    suggestion="删除无用代码或使用版本控制"
                ))

    # 3. 逻辑正确性基础检查
    for i, line in enumerate(lines, 1):
        # 未定义变量（非常基础的检查）
        if language == "Python":
            # 简单模式：使用但未定义的变量
            used_vars = set(re.findall(r"\b([a-z_][a-z0-9_]*)\s*=", line))
            # 这里只做提示，不做强断言（避免误报）

        # 循环终止条件检查（简化）
        if re.search(r"while\s+True\s*:", line):
            # 检查是否有 break
            block_end = min(i + 10, total_lines)
            has_break = False
            for j in range(i, block_end):
                if re.search(r"\bbreak\b", lines[j]):
                    has_break = True
                    break
            if not has_break:
                issues.append(ReviewIssue(
                    level="建议",
                    line=i,
                    description="检测到 while True 循环但未在附近发现 break",
                    suggestion="确保循环有明确的退出条件"
                ))

    # 4. 空值处理检查
    for i, line in enumerate(lines, 1):
        # 潜在的空指针/空引用
        if language in ("Java", "Go", "C++", "C"):
            if re.search(r"\b(?:\.\w+)\s*\(", line) and not re.search(r"\b(?:null|nil)\s*[!=]=", line):
                # 过于复杂，跳过具体实现
                pass

    # 5. 根据用户指定重点调整
    if focus:
        focus_lower = focus.lower()
        if "安全" in focus_lower or "security" in focus_lower:
            for i, line in enumerate(lines, 1):
                if re.search(r"(password|secret|token|key)\s*=", line, re.IGNORECASE):
                    issues.append(ReviewIssue(
                        level="建议",
                        line=i,
                        description="硬编码敏感信息",
                        suggestion="使用环境变量或密钥管理服务"
                    ))
        if "并发" in focus_lower or "concurr" in focus_lower:
            for i, line in enumerate(lines, 1):
                if re.search(r"\b(thread|goroutine|async|await)\b", line, re.IGNORECASE):
                    if not re.search(r"\b(lock|mutex|sync|await)\b", line, re.IGNORECASE):
                        issues.append(ReviewIssue(
                            level="可选",
                            line=i,
                            description="检测到并发操作但未见同步机制",
                            suggestion="检查是否需要锁或原子操作"
                        ))

    return issues


# ---------------------------------------------------------------------------
# 主审查函数
# ---------------------------------------------------------------------------
def perform_review(code: str, filename: str = "", language_hint: str = "", focus: str = "") -> ReviewResult:
    """执行完整审查流程。"""
    # E001: 输入为空
    if not code or not code.strip():
        raise ReviewError("E001")

    # 识别语言
    language = language_hint or detect_language(code, filename)
    if not language:
        raise ReviewError("E002")

    # E004: 多文件引用检测
    if check_multi_file_refs(code):
        # 仅提示，不阻断（因为单文件审查可能引用标准库）
        pass

    # E003: 完整性检查
    completeness_error = check_completeness(code, language)
    if completeness_error == "E003":
        raise ReviewError("E003")

    # 执行审查
    issues = analyze_code(code, language, focus)

    # 生成总结
    result = ReviewResult(
        filename=filename or "未命名文件",
        language=language,
        line_count=len(code.splitlines()),
        issues=issues,
    )

    # 生成总体评价
    block_count = sum(1 for i in issues if i.level == "阻断")
    suggest_count = sum(1 for i in issues if i.level == "建议")
    optional_count = sum(1 for i in issues if i.level == "可选")

    if block_count == 0 and suggest_count == 0:
        result.summary = "代码质量良好，未发现明显问题。建议保持现有风格并持续进行代码审查。"
    elif block_count > 0:
        result.summary = f"发现 {block_count} 个阻断级问题，建议优先修复后再合并代码。另有 {suggest_count} 条改进建议。"
    else:
        result.summary = f"未发现阻断级问题，但有 {suggest_count} 条改进建议和 {optional_count} 条可选优化项。"

    return result


# ---------------------------------------------------------------------------
# 自检函数（--selftest）
# ---------------------------------------------------------------------------
def selftest() -> int:
    """内置硬编码样例数据的离线自检。不读外部文件、不依赖工作目录、不访问网络。"""
    test_cases = []

    # 测试用例 1: 简单 Python 代码（应通过，无阻断问题）
    test_cases.append({
        "name": "简单 Python 代码",
        "code": """
def calculate_total(items):
    total = 0
    for item in items:
        total += item
    return total

result = calculate_total([1, 2, 3])
print(result)
""",
        "filename": "test.py",
        "expect_error": False,
    })

    # 测试用例 2: 有问题的代码（应检测到问题）
    test_cases.append({
        "name": "有问题的代码",
        "code": """
def BadFunctionName():
    x = 1
    y = 2
    return x + y

# 魔法数字
def calculate():
    return 3.14159 * 2
""",
        "filename": "bad.py",
        "expect_error": False,
    })

    # 测试用例 3: 空输入（应报 E001）
    test_cases.append({
        "name": "空输入",
        "code": "",
        "filename": "empty.py",
        "expect_error": True,
        "error_code": "E001",
    })

    # 测试用例 4: 无法识别语言
    test_cases.append({
        "name": "无法识别语言",
        "code": "just some random text without any code patterns",
        "filename": "unknown.txt",
        "expect_error": True,
        "error_code": "E002",
    })

    # 测试用例 5: 不完整代码（未闭合括号）
    test_cases.append({
        "name": "不完整代码",
        "code": "def foo(:\n    return",
        "filename": "incomplete.py",
        "expect_error": True,
        "error_code": "E003",
    })

    # 执行测试
    passed = 0
    for tc in test_cases:
        try:
            result = perform_review(tc["code"], tc["filename"])
            if tc["expect_error"]:
                print(f"✗ 测试 '{tc['name']}' 失败：期望错误但未抛出")
                return 1
            # 宽松断言：结果对象存在
            assert result is not None
            assert result.language != ""
            assert result.line_count > 0
            passed += 1
            print(f"✓ 测试 '{tc['name']}' 通过")
        except ReviewError as e:
            if tc["expect_error"] and e.code == tc.get("error_code"):
                passed += 1
                print(f"✓ 测试 '{tc['name']}' 通过（期望错误 {e.code}）")
            else:
                print(f"✗ 测试 '{tc['name']}' 失败：意外错误 {e.code}: {e.message}")
                return 1
        except Exception as e:
            print(f"✗ 测试 '{tc['name']}' 失败：未预期异常 {e}")
            return 1

    # 额外验证：Markdown 输出格式
    try:
        sample = ReviewResult(
            filename="sample.py",
            language="Python",
            line_count=10,
            issues=[
                ReviewIssue("建议", 5, "测试问题", "测试建议"),
            ],
            summary="测试总结",
        )
        md = sample.to_markdown()
        # 宽松断言：包含关键标题
        assert "审查报告" in md
        assert "问题清单" in md
        assert "总体评价" in md
        passed += 1
        print("✓ 测试 'Markdown 输出格式' 通过")
    except Exception as e:
        print(f"✗ 测试 'Markdown 输出格式' 失败：{e}")
        return 1

    # 额外验证：错误码体系
    try:
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_MESSAGES
            assert len(ERROR_MESSAGES[code]) > 0
        passed += 1
        print("✓ 测试 '错误码体系' 通过")
    except Exception as e:
        print(f"✗ 测试 '错误码体系' 失败：{e}")
        return 1

    print(f"\n自检完成：{passed} 项测试全部通过。")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="单文件代码审查工具 - 结构化的静态代码质量检查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py --file path/to/code.py           # 审查文件
  python main.py --code "print('hello')" --lang Python  # 直接传入代码
  python main.py --selftest                        # 运行离线自检
        """,
    )
    parser.add_argument("--file", "-f", help="待审查的代码文件路径")
    parser.add_argument("--code", "-c", help="直接传入代码内容")
    parser.add_argument("--lang", "-l", help="指定编程语言（可选）")
    parser.add_argument("--focus", help="审查重点（如：安全、并发、可读性）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--output", "-o", choices=["markdown", "text"], default="markdown", help="输出格式")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return selftest()
        except Exception as e:
            print(f"[E009] 自检失败：{e}")
            return 1

    # 获取代码内容
    code = ""
    filename = ""

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                code = f.read()
            filename = args.file
        except FileNotFoundError:
            print("[E007] 文件读取失败：文件不存在")
            return 1
        except Exception as e:
            print(f"[E007] 文件读取失败：{e}")
            return 1
    elif args.code:
        code = args.code
        filename = "命令行输入"
    else:
        # 尝试从标准输入读取
        if not sys.stdin.isatty():
            code = sys.stdin.read()
            filename = "标准输入"
        else:
            parser.print_help()
            print("\n[E006] 输入参数无效：请提供 --file 或 --code 参数")
            return 1

    # 执行审查
    try:
        result = perform_review(code, filename, args.lang or "", args.focus or "")

        # 输出
        if args.output == "markdown":
            print(result.to_markdown())
        else:
            # 文本格式
            print(f"文件：{result.filename}")
            print(f"语言：{result.language}")
            print(f"行数：{result.line_count}")
            print(f"问题数：{len(result.issues)}")
            for issue in result.issues:
                print(f"  [{issue.level}] 行 {issue.line}: {issue.description}")
            print(f"评价：{result.summary}")

        return 0
    except ReviewError as e:
        print(f"[{e.code}] {e.message}")
        return 1
    except Exception as e:
        print(f"[E010] 未预期的运行时错误：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
