#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub趋势周报 - 独立实现脚本

依据功能规格独立开发，不参考任何既有实现。
支持从 GitHub Trending 数据源抓取项目信息，生成结构化周报。
"""

import argparse
import json
import sys
import os
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "输入文件不存在",
    "E003": "文件格式不支持",
    "E004": "网络请求失败",
    "E005": "数据解析失败",
    "E006": "写入输出文件失败",
    "E007": "权限不足",
    "E008": "超时错误",
    "E009": "重试次数耗尽",
    "E010": "内部逻辑错误",
}

# 支持的语言列表（用于筛选）
SUPPORTED_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C",
    "PHP", "Ruby", "Swift", "Kotlin", "Shell", "HTML", "CSS", "Vue", "React",
]


class TrendingProject:
    """表示一个 GitHub Trending 项目"""
    
    def __init__(
        self,
        name: str = "",
        description: str = "",
        language: str = "",
        stars_total: int = 0,
        stars_today: int = 0,
        forks: int = 0,
        url: str = "",
        owner: str = "",
        repo: str = "",
    ):
        self.name = name
        self.description = description
        self.language = language
        self.stars_total = stars_total
        self.stars_today = stars_today
        self.forks = forks
        self.url = url
        self.owner = owner
        self.repo = repo
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "stars_total": self.stars_total,
            "stars_today": self.stars_today,
            "forks": self.forks,
            "url": self.url,
            "owner": self.owner,
            "repo": self.repo,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrendingProject":
        """从字典创建实例"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            language=data.get("language", ""),
            stars_total=data.get("stars_total", 0),
            stars_today=data.get("stars_today", 0),
            forks=data.get("forks", 0),
            url=data.get("url", ""),
            owner=data.get("owner", ""),
            repo=data.get("repo", ""),
        )


class TrendingFetcher:
    """负责抓取 GitHub Trending 数据"""
    
    TRENDING_URL = "https://github.com/trending"
    
    def __init__(self, language: str = "", since: str = "daily", timeout: int = 30):
        self.language = language
        self.since = since  # daily / weekly / monthly
        self.timeout = timeout
    
    def build_url(self) -> str:
        """构建请求 URL"""
        url = self.TRENDING_URL
        if self.language:
            url += f"/{self.language.lower()}"
        url += f"?since={self.since}"
        return url
    
    def fetch(self) -> List[TrendingProject]:
        """抓取 Trending 数据（网络请求）"""
        url = self.build_url()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                html = response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"E004: 网络请求失败 - {exc}")
        except Exception as exc:
            raise RuntimeError(f"E008: 超时或连接错误 - {exc}")
        
        # 解析 HTML
        projects = self._parse_html(html)
        return projects
    
    def _parse_html(self, html: str) -> List[TrendingProject]:
        """解析 HTML 页面提取项目信息"""
        projects: List[TrendingProject] = []
        
        # 简单的正则解析（不依赖第三方库）
        # 匹配每个项目卡片的基本模式
        article_pattern = re.compile(
            r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>',
            re.DOTALL | re.IGNORECASE,
        )
        
        articles = article_pattern.findall(html)
        
        for article in articles:
            project = self._parse_article(article)
            if project.name:  # 至少要有项目名
                projects.append(project)
        
        return projects
    
    def _parse_article(self, article: str) -> TrendingProject:
        """解析单个项目卡片"""
        project = TrendingProject()
        
        # 提取项目名（包含 owner/repo）
        name_match = re.search(
            r'href="/[^"]*?([^/"]+)/([^/"]+)"[^>]*>\s*<span[^>]*>',
            article,
            re.DOTALL,
        )
        if name_match:
            project.owner = name_match.group(1)
            project.repo = name_match.group(2)
            project.name = f"{project.owner}/{project.repo}"
            project.url = f"https://github.com/{project.owner}/{project.repo}"
        
        # 提取描述
        desc_match = re.search(
            r'<p[^>]*class="col-9[^"]*"[^>]*>\s*(.*?)\s*</p>',
            article,
            re.DOTALL,
        )
        if desc_match:
            project.description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
        
        # 提取语言
        lang_match = re.search(
            r'<span[^>]*itemprop="programmingLanguage"[^>]*>\s*([^<]+?)\s*</span>',
            article,
        )
        if lang_match:
            project.language = lang_match.group(1).strip()
        
        # 提取 Star 总数
        stars_match = re.search(
            r'href="[^"]*/stargazers"[^>]*>\s*<svg[^>]*>.*?</svg>\s*([\d,]+)',
            article,
            re.DOTALL,
        )
        if stars_match:
            project.stars_total = self._parse_number(stars_match.group(1))
        
        # 提取今日 Star 数
        today_match = re.search(
            r'<span[^>]*class="d-inline-block float-sm-right"[^>]*>\s*([\d,]+)',
            article,
        )
        if today_match:
            project.stars_today = self._parse_number(today_match.group(1))
        
        # 提取 Fork 数
        fork_match = re.search(
            r'href="[^"]*/forks"[^>]*>\s*<svg[^>]*>.*?</svg>\s*([\d,]+)',
            article,
            re.DOTALL,
        )
        if fork_match:
            project.forks = self._parse_number(fork_match.group(1))
        
        return project
    
    @staticmethod
    def _parse_number(text: str) -> int:
        """解析数字字符串（支持逗号分隔）"""
        cleaned = text.replace(",", "").replace(" ", "").strip()
        try:
            return int(cleaned)
        except ValueError:
            # 处理 k/m 后缀
            if cleaned.endswith("k"):
                return int(float(cleaned[:-1]) * 1000)
            elif cleaned.endswith("m"):
                return int(float(cleaned[:-1]) * 1000000)
            return 0


