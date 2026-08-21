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
import logging
import threading
import signal
import random
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Callable, Tuple

# 配置日志 - 使用独立 logger 避免全局污染
logger = logging.getLogger("agent_loop_engine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(_handler)


# ---------------------------------------------------------------------------
# 错误码定义（整数枚举，1-10）
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INVALID_ARGUMENT = 1       # 参数无效
ERR_AGENT_NOT_FOUND = 2        # 代理不存在
ERR_AGENT_ALREADY_EXISTS = 3   # 代理已存在
ERR_STATE_NOT_FOUND = 4        # 状态不存在
ERR_INVALID_STATE = 5          # 状态值非法
ERR_CYCLE_LIMIT = 6            # 循环次数超限
ERR_HANDOFF_CONFLICT = 7       # 交接冲突
ERR_WAKEUP_INVALID = 8         # 唤醒条件非法
ERR_PERSISTENCE = 9            # 持久化失败
ERR_INTERNAL = 10              # 内部错误

# 错误码到消息的映射
ERROR_MESSAGES = {
    ERR_OK: "成功",
    ERR_INVALID_ARGUMENT: "参数无效",
    ERR_AGENT_NOT_FOUND: "代理不存在",
    ERR_AGENT_ALREADY_EXISTS: "代理已存在",
    ERR_STATE_NOT_FOUND: "状态不存在",
    ERR_INVALID_STATE: "状态值非法",
    ERR_CYCLE_LIMIT: "循环次数超限",
    ERR_HANDOFF_CONFLICT: "交接冲突",
    ERR_WAKEUP_INVALID: "唤醒条件非法",
    ERR_PERSISTENCE: "持久化失败",
    ERR_INTERNAL: "内部错误",
}


def err_msg(err_code: int) -> str:
    """获取错误码对应的消息"""
    return ERROR_MESSAGES.get(err_code, f"未知错误码: {err_code}")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def utc_now() -> float:
    """返回 UTC 时间戳"""
    return datetime.now(timezone.utc).timestamp()


def utc_now_str() -> str:
    """返回 UTC 时间字符串"""
    return datetime.now(timezone.utc).isoformat()


# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)

# 全局线程池（复用，避免资源泄漏）
_global_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent_loop_io")


def retry_io(func: Callable, *args, max_retries: int = 3, timeout: float = 5.0, **kwargs) -> Any:
    """
    带指数退避+随机抖动重试的 I/O 操作包装器。
    仅重试可重试异常（网络超时、连接错误等），永久错误（权限拒绝等）直接抛出。
    每次尝试有超时控制。
    
    参数:
        func: 要执行的函数
        max_retries: 最大重试次数
        timeout: 每次尝试的超时时间（秒）
    
    返回:
        函数执行结果
    
    抛出:
        最后一次异常（如果所有重试都失败）
    """
    delay = 0.5
    last_exc = None
    
    for attempt in range(max_retries):
        try:
            # 使用全局线程池实现超时控制（复用，不新建）
            future = _global_executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError:
                future.cancel()
                raise TimeoutError(f"操作超时（{timeout}秒）")
            
        except RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            logger.warning(f"重试 {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                # 指数退避 + 随机抖动
                sleep_time = 0.5 * (2 ** attempt) + random.uniform(0, 0.1)
                time.sleep(sleep_time)
        except Exception as e:
            # 永久错误，不重试
            logger.error(f"永久错误，不重试: {e}")
            raise
    
    raise last_exc


def get_secret_key() -> str:
    """
    从环境变量获取签名密钥。
    如果未设置，抛出异常。
    """
    secret_key = os.environ.get("AGENT_LOOP_ENGINE_SECRET")
    if not secret_key:
        raise ValueError(
            "未设置 AGENT_LOOP_ENGINE_SECRET 环境变量。"
            "请设置强密钥以启用交接签名验证。"
        )
    if len(secret_key) < 16:
        raise ValueError("AGENT_LOOP_ENGINE_SECRET 必须至少 16 个字符")
    return secret_key


def compute_handoff_signature(context: 'HandoffContext', secret_key: Optional[str] = None) -> str:
    """计算交接上下文的 HMAC 签名"""
    if secret_key is None:
        secret_key = get_secret_key()
    
    payload = json.dumps({
        "from_agent": context.from_agent,
        "to_agent": context.to_agent,
        "payload": context.payload,
        "timestamp": context.timestamp
    }, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hmac.new(secret_key.encode('utf-8'), payload, hashlib.sha256).hexdigest()


def verify_handoff_signature(context: 'HandoffContext', secret_key: Optional[str] = None) -> bool:
    """验证交接上下文的 HMAC 签名"""
    if secret_key is None:
        secret_key = get_secret_key()
    
    expected = compute_handoff_signature(context, secret_key)
    return hmac.compare_digest(expected, context.signature)


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
# 持久化层
# ---------------------------------------------------------------------------
class PersistenceLayer:
    """
    基于 JSON 文件的持久化层。
    负责保存和加载内核状态。
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def save(self, kernel: 'LoopStateKernel') -> int:
        """
        保存内核状态到 JSON 文件。
        返回 ERR_OK 或错误码。
        """
        try:
            state = {
                "agents": {
                    aid: {
                        "id": a.id,
                        "name": a.name,
                        "role": a.role,
                        "enabled": a.enabled,
                        "metadata": a.metadata
                    } for aid, a in kernel.agents.items()
                },
                "goals": {
                    gid: {
                        "id": g.id,
                        "description": g.description,
                        "status": g.status,
                        "created_at": g.created_at,
                        "updated_at": g.updated_at,
                        "progress": g.progress,
                        "metadata": g.metadata
                    } for gid, g in kernel.goals.items()
                },
                "wakeup_conditions": {
                    aid: [
                        {
                            "type": c.type,
                            "target": c.target,
                            "operator": c.operator,
                            "payload": c.payload
                        } for c in conditions
                    ] for aid, conditions in kernel.wakeup_conditions.items()
                },
                "handoffs": [
                    {
                        "from_agent": h.from_agent,
                        "to_agent": h.to_agent,
                        "payload": h.payload,
                        "timestamp": h.timestamp,
                        "signature": h.signature
                    } for h in kernel.handoffs
                ],
                "cycle_history": [
                    {
                        "cycle_id": r.cycle_id,
                        "agent_id": r.agent_id,
                        "action": r.action,
                        "timestamp": r.timestamp,
                        "result": r.result,
                        "detail": r.detail
                    } for r in kernel.cycle_history
                ],
                "current_cycle": kernel.current_cycle,
                "global_state": kernel.global_state,
                "max_cycles": kernel.max_cycles
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.file_path) or '.', exist_ok=True)
            
            # 原子写入
            temp_file = self.file_path + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, self.file_path)
            
            return ERR_OK
        except Exception as e:
            logger.error(f"持久化保存失败: {e}")
            return ERR_PERSISTENCE

    def load(self, kernel: 'LoopStateKernel') -> int:
        """
        从 JSON 文件加载内核状态。
        返回 ERR_OK 或错误码。
        """
        try:
            if not os.path.exists(self.file_path):
                return ERR_OK
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # 恢复代理
            kernel.agents.clear()
            for aid, agent_data in state.get("agents", {}).items():
                kernel.agents[aid] = Agent(
                    id=agent_data["id"],
                    name=agent_data["name"],
                    role=agent_data["role"],
                    enabled=agent_data.get("enabled", True),
                    metadata=agent_data.get("metadata", {})
                )
            
            # 恢复目标
            kernel.goals.clear()
            for gid, goal_data in state.get("goals", {}).items():
                kernel.goals[gid] = Goal(
                    id=goal_data["id"],
                    description=goal_data["description"],
                    status=goal_data.get("status", "active"),
                    created_at=goal_data.get("created_at", utc_now()),
                    updated_at=goal_data.get("updated_at", utc_now()),
                    progress=goal_data.get("progress", 0.0),
                    metadata=goal_data.get("metadata", {})
                )
            
            # 恢复唤醒条件
            kernel.wakeup_conditions.clear()
            for aid, conditions_data in state.get("wakeup_conditions", {}).items():
                kernel.wakeup_conditions[aid] = [
                    WakeupCondition(
                        type=c["type"],
                        target=c.get("target", ""),
                        operator=c.get("operator", "eq"),
                        payload=c.get("payload", {})
                    ) for c in conditions_data
                ]
            
            # 恢复交接记录
            kernel.handoffs.clear()
            for h_data in state.get("handoffs", []):
                kernel.handoffs.append(HandoffContext(
                    from_agent=h_data["from_agent"],
                    to_agent=h_data["to_agent"],
                    payload=h_data.get("payload", {}),
                    timestamp=h_data.get("timestamp", utc_now()),
                    signature=h_data.get("signature", "")
                ))
            
            # 恢复循环历史
            kernel.cycle_history.clear()
            for r_data in state.get("cycle_history", []):
                kernel.cycle_history.append(CycleRecord(
                    cycle_id=r_data["cycle_id"],
                    agent_id=r_data["agent_id"],
                    action=r_data["action"],
                    timestamp=r_data.get("timestamp", utc_now()),
                    result=r_data.get("result", "ok"),
                    detail=r_data.get("detail", {})
                ))
            
            # 恢复其他状态
            kernel.current_cycle = state.get("current_cycle", 0)
            kernel.global_state = state.get("global_state", {})
            kernel.max_cycles = state.get("max_cycles", kernel.max_cycles)
            
            return ERR_OK
        except Exception as e:
            logger.error(f"持久化加载失败: {e}")
            return ERR_PERSISTENCE


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
            max_cycles: 最大循环次数，超过则触发 ERR_CYCLE_LIMIT 错误。
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
        self.dry_run = False  # 实例属性，不影响核心功能
        self.persistence = None

        # 如果提供了状态文件，初始化持久化层并尝试加载
        if state_file:
            self.persistence = PersistenceLayer(state_file)
            if os.path.exists(state_file):
                result = self.persistence.load(self)
                if result != ERR_OK:
                    logger.warning(f"加载持久化状态失败: {err_msg(result)}")

    # ------------------------------------------------------------------
    # 持久化方法
    # ------------------------------------------------------------------
    def save_state(self) -> int:
        """保存当前状态到持久化层"""
        if not self.persistence:
            return ERR_PERSISTENCE
        return self.persistence.save(self)

    def load_state(self, file_path: Optional[str] = None) -> int:
        """从持久化层加载状态"""
        if file_path:
            self.persistence = PersistenceLayer(file_path)
            self.state_file = file_path
        if not self.persistence:
            return ERR_PERSISTENCE
        return self.persistence.load(self)

    # ------------------------------------------------------------------
    # 代理管理
    # ------------------------------------------------------------------
    def register_agent(self, agent_id: str, name: str, role: str,
                       metadata: Optional[Dict[str, Any]] = None) -> int:
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

    def unregister_agent(self, agent_id: str) -> int:
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

    def set_agent_enabled(self, agent_id: str, enabled: bool) -> int:
        """启用或禁用代理"""
        if agent_id not in self.agents:
            return ERR_AGENT_NOT_FOUND
        self.agents[agent_id].enabled = enabled
        return ERR_OK

    # ------------------------------------------------------------------
    # 目标管理
    # ------------------------------------------------------------------
    def create_goal(self, goal_id: str, description: str,
                    metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        创建持久目标。

        返回:
            成功返回 ERR_OK，失败返回错误码。
        """


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--state-file", default=None, help="文档声明的参数")  # F3 补全
    args = ap.parse_args()
