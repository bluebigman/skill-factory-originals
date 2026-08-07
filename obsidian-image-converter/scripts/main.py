#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obsidian-image-converter 独立实现脚本
=====================================
基于功能规格的 clean-room 重写，仅依赖标准库。

核心能力：
- 图片格式转换、压缩、缩放、裁剪、旋转、翻转、标注等
- 批量处理
- 置信度评估
- 错误码体系 E001-E010

自检：
    python scripts/main.py --selftest
"""

import argparse
import base64
import io
import json
import math
import os
import sys
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 尝试导入 Pillow（仅在实际处理图片时需要）
try:
    from PIL import Image, ImageDraw, ImageOps, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ============================================================
# 错误码定义
# ============================================================
class ErrorCode(Enum):
    E001_INPUT_EMPTY = "E001"
    E002_KEY_INFO_MISSING = "E002"
    E003_INPUT_FORMAT_ERROR = "E003"
    E004_OUT_OF_SCOPE = "E004"
    E005_LOW_CONFIDENCE = "E005"
    E006_IMAGE_LOAD_FAILED = "E006"
    E007_IMAGE_SAVE_FAILED = "E007"
    E008_UNSUPPORTED_FORMAT = "E008"
    E009_PROCESSING_FAILED = "E009"
    E010_INTERNAL_ERROR = "E010"


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ImageInfo:
    """图片基本信息"""
    width: int = 0
    height: int = 0
    format: str = ""
    mode: str = ""
    size_bytes: int = 0


@dataclass
class ProcessingOptions:
    """处理选项"""
    convert_format: Optional[str] = None      # 目标格式
    quality: int = 85                          # 压缩质量 1-100
    resize: Optional[Tuple[int, int]] = None   # (宽, 高)
    crop: Optional[Tuple[int, int, int, int]] = None  # (left, top, right, bottom)
    rotate: int = 0                            # 旋转角度
    flip_h: bool = False                       # 水平翻转
    flip_v: bool = False                       # 垂直翻转
    grayscale: bool = False                    # 灰度化
    annotate: Optional[str] = None             # 标注文字
    output_dir: Optional[str] = None           # 输出目录


@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool = False
    output_path: Optional[str] = None
    image_info: Optional[ImageInfo] = None
    confidence: float = 0.0
    error_code: Optional[str] = None
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理类
# ============================================================
class ImageConverter:
    """图片转换器 - 核心处理逻辑"""

    SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "bmp", "gif", "webp", "tiff"}

    def __init__(self) -> None:
        self._pil_available = HAS_PIL
        if not self._pil_available:
            print("警告: Pillow 未安装，图片处理功能不可用。请执行: pip install Pillow")

    # --------------------------------------------------------
    # 公共接口
    # --------------------------------------------------------
    def process_image(
        self,
        input_path: str,
        options: ProcessingOptions,
        output_path: Optional[str] = None,
    ) -> ProcessingResult:
        """处理单张图片"""
        result = ProcessingResult()

        # 输入校验
        if not input_path or not os.path.exists(input_path):
            result.error_code = ErrorCode.E001_INPUT_EMPTY.value
            result.error_message = "输入文件不存在或为空"
            return result

        if not self._pil_available:
            result.error_code = ErrorCode.E009_PROCESSING_FAILED.value
            result.error_message = "Pillow 库未安装，无法处理图片"
            return result

        try:
            # 加载图片
            img, img_info = self._load_image(input_path)
            if img is None:
                result.error_code = ErrorCode.E006_IMAGE_LOAD_FAILED.value
                result.error_message = f"无法加载图片: {input_path}"
                return result

            # 应用处理
            img, warnings = self._apply_options(img, options)

            # 保存结果
            if output_path is None:
                output_path = self._generate_output_path(input_path, options)

            save_ok = self._save_image(img, output_path, options)
            if not save_ok:
                result.error_code = ErrorCode.E007_IMAGE_SAVE_FAILED.value
                result.error_message = f"保存图片失败: {output_path}"
                return result

            # 填充结果
            result.success = True
            result.output_path = output_path
            result.image_info = self._get_image_info(output_path)
            result.confidence = self._calculate_confidence(options)
            result.warnings = warnings

        except Exception as e:
            result.error_code = ErrorCode.E010_INTERNAL_ERROR.value
            result.error_message = f"处理失败: {str(e)}"

        return result

    def process_batch(
        self,
        input_paths: List[str],
        options: ProcessingOptions,
        output_dir: Optional[str] = None,
    ) -> List[ProcessingResult]:
        """批量处理图片"""
        results = []
        for path in input_paths:
            result = self.process_image(path, options, output_dir)
            results.append(result)
        return results

    # --------------------------------------------------------
    # 内部方法 - 加载和保存
    # --------------------------------------------------------
    def _load_image(self, path: str) -> Tuple[Optional[Any], Optional[ImageInfo]]:
        """加载图片并获取基本信息"""
        try:
            img = Image.open(path)
            img.load()  # 确保数据加载
            info = ImageInfo(
                width=img.width,
                height=img.height,
                format=img.format.lower() if img.format else "",
                mode=img.mode,
                size_bytes=os.path.getsize(path),
            )
            return img, info
        except Exception:
            return None, None

    def _save_image(self, img: Any, path: str, options: ProcessingOptions) -> bool:
        """保存图片"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

            # 确定保存格式
            fmt = options.convert_format or "png"
            if fmt.lower() in ("jpg", "jpeg"):
                img.save(path, "JPEG", quality=options.quality, optimize=True)
            elif fmt.lower() == "png":
                img.save(path, "PNG", optimize=True)
            elif fmt.lower() == "bmp":
                img.save(path, "BMP")
            elif fmt.lower() == "gif":
                img.save(path, "GIF")
            elif fmt.lower() == "webp":
                img.save(path, "WEBP", quality=options.quality)
            elif fmt.lower() == "tiff":
                img.save(path, "TIFF")
            else:
                img.save(path)
            return True
        except Exception:
            return False

    # --------------------------------------------------------
    # 内部方法 - 处理选项
    # --------------------------------------------------------
    def _apply_options(self, img: Any, options: ProcessingOptions) -> Tuple[Any, List[str]]:
        """应用处理选项，返回处理后的图片和警告列表"""
        warnings = []
        current = img

        # 格式转换
        if options.convert_format:
            fmt = options.convert_format.lower()
            if fmt not in self.SUPPORTED_FORMATS:
                warnings.append(f"不支持的格式: {fmt}，使用原始格式")
            else:
                current = current.convert("RGB" if fmt in ("jpg", "jpeg") else current.mode)

        # 裁剪
        if options.crop:
            try:
                left, top, right, bottom = options.crop
                current = current.crop((left, top, right, bottom))
            except Exception:
                warnings.append("裁剪参数无效，已跳过")

        # 旋转
        if options.rotate:
            try:
                current = current.rotate(options.rotate, expand=True)
            except Exception:
                warnings.append("旋转参数无效，已跳过")

        # 翻转
        if options.flip_h:
            current = current.transpose(Image.FLIP_LEFT_RIGHT)
        if options.flip_v:
            current = current.transpose(Image.FLIP_TOP_BOTTOM)

        # 缩放
        if options.resize:
            try:
                w, h = options.resize
                if w > 0 and h > 0:
                    current = current.resize((w, h), Image.LANCZOS)
                else:
                    warnings.append("缩放参数无效，已跳过")
            except Exception:
                warnings.append("缩放失败，已跳过")

        # 灰度化
        if options.grayscale:
            current = current.convert("L")

        # 标注
        if options.annotate:
            try:
                draw = ImageDraw.Draw(current)
                draw.text((10, 10), options.annotate, fill="red")
            except Exception:
                warnings.append("标注失败，已跳过")

        return current, warnings

    # --------------------------------------------------------
    # 内部方法 - 辅助功能
    # --------------------------------------------------------
    def _generate_output_path(self, input_path: str, options: ProcessingOptions) -> str:
        """生成输出文件路径"""
        base, _ = os.path.splitext(input_path)
        fmt = options.convert_format or "png"
        if options.output_dir:
            base = os.path.join(options.output_dir, os.path.basename(base))
        return f"{base}_processed.{fmt}"

    def _get_image_info(self, path: str) -> Optional[ImageInfo]:
        """获取图片信息"""
        try:
            img = Image.open(path)
            return ImageInfo(
                width=img.width,
                height=img.height,
                format=img.format.lower() if img.format else "",
                mode=img.mode,
                size_bytes=os.path.getsize(path),
            )
        except Exception:
            return None

    def _calculate_confidence(self, options: ProcessingOptions) -> float:
        """计算处理置信度"""
        confidence = 1.0
        # 简单规则：选项越多，置信度越低（因为不确定性增加）
        if options.crop:
            confidence -= 0.1
        if options.rotate:
            confidence -= 0.05
        if options.resize:
            confidence -= 0.05
        if options.annotate:
            confidence -= 0.1
        if options.flip_h or options.flip_v:
            confidence -= 0.05
        if options.grayscale:
            confidence -= 0.05
        if options.quality < 70:
            confidence -= 0.1
        return max(0.5, min(1.0, confidence))


