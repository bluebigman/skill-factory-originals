#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reviewday — 代码评审结构化汇总与置信标注
版本: 1.0.3
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "输入参数无效",
    "E002": "输入文件不存在或无法读取",
    "E003": "JSON 解析失败",
    "E004": "输入数据格式不符合预期",
    "E005": "输出目录不存在或无法写入",
    "E006": "内部逻辑错误",
    "E007": "严重级别无效",
    "E008": "置信度数值超出范围",
    "E009": "文件路径字段缺失或为空",
    "E010": "未知错误",
}

# 严重级别定义（从高到低）
SEVERITY_LEVELS = ["阻断", "严重", "一般", "建议"]

# 置信度阈值
HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.6


def error_exit(code: str, message: str = None) -> None:
    """输出错误信息并退出"""
    msg = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
    sys.stderr.write(f"[{code}] {msg}\n")
    sys.exit(1)


class ReviewItem:
    """单条审查条目"""

    def __init__(self, file_path: str, line_number: int, description: str,
                 severity: str = "一般", confidence: float = 0.7):
        self.file_path = file_path
        self.line_number = line_number
        self.description = description
        self.severity = severity
        self.confidence = confidence

    def validate(self) -> None:
        """校验字段合法性"""
        if not self.file_path or not isinstance(self.file_path, str):
            error_exit("E009", "文件路径字段缺失或为空")
        if self.severity not in SEVERITY_LEVELS:
            error_exit("E007", f"无效的严重级别: {self.severity}")
        if not (0.0 <= self.confidence <= 1.0):
            error_exit("E008", f"置信度超出范围: {self.confidence}")

    def to_dict(self) -> dict:
        """转为字典"""
        result = {
            "file": self.file_path,
            "line": self.line_number,
            "description": self.description,
            "severity": self.severity,
            "confidence": round(self.confidence, 2),
        }
        # 低置信度条目自动标记
        if self.confidence < MEDIUM_CONFIDENCE:
            result["needs_verification"] = self._find_low_conf_fields()
        return result

    def _find_low_conf_fields(self) -> list:
        """找出需要核实的字段"""
        fields = []
        if self.confidence < MEDIUM_CONFIDENCE:
            fields.append("description")
            if self.line_number <= 0:
                fields.append("line")
        return fields


def parse_review_text(text: str) -> list:
    """解析原始审查文本为 ReviewItem 列表

    支持格式:
    - "文件路径:行号 描述"
    - "文件路径 行号: 描述"
    - 结构化 JSON 数组
    """
    text = text.strip()
    if not text:
        return []

    # 尝试 JSON 解析
    if text.startswith("[") or text.startswith("{"):
        try:
            data = json.loads(text)
            return parse_json_data(data)
        except json.JSONDecodeError:
            pass

    # 文本行解析
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        item = parse_text_line(line)
        if item:
            items.append(item)
    return items


def parse_text_line(line: str) -> ReviewItem:
    """解析单行文本为 ReviewItem"""
    # 模式1: "路径:行号 描述"
    match = re.match(r'^(.+?):(\d+)\s+(.+)$', line)
    if match:
        return ReviewItem(match.group(1), int(match.group(2)), match.group(3))

    # 模式2: "路径 行号: 描述"
    match = re.match(r'^(.+?)\s+(\d+):\s+(.+)$', line)
    if match:
        return ReviewItem(match.group(1), int(match.group(2)), match.group(3))

    # 模式3: 仅 "路径: 描述"（无行号）
    match = re.match(r'^(.+?):\s+(.+)$', line)
    if match:
        return ReviewItem(match.group(1), 0, match.group(2))

    return None


