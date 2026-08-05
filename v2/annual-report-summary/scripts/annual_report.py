#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年报速读工具 - 解析上市公司财报文本，提取关键财务指标并生成投资决策简报
支持 .txt/.md/.csv 格式，内置20条评分规则，输出健康度打分与风险提示
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ==================== 指标识别规则 ====================
# 指标别名映射表：标准指标名 -> 可能的文本别名（正则表达式）
INDICATOR_ALIASES = {
    "营业收入": [r"营业收入", r"营业总收入", r"营收", r"总收入"],
    "净利润": [r"净利润", r"归母净利润", r"净利", r"纯利"],
    "毛利率": [r"毛利率", r"销售毛利率", r"主营业务毛利率"],
    "ROE": [r"净资产收益率", r"ROE", r"加权净资产收益率", r"股东权益回报率"],
    "资产负债率": [r"资产负债率", r"负债率", r"杠杆率"],
    "经营现金流": [r"经营现金流", r"经营活动现金流", r"经营性现金流", r"经营现金流量净额"],
    "研发投入": [r"研发投入", r"研发费用", r"研发支出", r"研发开支"],
    "分红": [r"分红", r"现金分红", r"股利", r"派息"],
}

# ==================== 评分规则字典（20条） ====================
# 每条规则: (指标名, 条件函数, 得分, 说明)
# 条件函数接收 (当前值, 上期值, 同比变化率) 返回布尔值
SCORE_RULES = [
    # 营业收入
    ("营业收入", lambda c, p, y: y > 20, 95, "营收高速增长(>20%)"),
    ("营业收入", lambda c, p, y: 10 < y <= 20, 85, "营收稳健增长(10-20%)"),
    ("营业收入", lambda c, p, y: 0 < y <= 10, 70, "营收小幅增长(0-10%)"),
    ("营业收入", lambda c, p, y: y <= 0, 40, "营收下滑或持平"),
    # 净利润
    ("净利润", lambda c, p, y: y > 30, 95, "净利润大幅增长(>30%)"),
    ("净利润", lambda c, p, y: 15 < y <= 30, 85, "净利润良好增长(15-30%)"),
    ("净利润", lambda c, p, y: 0 < y <= 15, 65, "净利润温和增长(0-15%)"),
    ("净利润", lambda c, p, y: y <= 0, 35, "净利润下滑或亏损"),
    # 毛利率
    ("毛利率", lambda c, p, y: c >= 40, 90, "高毛利率(>=40%)"),
    ("毛利率", lambda c, p, y: 25 <= c < 40, 75, "中等毛利率(25-40%)"),
    ("毛利率", lambda c, p, y: 10 <= c < 25, 55, "低毛利率(10-25%)"),
    ("毛利率", lambda c, p, y: c < 10, 30, "极低毛利率(<10%)"),
    # ROE
    ("ROE", lambda c, p, y: c >= 20, 95, "高ROE(>=20%)"),
    ("ROE", lambda c, p, y: 10 <= c < 20, 80, "良好ROE(10-20%)"),
    ("ROE", lambda c, p, y: 5 <= c < 10, 60, "一般ROE(5-10%)"),
    ("ROE", lambda c, p, y: c < 5, 35, "低ROE(<5%)"),
    # 资产负债率
    ("资产负债率", lambda c, p, y: c <= 40, 90, "低负债率(<=40%)"),
    ("资产负债率", lambda c, p, y: 40 < c <= 60, 70, "适中负债率(40-60%)"),
    ("资产负债率", lambda c, p, y: 60 < c <= 80, 45, "高负债率(60-80%)"),
    ("资产负债率", lambda c, p, y: c > 80, 20, "极高负债率(>80%)"),
]

# ==================== 核心解析函数 ====================

