#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto-subtitles - 字幕转录与处理工具

功能：
- 解析 SRT / VTT / ASS 字幕文件
- 将文本按时间轴整理为字幕结构
- 将字幕内容翻译为目标语言（模拟翻译/占位）
- 输出为 SRT / VTT / JSON / Markdown 表格
- 批量处理多个文件

用法示例：
    python scripts/main.py input.srt -o output.vtt
    python scripts/main.py input.srt --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用自定义异常，携带错误码"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def err(code: str, message: str) -> AppError:
    """构造错误异常"""
    return AppError(code, message)


# ============================================================
# 数据模型
# ============================================================
@dataclass
class SubtitleItem:
    """单条字幕条目"""
    index: int = 0
    start_ms: int = 0          # 开始时间（毫秒）
    end_ms: int = 0            # 结束时间（毫秒）
    text: str = ""
    style: str = ""            # ASS 样式名（可选）
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubtitleDocument:
    """字幕文档"""
    format: str = "srt"        # 原始格式
    items: List[SubtitleItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def sort(self) -> None:
        """按开始时间排序"""
        self.items.sort(key=lambda x: (x.start_ms, x.index))


# ============================================================
# 时间解析/格式化工具
# ============================================================
def parse_timestamp_srt(ts: str) -> int:
    """解析 SRT 时间戳 'HH:MM:SS,mmm' -> 毫秒"""
    m = re.match(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})", ts.strip())
    if not m:
        raise err("E001", f"无法解析 SRT 时间戳: {ts!r}")
    h, mi, s, ms = m.groups()
    ms = int(ms.ljust(3, "0"))  # 补零到3位
    return int(h) * 3600000 + int(mi) * 60000 + int(s) * 1000 + ms


def format_timestamp_srt(ms: int) -> str:
    """毫秒 -> SRT 时间戳 'HH:MM:SS,mmm'"""
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def parse_timestamp_vtt(ts: str) -> int:
    """解析 VTT 时间戳（支持 'HH:MM:SS.mmm' 或 'MM:SS.mmm'）"""
    ts = ts.strip().replace(" ", "")
    # 去掉可能存在的时区/设置信息
    ts = re.split(r"[ \t]", ts)[0]
    m = re.match(r"(?:(\d+):)?(\d{2}):(\d{2})[.](\d{1,3})", ts)
    if not m:
        # 尝试 SRT 格式（逗号）
        try:
            return parse_timestamp_srt(ts)
        except AppError:
            raise err("E002", f"无法解析 VTT 时间戳: {ts!r}")
    h = int(m.group(1) or 0)
    mi = int(m.group(2))
    s = int(m.group(3))
    ms = int(m.group(4).ljust(3, "0"))
    return h * 3600000 + mi * 60000 + s * 1000 + ms


def format_timestamp_vtt(ms: int) -> str:
    """毫秒 -> VTT 时间戳 'HH:MM:SS.mmm'"""
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


def parse_timestamp_ass(ts: str) -> int:
    """解析 ASS 时间戳 'H:MM:SS.cc'（百分秒）"""
    m = re.match(r"(\d+):(\d{2}):(\d{2})[.](\d{1,2})", ts.strip())
    if not m:
        raise err("E003", f"无法解析 ASS 时间戳: {ts!r}")
    h, mi, s, cs = m.groups()
    ms = int(cs.ljust(2, "0")) * 10
    return int(h) * 3600000 + int(mi) * 60000 + int(s) * 1000 + ms


