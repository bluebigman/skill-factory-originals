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
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

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
        {"name": "目标检测项目", "detail": "用YOLO实现目标检测", "hours": 4}
    ]
}

# 实战练习模板
PRACTICE_TEMPLATES = {
    "通用入门": [
        "完成一个简单的数据分析项目（如销售数据可视化）",
        "在Kaggle上完成Titanic生存预测并提交结果",
        "用Python实现一个简单的线性回归模型"
    ],
    "机器学习专项": [
        "用sklearn实现KNN分类器并在iris数据集上测试",
        "完成一个完整的机器学习项目（数据清洗→建模→评估）",
        "参加一个Kaggle竞赛并提交结果"
    ],
    "深度学习专项": [
        "用PyTorch实现一个简单的神经网络",
        "在CIFAR-10上训练CNN并达到80%以上准确率",
        "实现一个GAN生成手写数字"
    ],
    "NLP方向": [
        "用HuggingFace实现文本分类",
        "微调一个预训练模型完成情感分析",
        "实现一个简单的聊天机器人"
    ],
    "计算机视觉方向": [
        "用OpenCV实现图像边缘检测",
        "训练一个CNN进行图像分类",
        "实现一个目标检测系统"
    ]
}

# 验收标准模板
ACCEPTANCE_TEMPLATES = {
    "通用入门": [
        "能独立完成数据分析项目并输出报告",
        "Kaggle提交得分达到前50%",
        "模型在测试集上准确率≥80%"
    ],
    "机器学习专项": [
        "能解释KNN、朴素贝叶斯等算法原理",
        "能独立完成数据预处理和特征工程",
        "模型在测试集上准确率≥85%"
    ],
    "深度学习专项": [
        "能解释反向传播原理",
        "能独立训练CNN模型",
        "模型在测试集上准确率≥80%"
    ],
    "NLP方向": [
        "能解释Transformer架构",
        "能微调预训练模型",
        "模型在测试集上F1分数≥0.8"
    ],
    "计算机视觉方向": [
        "能解释CNN各层作用",
        "能独立实现图像分类",
        "模型在测试集上mAP≥0.7"
    ]
}


def determine_level(description: str) -> Tuple[str, float]:
    """
    通过关键词匹配确定基础水平
    
    Args:
        description: 用户描述的基础水平
        
    Returns:
        (水平等级, 置信度分数)
    """
    if not description:
        return "L0", 0.0
    
    description_lower = description.lower()
    scores = {}
    
    for level, keywords in LEVEL_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in description_lower:
                score += 1
        scores[level] = score
    
    # 找到最高分
    max_score = max(scores.values())
    if max_score == 0:
        return "L0", 0.0
    
    # 如果有多个相同最高分，取最高等级
    best_levels = [level for level, score in scores.items() if score == max_score]
    best_level = max(best_levels)
    
    # 计算置信度（0-1）
    confidence = min(1.0, max_score / 2)
    
    return best_level, confidence


def determine_goal(description: str) -> Tuple[str, float]:
    """
    通过关键词匹配确定学习目标
    
    Args:
        description: 用户描述的学习目标
        
    Returns:
        (目标类别, 置信度分数)
    """
    if not description:
        return "通用入门", 0.0
    
    description_lower = description.lower()
    scores = {}
    
    for goal, keywords in GOAL_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in description_lower:
                score += 1
        scores[goal] = score
    
    # 找到最高分
    max_score = max(scores.values())
    if max_score == 0:
        return "通用入门", 0.0
    
    # 如果有多个相同最高分，取第一个
    best_goals = [goal for goal, score in scores.items() if score == max_score]
    best_goal = best_goals[0]
    
    # 计算置信度（0-1）
    confidence = min(1.0, max_score / 2)
    
    return best_goal, confidence


