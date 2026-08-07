#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security-skill-router 独立实现
================================
按安全任务类型自动匹配工具链与技能包，生成操作流程与知识引用。

本脚本为 clean-room 实现，仅依据功能规格独立编写。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python main.py --task 渗透测试 --target "内网 192.168.1.0/24"
    python main.py --selftest
"""

import argparse
import sys
import re
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# 常量定义（错误码）
# ---------------------------------------------------------------------------
ERR_SUCCESS = 0
ERR_INVALID_ARGS = "E001"       # 参数缺失或非法
ERR_UNKNOWN_TASK = "E002"       # 无法识别的任务类型
ERR_EMPTY_TARGET = "E003"       # 目标范围为空
ERR_INTERNAL = "E004"           # 内部逻辑错误
ERR_SELFTEST_FAIL = "E005"      # 自检失败
ERR_OUTPUT_FAIL = "E006"        # 输出失败
ERR_UNSUPPORTED = "E007"        # 不支持的请求


# ---------------------------------------------------------------------------
# 任务类型定义（关键词 → 任务分类）
# ---------------------------------------------------------------------------
# 注意：更具体的关键词应该放在前面，避免被通用关键词提前匹配
TASK_KEYWORDS: Dict[str, str] = {
    # 渗透测试相关（优先匹配）
    "渗透测试": "penetration_test",
    "渗透": "penetration_test",
    "pentest": "penetration_test",
    
    # 安全审计相关
    "安全审计": "security_audit",
    "审计": "security_audit",
    "audit": "security_audit",
    
    # 漏洞评估相关
    "漏洞评估": "vuln_assessment",
    "漏洞": "vuln_assessment",
    "vuln": "vuln_assessment",
    
    # 安全测试相关
    "安全测试": "security_test",
    "测试": "security_test",
    "test": "security_test",
    
    # 安全分析相关
    "安全分析": "security_analysis",
    "分析": "security_analysis",
    "analysis": "security_analysis",
    
    # 安全巡检相关
    "安全巡检": "security_inspection",
    "巡检": "security_inspection",
    "inspection": "security_inspection",
    
    # 风险核查相关
    "风险核查": "risk_check",
    "风险": "risk_check",
    "risk": "risk_check",
}

# 任务类型 → 工具链推荐
TOOLCHAIN: Dict[str, List[str]] = {
    "security_audit": ["Nmap", "OpenVAS", "Lynis", "Nikto"],
    "security_analysis": ["Wireshark", "tcpdump", "Metasploit", "Burp Suite"],
    "security_test": ["Nmap", "Nikto", "Burp Suite", "OWASP ZAP"],
    "vuln_assessment": ["Nessus", "OpenVAS", "Nmap", "SearchSploit"],
    "penetration_test": ["Nmap", "Metasploit", "Burp Suite", "Hydra", "sqlmap"],
    "security_inspection": ["Lynis", "ClamAV", "chkrootkit", "Nmap"],
    "risk_check": ["OpenVAS", "Nessus", "Nmap", "OWASP Dependency-Check"],
}

# 任务类型 → 标准操作流程（步骤列表）
WORKFLOW: Dict[str, List[str]] = {
    "security_audit": [
        "信息收集：确认目标系统类型、版本、开放端口",
        "配置审计：检查系统安全配置基线",
        "漏洞扫描：使用工具链进行自动扫描",
        "验证分析：人工复核扫描结果，排除误报",
        "报告输出：整理发现项与整改建议",
    ],
    "security_analysis": [
        "流量采集：抓取目标网络流量",
        "协议分析：识别异常协议与行为",
        "威胁建模：关联已知攻击特征",
        "深入取证：对可疑会话进行深度分析",
        "报告输出：输出分析结论与证据链",
    ],
    "security_test": [
        "范围确认：明确测试边界与规则",
        "信息收集：子域、IP、端口枚举",
        "漏洞探测：自动化扫描与手工验证",
        "利用验证：在授权范围内验证漏洞",
        "报告输出：输出测试结果与修复建议",
    ],
    "vuln_assessment": [
        "资产识别：列出目标资产清单",
        "漏洞扫描：使用漏洞扫描器全面扫描",
        "风险评级：按 CVSS 进行风险分级",
        "验证复核：确认高危漏洞真实性",
        "报告输出：输出漏洞清单与修复优先级",
    ],
    "penetration_test": [
        "授权确认：核对测试授权与范围",
        "信息收集：被动与主动信息收集",
        "漏洞分析：识别可利用漏洞",
        "渗透利用：在授权范围内尝试突破",
        "后渗透：评估影响范围（可选）",
        "报告输出：输出渗透测试报告",
    ],
    "security_inspection": [
        "基线检查：核对安全配置基线",
        "恶意软件扫描：查杀病毒与后门",
        "日志审计：检查异常登录与操作",
        "合规检查：核对合规要求",
        "报告输出：输出巡检报告",
    ],
    "risk_check": [
        "资产盘点：梳理关键资产",
        "威胁识别：识别潜在威胁源",
        "脆弱性分析：评估弱点与漏洞",
        "风险计算：结合影响与可能性",
        "报告输出：输出风险评估报告",
    ],
}

# 任务类型 → 知识引用（漏洞库/标准）
KNOWLEDGE_REF: Dict[str, List[str]] = {
    "security_audit": ["CIS Benchmarks", "ISO 27001", "OWASP Top 10"],
    "security_analysis": ["OWASP Top 10", "CWE", "ATT&CK 框架"],
    "security_test": ["OWASP Testing Guide", "PTES", "CWE"],
    "vuln_assessment": ["CVE 数据库", "CVSS v3.1", "NVD"],
    "penetration_test": ["PTES", "OWASP Testing Guide", "OSSTMM"],
    "security_inspection": ["CIS Controls", "等保 2.0", "ISO 27001"],
    "risk_check": ["ISO 31000", "NIST SP 800-30", "CVSS v3.1"],
}

# 风险提示模板
RISK_NOTICE = (
    "⚠️ 风险提示：所有测试操作必须在获得明确授权后进行。"
    "本工具仅提供流程与工具建议，不自动执行任何命令。"
    "非法使用产生的后果由使用者自行承担。"
)


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------
def classify_task(user_input: str) -> Tuple[bool, str]:
    """
    根据用户输入文本识别任务类型。

    返回: (是否识别成功, 任务类型标识)
    """
    if not user_input or not user_input.strip():
        return False, ""

    text = user_input.strip().lower()
    
    # 优先匹配更具体的关键词
    # 按关键词长度降序排序，确保更长的关键词先匹配
    sorted_keywords = sorted(TASK_KEYWORDS.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword.lower() in text:
            return True, TASK_KEYWORDS[keyword]

    # 尝试语义匹配（宽松规则）
    if "渗透" in text or "pentest" in text:
        return True, "penetration_test"
    if "审计" in text or "audit" in text:
        return True, "security_audit"
    if "漏洞" in text or "vuln" in text:
        return True, "vuln_assessment"
    if "巡检" in text or "inspection" in text:
        return True, "security_inspection"
    if "风险" in text or "risk" in text:
        return True, "risk_check"
    if "测试" in text or "test" in text:
        return True, "security_test"
    if "分析" in text or "analysis" in text:
        return True, "security_analysis"

    return False, ""


def validate_target(target: str) -> Tuple[bool, str]:
    """
    校验目标范围是否合法（非空且包含基本网络标识）。

    返回: (是否合法, 规范化后的目标)
    """
    if not target or not target.strip():
        return False, ""

    target = target.strip()
    # 宽松校验：包含点号或斜杠（IP/域名/网段）即可认为有效
    if "." in target or "/" in target or ":" in target:
        return True, target
    # 允许纯主机名形式（如 localhost）
    if re.match(r"^[a-zA-Z0-9\-_]+$", target):
        return True, target
    return False, target


def build_plan(task_type: str, target: str) -> Dict:
    """
    根据任务类型与目标生成完整执行计划。

    返回: 包含工具链、流程、知识引用的字典。
    """
    if task_type not in TOOLCHAIN:
        raise ValueError(f"{ERR_UNKNOWN_TASK}: 未知任务类型 {task_type}")

    return {
        "task_type": task_type,
        "target": target,
        "tools": TOOLCHAIN.get(task_type, []),
        "workflow": WORKFLOW.get(task_type, []),
        "knowledge": KNOWLEDGE_REF.get(task_type, []),
        "risk_notice": RISK_NOTICE,
    }


def format_plan(plan: Dict) -> str:
    """
    将执行计划格式化为可读文本输出。
    """
    lines = []
    lines.append("=" * 60)
    lines.append("🔐 安全任务执行计划")
    lines.append("=" * 60)
    lines.append(f"📋 任务类型: {plan['task_type']}")
    lines.append(f"🎯 目标范围: {plan['target']}")
    lines.append("")
    lines.append("🛠️  推荐工具链:")
    for i, tool in enumerate(plan["tools"], 1):
        lines.append(f"   {i}. {tool}")
    lines.append("")
    lines.append("📝 操作流程:")
    for i, step in enumerate(plan["workflow"], 1):
        lines.append(f"   {i}. {step}")
    lines.append("")
    lines.append("📚 知识引用:")
    for ref in plan["knowledge"]:
        lines.append(f"   • {ref}")
    lines.append("")
    lines.append(f"{plan['risk_notice']}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。
    不依赖外部文件、网络或当前工作目录。

    返回: 自检是否通过
    """
    print("[自检] 开始执行离线自检...")

    # 测试用例 1: 任务分类（渗透测试）
    ok, task_type = classify_task("我想做一次渗透测试")
    if not ok or task_type != "penetration_test":
        print(f"[自检失败] 任务分类错误: {task_type}")
        return False
    print("[自检通过] 任务分类: 渗透测试")

    # 测试用例 2: 任务分类（安全审计）
    ok, task_type = classify_task("请帮我做安全审计")
    if not ok or task_type != "security_audit":
        print(f"[自检失败] 任务分类错误: {task_type}")
        return False
    print("[自检通过] 任务分类: 安全审计")

    # 测试用例 3: 无效输入
    ok, _ = classify_task("")
    if ok:
        print("[自检失败] 空输入不应识别成功")
        return False
    print("[自检通过] 空输入正确拒绝")

    # 测试用例 4: 目标校验
    ok, _ = validate_target("192.168.1.0/24")
    if not ok:
        print("[自检失败] 合法网段被拒绝")
        return False
    print("[自检通过] 目标校验: 网段格式")

    ok, _ = validate_target("")
    if ok:
        print("[自检失败] 空目标不应通过")
        return False
    print("[自检通过] 空目标正确拒绝")

    # 测试用例 5: 计划生成完整性
    plan = build_plan("penetration_test", "192.168.1.0/24")
    if not plan["tools"] or not plan["workflow"] or not plan["knowledge"]:
        print("[自检失败] 计划生成不完整")
        return False
    if len(plan["tools"]) < 3:
        print("[自检失败] 工具链过短")
        return False
    if len(plan["workflow"]) < 3:
        print("[自检失败] 流程步骤过少")
        return False
    print("[自检通过] 计划生成完整")

    # 测试用例 6: 所有任务类型均可生成计划
    for task in TOOLCHAIN.keys():
        try:
            p = build_plan(task, "test-target")
            if not p["tools"] or not p["workflow"]:
                print(f"[自检失败] 任务类型 {task} 计划不完整")
                return False
        except Exception as e:
            print(f"[自检失败] 任务类型 {task} 异常: {e}")
            return False
    print("[自检通过] 所有任务类型计划生成正常")

    # 测试用例 7: 输出格式化
    fmt = format_plan(plan)
    if "渗透测试" not in fmt and "penetration_test" not in fmt:
        print("[自检失败] 输出格式缺少任务信息")
        return False
    if "风险提示" not in fmt and "⚠️" not in fmt:
        print("[自检失败] 输出格式缺少风险提示")
        return False
    print("[自检通过] 输出格式化正常")

    # 测试用例 8: 边界输入（模糊表述应拒绝）
    ok, _ = classify_task("帮我看看系统")
    if ok:
        print("[自检失败] 模糊表述不应识别成功")
        return False
    print("[自检通过] 模糊表述正确拒绝")

    # 测试用例 9: 其他具体任务类型识别
    test_cases = [
        ("进行漏洞扫描", "vuln_assessment"),
        ("做安全巡检", "security_inspection"),
        ("评估一下风险", "risk_check"),
        ("帮我做个安全测试", "security_test"),
        ("分析一下网络流量", "security_analysis"),
    ]
    for input_text, expected in test_cases:
        ok, task_type = classify_task(input_text)
        if not ok or task_type != expected:
            print(f"[自检失败] 任务分类错误: {input_text} → {task_type} (期望 {expected})")
            return False
        print(f"[自检通过] 任务分类: {input_text} → {task_type}")

    print("[自检] 全部自检项通过 ✅")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    主入口函数。

    返回: 退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="安全任务路由与工具链编排工具",
        epilog="示例: %(prog)s --task 渗透测试 --target 192.168.1.0/24",
    )
    parser.add_argument(
        "--task",
        type=str,
        help="安全任务描述（如：渗透测试、安全审计、漏洞评估）",
    )
    parser.add_argument(
        "--target",
        type=str,
        help="目标范围（如：192.168.1.0/24、example.com）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="列出支持的任务类型",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            result = run_selftest()
            return 0 if result else 1
        except Exception as e:
            print(f"[错误 {ERR_SELFTEST_FAIL}] 自检异常: {e}")
            return 1

    # 列出任务类型
    if args.list_tasks:
        print("支持的任务类型:")
        for keyword, task in TASK_KEYWORDS.items():
            print(f"  {keyword} → {task}")
        return 0

    # 参数校验
    if not args.task:
        print(f"[错误 {ERR_INVALID_ARGS}] 缺少 --task 参数（可加 --selftest 自检）")
        return 1

    # 任务分类
    ok, task_type = classify_task(args.task)
    if not ok:
        print(
            f"[错误 {ERR_UNKNOWN_TASK}] 无法识别任务类型: '{args.task}'\n"
            "  请使用明确的任务描述（如：渗透测试、安全审计、漏洞评估）"
        )
        return 1

    # 目标校验
    if not args.target:
        print(f"[错误 {ERR_EMPTY_TARGET}] 缺少 --target 参数")
        return 1

    ok, target = validate_target(args.target)
    if not ok:
        print(f"[错误 {ERR_EMPTY_TARGET}] 目标格式无效: '{args.target}'")
        return 1

    # 生成并输出计划
    try:
        plan = build_plan(task_type, target)
        output = format_plan(plan)
        print(output)
        return 0
    except Exception as e:
        print(f"[错误 {ERR_INTERNAL}] 生成计划失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
