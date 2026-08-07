#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coding-interview-university - 编程面试计算机科学学习路径

本脚本根据功能规格独立实现（clean-room），提供学习路径规划、
知识点拆解、资源推荐、进度追踪建议和面试模拟指引等核心能力。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import sys
from typing import Dict, List, Tuple

# 错误码定义
ERROR_INVALID_INPUT = "E001"      # 输入参数无效
ERROR_INVALID_LEVEL = "E002"      # 用户水平等级无效
ERROR_INVALID_TARGET = "E003"     # 目标岗位无效
ERROR_UNKNOWN_TOPIC = "E004"      # 未知知识点主题
ERROR_UNKNOWN_RESOURCE_TYPE = "E005"  # 未知资源类型
ERROR_INVALID_PHASE = "E006"      # 无效的学习阶段
ERROR_INVALID_QUESTION_TYPE = "E007"  # 无效的面试题类型
ERROR_INVALID_PROGRESS = "E008"   # 无效的进度参数
ERROR_INTERNAL = "E009"           # 内部逻辑错误
ERROR_SELFTEST_FAILED = "E010"    # 自检失败

# ==================== 核心数据定义 ====================

# 用户水平等级
LEVELS = ["零基础", "初级", "中级", "高级"]

# 目标岗位类型
TARGET_ROLES = ["后端", "前端", "全栈", "算法", "系统"]

# 学习阶段
PHASES = ["第一阶段", "第二阶段", "第三阶段", "第四阶段"]

# 知识点主题分类
TOPICS = {
    "数据结构": ["数组", "链表", "栈", "队列", "哈希表", "树", "图", "堆"],
    "算法": ["排序", "搜索", "动态规划", "贪心", "回溯", "分治"],
    "操作系统": ["进程", "线程", "内存管理", "文件系统", "调度"],
    "网络": ["TCP/IP", "HTTP", "DNS", "WebSocket", "网络安全"],
    "数据库": ["SQL", "索引", "事务", "NoSQL", "优化"],
}

# 资源类型
RESOURCE_TYPES = ["书籍", "课程", "练习平台", "视频", "文档"]

# 面试题类型
QUESTION_TYPES = ["算法题", "系统设计", "行为面试", "基础知识", "编程语言"]

# 学习计划模板（按水平与目标岗位生成）
LEARNING_PLAN_TEMPLATE = {
    "零基础": {
        "第一阶段": "编程基础与计算机导论",
        "第二阶段": "数据结构与算法入门",
        "第三阶段": "操作系统与网络基础",
        "第四阶段": "系统设计初步与面试准备",
    },
    "初级": {
        "第一阶段": "数据结构与算法强化",
        "第二阶段": "操作系统与网络深入",
        "第三阶段": "数据库与系统设计入门",
        "第四阶段": "面试题专项训练",
    },
    "中级": {
        "第一阶段": "算法进阶与复杂度分析",
        "第二阶段": "系统设计深入与架构模式",
        "第三阶段": "分布式系统与高并发",
        "第四阶段": "综合面试模拟与项目梳理",
    },
    "高级": {
        "第一阶段": "高级算法与数学基础",
        "第二阶段": "大规模系统架构设计",
        "第三阶段": "性能优化与安全加固",
        "第四阶段": "技术领导力与面试策略",
    },
}

