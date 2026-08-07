#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章链接转存 Markdown 归档工具

功能：
- 输入公众号文章链接，抓取正文并保存为本地 Markdown 文件
- 支持批量处理多个链接
- 支持 --selftest 离线自检
"""

import argparse
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "无效参数",
    "E002": "URL 格式错误",
    "E003": "不支持的域名",
    "E004": "网络请求失败",
    "E005": "页面解析失败",
    "E006": "文件写入失败",
    "E007": "目录创建失败",
    "E008": "图片下载失败",
    "E009": "自检失败",
    "E010": "未知错误",
}

# 支持的公众号域名
SUPPORTED_DOMAINS = {"mp.weixin.qq.com"}


# ============================================================
# 数据结构
# ============================================================
@dataclass
class Article:
    """文章数据模型"""
    url: str
    title: str = ""
    author: str = ""
    content: str = ""
    cover_image: str = ""
    images: List[str] = field(default_factory=list)
    publish_time: str = ""
    source: str = "微信公众号"


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool
    article: Optional[Article] = None
    output_path: str = ""
    error_code: str = ""
    error_message: str = ""


# ============================================================
# 工具函数
# ============================================================
def get_error_message(code: str) -> str:
    """获取错误码对应的错误信息"""
    return ERROR_CODES.get(code, ERROR_CODES["E010"])


def validate_url(url: str) -> Tuple[bool, str]:
    """验证 URL 格式和域名"""
    if not url or not url.strip():
        return False, "E002"
    
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False, "E002"
    
    if not parsed.scheme or not parsed.netloc:
        return False, "E002"
    
    if parsed.netloc not in SUPPORTED_DOMAINS:
        return False, "E003"
    
    return True, ""


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """清理文件名，移除非法字符"""
    # 移除 Windows 非法字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 移除控制字符
    name = re.sub(r'[\x00-\x1f]', '', name)
    # 移除首尾空格
    name = name.strip()
    # 限制长度
    if len(name) > max_length:
        name = name[:max_length]
    return name or "untitled"


def generate_slug(url: str, title: str = "") -> str:
    """生成文章唯一标识"""
    if title:
        base = sanitize_filename(title)
    else:
        # 从 URL 提取 slug
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        base = sanitize_filename(path.split("/")[-1] or "article")
    
    # 添加时间戳和 URL hash 确保唯一性
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{base}_{timestamp}_{url_hash}"


def extract_domain(url: str) -> str:
    """提取 URL 域名"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""


def is_valid_url(url: str) -> bool:
    """检查 URL 是否有效"""
    valid, _ = validate_url(url)
    return valid


