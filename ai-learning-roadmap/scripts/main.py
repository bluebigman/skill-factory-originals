#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-learning-roadmap - AI学习路径分周规划与资源验收工具
版本: 1.1.0
许可证: MIT
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from collections import OrderedDict

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "参数错误：基础水平取值无效",
    "E003": "参数错误：目标类型取值无效",
    "E004": "参数错误：周数超出允许范围",
    "E005": "数据错误：内置模板数据缺失或损坏",
    "E006": "数据错误：生成结果为空",
    "E007": "运行时错误：JSON序列化失败",
    "E008": "运行时错误：文件写入失败",
    "E009": "运行时错误：文件读取失败",
    "E010": "未知错误",
    "E011": "网络错误：资源验证请求失败",
}

# ============================================================
# 内置基础数据（硬编码模板，不依赖外部文件）
# ============================================================

# 基础水平等级定义
LEVELS = {
    "L0": {"name": "零基础", "desc": "无编程经验，数学基础薄弱"},
    "L1": {"name": "入门", "desc": "有基础编程能力，了解基本数学概念"},
    "L2": {"name": "进阶", "desc": "熟练掌握编程，具备线性代数和概率统计基础"},
    "L3": {"name": "高级", "desc": "有AI项目经验，需要系统化提升"},
}

# 学习目标类型定义
GOAL_TYPES = {
    "career": {"name": "就业", "desc": "以进入AI相关岗位为目标"},
    "research": {"name": "科研", "desc": "以学术研究为目标"},
    "project": {"name": "项目开发", "desc": "以完成具体项目为目标"},
    "teaching": {"name": "团队培训", "desc": "以团队能力建设为目标"},
}

# 技能模块定义（按目标类型组织）
SKILL_MODULES = {
    "career": [
        {"id": "M01", "name": "Python编程基础", "weeks": 2},
        {"id": "M02", "name": "数学基础", "weeks": 3},
        {"id": "M03", "name": "机器学习核心", "weeks": 4},
        {"id": "M04", "name": "深度学习基础", "weeks": 3},
        {"id": "M05", "name": "工程实践", "weeks": 2},
    ],
    "research": [
        {"id": "M01", "name": "数学基础深化", "weeks": 3},
        {"id": "M02", "name": "经典ML算法", "weeks": 3},
        {"id": "M03", "name": "深度学习理论", "weeks": 4},
        {"id": "M04", "name": "论文阅读与复现", "weeks": 3},
        {"id": "M05", "name": "研究方向探索", "weeks": 2},
    ],
    "project": [
        {"id": "M01", "name": "Python与工具链", "weeks": 2},
        {"id": "M02", "name": "ML快速上手", "weeks": 3},
        {"id": "M03", "name": "深度学习实战", "weeks": 3},
        {"id": "M04", "name": "项目开发实践", "weeks": 3},
    ],
    "teaching": [
        {"id": "M01", "name": "团队基础摸底", "weeks": 1},
        {"id": "M02", "name": "核心知识体系", "weeks": 4},
        {"id": "M03", "name": "实战项目训练", "weeks": 3},
        {"id": "M04", "name": "内部知识沉淀", "weeks": 2},
    ],
}

