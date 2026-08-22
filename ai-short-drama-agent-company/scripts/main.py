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
            "responsibility": "剪辑合成、调色配乐、特效包装",
            "inputs": ["原始素材", "拍摄日志"],
            "outputs": ["成片", "后期工程文件"],
            "collaborators": ["拍摄", "宣发"]
        },
        {
            "name": "宣发",
            "responsibility": "渠道分发、营销推广、数据分析",
            "inputs": ["成片", "后期工程文件"],
            "outputs": ["宣发方案", "数据报告"],
            "collaborators": ["策划", "后期"]
        }
    ]
    return roles


def get_workflow_nodes() -> List[Dict[str, Any]]:
    """
    获取标准制作流程节点。

    返回 12 个标准节点，每个节点包含名称、依赖关系与产出物。

    错误码: E003（流程节点错误）
    """
    nodes = [
        {"id": 1, "name": "项目策划", "dependencies": [], "deliverable": "项目策划书"},
        {"id": 2, "name": "剧本创作", "dependencies": [1], "deliverable": "完整剧本"},
        {"id": 3, "name": "团队组建", "dependencies": [1], "deliverable": "团队成员名单"},
        {"id": 4, "name": "拍摄筹备", "dependencies": [2, 3], "deliverable": "拍摄计划、场景布置"},
        {"id": 5, "name": "正式拍摄", "dependencies": [4], "deliverable": "原始素材"},
        {"id": 6, "name": "后期制作", "dependencies": [5], "deliverable": "成片"},
        {"id": 7, "name": "审核发布", "dependencies": [6], "deliverable": "上线版本"},
        {"id": 8, "name": "宣传预热", "dependencies": [6], "deliverable": "宣发物料"},
        {"id": 9, "name": "数据监控", "dependencies": [7], "deliverable": "数据报告"},
        {"id": 10, "name": "用户反馈", "dependencies": [7], "deliverable": "反馈汇总"},
        {"id": 11, "name": "优化迭代", "dependencies": [9, 10], "deliverable": "优化方案"},
        {"id": 12, "name": "复盘总结", "dependencies": [11], "deliverable": "复盘报告"}
    ]
    return nodes


def get_deliverables() -> List[Dict[str, Any]]:
    """
    获取交付物模板。

    为每个流程节点提供对应的交付物模板名称。

    错误码: E004（交付物模板错误）
    """
    deliverables = [
        {"node_id": 1, "template": "项目策划书模板"},
        {"node_id": 2, "template": "剧本格式模板"},
        {"node_id": 3, "template": "团队成员职责表模板"},
        {"node_id": 4, "template": "拍摄计划表模板"},
        {"node_id": 5, "template": "拍摄日志模板"},
        {"node_id": 6, "template": "后期制作清单模板"},
        {"node_id": 7, "template": "发布审核表模板"},
        {"node_id": 8, "template": "宣发物料清单模板"},
        {"node_id": 9, "template": "数据监控报表模板"},
        {"node_id": 10, "template": "用户反馈收集表模板"},
        {"node_id": 11, "template": "优化迭代计划模板"},
        {"node_id": 12, "template": "项目复盘报告模板"}
    ]
    return deliverables


def get_collaboration_protocols() -> List[Dict[str, Any]]:
    """
    获取跨角色协作协议。

    定义角色间的交接格式与评审机制。

    错误码: E005（协作协议错误）
    """
    protocols = [
        {
            "from_role": "策划",
            "to_role": "编剧",
            "handoff_format": "策划案文档",
            "review_mechanism": "立项评审会"
        },
        {
            "from_role": "编剧",
            "to_role": "拍摄",
            "handoff_format": "分镜脚本",
            "review_mechanism": "剧本围读会"
        },
        {
            "from_role": "拍摄",
            "to_role": "后期",
            "handoff_format": "原始素材+拍摄日志",
            "review_mechanism": "素材交接单"
        },
        {
            "from_role": "后期",
            "to_role": "宣发",
            "handoff_format": "成片+后期工程文件",
            "review_mechanism": "成片审核会"
        },
        {
            "from_role": "宣发",
            "to_role": "策划",
            "handoff_format": "数据报告",
            "review_mechanism": "项目复盘会"
        }
    ]
    return protocols


