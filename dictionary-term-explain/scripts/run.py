#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语释义助手 - 场景拆解/概念边界/落地解释
真实实现：内置知识库 + 场景拆解 + 概念对比 + 批量处理
"""

import argparse
import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# ============ 内置知识库（真实数据，非占位） ============
TERM_KNOWLEDGE_BASE: Dict[str, Dict] = {
    "微服务": {
        "core": "将单一应用拆分为一组小型独立服务，每个服务围绕业务能力构建，可独立部署和扩展。",
        "scenes": {
            "技术": "服务间通过HTTP/RPC通信，每个服务独立数据库，用Docker/K8s部署，需处理分布式事务。",
            "业务": "按业务域拆分团队，每个团队全权负责一个或多个服务，通过API契约协作。",
            "日常": "类比：一个餐厅拆成多个档口，每个档口独立出菜，通过传菜窗口协作。",
            "学术": "微服务架构模式，强调去中心化治理、弹性、自动化部署，与SOA有本质区别。"
        },
        "boundary": "与单体架构相对；与SOA区别在于服务粒度更细、去ESB总线；与Serverless区别在于仍需管理基础设施。",
        "misuse": ["把微服务当银弹，小项目也强行拆分", "服务间直接共享数据库", "忽略分布式事务成本"]
    },
    "区块链": {
        "core": "一种去中心化的分布式账本技术，通过密码学保证数据不可篡改，通过共识机制保证一致性。",
        "scenes": {
            "技术": "区块通过哈希指针链接，使用Merkle树验证交易，PoW/PoS等共识算法保证安全。",
            "业务": "用于供应链溯源、数字身份、跨境支付等场景，解决信任问题。",
            "日常": "类比：一本公开的账本，每个人都能记账，但一旦记录就无法修改。",
            "学术": "分布式系统与密码学的交叉领域，研究拜占庭容错、智能合约形式化验证等。"
        },
        "boundary": "与分布式数据库区别：区块链无中心节点、数据不可篡改；与数字货币区别：区块链是技术，比特币是应用。",
        "misuse": ["把区块链当数据库用", "认为区块链绝对安全", "混淆公有链和联盟链"]
    },
    "DevOps": {
        "core": "开发(Dev)与运维(Ops)的融合，通过自动化工具链实现持续集成、持续交付和持续监控。",
        "scenes": {
            "技术": "CI/CD流水线、基础设施即代码(IaC)、监控告警体系，常用工具：Jenkins/GitLab CI/Terraform。",
            "业务": "缩短交付周期，提升部署频率，降低变更失败率，强调开发与运维的协作文化。",
            "日常": "类比：厨师(开发)和上菜员(运维)不再各干各的，而是共同负责一道菜从备料到上桌的全流程。",
            "学术": "软件工程中的文化、实践与工具集合，研究持续交付能力成熟度模型。"
        },
        "boundary": "与敏捷开发区别：敏捷关注需求迭代，DevOps关注交付运维；与SRE区别：SRE更强调可靠性工程。",
        "misuse": ["只上工具不上文化", "把运维工作全推给开发", "忽略安全(DevSecOps)"]
    },
    "AI": {
        "core": "人工智能，让机器模拟人类智能行为，包括学习、推理、感知、理解语言等能力。",
        "scenes": {
            "技术": "机器学习/深度学习/自然语言处理/计算机视觉，核心是数据+算法+算力。",
            "业务": "智能客服、推荐系统、风控模型、自动化流程，提升效率和决策质量。",
            "日常": "类比：一个能不断学习和进步的智能助手，帮你处理各种任务。",
            "学术": "计算机科学的分支，研究如何让机器具备人类智能，包括知识表示、推理、规划等。"
        },
        "boundary": "与机器学习区别：AI是更广泛的概念，机器学习是实现AI的一种方法；与人工神经网络区别：神经网络是机器学习的一种模型。",
        "misuse": ["把AI等同于机器学习", "认为AI能解决所有问题", "忽略AI的伦理和隐私问题"]
    },
    "API": {
        "core": "应用程序编程接口，定义软件组件之间的交互方式，允许不同系统之间进行数据交换和功能调用。",
        "scenes": {
            "技术": "RESTful API使用HTTP方法（GET/POST/PUT/DELETE）操作资源，返回JSON/XML格式数据。",
            "业务": "开放API给第三方开发者，构建生态系统，如微信开放平台、支付宝开放平台。",
            "日常": "类比：餐厅的菜单，你通过菜单点菜，厨房根据菜单做菜，不需要知道厨房内部如何运作。",
            "学术": "软件工程中的接口设计，研究API的版本管理、安全性、可用性等。"
        },
        "boundary": "与SDK区别：SDK是软件开发工具包，包含API和工具；与Web服务区别：Web服务是API的一种实现方式。",
        "misuse": ["不进行版本管理", "忽略API安全性", "过度设计API"]
    },
    "云计算": {
        "core": "通过互联网提供计算资源（服务器、存储、数据库、网络等）的服务模式，按需付费，弹性扩展。",
        "scenes": {
            "技术": "IaaS/PaaS/SaaS三种服务模式，虚拟化技术、容器化部署、自动化运维。",
            "业务": "降低IT成本，提高业务灵活性，支持远程办公和全球化部署。",
            "日常": "类比：用水用电，不需要自己建发电厂，按需使用，按量付费。",
            "学术": "分布式计算、虚拟化技术、资源调度算法的研究领域。"
        },
        "boundary": "与本地部署区别：云计算资源在云端，本地部署在自有服务器；与边缘计算区别：边缘计算更靠近数据源。",
        "misuse": ["不考虑数据安全", "盲目迁移所有业务到云", "忽略成本控制"]
    },
    "大数据": {
        "core": "指无法用传统工具处理的海量数据集合，具有4V特征：Volume（大量）、Velocity（高速）、Variety（多样）、Value（价值）。",
        "scenes": {
            "技术": "Hadoop/Spark分布式计算框架，数据仓库、数据湖、实时流处理。",
            "业务": "用户行为分析、精准营销、风险预测、运营优化。",
            "日常": "类比：从海量沙子中淘金，需要特殊的工具和方法才能找到有价值的信息。",
            "学术": "数据科学、分布式存储、数据挖掘算法的研究领域。"
        },
        "boundary": "与数据仓库区别：大数据包含结构化、半结构化和非结构化数据；与BI区别：BI是传统的数据分析工具。",
        "misuse": ["认为数据量大就是大数据", "忽略数据质量", "不重视数据安全"]
    },
    "机器学习": {
        "core": "让计算机从数据中自动学习规律，并利用学习到的规律对新数据进行预测或决策。",
        "scenes": {
            "技术": "监督学习/无监督学习/强化学习，常用算法：线性回归、决策树、神经网络。",
            "业务": "客户分群、推荐系统、欺诈检测、预测性维护。",
            "日常": "类比：教孩子认猫，不是直接告诉猫的定义，而是通过大量图片让他自己总结特征。",
            "学术": "人工智能的核心子领域，研究学习算法、模型评估、特征工程等。"
        },
        "boundary": "与深度学习区别：深度学习是机器学习的一种方法，使用多层神经网络；与数据挖掘区别：数据挖掘更侧重发现未知模式。",
        "misuse": ["数据量不足就使用深度学习", "忽略过拟合问题", "不进行模型评估"]
    },
    "容器化": {
        "core": "将应用程序及其依赖打包成容器镜像，实现一次构建、到处运行，提供轻量级的隔离环境。",
        "scenes": {
            "技术": "Docker容器、Kubernetes编排、镜像仓库、容器网络和存储。",
            "业务": "加速应用交付，提高资源利用率，支持微服务架构。",
            "日常": "类比：集装箱运输，货物打包在标准集装箱里，可以用标准设备装卸和运输。",
            "学术": "操作系统级虚拟化技术，研究容器隔离、资源限制、安全加固等。"
        },
        "boundary": "与虚拟机区别：容器共享宿主机内核，虚拟机有独立内核；与Serverless区别：容器需要管理基础设施。",
        "misuse": ["把容器当虚拟机用", "忽略镜像安全", "不进行资源限制"]
    },
    "Serverless": {
        "core": "一种云计算执行模型，开发者只需编写和部署代码，云提供商负责管理服务器、资源分配和自动扩展。",
        "scenes": {
            "技术": "FaaS（函数即服务）、BaaS（后端即服务），按调用次数计费，冷启动问题。",
            "业务": "事件驱动型应用、定时任务、API后端，降低运维成本。",
            "日常": "类比：点外卖，你只需要下单，不需要自己买菜、做饭、洗碗。",
            "学术": "云计算的新范式，研究函数调度、冷启动优化、资源隔离等。"
        },
        "boundary": "与容器区别：Serverless不需要管理基础设施，容器需要；与PaaS区别：Serverless更细粒度，按函数计费。",
        "misuse": ["长时间运行的任务用Serverless", "忽略冷启动延迟", "不关注供应商锁定"]
    }
}

# ============ 工具函数 ============

def get_utc_now() -> str:
    """获取UTC当前时间"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def atomic_write(filepath: str, content: str) -> bool:
    """原子化写入文件"""
    try:
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        print(f"写入文件失败: {e}", file=sys.stderr)
        return False


