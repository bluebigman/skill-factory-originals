#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — planning-with-files 技能独立实现

基于文件的多步骤计划持久化、崩溃恢复与长任务跟踪。
本脚本为 clean-room 实现，仅依据功能规格编写。
"""

import argparse
import datetime
import os
import re
import shutil
import sys
import tempfile
from datetime import timezone

dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "文件格式错误",
    "E004": "写入失败",
    "E005": "步骤不存在",
    "E006": "步骤状态错误",
    "E007": "目录创建失败",
    "E008": "备份失败",
    "E009": "读取失败",
    "E010": "内部逻辑错误",
}

# 步骤状态常量
STATUS_PENDING = "pending"
STATUS_DONE = "done"
STATUS_BLOCKED = "blocked"

# 计划文件格式标记
MARKER_START = "<!-- plan-start -->"
MARKER_END = "<!-- plan-end -->"


class PlanError(Exception):
    """计划相关异常，携带错误码"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _now_str() -> str:
    """返回当前时间戳字符串"""
    return datetime.datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _validate_status(status: str) -> None:
    """校验步骤状态合法性"""
    if status not in (STATUS_PENDING, STATUS_DONE, STATUS_BLOCKED):
        raise PlanError("E006", f"非法状态: {status}")


def _parse_plan_text(text: str) -> list:
    """从计划文本中解析步骤列表"""
    steps = []
    
    # 提取 MARKER_START 和 MARKER_END 之间的内容
    start_idx = text.find(MARKER_START)
    end_idx = text.find(MARKER_END)
    
    if start_idx == -1 or end_idx == -1:
        return steps
    
    # 提取标记之间的内容
    content_between = text[start_idx + len(MARKER_START):end_idx]
    
    # 按行分割并解析
    for line in content_between.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # 匹配步骤格式: - [x] 内容 :: 备注
        match = re.match(r'^-\s*\[([ xX])\]\s*(.+?)(?:\s*::\s*(.*))?$', line)
        if match:
            raw_status = match.group(1)
            content = match.group(2).strip()
            note = match.group(3).strip() if match.group(3) else ""
            status = STATUS_DONE if raw_status in ("x", "X") else STATUS_PENDING
            steps.append({"content": content, "status": status, "note": note})
    
    return steps


def _render_plan_text(steps: list) -> str:
    """将步骤列表渲染为计划文本"""
    lines = [MARKER_START]
    for step in steps:
        mark = "x" if step["status"] == STATUS_DONE else " "
        line = f"- [{mark}] {step['content']}"
        if step.get("note"):
            line += f" :: {step['note']}"
        lines.append(line)
    lines.append(MARKER_END)
    return "\n".join(lines) + "\n"


