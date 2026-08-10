#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrapfly-scrapers - 网页数据采集与结构化输出工具

面向40+主流网站的通用爬虫框架，支持HTML页面解析、字段抽取、
结构化JSON输出。本脚本为独立实现，仅依据功能规格编写。

用法:
    python main.py --selftest     # 运行内置自检
    python main.py --version      # 显示版本信息
    python main.py --help         # 显示帮助

错误码:
    E001 - 参数错误
    E002 - 输入数据格式错误
    E003 - HTML解析失败
    E004 - 字段抽取失败
    E005 - 目标站点不支持
    E006 - 请求频率超限
    E007 - 验证码检测
    E008 - 数据序列化失败
    E009 - 文件读写错误
    E010 - 内部逻辑错误
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 配置与常量
# ============================================================

VERSION = "1.0.3"
SKILL_NAME = "scrapfly-scrapers"
DISPLAY_NAME = "网页采集 数据抽取 结构化输出"

# 支持的站点列表（仅列举代表性站点）
SUPPORTED_SITES = [
    "amazon", "ebay", "walmart", "bestbuy",
    "cnn", "bbc", "nytimes", "theguardian",
    "twitter", "facebook", "instagram", "linkedin",
    "indeed", "glassdoor", "linkedin_jobs",
    "zillow", "redfin", "realtor",
    "github", "stackoverflow", "medium",
    "wikipedia", "reddit", "youtube",
    "etsy", "shopify", "target", "homedepot",
    "lowes", "costco", "wayfair", "overstock",
    "booking", "tripadvisor", "airbnb", "expedia",
    "craigslist", "alibaba", "aliexpress", "rakuten",
]

# 默认请求头
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ScrapflyBot/1.0; +https://example.com/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# 限速配置（秒）
DEFAULT_DELAY = 1.0
MAX_RETRIES = 3


# ============================================================
# 数据模型
# ============================================================

@dataclass
class FieldSpec:
    """字段抽取规格"""
    name: str                    # 字段名
    selector: str                # CSS选择器
    attribute: Optional[str] = None  # 提取属性（如 href, src），None表示文本
    required: bool = False       # 是否必填
    default: Any = None          # 默认值
    transform: str = "text"      # 转换方式: text, int, float, url, list


@dataclass
class SiteSpec:
    """站点采集规格"""
    site_name: str               # 站点名称
    base_url: str                # 基础URL
    item_selector: str           # 列表项选择器
    fields: List[FieldSpec]      # 字段规格列表
    pagination_selector: Optional[str] = None  # 翻页选择器


@dataclass
class ScrapeResult:
    """采集结果"""
    site: str
    url: str
    items: List[Dict[str, Any]]
    timestamp: float = field(default_factory=time.time)
    status: str = "success"
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# ============================================================
# 内置站点配置（硬编码样例，仅用于自检和演示）
# ============================================================

def _get_sample_site_spec() -> SiteSpec:
    """获取样例站点规格（用于自检）"""
    return SiteSpec(
        site_name="sample_store",
        base_url="https://example-store.com",
        item_selector=".product-item",
        fields=[
            FieldSpec(name="title", selector=".product-title", required=False),
            FieldSpec(name="price", selector=".product-price", transform="float"),
            FieldSpec(name="link", selector=".product-link", attribute="href", transform="url"),
            FieldSpec(name="rating", selector=".product-rating", transform="float", default=0.0),
            FieldSpec(name="tags", selector=".tag", transform="list"),
        ],
        pagination_selector=".next-page",
    )


# ============================================================
# HTML解析器（轻量级，不依赖第三方库）
# ============================================================

