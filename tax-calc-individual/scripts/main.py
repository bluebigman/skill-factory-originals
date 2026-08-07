#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 个税精算 收入筹划 税后测算

依据功能规格 clean-room 独立实现的命令行工具。
支持工资薪金、年终奖、劳务报酬、经营所得的个税计算与筹划建议。

用法示例:
    python main.py --salary 300000 --bonus 50000 --social 30000 --special 24000
    python main.py --selftest
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义（依据功能规格 1.3 关键参数速查）
# ============================================================

# 基本减除费用
BASIC_DEDUCTION_YEAR = 60000  # 元/年（5000元/月 × 12）

# 综合所得 7 级超额累进税率表: (上限, 税率, 速算扣除数)
COMPREHENSIVE_RATE_TABLE = [
    (36000, 0.03, 0),
    (144000, 0.10, 2520),
    (300000, 0.20, 16920),
    (420000, 0.25, 31920),
    (660000, 0.30, 52920),
    (960000, 0.35, 85920),
    (float("inf"), 0.45, 181920),
]

# 经营所得 5 级超额累进税率表: (上限, 税率, 速算扣除数)
BUSINESS_RATE_TABLE = [
    (30000, 0.05, 0),
    (90000, 0.10, 1500),
    (300000, 0.20, 10500),
    (500000, 0.30, 40500),
    (float("inf"), 0.35, 65500),
]

# 劳务报酬预扣预缴 3 级税率表: (上限, 税率, 速算扣除数)
LABOR_PRECOLLECT_RATE_TABLE = [
    (20000, 0.20, 0),
    (50000, 0.30, 2000),
    (float("inf"), 0.40, 7000),
]

# 年终奖单独计税月度税率表（按月换算后）: (上限, 税率, 速算扣除数)
BONUS_MONTHLY_RATE_TABLE = [
    (3000, 0.03, 0),
    (12000, 0.10, 210),
    (25000, 0.20, 1410),
    (35000, 0.25, 2660),
    (55000, 0.30, 4410),
    (80000, 0.35, 7160),
    (float("inf"), 0.45, 15160),
]

# 错误码定义
ERR_INVALID_INPUT = "E001"      # 输入参数非法
ERR_NEGATIVE_VALUE = "E002"     # 收入/扣除为负数
ERR_INTERNAL = "E003"           # 内部计算错误
ERR_UNKNOWN_SCENARIO = "E004"   # 未知场景


# ============================================================
# 核心计算函数
# ============================================================

def calc_tax_by_table(taxable: float, rate_table: List[Tuple[float, float, float]]) -> float:
    """
    根据税率表计算应纳税额。
    taxable: 应纳税所得额（非负）
    rate_table: [(上限, 税率, 速算扣除数), ...] 需按上限升序
    返回: 应纳税额
    """
    if taxable < 0:
        raise ValueError(f"{ERR_NEGATIVE_VALUE}: 应纳税所得额不能为负")
    for upper, rate, quick_deduction in rate_table:
        if taxable <= upper:
            return taxable * rate - quick_deduction
    # 理论不可达（最后一项上限为 inf）
    raise RuntimeError(f"{ERR_INTERNAL}: 税率表遍历未命中")


def calc_comprehensive_tax(
    annual_salary: float,
    social_insurance: float = 0.0,
    special_additional: float = 0.0,
    other_deduction: float = 0.0,
) -> Dict[str, float]:
    """
    计算综合所得（工资薪金）年度应纳税额。
    应纳税所得额 = 年收入 - 基本减除费用(60000) - 专项扣除(三险一金) - 专项附加扣除 - 其他扣除
    """
    taxable = annual_salary - BASIC_DEDUCTION_YEAR - social_insurance - special_additional - other_deduction
    if taxable < 0:
        taxable = 0.0
    tax = calc_tax_by_table(taxable, COMPREHENSIVE_RATE_TABLE)
    after_tax = annual_salary - social_insurance - special_additional - other_deduction - tax
    return {
        "taxable_income": taxable,
        "tax": tax,
        "after_tax": after_tax,
        "effective_rate": tax / annual_salary if annual_salary > 0 else 0.0,
    }


def calc_bonus_tax(bonus: float) -> Dict[str, float]:
    """
    年终奖单独计税（全年一次性奖金）。
    将年终奖除以12按月换算，查月度税率表计算。
    """
    if bonus < 0:
        raise ValueError(f"{ERR_NEGATIVE_VALUE}: 年终奖不能为负")
    if bonus == 0:
        return {"tax": 0.0, "after_tax": 0.0, "effective_rate": 0.0}
    monthly = bonus / 12.0
    tax = calc_tax_by_table(monthly, BONUS_MONTHLY_RATE_TABLE) * 12.0
    return {
        "tax": tax,
        "after_tax": bonus - tax,
        "effective_rate": tax / bonus,
    }