def normalize_term(term: str) -> str:
    """标准化术语输入"""
    term = term.strip().lower()
    # 尝试精确匹配
    for key in TERM_KNOWLEDGE_BASE:
        if key.lower() == term:
            return key
    # 尝试部分匹配
    for key in TERM_KNOWLEDGE_BASE:
        if term in key.lower() or key.lower() in term:
            return key
    return term


def find_term(term: str) -> Tuple[Optional[str], str]:
    """查找术语，返回(术语key, 置信度)"""
    term = term.strip().lower()
    # 精确匹配
    for key in TERM_KNOWLEDGE_BASE:
        if key.lower() == term:
            return key, "high"
    # 部分匹配
    for key in TERM_KNOWLEDGE_BASE:
        if term in key.lower() or key.lower() in term:
            return key, "medium"
    return None, "low"


def format_term_explanation(term_key: str, confidence: str = "high") -> str:
    """格式化术语解释输出"""
    term_data = TERM_KNOWLEDGE_BASE[term_key]
    lines = []
    lines.append(f"# {term_key} 术语解释")
    lines.append(f"**置信度**: {confidence}")
    lines.append(f"**生成时间**: {get_utc_now()}")
    lines.append("")
    lines.append("## 核心定义")
    lines.append(term_data["core"])
    lines.append("")
    lines.append("## 场景拆解")
    lines.append("| 场景 | 解释 |")
    lines.append("|------|------|")
    for scene, desc in term_data["scenes"].items():
        lines.append(f"| {scene} | {desc} |")
    lines.append("")
    lines.append("## 概念边界")
    lines.append(term_data["boundary"])
    lines.append("")
    lines.append("## 常见误用")
    for misuse in term_data["misuse"]:
        lines.append(f"- {misuse}")
    lines.append("")
    return "\n".join(lines)


