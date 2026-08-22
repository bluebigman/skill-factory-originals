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
import concurrent.futures
import json
import os
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
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

# 完整断言方法列表（修复截断问题，覆盖 Jest/Vitest 全部常用匹配器）
ASSERTION_METHODS = [
    # 基础匹配器
    "toBe", "toEqual", "toStrictEqual", "toBeTruthy", "toBeFalsy",
    "toBeNull", "toBeUndefined", "toBeDefined", "toBeNaN",
    "toBeGreaterThan", "toBeGreaterThanOrEqual",
    "toBeLessThan", "toBeLessThanOrEqual",
    "toContain", "toContainEqual", "toHaveLength",
    "toMatch", "toMatchObject", "toHaveProperty",
    "toThrow", "toThrowError", "toBeInstanceOf",
    "toBeCloseTo",
    
    # Mock 函数匹配器
    "toHaveBeenCalled", "toHaveBeenCalledTimes",
    "toHaveBeenCalledWith", "toHaveBeenLastCalledWith",
    "toHaveBeenNthCalledWith", "toHaveBeenCalledOnce",
    "toHaveBeenCalledExactlyOnceWith",
    "toHaveReturned", "toHaveReturnedTimes",
    "toHaveReturnedWith", "toHaveLastReturnedWith",
    "toHaveNthReturnedWith",
    
    # 异步匹配器
    "toHaveResolved", "toHaveResolvedTimes", "toHaveResolvedWith",
    "toHaveRejected", "toHaveRejectedTimes", "toHaveRejectedWith",
    "toHaveResolvedOnce", "toHaveRejectedOnce",
    "toHaveResolvedExactlyOnceWith", "toHaveRejectedExactlyOnceWith",
    "toHaveResolvedNthTimeWith", "toHaveRejectedNthTimeWith",
    "toHaveResolvedLastWith", "toHaveRejectedLastWith",
    
    # 扩展匹配器（Jest Extended / Vitest 扩展）
    "toSatisfy", "toSatisfyAll", "toSatisfyAny",
    "toInclude", "toIncludeEqual", "toStartWith", "toEndWith",
    "toBeEmpty", "toBeNonEmpty", "toBeArray", "toBeObject",
    "toBeString", "toBeNumber", "toBeBoolean", "toBeFunction",
    "toBeSymbol", "toBeBigInt", "toBeDate", "toBeRegExp",
    "toBeMap", "toBeSet", "toBeWeakMap", "toBeWeakSet",
    "toBePromise", "toBeIterable", "toBeAsyncIterable",
    "toBeGenerator", "toBeAsyncGenerator", "toBeClass",
    
    # 调用顺序匹配器
    "toHaveBeenCalledBefore", "toHaveBeenCalledAfter",
    "toHaveBeenCalledImmediatelyBefore", "toHaveBeenCalledImmediatelyAfter",
    
    # 精确匹配器
    "toHaveBeenCalledWithExactly", "toHaveBeenCalledTimesExactly",
    "toHaveReturnedTimesExactly", "toHaveReturnedWithExactly",
    "toHaveLastReturnedWithExactly", "toHaveNthReturnedWithExactly",
    "toHaveResolvedWithExactly", "toHaveRejectedWithExactly",
    "toHaveResolvedTimesExactly", "toHaveRejectedTimesExactly",
    "toHaveResolvedLastWithExactly", "toHaveRejectedLastWithExactly",
    "toHaveResolvedNthTimeWithExactly", "toHaveRejectedNthTimeWithExactly",
]

# describe/it 匹配模式（支持嵌套、异步、箭头函数等）
DESCRIBE_PATTERN = re.compile(
    r'describe\s*\(\s*["\']([^"\']+)["\']\s*,\s*(?:async\s*)?\(?\s*\)?\s*=>\s*\{',
    re.MULTILINE
)
IT_PATTERN = re.compile(
    r'\b(?:it|test)\s*\(\s*["\']([^"\']+)["\']\s*,\s*(?:async\s*)?\(?\s*\)?\s*=>\s*\{',
    re.MULTILINE
)

# 断言匹配模式：expect(...).method(args) - 支持多行和模板字符串
EXPECT_PATTERN = re.compile(
    r'expect\s*\(\s*(.*?)\s*\)\s*\.\s*([a-zA-Z]+)\s*\(\s*(.*?)\s*\)',
    re.DOTALL
)

