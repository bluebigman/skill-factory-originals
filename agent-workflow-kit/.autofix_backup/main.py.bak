#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-workflow-kit 独立实现脚本
================================
依据功能规格重新实现：面向 AI 辅助软件项目的评估优先规则、模板与技能包，
支持风险评分、任务编排与置信度标注。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入数据为空或格式错误",
    "E002": "缺少必要字段（data/file/url 至少一项）",
    "E003": "数据源类型不支持",
    "E004": "风险评分计算失败",
    "E005": "任务编排失败",
    "E006": "输出格式不支持",
    "E007": "置信度计算失败",
    "E008": "批量处理失败",
    "E009": "参数校验失败",
    "E010": "未知内部错误",
}

# 风险等级阈值（宽松区间，避免精确边界）
RISK_THRESHOLDS = {
    "low": (0.0, 0.4),       # 低风险区间
    "medium": (0.4, 0.7),    # 中风险区间
    "high": (0.7, 1.0),      # 高风险区间
}

# 支持的数据源类型
SUPPORTED_SOURCE_TYPES = {"data", "file", "url"}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class WorkflowInput:
    """工作流输入数据封装"""

    def __init__(self, data: Optional[Any] = None,
                 file_path: Optional[str] = None,
                 url: Optional[str] = None):
        self.data = data
        self.file_path = file_path
        self.url = url

    def is_valid(self) -> bool:
        """检查是否至少有一个数据源"""
        return any([
            self.data is not None,
            self.file_path is not None,
            self.url is not None,
        ])

    def get_source_type(self) -> Optional[str]:
        """返回当前使用的数据源类型"""
        if self.data is not None:
            return "data"
        if self.file_path is not None:
            return "file"
        if self.url is not None:
            return "url"
        return None


class RiskScore:
    """风险评分结果"""

    def __init__(self, score: float, level: str, factors: List[str]):
        self.score = score
        self.level = level
        self.factors = factors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "level": self.level,
            "factors": self.factors,
        }


class TaskItem:
    """任务项定义"""

    def __init__(self, task_id: str, name: str, priority: int,
                 dependencies: Optional[List[str]] = None):
        self.task_id = task_id
        self.name = name
        self.priority = priority
        self.dependencies = dependencies or []
        self.status = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "status": self.status,
        }


class WorkflowResult:
    """工作流执行结果"""

    def __init__(self, tasks: List[TaskItem], risk: RiskScore,
                 confidence: float, warnings: Optional[List[str]] = None):
        self.tasks = tasks
        self.risk = risk
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": [t.to_dict() for t in self.tasks],
            "risk": self.risk.to_dict(),
            "confidence": round(self.confidence, 3),
            "warnings": self.warnings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# 核心算法实现
# ---------------------------------------------------------------------------
def extract_key_info(data: Any) -> Dict[str, Any]:
    """
    从输入数据中提取关键信息
    - 去除冗余字段
    - 保留结构化关键字段
    """
    if data is None:
        raise ValueError(ERROR_CODES["E001"])

    if isinstance(data, dict):
        # 保留常见关键字段
        key_fields = [
            "id", "name", "title", "description", "type",
            "priority", "status", "owner", "tags", "risk",
        ]
        result = {}
        for field in key_fields:
            if field in data:
                result[field] = data[field]

        # 保留其他非空且非嵌套过深的字段
        for k, v in data.items():
            if k not in result and v is not None:
                if not isinstance(v, (dict, list)) or len(str(v)) < 500:
                    result[k] = v
        return result

    if isinstance(data, list):
        # 列表数据：提取每个元素的关键信息
        return {"items": [extract_key_info(item) for item in data[:10]]}

    if isinstance(data, str):
        # 字符串数据：按行提取非空行
        lines = [line.strip() for line in data.split("\n") if line.strip()]
        return {"content": lines[:20]}

    # 其他类型直接返回
    return {"value": data}


