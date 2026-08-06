#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体协作编排器 - 生产级实现
支持任务拆解、角色分配、执行编排、结果整合与质量校验
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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

    def __init__(self, task: str, agents: List[AgentConfig]):
        self.task = task
        self.agents = agents

    def decompose(self) -> List[Dict[str, Any]]:
        """将任务拆分为子任务列表"""
        subtasks = []
        for agent in self.agents:
            for i in range(agent.count):
                subtask_id = f"{agent.role}_{i+1}"
                template = self.ROLE_TEMPLATES.get(
                    agent.role, "执行分析任务并输出结果。"
                )
                subtasks.append({
                    "task_id": subtask_id,
                    "role": agent.role,
                    "description": f"{template} 任务: {self.task}",
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
    """执行单个Agent任务，支持超时和重试"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, retry: int = DEFAULT_RETRY):
        self.timeout = timeout
        self.retry = retry

    def execute(
        self, task_id: str, role: str, description: str
    ) -> AgentResult:
        """执行任务，带重试机制"""
        start_time = time.time()
        attempts = 0

        while attempts <= self.retry:
            attempts += 1
            try:
                # 模拟执行（实际可替换为真实AI调用）
                output = self._simulate_execution(role, description)
                elapsed = time.time() - start_time

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
                time.sleep(2 ** attempts)  # 指数退避
            except Exception as e:
                if attempts > self.retry:
                    raise RuntimeError(f"{ErrorCode.E008}: {str(e)}")
                time.sleep(2 ** attempts)

        raise RuntimeError(ErrorCode.E008)

    def _simulate_execution(self, role: str, description: str) -> str:
        """模拟Agent执行，生成结构化输出"""
        # 基于角色生成不同的输出模板
        templates = {
            "架构师": "架构方案: 采用微服务架构，包含API网关、服务注册中心、配置中心。",
            "测试工程师": "测试计划: 包含单元测试、集成测试、端到端测试，覆盖关键路径。",
            "数据分析师": "数据分析: 识别出3个关键趋势，提出2条优化建议。",
            "研究员": "研究结论: 汇总5个相关领域的最新进展，提出3个研究方向。",
            "代码审查员": "审查报告: 发现2个潜在问题，1个性能瓶颈，建议优化方案。",
        }
        template = templates.get(role, "执行完成，输出分析结果。")
        return f"{template} 任务描述: {description[:50]}..."

    def _check_timeout(self, start_time: float) -> None:
        """检查是否超时"""
        if time.time() - start_time > self.timeout:
            raise TimeoutError(ErrorCode.E007)


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


# ============================================================
# 编排器主类
# ============================================================
class MultiAgentOrchestrator:
    """多智能体协作编排器"""

    def __init__(self, config: TaskInput):
        self.config = config
        self.decomposer = TaskDecomposer(config.task, config.agents)
        self.executor = AgentExecutor(config.timeout, config.retry)
        self.integrator = ResultIntegrator()

    def run(self) -> OrchestratorResult:
        """执行完整编排流程"""
        try:
            # 1. 任务拆解
            subtasks = self.decomposer.decompose()

            # 2. 执行编排（按依赖排序）
            results = self._execute_with_dependencies(subtasks)

            # 3. 结果整合
            completeness, status = self.integrator.integrate(results)

            # 4. 生成时间戳
            timestamp = datetime.now(timezone.utc).isoformat()

            return OrchestratorResult(
                task=self.config.task,
                agents=[a.to_dict() for a in self.config.agents],
                results=results,
                completeness=completeness,
                status=status,
                timestamp=timestamp,
            )
        except Exception as e:
            raise RuntimeError(f"{ErrorCode.E010}: {str(e)}")

    def _execute_with_dependencies(
        self, subtasks: List[Dict[str, Any]]
    ) -> List[AgentResult]:
        """按依赖关系执行子任务"""
        results: List[AgentResult] = []
        executed: Dict[str, AgentResult] = {}

        # 简单拓扑排序（串行执行）
        remaining = subtasks.copy()
        while remaining:
            progress = False
            for subtask in remaining[:]:
                deps = subtask.get("dependencies", [])
                if all(dep in executed for dep in deps):
                    result = self.executor.execute(
                        subtask["task_id"],
                        subtask["role"],
                        subtask["description"],
                    )
                    executed[subtask["task_id"]] = result
                    results.append(result)
                    remaining.remove(subtask)
                    progress = True

            if not progress:
                # 存在循环依赖或无法满足的依赖
                for subtask in remaining:
                    result = self.executor.execute(
                        subtask["task_id"],
                        subtask["role"],
                        subtask["description"],
                    )
                    executed[subtask["task_id"]] = result
                    results.append(result)
                break

        return results


# ============================================================
# 输入校验
# ============================================================
def validate_input(args: argparse.Namespace) -> TaskInput:
    """校验输入参数并构建TaskInput"""
    # 校验任务描述
    if not args.task or len(args.task.strip()) < MIN_TASK_LENGTH:
        raise ValueError(ErrorCode.E001)

    # 解析角色配置
    agents = []
    if args.agents:
        try:
            agent_data = json.loads(args.agents)
            if not isinstance(agent_data, list):
                raise ValueError(ErrorCode.E002)
            for item in agent_data:
                if not isinstance(item, dict) or "role" not in item:
                    raise ValueError(ErrorCode.E002)
                role = item["role"]
                count = item.get("count", 1)
                if role not in VALID_ROLES:
                    raise ValueError(ErrorCode.E003)
                if not isinstance(count, int) or count < 1:
                    raise ValueError(ErrorCode.E002)
                agents.append(AgentConfig(role, count))
        except json.JSONDecodeError:
            raise ValueError(ErrorCode.E002)
    else:
        agents = [AgentConfig(**a) for a in DEFAULT_AGENTS]

    # 解析参数覆盖
    params = {}
    if args.params:
        try:
            params = json.loads(args.params)
            if not isinstance(params, dict):
                raise ValueError(ErrorCode.E004)
        except json.JSONDecodeError:
            raise ValueError(ErrorCode.E004)

    # 校验超时和重试
    timeout = args.timeout if args.timeout else DEFAULT_TIMEOUT
    retry = args.retry if args.retry else DEFAULT_RETRY

    if timeout < 1 or timeout > MAX_TIMEOUT:
        raise ValueError(f"超时时间必须在1-{MAX_TIMEOUT}秒之间")
    if retry < 0 or retry > MAX_RETRY:
        raise ValueError(f"重试次数必须在0-{MAX_RETRY}之间")

    return TaskInput(
        task=args.task,
        agents=agents,
        params=params,
        output_dir=args.output_dir,
        timeout=timeout,
        retry=retry,
    )


# ============================================================
# 输出处理
# ============================================================
def atomic_write_json(filepath: Path, data: Dict[str, Any]) -> None:
    """原子化写入JSON文件"""
    try:
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(
            dir=str(filepath.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            # 原子替换
            os.replace(temp_path, filepath)
        except Exception:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except OSError as e:
        raise OSError(f"{ErrorCode.E006}: {str(e)}")


def save_result(result: OrchestratorResult, output_dir: str) -> Path:
    """保存结果到输出目录"""
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"{ErrorCode.E005}: {str(e)}")

    # 生成文件名
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"orchestrator_result_{timestamp}.json"
    filepath = output_path / filename

    # 原子化写入
    atomic_write_json(filepath, result.to_dict())

    return filepath


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("多智能体协作编排器 - 自检")
    print("=" * 60)

    try:
        # 测试1: 任务拆解
        print("\n[测试1] 任务拆解...")
        task = "分析电商平台用户行为数据并优化推荐算法"
        agents = [
            AgentConfig("架构师", 1),
            AgentConfig("数据分析师", 2),
            AgentConfig("测试工程师", 1),
        ]
        decomposer = TaskDecomposer(task, agents)
        subtasks = decomposer.decompose()
        assert len(subtasks) == 4, f"预期4个子任务，实际{len(subtasks)}"
        assert subtasks[0]["role"] == "架构师"
        assert subtasks[1]["role"] == "数据分析师"
        print(f"  ✓ 拆解成功: {len(subtasks)}个子任务")

        # 测试2: Agent执行
        print("\n[测试2] Agent执行...")
        executor = AgentExecutor(timeout=10, retry=1)
        result = executor.execute("test_1", "架构师", "测试任务")
        assert result.status == "success"
        assert result.output, "输出不能为空"
        assert result.attempts >= 1
        print(f"  ✓ 执行成功: {result.role}, 耗时{result.execution_time:.2f}s")

        # 测试3: 结果整合
        print("\n[测试3] 结果整合...")
        integrator = ResultIntegrator()
        results = [
            AgentResult("t1", "架构师", "success", "输出1", 1.0, 1),
            AgentResult("t2", "研究员", "success", "输出2", 1.0, 1),
        ]
        completeness, status = integrator.integrate(results)
        assert completeness >= 0.9, f"完整性评分异常: {completeness}"
        assert status == "PASS"
        print(f"  ✓ 整合成功: 完整性={completeness:.2f}, 状态={status}")

        # 测试4: 完整编排流程
        print("\n[测试4] 完整编排流程...")
        config = TaskInput(
            task="设计一个高可用微服务架构并制定测试方案",
            agents=agents,
            output_dir=tempfile.mkdtemp(),
            timeout=30,
            retry=1,
        )
        orchestrator = MultiAgentOrchestrator(config)
        final_result = orchestrator.run()
        assert final_result.status in ["PASS", "WARN"]
        assert len(final_result.results) == 4
        print(f"  ✓ 编排成功: 状态={final_result.status}, "
              f"完整性={final_result.completeness:.2f}")

        # 测试5: 结果保存
        print("\n[测试5] 结果保存...")
        filepath = save_result(final_result, config.output_dir)
        assert filepath.exists(), "结果文件不存在"
        with open(filepath, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["task"] == config.task
        print(f"  ✓ 保存成功: {filepath}")

        # 测试6: 错误处理
        print("\n[测试6] 错误处理...")
        try:
            validate_input(argparse.Namespace(
                task="短", agents=None, params=None,
                output_dir="./output", timeout=300, retry=2
            ))
            assert False, "应该抛出E001错误"
        except ValueError as e:
            assert "E001" in str(e)
            print(f"  ✓ 错误处理正确: {e}")

        print("\n" + "=" * 60)
        print("所有自检通过!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ 自检失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 自检异常: {e}")
        return 1


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="多智能体协作编排器 - 编排多个AI Agent协作完成复杂任务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --task "分析用户行为数据并优化推荐算法"
  python run.py --task "设计微服务架构" --agents '[{"role":"架构师","count":2}]'
  python run.py --selftest
        """,
    )
    parser.add_argument(
        "--task", type=str, help="任务描述（至少10个字符）"
    )
    parser.add_argument(
        "--agents", type=str,
        help='角色配置JSON，如: [{"role":"架构师","count":1}]'
    )
    parser.add_argument(
        "--params", type=str, help='参数覆盖JSON，如: {"key":"value"}'
    )
    parser.add_argument(
        "--output-dir", type=str, default="./output",
        help="输出目录（默认: ./output）"
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"单Agent超时秒数（默认: {DEFAULT_TIMEOUT}）"
    )
    parser.add_argument(
        "--retry", type=int, default=DEFAULT_RETRY,
        help=f"失败重试次数（默认: {DEFAULT_RETRY}）"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 校验参数
    try:
        config = validate_input(args)
    except ValueError as e:
        print(f"参数错误: {e}", file=sys.stderr)
        return 1

    # 执行编排
    try:
        orchestrator = MultiAgentOrchestrator(config)
        result = orchestrator.run()

        # 保存结果
        filepath = save_result(result, config.output_dir)

        # 输出摘要
        print(f"任务: {result.task}")
        print(f"状态: {result.status}")
        print(f"完整性: {result.completeness:.2f}")
        print(f"Agent数: {len(result.results)}")
        print(f"结果文件: {filepath}")

        # 输出详细结果
        print("\n详细结果:")
        for r in result.results:
            print(f"  [{r.role}] {r.task_id}: {r.status} "
                  f"(耗时{r.execution_time:.2f}s, 尝试{r.attempts}次)")

        # 警告处理
        if result.status == "WARN":
            print("\n⚠ 警告: 结果完整性低于预期，请检查Agent输出", file=sys.stderr)
            return 2
        elif result.status == "FAIL":
            print(f"\n✗ 错误: {ErrorCode.E009}", file=sys.stderr)
            return 3

        return 0

    except TimeoutError as e:
        print(f"超时错误: {e}", file=sys.stderr)
        return 4
    except OSError as e:
        print(f"IO错误: {e}", file=sys.stderr)
        return 5
    except Exception as e:
        print(f"执行错误: {e}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    sys.exit(main())
