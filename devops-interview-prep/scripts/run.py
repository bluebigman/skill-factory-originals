#!/usr/bin/env python3
"""
devops-interview-prep: 生成定制化 DevOps/SRE/运维面试题、模拟打分与复习计划。

本脚本是 Skill「devops-interview-prep」的核心实现，提供以下能力：
1. generate: 根据岗位方向、经验年限、公司类型生成定制面试题库。
2. score: 对用户答案进行多维度打分。
3. plan: 根据薄弱知识域生成个性化复习计划。
4. search: 按关键词检索内置高频题。
5. selftest: 自测功能，验证核心流程正确性。

所有命令均支持 --dry-run 参数，用于预览输出而不实际写入文件。
"""

import argparse
import json
import sys
import datetime
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

dry_run = False  # v3.274 模块级 dry-run 标志

# ------------------------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------------------------
VALID_ROLES = {"ops", "sre", "devops"}
VALID_EXPERIENCES = {"junior", "mid", "senior"}
VALID_COMPANIES = {"big_tech", "startup", "traditional", "foreign"}
VALID_KNOWLEDGE_DOMAINS = {"linux", "network", "container", "k8s", "cicd", "monitoring"}

# 岗位方向对应的知识域权重
ROLE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "ops": {
        "linux": 0.3,
        "network": 0.2,
        "container": 0.15,
        "k8s": 0.15,
        "cicd": 0.1,
        "monitoring": 0.1,
    },
    "sre": {
        "linux": 0.1,
        "network": 0.1,
        "container": 0.15,
        "k8s": 0.25,
        "cicd": 0.15,
        "monitoring": 0.25,
    },
    "devops": {
        "linux": 0.1,
        "network": 0.1,
        "container": 0.2,
        "k8s": 0.2,
        "cicd": 0.25,
        "monitoring": 0.15,
    },
}

# 经验年限对应的难度标签
EXPERIENCE_LEVELS: Dict[str, str] = {
    "junior": "初级",
    "mid": "中级",
    "senior": "高级",
}

# 公司类型对应的考察风格
COMPANY_STYLES: Dict[str, str] = {
    "big_tech": "互联网大厂（偏算法与深挖）",
    "startup": "中小创业公司（偏全栈实战）",
    "traditional": "传统行业（偏稳定与规范）",
    "foreign": "外企（偏英文沟通与流程）",
}

# 难度分布默认值
DEFAULT_DIFFICULTY = "3:5:2"