def get_budget_allocation() -> Dict[str, Any]:
    """
    获取预算分配建议。

    返回各环节的预算分配比例，总和为 100%。

    错误码: E006（预算参数错误）
    """
    allocation = {
        "前期策划": 5,
        "剧本创作": 10,
        "团队薪酬": 35,
        "拍摄设备": 20,
        "后期制作": 15,
        "宣发推广": 10,
        "应急预留": 5
    }
    # 验证总和为 100
    total = sum(allocation.values())
    if total != 100:
        raise ValueError(f"预算分配总和必须为 100，当前为 {total}")
    return allocation


# ============================================================
# 二、核心功能模块
# ============================================================

def format_roles(roles: List[Dict[str, Any]]) -> str:
    """格式化角色列表为文本输出。"""
    lines = ["=== 短剧制作团队角色清单 ==="]
    for i, role in enumerate(roles, 1):
        lines.append(f"{i}. {role['name']}")
        lines.append(f"   职责: {role['responsibility']}")
        lines.append(f"   输入: {', '.join(role['inputs'])}")
        lines.append(f"   输出: {', '.join(role['outputs'])}")
        lines.append(f"   协作: {', '.join(role['collaborators'])}")
    return "\n".join(lines)


def format_nodes(nodes: List[Dict[str, Any]]) -> str:
    """格式化流程节点为文本输出。"""
    lines = ["=== 短剧制作流程节点 ==="]
    for node in nodes:
        dep_str = "无" if not node["dependencies"] else ", ".join(
            f"节点 {d}" for d in node["dependencies"]
        )
        lines.append(f"节点 {node['id']}: {node['name']}")
        lines.append(f"  依赖: {dep_str}")
        lines.append(f"  产出: {node['deliverable']}")
    return "\n".join(lines)


def format_deliverables(deliverables: List[Dict[str, Any]]) -> str:
    """格式化交付物模板为文本输出。"""
    lines = ["=== 交付物模板清单 ==="]
    for item in deliverables:
        lines.append(f"节点 {item['node_id']}: {item['template']}")
    return "\n".join(lines)


def format_protocols(protocols: List[Dict[str, Any]]) -> str:
    """格式化协作协议为文本输出。"""
    lines = ["=== 跨角色协作协议 ==="]
    for i, protocol in enumerate(protocols, 1):
        lines.append(f"{i}. {protocol['from_role']} → {protocol['to_role']}")
        lines.append(f"   交接格式: {protocol['handoff_format']}")
        lines.append(f"   评审机制: {protocol['review_mechanism']}")
    return "\n".join(lines)


def format_budget(allocation: Dict[str, int]) -> str:
    """格式化预算分配为文本输出。"""
    lines = ["=== 短剧制作预算分配建议 ==="]
    lines.append("总预算: 100%")
    lines.append("├── " + "\n├── ".join(
        f"{k}: {v}%" for k, v in allocation.items()
    ))
    return "\n".join(lines)


