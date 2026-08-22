#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
booking-scraper 技能独立实现（clean-room 重写）
=================================================
功能：解析 Booking.com 房源页面（HTML 文件或 URL），提取结构化字段，
      支持批量处理、自定义字段过滤、缺失字段占位符标注。

仅依据功能规格独立编写，不参考任何既有实现。
错误码：
  E001 参数不合法
  E002 输入文件不存在或不可读
  E003 网络请求失败（URL 抓取时）
  E004 HTML 解析失败
  E005 输出目录不可写
  E006 批量处理中单个条目失败（继续处理其余条目）
  E007 自定义字段格式不合法
  E008 未知输出格式
  E009 内部逻辑错误（不应发生）
  E010 文件写入失败

用法示例：
  python main.py --file sample.html
  python main.py --url https://www.booking.com/hotel/xx.html --fields name,price
  python main.py --dir ./htmls --out ./results --format json
  python main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数不合法",
    "E002": "输入文件不存在或不可读",
    "E003": "网络请求失败",
    "E004": "HTML 解析失败",
    "E005": "输出目录不可写",
    "E006": "批量处理中单个条目失败",
    "E007": "自定义字段格式不合法",
    "E008": "未知输出格式",
    "E009": "内部逻辑错误",
    "E010": "文件写入失败",
}

# 支持的输出字段
ALL_FIELDS = [
    "name",        # 房源名称
    "address",     # 地址
    "rating",      # 评分
    "price",       # 价格
    "facilities",  # 设施列表
    "images",      # 图片链接列表
    "description", # 描述文本
]

# 缺失字段占位符
MISSING_PLACEHOLDER = "[需核实:{}]"

# 网络请求配置
REQUEST_TIMEOUT = 15  # 秒
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # 指数退避基数（秒）
MAX_WORKERS = 5  # 并发线程数


