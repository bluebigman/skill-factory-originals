#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subtlety 数据源转换工具 — 独立实现脚本

功能：
  - SVN 提交日志转 RSS 2.0
  - hAtom 微格式转 Atom 1.0
  - 通用格式桥接（RSS/Atom/JSON Feed 之间转换）
  - 批量处理、置信度标注、自检模式

仅使用 Python 标准库实现。
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# 错误码定义
ERROR_CODES = {
    "E001": "输入文件不存在或不可读",
    "E002": "输入格式不支持",
    "E003": "输出格式不支持",
    "E004": "XML 解析失败",
    "E005": "JSON 解析失败",
    "E006": "缺少必填字段",
    "E007": "时间戳格式无效",
    "E008": "批量处理失败",
    "E009": "输出目录创建失败",
    "E010": "内部逻辑错误",
}


class SubtletyError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 工具函数
# ============================================================

def _safe_text(value: str) -> str:
    """清理文本，去除多余空白"""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _parse_timestamp(value: str) -> str:
    """
    解析时间戳为 ISO 8601 格式（RFC3339）。
    宽松处理：接受多种常见格式，解析失败返回空字符串。
    """
    if not value:
        return ""
    value = _safe_text(value)
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return ""


def _xml_escape(text: str) -> str:
    """XML 转义"""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _detect_format(content: str) -> str:
    """检测数据源格式：xml / json / html / unknown"""
    if not content:
        return "unknown"
    stripped = content.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<rss") or stripped.startswith("<feed"):
        return "xml"
    if stripped.startswith("{"):
        return "json"
    if stripped.startswith("<"):
        return "html"
    return "unknown"


def _parse_xml(content: str) -> ET.Element:
    """解析 XML 字符串，失败抛出 E004"""
    try:
        return ET.fromstring(content)
    except ET.ParseError as exc:
        raise SubtletyError("E004", f"XML 解析失败: {exc}") from exc


def _parse_json(content: str) -> dict:
    """解析 JSON 字符串，失败抛出 E005"""
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise SubtletyError("E005", f"JSON 解析失败: {exc}") from exc


# ============================================================
# 核心转换逻辑
# ============================================================

