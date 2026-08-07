#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security-skill-router: 安全任务路由、审计测试、漏洞评估
版本: 1.1.2
许可: MIT

本脚本根据功能规格独立实现，用于：
1. 对安全任务文本进行自动分类（审计/分析/测试/评估）
2. 根据任务类型匹配工具链与技能包
3. 生成操作流程步骤
4. 关联知识引用（CVE编号等）
5. 输出结构化报告框架

仅用于学习和参考用途。使用前请确保拥有合法授权。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERR_INVALID_INPUT = "E001"        # 输入为空或非字符串
ERR_UNKNOWN_TASK = "E002"         # 无法识别的任务类型
ERR_NO_TOOLCHAIN = "E003"         # 工具链匹配失败
ERR_NO_WORKFLOW = "E004"          # 流程编排失败
ERR_NO_KNOWLEDGE = "E005"         # 知识引用失败
ERR_REPORT_FAIL = "E006"          # 报告生成失败
ERR_CONFIG_MISSING = "E007"       # 配置缺失
ERR_DEPENDENCY = "E008"           # 依赖错误
ERR_SELFTEST_FAIL = "E009"        # 自检失败
ERR_UNKNOWN = "E010"              # 未知错误

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class TaskClassification:
    """任务分类结果"""
    category: str                 # 任务类别: audit/analysis/test/assessment
    confidence: float             # 置信度 0.0-1.0
    matched_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ToolItem:
    """工具项"""
    name: str
    priority: int                 # 优先级，数字越小越优先
    description: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WorkflowStep:
    """流程步骤"""
    step_id: str
    action: str
    description: str
    check_point: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KnowledgeRef:
    """知识引用"""
    ref_type: str                 # cve/kb/best_practice
    ref_id: str
    title: str
    url: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RoutingResult:
    """路由结果"""
    classification: TaskClassification
    toolchain: List[ToolItem]
    workflow: List[WorkflowStep]
    knowledge_refs: List[KnowledgeRef]

    def to_dict(self) -> Dict:
        return {
            "classification": self.classification.to_dict(),
            "toolchain": [t.to_dict() for t in self.toolchain],
            "workflow": [w.to_dict() for w in self.workflow],
            "knowledge_refs": [k.to_dict() for k in self.knowledge_refs],
        }


# ---------------------------------------------------------------------------
# 内置知识库 / 规则配置
# ---------------------------------------------------------------------------

# 任务类型关键词映射
TASK_KEYWORDS: Dict[str, List[str]] = {
    "audit": ["审计", "合规", "等保", "基线", "核查", "audit", "compliance"],
    "analysis": ["分析", "研判", "溯源", "日志", "威胁", "analysis", "forensic"],
    "test": ["测试", "渗透", "漏洞验证", "poc", "exploit", "test", "pentest"],
    "assessment": ["评估", "风险", "漏洞评估", "评分", "cvss", "assessment", "risk"],
}

# 工具链配置 (按任务类型)
TOOLCHAIN_CONFIG: Dict[str, List[Dict]] = {
    "audit": [
        {"name": "Lynis", "priority": 1, "description": "系统审计工具，检查安全配置"},
        {"name": "OpenSCAP", "priority": 2, "description": "合规性扫描，支持CIS基准"},
        {"name": "Nmap", "priority": 3, "description": "网络服务发现与端口扫描"},
        {"name": "checksec", "priority": 4, "description": "检查二进制安全属性"},
    ],
    "analysis": [
        {"name": "Wireshark", "priority": 1, "description": "网络流量分析"},
        {"name": "Volatility", "priority": 2, "description": "内存取证分析"},
        {"name": "grep/awk", "priority": 3, "description": "日志文本处理"},
        {"name": "ELK Stack", "priority": 4, "description": "日志集中分析与可视化"},
    ],
    "test": [
        {"name": "Metasploit", "priority": 1, "description": "渗透测试框架"},
        {"name": "Burp Suite", "priority": 2, "description": "Web应用安全测试"},
        {"name": "sqlmap", "priority": 3, "description": "SQL注入检测"},
        {"name": "Nuclei", "priority": 4, "description": "漏洞模板扫描器"},
    ],
    "assessment": [
        {"name": "Nessus", "priority": 1, "description": "漏洞扫描器"},
        {"name": "OpenVAS", "priority": 2, "description": "开源漏洞评估"},
        {"name": "OWASP Dependency-Check", "priority": 3, "description": "依赖漏洞检查"},
        {"name": "Trivy", "priority": 4, "description": "容器镜像漏洞扫描"},
    ],
}

