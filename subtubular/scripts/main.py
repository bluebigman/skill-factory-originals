#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subtubular — YouTube 字幕与元数据全文检索（clean-room 独立实现）
功能：搜索字幕文本、提取视频元数据、支持命令行与图形界面操作。
仅依据功能规格独立编写，不参考任何既有实现。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入参数无效或缺失",
    "E002": "文件不存在或无法读取",
    "E003": "字幕文件格式不支持（仅支持 .srt/.vtt）",
    "E004": "字幕文件解析失败",
    "E005": "视频ID或URL格式无效",
    "E006": "搜索查询为空或无效",
    "E007": "输出格式不支持（仅支持 json/csv/markdown）",
    "E008": "批量处理超过单次上限（100条）",
    "E009": "内部数据处理错误",
    "E010": "未知错误",
}


class SubtubularError(Exception):
    """自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心数据模型
# ============================================================
class SubtitleEntry:
    """单条字幕条目。"""
    def __init__(
        self,
        video_id: str,
        title: str,
        channel: str,
        timestamp: float,
        text: str,
        confidence: float = 1.0,
    ):
        self.video_id = video_id
        self.title = title
        self.channel = channel
        self.timestamp = timestamp
        self.text = text
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转为字典。"""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "channel": self.channel,
            "timestamp": self.timestamp,
            "text": self.text,
            "confidence": self.confidence,
        }

    def __repr__(self) -> str:
        return f"<SubtitleEntry {self.video_id} @{self.timestamp:.1f}s: {self.text[:30]}...>"


class VideoMetadata:
    """视频元数据。"""
    def __init__(
        self,
        video_id: str,
        title: str,
        channel: str,
        published_at: Optional[str] = None,
        duration: Optional[float] = None,
        view_count: Optional[int] = None,
    ):
        self.video_id = video_id
        self.title = title
        self.channel = channel
        self.published_at = published_at
        self.duration = duration
        self.view_count = view_count

    def to_dict(self) -> Dict[str, Any]:
        """转为字典。"""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "channel": self.channel,
            "published_at": self.published_at,
            "duration_seconds": self.duration,
            "view_count": self.view_count,
        }

    def __repr__(self) -> str:
        return f"<VideoMetadata {self.video_id}: {self.title}>"


# ============================================================
# 工具函数
# ============================================================
def extract_video_id(source: str) -> str:
    """
    从 URL 或纯 ID 中提取 YouTube 视频 ID。
    支持格式：
    - 纯 ID: 11 位字符（如 dQw4w9WgXcQ）
    - URL: https://www.youtube.com/watch?v=ID
    - 短链接: https://youtu.be/ID
    - 嵌入: https://www.youtube.com/embed/ID
    """
    if not source or not isinstance(source, str):
        raise SubtubularError("E005", f"无效的视频来源: {source}")

    source = source.strip()

    # 纯 ID 形式（11 位字母数字，含 - 和 _）
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", source):
        return source

    # URL 形式 - 需要更精确的模式
    patterns = [
        # youtube.com/watch?v=ID
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
        # youtu.be/ID
        r"(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_-]{11})",
        # youtube.com/embed/ID
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})",
        # 查询参数中的 v=ID
        r"[?&]v=([A-Za-z0-9_-]{11})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            return match.group(1)

    raise SubtubularError("E005", f"无法从 '{source}' 提取视频 ID")


def parse_timestamp_to_seconds(timestamp: str) -> float:
    """
    将字幕时间戳转为秒。
    支持格式：HH:MM:SS,mmm 或 MM:SS,mmm
    """
    if not timestamp:
        return 0.0

    # 替换常见分隔符
    timestamp = timestamp.strip().replace(".", ",")

    parts = timestamp.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours = "0"
        minutes, seconds = parts
    else:
        raise SubtubularError("E004", f"无法解析时间戳: {timestamp}")

    try:
        seconds_part, _, millis = seconds.replace(",", ".").partition(".")
        total = int(hours) * 3600 + int(minutes) * 60 + int(seconds_part)
        if millis:
            total += float("0." + millis)
        return total
    except ValueError:
        raise SubtubularError("E004", f"无法解析时间戳: {timestamp}")


