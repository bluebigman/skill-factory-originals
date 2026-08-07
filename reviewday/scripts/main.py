#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reviewday - 代码审查报告生成与结构化分析工具

本脚本依据功能规格独立实现（clean-room），不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能：
- 解析代码审查数据（评论、严重级别、文件路径等）
- 生成结构化报告（JSON 格式）
- 支持批量处理多个审查条目
- 自动计算置信度标注
- 提供 --selftest 离线自检模式
"""

import argparse
import json
import os
import sys
import datetime
from collections import Counter, defaultdict

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据格式错误（非字典或缺少必要字段）",
    "E002": "审查条目格式错误（缺少 comment 或 severity）",
    "E003": "严重级别取值非法（必须为 critical/major/minor/info）",
    "E004": "文件路径字段缺失或为空",
    "E005": "数据为空（无任何审查条目）",
    "E006": "输出目录不存在或无法写入",
    "E007": "JSON 序列化失败",
    "E008": "命令行参数冲突",
    "E009": "内部逻辑错误（不应发生）",
    "E010": "未知错误",
}


class ReviewDayError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据模型与校验
# ============================================================

VALID_SEVERITIES = {"critical", "major", "minor", "info"}


def validate_input(data) -> dict:
    """
    校验并规范化输入数据。

    输入应为字典，包含：
      - reviews: list，每个元素为字典，含 comment(str), severity(str), file(str), line(int, 可选)
      - meta: dict，可选，包含 project_name, reviewer, date 等元信息

    返回规范化后的字典。
    错误：E001（整体格式）、E002（条目缺字段）、E003（严重级别非法）、E004（文件路径缺失）、E005（数据为空）
    """
    if not isinstance(data, dict):
        raise ReviewDayError("E001", "顶层数据必须是字典")

    reviews = data.get("reviews", [])
    if not isinstance(reviews, list):
        raise ReviewDayError("E001", "reviews 字段必须是列表")

    if len(reviews) == 0:
        raise ReviewDayError("E005")

    normalized_reviews = []
    for idx, item in enumerate(reviews):
        if not isinstance(item, dict):
            raise ReviewDayError("E002", f"第 {idx + 1} 条审查不是字典")

        # 必需字段
        comment = item.get("comment")
        severity = item.get("severity")
        file_path = item.get("file")

        if not comment or not isinstance(comment, str):
            raise ReviewDayError("E002", f"第 {idx + 1} 条缺少非空 comment 字段")
        if not severity or not isinstance(severity, str):
            raise ReviewDayError("E002", f"第 {idx + 1} 条缺少 severity 字段")
        if severity not in VALID_SEVERITIES:
            raise ReviewDayError("E003", f"第 {idx + 1} 条 severity='{severity}' 非法")
        if not file_path or not isinstance(file_path, str):
            raise ReviewDayError("E004", f"第 {idx + 1} 条缺少非空 file 字段")

        # 可选字段
        line = item.get("line")
        if line is not None:
            try:
                line = int(line)
            except (TypeError, ValueError):
                line = None  # 非法行号忽略

        normalized_reviews.append({
            "comment": comment.strip(),
            "severity": severity,
            "file": file_path.strip(),
            "line": line,
        })

    # 元信息
    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}

    return {
        "reviews": normalized_reviews,
        "meta": meta,
    }


# ============================================================
# 统计分析
# ============================================================

def compute_statistics(reviews: list) -> dict:
    """
    计算审查统计数据。

    返回：
      - total: 总条数
      - by_severity: 各级别计数
      - by_file: 各文件计数（按文件路径分组）
      - severity_ratio: 各级别占比（0~1 浮点数）
    """
    total = len(reviews)
    severity_counter = Counter(r["severity"] for r in reviews)
    file_counter = Counter(r["file"] for r in reviews)

    # 计算占比（保留两位小数）
    severity_ratio = {}
    for sev in VALID_SEVERITIES:
        count = severity_counter.get(sev, 0)
        severity_ratio[sev] = round(count / total, 2) if total > 0 else 0.0

    return {
        "total": total,
        "by_severity": dict(severity_counter),
        "by_file": dict(file_counter),
        "severity_ratio": severity_ratio,
    }


def compute_confidence(reviews: list) -> dict:
    """
    计算置信度标注。

    规则：
      - 若总条数 >= 10，置信度为 "high"
      - 若总条数 >= 5，置信度为 "medium"
      - 否则为 "low"
      - 同时返回统计依据
    """
    total = len(reviews)
    if total >= 10:
        level = "high"
    elif total >= 5:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "basis": {
            "review_count": total,
            "threshold_high": 10,
            "threshold_medium": 5,
        },
    }


# ============================================================
# 报告生成
# ============================================================

def generate_report(data: dict) -> dict:
    """
    根据规范化输入生成结构化报告。

    报告结构：
      - meta: 原始元信息 + 生成时间戳
      - summary: 统计摘要
      - confidence: 置信度
      - reviews: 原始审查列表（含行号）
      - files: 按文件分组的审查条目
    """
    reviews = data["reviews"]
    meta = data["meta"]

    stats = compute_statistics(reviews)
    confidence = compute_confidence(reviews)

    # 按文件分组
    files_grouped = defaultdict(list)
    for r in reviews:
        files_grouped[r["file"]].append(r)

    # 排序（按文件路径字典序）
    files_sorted = {}
    for fpath in sorted(files_grouped.keys()):
        files_sorted[fpath] = files_grouped[fpath]

    report = {
        "meta": {
            **meta,
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "tool": "reviewday",
            "version": "1.0.1",
        },
        "summary": stats,
        "confidence": confidence,
        "reviews": reviews,
        "files": files_sorted,
    }

    return report


# ============================================================
# 输出处理
# ============================================================

def output_report(report: dict, output_path: str = "") -> str:
    """
    将报告输出为 JSON 字符串。

    若指定 output_path，则写入文件（错误 E006）。
    若序列化失败，抛 E007。
    """
    try:
        json_str = json.dumps(report, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise ReviewDayError("E007", str(exc)) from exc

    if output_path:
        # 检查目录
        dir_name = os.path.dirname(os.path.abspath(output_path))
        if not os.path.isdir(dir_name):
            raise ReviewDayError("E006", f"目录不存在: {dir_name}")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        except OSError as exc:
            raise ReviewDayError("E006", str(exc)) from exc

    return json_str


# ============================================================
# 主流程
# ============================================================

def process_review_data(raw_data: dict, output_path: str = "") -> str:
    """
    完整处理流程：校验 -> 生成报告 -> 输出。

    返回 JSON 字符串。
    """
    normalized = validate_input(raw_data)
    report = generate_report(normalized)
    return output_report(report, output_path)


def read_input_file(file_path: str) -> dict:
    """
    从 JSON 文件读取输入数据。
    错误：E001（JSON 解析失败或格式错误）
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewDayError("E001", f"读取输入文件失败: {exc}") from exc

    if not isinstance(data, dict):
        raise ReviewDayError("E001", "输入 JSON 顶层必须是对象")
    return data