# ============================================================
# 命令行接口
# ============================================================
def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="图片批量处理工具 - obsidian-image-converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input",
        nargs="*",
        help="输入图片路径（支持多个，批量处理）",
    )
    parser.add_argument(
        "--convert",
        choices=["png", "jpg", "jpeg", "bmp", "gif", "webp", "tiff"],
        help="目标格式",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="压缩质量 1-100，默认 85",
    )
    parser.add_argument(
        "--resize",
        nargs=2,
        type=int,
        metavar=("WIDTH", "HEIGHT"),
        help="缩放尺寸",
    )
    parser.add_argument(
        "--crop",
        nargs=4,
        type=int,
        metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
        help="裁剪区域",
    )
    parser.add_argument(
        "--rotate",
        type=int,
        default=0,
        help="旋转角度",
    )
    parser.add_argument(
        "--flip-h",
        action="store_true",
        help="水平翻转",
    )
    parser.add_argument(
        "--flip-v",
        action="store_true",
        help="垂直翻转",
    )
    parser.add_argument(
        "--grayscale",
        action="store_true",
        help="灰度化",
    )
    parser.add_argument(
        "--annotate",
        help="标注文字",
    )
    parser.add_argument(
        "--output-dir",
        help="输出目录",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检（内置样例数据，离线）",
    )

    return parser.parse_args()