# 流程模板 (按任务类型)
WORKFLOW_TEMPLATES: Dict[str, List[Dict]] = {
    "audit": [
        {"step_id": "A1", "action": "定义审计范围", "description": "明确审计目标系统、网络边界和合规标准", "check_point": "范围是否获得授权"},
        {"step_id": "A2", "action": "收集配置信息", "description": "获取系统配置、网络拓扑、安全策略文档", "check_point": "信息是否完整"},
        {"step_id": "A3", "action": "执行基线检查", "description": "使用Lynis/OpenSCAP对照安全基线进行核查", "check_point": "不符合项是否记录"},
        {"step_id": "A4", "action": "整理审计发现", "description": "汇总不合规项、风险点，形成审计发现列表", "check_point": "发现是否可追溯"},
        {"step_id": "A5", "action": "生成审计报告", "description": "输出审计报告，包含发现、风险等级、整改建议", "check_point": "报告是否经复核"},
    ],
    "analysis": [
        {"step_id": "N1", "action": "确定分析目标", "description": "明确分析对象（日志、流量、内存镜像）和问题", "check_point": "目标是否明确"},
        {"step_id": "N2", "action": "数据采集", "description": "收集相关日志、流量或内存数据", "check_point": "数据是否完整"},
        {"step_id": "N3", "action": "数据预处理", "description": "清洗数据、提取关键字段、格式化", "check_point": "数据是否可用"},
        {"step_id": "N4", "action": "深度分析", "description": "使用分析工具挖掘异常行为、攻击痕迹", "check_point": "是否发现可疑线索"},
        {"step_id": "N5", "action": "形成分析结论", "description": "整理分析结果，输出事件时间线和结论", "check_point": "结论是否有证据支持"},
    ],
    "test": [
        {"step_id": "T1", "action": "确认授权", "description": "核实测试目标的书面授权，明确测试边界", "check_point": "授权书是否有效"},
        {"step_id": "T2", "action": "信息收集", "description": "使用被动/主动方式收集目标信息", "check_point": "信息是否充分"},
        {"step_id": "T3", "action": "漏洞探测", "description": "使用扫描器与手工方式探测漏洞", "check_point": "漏洞是否复现"},
        {"step_id": "T4", "action": "漏洞验证", "description": "对发现的漏洞进行验证，确认可利用性", "check_point": "验证结果是否准确"},
        {"step_id": "T5", "action": "输出测试报告", "description": "编写渗透测试报告，含漏洞详情和修复建议", "check_point": "报告是否涵盖所有发现"},
    ],
    "assessment": [
        {"step_id": "R1", "action": "资产识别", "description": "识别目标资产、网络拓扑、系统组件", "check_point": "资产清单是否完整"},
        {"step_id": "R2", "action": "威胁建模", "description": "分析潜在威胁源、攻击向量和影响", "check_point": "威胁模型是否合理"},
        {"step_id": "R3", "action": "漏洞扫描", "description": "使用漏洞扫描器对目标进行扫描", "check_point": "扫描结果是否有效"},
        {"step_id": "R4", "action": "风险评估", "description": "结合CVSS评分和业务影响评估风险等级", "check_point": "风险评级是否准确"},
        {"step_id": "R5", "action": "输出评估报告", "description": "生成风险评估报告，包含风险矩阵和处置建议", "check_point": "报告是否含优先级"},
    ],
}

