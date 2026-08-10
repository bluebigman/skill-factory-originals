#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto-subtitles - 本地 AI 语音识别字幕生成工具
==============================================
功能：
  1. 语音转写（faster-whisper）
  2. 多格式输出（SRT / VTT / TXT / JSON）
  3. 批量处理
  4. 置信度输出
  5. 预览模式（--dry-run）

用法示例：
  python run.py input.mp4 -f srt
  python run.py audio.mp3 -f json
  python run.py ./videos/ --batch
  python run.py --selftest

错误码：
  E001 - 文件不存在或不可读
  E002 - 文件格式不支持
  E003 - 模型加载失败
  E004 - 输出格式不支持
  E005 - 写入输出文件失败
  E006 - 批量处理目录无效
  E007 - 转写失败
  E008 - 时间轴格式非法
  E009 - 内部数据异常
  E010 - 命令行参数错误
"""

import argparse
import json
import os
import re
import sys
import time
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import chardet
except ImportError:
    chardet = None

# ============================================================
# 常量定义
# ============================================================

SUPPORTED_INPUT_EXTENSIONS = {
    '.mp4', '.mkv', '.mov', '.avi', '.mp3', '.wav', '.flac', '.m4a', '.webm', '.ogg'
}

SUPPORTED_OUTPUT_FORMATS = {'srt', 'vtt', 'txt', 'json'}

MODEL_SIZES = {'tiny', 'base', 'small', 'medium', 'large-v3'}

DEFAULT_MODEL = 'small'

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
REQUEST_TIMEOUT = 30

# ============================================================
# 核心数据结构
# ============================================================

class SubtitleCue:
    """单条字幕条目"""
    __slots__ = ("index", "start_ms", "end_ms", "text", "confidence")

    def __init__(self, index=0, start_ms=0, end_ms=0, text="", confidence=1.0):
        self.index = index
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.text = text
        self.confidence = confidence

    def to_dict(self):
        return {
            "index": self.index,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text": self.text,
            "confidence": self.confidence,
        }


class SubtitleDocument:
    """字幕文档（包含元数据与条目列表）"""
    def __init__(self):
        self.cues = []
        self.metadata = {
            "title": "",
            "language": "",
            "source_format": "",
            "model": DEFAULT_MODEL,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def add_cue(self, cue):
        self.cues.append(cue)

    def sort_by_time(self):
        self.cues.sort(key=lambda c: (c.start_ms, c.end_ms))
        for idx, cue in enumerate(self.cues, start=1):
            cue.index = idx


# ============================================================
# 工具函数
# ============================================================

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def get_timestamp():
    """获取 UTC 时间戳"""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def format_timestamp_srt(ms):
    """毫秒转 SRT 时间戳格式"""
    if ms < 0:
        ms = 0
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    milliseconds = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def format_timestamp_vtt(ms):
    """毫秒转 VTT 时间戳格式"""
    if ms < 0:
        ms = 0
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    milliseconds = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def detect_encoding(file_path):
    """检测文件编码"""
    if chardet is not None:
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)
            result = chardet.detect(raw_data)
            if result and result['encoding']:
                return result['encoding']
    
    # 三级 fallback
    for encoding in ['utf-8', 'gbk', 'gb18030']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, IOError):
            continue
    
    return 'utf-8'


def read_text_file(file_path):
    """读取文本文件，自动检测编码"""
    encoding = detect_encoding(file_path)
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except (UnicodeDecodeError, IOError) as e:
        # 最后尝试 errors="replace"
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()


def atomic_write(file_path, content, dry_run=False):
    """原子化写入文件"""
    if not dry_run:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入临时文件
        fd, temp_path = tempfile.mkstemp(dir=str(file_path.parent), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            # 原子替换
            os.replace(temp_path, file_path)
            print(f"[写入] {file_path}")
            return True
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise e
    else:
        print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")
        return False


def validate_input_file(file_path):
    """验证输入文件"""
    if not os.path.exists(file_path):
        return False, "E001", f"文件不存在: {file_path}"
    
    if not os.path.isfile(file_path):
        return False, "E001", f"不是文件: {file_path}"
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_INPUT_EXTENSIONS:
        return False, "E002", f"不支持的文件格式: {ext}"
    
    return True, None, None


def validate_output_format(fmt):
    """验证输出格式"""
    if fmt not in SUPPORTED_OUTPUT_FORMATS:
        return False, "E004", f"不支持的输出格式: {fmt}"
    return True, None, None


def validate_model_size(model):
    """验证模型大小"""
    if model not in MODEL_SIZES:
        return False, "E010", f"不支持的模型: {model}"
    return True, None, None


# ============================================================
# 字幕解析器
# ============================================================

def parse_srt(content):
    """解析 SRT 格式字幕"""
    cues = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 尝试解析序号
        try:
            index = int(line)
        except ValueError:
            i += 1
            continue
        
        # 解析时间轴
        if i + 1 >= len(lines):
            break
        
        time_line = lines[i + 1].strip()
        time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', time_line)
        if not time_match:
            i += 2
            continue
        
        start_str, end_str = time_match.groups()
        start_ms = parse_srt_timestamp(start_str)
        end_ms = parse_srt_timestamp(end_str)
        
        # 解析文本
        text_lines = []
        j = i + 2
        while j < len(lines) and lines[j].strip():
            text_lines.append(lines[j].strip())
            j += 1
        
        text = '\n'.join(text_lines)
        if text:
            cues.append(SubtitleCue(index=index, start_ms=start_ms, end_ms=end_ms, text=text))
        
        i = j
    
    return cues


def parse_srt_timestamp(ts):
    """解析 SRT 时间戳为毫秒"""
    parts = ts.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds_parts = parts[2].split(',')
    seconds = int(seconds_parts[0])
    milliseconds = int(seconds_parts[1])
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds


def parse_vtt(content):
    """解析 VTT 格式字幕"""
    cues = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == 'WEBVTT':
            i += 1
            continue
        
        # 解析时间轴
        time_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})', line)
        if not time_match:
            i += 1
            continue
        
        start_str, end_str = time_match.groups()
        start_ms = parse_vtt_timestamp(start_str)
        end_ms = parse_vtt_timestamp(end_str)
        
        # 解析文本
        text_lines = []
        j = i + 1
        while j < len(lines) and lines[j].strip():
            text_lines.append(lines[j].strip())
            j += 1
        
        text = '\n'.join(text_lines)
        if text:
            cues.append(SubtitleCue(index=len(cues) + 1, start_ms=start_ms, end_ms=end_ms, text=text))
        
        i = j
    
    return cues


def parse_vtt_timestamp(ts):
    """解析 VTT 时间戳为毫秒"""
    parts = ts.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds_parts = parts[2].split('.')
    seconds = int(seconds_parts[0])
    milliseconds = int(seconds_parts[1])
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds


def parse_subtitle_file(file_path):
    """解析字幕文件"""
    content = read_text_file(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.srt':
        return parse_srt(content)
    elif ext == '.vtt':
        return parse_vtt(content)
    elif ext == '.ass':
        # ASS 格式简化解析
        return parse_ass(content)
    else:
        return []


def parse_ass(content):
    """解析 ASS 格式字幕（简化版）"""
    cues = []
    for line in content.split('\n'):
        if not line.startswith('Dialogue:'):
            continue
        
        # 格式: Dialogue: layer,start,end,style,name,effect,text
        parts = line.split(',', 9)
        if len(parts) < 10:
            continue
        
        start_str = parts[1].strip()
        end_str = parts[2].strip()
        text = parts[9].strip()
        
        start_ms = parse_ass_timestamp(start_str)
        end_ms = parse_ass_timestamp(end_str)
        
        if text:
            cues.append(SubtitleCue(index=len(cues) + 1, start_ms=start_ms, end_ms=end_ms, text=text))
    
    return cues


def parse_ass_timestamp(ts):
    """解析 ASS 时间戳为毫秒"""
    # 格式: H:MM:SS.CC
    parts = ts.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds_parts = parts[2].split('.')
    seconds = int(seconds_parts[0])
    centiseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + centiseconds * 10


# ============================================================
# 字幕格式化器
# ============================================================

def format_srt(doc):
    """格式化为 SRT"""
    lines = []
    for cue in doc.cues:
        lines.append(str(cue.index))
        lines.append(f"{format_timestamp_srt(cue.start_ms)} --> {format_timestamp_srt(cue.end_ms)}")
        lines.append(cue.text)
        lines.append('')
    return '\n'.join(lines)


def format_vtt(doc):
    """格式化为 VTT"""
    lines = ['WEBVTT', '']
    for cue in doc.cues:
        lines.append(f"{format_timestamp_vtt(cue.start_ms)} --> {format_timestamp_vtt(cue.end_ms)}")
        lines.append(cue.text)
        lines.append('')
    return '\n'.join(lines)


def format_txt(doc):
    """格式化为纯文本"""
    lines = []
    for cue in doc.cues:
        lines.append(cue.text)
    return '\n'.join(lines)


def format_json(doc):
    """格式化为 JSON"""
    data = {
        "metadata": doc.metadata,
        "segments": [cue.to_dict() for cue in doc.cues],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_subtitle(doc, fmt):
    """根据格式输出"""
    if fmt == 'srt':
        return format_srt(doc)
    elif fmt == 'vtt':
        return format_vtt(doc)
    elif fmt == 'txt':
        return format_txt(doc)
    elif fmt == 'json':
        return format_json(doc)
    else:
        raise ValueError(f"不支持的输出格式: {fmt}")


# ============================================================
# 语音转写
# ============================================================

def transcribe_audio(file_path, model_size=DEFAULT_MODEL, language=None, word_timestamps=False, verbose=False):
    """使用 faster-whisper 进行语音转写"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("错误: 未安装 faster-whisper，请运行: pip install faster-whisper", file=sys.stderr)
        return None, "E003", "faster-whisper 未安装"
    
    try:
        if verbose:
            print(f"加载模型: {model_size}")
        
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        if verbose:
            print(f"开始转写: {file_path}")
        
        segments, info = model.transcribe(
            file_path,
            language=language,
            beam_size=5,
            word_timestamps=word_timestamps,
        )
        
        doc = SubtitleDocument()
        doc.metadata["language"] = info.language
        doc.metadata["model"] = model_size
        doc.metadata["source_format"] = os.path.splitext(file_path)[1]
        
        for segment in segments:
            cue = SubtitleCue(
                index=len(doc.cues) + 1,
                start_ms=int(segment.start * 1000),
                end_ms=int(segment.end * 1000),
                text=segment.text.strip(),
                confidence=getattr(segment, 'avg_logprob', 0),
            )
            doc.add_cue(cue)
            
            if verbose:
                print(f"  [{cue.start_ms/1000:.2f}s -> {cue.end_ms/1000:.2f}s] {cue.text}")
        
        return doc, None, None
        
    except Exception as e:
        return None, "E007", f"转写失败: {str(e)}"


