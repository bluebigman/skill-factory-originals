#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n8n-azure-vm-starter 的独立实现脚本。

仅依据功能规格进行 clean-room 重写，用于学习场景下的
Azure VM 上 n8n 部署信息的结构化解析与指导输出。
"""

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或格式不正确",
    "E002": "无法从输入中解析出有效的IP地址",
    "E003": "无法从输入中解析出有效的端口号",
    "E004": "无法从输入中解析出资源组名称",
    "E005": "输入中包含无效的URL格式",
    "E006": "无法识别部署状态",
    "E007": "内部数据解析错误",
    "E008": "参数组合错误",
    "E009": "未知错误",
    "E010": "自检失败",
}


@dataclass
class DeploymentInfo:
    """存储从输入文本中提取的部署相关信息。"""

    ip_address: Optional[str] = None
    port: Optional[int] = None
    resource_group: Optional[str] = None
    deployment_status: Optional[str] = None
    urls: List[str] = field(default_factory=list)
    raw_text: str = ""
    confidence: float = 0.0


class InputParser:
    """负责从用户提供的文本中解析关键字段。"""

    # 常见的IP地址正则
    IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    # 端口号 (1-65535)
    PORT_PATTERN = re.compile(r"\b([1-9]\d{0,4})\b")
    # 资源组名称 (Azure 命名规则: 字母数字、下划线、括号、点、连字符)
    RESOURCE_GROUP_PATTERN = re.compile(r"resource[ _-]?group[:\s]+([\w\-\.\(\)]+)", re.IGNORECASE)
    # URL 模式
    URL_PATTERN = re.compile(r"https?://[^\s'\"]+", re.IGNORECASE)
    # 部署状态关键词
    STATUS_PATTERN = re.compile(
        r"\b(succeeded|successful|running|deploying|failed|error|provisioning|starting)\b",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> DeploymentInfo:
        """解析输入文本，返回结构化信息。"""
        if not text or not text.strip():
            raise ValueError(ERROR_CODES["E001"])

        info = DeploymentInfo(raw_text=text.strip())
        self._extract_urls(text, info)
        self._extract_ip(text, info)
        self._extract_port(text, info)
        self._extract_resource_group(text, info)
        self._extract_status(text, info)
        self._compute_confidence(info)
        return info

    def _extract_urls(self, text: str, info: DeploymentInfo) -> None:
        """提取所有URL。"""
        urls = self.URL_PATTERN.findall(text)
        # 清理尾部标点
        cleaned_urls = []
        for url in urls:
            cleaned = url.rstrip(".,;:!?)]}>")
            if cleaned:
                cleaned_urls.append(cleaned)
        info.urls = cleaned_urls

    def _extract_ip(self, text: str, info: DeploymentInfo) -> None:
        """提取IPv4地址，并验证合法性。"""
        candidates = self.IPV4_PATTERN.findall(text)
        valid_ips = []
        for candidate in candidates:
            try:
                ip_obj = ipaddress.ip_address(candidate)
                if ip_obj.version == 4 and not ip_obj.is_loopback:
                    valid_ips.append(str(ip_obj))
            except ValueError:
                continue
        if valid_ips:
            # 取第一个合法的IP（通常是最重要的）
            info.ip_address = valid_ips[0]

    def _extract_port(self, text: str, info: DeploymentInfo) -> None:
        """提取端口号。优先提取常见n8n端口附近的数字。"""
        # 尝试匹配 "port:XXXX" 或 "端口:XXXX" 模式
        port_pattern = re.compile(r"(?:port|端口)[:\s]*(\d{2,5})", re.IGNORECASE)
        match = port_pattern.search(text)
        if match:
            port = int(match.group(1))
            if 1 <= port <= 65535:
                info.port = port
                return

        # 退而求其次，寻找URL中的端口
        for url in info.urls:
            url_match = re.search(r":(\d{2,5})", url)
            if url_match:
                port = int(url_match.group(1))
                if 1 <= port <= 65535:
                    info.port = port
                    return

        # 最后，尝试在文本中寻找常见的n8n端口
        if "5678" in text:
            info.port = 5678

    def _extract_resource_group(self, text: str, info: DeploymentInfo) -> None:
        """提取资源组名称。"""
        match = self.RESOURCE_GROUP_PATTERN.search(text)
        if match:
            info.resource_group = match.group(1).strip()

    def _extract_status(self, text: str, info: DeploymentInfo) -> None:
        """提取部署状态关键词。"""
        match = self.STATUS_PATTERN.search(text)
        if match:
            # 统一为小写
            info.deployment_status = match.group(1).lower()

    def _compute_confidence(self, info: DeploymentInfo) -> None:
        """根据提取到的字段数量计算置信度（0-1之间的浮点数）。"""
        score = 0.0
        if info.ip_address:
            score += 0.3
        if info.port:
            score += 0.2
        if info.resource_group:
            score += 0.2
        if info.deployment_status:
            score += 0.2
        if info.urls:
            score += 0.1
        # 限制在0到1之间
        info.confidence = max(0.0, min(1.0, score))


class DeploymentChecker:
    """提供部署配置的校验清单和指导建议。"""

    @staticmethod
    def generate_checklist(info: DeploymentInfo) -> List[str]:
        """根据已解析的信息生成配置校验清单。"""
        checklist = []

        if info.ip_address:
            checklist.append(f"✓ 已识别虚拟机IP地址: {info.ip_address}")
        else:
            checklist.append("✗ 未识别到虚拟机IP地址，请检查输入文本")

        if info.port:
            checklist.append(f"✓ 已识别服务端口: {info.port}")
            if info.port == 5678:
                checklist.append("  ℹ 端口5678是n8n的默认端口")
        else:
            checklist.append("✗ 未识别到服务端口，请确认n8n的监听端口")

        if info.resource_group:
            checklist.append(f"✓ 已识别资源组: {info.resource_group}")
        else:
            checklist.append("✗ 未识别到资源组名称")

        if info.deployment_status:
            checklist.append(f"✓ 部署状态: {info.deployment_status}")
            if info.deployment_status in ("succeeded", "successful", "running"):
                checklist.append("  ℹ 部署状态良好，可以继续配置")
            else:
                checklist.append("  ⚠ 部署状态异常，请检查Azure控制台")
        else:
            checklist.append("✗ 未识别到部署状态")

        if info.urls:
            checklist.append(f"✓ 发现 {len(info.urls)} 个URL")
            for url in info.urls[:3]:
                checklist.append(f"  → {url}")
        else:
            checklist.append("✗ 未发现任何URL")

        return checklist

    @staticmethod
    def generate_next_steps(info: DeploymentInfo) -> List[str]:
        """生成下一步操作的指导建议。"""
        steps = []
        if info.ip_address and info.port:
            steps.append(f"1. 在浏览器中访问 http://{info.ip_address}:{info.port} 来确认n8n是否已启动")
            steps.append("2. 首次访问时，请设置管理员账号和密码")
            steps.append("3. 检查防火墙规则，确保入站规则允许访问该端口")
        elif info.ip_address:
            steps.append("1. 确认n8n的监听端口（默认5678）")
            steps.append("2. 在Azure网络安全组中添加相应的入站端口规则")
        else:
            steps.append("1. 请提供虚拟机的公网IP地址")
            steps.append("2. 确认n8n服务已启动")

        if info.resource_group:
            steps.append(f"3. 在Azure门户中查看资源组 '{info.resource_group}' 的部署日志")

        steps.append("4. 参考n8n官方文档进行后续工作流配置")
        return steps


def run_selftest() -> int:
    """使用内置硬编码数据进行自检。

    返回:
        0 表示成功，非0表示失败。
    """
    print("开始自检...")

    # 内置测试数据（不依赖任何外部文件）
    test_cases = [
        {
            "description": "正常部署场景",
            "input": (
                "虚拟机部署完成。IP地址: 52.183.120.45, 端口: 5678, "
                "resource group: n8n-prod-rg, 状态: succeeded, "
                "访问地址: http://52.183.120.45:5678"
            ),
            "checks": ["ip", "port", "resource_group", "status", "url"],
        },
        {
            "description": "仅包含IP和端口",
            "input": "服务器IP 20.84.56.123，n8n运行在5678端口",
            "checks": ["ip", "port"],
        },
        {
            "description": "空输入场景",
            "input": "",
            "expect_error": True,
        },
        {
            "description": "包含无效IP的场景",
            "input": "IP地址是 999.999.999.999，端口 8080，状态 running",
            "checks": ["port", "status"],
            "no_ip": True,
        },
    ]

    parser = InputParser()
    checker = DeploymentChecker()
    passed_count = 0

    for idx, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {idx}: {case['description']}")
        try:
            info = parser.parse(case["input"])
        except ValueError as exc:
            if case.get("expect_error"):
                print(f"  ✓ 预期错误处理正确: {exc}")
                passed_count += 1
                continue
            else:
                print(f"  ✗ 意外错误: {exc}")
                return 1

        # 进行宽松断言
        ok = True
        if "ip" in case.get("checks", []):
            if not info.ip_address:
                print("  ✗ IP地址解析失败")
                ok = False
            else:
                print(f"  ✓ IP地址: {info.ip_address}")

        if "no_ip" in case.get("checks", []):
            if info.ip_address:
                print("  ✗ 应忽略无效IP")
                ok = False
            else:
                print("  ✓ 正确忽略了无效IP")

        if "port" in case.get("checks", []):
            if not info.port or not (1 <= info.port <= 65535):
                print("  ✗ 端口号解析失败")
                ok = False
            else:
                print(f"  ✓ 端口: {info.port}")

        if "resource_group" in case.get("checks", []):
            if not info.resource_group:
                print("  ✗ 资源组解析失败")
                ok = False
            else:
                print(f"  ✓ 资源组: {info.resource_group}")

        if "status" in case.get("checks", []):
            if not info.deployment_status:
                print("  ✗ 状态解析失败")
                ok = False
            else:
                print(f"  ✓ 状态: {info.deployment_status}")

        if "url" in case.get("checks", []):
            if not info.urls:
                print("  ✗ URL解析失败")
                ok = False
            else:
                print(f"  ✓ URL数量: {len(info.urls)}")

        # 验证置信度范围
        if not (0.0 <= info.confidence <= 1.0):
            print(f"  ✗ 置信度超出范围: {info.confidence}")
            ok = False
        else:
            print(f"  ✓ 置信度: {info.confidence:.2f}")

        # 验证checklist生成
        checklist = checker.generate_checklist(info)
        if not checklist:
            print("  ✗ 校验清单为空")
            ok = False
        else:
            print(f"  ✓ 校验清单生成成功 ({len(checklist)} 条)")

        if ok:
            passed_count += 1
            print("  ✓ 用例通过")
        else:
            print("  ✗ 用例失败")
            return 1

    print(f"\n自检完成: {passed_count}/{len(test_cases)} 个用例通过")
    if passed_count == len(test_cases):
        print("所有自检通过 ✅")
        return 0
    else:
        print("自检未完全通过 ❌")
        return 1


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="Azure虚拟机 n8n部署 入门引导 - 结构化处理工具",
        epilog="示例: python main.py --input 'IP: 52.183.120.45, 端口: 5678'",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="包含部署信息的原始文本（如URL、IP、资源组、状态等）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件或网络）",
    )
    parser.add_argument(
        "--checklist",
        action="store_true",
        help="输出配置校验清单",
    )
    parser.add_argument(
        "--steps",
        action="store_true",
        help="输出下一步操作指导",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理输入模式
    if not args.input:
        print(f"错误: {ERROR_CODES['E001']}", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        # 解析输入
        input_parser = InputParser()
        info = input_parser.parse(args.input)

        # 输出解析结果
        print("\n=== 解析结果 ===")
        print(f"IP地址: {info.ip_address or '未识别'}")
        print(f"端口: {info.port or '未识别'}")
        print(f"资源组: {info.resource_group or '未识别'}")
        print(f"部署状态: {info.deployment_status or '未识别'}")
        print(f"URLs: {', '.join(info.urls) if info.urls else '未识别'}")
        print(f"置信度: {info.confidence:.2f}")

        # 输出校验清单
        if args.checklist:
            checker = DeploymentChecker()
            print("\n=== 配置校验清单 ===")
            for item in checker.generate_checklist(info):
                print(f"  {item}")

        # 输出下一步指导
        if args.steps:
            checker = DeploymentChecker()
            print("\n=== 下一步操作指导 ===")
            for step in checker.generate_next_steps(info):
                print(f"  {step}")

        return 0

    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底错误处理
        print(f"错误: {ERROR_CODES['E009']}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
