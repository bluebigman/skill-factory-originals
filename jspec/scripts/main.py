#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jspec - 前端测试 BDD 断言辅助工具（独立实现）

本脚本依据功能规格独立编写，提供以下核心能力：
  C1: 测试用例结构解析（describe/it/expect 层级提取）
  C2: 断言表达式识别（常见断言方法及参数提取）
  C3: 测试结果汇总（通过/失败/跳过统计）
  C4: 测试用例生成建议（BDD 风格用例骨架）
  C5: 批量文件扫描（目录下 .test.js/.spec.js 文件解析）

仅做静态文本分析，不执行测试代码，不修改用户源码。
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 参数错误
# E002: 输入内容为空
# E003: 无法解析的测试代码
# E004: 目录不存在
# E005: 目录不可读
# E006: 文件读取失败
# E007: JSON 序列化失败
# E008: 内部逻辑错误
# E009: 不支持的操作
# E010: 未知错误
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class AssertionInfo:
    """断言表达式信息"""
    method: str = ""          # 断言方法名，如 toBe
    args: List[str] = field(default_factory=list)  # 参数列表（字符串形式）
    line: int = 0             # 所在行号
    source: str = ""          # 原始代码片段


@dataclass
class TestCase:
    """单个测试用例（it）"""
    name: str = ""
    line: int = 0
    assertions: List[AssertionInfo] = field(default_factory=list)


@dataclass
class TestSuite:
    """测试套件（describe）"""
    name: str = ""
    line: int = 0
    cases: List[TestCase] = field(default_factory=list)


