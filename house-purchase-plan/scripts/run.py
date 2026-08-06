#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
购房测算工具 - 月供评估与预算规划
功能：计算月供、税费、现金流压力，生成购房建议
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ==================== 常量配置 ====================
DEFAULT_LPR = 3.85  # 5年期以上LPR（%）
DEFAULT_BP = 30     # 默认加点（基点）
DEFAULT_LOAN_YEARS = 30
DEFAULT_DOWN_PAYMENT_RATIO = 0.30
DEFAULT_AREA = 90.0
DEFAULT_IS_FIRST_HOME = True

# 税费参数（按常规标准估算）
TAX_RATES = {
    'deed_tax_first': 0.01,     # 契税（首套90平以下）
    'deed_tax_first_90': 0.015, # 契税（首套90平以上）
    'deed_tax_second': 0.02,    # 契税（二套）
    'agent_fee': 0.01,          # 中介费
    'maintenance_fund': 200,    # 维修基金（元/平）
    'stamp_tax': 0.0005,        # 印花税
    'transfer_fee': 80,         # 过户费（固定）
    'other_fee': 2000           # 其他杂费（评估、公证等）
}

# LPR API 配置
LPR_API_URL = "https://api.example.com/lpr"  # 示例API，实际使用需替换
LPR_API_TIMEOUT = 5  # 秒
LPR_API_RETRIES = 3  # 重试次数
LPR_API_BACKOFF = 1  # 初始退避时间（秒）

# 错误码定义
ERROR_CODES = {
    'E1001': '房价必须为正数',
    'E1002': '收入必须为正数',
    'E1003': '首付比例必须在0-1之间',
    'E1004': '贷款年限必须在1-30年',
    'E1005': 'LPR不能为负数',
    'E1006': '基点必须在-100到200之间',
    'E1007': '还款方式非法',
    'E2001': 'LPR API请求失败',
    'E2002': '输出文件写入失败',
    'E3001': '内部计算错误'
}


# ==================== 核心计算函数 ====================

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
            monthly_payment = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
            total_interest = monthly_payment * months - principal
        payment_list = [monthly_payment] * months
    elif method == 'equal_principal':
        monthly_principal = principal / months
        payment_list = []
        total_interest = 0
        for i in range(months):
            interest = (principal - monthly_principal * i) * monthly_rate
            payment = monthly_principal + interest
            payment_list.append(payment)
            total_interest += interest
        monthly_payment = payment_list[0]
    else:
        raise ValueError("还款方式非法")
    
    return monthly_payment, total_interest, payment_list


def calculate_taxes(price, area, is_first_home=True):
    """
    计算税费
    :param price: 房屋总价（万元）
    :param area: 房屋面积（平方米）
    :param is_first_home: 是否首套房
    :return: 税费字典
    """
    price_yuan = price * 10000  # 转换为元
    
    # 契税
    if is_first_home:
        if area <= 90:
            deed_tax = price_yuan * TAX_RATES['deed_tax_first']
        else:
            deed_tax = price_yuan * TAX_RATES['deed_tax_first_90']
    else:
        deed_tax = price_yuan * TAX_RATES['deed_tax_second']
    
    # 中介费
    agent_fee = price_yuan * TAX_RATES['agent_fee']
    
    # 维修基金
    maintenance_fund = area * TAX_RATES['maintenance_fund']
    
    # 印花税
    stamp_tax = price_yuan * TAX_RATES['stamp_tax']
    
    # 过户费（固定）
    transfer_fee = TAX_RATES['transfer_fee']
    
    # 其他杂费
    other_fee = TAX_RATES['other_fee']
    
    total = deed_tax + agent_fee + maintenance_fund + stamp_tax + transfer_fee + other_fee
    
    return {
        'deed_tax': round(deed_tax, 2),
        'agent_fee': round(agent_fee, 2),
        'maintenance_fund': round(maintenance_fund, 2),
        'stamp_tax': round(stamp_tax, 2),
        'transfer_fee': transfer_fee,
        'other_fee': other_fee,
        'total': round(total, 2)
    }