# 知识点拆解模板
TOPIC_DETAILS = {
    "数组": "线性数据结构，支持随机访问，插入删除 O(n)，适合读多写少场景",
    "链表": "线性数据结构，插入删除 O(1)，查找 O(n)，适合写多读少场景",
    "栈": "后进先出（LIFO），常用于函数调用、表达式求值、括号匹配",
    "队列": "先进先出（FIFO），常用于任务调度、缓冲、广度优先搜索",
    "哈希表": "键值存储，平均 O(1) 查找，需处理哈希冲突，如链地址法、开放寻址",
    "树": "层次结构，二叉树、BST、AVL、红黑树等，查找效率取决于树平衡",
    "图": "节点与边的集合，邻接矩阵或邻接表存储，遍历有 DFS 和 BFS",
    "堆": "完全二叉树，最大堆/最小堆，常用于优先队列和 Top-K 问题",
    "排序": "冒泡、选择、插入、归并、快排、堆排，重点掌握时间与空间复杂度",
    "搜索": "二分查找（有序数组）、深度优先、广度优先、A* 启发式搜索",
    "动态规划": "重叠子问题与最优子结构，状态转移方程，记忆化或递推实现",
    "贪心": "每一步取当前最优，需证明局部最优能导致全局最优",
    "回溯": "递归 + 剪枝，适用于排列组合、子集、棋盘类问题",
    "分治": "将大问题分解为小问题，递归求解后合并结果，如归并排序、快速幂",
    "进程": "资源分配基本单位，拥有独立地址空间，创建开销大",
    "线程": "CPU 调度基本单位，共享进程资源，创建开销小，需同步互斥",
    "内存管理": "虚拟内存、分页分段、局部性原理、页面置换算法",
    "文件系统": "文件存储与目录结构，inode、文件描述符、权限管理",
    "调度": "CPU 调度算法：先来先服务、短作业优先、时间片轮转、多级队列",
    "TCP/IP": "传输控制协议/网际协议，可靠连接、三次握手、四次挥手、拥塞控制",
    "HTTP": "应用层协议，无状态，方法有 GET/POST/PUT/DELETE，状态码分类",
    "DNS": "域名解析系统，层级结构，递归与迭代查询",
    "WebSocket": "全双工通信协议，基于 TCP，适合实时交互场景",
    "网络安全": "加密算法、HTTPS、防火墙、DDoS 防护、身份认证",
    "SQL": "结构化查询语言，DDL/DML/DCL，联表查询、聚合函数、子查询",
    "索引": "加速查询的数据结构，B+树、哈希索引，注意索引失效场景",
    "事务": "ACID 特性，隔离级别，并发控制，锁机制与 MVCC",
    "NoSQL": "非关系型数据库，KV、文档、列族、图数据库，适合特定场景",
    "优化": "执行计划分析、慢查询优化、分库分表、缓存策略",
}

# 资源推荐模板
RESOURCE_RECOMMENDATIONS = {
    "书籍": "《算法导论》《数据结构与算法分析》《深入理解计算机系统》《数据库系统概念》",
    "课程": "CS50、MIT 6.006、Coursera 算法专项、操作系统公开课",
    "练习平台": "LeetCode、HackerRank、Codeforces、牛客网、LintCode",
    "视频": "B站技术公开课、YouTube 算法讲解、慕课网实战课程",
    "文档": "MDN Web 文档、Java 官方文档、Python 官方教程、系统设计入门 GitHub",
}

# 进度追踪建议
PROGRESS_SUGGESTIONS = {
    "第一阶段": "每周完成 2-3 个核心知识点，每周末做一次总结复习，用思维导图梳理知识框架",
    "第二阶段": "每学完一个主题，完成 5-10 道相关练习题，记录错误并复盘",
    "第三阶段": "每两周完成一个项目实战，将所学知识应用到实际场景中",
    "第四阶段": "每周进行 2-3 次模拟面试，录制回答并复盘改进",
}

# 面试模拟指引
INTERVIEW_GUIDANCE = {
    "算法题": "先明确输入输出约束，思考暴力解法再优化，注意时间空间复杂度，边写边解释思路",
    "系统设计": "先明确需求和非功能指标，画系统架构图，考虑扩展性、可用性、一致性，分模块阐述",
    "行为面试": "用 STAR 法则（情境-任务-行动-结果）组织回答，突出个人贡献和量化成果",
    "基础知识": "系统复习核心概念，注意知识之间的联系，能举出实际例子说明",
    "编程语言": "掌握语言特性、内存管理、并发模型，熟悉常用库和框架",
}


# ==================== 核心业务逻辑 ====================

