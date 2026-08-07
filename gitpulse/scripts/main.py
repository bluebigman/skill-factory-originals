#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gitpulse 周报生成工具 - 独立实现脚本

功能：将用户提供的文本数据转换为结构化周报/日报/月报。
本脚本为 clean-room 实现，仅依据功能规格编写。

用法：
    python scripts/main.py --selftest    # 运行内置自检
    python scripts/main.py --input "..." # 处理输入文本
"""

import argparse
import sys
import re
from datetime import datetime, timedelta
from collections import Counter

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "输出格式错误",
    "E008": "参数错误",
    "E009": "文件读取失败",
    "E010": "未知错误",
}


class GitPulseError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class WorkItem:
    """单个工作条目"""
    def __init__(self, title: str = "", category: str = "其他",
                 status: str = "进行中", confidence: float = 1.0):
        self.title = title
        self.category = category
        self.status = status
        self.confidence = confidence

    def to_dict(self):
        return {
            "title": self.title,
            "category": self.category,
            "status": self.status,
            "confidence": self.confidence,
        }


class Report:
    """报告对象"""
    def __init__(self, report_type: str = "周报"):
        self.report_type = report_type
        self.items = []
        self.generated_at = datetime.now()
        self.summary = ""

    def add_item(self, item: WorkItem):
        self.items.append(item)

    def to_dict(self):
        return {
            "report_type": self.report_type,
            "generated_at": self.generated_at.isoformat(),
            "item_count": len(self.items),
            "items": [i.to_dict() for i in self.items],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw_text: str) -> list:
    """
    解析输入文本，提取工作条目。
    支持格式：
      - 每行一个条目
      - 支持 "标题 | 分类 | 状态" 格式
      - 支持 "标题，分类，状态" 格式
      - 纯文本行（自动分类）
    """
    if not raw_text or not raw_text.strip():
        raise GitPulseError("E001")

    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    if not lines:
        raise GitPulseError("E001")

    items = []
    for line in lines:
        # 尝试多种分隔符
        parts = None
        for sep in ["|", "，", ","]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep)]
                break

        if parts and len(parts) >= 1:
            title = parts[0]
            category = parts[1] if len(parts) > 1 and parts[1] else "其他"
            status = parts[2] if len(parts) > 2 and parts[2] else "进行中"
            # 简单置信度判断：有完整三段信息则高置信度
            confidence = 0.95 if len(parts) >= 3 else 0.85
        else:
            title = line
            category = _guess_category(line)
            status = "进行中"
            confidence = 0.75  # 自动推断，置信度较低

        items.append(WorkItem(title=title, category=category,
                              status=status, confidence=confidence))

    return items


def _guess_category(text: str) -> str:
    """根据关键词猜测分类"""
    keywords = {
        "开发": ["开发", "编码", "实现", "编程", "代码"],
        "测试": ["测试", "验证", "调试", "修复"],
        "文档": ["文档", "写", "编写", "整理"],
        "会议": ["会议", "讨论", "评审", "对齐"],
        "运维": ["部署", "上线", "运维", "监控"],
    }
    for cat, words in keywords.items():
        for w in words:
            if w in text:
                return cat
    return "其他"


def generate_report(items: list, report_type: str = "周报") -> Report:
    """生成报告对象"""
    if not items:
        raise GitPulseError("E001")

    report = Report(report_type=report_type)
    for item in items:
        report.add_item(item)

    # 生成摘要
    total = len(items)
    categories = Counter(i.category for i in items)
    cat_summary = "、".join(f"{k}({v}项)" for k, v in categories.most_common(3))
    report.summary = f"共{total}项工作，主要类别：{cat_summary}"

    return report


def format_text_output(report: Report) -> str:
    """格式化为文本输出"""
    lines = []
    lines.append(f"===== {report.report_type} =====")
    lines.append(f"生成时间：{report.generated_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"摘要：{report.summary}")
    lines.append("")

    for idx, item in enumerate(report.items, 1):
        conf_tag = ""
        if item.confidence < 0.85:
            conf_tag = " [需核实]"
        elif item.confidence < 0.9:
            conf_tag = " [建议复核]"

        lines.append(f"{idx}. [{item.category}] {item.title} "
                     f"({item.status}){conf_tag}")

    lines.append("")
    lines.append("置信度说明：≥90% 直接输出；85%-90% 建议复核；<85% 需核实")
    return "\n".join(lines)


def process_input(raw_text: str, report_type: str = "周报") -> dict:
    """
    主处理函数：输入文本 -> 结构化报告
    """
    if not raw_text or not raw_text.strip():
        raise GitPulseError("E001")

    # 解析
    items = parse_input(raw_text)
    if not items:
        raise GitPulseError("E001")

    # 生成报告
    report = generate_report(items, report_type)

    # 返回结构化结果
    return report.to_dict()


# ---------------------------------------------------------------------------
# 自检逻辑（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    所有断言使用宽松阈值，不依赖精确值。
    """
    print("开始自检...")

    # 测试用例 1：基本解析与生成
    sample_input = (
        "完成登录模块开发 | 开发 | 已完成\n"
        "编写API文档 | 文档 | 进行中\n"
        "修复支付接口bug，测试，已完成\n"
        "参加需求评审会议"
    )

    try:
        items = parse_input(sample_input)
        assert len(items) >= 3, "解析条目数应不少于3"
        assert all(i.title for i in items), "每个条目必须有标题"

        report = generate_report(items, "周报")
        assert len(report.items) == len(items), "报告条目数应等于输入条目数"
        assert report.summary, "摘要不应为空"

        # 验证分类合理性（宽松断言）
        categories = [i.category for i in items]
        assert any(c in categories for c in ["开发", "文档", "测试", "会议"]), \
            "应能识别至少一个已知分类"

        # 验证置信度范围
        for item in items:
            assert 0 <= item.confidence <= 1, "置信度应在0-1之间"

        # 验证输出格式
        text_out = format_text_output(report)
        assert "周报" in text_out, "输出应包含报告类型"
        assert len(text_out) > 50, "输出应有足够长度"

        # 验证结构化输出
        result_dict = process_input(sample_input)
        assert "report_type" in result_dict
        assert "items" in result_dict
        assert len(result_dict["items"]) >= 3

        print("  ✓ 基本解析与生成测试通过")

    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1
    except GitPulseError as e:
        print(f"  ✗ 处理错误: {e}")
        return 1

    # 测试用例 2：错误处理
    try:
        process_input("")
        print("  ✗ 空输入应抛出E001")
        return 1
    except GitPulseError as e:
        assert e.code == "E001", f"错误码应为E001，实际{e.code}"
        print("  ✓ 空输入错误处理测试通过")

    # 测试用例 3：边界情况
    try:
        # 只有标题的输入
        items = parse_input("只有标题的内容")
        assert len(items) == 1, "单行输入应解析为一个条目"
        # 置信度应较低（自动推断）
        assert items[0].confidence < 0.9, "自动推断置信度应较低"
        print("  ✓ 边界情况测试通过")

    except Exception as e:
        print(f"  ✗ 边界测试失败: {e}")
        return 1

    # 测试用例 4：批量数据
    try:
        batch_input = "\n".join([
            f"工作项{i} | 开发 | 进行中" for i in range(5)
        ])
        items = parse_input(batch_input)
        assert len(items) == 5, "应解析5个条目"
        assert all(i.category == "开发" for i in items), "分类应正确解析"
        print("  ✓ 批量数据处理测试通过")

    except Exception as e:
        print(f"  ✗ 批量测试失败: {e}")
        return 1

    # 测试用例 5：摘要与统计
    try:
        mixed_input = (
            "任务A | 开发 | 已完成\n"
            "任务B | 测试 | 已完成\n"
            "任务C | 文档 | 进行中\n"
            "任务D | 开发 | 进行中"
        )
        report = generate_report(parse_input(mixed_input), "日报")
        assert "4项" in report.summary, "摘要应包含总数"
        assert "开发" in report.summary, "摘要应包含主要类别"
        assert report.report_type == "日报", "报告类型应正确"
        print("  ✓ 摘要统计测试通过")

    except Exception as e:
        print(f"  ✗ 摘要测试失败: {e}")
        return 1

    print("全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="gitpulse 周报生成工具 - 本地优先的工作报告生成器",
        epilog="示例: python main.py --input '完成登录模块 | 开发 | 已完成'"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入文本内容，支持多行，每行一个工作条目"
    )
    parser.add_argument(
        "--type", "-t",
        default="周报",
        choices=["日报", "周报", "月报"],
        help="报告类型（默认：周报）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 处理输入
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest", file=sys.stderr)
        print(f"错误码 E008: {ERROR_CODES['E008']}", file=sys.stderr)
        sys.exit(1)

    try:
        result = process_input(args.input, args.type)
        # 输出文本格式报告
        report = Report(report_type=result["report_type"])
        for item_dict in result["items"]:
            report.add_item(WorkItem(
                title=item_dict["title"],
                category=item_dict["category"],
                status=item_dict["status"],
                confidence=item_dict["confidence"]
            ))
        report.generated_at = datetime.fromisoformat(result["generated_at"])
        report.summary = result["summary"]
        print(format_text_output(report))

    except GitPulseError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误码 E010: {ERROR_CODES['E010']}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
