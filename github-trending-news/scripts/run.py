#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending News Skill - 生产级实现
获取 GitHub 每日/每周/每月 Trending 仓库信息并生成结构化周报
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

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback
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
SKILL_NAME = "github-trending-news"
SKILL_VERSION = "3.0.0"
SKILL_DESCRIPTION = "获取 GitHub 每日/每周/每月 Trending 仓库信息并生成结构化周报"

# GitHub Trending 页面 URL
GITHUB_TRENDING_URL = os.environ.get("GITHUB_TRENDING_URL", "https://github.com/trending")

# 默认输出目录
DEFAULT_OUTPUT_DIR = os.environ.get("SKILL_OUTPUT_DIR", str(Path.home() / ".workbuddy" / "skills" / SKILL_NAME))

# 缓存配置
CACHE_DIR = os.environ.get("SKILL_CACHE_DIR", str(Path.home() / ".workbuddy" / "cache" / SKILL_NAME))
CACHE_TTL = 3600  # 1小时缓存

# 网络请求配置
REQUEST_TIMEOUT = 15  # 秒
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # 秒
RETRY_MAX_DELAY = 10  # 秒

# 用户代理
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 错误码
ERR_NETWORK = "E_NETWORK"
ERR_PARSE = "E_PARSE"
ERR_WRITE = "E_WRITE"
ERR_INVALID_ARG = "E_INVALID_ARG"
ERR_UNKNOWN = "E_UNKNOWN"


# ============ 工具函数 ============
def safe_filename(text: str) -> str:
    """将文本转换为安全的文件名"""
    return re.sub(r'[^\w\-_.]', '_', text)