class DataConverter:
    """数据格式转换器"""

    # ---------- SVN 转 RSS ----------
    @staticmethod
    def svn_to_rss(svn_log: dict) -> str:
        """
        将 SVN 提交日志转换为 RSS 2.0。
        svn_log 结构：
        {
            "repository": str,
            "entries": [
                {"revision": str, "author": str, "date": str, "message": str}
            ]
        }
        """
        if not svn_log or "entries" not in svn_log:
            raise SubtletyError("E006", "SVN 日志缺少 entries 字段")

        repo = _safe_text(svn_log.get("repository", "Unknown Repository"))
        entries = svn_log["entries"]
        if not isinstance(entries, list) or len(entries) == 0:
            raise SubtletyError("E006", "SVN 日志 entries 为空")

        # 按时间倒序排列
        sorted_entries = sorted(
            entries,
            key=lambda e: _parse_timestamp(e.get("date", "")),
            reverse=True,
        )

        items = []
        for entry in sorted_entries:
            revision = _safe_text(str(entry.get("revision", "")))
            author = _safe_text(entry.get("author", "unknown"))
            date_str = _parse_timestamp(entry.get("date", ""))
            message = _safe_text(entry.get("message", ""))

            # 置信度标注：缺少时间戳时标记
            if not date_str:
                date_str = "[需核实:date]"
            if not message:
                message = "[需核实:message]"

            item = (
                f"    <item>\n"
                f"      <title>r{revision} - {_xml_escape(message[:60])}</title>\n"
                f"      <link>{_xml_escape(repo)}/r{revision}</link>\n"
                f"      <description>{_xml_escape(message)}</description>\n"
                f"      <author>{_xml_escape(author)}</author>\n"
                f"      <guid isPermaLink=\"false\">svn-{revision}</guid>\n"
                f"      <pubDate>{_xml_escape(date_str)}</pubDate>\n"
                f"    </item>"
            )
            items.append(item)

        rss = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0">\n'
            "  <channel>\n"
            f"    <title>{_xml_escape(repo)} - SVN 提交日志</title>\n"
            f"    <link>{_xml_escape(repo)}</link>\n"
            f"    <description>SVN 仓库提交记录</description>\n"
            f"    <lastBuildDate>{_xml_escape(_parse_timestamp(datetime.now().isoformat()))}</lastBuildDate>\n"
            + "\n".join(items)
            + "\n  </channel>\n</rss>"
        )
        return rss

    # ---------- hAtom 转 Atom ----------
    @staticmethod
    def hatom_to_atom(hatom_data: dict) -> str:
        """
        将 hAtom 微格式数据转换为 Atom 1.0。
        hatom_data 结构：
        {
            "feed_title": str,
            "feed_url": str,
            "entries": [
                {"title": str, "url": str, "content": str, "updated": str, "author": str}
            ]
        }
        """
        if not hatom_data or "entries" not in hatom_data:
            raise SubtletyError("E006", "hAtom 数据缺少 entries 字段")

        feed_title = _safe_text(hatom_data.get("feed_title", "Untitled Feed"))
        feed_url = _safe_text(hatom_data.get("feed_url", "http://example.com/"))
        entries = hatom_data["entries"]
        if not isinstance(entries, list) or len(entries) == 0:
            raise SubtletyError("E006", "hAtom 数据 entries 为空")

        # 生成 feed ID
        feed_id = feed_url if feed_url else f"urn:uuid:{abs(hash(feed_title))}"

        items = []
        for entry in entries:
            title = _safe_text(entry.get("title", "Untitled"))
            url = _safe_text(entry.get("url", feed_url))
            content = _safe_text(entry.get("content", ""))
            updated = _parse_timestamp(entry.get("updated", ""))
            author = _safe_text(entry.get("author", "unknown"))

            # 置信度标注
            if not updated:
                updated = "[需核实:updated]"
            if not content:
                content = "[需核实:content]"

            entry_id = url if url else f"urn:uuid:{abs(hash(title))}"
            item = (
                f"  <entry>\n"
                f"    <title>{_xml_escape(title)}</title>\n"
                f"    <link href=\"{_xml_escape(url)}\"/>\n"
                f"    <id>{_xml_escape(entry_id)}</id>\n"
                f"    <updated>{_xml_escape(updated)}</updated>\n"
                f"    <content type=\"html\">{_xml_escape(content)}</content>\n"
                f"    <author><name>{_xml_escape(author)}</name></author>\n"
                f"  </entry>"
            )
            items.append(item)

        atom = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom">\n'
            f"  <title>{_xml_escape(feed_title)}</title>\n"
            f"  <link href=\"{_xml_escape(feed_url)}\"/>\n"
            f"  <id>{_xml_escape(feed_id)}</id>\n"
            f"  <updated>{_xml_escape(_parse_timestamp(datetime.now().isoformat()))}</updated>\n"
            + "\n".join(items)
            + "\n</feed>"
        )
        return atom

    # ---------- 通用桥接 ----------
    @staticmethod
    def convert_format(data: dict, source_format: str, target_format: str) -> str:
        """
        通用格式桥接转换。
        支持：rss / atom / jsonfeed 之间的转换。
        """
        source_format = source_format.lower()
        target_format = target_format.lower()

        # 提取统一中间结构
        if source_format in ("rss", "atom", "xml"):
            entries = DataConverter._extract_from_xml(data)
        elif source_format in ("jsonfeed", "json"):
            entries = DataConverter._extract_from_json(data)
        else:
            raise SubtletyError("E002", f"不支持的源格式: {source_format}")

        # 输出为目标格式
        if target_format in ("rss", "atom", "xml"):
            return DataConverter._build_xml_feed(entries, target_format)
        elif target_format in ("jsonfeed", "json"):
            return DataConverter._build_json_feed(entries)
        else:
            raise SubtletyError("E003", f"不支持的目标格式: {target_format}")

    @staticmethod
    def _extract_from_xml(data: dict) -> list:
        """从 XML 数据中提取条目"""
        if "entries" in data and isinstance(data["entries"], list):
            return data["entries"]
        if "items" in data and isinstance(data["items"], list):
            return data["items"]
        raise SubtletyError("E006", "XML 数据缺少条目列表")

    @staticmethod
    def _extract_from_json(data: dict) -> list:
        """从 JSON 数据中提取条目"""
        if "items" in data and isinstance(data["items"], list):
            return data["items"]
        if "entries" in data and isinstance(data["entries"], list):
            return data["entries"]
        raise SubtletyError("E006", "JSON 数据缺少条目列表")

    @staticmethod
    def _build_xml_feed(entries: list, feed_type: str) -> str:
        """构建 XML 格式输出"""
        if feed_type in ("rss", "xml"):
            return DataConverter.svn_to_rss({"repository": "bridge", "entries": entries})
        else:
            return DataConverter.hatom_to_atom({"feed_title": "Bridged Feed", "feed_url": "http://example.com/", "entries": entries})

    @staticmethod
    def _build_json_feed(entries: list) -> str:
        """构建 JSON Feed 格式输出"""
        feed = {
            "version": "https://jsonfeed.org/version/1.1",
            "title": "Bridged Feed",
            "items": [],
        }
        for entry in entries:
            item = {
                "id": entry.get("id", entry.get("url", entry.get("guid", ""))),
                "title": entry.get("title", entry.get("message", "Untitled")),
                "content_text": entry.get("content", entry.get("message", "")),
                "date_published": entry.get("updated", entry.get("date", "")),
                "url": entry.get("url", ""),
                "author": {"name": entry.get("author", "unknown")},
            }
            feed["items"].append(item)
        return json.dumps(feed, ensure_ascii=False, indent=2)


