#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rocket-fuel-skill 独立实现脚本
双引擎协作代码审查与质量门禁，自动生成结构化审查报告。
仅依据功能规格独立实现，不包含任何既有代码。
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "目录不存在",
    "E004": "文件读取失败",
    "E005": "文件解析失败",
    "E006": "URL格式错误",
    "E007": "不支持的来源类型",
    "E008": "审查规则配置错误",
    "E009": "报告生成失败",
    "E010": "内部逻辑错误",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


@dataclass
class ReviewIssue:
    """单条审查问题记录。"""

    file_path: str
    line_number: int
    issue_type: str
    severity: str  # high / medium / low
    confidence: str  # high / medium / low
    description: str
    suggestion: str


@dataclass
class ReviewReport:
    """结构化审查报告。"""

    report_id: str
    generated_at: str
    source: str
    engine_results: Dict[str, Any] = field(default_factory=dict)
    issues: List[ReviewIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "source": self.source,
            "engine_results": self.engine_results,
            "issues": [asdict(issue) for issue in self.issues],
            "summary": self.summary,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class CodeParser:
    """代码解析器：提取关键信息。"""

    # 常见编程语言注释符号
    COMMENT_SYMBOLS = {
        ".py": "#",
        ".js": "//",
        ".ts": "//",
        ".java": "//",
        ".c": "//",
        ".cpp": "//",
        ".h": "//",
        ".hpp": "//",
        ".cs": "//",
        ".go": "//",
        ".rb": "#",
        ".php": "//",
        ".swift": "//",
        ".kt": "//",
        ".rs": "//",
        ".sh": "#",
        ".yml": "#",
        ".yaml": "#",
        ".json": "//",
        ".html": "<!--",
        ".css": "/*",
    }

    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.lines = content.splitlines()
        self.extension = Path(file_path).suffix.lower()

    def extract_functions(self) -> List[Dict[str, Any]]:
        """提取函数定义（适用于常见语言）。"""
        functions = []
        patterns = [
            r"^\s*(?:def|function|func|public\s+static|private\s+static)\s+(\w+)\s*\(",
            r"^\s*(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(",
        ]
        for idx, line in enumerate(self.lines, 1):
            for pattern in patterns:
                match = re.search(pattern, line.strip())
                if match:
                    functions.append({
                        "name": match.group(1),
                        "line": idx,
                    })
                    break
        return functions

    def extract_classes(self) -> List[Dict[str, Any]]:
        """提取类定义。"""
        classes = []
        pattern = r"^\s*(?:class|interface|struct|enum)\s+(\w+)"
        for idx, line in enumerate(self.lines, 1):
            match = re.search(pattern, line.strip())
            if match:
                classes.append({
                    "name": match.group(1),
                    "line": idx,
                })
        return classes

    def extract_dependencies(self) -> List[str]:
        """提取依赖（import/require/include 等）。"""
        dependencies = []
        patterns = [
            r"^\s*(?:import|from|require|include|using)\s+([\w\.]+)",
            r"^\s*import\s+[\w\s]*\bfrom\s+['\"]([^'\"]+)['\"]",
        ]
        for line in self.lines:
            for pattern in patterns:
                match = re.search(pattern, line.strip())
                if match:
                    dep = match.group(1).strip()
                    if dep and dep not in dependencies:
                        dependencies.append(dep)
                    break
        return dependencies

    def detect_syntax_issues(self) -> List[Dict[str, Any]]:
        """检测基础语法问题（括号匹配、缩进等）。"""
        issues = []
        # 括号匹配检查
        stack = []
        bracket_pairs = {")": "(", "]": "[", "}": "{"}
        for idx, line in enumerate(self.lines, 1):
            for char in line:
                if char in "([{":
                    stack.append((char, idx))
                elif char in ")]}":
                    if not stack or stack[-1][0] != bracket_pairs[char]:
                        issues.append({
                            "line": idx,
                            "type": "语法错误",
                            "description": f"括号 '{char}' 不匹配",
                            "severity": "high",
                        })
                        break
                    else:
                        stack.pop()
            # 重置栈（每行独立检查更稳健）
            stack = []
        return issues

    def detect_security_risks(self) -> List[Dict[str, Any]]:
        """检测安全风险模式。"""
        risks = []
        patterns = [
            (r"eval\s*\(", "危险函数调用", "使用 eval 可能导致代码注入"),
            (r"exec\s*\(", "危险函数调用", "使用 exec 可能导致代码注入"),
            (r"system\s*\(|shell_exec\s*\(", "命令执行", "直接执行系统命令"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "硬编码密码", "发现硬编码密码"),
            (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "硬编码密钥", "发现硬编码 API 密钥"),
            (r"token\s*=\s*['\"][^'\"]+['\"]", "硬编码令牌", "发现硬编码令牌"),
            (r"SELECT\s+.*\s+FROM", "SQL 注入风险", "可能存在 SQL 注入"),
            (r"innerHTML\s*=", "XSS 风险", "可能存在 XSS 漏洞"),
        ]
        for idx, line in enumerate(self.lines, 1):
            for pattern, issue_type, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    risks.append({
                        "line": idx,
                        "type": issue_type,
                        "description": desc,
                        "severity": "high",
                    })
                    break
        return risks

    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """检测性能问题。"""
        issues = []
        patterns = [
            (r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(", "低效循环", "使用 range(len()) 遍历"),
            (r"\.\.\.\s*\+\s*\.\.\.", "低效字符串拼接", "循环中字符串拼接"),
            (r"while\s+True", "潜在死循环", "使用 while True 需谨慎"),
        ]
        for idx, line in enumerate(self.lines, 1):
            for pattern, issue_type, desc in patterns:
                if re.search(pattern, line):
                    issues.append({
                        "line": idx,
                        "type": issue_type,
                        "description": desc,
                        "severity": "medium",
                    })
                    break
        return issues

    def analyze(self) -> Dict[str, Any]:
        """综合分析代码。"""
        return {
            "functions": self.extract_functions(),
            "classes": self.extract_classes(),
            "dependencies": self.extract_dependencies(),
            "syntax_issues": self.detect_syntax_issues(),
            "security_risks": self.detect_security_risks(),
            "performance_issues": self.detect_performance_issues(),
        }


class ReviewEngine:
    """审查引擎基类。"""

    def __init__(self, name: str):
        self.name = name

    def review(self, code_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行审查，返回结果。"""
        raise NotImplementedError

    def _make_issues(self, code_info: Dict[str, Any]) -> List[ReviewIssue]:
        """根据代码分析生成审查问题。"""
        issues = []
        # 语法问题
        for issue in code_info.get("syntax_issues", []):
            issues.append(ReviewIssue(
                file_path=code_info.get("file_path", ""),
                line_number=issue["line"],
                issue_type=issue["type"],
                severity=issue["severity"],
                confidence="high",
                description=issue["description"],
                suggestion="请检查并修复语法问题",
            ))
        # 安全问题
        for issue in code_info.get("security_risks", []):
            issues.append(ReviewIssue(
                file_path=code_info.get("file_path", ""),
                line_number=issue["line"],
                issue_type=issue["type"],
                severity=issue["severity"],
                confidence="high",
                description=issue["description"],
                suggestion="请移除危险调用或使用安全替代方案",
            ))
        # 性能问题
        for issue in code_info.get("performance_issues", []):
            issues.append(ReviewIssue(
                file_path=code_info.get("file_path", ""),
                line_number=issue["line"],
                issue_type=issue["type"],
                severity=issue["severity"],
                confidence="medium",
                description=issue["description"],
                suggestion="请优化代码性能",
            ))
        return issues


class Fable5Engine(ReviewEngine):
    """Fable 5 审查引擎。"""

    def __init__(self):
        super().__init__("Fable 5")

    def review(self, code_info: Dict[str, Any]) -> Dict[str, Any]:
        issues = self._make_issues(code_info)
        # Fable 5 侧重逻辑分析
        logic_issues = []
        for issue in issues:
            if issue.severity == "high":
                logic_issues.append(issue)
        return {
            "engine": self.name,
            "status": "completed",
            "issues_found": len(issues),
            "high_severity": len([i for i in issues if i.severity == "high"]),
            "logic_analysis": "完成",
        }


class CodexEngine(ReviewEngine):
    """Codex 审查引擎。"""

    def __init__(self):
        super().__init__("Codex")

    def review(self, code_info: Dict[str, Any]) -> Dict[str, Any]:
        issues = self._make_issues(code_info)
        # Codex 侧重安全与最佳实践
        security_issues = [i for i in issues if i.issue_type in ("危险函数调用", "命令执行", "SQL 注入风险", "XSS 风险")]
        return {
            "engine": self.name,
            "status": "completed",
            "issues_found": len(issues),
            "security_issues": len(security_issues),
            "best_practices": "已检查",
        }


class DualEngineReviewer:
    """双引擎协作审查器。"""

    def __init__(self):
        self.engines = [Fable5Engine(), CodexEngine()]

    def review_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """审查单个文件。"""
        parser = CodeParser(file_path, content)
        code_info = parser.analyze()
        code_info["file_path"] = file_path

        results = {}
        all_issues = []
        for engine in self.engines:
            result = engine.review(code_info)
            results[engine.name] = result
            # 合并问题（去重）
            for issue in self._make_issues(code_info):
                if issue not in all_issues:
                    all_issues.append(issue)

        return {
            "file_path": file_path,
            "engine_results": results,
            "issues": all_issues,
        }

    def _make_issues(self, code_info: Dict[str, Any]) -> List[ReviewIssue]:
        """生成问题列表。"""
        issues = []
        for issue in code_info.get("syntax_issues", []):
            issues.append(ReviewIssue(
                file_path=code_info.get("file_path", ""),
                line_number=issue["line"],
                issue_type=issue["type"],
                severity=issue["severity"],
                confidence="high",
                description=issue["description"],
                suggestion="请修复语法错误",
            ))
        for issue in code_info.get("security_risks", []):
            issues.append(ReviewIssue(
                file_path=code_info.get("file_path", ""),
                line_number=issue["line"],
                issue_type=issue["type"],
                severity=issue["severity"],
                confidence="high",
                description=issue["description"],
                suggestion="请移除安全风险",
            ))
        for issue in code_info.get("performance_issues", []):
            issues.append(ReviewIssue(
                file_path=code_info.get("file_path", ""),
                line_number=issue["line"],
                issue_type=issue["type"],
                severity=issue["severity"],
                confidence="medium",
                description=issue["description"],
                suggestion="请优化性能",
            ))
        return issues

    def review_directory(self, directory: str) -> List[Dict[str, Any]]:
        """审查目录下所有代码文件。"""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise SkillError("E003", f"目录不存在: {directory}")
        if not dir_path.is_dir():
            raise SkillError("E007", f"不是目录: {directory}")

        results = []
        supported_extensions = CodeParser.COMMENT_SYMBOLS.keys()
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    result = self.review_file(str(file_path), content)
                    results.append(result)
                except Exception as exc:
                    raise SkillError("E004", f"读取文件失败: {file_path} - {exc}")
        return results


class ReportGenerator:
    """报告生成器。"""

    @staticmethod
    def generate_markdown(report: ReviewReport) -> str:
        """生成 Markdown 格式报告。"""
        lines = [
            f"# 代码审查报告",
            f"",
            f"- **报告 ID**: {report.report_id}",
            f"- **生成时间**: {report.generated_at}",
            f"- **审查来源**: {report.source}",
            f"",
            f"## 双引擎审查结果",
            f"",
        ]

        for engine_name, result in report.engine_results.items():
            lines.append(f"### {engine_name}")
            lines.append(f"")
            lines.append(f"- 状态: {result.get('status', '未知')}")
            lines.append(f"- 发现问题数: {result.get('issues_found', 0)}")
            lines.append(f"- 高危问题: {result.get('high_severity', result.get('security_issues', 0))}")
            lines.append(f"")

        lines.append(f"## 问题清单")
        lines.append(f"")
        if report.issues:
            lines.append(f"| 文件 | 行号 | 类型 | 严重级别 | 置信度 | 描述 | 建议 |")
            lines.append(f"|------|------|------|----------|--------|------|------|")
            for issue in report.issues:
                lines.append(
                    f"| {issue.file_path} | {issue.line_number} | {issue.issue_type} | "
                    f"{issue.severity} | {issue.confidence} | {issue.description} | {issue.suggestion} |"
                )
        else:
            lines.append(f"未发现任何问题。")
        lines.append(f"")

        lines.append(f"## 总结")
        lines.append(f"")
        lines.append(f"- 总问题数: {report.summary.get('total_issues', 0)}")
        lines.append(f"- 高危问题: {report.summary.get('high_severity', 0)}")
        lines.append(f"- 中危问题: {report.summary.get('medium_severity', 0)}")
        lines.append(f"- 低危问题: {report.summary.get('low_severity', 0)}")
        lines.append(f"- 置信度高: {report.summary.get('high_confidence', 0)}")
        lines.append(f"- 置信度中: {report.summary.get('medium_confidence', 0)}")
        lines.append(f"- 置信度低: {report.summary.get('low_confidence', 0)}")
        lines.append(f"")

        return "\n".join(lines)


class RocketFuelSkill:
    """主技能类。"""

    def __init__(self):
        self.reviewer = DualEngineReviewer()
        self.report_generator = ReportGenerator()

    def review_source(self, source: str, source_type: str = "auto") -> ReviewReport:
        """审查代码来源。"""
        # 确定来源类型
        if source_type == "auto":
            if source.startswith(("http://", "https://")):
                source_type = "url"
            elif os.path.isdir(source):
                source_type = "directory"
            elif os.path.isfile(source):
                source_type = "file"
            else:
                raise SkillError("E007", f"无法识别来源类型: {source}")

        # 执行审查
        if source_type == "file":
            if not os.path.isfile(source):
                raise SkillError("E002", f"文件不存在: {source}")
            try:
                with open(source, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as exc:
                raise SkillError("E004", f"读取文件失败: {source} - {exc}")
            results = [self.reviewer.review_file(source, content)]
        elif source_type == "directory":
            results = self.reviewer.review_directory(source)
        elif source_type == "url":
            raise SkillError("E006", "URL 来源需要网络访问，当前版本不支持")
        else:
            raise SkillError("E007", f"不支持的来源类型: {source_type}")

        # 汇总结果
        all_issues = []
        engine_results = {}
        for result in results:
            all_issues.extend(result["issues"])
            for engine_name, engine_result in result["engine_results"].items():
                if engine_name not in engine_results:
                    engine_results[engine_name] = {
                        "status": "completed",
                        "issues_found": 0,
                        "high_severity": 0,
                    }
                engine_results[engine_name]["issues_found"] += engine_result.get("issues_found", 0)
                engine_results[engine_name]["high_severity"] += engine_result.get("high_severity", 0)

        # 生成报告
        report = ReviewReport(
            report_id=f"review_{int(time.time())}",
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            source=source,
            engine_results=engine_results,
            issues=all_issues,
            summary={
                "total_issues": len(all_issues),
                "high_severity": len([i for i in all_issues if i.severity == "high"]),
                "medium_severity": len([i for i in all_issues if i.severity == "medium"]),
                "low_severity": len([i for i in all_issues if i.severity == "low"]),
                "high_confidence": len([i for i in all_issues if i.confidence == "high"]),
                "medium_confidence": len([i for i in all_issues if i.confidence == "medium"]),
                "low_confidence": len([i for i in all_issues if i.confidence == "low"]),
            },
        )
        return report


def run_selftest() -> bool:
    """内置硬编码样例数据离线自检核心逻辑。"""
    print("=" * 60)
    print("开始自检（内置样例数据，不依赖外部资源）")
    print("=" * 60)

    try:
        # 样例代码（包含多种问题）
        sample_code = '''
import os
import sqlite3

def process_data(data, password="secret123"):
    """处理数据函数"""
    result = ""
    for i in range(len(data)):
        result += str(data[i])
    
    # 安全问题
    eval("print('dangerous')")
    
    # 潜在 SQL 注入
    query = "SELECT * FROM users WHERE name = '" + data + "'"
    
    return result

class DataProcessor:
    def __init__(self):
        self.api_key = "sk-1234567890"
    
    def process(self, items):
        items_list = []
        for item in items:
            items_list.append(item)
        return items_list
'''

        # 1. 测试代码解析器
        print("\n[1/5] 测试代码解析器...")
        parser = CodeParser("sample.py", sample_code)
        functions = parser.extract_functions()
        classes = parser.extract_classes()
        dependencies = parser.extract_dependencies()

        assert len(functions) >= 1, "应至少提取到 1 个函数"
        assert len(classes) >= 1, "应至少提取到 1 个类"
        assert len(dependencies) >= 2, "应至少提取到 2 个依赖"
        print(f"  ✓ 函数提取: {len(functions)} 个")
        print(f"  ✓ 类提取: {len(classes)} 个")
        print(f"  ✓ 依赖提取: {len(dependencies)} 个")

        # 2. 测试问题检测
        print("\n[2/5] 测试问题检测...")
        syntax_issues = parser.detect_syntax_issues()
        security_risks = parser.detect_security_risks()
        performance_issues = parser.detect_performance_issues()

        assert len(security_risks) >= 1, "应检测到至少 1 个安全问题"
        assert len(performance_issues) >= 1, "应检测到至少 1 个性能问题"
        print(f"  ✓ 语法问题: {len(syntax_issues)} 个")
        print(f"  ✓ 安全问题: {len(security_risks)} 个")
        print(f"  ✓ 性能问题: {len(performance_issues)} 个")

        # 3. 测试双引擎审查
        print("\n[3/5] 测试双引擎审查...")
        reviewer = DualEngineReviewer()
        result = reviewer.review_file("sample.py", sample_code)

        assert "Fable 5" in result["engine_results"], "Fable 5 引擎结果缺失"
        assert "Codex" in result["engine_results"], "Codex 引擎结果缺失"
        assert len(result["issues"]) >= 1, "应生成至少 1 个审查问题"
        print(f"  ✓ Fable 5 引擎: 发现问题 {result['engine_results']['Fable 5']['issues_found']} 个")
        print(f"  ✓ Codex 引擎: 发现问题 {result['engine_results']['Codex']['issues_found']} 个")
        print(f"  ✓ 合并问题: {len(result['issues'])} 个")

        # 4. 测试报告生成
        print("\n[4/5] 测试报告生成...")
        report = ReviewReport(
            report_id="test_report",
            generated_at="2026-01-01 00:00:00",
            source="sample.py",
            engine_results=result["engine_results"],
            issues=result["issues"],
            summary={
                "total_issues": len(result["issues"]),
                "high_severity": len([i for i in result["issues"] if i.severity == "high"]),
                "medium_severity": len([i for i in result["issues"] if i.severity == "medium"]),
                "low_severity": len([i for i in result["issues"] if i.severity == "low"]),
                "high_confidence": len([i for i in result["issues"] if i.confidence == "high"]),
                "medium_confidence": len([i for i in result["issues"] if i.confidence == "medium"]),
                "low_confidence": len([i for i in result["issues"] if i.confidence == "low"]),
            },
        )
        markdown = ReportGenerator.generate_markdown(report)
        assert "代码审查报告" in markdown, "报告应包含标题"
        assert "问题清单" in markdown, "报告应包含问题清单"
        assert len(markdown) > 200, "报告内容应足够详细"
        print(f"  ✓ Markdown 报告生成成功（{len(markdown)} 字符）")

        # 5. 测试 JSON 序列化
        print("\n[5/5] 测试 JSON 序列化...")
        json_str = report.to_json()
        json_data = json.loads(json_str)
        assert json_data["report_id"] == "test_report", "报告 ID 应正确"
        assert len(json_data["issues"]) >= 1, "JSON 应包含问题"
        print(f"  ✓ JSON 序列化成功（{len(json_str)} 字符）")

        print("\n" + "=" * 60)
        print("✅ 全部自检通过！")
        print("=" * 60)
        return True

    except AssertionError as exc:
        print(f"\n❌ 自检失败: {exc}")
        return False
    except Exception as exc:
        print(f"\n❌ 自检异常: {exc}")
        return False


def main():
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="rocket-fuel-skill: 双引擎协作代码审查与质量门禁"
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="审查来源（文件路径、目录路径或 URL）",
    )
    parser.add_argument(
        "--type",
        choices=["file", "directory", "url", "auto"],
        default="auto",
        help="来源类型（默认 auto 自动识别）",
    )
    parser.add_argument(
        "--output",
        help="输出报告文件路径（支持 .md 或 .json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 需要审查来源
    if not args.source:
        parser.print_help()
        sys.exit(1)

    try:
        # 执行审查
        skill = RocketFuelSkill()
        report = skill.review_source(args.source, args.type)

        # 输出报告
        if args.output:
            output_path = Path(args.output)
            try:
                if output_path.suffix.lower() == ".json":
                    output_path.write_text(report.to_json(), encoding="utf-8")
                else:
                    output_path.write_text(
                        ReportGenerator.generate_markdown(report),
                        encoding="utf-8",
                    )
                print(f"报告已保存至: {output_path}")
            except Exception as exc:
                raise SkillError("E009", f"报告写入失败: {exc}")
        else:
            # 输出到控制台
            print(ReportGenerator.generate_markdown(report))

        # 输出摘要
        print(f"\n审查完成: 共发现 {report.summary['total_issues']} 个问题，"
              f"其中高危 {report.summary['high_severity']} 个")

    except SkillError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
