#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
独立实现的 youtube-transcript-api 技能工具集。

本脚本为 clean-room 重写，仅依据功能规格实现，不包含任何第三方既有代码。
核心能力：
  1. 从 YouTube 视频 URL 或视频 ID 中提取视频 ID。
  2. 获取真实字幕轨道列表（通过网络请求）。
  3. 提取转写文本（结构化输出：文本、开始时间、持续时间）。
  4. 支持多语言字幕轨道选择。
  5. 支持自动生成字幕回退。
  6. 内置 --selftest 自检，覆盖核心链路。

错误码约定：
  E001: 输入参数缺失或格式错误
  E002: 视频 ID 解析失败
  E003: 不支持的非 YouTube 平台
  E004: 无法获取字幕轨道（视频无字幕）
  E005: 指定的语言轨道不存在
  E006: 转写文本提取失败
  E007: 内部数据异常
  E008: 命令行参数错误
  E009: 自检失败（内部逻辑错误）
  E010: 未预期的运行时错误

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class TranscriptSnippet:
    """单条字幕片段。"""
    text: str                    # 字幕文本
    start: float                 # 开始时间（秒）
    duration: float              # 持续时间（秒）


@dataclass
class TranscriptTrack:
    """一条字幕轨道。"""
    language: str                # 语言代码，如 'en', 'zh-Hans'
    language_code: str           # 语言代码（短格式）
    is_generated: bool           # 是否为自动生成字幕
    is_translatable: bool        # 是否可翻译
    snippets: List[TranscriptSnippet] = field(default_factory=list)


# ============================================================
# 网络请求工具（带重试退避和超时）
# ============================================================

class NetworkError(Exception):
    """网络请求异常。"""
    pass


