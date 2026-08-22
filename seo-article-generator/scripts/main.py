#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seo-article-generator 独立实现脚本
----------------------------------
基于真实搜索数据与网页内容的SEO文章生成器，提供关键词解析、内容结构生成等核心能力。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --keyword "2025年家庭储能电池选购指南"
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import hashlib
from collections import OrderedDict

# 错误码定义
ERROR_CODES = {
    "E001": "参数缺失或格式错误",
    "E002": "关键词为空",
    "E003": "关键词长度超出限制",
    "E004": "URL 格式无效",
    "E005": "文档解析失败",
    "E006": "文章结构生成失败",
    "E007": "批量处理输入无效",
    "E008": "内部逻辑错误",
    "E009": "输出写入失败",
    "E010": "未知错误",
    "E011": "网络请求失败",
    "E012": "搜索结果为空",
}


@dataclass
class KeywordAnalysis:
    """关键词解析结果"""
    raw_keyword: str
    core_topic: str = ""
    search_intent: str = ""
    target_audience: str = ""
    sub_keywords: List[str] = field(default_factory=list)
    search_results: List[Dict] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)


@dataclass
class ArticleOutline:
    """文章大纲结构"""
    title: str = ""
    h1: str = ""
    h2_sections: List[str] = field(default_factory=list)
    h3_subsections: Dict[str, List[str]] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


