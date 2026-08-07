#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实习日志结构化整理 Skill（internship-daily-log）
独立实现脚本：将杂乱实习笔记转换为结构化日志，支持批量处理与置信度标注。
仅依赖标准库，无需安装第三方包。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERR_INVALID_INPUT = "E001"      # 输入格式无效
ERR_EMPTY_RECORD = "E002"       # 记录内容为空
ERR_MISSING_TIME = "E003"       # 缺少时间字段
ERR_MISSING_DESC = "E004"       # 缺少事件描述
ERR_BATCH_EXCEED = "E005"       # 批量超过50条限制
ERR_INVALID_DATE = "E006"       # 日期格式无效
ERR_INVALID_FORMAT = "E007"     # 输出格式参数无效
ERR_FILTER_NO_MATCH = "E008"    # 过滤后无匹配记录
ERR_INTERNAL = "E009"           # 内部处理错误
ERR_ARGS = "E010"               # 命令行参数错误


# 预设字段别名映射（用户可自定义字段别名）
FIELD_ALIASES = {
    "date": ["日期", "时间", "date", "time", "day", "日"],
    "task": ["任务", "工作", "事件", "事项", "task", "work", "event", "todo"],
    "owner": ["负责人", "人员", "owner", "assignee", "person", "人"],
    "status": ["状态", "进度", "status", "state", "阶段"],
    "output": ["产出", "产出物", "成果", "output", "deliverable", "result", "结果"],
    "blocker": ["阻塞", "阻塞项", "问题", "风险", "blocker", "issue", "risk", "困难"],
    "note": ["备注", "说明", "note", "comment", "备注说明"],
}

# 状态归一化映射
STATUS_MAP = {
    "完成": "done", "已完成": "done", "done": "done", "finished": "done", "closed": "done",
    "进行中": "in_progress", "进行": "in_progress", "in_progress": "in_progress", "ongoing": "in_progress", "wip": "in_progress",
    "待开始": "pending", "未开始": "pending", "pending": "pending", "todo": "pending", "planned": "pending",
    "阻塞": "blocked", "受阻": "blocked", "blocked": "blocked", "stuck": "blocked",
    "取消": "cancelled", "已取消": "cancelled", "cancelled": "cancelled", "canceled": "cancelled",
}

# 置信度关键词权重（用于评估结构化提取的可信度）
HIGH_CONF_KEYWORDS = ["明确", "确定", "完成", "已", "确认"]
MED_CONF_KEYWORDS = ["可能", "大概", "估计", "也许", "或许"]
LOW_CONF_KEYWORDS = ["不确定", "未知", "待定", "待确认", "?"]


