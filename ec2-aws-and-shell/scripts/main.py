#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EC2运维与Shell脚本处理工具（独立实现版）

本脚本依据功能规格独立实现，提供：
- EC2 实例信息解析与表格化输出
- Shell 脚本静态审查与建议生成
- 运维流程模板生成
- 内置自检功能（--selftest）
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入参数缺失或格式错误",
    "E002": "JSON 数据解析失败",
    "E003": "实例数据格式不符合预期",
    "E004": "安全组规则解析失败",
    "E005": "Shell 脚本内容为空",
    "E006": "Shell 脚本语法检查失败",
    "E007": "输出目录不可写",
    "E008": "模板生成失败",
    "E009": "自检数据初始化失败",
    "E010": "未知错误",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出程序"""
    err_msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        print(f"[错误 {code}] {err_msg}: {message}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {err_msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# EC2 实例信息处理
# ============================================================

def parse_ec2_instances(json_data: str) -> List[Dict[str, Any]]:
    """
    解析 AWS EC2 describe-instances 命令的 JSON 输出
    
    参数:
        json_data: JSON 格式的字符串
    
    返回:
        实例信息列表，每个实例包含 id, state, type, tags, security_groups
    """
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        error_exit("E002", f"JSON 解析失败: {e}")
    
    if not isinstance(data, dict) or "Reservations" not in data:
        error_exit("E003", "缺少 Reservations 字段")
    
    instances = []
    
    for reservation in data.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            if not isinstance(instance, dict):
                continue
            
            # 提取基本信息
            instance_info = {
                "id": instance.get("InstanceId", "未知"),
                "state": instance.get("State", {}).get("Name", "未知"),
                "type": instance.get("InstanceType", "未知"),
                "az": instance.get("Placement", {}).get("AvailabilityZone", "未知"),
                "private_ip": instance.get("PrivateIpAddress", "无"),
                "public_ip": instance.get("PublicIpAddress", "无"),
                "tags": {},
                "security_groups": [],
            }
            
            # 解析标签
            for tag in instance.get("Tags", []):
                if isinstance(tag, dict) and "Key" in tag and "Value" in tag:
                    instance_info["tags"][tag["Key"]] = tag["Value"]
            
            # 解析安全组
            for sg in instance.get("SecurityGroups", []):
                if isinstance(sg, dict) and "GroupId" in sg:
                    instance_info["security_groups"].append({
                        "id": sg.get("GroupId", ""),
                        "name": sg.get("GroupName", ""),
                    })
            
            instances.append(instance_info)
    
    return instances


def format_instance_table(instances: List[Dict[str, Any]]) -> str:
    """
    将实例列表格式化为易读的文本表格
    
    参数:
        instances: 实例信息列表
    
    返回:
        格式化后的表格字符串
    """
    if not instances:
        return "（无实例数据）"
    
    # 定义表格列
    headers = ["实例ID", "状态", "类型", "可用区", "私有IP", "公有IP", "名称标签"]
    
    # 构建行数据
    rows = []
    for inst in instances:
        name_tag = inst.get("tags", {}).get("Name", "-")
        rows.append([
            inst.get("id", "-"),
            inst.get("state", "-"),
            inst.get("type", "-"),
            inst.get("az", "-"),
            inst.get("private_ip", "-"),
            inst.get("public_ip", "-"),
            name_tag,
        ])
    
    # 计算每列最大宽度
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # 生成表格
    lines = []
    
    # 表头
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("-" * len(header_line))
    
    # 数据行
    for row in rows:
        line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        lines.append(line)
    
    return "\n".join(lines)


def analyze_security_groups(instances: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    分析实例的安全组配置情况
    
    参数:
        instances: 实例信息列表
    
    返回:
        安全组分析结果
    """
    if not instances:
        return {"total_instances": 0, "sg_count": 0, "summary": "无实例数据"}
    
    sg_map: Dict[str, Dict[str, Any]] = {}
    
    for inst in instances:
        for sg in inst.get("security_groups", []):
            sg_id = sg.get("id", "")
            if sg_id not in sg_map:
                sg_map[sg_id] = {
                    "id": sg_id,
                    "name": sg.get("name", ""),
                    "instances": [],
                }
            sg_map[sg_id]["instances"].append(inst.get("id", "未知"))
    
    result = {
        "total_instances": len(instances),
        "sg_count": len(sg_map),
        "security_groups": list(sg_map.values()),
        "summary": f"共 {len(instances)} 个实例，使用了 {len(sg_map)} 个安全组",
    }
    
    return result


# ============================================================
# Shell 脚本审查功能
# ============================================================

def analyze_shell_script(script_content: str) -> Dict[str, Any]:
    """
    对 Shell 脚本进行静态审查，提供改进建议
    
    参数:
        script_content: Shell 脚本内容
    
    返回:
        审查结果，包含问题列表和建议
    """
    if not script_content or not script_content.strip():
        error_exit("E005", "脚本内容为空")
    
    issues = []
    suggestions = []
    line_count = len(script_content.splitlines())
    
    # 检查是否包含 shebang
    if not script_content.startswith("#!/"):
        issues.append({
            "level": "警告",
            "line": 1,
            "message": "脚本缺少 shebang 行（如 #!/bin/bash）",
        })
        suggestions.append("在脚本首行添加 shebang，例如：#!/bin/bash")
    
    # 检查变量引用是否带引号
    unquoted_vars = re.findall(r'\$\{?[A-Za-z_][A-Za-z0-9_]*\}?', script_content)
    for var in unquoted_vars:
        # 简单检查：变量出现在赋值语句右侧且未加引号
        pattern = rf'[^"\'=]\s*{re.escape(var)}\s*[^"\'=]'
        if re.search(pattern, script_content):
            issues.append({
                "level": "建议",
                "line": 0,
                "message": f"变量 {var} 可能未加引号",
            })
            suggestions.append(f"建议对变量 {var} 使用双引号包裹，例如：\"{var}\"")
            break  # 只提示一次
    
    # 检查 set -e 使用
    if "set -e" not in script_content and "set -o errexit" not in script_content:
        issues.append({
            "level": "建议",
            "line": 0,
            "message": "未启用 set -e（错误退出）",
        })
        suggestions.append("建议在脚本开头添加 set -e 以便在命令失败时立即退出")
    
    # 检查函数定义
    func_count = len(re.findall(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{', script_content, re.MULTILINE))
    
    # 检查注释比例
    comment_lines = 0
    for line in script_content.splitlines():
        if line.strip().startswith("#"):
            comment_lines += 1
    
    comment_ratio = comment_lines / line_count if line_count > 0 else 0
    
    # 生成总结
    result = {
        "line_count": line_count,
        "function_count": func_count,
        "comment_ratio": round(comment_ratio * 100, 1),
        "issues": issues,
        "suggestions": suggestions,
        "summary": f"脚本共 {line_count} 行，{func_count} 个函数，注释占比 {comment_ratio*100:.1f}%",
    }
    
    return result


# ============================================================
# 运维流程模板生成
# ============================================================

def generate_operation_template(operation_type: str) -> str:
    """
    生成运维操作手册模板
    
    参数:
        operation_type: 操作类型（巡检/故障排查/变更）
    
    返回:
        模板文本
    """
    templates = {
        "巡检": """# EC2 实例巡检操作手册

## 巡检目标
- 确认所有实例运行状态正常
- 检查资源使用率是否在合理范围
- 验证安全组配置是否符合预期

## 巡检步骤
1. 获取所有实例状态
