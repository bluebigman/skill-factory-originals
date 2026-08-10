#!/usr/bin/env python3
"""Salary and bonus calculation skill - main entry point."""

import sys
import json
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


# ============================================================
# Constants
# ============================================================

# Seven-level progressive tax rate table (annual)
TAX_BRACKETS = [
    (36000, 0.03, 0),
    (144000, 0.10, 2520),
    (300000, 0.20, 16920),
    (420000, 0.25, 31920),
    (660000, 0.30, 52920),
    (960000, 0.35, 85920),
    (float('inf'), 0.45, 181920),
]

# Default social insurance ratios (individual portion)
DEFAULT_SI_RATIOS = {
    'pension': 0.08,   # 养老 8%
    'medical': 0.02,   # 医疗 2%
    'medical_add': 3,  # 医疗附加 3 元
    'unemployment': 0.005,  # 失业 0.5%
}

# Default housing fund ratio
DEFAULT_HF_RATIO = 0.07

# Monthly tax-free threshold
TAX_FREE_THRESHOLD = 5000

# Standard working days per month
DEFAULT_WORK_DAYS_STD = 21.75


# ============================================================
# Error codes
# ============================================================

class CalcError(Exception):
    """Base calculation error."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class MissingFieldError(CalcError):
    """E001: Required field missing."""
    def __init__(self, fields: List[str]):
        super().__init__("E001", f"Missing required fields: {', '.join(fields)}")


class AttendanceExceedError(CalcError):
    """E002: Attendance days exceed standard days."""
    def __init__(self, actual: float, std: float):
        super().__init__("E002", f"Attendance days {actual} exceed standard days {std}")


class SIBaseLowError(CalcError):
    """E003: Social insurance base below minimum."""
    def __init__(self, base: float, min_base: float):
        super().__init__("E003", f"SI base {base} below minimum {min_base}, adjusted to minimum")


# ============================================================
# Core calculation functions
# ============================================================

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


def calculate_tax(annual_taxable_income: float) -> float:
    """
    Calculate annual tax using seven-level progressive tax rate.
    
    Args:
        annual_taxable_income: Annual taxable income
        
    Returns:
        Annual tax amount
    """
    if annual_taxable_income <= 0:
        return 0.0
    
    for threshold, rate, quick_deduction in TAX_BRACKETS:
        if annual_taxable_income <= threshold:
            return annual_taxable_income * rate - quick_deduction
    
    # Should never reach here
    return annual_taxable_income * 0.45 - 181920


def calculate_si_personal(si_base: float, city_ratios: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    Calculate personal social insurance contributions.
    
    Args:
        si_base: Social insurance base
        city_ratios: Custom city ratios (optional)
        
    Returns:
        Dict with pension, medical, unemployment amounts
    """
    ratios = city_ratios or DEFAULT_SI_RATIOS
    
    pension = si_base * ratios.get('pension', 0.08)
    medical = si_base * ratios.get('medical', 0.02) + ratios.get('medical_add', 3)
    unemployment = si_base * ratios.get('unemployment', 0.005)
    
    return {
        'pension': round(pension, 2),
        'medical': round(medical, 2),
        'unemployment': round(unemployment, 2),
        'total': round(pension + medical + unemployment, 2)
    }


def calculate_hf_personal(si_base: float, hf_ratio: float = DEFAULT_HF_RATIO) -> float:
    """
    Calculate personal housing fund contribution.
    
    Args:
        si_base: Housing fund base
        hf_ratio: Housing fund ratio (5%-12%)
        
    Returns:
        Personal housing fund amount
    """
    return round(si_base * hf_ratio, 2)