def calc_labor_tax(labor_income: float) -> Dict[str, float]:
    """
    劳务报酬预扣预缴税额。
    每次收入不超过4000元: 减除800元费用
    超过4000元: 减除20%费用
    然后按 20%-40% 三级超额累进预扣率计算。
    """
    if labor_income < 0:
        raise ValueError(f"{ERR_NEGATIVE_VALUE}: 劳务报酬不能为负")
    if labor_income == 0:
        return {"tax": 0.0, "after_tax": 0.0, "effective_rate": 0.0}

    # 计算应纳税所得额（预扣预缴）
    if labor_income <= 4000:
        taxable = labor_income - 800
    else:
        taxable = labor_income * 0.8

    if taxable < 0:
        taxable = 0.0
    tax = calc_tax_by_table(taxable, LABOR_PRECOLLECT_RATE_TABLE)
    return {
        "tax": tax,
        "after_tax": labor_income - tax,
        "effective_rate": tax / labor_income,
    }


def calc_business_tax(business_income: float, cost: float = 0.0) -> Dict[str, float]:
    """
    经营所得（个体工商户/个人独资/合伙）年度应纳税额。
    应纳税所得额 = 收入 - 成本费用 - 基本减除费用(60000)
    """
    taxable = business_income - cost - BASIC_DEDUCTION_YEAR
    if taxable < 0:
        taxable = 0.0
    tax = calc_tax_by_table(taxable, BUSINESS_RATE_TABLE)
    after_tax = business_income - cost - tax
    return {
        "taxable_income": taxable,
        "tax": tax,
        "after_tax": after_tax,
        "effective_rate": tax / business_income if business_income > 0 else 0.0,
    }


def plan_bonus(
    salary: float,
    bonus: float,
    social_insurance: float = 0.0,
    special_additional: float = 0.0,
) -> Dict[str, object]:
    """
    年终奖筹划：对比"单独计税"与"并入综合所得"两种方案，给出建议。
    返回包含两种方案税负对比和推荐结果的字典。
    """
    # 方案一: 年终奖单独计税
    salary_tax = calc_comprehensive_tax(salary, social_insurance, special_additional)["tax"]
    bonus_tax = calc_bonus_tax(bonus)["tax"]
    plan_a_total = salary_tax + bonus_tax

    # 方案二: 年终奖并入综合所得
    combined_result = calc_comprehensive_tax(
        salary + bonus, social_insurance, special_additional
    )
    plan_b_total = combined_result["tax"]

    # 推荐税负更低的方案
    if plan_a_total <= plan_b_total:
        recommended = "单独计税"
        total_tax = plan_a_total
    else:
        recommended = "并入综合所得"
        total_tax = plan_b_total

    return {
        "plan_a_tax": plan_a_total,       # 单独计税总税额
        "plan_b_tax": plan_b_total,       # 并入综合所得总税额
        "recommended": recommended,
        "min_tax": total_tax,
    }


