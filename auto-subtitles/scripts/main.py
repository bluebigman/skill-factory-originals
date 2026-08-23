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
import urllib.request
import urllib.error
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

# 模型大小默认值，运行时校验
DEFAULT_MODEL = 'small'

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
REQUEST_TIMEOUT = 30

# 并发控制
MAX_WORKERS = 2

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


def retry_with_backoff(func, *args, max_retries=MAX_RETRIES, base_delay=RETRY_BASE_DELAY, **kwargs):
    """带指数退避的重试机制"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"重试 {attempt + 1}/{max_retries}，等待 {delay:.1f}s: {str(e)}", file=sys.stderr)
            time.sleep(delay)
    return None


def download_with_retry(url, dest_path, timeout=REQUEST_TIMEOUT):
    """带重试和超时的文件下载"""
    def _download():
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            with open(dest_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        return True
    
    return retry_with_backoff(_download, max_retries=MAX_RETRIES, base_delay=RETRY_BASE_DELAY)


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

def transcribe_audio(file_path, model_size=None, language=None, word_timestamps=False, verbose=False):
    """使用 faster-whisper 进行语音转写"""
    # 运行时校验模型大小，无效时回退到默认值
    if model_size is None:
        model_size = os.environ.get('AUTO_SUBTITLES_MODEL', DEFAULT_MODEL)
    if model_size not in MODEL_SIZES:
        print(f"警告: 模型 '{model_size}' 不在支持列表中，回退到默认模型 'small'", file=sys.stderr)
        model_size = DEFAULT_MODEL
    
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("错误: 未安装 faster-whisper，请运行: pip install faster-whisper", file=sys.stderr)
        return None, "E003", "faster-whisper 未安装"
    
    def _do_transcribe():
        if verbose:
            print(f"加载模型: {model_size}")
        
        model = Whis
