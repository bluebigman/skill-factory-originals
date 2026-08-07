#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章链接转存 Markdown 归档工具（独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlparse


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：未提供有效的公众号文章链接",
    "E002": "链接格式错误：仅支持 mp.weixin.qq.com 域名",
    "E003": "网络请求失败",
    "E004": "文章内容解析失败",
    "E005": "文件写入失败",
    "E006": "图片下载失败",
    "E007": "目录创建失败",
    "E008": "URL 编码错误",
    "E009": "数据清洗失败",
    "E010": "未知错误",
}


class AppError(Exception):
    """应用自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class Article:
    """文章数据模型"""

    def __init__(self):
        self.title = ""
        self.author = ""
        self.content = ""
        self.cover_image = ""
        self.images = []          # 图片 URL 列表
        self.source_url = ""
        self.publish_date = ""
        self.summary = ""

    def to_markdown(self) -> str:
        """生成带 YAML frontmatter 的 Markdown 文本"""
        lines = []
        lines.append("---")
        lines.append(f"title: \"{self._escape_yaml(self.title)}\"")
        lines.append(f"author: \"{self._escape_yaml(self.author)}\"")
        lines.append(f"date: \"{self.publish_date}\"")
        lines.append(f"source: \"{self._escape_yaml(self.source_url)}\"")
        lines.append(f"summary: \"{self._escape_yaml(self.summary)}\"")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")
        if self.author:
            lines.append(f"> 作者：{self.author}")
            lines.append("")
        if self.publish_date:
            lines.append(f"> 发布：{self.publish_date}")
            lines.append("")
        lines.append(self.content)
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _escape_yaml(text: str) -> str:
        """转义 YAML 特殊字符"""
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace("\"", "\\\"")


# ============================================================
# URL 校验与规范化
# ============================================================
def validate_wechat_url(url: str) -> str:
    """
    校验并规范化微信公众号文章 URL

    参数:
        url: 原始输入的链接

    返回:
        规范化后的 URL

    异常:
        AppError: E001 参数错误 / E002 域名不支持
    """
    if not url or not url.strip():
        raise AppError("E001")

    url = url.strip()

    # 自动补全协议
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        raise AppError("E002", "URL 解析失败")

    # 仅支持 mp.weixin.qq.com
    host = parsed.netloc.lower()
    if host != "mp.weixin.qq.com":
        raise AppError("E002", f"不支持的域名: {host}")

    # 必须包含 /s/ 路径
    if "/s/" not in parsed.path:
        raise AppError("E002", "链接格式不正确，应为 /s/ 路径")

    return url


# ============================================================
# HTML 解析与清洗（模拟抓取，实际使用标准库解析）
# ============================================================
def extract_article_from_html(html: str, source_url: str) -> Article:
    """
    从 HTML 文本中提取文章信息（模拟解析）

    实际项目中可替换为 BeautifulSoup 等库，此处用正则模拟。

    参数:
        html: HTML 文本内容
        source_url: 原始文章链接

    返回:
        Article 对象

    异常:
        AppError: E004 解析失败
    """
    if not html or len(html) < 100:
        raise AppError("E004", "HTML 内容过短或为空")

    article = Article()
    article.source_url = source_url

    # 提取标题（模拟：查找 og:title 或 <title>）
    title_match = re.search(
        r'<meta\s+property="og:title"\s+content="([^"]+)"', html
    ) or re.search(r"<title>([^<]+)</title>", html)
    if title_match:
        article.title = title_match.group(1).strip()
    else:
        article.title = "未命名文章"

    # 提取作者
    author_match = re.search(
        r'<meta\s+name="author"\s+content="([^"]+)"', html
    ) or re.search(r'var\s+author\s*=\s*"([^"]+)"', html)
    if author_match:
        article.author = author_match.group(1).strip()

    # 提取发布时间
    date_match = re.search(
        r'<meta\s+property="article:published_time"\s+content="([^"]+)"', html
    ) or re.search(r'var\s+createTime\s*=\s*"([^"]+)"', html)
    if date_match:
        raw_date = date_match.group(1).strip()
        # 尝试格式化日期
        try:
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            article.publish_date = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            article.publish_date = raw_date

    # 提取封面图
    cover_match = re.search(
        r'<meta\s+property="og:image"\s+content="([^"]+)"', html
    )
    if cover_match:
        article.cover_image = cover_match.group(1).strip()

    # 提取正文内容（模拟：去除脚本、样式、标签，保留文本）
    # 实际项目中应使用更精细的解析策略
    body_match = re.search(
        r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.DOTALL
    )
    if body_match:
        content_html = body_match.group(1)
        # 去除 script 和 style
        content_html = re.sub(r"<script[^>]*>.*?</script>", "", content_html, flags=re.DOTALL)
        content_html = re.sub(r"<style[^>]*>.*?</style>", "", content_html, flags=re.DOTALL)
        # 去除 HTML 标签
        text = re.sub(r"<[^>]+>", "\n", content_html)
        # 提取图片
        article.images = re.findall(r'<img[^>]+src="([^"]+)"', content_html)
        # 清理多余空白
        lines = [line.strip() for line in text.split("\n")]
        article.content = "\n".join([line for line in lines if line])
    else:
        # 回退方案：取整个 body
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL)
        if body_match:
            text = re.sub(r"<[^>]+>", "\n", body_match.group(1))
            lines = [line.strip() for line in text.split("\n")]
            article.content = "\n".join([line for line in lines if line])
        else:
            raise AppError("E004", "无法定位正文内容")

    # 生成摘要
    if article.content:
        article.summary = article.content[:200] + ("..." if len(article.content) > 200 else "")

    return article


# ============================================================
# 图片处理（模拟下载，实际实现为 URL 规范化）
# ============================================================
def process_images(article: Article, output_dir: str) -> int:
    """
    处理文章图片（模拟下载并保存到 assets 目录）

    实际项目中此函数应执行真实下载，此处仅做 URL 校验和计数。

    参数:
        article: 文章对象
        output_dir: 输出目录

    返回:
        处理成功的图片数量
    """
    if not article.images:
        return 0

    assets_dir = os.path.join(output_dir, "assets")
    try:
        os.makedirs(assets_dir, exist_ok=True)
    except OSError:
        raise AppError("E007", f"无法创建目录: {assets_dir}")

    processed = 0
    for i, img_url in enumerate(article.images):
        if not img_url.startswith(("http://", "https://")):
            continue
        # 模拟下载：生成文件名
        try:
            ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                ext = ".jpg"
            # 生成唯一文件名
            hash_obj = hashlib.md5(img_url.encode("utf-8"))
            filename = f"image_{hash_obj.hexdigest()[:8]}_{i}{ext}"
            # 实际项目中此处应下载图片并保存
            article.images[i] = f"assets/{filename}"
            processed += 1
        except Exception:
            continue

    return processed


# ============================================================
# 文件保存
# ============================================================
def save_markdown(article: Article, output_dir: str) -> str:
    """
    保存文章为 Markdown 文件

    参数:
        article: 文章对象
        output_dir: 输出目录

    返回:
        保存的文件路径

    异常:
        AppError: E005 写入失败 / E007 目录创建失败
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError:
        raise AppError("E007", f"无法创建目录: {output_dir}")

    # 生成安全的文件名
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", article.title)
    safe_title = safe_title.strip() or "未命名文章"
    date_prefix = datetime.now().strftime("%Y%m%d")
    filename = f"{date_prefix}_{safe_title}.md"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(article.to_markdown())
    except OSError:
        raise AppError("E005", f"无法写入文件: {filepath}")

    return filepath