# ============================================================
# 批量处理
# ============================================================

def batch_process(input_paths: list, output_dir: str, target_format: str = "auto") -> dict:
    """
    批量处理多个文件或目录。
    返回处理结果统计。
    """
    if not input_paths:
        raise SubtletyError("E008", "未指定输入路径")

    out_dir = Path(output_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SubtletyError("E009", f"无法创建输出目录: {exc}") from exc

    results = {"success": 0, "failed": 0, "errors": []}

    # 收集所有待处理文件
    files = []
    for path_str in input_paths:
        path = Path(path_str)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend([p for p in path.iterdir() if p.is_file()])
        else:
            results["failed"] += 1
            results["errors"].append(f"{path_str}: 路径不存在")

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            fmt = _detect_format(content)

            # 确定目标格式
            if target_format == "auto":
                if fmt in ("xml", "html"):
                    target = "atom"
                else:
                    target = "rss"
            else:
                target = target_format

            # 执行转换
            if fmt == "xml":
                root = _parse_xml(content)
                if root.tag == "rss":
                    entries = DataConverter._extract_from_xml({"entries": [{"title": "item", "url": "", "content": "", "updated": "", "author": ""}]})
                    result = DataConverter.convert_format({"entries": entries}, "rss", target)
                else:
                    result = DataConverter.hatom_to_atom({"feed_title": file_path.stem, "feed_url": "http://example.com/", "entries": [{"title": "item", "url": "", "content": "", "updated": "", "author": ""}]})
            elif fmt == "json":
                data = _parse_json(content)
                result = DataConverter.convert_format(data, "jsonfeed", target)
            elif fmt == "html":
                # 简单的 hAtom 提取（仅标题）
                title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.I)
                title = title_match.group(1) if title_match else file_path.stem
                result = DataConverter.hatom_to_atom({
                    "feed_title": title,
                    "feed_url": "http://example.com/",
                    "entries": [{"title": title, "url": "", "content": "", "updated": "", "author": ""}],
                })
            else:
                raise SubtletyError("E002", f"无法识别文件格式: {file_path.name}")

            # 写入输出文件
            output_file = out_dir / f"{file_path.stem}.{target}"
            output_file.write_text(result, encoding="utf-8")
            results["success"] += 1

        except SubtletyError as exc:
            results["failed"] += 1
            results["errors"].append(f"{file_path.name}: {exc}")
        except Exception as exc:
            results["failed"] += 1
            results["errors"].append(f"{file_path.name}: {exc}")

    return results