# 测试结果统计正则（兼容 Jest/Mocha 常见输出）
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
TEST_FILE_SUFFIXES = (".test.js", ".spec.js", ".test.jsx", ".spec.jsx", ".test.ts", ".spec.ts", ".test.tsx", ".spec.tsx")


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
# 测试结果解析（C3 能力实现）
# ---------------------------------------------------------------------------

def parse_results(file_path: str) -> TestSummary:
    """从测试结果文件（JSON/XML）中解析统计信息

    参数:
        file_path: 测试结果文件路径（支持 JSON 和 XML 格式）

    返回:
        TestSummary 对象

    错误码:
        E002: 输入为空
        E006: 文件读取失败
        E009: 不支持的文件格式
    """
    summary = TestSummary()

    if not file_path:
        summary.failures.append({"error": "E002: 文件路径不能为空"})
        return summary

    if not os.path.exists(file_path):
        summary.failures.append({"error": "E006: 文件不存在"})
        return summary

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError:
        summary.failures.append({"error": "E006: 文件读取失败"})
        return summary

    if not content.strip():
        summary.failures.append({"error": "E002: 文件内容为空"})
        return summary

    # 根据文件扩展名选择解析方式
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".json":
            return _parse_json_results(content)
        elif ext == ".xml":
            return _parse_xml_results(content)
        else:
            # 尝试自动检测格式
            if content.lstrip().startswith("{"):
                return _parse_json_results(content)
            elif content.lstrip().startswith("<"):
                return _parse_xml_results(content)
            else:
                summary.failures.append({"error": "E009: 不支持的文件格式"})
                return summary
    except Exception as e:
        summary.failures.append({"error": f"E010: 解析失败: {str(e)}"})
        return summary


def _parse_json_results(content: str) -> TestSummary:
    """解析 JSON 格式的测试结果"""
    summary = TestSummary()
    data = json.loads(content)

    # 支持多种常见 JSON 格式
    if "numTotalTests" in data:  # Jest 格式
        summary.total = data.get("numTotalTests", 0)
        summary.passed = data.get("numPassedTests", 0)
        summary.failed = data.get("numFailedTests", 0)
        summary.skipped = data.get("numPendingTests", 0)
        # 提取失败详情
        for test in data.get("testResults", []):
            if test.get("status") == "failed":
                summary.failures.append({
                    "name": test.get("name", "未知"),
                    "raw": test.get("message", "")[:200]
                })
    elif "stats" in data:  # Mocha 格式
        stats = data["stats"]
        summary.total = stats.get("tests", 0)
        summary.passed = stats.get("passes", 0)
        summary.failed = stats.get("failures", 0)
        summary.skipped = stats.get("pending", 0)
        # 提取失败详情
        for test in data.get("failures", []):
            summary.failures.append({
                "name": test.get("fullTitle", "未知"),
                "raw": test.get("err", {}).get("message", "")[:200]
            })
    elif "total" in data:  # 通用格式
        summary.total = data.get("total", 0)
        summary.passed = data.get("passed", 0)
        summary.failed = data.get("failed", 0)
        summary.skipped = data.get("skipped", 0)
        for failure in data.get("failures", []):
            summary.failures.append(failure)
    else:
        # 尝试从 testResults 数组中统计
        test_results = data.get("testResults", [])
        for result in test_results:
            summary.total += 1
            status = result.get("status", "")
            if status == "passed":
                summary.passed += 1
            elif status == "failed":
                summary.failed += 1
                summary.failures.append({
                    "name": result.get("name", "未知"),
                    "raw": result.get("message", "")[:200]
                })
            elif status in ("pending", "skipped"):
                summary.skipped += 1

    return summary


def _parse_xml_results(content: str) -> TestSummary:
    """解析 XML 格式的测试结果（JUnit 格式）"""
    summary = TestSummary()

    root = ET.fromstring(content)

    # JUnit 格式
    if root.tag == "testsuite":
        summary.total = int(root.get("tests", 0))
        summary.failed = int(root.get("failures", 0)) + int(root.get("errors", 0))
        summary.skipped = int(root.get("skipped", 0))
        summary.passed = summary.total - summary.failed - summary.skipped

        # 提取失败详情
        for testcase in root.iter("testcase"):
            for failure in testcase.findall("failure"):
                summary.failures.append({
                    "name": testcase.get("name", "未知"),
                    "raw": failure.get("message", "")[:200]
                })
            for error in testcase.findall("error"):
                summary.failures.append({
                    "name": testcase.get("name", "未知"),
                    "raw": error.get("message", "")[:200]
                })

    return summary


def parse_test_result(log_text: str) -> TestSummary:
    """从测试运行日志中解析统计信息（兼容旧接口）

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
        stripped = line.strip
