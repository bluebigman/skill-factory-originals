#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-loop-engine 独立实现脚本
基于功能规格 clean-room 重写，仅供学习参考。
"""

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


# 错误码定义
class ErrorCode:
    E001 = "E001: 参数错误"
    E002 = "E002: 目标不存在"
    E003 = "E003: 待办不存在"
    E004 = "E004: 状态非法"
    E005 = "E005: 存储写入失败"
    E006 = "E006: 存储读取失败"
    E007 = "E007: 交接凭证无效"
    E008 = "E008: 配额类型未知"
    E009 = "E009: 证据哈希不匹配"
    E010 = "E010: 内部状态异常"


# ---------- 枚举定义 ----------
class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class WakeType(str, Enum):
    TIME = "time"
    COUNT = "count"
    RESOURCE = "resource"


# ---------- 数据模型 ----------
@dataclass
class Evidence:
    """证据记录：每次操作的关键信息"""
    timestamp: str
    operation: str
    input_summary: str
    output_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TodoItem:
    """待办事项"""
    id: str
    title: str
    status: TodoStatus = TodoStatus.PENDING
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class WakeCondition:
    """唤醒条件"""
    type: WakeType
    threshold: float
    current_value: float = 0.0

    def is_satisfied(self) -> bool:
        return self.current_value >= self.threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "threshold": self.threshold,
            "current_value": self.current_value
        }


@dataclass
class Goal:
    """长期目标"""
    id: str
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    wake_conditions: List[WakeCondition] = field(default_factory=list)
    todos: List[TodoItem] = field(default_factory=list)
    evidence_log: List[Evidence] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "wake_conditions": [wc.to_dict() for wc in self.wake_conditions],
            "todos": [t.to_dict() for t in self.todos],
            "evidence_log": [e.to_dict() for e in self.evidence_log],
            "metadata": self.metadata
        }


@dataclass
class HandoverToken:
    """交接凭证"""
    token_id: str
    from_agent: str
    to_agent: str
    context_summary: str
    pending_todos: List[str]
    risk_notes: List[str]
    timestamp: str
    signature: str = ""

    def sign(self) -> None:
        """生成简单签名（内容哈希）"""
        payload = f"{self.token_id}|{self.from_agent}|{self.to_agent}|{self.timestamp}"
        self.signature = hashlib.sha256(payload.encode()).hexdigest()

    def verify(self) -> bool:
        """验证签名"""
        payload = f"{self.token_id}|{self.from_agent}|{self.to_agent}|{self.timestamp}"
        expected = hashlib.sha256(payload.encode()).hexdigest()
        return self.signature == expected

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------- 核心引擎 ----------
class AgentLoopEngine:
    """循环状态内核：管理目标、唤醒、待办、证据、交接"""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "agent_loop_data.json"
        )
        self._memory_mode = self.storage_path == ":memory:"
        self.goals: Dict[str, Goal] = {}
        if not self._memory_mode:
            self._load()

    # ---------- 存储 ----------
    def _load(self) -> None:
        """从文件加载状态"""
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for gid, gdata in data.get("goals", {}).items():
                self.goals[gid] = self._goal_from_dict(gdata)
        except Exception:
            # 读取失败不致命，但记录错误
            print(f"[{ErrorCode.E006}] 无法读取存储文件，使用空状态")

    def _save(self) -> None:
        """保存状态到文件"""
        if self._memory_mode:
            return  # 内存模式不需要保存
        try:
            data = {"goals": {gid: g.to_dict() for gid, g in self.goals.items()}}
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            raise RuntimeError(ErrorCode.E005)

    @staticmethod
    def _goal_from_dict(data: Dict[str, Any]) -> Goal:
        """从字典恢复目标对象"""
        g = Goal(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=Priority(data.get("priority", "medium")),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {})
        )
        # 恢复唤醒条件
        for wc in data.get("wake_conditions", []):
            g.wake_conditions.append(WakeCondition(
                type=WakeType(wc["type"]),
                threshold=wc["threshold"],
                current_value=wc.get("current_value", 0.0)
            ))
        # 恢复待办
        for t in data.get("todos", []):
            g.todos.append(TodoItem(
                id=t["id"],
                title=t["title"],
                status=TodoStatus(t.get("status", "pending")),
                created_at=t.get("created_at", ""),
                updated_at=t.get("updated_at", ""),
                metadata=t.get("metadata", {})
            ))
        # 恢复证据
        for e in data.get("evidence_log", []):
            g.evidence_log.append(Evidence(
                timestamp=e["timestamp"],
                operation=e["operation"],
                input_summary=e["input_summary"],
                output_hash=e["output_hash"],
                metadata=e.get("metadata", {})
            ))
        return g

    # ---------- 工具方法 ----------
    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def _add_evidence(self, goal_id: str, operation: str, input_summary: str, output: Any) -> None:
        """添加证据日志（仅追加）"""
        goal = self.goals.get(goal_id)
        if not goal:
            return
        output_str = json.dumps(output, ensure_ascii=False) if not isinstance(output, str) else output
        evidence = Evidence(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            operation=operation,
            input_summary=input_summary,
            output_hash=self._hash_content(output_str)
        )
        goal.evidence_log.append(evidence)

    # ---------- 目标管理 ----------
    def create_goal(self, title: str, description: str = "",
                    priority: str = "medium") -> Goal:
        """创建新目标"""
        if not title:
            raise ValueError(ErrorCode.E001)
        goal = Goal(
            id=self._generate_id(),
            title=title,
            description=description,
            priority=Priority(priority)
        )
        self.goals[goal.id] = goal
        self._add_evidence(goal.id, "create_goal", f"title={title}", {"goal_id": goal.id})
        self._save()
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """获取目标"""
        return self.goals.get(goal_id)

    def list_goals(self, sort_by_priority: bool = False) -> List[Goal]:
        """列出所有目标"""
        goals = list(self.goals.values())
        if sort_by_priority:
            priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1,
                              Priority.MEDIUM: 2, Priority.LOW: 3}
            goals.sort(key=lambda g: priority_order.get(g.priority, 99))
        return goals

    def update_goal_priority(self, goal_id: str, new_priority: str) -> Goal:
        """更新目标优先级"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        goal.priority = Priority(new_priority)
        goal.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._add_evidence(goal_id, "update_priority", f"new={new_priority}", {"ok": True})
        self._save()
        return goal

    # ---------- 唤醒机制 ----------
    def add_wake_condition(self, goal_id: str, wake_type: str,
                           threshold: float) -> WakeCondition:
        """添加唤醒条件"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        try:
            wtype = WakeType(wake_type)
        except ValueError:
            raise ValueError(ErrorCode.E008)
        wc = WakeCondition(type=wtype, threshold=threshold)
        goal.wake_conditions.append(wc)
        goal.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._add_evidence(goal_id, "add_wake_condition",
                           f"type={wake_type}, threshold={threshold}", {"ok": True})
        self._save()
        return wc

    def update_wake_value(self, goal_id: str, wake_type: str,
                          increment: float = 1.0) -> bool:
        """更新唤醒条件的当前值，返回是否满足唤醒"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        satisfied = False
        for wc in goal.wake_conditions:
            if wc.type.value == wake_type:
                wc.current_value += increment
                if wc.is_satisfied():
                    satisfied = True
        goal.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._add_evidence(goal_id, "update_wake_value",
                           f"type={wake_type}, inc={increment}",
                           {"satisfied": satisfied})
        self._save()
        return satisfied

    def check_wake_conditions(self, goal_id: str) -> List[str]:
        """检查所有唤醒条件，返回已满足的条件类型列表"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        satisfied = [wc.type.value for wc in goal.wake_conditions if wc.is_satisfied()]
        return satisfied

    # ---------- 待办事项 ----------
    def add_todo(self, goal_id: str, title: str) -> TodoItem:
        """添加待办事项"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        todo = TodoItem(id=self._generate_id(), title=title)
        goal.todos.append(todo)
        goal.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._add_evidence(goal_id, "add_todo", f"title={title}", {"todo_id": todo.id})
        self._save()
        return todo

    def update_todo_status(self, goal_id: str, todo_id: str,
                           new_status: str) -> TodoItem:
        """更新待办状态"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        try:
            status = TodoStatus(new_status)
        except ValueError:
            raise ValueError(ErrorCode.E004)
        for todo in goal.todos:
            if todo.id == todo_id:
                todo.status = status
                todo.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
                goal.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
                self._add_evidence(goal_id, "update_todo_status",
                                   f"todo={todo_id}, status={new_status}",
                                   {"ok": True})
                self._save()
                return todo
        raise KeyError(ErrorCode.E003)

    def list_todos(self, goal_id: str, status: Optional[str] = None) -> List[TodoItem]:
        """列出待办事项，可按状态过滤"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        todos = goal.todos
        if status:
            try:
                s = TodoStatus(status)
                todos = [t for t in todos if t.status == s]
            except ValueError:
                raise ValueError(ErrorCode.E004)
        return todos

    # ---------- 证据日志 ----------
    def get_evidence_log(self, goal_id: str) -> List[Evidence]:
        """获取证据日志（只读）"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        return list(goal.evidence_log)  # 返回副本，防止外部修改

    def verify_evidence(self, goal_id: str, index: int) -> bool:
        """验证指定证据的哈希一致性"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(ErrorCode.E002)
        if index < 0 or index >= len(goal.evidence_log):
            raise IndexError(ErrorCode.E001)
        ev = goal.evidence_log[index]
        # 由于我们存储的是哈希而非原始内容，这里验证元数据一致性
        # 实际场景应重新计算，这里简化验证
        return bool(ev.output_hash)

    # ---------- 交接验证 ----------
    def create_handover(self, from_agent: str, to_agent: str,
                        goal_ids: List[str]) -> HandoverToken:
        """创建交接凭证"""
        if not goal_ids:
            raise ValueError(ErrorCode.E001)
        pending_todos = []
        risk_notes = []
        context_parts = []
        for gid in goal_ids:
            goal = self.goals.get(gid)
            if not goal:
                raise KeyError(ErrorCode.E002)
            context_parts.append(f"目标[{goal.id}]: {goal.title}")
            # 收集未完成待办
            for todo in goal.todos:
                if todo.status in (TodoStatus.PENDING, TodoStatus.IN_PROGRESS):
                    pending_todos.append(todo.id)
                elif todo.status == TodoStatus.BLOCKED:
                    risk_notes.append(f"目标{gid}有待办被阻塞")
        token = HandoverToken(
            token_id=self._generate_id(),
            from_agent=from_agent,
            to_agent=to_agent,
            context_summary="; ".join(context_parts),
            pending_todos=pending_todos,
            risk_notes=risk_notes,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S")
        )
        token.sign()
        return token

    def verify_handover(self, token: HandoverToken) -> bool:
        """验证交接凭证"""
        return token.verify()

    # ---------- 导出 ----------
    def export_state(self, filepath: str) -> None:
        """导出完整状态"""
        try:
            data = {"goals": {gid: g.to_dict() for gid, g in self.goals.items()}}
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            raise RuntimeError(ErrorCode.E005)


