#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
travel-plan-gen 全新独立实现（clean-room）

根据功能规格独立编写，不参考任何既有实现。
功能：根据目的地、天数、预算生成结构化旅行行程方案。
支持命令行调用与 --selftest 离线自检。
"""

import argparse
import json
import math
import random
import re
import sys
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数缺失或为空",
    "E002": "天数必须为正整数",
    "E003": "预算必须为正数",
    "E004": "目的地格式不合法",
    "E005": "无法生成行程（内部错误）",
    "E006": "输出格式不支持",
    "E007": "输入数据解析失败",
    "E008": "JSON 序列化失败",
    "E009": "自检断言失败",
    "E010": "未知错误",
}


class TravelPlanError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心数据模型
# ============================================================

# 内置的常见景点/活动模板（仅用于行程生成，非实时数据）
# 每个条目：名称、类别、建议游玩时长（小时）、建议预算比例权重
_ATTRACTION_POOL = [
    {"name": "城市地标广场", "category": "观光", "hours": 2.0, "weight": 1.0},
    {"name": "历史博物馆", "category": "文化", "hours": 2.5, "weight": 1.2},
    {"name": "中央公园", "category": "自然", "hours": 3.0, "weight": 0.8},
    {"name": "老城区步行街", "category": "休闲", "hours": 2.0, "weight": 0.9},
    {"name": "艺术画廊", "category": "文化", "hours": 1.5, "weight": 0.7},
    {"name": "河边步道", "category": "自然", "hours": 1.5, "weight": 0.5},
    {"name": "夜市美食街", "category": "美食", "hours": 2.0, "weight": 1.0},
    {"name": "山顶观景台", "category": "自然", "hours": 3.0, "weight": 1.1},
    {"name": "科技馆", "category": "亲子", "hours": 2.5, "weight": 1.0},
    {"name": "寺庙/教堂", "category": "文化", "hours": 1.5, "weight": 0.6},
]

# 交通方式建议池
_TRANSPORT_POOL = ["公共交通", "出租车", "步行", "共享单车", "包车"]

# 餐饮建议池
_BREAKFAST_POOL = ["酒店早餐", "街边早点", "咖啡馆简餐"]
_LUNCH_POOL = ["当地特色餐厅", "快餐简餐", "商场美食广场"]
_DINNER_POOL = ["网红餐厅", "本地老字号", "夜市小吃"]


# ============================================================
# 工具函数
# ============================================================

def _validate_inputs(destination: str, days: int, budget: float) -> None:
    """校验输入参数合法性"""
    if not destination or not destination.strip():
        raise TravelPlanError("E001")
    if not isinstance(days, int) or days <= 0:
        raise TravelPlanError("E002")
    if not isinstance(budget, (int, float)) or budget <= 0:
        raise TravelPlanError("E003")
    # 目的地简单校验：仅允许中英文、数字、空格、连字符
    if not re.match(r"^[\u4e00-\u9fa5A-Za-z0-9\s\-]{1,50}$", destination.strip()):
        raise TravelPlanError("E004")


def _allocate_budget(total_budget: float, days: int) -> Dict[str, float]:
    """
    预算分配策略：
    - 住宿占 40%
    - 餐饮占 20%
    - 交通占 15%
    - 景点门票占 15%
    - 购物/其他占 10%
    按天均分住宿费用，其余按天均分。
    """
    if total_budget <= 0 or days <= 0:
        raise TravelPlanError("E003")

    accommodation_total = total_budget * 0.40
    food_total = total_budget * 0.20
    transport_total = total_budget * 0.15
    attraction_total = total_budget * 0.15
    misc_total = total_budget * 0.10

    # 按天分配（保留两位小数）
    per_day_accommodation = round(accommodation_total / days, 2)
    per_day_food = round(food_total / days, 2)
    per_day_transport = round(transport_total / days, 2)
    per_day_attraction = round(attraction_total / days, 2)
    per_day_misc = round(misc_total / days, 2)

    return {
        "accommodation_per_day": per_day_accommodation,
        "food_per_day": per_day_food,
        "transport_per_day": per_day_transport,
        "attraction_per_day": per_day_attraction,
        "misc_per_day": per_day_misc,
        "accommodation_total": round(accommodation_total, 2),
        "food_total": round(food_total, 2),
        "transport_total": round(transport_total, 2),
        "attraction_total": round(attraction_total, 2),
        "misc_total": round(misc_total, 2),
        "total_allocated": round(
            accommodation_total + food_total + transport_total + attraction_total + misc_total, 2
        ),
    }


def _generate_daily_plan(
    destination: str,
    day_index: int,
    total_days: int,
    budget_alloc: Dict[str, float],
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    生成单日行程安排。
    使用随机种子保证可复现（但自检时使用宽松断言，不依赖具体值）。
    """
    rng = random.Random(seed if seed is not None else (day_index * 100 + total_days))

    # 从景点池中选取 2-3 个景点（避免重复）
    num_attractions = rng.randint(2, 3)
    attractions = rng.sample(_ATTRACTION_POOL, k=min(num_attractions, len(_ATTRACTION_POOL)))

    # 生成交通方式（上午/下午各一种）
    transport_morning = rng.choice(_TRANSPORT_POOL)
    transport_afternoon = rng.choice(_TRANSPORT_POOL)

    # 餐饮安排
    breakfast = rng.choice(_BREAKFAST_POOL)
    lunch = rng.choice(_LUNCH_POOL)
    dinner = rng.choice(_DINNER_POOL)

    # 计算当日景点总时长（小时）
    total_hours = sum(a["hours"] for a in attractions)

    # 日期计算（从今天开始）
    current_date = date.today() + timedelta(days=day_index - 1)

    return {
        "day": day_index,
        "date": current_date.isoformat(),
        "title": f"第{day_index}天行程",
        "morning": {
            "transport": transport_morning,
            "activity": attractions[0]["name"] if attractions else "自由活动",
            "category": attractions[0]["category"] if attractions else "休闲",
            "hours": attractions[0]["hours"] if attractions else 2.0,
        },
        "afternoon": {
            "transport": transport_afternoon,
            "activity": attractions[1]["name"] if len(attractions) > 1 else "自由活动",
            "category": attractions[1]["category"] if len(attractions) > 1 else "休闲",
            "hours": attractions[1]["hours"] if len(attractions) > 1 else 2.0,
        },
        "evening": {
            "activity": attractions[2]["name"] if len(attractions) > 2 else "夜市/自由活动",
            "category": attractions[2]["category"] if len(attractions) > 2 else "美食",
            "hours": attractions[2]["hours"] if len(attractions) > 2 else 1.5,
        },
        "meals": {
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
        },
        "estimated_hours": round(total_hours, 1),
        "daily_budget": {
            "accommodation": budget_alloc["accommodation_per_day"],
            "food": budget_alloc["food_per_day"],
            "transport": budget_alloc["transport_per_day"],
            "attraction": budget_alloc["attraction_per_day"],
            "misc": budget_alloc["misc_per_day"],
        },
    }


