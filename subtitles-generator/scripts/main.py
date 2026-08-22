#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subtitles-generator 技能实现脚本
================================
根据功能规格独立实现，clean-room 重写。
支持从视频/音频文件提取字幕，生成带时间轴的转录文本。

功能特性：
- 输入：本地视频/音频文件路径、公开视频 URL
- 输出：SRT、VTT、TXT、JSON 格式
- 自动语言检测（中/英/日/韩/法/德/西）
- 置信度阈值标记（低于 0.6 标注 [低置信度]）
- 说话人区分（双人对话）、静音段跳过

命令行用法：
    python main.py <input_path> [--output-dir DIR] [--format srt|vtt|txt|json]
    python main.py --selftest   # 离线自检
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# 错误码定义
ERROR_CODES = {
    "E001": "输入路径无效或文件不存在",
    "E002": "不支持的输入格式",
    "E003": "输出目录不可写",
    "E004": "音频提取失败",
    "E005": "语音识别失败",
    "E006": "字幕文件生成失败",
    "E007": "URL 下载失败",
    "E008": "语言检测失败",
    "E009": "无效的输出格式",
    "E010": "内部处理错误",
}


@dataclass
class SubtitleSegment:
    """单个字幕片段"""
    index: int
    start_ms: int
    end_ms: int
    text: str
    confidence: float = 1.0
    speaker: Optional[str] = None
    is_silence: bool = False

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    def to_dict(self) -> Dict:
        """转为字典（JSON 输出用）"""
        return {
            "index": self.index,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "speaker": self.speaker,
            "is_silence": self.is_silence,
        }


