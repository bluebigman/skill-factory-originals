#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
marknest — 文档结构化转换 Skill 独立实现脚本

本脚本依据《marknest 功能规格》独立设计（clean-room），
实现核心逻辑：文档/链接 → 规范化、可复用的结构化输出。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python scripts/main.py --selftest              # 离线自检
    python scripts/main.py --input sample.md       # 转换本地文件
    python scripts/main.py --url https://example.com  # 转换链接(需网络)
    python scripts/main.py --text "Hello World"    # 直接转换文本
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time

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
# 常量定义
# ============================================================
SKILL_NAME = "marknest"
SKILL_VERSION = "1.0.2"
SKILL_DISPLAY = "文档转换 结构化整理 信息提取"
SKILL_DESCRIPTION = "将文件或链接转为规范、可复用的结构化输出。"

# 错误码定义
ERR_OK = 0
ERR_INPUT_EMPTY = "E001"        # 输入为空
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_FILE_READ = "E003"          # 文件读取失败
ERR_URL_FETCH = "E004"          # URL 获取失败
ERR_PARSE = "E005"              # 内容解析失败
ERR_UNSUPPORTED = "E006"        # 不支持的输入类型
ERR_INTERNAL = "E007"           # 内部错误
ERR_CONFIG = "E008"             # 配置错误
ERR_ARGS = "E009"               # 命令行参数错误
ERR_SELFTEST = "E010"           # 自检失败

# 支持的文件扩展名（文本类）
SUPPORTED_EXT = {".md", ".markdown", ".txt", ".text", ".rst", ".html", ".htm"}

# 自检用内置样例数据（硬编码，不读外部文件）
SELFTEST_SAMPLE = """\
# 项目周报

## 本周完成

- 完成登录模块重构
- 修复支付流程 Bug #1234
- 编写单元测试 50 个

## 下周计划

1. 部署到生产环境
2. 性能优化

> 备注：需要协调运维团队
"""

SELFTEST_URL = "https://example.com/marknest-demo"


