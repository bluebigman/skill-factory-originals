#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
爬虫采集（bestbuy-web-scraper-gpus）技能核心逻辑实现。

本脚本为独立实现（clean-room），仅依据功能规格编写，不参考任何既有代码。
仅供学习与参考用途，使用前请阅读相关文档。

功能概述：
    1. 监控百思买（Best Buy）显卡库存状态。
    2. 支持批量轮询多个显卡 SKU。
    3. 支持自定义轮询间隔、最大轮询次数和并发数。
    4. 库存变化时输出提醒信息（支持 Webhook 通知）。
    5. 支持 dry-run 模式（不实际发送网络请求）。

命令行用法：
    python main.py --selftest        # 运行内置自检（真实请求测试）
    python main.py --url <URL>       # 监控单个显卡 URL
    python main.py --batch <文件>    # 批量监控（每行一个 URL）
    python main.py --batch <文件> --interval 60 --max-polls 10  # 轮询模式
"""

import argparse
import json
import sys
import re
import time
import threading
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 尝试导入 requests，若不可用则使用 urllib
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    import urllib.request
    import urllib.error

# 尝试导入 BeautifulSoup，若不可用则使用 lxml
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    try:
        from lxml import html as lxml_html
        LXML_AVAILABLE = True
    except ImportError:
        LXML_AVAILABLE = False

# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------

# 技能元数据
SKILL_NAME = "bestbuy-web-scraper-gpus"
SKILL_DISPLAY = "百思买显卡库存监控"
SKILL_VERSION = "2.1.0"
SKILL_DESCRIPTION = "监控百思买（Best Buy）显卡库存状态，支持批量轮询和即时提醒。"

# 网络请求配置
REQUEST_TIMEOUT = 10  # 秒
REQUEST_RETRIES = 3   # 最大重试次数
RETRY_BACKOFF_BASE = 2  # 指数退避基数（秒）
RETRY_JITTER_MAX = 0.5  # 抖动最大值（秒）
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 全局请求间隔（秒），用于限速
GLOBAL_REQUEST_INTERVAL = 1.0
_last_request_time = 0.0
_request_lock = threading.Lock()

# Webhook 通知配置
WEBHOOK_URL = os.environ.get("BESTBUY_WEBHOOK_URL", "")  # 可通过环境变量设置
WEBHOOK_TIMEOUT = 5  # Webhook 请求超时（秒）

# 置信度阈值
CONFIDENCE_HIGH = 90          # >=90% 直接输出
CONFIDENCE_MEDIUM = 85        # 85%-90% 建议复核
CONFIDENCE_LOW = 85           # <85% 标注 [需核实]

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查输入格式。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "批量处理文件读取失败。",
    "E007": "批量处理文件格式错误。",
    "E008": "JSON 解析失败。",
    "E009": "输出格式不受支持。",
    "E010": "内部逻辑错误。",
    "E011": "网络请求失败。",
    "E012": "无效的百思买 URL。",
    "E013": "库存状态解析失败。",
}

# 默认输出字段模板
DEFAULT_FIELDS = ["名称", "型号", "价格", "库存状态", "评分", "评论数", "URL"]

# 技能能力边界声明
CAPABILITY_BOUNDARIES = [
    "仅监控百思买（bestbuy.com）显卡产品页面",
    "库存状态基于页面 HTML 解析，可能存在延迟",
    "提醒功能通过控制台输出和 Webhook 实现",
    "支持 dry-run 模式（不实际发送网络请求）",
]

# 库存状态关键词映射
STOCK_KEYWORDS = {
    "in_stock": ["in stock", "add to cart", "available", "有货"],
    "out_of_stock": ["sold out", "out of stock", "unavailable", "无货"],
    "coming_soon": ["coming soon", "pre-order", "即将上市"],
}

# 测试 URL（用于 selftest）
SELFTEST_URL_IN_STOCK = "https://www.bestbuy.com/site/nvidia-geforce-rtx-4080/1234567.p?skuId=1234567"
SELFTEST_URL_OUT_OF_STOCK = "https://www.bestbuy.com/site/nvidia-geforce-rtx-4090/7654321.p?skuId=7654321"

# 模拟 HTML 样本（用于 dry-run）
MOCK_HTML_SAMPLE = """
<!DOCTYPE html>
<html>
<head>
    <title>NVIDIA GeForce RTX 4080</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "NVIDIA GeForce RTX 4080",
        "offers": {
            "price": "1199.99",
            "availability": "https://schema.org/InStock"
        }
    }
    </script>
