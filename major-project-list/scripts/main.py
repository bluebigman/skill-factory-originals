#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周报生成 - 独立实现脚本
基于功能规格 clean-room 重写，仅依赖标准库。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理异常：{detail}",
    "E007": "输出格式不支持：{fmt}",
    "E008": "批量处理中断：第 {index} 项失败",
    "E009": "参数校验失败：{detail}",
    "E010": "未知错误：{detail}",
}


def make_error(code: str, **kwargs) -> Dict[str, str]:
    """构造错误信息字典"""
    template = ERROR_CODES.get(code, ERROR_CODES["E010"])
    message = template.format(**kwargs) if kwargs else template
    return {"error_code": code, "message": message}


# ============================================================
# 核心数据结构
# ============================================================
class WeeklyReportItem:
    """周报单项条目"""

    def __init__(self, title: str, category: str, progress: float, note: str = ""):
        self.title = title
        self.category = category
        self.progress = progress  # 0.0 ~ 1.0
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "category": self.category,
            "progress": self.progress,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeeklyReportItem":
        return cls(
            title=str(data.get("title", "")),
            category=str(data.get("category", "未分类")),
            progress=float(data.get("progress", 0.0)),
            note=str(data.get("note", "")),
        )


class WeeklyReport:
    """周报容器"""

    def __init__(self, period: str = "", author: str = ""):
        self.period = period
        self.author = author
        self.items: List[WeeklyReportItem] = []

    def add_item(self, item: WeeklyReportItem) -> None:
        self.items.append(item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "author": self.author,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeeklyReport":
        report = cls(
            period=str(data.get("period", "")),
            author=str(data.get("author", "")),
        )
        for item_data in data.get("items", []):
            report.add_item(WeeklyReportItem.from_dict(item_data))
        return report


# ============================================================
# 核心处理逻辑
# ============================================================
def parse_input(raw_input: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
    """
    解析输入内容，识别关键信息。
    支持 JSON 格式或简单文本格式。
    返回 (解析结果, 错误信息)，成功时错误为 None。
    """
    if raw_input is None or not raw_input.strip():
        return None, make_error("E001")

    text = raw_input.strip()

    # 尝试 JSON 解析
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data, None
            elif isinstance(data, list):
                return {"items": data}, None
            else:
                return None, make_error("E003", example='{"period": "2024-W01", "items": [...]}')
        except json.JSONDecodeError:
            return None, make_error("E003", example='{"period": "2024-W01", "items": [...]}')

    # 尝试简单文本格式：每行 "标题|分类|进度|备注"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        items = []
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                try:
                    progress = float(parts[2].rstrip("%")) / 100.0 if "%" in parts[2] else float(parts[2])
                    progress = max(0.0, min(1.0, progress))
                except ValueError:
                    progress = 0.0
                items.append({
                    "title": parts[0],
                    "category": parts[1] if len(parts) > 1 else "未分类",
                    "progress": progress,
                    "note": parts[3] if len(parts) > 3 else "",
                })
        if items:
            return {"items": items}, None

    return None, make_error("E003", example='{"period": "2024-W01", "items": [...]} 或 "标题|分类|进度|备注"')


def validate_data(data: Dict[str, Any]) -> Tuple[Optional[WeeklyReport], Optional[Dict[str, str]]]:
    """
    校验并结构化数据。
    返回 (周报对象, 错误信息)，成功时错误为 None。
    """
    if not isinstance(data, dict):
        return None, make_error("E003", example='{"period": "2024-W01", "items": [...]}')

    report = WeeklyReport(
        period=str(data.get("period", "")),
        author=str(data.get("author", "")),
    )

    items_data = data.get("items", [])
    if not isinstance(items_data, list):
        return None, make_error("E003", example='"items" 必须是数组')

    for idx, item_data in enumerate(items_data):
        if not isinstance(item_data, dict):
            return None, make_error("E003", example=f"items[{idx}] 必须是对象")

        # 必填字段检查
        missing_fields = []
        if "title" not in item_data or not str(item_data.get("title", "")).strip():
            missing_fields.append("title")
        if "progress" not in item_data:
            missing_fields.append("progress")

        if missing_fields:
            return None, make_error("E002", missing=", ".join(missing_fields))

        # 类型转换与校验
        try:
            title = str(item_data["title"]).strip()
            category = str(item_data.get("category", "未分类")).strip()
            progress_val = item_data["progress"]
            if isinstance(progress_val, str):
                if "%" in progress_val:
                    progress = float(progress_val.rstrip("%")) / 100.0
                else:
                    progress = float(progress_val)
            else:
                progress = float(progress_val)
            progress = max(0.0, min(1.0, progress))
            note = str(item_data.get("note", "")).strip()
        except (ValueError, TypeError):
            return None, make_error("E003", example=f"items[{idx}].progress 必须是数字")

        report.add_item(WeeklyReportItem(title, category, progress, note))

    if not report.items:
        return None, make_error("E002", missing="items（至少一条工作内容）")

    return report, None


def calculate_confidence(report: WeeklyReport) -> float:
    """
    计算整体置信度（0~100）。
    基于数据完整性和合理性。
    """
    if not report.items:
        return 0.0

    score = 100.0
    item_count = len(report.items)

    # 字段完整性
    for item in report.items:
        if not item.title:
            score -= 5.0
        if not item.category or item.category == "未分类":
            score -= 2.0
        if not item.note:
            score -= 1.0

    # 进度合理性（0 或 1 可能不准确）
    for item in report.items:
        if item.progress == 0.0 or item.progress == 1.0:
            score -= 1.0

    # 周期信息
    if not report.period:
        score -= 5.0
    if not report.author:
        score -= 3.0

    # 条目数量异常
    if item_count > 20:
        score -= 10.0

    return max(0.0, min(100.0, score))


def format_output(report: WeeklyReport, fmt: str = "text") -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    按指定格式生成输出。
    支持 text / json / markdown。
    返回 (输出内容, 错误信息)，成功时错误为 None。
    """
    confidence = calculate_confidence(report)

    # 置信度标注
    confidence_tag = ""
    if confidence >= 90:
        confidence_tag = ""
    elif confidence >= 85:
        confidence_tag = " [建议复核]"
    else:
        confidence_tag = " [需核实]"

    if fmt == "json":
        result = report.to_dict()
        result["confidence"] = confidence
        result["confidence_tag"] = confidence_tag.strip()
        return json.dumps(result, ensure_ascii=False, indent=2), None

    elif fmt == "markdown":
        lines = []
        lines.append(f"# 周报{confidence_tag}")
        lines.append("")
        if report.period:
            lines.append(f"**周期**: {report.period}")
        if report.author:
            lines.append(f"**作者**: {report.author}")
        lines.append("")
        lines.append("| 标题 | 分类 | 进度 | 备注 |")
        lines.append("|------|------|------|------|")
        for item in report.items:
            progress_str = f"{item.progress * 100:.0f}%"
            lines.append(f"| {item.title} | {item.category} | {progress_str} | {item.note} |")
        lines.append("")
        lines.append(f"**整体置信度**: {confidence:.1f}% {confidence_tag}")
        return "\n".join(lines), None

    else:  # text
        lines = []
        lines.append(f"===== 周报{confidence_tag} =====")
        if report.period:
            lines.append(f"周期: {report.period}")
        if report.author:
            lines.append(f"作者: {report.author}")
        lines.append("-" * 40)
        for idx, item in enumerate(report.items, 1):
            progress_str = f"{item.progress * 100:.0f}%"
            lines.append(f"{idx}. [{item.category}] {item.title} - {progress_str}")
            if item.note:
                lines.append(f"   备注: {item.note}")
        lines.append("-" * 40)
        lines.append(f"整体置信度: {confidence:.1f}% {confidence_tag}")
        return "\n".join(lines), None


def process_input(raw_input: str, fmt: str = "text") -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    标准流程入口：解析 -> 校验 -> 生成输出。
    返回 (输出内容, 错误信息)。
    """
    # Step 1: 解析
    data, err = parse_input(raw_input)
    if err:
        return None, err

    # Step 2: 校验与结构化
    report, err = validate_data(data)
    if err:
        return None, err

    # Step 3: 输出
    output, err = format_output(report, fmt)
    if err:
        return None, err

    return output, None


def batch_process(inputs: List[str], fmt: str = "text") -> Tuple[List[Any], Optional[Dict[str, str]]]:
    """
    批量处理多个输入。
    返回 (结果列表, 错误信息)。
    """
    results = []
    for idx, raw_input in enumerate(inputs, 1):
        output, err = process_input(raw_input, fmt)
        if err:
            return None, make_error("E008", index=idx)
        results.append(output)
    return results, None


# ============================================================
# 自检模块（--selftest）
# ============================================================
def selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    返回 0 表示通过，非 0 表示失败。
    """
    print("开始自检...")

    # ---- 测试用例 1: 正常 JSON 输入 ----
    sample_json = json.dumps({
        "period": "2024-W01",
        "author": "测试用户",
        "items": [
            {"title": "完成项目A需求分析", "category": "开发", "progress": 0.8, "note": "输出需求文档"},
            {"title": "修复Bug #123", "category": "运维", "progress": 1.0, "note": "已上线"},
            {"title": "团队周会", "category": "管理", "progress": 0.5, "note": ""},
        ]
    })
    output, err = process_input(sample_json, "json")
    assert err is None, f"JSON 输入处理失败: {err}"
    parsed = json.loads(output)
    # 宽松断言：只验证结构存在，不依赖精确值
    assert "items" in parsed, "输出缺少 items 字段"
    assert len(parsed["items"]) >= 2, "条目数量异常"
    assert "confidence" in parsed, "输出缺少 confidence 字段"
    assert parsed["confidence"] >= 0 and parsed["confidence"] <= 100, "置信度超出范围"
    print("  [PASS] JSON 输入处理")

    # ---- 测试用例 2: 文本格式输入 ----
    sample_text = "完成登录模块|前端|80%|实现 OAuth\n数据库优化|后端|60%|索引调整\n代码审查|质量|100%|"
    output, err = process_input(sample_text, "text")
    assert err is None, f"文本输入处理失败: {err}"
    assert "周报" in output, "输出缺少周报标题"
    assert "置信度" in output, "输出缺少置信度信息"
    print("  [PASS] 文本输入处理")

    # ---- 测试用例 3: 错误处理 ----
    _, err = process_input("", "text")
    assert err is not None, "空输入应报错"
    assert err["error_code"] == "E001", f"空输入错误码错误: {err}"
    print("  [PASS] 空输入错误处理")

    _, err = process_input("invalid json {", "text")
    assert err is not None, "无效 JSON 应报错"
    assert err["error_code"] == "E003", f"无效 JSON 错误码错误: {err}"
    print("  [PASS] 无效输入错误处理")

    # ---- 测试用例 4: 缺失必填字段 ----
    bad_data = json.dumps({"items": [{"progress": 0.5}]})
    _, err = process_input(bad_data, "text")
    assert err is not None, "缺失 title 应报错"
    assert err["error_code"] == "E002", f"缺失字段错误码错误: {err}"
    print("  [PASS] 缺失字段错误处理")

    # ---- 测试用例 5: 批量处理 ----
    inputs = [sample_json, sample_text]
    results, err = batch_process(inputs, "text")
    assert err is None, f"批量处理失败: {err}"
    assert len(results) == 2, f"批量处理结果数量异常: {len(results)}"
    print("  [PASS] 批量处理")

    # ---- 测试用例 6: 置信度计算 ----
    report = WeeklyReport("2024-W01", "测试")
    report.add_item(WeeklyReportItem("完整任务", "开发", 0.5, "有备注"))
    report.add_item(WeeklyReportItem("另一个任务", "测试", 0.7, "也有备注"))
    conf = calculate_confidence(report)
    assert conf >= 80, f"完整数据置信度应较高，实际: {conf}"
    print("  [PASS] 置信度计算")

    # ---- 测试用例 7: 边界情况 ----
    # 进度为 0 或 1 不应导致崩溃
    edge_data = json.dumps({
        "items": [
            {"title": "任务A", "progress": 0},
            {"title": "任务B", "progress": 100},
            {"title": "任务C", "progress": "50%"},
        ]
    })
    output, err = process_input(edge_data, "json")
    assert err is None, f"边界数据处理失败: {err}"
    print("  [PASS] 边界数据处理")

    print("\n所有自检通过！")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="周报生成工具 - 将输入数据转换为结构化周报",
        epilog="示例: python main.py --input '{\"items\": [{\"title\": \"任务A\", \"progress\": 0.5}]}' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入内容（JSON 或文本格式）")
    parser.add_argument("--file", "-f", type=str, help="从文件读取输入（可选）")
    parser.add_argument("--format", "-t", type=str, choices=["text", "json", "markdown"], default="text",
                        help="输出格式 (默认: text)")
    parser.add_argument("--batch", "-b", action="store_true", help="批量模式（每行一个输入）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="周报生成 v1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 读取输入
    raw_input = args.input
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                raw_input = fh.read()
        except (IOError, OSError) as e:
            err = make_error("E006", detail=f"读取文件失败: {e}")
            print(f"[{err['error_code']}] {err['message']}", file=sys.stderr)
            return 1

    if raw_input is None:
        parser.print_help()
        return 0

    # 批量模式
    if args.batch:
        lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
        if not lines:
            err = make_error("E001")
            print(f"[{err['error_code']}] {err['message']}", file=sys.stderr)
            return 1
        results, err = batch_process(lines, args.format)
        if err:
            print(f"[{err['error_code']}] {err['message']}", file=sys.stderr)
            return 1
        for result in results:
            print(result)
            print("---")
        return 0

    # 单条处理
    output, err = process_input(raw_input, args.format)
    if err:
        print(f"[{err['error_code']}] {err['message']}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
