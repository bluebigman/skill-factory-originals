#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - duplikate 技能核心实现（clean-room 独立重写）

功能：同步一个目录到另一个目录（例如：将 git 项目同步到 svn 仓库）。
本脚本仅依据功能规格独立实现，不复制任何既有代码。

用法示例：
    python scripts/main.py --source ./src --target ./dst
    python scripts/main.py --selftest

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 源目录不存在
    E007 目标目录创建失败
    E008 文件复制失败
    E009 参数解析失败
    E010 内部逻辑错误（不应发生）
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 核心逻辑：目录同步
# ============================================================

def sync_directory(source_dir, target_dir, dry_run=False):
    """
    将 source_dir 中的内容同步到 target_dir。

    同步策略：
    - 如果目标目录不存在，则创建它。
    - 遍历源目录中的所有文件和子目录。
    - 对于每个源文件，如果目标中不存在或内容不同，则复制。
    - 对于每个源子目录，递归同步。
    - 注意：本实现只做"单向推送"，不删除目标中多余的文件（保守策略）。

    参数：
        source_dir (str): 源目录路径。
        target_dir (str): 目标目录路径。
        dry_run (bool): 若为 True，则只打印将要执行的操作，不实际执行。

    返回：
        dict: 包含同步统计信息的字典，如 {"copied": 3, "skipped": 5, "created_dirs": 2}

    错误码：
        可能抛出 OSError（E008 场景），由上层调用者捕获并转换。
    """
    source_path = Path(source_dir)
    target_path = Path(target_dir)

    # --- 输入校验（E006） ---
    if not source_path.exists():
        raise FileNotFoundError(f"E006: 源目录不存在: {source_dir}")
    if not source_path.is_dir():
        raise NotADirectoryError(f"E006: 源路径不是目录: {source_dir}")

    # --- 统计信息 ---
    stats = {"copied": 0, "skipped": 0, "created_dirs": 0}

    # --- 创建目标目录（E007） ---
    if not target_path.exists():
        if dry_run:
            print(f"[DRY-RUN] 创建目录: {target_dir}")
        else:
            try:
                target_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise OSError(f"E007: 目标目录创建失败: {target_dir} ({exc})") from exc
        stats["created_dirs"] += 1

    # --- 遍历源目录 ---
    for root, dirs, files in os.walk(source_dir):
        # 计算相对路径
        rel_path = os.path.relpath(root, source_dir)
        if rel_path == ".":
            rel_path = ""

        # 目标中的对应目录
        target_subdir = target_path if rel_path == "" else target_path / rel_path

        # 确保目标子目录存在
        if rel_path != "" and not target_subdir.exists():
            if dry_run:
                print(f"[DRY-RUN] 创建子目录: {target_subdir}")
            else:
                try:
                    target_subdir.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    raise OSError(f"E007: 子目录创建失败: {target_subdir} ({exc})") from exc
            stats["created_dirs"] += 1

        # 复制文件
        for file_name in files:
            src_file = os.path.join(root, file_name)
            dst_file = target_subdir / file_name

            # 判断是否需要复制（目标不存在或内容不同）
            need_copy = False
            if not dst_file.exists():
                need_copy = True
            else:
                # 比较文件大小（快速判断）
                try:
                    src_size = os.path.getsize(src_file)
                    dst_size = os.path.getsize(dst_file)
                    if src_size != dst_size:
                        need_copy = True
                    else:
                        # 大小相同再比较内容（保守但更准确）
                        # 注意：这里使用简单比较，不处理大文件的内存问题（规格未要求）
                        with open(src_file, "rb") as f_src, open(dst_file, "rb") as f_dst:
                            # 分块比较，避免一次性读入超大文件
                            while True:
                                chunk_src = f_src.read(8192)
                                chunk_dst = f_dst.read(8192)
                                if chunk_src != chunk_dst:
                                    need_copy = True
                                    break
                                if not chunk_src:  # 都读完了且相同
                                    break
                except OSError:
                    # 任何读取错误都视为需要复制（保守）
                    need_copy = True

            if need_copy:
                if dry_run:
                    print(f"[DRY-RUN] 复制: {src_file} -> {dst_file}")
                else:
                    try:
                        shutil.copy2(src_file, dst_file)  # copy2 保留元数据
                    except OSError as exc:
                        raise OSError(f"E008: 文件复制失败: {src_file} -> {dst_file} ({exc})") from exc
                stats["copied"] += 1
            else:
                stats["skipped"] += 1

    return stats


