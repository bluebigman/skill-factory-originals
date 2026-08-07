#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一周膳食规划 Skill - 独立实现脚本
功能：根据口味、人数、预算生成一周三餐食谱与采购清单，附热量统计。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_INVALID_ARGS = "E001"       # 参数无效
ERR_BUDGET_TOO_LOW = "E002"     # 预算过低
ERR_BUDGET_TOO_HIGH = "E003"    # 预算过高
ERR_PEOPLE_COUNT = "E004"       # 人数无效
ERR_TASTE_UNKNOWN = "E005"      # 口味无法识别
ERR_INTERNAL = "E006"           # 内部错误
ERR_JSON_OUTPUT = "E007"        # JSON输出失败
ERR_SELF_TEST = "E008"          # 自检失败
ERR_FILE_ACCESS = "E009"        # 文件访问错误
ERR_UNEXPECTED = "E010"         # 未预期错误


# ============================================================
# 内置数据（食材库、口味映射、菜谱模板）
# ============================================================

# 食材营养与价格库（每100克）
# 字段：热量(kcal), 蛋白质(g), 脂肪(g), 碳水(g), 价格(元/100g)
FOOD_DB: Dict[str, Dict[str, float]] = {
    # 主食类
    "大米":   {"kcal": 116, "protein": 2.6, "fat": 0.3, "carb": 25.9, "price": 0.5},
    "面条":   {"kcal": 137, "protein": 4.5, "fat": 0.9, "carb": 27.4, "price": 0.8},
    "全麦面包": {"kcal": 246, "protein": 10.0, "fat": 3.0, "carb": 45.0, "price": 2.5},
    "燕麦":   {"kcal": 367, "protein": 15.0, "fat": 6.0, "carb": 60.0, "price": 1.5},
    "土豆":   {"kcal": 77,  "protein": 2.0, "fat": 0.1, "carb": 17.0, "price": 0.4},
    # 蛋白质类
    "鸡蛋":   {"kcal": 144, "protein": 13.3, "fat": 8.8, "carb": 2.8,  "price": 1.0},
    "鸡胸肉": {"kcal": 133, "protein": 23.0, "fat": 2.5, "carb": 0.0,  "price": 1.8},
    "牛肉":   {"kcal": 125, "protein": 20.0, "fat": 4.5, "carb": 0.0,  "price": 4.5},
    "猪肉":   {"kcal": 143, "protein": 20.0, "fat": 7.0, "carb": 0.0,  "price": 2.8},
    "三文鱼": {"kcal": 208, "protein": 20.0, "fat": 13.0, "carb": 0.0, "price": 9.0},
    "豆腐":   {"kcal": 82,  "protein": 8.0, "fat": 4.0, "carb": 3.0,  "price": 0.8},
    "牛奶":   {"kcal": 54,  "protein": 3.0, "fat": 3.2, "carb": 3.4,  "price": 1.2},
    # 蔬菜类
    "西兰花": {"kcal": 34,  "protein": 2.8, "fat": 0.4, "carb": 6.6,  "price": 1.5},
    "胡萝卜": {"kcal": 41,  "protein": 0.9, "fat": 0.2, "carb": 9.6,  "price": 0.6},
    "菠菜":   {"kcal": 28,  "protein": 2.6, "fat": 0.3, "carb": 4.5,  "price": 1.2},
    "西红柿": {"kcal": 18,  "protein": 0.9, "fat": 0.2, "carb": 3.9,  "price": 0.8},
    "黄瓜":   {"kcal": 15,  "protein": 0.7, "fat": 0.1, "carb": 3.6,  "price": 0.5},
    "生菜":   {"kcal": 15,  "protein": 1.4, "fat": 0.2, "carb": 2.9,  "price": 0.7},
    # 水果类
    "苹果":   {"kcal": 52,  "protein": 0.3, "fat": 0.2, "carb": 13.8, "price": 1.0},
    "香蕉":   {"kcal": 89,  "protein": 1.1, "fat": 0.3, "carb": 22.8, "price": 1.2},
    "橙子":   {"kcal": 47,  "protein": 0.9, "fat": 0.1, "carb": 11.8, "price": 1.5},
    # 调味品（少量不计入主要营养计算）
    "橄榄油": {"kcal": 884, "protein": 0.0, "fat": 100.0, "carb": 0.0, "price": 6.0},
    "盐":     {"kcal": 0,   "protein": 0.0, "fat": 0.0,   "carb": 0.0, "price": 0.2},
    "酱油":   {"kcal": 53,  "protein": 5.0, "fat": 0.0,   "carb": 5.0, "price": 1.0},
}


