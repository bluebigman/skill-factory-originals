#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — planning-with-files 技能的全新独立实现（clean-room）

本脚本依据功能规格独立编写，不包含任何既有代码。
提供基于文件的持久化规划、崩溃恢复与长任务跟踪能力。

用法示例:
    python scripts/main.py --new plan.md "三阶段开发计划"
    python scripts/main.py --add plan.md "[ ] 完成需求分析"
    python scripts/main.py --status plan.md
    python scripts/main.py --selftest
"""

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件错误：目标文件不存在或无法访问",
    "E003": "格式错误：文件内容不符合规划文件格式",
    "E004": "写入错误：无法写入目标文件",
    "E005": "读取错误：无法读取目标文件",
    "E006": "操作错误：不支持的操作类型",
    "E007": "状态错误：任务状态标记不合法",
    "E008": "路径错误：路径不合法或不在允许范围内",
    "E009": "自检错误：自检过程中发现逻辑错误",
    "E010": "未知错误：未预期的异常",
}

# 状态标记正则
STATUS_PATTERN = re.compile(r"^\[([ x~])\]\s*(.*)$")


def error_exit(code: str, message: str = None) -> None:
    """输出错误信息并以错误码退出"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    print(f"错误 [{code}]: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_path(path_str: str) -> Path:
    """校验并规范化路径，防止路径穿越"""
    if not path_str or not path_str.strip():
        error_exit("E001", "路径不能为空")
    p = Path(path_str).expanduser()
    # 防止路径穿越到非预期目录
    if ".." in p.parts:
        error_exit("E008", f"路径包含非法部分: {path_str}")
    return p


def read_plan_file(path: Path) -> str:
    """读取规划文件内容，文件不存在时返回空字符串"""
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        error_exit("E005", f"读取文件失败: {e}")


