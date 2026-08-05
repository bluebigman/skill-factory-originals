#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_resize.py - 图片批处理工具

功能：
- 批量调整图片尺寸（按宽度/高度/百分比/指定宽高）
- 格式转换（jpg/png/webp/bmp 互转）
- 质量压缩（JPEG/WebP）
- 处理前预览摘要，处理中自动备份原图元数据
- 支持回滚（处理失败不影响原图）

用法示例：
    python batch_resize.py --input ./input --output_format jpg --quality 70
    python batch_resize.py --input ./assets --width 800
    python batch_resize.py --input ./photos --width 800
    python batch_resize.py --input "$dir" --width 1200
"""

import os
import sys
import shutil
import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    from PIL import UnidentifiedImageError
except ImportError:
    print("错误: 需要 Pillow 库。请执行: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# 支持的图片格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
# 输出格式映射
FORMAT_MAP = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
    'bmp': 'BMP'
}
# 单张图片大小限制（50MB）
MAX_FILE_SIZE = 50 * 1024 * 1024
# 批量处理上限
MAX_BATCH_SIZE = 500


def get_image_files(input_path):
    """获取输入路径下的所有图片文件"""
    path = Path(input_path)
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(f"不支持的图片格式: {path.suffix}，仅支持 {SUPPORTED_FORMATS}")
        return [path]
    elif path.is_dir():
        files = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_FORMATS]
        if len(files) > MAX_BATCH_SIZE:
            raise ValueError(f"图片数量超过上限 {MAX_BATCH_SIZE} 张，请分批处理")
        return files
    else:
        raise FileNotFoundError(f"输入路径不存在: {input_path}")


def check_file_size(file_path):
    """检查文件大小是否超过限制"""
    size = os.path.getsize(file_path)
    if size > MAX_FILE_SIZE:
        raise ValueError(f"文件 {file_path.name} 大小 {size/1024/1024:.1f}MB 超过 50MB 限制，已跳过")


def resize_image(img, width=None, height=None, percent=None):
    """调整图片尺寸"""
    orig_w, orig_h = img.size
    
    if percent is not None:
        new_w = int(orig_w * percent / 100)
        new_h = int(orig_h * percent / 100)
    elif width is not None and height is not None:
        new_w, new_h = width, height
    elif width is not None:
        ratio = width / orig_w
        new_w = width
        new_h = int(orig_h * ratio)
    elif height is not None:
        ratio = height / orig_h
        new_h = height
        new_w = int(orig_w * ratio)
    else:
        return img
    
    # 确保尺寸为正整数
    new_w = max(1, new_w)
    new_h = max(1, new_h)
    
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def process_image(file_path, output_dir, output_format=None, width=None, height=None, percent=None, quality=None):
    """处理单张图片"""
    # 检查文件大小
    check_file_size(file_path)
    
    # 打开图片
    try:
        img = Image.open(file_path)
        img.load()  # 加载数据，确保文件可读
    except UnidentifiedImageError:
        raise ValueError(f"无法识别图片文件: {file_path.name}")
    except Exception as e:
        raise ValueError(f"打开图片失败 {file_path.name}: {str(e)}")
    
    # 记录原始信息用于回滚
    backup_info = {
        'original_path': str(file_path),
        'original_size': img.size,
        'original_format': img.format,
        'original_mode': img.mode,
        'processed_at': datetime.now().isoformat()
    }
    
    # 调整尺寸
    img = resize_image(img, width, height, percent)
    
    # 确定输出格式
    if output_format is None:
        # 默认保持原格式
        out_format = img.format if img.format in FORMAT_MAP.values() else 'JPEG'
        out_ext = Path(file_path).suffix.lower()
    else:
        out_format = FORMAT_MAP[output_format]
        out_ext = f".{output_format}"
    
    # 处理透明度（JPEG不支持透明通道）
    if out_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
        # 转换为RGB，白色背景
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成输出文件名（避免覆盖原图）
    base_name = file_path.stem
    output_path = output_dir / f"{base_name}{out_ext}"
    counter = 1
    while output_path.exists():
        output_path = output_dir / f"{base_name}_{counter}{out_ext}"
        counter += 1
    
    # 保存图片
    save_kwargs = {}
    if out_format in ('JPEG', 'WEBP') and quality is not None:
        save_kwargs['quality'] = quality
    
    try:
        img.save(output_path, format=out_format, **save_kwargs)
    except Exception as e:
        raise ValueError(f"保存图片失败 {output_path.name}: {str(e)}")
    
    # 保存备份信息（用于回滚）
    backup_file = output_path.with_suffix('.json')
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_info, f, ensure_ascii=False, indent=2)
    
    return output_path, backup_info


def print_preview(files, output_dir, output_format, width, height, percent, quality):
    """打印处理预览"""
    print("\n" + "="*60)
    print("图片批处理预览")
    print("="*60)
    print(f"输入路径: {files[0].parent if files else 'N/A'}")
    print(f"图片数量: {len(files)} 张")
    print(f"输出目录: {output_dir}")
    print(f"输出格式: {output_format if output_format else '保持原格式'}")
    if width:
        print(f"宽度: {width}px")
    if height:
        print(f"高度: {height}px")
    if percent:
        print(f"缩放比例: {percent}%")
    if quality:
        print(f"压缩质量: {quality}")
    print("="*60)
    
    # 列出前5张图片
    print("待处理图片（前5张）:")
    for f in files[:5]:
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f"  - {f.name} ({size_mb:.1f}MB)")
    if len(files) > 5:
        print(f"  ... 等共 {len(files)} 张")
    
    # 确认
    try:
        confirm = input("\n确认处理？(y/N): ").strip().lower()
        return confirm in ('y', 'yes')
    except (KeyboardInterrupt, EOFError):
        return False


def selftest():
    """自检函数 - 不联网，本地测试核心功能"""
    print("运行自检...")
    
    # 创建临时测试目录
    import tempfile
    test_dir = Path(tempfile.mkdtemp(prefix="batch_resize_test_"))
    input_dir = test_dir / "input"
    output_dir = test_dir / "output"
    input_dir.mkdir()
    
    try:
        # 创建测试图片
        test_img = Image.new('RGB', (100, 50), color=(255, 0, 0))
        test_img.save(input_dir / "test1.png")
        test_img.save(input_dir / "test2.jpg", quality=90)
        
        # 测试1: 按宽度缩放
        files = get_image_files(input_dir)
        assert len(files) == 2, "应找到2张图片"
        
        # 测试2: 处理图片
        out_path, info = process_image(files[0], output_dir, width=50)
        assert out_path.exists(), "输出文件应存在"
        with Image.open(out_path) as img:
            assert img.size == (50, 25), f"尺寸应为 (50,25)，实际 {img.size}"
        
        # 测试3: 格式转换
        out_path2, _ = process_image(files[1], output_dir, output_format='png')
        assert out_path2.suffix == '.png', "输出应为PNG格式"
        
        # 测试4: 质量压缩
        out_path3, _ = process_image(files[1], output_dir, quality=50)
        assert out_path3.exists(), "压缩输出应存在"
        
        # 测试5: 错误处理 - 不存在的文件
        try:
            get_image_files(test_dir / "nonexistent")
            assert False, "应抛出文件不存在错误"
        except FileNotFoundError:
            pass
        
        # 测试6: 不支持的文件格式
        bad_file = input_dir / "test.txt"
        bad_file.write_text("not an image")
        try:
            get_image_files(bad_file)
            assert False, "应抛出格式不支持错误"
        except ValueError:
            pass
        
        print("✓ 所有自检测试通过！")
        return True
        
    except AssertionError as e:
        print(f"✗ 自检失败: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ 自检异常: {e}", file=sys.stderr)
        return False
    finally:
        # 清理临时目录
        shutil.rmtree(test_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="图片批处理工具 - 批量调整尺寸、转换格式、压缩质量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python batch_resize.py --input ./input --output_format jpg --quality 70
  python batch_resize.py --input ./assets --width 800
  python batch_resize.py --input ./photos --width 800
  python batch_resize.py --input "$dir" --width 1200
        """
    )
    
    # 输入参数
    parser.add_argument('--input', '-i', required=True, help='输入文件夹路径或单文件路径')
    parser.add_argument('--output', '-o', help='输出目录（默认: 输入目录下的 output/）')
    
    # 尺寸调整参数（四选一）
    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument('--width', type=int, help='按指定宽度等比缩放')
    size_group.add_argument('--height', type=int, help='按指定高度等比缩放')
    size_group.add_argument('--percent', type=int, help='按百分比缩放（如 50 表示 50%）')
    size_group.add_argument('--size', nargs=2, type=int, metavar=('W', 'H'), help='指定宽高（如 --size 800 600）')
    
    # 格式和质量参数
    parser.add_argument('--output_format', choices=['jpg', 'jpeg', 'png', 'webp', 'bmp'], help='输出格式')
    parser.add_argument('--quality', type=int, choices=range(1, 96), help='压缩质量（1-95，仅对 JPEG/WebP 有效）')
    
    # 其他参数
    parser.add_argument('--preview', action='store_true', help='仅显示预览，不实际处理')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    parser.add_argument('--version', action='version', version='batch_resize 1.0.0')
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    
    # 参数校验
    if not args.width and not args.height and not args.percent and not args.size:
        print("错误: 必须指定一种尺寸调整方式（--width/--height/--percent/--size）", file=sys.stderr)
        sys.exit(1)
    
    if args.quality and args.output_format not in ('jpg', 'jpeg', 'webp', None):
        print("警告: quality 参数仅对 JPEG/WebP 格式有效，将忽略", file=sys.stderr)
    
    try:
        # 获取图片文件列表
        files = get_image_files(args.input)
        if not files:
            print(f"错误: 输入路径 {args.input} 中没有找到支持的图片文件", file=sys.stderr)
            sys.exit(1)
        
        # 确定输出目录
        if args.output:
            output_dir = Path(args.output)
        else:
            input_path = Path(args.input)
            if input_path.is_file():
                output_dir = input_path.parent / "output"
            else:
                output_dir = input_path / "output"
        
        # 解析尺寸参数
        width = args.width
        height = args.height
        percent = args.percent
        if args.size:
            width, height = args.size
        
        # 预览模式
        if args.preview:
            print_preview(files, output_dir, args.output_format, width, height, percent, args.quality)
            sys.exit(0)
        
        # 确认处理
        if not print_preview(files, output_dir, args.output_format, width, height, percent, args.quality):
            print("已取消处理")
            sys.exit(0)
        
        # 执行处理
        print("\n开始处理...")
        success_count = 0
        fail_count = 0
        
        for file in files:
            try:
                out_path, info = process_image(
                    file, output_dir,
                    output_format=args.output_format,
                    width=width, height=height, percent=percent,
                    quality=args.quality
                )
                print(f"  ✓ {file.name} -> {out_path.name}")
                success_count += 1
            except Exception as e:
                print(f"  ✗ {file.name}: {e}", file=sys.stderr)
                fail_count += 1
        
        # 输出结果摘要
        print("\n" + "="*60)
        print(f"处理完成: 成功 {success_count} 张，失败 {fail_count} 张")
        print(f"输出目录: {output_dir}")
        print("="*60)
        
        # 如果有失败，返回非零退出码
        if fail_count > 0:
            sys.exit(1)
            
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户中断处理", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
