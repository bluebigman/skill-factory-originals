#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending News Skill
获取 GitHub 每日 Trending 仓库信息并生成新闻摘要
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

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
SKILL_VERSION = "1.0.0"
SKILL_DESCRIPTION = "获取 GitHub 每日 Trending 仓库信息并生成新闻摘要"

# GitHub Trending 页面 URL
GITHUB_TRENDING_URL = "https://github.com/trending"
GITHUB_TRENDING_DAILY_URL = "https://github.com/trending?since=daily"
GITHUB_TRENDING_WEEKLY_URL = "https://github.com/trending?since=weekly"
GITHUB_TRENDING_MONTHLY_URL = "https://github.com/trending?since=monthly"

# 默认输出目录
DEFAULT_OUTPUT_DIR = str(Path.home() / ".workbuddy" / "skills" / SKILL_NAME)


# ============ 工具函数 ============
def safe_filename(text: str) -> str:
    """将文本转换为安全的文件名"""
    return re.sub(r'[^\w\-_.]', '_', text)


def get_today_str() -> str:
    """获取今天的日期字符串 YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")


def get_date_range(days: int = 7) -> str:
    """获取日期范围字符串"""
    end = datetime.now()
    start = end - timedelta(days=days)
    return f"{start.strftime('%Y-%m-%d')}_to_{end.strftime('%Y-%m-%d')}"


def load_spec() -> Dict[str, Any]:
    """加载技能规格说明"""
    return {
        "name": SKILL_NAME,
        "version": SKILL_VERSION,
        "description": SKILL_DESCRIPTION,
        "triggers": ["github trending", "github 趋势", "trending", "github热门"],
        "parameters": {
            "since": {
                "type": "string",
                "enum": ["daily", "weekly", "monthly"],
                "default": "daily",
                "description": "时间范围"
            },
            "language": {
                "type": "string",
                "description": "编程语言过滤",
                "default": ""
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "返回的仓库数量"
            }
        }
    }


def match_trigger(text: str) -> bool:
    """检查文本是否匹配触发条件"""
    triggers = load_spec()["triggers"]
    text_lower = text.lower()
    return any(trigger.lower() in text_lower for trigger in triggers)


# ============ 网络请求 ============
def fetch_page(url: str, timeout: int = 30) -> Optional[str]:
    """获取网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        if HAS_REQUESTS:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        else:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


# ============ 数据解析 ============
def parse_trending_repos(html: str, limit: int = 10) -> List[Dict[str, Any]]:
    """解析 GitHub Trending 页面，提取仓库信息"""
    repos = []
    
    if HAS_BS4:
        soup = BeautifulSoup(html, 'html.parser')
        # 查找仓库条目
        articles = soup.select('article.Box-row')
        
        for article in articles[:limit]:
            try:
                # 仓库名称
                h2 = article.select_one('h2 a')
                if not h2:
                    continue
                repo_name = h2.get_text(strip=True).replace('\n', '').replace(' ', '')
                
                # 仓库描述
                desc_elem = article.select_one('p')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # 编程语言
                lang_elem = article.select_one('[itemprop="programmingLanguage"]')
                language = lang_elem.get_text(strip=True) if lang_elem else ""
                
                # 星标数
                stars_elem = article.select_one('a[href$="/stargazers"]')
                stars = stars_elem.get_text(strip=True) if stars_elem else "0"
                stars = stars.replace(',', '')
                
                # 今日星标
                today_stars_elem = article.select_one('span.d-inline-block.float-sm-right')
                today_stars = today_stars_elem.get_text(strip=True) if today_stars_elem else ""
                
                # 仓库链接
                repo_url = f"https://github.com{repo_name}" if repo_name else ""
                
                repos.append({
                    "name": repo_name,
                    "url": repo_url,
                    "description": description,
                    "language": language,
                    "stars": stars,
                    "today_stars": today_stars
                })
            except Exception as e:
                print(f"Error parsing repo: {e}", file=sys.stderr)
                continue
    else:
        # 使用正则表达式解析（备用方案）
        # 匹配仓库名称
        repo_pattern = r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</span>\s*<span[^>]*>([^<]+)</span>'
        matches = re.findall(repo_pattern, html)
        
        for match in matches[:limit]:
            repo_name = f"{match[1]}/{match[2]}"
            repos.append({
                "name": repo_name,
                "url": f"https://github.com/{repo_name}",
                "description": "",
                "language": "",
                "stars": "0",
                "today_stars": ""
            })
    
    return repos


# ============ 数据生成 ============
def generate_news(repos: List[Dict[str, Any]], since: str = "daily") -> str:
    """生成新闻摘要文本"""
    if not repos:
        return "今日没有找到 GitHub Trending 仓库。"
    
    since_map = {
        "daily": "今日",
        "weekly": "本周",
        "monthly": "本月"
    }
    since_label = since_map.get(since, "今日")
    
    lines = [
        f"# GitHub Trending {since_label}热门仓库",
        "",
        f"共发现 {len(repos)} 个热门仓库：",
        ""
    ]
    
    for i, repo in enumerate(repos, 1):
        name = repo.get("name", "未知仓库")
        desc = repo.get("description", "")
        lang = repo.get("language", "")
        stars = repo.get("stars", "0")
        today_stars = repo.get("today_stars", "")
        url = repo.get("url", "")
        
        lines.append(f"## {i}. {name}")
        if desc:
            lines.append(f"   {desc}")
        if lang:
            lines.append(f"   语言: {lang}")
        lines.append(f"   星标: {stars}")
        if today_stars:
            lines.append(f"   {today_stars}")
        if url:
            lines.append(f"   链接: {url}")
        lines.append("")
    
    return "\n".join(lines)