# ============================================================
# 命令行交互
# ============================================================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="个税精算工具 - 支持工资、年终奖、劳务报酬、经营所得计算与筹划",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--salary", type=float, default=0.0, help="年工资薪金收入（元）")
    parser.add_argument("--bonus", type=float, default=0.0, help="年终奖金额（元）")
    parser.add_argument("--labor", type=float, default=0.0, help="劳务报酬收入（元）")
    parser.add_argument("--business", type=float, default=0.0, help="经营所得收入（元）")
    parser.add_argument("--cost", type=float, default=0.0, help="经营成本费用（元）")
    parser.add_argument("--social", type=float, default=0.0, help="专项扣除-三险一金（元/年）")
    parser.add_argument("--special", type=float, default=0.0, help="专项附加扣除（元/年）")
    parser.add_argument("--other", type=float, default=0.0, help="其他扣除（元/年）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    """校验输入参数合法性"""
    values = [
        args.salary, args.bonus, args.labor,
        args.business, args.cost,
        args.social, args.special, args.other,
    ]
    for v in values:
        if v < 0:
            raise ValueError(f"{ERR_NEGATIVE_VALUE}: 收入与扣除项不能为负数，收到 {v}")


def run_calculation(args: argparse.Namespace) -> Dict[str, object]:
    """根据参数执行计算，返回结果字典"""
    validate_args(args)
    result: Dict[str, object] = {}

    # 工资薪金
    if args.salary > 0:
        result["salary"] = calc_comprehensive_tax(
            args.salary, args.social, args.special, args.other
        )

    # 年终奖单独计税
    if args.bonus > 0:
        result["bonus"] = calc_bonus_tax(args.bonus)

    # 劳务报酬
    if args.labor > 0:
        result["labor"] = calc_labor_tax(args.labor)

    # 经营所得
    if args.business > 0:
        result["business"] = calc_business_tax(args.business, args.cost)

    # 年终奖筹划（仅当工资和年终奖同时存在时）
    if args.salary > 0 and args.bonus > 0:
        result["bonus_plan"] = plan_bonus(
            args.salary, args.bonus, args.social, args.special
        )

    return result


def format_result(result: Dict[str, object]) -> str:
    """格式化输出结果"""
    lines = ["=" * 50, "个税计算结果", "=" * 50]

    if "salary" in result:
        s = result["salary"]
        lines.append(f"\n【工资薪金】")
        lines.append(f"  应纳税所得额: {s['taxable_income']:.2f} 元")
        lines.append(f"  应纳税额:     {s['tax']:.2f} 元")
        lines.append(f"  税后收入:     {s['after_tax']:.2f} 元")
        lines.append(f"  有效税率:     {s['effective_rate']*100:.2f}%")

    if "bonus" in result:
        b = result["bonus"]
        lines.append(f"\n【年终奖单独计税】")
        lines.append(f"  应纳税额: {b['tax']:.2f} 元")
        lines.append(f"  税后金额: {b['after_tax']:.2f} 元")

    if "labor" in result:
        l = result["labor"]
        lines.append(f"\n【劳务报酬预扣预缴】")
        lines.append(f"  应纳税额: {l['tax']:.2f} 元")
        lines.append(f"  税后收入: {l['after_tax']:.2f} 元")

    if "business" in result:
        b = result["business"]
        lines.append(f"\n【经营所得】")
        lines.append(f"  应纳税所得额: {b['taxable_income']:.2f} 元")
        lines.append(f"  应纳税额:     {b['tax']:.2f} 元")
        lines.append(f"  税后利润:     {b['after_tax']:.2f} 元")

    if "bonus_plan" in result:
        p = result["bonus_plan"]
        lines.append(f"\n【年终奖筹划建议】")
        lines.append(f"  方案一(单独计税)总税负: {p['plan_a_tax']:.2f} 元")
        lines.append(f"  方案二(并入综合)总税负: {p['plan_b_tax']:.2f} 元")
        lines.append(f"  ★ 推荐方案: {p['recommended']} (总税负 {p['min_tax']:.2f} 元)")

    lines.append("\n" + "=" * 50)
    lines.append("注: 以上结果仅供参考，不构成税务建议。")
    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> None:
    """
    内置自检函数：使用硬编码样例数据验证核心逻辑。
    不读取外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值（大小比较/区间判断）确保稳健。
    """
    print("开始自检...")

    # ---- 测试 1: 综合所得（工资薪金） ----
    # 场景: 年薪 30 万，三险一金 3 万，专项附加 2.4 万
    # 应纳税所得额 = 300000 - 60000 - 30000 - 24000 = 186000
    # 应落在 144000-300000 区间，税率 20%，速算扣除 16920
    # 税额 = 186000 * 0.20 - 16920 = 20280
    r = calc_comprehensive_tax(300000, 30000, 24000)
    assert r["taxable_income"] > 180000, "应纳税所得额应在18万左右"
    assert r["taxable_income"] < 190000, "应纳税所得额应在18万左右"
    assert r["tax"] > 19000, "税额应大于19000"
    assert r["tax"] < 21500, "税额应小于21500"
    assert r["after_tax"] > 220000, "税后收入应大于22万"
    assert r["effective_rate"] > 0.06, "有效税率应大于6%"
    assert r["effective_rate"] < 0.08, "有效税率应小于8%"
    print("✓ 综合所得计算正确")

    # ---- 测试 2: 年终奖单独计税 ----
    # 场景: 年终奖 50000 元
    # 月均 = 50000 / 12 ≈ 4166.67，落在 3000-12000 区间
    # 税率 10%，速算扣除 210
    # 税额 = 4166.67 * 0.10 - 210 = 206.67，×12 = 2480
    b = calc_bonus_tax(50000)
    assert b["tax"] > 2300, "年终奖税额应大于2300"
    assert b["tax"] < 2700, "年终奖税额应小于2700"
    assert b["after_tax"] > 47000, "税后应大于47000"
    assert b["after_tax"] < 48000, "税后应小于48000"
    assert 0.045 < b["effective_rate"] < 0.055, "有效税率应在5%左右"
    print("✓ 年终奖单独计税正确")

    # ---- 测试 3: 劳务报酬预扣预缴 ----
    # 场景: 劳务收入 30000 元
    # 超过4000元，减除20%费用，应纳税所得额 = 24000
    # 落在 20000-50000 区间，税率 30%，速算扣除 2000
    # 税额 = 24000 * 0.30 - 2000 = 5200
    l = calc_labor_tax(30000)
    assert l["tax"] > 4800, "劳务报酬税额应大于4800"
    assert l["tax"] < 5600, "劳务报酬税额应小于5600"
    assert l["after_tax"] > 24000, "税后应大于24000"
    assert l["after_tax"] < 26000, "税后应小于26000"
    assert 0.15 < l["effective_rate"] < 0.20, "有效税率应在15%-20%之间"
    print("✓ 劳务报酬预扣预缴正确")

    # ---- 测试 4: 经营所得 ----
    # 场景: 经营收入 200000，成本 50000
    # 应纳税所得额 = 200000 - 50000 - 60000 = 90000
    # 落在 30000-90000 区间，税率 10%，速算扣除 1500
    # 税额 = 90000 * 0.10 - 1500 = 7500
    biz = calc_business_tax(200000, 50000)
    assert biz["taxable_income"] > 85000, "应纳税所得额应大于85000"
    assert biz["taxable_income"] < 95000, "应纳税所得额应小于95000"
    assert biz["tax"] > 7000, "经营所得税额应大于7000"
    assert biz["tax"] < 8000, "经营所得税额应小于8000"
    assert biz["after_tax"] > 140000, "税后利润应大于14万"
    assert 0.03 < biz["effective_rate"] < 0.05, "有效税率应在3%-5%之间"
    print("✓ 经营所得计算正确")

    # ---- 测试 5: 年终奖筹划对比 ----
    # 场景: 年薪 30 万 + 年终奖 5 万
    # 单独计税: 工资税额约 20280 + 年终奖税额约 2480 ≈ 22760
    # 并入综合: 应纳税所得额 = 350000 - 60000 - 30000 - 24000 = 236000
    #           税额 = 236000 * 0.20 - 16920 = 30280
    # 因此推荐单独计税
    plan = plan_bonus(300000, 50000, 30000, 24000)
    assert plan["plan_a_tax"] < plan["plan_b_tax"], "单独计税应更优"
    assert plan["recommended"] == "单独计税"
    assert plan["min_tax"] < 23000, "最小税负应小于23000"
    assert plan["min_tax"] > 22000, "最小税负应大于22000"
    print("✓ 年终奖筹划对比正确")

    # ---- 测试 6: 边界情况 ----
    # 零收入
    zero = calc_comprehensive_tax(0)
    assert zero["tax"] == 0.0, "零收入税额应为0"
    assert zero["after_tax"] == 0.0, "零收入税后应为0"
    zero_bonus = calc_bonus_tax(0)
    assert zero_bonus["tax"] == 0.0, "零年终奖税额应为0"

    # 低收入（低于起征点）
    low = calc_comprehensive_tax(40000)
    assert low["tax"] == 0.0, "年收入4万不应缴税"
    assert low["after_tax"] == 40000.0, "税后应等于收入"

    # 劳务报酬小额（低于800元）
    small_labor = calc_labor_tax(500)
    assert small_labor["tax"] == 0.0, "500元劳务报酬不应预扣"

    # 经营亏损（收入低于成本+起征点）
    loss = calc_business_tax(30000, 50000)
    assert loss["tax"] == 0.0, "经营亏损不应缴税"
    print("✓ 边界情况处理正确")

    # ---- 测试 7: 错误处理 ----
    try:
        calc_comprehensive_tax(-100)
        assert False, "应抛出异常"
    except ValueError as e:
        assert str(e).startswith(ERR_NEGATIVE_VALUE), "错误码应为 E002"

    try:
        calc_bonus_tax(-50)
        assert False, "应抛出异常"
    except ValueError as e:
        assert str(e).startswith(ERR_NEGATIVE_VALUE), "错误码应为 E002"

    # 非法参数校验
    try:
        validate_args(argparse.Namespace(
            salary=-1, bonus=0, labor=0, business=0,
            cost=0, social=0, special=0, other=0,
        ))
        assert False, "应抛出异常"
    except ValueError as e:
        assert str(e).startswith(ERR_NEGATIVE_VALUE), "错误码应为 E002"
    print("✓ 错误处理正确")

    print("\n✅ 全部自检通过！")


# ============================================================
# 程序入口
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    args = parse_args(argv)

    if args.selftest:
        try:
            run_selftest()
            return 0
        except Exception as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    try:
        result = run_calculation(args)
        if not result:
            print("未提供任何收入参数。请使用 --salary/--bonus/--labor/--business 指定收入。")
            print("或使用 --selftest 运行自检。")
            return 0
        print(format_result(result))
        return 0
    except ValueError as e:
        print(f"输入错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"计算错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