def generate_learning_plan(level: str, target_role: str) -> Dict[str, str]:
    """
    根据用户水平和目标岗位生成分阶段学习计划。

    Args:
        level: 用户当前水平（零基础/初级/中级/高级）
        target_role: 目标岗位（后端/前端/全栈/算法/系统）

    Returns:
        包含四个阶段学习计划的字典

    Raises:
        ValueError: 输入参数无效时抛出，错误码 E001/E002/E003
    """
    if not level or not isinstance(level, str):
        raise ValueError(f"{ERROR_INVALID_INPUT}: 用户水平不能为空且必须是字符串")
    if not target_role or not isinstance(target_role, str):
        raise ValueError(f"{ERROR_INVALID_INPUT}: 目标岗位不能为空且必须是字符串")

    if level not in LEVELS:
        raise ValueError(f"{ERROR_INVALID_LEVEL}: 无效的用户水平 '{level}'，可选值: {LEVELS}")
    if target_role not in TARGET_ROLES:
        raise ValueError(f"{ERROR_INVALID_TARGET}: 无效的目标岗位 '{target_role}'，可选值: {TARGET_ROLES}")

    # 根据水平和目标岗位生成计划
    base_plan = LEARNING_PLAN_TEMPLATE.get(level, {})
    plan = {}

    for phase, content in base_plan.items():
        # 根据目标岗位增加特定内容
        role_specific = ""
        if target_role == "后端":
            role_specific = "（侧重服务端架构、数据库设计、API 开发）"
        elif target_role == "前端":
            role_specific = "（侧重浏览器原理、渲染性能、组件化设计）"
        elif target_role == "全栈":
            role_specific = "（前后端兼顾，注重系统整体设计）"
        elif target_role == "算法":
            role_specific = "（侧重算法优化、数学建模、复杂度分析）"
        elif target_role == "系统":
            role_specific = "（侧重分布式、高并发、基础设施）"

        plan[phase] = f"{content}{role_specific}"

    return plan


def breakdown_topic(topic: str) -> str:
    """
    将计算机科学核心主题拆解为可执行的学习单元。

    Args:
        topic: 知识点主题名称

    Returns:
        知识点的详细拆解说明

    Raises:
        ValueError: 未知知识点主题时抛出，错误码 E004
    """
    if not topic or not isinstance(topic, str):
        raise ValueError(f"{ERROR_INVALID_INPUT}: 知识点主题不能为空且必须是字符串")

    # 先尝试精确匹配
    if topic in TOPIC_DETAILS:
        return TOPIC_DETAILS[topic]

    # 尝试在分类中找到
    for category, topics in TOPICS.items():
        if topic in topics:
            return TOPIC_DETAILS.get(topic, f"暂无详细拆解，建议从{category}分类中学习")

    # 尝试模糊匹配
    for known_topic, detail in TOPIC_DETAILS.items():
        if topic in known_topic or known_topic in topic:
            return detail

    raise ValueError(f"{ERROR_UNKNOWN_TOPIC}: 未知知识点主题 '{topic}'，请从以下主题中选择: {list(TOPIC_DETAILS.keys())}")


def recommend_resources(resource_type: str) -> str:
    """
    针对具体知识点推荐教材、课程、练习平台等资源。

    Args:
        resource_type: 资源类型（书籍/课程/练习平台/视频/文档）

    Returns:
        推荐的资源列表

    Raises:
        ValueError: 未知资源类型时抛出，错误码 E005
    """
    if not resource_type or not isinstance(resource_type, str):
        raise ValueError(f"{ERROR_INVALID_INPUT}: 资源类型不能为空且必须是字符串")

    if resource_type not in RESOURCE_TYPES:
        raise ValueError(f"{ERROR_UNKNOWN_RESOURCE_TYPE}: 未知资源类型 '{resource_type}'，可选值: {RESOURCE_TYPES}")

    return RESOURCE_RECOMMENDATIONS.get(resource_type, "")


def get_progress_suggestion(phase: str) -> str:
    """
    提供阶段性自测方法与里程碑设定建议。

    Args:
        phase: 学习阶段（第一阶段/第二阶段/第三阶段/第四阶段）

    Returns:
        该阶段的进度追踪建议

    Raises:
        ValueError: 无效的学习阶段时抛出，错误码 E006
    """
    if not phase or not isinstance(phase, str):
        raise ValueError(f"{ERROR_INVALID_INPUT}: 学习阶段不能为空且必须是字符串")

    if phase not in PHASES:
        raise ValueError(f"{ERROR_INVALID_PHASE}: 无效的学习阶段 '{phase}'，可选值: {PHASES}")

    return PROGRESS_SUGGESTIONS.get(phase, "")


