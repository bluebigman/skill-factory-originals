#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体协作框架 - 独立实现
基于功能规格文档进行 clean-room 重写
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime
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
    def __init__(self, role: str, output: str, success: bool, duration: float):
        self.role = role
        self.output = output
        self.success = success
        self.duration = duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "output": self.output,
            "success": self.success,
            "duration": self.duration,
        }


# ============================================================
# 输入校验模块
# ============================================================
class InputValidator:
    """输入参数校验器"""

    @staticmethod
    def validate_task(task: str) -> bool:
        """校验任务描述：非空字符串，长度≥10，且非纯标点"""
        if not task or not isinstance(task, str):
            return False
        if len(task.strip()) < MIN_TASK_LENGTH:
            return False
        # 检查是否纯标点
        if re.fullmatch(r'[\s\W_]+', task):
            return False
        return True

    @staticmethod
    def validate_agents(agents_json: str) -> Tuple[bool, Optional[List[AgentConfig]]]:
        """校验角色配置JSON"""
        try:
            data = json.loads(agents_json)
            if not isinstance(data, list):
                return False, None
            result = []
            for item in data:
                if not isinstance(item, dict):
                    return False, None
                role = item.get("role")
                count = item.get("count", 1)
                if role not in VALID_ROLES:
                    return False, None
                if not isinstance(count, int) or count < 1:
                    return False, None
                result.append(AgentConfig(role, count))
            return True, result
        except json.JSONDecodeError:
            return False, None

    @staticmethod
    def validate_params(params_str: str) -> Tuple[bool, Optional[Dict[str, str]]]:
        """校验参数覆盖格式：key=value 对，空格分隔"""
        if not params_str:
            return True, {}
        result = {}
        for pair in params_str.split():
            if "=" not in pair:
                return False, None
            key, value = pair.split("=", 1)
            if not key or not value:
                return False, None
            result[key] = value
        return True, result

    @staticmethod
    def validate_timeout(timeout: int) -> bool:
        """校验超时时间：正整数且不超过最大值"""
        return isinstance(timeout, int) and 0 < timeout <= MAX_TIMEOUT

    @staticmethod
    def validate_retry(retry: int) -> bool:
        """校验重试次数：非负整数且不超过最大值"""
        return isinstance(retry, int) and 0 <= retry <= MAX_RETRY


# ============================================================
# 环境准备模块
# ============================================================
class EnvironmentManager:
    """环境准备与输出目录管理"""

    @staticmethod
    def prepare_output_dir(output_dir: str) -> bool:
        """创建输出目录及其子目录"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "artifacts").mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    @staticmethod
    def save_output(output_dir: str, stdout: str, stderr: str) -> bool:
        """保存标准输出和错误输出到文件"""
        try:
            with open(os.path.join(output_dir, "stdout.log"), "w", encoding="utf-8") as f:
                f.write(stdout)
            with open(os.path.join(output_dir, "stderr.log"), "w", encoding="utf-8") as f:
                f.write(stderr)
            return True
        except OSError:
            return False


# ============================================================
# Agent执行模块
# ============================================================
class AgentExecutor:
    """模拟Agent执行器"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, retry: int = DEFAULT_RETRY):
        self.timeout = timeout
        self.retry = retry

    def execute_single(self, role: str, task: str, params: Dict[str, str]) -> AgentResult:
        """
        执行单个Agent任务
        在真实环境中，这里会调用LLM或外部服务
        此处使用模拟实现用于演示和测试
        """
        start_time = time.time()
        try:
            # 模拟执行时间
            time.sleep(0.1)
            
            # 模拟输出
            output = (
                f"[{role}] 任务分析完成\n"
                f"任务描述: {task[:50]}...\n"
                f"参数: {json.dumps(params, ensure_ascii=False)}\n"
                f"分析结果: 已完成任务分解，共识别出3个子任务\n"
                f"建议: 按优先级排序执行"
            )
            return AgentResult(role, output, True, time.time() - start_time)
        except Exception as e:
            return AgentResult(role, f"执行失败: {str(e)}", False, time.time() - start_time)

    def execute_with_retry(self, role: str, task: str, params: Dict[str, str]) -> AgentResult:
        """带重试机制的Agent执行"""
        result = None
        for attempt in range(self.retry + 1):
            result = self.execute_single(role, task, params)
            if result.success:
                return result
            if attempt < self.retry:
                time.sleep(0.5)  # 重试等待
        return result

    def execute_all(self, agents: List[AgentConfig], task: str, params: Dict[str, str]) -> List[AgentResult]:
        """执行所有Agent任务"""
        results = []
        for agent in agents:
            for _ in range(agent.count):
                result = self.execute_with_retry(agent.role, task, params)
                results.append(result)
        return results


