#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期权估值分析工具 (stock-option-analysis)

功能：
- 期权内在价值、时间价值计算
- 希腊字母近似计算（Delta, Gamma, Theta, Vega, Rho）
- 行权策略建议
- 内置自检模式（--selftest），离线运行不依赖外部文件

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 数值计算异常
    E007: 参数类型错误
    E008: 内部状态异常
    E009: 不受支持的期权类型
    E010: 自检失败

运行示例：
    python scripts/main.py --spot 100 --strike 105 --type call --expiry 0.5 --vol 0.3 --rate 0.02
    python scripts/main.py --selftest
"""

import argparse
import math
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class OptionError(Exception):
    """期权分析自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ============================================================
# 数据结构
# ============================================================
@dataclass
class OptionInput:
    """期权输入参数。"""

    spot: float          # 标的当前价格
    strike: float        # 行权价
    option_type: str     # 'call' 或 'put'
    expiry: float        # 剩余期限（年）
    vol: float           # 波动率（年化，小数形式）
    rate: float          # 无风险利率（年化，小数形式）
    dividend: float = 0.0  # 股息率（年化，小数形式）


@dataclass
class OptionResult:
    """期权分析结果。"""

    intrinsic_value: float       # 内在价值
    time_value: float            # 时间价值
    fair_price: float            # 理论价格（BS近似）
    delta: float                 # Delta
    gamma: float                 # Gamma
    theta: float                 # Theta（年化，通常为负）
    vega: float                  # Vega（每单位波动率变动）
    rho: float                   # Rho（每单位利率变动）
    strategy: str                # 行权策略建议
    confidence: float            # 置信度（0~1）
    warnings: List[str] = field(default_factory=list)  # 提示信息


# ============================================================
# 核心数学函数（Black-Scholes 近似）
# ============================================================
def _norm_cdf(x: float) -> float:
    """标准正态分布累积分布函数（数值近似）。"""
    # Abramowitz-Stegun 近似公式，误差 < 1e-7
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    d = 0.3989423 * math.exp(-x * x / 2.0)
    poly = ((((1.330274429 * t - 1.821255978) * t + 1.781477937) * t - 0.356563782) * t + 0.319381530) * t
    if x >= 0:
        return 1.0 - d * poly
    else:
        return d * poly


def _norm_pdf(x: float) -> float:
    """标准正态分布概率密度函数。"""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _black_scholes(inp: OptionInput) -> Tuple[float, float, float, float, float, float]:
    """
    计算 Black-Scholes 理论价格与希腊字母。

    返回: (价格, delta, gamma, theta, vega, rho)
    """
    s = inp.spot
    k = inp.strike
    t = inp.expiry
    v = inp.vol
    r = inp.rate
    q = inp.dividend

    if t <= 0:
        # 到期日：直接按内在价值处理
        if inp.option_type == "call":
            price = max(0.0, s - k)
            delta = 1.0 if s > k else 0.0
        else:
            price = max(0.0, k - s)
            delta = -1.0 if s < k else 0.0
        return price, delta, 0.0, 0.0, 0.0, 0.0

    if v <= 0:
        raise OptionError("E006", "波动率必须为正数")

    sqrt_t = math.sqrt(t)
    d1 = (math.log(s / k) + (r - q + 0.5 * v * v) * t) / (v * sqrt_t)
    d2 = d1 - v * sqrt_t

    if inp.option_type == "call":
        price = s * math.exp(-q * t) * _norm_cdf(d1) - k * math.exp(-r * t) * _norm_cdf(d2)
        delta = math.exp(-q * t) * _norm_cdf(d1)
        theta = (
            -(s * math.exp(-q * t) * _norm_pdf(d1) * v) / (2.0 * sqrt_t)
            - r * k * math.exp(-r * t) * _norm_cdf(d2)
            + q * s * math.exp(-q * t) * _norm_cdf(d1)
        )
        rho = k * t * math.exp(-r * t) * _norm_cdf(d2)
    elif inp.option_type == "put":
        price = k * math.exp(-r * t) * _norm_cdf(-d2) - s * math.exp(-q * t) * _norm_cdf(-d1)
        delta = -math.exp(-q * t) * _norm_cdf(-d1)
        theta = (
            -(s * math.exp(-q * t) * _norm_pdf(d1) * v) / (2.0 * sqrt_t)
            + r * k * math.exp(-r * t) * _norm_cdf(-d2)
            - q * s * math.exp(-q * t) * _norm_cdf(-d1)
        )
        rho = -k * t * math.exp(-r * t) * _norm_cdf(-d2)
    else:
        raise OptionError("E009", f"不支持的期权类型: {inp.option_type}")

    gamma = math.exp(-q * t) * _norm_pdf(d1) / (s * v * sqrt_t)
    vega = s * math.exp(-q * t) * _norm_pdf(d1) * sqrt_t / 100.0  # 每1%波动率变动

    return price, delta, gamma, theta, vega, rho


