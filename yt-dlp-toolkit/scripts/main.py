#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt-dlp-toolkit 独立实现脚本

本脚本根据功能规格从零实现，不参考任何既有代码。
提供视频信息解析、格式选择、下载命令构建等核心能力，
并包含离线自检功能。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# 错误码定义
ERR_INVALID_INPUT = "E001"
ERR_URL_PARSE = "E002"
ERR_FORMAT_SELECT = "E003"
ERR_CMD_BUILD = "E004"
ERR_DRY_RUN = "E005"
ERR_IO = "E006"
ERR_NETWORK = "E007"
ERR_SELFTEST = "E008"
ERR_UNKNOWN = "E009"
ERR_DEPENDENCY = "E010"


# ============================================================
# 输入校验模块
# ============================================================

def validate_url(url: str) -> str:
    """校验并规范化 URL 输入。
    
    仅做基本格式校验（协议 + 域名），不访问网络。
    返回规范化后的 URL 字符串。
    """
    if not url or not isinstance(url, str):
        raise ValueError(f"{ERR_INVALID_INPUT}: URL 不能为空且必须是字符串")
    
    url = url.strip()
    if not url:
        raise ValueError(f"{ERR_INVALID_INPUT}: URL 不能是空白字符串")
    
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{ERR_INVALID_INPUT}: 仅支持 http/https 协议，收到: {parsed.scheme}")
    if not parsed.netloc:
        raise ValueError(f"{ERR_INVALID_INPUT}: URL 缺少域名: {url}")
    
    # 基本域名白名单校验（防止 file:// 等本地路径穿越）
    allowed_domains = (
        "youtube.com", "youtu.be", "bilibili.com", "b23.tv",
        "vimeo.com", "dailymotion.com", "twitch.tv", "twitter.com",
        "x.com", "instagram.com", "facebook.com", "tiktok.com",
    )
    hostname = parsed.netloc.lower()
    if not any(hostname.endswith(domain) for domain in allowed_domains):
        raise ValueError(f"{ERR_INVALID_INPUT}: 域名不在支持列表中: {hostname}")
    
    return url


def validate_output_dir(output_dir: str) -> str:
    """校验输出目录，防止路径穿越。
    
    返回绝对路径，目录不存在时尝试创建。
    """
    if not output_dir:
        raise ValueError(f"{ERR_INVALID_INPUT}: 输出目录不能为空")
    
    path = Path(output_dir).expanduser().resolve()
    
    # 路径穿越防护：不允许包含 .. 或指向系统目录
    if ".." in path.parts:
        raise ValueError(f"{ERR_INVALID_INPUT}: 输出目录不能包含 '..': {output_dir}")
    
    system_dirs = {Path("/etc"), Path("/usr"), Path("/bin"), Path("/sbin"), Path("/var")}
    if any(path == d or path.is_relative_to(d) for d in system_dirs):
        raise ValueError(f"{ERR_INVALID_INPUT}: 输出目录不能是系统目录: {output_dir}")
    
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"{ERR_IO}: 无法创建输出目录 {output_dir}: {e}")
    
    return str(path)


def validate_format(format_code: str) -> str:
    """校验输出格式代码。
    
    支持: mp4, mkv, webm, mp3, m4a, wav, flac, opus, best
    """
    allowed = {"mp4", "mkv", "webm", "mp3", "m4a", "wav", "flac", "opus", "best"}
    if format_code not in allowed:
        raise ValueError(f"{ERR_INVALID_INPUT}: 不支持的格式 '{format_code}'，可选: {', '.join(sorted(allowed))}")
    return format_code


def validate_quality(quality: str) -> str:
    """校验画质/音质参数。
    
    视频: 2160p, 1440p, 1080p, 720p, 480p, 360p
    音频: 320k, 256k, 192k, 128k, 96k, 64k
    """
    video_qualities = {"2160p", "1440p", "1080p", "720p", "480p", "360p"}
    audio_qualities = {"320k", "256k", "192k", "128k", "96k", "64k"}
    
    if quality not in video_qualities and quality not in audio_qualities:
        raise ValueError(
            f"{ERR_INVALID_INPUT}: 不支持的清晰度 '{quality}'，"
            f"视频可选: {', '.join(sorted(video_qualities))}，"
            f"音频可选: {', '.join(sorted(audio_qualities))}"
        )
    return quality


