#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subtlety — 数据源格式转换与结构化输出工具

功能：将 SVN 日志、RSS 2.0、hAtom 微格式等数据源转换为 Atom 1.0 或结构化 JSON。
支持批量处理与置信度标注（不确定字段输出 [需核实:字段名] 占位符）。

用法：
    python main.py --selftest                # 运行内置自检（不依赖外部文件/网络）
    python main.py --input file.txt --format svn --output result.json
    python main.py --input file.xml --format rss --output result.atom

错误码：
    E001 参数错误
    E002 输入文件不存在或不可读
    E003 不支持的输入格式
    E004 解析失败（输入内容不符合预期格式）
    E005 输出目录不可写
    E006 内部逻辑错误（不应发生）
    E007 输出格式不支持
    E008 输入内容为空
    E009 批量处理时部分条目失败
    E010 未知异常
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ---------------------------------------------------------------
# 错误处理辅助
# ---------------------------------------------------------------

class SubtletyError(Exception):
    """带错误码的异常基类。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def fail(code: str, message: str) -> None:
    """抛出一个带错误码的异常。"""
    raise SubtletyError(code, message)


# ---------------------------------------------------------------
# 通用工具函数
# ---------------------------------------------------------------

def _safe_text(value: Any) -> str:
    """将任意值安全转换为字符串，None 转为空字符串。"""
    if value is None:
        return ""
    return str(value).strip()


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO8601 格式字符串。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_atom_entry(entry: Dict[str, Any]) -> ET.Element:
    """根据结构化条目字典构建一个 Atom <entry> 元素。"""
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    ET.register_namespace("", ns["atom"])

    elem = ET.Element("{http://www.w3.org/2005/Atom}entry")

    # 标题（必填）
    title = ET.SubElement(elem, "{http://www.w3.org/2005/Atom}title")
    title.text = _safe_text(entry.get("title") or "[无标题]")

    # 链接（可选）
    link_url = _safe_text(entry.get("link"))
    if link_url:
        link = ET.SubElement(elem, "{http://www.w3.org/2005/Atom}link")
        link.set("href", link_url)
        link.set("rel", "alternate")

    # 更新时间（必填）
    updated = ET.SubElement(elem, "{http://www.w3.org/2005/Atom}updated")
    updated.text = _safe_text(entry.get("updated") or _now_iso())

    # 作者（可选）
    author_name = _safe_text(entry.get("author"))
    if author_name:
        author = ET.SubElement(elem, "{http://www.w3.org/2005/Atom}author")
        name = ET.SubElement(author, "{http://www.w3.org/2005/Atom}name")
        name.text = author_name

    # 内容摘要（可选）
    summary_text = _safe_text(entry.get("summary"))
    if summary_text:
        summary = ET.SubElement(elem, "{http://www.w3.org/2005/Atom}summary")
        summary.text = summary_text

    # 置信度标注占位符（若存在不确定字段）
    for key in ("uncertain_fields",):
        fields = entry.get(key)
        if fields:
            placeholder = ET.SubElement(elem, "{http://www.w3.org/2005/Atom}category")
            placeholder.set("term", "[需核实:" + ",".join(fields) + "]")

    return elem


def _entries_to_atom(entries: List[Dict[str, Any]], feed_title: str = "转换结果") -> str:
    """将条目列表转换为 Atom 1.0 XML 字符串。"""
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    ET.register_namespace("", ns["atom"])

    root = ET.Element("{http://www.w3.org/2005/Atom}feed")

    # Feed 元信息
    title = ET.SubElement(root, "{http://www.w3.org/2005/Atom}title")
    title.text = feed_title

    updated = ET.SubElement(root, "{http://www.w3.org/2005/Atom}updated")
    updated.text = _now_iso()

    feed_id = ET.SubElement(root, "{http://www.w3.org/2005/Atom}id")
    feed_id.text = "urn:subtlety:feed:" + str(abs(hash(feed_title)))

    # 添加每个条目
    for entry in entries:
        root.append(_build_atom_entry(entry))

    # 序列化为字符串
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


# ---------------------------------------------------------------
# 解析器：SVN 日志
# ---------------------------------------------------------------

def parse_svn_log(text: str) -> List[Dict[str, Any]]:
    """
    解析 SVN 日志文本（svn log 命令的默认输出格式）。

    支持两种常见格式：
    1. 标准格式：以 "------------------------------------------------------------------------" 分隔
    2. 简单格式：每行 "r123 | author | date | lines"
    """
    if not text or not text.strip():
        fail("E008", "输入内容为空")

    entries: List[Dict[str, Any]] = []
    lines = text.splitlines()

    # 尝试标准格式（分隔线 + rN | author | date | lines）
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("-" * 20):
            # 分隔线，进入下一条记录
            i += 1
            continue

        # 尝试匹配 rN | author | date | lines 格式
        # 使用更灵活的正则表达式
        m = re.match(r"^r(\d+)\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*$", line)
        if m:
            rev = m.group(1)
            author = m.group(2).strip()
            date_str = m.group(3).strip()
            lines_count = int(m.group(4))

            # 收集消息（后续行直到下一个分隔线）
            i += 1
            msg_lines = []
            while i < len(lines) and not lines[i].strip().startswith("-" * 20):
                msg_lines.append(lines[i])
                i += 1

            message = "\n".join(msg_lines).strip()

            # 尝试解析日期（SVN 默认格式：YYYY-MM-DD HH:MM:SS +TZ (Day, DD Mon YYYY)）
            date_iso = date_str
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
            if date_match:
                date_iso = date_match.group(1) + "T00:00:00Z"

            entries.append({
                "id": f"svn-{rev}",
                "title": f"SVN r{rev}",
                "author": author,
                "updated": date_iso,
                "summary": message[:200] if message else "",
                "link": "",
                "uncertain_fields": [] if message else ["summary"],
            })
            continue

        i += 1

    # 如果标准格式解析失败，尝试简单逐行格式
    if not entries:
        # 简单格式：每行 "r123 author date message"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^r(\d+)\s+(\S+)\s+(\S+)\s+(.*)$", line)
            if m:
                rev = m.group(1)
                author = m.group(2)
                date_str = m.group(3)
                message = m.group(4)
                entries.append({
                    "id": f"svn-{rev}",
                    "title": f"SVN r{rev}",
                    "author": author,
                    "updated": date_str + "T00:00:00Z" if len(date_str) == 10 else date_str,
                    "summary": message[:200],
                    "link": "",
                    "uncertain_fields": [],
                })

    if not entries:
        fail("E004", "无法从输入中解析出 SVN 日志条目")

    return entries


# ---------------------------------------------------------------
# 解析器：RSS 2.0
# ---------------------------------------------------------------

def parse_rss(text: str) -> List[Dict[str, Any]]:
    """解析 RSS 2.0 XML 文本为条目列表。"""
    if not text or not text.strip():
        fail("E008", "输入内容为空")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        fail("E004", f"RSS XML 解析失败: {e}")

    entries: List[Dict[str, Any]] = []

    # 查找所有 <item> 元素（支持命名空间或默认命名空间）
    items = root.findall(".//item") or root.findall(".//{*}item")
    if not items:
        fail("E004", "RSS 中未找到 <item> 元素")

    for item in items:
        # 提取字段（兼容命名空间）
        def get_text(tag: str) -> str:
            elem = item.find(tag) or item.find("{*}" + tag)
            return _safe_text(elem.text if elem is not None else "")

        title = get_text("title")
        link = get_text("link")
        desc = get_text("description")
        author = get_text("author") or get_text("creator") or get_text("dc:creator")
        pub_date = get_text("pubDate") or get_text("date")

        # 尝试将 RFC822 日期转换为 ISO8601
        date_iso = pub_date
        if pub_date:
            try:
                # 简单提取日期部分
                m = re.search(r"\d{1,2}\s+\w+\s+\d{4}", pub_date)
                if m:
                    date_iso = m.group(0) + "T00:00:00Z"
            except Exception:
                date_iso = pub_date

        uncertain = []
        if not title:
            uncertain.append("title")
        if not author:
            uncertain.append("author")
        if not pub_date:
            uncertain.append("updated")

        entries.append({
            "id": link or f"rss-{len(entries)}",
            "title": title or "[无标题]",
            "author": author,
            "updated": date_iso,
            "summary": desc,
            "link": link,
            "uncertain_fields": uncertain,
        })

    return entries


# ---------------------------------------------------------------
# 解析器：hAtom 微格式
# ---------------------------------------------------------------

def parse_hatom(text: str) -> List[Dict[str, Any]]:
    """从 HTML 文本中提取 hAtom 微格式条目。"""
    if not text or not text.strip():
        fail("E008", "输入内容为空")

    entries: List[Dict[str, Any]] = []

    # 使用正则表达式提取 hEntry 块（简化实现）
    # 匹配 class="hentry" 或 class="h-entry" 的元素
    pattern = re.compile(
        r'<[^>]*class\s*=\s*["\']([^"\']*hentry[^"\']*)["\'][^>]*>(.*?)</[^>]+>',
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(text)
    if not matches:
        # 尝试另一种模式：没有引号的 class
        pattern2 = re.compile(
            r'<[^>]*class\s*=\s*([^\s>]+hentry[^\s>]*)[^>]*>(.*?)</[^>]+>',
            re.IGNORECASE | re.DOTALL
        )
        matches = [(m[0], m[1]) for m in pattern2.findall(text)]

    if not matches:
        fail("E004", "输入中未找到 hAtom 微格式条目")

    for idx, (class_attr, content) in enumerate(matches):
        # 提取标题
        title_match = re.search(
            r'<[^>]*class\s*=\s*["\']?[^"\']*entry-title[^"\']*["\']?[^>]*>(.*?)</[^>]+>',
            content, re.IGNORECASE | re.DOTALL
        )
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""

        # 提取作者
        author_match = re.search(
            r'<[^>]*class\s*=\s*["\']?[^"\']*author[^"\']*["\']?[^>]*>(.*?)</[^>]+>',
            content, re.IGNORECASE | re.DOTALL
        )
        author = re.sub(r"<[^>]+>", "", author_match.group(1)).strip() if author_match else ""

        # 提取时间
        time_match = re.search(
            r'<[^>]*class\s*=\s*["\']?[^"\']*published[^"\']*["\']?[^>]*>(.*?)</[^>]+>',
            content, re.IGNORECASE | re.DOTALL
        )
        if not time_match:
            time_match = re.search(
                r'<[^>]*class\s*=\s*["\']?[^"\']*updated[^"\']*["\']?[^>]*>(.*?)</[^>]+>',
                content, re.IGNORECASE | re.DOTALL
            )
        pub_date = re.sub(r"<[^>]+>", "", time_match.group(1)).strip() if time_match else ""

        # 提取链接
        link_match = re.search(r'href\s*=\s*["\']([^"\']+)["\']', content)
        link = link_match.group(1) if link_match else ""

        # 提取内容摘要（entry-content）
        content_match = re.search(
            r'<[^>]*class\s*=\s*["\']?[^"\']*entry-content[^"\']*["\']?[^>]*>(.*?)</[^>]+>',
            content, re.IGNORECASE | re.DOTALL
        )
        summary = re.sub(r"<[^>]+>", " ", content_match.group(1)).strip() if content_match else ""

        uncertain = []
        if not title:
            uncertain.append("title")
        if not author:
            uncertain.append("author")
        if not pub_date:
            uncertain.append("updated")

        entries.append({
            "id": link or f"hatom-{idx}",
            "title": title or "[无标题]",
            "author": author,
            "updated": pub_date,
            "summary": summary[:200],
            "link": link,
            "uncertain_fields": uncertain,
        })

    return entries


# ---------------------------------------------------------------
# 转换器
# ---------------------------------------------------------------

def convert_to_json(entries: List[Dict[str, Any]]) -> str:
    """将条目列表转换为 JSON 字符串。"""
    return json.dumps({"entries": entries}, ensure_ascii=False, indent=2)


def convert_to_atom(entries: List[Dict[str, Any]], feed_title: str = "转换结果") -> str:
    """将条目列表转换为 Atom XML 字符串。"""
    return _entries_to_atom(entries, feed_title)


def convert_entries(entries: List[Dict[str, Any]], output_format: str) -> str:
    """根据输出格式转换条目列表。"""
    fmt = output_format.lower()
    if fmt == "json":
        return convert_to_json(entries)
    elif fmt in ("atom", "xml", "atom.xml"):
        return convert_to_atom(entries)
    else:
        fail("E007", f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------

def batch_process(sources: List[Tuple[str, str]], output_format: str) -> Dict[str, Any]:
    """
    批量处理多个数据源。

    sources: 列表，每个元素为 (source_type, content) 元组。
    返回汇总结果。
    """
    all_entries: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for idx, (src_type, content) in enumerate(sources):
        try:
            if src_type == "svn":
                entries = parse_svn_log(content)
            elif src_type == "rss":
                entries = parse_rss(content)
            elif src_type == "hatom":
                entries = parse_hatom(content)
            else:
                errors.append({"index": idx, "code": "E003", "message": f"不支持的数据源类型: {src_type}"})
                continue

            all_entries.extend(entries)
        except SubtletyError as e:
            errors.append({"index": idx, "code": e.code, "message": e.message})
        except Exception as e:
            errors.append({"index": idx, "code": "E010", "message": str(e)})

    if errors:
        # 部分失败但仍有成功条目时返回警告
        if all_entries:
            result = {
                "status": "partial",
                "entries": all_entries,
                "errors": errors,
                "converted": convert_entries(all_entries, output_format)
            }
            return result
        fail("E009", "批量处理全部失败: " + json.dumps(errors, ensure_ascii=False))

    return {
        "status": "success",
        "entries": all_entries,
        "converted": convert_entries(all_entries, output_format)
    }


# ---------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------

def read_input(source: str, input_format: str) -> str:
    """读取输入数据（文件或直接文本）。"""
    if source.startswith("http://") or source.startswith("https://"):
        fail("E002", "不支持网络 URL，请先下载文件或直接提供内容文本")

    # 尝试作为文件读取
    if os.path.isfile(source):
        try:
            with open(source, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, OSError) as e:
            fail("E002", f"无法读取文件 {source}: {e}")
    else:
        # 作为直接文本处理
        return source


def process_single_input(input_text: str, input_format: str, output_format: str) -> str:
    """处理单个输入并返回转换结果。"""
    fmt = input_format.lower()

    if fmt == "svn":
        entries = parse_svn_log(input_text)
    elif fmt == "rss":
        entries = parse_rss(input_text)
    elif fmt == "hatom":
        entries = parse_hatom(input_text)
    else:
        # 自动检测
        stripped = input_text.strip()
        if stripped.startswith("<?xml") or stripped.startswith("<rss") or stripped.startswith("<feed"):
            entries = parse_rss(input_text)
        elif "<html" in stripped.lower() or "hentry" in stripped.lower():
            entries = parse_hatom(input_text)
        elif re.search(r"^r\d+\s*\|", stripped, re.MULTILINE):
            entries = parse_svn_log(input_text)
        else:
            fail("E003", f"无法自动检测输入格式，请指定 --format 参数")

    return convert_entries(entries, output_format)


def run_selftest() -> int:
    """内置自检：使用硬编码样例数据验证核心逻辑。"""
    print("=== subtlety 自检开始 ===")

    # 1. SVN 解析测试
    svn_sample = """
