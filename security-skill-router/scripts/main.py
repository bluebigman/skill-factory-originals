#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security-skill-router
安全任务路由与工具链编排

版本: 1.1.4
许可证: MIT
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------
VERSION = "1.1.4"
SKILL_NAME = "security-skill-router"
SKILL_DISPLAY_NAME = "安全任务路由 工具链匹配 流程编排"

# 错误码定义
ERR_AUTH = "E001"          # 目标未授权
ERR_TARGET_FORMAT = "E002" # 目标格式错误
ERR_TOOLCHAIN = "E003"     # 工具链不完整
ERR_NETWORK = "E004"       # 网络不可达
ERR_CONFLICT = "E005"      # 任务类型冲突
ERR_PARAM = "E006"         # 参数越界
ERR_TIME = "E007"          # 时间窗口冲突
ERR_OUTPUT = "E008"        # 输出目录不可写
ERR_INPUT = "E009"         # 输入解析错误
ERR_INTERNAL = "E010"      # 内部错误

# 触发词映射表（大白话 -> 触发词 -> 任务类型）
TRIGGER_MAP = [
    {"keywords": ["检查", "配置", "审计", "基线"], "trigger": "安全审计", "task": "配置审计"},
    {"keywords": ["流量", "异常", "抓包", "pcap"], "trigger": "安全分析", "task": "流量分析"},
    {"keywords": ["注入", "Web", "应用", "网站"], "trigger": "安全测试", "task": "应用测试"},
    {"keywords": ["入侵", "痕迹", "后门", "排查"], "trigger": "漏洞评估", "task": "入侵排查"},
    {"keywords": ["渗透", "黑客", "攻击", "漏洞利用"], "trigger": "渗透测试", "task": "授权渗透"},
    {"keywords": ["API", "接口"], "trigger": "安全测试", "task": "接口测试"},
    {"keywords": ["上线", "发布", "流程", "合规"], "trigger": "安全审计", "task": "上线前检查"},
    {"keywords": ["漏洞扫描", "扫描", "漏洞"], "trigger": "漏洞评估", "task": "入侵排查"},
]

# 任务类型 -> 工具链映射
TOOLCHAIN_MAP = {
    "配置审计": {
        "primary": ["OpenSCAP", "Lynis", "auditd"],
        "backup": ["CIS-CAT", "osquery"],
        "priority": "P1",
    },
    "流量分析": {
        "primary": ["Wireshark", "tshark", "Zeek"],
        "backup": ["Suricata", "Moloch"],
        "priority": "P1",
    },
    "应用测试": {
        "primary": ["Burp Suite", "SQLMap", "OWASP ZAP"],
        "backup": ["Nikto", "w3af"],
        "priority": "P1",
    },
    "入侵排查": {
        "primary": ["Nmap", "OpenVAS", "Nessus"],
        "backup": ["Masscan", "Vulners"],
        "priority": "P1",
    },
    "授权渗透": {
        "primary": ["Metasploit", "Cobalt Strike", "Empire"],
        "backup": ["手工验证", "自定义脚本"],
        "priority": "P1",
    },
    "接口测试": {
        "primary": ["Postman", "OWASP ZAP"],
        "backup": ["Burp Suite"],
        "priority": "P1",
    },
    "上线前检查": {
        "primary": ["OpenSCAP", "Lynis", "Nmap"],
        "backup": ["CIS-CAT", "osquery"],
        "priority": "P1",
    },
}

# 任务类型 -> 知识引用
KNOWLEDGE_MAP = {
    "配置审计": {"knowledge_base": "CIS Benchmarks", "example": "CIS Ubuntu 20.04 Benchmark v2.0"},
    "流量分析": {"knowledge_base": "MITRE ATT&CK", "example": "T1046 网络服务扫描"},
    "应用测试": {"knowledge_base": "OWASP Top 10", "example": "A03:2021-Injection"},
    "入侵排查": {"knowledge_base": "NVD/CVE", "example": "CVE-2023-1234 详情"},
    "授权渗透": {"knowledge_base": "PTES 标准", "example": "PTES 技术指南"},
    "接口测试": {"knowledge_base": "OWASP Top 10", "example": "A03:2021-Injection"},
    "上线前检查": {"knowledge_base": "CIS Benchmarks", "example": "CIS Ubuntu 20.04 Benchmark v2.0"},
}

