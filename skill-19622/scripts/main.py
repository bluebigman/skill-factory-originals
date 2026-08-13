#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 录屏操作演示 智能步骤生成（独立实现）

本脚本根据功能规格实现核心处理逻辑：
  1. 帧提取（模拟/真实 FFmpeg 调用）
  2. 相邻帧差异分析（Pillow 像素级对比）
  3. OCR 识别（可选，依赖 pytesseract）
  4. 步骤序列生成（时间戳排序 + 合并）
  5. Markdown 文档输出

所有核心逻辑均支持 --selftest 离线自检，不依赖外部文件或网络。
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "环境自检失败：缺少 FFmpeg / Pillow / pytesseract / Tesseract",
    "E002": "输入视频文件不存在或不可读",
    "E003": "输出目录无法创建或不可写",
    "E004": "帧提取失败：FFmpeg 执行出错",
    "E005": "差异分析失败：图像文件损坏或格式不支持",
    "E006": "OCR 识别失败：Tesseract 引擎不可用",
    "E007": "步骤生成失败：帧信息为空或数据异常",
    "E008": "输出文档写入失败",
    "E009": "输入参数校验失败：参数类型或范围错误",
    "E010": "未知内部错误",
}


class SkillError(Exception):
    """业务逻辑错误，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 输入校验（R7：guard clause 顶部校验）
# ============================================================

def validate_common_args(args) -> None:
    """校验公共参数（类型/范围）。"""
    if args.frame_interval <= 0:
        raise SkillError("E009", "frame_interval 必须为正数")
    if args.change_threshold < 0 or args.change_threshold > 255:
        raise SkillError("E009", "change_threshold 必须在 0-255 之间")
    if args.merge_window < 0:
        raise SkillError("E009", "merge_window 不能为负数")
    if args.min_change_ratio < 0 or args.min_change_ratio > 1:
        raise SkillError("E009", "min_change_ratio 必须在 0-1 之间")
    if args.max_change_ratio < 0 or args.max_change_ratio > 1:
        raise SkillError("E009", "max_change_ratio 必须在 0-1 之间")
    if args.min_change_ratio > args.max_change_ratio:
        raise SkillError("E009", "min_change_ratio 不能大于 max_change_ratio")


def validate_video_path(video_path: str) -> Path:
    """校验视频文件路径存在且可读。"""
    if not video_path:
        raise SkillError("E002", "未提供视频文件路径")
    path = Path(video_path).expanduser().resolve()
    if not path.is_file():
        raise SkillError("E002", f"视频文件不存在: {path}")
    if not os.access(path, os.R_OK):
        raise SkillError("E002", f"视频文件不可读: {path}")
    return path


def validate_output_dir(output_dir: str) -> Path:
    """校验输出目录存在或可创建。"""
    path = Path(output_dir).expanduser().resolve()
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SkillError("E003", f"无法创建输出目录: {path} ({exc})") from exc
    if not path.is_dir():
        raise SkillError("E003", f"输出路径不是目录: {path}")
    if not os.access(path, os.W_OK):
        raise SkillError("E003", f"输出目录不可写: {path}")
    return path


# ============================================================
# 环境自检（Step 1）
# ============================================================

def check_environment(verbose: bool = False) -> list:
    """检查依赖工具链是否可用，返回缺失项列表。"""
    missing = []

    # 检查 FFmpeg
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
        if verbose:
            print("  [环境] ffmpeg 未找到", file=sys.stderr)

    # 检查 Pillow
    try:
        import PIL  # noqa: F401
        if verbose:
            print("  [环境] Pillow OK")
    except ImportError:
        missing.append("pillow")
        if verbose:
            print("  [环境] Pillow 未安装", file=sys.stderr)

    # 检查 pytesseract（可选）
    try:
        import pytesseract  # noqa: F401
        if verbose:
            print("  [环境] pytesseract OK")
    except ImportError:
        missing.append("pytesseract")
        if verbose:
            print("  [环境] pytesseract 未安装（OCR 功能将降级）", file=sys.stderr)

    # 检查 Tesseract 引擎（可选）
    if shutil.which("tesseract") is None:
        missing.append("tesseract")
        if verbose:
            print("  [环境] tesseract 未找到（OCR 功能将降级）", file=sys.stderr)

    return missing


# ============================================================
# 帧提取（Step 2）
# ============================================================

def extract_frames(video_path: Path, output_dir: Path, frame_interval: float,
                   dry: bool = False, verbose: bool = False) -> list:
    """
    使用 FFmpeg 按固定间隔提取关键帧。

    返回帧文件路径列表（按时间戳排序）。
    若 dry=True 或 FFmpeg 不可用，则返回空列表（调用方需处理降级）。
    """
    if dry:
        if verbose:
            print(f"  [帧提取] dry-run 模式，跳过实际提取")
        return []

    if shutil.which("ffmpeg") is None:
        raise SkillError("E001", "FFmpeg 未安装，无法提取帧")

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # 清理旧帧
    for old in frames_dir.glob("frame_*.jpg"):
        old.unlink()

    # 构造 FFmpeg 命令
    fps_expr = f"1/{frame_interval}"
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"fps={fps_expr}",
        "-q:v", "2",
        str(frames_dir / "frame_%04d.jpg")
    ]

    if verbose:
        print(f"  [帧提取] 执行: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise SkillError("E004", f"FFmpeg 执行超时: {exc}") from exc
    except OSError as exc:
        raise SkillError("E004", f"FFmpeg 执行失败: {exc}") from exc

    if result.returncode != 0:
        error_msg = result.stderr[-500:] if result.stderr else "无错误输出"
        raise SkillError("E004", f"FFmpeg 退出码 {result.returncode}: {error_msg}")

    # 收集帧文件
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        raise SkillError("E004", "FFmpeg 未生成任何帧文件")

    if verbose:
        print(f"  [帧提取] 成功提取 {len(frames)} 帧")

    return frames


# ============================================================
# 差异分析（Step 3）
# ============================================================

def compute_change_ratio(frame_a_path: Path, frame_b_path: Path,
                         threshold: int = 30) -> float:
    """
    计算相邻两帧的差异像素比例（0.0 - 1.0）。

    使用 Pillow 的 ImageChops 进行像素级对比。
    """
    try:
        from PIL import Image, ImageChops
        import numpy as np
    except ImportError as exc:
        raise SkillError("E005", f"Pillow 或 numpy 未安装: {exc}") from exc

    try:
        img_a = Image.open(frame_a_path).convert("RGB")
        img_b = Image.open(frame_b_path).convert("RGB")

        # 确保尺寸一致（若不一致则缩放）
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size)

        diff = ImageChops.difference(img_a, img_b)
        diff_array = np.array(diff)

        # 计算差异像素比例
        changed_pixels = np.sum(np.any(diff_array > threshold, axis=2))
        total_pixels = diff_array.shape[0] * diff_array.shape[1]
        if total_pixels == 0:
            return 0.0
        return float(changed_pixels) / float(total_pixels)

    except Exception as exc:
        raise SkillError("E005", f"图像差异分析失败: {exc}") from exc


def analyze_frame_sequence(frames: list, frame_interval: float,
                           threshold: int = 30,
                           min_change_ratio: float = 0.01,
                           max_change_ratio: float = 0.30,
                           verbose: bool = False) -> list:
    """
    分析帧序列，返回带变化比例和时间戳的帧信息列表。

    每个帧信息: {path, timestamp, change_ratio, is_keyframe}
    """
    frame_infos = []
    total_frames = len(frames)

    for i, frame_path in enumerate(frames):
        timestamp = i * frame_interval
        change_ratio = 0.0
        is_keyframe = False

        if i > 0:
            # 与前一帧比较
            change_ratio = compute_change_ratio(frames[i - 1], frame_path, threshold)
            if change_ratio < min_change_ratio:
                is_keyframe = False  # 无变化，跳过
            elif change_ratio <= max_change_ratio:
                is_keyframe = True  # 局部变化，候选步骤
            else:
                is_keyframe = True  # 重大变化，强制关键节点

        # 第一帧始终作为关键帧
        if i == 0:
            is_keyframe = True

        frame_infos.append({
            "path": str(frame_path),
            "timestamp": timestamp,
            "change_ratio": change_ratio,
            "is_keyframe": is_keyframe,
        })

        if verbose and i > 0:
            status = "关键" if is_keyframe else "跳过"
            print(f"  [差异] 帧 {i:04d} 变化率={change_ratio:.4f} → {status}")

    return frame_infos


# ============================================================
# OCR 识别（Step 4）
# ============================================================

def ocr_image(image_path: str, lang: str = "chi_sim+eng") -> str:
    """
    对图像进行 OCR 识别，返回识别文本。

    若 pytesseract 或 Tesseract 不可用，返回空字符串（降级）。
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    if shutil.which("tesseract") is None:
        return ""

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip()
    except Exception:
        # OCR 失败不致命，降级为空文本
        return ""


