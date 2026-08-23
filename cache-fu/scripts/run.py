#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cache-fu — 智能缓存清理与优化工具

提供缓存目录扫描、安全预览、实际清理等功能。
支持 --dry-run 预览模式，--force 实际执行，--verbose 详细输出。
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# 默认扫描的缓存目录（用于演示，实际使用可修改）
CACHE_DIRS = [
    Path(tempfile.gettempdir()) / "cache-fu-test" / "cache1",
    Path(tempfile.gettempdir()) / "cache-fu-test" / "cache2",
]

# 触发词列表
TRIGGERS = ["cache", "缓存", "清理", "cleanup", "disk space", "磁盘空间"]


def _get_utc_now() -> str:
    """获取当前 UTC 时间字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _read_text_safe(path: Path) -> str:
    """多编码安全读取文件"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _iter_lines(path: Path):
    """流式读取文件行"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _get_dir_size(path: Path) -> int:
    """计算目录总大小（流式遍历）"""
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                try:
                    total += (Path(root) / file).stat().st_size
                except OSError:
                    continue
    except OSError as e:
        print(f"[警告] 无法访问目录 {path}: {e}", file=sys.stderr)
    return total


def _list_files(path: Path) -> List[Path]:
    """列出目录下所有文件"""
    files = []
    try:
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                files.append(Path(root) / filename)
    except OSError as e:
        print(f"[警告] 无法访问目录 {path}: {e}", file=sys.stderr)
    return files


def scan_caches(dirs: List[Path]) -> Dict[Path, int]:
    """扫描缓存目录，返回 {目录: 大小} 映射"""
    result = {}
    for d in dirs:
        if d.exists() and d.is_dir():
            size = _get_dir_size(d)
            if size > 0:
                result[d] = size
    return result


def clean_caches(dirs: List[Path], dry_run: bool = False, verbose: bool = False) -> Tuple[int, int]:
    """
    清理缓存目录
    返回: (删除文件数, 释放空间字节数)
    """
    deleted_count = 0
    freed_bytes = 0

    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue

        files = _list_files(d)
        for idx, file in enumerate(files, 1):
            try:
                file_size = file.stat().st_size
                if not dry_run:
                    if verbose:
                        print(f"[明细] {idx}. {file}: {_format_size(file_size)} -> 已删除")
                    file.unlink()
                    deleted_count += 1
                    freed_bytes += file_size
                else:
                    print(f"[预览] 将删除 {file} (大小: {_format_size(file_size)})")
            except OSError as e:
                print(f"[警告] 文件删除失败: {file} - {e}", file=sys.stderr)

        # 尝试删除空目录
        try:
            if not dry_run:
                d.rmdir()
            else:
                print(f"[预览] 将删除空目录 {d}")
        except OSError:
            pass  # 目录非空或不存在，忽略

    if verbose:
        print(f"[汇总] 删除 {deleted_count} 个文件，释放 {_format_size(freed_bytes)}")
    return deleted_count, freed_bytes


def match_trigger(text: str) -> List[str]:
    """匹配触发词"""
    low = text.lower()
    return [t for t in TRIGGERS if t.lower() in low]


def selftest() -> int:
    """离线自检：真实调用核心函数并断言关键输出"""
    print("== cache-fu 自检开始 ==")

    # 准备测试数据
    test_dir = Path(tempfile.gettempdir()) / "cache-fu-selftest"
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test.tmp"
    test_file.write_text("test data for selftest", encoding="utf-8")

    # 测试 _format_size
    assert _format_size(1024) == "1.00 KB", "格式化大小失败"
    assert _format_size(1024 * 1024) == "1.00 MB", "格式化大小失败"
    print("  [OK] _format_size 格式化大小")

    # 测试 _get_dir_size
    size = _get_dir_size(test_dir)
    assert size > 0, "目录大小计算失败"
    print(f"  [OK] _get_dir_size 目录大小: {size}")

    # 测试 _list_files
    files = _list_files(test_dir)
    assert len(files) == 1, "文件列表获取失败"
    print(f"  [OK] _list_files 文件列表: {len(files)} 个文件")

    # 测试 scan_caches
    scan_result = scan_caches([test_dir])
    assert test_dir in scan_result, "扫描结果不包含测试目录"
    print(f"  [OK] scan_caches 扫描结果: {len(scan_result)} 个目录")

    # 测试 clean_caches (dry-run)
    deleted, freed = clean_caches([test_dir], dry_run=True)
    assert deleted == 0, "dry-run 不应删除文件"
    assert freed == 0, "dry-run 不应释放空间"
    assert test_file.exists(), "dry-run 后文件应存在"
    print("  [OK] clean_caches dry-run 模式")

    # 测试 clean_caches (实际执行)
    deleted, freed = clean_caches([test_dir], dry_run=False)
    assert deleted == 1, f"实际删除文件数应为 1，实际 {deleted}"
    assert freed > 0, "释放空间应大于 0"
    assert not test_file.exists(), "文件应已被删除"
    print(f"  [OK] clean_caches 实际执行: 删除 {deleted} 个文件，释放 {_format_size(freed)}")

    # 测试 match_trigger
    matched = match_trigger("清理缓存")
    assert "缓存" in matched, "触发词匹配失败"
    print(f"  [OK] match_trigger 触发词匹配: {matched}")

    # 清理测试目录
    try:
        test_dir.rmdir()
    except OSError:
        pass

    print("== cache-fu 自检通过 ✅ ==")
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(description="cache-fu 智能缓存清理工具")
    parser.add_argument("--scan", action="store_true", help="扫描缓存目录")
    parser.add_argument("--clean", action="store_true", help="清理缓存")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际删除")
    parser.add_argument("--force", action="store_true", help="实际执行（需配合 --clean）")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--match", default="", help="匹配触发词")
    parser.add_argument("--selftest", action="store_true", help="离线自检")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 触发词匹配模式
    if args.match:
        matched = match_trigger(args.match)
        if matched:
            print(f"命中触发词: {matched}")
            return 0
        else:
            print("未命中任何触发词")
            return 1

    # 扫描模式
    if args.scan:
        print("[扫描] 开始扫描缓存目录...")
        scan_result = scan_caches(CACHE_DIRS)
        if not scan_result:
            print("[扫描] 未发现可清理的缓存目录")
            return 0
        total_size = sum(scan_result.values())
        for d, size in scan_result.items():
            print(f"[扫描] 发现缓存目录: {d} (大小: {_format_size(size)})")
        print(f"[扫描] 扫描完成。共发现 {len(scan_result)} 个缓存目录，总大小: {_format_size(total_size)}")
        return 0

    # 清理模式
    if args.clean:
        if args.dry_run:
            print("[预览] 模拟清理，不实际删除文件。")
            deleted, freed = clean_caches(CACHE_DIRS, dry_run=True, verbose=args.verbose)
            print(f"[预览] 预计释放空间: {_format_size(freed)}")
            return 0
        elif args.force:
            print("[清理] 开始清理缓存目录...")
            deleted, freed = clean_caches(CACHE_DIRS, dry_run=False, verbose=args.verbose)
            print(f"[清理] 清理完成。共删除 {deleted} 个文件，释放空间: {_format_size(freed)}")
            return 0
        else:
            print("[错误] 清理需要指定 --dry-run（预览）或 --force（实际执行）", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