def format_timestamp_ass(ms: int) -> str:
    """毫秒 -> ASS 时间戳 'H:MM:SS.cc'"""
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    cs = milli // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ============================================================
# 字幕解析器
# ============================================================
def parse_srt(content: str) -> SubtitleDocument:
    """解析 SRT 格式内容"""
    doc = SubtitleDocument(format="srt")
    lines = content.replace("\r\n", "\n").split("\n")
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        # 尝试读取序号
        try:
            idx = int(line)
        except ValueError:
            idx = None

        # 查找时间行（跳过可能的序号行）
        time_line = None
        seek = i
        if idx is not None:
            seek = i + 1
        while seek < n:
            cand = lines[seek].strip()
            if "-->" in cand:
                time_line = cand
                break
            if cand and not cand.isdigit():
                break
            seek += 1

        if time_line is None:
            # 没有时间行，跳过（错误容忍）
            i += 1
            continue

        # 解析时间范围
        m = re.search(r"(\d+:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d+:\d{2}:\d{2}[,.]\d{1,3})", time_line)
        if not m:
            raise err("E001", f"无效的时间行: {time_line!r}")
        start_ms = parse_timestamp_srt(m.group(1))
        end_ms = parse_timestamp_srt(m.group(2))

        # 收集文本（直到空行）
        text_lines = []
        j = seek + 1
        while j < n and lines[j].strip() != "":
            text_lines.append(lines[j].strip())
            j += 1

        item = SubtitleItem(
            index=idx if idx is not None else (len(doc.items) + 1),
            start_ms=start_ms,
            end_ms=end_ms,
            text="\n".join(text_lines),
        )
        doc.items.append(item)
        i = j  # 跳到空行之后

    doc.sort()
    return doc


def parse_vtt(content: str) -> SubtitleDocument:
    """解析 VTT 格式内容"""
    doc = SubtitleDocument(format="vtt")
    lines = content.replace("\r\n", "\n").split("\n")
    i = 0
    n = len(lines)
    # 跳过 WEBVTT 头部
    while i < n and not lines[i].strip().startswith("WEBVTT"):
        i += 1
    i += 1

    while i < n:
        line = lines[i].strip()
        if not line or line.startswith("NOTE"):
            # 跳过空行和注释
            if line.startswith("NOTE"):
                while i < n and lines[i].strip() != "":
                    i += 1
            i += 1
            continue

        # 检查是否是时间行
        if "-->" in line:
            m = re.search(r"(\S+)\s*-->\s*(\S+)", line)
            if m:
                try:
                    start_ms = parse_timestamp_vtt(m.group(1))
                    end_ms = parse_timestamp_vtt(m.group(2))
                except AppError as e:
                    raise err("E002", f"VTT 时间解析失败: {e.message}")
                # 收集文本
                text_lines = []
                j = i + 1
                while j < n and lines[j].strip() != "":
                    text_lines.append(lines[j].strip())
                    j += 1
                doc.items.append(SubtitleItem(
                    index=len(doc.items) + 1,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text="\n".join(text_lines),
                ))
                i = j
                continue
        i += 1

    doc.sort()
    return doc


def parse_ass(content: str) -> SubtitleDocument:
    """解析 ASS 格式内容（仅提取 Dialogue 行）"""
    doc = SubtitleDocument(format="ass")
    for raw_line in content.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line.startswith("Dialogue:"):
            continue
        
        # 移除 "Dialogue:" 前缀，然后按逗号分割（最多9次，保留文本部分）
        # ASS 格式: Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        # 移除前缀后，有 10 个字段
        content_part = line[len("Dialogue:"):].strip()
        parts = content_part.split(",", 9)
        if len(parts) < 10:
            continue
            
        # 解包10个字段
        layer, start_ts, end_ts, style, name, ml, mr, mv, effect, text = parts
        try:
            start_ms = parse_timestamp_ass(start_ts.strip())
            end_ms = parse_timestamp_ass(end_ts.strip())
        except AppError:
            continue
        doc.items.append(SubtitleItem(
            index=len(doc.items) + 1,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text.replace("\\N", "\n").replace("\\n", "\n"),
            style=style.strip(),
            extra={
                "layer": layer.strip(),
                "name": name.strip(),
                "margin_l": ml.strip(),
                "margin_r": mr.strip(),
                "margin_v": mv.strip(),
                "effect": effect.strip(),
            },
        ))
    doc.sort()
    return doc