# ============================================================
# 结果收集与校验模块
# ============================================================
class ResultCollector:
    """结果收集与完整性校验"""

    @staticmethod
    def validate_results(results: List[AgentResult]) -> Tuple[bool, str]:
        """校验结果完整性"""
        if not results:
            return False, "无Agent执行结果"
        
        # 检查是否有致命错误
        for result in results:
            if not result.success:
                return False, f"Agent {result.role} 执行失败"
            
        # 检查输出是否非空
        for result in results:
            if not result.output or len(result.output.strip()) == 0:
                return False, f"Agent {result.role} 输出为空"
        
        return True, "所有检查通过"

    @staticmethod
    def generate_summary(results: List[AgentResult], task: str) -> str:
        """生成任务执行摘要"""
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        roles = list(set(r.role for r in results))
        
        summary = (
            f"任务执行摘要\n"
            f"任务: {task}\n"
            f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"参与Agent: {', '.join(roles)}\n"
            f"成功率: {success_count}/{total_count}\n"
            f"总体状态: {'成功' if success_count == total_count else '部分成功'}"
        )
        return summary

    @staticmethod
    def create_artifacts(results: List[AgentResult], output_dir: str) -> List[Dict[str, Any]]:
        """创建输出文件产物"""
        artifacts = []
        artifacts_dir = os.path.join(output_dir, "artifacts")
        for i, result in enumerate(results):
            filename = f"agent_{i+1}_{result.role}_report.md"
            filepath = os.path.join(artifacts_dir, filename)
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# {result.role} 执行报告\n\n")
                    f.write(f"## 执行时间\n{datetime.now().isoformat()}\n\n")
                    f.write(f"## 执行时长\n{result.duration:.2f}秒\n\n")
                    f.write(f"## 输出内容\n{result.output}\n")
                
                size = os.path.getsize(filepath)
                artifacts.append({
                    "name": filename,
                    "path": filepath,
                    "size": size
                })
            except OSError:
                continue
        return artifacts


# ============================================================
# 主流程控制器
# ============================================================
class AgentFramework:
    """多智能体协作框架主控制器"""

    def __init__(self):
        self.validator = InputValidator()
        self.env_manager = EnvironmentManager()
        self.executor = None
        self.collector = ResultCollector()

    def run(self, args: argparse.Namespace) -> Dict[str, Any]:
        """执行完整流程"""
        try:
            # 步骤1: 收集输入并校验
            if not self.validator.validate_task(args.task):
                return self._error_response(ErrorCode.E001, "任务描述必须是非空字符串，长度≥10且不能是纯标点")

            # 校验超时和重试参数
            if not self.validator.validate_timeout(args.timeout):
                return self._error_response(ErrorCode.E010, f"超时时间必须是1-{MAX_TIMEOUT}之间的正整数")
            if not self.validator.validate_retry(args.retry):
                return self._error_response(ErrorCode.E010, f"重试次数必须是0-{MAX_RETRY}之间的非负整数")

            agents = None
            if args.agents:
                valid, agents = self.validator.validate_agents(args.agents)
                if not valid:
                    return self._error_response(ErrorCode.E002, "角色配置必须是合法JSON数组，且角色名必须在允许列表中")

            params = {}
            if args.params:
                valid, params = self.validator.validate_params(args.params)
                if not valid:
                    return self._error_response(ErrorCode.E004, "参数覆盖必须是key=value对，用空格分隔")

            # 步骤2: 环境准备
            if not self.env_manager.prepare_output_dir(args.output):
                return self._error_response(ErrorCode.E005, f"无法创建输出目录: {args.output}")

            # 步骤3: 执行Agent任务编排
            self.executor = AgentExecutor(timeout=args.timeout, retry=args.retry)
            agent_configs = agents or [AgentConfig(**a) for a in DEFAULT_AGENTS]
            results = self.executor.execute_all(agent_configs, args.task, params)

            # 步骤4: 结果收集与校验
            valid, message = self.collector.validate_results(results)
            if not valid:
                return self._error_response(ErrorCode.E009, f"结果完整性校验失败: {message}")

            # 生成输出
            summary = self.collector.generate_summary(results, args.task)
            artifacts = self.collector.create_artifacts(results, args.output)

            # 保存日志
            stdout_content = "\n".join([f"[{r.role}] {r.output}" for r in results])
            self.env_manager.save_output(args.output, stdout_content, "")

            # 构建响应
            return {
                "status": "success",
                "exit_code": 0,
                "summary": summary,
                "artifacts": artifacts,
                "agent_results": [r.to_dict() for r in results]
            }

        except Exception as e:
            return self._error_response(ErrorCode.E010, f"未预期的错误: {str(e)}")

    @staticmethod
    def _error_response(code: str, message: str) -> Dict[str, Any]:
        """构造错误响应"""
        return {
            "status": "error",
            "exit_code": 1,
            "error_code": code,
            "error_message": message
        }