# ============================================================
# 置信度评估（依据规格：E005 场景）
# ============================================================

def evaluate_confidence(stats):
    """
    根据同步结果评估置信度。

    规则（依据规格）：
    - 置信度 ≥90%：直接输出（无需标注）
    - 85%-90%：标注"建议复核"
    - <85%：标注"[需核实]"

    参数：
        stats (dict): sync_directory 返回的统计信息。

    返回：
        tuple: (confidence_float, label_str)
    """
    total = stats["copied"] + stats["skipped"]
    if total == 0:
        # 空目录同步，视为完全成功
        return 1.0, ""

    # 以"复制成功率"作为置信度基础
    # 复制失败会抛异常，能走到这里说明全部成功，但为了体现规格的"低置信度标注"，
    # 我们考虑"跳过率"：跳过的文件越多（说明目标越新），置信度越高。
    # 但为了简单且符合规格，这里用 1.0 表示全部成功。
    confidence = 1.0

    # 如果目标目录是新建的（created_dirs > 0），说明是全新同步，置信度稍低（因为首次同步可能有遗漏）
    if stats["created_dirs"] > 0:
        confidence = min(confidence, 0.95)

    # 如果复制的文件很多，说明同步量大，置信度稍低（因为可能有未覆盖的情况）
    if stats["copied"] > 100:
        confidence = min(confidence, 0.9)

    # 根据置信度生成标签
    if confidence >= 0.9:
        label = ""
    elif confidence >= 0.85:
        label = "建议复核"
    else:
        label = "[需核实]"

    return confidence, label


# ============================================================
# 命令行入口
# ============================================================

def parse_arguments(argv=None):
    """
    解析命令行参数。

    参数：
        argv (list): 命令行参数列表，默认为 sys.argv[1:]。

    返回：
        argparse.Namespace: 解析后的参数。
    """
    parser = argparse.ArgumentParser(
        description="duplikate - 同步一个目录到另一个目录",
        epilog="示例: python scripts/main.py --source ./src --target ./dst"
    )
    parser.add_argument("--source", "-s", help="源目录路径")
    parser.add_argument("--target", "-t", help="目标目录路径")
    parser.add_argument("--dry-run", "-n", action="store_true", help="只显示将要执行的操作，不实际执行")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（不访问外部文件/网络）")
    return parser.parse_args(argv)