# ============================================================
# 字幕序列化器
# ============================================================
def to_srt(doc: SubtitleDocument) -> str:
    """输出 SRT 格式"""
    out = []
    for i, item in enumerate(doc.items, 1):
        out.append(str(i))
        out.append(f"{format_timestamp_srt(item.start_ms)} --> {format_timestamp_srt(item.end_ms)}")
        out.append(item.text)
        out.append("")
    return "\n".join(out)


def to_vtt(doc: SubtitleDocument) -> str:
    """输出 VTT 格式"""
    out = ["WEBVTT", ""]
    for i, item in enumerate(doc.items, 1):
        out.append(f"{format_timestamp_vtt(item.start_ms)} --> {format_timestamp_vtt(item.end_ms)}")
        out.append(item.text)
        out.append("")
    return "\n".join(out)


def to_json(doc: SubtitleDocument) -> str:
    """输出 JSON 格式"""
    data = {
        "format": doc.format,
        "metadata": doc.metadata,
        "items": [
            {
                "index": item.index,
                "start_ms": item.start_ms,
                "end_ms": item.end_ms,
                "text": item.text,
                "style": item.style,
                "extra": item.extra,
            }
            for item in doc.items
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def to_markdown(doc: SubtitleDocument) -> str:
    """输出 Markdown 表格"""
    out = ["| 序号 | 开始时间 | 结束时间 | 文本 |", "|------|----------|----------|------|"]
    for item in doc.items:
        start = format_timestamp_srt(item.start_ms)
        end = format_timestamp_srt(item.end_ms)
        text = item.text.replace("\n", "<br>")
        out.append(f"| {item.index} | {start} | {end} | {text} |")
    return "\n".join(out)


# ============================================================
# 翻译功能（模拟/占位实现）
# ============================================================
def translate_text(text: str, target_lang: str) -> str:
    """
    翻译文本到目标语言。
    注意：这是模拟翻译，实际使用时请接入真实翻译 API。
    当前实现仅做标记，不改变原文。
    """
    # 在此处接入真实翻译服务（如 Google Translate API, DeepSeek 等）
    # 由于 clean-room 实现不依赖外部服务，这里返回原文并附加标记
    return f"[{target_lang}] {text}"


def translate_document(doc: SubtitleDocument, target_lang: str) -> SubtitleDocument:
    """翻译整个文档"""
    new_doc = SubtitleDocument(format=doc.format, metadata=dict(doc.metadata))
    for item in doc.items:
        new_item = SubtitleItem(
            index=item.index,
            start_ms=item.start_ms,
            end_ms=item.end_ms,
            text=translate_text(item.text, target_lang),
            style=item.style,
            extra=dict(item.extra),
        )
        new_doc.items.append(new_item)
    new_doc.sort()
    return new_doc


# ============================================================
# 文件处理
# ============================================================
def detect_format(path: Path) -> str:
    """根据扩展名检测格式"""
    ext = path.suffix.lower().lstrip(".")
    if ext in ("srt",):
        return "srt"
    if ext in ("vtt", "webvtt"):
        return "vtt"
    if ext in ("ass", "ssa"):
        return "ass"
    raise err("E004", f"不支持的文件格式: .{ext}")


def parse_file(path: Path) -> SubtitleDocument:
    """解析字幕文件"""
    fmt = detect_format(path)
    try:
        content = path.read_text(encoding="utf-8-sig")
    except Exception as e:
        raise err("E005", f"读取文件失败 {path}: {e}")
    if fmt == "srt":
        return parse_srt(content)
    if fmt == "vtt":
        return parse_vtt(content)
    if fmt == "ass":
        return parse_ass(content)
    raise err("E004", f"不支持的格式: {fmt}")


def write_output(doc: SubtitleDocument, out_path: Path, fmt: str) -> None:
    """写入输出文件"""
    if fmt == "srt":
        content = to_srt(doc)
    elif fmt == "vtt":
        content = to_vtt(doc)
    elif fmt == "json":
        content = to_json(doc)
    elif fmt == "md":
        content = to_markdown(doc)
    else:
        raise err("E006", f"不支持的输出格式: {fmt}")
    try:
        out_path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise err("E007", f"写入文件失败 {out_path}: {e}")


def process_file(input_path: Path, output_path: Optional[Path], fmt: Optional[str], target_lang: Optional[str]) -> None:
    """处理单个文件"""
    doc = parse_file(input_path)
    if target_lang:
        doc = translate_document(doc, target_lang)

    if fmt is None:
        fmt = "srt"  # 默认输出 SRT

    if output_path is None:
        # 默认输出到当前目录，同名但扩展名不同
        output_path = input_path.with_suffix(f".{fmt}")

    write_output(doc, output_path, fmt)
    print(f"已处理: {input_path} -> {output_path}")


def process_directory(input_dir: Path, output_dir: Path, fmt: str, target_lang: Optional[str]) -> None:
    """批量处理目录"""
    if not input_dir.is_dir():
        raise err("E008", f"输入目录不存在: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    for file_path in input_dir.rglob("*"):
        if file_path.is_file():
            try:
                fmt_in = detect_format(file_path)
            except AppError:
                continue  # 跳过不支持的文件
            rel_path = file_path.relative_to(input_dir)
            out_path = output_dir / rel_path.with_suffix(f".{fmt}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                process_file(file_path, out_path, fmt, target_lang)
            except AppError as e:
                print(f"跳过 {file_path}: {e.message}", file=sys.stderr)


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> int:
    """内置硬编码样例数据的离线自检"""
    print("=== auto-subtitles 自检开始 ===")

    # --- 样例数据 ---
    sample_srt = """1
00:00:01,000 --> 00:00:03,000
Hello world

2
00:00:04,500 --> 00:00:06,000
This is a test

"""

    sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello from VTT

00:00:04.000 --> 00:00:06.000
Second line

"""

    sample_ass = """[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize
Style: Default,Arial,20

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hello ASS

"""

    # --- 测试 SRT 解析 ---
    try:
        doc = parse_srt(sample_srt)
        assert len(doc.items) == 2, f"SRT 应解析出2条，实际 {len(doc.items)}"
        assert doc.items[0].text == "Hello world"
        assert doc.items[0].start_ms == 1000
        assert doc.items[1].end_ms == 6000
        print("[PASS] SRT 解析")
    except Exception as e:
        print(f"[FAIL] SRT 解析: {e}")
        return 1

    # --- 测试 VTT 解析 ---
    try:
        doc = parse_vtt(sample_vtt)
        assert len(doc.items) == 2, f"VTT 应解析出2条，实际 {len(doc.items)}"
        assert doc.items[0].start_ms == 1000
        assert doc.items[1].text == "Second line"
        print("[PASS] VTT 解析")
    except Exception as e:
        print(f"[FAIL] VTT 解析: {e}")
        return 1

    # --- 测试 ASS 解析 ---
    try:
        doc = parse_ass(sample_ass)
        assert len(doc.items) == 1, f"ASS 应解析出1条，实际 {len(doc.items)}"
        assert doc.items[0].text == "Hello ASS"
        assert doc.items[0].start_ms == 1000
        print("[PASS] ASS 解析")
    except Exception as e:
        print(f"[FAIL] ASS 解析: {e}")
        return 1

    # --- 测试格式转换 ---
    try:
        doc = parse_srt(sample_srt)
        srt_out = to_srt(doc)
        assert "Hello world" in srt_out
        assert "00:00:01,000" in srt_out

        vtt_out = to_vtt(doc)
        assert "WEBVTT" in vtt_out
        assert "00:00:01.000" in vtt_out

        json_out = to_json(doc)
        json_data = json.loads(json_out)
        assert len(json_data["items"]) == 2
        assert json_data["items"][0]["text"] == "Hello world"

        md_out = to_markdown(doc)
        assert "| 1 |" in md_out
        print("[PASS] 格式转换")
    except Exception as e:
        print(f"[FAIL] 格式转换: {e}")
        return 1

    # --- 测试翻译（模拟） ---
    try:
        doc = parse_srt(sample_srt)
        translated = translate_document(doc, "zh")
        assert "[zh]" in translated.items[0].text
        assert len(translated.items) == 2
        print("[PASS] 翻译模拟")
    except Exception as e:
        print(f"[FAIL] 翻译模拟: {e}")
        return 1

    # --- 测试时间戳往返 ---
    try:
        ms = 3661000  # 1:01:01.000
        srt_ts = format_timestamp_srt(ms)
        assert parse_timestamp_srt(srt_ts) == ms, "SRT 时间戳往返失败"
        vtt_ts = format_timestamp_vtt(ms)
        assert parse_timestamp_vtt(vtt_ts) == ms, "VTT 时间戳往返失败"
        ass_ts = format_timestamp_ass(ms)
        assert parse_timestamp_ass(ass_ts) == ms, "ASS 时间戳往返失败"
        print("[PASS] 时间戳往返")
    except Exception as e:
        print(f"[FAIL] 时间戳往返: {e}")
        return 1

    # --- 测试批量处理（临时目录） ---
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            in_dir = tmp / "in"
            out_dir = tmp / "out"
            in_dir.mkdir()
            (in_dir / "test.srt").write_text(sample_srt, encoding="utf-8")
            process_directory(in_dir, out_dir, "json", None)
            out_file = out_dir / "test.json"
            assert out_file.exists(), "批量处理应生成 JSON 文件"
            data = json.loads(out_file.read_text(encoding="utf-8"))
            assert len(data["items"]) == 2
        print("[PASS] 批量处理")
    except Exception as e:
        print(f"[FAIL] 批量处理: {e}")
        return 1

    # --- 测试错误处理 ---
    try:
        parse_srt("invalid content without time")
        print("[FAIL] 错误处理：应抛出异常")
        return 1
    except AppError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("[PASS] 错误处理")

    # --- 测试宽松阈值断言 ---
    try:
        doc = parse_srt(sample_srt)
        # 使用宽松阈值（不依赖精确值）
        assert len(doc.items) >= 1, "至少应有1条字幕"
        assert doc.items[0].start_ms < doc.items[0].end_ms, "开始时间应早于结束时间"
        assert doc.items[0].end_ms - doc.items[0].start_ms > 0, "持续时间应为正"
        assert len(doc.items[0].text) > 0, "文本不应为空"
        print("[PASS] 宽松阈值断言")
    except Exception as e:
        print(f"[FAIL] 宽松阈值断言: {e}")
        return 1

    print("=== 自检全部通过 ===")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="字幕转录与处理工具 (auto-subtitles)",
        epilog="示例: python main.py input.srt -o output.vtt --format vtt",
    )
    parser.add_argument("input", nargs="?", help="输入文件或目录")
    parser.add_argument("-o", "--output", help="输出文件（单个文件时）")
    parser.add_argument("-f", "--format", choices=["srt", "vtt", "json", "md"], help="输出格式")
    parser.add_argument("-t", "--translate", metavar="LANG", help="翻译目标语言（如 zh, en）")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.input:
        parser.print_help()
        return 1

    input_path = Path(args.input)

    try:
        if input_path.is_dir():
            # 批量处理目录
            output_dir = Path(args.output) if args.output else input_path / "output"
            fmt = args.format or "srt"
            process_directory(input_path, output_dir, fmt, args.translate)
        else:
            # 单文件处理
            output_path = Path(args.output) if args.output else None
            process_file(input_path, output_path, args.format, args.translate)
        return 0
    except AppError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
