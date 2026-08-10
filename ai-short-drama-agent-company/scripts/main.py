#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短剧制片 全流程团队 矩阵协作 - 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不包含任何既有实现代码。
仅依赖 Python 标准库，无第三方依赖。

功能概览:
    - 团队角色编排: 5 个专业角色（策划/编剧/拍摄/后期/宣发）
    - 流程节点管理: 12 个标准节点
    - 交付物模板: 为每个节点提供模板名称
    - 跨角色协作协议: 定义交接格式与评审机制
    - 预算与资源估算: 提供分环节的成本估算参数表
    - 流程编排引擎: 支持节点依赖关系验证与执行状态跟踪

命令行用法:
    python run.py --selftest   # 运行内置离线自检（不读外部文件、不访问网络）
    python run.py --budget     # 输出预算估算结果
    python run.py --budget --format json  # 以 JSON 格式输出预算估算
    python run.py --roles      # 输出团队角色配置
    python run.py --nodes      # 输出流程节点配置
    python run.py --deliverables  # 输出交付物模板
    python run.py --protocols  # 输出协作协议
    python run.py --validate   # 验证流程依赖关系

错误码说明:
    E001: 初始化配置错误
    E002: 角色数据错误
    E003: 流程节点错误
    E004: 交付物模板错误
    E005: 协作协议错误
    E006: 预算参数错误
    E007: 自检断言失败
    E008: 未识别的命令行参数
    E009: 运行时异常
    E010: 数据一致性校验失败
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


# ============================================================
# 一、核心数据定义（硬编码，作为内置模板）
# ============================================================

def get_team_roles() -> List[Dict[str, Any]]:
    """
    获取团队角色配置。

    返回 5 个专业角色，每个角色包含职责、输入、输出与协作对象。

    错误码: E002（角色数据错误）
    """
    roles = [
        {
            "name": "策划",
            "responsibility": "市场调研、选题定位、立项策划",
            "inputs": ["市场趋势", "用户画像", "平台需求"],
            "outputs": ["策划案", "立项报告"],
            "collaborators": ["编剧", "宣发"]
        },
        {
            "name": "编剧",
            "responsibility": "剧本创作、分集大纲、台词对白",
            "inputs": ["策划案", "立项报告"],
            "outputs": ["分集剧本", "分镜脚本"],
            "collaborators": ["策划", "拍摄"]
        },
        {
            "name": "拍摄",
            "responsibility": "现场拍摄、镜头调度、素材管理",
            "inputs": ["分镜脚本", "排期表"],
            "outputs": ["原始素材", "拍摄日志"],
            "collaborators": ["编剧", "后期"]
        },
        {
            "name": "后期",
            "responsibility": "剪辑合成、特效包装、调色配音",
            "inputs": ["原始素材", "拍摄日志"],
            "outputs": ["成片", "成片交付单"],
            "collaborators": ["拍摄", "宣发"]
        },
        {
            "name": "宣发",
            "responsibility": "渠道分发、营销推广、数据分析",
            "inputs": ["成片", "成片交付单"],
            "outputs": ["宣发方案", "数据报告"],
            "collaborators": ["策划", "后期"]
        }
    ]
    return roles


def get_process_nodes() -> List[Dict[str, Any]]:
    """
    获取流程节点配置。

    返回 12 个标准节点，每个节点包含名称、所属阶段、依赖关系与负责人。

    错误码: E003（流程节点错误）
    """
    nodes = [
        {"id": 1, "name": "立项策划", "stage": "策划", "depends_on": [], "owner": "策划"},
        {"id": 2, "name": "市场调研", "stage": "策划", "depends_on": ["立项策划"], "owner": "策划"},
        {"id": 3, "name": "剧本创作", "stage": "编剧", "depends_on": ["立项策划"], "owner": "编剧"},
        {"id": 4, "name": "分镜脚本", "stage": "编剧", "depends_on": ["剧本创作"], "owner": "编剧"},
        {"id": 5, "name": "选角筹备", "stage": "拍摄", "depends_on": ["分镜脚本"], "owner": "拍摄"},
        {"id": 6, "name": "现场拍摄", "stage": "拍摄", "depends_on": ["选角筹备"], "owner": "拍摄"},
        {"id": 7, "name": "素材整理", "stage": "拍摄", "depends_on": ["现场拍摄"], "owner": "拍摄"},
        {"id": 8, "name": "剪辑合成", "stage": "后期", "depends_on": ["素材整理"], "owner": "后期"},
        {"id": 9, "name": "特效包装", "stage": "后期", "depends_on": ["剪辑合成"], "owner": "后期"},
        {"id": 10, "name": "调色配音", "stage": "后期", "depends_on": ["特效包装"], "owner": "后期"},
        {"id": 11, "name": "成片交付", "stage": "后期", "depends_on": ["调色配音"], "owner": "后期"},
        {"id": 12, "name": "宣发推广", "stage": "宣发", "depends_on": ["成片交付"], "owner": "宣发"}
    ]
    return nodes