def validate_data(
    roles: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    deliverables: List[Dict[str, Any]],
    protocols: List[Dict[str, Any]],
    allocation: Dict[str, int]
) -> List[str]:
    """
    验证数据一致性。

    检查角色、节点、交付物、协议和预算之间的逻辑关系。

    返回验证结果列表，每项以 [通过] 或 [失败] 开头。
    """
    results = []

    # 1. 角色完整性
    if len(roles) == 5:
        results.append("[通过] 角色定义完整 (5个角色)")
    else:
        results.append(f"[失败] 角色定义不完整，期望 5 个，实际 {len(roles)} 个")

    # 2. 节点完整性
    if len(nodes) == 12:
        results.append("[通过] 流程节点完整 (12个节点)")
    else:
        results.append(f"[失败] 流程节点不完整，期望 12 个，实际 {len(nodes)} 个")

    # 3. 交付物完整性
    if len(deliverables) == 12:
        results.append("[通过] 交付物模板完整 (12个模板)")
    else:
        results.append(f"[失败] 交付物模板不完整，期望 12 个，实际 {len(deliverables)} 个")

    # 4. 协作协议完整性
    if len(protocols) == 5:
        results.append("[通过] 协作协议完整 (5个协议)")
    else:
        results.append(f"[失败] 协作协议不完整，期望 5 个，实际 {len(protocols)} 个")

    # 5. 预算分配合理性
    total_budget = sum(allocation.values())
    if total_budget == 100:
        results.append("[通过] 预算分配合理 (总和100%)")
    else:
        results.append(f"[失败] 预算分配不合理，总和为 {total_budget}%，期望 100%")

    # 6. 节点依赖关系正确性
    node_ids = {node["id"] for node in nodes}
    dep_ok = True
    for node in nodes:
        for dep in node["dependencies"]:
            if dep not in node_ids:
                results.append(f"[失败] 节点 {node['id']} 依赖不存在的节点 {dep}")
                dep_ok = False
    if dep_ok:
        results.append("[通过] 节点依赖关系正确")

    # 7. 交付物与节点对应关系
    deliverable_node_ids = {item["node_id"] for item in deliverables}
    if deliverable_node_ids == node_ids:
        results.append("[通过] 交付物与节点对应关系正确")
    else:
        missing = node_ids - deliverable_node_ids
        extra = deliverable_node_ids - node_ids
        if missing:
            results.append(f"[失败] 缺少交付物的节点: {sorted(missing)}")
        if extra:
            results.append(f"[失败] 存在多余交付物的节点: {sorted(extra)}")

    # 8. 协作协议角色有效性
    role_names = {role["name"] for role in roles}
    protocol_roles = set()
    for protocol in protocols:
        protocol_roles.add(protocol["from_role"])
        protocol_roles.add(protocol["to_role"])
    if protocol_roles.issubset(role_names):
        results.append("[通过] 协作协议角色有效")
    else:
        invalid_roles = protocol_roles - role_names
        results.append(f"[失败] 协作协议中存在无效角色: {sorted(invalid_roles)}")

    return results


# ============================================================
# 三、自检模块
# ============================================================

def run_selftest() -> int:
    """
    运行内置离线自检。

    验证核心功能模块是否正常工作，并断言关键输出。

    返回 0 表示全部通过，非 0 表示存在失败项。
    """
    print("[自检] 开始运行...")
    failures = 0

    # 1. 测试角色数据
    try:
        roles = get_team_roles()
        assert len(roles) == 5, f"期望 5 个角色，实际 {len(roles)} 个"
        assert all(role["name"] for role in roles), "存在空角色名"
        print("[OK] 角色数据正常 (5个角色)")
    except Exception as e:
        print(f"[错误] 角色数据异常: {e}")
        failures += 1

    # 2. 测试流程节点数据
    try:
        nodes = get_workflow_nodes()
        assert len(nodes) == 12, f"期望 12 个节点，实际 {len(nodes)} 个"
        assert all(node["id"] > 0 for node in nodes), "存在无效节点 ID"
        print("[OK] 流程节点数据正常 (12个节点)")
    except Exception as e:
        print(f"[错误] 流程节点数据异常: {e}")
        failures += 1

    # 3. 测试交付物数据
    try:
        deliverables = get_deliverables()
        assert len(deliverables) == 12, f"期望 12 个交付物，实际 {len(deliverables)} 个"
        assert all(item["node_id"] > 0 for item in deliverables), "存在无效节点 ID"
        print("[OK] 交付物数据正常 (12个模板)")
    except Exception as e:
        print(f"[错误] 交付物数据异常: {e}")
        failures += 1

    # 4. 测试协作协议数据
    try:
        protocols = get_collaboration_protocols()
        assert len(protocols) == 5, f"期望 5 个协议，实际 {len(protocols)} 个"
        assert all(p["from_role"] and p["to_role"] for p in protocols), "存在空角色"
        print("[OK] 协作协议数据正常 (5个协议)")
    except Exception as e:
        print(f"[错误] 协作协议数据异常: {e}")
        failures += 1

    # 5. 测试预算数据
    try:
        allocation = get_budget_allocation()
        total = sum(allocation.values())
        assert total == 100, f"预算总和必须为 100，实际 {total}"
        print("[OK] 预算数据正常 (总和100%)")
    except Exception as e:
        print(f"[错误] 预算数据异常: {e}")
        failures += 1

    # 6. 测试数据一致性验证
    try:
        results = validate_data(roles, nodes, deliverables, protocols, allocation)
        all_passed = all(r.startswith("[通过]") for r in results)
        if all_passed:
            print("[OK] 数据一致性验证通过")
        else:
            print("[错误] 数据一致性验证失败:")
            for r in results:
                if r.startswith("[失败]"):
                    print(f"  {r}")
            failures += 1
    except Exception as e:
        print(f"[错误] 数据一致性验证异常: {e}")
        failures += 1

    # 7. 测试格式化输出
    try:
        roles_text = format_roles(roles)
        assert "策划" in roles_text and "宣发" in roles_text, "角色格式化输出不完整"
        nodes_text = format_nodes(nodes)
        assert "项目策划" in nodes_text and "复盘总结" in nodes_text, "节点格式化输出不完整"
        print("[OK] 格式化输出正常")
    except Exception as e:
        print(f"[错误] 格式化输出异常: {e}")
        failures += 1

    # 8. 测试 JSON 序列化
    try:
        json_str = json.dumps({"roles": roles}, ensure_ascii=False)
        assert json_str, "JSON 序列化失败"
        print("[OK] JSON 序列化正常")
    except Exception as e:
        print(f"[错误] JSON 序列化异常: {e}")
        failures += 1

    if failures == 0:
        print("[自检] 全部通过")
        return 0
    else:
        print(f"[自检] 存在 {failures} 个失败项")
        return 1


