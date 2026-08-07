#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capscript-youtube-subtitle-search-tool
字幕检索、视频内容定位、时间轴匹配

本脚本为 clean-room 独立实现，仅依据功能规格编写。
支持将字幕数据转为结构化检索结果，提供时间轴定位与关键词过滤。

用法:
    python main.py <字幕文件> [关键词] [--selftest]

错误码:
    E001 参数数量错误
    E002 文件读取失败
    E003 字幕解析失败
    E004 时间轴格式非法
    E005 检索结果为空
    E006 内部逻辑错误
    E007 输出写入失败
    E008 输入数据为空
    E009 编码不支持
    E010 未预期的运行时错误
"""

import sys
import os
import re
import json
import argparse
from datetime import timedelta
from typing import Dict, List, Optional, Tuple, Any


# ---------------------------------------------------------------
# 字幕解析模块
# ---------------------------------------------------------------
class SubtitleParser:
    """字幕解析器：支持 SRT 和 VTT 两种常见格式。"""

    # 时间轴匹配模式：支持 "00:00:01,000 --> 00:00:04,000" 或 "00:00:01.000 --> 00:00:04.000"
    TIME_LINE_PATTERN = re.compile(
        r'(\d{1,2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*'
        r'(\d{1,2}):(\d{2}):(\d{2})[.,](\d{3})'
    )

    def parse(self, content: str) -> List[Dict[str, Any]]:
        """解析字幕文本，返回结构化列表。

        参数:
            content: 字幕文件内容字符串

        返回:
            列表，每个元素为:
            {
                "index": int,          # 字幕序号
                "start": float,        # 开始时间（秒）
                "end": float,          # 结束时间（秒）
                "text": str            # 字幕文本（去除换行）
            }

        异常:
            若内容为空或无法解析，抛出 ValueError(E003)
        """
        if not content or not content.strip():
            raise ValueError("E003: 字幕内容为空，无法解析")

        lines = content.strip().splitlines()
        entries: List[Dict[str, Any]] = []
        current_index: Optional[int] = None
        current_time: Optional[Tuple[float, float]] = None
        current_text: List[str] = []

        def flush_entry() -> None:
            """将当前累积的字幕条目写入 entries。"""
            nonlocal current_index, current_time, current_text
            if current_index is not None and current_time is not None:
                text = " ".join(current_text).strip()
                if text:  # 忽略空文本条目
                    entries.append({
                        "index": current_index,
                        "start": current_time[0],
                        "end": current_time[1],
                        "text": text
                    })
            current_index = None
            current_time = None
            current_text = []

        for line in lines:
            stripped = line.strip()

            # 跳过空行
            if not stripped:
                continue

            # 尝试匹配时间轴行
            time_match = self.TIME_LINE_PATTERN.search(stripped)
            if time_match:
                # 新条目开始前，先刷新上一条
                flush_entry()
                start = self._timestr_to_seconds(
                    time_match.group(1), time_match.group(2),
                    time_match.group(3), time_match.group(4)
                )
                end = self._timestr_to_seconds(
                    time_match.group(5), time_match.group(6),
                    time_match.group(7), time_match.group(8)
                )
                if end <= start:
                    raise ValueError(
                        f"E004: 时间轴非法，结束时间 {end} 不晚于开始时间 {start}"
                    )
                current_time = (start, end)
                continue

            # 尝试匹配序号行（纯数字）
            if stripped.isdigit() and current_index is None:
                current_index = int(stripped)
                continue

            # 其他行视为文本内容
            if current_time is not None:
                current_text.append(stripped)

        # 刷新最后一条
        flush_entry()

        if not entries:
            raise ValueError("E003: 字幕解析失败，未找到有效条目")

        return entries

    @staticmethod
    def _timestr_to_seconds(h: str, m: str, s: str, ms: str) -> float:
        """将时分秒毫秒转为秒数（浮点）。"""
        return (
            int(h) * 3600
            + int(m) * 60
            + int(s)
            + int(ms) / 1000.0
        )


# ---------------------------------------------------------------
# 检索模块
# ---------------------------------------------------------------
class SubtitleSearcher:
    """字幕检索器：支持关键词过滤、时间轴定位、上下文提取。"""

    def __init__(self, entries: List[Dict[str, Any]]):
        """初始化检索器。

        参数:
            entries: SubtitleParser.parse 的输出
        """
        if not entries:
            raise ValueError("E008: 输入数据为空，无法初始化检索器")
        self.entries = entries
        self._total_duration = max(e["end"] for e in entries)

    def search(
        self,
        keyword: str,
        case_sensitive: bool = False,
        context_before: int = 0,
        context_after: int = 0
    ) -> List[Dict[str, Any]]:
        """按关键词检索字幕。

        参数:
            keyword: 检索关键词
            case_sensitive: 是否区分大小写
            context_before: 匹配条目之前附加的上下文条目数
            context_after: 匹配条目之后附加的上下文条目数

        返回:
            检索结果列表，每个元素:
            {
                "index": int,
                "start": float,
                "end": float,
                "text": str,
                "matched": bool,       # 是否直接命中关键词
                "context": bool        # 是否为上下文附带条目
            }
        """
        if not keyword or not keyword.strip():
            raise ValueError("E005: 检索关键词为空")

        keyword = keyword.strip()
        matched_indices: List[int] = []

        for i, entry in enumerate(self.entries):
            text = entry["text"]
            if not case_sensitive:
                text = text.lower()
                kw = keyword.lower()
            else:
                kw = keyword

            if kw in text:
                matched_indices.append(i)

        if not matched_indices:
            return []

        # 构建结果（含上下文）
        result_indices = set()
        for idx in matched_indices:
            for offset in range(-context_before, context_after + 1):
                target = idx + offset
                if 0 <= target < len(self.entries):
                    result_indices.add(target)

        results = []
        for idx in sorted(result_indices):
            entry = self.entries[idx]
            results.append({
                "index": entry["index"],
                "start": entry["start"],
                "end": entry["end"],
                "text": entry["text"],
                "matched": idx in matched_indices,
                "context": idx not in matched_indices
            })

        return results

    def locate(self, timestamp: float) -> Optional[Dict[str, Any]]:
        """定位指定时间点所在的字幕条目。

        参数:
            timestamp: 时间点（秒）

        返回:
            命中的字幕条目（含 index/start/end/text），未命中返回 None
        """
        if timestamp < 0:
            return None

        for entry in self.entries:
            if entry["start"] <= timestamp < entry["end"]:
                return entry
        return None

    def get_total_duration(self) -> float:
        """返回字幕总时长（秒）。"""
        return self._total_duration

    def get_entry_count(self) -> int:
        """返回字幕条目总数。"""
        return len(self.entries)


# ---------------------------------------------------------------
# 输出模块
# ---------------------------------------------------------------
class OutputFormatter:
    """输出格式化：支持 JSON 和纯文本两种格式。"""

    @staticmethod
    def to_json(results: List[Dict[str, Any]], **extra: Any) -> str:
        """将结果转为 JSON 字符串。"""
        payload = {
            "results": results,
            "count": len(results),
            **extra
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def to_text(results: List[Dict[str, Any]]) -> str:
        """将结果转为纯文本格式。"""
        if not results:
            return "未找到匹配结果"

        lines = []
        for r in results:
            marker = ">" if r.get("matched", True) else " "
            lines.append(
                f"{marker} [{r['start']:.2f}s - {r['end']:.2f}s] "
                f"(#{r['index']}) {r['text']}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------
def run_selftest() -> int:
    """内置硬编码样例数据的离线自检。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("[SELFTEST] 开始离线自检...")

    # 硬编码样例字幕（SRT 格式）
    sample_srt = """\
1
00:00:00,500 --> 00:00:03,000
大家好，欢迎观看本期视频

2
00:00:03,500 --> 00:00:06,000
今天我们来讨论人工智能

3
00:00:06,500 --> 00:00:09,500
字幕检索工具的使用方法

4
00:00:10,000 --> 00:00:13,000
感谢观看，我们下期再见
"""

    # 测试 1: 解析
    try:
        parser = SubtitleParser()
        entries = parser.parse(sample_srt)
        assert len(entries) == 4, f"解析条目数应为4，实际 {len(entries)}"
        print(f"[SELFTEST] 解析通过，条目数: {len(entries)}")
    except Exception as e:
        print(f"[SELFTEST] 解析失败: {e}")
        return 1

    # 测试 2: 检索（宽阈值）
    try:
        searcher = SubtitleSearcher(entries)

        # 关键词 "人工智能"
        results = searcher.search("人工智能")
        assert len(results) >= 1, "应至少匹配1条"
        assert any("人工智能" in r["text"] for r in results), "匹配文本应包含关键词"
        print(f"[SELFTEST] 检索通过，命中 {len(results)} 条")

        # 关键词 "不存在"
        empty = searcher.search("不存在的关键词xyz")
        assert len(empty) == 0, "不应有匹配结果"
        print("[SELFTEST] 空检索通过")

        # 测试 3: 时间轴定位（宽松区间）
        located = searcher.locate(1.0)  # 1秒应在第一条内
        assert located is not None, "1秒应定位到字幕"
        assert located["start"] <= 1.0 < located["end"], "时间应在区间内"

        not_found = searcher.locate(999.0)
        assert not_found is None, "999秒不应定位到字幕"
        print("[SELFTEST] 时间轴定位通过")

        # 测试 4: 总时长
        duration = searcher.get_total_duration()
        assert duration > 10.0, f"总时长应大于10秒，实际 {duration}"
        print(f"[SELFTEST] 总时长检查通过: {duration:.2f}s")

        # 测试 5: 上下文
        ctx_results = searcher.search("人工智能", context_before=1, context_after=1)
        assert len(ctx_results) >= 1, "上下文检索应至少1条"
        print(f"[SELFTEST] 上下文检索通过，共 {len(ctx_results)} 条")

        # 测试 6: 输出格式化
        formatter = OutputFormatter()
        json_out = formatter.to_json(results)
        assert json_out is not None and len(json_out) > 0, "JSON输出不应为空"
        text_out = formatter.to_text(results)
        assert text_out is not None and len(text_out) > 0, "文本输出不应为空"
        print("[SELFTEST] 输出格式化通过")

    except Exception as e:
        print(f"[SELFTEST] 检索/定位/输出测试失败: {e}")
        return 1

    print("[SELFTEST] 全部通过 ✔")
    return 0


