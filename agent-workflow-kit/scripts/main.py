#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-workflow-kit 独立实现脚本
================================
面向 AI 辅助软件项目的结构化评估工具，支持多维度风险评分、
工作流质量分析与置信度门控，输出 JSON/Markdown 格式报告。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.request
import urllib.error
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


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
    "E011": "URL 获取失败",
}

# 风险等级阈值
RISK_THRESHOLDS = {
    "low": (0.0, 0.4),
    "medium": (0.4, 0.7),
    "high": (0.7, 1.0),
}

# 支持的数据源类型
SUPPORTED_SOURCE_TYPES = {"data", "file", "url"}

# URL 请求配置
URL_TIMEOUT = int(os.environ.get("AWK_URL_TIMEOUT", "10"))
URL_MAX_RETRIES = int(os.environ.get("AWK_MAX_RETRIES", "3"))
URL_RETRY_BACKOFF = 1.0

# 并发配置
MAX_WORKERS = 4

# 默认维度权重
DEFAULT_WEIGHTS = {
    "task_clarity": 0.25,
    "dependency": 0.20,
    "resource": 0.20,
    "risk_coverage": 0.20,
    "scalability": 0.15,
}

# 维度中文名映射
DIMENSION_NAMES = {
    "task_clarity": "任务清晰度",
    "dependency": "依赖合理性",
    "resource": "资源分配",
    "risk_coverage": "风险覆盖",
    "scalability": "可扩展性",
}


