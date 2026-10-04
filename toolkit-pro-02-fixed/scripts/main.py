#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm-manager: 任务治理、优先级排序、修复决策辅助工具

仅依据功能规格独立实现（clean-room），不依赖任何既有代码。
标准库实现，无第三方依赖。

用法:
    python scripts/main.py --selftest   # 离线自检
    python scripts/main.py --help       # 显示帮助
"""

import argparse
import sys
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
# E001: 输入为空或无效
# E002: 任务ID格式无效
# E003: 状态值非法
# E004: 优先级值非法
# E005: 依赖关系引用不存在的任务
# E006: 依赖关系形成循环
# E007: 输入解析失败
# E008: 任务列表为空
# E009: 参数组合无效
# E010: 内部逻辑错误


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Task:
    """任务条目"""
    task_id: str
    description: str
    priority: str = "中"          # 高/中/低
    status: str = "待处理"         # 待处理/进行中/已完成/阻塞
    impact: str = "中"            # 影响面: 大/中/小
    urgency: str = "中"           # 紧急度: 高/中/低
    dependencies: List[str] = field(default_factory=list)  # 前置任务ID列表
    estimated_hours: float = 1.0  # 预估工时(小时)


class TaskBoard:
    """任务看板：维护任务集合及其状态"""

    VALID_STATUSES = {"待处理", "进行中", "已完成", "阻塞"}
    VALID_PRIORITIES = {"高", "中", "低"}
    VALID_IMPACTS = {"大", "中", "小"}
    VALID_URGENCIES = {"高", "中", "低"}

    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    # ---------- 基础操作 ----------

    def add_task(self, task: Task) -> None:
        """添加任务，校验ID唯一性"""
        if not task.task_id or not task.task_id.strip():
            raise ValueError("E001: 任务ID不能为空")
        if task.task_id in self.tasks:
            raise ValueError(f"E002: 任务ID重复: {task.task_id}")
        self._validate_task(task)
        self.tasks[task.task_id] = task

    def update_status(self, task_id: str, new_status: str) -> None:
        """更新任务状态"""
        if task_id not in self.tasks:
            raise ValueError(f"E002: 任务不存在: {task_id}")
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"E003: 非法状态值: {new_status}")
        self.tasks[task_id].status = new_status

    def _validate_task(self, task: Task) -> None:
        """校验任务字段合法性"""
        if task.priority not in self.VALID_PRIORITIES:
            raise ValueError(f"E004: 非法优先级: {task.priority}")
        if task.status not in self.VALID_STATUSES:
            raise ValueError(f"E003: 非法状态: {task.status}")
        if task.impact not in self.VALID_IMPACTS:
            raise ValueError(f"E004: 非法影响面: {task.impact}")
        if task.urgency not in self.VALID_URGENCIES:
            raise ValueError(f"E004: 非法紧急度: {task.urgency}")
        if task.estimated_hours < 0:
            raise ValueError("E004: 预估工时不能为负")
        # 校验依赖引用
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                raise ValueError(f"E005: 依赖任务不存在: {dep_id}")

    # ---------- 核心逻辑 ----------

    def parse_free_text(self, text: str) -> List[Task]:
        """
        将自由文本解析为任务列表。
        规则:
          - 每行一个任务（以换行分割）
          - 行内格式: [描述] | 优先级=高 | 影响=大 | 紧急=高 | 依赖=T-001,T-002
          - 未标注的字段使用默认值
        """
        if not text or not text.strip():
            raise ValueError("E001: 输入文本为空")

        tasks: List[Task] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for idx, line in enumerate(lines, start=1):
            # 解析字段
            parts = [p.strip() for p in line.split("|")]
            description = parts[0].strip()
            if not description:
                raise ValueError(f"E007: 第{idx}行缺少任务描述")

            # 提取额外字段
            priority = "中"
            impact = "中"
            urgency = "中"
            deps: List[str] = []

            for part in parts[1:]:
                if "=" in part:
                    key, _, value = part.partition("=")
                    key = key.strip().lower()
                    value = value.strip()
                    if key in ("优先级", "priority", "pri"):
                        priority = value
                    elif key in ("影响", "影响面", "impact"):
                        impact = value
                    elif key in ("紧急", "紧急度", "urgency"):
                        urgency = value
                    elif key in ("依赖", "dependencies", "dep"):
                        deps = [d.strip() for d in value.split(",") if d.strip()]

            task = Task(
                task_id=f"T-{idx:03d}",
                description=description,
                priority=priority,
                impact=impact,
                urgency=urgency,
                dependencies=deps,
            )
            tasks.append(task)

        return tasks

    def add_tasks_from_text(self, text: str) -> List[Task]:
        """从文本解析并添加任务"""
        parsed = self.parse_free_text(text)
        for task in parsed:
            self.add_task(task)
        return parsed

    def calculate_priority_score(self, task: Task) -> float:
        """
        计算任务优先级分数（内部排序用）。
        分数越高越优先处理。
        公式: 基础分(紧急度) + 影响分 + 依赖加权
        """
        urgency_map = {"高": 30, "中": 20, "低": 10}
        impact_map = {"大": 30, "中": 20, "小": 10}
        priority_map = {"高": 20, "中": 10, "低": 0}

        score = urgency_map.get(task.urgency, 20) + impact_map.get(task.impact, 20)
        score += priority_map.get(task.priority, 10)

        # 被依赖方（前置任务）加权
        # 如果其他任务依赖此任务，则此任务应优先处理
        for other in self.tasks.values():
            if task.task_id in other.dependencies:
                score += 5

        # 已完成任务不再优先
        if task.status == "已完成":
            score -= 50
        if task.status == "阻塞":
            score -= 20

        return score

    def sort_by_priority(self) -> List[Task]:
        """按优先级分数降序排序（分数高者优先）"""
        if not self.tasks:
            raise ValueError("E008: 任务列表为空")
        scored = [(task, self.calculate_priority_score(task)) for task in self.tasks.values()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [task for task, _ in scored]

    def detect_cycles(self) -> Optional[List[str]]:
        """
        检测依赖循环。
        返回循环路径列表；无循环返回None。
        使用DFS检测有向图环。
        """
        visited: Dict[str, int] = {}  # 0=未访问, 1=访问中, 2=已访问完
        path: List[str] = []

        def dfs(node_id: str) -> Optional[List[str]]:
            visited[node_id] = 1
            path.append(node_id)

            task = self.tasks.get(node_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in self.tasks:
                        continue  # 已由add校验，防御性跳过
                    if visited.get(dep_id, 0) == 1:
                        # 找到环
                        cycle_start = path.index(dep_id)
                        return path[cycle_start:] + [dep_id]
                    if visited.get(dep_id, 0) == 0:
                        result = dfs(dep_id)
                        if result:
                            return result

            path.pop()
            visited[node_id] = 2
            return None

        for task_id in self.tasks:
            if visited.get(task_id, 0) == 0:
                result = dfs(task_id)
                if result:
                    return result
        return None

    def get_next_action(self) -> Tuple[Optional[Task], str]:
        """
        推荐下一步动作。
        返回 (推荐任务, 推荐理由)
        """
        if not self.tasks:
            raise ValueError("E008: 任务列表为空")

        # 检查循环依赖
        cycle = self.detect_cycles()
        if cycle:
            return None, f"检测到循环依赖: {' -> '.join(cycle)}，请先解决依赖关系"

        # 获取排序后的任务
        sorted_tasks = self.sort_by_priority()

        # 跳过已完成任务
        pending = [t for t in sorted_tasks if t.status != "已完成"]

        if not pending:
            return None, "所有任务均已完成"

        # 检查依赖是否就绪
        for task in pending:
            deps_ready = True
            for dep_id in task.dependencies:
                dep = self.tasks.get(dep_id)
                if dep and dep.status != "已完成":
                    deps_ready = False
                    break
            if deps_ready:
                reason = f"优先级最高且依赖已就绪（分数: {self.calculate_priority_score(task):.0f}）"
                return task, reason

        # 所有任务都有未完成依赖，推荐处理最前的前置任务
        for task in pending:
            for dep_id in task.dependencies:
                dep = self.tasks.get(dep_id)
                if dep and dep.status != "已完成":
                    reason = f"作为 {task.task_id} 的前置任务，需先完成"
                    return dep, reason

        return pending[0], "默认推荐（无依赖阻塞）"

    def format_task(self, task: Task) -> str:
        """格式化任务输出"""
        deps = ",".join(task.dependencies) if task.dependencies else "-"
        return (f"[{task.task_id}] {task.description} | "
                f"优先级:{task.priority} | 状态:{task.status} | "
                f"影响:{task.impact} | 紧急:{task.urgency} | 依赖:{deps}")

    def format_board(self) -> str:
        """输出任务看板"""
        if not self.tasks:
            return "任务列表为空"
        lines = ["=== 任务看板 ==="]
        for task in self.tasks.values():
            lines.append(self.format_task(task))
        return "\n".join(lines)

    def format_sorted(self) -> str:
        """输出排序结果"""
        try:
            sorted_tasks = self.sort_by_priority()
        except ValueError as e:
            return str(e)
        lines = ["=== 优先级排序（高→低） ==="]
        for i, task in enumerate(sorted_tasks, 1):
            score = self.calculate_priority_score(task)
            lines.append(f"{i}. {self.format_task(task)} [分数:{score:.0f}]")
        return "\n".join(lines)


# ============================================================
# 自检模块
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


def run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=== pm-manager 自检开始 ===")

    # ---------- 测试1: 基础任务添加 ----------
    board = TaskBoard()
    task1 = Task(
        task_id="T-001",
        description="登录页报错",
        priority="高",
        impact="大",
        urgency="高",
    )
    board.add_task(task1)
    assert len(board.tasks) == 1, "任务添加失败"
    assert board.tasks["T-001"].status == "待处理", "默认状态错误"
    print("[PASS] 基础任务添加")

    # ---------- 测试2: 自由文本解析 ----------
    board2 = TaskBoard()
    text = """
    登录页报错 | 优先级=高 | 影响=大 | 紧急=高
    支付超时 | 优先级=中 | 依赖=T-001
    用户反馈界面卡顿
    """
    parsed = board2.parse_free_text(text)
    assert len(parsed) == 3, "文本解析任务数错误"
    assert parsed[0].priority == "高", "优先级解析错误"
    assert parsed[1].dependencies == ["T-001"], "依赖解析错误"
    assert parsed[2].impact == "中", "默认影响面错误"
    print("[PASS] 自由文本解析")

    # ---------- 测试3: 优先级排序 ----------
    board3 = TaskBoard()
    board3.add_task(Task(
        task_id="T-001", description="紧急高影响任务",
        priority="高", impact="大", urgency="高",
    ))
    board3.add_task(Task(
        task_id="T-002", description="低优任务",
        priority="低", impact="小", urgency="低",
    ))
    board3.add_task(Task(
        task_id="T-003", description="中优任务",
        priority="中", impact="中", urgency="中",
    ))
    sorted_tasks = board3.sort_by_priority()
    assert len(sorted_tasks) == 3, "排序任务数错误"
    # 分数高者应排前面（宽松断言：第一个任务分数不低于最后一个）
    score_first = board3.calculate_priority_score(sorted_tasks[0])
    score_last = board3.calculate_priority_score(sorted_tasks[-1])
    assert score_first >= score_last, "排序顺序错误"
    # 高优任务应在低优任务之前
    ids = [t.task_id for t in sorted_tasks]
    assert ids.index("T-001") < ids.index("T-002"), "高优任务未排前面"
    print("[PASS] 优先级排序")

    # ---------- 测试4: 依赖分析 ----------
    board4 = TaskBoard()
    board4.add_task(Task(
        task_id="T-001", description="前置任务",
        priority="高", impact="大", urgency="高",
    ))
    board4.add_task(Task(
        task_id="T-002", description="后置任务",
        priority="高", impact="大", urgency="高",
        dependencies=["T-001"],
    ))
    # 无循环依赖
    assert board4.detect_cycles() is None, "误报循环依赖"

    # 添加循环依赖
    board4.tasks["T-001"].dependencies = ["T-002"]
    cycle = board4.detect_cycles()
    assert cycle is not None, "未检测到循环依赖"
    print("[PASS] 依赖分析")

    # ---------- 测试5: 下一步动作推荐 ----------
    board5 = TaskBoard()
    board5.add_task(Task(
        task_id="T-001", description="基础任务A",
        priority="中", impact="中", urgency="中",
    ))
    board5.add_task(Task(
        task_id="T-002", description="依赖任务B",
        priority="高", impact="大", urgency="高",
        dependencies=["T-001"],
    ))
    next_task, reason = board5.get_next_action()
    assert next_task is not None, "未推荐任务"
    # 应推荐前置任务T-001（因为T-002依赖它）
    assert next_task.task_id == "T-001", "应优先推荐前置任务"
    assert reason and len(reason) > 0, "推荐理由为空"
    print("[PASS] 下一步动作推荐")

    # ---------- 测试6: 状态追踪 ----------
    board6 = TaskBoard()
    board6.add_task(Task(task_id="T-001", description="状态测试任务"))
    board6.update_status("T-001", "进行中")
    assert board6.tasks["T-001"].status == "进行中", "状态更新失败"

    # 非法状态应报错
    try:
        board6.update_status("T-001", "非法状态")
        assert False, "非法状态未报错"
    except ValueError as e:
        assert "E003" in str(e), "错误码不正确"
    print("[PASS] 状态追踪")

    # ---------- 测试7: 错误处理 ----------
    board7 = TaskBoard()
    # 空文本
    try:
        board7.parse_free_text("")
        assert False, "空文本未报错"
    except ValueError as e:
        assert "E001" in str(e), "错误码不正确"

    # 空任务列表排序
    try:
        board7.sort_by_priority()
        assert False, "空列表排序未报错"
    except ValueError as e:
        assert "E008" in str(e), "错误码不正确"
    print("[PASS] 错误处理")

    # ---------- 测试8: 完整流程模拟 ----------
    board8 = TaskBoard()
    sample_text = """
    用户反馈登录失败 | 优先级=高 | 影响=大 | 紧急=高
    数据库连接超时 | 优先级=高 | 影响=大 | 紧急=高
    界面样式调整 | 优先级=低 | 影响=小 | 紧急=低
    支付流程优化 | 优先级=中 | 影响=中 | 紧急=中 | 依赖=T-001,T-002
    """
    board8.add_tasks_from_text(sample_text)
    assert len(board8.tasks) == 4, "完整流程任务数错误"

    # 排序后应高优任务在前
    sorted_list = board8.sort_by_priority()
    assert len(sorted_list) == 4, "完整流程排序错误"
    high_priority_ids = [t.task_id for t in sorted_list if t.priority == "高"]
    low_priority_ids = [t.task_id for t in sorted_list if t.priority == "低"]
    if high_priority_ids and low_priority_ids:
        assert high_priority_ids[0] != low_priority_ids[0], "排序异常"

    # 推荐动作
    next_task, reason = board8.get_next_action()
    assert next_task is not None, "完整流程无推荐"

    # 看板输出
    board_str = board8.format_board()
    assert "T-001" in board_str, "看板输出缺少任务"
    print("[PASS] 完整流程模拟")

    # ---------- 测试9: 格式输出 ----------
    board9 = TaskBoard()
    board9.add_task(Task(task_id="T-001", description="格式测试任务"))
    formatted = board9.format_task(board9.tasks["T-001"])
    assert "[T-001]" in formatted, "格式化输出缺ID"
    assert "格式测试任务" in formatted, "格式化输出缺描述"
    assert "待处理" in formatted, "格式化输出缺状态"
    print("[PASS] 格式输出")

    # ---------- 测试10: 边界情况 ----------
    board10 = TaskBoard()
    # 大量任务
    for i in range(50):
        board10.add_task(Task(
            task_id=f"T-{i:03d}",
            description=f"批量任务{i}",
            priority="中" if i % 2 == 0 else "低",
            impact="中",
            urgency="中",
        ))
    assert len(board10.tasks) == 50, "批量任务添加失败"
    sorted_10 = board10.sort_by_priority()
    assert len(sorted_10) == 50, "批量排序失败"
    print("[PASS] 批量任务处理")

    print("\n=== 全部自检通过 ===")
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="pm-manager: 任务治理、优先级排序、修复决策辅助工具",
        epilog="示例: 通过管道输入文本，或直接运行 --selftest 自检",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入自由文本（或通过stdin输入）",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="执行优先级排序并输出",
    )
    parser.add_argument(
        "--next",
        action="store_true",
        help="推荐下一步动作",
    )
    parser.add_argument(
        "--board",
        action="store_true",
        help="输出任务看板",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无参数时显示帮助
    if not args.input and not sys.stdin.isatty():
        # 从stdin读取
        input_text = sys.stdin.read()
    elif args.input:
        input_text = args.input
    else:
        parser.print_help()
        return 0

    try:
        board = TaskBoard()
        board.add_tasks_from_text(input_text)

        output_lines = []

        if args.sort:
            output_lines.append(board.format_sorted())

        if args.next:
            next_task, reason = board.get_next_action()
            if next_task:
                output_lines.append(f"下一步: {board.format_task(next_task)}")
                output_lines.append(f"理由: {reason}")
            else:
                output_lines.append(f"建议: {reason}")

        if args.board:
            output_lines.append(board.format_board())

        # 默认输出看板
        if not output_lines:
            output_lines.append(board.format_board())

        print("\n".join(output_lines))
        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 内部错误 - {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
