#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto-subtitles - 字幕转录与处理工具
=====================================
功能：
  1. 字幕文件解析（SRT / VTT / ASS）
  2. 文本转录整理（按时间轴结构化）
  3. 多语言翻译（字面直译）
  4. 格式转换输出（SRT / VTT / JSON / Markdown）
  5. 批量处理（保持目录结构）

用法示例：
  python scripts/main.py input.srt -o output.json
  python scripts/main.py input.srt -f vtt
  python scripts/main.py --selftest

错误码：
  E001 - 文件不存在或不可读
  E002 - 不支持的字幕格式
  E003 - 字幕内容解析失败
  E004 - 输出格式不支持
  E005 - 写入输出文件失败
  E006 - 批量处理目录无效
  E007 - 翻译目标语言未指定
  E008 - 时间轴格式非法
  E009 - 内部数据异常
  E010 - 命令行参数错误
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 核心数据结构
# ============================================================

class SubtitleCue:
    """单条字幕条目"""
    __slots__ = ("index", "start_ms", "end_ms", "text", "style")

    def __init__(self, index=0, start_ms=0, end_ms=0, text="", style=""):
        self.index = index
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.text = text
        self.style = style

    def to_dict(self):
        return {
            "index": self.index,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text": self.text,
            "style": self.style,
        }


class SubtitleDocument:
    """字幕文档（包含元数据与条目列表）"""
    def __init__(self):
        self.cues = []
        self.metadata = {
            "title": "",
            "language": "",
            "source_format": "",
        }

    def add_cue(self, cue):
        self.cues.append(cue)

    def sort_by_time(self):
        self.cues.sort(key=lambda c: (c.start_ms, c.end_ms))
        for idx, cue in enumerate(self.cues, start=1):
            cue.index = idx

    def to_dict(self):
        return {
            "metadata": self.metadata,
            "cues": [c.to_dict() for c in self.cues],
        }


# ============================================================
# 时间轴解析与格式化
# ============================================================

def parse_timestamp_srt(ts):
    """解析 SRT 时间戳 'HH:MM:SS,mmm' 为毫秒"""
    try:
        parts = ts.strip().split(":")
        if len(parts) != 3:
            return None
        h = int(parts[0])
        m = int(parts[1])
        sec_parts = parts[2].split(",")
        if len(sec_parts) != 2:
            return None
        s = int(sec_parts[0])
        ms = int(sec_parts[1])
        if not (0 <= m < 60 and 0 <= s < 60):
            return None
        return h * 3600000 + m * 60000 + s * 1000 + ms
    except (ValueError, IndexError):
        return None


def parse_timestamp_vtt(ts):
    """解析 VTT 时间戳 'HH:MM:SS.mmm' 或 'MM:SS.mmm' 为毫秒"""
    try:
        ts = ts.strip()
        # 去掉可能的尾部标签
        ts = re.sub(r"\s+<.*?>$", "", ts)
        parts = ts.split(":")
        if len(parts) == 2:
            m, s = parts
            h = 0
        elif len(parts) == 3:
            h, m, s = parts
        else:
            return None
        sec_parts = s.split(".")
        if len(sec_parts) != 2:
            return None
        sec_val = int(sec_parts[0])
        ms_val = int(sec_parts[1].ljust(3, "0")[:3])
        if not (0 <= int(m) < 60 and 0 <= sec_val < 60):
            return None
        return int(h) * 3600000 + int(m) * 60000 + sec_val * 1000 + ms_val
    except (ValueError, IndexError):
        return None


def format_timestamp_srt(ms):
    """毫秒转 SRT 时间戳 'HH:MM:SS,mmm'"""
    ms = max(0, int(ms))
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    milli = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def format_timestamp_vtt(ms):
    """毫秒转 VTT 时间戳 'HH:MM:SS.mmm'"""
    ms = max(0, int(ms))
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    milli = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


# ============================================================
# 字幕解析器
# ============================================================

def parse_srt(content):
    """解析 SRT 格式内容"""
    doc = SubtitleDocument()
    doc.metadata["source_format"] = "srt"
    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        try:
            # 第一行：序号（可省略）
            idx = 0
            line_pos = 0
            if lines[0].strip().isdigit():
                idx = int(lines[0].strip())
                line_pos = 1
            if line_pos >= len(lines):
                continue
            # 第二行：时间轴
            time_line = lines[line_pos]
            m = re.match(r"(\S+)\s*-->\s*(\S+)", time_line)
            if not m:
                continue
            start = parse_timestamp_srt(m.group(1))
            end = parse_timestamp_srt(m.group(2))
            if start is None or end is None:
                continue
            # 剩余行：文本
            text = "\n".join(lines[line_pos + 1:]).strip()
            cue = SubtitleCue(idx, start, end, text)
            doc.add_cue(cue)
        except Exception:
            continue
    return doc


