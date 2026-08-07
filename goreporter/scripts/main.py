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
from dataclasses import dataclass, field
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
    timestamp: float = field(default_factory=time.time)

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
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "grade": self.grade,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results],
        }


# ============================================================
# 核心分析引擎
# ============================================================

class GoAnalyzer:
    """
    Go 语言代码静态分析器
    执行规则：识别函数、注释、估算复杂度、检测常见问题
    """

    # 函数声明正则（简化版，覆盖常见形式）
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

        # 计算复杂度（简化估算）
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
        基于控制流语句密度和代码规模
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
        基于输入完整性和分析确定性
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
# 主流程
# ============================================================

def process_content(content: str, source_desc: str = "inline") -> QualityReport:
    """
    处理输入内容，返回质量报告
    """
    try:
        # 创建分析器并执行分析
        analyzer = GoAnalyzer(content)
        result = analyzer.analyze()
        result.source = source_desc

        # 生成报告
        report = ReportGenerator.generate([result])
        return report

    except GoReporterError:
        raise
    except Exception as e:
        raise GoReporterError("E008", f"分析过程发生错误: {str(e)}")


def process_file(filepath: str) -> QualityReport:
    """处理文件输入"""
    if not os.path.isfile(filepath):
        raise GoReporterError("E006", f"文件不存在或不可读: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        raise GoReporterError("E006", f"读取文件失败: {str(e)}")

    return process_content(content, source_desc=f"file:{filepath}")


def process_batch(contents: List[Tuple[str, str]]) -> QualityReport:
    """批量处理多个内容"""
    if not contents:
        raise GoReporterError("E001", "批量输入为空")

    results = []
    for content, source in contents:
        analyzer = GoAnalyzer(content)
        result = analyzer.analyze()
        result.source = source
        results.append(result)

    return ReportGenerator.generate(results)


# ============================================================
# 内置自检数据（硬编码样例）
# ============================================================

SELF_TEST_SAMPLES = [
    # (描述, Go 代码)
    ("良好代码示例", '''
package main

import "fmt"

// User 表示用户信息
type User struct {
    Name string
    Age  int
}

// NewUser 创建新用户
func NewUser(name string, age int) *User {
    return &User{Name: name, Age: age}
}

// GetName 获取用户名
func (u *User) GetName() string {
    return u.Name
}

func main() {
    user := NewUser("Alice", 30)
    fmt.Printf("User: %s, Age: %d\\n", user.GetName(), user.Age)
}
'''),
    ("普通代码示例", '''
package main

import "fmt"

func calculate(x int, y int) int {
    result := x * y
    if result > 100 {
        fmt.Println("Result is large")
    }
    return result
}

func main() {
    // TODO: 添加更多测试
    value := calculate(10, 20)
    fmt.Println(value)
}
'''),
    ("问题代码示例", '''
package main

func risky() {
    var data map[string]int
    data["key"] = 1  // nil map 赋值会 panic
    panic("something went wrong")
}

func main() {
    goto end
end:
    print("done")
}
'''),
]


def run_selftest() -> int:
    """
    内置自检函数
    使用硬编码样例数据验证核心逻辑
    断言使用宽松阈值，确保稳健性
    """
    print("=" * 60)
    print("goreporter 自检程序")
    print("=" * 60)

    passed = 0
    total = 0

    # 测试1: 基本分析功能
    print("\n[测试1] 基本分析功能")
    try:
        analyzer = GoAnalyzer(SELF_TEST_SAMPLES[0][1])
        result = analyzer.analyze()
        total += 1

        # 宽松断言
        assert result.line_count > 0, "行数应大于0"
        assert result.function_count >= 2, "函数数应至少为2"
        assert result.comment_count >= 1, "注释数应至少为1"
        assert 0 <= result.complexity_score <= 100, "复杂度应在0-100范围"
        assert 0 <= result.confidence <= 100, "置信度应在0-100范围"

        passed += 1
        print(f"  ✓ 通过 (行数={result.line_count}, 函数={result.function_count}, "
              f"复杂度={result.complexity_score:.1f}, 置信度={result.confidence:.1f}%)")
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")

    # 测试2: 问题检测功能
    print("\n[测试2] 问题检测")
    try:
        analyzer = GoAnalyzer(SELF_TEST_SAMPLES[2][1])
        result = analyzer.analyze()
        total += 1

        # 问题代码应检测到问题
        assert len(result.issues) > 0, "问题代码应检测到至少1个问题"
        passed += 1
        print(f"  ✓ 通过 (检测到 {len(result.issues)} 个问题)")
        for issue in result.issues[:3]:
            print(f"    - 行{issue['line']}: [{issue['severity']}] {issue['message']}")
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")

    # 测试3: 报告生成
    print("\n[测试3] 报告生成")
    try:
        results = []
        for desc, code in SELF_TEST_SAMPLES:
            analyzer = GoAnalyzer(code)
            r = analyzer.analyze()
            r.source = desc
            results.append(r)

        report = ReportGenerator.generate(results)
        total += 1

        # 宽松断言
        assert 0 <= report.overall_score <= 100, "总分应在0-100"
        assert report.grade in ["A", "B", "C", "D", "F"], "等级应有效"
        assert len(report.summary) > 0, "摘要不应为空"
        assert len(report.results) == 3, "应有3个结果"

        passed += 1
        print(f"  ✓ 通过 (总分={report.overall_score:.1f}, 等级={report.grade})")
        print(f"    摘要: {report.summary}")
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")

    # 测试4: 错误处理
    print("\n[测试4] 错误处理")
    total += 1
    try:
        # 空输入应抛出 E001
        try:
            GoAnalyzer("")
            print("  ✗ 失败: 空输入未抛出异常")
        except GoReporterError as e:
            assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
            passed += 1
            print(f"  ✓ 通过 (空输入正确返回 {e.code})")
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")

    # 测试5: 批量处理
    print("\n[测试5] 批量处理")
    try:
        contents = [(code, desc) for desc, code in SELF_TEST_SAMPLES]
        report = process_batch(contents)
        total += 1

        assert len(report.results) == 3, "批量处理应返回3个结果"
        passed += 1
        print(f"  ✓ 通过 (批量处理 {len(report.results)} 个输入)")
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")

    # 测试6: 文件处理（使用临时文件）
    print("\n[测试6] 文件处理")
    total += 1
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
            f.write(SELF_TEST_SAMPLES[0][1])
            tmp_path = f.name

        try:
            report = process_file(tmp_path)
            assert report.overall_score > 0, "文件处理应产生有效评分"
            passed += 1
            print(f"  ✓ 通过 (文件处理成功, 评分={report.overall_score:.1f})")
        finally:
            # 清理临时文件
            os.unlink(tmp_path)
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {passed}/{total} 通过")
    print("=" * 60)

    return 0 if passed == total else 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="goreporter - Go 代码审查与质量报告工具",
        epilog="示例: python main.py --file main.go 或 python main.py --selftest"
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", "-f", type=str, help="输入 Go 文件路径")
    input_group.add_argument("--code", "-c", type=str, help="直接输入代码字符串")
    input_group.add_argument("--selftest", action="store_true", help="运行内置自检")

    # 输出参数
    parser.add_argument("--output", "-o", type=str, help="输出 JSON 报告到文件")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--batch", "-b", type=str, help="批量处理文件列表（逗号分隔）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    try:
        report: Optional[QualityReport] = None

        # 批量处理
        if args.batch:
            file_list = [f.strip() for f in args.batch.split(",") if f.strip()]
            if not file_list:
                raise GoReporterError("E001", "批量文件列表为空")

            contents = []
            for fp in file_list:
                if not os.path.isfile(fp):
                    raise GoReporterError("E006", f"文件不存在: {fp}")
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    contents.append((f.read(), f"file:{fp}"))
            report = process_batch(contents)

        # 文件处理
        elif args.file:
            report = process_file(args.file)

        # 代码处理
        elif args.code:
            report = process_content(args.code, source_desc="command-line")

        # 无输入
        else:
            parser.print_help()
            raise GoReporterError("E001", "请提供输入内容，使用 --file 或 --code 参数")

        # 输出报告
        if args.json:
            output_str = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
        else:
            # 文本格式输出
            lines = []
            lines.append("=" * 60)
            lines.append(f"goreporter 代码审查报告")
            lines.append("=" * 60)
            lines.append(f"总体评分: {report.overall_score:.1f}/100")
            lines.append(f"质量等级: {report.grade}")
            lines.append(f"摘要: {report.summary}")
            lines.append("-" * 60)

            for i, r in enumerate(report.results, 1):
                lines.append(f"[{i}] {r.source}")
                lines.append(f"    行数: {r.line_count}, 函数: {r.function_count}, "
                           f"注释: {r.comment_count}")
                lines.append(f"    复杂度: {r.complexity_score:.1f}/100, "
                           f"置信度: {r.confidence:.1f}%")
                if r.issues:
                    lines.append(f"    问题 ({len(r.issues)}):")
                    for issue in r.issues[:5]:
                        lines.append(f"      - 行{issue['line']}: "
                                   f"[{issue['severity']}] {issue['message']}")
                else:
                    lines.append(f"    问题: 无")
                lines.append("")

            output_str = "\n".join(lines)

        # 输出到文件或终端
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_str)
                print(f"报告已写入: {args.output}")
            except Exception as e:
                raise GoReporterError("E007", f"写入报告文件失败: {str(e)}")
        else:
            print(output_str)

        return 0

    except GoReporterError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E008] 未预期错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