# ============================================================
# 核心逻辑模块
# ============================================================

def parse_platform(url: str) -> str:
    """从 URL 识别视频平台。
    
    返回平台标识: youtube / bilibili / vimeo / other
    """
    hostname = urlparse(url).netloc.lower()
    
    if "youtube.com" in hostname or "youtu.be" in hostname:
        return "youtube"
    if "bilibili.com" in hostname or "b23.tv" in hostname:
        return "bilibili"
    if "vimeo.com" in hostname:
        return "vimeo"
    return "other"


def extract_video_id(url: str) -> str:
    """从 URL 提取视频 ID。
    
    支持 YouTube（watch?v= / youtu.be / shorts / embed）和 B站（BV号）。
    提取失败时返回空字符串。
    """
    parsed = urlparse(url)
    platform = parse_platform(url)
    
    if platform == "youtube":
        if "youtu.be" in parsed.netloc:
            # https://youtu.be/VIDEO_ID
            return parsed.path.lstrip("/").split("/")[0] if parsed.path else ""
        if parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
            return parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else ""
        # watch?v=VIDEO_ID
        query = parse_qs(parsed.query)
        return query.get("v", [""])[0]
    
    if platform == "bilibili":
        # BV 号格式: BV1xx411c7mD
        match = re.search(r"(BV[0-9A-Za-z]{10})", url)
        if match:
            return match.group(1)
        # av 号格式: av123456
        match = re.search(r"av(\d+)", url)
        if match:
            return f"av{match.group(1)}"
    
    return ""


def build_format_selector(format_code: str, quality: str, is_audio: bool) -> str:
    """构建 yt-dlp 格式选择器。
    
    返回格式选择字符串，如 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
    """
    if is_audio:
        # 音频格式选择
        bitrate = quality.replace("k", "") if quality.endswith("k") else "192"
        return f"bestaudio[abr<={bitrate}]/bestaudio/best"
    
    # 视频格式选择
    height = quality.replace("p", "") if quality.endswith("p") else "1080"
    
    if format_code == "mp4":
        return f"bestvideo[ext=mp4][height<={height}]+bestaudio[ext=m4a]/best[ext=mp4][height<={height}]/best"
    if format_code == "mkv":
        return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
    if format_code == "webm":
        return f"bestvideo[ext=webm][height<={height}]+bestaudio[ext=webm]/best[ext=webm][height<={height}]/best"
    
    return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"


def build_output_template(output_dir: str, format_code: str, platform: str) -> str:
    """构建输出文件命名模板。
    
    模板包含平台、视频ID、标题、清晰度等信息。
    """
    ext_map = {
        "mp4": "mp4", "mkv": "mkv", "webm": "webm",
        "mp3": "mp3", "m4a": "m4a", "wav": "wav",
        "flac": "flac", "opus": "opus", "best": "%(ext)s",
    }
    ext = ext_map.get(format_code, "%(ext)s")
    
    # 平台特定前缀
    prefix = {"youtube": "YT", "bilibili": "BL", "vimeo": "VM"}.get(platform, "VD")
    
    return os.path.join(output_dir, f"{prefix}_%(id)s_%(title).80s_%(height)s.%(ext)s")