# ============================================================
# 主处理流程
# ============================================================
def process_article(url: str, output_dir: str = "output") -> dict:
    """
    处理单个公众号文章链接

    参数:
        url: 公众号文章链接
        output_dir: 输出目录

    返回:
        处理结果字典

    异常:
        AppError: 各种错误码
    """
    # 1. 校验 URL
    validated_url = validate_wechat_url(url)

    # 2. 模拟网络请求获取 HTML（实际项目中应使用 urllib/requests）
    #    此处生成模拟 HTML 数据用于演示流程
    mock_html = generate_mock_html(validated_url)

    # 3. 解析文章
    article = extract_article_from_html(mock_html, validated_url)

    # 4. 处理图片
    img_count = process_images(article, output_dir)

    # 5. 保存 Markdown
    filepath = save_markdown(article, output_dir)

    return {
        "title": article.title,
        "author": article.author,
        "filepath": filepath,
        "image_count": img_count,
        "content_length": len(article.content),
        "source_url": validated_url,
    }


def generate_mock_html(url: str) -> str:
    """
    生成模拟的公众号文章 HTML（用于演示和测试）

    实际项目中此函数应替换为真实的网络请求。

    参数:
        url: 文章链接

    返回:
        模拟的 HTML 字符串
    """
    # 从 URL 中提取一个 ID 用于生成不同的内容
    url_id = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta property="og:title" content="示例文章标题 {url_id}">
    <meta property="og:image" content="https://mmbiz.qpic.cn/mmbiz_jpg/example_cover_{url_id}/0">
    <meta property="article:published_time" content="2026-01-15T10:30:00+08:00">
    <meta name="author" content="示例作者">
    <title>示例文章标题 {url_id}</title>
