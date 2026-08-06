#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annual-report-summary Skill - 年报摘要生成器
从年报文本中提取关键财务指标并生成摘要
"""

import re
import json
import argparse
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


def load_spec() -> Dict[str, Any]:
    """加载技能规格说明"""
    return {
        "name": "annual-report-summary",
        "description": "从年报文本中提取关键财务指标并生成摘要",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "年报文本内容"
                }
            },
            "required": ["text"]
        }
    }


def match_trigger(text: str) -> bool:
    """判断是否触发本技能"""
    keywords = ["年报", "年度报告", "财务报告", "净资产收益率", "ROE"]
    return any(kw in text for kw in keywords)


def extract_roe(text: str) -> Optional[str]:
    """
    提取ROE（净资产收益率）
    支持多种写法：净资产收益率、ROE、加权平均净资产收益率
    """
    # 扩展正则别名覆盖
    patterns = [
        # 加权平均净资产收益率
        r'加权平均净资产收益率[：:为\s]*([-+]?\d+\.?\d*%?)',
        # 净资产收益率
        r'净资产收益率[（(]?[）)]?[：:为\s]*([-+]?\d+\.?\d*%?)',
        # ROE (不区分大小写)
        r'ROE[：:为\s]*([-+]?\d+\.?\d*%?)',
        # 净资产收益率(ROE)
        r'净资产收益率\s*[（(]ROE[）)]\s*[：:为\s]*([-+]?\d+\.?\d*%?)',
        # ROE(净资产收益率)
        r'ROE\s*[（(]净资产收益率[）)]\s*[：:为\s]*([-+]?\d+\.?\d*%?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_net_profit(text: str) -> Optional[str]:
    """提取净利润增长率（仅匹配增长率相关表述）"""
    patterns = [
        r'净利润增长率[：:为\s]*([-+]?\d+\.?\d*%?)',
        r'净利润同比[：:为\s]*([-+]?\d+\.?\d*%?)',
        r'净利润同比增长[：:为\s]*([-+]?\d+\.?\d*%?)',
        r'净利润同比变化[：:为\s]*([-+]?\d+\.?\d*%?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_net_profit_value(text: str) -> Optional[str]:
    """提取净利润绝对值（支持多种单位）"""
    # 预处理：去除千分位逗号
    processed_text = re.sub(r'(?<=\d),(?=\d)', '', text)
    patterns = [
        r'归属于上市公司股东的净利润[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
        r'净利润[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
    ]
    for pattern in patterns:
        match = re.search(pattern, processed_text)
        if match:
            return match.group(1)
    return None


def extract_revenue(text: str) -> Optional[str]:
    """提取营业收入增长率（仅匹配增长率相关表述）"""
    patterns = [
        r'营业收入增长率[：:为\s]*([-+]?\d+\.?\d*%?)',
        r'营业收入同比[：:为\s]*([-+]?\d+\.?\d*%?)',
        r'营业收入同比增长[：:为\s]*([-+]?\d+\.?\d*%?)',
        r'营业收入同比变化[：:为\s]*([-+]?\d+\.?\d*%?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_revenue_value(text: str) -> Optional[str]:
    """提取营业收入绝对值（支持多种单位）"""
    # 预处理：去除千分位逗号
    processed_text = re.sub(r'(?<=\d),(?=\d)', '', text)
    patterns = [
        r'营业总收入[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
        r'营业收入[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
    ]
    for pattern in patterns:
        match = re.search(pattern, processed_text)
        if match:
            return match.group(1)
    return None


def extract_eps(text: str) -> Optional[str]:
    """提取每股收益（不应带百分号）"""
    patterns = [
        r'每股收益[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
        r'EPS[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
        r'基本每股收益[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_total_assets(text: str) -> Optional[str]:
    """提取总资产（支持多种单位）"""
    # 预处理：去除千分位逗号
    processed_text = re.sub(r'(?<=\d),(?=\d)', '', text)
    patterns = [
        r'总资产[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
        r'资产总计[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
    ]
    for pattern in patterns:
        match = re.search(pattern, processed_text)
        if match:
            return match.group(1)
    return None


def extract_total_liabilities(text: str) -> Optional[str]:
    """提取总负债（支持多种单位）"""
    # 预处理：去除千分位逗号
    processed_text = re.sub(r'(?<=\d),(?=\d)', '', text)
    patterns = [
        r'总负债[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
        r'负债合计[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
    ]
    for pattern in patterns:
        match = re.search(pattern, processed_text)
        if match:
            return match.group(1)
    return None


def extract_equity(text: str) -> Optional[str]:
    """提取股东权益（支持多种单位）"""
    # 预处理：去除千分位逗号
    processed_text = re.sub(r'(?<=\d),(?=\d)', '', text)
    patterns = [
        r'股东权益[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
        r'所有者权益[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
        r'净资产[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
    ]
    for pattern in patterns:
        match = re.search(pattern, processed_text)
        if match:
            return match.group(1)
    return None


def extract_cash_flow(text: str) -> Optional[str]:
    """提取经营活动现金流（支持多种单位）"""
    # 预处理：去除千分位逗号
    processed_text = re.sub(r'(?<=\d),(?=\d)', '', text)
    patterns = [
        r'经营活动产生的现金流量净额[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
        r'经营现金流[：:为\s]*([-+]?\d+\.?\d*\s*(?:亿元|万元|元))',
    ]
    for pattern in patterns:
        match = re.search(pattern, processed_text)
        if match:
            return match.group(1)
    return None


def extract_metrics(text: str) -> Dict[str, Optional[str]]:
    """提取所有关键财务指标"""
    return {
        'roe': extract_roe(text),
        'net_profit': extract_net_profit(text),
        'net_profit_value': extract_net_profit_value(text),
        'revenue': extract_revenue(text),
        'revenue_value': extract_revenue_value(text),
        'eps': extract_eps(text),
        'total_assets': extract_total_assets(text),
        'total_liabilities': extract_total_liabilities(text),
        'equity': extract_equity(text),
        'cash_flow': extract_cash_flow(text),
    }


def generate_highlights(metrics: Dict[str, Optional[str]]) -> List[str]:
    """根据指标生成亮点"""
    highlights = []
    if metrics.get('roe'):
        try:
            roe_val = float(metrics['roe'].rstrip('%'))
            if roe_val > 10:
                highlights.append("报告期内公司净资产收益率表现良好")
        except ValueError:
            pass
    
    if metrics.get('net_profit'):
        try:
            np_val = float(metrics['net_profit'].rstrip('%'))
            if np_val > 0:
                highlights.append("报告期内公司业绩实现增长")
        except ValueError:
            pass
    
    if metrics.get('revenue'):
        try:
            rev_val = float(metrics['revenue'].rstrip('%'))
            if rev_val > 0:
                highlights.append("报告期内公司营业收入实现增长")
        except ValueError:
            pass
    
    return highlights


def generate_risks(metrics: Dict[str, Optional[str]]) -> List[str]:
    """根据指标生成风险提示"""
    risks = []
    if metrics.get('net_profit'):
        try:
            np_val = float(metrics['net_profit'].rstrip('%'))
            if np_val < 0:
                risks.append("报告期内公司净利润出现下滑")
        except ValueError:
            pass
    
    if metrics.get('revenue'):
        try:
            rev_val = float(metrics['revenue'].rstrip('%'))
            if rev_val < 0:
                risks.append("报告期内公司营业收入出现下滑")
        except ValueError:
            pass
    
    return risks


def generate_summary(text: str) -> Dict[str, Any]:
    """生成年报摘要"""
    metrics = extract_metrics(text)
    highlights = generate_highlights(metrics)
    risks = generate_risks(metrics)
    
    return {
        'metrics': metrics,
        'highlights': highlights,
        'risks': risks,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }


def selftest() -> None:
    """自检函数 - 测试核心链路"""
    # 测试数据包含ROE字段
    test_text = """
    公司2023年年度报告显示：
    加权平均净资产收益率为15.23%
    净利润增长率为18.92%
    营业收入增长率为125.67%
    每股收益为1.85元
    总资产为356.42亿元
    总负债为198.76亿元
    股东权益为157.66亿元
    经营活动产生的现金流量净额为23.45亿元
    """
    
    # 测试ROE提取
    roe = extract_roe(test_text)
    assert roe is not None, "ROE提取失败"
    assert roe == '15.23%', f"ROE提取错误: {roe}"
    print(f"ROE提取成功: {roe}")
    
    # 测试ROE别名
    test_text_alias = "报告期内公司净资产收益率为12.5%"
    roe_alias = extract_roe(test_text_alias)
    assert roe_alias is not None, "ROE别名提取失败"
    assert roe_alias == '12.5%', f"ROE别名提取错误: {roe_alias}"
    print(f"ROE别名提取成功: {roe_alias}")
    
    # 测试ROE大写
    test_text_upper = "报告期内公司ROE为10.8%"
    roe_upper = extract_roe(test_text_upper)
    assert roe_upper is not None, "ROE大写提取失败"
    assert roe_upper == '10.8%', f"ROE大写提取错误: {roe_upper}"
    print(f"ROE大写提取成功: {roe_upper}")
    
    # 测试净利润增长率提取
    test_text_growth = "报告期内净利润增长率为18.92%"
    np_growth = extract_net_profit(test_text_growth)
    assert np_growth is not None, "净利润增长率提取失败"
    assert np_growth == '18.92%', f"净利润增长率提取错误: {np_growth}"
    print(f"净利润增长率提取成功: {np_growth}")
    
    # 测试净利润绝对值提取（不应被增长率函数捕获）
    test_text_value = "归属于上市公司股东的净利润为25.67亿元"
    np_value = extract_net_profit(test_text_value)
    assert np_value is None, f"净利润绝对值不应被增长率函数捕获: {np_value}"
    np_value_extracted = extract_net_profit_value(test_text_value)
    assert np_value_extracted is not None, "净利润绝对值提取失败"
    assert np_value_extracted == '25.67亿元', f"净利润绝对值提取错误: {np_value_extracted}"
    print(f"净利润绝对值提取成功: {np_value_extracted}")
    
    # 测试净利润绝对值（万元单位）
    test_text_value_wan = "归属于上市公司股东的净利润为256,700万元"
    np_value_wan = extract_net_profit_value(test_text_value_wan)
    assert np_value_wan is not None, "净利润绝对值（万元）提取失败"
    assert np_value_wan == '256700万元', f"净利润绝对值（万元）提取错误: {np_value_wan}"
    print(f"净利润绝对值（万元）提取成功: {np_value_wan}")
    
    # 测试营业收入增长率提取
    test_text_rev_growth = "报告期内营业收入增长率为125.67%"
    rev_growth = extract_revenue(test_text_rev_growth)
    assert rev_growth is not None, "营业收入增长率提取失败"
    assert rev_growth == '125.67%', f"营业收入增长率提取错误: {rev_growth}"
    print(f"营业收入增长率提取成功: {rev_growth}")
    
    # 测试营业收入绝对值提取（不应被增长率函数捕获）
    test_text_rev_value = "营业总收入为356.42亿元"
    rev_value = extract_revenue(test_text_rev_value)
    assert rev_value is None, f"营业收入绝对值不应被增长率函数捕获: {rev_value}"
    rev_value_extracted = extract_revenue_value(test_text_rev_value)
    assert rev_value_extracted is not None, "营业收入绝对值提取失败"
    assert rev_value_extracted == '356.42亿元', f"营业收入绝对值提取错误: {rev_value_extracted}"
    print(f"营业收入绝对值提取成功: {rev_value_extracted}")
    
    # 测试营业收入绝对值（万元单位）
    test_text_rev_value_wan = "营业总收入为3,564,200万元"
    rev_value_wan = extract_revenue_value(test_text_rev_value_wan)
    assert rev_value_wan is not None, "营业收入绝对值（万元）提取失败"
    assert rev_value_wan == '3564200万元', f"营业收入绝对值（万元）提取错误: {rev_value_wan}"
    print(f"营业收入绝对值（万元）提取成功: {rev_value_wan}")
    
    # 测试EPS提取（不应带百分号）
    test_text_eps = "每股收益为1.85元"
    eps = extract_eps(test_text_eps)
    assert eps is not None, "EPS提取失败"
    assert eps == '1.85元', f"EPS提取错误: {eps}"
    assert '%' not in eps, f"EPS不应包含百分号: {eps}"
    print(f"EPS提取成功: {eps}")
    
    # 测试EPS负值
    test_text_eps_negative = "每股收益为-0.35元"
    eps_negative = extract_eps(test_text_eps_negative)
    assert eps_negative is not None, "负EPS提取失败"
    assert eps_negative == '-0.35元', f"负EPS提取错误: {eps_negative}"
    print(f"负EPS提取成功: {eps_negative}")
    
    # 测试无匹配场景
    test_text_no_match = "这是一个没有财务指标的年报文本"
    metrics_no_match = extract_metrics(test_text_no_match)
    assert all(v is None for v in metrics_no_match.values()), f"无匹配时应全部为None: {metrics_no_match}"
    print("无匹配场景测试通过")
    
    # 测试完整指标提取
    metrics = extract_metrics(test_text)
    assert metrics['roe'] is not None, "完整指标提取失败: ROE"
    assert metrics['net_profit'] is not None, "完整指标提取失败: net_profit"
    assert metrics['revenue'] is not None, "完整指标提取失败: revenue"
    assert metrics['eps'] is not None, "完整指标提取失败: eps"
    assert metrics['total_assets'] is not None, "完整指标提取失败: total_assets"
    assert metrics['total_liabilities'] is not None, "完整指标提取失败: total_liabilities"
    assert metrics['equity'] is not None, "完整指标提取失败: equity"
    assert metrics['cash_flow'] is not None, "完整指标提取失败: cash_flow"
    print(f"完整指标提取成功: {metrics}")
    
    # 测试摘要生成
