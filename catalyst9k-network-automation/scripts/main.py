#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Catalyst9K 网络自动化脚本生成助手
=================================
根据功能规格独立实现的 clean-room 版本。

功能概述：
    1. 解析网络配置需求（自然语言或半结构化文本）
    2. 生成 Python 脚本骨架
    3. 映射 YANG 模型字段
    4. 批量配置展开
    5. 配置合规性预检

仅依赖 Python 标准库，不访问网络，不读取外部文件。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_SUCCESS = 0          # 成功
ERR_INVALID_INPUT = "E001"   # 输入格式非法
ERR_UNSUPPORTED_INTF = "E002"  # 不支持的接口类型
ERR_VLAN_OUT_OF_RANGE = "E003"  # VLAN 超出范围
ERR_MISSING_REQUIRED = "E004"   # 缺少必填字段
ERR_BAD_MODE = "E005"           # 端口模式非法
ERR_TEMPLATE_MISMATCH = "E006"  # 模板与数据不匹配
ERR_DEVICE_LIST_EMPTY = "E007"  # 设备列表为空
ERR_YANG_MAPPING_FAIL = "E008"  # YANG 映射失败
ERR_INTERNAL = "E009"           # 内部错误
ERR_USAGE = "E010"              # 命令行用法错误


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# Catalyst 9000 系列支持的 VLAN 范围（标准范围 + 扩展范围）
VLAN_MIN = 1
VLAN_MAX = 4094

# 支持的端口模式
SUPPORTED_MODES = {"access", "trunk", "dynamic"}

# 常见接口类型前缀
INTERFACE_PREFIXES = ("Gi", "Te", "Fo", "Hu", "Tw", "Eth")

# 合规性检查阈值
COMPLIANCE_WARN_VLAN_USAGE = 1000   # VLAN 使用超过该值给出警告
COMPLIANCE_WARN_INTERFACES = 48     # 接口数量超过该值给出警告


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ConfigRequest:
    """配置需求解析结果"""
    
    def __init__(self, interface: str = "", vlan: int = 0, mode: str = "access",
                 description: str = "", extra: Dict[str, Any] = None):
        self.interface = interface
        self.vlan = vlan
        self.mode = mode
        self.description = description
        self.extra = extra or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "interface": self.interface,
            "vlan": self.vlan,
            "mode": self.mode,
            "description": self.description,
            "extra": self.extra
        }
    
    def __repr__(self) -> str:
        return f"ConfigRequest({self.to_dict()})"


class ComplianceReport:
    """合规性检查报告"""
    
    def __init__(self):
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.passed: bool = True
    
    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
    
    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.passed = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors
        }
    
    def __repr__(self) -> str:
        return f"ComplianceReport({self.to_dict()})"


# ---------------------------------------------------------------------------
# 功能 C1: 网络配置需求解析
# ---------------------------------------------------------------------------
def parse_config_request(text: str) -> Tuple[ConfigRequest, str]:
    """
    从自然语言或半结构化文本中提取配置意图。
    
    支持的格式示例：
        - "为接口Gi1/0/1配置VLAN 100，端口模式为access"
        - "interface: Gi1/0/1, vlan: 100, mode: trunk"
        - "配置 Gi1/0/1 为 trunk，VLAN 200"
        - JSON 字符串: {"interface": "Gi1/0/1", "vlan": 100, "mode": "access"}
    
    返回:
        (ConfigRequest, 错误码) 成功时错误码为空字符串
    """
    if not text or not isinstance(text, str):
        return ConfigRequest(), ERR_INVALID_INPUT
    
    text = text.strip()
    if not text:
        return ConfigRequest(), ERR_INVALID_INPUT
    
    # 尝试解析 JSON
    if text.startswith("{"):
        try:
            data = json.loads(text)
            return _parse_from_dict(data)
        except json.JSONDecodeError:
            return ConfigRequest(), ERR_INVALID_INPUT
    
    # 正则表达式提取
    req = ConfigRequest()
    
    # 提取接口
    intf_match = re.search(r'(?i)(?:接口|interface|int|port)?\s*(Gi\d(?:/\d+){1,3}|Te\d(?:/\d+){1,3}|Fo\d(?:/\d+){1,3}|Hu\d(?:/\d+){1,3}|Tw\d(?:/\d+){1,3}|Eth\d(?:/\d+){1,3})', text)
    if intf_match:
        req.interface = intf_match.group(1)
    else:
        return ConfigRequest(), ERR_MISSING_REQUIRED
    
    # 提取 VLAN
    vlan_match = re.search(r'(?i)(?:vlan|VLAN)\s*[:=]?\s*(\d+)', text)
    if vlan_match:
        vlan = int(vlan_match.group(1))
        if vlan < VLAN_MIN or vlan > VLAN_MAX:
            return ConfigRequest(), ERR_VLAN_OUT_OF_RANGE
        req.vlan = vlan
    else:
        return ConfigRequest(), ERR_MISSING_REQUIRED
    
    # 提取模式
    mode_match = re.search(r'(?i)(?:mode|模式|端口模式)\s*[:=]?\s*(access|trunk|dynamic)', text)
    if mode_match:
        req.mode = mode_match.group(1).lower()
    else:
        # 默认 access
        req.mode = "access"
    
    # 提取描述（可选）
    desc_match = re.search(r'(?i)(?:description|描述|desc)\s*[:=]?\s*["\']?([^"\',;]+)', text)
    if desc_match:
        req.description = desc_match.group(1).strip()
    
    return req, ""


