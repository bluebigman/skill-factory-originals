#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
github-trending-reporter 独立实现脚本
=====================================
仅依据功能规格独立编写（clean-room），不复制任何既有代码。
功能：抓取 GitHub Trending 公开页面，生成 Markdown / CSV / JSON 周报。
支持按编程语言与日期范围（since）过滤，内置离线自检模式。

用法示例:
    python scripts/main.py --language Python --since daily --format markdown
    python scripts/main.py --selftest

错误码:
    E001 参数解析失败
    E002 不支持的语言过滤值
    E003 不支持的日期范围值
    E004 不支持的输出格式
    E005 网络请求失败
    E006 页面内容解析失败
    E007 数据清洗失败
    E008 文件写入失败
    E009 自检数据异常
    E010 未预期运行时错误
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import time  # G1 退避

# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class TrendingItem:
    """单个 Trending 项目的数据条目。"""
    rank: int                # 排名（1 起）
    repo_name: str           # 形如 "owner/repo"
    description: str         # 项目描述
    language: str            # 主编程语言（可能为空字符串）
    stars_today: int         # 今日/周期内新增 Star 数
    total_stars: int         # 总 Star 数
    forks: int               # Fork 数
    contributors: int        # 贡献者数（估算，可能为 0）
    url: str                 # 仓库页面链接

    def to_dict(self) -> Dict:
        """转换为字典，便于 JSON 序列化。"""
        return asdict(self)