# ---------------------------------------------------------------------------
# 自定义 HTML 解析器（基于标准库 html.parser）
# 设计思路：通过特征 class 名或标签结构提取目标字段。
# 解析采用多级回退策略：
#   1. 优先匹配常见 class 名（如 hp__hotel-name、address 等）
#   2. 如果 class 匹配失败，退化为基于标签位置/文本的启发式提取
#   3. 最终兜底使用 meta 标签或 title
# ---------------------------------------------------------------------------
class BookingHTMLParser(HTMLParser):
    """轻量级 Booking.com 页面解析器，提取结构化字段。"""

    # 特征 class 名（多级回退）
    CLASS_PATTERNS = {
        "name": [
            ["hp__hotel-name", "hotel_name", "property-name"],
            ["bui-header__title", "h1", "hotel-title"],
            ["data-testid", "property-name"],
        ],
        "address": [
            ["hp_address_subtitle", "address", "property-address"],
            ["bui-header__address", "location"],
            ["data-testid", "address"],
        ],
        "rating": [
            ["bui-review-score__badge", "review-score-badge", "rating"],
            ["bui-review-score", "score"],
            ["data-testid", "rating"],
        ],
        "price": [
            ["prco-val", "price", "bui-price-display__value"],
            ["bui-price-display", "total-price"],
            ["data-testid", "price"],
        ],
        "facilities": [
            ["facility", "amenity", "hp_desc_important_facility"],
            ["bui-facility", "property-facilities"],
            ["data-testid", "facilities"],
        ],
        "images": [
            ["hp__main-image", "hotel_image", "property-photo"],
            ["bui-image", "hotel-photo"],
            ["data-testid", "image"],
        ],
        "description": [
            ["hp_description", "property-description", "hotel-description"],
            ["bui-description", "about-hotel"],
            ["data-testid", "description"],
        ],
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.result: Dict[str, Any] = {field: None for field in ALL_FIELDS}
        # 解析状态
        self._current_tag: str = ""
        self._text_buffer: List[str] = []
        self._in_target: Optional[str] = None
        self._depth: int = 0
        self._target_depth: int = 0
        self._image_urls: List[str] = []
        self._facility_list: List[str] = []
        self._description_parts: List[str] = []
        self._meta_description: Optional[str] = None
        self._title_text: Optional[str] = None
        self._current_class: str = ""
        self._class_match_level: Dict[str, int] = {}  # 记录每个字段的匹配级别
        # JSON-LD 兜底解析
        self._json_ld_data: Dict[str, Any] = {}
        self._script_data: List[str] = []

    def _match_class(self, class_name: str) -> Optional[str]:
        """匹配 class 名，返回字段名或 None。使用多级回退策略。"""
        if not class_name:
            return None
        
        # 逐级匹配
        for field, pattern_groups in self.CLASS_PATTERNS.items():
            for level, patterns in enumerate(pattern_groups):
                for pattern in patterns:
                    if pattern in class_name:
                        # 记录匹配级别，优先使用更精确的匹配
                        if field not in self._class_match_level or level < self._class_match_level[field]:
                            self._class_match_level[field] = level
                        return field
        return None

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        """处理开始标签，识别目标区域。"""
        attr_dict = dict(attrs)
        class_name = attr_dict.get("class", "")
        tag_lower = tag.lower()

        # 记录 title 用于兜底提取名称
        if tag_lower == "title" and self._title_text is None:
            self._current_tag = tag_lower
            self._text_buffer = []
            return

        # 识别 meta description（兜底描述）
        if tag_lower == "meta" and attr_dict.get("name", "").lower() == "description":
            self._meta_description = attr_dict.get("content", "")
            return

        # 识别 JSON-LD 脚本（兜底解析）
        if tag_lower == "script" and attr_dict.get("type", "").lower() == "application/ld+json":
            self._current_tag = "script_jsonld"
            self._text_buffer = []
            return

        # 根据 class 特征识别目标字段
        matched_field = self._match_class(class_name)
        if matched_field and self._in_target is None:
            self._in_target = matched_field
            self._target_depth = 1
            self._depth = 1
            self._text_buffer = []
            return

        # 图片标签特殊处理（img 的 src）
        if tag_lower == "img" and self._in_target == "images":
            src = attr_dict.get("src", "") or attr_dict.get("data-src", "")
            if src and src.startswith("http") and src not in self._image_urls:
                self._image_urls.append(src)

        # 如果当前在目标区域内，增加深度
        if self._in_target:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        """处理结束标签。"""
        if self._in_target:
            self._depth -= 1
            if self._depth <= 0:
                # 目标区域结束，保存文本
                text = " ".join(self._text_buffer).strip()
                if text and self.result.get(self._in_target) is None:
                    self.result[self._in_target] = text
                self._in_target = None
                self._text_buffer = []
                self._depth = 0

        if tag.lower() == "title" and self._title_text is None:
            self._title_text = " ".join(self._text_buffer).strip()
            self._text_buffer = []

        if tag.lower() == "script" and self._current_tag == "script_jsonld":
            # 解析 JSON-LD 数据
            try:
                script_content = " ".join(self._text_buffer).strip()
                if script_content:
                    data = json.loads(script_content)
                    if isinstance(data, dict):
                        self._json_ld_data = data
                    elif isinstance(data, list) and data:
                        self._json_ld_data = data[0] if isinstance(data[0], dict) else {}
            except (json.JSONDecodeError, ValueError):
                pass
            self._current_tag = ""
            self._text_buffer = []

    def handle_data(self, data: str) -> None:
        """处理文本数据。"""
        if self._in_target:
            self._text_buffer.append(data)
        if self._current_tag in ("title", "script_jsonld"):
            self._text_buffer.append(data)

    def handle_startendtag(self, tag: str, attrs: List[tuple]) -> None:
        """处理自闭合标签（如 img）。"""
        self.handle_starttag(tag, attrs)

    def _apply_json_ld_fallback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """从 JSON-LD 数据中提取字段作为兜底。"""
        if not self._json_ld_data:
            return result

        # 提取名称
        if not result.get("name"):
            for key in ["name", "headline", "title"]:
                if self._json_ld_data.get(key):
                    result["name"] = self._json_ld_data[key]
                    break

        # 提取地址
        if not result.get("address"):
            addr = self._json_ld_data.get("address", {})
            if isinstance(addr, dict):
                parts = [addr.get(k, "") for k in ["streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"]]
                result["address"] = ", ".join([p for p in parts if p])

        # 提取评分
        if not result.get("rating"):
            agg = self._json_ld_data.get("aggregateRating", {})
            if isinstance(agg, dict) and agg.get("ratingValue"):
                result["rating"] = agg["ratingValue"]

        # 提取价格
        if not result.get("price"):
            offers = self._json_ld_data.get("offers", {})
            if isinstance(offers, dict) and offers.get("price"):
                result["price"] = str(offers["price"])
            elif isinstance(offers, list) and offers:
                result["price"] = str(offers[0].get("price", ""))

        # 提取描述
        if not result.get("description"):
            for key in ["description", "about"]:
                if self._json_ld_data.get(key):
                    result["description"] = self._json_ld_data[key]
                    break

        # 提取图片
        if not result.get("images"):
            images = self._json_ld_data.get("image", [])
            if isinstance(images, str):
                result["images"] = [images]
            elif isinstance(images, list):
                result["images"] = [img for img in images if isinstance(img, str)]

        return result

    def get_result(self) -> Dict[str, Any]:
        """获取解析结果，应用兜底逻辑。"""
        result = dict(self.result)

        # 应用 JSON-LD 兜底
        result = self._apply_json_ld_fallback(result)

        # 兜底：名称从 title 提取（去掉 "Booking.com" 等后缀）
        if not result.get("name") and self._title_text:
            title = self._title_text
            # 常见格式："Hotel Name | Booking.com" 或 "Hotel Name, City - Booking.com"
            for sep in [" | ", " - ", " – "]:
                if sep in title:
                    title = title.split(sep)[0]
                    break
            result["name"] = title.strip()

        # 兜底：描述从 meta description
        if not result.get("description") and self._meta_description:
            result["description"] = self._meta_description.strip()

        # 图片列表
        if self._image_urls:
            result["images"] = self._image_urls

        # 设施列表（从文本中识别常见设施词）
        if not result.get("facilities") and self._facility_list:
            result["facilities"] = self._facility_list

        # 如果所有字段都未提取到，抛出解析错误
        if all(v is None for v in result.values()):
            raise ValueError("E004: 无法从HTML中提取任何有效字段")

        return result


# ---------------------------------------------------------------------------
# 核心数据提取函数
# ---------------------------------------------------------------------------
def _read_text_safe(path: str) -> str:
    """多编码安全读取"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_from_html(html_content: str) -> Dict[str, Any]:
    """
    从 HTML 内容中提取结构化数据。
    使用启发式规则，不依赖精确的 DOM 结构。
    """
    parser = BookingHTMLParser()
    try:
        parser.feed(html_content)
        parser.close()
        result = parser.get_result()
    except Exception as exc:
        if "E004" in str(exc):
            raise
        # 其他解析错误也视为解析失败
        raise ValueError(f"E004: HTML解析失败: {exc}")

    # 后处理：类型转换
    # 评分：尝试转为浮点数
    if result.get("rating"):
        try:
            rating_str = re.sub(r"[^\d.]", "", str(result["rating"]))
            if rating_str:
                result["rating"] = float(rating_str[:3])
        except (ValueError, TypeError):
            pass

    # 价格：提取数字部分（保留货币符号）
    if result.get("price"):
        price_str = str(result["price"]).strip()
        match = re.search(r"([^\d]*)([\d,]+\.?\d*)", price_str)
        if match:
            currency = match.group(1).strip()
            amount = match.group(2).replace(",", "")
            result["price"] = f"{currency} {amount}".strip() if currency else amount

    # 确保所有字段存在（缺失填占位符）
    for field in ALL_FIELDS:
        if field not in result or result[field] is None:
            result[field] = MISSING_PLACEHOLDER.format(field)

    return result


def extract_from_file(filepath: str) -> Dict[str, Any]:
    """从本地 HTML 文件提取数据。"""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"E002: 文件不存在或不可读: {filepath}")
    try:
        content = _read_text_safe(filepath)
    except OSError as exc:
        raise IOError(f"E002: 读取文件失败: {exc}") from exc
    return extract_from_html(content)


def _fetch_url_with_retry(url: str, timeout: int = REQUEST_TIMEOUT) -> str:
    """带重试和指数退避的 URL 抓取。"""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                # 指数退避
                backoff = RETRY_BACKOFF_BASE ** attempt
                time.sleep(backoff)
    
    raise ConnectionError(f"E003: 网络请求失败（重试{MAX_RETRIES}次后）: {last_exc}")


def extract_from_url(url: str, timeout: int = REQUEST_TIMEOUT) -> Dict[str, Any]:
    """从 URL 抓取并提取数据（需网络可用）。"""
    content = _fetch_url_with_retry(url, timeout)
    return extract_from_html(content)


# ---------------------------------------------------------------------------
# 批量处理与输出
# ---------------------------------------------------------------------------
def _process_single_source(src: Dict[str, str], fields: Optional[List[str]]) -> Dict[str, Any]:
    """处理单个来源（供线程池使用）。"""
