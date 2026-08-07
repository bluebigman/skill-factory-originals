#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security-skill-router
安全任务路由与工具链编排（Clean-Room 独立实现）

功能：
- 根据安全任务类型自动匹配工具链与技能包
- 生成结构化操作流程
- 输出知识引用与风险提示
- 支持 --selftest 离线自检
"""

import argparse
import sys
import json
from typing import Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# E001: 参数错误
# E002: 任务类型为空
# E003: 目标范围为空
# E004: 未知任务类型
# E005: 自检失败
# E006: 内部数据异常
# E007: 输出格式错误
# E008: 输入类型错误
# E009: 工具链匹配失败
# E010: 未知错误
# ============================================================

# ============================================================
# 内置知识库（硬编码数据，不依赖外部文件）
# ============================================================

# 任务类型分类表
TASK_CATEGORIES: Dict[str, str] = {
    "安全审计": "audit",
    "审计": "audit",
    "安全分析": "analysis",
    "分析": "analysis",
    "安全测试": "testing",
    "测试": "testing",
    "漏洞评估": "vulnerability",
    "漏洞": "vulnerability",
    "渗透测试": "pentest",
    "渗透": "pentest",
    "安全巡检": "inspection",
    "巡检": "inspection",
    "风险核查": "risk_check",
    "风险": "risk_check",
}

# 任务类型 → 工具链映射
TOOLCHAINS: Dict[str, Dict] = {
    "audit": {
        "name": "安全审计工具链",
        "tools": ["Nmap", "OpenVAS", "Wireshark", "Nessus"],
        "description": "用于系统安全配置审计与合规检查",
        "phases": ["信息收集", "配置核查", "漏洞扫描", "合规比对", "报告生成"],
    },
    "analysis": {
        "name": "安全分析工具链",
        "tools": ["Wireshark", "tcpdump", "Sysinternals", "Volatility"],
        "description": "用于日志分析、流量分析与取证分析",
        "phases": ["数据采集", "日志分析", "流量分析", "异常检测", "结论输出"],
    },
    "testing": {
        "name": "安全测试工具链",
        "tools": ["Burp Suite", "OWASP ZAP", "sqlmap", "curl"],
        "description": "用于Web应用与API安全测试",
        "phases": ["目标确认", "指纹识别", "漏洞探测", "验证利用", "修复建议"],
    },
    "vulnerability": {
        "name": "漏洞评估工具链",
        "tools": ["Nessus", "OpenVAS", "Nmap", "Metasploit"],
        "description": "用于系统与网络漏洞评估",
        "phases": ["资产识别", "漏洞扫描", "风险分级", "验证复现", "评估报告"],
    },
    "pentest": {
        "name": "渗透测试工具链",
        "tools": ["Nmap", "Metasploit", "Burp Suite", "Hydra", "sqlmap"],
        "description": "用于模拟攻击的渗透测试",
        "phases": ["信息收集", "端口扫描", "漏洞利用", "权限提升", "痕迹清理", "报告"],
    },
    "inspection": {
        "name": "安全巡检工具链",
        "tools": ["Nmap", "Lynis", "chkrootkit", "ClamAV"],
        "description": "用于日常安全巡检与基线核查",
        "phases": ["基线检查", "补丁核查", "恶意软件扫描", "日志审查", "巡检报告"],
    },
    "risk_check": {
        "name": "风险核查工具链",
        "tools": ["Nmap", "OpenVAS", "Nessus", "OWASP ZAP"],
        "description": "用于安全风险识别与核查",
        "phases": ["风险识别", "影响评估", "可能性分析", "风险定级", "处置建议"],
    },
}

# 知识引用库（CVE / OWASP 参考）
KNOWLEDGE_REFERENCES: Dict[str, List[str]] = {
    "audit": [
        "CIS Benchmarks: https://www.cisecurity.org/cis-benchmarks/",
        "ISO 27001: https://www.iso.org/standard/27001",
    ],
    "analysis": [
        "OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html",
        "CVE-2021-44228 (Log4Shell): https://nvd.nist.gov/vuln/detail/CVE-2021-44228",
    ],
    "testing": [
        "OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/",
        "CVE-2017-5638 (Struts2 RCE): https://nvd.nist.gov/vuln/detail/CVE-2017-5638",
    ],
    "vulnerability": [
        "CVE-2023-27350: https://nvd.nist.gov/vuln/detail/CVE-2023-27350",
        "OWASP Top 10: https://owasp.org/www-project-top-ten/",
    ],
    "pentest": [
        "PTES Standard: http://www.pentest-standard.org/",
        "CVE-2020-1472 (Zerologon): https://nvd.nist.gov/vuln/detail/CVE-2020-1472",
    ],
    "inspection": [
        "CIS Controls: https://www.cisecurity.org/controls/",
        "NIST SP 800-53: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
    ],
    "risk_check": [
        "NIST SP 800-30: https://csrc.nist.gov/publications/detail/sp/800-30/rev-1/final",
        "ISO 31000: https://www.iso.org/iso-31000-risk-management.html",
    ],
}

# 风险提示模板
RISK_NOTICES: Dict[str, List[str]] = {
    "audit": [
        "审计操作需获得系统所有者书面授权",
        "扫描可能影响生产环境性能，建议在维护窗口执行",
        "审计结果仅反映特定时间点的安全状态",
    ],
    "analysis": [
        "日志分析可能涉及个人隐私数据，需遵守相关法规",
        "流量捕获可能包含敏感信息，注意数据脱敏",
        "分析结论需结合业务上下文综合判断",
    ],
    "testing": [
        "测试前必须获得目标系统明确授权",
        "漏洞验证需避免对生产数据造成破坏",
        "测试活动可能触发安全告警，提前通知相关团队",
    ],
    "vulnerability": [
        "漏洞扫描可能影响服务可用性，建议在低峰期进行",
        "扫描结果需人工复核，避免误报",
        "高危漏洞需立即通知相关责任人",
    ],
    "pentest": [
        "渗透测试必须签署正式授权协议",
        "测试范围严格限定于授权目标",
        "测试过程需全程记录，保留证据链",
        "禁止在未授权情况下进行横向渗透",
    ],
    "inspection": [
        "巡检操作应避免中断业务服务",
        "发现的异常需及时上报并跟踪闭环",
        "巡检记录应妥善保存，作为合规依据",
    ],
    "risk_check": [
        "风险评估需结合资产价值与威胁情报",
        "风险处置措施需平衡成本与效益",
        "风险等级需定期复核与更新",
    ],
}


def classify_task(task_input: str) -> Optional[str]:
    """
    根据用户输入识别任务类型
    返回内部任务类型标识，无法识别时返回 None
    """
    if not task_input or not isinstance(task_input, str):
        return None

    # 先尝试精确匹配
    task_trimmed = task_input.strip()
    if task_trimmed in TASK_CATEGORIES:
        return TASK_CATEGORIES[task_trimmed]

    # 再尝试包含匹配（宽松匹配）
    for keyword, category in TASK_CATEGORIES.items():
        if keyword in task_input:
            return category

    return None


def build_workflow(task_type: str, target: str, constraints: str = "") -> Dict:
    """
    构建完整的安全任务工作流
    返回结构化任务清单
    """
    if task_type not in TOOLCHAINS:
        raise ValueError("未知任务类型")

    toolchain = TOOLCHAINS[task_type]
    references = KNOWLEDGE_REFERENCES.get(task_type, [])
    risks = RISK_NOTICES.get(task_type, [])

    workflow = {
        "task_type": task_type,
        "task_name": toolchain["name"],
        "description": toolchain["description"],
        "target": target,
        "constraints": constraints,
        "tools": toolchain["tools"],
        "phases": toolchain["phases"],
        "knowledge_references": references,
        "risk_notices": risks,
    }

    return workflow


def format_workflow(workflow: Dict, format_type: str = "text") -> str:
    """
    将工作流格式化为文本或JSON输出
    """
    if format_type == "json":
        return json.dumps(workflow, ensure_ascii=False, indent=2)

    # 文本格式输出
    lines = []
    lines.append("=" * 60)
    lines.append(f"🔐 安全任务工作流 - {workflow['task_name']}")
    lines.append("=" * 60)
    lines.append(f"📋 任务类型: {workflow['task_type']}")
    lines.append(f"🎯 目标范围: {workflow['target']}")
    if workflow["constraints"]:
        lines.append(f"⚠️  约束条件: {workflow['constraints']}")
    lines.append(f"📝 描述: {workflow['description']}")
    lines.append("")
    lines.append("🛠️  工具链:")
    for tool in workflow["tools"]:
        lines.append(f"  - {tool}")
    lines.append("")
    lines.append("📌 操作流程:")
    for i, phase in enumerate(workflow["phases"], 1):
        lines.append(f"  {i}. {phase}")
    lines.append("")
    lines.append("📚 知识引用:")
    for ref in workflow["knowledge_references"]:
        lines.append(f"  - {ref}")
    lines.append("")
    lines.append("⚠️  风险提示:")
    for risk in workflow["risk_notices"]:
        lines.append(f"  - {risk}")
    lines.append("=" * 60)

    return "\n".join(lines)


def validate_inputs(task_input: str, target: str) -> Tuple[bool, str]:
    """
    输入校验
    返回 (是否有效, 错误信息)
    """
    if not task_input or not task_input.strip():
        return False, "任务类型不能为空 (错误码: E002)"

    if not target or not target.strip():
        return False, "目标范围不能为空 (错误码: E003)"

    return True, ""


def process_request(task_input: str, target: str, constraints: str = "", output_format: str = "text") -> str:
    """
    处理安全任务路由请求
    返回格式化结果
    """
    # 输入校验
    valid, error_msg = validate_inputs(task_input, target)
    if not valid:
        return error_msg

    # 任务分类
    task_type = classify_task(task_input)
    if task_type is None:
        return f"无法识别任务类型，请明确指定（审计/分析/测试/漏洞/渗透/巡检/风险）(错误码: E004)"

    # 构建工作流
    try:
        workflow = build_workflow(task_type, target.strip(), constraints.strip())
    except ValueError as e:
        return f"工作流构建失败: {str(e)} (错误码: E009)"
    except Exception:
        return f"内部数据异常 (错误码: E006)"

    # 格式化输出
    try:
        result = format_workflow(workflow, output_format)
    except Exception:
        return f"输出格式化失败 (错误码: E007)"

    return result


def run_selftest() -> bool:
    """
    内置自检逻辑
    使用硬编码样例数据，不依赖外部文件、网络或当前目录
    """
    print("🔍 开始自检 (selftest)...")
    print("-" * 60)

    # 测试样例数据
    test_cases = [
        # (任务输入, 目标范围, 约束条件, 期望任务类型)
        ("渗透测试", "192.168.1.0/24", "仅限周末凌晨执行", "pentest"),
        ("安全审计", "公司内部网络", "", "audit"),
        ("漏洞评估", "生产服务器", "需提前通知", "vulnerability"),
        ("安全巡检", "全部业务系统", "", "inspection"),
        ("风险核查", "核心资产", "", "risk_check"),
        ("安全分析", "日志系统", "保留证据链", "analysis"),
        ("安全测试", "Web应用", "", "testing"),
    ]

    # 测试计数器
    passed = 0
    total = 5  # 共5组测试

    # 测试1: 任务分类正确性
    print("\n[测试1] 任务分类")
    classification_ok = True
    for task_input, _, _, _ in test_cases:
        result_type = classify_task(task_input)
        if result_type is None:
            print(f"  ❌ 分类失败: '{task_input}' 返回 None")
            classification_ok = False
        elif result_type not in TOOLCHAINS:
            print(f"  ❌ 未知类型: '{task_input}' -> {result_type}")
            classification_ok = False
        else:
            print(f"  ✅ '{task_input}' -> {result_type}")

    if classification_ok:
        passed += 1
        print("  ✅ 分类测试通过")
    else:
        print("  ❌ 分类测试失败")

    # 测试2: 工作流构建
    print("\n[测试2] 工作流构建")
    workflow_ok = True
    for task_input, target, constraints, _ in test_cases:
        task_type = classify_task(task_input)
        if task_type is None:
            continue
        try:
            workflow = build_workflow(task_type, target, constraints)
            if not workflow.get("tools"):
                print(f"  ❌ 工具链为空: {task_input}")
                workflow_ok = False
            elif not workflow.get("phases"):
                print(f"  ❌ 流程为空: {task_input}")
                workflow_ok = False
            elif not workflow.get("target"):
                print(f"  ❌ 目标为空: {task_input}")
                workflow_ok = False
            else:
                print(f"  ✅ {task_input}: {len(workflow['tools'])}个工具, {len(workflow['phases'])}个阶段")
        except Exception as e:
            print(f"  ❌ 构建异常: {task_input} - {str(e)}")
            workflow_ok = False

    if workflow_ok:
        passed += 1
        print("  ✅ 工作流构建测试通过")
    else:
        print("  ❌ 工作流构建测试失败")

    # 测试3: 完整请求处理
    print("\n[测试3] 完整请求处理")
    process_ok = True
    for task_input, target, constraints, _ in test_cases:
        result = process_request(task_input, target, constraints)
        if not result:
            print(f"  ❌ 请求处理返回空: {task_input}")
            process_ok = False
        elif "错误码" in result:
            print(f"  ❌ 请求处理报错: {task_input} -> {result[:50]}...")
            process_ok = False
        else:
            print(f"  ✅ {task_input}: 输出长度 {len(result)} 字符")

    if process_ok:
        passed += 1
        print("  ✅ 请求处理测试通过")
    else:
        print("  ❌ 请求处理测试失败")

    # 测试4: 边界情况
    print("\n[测试4] 边界情况")
    edge_ok = True

    # 空任务类型
    result = process_request("", "192.168.1.1")
    if "E002" in result:
        print("  ✅ 空任务类型正确报错 E002")
    else:
        print(f"  ❌ 空任务类型未报错: {result}")
        edge_ok = False

    # 空目标范围
    result = process_request("渗透测试", "")
    if "E003" in result:
        print("  ✅ 空目标范围正确报错 E003")
    else:
        print(f"  ❌ 空目标范围未报错: {result}")
        edge_ok = False

    # 未知任务类型
    result = process_request("帮我看看系统", "192.168.1.1")
    if "E004" in result:
        print("  ✅ 未知任务类型正确报错 E004")
    else:
        print(f"  ❌ 未知任务类型未报错: {result}")
        edge_ok = False

    # JSON输出格式
    result = process_request("渗透测试", "192.168.1.1", "", "json")
    try:
        json.loads(result)
        print("  ✅ JSON输出格式有效")
    except (json.JSONDecodeError, TypeError):
        print(f"  ❌ JSON输出格式无效: {result[:50]}...")
        edge_ok = False

    if edge_ok:
        passed += 1
        print("  ✅ 边界情况测试通过")
    else:
        print("  ❌ 边界情况测试失败")

    # 测试5: 数据完整性
    print("\n[测试5] 数据完整性")
    data_ok = True
    for task_type in TOOLCHAINS:
        if task_type not in KNOWLEDGE_REFERENCES:
            print(f"  ❌ 缺少知识引用: {task_type}")
            data_ok = False
        if task_type not in RISK_NOTICES:
            print(f"  ❌ 缺少风险提示: {task_type}")
            data_ok = False
        if len(TOOLCHAINS[task_type].get("tools", [])) < 1:
            print(f"  ❌ 工具链为空: {task_type}")
            data_ok = False
        if len(TOOLCHAINS[task_type].get("phases", [])) < 1:
            print(f"  ❌ 流程为空: {task_type}")
            data_ok = False

    if data_ok:
        passed += 1
        print("  ✅ 数据完整性测试通过")
    else:
        print("  ❌ 数据完整性测试失败")

    # 总结
    print("-" * 60)
    print(f"📊 自检结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("✅ 全部自检通过！")
        return True
    else:
        print(f"❌ 自检失败 (错误码: E005)")
        return False


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="安全任务路由与工具链编排工具",
        epilog="示例: python main.py --task '渗透测试' --target '192.168.1.0/24'"
    )
    parser.add_argument("--task", "-t", help="安全任务类型（审计/分析/测试/漏洞/渗透/巡检/风险）")
    parser.add_argument("--target", help="目标范围，如 '192.168.1.0/24' 或 '公司内网'")
    parser.add_argument("--constraints", "-c", default="", help="约束条件（可选），如 '仅限周末执行'")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常模式
    if not args.task or not args.target:
        parser.print_help()
        print("\n错误: 缺少必要参数 --task 或 --target (错误码: E001)")
        sys.exit(1)

    result = process_request(args.task, args.target, args.constraints, args.format)
    print(result)

    # 检查是否有错误码
    if "错误码" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
