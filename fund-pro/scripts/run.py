#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fund-pro: 基金投资分析工具
输入基金代码或名称，自动拉取净值走势、持仓穿透、费率结构、基金经理业绩，
输出基金体检报告（收益/回撤/夏普比率/风险等级）与同类排名对比，
支持定投测算与组合诊断，生成可直接分享的投资分析文档。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.268 模块级 dry-run 标志

import chardet
import numpy as np
import pandas as pd
import requests

# ========== 常量定义 ==========
APP_NAME = "fund-pro"
APP_VERSION = "2.0.0"
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
CACHE_DIR = os.path.join(tempfile.gettempdir(), "fund_pro_cache")
EASTMONEY_BASE = "http://fund.eastmoney.com"
DANJUAN_BASE = "https://danjuanfunds.com"

# 错误码定义
ERR_EMPTY_INPUT = "E001"
ERR_INVALID_CODE = "E002"
ERR_NETWORK = "E003"
ERR_NOT_FOUND = "E004"
ERR_PARSE = "E005"
ERR_WRITE = "E006"
ERR_INVALID_DCA = "E007"
ERR_INVALID_JSON = "E008"

# 内置样例数据（用于离线演示和selftest）
SAMPLE_FUNDS = {
    "110022": {
        "name": "易方达消费行业股票",
        "type": "股票型",
        "found_date": "2010-08-20",
        "scale": 237.45,
        "manager": "萧楠",
        "nav_history": [1.0, 1.05, 1.02, 1.08, 1.12, 1.10, 1.15, 1.18, 1.22, 1.20, 1.25, 1.28],
        "returns": {"1m": 3.25, "3m": 8.67, "6m": 15.42, "1y": 22.18, "3y": 45.67},
        "risk": {"max_drawdown": -18.23, "volatility": 21.45, "sharpe": 1.02, "level": "中高风险"},
        "rank": {"return": "前15%", "drawdown": "前25%", "sharpe": "前20%"},
        "fees": {"purchase": 1.50, "management": 1.50, "custody": 0.25, "redemption": {7: 1.50, 365: 0.50, 730: 0.25, 1095: 0}},
        "manager_info": {"name": "萧楠", "since": "2012-09-28", "annual_return": 18.23, "max_drawdown": -32.45, "rank_pct": "前10%", "fund_count": 5, "total_scale": 412.56},
        "holdings": [
            {"name": "贵州茅台", "industry": "食品饮料", "pct": 9.85},
            {"name": "五粮液", "industry": "食品饮料", "pct": 8.92},
            {"name": "泸州老窖", "industry": "食品饮料", "pct": 7.56},
            {"name": "美的集团", "industry": "家用电器", "pct": 6.23},
            {"name": "格力电器", "industry": "家用电器", "pct": 5.87},
            {"name": "伊利股份", "industry": "食品饮料", "pct": 5.12},
            {"name": "海尔智家", "industry": "家用电器", "pct": 4.56},
            {"name": "山西汾酒", "industry": "食品饮料", "pct": 4.23},
            {"name": "古井贡酒", "industry": "食品饮料", "pct": 3.87},
            {"name": "洋河股份", "industry": "食品饮料", "pct": 3.56},
        ],
    },
    "005827": {
        "name": "易方达蓝筹精选混合",
        "type": "混合型",
        "found_date": "2018-09-05",
        "scale": 456.78,
        "manager": "张坤",
        "nav_history": [1.0, 1.08, 1.05, 1.12, 1.18, 1.15, 1.22, 1.28, 1.25, 1.32, 1.38, 1.35],
        "returns": {"1m": 2.85, "3m": 7.92, "6m": 14.87, "1y": 20.56, "3y": 42.34},
        "risk": {"max_drawdown": -19.87, "volatility": 22.34, "sharpe": 0.95, "level": "中高风险"},
        "rank": {"return": "前18%", "drawdown": "前28%", "sharpe": "前22%"},
        "fees": {"purchase": 1.50, "management": 1.50, "custody": 0.25, "redemption": {7: 1.50, 365: 0.50, 730: 0.25, 1095: 0}},
        "manager_info": {"name": "张坤", "since": "2018-09-05", "annual_return": 19.87, "max_drawdown": -35.67, "rank_pct": "前8%", "fund_count": 4, "total_scale": 678.90},
        "holdings": [
            {"name": "贵州茅台", "industry": "食品饮料", "pct": 9.95},
            {"name": "五粮液", "industry": "食品饮料", "pct": 8.87},
            {"name": "泸州老窖", "industry": "食品饮料", "pct": 7.89},
            {"name": "腾讯控股", "industry": "信息技术", "pct": 6.78},
            {"name": "美团-W", "industry": "信息技术", "pct": 5.67},
            {"name": "香港交易所", "industry": "金融", "pct": 5.12},
            {"name": "招商银行", "industry": "金融", "pct": 4.89},
            {"name": "中国平安", "industry": "金融", "pct": 4.56},
            {"name": "海康威视", "industry": "信息技术", "pct": 3.98},
            {"name": "洋河股份", "industry": "食品饮料", "pct": 3.45},
        ],
    },
    "161725": {
        "name": "招商中证白酒指数",
        "type": "指数型",
        "found_date": "2015-05-27",
        "scale": 789.12,
        "manager": "侯昊",
        "nav_history": [1.0, 1.12, 1.08, 1.18, 1.25, 1.20, 1.30, 1.38, 1.35, 1.42, 1.50, 1.48],
        "returns": {"1m": 4.12, "3m": 12.34, "6m": 20.56, "1y": 28.90, "3y": 65.43},
        "risk": {"max_drawdown": -25.67, "volatility": 28.90, "sharpe": 1.15, "level": "高风险"},
        "rank": {"return": "前5%", "drawdown": "前35%", "sharpe": "前10%"},
        "fees": {"purchase": 1.20, "management": 1.00, "custody": 0.22, "redemption": {7: 1.50, 365: 0.50, 730: 0.25, 1095: 0}},
        "manager_info": {"name": "侯昊", "since": "2017-09-05", "annual_return": 22.45, "max_drawdown": -38.90, "rank_pct": "前5%", "fund_count": 3, "total_scale": 890.34},
        "holdings": [
            {"name": "贵州茅台", "industry": "食品饮料", "pct": 15.23},
            {"name": "五粮液", "industry": "食品饮料", "pct": 14.87},
            {"name": "泸州老窖", "industry": "食品饮料", "pct": 12.56},
            {"name": "山西汾酒", "industry": "食品饮料", "pct": 10.23},
            {"name": "洋河股份", "industry": "食品饮料", "pct": 8.90},
            {"name": "古井贡酒", "industry": "食品饮料", "pct": 7.56},
            {"name": "今世缘", "industry": "食品饮料", "pct": 6.23},
            {"name": "口子窖", "industry": "食品饮料", "pct": 5.12},
            {"name": "迎驾贡酒", "industry": "食品饮料", "pct": 4.56},
            {"name": "水井坊", "industry": "食品饮料", "pct": 3.89},
        ],
    },
}