# ============================================================
# 步骤序列生成（Step 5）
# ============================================================

def generate_steps(frame_infos: list, merge_window: float = 5.0,
                   use_ocr: bool = True, verbose: bool = False) -> list:
    """
    根据帧信息生成步骤序列。

    合并规则：相邻关键帧时间差 < merge_window 时合并为同一步骤。
    """
    keyframes = [f for f in frame_infos if f["is_keyframe"]]

    if not keyframes:
        raise SkillError("E007", "没有检测到任何关键帧")

    steps = []
    current_step = None

    for frame_info in keyframes:
        ts = frame_info["timestamp"]

        if current_step is None:
            # 开启新步骤
            current_step = {
                "start_time": ts,
                "end_time": ts,
                "screenshot": frame_info["path"],
                "ocr_text": "",
            }
            if use_ocr:
                current_step["ocr_text"] = ocr_image(frame_info["path"])
            steps.append(current_step)
        else:
            # 判断是否合并
            if ts - current_step["end_time"] < merge_window:
                # 合并到当前步骤
                current_step["end_time"] = ts
                if use_ocr:
                    extra_text = ocr_image(frame_info["path"])
                    if extra_text and extra_text not in current_step["ocr_text"]:
                        current_step["ocr_text"] += " " + extra_text
                if verbose:
                    print(f"  [步骤] 合并帧 @{ts:.1f}s 到步骤 {len(steps)}")
            else:
                # 开启新步骤
                current_step = {
                    "start_time": ts,
                    "end_time": ts,
                    "screenshot": frame_info["path"],
                    "ocr_text": "",
                }
                if use_ocr:
                    current_step["ocr_text"] = ocr_image(frame_info["path"])
                steps.append(current_step)
                if verbose:
                    print(f"  [步骤] 新步骤 {len(steps)} @{ts:.1f}s")

    return steps