def assess_cashflow(monthly_payment, monthly_income):
    """
    评估现金流压力
    :param monthly_payment: 月供
    :param monthly_income: 家庭月收入
    :return: 现金流评估字典
    """
    if monthly_income <= 0:
        raise ValueError("收入必须为正数")
    
    dti = monthly_payment / monthly_income
    
    if dti <= 0.3:
        rating = "safe"
        suggestion = "月供占收入比例较低，财务压力较小"
    elif dti <= 0.5:
        rating = "warning"
        suggestion = "月供占收入比例适中，建议预留应急资金"
    else:
        rating = "danger"
        suggestion = "月供占收入比例过高，建议考虑增加首付或延长贷款期限"
    
    return {
        'dti': round(dti, 2),
        'rating': rating,
        'suggestion': suggestion
    }


def generate_advice(dti_rating, down_payment_ratio, loan_years, lpr, bp):
    """
    生成购房建议
    :param dti_rating: 现金流评级
    :param down_payment_ratio: 首付比例
    :param loan_years: 贷款年限
    :param lpr: LPR
    :param bp: 基点
    :return: 建议字符串
    """
    advice_parts = []
    
    if dti_rating == "danger":
        advice_parts.append("当前月供压力较大，建议：")
        advice_parts.append("1. 增加首付比例，降低贷款金额")
        advice_parts.append("2. 延长贷款年限，分摊月供压力")
        advice_parts.append("3. 考虑选择更小的户型或更低总价的房源")
    elif dti_rating == "warning":
        advice_parts.append("当前月供压力适中，建议：")
        advice_parts.append("1. 预留3-6个月月供作为应急资金")
        advice_parts.append("2. 关注利率变化，适时考虑提前还款")
    else:
        advice_parts.append("当前月供压力较小，建议：")
        advice_parts.append("1. 可考虑适当提高贷款额度或缩短贷款年限")
        advice_parts.append("2. 关注利率变化，把握利率下行机会")
    
    # 利率建议
    effective_rate = lpr + bp / 100
    if effective_rate < 4:
        advice_parts.append(f"当前实际利率{effective_rate:.2f}%处于较低水平，适合贷款购房")
    elif effective_rate < 5:
        advice_parts.append(f"当前实际利率{effective_rate:.2f}%处于中等水平，可考虑固定利率锁定")
    else:
        advice_parts.append(f"当前实际利率{effective_rate:.2f}%较高，建议谨慎评估还款能力")
    
    return " ".join(advice_parts)