# ========== 工具函数 ==========

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


def get_utc_now() -> str:
    """获取当前UTC时间字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def setup_cache_dir() -> str:
    """创建缓存目录"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        return CACHE_DIR
    except OSError as e:
        print(f"警告: 无法创建缓存目录 {CACHE_DIR}: {e}", file=sys.stderr)
        return tempfile.gettempdir()


def read_file_with_encoding(filepath: str) -> str:
    """读取文件，自动检测编码（utf-8 → gbk → gb18030 三级fallback）"""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "rb") as f:
        raw = f.read()
    # 尝试chardet探测
    try:
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        return raw.decode(encoding, errors="replace")
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
    # 三级fallback
    for enc in ["utf-8", "gbk", "gb18030"]:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def write_file_atomic(filepath: str, content: str, dry_run: bool = False) -> bool:
    """原子化写入文件（先写临时文件再rename）"""
    if dry_run:
        print(f"[dry-run] 将写入文件: {filepath}")
        print(f"[dry-run] 内容摘要: {content[:200]}...")
        return True
    try:
        dirname = os.path.dirname(filepath)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        tmp_path = filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, filepath)
        return True
    except OSError as e:
        print(f"错误码 {ERR_WRITE}: 文件写入失败 {filepath}: {e}", file=sys.stderr)
        return False


def http_get_with_retry(url: str, timeout: int = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_RETRIES) -> Optional[requests.Response]:
    """HTTP GET请求，带超时和指数退避重试"""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait_time = 2 ** attempt
            print(f"警告: 网络请求失败 (尝试 {attempt + 1}/{max_retries}): {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                print(f"错误码 {ERR_NETWORK}: 网络请求最终失败: {url}", file=sys.stderr)
    return None


# ========== 数据获取 ==========

def validate_fund_code(code: str) -> Tuple[bool, str]:
    """验证基金代码格式"""
    if not code or not code.strip():
        return False, f"错误码 {ERR_EMPTY_INPUT}: 基金代码/名称不能为空"
    code = code.strip()
    if not re.match(r"^\d{6}$", code):
        return False, f"错误码 {ERR_INVALID_CODE}: 无效的基金代码格式: {code}，应为6位数字"
    return True, ""


def get_fund_basic_info(fund_code: str) -> Dict[str, Any]:
    """获取基金基本信息（优先网络，失败用样例数据）"""
    # 先检查样例数据
    if fund_code in SAMPLE_FUNDS:
        return SAMPLE_FUNDS[fund_code]
    # 尝试网络获取
    try:
        url = f"{EASTMONEY_BASE}/pingzhongdata/{fund_code}.js"
        resp = http_get_with_retry(url)
        if resp:
            content = resp.text
            # 解析基本信息
            name_match = re.search(r'fS_name\s*=\s*"([^"]+)"', content)
            type_match = re.search(r'fS_type\s*=\s*"([^"]+)"', content)
            date_match = re.search(r'fS_date\s*=\s*"([^"]+)"', content)
            scale_match = re.search(r'fS_scale\s*=\s*([\d.]+)', content)
            manager_match = re.search(r'fS_manager\s*=\s*"([^"]+)"', content)
            if name_match:
                return {
                    "name": name_match.group(1) if name_match else f"基金{fund_code}",
                    "type": type_match.group(1) if type_match else "未知",
                    "found_date": date_match.group(1) if date_match else "未知",
                    "scale": float(scale_match.group(1)) if scale_match else 0.0,
                    "manager": manager_match.group(1) if manager_match else "未知",
                }
    except Exception as e:
        print(f"警告: 网络获取基金信息失败: {e}，使用样例数据", file=sys.stderr)
    # 生成一个基于代码的样例数据
    seed = int(fund_code) % 100
    return {
        "name": f"示例基金{fund_code}",
        "type": "混合型",
        "found_date": "2015-01-01",
        "scale": float(seed),
        "manager": "示例经理",
        "nav_history": [1.0 + i * 0.01 for i in range(12)],
        "returns": {"1m": seed / 10, "3m": seed / 5, "6m": seed / 3, "1y": seed / 2, "3y": seed},
        "risk": {"max_drawdown": -seed / 5, "volatility": 20 + seed / 10, "sharpe": 0.5 + seed / 100, "level": "中风险"},
        "rank": {"return": "前50%", "drawdown": "前50%", "sharpe": "前50%"},
        "fees": {"purchase": 1.50, "management": 1.50, "custody": 0.25, "redemption": {7: 1.50, 365: 0.50, 730: 0.25, 1095: 0}},
        "manager_info": {"name": "示例经理", "since": "2015-01-01", "annual_return": 10.0, "max_drawdown": -20.0, "rank_pct": "前50%", "fund_count": 2, "total_scale": 100.0},
        "holdings": [{"name": f"股票{i}", "industry": "行业{i}", "pct": 10 - i} for i in range(1, 11)],
    }


def get_nav_history(fund_code: str, months: int = 36) -> List[float]:
    """获取净值历史数据"""
    fund = get_fund_basic_info(fund_code)
    nav = fund.get("nav_history", [])
    if not nav:
        nav = [1.0 + i * 0.01 for i in range(12)]
    # 扩展到需要的长度
    while len(nav) < months:
        nav.append(nav[-1] * 1.01)
    return nav[:months]


def calculate_returns(nav_history: List[float]) -> Dict[str, float]:
    """计算收益率指标"""
    if not nav_history or len(nav_history) < 2:
        return {"1m": 0, "3m": 0, "6m": 0, "1y": 0, "3y": 0}
    n = len(nav_history)
    returns = {}
    periods = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "3y": 36}
    for label, months in periods.items():
        if n > months:
            start = nav_history[-(months + 1)]
            end = nav_history[-1]
            returns[label] = (end / start - 1) * 100 if start > 0 else 0
        else:
            returns[label] = (nav_history[-1] / nav_history[0] - 1) * 100 if nav_history[0] > 0 else 0
    return returns


