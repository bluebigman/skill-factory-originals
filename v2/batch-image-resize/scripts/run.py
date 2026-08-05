#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量图片处理工具 - 缩放/压缩/格式转换/EXIF处理
支持 JPEG/PNG/WebP 格式，自动处理目录归档
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# 尝试导入 Pillow，处理依赖缺失
try:
    from PIL import Image, ImageOps
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None
    ImageOps = None
    TAGS = None

# 支持的输入/输出格式
SUPPORTED_INPUT_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
SUPPORTED_OUTPUT_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}


def check_dependencies():
    """检查 Pillow 依赖是否可用"""
    if not HAS_PIL:
        print("错误: 需要 Pillow 库来处理图片。请安装: pip install Pillow", file=sys.stderr)
        sys.exit(1)


def get_exif_data(img):
    """提取图片 EXIF 信息"""
    exif_data = {}
    try:
        exif = img._getexif()
        if exif:
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                exif_data[tag_name] = value
    except (AttributeError, TypeError, KeyError):
        pass
    return exif_data


def strip_exif(img):
    """剥离 EXIF 信息，返回新图片"""
    # 创建不含 EXIF 的新图片
    data = list(img.getdata())
    new_img = Image.new(img.mode, img.size)
    new_img.putdata(data)
    return new_img


def process_image(input_path, output_path, args):
    """
    处理单张图片
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    :param args: 命令行参数
    :return: (是否成功, 错误信息)
    """
    try:
        # 打开图片
        img = Image.open(input_path)
        
        # 处理 EXIF 方向（自动旋转）
        img = ImageOps.exif_transpose(img)
        
        # 记录原始 EXIF
        original_exif = None
        if not args.strip_exif:
            original_exif = img.info.get('exif', b'')
        
        # 计算目标尺寸
        target_width = args.width
        target_height = args.height
        
        if args.scale:
            # 按百分比缩放
            scale_percent = float(args.scale.rstrip('%')) / 100.0
            target_width = int(img.width * scale_percent)
            target_height = int(img.height * scale_percent)
        elif target_width and not target_height:
            # 只指定宽度，按比例计算高度
            ratio = target_width / img.width
            target_height = int(img.height * ratio)
        elif target_height and not target_width:
            # 只指定高度，按比例计算宽度
            ratio = target_height / img.height
            target_width = int(img.width * ratio)
        elif not target_width and not target_height:
            # 未指定尺寸，保持原尺寸
            target_width = img.width
            target_height = img.height
        
        # 确保尺寸为正数
        target_width = max(1, target_width)
        target_height = max(1, target_height)
        
        # 调整尺寸（使用高质量重采样）
        if (target_width, target_height) != img.size:
            img = img.resize((target_width, target_height), Image.LANCZOS)
        
        # 确定输出格式
        output_format = args.format.lower()
        if output_format:
            # 转换格式
            if output_format in ('jpg', 'jpeg'):
                output_format = 'JPEG'
                # JPEG 不支持透明，转为 RGB
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
            elif output_format == 'png':
                output_format = 'PNG'
            elif output_format == 'webp':
                output_format = 'WEBP'
            else:
                print(f"错误: 不支持的输出格式: {args.format}", file=sys.stderr)
                return False, f"不支持的输出格式: {args.format}"
        else:
            # 保持原格式
            output_format = img.format or 'JPEG'
            if output_format == 'JPEG' and img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
        
        # 处理 EXIF
        if args.strip_exif:
            img = strip_exif(img)
        elif original_exif:
            # 保留 EXIF（仅 JPEG 支持）
            if output_format == 'JPEG':
                img.save(output_path, format=output_format, quality=args.quality, exif=original_exif)
                return True, None
        
        # 保存图片
        save_kwargs = {'format': output_format}
        if output_format in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = args.quality
        if output_format == 'PNG':
            save_kwargs['optimize'] = True
        
        img.save(output_path, **save_kwargs)
        return True, None
        
    except Exception as e:
        return False, str(e)


