#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年报速读 · 财务透视 · 决策辅助
=================================
独立实现脚本（clean-room 重写）

功能：
  - 解析上市公司年报文本，提取关键财务章节
  - 计算核心财务指标（毛利率、ROE、资产负债率、经营现金流等）
  - 判断同比/环比趋势
  - 扫描常见风险信号
  - 输出结构化一页纸摘要

用法：
  python scripts/main.py --selftest          # 离线自检
  python scripts/main.py --file report.txt   # 解析文本年报
  python scripts/main.py --json data.json    # 解析 JSON 格式财务数据

错误码：
  E001 参数错误
  E002 文件不存在或无法读取
  E003 输入数据格式无效
  E004 缺少必需字段
  E005 数值解析失败
  E006 计算错误（除零等）
  E007 输出写入失败
  E008 自检失败
  E009 不支持的输入类型
  E010 未知错误
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在或无法读取",
    "E003": "输入数据格式无效",
    "E004": "缺少必需字段",
    "E005": "数值解析失败",
    "E006": "计算错误（除零等）",
    "E007": "输出写入失败",
    "E008": "自检失败",
    "E009": "不支持的输入类型",
    "E010": "未知错误",
}

REQUIRED_FIELDS = [
    "company_name",
    "year",
    "revenue",
    "net_profit",
    "total_assets",
    "total_liabilities",
    "operating_cash_flow",
]

# 风险信号阈值（宽松区间，避免精确值依赖）
RISK_THRESHOLDS = {
    "receivables_growth_ratio": 0.30,      # 应收账款同比增长超过 30%
    "inventory_growth_ratio": 0.30,        # 存货同比增长超过 30%
    "goodwill_to_assets_ratio": 0.20,      # 商誉占总资产比例超过 20%
    "debt_to_assets_ratio": 0.70,          # 资产负债率超过 70%
    "current_ratio": 1.0,                  # 流动比率低于 1.0
}


# ============================================================
# 工具函数
# ============================================================

