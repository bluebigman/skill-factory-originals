#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tax-calc-individual - 个税精算工具

根据收入构成计算个人所得税，输出税后收入与筹划建议。
仅使用 Python 标准库实现，无第三方依赖。

用法示例:
    python main.py --salary 30000 --bonus 50000 --social 3000 --special 2000
    python main.py --selftest
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple, Union

# ============================================================
# 错误码定义
# ============================================================
# E001: 参数解析错误
# E002: 收入金额非法（负数或非数字）
# E003: 社保/专项扣除非法
# E004: 年终奖金额非法
# E005: 内部计算异常
# E006: 输入类型错误
# E007: 参数缺失
# E008: 自检失败
# E009: 文件操作错误
# E010: 未知错误

# ============================================================
# 常量定义
# ============================================================

# 综合所得年度税率表（按月换算）
# 级数 | 月应纳税所得额区间（元） | 税率(%) | 速算扣除数（元）
MONTHLY_TAX_BRACKETS = [
    # (上限, 税率, 速算扣除数)
    (3000, 0.03, 0),          # 1级: 不超过3000元
    (12000, 0.10, 210),       # 2级: 3000-12000元
    (25000, 0.20, 1410),      # 3级: 12000-25000元
    (35000, 0.25, 2660),      # 4级: 25000-35000元
    (55000, 0.30, 4410),      # 5级: 35000-55000元
    (80000, 0.35, 7160),      # 6级: 55000-80000元
    (float('inf'), 0.45, 15160),  # 7级: 超过80000元
]

# 全年一次性奖金税率表（按月换算后的综合所得税率表）
# 级数 | 月均奖金区间（元） | 税率(%) | 速算扣除数（元）
BONUS_TAX_BRACKETS = [
    (3000, 0.03, 0),
    (12000, 0.10, 210),
    (25000, 0.20, 1410),
    (35000, 0.25, 2660),
    (55000, 0.30, 4410),
    (80000, 0.35, 7160),
    (float('inf'), 0.45, 15160),
]

# 基本减除费用（每月）
BASIC_DEDUCTION = 5000

# 社会保险缴费比例（个人部分，参考值）
# 实际比例因地区而异，此处使用常见参考值
SOCIAL_RATES = {
    'pension': 0.08,    # 养老保险
    'medical': 0.02,    # 医疗保险
    'unemployment': 0.005,  # 失业保险
    'housing_fund': 0.12,   # 住房公积金（最高比例）
}

# 社保缴费基数上下限（参考值，元/月）
SOCIAL_BASE_MIN = 3000
SOCIAL_BASE_MAX = 30000


# ============================================================
# 核心计算函数
# ============================================================

def calculate_monthly_tax(taxable_income: float) -> float:
    """
    计算月度综合所得个人所得税
    
    参数:
        taxable_income: 应纳税所得额（已扣除起征点和各项扣除）
    
    返回:
        应纳个人所得税额
    """
    if taxable_income <= 0:
        return 0.0
    
    for upper, rate, quick_deduction in MONTHLY_TAX_BRACKETS:
        if taxable_income <= upper:
            tax = taxable_income * rate - quick_deduction
            return max(0.0, tax)
    
    # 理论上不会走到这里，但为了安全
    return taxable_income * 0.45 - 15160


def calculate_bonus_tax(bonus: float) -> float:
    """
    计算全年一次性奖金个人所得税（单独计税方式）
    
    参数:
        bonus: 全年一次性奖金金额（元）
    
    返回:
        应纳个人所得税额
    """
    if bonus <= 0:
        return 0.0
    
    # 将年终奖除以12个月，确定适用税率和速算扣除数
    monthly_equivalent = bonus / 12.0
    
    for upper, rate, quick_deduction in BONUS_TAX_BRACKETS:
        if monthly_equivalent <= upper:
            tax = bonus * rate - quick_deduction
            return max(0.0, tax)
    
    # 理论上不会走到这里
    return bonus * 0.45 - 15160


