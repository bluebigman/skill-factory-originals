#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jina-cli 独立实现脚本
功能：将 URL 或本地文件内容转换为结构化文本（纯文本 / Markdown / JSON）
仅依据功能规格独立实现，不参考任何既有代码。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# ============================================================
# 错误码定义
# E001: 参数错误
# E002: 输入源不存在（文件不存在或 URL 无法访问）
# E003: 网络请求失败
# E004: 文件读取失败
# E005: 内容解析失败
# E006: 输出格式不支持
# E007: 内部逻辑错误
# E008: 自检失败
# E009: 权限不足
# E010: 未知错误
# ============================================================

ERROR_CODES = {
    "E001": "参数错误",
    "E002": "输入源不存在",
    "E003": "网络请求失败",
    "E004": "文件读取失败",
    "E005": "内容解析失败",
    "E006": "输出格式不支持",
    "E007": "内部逻辑错误",
    "E008": "自检失败",
    "E009": "权限不足",
    "E010": "未知错误",
}


class JinaCliError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心功能：内容提取与转换
# ============================================================

def is_url(source: str) -> bool:
    """判断输入是否为 URL"""
    return source.startswith(("http://", "https://"))


def fetch_url_content(url: str, timeout: int = 10) -> str:
    """
    从 URL 获取内容
    注意：不执行 JavaScript，仅获取静态 HTML
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "jina-cli/1.0.1 (content extractor)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 读取原始字节并尝试解码
            raw_data = resp.read()
            # 尝试从响应头获取编码
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                return raw_data.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                # 编码未知时尝试 UTF-8，失败则用 replace
                return raw_data.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise JinaCliError("E003", f"HTTP 错误: {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        raise JinaCliError("E003", f"URL 错误: {e.reason}")
    except TimeoutError:
        raise JinaCliError("E003", f"请求超时（{timeout}秒）")
    except Exception as e:
        raise JinaCliError("E003", f"网络请求失败: {str(e)}")


def read_local_file(file_path: str) -> str:
    """读取本地文件内容"""
    try:
        path = Path(file_path)
        if not path.exists():
            raise JinaCliError("E002", f"文件不存在: {file_path}")
        if not path.is_file():
            raise JinaCliError("E002", f"路径不是文件: {file_path}")
        # 尝试多种编码读取
        encodings = ["utf-8", "gbk", "latin-1"]
        for enc in encodings:
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        # 最后尝试二进制读取并强制解码
        try:
            return path.read_bytes().decode("utf-8", errors="replace")
        except PermissionError:
            raise JinaCliError("E009", f"权限不足，无法读取: {file_path}")
    except JinaCliError:
        raise
    except PermissionError:
        raise JinaCliError("E009", f"权限不足，无法读取: {file_path}")
    except Exception as e:
        raise JinaCliError("E004", f"文件读取失败: {str(e)}")


def extract_text_from_html(html: str) -> str:
    """
    从 HTML 中提取纯文本
    简单实现：去除 script/style 标签，去除 HTML 标签，保留文本
    """
    if not html:
        return ""
    try:
        # 移除 script 和 style 块
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        # 移除注释
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        # 将 br 和块级标签替换为换行
        text = re.sub(r"<(br|/p|/div|/h[1-6]|/li|/tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
        # 移除所有剩余标签
        text = re.sub(r"<[^>]+>", " ", text)
        # 解码常见 HTML 实体
        text = html_unescape(text)
        # 合并空白字符
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()
    except Exception as e:
        raise JinaCliError("E005", f"HTML 解析失败: {str(e)}")


def html_unescape(text: str) -> str:
    """简单的 HTML 实体反转义"""
    entities = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&nbsp;": " ",
        "&copy;": "©",
        "&reg;": "®",
        "&trade;": "™",
    }
    for key, value in entities.items():
        text = text.replace(key, value)
    # 处理数字实体
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    return text


def extract_text_from_markdown(md: str) -> str:
    """简单处理 Markdown，去除标记符号"""
    if not md:
        return ""
    try:
        text = md
        # 移除标题标记（包括行首的 # 和空格）
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
        # 移除粗体/斜体标记
        text = re.sub(r"\*\*|__|\*|_", "", text)
        # 移除行内代码标记
        text = re.sub(r"`([^`]*)`", r"\1", text)
        # 移除链接但保留文字
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        # 移除图片
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
        # 移除引用标记
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
        # 移除列表标记
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
        # 移除分隔线
        text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)
        # 清理多余空行
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()
    except Exception as e:
        raise JinaCliError("E005", f"Markdown 解析失败: {str(e)}")


def detect_content_type(content: str) -> str:
    """检测内容类型：html / markdown / plain"""
    if not content:
        return "plain"
    # 检查是否包含 HTML 标签
    if re.search(r"<[a-z][\s\S]*?>", content[:5000], re.IGNORECASE):
        return "html"
    # 检查是否包含 Markdown 标记
    md_patterns = [
        r"^#{1,6}\s",
        r"!\[.*\]\(.*\)",
        r"\[.*\]\(.*\)",
        r"^\s*[-*+]\s+",
        r"^\s*\d+\.\s+",
        r"^>\s+",
        r"`.*`",
    ]
    for pattern in md_patterns:
        if re.search(pattern, content[:5000], re.MULTILINE):
            return "markdown"
    return "plain"


def convert_to_plain(content: str) -> str:
    """统一转换为纯文本"""
    content_type = detect_content_type(content)
    if content_type == "html":
        return extract_text_from_html(content)
    elif content_type == "markdown":
        return extract_text_from_markdown(content)
    return content.strip()


def process_source(source: str) -> Dict[str, Any]:
    """
    处理单个输入源，返回结构化结果
    """
    result = {
        "source": source,
        "type": "url" if is_url(source) else "file",
        "content": "",
        "content_type": "plain",
    }

    # 获取原始内容
    if is_url(source):
        raw_content = fetch_url_content(source)
    else:
        raw_content = read_local_file(source)

    # 检测原始内容类型
    raw_type = detect_content_type(raw_content)
    result["raw_content_type"] = raw_type

    # 转换为纯文本
    plain_text = convert_to_plain(raw_content)
    result["content"] = plain_text
    result["content_type"] = "plain"

    # 统计信息
    result["stats"] = {
        "chars": len(plain_text),
        "words": len(plain_text.split()),
        "lines": len(plain_text.splitlines()),
    }

    return result


# ============================================================
# 输出格式化
# ============================================================

def format_output(results: List[Dict[str, Any]], fmt: str = "text") -> str:
    """按指定格式输出结果"""
    if fmt == "text":
        return _format_as_text(results)
    elif fmt == "markdown":
        return _format_as_markdown(results)
    elif fmt == "json":
        return _format_as_json(results)
    else:
        raise JinaCliError("E006", f"不支持的输出格式: {fmt}")


def _format_as_text(results: List[Dict[str, Any]]) -> str:
    """纯文本格式输出"""
    parts = []
    for i, result in enumerate(results, 1):
        parts.append(f"===== 来源 {i} =====")
        parts.append(f"地址: {result['source']}")
        parts.append(f"类型: {result['type']}")
        parts.append(f"字符数: {result['stats']['chars']}")
        parts.append(f"词数: {result['stats']['words']}")
        parts.append(f"行数: {result['stats']['lines']}")
        parts.append("--- 内容 ---")
        parts.append(result["content"])
        parts.append("")
    return "\n".join(parts)


def _format_as_markdown(results: List[Dict[str, Any]]) -> str:
    """Markdown 格式输出"""
    parts = ["# 内容提取结果\n"]
    for i, result in enumerate(results, 1):
        parts.append(f"## 来源 {i}")
        parts.append(f"- **地址**: {result['source']}")
        parts.append(f"- **类型**: {result['type']}")
        parts.append(f"- **统计**: {result['stats']['chars']} 字符, "
                     f"{result['stats']['words']} 词, {result['stats']['lines']} 行")
        parts.append("\n### 内容\n")
        # 将内容包裹在引用块中
        content_lines = result["content"].splitlines()
        quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in content_lines)
        parts.append(quoted)
        parts.append("")
    return "\n".join(parts)


def _format_as_json(results: List[Dict[str, Any]]) -> str:
    """JSON 格式输出"""
    output = {
        "tool": "jina-cli",
        "version": "1.0.1",
        "results": results,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# ============================================================
# 自检功能（离线，不依赖外部资源）
# ============================================================

def run_selftest() -> bool:
    """
    自检核心逻辑
    使用内置硬编码样例数据，不读外部文件、不访问网络
    """
    print("开始自检...")

    # 测试数据
    test_html = """
    <html>
    <head><title>测试页面</title></head>
    <body>
        <script>var x = 1;</script>
        <style>body { color: red; }</style>
        <h1>标题测试</h1>
        <p>这是第一段内容。</p>
        <p>这是第二段内容，包含<a href="https://example.com">链接</a>。</p>
        <ul>
            <li>列表项 1</li>
            <li>列表项 2</li>
        </ul>
    </body>
    </html>
    """

    test_markdown = """
    # 测试标题

    这是一个**测试**段落，包含[链接](https://example.com)。

    ## 二级标题

    - 项目一
    - 项目二

    > 引用内容
    """

    test_plain = "这是纯文本内容。\n第二行内容。"

    # 测试 1: HTML 提取
    print("测试 1: HTML 内容提取...")
    try:
        extracted = extract_text_from_html(test_html)
        assert "标题测试" in extracted, "HTML 提取应包含标题"
        assert "第一段内容" in extracted, "HTML 提取应包含第一段"
        assert "第二段内容" in extracted, "HTML 提取应包含第二段"
        assert "列表项" in extracted, "HTML 提取应包含列表项"
        # 不应包含脚本和样式内容
        assert "var x" not in extracted, "HTML 提取不应包含脚本内容"
        assert "color" not in extracted, "HTML 提取不应包含样式内容"
        # 长度应大于某个阈值
        assert len(extracted) > 10, "提取内容长度应大于 10"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 2: Markdown 提取
    print("测试 2: Markdown 内容提取...")
    try:
        extracted = extract_text_from_markdown(test_markdown)
        assert "测试标题" in extracted, "Markdown 提取应包含标题"
        assert "测试" in extracted, "Markdown 提取应包含加粗内容"
        assert "项目一" in extracted, "Markdown 提取应包含列表项"
        assert "引用内容" in extracted, "Markdown 提取应包含引用"
        # 不应包含 Markdown 标记
        assert "**" not in extracted, "Markdown 提取不应包含粗体标记"
        assert "#" not in extracted, "Markdown 提取不应包含标题标记"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 3: 内容类型检测
    print("测试 3: 内容类型检测...")
    try:
        assert detect_content_type(test_html) == "html", "HTML 应被检测为 html"
        assert detect_content_type(test_markdown) == "markdown", "Markdown 应被检测为 markdown"
        assert detect_content_type(test_plain) == "plain", "纯文本应被检测为 plain"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 4: URL 判断
    print("测试 4: URL 判断...")
    try:
        assert is_url("https://example.com") is True, "https URL 应返回 True"
        assert is_url("http://example.com") is True, "http URL 应返回 True"
        assert is_url("./local/file.txt") is False, "本地路径应返回 False"
        assert is_url("example.com") is False, "无协议 URL 应返回 False"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 5: 整体处理流程（使用内存中的模拟数据）
    print("测试 5: 整体处理流程...")
    try:
        # 模拟处理结果
        mock_result = {
            "source": "https://example.com/test",
            "type": "url",
            "content": "测试内容",
            "content_type": "plain",
            "stats": {"chars": 4, "words": 1, "lines": 1},
        }
        # 测试输出格式化
        text_output = format_output([mock_result], "text")
        assert "测试内容" in text_output, "文本输出应包含内容"
        assert "来源" in text_output, "文本输出应包含来源标记"

        json_output = format_output([mock_result], "json")
        parsed = json.loads(json_output)
        assert parsed["tool"] == "jina-cli", "JSON 输出应包含工具名"
        assert len(parsed["results"]) == 1, "JSON 输出应包含 1 个结果"
        assert parsed["results"][0]["content"] == "测试内容", "JSON 输出应包含内容"

        md_output = format_output([mock_result], "markdown")
        assert "测试内容" in md_output, "Markdown 输出应包含内容"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 6: 错误处理
    print("测试 6: 错误处理...")
    try:
        # 不存在的文件
        try:
            read_local_file("/nonexistent/path/file.txt")
            print("  ✗ 失败: 应抛出 E002 错误")
            return False
        except JinaCliError as e:
            assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"

        # 不支持的输出格式
        try:
            format_output([], "xml")
            print("  ✗ 失败: 应抛出 E006 错误")
            return False
        except JinaCliError as e:
            assert e.code == "E006", f"错误码应为 E006，实际为 {e.code}"

        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 7: HTML 实体解码
    print("测试 7: HTML 实体解码...")
    try:
        decoded = html_unescape("&lt;tag&gt; &amp; &quot;quoted&quot;")
        assert "<" in decoded, "应解码 &lt;"
        assert ">" in decoded, "应解码 &gt;"
        assert "&" in decoded, "应解码 &amp;"
        assert '"' in decoded, "应解码 &quot;"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    print("所有自检测试通过！")
    return True


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="网页转文本 内容提取 智能解析 (jina-cli)",
        epilog="示例: python main.py https://example.com --format json",
    )
    parser.add_argument(
        "sources",
        nargs="*",
        help="要处理的 URL 或文件路径，可多个",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="网络请求超时时间（秒）(默认: 10)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检并退出",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息并退出",
    )

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print("jina-cli version 1.0.1")
        print("网页转文本 内容提取 智能解析")
        return 0

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 检查是否有输入源
    if not args.sources:
        parser.print_help()
        return 0

    # 处理输入源
    try:
        results = []
        for source in args.sources:
            print(f"正在处理: {source}...", file=sys.stderr)
            result = process_source(source)
            results.append(result)
            # 输出进度信息到 stderr
            print(f"  完成: {result['stats']['chars']} 字符, "
                  f"{result['stats']['words']} 词", file=sys.stderr)

        # 格式化输出
        output = format_output(results, args.format)
        print(output)
        return 0

    except JinaCliError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未知错误 [E010]: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
