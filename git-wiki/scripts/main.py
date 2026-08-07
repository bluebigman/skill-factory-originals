#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-wiki: 文档速建 Git 驱动 Wiki 引擎

纯标准库实现，用于将零散文档快速转化为 Git 版本控制的轻量 Wiki 站点。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法:
    python main.py --selftest                 # 运行内置自检
    python main.py <input> [<input>...]       # 处理文件/文件夹/URL
    python main.py <input> -o <输出目录>       # 指定输出目录
"""

import argparse
import datetime
import html
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "未找到指定的文件或文件夹，请检查路径是否正确。",
    "E002": "无法访问该网址，请检查网络或链接有效性。",
    "E003": "文件编码无法识别，请转换为 UTF-8 格式。",
    "E004": "没有权限在目标目录创建文件，请更换目录。",
    "E005": "批量处理中部分失败，详见报告。",
}

DEFAULT_OUTPUT_DIR = "./wiki"
INDEX_FILENAME = "_index.md"
GENERATED_MARK = "<!-- generated-by: git-wiki -->"
PLACEHOLDER_TITLE = "[需核实:标题]"

# ============================================================
# 工具函数
# ============================================================


def error_exit(code: str, message: str = None) -> None:
    """输出错误信息并退出"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    print(f"[错误 {code}] {msg}")
    sys.exit(1)


def sanitize_filename(name: str, separator: str = "-") -> str:
    """将页面名称转换为安全的文件名（去除特殊字符，空格替换为分隔符）"""
    # 去除路径分隔符和特殊字符
    name = re.sub(r'[\\/]', separator, name)
    name = re.sub(r'[#&%*:?<>|"\']', '', name)
    # 空格替换为分隔符
    name = re.sub(r'\s+', separator, name)
    # 去除首尾分隔符
    name = name.strip(separator)
    return name or "untitled"


def extract_frontmatter(content: str) -> tuple:
    """提取 YAML frontmatter（title/date/tags），返回 (元数据字典, 剩余内容)"""
    meta = {}
    rest = content
    if content.startswith("---"):
        lines = content.split("\n")
        # 找到第二个 ---
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
        if end_idx:
            for line in lines[1:end_idx]:
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip()] = value.strip()
            rest = "\n".join(lines[end_idx + 1:])
    return meta, rest


def infer_title(content: str, source_name: str) -> str:
    """从 frontmatter、首行标题或文件名推断页面标题"""
    meta, rest = extract_frontmatter(content)
    if meta.get("title"):
        return meta["title"]

    # 查找第一个 Markdown 标题
    for line in rest.split("\n"):
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()

    # 从文件名推断
    stem = Path(source_name).stem
    if stem and not stem.isdigit():
        return stem.replace("_", " ").replace("-", " ").strip()

    return PLACEHOLDER_TITLE


def extract_date(content: str, source_name: str) -> str:
    """提取日期（frontmatter > 文件名 > 当前日期）"""
    meta, _ = extract_frontmatter(content)
    if meta.get("date"):
        return meta["date"]

    # 从文件名中匹配日期模式 YYYY-MM-DD
    match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', source_name)
    if match:
        return match.group(1).replace("_", "-")

    return datetime.date.today().isoformat()


def extract_tags(content: str) -> list:
    """提取标签（frontmatter 中的 tags 字段）"""
    meta, _ = extract_frontmatter(content)
    tags = meta.get("tags", "")
    if isinstance(tags, str):
        # 支持 "[tag1, tag2]" 或 "tag1, tag2" 格式
        tags = tags.strip("[]").split(",")
    return [t.strip() for t in tags if t.strip()]


def convert_html_to_markdown(html_content: str) -> str:
    """将 HTML 片段转换为简单的 Markdown（去除 script/style，保留标题和段落）"""
    # 去除 script 和 style 块
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
    # 去除内联样式
    html_content = re.sub(r'\sstyle="[^"]*"', '', html_content)
    # 标题转换
    for level in range(1, 7):
        html_content = re.sub(
            rf'<h{level}[^>]*>(.*?)</h{level}>',
            lambda m: '#' * level + ' ' + m.group(1).strip(),
            html_content,
            flags=re.DOTALL
        )
    # 段落转换
    html_content = re.sub(r'<p[^>]*>(.*?)</p>', lambda m: m.group(1).strip() + "\n\n", html_content, flags=re.DOTALL)
    # 列表转换
    html_content = re.sub(r'<li[^>]*>(.*?)</li>', lambda m: "- " + m.group(1).strip(), html_content, flags=re.DOTALL)
    # 去除剩余 HTML 标签
    html_content = re.sub(r'<[^>]+>', '', html_content)
    # 反转义 HTML 实体
    html_content = html.unescape(html_content)
    return html_content.strip()


