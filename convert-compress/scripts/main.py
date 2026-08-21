#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert-compress 图片转换压缩工具（独立实现）

功能概述：
- 支持 20+ 常见图片格式的转换（PNG/JPEG/WEBP/TIFF/BMP/GIF 等）
- 支持 JPEG/WEBP 质量压缩（0-100）
- 支持按宽/高/百分比/最长边/最短边五种模式缩放
- 支持批量处理与文件夹递归扫描
- 保留 EXIF 基础信息（拍摄时间、设备型号）
- 输出处理结果报告 JSON

错误码说明：
E001 - 输入文件不存在
E002 - 输入格式不支持
E003 - 输出格式不支持
E004 - 图片解码失败
E005 - 图片编码失败
E006 - 质量参数非法
E007 - 尺寸参数非法
E008 - 输出目录不可写
E009 - 批量处理部分失败
E010 - 未知异常
"""

import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise

# 尝试导入 Pillow（唯一第三方依赖，用于图片处理）
try:
    from PIL import Image, ImageOps
    from PIL.ExifTags import TAGS as EXIF_TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    # pip install Pillow

# 支持的输入格式（Pillow 可解码）
SUPPORTED_INPUT_FORMATS = {
    ".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif",
    ".tif", ".tiff", ".bmp", ".gif", ".svg", ".ico",
    ".ppm", ".pgm", ".pbm", ".pnm", ".dds", ".dib",
    ".eps", ".im", ".mpo", ".pcx", ".sgi", ".tga",
    ".xbm", ".xpm", ".cur", ".dcx", ".emf", ".wmf"
}

# 支持的输出格式（Pillow 可保存）
SUPPORTED_OUTPUT_FORMATS = {
    ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff",
    ".bmp", ".gif", ".ico", ".ppm", ".pgm", ".pbm",
    ".pnm", ".dds", ".dib", ".eps", ".im", ".mpo",
    ".pcx", ".sgi", ".tga", ".xbm", ".xpm", ".cur",
    ".dcx", ".emf", ".wmf"
}

# 输出格式与 Pillow 保存格式的映射
FORMAT_MAP = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
    ".webp": "WEBP", ".tif": "TIFF", ".tiff": "TIFF",
    ".bmp": "BMP", ".gif": "GIF", ".ico": "ICO",
    ".ppm": "PPM", ".pgm": "PGM", ".pbm": "PBM",
    ".pnm": "PNM", ".dds": "DDS", ".dib": "DIB",
    ".eps": "EPS", ".im": "IM", ".mpo": "MPO",
    ".pcx": "PCX", ".sgi": "SGI", ".tga": "TGA",
    ".xbm": "XBM", ".xpm": "XPM", ".cur": "CUR",
    ".dcx": "DCX", ".emf": "EMF", ".wmf": "WMF"
}


class ImageProcessor:
    """图片处理核心类"""

    def __init__(self, quality: int = 85, resize_mode: str = "none",
                 width: Optional[int] = None, height: Optional[int] = None,
                 percent: Optional[float] = None,
                 longest_edge: Optional[int] = None,
                 shortest_edge: Optional[int] = None,
                 keep_exif: bool = True):
        """
        初始化处理器

        :param quality: 压缩质量 0-100
        :param resize_mode: 缩放模式 none/width/height/percent/longest/shortest
        :param width: 目标宽度
        :param height: 目标高度
        :param percent: 缩放百分比
        :param longest_edge: 最长边目标长度
        :param shortest_edge: 最短边目标长度
        :param keep_exif: 是否保留 EXIF 信息
        """
        self.quality = quality
        self.resize_mode = resize_mode
        self.width = width
        self.height = height
        self.percent = percent
        self.longest_edge = longest_edge
        self.shortest_edge = shortest_edge
        self.keep_exif = keep_exif

    def process(self, input_path: str, output_path: str,
                output_format: Optional[str] = None) -> Dict[str, Any]:
        """
        处理单个图片文件

        :param input_path: 输入文件路径
        :param output_path: 输出文件路径
        :param output_format: 输出格式（如 .png/.jpg），默认由输出路径决定
        :return: 处理结果报告
        """
        start_time = time.time()

        # 检查输入文件
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"E001: 输入文件不存在: {input_path}")

        # 检查输入格式
        input_ext = Path(input_path).suffix.lower()
        if input_ext not in SUPPORTED_INPUT_FORMATS:
            raise ValueError(f"E002: 不支持的输入格式: {input_ext}")

        # 确定输出格式
        if output_format is None:
            output_ext = Path(output_path).suffix.lower()
        else:
            output_ext = output_format.lower()
            if not output_ext.startswith("."):
                output_ext = f".{output_ext}"

        if output_ext not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"E003: 不支持的输出格式: {output_ext}")

        # 检查质量参数
        if not 0 <= self.quality <= 100:
            raise ValueError(f"E006: 质量参数必须在 0-100 之间: {self.quality}")

        # 检查尺寸参数
        self._validate_resize_params()

        # 检查输出目录
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir and not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError:
                raise PermissionError(f"E008: 输出目录不可写: {output_dir}")

        if not os.access(output_dir, os.W_OK):
            raise PermissionError(f"E008: 输出目录不可写: {output_dir}")

        # 读取原始文件大小
        original_size = os.path.getsize(input_path)

        try:
            # 打开图片
            with Image.open(input_path) as img:
                # 处理 EXIF 方向
                img = ImageOps.exif_transpose(img)

                # 记录 EXIF 信息
                exif_data = None
                if self.keep_exif and hasattr(img, "getexif"):
                    exif_data = img.getexif()

                # 缩放处理
                img = self._resize_image(img)

                # 转换模式（处理透明通道）
                img = self._prepare_for_save(img, output_ext)

                # 保存参数
                save_kwargs = self._get_save_kwargs(output_ext, exif_data)

                # 保存图片
                img.save(output_path, **save_kwargs)

        except (IOError, OSError) as e:
            raise ValueError(f"E004: 图片解码失败: {str(e)}") from e
        except Exception as e:
            if isinstance(e, ValueError) and str(e).startswith("E00"):
                raise
            raise ValueError(f"E005: 图片编码失败: {str(e)}") from e

        # 计算处理结果
        new_size = os.path.getsize(output_path)
        duration_ms = int((time.time() - start_time) * 1000)
        ratio = round(new_size / original_size, 4) if original_size > 0 else 0.0

        return {
            "status": "success",
            "input": input_path,
            "output": output_path,
            "original_size": original_size,
            "new_size": new_size,
            "ratio": ratio,
            "duration_ms": duration_ms
        }

    def _validate_resize_params(self):
        """校验缩放参数"""
        if self.resize_mode == "width" and (self.width is None or self.width <= 0):
            raise ValueError(f"E007: 宽度模式需要正数宽度参数: {self.width}")
        if self.resize_mode == "height" and (self.height is None or self.height <= 0):
            raise ValueError(f"E007: 高度模式需要正数高度参数: {self.height}")
        if self.resize_mode == "percent" and (self.percent is None or self.percent <= 0):
            raise ValueError(f"E007: 百分比模式需要正数百分比参数: {self.percent}")
        if self.resize_mode == "longest" and (self.longest_edge is None or self.longest_edge <= 0):
            raise ValueError(f"E007: 最长边模式需要正数参数: {self.longest_edge}")
        if self.resize_mode == "shortest" and (self.shortest_edge is None or self.shortest_edge <= 0):
            raise ValueError(f"E007: 最短边模式需要正数参数: {self.shortest_edge}")

    def _resize_image(self, img: Image.Image) -> Image.Image:
        """根据缩放模式调整图片尺寸"""
        if self.resize_mode == "none":
            return img

        orig_w, orig_h = img.size
        new_w, new_h = orig_w, orig_h

        if self.resize_mode == "width":
            new_w = self.width
            new_h = int(orig_h * (new_w / orig_w))

        elif self.resize_mode == "height":
            new_h = self.height
            new_w = int(orig_w * (new_h / orig_h))

        elif self.resize_mode == "percent":
            new_w = int(orig_w * self.percent / 100)
            new_h = int(orig_h * self.percent / 100)

        elif self.resize_mode == "longest":
            longest = max(orig_w, orig_h)
            if longest > self.longest_edge:
                scale = self.longest_edge / longest
                new_w = max(1, int(orig_w * scale))
                new_h = max(1, int(orig_h * scale))

        elif self.resize_mode == "shortest":
            shortest = min(orig_w, orig_h)
            if shortest < self.shortest_edge:
                scale = self.shortest_edge / shortest
                new_w = max(1, int(orig_w * scale))
                new_h = max(1, int(orig_h * scale))

        # 确保尺寸不小于 1
        new_w = max(1, new_w)
        new_h = max(1, new_h)

        if (new_w, new_h) != (orig_w, orig_h):
            img = img.resize((new_w, new_h), Image.LANCZOS)

        return img

    def _prepare_for_save(self, img: Image.Image, output_ext: str) -> Image.Image:
        """为保存准备图片模式"""
        # JPEG 不支持透明通道，转换为 RGB
        if output_ext in (".jpg", ".jpeg") and img.mode in ("RGBA", "P", "LA"):
            # 创建白色背景
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])
            elif img.mode == "P":
                img = img.convert("RGBA")
                background.paste(img, mask=img.split()[3])
            else:
                img = img.convert("RGBA")
                background.paste(img, mask=img.split()[3])
            img = background

        # 其他格式确保 RGB 或 RGBA
        elif output_ext not in (".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"):
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

        return img

    def _get_save_kwargs(self, output_ext: str,
                         exif_data: Any) -> Dict[str, Any]:
        """获取保存参数"""
        save_format = FORMAT_MAP.get(output_ext, "PNG")
        kwargs: Dict[str, Any] = {"format": save_format}

        # 压缩质量参数
        if save_format in ("JPEG", "WEBP"):
            kwargs["quality"] = self.quality
            if save_format == "JPEG":
                kwargs["optimize"] = True

        # EXIF 信息
        if exif_data is not None and save_format in ("JPEG", "WEBP", "TIFF"):
            try:
                kwargs["exif"] = exif_data
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出  # EXIF 保存失败不影响主流程

        # PNG 压缩级别
        if save_format == "PNG":
            kwargs["optimize"] = True

        return kwargs


def process_batch(input_paths: List[str], output_dir: str,
                  processor: ImageProcessor,
                  output_format: Optional[str] = None,
                  prefix: str = "",
                  recursive: bool = False) -> List[Dict[str, Any]]:
    """
    批量处理图片文件

    :param input_paths: 输入文件或文件夹路径列表
    :param output_dir: 输出目录
    :param processor: 图片处理器实例
    :param output_format: 输出格式
    :param prefix: 输出文件名前缀
    :param recursive: 是否递归扫描文件夹
    :return: 处理结果列表
    """
    results = []
    files_to_process: List[str] = []

    # 收集所有需要处理的文件
    for path in input_paths:
        if os.path.isdir(path):
            # 扫描文件夹
            if recursive:
                for root, _, filenames in os.walk(path):
                    for fname in filenames:
                        fpath = os.path.join(root, fname)
                        if Path(fpath).suffix.lower() in SUPPORTED_INPUT_FORMATS:
                            files_to_process.append(fpath)
            else:
                for fname in os.listdir(path):
                    fpath = os.path.join(path, fname)
                    if os.path.isfile(fpath) and Path(fpath).suffix.lower() in SUPPORTED_INPUT_FORMATS:
                        files_to_process.append(fpath)
        elif os.path.isfile(path):
            if Path(path).suffix.lower() in SUPPORTED_INPUT_FORMATS:
                files_to_process.append(path)
            else:
                results.append({
                    "status": "failed",
                    "input": path,
                    "output": None,
                    "original_size": 0,
                    "new_size": 0,
                    "ratio": 0.0,
                    "duration_ms": 0,
                    "error": f"E002: 不支持的输入格式: {Path(path).suffix}"
                })

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 处理每个文件
    for file_path in files_to_process:
        try:
            # 生成输出文件名
            fname = Path(file_path).name
            if output_format:
                base_name = Path(fname).stem
                out_fname = f"{prefix}{base_name}{output_format}"
            else:
                out_fname = f"{prefix}{fname}"
            out_path = os.path.join(output_dir, out_fname)

            # 处理文件
            result = processor.process(file_path, out_path, output_format)
            results.append(result)

        except Exception as e:
            # 记录失败结果
            error_msg = str(e)
            # 提取错误码
            err_code = "E010"
            for code in ["E001", "E002", "E003", "E004", "E005",
                         "E006", "E007", "E008"]:
                if code in error_msg:
                    err_code = code
                    break

            results.append({
                "status": "failed",
                "input": file_path,
                "output": None,
                "original_size": 0,
                "new_size": 0,
                "ratio": 0.0,
                "duration_ms": 0,
                "error": f"{err_code}: {error_msg}"
            })

    # 检查是否有失败项
    failed_count = sum(1 for r in results if r["status"] == "failed")
    if failed_count > 0:
        results.append({
            "status": "partial_failed",
            "total": len(results),
            "failed": failed_count,
            "error": "E009: 批量处理部分失败"
        })

    return results


def download_image(url: str, save_path: Optional[str] = None) -> str:
    """
    从 URL 下载图片

    :param url: 图片 URL
    :param save_path: 保存路径，默认使用临时文件
    :return: 下载后的本地路径
    """
    if save_path is None:
        save_path = os.path.join(tempfile.gettempdir(),
                                 f"download_{int(time.time())}.tmp")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            with open(save_path, "wb") as f:
                shutil.copyfileobj(response, f)
    except Exception as e:
        raise ConnectionError(f"E010: 下载失败: {str(e)}") from e

    return save_path


def run_selftest() -> bool:
    """
    自检测试：使用内置硬编码数据验证核心逻辑
    """
    print("=" * 60)
    print("convert-compress 自检测试")
    print("=" * 60)

    # 检查 Pillow 是否可用
    if not HAS_PIL:
        print("[FAIL] Pillow 未安装，无法进行图片处理测试")
        print("请运行: pip install Pillow")
        return False

    # 使用内存中的硬编码图片数据
    # 创建一个 100x80 的测试图片（红色渐变）
    print("\n[1/5] 创建测试图片...")
    test_img = Image.new("RGB", (100, 80), (255, 0, 0))
    # 添加一些渐变效果
    for x in range(100):
        for y in range(80):
            r = int(255 * x / 100)
            g = int(255 * y / 80)
            b = 128
            test_img.putpixel((x, y), (r, g, b))

    # 保存到临时文件
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="convert_compress_selftest_")
    input_path = os.path.join(temp_dir, "test_input.png")
    output_path = os.path.join(temp_dir, "test_output.jpg")

    try:
        test_img.save(input_path, format="PNG")
        print(f"    测试图片已创建: {input_path} ({os.path.getsize(input_path)} bytes)")

        # 测试 1: 基本格式转换
        print("\n[2/5] 测试格式转换 (PNG -> JPEG)...")
        processor = ImageProcessor(quality=80)
        result = processor.process(input_path, output_path, ".jpg")

        assert result["status"] == "success", f"转换失败: {result}"
        assert os.path.exists(output_path), "输出文件不存在"
        assert result["new_size"] > 0, "输出文件为空"
        print(f"    成功: {result['input']} -> {result['output']}")
        print(f"    原始大小: {result['original_size']} bytes, "
              f"新大小: {result['new_size']} bytes, "
              f"压缩比: {result['ratio']}")

        # 测试 2: 尺寸调整
        print("\n[3/5] 测试尺寸调整 (宽度模式)...")
        processor2 = ImageProcessor(resize_mode="width", width=50)
        output_path2 = os.path.join(temp_dir, "test_output2.png")
        result2 = processor2.process(input_path, output_path2, ".png")

        with Image.open(output_path2) as img2:
            w2, h2 = img2.size
            assert w2 == 50, f"宽度应为 50，实际为 {w2}"
            assert h2 == 40, f"高度应为 40，实际为 {h2}"
        print(f"    成功: 尺寸调整为 {w2}x{h2}")

        # 测试 3: 压缩质量
        print("\n[4/5] 测试质量压缩...")
        processor3 = ImageProcessor(quality=20)
        output_path3 = os.path.join(temp_dir, "test_output3.jpg")
        result3 = processor3.process(input_path, output_path3, ".jpg")

        processor4 = ImageProcessor(quality=95)
        output_path4 = os.path.join(temp_dir, "test_output4.jpg")
        result4 = processor4.process(input_path, output_path4, ".jpg")

        assert result3["new_size"] < result4["new_size"], \
            "低质量应产生更小的文件"
        print(f"    成功: 低质量({result3['new_size']} bytes) "
              f"< 高质量({result4['new_size']} bytes)")

        # 测试 4: 批量处理
        print("\n[5/5] 测试批量处理...")
        batch_dir = os.path.join(temp_dir, "batch_input")
        os.makedirs(batch_dir, exist_ok=True)
        for i in range(3):
            img_i = Image.new("RGB", (50 + i * 10, 40 + i * 10), (i * 50, 100, 200))
            img_i.save(os.path.join(batch_dir, f"test_{i}.png"))

        batch_output = os.path.join(temp_dir, "batch_output")
        batch_results = process_batch(
            [batch_dir], batch_output, processor, ".jpg", prefix="conv_"
        )

        success_count = sum(1 for r in batch_results if r["status"] == "success")
        assert success_count == 3, f"应处理 3 个文件，实际成功 {success_count}"
        print(f"    成功: 批量处理 {success_count} 个文件")

        # 清理测试文件
        print("\n清理测试文件...")
        shutil.rmtree(temp_dir, ignore_errors=True)

        print("\n" + "=" * 60)
        print("所有自检测试通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n[FAIL] 断言失败: {str(e)}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
    except Exception as e:
        print(f"\n[FAIL] 测试异常: {str(e)}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="图片转换压缩工具 - 支持 20+ 格式批量处理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单文件转换
  python main.py input.png output.jpg

  # 批量转换并压缩
  python main.py input_dir/ output_dir/ --quality 70 --output-format .webp

  # 缩放图片
  python main.py input.png output.png --resize-mode width --width 800

  # 递归处理文件夹
  python main.py input_dir/ output_dir/ --recursive --prefix "conv_"

  # 自检测试
  python main.py --selftest
        """
    )

    # 输入输出参数
    parser.add_argument("--input", nargs="*", help="输入文件或文件夹路径")
    parser.add_argument("--output", nargs="?", help="输出文件或目录路径")

    # 处理参数
    parser.add_argument("--quality", type=int, default=85,
                        help="压缩质量 0-100 (默认: 85)")
    parser.add_argument("--output-format", "-f", help="输出格式 (如 .png/.jpg/.webp)")
    parser.add_argument("--prefix", default="", help="输出文件名前缀")

    # 缩放参数
    parser.add_argument("--resize-mode", choices=["none", "width", "height",
                                                  "percent", "longest", "shortest"],
                        default="none", help="缩放模式")
    parser.add_argument("--width", type=int, help="目标宽度")
    parser.add_argument("--height", type=int, help="目标高度")
    parser.add_argument("--percent", type=float, help="缩放百分比")
    parser.add_argument("--longest-edge", type=int, help="最长边目标长度")
    parser.add_argument("--shortest-edge", type=int, help="最短边目标长度")

    # 其他参数
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="递归扫描文件夹")
    parser.add_argument("--no-exif", action="store_true",
                        help="不保留 EXIF 信息")
    parser.add_argument("--json", action="store_true",
                        help="以 JSON 格式输出结果")
    parser.add_argument("--selftest", action="store_true",
                        help="运行自检测试")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 检查 Pillow
    if not HAS_PIL:
        print("错误: 需要安装 Pillow 库", file=sys.stderr)
        print("请运行: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    # 检查输入参数
    if not args.input:
        parser.print_help()
        sys.exit(1)

    # 处理 URL 输入
    input_paths = []
    for item in args.input:
        if item.startswith(("http://", "https://")):
            try:
                downloaded = download_image(item)
                input_paths.append(downloaded)
                print(f"已下载: {item} -> {downloaded}")
            except Exception as e:
                print(f"下载失败: {item} - {str(e)}", file=sys.stderr)
                sys.exit(1)
        else:
            input_paths.append(item)

    # 确定输出路径
    if len(input_paths) == 1 and os.path.isfile(input_paths[0]):
        # 单文件模式
        if args.output:
            output_path = args.output
        else:
            # 默认输出到当前目录
            input_ext = Path(input_paths[0]).suffix
            output_ext = args.output_format or input_ext
            output_path = str(Path(input_paths[0]).with_suffix(output_ext))

        try:
            processor = ImageProcessor(
                quality=args.quality,
                resize_mode=args.resize_mode,
                width=args.width,
                height=args.height,
                percent=args.percent,
                longest_edge=args.longest_edge,
                shortest_edge=args.shortest_edge,
                keep_exif=not args.no_exif
            )
            result = processor.process(input_paths[0], output_path, args.output_format)

            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                status = "✓" if result["status"] == "success" else "✗"
                print(f"{status} {result['input']} -> {result['output']}")
                print(f"  原始大小: {result['original_size']} bytes")
                print(f"  新大小: {result['new_size']} bytes")
                print(f"  压缩比: {result['ratio']:.2%}")
                print(f"  耗时: {result['duration_ms']}ms")

        except Exception as e:
            print(f"错误: {str(e)}", file=sys.stderr)
            sys.exit(1)

    else:
        # 批量模式
        if not args.output:
            print("错误: 批量处理需要指定输出目录", file=sys.stderr)
            sys.exit(1)

        try:
            processor = ImageProcessor(
                quality=args.quality,
                resize_mode=args.resize_mode,
                width=args.width,
                height=args.height,
                percent=args.percent,
                longest_edge=args.longest_edge,
                shortest_edge=args.shortest_edge,
                keep_exif=not args.no_exif
            )
            results = process_batch(
                input_paths, args.output, processor,
                args.output_format, args.prefix, args.recursive
            )

            # 统计结果
            success_count = sum(1 for r in results if r["status"] == "success")
            failed_count = sum(1 for r in results if r["status"] == "failed")

            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print(f"\n处理完成:")
                print(f"  成功: {success_count} 个文件")
                print(f"  失败: {failed_count} 个文件")

                # 显示失败详情
                for r in results:
                    if r["status"] == "failed":
                        print(f"  ✗ {r['input']}: {r.get('error', '未知错误')}")

                # 显示成功详情
                for r in results:
                    if r["status"] == "success":
                        print(f"  ✓ {r['input']} -> {r['output']} "
                              f"({r['original_size']} -> {r['new_size']} bytes, "
                              f"{r['ratio']:.0%})")

        except Exception as e:
            print(f"错误: {str(e)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