# 口味偏好 -> 菜系特征（影响食材选择权重）
TASTE_PROFILES: Dict[str, Dict[str, float]] = {
    "清淡": {"油": 0.5, "辣": 0.0, "重口": 0.0, "甜": 0.2},
    "家常": {"油": 1.0, "辣": 0.3, "重口": 0.5, "甜": 0.3},
    "川湘": {"油": 1.2, "辣": 2.0, "重口": 1.5, "甜": 0.1},
    "粤式": {"油": 0.7, "辣": 0.0, "重口": 0.2, "甜": 0.4},
    "西式": {"油": 1.0, "辣": 0.2, "重口": 0.8, "甜": 0.5},
    "日式": {"油": 0.6, "辣": 0.1, "重口": 0.3, "甜": 0.3},
    "素食": {"油": 0.8, "辣": 0.2, "重口": 0.3, "甜": 0.2},
}

# 口味名称映射（包含常见变体）
TASTE_ALIASES: Dict[str, str] = {
    "清淡": "清淡",
    "清谈": "清淡",
    "家常": "家常",
    "家常菜": "家常",
    "川菜": "川湘",
    "川湘": "川湘",
    "湘菜": "川湘",
    "辣": "川湘",
    "麻辣": "川湘",
    "粤菜": "粤式",
    "粤式": "粤式",
    "广东菜": "粤式",
    "西餐": "西式",
    "西式": "西式",
    "日料": "日式",
    "日式": "日式",
    "日本菜": "日式",
    "素菜": "素食",
    "素食": "素食",
}

# 默认口味
DEFAULT_TASTE = "家常"

# 一周七天
WEEK_DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 三餐类型
MEAL_TYPES = ["早餐", "午餐", "晚餐"]


# ============================================================
# 核心数据结构
# ============================================================

