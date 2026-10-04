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
dry_run = False  # v3.274 模块级 dry-run 标志


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

    def __init__(self, code: str = "E001", message: str = "输入数据为空或格式错误"):
        super().__init__(code, message)


class SourceTypeError(WorkflowError):
    """数据源类型错误"""

    def __init__(self, code: str = "E003", message: str = "数据源类型不支持"):
        super().__init__(code, message)


class URLError(WorkflowError):
    """URL 获取错误"""

    def __init__(self, code: str = "E011", message: str = "URL 获取失败"):
        super().__init__(code, message)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def utc_now_str() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """校验并规范化权重字典"""
    if not weights:
        return DEFAULT_WEIGHTS.copy()

    # 只保留支持的维度
    valid_weights = {k: v for k, v in weights.items() if k in DEFAULT_WEIGHTS}

    # 归一化
    total = sum(valid_weights.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()

    return {k: v / total for k, v in valid_weights.items()}


def atomic_write_file(filepath: str, content: str) -> None:
    """原子化写入文件"""
    dirname = os.path.dirname(filepath)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dirname or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# 数据获取
# ---------------------------------------------------------------------------
def fetch_data_from_url(url: str) -> Dict[str, Any]:
    """从 URL 获取 JSON 数据，带超时和指数退避重试"""
    last_error: Optional[Exception] = None

    for attempt in range(URL_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agent-workflow-kit/2.1.0"})
            with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
            last_error = e
            if attempt < URL_MAX_RETRIES - 1:
                time.sleep(URL_RETRY_BACKOFF * (2 ** attempt))

    raise URLError(message=f"URL 获取失败: {url}, 错误: {last_error}")


def load_input_data(args: argparse.Namespace) -> Dict[str, Any]:
    """加载输入数据"""
    if args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            raise InputError(message=f"JSON 解析失败: {e}")
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise InputError(message=f"文件读取失败: {e}")
    elif args.url:
        data = fetch_data_from_url(args.url)
    else:
        raise InputError(code="E002", message="缺少必要字段（data/file/url 至少一项）")

    if not data or not isinstance(data, dict):
        raise InputError(message="输入数据为空或格式错误")

    return data


# ---------------------------------------------------------------------------
# 核心评估逻辑
# ---------------------------------------------------------------------------
def validate_input_data(data: Dict[str, Any]) -> None:
    """校验输入数据的基本结构"""
    if "project" not in data:
        raise InputError(message="缺少必要字段: project")

    if "steps" not in data:
        raise InputError(message="缺少必要字段: steps")

    if not isinstance(data["steps"], list) or len(data["steps"]) == 0:
        raise InputError(message="steps 必须是非空列表")

    if len(data["steps"]) < 2:
        raise InputError(message="评估维度不足，至少需要 2 个步骤")


def calculate_dimension_scores(data: Dict[str, Any]) -> Dict[str, float]:
    """计算各维度得分"""
    steps = data.get("steps", [])
    total_steps = len(steps)

    if total_steps == 0:
        raise InputError(message="steps 列表为空")

    # 任务清晰度: 步骤名称完整性和描述完整性
    task_clarity_scores = []
    for step in steps:
        score = 0.0
        if step.get("name"):
            score += 50.0
        if step.get("description"):
            score += 50.0
        elif step.get("duration") is not None:
            score += 30.0
        task_clarity_scores.append(score)
    task_clarity = sum(task_clarity_scores) / len(task_clarity_scores) if task_clarity_scores else 0.0

    # 依赖合理性: 检查依赖关系
    dependency_scores = []
    for i, step in enumerate(steps):
        score = 100.0
        if i > 0 and not step.get("depends_on") and not step.get("previous"):
            score -= 20.0  # 缺少依赖声明
        if step.get("depends_on") and not isinstance(step["depends_on"], list):
            score -= 30.0  # 依赖格式错误
        dependency_scores.append(max(0.0, score))
    dependency = sum(dependency_scores) / len(dependency_scores) if dependency_scores else 0.0

    # 资源分配: 检查时长和资源分配
    resource_scores = []
    for step in steps:
        score = 100.0
        duration = safe_float(step.get("duration"), 0.0)
        if duration <= 0:
            score -= 40.0  # 缺少时长
        if step.get("resources") is None and step.get("assignee") is None:
            score -= 20.0  # 缺少资源分配
        resource_scores.append(max(0.0, score))
    resource = sum(resource_scores) / len(resource_scores) if resource_scores else 0.0

    # 风险覆盖: 检查风险标记和 AI 参与度
    risk_scores = []
    for step in steps:
        score = 100.0
        if step.get("risk") is None and step.get("ai_involved") is None:
            score -= 30.0  # 缺少风险标记
        if step.get("ai_involved") is True and step.get("review_required") is None:
            score -= 20.0  # AI 参与但无审查要求
        risk_scores.append(max(0.0, score))
    risk_coverage = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

    # 可扩展性: 检查步骤的模块化程度
    scalability_scores = []
    for step in steps:
        score = 100.0
        if not step.get("outputs") and not step.get("deliverables"):
            score -= 30.0  # 缺少输出定义
        if not step.get("inputs") and not step.get("depends_on"):
            score -= 20.0  # 缺少输入定义
        scalability_scores.append(max(0.0, score))
    scalability = sum(scalability_scores) / len(scalability_scores) if scalability_scores else 0.0

    return {
        "task_clarity": task_clarity,
        "dependency": dependency,
        "resource": resource,
        "risk_coverage": risk_coverage,
        "scalability": scalability,
    }


def calculate_overall_score(dimension_scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """计算综合评分"""
    total = 0.0
    for dim, score in dimension_scores.items():
        total += score * weights.get(dim, 0.0)
    return round(total, 1)


def determine_risk_level(overall_score: float) -> str:
    """根据综合评分确定风险等级"""
    normalized_score = overall_score / 100.0

    for level, (low, high) in RISK_THRESHOLDS.items():
        if low <= normalized_score < high:
            return level

    return "high"  # 默认高风险


def generate_confidence_flags(data: Dict[str, Any]) -> Tuple[List[str], bool]:
    """生成置信度标记"""
    flags = []
    steps = data.get("steps", [])

    for i, step in enumerate(steps):
        if step.get("duration") is None:
            flags.append(f"[需核实:steps[{i}].duration]")
        if step.get("ai_involved") is None:
            flags.append(f"[需核实:steps[{i}].ai_involved]")
        if step.get("name") is None:
            flags.append(f"[需核实:steps[{i}].name]")

    return flags, len(flags) > 0


def generate_recommendations(data: Dict[str, Any], dimension_scores: Dict[str, float]) -> List[str]:
    """生成改进建议"""
    recommendations = []
    steps = data.get("steps", [])

    # 基于维度得分
    for dim, score in dimension_scores.items():
        if score < 50.0:
            recommendations.append(f"改进{ DIMENSION_NAMES.get(dim, dim)}: 当前得分 {score:.1f}/100")

    # 基于具体数据
    for i, step in enumerate(steps):
        if step.get("duration") is None:
            recommendations.append(f"补充步骤 {i} ({step.get('name', '未知')}) 的时长记录")
        if step.get("ai_involved") is True and step.get("review_required") is None:
            recommendations.append(f"为 AI 参与的步骤 {i} ({step.get('name', '未知')}) 添加人工审查要求")

    return recommendations[:5]  # 最多返回 5 条建议


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------
def generate_json_report(data: Dict[str, Any], dimension_scores: Dict[str, float],
                         overall_score: float, risk_level: str,
                         confidence_flags: List[str], gated: bool,
                         recommendations: List[str]) -> Dict[str, Any]:
    """生成 JSON 格式报告"""
    return {
        "meta": {
            "tool": "agent-workflow-kit",
            "version": "2.1.0",
            "timestamp": utc_now_str(),
        },
        "input_summary": {
            "project": data.get("project", "unknown"),
            "steps_count": len(data.get("steps", [])),
            "dimensions_covered": len(dimension_scores),
        },
        "scores": {
            "dimension_scores": {k: round(v, 1) for k, v in dimension_scores.items()},
            "overall_score": overall_score,
            "risk_level": risk_level,
        },
        "confidence": {
            "flags": confidence_flags,
            "gated": gated,
        },
        "recommendations": recommendations,
    }


def generate_markdown_report(report: Dict[str, Any]) -> str:
    """生成 Markdown 格式报告"""
    lines = [
        "# 工作流质量评估报告",
        "",
        "## 项目信息",
        f"- 项目名称：{report['input_summary']['project']}",
        f"- 评估时间：{report['meta']['timestamp']}",
        f"- 工具版本：{report['meta']['version']}",
        "",
        "## 综合评分",
        f"- 总分：{report['scores']['overall_score']} / 100",
        f"- 风险等级：{report['scores']['risk_level']}",
        "",
        "## 维度得分",
        "| 维度 | 得分 | 说明 |",
        "|------|------|------|",
    ]

    for dim, score in report["scores"]["dimension_scores"].items():
        lines.append(f"| {DIMENSION_NAMES.get(dim, dim)} | {score} | {_get_dimension_comment(dim, score)} |")

    lines.extend([
        "",
        "## 置信度标记",
    ])

    if report["confidence"]["flags"]:
        for flag in report["confidence"]["flags"]:
            lines.append(f"- ⚠️ {flag}")
    else:
        lines.append("- ✅ 数据完整，无置信度问题")

    lines.extend([
        "",
        "## 改进建议",
    ])

    if report["recommendations"]:
        for rec in report["recommendations"]:
            lines.append(f"- {rec}")
    else:
        lines.append("- 当前工作流质量良好，无需改进")

    return "\n".join(lines)


def _get_dimension_comment(dim: str, score: float) -> str:
    """获取维度得分说明"""
    if score >= 80:
        return "优秀"
    elif score >= 60:
        return "良好"
    elif score >= 40:
        return "一般"
    else:
        return "需改进"


# ---------------------------------------------------------------------------
# 输出处理
# ---------------------------------------------------------------------------
def write_reports(report: Dict[str, Any], output_dir: str, dry_run: bool = False) -> Tuple[str, str]:
    """写入报告文件，返回文件路径"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(output_dir, f"report_{timestamp}.json")
    md_path = os.path.join(output_dir, f"report_{timestamp}.md")

    json_content = json.dumps(report, ensure_ascii=False, indent=2)
    md_content = generate_markdown_report(report)

    if not dry_run:
        atomic_write_file(json_path, json_content)
        atomic_write_file(md_path, md_content)
        print(f"JSON 报告已写入: {json_path}")
        print(f"Markdown 报告已写入: {md_path}")
    else:
        print(f"[DRY-RUN] 将写入 JSON 报告: {json_path}")
        print(f"[DRY-RUN] 将写入 Markdown 报告: {md_path}")
        print(f"[DRY-RUN] JSON 报告大小: {len(json_content)} 字节")
        print(f"[DRY-RUN] Markdown 报告大小: {len(md_content)} 字节")

    return json_path, md_path


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def process_single_file(filepath: str, args: argparse.Namespace) -> Tuple[str, bool, str]:
    """处理单个文件，返回 (文件路径, 是否成功, 错误信息)"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        result = evaluate_workflow(data, args.weights)
        report = result["report"]

        if args.output:
            output_dir = args.output
        else:
            output_dir = os.path.dirname(filepath) or "."

        write_reports(report, output_dir, args.dry_run)
        return filepath, True, ""
    except Exception as e:
        return filepath, False, str(e)


def process_batch(files: List[str], args: argparse.Namespace) -> None:
    """批量处理多个文件"""
    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_file, f, args): f for f in files}
        for future in as_completed(futures):
            filepath, success, error = future.result()
            if success:
                success_count += 1
                print(f"✓ 成功: {filepath}")
            else:
                fail_count += 1
                print(f"✗ 失败: {filepath} - {error}")

    print(f"\n批量处理完成: {len(files)} 个文件, {success_count} 个成功, {fail_count} 个失败")
    if fail_count > 0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# 主评估流程
# ---------------------------------------------------------------------------
def evaluate_workflow(data: Dict[str, Any], weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """执行完整的工作流评估"""
    # 校验输入
    validate_input_data(data)

    # 计算维度得分
    dimension_scores = calculate_dimension_scores(data)

    # 计算综合评分
    valid_weights = validate_weights(weights or {})
    overall_score = calculate_overall_score(dimension_scores, valid_weights)

    # 确定风险等级
    risk_level = determine_risk_level(overall_score)

    # 生成置信度标记
    confidence_flags, gated = generate_confidence_flags(data)

    # 生成建议
    recommendations = generate_recommendations(data, dimension_scores)

    # 生成报告
    report = generate_json_report(
        data, dimension_scores, overall_score, risk_level,
        confidence_flags, gated, recommendations
    )

    return {
        "report": report,
        "dimension_scores": dimension_scores,
        "overall_score": overall_score,
        "risk_level": risk_level,
    }


# ---------------------------------------------------------------------------
# 自检模式
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行自检，验证工具功能正常"""
    print("=" * 60)
    print("agent-workflow-kit 自检模式")
    print("=" * 60)

    # 测试用例 1: 正常数据
    print("\n[测试 1] 正常数据评估")
    test_data_1 = {
        "project": "selftest",
        "steps": [
            {"name": "需求分析", "duration": 3, "ai_involved": True},
            {"name": "代码生成", "duration": 5, "ai_involved": True},
            {"name": "人工审查", "duration": 2, "ai_involved": False},
        ]
    }
    try:
        result = evaluate_workflow(test_data_1)
        assert result["overall_score"] > 0, "综合评分应为正数"
        assert result["risk_level"] in ("low", "medium", "high"), "风险等级无效"
        assert len(result["report"]["scores"]["dimension_scores"]) == 5, "应有 5 个维度得分"
        print(f"  ✓ 通过 (总分: {result['overall_score']}, 风险: {result['risk_level']})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 2: 数据不完整触发置信度门控
    print("\n[测试 2] 置信度门控")
    test_data_2 = {
        "project": "selftest",
        "steps": [
            {"name": "需求分析", "ai_involved": True},
            {"name": "代码生成", "duration": 5},
        ]
    }
    try:
        result = evaluate_workflow(test_data_2)
        assert result["report"]["confidence"]["gated"] is True, "应触发置信度门控"
        assert len(result["report"]["confidence"]["flags"]) > 0, "应有置信度标记"
        print(f"  ✓ 通过 (标记数: {len(result['report']['confidence']['flags'])})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 3: 空数据应报错
    print("\n[测试 3] 空数据报错")
    try:
        evaluate_workflow({})
        print("  ✗ 失败: 空数据应报错")
        return 1
    except InputError:
        print("  ✓ 通过 (正确报错)")

    # 测试用例 4: 缺少关键字段应报错
    print("\n[测试 4] 缺少关键字段报错")
    try:
        evaluate_workflow({"project": "test"})
        print("  ✗ 失败: 缺少 steps 应报错")
        return 1
    except InputError:
        print("  ✓ 通过 (正确报错)")

    # 测试用例 5: 中文编码处理
    print("\n[测试 5] 中文编码处理")
    test_data_5 = {
        "project": "中文项目",
        "steps": [
            {"name": "需求分析", "duration": 3, "ai_involved": True},
            {"name": "代码生成", "duration": 5, "ai_involved": True},
        ]
    }
    try:
        result = evaluate_workflow(test_data_5)
        md_content = generate_markdown_report(result["report"])
        assert "中文项目" in md_content, "Markdown 报告应包含中文项目名"
        print("  ✓ 通过 (中文处理正常)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 6: 权重自定义
    print("\n[测试 6] 自定义权重")
    custom_weights = {"task_clarity": 0.5, "dependency": 0.5}
    try:
        result = evaluate_workflow(test_data_1, custom_weights)
        assert result["overall_score"] > 0, "自定义权重下综合评分应为正数"
        print(f"  ✓ 通过 (总分: {result['overall_score']})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 7: 批量处理
    print("\n[测试 7] 批量处理")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "test1.json")
            file2 = os.path.join(tmpdir, "test2.json")
            with open(file1, "w", encoding="utf-8") as f:
                json.dump(test_data_1, f)
            with open(file2, "w", encoding="utf-8") as f:
                json.dump(test_data_2, f)

            batch_args = argparse.Namespace(
                weights=None, output=tmpdir, dry_run=True
            )
            process_batch([file1, file2], batch_args)
        print("  ✓ 通过 (批量处理正常)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 8: URL 获取（模拟）
    print("\n[测试 8] URL 获取错误处理")
    try:
        fetch_data_from_url("http://invalid-url-12345.com/data.json")
        print("  ✗ 失败: 无效 URL 应报错")
        return 1
    except URLError:
        print("  ✓ 通过 (正确报错)")

    print("\n" + "=" * 60)
    print("自检完成: 全部测试通过")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="agent-workflow-kit: AI辅助项目工作流质量评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --data '{"project":"demo","steps":[{"name":"需求分析","duration":3,"ai_involved":true}]}'
  python run.py --file workflow.json
  python run.py --url https://example.com/workflow.json
  python run.py --batch file1.json file2.json
  python run.py --selftest
        """
    )

    # 数据源参数（互斥）
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--data", type=str, help="JSON 格式的输入数据字符串")
    source_group.add_argument("--file", type=str, help="JSON 格式的输入文件路径")
    source_group.add_argument("--url", type=str, help="JSON 数据的 URL 地址")

    # 其他参数
    parser.add_argument("--batch", nargs="+", help="批量处理多个文件或目录")
    parser.add_argument("--output", "-o", type=str, default="./reports", help="报告输出目录 (默认: ./reports)")
    parser.add_argument("--format", choices=["json", "markdown", "both"], default="both", help="输出格式 (默认: both)")
    parser.add_argument("--weights", type=str, help="自定义权重 JSON 字符串")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘，只打印将生成的内容")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细评估过程")
    parser.add_argument("--version", action="version", version="agent-workflow-kit 2.1.0")
    parser.add_argument("--selftest", action="store_true", help="运行自检模式")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量处理模式
    if args.batch:
        files = []
        for item in args.batch:
            if os.path.isdir(item):
                for root, _, filenames in os.walk(item):
                    for filename in filenames:
                        if filename.endswith(".json"):
                            files.append(os.path.join(root, filename))
            elif os.path.isfile(item):
                files.append(item)
            else:
                print(f"错误: 路径不存在: {item}")
                return 1

        if not files:
            print("错误: 未找到任何 JSON 文件")
            return 1

        process_batch(files, args)
        return 0

    # 解析权重
    weights = None
    if args.weights:
        try:
            weights = json.loads(args.weights)
        except json.JSONDecodeError as e:
            print(f"错误: 权重 JSON 解析失败: {e}")
            return 1

    # 加载输入数据
    try:
        data = load_input_data(args)
    except WorkflowError as e:
        print(f"错误: {e}")
        return 1

    # 执行评估
    try:
        result = evaluate_workflow(data, weights)
    except WorkflowError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"错误: [E010] 未知内部错误: {e}")
        return 1

    report = result["report"]

    # 详细输出
    if args.verbose:
        print("\n" + "=" * 60)
        print("详细评估过程")
        print("=" * 60)
        print(f"项目: {report['input_summary']['project']}")
        print(f"步骤数: {report['input_summary']['steps_count']}")
        print(f"维度覆盖: {report['input_summary']['dimensions_covered']}")
        print("\n维度得分:")
        for dim, score in report["scores"]["dimension_scores"].items():
            print(f"  {DIMENSION_NAMES.get(dim, dim)}: {score:.1f}/100")
        print(f"\n综合评分: {report['scores']['overall_score']}/100")
        print(f"风险等级: {report['scores']['risk_level']}")
        if report["confidence"]["flags"]:
            print("\n置信度标记:")
            for flag in report["confidence"]["flags"]:
                print(f"  ⚠️ {flag}")
        if report["recommendations"]:
            print("\n改进建议:")
            for rec in report["recommendations"]:
                print(f"  - {rec}")

    # 输出摘要
    print(f"\n项目: {report['input_summary']['project']} | "
          f"步骤数: {report['input_summary']['steps_count']} | "
          f"总分: {report['scores']['overall_score']}/100 | "
          f"风险等级: {report['scores']['risk_level']}")

    # 写入报告
    try:
        write_reports(report, args.output, args.dry_run)
    except Exception as e:
        print(f"错误: 报告写入失败: {e}")
        return 1

    # 高风险时返回非零退出码
    if report["scores"]["risk_level"] == "high":
        print("\n警告: 高风险项目，建议立即改进")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())


def read_text_safe(path):
    """多编码容错读取 (selftest contract)"""
    import codecs
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with codecs.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()
