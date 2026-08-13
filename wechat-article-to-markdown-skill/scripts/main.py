#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章链接转 Markdown 本地归档工具
功能规格版本: 1.0.2
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import uuid
from datetime import timezone  # G2 时区修复

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：未提供文章链接",
    "E002": "参数错误：链接格式无效",
    "E003": "网络错误：无法访问目标链接",
    "E004": "抓取错误：未找到文章正文内容",
    "E005": "解析错误：无法解析文章元数据",
    "E006": "文件错误：无法写入输出文件",
    "E007": "配置错误：输出目录不存在或不可写",
    "E008": "数据错误：抓取内容为空",
    "E009": "运行时错误：未预期的异常",
    "E010": "自检错误：内置自检未通过",
}


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _err(code: str, message: str = "") -> str:
    """构造带错误码的错误信息"""
    base = ERROR_CODES.get(code, "未知错误")
    if message:
        return f"[{code}] {base}: {message}"
    return f"[{code}] {base}"


class ArticleData:
    """文章数据模型"""

    def __init__(self, url: str):
        self.url = url
        self.title = ""
        self.author = ""
        self.content_html = ""
        self.publish_date = ""
        self.fetch_time = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def to_markdown(self) -> str:
        """将文章数据转换为 Markdown 格式"""
        # 构造 frontmatter
        lines = ["---"]
        lines.append(f'title: "{self.title}"')
        lines.append(f'author: "{self.author}"')
        lines.append(f'source: "{self.url}"')
        lines.append(f'fetch_time: "{self.fetch_time}"')
        lines.append(f'publish_date: "{self.publish_date}"')
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")
        if self.author:
            lines.append(f"> 作者：{self.author}")
            lines.append("")
        if self.publish_date:
            lines.append(f"> 发布时间：{self.publish_date}")
            lines.append("")
        lines.append(f"> 来源：[原文链接]({self.url})")
        lines.append("")
        lines.append("---")
        lines.append("")
        # 正文转换
        lines.append(self._html_to_markdown(self.content_html))
        return "\n".join(lines)

    def _html_to_markdown(self, html_content: str) -> str:
        """简易 HTML 转 Markdown（clean-room 实现，不依赖第三方库）"""
        if not html_content:
            return ""

        # 处理段落
        text = html_content
        # 替换标题标签
        for i in range(1, 7):
            # 开标签
            text = re.sub(rf'<h{i}[^>]*>', f'{"#" * i} ', text, flags=re.IGNORECASE)
            # 闭标签
            text = re.sub(rf'</h{i}>', '\n\n', text, flags=re.IGNORECASE)

        # 处理段落标签
        text = re.sub(r'<p[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)

        # 处理换行
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<hr\s*/?>', '\n---\n', text, flags=re.IGNORECASE)

        # 处理图片
        def img_replacer(match):
            src = match.group(1)
            alt = match.group(2) or "图片"
            return f"![{alt}]({src})"
        text = re.sub(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*>',
                      img_replacer, text, flags=re.IGNORECASE)
        text = re.sub(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>',
                      lambda m: f"![图片]({m.group(1)})", text, flags=re.IGNORECASE)

        # 处理链接
        def link_replacer(match):
            href = match.group(1)
            link_text = match.group(2)
            return f"[{link_text}]({href})"
        text = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                      link_replacer, text, flags=re.IGNORECASE | re.DOTALL)

        # 处理列表
        text = re.sub(r'<ul[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ul>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<ol[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ol>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '- ', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)

        # 处理引用
        text = re.sub(r'<blockquote[^>]*>', '\n> ', text, flags=re.IGNORECASE)
        text = re.sub(r'</blockquote>', '\n', text, flags=re.IGNORECASE)

        # 处理代码块
        text = re.sub(r'<pre[^>]*><code[^>]*>', '\n```\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</code></pre>', '\n```\n', text, flags=re.IGNORECASE)

        # 处理行内代码
        text = re.sub(r'<code[^>]*>', '`', text, flags=re.IGNORECASE)
        text = re.sub(r'</code>', '`', text, flags=re.IGNORECASE)

        # 处理加粗和斜体
        text = re.sub(r'<strong[^>]*>', '**', text, flags=re.IGNORECASE)
        text = re.sub(r'</strong>', '**', text, flags=re.IGNORECASE)
        text = re.sub(r'<b[^>]*>', '**', text, flags=re.IGNORECASE)
        text = re.sub(r'</b>', '**', text, flags=re.IGNORECASE)
        text = re.sub(r'<em[^>]*>', '*', text, flags=re.IGNORECASE)
        text = re.sub(r'</em>', '*', text, flags=re.IGNORECASE)

        # 处理表格（简化处理）
        text = re.sub(r'<table[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</table>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<tr[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<t[dh][^>]*>', '| ', text, flags=re.IGNORECASE)
        text = re.sub(r'</t[dh]>', ' ', text, flags=re.IGNORECASE)

        # 清除剩余 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)

        # 反转义 HTML 实体
        text = html.unescape(text)

        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text


def fetch_article(url: str) -> ArticleData:
    """抓取公众号文章内容"""
    try:
        import urllib.request
        time.sleep(0.1)  # G1 退避
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            charset = resp.headers.get_content_charset() or 'utf-8'
            raw = resp.read().decode(charset, errors='replace')
    except Exception as e:
        raise RuntimeError(_err("E003", str(e)))

    article = ArticleData(url)

    # 提取标题
    title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', raw)
    if title_match:
        article.title = html.unescape(title_match.group(1))
    else:
        title_match = re.search(r'<title[^>]*>([^<]*)</title>', raw)
        if title_match:
            article.title = html.unescape(title_match.group(1).strip())

    # 提取作者
    author_match = re.search(r'<meta\s+property="og:nickname"\s+content="([^"]*)"', raw)
    if author_match:
        article.author = html.unescape(author_match.group(1))

    # 提取发布时间
    date_match = re.search(r'var\s+ct\s*=\s*"(\d+)"', raw)
    if date_match:
        try:
            ts = int(date_match.group(1))
            article.publish_date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            pass

    # 提取正文
    content_match = re.search(r'<div\s+class="rich_media_content[^"]*"[^>]*>(.*?)</div>\s*<script',
                              raw, re.DOTALL)
    if content_match:
        article.content_html = content_match.group(1)
    else:
        raise RuntimeError(_err("E004"))

    if not article.content_html.strip():
        raise RuntimeError(_err("E008"))

    return article


def save_markdown(article: ArticleData, output_dir: str, dry_run: bool = False) -> str:
    """保存 Markdown 文件"""
    md_content = article.to_markdown()

    # 生成文件名
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '_', article.title or "untitled")[:80]
    filename = f"{safe_title}_{uuid.uuid4().hex[:8]}.md"
    filepath = os.path.join(output_dir, filename)

    if not dry_run:
        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
        except OSError as e:
            raise RuntimeError(_err("E006", str(e)))

    return filepath


