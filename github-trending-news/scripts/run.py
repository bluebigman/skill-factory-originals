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
dry_run = False  # v3.274 模块级 dry-run 标志

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


def exponential_backoff(attempt: int) -> float:
    """计算指数退避延迟时间"""
    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
    return delay


def get_cache_path(since: str, language: Optional[str]) -> str:
    """获取缓存文件路径"""
    lang_part = f"_{safe_filename(language)}" if language else ""
    return str(Path(CACHE_DIR) / f"trending_{since}{lang_part}.json")


def read_cache(since: str, language: Optional[str]) -> Optional[Dict[str, Any]]:
    """读取缓存数据"""
    cache_path = get_cache_path(since, language)
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            # 检查缓存是否过期
            cached_time = datetime.fromisoformat(data.get("cached_at", ""))
            if datetime.now(timezone.utc) - cached_time < timedelta(seconds=CACHE_TTL):
                return data
    except Exception as e:
        print(f"读取缓存失败: {e}", file=sys.stderr)
    return None


def write_cache(since: str, language: Optional[str], repos: List[Dict[str, Any]]) -> None:
    """写入缓存数据"""
    cache_path = get_cache_path(since, language)
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        data = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "repos": repos,
        }
        with open(cache_path, "w", encoding="utf-8", errors="replace") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"写入缓存失败: {e}", file=sys.stderr)


