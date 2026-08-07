#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_image_resize - 图片批处理工具（独立实现版）

功能：批量调整图片尺寸、转换格式与压缩质量，支持预览回滚。
本脚本为 clean-room 独立实现，仅依据功能规格设计。

用法示例：
    python main.py --input ./photos --width 1920 --height 1080 --format webp --quality 80
    python main.py --input ./photos --scale 0.5 --output ./resized --recursive
    python main.py --selftest
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

# 尝试导入图像处理库（标准库无法直接处理图片像素）
# 若未安装，则核心功能不可用，但 --selftest 仍可运行（使用内置模拟数据）
try:
    from PIL import Image, ImageOps  # pip install pillow
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ============================================================
# 错误码定义
# ============================================================
ERR_SUCCESS = 0          # 成功
ERR_INVALID_ARGS = "E001"   # 参数无效
ERR_INPUT_NOT_FOUND = "E002"  # 输入路径不存在
ERR_NO_IMAGES = "E003"      # 未找到任何图片
ERR_PROCESS_FAILED = "E004"  # 图片处理失败
ERR_OUTPUT_FAILED = "E005"   # 输出写入失败
ERR_UNSUPPORTED_FORMAT = "E006"  # 不支持的格式
ERR_IO_ERROR = "E007"       # 文件系统错误
ERR_PIL_MISSING = "E008"    # 缺少 Pillow 库
ERR_ROLLBACK_FAILED = "E009"  # 回滚失败
ERR_INTERNAL = "E010"       # 内部错误


# ============================================================
# 支持的格式（扩展名 -> 格式标识）
# ============================================================
SUPPORTED_INPUT_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
SUPPORTED_OUTPUT_FORMATS = {"jpeg", "png", "webp", "gif", "bmp"}

# 默认参数
DEFAULT_QUALITY = 85
MAX_IMAGE_COUNT = 5000  # 性能保护上限


# ============================================================
# 核心逻辑：图片尺寸计算
# ============================================================
def calc_new_size(orig_w, orig_h, width=None, height=None, scale=None):
    """
    根据原始宽高和目标参数，计算新的尺寸。
    支持三种模式：
      1. 指定宽高（同时指定时，保持比例，取较小缩放）
      2. 仅指定宽度（高度按比例）
      3. 仅指定高度（宽度按比例）
      4. 指定缩放比例（0~1 或 >1）
    返回 (new_w, new_h)
    """
    if orig_w <= 0 or orig_h <= 0:
        raise ValueError("原始尺寸必须为正数")

    # 缩放比例模式
    if scale is not None:
        if scale <= 0:
            raise ValueError("缩放比例必须大于 0")
        new_w = max(1, int(round(orig_w * scale)))
        new_h = max(1, int(round(orig_h * scale)))
        return new_w, new_h

    # 指定宽高模式
    if width is None and height is None:
        # 无任何参数，返回原尺寸
        return orig_w, orig_h

    # 计算比例因子
    ratio_w = None
    ratio_h = None
    if width is not None:
        if width <= 0:
            raise ValueError("宽度必须为正数")
        ratio_w = width / orig_w
    if height is not None:
        if height <= 0:
            raise ValueError("高度必须为正数")
        ratio_h = height / orig_h

    # 取较小比例（保证不超过任何指定边界）
    if ratio_w is not None and ratio_h is not None:
        ratio = min(ratio_w, ratio_h)
    elif ratio_w is not None:
        ratio = ratio_w
    else:
        ratio = ratio_h

    new_w = max(1, int(round(orig_w * ratio)))
    new_h = max(1, int(round(orig_h * ratio)))
    return new_w, new_h


