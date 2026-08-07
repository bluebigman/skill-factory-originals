#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
todo-cli - 命令行待办事项管理工具

本脚本为 clean-room 独立实现，仅依据功能规格编写。
核心功能：待办事项的增删改查、状态管理、优先级排序、简单搜索。
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# 错误码常量定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "待办事项不存在",
    "E007": "待办事项ID无效",
    "E008": "文件读写失败",
    "E009": "参数冲突",
    "E010": "内部状态异常",
}

class TodoError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")

class TodoItem:
    """单个待办事项"""
    def __init__(self, title: str, description: str = "", priority: int = 3, due_date: str = ""):
        if not title or not title.strip():
            raise TodoError("E001", "待办事项标题不能为空")
        if priority < 1 or priority > 5:
            raise TodoError("E003", "优先级必须在1-5之间")
        
        self.id = id(self)  # 使用对象id作为临时id
        self.title = title.strip()
        self.description = description.strip()
        self.priority = priority
        self.due_date = due_date
        self.completed = False
        self.created_at = datetime.now()
        self.updated_at = self.created_at

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "due_date": self.due_date,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TodoItem":
        """从字典创建实例"""
        item = cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=data.get("priority", 3),
            due_date=data.get("due_date", ""),
        )
        item.id = data.get("id", id(item))
        item.completed = data.get("completed", False)
        item.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        item.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        return item

class TodoManager:
    """待办事项管理器"""
    def __init__(self, storage_path: str = ""):
        if not storage_path:
            # 默认使用当前目录下的 .todo-cli.json
            storage_path = str(Path.cwd() / ".todo-cli.json")
        self.storage_path = storage_path
        self.items: list[TodoItem] = []
        self.load()

    def load(self) -> None:
        """从文件加载数据"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.items = [TodoItem.from_dict(item) for item in data]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise TodoError("E008", f"加载数据失败: {e}")

    def save(self) -> None:
        """保存数据到文件"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([item.to_dict() for item in self.items], f, ensure_ascii=False, indent=2)
        except (IOError, OSError) as e:
            raise TodoError("E008", f"保存数据失败: {e}")

    def add(self, title: str, description: str = "", priority: int = 3, due_date: str = "") -> TodoItem:
        """添加新待办"""
        item = TodoItem(title, description, priority, due_date)
        self.items.append(item)
        self.save()
        return item

    def list_all(self, show_completed: bool = True) -> list[TodoItem]:
        """列出所有待办"""
        if show_completed:
            return sorted(self.items, key=lambda x: (x.completed, x.priority, x.due_date))
        return sorted([i for i in self.items if not i.completed], 
                     key=lambda x: (x.priority, x.due_date))

    def get_by_id(self, item_id: int) -> TodoItem:
        """根据ID查找待办"""
        for item in self.items:
            if item.id == item_id:
                return item
        raise TodoError("E006", f"待办事项ID={item_id}不存在")

    def toggle_complete(self, item_id: int) -> TodoItem:
        """切换完成状态"""
        item = self.get_by_id(item_id)
        item.completed = not item.completed
        item.updated_at = datetime.now()
        self.save()
        return item

    def delete(self, item_id: int) -> bool:
        """删除待办"""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                del self.items[i]
                self.save()
                return True
        raise TodoError("E006", f"待办事项ID={item_id}不存在")

    def update(self, item_id: int, title: str = "", description: str = "", 
               priority: int = 0, due_date: str = "") -> TodoItem:
        """更新待办信息"""
        item = self.get_by_id(item_id)
        if title:
            item.title = title.strip()
        if description:
            item.description = description.strip()
        if priority:
            if priority < 1 or priority > 5:
                raise TodoError("E003", "优先级必须在1-5之间")
            item.priority = priority
        if due_date:
            item.due_date = due_date
        item.updated_at = datetime.now()
        self.save()
        return item

    def search(self, keyword: str) -> list[TodoItem]:
        """搜索待办"""
        if not keyword:
            raise TodoError("E001", "搜索关键词不能为空")
        keyword = keyword.lower()
        return [item for item in self.items 
                if keyword in item.title.lower() or keyword in item.description.lower()]

    def stats(self) -> dict:
        """统计信息"""
        total = len(self.items)
        completed = sum(1 for i in self.items if i.completed)
        pending = total - completed
        urgent = sum(1 for i in self.items if not i.completed and i.priority <= 2)
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "urgent": urgent,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
        }