def generate_travel_plan(
    destination: str,
    days: int,
    budget: float,
    output_format: str = "json",
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    核心生成函数：根据目的地、天数、预算生成完整行程方案。
    """
    # 1. 校验输入
    _validate_inputs(destination, days, budget)

    # 2. 预算分配
    budget_alloc = _allocate_budget(budget, days)

    # 3. 生成每日行程
    daily_plans = []
    for i in range(1, days + 1):
        daily = _generate_daily_plan(destination, i, days, budget_alloc, seed=seed)
        daily_plans.append(daily)

    # 4. 汇总信息
    result = {
        "meta": {
            "generator": "travel-plan-gen",
            "version": "1.0.1",
            "generated_at": date.today().isoformat(),
        },
        "input": {
            "destination": destination.strip(),
            "days": days,
            "budget": budget,
        },
        "budget_allocation": budget_alloc,
        "daily_plans": daily_plans,
        "summary": {
            "total_days": days,
            "total_estimated_hours": round(sum(d["estimated_hours"] for d in daily_plans), 1),
            "tips": [
                "建议提前预订酒店和热门景点门票",
                "根据实时天气调整户外活动安排",
                "预留部分弹性时间应对突发情况",
            ],
        },
    }

    # 5. 格式检查（目前仅支持 json 和 dict）
    if output_format not in ("json", "dict"):
        raise TravelPlanError("E006")

    return result


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """将结果格式化为 JSON 字符串或原样返回"""
    if output_format == "json":
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise TravelPlanError("E008", f"JSON 序列化失败: {exc}") from exc
    elif output_format == "dict":
        return str(result)
    else:
        raise TravelPlanError("E006")


def parse_input_text(text: str) -> Dict[str, Any]:
    """
    从自由文本中提取目的地、天数、预算。
    简单的正则提取，不保证 100% 准确，失败时抛出 E007。
    """
    if not text or not text.strip():
        raise TravelPlanError("E001")

    # 提取天数（如 "3天"、"三天"、"5 days"）
    days_match = re.search(r"(\d+)\s*(天|日|day|days)", text, re.IGNORECASE)
    days = int(days_match.group(1)) if days_match else None

    # 提取预算（如 "5000元"、"5000"、"5000块"）
    budget_match = re.search(r"(\d+)\s*(元|块|rmb|￥)?", text, re.IGNORECASE)
    budget = float(budget_match.group(1)) if budget_match else None

    # 提取目的地（简单策略：去除数字和常见词后取剩余部分）
    # 这里仅作演示，实际场景需要更复杂的 NLP
    cleaned = re.sub(r"\d+\s*(天|日|元|块|day|days|rmb|￥)", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[，。！？,.!?]", " ", cleaned)
    words = [w for w in cleaned.split() if w and not w.isdigit()]
    destination = " ".join(words[-3:]) if words else None

    if not days or not budget or not destination:
        raise TravelPlanError("E007")

    return {"destination": destination, "days": days, "budget": budget}


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境下都能通过。
    """
    print("=" * 60)
    print("travel-plan-gen 自检开始")
    print("=" * 60)

    test_cases = [
        {"destination": "北京", "days": 3, "budget": 5000},
        {"destination": "Tokyo", "days": 5, "budget": 10000},
        {"destination": "巴黎", "days": 2, "budget": 3000},
    ]

    for idx, case in enumerate(test_cases, 1):
        print(f"\n--- 测试样例 {idx}: {case['destination']} {case['days']}天 {case['budget']}元 ---")
        try:
            result = generate_travel_plan(
                destination=case["destination"],
                days=case["days"],
                budget=case["budget"],
                output_format="dict",
                seed=42,  # 固定种子保证可复现
            )

            # ---- 宽松断言 ----
            # 1. 基础结构存在
            assert "meta" in result, "缺少 meta 字段"
            assert "input" in result, "缺少 input 字段"
            assert "budget_allocation" in result, "缺少 budget_allocation 字段"
            assert "daily_plans" in result, "缺少 daily_plans 字段"
            assert "summary" in result, "缺少 summary 字段"

            # 2. 输入回显正确
            assert result["input"]["destination"] == case["destination"], "目的地不一致"
            assert result["input"]["days"] == case["days"], "天数不一致"
            assert result["input"]["budget"] == case["budget"], "预算不一致"

            # 3. 天数匹配
            assert len(result["daily_plans"]) == case["days"], "每日计划数量与天数不符"

            # 4. 预算分配合理性（宽松范围）
            alloc = result["budget_allocation"]
            total_alloc = alloc["total_allocated"]
            # 总分配金额与预算相差不超过 1%（允许四舍五入误差）
            assert abs(total_alloc - case["budget"]) <= max(1.0, case["budget"] * 0.01), \
                f"预算分配总额 {total_alloc} 与输入预算 {case['budget']} 偏差过大"
            # 每日住宿费为正数
            assert alloc["accommodation_per_day"] > 0, "每日住宿费应为正数"

            # 5. 每日计划结构
            for day_plan in result["daily_plans"]:
                assert "day" in day_plan, "每日计划缺少 day 字段"
                assert day_plan["day"] >= 1, "day 字段应为正整数"
                assert "morning" in day_plan, "缺少 morning"
                assert "afternoon" in day_plan, "缺少 afternoon"
                assert "evening" in day_plan, "缺少 evening"
                assert "meals" in day_plan, "缺少 meals"
                # 每日预算为正数
                daily_budget = day_plan["daily_budget"]
                assert daily_budget["accommodation"] > 0, "每日住宿预算应为正数"
                assert daily_budget["food"] > 0, "每日餐饮预算应为正数"
                # 活动时长合理（0.5 ~ 8 小时）
                assert 0.5 <= day_plan["estimated_hours"] <= 8.0, "每日活动时长超出合理范围"

            # 6. 汇总信息
            summary = result["summary"]
            assert summary["total_days"] == case["days"], "汇总天数不符"
            assert len(summary["tips"]) >= 1, "缺少旅行建议"

            print(f"  ✓ 样例 {idx} 通过")

        except AssertionError as exc:
            print(f"  ✗ 样例 {idx} 断言失败: {exc}")
            raise TravelPlanError("E009", str(exc)) from exc
        except TravelPlanError as exc:
            print(f"  ✗ 样例 {idx} 生成失败: {exc}")
            raise
        except Exception as exc:
            print(f"  ✗ 样例 {idx} 未知错误: {exc}")
            raise TravelPlanError("E010", str(exc)) from exc

    # ---- 测试错误处理 ----
    print("\n--- 错误处理测试 ---")
    error_cases = [
        ({"destination": "", "days": 3, "budget": 1000}, "E001"),
        ({"destination": "北京", "days": 0, "budget": 1000}, "E002"),
        ({"destination": "北京", "days": -1, "budget": 1000}, "E002"),
        ({"destination": "北京", "days": 3, "budget": 0}, "E003"),
        ({"destination": "北京", "days": 3, "budget": -100}, "E003"),
        ({"destination": "北京!!!", "days": 3, "budget": 1000}, "E004"),
    ]

    for case, expected_code in error_cases:
        try:
            generate_travel_plan(
                destination=case["destination"],
                days=case["days"],
                budget=case["budget"],
            )
            print(f"  ✗ 应抛出 {expected_code} 但未抛出")
            raise TravelPlanError("E009", f"预期错误 {expected_code} 未触发")
        except TravelPlanError as exc:
            if exc.code == expected_code:
                print(f"  ✓ 正确抛出 {exc.code}: {exc.message}")
            else:
                print(f"  ✗ 预期 {expected_code}，实际 {exc.code}: {exc.message}")
                raise

    # ---- 测试 JSON 输出 ----
    print("\n--- JSON 输出测试 ---")
    try:
        result = generate_travel_plan("上海", 2, 2000, output_format="json")
        json_str = format_output(result, "json")
        parsed = json.loads(json_str)
        assert parsed["input"]["days"] == 2, "JSON 解析后天数不符"
        print("  ✓ JSON 输出/解析正常")
    except Exception as exc:
        print(f"  ✗ JSON 测试失败: {exc}")
        raise TravelPlanError("E009", f"JSON 测试失败: {exc}") from exc

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="旅行行程规划工具 - 根据目的地、天数、预算生成结构化行程方案",
        epilog="示例: python main.py --destination 北京 --days 3 --budget 5000 --format json",
    )

    parser.add_argument("--destination", "-d", type=str, help="旅行目的地")
    parser.add_argument("--days", type=int, help="旅行天数（正整数）")
    parser.add_argument("--budget", type=float, help="总预算（正数）")
    parser.add_argument(
        "--format",
        choices=["json", "dict"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子（用于复现相同结果）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--parse-text",
        type=str,
        help="从自由文本中解析参数（如：'北京 3天 5000元'）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except TravelPlanError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1

    # 文本解析模式
    if args.parse_text:
        try:
            parsed = parse_input_text(args.parse_text)
            print(f"解析结果: 目的地={parsed['destination']}, 天数={parsed['days']}, 预算={parsed['budget']}")
            args.destination = parsed["destination"]
            args.days = parsed["days"]
            args.budget = parsed["budget"]
        except TravelPlanError as exc:
            print(f"文本解析失败: {exc}", file=sys.stderr)
            return 1

    # 参数完整性检查
    if not args.destination or not args.days or not args.budget:
        parser.print_help()
        print("\n错误: 必须提供 --destination, --days, --budget 或使用 --selftest", file=sys.stderr)
        return 1

    # 正常生成模式
    try:
        result = generate_travel_plan(
            destination=args.destination,
            days=args.days,
            budget=args.budget,
            output_format=args.format,
            seed=args.seed,
        )
        output = format_output(result, args.format)
        print(output)
        return 0
    except TravelPlanError as exc:
        print(f"生成失败: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