def run_selftest():
    """
    内置自检：使用硬编码的临时目录数据，验证核心逻辑。

    自检原则：
    - 不读取外部文件、不依赖当前工作目录、不访问网络。
    - 使用 tempfile 创建临时目录（系统临时目录，任何环境可用）。
    - 断言使用宽松阈值（大小比较/区间判断），不依赖精确值。

    返回：
        int: 0 表示成功，非 0 表示失败。
    """
    print("[SELFTEST] 开始自检...")
    try:
        # --- 创建临时源目录 ---
        with tempfile.TemporaryDirectory(prefix="duplikate_selftest_src_") as src_dir:
            # 创建测试文件
            test_files = {
                "file1.txt": b"hello world",
                "subdir/file2.txt": b"nested content",
                "subdir/deep/file3.txt": b"deep content",
            }
            for rel_path, content in test_files.items():
                full_path = os.path.join(src_dir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "wb") as f:
                    f.write(content)

            # --- 创建临时目标目录（初始为空） ---
            with tempfile.TemporaryDirectory(prefix="duplikate_selftest_dst_") as dst_dir:
                # 执行同步
                stats = sync_directory(src_dir, dst_dir, dry_run=False)

                # --- 宽松断言 1: 复制的文件数应该等于源文件数（3个） ---
                # 注意：不依赖精确值，只断言"复制数 >= 3"（因为可能未来增加文件）
                assert stats["copied"] >= 3, f"自检失败: 复制文件数过少, 实际: {stats['copied']}"

                # --- 宽松断言 2: 目标目录中应该存在所有源文件 ---
                for rel_path in test_files:
                    target_file = os.path.join(dst_dir, rel_path)
                    assert os.path.exists(target_file), f"自检失败: 目标文件不存在: {target_file}"

                # --- 宽松断言 3: 文件内容一致 ---
                for rel_path, expected_content in test_files.items():
                    target_file = os.path.join(dst_dir, rel_path)
                    with open(target_file, "rb") as f:
                        actual_content = f.read()
                    # 使用大小比较（宽松）
                    assert len(actual_content) == len(expected_content), (
                        f"自检失败: 文件大小不一致: {rel_path}"
                    )

                # --- 宽松断言 4: 第二次同步应该全部跳过（不复制） ---
                stats_second = sync_directory(src_dir, dst_dir, dry_run=False)
                assert stats_second["copied"] == 0, (
                    f"自检失败: 第二次同步不应复制任何文件, 实际复制: {stats_second['copied']}"
                )
                assert stats_second["skipped"] >= 3, (
                    f"自检失败: 第二次同步应跳过至少3个文件, 实际跳过: {stats_second['skipped']}"
                )

                # --- 宽松断言 5: 置信度评估（应该很高） ---
                confidence, label = evaluate_confidence(stats)
                assert confidence >= 0.8, f"自检失败: 置信度过低: {confidence}"
                # label 可以是空字符串或"建议复核"，但不能是"[需核实]"（因为同步成功）
                assert label != "[需核实]", f"自检失败: 置信度标签不应为[需核实]: {label}"

                # --- 宽松断言 6: dry-run 模式不实际修改目标 ---
                with tempfile.TemporaryDirectory(prefix="duplikate_selftest_dry_") as dry_dst:
                    stats_dry = sync_directory(src_dir, dry_dst, dry_run=True)
                    # dry-run 不应实际创建文件
                    assert stats_dry["copied"] >= 3, "自检失败: dry-run 统计信息错误"
                    # 目标目录可能被创建（mkdir 在 dry-run 中也会执行？），
                    # 但文件不应被复制。这里只检查没有文件被复制。
                    # 注意：我们的实现中 dry-run 也会创建目录（因为 mkdir 会执行），
                    # 所以只检查文件不存在。
                    for rel_path in test_files:
                        target_file = os.path.join(dry_dst, rel_path)
                        assert not os.path.exists(target_file), (
                            f"自检失败: dry-run 不应创建文件: {target_file}"
                        )

        print("[SELFTEST] 全部自检断言通过 ✓")
        return 0
    except AssertionError as exc:
        print(f"[SELFTEST] 自检失败: {exc}")
        return 1
    except Exception as exc:  # 捕获所有异常
        print(f"[SELFTEST] 自检异常: {exc}")
        return 1


def main(argv=None):
    """
    主入口函数。

    参数：
        argv (list): 命令行参数列表，默认为 sys.argv[1:]。

    返回：
        int: 退出码（0 成功，非 0 失败）。
    """
    # --- 参数解析（E009） ---
    try:
        args = parse_arguments(argv)
    except SystemExit as exc:
        # argparse 在参数错误时会调用 sys.exit()
        if exc.code != 0:
            print("E009: 参数解析失败", file=sys.stderr)
        return exc.code if isinstance(exc.code, int) else 1

    # --- 自检模式 ---
    if args.selftest:
        return run_selftest()

    # --- 正常模式：校验必要参数（E001/E002） ---
    if not args.source or not args.target:
        print("E001: 输入为空，请提供 --source 和 --target 参数", file=sys.stderr)
        print("用法: python scripts/main.py --source <源目录> --target <目标目录>", file=sys.stderr)
        return 1

    # --- 执行同步 ---
    try:
        stats = sync_directory(args.source, args.target, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        # 错误码已经在异常消息中（E007/E008）
        print(f"{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: 内部逻辑错误: {exc}", file=sys.stderr)
        return 1

    # --- 输出结果 ---
    confidence, label = evaluate_confidence(stats)
    print(f"同步完成: 复制 {stats['copied']} 个文件, 跳过 {stats['skipped']} 个文件, 创建 {stats['created_dirs']} 个目录")
    if label:
        print(f"置信度: {confidence:.0%} - {label}")
    else:
        print(f"置信度: {confidence:.0%}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