class SimpleHTMLParser:
    """
    极简HTML解析器，支持基本的CSS选择器子集。
    仅用于演示核心逻辑，生产环境建议使用 BeautifulSoup/lxml。
    """
    
    def __init__(self, html: str):
        self.html = html
        self._elements = self._parse_elements(html)
    
    def _parse_elements(self, html: str) -> List[Dict[str, Any]]:
        """将HTML解析为元素列表（基于正则匹配）"""
        elements = []
        
        # 匹配自闭合标签
        self_closing_pattern = re.compile(r'<(\w+)([^>]*?)/>', re.DOTALL)
        
        # 匹配带内容的标签
        tag_pattern = re.compile(r'<(\w+)([^>]*)>(.*?)</\1>', re.DOTALL)
        
        # 先处理带内容的标签
        for match in tag_pattern.finditer(html):
            tag = match.group(1)
            attrs_str = match.group(2)
            content = match.group(3)
            
            # 解析属性
            attrs = self._parse_attrs(attrs_str)
            
            # 提取纯文本（移除内部标签）
            text = self._extract_text(content)
            
            elements.append({
                "tag": tag,
                "attrs": attrs,
                "text": text,
                "classes": attrs.get("class", "").split() if attrs.get("class") else [],
                "id": attrs.get("id", ""),
                "html": content,
            })
        
        # 处理自闭合标签
        for match in self_closing_pattern.finditer(html):
            tag = match.group(1)
            attrs_str = match.group(2)
            
            attrs = self._parse_attrs(attrs_str)
            
            elements.append({
                "tag": tag,
                "attrs": attrs,
                "text": "",
                "classes": attrs.get("class", "").split() if attrs.get("class") else [],
                "id": attrs.get("id", ""),
                "html": "",
            })
        
        return elements
    
    def _parse_attrs(self, attrs_str: str) -> Dict[str, str]:
        """解析HTML属性字符串"""
        attrs = {}
        attr_pattern = re.compile(r'(\w+)\s*=\s*["\']([^"\']*)["\']')
        for attr_match in attr_pattern.finditer(attrs_str):
            attrs[attr_match.group(1)] = attr_match.group(2)
        return attrs
    
    def _extract_text(self, content: str) -> str:
        """从HTML内容中提取纯文本"""
        # 移除所有标签
        text = re.sub(r'<[^>]+>', '', content)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def select(self, selector: str) -> List[Dict[str, Any]]:
        """按CSS选择器选择元素（支持标签、.class、#id）"""
        results = []
        selector = selector.strip()
        
        for elem in self._elements:
            if self._matches_selector(elem, selector):
                results.append(elem)
        
        return results
    
    def _matches_selector(self, elem: Dict[str, Any], selector: str) -> bool:
        """判断元素是否匹配选择器"""
        # 处理 .class
        if selector.startswith("."):
            class_name = selector[1:]
            return class_name in elem["classes"]
        
        # 处理 #id
        if selector.startswith("#"):
            return elem.get("id") == selector[1:]
        
        # 处理标签名
        return elem["tag"] == selector.lower()
    
    def extract(self, elem: Dict[str, Any], attribute: Optional[str] = None) -> Optional[str]:
        """从元素提取文本或属性"""
        if attribute:
            return elem["attrs"].get(attribute)
        return elem.get("text")


# ============================================================
# 数据抽取引擎
# ============================================================