@dataclass
class ParseResult:
    """解析结果"""
    suites: List[TestSuite] = field(default_factory=list)
    total_cases: int = 0
    total_assertions: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class TestSummary:
    """测试结果汇总"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 常见断言方法列表
ASSERTION_METHODS = [
    "toBe", "toEqual", "toStrictEqual", "toBeTruthy", "toBeFalsy",
    "toBeNull", "toBeUndefined", "toBeDefined", "toBeNaN",
    "toBeGreaterThan", "toBeGreaterThanOrEqual",
    "toBeLessThan", "toBeLessThanOrEqual",
    "toContain", "toContainEqual", "toHaveLength",
    "toMatch", "toMatchObject", "toHaveProperty",
    "toThrow", "toThrowError", "toBeInstanceOf",
    "toBeCloseTo", "toHaveBeenCalled", "toHaveBeenCalledTimes",
    "toHaveBeenCalledWith", "toHaveBeenLastCalledWith",
    "toHaveReturned", "toHaveReturnedTimes",
    "expect",  # expect 本身也识别
]

# describe/it 匹配模式
DESCRIBE_PATTERN = re.compile(
    r'describe\s*\(\s*["\']([^"\']+)["\']\s*,\s*\(?\s*\)?\s*=>\s*\{',
    re.MULTILINE
)
IT_PATTERN = re.compile(
    r'\bit\s*\(\s*["\']([^"\']+)["\']\s*,\s*\(?\s*\)?\s*=>\s*\{',
    re.MULTILINE
)

# 断言匹配模式：expect(...).method(args)
EXPECT_PATTERN = re.compile(
    r'expect\s*\(\s*(.*?)\s*\)\s*\.\s*([a-zA-Z]+)\s*\(\s*(.*?)\s*\)',
    re.DOTALL
)

# 测试结果统计正则（兼容 Jest/Mocha 常见输出）
# 示例: "Tests: 10 passed, 2 failed, 1 skipped"
TEST_STATS_PATTERN = re.compile(
    r'Tests?\s*:\s*(\d+)\s+passed\s*,\s*(\d+)\s+failed\s*(?:,\s*(\d+)\s+skipped)?',
    re.IGNORECASE
)

# 失败详情行匹配（常见格式: "✗ 用例名" 或 "● 用例名"）
FAILURE_PATTERN = re.compile(
    r'[✗●×]?\s*([^\n]+?)\s*(?:\(|$)',
    re.MULTILINE
)

# 测试文件后缀
TEST_FILE_SUFFIXES = (".test.js", ".spec.js", ".test.jsx", ".spec.jsx", ".test.ts", ".spec.ts")


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------

class JSpecParser:
    """BDD 测试代码解析器（静态分析）"""

    def __init__(self) -> None:
        self.result = ParseResult()

    def parse(self, code: str) -> ParseResult:
        """解析测试代码，提取 describe/it/expect 结构

        参数:
            code: JavaScript 测试代码字符串

        返回:
            ParseResult 对象，包含解析出的结构信息

        错误码:
            E002: 输入为空
            E003: 无法解析出任何测试结构
        """
        if not code or not code.strip():
            self.result.errors.append("E002: 输入内容为空")
            return self.result

        lines = code.splitlines()
        self._parse_describes(code, lines)
        self._parse_cases(code, lines)
        self._parse_assertions(code, lines)

        # 统计
        for suite in self.result.suites:
            self.result.total_cases += len(suite.cases)
            for case in suite.cases:
                self.result.total_assertions += len(case.assertions)

        if not self.result.suites and not self.result.total_cases:
            self.result.errors.append("E003: 无法解析出任何测试结构")

        return self.result

    def _parse_describes(self, code: str, lines: List[str]) -> None:
        """解析 describe 块"""
        for match in DESCRIBE_PATTERN.finditer(code):
            name = match.group(1)
            # 计算行号
            line_no = code[:match.start()].count("\n") + 1
            suite = TestSuite(name=name, line=line_no)
            self.result.suites.append(suite)

    def _parse_cases(self, code: str, lines: List[str]) -> None:
        """解析 it 用例，并关联到最近的 describe"""
        for match in IT_PATTERN.finditer(code):
            name = match.group(1)
            line_no = code[:match.start()].count("\n") + 1
            case = TestCase(name=name, line=line_no)

            # 关联到最近的 describe（行号小于当前行号且最接近）
            target_suite = None
            for suite in self.result.suites:
                if suite.line < line_no:
                    if target_suite is None or suite.line > target_suite.line:
                        target_suite = suite

            if target_suite:
                target_suite.cases.append(case)
            else:
                # 没有 describe 时，创建隐式顶层 suite
                implicit = TestSuite(name="<顶层>", line=1)
                implicit.cases.append(case)
                self.result.suites.append(implicit)

    def _parse_assertions(self, code: str, lines: List[str]) -> None:
        """解析 expect 断言，并关联到最近的用例"""
        for match in EXPECT_PATTERN.finditer(code):
            target_expr = match.group(1).strip()
            method = match.group(2).strip()
            args_str = match.group(3).strip()

            # 只识别已知断言方法
            if method not in ASSERTION_METHODS:
                continue

            line_no = code[:match.start()].count("\n") + 1
            assertion = AssertionInfo(
                method=method,
                args=[args_str] if args_str else [],
                line=line_no,
                source=match.group(0).strip()
            )

            # 关联到最近的用例
            target_case = None
            for suite in self.result.suites:
                for case in suite.cases:
                    if case.line < line_no:
                        if target_case is None or case.line > target_case.line:
                            target_case = case

            if target_case:
                target_case.assertions.append(assertion)


# ---------------------------------------------------------------------------
# 测试结果解析
# ---------------------------------------------------------------------------

def parse_test_result(log_text: str) -> TestSummary:
    """从测试运行日志中解析统计信息

    参数:
        log_text: 测试运行日志文本

    返回:
        TestSummary 对象

    错误码:
        E002: 输入为空
    """
    summary = TestSummary()

    if not log_text or not log_text.strip():
        summary.failures.append({"error": "E002: 输入内容为空"})
        return summary

    # 匹配统计行
    match = TEST_STATS_PATTERN.search(log_text)
    if match:
        summary.total = int(match.group(1)) + int(match.group(2))
        summary.passed = int(match.group(1))
        summary.failed = int(match.group(2))
        summary.skipped = int(match.group(3)) if match.group(3) else 0

    # 提取失败详情（简单启发式）
    for line in log_text.splitlines():
        stripped = line.strip()
        # 跳过统计行和空行
        if not stripped or "Tests:" in stripped or "Test Suites:" in stripped:
            continue
        # 失败用例通常包含 ✗、●、× 等符号
        if any(marker in stripped for marker in ["✗", "●", "×", "FAIL"]):
            # 提取用例名
            fail_match = FAILURE_PATTERN.search(stripped)
            if fail_match:
                name = fail_match.group(1).strip()
                if name and len(name) < 100:  # 避免过长的堆栈信息
                    summary.failures.append({"name": name, "raw": stripped[:200]})

    return summary


# ---------------------------------------------------------------------------
# 用例生成建议
# ---------------------------------------------------------------------------

def generate_test_suggestions(func_signature: str) -> List[str]:
    """根据函数签名生成 BDD 风格测试用例建议

    参数:
        func_signature: 函数签名描述，如 "function sum(a, b)"

    返回:
        建议用例列表

    错误码:
        E002: 输入为空
    """
    if not func_signature or not func_signature.strip():
        return ["E002: 函数签名不能为空"]

    # 尝试提取函数名
    name_match = re.search(r'(?:function\s+)?([a-zA-Z_$][\w$]*)\s*\(', func_signature)
    func_name = name_match.group(1) if name_match else "targetFunction"

    # 提取参数列表
    args_match = re.search(r'\(([^)]*)\)', func_signature)
    args_str = args_match.group(1) if args_match else ""
    args = [a.strip() for a in args_str.split(",") if a.strip()]
    arg_names = args if args else ["input"]

    suggestions = [
        f"describe('{func_name}', () => {{",
        f"  it('应处理正常输入', () => {{",
        f"    const result = {func_name}({', '.join(arg_names)});",
        f"    expect(result).toBeDefined();",
        f"  }});",
        "",
        f"  it('应处理边界值', () => {{",
        f"    const result = {func_name}(null);",
        f"    expect(result).toBeDefined();",
        f"  }});",
        "",
        f"  it('应处理空参数', () => {{",
        f"    expect(() => {func_name}()).not.toThrow();",
        f"  }});",
        "",
    ]

    # 如果有参数，添加更多建议
    if len(arg_names) >= 2:
        suggestions.extend([
            f"  it('应验证多个参数组合', () => {{",
            f"    const result = {func_name}({', '.join(arg_names[:2])});",
            f"    expect(result).toBeTruthy();",
            f"  }});",
            "",
        ])

    suggestions.extend([
        f"  it('应处理异常输入', () => {{",
        f"    expect(() => {func_name}(undefined)).not.toThrow();",
        f"  }});",
        "",
        f"  it('应返回预期类型', () => {{",
        f"    const result = {func_name}({', '.join(arg_names[:1]) if arg_names else 'null'});",
        f"    expect(typeof result).toBe('object');",
        f"  }});",
        "});",
    ])

    return suggestions


# ---------------------------------------------------------------------------
# 批量文件扫描
# ---------------------------------------------------------------------------

def scan_test_directory(directory: str) -> Dict[str, List[Dict[str, Any]]]:
    """扫描目录下所有测试文件并解析

    参数:
        directory: 目录路径

    返回:
        字典，键为文件路径，值为解析结果列表

    错误码:
        E004: 目录不存在
        E005: 目录不可读
        E006: 文件读取失败
    """
    results: Dict[str, List[Dict[str, Any]]] = {}

    if not os.path.exists(directory):
        raise ValueError("E004: 目录不存在")

    if not os.path.isdir(directory):
        raise ValueError("E005: 不是有效目录")

    if not os.access(directory, os.R_OK):
        raise ValueError("E005: 目录不可读")

    for root, dirs, files in os.walk(directory):
        # 跳过 node_modules 和 .git
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist", "build")]

        for filename in files:
            if filename.endswith(TEST_FILE_SUFFIXES):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()

                    parser = JSpecParser()
                    parse_result = parser.parse(code)

                    file_data = []
                    for suite in parse_result.suites:
                        suite_data = {
                            "suite": suite.name,
                            "line": suite.line,
                            "cases": []
                        }
                        for case in suite.cases:
                            case_data = {
                                "name": case.name,
                                "line": case.line,
                                "assertions": [
                                    {"method": a.method, "args": a.args, "line": a.line}
                                    for a in case.assertions
                                ]
                            }
                            suite_data["cases"].append(case_data)
                        file_data.append(suite_data)

                    results[filepath] = file_data

                except IOError:
                    results[filepath] = [{"error": "E006: 文件读取失败"}]

    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_parse_result(parse_result: ParseResult) -> str:
    """将解析结果格式化为可读文本"""
    if not parse_result.suites:
        return "未解析到任何测试结构"

    lines = []
    lines.append(f"解析结果（共 {parse_result.total_cases} 个用例，{parse_result.total_assertions} 个断言）")
    lines.append("=" * 50)

    for suite in parse_result.suites:
        lines.append(f"\n📦 {suite.name} (行 {suite.line})")
        if not suite.cases:
            lines.append("  (空套件)")
            continue

        for case in suite.cases:
            lines.append(f"  ├─ ✅ {case.name} (行 {case.line})")
            if case.assertions:
                for assertion in case.assertions:
                    args_str = ", ".join(assertion.args) if assertion.args else ""
                    lines.append(f"     └─ expect(...).{assertion.method}({args_str})")

    return "\n".join(lines)


def format_summary(summary: TestSummary) -> str:
    """格式化测试结果汇总"""
    lines = []
    lines.append("测试结果汇总")
    lines.append("=" * 40)
    lines.append(f"总计: {summary.total}")
    lines.append(f"通过: {summary.passed}")
    lines.append(f"失败: {summary.failed}")
    lines.append(f"跳过: {summary.skipped}")
    lines.append(f"通过率: {summary.passed / summary.total * 100:.1f}%" if summary.total > 0 else "通过率: N/A")

    if summary.failures:
        lines.append("\n失败详情:")
        for failure in summary.failures[:10]:  # 最多显示10条
            lines.append(f"  - {failure.get('name', '未知')}")
            if failure.get('raw'):
                lines.append(f"    {failure['raw'][:100]}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="jspec - 前端测试 BDD 断言辅助工具",
        epilog="示例: python main.py --parse test.js 或 python main.py --scan ./tests"
    )
    parser.add_argument("--parse", metavar="FILE", help="解析单个测试文件")
    parser.add_argument("--scan", metavar="DIR", help="扫描目录下的测试文件")
    parser.add_argument("--log", metavar="FILE", help="解析测试日志文件")
    parser.add_argument("--suggest", metavar="SIGNATURE", help="生成测试用例建议")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    return parser


def run_selftest() -> int:
    """内置自检函数，使用硬编码样例数据验证核心逻辑

    返回:
        0 表示通过，非 0 表示失败
    """
    print("🔍 运行自检...")

    # 测试样例数据
    sample_code = """