# 任务类型 -> 流程模板
FLOW_TEMPLATES = {
    "配置审计": [
        {"stage": "资产盘点", "description": "梳理目标资产清单", "command": "hostname && uname -a"},
        {"stage": "基线核查", "description": "检查系统配置是否符合基线", "command": "lynis audit system"},
        {"stage": "日志分析", "description": "检查系统日志异常", "command": "auditctl -l"},
        {"stage": "报告生成", "description": "生成审计报告", "command": "lynis report"},
    ],
    "流量分析": [
        {"stage": "流量采集", "description": "捕获网络流量", "command": "tshark -i eth0 -w capture.pcap"},
        {"stage": "协议分析", "description": "分析协议特征", "command": "tshark -r capture.pcap -z io,phs"},
        {"stage": "异常检测", "description": "检测异常流量", "command": "zeek -r capture.pcap"},
        {"stage": "报告生成", "description": "生成分析报告", "command": "tshark -r capture.pcap -z endpoints,tcp"},
    ],
    "应用测试": [
        {"stage": "信息收集", "description": "收集应用信息", "command": "whatweb {target}"},
        {"stage": "漏洞扫描", "description": "扫描应用漏洞", "command": "sqlmap -u {target} --batch"},
        {"stage": "验证复现", "description": "验证漏洞真实性", "command": "burpsuite --scan {target}"},
        {"stage": "报告生成", "description": "生成测试报告", "command": "zap-cli report -o report.html"},
    ],
    "入侵排查": [
        {"stage": "资产发现", "description": "发现存活主机", "command": "nmap -sP {target}"},
        {"stage": "端口扫描", "description": "识别开放端口", "command": "nmap -sV -sC -O -p- {target}"},
        {"stage": "漏洞扫描", "description": "扫描系统漏洞", "command": "openvas-scan --target {target}"},
        {"stage": "验证复现", "description": "验证漏洞", "command": "nmap --script vuln {target}"},
        {"stage": "报告生成", "description": "生成评估报告", "command": "generate-report --type vuln"},
    ],
    "授权渗透": [
        {"stage": "信息收集", "description": "收集目标信息", "command": "nmap -sV -sC {target}"},
        {"stage": "漏洞探测", "description": "探测可利用漏洞", "command": "msfconsole -q -x 'search type:exploit'"},
        {"stage": "漏洞利用", "description": "尝试漏洞利用", "command": "msfconsole -q -x 'use exploit/multi/handler'"},
        {"stage": "后渗透", "description": "权限维持与信息收集", "command": "meterpreter > sysinfo"},
        {"stage": "报告生成", "description": "生成渗透报告", "command": "generate-report --type pentest"},
    ],
    "接口测试": [
        {"stage": "接口梳理", "description": "梳理 API 接口清单", "command": "postman --list-collections"},
        {"stage": "安全测试", "description": "测试接口安全性", "command": "zap-cli quick-scan {target}"},
        {"stage": "注入测试", "description": "测试注入漏洞", "command": "zap-cli attack {target}"},
        {"stage": "报告生成", "description": "生成测试报告", "command": "zap-cli report -o api-report.html"},
    ],
    "上线前检查": [
        {"stage": "资产清单", "description": "确认上线资产", "command": "nmap -sP {target}"},
        {"stage": "基线核查", "description": "检查配置基线", "command": "lynis audit system"},
        {"stage": "漏洞扫描", "description": "扫描已知漏洞", "command": "nmap -sV --script vuln {target}"},
        {"stage": "合规检查", "description": "检查合规要求", "command": "openscap-policy --check"},
        {"stage": "报告生成", "description": "生成上线检查报告", "command": "generate-report --type audit"},
    ],
}

# 目标格式校验正则
TARGET_PATTERNS = {
    "ip": re.compile(r"^\d{1,3}(\.\d{1,3}){3}(/\d{1,2})?$"),
    "domain": re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "url": re.compile(r"^https?://[^\s/$.?#].[^\s]*$"),
    "file": re.compile(r"^[\w\-. /\\]+\.(pcap|log|txt|json|csv)$", re.IGNORECASE),
}


# ------------------------------------------------------------
# 数据模型
# ------------------------------------------------------------
@dataclass
class TaskRequest:
    """任务请求模型"""
    raw_input: str
    task_type: str = ""
    target: str = ""
    scope: str = ""
    depth: str = "标准"
    special_reqs: List[str] = field(default_factory=list)
    auth_code: str = ""
    confidence: int = 0
    missing_fields: List[str] = field(default_factory=list)


