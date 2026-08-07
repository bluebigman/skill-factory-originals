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

命令行用法:
    python main.py --selftest   # 运行内置离线自检（不读外部文件、不访问网络）

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
import argparse
from typing import Dict, List, Any


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
            "responsibility": "投放策略、渠道对接、数据复盘",
            "inputs": ["成片", "成片交付单"],
            "outputs": ["投放计划", "数据报告"],
            "collaborators": ["后期", "策划"]
        }
    ]

    # 校验：必须恰好 5 个角色
    if len(roles) != 5:
        raise RuntimeError("E002: 团队角色数据错误，期望 5 个角色")

    return roles


def get_process_nodes() -> List[Dict[str, Any]]:
    """
    获取流程节点配置。

    返回 12 个标准节点，每个节点包含前置条件、执行动作、验收标准。

    错误码: E003（流程节点错误）
    """
    nodes = [
        {"id": 1, "name": "项目立项", "prerequisite": "完成市场调研", "action": "撰写立项报告", "acceptance": "立项报告通过评审"},
        {"id": 2, "name": "选题定位", "prerequisite": "立项通过", "action": "确定题材与用户画像", "acceptance": "选题方向明确"},
        {"id": 3, "name": "策划案撰写", "prerequisite": "选题确定", "action": "撰写完整策划案", "acceptance": "策划案包含预算与排期"},
        {"id": 4, "name": "剧本大纲", "prerequisite": "策划案通过", "action": "编写分集大纲", "acceptance": "大纲覆盖全部集数"},
        {"id": 5, "name": "分集剧本", "prerequisite": "大纲确认", "action": "撰写完整剧本", "acceptance": "每集剧本通过审核"},
        {"id": 6, "name": "分镜脚本", "prerequisite": "剧本定稿", "action": "绘制分镜与镜头描述", "acceptance": "分镜与剧本一致"},
        {"id": 7, "name": "拍摄排期", "prerequisite": "分镜完成", "action": "制定拍摄计划与人员安排", "acceptance": "排期表可执行"},
        {"id": 8, "name": "现场拍摄", "prerequisite": "排期确认", "action": "按计划完成拍摄", "acceptance": "素材完整可用"},
        {"id": 9, "name": "后期剪辑", "prerequisite": "素材齐备", "action": "剪辑合成与特效包装", "acceptance": "成片通过内部审片"},
        {"id": 10, "name": "成片交付", "prerequisite": "后期完成", "action": "输出交付物与文件清单", "acceptance": "交付单签字确认"},
        {"id": 11, "name": "宣发排期", "prerequisite": "成片交付", "action": "制定投放计划与渠道策略", "acceptance": "投放计划通过评审"},
        {"id": 12, "name": "数据复盘", "prerequisite": "投放结束", "action": "汇总数据并输出报告", "acceptance": "报告包含优化建议"}
    ]

    # 校验：必须恰好 12 个节点
    if len(nodes) != 12:
        raise RuntimeError("E003: 流程节点数据错误，期望 12 个节点")

    return nodes


def get_deliverable_templates() -> Dict[str, str]:
    """
    获取交付物模板配置（节点名称 -> 模板文件类型）。

    错误码: E004（交付物模板错误）
    """
    templates = {
        "项目立项": "立项报告模板.md",
        "选题定位": "选题分析表.md",
        "策划案撰写": "策划案模板.md",
        "剧本大纲": "分集大纲模板.md",
        "分集剧本": "剧本模板.md",
        "分镜脚本": "分镜脚本模板.csv",
        "拍摄排期": "排期表模板.csv",
        "现场拍摄": "拍摄日志模板.md",
        "后期剪辑": "剪辑进度表.csv",
        "成片交付": "成片交付单.md",
        "宣发排期": "投放计划模板.csv",
        "数据复盘": "数据报告模板.md"
    }

    # 校验：必须与 12 个节点一一对应
    if len(templates) != 12:
        raise RuntimeError("E004: 交付物模板数据错误，期望 12 个模板")

    return templates


