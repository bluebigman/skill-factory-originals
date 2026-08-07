#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓分析报告 - 独立实现脚本
根据持仓与行情数据生成投资分析周报：收益统计、持仓集中度、风险提示、调仓建议
仅依赖标准库，支持 --selftest 离线自检
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部计算错误",
    "E007": "参数错误",
    "E008": "数据异常",
    "E009": "输出生成失败",
    "E010": "未知错误",
}


class ReportError(Exception):
    """业务异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------- 数据结构 ----------

class Position:
    """单只持仓"""

    def __init__(self, symbol: str, name: str, shares: float, cost_price: float):
        self.symbol = symbol          # 代码
        self.name = name              # 名称
        self.shares = shares          # 持仓数量
        self.cost_price = cost_price  # 成本价

    def market_value(self, price: float) -> float:
        """市值"""
        return self.shares * price

    def profit(self, price: float) -> float:
        """浮动盈亏"""
        return (price - self.cost_price) * self.shares

    def profit_pct(self, price: float) -> float:
        """盈亏百分比"""
        if self.cost_price == 0:
            return 0.0
        return (price - self.cost_price) / self.cost_price * 100.0


class MarketData:
    """行情数据"""

    def __init__(self, prices: Dict[str, float]):
        self.prices = prices  # symbol -> 当前价


class ReportResult:
    """分析报告结果"""

    def __init__(self):
        self.total_market_value = 0.0     # 总市值
        self.total_cost = 0.0             # 总成本
        self.total_profit = 0.0           # 总盈亏
        self.total_profit_pct = 0.0       # 总盈亏百分比
        self.positions_detail: List[Dict] = []  # 明细
        self.concentration: Dict[str, float] = {}  # 集中度
        self.risk_level = "低"             # 风险等级
        self.suggestions: List[str] = []   # 建议
        self.confidence = 0.0              # 置信度
        self.generated_at = ""             # 生成时间


# ---------- 核心逻辑 ----------

def validate_input(positions: List[Position], market: MarketData) -> None:
    """校验输入数据"""
    if not positions:
        raise ReportError("E001", "请提供待处理的内容，格式为：持仓明细与交易记录")
    if not market or not market.prices:
        raise ReportError("E002", "缺少行情数据，请补充当前价格信息")
    for pos in positions:
        if pos.shares < 0:
            raise ReportError("E003", f"持仓数量不能为负: {pos.symbol}")
        if pos.cost_price < 0:
            raise ReportError("E003", f"成本价不能为负: {pos.symbol}")
        if pos.symbol not in market.prices:
            raise ReportError("E002", f"缺少 {pos.symbol} 的行情数据")
        if market.prices[pos.symbol] < 0:
            raise ReportError("E008", f"行情价格异常: {pos.symbol}")


def calculate_report(positions: List[Position], market: MarketData) -> ReportResult:
    """核心计算：收益统计、集中度、风险、建议"""
    validate_input(positions, market)

    result = ReportResult()
    result.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 收益统计
    total_value = 0.0
    total_cost = 0.0
    detail_list = []

    for pos in positions:
        price = market.prices[pos.symbol]
        value = pos.market_value(price)
        cost = pos.shares * pos.cost_price
        profit = pos.profit(price)
        profit_pct = pos.profit_pct(price)

        total_value += value
        total_cost += cost
        total_profit = total_value - total_cost

        detail_list.append({
            "symbol": pos.symbol,
            "name": pos.name,
            "shares": pos.shares,
            "cost_price": pos.cost_price,
            "current_price": price,
            "market_value": value,
            "profit": profit,
            "profit_pct": profit_pct,
            "weight": 0.0,  # 稍后计算
        })

    if total_value <= 0:
        raise ReportError("E008", "总市值为零，无法生成报告")

    # 计算权重
    for item in detail_list:
        item["weight"] = item["market_value"] / total_value * 100.0

    result.total_market_value = total_value
    result.total_cost = total_cost
    result.total_profit = total_value - total_cost
    result.total_profit_pct = (result.total_profit / total_cost * 100.0) if total_cost > 0 else 0.0
    result.positions_detail = detail_list

    # 2. 持仓集中度（前三大权重之和）
    weights = sorted([item["weight"] for item in detail_list], reverse=True)
    top3_weight = sum(weights[:3])
    result.concentration = {
        "top1": weights[0] if weights else 0.0,
        "top3": top3_weight,
        "position_count": len(positions),
    }

    # 3. 风险等级判断
    if top3_weight >= 70:
        result.risk_level = "高"
    elif top3_weight >= 50:
        result.risk_level = "中"
    else:
        result.risk_level = "低"

    # 4. 调仓建议
    suggestions = []
    # 集中度建议
    if result.risk_level == "高":
        suggestions.append("持仓集中度过高，建议适当分散投资，降低单一标的占比")
    elif result.risk_level == "中":
        suggestions.append("持仓集中度中等，可关注分散化机会")

    # 亏损标的建议
    for item in detail_list:
        if item["profit_pct"] < -10:
            suggestions.append(
                f"{item['name']}({item['symbol']}) 亏损 {abs(item['profit_pct']):.1f}%，"
                "建议评估基本面是否变化，设置止损纪律"
            )
        elif item["profit_pct"] > 20:
            suggestions.append(
                f"{item['name']}({item['symbol']}) 盈利 {item['profit_pct']:.1f}%，"
                "可考虑部分止盈锁定收益"
            )

    # 若持仓过少
    if len(positions) < 3:
        suggestions.append("持仓标的较少，建议增加相关性低的品种以平滑波动")

    # 若无明显问题
    if not suggestions:
        suggestions.append("当前持仓结构较为合理，建议维持定期复盘")

    result.suggestions = suggestions

    # 5. 置信度评估
    # 数据完整且计算成功，置信度高
    missing_fields = 0
    for pos in positions:
        if not pos.name:
            missing_fields += 1
    if missing_fields == 0:
        result.confidence = 95.0
    else:
        result.confidence = 88.0  # 部分名称缺失，建议复核

    return result


def format_report(result: ReportResult, include_detail: bool = True) -> str:
    """生成文本报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("持仓分析周报")
    lines.append("=" * 50)
    lines.append(f"生成时间: {result.generated_at}")
    lines.append(f"置信度: {result.confidence:.0f}%")
    if result.confidence < 90:
        lines.append("[建议复核] 部分信息不完整，请人工核对关键数据")
    lines.append("")

    # 收益统计
    lines.append("【收益统计】")
    lines.append(f"总市值: {result.total_market_value:,.2f}")
    lines.append(f"总成本: {result.total_cost:,.2f}")
    lines.append(f"总盈亏: {result.total_profit:+,.2f}")
    lines.append(f"总收益率: {result.total_profit_pct:+.2f}%")
    lines.append("")

    # 集中度
    lines.append("【持仓集中度】")
    lines.append(f"持仓数量: {result.concentration['position_count']} 只")
    lines.append(f"第一大权重: {result.concentration['top1']:.1f}%")
    lines.append(f"前三大权重合计: {result.concentration['top3']:.1f}%")
    lines.append(f"风险等级: {result.risk_level}")
    lines.append("")

    # 明细
    if include_detail:
        lines.append("【持仓明细】")
        lines.append(f"{'代码':<10}{'名称':<12}{'数量':>10}{'成本':>10}{'现价':>10}{'市值':>14}{'盈亏':>12}{'权重':>8}")
        for item in result.positions_detail:
            lines.append(
                f"{item['symbol']:<10}{item['name']:<12}{item['shares']:>10.0f}"
                f"{item['cost_price']:>10.2f}{item['current_price']:>10.2f}"
                f"{item['market_value']:>14,.0f}{item['profit']:>+12,.0f}"
                f"{item['weight']:>7.1f}%"
            )
        lines.append("")

    # 建议
    lines.append("【调仓建议】")
    for i, suggestion in enumerate(result.suggestions, 1):
        lines.append(f"{i}. {suggestion}")
    lines.append("")

    # 免责声明
    lines.append("-" * 50)
    lines.append("免责声明: 本报告仅供学习参考，不构成投资建议。")
    lines.append("投资有风险，决策需谨慎，请咨询持证专业人士。")
    lines.append("=" * 50)

    return "\n".join(lines)