# ---------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """主入口。

    参数:
        argv: 命令行参数列表（不含程序名）

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="字幕检索工具：支持时间轴定位与关键词过滤",
        epilog="示例: python main.py sub.srt 人工智能 --context 1"
    )
    parser.add_argument("file", nargs="?", help="字幕文件路径（SRT/VTT）")
    parser.add_argument("keyword", nargs="?", help="检索关键词")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--case-sensitive", action="store_true", help="区分大小写")
    parser.add_argument("--context", type=int, default=0,
                        help="上下文条目数（前后各N条）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--locate", type=float, default=None,
                        help="定位指定时间点（秒）")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.file:
        print("E001: 缺少字幕文件参数", file=sys.stderr)
        parser.print_usage(sys.stderr)
        return 1

    if not args.keyword and args.locate is None:
        print("E001: 需提供关键词或 --locate 时间点", file=sys.stderr)
        parser.print_usage(sys.stderr)
        return 1

    # 读取文件
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"E002: 文件不存在: {args.file}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        try:
            with open(args.file, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except Exception as e:
            print(f"E009: 编码不支持: {e}", file=sys.stderr)
            return 9
    except Exception as e:
        print(f"E002: 文件读取失败: {e}", file=sys.stderr)
        return 2

    # 解析
    try:
        parser = SubtitleParser()
        entries = parser.parse(content)
    except ValueError as e:
        print(f"E003: 字幕解析失败: {e}", file=sys.stderr)
        return 3

    # 初始化检索器
    try:
        searcher = SubtitleSearcher(entries)
    except ValueError as e:
        print(f"E008: {e}", file=sys.stderr)
        return 8

    # 执行操作
    try:
        formatter = OutputFormatter()

        # 时间定位模式
        if args.locate is not None:
            entry = searcher.locate(args.locate)
            if entry is None:
                print("E005: 指定时间点未命中任何字幕", file=sys.stderr)
                return 5
            result = [entry]
            if args.json:
                print(formatter.to_json(result, mode="locate", timestamp=args.locate))
            else:
                print(formatter.to_text(result))
            return 0

        # 关键词检索模式
        results = searcher.search(
            args.keyword,
            case_sensitive=args.case_sensitive,
            context_before=args.context,
            context_after=args.context
        )

        if not results:
            print("E005: 未找到匹配的字幕", file=sys.stderr)
            return 5

        if args.json:
            print(formatter.to_json(
                results,
                mode="search",
                keyword=args.keyword,
                total_duration=searcher.get_total_duration(),
                total_entries=searcher.get_entry_count()
            ))
        else:
            print(formatter.to_text(results))
            print(f"\n共 {len(results)} 条结果")

    except ValueError as e:
        print(f"E005: 检索失败: {e}", file=sys.stderr)
        return 5
    except Exception as e:
        print(f"E010: 未预期错误: {e}", file=sys.stderr)
        return 10

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