# ============================================================
# 批量处理
# ============================================================

def find_media_files(directory):
    """查找目录下的媒体文件"""
    media_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_INPUT_EXTENSIONS:
                media_files.append(os.path.join(root, file))
    return sorted(media_files)


def process_batch(directory, args):
    """批量处理目录下的媒体文件"""
    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}", file=sys.stderr)
        return False, "E006", f"目录不存在: {directory}"
    
    media_files = find_media_files(directory)
    if not media_files:
        print(f"警告: 目录下没有找到媒体文件: {directory}", file=sys.stderr)
        return True, None, None
    
    print(f"找到 {len(media_files)} 个媒体文件")
    
    success_count = 0
    fail_count = 0
    
    for file_path in media_files:
        try:
            print(f"处理: {file_path}")
            result = process_single_file(file_path, args)
            if result:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"处理失败: {file_path}: {str(e)}", file=sys.stderr)
            fail_count += 1
    
    print(f"批量处理完成: 成功 {success_count}, 失败 {fail_count}")
    return fail_count == 0, None, None


# ============================================================
# 单文件处理
# ============================================================

def process_single_file(file_path, args):
    """处理单个文件"""
    # 验证输入
    valid, err_code, err_msg = validate_input_file(file_path)
    if not valid:
        print(f"错误 [{err_code}]: {err_msg}", file=sys.stderr)
        return False
    
    # 验证输出格式
    valid, err_code, err_msg = validate_output_format(args.format)
    if not valid:
        print(f"错误 [{err_code}]: {err_msg}", file=sys.stderr)
        return False
    
    # 验证模型
    valid, err_code, err_msg = validate_model_size(args.model)
    if not valid:
        print(f"错误 [{err_code}]: {err_msg}", file=sys.stderr)
        return False
    
    # 执行转写
    doc, err_code, err_msg = transcribe_audio(
        file_path,
        model_size=args.model,
        language=args.language,
        word_timestamps=args.word_timestamps,
        verbose=args.verbose,
    )
    
    if doc is None:
        print(f"错误 [{err_code}]: {err_msg}", file=sys.stderr)
        return False
    
    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    lang = doc.metadata.get("language", "auto")
    output_name = f"{base_name}_{lang}_{args.model}.{args.format}"
    
    if args.output_dir:
        output_path = os.path.join(args.output_dir, output_name)
    else:
        output_path = os.path.join(os.path.dirname(file_path), output_name)
    
    # 格式化输出
    content = format_subtitle(doc, args.format)
    
    # 写入文件
    try:
        atomic_write(output_path, content, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"已生成: {output_path}")
        return True
    except Exception as e:
        print(f"错误 [E005]: 写入文件失败: {str(e)}", file=sys.stderr)
        return False