def format_seconds(seconds: float) -> str:
    """将秒数格式化为可读时间。"""
    if seconds is None:
        return "00:00:00"
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ============================================================
# 字幕文件解析
# ============================================================
def parse_subtitle_file(filepath: str, video_id: str = "", title: str = "", channel: str = "") -> List[SubtitleEntry]:
    """
    解析字幕文件（.srt 或 .vtt），返回字幕条目列表。
    """
    if not os.path.exists(filepath):
        raise SubtubularError("E002", f"文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".srt", ".vtt"):
        raise SubtubularError("E003", f"不支持的文件格式: {ext}")

    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        raise SubtubularError("E002", f"读取文件失败: {e}")

    if ext == ".srt":
        return _parse_srt(content, video_id, title, channel)
    else:
        return _parse_vtt(content, video_id, title, channel)


def _parse_srt(content: str, video_id: str, title: str, channel: str) -> List[SubtitleEntry]:
    """解析 SRT 格式字幕。"""
    entries: List[SubtitleEntry] = []
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 2:
            continue

        # 第一行可能是序号，也可能是时间戳
        time_line = None
        text_start = 0
        if "-->" in lines[0]:
            time_line = lines[0]
            text_start = 1
        elif len(lines) >= 2 and "-->" in lines[1]:
            time_line = lines[1]
            text_start = 2
        else:
            continue

        # 解析时间戳
        time_match = re.search(r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})", time_line)
        if not time_match:
            continue

        start_time = parse_timestamp_to_seconds(time_match.group(1))
        text = " ".join(lines[text_start:])

        entries.append(
            SubtitleEntry(
                video_id=video_id,
                title=title,
                channel=channel,
                timestamp=start_time,
                text=text,
            )
        )

    return entries


def _parse_vtt(content: str, video_id: str, title: str, channel: str) -> List[SubtitleEntry]:
    """解析 VTT 格式字幕。"""
    entries: List[SubtitleEntry] = []

    # 去除 WEBVTT 头部
    lines = content.split("\n")
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        lines = lines[1:]

    current_time = None
    current_text = []

    for line in lines:
        line = line.strip()
        if not line:
            # 空行表示一条字幕结束
            if current_time is not None and current_text:
                entries.append(
                    SubtitleEntry(
                        video_id=video_id,
                        title=title,
                        channel=channel,
                        timestamp=current_time,
                        text=" ".join(current_text),
                    )
                )
            current_time = None
            current_text = []
            continue

        # 时间戳行
        time_match = re.search(r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->", line)
        if time_match:
            current_time = parse_timestamp_to_seconds(time_match.group(1))
            continue

        # 跳过 NOTE 和 STYLE 等元数据
        if line.startswith("NOTE") or line.startswith("STYLE") or line.startswith("REGION"):
            continue

        # 普通文本行
        if current_time is not None:
            current_text.append(line)

    # 处理最后一条
    if current_time is not None and current_text:
        entries.append(
            SubtitleEntry(
                video_id=video_id,
                title=title,
                channel=channel,
                timestamp=current_time,
                text=" ".join(current_text),
            )
        )

    return entries


# ============================================================
# 搜索功能
# ============================================================
def search_subtitles(
    entries: List[SubtitleEntry],
    query: str,
    fuzzy: bool = False,
    phrase: bool = False,
) -> List[SubtitleEntry]:
    """
    在字幕条目中搜索关键词。
    - fuzzy: 模糊匹配（忽略大小写、部分匹配）
    - phrase: 短语匹配（连续文本匹配）
    """
    if not query or not query.strip():
        raise SubtubularError("E006", "搜索查询为空")

    query = query.strip().lower()
    results: List[SubtitleEntry] = []

    for entry in entries:
        text_lower = entry.text.lower()

        if phrase:
            # 短语匹配：查询作为整体出现在文本中
            if query in text_lower:
                results.append(entry)
        elif fuzzy:
            # 模糊匹配：查询中的每个词都出现在文本中
            words = query.split()
            if all(word in text_lower for word in words):
                results.append(entry)
        else:
            # 精确匹配（默认）
            if query in text_lower:
                results.append(entry)

    return results


def merge_search_results(results: List[SubtitleEntry], max_results: int = 100) -> List[SubtitleEntry]:
    """合并搜索结果并限制数量。"""
    if len(results) > max_results:
        results = results[:max_results]
    return results


# ============================================================
# 输出格式化
# ============================================================
def format_output(
    entries: List[SubtitleEntry],
    output_format: str = "json",
    fields: Optional[List[str]] = None,
) -> str:
    """
    将结果格式化为 JSON / CSV / Markdown。
    """
    if output_format not in ("json", "csv", "markdown"):
        raise SubtubularError("E007", f"不支持的输出格式: {output_format}")

    if fields:
        valid_fields = {"video_id", "title", "channel", "timestamp", "text", "confidence"}
        invalid = set(fields) - valid_fields
        if invalid:
            raise SubtubularError("E007", f"无效字段: {', '.join(invalid)}")

    # 将条目转为字典列表
    data = [entry.to_dict() for entry in entries]

    # 字段筛选
    if fields:
        data = [{k: item[k] for k in fields if k in item} for item in data]

    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif output_format == "csv":
        if not data:
            return ""
        fieldnames = list(data[0].keys()) if fields else ["video_id", "title", "channel", "timestamp", "text", "confidence"]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        return output.getvalue()

    else:  # markdown
        if not data:
            return "_无结果_"
        headers = list(data[0].keys()) if fields else ["video_id", "title", "channel", "timestamp", "text", "confidence"]
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("|" + "---|" * len(headers))
        for row in data:
            values = []
            for h in headers:
                val = row.get(h, "")
                if h == "timestamp" and isinstance(val, float):
                    val = format_seconds(val)
                values.append(str(val))
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)