class LRUCache:
    """带TTL和容量上限的LRU缓存"""
    def __init__(self, capacity: int = 100, ttl: int = 3600):
        self.capacity = capacity
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
    
    def get(self, key: str):
        if key not in self.cache:
            return None
        # 检查TTL
        if time.time() - self.timestamps[key] > self.ttl:
            self._remove(key)
            return None
        # 更新访问顺序
        value = self.cache.pop(key)
        self.cache[key] = value
        return value
    
    def put(self, key: str, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            # 移除最久未使用的
            oldest = next(iter(self.cache))
            self._remove(oldest)
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def _remove(self, key: str):
        if key in self.cache:
            self.cache.pop(key)
        if key in self.timestamps:
            self.timestamps.pop(key)


class SearchAPIClient:
    """搜索API客户端 - 使用DuckDuckGo HTML搜索端点获取真实结果"""
    
    BASE_URL = "https://html.duckduckgo.com/html/"
    TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒
    
    def __init__(self):
        self.cache = LRUCache(capacity=100, ttl=3600)  # 带TTL和容量的LRU缓存
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """执行搜索请求，带重试退避机制和缓存"""
        # 检查缓存
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached[:max_results]
        
        params = {
            'q': query,
            'kl': 'cn-zh',  # 中文搜索结果
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        
        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    html_content = response.read().decode('utf-8', errors='replace')
                    results = self._parse_results(html_content)
                    if results:
                        # 缓存结果
                        self.cache.put(cache_key, results)
                        return results[:max_results]
                    else:
                        # 结果为空，抛出E012错误
                        raise ValueError("E012: 搜索结果为空")
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    # 限流或服务器错误，指数退避
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (2 ** attempt))
                        continue
                    else:
                        raise ConnectionError(f"E011: 搜索请求失败 - HTTP {e.code}")
                else:
                    raise ConnectionError(f"E011: 搜索请求失败 - HTTP {e.code}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    raise ConnectionError(f"E011: 搜索请求失败 - {str(e)}")
            except ValueError as e:
                # E012错误，直接抛出
                raise
        
        return []
    
    def _parse_results(self, html_content: str) -> List[Dict]:
        """解析DuckDuckGo HTML搜索结果，带结构变化检测"""
        results = []
        
        try:
            # 使用正则提取搜索结果
            # DuckDuckGo HTML结果结构: <a class="result__a" href="...">标题</a>
            # <a class="result__snippet" ...>摘要</a>
            
            # 提取所有结果块
            result_blocks = re.findall(
                r'<div class="result[^"]*".*?</div>',
                html_content,
                re.DOTALL
            )
            
            for block in result_blocks[:10]:  # 最多解析10个结果
                # 提取标题
                title_match = re.search(r'class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
                # 提取URL
                url_match = re.search(r'class="result__a"[^>]*href="([^"]*)"', block)
                # 提取摘要
                snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
                
                if title_match and url_match:
                    # 清理HTML标签
                    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                    url = url_match.group(1)
                    snippet = ''
                    if snippet_match:
                        snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                    
                    # 处理DuckDuckGo的重定向URL
                    if 'uddg=' in url:
                        url = urllib.parse.unquote(url.split('uddg=')[1].split('&')[0])
                    
                    if title and url:
                        results.append({
                            'title': title[:200],
                            'url': url,
                            'snippet': snippet[:300]
                        })
            
            # 结构变化检测：如果HTML包含搜索结果标记但解析结果为空，抛出E005
            if 'result__a' in html_content and not results:
                raise ValueError("E005: 文档解析失败 - 搜索结果结构可能已变化")
                
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            # 其他解析异常，抛出E005
            raise ValueError(f"E005: 文档解析失败 - {str(e)}")
        
        return results


class WebContentFetcher:
    """网页内容抓取器"""
    
    TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    def __init__(self):
        self.cache = LRUCache(capacity=50, ttl=1800)  # 带TTL和容量的LRU缓存
    
    def fetch_content(self, url: str) -> str:
        """抓取网页内容，带缓存和重试机制"""
        cached = self.cache.get(url)
        if cached is not None:
            return cached
        
        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    content = response.read().decode('utf-8', errors='replace')
                    # 简单提取文本内容（去除HTML标签）
                    text = re.sub(r'<script[^>]*>.*?</script>', ' ', content, flags=re.DOTALL)
                    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    self.cache.put(url, text[:5000])  # 缓存前5000字符
                    return self.cache.get(url)
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (2 ** attempt))
                        continue
                    else:
                        return ""  # 降级：返回空内容
                else:
                    return ""
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    return ""  # 降级：返回空内容
        
        return ""


class SEOArticleGenerator:
    """SEO 文章生成器核心类"""

    # 搜索意图关键词模式
    INTENT_PATTERNS = {
        "对比": ["对比", "比较", "vs", "哪个好", "区别"],
        "选购": ["选购", "推荐", "指南", "怎么选", "购买"],
        "教程": ["教程", "怎么", "如何", "步骤", "方法"],
        "资讯": ["新闻", "最新", "趋势", "报告", "分析"],
    }

    # 受众关键词模式
    AUDIENCE_PATTERNS = {
        "户主/家庭用户": ["家庭", "家用", "户主", "住宅"],
        "DIY爱好者": ["DIY", "自制", "自己动手"],
        "企业采购": ["企业", "商用", "采购", "公司"],
        "专业人士": ["工程师", "专业", "行业"],
    }

    # 常见停用词（用于主题提取）
    STOP_WORDS = {"的", "了", "和", "是", "在", "有", "与", "及", "或", "年", "月", "日"}

    def __init__(self, max_keyword_length: int = 100, use_web: bool = True):
        self.max_keyword_length = max_keyword_length
        self.use_web = use_web
        self.search_client = SearchAPIClient() if use_web else None
        self.fetcher = WebContentFetcher() if use_web else None

    def analyze_keyword(self, keyword: str) -> KeywordAnalysis:
        """解析关键词，提取核心主题、搜索意图和目标受众"""
        if not keyword or not keyword.strip():
            raise ValueError("E002: 关键词为空")

        keyword = keyword.strip()
        if len(keyword) > self.max_keyword_length:
            raise ValueError(f"E003: 关键词长度超出限制（最大{self.max_keyword_length}字符）")

        # 提取核心主题
        core_topic = self._extract_core_topic(keyword)

        # 识别搜索意图
        search_intent = self._detect_intent(keyword)

        # 识别目标受众
        target_audience = self._detect_audience(keyword)

        # 生成子关键词
        sub_keywords = self._generate_sub_keywords(keyword, core_topic)

        # 获取真实搜索数据
        search_results = []
        source_urls = []
        if self.use_web and self.search_client:
            try:
                search_results = self.search_client.search(keyword)
                source_urls = [r['url'] for r in search_results if r.get('url')]
            except (ConnectionError, ValueError) as e:
                print(f"警告: 搜索请求失败，使用本地模式 - {e}")
                search_results = []
                source_urls = []

        return KeywordAnalysis(
            raw_keyword=keyword,
            core_topic=core_topic,
            search_intent=search_intent,
            target_audience=target_audience,
            sub_keywords=sub_keywords,
            search_results=search_results,
            source_urls=source_urls,
        )

    def _extract_core_topic(self, keyword: str) -> str:
        """从关键词中提取核心主题"""
        # 移除常见意图词
        intent_words = []
        for words in self.INTENT_PATTERNS.values():
            intent_words.extend(words)

        cleaned = keyword
        for word in intent_words:
            cleaned = cleaned.replace(word, "")

        # 移除停用词
        for word in self.STOP_WORDS:
            cleaned = cleaned.replace(word, "")

        # 取第一个有意义的片段（长度>=2）
        parts = [p for p in re.split(r'[\s,，。；;、]+', cleaned) if len(p) >= 2]
        if parts:
            return parts[0]
        return keyword[:10]  # 兜底

    def _detect_intent(self, keyword: str) -> str:
        """检测搜索意图"""
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in keyword:
                    return intent
        return "综合"  # 默认意图

    def _detect_audience(self, keyword: str) -> str:
        """检测目标受众"""
        for audience, patterns in self.AUDIENCE_PATTERNS.items():
            for pattern in patterns:
                if pattern in keyword:
                    return audience
        return "通用人群"  # 默认受众

    def _generate_sub_keywords(self, keyword: str, core_topic: str) -> List[str]:
        """生成相关子关键词"""
        sub_keywords = []
        intent = self._detect_intent(keyword)

        # 基于核心主题生成扩展
        if core_topic:
            sub_keywords.append(f"{core_topic} 优缺点")
            sub_keywords.append(f"{core_topic} 价格")
            sub_keywords.append(f"{core_topic} 品牌推荐")

        # 基于意图生成
        if intent == "对比":
            sub_keywords.append(f"{core_topic} 对比评测")
        elif intent == "选购":
            sub_keywords.append(f"{core_topic} 选购技巧")
        elif intent == "教程":
            sub_keywords.append(f"{core_topic} 使用教程")

        # 去重并限制数量
        unique_keywords = []
        for kw in sub_keywords:
            if kw not in unique_keywords:
                unique_keywords.append(kw)
            if len(unique_keywords) >= 5:
                break

        return unique_keywords

    def generate_outline(self, keyword: str) -> ArticleOutline:
        """根据关键词生成文章大纲"""
        try:
            analysis = self.analyze_keyword(keyword)

            # 获取网页内容用于增强生成
            web_content = ""
            if self.use_web and self.fetcher and analysis.source_urls:
                # 并发抓取前2个来源，限制并发数
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [executor.submit(self.fetcher.fetch_content, url) 
                              for url in analysis.source_urls[:2]]
                    for future in as_completed(futures):
                        content = future.result()
                        if content:
                            web_content += content + " "

            # 生成标题
            title = self._generate_title(analysis)

            # 生成 H1
            h1 = analysis.core_topic if analysis.core_topic else keyword

            # 生成 H2 段落
            h2_sections = self._generate_h2_sections(analysis, web_content)

            # 生成 H3 子段落
            h3_subsections = self._generate_h3_subsections(h2_sections, web_content)

            # 标记缺失字段
            missing = self._identify_missing_fields(analysis)

            return ArticleOutline(
                title=title,
                h1=h1,
                h2_sections=h2_sections,
                h3_subsections=h3_subsections,
                missing_fields=missing,
                sources=analysis.source_urls,
            )
        except ValueError as e:
            raise ValueError(f"E006: 文章结构生成失败 - {str(e)}")
        except Exception as e:
            raise RuntimeError(f"E008: 内部逻辑错误 - {str(e)}")

    def _generate_title(self, analysis: KeywordAnalysis) -> str:
        """生成文章标题"""
        topic = analysis.core
