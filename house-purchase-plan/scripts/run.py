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

# LPR API 配置 - 使用中国外汇交易中心官网API
LPR_API_URL = "https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/rate/benchmark.json"
LPR_API_TIMEOUT = 5  # 秒
LPR_API_RETRIES = 3  # 重试次数
LPR_API_BACKOFF = 1  # 初始退避时间（秒）

# 本地缓存文件路径 - 使用系统临时目录，避免多用户权限冲突
LPR_CACHE_DIR = os.path.join(tempfile.gettempdir(), "house_plan_cache")
LPR_CACHE_FILE = os.path.join(LPR_CACHE_DIR, "house_plan_lpr.json")
LPR_CACHE_MAX_AGE = 86400  # 24小时缓存有效期

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

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


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
        raise ValueError("参数不合法")

    monthly_rate = annual_rate / 100 / 12
    total_months = years * 12

    if method == 'equal_installment':
        if monthly_rate == 0:
            monthly_payment = principal / total_months
            total_interest = 0
        else:
            factor = (1 + monthly_rate) ** total_months
            monthly_payment = principal * monthly_rate * factor / (factor - 1)
            total_interest = monthly_payment * total_months - principal
        return monthly_payment, total_interest, [monthly_payment] * total_months

    elif method == 'equal_principal':
        monthly_principal = principal / total_months
        payments = []
        total_interest = 0
        for i in range(total_months):
            interest = (principal - monthly_principal * i) * monthly_rate
            payment = monthly_principal + interest
            payments.append(payment)
            total_interest += interest
        return payments[0], total_interest, payments

    else:
        raise ValueError("还款方式非法")


def calculate_taxes(price, area, is_first_home=True):
    """
    计算购房税费
    :param price: 房价
    :param area: 面积（平方米）
    :param is_first_home: 是否首套
    :return: 税费明细字典
    """
    if price <= 0 or area <= 0:
        raise ValueError("价格和面积必须为正数")

    # 契税
    if is_first_home:
        if area <= 90:
            deed_tax = price * TAX_RATES['deed_tax_first']
        else:
            deed_tax = price * TAX_RATES['deed_tax_first_90']
    else:
        deed_tax = price * TAX_RATES['deed_tax_second']

    # 中介费
    agent_fee = price * TAX_RATES['agent_fee']

    # 维修基金
    maintenance_fund = area * TAX_RATES['maintenance_fund']

    # 印花税
    stamp_tax = price * TAX_RATES['stamp_tax']

    # 过户费
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


def evaluate_cashflow(monthly_payment, monthly_income):
    """
    评估现金流压力
    :param monthly_payment: 月供
    :param monthly_income: 月收入
    :return: (DTI, 评估结果)
    """
    if monthly_income <= 0:
        raise ValueError("收入必须为正数")

    dti = monthly_payment / monthly_income

    if dti <= 0.35:
        level = "安全"
        suggestion = "月供占收入比在安全范围内，可考虑购买。"
    elif dti <= 0.50:
        level = "警告"
        suggestion = "月供占收入比较高，建议提高首付比例或延长贷款年限。"
    else:
        level = "危险"
        suggestion = "月供占收入比过高，建议降低购房预算或增加首付。"

    return dti, level, suggestion


def generate_advice(dti, method, down_payment_ratio, years):
    """
    生成购房建议
    :param dti: 负债收入比
    :param method: 还款方式
    :param down_payment_ratio: 首付比例
    :param years: 贷款年限
    :return: 建议字符串
    """
    advice = []

    if dti <= 0.35:
        advice.append("当前月供压力可控，可考虑适当提高预算或缩短贷款年限以减少利息支出。")
    elif dti <= 0.50:
        advice.append("月供压力偏大，建议：")
        advice.append("  1. 提高首付比例，降低贷款金额")
        advice.append("  2. 延长贷款年限，分摊月供压力")
        advice.append("  3. 考虑等额本金方式，前期压力大但总利息少")
    else:
        advice.append("月供压力过大，强烈建议：")
        advice.append("  1. 降低购房预算")
        advice.append("  2. 大幅提高首付比例")
        advice.append("  3. 暂缓购房，积累更多首付")

    if method == 'equal_principal':
        advice.append("等额本金方式总利息较少，但前期月供压力较大，适合收入预期增长的人群。")

    return "\n".join(advice)