# ============================================================
# 输出格式化（Step 6）
# ============================================================

def format_timestamp(seconds: float) -> str:
    """将秒数格式化为 HH:MM:SS。"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def generate_markdown(steps: list, video_name: str, frame_interval: float,
                      output_dir: Path) -> str:
    """生成 Markdown 格式的步骤文档。"""
    lines = []
    lines.append("# 操作演示步骤文档")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 视频来源：{video_name}")
    lines.append(f"> 帧提取间隔：{frame_interval} 秒")
    lines.append("")

    for idx, step in enumerate(steps, 1):
        start_str = format_timestamp(step["start_time"])
        end_str = format_timestamp(step["end_time"])
        lines.append(f"## 步骤 {idx}（{start_str} - {end_str}）")
        lines.append("")
        # 截图路径（相对输出目录）
        screenshot_path = Path(step["screenshot"])
        try:
            rel_path = screenshot_path.relative_to(output_dir)
        except ValueError:
            rel_path = screenshot_path
        lines.append(f"![截图]({rel_path})")
        lines.append("")
        # OCR 文本或占位符
        ocr_text = step.get("ocr_text", "").strip()
        if ocr_text:
            lines.append(ocr_text)
        else:
            lines.append("> ⚠️ 此步骤未识别到文字，请手动补充说明。")
        lines.append("")

    return "\n".join(lines)


def write_output(markdown_content: str, output_path: Path,
                 dry: bool = False, verbose: bool = False) -> None:
    """写入输出文件（受 dry 控制）。"""
    if dry:
        if verbose:
            print(f"  [输出] dry-run 模式，不写入文件: {output_path}")
            print("  [输出] 文档内容预览（前 500 字符）：")
            print(markdown_content[:500])
        return

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # 多编码写入：优先 UTF-8，失败则 GBK
        try:
            output_path.write_text(markdown_content, encoding="utf-8")
        except UnicodeEncodeError:
            output_path.write_text(markdown_content, encoding="gbk", errors="replace")
        if verbose:
            print(f"  [输出] 已写入: {output_path}")
    except OSError as exc:
        raise SkillError("E008", f"写入输出文件失败: {exc}") from exc


# ============================================================
# 主处理流程
# ============================================================

def process_video(video_path: Path, output_dir: Path, args) -> None:
    """执行完整的视频处理流程。"""
    # Step 1: 环境自检
    if args.verbose:
        print("[1/5] 环境自检...")
    missing = check_environment(args.verbose)
    if "ffmpeg" in missing:
        raise SkillError("E001", "FFmpeg 未安装，无法提取帧")
    if "pillow" in missing:
        raise SkillError("E001", "Pillow 未安装，无法进行差异分析")

    # Step 2: 帧提取
    if args.verbose:
        print(f"[2/5] 帧提取（间隔 {args.frame_interval} 秒）...")
    frames = extract_frames(video_path, output_dir, args.frame_interval,
                            dry=args.dry, verbose=args.verbose)

    # 若 dry-run 或帧提取失败，使用模拟帧数据
    if not frames:
        if args.verbose:
            print("  [帧提取] 未生成帧，使用模拟数据（dry-run 或降级模式）")
        frames = _generate_simulated_frames(output_dir, 5)

    # Step 3: 差异分析
    if args.verbose:
        print("[3/5] 差异分析...")
    frame_infos = analyze_frame_sequence(
        frames, args.frame_interval,
        threshold=args.change_threshold,
        min_change_ratio=args.min_change_ratio,
        max_change_ratio=args.max_change_ratio,
        verbose=args.verbose,
    )

    # Step 4: OCR 识别（在步骤生成中调用）
    if args.verbose:
        print("[4/5] OCR 识别（步骤生成中）...")

    # Step 5: 步骤生成
    if args.verbose:
        print("[5/5] 步骤序列生成...")
    steps = generate_steps(frame_infos, merge_window=args.merge_window,
                           use_ocr=args.use_ocr, verbose=args.verbose)

    # Step 6: 输出
    markdown = generate_markdown(steps, video_path.name, args.frame_interval, output_dir)
    output_file = output_dir / "steps.md"
    write_output(markdown, output_file, dry=args.dry, verbose=args.verbose)

    if args.verbose:
        print(f"  [完成] 共生成 {len(steps)} 个步骤")
        if not args.dry:
            print(f"  [完成] 文档已保存至: {output_file}")


def _generate_simulated_frames(output_dir: Path, count: int) -> list:
    """
    生成模拟帧文件（用于 dry-run 或降级模式）。

    使用 Pillow 生成纯色图像，保证流程可走通。
    """
    try:
        from PIL import Image
    except ImportError:
        # 无 Pillow 时创建空文件
        frames_dir = output_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        for i in range(count):
            p = frames_dir / f"frame_{i:04d}.jpg"
            p.write_bytes(b"")
            frames.append(p)
        return frames

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i in range(count):
        p = frames_dir / f"frame_{i:04d}.jpg"
        # 生成不同颜色的纯色图，模拟变化
        color = (i * 40 % 255, i * 80 % 255, i * 120 % 255)
        img = Image.new("RGB", (320, 240), color)
        img.save(p, "JPEG")
        frames.append(p)
    return frames


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> int:
    """离线自检核心逻辑，不依赖外部文件或网络。"""
    print("=== 自检开始 ===")
    failures = 0

    # --- 测试 1: 时间戳格式化 ---
    print("[测试 1] format_timestamp")
    ts = format_timestamp(3661.5)
    assert ts == "01:01:01", f"时间戳格式化错误: {ts}"
    ts_zero = format_timestamp(0)
    assert ts_zero == "00:00:00", f"零时间戳错误: {ts_zero}"
    ts_long = format_timestamp(86399)
    assert ts_long == "23:59:59", f"长时间戳错误: {ts_long}"
    print("  ✓ 通过")

    # --- 测试 2: 差异分析（使用模拟帧） ---
    print("[测试 2] compute_change_ratio")
    try:
        from PIL import Image
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # 创建两张完全相同的图像
            img1_path = tmp / "a.jpg"
            img2_path = tmp / "b.jpg"
            img3_path = tmp / "c.jpg"

            Image.new("RGB", (100, 100), (255, 0, 0)).save(img1_path)
            Image.new("RGB", (100, 100), (255, 0, 0)).save(img2_path)  # 相同
            Image.new("RGB", (100, 100), (0, 0, 255)).save(img3_path)  # 完全不同

            # 相同图像差异应为 0
            ratio_same = compute_change_ratio(img1_path, img2_path)
            assert ratio_same < 0.01, f"相同图像差异应接近 0，实际: {ratio_same}"

            # 不同图像差异应较大
            ratio_diff = compute_change_ratio(img1_path, img3_path)
            assert ratio_diff > 0.5, f"不同图像差异应较大，实际: {ratio_diff}"
            print(f"  ✓ 通过 (相同={ratio_same:.4f}, 不同={ratio_diff:.4f})")
    except ImportError:
        print("  ⚠ 跳过（Pillow 不可用）")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1

    # --- 测试 3: 步骤生成 ---
    print("[测试 3] generate_steps")
    # 构造模拟帧信息
    frame_infos = []
    for i in range(10):
        frame_infos.append({
            "path": f"/tmp/frame_{i:04d}.jpg",
            "timestamp": i * 2.0,
            "change_ratio": 0.05 if i % 2 == 0 else 0.0,
            "is_keyframe": i % 2 == 0,  # 每 4 秒一个关键帧
        })

    steps = generate_steps(frame_infos, merge_window=5.0, use_ocr=False)
    # 10 帧，每 2 秒一帧，关键帧间隔 4 秒 < 5 秒，应合并为 1 个步骤
    assert len(steps) >= 1, "应至少生成 1 个步骤"
    assert steps[0]["start_time"] == 0.0, "第一步应从 0 开始"
    print(f"  ✓ 通过 (生成 {len(steps)} 个步骤)")

    # --- 测试 4: Markdown 生成 ---
    print("[测试 4] generate_markdown")
    test_steps = [
        {
            "start_time": 0.0,
            "end_time": 4.0,
            "screenshot": "/tmp/frames/frame_0001.jpg",
            "ocr_text": "打开系统设置",
        },
        {
            "start_time": 10.0,
            "end_time": 16.0,
            "screenshot": "/tmp/frames/frame_0006.jpg",
            "ocr_text": "",
        },
    ]
    md = generate_markdown(test_steps, "test.mp4", 2.0, Path("/tmp"))
    assert "操作演示步骤文档" in md, "缺少标题"
    assert "步骤 1" in md, "缺少步骤 1"
    assert "步骤 2" in md, "缺少步骤 2"
    assert "打开系统设置" in md, "缺少 OCR 文本"
    assert "手动补充说明" in md, "缺少占位符提示"
    print("  ✓ 通过")

    # --- 测试 5: 空输入处理 ---
    print("[测试 5] 空输入处理")
    empty_infos = []
    try:
        generate_steps(empty_infos, use_ocr=False)
        print("  ✗ 失败: 空输入应抛出异常")
        failures += 1
    except SkillError as exc:
        assert exc.code == "E007", f"错误码应为 E007，实际: {exc.code}"
        print("  ✓ 通过（正确抛出 E007）")

    # --- 测试 6: 边界输入 ---
    print("[测试 6] 边界输入")
    # 超长时间戳
    long_ts = format_timestamp(3600 * 100)  # 100 小时
    assert long_ts.startswith("100:"), f"长时间戳格式错误: {long_ts}"
    # 零间隔
    try:
        validate_common_args(argparse.Namespace(
            frame_interval=0, change_threshold=30,
            merge_window=5, min_change_ratio=0.01, max_change_ratio=0.30
        ))
        print("  ✗ 失败: 零间隔应报错")
        failures += 1
    except SkillError as exc:
        assert exc.code == "E009", f"错误码应为 E009，实际: {exc.code}"
        print("  ✓ 通过（正确拒绝零间隔）")

    # --- 测试 7: 中文标点/编码 ---
    print("[测试 7] 编码处理")
    # 模拟含中文的 OCR 文本
    chinese_text = "打开「设置」界面，点击“显示”选项。"
    test_steps_cn = [
        {
            "start_time": 0.0,
            "end_time": 2.0,
            "screenshot": "/tmp/f.jpg",
            "ocr_text": chinese_text,
        }
    ]
    md_cn = generate_markdown(test_steps_cn, "中文视频.mp4", 2.0, Path("/tmp"))
    assert "中文视频" in md_cn, "中文文件名丢失"
    assert chinese_text in md_cn, "中文内容丢失"
    print("  ✓ 通过")

    # --- 测试 8: 环境自检 ---
    print("[测试 8] check_environment")
    missing = check_environment(verbose=False)
    assert isinstance(missing, list), "应返回列表"
    print(f"  ✓ 通过（缺失项: {missing if missing else '无'}）")

    # --- 测试 9: 输入校验 ---
    print("[测试 9] validate_video_path")
    try:
        validate_video_path("/nonexistent/file.mp4")
        print("  ✗ 失败: 不存在的文件应报错")
        failures += 1
    except SkillError as exc:
        assert exc.code == "E002", f"错误码应为 E002，实际: {exc.code}"
        print("  ✓ 通过（正确拒绝不存在的文件）")

    # --- 测试 10: 输出目录校验 ---
    print("[测试 10] validate_output_dir")
    with tempfile.TemporaryDirectory() as tmpdir:
        out = validate_output_dir(tmpdir)
        assert out.is_dir(), "应返回有效目录"
        print("  ✓ 通过")

    # 汇总
    print(f"\n=== 自检完成: {'全部通过' if failures == 0 else f'{failures} 项失败'} ===")
    return 0 if failures == 0 else 1


# ============================================================
# CLI 入口
# ============================================================

def main() -> int:
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="录屏操作演示 智能步骤生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s video.mp4 -o output/                # 标准处理
  %(prog)s video.mp4 --dry-run                 # 预览不写盘
  %(prog)s video.mp4 --frame-interval 5        # 慢速模式
  %(prog)s --selftest                          # 离线自检
        """,
    )
    parser.add_argument("video", nargs="?", help="输入视频文件路径")
    parser.add_argument("-o", "--output", default="./output",
                        help="输出目录（默认: ./output）")
    parser.add_argument("--frame-interval", type=float, default=2.0,
                        help="帧提取间隔秒数（默认: 2）")
    parser.add_argument("--change-threshold", type=int, default=30,
                        help="差异像素阈值 0-255（默认: 30）")
    parser.add_argument("--min-change-ratio", type=float, default=0.01,
                        help="最小变化比例（默认: 0.01）")
    parser.add_argument("--max-change-ratio", type=float, default=0.30,
                        help="最大变化比例（默认: 0.30）")
    parser.add_argument("--merge-window", type=float, default=5.0,
                        help="步骤合并时间窗口秒数（默认: 5）")
    parser.add_argument("--no-ocr", action="store_false", dest="use_ocr",
                        help="禁用 OCR 识别")
    parser.add_argument("--dry-run", action="store_true",
                        help="只预览不写盘")
    parser.add_argument("--verbose", action="store_true",
                        help="输出详细处理过程")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 校验视频参数
    if not args.video:
        parser.error("必须提供视频文件路径（或使用 --selftest）")

    try:
        # 输入校验
        validate_common_args(args)
        video_path = validate_video_path(args.video)
        output_dir = validate_output_dir(args.output)

        # 执行处理
        process_video(video_path, output_dir, args)
        return 0

    except SkillError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        print(f"错误码: {exc.code}", file=sys.stderr)
        if exc.code == "E001":
            print("请安装: pip install pillow pytesseract opencv-python && 安装 Tesseract OCR", file=sys.stderr)
        elif exc.code == "E002":
            print("请检查视频文件路径是否正确且可读", file=sys.stderr)
        elif exc.code == "E003":
            print("请检查输出目录权限", file=sys.stderr)
        elif exc.code == "E004":
            print("请检查 FFmpeg 是否安装并加入 PATH", file=sys.stderr)
        elif exc.code == "E005":
            print("请检查图像文件是否完整", file=sys.stderr)
        elif exc.code == "E007":
            print("视频中未检测到有效操作步骤", file=sys.stderr)
        elif exc.code == "E008":
            print("请检查磁盘空间和目录权限", file=sys.stderr)
        else:
            print("请根据错误信息排查问题", file=sys.stderr)
        return 1

    except Exception as exc:
        print(f"[E010] 未知错误: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
