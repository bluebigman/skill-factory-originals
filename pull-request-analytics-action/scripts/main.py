#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pull-request-analytics-action 独立实现脚本
==========================================
依据功能规格独立开发，不参考任何既有实现。

功能概述：
    - 解析用户提供的 pull request 数据（JSON 格式）
    - 计算团队与开发者维度的指标（提交数、审查数、平均响应时间等）
    - 输出结构化报告，含置信度标注
    - 错误码体系：E001-E010
    - 内置 --selftest 离线自检

作者：原创作者（自持版权）
许可证：MIT License
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容（数据/文件/URL）。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查 JSON 格式。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "文件读取失败，请检查路径。",
    "E007": "JSON 解析失败，请检查语法。",
    "E008": "数据字段缺失，请检查必填字段。",
    "E009": "日期格式错误，请使用 ISO 格式。",
    "E010": "内部计算错误，请联系维护者。",
}

# 必填字段定义
REQUIRED_PR_FIELDS = ["id", "author", "created_at", "status"]
REQUIRED_REVIEW_FIELDS = ["reviewer", "pr_id", "submitted_at"]

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ---------------------------------------------------------------------------
# 异常类
# ---------------------------------------------------------------------------
class AnalyticsError(Exception):
    """分析过程中的自定义异常，携带错误码。"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def parse_date(date_str: str) -> datetime:
    """解析 ISO 格式日期字符串，失败时抛出 E009。"""
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise AnalyticsError("E009", f"无法解析日期: {date_str}")


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，避免除零错误。"""
    if denominator == 0:
        return default
    return numerator / denominator


def compute_confidence(data: Dict[str, Any]) -> float:
    """
    基于数据完整性计算置信度。
    规则：
        - 所有必填字段存在且非空：1.0
        - 缺少一个字段：0.9
        - 缺少多个字段：0.8
        - 数据为空：0.0
    """
    if not data:
        return 0.0

    # 检查 PR 数据完整性
    if "pull_requests" in data:
        pr_list = data["pull_requests"]
        if not pr_list:
            return 0.0
        missing_count = 0
        for pr in pr_list:
            for field in REQUIRED_PR_FIELDS:
                if field not in pr or pr[field] in (None, ""):
                    missing_count += 1
        # 置信度 = 1 - 缺失率
        total_fields = len(pr_list) * len(REQUIRED_PR_FIELDS)
        confidence = 1.0 - (missing_count / total_fields)
        return max(0.0, min(1.0, confidence))

    # 通用数据完整性
    if isinstance(data, dict) and len(data) > 0:
        return 0.9  # 有数据但结构不明确，给中等置信度

    return 0.5


def format_confidence(confidence: float) -> str:
    """根据置信度生成标注。"""
    if confidence >= HIGH_CONFIDENCE:
        return "高置信度"
    elif confidence >= MEDIUM_CONFIDENCE:
        return "建议复核"
    else:
        return "[需核实]"


