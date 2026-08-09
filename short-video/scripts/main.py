#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短视频处理工具 - 字幕提取、视频信息识别、结果校验
基于功能规格独立实现，不依赖任何既有代码。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文件不存在",
    "E002": "ffmpeg 未安装",
    "E003": "视频无字幕流且未安装 Whisper",
    "E004": "字幕流提取失败",
    "E005": "输出文件校验失败",
    "E006": "磁盘空间不足",
    "E007": "视频编码不支持",
    "E008": "输入参数无效",
    "E009": "文件读取失败",
    "E010": "内部逻辑错误",
}


class VideoToolError(Exception):
    """视频处理工具自定义异常，携带错误码。"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 输入校验模块
# ============================================================
def validate_input_file(file_path: str) -> Path:
    """
    校验输入文件是否存在且可读。

    参数:
        file_path: 文件路径字符串

    返回:
        Path 对象

    异常:
        VideoToolError: E001 文件不存在, E008 参数无效
    """
    if not file_path or not isinstance(file_path, str):
        raise VideoToolError("E008", "文件路径必须是非空字符串")

    path = Path(file_path).expanduser().resolve()

    # 路径白名单校验：只允许常规文件路径，拒绝特殊字符
    if not re.match(r"^[\w\-\/\.\u4e00-\u9fff]+$", str(path)):
        raise VideoToolError("E008", "文件路径包含非法字符")

    if not path.exists():
        raise VideoToolError("E001", f"未找到输入文件: {file_path}")

    if not path.is_file():
        raise VideoToolError("E008", f"路径不是文件: {file_path}")

    if not os.access(path, os.R_OK):
        raise VideoToolError("E008", f"文件不可读: {file_path}")

    return path


def validate_output_path(output_path: str, input_path: Path) -> Path:
    """
    校验输出路径是否合法。

    参数:
        output_path: 输出路径字符串
        input_path: 输入文件路径

    返回:
        Path 对象
    """
    if not output_path:
        # 默认输出到输入文件同目录
        return input_path.with_suffix(".srt")

    path = Path(output_path).expanduser().resolve()

    # 检查输出目录是否存在
    parent_dir = path.parent
    if not parent_dir.exists():
        raise VideoToolError("E008", f"输出目录不存在: {parent_dir}")

    if not os.access(parent_dir, os.W_OK):
        raise VideoToolError("E008", f"输出目录不可写: {parent_dir}")

    return path


# ============================================================
# 核心逻辑模块
# ============================================================
def check_ffmpeg_available() -> bool:
    """
    检查 ffmpeg 是否可用。

    返回:
        True 如果 ffmpeg 可用，否则 False
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def probe_video_info(video_path: Path) -> Dict:
    """
    使用 ffprobe 解析视频元数据。

    参数:
        video_path: 视频文件路径

    返回:
        包含视频信息的字典

    异常:
        VideoToolError: E002 ffmpeg 未安装, E007 编码不支持
    """
    if not check_ffmpeg_available():
        raise VideoToolError("E002")

    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise VideoToolError("E007", f"视频解析失败: {result.stderr[:200]}")

        info = json.loads(result.stdout)

        # 提取关键信息
        video_info = {
            "format": info.get("format", {}),
            "streams": info.get("streams", []),
            "duration": float(info.get("format", {}).get("duration", 0)),
            "bit_rate": info.get("format", {}).get("bit_rate", "0"),
            "video_streams": [],
            "audio_streams": [],
            "subtitle_streams": [],
        }

        # 分类流
        for stream in info.get("streams", []):
            codec_type = stream.get("codec_type", "")
            if codec_type == "video":
                video_info["video_streams"].append(stream)
            elif codec_type == "audio":
                video_info["audio_streams"].append(stream)
            elif codec_type == "subtitle":
                video_info["subtitle_streams"].append(stream)

        return video_info

    except json.JSONDecodeError as exc:
        raise VideoToolError("E007", f"ffprobe 输出解析失败: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoToolError("E007", f"ffprobe 超时: {exc}") from exc


def extract_subtitle_stream(video_path: Path, output_path: Path, stream_index: int = 0) -> Path:
    """
    从视频中提取字幕流为 SRT 文件。

    参数:
        video_path: 视频文件路径
        output_path: 输出 SRT 文件路径
        stream_index: 字幕流索引

    返回:
        输出文件路径

    异常:
        VideoToolError: E004 提取失败
    """
    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-map", f"0:s:{stream_index}",
            "-y",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise VideoToolError("E004", f"字幕提取失败: {result.stderr[-200:]}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise VideoToolError("E004", "提取的字幕文件为空")

        return output_path

    except subprocess.TimeoutExpired as exc:
        raise VideoToolError("E004", f"字幕提取超时: {exc}") from exc
    except subprocess.SubprocessError as exc:
        raise VideoToolError("E004", f"字幕提取进程错误: {exc}") from exc


def transcribe_audio(video_path: Path, output_path: Path, language: str = "zh") -> Path:
    """
    使用 Whisper 进行语音转写。

    参数:
        video_path: 视频文件路径
        output_path: 输出 SRT 文件路径
        language: 识别语言

    返回:
        输出文件路径

    异常:
        VideoToolError: E003 Whisper 未安装
    """
    # 检查 whisper 是否可用
    try:
        import whisper  # pip install openai-whisper
    except ImportError as exc:
        raise VideoToolError("E003", "未安装 openai-whisper，请执行 pip install openai-whisper") from exc

    try:
        model = whisper.load_model("base")
        result = model.transcribe(str(video_path), language=language)

        # 生成 SRT 格式
        srt_content = []
        for idx, segment in enumerate(result.get("segments", []), start=1):
            start_time = format_srt_time(segment.get("start", 0))
            end_time = format_srt_time(segment.get("end", 0))
            text = segment.get("text", "").strip()
            srt_content.append(f"{idx}\n{start_time} --> {end_time}\n{text}\n")

        # 写入文件
        write_text_file_safe(output_path, "\n".join(srt_content))
        return output_path

    except Exception as exc:
        raise VideoToolError("E003", f"语音转写失败: {exc}") from exc


def format_srt_time(seconds: float) -> str:
    """
    将秒数格式化为 SRT 时间格式。

    参数:
        seconds: 秒数

    返回:
        SRT 时间字符串 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_text_file_safe(file_path: Path, content: str) -> None:
    """
    安全写入文本文件，处理编码问题。

    参数:
        file_path: 文件路径
        content: 文本内容

    异常:
        VideoToolError: E009 写入失败
    """
    try:
        # 尝试 UTF-8 写入
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except (IOError, OSError) as exc:
        try:
            # 降级为 GBK
            with open(file_path, "w", encoding="gbk") as f:
                f.write(content)
        except (IOError, OSError) as exc2:
            raise VideoToolError("E009", f"文件写入失败: {exc2}") from exc2


def read_text_file_safe(file_path: Path) -> str:
    """
    安全读取文本文件，支持多编码。

    参数:
        file_path: 文件路径

    返回:
        文件内容字符串

    异常:
        VideoToolError: E009 读取失败
    """
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, IOError):
            continue

    # 最后尝试 with errors="replace"
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (IOError, OSError) as exc:
        raise VideoToolError("E009", f"文件读取失败: {exc}") from exc


def validate_srt_format(srt_content: str) -> Tuple[bool, List[str]]:
    """
    校验 SRT 格式是否合法。

    参数:
        srt_content: SRT 文件内容

    返回:
        (是否合法, 错误列表)
    """
    errors = []
    if not srt_content.strip():
        return False, ["SRT 文件为空"]

    # 检查时间轴格式
    time_pattern = re.compile(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}")
    blocks = srt_content.strip().split("\n\n")

    for idx, block in enumerate(blocks, 1):
        lines = block.strip().split("\n")
        if len(lines) < 3:
            errors.append(f"第 {idx} 块格式不完整")
            continue

        # 第一行应该是序号
        if not lines[0].strip().isdigit():
            errors.append(f"第 {idx} 块序号格式错误: {lines[0]}")

        # 第二行应该是时间轴
        if not time_pattern.search(lines[1]):
            errors.append(f"第 {idx} 块时间轴格式错误: {lines[1]}")

    return len(errors) == 0, errors


def check_disk_space(input_path: Path, output_path: Path) -> bool:
    """
    检查磁盘空间是否充足（至少需要输入文件大小的 2 倍）。

    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径

    返回:
        True 如果空间充足
    """
    try:
        input_size = input_path.stat().st_size
        output_dir = output_path.parent

        # 使用 shutil 检查磁盘空间
        import shutil
        disk_usage = shutil.disk_usage(output_dir)
        return disk_usage.free >= input_size * 2
    except (OSError, IOError):
        # 无法检查时默认通过
        return True


# ============================================================
# 输出格式化模块
# ============================================================
def format_video_info_report(video_info: Dict) -> str:
    """
    格式化视频信息报告。

    参数:
        video_info: 视频信息字典

    返回:
        格式化后的报告字符串
    """
    lines = []
    lines.append("=" * 60)
    lines.append("视频信息报告")
    lines.append("=" * 60)

    # 格式信息
    fmt = video_info.get("format", {})
    lines.append(f"文件格式: {fmt.get('format_name', '[需核实:格式]')}")
    lines.append(f"时长: {video_info.get('duration', '[需核实:视频时长]')} 秒")
    lines.append(f"比特率: {video_info.get('bit_rate', '[需核实:比特率]')} bps")

    # 视频流
    lines.append("\n--- 视频流 ---")
    for idx, stream in enumerate(video_info.get("video_streams", []), 1):
        lines.append(f"流 {idx}:")
        lines.append(f"  编码: {stream.get('codec_name', '[需核实:编码]')}")
        lines.append(f"  分辨率: {stream.get('width', '?')}x{stream.get('height', '?')}")
        lines.append(f"  帧率: {stream.get('avg_frame_rate', '[需核实:帧率]')}")

    # 音频流
    lines.append("\n--- 音频流 ---")
    for idx, stream in enumerate(video_info.get("audio_streams", []), 1):
        lines.append(f"流 {idx}:")
        lines.append(f"  编码: {stream.get('codec_name', '[需核实:编码]')}")
        lines.append(f"  采样率: {stream.get('sample_rate', '[需核实:采样率]')} Hz")

    # 字幕流
    lines.append("\n--- 字幕流 ---")
    if video_info.get("subtitle_streams"):
        for idx, stream in enumerate(video_info.get("subtitle_streams", []), 1):
            lang = stream.get("tags", {}).get("language", "[需核实:字幕语言]")
            lines.append(f"流 {idx}: 语言={lang}")
    else:
        lines.append("无字幕流")

    lines.append("=" * 60)
    return "\n".join(lines)


def format_validation_report(is_valid: bool, errors: List[str], file_path: Path) -> str:
    """
    格式化校验报告。

    参数:
        is_valid: 是否通过校验
        errors: 错误列表
        file_path: 校验的文件路径

    返回:
        校验报告字符串
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"校验报告: {file_path}")
    lines.append("=" * 60)

    if is_valid:
        lines.append("✓ 校验通过")
    else:
        lines.append("✗ 校验未通过")
        for err in errors:
            lines.append(f"  - {err}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================
# 主流程模块
# ============================================================
def process_video(video_path: Path, output_path: Path, dry_run: bool = False, verbose: bool = False) -> Dict:
    """
    处理视频：提取字幕或转写。

    参数:
        video_path: 视频文件路径
        output_path: 输出文件路径
        dry_run: 是否只预览不写盘
        verbose: 是否输出详细日志

    返回:
        处理结果字典

    异常:
        VideoToolError: 各种处理错误
    """
    result = {
        "status": "success",
        "video_path": str(video_path),
        "output_path": str(output_path),
        "method": "",
        "details": [],
    }

    # 检查磁盘空间
    if not check_disk_space(video_path, output_path):
        raise VideoToolError("E006", "磁盘空间不足，需要至少输入文件大小的 2 倍空间")

    # 探测视频信息
    if verbose:
        print(f"[INFO] 正在解析视频: {video_path}")

    video_info = probe_video_info(video_path)
    result["video_info"] = video_info

    # 检查是否有字幕流
    if video_info.get("subtitle_streams"):
        result["method"] = "subtitle_extract"
        if verbose:
            print(f"[INFO] 检测到 {len(video_info['subtitle_streams'])} 个字幕流，尝试提取")

        if dry_run:
            result["details"].append(f"[DRY-RUN] 将提取字幕流到: {output_path}")
        else:
            extract_subtitle_stream(video_path, output_path, 0)
            result["details"].append(f"字幕流提取完成: {output_path}")
    else:
        result["method"] = "whisper_transcribe"
        if verbose:
            print("[INFO] 无字幕流，尝试语音转写")

        if dry_run:
            result["details"].append(f"[DRY-RUN] 将进行语音转写到: {output_path}")
        else:
            transcribe_audio(video_path, output_path, "zh")
            result["details"].append(f"语音转写完成: {output_path}")

    # 校验输出
    if not dry_run and output_path.exists():
        srt_content = read_text_file_safe(output_path)
        is_valid, errors = validate_srt_format(srt_content)
        result["validation"] = {"valid": is_valid, "errors": errors}

        if not is_valid:
            result["status"] = "warning"
            result["details"].append("输出文件存在格式问题，请检查")

    return result


def main() -> int:
    """
    主入口函数。

    返回:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="短视频处理工具 - 字幕提取、视频信息识别、结果校验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s video.mp4 -o output.srt          # 提取字幕
  %(prog)s video.mp4 --info                  # 查看视频信息
  %(prog)s video.mp4 --validate output.srt   # 校验字幕文件
  %(prog)s --selftest                        # 运行自检
        """,
    )

    parser.add_argument("input", nargs="?", help="输入视频文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径（默认与输入同目录）")
    parser.add_argument("--info", action="store_true", help="只显示视频信息")
    parser.add_argument("--validate", metavar="SRT_FILE", help="校验 SRT 文件格式")
    parser.add_argument("--dry-run", action="store_true", help="只预览不写盘")
    parser.add_argument("--force", action="store_true", help="实际执行写盘（需配合 --dry-run 使用）")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理日志")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input:
        parser.print_help()
        return 1

    try:
        # 校验输入文件
        input_path = validate_input_file(args.input)

        # 信息模式
        if args.info:
            video_info = probe_video_info(input_path)
            print(format_video_info_report(video_info))
            return 0

        # 校验模式
        if args.validate:
            srt_path = validate_input_file(args.validate)
            srt_content = read_text_file_safe(srt_path)
            is_valid, errors = validate_srt_format(srt_content)
            print(format_validation_report(is_valid, errors, srt_path))
            return 0 if is_valid else 1

        # 处理模式
        output_path = validate_output_path(args.output, input_path)

        # dry-run 控制
        dry = args.dry_run and not args.force

        # 执行处理
        result = process_video(input_path, output_path, dry_run=dry, verbose=args.verbose)

        # 输出结果
        print(f"处理完成: {result['status']}")
        for detail in result["details"]:
            print(f"  {detail}")

        if args.verbose and "video_info" in result:
            print("\n" + format_video_info_report(result["video_info"]))

        return 0

    except VideoToolError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        print(f"错误码: {exc.error_code}", file=sys.stderr)
        print(f"建议: {get_error_suggestion(exc.error_code)}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        print("请报告此问题并附上完整错误信息", file=sys.stderr)
        return 2


def get_error_suggestion(error_code: str) -> str:
    """
    根据错误码返回用户建议。

    参数:
        error_code: 错误码

    返回:
        建议字符串
    """
    suggestions = {
        "E001": "1. 确认文件路径是否正确 2. 检查文件权限",
        "E002": "1. 执行 apt install ffmpeg 或 brew install ffmpeg",
        "E003": "1. 执行 pip install openai-whisper 2. 重新运行",
        "E004": "1. 尝试提取其他字幕流（-map 0:s:1）2. 使用语音识别替代",
        "E005": "1. 查看日志定位错误 2. 重新执行处理",
        "E006": "1. 清理磁盘空间 2. 更换输出目录",
        "E007": "1. 使用 ffmpeg -i input.mp4 -c:v libx264 -c:a aac temp.mp4 转码 2. 重新处理",
        "E008": "1. 检查输入参数格式 2. 确认路径合法性",
        "E009": "1. 检查文件权限 2. 确认文件未被占用",
        "E010": "1. 检查输入数据 2. 报告问题",
    }
    return suggestions.get(error_code, "请参考文档")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    返回:
        0 如果全部通过，否则 1
    """
    print("=" * 60)
    print("短视频处理工具 - 自检模式")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # 测试 1: SRT 时间格式化
    print("\n[测试 1] SRT 时间格式化")
    try:
        assert format_srt_time(0) == "00:00:00,000"
        assert format_srt_time(3661.5) == "01:01:01,500"
        assert format_srt_time(125.34) == "00:02:05,340"
        print("  ✓ SRT 时间格式化正确")
        tests_passed += 1
    except AssertionError as exc:
        print(f"  ✗ 时间格式化失败: {exc}")
        tests_failed += 1

    # 测试 2: SRT 格式校验 - 正确格式
    print("\n[测试 2] SRT 格式校验（正确格式）")
    valid_srt = """1
00:00:01,000 --> 00:00:03,000
你好世界

2
00:00:04,000 --> 00:00:06,000
这是测试字幕
"""
    try:
        is_valid, errors = validate_srt_format(valid_srt)
        assert is_valid, f"正确格式被判定为无效: {errors}"
        assert len(errors) == 0
        print("  ✓ 正确格式通过校验")
        tests_passed += 1
    except AssertionError as exc:
        print(f"  ✗ 正确格式校验失败: {exc}")
        tests_failed += 1

    # 测试 3: SRT 格式校验 - 错误格式
    print("\n[测试 3] SRT 格式校验（错误格式）")
    invalid_srt = """1
错误时间轴
没有时间轴格式
"""
    try:
        is_valid, errors = validate_srt_format(invalid_srt)
        assert not is_valid, "错误格式被判定为有效"
        assert len(errors) > 0, "错误格式未产生错误列表"
        print(f"  ✓ 错误格式被正确识别（{len(errors)} 个错误）")
        tests_passed += 1
    except AssertionError as exc:
        print(f"  ✗ 错误格式校验失败: {exc}")
        tests_failed += 1

    # 测试 4: 空输入处理
    print("\n[测试 4] 空输入处理")
    try:
        is_valid, errors = validate_srt_format("")
        assert not is_valid, "空内容被判定为有效"
        assert len(errors) > 0, "空内容未产生错误"
        print("  ✓ 空输入被正确拒绝")
        tests_passed += 1
    except AssertionError as exc:
        print(f"  ✗ 空输入处理失败: {exc}")
        tests_failed += 1

    # 测试 5: 中文标点处理
    print("\n[测试 5] 中文标点处理")
    chinese_srt = """1
00:00:01,000 --> 00:00:03,000
你好，世界！这是测试。

2
00:00:04,000 --> 00:00:06,000
第二句：包含中文标点。
"""
    try:
        is_valid, errors = validate_srt_format(chinese_srt)
        assert is_valid, f"中文标点 SRT 被判定为无效: {errors}"
        print("  ✓ 中文标点 SRT 通过校验")
        tests_passed += 1
    except AssertionError as exc:
        print(f"  ✗ 中文标点处理失败: {exc}")
        tests_failed += 1

    # 测试 6: 文件读写（临时文件）
    print("\n[测试 6] 文件读写")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False, encoding="utf-8") as tmp:
            tmp.write(valid_srt)
            tmp_path = Path(tmp.name)

        content = read_text_file_safe(tmp_path)
        assert content == valid_srt, "读取内容与写入不一致"
        print("  ✓ 文件读写正常")
        tests_passed += 1

        # 清理
        tmp_path.unlink()
    except Exception as exc:
        print(f"  ✗ 文件读写失败: {exc}")
        tests_failed += 1

    # 测试 7: 输入校验
    print("\n[测试 7] 输入校验")
    try:
        # 不存在的文件
        try:
            validate_input_file("/nonexistent/path/file.mp4")
            print("  ✗ 不存在的文件未被拒绝")
            tests_failed += 1
        except VideoToolError as exc:
            assert exc.error_code == "E001", f"错误码应为 E001，实际为 {exc.error_code}"
            print("  ✓ 不存在的文件被正确拒绝 (E001)")
            tests_passed += 1

        # 空路径
        try:
            validate_input_file("")
            print("  ✗ 空路径未被拒绝")
            tests_failed += 1
        except VideoToolError as exc:
            assert exc.error_code == "E008", f"错误码应为 E008，实际为 {exc.error_code}"
            print("  ✓ 空路径被正确拒绝 (E008)")
            tests_passed += 1

    except Exception as exc:
        print(f"  ✗ 输入校验测试异常: {exc}")
        tests_failed += 1

    # 测试 8: 错误码完整性
    print("\n[测试 8] 错误码完整性")
    try:
        expected_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
        for code in expected_codes:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert ERROR_CODES[code], f"错误码 {code} 描述为空"
        print(f"  ✓ 全部 {len(expected_codes)} 个错误码已定义")
        tests_passed += 1
    except AssertionError as exc:
        print(f"  ✗ 错误码完整性检查失败: {exc}")
        tests_failed += 1

    # 测试 9: 超长输入处理
    print("\n[测试 9] 超长输入处理")
    try:
        long_srt = []
        for i in range(1, 1001):
            start = i * 2
            end = start + 1
            long_srt.append(f"{i}\n{format_srt_time(start)} --> {format_srt_time(end)}\n测试字幕第{i}行\n")

        long_content = "\n".join(long_srt)
        is_valid, errors = validate_srt_format(long_content)
        assert is_valid, f"超长 SRT 校验失败: {len(errors)} 个错误"
        print(f"  ✓ 超长 SRT（{len(long_srt)} 块）通过校验")
        tests_passed += 1
    except AssertionError as exc:
        print(f"  ✗ 超长输入处理失败: {exc}")
        tests_failed += 1

    # 测试 10: 编码异常处理
    print("\n[测试 10] 编码异常处理")
    try:
        # 创建 GBK 编码文件
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".srt", delete=False) as tmp:
            gbk_content = "1\n00:00:01,000 --> 00:00:03,000\n测试字幕\n".encode("gbk")
            tmp.write(gbk_content)
            tmp_path = Path(tmp.name)

        content = read_text_file_safe(tmp_path)
        assert "测试字幕" in content, "GBK 内容读取失败"
        print("  ✓ GBK 编码文件正确读取")
        tests_passed += 1

        tmp_path.unlink()
    except Exception as exc:
        print(f"  ✗ 编码异常处理失败: {exc}")
        tests_failed += 1

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)

    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