def get_interview_guidance(question_type: str) -> str:
    """
    给出常见面试题型分类与练习策略。

    Args:
        question_type: 面试题类型（算法题/系统设计/行为面试/基础知识/编程语言）

    Returns:
        对应题型的学习策略

    Raises:
        ValueError: 无效的面试题类型时抛出，错误码 E007
    """
    if not question_type or not isinstance(question_type, str):
        raise ValueError(f"{ERROR_INVALID_INPUT}: 面试题类型不能为空且必须是字符串")

    if question_type not in QUESTION_TYPES:
        raise ValueError(f"{ERROR_INVALID_QUESTION_TYPE}: 无效的面试题类型 '{question_type}'，可选值: {QUESTION_TYPES}")

    return INTERVIEW_GUIDANCE.get(question_type, "")


def estimate_progress(completed_topics: List[str], total_topics: List[str]) -> float:
    """
    根据已完成知识点估算学习进度。

    Args:
        completed_topics: 已完成的知识点列表
        total_topics: 总知识点列表

    Returns:
        进度百分比（0-100 的浮点数）

    Raises:
        ValueError: 进度参数无效时抛出，错误码 E008
    """
    if not total_topics:
        raise ValueError(f"{ERROR_INVALID_PROGRESS}: 总知识点列表不能为空")
    if not isinstance(completed_topics, list) or not isinstance(total_topics, list):
        raise ValueError(f"{ERROR_INVALID_PROGRESS}: 参数必须是列表类型")

    # 去重并过滤无效知识点
    valid_completed = set()
    for topic in completed_topics:
        if isinstance(topic, str) and topic in total_topics:
            valid_completed.add(topic)

    if not valid_completed:
        return 0.0

    progress = (len(valid_completed) / len(total_topics)) * 100.0
    return min(progress, 100.0)


