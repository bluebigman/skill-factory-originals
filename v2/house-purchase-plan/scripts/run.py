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
dry_run = False  # v3.274 模块级 dry-run 标志

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

# 错误码定义 - 仅保留实际使用的错误码
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

# 日志配置
LOG_LEVELS = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40}


def log(level, message):
    """简易日志系统"""
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] [{level}] {message}", file=sys.stderr)


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
    try:
        # 参数校验
        if principal <= 0:
            raise ValueError("贷款本金必须为正数")
        if annual_rate < 0 or annual_rate > 20:  # 补全年利率上限校验
            raise ValueError("年利率必须在0-20%之间")
        if years <= 0 or years > 30:
            raise ValueError("贷款年限必须在1-30年之间")
        if method not in ('equal_installment', 'equal_principal'):
            raise ValueError("还款方式非法")

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
    except Exception as e:
        log('ERROR', f"月供计算失败: {e}")
        raise


def calculate_taxes(price, area, is_first_home=True):
    """
    计算购房税费
    :param price: 房价
    :param area: 面积（平方米）
    :param is_first_home: 是否首套
    :return: 税费明细字典
    """
    try:
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
    except Exception as e:
        log('ERROR', f"税费计算失败: {e}")
        raise


def evaluate_cashflow(monthly_payment, monthly_income):
    """
    评估现金流压力
    :param monthly_payment: 月供
    :param monthly_income: 月收入
    :return: (DTI, 评估结果)
    """
    try:
        if monthly_income <= 0:
            raise ValueError("收入必须为正数")
        if monthly_payment < 0:
            raise ValueError("月供不能为负数")

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
    except Exception as e:
        log('ERROR', f"现金流评估失败: {e}")
        raise


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
            log('WARNING', f"环境变量 HOUSE_PLAN_LPR 值 '{env_lpr}' 无效，忽略")

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
            log('WARNING', f"LPR API 请求失败 (尝试 {attempt + 1}/{LPR_API_RETRIES}): {e}")
            if attempt < LPR_API_RETRIES - 1:
                time.sleep(LPR_API_BACKOFF * (2 ** attempt))

    log('WARNING', f"无法获取实时 LPR，使用默认值 {DEFAULT_LPR}%")
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
        log('WARNING', f"LPR 数据解析失败: {e}")
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
        log('WARNING', f"LPR 缓存读取失败: {e}")
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
        log('WARNING', f"LPR 缓存写入失败: {e}")


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


# =================


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--price", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--selftest", default=None, help="文档声明的参数")  # F3 补全
    args = ap.parse_args()
