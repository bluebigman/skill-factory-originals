#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security-skill-router 独立实现

按安全任务类型自动匹配工具链与技能包，生成操作流程与知识引用。
本脚本为 clean-room 实现，仅依据功能规格独立编写，不包含任何既有代码。

用法:
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --task "渗透测试 Web 应用"  # 路由示例
"""

import argparse
import sys
import re
from typing import Dict, List, Tuple, Optional

# 错误码定义
# E001: 参数错误
# E002: 任务类型无法识别
# E003: 目标环境无法识别
# E004: 授权信息缺失
# E005: 内部数据异常
# E006: 输入为空
# E007: 输出生成失败
# E008: 自检失败
# E009: 文件操作失败
# E010: 未知错误

# ---------------------------------------------------------------------------
# 核心数据定义（内置知识库）
# ---------------------------------------------------------------------------

# 任务类型关键词映射表 - 使用更精确的关键词避免歧义
TASK_KEYWORDS: Dict[str, List[str]] = {
    "安全审计": ["审计", "audit", "合规检查", "合规"],
    "安全分析": ["分析", "analysis", "研判", "威胁分析"],
    "安全测试": ["安全测试", "security test", "漏洞扫描", "vulnerability scan", "安全检测"],
    "漏洞评估": ["漏洞评估", "vulnerability assessment", "风险评估", "风险"],
    "渗透测试": ["渗透测试", "渗透", "penetration", "pentest", "攻防"],
    "安全巡检": ["巡检", "inspection", "日常检查", "定期检查"],
    "安全加固": ["加固", "hardening", "修复", "整改"],
}

# 工具链推荐表（按任务类型）
TOOLCHAIN_MAP: Dict[str, List[str]] = {
    "安全审计": ["Nessus", "OpenSCAP", "Lynis", "审计日志分析工具"],
    "安全分析": ["Wireshark", "tcpdump", "ELK Stack", "MISP"],
    "安全测试": ["Burp Suite", "OWASP ZAP", "sqlmap", "Nmap"],
    "漏洞评估": ["Nessus", "OpenVAS", "Qualys", "CVEdetails"],
    "渗透测试": ["Metasploit", "Burp Suite", "Nmap", "sqlmap", "John the Ripper"],
    "安全巡检": ["Nagios", "Zabbix", "OSSEC", "Tripwire"],
    "安全加固": ["CIS Benchmarks", "OpenSCAP", "Ansible", "Lynis"],
}

# 流程模板（按任务类型）
PROCESS_TEMPLATES: Dict[str, List[str]] = {
    "安全审计": [
        "1. 确定审计范围与合规标准",
        "2. 收集系统配置与日志信息",
        "3. 执行配置基线对比",
        "4. 生成审计报告并标注不合规项",
    ],
    "安全分析": [
        "1. 收集网络流量或日志数据",
        "2. 识别异常行为模式",
        "3. 关联威胁情报进行研判",
        "4. 输出分析结论与建议",
    ],
    "安全测试": [
        "1. 确认授权与测试范围",
        "2. 信息收集（域名、端口、服务）",
        "3. 漏洞扫描与验证",
        "4. 输出测试报告",
    ],
    "漏洞评估": [
        "1. 定义资产与评估范围",
        "2. 使用扫描器进行漏洞发现",
        "3. 漏洞验证与风险评级",
        "4. 输出风险评估报告",
    ],
    "渗透测试": [
        "1. 获得书面授权",
        "2. 信息收集与侦察",
        "3. 漏洞利用与权限提升",
        "4. 痕迹清理与报告输出",
    ],
    "安全巡检": [
        "1. 执行常规安全检查项",
        "2. 检查系统日志与告警",
        "3. 验证安全配置有效性",
        "4. 输出巡检记录",
    ],
    "安全加固": [
        "1. 识别系统薄弱点",
        "2. 应用安全加固策略",
        "3. 验证加固效果",
        "4. 更新配置文档",
    ],
}

# 知识引用表（按任务类型）
KNOWLEDGE_REFERENCES: Dict[str, List[str]] = {
    "安全审计": ["ISO 27001", "NIST SP 800-53", "CIS Controls"],
    "安全分析": ["MITRE ATT&CK", "OWASP Threat Modeling", "SANS Reading Room"],
    "安全测试": ["OWASP Testing Guide", "PTES Standard", "WASC Threat Classification"],
    "漏洞评估": ["CVE Database", "NVD", "CVSS v3.1"],
    "渗透测试": ["PTES", "OSSTMM", "OWASP Testing Guide"],
    "安全巡检": ["CIS Benchmarks", "NIST SP 800-137", "ISO 27002"],
    "安全加固": ["CIS Benchmarks", "NIST SP 800-123", "OWASP ASVS"],
}

# 授权检查关键词
AUTHORIZATION_KEYWORDS: List[str] = ["授权", "授权书", "书面授权", "测试范围", "authorized", "permission"]

# 目标环境关键词
ENVIRONMENT_KEYWORDS: Dict[str, List[str]] = {
    "Web应用": ["web", "网站", "网页", "http", "https", "浏览器"],
    "移动应用": ["移动", "app", "android", "ios", "手机"],
    "网络设备": ["路由器", "交换机", "防火墙", "网络设备", "cisco", "huawei"],
    "云环境": ["云", "aws", "azure", "gcp", "阿里云", "腾讯云"],
    "主机系统": ["linux", "windows", "服务器", "主机", "操作系统"],
    "数据库": ["数据库", "mysql", "oracle", "sqlserver", "postgresql", "mongodb"],
}


# ---------------------------------------------------------------------------
# 核心逻辑函数
# ---------------------------------------------------------------------------

def identify_task_type(task_description: str) -> Optional[str]:
    """
    从任务描述中识别任务类型

    参数:
        task_description: 用户输入的任务描述文本

    返回:
        识别出的任务类型字符串；无法识别时返回 None
    """
    if not task_description or not task_description.strip():
        return None

    # 转换为小写便于匹配
    text_lower = task_description.lower()

    # 统计每个任务类型的关键词命中次数
    score_map: Dict[str, int] = {}
    for task_type, keywords in TASK_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                # 更长的关键词匹配给予更高权重（避免"测试"匹配到"渗透测试"）
                score += len(keyword)
        if score > 0:
            score_map[task_type] = score

    if not score_map:
        return None

    # 返回得分最高的任务类型
    return max(score_map, key=score_map.get)


def identify_environment(task_description: str) -> Optional[str]:
    """
    从任务描述中识别目标环境

    参数:
        task_description: 用户输入的任务描述文本

    返回:
        识别出的目标环境；无法识别时返回 None
    """
    if not task_description or not task_description.strip():
        return None

    text_lower = task_description.lower()

    for env_type, keywords in ENVIRONMENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return env_type

    return None


def check_authorization(task_description: str) -> bool:
    """
    检查任务描述中是否包含授权信息

    参数:
        task_description: 用户输入的任务描述文本

    返回:
        是否包含授权信息
    """
    if not task_description:
        return False

    text_lower = task_description.lower()
    for keyword in AUTHORIZATION_KEYWORDS:
        if keyword.lower() in text_lower:
            return True

    return False


def generate_toolchain(task_type: str, environment: Optional[str]) -> List[str]:
    """
    根据任务类型和目标环境生成工具链推荐

    参数:
        task_type: 任务类型
        environment: 目标环境（可为空）

    返回:
        工具列表
    """
    tools = list(TOOLCHAIN_MAP.get(task_type, []))

    # 根据环境追加特定工具
    if environment:
        env_tools = {
            "Web应用": ["Burp Suite", "OWASP ZAP", "Nikto", "dirsearch"],
            "移动应用": ["MobSF", "Frida", "drozer", "jadx"],
            "网络设备": ["Nmap", "Hydra", "Cisco-auditing-tool"],
            "云环境": ["Prowler", "ScoutSuite", "CloudSploit"],
            "主机系统": ["Lynis", "OpenSCAP", "chkrootkit"],
            "数据库": ["sqlmap", "NoSQLMap", "HackSQL"],
        }
        env_specific = env_tools.get(environment, [])
        for tool in env_specific:
            if tool not in tools:
                tools.append(tool)

    return tools


def generate_process(task_type: str, environment: Optional[str]) -> List[str]:
    """
    生成操作流程

    参数:
        task_type: 任务类型
        environment: 目标环境（可为空）

    返回:
        流程步骤列表
    """
    steps = list(PROCESS_TEMPLATES.get(task_type, []))

    # 如果识别到环境，在第一步前加入环境确认
    if environment:
        env_step = f"0. 确认目标环境：{environment}"
        steps.insert(0, env_step)

    return steps


def generate_knowledge_refs(task_type: str) -> List[str]:
    """
    生成知识引用列表

    参数:
        task_type: 任务类型

    返回:
        知识引用列表
    """
    return list(KNOWLEDGE_REFERENCES.get(task_type, []))


def route_task(task_description: str) -> Dict:
    """
    核心路由函数：根据任务描述生成完整路由方案

    参数:
        task_description: 任务描述文本

    返回:
        包含路由结果的字典

    异常:
        E001: 输入为空
        E002: 任务类型无法识别
        E004: 缺少授权信息
    """
    if not task_description or not task_description.strip():
        raise ValueError("E001: 任务描述不能为空")

    # 识别任务类型
    task_type = identify_task_type(task_description)
    if task_type is None:
        raise ValueError("E002: 无法识别的任务类型，请使用更明确的安全任务关键词")

    # 识别目标环境
    environment = identify_environment(task_description)

    # 授权检查（仅对测试/渗透类任务强制要求）
    if task_type in ["渗透测试", "安全测试"] and not check_authorization(task_description):
        raise ValueError("E004: 渗透测试/安全测试任务需要提供授权信息（如'已获授权'）")

    # 生成工具链、流程和知识引用
    tools = generate_toolchain(task_type, environment)
    process = generate_process(task_type, environment)
    knowledge = generate_knowledge_refs(task_type)

    # 构建结果
    result = {
        "task_type": task_type,
        "environment": environment,
        "toolchain": tools,
        "process": process,
        "knowledge_refs": knowledge,
        "authorization_required": task_type in ["渗透测试", "安全测试"],
        "authorization_confirmed": check_authorization(task_description),
    }

    return result


def format_output(result: Dict) -> str:
    """
    将路由结果格式化为可读文本输出

    参数:
        result: route_task 返回的结果字典

    返回:
        格式化后的文本

    异常:
        E007: 格式化失败
    """
    try:
        lines = []
        lines.append("=" * 60)
        lines.append("🔒 安全任务路由结果")
        lines.append("=" * 60)
        lines.append(f"📋 任务类型: {result['task_type']}")

        env = result.get("environment")
        if env:
            lines.append(f"🎯 目标环境: {env}")
        else:
            lines.append("🎯 目标环境: 未明确指定（建议补充）")

        lines.append("")
        lines.append("🛠️  推荐工具链:")
        for i, tool in enumerate(result["toolchain"], 1):
            lines.append(f"   {i}. {tool}")

        lines.append("")
        lines.append("📝 操作流程:")
        for step in result["process"]:
            lines.append(f"   {step}")

        lines.append("")
        lines.append("📚 知识引用:")
        for ref in result["knowledge_refs"]:
            lines.append(f"   • {ref}")

        lines.append("")
        auth_status = "✅ 已确认" if result["authorization_confirmed"] else "⚠️  未确认"
        lines.append(f"🔑 授权状态: {auth_status}")

        if result["authorization_required"] and not result["authorization_confirmed"]:
            lines.append("")
            lines.append("⚠️  警告: 此任务类型需要合法授权，请确认已获得书面授权后再执行！")

        lines.append("=" * 60)
        lines.append("⚠️  免责声明: 本工具仅提供流程建议，不执行任何实际攻击操作。")
        lines.append("   使用者需自行确保操作合法合规。")
        lines.append("=" * 60)

        return "\n".join(lines)
    except Exception as e:
        raise ValueError(f"E007: 输出格式化失败 - {str(e)}")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据

    返回:
        True 表示自检通过；False 表示自检失败

    异常:
        E008: 自检失败
    """
    print("🔍 开始离线自检...")
    print("-" * 50)

    # 测试用例1: 渗透测试任务（含授权）
    test1_desc = "已获授权对 Web 应用进行渗透测试"
    try:
        result1 = route_task(test1_desc)
        assert result1["task_type"] == "渗透测试", f"任务类型错误: {result1['task_type']}"
        assert result1["environment"] == "Web应用", f"环境识别错误: {result1['environment']}"
        assert len(result1["toolchain"]) > 0, "工具链为空"
        assert len(result1["process"]) > 0, "流程为空"
        assert len(result1["knowledge_refs"]) > 0, "知识引用为空"
        assert result1["authorization_confirmed"] is True, "授权确认失败"
        print("✅ 测试用例1通过: 渗透测试任务路由")
    except AssertionError as e:
        print(f"❌ 测试用例1失败: {e}")
        raise ValueError("E008: 自检失败 - 测试用例1")
    except ValueError as e:
        print(f"❌ 测试用例1异常: {e}")
        raise ValueError("E008: 自检失败 - 测试用例1")

    # 测试用例2: 安全审计任务（无环境）
    test2_desc = "对服务器进行安全审计"
    try:
        result2 = route_task(test2_desc)
        assert result2["task_type"] == "安全审计", f"任务类型错误: {result2['task_type']}"
        assert result2["environment"] == "主机系统", f"环境识别错误: {result2['environment']}"
        assert len(result2["toolchain"]) > 0, "工具链为空"
        print("✅ 测试用例2通过: 安全审计任务路由")
    except AssertionError as e:
        print(f"❌ 测试用例2失败: {e}")
        raise ValueError("E008: 自检失败 - 测试用例2")
    except ValueError as e:
        print(f"❌ 测试用例2异常: {e}")
        raise ValueError("E008: 自检失败 - 测试用例2")

    # 测试用例3: 未授权渗透测试应报错
    test3_desc = "对网站进行渗透测试"
    try:
        route_task(test3_desc)
        print("❌ 测试用例3失败: 应抛出 E004 错误")
        raise ValueError("E008: 自检失败 - 测试用例3")
    except ValueError as e:
        assert "E004" in str(e), f"错误码错误: {e}"
        print("✅ 测试用例3通过: 未授权渗透测试正确拦截")

    # 测试用例4: 空输入应报错
    try:
        route_task("")
        print("❌ 测试用例4失败: 应抛出 E001 错误")
        raise ValueError("E008: 自检失败 - 测试用例4")
    except ValueError as e:
        assert "E001" in str(e), f"错误码错误: {e}"
        print("✅ 测试用例4通过: 空输入正确拦截")

    # 测试用例5: 无法识别的任务类型
    try:
        route_task("今天天气怎么样")
        print("❌ 测试用例5失败: 应抛出 E002 错误")
        raise ValueError("E008: 自检失败 - 测试用例5")
    except ValueError as e:
        assert "E002" in str(e), f"错误码错误: {e}"
        print("✅ 测试用例5通过: 无法识别任务正确拦截")

    # 测试用例6: 多关键词任务（宽松阈值验证）
    test6_desc = "对数据库进行安全分析和漏洞评估"
    try:
        result6 = route_task(test6_desc)
        assert result6["task_type"] in ["安全分析", "漏洞评估"], f"任务类型错误: {result6['task_type']}"
        assert result6["environment"] == "数据库", f"环境识别错误: {result6['environment']}"
        assert len(result6["toolchain"]) > 0, "工具链为空"
        print("✅ 测试用例6通过: 多关键词任务路由")

    except AssertionError as e:
        print(f"❌ 测试用例6失败: {e}")
        raise ValueError("E008: 自检失败 - 测试用例6")
    except ValueError as e:
        print(f"❌ 测试用例6异常: {e}")
        raise ValueError("E008: 自检失败 - 测试用例6")

    # 测试用例7: 输出格式化验证
    try:
        formatted = format_output(result1)
        assert "安全任务路由结果" in formatted, "输出缺少标题"
        assert "推荐工具链" in formatted, "输出缺少工具链"
        assert "操作流程" in formatted, "输出缺少流程"
        assert "知识引用" in formatted, "输出缺少知识引用"
        print("✅ 测试用例7通过: 输出格式化")

    except AssertionError as e:
        print(f"❌ 测试用例7失败: {e}")
        raise ValueError("E008: 自检失败 - 测试用例7")
    except ValueError as e:
        print(f"❌ 测试用例7异常: {e}")
        raise ValueError("E008: 自检失败 - 测试用例7")

    print("-" * 50)
    print("🎉 所有自检用例通过！")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    主函数

    返回:
        进程退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="安全任务路由工具 - 按任务类型匹配工具链与流程",
        epilog="示例: python main.py --task '已获授权对 Web 应用进行渗透测试'"
    )
    parser.add_argument(
        "--task",
        type=str,
        help="安全任务描述文本，例如: '对 Web 应用进行渗透测试'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部文件）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except ValueError as e:
            print(f"❌ 自检失败: {e}")
            return 1

    # 任务路由模式
    if args.task:
        try:
            result = route_task(args.task)
            output = format_output(result)
            print(output)
            return 0
        except ValueError as e:
            print(f"❌ 错误: {e}")
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