# 学习资源模板（按主题分类）- 完整数据
RESOURCES = {
    "python": [
        {"type": "课程", "name": "Python官方教程", "url": "https://docs.python.org/3/tutorial/"},
        {"type": "书籍", "name": "Python编程：从入门到实践", "url": "https://www.ituring.com.cn/book/1861"},
        {"type": "练习", "name": "LeetCode 简单题", "url": "https://leetcode.com/problemset/all/?difficulty=EASY"},
        {"type": "视频", "name": "Python核心编程", "url": "https://www.bilibili.com/video/BV1ex411x7Em"},
    ],
    "math": [
        {"type": "课程", "name": "3Blue1Brown 线性代数", "url": "https://www.3blue1brown.com/topics/linear-algebra"},
        {"type": "课程", "name": "Khan Academy 概率统计", "url": "https://www.khanacademy.org/math/statistics-probability"},
        {"type": "书籍", "name": "统计学习方法", "url": "https://book.douban.com/subject/10590856/"},
        {"type": "课程", "name": "MIT 线性代数公开课", "url": "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/"},
    ],
    "ml": [
        {"type": "课程", "name": "吴恩达机器学习", "url": "https://www.coursera.org/learn/machine-learning"},
        {"type": "文档", "name": "scikit-learn 用户指南", "url": "https://scikit-learn.org/stable/user_guide.html"},
        {"type": "书籍", "name": "机器学习（周志华）", "url": "https://book.douban.com/subject/26708119/"},
        {"type": "课程", "name": "机器学习基石", "url": "https://www.coursera.org/learn/ntumlone-mathematicalfoundations"},
    ],
    "dl": [
        {"type": "课程", "name": "吴恩达深度学习专项", "url": "https://www.deeplearning.ai/courses/deep-learning-specialization/"},
        {"type": "文档", "name": "PyTorch 官方教程", "url": "https://pytorch.org/tutorials/"},
        {"type": "论文", "name": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762"},
        {"type": "书籍", "name": "深度学习（花书）", "url": "https://book.douban.com/subject/26882718/"},
    ],
    "engineering": [
        {"type": "开源项目", "name": "Hugging Face Transformers", "url": "https://github.com/huggingface/transformers"},
        {"type": "工具", "name": "Docker 官方文档", "url": "https://docs.docker.com/"},
        {"type": "课程", "name": "MLOps 基础课程", "url": "https://madewithml.com/courses/mlops/"},
        {"type": "工具", "name": "Kubernetes 官方文档", "url": "https://kubernetes.io/docs/"},
    ],
    "research_method": [
        {"type": "论文", "name": "BERT", "url": "https://arxiv.org/abs/1810.04805"},
        {"type": "论文", "name": "ResNet", "url": "https://arxiv.org/abs/1512.03385"},
        {"type": "工具", "name": "Google Scholar", "url": "https://scholar.google.com/"},
        {"type": "课程", "name": "如何做科研", "url": "https://www.coursera.org/learn/how-to-write-a-scientific-paper"},
    ],
    "project_practice": [
        {"type": "平台", "name": "Kaggle 竞赛", "url": "https://www.kaggle.com/competitions"},
        {"type": "开源项目", "name": "GitHub Trending", "url": "https://github.com/trending"},
        {"type": "平台", "name": "Papers with Code", "url": "https://paperswithcode.com/"},
        {"type": "工具", "name": "Jupyter Notebook", "url": "https://jupyter.org/"},
    ],
    "team_training": [
        {"type": "工具", "name": "Confluence 知识库", "url": "https://www.atlassian.com/software/confluence"},
        {"type": "方法", "name": "费曼学习法", "url": "https://fs.blog/feynman-technique/"},
        {"type": "平台", "name": "内部代码评审", "url": "https://github.com/features/code-review/"},
        {"type": "课程", "name": "团队协作与沟通", "url": "https://www.coursera.org/learn/teamwork"},
    ],
}

# 模块到资源的映射
MODULE_RESOURCE_MAP = {
    "Python编程基础": "python",
    "Python与工具链": "python",
    "数学基础": "math",
    "数学基础深化": "math",
    "机器学习核心": "ml",
    "经典ML算法": "ml",
    "ML快速上手": "ml",
    "深度学习基础": "dl",
    "深度学习理论": "dl",
    "深度学习实战": "dl",
    "工程实践": "engineering",
    "论文阅读与复现": "research_method",
    "研究方向探索": "research_method",
    "项目开发实践": "project_practice",
    "团队基础摸底": "team_training",
    "核心知识体系": "ml",
    "实战项目训练": "project_practice",
    "内部知识沉淀": "team_training",
}

# 模块验收标准模板
ACCEPTANCE_CRITERIA = {
    "python": [
        "能独立编写Python脚本解决简单问题",
        "掌握基本数据类型、控制流和函数定义",
        "能使用pip安装和管理第三方库",
    ],
    "math": [
        "理解线性代数核心概念（矩阵、向量、特征值）",
        "掌握概率论基本概念（分布、期望、方差）",
        "能推导简单的梯度下降公式",
    ],
    "ml": [
        "理解监督学习、无监督学习基本概念",
        "能使用scikit-learn实现常见算法",
        "能解释模型评估指标（准确率、召回率、F1）",
    ],
    "dl": [
        "理解神经网络基本结构（前向传播、反向传播）",
        "能使用PyTorch构建简单CNN/RNN模型",
        "理解Transformer架构核心思想",
    ],
    "engineering": [
        "能使用Docker容器化部署模型",
        "了解MLOps基本流程和工具链",
        "能编写单元测试和集成测试",
    ],
    "research_method": [
        "能独立阅读并理解AI领域论文",
        "能复现论文中的核心实验",
        "能提出有价值的研究问题",
    ],
    "project_practice": [
        "能完成一个完整的AI项目（数据→模型→部署）",
        "能使用Kaggle平台参与竞赛",
        "能撰写项目技术文档",
    ],
    "team_training": [
        "能制定团队学习计划并跟踪进度",
        "能组织有效的知识分享会",
        "能建立团队知识库和代码评审流程",
    ],
}

# ============================================================
# 核心逻辑函数
# ============================================================

def validate_inputs(level, goal, total_weeks):
    """校验输入参数有效性"""
    # 先检查必需参数是否存在
    if not level or not goal:
        return False, "E001"
    
    # 检查水平是否有效
    if level not in LEVELS:
        return False, "E002"
    
    # 检查目标是否有效
    if goal not in GOAL_TYPES:
        return False, "E003"
    
    # 检查周数是否有效（注意：0 是无效值，但不是"缺少参数"）
    if total_weeks is None or total_weeks < 1 or total_weeks > 52:
        return False, "E004"
    
    return True, "OK"


def get_level_adjustment(level):
    """根据基础水平返回周数调整因子"""
    factors = {"L0": 1.3, "L1": 1.1, "L2": 0.9, "L3": 0.7}
    return factors.get(level, 1.0)


def get_goal_modules(goal):
    """获取目标对应的技能模块列表"""
    return SKILL_MODULES.get(goal, [])


def get_module_priority(module_name, goal):
    """根据目标和模块名称计算优先级权重"""
    # 基础优先级
    base_priority = {
        "career": {"Python编程基础": 1.2, "工程实践": 1.1},
        "research": {"数学基础深化": 1.2, "论文阅读与复现": 1.1},
        "project": {"项目开发实践": 1.2, "深度学习实战": 1.1},
        "teaching": {"核心知识体系": 1.2, "团队基础摸底": 1.1},
    }
    
    # 获取目标对应的优先级调整
    goal_priority = base_priority.get(goal, {})
    return goal_priority.get(module_name, 1.0)


def generate_weekly_plan(level, goal, total_weeks):
    """生成分周学习计划（动态调整版）"""
    # 校验输入
    valid, err_code = validate_inputs(level, goal, total_weeks)
    if not valid:
        return None, err_code

    # 获取模块列表
    modules = get_goal_modules(goal)
    if not modules:
        return None, "E005"

    # 计算调整后的总周数
    adjustment = get_level_adjustment(level)
    adjusted_weeks = max(1, int(total_weeks * adjustment))

    # 根据用户基础水平动态调整模块顺序
    if level in ["L0", "L1"]:
        # 基础较弱时，优先安排基础模块
        modules.sort(key=lambda m: 0 if "基础" in m["name"] or "入门" in m["name"] else 1)
    elif level in ["L2", "L3"]:
        # 基础较好时，优先安排核心/高级模块
        modules.sort(key=lambda m: 0 if "核心" in m["name"] or "深化" in m["name"] or "理论" in m["name"] else 1)

    # 计算模块权重（结合基础周数和优先级）
    module_weights = []
    for m in modules:
        priority = get_module_priority(m["name"], goal)
        weight = m["weeks"] * priority
        module_weights.append(weight)
    
    total_weight = sum(module_weights)
    if total_weight <= 0:
        return None, "E005"

    # 动态分配每周任务
    weekly_plan = []
    week_counter = 1

    for idx, module in enumerate(modules):
        # 计算该模块应分配的周数（动态调整）
        module_weeks = max(1, round(module_weights[idx] / total_weight * adjusted_weeks))
        
        # 根据基础水平调整每周任务深度
        if level == "L0":
            task_depth = "基础"
        elif level == "L1":
            task_depth = "入门"
        elif level == "L2":
            task_depth = "进阶"
        else:
            task_depth = "高级"

        for i in range(module_weeks):
            if week_counter > total_weeks:
                break

            # 获取该模块对应资源
            resource_key = MODULE_RESOURCE_MAP.get(module["name"], "ml")
            resources = RESOURCES.get(resource_key, [])
            
            # 获取验收标准
            acceptance = ACCEPTANCE_CRITERIA.get(resource_key, [])

            # 根据周数进度动态调整任务内容
            progress = i / max(1, module_weeks - 1) if module_weeks > 1 else 1.0
            
            # 构建每周计划项
            week_item = {
                "week": week_counter,
                "module_id": module["id"],
                "module_name": module["name"],
                "topic": f"{module['name']} - 第{i+1}周 ({task_depth})",
                "tasks": [
                    f"学习{module['name']}核心概念（{task_depth}阶段）",
                    f"完成{module['name']}配套练习（进度{int(progress*100)}%）",
                    "记录学习笔记并总结",
                ],
                "resources": resources[:3],  # 每周围绕3个资源
                "acceptance": acceptance[:2] if acceptance else [
                    f"完成{module['name']}相关练习",
                    "能独立解释核心概念",
                    "完成本周复盘总结",
                ],
                "metadata": {
                    "level": level,
                    "goal": goal,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "task_depth": task_depth,
                    "progress": progress,
                }
            }
            weekly_plan.append(week_item)
            week_counter += 1

        if week_counter > total_weeks:
            break

    # 如果生成的计划为空，返回错误
    if not weekly_plan:
        return None, "E006"

    return weekly_plan, "OK"


def format_plan_output(plan):
    """将计划格式化为可读文本"""
    if not plan:
        return ""

    lines = []
    lines.append("=" * 60)
    lines.append("AI学习路径规划")
    lines.append("=" * 60)

    current_module = None
    for item in plan:
        if item["module_name"] != current_module:
            current