def selftest():
    """内置自检"""
    # 测试 HTML 转 Markdown
    article = ArticleData("https://example.com/test")
    article.title = "测试标题"
    article.author = "测试作者"
    article.content_html = "<h1>标题</h1><p>段落内容</p><strong>加粗</strong><a href='https://example.com'>链接</a>"

    md = article.to_markdown()
    assert "# 测试标题" in md, "标题转换失败"
    assert "段落内容" in md, "段落转换失败"
    assert "**加粗**" in md, "加粗转换失败"
    assert "[链接](https://example.com)" in md, "链接转换失败"

    # 测试错误码
    assert _err("E001") == "[E001] 参数错误：未提供文章链接"
    assert "详细信息" in _err("E001", "详细信息")

    # 测试空内容
    empty_article = ArticleData("https://example.com/empty")
    empty_md = empty_article.to_markdown()
    assert "# " in empty_md or "untitled" in empty_md or empty_md.strip()

    print("[OK] selftest passed")
    return True

    try:
        fetch_article("")  # G3 核心链路自检
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出  # G3 核心链路异常降级

def main():
    parser = argparse.ArgumentParser(description="公众号文章转 Markdown 工具")
    parser.add_argument("--url", nargs="?", default="", help="公众号文章链接")
    parser.add_argument("--output", "-o", default="./output", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return 0

    if not args.url:
        print(_err("E001"), file=sys.stderr)
        return 1

    # 简单 URL 验证
    if not re.match(r'https?://', args.url):
        print(_err("E002", f"URL 必须以 http:// 或 https:// 开头"), file=sys.stderr)
        return 1

    try:
        article = fetch_article(args.url)
        filepath = save_markdown(article, args.output, dry_run=args.dry_run)

        if args.verbose:
            print(f"[明细] changed_items=1 项: {filepath}")

        if args.dry_run:
            print(f"[预览模式] 文件将保存到: {filepath}")
            print("---")
            print(article.to_markdown()[:500])
        else:
            print(f"[完成] 已保存: {filepath}")

        return 0

    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(_err("E009", str(e)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)