class ExtractionEngine:
    """数据抽取引擎，负责从HTML中提取结构化数据"""
    
    def __init__(self, site_spec: SiteSpec):
        self.site_spec = site_spec
    
    def extract_items(self, html: str) -> List[Dict[str, Any]]:
        """
        从HTML页面中提取所有条目数据。
        
        Args:
            html: 页面HTML内容
            
        Returns:
            结构化数据列表
            
        Raises:
            RuntimeError: 解析失败或字段抽取失败
        """
        try:
            parser = SimpleHTMLParser(html)
        except Exception as e:
            raise RuntimeError(f"E003: HTML解析失败 - {str(e)}")
        
        # 查找所有条目容器
        containers = parser.select(self.site_spec.item_selector)
        if not containers:
            return []
        
        items = []
        for container in containers:
            item = self._extract_item(container, parser)
            if item:
                items.append(item)
        
        return items
    
    def _extract_item(self, container: Dict[str, Any], parser: SimpleHTMLParser) -> Optional[Dict[str, Any]]:
        """从单个容器提取字段"""
        item = {}
        
        for field_spec in self.site_spec.fields:
            try:
                value = self._extract_field(container, parser, field_spec)
                if value is not None:
                    item[field_spec.name] = value
                elif field_spec.required:
                    # 必填字段缺失，跳过该条目
                    return None
                else:
                    item[field_spec.name] = field_spec.default
            except Exception as e:
                if field_spec.required:
                    raise RuntimeError(f"E004: 字段抽取失败 - {field_spec.name}: {str(e)}")
                item[field_spec.name] = field_spec.default
        
        return item
    
    def _extract_field(self, container: Dict[str, Any], parser: SimpleHTMLParser, 
                       field_spec: FieldSpec) -> Any:
        """抽取单个字段值"""
        # 从容器内查找
        elements = parser.select(field_spec.selector)
        if not elements:
            return None
        
        raw_value = parser.extract(elements[0], field_spec.attribute)
        if raw_value is None:
            return None
        
        # 应用转换
        return self._transform_value(raw_value, field_spec.transform)
    
    def _transform_value(self, value: str, transform: str) -> Any:
        """转换字段值类型"""
        value = value.strip()
        
        if transform == "text":
            return value
        
        if transform == "int":
            try:
                return int(re.sub(r'[^\d-]', '', value))
            except ValueError:
                return None
        
        if transform == "float":
            try:
                return float(re.sub(r'[^\d.-]', '', value))
            except ValueError:
                return None
        
        if transform == "url":
            # 相对URL转为绝对URL
            if value.startswith("/"):
                return urljoin(self.site_spec.base_url, value)
            return value
        
        if transform == "list":
            # 逗号分隔转列表
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return parts if parts else None
        
        return value


# ============================================================
# 采集调度器
# ============================================================

class ScrapeScheduler:
    """
    采集调度器，负责站点调度、限速和重试。
    注意：本实现不执行真实网络请求（仅模拟），
    实际使用时应替换为requests/httpx等库。
    """
    
    def __init__(self, delay: float = DEFAULT_DELAY, max_retries: int = MAX_RETRIES):
        self.delay = delay
        self.max_retries = max_retries
        self.last_request_time = 0.0
    
    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """
        获取页面内容（模拟实现）。
        
        Args:
            url: 目标URL
            headers: 请求头
            
        Returns:
            HTML内容字符串
        """
        # 限速控制
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        
        self.last_request_time = time.time()
        
        # 模拟请求（实际使用时应替换为requests库）
        return self._mock_fetch(url)
    
    def _mock_fetch(self, url: str) -> str:
        """模拟获取HTML（仅用于演示）"""
        # 生成模拟的产品列表页面
        items_html = ""
        for i in range(1, 6):
            items_html += f'''
            <div class="product-item">
                <h2 class="product-title">Sample Product {i}</h2>
                <span class="product-price">${19.99 + i}.00</span>
                <a class="product-link" href="/product/{i}">View</a>
                <span class="product-rating">{3.5 + i * 0.3:.1f}</span>
                <span class="tag">Electronics</span>
                <span class="tag">Gadget</span>
            </div>
            '''
        
        return f'''
        <html>
        <body>
            <div id="products">
                {items_html}
            </div>
            <a class="next-page" href="/page/2">Next</a>
        </body>
        </html>
        '''
    
    def scrape_site(self, site_spec: SiteSpec, url: str, 
                    headers: Optional[Dict[str, str]] = None) -> ScrapeResult:
        """
        采集指定站点页面。
        
        Args:
            site_spec: 站点规格
            url: 目标URL
            headers: 请求头
            
        Returns:
            采集结果
        """
        try:
            html = self.fetch(url, headers)
            engine = ExtractionEngine(site_spec)
            items = engine.extract_items(html)
            
            return ScrapeResult(
                site=site_spec.site_name,
                url=url,
                items=items,
            )
        except RuntimeError as e:
            error_code = str(e).split(":")[0]
            return ScrapeResult(
                site=site_spec.site_name,
                url=url,
                items=[],
                status="error",
                error_code=error_code,
                error_message=str(e),
            )
        except Exception as e:
            return ScrapeResult(
                site=site_spec.site_name,
                url=url,
                items=[],
                status="error",
                error_code="E010",
                error_message=f"E010: 内部错误 - {str(e)}",
            )