def format_item(item: TodoItem) -> str:
    """格式化单个待办项"""
    status = "[✓]" if item.completed else "[ ]"
    priority_str = "★" * item.priority
    due = f" 截止: {item.due_date}" if item.due_date else ""
    return f"{status} #{item.id} {item.title} (优先级:{priority_str}){due}"

def selftest() -> int:
    """内置自检函数，使用硬编码样例数据离线测试核心逻辑"""
    print("=== todo-cli 自检开始 ===")
    
    # 使用临时目录避免影响当前工作目录
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_todo.json")
        manager = TodoManager(storage_path)
        
        # 测试添加功能
        test_items = [
            {"title": "完成项目报告", "description": "编写季度总结报告", "priority": 1},
            {"title": "购买日用品", "description": "牛奶、面包、鸡蛋", "priority": 3},
            {"title": "预约牙医", "description": "复查牙齿矫正器", "priority": 2},
            {"title": "整理书架", "description": "按类别重新排列书籍", "priority": 5},
        ]
        
        for item_data in test_items:
            item = manager.add(**item_data)
            assert item.title, "添加待办后标题不应为空"
            assert item.priority >= 1 and item.priority <= 5, "优先级应在1-5之间"
            print(f"  添加成功: {format_item(item)}")
        
        # 测试列表功能
        all_items = manager.list_all()
        assert len(all_items) == 4, f"应有4个待办，实际{len(all_items)}个"
        print(f"  列表功能正常: 共{len(all_items)}个待办")
        
        # 测试完成状态切换
        first_item = all_items[0]
        manager.toggle_complete(first_item.id)
        updated_item = manager.get_by_id(first_item.id)
        assert updated_item.completed == True, "切换状态后应为已完成"
        print(f"  状态切换正常: {format_item(updated_item)}")
        
        # 测试搜索功能
        results = manager.search("报告")
        assert len(results) >= 1, "搜索'报告'应至少找到1个结果"
        print(f"  搜索功能正常: 找到{len(results)}个结果")
        
        # 测试更新功能
        item_to_update = all_items[1]
        manager.update(item_to_update.id, priority=1)
        updated = manager.get_by_id(item_to_update.id)
        assert updated.priority == 1, "更新后优先级应为1"
        print(f"  更新功能正常: {format_item(updated)}")
        
        # 测试统计功能
        stats = manager.stats()
        assert stats["total"] == 4, "总数应为4"
        assert stats["completed"] == 1, "已完成应为1"
        assert stats["pending"] == 3, "未完成应为3"
        assert stats["completion_rate"] > 0, "完成率应大于0"
        print(f"  统计功能正常: 总{stats['total']}个, 完成率{stats['completion_rate']:.1f}%")
        
        # 测试删除功能
        item_to_delete = all_items[2]
        manager.delete(item_to_delete.id)
        remaining = manager.list_all()
        assert len(remaining) == 3, "删除后应剩3个待办"
        print(f"  删除功能正常: 剩余{len(remaining)}个待办")
        
        # 测试持久化
        manager.save()
        assert os.path.exists(storage_path), "保存后文件应存在"
        manager2 = TodoManager(storage_path)
        assert len(manager2.items) == 3, "重新加载后应有3个待办"
        print("  持久化功能正常: 数据保存和加载成功")
        
        # 测试错误处理
        try:
            manager.get_by_id(99999)  # 不存在的ID
            assert False, "应抛出E006错误"
        except TodoError as e:
            assert e.code == "E006", f"错误码应为E006，实际为{e.code}"
            print(f"  错误处理正常: {e}")
        
        # 测试边界情况
        try:
            manager.add("")  # 空标题
            assert False, "应抛出E001错误"
        except TodoError as e:
            assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
            print(f"  边界处理正常: {e}")
        
        print("=== 自检完成: 所有测试通过 ===")
        return 0

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="✅ Command-line tool to manage Todo lists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s add "完成项目报告" -p 1 -d "2026-01-01"
  %(prog)s list
  %(prog)s done 1
  %(prog)s delete 1
  %(prog)s search "报告"
  %(prog)s stats
  %(prog)s --selftest
        """
    )
    
    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--storage", default="", help="数据存储文件路径")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # add 命令
    add_parser = subparsers.add_parser("add", help="添加新待办")
    add_parser.add_argument("title", help="待办标题")
    add_parser.add_argument("-d", "--description", default="", help="详细描述")
    add_parser.add_argument("-p", "--priority", type=int, default=3, 
                          choices=range(1, 6), help="优先级 1-5")
    add_parser.add_argument("--due", default="", help="截止日期")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有待办")
    list_parser.add_argument("--pending", action="store_true", help="仅显示未完成")
    
    # done 命令
    done_parser = subparsers.add_parser("done", help="切换完成状态")
    done_parser.add_argument("item_id", type=int, help="待办ID")
    
    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除待办")
    delete_parser.add_argument("item_id", type=int, help="待办ID")
    
    # update 命令
    update_parser = subparsers.add_parser("update", help="更新待办")
    update_parser.add_argument("item_id", type=int, help="待办ID")
    update_parser.add_argument("-t", "--title", default="", help="新标题")
    update_parser.add_argument("-d", "--description", default="", help="新描述")
    update_parser.add_argument("-p", "--priority", type=int, choices=range(1, 6), help="新优先级")
    update_parser.add_argument("--due", default="", help="新截止日期")
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索待办")
    search_parser.add_argument("keyword", help="搜索关键词")
    
    # stats 命令
    subparsers.add_parser("stats", help="显示统计信息")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return selftest()
    
    # 没有命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        manager = TodoManager(args.storage)
        
        if args.command == "add":
            item = manager.add(args.title, args.description, args.priority, args.due)
            print(f"已添加: {format_item(item)}")
            
        elif args.command == "list":
            items = manager.list_all(show_completed=not args.pending)
            if not items:
                print("暂无待办事项")
            else:
                for item in items:
                    print(format_item(item))
                    
        elif args.command == "done":
            item = manager.toggle_complete(args.item_id)
            status = "已完成" if item.completed else "已标记为未完成"
            print(f"{status}: {item.title}")
            
        elif args.command == "delete":
            manager.delete(args.item_id)
            print(f"已删除待办 #{args.item_id}")
            
        elif args.command == "update":
            item = manager.update(args.item_id, args.title, args.description, 
                                args.priority or 0, args.due)
            print(f"已更新: {format_item(item)}")
            
        elif args.command == "search":
            results = manager.search(args.keyword)
            if not results:
                print(f"未找到包含'{args.keyword}'的待办")
            else:
                print(f"找到{len(results)}个匹配项:")
                for item in results:
                    print(format_item(item))
                    
        elif args.command == "stats":
            stats = manager.stats()
            print(f"总计: {stats['total']} 个待办")
            print(f"已完成: {stats['completed']} 个")
            print(f"未完成: {stats['pending']} 个")
            print(f"紧急事项: {stats['urgent']} 个")
            print(f"完成率: {stats['completion_rate']:.1f}%")
            
        return 0
        
    except TodoError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130

if __name__ == "__main__":
    sys.exit(main())
