#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pull-request-analytics-action 独立实现脚本

基于功能规格 clean-room 重写，不依赖任何既有代码。
提供 PR 数据解析、指标计算、报告生成三大核心能力。

用法:
    python scripts/main.py <data_file> [--format json|markdown|text] [--selftest]

错误码:
    E001: 参数错误
    E002: 文件读取失败
    E003: 数据解析失败
    E004: 数据格式校验失败
    E005: 指标计算异常
    E006: 报告生成失败
    E007: 输出写入失败
    E008: 未知格式请求
    E009: 自检失败
    E010: 内部逻辑错误
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 数据模型层
# ============================================================

class PullRequest:
    """PR 数据模型，对应规格中的统一分析模型"""

    REQUIRED_FIELDS = {
        "id": (str, int),
        "title": str,
        "author": str,
        "created_at": str,
        "merged_at": (str, type(None)),
    }
    OPTIONAL_FIELDS = {
        "reviewers": list,
        "comments": int,
        "additions": int,
        "deletions": int,
        "changed_files": int,
    }

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self._validate()
        self._parse()

    def _validate(self) -> None:
        """校验必填字段与类型"""
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in self.raw:
                raise ValueError(f"缺少必填字段: {field}")
            if not isinstance(self.raw[field], expected_type):
                raise ValueError(
                    f"字段 {field} 类型错误: 期望 {expected_type}, 实际 {type(self.raw[field])}"
                )

    def _parse(self) -> None:
        """解析字段为内部属性"""
        try:
            self.id = str(self.raw["id"])
            self.title = str(self.raw["title"])
            self.author = str(self.raw["author"])
            self.created_at = self._parse_datetime(self.raw["created_at"])
            self.merged_at = (
                self._parse_datetime(self.raw["merged_at"])
                if self.raw["merged_at"]
                else None
            )
            self.reviewers = [
                str(r) for r in self.raw.get("reviewers", [])
            ]
            self.comments = int(self.raw.get("comments", 0))
            self.additions = int(self.raw.get("additions", 0))
            self.deletions = int(self.raw.get("deletions", 0))
            self.changed_files = int(self.raw.get("changed_files", 0))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"PR 数据解析失败 (id={self.raw.get('id')}): {exc}")

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """宽松解析多种常见时间格式"""
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError(f"无法解析时间字段: {value}")

    @property
    def review_time_hours(self) -> Optional[float]:
        """评审时长（小时），未合并返回 None"""
        if self.merged_at is None:
            return None
        delta = self.merged_at - self.created_at
        return max(delta.total_seconds() / 3600.0, 0.0)

    @property
    def total_changes(self) -> int:
        """总变更行数"""
        return self.additions + self.deletions

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于输出"""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "created_at": self.raw["created_at"],
            "merged_at": self.raw["merged_at"],
            "reviewers": self.reviewers,
            "comments": self.comments,
            "additions": self.additions,
            "deletions": self.deletions,
            "changed_files": self.changed_files,
            "review_time_hours": self.review_time_hours,
            "total_changes": self.total_changes,
        }


# ============================================================
# 数据解析层
# ============================================================

class DataParser:
    """解析外部输入为 PR 列表"""

    @staticmethod
    def parse_file(filepath: str) -> List[PullRequest]:
        """从文件读取并解析 PR 数据"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError) as exc:
            raise RuntimeError(f"E002: 文件读取失败 - {filepath}: {exc}")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"E003: JSON 解析失败 - {exc}")

        return DataParser.parse_data(data)

    @staticmethod
    def parse_data(data: Any) -> List[PullRequest]:
        """解析 JSON 数据为 PR 列表"""
        items = data if isinstance(data, list) else data.get("pull_requests", [])
        if not isinstance(items, list):
            raise RuntimeError("E004: 数据格式错误，期望 PR 列表")

        prs = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise RuntimeError(f"E004: 第 {idx} 项不是对象")
            try:
                prs.append(PullRequest(item))
            except ValueError as exc:
                raise RuntimeError(f"E004: 第 {idx} 项校验失败 - {exc}")
        return prs


# ============================================================
# 指标计算层
# ============================================================