# ---------------------------------------------------------------------------
# 异常定义
# ---------------------------------------------------------------------------
class WorkflowError(Exception):
    """工作流评估基础异常"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class InputError(WorkflowError):
    """输入数据错误"""

    def __init__(self, code: str = "E001", message: str = ""):
        super().__init__(code, message or ERROR_CODES.get(code, "未知错误"))


class URLFetchError(WorkflowError):
    """URL 获取错误"""

    def __init__(self, message: str = ""):
        super().__init__("E011", message or ERROR_CODES["E011"])


# ---------------------------------------------------------------------------
# 输入数据封装
# ---------------------------------------------------------------------------
class WorkflowInput:
    """工作流输入数据封装"""

    def __init__(self, data: Optional[Any] = None,
                 file_path: Optional[str] = None,
                 url: Optional[str] = None,
                 dry_run: bool = False):
        self.data = data
        self.file_path = file_path
        self.url = url
        self.dry_run = dry_run

    def is_valid(self) -> bool:
        """检查是否至少有一个数据源"""
        return any([
            self.data is not None,
            self.file_path is not None,
            self.url is not None,
        ])

    def get_source_type(self) -> Optional[str]:
        """获取数据源类型"""
        if self.data is not None:
            return "data"
        if self.file_path is not None:
            return "file"
        if self.url is not None:
            return "url"
        return None


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------
def load_input_data(workflow_input: WorkflowInput) -> Any:
    """加载输入数据，支持 data/file/url 三种来源"""
    source_type = workflow_input.get_source_type()
    if source_type is None:
        raise InputError("E002")

    try:
        if source_type == "data":
            return _parse_json_data(workflow_input.data)
        elif source_type == "file":
            return _load_from_file(workflow_input.file_path)
        elif source_type == "url":
            return _load_from_url(workflow_input.url)
        else:
            raise InputError("E003")
    except WorkflowError:
        raise
    except Exception as e:
        raise InputError("E001", f"数据加载失败: {str(e)}")


def _parse_json_data(data: Any) -> Any:
    """解析 JSON 数据"""
    if isinstance(data, (dict, list)):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise InputError("E001", f"JSON 解析失败: {str(e)}")
    raise InputError("E001", f"不支持的数据类型: {type(data).__name__}")


def _load_from_file(file_path: str) -> Any:
    """从文件加载数据，支持多编码"""
    if not os.path.isfile(file_path):
        raise InputError("E001", f"文件不存在: {file_path}")

    content = _read_file_with_encoding(file_path)
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise InputError("E001", f"JSON 解析失败: {str(e)}")


def _read_file_with_encoding(file_path: str) -> str:
    """读取文件内容，支持多编码 fallback"""
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except OSError as e:
            raise InputError("E001", f"文件读取失败: {str(e)}")
    raise InputError("E001", f"无法识别文件编码: {file_path}")


def _load_from_url(url: str) -> Any:
    """从 URL 加载数据，带超时和指数退避重试"""
    last_error: Optional[Exception] = None
    for attempt in range(URL_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agent-workflow-kit/2.0"})
            with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise InputError("E001", f"JSON 解析失败: {str(e)}")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < URL_MAX_RETRIES - 1:
                time.sleep(URL_RETRY_BACKOFF * (2 ** attempt))
    raise URLFetchError(f"URL 请求失败: {str(last_error)}")


# ---------------------------------------------------------------------------
# 项目数据校验
# ---------------------------------------------------------------------------
def validate_project_data(data: Any) -> Dict[str, Any]:
    """校验项目数据，返回规范化后的项目字典"""
    if not isinstance(data, dict):
        raise InputError("E001", "项目数据必须是 JSON 对象")

    project_name = data.get("project_name") or data.get("name")
    if not project_name:
        raise InputError("E002", "缺少 project_name 字段")

    return {
        "project_name": str(project_name),
        "description": data.get("description", ""),
        "workflow": data.get("workflow", {}),
        "resources": data.get("resources", {}),
        "risks": data.get("risks", []),
        "raw": data,
    }


# ---------------------------------------------------------------------------
# 维度评分
# ---------------------------------------------------------------------------
def score_task_clarity(project: Dict[str, Any]) -> Tuple[float, str]:
    """评估任务清晰度"""
    workflow = project.get("workflow", {})
    tasks = workflow.get("tasks", [])
    description = project.get("description", "")

    if not tasks and not description:
        return 0.0, "缺少任务定义和项目描述，无法评估"

    score = 50.0
    reasons = []

    if tasks:
        score += 20.0
        reasons.append(f"定义了 {len(tasks)} 个任务")
    if description:
        score += 15.0
        reasons.append("有项目描述")
    if workflow.get("dependencies"):
        score += 15.0
        reasons.append("定义了任务依赖关系")

    return min(score, 100.0), "; ".join(reasons) if reasons else "基础评估"


def score_dependency(project: Dict[str, Any]) -> Tuple[float, str]:
    """评估依赖合理性"""
    workflow = project.get("workflow", {})
    dependencies = workflow.get("dependencies", [])

    if not dependencies:
        return 50.0, "未定义依赖关系，无法评估合理性"

    score = 60.0
    reasons = [f"定义了 {len(dependencies)} 条依赖"]

    # 检查循环依赖
    if _has_cycle(dependencies):
        score -= 30.0
        reasons.append("检测到循环依赖")
    else:
        score += 20.0
        reasons.append("无循环依赖")

    return min(score, 100.0), "; ".join(reasons)


def _has_cycle(dependencies: List[Any]) -> bool:
    """检测依赖图中是否存在循环"""
    graph: Dict[str, List[str]] = {}
    for dep in dependencies:
        if isinstance(dep, dict):
            src = str(dep.get("from", ""))
            dst = str(dep.get("to", ""))
        elif isinstance(dep, (list, tuple)) and len(dep) >= 2:
            src, dst = str(dep[0]), str(dep[1])
        else:
            continue
        graph.setdefault(src, []).append(dst)

    visited = set()
    path = set()

    def dfs(node: str) -> bool:
        if node in path:
            return True
        if node in visited:
            return False
        visited.add(node)
        path.add(node)
        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True
        path.remove(node)
        return False

    for node in graph:
        if dfs(node):
            return True
    return False


def score_resource(project: Dict[str, Any]) -> Tuple[float, str]:
    """评估资源分配"""
    resources = project.get("resources", {})

    if not resources:
        return 50.0, "未定义资源分配"

    score = 60.0
    reasons = []

    if isinstance(resources, dict):
        if "team_size" in resources:
            score += 15.0
            reasons.append(f"团队规模: {resources['team_size']}")
        if "budget" in resources:
            score += 15.0
            reasons.append(f"预算: {resources['budget']}")
        if "timeline" in resources:
            score += 10.0
            reasons.append(f"时间线: {resources['timeline']}")

    return min(score, 100.0), "; ".join(reasons) if reasons else "基础资源评估"


def score_risk_coverage(project: Dict[str, Any]) -> Tuple[float, str]:
    """评估风险覆盖"""
    risks = project.get("risks", [])

    if not risks:
        return 40.0, "未定义风险清单"

    score = 50.0
    reasons = [f"识别了 {len(risks)} 个风险"]

    for risk in risks:
        if isinstance(risk, dict):
            if risk.get("mitigation"):
                score += 10.0
                reasons.append(f"风险 '{risk.get('id', 'unknown')}' 有缓解措施")
            if risk.get("likelihood") and risk.get("impact"):
                score += 5.0
                reasons.append(f"风险 '{risk.get('id', 'unknown')}' 有概率/影响评估")

    return min(score, 100.0), "; ".join(reasons)


def score_scalability(project: Dict[str, Any]) -> Tuple[float, str]:
    """评估可扩展性"""
    workflow = project.get("workflow", {})
    description = project.get("description", "").lower()

    score = 40.0
    reasons = []

    if "扩展" in description or "scalable" in description:
        score += 20.0
        reasons.append("描述中提到可扩展性")
    if workflow.get("parallel_tasks"):
        score += 20.0
        reasons.append("支持并行任务")
    if workflow.get("modular"):
        score += 20.0
        reasons.append("模块化设计")

    return min(score, 100.0), "; ".join(reasons) if reasons else "基础可扩展性评估"


# ---------------------------------------------------------------------------
# 评分引擎
# ---------------------------------------------------------------------------
def evaluate_project(project: Dict[str, Any],
                     weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """评估单个项目，返回完整评分结果"""
    effective_weights = _normalize_weights(weights)

    scorers = {
        "task_clarity": score_task_clarity,
        "dependency": score_dependency,
        "resource": score_resource,
        "risk_coverage": score_risk_coverage,
        "scalability": score_scalability,
    }

    dimensions = {}
    total_score = 0.0
    pending = []

    for dim_name, scorer in scorers.items():
        try:
            score, reason = scorer(project)
            if score is None:
                pending.append(dim_name)
                dimensions[dim_name] = {
                    "score": None,
                    "weight": effective_weights.get(dim_name, 0.0),
                    "weighted": None,
                    "reason": reason,
                    "status": "pending",
                }
            else:
                weighted = score * effective_weights.get(dim_name, 0.0)
                total_score += weighted
                dimensions[dim_name] = {
                    "score": score,
                    "weight": effective_weights.get(dim_name, 0.0),
                    "weighted": round(weighted, 2),
                    "reason": reason,
                    "status": "ok",
                }
        except Exception as e:
            pending.append(dim_name)
            dimensions[dim_name] = {
                "score": None,
                "weight": effective_weights.get(dim_name, 0.0),
                "weighted": None,
                "reason": f"评估失败: {str(e)}",
                "status": "error",
            }

    risk_level = None
    if not pending:
        risk_level = _get_risk_level(total_score / 100.0)

    return {
        "project_name": project["project_name"],
        "total_score": round(total_score, 2) if not pending else None,
        "risk_level": risk_level,
        "dimensions": dimensions,
        "pending_dimensions": pending,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_weights(weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    """规范化权重，确保总和为 1.0"""
    if not weights:
        return DEFAULT_WEIGHTS.copy()

    merged = DEFAULT_WEIGHTS.copy()
    for key, value in weights.items():
        if key in merged:
            try:
                merged[key] = float(value)
            except (ValueError, TypeError):
                raise InputError("E009", f"权重必须是数字: {key}")

    total = sum(merged.values())
    if total <= 0:
        raise InputError("E009", "权重总和必须大于 0")

    return {k: v / total for k, v in merged.items()}


def _get_risk_level(normalized_score: float) -> str:
    """根据归一化得分判定风险等级"""
    for level, (low, high) in RISK_THRESHOLDS.items():
        if low <= normalized_score < high:
            return level
    return "high"


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_markdown(result: Dict[str, Any]) -> str:
    """将评估结果格式化为 Markdown"""
    lines = [
        "# 项目风险评估报告",
        "",
        "## 项目信息",
        f"- 项目名称：{result['project_name']}",
        f"- 评估时间：{result['timestamp']}",
        "",
    ]

    if result["total_score"] is not None:
        lines.extend([
            "## 综合评分",
            f"- 总分：{result['total_score']} / 100",
            f"- 风险等级：{_level_name(result['risk_level'])}",
            "",
        ])
    else:
        lines.extend([
            "## 综合评分",
            "- 总分：暂无法计算（部分维度待核实）",
            "",
        ])

    lines.extend([
        "## 维度明细",
        "| 维度 | 得分 | 权重 | 加权得分 | 评估依据 |",
        "|------|------|------|----------|----------|",
    ])

    for dim_name, dim_data in result["dimensions"].items():
        dim_label = DIMENSION_NAMES.get(dim_name, dim_name)
        score_str = f"{dim_data['score']:.1f}" if dim_data["score"] is not None else "[需核实]"
        weighted_str = f"{dim_data['weighted']:.2f}" if dim_data["weighted"] is not None else "-"
        weight_str = f"{dim_data['weight'] * 100:.0f}%"
        reason = dim_data.get("reason", "")
        lines.append(f"| {dim_label} | {score_str} | {weight_str} | {weighted_str} | {reason} |")

    if result["pending_dimensions"]:
        lines.extend([
            "",
            "## 待核实维度",
        ])
        for dim in result["pending_dimensions"]:
            lines.append(f"- {DIMENSION_NAMES.get(dim, dim)}：信息不足，请补充相关数据")

    lines.extend([
        "",
        "## 风险提示",
    ])

    if result["risk_level"] == "high":
        lines.append("- 高风险：建议暂停推进，全面整改")
    elif result["risk_level"] == "medium":
        lines.append("- 中风险：建议针对性改进后推进")
    else:
        lines.append("- 低风险：可继续推进，保持监控")

    return "\n".join(lines)


def _level_name(level: Optional[str]) -> str:
    """风险等级中文名"""
    if level == "low":
        return "低风险"
    if level == "medium":
        return "中风险"
    if level == "high":
        return "高风险"
    return "未知"


def format_json(result: Dict[str, Any]) -> str:
    """将评估结果格式化为 JSON 字符串"""
    return json.dumps(result, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def process_batch(projects: List[Any],
                  weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """批量评估多个项目"""
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for item in projects:
            try:
                project = validate_project_data(item)
                future = executor.submit(evaluate_project, project, weights)
                futures.append(future)
            except InputError as e:
                results.append({
                    "project_name": "unknown",
                    "error": e.message,
                    "error_code": e.code,
                })

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "project_name": "unknown",
                    "error": str(e),
                    "error_code": "E008",
                })

    return results


# ---------------------------------------------------------------------------
# 文件写入（原子化）
# ---------------------------------------------------------------------------
def atomic_write_file(file_path: str, content: str) -> None:
    """原子化写入文件，避免写入中断导致文件损坏"""
    directory = os.path.dirname(os.path.abspath(file_path))
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("agent-workflow-kit 自检")
    print("=" * 60)

    # 测试 1：最小评估
    print("\n[测试 1] 最小评估")
    try:
        data = {"project_name": "test-project"}
        project = validate_project_data(data)
        result = evaluate_project(project)
        assert result["project_name"] == "test-project"
        assert result["total_score"] is not None
        assert result["risk_level"] in ("low", "medium", "high")
        assert len(result["dimensions"]) == 5
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 2：JSON 输出
    print("\n[测试 2] JSON 输出")
    try:
        json_str = format_json(result)
        parsed = json.loads(json_str)
        assert parsed["project_name"] == "test-project"
        assert "total_score" in parsed
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 3：Markdown 输出
    print("\n[测试 3] Markdown 输出")
    try:
        md_str = format_markdown(result)
        assert "# 项目风险评估报告" in md_str
        assert "test-project" in md_str
        assert "维度明细" in md_str
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 4：自定义权重
    print("\n[测试 4] 自定义权重")
    try:
        weights = {"task_clarity": 0.5}
        result_w = evaluate_project(project, weights)
        assert result_w["total_score"] is not None
        # 权重归一化后 task_clarity 的权重应为 0.5 / (0.5 + 0.2 + 0.2 + 0.2 + 0.15) = 0.5 / 1.25 = 0.4
        assert abs(result_w["dimensions"]["task_clarity"]["weight"] - 0.4) < 0.001
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 5：批量处理
    print("\n[测试 5] 批量处理")
    try:
        projects = [
            {"project_name": "batch-a"},
            {"project_name": "batch-b", "workflow": {"tasks": ["t1", "t2"]}},
        ]
        results = process_batch(projects)
        assert len(results) == 2
        for r in results:
            assert "project_name" in r
            assert "total_score" in r
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 6：循环依赖检测
    print("\n[测试 6] 循环依赖检测")
    try:
        deps = [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}]
        assert _has_cycle(deps) is True
        deps2 = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]
        assert _has_cycle(deps2) is False
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 7：空输入处理
    print("\n[测试 7] 空输入处理")
    try:
        try:
            validate_project_data({})
            print("  ✗ 失败: 应该抛出异常")
            return 1
        except InputError:
            print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 8：权重归一化
    print("\n[测试 8] 权重归一化")
    try:
        weights = _normalize_weights({"task_clarity": 0.5})
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 9：风险等级判定
    print("\n[测试 9] 风险等级判定")
    try:
        assert _get_risk_level(0.2) == "low"
        assert _get_risk_level(0.5) == "medium"
        assert _get_risk_level(0.8) == "high"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    # 测试 10：中文编码处理
    print("\n[测试 10] 中文编码处理")
    try:
        data_cn = {"project_name": "测试项目", "description": "这是一个中文项目描述"}
        project_cn = validate_project_data(data_cn)
        result_cn = evaluate_project(project_cn)
        assert result_cn["project_name"] == "测试项目"
        md_cn = format_markdown(result_cn)
        assert "测试项目" in md_cn
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        return 1

    print("\n" + "=" * 60)
    print("全部自检通过")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        description="agent-workflow-kit - AI 辅助软件项目评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --data '{"project_name":"demo"}'
  python run.py --data '{"project_name":"demo"}' --format json
  python run.py --file projects.json --format json
  python run.py --url https://example.com/project.json
  python run.py --data '{"project_name":"demo"}' --weights '{"task_clarity":0.3}'
  python run.py --selftest
        """,
    )

    parser.add_argument("--data", type=str, help="JSON 字符串数据")
    parser.add_argument("--file", type=str, help="JSON 文件路径")
    parser.add_argument("--url", type=str, help="远程 JSON 资源 URL")
    parser.add_argument("--format", type=str, choices=["json", "markdown"], default="markdown",
                        help="输出格式（默认: markdown）")
    parser.add_argument("--weights", type=str, help="自定义权重 JSON 字符串")
    parser.add_argument("--output", type=str, help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--verbose", action="store_true", help="详细模式，输出评估依据")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    # 先处理 selftest，不依赖任何业务参数
    if args.selftest:
        return run_selftest()

    # 解析权重
    weights = None
    if args.weights:
        try:
            weights = json.loads(args.weights)
        except json.JSONDecodeError as e:
            print(f"错误: 权重 JSON 解析失败: {str(e)}", file=sys.stderr)
            return 1

    # 创建输入对象
    workflow_input = WorkflowInput(
        data=args.data,
        file_path=args.file,
        url=args.url,
        dry_run=args.dry_run,
    )

    if not workflow_input.is_valid():
        print(f"错误: {ERROR_CODES['E002']}", file=sys.stderr)
        print("请使用 --data/--file/--url 至少提供一种数据源。", file=sys.stderr)
        return 1

    try:
        # 加载数据
        raw_data = load_input_data(workflow_input)

        # 判断是单个项目还是批量
        if isinstance(raw_data, list):
            results = process_batch(raw_data, weights)
            if args.format == "json":
                output = json.dumps(results, ensure_ascii=False, indent=2)
            else:
                output = "\n\n---\n\n".join(format_markdown(r) for r in results)
        else:
            project = validate_project_data(raw_data)
            result = evaluate_project(project, weights)

            if args.verbose:
                _print_verbose(result)

            if args.format == "json":
                output = format_json(result)
            else:
                output = format_markdown(result)

        # 输出 - R4 预览撤回：写盘必须包在 if not dry_run 分支内
        if args.output:
            if not args.dry_run:
                atomic_write_file(args.output, output)
                print(f"评估报告已写入: {args.output}")
            else:
                print(f"[dry-run] 将写入文件: {args.output}")
                print(f"[dry-run] 内容摘要: {len(output)} 字符")
        else:
            print(output)

        return 0

    except WorkflowError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {str(e)}", file=sys.stderr)
        return 1


def _print_verbose(result: Dict[str, Any]) -> None:
    """详细模式：输出每个维度的评估依据"""
    print(f"\n项目: {result['project_name']}")
    print(f"总分: {result['total_score']}")
    print(f"风险等级: {result['risk_level']}")
    print("\n维度明细:")
    for dim_name, dim_data in result["dimensions"].items():
        dim_label = DIMENSION_NAMES.get(dim_name, dim_name)
        score_str = f"{dim_data['score']:.1f}" if dim_data["score"] is not None else "[需核实]"
        print(f"  {dim_label}: {score_str}")
        if dim_data.get("reason"):
            print(f"    依据: {dim_data['reason']}")


if __name__ == "__main__":
    sys.exit(main())