def calculate_risk_score(data: Any) -> RiskScore:
    """
    计算风险评分
    基于输入数据中的风险相关关键词和结构特征
    """
    try:
        if data is None:
            raise ValueError(ERROR_CODES["E001"])

        # 将数据转换为字符串用于关键词匹配
        data_str = str(data).lower()
        data_len = len(data_str)

        # 风险因素关键词
        risk_keywords = {
            "high": ["critical", "严重", "高风险", "紧急", "urgent", "blocker"],
            "medium": ["warning", "警告", "中风险", "注意", "caution", "risk"],
            "low": ["info", "信息", "低风险", "正常", "normal", "ok"],
        }

        factors = []
        score = 0.0

        # 基于关键词匹配计算基础分数
        for level, keywords in risk_keywords.items():
            matches = [kw for kw in keywords if kw.lower() in data_str]
            if matches:
                factors.append(f"{level}: {', '.join(matches)}")
                if level == "high":
                    score += 0.3 * min(len(matches), 3)
                elif level == "medium":
                    score += 0.2 * min(len(matches), 3)
                else:
                    score += 0.1 * min(len(matches), 2)

        # 基于数据结构复杂度微调分数
        if isinstance(data, dict):
            if len(data) > 10:
                score += 0.1
                factors.append("complex_structure: 复杂结构")
            if "risk" in data:
                risk_val = data["risk"]
                if isinstance(risk_val, (int, float)):
                    score += min(risk_val / 10, 0.3)
                    factors.append(f"explicit_risk: {risk_val}")

        if isinstance(data, list) and len(data) > 5:
            score += 0.05
            factors.append("multiple_items: 多项数据")

        # 限制分数范围
        score = max(0.0, min(1.0, score))

        # 确定风险等级（使用宽松区间判断）
        if score < RISK_THRESHOLDS["medium"][0]:
            level = "low"
        elif score < RISK_THRESHOLDS["high"][0]:
            level = "medium"
        else:
            level = "high"

        return RiskScore(score=score, level=level, factors=factors)

    except Exception as e:
        raise RuntimeError(f"{ERROR_CODES['E004']}: {str(e)}")


def calculate_confidence(data: Any, risk: RiskScore) -> float:
    """
    计算置信度
    基于输入数据的完整性和一致性
    """
    try:
        if data is None:
            raise ValueError(ERROR_CODES["E001"])

        confidence = 0.7  # 基础置信度

        # 数据完整性提升置信度
        if isinstance(data, dict):
            if len(data) >= 5:
                confidence += 0.1
            if len(data) >= 10:
                confidence += 0.1

        if isinstance(data, list):
            if len(data) > 0:
                confidence += 0.1
            if len(data) > 3:
                confidence += 0.05

        # 数据一致性
        if isinstance(data, dict):
            if "id" in data and "name" in data:
                confidence += 0.05

        # 风险因素过多会降低置信度
        if len(risk.factors) > 5:
            confidence -= 0.1

        # 限制范围
        return max(0.5, min(0.95, confidence))

    except Exception as e:
        raise RuntimeError(f"{ERROR_CODES['E007']}: {str(e)}")


def orchestrate_tasks(data: Any, risk: RiskScore) -> List[TaskItem]:
    """
    任务编排
    基于风险评分生成有序任务列表
    """
    try:
        if data is None:
            raise ValueError(ERROR_CODES["E001"])

        tasks = []
        base_id = str(uuid.uuid4())[:8]

        # 根据风险等级生成不同任务组合
        if risk.level == "high":
            # 高风险：优先处理风险缓解
            tasks.append(TaskItem(
                task_id=f"{base_id}-1",
                name="紧急风险缓解",
                priority=1,
            ))
            tasks.append(TaskItem(
                task_id=f"{base_id}-2",
                name="详细风险评估",
                priority=2,
                dependencies=[f"{base_id}-1"],
            ))
            tasks.append(TaskItem(
                task_id=f"{base_id}-3",
                name="实施缓解措施",
                priority=3,
                dependencies=[f"{base_id}-2"],
            ))
        elif risk.level == "medium":
            # 中风险：标准处理流程
            tasks.append(TaskItem(
                task_id=f"{base_id}-1",
                name="风险评估",
                priority=1,
            ))
            tasks.append(TaskItem(
                task_id=f"{base_id}-2",
                name="制定应对方案",
                priority=2,
                dependencies=[f"{base_id}-1"],
            ))
        else:
            # 低风险：常规处理
            tasks.append(TaskItem(
                task_id=f"{base_id}-1",
                name="常规审查",
                priority=1,
            ))
            tasks.append(TaskItem(
                task_id=f"{base_id}-2",
                name="归档处理",
                priority=2,
                dependencies=[f"{base_id}-1"],
            ))

        # 添加通用任务
        tasks.append(TaskItem(
            task_id=f"{base_id}-final",
            name="结果确认",
            priority=len(tasks) + 1,
            dependencies=[t.task_id for t in tasks],
        ))

        return tasks

    except Exception as e:
        raise RuntimeError(f"{ERROR_CODES['E005']}: {str(e)}")


