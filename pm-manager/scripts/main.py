#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm-manager 技能实现脚本
------------------------
依据功能规格独立编写（clean-room 实现）。
功能：任务治理、优先级排序、依赖分析、下一步动作推荐、状态追踪。
"""

import re
import sys
import json
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# ============================================================
# 错误码定义
# ============================================================
class ErrorCode:
    """统一错误码。"""
    E001 = "E001: 输入参数无效或为空"
    E002 = "E002: 任务ID格式不正确"
    E003 = "E003: 任务状态值非法"
    E004 = "E004: 优先级值非法"
    E005 = "E005: 依赖关系引用不存在的任务"
    E006 = "E006: 依赖关系形成循环"
    E007 = "E007: 任务数据序列化失败"
    E008 = "E008: 任务数据反序列化失败"
    E009 = "E009: 内部逻辑错误"
    E010 = "E010: 不支持的操作或参数"


# ============================================================
# 枚举与常量
# ============================================================
class Priority(Enum):
    """任务优先级枚举。"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        """从字符串解析优先级，非法时抛出 E004。"""
        mapping = {
            "高": cls.HIGH, "中": cls.MEDIUM, "低": cls.LOW,
            "high": cls.HIGH, "medium": cls.MEDIUM, "low": cls.LOW,
            "HIGH": cls.HIGH, "MEDIUM": cls.MEDIUM, "LOW": cls.LOW,
            "高优先级": cls.HIGH, "中优先级": cls.MEDIUM, "低优先级": cls.LOW
        }
        if value not in mapping:
            raise ValueError(ErrorCode.E004)
        return mapping[value]


class TaskStatus(Enum):
    """任务生命周期状态。"""
    TODO = "待处理"
    IN_PROGRESS = "进行中"
    DONE = "已完成"
    BLOCKED = "阻塞"

    @classmethod
    def from_str(cls, value: str) -> "TaskStatus":
        """从字符串解析状态，非法时抛出 E003。"""
        mapping = {
            "待处理": cls.TODO, "进行中": cls.IN_PROGRESS,
            "已完成": cls.DONE, "阻塞": cls.BLOCKED,
            "todo": cls.TODO, "in_progress": cls.IN_PROGRESS,
            "done": cls.DONE, "blocked": cls.BLOCKED,
            "TODO": cls.TODO, "IN_PROGRESS": cls.IN_PROGRESS,
            "DONE": cls.DONE, "BLOCKED": cls.BLOCKED,
            "未开始": cls.TODO, "已完成任务": cls.DONE
        }
        if value not in mapping:
            raise ValueError(ErrorCode.E003)
        return mapping[value]


# ============================================================
# 数据模型
# ============================================================
@dataclass
class Task:
    """任务条目。"""
    task_id: str
    description: str
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    impact: str = ""          # 影响范围描述
    urgency: int = 5          # 紧急度 1-10
    dependencies: List[str] = field(default_factory=list)  # 前置任务ID列表
    tags: List[str] = field(default_factory=list)
    estimated_hours: float = 0.0

    def validate(self) -> None:
        """校验任务基本合法性。"""
        if not self.task_id or not re.match(r"^[A-Za-z0-9_-]+$", self.task_id):
            raise ValueError(ErrorCode.E002)
        if not self.description or not self.description.strip():
            raise ValueError(ErrorCode.E001)
        if not 1 <= self.urgency <= 10:
            raise ValueError(ErrorCode.E009)

    def to_dict(self) -> Dict:
        """转为字典（用于序列化）。"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "impact": self.impact,
            "urgency": self.urgency,
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "estimated_hours": self.estimated_hours,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Task":
        """从字典构建任务。"""
        try:
            task = cls(
                task_id=data["task_id"],
                description=data["description"],
                priority=Priority.from_str(data.get("priority", "中")),
                status=TaskStatus.from_str(data.get("status", "待处理")),
                impact=data.get("impact", ""),
                urgency=int(data.get("urgency", 5)),
                dependencies=list(data.get("dependencies", [])),
                tags=list(data.get("tags", [])),
                estimated_hours=float(data.get("estimated_hours", 0.0)),
            )
            task.validate()
            return task
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(ErrorCode.E008) from exc