def create_plan(filepath: str, steps: list, overwrite: bool = False) -> dict:
    """创建新计划文件

    Args:
        filepath: 计划文件路径
        steps: 步骤列表，元素为 dict，含 content/status/note
        overwrite: 是否覆盖已存在文件

    Returns:
        计划元信息 dict

    Raises:
        PlanError: E001 参数错误, E002 文件已存在, E004 写入失败
    """
    if not steps:
        raise PlanError("E001", "步骤列表不能为空")
    if os.path.exists(filepath) and not overwrite:
        raise PlanError("E002", f"文件已存在: {filepath}")

    # 规范化步骤
    normalized = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict) or not step.get("content"):
            raise PlanError("E001", f"步骤 {i+1} 格式错误")
        status = step.get("status", STATUS_PENDING)
        _validate_status(status)
        normalized.append(
            {
                "content": str(step["content"]).strip(),
                "status": status,
                "note": str(step.get("note", "")).strip(),
            }
        )

    # 确保目录存在
    parent = os.path.dirname(os.path.abspath(filepath))
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as exc:
            raise PlanError("E007", f"目录创建失败: {parent}") from exc

    # 写入文件
    try:
        with open(filepath, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(_render_plan_text(normalized))
    except OSError as exc:
        raise PlanError("E004", f"写入失败: {filepath}") from exc

    return {
        "filepath": filepath,
        "steps": normalized,
        "created_at": _now_str(),
        "total": len(normalized),
        "done": sum(1 for s in normalized if s["status"] == STATUS_DONE),
    }


def load_plan(filepath: str) -> dict:
    """从文件加载计划

    Args:
        filepath: 计划文件路径

    Returns:
        计划数据 dict

    Raises:
        PlanError: E002 文件不存在, E003 格式错误, E009 读取失败
    """
    if not os.path.exists(filepath):
        raise PlanError("E002", f"文件不存在: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as exc:
        raise PlanError("E009", f"读取失败: {filepath}") from exc

    if MARKER_START not in content or MARKER_END not in content:
        raise PlanError("E003", "文件缺少计划标记")

    steps = _parse_plan_text(content)
    if not steps:
        raise PlanError("E003", "未解析到任何步骤")

    return {
        "filepath": filepath,
        "steps": steps,
        "total": len(steps),
        "done": sum(1 for s in steps if s["status"] == STATUS_DONE),
    }


def update_step(filepath: str, index: int, status: str = None, note: str = None) -> dict:
    """更新指定步骤的状态或备注

    Args:
        filepath: 计划文件路径
        index: 步骤索引（从 1 开始）
        status: 新状态，None 表示不修改
        note: 新备注，None 表示不修改

    Returns:
        更新后的计划数据

    Raises:
        PlanError: E002/E003/E005/E006
    """
    plan = load_plan(filepath)
    if index < 1 or index > plan["total"]:
        raise PlanError("E005", f"步骤索引越界: {index}")

    if status is not None:
        _validate_status(status)
        plan["steps"][index - 1]["status"] = status
    if note is not None:
        plan["steps"][index - 1]["note"] = note

    # 写回文件
    try:
        with open(filepath, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(_render_plan_text(plan["steps"]))
    except OSError as exc:
        raise PlanError("E004", f"写入失败: {filepath}") from exc

    plan["done"] = sum(1 for s in plan["steps"] if s["status"] == STATUS_DONE)
    return plan


def backup_plan(filepath: str, backup_dir: str = None) -> str:
    """创建计划文件的时间戳备份

    Args:
        filepath: 计划文件路径
        backup_dir: 备份目录，默认与源文件同目录

    Returns:
        备份文件路径

    Raises:
        PlanError: E002 源文件不存在, E008 备份失败
    """
    if not os.path.exists(filepath):
        raise PlanError("E002", f"文件不存在: {filepath}")

    src_dir = os.path.dirname(os.path.abspath(filepath))
    backup_dir = backup_dir or src_dir
    if not os.path.exists(backup_dir):
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except OSError as exc:
            raise PlanError("E007", f"目录创建失败: {backup_dir}") from exc

    basename = os.path.basename(filepath)
    stem, ext = os.path.splitext(basename)
    backup_name = f"{stem}-{_now_str()}{ext}"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        shutil.copy2(filepath, backup_path)
    except OSError as exc:
        raise PlanError("E008", f"备份失败: {backup_path}") from exc

    return backup_path


def verify_plan(filepath: str) -> dict:
    """校验计划文件完整性

    Args:
        filepath: 计划文件路径

    Returns:
        校验结果 dict，含 valid、issues 列表

    Raises:
        PlanError: E002/E003
    """
    plan = load_plan(filepath)
    issues = []

    # 检查步骤内容非空
    for i, step in enumerate(plan["steps"], 1):
        if not step["content"].strip():
            issues.append(f"步骤 {i}: 内容为空")

    # 检查状态合法性
    for i, step in enumerate(plan["steps"], 1):
        if step["status"] not in (STATUS_PENDING, STATUS_DONE, STATUS_BLOCKED):
            issues.append(f"步骤 {i}: 非法状态 {step['status']}")

    # 检查文件标记完整性
    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    if content.count(MARKER_START) != 1 or content.count(MARKER_END) != 1:
        issues.append("文件标记不完整")

    return {
        "filepath": filepath,
        "valid": len(issues) == 0,
        "issues": issues,
        "total": plan["total"],
        "done": plan["done"],
        "pending": plan["total"] - plan["done"],
    }


def progress_report(filepath: str) -> dict:
    """生成进度报告

    Args:
        filepath: 计划文件路径

    Returns:
        进度报告 dict

    Raises:
        PlanError: E002/E003
    """
    plan = load_plan(filepath)
    total = plan["total"]
    done = plan["done"]
    ratio = (done / total) if total > 0 else 0.0

    return {
        "filepath": filepath,
        "total": total,
        "done": done,
        "pending": total - done,
        "percent": round(ratio * 100, 1),
        "status": "完成" if done == total else "进行中",
    }


def _selftest() -> int:
    """内置自检函数，使用硬编码样例数据离线验证核心逻辑

    Returns:
        0 表示全部通过，1 表示存在失败
    """
    print("开始自检 planning-with-files 核心逻辑...")
    failures = 0

    # 使用临时目录隔离测试文件
    with tempfile.TemporaryDirectory(prefix="plan-selftest-") as tmpdir:
        # ---- 测试 1: 创建计划 ----
        plan_path = os.path.join(tmpdir, "test-plan.md")
        sample_steps = [
            {"content": "分析需求", "status": STATUS_DONE, "note": "已完成"},
            {"content": "设计架构", "status": STATUS_PENDING, "note": ""},
            {"content": "编码实现", "status": STATUS_PENDING, "note": ""},
            {"content": "测试验证", "status": STATUS_BLOCKED, "note": "等待环境"},
        ]
        try:
            created = create_plan(plan_path, sample_steps)
            # 宽松断言：总数应为 4
            assert created["total"] == 4, f"创建步骤总数错误: {created['total']}"
            assert created["done"] == 1, f"完成数错误: {created['done']}"
            assert os.path.exists(plan_path), "计划文件未创建"
            print("  [PASS] 创建计划")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 创建计划: {exc}")

        # ---- 测试 2: 加载计划 ----
        try:
            loaded = load_plan(plan_path)
            assert loaded["total"] == 4, f"加载步骤总数错误: {loaded['total']}"
            assert loaded["steps"][0]["status"] == STATUS_DONE, "首步骤状态错误"
            assert loaded["steps"][3]["status"] == STATUS_BLOCKED, "末步骤状态错误"
            print("  [PASS] 加载计划")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 加载计划: {exc}")

        # ---- 测试 3: 更新步骤 ----
        try:
            updated = update_step(plan_path, 2, status=STATUS_DONE, note="已完成设计")
            assert updated["steps"][1]["status"] == STATUS_DONE, "步骤状态未更新"
            assert updated["steps"][1]["note"] == "已完成设计", "备注未更新"
            assert updated["done"] == 2, f"完成数未更新: {updated['done']}"

            # 再次加载验证持久化
            reloaded = load_plan(plan_path)
            assert reloaded["steps"][1]["status"] == STATUS_DONE, "持久化失败"
            print("  [PASS] 更新步骤")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 更新步骤: {exc}")

        # ---- 测试 4: 备份 ----
        try:
            backup_path = backup_plan(plan_path)
            assert os.path.exists(backup_path), "备份文件不存在"
            # 备份内容应与原文件一致
            with open(plan_path, "r", encoding="utf-8", errors="replace") as f1, open(
                backup_path, "r", encoding="utf-8", errors="replace"
            ) as f2:
                assert f1.read() == f2.read(), "备份内容不一致"
            print("  [PASS] 备份计划")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 备份计划: {exc}")

        # ---- 测试 5: 校验 ----
        try:
            result = verify_plan(plan_path)
            assert result["valid"] is True, f"校验未通过: {result['issues']}"
            assert result["total"] == 4, "校验总数错误"
            print("  [PASS] 校验计划")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 校验计划: {exc}")

        # ---- 测试 6: 进度报告 ----
        try:
            report = progress_report(plan_path)
            assert report["total"] == 4, "进度总数错误"
            assert report["done"] == 2, "进度完成数错误"
            # 宽松断言：百分比在 40-60 之间（2/4=50%）
            assert 40 <= report["percent"] <= 60, f"百分比异常: {report['percent']}"
            assert report["status"] == "进行中", "状态判断错误"
            print("  [PASS] 进度报告")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 进度报告: {exc}")

        # ---- 测试 7: 错误处理 ----
        try:
            # 文件不存在
            try:
                load_plan(os.path.join(tmpdir, "nonexistent.md"))
                failures += 1
                print("  [FAIL] 错误处理: 应抛出 E002")
            except PlanError as exc:
                assert exc.code == "E002", f"错误码错误: {exc.code}"

            # 步骤索引越界
            try:
                update_step(plan_path, 99)
                failures += 1
                print("  [FAIL] 错误处理: 应抛出 E005")
            except PlanError as exc:
                assert exc.code == "E005", f"错误码错误: {exc.code}"

            # 非法状态
            try:
                update_step(plan_path, 1, status="invalid")
                failures += 1
                print("  [FAIL] 错误处理: 应抛出 E006")
            except PlanError as exc:
                assert exc.code == "E006", f"错误码错误: {exc.code}"

            print("  [PASS] 错误处理")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 错误处理: {exc}")

        # ---- 测试 8: 自定义备份目录 ----
        try:
            custom_dir = os.path.join(tmpdir, "backups")
            backup_path = backup_plan(plan_path, backup_dir=custom_dir)
            assert os.path.exists(backup_path), "自定义备份目录失败"
            assert os.path.dirname(backup_path) == custom_dir, "备份目录不正确"
            print("  [PASS] 自定义备份目录")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] 自定义备份目录: {exc}")

    # 汇总结果
    if failures == 0:
        print("自检全部通过 ✅")
        return 0
    else:
        print(f"自检失败: {failures} 项未通过 ❌")
        return 1


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="文件规划技能 - 持久化多步骤计划管理",
        epilog="示例: python main.py create plan.md --steps '步骤1,步骤2,步骤3'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件）",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # create 子命令
    create_parser = subparsers.add_parser("create", help="创建计划文件")
    create_parser.add_argument("--filepath", help="计划文件路径")
    create_parser.add_argument("--steps", required=False, help="步骤内容，用逗号分隔")
    create_parser.add_argument("--overwrite", action="store_true", help="覆盖已存在文件")

    # update 子命令
    update_parser = subparsers.add_parser("update", help="更新步骤状态")
    update_parser.add_argument("--filepath", help="计划文件路径")
    update_parser.add_argument("--index", type=int, required=False, help="步骤索引（从1开始）")
    update_parser.add_argument("--status", choices=[STATUS_PENDING, STATUS_DONE, STATUS_BLOCKED], help="新状态")
    update_parser.add_argument("--note", help="新备注")

    # backup 子命令
    backup_parser = subparsers.add_parser("backup", help="创建备份")
    backup_parser.add_argument("--filepath", help="计划文件路径")
    backup_parser.add_argument("--dir", help="备份目录")

    # verify 子命令
    verify_parser = subparsers.add_parser("verify", help="校验计划")
    verify_parser.add_argument("--filepath", help="计划文件路径")

    # progress 子命令
    progress_parser = subparsers.add_parser("progress", help="查看进度")
    progress_parser.add_argument("--filepath", help="计划文件路径")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)

    # 自检模式
    if args.selftest:
        return _selftest()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "create":
            steps = [{"content": s.strip()} for s in args.steps.split(",") if s.strip()]
            result = create_plan(args.filepath, steps, overwrite=args.overwrite)
            print(
                f"计划已创建: {result['filepath']} "
                f"(共 {result['total']} 步，已完成 {result['done']} 步)"
            )

        elif args.command == "update":
            result = update_step(
                args.filepath,
                args.index,
                status=args.status,
                note=args.note,
            )
            step = result["steps"][args.index - 1]
            print(
                f"步骤 {args.index} 已更新: [{step['status']}] {step['content']} "
                f"(总进度: {result['done']}/{result['total']})"
            )

        elif args.command == "backup":
            path = backup_plan(args.filepath, backup_dir=args.dir)
            print(f"备份已创建: {path}")

        elif args.command == "verify":
            result = verify_plan(args.filepath)
            if result["valid"]:
                print(f"校验通过: 共 {result['total']} 步，已完成 {result['done']} 步")
            else:
                print(f"校验发现 {len(result['issues'])} 个问题:")
                for issue in result["issues"]:
                    print(f"  - {issue}")
                return 1

        elif args.command == "progress":
            report = progress_report(args.filepath)
            print(
                f"进度: {report['done']}/{report['total']} "
                f"({report['percent']}%) - {report['status']}"
            )

        return 0

    except PlanError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