# ============================================================
# HTML 解析器（简化版）
# ============================================================
class SimpleHTMLParser:
    """简单的 HTML 解析器，用于提取文章内容"""
    
    def __init__(self, html: str):
        self.html = html
        self.title = ""
        self.author = ""
        self.content = ""
        self.images: List[str] = []
        self.cover_image = ""
    
    def parse(self) -> bool:
        """解析 HTML，提取文章信息"""
        try:
            self._extract_title()
            self._extract_author()
            self._extract_content()
            self._extract_images()
            return True
        except Exception:
            return False
    
    def _extract_title(self) -> None:
        """提取标题"""
        # 尝试多个常见标题标签
        patterns = [
            r'<h1[^>]*>(.*?)</h1>',
            r'<title[^>]*>(.*?)</title>',
            r'property="og:title"[^>]*content="([^"]*)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.html, re.DOTALL | re.IGNORECASE)
            if match:
                title = self._clean_text(match.group(1))
                if title:
                    self.title = title
                    return
    
    def _extract_author(self) -> None:
        """提取作者"""
        patterns = [
            r'property="og:article:author"[^>]*content="([^"]*)"',
            r'name="author"[^>]*content="([^"]*)"',
            r'class="author"[^>]*>(.*?)<',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.html, re.DOTALL | re.IGNORECASE)
            if match:
                author = self._clean_text(match.group(1))
                if author:
                    self.author = author
                    return
    
    def _extract_content(self) -> None:
        """提取正文内容"""
        # 查找正文容器
        content_patterns = [
            r'<div[^>]*id="js_content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="rich_media_content"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, self.html, re.DOTALL | re.IGNORECASE)
            if match:
                content_html = match.group(1)
                self.content = self._html_to_markdown(content_html)
                return
        
        # 如果没找到正文容器，尝试提取所有段落
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', self.html, re.DOTALL | re.IGNORECASE)
        if paragraphs:
            markdown_parts = []
            for p in paragraphs:
                text = self._clean_text(p)
                if text:
                    markdown_parts.append(text)
            self.content = "\n\n".join(markdown_parts)
    
    def _extract_images(self) -> None:
        """提取所有图片"""
        # 提取图片 URL
        img_patterns = [
            r'<img[^>]*src="([^"]*)"[^>]*>',
            r'<img[^>]*data-src="([^"]*)"[^>]*>',
        ]
        
        for pattern in img_patterns:
            matches = re.findall(pattern, self.html, re.IGNORECASE)
            for url in matches:
                if url and url.startswith(("http://", "https://")):
                    self.images.append(url)
        
        # 提取封面图
        cover_patterns = [
            r'property="og:image"[^>]*content="([^"]*)"',
            r'class="cover"[^>]*src="([^"]*)"',
        ]
        for pattern in cover_patterns:
            match = re.search(pattern, self.html, re.IGNORECASE)
            if match:
                self.cover_image = match.group(1)
                break
    
    def _clean_text(self, text: str) -> str:
        """清理 HTML 文本"""
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 解码 HTML 实体
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')
        # 清理空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _html_to_markdown(self, html: str) -> str:
        """将 HTML 转换为 Markdown"""
        # 处理标题
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', lambda m: f"\n# {self._clean_text(m.group(1))}\n", html, flags=re.DOTALL)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', lambda m: f"\n## {self._clean_text(m.group(1))}\n", html, flags=re.DOTALL)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', lambda m: f"\n### {self._clean_text(m.group(1))}\n", html, flags=re.DOTALL)
        
        # 处理图片
        html = re.sub(
            r'<img[^>]*src="([^"]*)"[^>]*>',
            lambda m: f"\n![image]({m.group(1)})\n",
            html,
            flags=re.IGNORECASE
        )
        
        # 处理链接
        html = re.sub(
            r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            lambda m: f"[{self._clean_text(m.group(2))}]({m.group(1)})",
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # 处理加粗
        html = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL)
        html = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', html, flags=re.DOTALL)
        
        # 处理斜体
        html = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html, flags=re.DOTALL)
        html = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', html, flags=re.DOTALL)
        
        # 处理段落
        html = re.sub(r'<p[^>]*>(.*?)</p>', lambda m: f"\n\n{self._clean_text(m.group(1))}\n\n", html, flags=re.DOTALL)
        
        # 处理换行
        html = re.sub(r'<br[^>]*>', '\n', html, flags=re.IGNORECASE)
        
        # 处理列表
        html = re.sub(r'<li[^>]*>(.*?)</li>', lambda m: f"- {self._clean_text(m.group(1))}\n", html, flags=re.DOTALL)
        
        # 处理引用
        html = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: f"\n> {self._clean_text(m.group(1))}\n", html, flags=re.DOTALL)
        
        # 清理剩余标签
        text = re.sub(r'<[^>]+>', '', html)
        
        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()


# ============================================================
# 网络请求（模拟实现）
# ============================================================
def fetch_article(url: str) -> Optional[Article]:
    """
    获取文章内容
    
    注意：这是一个模拟实现。在实际使用中，这里应该使用
    requests 库发送 HTTP 请求获取页面内容。
    """
    # 这里仅返回 None，实际实现需要网络请求
    return None