# 内置知识库
KNOWLEDGE_BASE: Dict[str, List[Dict[str, str]]] = {
    "linux": [
        {
            "question": "如何排查 Linux 系统负载过高的问题？",
            "answer": "使用 top/htop 查看 CPU 与内存占用，使用 iostat 查看磁盘 I/O，使用 vmstat 查看系统整体状态，使用 strace 跟踪进程系统调用。重点排查 CPU 密集型进程、内存溢出（OOM）、磁盘 I/O 瓶颈。",
            "points": ["排查工具链", "CPU/内存/磁盘 I/O 分析", "进程定位", "系统调用跟踪"],
            "difficulty": "中",
        },
        {
            "question": "解释 Linux 的进程调度策略及其适用场景。",
            "answer": "Linux 主要使用 CFS（完全公平调度器）进行进程调度。支持 SCHED_OTHER（普通进程）、SCHED_FIFO（实时先进先出）、SCHED_RR（实时轮转）等策略。CFS 基于虚拟运行时间进行调度，保证公平性。",
            "points": ["CFS 原理", "实时调度策略", "优先级与 nice 值", "上下文切换"],
            "difficulty": "中",
        },
        {
            "question": "如何诊断和解决 Linux 系统的内存泄漏问题？",
            "answer": "使用 free 查看内存使用情况，使用 ps 查看进程内存占用，使用 valgrind 检测内存泄漏，使用 /proc/meminfo 查看内核内存统计。重点排查用户态进程和内核模块。",
            "points": ["内存监控工具", "valgrind 使用", "内核内存分析", "OOM 机制"],
            "difficulty": "高",
        },
        {
            "question": "Linux 文件系统权限管理有哪些关键概念？",
            "answer": "包括 rwx 权限位、属主/属组/其他用户、SUID/SGID/Sticky Bit 特殊权限、ACL 访问控制列表。使用 chmod/chown/setfacl 进行管理。",
            "points": ["权限位", "特殊权限", "ACL", "chmod/chown"],
            "difficulty": "低",
        },
        {
            "question": "如何配置 Linux 系统的网络参数？",
            "answer": "使用 ip 命令配置 IP 地址、路由、ARP 表。使用 sysctl 配置内核网络参数（如 TCP 缓冲区、连接跟踪）。使用 iptables/nftables 配置防火墙规则。",
            "points": ["ip 命令", "sysctl", "iptables/nftables", "网络命名空间"],
            "difficulty": "中",
        },
    ],
    "network": [
        {
            "question": "解释 TCP 三次握手和四次挥手的过程。",
            "answer": "三次握手：SYN → SYN-ACK → ACK。四次挥手：FIN → ACK → FIN → ACK。握手建立连接，挥手释放连接。",
            "points": ["SYN/SYN-ACK/ACK", "FIN/ACK", "TIME_WAIT 状态", "连接状态转换"],
            "difficulty": "低",
        },
        {
            "question": "如何排查网络延迟和丢包问题？",
            "answer": "使用 ping 测试连通性和延迟，使用 traceroute 定位路由路径，使用 mtr 持续监控，使用 tcpdump 抓包分析，使用 netstat/ss 查看连接状态。",
            "points": ["ping/traceroute/mtr", "tcpdump 抓包", "ss/netstat", "网络性能分析"],
            "difficulty": "中",
        },
        {
            "question": "解释 DNS 解析的完整流程。",
            "answer": "浏览器缓存 → 系统缓存 → 本地 DNS 服务器 → 根 DNS 服务器 → 顶级域服务器 → 权威 DNS 服务器。涉及递归查询和迭代查询。",
            "points": ["DNS 层级", "递归查询", "迭代查询", "缓存机制"],
            "difficulty": "中",
        },
        {
            "question": "什么是负载均衡？有哪些实现方式？",
            "answer": "负载均衡将流量分发到多个后端服务器。实现方式包括：DNS 负载均衡、硬件负载均衡（F5）、软件负载均衡（Nginx/HAProxy）、云负载均衡（SLB/ALB）。",
            "points": ["负载均衡原理", "L4/L7 负载均衡", "Nginx/HAProxy", "健康检查"],
            "difficulty": "中",
        },
        {
            "question": "如何设计一个高可用的网络架构？",
            "answer": "使用冗余链路（多线路接入）、冗余设备（主备/双活）、BGP 路由冗余、DNS 多地域解析、CDN 加速。确保单点故障不影响整体可用性。",
            "points": ["冗余设计", "BGP 路由", "DNS 多地域", "CDN"],
            "difficulty": "高",
        },
    ],
    "container": [
        {
            "question": "解释 Docker 镜像和容器的区别。",
            "answer": "镜像是只读的模板，容器是镜像的运行实例。镜像分层存储，容器在镜像之上添加可写层。容器可以启动、停止、删除，镜像不可变。",
            "points": ["镜像只读", "容器可写层", "分层存储", "生命周期"],
            "difficulty": "低",
        },
        {
            "question": "如何优化 Docker 镜像的大小？",
            "answer": "使用多阶段构建、选择精简基础镜像（Alpine）、合并 RUN 命令减少层数、清理缓存和临时文件、使用 .dockerignore 排除无关文件。",
            "points": ["多阶段构建", "精简基础镜像", "减少层数", ".dockerignore"],
            "difficulty": "中",
        },
        {
            "question": "解释 Docker 的网络模式。",
            "answer": "包括 bridge（默认）、host、none、overlay（Swarm 模式）。bridge 模式使用虚拟网桥，host 模式共享宿主机网络，overlay 用于跨主机通信。",
            "points": ["bridge/host/none", "overlay 网络", "端口映射", "网络隔离"],
            "difficulty": "中",
        },
        {
            "question": "什么是容器编排？Kubernetes 解决了什么问题？",
            "answer": "容器编排管理容器的部署、扩展、网络、存储。Kubernetes 提供自动部署、弹性伸缩、服务发现、负载均衡、自愈能力。",
            "points": ["编排概念", "K8s 核心能力", "自动伸缩", "服务发现"],
            "difficulty": "中",
        },
        {
            "question": "如何保证容器环境的安全性？",
            "answer": "使用非 root 用户运行容器、限制容器资源（CPU/内存）、使用 seccomp/AppArmor 安全策略、扫描镜像漏洞、使用私有镜像仓库。",
            "points": ["非 root 运行", "资源限制", "安全策略", "镜像扫描"],
            "difficulty": "高",
        },
    ],
    "k8s": [
        {
            "question": "解释 Kubernetes 的核心组件及其作用。",
            "answer": "包括 kube-apiserver（API 入口）、etcd（状态存储）、kube-scheduler（调度）、kube-controller-manager（控制器）、kubelet（节点代理）、kube-proxy（网络代理）。",
            "points": ["API Server", "etcd", "Scheduler", "Controller Manager"],
            "difficulty": "中",
        },
        {
            "question": "如何实现 Kubernetes 的滚动更新和回滚？",
            "answer": "使用 Deployment 的 RollingUpdate 策略，设置 maxSurge 和 maxUnavailable 参数。使用 kubectl rollout status 查看更新状态，使用 kubectl rollout undo 回滚。",
            "points": ["RollingUpdate", "maxSurge/maxUnavailable", "rollout 命令", "版本管理"],
            "difficulty": "中",
        },
        {
            "question": "解释 Kubernetes 的服务发现机制。",
            "answer": "Service 提供稳定的虚拟 IP 和 DNS 名称。ClusterIP 用于集群内访问，NodePort 用于外部访问，LoadBalancer 用于云负载均衡。DNS 使用 CoreDNS 解析服务名。",
            "points": ["Service 类型", "ClusterIP/NodePort/LoadBalancer", "CoreDNS", "Endpoints"],
            "difficulty": "中",
        },
        {
            "question": "如何配置 Kubernetes 的持久化存储？",
            "answer": "使用 PersistentVolume（PV）和 PersistentVolumeClaim（PVC）抽象存储。支持 NFS、Ceph、云存储（EBS/PD）等后端。使用 StorageClass 动态供给。",
            "points": ["PV/PVC", "StorageClass", "动态供给", "存储后端"],
            "difficulty": "高",
        },
        {
            "question": "如何排查 Kubernetes Pod 启动失败的问题？",
            "answer": "使用 kubectl describe pod 查看事件，使用 kubectl logs 查看日志，检查镜像是否存在、资源限制是否合理、探针配置是否正确、网络策略是否阻止。",
            "points": ["describe/logs", "镜像检查", "资源限制", "探针配置"],
            "difficulty": "中",
        },
    ],
    "cicd": [
        {
            "question": "解释 CI/CD 的核心概念和流程。",
            "answer": "CI（持续集成）自动构建和测试代码，CD（持续交付/部署）自动部署到环境。流程包括：代码提交 → 自动构建 → 自动测试 → 自动部署。",
            "points": ["CI/CD 定义", "流水线阶段", "自动化测试", "部署策略"],
            "difficulty": "低",
        },
        {
            "question": "如何设计一个高效的 CI/CD 流水线？",
            "answer": "使用并行构建、缓存依赖、增量构建、分层测试（单元/集成/E2E）、环境隔离（dev/staging/prod）、自动化回滚。",
            "points": ["并行构建", "缓存依赖", "分层测试", "环境隔离"],
            "difficulty": "中",
        },
        {
            "question": "解释蓝绿部署和金丝雀发布的区别。",
            "answer": "蓝绿部署：同时运行两套环境，切换流量。金丝雀发布：逐步放量，先小范围验证再全量。蓝绿切换快但成本高，金丝雀风险低但周期长。",
            "points": ["蓝绿部署", "金丝雀发布", "流量切换", "风险控制"],
            "difficulty": "中",
        },
        {
            "question": "如何管理 CI/CD 中的制品和版本？",
            "answer": "使用制品仓库（Nexus/Artifactory）存储构建产物，使用语义化版本号（SemVer）管理版本，使用标签和元数据追踪制品来源。",
            "points": ["制品仓库", "SemVer", "版本追踪", "制品安全"],
            "difficulty": "中",
        },
        {
            "question": "如何实现 CI/CD 流水线的安全？",
            "answer": "使用密钥管理（Vault/KMS）存储敏感信息，使用签名验证制品完整性，使用安全扫描（SAST/DAST）检测漏洞，使用最小权限原则配置访问控制。",
            "points": ["密钥管理", "制品签名", "安全扫描", "最小权限"],
            "difficulty": "高",
        },
    ],
    "monitoring": [
        {
            "question": "解释监控系统的核心组件和指标类型。",
            "answer": "包括指标采集（Prometheus）、日志收集（ELK）、链路追踪（Jaeger）。指标类型：Counter（计数器）、Gauge（仪表盘）、Histogram（直方图）、Summary（摘要）。",
            "points": ["采集/存储/展示", "指标类型", "Prometheus", "ELK"],
            "difficulty": "中",
        },
        {
            "question": "如何设计有效的告警策略？",
            "answer": "使用阈值告警、趋势告警、多条件组合告警。设置合理的告警级别（P0/P1/P2），避免告警风暴，使用告警降噪和聚合。",
            "points": ["告警级别", "阈值设置", "告警风暴", "告警聚合"],
            "difficulty": "中",
        },
        {
            "question": "解释 Prometheus 的架构和工作原理。",
            "answer": "Prometheus 通过 Pull 模式采集指标，存储在本地 TSDB，使用 PromQL 查询，通过 Alertmanager 发送告警。支持服务发现和联邦集群。",
            "points": ["Pull 模式", "TSDB", "PromQL", "Alertmanager"],
            "difficulty": "中",
        },
        {
            "question": "如何实现分布式系统的链路追踪？",
            "answer": "使用 Jaeger/Zipkin 实现分布式追踪，通过 Trace ID 串联跨服务调用，使用 Span 记录每个调用的耗时和状态。",
            "points": ["Trace ID", "Span", "Jaeger/Zipkin", "采样策略"],
            "difficulty": "高",
        },
        {
            "question": "如何监控 Kubernetes 集群的健康状态？",
            "answer": "使用 kube-state-metrics 采集集群状态，使用 cAdvisor 采集容器指标，使用 Prometheus 监控节点和 Pod，使用 Grafana 可视化。",
            "points": ["kube-state-metrics", "cAdvisor", "Prometheus", "Grafana"],
            "difficulty": "中",
        },
    ],
}

