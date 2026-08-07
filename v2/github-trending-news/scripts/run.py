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


def exponential_backoff(attempt: int) -> float:
    """计算指数退避延迟时间"""
    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
    return delay


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
                response.raise_for_status()
                return response.text
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read().decode("utf-8")
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

    else:
        # 正则表达式回退方案
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
        with open(temp_path, "w", encoding="utf-8") as f:
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
                        limit: int = 25) -> List[Dict[str, Any]]:
    """获取并解析 Trending 数据"""
    # 构建 URL
    url = GITHUB_TRENDING_URL
    params = []
    if since:
        params.append(f"since={since}")
    if language:
        params.append(f"language={language}")
    if params:
        url += "?" + "&".join(params)

    # 获取页面
    html = fetch_url(url)
    if not html:
        print("错误: 无法获取 GitHub Trending 页面", file=sys.stderr)
        return []

    # 解析数据
    repos = parse_trending_html(html)

    # 过滤和限制
    repos = filter_repos(repos, language, limit)

    return repos


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("开始自检...")
    errors = []

    # 测试 1: 工具函数
    try:
        assert safe_filename("test/name:with*chars") == "test_name_with_chars"
        assert get_today_str() == datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert get_date_range(7).count("-") == 4
        print("✓ 工具函数测试通过")
    except AssertionError as e:
        errors.append(f"工具函数测试失败: {e}")
        print("✗ 工具函数测试失败")

    # 测试 2: 指数退避
    try:
        assert exponential_backoff(0) == 2
        assert exponential_backoff(1) == 4
        assert exponential_backoff(2) == 8
        assert exponential_backoff(10) == 10  # 达到上限
        print("✓ 指数退避测试通过")
    except AssertionError as e:
        errors.append(f"指数退避测试失败: {e}")
        print("✗ 指数退避测试失败")

    # 测试 3: HTML 解析（使用模拟数据）
    try:
        mock_html = """
        <article class="Box-row">
            <h2><a href="/test/repo1">test/repo1</a></h2>
            <p>Test repository 1</p>
            <span itemprop="programmingLanguage">Python</span>
            <a href="/test/repo1/stargazers">1,234</a>
            <a href="/test/repo1/forks">56</a>
            <span class="d-inline-block float-sm-right">+89 stars today</span>
        </article>
        <article class="Box-row">
            <h2><a href="/test/repo2">test/repo2</a></h2>
            <p>Test repository 2</p>
            <span itemprop="programmingLanguage">JavaScript</span>
            <a href="/test/repo2/stargazers">567</a>
            <a href="/test/repo2/forks">23</a>
            <span class="d-inline-block float-sm-right">+45 stars today</span>
        </article>
        """
        repos = parse_trending_html(mock_html)
        assert len(repos) == 2
        assert repos[0]["name"] == "test/repo1"
        assert repos[0]["stars_total"] == 1234
        assert repos[0]["stars_today"] == 89
        assert repos[1]["language"] == "JavaScript"
        print("✓ HTML 解析测试通过")
    except AssertionError as e:
        errors.append(f"HTML 解析测试失败: {e}")
        print("✗ HTML 解析测试失败")

    # 测试 4: 过滤函数
    try:
        test_repos = [
            {"name": "a", "language": "Python", "stars_today": 10},
            {"name": "b", "language": "JavaScript", "stars_today": 20},
            {"name": "c", "language": "Python", "stars_today": 30},
        ]
        filtered = filter_repos(test_repos, "python", 2)
        assert len(filtered) == 2
        assert filtered[0]["name"] == "c"
        assert filtered[1]["name"] == "a"
        print("✓ 过滤函数测试通过")
    except AssertionError as e:
        errors.append(f"过滤函数测试失败: {e}")
        print("✗ 过滤函数测试失败")

    # 测试 5: 格式生成
    try:
        test_repos = [
            {"name": "test/repo", "description": "Test", "language": "Python",
             "stars_total": 100, "forks": 10, "stars_today": 5,
             "url": "https://github.com/test/repo"},
        ]
        md = generate_markdown(test_repos, "python", "daily", "zh")
        assert "# GitHub Trending 周报" in md
        assert "test/repo" in md

        csv_data = generate_csv(test_repos)
        assert "name,description" in csv_data

        json_data = generate_json(test_repos, "python", "daily")
        assert "repositories" in json_data
        print("✓ 格式生成测试通过")
    except AssertionError as e:
        errors.append(f"格式生成测试失败: {e}")
        print("✗ 格式生成测试失败")

    # 测试 6: 原子写入
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            temp_path = f.name
        assert atomic_write(temp_path, "test content")
        with open(temp_path, "r") as f:
            assert f.read() == "test content"
        os.unlink(temp_path)
        print("✓ 原子写入测试通过")
    except AssertionError as e:
        errors.append(f"原子写入测试失败: {e}")
        print("✗ 原子写入测试失败")

    # 测试 7: 真实网络请求（可选，如果网络不可用则跳过）
    try:
        repos = fetch_trending_data(since="daily", limit=5)
        if repos:
            assert len(repos) > 0
            assert "name" in repos[0]
            print(f"✓ 真实网络请求测试通过（获取 {len(repos)} 个仓库）")
        else:
            print("⚠ 真实网络请求测试跳过（网络不可用或返回空）")
    except Exception as e:
        print(f"⚠ 真实网络请求测试跳过: {e}")

    # 汇总结果
    if errors:
        print(f"\n自检失败: {len(errors)} 个错误")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("\n所有自检通过！")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description=SKILL_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python run.py --since weekly --language python --format markdown\n"
               "  python run.py --selftest\n"
    )

    parser.add_argument("--language", type=str, default=None,
                        help="编程语言过滤（如 python、javascript）")
    parser.add_argument("--since", type=str, default="daily",
                        choices=["daily", "weekly", "monthly"],
                        help="时间范围: daily/weekly/monthly（默认: daily）")
    parser.add_argument("--format", type=str, default="markdown",
                        choices=["markdown", "csv", "json"],
                        help="输出格式: markdown/csv/json（默认: markdown）")
    parser.add_argument("--output", type=str, default=None,
                        help="输出文件路径（默认自动生成）")
    parser.add_argument("--limit", type=int, default=25,
                        help="最大仓库数量 1-50（默认: 25）")
    parser.add_argument("--language-output", type=str, default="zh",
                        choices=["zh", "en"],
                        help="输出语言: zh/en（默认: zh）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行自检并退出")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 参数校验
    if not 1 <= args.limit <= 50:
        print("错误: --limit 必须在 1-50 之间", file=sys.stderr)
        sys.exit(1)

    # 获取数据
    print(f"正在获取 GitHub Trending 数据（since={args.since}, language={args.language or '全部'}）...")
    repos = fetch_trending_data(since=args.since, language=args.language, limit=args.limit)

    if not repos:
        print("错误: 未获取到任何仓库数据", file=sys.stderr)
        sys.exit(1)

    print(f"成功获取 {len(repos)} 个仓库")

    # 生成输出
    if args.format == "markdown":
        content = generate_markdown(repos, args.language, args.since, args.language_output)
    elif args.format == "csv":
        content = generate_csv(repos)
    else:  # json
        content = generate_json(repos, args.language, args.since)

    # 确定输出路径
    output_path = args.output or get_output_path(args.format, args.language, args.since)

    # 写入文件
    if atomic_write(output_path, content):
        print(f"报告已生成: {output_path}")
        # 同时输出到 stdout
        print("\n" + "=" * 60)
        print(content)
    else:
        print("错误: 写入文件失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