def generate_json(repos: List[Dict[str, Any]], since: str = "daily") -> str:
    """生成 JSON 格式数据"""
    data = {
        "skill": SKILL_NAME,
        "version": SKILL_VERSION,
        "timestamp": datetime.now().isoformat(),
        "since": since,
        "repos": repos
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# ============ 主功能 ============
def run(since: str = "daily", language: str = "", limit: int = 10, output_dir: str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """运行技能主功能"""
    # 构建 URL
    url = GITHUB_TRENDING_URL
    params = []
    if since != "daily":
        params.append(f"since={since}")
    if language:
        params.append(f"language={language}")
    if params:
        url += "?" + "&".join(params)
    
    # 获取页面
    html = fetch_page(url)
    if not html:
        return {
            "success": False,
            "error": "无法获取 GitHub Trending 页面",
            "data": None
        }
    
    # 解析仓库
    repos = parse_trending_repos(html, limit)
    
    # 生成输出
    news_text = generate_news(repos, since)
    json_data = generate_json(repos, since)
    
    # 保存文件
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"github_trending_{since}_{timestamp}"
    
    md_path = os.path.join(output_dir, f"{base_name}.md")
    json_path = os.path.join(output_dir, f"{base_name}.json")
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(news_text)
    
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_data)
    
    return {
        "success": True,
        "data": {
            "repos": repos,
            "news": news_text,
            "json": json_data,
            "files": [md_path, json_path]
        }
    }


# ============ 自检函数 ============
def selftest() -> int:
    """自检函数，验证技能功能是否正常"""
    print("Running selftest for github-trending-news skill...")
    
    # 测试 1: 检查依赖
    print("[1/5] Checking dependencies...")
    if not HAS_REQUESTS and not HAS_BS4:
        print("  Warning: Neither requests nor bs4 is available, using fallback methods")
    
    # 测试 2: 测试 load_spec
    print("[2/5] Testing load_spec...")
    spec = load_spec()
    assert spec["name"] == SKILL_NAME, "Skill name mismatch"
    assert "triggers" in spec, "Missing triggers"
    print("  OK")
    
    # 测试 3: 测试 match_trigger
    print("[3/5] Testing match_trigger...")
    assert match_trigger("github trending") == True, "Should match 'github trending'"
    assert match_trigger("github 趋势") == True, "Should match 'github 趋势'"
    assert match_trigger("hello world") == False, "Should not match 'hello world'"
    print("  OK")
    
    # 测试 4: 测试数据生成（不依赖网络）
    print("[4/5] Testing data generation...")
    test_repos = [
        {
            "name": "test/repo1",
            "url": "https://github.com/test/repo1",
            "description": "Test repository 1",
            "language": "Python",
            "stars": "100",
            "today_stars": "10 stars today"
        },
        {
            "name": "test/repo2",
            "url": "https://github.com/test/repo2",
            "description": "Test repository 2",
            "language": "JavaScript",
            "stars": "200",
            "today_stars": "20 stars today"
        }
    ]
    
    news = generate_news(test_repos, "daily")
    assert "GitHub Trending" in news, "News should contain 'GitHub Trending'"
    assert "test/repo1" in news, "News should contain repo1"
    assert "test/repo2" in news, "News should contain repo2"
    
    json_data = generate_json(test_repos, "daily")
    parsed = json.loads(json_data)
    assert parsed["skill"] == SKILL_NAME, "JSON should contain skill name"
    assert len(parsed["repos"]) == 2, "JSON should contain 2 repos"
    print("  OK")
    
    # 测试 5: 测试文件输出
    print("[5/5] Testing file output...")
    test_dir = Path(__file__).parent / "_selftest"
    test_dir.mkdir(exist_ok=True)
    
    # 测试写入文件
    test_file = test_dir / "test_output.md"
    test_file.write_text("# Test\n", encoding="utf-8")
    assert test_file.exists(), "Test file should exist"
    
    # 测试读取文件
    content = test_file.read_text(encoding="utf-8")
    assert content == "# Test\n", "Test file content mismatch"
    
    # 清理测试文件
    try:
        test_file.unlink()
    except OSError:
        # 如果删除失败（如 Windows 回收站问题），尝试直接删除
        try:
            os.remove(test_file)
        except OSError:
            print("  Warning: Could not delete test file, but this is not critical")
    
    # 清理测试目录
    try:
        test_dir.rmdir()
    except OSError:
        print("  Warning: Could not remove test directory, but this is not critical")
    
    print("  OK")
    
    print("\nAll selftest checks passed!")
    return 0


# ============ 命令行入口 ============
def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(description=SKILL_DESCRIPTION)
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--since", choices=["daily", "weekly", "monthly"], default="daily", help="时间范围")
    parser.add_argument("--language", default="", help="编程语言过滤")
    parser.add_argument("--limit", type=int, default=10, help="返回的仓库数量")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="输出目录")
    
    args = parser.parse_args()
    
    if args.selftest:
        return selftest()
    
    # 正常运行
    result = run(
        since=args.since,
        language=args.language,
        limit=args.limit,
        output_dir=args.output_dir
    )
    
    if result["success"]:
        print(result["data"]["news"])
        print(f"\nFiles saved to: {', '.join(result['data']['files'])}")
        return 0
    else:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
