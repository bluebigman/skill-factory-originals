#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一周膳食规划 营养搭配 采购清单 (recipe-meal-plan)

根据口味、人数、预算生成一周三餐食谱与采购清单，附热量统计。
本脚本为 clean-room 独立实现，仅依据功能规格文档编写。
"""

import argparse
import json
import math
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# E001: 参数缺失或类型错误
# E002: 预算超出支持范围
# E003: 人数不合法（<=0）
# E004: 口味偏好无法识别
# E005: 菜系数据缺失
# E006: 生成食谱失败
# E007: 采购清单生成失败
# E008: 热量统计失败
# E009: 输出格式不支持
# E010: 内部未知错误
# ============================================================

# ============================================================
# 内置基础数据（硬编码，不依赖外部文件）
# ============================================================

# 菜系定义: 每个菜系包含若干菜品，每个菜品包含食材与热量估算
CUISINES: Dict[str, Dict[str, Any]] = {
    "家常": {
        "早餐": [
            {"name": "小米粥+鸡蛋", "ingredients": ["小米50g", "鸡蛋1个"], "calories": 250},
            {"name": "豆浆+油条", "ingredients": ["豆浆300ml", "油条1根"], "calories": 350},
            {"name": "燕麦牛奶", "ingredients": ["燕麦40g", "牛奶250ml"], "calories": 280},
        ],
        "午餐": [
            {"name": "番茄炒蛋+米饭", "ingredients": ["番茄2个", "鸡蛋2个", "米饭200g"], "calories": 550},
            {"name": "青椒肉丝+米饭", "ingredients": ["青椒2个", "猪肉100g", "米饭200g"], "calories": 600},
            {"name": "土豆炖牛肉+米饭", "ingredients": ["土豆1个", "牛肉150g", "米饭200g"], "calories": 680},
        ],
        "晚餐": [
            {"name": "清炒时蔬+米饭", "ingredients": ["青菜200g", "米饭150g"], "calories": 350},
            {"name": "紫菜蛋花汤+馒头", "ingredients": ["紫菜10g", "鸡蛋1个", "馒头1个"], "calories": 320},
            {"name": "凉拌黄瓜+粥", "ingredients": ["黄瓜1根", "大米粥300ml"], "calories": 250},
        ],
    },
    "川味": {
        "早餐": [
            {"name": "红油抄手", "ingredients": ["抄手200g", "红油10g"], "calories": 420},
            {"name": "担担面", "ingredients": ["面条150g", "肉末50g", "花生碎10g"], "calories": 480},
            {"name": "红糖糍粑", "ingredients": ["糯米150g", "红糖20g"], "calories": 380},
        ],
        "午餐": [
            {"name": "麻婆豆腐+米饭", "ingredients": ["豆腐300g", "肉末50g", "米饭200g"], "calories": 580},
            {"name": "回锅肉+米饭", "ingredients": ["五花肉150g", "蒜苗100g", "米饭200g"], "calories": 720},
            {"name": "水煮鱼+米饭", "ingredients": ["鱼片200g", "豆芽100g", "米饭200g"], "calories": 650},
        ],
        "晚餐": [
            {"name": "酸辣土豆丝+米饭", "ingredients": ["土豆2个", "米饭150g"], "calories": 400},
            {"name": "宫保鸡丁+米饭", "ingredients": ["鸡胸肉150g", "花生50g", "米饭150g"], "calories": 520},
            {"name": "清汤火锅", "ingredients": ["蔬菜200g", "豆腐100g", "粉丝50g"], "calories": 450},
        ],
    },
    "清淡": {
        "早餐": [
            {"name": "蔬菜粥", "ingredients": ["大米50g", "青菜50g"], "calories": 200},
            {"name": "蒸蛋+全麦面包", "ingredients": ["鸡蛋2个", "全麦面包2片"], "calories": 300},
            {"name": "酸奶水果杯", "ingredients": ["酸奶200ml", "苹果1个"], "calories": 250},
        ],
        "午餐": [
            {"name": "清蒸鱼+米饭", "ingredients": ["鲈鱼200g", "米饭200g"], "calories": 500},
            {"name": "白灼虾+米饭", "ingredients": ["虾200g", "米饭200g"], "calories": 480},
            {"name": "蒸鸡胸+蔬菜沙拉", "ingredients": ["鸡胸肉150g", "生菜100g", "番茄1个"], "calories": 420},
        ],
        "晚餐": [
            {"name": "冬瓜汤+米饭", "ingredients": ["冬瓜200g", "米饭150g"], "calories": 280},
            {"name": "蒸南瓜+小米粥", "ingredients": ["南瓜200g", "小米粥300ml"], "calories": 260},
            {"name": "白灼西兰花+糙米饭", "ingredients": ["西兰花200g", "糙米饭150g"], "calories": 300},
        ],
    },
    "粤式": {
        "早餐": [
            {"name": "肠粉", "ingredients": ["米浆150g", "鸡蛋1个", "生菜20g"], "calories": 320},
            {"name": "虾饺", "ingredients": ["虾仁100g", "澄面皮50g"], "calories": 280},
            {"name": "皮蛋瘦肉粥", "ingredients": ["大米50g", "皮蛋1个", "瘦肉50g"], "calories": 350},
        ],
        "午餐": [
            {"name": "白切鸡+米饭", "ingredients": ["鸡肉200g", "姜葱10g", "米饭200g"], "calories": 550},
            {"name": "蜜汁叉烧+米饭", "ingredients": ["猪肉200g", "蜂蜜20g", "米饭200g"], "calories": 680},
            {"name": "清蒸排骨+米饭", "ingredients": ["排骨250g", "豆豉10g", "米饭200g"], "calories": 620},
        ],
        "晚餐": [
            {"name": "老火靓汤+米饭", "ingredients": ["排骨200g", "玉米1根", "米饭150g"], "calories": 450},
            {"name": "清蒸鱼+米饭", "ingredients": ["鱼200g", "蒸鱼豉油10ml", "米饭150g"], "calories": 400},
            {"name": "白灼菜心+米饭", "ingredients": ["菜心250g", "米饭150g"], "calories": 300},
        ],
    },
}

# 口味关键词映射
TASTE_KEYWORDS: Dict[str, List[str]] = {
    "家常": ["家常", "普通", "简单", "传统"],
    "川味": ["辣", "川菜", "麻辣", "重口", "香辣"],
    "清淡": ["清淡", "健康", "少油", "轻食", "减脂"],
    "粤式": ["粤菜", "广东", "鲜", "清淡粤", "早茶"],
}

# 默认参数
DEFAULT_PEOPLE = 2
DEFAULT_BUDGET_PER_DAY = 80  # 元/人/天
DEFAULT_TASTE = "家常"
DEFAULT_DAYS = 7

# 预算范围（元/人/天）
MIN_BUDGET = 30
MAX_BUDGET = 500

# 热量校准目标（千卡/人/天）
TARGET_CALORIES_PER_PERSON = 2000
CALORIES_RANGE = (1500, 2500)


# ============================================================
# 核心功能函数
# ============================================================

def extract_taste(user_input: str) -> Tuple[str, float]:
    """
    从用户输入中识别口味偏好。
    返回 (口味, 置信度 0~1)。无法识别时返回默认口味，置信度较低。
    """
    if not user_input or not isinstance(user_input, str):
        return DEFAULT_TASTE, 0.3

    text = user_input.lower()
    scores: Dict[str, int] = {}

    for taste, keywords in TASTE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in text:
                score += 1
        if score > 0:
            scores[taste] = score

    if not scores:
        return DEFAULT_TASTE, 0.3

    best_taste = max(scores, key=scores.get)
    total_score = sum(scores.values())
    confidence = scores[best_taste] / total_score if total_score > 0 else 0.5
    # 置信度范围 0.5~0.95
    confidence = min(0.95, max(0.5, confidence))
    return best_taste, confidence


def extract_people(user_input: str, default: int = DEFAULT_PEOPLE) -> Tuple[int, float]:
    """
    从用户输入中提取人数。
    返回 (人数, 置信度)。
    """
    if not user_input or not isinstance(user_input, str):
        return default, 0.3

    import re
    # 匹配 "X人" 或 "X个人" 或 "X口人"
    match = re.search(r'(\d+)\s*(?:人|个人|口人)', user_input)
    if match:
        people = int(match.group(1))
        if people > 0:
            return people, 0.9
    return default, 0.3


def extract_budget(user_input: str, default: float = DEFAULT_BUDGET_PER_DAY) -> Tuple[float, float]:
    """
    从用户输入中提取预算（元/人/天）。
    返回 (预算, 置信度)。
    """
    if not user_input or not isinstance(user_input, str):
        return default, 0.3

    import re
    # 匹配 "X元" 或 "X块钱" 或 "预算X"
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|块钱|块)', user_input)
    if match:
        budget = float(match.group(1))
        return budget, 0.9
    return default, 0.3


def validate_budget(budget: float) -> Optional[str]:
    """
    校验预算是否在支持范围内。
    返回错误码字符串或 None。
    """
    if budget < MIN_BUDGET or budget > MAX_BUDGET:
        return "E002"
    return None


def validate_people(people: int) -> Optional[str]:
    """校验人数是否合法。"""
    if people <= 0:
        return "E003"
    return None


def generate_meal_plan(
    taste: str = DEFAULT_TASTE,
    people: int = DEFAULT_PEOPLE,
    budget_per_day: float = DEFAULT_BUDGET_PER_DAY,
    days: int = DEFAULT_DAYS,
) -> Dict[str, Any]:
    """
    生成一周膳食计划。

    参数:
        taste: 口味偏好（家常/川味/清淡/粤式）
        people: 用餐人数
        budget_per_day: 每人每天预算（元）
        days: 生成天数（默认7）

    返回:
        包含食谱、采购清单、热量统计的字典。
    """
    # 参数校验
    if taste not in CUISINES:
        raise ValueError(f"E005: 未知菜系 {taste}")
    if people <= 0:
        raise ValueError("E003: 人数必须为正整数")
    if budget_per_day < MIN_BUDGET or budget_per_day > MAX_BUDGET:
        raise ValueError(f"E002: 预算超出范围 [{MIN_BUDGET}, {MAX_BUDGET}]")
    if days <= 0:
        raise ValueError("E001: 天数必须为正整数")

    cuisine_data = CUISINES[taste]

    # 根据预算调整食材分量系数（简化模型：预算越高，分量越足）
    # 基准预算 80 元/人/天，系数 = 预算/80
    portion_factor = budget_per_day / DEFAULT_BUDGET_PER_DAY
    # 限制系数范围 0.5~1.5，避免极端
    portion_factor = max(0.5, min(1.5, portion_factor))

    # 计算热量校准系数
    # 基准热量（按基础菜谱计算）
    base_calories_per_day = 0
    for meal_type in ["早餐", "午餐", "晚餐"]:
        options = cuisine_data[meal_type]
        # 取平均热量
        avg_cal = sum(d["calories"] for d in options) / len(options)
        base_calories_per_day += avg_cal

    # 校准系数：使人均每日热量接近目标值
    calibration_factor = TARGET_CALORIES_PER_PERSON / (base_calories_per_day * portion_factor)
    # 限制校准系数范围，避免过度调整
    calibration_factor = max(0.8, min(1.2, calibration_factor))

    # 生成每天的食谱
    weekly_plan: List[Dict[str, Any]] = []
    total_calories = 0.0
    total_cost = 0.0
    all_ingredients: Dict[str, float] = {}

    for day_idx in range(days):
        day_plan: Dict[str, Any] = {
            "day": day_idx + 1,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "meals": {},
        }

        day_calories = 0.0
        day_cost = 0.0

        for meal_type in ["早餐", "午餐", "晚餐"]:
            # 轮换选择菜品（简单轮询，保证多样性）
            options = cuisine_data[meal_type]
            dish = options[day_idx % len(options)]

            # 根据人数、预算系数和校准系数调整热量
            adjusted_calories = dish["calories"] * portion_factor * calibration_factor

            # 估算成本（简化：热量/10 约等于成本元）
            dish_cost = adjusted_calories * 0.02 * people

            day_plan["meals"][meal_type] = {
                "name": dish["name"],
                "ingredients": dish["ingredients"].copy(),
                "calories": round(adjusted_calories, 1),
                "cost": round(dish_cost, 2),
            }

            day_calories += adjusted_calories
            day_cost += dish_cost

            # 累加食材到采购清单
            for ing in dish["ingredients"]:
                # 解析食材名称（去掉数字和单位）
                ing_name = ing.rstrip("0123456789gml个根只")
                if ing_name in all_ingredients:
                    all_ingredients[ing_name] += 1.0 * people * portion_factor
                else:
                    all_ingredients[ing_name] = 1.0 * people * portion_factor

        day_plan["total_calories"] = round(day_calories, 1)
        day_plan["total_cost"] = round(day_cost, 2)

        weekly_plan.append(day_plan)
        total_calories += day_calories
        total_cost += day_cost

    # 构建采购清单（按食材汇总）
    shopping_list = []
    for ing_name, qty in all_ingredients.items():
        shopping_list.append({
            "name": ing_name,
            "quantity": round(qty, 1),
            "unit": "份",
        })

    # 计算人均每日热量
    avg_daily_calories_per_person = total_calories / days / people

    # 构建返回结果
    result = {
        "meta": {
            "taste": taste,
            "people": people,
            "budget_per_day": budget_per_day,
            "days": days,
            "generated_at": datetime.now().isoformat(),
            "disclaimer": "本方案由AI生成，仅供学习参考，热量为估算值（误差±15%），不构成医疗建议。",
        },
        "weekly_plan": weekly_plan,
        "shopping_list": shopping_list,
        "nutrition_summary": {
            "avg_daily_calories_per_person": round(avg_daily_calories_per_person, 1),
            "total_calories": round(total_calories, 1),
            "total_cost": round(total_cost, 2),
            "avg_daily_cost_per_person": round(total_cost / days / people, 2),
        },
    }

    return result


def format_output(plan: Dict[str, Any], output_format: str = "text") -> str:
    """
    将计划格式化为指定格式输出。
    支持 text / json / table。
    """
    if output_format == "json":
        return json.dumps(plan, ensure_ascii=False, indent=2)

    if output_format == "table":
        lines = []
        lines.append("=" * 60)
        lines.append(f"一周膳食计划 ({plan['meta']['taste']}风味, {plan['meta']['people']}人)")
        lines.append("=" * 60)

        for day in plan["weekly_plan"]:
            lines.append(f"\n第{day['day']}天:")
            for meal_type, meal in day["meals"].items():
                lines.append(f"  {meal_type}: {meal['name']} ({meal['calories']}千卡)")
            lines.append(f"  小计: {day['total_calories']}千卡, 花费: {day['total_cost']}元")

        lines.append("\n" + "=" * 60)
        lines.append("采购清单:")
        for item in plan["shopping_list"]:
            lines.append(f"  {item['name']}: {item['quantity']}{item['unit']}")

        lines.append("\n" + "=" * 60)
        lines.append("营养统计:")
        lines.append(f"  人均每日热量: {plan['nutrition_summary']['avg_daily_calories_per_person']}千卡")
        lines.append(f"  总热量: {plan['nutrition_summary']['total_calories']}千卡")
        lines.append(f"  总花费: {plan['nutrition_summary']['total_cost']}元")
        lines.append(f"  人均每日花费: {plan['nutrition_summary']['avg_daily_cost_per_person']}元")

        return "\n".join(lines)

    # 默认 text 格式
    lines = []
    lines.append(f"【一周膳食计划】{plan['meta']['taste']}风味 | {plan['meta']['people']}人 | "
                 f"预算{plan['meta']['budget_per_day']}元/人/天")
    lines.append("-" * 40)

    for day in plan["weekly_plan"]:
        lines.append(f"第{day['day']}天:")
        for meal_type, meal in day["meals"].items():
            lines.append(f"  {meal_type}: {meal['name']}")
            lines.append(f"    食材: {', '.join(meal['ingredients'])}")
            lines.append(f"    热量: {meal['calories']}千卡")
        lines.append(f"  日总热量: {day['total_calories']}千卡, 日花费: {day['total_cost']}元")
        lines.append("")

    lines.append("=" * 40)
    lines.append("【采购清单】")
    for item in plan["shopping_list"]:
        lines.append(f"  {item['name']}: {item['quantity']}{item['unit']}")

    lines.append("")
    lines.append("=" * 40)
    lines.append("【营养统计】")
    lines.append(f"  人均每日热量: {plan['nutrition_summary']['avg_daily_calories_per_person']}千卡")
    lines.append(f"  总热量: {plan['nutrition_summary']['total_calories']}千卡")
    lines.append(f"  总花费: {plan['nutrition_summary']['total_cost']}元")
    lines.append(f"  人均每日花费: {plan['nutrition_summary']['avg_daily_cost_per_person']}元")

    return "\n".join(lines)


# ============================================================
# 自检功能 (--selftest)
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。使用内置硬编码数据，不依赖外部环境。
    返回 True 表示全部通过。
    """
    print("开始自检...")
    all_passed = True

    # 测试1: 口味识别
    print("\n[测试1] 口味识别")
    taste, conf = extract_taste("我想要辣一点的川菜")
    assert taste == "川味", f"口味识别失败: {taste}"
    assert conf > 0.5, f"置信度异常: {conf}"
    print(f"  PASS: 识别到川味, 置信度={conf:.2f}")

    taste, conf = extract_taste("")
    assert taste == DEFAULT_TASTE, "空输入应返回默认口味"
    print(f"  PASS: 空输入返回默认口味")

    # 测试2: 人数提取
    print("\n[测试2] 人数提取")
    people, conf = extract_people("我们3个人吃饭")
    assert people == 3, f"人数提取失败: {people}"
    print(f"  PASS: 提取到3人")

    people, conf = extract_people("")
    assert people == DEFAULT_PEOPLE, "空输入应返回默认人数"
    print(f"  PASS: 空输入返回默认人数")

    # 测试3: 预算提取与校验
    print("\n[测试3] 预算提取与校验")
    budget, conf = extract_budget("预算100元一天")
    assert budget == 100.0, f"预算提取失败: {budget}"
    print(f"  PASS: 提取到预算100元")

    err = validate_budget(20)
    assert err == "E002", "低于最低预算应返回E002"
    print(f"  PASS: 低预算返回E002")

    err = validate_budget(600)
    assert err == "E002", "高于最高预算应返回E002"
    print(f"  PASS: 高预算返回E002")

    err = validate_budget(100)
    assert err is None, "正常预算不应返回错误"
    print(f"  PASS: 正常预算通过校验")

    # 测试4: 生成膳食计划
    print("\n[测试4] 生成膳食计划")
    plan = generate_meal_plan(taste="家常", people=2, budget_per_day=80, days=7)
    assert len(plan["weekly_plan"]) == 7, "应生成7天计划"
    assert len(plan["shopping_list"]) > 0, "采购清单不应为空"
    avg_cal = plan["nutrition_summary"]["avg_daily_calories_per_person"]
    assert avg_cal > 1000, f"人均热量应合理，实际: {avg_cal}"
    assert avg_cal < 3000, f"人均热量不应过高，实际: {avg_cal}"
    print(f"  PASS: 生成7天计划, 人均每日热量={avg_cal}千卡")

    # 测试5: 不同菜系
    print("\n[测试5] 不同菜系")
    for taste in CUISINES.keys():
        plan = generate_meal_plan(taste=taste, people=1, budget_per_day=100, days=3)
        assert len(plan["weekly_plan"]) == 3, f"{taste} 菜系生成失败"
        avg_cal = plan["nutrition_summary"]["avg_daily_calories_per_person"]
        assert avg_cal > 1000, f"{taste} 菜系人均热量过低: {avg_cal}"
        print(f"  PASS: {taste} 菜系生成成功, 人均热量={avg_cal:.0f}千卡")

    # 测试6: 预算影响
    print("\n[测试6] 预算影响")
    plan_low = generate_meal_plan(taste="家常", people=2, budget_per_day=40, days=1)
    plan_high = generate_meal_plan(taste="家常", people=2, budget_per_day=200, days=1)
    cal_low = plan_low["nutrition_summary"]["total_calories"]
    cal_high = plan_high["nutrition_summary"]["total_calories"]
    assert cal_high > cal_low, "高预算应产生更高热量（分量更大）"
    print(f"  PASS: 低预算热量={cal_low:.0f}, 高预算热量={cal_high:.0f}")

    # 测试7: 输出格式
    print("\n[测试7] 输出格式")
    plan = generate_meal_plan(taste="清淡", people=3, budget_per_day=60, days=2)
    json_out = format_output(plan, "json")
    assert json_out.startswith("{"), "JSON输出应以{开头"
    parsed = json.loads(json_out)
    assert parsed["meta"]["people"] == 3, "JSON解析失败"
    print(f"  PASS: JSON格式输出正常")

    text_out = format_output(plan, "text")
    assert "采购清单" in text_out, "文本输出应包含采购清单"
    print(f"  PASS: 文本格式输出正常")

    # 测试8: 错误处理
    print("\n[测试8] 错误处理")
    try:
        generate_meal_plan(taste="不存在的菜系", people=2, budget_per_day=80, days=1)
        assert False, "应抛出异常"
    except ValueError as e:
        assert "E005" in str(e), f"错误码错误: {e}"
        print(f"  PASS: 未知菜系返回E005")

    try:
        generate_meal_plan(taste="家常", people=0, budget_per_day=80, days=1)
        assert False, "应抛出异常"
    except ValueError as e:
        assert "E003" in str(e), f"错误码错误: {e}"
        print(f"  PASS: 非法人数返回E003")

    try:
        generate_meal_plan(taste="家常", people=2, budget_per_day=10, days=1)
        assert False, "应抛出异常"
    except ValueError as e:
        assert "E002" in str(e), f"错误码错误: {e}"
        print(f"  PASS: 非法预算返回E002")

    # 测试9: 人数影响
    print("\n[测试9] 人数影响")
    plan_1 = generate_meal_plan(taste="家常", people=1, budget_per_day=80, days=1)
    plan_4 = generate_meal_plan(taste="家常", people=4, budget_per_day=80, days=1)
    cost_1 = plan_1["nutrition_summary"]["total_cost"]
    cost_4 = plan_4["nutrition_summary"]["total_cost"]
    assert cost_4 > cost_1 * 2, "4人成本应显著高于1人"
    print(f"  PASS: 1人成本={cost_1:.0f}, 4人成本={cost_4:.0f}")

    # 测试10: 热量范围验证
    print("\n[测试10] 热量范围验证")
    for taste in CUISINES.keys():
        for budget in [40, 80, 150]:
            plan = generate_meal_plan(taste=taste, people=2, budget_per_day=budget, days=3)
            avg_cal = plan["nutrition_summary"]["avg_daily_calories_per_person"]
            assert 1000 < avg_cal < 3000, f"{taste} 预算{budget} 热量异常: {avg_cal}"
    print("  PASS: 所有菜系和预算组合的热量均在合理范围")

    print("\n" + "=" * 40)
    print("所有自检测试通过!")
    return True