def calculate_social_insurance(salary: float, 
                                base: Optional[float] = None,
                                rates: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    计算社会保险和住房公积金个人缴纳部分
    
    参数:
        salary: 月工资薪金
        base: 社保缴费基数（默认使用工资，但受上下限约束）
        rates: 各险种费率（默认使用参考值）
    
    返回:
        包含各险种金额和总金额的字典
    """
    if rates is None:
        rates = SOCIAL_RATES
    
    # 确定缴费基数
    if base is None:
        base = salary
    base = max(SOCIAL_BASE_MIN, min(base, SOCIAL_BASE_MAX))
    
    result = {}
    total = 0.0
    for key, rate in rates.items():
        amount = base * rate
        result[key] = round(amount, 2)
        total += amount
    
    result['total'] = round(total, 2)
    return result


def calculate_tax(salary: float,
                  bonus: float = 0.0,
                  social_insurance: float = 0.0,
                  special_deduction: float = 0.0,
                  other_deduction: float = 0.0) -> Dict[str, Union[float, str]]:
    """
    综合计算个人所得税
    
    参数:
        salary: 月工资薪金（税前）
        bonus: 全年一次性奖金（年终奖）
        social_insurance: 每月社保公积金个人缴纳总额
        special_deduction: 每月专项附加扣除
        other_deduction: 其他扣除（如企业年金等）
    
    返回:
        包含各项计算结果的字典
    """
    # 各类扣除合计
    total_deduction = BASIC_DEDUCTION + social_insurance + special_deduction + other_deduction
    
    # 工资薪金应纳税所得额
    salary_taxable = salary - total_deduction
    
    # 工资薪金应纳个税
    salary_tax = calculate_monthly_tax(salary_taxable)
    
    # 年终奖应纳个税（单独计税）
    bonus_tax = calculate_bonus_tax(bonus)
    
    # 总个税
    total_tax = salary_tax + bonus_tax
    
    # 税后收入（包含年终奖）
    after_tax = salary + bonus - social_insurance - special_deduction - other_deduction - total_tax
    
    # 实际税负率
    total_income = salary + bonus
    if total_income > 0:
        effective_rate = total_tax / total_income * 100
    else:
        effective_rate = 0.0
    
    return {
        'salary': salary,
        'bonus': bonus,
        'social_insurance': social_insurance,
        'special_deduction': special_deduction,
        'other_deduction': other_deduction,
        'total_deduction': total_deduction,
        'salary_taxable': salary_taxable,
        'salary_tax': salary_tax,
        'bonus_tax': bonus_tax,
        'total_tax': total_tax,
        'after_tax': after_tax,
        'effective_rate': round(effective_rate, 2),
        'monthly_after_tax': round(after_tax / 12.0, 2) if bonus > 0 else round(after_tax, 2),
    }


def generate_advice(result: Dict[str, Union[float, str]]) -> List[str]:
    """
    根据计算结果生成筹划建议
    
    参数:
        result: calculate_tax 的返回结果
    
    返回:
        建议列表
    """
    advice = []
    salary = float(result['salary'])
    bonus = float(result['bonus'])
    total_tax = float(result['total_tax'])
    salary_tax = float(result['salary_tax'])
    bonus_tax = float(result['bonus_tax'])
    
    # 建议1: 年终奖临界点提示
    if bonus > 0:
        # 检查是否接近临界点
        critical_points = [36000, 144000, 300000, 420000, 660000, 960000]
        for point in critical_points:
            if abs(bonus - point) < 1000:
                advice.append(f"年终奖 {bonus:.0f} 元接近临界点 {point} 元，建议调整金额以避免税负跳升。")
                break
    
    # 建议2: 工资与年终奖比例优化
    if salary > 0 and bonus > 0:
        ratio = bonus / salary if salary > 0 else 0
        if ratio > 2:
            advice.append("年终奖占比较高，可考虑适当降低年终奖、提高月薪，以平衡综合所得适用税率。")
        elif ratio < 0.5:
            advice.append("月薪占比较高，可考虑将部分收入转化为年终奖，利用单独计税政策降低税负。")
    
    # 建议3: 专项附加扣除提示
    special = float(result['special_deduction'])
    if special < 1000:
        advice.append("专项附加扣除较低，请确认是否已充分利用子女教育、赡养老人、住房贷款利息等扣除项目。")
    
    # 建议4: 税负率提示
    effective_rate = float(result['effective_rate'])
    if effective_rate > 30:
        advice.append(f"当前综合税负率 {effective_rate:.1f}% 偏高，建议咨询专业税务师进行综合筹划。")
    elif effective_rate < 5:
        advice.append(f"当前综合税负率 {effective_rate:.1f}% 较低，税务负担较轻。")
    
    # 建议5: 社保基数提示
    social = float(result['social_insurance'])
    if social == 0:
        advice.append("未计算社保扣除，请确认社保缴纳情况。社保个人部分可税前扣除。")
    
    if not advice:
        advice.append("当前收入结构较为合理，无需特别调整。")
    
    return advice


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据验证核心功能
    
    返回:
        自检是否通过
    """
    print("=" * 60)
    print("自检开始 (SELFTEST)")
    print("=" * 60)
    
    test_cases = [
        # (描述, 参数, 期望结果条件)
        (
            "基础案例：月薪10000，无年终奖",
            {'salary': 10000, 'bonus': 0, 'social_insurance': 1000, 'special_deduction': 1500},
            lambda r: r['total_tax'] >= 0 and r['after_tax'] > 0 and r['after_tax'] < 10000
        ),
        (
            "高收入案例：月薪50000，年终奖100000",
            {'salary': 50000, 'bonus': 100000, 'social_insurance': 3000, 'special_deduction': 2000},
            lambda r: r['total_tax'] > 0 and r['after_tax'] > 0 and r['effective_rate'] > 0
        ),
        (
            "低收入案例：月薪5000，无扣除",
            {'salary': 5000, 'bonus': 0, 'social_insurance': 0, 'special_deduction': 0},
            lambda r: r['total_tax'] == 0 and abs(r['after_tax'] - 5000) < 0.01
        ),
        (
            "仅年终奖案例",
            {'salary': 0, 'bonus': 36000, 'social_insurance': 0, 'special_deduction': 0},
            lambda r: r['bonus_tax'] > 0 and r['salary_tax'] == 0
        ),
        (
            "高额年终奖案例",
            {'salary': 20000, 'bonus': 200000, 'social_insurance': 2000, 'special_deduction': 1000},
            lambda r: r['total_tax'] > 0 and r['after_tax'] > 0
        ),
    ]
    
    all_passed = True
    for i, (desc, params, check) in enumerate(test_cases, 1):
        try:
            result = calculate_tax(**params)
            if check(result):
                print(f"  [通过] 案例{i}: {desc}")
                print(f"         税额={result['total_tax']:.2f}, 税后={result['after_tax']:.2f}")
            else:
                print(f"  [失败] 案例{i}: {desc}")
                print(f"         结果: {result}")
                all_passed = False
        except Exception as e:
            print(f"  [错误] 案例{i}: {desc}")
            print(f"         异常: {e}")
            all_passed = False
    
    # 测试边界情况
    print("-" * 40)
    print("边界情况测试:")
    
    # 测试零收入
    try:
        result = calculate_tax(0, 0, 0, 0, 0)
        assert result['total_tax'] == 0
        assert result['after_tax'] == 0
        print("  [通过] 零收入情况")
    except Exception as e:
        print(f"  [失败] 零收入情况: {e}")
        all_passed = False
    
    # 测试年终奖临界点
    try:
        bonus1 = 36000
        bonus2 = 36001
        tax1 = calculate_bonus_tax(bonus1)
        tax2 = calculate_bonus_tax(bonus2)
        # 临界点附近税负可能跳升，但税额应为正
        assert tax1 >= 0 and tax2 >= 0
        print(f"  [通过] 年终奖临界点测试: {bonus1}元税={tax1:.2f}, {bonus2}元税={tax2:.2f}")
    except Exception as e:
        print(f"  [失败] 年终奖临界点测试: {e}")
        all_passed = False
    
    # 测试社保计算
    try:
        social = calculate_social_insurance(10000)
        assert social['total'] > 0
        assert social['pension'] > 0
        print(f"  [通过] 社保计算: 月薪10000, 社保总额={social['total']:.2f}")
    except Exception as e:
        print(f"  [失败] 社保计算: {e}")
        all_passed = False
    
    # 测试建议生成
    try:
        result = calculate_tax(30000, 50000, 3000, 2000)
        advice = generate_advice(result)
        assert len(advice) > 0
        print(f"  [通过] 建议生成: {len(advice)}条建议")
    except Exception as e:
        print(f"  [失败] 建议生成: {e}")
        all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 输入验证
# ============================================================

def validate_amount(value: Optional[float], field_name: str, allow_zero: bool = True) -> float:
    """
    验证金额输入
    
    参数:
        value: 输入值
        field_name: 字段名称（用于错误信息）
        allow_zero: 是否允许为零
    
    返回:
        验证后的数值
    
    异常:
        E002: 金额非法
        E006: 类型错误
    """
    if value is None:
        return 0.0
    
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"E006: {field_name}必须是数字")
    
    if value < 0:
        raise ValueError(f"E002: {field_name}不能为负数")
    
    if not allow_zero and value == 0:
        raise ValueError(f"E002: {field_name}必须大于零")
    
    return value