# ============================================================
# 自测试模块
# ============================================================
class SelfTest:
    """内置自测试用例"""

    @staticmethod
    def run() -> bool:
        """运行自测试，返回是否全部通过"""
        print("=" * 60)
        print("开始自测试...")
        print("=" * 60)
        
        tests_passed = 0
        tests_failed = 0
        
        # 测试1: 任务描述校验
        print("\n[测试1] 任务描述校验")
        validator = InputValidator()
        assert validator.validate_task("这是一个有效的任务描述") == True
        assert validator.validate_task("短") == False
        assert validator.validate_task("！！！") == False
        assert validator.validate_task("") == False
        assert validator.validate_task(None) == False
        assert validator.validate_task(12345) == False
        assert validator.validate_task("   ") == False
        print("  ✓ 通过")
        tests_passed += 1

        # 测试2: 角色配置校验
        print("\n[测试2] 角色配置校验")
        valid, agents = validator.validate_agents('[{"role":"架构师","count":1}]')
        assert valid == True
        assert len(agents) == 1
        assert agents[0].role == "架构师"
        valid, _ = validator.validate_agents('invalid json')
        assert valid == False
        valid, _ = validator.validate_agents('[{"role":"未知角色","count":1}]')
        assert valid == False
        valid, _ = validator.validate_agents('[{"role":"架构师","count":0}]')
        assert valid == False
        valid, _ = validator.validate_agents('[{"role":"架构师","count":"1"}]')
        assert valid == False
        valid, _ = validator.validate_agents('{"role":"架构师","count":1}')
        assert valid == False
        valid, _ = validator.validate_agents('[]')
        assert valid == True
        print("  ✓ 通过")
        tests_passed += 1

        # 测试3: 参数覆盖校验
        print("\n[测试3] 参数覆盖校验")
        valid, params = validator.validate_params("year=2025 quarter=Q1")
        assert valid == True
        assert params == {"year": "2025", "quarter": "Q1"}
        valid, _ = validator.validate_params("invalid")
        assert valid == False
        valid, _ = validator.validate_params("key=")
        assert valid == False
        valid, _ = validator.validate_params("=value")
        assert valid == False
        valid, _ = validator.validate_params("")
        assert valid == True
        assert params == {"year": "2025", "quarter": "Q1"}
        print("  ✓ 通过")
        tests_passed += 1

        # 测试4: Agent执行器
        print("\n[测试4] Agent执行器")
        executor = AgentExecutor(timeout=10, retry=1)
        result = executor.execute_single("研究员", "测试任务描述", {})
        assert result.success == True
        assert result.role == "研究员"
        assert len(result.output) > 0
        print("  ✓ 通过")
        tests_passed += 1

        # 测试5: 结果收集与校验
        print("\n[测试5] 结果收集与校验")
        collector = ResultCollector()
        results = [
            AgentResult("架构师", "输出内容1", True, 0.1),
            AgentResult("研究员", "输出内容2", True, 0.2)
        ]
        valid, _ = collector.validate_results(results)
        assert valid == True
        summary = collector.generate_summary(results, "测试任务")
        assert "测试任务" in summary
        # 测试空结果
        valid, _ = collector.validate_results([])
        assert valid == False
        # 测试失败结果
        valid, _ = collector.validate_results([AgentResult("架构师", "", True, 0.1)])
        assert valid == False
        print("  ✓ 通过")
        tests_passed += 1

        # 测试6: 完整流程（使用临时目录）
        print("\n[测试6] 完整流程")
        with tempfile.TemporaryDirectory() as tmpdir:
            framework = AgentFramework()
            args = argparse.Namespace(
                task="这是一个用于测试的完整任务描述",
                agents=None,
                params="test=value",
                output=os.path.join(tmpdir, "output"),
                timeout=10,
                retry=1
            )
            response = framework.run(args)
            assert response["status"] == "success"
            assert response["exit_code"] == 0
            assert "summary" in response
            assert len(response["artifacts"]) > 0
            print("  ✓ 通过")
            tests_passed += 1

        # 测试7: 错误处理
        print("\n[测试7] 错误处理")
        framework = AgentFramework()
        args = argparse.Namespace(
            task="短",
            agents=None,
            params=None,
            output="./test_output",
            timeout=10,
            retry=1
        )
        response = framework.run(args)
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.E001
        print("  ✓ 通过")
        tests_passed += 1

        # 测试8: 超时和重试参数校验
        print("\n[测试8] 超时和重试参数校验")
        framework = AgentFramework()
        args = argparse.Namespace(
            task="这是一个用于测试的完整任务描述",
            agents=None,
            params=None,
            output="./test_output",
            timeout=0,
            retry=1
        )
        response = framework.run(args)
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.E010
        args.timeout = 10
        args.retry = -1
        response = framework.run(args)
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.E010
        print("  ✓ 通过")
        tests_passed += 1

        # 汇总
        print("\n" + "=" * 60)
        print(f"自测试完成: {tests_passed} 通过, {tests_failed} 失败")
        print("=" * 60)
        return tests_failed == 0


