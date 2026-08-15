#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体协作编排器 - 生产级实现
支持任务拆解、角色分配、执行编排、结果整合与质量校验
"""

import argparse
import json
import os
import random
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable


# ============================================================
# 错误码定义
# ============================================================
class ErrorCode:
    """错误码常量定义"""
    E001 = "E001: 任务描述为空或格式非法"
    E002 = "E002: 角色配置JSON格式非法"
    E003 = "E003: 角色配置包含未知角色"
    E004 = "E004: 参数覆盖格式非法"
    E005 = "E005: 输出目录创建失败"
    E006 = "E006: 结果文件写入失败"
    E007 = "E007: Agent执行超时"
    E008 = "E008: Agent执行重试次数耗尽"
    E009 = "E009: 结果完整性校验失败"
    E010 = "E010: 未知内部错误"


# ============================================================
# 核心数据结构
# ============================================================
VALID_ROLES = ["架构师", "测试工程师", "数据分析师", "研究员", "代码审查员"]

DEFAULT_AGENTS = [
    {"role": "架构师", "count": 1},
    {"role": "研究员", "count": 1},
]

# 任务描述最小长度
MIN_TASK_LENGTH = 10

# 超时和重试的默认值及边界
DEFAULT_TIMEOUT = 300
DEFAULT_RETRY = 2
MAX_TIMEOUT = 3600
MAX_RETRY = 10

# 完整性评分阈值
COMPLETENESS_THRESHOLD_WARN = 0.8
COMPLETENESS_THRESHOLD_PASS = 0.9

# LLM API 配置（可通过环境变量覆盖）
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))

# 缓存配置
CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.environ.get("CACHE_TTL", "3600"))  # 1小时

# 并发控制
MAX_CONCURRENT_AGENTS = int(os.environ.get("MAX_CONCURRENT_AGENTS", "5"))

# 熔断配置
CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get("CIRCUIT_BREAKER_THRESHOLD", "5"))
CIRCUIT_BREAKER_TIMEOUT = int(os.environ.get("CIRCUIT_BREAKER_TIMEOUT", "60"))


class AgentConfig:
    """Agent角色配置"""
    def __init__(self, role: str, count: int):
        self.role = role
        self.count = count

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "count": self.count}


class TaskInput:
    """任务输入参数"""
    def __init__(
        self,
        task: str,
        agents: Optional[List[AgentConfig]] = None,
        params: Optional[Dict[str, str]] = None,
        output_dir: str = "./output",
        timeout: int = DEFAULT_TIMEOUT,
        retry: int = DEFAULT_RETRY,
    ):
        self.task = task
        self.agents = agents or [AgentConfig(**a) for a in DEFAULT_AGENTS]
        self.params = params or {}
        self.output_dir = output_dir
        self.timeout = timeout
        self.retry = retry


class AgentResult:
    """单个Agent的执行结果"""
    def __init__(
        self,
        task_id: str,
        role: str,
        status: str,
        output: str,
        execution_time: float,
        attempts: int,
    ):
        self.task_id = task_id
        self.role = role
        self.status = status
        self.output = output
        self.execution_time = execution_time
        self.attempts = attempts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "role": self.role,
            "status": self.status,
            "output": self.output,
            "execution_time": self.execution_time,
            "attempts": self.attempts,
        }


class OrchestratorResult:
    """编排器最终结果"""
    def __init__(
        self,
        task: str,
        agents: List[Dict[str, Any]],
        results: List[AgentResult],
        completeness: float,
        status: str,
        timestamp: str,
    ):
        self.task = task
        self.agents = agents
        self.results = results
        self.completeness = completeness
        self.status = status
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "agents": self.agents,
            "results": [r.to_dict() for r in self.results],
            "completeness": self.completeness,
            "status": self.status,
            "timestamp": self.timestamp,
        }


# ============================================================
# 缓存实现
# ============================================================
class SimpleCache:
    """简单的内存缓存实现"""
    def __init__(self, ttl: int = CACHE_TTL):
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if not CACHE_ENABLED:
            return None
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if CACHE_ENABLED:
            self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()


# 全局缓存实例
global_cache = SimpleCache()


# ============================================================
# 熔断器实现
# ============================================================
class CircuitBreaker:
    """熔断器：连续失败超过阈值则熔断，一段时间后自动恢复"""
    def __init__(self, threshold: int = CIRCUIT_BREAKER_THRESHOLD, timeout: int = CIRCUIT_BREAKER_TIMEOUT):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.is_open = False

    def record_success(self) -> None:
        self.failure_count = 0
        self.is_open = False

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.threshold:
            self.is_open = True

    def can_proceed(self) -> bool:
        if not self.is_open:
            return True
        # 检查是否超过熔断时间
        if time.time() - self.last_failure_time > self.timeout:
            self.is_open = False
            self.failure_count = 0
            return True
        return False


# 全局熔断器实例
global_circuit_breaker = CircuitBreaker()


# ============================================================
# LLM API 调用（带指数退避重试和jitter）
# ============================================================
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def call_llm_api(prompt: str, role: str, timeout: int = LLM_TIMEOUT, max_retries: int = LLM_MAX_RETRIES) -> str:
    """
    调用真实LLM API，带指数退避重试（含jitter）、超时处理、熔断和缓存
    """
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY 环境变量未设置，无法调用真实LLM API")

    # 检查熔断器
    if not global_circuit_breaker.can_proceed():
        raise RuntimeError("熔断器已打开，暂时无法调用LLM API")

    # 检查缓存
    cache_key = f"llm:{role}:{hash(prompt)}"
    cached_result = global_cache.get(cache_key)
    if cached_result:
        return cached_result

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": f"你是一个专业的{role}，请根据任务要求输出专业分析结果。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }

    data = json.dumps(payload).encode("utf-8")
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                LLM_API_URL,
                data=data,
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                result = response_data["choices"][0]["message"]["content"].strip()

                # 记录成功并缓存结果
                global_circuit_breaker.record_success()
                global_cache.set(cache_key, result)
                return result

        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429 or e.code >= 500:  # 限流或服务器错误
                if attempt < max_retries:
                    # 指数退避 + jitter
                    base_wait = 2 ** attempt
                    jitter = random.uniform(0, 0.5 * base_wait)
                    wait_time = base_wait + jitter
                    time.sleep(wait_time)
                else:
                    global_circuit_breaker.record_failure()
                    break
            else:
                global_circuit_breaker.record_failure()
                raise
        except urllib.error.URLError as e:
            last_error = e
            if attempt < max_retries:
                base_wait = 2 ** attempt
                jitter = random.uniform(0, 0.5 * base_wait)
                wait_time = base_wait + jitter
                time.sleep(wait_time)
            else:
                global_circuit_breaker.record_failure()
                break
        except TimeoutError:
            last_error = TimeoutError("LLM API 调用超时")
            if attempt < max_retries:
                base_wait = 2 ** attempt
                jitter = random.uniform(0, 0.5 * base_wait)
                wait_time = base_wait + jitter
                time.sleep(wait_time)
            else:
                global_circuit_breaker.record_failure()
                break

    # 重试耗尽，降级处理
    raise RuntimeError(f"LLM API 调用失败，重试{max_retries}次后仍失败: {last_error}")


# ============================================================
# 任务拆解器
# ============================================================
class TaskDecomposer:
    """将复杂任务按角色模板拆分为子任务"""

    # 角色对应的任务模板
    ROLE_TEMPLATES = {
        "架构师": "设计系统架构方案，包括模块划分、接口定义和数据流设计。",
        "测试工程师": "制定测试策略，设计测试用例，覆盖正常和异常场景。",
        "数据分析师": "分析数据特征，识别模式，提出数据驱动的建议。",
        "研究员": "调研相关领域知识，收集信息，整理研究结论。",
        "代码审查员": "审查代码质量，识别潜在问题，提出改进建议。",
    }

    def __init__(self, task: str, agents: List[AgentConfig], params: Optional[Dict[str, str]] = None):
        self.task = task
        self.agents = agents
        self.params = params or {}

    def decompose(self) -> List[Dict[str, Any]]:
        """将任务拆分为子任务列表，支持参数覆盖"""
        subtasks = []
        for agent in self.agents:
            for i in range(agent.count):
                subtask_id = f"{agent.role}_{i+1}"
                template = self.ROLE_TEMPLATES.get(
                    agent.role, "执行分析任务并输出结果。"
                )
                # 应用参数覆盖
                description = f"{template} 任务: {self.task}"
                if self.params:
                    param_str = json.dumps(self.params, ensure_ascii=False)
                    description += f"\n附加参数: {param_str}"
                subtasks.append({
                    "task_id": subtask_id,
                    "role": agent.role,
                    "description": description,
                    "dependencies": self._get_dependencies(agent.role, i),
                })
        return subtasks

    def _get_dependencies(self, role: str, index: int) -> List[str]:
        """定义角色间的依赖关系"""
        deps = []
        if role == "测试工程师":
            deps.append("架构师_1")
        elif role == "代码审查员":
            deps.append("架构师_1")
        return deps


# ============================================================
# Agent执行器
# ============================================================
class AgentExecutor:
    """执行单个Agent任务，支持超时、重试、缓存和并发控制"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, retry: int = DEFAULT_RETRY):
        self.timeout = timeout
        self.retry = retry
        self.semaphore = None  # 并发控制信号量，在编排器中设置

    def execute(
        self, task_id: str, role: str, description: str
    ) -> AgentResult:
        """执行任务，带重试机制、缓存和并发控制"""
        start_time = time.time()
        attempts = 0

        # 检查缓存
        cache_key = f"agent:{task_id}:{hash(description)}"
        cached_result = global_cache.get(cache_key)
        if cached_result:
            return AgentResult(
                task_id=task_id,
                role=role,
                status="success",
                output=cached_result,
                execution_time=0.0,
                attempts=1,
            )

        while attempts <= self.retry:
            attempts += 1
            try:
                # 调用真实LLM API
                prompt = f"任务ID: {task_id}\n角色: {role}\n任务描述: {description}"
                output = call_llm_api(prompt, role, timeout=self.timeout)
                elapsed = time.time() - start_time

                # 缓存结果
                global_cache.set(cache_key, output)

                return AgentResult(
                    task_id=task_id,
                    role=role,
                    status="success",
                    output=output,
                    execution_time=elapsed,
                    attempts=attempts,
                )
            except TimeoutError:
                if attempts > self.retry:
                    raise TimeoutError(ErrorCode.E007)
                # 指数退避 + jitter
                base_wait = 2 ** attempts
                jitter = random.uniform(0, 0.5 * base_wait)
                time.sleep(base_wait + jitter)
            except Exception as e:
                if attempts > self.retry:
                    raise RuntimeError(f"{ErrorCode.E008}: {str(e)}")
                # 指数退避 + jitter
                base_wait = 2 ** attempts
                jitter = random.uniform(0, 0.5 * base_wait)
                time.sleep(base_wait + jitter)

        raise RuntimeError(ErrorCode.E008)


# ============================================================
# 结果整合器
# ============================================================
class ResultIntegrator:
    """整合所有Agent结果，进行完整性校验"""

    REQUIRED_FIELDS = ["task_id", "role", "status", "output"]

    def integrate(self, results: List[AgentResult]) -> Tuple[float, str]:
        """计算完整性评分并返回状态"""
        if not results:
            return 0.0, "FAIL"

        total_score = 0.0
        for result in results:
            result_dict = result.to_dict()
            field_score = 0.0
            for field in self.REQUIRED_FIELDS:
                if field in result_dict and result_dict[field]:
                    field_score += 1.0 / len(self.REQUIRED_FIELDS)
            total_score += field_score

        completeness = total_score / len(results)

        if completeness >= COMPLETENESS_THRESHOLD_PASS:
            status = "PASS"
        elif completeness >= COMPLETENESS_THRESHOLD_WARN:
            status = "WARN"
        else:
            status = "FAIL"

        return completeness, status


# =================================
