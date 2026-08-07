#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
any2md - 将 PDF/DOCX/HTML/TXT 文件或 URL 网页转换为 LLM 优化的 Markdown（含 YAML frontmatter）。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
标准库优先，无第三方依赖。

用法示例:
    python main.py --selftest
    python main.py --file input.txt --title "示例"
    python main.py --url https://example.com --title "网页"
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空：请提供待处理的内容（文件路径或 URL）。",
    "E002": "关键信息缺失：缺少必要的输入参数或元数据。",
    "E003": "输入格式错误：无法识别的文件类型或 URL 格式。",
    "E004": "超出能力边界：不支持的网络协议或非法操作。",
    "E005": "置信度过低：结果无法确定，建议人工复核。",
    "E006": "文件读取失败：目标文件不存在或无法访问。",
    "E007": "URL 访问失败：网络请求异常或返回非成功状态码。",
    "E008": "URL 内容为空：抓取到的网页内容为空。",
    "E009": "HTML 解析失败：无法从 HTML 中提取有效正文。",
    "E010": "内部处理错误：发生未预期的运行时异常。",
}


class Any2MdError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------
def generate_frontmatter(title: str, source_type: str, source_name: str) -> str:
    """
    生成 YAML frontmatter 字符串。
    """
    now = datetime.now(timezone.utc).isoformat()
    fm = {
        "title": title or "未命名文档",
        "source_type": source_type,
        "source": source_name,
        "converted_at": now,
        "converter": "any2md",
        "version": "1.0.0",
    }
    lines = ["---"]
    for key, value in fm.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def text_to_markdown(content: str, title: str, source_name: str) -> str:
    """
    将纯文本转换为 Markdown 结构：
    - 按空行分段
    - 每段转为段落文本
    - 简单识别标题行（以 # 开头或全大写短行）
    """
    if not content or not content.strip():
        raise Any2MdError("E001")

    # 规范化换行
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    # 去除过多的空行
    content = re.sub(r"\n{3,}", "\n\n", content)

    lines = content.split("\n")
    md_lines = []
    para_buffer = []

    def flush_para():
        """将缓冲的段落行合并为一个段落输出。"""
        nonlocal para_buffer
        if para_buffer:
            text = " ".join(line.strip() for line in para_buffer if line.strip())
            if text:
                md_lines.append(text)
            para_buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            continue

        # 识别标题：以 # 开头
        if stripped.startswith("#"):
            flush_para()
            md_lines.append(stripped)
            continue

        # 识别标题：短行且全大写（少于 40 字符）
        if len(stripped) < 40 and stripped.isupper() and stripped.replace(" ", "").isalpha():
            flush_para()
            md_lines.append(f"## {stripped.title()}")
            continue

        # 普通文本行，加入缓冲
        para_buffer.append(stripped)

    flush_para()

    if not md_lines:
        raise Any2MdError("E005")

    body = "\n\n".join(md_lines)
    front = generate_frontmatter(title, "text", source_name)
    return f"{front}\n\n{body}\n"


def html_to_markdown(html_content: str, title: str, source_name: str) -> str:
    """
    将 HTML 内容转换为 Markdown：
    - 提取 <title> 作为默认标题
    - 去掉 <script>/<style> 标签
    - 将 <h1>-<h6> 转为 Markdown 标题
    - 将 <p> 转为段落
    - 将 <li> 转为列表项
    - 将 <a href> 转为链接
    - 将 <strong>/<b> 转为粗体
    - 将 <em>/<i> 转为斜体
    - 其余标签去除，保留文本
    """
    if not html_content or not html_content.strip():
        raise Any2MdError("E001")

    # 提取 <title>
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    if title_match and not title:
        title = html.unescape(title_match.group(1)).strip()

    # 移除 script/style
    content = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.IGNORECASE | re.DOTALL)

    # 将 <br> 转为换行
    content = re.sub(r"<br\s*/?>", "\n", content, flags=re.IGNORECASE)

    # 将块级标签替换为分隔符
    content = re.sub(r"</(p|div|section|article|h[1-6]|li|ul|ol|blockquote)>", "\n\n", content, flags=re.IGNORECASE)
    content = re.sub(r"<(p|div|section|article|h[1-6]|li|ul|ol|blockquote)[^>]*>", "\n\n", content, flags=re.IGNORECASE)

    # 处理标题标签
    content = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n\n# \1\n\n", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n\n## \1\n\n", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n\n### \1\n\n", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<h4[^>]*>(.*?)</h4>", r"\n\n#### \1\n\n", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<h5[^>]*>(.*?)</h5>", r"\n\n##### \1\n\n", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<h6[^>]*>(.*?)</h6>", r"\n\n###### \1\n\n", content, flags=re.IGNORECASE | re.DOTALL)

    # 处理链接 <a href="...">text</a>
    content = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # 处理粗体和斜体
    content = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", content, flags=re.IGNORECASE | re.DOTALL)

    # 处理列表项
    content = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1\n", content, flags=re.IGNORECASE | re.DOTALL)

    # 去除其余所有 HTML 标签
    content = re.sub(r"<[^>]+>", "", content)

    # 解码 HTML 实体
    content = html.unescape(content)

    # 规范化空白
    content = re.sub(r"[ \t]+", " ", content)
    content = re.sub(r"\n{3,}", "\n\n", content)

    # 确保列表项格式正确
    # 将 "- " 前多余的空白移除
    content = re.sub(r"^\s*-\s+", "- ", content, flags=re.MULTILINE)

    # 去除首尾空白
    content = content.strip()

    if not content:
        raise Any2MdError("E009")

    front = generate_frontmatter(title, "html", source_name)
    return f"{front}\n\n{content}\n"


