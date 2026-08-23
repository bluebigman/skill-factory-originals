#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
goreporter - 代码审查工具（独立实现）

基于功能规格独立编写的 clean-room 实现。
提供静态分析、单元测试、代码审查与质量报告生成能力。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要参数",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败，检查文件路径",
    "E007": "文件写入失败，检查权限或磁盘空间",
    "E008": "分析过程内部错误",
    "E009": "参数冲突或非法组合",
    "E010": "系统资源不足",
}


class GoReporterError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class AnalysisResult:
    """单次分析结果"""
    source: str                    # 输入来源描述
    content_hash: str              # 内容哈希
    line_count: int = 0            # 代码行数
    function_count: int = 0        # 函数数量
    comment_count: int = 0         # 注释数量
    complexity_score: float = 0.0  # 复杂度评分 (0-100)
    issues: List[Dict[str, Any]] = field(default_factory=list)  # 发现的问题
    confidence: float = 0.0        # 置信度 (0-100)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "source": self.source,
            "content_hash": self.content_hash,
            "line_count": self.line_count,
            "function_count": self.function_count,
            "comment_count": self.comment_count,
            "complexity_score": round(self.complexity_score, 2),
            "issues": self.issues,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class QualityReport:
    """整体质量报告"""
    overall_score: float = 0.0     # 总体评分 (0-100)
    grade: str = "N/A"             # 等级 (A/B/C/D/F)
    summary: str = ""              # 摘要
    results: List[AnalysisResult] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "grade": self.grade,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results],
        }


# ============================================================
# 文件 I/O 工具（带重试和原子写入）
# ============================================================

def read_file_with_retry(filepath: str, max_retries: int = 3, base_delay: float = 0.5) -> str:
    """读取文件，带指数退避重试"""
    for attempt in range(max_retries):
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            if attempt == max_retries - 1:
                raise GoReporterError("E006", f"读取文件失败: {str(e)}")
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
    raise GoReporterError("E006", f"读取文件失败: {filepath}")


def write_file_atomic(filepath: str, content: str, max_retries: int = 3, base_delay: float = 0.5) -> None:
    """原子写入文件：先写临时文件，再 os.replace"""
    directory = os.path.dirname(os.path.abspath(filepath))
    for attempt in range(max_retries):
        temp_path = None
        try:
            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".tmp_", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            # 原子替换
            os.replace(temp_path, filepath)
            return
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            if attempt == max_retries - 1:
                raise GoReporterError("E007", f"写入文件失败: {str(e)}")
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
    raise GoReporterError("E007", f"写入文件失败: {filepath}")


# ============================================================
# 核心分析引擎
# ============================================================

class GoAnalyzer:
    """
    Go 语言代码静态分析器
    执行规则：识别函数、注释、估算复杂度、检测常见问题
    """

    # 函数声明正则（覆盖常见形式）
    FUNC_RE = re.compile(
        r'^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(',
        re.MULTILINE
    )

    # 注释行正则
    COMMENT_RE = re.compile(r'^\s*(?://|/\*|\*|//\s)')

    # 常见问题模式（简化启发式）
    ISSUE_PATTERNS = [
        (r'\bTODO\b', "存在 TODO 待办标记", "info"),
        (r'\bFIXME\b', "存在 FIXME 待修复标记", "warning"),
        (r'\bpanic\s*\(', "使用 panic，建议返回错误", "warning"),
        (r'\bprint\s*\(', "使用 print 而非日志库", "info"),
        (r'\bgoto\s+', "使用 goto，不建议使用", "warning"),
        (r'var\s+\w+\s+=\s+nil', "变量赋值为 nil，检查空指针风险", "warning"),
    ]

    def __init__(self, content: str):
        """初始化分析器"""
        if not content or not content.strip():
            raise GoReporterError("E001")
        self.content = content
        self.lines = content.splitlines()

    def analyze(self) -> AnalysisResult:
        """执行分析，返回结果"""
        result = AnalysisResult(
            source="inline-content",
            content_hash=self._hash_content(),
            line_count=len(self.lines),
        )

        # 统计函数数量
        result.function_count = self._count_functions()

        # 统计注释数量
        result.comment_count = self._count_comments()

        # 计算复杂度（基于控制流和规模的可解释算法）
        result.complexity_score = self._estimate_complexity()

        # 检测问题
        result.issues = self._detect_issues()

        # 计算置信度（基于输入完整性和分析确定性）
        result.confidence = self._calculate_confidence()

        return result

    def _hash_content(self) -> str:
        """计算内容哈希"""
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]

    def _count_functions(self) -> int:
        """统计函数数量"""
        matches = self.FUNC_RE.findall(self.content)
        return len(matches)

    def _count_comments(self) -> int:
        """统计注释行数"""
        count = 0
        in_block_comment = False
        for line in self.lines:
            stripped = line.strip()
            if in_block_comment:
                count += 1
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("/*"):
                count += 1
                if "*/" not in stripped:
                    in_block_comment = True
                continue
            if self.COMMENT_RE.match(line):
                count += 1
        return count

    def _estimate_complexity(self) -> float:
        """
        估算代码复杂度（0-100）
        基于控制流语句密度和代码规模的可解释算法
        """
        if not self.lines:
            return 0.0

        # 控制流关键词计数
        control_flow = sum(
            len(re.findall(r'\b' + kw + r'\b', self.content))
            for kw in ['if', 'else', 'for', 'switch', 'case', 'select', 'go ', 'defer']
        )

        # 代码行数（非空、非注释）
        code_lines = 0
        for line in self.lines:
            s = line.strip()
            if s and not self.COMMENT_RE.match(line):
                code_lines += 1

        if code_lines == 0:
            return 0.0

        # 基础复杂度：每 10 行代码 1 个控制流为合理基线
        base_score = min(50.0, (control_flow / max(code_lines / 10, 1)) * 10)

        # 规模惩罚：超大文件增加复杂度
        size_penalty = min(30.0, max(0.0, (code_lines - 500) / 50))

        # 函数密度：函数过多或过少都增加复杂度
        func_density = self._count_functions() / max(code_lines / 50, 1)
        density_factor = abs(func_density - 1.0) * 10

        score = base_score + size_penalty + density_factor
        return min(100.0, max(0.0, score))

    def _detect_issues(self) -> List[Dict[str, Any]]:
        """检测代码中的问题"""
        issues = []
        for line_num, line in enumerate(self.lines, 1):
            for pattern, message, severity in self.ISSUE_PATTERNS:
                if re.search(pattern, line):
                    issues.append({
                        "line": line_num,
                        "severity": severity,
                        "message": message,
                        "code": f"G{len(issues)+1:03d}",
                    })
        return issues

    def _calculate_confidence(self) -> float:
        """
        计算置信度
        基于输入完整性和分析确定性的可解释算法
        """
        # 基础置信度
        confidence = 90.0

        # 内容太短降低置信度
        if len(self.lines) < 5:
            confidence -= 10
        # 内容很长提高置信度（样本多）
        elif len(self.lines) > 100:
            confidence += 5

        # 无函数定义降低置信度（可能不是完整代码）
        if self._count_functions() == 0:
            confidence -= 15

        # 大量注释可能影响分析
        if self._count_comments() > len(self.lines) * 0.5:
            confidence -= 5

        return max(0.0, min(100.0, confidence))


