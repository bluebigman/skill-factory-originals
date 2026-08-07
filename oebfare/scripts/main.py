#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oebfare - 博客数据结构化整理与内容解析工具

功能：
- 从文本/HTML/Markdown 中提取文章元数据（标题、作者、日期、标签）
- 清洗正文内容（去除 HTML 标签、导航噪音）
- 输出结构化 JSON 或 Markdown 表格
- 支持批量文件解析
- 置信度标注（高/中/低）

错误码：
E001 参数错误
E002 文件不存在
E003 文件读取失败
E004 文件编码不支持
E005 目录不存在
E006 目录读取失败
E007 不支持的文件类型
E008 内容解析失败
E009 JSON 序列化失败
E010 未知错误

用法示例：
    python main.py --file article.html
    python main.py --dir ./blogs --format json
    python main.py --selftest
"""

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".html", ".htm", ".txt"}

# 日期格式模式（用于识别常见日期写法）
DATE_PATTERNS = [
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
    r"\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}",
    r"\d{4}年\d{1,2}月\d{1,2}日",
]

# 常见中文/英文标签前缀
TAG_PREFIXES = ["#", "@"]

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"


# ============================================================
# 数据模型
# ============================================================

class ArticleData:
    """文章结构化数据模型"""

    def __init__(self):
        self.title: str = ""
        self.author: str = ""
        self.date: str = ""
        self.tags: List[str] = []
        self.content: str = ""
        self.source: str = ""
        self.confidence: Dict[str, str] = {}

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "tags": self.tags,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 表格行"""
        tags_str = ", ".join(self.tags) if self.tags else "无"
        return (
            f"| {self.title} | {self.author or '未知'} | "
            f"{self.date or '未知'} | {tags_str} | "
            f"{self.confidence.get('title', '中')} |"
        )


# ============================================================
# 核心解析逻辑
# ============================================================

def clean_html(raw_text: str) -> str:
    """
    清洗 HTML 内容，去除标签和脚本，保留纯文本。
    
    参数:
        raw_text: 原始 HTML 文本
    
    返回:
        清洗后的纯文本
    """
    if not raw_text:
        return ""
    
    # 去除 script 和 style 块
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # 去除注释
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    
    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", " ", text)
    
    # 解码 HTML 实体
    text = html.unescape(text)
    
    # 去除多余空白
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


def extract_title(text: str, source: str = "") -> Tuple[str, str]:
    """
    提取文章标题。
    
    策略：
    1. 查找 Markdown 标题（# 开头）
    2. 查找 HTML <title> 标签
    3. 查找 <h1> 标签
    4. 使用第一行作为标题
    
    返回:
        (标题, 置信度)
    """
    if not text:
        return "", CONFIDENCE_LOW
    
    # 检查 HTML title 标签
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        if title:
            return title, CONFIDENCE_HIGH
    
    # 检查 Markdown 一级标题
    md_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if md_match:
        title = md_match.group(1).strip()
        if title:
            return title, CONFIDENCE_HIGH
    
    # 检查 HTML h1
    h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", text, re.IGNORECASE)
    if h1_match:
        title = h1_match.group(1).strip()
        if title:
            return title, CONFIDENCE_HIGH
    
    # 使用第一行非空内容
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        # 去除可能的 Markdown 标记
        first_line = lines[0]
        first_line = re.sub(r"^[#>*\-\s]+", "", first_line)
        if first_line:
            return first_line[:100], CONFIDENCE_MEDIUM
    
    return "未知标题", CONFIDENCE_LOW