class ReportGenerator:
    """生成各种格式的报告"""
    
    @staticmethod
    def generate_markdown(projects: List[TrendingProject], language: str = "", period: str = "") -> str:
        """生成 Markdown 格式报告"""
        lines = []
        lines.append("# GitHub 趋势项目周报")
        lines.append("")
        
        # 标题信息
        meta = []
        if language:
            meta.append(f"语言：{language}")
        if period:
            meta.append(f"周期：{period}")
        if meta:
            lines.append(f"> {' | '.join(meta)}")
            lines.append("")
        
        lines.append(f"共 {len(projects)} 个项目")
        lines.append("")
        
        if projects:
            lines.append("| 排名 | 项目 | 描述 | 语言 | Star 总数 | 今日 Star |")
            lines.append("|------|------|------|------|-----------|-----------|")
            for idx, proj in enumerate(projects, 1):
                desc = proj.description[:80] + "..." if len(proj.description) > 83 else proj.description
                desc = desc.replace("|", "\\|")
                lines.append(
                    f"| {idx} | [{proj.name}]({proj.url}) | {desc} | "
                    f"{proj.language} | {proj.stars_total:,} | +{proj.stars_today:,} |"
                )
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_text(projects: List[TrendingProject]) -> str:
        """生成纯文本格式报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("GitHub 趋势项目周报")
        lines.append("=" * 60)
        lines.append(f"共 {len(projects)} 个项目")
        lines.append("")
        
        for idx, proj in enumerate(projects, 1):
            lines.append(f"[{idx}] {proj.name}")
            lines.append(f"    描述: {proj.description or '无'}")
            lines.append(f"    语言: {proj.language or '未知'}")
            lines.append(f"    Star: {proj.stars_total:,} (+{proj.stars_today:,} 今日)")
            lines.append(f"    Fork: {proj.forks:,}")
            lines.append(f"    链接: {proj.url}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_json(projects: List[TrendingProject]) -> str:
        """生成 JSON 格式报告"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(projects),
            "projects": [p.to_dict() for p in projects],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


def load_input_file(filepath: str) -> List[Dict[str, Any]]:
    """
    加载输入文件（支持 JSON 格式）
    输入文件应为项目数据列表
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"E002: 输入文件不存在 - {filepath}")
    
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".json",):
        raise ValueError(f"E003: 文件格式不支持 - {ext}")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("E005: 输入数据应为列表格式")
        return data
    except json.JSONDecodeError as exc:
        raise ValueError(f"E005: JSON 解析失败 - {exc}")
    except PermissionError:
        raise PermissionError("E007: 读取权限不足")


def save_output(content: str, output_path: str) -> None:
    """保存输出文件"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
    except PermissionError:
        raise PermissionError("E007: 写入权限不足")
    except OSError as exc:
        raise IOError(f"E006: 写入失败 - {exc}")


def filter_projects(
    projects: List[TrendingProject],
    language: str = "",
    min_stars: int = 0,
    max_items: int = 50,
) -> List[TrendingProject]:
    """按条件过滤项目"""
    result = []
    for proj in projects:
        if language and proj.language.lower() != language.lower():
            continue
        if proj.stars_total < min_stars:
            continue
        result.append(proj)
        if len(result) >= max_items:
            break
    return result