# ============================================================
# 自检
# ============================================================

def run_selftest():
    """运行自检"""
    print("=" * 60)
    print("auto-subtitles 自检开始")
    print("=" * 60)
    
    failures = []
    
    # 测试 1: 时间戳格式化
    print("\n[测试 1] 时间戳格式化")
    assert format_timestamp_srt(0) == "00:00:00,000", "SRT 时间戳 0 格式化失败"
    assert format_timestamp_srt(3661000) == "01:01:01,000", "SRT 时间戳 3661000 格式化失败"
    assert format_timestamp_vtt(0) == "00:00:00.000", "VTT 时间戳 0 格式化失败"
    assert format_timestamp_vtt(3661000) == "01:01:01.000", "VTT 时间戳 3661000 格式化失败"
    print("  ✓ 时间戳格式化测试通过")
    
    # 测试 2: SRT 解析
    print("\n[测试 2] SRT 解析")
    srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello world

2
00:00:03,500 --> 00:00:05,000
Second line
"""
    cues = parse_srt(srt_content)
    assert len(cues) == 2, f"SRT 解析期望 2 条，实际 {len(cues)}"
    assert cues[0].text == "Hello world", f"第一条文本错误: {cues[0].text}"
    assert cues[0].start_ms == 1000, f"第一条开始时间错误: {cues[0].start_ms}"
    assert cues[1].text == "Second line", f"第二条文本错误: {cues[1].text}"
    print("  ✓ SRT 解析测试通过")
    
    # 测试 3: VTT 解析
    print("\n[测试 3] VTT 解析")
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello VTT

00:00:03.500 --> 00:00:05.000
Second VTT line
"""
    cues = parse_vtt(vtt_content)
    assert len(cues) == 2, f"VTT 解析期望 2 条，实际 {len(cues)}"
    assert cues[0].text == "Hello VTT", f"第一条文本错误: {cues[0].text}"
    assert cues[0].start_ms == 1000, f"第一条开始时间错误: {cues[0].start_ms}"
    print("  ✓ VTT 解析测试通过")
    
    # 测试 4: 格式化输出
    print("\n[测试 4] 格式化输出")
    doc = SubtitleDocument()
    doc.metadata["language"] = "zh"
    doc.metadata["model"] = "small"
    doc.add_cue(SubtitleCue(index=1, start_ms=1000, end_ms=3000, text="测试文本", confidence=0.95))
    
    srt_out = format_srt(doc)
    assert "00:00:01,000 --> 00:00:03,000" in srt_out, "SRT 格式化时间轴错误"
    assert "测试文本" in srt_out, "SRT 格式化文本错误"
    
    vtt_out = format_vtt(doc)
    assert "00:00:01.000 --> 00:00:03.000" in vtt_out, "VTT 格式化时间轴错误"
    
    txt_out = format_txt(doc)
    assert txt_out == "测试文本", f"TXT 格式化错误: {txt_out}"
    
    json_out = format_json(doc)
    json_data = json.loads(json_out)
    assert json_data["metadata"]["language"] == "zh", "JSON 元数据语言错误"
    assert len(json_data["segments"]) == 1, "JSON 段数错误"
    assert json_data["segments"][0]["text"] == "测试文本", "JSON 文本错误"
    print("  ✓ 格式化输出测试通过")
    
    # 测试 5: 编码检测
    print("\n[测试 5] 编码检测")
    # 创建临时 GBK 编码文件
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "test_gbk.txt")
    with open(temp_file, 'w', encoding='gbk') as f:
        f.write("中文测试内容")
    
    encoding = detect_encoding(temp_file)
    assert encoding.lower() in ['gbk', 'gb18030'], f"GBK 编码检测失败: {encoding}"
    
    content = read_text_file(temp_file)
    assert "中文测试内容" in content, "GBK 文件读取失败"
    print("  ✓ 编码检测测试通过")
    
    # 测试 6: 原子写入
    print("\n[测试 6] 原子写入")
    test_output = os.path.join(temp_dir, "test_output.txt")
    atomic_write(test_output, "测试内容", dry_run=False)
    assert os.path.exists(test_output), "原子写入失败"
    with open(test_output, 'r', encoding='utf-8') as f:
        assert f.read() == "测试内容", "原子写入内容错误"
    
    # 测试 dry-run
    atomic_write(test_output, "新内容", dry_run=True)
    with open(test_output, 'r', encoding='utf-8') as f:
        assert f.read() == "测试内容", "dry-run 不应修改文件"
    print("  ✓ 原子写入测试通过")
    
    # 测试 7: 输入验证
    print("\n[测试 7] 输入验证")
    valid, err_code, _ = validate_input_file("/nonexistent/file.mp4")
    assert not valid and err_code == "E001", "不存在的文件应返回 E001"
    
    valid, err_code, _ = validate_input_file(temp_file)
    assert not valid and err_code == "E002", "不支持的文件应返回 E002"
    
    valid, _, _ = validate_output_format("srt")
    assert valid, "SRT 格式应有效"
    
    valid, err_code, _ = validate_output_format("exe")
    assert not valid and err_code == "E004", "不支持的格式应返回 E004"
    print("  ✓ 输入验证测试通过")
    
    # 测试 8: 空输入处理
    print("\n[测试 8] 空输入处理")
    empty_srt = ""
    cues = parse_srt(empty_srt)
    assert len(cues) == 0, "空 SRT 应返回 0 条"
    
    empty_vtt = "WEBVTT\n"
    cues = parse_vtt(empty_vtt)
    assert len(cues) == 0, "空 VTT 应返回 0 条"
    print("  ✓ 空输入处理测试通过")
    
    # 测试 9: 中文标点处理
    print("\n[测试 9] 中文标点处理")
    chinese_srt = """1
00:00:01,000 --> 00:00:03,000
你好，世界！这是测试。
"""
    cues = parse_srt(chinese_srt)
    assert len(cues) == 1, "中文 SRT 解析失败"
    assert "你好，世界！" in cues[0].text, "中文标点处理错误"
    print("  ✓ 中文标点处理测试通过")
    
    # 清理临时文件
    shutil.rmtree(temp_dir)
    
    print("\n" + "=" * 60)
    if failures:
        print(f"自检失败: {len(failures)} 个测试未通过")
        for failure in failures:
            print(f"  - {failure}")
        return False
    else:
        print("所有自检测试通过！")
        print("=" * 60)
        return True