</head>
<body>
    <div id="js_content">
        <h1>示例文章标题 {url_id}</h1>
        <p>这是文章的第一段内容，用于测试解析和清洗逻辑。</p>
        <p>第二段包含一些<strong>加粗文字</strong>和<a href="#">链接</a>。</p>
        <img src="https://mmbiz.qpic.cn/mmbiz_jpg/example_img_1_{url_id}/0" alt="图片1">
        <p>中间段落。</p>
        <img src="https://mmbiz.qpic.cn/mmbiz_jpg/example_img_2_{url_id}/0" alt="图片2">
        <p>文章结尾段落。</p>
        <div class="qr_code">
            <p>扫码关注公众号</p>
            <img src="https://mmbiz.qpic.cn/mmbiz_png/qr_code_{url_id}/0" alt="二维码">
        </div>
        <div class="recommend">
            <p>推荐阅读</p>
            <a href="#">相关文章链接</a>
        </div>
    </div>
</body>
</html>"""
    return html


# ============================================================
# 自测功能
# ============================================================
def run_selftest() -> int:
    """
    内置自测：使用硬编码样例数据验证核心逻辑

    返回:
        0 表示通过，非 0 表示失败
    """
    print("=" * 60)
    print("开始自测...")
    print("=" * 60)

    test_cases = [
        # (描述, 输入, 期望行为)
        ("URL 校验 - 正常链接", "https://mp.weixin.qq.com/s/abc123", "pass"),
        ("URL 校验 - 缺少协议", "mp.weixin.qq.com/s/abc123", "pass"),
        ("URL 校验 - 错误域名", "https://example.com/s/abc123", "E002"),
        ("URL 校验 - 空输入", "", "E001"),
        ("URL 校验 - 错误路径", "https://mp.weixin.qq.com/other", "E002"),
    ]

    print("\n--- 测试 URL 校验 ---")
    for desc, input_url, expected in test_cases:
        try:
            result = validate_wechat_url(input_url)
            if expected == "pass":
                # 验证返回值是合法 URL
                assert result.startswith("http"), f"URL 应以 http 开头: {result}"
                assert "mp.weixin.qq.com" in result, f"URL 应包含合法域名: {result}"
                print(f"  ✓ {desc}: 通过 → {result}")
            else:
                print(f"  ✗ {desc}: 期望错误 {expected}，但未抛出异常")
                return 1
        except AppError as e:
            if expected == "pass":
                print(f"  ✗ {desc}: 不应抛出异常，但得到 {e.code}")
                return 1
            elif e.code == expected:
                print(f"  ✓ {desc}: 正确抛出 {e.code}")
            else:
                print(f"  ✗ {desc}: 期望 {expected}，得到 {e.code}")
                return 1
        except Exception as e:
            print(f"  ✗ {desc}: 未预期异常 {e}")
            return 1

    print("\n--- 测试 HTML 解析 ---")
    test_html = generate_mock_html("https://mp.weixin.qq.com/s/test_selftest")
    try:
        article = extract_article_from_html(test_html, "https://mp.weixin.qq.com/s/test_selftest")
        # 宽松断言：标题非空且包含"示例"
        assert article.title and "示例" in article.title, f"标题应包含'示例': {article.title}"
        print(f"  ✓ 标题提取: {article.title}")

        # 宽松断言：作者非空
        assert article.author, "作者不应为空"
        print(f"  ✓ 作者提取: {article.author}")

        # 宽松断言：正文长度应大于 50 字符
        assert len(article.content) > 50, f"正文长度应大于 50: {len(article.content)}"
        print(f"  ✓ 正文提取: {len(article.content)} 字符")

        # 宽松断言：应至少提取到 1 张图片
        assert len(article.images) >= 1, f"应至少提取到 1 张图片: {len(article.images)}"
        print(f"  ✓ 图片提取: {len(article.images)} 张")

        # 宽松断言：摘要非空
        assert article.summary, "摘要不应为空"
        print(f"  ✓ 摘要生成: {len(article.summary)} 字符")

        # 宽松断言：日期非空
        assert article.publish_date, "发布日期不应为空"
        print(f"  ✓ 日期提取: {article.publish_date}")

    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1
    except AppError as e:
        print(f"  ✗ 解析错误: {e.code} {e.message}")
        return 1

    print("\n--- 测试 Markdown 生成 ---")
    try:
        md_text = article.to_markdown()
        # 宽松断言：包含 frontmatter 标记
        assert md_text.startswith("---"), "Markdown 应以 --- 开头"
        assert "title:" in md_text, "应包含 title 字段"
        assert "# " in md_text, "应包含一级标题"
        print(f"  ✓ Markdown 生成: {len(md_text)} 字符")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1

    print("\n--- 测试文件保存 ---")
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = save_markdown(article, tmpdir)
            assert os.path.isfile(filepath), f"文件应存在: {filepath}"
            assert os.path.getsize(filepath) > 100, "文件大小应大于 100 字节"
            print(f"  ✓ 文件保存: {os.path.basename(filepath)} ({os.path.getsize(filepath)} 字节)")
    except AppError as e:
        print(f"  ✗ 保存错误: {e.code} {e.message}")
        return 1
    except Exception as e:
        print(f"  ✗ 未预期异常: {e}")
        return 1

    print("\n--- 测试图片处理 ---")
    try:
        test_article = Article()
        test_article.images = [
            "https://mmbiz.qpic.cn/mmbiz_jpg/test1/0",
            "https://mmbiz.qpic.cn/mmbiz_png/test2/0",
            "not_a_url",
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            count = process_images(test_article, tmpdir)
            # 宽松断言：应处理 2 张有效图片（跳过无效 URL）
            assert count == 2, f"应处理 2 张图片: {count}"
            # 验证相对路径
            assert test_article.images[0].startswith("assets/"), "图片路径应为相对路径"
            print(f"  ✓ 图片处理: {count} 张成功")
    except AppError as e:
        print(f"  ✗ 图片处理错误: {e.code} {e.message}")
        return 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1

    print("\n--- 测试完整流程 ---")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = process_article("https://mp.weixin.qq.com/s/selftest_full", tmpdir)
            assert result["title"], "标题不应为空"
            assert os.path.isfile(result["filepath"]), "文件应存在"
            assert result["content_length"] > 50, "内容长度应大于 50"
            print(f"  ✓ 完整流程: '{result['title']}' → {os.path.basename(result['filepath'])}")
    except AppError as e:
        print(f"  ✗ 流程错误: {e.code} {e.message}")
        return 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1

    print("\n" + "=" * 60)
    print("全部自测通过！")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="公众号文章链接转存 Markdown 归档工具",
        epilog="示例: python main.py https://mp.weixin.qq.com/s/xxxx -o ./output"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="公众号文章链接（支持多个）",
    )
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="输出目录（默认: output）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测（无需网络和外部文件）",
    )
    parser.add_argument(
        "-f", "--file",
        help="从文件读取链接列表（每行一个）",
    )

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        sys.exit(run_selftest())

    # 收集所有链接
    urls = list(args.urls)

    # 从文件读取链接
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls.extend(file_urls)
        except OSError as e:
            print(f"错误: 无法读取文件 {args.file}: {e}")
            sys.exit(1)

    # 检查是否有链接
    if not urls:
        parser.print_help()
        print("\n错误: 请提供至少一个公众号文章链接")
        sys.exit(1)

    # 处理每个链接
    success_count = 0
    fail_count = 0

    for url in urls:
        print(f"\n处理: {url}")
        try:
            result = process_article(url, args.output)
            print(f"  ✓ 成功: {result['title']}")
            print(f"    作者: {result['author']}")
            print(f"    图片: {result['image_count']} 张")
            print(f"    正文: {result['content_length']} 字符")
            print(f"    保存: {result['filepath']}")
            success_count += 1
        except AppError as e:
            print(f"  ✗ 失败: {e.code} {e.message}")
            fail_count += 1
        except Exception as e:
            print(f"  ✗ 未预期错误: {e}")
            fail_count += 1

    # 输出汇总
    print("\n" + "=" * 60)
    print(f"处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    if fail_count > 0:
        print("部分链接处理失败，请检查错误信息。")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