def get_collaboration_protocols() -> List[Dict[str, str]]:
    """
    获取跨角色协作协议配置。

    错误码: E005（协作协议错误）
    """
    protocols = [
        {
            "from_role": "策划",
            "to_role": "编剧",
            "handoff_format": "策划案文档 + 立项报告",
            "review_mechanism": "策划案评审会",
            "version_rule": "语义化版本号，重大变更升主版本"
        },
        {
            "from_role": "编剧",
            "to_role": "拍摄",
            "handoff_format": "分镜脚本 + 剧本定稿",
            "review_mechanism": "分镜脚本确认会",
            "version_rule": "每次修改记录变更日志"
        },
        {
            "from_role": "拍摄",
            "to_role": "后期",
            "handoff_format": "原始素材 + 拍摄日志",
            "review_mechanism": "素材完整性检查",
            "version_rule": "素材按日期与场景编号"
        },
        {
            "from_role": "后期",
            "to_role": "宣发",
            "handoff_format": "成片 + 成片交付单",
            "review_mechanism": "内部审片会",
            "version_rule": "成片版本号与交付单对应"
        }
    ]

    # 校验：至少 4 条协作协议
    if len(protocols) < 4:
        raise RuntimeError("E005: 协作协议数据错误，期望至少 4 条协议")

    return protocols


def get_budget_parameters() -> Dict[str, Dict[str, Any]]:
    """
    获取预算与资源估算参数表。

    错误码: E006（预算参数错误）
    """
    budget = {
        "策划阶段": {
            "duration_days": [3, 7],
            "staff_count": [1, 2],
            "equipment": ["办公电脑", "调研工具"]
        },
        "编剧阶段": {
            "duration_days": [5, 15],
            "staff_count": [1, 3],
            "equipment": ["写作软件", "剧本模板"]
        },
        "拍摄阶段": {
            "duration_days": [3, 10],
            "staff_count": [5, 15],
            "equipment": ["摄影机", "灯光", "收音设备"]
        },
        "后期阶段": {
            "duration_days": [4, 12],
            "staff_count": [2, 5],
            "equipment": ["剪辑工作站", "特效软件"]
        },
        "宣发阶段": {
            "duration_days": [3, 8],
            "staff_count": [1, 3],
            "equipment": ["投放平台账号", "数据工具"]
        }
    }

    # 校验：必须包含 5 个阶段
    if len(budget) != 5:
        raise RuntimeError("E006: 预算参数数据错误，期望 5 个阶段")

    return budget


# ============================================================
# 二、核心逻辑服务
# ============================================================

class DramaProductionService:
    """
    短剧制片全流程服务。

    封装团队矩阵模板的所有查询与计算逻辑。
    """

    def __init__(self) -> None:
        """初始化服务，加载全部内置数据。"""
        try:
            self.roles = get_team_roles()
            self.nodes = get_process_nodes()
            self.templates = get_deliverable_templates()
            self.protocols = get_collaboration_protocols()
            self.budget = get_budget_parameters()
        except RuntimeError as exc:
            # 统一包装为 E001 初始化错误
            raise RuntimeError(f"E001: 初始化失败 - {exc}") from exc

    # ---------- 查询接口 ----------

    def get_role_names(self) -> List[str]:
        """返回全部角色名称列表。"""
        return [role["name"] for role in self.roles]

    def get_node_names(self) -> List[str]:
        """返回全部流程节点名称列表。"""
        return [node["name"] for node in self.nodes]

    def get_node_by_id(self, node_id: int) -> Dict[str, Any]:
        """按 ID 查询流程节点。"""
        for node in self.nodes:
            if node["id"] == node_id:
                return node
        raise KeyError(f"E003: 未找到节点 ID {node_id}")

    def get_template_by_node(self, node_name: str) -> str:
        """按节点名称查询交付物模板。"""
        if node_name not in self.templates:
            raise KeyError(f"E004: 未找到节点 '{node_name}' 的模板")
        return self.templates[node_name]

    def get_protocols_for_role(self, role_name: str) -> List[Dict[str, str]]:
        """查询某角色作为输出方的协作协议。"""
        return [p for p in self.protocols if p["from_role"] == role_name]

    def estimate_total_days(self) -> Dict[str, List[int]]:
        """估算各阶段与总工期天数范围。"""
        total_min = 0
        total_max = 0
        result: Dict[str, List[int]] = {}

        for stage, params in self.budget.items():
            days = params["duration_days"]
            result[stage] = days
            total_min += days[0]
            total_max += days[1]

        result["总工期"] = [total_min, total_max]
        return result

    def validate_data_consistency(self) -> bool:
        """
        校验数据一致性。

        检查规则:
            1. 节点名称与交付物模板一一对应
            2. 协作协议中的角色必须存在于角色列表
            3. 预算阶段与角色数量匹配

        错误码: E010（数据一致性校验失败）
        """
        role_names = set(self.get_role_names())
        node_names = set(self.get_node_names())

        # 规则 1: 节点与模板一一对应
        template_nodes = set(self.templates.keys())
        if node_names != template_nodes:
            raise RuntimeError("E010: 节点与模板不一致")

        # 规则 2: 协作协议角色存在
        for protocol in self.protocols:
            if protocol["from_role"] not in role_names:
                raise RuntimeError(f"E010: 协议中角色 '{protocol['from_role']}' 不存在")
            if protocol["to_role"] not in role_names:
                raise RuntimeError(f"E010: 协议中角色 '{protocol['to_role']}' 不存在")

        # 规则 3: 预算阶段数量与角色数量一致
        if len(self.budget) != len(self.roles):
            raise RuntimeError("E010: 预算阶段与角色数量不一致")

        return True