# ============================================================
# 策略建议
# ============================================================
def _generate_strategy(inp: OptionInput, result: OptionResult) -> str:
    """根据计算结果生成行权策略建议。"""
    if inp.option_type == "call":
        if result.intrinsic_value <= 0:
            return "虚值看涨：不建议立即行权，可考虑观望或卖出期权获取时间价值"
        elif result.time_value <= 0:
            return "实值看涨且时间价值极低：临近到期，建议行权或平仓锁定收益"
        else:
            return "实值看涨：可继续持有，行权前需比较行权收益与卖出期权收益"
    else:
        if result.intrinsic_value <= 0:
            return "虚值看跌：不建议立即行权，可考虑观望或卖出期权获取时间价值"
        elif result.time_value <= 0:
            return "实值看跌且时间价值极低：临近到期，建议行权或平仓锁定收益"
        else:
            return "实值看跌：可继续持有，行权前需比较行权收益与卖出期权收益"


# ============================================================
# 主分析函数
# ============================================================
def analyze_option(inp: OptionInput) -> OptionResult:
    """
    执行期权估值分析主流程。

    参数:
        inp: 期权输入参数

    返回:
        OptionResult 包含估值结果与策略建议

    异常:
        OptionError: 输入校验失败或计算异常
    """
    # ---- 输入校验（E001/E002/E003）----
    if inp is None:
        raise OptionError("E001", "请提供待处理的内容，格式为：期权标的与行权参数")

    if inp.spot is None or inp.strike is None or inp.expiry is None or inp.vol is None or inp.rate is None:
        raise OptionError("E002", "还缺少以下信息，请补充：标的价、行权价、期限、波动率、利率")

    if inp.spot <= 0 or inp.strike <= 0:
        raise OptionError("E003", "标的价和行权价必须为正数")

    if inp.expiry < 0:
        raise OptionError("E003", "剩余期限不能为负数")

    if inp.vol <= 0:
        raise OptionError("E003", "波动率必须为正数")

    if inp.option_type not in ("call", "put"):
        raise OptionError("E009", f"不支持的期权类型: {inp.option_type}，仅支持 call / put")

    # ---- 计算 ----
    try:
        # 内在价值（使用 epsilon 处理浮点数精度问题）
        epsilon = 1e-10
        if inp.option_type == "call":
            intrinsic = max(0.0, inp.spot - inp.strike)
        else:
            intrinsic = max(0.0, inp.strike - inp.spot)
        
        # 处理浮点数精度问题：如果内在价值非常接近0，则设为0
        if intrinsic < epsilon:
            intrinsic = 0.0

        # 理论价格与希腊字母
        fair_price, delta, gamma, theta, vega, rho = _black_scholes(inp)

        # 时间价值 = 理论价格 - 内在价值（若理论价格 < 内在价值则取0，避免负值）
        time_value = max(0.0, fair_price - intrinsic)

        # 组装结果
        result = OptionResult(
            intrinsic_value=round(intrinsic, 4),
            time_value=round(time_value, 4),
            fair_price=round(fair_price, 4),
            delta=round(delta, 4),
            gamma=round(gamma, 6),
            theta=round(theta, 6),
            vega=round(vega, 6),
            rho=round(rho, 6),
            strategy="",
            confidence=0.0,
            warnings=[],
        )

        # 策略建议
        result.strategy = _generate_strategy(inp, result)

        # 置信度评估（基于参数合理性与计算稳定性）
        confidence = 0.95  # 默认高置信度
        if inp.expiry > 5:
            confidence -= 0.05
            result.warnings.append("剩余期限较长（>5年），模型误差可能增大")
        if inp.vol > 1.5:
            confidence -= 0.05
            result.warnings.append("波动率异常偏高（>150%），结果需谨慎参考")
        if inp.vol < 0.05:
            confidence -= 0.05
            result.warnings.append("波动率异常偏低（<5%），结果需谨慎参考")
        if inp.spot <= 0 or inp.strike <= 0:
            confidence -= 0.1
        if confidence < 0.85:
            result.warnings.append("[需核实] 置信度较低，建议人工复核关键参数")
        result.confidence = round(confidence, 2)

        return result

    except OptionError:
        raise
    except (ValueError, OverflowError, ZeroDivisionError) as e:
        raise OptionError("E006", f"数值计算异常: {str(e)}") from e
    except Exception as e:
        raise OptionError("E008", f"内部状态异常: {str(e)}") from e


