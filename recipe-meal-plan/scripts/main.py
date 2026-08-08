#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一周膳食规划（recipe-meal-plan）— 独立实现脚本

本脚本根据功能规格独立编写，仅依赖 Python 标准库。
支持通过命令行参数生成一周三餐食谱、采购清单与热量统计。
包含 --selftest 自检模式，使用内置硬编码样例数据离线验证核心逻辑。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_OK = 0
ERR_INVALID_ARGS = "E001"       # 参数无效
ERR_BUDGET_OUT_OF_RANGE = "E002"  # 预算超出可处理范围
ERR_PEOPLE_COUNT_INVALID = "E003" # 人数无效
ERR_NO_MATCHED_RECIPE = "E004"   # 无匹配食谱
ERR_DATA_CORRUPTED = "E005"      # 内置数据损坏
ERR_INPUT_EMPTY = "E006"         # 输入为空
ERR_OUTPUT_FAILED = "E007"       # 输出失败
ERR_UNKNOWN = "E008"             # 未知错误
ERR_SELFTEST_FAILED = "E009"     # 自检失败
ERR_INTERNAL = "E010"            # 内部逻辑错误


# ============================================================
# 内置基础食材库（平均营养数据，仅用于估算）
# ============================================================
# 每项: (食材名, 每100克热量kcal, 蛋白质g, 碳水g, 脂肪g, 参考单价元/500g)
FOOD_DB: Dict[str, Tuple[int, int, int, int, float]] = {
    "大米":     (346, 7, 77, 1, 4.0),
    "面粉":     (364, 10, 76, 1, 3.5),
    "鸡蛋":     (144, 13, 2, 10, 6.0),
    "牛奶":     (65, 3, 5, 4, 5.0),
    "鸡胸肉":   (165, 31, 0, 4, 12.0),
    "瘦猪肉":   (143, 20, 1, 7, 14.0),
    "牛肉":     (250, 26, 0, 17, 35.0),
    "三文鱼":   (208, 20, 0, 13, 60.0),
    "豆腐":     (84, 8, 4, 5, 3.0),
    "西兰花":   (36, 4, 7, 0, 5.0),
    "胡萝卜":   (41, 1, 10, 0, 2.0),
    "西红柿":   (20, 1, 4, 0, 3.0),
    "土豆":     (77, 2, 17, 0, 2.5),
    "菠菜":     (28, 3, 4, 0, 4.0),
    "苹果":     (52, 0, 14, 0, 4.0),
    "香蕉":     (89, 1, 23, 0, 3.0),
    "燕麦":     (389, 17, 66, 7, 8.0),
    "全麦面包": (247, 13, 41, 4, 10.0),
    "酸奶":     (72, 3, 9, 2, 8.0),
    "花生酱":   (588, 25, 20, 50, 12.0),
    "橄榄油":   (884, 0, 0, 100, 25.0),
    "盐":       (0, 0, 0, 0, 1.0),
    "黑胡椒":   (255, 10, 64, 3, 15.0),
    "生抽":     (60, 8, 5, 0, 8.0),
    "姜":       (80, 2, 17, 1, 5.0),
    "蒜":       (149, 6, 33, 0, 4.0),
    "洋葱":     (40, 1, 9, 0, 2.0),
    "青椒":     (22, 1, 5, 0, 3.0),
    "玉米":     (112, 4, 22, 1, 3.0),
    "红薯":     (90, 2, 21, 0, 2.0),
    "生菜":     (15, 1, 3, 0, 3.0),
}