# ============================================================
# 主程序入口
# ============================================================

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="一周膳食规划 营养搭配 采购清单",
        epilog="示例: python main.py --taste 川味 --people 3 --budget 100 --format json"
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--taste", type=str, default=None, help="口味偏好 (家常/川味/清淡/粤式)")
    parser.add_argument("--people", type=int, default=None, help="用餐人数")
    parser.add_argument("--budget", type=float, default=None, help="每人每天预算(元)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="生成天数(默认7)")
    parser.add_argument("--format", type=str, choices=["text", "json", "table"], default="text",
                        help="输出格式 (默认text)")
    parser.add_argument("--input", type=str, default="", help="自然语言输入(可选)")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 正常模式
    try:
        # 从参数或自然语言输入中提取信息
        user_input = args.input or ""

        # 提取口味
        if args.taste:
            taste = args.taste
            if taste not in CUISINES:
                print(f"E005: 未知菜系 '{taste}'，可选: {list(CUISINES.keys())}")
                return 1
        else:
            taste, taste_conf = extract_taste(user_input)
            if taste_conf < 0.5:
                print(f"提示: 未能明确识别口味，使用默认 '{taste}' (置信度 {taste_conf:.0%})")

        # 提取人数
        if args.people:
            people = args.people
        else:
            people, people_conf = extract_people(user_input)
            if people_conf < 0.5:
                print(f"提示: 未能明确识别人数，使用默认 {people} 人")

        # 提取预算
        if args.budget:
            budget = args.budget
        else:
            budget, budget_conf = extract_budget(user_input)
            if budget_conf < 0.5:
                print(f"提示: 未能明确识别预算，使用默认 {budget} 元/人/天")

        # 校验
        err = validate_budget(budget)
        if err:
            print(f"{err}: 预算 {budget} 元/人/天超出支持范围 [{MIN_BUDGET}, {MAX_BUDGET}]")
            return 1

        err = validate_people(people)
        if err:
            print(f"{err}: 人数 {people} 不合法")
            return 1

        # 生成计划
        plan = generate_meal_plan(
            taste=taste,
            people=people,
            budget_per_day=budget,
            days=args.days,
        )

        # 输出
        output = format_output(plan, args.format)
        print(output)

        return 0

    except ValueError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"E010: 未知错误 - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
