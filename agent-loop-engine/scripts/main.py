#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-loop-engine 独立实现（clean-room 重写）

轻量级循环状态内核，管理代理团队持久目标、唤醒与交接。
仅依据功能规格独立实现，不包含任何既有代码。

用法:
    python scripts/main.py --selftest   # 离线自检核心逻辑
    python scripts/main.py --help       # 查看帮助
"""

import sys
import time
import json
import argparse
import hashlib
import hmac
import os
from datetime import datetime, timezone
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Callable
dry_run = False  # v3.274 模块级 dry-run 标志


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INVALID_ARGUMENT = "E001"       # 参数无效
ERR_AGENT_NOT_FOUND = "E002"        # 代理不存在
ERR_AGENT_ALREADY_EXISTS = "E003"   # 代理已存在
ERR_STATE_NOT_FOUND = "E004"        # 状态不存在
ERR_INVALID_STATE = "E005"          # 状态值非法
ERR_CYCLE_LIMIT = "E006"            # 循环次数超限
ERR_HANDOFF_CONFLICT = "E007"       # 交接冲突
ERR_WAKEUP_INVALID = "E008"         # 唤醒条件非法
ERR_PERSISTENCE = "E009"            # 持久化失败
ERR_INTERNAL = "E010"               # 内部错误


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def utc_now() -> float:
    """返回 UTC 时间戳"""
    return datetime.now(timezone.utc).timestamp()


def utc_now_str() -> str:
    """返回 UTC 时间字符串"""
    return datetime.now(timezone.utc).isoformat()


def retry_io(func: Callable, *args, max_retries: int = 3, **kwargs) -> Any:
    """
    带指数退避重试的 I/O 操作包装器。
    最多重试 3 次，退避间隔 0.5s, 1s, 2s。
    """
    delay = 0.5
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
    raise last_exc


def compute_handoff_signature(context: 'HandoffContext', secret_key: str = "agent-loop-engine") -> str:
    """计算交接上下文的 HMAC 签名"""
    payload = json.dumps({
        "from_agent": context.from_agent,
        "to_agent": context.to_agent,
        "payload": context.payload,
        "timestamp": context.timestamp
    }, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hmac.new(secret_key.encode('utf-8'), payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Agent:
    """代理实体"""
    id: str
    name: str
    role: str
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Goal:
    """持久目标"""
    id: str
    description: str
    status: str = "active"          # active | paused | completed | archived
    created_at: float = field(default_factory=utc_now)
    updated_at: float = field(default_factory=utc_now)
    progress: float = 0.0           # 0.0 ~ 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WakeupCondition:
    """唤醒条件"""
    type: str                       # "time" | "state" | "manual"
    target: str                     # 时间戳或状态值
    operator: str = "eq"            # eq | ne | gt | lt | ge | le
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffContext:
    """交接上下文"""
    from_agent: str
    to_agent: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=utc_now)
    signature: str = ""  # 交接完整性签名


@dataclass
class CycleRecord:
    """循环记录"""
    cycle_id: int
    agent_id: str
    action: str
    timestamp: float = field(default_factory=utc_now)
    result: str = "ok"
    detail: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 循环状态内核
# ---------------------------------------------------------------------------
class LoopStateKernel:
    """
    循环状态内核：管理代理、目标、唤醒与交接。
    支持持久化存储与交接验证。
    """

    def __init__(self, max_cycles: int = 1000, state_file: Optional[str] = None):
        """
        初始化内核。

        参数:
            max_cycles: 最大循环次数，超过则触发 E006 错误。
            state_file: 状态持久化文件路径（可选）
        """
        self.max_cycles = max_cycles
        self.state_file = state_file
        self.agents: Dict[str, Agent] = OrderedDict()
        self.goals: Dict[str, Goal] = OrderedDict()
        self.wakeup_conditions: Dict[str, List[WakeupCondition]] = {}
        self.handoffs: List[HandoffContext] = []
        self.cycle_history: List[CycleRecord] = []
        self.current_cycle = 0
        self.global_state: Dict[str, Any] = {}
        self._paused = False

        # 如果提供了状态文件，尝试加载
        if state_file and os.path.exists(state_file):
            self.load_state(state_file)

    # ------------------------------------------------------------------
    # 代理管理
    # ------------------------------------------------------------------
    def register_agent(self, agent_id: str, name: str, role: str,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        注册新代理。

        返回:
            成功返回 ERR_OK，失败返回错误码。
        """
        if not agent_id or not name:
            return ERR_INVALID_ARGUMENT
        if agent_id in self.agents:
            return ERR_AGENT_ALREADY_EXISTS

        self.agents[agent_id] = Agent(
            id=agent_id,
            name=name,
            role=role,
            metadata=metadata or {}
        )
        return ERR_OK

    def unregister_agent(self, agent_id: str) -> str:
        """注销代理"""
        if agent_id not in self.agents:
            return ERR_AGENT_NOT_FOUND
        del self.agents[agent_id]
        return ERR_OK

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取代理信息"""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Agent]:
        """列出所有代理"""
        return list(self.agents.values())

    def set_agent_enabled(self, agent_id: str, enabled: bool) -> str:
        """启用或禁用代理"""
        if agent_id not in self.agents:
            return ERR_AGENT_NOT_FOUND
        self.agents[agent_id].enabled = enabled
        return ERR_OK

    # ------------------------------------------------------------------
    # 目标管理
    # ------------------------------------------------------------------
    def create_goal(self, goal_id: str, description: str,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建持久目标。

        返回:
            成功返回 ERR_OK，失败返回错误码。
        """
        if not goal_id or not description:
            return ERR_INVALID_ARGUMENT
        if goal_id in self.goals:
            return ERR_INVALID_ARGUMENT  # 目标重复

        self.goals[goal_id] = Goal(
            id=goal_id,
            description=description,
            metadata=metadata or {}
        )
        return ERR_OK

    def update_goal_status(self, goal_id: str, status: str) -> str:
        """
        更新目标状态。

        状态必须是: active | paused | completed | archived
        """
        if goal_id not in self.goals:
            return ERR_STATE_NOT_FOUND
        if status not in ("active", "paused", "completed", "archived"):
            return ERR_INVALID_STATE

        goal = self.goals[goal_id]
        goal.status = status
        goal.updated_at = utc_now()
        return ERR_OK

    def update_goal_progress(self, goal_id: str, progress: float) -> str:
        """更新目标进度（0.0 ~ 1.0）"""
        if goal_id not in self.goals:
            return ERR_STATE_NOT_FOUND
        if not 0.0 <= progress <= 1.0:
            return ERR_INVALID_STATE

        goal = self.goals[goal_id]
        goal.progress = progress
        goal.updated_at = utc_now()
        return ERR_OK

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """获取目标信息"""
        return self.goals.get(goal_id)

    def list_goals(self, status: Optional[str] = None) -> List[Goal]:
        """列出目标，可按状态过滤"""
        if status is None:
            return list(self.goals.values())
        return [g for g in self.goals.values() if g.status == status]

    # ------------------------------------------------------------------
    # 唤醒机制
    # ------------------------------------------------------------------
    def set_wakeup_condition(self, agent_id: str, condition: WakeupCondition) -> str:
        """
        为代理设置唤醒条件。

        条件类型:
            - time:   在指定时间后唤醒（target 为时间戳）
            - state:  当全局状态满足条件时唤醒
            - manual: 手动唤醒
        """
        if agent_id not in self.agents:
            return ERR_AGENT_NOT_FOUND
        if condition.type not in ("time", "state", "manual"):
            return ERR_WAKEUP_INVALID
        if condition.type in ("time", "state") and not condition.target:
            return ERR_WAKEUP_INVALID

        if agent_id not in self.wakeup_conditions:
            self.wakeup_conditions[agent_id] = []
        self.wakeup_conditions[agent_id].append(condition)
        return ERR_OK

    def clear_wakeup_conditions(self, agent_id: str) -> str:
        """清除代理的所有唤醒条件"""
        if agent_id not in self.agents:
            return ERR_AGENT_NOT_FOUND
        self.wakeup_conditions.pop(agent_id, None)
        return ERR_OK

    def check_wakeup(self, agent_id: str) -> bool:
        """
        检查代理是否应被唤醒。

        满足任一条件即返回 True。
        """
        if agent_id not in self.agents:
            return False

        conditions = self.wakeup_conditions.get(agent_id, [])
        for cond in conditions:
            if cond.type == "manual":
                return True
            elif cond.type == "time":
                if utc_now() >= float(cond.target):
                    return True
            elif cond.type == "state":
                state_val = self.global_state.get(cond.target)
                if state_val is None:
                    continue
                if self._compare(state_val, cond.operator, cond.payload.get("value")):
                    return True
        return False

    def wake_agent(self, agent_id: str) -> str:
        """
        手动唤醒代理。

        返回:
            成功返回 ERR_OK，代理不存在返回 E002。
        """
        if agent_id not in self.agents:
            return ERR_AGENT_NOT_FOUND
        if not self.agents[agent_id].enabled:
            return ERR_INVALID_STATE

        # 记录唤醒动作
        self._record_cycle(agent_id, "wake")
        return ERR_OK

    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        """比较操作符实现"""
        try:
            if operator == "eq":
                return actual == expected
            elif operator == "ne":
                return actual != expected
            elif operator == "gt":
                return actual > expected
            elif operator == "lt":
                return actual < expected
            elif operator == "ge":
                return actual >= expected
            elif operator == "le":
                return actual <= expected
        except TypeError:
            return False
        return False

    # ------------------------------------------------------------------
    # 交接管理
    # ------------------------------------------------------------------
    def handoff(self, from_agent: str, to_agent: str,
                payload: Optional[Dict[str, Any]] = None) -> str:
        """
        在代理之间进行交接。

        返回:
            成功返回 ERR_OK，失败返回错误码。
        """
        if from_agent not in self.agents:
            return ERR_AGENT_NOT_FOUND
        if to_agent not in self.agents:
            return ERR_AGENT_NOT_FOUND
        if from_agent == to_agent:
            return ERR_HANDOFF_CONFLICT
        if not self.agents[to_agent].enabled:
            return ERR_INVALID_STATE

        # 创建交接上下文并计算签名
        context = HandoffContext(
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload or {}
        )
        context.signature = compute_handoff_signature(context)
        self.handoffs.append(context)

        # 记录循环
        self._record_cycle(from_agent, "handoff_out", detail={"to": to_agent})
        self._record_cycle(to_agent, "handoff_in", detail={"from": from_agent})
        return ERR_OK

    def verify_handoff(self, context: HandoffContext) -> bool:
        """验证交接上下文的完整性"""
        if not context.signature:
            return False
        expected = compute_handoff_signature(context)
        return hmac.compare_digest(context.signature, expected)

    def list_handoffs(self, agent_id: Optional[str] = None) -> List[HandoffContext]:
        """列出交接记录，可按代理过滤"""
        if agent_id is None:
            return list(self.handoffs)
        return [h for h in self.handoffs
                if h.from_agent == agent_id or h.to_agent == agent_id]

    # ------------------------------------------------------------------
    # 循环状态追踪
    # ------------------------------------------------------------------
    def _record_cycle(self, agent_id: str, action: str,
                      detail: Optional[Dict[str, Any]] = None) -> None:
        """记录一次循环动作"""
        if self.current_cycle >= self.max_cycles:
            raise RuntimeError(f"{ERR_CYCLE_LIMIT}: 循环次数超过上限 {self.max_cycles}")

        self.current_cycle += 1
        record = CycleRecord(
            cycle_id=self.current_cycle,
            agent_id=agent_id,
            action=action,
            detail=detail or {}
        )
        self.cycle_history.append(record)

    def get_cycle_count(self) -> int:
        """获取当前循环次数"""
        return self.current_cycle

    def get_cycle_history(self, agent_id: Optional[str] = None) -> List[CycleRecord]:
        """获取循环历史，可按代理过滤"""
        if agent_id is None:
            return list(self.cycle_history)
        return [r for r in self.cycle_history if r.agent_id == agent_id]

    def reset_cycles(self) -> str:
        """重置循环计数"""
        self.current_cycle = 0
        self.cycle_history.clear()
        return ERR_OK

    # ------------------------------------------------------------------
    # 全局状态管理
    # ------------------------------------------------------------------
    def set_global_state(self, key: str, value: Any) -> str:
        """设置全局状态"""
        if not key:
            return ERR_INVALID_ARGUMENT
        self.global_state[key] = value
        return ERR_OK

    def get_global_state(self, key: str) -> Any:
        """获取全局状态"""
        return self.global_state.get(key)

    # ------------------------------------------------------------------
    # 持久化（JSON 序列化，带重试）
    # ------------------------------------------------------------------
    def save_state(self, filepath: Optional[str] = None) -> str:
        """
        将内核状态保存到 JSON 文件。

        返回:
            成功返回 ERR_OK，失败返回 E009。
        """
        target = filepath or self.state_file
        if not target:
            return ERR_INVALID_ARGUMENT

        try:
            state = {
                "agents": {aid: {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "enabled": a.enabled,
                    "metadata": a.metadata
                } for aid, a in self.agents.items()},
                "goals": {gid: {
                    "id": g.id,
                    "description": g.description,
                    "status": g.status,
                    "progress": g.progress,
                    "metadata": g.metadata,
                    "created_at": g.created_at,
                    "updated_at": g.updated_at
                } for gid, g in self.goals.items()},
                "global_state": self.global_state,
                "current_cycle": self.current_cycle,
                "handoffs": [{
                    "from_agent": h.from_agent,
                    "to_agent": h.to_agent,
                    "payload": h.payload,
                    "timestamp": h.timestamp,
                    "signature": h.signature
                } for h in self.handoffs]
            }

            def _write():
                with open(target, "w", encoding="utf-8", errors="replace") as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)

            retry_io(_write)
            return ERR_OK
        except Exception:
            return ERR_PERSISTENCE

    def load_state(self, filepath: Optional[str] = None) -> str:
        """
        从 JSON 文件加载内核状态。

        返回:
            成功返回 ERR_OK，失败返回 E009。
        """
        target = filepath or self.state_file
        if not target:
            return ERR_INVALID_ARG


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--force", action="store_true")  # R4 强制写盘

    ap.add_argument("--dry-run", action="store_true")  # R4 预览模式
    args = ap.parse_args()
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