@dataclass
class TaskResult:
    """任务处理结果"""
    summary: Dict[str, Any] = field(default_factory=dict)
    flow: List[Dict[str, str]] = field(default_factory=list)
    toolchain: Dict[str, Any] = field(default_factory=dict)
    knowledge: Dict[str, str] = field(default_factory=dict)
    confidence: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ------------------------------------------------------------
# 核心逻辑
# ------------------------------------------------------------
class SecuritySkillRouter:
    """安全任务路由与工具链编排主类"""

    def __init__(self):
        self.version = VERSION
        self.name = SKILL_NAME
        self.display_name = SKILL_DISPLAY_NAME

    # ---------- 任务类型识别 ----------
    def identify_task_type(self, user_input: str) -> List[str]:
        """从用户输入中识别可能的任务类型（可能多个，需进一步消歧）"""
        matched_tasks = []
        user_input_lower = user_input.lower()

        for mapping in TRIGGER_MAP:
            keyword_hits = sum(1 for kw in mapping["keywords"] if kw.lower() in user_input_lower)
            if keyword_hits > 0:
                # 命中至少一个关键词，记录任务类型
                matched_tasks.append({
                    "task": mapping["task"],
                    "trigger": mapping["trigger"],
                    "hits": keyword_hits,
                })

        # 按命中关键词数排序，取前3个候选
        matched_tasks.sort(key=lambda x: x["hits"], reverse=True)
        return [t["task"] for t in matched_tasks[:3]]

    # ---------- 目标格式校验 ----------
    def validate_target(self, target: str) -> bool:
        """校验目标格式是否合法"""
        if not target or not target.strip():
            return False

        for pattern in TARGET_PATTERNS.values():
            if pattern.match(target.strip()):
                return True
        return False

    # ---------- 工具链匹配 ----------
    def match_toolchain(self, task_type: str) -> Dict[str, Any]:
        """根据任务类型匹配工具链"""
        return TOOLCHAIN_MAP.get(task_type, {
            "primary": [],
            "backup": [],
            "priority": "P3",
        })

    # ---------- 流程生成 ----------
    def generate_flow(self, task_type: str, target: str) -> List[Dict[str, str]]:
        """生成分步骤操作流程"""
        template = FLOW_TEMPLATES.get(task_type, [])
        flow = []
        for step in template:
            # 替换命令中的目标占位符
            command = step["command"].replace("{target}", target or "[需核实:目标IP/域名]")
            flow.append({
                "stage": step["stage"],
                "description": step["description"],
                "command": command,
            })
        return flow

    # ---------- 知识引用 ----------
    def get_knowledge_ref(self, task_type: str) -> Dict[str, str]:
        """获取知识库引用"""
        return KNOWLEDGE_MAP.get(task_type, {
            "knowledge_base": "未知",
            "example": "无",
        })

    # ---------- 置信度计算 ----------
    def calculate_confidence(self, req: TaskRequest) -> int:
        """计算置信度（0-100）"""
        score = 0

        # 任务类型明确 +20
        if req.task_type:
            score += 20

        # 目标明确 +30
        if req.target and self.validate_target(req.target):
            score += 30

        # 授权信息 +20
        if req.auth_code:
            score += 20

        # 范围信息 +15
        if req.scope:
            score += 15

        # 深度信息 +15
        if req.depth and req.depth != "标准":
            score += 15
        else:
            score += 5

        return min(score, 100)

    # ---------- 缺失字段识别 ----------
    def find_missing_fields(self, req: TaskRequest) -> List[str]:
        """识别缺失的关键字段"""
        missing = []

        if not req.target:
            missing.append("目标IP/域名")
        if not req.auth_code:
            missing.append("授权编号")
        if not req.task_type:
            missing.append("任务类型")
        if not req.scope:
            missing.append("测试范围/边界")

        return missing

    # ---------- 主处理流程 ----------
    def process(self, user_input: str, target: str = "", auth_code: str = "") -> TaskResult:
        """处理用户输入，生成路由结果"""
        result = TaskResult()
        req = TaskRequest(raw_input=user_input)

        try:
            # 步骤1：任务解析
            candidate_tasks = self.identify_task_type(user_input)

            if not candidate_tasks:
                # 无法识别任务类型
                req.task_type = ""
                req.missing_fields.append("任务类型")
                result.warnings.append("未能从输入中识别明确的任务类型，请使用触发词（安全审计/安全分析/安全测试/漏洞评估/渗透测试）")
            elif len(candidate_tasks) == 1:
                req.task_type = candidate_tasks[0]
            else:
                # 多任务类型冲突
                req.task_type = candidate_tasks[0]
                result.warnings.append(f"输入同时匹配多种任务类型 {candidate_tasks}，默认使用 {candidate_tasks[0]}（可通过 --task 参数指定）")

            # 目标解析
            if target:
                req.target = target
            else:
                # 尝试从输入中提取目标
                req.target = self._extract_target(user_input)

            if not self.validate_target(req.target):
                req.missing_fields.append("目标IP/域名")

            # 授权信息
            req.auth_code = auth_code
            if not req.auth_code and req.task_type in ["授权渗透", "上线前检查"]:
                req.missing_fields.append("授权编号")

            # 范围与深度（简化处理，默认值）
            req.scope = req.target or ""
            req.depth = "标准"

            # 置信度计算
            req.confidence = self.calculate_confidence(req)
            result.confidence = req.confidence

            # 缺失字段
            req.missing_fields = self.find_missing_fields(req)
            result.summary["missing_fields"] = req.missing_fields

            # 步骤2：工具链匹配
            if req.task_type:
                result.toolchain = self.match_toolchain(req.task_type)
            else:
                result.toolchain = {"primary": [], "backup": [], "priority": "N/A"}

            # 步骤3：流程生成
            if req.task_type and req.target:
                result.flow = self.generate_flow(req.task_type, req.target)
            else:
                result.flow = []
                result.warnings.append("缺少任务类型或目标，无法生成完整流程")

            # 步骤4：知识引用
            if req.task_type:
                result.knowledge = self.get_knowledge_ref(req.task_type)
            else:
                result.knowledge = {"knowledge_base": "未知", "example": "无"}

            # 构建摘要
            result.summary.update({
                "task_type": req.task_type or "[需核实:任务类型]",
                "target": req.target or "[需核实:目标IP/域名]",
                "scope": req.scope or "[需核实:测试范围]",
                "depth": req.depth,
                "auth_code": req.auth_code or "[需核实:授权编号]",
                "timestamp": datetime.now().isoformat(),
                "toolchain_name": " + ".join(result.toolchain.get("primary", [])) or "未匹配",
                "confidence_level": self._confidence_level(req.confidence),
            })

            # 错误处理
            if req.confidence < 70:
                result.errors.append(f"置信度不足（{req.confidence}%），请补充以下信息: {', '.join(req.missing_fields)}")

        except Exception as exc:
            result.errors.append(f"{ERR_INTERNAL}: 内部错误 - {str(exc)}")

        return result

    # ---------- 辅助方法 ----------
    def _extract_target(self, text: str) -> str:
        """从输入文本中提取目标（简化实现）"""
        # 尝试匹配 IP
        ip_match = re.search(r"\d{1,3}(\.\d{1,3}){3}(/\d{1,2})?", text)
        if ip_match:
            return ip_match.group(0)

        # 尝试匹配域名
        domain_match = re.search(r"[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        if domain_match:
            return domain_match.group(0)

        # 尝试匹配 URL
        url_match = re.search(r"https?://[^\s/$.?#].[^\s]*", text)
        if url_match:
            return url_match.group(0)

        return ""

    def _confidence_level(self, confidence: int) -> str:
        """置信度分级"""
        if confidence >= 90:
            return "高"
        elif confidence >= 70:
            return "中"
        else:
            return "低"

    # ---------- 输出格式化 ----------
    def format_output(self, result: TaskResult, format_type: str = "text") -> str:
        """格式化输出结果"""
        if format_type == "json":
            return json.dumps({
                "summary": result.summary,
                "flow": result.flow,
                "toolchain": result.toolchain,
                "knowledge": result.knowledge,
                "confidence": result.confidence,
                "warnings": result.warnings,
                "errors": result.errors,
            }, ensure_ascii=False, indent=2)

        # 文本格式输出
        lines = []
        lines.append("=" * 60)
        lines.append("安全任务路由结果")
        lines.append("=" * 60)

        # 1. 任务摘要
        lines.append("\n【1. 任务摘要】")
        lines.append(f"  任务类型: {result.summary.get('task_type', '未知')}")
        lines.append(f"  目标: {result.summary.get('target', '未知')}")
        lines.append(f"  范围: {result.summary.get('scope', '未知')}")
        lines.append(f"  深度: {result.summary.get('depth', '标准')}")
        lines.append(f"  授权编号: {result.summary.get('auth_code', '未提供')}")
        lines.append(f"  时间: {result.summary.get('timestamp', '')}")
        lines.append(f"  工具链: {result.summary.get('toolchain_name', '未匹配')}")
        lines.append(f"  置信度: {result.confidence}% ({result.summary.get('confidence_level', '')})")

        # 2. 执行流程
        lines.append("\n【2. 执行流程】")
        if result.flow:
            for i, step in enumerate(result.flow, 1):
                lines.append(f"  阶段 {i}: {step['stage']}")
                lines.append(f"    说明: {step['description']}")
                lines.append(f"    命令: {step['command']}")
        else:
            lines.append("  无法生成流程（信息不足）")

        # 3. 工具链
        lines.append("\n【3. 推荐工具链】")
        if result.toolchain.get("primary"):
            lines.append(f"  主选: {', '.join(result.toolchain['primary'])}")
            lines.append(f"  备选: {', '.join(result.toolchain.get('backup', []))}")
            lines.append(f"  优先级: {result.toolchain.get('priority', 'N/A')}")
        else:
            lines.append("  未匹配到工具链")

        # 4. 知识引用
        lines.append("\n【4. 知识引用】")
        lines.append(f"  知识库: {result.knowledge.get('knowledge_base', '未知')}")
        lines.append(f"  示例条目: {result.knowledge.get('example', '无')}")

        # 5. 警告与错误
        if result.warnings:
            lines.append("\n【5. 警告】")
            for warn in result.warnings:
                lines.append(f"  - {warn}")

        if result.errors:
            lines.append("\n【6. 错误】")
            for err in result.errors:
                lines.append(f"  - {err}")

        # 缺失字段提示
        missing = result.summary.get("missing_fields", [])
        if missing:
            lines.append("\n【缺失信息】")
            for field_name in missing:
                lines.append(f"  [需核实:{field_name}]")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# ------------------------------------------------------------
# 自检模块
# ------------------------------------------------------------
def run_selftest() -> bool:
    """自检函数：验证核心逻辑的正确性"""
    print("=" * 60)
    print("安全任务路由 Skill 自检")
    print("=" * 60)

    router = SecuritySkillRouter()
    all_passed = True

    # 测试 1: 任务类型识别
    print("\n[测试1] 任务类型识别")
    test_cases = [
        ("帮我检查一下服务器安全配置", ["配置审计"]),
        ("分析一下这个流量包有什么异常", ["流量分析"]),
        ("测测这个 Web 应用有没有 SQL 注入", ["应用测试", "接口测试"]),
        ("模拟黑客攻击一下我们的测试环境", ["授权渗透"]),
        ("对 192.168.1.0/24 网段做一次漏洞扫描", ["入侵排查"]),
    ]

    for input_text, expected in test_cases:
        result = router.identify_task_type(input_text)
        # 检查是否有交集
        overlap = set(result) & set(expected)
        status = "通过" if overlap else "失败"
        if not overlap:
            all_passed = False
        print(f"  输入: {input_text}")
        print(f"  识别: {result}, 期望: {expected} -> {status}")

    # 测试 2: 目标格式校验
    print("\n[测试2] 目标格式校验")
    valid_targets = ["192.168.1.1", "192.168.1.0/24", "example.com", "https://example.com", "capture.pcap"]
    invalid_targets = ["", "not a target", "123", "http://"]

    for target in valid_targets:
        result = router.validate_target(target)
        status = "通过" if result else "失败"
        if not result:
            all_passed = False
        print(f"  合法目标: {target} -> {status}")

    for target in invalid_targets:
        result = router.validate_target(target)
        status = "通过" if not result else "失败"
        if result:
            all_passed = False
        print(f"  非法目标: '{target}' -> {status}")

    # 测试 3: 工具链匹配
    print("\n[测试3] 工具链匹配")
    for task_type in ["配置审计", "流量分析", "应用测试", "入侵排查", "授权渗透"]:
        toolchain = router.match_toolchain(task_type)
        has_primary = bool(toolchain.get("primary"))
        status = "通过" if has_primary else "失败"
        if not has_primary:
            all_passed = False
        print(f"  {task_type}: {toolchain.get('primary', [])} -> {status}")

    # 测试 4: 流程生成
    print("\n[测试4] 流程生成")
    flow = router.generate_flow("配置审计", "192.168.1.1")
    if flow and len(flow) > 0:
        print(f"  生成流程阶段数: {len(flow)} -> 通过")
    else:
        print("  流程生成失败 -> 失败")
        all_passed = False

    # 测试 5: 完整处理流程
    print("\n[测试5] 完整处理流程")
    result = router.process(
        "对 192.168.1.0/24 网段做一次漏洞扫描",
        target="192.168.1.0/24",
        auth_code="AUTH-2024-001"
    )
    if result.summary.get("task_type") and result.flow:
        print(f"  任务类型: {result.summary.get('task_type')}")
        print(f"  流程阶段数: {len(result.flow)}")
        print(f"  置信度: {result.confidence}%")
        print("  处理流程 -> 通过")
    else:
        print(f"  任务类型: {result.summary.get('task_type')}")
        print(f"  流程阶段数: {len(result.flow)}")
        print(f"  错误: {result.errors}")
        print("  处理流程失败 -> 失败")
        all_passed = False

    # 测试 6: 错误处理
    print("\n[测试6] 错误处理")
    # 无效目标
    result = router.process("测试", target="invalid!!", auth_code="")
    if result.errors or result.summary.get("missing_fields"):
        print(f"  无效目标检测 -> 通过 (错误: {result.errors})")
    else:
        print("  无效目标检测 -> 失败")
        all_passed = False

    # 测试 7: 置信度分级
    print("\n[测试7] 置信度分级")
    # 高置信度场景
    high_conf = router.process(
        "对 192.168.1.1 做渗透测试",
        target="192.168.1.1",
        auth_code="AUTH-2024-002"
    )
    # 低置信度场景
    low_conf = router.process("随便看看")

    if high_conf.confidence >= 70 and low_conf.confidence < 70:
        print(f"  高置信度: {high_conf.confidence}% -> 通过")
        print(f"  低置信度: {low_conf.confidence}% -> 通过")
    else:
        print(f"  高置信度: {high_conf.confidence}%, 低置信度: {low_conf.confidence}% -> 失败")
        all_passed = False

    # 测试 8: 输出格式（JSON）
    print("\n[测试8] 输出格式")
    json_output = router.format_output(result, format_type="json")
    try:
        parsed = json.loads(json_output)
        if "summary" in parsed and "flow" in parsed:
            print("  JSON 输出格式 -> 通过")
        else:
            print("  JSON 输出格式 -> 失败")
            all_passed = False
    except json.JSONDecodeError:
        print("  JSON 输出格式 -> 失败（无法解析）")
        all_passed = False

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="安全任务路由与工具链编排 Skill",
        epilog="示例: 安全审计 192.168.1.1 --auth AUTH-001"
    )

    # 位置参数
    parser.add_argument("input", nargs="?", help="用户输入描述（如: 对 192.168.1.0/24 网段做一次漏洞扫描）")
    parser.add_argument("target", nargs="?", help="目标 IP/域名/URL/文件路径")

    # 可选参数
    parser.add_argument("--task", help="指定任务类型（配置审计/流量分析/应用测试/入侵排查/授权渗透/接口测试/上线前检查）")
    parser.add_argument("--auth", help="授权编号")
    parser.add_argument("--scope", help="测试范围/边界")
    parser.add_argument("--depth", help="测试深度（标准/深入/快速）")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print(f"{SKILL_NAME} v{VERSION}")
        print(f"名称: {SKILL_DISPLAY_NAME}")
        print(f"许可证: MIT")
        return 0

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        parser.print_help()
        print("\n错误: 请提供输入描述或使用 --selftest 运行自检")
        return 1

    router = SecuritySkillRouter()

    # 处理输入
    result = router.process(args.input, target=args.target or "", auth_code=args.auth or "")

    # 输出结果
    output = router.format_output(result, format_type=args.format)
    print(output)

    # 错误码返回
    if result.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