# 知识引用配置 (按任务类型)
KNOWLEDGE_CONFIG: Dict[str, List[Dict]] = {
    "audit": [
        {"ref_type": "best_practice", "ref_id": "CIS-Benchmark", "title": "CIS 安全配置基准", "url": "https://www.cisecurity.org/cis-benchmarks/"},
        {"ref_type": "kb", "ref_id": "ISO-27001", "title": "ISO/IEC 27001 信息安全管理体系", "url": "https://www.iso.org/isoiec-27001-information-security.html"},
        {"ref_type": "kb", "ref_id": "MLPS", "title": "中国网络安全等级保护基本要求", "url": "https://www.mps.gov.cn/"},
    ],
    "analysis": [
        {"ref_type": "kb", "ref_id": "ATT-CK", "title": "MITRE ATT&CK 战术与技术知识库", "url": "https://attack.mitre.org/"},
        {"ref_type": "kb", "ref_id": "NIST-SP800-61", "title": "NIST SP 800-61 计算机安全事件处理指南", "url": "https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final"},
        {"ref_type": "cve", "ref_id": "CVE-2021-44228", "title": "Apache Log4j2 远程代码执行漏洞", "url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"},
    ],
    "test": [
        {"ref_type": "best_practice", "ref_id": "OWASP-Top10", "title": "OWASP Top 10 Web应用安全风险", "url": "https://owasp.org/www-project-top-ten/"},
        {"ref_type": "kb", "ref_id": "PTES", "title": "渗透测试执行标准", "url": "http://www.pentest-standard.org/"},
        {"ref_type": "cve", "ref_id": "CVE-2017-0144", "title": "MS17-010 EternalBlue SMB远程代码执行", "url": "https://nvd.nist.gov/vuln/detail/CVE-2017-0144"},
    ],
    "assessment": [
        {"ref_type": "kb", "ref_id": "CVSS-v3", "title": "通用漏洞评分系统 v3.1", "url": "https://www.first.org/cvss/"},
        {"ref_type": "kb", "ref_id": "NIST-SP800-30", "title": "NIST SP 800-30 风险评估指南", "url": "https://csrc.nist.gov/publications/detail/sp/800-30/rev-1/final"},
        {"ref_type": "kb", "ref_id": "ISO-31000", "title": "ISO 31000 风险管理原则与实施指南", "url": "https://www.iso.org/iso-31000-risk-management.html"},
    ],
}


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------

def classify_task(task_text: str) -> TaskClassification:
    """
    对任务文本进行分类，返回分类结果和置信度。

    分类策略：
    1. 对每个类别统计关键词命中数
    2. 命中最多关键词的类别为最终分类
    3. 置信度 = 该类命中数 / 总命中数 (若总命中数为0则置信度为0)
    """
    if not task_text or not isinstance(task_text, str):
        raise ValueError(f"{ERR_INVALID_INPUT}: 任务文本必须为非空字符串")

    # 统一转小写进行匹配
    text_lower = task_text.lower()
    category_hits: Dict[str, List[str]] = {}

    for category, keywords in TASK_KEYWORDS.items():
        hits = []
        for kw in keywords:
            # 关键词匹配（中文直接匹配，英文单词边界匹配）
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text_lower) or kw.lower() in text_lower:
                hits.append(kw)
        if hits:
            category_hits[category] = hits

    if not category_hits:
        # 无任何关键词命中，返回最低置信度的审计分类
        return TaskClassification(
            category="audit",
            confidence=0.0,
            matched_keywords=[]
        )

    # 找出命中关键词最多的类别
    best_category = max(category_hits, key=lambda k: len(category_hits[k]))
    best_hits = len(category_hits[best_category])
    total_hits = sum(len(hits) for hits in category_hits.values())

    # 置信度计算：该类命中数/总命中数，并考虑命中类别数量的影响
    confidence = best_hits / total_hits if total_hits > 0 else 0.0
    # 如果多个类别命中数相同，降低置信度
    same_count = sum(1 for hits in category_hits.values() if len(hits) == best_hits)
    if same_count > 1:
        confidence *= 0.8

    return TaskClassification(
        category=best_category,
        confidence=round(confidence, 4),
        matched_keywords=category_hits[best_category]
    )


def match_toolchain(category: str) -> List[ToolItem]:
    """根据任务类别匹配工具链"""
    if category not in TOOLCHAIN_CONFIG:
        raise ValueError(f"{ERR_NO_TOOLCHAIN}: 未知的任务类别 '{category}'")

    tools = []
    for item in TOOLCHAIN_CONFIG[category]:
        tools.append(ToolItem(**item))
    return tools


def generate_workflow(category: str) -> List[WorkflowStep]:
    """根据任务类别生成操作流程"""
    if category not in WORKFLOW_TEMPLATES:
        raise ValueError(f"{ERR_NO_WORKFLOW}: 未知的任务类别 '{category}'")

    steps = []
    for item in WORKFLOW_TEMPLATES[category]:
        steps.append(WorkflowStep(**item))
    return steps


def get_knowledge_refs(category: str) -> List[KnowledgeRef]:
    """获取知识引用"""
    if category not in KNOWLEDGE_CONFIG:
        raise ValueError(f"{ERR_NO_KNOWLEDGE}: 未知的任务类别 '{category}'")

    refs = []
    for item in KNOWLEDGE_CONFIG[category]:
        refs.append(KnowledgeRef(**item))
    return refs