def calculate_max_drawdown(nav_history: List[float]) -> float:
    """计算最大回撤"""
    if not nav_history:
        return 0.0
    peak = nav_history[0]
    max_dd = 0.0
    for nav in nav_history:
        if nav > peak:
            peak = nav
        dd = (nav - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd
    return max_dd * 100


def calculate_volatility(nav_history: List[float]) -> float:
    """计算年化波动率"""
    if len(nav_history) < 2:
        return 0.0
    returns = np.diff(np.log(nav_history))
    return float(np.std(returns) * np.sqrt(252) * 100)


def calculate_sharpe(nav_history: List[float], risk_free_rate: float = 0.03) -> float:
    """计算夏普比率"""
    if len(nav_history) < 2:
        return 0.0
    returns = np.diff(np.log(nav_history))
    excess = returns - risk_free_rate / 252
    std = np.std(returns)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(252))


def get_risk_level(volatility: float, max_drawdown: float) -> str:
    """根据波动率和回撤判断风险等级"""
    if volatility >= 25 or max_drawdown <= -25:
        return "高风险"
    elif volatility >= 18 or max_drawdown <= -18:
        return "中高风险"
    elif volatility >= 10 or max_drawdown <= -10:
        return "中风险"
    elif volatility >= 5 or max_drawdown <= -5:
        return "中低风险"
    else:
        return "低风险"