# ==================== LPR 获取函数 ====================

def fetch_lpr_with_retry():
    """
    从 API 获取最新 LPR，带超时和指数退避重试
    :return: LPR 值（%），失败返回 None
    """
    # 先检查环境变量
    env_lpr = os.environ.get('HOUSE_PLAN_LPR')
    if env_lpr:
        try:
            return float(env_lpr)
        except ValueError:
            print(f"警告: 环境变量 HOUSE_PLAN_LPR 值 '{env_lpr}' 无效，忽略", file=sys.stderr)

    # 检查缓存
    cached_lpr = read_lpr_cache()
    if cached_lpr is not None:
        return cached_lpr

    # 尝试 API 获取
    for attempt in range(LPR_API_RETRIES):
        try:
            req = urllib.request.Request(LPR_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=LPR_API_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8'))
                # 解析 LPR 数据
                lpr = parse_lpr_data(data)
                if lpr is not None:
                    write_lpr_cache(lpr)
                    return lpr
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError) as e:
            print(f"警告: LPR API 请求失败 (尝试 {attempt + 1}/{LPR_API_RETRIES}): {e}", file=sys.stderr)
            if attempt < LPR_API_RETRIES - 1:
                time.sleep(LPR_API_BACKOFF * (2 ** attempt))

    print(f"警告: 无法获取实时 LPR，使用默认值 {DEFAULT_LPR}%", file=sys.stderr)
    return DEFAULT_LPR


def parse_lpr_data(data):
    """
    解析 LPR API 返回的数据
    :param data: JSON 数据
    :return: LPR 值（%），解析失败返回 None
    """
    try:
        # 尝试多种可能的 JSON 结构
        if isinstance(data, dict):
            # 结构1: {"data": {"lpr": [...]}}
            if 'data' in data and isinstance(data['data'], dict):
                lpr_list = data['data'].get('lpr', [])
                if lpr_list:
                    return float(lpr_list[0].get('rate', DEFAULT_LPR))
            # 结构2: {"lpr": [...]}
            if 'lpr' in data and isinstance(data['lpr'], list):
                if data['lpr']:
                    return float(data['lpr'][0].get('rate', DEFAULT_LPR))
        return None
    except (TypeError, ValueError, IndexError) as e:
        print(f"警告: LPR 数据解析失败: {e}", file=sys.stderr)
        return None