def route_security_task(task_text: str) -> RoutingResult:
    """
    安全任务路由主函数：分类 -> 工具链 -> 流程 -> 知识引用

    参数:
        task_text: 用户输入的安全任务描述

    返回:
        RoutingResult: 包含分类、工具链、流程、知识引用的完整结果

    异常:
        ValueError: 输入无效或处理过程中出现错误
    """
    try:
        # 1. 任务分类
        classification = classify_task(task_text)

        # 2. 工具链匹配
        toolchain = match_toolchain(classification.category)

        # 3. 流程编排
        workflow = generate_workflow(classification.category)

        # 4. 知识引用
        knowledge_refs = get_knowledge_refs(classification.category)

        # 5. 组装结果
        result = RoutingResult(
            classification=classification,
            toolchain=toolchain,
            workflow=workflow,
            knowledge_refs=knowledge_refs
        )
        return result

    except ValueError as e:
        # 透传已定义的错误码
        raise
    except Exception as e:
        raise RuntimeError(f"{ERR_UNKNOWN}: 路由过程中发生未知错误: {str(e)}")


def format_report(result: RoutingResult) -> str:
    """
    将路由结果格式化为可读的报告文本

    参数:
        result: 路由结果

    返回:
        格式化后的报告字符串
    """
    try:
        lines = []
        lines.append("=" * 60)
        lines.append("安全任务路由报告")
        lines.append("=" * 60)

        # 分类信息
        lines.append(f"\n[任务分类]")
        lines.append(f"  类别: {result.classification.category}")
        lines.append(f"  置信度: {result.classification.confidence:.1%}")
        if result.classification.matched_keywords:
            lines.append(f"  命中关键词: {', '.join(result.classification.matched_keywords)}")

        # 工具链
        lines.append(f"\n[推荐工具链]")
        for tool in result.toolchain:
            lines.append(f"  {tool.priority}. {tool.name} - {tool.description}")

        # 操作流程
        lines.append(f"\n[操作流程]")
        for step in result.workflow:
            lines.append(f"  [{step.step_id}] {step.action}")
            lines.append(f"       {step.description}")
            if step.check_point:
                lines.append(f"       检查点: {step.check_point}")

        # 知识引用
        lines.append(f"\n[知识引用]")
        for ref in result.knowledge_refs:
            ref_type_display = {
                "cve": "CVE漏洞",
                "kb": "知识库",
                "best_practice": "最佳实践"
            }.get(ref.ref_type, ref.ref_type)
            lines.append(f"  - [{ref_type_display}] {ref.ref_id}: {ref.title}")
            if ref.url:
                lines.append(f"    参考: {ref.url}")

        lines.append("\n" + "=" * 60)
        lines.append("注意: 本报告由AI辅助生成，仅供学习参考。")
        lines.append("实际安全操作需由持证专业人员执行，并确保已获得授权。")
        lines.append("=" * 60)

        return "\n".join(lines)

    except Exception as e:
        raise RuntimeError(f"{ERR_REPORT_FAIL}: 报告生成失败: {str(e)}")