# ============================================================
# 命令行入口
# ============================================================
def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="多智能体协作框架 - 任务拆解、多角色协同、结果归并",
        epilog="示例:\n"
               "  python main.py --task \"分析用户流失原因并提出3条改进建议\"\n"
               "  python main.py --task \"编写登录模块测试\" --agents '[{\"role\":\"测试工程师\",\"count\":2}]'\n"
               "  python main.py --task \"生成销售报告\" --params \"year=2025 quarter=Q1\" --output ./reports"
    )
    parser.add_argument("--task", type=str, help="任务描述（必填，长度≥10字符）")
    parser.add_argument("--agents", type=str, help="角色配置JSON数组")
    parser.add_argument("--params", type=str, help="参数覆盖（key=value对，空格分隔）")
    parser.add_argument("--output", type=str, default="./output", help="输出目录（默认: ./output）")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"单Agent超时秒数（默认: {DEFAULT_TIMEOUT}）")
    parser.add_argument("--retry", type=int, default=DEFAULT_RETRY, help=f"失败重试次数（默认: {DEFAULT_RETRY}）")
    parser.add_argument("--selftest", action="store_true", help="运行自测试并退出")
    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 自测试模式
    if args.selftest:
        success = SelfTest.run()
        sys.exit(0 if success else 1)

    # 检查必要参数
    if not args.task:
        parser.print_help()
        print("\n错误: 缺少 --task 参数")
        sys.exit(1)

    # 执行主流程
    framework = AgentFramework()
    response = framework.run(args)

    # 输出结果
    print(json.dumps(response, ensure_ascii=False, indent=2))
    
    # 设置退出码
    sys.exit(0 if response["exit_code"] == 0 else 1)


if __name__ == "__main__":
    main()