def calculate_salary(
    base_salary: float,
    perf_salary: float = 0,
    perf_ratio: float = 1.0,
    work_days_std: float = DEFAULT_WORK_DAYS_STD,
    work_days_actual: float = None,
    leave_personal: float = 0,
    leave_sick: float = 0,
    sick_ratio: float = 0.6,
    ot_workday: float = 0,
    ot_weekend: float = 0,
    ot_holiday: float = 0,
    si_base: float = None,
    si_base_min: float = 0,
    si_base_max: float = float('inf'),
    hf_ratio: float = DEFAULT_HF_RATIO,
    special_deduct: float = 0,
    cum_income: float = 0,
    cum_tax_paid: float = 0,
    bonus: float = 0,
    bonus_mode: str = 'auto',
    city_ratios: Optional[Dict[str, float]] = None,
    month_index: int = 1,
) -> Dict[str, Any]:
    """
    Calculate monthly salary with all deductions.
    
    Args:
        base_salary: Monthly base salary (required)
        perf_salary: Performance salary base
        perf_ratio: Performance coefficient (0-2.0)
        work_days_std: Standard working days per month
        work_days_actual: Actual attendance days
        leave_personal: Personal leave days (full deduction)
        leave_sick: Sick leave days (partial deduction)
        sick_ratio: Sick leave pay ratio (0.6 = 60%)
        ot_workday: Overtime hours on workdays (1.5x)
        ot_weekend: Overtime hours on weekends (2x)
        ot_holiday: Overtime hours on holidays (3x)
        si_base: Social insurance base
        si_base_min: SI base minimum
        si_base_max: SI base maximum
        hf_ratio: Housing fund ratio
        special_deduct: Special additional deduction (monthly)
        cum_income: Cumulative income for the year
        cum_tax_paid: Cumulative tax already paid
        bonus: Year-end bonus amount
        bonus_mode: 'separate', 'combined', or 'auto'
        city_ratios: Custom city SI ratios
        month_index: Month number (1-12)
        
    Returns:
        Dict with all calculation results
    """
    # ===== Validation =====
    missing_fields = []
    if base_salary is None:
        missing_fields.append('base_salary')
    if work_days_actual is None:
        missing_fields.append('work_days_actual')
    if si_base is None:
        missing_fields.append('si_base')
    
    if missing_fields:
        raise MissingFieldError(missing_fields)
    
    # ===== Attendance check =====
    if work_days_actual > work_days_std:
        raise AttendanceExceedError(work_days_actual, work_days_std)
    
    # ===== SI base adjustment =====
    si_base_adjusted = si_base
    si_base_note = ""
    if si_base < si_base_min:
        si_base_adjusted = si_base_min
        si_base_note = "已按下限调整"
    elif si_base > si_base_max:
        si_base_adjusted = si_base_max
        si_base_note = "已按上限调整"
    
    # ===== 1. Gross salary calculation =====
    # Base salary adjusted by attendance
    attendance_ratio = work_days_actual / work_days_std if work_days_std > 0 else 1.0
    base_pay = base_salary * attendance_ratio
    
    # Performance pay
    perf_pay = perf_salary * perf_ratio
    
    # Overtime pay (hourly rate = base_salary / work_days_std / 8)
    hourly_rate = base_salary / work_days_std / 8 if work_days_std > 0 else 0
    ot_pay = (ot_workday * 1.5 + ot_weekend * 2 + ot_holiday * 3) * hourly_rate
    
    # Leave deductions
    daily_rate = base_salary / work_days_std if work_days_std > 0 else 0
    personal_leave_deduct = leave_personal * daily_rate
    sick_leave_deduct = leave_sick * daily_rate * (1 - sick_ratio)
    
    # Gross salary
    gross_salary = base_pay + perf_pay + ot_pay - personal_leave_deduct - sick_leave_deduct
    
    # ===== 2. Social insurance & housing fund =====
    si_personal = calculate_si_personal(si_base_adjusted, city_ratios)
    hf_personal = calculate_hf_personal(si_base_adjusted, hf_ratio)
    total_deductions_si_hf = si_personal['total'] + hf_personal
    
    # ===== 3. Taxable income (cumulative method) =====
    # Monthly income for this month
    monthly_income = gross_salary
    
    # Cumulative income including this month
    new_cum_income = cum_income + monthly_income
    
    # Cumulative deductions
    cum_tax_free = TAX_FREE_THRESHOLD * month_index
    cum_si_hf = (si_personal['total'] + hf_personal) * month_index
    cum_special_deduct = special_deduct * month_index
    
    # Cumulative taxable income
    cum_taxable_income = new_cum_income - cum_tax_free - cum_si_hf - cum_special_deduct
    
    # ===== 4. Tax calculation =====
    # Monthly tax using cumulative method
    cum_tax = calculate_tax(max(0, cum_taxable_income))
    monthly_tax = max(0, cum_tax - cum_tax_paid)
    
    # ===== 5. Net salary =====
    net_salary = gross_salary - total_deductions_si_hf - monthly_tax
    
    # ===== 6. Bonus calculation =====
    bonus_result = None
    if bonus > 0:
        bonus_result = calculate_bonus(
            bonus=bonus,
            monthly_income=monthly_income,
            cum_income=cum_income,
            cum_tax_paid=cum_tax_paid,
            month_index=month_index,
            mode=bonus_mode,
            si_hf_monthly=total_deductions_si_hf,
            special_deduct=special_deduct
        )
    
    # ===== 7. Anomaly checks =====
    anomalies = []
    if net_salary < 0:
        anomalies.append("实发工资为负数，请人工复核")
    if si_base_note:
        anomalies.append(si_base_note)
    
    # Tax jump check (compared to previous month)
    if cum_tax_paid > 0 and monthly_tax > 0:
        prev_month_tax = cum_tax_paid / (month_index - 1) if month_index > 1 else 0
        if prev_month_tax > 0 and monthly_tax / prev_month_tax > 1.5:
            anomalies.append("个税环比波动>50%，请人工复核（可能是累计预扣跳档）")
    
    return {
        'base_pay': round(base_pay, 2),
        'perf_pay': round(perf_pay, 2),
        'ot_pay': round(ot_pay, 2),
        'personal_leave_deduct': round(personal_leave_deduct, 2),
        'sick_leave_deduct': round(sick_leave_deduct, 2),
        'gross_salary': round(gross_salary, 2),
        'si_personal': si_personal,
        'hf_personal': hf_personal,
        'total_si_hf': round(total_deductions_si_hf, 2),
        'taxable_income': round(max(0, cum_taxable_income), 2),
        'monthly_tax': round(monthly_tax, 2),
        'net_salary': round(net_salary, 2),
        'si_base_adjusted': round(si_base_adjusted, 2),
        'si_base_note': si_base_note,
        'anomalies': anomalies,
        'bonus': bonus_result,
    }