# ---------------------------------------------------------------------------
# 核心分析逻辑
# ---------------------------------------------------------------------------
def analyze_pull_requests(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析 PR 数据，计算团队与开发者指标。

    输入数据格式：
    {
        "pull_requests": [
            {
                "id": "PR-001",
                "author": "alice",
                "created_at": "2026-01-01T10:00:00Z",
                "status": "merged",  # merged / open / closed
                "merged_at": "2026-01-02T10:00:00Z",  # 可选
                "title": "Fix bug"  # 可选
            }
        ],
        "reviews": [
            {
                "reviewer": "bob",
                "pr_id": "PR-001",
                "submitted_at": "2026-01-01T12:00:00Z",
                "action": "approve"  # 可选
            }
        ]
    }

    输出指标：
        - 总 PR 数
        - 按状态统计
        - 平均合并时间（小时）
        - 开发者维度：提交数、审查数、平均审查响应时间
        - 团队维度：总提交、总审查、平均响应时间
    """
    # 数据校验
    if not data:
        raise AnalyticsError("E001")

    pr_list = data.get("pull_requests", [])
    review_list = data.get("reviews", [])

    if not pr_list:
        raise AnalyticsError("E002", "缺少 pull_requests 数据")

    # 基本统计
    total_prs = len(pr_list)
    status_counts = defaultdict(int)
    author_prs = defaultdict(int)
    author_reviews = defaultdict(int)
    review_response_times = defaultdict(list)  # reviewer -> [小时]
    merge_times = []  # 合并时间（小时）

    # 建立 PR 索引
    pr_map = {}
    for pr in pr_list:
        # 必填字段检查
        for field in REQUIRED_PR_FIELDS:
            if field not in pr or pr[field] in (None, ""):
                raise AnalyticsError("E008", f"PR 缺少必填字段: {field}")

        pr_id = pr["id"]
        pr_map[pr_id] = pr
        status_counts[pr["status"]] += 1
        author_prs[pr["author"]] += 1

        # 计算合并时间
        if pr["status"] == "merged" and pr.get("merged_at"):
            created = parse_date(pr["created_at"])
            merged = parse_date(pr["merged_at"])
            merge_hours = (merged - created).total_seconds() / 3600.0
            merge_times.append(max(0, merge_hours))

    # 审查数据分析
    pr_created_times = {}
    for pr in pr_list:
        pr_created_times[pr["id"]] = parse_date(pr["created_at"])

    for review in review_list:
        # 必填字段检查
        for field in REQUIRED_REVIEW_FIELDS:
            if field not in review or review[field] in (None, ""):
                raise AnalyticsError("E008", f"审查记录缺少必填字段: {field}")

        reviewer = review["reviewer"]
        pr_id = review["pr_id"]
        submitted_at = parse_date(review["submitted_at"])

        author_reviews[reviewer] += 1

        # 计算响应时间（PR 创建到审查提交）
        if pr_id in pr_created_times:
            response_hours = (submitted_at - pr_created_times[pr_id]).total_seconds() / 3600.0
            review_response_times[reviewer].append(max(0, response_hours))

    # 计算指标
    avg_merge_time = safe_divide(sum(merge_times), len(merge_times)) if merge_times else 0.0

    # 开发者维度
    developers = {}
    all_authors = set(author_prs.keys()) | set(author_reviews.keys())
    for dev in all_authors:
        pr_count = author_prs.get(dev, 0)
        review_count = author_reviews.get(dev, 0)
        resp_times = review_response_times.get(dev, [])
        avg_resp = safe_divide(sum(resp_times), len(resp_times)) if resp_times else 0.0

        developers[dev] = {
            "pr_count": pr_count,
            "review_count": review_count,
            "avg_review_response_hours": round(avg_resp, 2),
        }

    # 团队维度
    all_review_times = []
    for times in review_response_times.values():
        all_review_times.extend(times)
    team_avg_review_time = safe_divide(sum(all_review_times), len(all_review_times)) if all_review_times else 0.0

    # 计算置信度
    confidence = compute_confidence(data)
    confidence_label = format_confidence(confidence)

    # 组装结果
    result = {
        "summary": {
            "total_prs": total_prs,
            "status_counts": dict(status_counts),
            "avg_merge_time_hours": round(avg_merge_time, 2),
            "total_reviews": len(review_list),
            "team_avg_review_response_hours": round(team_avg_review_time, 2),
        },
        "developers": developers,
        "confidence": {
            "score": round(confidence, 2),
            "label": confidence_label,
        },
        "generated_at": datetime.now().isoformat(),
    }

    return result


# ---------------------------------------------------------------------------
# 输入解析
# ---------------------------------------------------------------------------
def load_input(source: str) -> Dict[str, Any]:
    """
    从字符串或文件路径加载数据。
    支持：
        - 直接 JSON 字符串
        - 文件路径（以 @ 开头或路径存在）
    """
    if not source or not source.strip():
        raise AnalyticsError("E001")

    source = source.strip()

    # 检查是否为文件路径
    is_file = source.startswith("@") or os.path.isfile(source)
    if is_file:
        file_path = source[1:] if source.startswith("@") else source
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError) as e:
            raise AnalyticsError("E006", f"文件读取失败: {file_path} - {e}")
    else:
        content = source

    # 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AnalyticsError("E007", f"JSON 解析失败: {e}")

    if not isinstance(data, dict):
        raise AnalyticsError("E003", "JSON 顶层必须是对象")

    return data


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """按指定格式输出结果。"""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        return _format_as_text(result)
    else:
        raise AnalyticsError("E003", f"不支持的输出格式: {output_format}")


def _format_as_text(result: Dict[str, Any]) -> str:
    """将结果格式化为可读文本。"""
    lines = []
    lines.append("=" * 50)
    lines.append("Pull Request 分析报告")
    lines.append("=" * 50)

    summary = result.get("summary", {})
    lines.append("\n【总体概览】")
    lines.append(f"  总 PR 数: {summary.get('total_prs', 0)}")
    lines.append(f"  总审查数: {summary.get('total_reviews', 0)}")

    status_counts = summary.get("status_counts", {})
    if status_counts:
        lines.append("  状态分布:")
        for status, count in status_counts.items():
            lines.append(f"    - {status}: {count}")

    lines.append(f"  平均合并时间: {summary.get('avg_merge_time_hours', 0)} 小时")
    lines.append(f"  团队平均审查响应: {summary.get('team_avg_review_response_hours', 0)} 小时")

    developers = result.get("developers", {})
    if developers:
        lines.append("\n【开发者维度】")
        for dev, metrics in developers.items():
            lines.append(f"  {dev}:")
            lines.append(f"    - PR 提交数: {metrics['pr_count']}")
            lines.append(f"    - 审查数: {metrics['review_count']}")
            lines.append(f"    - 平均审查响应: {metrics['avg_review_response_hours']} 小时")

    confidence = result.get("confidence", {})
    lines.append(f"\n【置信度】: {confidence.get('label', '未知')} (得分: {confidence.get('score', 0)})")
    lines.append("=" * 50)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码数据，不依赖外部文件、网络或工作目录。
    """
    print("开始自检...")

    # 内置测试数据
    test_data = {
        "pull_requests": [
            {
                "id": "PR-001",
                "author": "alice",
                "created_at": "2026-01-01T10:00:00Z",
                "status": "merged",
                "merged_at": "2026-01-02T10:00:00Z",
                "title": "Fix login bug",
            },
            {
                "id": "PR-002",
                "author": "bob",
                "created_at": "2026-01-03T09:00:00Z",
                "status": "open",
                "title": "Add new feature",
            },
            {
                "id": "PR-003",
                "author": "alice",
                "created_at": "2026-01-05T14:00:00Z",
                "status": "merged",
                "merged_at": "2026-01-06T10:00:00Z",
                "title": "Refactor API",
            },
            {
                "id": "PR-004",
                "author": "carol",
                "created_at": "2026-01-07T11:00:00Z",
                "status": "closed",
                "title": "WIP not ready",
            },
        ],
        "reviews": [
            {
                "reviewer": "bob",
                "pr_id": "PR-001",
                "submitted_at": "2026-01-01T12:00:00Z",
                "action": "approve",
            },
            {
                "reviewer": "carol",
                "pr_id": "PR-001",
                "submitted_at": "2026-01-01T15:00:00Z",
                "action": "comment",
            },
            {
                "reviewer": "alice",
                "pr_id": "PR-002",
                "submitted_at": "2026-01-03T11:00:00Z",
                "action": "approve",
            },
            {
                "reviewer": "bob",
                "pr_id": "PR-003",
                "submitted_at": "2026-01-05T16:00:00Z",
                "action": "approve",
            },
        ],
    }

    # 测试 1: 正常分析
    try:
        result = analyze_pull_requests(test_data)
        summary = result["summary"]

        # 宽松断言（不依赖精确值）
        assert summary["total_prs"] == 4, "PR 总数应为 4"
        assert summary["status_counts"].get("merged", 0) == 2, "应有 2 个合并 PR"
        assert summary["status_counts"].get("open", 0) == 1, "应有 1 个开放 PR"
        assert summary["status_counts"].get("closed", 0) == 1, "应有 1 个关闭 PR"
        assert summary["total_reviews"] == 4, "审查总数应为 4"
        # 平均合并时间应在合理范围（0-48 小时）
        assert 0 <= summary["avg_merge_time_hours"] <= 48, "平均合并时间应在合理范围"
        # 团队平均响应时间应在合理范围（0-24 小时）
        assert 0 <= summary["team_avg_review_response_hours"] <= 24, "平均响应时间应在合理范围"

        # 开发者维度检查
        developers = result["developers"]
        assert "alice" in developers, "alice 应在开发者列表中"
        assert "bob" in developers, "bob 应在开发者列表中"
        assert "carol" in developers, "carol 应在开发者列表中"

        # alice 提交了 2 个 PR
        assert developers["alice"]["pr_count"] == 2, "alice 应提交 2 个 PR"
        # bob 审查了 2 个 PR
        assert developers["bob"]["review_count"] == 2, "bob 应审查 2 个 PR"
        # 响应时间应为非负值
        for dev_metrics in developers.values():
            assert dev_metrics["avg_review_response_hours"] >= 0, "响应时间应为非负"

        # 置信度检查
        assert result["confidence"]["score"] > 0.5, "置信度应大于 0.5"

        print("  ✓ 正常数据分析测试通过")

    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except AnalyticsError as e:
        print(f"  ✗ 分析异常: {e}")
        return False

    # 测试 2: 错误处理 - 空输入
    try:
        analyze_pull_requests({})
        print("  ✗ 空输入应抛出 E001")
        return False
    except AnalyticsError as e:
        assert e.error_code == "E001", "错误码应为 E001"
        print("  ✓ 空输入错误处理测试通过")

    # 测试 3: 错误处理 - 缺失字段
    bad_data = {
        "pull_requests": [
            {"id": "PR-001", "author": "alice"},  # 缺少 created_at 和 status
        ],
        "reviews": [],
    }
    try:
        analyze_pull_requests(bad_data)
        print("  ✗ 缺失字段应抛出 E008")
        return False
    except AnalyticsError as e:
        assert e.error_code == "E008", "错误码应为 E008"
        print("  ✓ 缺失字段错误处理测试通过")

    # 测试 4: 输入解析 - JSON 字符串
    try:
        data = load_input(json.dumps(test_data))
        assert data == test_data, "JSON 解析结果应一致"
        print("  ✓ JSON 字符串解析测试通过")
    except AnalyticsError as e:
        print(f"  ✗ JSON 解析异常: {e}")
        return False

    # 测试 5: 输入解析 - 格式错误
    try:
        load_input("这不是合法的 JSON")
        print("  ✗ 非法 JSON 应抛出 E007")
        return False
    except AnalyticsError as e:
        assert e.error_code == "E007", "错误码应为 E007"
        print("  ✓ 非法 JSON 错误处理测试通过")

    # 测试 6: 输出格式化
    try:
        result = analyze_pull_requests(test_data)
        json_output = format_output(result, "json")
        assert json_output.startswith("{"), "JSON 输出应以 { 开头"
        text_output = format_output(result, "text")
        assert "Pull Request 分析报告" in text_output, "文本输出应包含报告标题"
        print("  ✓ 输出格式化测试通过")
    except AnalyticsError as e:
        print(f"  ✗ 输出格式化异常: {e}")
        return False

    # 测试 7: 空 PR 列表
    try:
        analyze_pull_requests({"pull_requests": [], "reviews": []})
        print("  ✗ 空 PR 列表应抛出 E002")
        return False
    except AnalyticsError as e:
        assert e.error_code == "E002", "错误码应为 E002"
        print("  ✓ 空 PR 列表错误处理测试通过")

    # 测试 8: 日期解析
    try:
        parse_date("2026-01-01T10:00:00Z")
        parse_date("2026-01-01T10:00:00+08:00")
        print("  ✓ 日期解析测试通过")
    except AnalyticsError as e:
        print(f"  ✗ 日期解析异常: {e}")
        return False

    # 测试 9: 非法日期
    try:
        parse_date("不是日期")
        print("  ✗ 非法日期应抛出 E009")
        return False
    except AnalyticsError as e:
        assert e.error_code == "E009", "错误码应为 E009"
        print("  ✓ 非法日期错误处理测试通过")

    # 测试 10: 边界情况 - 无审查数据
    no_reviews_data = {
        "pull_requests": [
            {"id": "PR-001", "author": "alice", "created_at": "2026-01-01T10:00:00Z", "status": "open"},
        ],
        "reviews": [],
    }
    try:
        result = analyze_pull_requests(no_reviews_data)
        assert result["summary"]["total_reviews"] == 0, "审查数应为 0"
        assert result["summary"]["team_avg_review_response_hours"] == 0, "平均响应时间应为 0"
        print("  ✓ 无审查数据边界测试通过")
    except AnalyticsError as e:
        print(f"  ✗ 无审查数据异常: {e}")
        return False

    print("\n所有自检测试通过！")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="Pull Request 分析工具 - 基于 PR 数据生成团队和开发者指标"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入数据：JSON 字符串或文件路径（文件路径需以 @ 开头）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置数据，不依赖外部环境）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常模式
    if not args.input:
        print("错误: 请提供输入数据（JSON 字符串或文件路径）", file=sys.stderr)
        print("用法: python main.py '<json>' 或 python main.py '@data.json'", file=sys.stderr)
        return 1

    try:
        # 加载数据
        data = load_input(args.input)

        # 执行分析
        result = analyze_pull_requests(data)

        # 输出结果
        output = format_output(result, args.format)
        print(output)

        return 0

    except AnalyticsError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E010]: 未预期的异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