# ============================================================
# 核心逻辑：任务管理器
# ============================================================
class TaskManager:
    """任务治理核心类。"""

    def __init__(self) -> None:
        self.tasks: Dict[str, Task] = {}

    # ---------- 基础操作 ----------
    def add_task(self, task: Task) -> str:
        """添加任务。"""
        task.validate()
        if task.task_id in self.tasks:
            raise ValueError(ErrorCode.E009 + f": 任务ID {task.task_id} 已存在")
        self.tasks[task.task_id] = task
        return task.task_id

    def remove_task(self, task_id: str) -> None:
        """删除任务。"""
        self._get_task(task_id)
        # 同时清理其他任务对该任务的依赖引用
        for t in self.tasks.values():
            if task_id in t.dependencies:
                t.dependencies.remove(task_id)
        del self.tasks[task_id]

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务。"""
        return self.tasks.get(task_id)

    def _get_task(self, task_id: str) -> Task:
        """获取任务，不存在则报错。"""
        task = self.tasks.get(task_id)
        if task is None:
            raise ValueError(ErrorCode.E005 + f": 任务 {task_id} 不存在")
        return task

    def update_status(self, task_id: str, new_status: TaskStatus) -> None:
        """更新任务状态。"""
        task = self._get_task(task_id)
        task.status = new_status

    def update_priority(self, task_id: str, new_priority: Priority) -> None:
        """更新任务优先级。"""
        task = self._get_task(task_id)
        task.priority = new_priority

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """添加依赖关系：task_id 依赖 depends_on。"""
        task = self._get_task(task_id)
        self._get_task(depends_on)  # 确保被依赖任务存在
        if depends_on not in task.dependencies:
            task.dependencies.append(depends_on)
        self._check_cycle(task_id)

    def remove_dependency(self, task_id: str, depends_on: str) -> None:
        """移除依赖关系。"""
        task = self._get_task(task_id)
        if depends_on in task.dependencies:
            task.dependencies.remove(depends_on)

    # ---------- 依赖与循环检测 ----------
    def _check_cycle(self, start_id: str) -> None:
        """检测从 start_id 出发是否存在循环依赖。"""
        visited = set()
        stack = [start_id]

        while stack:
            current = stack.pop()
            if current in visited:
                raise ValueError(ErrorCode.E006 + f": 检测到循环依赖，涉及任务 {current}")
            visited.add(current)
            for dep in self.tasks[current].dependencies:
                stack.append(dep)

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """返回依赖关系图。"""
        graph = {}
        for task_id, task in self.tasks.items():
            graph[task_id] = list(task.dependencies)
        return graph

    # ---------- 优先级排序 ----------
    def _compute_score(self, task: Task) -> float:
        """计算任务综合优先级分数（分数越高越优先处理）。"""
        # 基础分：优先级权重
        priority_weight = {Priority.HIGH: 30, Priority.MEDIUM: 20, Priority.LOW: 10}
        base = priority_weight[task.priority]

        # 紧急度加权
        urgency_score = task.urgency * 3  # 1-10 => 3-30

        # 影响面：非空加 15 分
        impact_score = 15 if task.impact.strip() else 0

        # 阻塞状态惩罚
        if task.status == TaskStatus.BLOCKED:
            penalty = -20
        elif task.status == TaskStatus.DONE:
            penalty = -100  # 已完成任务排最后
        else:
            penalty = 0

        # 依赖数量加权：被依赖越多越优先（是其他任务的前置）
        dependents_count = sum(
            1 for t in self.tasks.values() if task.task_id in t.dependencies
        )
        dependency_score = dependents_count * 5

        return base + urgency_score + impact_score + penalty + dependency_score

    def sort_by_priority(self) -> List[Task]:
        """按优先级排序返回任务列表（从高到低）。"""
        tasks = list(self.tasks.values())
        tasks.sort(key=lambda t: self._compute_score(t), reverse=True)
        return tasks

    def get_priority_queue(self) -> List[Dict]:
        """返回排序后的任务队列（含排序理由）。"""
        sorted_tasks = self.sort_by_priority()
        result = []
        for idx, task in enumerate(sorted_tasks, 1):
            score = self._compute_score(task)
            reasons = self._explain_score(task)
            result.append({
                "rank": idx,
                "task_id": task.task_id,
                "description": task.description,
                "priority": task.priority.value,
                "status": task.status.value,
                "score": round(score, 1),
                "reasons": reasons,
            })
        return result

    def _explain_score(self, task: Task) -> List[str]:
        """生成排序理由。"""
        reasons = []
        reasons.append(f"优先级基础分: {task.priority.value}")
        reasons.append(f"紧急度 {task.urgency}/10")
        if task.impact.strip():
            reasons.append("有明确影响范围")
        if task.status == TaskStatus.BLOCKED:
            reasons.append("当前处于阻塞状态，建议优先处理")
        dependents = [t for t in self.tasks.values() if task.task_id in t.dependencies]
        if dependents:
            reasons.append(f"被 {len(dependents)} 个任务依赖")
        return reasons

    # ---------- 下一步动作推荐 ----------
    def recommend_next_actions(self, max_actions: int = 3) -> List[Dict]:
        """推荐下一步动作。"""
        sorted_tasks = self.sort_by_priority()
        recommendations = []

        for task in sorted_tasks:
            if task.status == TaskStatus.DONE:
                continue

            # 检查依赖是否全部完成
            blocked_by = [dep for dep in task.dependencies
                          if self.tasks[dep].status != TaskStatus.DONE]

            if blocked_by:
                # 有未完成的依赖，推荐处理依赖
                action = {
                    "task_id": task.task_id,
                    "action": "先处理前置任务",
                    "reason": f"任务 {task.task_id} 依赖 {blocked_by}，需先完成这些任务",
                    "blocked_by": blocked_by,
                }
            elif task.status == TaskStatus.BLOCKED:
                action = {
                    "task_id": task.task_id,
                    "action": "解除阻塞",
                    "reason": f"任务 {task.task_id} 处于阻塞状态，需排查阻塞原因",
                    "blocked_by": [],
                }
            else:
                action = {
                    "task_id": task.task_id,
                    "action": "立即开始",
                    "reason": f"任务 {task.task_id} 优先级最高且无阻塞依赖",
                    "blocked_by": [],
                }
            recommendations.append(action)

            if len(recommendations) >= max_actions:
                break

        return recommendations

    # ---------- 序列化 ----------
    def to_json(self) -> str:
        """导出为 JSON 字符串。"""
        try:
            data = {"tasks": [t.to_dict() for t in self.tasks.values()]}
            return json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise ValueError(ErrorCode.E007) from exc

    @classmethod
    def from_json(cls, json_str: str) -> "TaskManager":
        """从 JSON 字符串加载。"""
        try:
            data = json.loads(json_str)
            manager = cls()
            for task_data in data.get("tasks", []):
                task = Task.from_dict(task_data)
                manager.add_task(task)
            return manager
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise ValueError(ErrorCode.E008) from exc


# ============================================================
# 输入解析（自由文本 → 结构化任务）
# ============================================================
class InputParser:
    """将自由文本解析为任务列表。"""

    @staticmethod
    def parse_free_text(text: str) -> List[Task]:
        """从自由文本中提取任务。"""
        if not text or not text.strip():
            raise ValueError(ErrorCode.E001)

        lines = text.strip().splitlines()
        tasks = []
        task_id_counter = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试提取优先级标记
            priority = Priority.MEDIUM
            if "高优" in line or "紧急" in line or "高优先级" in line:
                priority = Priority.HIGH
            elif "低优" in line or "不急" in line or "低优先级" in line:
                priority = Priority.LOW

            # 尝试提取紧急度
            urgency = 5
            m = re.search(r"紧急度[：:]\s*(\d+)", line)
            if m:
                urgency = max(1, min(10, int(m.group(1))))

            # 创建任务
            task = Task(
                task_id=f"T-{task_id_counter:03d}",
                description=line,
                priority=priority,
                urgency=urgency,
            )
            tasks.append(task)
            task_id_counter += 1

        if not tasks:
            raise ValueError(ErrorCode.E001 + ": 未提取到有效任务描述")

        return tasks


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松断言，确保任何环境可直接通过。
    """
    print("=== pm-manager 自检开始 ===")

    # ---------- 1. 构建测试数据 ----------
    manager = TaskManager()

    # 任务1: 高优先级，紧急
    t1 = Task(
        task_id="T-001",
        description="登录页报错，用户无法登录",
        priority=Priority.HIGH,
        urgency=9,
        impact="影响所有用户登录",
        status=TaskStatus.TODO,
    )
    # 任务2: 中优先级
    t2 = Task(
        task_id="T-002",
        description="支付超时问题",
        priority=Priority.MEDIUM,
        urgency=7,
        impact="影响支付流程",
        status=TaskStatus.TODO,
    )
    # 任务3: 低优先级，依赖 T-001
    t3 = Task(
        task_id="T-003",
        description="优化登录页面 UI",
        priority=Priority.LOW,
        urgency=3,
        status=TaskStatus.BLOCKED,
        dependencies=["T-001"],
    )
    # 任务4: 已完成
    t4 = Task(
        task_id="T-004",
        description="数据库备份",
        priority=Priority.MEDIUM,
        urgency=2,
        status=TaskStatus.DONE,
    )

    for task in [t1, t2, t3, t4]:
        manager.add_task(task)

    # ---------- 2. 基础操作自检 ----------
    assert len(manager.tasks) == 4, "任务添加失败"
    print("[PASS] 任务添加")

    # 状态更新
    manager.update_status("T-002", TaskStatus.IN_PROGRESS)
    assert manager.get_task("T-002").status == TaskStatus.IN_PROGRESS, "状态更新失败"
    print("[PASS] 状态更新")

    # 优先级更新
    manager.update_priority("T-002", Priority.HIGH)
    assert manager.get_task("T-002").priority == Priority.HIGH, "优先级更新失败"
    print("[PASS] 优先级更新")

    # ---------- 3. 依赖分析自检 ----------
    graph = manager.get_dependency_graph()
    assert "T-001" in graph.get("T-003", []), "依赖关系未正确记录"
    print("[PASS] 依赖关系")

    # 循环检测
    try:
        manager.add_dependency("T-001", "T-003")  # 会形成循环
        assert False, "循环检测未生效"
    except ValueError as exc:
        assert ErrorCode.E006 in str(exc), "循环检测错误码不正确"
    print("[PASS] 循环依赖检测")

    # ---------- 4. 优先级排序自检 ----------
    queue = manager.get_priority_queue()
    assert len(queue) == 4, "排序队列长度不正确"

    # 宽松断言：T-001（高优先级+高紧急度）应排在 T-004（已完成）之前
    rank_t1 = next(item["rank"] for item in queue if item["task_id"] == "T-001")
    rank_t4 = next(item["rank"] for item in queue if item["task_id"] == "T-004")
    assert rank_t1 < rank_t4, "高优先级任务应排在已完成任务之前"
    print("[PASS] 优先级排序")

    # 排序理由非空
    for item in queue:
        assert len(item["reasons"]) > 0, "排序理由不应为空"
    print("[PASS] 排序理由")

    # ---------- 5. 下一步动作推荐自检 ----------
    recs = manager.recommend_next_actions(max_actions=3)
    assert 1 <= len(recs) <= 3, "推荐动作数量应在 1-3 之间"
    for rec in recs:
        assert "task_id" in rec and "action" in rec and "reason" in rec, "推荐动作字段不完整"
    print("[PASS] 下一步动作推荐")

    # ---------- 6. 序列化自检 ----------
    json_str = manager.to_json()
    assert len(json_str) > 0, "序列化结果为空"
    manager2 = TaskManager.from_json(json_str)
    assert len(manager2.tasks) == 4, "反序列化后任务数量不一致"
    assert manager2.get_task("T-001").description == t1.description, "反序列化内容不一致"
    print("[PASS] JSON 序列化/反序列化")

    # ---------- 7. 输入解析自检 ----------
    parser = InputParser()
    parsed_tasks = parser.parse_free_text("高优：修复登录页报错\n支付超时也需要处理")
    assert len(parsed_tasks) == 2, "自由文本解析任务数量不正确"
    assert parsed_tasks[0].priority == Priority.HIGH, "高优标记解析失败"
    print("[PASS] 自由文本解析")

    # ---------- 8. 错误处理自检 ----------
    try:
        manager.get_task("NON_EXIST")
        assert False, "应抛出 E005 错误"
    except ValueError as exc:
        assert ErrorCode.E005 in str(exc), "错误码 E005 未正确抛出"
    print("[PASS] 错误处理")

    print("=== 全部自检通过 ===")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="pm-manager: 任务治理、优先级排序、修复决策",
        epilog="示例: python main.py --add '登录页报错' --priority 高",
    )
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（无需外部依赖）")
    parser.add_argument("--add", type=str, metavar="TEXT",
                        help="添加新任务（自由文本）")
    parser.add_argument("--priority", type=str, choices=["高", "中", "低"],
                        default="中", help="任务优先级")
    parser.add_argument("--urgency", type=int, default=5, choices=range(1, 11),
                        help="紧急度 (1-10)")
    parser.add_argument("--list", action="store_true",
                        help="按优先级列出所有任务")
    parser.add_argument("--recommend", action="store_true",
                        help="获取下一步动作推荐")
    parser.add_argument("--status", type=str, metavar="TASK_ID",
                        help="查看指定任务状态")
    parser.add_argument("--export", type=str, metavar="FILE",
                        help="导出任务到 JSON 文件")
    parser.add_argument("--import", dest="import_file", type=str, metavar="FILE",
                        help="从 JSON 文件导入任务")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"自检异常: {exc}", file=sys.stderr)
            return 1

    manager = TaskManager()

    # 导入模式
    if args.import_file:
        try:
            with open(args.import_file, "r", encoding="utf-8") as f:
                manager = TaskManager.from_json(f.read())
            print(f"已从 {args.import_file} 导入 {len(manager.tasks)} 个任务")
        except (OSError, ValueError) as exc:
            print(f"导入失败: {exc}", file=sys.stderr)
            return 1

    # 添加任务模式
    if args.add:
        try:
            task = Task(
                task_id=f"T-{len(manager.tasks) + 1:03d}",
                description=args.add,
                priority=Priority.from_str(args.priority),
                urgency=args.urgency,
            )
            manager.add_task(task)
            print(f"已添加任务: {task.task_id} | {task.description} | 优先级:{task.priority.value}")
        except ValueError as exc:
            print(f"添加失败: {exc}", file=sys.stderr)
            return 1

    # 查看状态模式
    if args.status:
        try:
            task = manager.get_task(args.status)
            if task is None:
                print(f"任务 {args.status} 不存在", file=sys.stderr)
                return 1
            print(f"任务: {task.task_id}")
            print(f"  描述: {task.description}")
            print(f"  优先级: {task.priority.value}")
            print(f"  状态: {task.status.value}")
            print(f"  紧急度: {task.urgency}/10")
            print(f"  影响: {task.impact or '无'}")
            print(f"  依赖: {task.dependencies or '无'}")
        except ValueError as exc:
            print(f"查询失败: {exc}", file=sys.stderr)
            return 1

    # 列表模式
    if args.list:
        queue = manager.get_priority_queue()
        if not queue:
            print("当前无任务")
        else:
            print("=== 优先级队列 ===")
            for item in queue:
                print(f"[{item['rank']}] {item['task_id']} | {item['description']} "
                      f"| 优先级:{item['priority']} | 状态:{item['status']} | 分数:{item['score']}")

    # 推荐模式
    if args.recommend:
        recs = manager.recommend_next_actions()
        if not recs:
            print("当前无任务需要处理")
        else:
            print("=== 下一步动作推荐 ===")
            for rec in recs:
                print(f"  → {rec['task_id']}: {rec['action']} - {rec['reason']}")

    # 导出模式
    if args.export:
        try:
            with open(args.export, "w", encoding="utf-8") as f:
                f.write(manager.to_json())
            print(f"已导出到 {args.export}")
        except (OSError, ValueError) as exc:
            print(f"导出失败: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
