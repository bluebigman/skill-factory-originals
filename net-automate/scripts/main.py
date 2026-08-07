#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
net-automate 独立实现脚本
功能：将网络配置需求文本解析为结构化 JSON 指令数据
仅基于功能规格实现，不参考任何既有代码
"""

import json
import re
import sys
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERR_INVALID_INPUT = "E001"      # 输入为空或非字符串
ERR_PARSE_FAILED = "E002"       # 解析过程出现异常
ERR_UNSUPPORTED_TYPE = "E003"   # 不支持的设备类型
ERR_OUTPUT_FAILED = "E004"      # 输出序列化失败
ERR_INTERNAL = "E005"           # 内部逻辑错误
ERR_SELFTEST_FAILED = "E006"    # 自检失败
ERR_INVALID_ARGS = "E007"       # 命令行参数错误
ERR_IO_READ = "E008"            # 文件读取失败
ERR_IO_WRITE = "E009"           # 文件写入失败
ERR_UNKNOWN = "E010"            # 未知错误


# ============================================================
# 核心解析逻辑
# ============================================================

def _extract_device_type(text: str) -> str:
    """从文本中识别设备类型（思科常见系列）"""
    text_lower = text.lower()
    if "router" in text_lower or "isr" in text_lower or "路由器" in text_lower:
        return "cisco_router"
    if "switch" in text_lower or "交换机" in text_lower or "cat" in text_lower:
        return "cisco_switch"
    if "firewall" in text_lower or "asa" in text_lower or "防火墙" in text_lower:
        return "cisco_firewall"
    return "unknown"


def _extract_interfaces(text: str) -> List[Dict[str, str]]:
    """提取接口信息（接口名、IP、VLAN）"""
    interfaces = []
    # 匹配类似 GigabitEthernet0/1, Gi0/1, FastEthernet0/1 等
    iface_pattern = re.compile(
        r'\b(?:GigabitEthernet|FastEthernet|TenGigabitEthernet|Gi|Fa|Te)'
        r'[\d/\.]+\b',
        re.IGNORECASE
    )
    for match in iface_pattern.finditer(text):
        iface_name = match.group()
        # 查找该接口附近的IP地址（简单启发式：接口名后200字符内）
        snippet = text[match.end():match.end() + 200]
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', snippet)
        ip_addr = ip_match.group() if ip_match else None

        # 查找VLAN信息（接口名后100字符内）
        vlan_snippet = text[match.end():match.end() + 100]
        vlan_match = re.search(r'vlan\s+(\d+)', vlan_snippet, re.IGNORECASE)
        vlan_id = vlan_match.group(1) if vlan_match else None

        iface_info: Dict[str, str] = {"name": iface_name}
        if ip_addr:
            iface_info["ip"] = ip_addr
        if vlan_id:
            iface_info["vlan"] = vlan_id

        # 去重（同名接口只保留一个）
        if not any(i["name"] == iface_name for i in interfaces):
            interfaces.append(iface_info)

    return interfaces


def _extract_protocols(text: str) -> List[str]:
    """提取网络协议（OSPF、BGP、EIGRP等）"""
    protocols = []
    protocol_map = {
        "ospf": "OSPF",
        "bgp": "BGP",
        "eigrp": "EIGRP",
        "rip": "RIP",
        "vrrp": "VRRP",
        "hsrp": "HSRP",
        "stp": "STP",
        "rstp": "RSTP",
    }
    text_lower = text.lower()
    for key, value in protocol_map.items():
        if key in text_lower:
            protocols.append(value)
    return protocols


def _extract_vlans(text: str) -> List[Dict[str, Any]]:
    """提取VLAN信息"""
    vlans = []
    # 匹配 "vlan 10" 或 "vlan 10-20" 或 "vlan 10,20,30"
    vlan_pattern = re.compile(
        r'vlan\s+(\d+)(?:[-,](\d+))?', re.IGNORECASE
    )
    for match in vlan_pattern.finditer(text):
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        if start > end:
            start, end = end, start
        for vlan_id in range(start, end + 1):
            if vlan_id not in vlans:
                vlans.append({"id": vlan_id, "name": f"VLAN{vlan_id}"})
    return vlans


def _extract_as_numbers(text: str) -> List[int]:
    """提取AS号（BGP自治系统号）"""
    as_numbers = []
    # 匹配 "AS 65001" 或 "as-number 65001" 或 "bgp 65001"
    as_pattern = re.compile(
        r'(?:AS|as-number|bgp)\s+(\d{4,5})', re.IGNORECASE
    )
    for match in as_pattern.finditer(text):
        as_num = int(match.group(1))
        if as_num not in as_numbers:
            as_numbers.append(as_num)
    return as_numbers


def _extract_confidence(text: str, parsed: Dict[str, Any]) -> float:
    """计算解析置信度（0-1）"""
    confidence = 0.0
    checks = 0

    # 设备类型识别
    if parsed.get("device_type") != "unknown":
        confidence += 0.3
    checks += 1

    # 接口识别
    if parsed.get("interfaces"):
        confidence += 0.3
    checks += 1

    # 协议识别
    if parsed.get("protocols"):
        confidence += 0.2
    checks += 1

    # VLAN或AS号识别
    if parsed.get("vlans") or parsed.get("as_numbers"):
        confidence += 0.2
    checks += 1

    # 文本长度合理性
    if len(text) > 20:
        confidence += 0.1
    checks += 1

    return round(confidence / checks, 2) if checks > 0 else 0.0


def parse_config_text(text: str) -> Dict[str, Any]:
    """
    解析网络配置文本，返回结构化JSON数据
    """
    if not text or not isinstance(text, str):
        raise ValueError(f"{ERR_INVALID_INPUT}: 输入必须为非空字符串")

    try:
        # 清理文本（去除多余空白）
        cleaned = re.sub(r'\s+', ' ', text.strip())

        # 提取各项参数
        device_type = _extract_device_type(cleaned)
        interfaces = _extract_interfaces(cleaned)
        protocols = _extract_protocols(cleaned)
        vlans = _extract_vlans(cleaned)
        as_numbers = _extract_as_numbers(cleaned)

        # 构建结果对象
        parsed_item: Dict[str, Any] = {
            "device_type": device_type,
            "interfaces": interfaces,
            "protocols": protocols,
            "vlans": vlans,
        }

        if as_numbers:
            parsed_item["as_numbers"] = as_numbers

        # 计算置信度
        confidence = _extract_confidence(cleaned, parsed_item)
        parsed_item["confidence"] = confidence

        # 构建完整输出
        result = {
            "parsed_items": [parsed_item],
            "meta": {
                "source": "text_input",
                "item_count": 1,
                "parser_version": "1.0.0",
                "timestamp": None,  # 由上层填充
            }
        }

        return result

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"{ERR_PARSE_FAILED}: 解析失败 - {str(e)}")


def process_batch_input(inputs: List[str]) -> Dict[str, Any]:
    """批量处理多个配置需求"""
    if not inputs:
        raise ValueError(f"{ERR_INVALID_INPUT}: 批量输入列表为空")

    parsed_items = []
    for item in inputs:
        try:
            result = parse_config_text(item)
            parsed_items.extend(result["parsed_items"])
        except Exception as e:
            # 单条失败不影响整体
            parsed_items.append({
                "error": str(e),
                "raw_input_preview": item[:100] if item else ""
            })

    return {
        "parsed_items": parsed_items,
        "meta": {
            "source": "batch_input",
            "item_count": len(parsed_items),
            "parser_version": "1.0.0",
            "timestamp": None,
        }
    }


# ============================================================
# 自检功能
# ============================================================

def _run_selftest() -> bool:
    """内置硬编码样例数据的离线自检"""
    print("[selftest] 开始自检...")

    # 测试用例1：交换机配置
    test1 = """
    配置一台思科交换机 Catalyst 3850。
    创建 VLAN 10 和 VLAN 20。
    GigabitEthernet0/1 配置 IP 192.168.10.1。
    GigabitEthernet0/2 属于 VLAN 20。
    启用 STP 协议。
    """
    try:
        result1 = parse_config_text(test1)
        assert result1["parsed_items"], "测试1失败：解析结果为空"
        item1 = result1["parsed_items"][0]
        assert item1["device_type"] == "cisco_switch", f"测试1失败：设备类型错误 {item1['device_type']}"
        assert len(item1["interfaces"]) >= 1, "测试1失败：未识别到接口"
        assert len(item1["vlans"]) >= 2, "测试1失败：未识别到VLAN"
        assert "STP" in item1["protocols"], "测试1失败：未识别到STP协议"
        assert 0 <= item1["confidence"] <= 1, "测试1失败：置信度超出范围"
        print("[selftest] 测试1（交换机）通过")
    except AssertionError as e:
        print(f"[selftest] {str(e)}")
        return False
    except Exception as e:
        print(f"[selftest] 测试1异常: {str(e)}")
        return False

    # 测试用例2：路由器配置
    test2 = """
    配置思科 ISR 路由器启用 OSPF 协议。
    GigabitEthernet0/0 配置 IP 10.0.0.1 255.255.255.0。
    配置 BGP AS 65001。
    """
    try:
        result2 = parse_config_text(test2)
        assert result2["parsed_items"], "测试2失败：解析结果为空"
        item2 = result2["parsed_items"][0]
        assert item2["device_type"] == "cisco_router", f"测试2失败：设备类型错误 {item2['device_type']}"
        assert len(item2["interfaces"]) >= 1, "测试2失败：未识别到接口"
        assert "OSPF" in item2["protocols"], "测试2失败：未识别到OSPF"
        assert len(item2.get("as_numbers", [])) >= 1, "测试2失败：未识别到AS号"
        print("[selftest] 测试2（路由器）通过")
    except AssertionError as e:
        print(f"[selftest] {str(e)}")
        return False
    except Exception as e:
        print(f"[selftest] 测试2异常: {str(e)}")
        return False

    # 测试用例3：批量处理
    try:
        batch_result = process_batch_input([test1, test2])
        assert batch_result["parsed_items"], "测试3失败：批量解析结果为空"
        assert len(batch_result["parsed_items"]) >= 2, "测试3失败：批量解析数量不足"
        print("[selftest] 测试3（批量处理）通过")
    except AssertionError as e:
        print(f"[selftest] {str(e)}")
        return False
    except Exception as e:
        print(f"[selftest] 测试3异常: {str(e)}")
        return False

    # 测试用例4：边界情况
    try:
        # 空输入应报错
        try:
            parse_config_text("")
            print("[selftest] 测试4失败：空输入未报错")
            return False
        except ValueError:
            pass

        # 非字符串输入应报错
        try:
            parse_config_text(12345)  # type: ignore
            print("[selftest] 测试4失败：非字符串输入未报错")
            return False
        except ValueError:
            pass

        # 无意义文本应返回未知设备类型
        result4 = parse_config_text("这是一段无关紧要的内容没有任何网络配置")
        assert result4["parsed_items"][0]["device_type"] == "unknown", \
            "测试4失败：应返回unknown设备类型"
        print("[selftest] 测试4（边界情况）通过")
    except AssertionError as e:
        print(f"[selftest] {str(e)}")
        return False
    except Exception as e:
        print(f"[selftest] 测试4异常: {str(e)}")
        return False

    # 测试用例5：输出格式验证
    try:
        test5_input = "配置交换机 VLAN 100 和 VLAN 200"
        result5 = parse_config_text(test5_input)
        # 验证JSON可序列化
        json_str = json.dumps(result5, ensure_ascii=False)
        assert json_str, "测试5失败：JSON序列化失败"
        # 验证结构完整性
        assert "parsed_items" in result5, "测试5失败：缺少parsed_items字段"
        assert "meta" in result5, "测试5失败：缺少meta字段"
        assert result5["meta"]["item_count"] >= 1, "测试5失败：item_count错误"
        print("[selftest] 测试5（输出格式）通过")
    except AssertionError as e:
        print(f"[selftest] {str(e)}")
        return False
    except Exception as e:
        print(f"[selftest] 测试5异常: {str(e)}")
        return False

    print("[selftest] 全部测试通过 ✓")
    return True


# ============================================================
# CLI 入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    args = sys.argv[1:]

    # 自检模式
    if "--selftest" in args:
        try:
            success = _run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"[selftest] 自检失败: {str(e)}")
            return 1

    # 无参数时显示帮助
    if not args:
        print("net-automate 网络配置解析工具")
        print("用法:")
        print("  python main.py --selftest          运行自检")
        print("  python main.py '配置文本'          解析配置文本")
        print("  python main.py --batch '文本1' '文本2'  批量解析")
        return 0

    try:
        # 批量模式
        if args[0] == "--batch":
            if len(args) < 2:
                print(f"错误 [{ERR_INVALID_ARGS}]: --batch 模式需要至少一个文本参数")
                return 1
            result = process_batch_input(args[1:])
        # 单条模式
        else:
            text = " ".join(args)
            result = parse_config_text(text)

        # 输出JSON
        output = json.dumps(result, ensure_ascii=False, indent=2)
        print(output)
        return 0

    except ValueError as e:
        print(f"错误: {str(e)}")
        return 1
    except RuntimeError as e:
        print(f"错误: {str(e)}")
        return 1
    except Exception as e:
        print(f"错误 [{ERR_UNKNOWN}]: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
