#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI学习路径 分周规划 资源验收工具
根据用户基础水平、学习目标和时间预算，生成结构化的分周学习路线，
包含学习资源、实战练习和可量化的验收标准。
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# ============ 内置知识库 ============
# 基础水平判定关键词
LEVEL_KEYWORDS = {
    "L0": ["零基础", "没学过", "完全不懂", "小白", "新手", "无经验"],
    "L1": ["会python", "有编程经验", "写过代码", "会编程", "python基础"],
    "L2": ["学过机器学习", "了解神经网络", "ml基础", "深度学习基础"],
    "L3": ["做过项目", "熟悉深度学习", "有项目经验", "资深"]
}

# 学习目标判定关键词
GOAL_KEYWORDS = {
    "通用入门": ["入门", "全面", "基础", "通识"],
    "机器学习专项": ["机器学习", "ml", "machine learning"],
    "深度学习专项": ["深度学习", "神经网络", "deep learning"],
    "NLP方向": ["nlp", "自然语言", "文本", "语言模型"],
    "计算机视觉方向": ["cv", "视觉", "图像", "computer vision"]
}

# 各方向课程资源库 (真实可用的公开资源)
RESOURCES = {
    "通用入门": [
        {"name": "吴恩达《机器学习》", "detail": "Coursera 课程第1-4周", "hours": 4},
        {"name": "Python数据分析", "detail": "B站黑马程序员视频 P1-P30", "hours": 3},
        {"name": "Kaggle入门教程", "detail": "Titanic 生存预测实战", "hours": 2}
    ],
    "机器学习专项": [
        {"name": "《统计学习方法》", "detail": "第1-3章 感知机/KNN/朴素贝叶斯", "hours": 5},
        {"name": "sklearn官方文档", "detail": "分类算法部分", "hours": 3},
        {"name": "Kaggle竞赛", "detail": "House Prices 回归预测", "hours": 4}
    ],
    "深度学习专项": [
        {"name": "《深度学习》花书", "detail": "第6-8章 深度前馈网络", "hours": 5},
        {"name": "PyTorch官方教程", "detail": "60分钟入门 + 图像分类", "hours": 3},
        {"name": "CIFAR-10实战", "detail": "用CNN实现图像分类", "hours": 4}
    ],
    "NLP方向": [
        {"name": "《NLP with Transformers》", "detail": "第1-3章 Transformer原理", "hours": 5},
        {"name": "HuggingFace教程", "detail": "Pipeline + Fine-tuning", "hours": 3},
        {"name": "情感分析项目", "detail": "IMDB影评情感分类", "hours": 4}
    ],
    "计算机视觉方向": [
        {"name": "CS231n课程", "detail": "Lecture 1-5 CNN基础", "hours": 5},
        {"name": "OpenCV官方教程", "detail": "图像处理基础", "hours": 3},
        {"name": "目标检测项目", "detail": "用YOLO实现实时检测", "hours": 4}
    ]
}

# 各水平对应的前置知识
PREREQUISITES = {
    "L0": ["Python基础语法", "Linux命令行", "数学基础(线性代数/概率论)"],
    "L1": ["Python高级特性", "NumPy/Pandas", "数据可视化"],
    "L2": ["机器学习算法", "模型评估方法", "特征工程"],
    "L3": ["深度学习框架", "模型调优", "分布式训练"]
}

# 每周主题模板
WEEKLY_THEMES = {
    "通用入门": ["AI概述与Python基础", "数据处理与可视化", "机器学习入门", "监督学习算法", "模型评估与调优", "深度学习基础", "项目实战", "综合复习"],
    "机器学习专项": ["数学基础复习", "经典ML算法", "特征工程", "模型集成", "实战项目1", "实战项目2", "算法优化", "综合测评"],
    "深度学习专项": ["神经网络基础", "CNN原理", "RNN与序列模型", "PyTorch实战", "生成模型", "迁移学习", "实战项目", "前沿技术"],
    "NLP方向": ["文本预处理", "词向量与Embedding", "RNN/LSTM", "Attention机制", "Transformer", "BERT与预训练", "NLP实战", "综合项目"],
    "计算机视觉方向": ["图像基础", "CNN架构", "目标检测", "图像分割", "生成对抗网络", "模型部署", "视觉实战", "综合项目"]
}


