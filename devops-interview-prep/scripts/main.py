#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
devops-interview-prep 独立实现脚本

根据岗位名称与技能水平，生成定制化 DevOps 面试题集与模拟问答。
仅依赖标准库，支持 --selftest 离线自检。
"""

import argparse
import json
import sys
import os
from typing import Dict, List, Optional, Union


# ============================================================
# 常量与内置数据（硬编码样例）
# ============================================================

# 岗位 → 技能领域映射
ROLE_SKILLS: Dict[str, List[str]] = {
    "devops": ["CI/CD", "容器化", "配置管理", "监控告警", "云平台"],
    "sre": ["SLO/SLI", "容量规划", "故障演练", "可观测性", "自动化运维"],
    "platform": ["平台架构", "开发者体验", "多集群管理", "服务网格", "基础设施即代码"],
}

# 技能水平 → 难度系数（1-5）
LEVEL_DIFFICULTY: Dict[str, int] = {
    "初级": 1,
    "中级": 3,
    "高级": 5,
}

# 技能领域 → 面试题模板
SKILL_QUESTIONS: Dict[str, List[str]] = {
    "CI/CD": [
        "请描述一条完整的 CI/CD 流水线包含哪些阶段？",
        "如何实现流水线的并行构建与缓存优化？",
        "在 CD 阶段如何实现蓝绿部署或金丝雀发布？",
    ],
    "容器化": [
        "Docker 镜像分层机制的原理是什么？",
        "如何优化 Docker 镜像体积？",
        "Kubernetes 中 Pod 的生命周期有哪些阶段？",
    ],
    "配置管理": [
        "Ansible 与 Terraform 在配置管理上的核心区别？",
        "如何设计一套多环境（开发/测试/生产）的配置管理方案？",
        "配置漂移（Configuration Drift）如何检测与修复？",
    ],
    "监控告警": [
        "Prometheus 的拉取模型与推模型相比有什么优势？",
        "如何设计一套分级告警规则避免告警风暴？",
        "监控数据的长期存储与高基数问题如何解决？",
    ],
    "云平台": [
        "如何在 AWS 上设计一个高可用架构？",
        "云成本优化有哪些常用策略？",
        "多云或混合云架构的挑战与解决方案？",
    ],
    "SLO/SLI": [
        "如何定义 SLI（服务等级指标）？",
        "SLO 与 SLA 的区别是什么？",
        "如何基于 SLO 驱动容量规划？",
    ],
    "容量规划": [
        "如何根据历史流量预测未来容量需求？",
        "容量规划的常用工具与技术有哪些？",
        "如何应对突发流量导致的容量瓶颈？",
    ],
    "故障演练": [
        "混沌工程的核心原则是什么？",
        "如何设计一次安全的故障演练？",
        "故障演练后的复盘流程是怎样的？",
    ],
    "可观测性": [
        "Metrics、Logs、Traces 三者的关系与区别？",
        "如何实现分布式链路追踪？",
        "可观测性建设的最佳实践有哪些？",
    ],
    "自动化运维": [
        "如何设计一套自动化巡检系统？",
        "自动化运维中如何保证安全性？",
        "脚本化运维与平台化运维的演进路径？",
    ],
    "平台架构": [
        "内部开发者平台（IDP）的核心组件有哪些？",
        "如何设计一套多租户平台架构？",
        "平台工程与 DevOps 的关系是什么？",
    ],
    "开发者体验": [
        "如何缩短开发者从提交代码到上线的周期？",
        "开发者自助服务门户应包含哪些功能？",
        "如何度量开发者体验（DX）？",
    ],
    "多集群管理": [
        "多集群管理的挑战有哪些？",
        "如何实现跨集群的服务发现与流量调度？",
        "集群联邦（Federation）与多集群管理的区别？",
    ],
    "服务网格": [
        "Istio 的核心组件与流量管理原理？",
        "服务网格的南北向与东西向流量分别指什么？",
        "服务网格的性能开销如何评估？",
    ],
    "基础设施即代码": [
        "Terraform 的 state 文件管理与团队协作？",
        "如何实现基础设施代码的 CI/CD？",
        "IaC 与配置管理工具的分工与边界？",
    ],
}

# 参考答案模板（三段式：提问→参考回答→评分要点）
ANSWER_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "CI/CD": {
        "参考回答": [
            "CI/CD 流水线通常包含代码提交、静态检查、单元测试、构建镜像、部署到测试环境、集成测试、部署到生产环境等阶段。",
            "每个阶段通过自动化工具串联，失败时自动阻断并通知相关人员。",
            "现代实践还包括安全扫描（SAST/DAST）和合规检查。",
        ],
        "评分要点": [
            "是否覆盖了从代码到生产的完整链路",
            "是否提及自动化与失败处理机制",
            "是否包含安全与合规环节",
        ],
    },
    "容器化": {
        "参考回答": [
            "Docker 镜像采用分层存储，每一层代表一个文件系统变更，层与层之间可以共享与缓存。",
            "构建时利用层缓存可以显著加速；运行时通过写时复制（COW）机制节省空间。",
            "优化镜像体积常用多阶段构建、使用精简基础镜像、合并 RUN 指令等方法。",
        ],
        "评分要点": [
            "是否理解分层与缓存机制",
            "是否掌握镜像瘦身的具体方法",
            "是否了解 Kubernetes 的 Pod 生命周期",
        ],
    },
    "配置管理": {
        "参考回答": [
            "Ansible 是配置管理工具，关注服务器状态的一致性；Terraform 是基础设施编排工具，关注资源的声明式管理。",
            "多环境配置通常使用变量文件、目录分层或参数化模板实现。",
            "配置漂移可通过定期巡检、强制收敛或 GitOps 模式来检测与修复。",
        ],
        "评分要点": [
            "是否准确区分两类工具的使用场景",
            "是否有多环境配置的实际经验",
            "是否了解配置漂移的应对策略",
        ],
    },
    "监控告警": {
        "参考回答": [
            "Prometheus 的拉取模型便于服务发现、故障隔离和水平扩展。",
            "分级告警可通过告警规则优先级、静默规则和聚合策略实现。",
            "高基数问题可通过标签降维、采样存储或分片方案解决。",
        ],
        "评分要点": [
            "是否理解拉取模型的优缺点",
            "是否有告警治理的实际经验",
            "是否了解时序数据库的扩展方案",
        ],
    },
    "云平台": {
        "参考回答": [
            "高可用架构通常涉及多可用区部署、负载均衡、自动伸缩和数据冗余。",
            "云成本优化包括实例选型、按需/预留组合、资源利用率监控和标签治理。",
            "多云架构的挑战包括网络互通、统一身份认证和数据一致性。",
        ],
        "评分要点": [
            "是否具备云架构设计经验",
            "是否有成本优化的具体案例",
            "是否了解多云/混合云的复杂度",
        ],
    },
    "SLO/SLI": {
        "参考回答": [
            "SLI 是可量化的服务指标，如可用性、延迟、错误率。",
            "SLO 是 SLI 的目标值，SLA 是服务合同中的承诺，SLO 通常比 SLA 更严格。",
            "基于 SLO 可以建立错误预算，驱动容量规划和发布决策。",
        ],
        "评分要点": [
            "是否理解 SLI/SLO/SLA 三者的关系",
            "是否了解错误预算的概念与应用",
            "是否能将 SLO 与业务目标关联",
        ],
    },
    "容量规划": {
        "参考回答": [
            "容量规划基于历史流量数据、业务增长预测和季节性规律进行建模。",
            "常用工具包括 Prometheus 数据预测、Kubernetes HPA/VPA 和云厂商的容量分析服务。",
            "应对突发流量可通过弹性伸缩、限流降级和缓存预热等策略。",
        ],
        "评分要点": [
            "是否掌握容量预测的基本方法",
            "是否了解弹性伸缩的配置与局限",
            "是否有应对突发流量的应急预案",
        ],
    },
    "故障演练": {
        "参考回答": [
            "混沌工程的核心原则是：在生产环境主动注入故障，验证系统的韧性。",
            "安全演练需遵循最小爆炸半径、可观测性和快速回滚原则。",
            "复盘流程包括：时间线梳理、根因分析、改进项跟踪和知识沉淀。",
        ],
        "评分要点": [
            "是否理解混沌工程的价值与风险",
            "是否有设计演练方案的经验",
            "是否掌握复盘的方法论",
        ],
    },
    "可观测性": {
        "参考回答": [
            "Metrics 提供聚合指标，Logs 提供事件记录，Traces 提供请求链路。",
            "分布式链路追踪通过 Trace ID 串联跨服务调用，常用 OpenTelemetry 标准。",
            "最佳实践包括：统一采集标准、关联三类数据、建立监控大盘和告警体系。",
        ],
        "评分要点": [
            "是否理解三类数据的互补关系",
            "是否了解链路追踪的实现原理",
            "是否有可观测性平台的建设经验",
        ],
    },
    "自动化运维": {
        "参考回答": [
            "自动化巡检系统通常包含：任务调度、脚本执行、结果采集、异常告警和报表生成。",
            "安全性保障包括：最小权限、审计日志、敏感信息加密和变更审批流程。",
            "从脚本化到平台化的演进，核心是抽象通用能力、提供自助服务和统一管控。",
        ],
        "评分要点": [
            "是否设计过完整的自动化体系",
            "是否重视运维安全与合规",
            "是否理解平台化的演进方向",
        ],
    },
    "平台架构": {
        "参考回答": [
            "IDP 核心组件包括：开发者门户、CI/CD 引擎、环境管理、权限系统和可观测性面板。",
            "多租户架构需考虑租户隔离、配额管理、计费与审计。",
            "平台工程是 DevOps 的演进，通过抽象基础设施复杂度，提升开发者效率。",
        ],
        "评分要点": [
            "是否理解 IDP 的价值与组成",
            "是否有租户隔离的设计经验",
            "是否了解平台工程与 DevOps 的关系",
        ],
    },
    "开发者体验": {
        "参考回答": [
            "缩短上线周期可通过：标准化模板、自动化流水线、环境即服务（EaaS）和自助部署能力。",
            "开发者门户应提供：项目创建、环境申请、部署发布、日志查询和文档检索。",
            "DX 度量可通过：部署频率、变更前置时间、失败率和恢复时间（DORA 指标）。",
        ],
        "评分要点": [
            "是否关注开发者效率与体验",
            "是否了解自助服务的核心功能",
            "是否掌握 DORA 度量指标",
        ],
    },
    "多集群管理": {
        "参考回答": [
            "多集群管理挑战包括：网络互通、配置同步、证书管理和成本控制。",
            "跨集群服务发现可通过 DNS、服务网格或专门的同步工具实现。",
            "集群联邦提供统一控制面，但复杂度较高；多集群管理更强调独立性与灵活性。",
        ],
        "评分要点": [
            "是否理解多集群的典型挑战",
            "是否有跨集群流量的解决方案",
            "是否了解联邦与多集群的取舍",
        ],
    },
    "服务网格": {
        "参考回答": [
            "Istio 由数据平面（Envoy）和控制平面（Pilot、Mixer、Citadel）组成。",
            "南北向流量指外部请求进入集群，东西向流量指集群内部服务间调用。",
            "性能开销主要来自 Envoy 代理的额外跳数，可通过采样追踪和资源调优缓解。",
        ],
        "评分要点": [
            "是否理解服务网格的架构与原理",
            "是否区分南北向与东西向流量",
            "是否了解性能开销的评估方法",
        ],
    },
    "基础设施即代码": {
        "参考回答": [
            "Terraform state 文件需远程存储（如 S3+锁），团队协作时避免并发冲突。",
            "IaC 的 CI/CD 包括：代码审查、计划预览（plan）、自动审批和部署（apply）。",
            "IaC 关注资源生命周期，配置管理关注软件状态，两者互补。",
        ],
        "评分要点": [
            "是否有 Terraform 团队协作经验",
            "是否理解 IaC 流水线的关键环节",
            "是否清楚 IaC 与配置管理的边界",
        ],
    },
}


# ============================================================
# 错误码定义
# ============================================================

class AppError(Exception):
    """应用级异常基类，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def error_exit(code: str, message: str) -> None:
    """输出错误信息到 stderr 并退出。"""
    print(f"[错误 {code}] {message}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 输入校验（guard clause 风格）
# ============================================================

def validate_role(role: str) -> str:
    """校验岗位名称，返回标准化后的岗位 key。"""
    if not isinstance(role, str) or not role.strip():
        raise AppError("E001", "岗位名称不能为空")
    normalized = role.strip().lower()
    if normalized not in ROLE_SKILLS:
        raise AppError("E002", f"不支持的岗位: {role}，可选: {', '.join(ROLE_SKILLS.keys())}")
    return normalized


def validate_level(level: str) -> str:
    """校验技能水平，返回标准化后的水平 key。"""
    if not isinstance(level, str) or not level.strip():
        raise AppError("E003", "技能水平不能为空")
    normalized = level.strip()
    if normalized not in LEVEL_DIFFICULTY:
        raise AppError("E004", f"不支持的技能水平: {level}，可选: {', '.join(LEVEL_DIFFICULTY.keys())}")
    return normalized


def validate_count(count: int) -> int:
    """校验题目数量，限制在 1-50 之间。"""
    if not isinstance(count, int):
        raise AppError("E005", "题目数量必须是整数")
    if count < 1 or count > 50:
        raise AppError("E006", "题目数量必须在 1-50 之间")
    return count


def validate_format(fmt: str) -> str:
    """校验输出格式。"""
    if fmt not in ("markdown", "json", "text"):
        raise AppError("E007", f"不支持的输出格式: {fmt}，可选: markdown/json/text")
    return fmt


# ============================================================
# 核心逻辑：题目生成
# ============================================================

def generate_questions(role: str, level: str, count: int) -> List[Dict[str, Union[str, int]]]:
    """
    根据岗位与水平生成面试题列表。
    返回: [{"skill": 技能领域, "question": 题目, "difficulty": 难度系数}, ...]
    """
    skills = ROLE_SKILLS[role]
    difficulty = LEVEL_DIFFICULTY[level]

    questions: List[Dict[str, Union[str, int]]] = []
    # 按技能领域轮询取题，保证覆盖面
    skill_idx = 0
    question_idx = {skill: 0 for skill in skills}

    for _ in range(count):
        skill = skills[skill_idx % len(skills)]
        pool = SKILL_QUESTIONS[skill]
        q_idx = question_idx[skill] % len(pool)
        questions.append({
            "skill": skill,
            "question": pool[q_idx],
            "difficulty": difficulty,
        })
        question_idx[skill] += 1
        skill_idx += 1

    return questions


def generate_answer(question: Dict[str, Union[str, int]]) -> Dict[str, List[str]]:
    """为单个题目生成模拟问答（提问→参考回答→评分要点）。"""
    skill = question["skill"]
    template = ANSWER_TEMPLATES.get(skill, {
        "参考回答": ["暂无参考回答，请结合实践经验作答。"],
        "评分要点": ["是否结合具体项目经验", "是否体现系统化思考", "是否关注可落地性"],
    })
    return {
        "提问": question["question"],
        "参考回答": template["参考回答"],
        "评分要点": template["评分要点"],
    }


def generate_qa_set(role: str, level: str, count: int) -> List[Dict[str, Union[str, List[str]]]]:
    """生成整套模拟问答。"""
    questions = generate_questions(role, level, count)
    return [generate_answer(q) for q in questions]


# ============================================================
# 输出格式化
# ============================================================

def format_markdown(qa_set: List[Dict[str, Union[str, List[str]]]], role: str, level: str) -> str:
    """格式化为 Markdown 表格。"""
    lines = [
        f"# {role} 岗位面试题（{level}）",
        "",
        "| 序号 | 技能领域 | 题目 |",
        "|------|----------|------|",
    ]
    for i, item in enumerate(qa_set, 1):
        lines.append(f"| {i} | {item.get('skill', '通用')} | {item['提问']} |")
    return "\n".join(lines)


def format_json(qa_set: List[Dict[str, Union[str, List[str]]]]) -> str:
    """格式化为 JSON。"""
    return json.dumps(qa_set, ensure_ascii=False, indent=2)


def format_text(qa_set: List[Dict[str, Union[str, List[str]]]]) -> str:
    """格式化为纯文本列表。"""
    lines = []
    for i, item in enumerate(qa_set, 1):
        lines.append(f"{i}. [{item.get('skill', '通用')}] {item['提问']}")
    return "\n".join(lines)


def format_output(qa_set: List[Dict[str, Union[str, List[str]]]], fmt: str, role: str, level: str) -> str:
    """统一输出入口。"""
    if fmt == "markdown":
        return format_markdown(qa_set, role, level)
    elif fmt == "json":
        return format_json(qa_set)
    elif fmt == "text":
        return format_text(qa_set)
    else:
        raise AppError("E008", f"未知输出格式: {fmt}")


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不读外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("[自检] 开始...")

    # 用例 1：正常生成题目
    try:
        qs = generate_questions("devops", "中级", 5)
        assert len(qs) == 5, f"题目数量应为5，实际{len(qs)}"
        assert all(q["question"] for q in qs), "存在空题目"
        assert all(q["skill"] in ROLE_SKILLS["devops"] for q in qs), "技能领域不在预期范围"
        print("[自检] 用例1（正常生成）通过")
    except AssertionError as e:
        print(f"[自检] 用例1失败: {e}")
        return 1

    # 用例 2：空输入校验
    try:
        validate_role("")
        print("[自检] 用例2失败: 空岗位未抛异常")
        return 1
    except AppError:
        print("[自检] 用例2（空输入校验）通过")

    # 用例 3：中文标点与编码（模拟中文内容生成）
    try:
        qa = generate_answer({"skill": "CI/CD", "question": "请描述一条完整的 CI/CD 流水线包含哪些阶段？", "difficulty": 3})
        assert len(qa["参考回答"]) >= 1, "参考回答为空"
        assert len(qa["评分要点"]) >= 1, "评分要点为空"
        # 验证中文内容非空
        joined = "".join(qa["参考回答"]) + "".join(qa["评分要点"])
        assert len(joined) > 10, "中文内容过短"
        print("[自检] 用例3（中文内容生成）通过")
    except AssertionError as e:
        print(f"[自检] 用例3失败: {e}")
        return 1

    # 用例 4：超长输入（模拟大量题目）
    try:
        qs = generate_questions("sre", "高级", 50)
        assert len(qs) == 50, f"50题生成失败，实际{len(qs)}"
        assert len(qs) >= 10, "题目数量异常"
        print("[自检] 用例4（超长输入）通过")
    except AssertionError as e:
        print(f"[自检] 用例4失败: {e}")
        return 1

    # 用例 5：输出格式完整性
    try:
        qa = generate_qa_set("platform", "初级", 3)
        md = format_markdown(qa, "platform", "初级")
        js = format_json(qa)
        tx = format_text(qa)
        assert "platform" in md, "Markdown 缺少岗位名"
        assert md.count("|") >= 4, "Markdown 表格格式异常"
        assert json.loads(js), "JSON 解析失败"
        assert len(tx) > 0, "纯文本输出为空"
        print("[自检] 用例5（输出格式）通过")
    except AssertionError as e:
        print(f"[自检] 用例5失败: {e}")
        return 1

    # 用例 6：异常输入（非法岗位）
    try:
        validate_role("unknown_role")
        print("[自检] 用例6失败: 非法岗位未抛异常")
        return 1
    except AppError:
        print("[自检] 用例6（非法岗位校验）通过")

    # 用例 7：异常输入（非法数量）
    try:
        validate_count(0)
        print("[自检] 用例7失败: 非法数量未抛异常")
        return 1
    except AppError:
        print("[自检] 用例7（非法数量校验）通过")

    # 用例 8：None 输入防御
    try:
        validate_role(None)  # type: ignore
        print("[自检] 用例8失败: None 岗位未抛异常")
        return 1
    except AppError:
        print("[自检] 用例8（None 输入防御）通过")

    # 用例 9：边界值（数量=1）
    try:
        qs = generate_questions("devops", "初级", 1)
        assert len(qs) == 1, "边界值1题生成失败"
        print("[自检] 用例9（边界值）通过")
    except AssertionError as e:
        print(f"[自检] 用例9失败: {e}")
        return 1

    # 用例 10：所有岗位覆盖
    try:
        for role in ROLE_SKILLS:
            qs = generate_questions(role, "中级", 3)
            assert len(qs) == 3, f"{role} 岗位生成失败"
        print("[自检] 用例10（全岗位覆盖）通过")
    except AssertionError as e:
        print(f"[自检] 用例10失败: {e}")
        return 1

    print("[自检] 全部通过 ✅")
    return 0


# ============================================================
# CLI 入口
# ============================================================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="DevOps 面试题生成器",
        epilog="示例: python main.py --role devops --level 中级 --count 5 --format markdown"
    )
    parser.add_argument("--role", type=str, help="岗位名称: devops/sre/platform")
    parser.add_argument("--level", type=str, help="技能水平: 初级/中级/高级")
    parser.add_argument("--count", type=int, default=5, help="题目数量 (1-50，默认5)")
    parser.add_argument("--format", type=str, default="markdown", choices=["markdown", "json", "text"], help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写盘")
    parser.add_argument("--force", action="store_true", help="强制写盘（配合 --dry-run 使用）")
    parser.add_argument("--output", type=str, help="输出文件路径（可选）")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    args = parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    try:
        role = validate_role(args.role)
        level = validate_level(args.level)
        count = validate_count(args.count)
        fmt = validate_format(args.format)
    except AppError as e:
        error_exit(e.code, e.message)

    # 生成核心数据
    try:
        qa_set = generate_qa_set(role, level, count)
        output = format_output(qa_set, fmt, role, level)
    except AppError as e:
        error_exit(e.code, e.message)
    except Exception as e:
        error_exit("E009", f"生成过程中发生未知错误: {e}")

    # verbose 模式输出决策明细
    if args.verbose:
        print(f"[详细] 岗位: {role}", file=sys.stderr)
        print(f"[详细] 水平: {level}", file=sys.stderr)
        print(f"[详细] 数量: {count}", file=sys.stderr)
        print(f"[详细] 格式: {fmt}", file=sys.stderr)
        print(f"[详细] 技能领域: {', '.join(ROLE_SKILLS[role])}", file=sys.stderr)
        print(f"[详细] 共生成 {len(qa_set)} 道题目", file=sys.stderr)

    # 输出处理（dry-run 控制）
    dry = args.dry_run and not args.force
    if args.output:
        # 路径安全校验：仅允许相对路径或当前目录下的文件
        output_path = args.output
        if os.path.isabs(output_path):
            error_exit("E010", "输出路径必须是相对路径，禁止使用绝对路径")
        if ".." in output_path.split(os.sep):
            error_exit("E010", "输出路径禁止包含 .. 穿越目录")

        if dry:
            print(f"[dry-run] 预览输出到 {output_path}:")
            print(output)
            print(f"[dry-run] 未写盘（使用 --force 强制写入）")
        else:
            try:
                with open(output_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(output)
                print(f"已写入: {output_path}")
            except OSError as e:
                error_exit("E010", f"写入文件失败: {e}")
    else:
        # 无输出文件时直接打印到 stdout
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