def fetch_lpr():
    """
    从API获取最新LPR（含超时与重试）
    :return: LPR值（float），失败返回None
    """
    for attempt in range(LPR_API_RETRIES):
        try:
            req = urllib.request.Request(LPR_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=LPR_API_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8'))
                lpr = float(data.get('lpr', DEFAULT_LPR))
                return lpr
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt < LPR_API_RETRIES - 1:
                time.sleep(LPR_API_BACKOFF * (2 ** attempt))
            else:
                return None
    return None


def compare_scenarios(base_result, compare_json):
    """
    对比方案
    :param base_result: 基准方案结果
    :param compare_json: 对比方案JSON字符串
    :return: 对比结果列表
    """
    try:
        compare_params = json.loads(compare_json)
    except json.JSONDecodeError:
        raise ValueError("对比方案JSON格式错误")
    
    results = [{"name": "基准方案", **base_result}]
    
    for i, params in enumerate(compare_params, 1):
        # 使用基准参数并覆盖对比参数
        merged_params = {**base_result['input'], **params}
        result = run_calculation(merged_params)
        results.append({"name": f"方案{i}", **result})
    
    return results


def run_calculation(params):
    """
    执行完整计算流程
    :param params: 参数字典
    :return: 结果字典
    """
    # 参数校验
    price = params.get('price')
    income = params.get('income')
    if price is None or income is None:
        raise ValueError("房价和收入为必填参数")
    
    if price <= 0:
        raise ValueError(ERROR_CODES['E1001'])
    if income <= 0:
        raise ValueError(ERROR_CODES['E1002'])
    
    down_payment_ratio = params.get('down_payment_ratio', DEFAULT_DOWN_PAYMENT_RATIO)
    if not 0 <= down_payment_ratio <= 1:
        raise ValueError(ERROR_CODES['E1003'])
    
    loan_years = params.get('loan_years', DEFAULT_LOAN_YEARS)
    if not 1 <= loan_years <= 30:
        raise ValueError(ERROR_CODES['E1004'])
    
    lpr = params.get('lpr', DEFAULT_LPR)
    if lpr < 0:
        raise ValueError(ERROR_CODES['E1005'])
    
    bp = params.get('bp', DEFAULT_BP)
    if not -100 <= bp <= 200:
        raise ValueError(ERROR_CODES['E1006'])
    
    method = params.get('method', 'equal_installment')
    if method not in ['equal_installment', 'equal_principal']:
        raise ValueError(ERROR_CODES['E1007'])
    
    area = params.get('area', DEFAULT_AREA)
    is_first_home = params.get('is_first_home', DEFAULT_IS_FIRST_HOME)
    
    # 计算贷款金额
    loan_amount = price * 10000 * (1 - down_payment_ratio)
    
    # 计算月供
    annual_rate = lpr + bp / 100
    monthly_payment, total_interest, payment_list = calculate_monthly_payment(
        loan_amount, annual_rate, loan_years, method
    )
    
    # 计算税费
    taxes = calculate_taxes(price, area, is_first_home)
    
    # 评估现金流
    cashflow = assess_cashflow(monthly_payment, income)
    
    # 生成建议
    advice = generate_advice(cashflow['rating'], down_payment_ratio, loan_years, lpr, bp)
    
    return {
        'input': {
            'price': price,
            'income': income,
            'down_payment_ratio': down_payment_ratio,
            'loan_years': loan_years,
            'lpr': lpr,
            'bp': bp,
            'method': method,
            'area': area,
            'is_first_home': is_first_home
        },
        'result': {
            'loan_amount': round(loan_amount, 2),
            'monthly_payment': round(monthly_payment, 2),
            'total_interest': round(total_interest, 2),
            'total_payment': round(loan_amount + total_interest, 2),
            'taxes': taxes,
            'cashflow': cashflow,
            'advice': advice
        }
    }


def selftest():
    """
    自检函数：验证核心函数正确性
    :return: 退出码（0成功，非0失败）
    """
    print("开始自检...")
    
    # 测试1：等额本息月供计算
    try:
        monthly_payment, total_interest, _ = calculate_monthly_payment(1000000, 4.15, 30, 'equal_installment')
        assert abs(monthly_payment - 4861.03) < 1, f"等额本息月供计算错误: {monthly_payment}"
        print("✓ 等额本息月供计算正确")
    except AssertionError as e:
        print(f"✗ 等额本息月供计算失败: {e}")
        return 1
    
    # 测试2：等额本金月供计算
    try:
        monthly_payment, total_interest, _ = calculate_monthly_payment(1000000, 4.15, 30, 'equal_principal')
        assert abs(monthly_payment - 6236.11) < 1, f"等额本金首月月供计算错误: {monthly_payment}"
        print("✓ 等额本金月供计算正确")
    except AssertionError as e:
        print(f"✗ 等额本金月供计算失败: {e}")
        return 1
    
    # 测试3：税费计算
    try:
        taxes = calculate_taxes(300, 90, True)
        assert abs(taxes['deed_tax'] - 30000) < 1, f"契税计算错误: {taxes['deed_tax']}"
        assert abs(taxes['agent_fee'] - 30000) < 1, f"中介费计算错误: {taxes['agent_fee']}"
        print("✓ 税费计算正确")
    except AssertionError as e:
        print(f"✗ 税费计算失败: {e}")
        return 1
    
    # 测试4：现金流评估
    try:
        cashflow = assess_cashflow(5000, 20000)
        assert cashflow['dti'] == 0.25, f"DTI计算错误: {cashflow['dti']}"
        assert cashflow['rating'] == 'safe', f"评级错误: {cashflow['rating']}"
        print("✓ 现金流评估正确")
    except AssertionError as e:
        print(f"✗ 现金流评估失败: {e}")
        return 1
    
    # 测试5：完整流程
    try:
        params = {
            'price': 300,
            'income': 20000,
            'down_payment_ratio': 0.3,
            'loan_years': 30,
            'lpr': 3.85,
            'bp': 30,
            'method': 'equal_installment',
            'area': 90,
            'is_first_home': True
        }
        result = run_calculation(params)
        assert result['result']['monthly_payment'] > 0, "月供计算错误"
        assert result['result']['taxes']['total'] > 0, "税费计算错误"
        assert result['result']['cashflow']['dti'] > 0, "DTI计算错误"
        print("✓ 完整流程计算正确")
    except AssertionError as e:
        print(f"✗ 完整流程计算失败: {e}")
        return 1
    
    # 测试6：参数校验
    try:
        params = {'price': -100, 'income': 20000}
        run_calculation(params)
        print("✗ 参数校验失败：应抛出异常")
        return 1
    except ValueError as e:
        assert str(e) == ERROR_CODES['E1001'], f"错误码不匹配: {e}"
        print("✓ 参数校验正确")
    
    print("所有自检通过！")
    return 0


def main():
    parser = argparse.ArgumentParser(description='购房测算工具 - 月供评估与预算规划')
    parser.add_argument('--price', type=float, help='房屋总价（万元）')
    parser.add_argument('--income', type=float, help='家庭月收入（元）')
    parser.add_argument('--down-payment-ratio', type=float, default=DEFAULT_DOWN_PAYMENT_RATIO, help='首付比例（0-1）')
    parser.add_argument('--loan-years', type=int, default=DEFAULT_LOAN_YEARS, help='贷款年限（年）')
    parser.add_argument('--lpr', type=float, default=DEFAULT_LPR, help='5年期以上LPR（%）')
    parser.add_argument('--bp', type=int, default=DEFAULT_BP, help='利率加点（基点）')
    parser.add_argument('--method', type=str, default='equal_installment', choices=['equal_installment', 'equal_principal'], help='还款方式')
    parser.add_argument('--area', type=float, default=DEFAULT_AREA, help='房屋面积（平方米）')
    parser.add_argument('--is-first-home', type=bool, default=DEFAULT_IS_FIRST_HOME, help='是否首套房')
    parser.add_argument('--compare', type=str, help='对比方案JSON字符串')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        sys.exit(selftest())
    
    # 检查必填参数
    if args.price is None or args.income is None:
        parser.error("--price 和 --income 为必填参数")
    
    # 获取LPR
    lpr = args.lpr
    lpr_source = "default"
    if args.lpr == DEFAULT_LPR:  # 用户未指定LPR时尝试获取
        fetched_lpr = fetch_lpr()
        if fetched_lpr is not None:
            lpr = fetched_lpr
            lpr_source = "api"
        else:
            print("警告: LPR API不可用，使用默认值", file=sys.stderr)
    
    # 构建参数
    params = {
        'price': args.price,
        'income': args.income,
        'down_payment_ratio': args.down_payment_ratio,
        'loan_years': args.loan_years,
        'lpr': lpr,
        'bp': args.bp,
        'method': args.method,
        'area': args.area,
        'is_first_home': args.is_first_home
    }
    
    try:
        # 执行计算
        result = run_calculation(params)
        
        # 添加元数据
        output = {
            'meta': {
                'version': '3.0.0',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'lpr_source': lpr_source
            },
            **result
        }
        
        # 方案对比
        if args.compare:
            try:
                compare_results = compare_scenarios(result, args.compare)
                output['comparison'] = compare_results
            except ValueError as e:
                print(f"错误: {e}", file=sys.stderr)
                sys.exit(1)
        
        # 输出
        output_json = json.dumps(output, ensure_ascii=False, indent=2)
        
        if args.output:
            # 原子化写入文件
            try:
                fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(args.output) or '.')
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(output_json)
                os.replace(temp_path, args.output)
            except (OSError, IOError) as e:
                print(f"错误: {ERROR_CODES['E2002']}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output_json)
    
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {ERROR_CODES['E3001']}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