# ============================================================
# 四、主入口
# ============================================================

def main() -> int:
    """
    主入口函数。

    解析命令行参数并执行相应操作。

    返回进程退出码，0 表示成功，非 0 表示失败。
    """
    parser = argparse.ArgumentParser(
        description="短剧制片全流程团队矩阵协作工具",
        epilog="示例: python run.py --roles --format json"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行内置离线自检"
    )
    parser.add_argument(
        "--roles", action="store_true", help="输出团队角色配置"
    )
    parser.add_argument(
        "--nodes", action="store_true", help="输出流程节点配置"
    )
    parser.add_argument(
        "--deliverables", action="store_true", help="输出交付物模板"
    )
    parser.add_argument(
        "--protocols", action="store_true", help="输出协作协议"
    )
    parser.add_argument(
        "--budget", action="store_true", help="输出预算估算结果"
    )
    parser.add_argument(
        "--validate", action="store_true", help="验证流程依赖关系"
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="输出详细执行信息"
    )

    args = parser.parse_args()

    # 记录开始时间
    start_time = datetime.now(timezone.utc)

    try:
        # 自检模式
        if args.selftest:
            return run_selftest()

        # 检查是否指定了任何操作
        if not (args.roles or args.nodes or args.deliverables or
                args.protocols or args.budget or args.validate):
            parser.print_help()
            return 0

        # 加载数据
        roles = get_team_roles()
        nodes = get_workflow_nodes()
        deliverables = get_deliverables()
        protocols = get_collaboration_protocols()
        allocation = get_budget_allocation()

        # 构建输出
        output_data = {}
        output_text = []

        if args.roles:
            output_data["roles"] = roles
            output_text.append(format_roles(roles))

        if args.nodes:
            output_data["nodes"] = nodes
            output_text.append(format_nodes(nodes))

        if args.deliverables:
            output_data["deliverables"] = deliverables
            output_text.append(format_deliverables(deliverables))

        if args.protocols:
            output_data["protocols"] = protocols
            output_text.append(format_protocols(protocols))

        if args.budget:
            output_data["budget"] = allocation
            output_text.append(format_budget(allocation))

        if args.validate:
            validation_results = validate_data(
                roles, nodes, deliverables, protocols, allocation
            )
            output_data["validation"] = validation_results
            output_text.append("=== 完整性验证报告 ===")
            output_text.extend(validation_results)
            all_passed = all(r.startswith("[通过]") for r in validation_results)
            output_text.append(
                f"验证结果: {'全部通过' if all_passed else '存在失败项'}"
            )

        # 输出结果
        if args.format == "json":
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
        else:
            print("\n\n".join(output_text))

        # 详细模式输出
        if args.verbose:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            print(f"\n[详细] 执行时间: {duration:.3f} 秒", file=sys.stderr)
            print(f"[详细] 输出格式: {args.format}", file=sys.stderr)

        return 0

    except ValueError as e:
        print(f"[错误] 数据错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[错误] 运行时异常: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