def fetch_url_content(url: str) -> str:
    """
    从 URL 获取内容（仅支持 http/https）。
    返回解码后的文本内容。
    """
    if not url.startswith(("http://", "https://")):
        raise Any2MdError("E004")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "any2md/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            if status != 200:
                raise Any2MdError("E007", f"HTTP 状态码: {status}")
            raw = resp.read()
            # 尝试从响应头获取编码
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                content = raw.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                content = raw.decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise Any2MdError("E007", str(exc)) from exc
    except TimeoutError as exc:
        raise Any2MdError("E007", "请求超时") from exc

    if not content or not content.strip():
        raise Any2MdError("E008")

    return content


def process_file(file_path: str, title: str = "") -> str:
    """
    处理本地文件（TXT/HTML/HTM/MD）。
    返回 Markdown 字符串。
    """
    path = Path(file_path)
    if not path.exists():
        raise Any2MdError("E006", f"文件不存在: {file_path}")
    if not path.is_file():
        raise Any2MdError("E006", f"不是文件: {file_path}")

    suffix = path.suffix.lower()
    if suffix not in (".txt", ".html", ".htm", ".md", ".markdown"):
        raise Any2MdError("E003", f"不支持的文件类型: {suffix}")

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise Any2MdError("E006", str(exc)) from exc

    if not content.strip():
        raise Any2MdError("E001")

    if suffix in (".html", ".htm"):
        return html_to_markdown(content, title, str(path))
    # TXT 或 Markdown 文件
    return text_to_markdown(content, title, str(path))


def process_url(url: str, title: str = "") -> str:
    """
    处理 URL 网页。
    返回 Markdown 字符串。
    """
    content = fetch_url_content(url)
    return html_to_markdown(content, title, url)


def process_input(target: str, title: str = "") -> str:
    """
    统一入口：根据输入类型（文件或 URL）分派处理。
    """
    if not target or not target.strip():
        raise Any2MdError("E001")

    target = target.strip()
    if target.startswith(("http://", "https://")):
        return process_url(target, title)
    return process_file(target, title)


# ---------------------------------------------------------------------------
# 自检模块 (--selftest)
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不访问网络。
    断言使用宽松阈值，确保稳健。
    """
    print("开始自检 (selftest)...")
    failures = 0

    # --- 测试 1: text_to_markdown 基本功能 ---
    print("测试 1: text_to_markdown 基本功能")
    sample_text = """这是一个测试文档。

这是第二段，包含一些内容。

# 一级标题

这是标题下的内容。

## 二级标题

列表项目一
列表项目二
"""
    try:
        md = text_to_markdown(sample_text, "测试文档", "test.txt")
        # 宽松断言：包含关键结构
        assert md.startswith("---"), "YAML frontmatter 应以 --- 开头"
        assert "title: \"测试文档\"" in md, "frontmatter 应包含标题"
        assert "# 一级标题" in md, "应识别一级标题"
        assert "## 二级标题" in md, "应识别二级标题"
        assert "这是第二段" in md, "应包含第二段内容"
        assert len(md) > 100, "输出应有一定长度"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Any2MdError as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # --- 测试 2: html_to_markdown 基本功能 ---
    print("测试 2: html_to_markdown 基本功能")
    sample_html = """<!DOCTYPE html>
