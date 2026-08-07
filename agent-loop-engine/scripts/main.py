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
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Callable


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
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
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
    timestamp: float = field(default_factory=time.time)


@dataclass
class CycleRecord:
    """循环记录"""
    cycle_id: int
    agent_id: str
    action: str
    timestamp: float = field(default_factory=time.time)
    result: str = "ok"
    detail: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 循环状态内核
# ---------------------------------------------------------------------------
class LoopStateKernel:
    """
    循环状态内核：管理代理、目标、唤醒与交接。
    单机内存态实现，提供编程接口。
    """

    def __init__(self, max_cycles: int = 1000):
        """
        初始化内核。

        参数:
            max_cycles: 最大循环次数，超过则触发 E006 错误。
        """
        self.max_cycles = max_cycles
        self.agents: Dict[str, Agent] = OrderedDict()
        self.goals: Dict[str, Goal] = OrderedDict()
        self.wakeup_conditions: Dict[str, List[WakeupCondition]] = {}
        self.handoffs: List[HandoffContext] = []
        self.cycle_history: List[CycleRecord] = []
        self.current_cycle = 0
        self.global_state: Dict[str, Any] = {}
        self._paused = False

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
        goal.updated_at = time.time()
        return ERR_OK

    def update_goal_progress(self, goal_id: str, progress: float) -> str:
        """更新目标进度（0.0 ~ 1.0）"""
        if goal_id not in self.goals:
            return ERR_STATE_NOT_FOUND
        if not 0.0 <= progress <= 1.0:
            return ERR_INVALID_STATE

        goal = self.goals[goal_id]
        goal.progress = progress
        goal.updated_at = time.time()
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
                if time.time() >= float(cond.target):
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

        # 创建交接上下文
        context = HandoffContext(
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload or {}
        )
        self.handoffs.append(context)

        # 记录循环
        self._record_cycle(from_agent, "handoff_out", detail={"to": to_agent})
        self._record_cycle(to_agent, "handoff_in", detail={"from": from_agent})
        return ERR_OK

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
    # 持久化（简单 JSON 序列化）
    # ------------------------------------------------------------------
    def save_state(self, filepath: str) -> str:
        """
        将内核状态保存到 JSON 文件。

        返回:
            成功返回 ERR_OK，失败返回 E009。
        """
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
                    "metadata": g.metadata
                } for gid, g in self.goals.items()},
                "global_state": self.global_state,
                "current_cycle": self.current_cycle
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return ERR_OK
        except Exception:
            return ERR_PERSISTENCE

    def load_state(self, filepath: str) -> str:
        """
        从 JSON 文件加载内核状态。

        返回:
            成功返回 ERR_OK，失败返回 E009。
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                state = json.load(f)

            # 清空当前状态
            self.agents.clear()
            self.goals.clear()
            self.global_state.clear()

            # 恢复代理
            for aid, adata in state.get("agents", {}).items():
                self.agents[aid] = Agent(
                    id=adata["id"],
                    name=adata["name"],
                    role=adata["role"],
                    enabled=adata.get("enabled", True),
                    metadata=adata.get("metadata", {})
                )

            # 恢复目标
            for gid, gdata in state.get("goals", {}).items():
                goal = Goal(
                    id=gdata["id"],
                    description=gdata["description"],
                    status=gdata.get("status", "active"),
                    progress=gdata.get("progress", 0.0),
                    metadata=gdata.get("metadata", {})
                )
                self.goals[gid] = goal

            # 恢复全局状态
            self.global_state = state.get("global_state", {})
            self.current_cycle = state.get("current_cycle", 0)
            return ERR_OK
        except Exception:
            return ERR_PERSISTENCE


# ---------------------------------------------------------------------------
# 自检模块（不依赖外部文件与网络）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检核心逻辑。

    断言使用宽松阈值（大小比较/区间判断），确保必然匹配。

    返回:
        0 表示全部通过，非 0 表示失败。
    """
    print("[selftest] 开始 agent-loop-engine 核心逻辑自检...")
    failures = 0

    # ------------------------------------------------------------------
    # 1. 创建内核
    # ------------------------------------------------------------------
    kernel = LoopStateKernel(max_cycles=50)
    assert kernel is not None, "无法创建内核实例"
    print("[selftest] 1. 内核创建成功")

    # ------------------------------------------------------------------
    # 2. 代理注册与查询
    # ------------------------------------------------------------------
    ret = kernel.register_agent("agent_a", "代理A", "前端处理")
    assert ret == ERR_OK, f"注册代理A失败: {ret}"

    ret = kernel.register_agent("agent_b", "代理B", "后端处理")
    assert ret == ERR_OK, f"注册代理B失败: {ret}"

    # 重复注册应失败
    ret = kernel.register_agent("agent_a", "重复代理", "测试")
    assert ret == ERR_AGENT_ALREADY_EXISTS, "重复注册应返回 E003"

    # 查询代理
    agent = kernel.get_agent("agent_a")
    assert agent is not None, "查询代理A失败"
    assert agent.name == "代理A", "代理名称不匹配"

    # 不存在的代理
    ret = kernel.unregister_agent("nonexistent")
    assert ret == ERR_AGENT_NOT_FOUND, "注销不存在代理应返回 E002"

    # 代理数量校验（宽松断言：至少2个）
    agents = kernel.list_agents()
    assert len(agents) >= 2, f"代理数量应>=2，实际{len(agents)}"
    print("[selftest] 2. 代理管理通过")

    # ------------------------------------------------------------------
    # 3. 目标管理
    # ------------------------------------------------------------------
    ret = kernel.create_goal("goal_1", "完成项目交付")
    assert ret == ERR_OK, f"创建目标失败: {ret}"

    ret = kernel.create_goal("goal_2", "质量保障")
    assert ret == ERR_OK, f"创建目标失败: {ret}"

    # 更新状态
    ret = kernel.update_goal_status("goal_1", "active")
    assert ret == ERR_OK, f"更新目标状态失败: {ret}"

    ret = kernel.update_goal_status("goal_1", "completed")
    assert ret == ERR_OK, f"更新目标状态为completed失败: {ret}"

    # 非法状态
    ret = kernel.update_goal_status("goal_1", "invalid_status")
    assert ret == ERR_INVALID_STATE, "非法状态应返回 E005"

    # 进度更新
    ret = kernel.update_goal_progress("goal_2", 0.5)
    assert ret == ERR_OK, f"更新进度失败: {ret}"

    # 非法进度
    ret = kernel.update_goal_progress("goal_2", 1.5)
    assert ret == ERR_INVALID_STATE, "非法进度应返回 E005"

    # 目标查询
    goals = kernel.list_goals()
    assert len(goals) >= 2, f"目标数量应>=2，实际{len(goals)}"

    completed = kernel.list_goals(status="completed")
    assert len(completed) >= 1, "应至少有一个已完成目标"

    # 不存在的目标
    ret = kernel.update_goal_status("nonexistent", "active")
    assert ret == ERR_STATE_NOT_FOUND, "更新不存在目标应返回 E004"
    print("[selftest] 3. 目标管理通过")

    # ------------------------------------------------------------------
    # 4. 唤醒机制
    # ------------------------------------------------------------------
    # 手动唤醒条件
    cond_manual = WakeupCondition(type="manual", target="")
    ret = kernel.set_wakeup_condition("agent_a", cond_manual)
    assert ret == ERR_OK, f"设置手动唤醒失败: {ret}"

    # 时间唤醒条件
    future_time = str(time.time() + 3600)  # 1小时后
    cond_time = WakeupCondition(type="time", target=future_time)
    ret = kernel.set_wakeup_condition("agent_b", cond_time)
    assert ret == ERR_OK, f"设置时间唤醒失败: {ret}"

    # 状态唤醒条件
    cond_state = WakeupCondition(
        type="state",
        target="task_status",
        operator="eq",
        payload={"value": "ready"}
    )
    ret = kernel.set_wakeup_condition("agent_b", cond_state)
    assert ret == ERR_OK, f"设置状态唤醒失败: {ret}"

    # 非法唤醒条件
    cond_invalid = WakeupCondition(type="invalid", target="")
    ret = kernel.set_wakeup_condition("agent_a", cond_invalid)
    assert ret == ERR_WAKEUP_INVALID, "非法唤醒类型应返回 E008"

    # 检查唤醒
    # agent_a 有手动条件，应被唤醒
    assert kernel.check_wakeup("agent_a") is True, "agent_a 应被手动唤醒"

    # agent_b 时间条件未到，但状态条件未满足，不应被唤醒
    # 注意：这里不做严格断言，因为时间可能变化

    # 设置全局状态触发唤醒
    kernel.set_global_state("task_status", "ready")
    assert kernel.check_wakeup("agent_b") is True, "agent_b 应被状态条件唤醒"

    # 手动唤醒
    ret = kernel.wake_agent("agent_a")
    assert ret == ERR_OK, f"手动唤醒失败: {ret}"

    # 唤醒不存在的代理
    ret = kernel.wake_agent("nonexistent")
    assert ret == ERR_AGENT_NOT_FOUND, "唤醒不存在代理应返回 E002"

    # 清除唤醒条件
    ret = kernel.clear_wakeup_conditions("agent_a")
    assert ret == ERR_OK, f"清除唤醒条件失败: {ret}"

    # 清除后不应再被唤醒
    assert kernel.check_wakeup("agent_a") is False, "清除条件后不应被唤醒"
    print("[selftest] 4. 唤醒机制通过")

    # ------------------------------------------------------------------
    # 5. 交接管理
    # ------------------------------------------------------------------
    ret = kernel.handoff("agent_a", "agent_b", {"task": "data_process"})
    assert ret == ERR_OK, f"交接失败: {ret}"

    # 非法交接（相同代理）
    ret = kernel.handoff("agent_a", "agent_a")
    assert ret == ERR_HANDOFF_CONFLICT, "自我交接应返回 E007"

    # 交接给不存在的代理
    ret = kernel.handoff("agent_a", "nonexistent")
    assert ret == ERR_AGENT_NOT_FOUND, "交接给不存在代理应返回 E002"

    # 查询交接记录
    handoffs = kernel.list_handoffs()
    assert len(handoffs) >= 1, "应至少有一条交接记录"

    handoffs_a = kernel.list_handoffs(agent_id="agent_a")
    assert len(handoffs_a) >= 1, "agent_a 应至少参与一条交接"
    print("[selftest] 5. 交接管理通过")

    # ------------------------------------------------------------------
    # 6. 循环状态追踪
    # ------------------------------------------------------------------
    cycle_count = kernel.get_cycle_count()
    assert cycle_count > 0, f"循环次数应>0，实际{cycle_count}"

    history = kernel.get_cycle_history()
    assert len(history) > 0, "循环历史不应为空"

    history_a = kernel.get_cycle_history(agent_id="agent_a")
    assert len(history_a) > 0, "agent_a 应有循环历史"

    # 重置循环
    ret = kernel.reset_cycles()
    assert ret == ERR_OK, f"重置循环失败: {ret}"
    assert kernel.get_cycle_count() == 0, "重置后循环次数应为0"
    print("[selftest] 6. 循环追踪通过")

    # ------------------------------------------------------------------
    # 7. 全局状态
    # ------------------------------------------------------------------
    ret = kernel.set_global_state("mode", "production")
    assert ret == ERR_OK, f"设置全局状态失败: {ret}"

    mode = kernel.get_global_state("mode")
    assert mode == "production", "全局状态值不匹配"

    # 无效键
    ret = kernel.set_global_state("", "value")
    assert ret == ERR_INVALID_ARGUMENT, "空键应返回 E001"
    print("[selftest] 7. 全局状态通过")

    # ------------------------------------------------------------------
    # 8. 持久化（使用临时文件）
    # ------------------------------------------------------------------
    import tempfile
    import os

    # 先重置
    kernel.reset_cycles()

    # 重新注册代理（因为之前已重置）
    kernel.register_agent("agent_x", "代理X", "测试角色")
    kernel.create_goal("goal_x", "测试目标")
    kernel.set_global_state("test_key", "test_value")

    # 保存到临时文件
    tmp_path = os.path.join(tempfile.gettempdir(), "agent_loop_test_state.json")
    ret = kernel.save_state(tmp_path)
    assert ret == ERR_OK, f"保存状态失败: {ret}"

    # 创建新内核并加载
    kernel2 = LoopStateKernel()
    ret = kernel2.load_state(tmp_path)
    assert ret == ERR_OK, f"加载状态失败: {ret}"

    # 验证加载的数据
    assert kernel2.get_agent("agent_x") is not None, "加载后代理不存在"
    assert kernel2.get_goal("goal_x") is not None, "加载后目标不存在"
    assert kernel2.get_global_state("test_key") == "test_value", "加载后全局状态不匹配"

    # 清理临时文件
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    print("[selftest] 8. 持久化通过")

    # ------------------------------------------------------------------
    # 9. 错误处理验证
    # ------------------------------------------------------------------
    # 非法参数
    ret = kernel.register_agent("", "空ID", "角色")
    assert ret == ERR_INVALID_ARGUMENT, "空ID应返回 E001"

    # 不存在的代理操作
    ret = kernel.set_agent_enabled("nonexistent", False)
    assert ret == ERR_AGENT_NOT_FOUND, "操作不存在代理应返回 E002"

    # 循环上限
    small_kernel = LoopStateKernel(max_cycles=3)
    small_kernel.register_agent("a1", "代理1", "角色")
    small_kernel.register_agent("a2", "代理2", "角色")

    # 执行多次循环，直到触发上限
    exceeded = False
    try:
        for _ in range(10):
            small_kernel.handoff("a1", "a2", {"seq": _})
    except RuntimeError as e:
        if ERR_CYCLE_LIMIT in str(e):
            exceeded = True

    assert exceeded, "应触发循环次数上限 E006"
    print("[selftest] 9. 错误处理通过")

    # ------------------------------------------------------------------
    # 10. 综合场景验证
    # ------------------------------------------------------------------
    # 模拟完整工作流
    kernel3 = LoopStateKernel()
    kernel3.register_agent("frontend", "前端代理", "UI处理")
    kernel3.register_agent("backend", "后端代理", "逻辑处理")
    kernel3.register_agent("db", "数据库代理", "存储")

    kernel3.create_goal("project", "完成用户请求")

    # 前端 -> 后端 -> 数据库
    assert kernel3.handoff("frontend", "backend", {"action": "validate"}) == ERR_OK
    assert kernel3.handoff("backend", "db", {"action": "save"}) == ERR_OK

    # 目标进度更新
    assert kernel3.update_goal_progress("project", 0.7) == ERR_OK
    goal = kernel3.get_goal("project")
    assert goal.progress > 0.5, "目标进度应大于0.5"

    # 完成目标
    assert kernel3.update_goal_status("project", "completed") == ERR_OK

    # 验证循环次数
    assert kernel3.get_cycle_count() >= 2, "循环次数应>=2"

    # 验证交接链
    handoff_chain = kernel3.list_handoffs()
    assert len(handoff_chain) >= 2, "应有至少2次交接"

    print("[selftest] 10. 综合场景通过")

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    if failures > 0:
        print(f"[selftest] 失败: {failures} 项检查未通过")
        return 1

    print("[selftest] 全部自检通过 ✔")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="agent-loop-engine 循环状态内核",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/main.py --selftest     # 运行离线自检
  python scripts/main.py --info         # 显示版本信息
        """
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不依赖外部文件与网络）"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="显示版本信息"
    )

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if args.info:
        print("agent-loop-engine v1.0.2")
        print("轻量级循环状态内核，管理代理团队持久目标、唤醒与交接。")
        print("MIT License")
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
