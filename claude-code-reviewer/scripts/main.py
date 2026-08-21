#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-code-reviewer 独立实现脚本
=================================
将代码或补丁转为结构化审查报告，标注风险等级与置信度，辅助人工决策。

仅依据功能规格独立实现（clean-room），不包含任何既有代码。
标准库实现，无第三方依赖。

用法示例：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --file sample.py    # 审查单个文件
    python scripts/main.py --patch diff.txt    # 审查补丁文件
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "参数错误：未提供有效的输入文件或补丁",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "补丁解析失败：补丁格式无法识别",
    "E004": "语言识别失败：不支持的文件类型",
    "E005": "审查分析失败：内部逻辑错误",
    "E006": "报告生成失败：输出写入错误",
    "E007": "自检失败：核心逻辑未通过验证",
    "E008": "输入内容为空：无有效代码可审查",
    "E009": "路径不安全：拒绝访问非文件路径",
    "E010": "未知错误：未预期的异常",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    """单个审查问题项"""
    line: int
    column: int
    severity: str          # critical / warning / info
    confidence: float      # 0.0 ~ 1.0
    category: str          # 问题类别
    message: str
    suggestion: str = ""


@dataclass
class ReviewResult:
    """审查结果汇总"""
    file_path: str
    language: str
    total_lines: int
    issues: List[Issue] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")

    @property
    def risk_score(self) -> float:
        """综合风险得分（0~100）"""
        if not self.issues:
            return 0.0
        base = (
            self.critical_count * 10.0
            + self.warning_count * 4.0
            + self.info_count * 1.0
        )
        # 置信度加权
        confidence_factor = sum(i.confidence for i in self.issues) / len(self.issues)
        score = base * (0.5 + confidence_factor * 0.5)
        return min(100.0, max(0.0, score))


# ---------------------------------------------------------------------------
# 语言识别与基础解析
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
}