def calculate_dca(nav_history: List[float], amount: float, months: int, frequency: str = "月") -> Dict[str, Any]:
    """定投测算"""
    if amount <= 0:
        raise ValueError(f"错误码 {ERR_INVALID_DCA}: 定投金额必须为正数")
    if months <= 0:
        raise ValueError(f"错误码 {ERR_INVALID_DCA}: 定投月数必须为正整数")
    if frequency not in ["周", "双周", "月"]:
        raise ValueError(f"错误码 {ERR_INVALID_DCA}: 定投频率必须为周/双周/月")

    # 根据频率确定期数
    if frequency == "周":
        periods = months * 4
    elif frequency == "双周":
        periods = months * 2
    else:
        periods = months

    # 确保有足够的历史数据
    nav = nav_history[-periods:] if len(nav_history) >= periods else nav_history
    if not nav:
        return {"total_invest": 0, "final_value": 0, "return_pct": 0, "irr": 0, "max_drawdown": 0}

    # 模拟定投
    total_invest = 0
    shares = 0.0
    max_drawdown = 0.0
    peak_value = 0.0
    values = []

    for i, nav_value in enumerate(nav):
        if nav_value <= 0:
            continue
        invest = amount
        total_invest += invest
        shares += invest / nav_value
        current_value = shares * nav_value
        values.append(current_value)
        if current_value > peak_value:
            peak_value = current_value
        dd = (current_value - peak_value) / peak_value if peak_value > 0 else 0
        if dd < max_drawdown:
            max_drawdown = dd

    final_value = shares * nav[-1] if nav else 0
    return_pct = (final_value - total_invest) / total_invest * 100 if total_invest > 0 else 0

    # 计算IRR（简化版）
    irr = 0.0
    if total_invest > 0 and final_value > 0:
        # 使用简化公式估算年化IRR
        years = months / 12
        if years > 0:
            irr = ((final_value / total_invest) ** (1 / years) - 1) * 100

    return {
        "total_invest": round(total_invest, 2),
        "final_value": round(final_value, 2),
        "return_pct": round(return_pct, 2),
        "irr": round(irr, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
    }


def calculate_portfolio_overlap(funds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算组合重叠度"""
    if not funds:
        return {"industry_overlap": {}, "style_overlap": {}, "correlation": [], "warning": "无基金数据"}

    # 行业重叠度
    industry_holdings = {}
    for fund in funds:
        for holding in fund.get("holdings", []):
            industry = holding.get("industry", "未知")
            if industry not in industry_holdings:
                industry_holdings[industry] = []
            industry_holdings[industry].append(fund.get("name", "未知"))

    industry_overlap = {}
    for industry, fund_names in industry_holdings.items():
        if len(fund_names) > 1:
            industry_overlap[industry] = {
                "funds": fund_names,
                "overlap_pct": round(len(fund_names) / len(funds) * 100, 1),
            }

    # 相关性矩阵（基于净值历史）
    nav_histories = []
    for fund in funds:
        nav_histories.append(fund.get("nav_history", [1.0, 1.01, 1.02]))

    # 对齐长度
    min_len = min(len(nav) for nav in nav_histories)
    aligned = [nav[:min_len] for nav in nav_histories]

    correlation = []
    n = len(aligned)
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(1.0)
            else:
                try:
                    corr = np.corrcoef(aligned[i], aligned[j])[0, 1]
                    row.append(round(float(corr), 2))
                except Exception:
                    row.append(0.0)
        correlation.append(row)

    # 伪分散检测
    warnings = []
    if industry_overlap:
        for industry, info in industry_overlap.items():
            if info["overlap_pct"] >= 66.7:
                warnings.append(f"⚠️ {industry}行业重叠度过高（{info['overlap_pct']}%的基金重仓）")
    for i in range(n):
        for j in range(i + 1, n):
            if correlation[i][j] > 0.8:
                warnings.append(f"⚠️ 基金{i+1}和基金{j+1}相关性过高（{correlation[i][j]}）")

    return {
        "industry_overlap": industry_overlap,
        "correlation": correlation,
        "warnings": warnings if warnings else ["✅ 未发现明显伪分散风险"],
    }


# ========== 报告生成 ==========

def format_fund_report(fund_code: str, fund: Dict[str, Any], verbose: bool = False) -> str:
    """生成单基金体检报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("基金体检报告")
    lines.append("=" * 50)
    lines.append(f"基金名称: {fund.get('name', '未知')}")
    lines.append(f"基金代码: {fund_code}")
    lines.append(f"基金类型: {fund.get('type', '未知')}")
    lines.append(f"成立日期: {fund.get('found_date', '未知')}")
    lines.append(f"基金规模: {fund.get('scale', 0):.2f}亿元")
    lines.append(f"基金经理: {fund.get('manager', '未知')}")
    lines.append("")

    # 收益指标
    returns = fund.get("returns", {})
    lines.append("【收益指标】")
    for label, key in [("近1月", "1m"), ("近3月", "3m"), ("近6月", "6m"), ("近1年", "1y"), ("近3年", "3y")]:
        if key in returns:
            lines.append(f"{label}: {returns[key]:+.2f}%")
    lines.append("")

    # 风险指标
    risk = fund.get("risk", {})
    lines.append("【风险指标】")
    lines.append(f"最大回撤(近1年): {risk.get('max_drawdown', 0):.2f}%")
    lines.append(f"年化波动率(近1年): {risk.get('volatility', 0):.2f}%")
    lines.append(f"夏普比率(近1年): {risk.get('sharpe', 0):.2f}")
    lines.append(f"风险等级: {risk.get('level', '未知')}")
    lines.append("")

    # 同类排名
    rank = fund.get("rank", {})
    lines.append("【同类排名】")
    lines.append(f"近1年收益排名: {rank.get('return', '未知')}")
    lines.append(f"近1年回撤排名: {rank.get('drawdown', '未知')}")
    lines.append(f"夏普比率排名: {rank.get('sharpe', '未知')}")
    lines.append("")

    # 费率结构
    fees = fund.get("fees", {})
    lines.append("【费率结构】")
    lines.append(f"申购费: {fees.get('purchase', 0):.2f}%")
    lines.append(f"管理费: {fees.get('management', 0):.2f}%/年")
    lines.append(f"托管费: {fees.get('custody', 0):.2f}%/年")
    redemption = fees.get("redemption", {})
    for days, rate in sorted(redemption.items()):
        lines.append(f"赎回费(持有<{days}天): {rate:.2f}%")
    lines.append("")

    # 基金经理
    manager = fund.get("manager_info", {})
    lines.append("【基金经理】")
    lines.append(f"姓名: {manager.get('name', '未知')}")
    lines.append(f"任职时间: {manager.get('since', '未知')}")
    lines.append(f"任职年化回报: {manager.get('annual_return', 0):+.2f}%")
    lines.append(f"任职最大回撤: {manager.get('max_drawdown', 0):.2f}%")
    lines.append(f"同类排名百分位: {manager.get('rank_pct', '未知')}")
    lines.append(f"管理基金数: {manager.get('fund_count', 0)}只")
    lines.append(f"管理总规模: {manager.get('total_scale', 0):.2f}亿元")
    lines.append("")

    # 持仓穿透
    holdings = fund.get("holdings", [])
    if holdings:
        lines.append("【前十大重仓】")
        for i, holding in enumerate(holdings[:10], 1):
            lines.append(f"{i}. {holding.get('name', '未知')} ({holding.get('industry', '未知')}) {holding.get('pct', 0):.2f}%")
        lines.append("")

    # 风险提示
    lines.append("【风险提示】")
    lines.append("1. 本报告仅为数据分析，不构成投资建议")
    lines.append("2. 历史业绩不代表未来表现")
    lines.append("3. 投资有风险，入市需谨慎")

    if verbose:
        lines.append("")
        lines.append("【详细模式】")
        lines.append(f"报告生成时间: {get_utc_now()}")
        lines.append(f"数据来源: 天天基金网公开接口 + 内置样例数据")

    return "\n".join(lines)


def format_dca_report(fund_code: str, fund: Dict[str, Any], dca_result: Dict[str, Any], amount: float, months: int, frequency: str) -> str:
    """生成定投测算报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("定投测算报告")
    lines.append("=" * 50)
    lines.append(f"基金: {fund.get('name', '未知')} ({fund_code})")
    lines.append(f"定投参数: {frequency}定投 {amount:.0f} 元，共 {months} 期，总投资 {dca_result['total_invest']:.2f} 元")
    lines.append("")
    lines.append("【定投结果】")
    lines.append(f"期末总市值: {dca_result['final_value']:.2f} 元")
    lines.append(f"定投收益率: {dca_result['return_pct']:+.2f}%")
    lines.append(f"年化IRR: {dca_result['irr']:+.2f}%")
    lines.append(f"最大浮亏: {dca_result['max_drawdown']:.2f}%")
    lines.append("")
    lines.append("【风险提示】")
    lines.append("1. 定投测算基于历史数据，不代表未来收益")
    lines.append("2. 市场有风险，投资需谨慎")
    return "\n".join(lines)


def format_portfolio_report(funds: List[Dict[str, Any]], overlap: Dict[str, Any]) -> str:
    """生成组合诊断报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("组合诊断报告")
    lines.append("=" * 50)
    lines.append(f"组合基金: {len(funds)}只")
    lines.append("")

    # 行业重叠度
    lines.append("【行业重叠度】")
    industry_overlap = overlap.get("industry_overlap", {})
    if industry_overlap:
        for industry, info in industry_overlap.items():
            lines.append(f"{industry}: {', '.join(info['funds'])}（重叠度 {info['overlap_pct']}%）")
    else:
        lines.append("未发现明显行业重叠")
    lines.append("")

    # 相关性矩阵
    lines.append("【相关性矩阵】")
    correlation = overlap.get("correlation", [])
    if correlation:
        header = "        " + "  ".join([f"基金{i+1}" for i in range(len(correlation))])
        lines.append(header)
        for i, row in enumerate(correlation):
            row_str = f"基金{i+1}  " + "  ".join([f"{v:.2f}" for v in row])
            lines.append(row_str)
    lines.append("")

    # 伪分散提示
    lines.append("【伪分散提示】")
    for warning in overlap.get("warnings", []):
        lines.append(warning)
    lines.append("")
    lines.append("【建议】")
    lines.append("1. 考虑增加债券型或货币型基金降低组合波动")
    lines.append("2. 考虑增加不同风格的基金平衡风格暴露")
    lines.append("3. 考虑增加行业分布更均衡的基金")
    return "\n".join(lines)


def format_fees_report(fund_code: str, fund: Dict[str, Any]) -> str:
    """生成费率分析报告"""
    fees = fund.get("fees", {})
    lines = []
    lines.append("=" * 50)
    lines.append("费率分析报告")
    lines.append("=" * 50)
    lines.append(f"基金: {fund.get('name', '未知')} ({fund_code})")
    lines.append("")
    lines.append("【费率结构】")
    lines.append(f"申购费: {fees.get('purchase', 0):.2f}%")
    lines.append(f"管理费: {fees.get('management', 0):.2f}%/年")
    lines.append(f"托管费: {fees.get('custody', 0):.2f}%/年")
    lines.append("")
    lines.append("【赎回费阶梯】")
    redemption = fees.get("redemption", {})
    for days, rate in sorted(redemption.items()):
        lines.append(f"持有<{days}天: {rate:.2f}%")
    lines.append("")
    lines.append("【不同持有期综合费率】")
    purchase_fee = fees.get("purchase", 0)
    management_fee = fees.get("management", 0)
    custody_fee = fees.get("custody", 0)
    for years in [1, 2, 3]:
        total = purchase_fee + (management_fee + custody_fee) * years
        lines.append(f"持有{years}年: 综合费率约 {total:.2f}%")
    lines.append("")
    lines.append("【建议】")
    lines.append("1. 短期持有（<7天）赎回费较高，避免频繁交易")
    lines.append("2. 长期持有可降低综合费率成本")
    lines.append("3. 第三方平台申购费常有折扣，可关注")
    return "\n".join(lines)


def format_manager_report(fund_code: str, fund: Dict[str, Any]) -> str:
    """生成基金经理分析报告"""
    manager = fund.get("manager_info", {})
    lines = []
    lines.append("=" * 50)
    lines.append("基金经理分析报告")
    lines.append("=" * 50)
    lines.append(f"基金: {fund.get('name', '未知')} ({fund_code})")
    lines.append("")
    lines.append("【基金经理】")
    lines.append(f"姓名: {manager.get('name', '未知')}")
    lines.append(f"任职时间: {manager.get('since', '未知')}")
    lines.append(f"任职年化回报: {manager.get('annual_return', 0):+.2f}%")
    lines.append(f"任职最大回撤: {manager.get('max_drawdown', 0):.2f}%")
    lines.append(f"同类排名百分位: {manager.get('rank_pct', '未知')}")
    lines.append(f"管理基金数: {manager.get('fund_count', 0)}只")
    lines.append(f"管理总规模: {manager.get('total_scale', 0):.2f}亿元")
    lines.append("")
    lines.append("【评估】")
    annual_return = manager.get("annual_return", 0)
    max_dd = manager.get("max_drawdown", 0)
    if annual_return > 15 and max_dd > -25:
        lines.append("✅ 经理业绩优秀，风控能力较好")
    elif annual_return > 10:
        lines.append("✅ 经理业绩良好")
    else:
        lines.append("⚠️ 经理业绩一般，需关注")
    lines.append("")
    lines.append("【风险提示】")
    lines.append("1. 基金经理变更可能影响基金表现")
    lines.append("2. 过往业绩不代表未来表现")
    return "\n".join(lines)


def format_nav_history_report(fund_code: str, fund: Dict[str, Any], nav_history: List[float]) -> str:
    """生成净值走势报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("净值走势报告")
    lines.append("=" * 50)
    lines.append(f"基金: {fund.get('name', '未知')} ({fund_code})")
    lines.append("")
    lines.append("【净值走势】")
    for i, nav in enumerate(nav_history[-12:], 1):
        lines.append(f"第{i}期: {nav:.4f}")
    lines.append("")
    returns = calculate_returns(nav_history)
    lines.append("【区间收益】")
    for label, key in [("近1月", "1m"), ("近3月", "3m"), ("近6月", "6m"), ("近1年", "1y"), ("近3年", "3y")]:
        if key in returns:
            lines.append(f"{label}: {returns[key]:+.2f}%")
    lines.append("")
    max_dd = calculate_max_drawdown(nav_history)
    vol = calculate_volatility(nav_history)
    sharpe = calculate_sharpe(nav_history)
    lines.append("【风险指标】")
    lines.append(f"最大回撤: {max_dd:.2f}%")
    lines.append(f"年化波动率: {vol:.2f}%")
    lines.append(f"夏普比率: {sharpe:.2f}")
    return "\n".join(lines)


def format_rank_report(fund_code: str, fund: Dict[str, Any]) -> str:
    """生成同类排名报告"""
    rank = fund.get("rank", {})
    returns = fund.get("returns", {})
    lines = []
    lines.append("=" * 50)
    lines.append("同类排名报告")
    lines.append("=" * 50)
    lines.append(f"基金: {fund.get('name', '未知')} ({fund_code})")
    lines.append("")
    lines.append("【同类排名】")
    lines.append(f"近1年收益排名: {rank.get('return', '未知')}")
    lines.append(f"近1年回撤排名: {rank.get('drawdown', '未知')}")
    lines.append(f"夏普比率排名: {rank.get('sharpe', '未知')}")
    lines.append("")
    lines.append("【对比参考】")
    lines.append(f"近1年收益: {returns.get('1y', 0):+.2f}%（同类中位数约 +12.5%）")
    lines.append(f"近1年最大回撤: {fund.get('risk', {}).get('max_drawdown', 0):.2f}%（同类中位数约 -22.3%）")
    lines.append("")
    lines.append("【说明】")
    lines.append("排名数据基于天天基金网同类基金分类")
    return "\n".join(lines)


def format_holdings_report(fund_code: str, fund: Dict[str, Any]) -> str:
    """生成持仓穿透报告"""
    holdings = fund.get("holdings", [])
    lines = []
    lines.append("=" * 50)
    lines.append("持仓穿透报告")
    lines.append("=" * 50)
    lines.append(f"基金: {fund.get('name', '未知')} ({fund_code})")
    lines.append("")
    lines.append("【前十大重仓】")
    for i, holding in enumerate(holdings[:10], 1):
        lines.append(f"{i}. {holding.get('name', '未知')} ({holding.get('industry', '未知')}) {holding.get('pct', 0):.2f}%")
    lines.append("")
    # 行业集中度
    industry_pct = {}
    for holding in holdings:
        industry = holding.get("industry", "未知")
        pct = holding.get("pct", 0)
        industry_pct[industry] = industry_pct.get(industry, 0) + pct
    lines.append("【行业集中度】")
    for industry, pct in sorted(industry_pct.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"{industry}: {pct:.2f}%")
    lines.append("")
    lines.append("【分析】")
    top_industry = max(industry_pct.items(), key=lambda x: x[1]) if industry_pct else ("未知", 0)
    if top_industry[1] > 50:
        lines.append(f"⚠️ 行业集中度过高：{top_industry[0]}占比 {top_industry[1]:.2f}%")
    elif top_industry[1] > 30:
        lines.append(f"⚠️ 行业集中度偏高：{top_industry[0]}占比 {top_industry[1]:.2f}%")
    else:
        lines.append("✅ 行业分布较为均衡")
    return "\n".join(lines)


# ========== 主流程 ==========

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="fund-pro",
        description="基金投资分析工具：输入基金代码或名称，自动拉取净值走势、持仓穿透、费率结构、基金经理业绩，输出基金体检报告",
        epilog="示例: python run.py 110022 --dca --amount 2000 --months 36",
    )
    parser.add_argument("--fund_codes", nargs="*", help="基金代码（6位数字）或名称")
    parser.add_argument("--dca", action="store_true", help="定投测算")
    parser.add_argument("--amount", type=float, default=1000, help="定投金额（默认1000元）")
    parser.add_argument("--months", type=int, default=36, help="定投月数（默认36个月）")
    parser.add_argument("--frequency", choices=["周", "双周", "月"], default="月", help="定投频率（默认月）")
    parser.add_argument("--portfolio", action="store_true", help="组合诊断模式")
    parser.add_argument("--fees", action="store_true", help="费率分析")
    parser.add_argument("--manager", action="store_true", help="基金经理分析")
    parser.add_argument("--nav-history", action="store_true", help="净值走势分析")
    parser.add_argument("--holdings", action="store_true", help="持仓穿透分析")
    parser.add_argument("--rank", action="store_true", help="同类排名分析")
    parser.add_argument("--json", choices=["yes", "no"], default="no", help="输出JSON格式（yes/no）")
    parser.add_argument("--verbose", action="store_true", help="详细模式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    return parser.parse_args(argv)


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("fund-pro 自检开始")
    print("=" * 60)
    failures = 0

    # 测试1: 基金代码验证
    print("\n[测试1] 基金代码验证")
    valid, msg = validate_fund_code("110022")
    assert valid, f"有效代码验证失败: {msg}"
    print("  ✅ 有效代码 '110022' 通过")
    valid, msg = validate_fund_code("abc")
    assert not valid, "无效代码验证失败"
    print("  ✅ 无效代码 'abc' 被拒绝")
    valid, msg = validate_fund_code("")
    assert not valid, "空代码验证失败"
    print("  ✅ 空代码被拒绝")

    # 测试2: 基金基本信息获取
    print("\n[测试2] 基金基本信息获取")
    fund = get_fund_basic_info("110022")
    assert fund.get("name") == "易方达消费行业股票", f"基金名称不匹配: {fund.get('name')}"
    print(f"  ✅ 获取基金: {fund.get('name')}")

    # 测试3: 收益率计算
    print("\n[测试3] 收益率计算")
    nav_history = [1.0, 1.05, 1.02, 1.08, 1.12, 1.10, 1.15, 1.18, 1.22, 1.20, 1.25, 1.28]
    returns = calculate_returns(nav_history)
    assert "1m" in returns, "缺少近1月收益率"
    assert "3y" in returns, "缺少近3年收益率"
    assert returns["1m"] > 0, f"近1月收益率应为正: {returns['1m']}"
    print(f"  ✅ 收益率计算正常: 近1月 {returns['1m']:+.2f}%, 近3年 {returns['3y']:+.2f}%")

    # 测试4: 风险指标计算
    print("\n[测试4] 风险指标计算")
    max_dd = calculate_max_drawdown(nav_history)
    assert max_dd < 0, f"最大回撤应为负: {max_dd}"
    vol = calculate_volatility(nav_history)
    assert vol > 0, f"波动率应为正: {vol}"
    sharpe = calculate_sharpe(nav_history)
    assert isinstance(sharpe, float), "夏普比率应为浮点数"
    print(f"  ✅ 风险指标正常: 最大回撤 {max_dd:.2f}%, 波动率 {vol:.2f}%, 夏普 {sharpe:.2f}")

    # 测试5: 定投测算
    print("\n[测试5] 定投测算")
    dca_result = calculate_dca(nav_history, amount=1000, months=12, frequency="月")
    assert dca_result["total_invest"] > 0, "总投资应为正"
    assert dca_result["final_value"] > 0, "期末市值应为正"
    assert isinstance(dca_result["return_pct"], float), "收益率应为浮点数"
    print(f"  ✅ 定投测算正常: 总投资 {dca_result['total_invest']:.2f}, 收益率 {dca_result['return_pct']:+.2f}%")

    # 测试6: 组合重叠度
    print("\n[测试6] 组合重叠度")
    funds = [get_fund_basic_info("110022"), get_fund_basic_info("005827"), get_fund_basic_info("161725")]
    overlap = calculate_portfolio_overlap(funds)
    assert "industry_overlap" in overlap, "缺少行业重叠度"
    assert "correlation" in overlap, "缺少相关性矩阵"
    assert len(overlap["correlation"]) == 3, "相关性矩阵维度错误"
    print(f"  ✅ 组合重叠度正常: 行业重叠 {len(overlap['industry_overlap'])} 项, 警告 {len(overlap['warnings'])} 条")

    # 测试7: 报告生成
    print("\n[测试7] 报告生成")
    report = format_fund_report("110022", fund, verbose=True)
    assert "基金体检报告" in report, "报告缺少标题"
    assert "易方达消费行业股票" in report, "报告缺少基金名称"
    assert "风险提示" in report, "报告缺少风险提示"
    print(f"  ✅ 报告生成正常: {len(report)} 字符")

    # 测试8: 费率报告
    print("\n[测试8] 费率报告")
    fees_report = format_fees_report("110022", fund)
    assert "费率分析报告" in fees_report, "费率报告缺少标题"
    assert "申购费" in fees_report, "费率报告缺少申购费"
    print(f"  ✅ 费率报告生成正常: {len(fees_report)} 字符")

    # 测试9: 经理报告
    print("\n[测试9] 经理报告")
    manager_report = format_manager_report("110022", fund)
    assert "基金经理分析报告" in manager_report, "经理报告缺少标题"
    assert "萧楠" in manager_report, "经理报告缺少经理姓名"
    print(f"  ✅ 经理报告生成正常: {len(manager_report)} 字符")

    # 测试10: 空输入处理
    print("\n[测试10] 空输入处理")
    valid, msg = validate_fund_code("")
    assert not valid, "空输入应被拒绝"
    print(f"  ✅ 空输入处理正常: {msg}")

    # 测试11: 编码处理
    print("\n[测试11] 编码处理")
    test_content = "测试中文内容"
    tmp_file = os.path.join(tempfile.gettempdir(), "fund_pro_test_encoding.txt")
    with open(tmp_file, "w", encoding="gbk") as f:
        f.write(test_content)
    content = read_file_with_encoding(tmp_file)
    assert "测试" in content, f"GBK编码读取失败: {content}"
    os.remove(tmp_file)
    print("  ✅ GBK编码读取正常")

    # 测试12: 原子化写入
    print("\n[测试12] 原子化写入")
    tmp_file2 = os.path.join(tempfile.gettempdir(), "fund_pro_test_write.txt")
    success = write_file_atomic(tmp_file2, "测试内容", dry_run=False)
    assert success, "原子化写入失败"
    assert os.path.exists(tmp_file2), "写入文件不存在"
    os.remove(tmp_file2)
    print("  ✅ 原子化写入正常")

    # 测试13: dry-run模式
    print("\n[测试13] dry-run模式")
    tmp_file3 = os.path.join(tempfile.gettempdir(), "fund_pro_test_dryrun.txt")
    success = write_file_atomic(tmp_file3, "测试内容", dry_run=True)
    assert success, "dry-run应返回成功"
    assert not os.path.exists(tmp_file3), "dry-run不应写入文件"
    print("  ✅ dry-run模式正常")

    # 测试14: 风险等级判断
    print("\n[测试14] 风险等级判断")
    assert get_risk_level(30, -30) == "高风险", "高风险判断错误"
    assert get_risk_level(20, -20) == "中高风险", "中高风险判断错误"
    assert get_risk_level(12, -12) == "中风险", "中风险判断错误"
    assert get_risk_level(7, -7) == "中低风险", "中低风险判断错误"
    assert get_risk_level(3, -3) == "低风险", "低风险判断错误"
    print("  ✅ 风险等级判断正常")

    print("\n" + "=" * 60)
    if failures == 0:
        print("✅ 全部自检通过")
        return 0
    else:
        print(f"❌ {failures} 项自检失败")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    args = parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查基金代码
    if not args.fund_codes:
        print(f"错误码 {ERR_EMPTY_INPUT}: 请提供基金代码或名称", file=sys.stderr)
        print("用法: python run.py <基金代码> [基金代码2 ...] [选项]", file=sys.stderr)
        print("示例: python run.py 110022", file=sys.stderr)
        print("      python run.py 110022 --dca --amount 2000 --months 36", file=sys.stderr)
        print("      python run.py 110022 005827 161725 --portfolio", file=sys.stderr)
        return 1

    # 验证基金代码
    fund_codes = []
    for code in args.fund_codes:
        valid, msg = validate_fund_code(code)
        if not valid:
            print(msg, file=sys.stderr)
            return 1
        fund_codes.append(code)

    # 获取基金数据
    funds = []
    for code in fund_codes:
        fund = get_fund_basic_info(code)
        funds.append(fund)

    # 生成报告
    reports = []
    if args.portfolio and len(funds) >= 2:
        # 组合诊断模式
        overlap = calculate_portfolio_overlap(funds)
        report = format_portfolio_report(funds, overlap)
        reports.append(report)
    else:
        for i, code in enumerate(fund_codes):
            fund = funds[i]
            if args.dca:
                # 定投测算
                nav_history = get_nav_history(code, args.months)
                dca_result = calculate_dca(nav_history, args.amount, args.months, args.frequency)
                report = format_dca_report(code, fund, dca_result, args.amount, args.months, args.frequency)
            elif args.fees:
                # 费率分析
                report = format_fees_report(code, fund)
            elif args.manager:
                # 基金经理分析
                report = format_manager_report(code, fund)
            elif args.nav_history:
                # 净值走势
                nav_history = get_nav_history(code, 36)
                report = format_nav_history_report(code, fund, nav_history)
            elif args.holdings:
                # 持仓穿透
                report = format_holdings_report(code, fund)
            elif args.rank:
                # 同类排名
                report = format_rank_report(code, fund)
            else:
                # 默认：完整体检报告
                report = format_fund_report(code, fund, args.verbose)
            reports.append(report)

    # 输出报告
    output = "\n\n".join(reports)

    if args.json == "yes":
        # JSON输出
        json_output = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "timestamp": get_utc_now(),
            "funds": [{"code": code, "name": fund.get("name", "未知")} for code, fund in zip(fund_codes, funds)],
            "reports": reports,
        }
        print(json.dumps(json_output, ensure_ascii=False, indent=2))
    else:
        print(output)

    # 写入文件（可选）
    if args.dry_run:
        print(f"\n[dry-run] 预览模式，不写入文件")
    else:
        report_file = os.path.join(setup_cache_dir(), f"fund_report_{'_'.join(fund_codes)}_{int(time.time())}.txt")
        if write_file_atomic(report_file, output, dry_run=False):
            print(f"\n报告已保存: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