def extract_author(text: str) -> Tuple[str, str]:
    """
    提取作者信息。
    
    策略：
    1. 查找 "作者" / "by" / "author" 关键词
    2. 查找 meta 标签
    
    返回:
        (作者, 置信度)
    """
    if not text:
        return "", CONFIDENCE_LOW
    
    # 中文关键词
    cn_match = re.search(r"(?:作者|撰文|原创)[：:\s]*([^\s，。；;]{2,20})", text)
    if cn_match:
        return cn_match.group(1).strip(), CONFIDENCE_HIGH
    
    # 英文关键词
    en_match = re.search(r"(?:by|author)[：:\s]+([A-Za-z][A-Za-z\s\.]{1,30})", text, re.IGNORECASE)
    if en_match:
        return en_match.group(1).strip(), CONFIDENCE_HIGH
    
    # HTML meta 标签
    meta_match = re.search(r'<meta[^>]*name=["\'](?:author|byline)["\'][^>]*content=["\']([^"\']+)["\']', text, re.IGNORECASE)
    if meta_match:
        return meta_match.group(1).strip(), CONFIDENCE_HIGH
    
    return "", CONFIDENCE_LOW


def extract_date(text: str) -> Tuple[str, str]:
    """
    提取发布日期。
    
    策略：
    1. 匹配常见日期格式
    2. 查找 HTML meta 标签
    
    返回:
        (日期字符串, 置信度)
    """
    if not text:
        return "", CONFIDENCE_LOW
    
    # 查找 HTML meta 标签
    meta_match = re.search(r'<meta[^>]*name=["\'](?:date|published|pubdate)["\'][^>]*content=["\']([^"\']+)["\']', text, re.IGNORECASE)
    if meta_match:
        date_str = meta_match.group(1).strip()
        if date_str:
            return date_str, CONFIDENCE_HIGH
    
    # 匹配常见日期格式
    for pattern in DATE_PATTERNS:
        date_match = re.search(pattern, text)
        if date_match:
            date_str = date_match.group(0)
            # 规范化日期格式
            date_str = re.sub(r"年", "-", date_str)
            date_str = re.sub(r"月", "-", date_str)
            date_str = re.sub(r"日", "", date_str)
            date_str = re.sub(r"/", "-", date_str)
            return date_str, CONFIDENCE_HIGH
    
    return "", CONFIDENCE_LOW


def extract_tags(text: str) -> Tuple[List[str], str]:
    """
    提取标签。
    
    策略：
    1. 查找 #标签 或 @标签
    2. 查找 "标签" 关键词行
    
    返回:
        (标签列表, 置信度)
    """
    if not text:
        return [], CONFIDENCE_LOW
    
    tags = []
    
    # 查找 #标签 格式
    hash_tags = re.findall(r"#([\w\u4e00-\u9fff\-]{2,20})", text)
    tags.extend(hash_tags)
    
    # 查找标签关键词行
    tag_line = re.search(r"(?:标签|关键词|tags?)[：:\s]+([^\n]+)", text, re.IGNORECASE)
    if tag_line:
        line_tags = re.split(r"[,，、\s]+", tag_line.group(1).strip())
        tags.extend([t for t in line_tags if t and len(t) <= 20])
    
    # 去重并限制数量
    seen = set()
    unique_tags = []
    for tag in tags:
        tag = tag.strip()
        if tag and tag not in seen and len(unique_tags) < 10:
            seen.add(tag)
            unique_tags.append(tag)
    
    if unique_tags:
        return unique_tags, CONFIDENCE_MEDIUM
    
    return [], CONFIDENCE_LOW


def extract_content(text: str, is_html: bool = False) -> str:
    """
    提取正文内容。
    
    策略：
    1. 如果是 HTML，先清洗
    2. 去除导航噪音（常见导航关键词）
    3. 保留主要段落
    
    返回:
        清洗后的正文
    """
    if not text:
        return "", CONFIDENCE_LOW
    
    content = text
    
    # HTML 清洗
    if is_html or "<html" in text.lower() or "<body" in text.lower():
        content = clean_html(content)
    
    # 去除常见导航噪音
    noise_patterns = [
        r"首页|导航|菜单|关于我们|联系我们|友情链接|版权声明|隐私政策",
        r"Home|Navigation|Menu|About Us|Contact|Links|Copyright|Privacy",
        r"上一篇|下一篇|相关文章|推荐阅读",
        r"Prev|Next|Related|Recommended",
    ]
    
    for pattern in noise_patterns:
        content = re.sub(pattern, "", content, flags=re.IGNORECASE)
    
    # 去除多余空白
    content = re.sub(r"\s+", " ", content).strip()
    
    # 限制长度（前 5000 字符作为正文）
    content = content[:5000]
    
    if content:
        return content, CONFIDENCE_HIGH
    
    return "", CONFIDENCE_LOW