def generate_report(positions: List[Position], market: MarketData, include_detail: bool = True) -> str:
    """生成完整报告文本（主入口函数）"""
    try:
        result = calculate_report(positions, market)
        return format_report(result, include_detail)
    except ReportError:
        raise
    except Exception as e:
        raise ReportError("E006", f"内部计算错误: {str(e)}")


# ---------- 自检模块 ----------

def run_selftest() -> int:
    """离线自检核心逻辑，使用内置硬编码数据"""
    print("=== 持仓分析报告 自检开始 ===")
    passed = 0
    total = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name}")

    # --- 测试用例 1: 正常场景 ---
    print("\n[测试用例 1] 正常持仓分析")
    positions = [
        Position("600519", "贵州茅台", 100, 1500.0),
        Position("000858", "五粮液", 200, 120.0),
        Position("601318", "中国平安", 500, 40.0),
    ]
    market = MarketData({
        "600519": 1600.0,
        "000858": 130.0,
        "601318": 45.0,
    })

    result = calculate_report(positions, market)

    # 总市值 = 100*1600 + 200*130 + 500*45 = 160000 + 26000 + 22500 = 208500
    check("总市值大于0", result.total_market_value > 0)
    check("总市值在合理范围", 200000 < result.total_market_value < 220000)
    check("总盈亏为正（行情上涨）", result.total_profit > 0)
    check("持仓明细数量正确", len(result.positions_detail) == 3)
    check("集中度 top3 接近100%", result.concentration["top3"] > 90)
    check("风险等级为高", result.risk_level == "高")
    check("有调仓建议", len(result.suggestions) > 0)
    check("置信度高", result.confidence >= 90)

    # --- 测试用例 2: 亏损场景 ---
    print("\n[测试用例 2] 亏损持仓")
    positions2 = [
        Position("000001", "平安银行", 1000, 15.0),
        Position("000002", "万科A", 500, 10.0),
    ]
    market2 = MarketData({
        "000001": 12.0,   # 亏损
        "000002": 8.0,    # 亏损
    })

    result2 = calculate_report(positions2, market2)
    check("总盈亏为负", result2.total_profit < 0)
    check("收益率小于0", result2.total_profit_pct < 0)
    check("有止损建议", any("止损" in s or "亏损" in s for s in result2.suggestions))
    check("持仓数小于3有分散建议", any("分散" in s or "相关性" in s for s in result2.suggestions))

    # --- 测试用例 3: 错误处理 ---
    print("\n[测试用例 3] 错误处理")
    try:
        calculate_report([], MarketData({"000001": 10.0}))
        check("空持仓应报错", False)
    except ReportError as e:
        check("空持仓应报错", e.code == "E001")

    try:
        calculate_report(
            [Position("000001", "测试", 100, 10.0)],
            MarketData({})  # 缺行情
        )
        check("缺行情应报错", False)
    except ReportError as e:
        check("缺行情应报错", e.code == "E002")

    try:
        calculate_report(
            [Position("000001", "测试", -5, 10.0)],  # 负数量
            MarketData({"000001": 10.0})
        )
        check("负数量应报错", False)
    except ReportError as e:
        check("负数量应报错", e.code == "E003")

    # --- 测试用例 4: 报告格式 ---
    print("\n[测试用例 4] 报告格式")
    report_text = format_report(result)
    check("报告包含标题", "持仓分析周报" in report_text)
    check("报告包含收益统计", "收益统计" in report_text)
    check("报告包含集中度", "集中度" in report_text)
    check("报告包含建议", "调仓建议" in report_text)
    check("报告包含免责声明", "免责声明" in report_text)
    check("报告包含置信度", "置信度" in report_text)

    # --- 测试用例 5: 边界情况 ---
    print("\n[测试用例 5] 边界情况")
    # 单只持仓
    result_single = calculate_report(
        [Position("000001", "单一持仓", 100, 10.0)],
        MarketData({"000001": 11.0})
    )
    check("单只持仓top1权重100%", abs(result_single.concentration["top1"] - 100.0) < 0.01)
    check("单只持仓风险高", result_single.risk_level == "高")

    # 成本为零
    result_zero_cost = calculate_report(
        [Position("000001", "零成本", 100, 0.0)],
        MarketData({"000001": 10.0})
    )
    check("零成本不报错", result_zero_cost.total_profit_pct == 0.0)

    # --- 测试用例 6: 完整流程 ---
    print("\n[测试用例 6] 完整报告生成")
    full_report = generate_report(positions, market)
    check("完整报告非空", len(full_report) > 100)
    check("包含所有持仓代码", "600519" in full_report and "000858" in full_report)
    check("包含建议内容", len(result.suggestions) > 0)

    # --- 总结 ---
    print(f"\n=== 自检完成: {passed}/{total} 通过 ===")
    if passed == total:
        print("全部通过 ✓")
        return 0
    else:
        print(f"存在失败项: {total - passed} 个")
        return 1