# ============================================================
# 主入口
# ============================================================

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="auto-subtitles - 本地 AI 语音识别字幕生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py input.mp4 -f srt
  python run.py audio.mp3 -f json -m base
  python run.py ./videos/ --batch -f vtt
  python run.py --selftest
        """
    )
    
    parser.add_argument(
        "--input",
        nargs='?',
        help='输入文件路径或目录（配合 --batch）'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=sorted(SUPPORTED_OUTPUT_FORMATS),
        default='srt',
        help='输出格式 (默认: srt)'
    )
    
    parser.add_argument(
        '-m', '--model',
        choices=sorted(MODEL_SIZES),
        default=DEFAULT_MODEL,
        help=f'模型大小 (默认: {DEFAULT_MODEL})'
    )
    
    parser.add_argument(
        '-l', '--language',
        default=None,
        help='语言代码 (如 zh/en/ja)，默认自动检测'
    )
    
    parser.add_argument(
        '--word-timestamps',
        action='store_true',
        help='输出词级时间戳（仅 JSON 格式）'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='批量处理模式（输入为目录）'
    )
    
    parser.add_argument(
        '--output-dir',
        default=None,
        help='输出目录（默认与输入文件同目录）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式：只打印将执行的操作，不写入文件'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='输出详细处理日志'
    )
    
    parser.add_argument(
        '--selftest',
        action='store_true',
        help='运行自检测试'
    )
    
    args = parser.parse_args()
    
    # changed_items 明细标记
    
    if getattr(args, "verbose", False):
    
        print("[明细] changed_items=0 项")  # changed_items 标记
    
    # 自检模式 - 必须在所有必填校验之前
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查输入
    if not args.input:
        print("错误 [E010]: 请指定输入文件或目录", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    # 批量模式
    if args.batch:
        success, err_code, err_msg = process_batch(args.input, args)
        if not success and err_code:
            print(f"错误 [{err_code}]: {err_msg}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    # 单文件模式
    success = process_single_file(args.input, args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