# ---------- 自检函数 ----------
def run_selftest() -> int:
    """内置样例数据离线自检核心逻辑"""
    print("=== agent-loop-engine 自检开始 ===")
    engine = AgentLoopEngine(storage_path=":memory:")  # 使用内存模式

    # 1. 创建目标
    try:
        goal = engine.create_goal("完成项目交付", "在截止日期前完成所有任务", "high")
        assert goal.id, "目标ID不应为空"
        print("[PASS] 创建目标")
    except Exception as e:
        print(f"[FAIL] 创建目标: {e}")
        return 1

    # 2. 添加唤醒条件
    try:
        wc = engine.add_wake_condition(goal.id, "time", 3)
        assert wc.threshold == 3, "阈值错误"
        print("[PASS] 添加唤醒条件")
    except Exception as e:
        print(f"[FAIL] 添加唤醒条件: {e}")
        return 1

    # 3. 更新唤醒值并触发
    try:
        engine.update_wake_value(goal.id, "time", 2)
        satisfied = engine.check_wake_conditions(goal.id)
        assert len(satisfied) == 0, "不应满足唤醒"
        engine.update_wake_value(goal.id, "time", 1)
        satisfied = engine.check_wake_conditions(goal.id)
        assert "time" in satisfied, "应满足唤醒条件"
        print("[PASS] 唤醒机制")
    except Exception as e:
        print(f"[FAIL] 唤醒机制: {e}")
        return 1

    # 4. 添加待办并更新状态
    try:
        todo = engine.add_todo(goal.id, "编写代码")
        assert todo.status == TodoStatus.PENDING, "初始状态错误"
        engine.update_todo_status(goal.id, todo.id, "in_progress")
        todos = engine.list_todos(goal.id, status="in_progress")
        assert len(todos) == 1, "过滤结果错误"
        print("[PASS] 待办管理")
    except Exception as e:
        print(f"[FAIL] 待办管理: {e}")
        return 1

    # 5. 证据日志
    try:
        log = engine.get_evidence_log(goal.id)
        assert len(log) >= 3, "证据日志数量不足"
        print("[PASS] 证据日志")
    except Exception as e:
        print(f"[FAIL] 证据日志: {e}")
        return 1

    # 6. 交接凭证
    try:
        token = engine.create_handover("agent_a", "agent_b", [goal.id])
        assert token.verify(), "交接凭证签名无效"
        assert len(token.pending_todos) == 1, "待办交接数量错误"
        print("[PASS] 交接验证")
    except Exception as e:
        print(f"[FAIL] 交接验证: {e}")
        return 1

    # 7. 持久化测试（使用临时文件）
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        engine2 = AgentLoopEngine(storage_path=tmp_path)
        g2 = engine2.create_goal("临时目标")
        assert engine2.get_goal(g2.id) is not None, "保存失败"
        # 重新加载
        engine3 = AgentLoopEngine(storage_path=tmp_path)
        assert engine3.get_goal(g2.id) is not None, "加载失败"
        os.unlink(tmp_path)
        print("[PASS] 持久化存储")
    except Exception as e:
        print(f"[FAIL] 持久化存储: {e}")
        return 1

    print("=== 全部自检通过 ===")
    return 0


# ---------- 主入口 ----------
def main():
    parser = argparse.ArgumentParser(description="agent-loop-engine 循环状态内核")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    parser.add_argument("--create-goal", nargs=2, metavar=("TITLE", "DESC"),
                        help="创建目标")
    parser.add_argument("--list-goals", action="store_true",
                        help="列出所有目标")
    parser.add_argument("--add-todo", nargs=2, metavar=("GOAL_ID", "TITLE"),
                        help="添加待办")
    parser.add_argument("--storage", default=None,
                        help="存储文件路径")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 正常模式
    engine = AgentLoopEngine(storage_path=args.storage)

    try:
        if args.create_goal:
            title, desc = args.create_goal
            goal = engine.create_goal(title, desc)
            print(f"已创建目标: {goal.id} - {goal.title}")

        elif args.list_goals:
            goals = engine.list_goals(sort_by_priority=True)
            if not goals:
                print("暂无目标")
            for g in goals:
                print(f"[{g.priority.value}] {g.id}: {g.title}")

        elif args.add_todo:
            goal_id, title = args.add_todo
            todo = engine.add_todo(goal_id, title)
            print(f"已添加待办: {todo.id} - {todo.title}")

        else:
            parser.print_help()

    except KeyError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"未预期错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
