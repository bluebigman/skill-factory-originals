#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reviewday — 代码评审结构化汇总与置信标注
版本: 1.0.5
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
        if not isinstance(self.description, str) or not self.description.strip():
            error_exit("E006", "描述字段缺失或为空")
        if self.severity not in SEVERITY_LEVELS:
            error_exit("E007", f"无效的严重级别: {self.severity}")
        if not isinstance(self.confidence, (int, float)) or not (0.0 <= self.confidence <= 1.0):
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

    # 测试8: 空输入处理
    empty_items = parse_review_text("")
    assert len(empty_items) == 0, "空输入应返回空列表"
    print("  [通过] 空输入处理")

    # 测试9: 无效置信度校验
    try:
        invalid_item = ReviewItem("test.py", 1, "测试", "一般", 1.5)
        invalid_item.validate()
        assert False, "置信度超出范围应抛出错误"
    except SystemExit:
        print("  [通过] 无效置信度校验")

    # 测试10: 无效严重级别校验
    try:
        invalid_item = ReviewItem("test.py", 1, "测试", "无效级别", 0.5)
        invalid_item.validate()
        assert False, "无效严重级别应抛出错误"
    except SystemExit:
        print("  [通过] 无效严重级别校验")

    # 测试11: 边界置信度（0.0 和 1.0 应合法）
    try:
        edge_item = ReviewItem("test.py", 1, "边界测试", "一般", 0.0)
        edge_item.validate()
        edge_item2 = ReviewItem("test.py", 1, "边界测试", "一般", 1.0)
        edge_item2.validate()
        print("  [通过] 边界置信度校验")
    except SystemExit:
        assert False, "边界置信度不应抛出错误"

    # 测试12: 文件路径缺失校验
    try:
        invalid_item = ReviewItem("", 1, "测试", "一般", 0.5)
        invalid_item.validate()
        assert False, "空文件路径应抛出错误"
    except SystemExit:
        print("  [通过] 空文件路径校验")

    # 测试13: 负行号处理（不报错，但标记需核实）
    neg_item = ReviewItem("test.py", -5, "负行号测试", "一般", 0.9)
    neg_item.validate()
    neg_dict = neg_item.to_dict()
    assert neg_dict["line"] == -5, "负行号应保留"
    print("  [通过] 负行号处理")

    # 测试14: 高置信度不标记需核实
    high_conf_item = ReviewItem("test.py", 10, "高置信度", "一般", 0.9)
    high_conf_item.validate()
    high_conf_dict = high_conf_item.to_dict()
    assert "needs_verification" not in high_conf_dict, "高置信度不应标记需核实"
    print("  [通过] 高置信度处理")

    # 测试15: 中置信度（0.6）不标记需核实
    med_conf_item = ReviewItem("test.py", 10, "中置信度", "一般", 0.6)
    med_conf_item.validate()
    med_conf_dict = med_conf_item.to_dict()
    assert "needs_verification" not in med_conf_dict, "中置信度不应标记需核实"
    print("  [通过] 中置信度处理")

    # 测试16: 低置信度（0.59）标记需核实
    low_conf_item2 = ReviewItem("test.py", 10, "低置信度", "一般", 0.59)
    low_conf_item2.validate()
    low_conf_dict2 = low_conf_item2.to_dict()
    assert "needs_verification" in low_conf_dict2, "低置信度应标记需核实"
    print("  [通过] 低置信度处理")

    # 测试17: 空描述处理
    try:
        empty_desc_item = ReviewItem("test.py", 1, "", "一般", 0.5)
        empty_desc_item.validate()
        assert False, "空描述应抛出错误"
    except SystemExit:
        print("  [通过] 空描述校验")

    # 测试18: 非字符串描述处理
    try:
        non_str_item = ReviewItem("test.py", 1, 12345, "一般", 0.5)
        non_str_item.validate()
        assert False, "非字符串描述应抛出错误"
    except SystemExit:
        print("  [通过] 非字符串描述校验")

    # 测试19: 非字符串文件路径处理
    try:
        non_str_path = ReviewItem(12345, 1, "测试", "一般", 0.5)
        non_str_path.validate()
        assert False, "非字符串文件路径应抛出错误"
    except SystemExit:
        print("  [通过] 非字符串文件路径校验")

    # 测试20: 文本解析 - 无行号格式
    no_line_items = parse_review_text("src/config.py 配置文件缺少默认值")
    assert len(no_line_items) == 1, f"无行号格式应解析1条，实际{len(no_line_items)}"
    assert no_line_items[0].line_number == 0, "无行号格式行号应为0"
    print("  [通过] 无行号格式解析")

    # 测试21: 文本解析 - 带冒号无行号格式
    colon_no_line_items = parse_review_text("src/config.py: 配置文件缺少默认值")
    assert len(colon_no_line_items) == 1, f"冒号无行号格式应解析1条，实际{len(colon_no_line_items)}"
    assert colon_no_line_items[0].line_number == 0, "冒号无行号格式行号应为0"
    print("  [通过] 冒号无行号格式解析")

    # 测试22: 文本解析 - 无效行跳过
    invalid_line_items = parse_review_text("这是一行无效内容\nsrc/main.py:42 有效内容")
    assert len(invalid_line_items) == 1, f"无效行应跳过，实际{len(invalid_line_items)}"
    print("  [通过] 无效行跳过")

    # 测试23: JSON 解析 - 单对象
    single_obj_items = parse_review_text('{"file": "test.py", "line": 5, "description": "测试"}')
    assert len(single_obj_items) == 1, f"单对象应解析1条，实际{len(single_obj_items)}"
    print("  [通过] JSON 单对象解析")

    # 测试24: JSON 解析 - 缺失字段跳过
    missing_field_items = parse_review_text('[{"file": "test.py", "line": 5}, {"file": "test2.py", "description": "测试"}]')
    assert len(missing_field_items) == 1, f"缺失字段应跳过，实际{len(missing_field_items)}"
    print("  [通过] JSON 缺失字段跳过")

    # 测试25: JSON 解析 - 非对象元素跳过
    non_obj_items = parse_review_text('[1, 2, {"file": "test.py", "description": "测试"}]')
    assert len(non_obj_items) == 1, f"非对象元素应跳过，实际{len(non_obj_items)}"
    print("  [通过] JSON 非对象元素跳过")

    # 测试26: 严重级别分类 - 关键词匹配
    blocker_item = ReviewItem("test.py", 1, "系统崩溃", "一般", 0.9)
    assert classify_severity(blocker_item) == "阻断", "崩溃应分类为阻断"
    major_item = ReviewItem("test.py", 1, "内存泄漏", "一般", 0.9)
    assert classify_severity(major_item) == "严重", "内存泄漏应分类为严重"
    minor_item = ReviewItem("test.py", 1, "代码规范问题", "一般", 0.9)
    assert classify_severity(minor_item) == "一般", "规范问题应分类为一般"
    suggestion_item = ReviewItem("test.py", 1, "建议优化", "一般", 0.9)
    assert classify_severity(suggestion_item) == "建议", "建议优化应分类为建议"
    print("  [通过] 严重级别关键词分类")

    # 测试27: 严重级别分类 - 无关键词保持原级别
    no_keyword_item = ReviewItem("test.py", 1, "自定义问题", "严重", 0.9)
    assert classify_severity(no_keyword_item) == "严重", "无关键词应保持原级别"
    print("  [通过] 严重级别无关键词保持")

    # 测试28: 报告生成 - 空列表
    empty_report_json = generate_report([], "json")
    assert empty_report_json == "[]", "空JSON报告应为[]"
    empty_report_md = generate_report([], "markdown")
    assert "无审查条目" in empty_report_md, "空Markdown报告应包含无审查条目"
    print("  [通过] 空报告生成")

    # 测试29: 报告生成 - 无效格式
    try:
        generate_report(items, "xml")
        assert False, "无效格式应抛出错误"
    except SystemExit:
        print("  [通过] 无效格式校验")

    # 测试30: 合并 - 不同描述相同位置不去重
    diff_desc_items = [
        ReviewItem("test.py", 1, "问题A", "一般", 0.9),
        ReviewItem("test.py", 1, "问题B", "一般", 0.9),
    ]
    merged_diff = merge_review_items(diff_desc_items)
    assert merged_diff["total_count"] == 2, "不同描述不应去重"
    print("  [通过] 合并不同描述不去重")

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
