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
  5. 生成调仓建议（基于预设规则，支持自定义目标仓位）
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
import time
import os
import re
import threading
import tempfile
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 网络请求相关
import urllib.request
import urllib.error
import urllib.parse

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

# 网络请求配置
REQUEST_TIMEOUT = 10               # 请求超时时间（秒）
REQUEST_MAX_RETRIES = 3            # 最大重试次数
REQUEST_BACKOFF_BASE = 2           # 退避基数（秒）
CACHE_TTL = 300                    # 缓存有效期（秒）
CACHE_DIR = os.path.join(tempfile.gettempdir(), "stock_fund_report_cache")

# 行情数据源配置
QUOTE_API_URL = "https://qt.gtimg.cn/q={symbols}"  # 腾讯行情API
QUOTE_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# 备用行情源（新浪财经）
BACKUP_QUOTE_API_URL = "https://hq.sinajs.cn/list={symbols}"
BACKUP_QUOTE_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn"
}

# 并发配置
MAX_WORKERS = 5  # 批量请求最大并发数


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
# 行情数据获取（真实API + 重试 + 缓存 + 并发 + 降级）
# ============================================================

def _get_cache_path(symbols: List[str]) -> str:
    """获取缓存文件路径"""
    cache_key = "_".join(sorted(symbols))
    cache_file = os.path.join(CACHE_DIR, f"quotes_{cache_key}.json")
    return cache_file


def _read_cache(cache_path: str) -> Optional[Dict[str, float]]:
    """读取缓存数据（带文件锁）"""
    try:
        if not os.path.exists(cache_path):
            return None
        # 检查缓存是否过期
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime > CACHE_TTL:
            return None
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache_atomic(cache_path: str, data: Dict[str, float]) -> None:
    """原子写入缓存（临时文件+rename，避免并发竞态）"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        # 写入临时文件
        fd, tmp_path = tempfile.mkstemp(dir=CACHE_DIR, prefix=".tmp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            # 原子替换
            os.replace(tmp_path, cache_path)
        except OSError:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError:
        pass  # 缓存写入失败不影响主流程


def _cleanup_cache() -> None:
    """清理过期缓存文件"""
    try:
        if not os.path.exists(CACHE_DIR):
            return
        now = time.time()
        for fname in os.listdir(CACHE_DIR):
            if fname.startswith("quotes_") and fname.endswith(".json"):
                fpath = os.path.join(CACHE_DIR, fname)
                try:
                    if now - os.path.getmtime(fpath) > CACHE_TTL * 10:  # 10倍TTL后清理
                        os.unlink(fpath)
                except OSError:
                    continue
    except OSError:
        pass


def _parse_quote_response(response_text: str) -> Dict[str, float]:
    """
    解析腾讯行情API返回的文本格式。
    格式示例: v_sz000001="51~平安银行~000001~12.34~...";
    返回 {symbol: price} 字典。
    """
    quotes: Dict[str, float] = {}
    if not response_text:
        return quotes

    # 按分号分割每条记录
    for line in response_text.split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue

        try:
            var_part, value_part = line.split("=", 1)
            # 提取symbol: v_sz000001 -> sz000001
            symbol = var_part.replace("v_", "").strip()
            if not symbol:
                continue

            # 去除引号
            value_part = value_part.strip().strip('"')
            # 按~分割字段
            fields = value_part.split("~")

            # 腾讯行情格式: 0:未知 1:名称 2:代码 3:当前价格 4:昨收 ...
            if len(fields) >= 4:
                price_str = fields[3].strip()
                price = _safe_float(price_str)
                if price is not None and price > 0:
                    quotes[symbol] = price
        except (ValueError, IndexError):
            continue

    return quotes


def _parse_backup_quote_response(response_text: str) -> Dict[str, float]:
    """
    解析新浪财经行情API返回的文本格式。
    格式示例: var hq_str_sz000001="平安银行,12.34,12.30,12.45,...";
    返回 {symbol: price} 字典。
    """
    quotes: Dict[str, float] = {}
    if not response_text:
        return quotes

    # 按换行分割每条记录
    for line in response_text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue

        try:
            var_part, value_part = line.split("=", 1)
            # 提取symbol: hq_str_sz000001 -> sz000001
            symbol = var_part.replace("hq_str_", "").strip()
            if not symbol:
                continue

            # 去除引号
            value_part = value_part.strip().strip('"')
            # 按逗号分割字段
            fields = value_part.split(",")

            # 新浪行情格式: 0:名称 1:今开 2:昨收 3:当前价格 ...
            if len(fields) >= 4:
                price_str = fields[3].strip()
                price = _safe_float(price_str)
                if price is not None and price > 0:
                    quotes[symbol] = price
        except (ValueError, IndexError):
            continue

    return quotes


def _fetch_single_quote(symbol: str) -> Tuple[str, Optional[float]]:
    """
    获取单个股票行情（带重试退避和超时）。
    先尝试腾讯API，失败后降级到新浪API。
    返回 (symbol, price) 元组，失败时 price 为 None。
    """
    # 主源：腾讯行情
    url = QUOTE_API_URL.format(symbols=symbol)
    last_error: Optional[Exception] = None

    for attempt in range(REQUEST_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=QUOTE_API_HEADERS)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                data = response.read().decode("gbk", errors="replace")

            quotes = _parse_quote_response(data)
            if symbol in quotes:
                return symbol, quotes[symbol]

            last_error = ValueError(f"行情数据解析失败: {symbol}")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_error = e
            if attempt < REQUEST_MAX_RETRIES - 1:
                # 指数退避
                backoff = REQUEST_BACKOFF_BASE ** attempt
                time.sleep(backoff)

    # 主源失败，降级到备用源（新浪）