def process_wikilinks(content: str) -> tuple:
    """处理 [[双链]] 语法，返回 (转换后内容, 链接到的页面列表)"""
    links = re.findall(r'\[\[([^\]]+)\]\]', content)
    for link in links:
        # 将 [[页面名]] 转换为 [页面名](页面名.md)
        target = sanitize_filename(link)
        content = content.replace(
            f"[[{link}]]",
            f"[{link}]({target}.md)"
        )
    return content, links


def get_summary(content: str, max_chars: int = 50) -> str:
    """获取页面摘要（首段前 N 字）"""
    # 去除 frontmatter
    _, rest = extract_frontmatter(content)
    # 去除标题行
    lines = [l for l in rest.split("\n") if l.strip() and not l.startswith("#")]
    if not lines:
        return ""
    summary = lines[0].strip()
    return summary[:max_chars] + ("..." if len(summary) > max_chars else "")


# ============================================================
# 内容处理核心
# ============================================================


def read_local_file(filepath: str) -> str:
    """读取本地文件内容（UTF-8 优先）"""
    path = Path(filepath)
    if not path.exists():
        error_exit("E001")
    if not path.is_file():
        error_exit("E001", "指定路径不是文件。")

    # 尝试 UTF-8 读取
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # 尝试常见编码
        for enc in ["gbk", "latin-1", "utf-16"]:
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, LookupError):
                continue
        error_exit("E003")


def fetch_url_content(url: str) -> str:
    """抓取 URL 内容"""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read()
            # 尝试从 header 获取编码
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(charset)
            except (UnicodeDecodeError, LookupError):
                return raw.decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        error_exit("E002")


def process_input(input_source: str) -> dict:
    """处理单个输入源，返回页面数据"""
    result = {
        "source": input_source,
        "title": PLACEHOLDER_TITLE,
        "content": "",
        "links": [],
        "tags": [],
        "date": "",
        "success": False,
        "error": None,
    }

    try:
        # 判断是本地文件还是 URL
        if input_source.startswith(("http://", "https://")):
            raw_content = fetch_url_content(input_source)
            # URL 内容可能是 HTML
            if "<html" in raw_content.lower() or "<!doctype" in raw_content.lower():
                content = convert_html_to_markdown(raw_content)
            else:
                content = raw_content
            source_name = input_source.split("/")[-1] or "url-page"
        else:
            content = read_local_file(input_source)
            source_name = Path(input_source).name

        # 提取元数据
        title = infer_title(content, source_name)
        date = extract_date(content, source_name)
        tags = extract_tags(content)

        # 处理 wiki 链接
        content, links = process_wikilinks(content)

        # 清理内容：去除原始 frontmatter，保留正文
        _, body = extract_frontmatter(content)

        result.update({
            "title": title,
            "content": body.strip(),
            "links": links,
            "tags": tags,
            "date": date,
            "success": True,
        })
    except SystemExit:
        raise
    except Exception as e:
        result["error"] = str(e)

    return result


def generate_page_file(page: dict) -> str:
    """生成 Wiki 页面文件内容"""
    lines = []
    lines.append("---")
    lines.append(f'title: "{page["title"]}"')
    lines.append(f'source: "{page["source"]}"')
    lines.append(f'date: "{page["date"]}"')
    if page["tags"]:
        lines.append(f'tags: [{", ".join(page["tags"])}]')
    lines.append("---")
    lines.append("")
    lines.append(page["content"])
    lines.append("")
    lines.append(GENERATED_MARK)
    return "\n".join(lines)


def generate_index(pages: list) -> str:
    """生成首页索引文件"""
    lines = ["# Wiki 首页", ""]
    lines.append(f"共 {len(pages)} 个页面。", )
    lines.append("")
    lines.append("## 页面列表", )
    lines.append("")

    # 按日期倒序排列
    sorted_pages = sorted(pages, key=lambda p: p["date"], reverse=True)

    for page in sorted_pages:
        filename = sanitize_filename(page["title"]) + ".md"
        summary = get_summary(page["content"])
        link_line = f"- [{page['title']}]({filename})"
        if summary:
            link_line += f" — {summary}"
        if page["tags"]:
            link_line += f" `{'、'.join(page['tags'])}`"
        lines.append(link_line)

    lines.append("")
    lines.append(GENERATED_MARK)
    return "\n".join(lines)