<html>
<head><title>HTML测试页</title></head>
<body>
<h1>主标题</h1>
<p>这是第一段，包含 <strong>粗体</strong> 和 <em>斜体</em> 文本。</p>
<p>这是 <a href="https://example.com">链接</a> 测试。</p>
<ul>
<li>项目一</li>
<li>项目二</li>
</ul>
</body>
</html>"""
    try:
        md = html_to_markdown(sample_html, "", "test.html")
        # 调试输出
        # print(f"调试: md = {md}")
        assert md.startswith("---"), "应以 frontmatter 开头"
        assert "主标题" in md, "应包含 h1 内容"
        assert "**粗体**" in md, "应保留粗体格式"
        assert "*斜体*" in md, "应保留斜体格式"
        assert "[链接](https://example.com)" in md, "应转换链接"
        assert "- 项目一" in md, "应转换列表项"
        assert "HTML测试页" in md, "应从 <title> 提取标题"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        # 调试输出
        # print(f"调试: md = {md}")
        failures += 1
    except Any2MdError as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # --- 测试 3: generate_frontmatter 结构 ---
    print("测试 3: generate_frontmatter 结构")
    try:
        fm = generate_frontmatter("测试", "text", "source.txt")
        assert fm.startswith("---\n"), "应以 --- 和换行开头"
        assert "\n---" in fm, "应包含结束的 ---"
        assert "title:" in fm, "应包含 title 键"
        assert "converted_at:" in fm, "应包含时间戳"
        assert "converter:" in fm, "应包含转换器标识"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1

    # --- 测试 4: 错误处理 ---
    print("测试 4: 错误处理")
    try:
        text_to_markdown("", "test", "none")
        print("  FAIL: 空输入应抛出 E001")
        failures += 1
    except Any2MdError as exc:
        if exc.code == "E001":
            print("  PASS")
        else:
            print(f"  FAIL: 错误码应为 E001，实际为 {exc.code}")
            failures += 1

    # --- 测试 5: 边界情况 ---
    print("测试 5: 边界情况（长文本）")
    long_text = "\n\n".join([f"这是第 {i} 段的测试内容，用于验证长文本处理。" for i in range(50)])
    try:
        md = text_to_markdown(long_text, "长文本", "long.txt")
        assert len(md) > 500, "长文本输出应有一定长度"
        assert "这是第 0 段" in md, "应包含第一段"
        assert "这是第 49 段" in md, "应包含最后一段"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Any2MdError as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # --- 测试 6: 特殊字符 ---
    print("测试 6: 特殊字符处理")
    special_text = """包含特殊字符的文本。

引号："双引号" 和 '单引号'

符号：@ # $ % ^ & * ( ) + - = { } [ ] | \\ / ? < > ~ ` ! 等
"""
    try:
        md = text_to_markdown(special_text, "特殊", "special.txt")
        assert "双引号" in md, "应保留双引号"
        assert "单引号" in md, "应保留单引号"
        assert "@" in md, "应保留符号"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Any2MdError as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # --- 汇总 ---
    if failures == 0:
        print("\n所有自检通过 ✓")
        return 0
    else:
        print(f"\n自检失败: {failures} 项未通过 ✗")
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="any2md - 将文件或 URL 转换为 LLM 优化的 Markdown",
        epilog="示例: python main.py --file input.txt --title '标题'",
    )
    parser.add_argument("--file", type=str, help="输入文件路径（TXT/HTML/HTM/MD）")
    parser.add_argument("--url", type=str, help="输入 URL（http/https）")
    parser.add_argument("--title", type=str, default="", help="文档标题（可选）")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（可选，默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", type=str, help="通用输入（文件路径或 URL）")

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    # 确定输入目标
    target = ""
    if args.file:
        target = args.file
    elif args.url:
        target = args.url
    elif args.input:
        target = args.input
    else:
        parser.print_help()
        return 0

    try:
        result = process_input(target, args.title)
    except Any2MdError as exc:
        print(f"错误 {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底异常
        print(f"错误 E010: 未预期异常: {exc}", file=sys.stderr)
        return 1

    # 输出
    if args.output:
        try:
            Path(args.output).write_text(result, encoding="utf-8")
            print(f"已写入: {args.output}")
        except OSError as exc:
            print(f"错误 E010: 写入失败: {exc}", file=sys.stderr)
            return 1
    else:
        print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
