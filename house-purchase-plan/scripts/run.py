#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
购房测算工具 - 月供评估与预算规划
功能：计算月供、税费、现金流压力，生成购房建议
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone

# 默认参数配置
DEFAULT_LPR = 3.85  # 5年期以上LPR（%）
DEFAULT_BP = 30     # 默认加点（基点）
DEFAULT_LOAN_YEARS = 30
DEFAULT_DOWN_PAYMENT_RATIO = 0.30

# 税费参数（按常规标准估算）
TAX_RATES = {
    'deed_tax': 0.015,      # 契税（首套90平以上）
    'agent_fee': 0.01,      # 中介费
    'maintenance_fund': 200, # 维修基金（元/平）
    'stamp_tax': 0.0005,    # 印花税
    'transfer_fee': 80,     # 过户费（固定）
    'other_fee': 2000       # 其他杂费（评估、公证等）
}

def calculate_monthly_payment(principal, annual_rate, years, method='equal_installment'):
    """
    计算月供
    :param principal: 贷款本金
    :param annual_rate: 年利率（%）
    :param years: 贷款年限
    :param method: equal_installment(等额本息) / equal_principal(等额本金)
    :return: (首月月供, 总利息, 月供列表)
    """
    if principal <= 0 or annual_rate < 0 or years <= 0:
        raise ValueError("贷款金额、利率、年限必须为正数")
    
    monthly_rate = annual_rate / 100 / 12
    months = years * 12
    
    if method == 'equal_installment':
        if monthly_rate == 0:
            monthly_payment = principal / months
            total_interest = 0
        else:
            factor = (1 + monthly_rate) ** months
            monthly_payment = principal * monthly_rate * factor / (factor - 1)
            total_interest = monthly_payment * months - principal
        return monthly_payment, total_interest, [monthly_payment] * months
    
    elif method == 'equal_principal':
        monthly_principal = principal / months
        payments = []
        total_interest = 0
        for i in range(months):
            interest = (principal - monthly_principal * i) * monthly_rate
            payment = monthly_principal + interest
            payments.append(payment)
            total_interest += interest
        return payments[0], total_interest, payments
    
    else:
        raise ValueError("还款方式必须是 equal_installment 或 equal_principal")

def calculate_taxes(house_price, area, is_first_house=True):
    """
    估算购房税费
    :param house_price: 房屋总价
    :param area: 房屋面积（平米）
    :param is_first_house: 是否首套房
    :return: 税费明细字典
    """
    if area <= 0:
        raise ValueError("房屋面积必须为正数")
    
    taxes = {}
    
    # 契税（首套90平以下1%，90平以上1.5%；二套3%）
    if is_first_house:
        deed_rate = 0.01 if area <= 90 else 0.015
    else:
        deed_rate = 0.03
    taxes['契税'] = house_price * deed_rate
    
    # 中介费
    taxes['中介费'] = house_price * TAX_RATES['agent_fee']
    
    # 维修基金（按面积动态计算）
    taxes['维修基金'] = TAX_RATES['maintenance_fund'] * area
    
    # 印花税
    taxes['印花税'] = house_price * TAX_RATES['stamp_tax']
    
    # 固定费用
    taxes['过户费'] = TAX_RATES['transfer_fee']
    taxes['其他杂费'] = TAX_RATES['other_fee']
    
    return taxes

def assess_affordability(monthly_payment, monthly_income):
    """
    评估月供压力
    :param monthly_payment: 月供
    :param monthly_income: 月收入
    :return: (DTI比率, 压力等级, 建议)
    """
    if monthly_income <= 0:
        raise ValueError("月收入必须为正数")
    
    dti = monthly_payment / monthly_income * 100
    
    if dti <= 20:
        level = "轻松"
        advice = "月供压力很小，可考虑适当提高贷款额度或缩短贷款年限。"
    elif dti <= 28:
        level = "舒适"
        advice = "月供在安全范围内，建议预留3-6个月月供作为应急资金。"
    elif dti <= 35:
        level = "警戒"
        advice = "月供接近警戒线，建议控制其他负债，增加收入或降低贷款额度。"
    elif dti <= 45:
        level = "危险"
        advice = "月供压力较大，建议重新评估购房预算或延长贷款年限。"
    else:
        level = "高危"
        advice = "月供严重超出安全范围，强烈建议调整购房计划。"
    
    return dti, level, advice