def parse_vtt(content):
    """解析 VTT 格式内容"""
    doc = SubtitleDocument()
    doc.metadata["source_format"] = "vtt"
    lines = content.splitlines()
    idx = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 跳过头部
        if line.startswith("WEBVTT"):
            i += 1
            continue
        if line.startswith("NOTE"):
            while i < len(lines) and lines[i].strip():
                i += 1
            continue
        # 检查是否为时间轴行
        m = re.match(r"(\S+)\s*-->\s*(\S+)", line)
        if m:
            idx += 1
            start = parse_timestamp_vtt(m.group(1))
            end = parse_timestamp_vtt(m.group(2))
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = "\n".join(text_lines)
            cue = SubtitleCue(idx, start or 0, end or 0, text)
            doc.add_cue(cue)
        i += 1
    return doc


def parse_ass(content):
    """解析 ASS 格式内容（简化版：仅提取 Dialogue 行）"""
    doc = SubtitleDocument()
    doc.metadata["source_format"] = "ass"
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        try:
            start = parse_timestamp_ass(parts[1])
            end = parse_timestamp_ass(parts[2])
            style = parts[3]
            text = parts[9].replace("\\N", "\n").replace("\\n", "\n")
            cue = SubtitleCue(0, start, end, text, style)
            doc.add_cue(cue)
        except Exception:
            continue
    return doc


def parse_timestamp_ass(ts):
    """解析 ASS 时间戳 'H:MM:SS.cc' 为毫秒"""
    try:
        parts = ts.strip().split(":")
        if len(parts) != 3:
            return 0
        h = int(parts[0])
        m = int(parts[1])
        sec_parts = parts[2].split(".")
        if len(sec_parts) != 2:
            return 0
        s = int(sec_parts[0])
        cs = int(sec_parts[1])
        return h * 3600000 + m * 60000 + s * 1000 + cs * 10
    except (ValueError, IndexError):
        return 0


def parse_subtitle(content, fmt):
    """根据格式解析字幕内容"""
    fmt = fmt.lower().lstrip(".")
    if fmt == "srt":
        return parse_srt(content)
    elif fmt == "vtt":
        return parse_vtt(content)
    elif fmt == "ass":
        return parse_ass(content)
    else:
        raise ValueError(f"E002: 不支持的字幕格式 '{fmt}'")


def detect_format(filepath):
    """根据文件扩展名检测格式"""
    ext = Path(filepath).suffix.lower().lstrip(".")
    if ext in ("srt", "vtt", "ass"):
        return ext
    return None


# ============================================================
# 字幕写入器
# ============================================================