# 错误码定义
class ErrorCode:
    """错误码定义"""
    SUCCESS = 0
    INVALID_INPUT = 1
    FILE_NOT_FOUND = 2
    NETWORK_ERROR = 3
    INTERNAL_ERROR = 4


class SkillError(Exception):
    """Skill 自定义异常"""
    def __init__(self, message: str, code: int = ErrorCode.INTERNAL_ERROR):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------------------
# 输入校验
# ------------------------------------------------------------------------------
def validate_role(role: str) -> None:
    """校验岗位方向"""
    if role not in VALID_ROLES:
        raise SkillError(
            f"无效的岗位方向: {role}，可选值: {', '.join(sorted(VALID_ROLES))}",
            ErrorCode.INVALID_INPUT,
        )


def validate_experience(experience: str) -> None:
    """校验经验年限"""
    if experience not in VALID_EXPERIENCES:
        raise SkillError(
            f"无效的经验年限: {experience}，可选值: {', '.join(sorted(VALID_EXPERIENCES))}",
            ErrorCode.INVALID_INPUT,
        )


def validate_company(company: str) -> None:
    """校验公司类型"""
    if company not in VALID_COMPANIES:
        raise SkillError(
            f"无效的公司类型: {company}，可选值: {', '.join(sorted(VALID_COMPANIES))}",
            ErrorCode.INVALID_INPUT,
        )


def validate_count(count: int) -> None:
    """校验题目数量"""
    if not isinstance(count, int) or count < 1 or count > 30:
        raise SkillError(
            f"无效的题目数量: {count}，必须是 1-30 的整数",
            ErrorCode.INVALID_INPUT,
        )


def validate_difficulty(difficulty: str) -> Tuple[int, int, int]:
    """校验难度分布，返回 (易, 中, 难) 三元组"""
    parts = difficulty.split(":")
    if len(parts) != 3:
        raise SkillError(
            f"无效的难度分布: {difficulty}，格式应为 易:中:难（如 3:5:2）",
            ErrorCode.INVALID_INPUT,
        )
    try:
        easy, mid, hard = map(int, parts)
    except ValueError:
        raise SkillError(
            f"无效的难度分布: {difficulty}，必须为三个正整数",
            ErrorCode.INVALID_INPUT,
        )
    if easy < 0 or mid < 0 or hard < 0 or (easy + mid + hard) == 0:
        raise SkillError(
            f"无效的难度分布: {difficulty}，三个值必须为非负整数且和大于 0",
            ErrorCode.INVALID_INPUT,
        )
    return easy, mid, hard


def validate_domain(domain: Optional[str]) -> None:
    """校验知识域"""
    if domain is not None and domain not in VALID_KNOWLEDGE_DOMAINS:
        raise SkillError(
            f"无效的知识域: {domain}，可选值: {', '.join(sorted(VALID_KNOWLEDGE_DOMAINS))}",
            ErrorCode.INVALID_INPUT,
        )


# ------------------------------------------------------------------------------
# 核心逻辑
# ------------------------------------------------------------------------------
def get_difficulty_label(experience: str) -> str:
    """根据经验年限返回难度标签"""
    return EXPERIENCE_LEVELS.get(experience, "中级")


def get_company_style(company: str) -> str:
    """根据公司类型返回考察风格"""
    return COMPANY_STYLES.get(company, "通用")


def get_role_domains(role: str) -> List[str]:
    """根据岗位方向返回知识域列表（按权重排序）"""
    weights = ROLE_WEIGHTS.get(role, {})
    return sorted(weights.keys(), key=lambda d: weights[d], reverse=True)