</head>
<body>
    <div class="sku-title">NVIDIA GeForce RTX 4080</div>
    <div class="sku-model">SKU: 1234567</div>
    <div class="priceView">$1,199.99</div>
    <button class="add-to-cart-button">Add to Cart</button>
</body>
</html>
"""

MOCK_HTML_SAMPLE_OUT_OF_STOCK = """
<!DOCTYPE html>
<html>
<head>
    <title>NVIDIA GeForce RTX 4090</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "NVIDIA GeForce RTX 4090",
        "offers": {
            "price": "1599.99",
            "availability": "https://schema.org/OutOfStock"
        }
    }
    </script>
</head>
<body>
    <div class="sku-title">NVIDIA GeForce RTX 4090</div>
    <div class="sku-model">SKU: 7654321</div>
    <div class="priceView">$1,599.99</div>
    <button class="add-to-cart-button" disabled>Sold Out</button>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessingResult:
    """处理结果数据类。"""

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        confidence: int = 100,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
    ) -> None:
        self.data = data or {}
        self.confidence = confidence
        self.warnings = warnings or []
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class StockStatus:
    """库存状态数据类。"""

    def __init__(
        self,
        url: str,
        name: str = "",
        model: str = "",
        price: str = "",
        status: str = "unknown",
        timestamp: str = "",
    ) -> None:
        self.url = url
        self.name = name
        self.model = model
        self.price = price
        self.status = status
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "url": self.url,
            "name": self.name,
            "model": self.model,
            "price": self.price,
            "status": self.status,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# 网络请求与解析逻辑
# ---------------------------------------------------------------------------

def _rate_limit():
    """全局请求限速，确保请求间隔不小于 GLOBAL_REQUEST_INTERVAL。"""
    global _last_request_time
    with _request_lock:
        now = time.time()
        wait_time = GLOBAL_REQUEST_INTERVAL - (now - _last_request_time)
        if wait_time > 0:
            time.sleep(wait_time)
        _last_request_time = time.time()


def _get_backoff_with_jitter(attempt: int, status_code: Optional[int] = None) -> float:
    """计算带抖动的指数退避时间。"""
    base_backoff = RETRY_BACKOFF_BASE ** attempt
    if status_code == 429:
        base_backoff *= 3
    # 使用确定性抖动（基于时间和 attempt 的哈希），避免 random 模块
    jitter_seed = (time.time_ns() + attempt * 7919) % 1000 / 1000.0 * RETRY_JITTER_MAX
    return base_backoff + jitter_seed


def make_request(url: str, dry_run: bool = False) -> Optional[str]:
    """
    发送 HTTP 请求获取页面内容，支持重试退避和超时。

    参数:
        url: 目标 URL。
        dry_run: 是否模拟请求（不实际发送）。

    返回:
        页面 HTML 字符串，失败返回 None。

    错误码:
        E011: 网络请求失败
    """
    if dry_run:
        # 模拟响应，用于测试
        return _generate_mock_response(url)

    # 应用全局限速
    _rate_limit()

    if not REQUESTS_AVAILABLE:
        return _make_request_urllib(url)
    return _make_request_requests(url)