def extract_indicators_from_text(text: str) -> Dict[str, Tuple[float, Optional[float]]]:
    """
    从文本中提取指标值，返回 {标准指标名: (当前值, 上期值)}
    支持格式: "指标名: 数值" 或 "指标名 数值" 或 "指标名：数值（上期: 数值）"
    """
    extracted = {}
    for indicator, aliases in INDICATOR_ALIASES.items():
        for alias in aliases:
            # 匹配模式: 别名 + 分隔符 + 数字（支持千分位、负号、百分比）
            pattern = rf"{alias}\s*[：:]\s*(-?\d{{1,3}}(?:,\d{{3}})*\.?\d*)\s*%?"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                current = float(match.group(1).replace(",", ""))
                # 尝试查找上期值（支持括号内"上期: xx"或"上年: xx"）
                after_match = text[match.end():match.end()+200]
                prev_pattern = r"(?:上期|上年|上一年)[：:]\s*(-?\d{1,3}(?:,\d{3})*\.?\d*)\s*%?"
                prev_match = re.search(prev_pattern, after_match)
                prev = float(prev_match.group(1).replace(",", "")) if prev_match else None
                extracted[indicator] = (current, prev)
                break
            # 尝试匹配 "指标名: 数值 (上期: 数值)" 格式
            pattern2 = rf"{alias}\s*[：:]\s*(-?\d{{1,3}}(?:,\d{{3}})*\.?\d*)\s*%?\s*[\(（]?(?:上期|上年)[：:]\s*(-?\d{{1,3}}(?:,\d{{3}})*\.?\d*)\s*%?[\)）]?"
            match2 = re.search(pattern2, text, re.IGNORECASE)
            if match2:
                current = float(match2.group(1).replace(",", ""))
                prev = float(match2.group(2).replace(",", "")) if match2.group(2) else None
                extracted[indicator] = (current, prev)
                break
    return extracted