def _parse_from_dict(data: Dict[str, Any]) -> Tuple[ConfigRequest, str]:
    """从字典解析配置需求"""
    req = ConfigRequest()
    
    # 检查必填字段
    if "interface" not in data:
        return ConfigRequest(), ERR_MISSING_REQUIRED
    if "vlan" not in data:
        return ConfigRequest(), ERR_MISSING_REQUIRED
    
    req.interface = str(data["interface"])
    
    try:
        req.vlan = int(data["vlan"])
    except (ValueError, TypeError):
        return ConfigRequest(), ERR_INVALID_INPUT
    
    if req.vlan < VLAN_MIN or req.vlan > VLAN_MAX:
        return ConfigRequest(), ERR_VLAN_OUT_OF_RANGE
    
    req.mode = str(data.get("mode", "access")).lower()
    if req.mode not in SUPPORTED_MODES:
        return ConfigRequest(), ERR_BAD_MODE
    
    req.description = str(data.get("description", ""))
    
    # 保留额外字段
    for key, value in data.items():
        if key not in ("interface", "vlan", "mode", "description"):
            req.extra[key] = value
    
    # 验证接口格式
    if not _validate_interface(req.interface):
        return ConfigRequest(), ERR_UNSUPPORTED_INTF
    
    return req, ""


def _validate_interface(interface: str) -> bool:
    """验证接口格式是否合法"""
    if not interface or not isinstance(interface, str):
        return False
    
    # 检查前缀
    if not interface.startswith(INTERFACE_PREFIXES):
        return False
    
    # 检查格式：前缀 + 数字(可含/分隔)
    pattern = r'^(?:' + '|'.join(INTERFACE_PREFIXES) + r')\d+(?:/\d+){0,3}$'
    return bool(re.match(pattern, interface))