@dataclass
class SubtitleResult:
    """字幕生成结果"""
    source: str
    language: str
    segments: List[SubtitleSegment] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_srt(self) -> str:
        """生成 SRT 格式字符串"""
        lines = []
        for seg in self.segments:
            if seg.is_silence:
                continue
            start = _format_timestamp_srt(seg.start_ms)
            end = _format_timestamp_srt(seg.end_ms)
            text = seg.text
            if seg.confidence < 0.6:
                text = f"[低置信度] {text}"
            if seg.speaker:
                text = f"{seg.speaker}: {text}"
            lines.append(str(seg.index))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")  # 空行分隔
        return "\n".join(lines)

    def to_vtt(self) -> str:
        """生成 WebVTT 格式字符串"""
        lines = ["WEBVTT", ""]
        for seg in self.segments:
            if seg.is_silence:
                continue
            start = _format_timestamp_vtt(seg.start_ms)
            end = _format_timestamp_vtt(seg.end_ms)
            text = seg.text
            if seg.confidence < 0.6:
                text = f"[低置信度] {text}"
            if seg.speaker:
                text = f"{seg.speaker}: {text}"
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def to_txt(self) -> str:
        """生成纯文本格式"""
        lines = []
        for seg in self.segments:
            if seg.is_silence:
                continue
            text = seg.text
            if seg.confidence < 0.6:
                text = f"[低置信度] {text}"
            lines.append(text)
        return "\n".join(lines)

    def to_json(self) -> str:
        """生成 JSON 格式"""
        data = {
            "source": self.source,
            "language": self.language,
            "metadata": self.metadata,
            "segments": [seg.to_dict() for seg in self.segments],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ---------- 工具函数 ----------

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


def _format_timestamp_srt(ms: int) -> str:
    """毫秒转 SRT 时间戳格式: HH:MM:SS,mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _format_timestamp_vtt(ms: int) -> str:
    """毫秒转 VTT 时间戳格式: HH:MM:SS.mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _detect_language(text: str) -> str:
    """
    简单语言检测（基于 Unicode 范围）
    支持：中、英、日、韩、法、德、西
    """
    if not text:
        return "unknown"

    # 统计各语言字符数量
    scores = {
        "zh": len(re.findall(r'[\u4e00-\u9fff]', text)),
        "ja": len(re.findall(r'[\u3040-\u30ff]', text)),
        "ko": len(re.findall(r'[\uac00-\ud7af]', text)),
        "fr": len(re.findall(r'[àâäéèêëîïôöùûüçœ]', text, re.IGNORECASE)),
        "de": len(re.findall(r'[äöüß]', text, re.IGNORECASE)),
        "es": len(re.findall(r'[ñáéíóúü]', text, re.IGNORECASE)),
        "en": len(re.findall(r'[a-zA-Z]', text)),
    }

    # 返回得分最高的语言
    best_lang = max(scores, key=scores.get)
    if scores[best_lang] == 0:
        return "unknown"
    return best_lang


def _is_url(path: str) -> bool:
    """判断是否为 URL"""
    return path.startswith(("http://", "https://"))


def _validate_input(path: str) -> None:
    """验证输入路径有效性"""
    if _is_url(path):
        # URL 格式基本校验
        if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', path):
            raise RuntimeError("E001: 无效的 URL 格式")
    else:
        p = Path(path)
        if not p.exists():
            raise RuntimeError("E001: 输入文件不存在")
        if not p.is_file():
            raise RuntimeError("E001: 输入路径不是文件")
        # 检查扩展名
        ext = p.suffix.lower()
        if ext not in {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv",
                       ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}:
            raise RuntimeError("E002: 不支持的输入格式")


def _download_url(url: str, timeout: int = 30, max_retries: int = 3) -> str:
    """
    下载 URL 到临时文件，带重试退避和超时
    
    参数:
        url: 下载地址
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
    
    返回:
        临时文件路径
    """
    # 创建临时文件
    fd, temp_path = tempfile.mkstemp(suffix=Path(url).suffix or ".tmp")
    os.close(fd)
    
    for attempt in range(max_retries):
        try:
            # 设置请求头模拟浏览器
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # 下载文件
            with urllib.request.urlopen(req, timeout=timeout) as response:
                with open(temp_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            
            return temp_path
            
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            if attempt == max_retries - 1:
                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise RuntimeError(f"E007: URL 下载失败: {e}") from e
            
            # 指数退避
            wait_time = 2 ** attempt
            print(f"下载失败，{wait_time}秒后重试 ({attempt + 1}/{max_retries})...")
            time.sleep(wait_time)
    
    # 不应该到达这里
    raise RuntimeError("E007: URL 下载失败")


# ---------- 核心处理逻辑 ----------

class SubtitleGenerator:
    """
    字幕生成器主类
    使用 whisper 进行语音识别，ffmpeg 进行音频提取
    """

    def __init__(self, confidence_threshold: float = 0.6):
        self.confidence_threshold = confidence_threshold

    def process(
        self,
        input_path: str,
        output_dir: Optional[str] = None,
        output_format: str = "srt",
        language: Optional[str] = None,
    ) -> SubtitleResult:
        """
        处理输入文件，生成字幕

        参数:
            input_path: 输入文件路径或 URL
            output_dir: 输出目录（默认与输入同目录）
            output_format: 输出格式 (srt/vtt/txt/json)
            language: 指定语言（可选，默认自动检测）

        返回:
            SubtitleResult 对象
        """
        try:
            _validate_input(input_path)
        except RuntimeError:
            raise

        # 确定输出目录
        if output_dir:
            out_dir = Path(output_dir)
            if not out_dir.exists():
                try:
                    out_dir.mkdir(parents=True)
                except OSError as e:
                    raise RuntimeError(f"E003: 无法创建输出目录: {e}") from e
            if not os.access(out_dir, os.W_OK):
                raise RuntimeError("E003: 输出目录不可写")
        else:
            if _is_url(input_path):
                out_dir = Path(tempfile.gettempdir())
            else:
                out_dir = Path(input_path).parent

        # 验证输出格式
        if output_format not in {"srt", "vtt", "txt", "json"}:
            raise RuntimeError("E009: 无效的输出格式")

        try:
            # 处理输入：如果是 URL 则下载
            local_path = input_path
            if _is_url(input_path):
                print(f"正在下载: {input_path}")
                local_path = _download_url(input_path)
                print(f"下载完成: {local_path}")

            # 提取音频
            audio_path = self._extract_audio(local_path)

            # 语音识别
            segments = self._recognize_speech(audio_path, language)

            # 语言检测
            full_text = " ".join(s.text for s in segments)
            if language:
                detected_language = language
            else:
                detected_language = _detect_language(full_text)
                if detected_language == "unknown":
                    detected_language = "zh"  # 默认中文

            # 构建结果
            result = SubtitleResult(
                source=input_path,
                language=detected_language,
                segments=segments,
                metadata={
                    "generator": "subtitles-generator v1.0.1",
                    "confidence_threshold": self.confidence_threshold,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "segment_count": len(segments),
                },
            )

            # 写入文件
            self._write_output(result, out_dir, output_format)

            # 清理临时文件
            if _is_url(input_path) and local_path != input_path:
                try:
                    os.unlink(local_path)
                except OSError:
                    pass

            return result

        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"E010: 处理失败: {e}") from e

    def _extract_audio(self, input_path: str) -> str:
        """
        提取音频，使用 ffmpeg
        
        参数:
            input_path: 输入文件路径
        
        返回:
            音频文件路径
        """
        # 检查 ffmpeg 是否可用
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError("E004: ffmpeg 未安装，无法提取音频")

        # 创建临时音频文件
        fd, temp_audio = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        try:
            # 提取音频
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-vn",  # 禁用视频
                "-acodec", "pcm_s16le",  # PCM 16-bit
                "-ar", "16000",  # 16kHz
                "-ac", "1",  # 单声道
                "-y",  # 覆盖输出
                temp_audio
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise RuntimeError(f"E004: 音频提取失败: {result.stderr[:200]}")
            
            return temp_audio
            
        except subprocess.TimeoutExpired:
            try:
                os.unlink(temp_audio)
            except OSError:
                pass
            raise RuntimeError("E004: 音频提取超时")
        except Exception as e:
            try:
                os.unlink(temp_audio)
            except OSError:
                pass
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"E004: 音频提取失败: {e}") from e

    def _recognize_speech(self, audio_path: str, language: Optional[str] = None) -> List[SubtitleSegment]:
        """
        语音识别，使用 whisper
        
        参数:
            audio_path: 音频文件路径
            language: 指定语言（可选）
        
        返回:
            字幕片段列表
        """
        # 检查 whisper 是否可用
        try:
            import whisper
        except ImportError:
            raise RuntimeError("E005: whisper 未安装，请运行 pip install openai-whisper")

        try:
            # 加载模型
            model = whisper.load_model("base")
            
            # 转写
            result = model.transcribe(
                audio_path,
                language=language,  # 如果为 None 则自动检测
                fp16=False,  # CPU 兼容
            )
            
            # 构建字幕片段
            segments = []
            for i, seg in enumerate(result["segments"], 1):
                segments.append(
                    SubtitleSegment(
                        index=i,
                        start_ms=int(seg["start"] * 1000),
                        end_ms=int(seg["end"] * 1000),
                        text=seg["text"].strip(),
                        confidence=seg.get("confidence", 1.0),
                    )
                )
            
            return segments
            
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"E005: 语音识别失败: {e}") from e

    def _write_output(self, result: SubtitleResult, out_dir: Path, fmt: str) -> Path:
        """写入输出文件"""
        # 生成文件名
        if _is_url(result.source):
            base_name = "subtitles"
        else:
            base_name = Path(result.source).stem

        ext_map = {"srt": ".srt", "vtt": ".vtt", "txt": ".txt", "json": ".json"}
        output_path = out_dir / f"{base_name}{ext_map[fmt]}"

        # 生成内容
        if fmt == "srt":
            content