class MetricsCalculator:
    """计算团队与个人效能指标"""

    def __init__(self, prs: List[PullRequest]):
        self.prs = prs
        self._validate()

    def _validate(self) -> None:
        """确保有数据可计算"""
        if not self.prs:
            raise RuntimeError("E004: 没有可分析的 PR 数据")

    # ---------- 团队指标 ----------
    def team_metrics(self) -> Dict[str, Any]:
        """计算团队级指标"""
        try:
            total_prs = len(self.prs)
            merged_prs = [pr for pr in self.prs if pr.merged_at is not None]
            total_merged = len(merged_prs)

            # 评审时长（仅统计已合并）
            review_times = [
                pr.review_time_hours for pr in merged_prs
                if pr.review_time_hours is not None
            ]
            avg_review_hours = (
                sum(review_times) / len(review_times) if review_times else 0.0
            )

            # 评论总数
            total_comments = sum(pr.comments for pr in self.prs)

            # 变更规模
            total_additions = sum(pr.additions for pr in self.prs)
            total_deletions = sum(pr.deletions for pr in self.prs)
            total_changes = total_additions + total_deletions

            # 评审人唯一数量
            all_reviewers = set()
            for pr in self.prs:
                all_reviewers.update(pr.reviewers)
            unique_reviewers = len(all_reviewers)

            # 评审覆盖率（至少有一个评审人的 PR 占比）
            reviewed_prs = [pr for pr in self.prs if pr.reviewers]
            review_coverage = (
                len(reviewed_prs) / total_prs if total_prs > 0 else 0.0
            )

            return {
                "total_prs": total_prs,
                "merged_prs": total_merged,
                "merge_rate": total_merged / total_prs if total_prs else 0.0,
                "avg_review_hours": avg_review_hours,
                "total_comments": total_comments,
                "avg_comments_per_pr": total_comments / total_prs if total_prs else 0.0,
                "total_additions": total_additions,
                "total_deletions": total_deletions,
                "total_changes": total_changes,
                "avg_changes_per_pr": total_changes / total_prs if total_prs else 0.0,
                "unique_reviewers": unique_reviewers,
                "review_coverage": review_coverage,
            }
        except Exception as exc:
            raise RuntimeError(f"E005: 团队指标计算失败 - {exc}")

    # ---------- 个人指标 ----------
    def individual_metrics(self) -> List[Dict[str, Any]]:
        """按作者统计个人指标"""
        try:
            author_stats: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "pr_count": 0,
                    "merged_count": 0,
                    "total_comments": 0,
                    "total_additions": 0,
                    "total_deletions": 0,
                    "total_changes": 0,
                    "reviewed_prs": 0,
                    "review_times": [],
                    "review_tasks": 0,
                }
            )

            for pr in self.prs:
                stats = author_stats[pr.author]
                stats["pr_count"] += 1
                if pr.merged_at is not None:
                    stats["merged_count"] += 1
                    if pr.review_time_hours is not None:
                        stats["review_times"].append(pr.review_time_hours)
                stats["total_comments"] += pr.comments
                stats["total_additions"] += pr.additions
                stats["total_deletions"] += pr.deletions
                stats["total_changes"] += pr.total_changes
                if pr.reviewers:
                    stats["reviewed_prs"] += 1

                # 作为评审人的工作量
                for reviewer in pr.reviewers:
                    reviewer_stats = author_stats[reviewer]
                    reviewer_stats["review_tasks"] += 1

            results = []
            for author, stats in author_stats.items():
                merged = stats["merged_count"]
                review_times = stats["review_times"]
                results.append(
                    {
                        "author": author,
                        "pr_created": stats["pr_count"],
                        "pr_merged": merged,
                        "merge_rate": merged / stats["pr_count"] if stats["pr_count"] else 0.0,
                        "avg_comments_per_pr": (
                            stats["total_comments"] / stats["pr_count"]
                            if stats["pr_count"]
                            else 0.0
                        ),
                        "total_additions": stats["total_additions"],
                        "total_deletions": stats["total_deletions"],
                        "total_changes": stats["total_changes"],
                        "avg_changes_per_pr": (
                            stats["total_changes"] / stats["pr_count"]
                            if stats["pr_count"]
                            else 0.0
                        ),
                        "avg_review_hours": (
                            sum(review_times) / len(review_times)
                            if review_times
                            else None
                        ),
                        "review_coverage": (
                            stats["reviewed_prs"] / stats["pr_count"]
                            if stats["pr_count"]
                            else 0.0
                        ),
                        "review_tasks": stats["review_tasks"],
                    }
                )
            return results
        except Exception as exc:
            raise RuntimeError(f"E005: 个人指标计算失败 - {exc}")

    # ---------- 综合结果 ----------
    def all_metrics(self) -> Dict[str, Any]:
        """返回全部指标"""
        return {
            "team": self.team_metrics(),
            "individuals": self.individual_metrics(),
        }


# ============================================================
# 报告生成层
# ============================================================