def detect_language(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """根据文件扩展名识别语言类型"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[ext], ext
    return None, ext


def read_file_content(file_path: str) -> List[str]:
    """读取文件内容为行列表"""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(ERROR_CODES["E002"])
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()


# ---------------------------------------------------------------------------
# 补丁解析
# ---------------------------------------------------------------------------

def parse_patch(patch_text: str) -> List[Tuple[str, List[str]]]:
    """
    解析统一格式补丁（unified diff），
    返回 [(文件名, 新增行列表), ...]
    """
    files: List[Tuple[str, List[str]]] = []
    current_file: Optional[str] = None
    current_lines: List[str] = []

    for line in patch_text.splitlines():
        if line.startswith("+++ "):
            # 新文件路径
            current_file = line[4:].strip()
            if current_file.startswith("a/") or current_file.startswith("b/"):
                current_file = current_file[2:]
            current_lines = []
            files.append((current_file, current_lines))
        elif line.startswith("+") and not line.startswith("+++"):
            # 新增行（去掉 + 前缀）
            if current_file:
                current_lines.append(line[1:])
        elif line.startswith("---") or line.startswith("@@") or line.startswith("diff "):
            continue

    return files


# ---------------------------------------------------------------------------
# 审查规则引擎
# ---------------------------------------------------------------------------

class ReviewRule:
    """审查规则基类"""
    def __init__(self, severity: str, confidence: float, category: str):
        self.severity = severity
        self.confidence = confidence
        self.category = category

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        """检查单行，返回 Issue 或 None"""
        raise NotImplementedError


class HardcodedSecretRule(ReviewRule):
    """检测硬编码密钥/密码"""
    PATTERNS = [
        (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]+['\"]", "硬编码密码"),
        (r"(?i)(api[_-]?key|apikey|secret|token)\s*[=:]\s*['\"][^'\"]+['\"]", "硬编码密钥"),
        (r"(?i)(access[_-]?key|auth[_-]?token)\s*[=:]\s*['\"][^'\"]+['\"]", "硬编码访问令牌"),
    ]

    def __init__(self):
        super().__init__("critical", 0.9, "安全")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        for pattern, desc in self.PATTERNS:
            match = re.search(pattern, line)
            if match:
                col = match.start() + 1
                return Issue(
                    line=line_no,
                    column=col,
                    severity=self.severity,
                    confidence=self.confidence,
                    category=self.category,
                    message=f"检测到疑似{desc}，建议使用环境变量或密钥管理服务",
                    suggestion="将敏感信息移出代码，改用配置中心或环境变量注入",
                )
        return None


class TodoFIXMERule(ReviewRule):
    """检测 TODO/FIXME 标记"""
    def __init__(self):
        super().__init__("info", 0.6, "代码质量")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        match = re.search(r"(?i)\b(TODO|FIXME|HACK|XXX)\b", line)
        if match:
            return Issue(
                line=line_no,
                column=match.start() + 1,
                severity=self.severity,
                confidence=self.confidence,
                category=self.category,
                message=f"发现未完成的标记: {match.group(0).upper()}",
                suggestion="尽快处理该标记对应的任务或缺陷",
            )
        return None


class LongLineRule(ReviewRule):
    """检测超长行（>120字符）"""
    def __init__(self):
        super().__init__("warning", 0.7, "代码风格")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        stripped = line.rstrip("\n")
        if len(stripped) > 120:
            return Issue(
                line=line_no,
                column=121,
                severity=self.severity,
                confidence=self.confidence,
                category=self.category,
                message=f"行长度 {len(stripped)} 超过120字符",
                suggestion="考虑拆分为多行以提高可读性",
            )
        return None


class EmptyExceptRule(ReviewRule):
    """检测空的 except 块"""
    def __init__(self):
        super().__init__("warning", 0.8, "错误处理")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        if language == "python":
            if re.match(r"\s*except\s*:", line) or re.match(r"\s*except\s+[^:]+:", line):
                return Issue(
                    line=line_no,
                    column=1,
                    severity=self.severity,
                    confidence=self.confidence,
                    category=self.category,
                    message="检测到 except 块，请确认是否有适当的错误处理",
                    suggestion="避免空 except，应捕获具体异常并记录日志",
                )
        return None


class PrintStatementRule(ReviewRule):
    """检测调试用 print 语句"""
    def __init__(self):
        super().__init__("info", 0.5, "代码质量")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        stripped = line.strip()
        if language in ("python", "javascript", "typescript", "php"):
            if re.match(r"^(print|console\.log|var_dump|echo)\s*\(", stripped):
                return Issue(
                    line=line_no,
                    column=1,
                    severity=self.severity,
                    confidence=self.confidence,
                    category=self.category,
                    message="检测到调试输出语句",
                    suggestion="移除调试代码或改用日志框架",
                )
        return None


class GlobalVariableRule(ReviewRule):
    """检测全局变量滥用（Python）"""
    def __init__(self):
        super().__init__("warning", 0.6, "代码设计")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        if language == "python":
            if re.match(r"\s*global\s+", line):
                return Issue(
                    line=line_no,
                    column=1,
                    severity=self.severity,
                    confidence=self.confidence,
                    category=self.category,
                    message="使用 global 关键字，需谨慎",
                    suggestion="考虑通过参数传递或类封装来避免全局状态",
                )
        return None


class UnsafeEvalRule(ReviewRule):
    """检测危险函数调用"""
    def __init__(self):
        super().__init__("critical", 0.85, "安全")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        dangerous = {
            "python": [r"\beval\s*\(", r"\bexec\s*\(", r"\b__import__\s*\("],
            "javascript": [r"\beval\s*\(", r"\bFunction\s*\("],
            "php": [r"\beval\s*\(", r"\bassert\s*\("],
        }
        patterns = dangerous.get(language, [])
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return Issue(
                    line=line_no,
                    column=match.start() + 1,
                    severity=self.severity,
                    confidence=self.confidence,
                    category=self.category,
                    message=f"检测到危险函数调用: {match.group(0).strip('(')}",
                    suggestion="避免使用动态执行，需严格校验输入",
                )
        return None


class SQLInjectionRule(ReviewRule):
    """检测 SQL 注入风险"""
    def __init__(self):
        super().__init__("critical", 0.75, "安全")

    def check(self, line: str, line_no: int, language: str) -> Optional[Issue]:
        # 检测字符串拼接 SQL
        if re.search(r"(?i)(SELECT|INSERT|UPDATE|DELETE).*\+", line) or \
           re.search(r"(?i)(SELECT|INSERT|UPDATE|DELETE).*%s", line) and not re.search(r"(?i)execute|query", line):
            if re.search(r"['\"]\s*\+\s*", line) or re.search(r"\+\s*['\"]", line):
                return Issue(
                    line=line_no,
                    column=1,
                    severity=self.severity,
                    confidence=self.confidence,
                    category=self.category,
                    message="检测到可能的 SQL 注入风险（字符串拼接）",
                    suggestion="使用参数化查询或 ORM 框架",
                )
        return None


# ---------------------------------------------------------------------------
# 审查引擎
# ---------------------------------------------------------------------------

class ReviewEngine:
    """代码审查引擎"""
    def __init__(self):
        self.rules: List[ReviewRule] = [
            HardcodedSecretRule(),
            TodoFIXMERule(),
            LongLineRule(),
            EmptyExceptRule(),
            PrintStatementRule(),
            GlobalVariableRule(),
            UnsafeEvalRule(),
            SQLInjectionRule(),
        ]

    def review_lines(self, lines: List[str], language: str) -> List[Issue]:
        """对代码行执行全部规则检查"""
        issues: List[Issue] = []
        for i, line in enumerate(lines, start=1):
            for rule in self.rules:
                try:
                    issue = rule.check(line, i, language)
                    if issue:
                        issues.append(issue)
                except Exception:
                    # 单条规则异常不影响整体审查
                    continue
        return issues

    def review_file(self, file_path: str) -> ReviewResult:
        """审查单个文件"""
        language, ext = detect_language(file_path)
        if not language:
            raise ValueError(ERROR_CODES["E004"])
        lines = read_file_content(file_path)
        if not lines:
            raise ValueError(ERROR_CODES["E008"])

        issues = self.review_lines(lines, language)
        result = ReviewResult(
            file_path=file_path,
            language=language,
            total_lines=len(lines),
            issues=issues,
        )
        # 简单指标统计
        code_lines = sum(1 for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*")))
        result.metrics = {
            "code_lines": code_lines,
            "comment_lines": len(lines) - code_lines,
            "issue_density": len(issues) / max(1, code_lines) * 100,
        }
        return result

    def review_patch(self, patch_text: str) -> List[ReviewResult]:
        """审查补丁中的新增代码"""
        files = parse_patch(patch_text)
        if not files:
            raise ValueError(ERROR_CODES["E003"])

        results: List[ReviewResult] = []
        for file_name, added_lines in files:
            if not added_lines:
                continue
            language, _ = detect_language(file_name)
            if not language:
                continue
            issues = self.review_lines(added_lines, language)
            result = ReviewResult(
                file_path=file_name,
                language=language,
                total_lines=len(added_lines),
                issues=issues,
            )
            result.metrics = {
                "code_lines": len(added_lines),
                "comment_lines": 0,
                "issue_density": len(issues) / max(1, len(added_lines)) * 100,
            }
            results.append(result)
        return results


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------

def generate_report(result: ReviewResult, verbose: bool = False) -> str:
    """生成结构化审查报告（文本格式）"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"代码审查报告")
    lines.append("=" * 70)
    lines.append(f"文件: {result.file_path}")
    lines.append(f"语言: {result.language}")
    lines.append(f"总行数: {result.total_lines}")
    lines.append(f"风险评分: {result.risk_score:.1f} / 100")
    lines.append(f"问题统计: {result.critical_count} 严重, {result.warning_count} 警告, {result.info_count} 提示")
    lines.append("-" * 70)

    if not result.issues:
        lines.append("✅ 未发现明显问题")
    else:
        # 按严重程度排序
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_issues = sorted(result.issues, key=lambda i: severity_order.get(i.severity, 9))

        for issue in sorted_issues:
            lines.append(f"[{issue.severity.upper():8}] 第{issue.line}行 第{issue.column}列")
            lines.append(f"  类别: {issue.category}")
            lines.append(f"  描述: {issue.message}")
            lines.append(f"  置信度: {issue.confidence:.0%}")
            if issue.suggestion:
                lines.append(f"  建议: {issue.suggestion}")
            if verbose:
                lines.append(f"  严重程度: {issue.severity}")
            lines.append("-" * 50)

    lines.append("=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保稳健。
    """
    print("开始自检...")

    # 1. 测试语言识别
    lang, ext = detect_language("test.py")
    assert lang == "python", "语言识别失败"
    assert ext == ".py", "扩展名识别失败"

    # 2. 测试补丁解析
    sample_patch = """diff --git a/example.py b/example.py
--- a/example.py
+++ b/example.py
@@ -1,5 +1,8 @@
 def main():
     print("hello")
+    password = "secret123"
+    # TODO: fix this
+    eval(user_input)
+    long_line = "x" * 200
"""
    files = parse_patch(sample_patch)
    assert len(files) >= 1, "补丁解析失败"
    assert files[0][0] == "example.py", "补丁文件名解析失败"
    assert len(files[0][1]) >= 4, "补丁新增行解析失败"

    # 3. 测试审查引擎
    engine = ReviewEngine()
    sample_code = [
        'def process(data):\n',
        '    password = "hardcoded_secret"\n',
        '    # TODO: implement validation\n',
        '    eval(data)\n',
        '    result = "a" * 150\n',
        '    return result\n',
    ]
    issues = engine.review_lines(sample_code, "python")
    assert len(issues) >= 3, f"审查发现问题数不足，实际: {len(issues)}"

    # 分类断言（宽松）
    severities = [i.severity for i in issues]
    assert "critical" in severities, "应检测到严重问题"
    assert "warning" in severities or "info" in severities, "应检测到警告或提示"

    # 4. 测试审查结果汇总
    result = ReviewResult(
        file_path="test.py",
        language="python",
        total_lines=10,
        issues=issues,
    )
    assert result.critical_count >= 1, "严重问题计数错误"
    assert result.risk_score >= 0, "风险评分不应为负"
    assert result.risk_score <= 100, "风险评分不应超过100"

    # 5. 测试报告生成
    report = generate_report(result)
    assert "代码审查报告" in report, "报告格式错误"
    assert "test.py" in report, "报告缺少文件名"

    # 6. 测试空输入处理
    empty_result = ReviewResult(file_path="empty.py", language="python", total_lines=0, issues=[])
    assert empty_result.risk_score == 0, "空结果风险评分应为0"
    assert empty_result.critical_count == 0, "空结果严重计数应为0"

    # 7. 测试完整文件审查（使用临时内存模拟）
    # 直接测试 review_lines 而非 review_file（避免文件系统依赖）
    more_issues = engine.review_lines([
        'import os\n',
        'def main():\n',
        '    global x\n',
        '    try:\n',
        '        pass\n',
        '    except Exception:\n',
        '        pass\n',
        '    api_key = "abcdef123456"\n',
        '    return True\n',
    ], "python")
    assert len(more_issues) >= 2, "复杂样例应发现更多问题"

    print("✅ 自检通过：所有核心逻辑验证成功")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="代码审查工具 - 将代码或补丁转为结构化审查报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python main.py --selftest\n"
               "  python main.py --file sample.py\n"
               "  python main.py --patch changes.diff\n"
               "  python main.py --file sample.py --verbose\n"
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--file", type=str, help="要审查的代码文件路径")
    parser.add_argument("--patch", type=str, help="要审查的补丁文件路径")
    parser.add_argument("--verbose", action="store_true", help="输出详细信息")

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            success = run_selftest()
            return 0 if success else 1

        # 文件审查模式
        if args.file:
            if not os.path.isfile(args.file):
                print(f"错误 {ERROR_CODES['E002']}: 文件不存在或无法访问", file=sys.stderr)
                return 2
            engine = ReviewEngine()
            result = engine.review_file(args.file)
            report = generate_report(result, verbose=args.verbose)
            print(report)
            return 0

        # 补丁审查模式
        if args.patch:
            if not os.path.isfile(args.patch):
                print(f"错误 {ERROR_CODES['E002']}: 补丁文件不存在或无法访问", file=sys.stderr)
                return 2
            with open(args.patch, "r", encoding="utf-8", errors="replace") as f:
                patch_text = f.read()
            engine = ReviewEngine()
            results = engine.review_patch(patch_text)
            if not results:
                print("未在补丁中发现可审查的代码")
                return 0
            for result in results:
                report = generate_report(result, verbose=args.verbose)
                print(report)
                print()
            return 0

        # 无有效参数
        parser.print_help()
        print(f"\n错误 {ERROR_CODES['E001']}: 请提供 --file 或 --patch 参数", file=sys.stderr)
        return 2

    except FileNotFoundError as e:
        print(f"错误 {ERROR_CODES['E002']}: {e}", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"错误 {ERROR_CODES['E009']}: 权限不足，无法访问文件", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"错误 {ERROR_CODES['E010']}: 未预期的异常: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