def generate_roadmap(level: str, goal: str, weeks: int) -> Dict:
    """
    生成分周学习路线
    
    Args:
        level: 基础水平（L0-L3）
        goal: 学习目标
        weeks: 学习周数（4-16）
        
    Returns:
        学习路线字典
    """
    # 获取资源
    resources = RESOURCES.get(goal, RESOURCES["通用入门"])
    practices = PRACTICE_TEMPLATES.get(goal, PRACTICE_TEMPLATES["通用入门"])
    acceptances = ACCEPTANCE_TEMPLATES.get(goal, ACCEPTANCE_TEMPLATES["通用入门"])
    
    # 生成分周计划
    weekly_plans = []
    for week in range(1, weeks + 1):
        # 循环使用资源
        resource_idx = (week - 1) % len(resources)
        practice_idx = (week - 1) % len(practices)
        acceptance_idx = (week - 1) % len(acceptances)
        
        # 根据周数调整难度
        difficulty = "基础" if week <= weeks // 3 else ("进阶" if week <= weeks * 2 // 3 else "高级")
        
        plan = {
            "week": week,
            "topic": f"{difficulty}阶段：{resources[resource_idx]['name']}",
            "resources": [resources[resource_idx]],
            "practice": practices[practice_idx],
            "acceptance": acceptances[acceptance_idx]
        }
        weekly_plans.append(plan)
    
    # 生成路线
    roadmap = {
        "level": level,
        "goal": goal,
        "weeks": weeks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "weekly_plans": weekly_plans,
        "total_hours": sum(r["hours"] for r in resources) * (weeks // len(resources) + 1)
    }
    
    return roadmap


def score_roadmap(roadmap: Dict, level_confidence: float, goal_confidence: float) -> int:
    """
    对生成的路线进行质量评分（0-100）
    
    Args:
        roadmap: 学习路线字典
        level_confidence: 水平判定置信度
        goal_confidence: 目标判定置信度
        
    Returns:
        评分（0-100）
    """
    score = 0
    
    # 水平判定成功
    if level_confidence > 0:
        score += 20
    
    # 目标判定成功
    if goal_confidence > 0:
        score += 20
    
    # 周数在 4-16 范围内
    if 4 <= roadmap["weeks"] <= 16:
        score += 20
    
    # 资源库匹配成功
    if roadmap["goal"] in RESOURCES:
        score += 20
    
    # 每周计划完整
    if all(all(k in plan for k in ["week", "topic", "resources", "practice", "acceptance"]) 
           for plan in roadmap["weekly_plans"]):
        score += 20
    
    return min(100, score)


def format_roadmap_markdown(roadmap: Dict, score: int) -> str:
    """
    将学习路线格式化为 Markdown
    
    Args:
        roadmap: 学习路线字典
        score: 质量评分
        
    Returns:
        Markdown 格式的路线
    """
    lines = []
    lines.append(f"# AI 学习路线（{roadmap['level']} → {roadmap['goal']}，{roadmap['weeks']}周）")
    lines.append("")
    lines.append("## 基本信息")
    lines.append(f"- 基础水平：{roadmap['level']}")
    lines.append(f"- 学习目标：{roadmap['goal']}")
    lines.append(f"- 学习周期：{roadmap['weeks']}周")
    lines.append(f"- 生成时间：{roadmap['generated_at']}")
    lines.append("")
    lines.append("## 分周计划")
    
    for plan in roadmap["weekly_plans"]:
        lines.append(f"### 第 {plan['week']} 周：{plan['topic']}")
        lines.append(f"- **学习资源**：{plan['resources'][0]['name']} - {plan['resources'][0]['detail']}")
        lines.append(f"- **实战练习**：{plan['practice']}")
        lines.append(f"- **验收标准**：{plan['acceptance']}")
        lines.append("")
    
    lines.append("## 总体评估")
    lines.append(f"- 路线评分：{score}/100")
    
    if score >= 80:
        lines.append("- 建议：路线质量优秀，按计划执行即可。")
    elif score >= 60:
        lines.append("- 建议：路线质量良好，建议根据实际情况微调。")
    else:
        lines.append("- 建议：路线质量一般，建议重新描述需求。")
    
    return "\n".join(lines)


def atomic_write_file(filepath: str, content: str) -> None:
    """
    原子化写入文件
    
    Args:
        filepath: 文件路径
        content: 文件内容
    """
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=directory or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 原子替换
        os.replace(temp_path, filepath)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def run_selftest() -> int:
    """
    运行自检，验证核心功能
    
    Returns:
        退出码（0 表示成功）
    """
    print("开始自检...")
    
    # 1. 测试水平判定
    test_cases = [
        ("零基础", "L0"),
        ("会python", "L1"),
        ("学过机器学习", "L2"),
        ("做过项目", "L3"),
    ]
    
    for desc, expected in test_cases:
        level, confidence = determine_level(desc)
        assert level == expected, f"水平判定失败: {desc} -> {level}, 期望 {expected}"
        assert confidence > 0, f"置信度应为正数: {desc}"
        print(f"  ✓ 水平判定: {desc} -> {level} (置信度: {confidence:.2f})")
    
    # 2. 测试目标判定
    goal_cases = [
        ("入门", "通用入门"),
        ("机器学习", "机器学习专项"),
        ("深度学习", "深度学习专项"),
        ("nlp", "NLP方向"),
        ("cv", "计算机视觉方向"),
    ]
    
    for desc, expected in goal_cases:
        goal, confidence = determine_goal(desc)
        assert goal == expected, f"目标判定失败: {desc} -> {goal}, 期望 {expected}"
        assert confidence > 0, f"置信度应为正数: {desc}"
        print(f"  ✓ 目标判定: {desc} -> {goal} (置信度: {confidence:.2f})")
    
    # 3. 测试路线生成
    for weeks in [4, 8, 16]:
        roadmap = generate_roadmap("L1", "机器学习专项", weeks)
        assert len(roadmap["weekly_plans"]) == weeks, f"周数错误: {len(roadmap['weekly_plans'])} != {weeks}"
        assert roadmap["goal"] == "机器学习专项", f"目标错误: {roadmap['goal']}"
        print(f"  ✓ 路线生成: {weeks}周路线生成成功")
    
    # 4. 测试评分
    roadmap = generate_roadmap("L1", "机器学习专项", 8)
    score = score_roadmap(roadmap, 0.8, 0.8)
    assert 0 <= score <= 100, f"评分超出范围: {score}"
    print(f"  ✓ 质量评分: {score}/100")
    
    # 5. 测试输出格式
    roadmap = generate_roadmap("L1", "机器学习专项", 8)
    score = score_roadmap(roadmap, 0.8, 0.8)
    markdown = format_roadmap_markdown(roadmap, score)
    assert "# AI 学习路线" in markdown, "Markdown 缺少标题"
    assert "## 分周计划" in markdown, "Markdown 缺少分周计划"
    assert "## 总体评估" in markdown, "Markdown 缺少总体评估"
    print("  ✓ 输出格式验证通过")
    
    # 6. 测试原子写入
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as f:
        test_file = f.name
    
    try:
        atomic_write_file(test_file, "# 测试内容")
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "# 测试内容", "文件写入失败"
        print(f"  ✓ 原子写入验证通过: {test_file}")
    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)
    
    print("所有自检通过！")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="AI学习路径 分周规划 资源验收工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--level",
        type=str,
        help="基础水平描述，如 '零基础'、'会python'"
    )
    parser.add_argument(
        "--goal",
        type=str,
        help="学习目标，如 '机器学习'、'NLP'"
    )
    parser.add_argument(
        "--weeks",
        type=int,
        help="学习周数，4-16"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径，默认输出到 stdout"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检并退出"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1
    
    # 参数校验
    if not args.level or not args.goal or not args.weeks:
        print("错误: 缺少必要参数 --level, --goal, --weeks", file=sys.stderr)
        print("用法: python run.py --level '零基础' --goal '机器学习' --weeks 8", file=sys.stderr)
        return 1
    
    if not 4 <= args.weeks <= 16:
        print("错误: --weeks 必须在 4-16 之间", file=sys.stderr)
        return 1
    
    # 判定水平
    level, level_confidence = determine_level(args.level)
    if level_confidence == 0:
        print("警告: 无法准确判定基础水平，使用默认值 L0", file=sys.stderr)
    
    # 判定目标
    goal, goal_confidence = determine_goal(args.goal)
    if goal_confidence == 0:
        print("警告: 无法准确判定学习目标，使用默认值 通用入门", file=sys.stderr)
    
    # 生成路线
    roadmap = generate_roadmap(level, goal, args.weeks)
    
    # 质量评分
    score = score_roadmap(roadmap, level_confidence, goal_confidence)
    
    # 置信度门控
    if score < 60:
        print(f"错误: 路线质量评分过低 ({score}/100)，无法生成路线", file=sys.stderr)
        print("建议: 请重新描述基础水平和学习目标", file=sys.stderr)
        return 1
    
    # 格式化输出
    markdown = format_roadmap_markdown(roadmap, score)
    
    # 输出
    if args.output:
        try:
            atomic_write_file(args.output, markdown)
            print(f"路线已写入: {args.output}")
        except Exception as e:
            print(f"写入文件失败: {e}", file=sys.stderr)
            return 1
    else:
        print(markdown)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