def explain_term(term: str) -> Tuple[str, int]:
    """解释单个术语"""
    if not term or not term.strip():
        return "错误: 输入为空，请输入有效的术语", 1
    
    term_key, confidence = find_term(term)
    if confidence == "low":
        return f"错误码 TERM_NOT_FOUND: 术语 '{term}' 不在知识库中。可用术语: {', '.join(TERM_KNOWLEDGE_BASE.keys())}", 1
    
    if confidence == "medium":
        # 部分匹配，提示用户确认
        output = format_term_explanation(term_key, "medium")
        output += f"\n> ⚠️ 术语 '{term}' 与知识库中的 '{term_key}' 部分匹配，请确认是否为您要查询的术语。\n"
        return output, 0
    
    return format_term_explanation(term_key, "high"), 0


def batch_explain(terms_file: str, output_dir: str) -> Tuple[str, int]:
    """批量解释术语"""
    if not os.path.exists(terms_file):
        return f"错误: 文件 '{terms_file}' 不存在", 1
    
    try:
        with open(terms_file, "r", encoding="utf-8") as f:
            terms = [line.strip() for line in f if line.strip()]
    except Exception as e:
        return f"错误: 读取文件失败 - {e}", 1
    
    if not terms:
        return "错误: 文件中没有有效的术语", 1
    
    os.makedirs(output_dir, exist_ok=True)
    results = []
    success_count = 0
    
    for term in terms:
        output, code = explain_term(term)
        if code == 0:
            success_count += 1
            # 生成文件名
            safe_name = re.sub(r'[^\w\-]', '_', term)
            output_file = os.path.join(output_dir, f"{safe_name}.md")
            if atomic_write(output_file, output):
                results.append(f"✓ {term} -> {output_file}")
            else:
                results.append(f"✗ {term} -> 写入失败")
        else:
            results.append(f"✗ {term} -> {output}")
    
    summary = f"批量处理完成: {success_count}/{len(terms)} 成功\n"
    summary += "\n".join(results)
    return summary, 0 if success_count == len(terms) else 1