def parse_article(text: str, source: str = "", file_type: str = "") -> ArticleData:
    """
    解析文章文本为结构化数据。
    
    参数:
        text: 文章原始文本
        source: 来源（URL 或文件路径）
        file_type: 文件类型（.md/.html/.txt）
    
    返回:
        ArticleData 对象
    """
    if not text:
        raise ValueError("E008: 内容为空，无法解析")
    
    article = ArticleData()
    article.source = source
    is_html = file_type in (".html", ".htm") or "<html" in text.lower()
    
    # 提取元数据
    article.title, article.confidence["title"] = extract_title(text, source)
    article.author, article.confidence["author"] = extract_author(text)
    article.date, article.confidence["date"] = extract_date(text)
    article.tags, article.confidence["tags"] = extract_tags(text)
    
    # 提取正文
    article.content, article.confidence["content"] = extract_content(text, is_html)
    
    # 如果标题来自第一行，可能包含在正文中，需要去除
    if article.confidence["title"] == CONFIDENCE_MEDIUM and article.content:
        first_sentence = article.content.split("。")[0] if "。" in article.content else article.content.split(".")[0]
        if article.title in first_sentence:
            article.content = article.content.replace(article.title, "", 1).strip()
    
    return article


# ============================================================
# 文件处理
# ============================================================

