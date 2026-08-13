#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 文件重命名批量处理工具（干净室独立实现）

依据功能规格 skill-64523 独立实现，不复制任何既有代码。
核心能力：批量添加前缀/后缀、序号填充、日期格式化、查找替换、扩展名统一、
重命名规则脚本生成、模拟执行与预览。

用法示例:
    python main.py --plan '{"type":"prefix","value":"2024_","folder":"./test"}' --dry-run
    python main.py --selftest
    python main.py --plan '{"type":"sequence","folder":"./test","sort_by":"name","start":1,"step":1,"digits":3}' --dry-run --verbose
"""

import argparse
import datetime
import json
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数缺失或格式错误",
    "E002": "目标文件夹不存在或不可访问",
    "E003": "规则类型未知或不支持",
    "E004": "正则表达式编译失败",
    "E005": "日期格式字符串无效",
    "E006": "文件筛选后无匹配文件",
    "E007": "重命名计划生成失败",
    "E008": "输入输出校验失败",
    "E009": "文件系统操作失败",
    "E010": "内部逻辑错误",
}


# ------------------------------------------------------------
# 输入校验模块
# ------------------------------------------------------------
def validate_plan_argument(plan_str: Optional[str]) -> Dict:
    """
    校验并解析 --plan 参数。

    Args:
        plan_str: JSON 格式的规则字符串。

    Returns:
        解析后的规则字典。

    Raises:
        ValueError: 当参数缺失或 JSON 解析失败时抛出，附带错误码 E001。
    """
    if not plan_str:
        raise ValueError(f"[E001] 缺少 --plan 参数。请提供 JSON 格式的重命名规则。")

    try:
        plan = json.loads(plan_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"[E001] --plan 参数不是合法的 JSON 格式: {e}")

    if not isinstance(plan, dict):
        raise ValueError(f"[E001] --plan 参数必须是一个 JSON 对象（字典）。")

    # 必填字段检查
    if "type" not in plan:
        raise ValueError(f"[E001] --plan 参数缺少 'type' 字段（规则类型）。")

    # 文件夹路径检查（可选，但如果有则必须存在）
    if "folder" in plan and plan["folder"]:
        folder_path = Path(plan["folder"])
        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError(f"[E002] 目标文件夹不存在或不是目录: {plan['folder']}")

    return plan


def validate_folder_path(folder: str) -> Path:
    """
    校验并规范化文件夹路径。

    Args:
        folder: 文件夹路径字符串。

    Returns:
        规范化后的 Path 对象。

    Raises:
        ValueError: 当路径不存在或不是目录时抛出，附带错误码 E002。
    """
    if not folder:
        raise ValueError(f"[E002] 文件夹路径不能为空。")

    folder_path = Path(folder).expanduser().resolve()

    if not folder_path.exists():
        raise ValueError(f"[E002] 目标文件夹不存在: {folder_path}")

    if not folder_path.is_dir():
        raise ValueError(f"[E002] 目标路径不是文件夹: {folder_path}")

    return folder_path


def validate_rule_type(rule_type: str) -> None:
    """
    校验规则类型是否支持。

    Args:
        rule_type: 规则类型字符串。

    Raises:
        ValueError: 当规则类型不支持时抛出，附带错误码 E003。
    """
    supported_types = {"prefix", "suffix", "sequence", "replace", "date", "ext"}
    if rule_type not in supported_types:
        raise ValueError(
            f"[E003] 不支持的规则类型: '{rule_type}'。"
            f"支持的类型: {', '.join(sorted(supported_types))}"
        )


# ------------------------------------------------------------
# 核心逻辑模块
# ------------------------------------------------------------
def filter_and_sort_files(folder_path: Path, rule: Dict) -> List[Path]:
    """
    根据规则筛选并排序文件列表。

    Args:
        folder_path: 目标文件夹 Path 对象。
        rule: 规则字典。

    Returns:
        排序后的文件 Path 列表。

    Raises:
        ValueError: 当没有匹配文件时抛出，附带错误码 E006。
    """
    # 获取所有文件（不包含子目录）
    all_files = [f for f in folder_path.iterdir() if f.is_file()]

    # 按扩展名筛选
    ext_filter = rule.get("ext_filter")
    if ext_filter:
        # 统一转换为小写并确保带点前缀
        normalized_exts = {
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in ext_filter
        }
        all_files = [
            f for f in all_files
            if f.suffix.lower() in normalized_exts
        ]

    # 按文件名模式筛选（支持 glob 模式）
    name_pattern = rule.get("name_pattern")
    if name_pattern:
        import fnmatch
        all_files = [
            f for f in all_files
            if fnmatch.fnmatch(f.name, name_pattern)
        ]

    if not all_files:
        raise ValueError(f"[E006] 筛选后没有匹配的文件。请检查文件夹路径和筛选条件。")

    # 排序
    sort_by = rule.get("sort_by", "name")
    if sort_by == "mtime":
        all_files.sort(key=lambda f: f.stat().st_mtime)
    elif sort_by == "ctime":
        all_files.sort(key=lambda f: f.stat().st_ctime)
    elif sort_by == "size":
        all_files.sort(key=lambda f: f.stat().st_size)
    else:  # 默认按名称字母序
        all_files.sort(key=lambda f: f.name.lower())

    return all_files


def build_new_filename(file_path: Path, rule: Dict, seq_num: int) -> str:
    """
    根据规则生成新文件名。

    Args:
        file_path: 原始文件 Path 对象。
        rule: 规则字典。
        seq_num: 序号值（用于 sequence 类型）。

    Returns:
        新文件名（不含路径）。

    Raises:
        ValueError: 当规则类型不支持或参数无效时抛出。
    """
    stem = file_path.stem
    ext = file_path.suffix
    rule_type = rule["type"]

    if rule_type == "prefix":
        prefix_value = rule.get("value", "")
        separator = rule.get("separator", "")
        new_name = f"{prefix_value}{separator}{stem}{ext}"

    elif rule_type == "suffix":
        suffix_value = rule.get("value", "")
        separator = rule.get("separator", "")
        new_name = f"{stem}{separator}{suffix_value}{ext}"

    elif rule_type == "sequence":
        start = rule.get("start", 1)
        step = rule.get("step", 1)
        digits = rule.get("digits", 3)
        seq_str = str(seq_num).zfill(digits)
        separator = rule.get("separator", "_")
        new_name = f"{seq_str}{separator}{stem}{ext}"

    elif rule_type == "replace":
        pattern = rule.get("pattern", "")
        replacement = rule.get("replacement", "")
        try:
            new_stem = re.sub(pattern, replacement, stem)
        except re.error as e:
            raise ValueError(f"[E004] 正则表达式编译失败: {pattern} - {e}")
        new_name = f"{new_stem}{ext}"

    elif rule_type == "date":
        date_format = rule.get("date_format", "%Y%m%d")
        try:
            # 验证日期格式
            datetime.datetime.now().strftime(date_format)
        except (ValueError, TypeError) as e:
            raise ValueError(f"[E005] 日期格式字符串无效: {date_format} - {e}")

        ts = file_path.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(ts)
        date_str = dt.strftime(date_format)
        separator = rule.get("separator", "_")
        new_name = f"{date_str}{separator}{stem}{ext}"

    elif rule_type == "ext":
        new_ext = rule.get("new_ext", "")
        # 确保新扩展名不带点
        new_ext = new_ext.lstrip(".")
        if not new_ext:
            raise ValueError(f"[E003] 新扩展名不能为空。")
        new_name = f"{stem}.{new_ext}"

    else:
        raise ValueError(f"[E003] 不支持的规则类型: {rule_type}")

    return new_name


def build_rename_plan(folder: str, rule: Dict) -> List[Tuple[str, str]]:
    """
    构建重命名计划。

    Args:
        folder: 目标文件夹路径。
        rule: 规则字典。

    Returns:
        重命名计划列表，每个元素为 (原文件名, 新文件名) 元组。

    Raises:
        ValueError: 当规则无效或生成失败时抛出。
    """
    folder_path = validate_folder_path(folder)
    validate_rule_type(rule["type"])

    files = filter_and_sort_files(folder_path, rule)

    plan = []
    try:
        for idx, file_path in enumerate(files):
            seq_num = rule.get("start", 1) + idx * rule.get("step", 1)
            new_name = build_new_filename(file_path, rule, seq_num)
            plan.append((file_path.name, new_name))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"[E007] 重命名计划生成失败: {e}")

    return plan


# ------------------------------------------------------------
# 冲突检测与安全校验模块
# ------------------------------------------------------------
def check_filename_legal(filename: str) -> Tuple[bool, str]:
    """
    检查文件名是否合法（不包含非法字符）。

    Args:
        filename: 文件名。

    Returns:
        (是否合法, 问题描述) 元组。
    """
    # Windows 非法字符
    illegal_chars = '<>:"/\\|?*'
    for ch in illegal_chars:
        if ch in filename:
            return False, f"包含非法字符 '{ch}'"

    # 检查保留名（Windows）
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
        "LPT6", "LPT7", "LPT8", "LPT9",
    }
    stem = filename.split(".")[0].upper()
    if stem in reserved_names:
        return False, f"是系统保留名称 '{stem}'"

    # 检查文件名长度（255 字节限制，保守用 200）
    if len(filename.encode("utf-8", errors="replace")) > 200:
        return False, "文件名过长（超过 200 字节）"

    # 检查是否以点或空格结尾
    if filename.endswith(".") or filename.endswith(" "):
        return False, "不能以点或空格结尾"

    return True, ""


def validate_plan(plan: List[Tuple[str, str]], folder: str) -> Dict:
    """
    检查重命名计划中的冲突和非法文件名。

    Args:
        plan: 重命名计划列表。
        folder: 目标文件夹路径。

    Returns:
        校验结果字典，包含 issues 列表和 warnings 列表。
    """
    folder_path = Path(folder)
    issues = []
    warnings = []

    existing_names = set(f.name for f in folder_path.iterdir() if f.is_file())

    # 检查新文件名是否合法
    for old_name, new_name in plan:
        legal, reason = check_filename_legal(new_name)
        if not legal:
            issues.append(f"'{old_name}' → '{new_name}': 非法文件名 - {reason}")

    # 检查重名冲突
    new_names_set = set()
    for old_name, new_name in plan:
        if new_name in new_names_set:
            issues.append(f"重名冲突: '{new_name}' 在计划中出现多次")
        new_names_set.add(new_name)

        # 与现有文件冲突（排除自身）
        if new_name in existing_names and new_name != old_name:
            # 检查是否有其他文件会被重命名为这个名字
            other_files = [n for o, n in plan if o != old_name]
            if new_name not in other_files:
                warnings.append(f"'{new_name}' 与现有文件重名，将被覆盖")

    return {"issues": issues, "warnings": warnings}


# ------------------------------------------------------------
# 输出格式化模块
# ------------------------------------------------------------
def format_plan_table(plan: List[Tuple[str, str]]) -> str:
    """
    将重命名计划格式化为表格。

    Args:
        plan: 重命名计划列表。

    Returns:
        格式化后的表格字符串。
    """
    if not plan:
        return "（空计划）"

    lines = []
    lines.append("┌────┬──────────────────────────────┬──────────────────────────────┐")
    lines.append("│ #  │ 原文件名                     │ 新文件名                     │")
    lines.append("├────┼──────────────────────────────┼──────────────────────────────┤")

    for idx, (old_name, new_name) in enumerate(plan, 1):
        # 截断过长的文件名
        old_display = old_name if len(old_name) <= 28 else old_name[:25] + "..."
        new_display = new_name if len(new_name) <= 28 else new_name[:25] + "..."
        lines.append(f"│ {idx:2d} │ {old_display:<28s} │ {new_display:<28s} │")

    lines.append("└────┴──────────────────────────────┴──────────────────────────────┘")
    return "\n".join(lines)


def format_verbose_details(plan: List[Tuple[str, str]], rule: Dict) -> str:
    """
    生成详细的操作说明（用于 --verbose 模式）。

    Args:
        plan: 重命名计划。
        rule: 规则字典。

    Returns:
        详细说明字符串。
    """
    lines = []
    lines.append("【操作明细】")
    lines.append(f"  规则类型: {rule['type']}")

    if rule["type"] == "prefix":
        lines.append(f"  添加前缀: '{rule.get('value', '')}'" +
                     (f"（分隔符: '{rule.get('separator', '')}'）" if rule.get("separator") else ""))
    elif rule["type"] == "suffix":
        lines.append(f"  添加后缀: '{rule.get('value', '')}'" +
                     (f"（分隔符: '{rule.get('separator', '')}'）" if rule.get("separator") else ""))
    elif rule["type"] == "sequence":
        lines.append(f"  序号填充: 起始={rule.get('start', 1)}, 步长={rule.get('step', 1)}, 位数={rule.get('digits', 3)}")
    elif rule["type"] == "replace":
        lines.append(f"  查找替换: 模式='{rule.get('pattern', '')}' → 替换为='{rule.get('replacement', '')}'")
    elif rule["type"] == "date":
        lines.append(f"  日期格式化: 格式='{rule.get('date_format', '%Y%m%d')}'（基于文件修改时间）")
    elif rule["type"] == "ext":
        lines.append(f"  扩展名修改: 统一为 '.{rule.get('new_ext', '')}'")

    lines.append("")
    lines.append("  逐文件操作:")
    for idx, (old_name, new_name) in enumerate(plan, 1):
        if old_name != new_name:
            lines.append(f"    [{idx:2d}] {old_name}")
            lines.append(f"         ↓ 重命名为")
            lines.append(f"         {new_name}")
        else:
            lines.append(f"    [{idx:2d}] {old_name} （无变化）")

    return "\n".join(lines)


def print_diff(plan: List[Tuple[str, str]]) -> None:
    """
    打印 diff 风格的变更摘要。

    Args:
        plan: 重命名计划。
    """
    changed = sum(1 for old, new in plan if old != new)
    unchanged = len(plan) - changed

    print(f"变更摘要: 共 {len(plan)} 个文件, {changed} 个将重命名, {unchanged} 个保持不变")
    for old, new in plan:
        if old != new:
            print(f"  - {old}")
            print(f"  + {new}")


# ------------------------------------------------------------
# 实际执行模块
# ------------------------------------------------------------
def execute_rename(plan: List[Tuple[str, str]], folder: str, dry: bool = True) -> None:
    """
    执行重命名操作。

    Args:
        plan: 重命名计划。
        folder: 目标文件夹路径。
        dry: 是否为干跑模式（不实际执行）。

    Raises:
        OSError: 当文件操作失败时抛出。
    """
    folder_path = Path(folder)

    for old_name, new_name in plan:
        if old_name == new_name:
            continue

        old_path = folder_path / old_name
        new_path = folder_path / new_name

        if dry:
            print(f"  [干跑] {old_name} → {new_name}")
        else:
            try:
                old_path.rename(new_path)
                print(f"  [已执行] {old_name} → {new_name}")
            except OSError as e:
                print(f"  [失败] {old_name} → {new_name}: {e}", file=sys.stderr)
                raise


# ------------------------------------------------------------
# 自检模块
# ------------------------------------------------------------
def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    Returns:
        0 表示全部通过，非 0 表示有失败。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    failures = 0

    # ---- 测试 1: 前缀规则 ----
    print("\n[测试 1] 前缀规则")
    try:
        # 使用临时目录
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_files = ["report.pdf", "summary.docx", "notes.txt"]
            for fname in test_files:
                Path(tmpdir, fname).write_text("test", encoding="utf-8")

            rule = {"type": "prefix", "value": "2024_", "folder": tmpdir}
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 3, f"预期 3 个文件，实际 {len(plan)}"
            for old_name, new_name in plan:
                assert new_name.startswith("2024_"), f"新文件名应以 '2024_' 开头: {new_name}"
                # 验证扩展名保留
                assert Path(old_name).suffix == Path(new_name).suffix, "扩展名应保留"

            print(f"  ✅ 通过: 生成 {len(plan)} 个重命名计划，前缀添加正确")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 2: 序号规则 ----
    print("\n[测试 2] 序号规则")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件（乱序创建）
            for fname in ["b.txt", "a.txt", "c.txt"]:
                Path(tmpdir, fname).write_text("test", encoding="utf-8")

            rule = {
                "type": "sequence",
                "folder": tmpdir,
                "sort_by": "name",
                "start": 1,
                "step": 1,
                "digits": 3,
            }
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 3, f"预期 3 个文件，实际 {len(plan)}"

            # 按名称排序后，a.txt 应该得到 001
            first_new_name = plan[0][1]
            assert first_new_name.startswith("001_"), f"第一个文件应编号 001: {first_new_name}"

            # 验证序号递增
            seqs = [int(new.split("_")[0]) for _, new in plan]
            assert seqs == sorted(seqs), f"序号应递增: {seqs}"
            assert seqs[0] == 1 and seqs[-1] == 3, f"序号范围应为 1-3: {seqs}"

            print(f"  ✅ 通过: 序号填充正确，按名称排序生效")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 3: 替换规则 ----
    print("\n[测试 3] 替换规则")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建包含空格的文件名
            Path(tmpdir, "my report final.txt").write_text("test", encoding="utf-8")
            Path(tmpdir, "another file.txt").write_text("test", encoding="utf-8")

            rule = {
                "type": "replace",
                "folder": tmpdir,
                "pattern": r"\s+",
                "replacement": "_",
            }
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 2, f"预期 2 个文件，实际 {len(plan)}"
            for old_name, new_name in plan:
                assert " " not in new_name, f"新文件名不应包含空格: {new_name}"
                assert "_" in new_name, f"新文件名应包含下划线: {new_name}"

            print(f"  ✅ 通过: 空格替换为下划线正确")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 4: 日期规则 ----
    print("\n[测试 4] 日期规则")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "photo.jpg").write_text("test", encoding="utf-8")

            rule = {
                "type": "date",
                "folder": tmpdir,
                "date_format": "%Y%m%d",
            }
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 1, f"预期 1 个文件，实际 {len(plan)}"
            old_name, new_name = plan[0]
            # 验证日期格式（8位数字）
            date_part = new_name.split("_")[0]
            assert len(date_part) == 8 and date_part.isdigit(), f"日期部分应为 8 位数字: {date_part}"
            # 验证年份合理
            year = int(date_part[:4])
            assert 2000 <= year <= 2100, f"年份应在合理范围: {year}"

            print(f"  ✅ 通过: 日期格式化正确，格式 {date_part}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 5: 扩展名规则 ----
    print("\n[测试 5] 扩展名规则")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "image.JPG").write_text("test", encoding="utf-8")
            Path(tmpdir, "photo.jpeg").write_text("test", encoding="utf-8")

            rule = {
                "type": "ext",
                "folder": tmpdir,
                "new_ext": "jpg",
            }
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 2, f"预期 2 个文件，实际 {len(plan)}"
            for old_name, new_name in plan:
                assert new_name.endswith(".jpg"), f"新扩展名应为 .jpg: {new_name}"

            print(f"  ✅ 通过: 扩展名统一为 .jpg 正确")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 6: 空输入和异常输入 ----
    print("\n[测试 6] 异常输入处理")
    try:
        # 空文件夹
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = {"type": "prefix", "value": "x_", "folder": tmpdir}
            try:
                build_rename_plan(tmpdir, rule)
                failures += 1
                print("  ❌ 失败: 空文件夹应抛出异常")
            except ValueError as e:
                assert "E006" in str(e), f"应包含错误码 E006: {e}"
                print(f"  ✅ 通过: 空文件夹正确抛出异常")

        # 不存在的文件夹
        try:
            rule = {"type": "prefix", "value": "x_", "folder": "/nonexistent/path/xyz"}
            build_rename_plan("/nonexistent/path/xyz", rule)
            failures += 1
            print("  ❌ 失败: 不存在的文件夹应抛出异常")
        except ValueError as e:
            assert "E002" in str(e), f"应包含错误码 E002: {e}"
            print(f"  ✅ 通过: 不存在的文件夹正确抛出异常")

        # 不支持的规则类型
        try:
            rule = {"type": "invalid_type", "folder": "."}
            validate_rule_type("invalid_type")
            failures += 1
            print("  ❌ 失败: 不支持的规则类型应抛出异常")
        except ValueError as e:
            assert "E003" in str(e), f"应包含错误码 E003: {e}"
            print(f"  ✅ 通过: 不支持的规则类型正确抛出异常")

    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 7: 中文文件名和编码 ----
    print("\n[测试 7] 中文文件名处理")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建中文文件名
            Path(tmpdir, "年度报告.pdf").write_text("test", encoding="utf-8")
            Path(tmpdir, "项目总结.docx").write_text("test", encoding="utf-8")

            rule = {"type": "prefix", "value": "2024_", "folder": tmpdir}
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 2, f"预期 2 个文件，实际 {len(plan)}"
            for old_name, new_name in plan:
                assert new_name.startswith("2024_"), f"新文件名应以 '2024_' 开头: {new_name}"
                # 验证中文保留
                assert "报告" in new_name or "总结" in new_name, f"中文应保留: {new_name}"

            print(f"  ✅ 通过: 中文文件名处理正确")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 8: 冲突检测 ----
    print("\n[测试 8] 冲突检测")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.txt").write_text("test", encoding="utf-8")
            Path(tmpdir, "b.txt").write_text("test", encoding="utf-8")

            # 构造一个会产生重名的计划
            plan = [("a.txt", "c.txt"), ("b.txt", "c.txt")]
            result = validate_plan(plan, tmpdir)

            assert len(result["issues"]) > 0, "应检测到重名冲突"
            print(f"  ✅ 通过: 重名冲突检测正确，发现 {len(result['issues'])} 个问题")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 9: 后缀规则 ----
    print("\n[测试 9] 后缀规则")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "report.pdf").write_text("test", encoding="utf-8")
            Path(tmpdir, "summary.docx").write_text("test", encoding="utf-8")

            rule = {"type": "suffix", "value": "_final", "folder": tmpdir}
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 2, f"预期 2 个文件，实际 {len(plan)}"
            for old_name, new_name in plan:
                assert new_name.endswith("_final.pdf") or new_name.endswith("_final.docx"), f"后缀添加错误: {new_name}"

            print(f"  ✅ 通过: 后缀添加正确")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 测试 10: 分隔符 ----
    print("\n[测试 10] 分隔符")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "report.pdf").write_text("test", encoding="utf-8")

            rule = {"type": "prefix", "value": "2024", "separator": "-", "folder": tmpdir}
            plan = build_rename_plan(tmpdir, rule)

            assert len(plan) == 1, f"预期 1 个文件，实际 {len(plan)}"
            old_name, new_name = plan[0]
            assert new_name == "2024-report.pdf", f"分隔符处理错误: {new_name}"

            print(f"  ✅ 通过: 分隔符处理正确")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # ---- 总结 ----
    print("\n" + "=" * 60)
    if failures == 0:
        print(f"自检完成: 全部通过 ✅")
        return 0
    else:
        print(f"自检完成: {failures} 项失败 ❌")
        return 1


# ------------------------------------------------------------
# 主入口
# ------------------------------------------------------------
def main() -> int:
    """
    主入口函数。

    Returns:
        退出码（0 成功，非 0 失败）。
    """
    parser = argparse.ArgumentParser(
        description="文件重命名批量处理工具（干净室实现）",
        epilog="示例: python main.py --plan '{\"type\":\"prefix\",\"value\":\"2024_\",\"folder\":\"./test\"}' --dry-run"
    )
    parser.add_argument(
        "--plan",
        type=str,
        help="JSON 格式的重命名规则，如 '{\"type\":\"prefix\",\"value\":\"2024_\",\"folder\":\"./test\"}'"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="干跑模式，只打印计划不实际执行（默认开启）"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制执行（需配合 --dry-run 使用，实际执行重命名）"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细的操作明细"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式
    try:
        # 输入校验
        rule = validate_plan_argument(args.plan)

        # 确定文件夹路径
        folder = rule.get("folder", ".")
        if not folder:
            folder = "."

        # 构建重命名计划
        plan = build_rename_plan(folder, rule)

        # 校验计划
        validation = validate_plan(plan, folder)
        if validation["issues"]:
            print("⚠️  发现计划问题:", file=sys.stderr)
            for issue in validation["issues"]:
                print(f"  - {issue}", file=sys.stderr)
            print("请修改规则后重试。", file=sys.stderr)
            return 1

        # 输出计划
        print("\n📋 重命名计划:")
        print(format_plan_table(plan))

        if validation["warnings"]:
            print("\n⚠️  警告:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")

        # 详细模式
        if args.verbose:
            print("\n" + format_verbose_details(plan, rule))

        # 执行或干跑
        dry = not args.force  # 默认干跑，只有 --force 才实际执行
        print(f"\n{'🔍 干跑模式（不实际执行）' if dry else '⚡ 执行模式'}")

        if dry:
            print_diff(plan)
            print("\n提示: 确认无误后，加 --force 参数实际执行。")
        else:
            print("\n开始执行重命名...")
            execute_rename(plan, folder, dry=False)
            print("✅ 重命名完成。")

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[E009] 文件系统错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未预期的错误: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