def generate_advice(house_price, down_payment, loan_amount, monthly_payment, 
                    monthly_income, dti, total_taxes, method):
    """
    生成综合购房建议
    """
    advice_lines = []
    
    # 首付比例建议
    down_ratio = down_payment / house_price * 100
    if down_ratio < 30:
        advice_lines.append(f"当前首付比例{down_ratio:.1f}%，低于30%，建议提高首付以降低月供压力。")
    elif down_ratio >= 50:
        advice_lines.append(f"首付比例{down_ratio:.1f}%，较为充足，可考虑缩短贷款年限节省利息。")
    
    # 还款方式建议
    if method == 'equal_installment':
        advice_lines.append("等额本息月供固定，适合收入稳定的工薪族，便于预算管理。")
    else:
        advice_lines.append("等额本金前期压力大但总利息少，适合收入较高且预期收入增长的人群。")
    
    # 税费提醒
    tax_ratio = total_taxes / house_price * 100
    advice_lines.append(f"税费约占房价{tax_ratio:.1f}%，需提前准备{total_taxes:,.0f}元现金。")
    
    # 综合建议
    if dti <= 28:
        advice_lines.append("整体财务状况健康，购房计划可行。")
    elif dti <= 35:
        advice_lines.append("财务状况尚可，建议控制其他消费，确保月供按时支付。")
    else:
        advice_lines.append("财务压力较大，建议重新评估购房预算或增加收入来源。")
    
    return "\n".join(advice_lines)

def format_output(result):
    """格式化输出结果"""
    lines = []
    lines.append("=" * 60)
    lines.append("购房测算结果")
    lines.append("=" * 60)
    lines.append(f"房屋总价: {result['house_price']:,.0f} 元")
    lines.append(f"房屋面积: {result['area']:.0f} 平米")
    lines.append(f"首付金额: {result['down_payment']:,.0f} 元")
    lines.append(f"贷款金额: {result['loan_amount']:,.0f} 元")
    lines.append(f"贷款年限: {result['loan_years']} 年")
    lines.append(f"年利率: {result['annual_rate']:.2f}%")
    lines.append(f"还款方式: {'等额本息' if result['method'] == 'equal_installment' else '等额本金'}")
    lines.append("-" * 60)
    lines.append(f"首月月供: {result['first_month_payment']:,.2f} 元")
    lines.append(f"总利息: {result['total_interest']:,.2f} 元")
    lines.append(f"总还款额: {result['total_payment']:,.2f} 元")
    lines.append("-" * 60)
    lines.append("税费估算:")
    for tax_name, tax_amount in result['taxes'].items():
        lines.append(f"  {tax_name}: {tax_amount:,.2f} 元")
    lines.append(f"  税费合计: {result['total_taxes']:,.2f} 元")
    lines.append("-" * 60)
    lines.append(f"月收入: {result['monthly_income']:,.0f} 元")
    lines.append(f"DTI比率: {result['dti']:.1f}%")
    lines.append(f"压力等级: {result['pressure_level']}")
    lines.append("-" * 60)
    lines.append("建议:")
    lines.append(result['advice'])
    lines.append("=" * 60)
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description='购房测算工具 - 计算月供、税费、现金流压力与购房建议',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''示例:
  python run.py --price 3000000 --income 20000 --area 100 --down-ratio 30
  python run.py --price 3000000 --income 20000 --area 100 --down-payment 1000000 --years 20
  python run.py --price 3000000 --income 20000 --area 100 --rate 4.15 --method equal_principal
  python run.py --price 3000000 --income 20000 --area 100 --json
