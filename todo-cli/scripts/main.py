#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
todo-cli 命令行工具（独立实现）

功能：将输入文本解析为结构化待办事项，支持多种输出格式。
仅依据功能规格独立实现，不包含任何既有代码。
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "文件读取失败：无法读取指定的输入文件",
    "E003": "URL 获取失败：无法获取指定的 URL 内容",
    "E004": "数据解析失败：无法解析输入内容",
    "E005": "输出格式错误：不支持的输出格式",
    "E006": "模板渲染失败：自定义模板无效",
    "E007": "批量处理失败：目录读取错误",
    "E008": "内部错误：未知异常",
    "E009": "自检失败：核心逻辑验证未通过",
    "E010": "输入内容为空：没有可解析的数据",
}


class TodoCliError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class TodoItem:
    """待办事项数据结构"""

    def __init__(
        self,
        task: str,
        due: str = "",
        priority: str = "",
        confidence: float = 1.0,
        source: str = "",
    ):
        self.task = task
        self.due = due
        self.priority = priority
        self.confidence = confidence  # 0.0 ~ 1.0
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task": self.task,
            "due": self.due,
            "priority": self.priority,
            "confidence": round(self.confidence, 2),
            "source": self.source,
        }


# ============================================================
# 解析器：从非结构化文本提取待办要素
# ============================================================
class TodoParser:
    """将文本解析为 TodoItem 列表"""

    # 优先级关键词映射
    PRIORITY_MAP = {
        "高": "高",
        "紧急": "高",
        "urgent": "高",
        "high": "高",
        "中": "中",
        "medium": "中",
        "normal": "中",
        "低": "低",
        "low": "低",
        "不急": "低",
    }

    # 日期关键词映射（宽松匹配）
    DUE_KEYWORDS = {
        "今天": "今天",
        "今日": "今天",
        "明天": "明天",
        "明日": "明天",
        "后天": "后天",
        "周五": "周五",
        "星期五": "周五",
        "下周一": "下周一",
        "月底": "月底",
    }

    # 置信度阈值：明确标注的字段置信度高，推断的置信度低
    HIGH_CONFIDENCE = 0.95
    MEDIUM_CONFIDENCE = 0.80
    LOW_CONFIDENCE = 0.60

    def parse(self, text: str, source: str = "") -> List[TodoItem]:
        """
        解析文本为待办事项列表。
        支持两种输入：
        1. 单行文本：整体作为一个待办
        2. 多行文本：每行作为一个待办
        """
        if not text or not text.strip():
            raise TodoCliError("E010")

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise TodoCliError("E010")

        items = []
        for line in lines:
            item = self._parse_single(line, source)
            if item:
                items.append(item)

        if not items:
            raise TodoCliError("E004")

        return items

    def _parse_single(self, line: str, source: str) -> Optional[TodoItem]:
        """解析单行文本为一个待办事项"""
        if not line:
            return None

        original = line

        # 提取优先级（先处理括号内的，再处理行首关键词）
        priority, confidence_p, line_after_p = self._extract_priority(line)

        # 提取截止日期
        due, confidence_d, line_after_d = self._extract_due(line_after_p)

        # 提取任务描述（去除括号内的优先级/日期标注）
        task_text = self._clean_task(line_after_d)

        if not task_text:
            task_text = line  # 兜底：如果清理后为空，使用原文本

        # 综合置信度：取各字段置信度的最小值
        confidence = min(confidence_p, confidence_d)

        return TodoItem(
            task=task_text,
            due=due,
            priority=priority,
            confidence=confidence,
            source=source,
        )

    def _extract_priority(self, text: str):
        """提取优先级信息，返回 (优先级, 置信度, 剩余文本)"""
        # 匹配模式1：括号内包含优先级关键词（如：高优先级、低优先级）
        pattern1 = r"[（(]\s*(高|中|低|紧急|urgent|high|medium|low|normal|不急)\s*优先级?\s*[)）]"
        match1 = re.search(pattern1, text, re.IGNORECASE)
        
        if match1:
            keyword = match1.group(1).lower()
            priority = self.PRIORITY_MAP.get(keyword, "中")
            remaining = text[: match1.start()] + text[match1.end():]
            return priority, self.HIGH_CONFIDENCE, remaining

        # 匹配模式2：括号内仅包含优先级关键词
        pattern2 = r"[（(]\s*(高|中|低|紧急|urgent|high|medium|low|normal|不急)\s*[)）]"
        match2 = re.search(pattern2, text, re.IGNORECASE)
        
        if match2:
            keyword = match2.group(1).lower()
            priority = self.PRIORITY_MAP.get(keyword, "中")
            remaining = text[: match2.start()] + text[match2.end():]
            return priority, self.HIGH_CONFIDENCE, remaining

        # 匹配模式3：括号内包含"优先级"字样（如：高优先级）
        pattern3 = r"[（(]\s*(高|中|低|紧急)\s*优先级\s*[)）]"
        match3 = re.search(pattern3, text, re.IGNORECASE)
        
        if match3:
            keyword = match3.group(1).lower()
            priority = self.PRIORITY_MAP.get(keyword, "中")
            remaining = text[: match3.start()] + text[match3.end():]
            return priority, self.HIGH_CONFIDENCE, remaining

        # 无括号标注，尝试识别行首关键词
        for keyword, priority in self.PRIORITY_MAP.items():
            if text.lower().startswith(keyword):
                remaining = text[len(keyword):].strip()
                if remaining:
                    return priority, self.MEDIUM_CONFIDENCE, remaining

        # 未找到优先级
        return "", self.HIGH_CONFIDENCE, text

    def _extract_due(self, text: str):
        """提取截止日期信息，返回 (日期, 置信度, 剩余文本)"""
        # 匹配模式1：括号内包含日期关键词
        pattern1 = r"[（(]\s*(今天|今日|明天|明日|后天|周五|星期五|下周一|月底|尽快|asap)\s*[)）]"
        match1 = re.search(pattern1, text, re.IGNORECASE)

        if match1:
            keyword = match1.group(1).lower()
            due = self.DUE_KEYWORDS.get(keyword, "")
            if not due:
                due = "[需核实:截止日期]"  # 无法明确映射时使用占位符
            remaining = text[: match1.start()] + text[match1.end():]
            return due, self.HIGH_CONFIDENCE, remaining

        # 匹配模式2："XX前完成"
        pattern2 = r"(.+?)\s*前\s*完成"
        match2 = re.search(pattern2, text)
        if match2:
            due = match2.group(1).strip()
            remaining = text[: match2.start()] + text[match2.end():]
            return due, self.MEDIUM_CONFIDENCE, remaining

        # 匹配模式3：行首日期关键词（如：今天 完成XXX）
        for keyword, due in self.DUE_KEYWORDS.items():
            if text.startswith(keyword):
                remaining = text[len(keyword):].strip()
                if remaining:
                    return due, self.MEDIUM_CONFIDENCE, remaining

        # 未找到日期
        return "", self.HIGH_CONFIDENCE, text

    def _clean_task(self, text: str) -> str:
        """清理任务描述文本"""
        # 去除所有括号内容（包括中文和英文括号）
        text = re.sub(r"[（(][^）)]*[)）]", "", text)
        # 去除多余空白
        text = re.sub(r"\s+", " ", text).strip()
        # 去除行首的连字符、星号等标记
        text = re.sub(r"^[-*•·]\s*", "", text)
        # 去除行首的优先级关键词（如果提取时未完全移除）
        for keyword in ["高优先级", "中优先级", "低优先级", "紧急", "urgent", "high", "medium", "low", "normal", "不急"]:
            if text.lower().startswith(keyword):
                text = text[len(keyword):].strip()
                break
        return text