def extract_indicators_from_csv(filepath: Path) -> Dict[str, Tuple[float, Optional[float]]]:
    """从CSV文件提取指标，要求列: 指标名,数值,上期数值"""
    extracted = {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("指标名", "").strip()
            value = row.get("数值", "").strip()
            prev = row.get("上期数值", "").strip()
            if not name or not value:
                continue
            # 标准化指标名
            std_name = None
            for indicator, aliases in INDICATOR_ALIASES.items():
                if name in aliases or name == indicator:
                    std_name = indicator
                    break
            if std_name:
                try:
                    val = float(value.replace(",", "").replace("%", ""))
                    prev_val = float(prev.replace(",", "").replace("%", "")) if prev else None
                    extracted[std_name] = (val, prev_val)
                except ValueError:
                    continue
    return extracted

def calculate_yoy(current: float, prev: Optional[float]) -> Optional[float]:
    """计算同比变化率（百分比），上期缺失时返回None"""
    if prev is None or prev == 0:
        return None
    return (current - prev) / abs(prev) * 100

def score_indicators(indicators: Dict[str, Tuple[float, Optional[float]]]) -> Dict[str, Dict]:
    """
    对每个指标进行评分，返回 {指标名: {"score": int, "reason": str, "current": float, "prev": float, "yoy": float}}
    """
    results = {}
    for indicator, (current, prev) in indicators.items():
        yoy = calculate_yoy(current, prev)
        best_score = 50  # 默认中性分
        best_reason = "无匹配规则"
        for rule_indicator, condition, score, reason in SCORE_RULES:
            if rule_indicator == indicator and condition(current, prev, yoy):
                if score > best_score:
                    best_score = score
                    best_reason = reason
        results[indicator] = {
            "score": best_score,
            "reason": best_reason,
            "current": current,
            "prev": prev,
            "yoy": yoy,
        }
    return results

def generate_risk_notes(scored: Dict[str, Dict]) -> List[str]:
    """根据评分生成风险提示"""
    risks = []
    for indicator, data in scored.items():
        score = data["score"]
        if score < 40:
            risks.append(f"{indicator}表现较差（{score}分）：{data['reason']}")
        elif score < 60:
            risks.append(f"{indicator}需关注（{score}分）：{data['reason']}")
    if not risks:
        risks.append("整体财务指标健康，无明显风险")
    return risks

def generate_report(scored: Dict[str, Dict], year: int, format: str = "markdown") -> str:
    """生成投资决策简报"""
    total_score = sum(d["score"] for d in scored.values()) / len(scored) if scored else 0
    risks = generate_risk_notes(scored)

    if format == "markdown":
        lines = [
            f"# 年报速读报告（{year}年度）",
            "",
            f"**综合健康度评分：{total_score:.1f}/100**",
            "",
            "## 关键财务指标",
            "",
            "| 指标 | 当前值 | 上期值 | 同比变化 | 评分 | 评价 |",
            "|------|--------|--------|----------|------|------|",
        ]
        for indicator, data in scored.items():
            yoy_str = f"{data['yoy']:.1f}%" if data['yoy'] is not None else "N/A"
            prev_str = f"{data['prev']:.2f}" if data['prev'] is not None else "N/A"
            lines.append(
                f"| {indicator} | {data['current']:.2f} | {prev_str} | {yoy_str} | "
                f"{data['score']} | {data['reason']} |"
            )
        lines.append("")
        lines.append("## 风险提示")
        for risk in risks:
            lines.append(f"- {risk}")
        return "\n".join(lines)
    else:  # text
        lines = [
            f"=== 年报速读报告（{year}年度） ===",
            f"综合健康度评分：{total_score:.1f}/100",
            "",
            "关键财务指标：",
        ]
        for indicator, data in scored.items():
            yoy_str = f"{data['yoy']:.1f}%" if data['yoy'] is not None else "N/A"
            prev_str = f"{data['prev']:.2f}" if data['prev'] is not None else "N/A"
            lines.append(
                f"  {indicator}: {data['current']:.2f} (上期: {prev_str}, 同比: {yoy_str}) "
                f"[评分: {data['score']}] {data['reason']}"
            )
        lines.append("")
        lines.append("风险提示：")
        for risk in risks:
            lines.append(f"  - {risk}")
        return "\n".join(lines)

# ==================== 演示数据 ====================

def demo_data() -> str:
    """生成示例财报文本"""
    return """
    公司2025年度财务报告摘要：
    营业收入：1,234,567万元（上期：1,100,000万元）
    净利润：123,456万元（上期：100,000万元）
    毛利率：35.5%（上期：33.2%）
    净资产收益率（ROE）：18.2%（上期：16.8%）
    资产负债率：55.3%（上期：58.1%）
    经营活动现金流：98,765万元（上期：85,432万元）
    研发投入：45,678万元（上期：40,123万元）
    现金分红：30,000万元（上期：25,000万元）
    """

# ==================== 自测函数 ====================

def selftest():
    """验证提取和评分逻辑"""
    print("运行自测...")
    # 测试文本提取
    text = demo_data()
    indicators = extract_indicators_from_text(text)
    assert "营业收入" in indicators, "营业收入提取失败"
    assert "净利润" in indicators, "净利润提取失败"
    assert "毛利率" in indicators, "毛利率提取失败"
    assert "ROE" in indicators, "ROE提取失败"
    assert "资产负债率" in indicators, "资产负债率提取失败"
    assert "经营现金流" in indicators, "经营现金流提取失败"
    assert "研发投入" in indicators, "研发投入提取失败"
    assert "分红" in indicators, "分红提取失败"
    print(f"文本提取成功: {len(indicators)}个指标")

    # 测试评分
    scored = score_indicators(indicators)
    assert len(scored) == 8, f"评分数量错误: {len(scored)}"
    for indicator, data in scored.items():
        assert 0 <= data["score"] <= 100, f"{indicator}评分超出范围"
    print("评分逻辑验证通过")

    # 测试同比计算
    yoy = calculate_yoy(123456, 100000)
    assert abs(yoy - 23.456) < 0.01, f"同比计算错误: {yoy}"
    print(f"同比计算验证通过: {yoy:.2f}%")

    # 测试报告生成
    report = generate_report(scored, 2025, "markdown")
    assert "综合健康度评分" in report
    assert "风险提示" in report
    print("报告生成验证通过")
    print("所有自测通过！")
    return True

# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(description="年报速读工具 - 解析财报并生成投资决策简报")
    parser.add_argument("--input", type=str, help="输入文件路径（.txt/.md/.csv）")
    parser.add_argument("--output", type=str, default="report.md", help="输出报告文件路径")
    parser.add_argument("--format", type=str, choices=["text", "markdown"], default="markdown", help="输出格式")
    parser.add_argument("--year", type=int, default=2025, help="报告年份")
    parser.add_argument("--demo", action="store_true", help="使用演示数据")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    # 获取数据源
    if args.demo:
        text = demo_data()
        indicators = extract_indicators_from_text(text)
        source_desc = "演示数据"
    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"错误: 文件不存在 {args.input}")
            sys.exit(1)
        if input_path.suffix.lower() == ".csv":
            indicators = extract_indicators_from_csv(input_path)
        else:
            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()
            indicators = extract_indicators_from_text(text)
        source_desc = str(input_path)
    else:
        print("错误: 请提供 --input 文件路径或使用 --demo 演示模式")
        parser.print_help()
        sys.exit(1)

    if not indicators:
        print("警告: 未提取到任何指标，请检查文件格式")
        sys.exit(1)

    # 评分和生成报告
    scored = score_indicators(indicators)
    report = generate_report(scored, args.year, args.format)

    # 输出
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(report, encoding="utf-8")
        print(f"报告已生成: {output_path} (来源: {source_desc})")
    else:
        print(report)

if __name__ == "__main__":
    main()