'''
    )
    
    parser.add_argument('--price', type=float, required=True, help='房屋总价（元）')
    parser.add_argument('--income', type=float, required=True, help='家庭月收入（税后，元）')
    parser.add_argument('--area', type=float, required=True, help='房屋面积（平米）')
    parser.add_argument('--down-ratio', type=float, default=DEFAULT_DOWN_PAYMENT_RATIO * 100,
                       help=f'首付比例（%），默认{DEFAULT_DOWN_PAYMENT_RATIO*100:.0f}%')
    parser.add_argument('--down-payment', type=float, help='首付金额（元），与--down-ratio二选一')
    parser.add_argument('--years', type=int, default=DEFAULT_LOAN_YEARS,
                       help=f'贷款年限（年），默认{DEFAULT_LOAN_YEARS}')
    parser.add_argument('--rate', type=float, default=DEFAULT_LPR + DEFAULT_BP / 100,
                       help=f'年利率（%），默认{DEFAULT_LPR + DEFAULT_BP/100:.2f}%')
    parser.add_argument('--method', choices=['equal_installment', 'equal_principal'],
                       default='equal_installment', help='还款方式，默认等额本息')
    parser.add_argument('--first-house', action='store_true', default=True,
                       help='是否首套房（默认是）')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出')
    
    args = parser.parse_args()
    
    try:
        # 参数校验
        if args.price <= 0:
            raise ValueError("房屋总价必须为正数")
        if args.income <= 0:
            raise ValueError("月收入必须为正数")
        if args.area <= 0:
            raise ValueError("房屋面积必须为正数")
        if args.years <= 0 or args.years > 30:
            raise ValueError("贷款年限必须在1-30年之间")
        if args.rate < 0:
            raise ValueError("利率不能为负数")
        
        # 计算首付
        if args.down_payment is not None:
            if args.down_payment >= args.price:
                raise ValueError("首付金额不能大于或等于房屋总价")
            down_payment = args.down_payment
        else:
            if args.down_ratio <= 0 or args.down_ratio >= 100:
                raise ValueError("首付比例必须在0-100之间")
            down_payment = args.price * args.down_ratio / 100
        
        loan_amount = args.price - down_payment
        
        # 计算月供
        first_month_payment, total_interest, _ = calculate_monthly_payment(
            loan_amount, args.rate, args.years, args.method
        )
        
        # 计算税费
        taxes = calculate_taxes(args.price, args.area, args.first_house)
        total_taxes = sum(taxes.values())
        
        # 评估压力
        dti, pressure_level, pressure_advice = assess_affordability(
            first_month_payment, args.income
        )
        
        # 生成建议
        advice = generate_advice(
            args.price, down_payment, loan_amount, first_month_payment,
            args.income, dti, total_taxes, args.method
        )
        
        # 组装结果
        result = {
            'house_price': args.price,
            'area': args.area,
            'down_payment': down_payment,
            'loan_amount': loan_amount,
            'loan_years': args.years,
            'annual_rate': args.rate,
            'method': args.method,
            'first_month_payment': first_month_payment,
            'total_interest': total_interest,
            'total_payment': loan_amount + total_interest,
            'taxes': taxes,
            'total_taxes': total_taxes,
            'monthly_income': args.income,
            'dti': dti,
            'pressure_level': pressure_level,
            'advice': advice,
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 输出
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_output(result))
            
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"计算失败: {e}", file=sys.stderr)
        sys.exit(1)

def selftest():
    """自检函数 - 验证核心计算逻辑"""
    print("运行自检...")
    
    # 测试1: 等额本息计算
    payment, interest, _ = calculate_monthly_payment(1000000, 4.15, 30, 'equal_installment')
    assert abs(payment - 4861.03) < 1, f"等额本息月供计算错误: {payment}"
    assert interest > 0, "总利息应为正数"
    print(f"✓ 等额本息计算正确: 月供{payment:.2f}元")
    
    # 测试2: 等额本金计算
    payment, interest, _ = calculate_monthly_payment(1000000, 4.15, 30, 'equal_principal')
    assert payment > 6000, f"等额本金首月月供应较高: {payment}"
    print(f"✓ 等额本金计算正确: 首月月供{payment:.2f}元")
    
    # 测试3: 税费计算（动态面积）
    taxes = calculate_taxes(3000000, 100, True)
    assert taxes['契税'] == 45000, f"契税计算错误: {taxes['契税']}"
    assert taxes['维修基金'] == 20000, f"维修基金计算错误: {taxes['维修基金']}"
    print(f"✓ 税费计算正确: 契税{taxes['契税']:.0f}元, 维修基金{taxes['维修基金']:.0f}元")
    
    # 测试4: DTI评估
    dti, level, _ = assess_affordability(5000, 20000)
    assert dti == 25.0, f"DTI计算错误: {dti}"
    assert level == "舒适", f"压力等级错误: {level}"
    print(f"✓ DTI评估正确: {dti:.1f}% -> {level}")
    
    # 测试5: 建议生成
    advice = generate_advice(3000000, 900000, 2100000, 10000, 20000, 50, 100000, 'equal_installment')
    assert len(advice) > 0, "建议不能为空"
    print(f"✓ 建议生成正确: {len(advice)}字符")
    
    # 测试6: 边界条件
    try:
        calculate_monthly_payment(-100, 4.15, 30)
        assert False, "应抛出异常"
    except ValueError:
        print("✓ 边界条件处理正确")
    
    print("所有自检通过!")
    return 0

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        sys.exit(selftest())
    main()
