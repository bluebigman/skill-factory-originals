#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 健身计划定制技能（Clean-Room 独立实现）

功能概述：
    依据用户输入的健身目标、每周可用天数、单次训练时长与器械条件，
    生成结构化的训练计划与饮食参考方案。

设计原则：
    1. 仅依据功能规格独立实现，不参考任何既有代码。
    2. 仅使用 Python 标准库，无第三方依赖。
    3. 提供 --selftest 离线自检模式，使用内置硬编码样例验证核心逻辑。
    4. 中文注释，错误码 E001-E010。
"""

import argparse
import sys
import json
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

class ErrorCode(Enum):
    """错误码定义"""
    E001 = "E001: 参数缺失或为空"
    E002 = "E002: 目标类型不支持"
    E003 = "E003: 训练天数超出合理范围"
    E004 = "E004: 训练时长超出合理范围"
    E005 = "E005: 器械条件无效"
    E006 = "E006: 输入格式错误"
    E007 = "E007: 内部逻辑错误"
    E008 = "E008: 输出序列化失败"
    E009 = "E009: 未知错误"
    E010 = "E010: 自检失败"


# 支持的目标类型
SUPPORTED_GOALS = ("减脂", "增肌", "塑形")

# 器械条件映射
EQUIPMENT_MAP = {
    "自由重量": "free_weights",
    "固定器械": "machines",
    "自重训练": "bodyweight",
    "弹力带": "resistance_bands",
    "混合": "mixed",
}

# 动作模式分类
MOVEMENT_PATTERNS = ["推", "拉", "蹲", "铰链", "核心"]

# 饮食宏量营养素比例（目标类型 -> (蛋白质, 碳水, 脂肪)）
MACRO_RATIOS = {
    "减脂": (0.35, 0.40, 0.25),
    "增肌": (0.30, 0.50, 0.20),
    "塑形": (0.30, 0.45, 0.25),
}

# 动作库（肌群 -> 动作列表）
EXERCISE_LIBRARY = {
    "推": ["俯卧撑", "哑铃卧推", "杠铃卧推", "坐姿推胸", "肩推"],
    "拉": ["引体向上", "哑铃划船", "坐姿划船", "高位下拉", "面拉"],
    "蹲": ["深蹲", "哑铃深蹲", "腿举", "箭步蹲", "保加利亚分腿蹲"],
    "铰链": ["硬拉", "罗马尼亚硬拉", "臀桥", "壶铃摆动", "早安式"],
    "核心": ["平板支撑", "卷腹", "俄罗斯转体", "悬垂举腿", "鸟狗式"],
}

# 默认动作分配（目标类型 -> 动作模式 -> 动作数）
DEFAULT_EXERCISE_DISTRIBUTION = {
    "减脂": {"推": 2, "拉": 2, "蹲": 2, "铰链": 1, "核心": 2},
    "增肌": {"推": 3, "拉": 3, "蹲": 2, "铰链": 2, "核心": 1},
    "塑形": {"推": 2, "拉": 2, "蹲": 2, "铰链": 2, "核心": 2},
}

# 饮食食物示例
FOOD_EXAMPLES = {
    "蛋白质": ["鸡胸肉", "鸡蛋", "鱼肉", "豆腐", "希腊酸奶", "牛肉"],
    "碳水": ["糙米", "燕麦", "红薯", "全麦面包", "藜麦", "香蕉"],
    "脂肪": ["牛油果", "坚果", "橄榄油", "花生酱", "亚麻籽", "鲑鱼"],
}

# 训练提示语
TRAINING_NOTES = {
    "减脂": "保持中等强度，组间休息30-60秒，注意心率控制。",
    "增肌": "采用渐进超负荷原则，组间休息60-90秒，注重动作质量。",
    "塑形": "中等重量多次数，组间休息45-60秒，强调肌肉控制与拉伸。",
}


# ============================================================
# 核心数据结构
# ============================================================

class TrainingPlan:
    """训练计划数据结构"""

    def __init__(self, goal: str, days_per_week: int, session_minutes: int,
                 equipment: str):
        self.goal = goal
        self.days_per_week = days_per_week
        self.session_minutes = session_minutes
        self.equipment = equipment
        self.weekly_schedule: List[Dict] = []
        self.diet_plan: Dict = {}
        self.notes: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "goal": self.goal,
            "days_per_week": self.days_per_week,
            "session_minutes": self.session_minutes,
            "equipment": self.equipment,
            "weekly_schedule": self.weekly_schedule,
            "diet_plan": self.diet_plan,
            "notes": self.notes,
        }


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(goal: str, days_per_week: int, session_minutes: int,
                   equipment: str) -> None:
    """
    校验输入参数合法性

    参数:
        goal: 健身目标
        days_per_week: 每周训练天数
        session_minutes: 单次训练时长（分钟）
        equipment: 器械条件

    异常:
        raises ValueError: 参数不合法时抛出，附错误码
    """
    # E001: 参数缺失或为空
    if not goal or not equipment:
        raise ValueError(f"{ErrorCode.E001.value}: goal和equipment不能为空")

    # E002: 目标类型不支持
    if goal not in SUPPORTED_GOALS:
        raise ValueError(
            f"{ErrorCode.E002.value}: 不支持的目标类型 '{goal}'，"
            f"支持: {SUPPORTED_GOALS}"
        )

    # E003: 训练天数超出合理范围
    if not isinstance(days_per_week, int) or days_per_week < 1 or days_per_week > 7:
        raise ValueError(
            f"{ErrorCode.E003.value}: 训练天数必须在1-7之间，"
            f"当前值: {days_per_week}"
        )

    # E004: 训练时长超出合理范围
    if not isinstance(session_minutes, int) or session_minutes < 20 or session_minutes > 120:
        raise ValueError(
            f"{ErrorCode.E004.value}: 训练时长必须在20-120分钟之间，"
            f"当前值: {session_minutes}"
        )

    # E005: 器械条件无效
    if equipment not in EQUIPMENT_MAP:
        raise ValueError(
            f"{ErrorCode.E005.value}: 器械条件 '{equipment}' 不在支持列表中，"
            f"支持: {list(EQUIPMENT_MAP.keys())}"
        )


def calculate_exercise_count(session_minutes: int, days_per_week: int) -> int:
    """
    计算单次训练建议动作数量

    规则:
        - 基础数量根据训练时长确定
        - 训练天数多时适当减少单次动作数，避免过度训练

    参数:
        session_minutes: 单次训练时长（分钟）
        days_per_week: 每周训练天数

    返回:
        int: 建议动作数量
    """
    # 基础数量：20分钟3个，60分钟6个，120分钟10个（线性插值）
    base_count = 3 + (session_minutes - 20) * 7 // 100

    # 天数调整：天数多则减少单次动作数
    if days_per_week >= 6:
        base_count = max(3, base_count - 2)
    elif days_per_week >= 4:
        base_count = max(3, base_count - 1)

    return base_count


def distribute_exercises(goal: str, total_count: int) -> Dict[str, int]:
    """
    根据目标分配动作到各动作模式

    参数:
        goal: 健身目标
        total_count: 总动作数

    返回:
        Dict[str, int]: 动作模式 -> 动作数量
    """
    # 获取默认分配比例
    distribution = DEFAULT_EXERCISE_DISTRIBUTION[goal].copy()

    # 计算默认总数
    default_total = sum(distribution.values())

    # 如果总动作数不同，按比例调整
    if default_total != total_count:
        scale = total_count / default_total
        adjusted = {}
        remaining = total_count

        # 先按比例分配
        for pattern, count in distribution.items():
            adjusted[pattern] = max(1, int(count * scale))
            remaining -= adjusted[pattern]

        # 处理余数，优先分配给核心
        if remaining > 0:
            adjusted["核心"] += remaining
        elif remaining < 0:
            # 从数量最多的模式中扣除
            max_pattern = max(adjusted, key=adjusted.get)
            adjusted[max_pattern] += remaining

        return adjusted

    return distribution


def select_exercises(pattern: str, count: int, equipment: str) -> List[str]:
    """
    从动作库中选择动作

    参数:
        pattern: 动作模式
        count: 需要选择的动作数
        equipment: 器械条件

    返回:
        List[str]: 动作名称列表
    """
    # 获取该模式下的动作库
    available = EXERCISE_LIBRARY.get(pattern, [])

    # 根据器械条件过滤（简化处理：全部动作都可用，实际可增加过滤逻辑）
    # 这里仅做示例，实际可根据器械类型筛选动作

    # 确保不超过可用动作数
    count = min(count, len(available))

    # 简单轮询选择，避免重复
    selected = []
    idx = 0
    while len(selected) < count:
        selected.append(available[idx % len(available)])
        idx += 1

    return selected


def generate_weekly_schedule(goal: str, days_per_week: int,
                            session_minutes: int,
                            equipment: str) -> List[Dict]:
    """
    生成每周训练计划

    参数:
        goal: 健身目标
        days_per_week: 每周训练天数
        session_minutes: 单次训练时长
        equipment: 器械条件

    返回:
        List[Dict]: 每周训练计划列表
    """
    # 计算每次训练的动作数
    exercises_per_session = calculate_exercise_count(session_minutes, days_per_week)

    # 计算动作分配
    distribution = distribute_exercises(goal, exercises_per_session)

    # 生成每周计划
    weekly_schedule = []

    # 定义训练日名称
    days_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    # 根据训练天数生成计划
    for day_idx in range(days_per_week):
        # 选择训练重点（轮换模式）
        focus_patterns = list(distribution.keys())

        # 创建当日训练计划
        day_plan = {
            "day": days_names[day_idx],
            "focus": f"{goal}训练",
            "exercises": [],
            "duration_minutes": session_minutes,
        }

        # 为每个动作模式选择动作
        for pattern in focus_patterns:
            count = distribution[pattern]
            exercises = select_exercises(pattern, count, equipment)
            for exercise in exercises:
                day_plan["exercises"].append({
                    "name": exercise,
                    "pattern": pattern,
                    "sets": 3 if goal != "减脂" else 4,
                    "reps": "8-12" if goal != "减脂" else "15-20",
                    "rest_seconds": 90 if goal != "减脂" else 45,
                })

        weekly_schedule.append(day_plan)

    return weekly_schedule


def generate_diet_plan(goal: str) -> Dict:
    """
    生成饮食参考方案

    参数:
        goal: 健身目标

    返回:
        Dict: 饮食计划
    """
    # 获取宏量营养素比例
    protein_ratio, carb_ratio, fat_ratio = MACRO_RATIOS[goal]

    # 生成饮食建议
    diet_plan = {
        "macro_ratios": {
            "protein": protein_ratio,
            "carbohydrate": carb_ratio,
            "fat": fat_ratio,
        },
        "food_examples": {
            "protein": FOOD_EXAMPLES["蛋白质"][:4],
            "carbohydrate": FOOD_EXAMPLES["碳水"][:4],
            "fat": FOOD_EXAMPLES["脂肪"][:4],
        },
        "recommendations": [],
    }

    # 根据目标添加建议
    if goal == "减脂":
        diet_plan["recommendations"] = [
            "控制总热量摄入，制造适当热量缺口",
            "增加蛋白质摄入，保持饱腹感",
            "多喝水，减少含糖饮料",
            "注意饮食规律，避免暴饮暴食",
        ]
    elif goal == "增肌":
        diet_plan["recommendations"] = [
            "保证热量盈余，支持肌肉生长",
            "训练后补充蛋白质和碳水",
            "少食多餐，保证营养吸收",
            "保证充足睡眠，促进恢复",
        ]
    else:  # 塑形
        diet_plan["recommendations"] = [
            "均衡营养，控制油脂摄入",
            "适量蛋白质，保持肌肉线条",
            "多吃蔬菜水果，补充维生素",
            "规律饮食，避免过度节食",
        ]

    return diet_plan


def generate_training_plan(goal: str, days_per_week: int,
                           session_minutes: int,
                           equipment: str) -> TrainingPlan:
    """
    生成完整训练计划

    参数:
        goal: 健身目标
        days_per_week: 每周训练天数
        session_minutes: 单次训练时长
        equipment: 器械条件

    返回:
        TrainingPlan: 训练计划对象
    """
    # 校验输入
    validate_input(goal, days_per_week, session_minutes, equipment)

    # 创建计划对象
    plan = TrainingPlan(goal, days_per_week, session_minutes, equipment)

    # 生成每周训练计划
    plan.weekly_schedule = generate_weekly_schedule(
        goal, days_per_week, session_minutes, equipment
    )

    # 生成饮食计划
    plan.diet_plan = generate_diet_plan(goal)

    # 添加训练提示
    plan.notes = TRAINING_NOTES[goal]

    return plan


# ============================================================
# 输出格式化
# ============================================================

def format_plan_as_markdown(plan: TrainingPlan) -> str:
    """
    将训练计划格式化为 Markdown 文本

    参数:
        plan: 训练计划对象

    返回:
        str: Markdown 格式的计划文本
    """
    lines = []
    lines.append(f"# 健身训练计划（{plan.goal}）")
    lines.append("")
    lines.append(f"**目标**: {plan.goal}")
    lines.append(f"**每周训练天数**: {plan.days_per_week} 天")
    lines.append(f"**单次训练时长**: {plan.session_minutes} 分钟")
    lines.append(f"**器械条件**: {plan.equipment}")
    lines.append("")
    lines.append("## 每周训练安排")
    lines.append("")
    lines.append("| 日期 | 训练内容 | 动作数 |")
    lines.append("|------|----------|--------|")

    for day in plan.weekly_schedule:
        lines.append(
            f"| {day['day']} | {day['focus']} | {len(day['exercises'])} |"
        )

    lines.append("")
    lines.append("## 训练动作详情")
    lines.append("")

    for day in plan.weekly_schedule:
        lines.append(f"### {day['day']}")
        lines.append("")
        lines.append("| 动作 | 动作模式 | 组数 | 次数 | 休息(秒) |")
        lines.append("|------|----------|------|------|----------|")

        for exercise in day["exercises"]:
            lines.append(
                f"| {exercise['name']} | {exercise['pattern']} | "
                f"{exercise['sets']} | {exercise['reps']} | "
                f"{exercise['rest_seconds']} |"
            )
        lines.append("")

    # 饮食计划
    lines.append("## 饮食参考方案")
    lines.append("")
    lines.append("### 宏量营养素比例")
    lines.append("")
    ratios = plan.diet_plan["macro_ratios"]
    lines.append(f"- 蛋白质: {ratios['protein']:.0%}")
    lines.append(f"- 碳水化合物: {ratios['carbohydrate']:.0%}")
    lines.append(f"- 脂肪: {ratios['fat']:.0%}")
    lines.append("")
    lines.append("### 食物示例")
    lines.append("")
    for category, foods in plan.diet_plan["food_examples"].items():
        lines.append(f"**{category}**: {', '.join(foods)}")
    lines.append("")
    lines.append("### 建议")
    lines.append("")
    for recommendation in plan.diet_plan["recommendations"]:
        lines.append(f"- {recommendation}")
    lines.append("")
    lines.append("## 训练提示")
    lines.append("")
    lines.append(plan.notes)
    lines.append("")
    lines.append("> ⚠️ 本计划仅供参考，实际训练请根据个人情况调整。")
    lines.append("> 如有身体不适，请立即停止训练并咨询专业人士。")

    return "\n".join(lines)


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检

    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。

    返回:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("开始自检（离线模式，使用内置样例数据）")
    print("=" * 60)

    # 测试用例 1: 减脂计划
    print("\n[测试 1] 减脂计划生成")
    try:
        plan = generate_training_plan("减脂", 4, 45, "混合")
        assert plan is not None, "计划对象不应为 None"
        assert len(plan.weekly_schedule) == 4, "每周应有 4 天训练"
        assert plan.diet_plan is not None, "饮食计划不应为 None"
        assert "macro_ratios" in plan.diet_plan, "饮食计划应包含宏量营养素比例"
        assert 0 < plan.diet_plan["macro_ratios"]["protein"] < 1, "蛋白质比例应在0-1之间"
        print("  ✓ 减脂计划生成成功")
        print(f"  ✓ 训练天数: {len(plan.weekly_schedule)}")
        print(f"  ✓ 蛋白质比例: {plan.diet_plan['macro_ratios']['protein']:.0%}")
    except Exception as e:
        print(f"  ✗ 减脂计划测试失败: {e}")
        return False

    # 测试用例 2: 增肌计划
    print("\n[测试 2] 增肌计划生成")
    try:
        plan = generate_training_plan("增肌", 5, 60, "自由重量")
        assert plan is not None, "计划对象不应为 None"
        assert len(plan.weekly_schedule) == 5, "每周应有 5 天训练"
        assert len(plan.weekly_schedule[0]["exercises"]) > 0, "每天应有训练动作"
        print("  ✓ 增肌计划生成成功")
        print(f"  ✓ 训练天数: {len(plan.weekly_schedule)}")
        print(f"  ✓ 第一天动作数: {len(plan.weekly_schedule[0]['exercises'])}")
    except Exception as e:
        print(f"  ✗ 增肌计划测试失败: {e}")
        return False

    # 测试用例 3: 塑形计划
    print("\n[测试 3] 塑形计划生成")
    try:
        plan = generate_training_plan("塑形", 3, 30, "自重训练")
        assert plan is not None, "计划对象不应为 None"
        assert len(plan.weekly_schedule) == 3, "每周应有 3 天训练"
        assert plan.notes, "训练提示不应为空"
        print("  ✓ 塑形计划生成成功")
        print(f"  ✓ 训练天数: {len(plan.weekly_schedule)}")
        print(f"  ✓ 训练提示: {plan.notes[:20]}...")
    except Exception as e:
        print(f"  ✗ 塑形计划测试失败: {e}")
        return False

    # 测试用例 4: 输入校验
    print("\n[测试 4] 输入校验")
    try:
        # 无效目标
        try:
            generate_training_plan("无效目标", 3, 30, "混合")
            print("  ✗ 无效目标未抛出异常")
            return False
        except ValueError as e:
            assert "E002" in str(e), "错误码应为 E002"
            print("  ✓ 无效目标被正确拒绝")

        # 无效天数
        try:
            generate_training_plan("减脂", 0, 30, "混合")
            print("  ✗ 无效天数未抛出异常")
            return False
        except ValueError as e:
            assert "E003" in str(e), "错误码应为 E003"
            print("  ✓ 无效天数被正确拒绝")

        # 无效时长
        try:
            generate_training_plan("减脂", 3, 10, "混合")
            print("  ✗ 无效时长未抛出异常")
            return False
        except ValueError as e:
            assert "E004" in str(e), "错误码应为 E004"
            print("  ✓ 无效时长被正确拒绝")

        # 无效器械
        try:
            generate_training_plan("减脂", 3, 30, "不存在")
            print("  ✗ 无效器械未抛出异常")
            return False
        except ValueError as e:
            assert "E005" in str(e), "错误码应为 E005"
            print("  ✓ 无效器械被正确拒绝")

    except Exception as e:
        print(f"  ✗ 输入校验测试失败: {e}")
        return False

    # 测试用例 5: 动作数量计算
    print("\n[测试 5] 动作数量计算")
    try:
        count_short = calculate_exercise_count(30, 3)
        count_long = calculate_exercise_count(90, 3)
        assert count_short < count_long, "训练时长越长，动作数应越多"
        assert 3 <= count_short <= 10, "动作数应在合理范围内"
        print(f"  ✓ 30分钟动作数: {count_short}")
        print(f"  ✓ 90分钟动作数: {count_long}")
        print("  ✓ 动作数量计算合理")
    except Exception as e:
        print(f"  ✗ 动作数量计算测试失败: {e}")
        return False

    # 测试用例 6: Markdown 输出
    print("\n[测试 6] Markdown 输出")
    try:
        plan = generate_training_plan("减脂", 4, 45, "混合")
        markdown = format_plan_as_markdown(plan)
        assert markdown, "Markdown 输出不应为空"
        assert "#" in markdown, "应包含标题"
        assert "|" in markdown, "应包含表格"
        assert "饮食" in markdown, "应包含饮食部分"
        print("  ✓ Markdown 输出生成成功")
        print(f"  ✓ 输出长度: {len(markdown)} 字符")
    except Exception as e:
        print(f"  ✗ Markdown 输出测试失败: {e}")
        return False

    # 测试用例 7: JSON 序列化
    print("\n[测试 7] JSON 序列化")
    try:
        plan = generate_training_plan("增肌", 4, 60, "自由重量")
        plan_dict = plan.to_dict()
        json_str = json.dumps(plan_dict, ensure_ascii=False)
        assert json_str, "JSON 序列化不应为空"
        # 验证可以反序列化
        parsed = json.loads(json_str)
        assert parsed["goal"] == "增肌", "目标应保持一致"
        print("  ✓ JSON 序列化成功")
        print(f"  ✓ JSON 长度: {len(json_str)} 字符")
    except Exception as e:
        print(f"  ✗ JSON 序列化测试失败: {e}")
        return False

    # 测试用例 8: 边界情况
    print("\n[测试 8] 边界情况")
    try:
        # 最小参数
        plan_min = generate_training_plan("减脂", 1, 20, "自重训练")
        assert len(plan_min.weekly_schedule) == 1, "最少 1 天训练"
        print("  ✓ 最小参数（1天20分钟）正常")

        # 最大参数
        plan_max = generate_training_plan("增肌", 7, 120, "混合")
        assert len(plan_max.weekly_schedule) == 7, "最多 7 天训练"
        print("  ✓ 最大参数（7天120分钟）正常")

        # 所有目标类型
        for goal in SUPPORTED_GOALS:
            plan = generate_training_plan(goal, 3, 45, "混合")
            assert plan.goal == goal, "目标应匹配"
        print("  ✓ 所有目标类型均正常工作")

    except Exception as e:
        print(f"  ✗ 边界情况测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("自检完成：所有测试通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行接口
# ============================================================

def main() -> int:
    """
    主入口函数

    返回:
        int: 退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="健身计划定制技能 - 生成结构化训练与饮食方案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--goal",
        choices=SUPPORTED_GOALS,
        help="健身目标（减脂/增肌/塑形）",
    )
    parser.add_argument(
        "--days",
        type=int,
        help="每周训练天数（1-7）",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        help="单次训练时长（20-120分钟）",
    )
    parser.add_argument(
        "--equipment",
        choices=list(EQUIPMENT_MAP.keys()),
        help="器械条件",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，离线执行）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 检查必要参数
    if not all([args.goal, args.days, args.minutes, args.equipment]):
        parser.print_help()
        print("\n错误: 需要提供 --goal, --days, --minutes, --equipment 参数")
        print("提示: 使用 --selftest 可运行离线自检")
        return 1

    try:
        # 生成训练计划
        plan = generate_training_plan(
            goal=args.goal,
            days_per_week=args.days,
            session_minutes=args.minutes,
            equipment=args.equipment,
        )

        # 输出结果
        if args.json:
            # JSON 格式输出
            output = json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
        else:
            # Markdown 格式输出
            output = format_plan_as_markdown(plan)

        print(output)
        return 0

    except ValueError as e:
        print(f"输入错误: {e}")
        return 1
    except Exception as e:
        print(f"生成计划失败: {ErrorCode.E009.value}: {e}")
        return 1


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