class MealPlanError(Exception):
    """膳食规划业务异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 参数解析与校验
# ============================================================

def parse_user_input(text: str) -> Dict[str, Any]:
    """
    从用户自由文本中提取关键参数。
    支持：口味、人数、预算、忌口。
    返回字典包含：taste, people, budget, avoid。
    """
    result: Dict[str, Any] = {
        "taste": None,
        "people": None,
        "budget": None,
        "avoid": [],
    }
    if not text:
        return result

    # 提取人数（如：3人、4个人）
    people_match = re.search(r"(\d+)\s*(人|个人|口)", text)
    if people_match:
        result["people"] = int(people_match.group(1))

    # 提取预算（如：100元、200块）
    budget_match = re.search(r"(\d+)\s*(元|块|预算)", text)
    if budget_match:
        result["budget"] = float(budget_match.group(1))

    # 提取口味（使用别名映射，支持更多表达方式）
    for alias, taste in TASTE_ALIASES.items():
        if alias in text:
            result["taste"] = taste
            break
    
    # 如果未找到，尝试直接匹配口味名称
    if result["taste"] is None:
        for taste in TASTE_PROFILES:
            if taste in text:
                result["taste"] = taste
                break

    # 提取忌口（简单关键词）
    avoid_keywords = ["不吃", "忌口", "过敏"]
    for kw in avoid_keywords:
        if kw in text:
            # 提取忌口内容（简化处理）
            idx = text.find(kw)
            if idx >= 0:
                avoid_text = text[idx+len(kw):idx+len(kw)+5].strip()
                if avoid_text:
                    result["avoid"].append(avoid_text)

    return result


def validate_params(people: int, budget: float) -> None:
    """校验人数与预算合法性"""
    if people <= 0 or people > 20:
        raise MealPlanError(ERR_PEOPLE_COUNT, f"人数无效: {people}（支持1-20人）")
    if budget < 30 * people * 7:
        raise MealPlanError(ERR_BUDGET_TOO_LOW, f"预算过低: {budget}元/周（最低需约{30*people*7}元）")
    if budget > 500 * people * 7:
        raise MealPlanError(ERR_BUDGET_TOO_HIGH, f"预算过高: {budget}元/周（最高建议{500*people*7}元）")


# ============================================================
# 食谱生成逻辑
# ============================================================

def select_food_by_taste(taste: str, category: str, count: int = 1) -> List[str]:
    """
    根据口味偏好从食材库中选择食材。
    category: 主食/蛋白质/蔬菜/水果
    """
    if taste not in TASTE_PROFILES:
        taste = DEFAULT_TASTE

    # 根据类别筛选食材
    category_map = {
        "主食": ["大米", "面条", "全麦面包", "燕麦", "土豆"],
        "蛋白质": ["鸡蛋", "鸡胸肉", "牛肉", "猪肉", "三文鱼", "豆腐", "牛奶"],
        "蔬菜": ["西兰花", "胡萝卜", "菠菜", "西红柿", "黄瓜", "生菜"],
        "水果": ["苹果", "香蕉", "橙子"],
    }

    candidates = category_map.get(category, [])
    if not candidates:
        return []

    # 根据口味调整选择（简单加权随机，保证确定性）
    profile = TASTE_PROFILES[taste]
    # 口味越重越倾向选择红肉/重口味食材
    heavy_score = profile.get("重口", 0.5)
    spicy_score = profile.get("辣", 0.0)

    # 评分函数：分数越高越可能被选中
    def score_food(food: str) -> float:
        base = 1.0
        if category == "蛋白质":
            if food in ["牛肉", "猪肉"]:
                base += heavy_score * 0.8
            if food in ["鸡胸肉", "豆腐"]:
                base += (1.0 - heavy_score) * 0.5
            if food == "三文鱼":
                base += 0.3
        if category == "蔬菜":
            if food in ["西红柿", "黄瓜", "生菜"]:
                base += (1.0 - heavy_score) * 0.3
            if spicy_score > 1.0 and food in ["菠菜", "西兰花"]:
                base += 0.2
        return base

    # 按评分排序，取前N个（确定性）
    scored = sorted(candidates, key=score_food, reverse=True)
    return scored[:count]


def generate_recipe(taste: str, day: str, meal: str) -> Dict[str, Any]:
    """
    生成一餐的食谱。
    返回：{主食材, 辅食材, 做法, 热量, 蛋白质, 脂肪, 碳水, 成本}
    """
    # 根据餐次选择食材组合
    if meal == "早餐":
        main_food = select_food_by_taste(taste, "主食", 1)[0]
        protein = select_food_by_taste(taste, "蛋白质", 1)[0]
        fruit = select_food_by_taste(taste, "水果", 1)[0]
        foods = [main_food, protein, fruit]
        portions = [50, 50, 100]  # 克
        method = f"{main_food}搭配{protein}，配{fruit}，简单烹饪"
    elif meal == "午餐":
        main_food = select_food_by_taste(taste, "主食", 1)[0]
        protein = select_food_by_taste(taste, "蛋白质", 1)[0]
        veg1 = select_food_by_taste(taste, "蔬菜", 1)[0]
        veg2 = select_food_by_taste(taste, "蔬菜", 1)[0]
        foods = [main_food, protein, veg1, veg2]
        portions = [80, 80, 100, 100]
        method = f"{main_food}配{protein}，炒{veg1}和{veg2}，营养均衡"
    else:  # 晚餐
        main_food = select_food_by_taste(taste, "主食", 1)[0]
        protein = select_food_by_taste(taste, "蛋白质", 1)[0]
        veg = select_food_by_taste(taste, "蔬菜", 1)[0]
        foods = [main_food, protein, veg]
        portions = [60, 70, 120]
        method = f"{main_food}配{protein}，清炒{veg}，清淡为主"

    # 计算营养与成本
    total_kcal = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carb = 0.0
    total_cost = 0.0

    for food, portion in zip(foods, portions):
        if food in FOOD_DB:
            info = FOOD_DB[food]
            factor = portion / 100.0
            total_kcal += info["kcal"] * factor
            total_protein += info["protein"] * factor
            total_fat += info["fat"] * factor
            total_carb += info["carb"] * factor
            total_cost += info["price"] * factor

    return {
        "day": day,
        "meal": meal,
        "foods": foods,
        "method": method,
        "kcal": round(total_kcal, 1),
        "protein": round(total_protein, 1),
        "fat": round(total_fat, 1),
        "carb": round(total_carb, 1),
        "cost": round(total_cost, 2),
    }


def generate_week_plan(taste: str, people: int, budget: float) -> Dict[str, Any]:
    """
    生成一周膳食计划。
    返回完整计划字典。
    """
    # 校验参数
    validate_params(people, budget)

    # 初始化计划
    plan: Dict[str, Any] = {
        "meta": {
            "taste": taste,
            "people": people,
            "budget": budget,
            "days": 7,
        },
        "meals": [],
        "summary": {
            "total_kcal": 0.0,
            "avg_kcal_per_day": 0.0,
            "total_cost": 0.0,
            "avg_cost_per_day": 0.0,
        },
        "shopping_list": {},
    }

    # 生成每天每餐
    for day in WEEK_DAYS:
        for meal in MEAL_TYPES:
            recipe = generate_recipe(taste, day, meal)
            # 按人数调整份量和成本
            recipe["people"] = people
            recipe["cost"] = round(recipe["cost"] * people, 2)
            recipe["kcal"] = round(recipe["kcal"] * people, 1)
            recipe["protein"] = round(recipe["protein"] * people, 1)
            recipe["fat"] = round(recipe["fat"] * people, 1)
            recipe["carb"] = round(recipe["carb"] * people, 1)
            plan["meals"].append(recipe)

            # 汇总
            plan["summary"]["total_kcal"] += recipe["kcal"]
            plan["summary"]["total_cost"] += recipe["cost"]

            # 收集采购食材
            for food in recipe["foods"]:
                if food not in plan["shopping_list"]:
                    plan["shopping_list"][food] = 0
                plan["shopping_list"][food] += 1

    # 计算平均值
    total_meals = len(plan["meals"])
    plan["summary"]["avg_kcal_per_day"] = round(plan["summary"]["total_kcal"] / 7, 1)
    plan["summary"]["avg_cost_per_day"] = round(plan["summary"]["total_cost"] / 7, 2)

    # 预算检查（生成后调整）
    if plan["summary"]["total_cost"] > budget:
        # 预算超支，尝试替换部分高价食材（简化处理：仅提示）
        plan["meta"]["budget_warning"] = f"预算超支，实际约{plan['summary']['total_cost']}元"

    return plan


# ============================================================
# 输出格式化
# ============================================================

def format_table(plan: Dict[str, Any]) -> str:
    """表格格式输出"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"一周膳食规划（口味：{plan['meta']['taste']}，人数：{plan['meta']['people']}人）")
    lines.append("=" * 70)

    for day in WEEK_DAYS:
        lines.append(f"\n【{day}】")
        day_meals = [m for m in plan["meals"] if m["day"] == day]
        for meal in day_meals:
            lines.append(f"  {meal['meal']}: {'、'.join(meal['foods'])}")
            lines.append(f"    做法: {meal['method']}")
            lines.append(f"    热量: {meal['kcal']} kcal | 蛋白质: {meal['protein']}g | 成本: {meal['cost']}元")

    lines.append("\n" + "=" * 70)
    lines.append("采购清单：")
    for food, count in sorted(plan["shopping_list"].items()):
        lines.append(f"  - {food} x {count}")

    lines.append("\n" + "=" * 70)
    lines.append(f"汇总：总热量 {plan['summary']['total_kcal']} kcal | 日均 {plan['summary']['avg_kcal_per_day']} kcal")
    lines.append(f"总成本 {plan['summary']['total_cost']} 元 | 日均 {plan['summary']['avg_cost_per_day']} 元")
    if "budget_warning" in plan["meta"]:
        lines.append(f"⚠️ {plan['meta']['budget_warning']}")

    return "\n".join(lines)


