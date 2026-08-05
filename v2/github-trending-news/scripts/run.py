#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending 周报生成器 - 单文件实现

功能：
1. 抓取 GitHub Trending 页面公开数据（无需 API Token）
2. 按编程语言、时间范围过滤
3. 生成 Markdown 周报、CSV 表格、JSON 结构化数据
4. 内置离线演示数据（无网络时可用 --demo 模式）

用法示例：
  python run.py --since daily --language python --output report.md
  python run.py --since weekly --format json --output data.json
  python run.py --demo --since monthly --format csv --output demo.csv
  python run.py --selftest
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# ============ 内置演示数据（离线可用） ============
DEMO_REPOS = [
    {
        "name": "openai/gpt-4o-mini",
        "description": "OpenAI's new compact model with vision capabilities",
        "language": "Python",
        "stars_today": 1250,
        "total_stars": 45200,
        "forks": 8900,
        "url": "https://github.com/openai/gpt-4o-mini"
    },
    {
        "name": "microsoft/autogen",
        "description": "A framework for building multi-agent AI systems",
        "language": "Python",
        "stars_today": 890,
        "total_stars": 23400,
        "forks": 3100,
        "url": "https://github.com/microsoft/autogen"
    },
    {
        "name": "langchain-ai/langchain",
        "description": "Building applications with LLMs through composability",
        "language": "Python",
        "stars_today": 760,
        "total_stars": 78900,
        "forks": 12400,
        "url": "https://github.com/langchain-ai/langchain"
    },
    {
        "name": "rust-lang/rustlings",
        "description": "Small exercises to get you used to reading and writing Rust code",
        "language": "Rust",
        "stars_today": 340,
        "total_stars": 45600,
        "forks": 6800,
        "url": "https://github.com/rust-lang/rustlings"
    },
    {
        "name": "tauri-apps/tauri",
        "description": "Build smaller, faster, and more secure desktop applications",
        "language": "Rust",
        "stars_today": 280,
        "total_stars": 67800,
        "forks": 5200,
        "url": "https://github.com/tauri-apps/tauri"
    },
    {
        "name": "vercel/next.js",
        "description": "The React framework for production",
        "language": "JavaScript",
        "stars_today": 520,
        "total_stars": 112000,
        "forks": 24500,
        "url": "https://github.com/vercel/next.js"
    },
    {
        "name": "facebook/react",
        "description": "The library for web and native user interfaces",
        "language": "JavaScript",
        "stars_today": 430,
        "total_stars": 213000,
        "forks": 44500,
        "url": "https://github.com/facebook/react"
    },
    {
        "name": "golang/go",
        "description": "The Go programming language",
        "language": "Go",
        "stars_today": 310,
        "total_stars": 115000,
        "forks": 16800,
        "url": "https://github.com/golang/go"
    }
]

# 语言别名映射
LANGUAGE_ALIASES = {
    "py": "python",
    "python": "python",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "go": "go",
    "golang": "go",
    "rust": "rust",
    "rs": "rust",
    "java": "java",
    "c": "c",
    "c++": "cpp",
    "cpp": "cpp",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin"
}

# 时间范围映射
SINCE_MAP = {
    "daily": "今日",
    "weekly": "本周",
    "monthly": "本月"
}


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="GitHub Trending 周报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--input", "-i", help="输入文件（预留，当前版本不使用）")
    parser.add_argument("--output", "-o", default="trending_report.md",
                        help="输出文件路径（默认: trending_report.md）")
    parser.add_argument("--language", "-l", default=None,
                        help="过滤语言，如 python/javascript/go（默认: 全部）")
    parser.add_argument("--since", "-s", default="daily",
                        choices=["daily", "weekly", "monthly"],
                        help="时间范围: daily/weekly/monthly（默认: daily）")
    parser.add_argument("--format", "-f", default="markdown",
                        choices=["markdown", "csv", "json"],
                        help="输出格式: markdown/csv/json（默认: markdown）")
    parser.add_argument("--demo", action="store_true",
                        help="使用内置演示数据（离线模式）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行自检")
    return parser.parse_args()