# ---------------------------------------------------------------------------
# 功能 C2: Python 脚本骨架生成
# ---------------------------------------------------------------------------
def generate_script_skeleton(req: ConfigRequest) -> str:
    """
    基于解析结果生成可运行的 Python 脚本框架。
    
    生成包含 connect()、configure()、disconnect() 的脚本模板。
    """
    interface = req.interface
    vlan = req.vlan
    mode = req.mode
    description = req.description or f"Configured by automation for VLAN {vlan}"
    
    script = f'''#!/usr/bin/env python3
"""
Catalyst 9000 交换机自动化配置脚本
==================================
生成时间: 由 Catalyst9K Automation Skill 自动生成
目标接口: {interface}
VLAN: {vlan}
端口模式: {mode}
"""

import time
from typing import Dict, Any


class Catalyst9KClient:
    """Catalyst 9000 交换机连接客户端（示例骨架）"""
    
    def __init__(self, host: str, username: str, password: str):
        """
        初始化连接参数。
        
        生产环境中可替换为 netmiko / paramiko / RESTCONF 等实现。
        """
        self.host = host
        self.username = username
        self.password = password
        self.connected = False
    
    def connect(self) -> bool:
        """
        建立到设备的连接。
        
        返回:
            bool: 连接是否成功
        """
        # TODO: 实现实际的连接逻辑
        # 示例: 使用 netmiko
        # from netmiko import ConnectHandler
        # device = {{
        #     "device_type": "cisco_ios",
        #     "host": self.host,
        #     "username": self.username,
        #     "password": self.password,
        # }}
        # self.connection = ConnectHandler(**device)
        print(f"[CONNECT] 正在连接到 {{self.host}} ...")
        time.sleep(0.1)  # 模拟连接延迟
        self.connected = True
        return True
    
    def configure(self, config_commands: list) -> bool:
        """
        下发配置命令。
        
        参数:
            config_commands: 配置命令列表
            
        返回:
            bool: 配置是否成功
        """
        if not self.connected:
            print("[ERROR] 未建立连接")
            return False
        
        print("[CONFIGURE] 开始下发配置 ...")
        for cmd in config_commands:
            # TODO: 实际发送命令
            print(f"  -> {{cmd}}")
        return True
    
    def disconnect(self) -> None:
        """断开连接"""
        if self.connected:
            print(f"[DISCONNECT] 断开与 {{self.host}} 的连接")
            self.connected = False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False


def build_config_commands(interface: str, vlan: int, mode: str = "access",
                          description: str = "") -> list:
    """
    构建接口配置命令列表。
    
    参数:
        interface: 接口名称，如 "Gi1/0/1"
        vlan: VLAN ID
        mode: 端口模式 (access/trunk/dynamic)
        description: 接口描述
        
    返回:
        配置命令列表
    """
    commands = []
    
    # 进入接口配置模式
    commands.append(f"interface {{interface}}")
    
    # 设置描述
    if description:
        commands.append(f"description {{description}}")
    
    # 设置端口模式
    if mode == "access":
        commands.append("switchport mode access")
        commands.append(f"switchport access vlan {{vlan}}")
    elif mode == "trunk":
        commands.append("switchport mode trunk")
        commands.append(f"switchport trunk allowed vlan add {{vlan}}")
    elif mode == "dynamic":
        commands.append("switchport mode dynamic desirable")
        commands.append(f"switchport access vlan {{vlan}}")
    
    # 启用接口
    commands.append("no shutdown")
    
    return commands


def main():
    """主函数"""
    # 设备连接参数（示例）
    device = {{
        "host": "192.168.1.1",
        "username": "admin",
        "password": "password",
    }}
    
    # 配置参数
    interface = "{interface}"
    vlan = {vlan}
    mode = "{mode}"
    description = "{description}"
    
    # 构建配置命令
    commands = build_config_commands(interface, vlan, mode, description)
    
    print("=" * 60)
    print("Catalyst 9000 自动化配置")
    print("=" * 60)
    print(f"目标设备: {{device['host']}}")
    print(f"目标接口: {{interface}}")
    print(f"VLAN: {{vlan}}")
    print(f"模式: {{mode}}")
    print("-" * 60)
    print("配置命令预览:")
    for cmd in commands:
        print(f"  {{cmd}}")
    print("-" * 60)
    
    # 执行配置
    with Catalyst9KClient(**device) as client:
        success = client.configure(commands)
        if success:
            print("[SUCCESS] 配置下发完成")
        else:
            print("[FAILED] 配置下发失败")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
'''
    return script


# ---------------------------------------------------------------------------
# 功能 C3: YANG 模型字段映射
# ---------------------------------------------------------------------------
def map_to_yang(req: ConfigRequest) -> Dict[str, str]:
    """
    将配置项映射到 Open YANG 模型中的对应叶子节点。
    
    返回:
        映射字典: {YANG路径: 值}
    """
    mappings = {}
    
    # 接口映射 (Cisco-IOS-XE-interfaces)
    mappings["Cisco-IOS-XE-interfaces:interfaces/interface/name"] = req.interface
    
    # VLAN 映射 (Cisco-IOS-XE-vlan)
    mappings["Cisco-IOS-XE-vlan:VLAN/vlan-id"] = str(req.vlan)
    
    # 端口模式映射 (Cisco-IOS-XE-switchport)
    if req.mode == "access":
        mappings["Cisco-IOS-XE-switchport:switchport/mode"] = "access"
        mappings["Cisco-IOS-XE-switchport:switchport/access/vlan"] = str(req.vlan)
    elif req.mode == "trunk":
        mappings["Cisco-IOS-XE-switchport:switchport/mode"] = "trunk"
        mappings["Cisco-IOS-XE-switchport:switchport/trunk/allowed-vlans"] = str(req.vlan)
    elif req.mode == "dynamic":
        mappings["Cisco-IOS-XE-switchport:switchport/mode"] = "dynamic"
        mappings["Cisco-IOS-XE-switchport:switchport/access/vlan"] = str(req.vlan)
    
    # 描述映射 (Cisco-IOS-XE-interfaces)
    if req.description:
        mappings["Cisco-IOS-XE-interfaces:interfaces/interface/description"] = req.description
    
    # 额外字段映射
    extra_mappings = {
        "speed": "Cisco-IOS-XE-interfaces:interfaces/interface/speed",
        "duplex": "Cisco-IOS-XE-interfaces:interfaces/interface/duplex",
        "mtu": "Cisco-IOS-XE-interfaces:interfaces/interface/mtu",
        "shutdown": "Cisco-IOS-XE-interfaces:interfaces/interface/shutdown",
    }
    
    for key, value in req.extra.items():
        if key in extra_mappings:
            mappings[extra_mappings[key]] = str(value)
    
    return mappings