# ============================================================
# 核心逻辑：图片处理（依赖 Pillow）
# ============================================================
def process_image_file(src_path, dst_path, width=None, height=None, scale=None,
                       out_format=None, quality=DEFAULT_QUALITY, keep_metadata=False):
    """
    处理单张图片：缩放、格式转换、质量压缩。
    返回处理后的 (格式, 宽, 高, 文件大小)
    """
    if not HAS_PIL:
        raise RuntimeError(ERR_PIL_MISSING)

    try:
        img = Image.open(src_path)
        orig_w, orig_h = img.size

        # 计算新尺寸
        new_w, new_h = calc_new_size(orig_w, orig_h, width, height, scale)

        # 执行缩放（使用高质量重采样）
        if (new_w, new_h) != (orig_w, orig_h):
            img = img.resize((new_w, new_h), Image.LANCZOS)

        # 确定输出格式
        if out_format is None:
            # 默认保持原格式（但扩展名可能变化）
            out_format = (img.format or "JPEG").lower()
            if out_format == "jpg":
                out_format = "jpeg"

        # 格式规范化
        out_format = out_format.lower()
        if out_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"不支持的输出格式: {out_format}")

        # 转换模式（处理透明度、调色板等）
        if out_format in ("jpeg", "bmp"):
            # JPEG/BMP 不支持透明度，转为 RGB
            if img.mode in ("RGBA", "P", "LA"):
                # 白色背景合成
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if img.mode == "LA":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = bg
            else:
                img = img.convert("RGB")
        elif out_format == "png":
            if img.mode not in ("RGBA", "RGB", "L"):
                img = img.convert("RGBA")
        elif out_format == "webp":
            if img.mode not in ("RGBA", "RGB", "L"):
                img = img.convert("RGBA")
        elif out_format == "gif":
            if img.mode != "P":
                img = img.convert("P", palette=Image.ADAPTIVE)
        else:
            img = img.convert("RGB")

        # 保存
        save_kwargs = {}
        if out_format in ("jpeg", "webp"):
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif out_format == "png":
            save_kwargs["optimize"] = True

        # 元数据处理（可选保留 EXIF）
        if keep_metadata and hasattr(img, "info"):
            exif = img.info.get("exif")
            if exif:
                save_kwargs["exif"] = exif

        img.save(dst_path, format=out_format, **save_kwargs)

        # 获取输出文件大小
        file_size = os.path.getsize(dst_path)
        return out_format, new_w, new_h, file_size

    except Exception as e:
        raise RuntimeError(f"{ERR_PROCESS_FAILED}: {e}") from e


# ============================================================
# 文件收集
# ============================================================
def collect_images(input_path, recursive=False):
    """
    收集输入目录（或文件）下的所有图片文件。
    返回 Path 列表，按名称排序。
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(ERR_INPUT_NOT_FOUND)

    images = []
    if input_path.is_file():
        if input_path.suffix.lower() in SUPPORTED_INPUT_EXT:
            images.append(input_path)
    else:
        # 目录
        if recursive:
            for root, _, files in os.walk(input_path):
                for f in sorted(files):
                    p = Path(root) / f
                    if p.suffix.lower() in SUPPORTED_INPUT_EXT:
                        images.append(p)
        else:
            for f in sorted(input_path.iterdir()):
                if f.is_file() and f.suffix.lower() in SUPPORTED_INPUT_EXT:
                    images.append(f)

    if len(images) > MAX_IMAGE_COUNT:
        raise ValueError(f"{ERR_INVALID_ARGS}: 图片数量超过上限 {MAX_IMAGE_COUNT}")

    return images


# ============================================================
# 输出路径生成
# ============================================================
def build_output_path(src_path, output_dir, out_format=None, suffix="_resized"):
    """
    在 output_dir 下生成与源文件对应的输出路径。
    保持相对目录结构（若需递归）。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保持相对路径结构
    rel_path = src_path.name  # 默认仅文件名
    # 若输出目录与输入目录有共同父级，保留子目录结构
    # 简化处理：仅使用文件名，避免复杂路径映射

    stem = src_path.stem
    if out_format:
        ext = f".{out_format}"
    else:
        ext = src_path.suffix.lower()
        if ext == ".jpg":
            ext = ".jpeg"

    # 避免重名覆盖：若目标已存在，自动加序号
    base_name = f"{stem}{suffix}{ext}"
    dst_path = output_dir / base_name
    counter = 1
    while dst_path.exists():
        dst_path = output_dir / f"{stem}{suffix}_{counter}{ext}"
        counter += 1

    return dst_path