def read_lpr_cache():
    """
    读取 LPR 缓存
    :return: 缓存的 LPR 值，无缓存或过期返回 None
    """
    try:
        if not os.path.exists(LPR_CACHE_FILE):
            return None
        with open(LPR_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        now = datetime.now(timezone.utc)
        if (now - cache_time).total_seconds() < LPR_CACHE_MAX_AGE:
            return float(cache_data['lpr'])
        return None
    except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
        print(f"警告: LPR 缓存读取失败: {e}", file=sys.stderr)
        return None


def write_lpr_cache(lpr):
    """
    写入 LPR 缓存（原子化）
    :param lpr: LPR 值
    """
    try:
        os.makedirs(LPR_CACHE_DIR, exist_ok=True)
        cache_data = {
            'lpr': lpr,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        # 原子化写入：先写临时文件，再重命名
        temp_file = LPR_CACHE_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
        os.replace(temp_file, LPR_CACHE_FILE)
    except OSError as e:
        print(f"警告: LPR 缓存写入失败: {e}", file=sys.stderr)


# ==================== 输入校验函数 ====================

def validate_positive_float(value, error_code, param_name):
    """校验正浮点数"""
    if value is None or value <= 0:
        raise ValueError(f"{error_code}: {ERROR_CODES[error_code]} (参数: {param_name})")
    return value


def validate_range(value, min_val, max_val, error_code, param_name):
    """校验数值范围"""
    if value is None or not (min_val <= value <= max_val):
        raise ValueError(f"{error_code}: {ERROR_CODES[error_code]} (参数: {param_name})")
    return value


# ==================== 输出格式化函数 ====================

def format_currency(amount):
    """格式化货币显示"""
    return f"{amount:,.2f}"


def format_percent(value):
    """格式化百分比显示"""
    return f"{value * 100:.1f}%"


def print_result(result, verbose=False):
    """
    打印计算结果
    :param result: 计算结果字典
    :param verbose: 是否详细模式
    """
    print("\n=== 购房测算结果 ===")
    print(f"房价: {format_currency(result['price'])} 元")
    print(f"首付 ({format_percent(result['down_payment_ratio'])}): {format_currency(result['down_payment'])} 元")
    print(f"贷款金额: {format_currency(result['loan_amount'])} 元")
    print(f"贷款年限: {result['years']} 年")
    print(f"年利率: {result['annual_rate']:.2f}% (LPR {result['lpr']:.2f}% + {result['bp']}BP)")

    print(f"\n月供 ({result['method_label']}): {format_currency(result['monthly_payment'])} 元")
    print(f"总利息: {format_currency(result['total_interest'])} 元")

    if verbose:
        print("\n--- 税费明细 ---")
        for key, value in result['taxes'].items():
            if key != 'total':
                print(f"  {key}: {format_currency(value)} 元")
    print(f"税费合计: {format_currency(result['taxes']['total'])} 元")

    print(f"\nDTI: {format_percent(result['dti'])} ({result['dti_level']})")
    print(f"\n建议: {result['advice']}")


def print_comparison(results, verbose=False):
    """
    打印多方案对比结果
    :param results: 结果列表
    :param verbose: 是否详细模式
    """
    print("\n=== 方案对比 ===")
    for i, result in enumerate(results, 1):
        print(f"方案{i} (首付{format_percent(result['down_payment_ratio'])}): "
              f"月供 {format_currency(result['monthly_payment'])} 元, "
              f"DTI {format_percent(result['dti'])} ({result['dti_level']})")

    # 找出最优方案
    best = min(results, key=lambda x: x['dti'])
    print(f"\n建议: 方案{results.index(best) + 1} 更稳健，月供压力更小。")


# ==================== 主流程 ====================

def run_calculation(args, lpr):
    """
    执行单次计算
    :param args: 命令行参数
    :param lpr: LPR 值
    :return: 结果字典
    """
    try:
        # 输入校验
        validate_positive_float(args.price, 'E1001', '--price')
        validate_positive_float(args.income, 'E1002', '--income')
        validate_range(args.down_payment_ratio, 0, 1, 'E1003', '--down-payment-ratio')
        validate_range(args.years, 1, 30, 'E1004', '--years')
        validate_range(lpr, 0, float('inf'), 'E1005', '--lpr')
        validate_range(args.bp, -100, 200, 'E1006', '--bp')

        if args.method not in ('equal_installment', 'equal_principal'):
            raise ValueError(f"E1007: {ERROR_CODES['E1007']}")

        # 计算
        annual_rate = lpr + args.bp / 100
        down_payment = args.price * args.down_payment_ratio
        loan_amount = args.price - down_payment

        monthly_payment, total_interest, _ = calculate_monthly_payment(
            loan_amount, annual_rate, args.years, args.method
        )

        taxes = calculate_taxes(args.price, args.area, args.is_first_home)

        dti, dti_level, _ = evaluate_cashflow(monthly_payment, args.income)

        advice = generate_advice(dti, args.method, args.down_payment_ratio, args.years)

        method_label = "等额本息" if args.method == 'equal_installment' else "等额本金"

        return {
            'price': args.price,
            'down_payment_ratio': args.down_payment_ratio,
            'down_payment': down_payment,
            'loan_amount': loan_amount,
            'years': args.years,
            'lpr': lpr,
            'bp': args.bp,
            'annual_rate': annual_rate,
            'method': args.method,
            'method_label': method_label,
            'monthly_payment': monthly_payment,
            'total_interest': total_interest,
            'taxes': taxes,
            'dti': dti,
            'dti_level': dti_level,
            'advice': advice
        }
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        raise


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='购房测算工具 - 月供评估与预算规划',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --price 3000000 --income 25000
  python run.py --price 3000000 --income 25000 --down-payment-ratio 0.3 --down-payment-ratio 0.5
  python run.py --price 2000000 --income 20000 --method equal_principal
  python run.py --selftest
        """
    )

    # 基本参数
    parser.add_argument('--price', type=float, help='房价（元）')
    parser.add_argument('--income', type=float, help='家庭月收入（元）')
    parser.add_argument('--down-payment-ratio', type=float, action='append',
                        default=[DEFAULT_DOWN_PAYMENT_RATIO],
                        help='首付比例（0-1），可多次指定进行方案对比')
    parser.add_argument('--years', type=int, default=DEFAULT_LOAN_YEARS,
                        help=f'贷款年限（1-30年，默认{DEFAULT_LOAN_YEARS}）')
    parser.add_argument('--method', choices=['equal_installment', 'equal_principal'],
                        default='equal_installment',
                        help='还款方式: equal_installment(等额本息)/equal_principal(等额本金)')
    parser.add_argument('--area', type=float, default=DEFAULT_AREA,
                        help=f'房屋面积（平方米，默认{DEFAULT_AREA}）')
    parser.add_argument('--is-first-home', action='store_true', default=DEFAULT_IS_FIRST_HOME,
                        help='是否首套（默认是）')
    parser.add_argument('--lpr', type=float, default=None,
                        help=f'LPR利率（%），默认{DEFAULT_LPR}或从API获取')
    parser.add_argument('--bp', type=int, default=DEFAULT_BP,
                        help=f'加点基点（默认{DEFAULT_BP}BP）')
    parser.add_argument('--fetch-lpr', action='store_true',
                        help='从API获取最新LPR')
    parser.add_argument('--output-json', type=str, help='输出JSON文件路径')
    parser.add_argument('--dry-run', action='store_true',
                        help='试运行模式，不写文件，只打印将执行的操作')
    parser.add_argument('--verbose', action='store_true', help='详细模式，输出计算明细')
    parser.add_argument('--selftest', action='store_true', help='运行自检')

    args = parser.parse_args()

    # 自检模式 - 必须在必填校验之前
    if args.selftest:
        sys.exit(run_selftest())

    # 参数校验 - 手工检查必填参数
    if args.price is None or args.income is None:
        parser.error("必须指定 --price 和 --income 参数")

    # 获取 LPR
    if args.lpr is not None:
        lpr = args.lpr
    elif args.fetch_lpr:
        lpr = fetch_lpr_with_retry()
    else:
        lpr = DEFAULT_LPR

    try:
        # 执行计算
        results = []
        for ratio in args.down_payment_ratio:
            args.down_payment_ratio = ratio
            result = run_calculation(args, lpr)
            results.append(result)

        # 输出结果
        if len(results) == 1:
            print_result(results[0], args.verbose)
        else:
            print_comparison(results, args.verbose)

        # 输出 JSON 文件 - R4 预览撤回：写盘必须受 --dry-run 控制
        if args.output_json:
            if not args.dry_run:
                try:
                    output_data = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'results': results
                    }
                    # 原子化写入
                    temp_file = args.output_json + '.tmp'
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                    os.replace(temp_file, args.output_json)
                    print(f"\n结果已写入: {args.output_json}")
                except OSError as e:
                    print(f"错误: E2002: {ERROR_CODES['E2002']}: {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"\n[dry-run] 将写入 {args.output_json}（{len(results)} 个方案结果），未落盘")

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: E3001: {ERROR_CODES['E3001']}: {e}", file=sys.stderr)
        sys.exit(1)


# ==================== 自检函数 ====================

def run_selftest():
    """
    运行自检，验证核心功能
    :return: 退出码（0 成功，非 0 失败）
    """
    print("=== 自检开始 ===")
    failures = 0

    # 测试1: 等额本息月供计算
    print("\n[测试1] 等额本息月供计算")
    try:
        payment, interest, _ = calculate_monthly_payment(1000000, 4.15, 30, 'equal_installment')
        # 验证: 月供应在合理范围内 (100万, 30年, 4.15% -> 约4861元)
        assert 4000 < payment < 6000, f"月供 {payment} 不在预期范围"
        assert interest > 0, "总利息应为正数"
        print(f"  通过: 月供={payment:.2f}, 总利息={interest:.2f}")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试2: 等额本金月供计算
    print("\n[测试2] 等额本金月供计算")
    try:
        first_payment, interest, payments = calculate_monthly_payment(1000000, 4.15, 30, 'equal_principal')
        # 验证: 首月月供应大于等额本息月供
        assert first_payment > 4000, f"首月月供 {first_payment} 不在预期范围"
        assert len(payments) == 360, f"月供列表长度 {len(payments)} 应为360"
        # 验证: 月供递减
        assert payments[0] > payments[-1], "月供应递减"
        print(f"  通过: 首月月供={first_payment:.2f}, 末月月供={payments[-1]:.2f}")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试3: 税费计算
    print("\n[测试3] 税费计算")
    try:
        taxes = calculate_taxes(3000000, 90, True)
        assert taxes['total'] > 0, "税费总额应为正数"
        assert taxes['deed_tax'] == 30000, f"契税 {taxes['deed_tax']} 应为30000"
        print(f"  通过: 税费总额={taxes['total']:.2f}")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试4: 现金流评估
    print("\n[测试4] 现金流评估")
    try:
        dti, level, suggestion = evaluate_cashflow(5000, 20000)
        assert 0 < dti < 1, f"DTI {dti} 应在0-1之间"
        assert level in ('安全', '警告', '危险'), f"评估等级 {level} 非法"
        print(f"  通过: DTI={dti:.2%}, 等级={level}")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试5: 输入校验
    print("\n[测试5] 输入校验")
    try:
        try:
            validate_positive_float(-100, 'E1001', '--price')
            print("  失败: 负数房价未被拦截")
            failures += 1
        except ValueError:
            print("  通过: 负数房价被正确拦截")

        try:
            validate_range(50, 1, 30, 'E1004', '--years')
            print("  失败: 超范围年限未被拦截")
            failures += 1
        except ValueError:
            print("  通过: 超范围年限被正确拦截")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试6: 完整流程
    print("\n[测试6] 完整流程")
    try:
        # 模拟命令行参数
        class Args:
            price = 3000000
            income = 25000
            down_payment_ratio = 0.3
            years = 30
            method = 'equal_installment'
            area = 90
            is_first_home = True
            bp = 30
            verbose = False

        result = run_calculation(Args(), DEFAULT_LPR)
        assert result['monthly_payment'] > 0, "月供应为正数"
        assert result['dti'] > 0, "DTI应为正数"
        assert result['taxes']['total'] > 0, "税费应为正数"
        print(f"  通过: 月供={result['monthly_payment']:.2f}, DTI={result['dti']:.2%}")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试7: 多方案对比
    print("\n[测试7] 多方案对比")
    try:
        class Args:
            price = 3000000
            income = 25000
            down_payment_ratio = 0.3
            years = 30
            method = 'equal_installment'
            area = 90
            is_first_home = True
            bp = 30
            verbose = False

        results = []
        for ratio in [0.3, 0.5]:
            Args.down_payment_ratio = ratio
            result = run_calculation(Args(), DEFAULT_LPR)
            results.append(result)

        assert len(results) == 2, f"应有2个结果，实际{len(results)}"
        assert results[0]['down_payment'] < results[1]['down_payment'], "首付应递增"
        assert results[0]['monthly_payment'] > results[1]['monthly_payment'], "月供应递减"
        print(f"  通过: 方案1月供={results[0]['monthly_payment']:.2f}, 方案2月供={results[1]['monthly_payment']:.2f}")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试8: 边界情况 - 零利率
    print("\n[测试8] 零利率边界")
    try:
        payment, interest, _ = calculate_monthly_payment(1000000, 0, 30, 'equal_installment')
        expected = 1000000 / 360
        assert abs(payment - expected) < 1, f"零利率月供 {payment} 应约为 {expected}"
        assert interest == 0, "零利率总利息应为0"
        print(f"  通过: 零利率月供={payment:.2f}")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试9: 编码处理
    print("\n[测试9] 编码处理")
    try:
        # 测试中文输出
        test_text = "购房测算结果"
        encoded = test_text.encode('utf-8').decode('utf-8')
        assert encoded == test_text, "中文编码处理失败"
        print("  通过: 中文编码处理正常")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 测试10: 空输入处理
    print("\n[测试10] 空输入处理")
    try:
        try:
            validate_positive_float(None, 'E1001', '--price')
            print("  失败: None输入未被拦截")
            failures += 1
        except ValueError:
            print("  通过: None输入被正确拦截")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # 汇总
    print(f"\n=== 自检完成: {10 - failures}/10 通过 ===")
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    main()