def build_options(args: argparse.Namespace) -> ProcessingOptions:
    """从命令行参数构建处理选项"""
    options = ProcessingOptions(
        convert_format=args.convert,
        quality=args.quality,
        resize=tuple(args.resize) if args.resize else None,
        crop=tuple(args.crop) if args.crop else None,
        rotate=args.rotate,
        flip_h=args.flip_h,
        flip_v=args.flip_v,
        grayscale=args.grayscale,
        annotate=args.annotate,
        output_dir=args.output_dir,
    )
    return options


def print_result(result: ProcessingResult) -> None:
    """打印处理结果"""
    if result.success:
        print(f"✅ 成功: {result.output_path}")
        if result.image_info:
            info = result.image_info
            print(f"   尺寸: {info.width}x{info.height}")
            print(f"   格式: {info.format}")
            print(f"   大小: {info.size_bytes} 字节")
        print(f"   置信度: {result.confidence:.1%}")
        if result.warnings:
            print(f"   警告: {', '.join(result.warnings)}")
    else:
        print(f"❌ 失败 [{result.error_code}]: {result.error_message}")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """运行自检（内置硬编码样例数据，离线）"""
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 检查 Pillow 可用性
    if not HAS_PIL:
        print("⚠️  Pillow 未安装，跳过图片处理测试")
        print("    执行: pip install Pillow")
        print("=" * 60)
        return False

    # 创建临时图片（内存中）
    test_image = _create_test_image()
    if test_image is None:
        print("❌ 测试图片创建失败")
        return False

    # 保存到临时文件
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "test_input.png")
        test_image.save(input_path, "PNG")

        converter = ImageConverter()

        # 测试1: 基本格式转换
        print("\n[测试1] PNG -> JPEG 转换")
        options = ProcessingOptions(convert_format="jpg", quality=75)
        result = converter.process_image(input_path, options)
        assert result.success, f"格式转换失败: {result.error_message}"
        assert result.output_path and result.output_path.endswith(".jpg"), "输出格式错误"
        assert result.confidence > 0.5, "置信度过低"
        print(f"  ✅ 通过 (置信度: {result.confidence:.1%})")

        # 测试2: 缩放
        print("\n[测试2] 图片缩放")
        options = ProcessingOptions(resize=(100, 100))
        result = converter.process_image(input_path, options)
        assert result.success, f"缩放失败: {result.error_message}"
        assert result.image_info and result.image_info.width == 100, "宽度错误"
        assert result.image_info and result.image_info.height == 100, "高度错误"
        print(f"  ✅ 通过 (尺寸: {result.image_info.width}x{result.image_info.height})")

        # 测试3: 旋转
        print("\n[测试3] 图片旋转 90 度")
        options = ProcessingOptions(rotate=90)
        result = converter.process_image(input_path, options)
        assert result.success, f"旋转失败: {result.error_message}"
        assert result.image_info and result.image_info.width > 0, "旋转后无效"
        print(f"  ✅ 通过 (尺寸: {result.image_info.width}x{result.image_info.height})")

        # 测试4: 批量处理
        print("\n[测试4] 批量处理")
        input_paths = [input_path, input_path]  # 同一文件两次
        options = ProcessingOptions(convert_format="bmp")
        results = converter.process_batch(input_paths, options)
        assert len(results) == 2, "批量处理数量错误"
        assert all(r.success for r in results), "批量处理存在失败"
        print(f"  ✅ 通过 ({len(results)} 个文件)")

        # 测试5: 错误处理
        print("\n[测试5] 错误处理")
        result = converter.process_image("/nonexistent/path.png", ProcessingOptions())
        assert not result.success, "不存在的文件应该失败"
        assert result.error_code == ErrorCode.E001_INPUT_EMPTY.value, "错误码错误"
        print(f"  ✅ 通过 (错误码: {result.error_code})")

        # 测试6: 组合处理
        print("\n[测试6] 组合处理 (缩放+灰度+翻转)")
        options = ProcessingOptions(
            resize=(50, 50),
            grayscale=True,
            flip_h=True,
            quality=80,
        )
        result = converter.process_image(input_path, options)
        assert result.success, f"组合处理失败: {result.error_message}"
        assert result.image_info and result.image_info.mode == "L", "灰度模式错误"
        print(f"  ✅ 通过 (模式: {result.image_info.mode}, 尺寸: {result.image_info.width}x{result.image_info.height})")

        # 测试7: 裁剪
        print("\n[测试7] 图片裁剪")
        options = ProcessingOptions(crop=(10, 10, 50, 50))
        result = converter.process_image(input_path, options)
        assert result.success, f"裁剪失败: {result.error_message}"
        assert result.image_info and result.image_info.width == 40, "裁剪宽度错误"
        assert result.image_info and result.image_info.height == 40, "裁剪高度错误"
        print(f"  ✅ 通过 (尺寸: {result.image_info.width}x{result.image_info.height})")

        # 测试8: 置信度计算
        print("\n[测试8] 置信度计算")
        simple_options = ProcessingOptions()
        complex_options = ProcessingOptions(
            crop=(1, 1, 10, 10),
            rotate=45,
            resize=(100, 100),
            annotate="test",
            quality=50,
        )
        simple_conf = converter._calculate_confidence(simple_options)
        complex_conf = converter._calculate_confidence(complex_options)
        assert simple_conf > complex_conf, "简单操作的置信度应更高"
        assert 0.5 <= complex_conf <= 1.0, "置信度范围错误"
        print(f"  ✅ 通过 (简单: {simple_conf:.1%}, 复杂: {complex_conf:.1%})")

        print("\n" + "=" * 60)
        print("✅ 所有自检通过！")
        print("=" * 60)
        return True