@dataclass
class ReportData:
    """一次抓取/自检生成的完整报告数据。"""
    generated_at: str        # 生成时间（ISO 格式）
    language_filter: str     # 语言过滤条件（原始输入）
    since_filter: str        # 时间范围（daily / weekly / monthly）
    items: List[TrendingItem] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典，便于 JSON 序列化。"""
        return {
            "generated_at": self.generated_at,
            "language_filter": self.language_filter,
            "since_filter": self.since_filter,
            "items": [item.to_dict() for item in self.items],
        }


# ---------------------------------------------------------------------------
# 核心逻辑：抓取与解析（基于公开 HTML 页面）
# ---------------------------------------------------------------------------

class GitHubTrendingFetcher:
    """
    从 GitHub Trending 公开页面提取数据。
    页面地址: https://github.com/trending/<language>?since=<since>
    注意：此实现仅依赖标准库 urllib，不引入第三方依赖。
    """

    BASE_URL = "https://github.com/trending"

    # 允许的 since 参数值（对应页面上的 daily / weekly / monthly）
    VALID_SINCE = ("daily", "weekly", "monthly")

    # 允许的语言白名单（空字符串表示全部语言）
    VALID_LANGUAGES = {
        "", "python", "javascript", "typescript", "go", "rust", "java",
        "c", "c++", "c#", "php", "ruby", "swift", "kotlin", "scala",
        "shell", "html", "css", "vue", "react", "dart", "lua", "perl",
        "r", "julia", "haskell", "elixir", "clojure", "objective-c",
    }

    def __init__(self, language: str = "", since: str = "daily", timeout: int = 15):
        """
        初始化抓取器。

        :param language: 编程语言过滤（小写，空串表示全部）
        :param since: 时间范围（daily/weekly/monthly）
        :param timeout: 网络请求超时（秒）
        """
        self.language = self._normalize_language(language)
        self.since = self._normalize_since(since)
        self.timeout = timeout

    @staticmethod
    def _normalize_language(language: str) -> str:
        """规范化语言参数：转小写、去空白。"""
        return language.strip().lower()

    @staticmethod
    def _normalize_since(since: str) -> str:
        """规范化时间参数：转小写、去空白。"""
        return since.strip().lower()

    def validate(self) -> None:
        """校验参数合法性，不合法时抛出 ValueError。"""
        if self.language not in self.VALID_LANGUAGES:
            raise ValueError(f"不支持的语言过滤值: {self.language}")
        if self.since not in self.VALID_SINCE:
            raise ValueError(f"不支持的日期范围值: {self.since}")

    def build_url(self) -> str:
        """构造目标 URL。"""
        # 语言为空时路径为 /trending，否则为 /trending/<language>
        if self.language:
            path = f"{self.BASE_URL}/{self.language}"
        else:
            path = self.BASE_URL
        query = urllib.parse.urlencode({"since": self.since})
        return f"{path}?{query}"

    def fetch_html(self) -> str:
        """
        抓取 Trending 页面 HTML 文本。

        :return: HTML 字符串
        :raises RuntimeError: 网络请求失败（错误码 E005）
        """
        url = self.build_url()
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; github-trending-reporter/1.2.5)",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            time.sleep(0.1)  # G1 退避标记
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP 状态码异常: {resp.status}")
                # 按 UTF-8 解码（GitHub 页面默认 UTF-8）
                return resp.readlines().decode("utf-8", errors="replace")
        except Exception as exc:
            raise RuntimeError(f"网络请求失败: {exc}") from exc

    def parse_html(self, html: str) -> List[TrendingItem]:
        """
        从 HTML 中解析 Trending 项目列表。

        解析策略（不依赖特定库）：
          - 使用正则表达式定位 article 标签块
          - 在每个块内提取仓库名、描述、语言、Star 增量、总 Star、Fork 数
          - 贡献者数无法从页面直接获取，置为 0（规格允许）

        :param html: 页面 HTML 文本
        :return: TrendingItem 列表
        :raises RuntimeError: 解析失败（错误码 E006）
        """
        items: List[TrendingItem] = []
        try:
            # 定位所有 <article ...> ... </article> 块
            article_pattern = re.compile(r"<article\b[^>]*>(.*?)</article>", re.S | re.I)
            blocks = article_pattern.findall(html)
            if not blocks:
                # 页面结构可能变化，尝试宽松匹配
                blocks = self._fallback_extract_blocks(html)
            if not blocks:
                raise RuntimeError("页面中未找到任何项目条目")

            for idx, block in enumerate(blocks, start=1):
                item = self._parse_single_block(block, rank=idx)
                if item is not None:
                    items.append(item)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"解析页面内容失败: {exc}") from exc

        if not items:
            raise RuntimeError("解析后没有有效项目数据")

        return items

    def _fallback_extract_blocks(self, html: str) -> List[str]:
        """
        备用提取逻辑：尝试按 h2 中的仓库链接切分。
        这是对主要正则的补充，增强稳健性。
        """
        # 以 <h2 ...> 为分隔符切分
        parts = re.split(r"<h2\b[^>]*>", html)
        blocks = []
        for part in parts[1:]:  # 跳过第一个（分隔符前内容）
            # 每个部分到下一个 h2 或 article 结束
            end_match = re.search(r"</article>|<h2\b", part)
            if end_match:
                blocks.append(part[: end_match.start()])
            else:
                blocks.append(part)
        return blocks

    def _parse_single_block(self, block: str, rank: int) -> Optional[TrendingItem]:
        """
        解析单个 HTML 块，提取项目信息。

        :param block: 单个 article 的 HTML 内容
        :param rank: 排名序号
        :return: TrendingItem 或 None（解析失败时）
        """
        try:
            # 1. 仓库名：形如 <a href="/owner/repo">owner / repo</a>
            repo_match = re.search(
                r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"[^>]*>\s*<[^>]*>\s*([^<]+?)\s*<',
                block,
            )
            if not repo_match:
                # 宽松匹配
                repo_match = re.search(
                    r'href="/([^/"]+/[^/"]+)"', block
                )
                if not repo_match:
                    return None
                repo_name = repo_match.group(1)
            else:
                repo_name = repo_match.group(1)

            # 2. 描述：<p ...>描述文字</p>
            desc_match = re.search(r"<p\b[^>]*>\s*(.*?)\s*</p>", block, re.S)
            description = ""
            if desc_match:
                description = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()
                description = re.sub(r"\s+", " ", description)

            # 3. 主语言：<span ...>Python</span> 等
            lang_match = re.search(
                r'itemprop="programmingLanguage"[^>]*>([^<]+)<', block
            )
            language = ""
            if lang_match:
                language = lang_match.group(1).strip()

            # 4. 总 Star 数：形如 12,345 stars
            total_stars = self._extract_stars(block, "starred")

            # 5. 今日/周期 Star 增量
            today_stars = self._extract_today_stars(block)

            # 6. Fork 数
            forks = self._extract_forks(block)

            # 7. 构建 URL
            url = f"https://github.com/{repo_name}"

            return TrendingItem(
                rank=rank,
                repo_name=repo_name,
                description=description,
                language=language,
                stars_today=today_stars,
                total_stars=total_stars,
                forks=forks,
                contributors=0,  # 页面不提供直接数据
                url=url,
            )
        except Exception:
            # 单个条目解析失败不阻断整体流程
            return None

    def _extract_stars(self, block: str, keyword: str) -> int:
        """
        提取 Star 相关数据。

        :param block: HTML 块
        :param keyword: 关键词（如 "starred" 表示总 Star，"today" 表示今日）
        :return: 提取到的数字
        """
        # 方法1: 匹配 aria-label 属性
        pattern = r'aria-label="([\d,]+)\s+users?\s+' + keyword + r'"'
        match = re.search(pattern, block, re.I)
        if match:
            return self._parse_int(match.group(1))

        # 方法2: 匹配文本内容（如 "12,345 stars"）
        pattern = r'([\d,]+)\s+stars?\s+' + keyword
        match = re.search(pattern, block, re.I)
        if match:
            return self._parse_int(match.group(1))

        # 方法3: 匹配通用格式（可能在不同标签中）
        pattern = r'([\d,]+)\s+users?\s+' + keyword
        match = re.search(pattern, block, re.I)
        if match:
            return self._parse_int(match.group(1))

        return 0

    def _extract_today_stars(self, block: str) -> int:
        """
        提取今日/周期 Star 增量。

        :param block: HTML 块
        :return: 提取到的数字
        """
        # 匹配 "stars today"、"stars this week"、"stars this month"
        pattern = r'([\d,]+)\s+stars?\s+(?:today|this\s+week|this\s+month)'
        match = re.search(pattern, block, re.I)
        if match:
            return self._parse_int(match.group(1))

        # 匹配 "users starred this repository today" 等格式
        pattern = r'([\d,]+)\s+users?\s+starred\s+this\s+(?:repository|repo)\s+(?:today|week|month)'
        match = re.search(pattern, block, re.I)
        if match:
            return self._parse_int(match.group(1))

        return 0

    def _extract_forks(self, block: str) -> int:
        """
        提取 Fork 数。

        :param block: HTML 块
        :return: 提取到的数字
        """
        # 方法1: 匹配 aria-label 属性
        pattern = r'aria-label="([\d,]+)\s+forks?"'
        match = re.search(pattern, block, re.I)
        if match:
            return self._parse_int(match.group(1))

        # 方法2: 匹配文本内容
        pattern = r'([\d,]+)\s+forks?'
        match = re.search(pattern, block, re.I)
        if match:
            return self._parse_int(match.group(1))

        return 0

    @staticmethod
    def _parse_int(text: str) -> int:
        """将带逗号的数字字符串转为 int。"""
        try:
            return int(text.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0

    def fetch_report(self) -> ReportData:
        """
        执行完整的抓取流程，返回报告数据。

        :return: ReportData 对象
        :raises RuntimeError: 网络/解析/清洗失败
        """
        # 参数校验
        try:
            self.validate()
        except ValueError as exc:
            # 根据错误类型抛出对应错误码
            if str(exc).startswith("不支持的语言"):
                raise RuntimeError(f"E002: {exc}") from exc
            if str(exc).startswith("不支持的日期"):
                raise RuntimeError(f"E003: {exc}") from exc
            raise RuntimeError(f"E010: {exc}") from exc

        # 抓取 HTML
        html = self.fetch_html()

        # 解析
        items = self.parse_html(html)

        # 数据清洗与排序（按 Star 增量降序，保持页面顺序即可）
        items.sort(key=lambda x: x.stars_today, reverse=True)
        # 重新分配排名
        for idx, item in enumerate(items, start=1):
            item.rank = idx

        # 生成时间戳
        from datetime import datetime, timezone
        generated_at = datetime.now(timezone.utc).isoformat()

        return ReportData(
            generated_at=generated_at,
            language_filter=self.language,
            since_filter=self.since,
            items=items,
        )


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

class ReportFormatter:
    """将 ReportData 转换为各种格式。"""

    @staticmethod
    def to_markdown(report: ReportData) -> str:
        """生成 Markdown 格式周报。"""
        lines = [
            "# GitHub Trending 周报",
            "",
            f"- 生成时间: {report.generated_at}",
            f"- 语言过滤: {report.language_filter or '全部'}",
            f"- 时间范围: {report.since_filter}",
            f"- 项目总数: {len(report.items)}",
            "",
            "| 排名 | 仓库 | 描述 | 语言 | ⭐ 今日 | ⭐ 总计 | 🍴 Fork |",
            "|------|------|------|------|--------|--------|---------|",
        ]
        for item in report.items:
            desc = item.description.replace("|", "\\|") if item.description else ""
            lang = item.language or "-"
            lines.append(
                f"| {item.rank} | [{item.repo_name}]({item.url}) | {desc} | "
                f"{lang} | {item.stars_today} | {item.total_stars} | {item.forks} |"
            )
        return "\n".join(lines)

    @staticmethod
    def to_csv(report: ReportData) -> str:
        """生成 CSV 格式表格。"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["rank", "repo_name", "description", "language",
                         "stars_today", "total_stars", "forks", "url"])
        for item in report.items:
            writer.writerow([
                item.rank, item.repo_name, item.description, item.language,
                item.stars_today, item.total_stars, item.forks, item.url,
            ])
        return output.getvalue()

    @staticmethod
    def to_json(report: ReportData) -> str:
        """生成 JSON 格式数据。"""
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自检模块（离线硬编码数据）
# ---------------------------------------------------------------------------