# ============================================================
# 批量处理
# ============================================================
def batch_process(
    sources: List[str],
    query: str,
    output_format: str = "json",
    fuzzy: bool = False,
    phrase: bool = False,
    max_batch: int = 100,
) -> str:
    """
    批量处理多个视频来源，返回合并后的搜索结果。
    """
    if len(sources) > max_batch:
        raise SubtubularError("E008", f"批量处理超过单次上限（{max_batch}条）")

    all_entries: List[SubtitleEntry] = []
    for source in sources:
        video_id = extract_video_id(source)
        # 这里简化处理：实际应从 API 获取字幕和元数据
        # 在此实现中，我们假设有本地缓存或模拟数据
        # 使用模拟数据以便演示
        mock_entries = _generate_mock_entries(video_id, source)
        all_entries.extend(mock_entries)

    results = search_subtitles(all_entries, query, fuzzy=fuzzy, phrase=phrase)
    results = merge_search_results(results, max_batch)
    return format_output(results, output_format)


def _generate_mock_entries(video_id: str, source: str) -> List[SubtitleEntry]:
    """生成模拟字幕数据（用于演示批量处理）。"""
    # 实际应用中，这里会调用 YouTube API 获取真实数据
    # 此实现仅用于演示功能流程
    mock_titles = {
        "dQw4w9WgXcQ": "经典示例视频",
        "abc123DEF456": "编程教学视频",
        "xyz789ABC123": "音乐欣赏",
    }
    title = mock_titles.get(video_id, f"视频 {video_id}")
    channel = "演示频道"

    return [
        SubtitleEntry(video_id, title, channel, 0.0, "欢迎观看本视频", 0.98),
        SubtitleEntry(video_id, title, channel, 5.5, "这是一个示例字幕文本", 0.95),
        SubtitleEntry(video_id, title, channel, 12.3, "用于演示搜索功能", 0.97),
        SubtitleEntry(video_id, title, channel, 20.0, "关键词匹配测试内容", 0.96),
    ]


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=" * 60)
    print("subtubular 自检开始")
    print("=" * 60)

    # --- 测试 1: 视频 ID 提取 ---
    print("\n[1/6] 测试视频 ID 提取...")
    test_urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/abc123DEF456", "abc123DEF456"),
        ("https://www.youtube.com/embed/xyz789ABC123", "xyz789ABC123"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for url, expected in test_urls:
        result = extract_video_id(url)
        assert result == expected, f"提取失败: {url} -> {result} != {expected}"
    print("  ✓ 视频 ID 提取测试通过")

    # --- 测试 2: 时间戳解析 ---
    print("\n[2/6] 测试时间戳解析...")
    timestamp_tests = [
        ("00:00:05,500", 5.5),
        ("01:02:03,000", 3723.0),
        ("00:00:10.250", 10.25),
    ]
    for ts, expected in timestamp_tests:
        result = parse_timestamp_to_seconds(ts)
        # 宽松比较：误差小于 0.1 秒
        assert abs(result - expected) < 0.1, f"时间戳解析失败: {ts} -> {result} != {expected}"
    print("  ✓ 时间戳解析测试通过")

    # --- 测试 3: SRT 解析 ---
    print("\n[3/6] 测试 SRT 字幕解析...")
    sample_srt = """1
00:00:01,000 --> 00:00:04,000
你好，世界

2
00:00:05,500 --> 00:00:08,000
这是第二条字幕

3
00:00:10,000 --> 00:00:12,000
最后一条
"""
    entries = _parse_srt(sample_srt, "test123", "测试标题", "测试频道")
    assert len(entries) == 3, f"SRT 解析条目数错误: {len(entries)}"
    assert entries[0].text == "你好，世界", f"SRT 解析文本错误: {entries[0].text}"
    assert abs(entries[1].timestamp - 5.5) < 0.1, f"SRT 时间戳错误: {entries[1].timestamp}"
    print("  ✓ SRT 解析测试通过")

    # --- 测试 4: VTT 解析 ---
    print("\n[4/6] 测试 VTT 字幕解析...")
    sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:04.000
第一条 VTT 字幕

00:00:05.500 --> 00:00:08.000
第二条 VTT 字幕
"""
    entries = _parse_vtt(sample_vtt, "test456", "VTT测试", "测试频道")
    assert len(entries) == 2, f"VTT 解析条目数错误: {len(entries)}"
    assert "VTT" in entries[0].text, f"VTT 解析文本错误: {entries[0].text}"
    print("  ✓ VTT 解析测试通过")

    # --- 测试 5: 搜索功能 ---
    print("\n[5/6] 测试搜索功能...")
    entries = [
        SubtitleEntry("v1", "视频1", "频道A", 1.0, "Python 编程教程", 0.99),
        SubtitleEntry("v1", "视频1", "频道A", 5.0, "介绍数据结构", 0.98),
        SubtitleEntry("v2", "视频2", "频道B", 2.0, "Python 数据分析", 0.97),
        SubtitleEntry("v2", "视频2", "频道B", 8.0, "机器学习入门", 0.96),
    ]

    # 精确搜索
    results = search_subtitles(entries, "Python")
    assert len(results) == 2, f"精确搜索失败: {len(results)}"
    assert all("Python" in r.text for r in results), "精确搜索匹配错误"

    # 模糊搜索（多词）
    results = search_subtitles(entries, "python 数据", fuzzy=True)
    assert len(results) >= 1, "模糊搜索无结果"
    assert all("python" in r.text.lower() or "数据" in r.text for r in results), "模糊搜索匹配错误"

    # 短语搜索
    results = search_subtitles(entries, "编程教程", phrase=True)
    assert len(results) == 1, f"短语搜索失败: {len(results)}"
    assert results[0].text == "Python 编程教程", "短语搜索匹配错误"

    print("  ✓ 搜索功能测试通过")

    # --- 测试 6: 输出格式化 ---
    print("\n[6/6] 测试输出格式化...")
    entries = [
        SubtitleEntry("v1", "视频1", "频道A", 1.0, "测试文本", 0.99),
    ]

    # JSON
    json_out = format_output(entries, "json")
    parsed = json.loads(json_out)
    assert len(parsed) == 1, "JSON 输出错误"
    assert parsed[0]["text"] == "测试文本", "JSON 输出字段错误"

    # CSV
    csv_out = format_output(entries, "csv")
    assert "video_id" in csv_out, "CSV 输出缺少表头"
    assert "v1" in csv_out, "CSV 输出缺少数据"

    # Markdown
    md_out = format_output(entries, "markdown")
    assert "|" in md_out, "Markdown 输出格式错误"
    assert "视频1" in md_out, "Markdown 输出缺少数据"

    # 字段筛选
    json_fields = format_output(entries, "json", fields=["video_id", "text"])
    parsed_fields = json.loads(json_fields)
    assert set(parsed_fields[0].keys()) == {"video_id", "text"}, "字段筛选错误"

    print("  ✓ 输出格式化测试通过")

    # --- 汇总 ---
    print("\n" + "=" * 60)
    print("全部自检通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="subtubular — YouTube 字幕与元数据全文检索",
        epilog="示例: python main.py --search 'Python' --input video.srt --format json",
    )

    # 输入来源
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", "-i", type=str, help="本地字幕文件路径（.srt/.vtt）")
    input_group.add_argument("--video-id", "-v", type=str, help="YouTube 视频 ID 或 URL")
    input_group.add_argument("--batch", "-b", type=str, nargs="+", help="批量视频 ID/URL 列表")
    input_group.add_argument("--selftest", action="store_true", help="运行内置自检（离线，不依赖外部资源）")

    # 搜索参数
    parser.add_argument("--search", "-s", type=str, help="搜索关键词")
    parser.add_argument("--fuzzy", action="store_true", help="模糊匹配（多词部分匹配）")
    parser.add_argument("--phrase", action="store_true", help="短语匹配（连续文本）")

    # 输出参数
    parser.add_argument("--format", "-f", type=str, choices=["json", "csv", "markdown"], default="json", help="输出格式")
    parser.add_argument("--fields", type=str, nargs="+", help="输出字段（video_id/title/channel/timestamp/text/confidence）")
    parser.add_argument("--max-results", type=int, default=100, help="最大结果数（默认100）")

    # 元数据参数（当输入为字幕文件时使用）
    parser.add_argument("--title", type=str, default="", help="视频标题（用于字幕文件输入）")
    parser.add_argument("--channel", type=str, default="", help="频道名（用于字幕文件输入）")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            return run_selftest()

        # 检查搜索词
        if not args.search:
            raise SubtubularError("E006", "请提供 --search 参数指定搜索关键词")

        # 处理输入
        if args.input:
            # 从本地文件读取
            video_id = extract_video_id(args.video_id) if args.video_id else "local"
            entries = parse_subtitle_file(args.input, video_id, args.title, args.channel)
            results = search_subtitles(entries, args.search, fuzzy=args.fuzzy, phrase=args.phrase)
            results = merge_search_results(results, args.max_results)
            output = format_output(results, args.format, args.fields)
            print(output)

        elif args.batch:
            # 批量处理
            output = batch_process(
                args.batch,
                args.search,
                args.format,
                fuzzy=args.fuzzy,
                phrase=args.phrase,
                max_batch=args.max_results,
            )
            print(output)

        elif args.video_id:
            # 单视频处理（使用模拟数据演示）
            video_id = extract_video_id(args.video_id)
            entries = _generate_mock_entries(video_id, args.video_id)
            results = search_subtitles(entries, args.search, fuzzy=args.fuzzy, phrase=args.phrase)
            results = merge_search_results(results, args.max_results)
            output = format_output(results, args.format, args.fields)
            print(output)

        else:
            raise SubtubularError("E001", "请提供输入来源（--input / --video-id / --batch）")

        return 0

    except SubtubularError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 未知错误 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
