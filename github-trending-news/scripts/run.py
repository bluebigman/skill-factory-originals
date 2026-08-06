#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending News Skill - 生产级实现
获取 GitHub 每日 Trending 仓库信息并生成结构化周报
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入第三方库，如果失败则使用内置替代
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ============ 配置 ============
SKILL_NAME = "github-trending"
SKILL_VERSION = "2.0.0"
SKILL_DESCRIPTION = "获取 GitHub 每日 Trending 仓库信息并生成结构化周报"

# GitHub Trending 页面 URL
GITHUB_TRENDING_URL = "https://github.com/trending"
GITHUB_TRENDING_DAILY_URL = "https://github.com/trending?since=daily"
GITHUB_TRENDING_WEEKLY_URL = "https://github.com/trending?since=weekly"
GITHUB_TRENDING_MONTHLY_URL = "https://github.com/trending?since=monthly"

# 默认输出目录
DEFAULT_OUTPUT_DIR = str(Path.home() / ".workbuddy" / "skills" / SKILL_NAME)

# 缓存配置
CACHE_DIR = str(Path.home() / ".workbuddy" / "cache" / SKILL_NAME)
CACHE_TTL = 3600  # 1小时缓存

# 网络请求配置
REQUEST_TIMEOUT = 15  # 秒
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # 秒
RETRY_MAX_DELAY = 10  # 秒

# 用户代理
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ============ 工具函数 ============
def safe_filename(text: str) -> str:
    """将文本转换为安全的文件名"""
    return re.sub(r'[^\w\-_.]', '_', text)