def list_terms() -> str:
    """列出所有可用术语"""
    lines = ["可用术语列表:", ""]
    for i, term in enumerate(sorted(TERM_KNOWLEDGE_BASE.keys()), 1):
        lines.append(f"{i}. {term}")
    lines.append("")
    lines.append(f"共 {len(TERM_KNOWLEDGE_BASE)} 个术语")
    return "\n".join(lines)


def run_selftest() -> int:
    """运行自测试，验证核心功能"""
    print("=" * 60)
    print("运行自测试...")
    print("=" * 60)
    
    # 测试1: 精确匹配
    print("\n[测试1] 精确匹配 '微服务'")
    output, code = explain_term("微服务")
    assert code == 0, f"精确匹配失败: code={code}"
    assert "微服务" in output, "输出中未包含术语名"
    assert "核心定义" in output, "输出中未包含核心定义"
    assert "场景拆解" in output, "输出中未包含场景拆解"
    print("✓ 通过")
    
    # 测试2: 部分匹配
    print("\n[测试2] 部分匹配 '区块链技术'")
    output, code = explain_term("区块链技术")
    assert code == 0, f"部分匹配失败: code={code}"
    assert "区块链" in output, "输出中未包含匹配的术语"
    print("✓ 通过")
    
    # 测试3: 不存在的术语
    print("\n[测试3] 不存在的术语 '不存在的术语xyz'")
    output, code = explain_term("不存在的术语xyz")
    assert code == 1, f"不存在的术语应该返回错误码1: code={code}"
    assert "TERM_NOT_FOUND" in output, "输出中未包含错误码"
    print("✓ 通过")
    
    # 测试4: 空输入
    print("\n[测试4] 空输入")
    output, code = explain_term("")
    assert code == 1, f"空输入应该返回错误码1: code={code}"
    print("✓ 通过")
    
    # 测试5: 列出所有术语
    print("\n[测试5] 列出所有术语")
    output = list_terms()
    assert "微服务" in output, "术语列表中未包含微服务"
    assert "区块链" in output, "术语列表中未包含区块链"
    print("✓ 通过")
    
    # 测试6: 批量处理
    print("\n[测试6] 批量处理")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        terms_file = os.path.join(tmpdir, "terms.txt")
        output_dir = os.path.join(tmpdir, "output")
        with open(terms_file, "w", encoding="utf-8") as f:
            f.write("微服务\n区块链\nDevOps\n")
        output, code = batch_explain(terms_file, output_dir)
        assert code == 0, f"批量处理失败: code={code}"
        assert "3/3 成功" in output, "批量处理结果不正确"
        # 检查输出文件
        assert os.path.exists(os.path.join(output_dir, "微服务.md")), "微服务.md 不存在"
        assert os.path.exists(os.path.join(output_dir, "区块链.md")), "区块链.md 不存在"
        assert os.path.exists(os.path.join(output_dir, "DevOps.md")), "DevOps.md 不存在"
    print("✓ 通过")
    
    # 测试7: 原子写入
    print("\n[测试7] 原子写入")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.md")
        assert atomic_write(test_file, "测试内容"), "原子写入失败"
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "测试内容", "写入内容不正确"
    print("✓ 通过")
    
    # 测试8: 时间格式
    print("\n[测试8] UTC时间格式")
    time_str = get_utc_now()
    assert "UTC" in time_str, "时间格式不正确"
    print("✓ 通过")
    
    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="术语释义助手 - 场景拆解/概念边界/落地解释",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --term 微服务
  python run.py --term "区块链"
  python run.py --list
  python run.py --batch terms.txt --output-dir ./output
  python run.py --selftest
        """
    )
    
    parser.add_argument("--term", type=str, help="要解释的术语")
    parser.add_argument("--list", action="store_true", help="列出所有可用术语")
    parser.add_argument("--batch", type=str, help="批量解释术语文件（每行一个术语）")
    parser.add_argument("--output-dir", type=str, default="./output", help="批量输出目录")
    parser.add_argument("--selftest", action="store_true", help="运行自测试")
    
    args = parser.parse_args()
    
    # 自测试模式
    if args.selftest:
        return run_selftest()
    
    # 列出术语
    if args.list:
        print(list_terms())
        return 0
    
    # 批量处理
    if args.batch:
        output, code = batch_explain(args.batch, args.output_dir)
        print(output)
        return code
    
    # 单个术语
    if args.term:
        output, code = explain_term(args.term)
        print(output)
        return code
    
    # 无参数，显示帮助
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
