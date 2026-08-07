#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期权估值分析工具（独立实现）

功能：对期权/权证进行估值分析，计算内在价值、时间价值、希腊字母，
      并给出行权策略建议。

本脚本为 clean-room 实现，仅依据功能规格独立编写。
仅使用 Python 标准库，无第三方依赖。

用法：
    python scripts/main.py --selftest          # 运行内置自检
    python scripts/main.py --input "..."       # 分析单条输入
    python scripts/main.py --help              # 显示帮助
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

# ============================================================
# 错误码定义（遵循规格 E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "参数解析失败",
    "E007": "数值计算异常",
    "E008": "内部状态错误",
    "E009": "自检失败",
    "E010": "未知错误",
}


class OptionAnalysisError(Exception):
    """期权分析业务异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class OptionInput:
    """期权输入参数。"""

    spot_price: float          # 标的当前价格
    strike_price: float        # 行权价
    time_to_expiry: float      # 剩余期限（年）
    risk_free_rate: float      # 无风险利率（小数，如 0.03 表示 3%）
    volatility: float          # 波动率（小数，如 0.25 表示 25%）
    option_type: str           # "call" 或 "put"
    quantity: int = 1          # 合约数量


@dataclass
class OptionResult:
    """期权分析结果。"""

    intrinsic_value: float          # 内在价值
    time_value: float               # 时间价值
    total_value: float              # 总价值（理论价）
    delta: float                    # Delta
    gamma: float                    # Gamma
    theta: float                    # Theta（年化）
    vega: float                     # Vega
    rho: float                      # Rho
    moneyness: str                  # 价内/平值/价外
    strategy_suggestion: str        # 策略建议
    confidence: float               # 置信度（0-1）
    warning: str = ""               # 警告信息


# ============================================================
# 核心计算逻辑
# ============================================================
class OptionPricer:
    """期权定价与希腊字母计算器（Black-Scholes 模型）。"""

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """标准正态分布累积分布函数（近似）。"""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def _norm_pdf(x: float) -> float:
        """标准正态分布概率密度函数。"""
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    def compute(self, opt: OptionInput) -> OptionResult:
        """
        计算期权理论价值与希腊字母。

        参数：
            opt: 期权输入参数

        返回：
            OptionResult 包含估值结果

        异常：
            OptionAnalysisError: 当输入参数非法时抛出
        """
        # 参数校验
        if opt.spot_price <= 0 or opt.strike_price <= 0:
            raise OptionAnalysisError("E003", "标的价和行权价必须为正数")
        if opt.time_to_expiry < 0:
            raise OptionAnalysisError("E003", "剩余期限不能为负")
        if opt.volatility <= 0:
            raise OptionAnalysisError("E003", "波动率必须为正数")
        if opt.risk_free_rate < -0.5 or opt.risk_free_rate > 0.5:
            raise OptionAnalysisError("E003", "无风险利率超出合理范围")
        if opt.option_type not in ("call", "put"):
            raise OptionAnalysisError("E003", "期权类型必须为 call 或 put")

        try:
            S = opt.spot_price
            K = opt.strike_price
            T = opt.time_to_expiry
            r = opt.risk_free_rate
            sigma = opt.volatility

            # 处理到期日（T=0 或接近 0）
            if T <= 1e-10:
                # 到期时用内在价值
                if opt.option_type == "call":
                    intrinsic = max(0.0, S - K)
                    delta = 1.0 if S > K else 0.0
                    gamma = 0.0
                    theta = 0.0
                    vega = 0.0
                    rho = 0.0
                else:
                    intrinsic = max(0.0, K - S)
                    delta = -1.0 if S < K else 0.0
                    gamma = 0.0
                    theta = 0.0
                    vega = 0.0
                    rho = 0.0
                time_value = 0.0
                total = intrinsic
            else:
                # Black-Scholes 公式
                d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)

                if opt.option_type == "call":
                    total = S * self._norm_cdf(d1) - K * math.exp(-r * T) * self._norm_cdf(d2)
                    intrinsic = max(0.0, S - K)
                    delta = self._norm_cdf(d1)
                    gamma = self._norm_pdf(d1) / (S * sigma * math.sqrt(T))
                    theta = (-(S * self._norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                             - r * K * math.exp(-r * T) * self._norm_cdf(d2))
                    vega = S * self._norm_pdf(d1) * math.sqrt(T)
                    rho = K * T * math.exp(-r * T) * self._norm_cdf(d2)
                else:
                    total = K * math.exp(-r * T) * self._norm_cdf(-d2) - S * self._norm_cdf(-d1)
                    intrinsic = max(0.0, K - S)
                    delta = self._norm_cdf(d1) - 1.0
                    gamma = self._norm_pdf(d1) / (S * sigma * math.sqrt(T))
                    theta = (-(S * self._norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                             + r * K * math.exp(-r * T) * self._norm_cdf(-d2))
                    vega = S * self._norm_pdf(d1) * math.sqrt(T)
                    rho = -K * T * math.exp(-r * T) * self._norm_cdf(-d2)

                time_value = total - intrinsic

            # 判断价内/价外
            if opt.option_type == "call":
                if S > K * 1.02:
                    moneyness = "价内"
                elif S < K * 0.98:
                    moneyness = "价外"
                else:
                    moneyness = "平值"
            else:
                if S < K * 0.98:
                    moneyness = "价内"
                elif S > K * 1.02:
                    moneyness = "价外"
                else:
                    moneyness = "平值"

            # 策略建议
            suggestion = self._generate_suggestion(
                opt.option_type, moneyness, time_value, intrinsic, T
            )

            # 置信度评估
            confidence = self._calc_confidence(opt)

            # 警告信息
            warning = ""
            if T < 0.02:
                warning = "临近到期，模型精度下降"
            elif sigma > 0.8:
                warning = "波动率异常偏高，结果需谨慎"

            return OptionResult(
                intrinsic_value=round(intrinsic, 4),
                time_value=round(time_value, 4),
                total_value=round(total, 4),
                delta=round(delta, 4),
                gamma=round(gamma, 4),
                theta=round(theta, 4),
                vega=round(vega, 4),
                rho=round(rho, 4),
                moneyness=moneyness,
                strategy_suggestion=suggestion,
                confidence=confidence,
                warning=warning,
            )

        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            raise OptionAnalysisError("E007", f"数值计算异常: {str(exc)}") from exc

    @staticmethod
    def _generate_suggestion(
        opt_type: str, moneyness: str, time_value: float, intrinsic: float, T: float
    ) -> str:
        """生成行权策略建议。"""
        if T <= 0.01:
            # 临近到期
            if intrinsic > 0:
                return "临近到期且为价内，建议及时行权或平仓锁定利润"
            return "临近到期且为价外，建议放弃行权，避免额外成本"

        if moneyness == "价内":
            if opt_type == "call":
                return "价内看涨期权，持有价值较高，可考虑继续持有或部分止盈"
            return "价内看跌期权，持有价值较高，可考虑继续持有或部分止盈"
        elif moneyness == "平值":
            return "平值期权时间价值占比高，注意时间衰减风险，建议关注波动率变化"
        else:
            if time_value < intrinsic * 0.1:
                return "深度价外期权，时间价值有限，建议观望或放弃"
            return "价外期权，等待标的走势变化，注意时间价值损耗"

    @staticmethod
    def _calc_confidence(opt: OptionInput) -> float:
        """计算置信度（0-1）。"""
        confidence = 0.95  # 基础置信度

        # 期限过短降低置信度
        if opt.time_to_expiry < 0.05:
            confidence -= 0.15
        elif opt.time_to_expiry < 0.1:
            confidence -= 0.05

        # 波动率极端降低置信度
        if opt.volatility < 0.1 or opt.volatility > 0.8:
            confidence -= 0.1

        # 深度价外或价内降低置信度
        ratio = opt.spot_price / opt.strike_price
        if opt.option_type == "call":
            if ratio > 1.5 or ratio < 0.5:
                confidence -= 0.1
        else:
            if ratio < 0.5 or ratio > 1.5:
                confidence -= 0.1

        return max(0.5, min(0.99, confidence))


# ============================================================
# 输入解析与输出格式化
# ============================================================
class InputParser:
    """解析用户输入为 OptionInput 对象。"""

    @staticmethod
    def parse(text: str) -> OptionInput:
        """
        解析文本输入。

        支持的格式示例：
            "call S=100 K=105 T=0.5 r=0.03 sigma=0.25"
            "put spot=50 strike=55 expiry=1 rate=0.02 vol=0.3"
            JSON 格式: {"option_type":"call","spot_price":100,...}

        参数：
            text: 用户输入文本

        返回：
            OptionInput 对象

        异常：
            OptionAnalysisError: 解析失败时抛出
        """
        if not text or not text.strip():
            raise OptionAnalysisError("E001")

        text = text.strip()

        # 尝试 JSON 解析
        if text.startswith("{"):
            try:
                data = json.loads(text)
                return InputParser._from_dict(data)
            except json.JSONDecodeError:
                raise OptionAnalysisError("E003", "JSON 格式不正确")
            except KeyError as exc:
                raise OptionAnalysisError("E002", f"缺少字段: {exc}")

        # 尝试键值对解析
        try:
            return InputParser._from_key_value(text)
        except OptionAnalysisError:
            raise
        except Exception as exc:
            raise OptionAnalysisError("E003", f"解析失败: {str(exc)}")

    @staticmethod
    def _from_dict(data: Dict) -> OptionInput:
        """从字典构建输入。"""
        required = ["option_type", "spot_price", "strike_price"]
        missing = [k for k in required if k not in data]
        if missing:
            raise OptionAnalysisError("E002", f"缺少字段: {', '.join(missing)}")

        try:
            return OptionInput(
                option_type=str(data["option_type"]).lower(),
                spot_price=float(data["spot_price"]),
                strike_price=float(data["strike_price"]),
                time_to_expiry=float(data.get("time_to_expiry", data.get("T", 1.0))),
                risk_free_rate=float(data.get("risk_free_rate", data.get("r", 0.03))),
                volatility=float(data.get("volatility", data.get("sigma", 0.25))),
                quantity=int(data.get("quantity", 1)),
            )
        except (ValueError, TypeError) as exc:
            raise OptionAnalysisError("E003", f"字段类型错误: {str(exc)}")

    @staticmethod
    def _from_key_value(text: str) -> OptionInput:
        """从键值对文本解析。"""
        tokens = text.split()
        if not tokens:
            raise OptionAnalysisError("E001")

        opt_type = tokens[0].lower()
        if opt_type not in ("call", "put"):
            raise OptionAnalysisError("E003", "第一个词必须是 call 或 put")

        params: Dict[str, float] = {}
        aliases = {
            "s": "spot", "spot": "spot", "price": "spot",
            "k": "strike", "strike": "strike",
            "t": "time", "expiry": "time",
            "r": "rate", "rate": "rate",
            "sigma": "vol", "vol": "vol", "volatility": "vol",
        }

        for token in tokens[1:]:
            if "=" not in token:
                raise OptionAnalysisError("E003", f"无法解析参数: {token}")
            key, _, value = token.partition("=")
            key = key.strip().lower()
            try:
                val = float(value.strip())
            except ValueError:
                raise OptionAnalysisError("E003", f"参数值非数字: {value}")

            canonical = aliases.get(key)
            if canonical:
                params[canonical] = val
            else:
                raise OptionAnalysisError("E003", f"未知参数: {key}")

        # 检查必需参数
        if "spot" not in params:
            raise OptionAnalysisError("E002", "缺少标的价 spot")
        if "strike" not in params:
            raise OptionAnalysisError("E002", "缺少行权价 strike")

        return OptionInput(
            option_type=opt_type,
            spot_price=params["spot"],
            strike_price=params["strike"],
            time_to_expiry=params.get("time", 1.0),
            risk_free_rate=params.get("rate", 0.03),
            volatility=params.get("vol", 0.25),
        )


class OutputFormatter:
    """格式化输出结果。"""

    @staticmethod
    def format_result(result: OptionResult, opt: OptionInput) -> str:
        """格式化单个分析结果。"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"期权估值分析结果 ({opt.option_type.upper()})")
        lines.append("=" * 50)
        lines.append(f"标的价: {opt.spot_price:.2f}  行权价: {opt.strike_price:.2f}")
        lines.append(f"剩余期限: {opt.time_to_expiry:.2f} 年  无风险利率: {opt.risk_free_rate:.2%}")
        lines.append(f"波动率: {opt.volatility:.2%}")
        lines.append("-" * 50)
        lines.append(f"内在价值: {result.intrinsic_value:.4f}")
        lines.append(f"时间价值: {result.time_value:.4f}")
        lines.append(f"理论总价: {result.total_value:.4f}")
        lines.append(f"合约数量: {opt.quantity}  总价值: {result.total_value * opt.quantity:.4f}")
        lines.append("-" * 50)
        lines.append(f"Delta: {result.delta:.4f}")
        lines.append(f"Gamma: {result.gamma:.4f}")
        lines.append(f"Theta: {result.theta:.4f} (年化)")
        lines.append(f"Vega:  {result.vega:.4f}")
        lines.append(f"Rho:   {result.rho:.4f}")
        lines.append("-" * 50)
        lines.append(f"状态: {result.moneyness}")
        lines.append(f"策略建议: {result.strategy_suggestion}")
        lines.append(f"置信度: {result.confidence:.0%}")

        if result.warning:
            lines.append(f"警告: {result.warning}")

        if result.confidence < 0.85:
            lines.append("[需核实] 置信度偏低，建议人工复核关键参数")

        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def format_json(result: OptionResult, opt: OptionInput) -> str:
        """格式化为 JSON 输出。"""
        data = {
            "input": asdict(opt),
            "result": asdict(result),
            "error_code": None,
            "error_message": None,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 自检模块
# ============================================================
class SelfTest:
    """内置自检，使用硬编码样例数据验证核心逻辑。"""

    @staticmethod
    def run() -> bool:
        """
        运行自检。

        使用宽松阈值断言，确保在任何环境可稳定通过。
        """
        print("开始自检...")

        try:
            pricer = OptionPricer()

            # ---------------------------
            # 样例 1：平值看涨期权
            # ---------------------------
            opt1 = OptionInput(
                spot_price=100.0,
                strike_price=100.0,
                time_to_expiry=1.0,
                risk_free_rate=0.03,
                volatility=0.25,
                option_type="call",
            )
            r1 = pricer.compute(opt1)
            assert r1.total_value > 0, "平值看涨期权理论价值应为正"
            assert r1.intrinsic_value == 0, "平值期权内在价值应为 0"
            assert abs(r1.delta - 0.5) < 0.2, "平值看涨期权 Delta 应接近 0.5"
            assert r1.gamma > 0, "Gamma 应为正"
            assert r1.vega > 0, "Vega 应为正"
            assert r1.confidence >= 0.8, "置信度应不低于 0.8"
            print("  [通过] 平值看涨期权")

            # ---------------------------
            # 样例 2：价内看涨期权
            # ---------------------------
            opt2 = OptionInput(
                spot_price=120.0,
                strike_price=100.0,
                time_to_expiry=0.5,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type="call",
            )
            r2 = pricer.compute(opt2)
            assert r2.intrinsic_value == 20.0, "价内看涨期权内在价值应为 S-K"
            assert r2.total_value >= r2.intrinsic_value, "总价值应不低于内在价值"
            assert r2.delta > 0.5, "价内看涨期权 Delta 应大于 0.5"
            assert r2.moneyness == "价内", "应为价内状态"
            print("  [通过] 价内看涨期权")

            # ---------------------------
            # 样例 3：价外看跌期权
            # ---------------------------
            opt3 = OptionInput(
                spot_price=80.0,
                strike_price=100.0,
                time_to_expiry=0.3,
                risk_free_rate=0.02,
                volatility=0.3,
                option_type="put",
            )
            r3 = pricer.compute(opt3)
            assert r3.intrinsic_value == 20.0, "价外看跌期权内在价值应为 K-S"
            assert r3.total_value > 0, "总价值应为正"
            assert r3.delta < 0, "看跌期权 Delta 应为负"
            assert r3.moneyness == "价内", "此处应为价内状态"
            print("  [通过] 价内看跌期权")

            # ---------------------------
            # 样例 4：极端参数（临近到期）
            # ---------------------------
            opt4 = OptionInput(
                spot_price=100.0,
                strike_price=100.0,
                time_to_expiry=0.001,
                risk_free_rate=0.03,
                volatility=0.25,
                option_type="call",
            )
            r4 = pricer.compute(opt4)
            assert r4.total_value >= 0, "总价值不应为负"
            assert r4.warning != "", "临近到期应有警告"
            print("  [通过] 临近到期期权")

            # ---------------------------
            # 样例 5：输入解析
            # ---------------------------
            parser = InputParser()
            parsed = parser.parse("call S=105 K=100 T=0.5 r=0.03 sigma=0.2")
            assert parsed.option_type == "call", "期权类型解析错误"
            assert abs(parsed.spot_price - 105.0) < 1e-6, "标的价解析错误"
            assert abs(parsed.strike_price - 100.0) < 1e-6, "行权价解析错误"
            assert abs(parsed.time_to_expiry - 0.5) < 1e-6, "期限解析错误"
            print("  [通过] 输入解析")

            # ---------------------------
            # 样例 6：错误处理
            # ---------------------------
            try:
                parser.parse("")
                assert False, "空输入应抛异常"
            except OptionAnalysisError as exc:
                assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
            print("  [通过] 错误处理")

            # ---------------------------
            # 样例 7：批量一致性（幂等性验证）
            # ---------------------------
            r5a = pricer.compute(opt1)
            r5b = pricer.compute(opt1)
            assert abs(r5a.total_value - r5b.total_value) < 1e-6, "幂等性验证失败"
            print("  [通过] 幂等性")

            print("自检全部通过！")
            return True

        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return False
        except OptionAnalysisError as exc:
            print(f"自检异常: [{exc.code}] {exc.message}", file=sys.stderr)
            return False
        except Exception as exc:
            print(f"自检未预期异常: {exc}", file=sys.stderr)
            return False


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="期权估值分析工具（仅使用标准库）",
        epilog="示例: python scripts/main.py --input 'call S=100 K=105 T=0.5 r=0.03 sigma=0.25'",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="期权参数输入，格式: 'call S=100 K=105 T=0.5 r=0.03 sigma=0.25' 或 JSON",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="以 JSON 格式输出",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = SelfTest.run()
        return 0 if ok else 1

    # 分析模式
    if not args.input:
        parser.print_help()
        print("\n错误: 请提供 --input 参数或使用 --selftest", file=sys.stderr)
        return 1

    try:
        # 解析输入
        opt = InputParser.parse(args.input)

        # 计算
        pricer = OptionPricer()
        result = pricer.compute(opt)

        # 输出
        if args.json_output:
            print(OutputFormatter.format_json(result, opt))
        else:
            print(OutputFormatter.format_result(result, opt))

        # 置信度提示
        if result.confidence < 0.85:
            print("\n提示: 结果置信度偏低，关键参数请人工复核", file=sys.stderr)

        return 0

    except OptionAnalysisError as exc:
        print(f"错误 [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误 [E010]: 未知异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