def fetch_trending(language=None, since="daily"):
    """
    从 GitHub Trending 页面抓取数据
    返回: list[dict] 仓库列表
    """
    if requests is None:
        raise RuntimeError("需要 requests 库。请运行: pip install requests")

    url = "https://github.com/trending"
    if language:
        url += f"/{language}"
    url += f"?since={since}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml"
    }

    print(f"正在抓取: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"网络请求失败: {e}")

    # 解析 HTML（简化版，使用正则提取关键信息）
    html = resp.text
    repos = []

    # 匹配仓库条目
    pattern = re.compile(
        r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"[^>]*>([^<]+)</a>',
        re.IGNORECASE
    )
    matches = pattern.findall(html)

    for path, name in matches[:20]:  # 最多取 20 个
        repo = {
            "name": path.strip(),
            "description": "",
            "language": language or "Unknown",
            "stars_today": 0,
            "total_stars": 0,
            "forks": 0,
            "url": f"https://github.com/{path.strip()}"
        }
        repos.append(repo)

    if not repos:
        raise RuntimeError("未能从页面解析到仓库数据，请检查网络或稍后重试")

    # 提取描述和星标数（简化处理）
    desc_pattern = re.compile(r'<p[^>]*class="col-9[^"]*"[^>]*>([^<]+)</p>')
    descs = desc_pattern.findall(html)
    for i, repo in enumerate(repos):
        if i < len(descs):
            repo["description"] = descs[i].strip()

    # 提取星标数
    star_pattern = re.compile(r'<span[^>]*class="d-inline-block float-sm-right">\s*([\d,]+)\s*</span>')
    stars = star_pattern.findall(html)
    for i, repo in enumerate(repos):
        if i < len(stars):
            repo["stars_today"] = int(stars[i].replace(",", ""))

    return repos


def filter_by_language(repos, language):
    """按语言过滤仓库列表"""
    if not language:
        return repos
    lang = LANGUAGE_ALIASES.get(language.lower(), language.lower())
    return [r for r in repos if r.get("language", "").lower() == lang]


def generate_markdown(repos, since, language):
    """生成 Markdown 格式周报"""
    lines = []
    lines.append("# GitHub Trending 周报\n")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**时间范围**: {SINCE_MAP.get(since, since)}")
    lines.append(f"**语言过滤**: {language or '全部'}\n")
    lines.append("---\n")
    lines.append("## 热门仓库排行\n")

    for i, repo in enumerate(repos, 1):
        lines.append(f"### {i}. [{repo['name']}]({repo['url']})")
        lines.append(f"- **描述**: {repo.get('description', '暂无描述')}")
        lines.append(f"- **语言**: {repo.get('language', 'Unknown')}")
        lines.append(f"- **今日星标**: ⭐ {repo.get('stars_today', 0):,}")
        lines.append(f"- **总星标**: ⭐ {repo.get('total_stars', 0):,}")
        lines.append(f"- **Fork 数**: {repo.get('forks', 0):,}")
        lines.append("")

    lines.append("---\n")
    lines.append("*本报告由 GitHub Trending 周报生成器自动生成*\n")
    return "\n".join(lines)


def generate_csv(repos, output_path):
    """生成 CSV 格式数据"""
    if not repos:
        raise ValueError("没有可导出的数据")

    fieldnames = ["name", "description", "language", "stars_today",
                  "total_stars", "forks", "url"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(repos)
    return f"CSV 已保存到 {output_path}"


def generate_json(repos, output_path, since, language):
    """生成 JSON 格式数据"""
    data = {
        "generated_at": datetime.now().isoformat(),
        "since": since,
        "language": language,
        "total_count": len(repos),
        "repositories": repos
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return f"JSON 已保存到 {output_path}"


def selftest():
    """自检函数：验证核心功能"""
    print("=" * 50)
    print("运行自检...")
    print("=" * 50)

    # 测试语言别名映射
    assert LANGUAGE_ALIASES["py"] == "python", "语言别名映射失败"
    assert LANGUAGE_ALIASES["js"] == "javascript", "语言别名映射失败"
    print("[PASS] 语言别名映射")

    # 测试时间范围映射
    assert SINCE_MAP["daily"] == "今日", "时间范围映射失败"
    assert SINCE_MAP["weekly"] == "本周", "时间范围映射失败"
    print("[PASS] 时间范围映射")

    # 测试数据过滤
    filtered = filter_by_language(DEMO_REPOS, "python")
    assert len(filtered) == 3, f"Python 过滤失败，期望 3 个，实际 {len(filtered)}"
    assert all(r["language"] == "Python" for r in filtered), "过滤结果语言不匹配"
    print("[PASS] 语言过滤功能")

    # 测试 Markdown 生成
    md = generate_markdown(DEMO_REPOS[:3], "daily", "python")
    assert "# GitHub Trending" in md, "Markdown 标题缺失"
    assert "热门仓库排行" in md, "Markdown 章节缺失"
    print("[PASS] Markdown 生成")

    # 测试 CSV 生成
    csv_path = Path("_selftest.csv")
    try:
        generate_csv(DEMO_REPOS[:2], csv_path)
        assert csv_path.exists(), "CSV 文件未创建"
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "name" in content, "CSV 缺少表头"
        print("[PASS] CSV 生成")
    finally:
        if csv_path.exists():
            csv_path.unlink()

    # 测试 JSON 生成
    json_path = Path("_selftest.json")
    try:
        generate_json(DEMO_REPOS[:2], json_path, "daily", "python")
        assert json_path.exists(), "JSON 文件未创建"
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_count"] == 2, "JSON 数据数量错误"
        print("[PASS] JSON 生成")
    finally:
        if json_path.exists():
            json_path.unlink()

    # 测试异常处理
    try:
        generate_csv([], "test.csv")
        assert False, "空数据应抛出异常"
    except ValueError:
        print("[PASS] 空数据异常处理")

    print("=" * 50)
    print("所有自检通过！")
    print("=" * 50)
    return 0


def main():
    """主入口函数"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 获取数据
    try:
        if args.demo:
            print("使用内置演示数据（离线模式）")
            repos = DEMO_REPOS.copy()
            # 模拟时间过滤
            if args.since == "daily":
                repos = [r for r in repos if r["stars_today"] > 300]
            elif args.since == "weekly":
                repos = [r for r in repos if r["stars_today"] > 200]
            elif args.since == "monthly":
                repos = [r for r in repos if r["stars_today"] > 100]
        else:
            repos = fetch_trending(args.language, args.since)
            # 等待避免限流
            time.sleep(1)

        # 语言过滤
        repos = filter_by_language(repos, args.language)

        if not repos:
            print(f"警告: 没有找到符合条件的仓库（语言={args.language or '全部'}）")
            return 1

        # 按今日星标排序
        repos.sort(key=lambda x: x.get("stars_today", 0), reverse=True)

        # 生成输出
        if args.format == "markdown":
            content = generate_markdown(repos, args.since, args.language)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Markdown 周报已保存到: {args.output}")
            print(f"共 {len(repos)} 个仓库")

        elif args.format == "csv":
            msg = generate_csv(repos, args.output)
            print(msg)

        elif args.format == "json":
            msg = generate_json(repos, args.output, args.since, args.language)
            print(msg)

        return 0

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"参数错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
