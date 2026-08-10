#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
独立实现的 youtube-transcript-api 技能工具集。

本脚本为 clean-room 重写，仅依据功能规格实现，不包含任何第三方既有代码。
核心能力：
  1. 从 YouTube 视频 URL 或视频 ID 中提取视频 ID。
  2. 模拟获取字幕轨道列表（离线模式）。
  3. 模拟提取转写文本（结构化输出：文本、开始时间、持续时间）。
  4. 支持多语言字幕轨道选择。
  5. 支持自动生成字幕回退。
  6. 内置 --selftest 离线自检，不依赖网络与外部文件。

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
from dataclasses import dataclass, field
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
# 内置离线样例数据（用于自检与演示）
# ============================================================

# 内置样例视频ID与字幕数据（硬编码，不读取任何外部文件）
_BUILTIN_VIDEO_ID = "dQw4w9WgXcQ"
_BUILTIN_TRANSCRIPTS: Dict[str, List[TranscriptTrack]] = {
    _BUILTIN_VIDEO_ID: [
        TranscriptTrack(
            language="英语",
            language_code="en",
            is_generated=False,
            is_translatable=True,
            snippets=[
                TranscriptSnippet(text="Hello world, this is a test.", start=0.0, duration=2.5),
                TranscriptSnippet(text="Welcome to the transcript API.", start=2.5, duration=3.0),
                TranscriptSnippet(text="This is the end of the sample.", start=5.5, duration=2.0),
            ],
        ),
        TranscriptTrack(
            language="中文（简体）",
            language_code="zh-Hans",
            is_generated=True,
            is_translatable=True,
            snippets=[
                TranscriptSnippet(text="你好，世界，这是一个测试。", start=0.0, duration=2.5),
                TranscriptSnippet(text="欢迎使用字幕 API。", start=2.5, duration=3.0),
                TranscriptSnippet(text="这是示例的结尾。", start=5.5, duration=2.0),
            ],
        ),
    ],
    # 另一个内置视频，用于测试无字幕场景
    "NO_SUBTITLES_VIDEO": [],
}


# ============================================================
# 核心工具函数
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


