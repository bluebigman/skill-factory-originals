#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
todo-cli: 命令行待办事项管理工具
版本: 1.0.0
版权: 原创作者（自持版权）
许可证: MIT
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 错误码常量
# ============================================================
class ErrorCode:
    """错误码定义"""
    E001 = "E001: 输入为空，请提供待处理的内容"
    E002 = "E002: 关键信息缺失，请补充必要字段"
    E003 = "E003: 输入格式错误，请检查格式"
    E004 = "E004: 超出能力边界，无法处理该请求"
    E005 = "E005: 置信度过低，结果无法确定"
    E006 = "E006: 文件读写失败"
    E007 = "E007: 无效的命令参数"
    E008 = "E008: 待办事项不存在"
    E009 = "E009: 存储目录不可用"
    E010 = "E010: 内部逻辑错误"


# ============================================================
# 数据模型
# ============================================================
class TodoItem:
    """待办事项数据模型"""
    
    def __init__(self, task_id, title, description="", priority="medium", 
                 due_date=None, completed=False, created_at=None):
        self.id = task_id
        self.title = title
        self.description = description
        self.priority = priority  # low, medium, high
        self.due_date = due_date  # ISO 格式字符串
        self.completed = completed
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "due_date": self.due_date,
            "completed": self.completed,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            task_id=data.get("id"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=data.get("priority", "medium"),
            due_date=data.get("due_date"),
            completed=data.get("completed", False),
            created_at=data.get("created_at")
        )