def find_images(input_dir, recursive=False):
    """查找目录下的所有图片文件"""
    images = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"错误: 输入目录不存在: {input_dir}", file=sys.stderr)
        sys.exit(1)
    
    if input_path.is_file():
        # 输入是单个文件
        if input_path.suffix.lower() in SUPPORTED_INPUT_FORMATS:
            images.append(input_path)
        else:
            print(f"错误: 不支持的图片格式: {input_path.suffix}", file=sys.stderr)
            sys.exit(1)
    else:
        # 输入是目录
        pattern = '**/*' if recursive else '*'
        for file_path in input_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_INPUT_FORMATS:
                images.append(file_path)
    
    return images


def main():
    parser = argparse.ArgumentParser(
        description='批量图片处理工具 - 缩放、压缩、格式转换、EXIF处理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 批量缩放到 50%
  python run.py --input ./images/ --output ./processed/ --scale 50%
  
  # 指定宽度，保持比例
  python run.py --input ./images/ --output ./processed/ --width 1920
  
  # 压缩为 JPEG，质量 70
  python run.py --input ./images/ --output ./processed/ --quality 70 --format jpeg
  
  # 转换为 WebP，剥离 EXIF
  python run.py --input ./images/ --output ./processed/ --format webp --strip-exif
  
  # 递归处理子目录
  python run.py --input ./images/ --output ./processed/ --scale 50% --recursive
        '''
    )
    
    parser.add_argument('--input', '-i', required=True, help='输入目录或图片文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出目录路径')
    parser.add_argument('--width', type=int, help='目标宽度（像素）')
    parser.add_argument('--height', type=int, help='目标高度（像素）')
    parser.add_argument('--scale', help='缩放百分比，如 50%')
    parser.add_argument('--quality', type=int, default=85, help='压缩质量（1-100），默认 85')
    parser.add_argument('--format', choices=['jpg', 'jpeg', 'png', 'webp'], help='输出格式')
    parser.add_argument('--strip-exif', action='store_true', help='剥离 EXIF 信息')
    parser.add_argument('--keep-exif', action='store_true', help='保留 EXIF 信息（默认）')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    args = parser.parse_args()
    
    # 检查依赖
    check_dependencies()
    
    # 参数校验
    if args.width and args.width <= 0:
        print("错误: --width 必须为正整数", file=sys.stderr)
        sys.exit(1)
    if args.height and args.height <= 0:
        print("错误: --height 必须为正整数", file=sys.stderr)
        sys.exit(1)
    if args.quality < 1 or args.quality > 100:
        print("错误: --quality 必须在 1-100 之间", file=sys.stderr)
        sys.exit(1)
    if args.scale:
        try:
            scale_val = float(args.scale.rstrip('%'))
            if scale_val <= 0:
                raise ValueError
        except ValueError:
            print(f"错误: 无效的缩放比例: {args.scale}，应为正数百分比如 50%", file=sys.stderr)
            sys.exit(1)
    if args.strip_exif and args.keep_exif:
        print("错误: --strip-exif 和 --keep-exif 不能同时使用", file=sys.stderr)
        sys.exit(1)
    
    # 创建输出目录
    output_dir = Path(args.output)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(f"错误: 无法创建输出目录: {args.output}（权限不足）", file=sys.stderr)
        sys.exit(1)
    
    # 查找图片
    images = find_images(args.input, args.recursive)
    if not images:
        print(f"警告: 在 {args.input} 中未找到支持的图片文件", file=sys.stderr)
        sys.exit(1)
    
    # 处理图片
    success_count = 0
    fail_count = 0
    total_size_before = 0
    total_size_after = 0
    
    print(f"开始处理 {len(images)} 张图片...")
    print(f"输出目录: {output_dir}")
    print("-" * 60)
    
    for img_path in images:
        # 计算输出文件名
        if args.format:
            # 转换格式时改变扩展名
            ext_map = {'jpg': '.jpg', 'jpeg': '.jpg', 'png': '.png', 'webp': '.webp'}
            output_filename = img_path.stem + ext_map[args.format]
        else:
            # 保持原格式
            output_filename = img_path.name
        
        # 处理子目录结构
        if args.recursive and img_path.parent != Path(args.input):
            # 保留相对路径结构
            rel_path = img_path.parent.relative_to(args.input)
            target_dir = output_dir / rel_path
            target_dir.mkdir(parents=True, exist_ok=True)
            output_path = target_dir / output_filename
        else:
            output_path = output_dir / output_filename
        
        # 检查输出文件是否已存在
        if output_path.exists():
            print(f"跳过: {img_path.name} -> 输出文件已存在: {output_path.name}")
            continue
        
        # 记录原文件大小
        size_before = img_path.stat().st_size
        total_size_before += size_before
        
        # 处理图片
        success, error = process_image(str(img_path), str(output_path), args)
        
        if success:
            size_after = output_path.stat().st_size
            total_size_after += size_after
            success_count += 1
            reduction = (1 - size_after / size_before) * 100 if size_before > 0 else 0
            print(f"✓ {img_path.name} -> {output_path.name} ({size_before/1024:.1f}KB -> {size_after/1024:.1f}KB, 减少 {reduction:.1f}%)")
        else:
            fail_count += 1
            print(f"✗ {img_path.name} 处理失败: {error}", file=sys.stderr)
    
    # 输出统计信息
    print("-" * 60)
    print(f"处理完成: 成功 {success_count} 张, 失败 {fail_count} 张")
    if success_count > 0:
        total_reduction = (1 - total_size_after / total_size_before) * 100 if total_size_before > 0 else 0
        print(f"总大小: {total_size_before/1024/1024:.2f}MB -> {total_size_after/1024/1024:.2f}MB (减少 {total_reduction:.1f}%)")
    
    # 如果有失败，返回非零退出码
    if fail_count > 0:
        sys.exit(1)


def selftest():
    """自检函数 - 不联网，纯本地测试"""
    print("运行自检...")
    
    # 检查依赖
    if not HAS_PIL:
        print("✗ Pillow 未安装", file=sys.stderr)
        return False
    
    print("✓ Pillow 已安装")
    
    # 创建测试图片
    test_dir = Path("./selftest_tmp")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # 创建测试图片
        test_img = Image.new('RGB', (200, 100), color='red')
        test_path = test_dir / "test.jpg"
        test_img.save(test_path, 'JPEG', quality=95)
        
        # 测试缩放
        output_path = test_dir / "test_resized.jpg"
        args = argparse.Namespace(
            width=100, height=None, scale=None, quality=80,
            format=None, strip_exif=False, keep_exif=True
        )
        success, error = process_image(str(test_path), str(output_path), args)
        if not success:
            print(f"✗ 缩放测试失败: {error}", file=sys.stderr)
            return False
        
        # 验证尺寸
        with Image.open(output_path) as img:
            if img.size != (100, 50):
                print(f"✗ 缩放尺寸错误: {img.size}", file=sys.stderr)
                return False
        print("✓ 缩放测试通过")
        
        # 测试格式转换
        output_path = test_dir / "test.webp"
        args = argparse.Namespace(
            width=None, height=None, scale=None, quality=80,
            format='webp', strip_exif=False, keep_exif=True
        )
        success, error = process_image(str(test_path), str(output_path), args)
        if not success:
            print(f"✗ 格式转换测试失败: {error}", file=sys.stderr)
            return False
        
        if not output_path.exists():
            print("✗ 格式转换输出文件不存在", file=sys.stderr)
            return False
        print("✓ 格式转换测试通过")
        
        # 测试 EXIF 剥离
        output_path = test_dir / "test_noexif.jpg"
        args = argparse.Namespace(
            width=None, height=None, scale=None, quality=80,
            format=None, strip_exif=True, keep_exif=False
        )
        success, error = process_image(str(test_path), str(output_path), args)
        if not success:
            print(f"✗ EXIF 剥离测试失败: {error}", file=sys.stderr)
            return False
        print("✓ EXIF 剥离测试通过")
        
        print("✓ 所有自检测试通过")
        return True
        
    finally:
        # 清理测试文件
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    # 支持 --selftest 参数
    if '--selftest' in sys.argv:
        if selftest():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        main()