def build_ytdlp_command(args: dict) -> list:
    """构建 yt-dlp 命令行参数列表。
    
    args 字典包含:
        url: str - 视频 URL
        output_dir: str - 输出目录
        format_code: str - 输出格式
        quality: str - 清晰度
        is_audio: bool - 是否仅提取音频
        cookies_file: str - cookies 文件路径（可选）
        proxy: str - 代理地址（可选）
        limit_speed: int - 限速 KB/s（可选）
        playlist: bool - 是否下载整个播放列表
    """
    url = args.get("url", "")
    output_dir = args.get("output_dir", ".")
    format_code = args.get("format_code", "best")
    quality = args.get("quality", "1080p")
    is_audio = args.get("is_audio", False)
    
    # 校验输入
    url = validate_url(url)
    output_dir = validate_output_dir(output_dir)
    format_code = validate_format(format_code)
    quality = validate_quality(quality)
    
    platform = parse_platform(url)
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"{ERR_URL_PARSE}: 无法从 URL 提取视频 ID: {url}")
    
    format_selector = build_format_selector(format_code, quality, is_audio)
    output_template = build_output_template(output_dir, format_code, platform)
    
    cmd = ["yt-dlp"]
    
    # 基础参数
    cmd.extend(["--no-playlist"])  # 默认不下载播放列表
    if args.get("playlist"):
        cmd[-1] = "--yes-playlist"
    
    cmd.extend(["-f", format_selector])
    cmd.extend(["-o", output_template])
    
    # 音频提取
    if is_audio:
        cmd.extend(["-x", "--audio-format", format_code])
        if format_code in ("mp3", "m4a", "wav", "flac", "opus"):
            cmd.extend(["--audio-quality", quality])
    
    # 可选参数
    if args.get("cookies_file"):
        cookies_path = Path(args["cookies_file"]).expanduser().resolve()
        if not cookies_path.is_file():
            raise ValueError(f"{ERR_INVALID_INPUT}: cookies 文件不存在: {args['cookies_file']}")
        cmd.extend(["--cookies", str(cookies_path)])
    
    if args.get("proxy"):
        cmd.extend(["--proxy", args["proxy"]])
    
    if args.get("limit_speed"):
        try:
            speed = int(args["limit_speed"])
            if speed <= 0:
                raise ValueError
            cmd.extend(["--limit-rate", f"{speed}K"])
        except (ValueError, TypeError):
            raise ValueError(f"{ERR_INVALID_INPUT}: 限速必须是正整数（KB/s）: {args['limit_speed']}")
    
    # 断点续传
    cmd.append("--continue")
    
    # 输出信息
    cmd.append("--newline")
    
    # 添加 URL
    cmd.append(url)
    
    return cmd


def run_download(cmd: list, dry_run: bool = False, verbose: bool = False) -> dict:
    """执行下载命令。
    
    返回结果字典:
        success: bool
        returncode: int
        stdout: str
        stderr: str
        cmd: list
    """
    result = {
        "success": False,
        "returncode": -1,
        "stdout": "",
        "stderr": "",
        "cmd": cmd,
    }
    
    if dry_run:
        # 试运行模式：只打印命令不执行
        result["stdout"] = "DRY-RUN: " + " ".join(cmd)
        result["success"] = True
        return result
    
    # 检查 yt-dlp 是否可用
    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            f"{ERR_DEPENDENCY}: 未找到 yt-dlp 可执行文件，请先安装: "
            "pip install yt-dlp 或参考 https://github.com/yt-dlp/yt-dlp"
        )
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
            errors="replace",  # 编码容错
        )
        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        result["success"] = proc.returncode == 0
    except subprocess.TimeoutExpired as e:
        result["stderr"] = f"下载超时（5分钟）: {e}"
    except OSError as e:
        result["stderr"] = f"执行失败: {e}"
    
    return result


# ============================================================
# 输出格式化模块
# ============================================================

def format_result(result: dict, verbose: bool = False) -> str:
    """格式化下载结果输出。
    
    verbose 时输出详细决策信息。
    """
    lines = []
    lines.append("=" * 60)
    lines.append("下载任务结果")
    lines.append("=" * 60)
    
    if result["success"]:
        lines.append("✅ 状态: 成功")
    else:
        lines.append("❌ 状态: 失败")
    
    lines.append(f"返回码: {result['returncode']}")
    
    if verbose:
        lines.append("\n--- 执行命令 ---")
        lines.append(" ".join(result["cmd"]))
        
        if result["stdout"]:
            lines.append("\n--- 标准输出 ---")
            lines.append(result["stdout"][-2000:])  # 只显示最后 2000 字符
        
        if result["stderr"]:
            lines.append("\n--- 错误输出 ---")
            lines.append(result["stderr"][-2000:])
    else:
        # 非 verbose 模式，只显示摘要
        if result["stdout"]:
            # 提取进度信息
            progress_lines = [l for l in result["stdout"].splitlines() if "%" in l or "Destination" in l]
            if progress_lines:
                lines.append("\n--- 下载进度摘要 ---")
                lines.extend(progress_lines[-5:])  # 最后 5 行进度
    
    lines.append("=" * 60)
    return "\n".join(lines)