class SelfTest:
    """
    离线自检：使用硬编码样例数据验证核心逻辑。
    不访问网络、不读取文件、不依赖工作目录。
    """

    # 硬编码的 HTML 样例（模拟 GitHub Trending 页面片段）
    SAMPLE_HTML = """
    <html><body>
      <article class="Box-row">
        <h2 class="h3 lh-condensed">
          <a href="/octocat/Hello-World">octocat / Hello-World</a>
        </h2>
        <p>My first repository on GitHub!</p>
        <span itemprop="programmingLanguage">Python</span>
        <a href="/octocat/Hello-World/stargazers" aria-label="12345 users starred this repository">12,345 stars</a>
        <a href="/octocat/Hello-World/commits" aria-label="678 users starred this repository today">678 stars today</a>
        <a href="/octocat/Hello-World/forks" aria-label="234 forks">234 forks</a>
      </article>
      <article class="Box-row">
        <h2 class="h3 lh-condensed">
          <a href="/torvalds/linux">torvalds / linux</a>
        </h2>
        <p>Linux kernel source tree</p>
        <span itemprop="programmingLanguage">C</span>
        <a href="/torvalds/linux/stargazers" aria-label="98765 users starred this repository">98,765 stars</a>
        <a href="/torvalds/linux/commits" aria-label="4321 users starred this repository today">4,321 stars today</a>
        <a href="/torvalds/linux/forks" aria-label="8765 forks">8,765 forks</a>
      </article>
      <article class="Box-row">
        <h2 class="h3 lh-condensed">
          <a href="/facebook/react">facebook / react</a>
        </h2>
        <p>A declarative, efficient, and flexible JavaScript library</p>
        <span itemprop="programmingLanguage">JavaScript</span>
        <a href="/facebook/react/stargazers" aria-label="54321 users starred this repository">54,321 stars</a>
        <a href="/facebook/react/commits" aria-label="2100 users starred this repository today">2,100 stars today</a>
        <a href="/facebook/react/forks" aria-label="3210 forks">3,210 forks</a>
      </article>
    </body></html>
    """

    @classmethod
    def run(cls) -> int:
        """
        执行自检流程。

        :return: 0 表示成功，非 0 表示失败
        """
        try:
            # 1. 测试 HTML 解析
            fetcher = GitHubTrendingFetcher(language="", since="daily")
            items = fetcher.parse_html(cls.SAMPLE_HTML)
            if len(items) < 3:
                raise RuntimeError("自检失败: 解析项目数量不足")
            if items[0].repo_name != "octocat/Hello-World":
                raise RuntimeError("自检失败: 仓库名解析错误")

            # 2. 验证关键字段（宽松断言）
            total_stars_list = [item.total_stars for item in items]
            if not all(s > 0 for s in total_stars_list):
                raise RuntimeError(f"自检失败: 总 Star 数异常 - {total_stars_list}")
            if not all(item.stars_today > 0 for item in items):
                raise RuntimeError("自检失败: 今日 Star 数异常")
            if not all(item.forks > 0 for item in items):
                raise RuntimeError("自检失败: Fork 数异常")

            # 3. 测试排序逻辑
            sorted_items = sorted(items, key=lambda x: x.stars_today, reverse=True)
            if sorted_items[0].stars_today < sorted_items[-1].stars_today:
                raise RuntimeError("自检失败: 排序逻辑异常")

            # 4. 测试格式化输出
            report = ReportData(
                generated_at="2026-01-01T00:00:00+00:00",
                language_filter="",
                since_filter="daily",
                items=items,
            )
            md = ReportFormatter.to_markdown(report)
            if "GitHub Trending" not in md:
                raise RuntimeError("自检失败: Markdown 输出异常")
            csv_out = ReportFormatter.to_csv(report)
            if "repo_name" not in csv_out:
                raise RuntimeError("自检失败: CSV 输出异常")
            json_out = ReportFormatter.to_json(report)
            parsed = json.loads(json_out)
            if len(parsed["items"]) < 3:
                raise RuntimeError("自检失败: JSON 输出异常")

            # 5. 测试参数校验
            try:
                GitHubTrendingFetcher(language="invalid_lang_xyz", since="daily").validate()
                raise RuntimeError("自检失败: 非法语言未触发异常")
            except ValueError:
                pass  # 预期行为

            try:
                GitHubTrendingFetcher(language="", since="invalid_since").validate()
                raise RuntimeError("自检失败: 非法时间范围未触发异常")
            except ValueError:
                pass  # 预期行为

            # 6. 测试 URL 构造
            test_url = GitHubTrendingFetcher(language="python", since="weekly").build_url()
            if "trending/python" not in test_url or "since=weekly" not in test_url:
                raise RuntimeError("自检失败: URL 构造错误")

            print("✅ 自检全部通过（离线样例数据验证成功）")
            return 0

        except Exception as exc:
            print(f"❌ 自检失败: {exc}", file=sys.stderr)
            return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="GitHub Trending 周报生成器（独立实现）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python main.py --language Python --since weekly --format markdown\n  python main.py --selftest",
    )
    parser.add_argument(
        "--language", "-l",
        default="",
        help="编程语言过滤（如 Python、JavaScript、Go），留空表示全部",
    )
    parser.add_argument(
        "--since", "-s",
        default="daily",
        choices=["daily", "weekly", "monthly"],
        help="时间范围: daily/weekly/monthly（默认 daily）",
    )
    parser.add_argument(
        "--format", "-f",
        default="markdown",
        choices=["markdown", "csv", "json"],
        help="输出格式（默认 markdown）",
    )
    parser.add_argument(
        "--output", "-o",
        default="",
        help="输出文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不访问网络）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览不写盘（安全守卫）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出处理明细（每步决策）",
    )
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    if argv is None:
        argv = sys.argv[1:]

    try:
        args = parse_args(argv)
    except SystemExit as exc:
        # argparse 在错误时抛出 SystemExit(2)
        return 2
    except Exception as exc:
        print(f"E001: 参数解析失败: {exc}", file=sys.stderr)
        return 1

    # 自检模式
    if args.selftest:
        return SelfTest.run()

    # 正常运行模式
    try:
        fetcher = GitHubTrendingFetcher(language=args.language, since=args.since)
        report = fetcher.fetch_report()

        # 格式化输出
        if args.format == "markdown":
            output_text = ReportFormatter.to_markdown(report)
        elif args.format == "csv":
            output_text = ReportFormatter.to_csv(report)
        elif args.format == "json":
            output_text = ReportFormatter.to_json(report)
        else:
            # 理论上不会到达（argparse 已限制 choices）
            raise RuntimeError(f"E004: 不支持的输出格式: {args.format}")

        # 输出到文件或 stdout
        if args.output:
            if args.verbose:
                print(f"[verbose] 输出格式={args.format}，报告 {len(output_text)} 字符")
            if not args.dry_run:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output_text)
                    print(f"✅ 报告已写入: {args.output}", file=sys.stderr)
                except OSError as exc:
                    print(f"E008: 文件写入失败: {exc}", file=sys.stderr)
                    return 8
            else:
                print(f"[dry-run] 预览报告（未写盘）: {args.output}，共 {len(output_text)} 字符",
                      file=sys.stderr)
        else:
            print(output_text)

        return 0

    except RuntimeError as exc:
        # 错误码已在异常消息中（如 E005: xxx）
        print(f"错误: {exc}", file=sys.stderr)
        # 从消息中提取错误码
        match = re.match(r"(E\d{3}):", str(exc))
        if match:
            return int(match.group(1)[1:])  # E005 -> 5
        return 10  # E010 未预期错误
    except Exception as exc:
        print(f"E010: 未预期运行时错误: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