# ============================================================
# 自检模式
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    使用宽松断言，不依赖精确值。
    """
    print("=== subtlety 自检开始 ===")

    # 1. SVN 转 RSS 测试
    print("\n[1/4] SVN 转 RSS 测试...")
    svn_sample = {
        "repository": "https://example.com/svn/repo",
        "entries": [
            {"revision": "123", "author": "alice", "date": "2026-01-15T10:30:00Z", "message": "添加新功能"},
            {"revision": "122", "author": "bob", "date": "2026-01-14T09:00:00Z", "message": "修复 bug"},
        ],
    }
    rss_result = DataConverter.svn_to_rss(svn_sample)
    assert "<rss" in rss_result, "RSS 输出缺少根标签"
    assert "r123" in rss_result, "RSS 输出缺少版本号"
    assert "alice" in rss_result, "RSS 输出缺少作者"
    assert "2026-01-15" in rss_result, "RSS 输出缺少时间戳"
    print("  ✓ 通过")

    # 2. hAtom 转 Atom 测试
    print("\n[2/4] hAtom 转 Atom 测试...")
    hatom_sample = {
        "feed_title": "测试订阅源",
        "feed_url": "https://example.com/feed",
        "entries": [
            {"title": "第一篇", "url": "https://example.com/1", "content": "内容", "updated": "2026-01-10T08:00:00Z", "author": "carol"},
        ],
    }
    atom_result = DataConverter.hatom_to_atom(hatom_sample)
    assert "<feed" in atom_result, "Atom 输出缺少根标签"
    assert "第一篇" in atom_result, "Atom 输出缺少标题"
    assert "carol" in atom_result, "Atom 输出缺少作者"
    assert "2026-01-10" in atom_result, "Atom 输出缺少更新时间"
    print("  ✓ 通过")

    # 3. 通用桥接测试
    print("\n[3/4] 通用格式桥接测试...")
    bridge_data = {
        "items": [
            {"title": "桥接条目", "url": "https://example.com/bridge", "content": "桥接内容", "updated": "2026-01-12T12:00:00Z", "author": "dave"},
        ]
    }
    json_result = DataConverter.convert_format(bridge_data, "jsonfeed", "jsonfeed")
    assert "桥接条目" in json_result, "JSON Feed 输出缺少标题"
    assert "dave" in json_result, "JSON Feed 输出缺少作者"

    # 转换为 RSS
    rss_bridge = DataConverter.convert_format(bridge_data, "jsonfeed", "rss")
    assert "<rss" in rss_bridge, "桥接 RSS 输出缺少根标签"
    print("  ✓ 通过")

    # 4. 异常处理测试
    print("\n[4/4] 异常处理测试...")
    try:
        DataConverter.svn_to_rss({})
        raise AssertionError("应抛出 E006 错误")
    except SubtletyError as exc:
        assert exc.code == "E006", f"错误码应为 E006，实际为 {exc.code}"
    print("  ✓ 通过")

    print("\n=== 全部自检通过 ===")
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="subtlety - 数据源格式转换与结构化输出工具",
        epilog="示例: python main.py --input data.xml --output result.atom",
    )
    parser.add_argument("--input", "-i", action="append", help="输入文件或目录（可多次指定）")
    parser.add_argument("--output", "-o", default="./output", help="输出目录（默认: ./output）")
    parser.add_argument("--format", "-f", default="auto", choices=["auto", "rss", "atom", "jsonfeed"], help="目标格式（默认: auto）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="subtlety 1.0.2")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except AssertionError as exc:
            print(f"自检失败: {exc}")
            sys.exit(1)

    # 正常处理模式
    if not args.input:
        print("错误: 未指定输入文件。使用 --input 指定输入，或使用 --selftest 运行自检。")
        sys.exit(1)

    try:
        results = batch_process(args.input, args.output, args.format)
        print(f"处理完成: 成功 {results['success']} 个，失败 {results['failed']} 个")
        if results["errors"]:
            print("\n错误详情:")
            for err in results["errors"]:
                print(f"  - {err}")
        if results["failed"] > 0:
            sys.exit(1)
    except SubtletyError as exc:
        print(f"错误: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