def get_deliverable_templates() -> List[Dict[str, Any]]:
    """
    获取交付物模板配置。

    为每个流程节点提供对应的交付物模板名称。

    错误码: E004（交付物模板错误）
    """
    templates = [
        {"node_id": 1, "node_name": "立项策划", "template": "立项策划书模板"},
        {"node_id": 2, "node_name": "市场调研", "template": "市场调研报告模板"},
        {"node_id": 3, "node_name": "剧本创作", "template": "分集剧本模板"},
        {"node_id": 4, "node_name": "分镜脚本", "template": "分镜脚本模板"},
        {"node_id": 5, "node_name": "选角筹备", "template": "选角方案模板"},
        {"node_id": 6, "node_name": "现场拍摄", "template": "拍摄日志模板"},
        {"node_id": 7, "node_name": "素材整理", "template": "素材清单模板"},
        {"node_id": 8, "node_name": "剪辑合成", "template": "剪辑脚本模板"},
        {"node_id": 9, "node_name": "特效包装", "template": "特效制作单模板"},
        {"node_id": 10, "node_name": "调色配音", "template": "调色配音单模板"},
        {"node_id": 11, "node_name": "成片交付", "template": "成片交付单模板"},
        {"node_id": 12, "node_name": "宣发推广", "template": "宣发方案模板"}
    ]
    return templates


def get_collaboration_protocols() -> List[Dict[str, Any]]:
    """
    获取跨角色协作协议。

    定义交接格式与评审机制。

    错误码: E005（协作协议错误）
    """
    protocols = [
        {
            "from_role": "策划",
            "to_role": "编剧",
            "handoff_format": "策划案 + 立项报告（书面文档）",
            "review_mechanism": "立项评审会（策划/编剧/宣发三方参与）"
        },
        {
            "from_role": "编剧",
            "to_role": "拍摄",
            "handoff_format": "分镜脚本 + 剧本终稿（书面文档）",
            "review_mechanism": "剧本围读会（编剧/拍摄/导演参与）"
        },
        {
            "from_role": "拍摄",
            "to_role": "后期",
            "handoff_format": "原始素材 + 拍摄日志（数字文件）",
            "review_mechanism": "素材交接单签字确认"
        },
        {
            "from_role": "后期",
            "to_role": "宣发",
            "handoff_format": "成片 + 成片交付单（数字文件）",
            "review_mechanism": "成片验收会（后期/宣发/平台方参与）"
        },
        {
            "from_role": "宣发",
            "to_role": "策划",
            "handoff_format": "数据报告 + 用户反馈（书面文档）",
            "review_mechanism": "复盘会（全部门参与）"
        }
    ]
    return protocols


def get_budget_parameters() -> List[Dict[str, Any]]:
    """
    获取预算估算参数。

    提供分环节的成本估算参数表。

    错误码: E006（预算参数错误）
    """
    parameters = [
        {"stage": "策划", "base_cost": 50000, "description": "市场调研、选题定位、立项策划"},
        {"stage": "编剧", "base_cost": 100000, "description": "剧本创作、分集大纲、台词对白"},
        {"stage": "拍摄", "base_cost": 400000, "description": "现场拍摄、镜头调度、素材管理"},
        {"stage": "后期", "base_cost": 200000, "description": "剪辑合成、特效包装、调色配音"},
        {"stage": "宣发", "base_cost": 100000, "description": "渠道分发、营销推广、数据分析"}
    ]
    return parameters