# ============================================================
# 格式化输出器
# ============================================================
class OutputFormatter:
    """将 TodoItem 列表格式化为指定格式输出"""

    @staticmethod
    def format_json(items: List[TodoItem]) -> str:
        """JSON 格式输出"""
        data = [item.to_dict() for item in items]
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def format_csv(items: List[TodoItem]) -> str:
        """CSV 格式输出"""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["task", "due", "priority", "confidence", "source"],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(item.to_dict())
        return output.getvalue()

    @staticmethod
    def format_table(items: List[TodoItem]) -> str:
        """表格格式输出"""
        if not items:
            return "（无待办事项）"

        # 计算列宽
        headers = ["任务", "截止日期", "优先级", "置信度"]
        rows = []
        for item in items:
            rows.append(
                [
                    item.task,
                    item.due or "-",
                    item.priority or "-",
                    f"{item.confidence:.0%}",
                ]
            )

        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # 生成表格
        lines = []
        # 表头
        header_line = " | ".join(
            h.ljust(col_widths[i]) for i, h in enumerate(headers)
        )
        lines.append(header_line)
        lines.append("-+-".join("-" * w for w in col_widths))
        # 数据行
        for row in rows:
            lines.append(
                " | ".join(
                    str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
                )
            )
        return "\n".join(lines)

    @staticmethod
    def format_custom(items: List[TodoItem], template: str) -> str:
        """自定义模板格式输出"""
        try:
            lines = []
            for item in items:
                line = template
                line = line.replace("{task}", item.task)
                line = line.replace("{due}", item.due or "")
                line = line.replace("{priority}", item.priority or "")
                line = line.replace("{confidence}", f"{item.confidence:.2f}")
                line = line.replace("{source}", item.source)
                lines.append(line)
            return "\n".join(lines)
        except Exception:
            raise TodoCliError("E006")