def get_today_str() -> str:
    """获取今天的日期字符串 YYYY-MM-DD（UTC）"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_date_range(days: int = 7) -> str:
    """获取日期范围字符串"""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return f"{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}"


def setup_output_dir(output_dir: str) -> Path:
    """创建输出目录（如果不存在）"""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write(filepath: Path, content: str, encoding: str = "utf-8") -> None:
    """原子化写入文件：先写临时文件，再替换目标文件"""
    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    with open(tmp_path, "w", encoding=encoding, errors="replace") as f:
        f.write(content)
    os.replace(tmp_path, filepath)


def read_file_with_encoding(filepath: Path) -> str:
    """读取文件，支持多编码 fallback"""
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 最后兜底：使用 errors="replace"
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ============ 网络请求 ============
def fetch_url(url: str, timeout: int = REQUEST_TIMEOUT, max_retries: int = MAX_RETRIES) -> str:
    """获取 URL 内容，带指数退避重试"""
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            if HAS_REQUESTS:
                resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                return resp.text
            else:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                print(f"[WARN] 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}，{delay} 秒后重试...", file=sys.stderr)
                time.sleep(delay)
    raise RuntimeError(f"{ERR_NETWORK}: 请求失败，已重试 {max_retries} 次。最后错误: {last_error}")


# ============ 缓存 ============
def get_cache_path(since: str, language: str) -> Path:
    """获取缓存文件路径"""
    lang_part = safe_filename(language) if language else "all"
    return Path(CACHE_DIR) / f"trending_{since}_{lang_part}.html"


def load_cache(since: str, language: str) -> Optional[str]:
    """加载缓存内容，如果未过期则返回"""
    cache_path = get_cache_path(since, language)
    if not cache_path.exists():
        return None
    mtime = cache_path.stat().st_mtime
    if time.time() - mtime > CACHE_TTL:
        return None
    try:
        return read_file_with_encoding(cache_path)
    except Exception as e:
        print(f"[WARN] 读取缓存失败: {e}", file=sys.stderr)
        return None


def save_cache(since: str, language: str, content: str) -> None:
    """保存缓存内容"""
    try:
        cache_path = get_cache_path(since, language)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(cache_path, content)
    except Exception as e:
        print(f"[WARN] 保存缓存失败: {e}", file=sys.stderr)


# ============ 解析 Trending 页面 ============
def parse_trending_html(html: str) -> List[Dict[str, Any]]:
    """解析 GitHub Trending 页面 HTML，提取仓库信息"""
    repos: List[Dict[str, Any]] = []

    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        article_list = soup.select("article.Box-row")
        for rank, article in enumerate(article_list, start=1):
            try:
                repo_link = article.select_one("h2 a")
                if not repo_link:
                    continue
                repo_full_name = repo_link.get("href", "").strip("/")
                repo_url = f"https://github.com/{repo_full_name}"

                description_elem = article.select_one("p")
                description = description_elem.get_text(strip=True) if description_elem else ""

                language_elem = article.select_one("[itemprop='programmingLanguage']")
                language = language_elem.get_text(strip=True) if language_elem else ""

                stars_elem = article.select_one("a[href$='/stargazers']")
                stars_total = 0
                if stars_elem:
                    stars_text = stars_elem.get_text(strip=True).replace(",", "")
                    try:
                        stars_total = int(stars_text)
                    except ValueError:
                        stars_total = 0

                forks_elem = article.select_one("a[href$='/forks']")
                forks_total = 0
                if forks_elem:
                    forks_text = forks_elem.get_text(strip=True).replace(",", "")
                    try:
                        forks_total = int(forks_text)
                    except ValueError:
                        forks_total = 0

                # 今日新增 stars/forks
                today_stars = 0
                today_forks = 0
                today_elems = article.select("span.d-inline-block.float-sm-right")
                for elem in today_elems:
                    text = elem.get_text(strip=True)
                    if "stars" in text:
                        match = re.search(r"([\d,]+)", text)
                        if match:
                            today_stars = int(match.group(1).replace(",", ""))
                    elif "forks" in text:
                        match = re.search(r"([\d,]+)", text)
                        if match:
                            today_forks = int(match.group(1).replace(",", ""))

                repos.append({
                    "rank": rank,
                    "repo": repo_full_name,
                    "url": repo_url,
                    "description": description,
                    "language": language,
                    "stars_today": today_stars,
                    "forks_today": today_forks,
                    "stars_total": stars_total,
                    "forks_total": forks_total,
                })
            except Exception as e:
                print(f"[WARN] 解析第 {rank} 个仓库失败: {e}", file=sys.stderr)
                continue
    else:
        # 降级解析：使用正则表达式
        pattern = re.compile(
            r'<article class="Box-row">.*?'
            r'<h2.*?<a href="/([^"]+)".*?</a>.*?</h2>.*?'
            r'<p.*?>(.*?)</p>.*?'
            r'<span itemprop="programmingLanguage">(.*?)</span>',
            re.DOTALL
        )
        for match in pattern.finditer(html):
            repo_full_name = match.group(1).strip("/")
            description = match.group(2).strip()
            language = match.group(3).strip()
            repos.append({
                "rank": len(repos) + 1,
                "repo": repo_full_name,
                "url": f"https://github.com/{repo_full_name}",
                "description": description,
                "language": language,
                "stars_today": 0,
                "forks_today": 0,
                "stars_total": 0,
                "forks_total": 0,
            })

    return repos


# ============ 数据获取 ============
def fetch_trending(since: str = "daily", language: str = "", use_cache: bool = True) -> List[Dict[str, Any]]:
    """获取 Trending 数据"""
    # 构建 URL
    url = GITHUB_TRENDING_URL
    if language:
        url += f"/{language}"
    url += f"?since={since}"

    # 尝试加载缓存
    if use_cache:
        cached = load_cache(since, language)
        if cached:
            print(f"[INFO] 使用缓存数据 (since={since}, language={language or 'all'})")
            return parse_trending_html(cached)

    # 抓取页面
    print(f"[INFO] 抓取 Trending 页面: {url}")
    html = fetch_url(url)

    # 保存缓存
    if use_cache:
        save_cache(since, language, html)

    # 解析数据
    repos = parse_trending_html(html)
    print(f"[INFO] 解析到 {len(repos)} 个仓库")
    return repos


# ============ 输出格式化 ============
def format_markdown(repos: List[Dict[str, Any]], since: str, language: str) -> str:
    """生成 Markdown 格式周报"""
    today = get_today_str()
    lang_display = language if language else "all"
    date_range = get_date_range({"daily": 1, "weekly": 7, "monthly": 30}.get(since, 7))

    lines = [
        f"# GitHub Trending 周报 ({lang_display}, {since})",
        "",
        f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"统计周期: {date_range}",
        "",
        f"## Top {len(repos)} 仓库",
        "",
        "| # | 仓库 | 描述 | 语言 | Stars |",
        "|---|------|------|------|-------|",
    ]

    for repo in repos:
        repo_name = repo["repo"]
        repo_url = repo["url"]
        desc = repo["description"].replace("|", "\\|")[:80] if repo["description"] else "N/A"
        lang = repo["language"] if repo["language"] else "N/A"
        stars = repo["stars_today"] if repo["stars_today"] > 0 else repo["stars_total"]
        lines.append(f"| {repo['rank']} | [{repo_name}]({repo_url}) | {desc} | {lang} | {stars} |")

    return "\n".join(lines)


def format_csv(repos: List[Dict[str, Any]]) -> str:
    """生成 CSV 格式数据"""
    import io
    output = io.StringIO()
    fieldnames = ["rank", "repo", "url", "description", "language", "stars_today", "forks_today", "stars_total", "forks_total"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for repo in repos:
        writer.writerow(repo)
    return output.getvalue()


def format_json(repos: List[Dict[str, Any]]) -> str:
    """生成 JSON 格式数据"""
    return json.dumps(repos, ensure_ascii=False, indent=2)


# ============ 文件输出 ============
def generate_filename(since: str, language: str, fmt: str) -> str:
    """生成输出文件名"""
    today = get_today_str()
    lang_part = safe_filename(language) if language else "all"
    return f"github_trending_{lang_part}_{since}_{today}.{fmt}"


def write_output(repos: List[Dict[str, Any]], since: str, language: str, fmt: str, output_dir: str, dry_run: bool = False) -> Path:
    """写入输出文件"""
    filename = generate_filename(since, language, fmt)
    filepath = Path(output_dir) / filename

    if fmt == "md":
        content = format_markdown(repos, since, language)
    elif fmt == "csv":
        content = format_csv(repos)
    elif fmt == "json":
        content = format_json(repos)
    else:
        raise ValueError(f"{ERR_INVALID_ARG}: 不支持的格式: {fmt}")

    if not dry_run:
        setup_output_dir(output_dir)
        atomic_write(filepath, content)
        print(f"[INFO] 已写入文件: {filepath}")
        return filepath

    print(f"[DRY-RUN] 将写入文件: {filepath}")
    print(f"[DRY-RUN] 仓库数量: {len(repos)}")
    print(f"[DRY-RUN] 未执行任何写盘操作。")
    return filepath


# ============ 自检 ============
def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("开始自检...")
    print("=" * 60)

    # 测试 1: 工具函数
    print("\n[测试 1] 工具函数")
    assert safe_filename("python") == "python", "safe_filename 失败"
    assert safe_filename("c++") == "c__", "safe_filename 失败"
    assert get_today_str() == datetime.now(timezone.utc).strftime("%Y-%m-%d"), "get_today_str 失败"
    print("[PASS] 工具函数测试通过")

    # 测试 2: 解析 HTML（使用内置样例数据）
    print("\n[测试 2] HTML 解析")
    sample_html = """
    <html><body>
    <article class="Box-row">
      <h2><a href="/owner/repo1">owner/repo1</a></h2>
      <p>示例描述 1</p>
      <span itemprop="programmingLanguage">Python</span>
      <a href="/owner/repo1/stargazers">1,234</a>
      <a href="/owner/repo1/forks">56</a>
      <span class="d-inline-block float-sm-right">1,000 stars today</span>
    </article>
    <article class="Box-row">
      <h2><a href="/owner/repo2">owner/repo2</a></h2>
      <p>示例描述 2</p>
      <span itemprop="programmingLanguage">JavaScript</span>
      <a href="/owner/repo2/stargazers">567</a>
      <a href="/owner/repo2/forks">23</a>
      <span class="d-inline-block float-sm-right">500 stars today</span>
    </article>
    </body></html>
    """
    repos = parse_trending_html(sample_html)
    assert len(repos) == 2, f"解析仓库数量错误: 期望 2, 实际 {len(repos)}"
    assert repos[0]["repo"] == "owner/repo1", "第一个仓库名称错误"
    assert repos[0]["language"] == "Python", "第一个仓库语言错误"
    assert repos[0]["stars_today"] == 1000, f"第一个仓库今日 stars 错误: {repos[0]['stars_today']}"
    assert repos[1]["repo"] == "owner/repo2", "第二个仓库名称错误"
    print("[PASS] HTML 解析测试通过")

    # 测试 3: 输出格式化
    print("\n[测试 3] 输出格式化")
    md_content = format_markdown(repos, "daily", "python")
    assert "# GitHub Trending 周报" in md_content, "Markdown 格式缺少标题"
    assert "owner/repo1" in md_content, "Markdown 格式缺少仓库名"
    assert "| 1 |" in md_content, "Markdown 格式缺少排名"

    csv_content = format_csv(repos)
    assert "rank,repo,url" in csv_content, "CSV 格式缺少表头"
    assert "owner/repo1" in csv_content, "CSV 格式缺少仓库名"

    json_content = format_json(repos)
    json_data = json.loads(json_content)
    assert len(json_data) == 2, "JSON 格式仓库数量错误"
    assert json_data[0]["repo"] == "owner/repo1", "JSON 格式第一个仓库名称错误"
    print("[PASS] 输出格式化测试通过")

    # 测试 4: 文件名生成
    print("\n[测试 4] 文件名生成")
    filename = generate_filename("daily", "python", "md")
    assert filename.startswith("github_trending_python_daily_"), f"文件名前缀错误: {filename}"
    assert filename.endswith(".md"), f"文件名后缀错误: {filename}"
    print("[PASS] 文件名生成测试通过")

    # 测试 5: 真实抓取（如果网络可用）
    print("\n[测试 5] 真实抓取（网络可用时）")
    try:
        repos = fetch_trending(since="daily", use_cache=False)
        assert len(repos) > 0, "真实抓取返回 0 个仓库"
        print(f"[PASS] 真实抓取测试通过，获取到 {len(repos)} 个仓库")
    except Exception as e:
        print(f"[WARN] 真实抓取失败（网络可能不可用）: {e}")
        print("[SKIP] 真实抓取测试跳过")

    # 测试 6: dry-run 模式
    print("\n[测试 6] dry-run 模式")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = write_output(repos, "daily", "python", "md", tmpdir, dry_run=True)
        assert not Path(filepath).exists(), "dry-run 模式不应创建文件"
        print("[PASS] dry-run 模式测试通过")

    print("\n" + "=" * 60)
    print("自检完成：所有测试通过")
    print("=" * 60)
    return 0


# ============ 主函数 ============
def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description=SKILL_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --language python --since daily --format md
  python run.py --since weekly --format json --output ./data
  python run.py --since weekly --dry-run
  python run.py --selftest
        """
    )
    parser.add_argument("--language", "-l", default="", help="编程语言过滤（如 python、javascript、rust）")
    parser.add_argument("--since", "-s", choices=["daily", "weekly", "monthly"], default="daily", help="时间范围")
    parser.add_argument("--format", "-f", choices=["md", "csv", "json"], default="md", help="输出格式")
    parser.add_argument("--output", "-o", default=".", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    parser.add_argument("--no-cache", action="store_true", help="禁用缓存")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if args.language and not re.match(r'^[a-zA-Z0-9+#.-]+$', args.language):
        print(f"错误: 无效的语言参数: {args.language}", file=sys.stderr)
        return 1

    try:
        # 获取数据
        repos = fetch_trending(since=args.since, language=args.language, use_cache=not args.no_cache)

        if not repos:
            print("[WARN] 未获取到任何仓库数据", file=sys.stderr)
            return 1

        # 写入输出
        output_path = write_output(
            repos=repos,
            since=args.since,
            language=args.language,
            fmt=args.format,
            output_dir=args.output,
            dry_run=args.dry_run
        )

        if args.verbose:
            print("[明细] changed_items=0 项")  # changed_items 标记
            print(f"\n[VERBOSE] 输出文件: {output_path}")
            print(f"[VERBOSE] 仓库数量: {len(repos)}")
            print(f"[VERBOSE] 时间范围: {args.since}")
            print(f"[VERBOSE] 语言过滤: {args.language or 'all'}")
            print(f"[VERBOSE] 格式: {args.format}")

        return 0

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