# ============================================================
# 二、核心逻辑函数
# ============================================================

def validate_process_nodes(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    验证流程节点的依赖关系。

    检查是否存在循环依赖、缺失依赖或未知依赖。

    错误码: E010（数据一致性校验失败）
    """
    result = {"valid": True, "errors": [], "execution_order": []}
    node_names = [node["name"] for node in nodes]
    node_map = {node["name"]: node for node in nodes}

    # 检查依赖是否存在
    for node in nodes:
        for dep in node["depends_on"]:
            if dep not in node_names:
                result["valid"] = False
                result["errors"].append(f"节点 '{node['name']}' 依赖不存在的节点 '{dep}'")

    # 检查循环依赖（拓扑排序）
    temp_visited = set()
    visited = set()
    order = []

    def dfs(node_name: str) -> bool:
        """深度优先搜索检测循环依赖。"""
        if node_name in temp_visited:
            return False
        if node_name in visited:
            return True
        temp_visited.add(node_name)
        node = node_map.get(node_name)
        if node:
            for dep in node["depends_on"]:
                if not dfs(dep):
                    return False
        temp_visited.remove(node_name)
        visited.add(node_name)
        order.append(node_name)
        return True

    for node in nodes:
        if node["name"] not in visited:
            if not dfs(node["name"]):
                result["valid"] = False
                result["errors"].append(f"检测到循环依赖，涉及节点 '{node['name']}'")
                break

    if result["valid"]:
        result["execution_order"] = order

    return result


def calculate_budget(parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算预算估算结果。

    根据参数表计算各环节成本与总预算。

    错误码: E006（预算参数错误）
    """
    total = sum(item["base_cost"] for item in parameters)
    items = []
    for item in parameters:
        percentage = (item["base_cost"] / total * 100) if total > 0 else 0
        items.append({
            "stage": item["stage"],
            "cost": item["base_cost"],
            "percentage": f"{percentage:.2f}%"
        })

    return {
        "total_budget": total,
        "items": items,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# 三、输出格式化函数
# ============================================================

def format_roles_table(roles: List[Dict[str, Any]]) -> str:
    """格式化角色配置为文本表格。"""
    lines = ["\n=== 团队角色配置 ===\n"]
    lines.append(f"{'角色':<6} {'职责':<30} {'输入':<20} {'输出':<20} {'协作对象':<15}")
    lines.append("-" * 100)
    for role in roles:
        lines.append(
            f"{role['name']:<6} {role['responsibility']:<30} "
            f"{','.join(role['inputs']):<20} {','.join(role['outputs']):<20} "
            f"{','.join(role['collaborators']):<15}"
        )
    return "\n".join(lines)


def format_nodes_table(nodes: List[Dict[str, Any]]) -> str:
    """格式化流程节点为文本表格。"""
    lines = ["\n=== 流程节点配置 ===\n"]
    lines.append(f"{'ID':<4} {'名称':<12} {'阶段':<8} {'依赖':<20} {'负责人':<8}")
    lines.append("-" * 60)
    for node in nodes:
        deps = ",".join(node["depends_on"]) if node["depends_on"] else "无"
        lines.append(
            f"{node['id']:<4} {node['name']:<12} {node['stage']:<8} "
            f"{deps:<20} {node['owner']:<8}"
        )
    return "\n".join(lines)


def format_deliverables_table(templates: List[Dict[str, Any]]) -> str:
    """格式化交付物模板为文本表格。"""
    lines = ["\n=== 交付物模板 ===\n"]
    lines.append(f"{'节点ID':<6} {'节点名称':<12} {'交付物模板':<30}")
    lines.append("-" * 50)
    for template in templates:
        lines.append(
            f"{template['node_id']:<6} {template['node_name']:<12} {template['template']:<30}"
        )
    return "\n".join(lines)


def format_protocols_table(protocols: List[Dict[str, Any]]) -> str:
    """格式化协作协议为文本表格。"""
    lines = ["\n=== 跨角色协作协议 ===\n"]
    lines.append(f"{'从':<6} {'到':<6} {'交接格式':<40} {'评审机制':<40}")
    lines.append("-" * 100)
    for protocol in protocols:
        lines.append(
            f"{protocol['from_role']:<6} {protocol['to_role']:<6} "
            f"{protocol['handoff_format']:<40} {protocol['review_mechanism']:<40}"
        )
    return "\n".join(lines)


def format_budget_table(budget: Dict[str, Any]) -> str:
    """格式化预算估算为文本表格。"""
    lines = ["\n=== 预算估算 ===\n"]
    lines.append(f"{'环节':<8} {'成本(元)':<12} {'占比':<10}")
    lines.append("-" * 35)
    for item in budget["items"]:
        lines.append(f"{item['stage']:<8} {item['cost']:<12} {item['percentage']:<10}")
    lines.append("-" * 35)
    lines.append(f"{'总计':<8} {budget['total_budget']:<12}")
    return "\n".join(lines)


# ============================================================
# 四、自检函数
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检。

    验证所有核心功能与数据一致性。

    错误码: E007（自检断言失败）
    """
    print("[INFO] 开始自检...")
    all_passed = True

    try:
        # 1. 验证团队角色
        roles = get_team_roles()
        assert len(roles) == 5, f"角色数量应为 5，实际 {len(roles)}"
        role_names = [r["name"] for r in roles]
        expected_roles = ["策划", "编剧", "拍摄", "后期", "宣发"]
        assert role_names == expected_roles, f"角色名称不匹配: {role_names}"
        print(f"[INFO] 团队角色数量: {len(roles)}")

        # 2. 验证流程节点
        nodes = get_process_nodes()
        assert len(nodes) == 12, f"节点数量应为 12，实际 {len(nodes)}"
        node_ids = [n["id"] for n in nodes]
        assert node_ids == list(range(1, 13)), f"节点 ID 不连续: {node_ids}"
        print(f"[INFO] 流程节点数量: {len(nodes)}")

        # 3. 验证交付物模板
        templates = get_deliverable_templates()
        assert len(templates) == 12, f"交付物模板数量应为 12，实际 {len(templates)}"
        template_node_ids = [t["node_id"] for t in templates]
        assert template_node_ids == list(range(1, 13)), f"模板节点 ID 不连续: {template_node_ids}"
        print(f"[INFO] 交付物模板数量: {len(templates)}")

        # 4. 验证协作协议
        protocols = get_collaboration_protocols()
        assert len(protocols) == 5, f"协作协议数量应为 5，实际 {len(protocols)}"
        protocol_roles = [(p["from_role"], p["to_role"]) for p in protocols]
        assert all(len(p) == 2 for p in protocol_roles), "协作协议角色对格式错误"
        print(f"[INFO] 协作协议数量: {len(protocols)}")

        # 5. 验证预算参数
        budget_params = get_budget_parameters()
        assert len(budget_params) == 5, f"预算参数数量应为 5，实际 {len(budget_params)}"
        budget_stages = [b["stage"] for b in budget_params]
        assert budget_stages == ["策划", "编剧", "拍摄", "后期", "宣发"], f"预算环节不匹配: {budget_stages}"
        print(f"[INFO] 预算参数数量: {len(budget_params)}")

        # 6. 验证流程依赖
        validation_result = validate_process_nodes(nodes)
        assert validation_result["valid"], f"流程依赖验证失败: {validation_result['errors']}"
        assert len(validation_result["execution_order"]) == 12, \
            f"执行顺序长度应为 12，实际 {len(validation_result['execution_order'])}"
        print(f"[INFO] 流程依赖验证: 通过")

        # 7. 验证预算计算
        budget = calculate_budget(budget_params)
        assert budget["total_budget"] == 850000, f"总预算应为 850000，实际 {budget['total_budget']}"
        assert len(budget["items"]) == 5, f"预算明细数量应为 5，实际 {len(budget['items'])}"
        print(f"[INFO] 预算计算验证: 通过")

        # 8. 验证输出格式化
        roles_table = format_roles_table(roles)
        assert "策划" in roles_table and "宣发" in roles_table, "角色表格缺少关键角色"
        nodes_table = format_nodes_table(nodes)
        assert "立项策划" in nodes_table and "宣发推广" in nodes_table, "节点表格缺少关键节点"
        print(f"[INFO] 输出格式化验证: 通过")

    except AssertionError as e:
        print(f"[ERROR] 自检断言失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"[ERROR] 自检异常: {e}")
        all_passed = False

    if all_passed:
        print("✅ SELFTEST PASSED")
    else:
        print("❌ SELFTEST FAILED")
        sys.exit(1)

    return all_passed


# ============================================================
# 五、主函数
# ============================================================

def main() -> int:
    """
    主函数。

    解析命令行参数并执行相应功能。

    错误码:
        E008: 未识别的命令行参数
        E009: 运行时异常
    """
    parser = argparse.ArgumentParser(
        description="短剧制片全流程矩阵 - 团队协作与流程管理工具",
        epilog="示例: python run.py --budget --format json"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--roles", action="store_true", help="输出团队角色配置")
    parser.add_argument("--nodes", action="store_true", help="输出流程节点配置")
    parser.add_argument("--deliverables", action="store_true", help="输出交付物模板")
    parser.add_argument("--protocols", action="store_true", help="输出协作协议")
    parser.add_argument("--budget", action="store_true", help="输出预算估算")
    parser.add_argument("--validate", action="store_true", help="验证流程依赖关系")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式（默认 text）")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")

    parser.add_argument("--help", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()

    try:
        # 自检模式 - 必须在所有业务校验之前处理
        if args.selftest:
            run_selftest()
            return 0

        # 输出团队角色
        if args.roles:
            roles = get_team_roles()
            if args.format == "json":
                print(json.dumps(roles, ensure_ascii=False, indent=2))
            else:
                print(format_roles_table(roles))
            if args.verbose:
                print(f"[明细] 角色配置: 共 {len(roles)} 个角色")
            return 0

        # 输出流程节点
        if args.nodes:
            nodes = get_process_nodes()
            if args.format == "json":
                print(json.dumps(nodes, ensure_ascii=False, indent=2))
            else:
                print(format_nodes_table(nodes))
            if args.verbose:
                print(f"[明细] 流程节点: 共 {len(nodes)} 个节点")
            return 0

        # 输出交付物模板
        if args.deliverables:
            templates = get_deliverable_templates()
            if args.format == "json":
                print(json.dumps(templates, ensure_ascii=False, indent=2))
            else:
                print(format_deliverables_table(templates))
            if args.verbose:
                print(f"[明细] 交付物模板: 共 {len(templates)} 个模板")
            return 0

        # 输出协作协议
        if args.protocols:
            protocols = get_collaboration_protocols()
            if args.format == "json":
                print(json.dumps(protocols, ensure_ascii=False, indent=2))
            else:
                print(format_protocols_table(protocols))
            if args.verbose:
                print(f"[明细] 协作协议: 共 {len(protocols)} 条协议")
            return 0

        # 输出预算估算
        if args.budget:
            budget_params = get_budget_parameters()
            budget = calculate_budget(budget_params)
            if args.format == "json":
                print(json.dumps(budget, ensure_ascii=False, indent=2))
            else:
                print(format_budget_table(budget))
            if args.verbose:
                print(f"[明细] 预算估算: 总预算 {budget['total_budget']} 元，共 {len(budget['items'])} 个环节")
            return 0

        # 验证流程依赖
        if args.validate:
            nodes = get_process_nodes()
            result = validate_process_nodes(nodes)
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                if result["valid"]:
                    print("[INFO] 所有依赖关系验证通过 ✅")
                    print(f"[INFO] 执行顺序: {' → '.join(result['execution_order'])}")
                else:
                    print("[ERROR] 依赖关系验证失败 ❌")
                    for error in result["errors"]:
                        print(f"  - {error}")
                    return 1
            if args.verbose:
                print(f"[明细] 依赖验证: valid={result['valid']}, 执行顺序长度={len(result['execution_order'])}")
            return 0

        # 未指定任何参数，输出帮助
        parser.print_help()
        return 0

    except Exception as e:
        print(f"[ERROR] 运行时异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