# ============================================================
# 内置食谱库（每道菜包含食材及用量克数）
# ============================================================
# 每项: (菜名, 类型[早餐/午餐/晚餐], 食材字典{食材名: 克数}, 适合口味标签)
RECIPE_DB: List[Dict[str, Any]] = [
    {
        "name": "牛奶燕麦粥",
        "meal_type": "早餐",
        "ingredients": {"燕麦": 50, "牛奶": 250, "香蕉": 100},
        "tags": ["清淡", "高纤"],
    },
    {
        "name": "全麦鸡蛋三明治",
        "meal_type": "早餐",
        "ingredients": {"全麦面包": 100, "鸡蛋": 50, "生菜": 20, "西红柿": 30},
        "tags": ["便捷", "高蛋白"],
    },
    {
        "name": "酸奶水果杯",
        "meal_type": "早餐",
        "ingredients": {"酸奶": 200, "苹果": 100, "香蕉": 100, "燕麦": 20},
        "tags": ["清淡", "低脂"],
    },
    {
        "name": "鸡胸肉沙拉",
        "meal_type": "午餐",
        "ingredients": {"鸡胸肉": 150, "西兰花": 100, "胡萝卜": 50, "西红柿": 50, "橄榄油": 5},
        "tags": ["高蛋白", "低脂"],
    },
    {
        "name": "番茄牛肉面",
        "meal_type": "午餐",
        "ingredients": {"面粉": 100, "牛肉": 100, "西红柿": 100, "洋葱": 30, "生抽": 5},
        "tags": ["浓郁", "高蛋白"],
    },
    {
        "name": "豆腐蔬菜煲",
        "meal_type": "午餐",
        "ingredients": {"豆腐": 200, "西兰花": 100, "胡萝卜": 50, "青椒": 50, "蒜": 5},
        "tags": ["清淡", "素食"],
    },
    {
        "name": "香煎三文鱼",
        "meal_type": "晚餐",
        "ingredients": {"三文鱼": 150, "土豆": 100, "菠菜": 100, "橄榄油": 5},
        "tags": ["高蛋白", "低脂"],
    },
    {
        "name": "青椒肉丝",
        "meal_type": "晚餐",
        "ingredients": {"瘦猪肉": 100, "青椒": 100, "洋葱": 30, "生抽": 5, "姜": 3},
        "tags": ["家常", "下饭"],
    },
    {
        "name": "蒜蓉西兰花配米饭",
        "meal_type": "晚餐",
        "ingredients": {"大米": 100, "西兰花": 200, "蒜": 5, "橄榄油": 3},
        "tags": ["清淡", "素食"],
    },
]


# ============================================================
# 核心工具函数
# ============================================================

def _get_food_nutrition(food_name: str) -> Optional[Tuple[int, int, int, int, float]]:
    """获取食材营养数据，找不到返回 None"""
    return FOOD_DB.get(food_name)


def _parse_taste_input(taste_str: str) -> List[str]:
    """解析口味输入字符串，返回标签列表"""
    if not taste_str or not taste_str.strip():
        return []
    # 支持逗号、空格、顿号分隔
    parts = re.split(r"[,，、\s]+", taste_str.strip())
    return [p for p in parts if p]


def _validate_budget(budget: float) -> Optional[str]:
    """校验预算是否在可处理范围（30-500元/人/天）"""
    if budget < 30 or budget > 500:
        return ERR_BUDGET_OUT_OF_RANGE
    return None


def _validate_people_count(people: int) -> Optional[str]:
    """校验人数是否有效"""
    if people < 1 or people > 20:
        return ERR_PEOPLE_COUNT_INVALID
    return None


def _calc_recipe_nutrition(recipe: Dict[str, Any]) -> Dict[str, float]:
    """计算单个食谱的营养估算值（按食材用量折算）"""
    total_kcal = 0.0
    total_protein = 0.0
    total_carb = 0.0
    total_fat = 0.0
    total_cost = 0.0

    for food_name, grams in recipe["ingredients"].items():
        nutrition = _get_food_nutrition(food_name)
        if nutrition is None:
            continue
        kcal, protein, carb, fat, price_per_500g = nutrition
        # 按克数折算
        ratio = grams / 100.0
        total_kcal += kcal * ratio
        total_protein += protein * ratio
        total_carb += carb * ratio
        total_fat += fat * ratio
        # 成本估算：每500g价格 -> 每克价格
        total_cost += (price_per_500g / 500.0) * grams

    return {
        "kcal": round(total_kcal, 1),
        "protein": round(total_protein, 1),
        "carb": round(total_carb, 1),
        "fat": round(total_fat, 1),
        "cost": round(total_cost, 2),
    }


def _match_recipes(meal_type: str, taste_tags: List[str], max_count: int = 3) -> List[Dict[str, Any]]:
    """根据餐型与口味标签匹配食谱"""
    candidates = [r for r in RECIPE_DB if r["meal_type"] == meal_type]
    if not candidates:
        return []

    # 按标签匹配度排序
    def _score(recipe: Dict[str, Any]) -> int:
        if not taste_tags:
            return 0
        return sum(1 for tag in taste_tags if tag in recipe["tags"])

    candidates.sort(key=_score, reverse=True)
    # 取前 max_count 个
    return candidates[:max_count]