def parse_json_data(data) -> list:
    """解析 JSON 数据为 ReviewItem 列表"""
    items = []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        error_exit("E004", "JSON 数据必须是对象或数组")

    for entry in data:
        if not isinstance(entry, dict):
            continue
        file_path = entry.get("file") or entry.get("path") or entry.get("file_path")
        line_number = entry.get("line") or entry.get("line_number") or 0
        description = entry.get("description") or entry.get("message") or entry.get("issue")
        severity = entry.get("severity") or "一般"
        confidence = entry.get("confidence", 0.7)

        if file_path and description:
            items.append(ReviewItem(
                file_path=str(file_path),
                line_number=int(line_number),
                description=str(description),
                severity=str(severity),
                confidence=float(confidence)
            ))
    return items


def classify_severity(item: ReviewItem) -> str:
    """严重级别分类（基于关键词）"""
    text = item.description.lower()
    keywords = {
        "阻断": ["crash", "崩溃", "安全漏洞", "数据丢失", "blocker", "critical"],
        "严重": ["严重", "major", "内存泄漏", "性能问题", "死锁"],
        "一般": ["一般", "minor", "规范", "建议修改"],
        "建议": ["建议", "优化", "suggestion", "风格"],
    }
    for level, words in keywords.items():
        if any(word in text for word in words):
            return level
    return item.severity  # 保持原分级


def merge_review_items(items: list) -> dict:
    """合并审查条目，去重并统计频次"""
    # 去重（基于文件+行号+描述）
    seen = set()
    unique_items = []
    for item in items:
        key = (item.file_path, item.line_number, item.description)
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    # 按文件分组
    grouped = {}
    for item in unique_items:
        if item.file_path not in grouped:
            grouped[item.file_path] = []
        grouped[item.file_path].append(item)

    # 统计频次
    freq = Counter((item.file_path, item.line_number) for item in unique_items)

    return {
        "grouped": grouped,
        "unique_items": unique_items,
        "frequency": freq,
        "total_count": len(unique_items),
    }


def generate_report(items: list, output_format: str = "json") -> str:
    """生成结构化报告"""
    if not items:
        return "[]" if output_format == "json" else "# 审查报告\n\n无审查条目。"

    # 严重级别分类统计
    severity_count = Counter(item.severity for item in items)

    # 生成报告数据
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "total_issues": len(items),
        "severity_summary": dict(severity_count),
        "items": [item.to_dict() for item in items],
    }

    if output_format == "json":
        return json.dumps(report_data, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        return format_markdown(report_data)
    else:
        error_exit("E001", f"不支持的输出格式: {output_format}")


def format_markdown(data: dict) -> str:
    """格式化为 Markdown 报告"""
    lines = []
    lines.append("# 代码审查报告")
    lines.append("")
    lines.append(f"- **生成时间**: {data['generated_at']}")
    lines.append(f"- **问题总数**: {data['total_issues']}")
    lines.append("")
    lines.append("## 严重级别统计")
    lines.append("")
    lines.append("| 级别 | 数量 |")
    lines.append("|------|------|")
    for level in SEVERITY_LEVELS:
        count = data["severity_summary"].get(level, 0)
        lines.append(f"| {level} | {count} |")
    lines.append("")
    lines.append("## 问题清单")
    lines.append("")
    for item in data["items"]:
        lines.append(f"### {item['file']}:{item['line']}")
        lines.append("")
        lines.append(f"- **描述**: {item['description']}")
        lines.append(f"- **严重级别**: {item['severity']}")
        lines.append(f"- **置信度**: {item['confidence']}")
        if "needs_verification" in item:
            lines.append(f"- **需核实**: {', '.join(item['needs_verification'])}")
        lines.append("")
    return "\n".join(lines)


def process_file(input_path: str, output_path: str = None,
                 output_format: str = "json") -> None:
    """处理单个审查文件"""
    try:
        input_file = Path(input_path)
        if not input_file.exists():
            error_exit("E002", f"文件不存在: {input_path}")
        text = input_file.read_text(encoding="utf-8")
    except (IOError, OSError) as e:
        error_exit("E002", f"读取文件失败: {e}")

    items = parse_review_text(text)

    # 校验所有条目
    for item in items:
        item.validate()
        # 尝试自动分类严重级别
        item.severity = classify_severity(item)

    report = generate_report(items, output_format)

    if output_path:
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report, encoding="utf-8")
            print(f"报告已写入: {output_path}")
        except (IOError, OSError) as e:
            error_exit("E005", f"写入文件失败: {e}")
    else:
        print(report)