# ---------- 主入口 ----------

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="持仓分析报告 - 根据持仓与行情生成投资分析周报",
        epilog="示例: python main.py --input positions.json --output report.txt"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入 JSON 文件路径（含持仓与行情数据）"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出报告文件路径（默认输出到 stdout）"
    )
    parser.add_argument(
        "--no-detail",
        action="store_true",
        help="报告中不包含持仓明细"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取任何外部文件）"
    )
    return parser.parse_args()


def load_input_file(filepath: str) -> Tuple[List[Position], MarketData]:
    """从 JSON 文件加载输入数据"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ReportError("E001", f"输入文件不存在: {filepath}")
    except json.JSONDecodeError:
        raise ReportError("E003", f"输入文件格式错误（不是合法 JSON）: {filepath}")

    # 解析持仓
    positions_data = data.get("positions", [])
    if not positions_data:
        raise ReportError("E001", "输入中缺少 positions 字段")

    positions = []
    for item in positions_data:
        try:
            pos = Position(
                symbol=str(item["symbol"]),
                name=str(item.get("name", "")),
                shares=float(item["shares"]),
                cost_price=float(item["cost_price"]),
            )
            positions.append(pos)
        except (KeyError, TypeError, ValueError) as e:
            raise ReportError("E003", f"持仓数据格式错误: {item} ({str(e)})")

    # 解析行情
    prices_data = data.get("prices", {})
    if not prices_data:
        raise ReportError("E002", "输入中缺少 prices 行情数据")

    try:
        prices = {str(k): float(v) for k, v in prices_data.items()}
    except (TypeError, ValueError) as e:
        raise ReportError("E003", f"行情数据格式错误: {str(e)}")

    return positions, MarketData(prices)


def main() -> int:
    """主函数"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式：需要输入文件
    if not args.input:
        print("错误: 请提供输入文件 (--input) 或使用 --selftest 运行自检", file=sys.stderr)
        print("示例: python main.py --selftest", file=sys.stderr)
        print("示例: python main.py --input data.json --output report.txt", file=sys.stderr)
        return 2

    try:
        # 加载输入
        positions, market = load_input_file(args.input)

        # 生成报告
        report_text = generate_report(positions, market, include_detail=not args.no_detail)

        # 输出
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"报告已生成: {args.output}")
        else:
            print(report_text)

        return 0

    except ReportError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