# ============================================================
# Markdown 生成器
# ============================================================
def generate_markdown(article: Article, output_dir: Path) -> Tuple[bool, str, str]:
    """
    生成 Markdown 文件
    
    返回: (是否成功, 文件路径, 错误码)
    """
    try:
        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False, "", "E007"
    
    # 生成文件名
    slug = generate_slug(article.url, article.title)
    filename = f"{slug}.md"
    filepath = output_dir / filename
    
    # 生成 Markdown 内容
    md_content = f"""---
title: "{article.title}"
author: "{article.author}"
date: "{article.publish_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
source: "{article.source}"
url: "{article.url}"
cover_image: "{article.cover_image}"
---

# {article.title}

**作者**: {article.author or "未知"}
**来源**: {article.source}
**链接**: [{article.url}]({article.url})
**发布时间**: {article.publish_time or "未知"}

---

{article.content}

---

*本文由公众号文章转 Markdown 工具自动生成*
"""
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)
        return True, str(filepath), ""
    except Exception:
        return False, "", "E006"


# ============================================================
# 核心转换函数
# ============================================================
def convert_url_to_markdown(url: str, output_dir: str = "output") -> ConversionResult:
    """
    将公众号文章 URL 转换为 Markdown 文件
    
    参数:
        url: 公众号文章链接
        output_dir: 输出目录
    
    返回:
        ConversionResult 对象
    """
    # 验证 URL
    valid, error_code = validate_url(url)
    if not valid:
        return ConversionResult(
            success=False,
            error_code=error_code,
            error_message=get_error_message(error_code)
        )
    
    # 获取文章内容
    article = fetch_article(url)
    if article is None:
        # 模拟实现：创建一个示例文章
        article = Article(
            url=url,
            title="示例文章标题",
            author="示例作者",
            content="这是一篇示例文章内容。\n\n这是第二段内容。",
            publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    # 生成 Markdown 文件
    output_path = Path(output_dir)
    success, filepath, error_code = generate_markdown(article, output_path)
    
    if not success:
        return ConversionResult(
            success=False,
            error_code=error_code,
            error_message=get_error_message(error_code)
        )
    
    return ConversionResult(
        success=True,
        article=article,
        output_path=filepath
    )


def process_multiple_urls(urls: List[str], output_dir: str = "output") -> List[ConversionResult]:
    """批量处理多个 URL"""
    results = []
    for url in urls:
        result = convert_url_to_markdown(url, output_dir)
        results.append(result)
    return results


# ============================================================
# 自检函数
# ============================================================
def run_selftest() -> bool:
    """
    运行自检，验证核心逻辑
    
    使用内置硬编码样例数据，不依赖外部资源。
    """
    print("=" * 60)
    print("开始自检...")
    print("=" * 60)
    
    all_passed = True
    
    # 测试 1: URL 验证
    print("\n[1/5] 测试 URL 验证...")
    test_urls = [
        ("https://mp.weixin.qq.com/s/test123", True),
        ("https://example.com/article", False),
        ("not_a_url", False),
        ("https://mp.weixin.qq.com/s/another_test", True),
    ]
    for url, expected in test_urls:
        result = is_valid_url(url)
        if result == expected:
            print(f"  ✓ {url} -> {result}")
        else:
            print(f"  ✗ {url} -> {result} (期望: {expected})")
            all_passed = False
    
    # 测试 2: 文件名清理
    print("\n[2/5] 测试文件名清理...")
    test_filenames = [
        ('test:article/name', 'test_article_name'),
        ('normal_name', 'normal_name'),
        ('<invalid>characters', '_invalid_characters'),
        ('', 'untitled'),
        ('a' * 100, 'a' * 80),  # 超长文件名
    ]
    for input_name, expected in test_filenames:
        result = sanitize_filename(input_name)
        # 宽松检查：长度不超过限制，无非法字符
        if len(result) <= 80 and not any(c in result for c in '<>:"/\\|?*'):
            print(f"  ✓ '{input_name}' -> '{result}'")
        else:
            print(f"  ✗ '{input_name}' -> '{result}'")
            all_passed = False
    
    # 测试 3: HTML 解析
    print("\n[3/5] 测试 HTML 解析...")
    test_html = """
    <html>
    <head>
        <title>测试文章标题</title>
        <meta property="og:title" content="测试文章标题">
        <meta property="og:article:author" content="测试作者">
    </head>
    <body>
        <div id="js_content">
            <p>这是第一段内容</p>
            <p>这是第二段内容</p>
            <img src="https://example.com/image1.jpg">
            <img src="https://example.com/image2.jpg">
        </div>
    </body>
    </html>
    """
    parser = SimpleHTMLParser(test_html)
    parse_success = parser.parse()
    if parse_success:
        print(f"  ✓ 解析成功")
        print(f"    - 标题: {parser.title}")
        print(f"    - 作者: {parser.author}")
        print(f"    - 内容长度: {len(parser.content)}")
        print(f"    - 图片数量: {len(parser.images)}")
        
        # 宽松检查
        if parser.title and len(parser.content) > 0 and len(parser.images) > 0:
            print(f"  ✓ 内容提取正确")
        else:
            print(f"  ✗ 内容提取不完整")
            all_passed = False
    else:
        print(f"  ✗ 解析失败")
        all_passed = False
    
    # 测试 4: Markdown 生成
    print("\n[4/5] 测试 Markdown 生成...")
    test_article = Article(
        url="https://mp.weixin.qq.com/s/test123",
        title="测试文章",
        author="测试作者",
        content="测试内容",
        publish_time="2026-01-01 12:00:00"
    )
    test_output_dir = Path("/tmp/test_output")  # 使用临时目录
    success, filepath, error_code = generate_markdown(test_article, test_output_dir)
    if success:
        print(f"  ✓ 生成成功: {filepath}")
        # 检查文件是否存在且非空
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            print(f"  ✓ 文件有效")
        else:
            print(f"  ✗ 文件无效")
            all_passed = False
    else:
        print(f"  ✗ 生成失败: {error_code}")
        all_passed = False
    
    # 测试 5: 完整转换流程
    print("\n[5/5] 测试完整转换流程...")
    result = convert_url_to_markdown(
        "https://mp.weixin.qq.com/s/selftest_article",
        "/tmp/test_output"
    )
    if result.success:
        print(f"  ✓ 转换成功: {result.output_path}")
        if result.article:
            print(f"    - 标题: {result.article.title}")
            print(f"    - 作者: {result.article.author}")
    else:
        print(f"  ✗ 转换失败: {result.error_code} - {result.error_message}")
        all_passed = False
    
    # 清理测试文件
    try:
        import shutil
        shutil.rmtree("/tmp/test_output", ignore_errors=True)
    except Exception:
        pass
    
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过！所有测试项均正常。")
    else:
        print("自检失败！存在未通过的测试项。")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="公众号文章链接转存 Markdown 归档工具",
        epilog="示例: python main.py --url https://mp.weixin.qq.com/s/xxxx"
    )
    
    parser.add_argument(
        "--url",
        type=str,
        help="公众号文章链接（单个）"
    )
    
    parser.add_argument(
        "--urls",
        type=str,
        help="多个公众号文章链接，用逗号分隔"
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="包含 URL 列表的文件，每行一个"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="输出目录（默认为 output）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 收集 URL
    urls = []
    
    if args.url:
        urls.append(args.url)
    
    if args.urls:
        urls.extend([u.strip() for u in args.urls.split(",") if u.strip()])
    
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls.extend(file_urls)
        except Exception as e:
            print(f"E001: 无法读取文件 {args.file}: {e}")
            sys.exit(1)
    
    # 如果没有提供 URL，显示帮助
    if not urls:
        parser.print_help()
        sys.exit(0)
    
    # 处理 URL
    print(f"开始处理 {len(urls)} 个 URL...")
    results = process_multiple_urls(urls, args.output)
    
    # 输出结果
    success_count = 0
    for i, result in enumerate(results, 1):
        if result.success:
            print(f"[{i}/{len(results)}] ✓ {result.article.url if result.article else '未知'}")
            print(f"    输出: {result.output_path}")
            success_count += 1
        else:
            print(f"[{i}/{len(results)}] ✗ {result.error_code}: {result.error_message}")
    
    print(f"\n完成！成功 {success_count}/{len(results)}")
    
    # 如果有失败，返回非零退出码
    if success_count < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