def detect_level(description: str) -> str:
    """根据用户描述识别基础水平"""
    desc_lower = description.lower()
    for level, keywords in LEVEL_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return level
    return "L0"  # 默认零基础


def detect_goal(description: str) -> str:
    """根据用户描述识别学习目标"""
    desc_lower = description.lower()
    for goal, keywords in GOAL_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return goal
    return "通用入门"  # 默认通用入门


def generate_roadmap(level: str, goal: str, weeks: int, hours_per_week: int) -> Dict:
    """生成分周学习路线"""
    if weeks < 4 or weeks > 16:
        raise ValueError(f"总周数必须在4-16之间，当前值: {weeks}")
    if hours_per_week < 2 or hours_per_week > 20:
        raise ValueError(f"每周投入时间必须在2-20小时之间，当前值: {hours_per_week}")

    # 获取该方向的课程资源
    resources = RESOURCES.get(goal, RESOURCES["通用入门"])
    themes = WEEKLY_THEMES.get(goal, WEEKLY_THEMES["通用入门"])
    prereqs = PREREQUISITES.get(level, PREREQUISITES["L0"])

    # 计算每周资源分配
    total_resources = len(resources)
    resources_per_week = max(1, total_resources // weeks)

    roadmap = {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "goal": goal,
            "weeks": weeks,
            "hours_per_week": hours_per_week,
            "total_hours": weeks * hours_per_week
        },
        "prerequisites": prereqs,
        "weeks": []
    }

    for week in range(1, weeks + 1):
        # 选择本周主题
        theme_idx = (week - 1) % len(themes)
        theme = themes[theme_idx]

        # 分配资源
        start_idx = ((week - 1) * resources_per_week) % total_resources
        week_resources = []
        for i in range(resources_per_week):
            idx = (start_idx + i) % total_resources
            res = resources[idx]
            week_resources.append({
                "name": res["name"],
                "detail": res["detail"],
                "estimated_hours": min(res["hours"], hours_per_week)
            })

        # 生成验收标准
        acceptance = [
            f"能独立完成本周主题相关的代码练习",
            f"能解释{theme}的核心概念",
            f"通过本周自测题（正确率≥80%）"
        ]

        # 生成实战练习
        practice = {
            "name": f"{theme}实战练习",
            "description": f"基于{theme}完成一个小型项目或练习",
            "acceptance": acceptance
        }

        roadmap["weeks"].append({
            "week": week,
            "theme": theme,
            "overview": f"本周重点学习{theme}，掌握核心概念和基本应用",
            "resources": week_resources,
            "practice": practice,
            "estimated_hours": min(hours_per_week, sum(r["estimated_hours"] for r in week_resources))
        })

    return roadmap


def format_roadmap(roadmap: Dict) -> str:
    """将路线格式化为可读文本"""
    lines = []
    meta = roadmap["meta"]

    lines.append("=" * 60)
    lines.append("AI 学习路径规划")
    lines.append("=" * 60)
    lines.append(f"生成时间: {meta['generated_at']}")
    lines.append(f"基础水平: {meta['level']}")
    lines.append(f"学习目标: {meta['goal']}")
    lines.append(f"总周数: {meta['weeks']} 周")
    lines.append(f"每周投入: {meta['hours_per_week']} 小时")
    lines.append(f"总投入: {meta['total_hours']} 小时")
    lines.append("")

    # 前置知识
    lines.append("【前置知识要求】")
    for prereq in roadmap["prerequisites"]:
        lines.append(f"  - {prereq}")
    lines.append("")

    # 每周计划
    for week_data in roadmap["weeks"]:
        lines.append(f"### 第 {week_data['week']} 周：{week_data['theme']}")
        lines.append(f"**主题概述**：{week_data['overview']}")
        lines.append("")
        lines.append("**学习资源**：")
        for res in week_data["resources"]:
            lines.append(f"  - {res['name']}：{res['detail']}，预计 {res['estimated_hours']} 小时")
        lines.append("")
        lines.append("**实战练习**：")
        lines.append(f"  - 练习名称：{week_data['practice']['name']}")
        lines.append(f"  - 任务描述：{week_data['practice']['description']}")
        lines.append("  - 验收标准：")
        for acc in week_data["practice"]["acceptance"]:
            lines.append(f"    - [ ] {acc}")
        lines.append(f"**预计耗时**：{week_data['estimated_hours']} 小时")
        lines.append("")

    return "\n".join(lines)