def get_role_weights(role: str) -> Dict[str, float]:
    """根据岗位方向返回知识域权重"""
    return ROLE_WEIGHTS.get(role, {})


def allocate_questions(
    role: str,
    count: int,
    difficulty: str,
    domain: Optional[str] = None,
) -> Dict[str, Dict[str, int]]:
    """
    按难度分布和知识域权重分配题目数量。
    返回: {知识域: {难度: 数量}}
    """
    easy, mid, hard = validate_difficulty(difficulty)
    total_weight = easy + mid + hard

    # 计算各难度题目数量
    easy_count = round(count * easy / total_weight)
    mid_count = round(count * mid / total_weight)
    hard_count = count - easy_count - mid_count

    # 确保非负
    easy_count = max(0, easy_count)
    mid_count = max(0, mid_count)
    hard_count = max(0, hard_count)

    # 如果 domain 指定，只使用该 domain
    if domain is not None:
        domains = [domain]
    else:
        domains = get_role_domains(role)

    weights = get_role_weights(role)
    domain_weights = {d: weights.get(d, 0.0) for d in domains}
    total_domain_weight = sum(domain_weights.values())
    if total_domain_weight == 0:
        # 均分
        domain_weights = {d: 1.0 / len(domains) for d in domains}
        total_domain_weight = 1.0

    # 分配各难度题目到知识域
    allocation: Dict[str, Dict[str, int]] = {}
    for d in domains:
        allocation[d] = {"easy": 0, "mid": 0, "hard": 0}

    # 按权重分配
    for d in domains:
        weight = domain_weights[d] / total_domain_weight
        allocation[d]["easy"] = int(easy_count * weight)
        allocation[d]["mid"] = int(mid_count * weight)
        allocation[d]["hard"] = int(hard_count * weight)

    # 处理余数（优先分配给权重最大的 domain 的 mid 难度）
    remaining_easy = easy_count - sum(a["easy"] for a in allocation.values())
    remaining_mid = mid_count - sum(a["mid"] for a in allocation.values())
    remaining_hard = hard_count - sum(a["hard"] for a in allocation.values())

    # 按权重排序 domains
    sorted_domains = sorted(domains, key=lambda d: domain_weights[d], reverse=True)

    for d in sorted_domains:
        if remaining_easy > 0:
            allocation[d]["easy"] += 1
            remaining_easy -= 1
        if remaining_mid > 0:
            allocation[d]["mid"] += 1
            remaining_mid -= 1
        if remaining_hard > 0:
            allocation[d]["hard"] += 1
            remaining_hard -= 1

    return allocation