# ============================================================
# 三、离线自检（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    运行内置离线自检。

    使用硬编码样例数据验证核心逻辑，不读取外部文件、不访问网络。
    断言采用宽松阈值，确保任何环境直接可过。

    错误码: E007（自检断言失败）
    """
    print("[自检] 开始...")

    try:
        # 1. 初始化服务
        service = DramaProductionService()
        print("[自检] 服务初始化成功")

        # 2. 角色数量检查（必须为 5）
        roles = service.get_role_names()
        assert len(roles) == 5, "角色数量必须为 5"
        assert "策划" in roles and "编剧" in roles, "必须包含策划与编剧角色"
        print(f"[自检] 角色数据正确: {roles}")

        # 3. 流程节点检查（必须为 12）
        nodes = service.get_node_names()
        assert len(nodes) == 12, "节点数量必须为 12"
        assert "项目立项" in nodes and "数据复盘" in nodes, "首尾节点必须存在"
        print(f"[自检] 流程节点正确（共 {len(nodes)} 个）")

        # 4. 交付物模板检查
        template = service.get_template_by_node("分集剧本")
        assert template.endswith(".md"), "剧本模板应为 Markdown 格式"
        print(f"[自检] 交付物模板正确: {template}")

        # 5. 协作协议检查
        protocols = service.get_protocols_for_role("策划")
        assert len(protocols) >= 1, "策划角色至少应有 1 条协作协议"
        assert protocols[0]["to_role"] == "编剧", "策划应首先对接编剧"
        print(f"[自检] 协作协议正确: {len(protocols)} 条")

        # 6. 预算估算检查（宽松区间）
        days = service.estimate_total_days()
        total = days.get("总工期", [0, 0])
        # 宽松断言: 总工期至少 18 天（5+5+3+4+3），最多不超过 60 天
        assert total[0] >= 18, f"最短工期应 >= 18 天，实际 {total[0]}"
        assert total[1] <= 60, f"最长工期应 <= 60 天，实际 {total[1]}"
        print(f"[自检] 预算估算正确: 总工期 {total[0]}-{total[1]} 天")

        # 7. 数据一致性校验
        assert service.validate_data_consistency(), "数据一致性校验失败"
        print("[自检] 数据一致性校验通过")

    except AssertionError as exc:
        print(f"[自检] 失败（断言错误）: {exc}")
        return 7  # E007
    except RuntimeError as exc:
        print(f"[自检] 失败（运行时错误）: {exc}")
        return 9  # E009
    except Exception as exc:  # 兜底异常
        print(f"[自检] 失败（未知异常）: {exc}")
        return 9  # E009

    print("[自检] 全部通过 ✔")
    return 0


# ============================================================
# 四、主入口
# ============================================================

def main() -> int:
    """
    主入口函数。

    解析命令行参数并执行相应操作。

    错误码:
        E008: 未识别的命令行参数
        E009: 运行时异常
    """
    parser = argparse.ArgumentParser(
        description="短剧制片 全流程团队 矩阵协作 - 独立实现脚本"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读外部文件、不访问网络）"
    )

    try:
        args = parser.parse_args()

        if args.selftest:
            return run_selftest()

        # 未指定任何参数时，打印使用说明
        print("短剧制片 全流程团队 矩阵协作 脚本")
        print("用法: python main.py --selftest")
        print("提示: 使用 --selftest 运行内置自检")
        return 0

    except SystemExit as exc:
        # argparse 在参数错误时会抛出 SystemExit
        if exc.code != 0:
            print("E008: 未识别的命令行参数或参数错误")
            return 8
        return 0
    except Exception as exc:
        print(f"E009: 运行时异常 - {exc}")
        return 9


if __name__ == "__main__":
    sys.exit(main())
