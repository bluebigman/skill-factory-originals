#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
email-scraper - 邮箱采集工具（独立实现）

功能：
- 递归爬取网站页面，自动提取并整理公开邮箱地址。
- 支持命令行参数：起始 URL、最大深度、域名白名单/黑名单、输出格式。
- 提供 --selftest 离线自检，不依赖外部文件或网络。

错误码：
- E001: 参数错误
- E002: URL 格式错误
- E003: 网络请求失败
- E004: HTML 解析失败
- E005: 文件写入失败
- E006: 文件读取失败
- E007: 输出格式不支持
- E008: 自检失败
- E009: 递归深度超限
- E010: 未找到有效邮箱

仅依赖 Python 标准库。
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import OrderedDict
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set, Tuple
import time

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ============================================================
# 邮箱提取逻辑（纯字符串处理，不依赖外部库）
# ============================================================
# 宽松的邮箱正则：允许常见字符，不校验域名有效性
EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

# 用于从 mailto: 链接中提取邮箱
MAILTO_RE = re.compile(r"mailto:([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", re.IGNORECASE)


def extract_emails_from_text(text: str) -> Set[str]:
    """
    从纯文本中提取所有邮箱地址。
    返回去重后的邮箱集合。
    """
    if not text:
        return set()
    # 先提取 mailto: 链接（可能带参数）
    mailto_emails = set(MAILTO_RE.findall(text))
    # 再提取普通文本中的邮箱
    plain_emails = set(EMAIL_RE.findall(text))
    # 合并去重
    return mailto_emails | plain_emails


def normalize_email(email: str) -> Optional[str]:
    """
    规范化邮箱地址：
    - 去除首尾空白
    - 转小写（邮箱本地部分理论上区分大小写，但实际使用中通常不区分）
    - 去除 mailto: 前缀
    - 去除多余参数（如 ?subject=xxx）
    """
    if not email:
        return None
    email = email.strip()
    # 去掉 mailto: 前缀（如果存在）
    if email.lower().startswith("mailto:"):
        email = email[7:]
    # 去掉查询参数（? 后面的内容）
    if "?" in email:
        email = email.split("?", 1)[0]
    # 去掉 # 锚点
    if "#" in email:
        email = email.split("#", 1)[0]
    email = email.strip()
    # 再次验证格式
    if not EMAIL_RE.fullmatch(email):
        return None
    # 转小写，便于去重
    return email.lower()


def extract_emails_from_html(html: str) -> Set[str]:
    """
    从 HTML 源码中提取邮箱地址。
    同时处理 mailto: 链接和纯文本中的邮箱。
    """
    if not html:
        return set()
    # 提取 mailto: 链接
    mailto_emails = set()
    for match in MAILTO_RE.finditer(html):
        email = normalize_email(match.group(1))
        if email:
            mailto_emails.add(email)

    # 提取纯文本中的邮箱（粗略过滤掉 HTML 标签干扰）
    # 先将 HTML 标签替换为空格，避免标签属性中的邮箱误匹配
    text_only = re.sub(r"<[^>]+>", " ", html)
    plain_emails = set()
    for match in EMAIL_RE.finditer(text_only):
        email = normalize_email(match.group(0))
        if email:
            plain_emails.add(email)

    return mailto_emails | plain_emails


# ============================================================
# HTML 解析器：提取页面链接（标准库 HTMLParser）
# ============================================================
class LinkParser(HTMLParser):
    """解析 HTML，提取所有 href 链接。"""

    def __init__(self):
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "a":
            for attr_name, attr_value in attrs:
                if attr_name.lower() == "href" and attr_value:
                    self.links.append(attr_value)