def generate_report(
    projects: List[TrendingProject],
    output_format: str = "markdown",
    language: str = "",
    period: str = "",
) -> str:
    """根据指定格式生成报告"""
    generator = ReportGenerator()
    
    if output_format == "json":
        return generator.generate_json(projects)
    elif output_format == "text":
        return generator.generate_text(projects)
    else:  # markdown 默认
        return generator.generate_markdown(projects, language, period)


def run_selftest() -> bool:
    """
    内置自检功能
    使用硬编码样例数据验证核心逻辑，不依赖外部环境
    """
    print("开始自检...")
    
    # 硬编码测试数据
    test_data = [
        {
            "name": "facebook/react",
            "description": "A declarative, efficient, and flexible JavaScript library for building user interfaces.",
            "language": "JavaScript",
            "stars_total": 220000,
            "stars_today": 150,
            "forks": 45000,
            "url": "https://github.com/facebook/react",
            "owner": "facebook",
            "repo": "react",
        },
        {
            "name": "pytorch/pytorch",
            "description": "Tensors and Dynamic neural networks in Python with strong GPU acceleration",
            "language": "Python",
            "stars_total": 78000,
            "stars_today": 80,
            "forks": 21000,
            "url": "https://github.com/pytorch/pytorch",
            "owner": "pytorch",
            "repo": "pytorch",
        },
        {
            "name": "golang/go",
            "description": "The Go programming language",
            "language": "Go",
            "stars_total": 120000,
            "stars_today": 45,
            "forks": 17000,
            "url": "https://github.com/golang/go",
            "owner": "golang",
            "repo": "go",
        },
        {
            "name": "rust-lang/rust",
            "description": "Empowering everyone to build reliable and efficient software.",
            "language": "Rust",
            "stars_total": 95000,
            "stars_today": 60,
            "forks": 12000,
            "url": "https://github.com/rust-lang/rust",
            "owner": "rust-lang",
            "repo": "rust",
        },
        {
            "name": "microsoft/vscode",
            "description": "Visual Studio Code",
            "language": "TypeScript",
            "stars_total": 160000,
            "stars_today": 100,
            "forks": 28000,
            "url": "https://github.com/microsoft/vscode",
            "owner": "microsoft",
            "repo": "vscode",
        },
    ]
    
    # 转换为对象
    projects = [TrendingProject.from_dict(item) for item in test_data]
    
    # 测试 1: 解析功能
    assert len(projects) == 5, f"E010: 项目数量不正确 - {len(projects)}"
    assert all(p.name for p in projects), "E010: 项目名缺失"
    assert all(p.url for p in projects), "E010: 项目链接缺失"
    print("  [PASS] 数据解析")
    
    # 测试 2: 过滤功能
    python_projects = filter_projects(projects, language="Python")
    assert len(python_projects) == 1, f"E010: Python 过滤失败 - {len(python_projects)}"
    assert python_projects[0].name == "pytorch/pytorch"
    print("  [PASS] 语言过滤")
    
    # 测试 3: Star 过滤
    big_projects = filter_projects(projects, min_stars=100000)
    assert len(big_projects) == 3, f"E010: Star 过滤失败 - {len(big_projects)}"
    print("  [PASS] Star 过滤")
    
    # 测试 4: Markdown 生成
    md_report = ReportGenerator.generate_markdown(projects)
    assert "GitHub 趋势项目周报" in md_report, "E010: Markdown 报告缺少标题"
    assert "| 排名 |" in md_report, "E010: Markdown 报告缺少表格头"
    assert "facebook/react" in md_report, "E010: Markdown 报告缺少项目数据"
    print("  [PASS] Markdown 生成")
    
    # 测试 5: JSON 生成
    json_report = ReportGenerator.generate_json(projects)
    parsed = json.loads(json_report)
    assert parsed["total_count"] == 5, "E010: JSON 报告数量错误"
    assert len(parsed["projects"]) == 5, "E010: JSON 项目列表错误"
    print("  [PASS] JSON 生成")
    
    # 测试 6: 文本生成
    text_report = ReportGenerator.generate_text(projects)
    assert "GitHub 趋势项目周报" in text_report, "E010: 文本报告缺少标题"
    assert "rust-lang/rust" in text_report, "E010: 文本报告缺少项目数据"
    print("  [PASS] 文本生成")
    
    # 测试 7: 数字解析
    assert TrendingFetcher._parse_number("1,234") == 1234, "E010: 数字解析失败"
    assert TrendingFetcher._parse_number("12k") == 12000, "E010: k 后缀解析失败"
    assert TrendingFetcher._parse_number("1.5m") == 1500000, "E010: m 后缀解析失败"
    print("  [PASS] 数字解析")
    
    # 测试 8: 宽松阈值验证
    # 验证 Star 数量级合理（大于 0）
    for proj in projects:
        assert proj.stars_total > 0, f"E010: {proj.name} Star 数异常"
        assert proj.stars_today >= 0, f"E010: {proj.name} 今日 Star 异常"
        assert proj.forks > 0, f"E010: {proj.name} Fork 数异常"
    print("  [PASS] 数据合理性")
    
    print("自检全部通过！")
    return True


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="GitHub 趋势周报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --selftest
  python main.py --fetch --language Python --since weekly --format markdown
  python main.py --input data.json --output report.md --format markdown
        """,
    )
    
    # 自检参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    
    # 抓取模式参数
    parser.add_argument("--fetch", action="store_true", help="从 GitHub 抓取 Trending 数据")
    parser.add_argument("--language", type=str, default="", help="筛选语言（如 Python）")
    parser.add_argument("--since", type=str, default="daily", choices=["daily", "weekly", "monthly"], help="时间范围")
    
    # 文件模式参数
    parser.add_argument("--input", type=str, help="输入 JSON 文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    
    # 通用参数
    parser.add_argument("--format", type=str, default="markdown", choices=["markdown", "text", "json"], help="输出格式")
    parser.add_argument("--min-stars", type=int, default=0, help="最小 Star 数过滤")
    parser.add_argument("--max-items", type=int, default=50, help="最大项目数")
    parser.add_argument("--timeout", type=int, default=30, help="网络请求超时（秒）")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as exc:
            print(f"自检失败: {exc}")
            return 1
        except Exception as exc:
            print(f"自检异常: {exc}")
            return 1
    
    # 处理模式
    try:
        projects: List[TrendingProject] = []
        
        if args.fetch:
            # 网络抓取模式
            print(f"正在从 GitHub Trending 抓取数据（语言: {args.language or '全部'}，周期: {args.since}）...")
            fetcher = TrendingFetcher(language=args.language, since=args.since, timeout=args.timeout)
            projects = fetcher.fetch()
            print(f"抓取到 {len(projects)} 个项目")
            
            # 过滤
            projects = filter_projects(
                projects,
                language=args.language,
                min_stars=args.min_stars,
                max_items=args.max_items,
            )
            print(f"过滤后 {len(projects)} 个项目")
            
            # 生成报告
            report = generate_report(
                projects,
                output_format=args.format,
                language=args.language,
                period=args.since,
            )
            
            # 输出
            if args.output:
                save_output(report, args.output)
                print(f"报告已保存至: {args.output}")
            else:
                print(report)
        
        elif args.input:
            # 文件处理模式
            print(f"正在处理输入文件: {args.input}")
            data = load_input_file(args.input)
            
            # 转换为项目对象
            projects = [TrendingProject.from_dict(item) for item in data]
            print(f"加载 {len(projects)} 个项目")
            
            # 过滤
            projects = filter_projects(
                projects,
                language=args.language,
                min_stars=args.min_stars,
                max_items=args.max_items,
            )
            print(f"过滤后 {len(projects)} 个项目")
            
            # 生成报告
            report = generate_report(
                projects,
                output_format=args.format,
                language=args.language,
                period="custom",
            )
            
            # 输出
            if args.output:
                save_output(report, args.output)
                print(f"报告已保存至: {args.output}")
            else:
                # 默认输出到输入文件同目录
                input_dir = os.path.dirname(os.path.abspath(args.input))
                base_name = os.path.splitext(os.path.basename(args.input))[0]
                ext_map = {"markdown": ".md", "text": ".txt", "json": ".json"}
                output_path = os.path.join(input_dir, f"{base_name}_out{ext_map.get(args.format, '.md')}")
                save_output(report, output_path)
                print(f"报告已保存至: {output_path}")
        
        else:
            print("E001: 请指定 --fetch 或 --input 参数", file=sys.stderr)
            parser.print_help()
            return 1
        
        # 控制台摘要
        print(f"\n处理完成: 共 {len(projects)} 个项目")
        return 0
        
    except FileNotFoundError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: 未预期错误 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
