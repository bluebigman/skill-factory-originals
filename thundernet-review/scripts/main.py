#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thundernet-review — 代码审查与缺陷扫描 Skill 的独立实现
=========================================================
本脚本根据功能规格独立编写（clean-room），不复制任何既有代码。

核心能力：
  - 将文本源码解析为可审查单元（函数/类/模块）
  - 静态规则扫描，输出结构化 Markdown / JSON 审查报告
  - 置信度标注与“需核实”占位符
  - 内置离线自检（--selftest），不依赖外部文件或网络

用法示例：
  python scripts/main.py sample.py
  python scripts/main.py --format json sample.py
  python scripts/main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义（E001 - E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入参数缺失或格式错误",
    "E002": "文件不存在或不可读",
    "E003": "文件类型不支持（非文本源码）",
    "E004": "源码解析失败（语法结构无法识别）",
    "E005": "输出格式未知",
    "E006": "JSON 序列化失败",
    "E007": "自检断言失败",
    "E008": "临时文件操作失败",
    "E009": "内部规则引擎异常",
    "E010": "未知错误",
}


def fail(code: str, message: str = "") -> None:
    """输出错误码并退出。"""
    desc = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        print(f"[{code}] {desc}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {desc}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ReviewIssue:
    """单条审查结论。"""
    severity: str          # 高 / 中 / 低
    line: int              # 行号（1-based），未知为 0
    message: str           # 缺陷描述
    suggestion: str        # 修复建议
    confidence: float      # 0.0 - 1.0
    rule_id: str           # 规则标识


@dataclass
class ReviewUnit:
    """一个可审查单元（函数/类/模块片段）。"""
    kind: str              # function / class / module
    name: str
    start_line: int
    end_line: int
    source: str = ""
    issues: List[ReviewIssue] = field(default_factory=list)


@dataclass
class ReviewReport:
    """完整审查报告。"""
    units: List[ReviewUnit] = field(default_factory=list)
    issues: List[ReviewIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = []
        lines.append("# ThunderNet Review 报告")
        lines.append("")
        lines.append(f"## 摘要")
        lines.append(f"- 审查单元数: {len(self.units)}")
        lines.append(f"- 总问题数: {self.summary.get('total', 0)}")
        lines.append(f"- 高: {self.summary.get('high', 0)}  中: {self.summary.get('medium', 0)}  低: {self.summary.get('low', 0)}")
        lines.append("")
        lines.append("## 详细结果")
        lines.append("")
        if not self.issues:
            lines.append("未发现明显问题。")
        for i, issue in enumerate(self.issues, 1):
            lines.append(f"### 缺陷 #{i} [{issue.severity}]")
            lines.append(f"- 位置: 行 {issue.line}")
            lines.append(f"- 规则: {issue.rule_id}")
            lines.append(f"- 描述: {issue.message}")
            lines.append(f"- 建议: {issue.suggestion}")
            lines.append(f"- 置信度: {issue.confidence:.2f}")
            lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        data = {
            "units": [
                {
                    "kind": u.kind,
                    "name": u.name,
                    "start_line": u.start_line,
                    "end_line": u.end_line,
                }
                for u in self.units
            ],
            "issues": [
                {
                    "severity": i.severity,
                    "line": i.line,
                    "message": i.message,
                    "suggestion": i.suggestion,
                    "confidence": i.confidence,
                    "rule_id": i.rule_id,
                }
                for i in self.issues
            ],
            "summary": self.summary,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 静态规则引擎
# ---------------------------------------------------------------------------
# 规则列表: (规则ID, 正则表达式, 严重级别, 描述, 建议, 置信度)
RULES = [
    (
        "R001",
        r"\bexcept\s*:",
        "中",
        "裸 except 捕获所有异常，可能隐藏错误。",
        "建议改为 except Exception 或更具体的异常类型。",
        0.80,
    ),
    (
        "R002",
        r"\bprint\s*\(",
        "低",
        "使用 print 输出，可能残留调试代码。",
        "建议使用日志模块（logging）替代 print。",
        0.60,
    ),
    (
        "R003",
        r"\beval\s*\(",
        "高",
        "使用 eval 执行动态代码，存在安全风险。",
        "避免使用 eval，改用 ast.literal_eval 或安全解析方案。",
        0.90,
    ),
    (
        "R004",
        r"\bexec\s*\(",
        "高",
        "使用 exec 执行动态代码，存在安全风险。",
        "避免使用 exec，重构为安全的函数调用。",
        0.90,
    ),
    (
        "R005",
        r"\bpassword\s*=",
        "中",
        "检测到密码赋值，注意敏感信息泄露风险。",
        "使用环境变量或密钥管理服务存储密码。",
        0.70,
    ),
    (
        "R006",
        r"\bTODO\b",
        "低",
        "发现 TODO 标记，存在未完成的工作。",
        "确认 TODO 项是否完成，或建立跟踪机制。",
        0.50,
    ),
]


def _apply_rules(source: str, start_line: int = 1) -> List[ReviewIssue]:
    """对源码片段应用规则，返回问题列表。"""
    issues = []
    lines = source.splitlines()
    for rule_id, pattern, severity, desc, sug, conf in RULES:
        regex = re.compile(pattern)
        for offset, line in enumerate(lines, start=start_line):
            if regex.search(line):
                issues.append(
                    ReviewIssue(
                        severity=severity,
                        line=offset,
                        message=desc,
                        suggestion=sug,
                        confidence=conf,
                        rule_id=rule_id,
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# 解析器：将文本源码拆分为可审查单元
# ---------------------------------------------------------------------------
def _extract_units(source: str) -> List[ReviewUnit]:
    """提取函数、类定义作为审查单元，并附带模块级规则扫描。"""
    units = []
    lines = source.splitlines()
    # 识别函数和类定义行
    pattern = re.compile(r"^(?P<indent>\s*)(?:def|class)\s+(?P<name>\w+)\s*[\(:]")
    current_unit = None
    unit_start = 0
    for idx, line in enumerate(lines, start=1):
        m = pattern.match(line)
        if m:
            # 结束上一个单元
            if current_unit is not None:
                current_unit.end_line = idx - 1
                current_unit.source = "\n".join(lines[unit_start - 1: idx - 1])
                units.append(current_unit)
            # 开始新单元
            kind = "class" if "class" in line else "function"
            current_unit = ReviewUnit(
                kind=kind,
                name=m.group("name"),
                start_line=idx,
                end_line=idx,  # 临时
            )
            unit_start = idx
    # 处理最后一个单元
    if current_unit is not None:
        current_unit.end_line = len(lines)
        current_unit.source = "\n".join(lines[unit_start - 1:])
        units.append(current_unit)

    # 如果没有找到单元，则整个文件作为一个模块单元
    if not units:
        units.append(
            ReviewUnit(
                kind="module",
                name="<module>",
                start_line=1,
                end_line=len(lines),
                source=source,
            )
        )
    return units


# ---------------------------------------------------------------------------
# 主审查流程
# ---------------------------------------------------------------------------
def review_source(source: str) -> ReviewReport:
    """执行完整审查流程，返回报告对象。"""
    report = ReviewReport()
    units = _extract_units(source)
    report.units = units

    for unit in units:
        # 对每个单元应用规则
        unit_issues = _apply_rules(unit.source, unit.start_line)
        unit.issues = unit_issues
        report.issues.extend(unit_issues)

    # 统计摘要
    total = len(report.issues)
    high = sum(1 for i in report.issues if i.severity == "高")
    medium = sum(1 for i in report.issues if i.severity == "中")
    low = sum(1 for i in report.issues if i.severity == "低")
    report.summary = {
        "total": total,
        "high": high,
        "medium": medium,
        "low": low,
    }
    return report


def review_file(path: str, output_format: str = "markdown") -> str:
    """读取文件并生成报告字符串。"""
    # 检查文件存在
    if not os.path.isfile(path):
        fail("E002", f"文件不存在: {path}")

    # 检查扩展名（简单文本类型判断）
    allowed_ext = {".py", ".js", ".java", ".go", ".c", ".cpp", ".ts", ".txt", ".md"}
    ext = os.path.splitext(path)[1].lower()
    if ext and ext not in allowed_ext:
        fail("E003", f"不支持的文件类型: {ext}")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        fail("E002", f"读取失败: {e}")

    report = review_source(source)

    if output_format == "json":
        return report.to_json()
    elif output_format == "markdown":
        return report.to_markdown()
    else:
        fail("E005", f"未知输出格式: {output_format}")
        return ""  # 不可达


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def selftest() -> None:
    """内置硬编码样例数据，离线验证核心逻辑。"""
    # 样例源码：包含多种规则命中
    sample = """\
import os

def process_data(data):
    password = "secret"
    print("Processing...")
    # TODO: 优化此函数
    try:
        result = eval(data)
    except:
        pass
    return result

class Helper:
    def run(self):
        exec("x = 1")
        return x
"""

    try:
        report = review_source(sample)
    except Exception as e:
        fail("E009", f"规则引擎异常: {e}")

    # 宽松断言：不依赖精确值，只判断区间和存在性
    # 1. 应当识别出单元
    assert len(report.units) >= 2, f"应至少识别2个单元，实际 {len(report.units)}"

    # 2. 应当命中若干条规则（至少包含 eval / exec / password / print / TODO / except）
    rule_ids = {i.rule_id for i in report.issues}
    assert "R001" in rule_ids, "应检测到裸 except"
    assert "R002" in rule_ids, "应检测到 print"
    assert "R003" in rule_ids, "应检测到 eval"
    assert "R004" in rule_ids, "应检测到 exec"
    assert "R005" in rule_ids, "应检测到 password"
    assert "R006" in rule_ids, "应检测到 TODO"

    # 3. 置信度应在合理区间
    for issue in report.issues:
        assert 0.0 <= issue.confidence <= 1.0, f"置信度越界: {issue.confidence}"

    # 4. 严重级别合法
    for issue in report.issues:
        assert issue.severity in ("高", "中", "低"), f"非法级别: {issue.severity}"

    # 5. 摘要统计与问题数一致（宽松比较）
    assert report.summary["total"] == len(report.issues), "摘要总数不一致"
    assert report.summary["high"] >= 2, "高严重级别问题应至少2个（eval/exec）"
    assert report.summary["medium"] >= 1, "中严重级别问题应至少1个"
    assert report.summary["low"] >= 1, "低严重级别问题应至少1个"

    # 6. JSON 输出可用
    try:
        json_str = report.to_json()
        data = json.loads(json_str)
        assert "issues" in data and "summary" in data, "JSON 结构不完整"
    except Exception as e:
        fail("E006", f"JSON 序列化失败: {e}")

    # 7. Markdown 输出可用
    md = report.to_markdown()
    assert "缺陷" in md, "Markdown 报告缺少缺陷标记"

    # 8. 文件读取功能（使用临时文件，不依赖当前工作目录）
    tmp_path = ""
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".py", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(sample)
        md_from_file = review_file(tmp_path, "markdown")
        assert len(md_from_file) > 0, "文件审查结果为空"
        json_from_file = review_file(tmp_path, "json")
        data = json.loads(json_from_file)
        assert data["summary"]["total"] >= 3, "文件审查问题数异常"
    except Exception as e:
        fail("E008", f"临时文件操作失败: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    print("[selftest] 全部断言通过 ✔")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="thundernet-review — 代码审查与缺陷扫描"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="源码文件路径（文本文件）",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认 markdown）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件）",
    )
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    if not args.path:
        fail("E001", "请提供文件路径，或使用 --selftest 运行自检")

    result = review_file(args.path, args.format)
    print(result)


if __name__ == "__main__":
    main()