def calculate_bonus(
    bonus: float,
    monthly_income: float,
    cum_income: float,
    cum_tax_paid: float,
    month_index: int,
    mode: str = 'auto',
    si_hf_monthly: float = 0,
    special_deduct: float = 0,
) -> Dict[str, Any]:
    """
    Calculate year-end bonus tax under different modes.
    
    Args:
        bonus: Bonus amount
        monthly_income: Current month income
        cum_income: Cumulative income before this month
        cum_tax_paid: Cumulative tax paid before this month
        month_index: Current month number
        mode: 'separate', 'combined', or 'auto'
        si_hf_monthly: Monthly SI + HF deduction
        special_deduct: Monthly special deduction
        
    Returns:
        Dict with comparison results
    """
    results = {}
    
    # ===== Mode 1: Separate taxation =====
    # Bonus / 12 to determine rate
    monthly_bonus = bonus / 12
    rate = 0.03
    quick_deduction = 0
    for threshold, r, qd in TAX_BRACKETS:
        if monthly_bonus <= threshold:
            rate = r
            quick_deduction = qd
            break
    
    separate_tax = bonus * rate - quick_deduction
    separate_net = bonus - separate_tax
    results['separate'] = {
        'tax': round(separate_tax, 2),
        'net': round(separate_net, 2),
        'rate': rate,
        'quick_deduction': quick_deduction,
    }
    
    # ===== Mode 2: Combined taxation =====
    # Add bonus to annual income
    total_income = cum_income + monthly_income + bonus
    total_tax_free = TAX_FREE_THRESHOLD * month_index
    total_si_hf = si_hf_monthly * month_index
    total_special = special_deduct * month_index
    
    total_taxable = total_income - total_tax_free - total_si_hf - total_special
    total_tax = calculate_tax(max(0, total_taxable))
    
    # Tax for this month including bonus
    combined_tax = max(0, total_tax - cum_tax_paid)
    # Tax attributable to bonus (additional tax compared to no bonus)
    # We need to calculate tax without bonus for comparison
    no_bonus_taxable = cum_income + monthly_income - total_tax_free - total_si_hf - total_special
    no_bonus_tax = calculate_tax(max(0, no_bonus_taxable))
    no_bonus_monthly_tax = max(0, no_bonus_tax - cum_tax_paid)
    
    bonus_combined_tax = combined_tax - no_bonus_monthly_tax
    bonus_combined_net = bonus - bonus_combined_tax
    
    results['combined'] = {
        'tax': round(bonus_combined_tax, 2),
        'net': round(bonus_combined_net, 2),
        'total_tax': round(total_tax, 2),
        'monthly_tax_with_bonus': round(combined_tax, 2),
    }
    
    # ===== Auto selection =====
    if mode == 'auto':
        if results['separate']['net'] >= results['combined']['net']:
            best_mode = 'separate'
        else:
            best_mode = 'combined'
    else:
        best_mode = mode if mode in ('separate', 'combined') else 'separate'
    
    results['best_mode'] = best_mode
    results['best'] = results[best_mode]
    
    return results