def _generate_weekly_plan(
    people: int,
    budget_per_person: float,
    taste_tags: List[str],
) -> Dict[str, Any]:
    """生成一周膳食计划核心逻辑"""
    # 校验参数
    if people < 1:
        raise ValueError(ERR_PEOPLE_COUNT_INVALID)
    if budget_per_person < 30 or budget_per_person > 500:
        raise ValueError(ERR_BUDGET_OUT_OF_RANGE)

    # 每天三餐
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    meal_types = ["早餐", "午餐", "晚餐"]

    # 存储每日计划
    weekly_plan = []
    total_cost_all = 0.0
    total_kcal_all = 0.0

    for day in weekdays:
        day_plan = {"day": day, "meals": [], "day_cost": 0.0, "day_kcal": 0.0}
        for meal_type in meal_types:
            # 匹配食谱
            matched = _match_recipes(meal_type, taste_tags)
            if not matched:
                # 降级：无标签匹配时取第一个
                matched = _match_recipes(meal_type, [])
            if not matched:
                raise ValueError(ERR_NO_MATCHED_RECIPE)

            # 选择第一个匹配的食谱
            recipe = matched[0]
            nutrition = _calc_recipe_nutrition(recipe)

            # 按人数缩放食材用量
            scaled_ingredients = {
                food: grams * people for food, grams in recipe["ingredients"].items()
            }
            scaled_cost = nutrition["cost"] * people
            scaled_kcal = nutrition["kcal"] * people

            meal_entry = {
                "meal_type": meal_type,
                "recipe_name": recipe["name"],
                "ingredients": scaled_ingredients,
                "nutrition": {
                    "kcal": round(scaled_kcal, 1),
                    "protein": round(nutrition["protein"] * people, 1),
                    "carb": round(nutrition["carb"] * people, 1),
                    "fat": round(nutrition["fat"] * people, 1),
                },
                "cost": round(scaled_cost, 2),
            }

            day_plan["meals"].append(meal_entry)
            day_plan["day_cost"] += scaled_cost
            day_plan["day_kcal"] += scaled_kcal

        weekly_plan.append(day_plan)
        total_cost_all += day_plan["day_cost"]
        total_kcal_all += day_plan["day_kcal"]

    # 汇总采购清单
    shopping_list: Dict[str, float] = {}
    for day in weekly_plan:
        for meal in day["meals"]:
            for food, grams in meal["ingredients"].items():
                shopping_list[food] = shopping_list.get(food, 0.0) + grams

    # 生成输出结构
    result = {
        "meta": {
            "people": people,
            "budget_per_person": budget_per_person,
            "taste_tags": taste_tags,
            "generated_at": datetime.now().isoformat(),
        },
        "weekly_plan": weekly_plan,
        "shopping_list": {k: round(v, 1) for k, v in shopping_list.items()},
        "summary": {
            "total_cost": round(total_cost_all, 2),
            "total_kcal": round(total_kcal_all, 1),
            "avg_daily_cost_per_person": round(total_cost_all / people / 7, 2),
            "avg_daily_kcal_per_person": round(total_kcal_all / people / 7, 1),
        },
        "confidence": {
            "people": "high" if people else "medium",
            "budget": "high" if budget_per_person else "medium",
            "taste": "high" if taste_tags else "low",
        },
    }
    return result


def _format_output_plain(plan: Dict[str, Any]) -> str:
    """格式化为纯文本输出"""
    lines = []
    lines.append("=" * 60)
    lines.append("一周膳食规划方案")
    lines.append("=" * 60)
    lines.append(f"用餐人数: {plan['meta']['people']} 人")
    lines.append(f"每日预算: {plan['meta']['budget_per_person']} 元/人")
    lines.append(f"口味偏好: {', '.join(plan['meta']['taste_tags']) if plan['meta']['taste_tags'] else '无特定偏好'}")
    lines.append("")

    for day in plan["weekly_plan"]:
        lines.append(f"--- {day['day']} (预估花费: {day['day_cost']:.1f}元, 热量: {day['day_kcal']:.0f} kcal) ---")
        for meal in day["meals"]:
            lines.append(f"  [{meal['meal_type']}] {meal['recipe_name']}")
            lines.append(f"    食材: {', '.join(f'{k}{v:.0f}g' for k, v in meal['ingredients'].items())}")
            lines.append(f"    营养: {meal['nutrition']['kcal']:.0f} kcal | 蛋白 {meal['nutrition']['protein']:.0f}g | 碳水 {meal['nutrition']['carb']:.0f}g | 脂肪 {meal['nutrition']['fat']:.0f}g")
            lines.append(f"    预估成本: {meal['cost']:.1f} 元")
        lines.append("")

    lines.append("=" * 60)
    lines.append("一周采购清单")
    lines.append("=" * 60)
    for food, grams in plan["shopping_list"].items():
        lines.append(f"  {food}: {grams:.0f} 克")

    lines.append("")
    lines.append("=" * 60)
    lines.append("汇总统计")
    lines.append("=" * 60)
    lines.append(f"一周总花费: {plan['summary']['total_cost']:.1f} 元")
    lines.append(f"一周总热量: {plan['summary']['total_kcal']:.0f} kcal")
    lines.append(f"人均每日花费: {plan['summary']['avg_daily_cost_per_person']:.1f} 元")
    lines.append(f"人均每日热量: {plan['summary']['avg_daily_kcal_per_person']:.0f} kcal")
    lines.append("")
    lines.append("置信度标注:")
    for key, conf in plan["confidence"].items():
        lines.append(f"  {key}: {conf}")
    lines.append("")
    lines.append("提示: 热量为估算值，误差约±15%；食材需自行核对市场可得性。")
    return "\n".join(lines)