def write_output(pages: list, output_dir: str) -> list:
    """写入输出文件，返回生成的文件路径列表"""
    out_path = Path(output_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        error_exit("E004")

    generated_files = []

    # 生成页面文件
    for page in pages:
        if not page["success"]:
            continue
        filename = sanitize_filename(page["title"]) + ".md"
        filepath = out_path / filename
        try:
            filepath.write_text(generate_page_file(page), encoding="utf-8")
            generated_files.append(str(filepath))
        except PermissionError:
            error_exit("E004")

    # 生成首页索引
    if generated_files:
        index_path = out_path / INDEX_FILENAME
        try:
            index_path.write_text(generate_index(pages), encoding="utf-8")
            generated_files.append(str(index_path))
        except PermissionError:
            error_exit("E004")

    return generated_files


# ============================================================
# 自检模块
# ============================================================


def run_selftest() -> int:
    """内置自检：使用硬编码样例数据验证核心逻辑"""
    print("=" * 60)
    print("git-wiki 自检开始")
    print("=" * 60)

    # --- 测试数据（硬编码，不依赖外部文件） ---
    sample_content = """---
title: 测试页面
date: 2025-03-15
tags: [测试, 示例]
---
# 测试标题

这是第一段内容，用于测试摘要提取。

- 列表项一
- 列表项二

[[另一个页面]] 双链测试。
"""

    sample_content2 = """# 第二个页面

这是第二个页面的内容，包含一些文字。
"""

    # --- 测试 1: 文件名清洗 ---
    print("[测试 1] 文件名清洗...")
    test_names = ["My Page Name", "特殊#字符&测试", "  前后空格  "]
    for name in test_names:
        cleaned = sanitize_filename(name)
        assert cleaned, "文件名清洗结果不应为空"
        assert " " not in cleaned, f"清洗后不应含空格: {cleaned}"
    print("  ✓ 通过")

    # --- 测试 2: frontmatter 提取 ---
    print("[测试 2] frontmatter 提取...")
    meta, rest = extract_frontmatter(sample_content)
    assert meta.get("title") == "测试页面", "frontmatter 标题提取失败"
    assert meta.get("date") == "2025-03-15", "frontmatter 日期提取失败"
    assert "测试标题" in rest, "frontmatter 后内容提取失败"
    print("  ✓ 通过")

    # --- 测试 3: 标题推断 ---
    print("[测试 3] 标题推断...")
    title1 = infer_title(sample_content, "test.md")
    assert title1 == "测试页面", f"应优先使用 frontmatter 标题，得到: {title1}"
    title2 = infer_title(sample_content2, "second-page.md")
    assert title2 == "第二个页面", f"应从 Markdown 标题推断，得到: {title2}"
    title3 = infer_title("# 无 frontmatter", "no-front.md")
    assert title3 == "无 frontmatter", f"应从首行标题推断，得到: {title3}"
    print("  ✓ 通过")

    # --- 测试 4: 日期提取 ---
    print("[测试 4] 日期提取...")
    date1 = extract_date(sample_content, "test.md")
    assert date1 == "2025-03-15", f"应从 frontmatter 提取日期，得到: {date1}"
    date2 = extract_date("", "2024-12-01-notes.md")
    assert date2 == "2024-12-01", f"应从文件名提取日期，得到: {date2}"
    date3 = extract_date("", "no-date.md")
    assert date3, "无日期时应返回当前日期"
    print("  ✓ 通过")

    # --- 测试 5: 标签提取 ---
    print("[测试 5] 标签提取...")
    tags = extract_tags(sample_content)
    assert len(tags) == 2, f"应提取 2 个标签，得到: {tags}"
    assert "测试" in tags, "标签内容不正确"
    print("  ✓ 通过")

    # --- 测试 6: Wiki 链接处理 ---
    print("[测试 6] Wiki 链接处理...")
    converted, links = process_wikilinks(sample_content)
    assert "另一个页面" in links, "应检测到双链"
    assert "另一个页面.md" in converted, "双链应转换为相对链接"
    print("  ✓ 通过")

    # --- 测试 7: HTML 转 Markdown ---
    print("[测试 7] HTML 转 Markdown...")
    html_content = "<html><body><h1>标题</h1><p>段落</p><script>alert('x')</script></body></html>"
    md = convert_html_to_markdown(html_content)
    assert "标题" in md, "HTML 标题转换失败"
    assert "段落" in md, "HTML 段落转换失败"
    assert "script" not in md.lower() or "alert" not in md, "script 内容未移除"
    print("  ✓ 通过")

    # --- 测试 8: 完整处理流程 ---
    print("[测试 8] 完整处理流程...")
    # 模拟两个输入页面的处理
    page1 = process_input_from_content(sample_content, "test.md")
    page2 = process_input_from_content(sample_content2, "second.md")

    assert page1["success"], "页面1 处理失败"
    assert page2["success"], "页面2 处理失败"
    assert page1["title"] == "测试页面", "页面1 标题错误"
    assert page2["title"] == "第二个页面", "页面2 标题错误"

    # 生成文件内容
    page1_file = generate_page_file(page1)
    assert "---" in page1_file, "应包含 frontmatter"
    assert GENERATED_MARK in page1_file, "应包含生成标记"

    # 生成索引
    index = generate_index([page1, page2])
    assert "测试页面" in index, "索引应包含页面1"
    assert "第二个页面" in index, "索引应包含页面2"
    print("  ✓ 通过")

    # --- 测试 9: 摘要提取 ---
    print("[测试 9] 摘要提取...")
    summary = get_summary(sample_content)
    assert "这是第一段内容" in summary, "摘要应包含首段内容"
    assert len(summary) <= 53, f"摘要长度应有限制，得到 {len(summary)}"
    print("  ✓ 通过")

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return 0


def process_input_from_content(content: str, source_name: str) -> dict:
    """从内容直接处理（用于测试和内部调用）"""
    result = {
        "source": source_name,
        "title": PLACEHOLDER_TITLE,
        "content": "",
        "links": [],
        "tags": [],
        "date": "",
        "success": False,
        "error": None,
    }

    try:
        title = infer_title(content, source_name)
        date = extract_date(content, source_name)
        tags = extract_tags(content)
        content, links = process_wikilinks(content)
        _, body = extract_frontmatter(content)

        result.update({
            "title": title,
            "content": body.strip(),
            "links": links,
            "tags": tags,
            "date": date,
            "success": True,
        })
    except Exception as e:
        result["error"] = str(e)

    return result


# ============================================================
# 主程序
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="git-wiki: 文档速建 Git 驱动 Wiki 引擎",
        epilog="示例: python main.py ./docs -o ./wiki"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="输入源：本地文件路径、文件夹路径或 URL"
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"输出目录（默认: {DEFAULT_OUTPUT_DIR}）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检后退出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 检查输入
    if not args.inputs:
        parser.print_help()
        error_exit("E001", "请至少提供一个输入源（文件、文件夹或 URL）。")

    # 处理输入
    pages = []
    failed = []

    for input_source in args.inputs:
        print(f"处理: {input_source}")

        # 检查路径是否存在
        if not input_source.startswith(("http://", "https://")):
            if not Path(input_source).exists():
                failed.append((input_source, "E001"))
                print(f"  [跳过] 路径不存在")
                continue

        try:
            page = process_input(input_source)
            if page["success"]:
                pages.append(page)
                print(f"  ✓ 成功: {page['title']}")
            else:
                failed.append((input_source, page.get("error") or "未知错误"))
                print(f"  ✗ 失败: {page.get('error')}")
        except SystemExit:
            raise
        except Exception as e:
            failed.append((input_source, str(e)))
            print(f"  ✗ 失败: {e}")

    # 生成输出
    if pages:
        generated = write_output(pages, args.output)
        print(f"\n成功生成 {len(generated)} 个文件到 {args.output}:")
        for f in generated:
            print(f"  - {f}")

        # 生成报告
        print("\n" + "=" * 60)
        print("处理报告")
        print("=" * 60)
        print(f"输入总数: {len(args.inputs)}")
        print(f"成功: {len(pages)}")
        print(f"失败: {len(failed)}")

        if failed:
            print("\n失败清单:")
            for src, err in failed:
                print(f"  - {src}: {err}")
            error_exit("E005", f"共 {len(args.inputs)} 个输入，成功 {len(pages)} 个，失败 {len(failed)} 个。")

        # 检查首页索引完整性
        index_path = Path(args.output) / INDEX_FILENAME
        if index_path.exists():
            index_content = index_path.read_text(encoding="utf-8")
            missing_links = [p["title"] for p in pages if p["title"] not in index_content]
            if missing_links:
                print(f"\n[警告] 以下页面未在首页索引中找到: {missing_links}")
            else:
                print("\n首页索引完整性检查: 通过")
        else:
            print("\n[警告] 首页索引未生成")

        print("\n提示: 建议在输出目录执行以下命令初始化 Git 仓库:")
        print(f"  cd {args.output} && git init && git add . && git commit -m 'initial wiki'")

    else:
        error_exit("E005", "没有成功生成任何页面。")


if __name__ == "__main__":
    main()