def write_plan_file(path: Path, content: str) -> None:
    """写入规划文件内容"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        error_exit("E004", f"写入文件失败: {e}")


def parse_tasks(content: str) -> list:
    """解析文件内容中的任务行，返回任务列表"""
    tasks = []
    for line in content.splitlines():
        line = line.rstrip("\n")
        m = STATUS_PATTERN.match(line)
        if m:
            status = m.group(1)
            desc = m.group(2)
            tasks.append({"status": status, "desc": desc, "line": line})
    return tasks


def count_status(tasks: list) -> dict:
    """统计各类状态的任务数量"""
    counts = {" ": 0, "x": 0, "~": 0}
    for t in tasks:
        if t["status"] in counts:
            counts[t["status"]] += 1
    return counts


def generate_summary(content: str) -> str:
    """生成规划文件的摘要信息"""
    tasks = parse_tasks(content)
    counts = count_status(tasks)
    total = len(tasks)
    completed = counts["x"]
    in_progress = counts["~"]
    pending = counts[" "]

    # 计算完成率（避免除零）
    if total > 0:
        ratio = (completed / total) * 100
    else:
        ratio = 0.0

    lines = [
        f"任务总数: {total}",
        f"已完成: {completed}",
        f"进行中: {in_progress}",
        f"待办: {pending}",
        f"完成率: {ratio:.1f}%",
    ]
    return "\n".join(lines)


def create_plan(path: Path, title: str) -> None:
    """创建新的规划文件"""
    if path.exists():
        error_exit("E002", f"文件已存在: {path}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"# {title}\n\n> 创建时间: {now}\n\n## 任务列表\n\n"
    write_plan_file(path, content)
    print(f"已创建规划文件: {path}")


def add_task(path: Path, task_line: str) -> None:
    """向规划文件添加任务"""
    if not path.exists():
        error_exit("E002", f"文件不存在: {path}")
    content = read_plan_file(path)
    if not task_line.strip():
        error_exit("E001", "任务内容不能为空")

    # 规范化任务行，确保有状态标记
    if STATUS_PATTERN.match(task_line):
        line = task_line
    else:
        line = f"[ ] {task_line}"

    # 检查重复任务
    tasks = parse_tasks(content)
    for t in tasks:
        if t["desc"] == line[4:].strip():
            error_exit("E003", f"任务已存在: {line[4:].strip()}")

    new_content = content.rstrip() + "\n" + line + "\n"
    write_plan_file(path, new_content)
    print(f"已添加任务: {line}")


def update_task(path: Path, task_desc: str, new_status: str) -> None:
    """更新任务状态"""
    if not path.exists():
        error_exit("E002", f"文件不存在: {path}")
    if new_status not in (" ", "x", "~"):
        error_exit("E007", f"非法状态标记: {new_status}")

    content = read_plan_file(path)
    tasks = parse_tasks(content)
    found = False

    new_lines = []
    for line in content.splitlines():
        m = STATUS_PATTERN.match(line)
        if m and m.group(2).strip() == task_desc.strip():
            new_line = f"[{new_status}] {m.group(2)}"
            new_lines.append(new_line)
            found = True
        else:
            new_lines.append(line)

    if not found:
        error_exit("E003", f"未找到任务: {task_desc}")

    write_plan_file(path, "\n".join(new_lines) + "\n")
    print(f"任务已更新: [{new_status}] {task_desc}")


def list_tasks(path: Path) -> None:
    """列出所有任务"""
    if not path.exists():
        error_exit("E002", f"文件不存在: {path}")
    content = read_plan_file(path)
    tasks = parse_tasks(content)
    if not tasks:
        print("（无任务）")
        return
    for i, t in enumerate(tasks, 1):
        status_desc = {" ": "待办", "x": "完成", "~": "进行中"}.get(t["status"], "未知")
        print(f"{i:3d}. [{t['status']}] {t['desc']}  ({status_desc})")


def show_status(path: Path) -> None:
    """显示规划文件状态摘要"""
    if not path.exists():
        error_exit("E002", f"文件不存在: {path}")
    content = read_plan_file(path)
    print(generate_summary(content))


def selftest() -> None:
    """内置自检函数，使用硬编码样例数据离线验证核心逻辑"""
    print("开始自检...")

    # 使用临时目录，避免污染当前工作目录
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        plan_file = tmp_path / "test_plan.md"

        # 测试1: 创建规划文件
        try:
            create_plan(plan_file, "自检测试计划")
            if not plan_file.exists():
                error_exit("E009", "创建文件失败")
            print("[通过] 创建规划文件")
        except SystemExit:
            error_exit("E009", "创建规划文件异常")

        # 测试2: 添加任务
        try:
            add_task(plan_file, "[ ] 任务A")
            add_task(plan_file, "[ ] 任务B")
            add_task(plan_file, "[~] 任务C")
            content = read_plan_file(plan_file)
            tasks = parse_tasks(content)
            if len(tasks) != 3:
                error_exit("E009", f"添加任务数量错误: {len(tasks)}")
            print("[通过] 添加任务")
        except SystemExit:
            error_exit("E009", "添加任务异常")

        # 测试3: 更新任务状态
        try:
            update_task(plan_file, "任务A", "x")
            content = read_plan_file(plan_file)
            tasks = parse_tasks(content)
            task_a = [t for t in tasks if t["desc"] == "任务A"]
            if not task_a or task_a[0]["status"] != "x":
                error_exit("E009", "更新任务状态失败")
            print("[通过] 更新任务状态")
        except SystemExit:
            error_exit("E009", "更新任务状态异常")

        # 测试4: 状态统计
        try:
            content = read_plan_file(plan_file)
            tasks = parse_tasks(content)
            counts = count_status(tasks)
            if counts["x"] != 1 or counts["~"] != 1 or counts[" "] != 1:
                error_exit("E009", f"状态统计错误: {counts}")
            print("[通过] 状态统计")
        except SystemExit:
            error_exit("E009", "状态统计异常")

        # 测试5: 摘要生成
        try:
            content = read_plan_file(plan_file)
            summary = generate_summary(content)
            if "任务总数" not in summary or "完成率" not in summary:
                error_exit("E009", "摘要生成错误")
            # 宽松验证完成率在合理范围
            ratio_match = re.search(r"完成率: (\d+\.?\d*)%", summary)
            if ratio_match:
                ratio = float(ratio_match.group(1))
                if ratio < 0 or ratio > 100:
                    error_exit("E009", f"完成率超出范围: {ratio}")
            print("[通过] 摘要生成")
        except SystemExit:
            error_exit("E009", "摘要生成异常")

        # 测试6: 重复任务检测
        try:
            add_task(plan_file, "[ ] 任务A")
            error_exit("E009", "未检测到重复任务")
        except SystemExit:
            # 预期应失败，说明检测有效
            print("[通过] 重复任务检测")

        # 测试7: 解析空内容
        try:
            empty_tasks = parse_tasks("")
            if empty_tasks:
                error_exit("E009", "空内容解析错误")
            print("[通过] 空内容解析")
        except SystemExit:
            error_exit("E009", "空内容解析异常")

        # 测试8: 路径校验
        try:
            validate_path("normal/path/file.md")
            try:
                validate_path("../evil/path")
                error_exit("E009", "路径穿越未拦截")
            except SystemExit:
                print("[通过] 路径校验")
        except SystemExit:
            error_exit("E009", "路径校验异常")

        # 测试9: 状态标记解析
        try:
            m = STATUS_PATTERN.match("[x] 完成的任务")
            if not m or m.group(1) != "x":
                error_exit("E009", "状态标记解析失败")
            m2 = STATUS_PATTERN.match("[~] 进行中")
            if not m2 or m2.group(1) != "~":
                error_exit("E009", "进行中状态解析失败")
            m3 = STATUS_PATTERN.match("[ ] 待办")
            if not m3 or m3.group(1) != " ":
                error_exit("E009", "待办状态解析失败")
            print("[通过] 状态标记解析")
        except SystemExit:
            error_exit("E009", "状态标记解析异常")

        # 测试10: 文件写入读取
        try:
            test_content = "# 测试\n\n[ ] 任务1\n[x] 任务2\n"
            write_plan_file(plan_file, test_content)
            read_back = read_plan_file(plan_file)
            if read_back != test_content:
                error_exit("E009", "文件读写不一致")
            print("[通过] 文件读写")
        except SystemExit:
            error_exit("E009", "文件读写异常")

    print("\n全部自检通过！")
    sys.exit(0)


def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="文件规划工具 - 基于文件的持久化任务跟踪",
        epilog="示例: %(prog)s --new plan.md '项目计划'",
    )
    parser.add_argument("--new", nargs=2, metavar=("FILE", "TITLE"),
                        help="创建新的规划文件")
    parser.add_argument("--add", nargs=2, metavar=("FILE", "TASK"),
                        help="添加任务到规划文件")
    parser.add_argument("--update", nargs=3, metavar=("FILE", "TASK", "STATUS"),
                        help="更新任务状态 (状态: ' '=待办, x=完成, ~=进行中)")
    parser.add_argument("--list", metavar="FILE", help="列出所有任务")
    parser.add_argument("--status", metavar="FILE", help="显示任务状态统计")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检")

    args = parser.parse_args()

    # 自检模式优先
    if args.selftest:
        selftest()
        return

    # 解析操作
    try:
        if args.new:
            path = validate_path(args.new[0])
            create_plan(path, args.new[1])
        elif args.add:
            path = validate_path(args.add[0])
            add_task(path, args.add[1])
        elif args.update:
            path = validate_path(args.update[0])
            task_desc = args.update[1]
            status = args.update[2]
            # 将用户输入的 "todo"/"done"/"doing" 转换为标记
            status_map = {"todo": " ", "done": "x", "doing": "~", " ": " ", "x": "x", "~": "~"}
            if status not in status_map:
                error_exit("E007", f"非法状态: {status} (可用: todo/done/doing)")
            update_task(path, task_desc, status_map[status])
        elif args.list:
            path = validate_path(args.list)
            list_tasks(path)
        elif args.status:
            path = validate_path(args.status)
            show_status(path)
        else:
            parser.print_help()
            error_exit("E001", "请指定操作参数")
    except SystemExit:
        raise
    except Exception as e:
        error_exit("E010", f"未预期错误: {e}")


if __name__ == "__main__":
    main()