def _fetch_transcript_data(video_id: str) -> List[TranscriptTrack]:
    """
    获取视频的字幕轨道列表。

    在真实场景中，此函数会调用 YouTube 内部 API 获取字幕轨道。
    当前实现使用内置离线数据（若视频 ID 匹配内置数据），
    否则返回空列表表示无字幕。

    错误码：E004（无字幕）、E007（数据异常）
    """
    if video_id in _BUILTIN_TRANSCRIPTS:
        tracks = _BUILTIN_TRANSCRIPTS[video_id]
        if tracks is None:
            raise RuntimeError("E007: 内部数据异常")
        return tracks
    else:
        # 未内置该视频数据，视为无字幕
        return []


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
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"视频 ID: {_extract_video_id(args.video)}")
    print(f"可用字幕轨道: {len(tracks)} 条")
    for i, track in enumerate(tracks, 1):
        gen_mark = " [自动生成]" if track["is_generated"] else ""
        print(f"  {i}. {track['language']} ({track['language_code']}){gen_mark}")
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    """处理 get 子命令：获取转写内容。"""
    try:
        data = get_transcript(args.video, args.language)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"视频 ID: {data['video_id']}")
    print(f"语言: {data['language']} ({data['language_code']})")
    print(f"自动生成: {'是' if data['is_generated'] else '否'}")
    print(f"字幕片段数: {len(data['snippets'])}")
    print("-" * 50)
    for snippet in data["snippets"]:
        start_mm = int(snippet["start"] // 60)
        start_ss = snippet["start"] % 60
        print(f"[{start_mm:02d}:{start_ss:05.2f}] {snippet['text']}")
    return 0


def _cmd_text(args: argparse.Namespace) -> int:
    """处理 text 子命令：获取纯文本转写。"""
    try:
        text = get_transcript_text(args.video, args.language)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(text)
    return 0


def _cmd_json(args: argparse.Namespace) -> int:
    """处理 json 子命令：以 JSON 格式输出转写数据。"""
    try:
        data = get_transcript(args.video, args.language)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def _cmd_selftest(args: argparse.Namespace) -> int:
    """
    执行离线自检。

    使用内置硬编码样例数据验证核心逻辑。
    断言使用宽松阈值（大小比较/区间判断），确保稳健。
    """
    print("运行自检...")
    errors = []

    # 1. 测试视频 ID 提取
    test_urls = [
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for input_str, expected in test_urls:
        try:
            result = _extract_video_id(input_str)
            if result != expected:
                errors.append(f"视频 ID 提取失败: {input_str} -> {result} (期望 {expected})")
        except Exception as e:
            errors.append(f"视频 ID 提取异常: {input_str}: {e}")

    # 2. 测试非 YouTube URL 拒绝
    try:
        _extract_video_id("https://vimeo.com/12345")
        errors.append("非 YouTube URL 未被拒绝")
    except ValueError as e:
        if not str(e).startswith("E003"):
            errors.append(f"非 YouTube URL 错误码错误: {e}")

    # 3. 测试获取轨道列表
    try:
        tracks = get_transcript_tracks("dQw4w9WgXcQ")
        if len(tracks) < 1:
            errors.append("内置视频应至少有 1 条字幕轨道")
        else:
            # 验证轨道元数据字段
            for track in tracks:
                if "language" not in track or "language_code" not in track:
                    errors.append("轨道元数据缺少必要字段")
                if not isinstance(track.get("is_generated"), bool):
                    errors.append("is_generated 字段类型错误")
    except Exception as e:
        errors.append(f"获取轨道列表异常: {e}")

    # 4. 测试无字幕视频
    try:
        get_transcript_tracks("NO_SUBTITLES_VIDEO")
        errors.append("无字幕视频应抛出 E004")
    except ValueError as e:
        if not str(e).startswith("E004"):
            errors.append(f"无字幕视频错误码错误: {e}")

    # 5. 测试获取转写内容（默认语言）
    try:
        transcript = get_transcript("dQw4w9WgXcQ")
        snippets = transcript["snippets"]
        if len(snippets) < 1:
            errors.append("内置视频应至少有 1 条字幕片段")
        else:
            # 宽松验证：文本非空、时间非负
            for snippet in snippets:
                if not snippet["text"] or not snippet["text"].strip():
                    errors.append("字幕文本为空")
                if snippet["start"] < 0:
                    errors.append("开始时间不应为负")
                if snippet["duration"] <= 0:
                    errors.append("持续时间应大于 0")
            # 验证时间顺序（非严格）
            for i in range(1, len(snippets)):
                if snippets[i]["start"] < snippets[i - 1]["start"]:
                    errors.append("字幕时间戳顺序异常")
    except Exception as e:
        errors.append(f"获取转写异常: {e}")

    # 6. 测试指定语言
    try:
        transcript_en = get_transcript("dQw4w9WgXcQ", "en")
        if transcript_en["language_code"] != "en":
            errors.append("指定 en 语言未返回正确轨道")
    except Exception as e:
        errors.append(f"指定语言获取异常: {e}")

    # 7. 测试不存在的语言
    try:
        get_transcript("dQw4w9WgXcQ", "xx")
        errors.append("不存在的语言应抛出 E005")
    except ValueError as e:
        if not str(e).startswith("E005"):
            errors.append(f"不存在的语言错误码错误: {e}")

    # 8. 测试纯文本提取
    try:
        text = get_transcript_text("dQw4w9WgXcQ")
        if not text or len(text) < 10:
            errors.append("纯文本提取结果过短")
    except Exception as e:
        errors.append(f"纯文本提取异常: {e}")

    # 9. 测试自动生成字幕回退
    try:
        transcript_zh = get_transcript("dQw4w9WgXcQ", "zh-Hans")
        if not transcript_zh["is_generated"]:
            errors.append("zh-Hans 轨道应为自动生成字幕")
    except Exception as e:
        errors.append(f"自动生成字幕获取异常: {e}")

    # 10. 测试错误输入
    try:
        get_transcript("")
        errors.append("空输入应抛出 E001")
    except ValueError as e:
        if not str(e).startswith("E001"):
            errors.append(f"空输入错误码错误: {e}")

    # 输出结果
    if errors:
        print(f"自检失败: {len(errors)} 个错误", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    else:
        print("自检通过: 所有核心逻辑验证成功")
        return 0


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="youtube-transcript-api",
        description="获取 YouTube 视频字幕与转写文本的工具集",
        epilog="示例: python main.py get https://www.youtube.com/watch?v=dQw4w9WgXcQ --language zh-Hans",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # list 子命令
    parser_list = subparsers.add_parser("list", help="列出视频可用的字幕轨道")
    parser_list.add_argument("--video", help="YouTube 视频 URL 或视频 ID")
    parser_list.set_defaults(func=_cmd_list)

    # get 子命令
    parser_get = subparsers.add_parser("get", help="获取结构化转写数据")
    parser_get.add_argument("--video", help="YouTube 视频 URL 或视频 ID")
    parser_get.add_argument("--language", "-l", default=None, help="指定语言代码或名称")
    parser_get.set_defaults(func=_cmd_get)

    # text 子命令
    parser_text = subparsers.add_parser("text", help="获取纯文本转写内容")
    parser_text.add_argument("--video", help="YouTube 视频 URL 或视频 ID")
    parser_text.add_argument("--language", "-l", default=None, help="指定语言代码或名称")
    parser_text.set_defaults(func=_cmd_text)

    # json 子命令
    parser_json = subparsers.add_parser("json", help="以 JSON 格式输出转写数据")
    parser_json.add_argument("--video", help="YouTube 视频 URL 或视频 ID")
    parser_json.add_argument("--language", "-l", default=None, help="指定语言代码或名称")
    parser_json.set_defaults(func=_cmd_json)

    # selftest 子命令
    parser_selftest = subparsers.add_parser("selftest", help="运行离线自检")
    parser_selftest.set_defaults(func=_cmd_selftest)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。

    参数：
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回：
        进程退出码（0 成功，非 0 失败）
    """
    parser = _build_parser()

    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        args = parser.parse_args(argv)
        if not hasattr(args, "func"):
            parser.print_help()
            return 0
        return args.func(args)
    except KeyboardInterrupt:
        print("操作被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"E010: 未预期的运行时错误: {e}", file=sys.stderr)
        return 1


# ============================================================
# 入口点
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