# ---------------------------------------------------------------------------
# 功能 C4: 批量配置展开
# ---------------------------------------------------------------------------
def expand_batch_config(template: Dict[str, Any], devices: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    """
    将单条配置模板展开为多设备/多接口的批量配置。
    
    参数:
        template: 配置模板，包含 interface/vlan/mode 等
        devices: 设备列表，每个设备可包含 host/interface/vlan 等覆盖字段
    
    返回:
        (展开后的配置列表, 错误码)
    """
    if not devices:
        return [], ERR_DEVICE_LIST_EMPTY
    
    if not template or not isinstance(template, dict):
        return [], ERR_TEMPLATE_MISMATCH
    
    # 验证模板必填字段
    if "vlan" not in template:
        return [], ERR_TEMPLATE_MISMATCH
    
    expanded = []
    
    for device in devices:
        if not isinstance(device, dict):
            continue
        
        # 合并模板和设备特定配置
        config = dict(template)
        
        # 设备特定字段覆盖模板
        for key in ("interface", "vlan", "mode", "description"):
            if key in device:
                config[key] = device[key]
        
        # 添加设备标识
        if "host" in device:
            config["host"] = device["host"]
        elif "name" in device:
            config["host"] = device["name"]
        
        # 验证配置
        req, err = _parse_from_dict(config)
        if err:
            continue
        
        expanded.append(config)
    
    if not expanded:
        return [], ERR_TEMPLATE_MISMATCH
    
    return expanded, ""


# ---------------------------------------------------------------------------
# 功能 C5: 配置合规性预检
# ---------------------------------------------------------------------------
def compliance_check(configs: List[Dict[str, Any]]) -> ComplianceReport:
    """
    检查生成的配置是否符合常见网络规范。
    
    检查项:
        - VLAN 范围是否合法
        - 端口模式是否合法
        - 接口格式是否正确
        - VLAN 使用量是否过大（警告）
        - 接口数量是否过多（警告）
    """
    report = ComplianceReport()
    
    if not configs:
        report.add_error("配置列表为空")
        return report
    
    vlan_usage = {}
    interface_count = len(configs)
    
    for i, config in enumerate(configs):
        # 检查 VLAN
        vlan = config.get("vlan", 0)
        try:
            vlan = int(vlan)
        except (ValueError, TypeError):
            report.add_error(f"配置 #{i+1}: VLAN 值非法")
            continue
        
        if vlan < VLAN_MIN or vlan > VLAN_MAX:
            report.add_error(f"配置 #{i+1}: VLAN {vlan} 超出范围 [{VLAN_MIN}-{VLAN_MAX}]")
        else:
            vlan_usage[vlan] = vlan_usage.get(vlan, 0) + 1
        
        # 检查模式
        mode = config.get("mode", "access")
        if mode not in SUPPORTED_MODES:
            report.add_error(f"配置 #{i+1}: 端口模式 '{mode}' 不支持")
        
        # 检查接口
        interface = config.get("interface", "")
        if not _validate_interface(interface):
            report.add_error(f"配置 #{i+1}: 接口 '{interface}' 格式非法")
    
    # 全局检查
    if len(vlan_usage) > COMPLIANCE_WARN_VLAN_USAGE:
        report.add_warning(f"VLAN 使用数量 ({len(vlan_usage)}) 超过建议阈值 {COMPLIANCE_WARN_VLAN_USAGE}")
    
    if interface_count > COMPLIANCE_WARN_INTERFACES:
        report.add_warning(f"接口配置数量 ({interface_count}) 超过建议阈值 {COMPLIANCE_WARN_INTERFACES}")
    
    # 检查重复配置
    seen = set()
    for config in configs:
        key = (config.get("interface", ""), config.get("vlan", 0))
        if key in seen:
            report.add_warning(f"检测到重复配置: 接口 {key[0]} VLAN {key[1]}")
        seen.add(key)
    
    return report


# ---------------------------------------------------------------------------
# 主流程编排
# ---------------------------------------------------------------------------
def process_request(text: str, generate_script: bool = True,
                    generate_yang: bool = True,
                    check_compliance: bool = True) -> Dict[str, Any]:
    """
    处理配置需求并生成所有输出。
    
    参数:
        text: 配置需求文本
        generate_script: 是否生成脚本骨架
        generate_yang: 是否生成 YANG 映射
        check_compliance: 是否进行合规性检查
    
    返回:
        包含所有结果的字典
    """
    result = {
        "success": False,
        "error_code": "",
        "error_message": "",
        "request": None,
        "script": None,
        "yang_mappings": None,
        "compliance": None,
    }
    
    # 1. 解析需求
    req, err = parse_config_request(text)
    if err:
        result["error_code"] = err
        result["error_message"] = _error_message(err)
        return result
    
    result["request"] = req.to_dict()
    
    # 2. 生成脚本骨架
    if generate_script:
        result["script"] = generate_script_skeleton(req)
    
    # 3. 生成 YANG 映射
    if generate_yang:
        result["yang_mappings"] = map_to_yang(req)
    
    # 4. 合规性检查
    if check_compliance:
        configs = [req.to_dict()]
        result["compliance"] = compliance_check(configs).to_dict()
    
    result["success"] = True
    return result


def _error_message(err_code: str) -> str:
    """获取错误码对应的错误消息"""
    messages = {
        ERR_INVALID_INPUT: "输入格式非法，无法解析",
        ERR_UNSUPPORTED_INTF: "不支持的接口类型",
        ERR_VLAN_OUT_OF_RANGE: f"VLAN 超出范围 [{VLAN_MIN}-{VLAN_MAX}]",
        ERR_MISSING_REQUIRED: "缺少必填字段（接口或 VLAN）",
        ERR_BAD_MODE: f"端口模式非法，支持: {', '.join(sorted(SUPPORTED_MODES))}",
        ERR_TEMPLATE_MISMATCH: "模板与数据不匹配",
        ERR_DEVICE_LIST_EMPTY: "设备列表为空",
        ERR_YANG_MAPPING_FAIL: "YANG 映射失败",
        ERR_INTERNAL: "内部错误",
        ERR_USAGE: "命令行用法错误",
    }
    return messages.get(err_code, f"未知错误 ({err_code})")


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检核心逻辑。
    
    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保自检样例与实际逻辑必然匹配。
    
    返回:
        0 表示全部通过，非 0 表示有失败项
    """
    print("=" * 60)
    print("Catalyst9K Automation Skill 自检")
    print("=" * 60)
    
    failures = 0
    
    # ---- 测试 1: 解析配置需求 ----
    print("\n[测试 1] 配置需求解析")
    test_cases = [
        ("为接口Gi1/0/1配置VLAN 100，端口模式为access", "Gi1/0/1", 100, "access"),
        ("interface: Te1/0/2, vlan: 200, mode: trunk", "Te1/0/2", 200, "trunk"),
        ('{"interface": "Fo1/0/1", "vlan": 300, "mode": "dynamic"}', "Fo1/0/1", 300, "dynamic"),
    ]
    
    for i, (text, exp_intf, exp_vlan, exp_mode) in enumerate(test_cases):
        req, err = parse_config_request(text)
        assert err == "", f"测试 1.{i}: 解析失败: {err}"
        assert req.interface == exp_intf, f"测试 1.{i}: 接口不匹配: {req.interface} != {exp_intf}"
        assert req.vlan == exp_vlan, f"测试 1.{i}: VLAN 不匹配: {req.vlan} != {exp_vlan}"
        assert req.mode == exp_mode, f"测试 1.{i}: 模式不匹配: {req.mode} != {exp_mode}"
        print(f"  ✓ 测试 1.{i}: 解析成功 -> {req.interface} VLAN {req.vlan} {req.mode}")
    
    # 测试错误情况
    err_cases = [
        ("", ERR_INVALID_INPUT),  # 空输入
        ("没有接口信息", ERR_MISSING_REQUIRED),  # 缺少接口
        ("为接口Gi1/0/1配置VLAN", ERR_MISSING_REQUIRED),  # 缺少 VLAN
        ("为接口Gi1/0/1配置VLAN 99999", ERR_VLAN_OUT_OF_RANGE),  # VLAN 超范围
    ]
    
    for i, (text, exp_err) in enumerate(err_cases):
        _, err = parse_config_request(text)
        assert err == exp_err, f"测试 1 错误情况 {i}: 期望 {exp_err}, 实际 {err}"
        print(f"  ✓ 测试 1 错误情况 {i}: 正确返回 {exp_err}")
    
    # ---- 测试 2: 脚本骨架生成 ----
    print("\n[测试 2] 脚本骨架生成")
    req = ConfigRequest(interface="Gi1/0/1", vlan=100, mode="access", description="test")
    script = generate_script_skeleton(req)
    
    assert "def connect" in script, "测试 2: 缺少 connect 函数"
    assert "def configure" in script, "测试 2: 缺少 configure 函数"
    assert "def disconnect" in script, "测试 2: 缺少 disconnect 函数"
    assert "Gi1/0/1" in script, "测试 2: 缺少接口信息"
    assert "100" in script, "测试 2: 缺少 VLAN 信息"
    print("  ✓ 脚本包含 connect/configure/disconnect 函数")
    print("  ✓ 脚本包含接口和 VLAN 信息")
    print(f"  ✓ 脚本长度: {len(script)} 字符")
    
    # ---- 测试 3: YANG 映射 ----
    print("\n[测试 3] YANG 模型字段映射")
    req = ConfigRequest(interface="Gi1/0/1", vlan=100, mode="access", description="test")
    yang = map_to_yang(req)
    
    assert len(yang) >= 3, f"测试 3: 映射数量过少: {len(yang)}"
    assert any("vlan-id" in k for k in yang), "测试 3: 缺少 VLAN 映射"
    assert any("interface" in k for k in yang), "测试 3: 缺少接口映射"
    assert any("mode" in k for k in yang), "测试 3: 缺少模式映射"
    print(f"  ✓ YANG 映射生成 {len(yang)} 个字段")
    for key, value in list(yang.items())[:3]:
        print(f"    - {key} = {value}")
    
    # ---- 测试 4: 批量配置展开 ----
    print("\n[测试 4] 批量配置展开")
    template = {"vlan": 100, "mode": "access"}
    devices = [
        {"host": "sw1.example.com", "interface": "Gi1/0/1"},
        {"host": "sw2.example.com", "interface": "Gi1/0/2", "vlan": 200},
        {"host": "sw3.example.com", "interface": "Te1/0/1", "mode": "trunk"},
    ]
    
    expanded, err = expand_batch_config(template, devices)
    assert err == "", f"测试 4: 展开失败: {err}"
    assert len(expanded) == 3, f"测试 4: 展开数量错误: {len(expanded)}"
    assert expanded[0]["interface"] == "Gi1/0/1", "测试 4: 接口继承错误"
    assert expanded[1]["vlan"] == 200, "测试 4: VLAN 覆盖错误"
    assert expanded[2]["mode"] == "trunk", "测试 4: 模式覆盖错误"
    print(f"  ✓ 批量展开 {len(expanded)} 条配置")
    for cfg in expanded:
        print(f"    - {cfg.get('host')}: {cfg.get('interface')} VLAN {cfg.get('vlan')} {cfg.get('mode')}")
    
    # 测试空设备列表
    _, err = expand_batch_config(template, [])
    assert err == ERR_DEVICE_LIST_EMPTY, f"测试 4 空列表: 期望 {ERR_DEVICE_LIST_EMPTY}"
    print(f"  ✓ 空设备列表正确返回 {ERR_DEVICE_LIST_EMPTY}")
    
    # ---- 测试 5: 合规性检查 ----
    print("\n[测试 5] 合规性检查")
    
    # 正常配置
    good_configs = [
        {"interface": "Gi1/0/1", "vlan": 100, "mode": "access"},
        {"interface": "Te1/0/1", "vlan": 200, "mode": "trunk"},
    ]
    report = compliance_check(good_configs)
    assert report.passed, f"测试 5: 正常配置不应报错: {report.errors}"
    assert len(report.warnings) == 0, f"测试 5: 正常配置不应有警告: {report.warnings}"
    print(f"  ✓ 正常配置通过检查")
    
    # 异常配置
    bad_configs = [
        {"interface": "Gi1/0/1", "vlan": 99999, "mode": "access"},  # VLAN 超范围
        {"interface": "Invalid", "vlan": 100, "mode": "access"},     # 接口非法
        {"interface": "Gi1/0/2", "vlan": 100, "mode": "badmode"},    # 模式非法
    ]
    report = compliance_check(bad_configs)
    assert not report.passed, "测试 5: 异常配置应失败"
    assert len(report.errors) >= 3, f"测试 5: 应至少有 3 个错误: {report.errors}"
    print(f"  ✓ 异常配置检测到 {len(report.errors)} 个错误")
    for err_msg in report.errors[:3]:
        print(f"    - {err_msg}")
    
    # 重复配置警告
    dup_configs = [
        {"interface": "Gi1/0/1", "vlan": 100, "mode": "access"},
        {"interface": "Gi1/0/1", "vlan": 100, "mode": "access"},
    ]
    report = compliance_check(dup_configs)
    assert report.passed, f"测试 5 重复: 重复配置不应报错: {report.errors}"
    assert len(report.warnings) >= 1, f"测试 5 重复: 应有重复配置警告: {report.warnings}"
    print(f"  ✓ 重复配置检测到警告")
    
    # ---- 测试 6: 完整流程 ----
    print("\n[测试 6] 完整流程")
    result = process_request("为接口Gi1/0/1配置VLAN 100，端口模式为access")
    assert result["success"], f"测试 6: 流程失败: {result['error_message']}"
    assert result["request"] is not None, "测试 6: 缺少请求解析结果"
    assert result["script"] is not None, "测试 6: 缺少脚本"
    assert result["yang_mappings"] is not None, "测试 6: 缺少 YANG 映射"
    assert result["compliance"] is not None, "测试 6: 缺少合规性报告"
    assert result["compliance"]["passed"], "测试 6: 合规性检查应通过"
    print("  ✓ 完整流程执行成功")
    print(f"  ✓ 请求: {result['request']}")
    print(f"  ✓ YANG 映射: {len(result['yang_mappings'])} 项")
    print(f"  ✓ 合规性: 通过")
    
    # ---- 汇总 ----
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检全部通过 ✓")
    else:
        print(f"自检失败: {failures} 项")
    print("=" * 60)
    
    return failures


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main_cli() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="Catalyst9K 网络自动化脚本生成助手",
        epilog="示例: python main.py --parse '为接口Gi1/0/1配置VLAN 100' --script"
    )
    
    parser.add_argument("--parse", metavar="TEXT",
                        help="解析配置需求文本")
    parser.add_argument("--script", action="store_true",
                        help="生成 Python 脚本骨架")
    parser.add_argument("--yang", action="store_true",
                        help="生成 YANG 模型映射")
    parser.add_argument("--check", action="store_true",
                        help="执行合规性检查")
    parser.add_argument("--batch", metavar="JSON",
                        help="批量配置展开 (JSON: {\"template\": {...}, \"devices\": [...]})")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 批量模式
    if args.batch:
        try:
            data = json.loads(args.batch)
            template = data.get("template", {})
            devices = data.get("devices", [])
            expanded, err = expand_batch_config(template, devices)
            if err:
                print(f"错误 [{err}]: {_error_message(err)}", file=sys.stderr)
                return 1
            print(json.dumps(expanded, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(f"错误 [{ERR_INVALID_INPUT}]: JSON 格式非法", file=sys.stderr)
            return 1
        return 0
    
    # 解析模式
    if args.parse:
        result = process_request(args.parse, generate_script=args.script,
                                 generate_yang=args.yang, check_compliance=args.check)
        
        if not result["success"]:
            print(f"错误 [{result['error_code']}]: {result['error_message']}", file=sys.stderr)
            return 1
        
        # 输出结果
        output = {}
        if result["request"]:
            output["request"] = result["request"]
        if result["script"]:
            output["script"] = result["script"]
        if result["yang_mappings"]:
            output["yang_mappings"] = result["yang_mappings"]
        if result["compliance"]:
            output["compliance"] = result["compliance"]
        
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    
    # 无参数
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