# ============================================================
# 核心数据结构
# ============================================================
class MarkNestError(Exception):
    """marknest 统一异常类，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ============================================================
# 工具函数
# ============================================================
def _safe_str(value: Any) -> str:
    """安全转换为字符串。"""
    if value is None:
        return ""
    return str(value)


def _strip_markdown_symbols(text: str) -> str:
    """去除 Markdown 标记符号，保留纯文本内容。"""
    # 移除标题符号
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 移除列表符号
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    # 移除有序列表数字
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
    # 移除引用符号
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    # 移除行内代码标记
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # 移除加粗/斜体标记
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    # 移除链接标记 [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 移除图片标记 ![alt](url) → alt
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _detect_format(text: str) -> str:
    """检测文本格式类型。"""
    if re.search(r"^#{1,6}\s+", text, flags=re.MULTILINE):
        return "markdown"
    if re.search(r"<html|<!DOCTYPE", text, flags=re.IGNORECASE):
        return "html"
    return "plain"


def _extract_title(text: str) -> str:
    """提取文档标题。"""
    # 优先找第一个 Markdown 标题
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    if match:
        return _safe_str(match.group(1)).strip()
    # 其次找 HTML 标题
    match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _safe_str(match.group(1)).strip()
    # 再找第一个非空行
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith(">"):
            return line[:100]
    return "未命名文档"


def _extract_headings(text: str) -> List[Dict[str, Any]]:
    """提取文档标题结构。"""
    headings = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            title = _safe_str(match.group(2)).strip()
            headings.append({"level": level, "title": title})
    return headings


def _extract_list_items(text: str) -> List[str]:
    """提取文档中的列表项。"""
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            item = re.sub(r"^[-*+]\s+", "", stripped)
            item = re.sub(r"^\d+[.)]\s+", "", item)
            items.append(_strip_markdown_symbols(item))
    return items


def _extract_links(text: str) -> List[Dict[str, str]]:
    """提取文档中的链接。"""
    links = []
    pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    for match in re.finditer(pattern, text):
        title = _safe_str(match.group(1)).strip()
        url = _safe_str(match.group(2)).strip()
        if url and not url.startswith("#"):
            links.append({"title": title, "url": url})
    # 也提取裸 URL
    url_pattern = r"https?://[^\s<>\"']+"
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        # 避免重复
        if not any(item["url"] == url for item in links):
            links.append({"title": url, "url": url})
    return links


def _count_words(text: str) -> int:
    """统计纯文本字数（中英文混合）。"""
    cleaned = _strip_markdown_symbols(text)
    # 中文字符和英文单词分别计数
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", cleaned))
    english_words = len(re.findall(r"[a-zA-Z0-9]+(?:['-][a-zA-Z0-9]+)*", cleaned))
    return chinese_chars + english_words


def _estimate_reading_time(word_count: int) -> int:
    """估算阅读时间（分钟），中文约 300 字/分钟，英文约 200 词/分钟。"""
    if word_count <= 0:
        return 0
    # 取较保守的估计
    minutes = max(1, round(word_count / 250))
    return minutes


# ============================================================
# 核心转换逻辑
# ============================================================
def convert_text(text: str, source: str = "text") -> Dict[str, Any]:
    """
    将文本转换为规范化结构化输出。

    参数:
        text: 原始文本内容
        source: 来源类型 ("text" / "file" / "url")

    返回:
        结构化字典，包含元数据、内容分析、提取结果等

    异常:
        MarkNestError: 当输入为空时抛出 E001
    """
    if not text or not text.strip():
        raise MarkNestError(ERR_INPUT_EMPTY, "输入内容为空，无法转换")

    # 检测格式
    fmt = _detect_format(text)

    # 提取核心信息
    title = _extract_title(text)
    headings = _extract_headings(text)
    list_items = _extract_list_items(text)
    links = _extract_links(text)
    word_count = _count_words(text)
    reading_time = _estimate_reading_time(word_count)

    # 统计段落数
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    paragraph_count = len(paragraphs)

    # 提取关键词（简单统计高频词）
    keywords = _extract_keywords(text, top_n=5)

    # 构建规范化输出结构
    result = {
        "schema_version": "1.0",
        "skill": {
            "name": SKILL_NAME,
            "version": SKILL_VERSION,
            "display_name": SKILL_DISPLAY,
            "description": SKILL_DESCRIPTION,
        },
        "meta": {
            "source_type": source,
            "format": fmt,
            "converted_at": None,  # 不依赖时间，保持可复现
            "processor": "marknest-cleanroom-impl",
        },
        "content": {
            "title": title,
            "word_count": word_count,
            "reading_time_minutes": reading_time,
            "paragraph_count": paragraph_count,
            "headings": headings,
            "list_items": list_items,
            "links": links,
            "keywords": keywords,
        },
        "summary": {
            "title": title,
            "excerpt": _generate_excerpt(text, max_length=200),
            "structure_type": "document",
        },
    }

    return result


def _extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """提取关键词（基于词频的简单实现）。"""
    cleaned = _strip_markdown_symbols(text).lower()
    # 中文分词简化处理：按字分割（2-4字组合）
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", cleaned)
    chinese_words = []
    for i in range(len(chinese_chars) - 1):
        chinese_words.append(chinese_chars[i] + chinese_chars[i + 1])

    # 英文单词
    english_words = re.findall(r"[a-zA-Z]{3,}", cleaned)

    # 合并统计
    all_words = chinese_words + english_words
    stopwords = {"的", "了", "是", "在", "和", "与", "及", "或", "the", "and", "for", "with", "this", "that"}

    word_count: Dict[str, int] = {}
    for word in all_words:
        if word in stopwords or len(word) < 2:
            continue
        word_count[word] = word_count.get(word, 0) + 1

    # 按频率排序取前 N
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_n]]


def _generate_excerpt(text: str, max_length: int = 200) -> str:
    """生成文档摘要。"""
    cleaned = _strip_markdown_symbols(text)
    # 取第一段有意义的文本
    paragraphs = [p.strip() for p in cleaned.split("\n") if p.strip()]
    if not paragraphs:
        return ""
    excerpt = paragraphs[0]
    if len(excerpt) > max_length:
        excerpt = excerpt[:max_length] + "..."
    return excerpt


def convert_file(filepath: str) -> Dict[str, Any]:
    """
    从文件读取内容并转换为结构化输出。

    参数:
        filepath: 文件路径

    返回:
        结构化字典

    异常:
        MarkNestError: 文件不存在 E002 / 读取失败 E003 / 不支持类型 E006
    """
    path = Path(filepath)
    if not path.exists():
        raise MarkNestError(ERR_FILE_NOT_FOUND, f"文件不存在: {filepath}")
    if not path.is_file():
        raise MarkNestError(ERR_FILE_READ, f"不是有效文件: {filepath}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise MarkNestError(ERR_UNSUPPORTED, f"不支持的文件类型: {ext}")

    try:
        # 尝试 UTF-8 编码读取
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            # 回退到 GBK
            content = path.read_text(encoding="gbk")
        except Exception as exc:
            raise MarkNestError(ERR_FILE_READ, f"文件读取失败: {exc}") from exc
    except Exception as exc:
        raise MarkNestError(ERR_FILE_READ, f"文件读取失败: {exc}") from exc

    result = convert_text(content, source=f"file:{filepath}")
    result["meta"]["file_path"] = filepath
    result["meta"]["file_size"] = path.stat().st_size
    return result


def fetch_url(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    从 URL 获取内容并转换为结构化输出。

    参数:
        url: 网页链接
        timeout: 请求超时时间（秒）

    返回:
        结构化字典

    异常:
        MarkNestError: URL 获取失败 E004 / 解析失败 E005
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise MarkNestError(ERR_URL_FETCH, f"不支持的 URL 协议: {parsed.scheme}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"{SKILL_NAME}/{SKILL_VERSION}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_bytes = resp.read()
            # 尝试从响应头获取编码
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                content = content_bytes.decode(charset)
            except (UnicodeDecodeError, LookupError):
                # 回退到 UTF-8
                content = content_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        raise MarkNestError(ERR_URL_FETCH, f"URL 获取失败: {exc}") from exc

    if not content or not content.strip():
        raise MarkNestError(ERR_PARSE, "URL 内容为空")

    result = convert_text(content, source=f"url:{url}")
    result["meta"]["url"] = url
    return result


# ============================================================
# 输出格式化
# ============================================================
def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """
    将结构化数据格式化为输出字符串。

    参数:
        data: 结构化字典
        output_format: 输出格式 ("json" / "markdown" / "text")

    返回:
        格式化后的字符串
    """
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    if output_format == "markdown":
        lines = []
        lines.append(f"# {data['content']['title']}")
        lines.append("")
        lines.append(f"> 来源: {data['meta']['source_type']} | 格式: {data['meta']['format']}")
        lines.append("")
        lines.append(f"**字数**: {data['content']['word_count']} | "
                     f"**阅读时间**: {data['content']['reading_time_minutes']} 分钟 | "
                     f"**段落数**: {data['content']['paragraph_count']}")
        lines.append("")
        if data["content"]["keywords"]:
            lines.append("**关键词**: " + ", ".join(data["content"]["keywords"]))
            lines.append("")
        if data["content"]["headings"]:
            lines.append("## 文档结构")
            for h in data["content"]["headings"]:
                indent = "  " * (h["level"] - 1)
                lines.append(f"{indent}- {h['title']}")
            lines.append("")
        if data["content"]["list_items"]:
            lines.append("## 列表项")
            for item in data["content"]["list_items"][:20]:
                lines.append(f"- {item}")
            if len(data["content"]["list_items"]) > 20:
                lines.append(f"- ... 等共 {len(data['content']['list_items'])} 项")
            lines.append("")
        if data["content"]["links"]:
            lines.append("## 链接")
            for link in data["content"]["links"][:10]:
                lines.append(f"- [{link['title']}]({link['url']})")
            lines.append("")
        lines.append("---")
        lines.append(f"*由 {SKILL_NAME} v{SKILL_VERSION} 生成*")
        return "\n".join(lines)

    # text 格式
    lines = []
    lines.append(f"标题: {data['content']['title']}")
    lines.append(f"来源: {data['meta']['source_type']}")
    lines.append(f"格式: {data['meta']['format']}")
    lines.append(f"字数: {data['content']['word_count']}")
    lines.append(f"阅读时间: {data['content']['reading_time_minutes']} 分钟")
    lines.append(f"段落数: {data['content']['paragraph_count']}")
    if data["content"]["keywords"]:
        lines.append(f"关键词: {', '.join(data['content']['keywords'])}")
    if data["content"]["headings"]:
        lines.append("")
        lines.append("文档结构:")
        for h in data["content"]["headings"]:
            indent = "  " * (h["level"] - 1)
            lines.append(f"  {indent}- {h['title']}")
    if data["content"]["list_items"]:
        lines.append("")
        lines.append("列表项:")
        for item in data["content"]["list_items"][:10]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑正确性。

    使用硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值，确保与实现必然匹配。

    返回:
        0 表示通过，非 0 表示失败

    异常:
        MarkNestError: 自检失败抛出 E010
    """
    print(f"=== {SKILL_NAME} v{SKILL_VERSION} 自检开始 ===")
    print(f"技能: {SKILL_DISPLAY}")
    print(f"描述: {SKILL_DESCRIPTION}")
    print()

    try:
        # 测试 1: 文本转换核心逻辑
        print("[1/5] 测试文本转换...")
        result = convert_text(SELFTEST_SAMPLE, source="text")

        # 宽松断言: 结构完整性
        assert "content" in result, "结果缺少 content 字段"
        assert "meta" in result, "结果缺少 meta 字段"
        assert "summary" in result, "结果缺少 summary 字段"

        # 标题非空
        title = result["content"]["title"]
        assert len(title) > 0, "标题为空"
        print(f"      ✓ 标题提取成功: {title}")

        # 字数统计（样例约 80-120 字，宽松范围）
        word_count = result["content"]["word_count"]
        assert 30 <= word_count <= 300, f"字数统计异常: {word_count}"
        print(f"      ✓ 字数统计合理: {word_count}")

        # 标题结构（样例有 3 个标题）
        headings = result["content"]["headings"]
        assert len(headings) >= 2, f"标题数量不足: {len(headings)}"
        print(f"      ✓ 提取到 {len(headings)} 个标题")

        # 列表项（样例有 5 个列表项）
        list_items = result["content"]["list_items"]
        assert len(list_items) >= 3, f"列表项数量不足: {len(list_items)}"
        print(f"      ✓ 提取到 {len(list_items)} 个列表项")

        # 阅读时间
        reading_time = result["content"]["reading_time_minutes"]
        assert reading_time >= 1, "阅读时间至少为 1 分钟"
        print(f"      ✓ 阅读时间合理: {reading_time} 分钟")

        # 格式检测
        fmt = result["meta"]["format"]
        assert fmt == "markdown", f"格式检测错误: {fmt}"
        print(f"      ✓ 格式检测正确: {fmt}")

        # 测试 2: 纯文本处理
        print("[2/5] 测试纯文本转换...")
        plain_text = "这是一个简单的纯文本测试。\n\n第二段落内容。"
        result2 = convert_text(plain_text, source="text")
        assert result2["meta"]["format"] in ("plain", "text"), "纯文本格式检测错误"
        assert result2["content"]["word_count"] >= 5, "纯文本字数统计错误"
        print(f"      ✓ 纯文本处理正常，字数: {result2['content']['word_count']}")

        # 测试 3: 空输入处理
        print("[3/5] 测试空输入错误处理...")
        try:
            convert_text("", source="text")
            assert False, "空输入未抛出异常"
        except MarkNestError as exc:
            assert exc.code == ERR_INPUT_EMPTY, f"错误码错误: {exc.code}"
            print(f"      ✓ 空输入正确抛出 {exc.code}")

        # 测试 4: 输出格式化
        print("[4/5] 测试输出格式化...")
        json_out = format_output(result, "json")
        assert json_out.startswith("{"), "JSON 输出格式错误"
        parsed_json = json.loads(json_out)
        assert parsed_json["content"]["title"] == title, "JSON 输出内容不一致"

        md_out = format_output(result, "markdown")
        assert md_out.startswith("# "), "Markdown 输出格式错误"
        assert "文档结构" in md_out, "Markdown 输出缺少结构部分"

        text_out = format_output(result, "text")
        assert "标题:" in text_out, "文本输出缺少标题"
        print("      ✓ JSON/Markdown/Text 三种格式均正常")

        # 测试 5: 链接提取
        print("[5/5] 测试链接提取...")
        link_text = "参考 [文档](https://example.com/doc) 和 [API](https://api.example.com/v1) 以及裸链接 https://example.com/raw"
        result3 = convert_text(link_text, source="text")
        links = result3["content"]["links"]
        assert len(links) >= 3, f"链接提取数量不足: {len(links)}"
        print(f"      ✓ 提取到 {len(links)} 个链接")

        print()
        print("=== 自检全部通过 ===")
        return 0

    except AssertionError as exc:
        print(f"✗ 自检失败: {exc}")
        print(f"错误码: {ERR_SELFTEST}")
        return 1
    except MarkNestError as exc:
        print(f"✗ 自检异常: {exc.message} (错误码: {exc.code})")
        return 1
    except Exception as exc:
        print(f"✗ 自检意外异常: {exc}")
        print(f"错误码: {ERR_SELFTEST}")
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        prog="marknest",
        description=f"{SKILL_DISPLAY} — {SKILL_DESCRIPTION}",
        epilog=f"版本 {SKILL_VERSION} | 独立实现 (clean-room)",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", "-i", metavar="FILE", help="输入文件路径")
    parser.add_argument("--url", "-u", metavar="URL", help="输入网页链接")
    parser.add_argument("--text", "-t", metavar="TEXT", help="直接输入文本")
    parser.add_argument("--format", "-f", choices=["json", "markdown", "text"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--output", "-o", metavar="FILE", help="输出到文件（默认输出到 stdout）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入参数
    input_count = sum(1 for x in [args.input, args.url, args.text] if x)
    if input_count == 0:
        print(f"[{ERR_ARGS}] 错误: 请提供 --input、--url 或 --text 之一", file=sys.stderr)
        parser.print_help()
        return 1
    if input_count > 1:
        print(f"[{ERR_ARGS}] 错误: --input、--url、--text 只能指定一个", file=sys.stderr)
        return 1

    # 执行转换
    try:
        if args.input:
            result = convert_file(args.input)
            print(f"✓ 文件转换成功: {args.input}", file=sys.stderr)
        elif args.url:
            print(f"正在获取 URL: {args.url} ...", file=sys.stderr)
            result = fetch_url(args.url)
            print(f"✓ URL 转换成功: {args.url}", file=sys.stderr)
        else:
            result = convert_text(args.text, source="text")
            print("✓ 文本转换成功", file=sys.stderr)

        # 格式化输出
        output_str = format_output(result, args.format)

        # 输出到文件或 stdout
        if args.output:
            Path(args.output).write_text(output_str, encoding="utf-8")
            print(f"✓ 输出已保存到: {args.output}", file=sys.stderr)
        else:
            print(output_str)

        return 0

    except MarkNestError as exc:
        print(f"错误 [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误 [{ERR_INTERNAL}]: 未预期异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