------------------------------------------------------------------------
r123 | alice | 2025-01-15 10:30:00 +0800 (Wed, 15 Jan 2025) | 2 lines

修复登录模块的验证逻辑
详细描述内容...

------------------------------------------------------------------------
r124 | bob | 2025-01-16 14:00:00 +0800 (Thu, 16 Jan 2025) | 1 line

更新文档
"""
    try:
        svn_entries = parse_svn_log(svn_sample)
        assert len(svn_entries) >= 2, "SVN 解析应至少得到 2 条记录"
        assert svn_entries[0]["author"] == "alice", "SVN 作者解析错误"
        assert "123" in svn_entries[0]["id"], "SVN ID 解析错误"
        print("  [PASS] SVN 解析")
    except AssertionError as e:
        print(f"  [FAIL] SVN 解析: {e}")
        return 1
    except SubtletyError as e:
        print(f"  [FAIL] SVN 解析异常: {e}")
        return 1

    # 2. RSS 解析测试
    rss_sample = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>测试频道</title>
    <item>
      <title>第一篇文章</title>
      <link>https://example.com/post/1</link>
      <description>这是第一篇文章的摘要内容</description>
      <author>test@example.com</author>
      <pubDate>Wed, 15 Jan 2025 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>第二篇文章</title>
      <link>https://example.com/post/2</link>
      <description>第二篇的摘要</description>
    </item>
  </channel>
</rss>
"""
    try:
        rss_entries = parse_rss(rss_sample)
        assert len(rss_entries) >= 2, "RSS 解析应至少得到 2 条记录"
        assert rss_entries[0]["title"] == "第一篇文章", "RSS 标题解析错误"
        assert "https://example.com" in rss_entries[0]["link"], "RSS 链接解析错误"
        print("  [PASS] RSS 解析")
    except AssertionError as e:
        print(f"  [FAIL] RSS 解析: {e}")
        return 1
    except SubtletyError as e:
        print(f"  [FAIL] RSS 解析异常: {e}")
        return 1

    # 3. hAtom 解析测试
    hatom_sample = """
<html>
<body>
<div class="hentry">
  <h1 class="entry-title">我的博客文章</h1>
  <span class="author">张三</span>
  <time class="published" datetime="2025-01-15">2025年1月15日</time>
  <div class="entry-content"><p>这是文章内容。</p></div>
  <a href="https://example.com/blog/post-1">阅读更多</a>
</div>
<div class="hentry">
  <h1 class="entry-title">第二篇文章</h1>
  <span class="author">李四</span>
  <time class="published" datetime="2025-01-16">2025年1月16日</time>
  <div class="entry-content"><p>另一篇文章内容。</p></div>
  <a href="https://example.com/blog/post-2">链接</a>
</div>
</body>
</html>
"""
    try:
        hatom_entries = parse_hatom(hatom_sample)
        assert len(hatom_entries) >= 2, "hAtom 解析应至少得到 2 条记录"
        assert "张三" in hatom_entries[0]["author"], "hAtom 作者解析错误"
        assert "我的博客文章" in hatom_entries[0]["title"], "hAtom 标题解析错误"
        print("  [PASS] hAtom 解析")
    except AssertionError as e:
        print(f"  [FAIL] hAtom 解析: {e}")
        return 1
    except SubtletyError as e:
        print(f"  [FAIL] hAtom 解析异常: {e}")
        return 1

    # 4. 转换测试（JSON）
    try:
        json_result = convert_to_json(svn_entries)
        parsed = json.loads(json_result)
        assert "entries" in parsed, "JSON 转换结果缺少 entries 字段"
        assert len(parsed["entries"]) >= 2, "JSON 转换条目数量不正确"
        print("  [PASS] JSON 转换")
    except Exception as e:
        print(f"  [FAIL] JSON 转换: {e}")
        return 1

    # 5. 转换测试（Atom）
    try:
        atom_result = convert_to_atom(svn_entries, "自检 Feed")
        assert "<feed" in atom_result, "Atom 输出缺少 feed 标签"
        assert "<entry" in atom_result, "Atom 输出缺少 entry 标签"
        print("  [PASS] Atom 转换")
    except Exception as e:
        print(f"  [FAIL] Atom 转换: {e}")
        return 1

    # 6. 批量处理测试
    try:
        batch_result = batch_process(
            [("svn", svn_sample), ("rss", rss_sample)],
            "json"
        )
        assert batch_result["status"] == "success", "批量处理状态不正确"
        assert len(batch_result["entries"]) >= 4, "批量处理条目数量不足"
        assert "converted" in batch_result, "批量处理缺少转换结果"
        print("  [PASS] 批量处理")
    except Exception as e:
        print(f"  [FAIL] 批量处理: {e}")
        return 1

    # 7. 完整流程测试（文件模拟）
    try:
        result = process_single_input(svn_sample, "svn", "atom")
        assert "<feed" in result, "完整流程 Atom 输出错误"
        assert "SVN" in result or "entry" in result, "完整流程输出内容异常"
        print("  [PASS] 完整流程")
    except Exception as e:
        print(f"  [FAIL] 完整流程: {e}")
        return 1

    print("=== 全部自检通过 ===")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="subtlety — 数据源格式转换与结构化输出工具",
        epilog="支持 SVN 日志、RSS 2.0、hAtom 微格式 → Atom 1.0 / JSON"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--input", type=str, help="输入文件路径或直接文本内容")
    parser.add_argument("--format", type=str, choices=["svn", "rss", "hatom", "auto"],
                        default="auto", help="输入格式（默认自动检测）")
    parser.add_argument("--output", type=str, help="输出格式: json 或 atom（默认 json）")
    parser.add_argument("--output-file", type=str, help="输出文件路径（可选）")
    parser.add_argument("--batch", action="store_true", help="批量处理模式")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数检查
    if not args.input:
        parser.print_help()
        fail("E001", "必须提供 --input 参数")

    # 设置默认输出格式
    output_format = args.output or "json"

    try:
        # 读取输入
        input_text = read_input(args.input, args.format)

        # 处理转换
        if args.batch:
            # 批量模式：尝试分割输入为多个源
            # 简化实现：将输入按空行分割为多个块
            blocks = [b.strip() for b in input_text.split("\n\n") if b.strip()]
            sources = [(args.format if args.format != "auto" else "svn", b) for b in blocks]
            result = batch_process(sources, output_format)
            output_text = result["converted"]
        else:
            output_text = process_single_input(input_text, args.format, output_format)

        # 输出结果
        if args.output_file:
            try:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write(output_text)
                print(f"转换结果已写入: {args.output_file}")
            except (IOError, OSError) as e:
                fail("E005", f"无法写入输出文件: {e}")
        else:
            print(output_text)

        return 0

    except SubtletyError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