# ============================================================
# 输入数据加载器
# ============================================================
class InputLoader:
    """加载输入数据：支持文本、文件、URL"""

    @staticmethod
    def load_text(text: str) -> str:
        """直接使用文本输入"""
        if not text or not text.strip():
            raise TodoCliError("E010")
        return text

    @staticmethod
    def load_file(file_path: str) -> str:
        """从文件读取内容"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise TodoCliError("E002", f"文件不存在: {file_path}")
            return path.read_text(encoding="utf-8")
        except TodoCliError:
            raise
        except Exception as e:
            raise TodoCliError("E002", f"读取文件失败: {str(e)}")

    @staticmethod
    def load_url(url: str) -> str:
        """从 URL 获取内容（仅支持公开 URL）"""
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            raise TodoCliError("E003", f"获取 URL 失败: {str(e)}")

    @staticmethod
    def load_batch(directory: str) -> Dict[str, str]:
        """批量读取目录下所有文本文件"""
        try:
            path = Path(directory)
            if not path.is_dir():
                raise TodoCliError("E007", f"目录不存在: {directory}")

            contents = {}
            for file_path in sorted(path.glob("*.txt")):
                contents[file_path.name] = file_path.read_text(encoding="utf-8")
            return contents
        except TodoCliError:
            raise
        except Exception as e:
            raise TodoCliError("E007", f"批量读取失败: {str(e)}")


# ============================================================
# 核心处理逻辑
# ============================================================
class TodoProcessor:
    """主处理流程"""

    def __init__(self):
        self.parser = TodoParser()
        self.formatter = OutputFormatter()

    def process(
        self,
        content: str,
        source: str = "",
        output_format: str = "table",
        template: str = "",
    ) -> str:
        """处理输入内容并返回格式化结果"""
        # 解析
        items = self.parser.parse(content, source)

        # 格式化输出
        if output_format == "json":
            return self.formatter.format_json(items)
        elif output_format == "csv":
            return self.formatter.format_csv(items)
        elif output_format == "table":
            return self.formatter.format_table(items)
        elif output_format == "custom":
            if not template:
                raise TodoCliError("E006", "自定义格式需要提供模板")
            return self.formatter.format_custom(items, template)
        else:
            raise TodoCliError("E005", f"不支持的输出格式: {output_format}")


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值确保稳健性。
    """
    try:
        processor = TodoProcessor()

        # ---------- 测试用例 1：基本解析 ----------
        test1 = "周五前完成报告（高优先级）"
        items1 = processor.parser.parse(test1, source="selftest")
        assert len(items1) >= 1, "测试1: 应解析出至少一个待办"
        item1 = items1[0]
        assert item1.task, "测试1: 任务描述不应为空"
        assert "报告" in item1.task, "测试1: 任务描述应包含'报告'"
        assert item1.priority == "高", f"测试1: 优先级应为'高'，实际为'{item1.priority}'"
        assert item1.due == "周五", f"测试1: 截止日期应为'周五'，实际为'{item1.due}'"
        assert item1.confidence > 0.5, "测试1: 置信度应大于0.5"

        # ---------- 测试用例 2：多行输入 ----------
        test2 = "买菜\n打扫房间（明天）\n交水电费（低优先级）"
        items2 = processor.parser.parse(test2, source="selftest")
        assert len(items2) >= 3, "测试2: 应解析出至少三个待办"
        # 验证每项都有任务描述
        for item in items2:
            assert item.task, "测试2: 每项任务描述不应为空"

        # ---------- 测试用例 3：格式输出 ----------
        test3 = "测试任务"
        items3 = processor.parser.parse(test3, source="selftest")
        json_out = processor.formatter.format_json(items3)
        assert json_out, "测试3: JSON 输出不应为空"
        assert "task" in json_out, "测试3: JSON 应包含 task 字段"

        csv_out = processor.formatter.format_csv(items3)
        assert csv_out, "测试3: CSV 输出不应为空"
        assert "task" in csv_out, "测试3: CSV 应包含 task 列"

        table_out = processor.formatter.format_table(items3)
        assert table_out, "测试3: 表格输出不应为空"
        assert "任务" in table_out, "测试3: 表格应包含'任务'列"

        # ---------- 测试用例 4：置信度标注 ----------
        test4 = "尽快完成这个任务"
        items4 = processor.parser.parse(test4, source="selftest")
        item4 = items4[0]
        # "尽快"无法映射为具体日期，应使用占位符或空
        assert item4.due in ("", "[需核实:截止日期]"), "测试4: 模糊日期应使用占位符"

        # ---------- 测试用例 5：优先级提取 ----------
        test5 = "（紧急）处理服务器故障"
        items5 = processor.parser.parse(test5, source="selftest")
        item5 = items5[0]
        assert item5.priority == "高", f"测试5: '紧急'应映射为'高'优先级，实际为'{item5.priority}'"

        # ---------- 测试用例 6：完整流程 ----------
        test6 = "完成项目文档（明天）（高优先级）"
        result6 = processor.process(test6, source="selftest", output_format="json")
        assert result6, "测试6: 完整流程应返回结果"
        assert "完成项目文档" in result6, "测试6: 结果应包含任务描述"

        # ---------- 测试用例 7：批量处理 ----------
        test7_lines = ["任务A", "任务B（低）", "任务C（周五）"]
        test7 = "\n".join(test7_lines)
        items7 = processor.parser.parse(test7, source="selftest")
        assert len(items7) >= 3, "测试7: 应解析出至少三个待办"

        # ---------- 测试用例 8：自定义模板 ----------
        test8 = "测试模板任务"
        items8 = processor.parser.parse(test8, source="selftest")
        custom_out = processor.formatter.format_custom(
            items8, "[{priority}] {task} 截止:{due}"
        )
        assert custom_out, "测试8: 自定义模板输出不应为空"
        assert "测试模板任务" in custom_out, "测试8: 模板输出应包含任务"

        # 所有测试通过
        print("✅ 自检通过：所有核心逻辑验证成功")
        return True

    except AssertionError as e:
        print(f"❌ 自检失败: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 自检异常: {str(e)}")
        return False


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        prog="todo-cli",
        description="待办清单命令行工具：将输入数据解析为结构化待办事项并输出",
        epilog="示例: todo-cli parse --text '周五前完成报告（高优先级）' --format json",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse 子命令
    parse_parser = subparsers.add_parser("parse", help="解析输入数据")
    input_group = parse_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text", help="直接提供文本内容")
    input_group.add_argument("--file", help="从文件读取内容")
    input_group.add_argument("--url", help="从 URL 获取内容")
    parse_parser.add_argument("--format", choices=["json", "csv", "table", "custom"], default="table", help="输出格式")
    parse_parser.add_argument("--template", help="自定义输出模板（format=custom 时使用）")
    parse_parser.add_argument("--source", default="", help="数据来源标识")

    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量处理目录下的文件")
    batch_parser.add_argument("directory", help="包含 .txt 文件的目录路径")
    batch_parser.add_argument("--format", choices=["json", "csv", "table", "custom"], default="table", help="输出格式")
    batch_parser.add_argument("--template", help="自定义输出模板（format=custom 时使用）")

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检并退出")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 没有子命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0

    try:
        processor = TodoProcessor()

        # 处理 parse 子命令
        if args.command == "parse":
            # 加载输入
            if args.text:
                content = InputLoader.load_text(args.text)
                source = args.source or "命令行输入"
            elif args.file:
                content = InputLoader.load_file(args.file)
                source = args.source or args.file
            elif args.url:
                content = InputLoader.load_url(args.url)
                source = args.source or args.url
            else:
                raise TodoCliError("E001")

            # 处理并输出
            result = processor.process(
                content,
                source=source,
                output_format=args.format,
                template=args.template or "",
            )
            print(result)
            return 0

        # 处理 batch 子命令
        elif args.command == "batch":
            contents = InputLoader.load_batch(args.directory)
            if not contents:
                print("（目录中没有找到 .txt 文件）")
                return 0

            all_items = []
            for filename, content in contents.items():
                try:
                    items = processor.parser.parse(content, source=filename)
                    all_items.extend(items)
                except TodoCliError as e:
                    print(f"⚠️ 跳过 {filename}: {e}", file=sys.stderr)

            # 格式化输出
            if args.format == "json":
                print(processor.formatter.format_json(all_items))
            elif args.format == "csv":
                print(processor.formatter.format_csv(all_items))
            elif args.format == "custom":
                if not args.template:
                    raise TodoCliError("E006")
                print(processor.formatter.format_custom(all_items, args.template))
            else:
                print(processor.formatter.format_table(all_items))
            return 0

        else:
            raise TodoCliError("E001")

    except TodoCliError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E008']}] 未知异常: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