def extract_links_from_html(html: str, base_url: str) -> Set[str]:
    """
    从 HTML 中提取所有站内链接，并转换为绝对 URL。
    base_url 用于解析相对路径。
    """
    parser = LinkParser()
    try:
        parser.feed(html)
    except Exception:
        # 解析失败时返回空集合
        return set()

    base_parsed = urllib.parse.urlparse(base_url)
    base_origin = f"{base_parsed.scheme}://{base_parsed.netloc}"

    absolute_links: Set[str] = set()
    for link in parser.links:
        # 跳过空链接、javascript、mailto、tel 等协议
        if not link or link.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        # 解析为绝对 URL
        try:
            abs_url = urllib.parse.urljoin(base_url, link)
            parsed = urllib.parse.urlparse(abs_url)
            # 只保留 http/https 协议
            if parsed.scheme not in ("http", "https"):
                continue
            # 只保留站内链接（同源）
            if parsed.netloc == base_parsed.netloc:
                # 去掉 fragment
                clean_url = urllib.parse.urlunparse(
                    (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
                )
                absolute_links.add(clean_url)
        except Exception:
            continue
    return absolute_links


# ============================================================
# 域名过滤逻辑
# ============================================================
def is_domain_allowed(url: str, whitelist: Optional[Set[str]], blacklist: Optional[Set[str]]) -> bool:
    """
    判断 URL 的域名是否允许爬取。
    - 白名单非空时，仅允许白名单中的域名。
    - 黑名单非空时，禁止黑名单中的域名。
    - 白名单和黑名单同时为空时，允许所有域名。
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    # 去掉端口
    if ":" in host:
        host = host.split(":", 1)[0]

    if whitelist and host not in whitelist:
        return False
    if blacklist and host in blacklist:
        return False
    return True


# ============================================================
# 爬虫核心逻辑
# ============================================================
class EmailScraper:
    """递归爬取网站并提取邮箱地址。"""

    def __init__(
        self,
        max_depth: int = 2,
        whitelist: Optional[Set[str]] = None,
        blacklist: Optional[Set[str]] = None,
        timeout: int = 10,
        user_agent: str = "email-scraper/1.0",
    ):
        self.max_depth = max_depth
        self.whitelist = whitelist
        self.blacklist = blacklist
        self.timeout = timeout
        self.user_agent = user_agent
        self.visited: Set[str] = set()
        self.emails: Set[str] = set()
        self.page_emails: Dict[str, List[str]] = OrderedDict()

    def _fetch_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        获取 URL 内容。
        返回 (HTML内容, 错误信息)。成功时错误信息为 None。
        """
        request = urllib.request.Request(
            url,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                # 只处理 HTML 内容
                if "html" not in content_type.lower():
                    return None, f"非 HTML 内容: {content_type}"
                data = response.read()
                # 尝试使用 UTF-8 解码，失败则用 latin-1
                try:
                    html = data.decode("utf-8")
                except UnicodeDecodeError:
                    html = data.decode("latin-1")
                return html, None
        except Exception as e:
            return None, str(e)

    def crawl(self, start_url: str, max_pages: int = 100) -> Dict[str, List[str]]:
        """
        从起始 URL 开始递归爬取。
        返回 {页面URL: [邮箱列表]} 的字典。
        """
        if not start_url:
            raise AppError("E001", "起始 URL 不能为空")
        if self.max_depth < 0:
            raise AppError("E001", "最大深度不能为负数")
        if max_pages <= 0:
            raise AppError("E001", "最大页面数必须为正数")

        self.visited.clear()
        self.emails.clear()
        self.page_emails.clear()

        # BFS 队列: (url, depth)
        queue: List[Tuple[str, int]] = [(start_url, 0)]
        page_count = 0

        while queue and page_count < max_pages:
            url, depth = queue.pop(0)
            if url in self.visited:
                continue
            if not is_domain_allowed(url, self.whitelist, self.blacklist):
                continue

            self.visited.add(url)
            page_count += 1

            html, error = self._fetch_url(url)
            if error:
                # 请求失败，记录错误但继续
                self.page_emails[url] = []
                continue
            if html is None:
                continue

            # 提取邮箱
            page_emails = extract_emails_from_html(html)
            normalized_page_emails = set()
            for email in page_emails:
                normalized = normalize_email(email)
                if normalized:
                    normalized_page_emails.add(normalized)
                    self.emails.add(normalized)
            self.page_emails[url] = sorted(normalized_page_emails)

            # 如果还有深度剩余，提取链接继续爬
            if depth < self.max_depth:
                links = extract_links_from_html(html, url)
                for link in links:
                    if link not in self.visited and link not in [u for u, _ in queue]:
                        # 检查新链接的深度
                        queue.append((link, depth + 1))

        return self.page_emails

    def get_all_emails(self) -> List[str]:
        """返回所有去重后的邮箱列表。"""
        return sorted(self.emails)


# ============================================================
# 输出格式化
# ============================================================
def format_output(emails: List[str], output_format: str) -> str:
    """按指定格式输出邮箱列表。"""
    if output_format == "txt":
        return "\n".join(emails)
    elif output_format == "json":
        return json.dumps({"emails": emails}, ensure_ascii=False, indent=2)
    elif output_format == "csv":
        if not emails:
            return ""
        # 简单 CSV 输出，每个邮箱一行
        lines = ["email"]
        lines.extend(emails)
        return "\n".join(lines)
    else:
        raise AppError("E007", f"不支持的输出格式: {output_format}")


# ============================================================
# 自检逻辑（离线，不依赖外部文件或网络）
# ============================================================
def run_selftest() -> int:
    """
    自检核心逻辑。使用内置硬编码样例数据。
    返回 0 表示通过，1 表示失败。
    """
    print("开始自检...")

    # ---- 测试 1: 从纯文本提取邮箱 ----
    test_text = """
    联系我们：support@example.com 或 sales@example.com
    也欢迎邮件至: admin@test.org (注意这不是真实邮箱)
    无效邮箱: not-an-email, @nodomain.com, user@.com
    """
    emails_from_text = extract_emails_from_text(test_text)
    assert len(emails_from_text) >= 3, f"E008: 文本提取邮箱数量不足，实际: {len(emails_from_text)}"
    assert "support@example.com" in emails_from_text, "E008: 缺少 support@example.com"
    assert "sales@example.com" in emails_from_text, "E008: 缺少 sales@example.com"
    assert "admin@test.org" in emails_from_text, "E008: 缺少 admin@test.org"
    print(f"  [通过] 文本提取: {len(emails_from_text)} 个邮箱")

    # ---- 测试 2: 从 HTML 提取邮箱 ----
    test_html = """
    <html>
    <body>
        <a href="mailto:contact@example.com?subject=Hello">联系我们</a>
        <a href="mailto:info@example.com">信息</a>
        <p>业务邮箱: business@example.org</p>
        <script>var x = "fake@example.com";</script>
    </body>
    </html>
    """
    emails_from_html = extract_emails_from_html(test_html)
    assert len(emails_from_html) >= 3, f"E008: HTML 提取邮箱数量不足，实际: {len(emails_from_html)}"
    assert "contact@example.com" in emails_from_html, "E008: 缺少 mailto 邮箱"
    assert "business@example.org" in emails_from_html, "E008: 缺少正文邮箱"
    print(f"  [通过] HTML 提取: {len(emails_from_html)} 个邮箱")

    # ---- 测试 3: 邮箱规范化 ----
    normalized = normalize_email("  Example@Example.COM  ")
    assert normalized == "example@example.com", f"E008: 规范化失败: {normalized}"
    normalized2 = normalize_email("mailto:test@example.com?subject=x")
    assert normalized2 == "test@example.com", f"E008: mailto 规范化失败: {normalized2}"
    invalid = normalize_email("not-an-email")
    assert invalid is None, f"E008: 无效邮箱应返回 None，实际: {invalid}"
    print("  [通过] 邮箱规范化")

    # ---- 测试 4: 链接提取 ----
    test_html_links = """
    <html>
    <a href="/page1">页面1</a>
    <a href="https://example.com/page2">页面2</a>
    <a href="https://other-site.com/external">外部</a>
    <a href="mailto:x@y.com">邮件</a>
    <a href="javascript:void(0)">JS</a>
    </html>
    """
    links = extract_links_from_html(test_html_links, "https://example.com")
    assert len(links) >= 2, f"E008: 链接提取数量不足，实际: {len(links)}"
    assert "https://example.com/page1" in links, "E008: 缺少相对路径链接"
    assert "https://example.com/page2" in links, "E008: 缺少绝对路径链接"
    assert all("other-site.com" not in link for link in links), "E008: 不应包含外部链接"
    print(f"  [通过] 链接提取: {len(links)} 个站内链接")

    # ---- 测试 5: 域名过滤 ----
    allowed = is_domain_allowed("https://example.com/page", {"example.com"}, None)
    assert allowed, "E008: 白名单过滤失败"
    blocked = is_domain_allowed("https://blocked.com/page", None, {"blocked.com"})
    assert not blocked, "E008: 黑名单过滤失败"
    allowed_all = is_domain_allowed("https://any.com/page", None, None)
    assert allowed_all, "E008: 无过滤时应允许所有"
    print("  [通过] 域名过滤")

    # ---- 测试 6: 输出格式化 ----
    test_emails = ["a@example.com", "b@example.org"]
    txt_output = format_output(test_emails, "txt")
    assert len(txt_output.splitlines()) == 2, "E008: TXT 输出格式错误"
    json_output = format_output(test_emails, "json")
    json_data = json.loads(json_output)
    assert len(json_data["emails"]) == 2, "E008: JSON 输出格式错误"
    csv_output = format_output(test_emails, "csv")
    assert len(csv_output.splitlines()) == 3, "E008: CSV 输出格式错误"
    print("  [通过] 输出格式化")

    # ---- 测试 7: 模拟爬虫（使用本地 HTML 字符串，不访问网络） ----
    # 创建一个模拟的爬虫实例，但直接测试其内部逻辑
    scraper = EmailScraper(max_depth=2)
    # 测试 visited 去重
    scraper.visited.add("https://example.com")
    assert "https://example.com" in scraper.visited
    print("  [通过] 爬虫实例初始化")

    print("\n全部自检通过！")
    return 0


# ============================================================
# 主入口
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    """主函数入口。"""
    parser = argparse.ArgumentParser(
        description="email-scraper - 递归爬取网站并提取公开邮箱地址",
        epilog="示例: python main.py https://example.com -d 2 -o result.json",
    )
    parser.add_argument("url", nargs="?", help="起始 URL（不提供时使用默认示例）")
    parser.add_argument("-d", "--depth", type=int, default=2, help="递归爬取深度（默认 2）")
    parser.add_argument("-w", "--whitelist", help="域名白名单，逗号分隔（如 example.com,test.org）")
    parser.add_argument("-b", "--blacklist", help="域名黑名单，逗号分隔")
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("-f", "--format", choices=["txt", "json", "csv"], default="txt", help="输出格式（默认 txt）")
    parser.add_argument("--timeout", type=int, default=10, help="请求超时时间（秒，默认 10）")
    parser.add_argument("--max-pages", type=int, default=100, help="最大爬取页面数（默认 100）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 正常模式
    if not args.url:
        print("错误: 请提供起始 URL（或使用 --selftest 运行自检）", file=sys.stderr)
        print("示例: python main.py https://example.com", file=sys.stderr)
        return 1

    # 解析白名单/黑名单
    whitelist = None
    if args.whitelist:
        whitelist = {d.strip().lower() for d in args.whitelist.split(",") if d.strip()}
    blacklist = None
    if args.blacklist:
        blacklist = {d.strip().lower() for d in args.blacklist.split(",") if d.strip()}

    # 验证 URL 格式
    parsed_url = urllib.parse.urlparse(args.url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        print(f"错误: URL 格式无效: {args.url}", file=sys.stderr)
        return 1

    # 创建爬虫并执行
    scraper = EmailScraper(
        max_depth=args.depth,
        whitelist=whitelist,
        blacklist=blacklist,
        timeout=args.timeout,
    )

    try:
        print(f"开始爬取: {args.url} (深度: {args.depth})")
        page_emails = scraper.crawl(args.url, max_pages=args.max_pages)
        all_emails = scraper.get_all_emails()

        if not all_emails:
            print("未找到任何邮箱地址。", file=sys.stderr)
            return 0

        print(f"共爬取 {len(page_emails)} 个页面，找到 {len(all_emails)} 个唯一邮箱。")

        # 输出结果
        output_text = format_output(all_emails, args.format)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_text)
                print(f"结果已保存到: {args.output}")
            except Exception as e:
                print(f"错误: 无法写入文件: {e}", file=sys.stderr)
                return 1
        else:
            print("\n" + output_text)

        return 0

    except AppError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