# ============================================================
# 自检（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。
    不读外部文件、不访问网络、不依赖当前工作目录。

    断言采用宽松阈值（大小比较/区间判断），保证稳健。
    """
    print("[selftest] 开始自检...")

    # ---- 样例数据（硬编码） ----
    sample_data = {
        "meta": {
            "project_name": "selftest_project",
            "reviewer": "tester",
        },
        "reviews": [
            {"comment": "未处理的异常", "severity": "critical", "file": "src/main.py", "line": 42},
            {"comment": "内存泄漏风险", "severity": "critical", "file": "src/utils.py", "line": 10},
            {"comment": "缺少输入校验", "severity": "major", "file": "src/main.py", "line": 55},
            {"comment": "建议使用常量", "severity": "minor", "file": "src/config.py"},
            {"comment": "注释过时", "severity": "info", "file": "src/main.py", "line": 3},
            {"comment": "重复代码", "severity": "major", "file": "src/utils.py", "line": 20},
            {"comment": "命名不规范", "severity": "minor", "file": "src/main.py"},
        ],
    }

    # ---- 测试 1：校验与规范化 ----
    try:
        normalized = validate_input(sample_data)
    except ReviewDayError as exc:
        print(f"  [FAIL] 校验失败: {exc}")
        return 1
    print("  [PASS] 数据校验通过")

    # 断言：条目数正确
    assert len(normalized["reviews"]) == 7, "条目数应为 7"
    print("  [PASS] 条目数校验")

    # ---- 测试 2：统计计算 ----
    stats = compute_statistics(normalized["reviews"])
    assert stats["total"] == 7, "总数应为 7"
    assert stats["by_severity"]["critical"] == 2, "critical 应为 2"
    assert stats["by_severity"]["major"] == 2, "major 应为 2"
    # 宽松断言：占比在合理范围
    assert 0.2 <= stats["severity_ratio"]["critical"] <= 0.4, "critical 占比应在 0.2~0.4"
    assert 0.2 <= stats["severity_ratio"]["major"] <= 0.4, "major 占比应在 0.2~0.4"
    print("  [PASS] 统计计算")

    # ---- 测试 3：置信度 ----
    conf = compute_confidence(normalized["reviews"])
    assert conf["level"] == "medium", "7 条应返回 medium"
    # 宽松断言：置信度级别在合法集合内
    assert conf["level"] in {"low", "medium", "high"}, "置信度级别非法"
    print("  [PASS] 置信度计算")

    # ---- 测试 4：报告生成 ----
    report = generate_report(normalized)
    assert "summary" in report, "报告缺少 summary"
    assert "confidence" in report, "报告缺少 confidence"
    assert "reviews" in report, "报告缺少 reviews"
    assert "files" in report, "报告缺少 files"
    # 宽松断言：文件分组数量合理（至少 2 个文件）
    assert len(report["files"]) >= 2, "文件分组应至少 2 个"
    print("  [PASS] 报告生成")

    # ---- 测试 5：JSON 输出 ----
    json_str = output_report(report)
    parsed = json.loads(json_str)
    assert parsed["summary"]["total"] == 7, "JSON 解析后总数应为 7"
    print("  [PASS] JSON 输出")

    # ---- 测试 6：错误处理 ----
    # 空数据
    try:
        validate_input({"reviews": []})
        print("  [FAIL] 空数据应抛 E005")
        return 1
    except ReviewDayError as exc:
        assert exc.code == "E005", f"错误码应为 E005，实际 {exc.code}"
    print("  [PASS] 空数据错误处理")

    # 非法严重级别
    bad_data = {"reviews": [{"comment": "x", "severity": "bad", "file": "f.py"}]}
    try:
        validate_input(bad_data)
        print("  [FAIL] 非法级别应抛 E003")
        return 1
    except ReviewDayError as exc:
        assert exc.code == "E003", f"错误码应为 E003，实际 {exc.code}"
    print("  [PASS] 非法级别错误处理")

    # 缺少字段
    bad_data2 = {"reviews": [{"severity": "major", "file": "f.py"}]}
    try:
        validate_input(bad_data2)
        print("  [FAIL] 缺少 comment 应抛 E002")
        return 1
    except ReviewDayError as exc:
        assert exc.code == "E002", f"错误码应为 E002，实际 {exc.code}"
    print("  [PASS] 缺字段错误处理")

    print("[selftest] 全部自检通过 ✅")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        prog="reviewday",
        description="代码审查报告生成工具（结构化分析）",
        epilog="示例: python main.py -i input.json -o report.json",
    )
    parser.add_argument(
        "-i", "--input",
        help="输入 JSON 文件路径（包含 reviews 数组）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出 JSON 文件路径（可选，默认输出到 stdout）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不访问网络）",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息",
    )

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print("reviewday version 1.0.1")
        return 0

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print("错误: 必须提供 --input 或使用 --selftest", file=sys.stderr)
        print("提示: 使用 --help 查看帮助", file=sys.stderr)
        return 1

    try:
        # 读取输入
        raw_data = read_input_file(args.input)
        # 处理并输出
        result = process_review_data(raw_data, args.output or "")
        if not args.output:
            # 输出到 stdout
            print(result)
        else:
            print(f"报告已写入: {args.output}")
        return 0

    except ReviewDayError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底错误
        print(f"错误: [E010] 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
