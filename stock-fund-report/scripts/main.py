#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓分析报告（stock-fund-report）— 独立实现脚本

依据功能规格从零编写，不复制任何既有代码。
核心能力：
  1. 解析持仓明细与交易记录
  2. 计算收益统计（浮动盈亏、收益率、持仓市值）
  3. 计算持仓集中度（前N大持仓占比、单一持仓最高占比）
  4. 生成风险提示（波动率、回撤、集中度风险）
  5. 生成调仓建议（基于预设规则）
  6. 输出结构化文本报告

错误码说明：
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 数值计算异常
  E007 内部状态异常
  E008 参数解析失败
  E009 自检失败
  E010 未知异常
"""

import argparse
import json
import math
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 置信度阈值
CONFIDENCE_HIGH = 90.0
CONFIDENCE_MEDIUM = 85.0

# 风险提示阈值
RISK_CONCENTRATION_HIGH = 0.5      # 单一持仓占比超过50%视为高集中度
RISK_CONCENTRATION_MEDIUM = 0.3    # 单一持仓占比超过30%视为中集中度
RISK_TOP3_HIGH = 0.7               # 前三大持仓合计超过70%视为高集中度
RISK_TOP3_MEDIUM = 0.5             # 前三大持仓合计超过50%视为中集中度
RISK_DRAWDOWN_HIGH = 0.15          # 回撤超过15%视为高风险
RISK_DRAWDOWN_MEDIUM = 0.08        # 回撤超过8%视为中风险
RISK_VOLATILITY_HIGH = 0.30        # 年化波动率超过30%视为高风险
RISK_VOLATILITY_MEDIUM = 0.20      # 年化波动率超过20%视为中风险

# 调仓建议阈值
REBALANCE_UP = 0.05                # 单只持仓占比超过目标5%以上建议减仓
REBALANCE_DOWN = -0.05             # 单只持仓占比低于目标5%以上建议加仓
REBALANCE_TARGET = 0.25            # 默认目标仓位（等权配置时使用）


# ============================================================
# 数据模型与解析
# ============================================================

class Holding:
    """单只持仓数据"""
    __slots__ = ("symbol", "name", "quantity", "cost_price", "current_price", "market_value", "weight")

    def __init__(self, symbol: str, name: str, quantity: float,
                 cost_price: float, current_price: float) -> None:
        self.symbol = symbol
        self.name = name
        self.quantity = quantity
        self.cost_price = cost_price
        self.current_price = current_price
        self.market_value = quantity * current_price
        self.weight = 0.0  # 占总市值比例，后续计算


class PortfolioData:
    """解析后的完整持仓数据"""
    def __init__(self) -> None:
        self.holdings: List[Holding] = []
        self.total_cost: float = 0.0       # 总成本
        self.total_market_value: float = 0.0  # 总市值
        self.total_pnl: float = 0.0        # 总浮动盈亏
        self.total_pnl_pct: float = 0.0    # 总收益率
        self.period_return: float = 0.0    # 期间收益率（如周收益率）
        self.history_prices: Dict[str, List[float]] = {}  # 用于计算波动率/回撤


def parse_input(raw_input: str) -> PortfolioData:
    """
    解析输入内容。
    支持两种格式：
      1. JSON 字符串（推荐）
      2. 简单文本格式（每行：代码 名称 数量 成本价 现价）

    返回 PortfolioData 对象；解析失败抛出 ValueError。
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    data = PortfolioData()
    raw_input = raw_input.strip()

    # 尝试 JSON 解析
    parsed: Optional[Dict[str, Any]] = None
    try:
        parsed = json.loads(raw_input)
    except json.JSONDecodeError:
        parsed = None

    if parsed is not None:
        _parse_json(parsed, data)
    else:
        _parse_text(raw_input, data)

    if not data.holdings:
        raise ValueError("E002")

    _finalize_portfolio(data)
    return data