# ============================================================
# 主入口
# ============================================================

def parse_args(argv: List[str]) -> argparse.Namespace:
    """
    解析命令行参数
    
    参数:
        argv: 命令行参数列表
    
    返回:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description="个税精算工具 - 计算个人所得税并生成筹划建议",
        epilog="示例: python main.py --salary 30000 --bonus 50000 --social 3000 --special 2000"
    )
    
    parser.add_argument("--salary", type=float, default=0,
                        help="月工资薪金（税前），默认0")
    parser.add_argument("--bonus", type=float, default=0,
                        help="全年一次性奖金（年终奖），默认0")
    parser.add_argument("--social", type=float, default=0,
                        help="每月社保公积金个人缴纳总额，默认0")
    parser.add_argument("--special", type=float, default=0,
                        help="每月专项附加扣除，默认0")
    parser.add_argument("--other", type=float, default=0,
                        help="每月其他扣除（如企业年金），默认0")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    parser.add_argument("--json", action="store_true",
                        help="以JSON格式输出结果")
    
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        raise ValueError("E001: 参数解析失败")
    
    return args


def main(argv: Optional[List[str]] = None) -> int:
    """
    主函数
    
    参数:
        argv: 命令行参数列表
    
    返回:
        退出码（0成功，非0失败）
    """
    if argv is None:
        argv = sys.argv[1:]
    
    try:
        args = parse_args(argv)
        
        # 自检模式
        if args.selftest:
            success = run_selftest()
            return 0 if success else 8
        
        # 验证输入
        try:
            salary = validate_amount(args.salary, "工资")
            bonus = validate_amount(args.bonus, "年终奖")
            social = validate_amount(args.social, "社保")
            special = validate_amount(args.special, "专项扣除")
            other = validate_amount(args.other, "其他扣除")
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 2
        
        # 检查是否有任何收入输入
        if salary == 0 and bonus == 0:
            print("错误: E007 请至少输入工资或年终奖一项收入", file=sys.stderr)
            print("示例: python main.py --salary 30000 --bonus 50000", file=sys.stderr)
            return 7
        
        # 计算
        try:
            result = calculate_tax(salary, bonus, social, special, other)
            advice = generate_advice(result)
        except Exception as e:
            print(f"错误: E005 计算异常: {e}", file=sys.stderr)
            return 5
        
        # 输出结果
        if args.json:
            output = {
                'input': {
                    'salary': salary,
                    'bonus': bonus,
                    'social_insurance': social,
                    'special_deduction': special,
                    'other_deduction': other,
                },
                'result': {k: (float(v) if isinstance(v, (int, float)) else v) 
                          for k, v in result.items()},
                'advice': advice,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print("个人所得税计算明细")
            print("=" * 60)
            print(f"月工资薪金:        {salary:>12,.2f} 元")
            print(f"年终奖:            {bonus:>12,.2f} 元")
            print(f"社保公积金(月):    {social:>12,.2f} 元")
            print(f"专项附加扣除(月):  {special:>12,.2f} 元")
            print(f"其他扣除(月):      {other:>12,.2f} 元")
            print("-" * 60)
            print(f"工资应纳税所得额:  {result['salary_taxable']:>12,.2f} 元")
            print(f"工资应纳个税:      {result['salary_tax']:>12,.2f} 元")
            print(f"年终奖应纳个税:    {result['bonus_tax']:>12,.2f} 元")
            print(f"合计应纳个税:      {result['total_tax']:>12,.2f} 元")
            print(f"税后收入(年):      {result['after_tax']:>12,.2f} 元")
            print(f"综合税负率:        {result['effective_rate']:>10.2f} %")
            print("=" * 60)
            print("筹划建议:")
            for i, item in enumerate(advice, 1):
                print(f"  {i}. {item}")
            print("=" * 60)
        
        return 0
        
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010 未知错误: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