def _http_get_with_retry(url: str, max_retries: int = 3, timeout: int = 10) -> str:
    """
    执行 HTTP GET 请求，带重试退避和超时。

    参数：
        url: 请求 URL
        max_retries: 最大重试次数
        timeout: 超时时间（秒）

    返回：
        响应文本

    异常：
        NetworkError: 网络请求失败
    """
    retry_delays = [1, 2, 4]  # 指数退避延迟（秒）
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    ]
    
    for attempt in range(max_retries):
        try:
            # 轮换 User-Agent
            ua = user_agents[attempt % len(user_agents)]
            req = urllib.request.Request(url, headers={
                'User-Agent': ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            })
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            # 处理限流和禁止访问
            if e.code in (429, 403):
                if attempt < max_retries - 1:
                    # 使用动态计算的延迟时间
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)] * (attempt + 1)
                    time.sleep(delay)
                    continue
                else:
                    raise NetworkError(f"HTTP {e.code}: 请求被限流或禁止，请稍后重试") from e
            elif e.code == 404:
                raise NetworkError(f"HTTP 404: 资源不存在") from e
            else:
                if attempt < max_retries - 1:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    time.sleep(delay)
                else:
                    raise NetworkError(f"HTTP {e.code}: {e}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_retries - 1:
                delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                time.sleep(delay)
            else:
                raise NetworkError(f"网络请求失败: {e}") from e
    raise NetworkError("网络请求失败")


# ============================================================
# YouTube 字幕获取核心实现
# ============================================================

def _extract_video_id(url_or_id: str) -> str:
    """
    从 YouTube 视频 URL 或视频 ID 中提取纯视频 ID。

    支持格式：
      - 纯视频 ID（11 位字符）
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - 其他带参数或路径的 YouTube 链接

    错误码：E002（解析失败）、E003（非 YouTube 平台）
    """
    if not url_or_id or not isinstance(url_or_id, str) or not url_or_id.strip():
        raise ValueError("E001: 输入参数缺失或格式错误")

    text = url_or_id.strip()

    # 判断是否为纯视频 ID（常见 YouTube ID 为 11 位字母数字）
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text

    # 尝试解析 URL
    if "youtube.com" in text or "youtu.be" in text:
        # 处理 youtu.be 短链接
        if "youtu.be" in text:
            match = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", text)
            if match:
                return match.group(1)
            raise ValueError("E002: 视频 ID 解析失败")

        # 处理 youtube.com 各种路径
        match = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", text)
        if match:
            return match.group(1)

        # 处理 /embed/ 或 /v/ 路径
        match = re.search(r"/(?:embed|v|shorts)/([A-Za-z0-9_-]{11})", text)
        if match:
            return match.group(1)

        raise ValueError("E002: 视频 ID 解析失败")
    else:
        raise ValueError("E003: 不支持的非 YouTube 平台")


def _parse_timedtext_xml(xml_content: str) -> List[TranscriptSnippet]:
    """
    解析 YouTube timedtext XML 格式的字幕内容。

    参数：
        xml_content: XML 字符串

    返回：
        字幕片段列表
    """
    snippets = []
    
    # 提取 <text> 标签内容
    text_pattern = re.compile(
        r'<text[^>]*start="([\d.]+)"[^>]*dur="([\d.]+)"[^>]*>(.*?)</text>',
        re.DOTALL
    )
    
    for match in text_pattern.finditer(xml_content):
        start = float(match.group(1))
        duration = float(match.group(2))
        # 解码 HTML 实体
        text = match.group(3)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        snippets.append(TranscriptSnippet(text=text, start=start, duration=duration))
    
    return snippets


def _fetch_transcript_data(video_id: str) -> List[TranscriptTrack]:
    """
    获取视频的字幕轨道列表（通过网络请求）。

    使用 YouTube 的 timedtext API 获取字幕数据。
    首先获取字幕轨道列表，然后获取各轨道内容。

    参数：
        video_id: YouTube 视频 ID

    返回：
        字幕轨道列表

    异常：
        NetworkError: 网络请求失败
        ValueError: 视频无字幕或数据异常
    """
    # 构建字幕轨道列表请求 URL
    track_list_url = (
        f"https://www.youtube.com/api/timedtext?v={video_id}"
        f"&type=list&asr=1&kind=asr&fmt=json3"
    )
    
    try:
        response = _http_get_with_retry(track_list_url)
    except NetworkError as e:
        raise ValueError(f"E010: 网络请求失败: {e}") from e
    
    # 解析轨道列表
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        # 尝试 XML 格式
        if '<track' in response:
            # 解析 XML 格式的轨道列表
            tracks = []
            track_pattern = re.compile(
                r'<track[^>]*lang_code="([^"]*)"[^>]*lang_translated="([^"]*)"[^>]*kind="([^"]*)"[^>]*>'
            )
            for match in track_pattern.finditer(response):
                lang_code = match.group(1)
                lang_name = match.group(2)
                kind = match.group(3)
                tracks.append({
                    'language_code': lang_code,
                    'language': lang_name,
                    'is_generated': kind == 'asr',
                    'is_translatable': True
                })
            
            if not tracks:
                raise ValueError("E004: 无法获取字幕轨道（视频无字幕）")
            
            # 获取每个轨道的字幕内容
            result_tracks = []
            for track_info in tracks:
                track_url = (
                    f"https://www.youtube.com/api/timedtext?v={video_id}"
                    f"&lang={track_info['language_code']}"
                    f"&fmt=xml"
                )
                try:
                    track_response = _http_get_with_retry(track_url)
                    snippets = _parse_timedtext_xml(track_response)
                    if snippets:
                        result_tracks.append(TranscriptTrack(
                            language=track_info['language'],
                            language_code=track_info['language_code'],
                            is_generated=track_info['is_generated'],
                            is_translatable=track_info['is_translatable'],
                            snippets=snippets
                        ))
                except NetworkError:
                    continue
            
            if not result_tracks:
                raise ValueError("E004: 无法获取字幕轨道（视频无字幕）")
            
            return result_tracks
        else:
            raise ValueError("E007: 内部数据异常")
    
    # 解析 JSON 格式的轨道列表
    if 'events' not in data:
        raise ValueError("E004: 无法获取字幕轨道（视频无字幕）")
    
    # 从事件中提取字幕轨道
    tracks = []
    seen_languages = set()
    
    for event in data.get('events', []):
        segs = event.get('segs', [])
        if not segs:
            continue
        
        # 获取语言信息
        lang_code = event.get('lang_code', 'unknown')
        if lang_code in seen_languages:
            continue
        
        seen_languages.add(lang_code)
        
        # 构建字幕片段
        snippets = []
        for seg in segs:
            text = seg.get('utf8', '')
            if not text:
                continue
            start = event.get('tStartMs', 0) / 1000.0
            duration = event.get('dDurationMs', 0) / 1000.0
            snippets.append(TranscriptSnippet(text=text, start=start, duration=duration))
        
        if snippets:
            tracks.append(TranscriptTrack(
                language=lang_code,
                language_code=lang_code,
                is_generated=event.get('kind', '') == 'asr',
                is_translatable=True,
                snippets=snippets
            ))
    
    if not tracks:
        raise ValueError("E004: 无法获取字幕轨道（视频无字幕）")
    
    return tracks


def _normalize_language_code(lang: str) -> str:
    """规范化语言代码，去除多余空格并转为小写（保留大写后缀）。"""
    if not lang:
        return ""
    return lang.strip().lower()


def _find_track(tracks: List[TranscriptTrack], language: Optional[str] = None) -> Optional[TranscriptTrack]:
    """
    在字幕轨道列表中查找指定语言轨道。

    若未指定语言，返回第一条轨道（若有）。
    若指定语言，匹配 language_code 或 language 字段。
    """
    if not tracks:
        return None

    if not language:
        return tracks[0]

    target = _normalize_language_code(language)

    for track in tracks:
        # 匹配 language_code（精确匹配）
        if _normalize_language_code(track.language_code) == target:
            return track
        # 匹配 language 显示名称
        if _normalize_language_code(track.language) == target:
            return track

    return None


# ============================================================
# 对外核心 API
# ============================================================

def get_transcript_tracks(url_or_id: str) -> List[Dict]:
    """
    获取视频可用的字幕轨道列表（元数据，不含字幕内容）。

    参数：
        url_or_id: YouTube 视频 URL 或视频 ID

    返回：
        字幕轨道元数据列表，每个元素包含：
        - language: 语言显示名称
        - language_code: 语言代码
        - is_generated: 是否自动生成
        - is_translatable: 是否可翻译

    错误码：
        E001: 输入参数错误
        E002: 视频 ID 解析失败
        E003: 非 YouTube 平台
        E004: 视频无字幕
    """
    try:
        video_id = _extract_video_id(url_or_id)
    except ValueError as e:
        raise ValueError(str(e)) from e

    tracks = _fetch_transcript_data(video_id)

    if not tracks:
        raise ValueError("E004: 无法获取字幕轨道（视频无字幕）")

    result = []
    for track in tracks:
        result.append({
            "language": track.language,
            "language_code": track.language_code,
            "is_generated": track.is_generated,
            "is_translatable": track.is_translatable,
        })
    return result


def get_transcript(url_or_id: str, language: Optional[str] = None) -> Dict:
    """
    获取视频的转写文本（结构化数据）。

    参数：
        url_or_id: YouTube 视频 URL 或视频 ID
        language:  可选，指定语言代码（如 'en', 'zh-Hans'）或语言名称
                   不指定时返回第一条字幕轨道

    返回：
        结构化转写数据：
        - video_id: 视频 ID
        - language: 语言显示名称
        - language_code: 语言代码
        - is_generated: 是否自动生成
        - snippets: 字幕片段列表（text/start/duration）

    错误码：
        E001: 输入参数错误
        E002: 视频 ID 解析失败
        E003: 非 YouTube 平台
        E004: 视频无字幕
        E005: 指定语言不存在
        E006: 转写提取失败
    """
    try:
        video_id = _extract_video_id(url_or_id)
    except ValueError as e:
        raise ValueError(str(e)) from e

    tracks = _fetch_transcript_data(video_id)

    if not tracks:
        raise ValueError("E004: 无法获取字幕轨道（视频无字幕）")

    track = _find_track(tracks, language)
    if track is None:
        raise ValueError("E005: 指定的语言轨道不存在")

    if not track.snippets:
        raise ValueError("E006: 转写文本提取失败（字幕内容为空）")

    return {
        "video_id": video_id,
        "language": track.language,
        "language_code": track.language_code,
        "is_generated": track.is_generated,
        "snippets": [
            {
                "text": s.text,
                "start": s.start,
                "duration": s.duration,
            }
            for s in track.snippets
        ],
    }


def get_transcript_text(url_or_id: str, language: Optional[str] = None) -> str:
    """
    获取纯文本转写内容（不含时间戳）。

    参数：
        url_or_id: YouTube 视频 URL 或视频 ID
        language:  可选，指定语言

    返回：
        拼接后的纯文本，每段字幕以空格连接。

    错误码：同 get_transcript
    """
    data = get_transcript(url_or_id, language)
    texts = [snippet["text"] for snippet in data["snippets"]]
    return " ".join(texts)


# ============================================================
# 命令行接口
# ============================================================

def _cmd_list(args: argparse.Namespace) -> int:
    """处理 list 子命令：列出可用字幕轨道。"""
    try:
        tracks = get_transcript_tracks(args.video)
    except ValueError as e:
        print