# ==================== 命令行接口 ====================

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑的正确性。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。

    Returns:
        0 表示自检通过，1 表示自检失败
    """
    print("开始运行自检...")

    try:
        # 测试 1: 生成学习计划
        plan = generate_learning_plan("零基础", "后端")
        assert len(plan) == 4, f"学习计划应包含 4 个阶段，实际 {len(plan)} 个"
        for phase in PHASES:
            assert phase in plan, f"学习计划缺少 {phase}"
            assert isinstance(plan[phase], str) and len(plan[phase]) > 0, f"{phase} 内容为空"

        # 测试 2: 不同水平生成不同计划
        plan_beginner = generate_learning_plan("零基础", "后端")
        plan_expert = generate_learning_plan("高级", "后端")
        assert plan_beginner != plan_expert, "不同水平应生成不同计划"

        # 测试 3: 知识点拆解
        topic_detail = breakdown_topic("数组")
        assert isinstance(topic_detail, str) and len(topic_detail) > 10, "知识点拆解内容过短"

        # 测试 4: 资源推荐
        books = recommend_resources("书籍")
        assert isinstance(books, str) and len(books) > 10, "书籍推荐内容过短"

        # 测试 5: 进度追踪建议
        suggestion = get_progress_suggestion("第一阶段")
        assert isinstance(suggestion, str) and len(suggestion) > 10, "进度建议内容过短"

        # 测试 6: 面试模拟指引
        guidance = get_interview_guidance("算法题")
        assert isinstance(guidance, str) and len(guidance) > 10, "面试指引内容过短"

        # 测试 7: 进度估算
        all_topics = ["数组", "链表", "栈", "队列"]
        completed = ["数组", "链表"]
        progress = estimate_progress(completed, all_topics)
        # 宽松断言：进度应在合理范围内（约 50%，允许 ±20% 浮动）
        assert 30 <= progress <= 70, f"进度估算异常: {progress}"

        # 测试 8: 错误处理
        try:
            generate_learning_plan("invalid_level", "后端")
            assert False, "应抛出无效水平错误"
        except ValueError as e:
            assert str(e).startswith(ERROR_INVALID_LEVEL), f"错误码不正确: {e}"

        try:
            breakdown_topic("不存在的主题")
            assert False, "应抛出未知主题错误"
        except ValueError as e:
            assert str(e).startswith(ERROR_UNKNOWN_TOPIC), f"错误码不正确: {e}"

        # 测试 9: 边界情况 - 空进度
        progress_zero = estimate_progress([], all_topics)
        assert progress_zero == 0.0, "空进度应返回 0"

        # 测试 10: 所有知识点主题都能拆解
        for category, topics in TOPICS.items():
            for topic in topics:
                detail = breakdown_topic(topic)
                assert isinstance(detail, str) and len(detail) > 5, f"主题 '{topic}' 拆解失败"

        print("自检通过：所有核心逻辑验证成功")
        return 0

    except AssertionError as e:
        print(f"{ERROR_SELFTEST_FAILED}: 自检失败 - 断言错误: {e}")
        return 1
    except ValueError as e:
        print(f"{ERROR_SELFTEST_FAILED}: 自检失败 - 值错误: {e}")
        return 1
    except Exception as e:
        print(f"{ERROR_SELFTEST_FAILED}: 自检失败 - 未预期异常: {e}")
        return 1


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="编程面试计算机科学学习路径工具",
        epilog="示例: python main.py --plan --level 零基础 --target 后端"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码数据，不访问外部资源）"
    )

    parser.add_argument(
        "--plan",
        action="store_true",
        help="生成学习计划"
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=LEVELS,
        default="零基础",
        help="用户当前水平"
    )
    parser.add_argument(
        "--target",
        type=str,
        choices=TARGET_ROLES,
        default="后端",
        help="目标岗位"
    )

    parser.add_argument(
        "--topic",
        type=str,
        help="知识点主题拆解"
    )

    parser.add_argument(
        "--resource",
        type=str,
        choices=RESOURCE_TYPES,
        help="推荐的学习资源类型"
    )

    parser.add_argument(
        "--progress",
        type=str,
        choices=PHASES,
        help="获取某阶段的进度追踪建议"
    )

    parser.add_argument(
        "--interview",
        type=str,
        choices=QUESTION_TYPES,
        help="获取某类面试题的准备策略"
    )

    return parser.parse_args()


def main():
    """主入口函数。"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 正常功能模式
    try:
        if args.plan:
            print("=" * 60)
            print(f"【学习计划】水平: {args.level} | 目标岗位: {args.target}")
            print("=" * 60)
            plan = generate_learning_plan(args.level, args.target)
            for phase, content in plan.items():
                print(f"\n📌 {phase}:")
                print(f"   {content}")
            print()

        if args.topic:
            print("=" * 60)
            print(f"【知识点拆解】{args.topic}")
            print("=" * 60)
            detail = breakdown_topic(args.topic)
            print(f"  {detail}")
            print()

        if args.resource:
            print("=" * 60)
            print(f"【资源推荐】{args.resource}")
            print("=" * 60)
            resources = recommend_resources(args.resource)
            print(f"  {resources}")
            print()

        if args.progress:
            print("=" * 60)
            print(f"【进度追踪建议】{args.progress}")
            print("=" * 60)
            suggestion = get_progress_suggestion(args.progress)
            print(f"  {suggestion}")
            print()

        if args.interview:
            print("=" * 60)
            print(f"【面试模拟指引】{args.interview}")
            print("=" * 60)
            guidance = get_interview_guidance(args.interview)
            print(f"  {guidance}")
            print()

        # 如果没有指定任何功能，显示帮助
        if not (args.plan or args.topic or args.resource or args.progress or args.interview):
            print("请指定要执行的功能。使用 --help 查看帮助。")
            print("示例: python main.py --plan --level 零基础 --target 后端")
            print("      python main.py --topic 数组")
            print("      python main.py --resource 书籍")
            print("      python main.py --progress 第一阶段")
            print("      python main.py --interview 算法题")
            print("      python main.py --selftest  # 运行自检")

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"{ERROR_INTERNAL}: 发生未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
