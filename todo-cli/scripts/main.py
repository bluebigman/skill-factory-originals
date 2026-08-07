#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
todo-cli: 命令行待办事项管理工具

基于功能规格独立实现（clean-room），仅使用标准库。
支持添加、列出、完成、删除待办事项，并包含离线自检功能。
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# ============================================================
# 错误码定义（对应规格第四章）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空：请提供待处理的内容",
    "E002": "关键信息缺失：请补充必要参数",
    "E003": "输入格式错误：参数格式不符合要求",
    "E004": "超出能力边界：操作不被支持",
    "E005": "置信度过低：结果无法确定",
    "E006": "文件读写失败：无法访问数据文件",
    "E007": "数据损坏：存储内容无法解析",
    "E008": "待办不存在：找不到指定ID",
    "E009": "参数冲突：提供的参数互相矛盾",
    "E010": "内部错误：未预期的异常",
}


class TodoError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据模型
# ============================================================
class TodoItem:
    """单条待办事项"""

    def __init__(self, title: str, description: str = "", due_date: str = ""):
        if not title or not title.strip():
            raise TodoError("E001", "待办标题不能为空")
        self.id = None  # 由存储层分配
        self.title = title.strip()
        self.description = description.strip()
        self.due_date = due_date.strip()
        self.completed = False
        self.created_at = datetime.now().isoformat(timespec="seconds")
        self.completed_at = None

    def to_dict(self) -> dict:
        """转为字典，便于序列化"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TodoItem":
        """从字典恢复对象"""
        item = cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            due_date=data.get("due_date", ""),
        )
        item.id = data.get("id")
        item.completed = data.get("completed", False)
        item.created_at = data.get("created_at", "")
        item.completed_at = data.get("completed_at")
        return item


# ============================================================
# 存储层（JSON 文件）
# ============================================================
class TodoStorage:
    """基于 JSON 文件的持久化存储"""

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self._next_id = 1
        self._items = []
        self._load()

    def _load(self):
        """从文件加载数据"""
        try:
            if self.filepath.exists():
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._items = [TodoItem.from_dict(x) for x in data.get("items", [])]
                self._next_id = data.get("next_id", 1)
                # 确保 next_id 大于所有现有 ID
                for item in self._items:
                    if item.id is not None and item.id >= self._next_id:
                        self._next_id = item.id + 1
        except json.JSONDecodeError:
            raise TodoError("E007", f"数据文件损坏: {self.filepath}")
        except OSError:
            raise TodoError("E006", f"无法读取文件: {self.filepath}")

    def _save(self):
        """保存数据到文件"""
        try:
            # 确保父目录存在
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "next_id": self._next_id,
                "items": [x.to_dict() for x in self._items],
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            raise TodoError("E006", f"无法写入文件: {self.filepath}")

    def add(self, item: TodoItem) -> TodoItem:
        """添加新待办"""
        item.id = self._next_id
        self._next_id += 1
        self._items.append(item)
        self._save()
        return item

    def list(self, include_completed: bool = True) -> list:
        """列出待办，可按完成状态过滤"""
        if include_completed:
            return list(self._items)
        return [x for x in self._items if not x.completed]

    def get(self, item_id: int) -> TodoItem:
        """按 ID 获取待办"""
        for item in self._items:
            if item.id == item_id:
                return item
        raise TodoError("E008", f"待办 ID={item_id} 不存在")

    def complete(self, item_id: int) -> TodoItem:
        """标记待办为完成"""
        item = self.get(item_id)
        if not item.completed:
            item.completed = True
            item.completed_at = datetime.now().isoformat(timespec="seconds")
            self._save()
        return item

    def delete(self, item_id: int) -> bool:
        """删除待办"""
        for i, item in enumerate(self._items):
            if item.id == item_id:
                del self._items[i]
                self._save()
                return True
        raise TodoError("E008", f"待办 ID={item_id} 不存在")


# ============================================================
# 业务逻辑层
# ============================================================
class TodoService:
    """待办事项核心业务"""

    def __init__(self, storage: TodoStorage):
        self.storage = storage

    def add_todo(self, title: str, description: str = "", due_date: str = "") -> TodoItem:
        """添加待办"""
        if not title:
            raise TodoError("E001")
        return self.storage.add(TodoItem(title, description, due_date))

    def list_todos(self, show_all: bool = True) -> list:
        """列出待办"""
        return self.storage.list(include_completed=show_all)

    def complete_todo(self, item_id: int) -> TodoItem:
        """完成待办"""
        return self.storage.complete(item_id)

    def delete_todo(self, item_id: int) -> bool:
        """删除待办"""
        return self.storage.delete(item_id)

    def stats(self) -> dict:
        """统计信息"""
        items = self.storage.list()
        total = len(items)
        completed = sum(1 for x in items if x.completed)
        pending = total - completed
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
        }


# ============================================================
# 输出格式化
# ============================================================
def format_todo_item(item: TodoItem) -> str:
    """格式化单条待办"""
    status = "[✓]" if item.completed else "[ ]"
    due = f" 截止: {item.due_date}" if item.due_date else ""
    desc = f" 描述: {item.description}" if item.description else ""
    return f"{status} #{item.id} {item.title}{due}{desc}"


def format_todo_list(items: list) -> str:
    """格式化待办列表"""
    if not items:
        return "（暂无待办事项）"
    lines = [format_todo_item(item) for item in items]
    return "\n".join(lines)


def format_stats(stats: dict) -> str:
    """格式化统计信息"""
    return (
        f"总计: {stats['total']} | "
        f"已完成: {stats['completed']} | "
        f"待处理: {stats['pending']} | "
        f"完成率: {stats['completion_rate']:.1f}%"
    )


# ============================================================
# 自检模块（离线、不依赖外部环境）
# ============================================================
def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不访问网络。
    断言采用宽松阈值，确保稳定性。
    """
    print("=== todo-cli 自检开始 ===")
    failures = 0

    # 使用临时目录，避免污染工作目录
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_todos.json")
        storage = TodoStorage(db_path)
        service = TodoService(storage)

        # --- 测试1: 添加待办 ---
        try:
            item1 = service.add_todo("完成项目报告", "月度总结", "2026-01-31")
            item2 = service.add_todo("购买生日礼物")
            item3 = service.add_todo("预约体检", due_date="2026-02-15")

            assert item1.id is not None, "ID 不应为空"
            assert item2.id == item1.id + 1, "ID 应递增"
            assert item3.id == item2.id + 1, "ID 应递增"
            assert not item1.completed, "新待办不应是完成状态"
            print("  [PASS] 添加待办功能正常")
        except AssertionError as e:
            failures += 1
            print(f"  [FAIL] 添加待办: {e}")
        except TodoError as e:
            failures += 1
            print(f"  [FAIL] 添加待办异常: {e}")

        # --- 测试2: 列出待办 ---
        try:
            all_items = service.list_todos()
            assert len(all_items) == 3, f"应列出3条，实际{len(all_items)}"

            pending_items = service.list_todos(show_all=False)
            assert len(pending_items) == 3, f"应列出3条未完成，实际{len(pending_items)}"

            # 宽松验证：所有待办标题非空
            for item in all_items:
                assert item.title.strip(), "标题不应为空字符串"
            print("  [PASS] 列出待办功能正常")
        except AssertionError as e:
            failures += 1
            print(f"  [FAIL] 列出待办: {e}")
        except TodoError as e:
            failures += 1
            print(f"  [FAIL] 列出待办异常: {e}")

        # --- 测试3: 完成待办 ---
        try:
            completed = service.complete_todo(item1.id)
            assert completed.completed, "待办应标记为完成"
            assert completed.completed_at is not None, "完成时间不应为空"

            # 完成后再列出
            pending_after = service.list_todos(show_all=False)
            assert len(pending_after) == 2, f"应剩2条未完成，实际{len(pending_after)}"
            print("  [PASS] 完成待办功能正常")
        except AssertionError as e:
            failures += 1
            print(f"  [FAIL] 完成待办: {e}")
        except TodoError as e:
            failures += 1
            print(f"  [FAIL] 完成待办异常: {e}")

        # --- 测试4: 统计信息 ---
        try:
            stats = service.stats()
            assert stats["total"] == 3, f"总数应为3，实际{stats['total']}"
            assert stats["completed"] == 1, f"完成数应为1，实际{stats['completed']}"
            assert stats["pending"] == 2, f"待处理应为2，实际{stats['pending']}"
            # 宽松验证：完成率应在合理范围
            assert 0 <= stats["completion_rate"] <= 100, "完成率应在0-100之间"
            assert stats["completion_rate"] > 30, f"完成率应大于30%，实际{stats['completion_rate']:.1f}%"
            assert stats["completion_rate"] < 40, f"完成率应小于40%，实际{stats['completion_rate']:.1f}%"
            print("  [PASS] 统计功能正常")
        except AssertionError as e:
            failures += 1
            print(f"  [FAIL] 统计功能: {e}")
        except TodoError as e:
            failures += 1
            print(f"  [FAIL] 统计功能异常: {e}")

        # --- 测试5: 删除待办 ---
        try:
            deleted = service.delete_todo(item2.id)
            assert deleted, "删除应返回 True"

            remaining = service.list_todos()
            assert len(remaining) == 2, f"删除后应剩2条，实际{len(remaining)}"

            # 验证删除的 ID 不再存在
            ids = [x.id for x in remaining]
            assert item2.id not in ids, "删除的 ID 不应存在"
            print("  [PASS] 删除待办功能正常")
        except AssertionError as e:
            failures += 1
            print(f"  [FAIL] 删除待办: {e}")
        except TodoError as e:
            failures += 1
            print(f"  [FAIL] 删除待办异常: {e}")

        # --- 测试6: 错误处理 ---
        try:
            # 空标题
            try:
                service.add_todo("")
                failures += 1
                print("  [FAIL] 空标题应抛出 E001")
            except TodoError as e:
                assert e.code == "E001", f"错误码应为E001，实际{e.code}"
                print("  [PASS] 空标题错误处理正常")

            # 不存在的 ID
            try:
                service.complete_todo(9999)
                failures += 1
                print("  [FAIL] 不存在的 ID 应抛出 E008")
            except TodoError as e:
                assert e.code == "E008", f"错误码应为E008，实际{e.code}"
                print("  [PASS] 不存在 ID 错误处理正常")
        except AssertionError as e:
            failures += 1
            print(f"  [FAIL] 错误处理: {e}")

        # --- 测试7: 持久化 ---
        try:
            # 重新加载存储（模拟重启）
            storage2 = TodoStorage(db_path)
            service2 = TodoService(storage2)
            items = service2.list_todos()
            assert len(items) == 2, f"持久化后应剩2条，实际{len(items)}"
            # 验证数据一致性
            titles = [x.title for x in items]
            assert "完成项目报告" in titles, "标题应保留"
            assert "预约体检" in titles, "标题应保留"
            print("  [PASS] 数据持久化正常")
        except AssertionError as e:
            failures += 1
            print(f"  [FAIL] 数据持久化: {e}")
        except TodoError as e:
            failures += 1
            print(f"  [FAIL] 数据持久化异常: {e}")

    # 汇总
    print(f"\n=== 自检完成: {'全部通过' if failures == 0 else f'{failures} 项失败'} ===")
    return 0 if failures == 0 else 1