# ============================================================
# 输出格式化
# ============================================================
def format_result(result: OptionResult, inp: OptionInput) -> str:
    """将分析结果格式化为可读文本。"""
    lines = []
    lines.append("=" * 50)
    lines.append("期权估值分析结果")
    lines.append("=" * 50)
    lines.append(f"期权类型: {'看涨' if inp.option_type == 'call' else '看跌'}")
    lines.append(f"标的价: {inp.spot:.2f}  行权价: {inp.strike:.2f}")
    lines.append(f"剩余期限: {inp.expiry:.2f} 年  波动率: {inp.vol*100:.1f}%  利率: {inp.rate*100:.2f}%")
    lines.append("-" * 50)
    lines.append(f"理论价格:    {result.fair_price:.4f}")
    lines.append(f"内在价值:    {result.intrinsic_value:.4f}")
    lines.append(f"时间价值:    {result.time_value:.4f}")
    lines.append("-" * 50)
    lines.append("希腊字母:")
    lines.append(f"  Delta: {result.delta:.4f}")
    lines.append(f"  Gamma: {result.gamma:.6f}")
    lines.append(f"  Theta: {result.theta:.6f} (年化)")
    lines.append(f"  Vega:  {result.vega:.6f} (每1%波动率)")
    lines.append(f"  Rho:   {result.rho:.6f} (每1%利率)")
    lines.append("-" * 50)
    lines.append(f"置信度: {result.confidence*100:.0f}%")
    if result.warnings:
        lines.append("提示:")
        for w in result.warnings:
            lines.append(f"  - {w}")
    lines.append("-" * 50)
    lines.append("策略建议:")
    lines.append(f"  {result.strategy}")
    lines.append("=" * 50)
    return "\n".join(lines)


