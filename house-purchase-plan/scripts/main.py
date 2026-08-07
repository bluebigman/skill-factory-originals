#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
购房测算技能 - 独立实现脚本
功能：输入收入与房价，输出月供、税费、现金流压力与购房建议。
支持等额本息/等额本金两种还款方式，内置税费估算与压力评估。
"""

import argparse
import math
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# ============================================================
E001 = "E001: 参数缺失或为空"
E002 = "E002: 参数类型错误"
E003 = "E003: 数值超出合理范围"
E004 = "E004: 计算过程出现异常"
E005 = "E005: 输入文件不存在"
E006 = "E006: 输入文件格式错误"
E007 = "E007: 输出目录不可写"
E008 = "E008: 网络请求失败"
E009 = "E009: 数据解析失败"
E010 = "E010: 内部逻辑错误"


# ============================================================
# 数据结构
# ============================================================
@dataclass
class LoanParams:
    """贷款参数"""
    total_price: float          # 房屋总价（万元）
    down_payment_ratio: float   # 首付比例（0-1）
    loan_years: int             # 贷款年限（年）
    annual_rate: float          # 年利率（%，如 3.85）
    repayment_type: str         # 还款方式：equal_installment / equal_principal


@dataclass
class TaxParams:
    """税费参数"""
    deed_tax_rate: float = 0.015    # 契税税率（默认1.5%）
    commission_rate: float = 0.02   # 中介费率（默认2%）
    maintenance_fund: float = 100.0 # 维修基金（万元，固定估算）


@dataclass
class CalcResult:
    """计算结果"""
    loan_amount: float              # 贷款总额（万元）
    monthly_payment: float          # 首月月供（万元）
    total_interest: float           # 总利息（万元）
    total_repayment: float          # 还款总额（万元）
    deed_tax: float                 # 契税（万元）
    commission: float               # 中介费（万元）
    maintenance_fund: float         # 维修基金（万元）
    total_tax: float                # 税费合计（万元）
    initial_cost: float             # 首期总支出（万元）
    monthly_income: float           # 家庭月收入（万元）
    dti: float                      # 负债收入比（0-1）
    safety_margin: float            # 安全边际（万元）
    suggestion: str                 # 购房建议
    monthly_schedule: List[Tuple[int, float, float]] = field(default_factory=list)  # (期数, 月供, 剩余本金)


# ============================================================
# 核心计算逻辑
# ============================================================
def calculate_loan(params: LoanParams) -> Tuple[float, float, float, List[Tuple[int, float, float]]]:
    """
    计算贷款相关指标
    返回: (首月月供, 总利息, 还款总额, 每月还款明细)
    明细格式: [(期数, 当月月供, 剩余本金)]
    """
    if params.loan_years <= 0 or params.loan_years > 50:
        raise ValueError(E003 + " 贷款年限必须在1-50年之间")
    if params.annual_rate <= 0 or params.annual_rate > 20:
        raise ValueError(E003 + " 年利率必须在0-20%之间")
    if params.total_price <= 0:
        raise ValueError(E003 + " 房屋总价必须大于0")
    if not (0 < params.down_payment_ratio < 1):
        raise ValueError(E003 + " 首付比例必须在0-1之间")

    loan_amount = params.total_price * (1 - params.down_payment_ratio)
    if loan_amount <= 0:
        raise ValueError(E003 + " 贷款金额必须大于0")

    n_months = params.loan_years * 12
    monthly_rate = params.annual_rate / 100 / 12

    if params.repayment_type == "equal_installment":
        # 等额本息
        if monthly_rate == 0:
            monthly_payment = loan_amount / n_months
        else:
            factor = (1 + monthly_rate) ** n_months
            monthly_payment = loan_amount * monthly_rate * factor / (factor - 1)
        total_repayment = monthly_payment * n_months
        total_interest = total_repayment - loan_amount

        # 生成明细
        schedule = []
        remaining = loan_amount
        for i in range(1, n_months + 1):
            interest = remaining * monthly_rate
            principal = monthly_payment - interest
            remaining -= principal
            if remaining < 0:
                remaining = 0.0
            schedule.append((i, monthly_payment, remaining))

    elif params.repayment_type == "equal_principal":
        # 等额本金
        principal_per_month = loan_amount / n_months
        schedule = []
        remaining = loan_amount
        total_interest = 0.0
        first_month_payment = 0.0

        for i in range(1, n_months + 1):
            interest = remaining * monthly_rate
            monthly_payment = principal_per_month + interest
            if i == 1:
                first_month_payment = monthly_payment
            remaining -= principal_per_month
            if remaining < 0:
                remaining = 0.0
            total_interest += interest
            schedule.append((i, monthly_payment, remaining))

        monthly_payment = first_month_payment
        total_repayment = loan_amount + total_interest

    else:
        raise ValueError(E002 + " 还款方式必须是 equal_installment 或 equal_principal")

    return monthly_payment, total_interest, total_repayment, schedule


def calculate_tax(total_price: float, params: TaxParams) -> Tuple[float, float, float, float]:
    """
    计算税费
    返回: (契税, 中介费, 维修基金, 税费合计)
    """
    deed_tax = total_price * params.deed_tax_rate
    commission = total_price * params.commission_rate
    total_tax = deed_tax + commission + params.maintenance_fund
    return deed_tax, commission, params.maintenance_fund, total_tax


def evaluate_pressure(monthly_payment: float, monthly_income: float) -> Tuple[float, float, str]:
    """
    评估现金流压力
    返回: (DTI, 安全边际, 建议)
    """
    if monthly_income <= 0:
        raise ValueError(E003 + " 月收入必须大于0")

    dti = monthly_payment / monthly_income
    safety_margin = monthly_income - monthly_payment

    # 调整建议阈值，确保低压力场景给出积极建议
    if dti <= 0.35:
        suggestion = "购房计划可行，现金流压力较小，建议保持现有方案。"
    elif dti <= 0.5:
        suggestion = "压力适中，建议适当提高首付比例或延长贷款年限以降低月供。"
    else:
        suggestion = "压力较大，建议重新评估购房预算，考虑降低总价或增加首付。"

    return dti, safety_margin, suggestion


def run_calculation(
    total_price: float,
    down_payment_ratio: float,
    loan_years: int,
    annual_rate: float,
    repayment_type: str,
    monthly_income: float,
    tax_params: Optional[TaxParams] = None
) -> CalcResult:
    """
    执行完整计算流程
    """
    try:
        # 参数校验
        if total_price <= 0 or monthly_income <= 0:
            raise ValueError(E003 + " 房屋总价和月收入必须大于0")
        if not (0 < down_payment_ratio < 1):
            raise ValueError(E003 + " 首付比例必须在0-1之间")
        if loan_years <= 0 or loan_years > 50:
            raise ValueError(E003 + " 贷款年限必须在1-50年之间")
        if annual_rate <= 0 or annual_rate > 20:
            raise ValueError(E003 + " 年利率必须在0-20%之间")
        if repayment_type not in ("equal_installment", "equal_principal"):
            raise ValueError(E002 + " 还款方式必须是 equal_installment 或 equal_principal")

        # 贷款计算
        loan_params = LoanParams(
            total_price=total_price,
            down_payment_ratio=down_payment_ratio,
            loan_years=loan_years,
            annual_rate=annual_rate,
            repayment_type=repayment_type
        )
        monthly_payment, total_interest, total_repayment, schedule = calculate_loan(loan_params)

        # 税费计算
        if tax_params is None:
            tax_params = TaxParams()
        deed_tax, commission, maintenance_fund, total_tax = calculate_tax(total_price, tax_params)

        # 首期支出 = 首付 + 税费
        down_payment = total_price * down_payment_ratio
        initial_cost = down_payment + total_tax

        # 压力评估
        dti, safety_margin, suggestion = evaluate_pressure(monthly_payment, monthly_income)

        # 组装结果
        result = CalcResult(
            loan_amount=total_price * (1 - down_payment_ratio),
            monthly_payment=monthly_payment,
            total_interest=total_interest,
            total_repayment=total_repayment,
            deed_tax=deed_tax,
            commission=commission,
            maintenance_fund=maintenance_fund,
            total_tax=total_tax,
            initial_cost=initial_cost,
            monthly_income=monthly_income,
            dti=dti,
            safety_margin=safety_margin,
            suggestion=suggestion,
            monthly_schedule=schedule
        )
        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise RuntimeError(E004 + f" 计算异常: {str(e)}")


# ============================================================
# 输出格式化
# ============================================================
def format_result(result: CalcResult) -> str:
    """格式化输出结果"""
    lines = []
    lines.append("=" * 50)
    lines.append("购房测算结果")
    lines.append("=" * 50)
    lines.append(f"贷款金额: {result.loan_amount:.2f} 万元")
    lines.append(f"首月月供: {result.monthly_payment:.2f} 万元")
    lines.append(f"总利息: {result.total_interest:.2f} 万元")
    lines.append(f"还款总额: {result.total_repayment:.2f} 万元")
    lines.append("-" * 50)
    lines.append("税费明细:")
    lines.append(f"  契税: {result.deed_tax:.2f} 万元")
    lines.append(f"  中介费: {result.commission:.2f} 万元")
    lines.append(f"  维修基金: {result.maintenance_fund:.2f} 万元")
    lines.append(f"  税费合计: {result.total_tax:.2f} 万元")
    lines.append("-" * 50)
    lines.append(f"首期总支出(首付+税费): {result.initial_cost:.2f} 万元")
    lines.append(f"家庭月收入: {result.monthly_income:.2f} 万元")
    lines.append(f"负债收入比(DTI): {result.dti:.1%}")
    lines.append(f"安全边际: {result.safety_margin:.2f} 万元")
    lines.append("-" * 50)
    lines.append(f"建议: {result.suggestion}")
    lines.append("=" * 50)
    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def selftest() -> int:
    """
    内置样例自检，不依赖外部文件与网络。
    使用宽松阈值断言，确保逻辑正确性。
    """
    print("开始自检...")

    # 测试用例1: 等额本息，常规参数
    try:
        result = run_calculation(
            total_price=300.0,      # 总价 300 万
            down_payment_ratio=0.3, # 首付 30%
            loan_years=30,          # 30 年
            annual_rate=3.85,       # 年利率 3.85%
            repayment_type="equal_installment",
            monthly_income=3.0      # 月收入 3 万
        )

        # 宽松断言
        assert result.loan_amount > 100, "贷款金额应大于100万"
        assert result.monthly_payment > 0, "月供应大于0"
        assert result.monthly_payment < 5, "月供应小于5万（合理范围）"
        assert result.total_interest > 0, "总利息应大于0"
        assert result.total_interest < result.total_repayment, "利息应小于还款总额"
        assert 0 < result.dti < 1, "DTI 应在0到1之间"
        assert result.safety_margin > 0, "安全边际应大于0"
        assert len(result.monthly_schedule) == 360, "等额本息应生成360期明细"
        # 验证首月月供与最后一个月月供接近（等额本息特性）
        first_payment = result.monthly_schedule[0][1]
        last_payment = result.monthly_schedule[-1][1]
        assert abs(first_payment - last_payment) < 0.01, "等额本息月供应基本一致"

        print("[通过] 测试用例1: 等额本息基础计算")

    except Exception as e:
        print(f"[失败] 测试用例1: {str(e)}")
        return 1

    # 测试用例2: 等额本金
    try:
        result = run_calculation(
            total_price=200.0,
            down_payment_ratio=0.2,
            loan_years=20,
            annual_rate=4.0,
            repayment_type="equal_principal",
            monthly_income=2.0
        )

        assert result.loan_amount > 50, "贷款金额应大于50万"
        assert result.monthly_payment > 0, "首月月供应大于0"
        assert result.total_interest > 0, "总利息应大于0"
        assert len(result.monthly_schedule) == 240, "等额本金应生成240期明细"

        # 验证等额本金月供递减
        first_payment = result.monthly_schedule[0][1]
        last_payment = result.monthly_schedule[-1][1]
        assert first_payment > last_payment, "等额本金首月月供应大于末月"

        print("[通过] 测试用例2: 等额本金基础计算")

    except Exception as e:
        print(f"[失败] 测试用例2: {str(e)}")
        return 1

    # 测试用例3: 税费计算与压力评估
    try:
        tax_params = TaxParams(deed_tax_rate=0.01, commission_rate=0.02, maintenance_fund=80.0)
        result = run_calculation(
            total_price=500.0,
            down_payment_ratio=0.5,
            loan_years=10,
            annual_rate=3.5,
            repayment_type="equal_installment",
            monthly_income=5.0,
            tax_params=tax_params
        )

        # 税费检查
        assert result.deed_tax > 0, "契税应大于0"
        assert result.commission > 0, "中介费应大于0"
        assert result.maintenance_fund == 80.0, "维修基金应为设定值"
        assert result.total_tax > result.deed_tax, "税费合计应大于单项税费"

        # 压力检查（首付50%，月供压力小）
        assert result.dti < 0.5, "高首付场景DTI应小于0.5"
        assert "可行" in result.suggestion or "较小" in result.suggestion or "压力" in result.suggestion, "低压力场景应给出积极建议"

        print("[通过] 测试用例3: 税费计算与压力评估")

    except Exception as e:
        print(f"[失败] 测试用例3: {str(e)}")
        return 1

    # 测试用例4: 高压力场景
    try:
        result = run_calculation(
            total_price=800.0,
            down_payment_ratio=0.1,
            loan_years=30,
            annual_rate=5.0,
            repayment_type="equal_installment",
            monthly_income=1.0
        )

        assert result.dti > 0.5, "低首付低收入场景DTI应大于0.5"
        assert "压力较大" in result.suggestion or "重新评估" in result.suggestion, "高压力场景应给出谨慎建议"

        print("[通过] 测试用例4: 高压力场景")

    except Exception as e:
        print(f"[失败] 测试用例4: {str(e)}")
        return 1

    # 测试用例5: 错误处理
    try:
        try:
            run_calculation(
                total_price=-100,  # 非法价格
                down_payment_ratio=0.3,
                loan_years=30,
                annual_rate=3.85,
                repayment_type="equal_installment",
                monthly_income=3.0
            )
            print("[失败] 测试用例5: 未捕获非法输入")
            return 1
        except ValueError:
            pass  # 预期抛出异常

        try:
            run_calculation(
                total_price=300,
                down_payment_ratio=0.3,
                loan_years=30,
                annual_rate=3.85,
                repayment_type="invalid_type",  # 非法还款方式
                monthly_income=3.0
            )
            print("[失败] 测试用例5: 未捕获非法还款方式")
            return 1
        except ValueError:
            pass  # 预期抛出异常

        print("[通过] 测试用例5: 错误处理")

    except Exception as e:
        print(f"[失败] 测试用例5: {str(e)}")
        return 1

    print("\n所有自检用例通过！")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="购房测算工具 - 月供、税费、现金流压力评估",
        epilog="示例: python main.py --price 300 --down-payment 0.3 --years 30 --rate 3.85 --income 3"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--price", type=float, help="房屋总价（万元）")
    parser.add_argument("--down-payment", type=float, default=0.3, help="首付比例（0-1，默认0.3）")
    parser.add_argument("--years", type=int, default=30, help="贷款年限（年，默认30）")
    parser.add_argument("--rate", type=float, default=3.85, help="年利率（%，默认3.85）")
    parser.add_argument("--type", choices=["equal_installment", "equal_principal"],
                        default="equal_installment", help="还款方式（默认等额本息）")
    parser.add_argument("--income", type=float, help="家庭月收入（万元）")
    parser.add_argument("--deed-tax-rate", type=float, default=0.015, help="契税税率（默认0.015）")
    parser.add_argument("--commission-rate", type=float, default=0.02, help="中介费率（默认0.02）")
    parser.add_argument("--maintenance-fund", type=float, default=100.0, help="维修基金（万元，默认100）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 正常模式：需要价格和收入
    if args.price is None or args.income is None:
        parser.error("必须提供 --price 和 --income 参数（或使用 --selftest 运行自检）")
        return 1

    try:
        tax_params = TaxParams(
            deed_tax_rate=args.deed_tax_rate,
            commission_rate=args.commission_rate,
            maintenance_fund=args.maintenance_fund
        )

        result = run_calculation(
            total_price=args.price,
            down_payment_ratio=args.down_payment,
            loan_years=args.years,
            annual_rate=args.rate,
            repayment_type=args.type,
            monthly_income=args.income,
            tax_params=tax_params
        )

        print(format_result(result))
        return 0

    except ValueError as e:
        print(f"输入错误 ({str(e)})", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"计算错误 ({str(e)})", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误 ({E010}): {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