def run_selftest() -> None:
    """内置自检逻辑（不依赖外部文件）"""
    print("运行自检...")

    # 硬编码测试数据
    test_text = """
src/main.py:42 存在空指针引用风险
src/utils.py:15 建议使用更高效的排序算法
src/config.py 配置文件缺少默认值
src/main.py:55 严重性能问题，循环中执行数据库查询
src/utils.py:15 建议使用更高效的排序算法（重复项）
"""

    # 测试1: 文本解析
    items = parse_review_text(test_text)
    assert len(items) >= 4, f"解析条目数应>=4，实际{len(items)}"
    print(f"  [通过] 文本解析: {len(items)} 条")

    # 测试2: 去重合并
    merged = merge_review_items(items)
    assert merged["total_count"] <= len(items), "去重后数量不应增加"
    assert merged["total_count"] >= 3, f"去重后应>=3条，实际{merged['total_count']}"
    print(f"  [通过] 去重合并: {len(items)} -> {merged['total_count']} 条")

    # 测试3: 严重级别分类
    for item in items:
        item.validate()
        item.severity = classify_severity(item)
        assert item.severity in SEVERITY_LEVELS, f"无效级别: {item.severity}"
    print("  [通过] 严重级别分类")

    # 测试4: 置信度标注
    low_conf_item = ReviewItem("test.py", -1, "模糊描述", "一般", 0.4)
    low_conf_item.validate()
    low_conf_dict = low_conf_item.to_dict()
    assert "needs_verification" in low_conf_dict, "低置信度应标记需核实"
    assert len(low_conf_dict["needs_verification"]) > 0, "需核实字段不应为空"
    print("  [通过] 置信度标注")

    # 测试5: JSON 输出
    report_json = generate_report(items, "json")
    parsed = json.loads(report_json)
    assert parsed["total_issues"] == len(items), "JSON报告数量不匹配"
    assert "severity_summary" in parsed, "缺少严重级别统计"
    print("  [通过] JSON 报告生成")

    # 测试6: Markdown 输出
    report_md = generate_report(items, "markdown")
    assert report_md.startswith("#"), "Markdown 报告格式错误"
    assert "问题清单" in report_md, "Markdown 缺少问题清单"
    print("  [通过] Markdown 报告生成")

    # 测试7: JSON 输入解析
    json_input = json.dumps([
        {"file": "src/app.py", "line": 10, "description": "测试问题", "severity": "严重", "confidence": 0.9},
        {"path": "src/lib.py", "line": 20, "message": "另一个问题", "severity": "一般", "confidence": 0.5},
    ])
    json_items = parse_review_text(json_input)
    assert len(json_items) == 2, f"JSON解析应得2条，实际{len(json_items)}"
    print("  [通过] JSON 输入解析")

    print("全部自检通过 ✓")


def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="reviewday - 代码评审结构化汇总与置信标注",
        epilog="示例: python main.py input.txt -o report.json --format json"
    )
    parser.add_argument("input", nargs="?", help="输入审查文件路径")
    parser.add_argument("-o", "--output", help="输出报告文件路径")
    parser.add_argument("-f", "--format", choices=["json", "markdown"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not args.input:
        error_exit("E001", "请提供输入文件路径（或使用 --selftest 运行自检）")

    process_file(args.input, args.output, args.format)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        error_exit("E010", "用户中断执行")
    except Exception as e:
        error_exit("E006", f"未预期错误: {e}")