# ============================================================
# 报告生成器
# ============================================================

class ReportGenerator:
    """生成质量报告"""

    @staticmethod
    def generate(results: List[AnalysisResult]) -> QualityReport:
        """根据分析结果生成报告"""
        if not results:
            raise GoReporterError("E001", "没有可用的分析结果")

        report = QualityReport(results=results)

        # 计算总体评分（加权平均）
        total_weight = 0.0
        weighted_score = 0.0
        for r in results:
            weight = r.confidence / 100.0
            weighted_score += r.complexity_score * weight
            total_weight += weight

        if total_weight > 0:
            # 复杂度评分反向映射为质量评分（复杂度越低质量越高）
            quality = 100.0 - (weighted_score / total_weight)
            report.overall_score = max(0.0, min(100.0, quality))
        else:
            report.overall_score = 50.0

        # 确定等级
        score = report.overall_score
        if score >= 90:
            report.grade = "A"
            report.summary = "代码质量优秀，结构清晰，建议保持"
        elif score >= 80:
            report.grade = "B"
            report.summary = "代码质量良好，有少量可改进之处"
        elif score >= 70:
            report.grade = "C"
            report.summary = "代码质量一般，建议针对问题项进行优化"
        elif score >= 60:
            report.grade = "D"
            report.summary = "代码质量较差，存在较多风险，建议重构"
        else:
            report.grade = "F"
            report.summary = "代码质量很差，存在严重问题，强烈建议重构"

        # 添加置信度提示
        low_conf = [r for r in results if r.confidence < 85]
        if low_conf:
            report.summary += "（部分结果置信度较低，建议人工复核）"

        return report


# ============================================================
# 可视化输出（HTML 报告）
# ============================================================

def generate_html_report(report: QualityReport) -> str:
    """生成 HTML 格式的可视化报告"""
    results_html = ""
    for i, r in enumerate(report.results, 1):
        issues_html = ""
        if r.issues:
            issues_html = "<ul>"
            for issue in r.issues:
                issues_html += f"<li><strong>{issue['severity']}</strong>: {issue['message']} (行 {issue['line']})</li>"
            issues_html += "</ul>"
        else:
            issues_html = "<p>未发现问题</p>"

        results_html += f"""
        <div class="result">
            <h3>分析 {i}: {r.source}</h3>
            <p>代码行数: {r.line_count} | 函数数量: {r.function_count} | 注释行数: {r.comment_count}</p>
            <p>复杂度评分: {r.complexity_score:.2f}/100 | 置信度: {r.confidence:.2f}%</p>
            <h4>发现的问题:</h4>
            {issues_html}
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>GoReporter 质量报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .score {{ font-size: 48px; font-weight: bold; color: {('#4CAF50' if report.overall_score >= 80 else '#FF9800' if report.overall_score >= 60 else '#F44336')}; }}
        .grade {{ font-size: 24px; color: #666; }}
        .summary {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .result {{ background: #fafafa; border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 15px 0; }}
        .result h3 {{ margin-top: 0; color: #2196F3; }}
        ul {{ margin: 5px 0; }}
        li {{ margin: 3px 0; }}
        .timestamp {{ color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>GoReporter 代码质量报告</h1>
        <div class="score">{report.overall_score:.1f}/100</div>
        <div class="grade">等级: {report.grade}</div>
        <div class="summary">
            <strong>摘要:</strong> {report.summary}
        </div>
        <h2>详细分析</h2>
        {results_html}
        <div class="timestamp">报告生成时间: {datetime.fromisoformat(report.generated_at).strftime('%Y-%m-%d %H:%M:%S %Z')}</div>
    </div>
</body>
</html>"""
    return html


def generate_csv_report(report: QualityReport) -> str:
    """生成 CSV 格式报告"""
    lines = ["source,line_count,function_count,comment_count,complexity_score,confidence,issue_count"]
    for r in report.results:
        lines.append(f"{r.source},{r.line_count},{r.function_count},{r.comment_count},{r.complexity_score:.2f},{r.confidence:.2f},{len(r.issues)}")
    return "\n".join(lines)


# ============================================================
# 主