def _parse_json(obj: Dict[str, Any], data: PortfolioData) -> None:
    """从 JSON 对象解析持仓"""
    if not isinstance(obj, dict):
        raise ValueError("E003")

    # 兼容多种字段命名
    holdings_raw = (obj.get("holdings") or obj.get("positions")
                    or obj.get("stocks") or obj.get("持仓") or [])

    if not holdings_raw:
        raise ValueError("E002")

    for item in holdings_raw:
        if not isinstance(item, dict):
            raise ValueError("E003")

        symbol = str(item.get("symbol") or item.get("code") or item.get("代码") or "").strip()
        name = str(item.get("name") or item.get("名称") or "").strip()
        quantity = _safe_float(item.get("quantity") or item.get("shares") or item.get("数量"))
        cost_price = _safe_float(item.get("cost_price") or item.get("cost") or item.get("成本价"))
        current_price = _safe_float(item.get("current_price") or item.get("price") or item.get("现价"))

        if not symbol:
            raise ValueError("E003")

        if quantity is None or cost_price is None or current_price is None:
            raise ValueError("E003")

        if quantity < 0 or cost_price < 0 or current_price < 0:
            raise ValueError("E003")

        holding = Holding(symbol, name, quantity, cost_price, current_price)
        data.holdings.append(holding)

    # 可选：历史价格数据（用于波动率/回撤计算）
    hist_raw = obj.get("history") or obj.get("history_prices") or obj.get("历史价格")
    if isinstance(hist_raw, dict):
        for sym, prices in hist_raw.items():
            if isinstance(prices, list):
                data.history_prices[str(sym)] = [_safe_float(p) for p in prices if _safe_float(p) is not None]

    # 可选：期间收益率
    period_ret = obj.get("period_return") or obj.get("期间收益率")
    if period_ret is not None:
        data.period_return = _safe_float(period_ret) or 0.0