# ============================================================
# 自检模块（离线、硬编码数据、宽松断言）
# ============================================================
def _run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保稳健性。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("[自检] 开始执行离线自检...")
    failures = 0

    # ---- 样例1: 标准看涨期权（实值）----
    try:
        inp1 = OptionInput(
            spot=110.0, strike=100.0, option_type="call",
            expiry=1.0, vol=0.25, rate=0.03, dividend=0.0
        )
        r1 = analyze_option(inp1)
        # 宽松断言：实值看涨内在价值 > 0
        assert r1.intrinsic_value > 0, "实值看涨内在价值应大于0"
        assert r1.intrinsic_value <= 10.0, "内在价值不应超过价差(110-100=10)"
        # 看涨 Delta 应在 (0, 1) 之间且实值应 > 0.5
        assert 0.0 < r1.delta < 1.0, "看涨 Delta 应在 (0,1) 区间"
        assert r1.delta > 0.5, "实值看涨 Delta 应 > 0.5"
        # Gamma 应为正数
        assert r1.gamma > 0, "Gamma 应为正数"
        # 理论价格应 >= 内在价值
        assert r1.fair_price >= r1.intrinsic_value, "理论价格应不低于内在价值"
        # 置信度应较高
        assert r1.confidence >= 0.85, "标准输入置信度应 >= 0.85"
        print(f"  [通过] 样例1 看涨实值: 价格={r1.fair_price:.4f}, Delta={r1.delta:.4f}")
    except AssertionError as e:
        failures += 1
        print(f"  [失败] 样例1 断言错误: {e}")
    except Exception as e:
        failures += 1
        print(f"  [失败] 样例1 异常: {e}")

    # ---- 样例2: 标准看跌期权（虚值）----
    try:
        inp2 = OptionInput(
            spot=90.0, strike=100.0, option_type="put",
            expiry=0.5, vol=0.30, rate=0.02, dividend=0.01
        )
        r2 = analyze_option(inp2)
        # 虚值看跌内在价值应为 0
        assert r2.intrinsic_value == 0.0, "虚值看跌内在价值应为 0"
        # 看跌 Delta 应在 (-1, 0) 区间
        assert -1.0 < r2.delta < 0.0, "看跌 Delta 应在 (-1,0) 区间"
        # 时间价值应 > 0
        assert r2.time_value > 0, "虚值期权时间价值应 > 0"
        print(f"  [通过] 样例2 看跌虚值: 价格={r2.fair_price:.4f}, Delta={r2.delta:.4f}")
    except AssertionError as e:
        failures += 1
        print(f"  [失败] 样例2 断言错误: {e}")
    except Exception as e:
        failures += 1
        print(f"  [失败] 样例2 异常: {e}")

    # ---- 样例3: 深度实值看涨（临近到期）----
    try:
        inp3 = OptionInput(
            spot=150.0, strike=50.0, option_type="call",
            expiry=0.05, vol=0.20, rate=0.03, dividend=0.0
        )
        r3 = analyze_option(inp3)
        # 深度实值：内在价值接近价差
        assert r3.intrinsic_value > 90.0, "深度实值内在价值应接近价差(150-50=100)"
        assert r3.delta > 0.9, "深度实值看涨 Delta 应接近 1"
        print(f"  [通过] 样例3 深度实值: 价格={r3.fair_price:.4f}, Delta={r3.delta:.4f}")
    except AssertionError as e:
        failures += 1
        print(f"  [失败] 样例3 断言错误: {e}")
    except Exception as e:
        failures += 1
        print(f"  [失败] 样例3 异常: {e}")

    # ---- 样例4: 平价期权（At-the-Money）----
    try:
        inp4 = OptionInput(
            spot=100.0, strike=100.0, option_type="call",
            expiry=1.0, vol=0.30, rate=0.03, dividend=0.0
        )
        r4 = analyze_option(inp4)
        # 平价期权：内在价值为 0，Delta 接近 0.5
        assert r4.intrinsic_value == 0.0, "平价期权内在价值应为 0"
        assert 0.3 < r4.delta < 0.7, "平价看涨 Delta 应接近 0.5"
        assert r4.time_value > 0, "平价期权时间价值应 > 0"
        print(f"  [通过] 样例4 平价期权: 价格={r4.fair_price:.4f}, Delta={r4.delta:.4f}")
    except AssertionError as e:
        failures += 1
        print(f"  [失败] 样例4 断言错误: {e}")
    except Exception as e:
        failures += 1
        print(f"  [失败] 样例4 异常: {e}")

    # ---- 样例5: 错误输入处理（输入为空）----
    try:
        analyze_option(None)
        failures += 1
        print("  [失败] 样例5 应抛出 E001 异常但未抛出")
    except OptionError as e:
        if e.code == "E001":
            print("  [通过] 样例5 空输入正确返回 E001")
        else:
            failures += 1
            print(f"  [失败] 样例5 错误码不正确: {e.code}")
    except Exception as e:
        failures += 1
        print(f"  [失败] 样例5 异常类型错误: {e}")

    # ---- 样例6: 错误输入处理（非法期权类型）----
    try:
        bad_inp = OptionInput(
            spot=100.0, strike=100.0, option_type="invalid",
            expiry=1.0, vol=0.3, rate=0.03
        )
        analyze_option(bad_inp)
        failures += 1
        print("  [失败] 样例6 应抛出 E009 异常但未抛出")
    except OptionError as e:
        if e.code == "E009":
            print("  [通过] 样例6 非法类型正确返回 E009")
        else:
            failures += 1
            print(f"  [失败] 样例6 错误码不正确: {e.code}")
    except Exception as e:
        failures += 1
        print(f"  [失败] 样例6 异常类型错误: {e}")

    # ---- 汇总 ----
    if failures == 0:
        print("[自检] 全部通过 ✓")
        return 0
    else:
        print(f"[自检] 共 {failures} 项失败 ✗")
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="期权估值分析工具 (stock-option-analysis)",
        epilog="示例: python main.py --spot 100 --strike 105 --type call --expiry 0.5 --vol 0.3 --rate 0.02"
    )
    parser.add_argument("--spot", type=float, help="标的当前价格")
    parser.add_argument("--strike", type=float, help="行权价")
    parser.add_argument("--type", dest="option_type", choices=["call", "put"], help="期权类型: call/put")
    parser.add_argument("--expiry", type=float, help="剩余期限（年）")
    parser.add_argument("--vol", type=float, help="波动率（年化，小数形式，如 0.3 表示 30%%）")
    parser.add_argument("--rate", type=float, help="无风险利率（年化，小数形式）")
    parser.add_argument("--dividend", type=float, default=0.0, help="股息率（年化，默认0）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 参数完整性校验
    missing = []
    if args.spot is None:
        missing.append("--spot")
    if args.strike is None:
        missing.append("--strike")
    if args.option_type is None:
        missing.append("--type")
    if args.expiry is None:
        missing.append("--expiry")
    if args.vol is None:
        missing.append("--vol")
    if args.rate is None:
        missing.append("--rate")

    if missing:
        print(f"E002: 还缺少以下信息，请补充: {', '.join(missing)}", file=sys.stderr)
        print("示例: python main.py --spot 100 --strike 105 --type call --expiry 0.5 --vol 0.3 --rate 0.02", file=sys.stderr)
        return 2

    # 构建输入并分析
    try:
        inp = OptionInput(
            spot=args.spot,
            strike=args.strike,
            option_type=args.option_type,
            expiry=args.expiry,
            vol=args.vol,
            rate=args.rate,
            dividend=args.dividend,
        )
        result = analyze_option(inp)
        print(format_result(result, inp))
        return 0
    except OptionError as e:
        print(f"{e.code}: {e.message}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"E008: 未预期异常: {str(e)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
