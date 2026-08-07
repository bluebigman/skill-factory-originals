#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
todo-cli - 命令行待办事项管理工具
版本: 1.0.0
许可证: MIT
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定",
    "E006": "任务不存在",
    "E007": "任务ID格式错误",
    "E008": "状态值不合法",
    "E009": "日期格式错误",
    "E010": "文件读写失败",
}


class TodoError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
class TodoItem:
    """待办事项数据模型"""

    def __init__(
        self,
        task_id: int,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: int = 1,
        completed: bool = False,
        created_at: Optional[str] = None,
    ):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.completed = completed
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "id": self.task_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "priority": self.priority,
            "completed": self.completed,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TodoItem":
        """从字典创建对象"""
        return cls(
            task_id=data.get("id", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            due_date=data.get("due_date"),
            priority=data.get("priority", 1),
            completed=data.get("completed", False),
            created_at=data.get("created_at"),
        )

    def validate(self) -> None:
        """验证数据完整性"""
        if not self.title or not self.title.strip():
            raise TodoError("E002", "任务标题不能为空")
        if self.priority < 0 or self.priority > 3:
            raise TodoError("E002", "优先级必须在0-3之间")
        if self.due_date:
            try:
                datetime.strptime(self.due_date, "%Y-%m-%d")
            except ValueError:
                raise TodoError("E009", f"日期格式错误: {self.due_date}")


# ---------------------------------------------------------------------------
# 存储管理器
# ---------------------------------------------------------------------------
class TodoStorage:
    """待办事项存储管理"""

    def __init__(self, filepath: str = "todos.json"):
        self.filepath = filepath
        self.todos: Dict[int, TodoItem] = {}
        self._next_id = 1
        self._load()

    def _load(self) -> None:
        """从文件加载数据"""
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.todos = {}
            for item_data in data:
                item = TodoItem.from_dict(item_data)
                self.todos[item.task_id] = item
            if self.todos:
                self._next_id = max(self.todos.keys()) + 1
        except (json.JSONDecodeError, OSError) as e:
            raise TodoError("E010", f"读取文件失败: {e}")

    def _save(self) -> None:
        """保存数据到文件"""
        try:
            data = [todo.to_dict() for todo in self.todos.values()]
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise TodoError("E010", f"写入文件失败: {e}")

    def add(self, item: TodoItem) -> TodoItem:
        """添加新任务"""
        item.validate()
        item.task_id = self._next_id
        self.todos[item.task_id] = item
        self._next_id += 1
        self._save()
        return item

    def get(self, task_id: int) -> Optional[TodoItem]:
        """获取指定任务"""
        return self.todos.get(task_id)

    def update(self, task_id: int, **kwargs) -> Optional[TodoItem]:
        """更新任务"""
        item = self.todos.get(task_id)
        if not item:
            raise TodoError("E006", f"任务 {task_id} 不存在")
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        item.validate()
        self._save()
        return item

    def delete(self, task_id: int) -> bool:
        """删除任务"""
        if task_id not in self.todos:
            raise TodoError("E006", f"任务 {task_id} 不存在")
        del self.todos[task_id]
        self._save()
        return True

    def list_all(self, completed: Optional[bool] = None) -> List[TodoItem]:
        """列出所有任务"""
        items = list(self.todos.values())
        if completed is not None:
            items = [i for i in items if i.completed == completed]
        return sorted(items, key=lambda x: (x.priority, x.created_at))


# ---------------------------------------------------------------------------
# 核心业务逻辑
# ---------------------------------------------------------------------------
class TodoManager:
    """待办事项管理器"""

    def __init__(self, storage: TodoStorage):
        self.storage = storage

    def add_task(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: int = 1,
    ) -> TodoItem:
        """添加新任务"""
        if not title or not title.strip():
            raise TodoError("E001", "任务标题不能为空")
        
        # 提前验证日期格式
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                raise TodoError("E009", f"日期格式错误: {due_date}")
        
        item = TodoItem(
            task_id=0,
            title=title.strip(),
            description=description.strip() if description else "",
            due_date=due_date,
            priority=priority,
        )
        return self.storage.add(item)

    def complete_task(self, task_id: int) -> Optional[TodoItem]:
        """完成任务"""
        if task_id <= 0:
            raise TodoError("E007", f"无效的任务ID: {task_id}")
        return self.storage.update(task_id, completed=True)

    def uncomplete_task(self, task_id: int) -> Optional[TodoItem]:
        """取消完成任务"""
        if task_id <= 0:
            raise TodoError("E007", f"无效的任务ID: {task_id}")
        return self.storage.update(task_id, completed=False)

    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        if task_id <= 0:
            raise TodoError("E007", f"无效的任务ID: {task_id}")
        return self.storage.delete(task_id)

    def list_tasks(self, status: str = "all") -> List[TodoItem]:
        """列出任务"""
        if status == "completed":
            return self.storage.list_all(completed=True)
        elif status == "pending":
            return self.storage.list_all(completed=False)
        elif status == "all":
            return self.storage.list_all()
        else:
            raise TodoError("E008", f"无效的状态值: {status}")

    def get_task(self, task_id: int) -> Optional[TodoItem]:
        """获取单个任务"""
        if task_id <= 0:
            raise TodoError("E007", f"无效的任务ID: {task_id}")
        return self.storage.get(task_id)


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_task_list(tasks: List[TodoItem], verbose: bool = False) -> str:
    """格式化任务列表输出"""
    if not tasks:
        return "暂无任务"

    lines = []
    lines.append(f"共 {len(tasks)} 个任务:")
    lines.append("-" * 60)

    for item in tasks:
        status = "✓" if item.completed else "□"
        priority_str = "!" * item.priority if item.priority > 0 else " "
        due_str = f" [截止: {item.due_date}]" if item.due_date else ""
        lines.append(f"{status} [{item.task_id}] {item.title} {priority_str}{due_str}")
        if verbose and item.description:
            lines.append(f"    描述: {item.description}")
        if verbose and item.created_at:
            lines.append(f"    创建: {item.created_at}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="待办事项管理工具",
        epilog="示例: todo-cli add '完成任务' -d '完成规格文档' -p 2",
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行内置自检测试"
    )
    parser.add_argument(
        "--file", default="todos.json", help="数据文件路径 (默认: todos.json)"
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加新任务")
    add_parser.add_argument("title", help="任务标题")
    add_parser.add_argument("-d", "--description", default="", help="任务描述")
    add_parser.add_argument("-t", "--due-date", help="截止日期 (YYYY-MM-DD)")
    add_parser.add_argument("-p", "--priority", type=int, default=1, help="优先级 (0-3)")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出任务")
    list_parser.add_argument(
        "-s", "--status", choices=["all", "completed", "pending"], default="all",
        help="任务状态筛选"
    )
    list_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    # complete 命令
    complete_parser = subparsers.add_parser("complete", help="完成任务")
    complete_parser.add_argument("task_id", type=int, help="任务ID")

    # uncomplete 命令
    uncomplete_parser = subparsers.add_parser("uncomplete", help="恢复任务")
    uncomplete_parser.add_argument("task_id", type=int, help="任务ID")

    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除任务")
    delete_parser.add_argument("task_id", type=int, help="任务ID")

    # show 命令
    show_parser = subparsers.add_parser("show", help="查看任务详情")
    show_parser.add_argument("task_id", type=int, help="任务ID")

    return parser


def run_command(args: argparse.Namespace) -> int:
    """执行命令行命令"""
    if args.selftest:
        return run_selftest()

    storage = TodoStorage(args.file)
    manager = TodoManager(storage)

    if not args.command:
        print("请指定操作命令，使用 --help 查看帮助")
        return 1

    try:
        if args.command == "add":
            item = manager.add_task(
                title=args.title,
                description=args.description,
                due_date=args.due_date,
                priority=args.priority,
            )
            print(f"任务已添加: [{item.task_id}] {item.title}")

        elif args.command == "list":
            tasks = manager.list_tasks(args.status)
            print(format_task_list(tasks, args.verbose))

        elif args.command == "complete":
            item = manager.complete_task(args.task_id)
            if item:
                print(f"任务已完成: [{item.task_id}] {item.title}")

        elif args.command == "uncomplete":
            item = manager.uncomplete_task(args.task_id)
            if item:
                print(f"任务已恢复: [{item.task_id}] {item.title}")

        elif args.command == "delete":
            manager.delete_task(args.task_id)
            print(f"任务已删除: {args.task_id}")

        elif args.command == "show":
            item = manager.get_task(args.task_id)
            if item:
                print(format_task_list([item], verbose=True))
            else:
                print(f"任务不存在: {args.task_id}")

        else:
            print(f"未知命令: {args.command}")
            return 1

        return 0

    except TodoError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 自检测试
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行内置自检测试"""
    print("开始运行自检测试...")

    # 创建临时存储
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        storage = TodoStorage(tmp_path)
        manager = TodoManager(storage)

        # 测试1: 添加任务
        item1 = manager.add_task("完成规格文档", "编写详细规格说明", "2026-01-01", 2)
        assert item1.task_id > 0, "任务ID应为正数"
        assert item1.title == "完成规格文档", "任务标题不匹配"
        assert item1.priority == 2, "优先级不匹配"
        print("✓ 添加任务测试通过")

        # 测试2: 批量添加
        item2 = manager.add_task("代码审查", priority=1)
        item3 = manager.add_task("发布版本", "发布v1.0.0", "2026-01-15", 3)
        assert item2.task_id > item1.task_id, "任务ID应递增"
        assert item3.task_id > item2.task_id, "任务ID应递增"
        print("✓ 批量添加测试通过")

        # 测试3: 完成任务
        completed = manager.complete_task(item1.task_id)
        assert completed is not None, "完成任务失败"
        assert completed.completed is True, "任务应标记为完成"
        print("✓ 完成任务测试通过")

        # 测试4: 列出任务
        all_tasks = manager.list_tasks("all")
        assert len(all_tasks) == 3, "应列出3个任务"
        completed_tasks = manager.list_tasks("completed")
        assert len(completed_tasks) == 1, "应列出1个已完成任务"
        pending_tasks = manager.list_tasks("pending")
        assert len(pending_tasks) == 2, "应列出2个未完成任务"
        print("✓ 任务列表测试通过")

        # 测试5: 获取任务
        fetched = manager.get_task(item2.task_id)
        assert fetched is not None, "获取任务失败"
        assert fetched.title == "代码审查", "任务标题不匹配"
        print("✓ 获取任务测试通过")

        # 测试6: 恢复任务
        restored = manager.uncomplete_task(item1.task_id)
        assert restored is not None, "恢复任务失败"
        assert restored.completed is False, "任务应恢复为未完成"
        print("✓ 恢复任务测试通过")

        # 测试7: 删除任务
        assert manager.delete_task(item3.task_id), "删除任务失败"
        remaining = manager.list_tasks("all")
        assert len(remaining) == 2, "删除后应剩2个任务"
        print("✓ 删除任务测试通过")

        # 测试8: 错误处理
        try:
            manager.add_task("", "空标题测试")
            assert False, "空标题应抛出异常"
        except TodoError as e:
            assert e.code == "E001", f"错误码应为E001，实际: {e.code}"
        print("✓ 错误处理测试通过")

        # 测试9: 日期验证
        try:
            manager.add_task("日期测试", due_date="2026/01/01")
            assert False, "非法日期应抛出异常"
        except TodoError as e:
            assert e.code == "E009", f"错误码应为E009，实际: {e.code}"
        print("✓ 日期验证测试通过")

        # 测试10: 持久化验证
        storage2 = TodoStorage(tmp_path)
        assert len(storage2.todos) == 2, "持久化后应仍有2个任务"
        print("✓ 持久化测试通过")

        print("\n所有自检测试通过！")
        return 0

    except AssertionError as e:
        print(f"自检失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"自检过程中发生错误: {e}", file=sys.stderr)
        return 1
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主程序入口"""
    parser = build_parser()
    args = parser.parse_args()
    return run_command(args)


if __name__ == "__main__":
    sys.exit(main())
