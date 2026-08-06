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
            "日常": "类比：教小孩认猫——给他看很多猫的图片，他就能自己认出猫。",
            "学术": "计算机科学分支，研究智能agent的构建，涉及搜索、知识表示、学习理论等。"
        },
        "boundary": "与机器学习区别：AI是更广的概念，ML是实现AI的一种方法；与AGI区别：当前AI多为弱AI，AGI是通用智能。",
        "misuse": ["把规则系统当AI", "认为AI能完全替代人类", "忽略数据偏见问题"]
    },
    "云计算": {
        "core": "通过网络按需提供可配置计算资源（网络、服务器、存储、应用）的模式，资源可快速供给和释放。",
        "scenes": {
            "技术": "虚拟化技术、容器编排、弹性伸缩、负载均衡，IaaS/PaaS/SaaS三层服务模型。",
            "业务": "按需付费降低IT成本，弹性应对业务高峰，全球部署加速访问。",
            "日常": "类比：用水不需要自己建水厂，打开水龙头就有水——用云服务不需要自己买服务器。",
            "学术": "分布式计算、虚拟化、效用计算的商业实现，研究资源调度和SLA保障。"
        },
        "boundary": "与本地数据中心区别：云服务按需付费、弹性扩展；与边缘计算区别：边缘计算靠近数据源，降低延迟。",
        "misuse": ["把云当简单虚拟机用", "忽略安全合规要求", "不评估成本就迁移上云"]
    }
}

# 内置同义词/缩写映射
TERM_ALIASES = {
    "微服务架构": "微服务",
    "microservice": "微服务",
    "microservices": "微服务",
    "区块链技术": "区块链",
    "blockchain": "区块链",
    "开发运维一体化": "DevOps",
    "开发运维": "DevOps",
    "人工智能": "AI",
    "artificial intelligence": "AI",
    "云服务": "云计算",
    "cloud computing": "云计算",
}

# ============ 核心业务逻辑 ============

def normalize_term(term: str) -> str:
    """术语规范化：去除空格、统一大小写、检查别名"""
    term = term.strip().lower()
    if term in TERM_ALIASES:
        return TERM_ALIASES[term]
    # 尝试模糊匹配（包含关系）
    for key in TERM_KNOWLEDGE_BASE:
        if key.lower() in term or term in key.lower():
            return key
    return term

def explain_term(term: str, scene: str = "通用") -> Dict:
    """
    核心解释函数：返回结构化解释
    scene: 技术/业务/日常/学术/通用
    """
    normalized = normalize_term(term)
    if normalized not in TERM_KNOWLEDGE_BASE:
        return {
            "found": False,
            "term": term,
            "message": f"知识库中未找到术语「{term}」的解释。可用 --list 查看支持的术语。"
        }
    
    data = TERM_KNOWLEDGE_BASE[normalized]
    # 场景选择
    if scene in data["scenes"]:
        scene_explain = data["scenes"][scene]
    else:
        scene_explain = data["scenes"]["技术"] + "（未指定场景，默认技术视角）"
    
    return {
        "found": True,
        "term": normalized,
        "core": data["core"],
        "scene": scene,
        "scene_explain": scene_explain,
        "boundary": data["boundary"],
        "misuse": data["misuse"]
    }

def format_output(result: Dict, format_type: str = "text") -> str:
    """格式化输出：text/markdown/json"""
    if not result["found"]:
        return result["message"]
    
    if format_type == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    if format_type == "markdown":
        lines = [
            f"## 术语：{result['term']}",
            "",
            f"**核心定义**：{result['core']}",
            "",
            f"**场景拆解（{result['scene']}）**：",
            result["scene_explain"],
            "",
            "**概念边界**：",
            result["boundary"],
            "",
            "**常见误用**：",
        ]
        for i, misuse in enumerate(result["misuse"], 1):
            lines.append(f"{i}. {misuse}")
        return "\n".join(lines)
    
    # 默认text格式
    lines = [
        f"【术语】{result['term']}",
        f"【核心定义】{result['core']}",
        f"【场景拆解（{result['scene']}）】",
        result["scene_explain"],
        f"【概念边界】{result['boundary']}",
        "【常见误用】",
    ]
    for i, misuse in enumerate(result["misuse"], 1):
        lines.append(f"  {i}. {misuse}")
    return "\n".join(lines)

def batch_explain(input_file: str, output_file: str, scene: str, format_type: str) -> Tuple[int, str]:
    """
    批量处理：每行一个术语
    返回 (成功数, 错误信息)
    """
    if not os.path.exists(input_file):
        return 0, f"输入文件不存在: {input_file}"
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            terms = [line.strip() for line in f if line.strip()]
    except Exception as e:
        return 0, f"读取文件失败: {e}"
    
    if not terms:
        return 0, "输入文件为空"
    
    results = []
    success_count = 0
    for term in terms:
        result = explain_term(term, scene)
        if result["found"]:
            success_count += 1
        results.append(format_output(result, format_type))
    
    # 写入输出
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            if format_type == "json":
                # JSON格式输出数组
                json_results = [explain_term(t, scene) for t in terms]
                f.write(json.dumps(json_results, ensure_ascii=False, indent=2))
            else:
                f.write("\n\n---\n\n".join(results))
    except Exception as e:
        return success_count, f"写入输出文件失败: {e}"
    
    return success_count, f"成功处理 {success_count}/{len(terms)} 个术语，结果已写入 {output_file}"

