#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章归档技能 - 独立实现脚本
基于功能规格 clean-room 重写，不复制任何既有代码。
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件写入失败，请检查权限",
    "E007": "ZIP 打包失败，请检查文件",
    "E008": "图片下载失败，请检查 URL",
    "E009": "Markdown 渲染失败，请检查内容",
    "E010": "内部校验失败，请重试",
}


class ArticleArchiveError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def extract_text_from_html(html_content: str) -> str:
    """从 HTML 中提取纯文本（简易实现）。"""
    # 移除 script/style 标签及其内容
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码常见 HTML 实体
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    # 压缩空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_images_from_html(html_content: str) -> list:
    """从 HTML 中提取图片 URL 列表。"""
    # 匹配 img 标签的 src 属性（支持单双引号）
    pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
    return pattern.findall(html_content)


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符。"""
    # 替换 Windows/Unix 非法字符
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    # 去除首尾空白和点号
    cleaned = cleaned.strip().strip('.')
    # 限制长度
    if len(cleaned) > 100:
        cleaned = cleaned[:100]
    return cleaned or "untitled"


def get_image_extension(url: str) -> str:
    """从 URL 推断图片扩展名。"""
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'):
        return ext
    return '.jpg'  # 默认


def download_image(url: str, timeout: int = 10) -> bytes:
    """下载图片数据（简化实现，支持 data URI）。"""
    if url.startswith('data:'):
        # data URI 格式: data:image/png;base64,xxxx
        try:
            header, data = url.split(',', 1)
            if 'base64' in header:
                return base64.b64decode(data)
            return data.encode('utf-8')
        except Exception as e:
            raise ArticleArchiveError("E008", f"data URI 解析失败: {e}")

    # 仅支持本地文件路径，不访问网络（规格要求）
    if url.startswith('file://'):
        path = urlparse(url).path
        try:
            with open(path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise ArticleArchiveError("E008", f"图片读取失败: {e}")

    # 其他情况视为无法访问
    raise ArticleArchiveError("E008", f"不支持的图片来源（不访问网络）: {url}")


def render_markdown(title: str, author: str, content_html: str, images: list, confidence: float) -> str:
    """将文章内容渲染为 Markdown 格式。"""
    # 提取纯文本
    text_content = extract_text_from_html(content_html)

    # 构建 Markdown
    lines = []
    lines.append(f"# {title}\n")
    if author:
        lines.append(f"> 作者：{author}\n")
    lines.append(f"> 归档时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    lines.append(f"> 置信度：{confidence:.0%}\n")

    if confidence < 0.85:
        lines.append(f"> ⚠️ [需核实] 本结果置信度较低，请人工复核。\n")
    elif confidence < 0.90:
        lines.append(f"> ⚠️ 建议复核：本结果置信度中等。\n")

    lines.append("---\n")

    # 添加图片引用
    if images:
        lines.append("## 图片\n")
        for i, img in enumerate(images, 1):
            lines.append(f"![图片{i}]({img})\n")

    lines.append("## 正文\n")
    lines.append(text_content)
    lines.append("")

    return "\n".join(lines)


def validate_and_package(markdown_content: str, images_dir: str, output_zip: str) -> bool:
    """验证 Markdown 并打包为 ZIP。"""
    try:
        # 验证 Markdown 基本结构
        if not markdown_content.strip():
            raise ArticleArchiveError("E009", "Markdown 内容为空")

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            md_file = temp_path / "article.md"
            md_file.write_text(markdown_content, encoding='utf-8')

            # 复制图片（如果有）
            img_files = []
            if images_dir and os.path.isdir(images_dir):
                for f in os.listdir(images_dir):
                    src = os.path.join(images_dir, f)
                    if os.path.isfile(src):
                        dst = temp_path / "images" / f
                        dst.parent.mkdir(exist_ok=True)
                        import shutil
                        shutil.copy2(src, dst)
                        img_files.append(dst)

            # 打包 ZIP
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(md_file, "article.md")
                for img in img_files:
                    zf.write(img, f"images/{img.name}")

            return True

    except ArticleArchiveError:
        raise
    except Exception as e:
        raise ArticleArchiveError("E007", f"ZIP 打包失败: {e}")


def process_article(article_data: dict) -> dict:
    """处理单篇文章，返回结构化结果。"""
    # 输入校验
    if not article_data:
        raise ArticleArchiveError("E001")

    title = article_data.get("title", "").strip()
    author = article_data.get("author", "").strip()
    content = article_data.get("content", "").strip()

    if not title:
        raise ArticleArchiveError("E002", "缺少标题")
    if not content:
        raise ArticleArchiveError("E002", "缺少正文内容")

    # 提取图片
    images = extract_images_from_html(content)

    # 计算置信度（基于内容完整性）
    confidence = 0.95
    if not author:
        confidence -= 0.05
    if not images:
        confidence -= 0.05
    if len(content) < 100:
        confidence -= 0.10

    confidence = max(0.0, min(1.0, confidence))

    # 生成 Markdown
    md_content = render_markdown(title, author, content, images, confidence)

    # 返回结果
    return {
        "title": title,
        "author": author,
        "confidence": confidence,
        "images": images,
        "markdown": md_content,
        "status": "success" if confidence >= 0.85 else "needs_review",
    }


def run_selftest() -> bool:
    """内置硬编码样例数据自检核心逻辑。"""
    print("=== 开始自检 ===\n")

    # 测试数据（硬编码，不依赖外部文件）
    test_html = """
    <html>
    <head><title>测试文章</title></head>
    <body>
        <h1>测试标题</h1>
        <p>这是一段测试正文内容，包含足够长的文字来满足置信度计算要求。</p>
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==" />
        <p>更多正文内容，确保长度超过100字符。这里继续添加一些文字来凑数。</p>
    </body>
    </html>
    """

    test_article = {
        "title": "测试公众号文章",
        "author": "测试作者",
        "content": test_html,
    }

    # 测试1: 文本提取
    print("测试1: HTML 文本提取...")
    text = extract_text_from_html(test_html)
    assert len(text) > 50, "文本提取失败：内容过短"
    assert "测试标题" in text, "文本提取失败：缺少标题内容"
    print("  通过 ✓")

    # 测试2: 图片提取
    print("测试2: 图片 URL 提取...")
    images = extract_images_from_html(test_html)
    assert len(images) >= 1, "图片提取失败：未找到图片"
    assert images[0].startswith("data:"), "图片提取失败：data URI 未识别"
    print("  通过 ✓")

    # 测试3: 文章处理
    print("测试3: 文章处理流程...")
    result = process_article(test_article)
    assert result["status"] in ("success", "needs_review"), "处理状态异常"
    assert result["confidence"] >= 0.5, "置信度计算异常"
    assert "# 测试公众号文章" in result["markdown"], "Markdown 渲染失败：缺少标题"
    assert "![图片1]" in result["markdown"], "Markdown 渲染失败：缺少图片引用"
    print(f"  通过 ✓ (置信度: {result['confidence']:.2%})")

    # 测试4: 错误处理
    print("测试4: 错误处理...")
    try:
        process_article({})
        assert False, "空输入未抛出异常"
    except ArticleArchiveError as e:
        assert e.code == "E001", f"错误码错误: {e.code}"
    print("  通过 ✓")

    # 测试5: 文件名清理
    print("测试5: 文件名清理...")
    bad_name = 'test<>:"/\\|?*name'
    clean = sanitize_filename(bad_name)
    assert clean == "test_________name", f"文件名清理失败: {clean}"
    assert not any(c in clean for c in '<>:"/\\|?*'), "文件名包含非法字符"
    print("  通过 ✓")

    # 测试6: ZIP 打包
    print("测试6: ZIP 打包验证...")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "test.zip")
        ok = validate_and_package(result["markdown"], None, zip_path)
        assert ok, "ZIP 打包失败"
        assert os.path.exists(zip_path), "ZIP 文件未生成"
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            assert "article.md" in names, "ZIP 中缺少 article.md"
    print("  通过 ✓")

    print("\n=== 全部自检通过 ✓ ===")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="公众号文章归档工具 - 将 HTML 内容转换为 Markdown 并打包"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--input", help="输入 HTML 文件路径")
    parser.add_argument("--output", help="输出 ZIP 文件路径")
    parser.add_argument("--json", dest="json_input", help="输入 JSON 文件路径（包含文章数据）")
    parser.add_argument("--title", help="文章标题（覆盖输入中的标题）")
    parser.add_argument("--author", help="文章作者")
    parser.add_argument("--images-dir", help="图片目录（用于打包）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"\n自检失败: {e}")
            sys.exit(1)

    # 正常处理模式
    try:
        # 获取输入
        if args.json_input:
            # 从 JSON 文件读取
            with open(args.json_input, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
        elif args.input:
            # 从 HTML 文件读取
            with open(args.input, 'r', encoding='utf-8') as f:
                html_content = f.read()
            article_data = {
                "title": args.title or Path(args.input).stem,
                "author": args.author or "",
                "content": html_content,
            }
        else:
            # 无输入则显示帮助
            parser.print_help()
            sys.exit(0)

        # 覆盖标题/作者（如果指定）
        if args.title:
            article_data["title"] = args.title
        if args.author:
            article_data["author"] = args.author

        # 处理文章
        result = process_article(article_data)

        # 输出结果
        output_path = args.output or f"{sanitize_filename(result['title'])}.zip"
        ok = validate_and_package(result["markdown"], args.images_dir, output_path)

        if ok:
            print(f"✓ 处理成功: {result['title']}")
            print(f"  置信度: {result['confidence']:.1%}")
            print(f"  图片数: {len(result['images'])}")
            print(f"  输出: {output_path}")
            if result["confidence"] < 0.85:
                print("  ⚠️ [需核实] 置信度较低，请人工复核")
            elif result["confidence"] < 0.90:
                print("  ⚠️ 建议复核")
        else:
            raise ArticleArchiveError("E007", "打包失败")

    except ArticleArchiveError as e:
        print(f"错误 {e.code}: {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"错误 E010: 内部错误 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