# ============================================================
# 输出处理器
# ============================================================

class OutputHandler:
    """输出处理器，负责JSON序列化和文件写入"""
    
    @staticmethod
    def to_json(data: Any, pretty: bool = True) -> str:
        """转换为JSON字符串"""
        try:
            if pretty:
                return json.dumps(data, indent=2, ensure_ascii=False)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"E008: 数据序列化失败 - {str(e)}")
    
    @staticmethod
    def save_to_file(data: Any, filename: str) -> None:
        """保存到文件"""
        try:
            with open(filename, "w", encoding="utf-8", errors="replace") as f:
                f.write(OutputHandler.to_json(data))
        except Exception as e:
            raise RuntimeError(f"E009: 文件读写错误 - {str(e)}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检。
    使用硬编码样例数据，不访问网络，不依赖外部文件。
    
    Returns:
        True表示全部通过，False表示有失败项
    """
    print(f"=== {SKILL_NAME} 自检开始 ===")
    print(f"版本: {VERSION}")
    print(f"描述: {DISPLAY_NAME}\n")
    
    all_passed = True
    
    # 测试1: 数据模型
    print("[1/5] 测试数据模型...")
    try:
        site_spec = _get_sample_site_spec()
        assert site_spec.site_name == "sample_store"
        assert len(site_spec.fields) >= 4, "字段数量应至少为4"
        assert any(f.name == "title" for f in site_spec.fields)
        print("  ✓ 数据模型正常")
    except AssertionError as e:
        print(f"  ✗ 数据模型异常: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 数据模型异常: {e}")
        all_passed = False
    
    # 测试2: HTML解析器
    print("[2/5] 测试HTML解析器...")
    try:
        html = '''
        <div class="product-item">
            <h2 class="product-title">Test Product</h2>
            <span class="product-price">$25.50</span>
        </div>
        '''
        parser = SimpleHTMLParser(html)
        products = parser.select(".product-item")
        assert len(products) == 1, f"应找到1个产品，实际: {len(products)}"
        
        titles = parser.select(".product-title")
        assert len(titles) == 1, f"应找到1个标题，实际: {len(titles)}"
        assert "Test Product" in titles[0]["text"], f"标题内容不符: {titles[0]['text']}"
        
        prices = parser.select(".product-price")
        assert len(prices) == 1, f"应找到1个价格，实际: {len(prices)}"
        assert "$25.50" in prices[0]["text"], f"价格内容不符: {prices[0]['text']}"
        
        print("  ✓ HTML解析器正常")
    except AssertionError as e:
        print(f"  ✗ HTML解析器异常: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ HTML解析器异常: {e}")
        all_passed = False
    
    # 测试3: 抽取引擎
    print("[3/5] 测试抽取引擎...")
    try:
        site_spec = _get_sample_site_spec()
        engine = ExtractionEngine(site_spec)
        
        # 使用模拟HTML
        mock_html = '''
        <div class="product-item">
            <h2 class="product-title">Laptop Pro</h2>
            <span class="product-price">$999.99</span>
            <a class="product-link" href="/laptop-pro">View</a>
            <span class="product-rating">4.5</span>
            <span class="tag">Computers</span>
            <span class="tag">Electronics</span>
        </div>
        '''
        
        items = engine.extract_items(mock_html)
        assert len(items) == 1, f"应提取到1个条目，实际: {len(items)}"
        
        item = items[0]
        assert "title" in item, "应包含title字段"
        assert "price" in item, "应包含price字段"
        assert float(item["price"]) > 0, f"价格应大于0，实际: {item['price']}"
        assert item["link"].startswith("https://"), f"链接应为绝对URL，实际: {item['link']}"
        assert isinstance(item["tags"], list), "标签应为列表"
        assert len(item["tags"]) >= 2, f"标签应至少2个，实际: {len(item['tags'])}"
        
        print("  ✓ 抽取引擎正常")
        print(f"    样例: {item['title']}, 价格: {item['price']}, 标签数: {len(item['tags'])}")
    except AssertionError as e:
        print(f"  ✗ 抽取引擎异常: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 抽取引擎异常: {e}")
        all_passed = False
    
    # 测试4: 调度器
    print("[4/5] 测试调度器...")
    try:
        scheduler = ScrapeScheduler(delay=0.01)
        site_spec = _get_sample_site_spec()
        
        result = scheduler.scrape_site(site_spec, "https://example-store.com")
        assert result.status == "success", f"采集应成功，实际: {result.status}"
        assert len(result.items) >= 3, f"应至少3个条目，实际: {len(result.items)}"
        assert result.site == "sample_store"
        
        print(f"  ✓ 调度器正常，获取 {len(result.items)} 个条目")
    except AssertionError as e:
        print(f"  ✗ 调度器异常: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 调度器异常: {e}")
        all_passed = False
    
    # 测试5: 输出处理
    print("[5/5] 测试输出处理器...")
    try:
        handler = OutputHandler()
        
        test_data = {
            "site": "test",
            "items": [
                {"title": "Item 1", "price": 10.5},
                {"title": "Item 2", "price": 20.75},
            ]
        }
        
        json_str = handler.to_json(test_data)
        assert json_str is not None, "JSON序列化不应返回None"
        assert len(json_str) > 0, "JSON字符串不应为空"
        
        # 验证JSON可解析
        parsed = json.loads(json_str)
        assert len(parsed["items"]) == 2, "应包含2个条目"
        
        print("  ✓ 输出处理器正常")
    except AssertionError as e:
        print(f"  ✗ 输出处理器异常: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 输出处理器异常: {e}")
        all_passed = False
    
    # 汇总
    print("\n=== 自检结果 ===")
    if all_passed:
        print("✓ 全部测试通过")
        return True
    else:
        print("✗ 存在失败项，请检查")
        return False


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - {SKILL_NAME} v{VERSION}",
        epilog="示例: python main.py --selftest"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不访问网络，不依赖外部文件）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} {VERSION}"
    )
    
    parser.add_argument(
        "--url",
        type=str,
        help="目标URL（演示用，不实际请求）"
    )
    
    parser.add_argument(
        "--site",
        type=str,
        default="sample_store",
        help="站点名称（默认: sample_store）"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="输出JSON文件路径"
    )
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 演示模式
    if args.url:
        print(f"演示模式（不执行真实网络请求）")
        print(f"站点: {args.site}")
        print(f"URL: {args.url}")
        
        # 获取站点规格
        if args.site == "sample_store":
            site_spec = _get_sample_site_spec()
        else:
            print(f"E005: 不支持的站点: {args.site}")
            return 5
        
        # 执行采集
        scheduler = ScrapeScheduler(delay=0.1)
        result = scheduler.scrape_site(site_spec, args.url)
        
        # 输出结果
        output_data = asdict(result)
        
        if args.output:
            try:
                OutputHandler.save_to_file(output_data, args.output)
                print(f"结果已保存到: {args.output}")
            except RuntimeError as e:
                print(str(e))
                return 9
        else:
            print(OutputHandler.to_json(output_data))
        
        return 0
    
    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