# ============================================================
# 批处理主流程（含预览/回滚）
# ============================================================
def batch_process(input_path, output_dir=None, width=None, height=None, scale=None,
                  out_format=None, quality=DEFAULT_QUALITY, recursive=False,
                  keep_metadata=False, preview=False, rollback=False):
    """
    批量处理图片。
    若 preview=True，仅生成预览报告（不实际写入最终文件）。
    若 rollback=True，尝试撤销最近一次处理（恢复原文件）。
    返回处理结果字典。
    """
    results = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "files": [],
        "errors": [],
    }

    try:
        # 收集图片
        images = collect_images(input_path, recursive)
        results["total"] = len(images)

        if not images:
            raise FileNotFoundError(ERR_NO_IMAGES)

        # 确定输出目录
        if output_dir is None:
            # 默认在输入目录下创建 output 子目录
            input_p = Path(input_path)
            if input_p.is_dir():
                output_dir = input_p / "output"
            else:
                output_dir = input_p.parent / "output"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 若回滚模式，则尝试恢复
        if rollback:
            return _do_rollback(input_path, output_dir, images, results)

        # 预览模式：不实际写入，仅计算
        if preview:
            for img_path in images:
                try:
                    if HAS_PIL:
                        with Image.open(img_path) as img:
                            orig_w, orig_h = img.size
                            new_w, new_h = calc_new_size(orig_w, orig_h, width, height, scale)
                            fmt = (out_format or (img.format or "jpeg").lower())
                            results["files"].append({
                                "src": str(img_path),
                                "dst": str(build_output_path(img_path, output_dir, out_format)),
                                "orig_size": (orig_w, orig_h),
                                "new_size": (new_w, new_h),
                                "format": fmt,
                                "status": "preview",
                            })
                            results["success"] += 1
                    else:
                        # 无 PIL 时仅做参数校验
                        new_w, new_h = calc_new_size(100, 100, width, height, scale)
                        results["files"].append({
                            "src": str(img_path),
                            "dst": str(build_output_path(img_path, output_dir, out_format)),
                            "orig_size": (100, 100),
                            "new_size": (new_w, new_h),
                            "format": out_format or "jpeg",
                            "status": "preview(no-pil)",
                        })
                        results["success"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{img_path}: {e}")
            return results

        # 正式处理
        for img_path in images:
            try:
                # 生成输出路径
                dst_path = build_output_path(img_path, output_dir, out_format)

                # 处理图片
                fmt, w, h, size = process_image_file(
                    img_path, dst_path, width, height, scale,
                    out_format, quality, keep_metadata
                )
                results["files"].append({
                    "src": str(img_path),
                    "dst": str(dst_path),
                    "orig_size": None,  # 可在实际处理时获取
                    "new_size": (w, h),
                    "format": fmt,
                    "size": size,
                    "status": "done",
                })
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{img_path}: {e}")

        return results

    except Exception as e:
        results["errors"].append(f"批处理失败: {e}")
        return results


def _do_rollback(input_path, output_dir, images, results):
    """
    回滚操作：将输出目录中与源文件同名的文件删除。
    简化实现：仅清理本次生成的输出文件（不恢复原文件，因为原文件未被修改）。
    """
    try:
        removed = 0
        for img_path in images:
            # 查找可能生成的输出文件
            for candidate in output_dir.glob(f"{img_path.stem}_resized*"):
                try:
                    candidate.unlink()
                    removed += 1
                except OSError:
                    pass
        results["success"] = removed
        results["files"].append({"status": f"rollback-removed-{removed}"})
    except Exception as e:
        results["errors"].append(f"回滚失败: {e}")
        results["failed"] += 1
        results["success"] = 0
    return results


# ============================================================
# 自测模块（内置硬编码样例，不依赖外部文件）
# ============================================================
def _selftest():
    """
    内置自检逻辑：使用内存中的模拟数据验证核心算法。
    不读取任何外部文件，不依赖网络，不依赖当前工作目录。
    """
    print("[selftest] 开始自检...")
    errors = []

    # ---- 测试 1: 尺寸计算 ----
    print("[selftest] 测试尺寸计算...")
    try:
        # 原图 1920x1080
        cases = [
            # (orig_w, orig_h, width, height, scale, 预期宽, 预期高)
            (1920, 1080, 960, None, None, 960, 540),      # 仅指定宽度
            (1920, 1080, None, 540, None, 960, 540),      # 仅指定高度
            (1920, 1080, 960, 540, None, 960, 540),       # 指定宽高（等比例）
            (1920, 1080, 1000, 1000, None, 1000, 562),    # 指定宽高（取小比例）
            (1920, 1080, None, None, 0.5, 960, 540),      # 缩放 50%
            (1920, 1080, None, None, 2.0, 3840, 2160),    # 放大 2 倍
            (100, 100, 200, 100, None, 100, 100),         # 边界：宽高比差异大
        ]
        for i, (ow, oh, w, h, s, ew, eh) in enumerate(cases):
            nw, nh = calc_new_size(ow, oh, w, h, s)
            # 宽松断言：允许 1 像素误差
            assert abs(nw - ew) <= 1, f"用例 {i}: 宽 {nw} != {ew}"
            assert abs(nh - eh) <= 1, f"用例 {i}: 高 {nh} != {eh}"
        print("  ✓ 尺寸计算通过")
    except Exception as e:
        errors.append(f"尺寸计算失败: {e}")
        print(f"  ✗ 尺寸计算失败: {e}")

    # ---- 测试 2: 参数校验 ----
    print("[selftest] 测试参数校验...")
    try:
        # 非法参数应抛异常
        try:
            calc_new_size(100, 100, width=0, height=100)
            errors.append("宽度为 0 未报错")
        except ValueError:
            pass

        try:
            calc_new_size(100, 100, scale=-1)
            errors.append("负缩放未报错")
        except ValueError:
            pass

        try:
            calc_new_size(0, 100, width=100)
            errors.append("原始宽为 0 未报错")
        except ValueError:
            pass

        print("  ✓ 参数校验通过")
    except Exception as e:
        errors.append(f"参数校验失败: {e}")
        print(f"  ✗ 参数校验失败: {e}")

    # ---- 测试 3: 文件收集（使用临时目录） ----
    print("[selftest] 测试文件收集...")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # 创建测试文件
            (tmp / "a.jpg").write_bytes(b"fake")
            (tmp / "b.png").write_bytes(b"fake")
            (tmp / "c.txt").write_bytes(b"fake")  # 非图片
            sub = tmp / "sub"
            sub.mkdir()
            (sub / "d.jpeg").write_bytes(b"fake")

            # 非递归
            imgs = collect_images(tmp, recursive=False)
            assert len(imgs) == 2, f"非递归应找到 2 个，实际 {len(imgs)}"

            # 递归
            imgs = collect_images(tmp, recursive=True)
            assert len(imgs) == 3, f"递归应找到 3 个，实际 {len(imgs)}"

            # 单文件
            imgs = collect_images(tmp / "a.jpg")
            assert len(imgs) == 1

            # 不存在的路径
            try:
                collect_images(tmp / "nonexist")
                errors.append("不存在的路径未报错")
            except FileNotFoundError:
                pass

        print("  ✓ 文件收集通过")
    except Exception as e:
        errors.append(f"文件收集失败: {e}")
        print(f"  ✗ 文件收集失败: {e}")

    # ---- 测试 4: 输出路径生成 ----
    print("[selftest] 测试输出路径...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            src = tmp / "photo.jpg"
            out_dir = tmp / "out"

            # 基本生成
            dst = build_output_path(src, out_dir, "webp")
            assert dst.name == "photo_resized.webp", f"名称错误: {dst.name}"
            assert dst.parent == out_dir

            # 重复生成（避免覆盖）
            dst1 = build_output_path(src, out_dir, "webp")
            dst2 = build_output_path(src, out_dir, "webp")
            # 手动创建第一个文件
            dst1.parent.mkdir(parents=True, exist_ok=True)
            dst1.write_bytes(b"x")
            dst3 = build_output_path(src, out_dir, "webp")
            assert dst3.name != dst1.name, "重复生成未避免覆盖"

        print("  ✓ 输出路径生成通过")
    except Exception as e:
        errors.append(f"输出路径生成失败: {e}")
        print(f"  ✗ 输出路径生成失败: {e}")

    # ---- 测试 5: 端到端批处理（使用 PIL 或模拟） ----
    print("[selftest] 测试批处理流程...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            in_dir = tmp / "input"
            in_dir.mkdir()

            if HAS_PIL:
                # 创建真实图片
                from PIL import Image as PILImage
                img = PILImage.new("RGB", (200, 100), color=(255, 0, 0))
                img.save(in_dir / "test.jpg", "JPEG")
            else:
                # 无 PIL 时创建伪文件
                (in_dir / "test.jpg").write_bytes(b"fake-image-data")

            out_dir = tmp / "output"

            # 执行批处理
            results = batch_process(
                input_path=in_dir,
                output_dir=out_dir,
                width=100,
                height=50,
                out_format="png",
                quality=80,
            )

            # 检查结果
            assert results["total"] == 1, f"应处理 1 张，实际 {results['total']}"
            if HAS_PIL:
                assert results["success"] == 1, f"应成功 1 张，实际 {results['success']}"
                # 验证输出文件存在
                out_files = list(out_dir.glob("*.png"))
                assert len(out_files) == 1, f"应有 1 个输出文件，实际 {len(out_files)}"
                # 验证尺寸
                with PILImage.open(out_files[0]) as out_img:
                    w, h = out_img.size
                    assert w == 100 and h == 50, f"输出尺寸错误: {w}x{h}"
            else:
                # 无 PIL 时只验证流程不崩溃
                print("  (无 Pillow，跳过实际图像验证)")

        print("  ✓ 批处理流程通过")
    except Exception as e:
        errors.append(f"批处理流程失败: {e}")
        print(f"  ✗ 批处理流程失败: {e}")

    # ---- 测试 6: 预览模式 ----
    print("[selftest] 测试预览模式...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            in_dir = tmp / "input"
            in_dir.mkdir()
            (in_dir / "a.jpg").write_bytes(b"fake")

            results = batch_process(
                input_path=in_dir,
                output_dir=tmp / "out",
                width=800,
                height=600,
                preview=True,
            )
            assert results["total"] == 1
            # 预览不应生成实际文件
            out_dir = tmp / "out"
            assert not out_dir.exists() or len(list(out_dir.glob("*"))) == 0, "预览模式不应生成文件"

        print("  ✓ 预览模式通过")
    except Exception as e:
        errors.append(f"预览模式失败: {e}")
        print(f"  ✗ 预览模式失败: {e}")

    # ---- 汇总 ----
    if errors:
        print(f"\n[selftest] 自检失败，共 {len(errors)} 个错误:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n[selftest] 全部自检通过 ✓")
        return True


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="图片批处理工具 - 批量调整尺寸、转换格式、压缩质量",
        epilog="示例: python main.py --input ./photos --width 1920 --height 1080 --format webp --quality 80"
    )

    # 核心参数
    parser.add_argument("--input", "-i", type=str, help="输入文件或目录")
    parser.add_argument("--output", "-o", type=str, help="输出目录（默认在输入目录下创建 output）")

    # 尺寸参数（三选一或组合）
    size_group = parser.add_mutually_exclusive_group(required=False)
    size_group.add_argument("--width", type=int, help="目标宽度（像素）")
    size_group.add_argument("--height", type=int, help="目标高度（像素）")
    size_group.add_argument("--scale", type=float, help="缩放比例（如 0.5 表示 50%）")

    # 格式与质量
    parser.add_argument("--format", "-f", type=str, choices=sorted(SUPPORTED_OUTPUT_FORMATS),
                        help="输出格式: jpeg/png/webp/gif/bmp")
    parser.add_argument("--quality", "-q", type=int, default=DEFAULT_QUALITY,
                        help=f"压缩质量 (1-100，默认 {DEFAULT_QUALITY})")

    # 功能选项
    parser.add_argument("--recursive", "-r", action="store_true", help="递归处理子目录")
    parser.add_argument("--keep-metadata", action="store_true", help="保留 EXIF 等元数据")
    parser.add_argument("--preview", action="store_true", help="仅生成预览报告，不实际写入")
    parser.add_argument("--rollback", action="store_true", help="回滚（删除已生成的输出文件）")

    # 自测
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = _selftest()
        sys.exit(0 if ok else 1)

    # 参数校验
    if not args.input:
        print(f"错误 {ERR_INVALID_ARGS}: 必须指定 --input", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if not HAS_PIL:
        print(f"错误 {ERR_PIL_MISSING}: 需要 Pillow 库，请安装: pip install pillow", file=sys.stderr)
        sys.exit(1)

    # 执行批处理
    try:
        results = batch_process(
            input_path=args.input,
            output_dir=args.output,
            width=args.width,
            height=args.height,
            scale=args.scale,
            out_format=args.format,
            quality=args.quality,
            recursive=args.recursive,
            keep_metadata=args.keep_metadata,
            preview=args.preview,
            rollback=args.rollback,
        )

        # 输出结果摘要
        print(f"处理完成: 共 {results['total']} 个文件，成功 {results['success']}，失败 {results['failed']}")
        if results["files"]:
            for f in results["files"][:20]:  # 最多显示 20 条
                if f.get("status") == "done":
                    print(f"  ✓ {f['src']} -> {f['dst']} ({f['format']}, {f['new_size'][0]}x{f['new_size'][1]})")
                elif f.get("status") == "preview":
                    print(f"  👁 {f['src']} -> {f['dst']} (预览)")
                else:
                    print(f"  ℹ {f}")

        if results["errors"]:
            print("\n错误详情:")
            for err in results["errors"][:10]:
                print(f"  ✗ {err}")

        # 失败时返回非零退出码
        if results["failed"] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"错误 {ERR_INTERNAL}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