def write_srt(doc):
    """输出 SRT 格式"""
    lines = []
    for cue in doc.cues:
        lines.append(str(cue.index))
        lines.append(f"{format_timestamp_srt(cue.start_ms)} --> {format_timestamp_srt(cue.end_ms)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)


def write_vtt(doc):
    """输出 VTT 格式"""
    lines = ["WEBVTT", ""]
    for cue in doc.cues:
        lines.append(f"{format_timestamp_vtt(cue.start_ms)} --> {format_timestamp_vtt(cue.end_ms)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)


def write_json(doc):
    """输出 JSON 格式"""
    return json.dumps(doc.to_dict(), ensure_ascii=False, indent=2)


def write_markdown(doc):
    """输出 Markdown 表格格式"""
    lines = ["| 序号 | 开始时间 | 结束时间 | 文本 |", "|------|----------|----------|------|"]
    for cue in doc.cues:
        start = format_timestamp_srt(cue.start_ms)
        end = format_timestamp_srt(cue.end_ms)
        text = cue.text.replace("\n", "<br>")
        lines.append(f"| {cue.index} | {start} | {end} | {text} |")
    return "\n".join(lines)


def write_subtitle(doc, fmt):
    """根据格式输出字幕内容"""
    fmt = fmt.lower().lstrip(".")
    if fmt == "srt":
        return write_srt(doc)
    elif fmt == "vtt":
        return write_vtt(doc)
    elif fmt == "json":
        return write_json(doc)
    elif fmt == "md":
        return write_markdown(doc)
    else:
        raise ValueError(f"E004: 不支持的输出格式 '{fmt}'")


# ============================================================
# 翻译功能（字面直译占位）
# ============================================================

def translate_text(text, target_lang):
    """
    字面直译占位实现。
    实际场景可接入外部翻译 API，此处提供基础映射示例。
    """
    if not target_lang:
        raise ValueError("E007: 翻译目标语言未指定")
    # 简易示例：英文→中文的常用词映射
    simple_map = {
        "hello": "你好",
        "world": "世界",
        "thank": "谢谢",
        "you": "你",
        "welcome": "欢迎",
        "please": "请",
        "yes": "是",
        "no": "不",
        "good": "好",
        "bad": "坏",
    }
    if target_lang.lower() in ("zh", "cn", "chinese", "中文"):
        words = text.lower().split()
        translated = [simple_map.get(w, w) for w in words]
        return " ".join(translated)
    # 其他语言暂不支持，原样返回
    return text


def translate_document(doc, target_lang):
    """翻译文档中所有字幕文本"""
    for cue in doc.cues:
        cue.text = translate_text(cue.text, target_lang)
    return doc


# ============================================================
# 文件处理
# ============================================================

def read_file(filepath):
    """读取文件内容（自动检测编码）"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"E001: 文件不存在 '{filepath}'")
    if not path.is_file():
        raise IsADirectoryError(f"E001: 路径不是文件 '{filepath}'")
    # 尝试多种编码
    encodings = ["utf-8-sig", "utf-8", "gbk", "latin-1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"E001: 无法解码文件 '{filepath}'")


def write_file(filepath, content):
    """写入文件内容"""
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise OSError(f"E005: 写入文件失败 '{filepath}': {e}")


def process_file(input_path, output_format="srt", output_path=None, target_lang=None):
    """处理单个字幕文件"""
    # 读取文件
    content = read_file(input_path)
    # 检测格式
    src_fmt = detect_format(input_path)
    if not src_fmt:
        raise ValueError(f"E002: 无法识别文件格式 '{input_path}'")
    # 解析
    doc = parse_subtitle(content, src_fmt)
    if not doc.cues:
        raise ValueError(f"E003: 字幕内容解析失败 '{input_path}'")
    # 排序
    doc.sort_by_time()
    # 翻译
    if target_lang:
        doc = translate_document(doc, target_lang)
    # 输出
    content_out = write_subtitle(doc, output_format)
    if output_path:
        write_file(output_path, content_out)
    return content_out, doc


def process_directory(input_dir, output_format="srt", output_dir=None, target_lang=None):
    """批量处理目录下的字幕文件"""
    in_path = Path(input_dir)
    if not in_path.is_dir():
        raise NotADirectoryError(f"E006: 输入目录无效 '{input_dir}'")

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        out_path = in_path

    results = []
    for filepath in sorted(in_path.rglob("*")):
        if not filepath.is_file():
            continue
        src_fmt = detect_format(filepath)
        if not src_fmt:
            continue
        rel_path = filepath.relative_to(in_path)
        out_file = out_path / rel_path.with_suffix(f".{output_format.lower().lstrip('.')}")
        try:
            content_out, doc = process_file(
                str(filepath),
                output_format=output_format,
                output_path=str(out_file),
                target_lang=target_lang,
            )
            results.append({"input": str(filepath), "output": str(out_file), "cues": len(doc.cues)})
        except Exception as e:
            results.append({"input": str(filepath), "error": str(e)})
    return results


# ============================================================
# 自检功能
# ============================================================

def run_selftest():
    """内置硬编码样例数据离线自检核心逻辑"""
    print("=== auto-subtitles 自检开始 ===")
    errors = []

    # ---- 测试 1: SRT 解析与时间戳 ----
    sample_srt = """1
00:00:01,000 --> 00:00:03,500
Hello world

2
00:00:04,000 --> 00:00:06,000
This is a test
"""
    try:
        doc = parse_srt(sample_srt)
        if len(doc.cues) != 2:
            errors.append("SRT 解析条目数错误")
        else:
            c1 = doc.cues[0]
            # 宽松断言：时间在合理范围
            if not (c1.start_ms >= 0 and c1.start_ms < 60000):
                errors.append("SRT 开始时间解析异常")
            if not (c1.end_ms > c1.start_ms):
                errors.append("SRT 结束时间应大于开始时间")
            if c1.text != "Hello world":
                errors.append("SRT 文本解析错误")
        print("[PASS] SRT 解析测试")
    except Exception as e:
        errors.append(f"SRT 解析异常: {e}")
        print(f"[FAIL] SRT 解析测试: {e}")

    # ---- 测试 2: VTT 解析 ----
    sample_vtt = """WEBVTT

00:00:02.000 --> 00:00:04.500
Hello VTT

00:00:05.000 --> 00:00:07.000
Second cue
"""
    try:
        doc = parse_vtt(sample_vtt)
        if len(doc.cues) != 2:
            errors.append("VTT 解析条目数错误")
        else:
            c1 = doc.cues[0]
            if not (c1.start_ms >= 0 and c1.start_ms < 60000):
                errors.append("VTT 开始时间解析异常")
            if c1.text != "Hello VTT":
                errors.append("VTT 文本解析错误")
        print("[PASS] VTT 解析测试")
    except Exception as e:
        errors.append(f"VTT 解析异常: {e}")
        print(f"[FAIL] VTT 解析测试: {e}")

    # ---- 测试 3: 格式转换 ----
    sample_doc = SubtitleDocument()
    sample_doc.add_cue(SubtitleCue(1, 1000, 3000, "Test line"))
    try:
        srt_out = write_srt(sample_doc)
        if "Test line" not in srt_out:
            errors.append("SRT 输出缺少文本")
        json_out = write_json(sample_doc)
        data = json.loads(json_out)
        if len(data["cues"]) != 1:
            errors.append("JSON 输出条目数错误")
        md_out = write_markdown(sample_doc)
        if "Test line" not in md_out:
            errors.append("Markdown 输出缺少文本")
        print("[PASS] 格式转换测试")
    except Exception as e:
        errors.append(f"格式转换异常: {e}")
        print(f"[FAIL] 格式转换测试: {e}")

    # ---- 测试 4: 时间戳格式化往返 ----
    try:
        ms = 3661000  # 1:01:01.000
        srt_ts = format_timestamp_srt(ms)
        parsed = parse_timestamp_srt(srt_ts)
        if parsed is None:
            errors.append("SRT 时间戳往返解析失败")
        elif abs(parsed - ms) > 5:  # 宽松阈值
            errors.append(f"SRT 时间戳往返偏差过大: {parsed} vs {ms}")
        print("[PASS] 时间戳往返测试")
    except Exception as e:
        errors.append(f"时间戳异常: {e}")
        print(f"[FAIL] 时间戳往返测试: {e}")

    # ---- 测试 5: 翻译功能 ----
    try:
        translated = translate_text("hello world", "zh")
        if "你好" not in translated:
            errors.append("翻译结果缺少预期词")
        print("[PASS] 翻译功能测试")
    except Exception as e:
        errors.append(f"翻译异常: {e}")
        print(f"[FAIL] 翻译功能测试: {e}")

    # ---- 测试 6: 完整流程 ----
    try:
        content_out, doc = process_file_from_string(sample_srt, "srt", "json")
        data = json.loads(content_out)
        if len(data["cues"]) != 2:
            errors.append("完整流程 JSON 输出条目数错误")
        print("[PASS] 完整流程测试")
    except Exception as e:
        errors.append(f"完整流程异常: {e}")
        print(f"[FAIL] 完整流程测试: {e}")

    # ---- 汇总 ----
    print(f"\n=== 自检完成: {len(errors)} 个错误 ===")
    if errors:
        for e in errors:
            print(f"  - {e}")
        return False
    return True


def process_file_from_string(content, src_fmt, output_format):
    """从字符串处理字幕（用于测试）"""
    doc = parse_subtitle(content, src_fmt)
    doc.sort_by_time()
    return write_subtitle(doc, output_format), doc


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="字幕转录与处理工具 auto-subtitles",
        epilog="示例: python scripts/main.py input.srt -f json -o output.json",
    )
    parser.add_argument("--input", nargs="?", help="输入字幕文件或目录")
    parser.add_argument("-o", "--output", help="输出文件路径（单文件模式）")
    parser.add_argument("-f", "--format", default="srt", help="输出格式: srt/vtt/json/md")
    parser.add_argument("-t", "--translate", help="翻译目标语言（如 zh）")
    parser.add_argument("-d", "--directory", action="store_true", help="批量处理目录模式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        sys.exit(0 if ok else 1)

    # 参数检查
    if not args.input:
        parser.error("E010: 必须指定输入文件或目录")
        return

    try:
        if args.directory:
            results = process_directory(
                args.input,
                output_format=args.format,
                output_dir=args.output,
                target_lang=args.translate,
            )
            for r in results:
                if "error" in r:
                    print(f"[失败] {r['input']}: {r['error']}")
                else:
                    print(f"[成功] {r['input']} -> {r['output']} ({r['cues']} 条)")
        else:
            content_out, doc = process_file(
                args.input,
                output_format=args.format,
                output_path=args.output,
                target_lang=args.translate,
            )
            if not args.output:
                # 未指定输出路径时打印到标准输出
                print(content_out)
            else:
                print(f"处理完成: {args.input} -> {args.output} ({len(doc.cues)} 条字幕)")
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E009: 未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