def fetch_url(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """
    获取 URL 内容，带重试和指数退避
    优先使用 requests，如果不可用则使用 urllib
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    for attempt in range(MAX_RETRIES):
        try:
            if HAS_REQUESTS:
                response = requests.get(url, headers=headers, timeout=timeout)
                # 检查 HTTP 状态码
                if response.status_code == 403 or response.status_code == 429:
                    print(f"HTTP {response.status_code} 错误，触发重试", file=sys.stderr)
                    raise urllib.error.HTTPError(url, response.status_code, "Rate limited", None, None)
                response.raise_for_status()
                return response.text
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                print(f"HTTP {e.code} 错误，触发重试", file=sys.stderr)
            if attempt == MAX_RETRIES - 1:
                print(f"错误: 获取 {url} 失败: {e}", file=sys.stderr)
                return None
            delay = exponential_backoff(attempt)
            print(f"重试 {attempt + 1}/{MAX_RETRIES}，等待 {delay} 秒...", file=sys.stderr)
            time.sleep(delay)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"错误: 获取 {url} 失败: {e}", file=sys.stderr)
                return None
            delay = exponential_backoff(attempt)
            print(f"重试 {attempt + 1}/{MAX_RETRIES}，等待 {delay} 秒...", file=sys.stderr)
            time.sleep(delay)

    return None


def parse_trending_html(html: str) -> List[Dict[str, Any]]:
    """
    解析 GitHub Trending 页面 HTML，提取仓库信息
    支持 BeautifulSoup 和正则表达式两种方式
    """
    repos = []

    if HAS_BS4:
        try:
            soup = BeautifulSoup(html, "html.parser")
            article_list = soup.select("article.Box-row")

            for article in article_list:
                try:
                    # 仓库名称
                    name_elem = article.select_one("h2 a")
                    if not name_elem:
                        continue
                    full_name = name_elem.get("href", "").strip("/")
                    if not full_name:
                        continue

                    # 描述
                    desc_elem = article.select_one("p")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    # 语言
                    lang_elem = article.select_one("[itemprop='programmingLanguage']")
                    language = lang_elem.get_text(strip=True) if lang_elem else ""

                    # Stars（总数）
                    stars_elem = article.select_one("a[href$='/stargazers']")
                    stars_total = 0
                    if stars_elem:
                        stars_text = stars_elem.get_text(strip=True).replace(",", "")
                        try:
                            stars_total = int(stars_text)
                        except ValueError:
                            stars_total = 0

                    # Forks
                    forks_elem = article.select_one("a[href$='/forks']")
                    forks = 0
                    if forks_elem:
                        forks_text = forks_elem.get_text(strip=True).replace(",", "")
                        try:
                            forks = int(forks_text)
                        except ValueError:
                            forks = 0

                    # 今日新增 Stars
                    today_stars_elem = article.select_one("span.d-inline-block.float-sm-right")
                    today_stars = 0
                    if today_stars_elem:
                        today_text = today_stars_elem.get_text(strip=True)
                        match = re.search(r'([\d,]+)', today_text)
                        if match:
                            try:
                                today_stars = int(match.group(1).replace(",", ""))
                            except ValueError:
                                today_stars = 0

                    repos.append({
                        "name": full_name,
                        "description": description,
                        "language": language,
                        "stars_total": stars_total,
                        "forks": forks,
                        "stars_today": today_stars,
                        "url": f"https://github.com/{full_name}",
                    })
                except Exception as e:
                    print(f"解析仓库条目失败: {e}", file=sys.stderr)
                    continue
        except Exception as e:
            print(f"HTML 解析失败: {e}", file=sys.stderr)
            # 降级到正则表达式解析
            repos = parse_trending_html_regex(html)
    else:
        # 正则表达式回退方案
        repos = parse_trending_html_regex(html)

    return repos


def parse_trending_html_regex(html: str) -> List[Dict[str, Any]]:
    """使用正则表达式解析 HTML（降级方案）"""
    repos = []
    try:
        pattern = re.compile(
            r'<article class="Box-row">.*?'
            r'<h2.*?<a href="/([^"]+)".*?</a>.*?</h2>.*?'
            r'<p[^>]*>(.*?)</p>.*?'
            r'<span[^>]*itemprop="programmingLanguage"[^>]*>(.*?)</span>.*?'
            r'<a[^>]*href="[^"]*stargazers"[^>]*>([\d,]+)</a>.*?'
            r'<a[^>]*href="[^"]*forks"[^>]*>([\d,]+)</a>.*?'
            r'<span[^>]*class="d-inline-block float-sm-right"[^>]*>([^<]*)</span>',
            re.DOTALL
        )

        for match in pattern.finditer(html):
            try:
                full_name = match.group(1).strip()
                description = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                language = match.group(3).strip()
                stars_total = int(match.group(4).replace(",", ""))
                forks = int(match.group(5).replace(",", ""))
                today_text = match.group(6)
                today_match = re.search(r'([\d,]+)', today_text)
                today_stars = int(today_match.group(1).replace(",", "")) if today_match else 0

                repos.append({
                    "name": full_name,
                    "description": description,
                    "language": language,
                    "stars_total": stars_total,
                    "forks": forks,
                    "stars_today": today_stars,
                    "url": f"https://github.com/{full_name}",
                })
            except Exception as e:
                print(f"正则解析仓库条目失败: {e}", file=sys.stderr)
                continue
    except Exception as e:
        print(f"正则解析失败: {e}", file=sys.stderr)
    
    return repos


def filter_repos(repos: List[Dict[str, Any]], language: Optional[str] = None,
                 limit: int = 25) -> List[Dict[str, Any]]:
    """按语言过滤并限制数量"""
    if language:
        language_lower = language.lower()
        repos = [r for r in repos if r.get("language", "").lower() == language_lower]

    # 按今日 stars 排序（降序）
    repos.sort(key=lambda x: x.get("stars_today", 0), reverse=True)

    return repos[:limit]


def generate_markdown(repos: List[Dict[str, Any]], language: Optional[str],
                      since: str, lang_output: str = "zh") -> str:
    """生成 Markdown 格式周报"""
    lines = []
    lines.append("# GitHub Trending 周报")
    lines.append("")
    lines.append(f"- **生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"- **时间范围**: {since}")
    if language:
        lines.append(f"- **语言过滤**: {language}")
    lines.append(f"- **仓库数量**: {len(repos)}")
    lines.append("")

    if not repos:
        lines.append("> 未找到符合条件的仓库。")
        return "\n".join(lines)

    lines.append("## 仓库列表")
    lines.append("")
    lines.append("| # | 仓库 | 描述 | 语言 | Stars | Forks | 今日Stars |")
    lines.append("|---|------|------|------|-------|-------|-----------|")

    for idx, repo in enumerate(repos, 1):
        name = repo.get("name", "")
        desc = repo.get("description", "")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        lang = repo.get("language", "")
        stars = repo.get("stars_total", 0)
        forks = repo.get("forks", 0)
        today = repo.get("stars_today", 0)

        lines.append(f"| {idx} | [{name}]({repo.get('url', '#')}) | {desc} | {lang} | {stars:,} | {forks:,} | +{today:,} |")

    lines.append("")
    lines.append("## 语言统计")
    lines.append("")

    lang_stats = {}
    for repo in repos:
        lang = repo.get("language", "Unknown")
        lang_stats[lang] = lang_stats.get(lang, 0) + 1

    for lang, count in sorted(lang_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(repos)) * 100
        lines.append(f"- {lang}: {count} ({percentage:.1f}%)")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 GitHub Trending Skill 自动生成*")

    return "\n".join(lines)


def generate_csv(repos: List[Dict[str, Any]]) -> str:
    """生成 CSV 格式数据"""
    if not repos:
        return "name,description,language,stars_total,forks,stars_today,url\n"

    output = []
    fieldnames = ["name", "description", "language", "stars_total", "forks", "stars_today", "url"]
    output.append(",".join(fieldnames))

    for repo in repos:
        row = [
            repo.get("name", ""),
            repo.get("description", "").replace(",", " ").replace("\n", " "),
            repo.get("language", ""),
            str(repo.get("stars_total", 0)),
            str(repo.get("forks", 0)),
            str(repo.get("stars_today", 0)),
            repo.get("url", ""),
        ]
        output.append(",".join(row))

    return "\n".join(output)


def generate_json(repos: List[Dict[str, Any]], language: Optional[str],
                  since: str) -> str:
    """生成 JSON 格式数据"""
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since": since,
        "language": language,
        "total_count": len(repos),
        "repositories": repos,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def atomic_write(filepath: str, content: str) -> bool:
    """原子化写入文件"""
    try:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 写入临时文件
        temp_path = filepath.with_suffix(filepath.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # 原子替换
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        print(f"写入文件失败: {e}", file=sys.stderr)
        return False


def get_output_path(format_type: str, language: Optional[str], since: str) -> str:
    """生成默认输出文件路径"""
    today = get_today_str()
    lang_part = f"_{safe_filename(language)}" if language else ""
    filename = f"github_trending_{since}{lang_part}_{today}.{format_type}"
    return str(Path(DEFAULT_OUTPUT_DIR) / filename)


def fetch_trending_data(since: str = "daily", language: Optional[str] = None,
                        limit: int = 25) -> Tuple[List[Dict[str, Any]], bool]:
    """
    获取并解析 Trending 数据
    返回 (仓库列表, 是否使用缓存)
    """
    # 先尝试读取缓存
    cached_data = read_cache(since, language)
    if cached_data:
        print("使用缓存数据", file=sys.stderr)
        repos = cached_data.get("repos", [])
        return filter_repos(repos, language, limit), True

    # 构建 URL
    url = GITH