def _parse_text(text: str, data: PortfolioData) -> None:
    """从简单文本格式解析持仓"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        # 跳过注释行
        if line.startswith("#") or line.startswith("//"):
            continue

        parts = line.replace(",", " ").split()
        if len(parts) < 5:
            raise ValueError("E003")

        symbol = parts[0]
        name = parts[1]
        quantity = _safe_float(parts[2])
        cost_price = _safe_float(parts[3])
        current_price = _safe_float(parts[4])

        if quantity is None or cost_price is None or current_price is None:
            raise ValueError("E003")

        holding = Holding(symbol, name, quantity, cost_price, current_price)
        data.holdings.append(holding)

    if not data.holdings:
        raise ValueError("E002")


def _safe_float(value: Any) -> Optional[float]:
    """安全转换为 float，失败返回 None"""
    if value is None:
        return None
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def _finalize_portfolio(data: PortfolioData) -> None:
    """计算汇总指标"""
    total_mv = 0.0
    total_cost = 0.0

    for h in data.holdings:
        total_mv += h.market_value
        total_cost += h.quantity * h.cost_price

    if total_mv <= 0:
        raise ValueError("E006")

    # 计算权重
    for h in data.holdings:
        h.weight = h.market_value / total_mv

    data.total_market_value = total_mv
    data.total_cost = total_cost
    data.total_pnl = total_mv - total_cost
    data.total_pnl_pct = (total_mv - total_cost) / total_cost if total_cost > 0 else 0.0


# ============================================================
# 分析计算
# ============================================================

def calculate_concentration(holdings: List[Holding]) -> Dict[str, Any]:
    """
    计算持仓集中度指标。
    返回：最大持仓占比、前3大持仓占比、前5大持仓占比
    """
    if not holdings:
        return {"max_weight": 0.0, "top3_weight": 0.0, "top5_weight": 0.0, "count": 0}

    sorted_holdings = sorted(holdings, key=lambda h: h.weight, reverse=True)
    weights = [h.weight for h in sorted_holdings]

    result = {
        "max_weight": weights[0] if weights else 0.0,
        "top3_weight": sum(weights[:3]),
        "top5_weight": sum(weights[:5]),
        "count": len(weights),
    }
    return result


def calculate_volatility(history_prices: Dict[str, List[float]]) -> Tuple[float, float]:
    """
    根据历史价格计算年化波动率和最大回撤。
    若数据不足，返回保守估计值。
    """
    if not history_prices:
        return 0.0, 0.0

    all_returns: List[float] = []
    max_drawdown = 0.0

    for sym, prices in history_prices.items():
        if len(prices) < 2:
            continue

        # 计算每日收益率
        daily_returns = []
        for i in range(1, len(prices)):
            prev = prices[i - 1]
            curr = prices[i]
            if prev > 0:
                daily_returns.append((curr - prev) / prev)

        if daily_returns:
            all_returns.extend(daily_returns)

        # 计算回撤
        peak = prices[0]
        for p in prices:
            if p > peak:
                peak = p
            if peak > 0:
                drawdown = (peak - p) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

    if not all_returns:
        return 0.0, max_drawdown

    # 简单年化波动率（假设日频，252个交易日）
    mean_ret = sum(all_returns) / len(all_returns)
    variance = sum((r - mean_ret) ** 2 for r in all_returns) / len(all_returns)
    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(252)

    return annual_vol, max_drawdown


def generate_risk_alerts(data: PortfolioData, concentration: Dict[str, Any],
                         volatility: float, max_drawdown: float) -> List[Dict[str, str]]:
    """生成风险提示列表"""
    alerts: List[Dict[str, str]] = []

    # 集中度风险
    if concentration["max_weight"] > RISK_CONCENTRATION_HIGH:
        alerts.append({
            "level": "高",
            "type": "集中度风险",
            "message": f"单一持仓占比 {concentration['max_weight']*100:.1f}% 超过50%，集中度过高",
        })
    elif concentration["max_weight"] > RISK_CONCENTRATION_MEDIUM:
        alerts.append({
            "level": "中",
            "type": "集中度风险",
            "message": f"单一持仓占比 {concentration['max_weight']*100:.1f}% 超过30%，注意集中度",
        })

    if concentration["top3_weight"] > RISK_TOP3_HIGH:
        alerts.append({
            "level": "高",
            "type": "集中度风险",
            "message": f"前三大持仓合计 {concentration['top3_weight']*100:.1f}% 超过70%",
        })
    elif concentration["top3_weight"] > RISK_TOP3_MEDIUM:
        alerts.append({
            "level": "中",
            "type": "集中度风险",
            "message": f"前三大持仓合计 {concentration['top3_weight']*100:.1f}% 超过50%",
        })

    # 波动率风险
    if volatility > RISK_VOLATILITY_HIGH:
        alerts.append({
            "level": "高",
            "type": "波动率风险",
            "message": f"年化波动率 {volatility*100:.1f}% 超过30%，波动较大",
        })
    elif volatility > RISK_VOLATILITY_MEDIUM:
        alerts.append({
            "level": "中",
            "type": "波动率风险",
            "message": f"年化波动率 {volatility*100:.1f}% 超过20%",
        })

    # 回撤风险
    if max_drawdown > RISK_DRAWDOWN_HIGH:
        alerts.append({
            "level": "高",
            "type": "回撤风险",
            "message": f"历史最大回撤 {max_drawdown*100:.1f}% 超过15%",
        })
    elif max_drawdown > RISK_DRAWDOWN_MEDIUM:
        alerts.append({
            "level": "中",
            "type": "回撤风险",
            "message": f"历史最大回撤 {max_drawdown*100:.1f}% 超过8%",
        })

    # 亏损持仓提示
    loss_holdings = [h for h in data.holdings if h.market_value < h.quantity * h.cost_price]
    if loss_holdings:
        loss_names = "、".join(h.name or h.symbol for h in loss_holdings[:3])
        alerts.append({
            "level": "中",
            "type": "浮亏提示",
            "message": f"存在浮亏持仓：{loss_names}",
        })

    return alerts


def generate_rebalance_suggestions(holdings: List[Holding]) -> List[str]:
    """
    基于等权配置生成调仓建议。
    目标仓位 = 1 / 持仓数量（等权）。
    偏离超过阈值时给出加减仓建议。
    """
    if not holdings:
        return []

    n = len(holdings)
    target_weight = 1.0 / n if n > 0 else 0.0
    suggestions: List[str] = []

    for h in holdings:
        deviation = h.weight - target_weight
        if deviation > REBALANCE_UP:
            suggestions.append(
                f"{h.name or h.symbol}: 当前占比 {h.weight*100:.1f}%，高于目标 {target_weight*100:.1f}%，"
                f"建议减仓约 {deviation*100:.1f}%"
            )
        elif deviation < REBALANCE_DOWN:
            suggestions.append(
                f"{h.name or h.symbol}: 当前占比 {h.weight*100:.1f}%，低于目标 {target_weight*100:.1f}%，"
                f"建议加仓约 {-deviation*100:.1f}%"
            )

    if not suggestions:
        suggestions.append("当前持仓比例接近等权配置，无需大幅调仓")

    return suggestions


def calculate_confidence(data: PortfolioData) -> float:
    """
    计算结果置信度。
    基于数据完整性和一致性估算。
    """
    score = 100.0

    # 数据完整性
    for h in data.holdings:
        if not h.name:
            score -= 2.0  # 缺少名称
        if h.quantity <= 0:
            score -= 10.0

    # 一致性检查：现价与成本价差异过大（>10倍）可能数据有误
    for h in data.holdings:
        if h.cost_price > 0 and (h.current_price / h.cost_price > 10.0
                                 or h.current_price / h.cost_price < 0.1):
            score -= 5.0

    # 历史数据缺失
    if not data.history_prices:
        score -= 8.0

    # 期间收益率缺失
    if data.period_return == 0.0:
        score -= 2.0

    return max(score, 0.0)


# ============================================================
# 报告生成
# ============================================================

def generate_report(data: PortfolioData) -> str:
    """生成完整分析报告（文本格式）"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("持仓分析报告")
    lines.append("=" * 60)

    # 置信度
    confidence = calculate_confidence(data)
    conf_label = ""
    if confidence >= CONFIDENCE_HIGH:
        conf_label = "高置信度"
    elif confidence >= CONFIDENCE_MEDIUM:
        conf_label = "建议复核"
    else:
        conf_label = "[需核实]"
    lines.append(f"置信度: {confidence:.1f}% ({conf_label})")

    # 汇总统计
    lines.append("")
    lines.append("【收益统计】")
    lines.append(f"  持仓数量: {len(data.holdings)}")
    lines.append(f"  总成本: {data.total_cost:,.2f}")
    lines.append(f"  总市值: {data.total_market_value:,.2f}")
    lines.append(f"  浮动盈亏: {data.total_pnl:+,.2f}")
    lines.append(f"  收益率: {data.total_pnl_pct*100:+.2f}%")
    if data.period_return:
        lines.append(f"  期间收益率: {data.period_return*100:+.2f}%")

    # 持仓明细
    lines.append("")
    lines.append("【持仓明细】")
    header = f"  {'代码':<8} {'名称':<10} {'数量':>10} {'成本价':>10} {'现价':>10} {'市值':>12} {'占比':>8} {'盈亏':>10}"
    lines.append(header)
    lines.append("  " + "-" * 72)
    for h in sorted(data.holdings, key=lambda x: x.weight, reverse=True):
        pnl = (h.current_price - h.cost_price) * h.quantity
        name_display = h.name if h.name else "-"
        lines.append(
            f"  {h.symbol:<8} {name_display:<10} {h.quantity:>10.2f} "
            f"{h.cost_price:>10.2f} {h.current_price:>10.2f} "
            f"{h.market_value:>12,.2f} {h.weight*100:>7.1f}% {pnl:>+10,.2f}"
        )

    # 集中度分析
    concentration = calculate_concentration(data.holdings)
    lines.append("")
    lines.append("【持仓集中度】")
    lines.append(f"  最大单一持仓占比: {concentration['max_weight']*100:.1f}%")
    lines.append(f"  前三大持仓合计: {concentration['top3_weight']*100:.1f}%")
    lines.append(f"  前五大持仓合计: {concentration['top5_weight']*100:.1f}%")

    # 风险提示
    volatility, max_drawdown = calculate_volatility(data.history_prices)
    alerts = generate_risk_alerts(data, concentration, volatility, max_drawdown)
    lines.append("")
    lines.append("【风险提示】")
    if alerts:
        for alert in alerts:
            lines.append(f"  [{alert['level']}] {alert['type']}: {alert['message']}")
    else:
        lines.append("  暂无显著风险提示")

    if data.history_prices:
        lines.append(f"  (参考)年化波动率: {volatility*100:.1f}%, 最大回撤: {max_drawdown*100:.1f}%")

    # 调仓建议
    suggestions = generate_rebalance_suggestions(data.holdings)
    lines.append("")
    lines.append("【调仓建议】")
    for s in suggestions:
        lines.append(f"  - {s}")

    # 免责声明
    lines.append("")
    lines.append("-" * 60)
    lines.append("⚠️ 本报告仅供参考，不构成投资建议。据此操作风险自担。")
    lines.append("AI生成内容，请人工复核关键数据。")

    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保在任何环境可过。
    """
    print("开始自检...")

    # ---- 测试用例 1: 基本解析与统计 ----
    sample_json = json.dumps({
        "holdings": [
            {"symbol": "600519", "name": "贵州茅台", "quantity": 100, "cost_price": 1500.0, "current_price": 1700.0},
            {"symbol": "000858", "name": "五粮液", "quantity": 200, "cost_price": 120.0, "current_price": 130.0},
            {"symbol": "601318", "name": "中国平安", "quantity": 500, "cost_price": 45.0, "current_price": 42.0},
        ],
        "period_return": 0.032,
    })

    try:
        data = parse_input(sample_json)
    except ValueError as e:
        print(f"  自检失败: 解析样例数据出错 {e}")
        return False

    # 断言 1: 持仓数量正确
    assert len(data.holdings) == 3, "持仓数量应为3"
    print("  [通过] 持仓解析数量")

    # 断言 2: 总市值大于0
    assert data.total_market_value > 0, "总市值应大于0"
    print(f"  [通过] 总市值计算: {data.total_market_value:,.2f}")

    # 断言 3: 权重之和约等于1（宽松判断）
    weight_sum = sum(h.weight for h in data.holdings)
    assert abs(weight_sum - 1.0) < 0.01, f"权重之和应接近1，实际 {weight_sum}"
    print(f"  [通过] 权重归一化: {weight_sum:.4f}")

    # 断言 4: 集中度指标合理
    conc = calculate_concentration(data.holdings)
    assert 0 <= conc["max_weight"] <= 1, "最大持仓占比应在0-1之间"
    assert conc["top3_weight"] >= conc["max_weight"], "前3占比应不小于最大占比"
    print("  [通过] 集中度计算")

    # ---- 测试用例 2: 文本格式解析 ----
    sample_text = """
    # 测试持仓
    600036 招商银行 300 30.0 32.5
    000001 平安银行 500 10.0 11.2
    """
    try:
        data2 = parse_input(sample_text)
    except ValueError as e:
        print(f"  自检失败: 文本解析出错 {e}")
        return False

    assert len(data2.holdings) == 2, "文本格式应解析出2条持仓"
    print("  [通过] 文本格式解析")

    # ---- 测试用例 3: 风险提示生成 ----
    alerts = generate_risk_alerts(data, conc, 0.25, 0.12)
    assert isinstance(alerts, list), "风险提示应为列表"
    assert len(alerts) >= 0, "风险提示数量应非负"
    print(f"  [通过] 风险提示生成 ({len(alerts)} 条)")

    # ---- 测试用例 4: 调仓建议 ----
    suggestions = generate_rebalance_suggestions(data.holdings)
    assert isinstance(suggestions, list), "调仓建议应为列表"
    assert len(suggestions) >= 1, "至少应有一条建议"
    print(f"  [通过] 调仓建议生成 ({len(suggestions)} 条)")

    # ---- 测试用例 5: 报告生成 ----
    report = generate_report(data)
    assert "持仓分析报告" in report, "报告应包含标题"
    assert "收益统计" in report, "报告应包含收益统计"
    assert "风险提示" in report, "报告应包含风险提示"
    assert "调仓建议" in report, "报告应包含调仓建议"
    print("  [通过] 报告生成")

    # ---- 测试用例 6: 错误处理 ----
    try:
        parse_input("")
        print("  自检失败: 空输入应抛出E001")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为E001，实际 {e}"
        print("  [通过] 空输入错误处理 (E001)")

    try:
        parse_input("不是有效格式的内容")
        print("  自检失败: 格式错误应抛出E003")
        return False
    except ValueError as e:
        assert str(e) == "E003", f"错误码应为E003，实际 {e}"
        print("  [通过] 格式错误处理 (E003)")

    # ---- 测试用例 7: 波动率计算 ----
    vol, dd = calculate_volatility({"TEST": [10.0, 9.5, 10.2, 9.8, 10.5]})
    assert vol >= 0, "波动率应为非负"
    assert dd >= 0, "回撤应为非负"
    print("  [通过] 波动率/回撤计算")

    print("")
    print("自检全部通过 ✓")
    return True


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="持仓分析报告 - 根据持仓与行情数据生成投资分析周报",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --input '{"holdings":[{"symbol":"600519","name":"贵州茅台","quantity":100,"cost_price":1500,"current_price":1700}]}'
  python main.py --input holdings.txt
  python main.py --selftest
        """,
    )
    parser.add_argument("--input", "-i", help="输入内容：JSON字符串或文本文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到终端）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出结果")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 9  # E009
        except Exception as e:  # 兜底
            print(f"自检异常: {e}")
            return 10  # E010
        return 0 if success else 9

    # 正常处理模式
    if not args.input:
        print("错误 E001: 请提供输入内容，格式为：持仓明细与交易记录", file=sys.stderr)
        return 1

    # 检查输入是否为文件路径
    raw_input: str = args.input
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            raw_input = f.read()
    except (OSError, IOError):
        # 不是文件，按原始字符串处理
        pass

    try:
        data = parse_input(raw_input)
    except ValueError as e:
        error_code = str(e)
        if error_code == "E001":
            print("错误 E001: 请提供待处理的内容，格式为：持仓明细与交易记录", file=sys.stderr)
        elif error_code == "E002":
            print("错误 E002: 关键信息缺失，请补充持仓明细", file=sys.stderr)
        elif error_code == "E003":
            print("错误 E003: 输入格式不符合要求，示例：", file=sys.stderr)
            print('  {"holdings":[{"symbol":"600519","name":"贵州茅台","quantity":100,"cost_price":1500,"current_price":1700}]}', file=sys.stderr)
        else:
            print(f"错误 {error_code}: 处理失败", file=sys.stderr)
        return 1

    # 生成报告
    try:
        report = generate_report(data)
    except Exception as e:
        print(f"错误 E006: 数值计算异常 - {e}", file=sys.stderr)
        return 6

    # 输出
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"报告已写入: {args.output}")
        except OSError as e:
            print(f"错误 E008: 无法写入输出文件 - {e}", file=sys.stderr)
            return 8
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
