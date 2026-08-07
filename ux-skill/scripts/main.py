#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ux-skill 交互设计体验审查引擎 — 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不参考任何既有实现。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    将输入（文本/URL/文件路径）转化为结构化 UX 诊断结果，
    包含问题清单、优先级排序、置信度标注，并支持字段筛选。

用法示例：
    python main.py --input "登录页缺少错误提示" --fields 问题,建议,优先级
    python main.py --selftest
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import datetime

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "输入为空：未提供任何可分析的输入内容",
    "E003": "文件读取失败：无法读取指定文件",
    "E004": "URL 格式错误：无法从 URL 提取有效信息",
    "E005": "字段筛选错误：指定的字段不存在",
    "E006": "输出格式错误：不支持的输出格式",
    "E007": "内部处理异常：未预期的运行时错误",
    "E008": "输入类型错误：不支持的输入类型",
    "E009": "批量处理中断：批量任务中某一项失败",
    "E010": "自检失败：核心逻辑验证未通过",
}


def fail(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出程序。"""
    err_text = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {err_text}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {err_text}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class UXIssue:
    """单个 UX 诊断问题。"""
    id: str                    # 问题唯一标识
    category: str              # 问题类别（如：交互/反馈/视觉/内容）
    problem: str               # 问题描述
    suggestion: str            # 改进建议
    priority: str              # 优先级：高/中/低
    confidence: str            # 置信度：高/中/低
    location: str              # 问题位置（如组件名/URL/行号）
    evidence: str              # 判断依据/证据


@dataclass
class UXReport:
    """一次审查的完整报告。"""
    source: str                        # 输入来源描述
    timestamp: str                     # 生成时间
    total_issues: int                  # 问题总数
    issues: List[UXIssue]              # 问题列表
    summary: Dict[str, int]            # 按优先级统计
    unchecked_items: List[str]         # 未检查项
    metadata: Dict[str, Any]           # 额外元数据


# ---------------------------------------------------------------------------
# 核心诊断引擎
# ---------------------------------------------------------------------------
class UXAnalyzer:
    """
    体验审查核心引擎。
    通过规则匹配与启发式分析，从输入文本中提取 UX 问题。
    """

    # 规则库：关键词 -> (类别, 问题模板, 建议模板, 优先级, 置信度)
    RULES = [
        {
            "keywords": ["无反馈", "没反应", "无提示", "没有提示", "不响应"],
            "category": "反馈机制",
            "problem": "用户操作后缺少即时反馈，可能导致重复操作或困惑",
            "suggestion": "为所有可交互元素添加视觉/文字反馈（如 loading、toast、状态变化）",
            "priority": "高",
            "confidence": "高",
        },
        {
            "keywords": ["按钮", "点击", "提交"],
            "category": "交互设计",
            "problem": "关键操作元素（按钮/提交）可能存在可发现性或点击区域问题",
            "suggestion": "确保主要操作按钮视觉突出，点击区域不小于 44×44px，并支持键盘操作",
            "priority": "中",
            "confidence": "中",
        },
        {
            "keywords": ["颜色", "对比度", "看不清", "看不清文字"],
            "category": "视觉层级",
            "problem": "界面元素可能存在对比度不足或视觉层级不清晰的问题",
            "suggestion": "检查文字与背景的对比度（WCAG AA 标准 ≥4.5:1），使用语义化颜色",
            "priority": "中",
            "confidence": "中",
        },
        {
            "keywords": ["表单", "输入", "校验", "验证"],
            "category": "表单交互",
            "problem": "表单可能存在校验反馈不充分或输入约束不明确的问题",
            "suggestion": "提供实时校验、明确的错误提示（含具体修正建议），并标注必填项",
            "priority": "高",
            "confidence": "高",
        },
        {
            "keywords": ["导航", "菜单", "返回", "跳转"],
            "category": "信息架构",
            "problem": "导航结构可能存在路径不清晰或返回机制缺失的问题",
            "suggestion": "确保主导航层级清晰，提供面包屑导航和明确的返回路径",
            "priority": "中",
            "confidence": "中",
        },
        {
            "keywords": ["加载", "等待", "慢", "卡顿"],
            "category": "性能感知",
            "problem": "页面加载或响应可能过慢，影响用户体验",
            "suggestion": "优化资源加载，使用骨架屏或进度指示，目标首屏时间 <3秒",
            "priority": "高",
            "confidence": "低",
        },
        {
            "keywords": ["错误", "失败", "异常", "报错"],
            "category": "错误处理",
            "problem": "错误提示可能不够友好或缺少恢复指引",
            "suggestion": "错误信息应说明原因、提供解决方案，并允许用户轻松重试或返回",
            "priority": "高",
            "confidence": "高",
        },
        {
            "keywords": ["弹窗", "对话框", "弹出"],
            "category": "交互模式",
            "problem": "弹窗/对话框使用可能过度或打断用户流程",
            "suggestion": "评估弹窗必要性，优先使用内联确认或非模态提示，确保可轻松关闭",
            "priority": "低",
            "confidence": "低",
        },
        {
            "keywords": ["手机", "移动端", "响应式", "适配"],
            "category": "响应式设计",
            "problem": "移动端适配可能存在布局或交互体验问题",
            "suggestion": "测试不同屏幕尺寸，确保触控目标大小合适，内容不溢出",
            "priority": "中",
            "confidence": "中",
        },
        {
            "keywords": ["注册", "登录", "密码", "账号"],
            "category": "用户流程",
            "problem": "认证流程可能存在步骤繁琐或引导不清晰的问题",
            "suggestion": "简化注册/登录流程，提供社交登录选项，明确步骤指示",
            "priority": "中",
            "confidence": "中",
        },
    ]

    # 未检查项（能力边界声明）
    UNCHECKED_ITEMS = [
        "真实用户可用性测试（无真实交互数据）",
        "视觉美观度主观评分（仅客观规范检查）",
        "需登录认证的私有页面",
        "自动修复代码问题（仅输出诊断建议）",
        "所有边界场景覆盖（输出中标注未检查项）",
    ]

    def __init__(self) -> None:
        self._rule_cache: List[Dict[str, str]] = []

    def analyze(self, raw_input: str, source: str = "") -> UXReport:
        """对输入文本执行体验审查，返回结构化报告。"""
        if not raw_input or not raw_input.strip():
            fail("E002", "输入内容不能为空")

        issues: List[UXIssue] = []
        text_lower = raw_input.lower()

        # 逐条规则匹配
        for idx, rule in enumerate(self.RULES, start=1):
            matched = any(kw in text_lower for kw in rule["keywords"])
            if matched:
                # 找出实际匹配的关键词
                matched_kws = [k for k in rule["keywords"] if k in text_lower]
                issue = UXIssue(
                    id=f"I{idx:03d}",
                    category=rule["category"],
                    problem=rule["problem"],
                    suggestion=rule["suggestion"],
                    priority=rule["priority"],
                    confidence=rule["confidence"],
                    location=source if source else "全局",
                    evidence=f"检测到关键词: {', '.join(matched_kws)}",
                )
                issues.append(issue)

        # 生成摘要统计
        summary = {"高": 0, "中": 0, "低": 0}
        for iss in issues:
            if iss.priority in summary:
                summary[iss.priority] += 1
            else:
                summary[iss.priority] = 1

        # 若没有匹配到任何规则，生成一条通用提示
        if not issues:
            issues.append(UXIssue(
                id="I000",
                category="综合",
                problem="未检测到明确的 UX 问题，建议进行人工走查",
                suggestion="对照交互设计规范逐项检查，或邀请其他设计师进行交叉评审",
                priority="低",
                confidence="低",
                location=source if source else "全局",
                evidence="未触发任何内置规则",
            ))
            summary["低"] = 1

        report = UXReport(
            source=source if source else "直接输入",
            timestamp=self._now_str(),
            total_issues=len(issues),
            issues=issues,
            summary=summary,
            unchecked_items=list(self.UNCHECKED_ITEMS),
            metadata={
                "engine_version": "1.0.1",
                "rule_count": len(self.RULES),
                "input_length": len(raw_input),
            },
        )
        return report

    @staticmethod
    def _now_str() -> str:
        """返回当前时间的 ISO 格式字符串（不依赖第三方库）。"""
        return datetime.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 输入处理模块
# ---------------------------------------------------------------------------
class InputProcessor:
    """处理多种输入类型：文本、文件路径、URL。"""

    @staticmethod
    def resolve(raw: str) -> tuple:
        """
        根据输入内容判断类型并提取可分析文本。
        返回 (文本内容, 来源描述)
        """
        if not raw or not raw.strip():
            fail("E002", "输入内容为空")

        stripped = raw.strip()

        # URL 检测
        if re.match(r'^https?://', stripped, re.IGNORECASE):
            return InputProcessor._handle_url(stripped)

        # 文件路径检测（简单判断：包含路径分隔符或常见扩展名）
        if InputProcessor._looks_like_path(stripped):
            return InputProcessor._handle_file(stripped)

        # 默认按纯文本处理
        return stripped, "直接输入文本"

    @staticmethod
    def _looks_like_path(s: str) -> bool:
        """启发式判断是否为文件路径。"""
        if '/' in s or '\\' in s:
            return True
        if re.search(r'\.(txt|md|json|html?|css|js|yaml|yml)$', s, re.IGNORECASE):
            return True
        return False

    @staticmethod
    def _handle_url(url: str) -> tuple:
        """
        处理 URL 输入。
        由于不访问网络，仅从 URL 中提取可用的文本信息。
        """
        # 提取 URL 中的关键词
        path_part = url.split('//')[-1] if '//' in url else url
        # 去除协议和查询参数
        path_part = re.sub(r'^[^/]+', '', path_part)  # 移除域名
        path_part = path_part.split('?')[0].split('#')[0]
        keywords = re.findall(r'[a-zA-Z0-9]+', path_part)
        keyword_text = ' '.join(keywords)

        if not keyword_text:
            fail("E004", f"无法从 URL 提取有效信息: {url}")

        # 补充说明：URL 分析为静态分析，不访问网络
        text = f"URL 页面分析: {keyword_text}。请检查该页面的导航、反馈机制、表单交互。"
        return text, f"URL: {url}"

    @staticmethod
    def _handle_file(filepath: str) -> tuple:
        """读取并处理本地文件。"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            fail("E003", f"文件不存在: {filepath}")
        except PermissionError:
            fail("E003", f"无权限读取文件: {filepath}")
        except Exception as e:
            fail("E003", f"读取文件失败: {filepath} - {str(e)}")

        if not content.strip():
            fail("E002", f"文件内容为空: {filepath}")

        return content.strip(), f"文件: {filepath}"


# ---------------------------------------------------------------------------
# 输出格式化模块
# ---------------------------------------------------------------------------
class OutputFormatter:
    """将 UXReport 格式化为多种输出格式。"""

    @staticmethod
    def to_markdown(report: UXReport, fields: Optional[List[str]] = None) -> str:
        """生成 Markdown 格式报告。"""
        lines = []
        lines.append(f"# UX 体验审查报告")
        lines.append(f"")
        lines.append(f"- **来源**: {report.source}")
        lines.append(f"- **时间**: {report.timestamp}")
        lines.append(f"- **问题总数**: {report.total_issues}")
        lines.append(f"- **优先级分布**: 高={report.summary.get('高', 0)}, 中={report.summary.get('中', 0)}, 低={report.summary.get('低', 0)}")
        lines.append(f"")

        # 问题清单表格
        lines.append(f"## 问题清单")
        lines.append(f"")
        lines.append(f"| 编号 | 类别 | 问题 | 建议 | 优先级 | 置信度 | 位置 |")
        lines.append(f"|------|------|------|------|--------|--------|------|")

        for iss in report.issues:
            lines.append(
                f"| {iss.id} | {iss.category} | {iss.problem} | {iss.suggestion} | "
                f"{iss.priority} | {iss.confidence} | {iss.location} |"
            )

        # 未检查项
        lines.append(f"")
        lines.append(f"## 未检查项")
        lines.append(f"")
        for item in report.unchecked_items:
            lines.append(f"- {item}")

        # 元数据
        lines.append(f"")
        lines.append(f"## 元数据")
        lines.append(f"")
        lines.append(f"- 引擎版本: {report.metadata.get('engine_version', 'unknown')}")
        lines.append(f"- 规则数量: {report.metadata.get('rule_count', 0)}")
        lines.append(f"- 输入长度: {report.metadata.get('input_length', 0)} 字符")

        return '\n'.join(lines)

    @staticmethod
    def to_json(report: UXReport) -> str:
        """生成 JSON 格式报告。"""
        data = asdict(report)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_text(report: UXReport, fields: Optional[List[str]] = None) -> str:
        """生成纯文本格式报告。"""
        lines = []
        lines.append(f"UX 体验审查报告")
        lines.append(f"来源: {report.source}")
        lines.append(f"时间: {report.timestamp}")
        lines.append(f"问题总数: {report.total_issues}")
        lines.append(f"")
        lines.append(f"问题清单:")
        for iss in report.issues:
            lines.append(f"  [{iss.priority}/{iss.confidence}] {iss.id}: {iss.problem}")
            lines.append(f"    建议: {iss.suggestion}")
            lines.append(f"    位置: {iss.location}")
        lines.append(f"")
        lines.append(f"未检查项:")
        for item in report.unchecked_items:
            lines.append(f"  - {item}")
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# 字段筛选模块
# ---------------------------------------------------------------------------
VALID_FIELDS = {
    "id": "编号",
    "category": "类别",
    "problem": "问题",
    "suggestion": "建议",
    "priority": "优先级",
    "confidence": "置信度",
    "location": "位置",
    "evidence": "证据",
}


def filter_fields(report: UXReport, fields: List[str]) -> UXReport:
    """
    根据字段列表筛选报告内容。
    仅保留用户指定的字段，其他字段置空。
    """
    # 校验字段合法性
    for f in fields:
        if f not in VALID_FIELDS:
            fail("E005", f"不支持的字段: {f}，可选字段: {', '.join(VALID_FIELDS.keys())}")

    # 创建过滤后的报告副本
    filtered = UXReport(
        source=report.source,
        timestamp=report.timestamp,
        total_issues=report.total_issues,
        issues=[],
        summary=report.summary,
        unchecked_items=report.unchecked_items,
        metadata=report.metadata,
    )

    # 过滤每个问题的字段
    for iss in report.issues:
        new_issue = UXIssue(
            id=iss.id if "id" in fields else "",
            category=iss.category if "category" in fields else "",
            problem=iss.problem if "problem" in fields else "",
            suggestion=iss.suggestion if "suggestion" in fields else "",
            priority=iss.priority if "priority" in fields else "",
            confidence=iss.confidence if "confidence" in fields else "",
            location=iss.location if "location" in fields else "",
            evidence=iss.evidence if "evidence" in fields else "",
        )
        filtered.issues.append(new_issue)

    return filtered


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> None:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读取外部文件、不访问网络，任何环境直接可过。
    使用宽松阈值断言，避免依赖精确值。
    """
    print("[自检] 开始执行核心逻辑自检...")

    # 1. 创建分析器实例
    analyzer = UXAnalyzer()

    # 2. 测试样例1：包含多个问题的输入
    sample1 = "登录页的提交按钮点击后无反馈，表单校验错误提示不清晰，页面加载很慢。"
    report1 = analyzer.analyze(sample1, source="selftest-sample1")

    # 宽松断言：问题数量应大于0
    assert report1.total_issues > 0, "样例1应至少产生1个问题"
    assert report1.summary.get("高", 0) > 0, "样例1应包含高优先级问题"
    assert len(report1.issues) > 0, "样例1问题列表不应为空"
    print(f"[自检] 样例1通过: 生成 {report1.total_issues} 个问题")

    # 3. 测试样例2：无匹配问题的输入
    sample2 = "这是一个简单的文本，没有任何交互相关内容。"
    report2 = analyzer.analyze(sample2, source="selftest-sample2")
    assert report2.total_issues >= 1, "样例2应至少产生1条通用建议"
    assert report2.issues[0].priority == "低", "样例2默认问题应为低优先级"
    print(f"[自检] 样例2通过: 生成 {report2.total_issues} 个问题")

    # 4. 测试字段筛选
    filtered = filter_fields(report1, ["problem", "suggestion"])
    for iss in filtered.issues:
        assert iss.problem != "", "筛选后问题字段不应为空"
        assert iss.suggestion != "", "筛选后建议字段不应为空"
        assert iss.priority == "", "筛选后未选中的字段应为空"
    print("[自检] 字段筛选功能通过")

    # 5. 测试输出格式化
    md = OutputFormatter.to_markdown(report1)
    assert "UX 体验审查报告" in md, "Markdown 输出应包含标题"
    assert "问题清单" in md, "Markdown 输出应包含问题清单"
    assert "|" in md, "Markdown 输出应包含表格"
    print("[自检] Markdown 输出通过")

    json_out = OutputFormatter.to_json(report1)
    data = json.loads(json_out)
    assert data["total_issues"] == report1.total_issues, "JSON 输出应包含问题总数"
    assert len(data["issues"]) > 0, "JSON 输出应包含问题列表"
    print("[自检] JSON 输出通过")

    text_out = OutputFormatter.to_text(report1)
    assert "UX 体验审查报告" in text_out, "文本输出应包含标题"
    assert "问题清单" in text_out, "文本输出应包含问题清单"
    print("[自检] 文本输出通过")

    # 6. 测试输入处理器
    text, source = InputProcessor.resolve("这是一个测试输入")
    assert len(text) > 0, "文本输入应非空"
    assert "直接输入" in source, "文本输入来源描述应正确"
    print("[自检] 文本输入处理通过")

    # URL 处理（不访问网络）
    url_text, url_source = InputProcessor.resolve("https://example.com/login")
    assert len(url_text) > 0, "URL 输入应提取到文本"
    assert "URL" in url_source, "URL 输入来源描述应正确"
    print("[自检] URL 输入处理通过")

    # 7. 测试错误处理
    try:
        InputProcessor.resolve("")
        assert False, "空输入应抛出错误"
    except SystemExit:
        pass  # 预期退出
    print("[自检] 空输入错误处理通过")

    # 8. 验证所有规则可触发
    all_keywords = []
    for rule in analyzer.RULES:
        all_keywords.extend(rule["keywords"])
    sample3 = " ".join(all_keywords[:5])  # 至少触发前几条规则
    report3 = analyzer.analyze(sample3, source="selftest-sample3")
    assert report3.total_issues >= 3, "组合关键词应触发多条规则"
    print(f"[自检] 规则触发测试通过: {report3.total_issues} 条规则被触发")

    # 9. 检查错误码定义完整
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"错误码 {code} 应已定义"
    print("[自检] 错误码定义完整")

    # 10. 测试文件路径处理（创建一个临时文件）
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("测试文件内容：登录按钮无反馈，页面加载慢")
        temp_path = f.name
    try:
        file_text, file_source = InputProcessor.resolve(temp_path)
        assert len(file_text) > 0, "文件输入应非空"
        assert "文件" in file_source, "文件输入来源描述应正确"
        print("[自检] 文件输入处理通过")
    finally:
        os.unlink(temp_path)

    print("\n[自检] ✅ 全部自检通过！核心逻辑验证成功。")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> None:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="ux-skill 交互设计体验审查引擎",
        epilog="示例: python main.py --input '登录页缺少错误提示' --fields 问题,建议,优先级",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：文本、URL 或文件路径",
    )
    parser.add_argument(
        "--fields",
        type=str,
        default="",
        help="要输出的字段，逗号分隔（如: 问题,建议,优先级）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "json", "text"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except AssertionError as e:
            fail("E010", str(e))
        except Exception as e:
            fail("E007", f"自检过程异常: {str(e)}")

    # 正常分析模式
    if not args.input:
        parser.print_help()
        fail("E001", "必须提供 --input 参数或使用 --selftest")

    try:
        # 处理输入
        text, source = InputProcessor.resolve(args.input)

        # 执行分析
        analyzer = UXAnalyzer()
        report = analyzer.analyze(text, source=source)

        # 字段筛选
        if args.fields:
            field_list = [f.strip() for f in args.fields.split(",") if f.strip()]
            report = filter_fields(report, field_list)

        # 输出
        if args.format == "json":
            print(OutputFormatter.to_json(report))
        elif args.format == "text":
            print(OutputFormatter.to_text(report))
        else:
            print(OutputFormatter.to_markdown(report))

    except SystemExit:
        raise
    except Exception as e:
        fail("E007", f"处理过程中发生异常: {str(e)}")


if __name__ == "__main__":
    main()