# ============================================================
# 命令行入口
# ============================================================
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="todo-cli",
        description="✅ Command-line tool to manage Todo lists",
        epilog="示例: todo-cli add '完成报告' -d '季度总结' --due 2026-01-31",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线、无需外部依赖）",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加待办")
    add_parser.add_argument("title", help="待办标题（必填）")
    add_parser.add_argument("-d", "--description", default="", help="待办描述")
    add_parser.add_argument("--due", dest="due_date", default="", help="截止日期 (YYYY-MM-DD)")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出待办")
    list_parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="显示所有待办（默认）",
    )
    list_parser.add_argument(
        "--pending",
        action="store_true",
        help="仅显示未完成的待办",
    )

    # complete 命令
    complete_parser = subparsers.add_parser("complete", help="标记待办为完成")
    complete_parser.add_argument("id", type=int, help="待办 ID")

    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除待办")
    delete_parser.add_argument("id", type=int, help="待办 ID")

    # stats 命令
    subparsers.add_parser("stats", help="显示统计信息")

    return parser.parse_args()


def get_default_db_path() -> str:
    """获取默认数据库路径"""
    # 优先使用环境变量，否则使用用户目录
    env_path = os.environ.get("TODO_CLI_DB")
    if env_path:
        return env_path
    home = Path.home()
    return str(home / ".todo-cli" / "todos.json")


def main() -> int:
    """主入口函数"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无命令时显示帮助
    if not hasattr(args, "command") or args.command is None:
        print("请指定操作命令。使用 --help 查看帮助。")
        return 1

    try:
        # 初始化存储和服务
        db_path = get_default_db_path()
        storage = TodoStorage(db_path)
        service = TodoService(storage)

        # 执行命令
        if args.command == "add":
            item = service.add_todo(args.title, args.description, args.due_date)
            print(f"✓ 已添加待办 #{item.id}: {item.title}")

        elif args.command == "list":
            show_all = not args.pending
            items = service.list_todos(show_all=show_all)
            print(format_todo_list(items))

        elif args.command == "complete":
            item = service.complete_todo(args.id)
            print(f"✓ 已完成待办 #{item.id}: {item.title}")

        elif args.command == "delete":
            deleted = service.delete_todo(args.id)
            if deleted:
                print(f"✓ 已删除待办 #{args.id}")

        elif args.command == "stats":
            stats = service.stats()
            print(format_stats(stats))

        else:
            raise TodoError("E004", f"未知命令: {args.command}")

        return 0

    except TodoError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[E010] 内部错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