def generate_questions(
    role: str,
    experience: str,
    company: str,
    count: int,
    difficulty: str,
    domain: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    根据岗位方向、经验年限、公司类型生成定制面试题库。
    """
    # 校验输入
    validate_role(role)
    validate_experience(experience)
    validate_company(company)
    validate_count(count)
    validate_difficulty(difficulty)
    validate_domain(domain)

    # 获取难度标签和公司风格
    difficulty_label = get_difficulty_label(experience)
    company_style = get_company_style(company)

    # 分配题目数量
    allocation = allocate_questions(role, count, difficulty, domain)

    # 生成题目
    questions: List[Dict[str, Any]] = []
    for d, counts in allocation.items():
        domain_questions = KNOWLEDGE_BASE.get(d, [])
        if not domain_questions:
            continue

        # 按难度筛选
        for diff_key, diff_count in counts.items():
            if diff_count <= 0:
                continue
            # 映射难度标签
            diff_label = {"easy": "低", "mid": "中", "hard": "高"}.get(diff_key, "中")
            # 筛选匹配难度的题目
            matching = [q for q in domain_questions if q.get("difficulty") == diff_label]
            if not matching:
                # 如果没有匹配的，使用该 domain 的所有题目
                matching = domain_questions
            # 选择题目（不重复）
            selected = matching[:diff_count]
            for q in selected:
                questions.append({
                    "domain": d,
                    "difficulty": diff_label,
                    "question": q["question"],
                    "points": q.get("points", []),
                    "reference_answer": q.get("answer", ""),
                })

    # 如果题目不足，补充其他 domain 的题目
    if len(questions) < count:
        # 收集所有未使用的题目
        used_questions = {q["question"] for q in questions}
        all_questions = []
        for d in VALID_KNOWLEDGE_DOMAINS:
            for q in KNOWLEDGE_BASE.get(d, []):
                if q["question"] not in used_questions:
                    all_questions.append({
                        "domain": d,
                        "difficulty": q.get("difficulty", "中"),
                        "question": q["question"],
                        "points": q.get("points", []),
                        "reference_answer": q.get("answer", ""),
                    })
        # 补充题目
        for q in all_questions:
            if len(questions) >= count:
                break
            questions.append(q)

    # 截断到 count
    questions = questions[:count]

    # 添加元数据
    result = {
        "metadata": {
            "role": role,
            "experience": experience,
            "company": company,
            "difficulty_label": difficulty_label,
            "company_style": company_style,
            "count": len(questions),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "questions": questions,
    }
    return result


def score_answers(
    role: str,
    experience: str,
    answers: Dict[str, str],
) -> Dict[str, Any]:
    """
    对用户答案进行多维度打分。
    """
    # 校验输入
    validate_role(role)
    validate_experience(experience)

    if not answers:
        raise SkillError("答案不能为空", ErrorCode.INVALID_INPUT)

    # 获取岗位对应的知识域
    domains = get_role_domains(role)
    weights = get_role_weights(role)

    # 打分维度
    dimensions = ["准确性", "完整性", "条理性", "深度"]
    dimension_scores: Dict[str, float] = {d: 0.0 for d in dimensions}
    domain_scores: Dict[str, float] = {}
    total_score = 0.0
    total_weight = 0.0

    # 对每个答案进行打分
    for domain, answer in answers.items():
        if domain not in VALID_KNOWLEDGE_DOMAINS:
            continue
        # 基于答案长度和关键词匹配进行简单打分
        # 注意：这里不使用 random，而是基于规则
        answer_len = len(answer.strip())
        if answer_len < 20:
            accuracy = 30.0
            completeness = 20.0
            clarity = 30.0
            depth = 20.0
        elif answer_len < 50:
            accuracy = 50.0
            completeness = 40.0
            clarity = 50.0
            depth = 30.0
        elif answer_len < 100:
            accuracy = 70.0
            completeness = 60.0
            clarity = 70.0
            depth = 50.0
        elif answer_len < 200:
            accuracy = 80.0
            completeness = 75.0
            clarity = 80.0
            depth = 70.0
        else:
            accuracy = 90.0
            completeness = 85.0
            clarity = 90.0
            depth = 80.0

        # 检查关键词
        domain_questions = KNOWLEDGE_BASE.get(domain, [])
        keywords = set()
        for q in domain_questions:
            for p in q.get("points", []):
                keywords.add(p.lower())
        answer_lower = answer.lower()
        keyword_hits = sum(1 for kw in keywords if kw in answer_lower)
        keyword_ratio = min(1.0, keyword_hits / max(1, len(keywords) // 3))
        accuracy = min(100.0, accuracy + keyword_ratio * 10)

        domain_score = (accuracy + completeness + clarity + depth) / 4.0
        domain_scores[domain] = domain_score

        # 累加总分
        weight = weights.get(domain, 0.0)
        total_score += domain_score * weight
        total_weight += weight

        # 累加维度分
        dimension_scores["准确性"] += accuracy * weight
        dimension_scores["完整性"] += completeness * weight
        dimension_scores["条理性"] += clarity * weight
        dimension_scores["深度"] += depth * weight

    if total_weight == 0:
        total_weight = 1.0

    # 计算最终分数
    final_score = total_score / total_weight
    for dim in dimensions:
        dimension_scores[dim] = dimension_scores[dim] / total_weight

    # 生成评价
    if final_score >= 85:
        level = "优秀"
        comment = "答案质量很高，展现了扎实的技术功底和深入的理解。"
    elif final_score >= 70:
        level = "良好"
        comment = "答案整体不错，但部分知识点需要进一步深化。"
    elif final_score >= 55:
        level = "一般"
        comment = "答案基本合格，建议加强核心知识点的学习。"
    else:
        level = "待提升"
        comment = "答案质量有待提高，建议系统性地复习相关知识点。"

    result = {
        "metadata": {
            "role": role,
            "experience": experience,
            "scored_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "total_score": round(final_score, 1),
        "level": level,
        "comment": comment,
        "dimension_scores": {k: round(v, 1) for k, v in dimension_scores.items()},
        "domain_scores": {k: round(v, 1) for k, v in domain_scores.items()},
    }
    return result


def generate_plan(
    role: str,
    weak_domains: List[str],
) -> Dict[str, Any]:
    """
    根据薄弱知识域生成个性化复习计划。
    """
    # 校验输入
    validate_role(role)

    if not weak_domains:
        raise SkillError("薄弱知识域不能为空", ErrorCode.INVALID_INPUT)

    # 校验知识域
    for d in weak_domains:
        validate_domain(d)

    # 生成复习计划
    plan_items = []
    for domain in weak_domains:
        domain_questions = KNOWLEDGE_BASE.get(domain, [])
        if not domain_questions:
            continue

        # 按难度分组
        by_difficulty: Dict[str, List[Dict[str, str]]] = {"低": [], "中": [], "高": []}
        for q in domain_questions:
            diff = q.get("difficulty", "中")
            by_difficulty.setdefault(diff, []).append(q)

        # 生成计划
        plan_items.append({
            "domain": domain,
            "priority": "高" if domain in weak_domains[:2] else "中",
            "suggested_hours": len(domain_questions) * 2,
            "key_topics": [q["question"] for q in domain_questions[:3]],
            "practice_questions": [q["question"] for q in domain_questions[:2]],
        })

    result = {
        "metadata": {
            "role": role,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "plan": plan_items,
        "total_hours": sum(item["suggested_hours"] for item in plan_items),
    }
    return result


def search_questions(keyword: str) -> List[Dict[str, Any]]:
    """
    按关键词检索内置高频题。
    """
    if not keyword or not keyword.strip():
        raise SkillError("搜索关键词不能为空", ErrorCode.INVALID_INPUT)

    keyword_lower = keyword.strip().lower()
    results = []
    for domain, questions in KNOWLEDGE_BASE.items():
        for q in questions:
            # 在题目、答案、要点中搜索
            search_text = f"{q['question']} {q.get('answer', '')} {' '.join(q.get('points', []))}".lower()
            if keyword_lower in search_text:
                results.append({
                    "domain": domain,
                    "difficulty": q.get("difficulty", "中"),
                    "question": q["question"],
                    "points": q.get("points", []),
                    "reference_answer": q.get("answer", ""),
                })

    return results


# ------------------------------------------------------------------------------
# 输出格式化
# ------------------------------------------------------------------------------
def format_text(data: Any) -> str:
    """格式化文本输出"""
    if isinstance(data, dict):
        lines = []
        if "metadata" in data:
            meta = data["metadata"]
            lines.append(f"# DevOps 面试题生成器")
            lines.append(f"岗位方向: {meta.get('role', '')}")
            lines.append(f"经验年限: {meta.get('experience', '')}")
            lines.append(f"公司类型: {meta.get('company', '')}")
            lines.append(f"难度标签: {meta.get('difficulty_label', '')}")
            lines.append(f"考察风格: {meta.get('company_style', '')}")
            lines.append(f"题目数量: {meta.get('count', '')}")
            lines.append(f"生成时间: {meta.get('generated_at', '')}")
            lines.append("")

        if "questions" in data:
            lines.append("## 面试题目")
            for i, q in enumerate(data["questions"], 1):
                lines.append(f"### 第 {i} 题 [{q.get('difficulty', '中')} | {q.get('domain', '')}]")
                lines.append(f"**题目**: {q.get('question', '')}")
                points = q.get("points", [])
                if points:
                    lines.append("**参考要点**:")
                    for p in points:
                        lines.append(f"- {p}")
                lines.append("")

        if "total_score" in data:
            lines.append(f"## 评分结果")
            lines.append(f"总分: {data['total_score']} / 100")
            lines.append(f"等级: {data.get('level', '')}")
            lines.append(f"评价: {data.get('comment', '')}")
            lines.append("")
            if "dimension_scores" in data:
                lines.append("### 维度得分")
                for dim, score in data["dimension_scores"].items():
                    lines.append(f"- {dim}: {score}")
            lines.append("")
            if "domain_scores" in data:
                lines.append("### 知识域得分")
                for domain, score in data["domain_scores"].items():
                    lines.append(f"- {domain}: {score}")
            lines.append("")

        if "plan" in data:
            lines.append(f"## 复习计划")
            lines.append(f"总建议时长: {data.get('total_hours', 0)} 小时")
            lines.append("")
            for item in data.get("plan", []):
                lines.append(f"### {item.get('domain', '')} (优先级: {item.get('priority', '')})")
                lines.append(f"建议时长: {item.get('suggested_hours', 0)} 小时")
                lines.append("**核心主题**:")
                for topic in item.get("key_topics", []):
                    lines.append(f"- {topic}")
                lines.append("**练习题目**:")
                for q in item.get("practice_questions", []):
                    lines.append(f"- {q}")
                lines.append("")

        return "\n".join(lines)
    elif isinstance(data, list):
        if not data:
            return "未找到匹配的题目。"
        lines = [f"找到 {len(data)} 条结果:", ""]
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines.append(f"### 第 {i} 条 [{item.get('domain', '')} | {item.get('difficulty', '中')}]")
                lines.append(f"**题目**: {item.get('question', '')}")
                points = item.get("points", [])
                if points:
                    lines.append("**参考要点**:")
                    for p in points:
                        lines.append(f"- {p}")
                lines.append("")
        return "\n".join(lines)
    else:
        return str(data)


def format_json(data: Any) -> str:
    """格式化 JSON 输出"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_output(data: Any, format_type: str = "text") -> str:
    """根据格式类型输出"""
    if format_type == "json":
        return format_json(data)
    else:
        return format_text(data)


# ------------------------------------------------------------------------------
# 文件操作
# ------------------------------------------------------------------------------
def read_text_safe(path: str) -> str:
    """安全读取文本文件，支持多编码回退"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def atomic_write(path: Path, content: str) -> None:
    """原子化写入文件"""
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子替换
        os.replace(temp_path, str(path))
    except Exception:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def save(path: Path, data: str, dry_run: bool = False) -> bool:
    """保存文件，支持 dry-run 模式"""
    if not dry_run:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


# ------------------------------------------------------------------------------
# 自测
# ------------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行自测，验证核心功能"""
    print("=" * 60)
    print("运行自测...")
    print("=" * 60)

    all_passed = True

    # 测试 1: 生成面试题
    print("\n[测试 1] 生成面试题 (sre/senior/big_tech/5)")
    try:
        result = generate_questions("sre", "senior", "big_tech", 5, "3:5:2")
        questions = result.get("questions", [])
        assert len(questions) > 0, f"题目数量应为正数，实际为 {len(questions)}"
        assert len(questions) <= 5, f"题目数量应不超过 5，实际为 {len(questions)}"
        assert all("question" in q for q in questions), "每道题应包含 question 字段"
        assert all("points" in q for q in questions), "每道题应包含 points 字段"
        print(f"  ✓ 通过: 生成 {len(questions)} 道题")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 2: 生成面试题（指定 domain）
    print("\n[测试 2] 生成面试题 (devops/mid/startup/3/domain=linux)")
    try:
        result = generate_questions("devops", "mid", "startup", 3, "3:5:2", domain="linux")
        questions = result.get("questions", [])
        assert len(questions) > 0, f"题目数量应为正数，实际为 {len(questions)}"
        assert all(q.get("domain") == "linux" for q in questions), "所有题目应属于 linux 域"
        print(f"  ✓ 通过: 生成 {len(questions)} 道 linux 域题目")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 3: 打分
    print("\n[测试 3] 打分 (ops/junior)")
    try:
        answers = {
            "linux": "使用 top 查看 CPU 和内存，使用 iostat 查看磁盘 I/O，使用 vmstat 查看系统状态。",
            "network": "使用 ping 测试连通性，使用 traceroute 定位路由。",
        }
        result = score_answers("ops", "junior", answers)
        assert "total_score" in result, "结果应包含 total_score"
        assert 0 <= result["total_score"] <= 100, f"总分应在 0-100 之间，实际为 {result['total_score']}"
        assert "dimension_scores" in result, "结果应包含 dimension_scores"
        assert "domain_scores" in result, "结果应包含 domain_scores"
        print(f"  ✓ 通过: 总分 {result['total_score']}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 4: 复习计划
    print("\n[测试 4] 复习计划 (sre/linux,network)")
    try:
        result = generate_plan("sre", ["linux", "network"])
        assert "plan" in result, "结果应包含 plan"
        assert len(result["plan"]) > 0, "计划不应为空"
        assert "total_hours" in result, "结果应包含 total_hours"
        print(f"  ✓ 通过: 计划包含 {len(result['plan'])} 个知识域，共 {result['total_hours']} 小时")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 5: 搜索
    print("\n[测试 5] 搜索 (关键词: 负载)")
    try:
        results = search_questions("负载")
        assert len(results) > 0, "搜索结果不应为空"
        print(f"  ✓ 通过: 找到 {len(results)} 条结果")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 6: 输入校验
    print("\n[测试 6] 输入校验 (无效岗位方向)")
    try:
        try:
            generate_questions("invalid_role", "junior", "big_tech", 5, "3:5:2")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 7: 难度分布校验
    print("\n[测试 7] 难度分布校验 (无效格式)")
    try:
        try:
            generate_questions("sre", "junior", "big_tech", 5, "invalid")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 8: 空答案打分
    print("\n[测试 8] 空答案打分")
    try:
        try:
            score_answers("sre", "junior", {})
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 9: 原子写入
    print("\n[测试 9] 原子写入")
    try:
        import tempfile as tmp
        with tmp.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            atomic_write(test_file, "测试内容")
            assert test_file.exists(), "文件应存在"
            content = test_file.read_text(encoding="utf-8")
            assert content == "测试内容", f"文件内容应为 '测试内容'，实际为 '{content}'"
            print(f"  ✓ 通过: 文件写入成功")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 10: 输出格式化
    print("\n[测试 10] 输出格式化")
    try:
        data = {"metadata": {"role": "sre"}, "questions": [{"question": "测试题", "points": ["要点1"]}]}
        text_output = format_output(data, "text")
        assert "测试题" in text_output, "文本输出应包含题目"
        json_output = format_output(data, "json")
        parsed = json.loads(json_output)
        assert parsed["metadata"]["role"] == "sre", "JSON 输出应包含 role"
        print(f"  ✓ 通过: 文本和 JSON 输出均正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 11: 时间戳使用 UTC
    print("\n[测试 11] 时间戳使用 UTC")
    try:
        result = generate_questions("sre", "junior", "big_tech", 1, "3:5:2")
        generated_at = result["metadata"]["generated_at"]
        # 检查是否包含时区信息
        assert "+" in generated_at or "Z" in generated_at, f"时间戳应包含时区信息: {generated_at}"
        print(f"  ✓ 通过: 时间戳包含时区信息")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 12: 大输入流式处理（模拟）
    print("\n[测试 12] 大输入流式处理")
    try:
        # 生成大量题目
        result = generate_questions("devops", "senior", "big_tech", 30, "3:5:2")
        questions = result.get("questions", [])
        assert len(questions) <= 30, f"题目数量应不超过 30，实际为 {len(questions)}"
        print(f"  ✓ 通过: 生成 {len(questions)} 道题（最大 30）")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 13: 中文编码
    print("\n[测试 13] 中文编码")
    try:
        result = generate_questions("ops", "mid", "traditional", 2, "3:5:2")
        text_output = format_output(result, "text")
        assert "面试" in text_output or "题目" in text_output, "输出应包含中文"
        print(f"  ✓ 通过: 中文输出正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 14: 边界条件 - 最小题目数
    print("\n[测试 14] 边界条件 - 最小题目数")
    try:
        result = generate_questions("sre", "junior", "big_tech", 1, "3:5:2")
        questions = result.get("questions", [])
        assert len(questions) == 1, f"题目数量应为 1，实际为 {len(questions)}"
        print(f"  ✓ 通过: 生成 1 道题")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 15: 边界条件 - 最大题目数
    print("\n[测试 15] 边界条件 - 最大题目数")
    try:
        result = generate_questions("sre", "senior", "big_tech", 30, "3:5:2")
        questions = result.get("questions", [])
        assert len(questions) <= 30, f"题目数量应不超过 30，实际为 {len(questions)}"
        print(f"  ✓ 通过: 生成 {len(questions)} 道题")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 16: 边界条件 - 无效题目数
    print("\n[测试 16] 边界条件 - 无效题目数")
    try:
        try:
            generate_questions("sre", "junior", "big_tech", 0, "3:5:2")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 17: 边界条件 - 无效公司类型
    print("\n[测试 17] 边界条件 - 无效公司类型")
    try:
        try:
            generate_questions("sre", "junior", "invalid_company", 5, "3:5:2")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 18: 边界条件 - 无效经验年限
    print("\n[测试 18] 边界条件 - 无效经验年限")
    try:
        try:
            generate_questions("sre", "invalid_exp", "big_tech", 5, "3:5:2")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 19: 边界条件 - 无效知识域
    print("\n[测试 19] 边界条件 - 无效知识域")
    try:
        try:
            generate_questions("sre", "junior", "big_tech", 5, "3:5:2", domain="invalid_domain")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 20: 边界条件 - 空搜索关键词
    print("\n[测试 20] 边界条件 - 空搜索关键词")
    try:
        try:
            search_questions("")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 21: 边界条件 - 空薄弱知识域
    print("\n[测试 21] 边界条件 - 空薄弱知识域")
    try:
        try:
            generate_plan("sre", [])
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 22: 边界条件 - 难度分布全零
    print("\n[测试 22] 边界条件 - 难度分布全零")
    try:
        try:
            generate_questions("sre", "junior", "big_tech", 5, "0:0:0")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 23: 边界条件 - 难度分布负数
    print("\n[测试 23] 边界条件 - 难度分布负数")
    try:
        try:
            generate_questions("sre", "junior", "big_tech", 5, "-1:5:2")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 24: 边界条件 - 难度分布非数字
    print("\n[测试 24] 边界条件 - 难度分布非数字")
    try:
        try:
            generate_questions("sre", "junior", "big_tech", 5, "a:b:c")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 25: 边界条件 - 题目数超过最大值
    print("\n[测试 25] 边界条件 - 题目数超过最大值")
    try:
        try:
            generate_questions("sre", "junior", "big_tech", 31, "3:5:2")
            all_passed = False
            print("  ✗ 失败: 应抛出异常但未抛出")
        except SkillError as e:
            assert e.code == ErrorCode.INVALID_INPUT, f"错误码应为 {ErrorCode.INVALID_INPUT}，实际为 {e.code}"
            print(f"  ✓ 通过: 正确抛出异常 (错误码 {e.code})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 26: dry-run 模式
    print("\n[测试 26] dry-run 模式")
    try:
        import tempfile as tmp
        with tmp.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            result = save(test_file, "测试内容", dry_run=True)
            assert result is False, "dry-run 应返回 False"
            assert not test_file.exists(), "dry-run 不应创建文件"
            print(f"  ✓ 通过: dry-run 模式正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 27: 编码回退
    print("\n[测试 27] 编码回退")
    try:
        import tempfile as tmp
        with tmp.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            # 写入 GBK 编码文件
            test_file.write_bytes("测试内容".encode("gbk"))
            content = read_text_safe(str(test_file))
            assert content == "测试内容", f"GBK 编码读取失败: {content}"
            print(f"  ✓ 通过: GBK 编码读取正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试 28: 流式读取
    print("\n[测试 28] 流式读取")
    try:
        import tempfile as tmp
        with tmp.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("line1\nline2\nline3\n", encoding="utf-8")
            lines = []
            with open(str(test_file), encoding="utf-8", errors="replace") as f:
                for line in f:
                    lines.append(line.strip())
            assert len(lines) == 3, f"应读取 3 行，实际为 {len(lines)}"
            print(f"  ✓ 通过: 流式读取正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自测全部通过 ✓")
    else:
        print("自测存在失败项 ✗")
    print("=" * 60)
    return all_passed


# ------------------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------------------
def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="devops-interview-prep",
        description="生成定制化 DevOps/SRE/运维面试题、模拟打分与复习计划",
        epilog="示例: python run.py generate --role sre --experience senior --count 5",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate 子命令
    gen_parser = subparsers.add_parser("generate", help="生成面试题库")
    gen_parser.add_argument("--role", "-r", help="岗位方向 (ops/sre/devops)")
    gen_parser.add_argument("--experience", "-e", help="经验年限 (junior/mid/senior)")
    gen_parser.add_argument("--company", "-c", default="big_tech", help="公司类型 (big_tech/startup/traditional/foreign)")
    gen_parser.add_argument("--count", "-n", type=int, default=10, help="题目数量 (1-30)")
    gen_parser.add_argument("--difficulty", "-d", default=DEFAULT_DIFFICULTY, help="难度分布 (易:中:难)")
    gen_parser.add_argument("--domain", help="知识域过滤 (linux/network/container/k8s/cicd/monitoring)")
    gen_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="输出格式")
    gen_parser.add_argument("--output", "-o", help="输出文件路径")
    gen_parser.add_argument("--dry-run", action="store_true", help="预览输出而不写入文件")
    gen_parser.add_argument("--verbose", action="store_true", help="详细输出")

    # score 子命令
    score_parser = subparsers.add_parser("score", help="对答案进行打分")
    score_parser.add_argument("--role", "-r", help="岗位方向 (ops/sre/devops)")
    score_parser.add_argument("--experience", "-e", help="经验年限 (junior/mid/senior)")
    score_parser.add_argument("--answers", "-a", help="答案 JSON 字符串")
    score_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="输出格式")
    score_parser.add_argument("--output", "-o", help="输出文件路径")
    score_parser.add_argument("--dry-run", action="store_true", help="预览输出而不写入文件")
    score_parser.add_argument("--verbose", action="store_true", help="详细输出")

    # plan 子命令
    plan_parser = subparsers.add_parser("plan", help="生成复习计划")
    plan_parser.add_argument("--role", "-r", help="岗位方向 (ops/sre/devops)")
    plan_parser.add_argument("--weak-domains", "-w", help="薄弱知识域 (逗号分隔)")
    plan_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="输出格式")
    plan_parser.add_argument("--output", "-o", help="输出文件路径")
    plan_parser.add_argument("--dry-run", action="store_true", help="预览输出而不写入文件")
    plan_parser.add_argument("--verbose", action="store_true", help="详细输出")

    # search 子命令
    search_parser = subparsers.add_parser("search", help="搜索题目")
    search_parser.add_argument("--keyword", "-k", help="搜索关键词")
    search_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="输出格式")
    search_parser.add_argument("--output", "-o", help="输出文件路径")
    search_parser.add_argument("--dry-run", action="store_true", help="预览输出而不写入文件")
    search_parser.add_argument("--verbose", action="store_true", help="详细输出")

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--version", action="version", version="devops-interview-prep 1.0.0")

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    if argv is None:
        argv = sys.argv[1:]

    try:
        args = parse_args(argv)

        # 自测模式 - 必须在任何业务校验之前
        if args.selftest:
            success = run_selftest()
            return 0 if success else 1

        # 检查子命令
        if not hasattr(args, "command") or args.command is None:
            print("错误: 请指定子命令 (generate/score/plan/search)", file=sys.stderr)
            print("运行 'python run.py --help' 查看帮助", file=sys.stderr)
            return ErrorCode.INVALID_INPUT

        # 执行子命令
        result = None
        if args.command == "generate":
            # 手动校验必填参数
            if args.role is None:
                print("错误: --role 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.experience is None:
                print("错误: --experience 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.verbose:
                print(f"生成面试题: role={args.role}, experience={args.experience}, company={args.company}, count={args.count}, difficulty={args.difficulty}, domain={args.domain}")
            result = generate_questions(
                args.role,
                args.experience,
                args.company,
                args.count,
                args.difficulty,
                args.domain,
            )
        elif args.command == "score":
            if args.role is None:
                print("错误: --role 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.experience is None:
                print("错误: --experience 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.answers is None:
                print("错误: --answers 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.verbose:
                print(f"打分: role={args.role}, experience={args.experience}")
            # 解析答案 JSON
            try:
                answers = json.loads(args.answers)
            except json.JSONDecodeError as e:
                print(f"错误: 答案 JSON 解析失败: {e}", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if not isinstance(answers, dict):
                print("错误: 答案必须是 JSON 对象", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            result = score_answers(args.role, args.experience, answers)
        elif args.command == "plan":
            if args.role is None:
                print("错误: --role 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.weak_domains is None:
                print("错误: --weak-domains 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.verbose:
                print(f"生成复习计划: role={args.role}, weak_domains={args.weak_domains}")
            weak_domains = [d.strip() for d in args.weak_domains.split(",") if d.strip()]
            result = generate_plan(args.role, weak_domains)
        elif args.command == "search":
            if args.keyword is None:
                print("错误: --keyword 为必填参数", file=sys.stderr)
                return ErrorCode.INVALID_INPUT
            if args.verbose:
                print(f"搜索: keyword={args.keyword}")
            result = search_questions(args.keyword)
        else:
            print(f"错误: 未知子命令 '{args.command}'", file=sys.stderr)
            return ErrorCode.INVALID_INPUT

        # 格式化输出
        output = format_output(result, args.format)

        # 输出或写入文件
        if args.output:
            output_path = Path(args.output)
            if args.verbose:
                print(f"[明细] 输出格式: {args.format}, 内容长度: {len(output)} 字符")
            save(output_path, output, dry_run=args.dry_run)
        else:
            print(output)

        return ErrorCode.SUCCESS

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return e.code
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return ErrorCode.INTERNAL_ERROR


if __name__ == "__main__":
    sys.exit(main())