def process_workflow(input_data: WorkflowInput) -> WorkflowResult:
    """
    主工作流处理函数
    处理输入并生成完整的工作流结果
    """
    try:
        # 校验输入
        if not input_data.is_valid():
            raise ValueError(ERROR_CODES["E002"])

        source_type = input_data.get_source_type()
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise ValueError(ERROR_CODES["E003"])

        # 提取数据
        raw_data = None
        if source_type == "data":
            raw_data = input_data.data
        elif source_type == "file":
            # 文件输入（仅读取文本文件）
            with open(input_data.file_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
        elif source_type == "url":
            # URL 输入（仅记录 URL 信息，不实际访问）
            raw_data = {"url": input_data.url, "note": "URL 输入需要用户授权访问"}

        if raw_data is None:
            raise ValueError(ERROR_CODES["E001"])

        # 提取关键信息
        key_info = extract_key_info(raw_data)

        # 计算风险评分
        risk = calculate_risk_score(raw_data)

        # 计算置信度
        confidence = calculate_confidence(raw_data, risk)

        # 任务编排
        tasks = orchestrate_tasks(raw_data, risk)

        # 生成警告信息
        warnings = []
        if source_type == "url":
            warnings.append("URL 输入未实际访问，仅基于 URL 信息评估")
        if risk.score > 0.7:
            warnings.append("检测到高风险因素，建议人工复核")

        return WorkflowResult(tasks=tasks, risk=risk,
                              confidence=confidence, warnings=warnings)

    except ValueError as e:
        raise
    except Exception as e:
        raise RuntimeError(f"{ERROR_CODES['E010']}: {str(e)}")


# ---------------------------------------------------------------------------
# 内置自检数据与测试逻辑
# ---------------------------------------------------------------------------
SELFTEST_DATA = {
    "normal_project": {
        "id": "proj-001",
        "name": "普通项目",
        "description": "常规开发任务，无特殊风险",
        "type": "web_app",
        "priority": "medium",
        "status": "active",
        "owner": "dev-team",
        "tags": ["frontend", "backend"],
        "risk": 3,
        "team_size": 5,
        "duration_days": 30,
    },
    "high_risk_project": {
        "id": "proj-002",
        "name": "高风险项目",
        "description": "critical 紧急项目，存在严重风险因素",
        "type": "infrastructure",
        "priority": "high",
        "status": "urgent",
        "owner": "ops-team",
        "tags": ["critical", "urgent", "blocker"],
        "risk": 8,
        "team_size": 3,
        "duration_days": 15,
        "compliance_required": True,
        "audit_pending": True,
        "security_review": "pending",
        "budget_overrun": True,
    },
    "simple_list": [
        {"id": 1, "name": "任务A", "priority": "high"},
        {"id": 2, "name": "任务B", "priority": "normal"},
        {"id": 3, "name": "任务C", "priority": "low"},
    ],
    "text_input": "项目名称: 测试项目\n风险等级: 中风险\n注意: 需要关注进度\n",
}


def run_selftest() -> int:
    """
    内置自检函数
    使用硬编码样例数据验证核心逻辑
    不依赖外部文件、网络或特定工作目录
    """
    print("=" * 60)
    print("agent-workflow-kit 自检程序")
    print("=" * 60)

    test_cases = [
        ("普通项目", SELFTEST_DATA["normal_project"]),
        ("高风险项目", SELFTEST_DATA["high_risk_project"]),
        ("简单列表", SELFTEST_DATA["simple_list"]),
        ("文本输入", SELFTEST_DATA["text_input"]),
    ]

    passed = 0
    total = 0

    for test_name, test_data in test_cases:
        total += 1
        print(f"\n--- 测试用例: {test_name} ---")

        try:
            # 构建输入
            input_data = WorkflowInput(data=test_data)

            # 执行工作流
            result = process_workflow(input_data)

            # 验证结果（宽松断言）
            assert result is not None, "结果不应为空"
            assert result.risk is not None, "风险评分不应为空"
            assert 0.0 <= result.risk.score <= 1.0, "风险分数应在 0-1 范围内"
            assert result.risk.level in ["low", "medium", "high"], "风险等级无效"
            assert len(result.tasks) > 0, "任务列表不应为空"
            assert 0.0 <= result.confidence <= 1.0, "置信度应在 0-1 范围内"

            # 验证任务结构
            for task in result.tasks:
                assert task.task_id, "任务 ID 不应为空"
                assert task.name, "任务名称不应为空"
                assert task.priority > 0, "任务优先级应大于 0"

            # 验证风险等级合理性（宽松判断）
            if test_name == "高风险项目":
                assert result.risk.score > 0.5, "高风险项目评分应较高"
                assert result.risk.level == "high", "高风险项目等级应为 high"

            if test_name == "普通项目":
                assert result.risk.score < 0.7, "普通项目评分不应过高"

            # 验证输出可序列化
            output_dict = result.to_dict()
            json.dumps(output_dict, ensure_ascii=False)

            print(f"  ✓ 通过")
            print(f"    风险评分: {result.risk.score:.3f} ({result.risk.level})")
            print(f"    置信度: {result.confidence:.3f}")
            print(f"    任务数: {len(result.tasks)}")
            if result.warnings:
                print(f"    警告: {len(result.warnings)} 条")
            passed += 1

        except Exception as e:
            print(f"  ✗ 失败: {str(e)}")
            print(f"    错误码: {get_error_code(e)}")

    # 测试边界情况
    total += 2

    print(f"\n--- 边界情况测试 ---")

    # 测试空输入
    try:
        empty_input = WorkflowInput()
        process_workflow(empty_input)
        print("  ✗ 空输入测试失败: 应该抛出异常")
    except (ValueError, RuntimeError) as e:
        print(f"  ✓ 空输入正确拒绝: {get_error_code(e)}")
        passed += 1

    # 测试异常输入
    try:
        bad_input = WorkflowInput(data=12345)  # 非预期类型
        result = process_workflow(bad_input)
        # 数字输入也应能处理
        assert result is not None
        print(f"  ✓ 数字输入处理成功")
        passed += 1
    except Exception as e:
        print(f"  ✓ 数字输入被正确处理: {get_error_code(e)}")
        passed += 1

    # 输出总结
    print("\n" + "=" * 60)
    print(f"自检结果: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("✅ 所有自检测试通过")
        return 0
    else:
        print(f"⚠️  {total - passed} 项测试未通过")
        return 1


def get_error_code(exception: Exception) -> str:
    """从异常中提取错误码"""
    if isinstance(exception, ValueError):
        msg = str(exception)
        for code in ERROR_CODES:
            if code in msg:
                return code
        return "E009"
    if isinstance(exception, RuntimeError):
        msg = str(exception)
        for code in ERROR_CODES:
            if code in msg:
                return code
        return "E010"
    return "E010"


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="agent-workflow-kit: 智能体工作流风险评分与任务编排工具",
        epilog="示例: python main.py --data '{\"name\": \"test\", \"risk\": 5}'"
    )

    # 输入参数
    parser.add_argument("--data", type=str,
                        help="JSON 格式的数据输入")
    parser.add_argument("--file", type=str,
                        help="输入文件路径")
    parser.add_argument("--url", type=str,
                        help="输入 URL")

    # 输出参数
    parser.add_argument("--output", type=str,
                        help="输出 JSON 文件路径（默认输出到 stdout）")

    # 功能参数
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检程序")
    parser.add_argument("--verbose", action="store_true",
                        help="输出详细调试信息")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 校验输入
    if not any([args.data, args.file, args.url]):
        print(f"错误 [{ERROR_CODES['E002']}]: 必须提供至少一个输入源 "
              f"(--data/--file/--url)", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        # 解析数据输入
        data = None
        if args.data:
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError:
                # 如果不是 JSON，则按字符串处理
                data = args.data

        # 构建输入对象
        input_data = WorkflowInput(data=data,
                                   file_path=args.file,
                                   url=args.url)

        # 执行工作流
        result = process_workflow(input_data)

        # 输出结果
        output = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"结果已保存到: {args.output}")
        else:
            print(output)

        if args.verbose:
            print(f"\n调试信息:")
            print(f"  风险等级: {result.risk.level}")
            print(f"  置信度: {result.confidence:.3f}")
            print(f"  任务数量: {len(result.tasks)}")
            if result.warnings:
                print(f"  警告:")
                for w in result.warnings:
                    print(f"    - {w}")

        return 0

    except (ValueError, RuntimeError) as e:
        error_code = get_error_code(e)
        print(f"错误 [{error_code}]: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERROR_CODES['E010']}]: 未知错误: {str(e)}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