# ---------------------------------------------------------------------------
# 自检功能 (--selftest)
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置自检程序，使用离线样例数据验证核心逻辑。

    返回:
        True 表示所有测试通过，否则抛出异常或返回 False
    """
    print("开始自检...")

    # 测试用例
    test_cases = [
        {
            "input": "对生产服务器进行安全审计，检查是否符合等保三级要求",
            "expected_category": "audit",
            "min_confidence": 0.5,
        },
        {
            "input": "分析防火墙日志，追溯最近一次入侵事件的攻击路径",
            "expected_category": "analysis",
            "min_confidence": 0.5,
        },
        {
            "input": "对Web应用进行渗透测试，验证是否存在SQL注入漏洞",
            "expected_category": "test",
            "min_confidence": 0.5,
        },
        {
            "input": "对内部网络进行风险评估，识别关键资产和潜在威胁",
            "expected_category": "assessment",
            "min_confidence": 0.5,
        },
    ]

    # 1. 测试分类功能
    print("\n[1] 测试任务分类...")
    for i, case in enumerate(test_cases, 1):
        try:
            result = route_security_task(case["input"])
            actual_category = result.classification.category
            confidence = result.classification.confidence

            assert actual_category == case["expected_category"], \
                f"用例{i}失败: 期望类别 '{case['expected_category']}', 实际 '{actual_category}'"
            assert confidence >= case["min_confidence"], \
                f"用例{i}失败: 置信度 {confidence} 低于阈值 {case['min_confidence']}"

            print(f"  ✓ 用例{i}: 分类为 '{actual_category}' (置信度: {confidence:.1%})")
        except Exception as e:
            print(f"  ✗ 用例{i}失败: {str(e)}")
            raise

    # 2. 测试工具链完整性
    print("\n[2] 测试工具链匹配...")
    categories = ["audit", "analysis", "test", "assessment"]
    for cat in categories:
        try:
            tools = match_toolchain(cat)
            assert len(tools) > 0, f"类别 '{cat}' 工具链为空"
            # 验证优先级排序
            priorities = [t.priority for t in tools]
            assert priorities == sorted(priorities), f"类别 '{cat}' 工具优先级未排序"
            print(f"  ✓ 类别 '{cat}': {len(tools)}个工具, 优先级正确")
        except Exception as e:
            print(f"  ✗ 类别 '{cat}' 工具链测试失败: {str(e)}")
            raise

    # 3. 测试流程生成
    print("\n[3] 测试流程生成...")
    for cat in categories:
        try:
            steps = generate_workflow(cat)
            assert len(steps) >= 3, f"类别 '{cat}' 流程步骤过少"
            # 验证步骤ID唯一性
            step_ids = [s.step_id for s in steps]
            assert len(step_ids) == len(set(step_ids)), f"类别 '{cat}' 存在重复步骤ID"
            print(f"  ✓ 类别 '{cat}': {len(steps)}个步骤, ID唯一")
        except Exception as e:
            print(f"  ✗ 类别 '{cat}' 流程测试失败: {str(e)}")
            raise

    # 4. 测试知识引用
    print("\n[4] 测试知识引用...")
    for cat in categories:
        try:
            refs = get_knowledge_refs(cat)
            assert len(refs) >= 2, f"类别 '{cat}' 知识引用过少"
            print(f"  ✓ 类别 '{cat}': {len(refs)}条引用")
        except Exception as e:
            print(f"  ✗ 类别 '{cat}' 知识引用测试失败: {str(e)}")
            raise

    # 5. 测试报告生成
    print("\n[5] 测试报告生成...")
    try:
        sample_result = route_security_task("对Web服务器进行安全审计")
        report = format_report(sample_result)
        assert len(report) > 100, "报告内容过短"
        assert "安全任务路由报告" in report, "报告缺少标题"
        print(f"  ✓ 报告生成成功 ({len(report)}字符)")
    except Exception as e:
        print(f"  ✗ 报告生成测试失败: {str(e)}")
        raise

    # 6. 测试边界情况
    print("\n[6] 测试边界情况...")
    try:
        # 空输入
        try:
            classify_task("")
            print("  ✗ 空输入未抛出异常")
            raise AssertionError("空输入应抛出异常")
        except ValueError:
            print("  ✓ 空输入正确处理")

        # 无关键词输入
        result = route_security_task("你好世界")
        assert result.classification.confidence == 0.0, "无关键词输入置信度应为0"
        print("  ✓ 无关键词输入正确处理")

        # 混合输入（多类别关键词）
        result = route_security_task("进行安全审计和渗透测试")
        assert result.classification.category in ["audit", "test"], "混合输入应归类到任一命中类别"
        print(f"  ✓ 混合输入归类为 '{result.classification.category}'")

    except Exception as e:
        print(f"  ✗ 边界测试失败: {str(e)}")
        raise

    # 7. 测试错误处理
    print("\n[7] 测试错误处理...")
    try:
        # 无效类别
        try:
            match_toolchain("invalid_category")
            print("  ✗ 无效类别未抛出异常")
            raise AssertionError("无效类别应抛出异常")
        except ValueError as e:
            assert str(e).startswith(ERR_NO_TOOLCHAIN), "错误码不正确"
            print("  ✓ 无效类别错误处理正确")

        # 无效输入类型
        try:
            classify_task(12345)  # type: ignore
            print("  ✗ 非字符串输入未抛出异常")
            raise AssertionError("非字符串输入应抛出异常")
        except ValueError as e:
            assert str(e).startswith(ERR_INVALID_INPUT), "错误码不正确"
            print("  ✓ 非字符串输入错误处理正确")

    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {str(e)}")
        raise

    print("\n" + "=" * 60)
    print("自检全部通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="安全任务路由工具 - 自动匹配工具链、生成操作流程与知识引用",
        epilog="示例: python main.py \"对Web应用进行渗透测试\""
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="安全任务描述文本"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出结果"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.1.2"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"自检失败: {str(e)}", file=sys.stderr)
            return 1

    # 需要任务文本
    if not args.task:
        parser.print_help()
        print("\n错误: 必须提供任务描述或使用 --selftest", file=sys.stderr)
        return 1

    try:
        # 执行路由
        result = route_security_task(args.task)

        # 输出结果
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(format_report(result))

        return 0

    except ValueError as e:
        print(f"错误 ({e})", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"错误 ({e})", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期的错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