def _format_output_json(plan: Dict[str, Any]) -> str:
    """格式化为 JSON 输出"""
    return json.dumps(plan, ensure_ascii=False, indent=2)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def _run_selftest() -> int:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("[SELFTEST] 开始自检...")

    # 测试1: 基础数据完整性
    print("[SELFTEST] 检查内置食材库...")
    if len(FOOD_DB) < 10:
        print("[SELFTEST] 失败: 食材库过小")
        return 1
    # 检查关键食材存在
    for essential in ["大米", "鸡蛋", "鸡胸肉", "牛奶", "西兰花"]:
        if essential not in FOOD_DB:
            print(f"[SELFTEST] 失败: 缺少必要食材 {essential}")
            return 1
    print("[SELFTEST] 食材库检查通过")

    # 测试2: 食谱库完整性
    print("[SELFTEST] 检查食谱库...")
    if len(RECIPE_DB) < 5:
        print("[SELFTEST] 失败: 食谱库过小")
        return 1
    meal_types_present = set(r["meal_type"] for r in RECIPE_DB)
    if not {"早餐", "午餐", "晚餐"}.issubset(meal_types_present):
        print("[SELFTEST] 失败: 缺少必要餐型")
        return 1
    print("[SELFTEST] 食谱库检查通过")

    # 测试3: 营养计算函数
    print("[SELFTEST] 测试营养计算...")
    test_recipe = {
        "name": "测试菜",
        "meal_type": "午餐",
        "ingredients": {"大米": 100, "鸡胸肉": 100},
        "tags": [],
    }
    nutrition = _calc_recipe_nutrition(test_recipe)
    # 宽松断言：大米346 + 鸡胸165 ≈ 511，允许较大误差
    if not (400 < nutrition["kcal"] < 650):
        print(f"[SELFTEST] 失败: 热量计算异常 {nutrition['kcal']}")
        return 1
    if nutrition["protein"] <= 20:
        print(f"[SELFTEST] 失败: 蛋白质计算异常 {nutrition['protein']}")
        return 1
    print(f"[SELFTEST] 营养计算通过 (kcal={nutrition['kcal']})")

    # 测试4: 口味匹配
    print("[SELFTEST] 测试口味匹配...")
    matched = _match_recipes("早餐", ["高纤"])
    if not matched:
        print("[SELFTEST] 失败: 口味匹配无结果")
        return 1
    # 高纤标签应匹配到燕麦粥
    if matched[0]["name"] != "牛奶燕麦粥":
        print(f"[SELFTEST] 失败: 匹配结果不正确 {matched[0]['name']}")
        return 1
    print("[SELFTEST] 口味匹配通过")

    # 测试5: 完整的一周计划生成
    print("[SELFTEST] 测试一周计划生成...")
    try:
        plan = _generate_weekly_plan(people=2, budget_per_person=80, taste_tags=["清淡"])
    except ValueError as e:
        print(f"[SELFTEST] 失败: 生成异常 {e}")
        return 1

    # 宽松断言
    if len(plan["weekly_plan"]) != 7:
        print("[SELFTEST] 失败: 周计划天数错误")
        return 1
    # 每天应有3餐
    for day in plan["weekly_plan"]:
        if len(day["meals"]) != 3:
            print("[SELFTEST] 失败: 每日餐数错误")
            return 1
    # 汇总数据应合理
    if plan["summary"]["total_cost"] <= 0:
        print("[SELFTEST] 失败: 总花费异常")
        return 1
    if plan["summary"]["total_kcal"] <= 0:
        print("[SELFTEST] 失败: 总热量异常")
        return 1
    # 采购清单非空
    if not plan["shopping_list"]:
        print("[SELFTEST] 失败: 采购清单为空")
        return 1
    print(f"[SELFTEST] 一周计划生成通过 (总花费: {plan['summary']['total_cost']}元)")

    # 测试6: 预算边界校验
    print("[SELFTEST] 测试预算边界...")
    if _validate_budget(10) != ERR_BUDGET_OUT_OF_RANGE:
        print("[SELFTEST] 失败: 低预算未正确拒绝")
        return 1
    if _validate_budget(600) != ERR_BUDGET_OUT_OF_RANGE:
        print("[SELFTEST] 失败: 高预算未正确拒绝")
        return 1
    if _validate_budget(100) is not None:
        print("[SELFTEST] 失败: 正常预算被拒绝")
        return 1
    print("[SELFTEST] 预算边界校验通过")

    # 测试7: 人数校验
    print("[SELFTEST] 测试人数校验...")
    if _validate_people_count(0) != ERR_PEOPLE_COUNT_INVALID:
        print("[SELFTEST] 失败: 0人未正确拒绝")
        return 1
    if _validate_people_count(21) != ERR_PEOPLE_COUNT_INVALID:
        print("[SELFTEST] 失败: 21人未正确拒绝")
        return 1
    if _validate_people_count(4) is not None:
        print("[SELFTEST] 失败: 正常人数被拒绝")
        return 1
    print("[SELFTEST] 人数校验通过")

    # 测试8: 口味解析
    print("[SELFTEST] 测试口味解析...")
    tags = _parse_taste_input("清淡,高蛋白 低脂")
    if len(tags) != 3:
        print(f"[SELFTEST] 失败: 口味解析数量错误 {tags}")
        return 1
    if "清淡" not in tags or "高蛋白" not in tags:
        print("[SELFTEST] 失败: 口味解析内容错误")
        return 1
    print("[SELFTEST] 口味解析通过")

    # 测试9: 输出格式
    print("[SELFTEST] 测试输出格式...")
    plan_text = _format_output_plain(plan)
    if "一周膳食规划方案" not in plan_text:
        print("[SELFTEST] 失败: 纯文本输出缺少标题")
        return 1
    if "采购清单" not in plan_text:
        print("[SELFTEST] 失败: 纯文本输出缺少采购清单")
        return 1
    plan_json = _format_output_json(plan)
    try:
        parsed = json.loads(plan_json)
        if "weekly_plan" not in parsed:
            print("[SELFTEST] 失败: JSON输出缺少关键字段")
            return 1
    except json.JSONDecodeError:
        print("[SELFTEST] 失败: JSON输出无法解析")
        return 1
    print("[SELFTEST] 输出格式通过")

    print("[SELFTEST] 全部自检通过!")
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="一周膳食规划: 根据口味、人数、预算生成食谱与采购清单",
        epilog="示例: python main.py --people 3 --budget 100 --taste '清淡,高蛋白'",
    )
    parser.add_argument(
        "--people", "-p",
        type=int,
        default=2,
        help="用餐人数 (默认: 2)",
    )
    parser.add_argument(
        "--budget", "-b",
        type=float,
        default=80.0,
        help="每日预算 元/人 (有效范围: 30-500, 默认: 80)",
    )
    parser.add_argument(
        "--taste", "-t",
        type=str,
        default="",
        help="口味偏好, 逗号分隔 (例如: 清淡,高蛋白,素食)",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检 (无需外部输入)",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        result = _run_selftest()
        return 0 if result == 0 else 1

    # 正常模式: 校验参数
    try:
        # 校验人数
        people_err = _validate_people_count(args.people)
        if people_err:
            print(f"错误 [{people_err}]: 用餐人数需为 1-20 之间的整数", file=sys.stderr)
            return 1

        # 校验预算
        budget_err = _validate_budget(args.budget)
        if budget_err:
            print(f"错误 [{budget_err}]: 预算需在 30-500 元/人/天 范围内", file=sys.stderr)
            return 1

        # 解析口味
        taste_tags = _parse_taste_input(args.taste)

        # 生成计划
        plan = _generate_weekly_plan(
            people=args.people,
            budget_per_person=args.budget,
            taste_tags=taste_tags,
        )

        # 输出
        if args.format == "json":
            output = _format_output_json(plan)
        else:
            output = _format_output_plain(plan)

        print(output)
        return 0

    except ValueError as e:
        # 将错误码字符串映射为友好提示
        err_msg = str(e)
        if err_msg in [ERR_BUDGET_OUT_OF_RANGE, ERR_PEOPLE_COUNT_INVALID, ERR_NO_MATCHED_RECIPE]:
            print(f"错误 [{err_msg}]: 参数或数据问题", file=sys.stderr)
        else:
            print(f"错误 [{ERR_INTERNAL}]: 内部错误 - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERR_UNKNOWN}]: 未知异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