class DailyLogParser:
    """实习日志解析器：将非结构化文本转换为结构化记录。"""

    def __init__(self, custom_aliases: Optional[Dict[str, List[str]]] = None):
        """初始化解析器，可传入自定义字段别名。"""
        self.aliases = FIELD_ALIASES.copy()
        if custom_aliases:
            for field, aliases in custom_aliases.items():
                if field in self.aliases:
                    self.aliases[field].extend(aliases)
                else:
                    self.aliases[field] = aliases

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """解析输入文本，返回结构化记录列表。"""
        if not text or not text.strip():
            raise ValueError(f"{ERR_EMPTY_RECORD}: 输入文本为空")

        lines = self._split_lines(text)
        records = []
        current_date = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测日期行（如 2026-01-15 或 1月15日）
            date_match = self._extract_date(line)
            if date_match and self._is_date_only_line(line):
                current_date = date_match
                continue

            # 解析记录行
            record = self._parse_line(line, current_date)
            if record:
                records.append(record)

        if not records:
            raise ValueError(f"{ERR_MISSING_DESC}: 未找到有效记录（每条记录至少需要时间和事件描述）")

        return records

    def _split_lines(self, text: str) -> List[str]:
        """按换行符分割文本，兼容不同换行符。"""
        return re.split(r'\r\n|\r|\n', text)

    def _extract_date(self, line: str) -> Optional[str]:
        """从文本中提取日期，支持多种格式。"""
        # 格式: YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY年M月D日
        patterns = [
            r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{1,2}月\d{1,2}日)',
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return None

    def _is_date_only_line(self, line: str) -> bool:
        """判断是否仅为日期行（无其他内容）。"""
        date_str = self._extract_date(line)
        if not date_str:
            return False
        # 去除日期部分后，剩余内容应很少或没有
        remainder = re.sub(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}月\d{1,2}日', '', line)
        return len(remainder.strip()) < 5

    def _parse_line(self, line: str, default_date: Optional[str]) -> Optional[Dict[str, Any]]:
        """解析单行记录。"""
        # 跳过纯日期行
        if self._is_date_only_line(line):
            return None

        # 提取日期（优先行内日期，否则使用默认日期）
        date_str = self._extract_date(line) or default_date
        if not date_str:
            return None  # 无日期信息，跳过

        # 提取任务描述（去除日期前缀）
        task_desc = re.sub(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}月\d{1,2}日', '', line).strip()
        if not task_desc:
            return None

        # 提取各字段
        record = {
            "date": self._normalize_date(date_str),
            "task": task_desc,
            "owner": self._extract_field(task_desc, "owner"),
            "status": self._extract_status(task_desc),
            "output": self._extract_field(task_desc, "output"),
            "blocker": self._extract_field(task_desc, "blocker"),
            "note": self._extract_field(task_desc, "note"),
            "confidence": self._calculate_confidence(task_desc),
        }

        # 去除任务描述中已提取的字段信息，保留核心描述
        record["task"] = self._clean_task_desc(task_desc)

        return record

    def _extract_field(self, text: str, field: str) -> Optional[str]:
        """根据别名提取指定字段。"""
        aliases = self.aliases.get(field, [])
        for alias in aliases:
            # 匹配 "别名: 值" 或 "别名：值" 模式
            pattern = rf'{re.escape(alias)}\s*[:：]\s*([^,;，；]+)'
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_status(self, text: str) -> str:
        """提取并归一化状态。"""
        aliases = self.aliases.get("status", [])
        for alias in aliases:
            pattern = rf'{re.escape(alias)}\s*[:：]\s*([^,;，；]+)'
            match = re.search(pattern, text)
            if match:
                status_raw = match.group(1).strip().lower()
                if status_raw in STATUS_MAP:
                    return STATUS_MAP[status_raw]
                # 模糊匹配
                for key, value in STATUS_MAP.items():
                    if key in status_raw or status_raw in key:
                        return value
                return "unknown"
        return "pending"  # 默认状态

    def _normalize_date(self, date_str: str) -> str:
        """将日期字符串标准化为 YYYY-MM-DD 格式。"""
        try:
            # 处理 "2026年1月5日" 格式
            if '年' in date_str:
                parts = re.findall(r'\d+', date_str)
                if len(parts) >= 3:
                    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            # 处理 "1月5日" 格式（默认当前年份）
            elif '月' in date_str and '年' not in date_str:
                parts = re.findall(r'\d+', date_str)
                if len(parts) >= 2:
                    year = datetime.now().year
                    return f"{year:04d}-{int(parts[0]):02d}-{int(parts[1]):02d}"
            # 处理 "2026-1-5" 或 "2026/1/5" 格式
            else:
                date_str = date_str.replace('/', '-').replace('年', '-').replace('月', '-').replace('日', '')
                parts = date_str.split('-')
                if len(parts) >= 3:
                    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            raise ValueError("无法解析日期")
        except (ValueError, IndexError) as e:
            raise ValueError(f"{ERR_INVALID_DATE}: 日期格式无效 - {date_str}") from e

    def _calculate_confidence(self, text: str) -> float:
        """基于关键词计算置信度（0-1区间）。"""
        score = 0.5  # 基础置信度
        for kw in HIGH_CONF_KEYWORDS:
            if kw in text:
                score += 0.1
        for kw in MED_CONF_KEYWORDS:
            if kw in text:
                score -= 0.05
        for kw in LOW_CONF_KEYWORDS:
            if kw in text:
                score -= 0.15
        return max(0.1, min(0.95, score))

    def _clean_task_desc(self, text: str) -> str:
        """清理任务描述，去除已提取的字段标签。"""
        # 去除所有 "别名: 值" 模式
        for field, aliases in self.aliases.items():
            if field in ["date"]:
                continue
            for alias in aliases:
                pattern = rf'{re.escape(alias)}\s*[:：]\s*[^,;，；]+'
                text = re.sub(pattern, '', text)
        # 清理多余的分隔符和空白
        text = re.sub(r'[,;，；]+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text


class DailyLogFormatter:
    """格式化输出：支持 Markdown、JSON、纯文本三种格式。"""

    @staticmethod
    def to_markdown(records: List[Dict[str, Any]]) -> str:
        """输出 Markdown 表格。"""
        if not records:
            return "（无记录）"

        headers = ["日期", "任务", "负责人", "状态", "产出物", "阻塞项", "备注", "置信度"]
        lines = [
            "| " + " | ".join(headers) + " |",
            "|" + "---|" * len(headers),
        ]
        for rec in records:
            row = [
                rec.get("date", ""),
                rec.get("task", ""),
                rec.get("owner", ""),
                rec.get("status", ""),
                rec.get("output", ""),
                rec.get("blocker", ""),
                rec.get("note", ""),
                f"{rec.get('confidence', 0):.0%}",
            ]
            # 转义 Markdown 特殊字符
            row = [str(cell).replace("|", "\\|") for cell in row]
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    @staticmethod
    def to_json(records: List[Dict[str, Any]]) -> str:
        """输出 JSON 格式。"""
        return json.dumps({"records": records}, ensure_ascii=False, indent=2)

    @staticmethod
    def to_plain(records: List[Dict[str, Any]]) -> str:
        """输出纯文本清单。"""
        if not records:
            return "（无记录）"

        lines = []
        for i, rec in enumerate(records, 1):
            lines.append(f"记录 {i}:")
            lines.append(f"  日期: {rec.get('date', '')}")
            lines.append(f"  任务: {rec.get('task', '')}")
            if rec.get("owner"):
                lines.append(f"  负责人: {rec['owner']}")
            if rec.get("status"):
                lines.append(f"  状态: {rec['status']}")
            if rec.get("output"):
                lines.append(f"  产出物: {rec['output']}")
            if rec.get("blocker"):
                lines.append(f"  阻塞项: {rec['blocker']}")
            if rec.get("note"):
                lines.append(f"  备注: {rec['note']}")
            lines.append(f"  置信度: {rec.get('confidence', 0):.0%}")
            lines.append("")
        return "\n".join(lines)


def filter_records(records: List[Dict[str, Any]], start_date: Optional[str] = None,
                   end_date: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """按日期范围和状态过滤记录。"""
    filtered = records

    if start_date:
        filtered = [r for r in filtered if r.get("date", "") >= start_date]
    if end_date:
        filtered = [r for r in filtered if r.get("date", "") <= end_date]
    if status:
        filtered = [r for r in filtered if r.get("status", "") == status]

    return filtered


def process_batch(text: str, output_format: str = "markdown",
                  start_date: Optional[str] = None, end_date: Optional[str] = None,
                  status: Optional[str] = None, custom_aliases: Optional[Dict[str, List[str]]] = None) -> str:
    """批量处理入口：解析、过滤、格式化输出。"""
    try:
        # 检查批量大小（按行估算）
        line_count = len([l for l in re.split(r'\r\n|\r|\n', text) if l.strip()])
        if line_count > 50:
            raise ValueError(f"{ERR_BATCH_EXCEED}: 单批次最多处理50条记录，当前约{line_count}条")

        # 解析
        parser = DailyLogParser(custom_aliases)
        records = parser.parse(text)

        # 过滤
        records = filter_records(records, start_date, end_date, status)
        if not records:
            raise ValueError(f"{ERR_FILTER_NO_MATCH}: 过滤后无匹配记录")

        # 格式化输出
        if output_format == "markdown":
            return DailyLogFormatter.to_markdown(records)
        elif output_format == "json":
            return DailyLogFormatter.to_json(records)
        elif output_format == "plain":
            return DailyLogFormatter.to_plain(records)
        else:
            raise ValueError(f"{ERR_INVALID_FORMAT}: 不支持的输出格式 - {output_format}")

    except ValueError as e:
        raise
    except Exception as e:
        raise ValueError(f"{ERR_INTERNAL}: 处理过程中发生错误 - {str(e)}") from e


def run_selftest() -> int:
    """内置自检：使用硬编码样例数据验证核心逻辑，不依赖外部文件。"""
    print("=== 自检开始 ===")

    # 硬编码测试数据（不依赖任何外部文件）
    test_text = """
2026年1月5日
- 完成用户登录模块开发，负责人: 张三，状态: 完成，产出物: 登录接口文档
- 修复支付流程Bug，状态: 进行中，阻塞项: 等待第三方支付审核
- 编写测试用例，负责人: 李四，状态: 待开始

2026年1月6日
- 代码审查会议，产出物: 评审记录，备注: 需要跟进遗留问题
- 部署到测试环境，状态: 完成，置信度较高
"""

    # 测试1: 基础解析
    print("测试1: 解析基础数据...")
    parser = DailyLogParser()
    records = parser.parse(test_text)
    assert len(records) >= 4, f"解析记录数应>=4，实际: {len(records)}"
    assert all(r.get("date") for r in records), "所有记录必须有日期"
    assert all(r.get("task") for r in records), "所有记录必须有任务描述"
    print(f"  ✓ 成功解析 {len(records)} 条记录")

    # 测试2: 字段提取
    print("测试2: 字段提取验证...")
    first_record = records[0]
    assert first_record.get("owner") == "张三", f"负责人提取错误: {first_record.get('owner')}"
    assert first_record.get("status") == "done", f"状态提取错误: {first_record.get('status')}"
    assert first_record.get("output") is not None, "产出物提取失败"
    print(f"  ✓ 字段提取正确 (负责人={first_record.get('owner')}, 状态={first_record.get('status')})")

    # 测试3: 置信度计算（宽松阈值）
    print("测试3: 置信度计算...")
    confidences = [r.get("confidence", 0) for r in records]
    assert all(0 <= c <= 1 for c in confidences), f"置信度应在[0,1]区间: {confidences}"
    assert max(confidences) > 0.5, "至少一条记录置信度应高于0.5"
    print(f"  ✓ 置信度区间正确 (范围: {min(confidences):.2f} - {max(confidences):.2f})")

    # 测试4: 过滤功能
    print("测试4: 过滤功能...")
    filtered = filter_records(records, start_date="2026-01-06")
    assert len(filtered) >= 1, "日期过滤后至少应有1条记录"
    assert all(r["date"] >= "2026-01-06" for r in filtered), "过滤后日期应满足条件"
    print(f"  ✓ 日期过滤正确 (过滤后 {len(filtered)} 条)")

    # 测试5: 格式化输出
    print("测试5: 格式化输出...")
    md_output = DailyLogFormatter.to_markdown(records)
    assert "|" in md_output and "---" in md_output, "Markdown表格格式错误"
    json_output = DailyLogFormatter.to_json(records)
    json_data = json.loads(json_output)
    assert "records" in json_data, "JSON输出缺少records字段"
    plain_output = DailyLogFormatter.to_plain(records)
    assert "记录" in plain_output, "纯文本输出格式错误"
    print("  ✓ 三种格式输出正常")

    # 测试6: 批量处理入口
    print("测试6: 批量处理入口...")
    result = process_batch(test_text, output_format="markdown")
    assert "|" in result, "批量处理Markdown输出异常"
    print("  ✓ 批量处理正常")

    # 测试7: 错误处理
    print("测试7: 错误处理...")
    try:
        process_batch("", output_format="markdown")
        assert False, "空输入应抛出异常"
    except ValueError as e:
        assert str(e).startswith(ERR_EMPTY_RECORD), f"错误码应为{ERR_EMPTY_RECORD}: {e}"
    print(f"  ✓ 错误处理正确 ({ERR_EMPTY_RECORD})")

    print("=== 自检全部通过 ===")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="实习日志结构化整理工具",
        epilog="示例: python main.py -f input.txt -o json --start 2026-01-01"
    )
    parser.add_argument("input", nargs="?", help="输入文件路径（.txt/.md），省略时从标准输入读取")
    parser.add_argument("-f", "--file", help="输入文件路径（替代位置参数）")
    parser.add_argument("-o", "--output", choices=["markdown", "json", "plain"],
                        default="markdown", help="输出格式（默认: markdown）")
    parser.add_argument("--start", help="起始日期过滤（YYYY-MM-DD）")
    parser.add_argument("--end", help="结束日期过滤（YYYY-MM-DD）")
    parser.add_argument("--status", help="状态过滤（done/in_progress/pending/blocked/cancelled）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--alias", action="append", help="自定义字段别名，格式: 字段=别名1,别名2")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 解析自定义别名
    custom_aliases = None
    if args.alias:
        custom_aliases = {}
        for item in args.alias:
            try:
                field, aliases = item.split("=", 1)
                custom_aliases[field.strip()] = [a.strip() for a in aliases.split(",")]
            except ValueError:
                print(f"{ERR_ARGS}: 别名格式错误，应为 字段=别名1,别名2 - {item}", file=sys.stderr)
                return 1

    # 获取输入文本
    input_path = args.file or args.input
    try:
        if input_path:
            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            # 从标准输入读取
            print("请输入实习日志文本（Ctrl+D 结束输入）:")
            text = sys.stdin.read()
    except FileNotFoundError:
        print(f"{ERR_INVALID_INPUT}: 文件不存在 - {input_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{ERR_INVALID_INPUT}: 读取文件失败 - {str(e)}", file=sys.stderr)
        return 1

    # 处理
    try:
        result = process_batch(
            text,
            output_format=args.output,
            start_date=args.start,
            end_date=args.end,
            status=args.status,
            custom_aliases=custom_aliases,
        )
        print(result)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