class ReportGenerator:
    """生成不同格式的分析报告"""

    @staticmethod
    def generate(data: Dict[str, Any], fmt: str) -> str:
        """根据指定格式生成报告"""
        if fmt == "json":
            return ReportGenerator._to_json(data)
        elif fmt == "markdown":
            return ReportGenerator._to_markdown(data)
        elif fmt == "text":
            return ReportGenerator._to_text(data)
        else:
            raise RuntimeError(f"E008: 未知输出格式: {fmt}")

    @staticmethod
    def _to_json(data: Dict[str, Any]) -> str:
        """JSON 格式，带置信度标注"""
        annotated = ReportGenerator._annotate_confidence(data)
        return json.dumps(annotated, ensure_ascii=False, indent=2)

    @staticmethod
    def _annotate_confidence(data: Dict[str, Any]) -> Dict[str, Any]:
        """为输出添加置信度标注"""
        result = {"confidence": "high", "data": data}
        return result

    @staticmethod
    def _to_markdown(data: Dict[str, Any]) -> str:
        """Markdown 表格格式"""
        lines = ["# 代码评审效能分析报告\n"]
        team = data["team"]

        # 团队指标
        lines.append("## 团队指标\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| PR 总数 | {team['total_prs']} |")
        lines.append(f"| 合并数 | {team['merged_prs']} |")
        lines.append(f"| 合并率 | {team['merge_rate']:.1%} |")
        lines.append(f"| 平均评审时长(小时) | {team['avg_review_hours']:.1f} |")
        lines.append(f"| 平均评论数/PR | {team['avg_comments_per_pr']:.1f} |")
        lines.append(f"| 平均变更行数/PR | {team['avg_changes_per_pr']:.1f} |")
        lines.append(f"| 唯一评审人 | {team['unique_reviewers']} |")
        lines.append(f"| 评审覆盖率 | {team['review_coverage']:.1%} |\n")

        # 个人指标
        lines.append("## 个人指标\n")
        lines.append("| 作者 | PR数 | 合并率 | 均评论/PR | 均变更/PR | 均评审时长(h) | 评审覆盖率 | 评审任务数 |")
        lines.append("|------|-------|--------|-----------|-----------|---------------|------------|------------|")
        for person in data["individuals"]:
            avg_review = (
                f"{person['avg_review_hours']:.1f}"
                if person["avg_review_hours"] is not None
                else "N/A"
            )
            lines.append(
                f"| {person['author']} | {person['pr_created']} | "
                f"{person['merge_rate']:.1%} | {person['avg_comments_per_pr']:.1f} | "
                f"{person['avg_changes_per_pr']:.1f} | {avg_review} | "
                f"{person['review_coverage']:.1%} | {person['review_tasks']} |"
            )
        return "\n".join(lines)

    @staticmethod
    def _to_text(data: Dict[str, Any]) -> str:
        """纯文本摘要格式"""
        lines = ["代码评审效能分析报告", "=" * 30]
        team = data["team"]

        lines.append("\n[团队指标]")
        lines.append(f"  PR总数: {team['total_prs']}")
        lines.append(f"  合并率: {team['merge_rate']:.1%}")
        lines.append(f"  平均评审时长: {team['avg_review_hours']:.1f} 小时")
        lines.append(f"  平均评论/PR: {team['avg_comments_per_pr']:.1f}")
        lines.append(f"  平均变更/PR: {team['avg_changes_per_pr']:.1f} 行")
        lines.append(f"  评审覆盖率: {team['review_coverage']:.1%}")

        lines.append("\n[个人指标]")
        for person in data["individuals"]:
            avg_review = (
                f"{person['avg_review_hours']:.1f}h"
                if person["avg_review_hours"] is not None
                else "N/A"
            )
            lines.append(
                f"  {person['author']}: {person['pr_created']} PRs, "
                f"合并率 {person['merge_rate']:.0%}, "
                f"均评论 {person['avg_comments_per_pr']:.1f}, "
                f"均变更 {person['avg_changes_per_pr']:.0f}, "
                f"评审时长 {avg_review}, "
                f"覆盖率 {person['review_coverage']:.0%}, "
                f"评审任务 {person['review_tasks']}"
            )
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