def _make_request_requests(url: str) -> Optional[str]:
    """使用 requests 库发送请求，带指数退避重试。"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for attempt in range(REQUEST_RETRIES):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            # 处理 403/429 状态码
            if response.status_code in (403, 429):
                if attempt == REQUEST_RETRIES - 1:
                    print(f"E011: 请求被拒绝（HTTP {response.status_code}），已重试 {REQUEST_RETRIES} 次")
                    return None
                backoff = _get_backoff_with_jitter(attempt, response.status_code)
                print(f"HTTP {response.status_code}，{backoff:.2f} 秒后重试...")
                time.sleep(backoff)
                continue

            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if attempt == REQUEST_RETRIES - 1:
                print(f"E011: 网络请求失败（尝试 {attempt + 1}/{REQUEST_RETRIES}）: {e}")
                return None
            backoff = _get_backoff_with_jitter(attempt)
            print(f"请求失败，{backoff:.2f} 秒后重试...")
            time.sleep(backoff)
    return None


def _make_request_urllib(url: str) -> Optional[str]:
    """使用 urllib 库发送请求（备用方案），带指数退避重试。"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    for attempt in range(REQUEST_RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                # 处理 403/429 状态码
                if response.status in (403, 429):
                    if attempt == REQUEST_RETRIES - 1:
                        print(f"E011: 请求被拒绝（HTTP {response.status}），已重试 {REQUEST_RETRIES} 次")
                        return None
                    backoff = _get_backoff_with_jitter(attempt, response.status)
                    print(f"HTTP {response.status}，{backoff:.2f} 秒后重试...")
                    time.sleep(backoff)
                    continue
                return response.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            if attempt == REQUEST_RETRIES - 1:
                print(f"E011: 网络请求失败（尝试 {attempt + 1}/{REQUEST_RETRIES}）: {e}")
                return None
            backoff = _get_backoff_with_jitter(attempt)
            print(f"请求失败，{backoff:.2f} 秒后重试...")
            time.sleep(backoff)
    return None


def _generate_mock_response(url: str) -> str:
    """
    生成模拟的百思买页面响应（用于 dry-run）。
    使用固定的、已知的 HTML 样本，不生成随机数据。

    参数:
        url: 目标 URL。

    返回:
        模拟的 HTML 字符串。
    """
    # 根据 URL 中的关键词决定返回哪个样本
    if "4090" in url.lower():
        return MOCK_HTML_SAMPLE_OUT_OF_STOCK
    return MOCK_HTML_SAMPLE


def parse_stock_html(html: str, url: str) -> StockStatus:
    """
    从 HTML 中解析库存状态，优先使用 BeautifulSoup/lxml 解析。

    参数:
        html: 页面 HTML 内容。
        url: 原始 URL。

    返回:
        StockStatus 对象。

    错误码:
        E013: 库存状态解析失败
    """
    if not html:
        raise ValueError("E013")

    # 优先使用 BeautifulSoup 解析
    if BS4_AVAILABLE:
        return _parse_stock_html_bs4(html, url)
    elif LXML_AVAILABLE:
        return _parse_stock_html_lxml(html, url)
    else:
        # 降级方案：使用正则表达式解析
        return _parse_stock_html_regex(html, url)


def _parse_stock_html_bs4(html: str, url: str) -> StockStatus:
    """使用 BeautifulSoup 解析 HTML。"""
    soup = BeautifulSoup(html, "html.parser")

    # 解析产品名称
    name_elem = soup.find(class_="sku-title")
    name = name_elem.get_text(strip=True) if name_elem else ""

    # 解析型号
    model_elem = soup.find(class_="sku-model")
    model = model_elem.get_text(strip=True) if model_elem else ""

    # 解析价格
    price_elem = soup.find(class_="priceView")
    price = ""
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        price_match = re.search(r'\$([\d,]+\.?\d*)', price_text)
        if price_match:
            price = f"${price_match.group(1)}"

    # 解析库存状态 - 优先从 JSON-LD 结构化数据提取
    status = "unknown"
    json_ld = soup.find("script", type="application/ld+json")
    if json_ld:
        try:
            data = json.loads(json_ld.string)
            if "offers" in data:
                availability = data["offers"].get("availability", "")
                if "InStock" in availability:
                    status = "in_stock"
                elif "OutOfStock" in availability:
                    status = "out_of_stock"
                elif "PreOrder" in availability:
                    status = "coming_soon"
        except (json.JSONDecodeError, AttributeError):
            pass

    # 如果 JSON-LD 未解析出状态，使用关键词匹配
    if status == "unknown":
        html_lower = html.lower()
        for stock_status, keywords in STOCK_KEYWORDS.items():
            if any(keyword.lower() in html_lower for keyword in keywords):
                status = stock_status
                break

    if status == "unknown":
        raise ValueError("E013")

    return StockStatus(
        url=url,
        name=name,
        model=model,
        price=price,
        status=status,
    )


def _parse_stock_html_lxml(html: str, url: str) -> StockStatus:
    """使用 lxml 解析 HTML。"""
    tree = lxml_html.fromstring(html)

    # 解析产品名称
    name_elems = tree.xpath('//*[contains(@class, "sku-title")]')
    name = name_elems[0].text_content().strip() if name_elems else ""

    # 解析型号
    model_elems = tree.xpath