def read_file(file_path: str) -> Tuple[str, str]:
    """
    读取文件内容。
    
    参数:
        file_path: 文件路径
    
    返回:
        (文件内容, 文件类型)
    
    抛出:
        ValueError: 文件不存在或读取失败
    """
    path = Path(file_path)
    
    # 先检查文件类型（扩展名）
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"E007: 不支持的文件类型: {ext}")
    
    # 再检查文件是否存在
    if not path.exists():
        raise ValueError(f"E002: 文件不存在: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"E002: 路径不是文件: {file_path}")
    
    # 尝试多种编码
    encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
    for encoding in encodings:
        try:
            content = path.read_text(encoding=encoding)
            return content, ext
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise ValueError(f"E003: 文件读取失败: {file_path} - {str(e)}")
    
    raise ValueError(f"E004: 无法识别文件编码: {file_path}")


def process_file(file_path: str, output_format: str = "json") -> Dict:
    """
    处理单个文件。
    
    参数:
        file_path: 文件路径
        output_format: 输出格式 (json/markdown)
    
    返回:
        结构化数据字典
    """
    try:
        content, file_type = read_file(file_path)
        article = parse_article(content, source=file_path, file_type=file_type)
        result = article.to_dict()
        result["_format"] = output_format
        return result
    except ValueError as e:
        return {"error": str(e), "file": file_path}


def process_directory(dir_path: str, output_format: str = "json") -> List[Dict]:
    """
    批量处理目录下的所有支持文件。
    
    参数:
        dir_path: 目录路径
        output_format: 输出格式
    
    返回:
        结构化数据列表
    """
    path = Path(dir_path)
    
    if not path.exists():
        raise ValueError(f"E005: 目录不存在: {dir_path}")
    
    if not path.is_dir():
        raise ValueError(f"E005: 路径不是目录: {dir_path}")
    
    results = []
    try:
        for file_path in sorted(path.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                result = process_file(str(file_path), output_format)
                results.append(result)
    except PermissionError as e:
        raise ValueError(f"E006: 目录读取失败: {dir_path} - {str(e)}")
    
    return results


# ============================================================
# 输出格式化
# ============================================================

def format_output(data, output_format: str = "json") -> str:
    """
    格式化输出。
    
    参数:
        data: 结构化数据（字典或列表）
        output_format: 输出格式 (json/markdown)
    
    返回:
        格式化后的字符串
    """
    if output_format == "json":
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ValueError(f"E009: JSON 序列化失败 - {str(e)}")
    
    elif output_format == "markdown":
        if isinstance(data, dict):
            data = [data]
        
        lines = ["| 标题 | 作者 | 日期 | 标签 | 置信度 |", "|------|------|------|------|--------|"]
        for item in data:
            if "error" in item:
                lines.append(f"| 错误 | {item.get('file', '未知')} | - | - | {item['error']} |")
            else:
                tags_str = ", ".join(item.get("tags", [])) if item.get("tags") else "无"
                confidence = item.get("confidence", {})
                conf_str = confidence.get("title", "中")
                lines.append(
                    f"| {item.get('title', '未知')} | {item.get('author', '未知')} | "
                    f"{item.get('date', '未知')} | {tags_str} | {conf_str} |"
                )
        return "\n".join(lines)
    
    else:
        raise ValueError(f"E001: 不支持的输出格式: {output_format}")


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。
    
    使用硬编码样例数据，不依赖外部文件或网络。
    
    返回:
        True 表示所有测试通过
    """
    print("=" * 60)
    print("oebfare 自检程序")
    print("=" * 60)
    
    all_passed = True
    
    # 测试用例 1: HTML 文章
    print("\n[测试 1] HTML 文章解析")
    html_sample = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>深入理解 Python 装饰器</title>
        <meta name="author" content="张三">
        <meta name="date" content="2025-03-15">
    </head>
    <body>
        <nav>首页 | 导航 | 关于我们</nav>
        <h1>深入理解 Python 装饰器</h1>
        <p>装饰器是 Python 中强大的功能，允许在不修改原函数的情况下增强其功能。</p>
        <p>本文将从基础概念讲起，逐步深入。</p>
        <div>版权声明 2025</div>
    </body>
    </html>
    """
    try:
        article = parse_article(html_sample, source="test.html", file_type=".html")
        print(f"  标题: {article.title}")
        print(f"  作者: {article.author}")
        print(f"  日期: {article.date}")
        print(f"  标签: {article.tags}")
        print(f"  正文长度: {len(article.content)}")
        
        # 宽松断言
        assert article.title, "标题不应为空"
        assert "装饰器" in article.title or "Python" in article.title, "标题应包含关键词"
        assert article.author == "张三", "作者应为张三"
        assert article.date, "日期不应为空"
        assert len(article.content) > 50, "正文应有一定长度"
        assert "首页" not in article.content, "导航噪音应被清除"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        all_passed = False
    
    # 测试用例 2: Markdown 文章
    print("\n[测试 2] Markdown 文章解析")
    md_sample = """# 我的第一篇博客文章

作者：李四

日期：2025年1月20日

标签：#Python #教程 #入门

## 引言

这是一篇关于 Python 入门的博客文章，适合初学者阅读。

## 正文

Python 是一种简单易学的编程语言，广泛应用于数据分析、Web 开发等领域。
"""
    try:
        article = parse_article(md_sample, source="test.md", file_type=".md")
        print(f"  标题: {article.title}")
        print(f"  作者: {article.author}")
        print(f"  日期: {article.date}")
        print(f"  标签: {article.tags}")
        
        # 宽松断言
        assert article.title, "标题不应为空"
        assert "Python" in article.title or "博客" in article.title, "标题应包含关键词"
        assert len(article.tags) >= 2, "至少应有2个标签"
        assert article.date, "日期不应为空"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        all_passed = False
    
    # 测试用例 3: 纯文本文章
    print("\n[测试 3] 纯文本文章解析")
    txt_sample = """今天学习 Python 的列表推导式

作者：王五

标签：#Python #技巧

列表推导式是 Python 中非常实用的特性，可以用一行代码完成循环和条件筛选。

例如：[x * 2 for x in range(10) if x % 2 == 0]
"""
    try:
        article = parse_article(txt_sample, source="test.txt", file_type=".txt")
        print(f"  标题: {article.title}")
        print(f"  作者: {article.author}")
        print(f"  标签: {article.tags}")
        
        # 宽松断言
        assert article.title, "标题不应为空"
        assert len(article.content) > 30, "正文应有一定长度"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        all_passed = False
    
    # 测试用例 4: 批量处理（模拟目录）
    print("\n[测试 4] 批量处理与输出格式")
    try:
        # 模拟批量结果
        sample_results = [
            {"title": "文章A", "author": "作者1", "date": "2025-01-01", "tags": ["Python"], "content": "内容A", "confidence": {"title": "高"}},
            {"title": "文章B", "author": "作者2", "date": "2025-02-01", "tags": ["Java"], "content": "内容B", "confidence": {"title": "高"}},
        ]
        
        # 测试 JSON 输出
        json_out = format_output(sample_results, "json")
        assert json_out, "JSON 输出不应为空"
        assert "文章A" in json_out, "JSON 应包含文章A"
        print(f"  JSON 输出长度: {len(json_out)}")
        
        # 测试 Markdown 输出
        md_out = format_output(sample_results, "markdown")
        assert md_out, "Markdown 输出不应为空"
        assert "|" in md_out, "Markdown 应包含表格符号"
        print(f"  Markdown 输出行数: {len(md_out.splitlines())}")
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        all_passed = False
    
    # 测试用例 5: HTML 清洗
    print("\n[测试 5] HTML 内容清洗")
    dirty_html = "<div><p>第一段内容</p><script>alert('xss')</script><style>body{color:red}</style><p>第二段内容</p></div>"
    try:
        cleaned = clean_html(dirty_html)
        print(f"  清洗结果: {cleaned}")
        assert "第一段" in cleaned, "应保留第一段内容"
        assert "第二段" in cleaned, "应保留第二段内容"
        assert "script" not in cleaned.lower(), "不应包含 script 标签"
        assert "style" not in cleaned.lower(), "不应包含 style 标签"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        all_passed = False
    
    # 测试用例 6: 错误处理
    print("\n[测试 6] 错误处理")
    try:
        # 不存在的文件
        try:
            read_file("/nonexistent/path/file.md")
            print("  ✗ 失败: 应抛出文件不存在错误")
            all_passed = False
        except ValueError as e:
            assert "E002" in str(e), "错误码应为 E002"
            print(f"  ✓ 文件不存在错误: {str(e)[:50]}...")
        
        # 不支持的文件类型
        try:
            read_file("test.xyz")
            print("  ✗ 失败: 应抛出文件类型错误")
            all_passed = False
        except ValueError as e:
            assert "E007" in str(e), "错误码应为 E007"
            print(f"  ✓ 文件类型错误: {str(e)[:50]}...")
        
        # 空内容解析
        try:
            parse_article("", source="empty.txt", file_type=".txt")
            print("  ✗ 失败: 应抛出空内容错误")
            all_passed = False
        except ValueError as e:
            assert "E008" in str(e), "错误码应为 E008"
            print(f"  ✓ 空内容错误: {str(e)[:50]}...")
        
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        all_passed = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="oebfare - 博客数据结构化整理与内容解析工具",
        epilog="示例: python main.py --file article.html --format json"
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", "-f", help="要解析的单个文件路径")
    input_group.add_argument("--dir", "-d", help="要批量解析的目录路径")
    input_group.add_argument("--text", "-t", help="直接传入文本内容进行解析")
    
    # 输出参数
    parser.add_argument("--format", "-fmt", choices=["json", "markdown"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--output", "-o", help="输出文件路径（可选）")
    
    # 自检参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检程序")
    
    # 版本参数
    parser.add_argument("--version", "-v", action="version", version="oebfare 1.0.1")
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查输入参数
    if not args.file and not args.dir and not args.text:
        parser.print_help()
        sys.exit(1)
    
    try:
        # 处理输入
        if args.file:
            result = process_file(args.file, args.format)
            output = format_output(result, args.format)
        elif args.dir:
            results = process_directory(args.dir, args.format)
            output = format_output(results, args.format)
        elif args.text:
            article = parse_article(args.text, source="<直接输入>", file_type=".txt")
            result = article.to_dict()
            output = format_output(result, args.format)
        else:
            raise ValueError("E001: 未指定输入")
        
        # 输出结果
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"结果已写入: {args.output}")
        else:
            print(output)
    
    except ValueError as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E010: 未知错误 - {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