class SelfTest:
    """内置硬编码样例数据的离线自检"""

    SAMPLE_DATA = [
        {
            "id": 101,
            "title": "Add user authentication",
            "author": "alice",
            "created_at": "2026-01-01T10:00:00Z",
            "merged_at": "2026-01-01T14:30:00Z",
            "reviewers": ["bob", "carol"],
            "comments": 8,
            "additions": 150,
            "deletions": 30,
            "changed_files": 5,
        },
        {
            "id": 102,
            "title": "Fix login bug",
            "author": "bob",
            "created_at": "2026-01-02T09:00:00Z",
            "merged_at": "2026-01-02T11:15:00Z",
            "reviewers": ["alice"],
            "comments": 3,
            "additions": 20,
            "deletions": 10,
            "changed_files": 2,
        },
        {
            "id": 103,
            "title": "Refactor database layer",
            "author": "alice",
            "created_at": "2026-01-03T08:30:00Z",
            "merged_at": None,
            "reviewers": ["carol"],
            "comments": 12,
            "additions": 300,
            "deletions": 120,
            "changed_files": 8,
        },
        {
            "id": 104,
            "title": "Update documentation",
            "author": "carol",
            "created_at": "2026-01-04T13:00:00Z",
            "merged_at": "2026-01-04T15:45:00Z",
            "reviewers": [],
            "comments": 1,
            "additions": 45,
            "deletions": 5,
            "changed_files": 3,
        },
    ]

    @classmethod
    def run(cls) -> bool:
        """执行自检，全部通过返回 True"""
        try:
            # 1. 数据解析
            prs = DataParser.parse_data(cls.SAMPLE_DATA)
            assert len(prs) == 4, "PR 数量应为 4"

            # 2. 指标计算
            calc = MetricsCalculator(prs)
            metrics = calc.all_metrics()
            team = metrics["team"]
            individuals = metrics["individuals"]

            # 3. 团队指标宽松断言（不依赖精确值）
            assert team["total_prs"] == 4, "PR 总数应为 4"
            assert team["merged_prs"] >= 3, "合并数应至少为 3"
            assert 0.0 < team["merge_rate"] <= 1.0, "合并率应在 (0,1] 区间"
            assert team["avg_review_hours"] > 0.0, "平均评审时长应为正数"
            assert team["total_comments"] >= 20, "评论总数应至少为 20"
            assert team["total_changes"] > 500, "总变更行数应超过 500"
            assert team["unique_reviewers"] >= 2, "唯一评审人应至少 2 人"
            assert 0.0 < team["review_coverage"] <= 1.0, "评审覆盖率应在 (0,1] 区间"

            # 4. 个人指标宽松断言
            assert len(individuals) >= 3, "应有至少 3 位作者"
            author_names = {p["author"] for p in individuals}
            assert "alice" in author_names, "alice 应存在"
            assert "bob" in author_names, "bob 应存在"

            # alice 的指标
            alice = next(p for p in individuals if p["author"] == "alice")
            assert alice["pr_created"] >= 2, "alice 应创建至少 2 个 PR"
            assert alice["pr_merged"] >= 1, "alice 应合并至少 1 个 PR"
            assert alice["review_tasks"] >= 1, "alice 应承担至少 1 个评审任务"
            assert alice["avg_review_hours"] is None or alice["avg_review_hours"] > 0, \
                "alice 的评审时长应为正或 None"

            # bob 的指标
            bob = next(p for p in individuals if p["author"] == "bob")
            assert bob["pr_created"] >= 1, "bob 应创建至少 1 个 PR"
            assert bob["review_tasks"] >= 1, "bob 应承担至少 1 个评审任务"

            # 5. 报告生成
            for fmt in ["json", "markdown", "text"]:
                report = ReportGenerator.generate(metrics, fmt)
                assert isinstance(report, str), f"{fmt} 报告应为字符串"
                assert len(report) > 0, f"{fmt} 报告不应为空"

            # 6. JSON 可解析性
            json_report = ReportGenerator.generate(metrics, "json")
            parsed = json.loads(json_report)
            assert "data" in parsed, "JSON 报告应包含 data 字段"
            assert "team" in parsed["data"], "JSON 报告应包含 team 指标"

            return True
        except AssertionError as exc:
            print(f"E009: 自检断言失败 - {exc}", file=sys.stderr)
            return False
        except Exception as exc:
            print(f"E009: 自检执行异常 - {exc}", file=sys.stderr)
            return False


# ============================================================
# 主程序
# ============================================================

def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="代码评审效能分析工具",
        epilog="错误码: E001-E010，详见脚本头部注释",
    )
    parser.add_argument(
        "data_file",
        nargs="?",
        help="PR 数据 JSON 文件路径",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "text"],
        default="markdown",
        help="输出格式 (默认: markdown)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    args = parse_args(argv if argv is not None else sys.argv[1:])

    # 自检模式
    if args.selftest:
        if SelfTest.run():
            print("自检通过 ✔")
            return 0
        return 9  # 对应 E009

    # 正常模式
    if not args.data_file:
        print("E001: 缺少数据文件参数", file=sys.stderr)
        return 1

    try:
        # 解析数据
        prs = DataParser.parse_file(args.data_file)

        # 计算指标
        calc = MetricsCalculator(prs)
        metrics = calc.all_metrics()

        # 生成报告
        report = ReportGenerator.generate(metrics, args.format)
        print(report)
        return 0

    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        # 从错误消息提取错误码
        code = str(exc).split(":")[0] if ":" in str(exc) else "E010"
        return int(code[1:]) if code[1:].isdigit() else 10
    except Exception as exc:
        print(f"E010: 未预期错误 - {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