def _create_test_image() -> Optional[Any]:
    """创建测试图片（内存中）"""
    try:
        # 创建 200x150 的测试图片
        img = Image.new("RGB", (200, 150), color=(73, 109, 137))
        draw = ImageDraw.Draw(img)
        # 画一些形状
        draw.rectangle([50, 50, 150, 100], fill=(255, 255, 255))
        draw.ellipse([75, 25, 125, 75], fill=(255, 0, 0))
        draw.line([(0, 0), (199, 149)], fill=(0, 255, 0), width=3)
        return img
    except Exception:
        return None


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主函数"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 检查输入
    if not args.input:
        print(f"错误 [{ErrorCode.E001_INPUT_EMPTY.value}]: 请提供输入图片路径")
        print("用法: python main.py <图片路径> [选项]")
        print("示例: python main.py image.png --convert jpg --quality 80")
        print("      python main.py img1.png img2.png --resize 800 600")
        return 1

    # 检查 Pillow
    if not HAS_PIL:
        print(f"错误 [{ErrorCode.E009_PROCESSING_FAILED.value}]: Pillow 库未安装")
        print("请执行: pip install Pillow")
        return 1

    # 构建选项
    options = build_options(args)

    # 处理图片
    converter = ImageConverter()
    results = converter.process_batch(args.input, options, args.output_dir)

    # 输出结果
    print("\n处理结果:")
    print("-" * 60)
    success_count = 0
    for result in results:
        print_result(result)
        if result.success:
            success_count += 1
        print()

    # 汇总
    print("-" * 60)
    print(f"总计: {len(results)} 个文件, 成功: {success_count}, 失败: {len(results) - success_count}")

    # 检查是否有错误
    for result in results:
        if not result.success and result.error_code in (
            ErrorCode.E004_OUT_OF_SCOPE.value,
            ErrorCode.E005_LOW_CONFIDENCE.value,
        ):
            print(f"\n⚠️  建议: 错误 {result.error_code} 可能需要人工复核")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
