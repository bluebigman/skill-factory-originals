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
- 并行处理提升性能
- 支持断点续传（--resume）

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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
dry_run = False  # v3.274 模块级 dry-run 标志

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
# 并行处理线程数
MAX_WORKERS = 4
# 进度条宽度
PROGRESS_BAR_WIDTH = 50


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


def validate_resize_params(width=None, height=None, percent=None):
    """验证尺寸调整参数合法性"""
    if percent is not None:
        if not isinstance(percent, (int, float)) or percent <= 0 or percent > 1000:
            raise ValueError(f"percent 必须在 (0, 1000] 范围内，当前值: {percent}")
    if width is not None:
        if not isinstance(width, (int, float)) or width <= 0:
            raise ValueError(f"width 必须为正数，当前值: {width}")
    if height is not None:
        if not isinstance(height, (int, float)) or height <= 0:
            raise ValueError(f"height 必须为正数，当前值: {height}")
    if width is None and height is None and percent is None:
        raise ValueError("必须指定 width、height 或 percent 中的至少一个")


def resize_image(img, width=None, height=None, percent=None):
    """调整图片尺寸"""
    # 参数验证
    validate_resize_params(width, height, percent)
    
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
    new_w = max(1, int(new_w))
    new_h = max(1, int(new_h))
    
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
        'processed_at': datetime.now(timezone.utc).isoformat()
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


def print_progress(current, total, success, failed):
    """打印进度条"""
    percent = (current / total) * 100 if total > 0 else 0
    filled = int(PROGRESS_BAR_WIDTH * current // total) if total > 0 else 0
    bar = '█' * filled + '░' * (PROGRESS_BAR_WIDTH - filled)
    print(f"\r进度: [{bar}] {percent:.1f}% ({current}/{total}) 成功:{success} 失败:{failed}", end='', flush=True)


def process_batch_parallel(files, output_dir, output_format, width, height, percent, quality, resume_file=None):
    """并行处理图片批次"""
    # 加载断点信息
    processed_files = set()
    if resume_file and resume_file.exists():
        try:
            with open(resume_file, 'r', encoding='utf-8') as f:
                processed_files = set(json.load(f))
            print(f"发现断点信息，跳过 {len(processed_files)} 个已处理文件")
        except (json.JSONDecodeError, KeyError):
            print("断点文件损坏，将重新处理所有文件")
    
    # 过滤已处理的文件
    files_to_process = [f for f in files if str(f) not in processed_files]
    
    if not files_to_process:
        print("所有文件均已处理完成")
        return 0, 0
    
    print(f"开始并行处理 {len(files_to_process)} 个文件（线程数: {MAX_WORKERS}）...")
    
    success_count = 0
    fail_count = 0
    current = 0
    
    # 创建临时备份目录
    backup_dir = Path(tempfile.mkdtemp(prefix="batch_resize_backup_"))
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(
                    process_image, f, output_dir,
                    output_format=output_format,
                    width=width, height=height, percent=percent,
                    quality=quality
                ): f for f in files_to_process
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                current += 1
                try:
                    out_path, info = future.result()
                    success_count += 1
                    # 记录处理进度
                    processed_files.add(str(file))
                    # 更新断点文件
                    if resume_file:
                        with open(resume_file, 'w', encoding='utf-8') as f:
                            json.dump(list(processed_files), f)
                    print_progress(current, len(files_to_process), success_count, fail_count)
                except Exception as e:
                    fail_count += 1
                    print(f"\n✗ {file.name}: {e}", file=sys.stderr)
                    print_progress(current, len(files_to_process), success_count, fail_count)
        
        print()  # 换行
        return success_count, fail_count
        
    except KeyboardInterrupt:
        print("\n用户中断处理，已处理文件将保存到断点文件")
        if resume_file:
            with open(resume_file, 'w', encoding='utf-8') as f:
                json.dump(list(processed_files), f)
        raise
    finally:
        # 清理备份目录
        shutil.rmtree(backup_dir, ignore_errors=True)


def selftest():
    """自检函数 - 不联网，本地测试核心功能"""
    print("运行自检...")
    
    # 创建临时测试目录
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
        if not dry_run:
            bad_file.write_text("not an image")
        try:
            get_image_files(bad_file)
            assert False, "应抛出格式不支持错误"
        except ValueError:
            pass
        
        # 测试7: 参数验证 - 非法宽度
        try:
            resize_image(Image.new('RGB', (10, 10)), width=0)
            assert False, "应抛出 ValueError"
        except ValueError:
            pass
        
        # 测试8: 参数验证 - 非法百分比
        try:
            resize_image(Image.new('RGB', (10, 10)), percent=0)
            assert False, "应抛出 ValueError"
        except ValueError:
            pass
        
        # 测试9: 参数验证 - 非法百分比上限
        try:
            resize_image(Image.new('RGB', (10, 10)), percent=1001)
            assert False, "应抛出 ValueError"
        except ValueError:
            pass
        
        # 测试10: 并行处理
        success, fail = process_batch_parallel(files, output_dir, None, 80, None, None, None)
        assert success == 2, f"并行处理应成功2个，实际 {success}"
        assert fail == 0, f"并行处理应失败0个，实际 {fail}"
        
        # 测试11: 断点续传
        resume_file = test_dir / "resume.json"
        success, fail = process_batch_parallel(files, output_dir, None, 80, None, None, None, resume_file)
        assert success == 0, f"断点续传应跳过所有文件，实际成功 {success}"
        
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
  python batch_resize.py --input ./input --preview  # 仅预览
  python batch_resize.py --input ./input --dry-run  # 试运行
  python batch_resize.py --input ./input --resume   # 断点续传
        """
    )
    
    # 输入参数
    parser.add_argument('--input', '-i', required=False, help='输入文件夹路径或单文件路径')
    parser.add_argument('--output', '-o', help='输出目录（默认: 输入目录下的 output/）')
    
    # 尺寸调整参数（四选一）
    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument('--width', type=int, help='按指定宽度等比缩放')
    size_group.add_argument('--height', type=int, help='按指定高度等比缩放')
    size_group.add_argument('--percent', type=int, help='按百分比缩放（如 50 表示 50%）')