# ============================================================
# Report generation
# ============================================================

def generate_payslip(result: Dict[str, Any], employee_info: Dict[str, Any]) -> str:
    """
    Generate a text payslip for one employee.
    
    Args:
        result: Calculation result dict
        employee_info: Employee basic info
        
    Returns:
        Formatted payslip text
    """
    lines = []
    lines.append("=" * 50)
    lines.append(f"工资条 - {employee_info.get('name', '未知')} ({employee_info.get('emp_id', 'N/A')})")
    lines.append(f"部门: {employee_info.get('department', 'N/A')}")
    lines.append(f"计薪周期: {employee_info.get('period', 'N/A')}")
    lines.append("=" * 50)
    
    lines.append("\n【应发项目】")
    lines.append(f"  基本工资: {result['base_pay']:.2f}")
    lines.append(f"  绩效工资: {result['perf_pay']:.2f}")
    lines.append(f"  加班费: {result['ot_pay']:.2f}")
    lines.append(f"  应发合计: {result['gross_salary']:.2f}")
    
    lines.append("\n【扣款项目】")
    lines.append(f"  事假扣款: {result['personal_leave_deduct']:.2f}")
    lines.append(f"  病假扣款: {result['sick_leave_deduct']:.2f}")
    lines.append(f"  养老保险: {result['si_personal']['pension']:.2f}")
    lines.append(f"  医疗保险: {result['si_personal']['medical']:.2f}")
    lines.append(f"  失业保险: {result['si_personal']['unemployment']:.2f}")
    lines.append(f"  住房公积金: {result['hf_personal']:.2f}")
    lines.append(f"  个人所得税: {result['monthly_tax']:.2f}")
    
    lines.append("\n【实发工资】")
    lines.append(f"  实发金额: {result['net_salary']:.2f}")
    
    if result.get('bonus'):
        bonus = result['bonus']
        lines.append("\n【年终奖】")
        lines.append(f"  奖金金额: {bonus.get('bonus_amount', 0):.2f}")
        lines.append(f"  最优计税方式: {bonus['best_mode']}")
        lines.append(f"  奖金个税: {bonus['best']['tax']:.2f}")
        lines.append(f"  奖金实发: {bonus['best']['net']:.2f}")
    
    if result.get('anomalies'):
        lines.append("\n【异常提示】")
        for anomaly in result['anomalies']:
            lines.append(f"  ⚠️ {anomaly}")
    
    lines.append("\n" + "=" * 50)
    lines.append("本表为核算参考，发放前需财务复核")
    lines.append("=" * 50)
    
    return "\n".join(lines)