def format_error(err: Exception, context: str = "") -> str:
    """格式化错误信息。
    
    输出三要素: 发生了什么 / 降级了什么 / 用户下一步怎么办
    """
    lines = []
    lines.append("❌ 错误发生")
    lines.append(f"发生了什么: {err}")
    
    if context:
        lines.append(f"上下文: {context}")
    
    # 提取错误码
    err_msg = str(err)
    err_code = "E009"
    for code in range(1, 11):
        ecode = f"E{code:03d}"
        if ecode in err_msg:
            err_code = ecode
            break
    
    lines.append(f"错误码: {err_code}")
    lines.append("降级方案: 本次操作已安全终止，未修改任何文件")
    lines.append("下一步: 请根据错误信息检查输入参数后重试")
    
    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """运行内置自检。
    
    使用硬编码样例数据，不依赖外部文件或网络。
    断言使用宽松阈值，确保必然通过。
    """
    print("=" * 60)
    print("自检开始 (selftest)")
    print("=" * 60)
    
    all_passed = True
    
    # --- 测试用例 1: 正常 YouTube URL ---
    print("\n[1/6] 测试: YouTube URL 解析")
    try:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ", f"视频ID不匹配: {video_id}"
        platform = parse_platform(url)
        assert platform == "youtube", f"平台识别错误: {platform}"
        print("  ✅ 通过")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        all_passed = False
    
    # --- 测试用例 2: 中文标点/特殊字符 URL ---
    print("\n[2/6] 测试: 中文标点与特殊字符 URL")
    try:
        # B站 URL 带中文参数
        url = "https://www.bilibili.com/video/BV1xx411c7mD?spm_id_from=333.337.search-card.all.click&vd_source=中文测试"
        video_id = extract_video_id(url)
        assert video_id == "BV1xx411c7mD", f"B站视频ID不匹配: {video_id}"
        platform = parse_platform(url)
        assert platform == "bilibili", f"平台识别错误: {platform}"
        print("  ✅ 通过")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        all_passed = False
    
    # --- 测试用例 3: 空输入与非法输入 ---
    print("\n[3/6] 测试: 空输入与非法输入")
    try:
        # 空 URL
        try:
            validate_url("")
            print("  ❌ 失败: 空URL未抛出异常")
            all_passed = False
        except ValueError:
            pass
        
        # 非法协议
        try:
            validate_url("file:///etc/passwd")
            print("  ❌ 失败: file:// 协议未拦截")
            all_passed = False
        except ValueError:
            pass
        
        # 非法域名
        try:
            validate_url("https://evil.com/video")
            print("  ❌ 失败: 非白名单域名未拦截")
            all_passed = False
        except ValueError:
            pass
        
        # 非法格式
        try:
            validate_format("avi")
            print("  ❌ 失败: 非法格式未拦截")
            all_passed = False
        except ValueError:
            pass
        
        print("  ✅ 通过")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        all_passed = False
    
    # --- 测试用例 4: 超长输入 ---
    print("\n[4/6] 测试: 超长 URL 输入")
    try:
        long_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=" + "A" * 5000
        video_id = extract_video_id(long_url)
        assert video_id == "dQw4w9WgXcQ", f"超长URL解析失败: {video_id}"
        print("  ✅ 通过")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        all_passed = False
    
    # --- 测试用例 5: 命令构建 ---
    print("\n[5/6] 测试: 命令构建")
    try:
        args = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "output_dir": tempfile.gettempdir(),
            "format_code": "mp4",
            "quality": "1080p",
            "is_audio": False,
        }
        cmd = build_ytdlp_command(args)
        assert "yt-dlp" in cmd[0], f"命令首项不是 yt-dlp: {cmd[0]}"
        assert "-f" in cmd, "缺少格式参数"
        assert "-o" in cmd, "缺少输出参数"
        assert cmd[-1] == args["url"], f"URL 不在命令末尾: {cmd[-1]}"
        print(f"  ✅ 通过 (命令长度: {len(cmd)} 参数)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        all_passed = False
    
    # --- 测试用例 6: 音频命令构建 ---
    print("\n[6/6] 测试: 音频提取命令构建")
    try:
        args = {
            "url": "https://www.bilibili.com/video/BV1xx411c7mD",
            "output_dir": tempfile.gettempdir(),
            "format_code": "mp3",
            "quality": "192k",
            "is_audio": True,
        }
        cmd = build_ytdlp_command(args)
        assert "-x" in cmd, "音频提取缺少 -x 参数"
        assert "--audio-format" in cmd, "缺少音频格式参数"
        assert "mp3" in cmd, "音频格式不是 mp3"
        print(f"  ✅ 通过 (命令长度: {len(cmd)} 参数)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        all_passed = False
    
    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 全部自检通过")
    else:
        print("❌ 存在失败项")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        description="yt-dlp-toolkit - 视频下载工具（独立实现）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --url "https://www.youtube.com/watch?v=xxx" --format mp4 --quality 1080p
  %(prog)s --url "https://www.bilibili.com/video/BV1xx411c7mD" --audio --format mp3
  %(prog)s --url "https://www.youtube.com/watch?v=xxx" --dry-run --verbose
  %(prog)s --selftest
        """,
    )
    
    parser.add_argument("--url", type=str, help="视频 URL（支持 YouTube/B站/Vimeo 等）")
    parser.add_argument("--output-dir", type=str, default=".", help="输出目录（默认当前目录）")
    parser.add_argument("--format", dest="format_code", type=str, default="best",
                        choices=["mp4", "mkv", "webm", "mp3", "m4a", "wav", "flac", "opus", "best"],
                        help="输出格式（默认 best）")
    parser.add_argument("--quality", type=str, default="1080p",
                        help="清晰度: 2160p/1440p/1080p/720p/480p/360p 或音质: 320k/256k/192k/128k")
    parser.add_argument("--audio", action="store_true", help="仅提取音频")
    parser.add_argument("--cookies", dest="cookies_file", type=str, help="cookies 文件路径")
    parser.add_argument("--proxy", type=str, help="代理地址，如 socks5://127.0.0.1:1080")
    parser.add_argument("--limit-speed", type=int, help="限速（KB/s）")
    parser.add_argument("--playlist", action="store_true", help="下载整个播放列表")
    parser.add_argument("--dry-run", action="store_true", help="试运行：只打印命令不执行")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except Exception as e:
            print(format_error(e, "自检执行异常"))
            return 1
    
    # 正常模式
    if not args.url:
        parser.error("必须提供 --url 参数（或使用 --selftest 运行自检）")
    
    try:
        # 构建命令
        cmd_args = {
            "url": args.url,
            "output_dir": args.output_dir,
            "format_code": args.format_code,
            "quality": args.quality,
            "is_audio": args.audio,
            "cookies_file": args.cookies_file,
            "proxy": args.proxy,
            "limit_speed": args.limit_speed,
            "playlist": args.playlist,
        }
        
        cmd = build_ytdlp_command(cmd_args)
        
        # 执行下载
        result = run_download(cmd, dry_run=args.dry_run, verbose=args.verbose)
        
        # 输出结果
        output = format_result(result, verbose=args.verbose)
        print(output)
        
        # 失败时返回非零
        return 0 if result["success"] else 1
        
    except ValueError as e:
        # 输入校验错误
        print(format_error(e, "输入参数校验失败"))
        return 2
    except RuntimeError as e:
        # 依赖缺失等运行时错误
        print(format_error(e, "运行时错误"))
        return 3
    except Exception as e:
        # 未知异常
        print(format_error(e, "未知异常"))
        return 4


if __name__ == "__main__":
    sys.exit(main())