def get_today_str() -> str:
    """获取今天的日期字符串 YYYY-MM-DD"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_date_range(days: int = 7) -> str:
    """获取日期范围字符串"""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return f"{start.strftime('%Y-%m-%d')}_to_{end.strftime('%Y-%m-%d')}"


def parse_stars(text: str) -> int:
    """解析 stars 数字，处理 '1.2k'、'3.4m' 等格式"""
    if not text:
        return 0
    text = text.strip().replace(',', '')
    match = re.match(r'([\d.]+)\s*([km]?)', text.lower())
    if not match:
        return 0
    value = float(match.group(1))
    suffix = match.group(2)
    if suffix == 'k':
        value *= 1000
    elif suffix == 'm':
        value *= 1000000
    return int(value)


def parse_star_change(text: str) -> int:
    """解析 star 变化，处理 '+1,234'、'-56' 等格式"""
    if not text:
        return 0
    text = text.strip().replace(',', '')
    match = re.search(r'([+-]?\d+)', text)
    if not match:
        return 0
    return int(match.group(1))


def exponential_backoff(attempt: int) -> float:
    """计算指数退避延迟时间"""
    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
    return delay


def atomic_write(filepath: str, content: str) -> bool:
    """原子化写入文件，避免半成品"""
    try:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        temp_path = filepath.with_suffix(filepath.suffix + '.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        print(f"错误: 写入文件失败 {filepath}: {e}", file=sys.stderr)
        return False


# ============ 数据抓取 ============
def fetch_url(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """抓取 URL 内容，带超时和指数退避重试"""
    for attempt in range(MAX_RETRIES):
        try:
            if HAS_REQUESTS:
                headers = {'User-Agent': USER_AGENT}
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response.text
            else:
                req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read().decode('utf-8')
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            if attempt < MAX_RETRIES - 1:
                delay = exponential_backoff(attempt)
                print(f"警告: 请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}", file=sys.stderr)
                print(f"将在 {delay} 秒后重试...", file=sys.stderr)
                time.sleep(delay)
            else:
                print(f"错误: 请求最终失败: {e}", file=sys.stderr)
                return None
    return None


def parse_trending_html(html: str) -> List[Dict[str, Any]]:
    """解析 GitHub Trending 页面 HTML，提取仓库信息"""
    repos = []
    
    # 检查 HTML 是否包含关键元素
    if 'Box-row' not in html and 'article' not in html:
        print("警告: HTML 结构可能已变化，未找到预期的仓库元素", file=sys.stderr)
        # 尝试正则备用解析
        pattern = r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"[^>]*>'
        matches = re.findall(pattern, html)
        if matches:
            print(f"使用正则备用解析，找到 {len(matches)} 个仓库", file=sys.stderr)
            for match in matches:
                repos.append({
                    'name': match,
                    'description': '',
                    'language': '',
                    'stars': 0,
                    'forks': 0,
                    'star_change': 0,
                    'url': f'https://github.com/{match}'
                })
            return repos
        else:
            print("错误: 无法从 HTML 中解析任何仓库信息", file=sys.stderr)
            return []
    
    if HAS_BS4:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            article_list = soup.select('article.Box-row')
            
            if not article_list:
                print("警告: BeautifulSoup 未找到 article.Box-row 元素，尝试备用解析", file=sys.stderr)
                # 备用解析：尝试其他选择器
                article_list = soup.select('article')
                if not article_list:
                    # 最终备用：正则解析
                    pattern = r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"[^>]*>'
                    matches = re.findall(pattern, html)
                    if matches:
                        print(f"使用正则备用解析，找到 {len(matches)} 个仓库", file=sys.stderr)
                        for match in matches:
                            repos.append({
                                'name': match,
                                'description': '',
                                'language': '',
                                'stars': 0,
                                'forks': 0,
                                'star_change': 0,
                                'url': f'https://github.com/{match}'
                            })
                        return repos
                    else:
                        print("错误: 无法从 HTML 中解析任何仓库信息", file=sys.stderr)
                        return []
            
            for article in article_list:
                try:
                    # 仓库名称
                    h2 = article.select_one('h2 a')
                    if not h2:
                        continue
                    full_name = h2.get('href', '').strip('/')
                    if not full_name:
                        continue
                    
                    # 描述
                    desc_elem = article.select_one('p')
                    description = desc_elem.get_text(strip=True) if desc_elem else ''
                    
                    # 语言
                    lang_elem = article.select_one('[itemprop="programmingLanguage"]')
                    language = lang_elem.get_text(strip=True) if lang_elem else ''
                    
                    # stars 和 forks
                    stars_elem = article.select_one('a[href$="/stargazers"]')
                    forks_elem = article.select_one('a[href$="/forks"]')
                    stars = parse_stars(stars_elem.get_text(strip=True)) if stars_elem else 0
                    forks = parse_stars(forks_elem.get_text(strip=True)) if forks_elem else 0
                    
                    # star 变化
                    change_elem = article.select_one('span.d-inline-block.float-sm-right')
                    star_change = parse_star_change(change_elem.get_text(strip=True)) if change_elem else 0
                    
                    repos.append({
                        'name': full_name,
                        'description': description,
                        'language': language,
                        'stars': stars,
                        'forks': forks,
                        'star_change': star_change,
                        'url': f'https://github.com/{full_name}'
                    })
                except Exception as e:
                    print(f"警告: 解析仓库条目失败: {e}", file=sys.stderr)
                    continue
        except Exception as e:
            print(f"警告: BeautifulSoup 解析失败: {e}，尝试正则备用解析", file=sys.stderr)
            # 正则备用解析
            pattern = r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"[^>]*>'
            matches = re.findall(pattern, html)
            if matches:
                print(f"使用正则备用解析，找到 {len(matches)} 个仓库", file=sys.stderr)
                for match in matches:
                    repos.append({
                        'name': match,
                        'description': '',
                        'language': '',
                        'stars': 0,
                        'forks': 0,
                        'star_change': 0,
                        'url': f'https://github.com/{match}'
                    })
            else:
                print("错误: 无法从 HTML 中解析任何仓库信息", file=sys.stderr)
    else:
        # 无 BeautifulSoup 时的简易正则解析
        pattern = r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"[^>]*>'
        matches = re.findall(pattern, html)
        if not matches:
            print("错误: 正则解析未找到任何仓库", file=sys.stderr)
            return []
        print(f"使用正则解析，找到 {len(matches)} 个仓库", file=sys.stderr)
        for match in matches:
            repos.append({
                'name': match,
                'description': '',
                'language': '',
                'stars': 0,
                'forks': 0,
                'star_change': 0,
                'url': f'https://github.com/{match}'
            })
    
    return repos


def fetch_trending(language: str = '', since: str = 'daily') -> List[Dict[str, Any]]:
    """获取 GitHub Trending 数据"""
    # 构建 URL，支持语言过滤
    url = GITHUB_TRENDING_URL
    
    # 如果指定了语言，添加到路径中
    if language:
        url += f"/{language}"
    
    # 添加时间参数
    params = []
    if since and since != 'daily':
        params.append(f'since={since}')
    
    if params:
        url += '?' + '&'.join(params)
    
    print(f"正在抓取: {url}", file=sys.stderr)
    html = fetch_url(url)
    if not html:
        return []
    
    repos = parse_trending_html(html)
    print(f"成功解析 {len(repos)} 个仓库", file=sys.stderr)
    return repos


# ============ 数据处理 ============
def filter_repos(repos: List[Dict[str, Any]], language: str = '') -> List[Dict[str, Any]]:
    """按语言过滤仓库"""
    if not language:
        return repos
    return [r for r in repos if r.get('language', '').lower() == language.lower()]


def sort_repos(repos: List[Dict[str, Any]], sort_by: str = 'star_change') -> List[Dict[str, Any]]:
    """按指定字段排序"""
    if sort_by == 'stars':
        return sorted(repos, key=lambda x: x.get('stars', 0), reverse=True)
    return sorted(repos, key=lambda x: x.get('star_change', 0), reverse=True)


def calculate_language_stats(repos: List[Dict[str, Any]]) -> Dict[str, int]:
    """统计语言分布"""
    stats = {}
    for repo in repos:
        lang = repo.get('language', 'Unknown')
        if not lang:
            lang = 'Unknown'
        stats[lang] = stats.get(lang, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))


# ============ 格式生成 ============
def generate_markdown(repos: List[Dict[str, Any]], language: str, since: str, lang: str = 'zh') -> str:
    """生成 Markdown 格式周报"""
    today = get_today_str()
    date_range = get_date_range(7 if since == 'weekly' else 1)
    
    lines = []
    if lang == 'zh':
        lines.append(f"# GitHub Trending 周报 ({date_range})")
        lines.append("")
        lines.append("## 总览")
        lines.append(f"- 统计周期：{date_range}")
        lines.append(f"- 仓库总数：{len(repos)}")
        
        if language:
            lines.append(f"- 过滤语言：{language}")
        
        lang_stats = calculate_language_stats(repos)
        if lang_stats:
            stats_str = ", ".join([f"{k} ({v})" for k, v in list(lang_stats.items())[:5]])
            lines.append(f"- 主要语言：{stats_str}")
        
        lines.append("")
        lines.append("## 热门仓库 TOP 10")
        lines.append("")
        
        for i, repo in enumerate(repos[:10], 1):
            lines.append(f"### {i}. {repo['name']} ⭐ {repo['stars']:,}")
            if repo.get('description'):
                lines.append(f"- **描述**：{repo['description']}")
            if repo.get('language'):
                lines.append(f"- **语言**：{repo['language']}")
            if repo.get('star_change'):
                change = repo['star_change']
                sign = '+' if change > 0 else ''
                lines.append(f"- **今日新增**：{sign}{change:,} stars")
            lines.append(f"- **链接**：{repo['url']}")
            lines.append("")
    else:
        lines.append(f"# GitHub Trending Report ({date_range})")
        lines.append("")
        lines.append("## Overview")
        lines.append(f"- Period: {date_range}")
        lines.append(f"- Total Repos: {len(repos)}")
        
        if language:
            lines.append(f"- Language Filter: {language}")
        
        lang_stats = calculate_language_stats(repos)
        if lang_stats:
            stats_str = ", ".join([f"{k} ({v})" for k, v in list(lang_stats.items())[:5]])
            lines.append(f"- Top Languages: {stats_str}")
        
        lines.append("")
        lines.append("## Top 10 Repositories")
        lines.append("")
        
        for i, repo in enumerate(repos[:10], 1):
            lines.append(f"### {i}. {repo['name']} ⭐ {repo['stars']:,}")
            if repo.get('description'):
                lines.append(f"- **Description**: {repo['description']}")
            if repo.get('language'):
                lines.append(f"- **Language**: {repo['language']}")
            if repo.get('star_change'):
                change = repo['star_change']
                sign = '+' if change > 0 else ''
                lines.append(f"- **Today's Change**: {sign}{change:,} stars")
            lines.append(f"- **URL**: {repo['url']}")
            lines.append("")
    
    return "\n".join(lines)


def generate_csv(repos: List[Dict[str, Any]]) -> str:
    """生成 CSV 格式数据"""
    output = []
    output.append("name,description,language,stars,forks,star_change,url")
    
    for repo in repos:
        desc = repo.get('description', '').replace('"', '""')
        output.append(f'"{repo["name"]}","{desc}","{repo.get("language", "")}",{repo.get("stars", 0)},{repo.get("forks", 0)},{repo.get("star_change", 0)},"{repo["url"]}"')
    
    return "\n".join(output)


def generate_json(repos: List[Dict[str, Any]]) -> str:
    """生成 JSON 格式数据"""
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(repos),
        "repositories": repos
    }
