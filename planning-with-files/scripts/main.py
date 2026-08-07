#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
planning-with-files 技能核心逻辑实现
基于文件的持久化规划，支持崩溃恢复与长任务跟踪
"""

import os
import sys
import json
import time
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "文件读取失败",
    "E004": "文件写入失败",
    "E005": "JSON解析失败",
    "E006": "任务状态无效",
    "E007": "任务不存在",
    "E008": "目录创建失败",
    "E009": "计划数据校验失败",
    "E010": "内部逻辑错误",
}


class PlanningError(Exception):
    """规划功能自定义异常"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


class PlanManager:
    """
    计划管理器
    负责计划的创建、加载、保存、任务状态管理和变更日志
    """

    # 合法的任务状态集合
    VALID_STATUSES = {"待办", "进行中", "已完成", "阻塞"}

    def __init__(self, plan_dir: Optional[str] = None):
        """
        初始化计划管理器
        :param plan_dir: 计划文件存储目录，默认为当前目录下的 plans 文件夹
        """
        self.plan_dir = Path(plan_dir) if plan_dir else Path.cwd() / "plans"
        self.current_plan = None
        self.current_plan_path = None
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """确保计划目录存在"""
        try:
            self.plan_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PlanningError("E008", f"无法创建计划目录: {exc}")

    def create_plan(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        创建新计划
        :param name: 计划名称
        :param description: 计划描述
        :return: 创建的计划数据
        """
        if not name or not name.strip():
            raise PlanningError("E001", "计划名称不能为空")

        plan_data = {
            "name": name.strip(),
            "description": description.strip(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "进行中",
            "tasks": [],
            "change_log": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "创建计划",
                    "detail": f"计划 '{name}' 已创建",
                }
            ],
        }

        # 生成文件名：时间戳_计划名.json
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").strip() or "plan"
        filename = f"{timestamp}_{safe_name}.json"
        filepath = self.plan_dir / filename

        self._save_plan(filepath, plan_data)
        self.current_plan = plan_data
        self.current_plan_path = filepath
        return plan_data

    def load_plan(self, filepath: str) -> Dict[str, Any]:
        """
        加载已有计划
        :param filepath: 计划文件路径
        :return: 计划数据
        """
        path = Path(filepath)
        if not path.exists():
            raise PlanningError("E002", f"计划文件不存在: {filepath}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
        except json.JSONDecodeError as exc:
            raise PlanningError("E005", f"JSON解析失败: {exc}")
        except OSError as exc:
            raise PlanningError("E003", f"文件读取失败: {exc}")

        # 校验计划数据基本结构
        self._validate_plan_data(plan_data)

        self.current_plan = plan_data
        self.current_plan_path = path
        return plan_data

    def _validate_plan_data(self, plan_data: Dict[str, Any]) -> None:
        """校验计划数据的合法性"""
        if not isinstance(plan_data, dict):
            raise PlanningError("E009", "计划数据格式错误")
        if "name" not in plan_data or "tasks" not in plan_data:
            raise PlanningError("E009", "计划数据缺少必要字段")
        if not isinstance(plan_data["tasks"], list):
            raise PlanningError("E009", "任务列表格式错误")

    def _save_plan(self, filepath: Path, plan_data: Dict[str, Any]) -> None:
        """
        保存计划到文件
        :param filepath: 文件路径
        :param plan_data: 计划数据
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(plan_data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise PlanningError("E004", f"文件写入失败: {exc}")

    def save_current(self) -> None:
        """保存当前计划到文件"""
        if self.current_plan is None or self.current_plan_path is None:
            raise PlanningError("E010", "当前没有加载计划")
        self._save_plan(self.current_plan_path, self.current_plan)

    def add_task(self, title: str, description: str = "") -> Dict[str, Any]:
        """
        添加任务到当前计划
        :param title: 任务标题
        :param description: 任务描述
        :return: 添加的任务
        """
        if self.current_plan is None:
            raise PlanningError("E010", "当前没有加载计划")
        if not title or not title.strip():
            raise PlanningError("E001", "任务标题不能为空")

        task = {
            "id": len(self.current_plan["tasks"]) + 1,
            "title": title.strip(),
            "description": description.strip(),
            "status": "待办",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        self.current_plan["tasks"].append(task)
        self._record_change("添加任务", f"添加任务: {title}")
        self._update_plan_timestamp()
        self.save_current()
        return task

    def update_task_status(self, task_id: int, new_status: str) -> Dict[str, Any]:
        """
        更新任务状态
        :param task_id: 任务ID
        :param new_status: 新状态（待办/进行中/已完成/阻塞）
        :return: 更新后的任务
        """
        if self.current_plan is None:
            raise PlanningError("E010", "当前没有加载计划")

        if new_status not in self.VALID_STATUSES:
            raise PlanningError("E006", f"无效的任务状态: {new_status}")

        task = self._find_task(task_id)
        if task is None:
            raise PlanningError("E007", f"任务不存在: {task_id}")

        old_status = task["status"]
        task["status"] = new_status
        task["updated_at"] = datetime.now().isoformat()
        self._record_change("更新任务状态", f"任务 '{task['title']}' 状态: {old_status} -> {new_status}")
        self._update_plan_timestamp()
        self.save_current()
        return task

    def _find_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查找任务"""
        for task in self.current_plan["tasks"]:
            if task["id"] == task_id:
                return task
        return None

    def remove_task(self, task_id: int) -> None:
        """
        删除任务
        :param task_id: 任务ID
        """
        if self.current_plan is None:
            raise PlanningError("E010", "当前没有加载计划")

        task = self._find_task(task_id)
        if task is None:
            raise PlanningError("E007", f"任务不存在: {task_id}")

        self.current_plan["tasks"] = [t for t in self.current_plan["tasks"] if t["id"] != task_id]
        self._record_change("删除任务", f"删除任务: {task['title']}")
        self._update_plan_timestamp()
        self.save_current()

    def get_progress(self) -> Dict[str, Any]:
        """
        获取计划进度统计
        :return: 进度统计数据
        """
        if self.current_plan is None:
            raise PlanningError("E010", "当前没有加载计划")

        tasks = self.current_plan["tasks"]
        total = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "已完成")
        in_progress = sum(1 for t in tasks if t["status"] == "进行中")
        blocked = sum(1 for t in tasks if t["status"] == "阻塞")
        pending = sum(1 for t in tasks if t["status"] == "待办")

        progress_percent = (completed / total * 100) if total > 0 else 0

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "pending": pending,
            "progress_percent": round(progress_percent, 1),
            "plan_name": self.current_plan["name"],
            "plan_status": self.current_plan["status"],
        }

    def get_next_action(self) -> Optional[str]:
        """
        获取下一步建议
        :return: 下一步建议文本
        """
        if self.current_plan is None:
            raise PlanningError("E010", "当前没有加载计划")

        # 查找第一个待办或进行中的任务
        for task in self.current_plan["tasks"]:
            if task["status"] in ("待办", "进行中"):
                return f"下一步: {task['title']} (状态: {task['status']})"

        if self.current_plan["status"] == "已完成":
            return "计划已完成，无需继续"
        return "所有任务已完成，可以结束计划"

    def _record_change(self, action: str, detail: str) -> None:
        """记录变更日志"""
        self.current_plan["change_log"].append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "detail": detail,
        })

    def _update_plan_timestamp(self) -> None:
        """更新计划时间戳"""
        self.current_plan["updated_at"] = datetime.now().isoformat()


def run_selftest() -> int:
    """
    运行自检
    使用内置硬编码样例数据，不依赖外部文件
    :return: 0表示成功，非0表示失败
    """
    print("开始自检...")

    try:
        # 使用临时目录作为计划目录
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PlanManager(tmpdir)

            # 测试1: 创建计划
            plan = manager.create_plan("测试计划", "自检用测试计划")
            assert plan["name"] == "测试计划", "计划名称错误"
            assert plan["status"] == "进行中", "计划初始状态错误"
            assert len(plan["tasks"]) == 0, "初始任务列表应为空"
            print("  [通过] 创建计划")

            # 测试2: 添加任务
            task1 = manager.add_task("任务一", "第一个测试任务")
            task2 = manager.add_task("任务二", "第二个测试任务")
            assert task1["id"] == 1, "第一个任务ID应为1"
            assert task2["id"] == 2, "第二个任务ID应为2"
            assert len(manager.current_plan["tasks"]) == 2, "任务数量应为2"
            print("  [通过] 添加任务")

            # 测试3: 更新任务状态
            manager.update_task_status(1, "进行中")
            manager.update_task_status(2, "已完成")
            task1_updated = manager._find_task(1)
            task2_updated = manager._find_task(2)
            assert task1_updated["status"] == "进行中", "任务1状态应为进行中"
            assert task2_updated["status"] == "已完成", "任务2状态应为已完成"
            print("  [通过] 更新任务状态")

            # 测试4: 进度统计
            progress = manager.get_progress()
            assert progress["total"] == 2, "总任务数应为2"
            assert progress["completed"] == 1, "已完成数应为1"
            assert progress["in_progress"] == 1, "进行中数应为1"
            assert progress["progress_percent"] > 0, "进度百分比应大于0"
            assert progress["progress_percent"] < 100, "进度百分比应小于100"
            print("  [通过] 进度统计")

            # 测试5: 下一步建议
            next_action = manager.get_next_action()
            assert next_action is not None, "应返回下一步建议"
            assert "任务一" in next_action, "下一步建议应指向任务一"
            print("  [通过] 下一步建议")

            # 测试6: 保存和重新加载
            manager.save_current()
            saved_path = manager.current_plan_path
            reloaded = manager.load_plan(str(saved_path))
            assert reloaded["name"] == "测试计划", "重新加载后计划名称应一致"
            assert len(reloaded["tasks"]) == 2, "重新加载后任务数应一致"
            assert reloaded["tasks"][0]["status"] == "进行中", "重新加载后任务状态应保留"
            print("  [通过] 保存与加载")

            # 测试7: 删除任务
            manager.remove_task(1)
            assert len(manager.current_plan["tasks"]) == 1, "删除后任务数应为1"
            assert manager.current_plan["tasks"][0]["id"] == 2, "剩余任务ID应为2"
            print("  [通过] 删除任务")

            # 测试8: 错误处理
            try:
                manager.update_task_status(999, "已完成")
                assert False, "应抛出任务不存在的错误"
            except PlanningError as exc:
                assert exc.code == "E007", f"错误码应为E007，实际为{exc.code}"

            try:
                manager.update_task_status(2, "无效状态")
                assert False, "应抛出无效状态的错误"
            except PlanningError as exc:
                assert exc.code == "E006", f"错误码应为E006，实际为{exc.code}"
            print("  [通过] 错误处理")

            # 测试9: 变更日志
            log_count = len(manager.current_plan["change_log"])
            assert log_count > 0, "变更日志不应为空"
            assert log_count >= 4, f"变更日志数量应至少为4，实际为{log_count}"
            print("  [通过] 变更日志")

        print("所有自检通过！")
        return 0

    except AssertionError as exc:
        print(f"自检失败: {exc}")
        return 1
    except PlanningError as exc:
        print(f"自检失败: [{exc.code}] {exc.message}")
        return 1
    except Exception as exc:
        print(f"自检异常: {exc}")
        return 1


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="planning-with-files - 基于文件的持久化规划工具",
        epilog="示例: python main.py --create \"我的计划\" --description \"计划描述\""
    )

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--dir", type=str, default=None, help="计划文件存储目录")

    # 操作参数
    parser.add_argument("--create", type=str, metavar="NAME", help="创建新计划")
    parser.add_argument("--description", type=str, default="", help="计划描述")
    parser.add_argument("--load", type=str, metavar="FILE", help="加载已有计划")
    parser.add_argument("--add-task", type=str, metavar="TITLE", help="添加任务")
    parser.add_argument("--task-desc", type=str, default="", help="任务描述")
    parser.add_argument("--update-status", type=str, nargs=2, metavar=("TASK_ID", "STATUS"), help="更新任务状态")
    parser.add_argument("--remove-task", type=int, metavar="TASK_ID", help="删除任务")
    parser.add_argument("--progress", action="store_true", help="显示进度")
    parser.add_argument("--next-action", action="store_true", help="显示下一步建议")

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        return run_selftest()

    try:
        manager = PlanManager(args.dir)

        # 创建新计划
        if args.create:
            plan = manager.create_plan(args.create, args.description)
            print(f"计划已创建: {plan['name']}")
            print(f"文件位置: {manager.current_plan_path}")
            return 0

        # 加载已有计划
        if args.load:
            plan = manager.load_plan(args.load)
            print(f"计划已加载: {plan['name']}")
            print(f"任务数量: {len(plan['tasks'])}")

        # 添加任务
        if args.add_task:
            if manager.current_plan is None:
                print("错误: 请先创建或加载计划", file=sys.stderr)
                return 1
            task = manager.add_task(args.add_task, args.task_desc)
            print(f"任务已添加: ID={task['id']}, 标题={task['title']}")

        # 更新任务状态
        if args.update_status:
            if manager.current_plan is None:
                print("错误: 请先创建或加载计划", file=sys.stderr)
                return 1
            task_id = int(args.update_status[0])
            status = args.update_status[1]
            task = manager.update_task_status(task_id, status)
            print(f"任务状态已更新: ID={task['id']}, 状态={task['status']}")

        # 删除任务
        if args.remove_task is not None:
            if manager.current_plan is None:
                print("错误: 请先创建或加载计划", file=sys.stderr)
                return 1
            manager.remove_task(args.remove_task)
            print(f"任务已删除: ID={args.remove_task}")

        # 显示进度
        if args.progress:
            if manager.current_plan is None:
                print("错误: 请先创建或加载计划", file=sys.stderr)
                return 1
            progress = manager.get_progress()
            print(f"计划: {progress['plan_name']} (状态: {progress['plan_status']})")
            print(f"总任务: {progress['total']}")
            print(f"已完成: {progress['completed']}")
            print(f"进行中: {progress['in_progress']}")
            print(f"阻塞: {progress['blocked']}")
            print(f"待办: {progress['pending']}")
            print(f"完成度: {progress['progress_percent']}%")

        # 显示下一步建议
        if args.next_action:
            if manager.current_plan is None:
                print("错误: 请先创建或加载计划", file=sys.stderr)
                return 1
            action = manager.get_next_action()
            print(action)

        # 如果没有执行任何操作
        if not any([args.create, args.load, args.add_task, args.update_status,
                    args.remove_task is not None, args.progress, args.next_action]):
            parser.print_help()
            return 0

        return 0

    except PlanningError as exc:
        print(f"错误: [{exc.code}] {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误: [E010] 未预期异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