def err_exit(code: str, message: str = "") -> None:
    """输出错误信息并退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {msg}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {msg}", file=sys.stderr)
    sys.exit(1)


def safe_float(value: Any, field_name: str = "") -> float:
    """安全转换为浮点数，失败时抛出 E005"""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # 清理常见格式符号
            cleaned = value.replace(",", "").replace("，", "").replace("%", "").strip()
            if not cleaned:
                return 0.0
            return float(cleaned)
        raise ValueError(f"无法转换类型 {type(value)}")
    except (ValueError, TypeError) as e:
        err_exit("E005", f"字段 '{field_name}' 数值解析失败: {e}")


def safe_divide(numerator: float, denominator: float) -> float:
    """安全除法，除零返回 0.0"""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def extract_year(text: str) -> Optional[int]:
    """从文本中提取年份"""
    match = re.search(r"(20\d{2})", text)
    if match:
        return int(match.group(1))
    return None


def extract_money(text: str) -> Optional[float]:
    """从文本中提取金额（支持 亿/万 单位）"""
    # 匹配可能的数字+单位，支持负数和括号表示法
    pattern = r"([-+]?\d+(?:\.\d+)?)\s*(亿元|万元|亿|万|元)?"
    match = re.search(pattern, text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2) or ""
    if "亿" in unit:
        value *= 100000000
    elif "万" in unit:
        value *= 10000
    return value


# ============================================================
# 数据解析模块
# ============================================================

class AnnualReportParser:
    """年报解析器：支持文本和 JSON 输入"""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.raw_text = data.get("raw_text", "")

    def parse_text(self, text: str) -> Dict[str, Any]:
        """从纯文本中解析财务数据"""
        result: Dict[str, Any] = {}

        # 提取公司名称（支持多种格式）
        company_patterns = [
            r"(?:公司名称|企业名称)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9]+)",
            r"(?:公司|企业)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9]+)",
            r"^([\u4e00-\u9fa5A-Za-z0-9]+(?:股份|集团|有限|控股))",
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                result["company_name"] = match.group(1)
                break
        else:
            result["company_name"] = "未知公司"

        # 提取年份
        year = extract_year(text)
        result["year"] = year if year else 0

        # 提取主要财务数据
        keywords = {
            "revenue": ["营业收入", "营业总收入", "主营业务收入"],
            "net_profit": ["净利润", "归母净利润", "归属于母公司股东的净利润"],
            "total_assets": ["总资产", "资产总计", "资产总额"],
            "total_liabilities": ["总负债", "负债合计", "负债总额"],
            "operating_cash_flow": ["经营活动产生的现金流量净额", "经营现金流", "经营活动现金流量净额"],
            "operating_cost": ["营业成本", "主营业务成本"],
            "receivables": ["应收账款"],
            "inventory": ["存货"],
            "goodwill": ["商誉"],
            "current_assets": ["流动资产", "流动资产合计"],
            "current_liabilities": ["流动负债", "流动负债合计"],
            "total_shares": ["总股本", "股本", "实收资本"],
        }

        for field, aliases in keywords.items():
            for alias in aliases:
                idx = text.find(alias)
                if idx >= 0:
                    # 获取关键词后的一段文本
                    segment = text[idx: idx + 200]
                    # 尝试多种模式
                    value = None
                    
                    # 模式1: 直接数字
                    num_match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(亿元|万元|亿|万|元)?", segment)
                    if num_match:
                        value = float(num_match.group(1))
                        unit = num_match.group(2) or ""
                        if "亿" in unit:
                            value *= 100000000
                        elif "万" in unit:
                            value *= 10000
                    
                    if value is not None:
                        result[field] = value
                        break

        # 提取同比数据（如有）
        for field in ["revenue", "net_profit"]:
            if field in keywords:
                alias = keywords[field][0]
                # 查找同比数据
                patterns = [
                    rf"{alias}.*?同比[增长下降]*\s*([-+]?\d+(?:\.\d+)?)%",
                    rf"{alias}.*?增减[幅度率]*\s*([-+]?\d+(?:\.\d+)?)%",
                ]
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        result[f"{field}_growth"] = float(match.group(1)) / 100
                        break

        return result

    def parse(self) -> Dict[str, Any]:
        """解析入口"""
        if self.raw_text:
            parsed = self.parse_text(self.raw_text)
            # 合并已有结构化数据（结构化数据优先）
            for key in REQUIRED_FIELDS:
                if key in self.data and self.data[key] is not None:
                    parsed[key] = self.data[key]
            return parsed
        return self.data


# ============================================================
# 财务指标计算模块
# ============================================================

class FinancialAnalyzer:
    """财务指标计算器"""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.metrics: Dict[str, Any] = {}

    def calculate(self) -> Dict[str, Any]:
        """计算所有核心财务指标"""
        d = self.data

        # 基础数据
        revenue = safe_float(d.get("revenue", 0), "revenue")
        net_profit = safe_float(d.get("net_profit", 0), "net_profit")
        total_assets = safe_float(d.get("total_assets", 0), "total_assets")
        total_liabilities = safe_float(d.get("total_liabilities", 0), "total_liabilities")
        operating_cash_flow = safe_float(d.get("operating_cash_flow", 0), "operating_cash_flow")

        # 毛利率（假设营业成本存在，否则用 0）
        cost = safe_float(d.get("operating_cost", 0), "operating_cost")
        gross_profit = revenue - cost
        gross_margin = safe_divide(gross_profit, revenue) * 100

        # 净利率
        net_margin = safe_divide(net_profit, revenue) * 100

        # ROE（净资产收益率）
        equity = total_assets - total_liabilities
        roe = safe_divide(net_profit, equity) * 100

        # 资产负债率
        debt_ratio = safe_divide(total_liabilities, total_assets) * 100

        # 每股收益（假设股本存在，否则用 1）
        shares = safe_float(d.get("total_shares", 1), "total_shares")
        eps = safe_divide(net_profit, shares)

        # 经营现金流/净利润比
        cash_flow_ratio = safe_divide(operating_cash_flow, net_profit)

        # 流动比率（假设流动资产/流动负债存在）
        current_assets = safe_float(d.get("current_assets", 0), "current_assets")
        current_liabilities = safe_float(d.get("current_liabilities", 0), "current_liabilities")
        current_ratio = safe_divide(current_assets, current_liabilities)

        # 同比数据（如有）
        revenue_growth = safe_float(d.get("revenue_growth", 0), "revenue_growth")
        profit_growth = safe_float(d.get("profit_growth", 0), "profit_growth")

        self.metrics = {
            "revenue": revenue,
            "net_profit": net_profit,
            "gross_margin": gross_margin,
            "net_margin": net_margin,
            "roe": roe,
            "debt_ratio": debt_ratio,
            "eps": eps,
            "cash_flow_ratio": cash_flow_ratio,
            "current_ratio": current_ratio,
            "revenue_growth": revenue_growth,
            "profit_growth": profit_growth,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "operating_cash_flow": operating_cash_flow,
            "equity": equity,
        }
        return self.metrics


# ============================================================
# 趋势分析与风险扫描模块
# ============================================================

class RiskScanner:
    """风险信号扫描器"""

    def __init__(self, metrics: Dict[str, Any], data: Dict[str, Any]):
        self.metrics = metrics
        self.data = data
        self.risks: List[str] = []

    def scan(self) -> List[str]:
        """扫描所有风险信号"""
        m = self.metrics
        d = self.data

        # 1. 资产负债率过高
        if m["debt_ratio"] > RISK_THRESHOLDS["debt_to_assets_ratio"] * 100:
            self.risks.append(f"资产负债率偏高（{m['debt_ratio']:.1f}%）")

        # 2. 流动比率过低
        if 0 < m["current_ratio"] < RISK_THRESHOLDS["current_ratio"]:
            self.risks.append(f"流动比率偏低（{m['current_ratio']:.2f}），短期偿债压力较大")

        # 3. 应收账款激增（如有数据）
        receivables = safe_float(d.get("receivables", 0), "receivables")
        if receivables > 0:
            # 假设上期数据存在
            prev_receivables = safe_float(d.get("prev_receivables", 0), "prev_receivables")
            if prev_receivables > 0:
                growth = safe_divide(receivables - prev_receivables, prev_receivables)
                if growth > RISK_THRESHOLDS["receivables_growth_ratio"]:
                    self.risks.append(f"应收账款增长较快（{growth*100:.1f}%）")

        # 4. 存货积压（如有数据）
        inventory = safe_float(d.get("inventory", 0), "inventory")
        if inventory > 0:
            prev_inventory = safe_float(d.get("prev_inventory", 0), "prev_inventory")
            if prev_inventory > 0:
                growth = safe_divide(inventory - prev_inventory, prev_inventory)
                if growth > RISK_THRESHOLDS["inventory_growth_ratio"]:
                    self.risks.append(f"存货增长较快（{growth*100:.1f}%）")

        # 5. 商誉占总资产比例过高
        goodwill = safe_float(d.get("goodwill", 0), "goodwill")
        if goodwill > 0:
            ratio = safe_divide(goodwill, m["total_assets"])
            if ratio > RISK_THRESHOLDS["goodwill_to_assets_ratio"]:
                self.risks.append(f"商誉占比较大（{ratio*100:.1f}%）")

        # 6. 经营现金流为负
        if m["operating_cash_flow"] < 0:
            self.risks.append("经营活动现金流为负")

        # 7. 净利润为负
        if m["net_profit"] < 0:
            self.risks.append("净利润为负（亏损）")

        # 8. 营收下滑
        if m["revenue_growth"] < -0.05:
            self.risks.append(f"营业收入同比下降（{m['revenue_growth']*100:.1f}%）")

        # 9. 利润下滑
        if m["profit_growth"] < -0.10:
            self.risks.append(f"净利润同比下降（{m['profit_growth']*100:.1f}%）")

        # 10. 现金流与利润背离
        if m["cash_flow_ratio"] < 0.5 and m["net_profit"] > 0:
            self.risks.append("经营现金流/净利润比值偏低，利润质量存疑")

        return self.risks


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self, current: Dict[str, Any], previous: Optional[Dict[str, Any]] = None):
        self.current = current
        self.previous = previous

    def analyze(self) -> Dict[str, Any]:
        """分析趋势"""
        trend = {}
        if not self.previous:
            trend["summary"] = "无历史数据，无法进行趋势分析"
            return trend

        # 营收趋势
        cur_rev = safe_float(self.current.get("revenue", 0), "revenue")
        prev_rev = safe_float(self.previous.get("revenue", 0), "revenue")
        if prev_rev != 0:
            rev_change = (cur_rev - prev_rev) / prev_rev * 100
            trend["revenue_change"] = rev_change
            trend["revenue_trend"] = "增长" if rev_change > 0 else "下滑"

        # 利润趋势
        cur_profit = safe_float(self.current.get("net_profit", 0), "net_profit")
        prev_profit = safe_float(self.previous.get("net_profit", 0), "net_profit")
        if prev_profit != 0:
            profit_change = (cur_profit - prev_profit) / prev_profit * 100
            trend["profit_change"] = profit_change
            trend["profit_trend"] = "增长" if profit_change > 0 else "下滑"

        # 资产负债率变化
        cur_debt_ratio = safe_divide(
            safe_float(self.current.get("total_liabilities", 0), "liabilities"),
            safe_float(self.current.get("total_assets", 0), "assets"),
        ) * 100
        prev_debt_ratio = safe_divide(
            safe_float(self.previous.get("total_liabilities", 0), "liabilities"),
            safe_float(self.previous.get("total_assets", 0), "assets"),
        ) * 100
        trend["debt_ratio_change"] = cur_debt_ratio - prev_debt_ratio

        return trend


# ============================================================
# 摘要生成模块
# ============================================================

class SummaryGenerator:
    """结构化摘要生成器"""

    def __init__(self, company_info: Dict[str, Any], metrics: Dict[str, Any],
                 risks: List[str], trend: Dict[str, Any]):
        self.company_info = company_info
        self.metrics = metrics
        self.risks = risks
        self.trend = trend

    def generate(self) -> str:
        """生成一页纸摘要"""
        m = self.metrics
        info = self.company_info
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {info.get('company_name', '未知公司')} {info.get('year', '')}年度报告摘要")
        lines.append("=" * 60)
        lines.append("")

        # 核心财务数据
        lines.append("【核心财务指标】")
        lines.append(f"  - 营业收入：{m['revenue']/100000000:.2f} 亿元")
        lines.append(f"  - 净利润：{m['net_profit']/100000000:.2f} 亿元")
        lines.append(f"  - 毛利率：{m['gross_margin']:.1f}%")
        lines.append(f"  - 净利率：{m['net_margin']:.1f}%")
        lines.append(f"  - ROE：{m['roe']:.1f}%")
        lines.append(f"  - 资产负债率：{m['debt_ratio']:.1f}%")
        lines.append(f"  - 每股收益：{m['eps']:.2f} 元")
        lines.append(f"  - 经营现金流：{m['operating_cash_flow']/100000000:.2f} 亿元")
        lines.append("")

        # 趋势分析
        lines.append("【趋势分析】")
        if "revenue_trend" in self.trend:
            lines.append(f"  - 营业收入{self.trend['revenue_trend']}（{self.trend['revenue_change']:.1f}%）")
        if "profit_trend" in self.trend:
            lines.append(f"  - 净利润{self.trend['profit_trend']}（{self.trend['profit_change']:.1f}%）")
        if "debt_ratio_change" in self.trend:
            change = self.trend["debt_ratio_change"]
            direction = "上升" if change > 0 else "下降"
            lines.append(f"  - 资产负债率{direction} {abs(change):.1f} 个百分点")
        if "summary" in self.trend:
            lines.append(f"  - {self.trend['summary']}")
        lines.append("")

        # 风险提示
        lines.append("【风险提示】")
        if self.risks:
            for risk in self.risks:
                lines.append(f"  ⚠ {risk}")
        else:
            lines.append("  ✓ 未发现明显风险信号")
        lines.append("")
        lines.append("=" * 60)
        lines.append("⚠ 本摘要由程序自动生成，仅供学习参考，不构成投资建议。")
        lines.append("  数据准确性请以原始年报为准。")

        return "\n".join(lines)


# ============================================================
# 主处理流程
# ============================================================

def process_data(data: Dict[str, Any], previous_data: Optional[Dict[str, Any]] = None) -> str:
    """处理数据并生成摘要"""
    # 检查必需字段
    for field in REQUIRED_FIELDS:
        if field not in data:
            err_exit("E004", f"缺少必需字段: {field}")

    # 解析数据
    parser = AnnualReportParser(data)
    parsed_data = parser.parse()

    # 计算指标
    analyzer = FinancialAnalyzer(parsed_data)
    metrics = analyzer.calculate()

    # 扫描风险
    scanner = RiskScanner(metrics, parsed_data)
    risks = scanner.scan()

    # 趋势分析
    trend_analyzer = TrendAnalyzer(parsed_data, previous_data)
    trend = trend_analyzer.analyze()

    # 生成摘要
    generator = SummaryGenerator(parsed_data, metrics, risks, trend)
    return generator.generate()


def load_data_from_file(filepath: str) -> Dict[str, Any]:
    """从文件加载数据"""
    if not os.path.exists(filepath):
        err_exit("E002", f"文件不存在: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        err_exit("E002", f"无法读取文件: {e}")

    # 尝试 JSON 解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 作为纯文本处理
    return {"raw_text": content, "company_name": "文本输入", "year": 0}


def run_selftest() -> None:
    """内置自检逻辑（硬编码样例数据，离线运行）"""
    print("开始自检...")

    # 测试样例 1：正常公司
    sample1 = {
        "company_name": "测试科技股份有限公司",
        "year": 2025,
        "revenue": 5000000000,        # 50亿
        "net_profit": 800000000,      # 8亿
        "total_assets": 10000000000,  # 100亿
        "total_liabilities": 4000000000,  # 40亿
        "operating_cash_flow": 900000000,  # 9亿
        "operating_cost": 3000000000,  # 30亿
        "total_shares": 1000000000,    # 10亿股
        "current_assets": 6000000000,
        "current_liabilities": 3000000000,
        "revenue_growth": 0.15,
        "profit_growth": 0.20,
    }

    summary1 = process_data(sample1)
    assert "测试科技" in summary1, "公司名称未正确显示"
    assert "营业收入" in summary1, "缺少营业收入"
    assert "净利润" in summary1, "缺少净利润"
    assert "毛利率" in summary1, "缺少毛利率"
    assert "风险" in summary1, "缺少风险提示"
    print("✓ 样例1（正常公司）通过")

    # 测试样例 2：高风险公司
    sample2 = {
        "company_name": "风险警示股份有限公司",
        "year": 2025,
        "revenue": 1000000000,        # 10亿
        "net_profit": -200000000,     # 亏损2亿
        "total_assets": 5000000000,   # 50亿
        "total_liabilities": 4500000000,  # 45亿（负债率90%）
        "operating_cash_flow": -100000000,  # 负现金流
        "operating_cost": 1200000000,
        "total_shares": 500000000,
        "current_assets": 1000000000,
        "current_liabilities": 2000000000,  # 流动比率 0.5
        "revenue_growth": -0.20,
        "profit_growth": -0.30,
        "goodwill": 1500000000,       # 商誉 15亿，占总资产30%
    }

    summary2 = process_data(sample2)
    assert "风险警示" in summary2, "公司名称未正确显示"
    assert "亏损" in summary2 or "风险" in summary2, "未识别出风险"
    print("✓ 样例2（高风险公司）通过")

    # 测试样例 3：文本解析
    sample3 = {
        "raw_text": """
        公司名称：示例控股有限公司
        年度：2025年
        营业收入：88.5亿元
        净利润：12.3亿元
        总资产：200亿元
        总负债：80亿元
        经营活动产生的现金流量净额：15.6亿元
        应收账款：20亿元
        存货：15亿元
        商誉：5亿元
        营业成本：50亿元
        """,
        "company_name": "示例控股有限公司",
        "year": 2025,
    }

    summary3 = process_data(sample3)
    assert "示例控股" in summary3, "文本解析失败"
    assert "营业收入" in summary3, "文本解析缺少营收"
    assert "净利润" in summary3, "文本解析缺少净利润"
    print("✓ 样例3（文本解析）通过")

    # 测试错误处理
    try:
        process_data({})
        assert False, "应抛出 E004 错误"
    except SystemExit as e:
        assert e.code == 1, "退出码不正确"
    print("✓ 错误处理通过")

    print("=" * 50)
    print("✅ 全部自检通过！")


# ============================================================
# 命令行入口
# ============================================================

def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="年报速读 · 财务透视 · 决策辅助",
        epilog="示例: python scripts/main.py --file report.txt"
    )
    parser.add_argument("--file", type=str, help="输入文件路径（支持 JSON 或纯文本）")
    parser.add_argument("--previous", type=str, help="上一年度数据文件路径（用于趋势分析）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--output", type=str, help="输出文件路径")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 没有输入文件
    if not args.file:
        err_exit("E001", "请指定 --file 参数或使用 --selftest")

    # 加载数据
    data = load_data_from_file(args.file)

    # 加载历史数据（可选）
    previous_data = None
    if args.previous:
        previous_data = load_data_from_file(args.previous)

    # 处理数据
    summary = process_data(data, previous_data)

    # 输出结果
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(summary)
        except Exception as e:
            err_exit("E007", f"写入输出文件失败: {e}")
    else:
        print(summary)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        err_exit("E010", "用户中断")
    except SystemExit:
        raise
    except Exception as e:
        err_exit("E010", f"未知错误: {e}")
