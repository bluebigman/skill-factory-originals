#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体协作调度中枢 (Agent Orchestration Coordinator)

独立实现脚本：解析任务描述、拆解子任务、生成编排方案（DAG）、跟踪状态、汇总结果。
仅依赖标准库，支持 --selftest 离线自检。

用法示例:
    python scripts/main.py --task "写一份市场分析报告" --agents 3 --verbose
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
import traceback
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入参数类型错误",
    "E003": "子任务数量超出限制 (1-20)",
    "E004": "任务描述解析失败",
    "E005": "Agent 角色分配失败",
    "E006": "DAG 构建失败（存在环或孤立节点）",
    "E007": "状态更新失败（非法状态转换）",
    "E008": "结果汇总校验失败",
    "E009": "输出格式化失败",
    "E010": "未知内部错误",
}


class OrchestrationError(Exception):
    """业务逻辑异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# 输入校验层
# ---------------------------------------------------------------------------
def validate_task_description(task_text: Any) -> str:
    """校验任务描述：必须是非空字符串，长度上限 5000 字符。

    Args:
        task_text: 用户输入的任务描述。

    Returns:
        清洗后的任务描述字符串。

    Raises:
        OrchestrationError: E001（空输入）或 E002（类型错误）。
    """
    if task_text is None:
        raise OrchestrationError("E001", "任务描述不能为空")
    if not isinstance(task_text, str):
        # 尝试转为字符串，但二进制内容视为无效
        if isinstance(task_text, (bytes, bytearray)):
            raise OrchestrationError("E002", "任务描述必须是文本字符串，不接受二进制数据")
        task_text = str(task_text)
    task_text = task_text.strip()
    if not task_text:
        raise OrchestrationError("E001", "任务描述不能是空白字符")
    if len(task_text) > 5000:
        # 超长输入不拒绝，但截断并警告（符合 R5 性能要求，不限制输入量）
        print(f"[警告] 任务描述超过 5000 字符，已截断至 5000 字符进行处理", file=sys.stderr)
        task_text = task_text[:5000]
    return task_text


def validate_agent_count(agent_count: Any) -> int:
    """校验 Agent 数量：必须是 1-20 之间的整数。

    Args:
        agent_count: 用户指定的 Agent 数量。

    Returns:
        合法的 Agent 数量。

    Raises:
        OrchestrationError: E002（类型错误）或 E003（超出范围）。
    """
    if agent_count is None:
        return 3  # 默认值
    if isinstance(agent_count, bool) or not isinstance(agent_count, int):
        raise OrchestrationError("E002", "Agent 数量必须是整数")
    if agent_count < 1 or agent_count > 20:
        raise OrchestrationError("E003", "Agent 数量必须在 1-20 之间")
    return agent_count


# ---------------------------------------------------------------------------
# 核心逻辑层：任务拆解与编排
# ---------------------------------------------------------------------------
# 中文标点符号集合，用于任务拆分的边界识别
_CHINESE_PUNCTUATION = set("，。！？；：、,.!?;:")

# Agent 角色池
AGENT_ROLES = ["分析型", "生成型", "审查型", "数据提取型", "汇总型"]


def split_task_into_subtasks(task_text: str, max_subtasks: int) -> List[str]:
    """将任务描述拆分为子任务列表。

    以中文/英文标点符号为边界进行滑窗切分，保证每个子任务语义相对完整。
    采用流式处理，时间复杂度 O(n)。

    Args:
        task_text: 已校验的任务描述。
        max_subtasks: 最大子任务数（由 Agent 数量决定）。

    Returns:
        子任务字符串列表，长度不超过 max_subtasks。
    """
    if not task_text:
        return []

    # 第一遍：按标点切分为句子片段
    sentences: List[str] = []
    current = []
    for ch in task_text:
        current.append(ch)
        if ch in _CHINESE_PUNCTUATION:
            sentence = "".join(current).strip()
            if sentence:
                sentences.append(sentence)
            current = []
    # 处理末尾无标点的剩余部分
    if current:
        tail = "".join(current).strip()
        if tail:
            sentences.append(tail)

    # 如果句子数量超过限制，则按长度均匀合并（保持 O(n)）
    if len(sentences) <= max_subtasks:
        return [s for s in sentences if s]

    # 需要合并句子：计算每个桶的目标大小
    total_len = sum(len(s) for s in sentences)
    bucket_size = max(1, total_len // max_subtasks)
    buckets: List[str] = []
    current_bucket = []
    current_len = 0
    for s in sentences:
        current_bucket.append(s)
        current_len += len(s)
        if current_len >= bucket_size and len(buckets) < max_subtasks - 1:
            buckets.append("".join(current_bucket))
            current_bucket = []
            current_len = 0
    if current_bucket:
        buckets.append("".join(current_bucket))

    return buckets


def assign_agent_roles(subtasks: List[str], agent_count: int) -> List[Dict[str, str]]:
    """为每个子任务分配 Agent 角色。

    采用轮询方式分配角色，保证负载均衡。

    Args:
        subtasks: 子任务列表。
        agent_count: Agent 数量（决定角色池大小）。

    Returns:
        包含子任务和角色的字典列表。
    """
    if not subtasks:
        return []
    if agent_count <= 0:
        raise OrchestrationError("E005", "Agent 数量必须大于 0")

    # 根据 Agent 数量裁剪角色池
    roles = AGENT_ROLES[:agent_count] if agent_count <= len(AGENT_ROLES) else AGENT_ROLES
    if len(roles) < agent_count:
        # 角色不足时循环补充
        while len(roles) < agent_count:
            roles.append(AGENT_ROLES[len(roles) % len(AGENT_ROLES)])

    assignments = []
    for i, subtask in enumerate(subtasks):
        role = roles[i % len(roles)]
        assignments.append({
            "subtask_id": f"T{i+1:02d}",
            "description": subtask,
            "agent_role": role,
            "status": "待执行",
            "dependencies": [],
        })
    return assignments


def build_dag(assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """构建 DAG 结构，确定执行顺序。

    简化策略：相邻子任务之间建立依赖关系（串行链），
    同时允许并行分支（每 3 个任务一组，组内并行，组间串行）。

    Args:
        assignments: 子任务分配列表。

    Returns:
        带依赖关系的任务列表（DAG 节点）。
    """
    if not assignments:
        return []

    n = len(assignments)
    # 组大小：每 3 个任务一组，组内并行
    group_size = 3
    for i, task in enumerate(assignments):
        group_idx = i // group_size
        prev_group_end = group_idx * group_size - 1
        if prev_group_end >= 0:
            # 依赖上一组的所有任务
            task["dependencies"] = [f"T{j+1:02d}" for j in range(max(0, prev_group_end - group_size + 1), prev_group_end + 1)]
        else:
            task["dependencies"] = []
    return assignments


def update_task_status(assignments: List[Dict[str, Any]], task_id: str, new_status: str) -> List[Dict[str, Any]]:
    """更新指定任务的状态（带合法性校验）。

    Args:
        assignments: 任务列表。
        task_id: 任务 ID（如 "T01"）。
        new_status: 新状态（待执行/执行中/已完成/失败）。

    Returns:
        更新后的任务列表。

    Raises:
        OrchestrationError: E007（非法状态转换或任务不存在）。
    """
    valid_statuses = {"待执行", "执行中", "已完成", "失败"}
    if new_status not in valid_statuses:
        raise OrchestrationError("E007", f"非法状态: {new_status}")

    for task in assignments:
        if task["subtask_id"] == task_id:
            old_status = task["status"]
            # 简单状态机校验：待执行 -> 执行中 -> 已完成/失败
            if old_status == "待执行" and new_status not in ("执行中", "失败"):
                raise OrchestrationError("E007", f"非法状态转换: {old_status} -> {new_status}")
            if old_status == "执行中" and new_status not in ("已完成", "失败"):
                raise OrchestrationError("E007", f"非法状态转换: {old_status} -> {new_status}")
            if old_status in ("已完成", "失败"):
                raise OrchestrationError("E007", f"任务已终止，不能转换: {old_status} -> {new_status}")
            task["status"] = new_status
            return assignments

    raise OrchestrationError("E007", f"任务不存在: {task_id}")


def summarize_results(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """汇总各 Agent 执行结果，进行一致性校验。

    Args:
        assignments: 任务列表。

    Returns:
        汇总报告字典。
    """
    if not assignments:
        return {"total": 0, "completed": 0, "failed": 0, "pending": 0, "status": "空任务列表"}

    total = len(assignments)
    completed = sum(1 for t in assignments if t["status"] == "已完成")
    failed = sum(1 for t in assignments if t["status"] == "失败")
    pending = total - completed - failed

    # 一致性校验：检查是否有任务缺少必要字段
    issues = []
    for t in assignments:
        if not t.get("description"):
            issues.append(f"{t['subtask_id']}: 缺少描述")
        if not t.get("agent_role"):
            issues.append(f"{t['subtask_id']}: 缺少角色")
        if t["status"] == "已完成" and not t.get("output"):
            issues.append(f"{t['subtask_id']}: 已完成但无输出")

    summary = {
        "total": total,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "status": "全部完成" if pending == 0 and failed == 0 else "进行中",
        "issues": issues,
    }
    return summary


# ---------------------------------------------------------------------------
# 输出格式化层
# ---------------------------------------------------------------------------
def format_plan_output(assignments: List[Dict[str, Any]], verbose: bool = False) -> str:
    """将编排方案格式化为可读文本。

    Args:
        assignments: 任务列表。
        verbose: 是否输出详细决策信息。

    Returns:
        格式化后的文本。
    """
    if not assignments:
        return "（空编排方案）"

    lines = ["=== 多智能体协作编排方案 ==="]
    lines.append(f"子任务总数: {len(assignments)}")
    lines.append("")

    for task in assignments:
        dep_str = ", ".join(task["dependencies"]) if task["dependencies"] else "无"
        lines.append(f"  {task['subtask_id']} [{task['agent_role']}] {task['status']}")
        lines.append(f"    任务内容: {task['description'][:80]}{'...' if len(task['description']) > 80 else ''}")
        lines.append(f"    依赖: {dep_str}")
        if verbose and task.get("output"):
            lines.append(f"    输出: {task['output'][:100]}")
        lines.append("")

    return "\n".join(lines)


def format_summary_output(summary: Dict[str, Any]) -> str:
    """格式化汇总报告。

    Args:
        summary: 汇总字典。

    Returns:
        格式化后的文本。
    """
    lines = ["=== 执行汇总 ==="]
    lines.append(f"总任务数: {summary.get('total', 0)}")
    lines.append(f"已完成: {summary.get('completed', 0)}")
    lines.append(f"失败: {summary.get('failed', 0)}")
    lines.append(f"待执行: {summary.get('pending', 0)}")
    lines.append(f"整体状态: {summary.get('status', '未知')}")
    if summary.get("issues"):
        lines.append("校验问题:")
        for issue in summary["issues"]:
            lines.append(f"  - {issue}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def run_orchestration(task_text: str, agent_count: int, verbose: bool = False) -> Tuple[int, str]:
    """执行完整编排流程。

    Args:
        task_text: 任务描述。
        agent_count: Agent 数量。
        verbose: 是否输出详细决策。

    Returns:
        (退出码, 输出文本)。
    """
    try:
        # 1. 输入校验
        clean_task = validate_task_description(task_text)
        clean_agents = validate_agent_count(agent_count)

        # 2. 任务拆解
        subtasks = split_task_into_subtasks(clean_task, clean_agents)
        if not subtasks:
            raise OrchestrationError("E004", "任务描述无法拆解为子任务")

        # 3. 角色分配
        assignments = assign_agent_roles(subtasks, clean_agents)

        # 4. 构建 DAG
        assignments = build_dag(assignments)

        # 5. 模拟执行（演示状态流转）
        for task in assignments:
            update_task_status(assignments, task["subtask_id"], "执行中")
            # 模拟执行结果
            task["output"] = f"[模拟输出] {task['description'][:30]} 的分析结果"
            update_task_status(assignments, task["subtask_id"], "已完成")

        # 6. 汇总
        summary = summarize_results(assignments)

        # 7. 输出
        output_parts = []
        output_parts.append(format_plan_output(assignments, verbose))
        output_parts.append("")
        output_parts.append(format_summary_output(summary))

        if verbose:
            output_parts.append("")
            output_parts.append("=== 决策明细 ===")
            output_parts.append(f"输入任务: {clean_task[:100]}")
            output_parts.append(f"拆分为 {len(subtasks)} 个子任务")
            for i, s in enumerate(subtasks):
                output_parts.append(f"  T{i+1:02d}: {s[:60]}...")
            output_parts.append(f"角色分配策略: 轮询分配 {clean_agents} 个角色")

        return 0, "\n".join(output_parts)

    except OrchestrationError as e:
        return 1, f"错误: {e.message} (错误码: {e.code})"
    except Exception as e:
        # 未知异常：完整上报（R10 失败要响亮）
        print(f"[严重错误] 未知异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1, f"错误: 发生未知异常: {e} (错误码: E010)"


# ---------------------------------------------------------------------------
# 自检模块 (--selftest)
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """离线自检核心逻辑，使用内置硬编码样例数据。

    Returns:
        退出码（0 表示全部通过）。
    """
    print("=== 自检开始 ===")
    failures = 0

    # 测试用例 1: 正常中文任务
    try:
        task1 = "分析市场趋势，撰写报告，并给出建议。"
        assignments1 = assign_agent_roles(split_task_into_subtasks(task1, 3), 3)
        assert len(assignments1) >= 1, "正常任务应至少拆出 1 个子任务"
        assert all(t["agent_role"] for t in assignments1), "每个子任务必须有角色"
        print("[PASS] 正常中文任务拆解与角色分配")
    except AssertionError as e:
        print(f"[FAIL] 正常中文任务: {e}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 正常中文任务异常: {e}")
        failures += 1

    # 测试用例 2: 空输入
    try:
        try:
            validate_task_description("")
            print("[FAIL] 空输入应抛出 E001")
            failures += 1
        except OrchestrationError as e:
            assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
            print("[PASS] 空输入正确拒绝")
    except Exception as e:
        print(f"[FAIL] 空输入测试异常: {e}")
        failures += 1

    # 测试用例 3: 中文标点边界
    try:
        task3 = "第一项任务。第二项任务！第三项任务？"
        subtasks3 = split_task_into_subtasks(task3, 5)
        assert len(subtasks3) >= 3, f"应拆出至少 3 个子任务，实际 {len(subtasks3)}"
        print(f"[PASS] 中文标点切分（{len(subtasks3)} 个子任务）")
    except AssertionError as e:
        print(f"[FAIL] 中文标点切分: {e}")
        failures += 1

    # 测试用例 4: 超长输入（性能 O(n) 验证）
    try:
        long_task = "任务。" * 10000  # 5 万字符
        import time
        start = time.time()
        subtasks4 = split_task_into_subtasks(long_task, 5)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"超长输入处理时间过长: {elapsed:.2f}s"
        assert len(subtasks4) <= 5, f"子任务数应不超过 5，实际 {len(subtasks4)}"
        print(f"[PASS] 超长输入处理（{len(long_task)} 字符, {elapsed:.3f}s）")
    except AssertionError as e:
        print(f"[FAIL] 超长输入: {e}")
        failures += 1

    # 测试用例 5: 状态流转
    try:
        assignments5 = assign_agent_roles(["测试任务"], 1)
        update_task_status(assignments5, "T01", "执行中")
        update_task_status(assignments5, "T01", "已完成")
        assert assignments5[0]["status"] == "已完成", "状态应为已完成"
        try:
            update_task_status(assignments5, "T01", "失败")
            print("[FAIL] 已完成任务不应允许再次转换")
            failures += 1
        except OrchestrationError:
            print("[PASS] 非法状态转换正确拒绝")
    except Exception as e:
        print(f"[FAIL] 状态流转测试异常: {e}")
        failures += 1

    # 测试用例 6: 汇总逻辑
    try:
        assignments6 = assign_agent_roles(["任务A", "任务B"], 2)
        for t in assignments6:
            t["status"] = "已完成"
            t["output"] = "测试输出"
        summary6 = summarize_results(assignments6)
        assert summary6["completed"] == 2, "应统计到 2 个已完成"
        assert summary6["status"] == "全部完成", "状态应为全部完成"
        print("[PASS] 汇总逻辑正确")
    except AssertionError as e:
        print(f"[FAIL] 汇总逻辑: {e}")
        failures += 1

    # 测试用例 7: DAG 构建
    try:
        assignments7 = assign_agent_roles(["任务1", "任务2", "任务3", "任务4"], 2)
        dag7 = build_dag(assignments7)
        assert len(dag7) == 4, "DAG 应包含 4 个节点"
        assert dag7[0]["dependencies"] == [], "第一个任务不应有依赖"
        assert len(dag7[3]["dependencies"]) >= 1, "第四个任务应有依赖"
        print("[PASS] DAG 构建正确")
    except AssertionError as e:
        print(f"[FAIL] DAG 构建: {e}")
        failures += 1

    # 测试用例 8: 完整流程
    try:
        code, output = run_orchestration("完成市场调研，分析竞品，输出报告。", 3, verbose=False)
        assert code == 0, f"完整流程应成功，退出码 {code}"
        assert "编排方案" in output, "输出应包含编排方案"
        assert "执行汇总" in output, "输出应包含汇总"
        print("[PASS] 完整编排流程")
    except AssertionError as e:
        print(f"[FAIL] 完整流程: {e}")
        failures += 1

    # 测试用例 9: 编码容错（GBK 编码输入）
    try:
        gbk_bytes = "中文任务测试".encode("gbk")
        # 模拟读取 GBK 文件
        decoded = gbk_bytes.decode("gbk")
        subtasks9 = split_task_into_subtasks(decoded, 3)
        assert len(subtasks9) >= 1, "GBK 解码后应能正常拆解"
        print("[PASS] GBK 编码兼容")
    except Exception as e:
        print(f"[FAIL] GBK 编码: {e}")
        failures += 1

    print(f"\n=== 自检结束: {'全部通过' if failures == 0 else f'{failures} 项失败'} ===")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main() -> int:
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="多智能体协作调度中枢 - 任务编排与协调",
        epilog="示例: python scripts/main.py --task '写一份报告' --agents 3 --verbose"
    )
    parser.add_argument("--task", type=str, help="任务描述（自然语言或结构化文本）")
    parser.add_argument("--agents", type=int, default=3, help="Agent 数量 (1-20，默认 3)")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不执行（本脚本无落盘操作，保留参数以兼容）")
    parser.add_argument("--force", action="store_true", help="强制执行（本脚本无落盘操作，保留参数以兼容）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式
    if not args.task:
        print("错误: 必须提供 --task 参数 (错误码: E001)", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检，或 --help 查看帮助", file=sys.stderr)
        return 1

    # 执行编排
    code, output = run_orchestration(args.task, args.agents, args.verbose)
    print(output)
    return code


if __name__ == "__main__":
    sys.exit(main())