describe('计算器', () => {
  it('加法', () => {
    expect(add(1, 2)).toBe(3);
    expect(add(-1, 1)).toBe(0);
  });

  it('减法', () => {
    expect(subtract(5, 3)).toBe(2);
  });
});

describe('字符串工具', () => {
  it('拼接', () => {
    expect(concat('a', 'b')).toBe('ab');
    expect(concat('', '')).toBe('');
  });

  it('长度', () => {
    expect(strlen('hello')).toBeGreaterThan(3);
  });
});
"""

    sample_log = """
Test Suites: 2 passed, 2 total
Tests: 4 passed, 1 failed, 1 skipped
✗ 减法 应处理负数
● 计算器 > 加法
"""

    # --- C1/C2: 结构解析与断言识别 ---
    parser = JSpecParser()
    result = parser.parse(sample_code)

    assert result.suites, "E003: 应解析出 describe 套件"
    assert len(result.suites) == 2, f"应解析出 2 个套件，实际 {len(result.suites)}"
    assert result.total_cases == 4, f"应解析出 4 个用例，实际 {result.total_cases}"
    assert result.total_assertions >= 5, f"应至少解析出 5 个断言，实际 {result.total_assertions}"

    # 验证套件名称
    suite_names = [s.name for s in result.suites]
    assert "计算器" in suite_names, "应包含 '计算器' 套件"
    assert "字符串工具" in suite_names, "应包含 '字符串工具' 套件"

    # 验证断言方法识别
    all_methods = set()
    for suite in result.suites:
        for case in suite.cases:
            for assertion in case.assertions:
                all_methods.add(assertion.method)

    assert "toBe" in all_methods, "应识别 toBe 断言"
    assert "toBeGreaterThan" in all_methods, "应识别 toBeGreaterThan 断言"

    # --- C3: 测试结果汇总 ---
    summary = parse_test_result(sample_log)
    assert summary.total == 5, f"总计应为 5，实际 {summary.total}"
    assert summary.passed == 4, f"通过应为 4，实际 {summary.passed}"
    assert summary.failed == 1, f"失败应为 1，实际 {summary.failed}"
    assert summary.skipped == 1, f"跳过应为 1，实际 {summary.skipped}"
    assert len(summary.failures) > 0, "应提取到失败详情"

    # --- C4: 用例生成建议 ---
    suggestions = generate_test_suggestions("function calculate(a, b)")
    assert len(suggestions) >= 5, f"应生成至少 5 条建议，实际 {len(suggestions)}"
    assert any("describe" in s for s in suggestions), "建议应包含 describe"
    assert any("it" in s for s in suggestions), "建议应包含 it"

    # --- 宽松阈值验证（不依赖精确值） ---
    # 验证套件数量在合理范围（1-10）
    assert 1 <= len(result.suites) <= 10, "套件数量应在合理范围"
    # 验证用例数量在合理范围（1-20）
    assert 1 <= result.total_cases <= 20, "用例数量应在合理范围"
    # 验证断言数量在合理范围（1-50）
    assert 1 <= result.total_assertions <= 50, "断言数量应在合理范围"
    # 验证通过率在合理范围（0-100%）
    if summary.total > 0:
        pass_rate = summary.passed / summary.total * 100
        assert 0 <= pass_rate <= 100, "通过率应在 0-100% 范围"

    # --- C5: 批量扫描（使用临时目录） ---
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建临时测试文件
        test_file = os.path.join(tmpdir, "sample.test.js")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(sample_code)

        scan_results = scan_test_directory(tmpdir)
        assert test_file in scan_results, "应扫描到测试文件"
        assert len(scan_results[test_file]) >= 1, "应解析出至少一个套件"

    print("✅ 所有自检通过！")
    return 0


def main() -> int:
    """主入口函数"""
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args()

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

    # 参数互斥检查
    action_count = sum([
        bool(args.parse),
        bool(args.scan),
        bool(args.log),
        bool(args.suggest),
    ])
    if action_count == 0:
        arg_parser.print_help()
        return 0
    if action_count > 1:
        print("错误: E001 - 只能指定一个操作参数（--parse/--scan/--log/--suggest）")
        return 1

    try:
        # 解析单个文件
        if args.parse:
            with open(args.parse, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            parser = JSpecParser()
            result = parser.parse(code)

            if args.json:
                data = {
                    "total_cases": result.total_cases,
                    "total_assertions": result.total_assertions,
                    "suites": [
                        {
                            "name": s.name,
                            "line": s.line,
                            "cases": [
                                {
                                    "name": c.name,
                                    "line": c.line,
                                    "assertions": [
                                        {"method": a.method, "args": a.args}
                                        for a in c.assertions
                                    ]
                                }
                                for c in s.cases
                            ]
                        }
                        for s in result.suites
                    ],
                    "errors": result.errors
                }
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(format_parse_result(result))
                if result.errors:
                    print("\n⚠️ 警告:", "; ".join(result.errors))

        # 目录扫描
        elif args.scan:
            scan_results = scan_test_directory(args.scan)

            if args.json:
                print(json.dumps(scan_results, ensure_ascii=False, indent=2))
            else:
                total_files = len(scan_results)
                total_suites = sum(len(suites) for suites in scan_results.values())
                total_cases = sum(
                    len(case) for suites in scan_results.values() for case in suites
                )
                print(f"扫描完成: {total_files} 个文件, {total_suites} 个套件, {total_cases} 个用例")
                for filepath, suites in scan_results.items():
                    print(f"\n📄 {filepath}")
                    for suite in suites:
                        if "error" in suite:
                            print(f"  ⚠️ {suite['error']}")
                        else:
                            print(f"  📦 {suite['suite']} ({len(suite['cases'])} 个用例)")

        # 日志解析
        elif args.log:
            with open(args.log, "r", encoding="utf-8", errors="ignore") as f:
                log_text = f.read()
            summary = parse_test_result(log_text)

            if args.json:
                print(json.dumps({
                    "total": summary.total,
                    "passed": summary.passed,
                    "failed": summary.failed,
                    "skipped": summary.skipped,
                    "failures": summary.failures
                }, ensure_ascii=False, indent=2))
            else:
                print(format_summary(summary))

        # 用例生成建议
        elif args.suggest:
            suggestions = generate_test_suggestions(args.suggest)

            if args.json:
                print(json.dumps({"suggestions": suggestions}, ensure_ascii=False, indent=2))
            else:
                print("\n".join(suggestions))

    except FileNotFoundError:
        print("错误: E006 - 文件不存在")
        return 1
    except PermissionError:
        print("错误: E005 - 权限不足")
        return 1
    except ValueError as e:
        print(f"错误: {e}")
        return 1
    except json.JSONEncodeError:
        print("错误: E007 - JSON 序列化失败")
        return 1
    except Exception as e:
        print(f"错误: E010 - 未知错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