def save_roadmap(roadmap: Dict, output_path: str, format_type: str = "text") -> None:
    """保存路线到文件"""
    if format_type == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(roadmap, f, ensure_ascii=False, indent=2)
    else:
        content = format_roadmap(roadmap)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)


def selftest() -> bool:
    """自检函数：验证核心功能"""
    print("运行自检...")

    # 测试1: 水平识别
    assert detect_level("我完全不懂编程") == "L0"
    assert detect_level("我会Python编程") == "L1"
    assert detect_level("我学过机器学习") == "L2"
    print("✓ 水平识别测试通过")

    # 测试2: 目标识别
    assert detect_goal("我想学机器学习") == "机器学习专项"
    assert detect_goal("我想做NLP") == "NLP方向"
    assert detect_goal("我想入门AI") == "通用入门"
    print("✓ 目标识别测试通过")

    # 测试3: 路线生成
    roadmap = generate_roadmap("L1", "机器学习专项", 8, 5)
    assert len(roadmap["weeks"]) == 8
    assert roadmap["meta"]["total_hours"] == 40
    assert all(w["estimated_hours"] > 0 for w in roadmap["weeks"])
    print("✓ 路线生成测试通过")

    # 测试4: 参数校验
    try:
        generate_roadmap("L1", "机器学习专项", 3, 5)
        assert False, "应该抛出异常"
    except ValueError:
        pass
    print("✓ 参数校验测试通过")

    # 测试5: 格式输出
    content = format_roadmap(roadmap)
    assert "第 1 周" in content
    assert "验收标准" in content
    print("✓ 格式输出测试通过")

    print("所有自检测试通过！")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="AI学习路径规划工具 - 根据基础与目标生成分周学习路线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --description "零基础想学机器学习" --output roadmap.txt
  %(prog)s --description "会Python想搞NLP" --weeks 12 --hours 10 --output roadmap.json --format json
  %(prog)s --selftest
        """
    )

    parser.add_argument(
        "--description", "-d",
        type=str,
        help="用户描述，包含基础水平和学习目标，如：'零基础想学机器学习'"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="ai_roadmap.txt",
        help="输出文件路径 (默认: ai_roadmap.txt)"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--weeks", "-w",
        type=int,
        default=8,
        help="总周数，4-16 (默认: 8)"
    )
    parser.add_argument(
        "--hours", "-H",
        type=int,
        default=5,
        help="每周投入小时数，2-20 (默认: 5)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)

    # 参数验证
    if not args.description:
        parser.error("必须提供 --description 参数描述你的基础和学习目标")

    # 生成路线
    try:
        level = detect_level(args.description)
        goal = detect_goal(args.description)
        roadmap = generate_roadmap(level, goal, args.weeks, args.hours)

        # 保存输出
        save_roadmap(roadmap, args.output, args.format)
        print(f"✅ 学习路线已生成: {args.output}")
        print(f"   基础水平: {level}")
        print(f"   学习目标: {goal}")
        print(f"   总周数: {args.weeks} 周")
        print(f"   每周投入: {args.hours} 小时")

        # 同时打印预览
        if args.format == "text":
            print("\n" + "=" * 60)
            print("预览（前5周）：")
            print("=" * 60)
            lines = format_roadmap(roadmap).split("\n")
            preview_lines = []
            week_count = 0
            for line in lines:
                if line.startswith("### 第"):
                    week_count += 1
                    if week_count > 5:
                        break
                preview_lines.append(line)
            print("\n".join(preview_lines))
            if week_count > 5:
                print(f"\n... (共 {args.weeks} 周，完整内容见文件)")

    except ValueError as e:
        print(f"❌ 参数错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 生成失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