def format_list(plan: Dict[str, Any]) -> str:
    """清单格式输出"""
    lines = []
    lines.append(f"一周膳食计划（{plan['meta']['people']}人，{plan['meta']['taste']}口味）")
    lines.append("\n=== 每日三餐 ===")
    for day in WEEK_DAYS:
        lines.append(f"\n{day}:")
        day_meals = [m for m in plan["meals"] if m["day"] == day]
        for meal in day_meals:
            lines.append(f"  {meal['meal']}: {'、'.join(meal['foods'])}（{meal['kcal']}kcal）")

    lines.append("\n=== 采购清单 ===")
    for food, count in sorted(plan["shopping_list"].items()):
        lines.append(f"  {food}: {count}份")

    lines.append(f"\n=== 汇总 ===")
    lines.append(f"  总热量: {plan['summary']['total_kcal']} kcal")
    lines.append(f"  总成本: {plan['summary']['total_cost']} 元")
    return "\n".join(lines)


def format_json(plan: Dict[str, Any]) -> str:
    """JSON格式输出"""
    try:
        return json.dumps(plan, ensure_ascii=False, indent=2)
    except Exception as e:
        raise MealPlanError(ERR_JSON_OUTPUT, f"JSON序列化失败: {e}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言。
    """
    print("开始自检...")

    # 测试1：参数解析
    try:
        parsed = parse_user_input("我想吃川菜，3个人，预算500元")
        assert parsed["taste"] == "川湘", f"口味解析失败: {parsed['taste']}"
        assert parsed["people"] == 3, f"人数解析失败: {parsed['people']}"
        assert parsed["budget"] == 500, f"预算解析失败: {parsed['budget']}"
        print("  [PASS] 参数解析")
    except AssertionError as e:
        print(f"  [FAIL] 参数解析: {e}")
        return False

    # 测试2：预算校验
    try:
        validate_params(2, 100)
        print("  [FAIL] 预算过低校验未生效")
        return False
    except MealPlanError as e:
        assert e.code == ERR_BUDGET_TOO_LOW, f"错误码错误: {e.code}"
        print("  [PASS] 预算过低校验")

    try:
        validate_params(2, 10000)
        print("  [FAIL] 预算过高校验未生效")
        return False
    except MealPlanError as e:
        assert e.code == ERR_BUDGET_TOO_HIGH, f"错误码错误: {e.code}"
        print("  [PASS] 预算过高校验")

    # 测试3：食谱生成
    try:
        recipe = generate_recipe("家常", "周一", "早餐")
        assert len(recipe["foods"]) >= 2, "食谱食材不足"
        assert recipe["kcal"] > 0, "热量应为正数"
        assert recipe["protein"] > 0, "蛋白质应为正数"
        assert recipe["cost"] > 0, "成本应为正数"
        print("  [PASS] 单餐食谱生成")
    except Exception as e:
        print(f"  [FAIL] 单餐食谱生成: {e}")
        return False

    # 测试4：一周计划生成
    try:
        plan = generate_week_plan("家常", 2, 500)
        assert len(plan["meals"]) == 21, f"应生成21餐，实际{len(plan['meals'])}"
        assert len(plan["shopping_list"]) > 0, "采购清单为空"
        assert plan["summary"]["total_kcal"] > 0, "总热量应为正数"
        assert plan["summary"]["total_cost"] > 0, "总成本应为正数"
        # 宽松阈值：日均热量在合理范围（每人每天约1500-3000kcal）
        avg_per_person = plan["summary"]["avg_kcal_per_day"] / 2
        assert 1000 < avg_per_person < 4000, f"日均热量异常: {avg_per_person}"
        # 日均成本在合理范围
        assert 30 < plan["summary"]["avg_cost_per_day"] < 200, f"日均成本异常: {plan['summary']['avg_cost_per_day']}"
        print("  [PASS] 一周计划生成")
    except AssertionError as e:
        print(f"  [FAIL] 一周计划生成: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 一周计划生成异常: {e}")
        return False

    # 测试5：输出格式
    try:
        plan = generate_week_plan("粤式", 3, 800)
        table_text = format_table(plan)
        assert "周一" in table_text, "表格输出缺少日期"
        assert "采购清单" in table_text, "表格输出缺少采购清单"

        list_text = format_list(plan)
        assert "采购清单" in list_text, "清单输出缺少采购清单"

        json_text = format_json(plan)
        json_data = json.loads(json_text)
        assert "meals" in json_data, "JSON输出缺少meals字段"
        print("  [PASS] 输出格式")
    except AssertionError as e:
        print(f"  [FAIL] 输出格式: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 输出格式异常: {e}")
        return False

    # 测试6：边界输入
    try:
        # 极端口味使用默认
        recipe = generate_recipe("不存在口味", "周二", "午餐")
        assert recipe["kcal"] > 0, "未知口味应使用默认值"
        print("  [PASS] 边界输入处理")
    except Exception as e:
        print(f"  [FAIL] 边界输入处理: {e}")
        return False

    print("\n所有自检通过 ✅")
    return True


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="一周膳食规划 Skill - 生成一周三餐食谱与采购清单",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python main.py --taste 家常 --people 3 --budget 500\n"
               "  python main.py --text \"我想吃川菜，2个人，预算300元\"\n"
               "  python main.py --selftest\n"
    )
    parser.add_argument("--taste", type=str, default=None, help="口味偏好（清淡/家常/川湘/粤式/西式/日式/素食）")
    parser.add_argument("--people", type=int, default=None, help="用餐人数")
    parser.add_argument("--budget", type=float, default=None, help="预算（元/周）")
    parser.add_argument("--text", type=str, default=None, help="自然语言输入，自动解析参数")
    parser.add_argument("--format", type=str, choices=["table", "list", "json"], default="table",
                        help="输出格式（默认table）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 正常模式
    try:
        # 参数来源：优先使用显式参数，其次解析自然语言
        taste = args.taste
        people = args.people
        budget = args.budget

        if args.text:
            parsed = parse_user_input(args.text)
            if taste is None:
                taste = parsed["taste"]
            if people is None:
                people = parsed["people"]
            if budget is None:
                budget = parsed["budget"]

        # 默认值
        if taste is None:
            taste = DEFAULT_TASTE
        if people is None:
            people = 2
        if budget is None:
            budget = 200.0

        # 校验并生成
        plan = generate_week_plan(taste, people, budget)

        # 输出
        if args.format == "json":
            output = format_json(plan)
        elif args.format == "list":
            output = format_list(plan)
        else:
            output = format_table(plan)

        print(output)
        return 0

    except MealPlanError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误 [{ERR_UNEXPECTED}]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