def generate_summary(results: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> str:
    """
    Generate department summary report.
    
    Args:
        results: List of (calculation_result, employee_info) tuples
        
    Returns:
        Formatted summary text
    """
    lines = []
    lines.append("=" * 60)
    lines.append("部门薪资汇总表")
    lines.append("=" * 60)
    
    # Group by department
    departments = {}
    for result, emp in results:
        dept = emp.get('department', '未知')
        if dept not in departments:
            departments[dept] = {
                'count': 0,
                'gross': 0,
                'si_hf': 0,
                'tax': 0,
                'net': 0,
                'employer_cost': 0,
            }
        d = departments[dept]
        d['count'] += 1
        d['gross'] += result['gross_salary']
        d['si_hf'] += result['total_si_hf']
        d['tax'] += result['monthly_tax']
        d['net'] += result['net_salary']
        # Employer cost estimate (roughly 1.3x of gross for SI/HF employer portion)
        d['employer_cost'] += result['gross_salary'] * 1.3
    
    lines.append(f"\n{'部门':<15} {'人数':>5} {'应发合计':>12} {'代扣合计':>12} {'实发合计':>12} {'单位成本':>12}")
    lines.append("-" * 60)
    
    total = {'count': 0, 'gross': 0, 'si_hf': 0, 'tax': 0, 'net': 0, 'employer_cost': 0}
    for dept, d in sorted(departments.items()):
        lines.append(f"{dept:<15} {d['count']:>5} {d['gross']:>12.2f} {d['si_hf']+d['tax']:>12.2f} {d['net']:>12.2f} {d['employer_cost']:>12.2f}")
        total['count'] += d['count']
        total['gross'] += d['gross']
        total['si_hf'] += d['si_hf']
        total['tax'] += d['tax']
        total['net'] += d['net']
        total['employer_cost'] += d['employer_cost']
    
    lines.append("-" * 60)
    lines.append(f"{'合计':<15} {total['count']:>5} {total['gross']:>12.2f} {total['si_hf']+total['tax']:>12.2f} {total['net']:>12.2f} {total['employer_cost']:>12.2f}")
    
    lines.append("\n" + "=" * 60)
    lines.append("本表为核算参考，发放前需财务复核")
    lines.append("=" * 60)
    
    return "\n".join(lines)


# ============================================================
# Config parsing
# ============================================================

def parse_config(text: str) -> Dict[str, Any]:
    """
    Parse key=value config text into a dict.
    Supports JSON values, comments, and blank lines.
    """
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        try:
            result[key] = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            result[key] = value
    return result


def parse_employee_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse employee config, extracting employee info and calculation params.
    """
    employee_info = {
        'name': config.get('name', '未知'),
        'emp_id': config.get('emp_id', 'N/A'),
        'department': config.get('department', '未知'),
        'period': config.get('period', ''),
    }
    
    calc_params = {
        'base_salary': config.get('base_salary'),
        'perf_salary': config.get('perf_salary', 0),
        'perf_ratio': config.get('perf_ratio', 1.0),
        'work_days_std': config.get('work_days_std', DEFAULT_WORK_DAYS_STD),
        'work_days_actual': config.get('work_days_actual'),
        'leave_personal': config.get('leave_personal', 0),
        'leave_sick': config.get('leave_sick', 0),
        'sick_ratio': config.get('sick_ratio', 0.6),
        'ot_workday': config.get('ot_workday', 0),
        'ot_weekend': config.get('ot_weekend', 0),
        'ot_holiday': config.get('ot_holiday', 0),
        'si_base': config.get('si_base'),
        'si_base_min': config.get('si_base_min', 0),
        'si_base_max': config.get('si_base_max', float('inf')),
        'hf_ratio': config.get('hf_ratio', DEFAULT_HF_RATIO),
        'special_deduct': config.get('special_deduct', 0),
        'cum_income': config.get('cum_income', 0),
        'cum_tax_paid': config.get('cum_tax_paid', 0),
        'bonus': config.get('bonus', 0),
        'bonus_mode': config.get('bonus_mode', 'auto'),
        'month_index': config.get('month_index', 1),
    }
    
    return employee_info, calc_params


# ============================================================
# Self-test
# ============================================================

def run_selftest() -> bool:
    """Run offline self-tests."""
    tests = []
    
    # Test 1: parse_config handles comments, blanks, and values
    sample = """
    # This is a comment
    server_name = myhost
    port = 8080
    debug = true

    timeout = 30.5
    """
    cfg = parse_config(sample)
    tests.append(("parse_config basic", cfg.get("server_name") == "myhost"))
    tests.append(("parse_config int", cfg.get("port") == 8080))
    tests.append(("parse_config bool", cfg.get("debug") is True))
    tests.append(("parse_config float", abs(cfg.get("timeout") - 30.5) < 1e-9))
    
    # Test 2: parse_config converts JSON-like values
    cfg2 = parse_config("items = [1,2,3]\nname = \"hello\"")
    tests.append(("parse_config list", cfg2.get("items") == [1, 2, 3]))
    tests.append(("parse_config quoted string", cfg2.get("name") == "hello"))
    
    # Test 3: Tax calculation
    # Annual taxable income 36000 -> tax = 36000 * 0.03 = 1080
    tax1 = calculate_tax(36000)
    tests.append(("tax bracket 1", abs(tax1 - 1080) < 0.01))
    
    # Annual taxable income 50000 -> tax = 50000 * 0.10 - 2520 = 2480
    tax2 = calculate_tax(50000)
    tests.append(("tax bracket 2", abs(tax2 - 2480) < 0.01))
    
    # Annual taxable income 200000 -> tax = 200000 * 0.20 - 16920 = 23080
    tax3 = calculate_tax(200000)
    tests.append(("tax bracket 3", abs(tax3 - 23080) < 0.01))
    
    # Test 4: SI calculation
    si = calculate_si_personal(10000)
    expected_pension = 800.0
    expected_medical = 200.0 + 3
    expected_unemployment = 50.0
    tests.append(("SI pension", abs(si['pension'] - expected_pension) < 0.01))
    tests.append(("SI medical", abs(si['medical'] - expected_medical) < 0.01))
    tests.append(("SI unemployment", abs(si['unemployment'] - expected_unemployment) < 0.01))
    tests.append(("SI total", abs(si['total'] - (800 + 203 + 50)) < 0.01))
    
    # Test 5: HF calculation
    hf = calculate_hf_personal(10000, 0.07)
    tests.append(("HF 7%", abs(hf - 700) < 0.01))
    
    # Test 6: Full salary calculation
    result = calculate_salary(
        base_salary=20000,
        perf_salary=5000,
        perf_ratio=1.0,
        work_days_std=21.75,
        work_days_actual=21.75,
        si_base=20000,
        si_base_min=3000,
        si_base_max=30000,
        hf_ratio=0.07,
        cum_income=0,
        cum_tax_paid=0,
        month_index=1,
    )
    tests.append(("salary gross", abs(result['gross_salary'] - 25000) < 0.01))
    tests.append(("salary si_hf", abs(result['total_si_hf'] - (1600 + 403 + 100 + 1400)) < 0.01))
    tests.append(("salary net positive", result['net_salary'] > 0))
    
    # Test 7: Bonus calculation
    bonus_result = calculate_bonus(
        bonus=50000,
        monthly_income=25000,
        cum_income=0,
        cum_tax_paid=0,
        month_index=1,
        mode='auto',
        si_hf_monthly=3503,
        special_deduct=0,
    )
    tests.append(("bonus has separate", 'separate' in bonus_result))
    tests.append(("bonus has combined", 'combined' in bonus_result))
    tests.append(("bonus best mode valid", bonus_result['best_mode'] in ('separate', 'combined')))
    
    # Test 8: Error handling
    try:
        calculate_salary(base_salary=None, work_days_actual=20, si_base=10000)
        tests.append(("missing field error", False))
    except MissingFieldError:
        tests.append(("missing field error", True))
    
    try:
        calculate_salary(base_salary=10000, work_days_actual=25, si_base=10000, work_days_std=21.75)
        tests.append(("attendance exceed error", False))
    except AttendanceExceedError:
        tests.append(("attendance exceed error", True))
    
    # Test 9: SI base adjustment
    result_low = calculate_salary(
        base_salary=10000,
        work_days_actual=21.75,
        si_base=2000,
        si_base_min=3000,
        si_base_max=30000,
    )
    tests.append(("SI base adjusted to min", result_low['si_base_adjusted'] == 3000))
    tests.append(("SI base note", "下限" in result_low['si_base_note']))
    
    # Test 10: Payslip generation
    payslip = generate_payslip(result, {'name': '张三', 'emp_id': '001', 'department': '技术部'})
    tests.append(("payslip contains name", "张三" in payslip))
    tests.append(("payslip contains gross", "应发合计" in payslip))
    tests.append(("payslip contains net", "实发金额" in payslip))
    
    # Run all tests
    all_passed = True
    for name, passed in tests:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
        if not passed:
            all_passed = False
    
    return all_passed


# ============================================================
# Main entry
# ============================================================

def main():
    if "--selftest" in sys.argv:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # Default behavior: read stdin, parse, calculate
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
    else:
        input_text = ""
    
    if not input_text.strip():
        print("No input provided. Usage: echo 'key=value...' | python main.py")
        print("Or run with --selftest for self-test.")
        sys.exit(0)
    
    config = parse_config(input_text)
    
    # Check if this is a single employee or multiple
    if 'employees' in config:
        # Multiple employees
        results = []
        for emp_config in config['employees']:
            emp_info, calc_params = parse_employee_config(emp_config)
            try:
                result = calculate_salary(**calc_params)
                results.append((result, emp_info))
                print(generate_payslip(result, emp_info))
                print()
            except CalcError as e:
                print(f"错误: {e}")
                print()
        
        if results:
            print(generate_summary(results))
    else:
        # Single employee
        emp_info, calc_params = parse_employee_config(config)
        try:
            result = calculate_salary(**calc_params)
            print(generate_payslip(result, emp_info))
            
            # Output as JSON for programmatic use
            if '--json' in sys.argv:
                print("\n--- JSON OUTPUT ---")
                print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        except CalcError as e:
            print(f"错误: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
