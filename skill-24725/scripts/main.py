#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import argparse
from datetime import datetime, timedelta

class TaskManager:
    """任务管理器，支持添加、删除、完成任务和查看任务"""
    
    def __init__(self):
        self.tasks = []
        self.next_id = 1
    
    def add_task(self, title, priority='medium', due_date=None):
        """添加新任务"""
        task = {
            'id': self.next_id,
            'title': title,
            'priority': priority,
            'due_date': due_date,
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        self.tasks.append(task)
        self.next_id += 1
        return task['id']
    
    def delete_task(self, task_id):
        """删除任务"""
        for i, task in enumerate(self.tasks):
            if task['id'] == task_id:
                return self.tasks.pop(i)
        return None
    
    def complete_task(self, task_id):
        """完成任务"""
        task = self.get_task(task_id)
        if task:
            task['completed'] = True
            return True
        return False
    
    def get_task(self, task_id):
        """获取任务"""
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None
    
    def list_tasks(self, include_completed=True):
        """列出任务"""
        if include_completed:
            return self.tasks
        return [t for t in self.tasks if not t['completed']]
    
    def get_stats(self):
        """获取任务统计信息"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t['completed'])
        pending = total - completed
        return {
            'total': total,
            'completed': completed,
            'pending': pending
        }
    
    def to_json(self):
        """转换为JSON格式"""
        return json.dumps({
            'tasks': self.tasks,
            'next_id': self.next_id
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str):
        """从JSON加载"""
        data = json.loads(json_str)
        manager = cls()
        manager.tasks = data['tasks']
        manager.next_id = data['next_id']
        return manager

def selftest():
    """自测函数"""
    print("Running selftest...")
    
    # 创建任务管理器
    manager = TaskManager()
    
    # 测试添加任务
    id1 = manager.add_task("测试任务1", "high")
    id2 = manager.add_task("测试任务2", "medium", "2024-12-31")
    id3 = manager.add_task("测试任务3", "low")
    
    # 验证任务数量
    stats = manager.get_stats()
    assert stats['total'] >= 3, f"Expected at least 3 tasks, got {stats['total']}"
    assert stats['pending'] >= 3, f"Expected at least 3 pending tasks, got {stats['pending']}"
    
    # 测试获取任务
    task1 = manager.get_task(id1)
    assert task1 is not None, "Task 1 should exist"
    assert task1['title'] == "测试任务1", f"Unexpected title: {task1['title']}"
    assert task1['priority'] == "high", f"Unexpected priority: {task1['priority']}"
    
    # 测试完成任务
    assert manager.complete_task(id1) == True, "Should complete task successfully"
    task1 = manager.get_task(id1)
    assert task1['completed'] == True, "Task 1 should be completed"
    
    # 测试统计
    stats = manager.get_stats()
    assert stats['completed'] >= 1, f"Expected at least 1 completed task, got {stats['completed']}"
    assert stats['pending'] >= 2, f"Expected at least 2 pending tasks, got {stats['pending']}"
    
    # 测试删除任务
    deleted = manager.delete_task(id2)
    assert deleted is not None, "Should delete task successfully"
    assert manager.get_task(id2) is None, "Task 2 should not exist after deletion"
    
    # 测试列表功能
    all_tasks = manager.list_tasks()
    assert len(all_tasks) >= 2, f"Expected at least 2 tasks, got {len(all_tasks)}"
    
    pending_tasks = manager.list_tasks(include_completed=False)
    assert len(pending_tasks) >= 1, f"Expected at least 1 pending task, got {len(pending_tasks)}"
    
    # 测试JSON序列化
    json_str = manager.to_json()
    assert json_str is not None, "JSON serialization should work"
    
    # 测试JSON反序列化
    manager2 = TaskManager.from_json(json_str)
    assert manager2 is not None, "JSON deserialization should work"
    assert len(manager2.tasks) == len(manager.tasks), "Task count should match after deserialization"
    
    # 测试边界情况
    assert manager.complete_task(999) == False, "Should return False for non-existent task"
    assert manager.delete_task(999) is None, "Should return None for non-existent task"
    assert manager.get_task(999) is None, "Should return None for non-existent task"
    
    print("All selftest assertions passed!")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="任务管理器")
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    parser.add_argument('--add', nargs='+', help='添加任务: --add "任务标题" [优先级] [截止日期]')
    parser.add_argument('--list', action='store_true', help='列出所有任务')
    parser.add_argument('--complete', type=int, help='完成任务: --complete 任务ID')
    parser.add_argument('--delete', type=int, help='删除任务: --delete 任务ID')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    if args.selftest:
        selftest()
        return 0
    
    manager = TaskManager()
    
    if args.add:
        title = args.add[0]
        priority = args.add[1] if len(args.add) > 1 else 'medium'
        due_date = args.add[2] if len(args.add) > 2 else None
        task_id = manager.add_task(title, priority, due_date)
        print(f"任务已添加，ID: {task_id}")
    
    if args.list:
        tasks = manager.list_tasks()
        if not tasks:
            print("暂无任务")
        else:
            for task in tasks:
                status = "✓" if task['completed'] else "✗"
                print(f"[{status}] ID: {task['id']}, 标题: {task['title']}, "
                      f"优先级: {task['priority']}, 截止日期: {task['due_date'] or '无'}")
    
    if args.complete is not None:
        if manager.complete_task(args.complete):
            print(f"任务 {args.complete} 已完成")
        else:
            print(f"任务 {args.complete} 不存在")
    
    if args.delete is not None:
        task = manager.delete_task(args.delete)
        if task:
            print(f"任务 {args.delete} 已删除")
        else:
            print(f"任务 {args.delete} 不存在")
    
    if args.stats:
        stats = manager.get_stats()
        print(f"总任务数: {stats['total']}")
        print(f"已完成: {stats['completed']}")
        print(f"待完成: {stats['pending']}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