# ============================================================
# 核心存储层
# ============================================================
class TodoStorage:
    """待办事项存储管理"""
    
    def __init__(self, storage_path=None):
        """初始化存储"""
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # 默认使用临时目录，避免污染工作目录
            self.storage_path = Path(tempfile.gettempdir()) / "todo_cli_data"
        
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise RuntimeError(ErrorCode.E009)
        
        self.data_file = self.storage_path / "todos.json"
        self._load()
    
    def _load(self):
        """加载数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                self.todos = [TodoItem.from_dict(item) for item in raw_data]
            except (json.JSONDecodeError, OSError):
                # 数据文件损坏时备份并重新开始
                backup = self.data_file.with_suffix(".bak")
                try:
                    if self.data_file.exists():
                        os.replace(self.data_file, backup)
                except OSError:
                    pass
                self.todos = []
        else:
            self.todos = []
    
    def _save(self):
        """保存数据"""
        try:
            data = [todo.to_dict() for todo in self.todos]
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            raise RuntimeError(ErrorCode.E006)
    
    def add(self, title, description="", priority="medium", due_date=None):
        """添加待办事项"""
        if not title or not title.strip():
            raise ValueError(ErrorCode.E001)
        
        # 生成新 ID
        new_id = 1
        if self.todos:
            new_id = max(todo.id for todo in self.todos) + 1
        
        todo = TodoItem(
            task_id=new_id,
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            due_date=due_date
        )
        self.todos.append(todo)
        self._save()
        return todo
    
    def list_all(self, show_completed=True):
        """列出所有待办事项"""
        if show_completed:
            return self.todos.copy()
        return [t for t in self.todos if not t.completed]
    
    def get_by_id(self, todo_id):
        """按 ID 查找"""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None
    
    def complete(self, todo_id):
        """标记完成"""
        todo = self.get_by_id(todo_id)
        if not todo:
            raise ValueError(ErrorCode.E008)
        todo.completed = True
        self._save()
        return todo
    
    def delete(self, todo_id):
        """删除待办事项"""
        todo = self.get_by_id(todo_id)
        if not todo:
            raise ValueError(ErrorCode.E008)
        self.todos.remove(todo)
        self._save()
        return todo
    
    def search(self, keyword):
        """搜索待办事项"""
        keyword = keyword.lower()
        results = []
        for todo in self.todos:
            if keyword in todo.title.lower() or keyword in todo.description.lower():
                results.append(todo)
        return results
    
    def clear(self):
        """清空所有待办事项"""
        self.todos = []
        self._save()


# ============================================================
# 统计与分析功能
# ============================================================
class TodoAnalyzer:
    """待办事项统计分析"""
    
    @staticmethod
    def get_statistics(todos):
        """获取统计信息"""
        total = len(todos)
        completed = sum(1 for t in todos if t.completed)
        pending = total - completed
        
        # 优先级分布
        priority_dist = {"high": 0, "medium": 0, "low": 0}
        for t in todos:
            if t.priority in priority_dist:
                priority_dist[t.priority] += 1
        
        # 逾期统计
        overdue = 0
        today = datetime.now().date()
        for t in todos:
            if t.due_date and not t.completed:
                try:
                    due = datetime.fromisoformat(t.due_date).date()
                    if due < today:
                        overdue += 1
                except (ValueError, TypeError):
                    pass
        
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "priority_distribution": priority_dist,
            "overdue": overdue
        }
    
    @staticmethod
    def get_upcoming(todos, days=7):
        """获取未来指定天数内到期的待办"""
        today = datetime.now().date()
        deadline = today + timedelta(days=days)
        upcoming = []
        
        for t in todos:
            if t.due_date and not t.completed:
                try:
                    due = datetime.fromisoformat(t.due_date).date()
                    if today <= due <= deadline:
                        upcoming.append(t)
                except (ValueError, TypeError):
                    continue
        
        # 按到期日排序
        upcoming.sort(key=lambda x: x.due_date or "")
        return upcoming


# ============================================================
# 格式化输出
# ============================================================
def format_todo(todo, verbose=False):
    """格式化单个待办事项"""
    status = "[✓]" if todo.completed else "[ ]"
    priority_mark = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(todo.priority, "⚪")
    
    line = f"{status} #{todo.id} {priority_mark} {todo.title}"
    
    if verbose:
        if todo.description:
            line += f"\n    描述: {todo.description}"
        line += f"\n    优先级: {todo.priority}"
        if todo.due_date:
            line += f"\n    到期: {todo.due_date}"
        line += f"\n    创建: {todo.created_at}"
    
    return line


def format_statistics(stats):
    """格式化统计信息"""
    lines = [
        "📊 待办事项统计",
        "=" * 40,
        f"总事项: {stats['total']}",
        f"已完成: {stats['completed']}",
        f"待处理: {stats['pending']}",
        f"完成率: {stats['completion_rate']:.1f}%",
        f"已逾期: {stats['overdue']}",
        "",
        "优先级分布:",
        f"  高: {stats['priority_distribution']['high']}",
        f"  中: {stats['priority_distribution']['medium']}",
        f"  低: {stats['priority_distribution']['low']}"
    ]
    return "\n".join(lines)


# ============================================================
# 命令行接口
# ============================================================
def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="✅ Command-line tool to manage Todo lists",
        epilog="示例: todo-cli add '完成报告' -p high -d 2026-12-31"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # add 命令
    add_parser = subparsers.add_parser("add", help="添加待办事项")
    add_parser.add_argument("title", help="待办事项标题")
    add_parser.add_argument("-d", "--description", default="", help="详细描述")
    add_parser.add_argument("-p", "--priority", choices=["low", "medium", "high"], 
                           default="medium", help="优先级")
    add_parser.add_argument("--due", help="到期日期 (YYYY-MM-DD)")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出待办事项")
    list_parser.add_argument("-a", "--all", action="store_true", help="显示所有（含已完成）")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    
    # done 命令
    done_parser = subparsers.add_parser("done", help="标记完成")
    done_parser.add_argument("todo_id", type=int, help="待办事项 ID")
    
    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除待办事项")
    delete_parser.add_argument("todo_id", type=int, help="待办事项 ID")
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索待办事项")
    search_parser.add_argument("keyword", help="搜索关键词")
    
    # stats 命令
    subparsers.add_parser("stats", help="显示统计信息")
    
    # upcoming 命令
    upcoming_parser = subparsers.add_parser("upcoming", help="显示未来到期待办")
    upcoming_parser.add_argument("-d", "--days", type=int, default=7, help="未来天数")
    
    # clear 命令
    subparsers.add_parser("clear", help="清空所有待办事项")
    
    # selftest 参数（放在主解析器）
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    return parser


def run_selftest():
    """内置自检逻辑（不依赖外部文件）"""
    print("🔍 开始自检...")
    results = []
    
    try:
        # 使用临时目录隔离测试数据
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TodoStorage(tmpdir)
            
            # 测试添加功能
            todo1 = storage.add("测试任务一", "这是测试描述", "high", "2026-12-31")
            todo2 = storage.add("测试任务二", "", "low")
            
            # 断言：添加后总数合理
            all_todos = storage.list_all()
            assert len(all_todos) >= 2, "添加后至少应有2个事项"
            results.append("添加功能 ✅")
            
            # 断言：ID 递增
            assert todo2.id > todo1.id, "第二个任务 ID 应大于第一个"
            results.append("ID 生成 ✅")
            
            # 测试完成功能
            storage.complete(todo1.id)
            completed_todo = storage.get_by_id(todo1.id)
            assert completed_todo.completed is True, "任务应标记为完成"
            results.append("完成功能 ✅")
            
            # 测试过滤功能
            pending_todos = storage.list_all(show_completed=False)
            assert len(pending_todos) >= 1, "至少应有1个未完成任务"
            results.append("过滤功能 ✅")
            
            # 测试搜索功能
            search_results = storage.search("测试")
            assert len(search_results) >= 2, "应能搜索到至少2个任务"
            results.append("搜索功能 ✅")
            
            # 测试统计功能
            stats = TodoAnalyzer.get_statistics(all_todos)
            assert stats["total"] >= 2, "统计总数应不少于2"
            assert stats["completed"] >= 1, "完成数应不少于1"
            assert stats["pending"] >= 1, "待办数应不少于1"
            assert stats["completion_rate"] > 0, "完成率应大于0"
            results.append("统计分析 ✅")
            
            # 测试删除功能
            storage.delete(todo2.id)
            after_delete = storage.list_all()
            assert len(after_delete) < len(all_todos), "删除后数量应减少"
            results.append("删除功能 ✅")
            
            # 测试持久化（重新加载）
            storage2 = TodoStorage(tmpdir)
            reloaded = storage2.list_all()
            assert len(reloaded) >= 1, "重新加载后应保留数据"
            results.append("持久化 ✅")
            
            # 测试清空功能
            storage.clear()
            cleared = storage.list_all()
            assert len(cleared) == 0, "清空后应为空"
            results.append("清空功能 ✅")
            
            # 测试 upcoming
            future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
            storage.add("近期任务", due_date=future_date)
            upcoming = TodoAnalyzer.get_upcoming(storage.list_all(), days=7)
            assert len(upcoming) >= 1, "应有近期任务"
            results.append("近期任务查询 ✅")
            
            # 测试边界：空输入
            try:
                storage.add("   ")
                assert False, "空标题应抛出异常"
            except ValueError:
                results.append("空输入校验 ✅")
            
            # 测试边界：无效 ID
            try:
                storage.complete(999)
                assert False, "无效 ID 应抛出异常"
            except ValueError:
                results.append("无效 ID 校验 ✅")
            
            # 测试格式化输出
            formatted = format_todo(todo1, verbose=True)
            assert len(formatted) > 0, "格式化输出不应为空"
            results.append("格式化输出 ✅")
            
            # 测试统计格式化
            stats_text = format_statistics(stats)
            assert "待办事项统计" in stats_text, "统计文本应包含标题"
            results.append("统计格式化 ✅")
            
            # 测试错误码定义
            assert len(ErrorCode.E001) > 0, "错误码不应为空"
            assert "E001" in ErrorCode.E001, "错误码应包含编号"
            results.append("错误码体系 ✅")
    
    except AssertionError as e:
        print(f"❌ 自检失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 自检异常: {e}")
        return False
    
    print("\n".join(results))
    print(f"\n✅ 全部 {len(results)} 项自检通过！")
    return True


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 无命令时显示帮助
    if not args.command:
        parser.print_help()
        return
    
    try:
        storage = TodoStorage()
        
        if args.command == "add":
            todo = storage.add(args.title, args.description, args.priority, args.due)
            print(f"✅ 已添加: {format_todo(todo)}")
            
        elif args.command == "list":
            todos = storage.list_all(show_completed=args.all)
            if not todos:
                print("📝 暂无待办事项")
            else:
                for todo in todos:
                    print(format_todo(todo, args.verbose))
                print(f"\n共 {len(todos)} 项")
                
        elif args.command == "done":
            todo = storage.complete(args.todo_id)
            print(f"✅ 已完成: {todo.title}")
            
        elif args.command == "delete":
            todo = storage.delete(args.todo_id)
            print(f"🗑️ 已删除: {todo.title}")
            
        elif args.command == "search":
            results = storage.search(args.keyword)
            if not results:
                print(f"🔍 未找到包含 '{args.keyword}' 的待办事项")
            else:
                print(f"🔍 找到 {len(results)} 个匹配项:")
                for todo in results:
                    print(format_todo(todo))
                    
        elif args.command == "stats":
            todos = storage.list_all()
            if not todos:
                print("📝 暂无待办事项，无法生成统计")
            else:
                stats = TodoAnalyzer.get_statistics(todos)
                print(format_statistics(stats))
                
        elif args.command == "upcoming":
            todos = storage.list_all(show_completed=False)
            upcoming = TodoAnalyzer.get_upcoming(todos, args.days)
            if not upcoming:
                print(f"🗓️ 未来 {args.days} 天内无到期事项")
            else:
                print(f"🗓️ 未来 {args.days} 天内到期事项:")
                for todo in upcoming:
                    print(format_todo(todo))
                    
        elif args.command == "clear":
            confirm = input("⚠️ 确定要清空所有待办事项吗？(y/N): ")
            if confirm.lower() in ("y", "yes"):
                storage.clear()
                print("🗑️ 已清空所有待办事项")
            else:
                print("已取消")
    
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ {ErrorCode.E010}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