def list_terms() -> str:
    """列出知识库所有术语"""
    lines = ["【支持的术语列表】", ""]
    for term, data in TERM_KNOWLEDGE_BASE.items():
        lines.append(f"• {term}: {data['core'][:30]}...")
    lines.append("")
    lines.append("【别名/同义词】")
    for alias, target in TERM_ALIASES.items():
        lines.append(f"• {alias} → {target}")
    return "\n".join(lines)

# ============ 自检函数 ============

def selftest() -> bool:
    """自检：验证核心功能正常"""
    print("=== 自检开始 ===")
    
    # 测试1: 正常术语解释
    result = explain_term("微服务", "技术")
    assert result["found"], "微服务解释失败"
    assert "独立服务" in result["core"], "核心定义不完整"
    print("✓ 术语解释功能正常")
    
    # 测试2: 别名解析
    result = explain_term("microservice")
    assert result["found"] and result["term"] == "微服务", "别名解析失败"
    print("✓ 别名解析功能正常")
    
    # 测试3: 未知术语处理
    result = explain_term("不存在的术语xyz")
    assert not result["found"], "未知术语应返回未找到"
    print("✓ 未知术语处理正常")
    
    # 测试4: 场景切换
    result1 = explain_term("区块链", "业务")
    result2 = explain_term("区块链", "技术")
    assert result1["scene_explain"] != result2["scene_explain"], "场景切换失败"
    print("✓ 场景切换功能正常")
    
    # 测试5: 格式化输出
    md = format_output(explain_term("DevOps"), "markdown")
    assert "## 术语" in md, "Markdown格式化失败"
    js = format_output(explain_term("AI"), "json")
    assert json.loads(js)["found"], "JSON格式化失败"
    print("✓ 格式化输出功能正常")
    
    # 测试6: 批量处理（临时文件）
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("微服务\n区块链\nDevOps\n")
        temp_input = f.name
    temp_output = temp_input.replace(".txt", "_out.txt")
    try:
        count, msg = batch_explain(temp_input, temp_output, "通用", "text")
        assert count == 3, f"批量处理失败: {msg}"
        assert os.path.exists(temp_output), "输出文件未生成"
        print("✓ 批量处理功能正常")
    finally:
        os.unlink(temp_input)
        if os.path.exists(temp_output):
            os.unlink(temp_output)
    
    print("=== 自检全部通过 ===")
    return True

# ============ 主入口 ============

def main():
    parser = argparse.ArgumentParser(
        description="术语释义助手 - 场景拆解/概念边界/落地解释",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python run.py --term 微服务\n"
               "  python run.py --term 区块链 --scene 业务 --format markdown\n"
               "  python run.py --input terms.txt --output result.txt --scene 技术\n"
               "  python run.py --list\n"
               "  python run.py --selftest"
    )
    
    # 互斥模式：单术语解释 / 批量处理 / 列表 / 自检
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--term", "-t", help="要解释的术语")
    group.add_argument("--input", "-i", help="批量处理：输入文件（每行一个术语）")
    group.add_argument("--list", "-l", action="store_true", help="列出所有支持的术语")
    group.add_argument("--selftest", action="store_true", help="运行自检")
    
    # 公共参数
    parser.add_argument("--output", "-o", help="批量处理时的输出文件")
    parser.add_argument("--scene", "-s", default="通用", 
                        choices=["技术", "业务", "日常", "学术", "通用"],
                        help="解释场景（默认: 通用）")
    parser.add_argument("--format", "-f", default="text",
                        choices=["text", "markdown", "json"],
                        help="输出格式（默认: text）")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            selftest()
            sys.exit(0)
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 列表模式
    if args.list:
        print(list_terms())
        sys.exit(0)
    
    # 单术语模式
    if args.term:
        result = explain_term(args.term, args.scene)
        print(format_output(result, args.format))
        if not result["found"]:
            sys.exit(1)
        sys.exit(0)
    
    # 批量模式
    if args.input:
        if not args.output:
            print("错误: 批量处理时必须指定 --output 参数", file=sys.stderr)
            sys.exit(1)
        count, msg = batch_explain(args.input, args.output, args.scene, args.format)
        print(msg)
        if count == 0:
            sys.exit(1)
        sys.exit(0)
    
    # 不应到达这里
    parser.print_help()
    sys.exit(1)

if __name__ == "__main__":
    main()
