#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toggl-tally 工时数据整理技能 - 独立实现脚本
版本: 1.0.2 (clean-room 重写)
仅依据功能规格实现，不复制任何既有代码。
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 错误码定义 (E001-E010)
ERROR_CODES = {
    "E001": "输入参数缺失或不合法",
    "E002": "文件不存在或无法读取",
    "E003": "文件格式不支持",
    "E004": "JSON 解析失败",
    "E005": "CSV 解析失败",
    "E006": "URL 格式不合法",
    "E007": "数据中缺少必要字段",
    "E008": "时间格式无法识别",
    "E009": "数据处理内部错误",
    "E010": "未知错误",
}


def _fail(code: str, message: str) -> None:
    """统一错误输出并退出"""
    print(f"错误 [{code}]: {message}", file=sys.stderr)
    sys.exit(1)


# ---------- 核心数据结构 ----------

class TimeRecord:
    """单条工时记录"""
    def __init__(self) -> None:
        self.project: str = ""
        self.task: str = ""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration_minutes: Optional[float] = None
        self.tags: List[str] = []
        self.confidence: str = "高"  # 高/中/低
        self.raw_source: str = ""    # 原始来源标识

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（用于 JSON 输出）"""
        result = {
            "项目": self.project,
            "任务": self.task,
            "开始时间": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "[需核实:时间]",
            "结束时间": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else "[需核实:时间]",
            "时长(分钟)": self.duration_minutes if self.duration_minutes is not None else "[需核实:时长]",
            "标签": self.tags,
            "置信度": self.confidence,
            "来源": self.raw_source,
        }
        return result

    def to_markdown_row(self) -> str:
        """转为 Markdown 表格行"""
        start = self.start_time.strftime("%Y-%m-%d %H:%M") if self.start_time else "[需核实]"
        end = self.end_time.strftime("%Y-%m-%d %H:%M") if self.end_time else "[需核实]"
        dur = f"{self.duration_minutes:.1f}" if self.duration_minutes is not None else "[需核实]"
        tags = ", ".join(self.tags) if self.tags else "-"
        return f"| {self.project} | {self.task} | {start} | {end} | {dur} | {tags} | {self.confidence} |"


# ---------- 时间解析工具 ----------

def _parse_time(text: str) -> Optional[datetime]:
    """尝试多种常见时间格式解析"""
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    # 常见格式列表
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%H:%M:%S",
        "%H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_duration(text: Any) -> Optional[float]:
    """解析时长（分钟），支持多种表示：数字、HH:MM、HH:MM:SS、ISO8601 等"""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        # 数字直接按分钟处理
        return float(text)
    if not isinstance(text, str):
        return None
    text = text.strip().lower()
    if not text:
        return None

    # 纯数字（按分钟处理）
    if text.isdigit():
        return float(text)

    # ISO8601 格式 PT1H30M
    iso_match = re.match(r"^pt(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", text)
    if iso_match:
        hours = int(iso_match.group(1) or 0)
        mins = int(iso_match.group(2) or 0)
        secs = int(iso_match.group(3) or 0)
        return float(hours * 60 + mins + secs / 60.0)

    # HH:MM 或 HH:MM:SS
    parts = text.split(":")
    if len(parts) in (2, 3):
        try:
            nums = [int(p) for p in parts]
            if len(nums) == 2:
                return float(nums[0] * 60 + nums[1])
            return float(nums[0] * 3600 + nums[1] * 60 + nums[2]) / 60.0
        except ValueError:
            return None

    # 带单位文本，如 "1.5h" "30m" "2小时"
    unit_match = re.match(r"^([\d.]+)\s*(h|hr|hour|hours|m|min|mins|minute|minutes|s|sec|secs)?$", text)
    if unit_match:
        val = float(unit_match.group(1))
        unit = unit_match.group(2) or "m"
        if unit.startswith("h"):
            return val * 60.0
        if unit.startswith("s"):
            return val / 60.0
        return val  # 默认分钟

    return None


def _parse_duration_seconds(text: Any) -> Optional[float]:
    """解析时长（秒），用于需要按秒处理的场景"""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    if not isinstance(text, str):
        return None
    text = text.strip().lower()
    if not text:
        return None

    # 纯数字（秒）
    if text.isdigit():
        return float(text)

    # ISO8601 格式 PT1H30M
    iso_match = re.match(r"^pt(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", text)
    if iso_match:
        hours = int(iso_match.group(1) or 0)
        mins = int(iso_match.group(2) or 0)
        secs = int(iso_match.group(3) or 0)
        return float(hours * 3600 + mins * 60 + secs)

    # HH:MM 或 HH:MM:SS
    parts = text.split(":")
    if len(parts) in (2, 3):
        try:
            nums = [int(p) for p in parts]
            if len(nums) == 2:
                return float(nums[0] * 3600 + nums[1] * 60)
            return float(nums[0] * 3600 + nums[1] * 60 + nums[2])
        except ValueError:
            return None

    # 带单位文本，如 "1.5h" "30m" "2小时"
    unit_match = re.match(r"^([\d.]+)\s*(h|hr|hour|hours|m|min|mins|minute|minutes|s|sec|secs)?$", text)
    if unit_match:
        val = float(unit_match.group(1))
        unit = unit_match.group(2) or "s"
        if unit.startswith("h"):
            return val * 3600.0
        if unit.startswith("m"):
            return val * 60.0
        return val  # 默认秒

    return None


def _guess_confidence(record: TimeRecord) -> str:
    """根据字段完整度推测置信度"""
    missing = 0
    if not record.project:
        missing += 1
    if not record.task:
        missing += 1
    if record.start_time is None and record.end_time is None and record.duration_minutes is None:
        missing += 2
    if missing == 0:
        return "高"
    if missing <= 1:
        return "中"
    return "低"


# ---------- 数据解析器 ----------

class DataParser:
    """从不同来源解析工时数据"""

    @staticmethod
    def parse_text(text: str) -> List[TimeRecord]:
        """从纯文本解析（每行一条记录，支持简单分隔）"""
        records: List[TimeRecord] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            rec = DataParser._parse_line(line)
            if rec:
                records.append(rec)
        return records

    @staticmethod
    def _parse_line(line: str) -> Optional[TimeRecord]:
        """解析单行文本，尝试多种分隔符"""
        # 尝试不同分隔符
        delimiters = ["\t", ",", "|", ";"]
        best_parts: Optional[List[str]] = None
        best_delim = None
        for d in delimiters:
            parts = line.split(d)
            if len(parts) >= 2:
                best_parts = [p.strip() for p in parts]
                best_delim = d
                break

        if not best_parts:
            return None

        rec = TimeRecord()
        rec.raw_source = "text"

        # 按位置尝试提取字段
        # 常见格式: 项目 | 任务 | 开始 | 结束 | 时长 | 标签
        if len(best_parts) >= 2:
            rec.project = best_parts[0]
        if len(best_parts) >= 2:
            rec.task = best_parts[1]
        if len(best_parts) >= 3:
            rec.start_time = _parse_time(best_parts[2])
        if len(best_parts) >= 4:
            rec.end_time = _parse_time(best_parts[3])
        if len(best_parts) >= 5:
            rec.duration_minutes = _parse_duration(best_parts[4])
        if len(best_parts) >= 6:
            rec.tags = [t.strip() for t in best_parts[5].split("+") if t.strip()]

        # 若没有时长但有起止时间，计算时长
        if rec.duration_minutes is None and rec.start_time and rec.end_time:
            delta = rec.end_time - rec.start_time
            rec.duration_minutes = delta.total_seconds() / 60.0

        # 置信度
        rec.confidence = _guess_confidence(rec)
        return rec

    @staticmethod
    def parse_json(data: Any) -> List[TimeRecord]:
        """从 JSON 数据解析"""
        records: List[TimeRecord] = []
        if isinstance(data, dict):
            # 可能是单条记录或包含 records 字段
            if any(k in data for k in ["project", "项目", "task", "任务"]):
                rec = DataParser._parse_json_record(data)
                if rec:
                    records.append(rec)
            elif "records" in data and isinstance(data["records"], list):
                for item in data["records"]:
                    rec = DataParser._parse_json_record(item)
                    if rec:
                        records.append(rec)
        elif isinstance(data, list):
            for item in data:
                rec = DataParser._parse_json_record(item)
                if rec:
                    records.append(rec)
        return records

    @staticmethod
    def _parse_json_record(item: Any) -> Optional[TimeRecord]:
        """从单个 JSON 对象解析"""
        if not isinstance(item, dict):
            return None
        rec = TimeRecord()
        rec.raw_source = "json"
        rec.project = str(item.get("project", item.get("项目", item.get("project_name", "")))).strip()
        rec.task = str(item.get("task", item.get("任务", item.get("description", "")))).strip()
        rec.start_time = _parse_time(str(item.get("start", item.get("start_time", item.get("开始时间", "")))))
        rec.end_time = _parse_time(str(item.get("end", item.get("end_time", item.get("结束时间", "")))))
        
        # 处理时长字段 - JSON中duration通常按分钟，如果是纯数字直接按分钟
        duration_val = item.get("duration", item.get("duration_minutes", item.get("时长", "")))
        if isinstance(duration_val, (int, float)):
            rec.duration_minutes = float(duration_val)
        elif isinstance(duration_val, str):
            # 如果是纯数字字符串，按分钟处理
            if duration_val.strip().isdigit():
                rec.duration_minutes = float(duration_val)
            else:
                rec.duration_minutes = _parse_duration(duration_val)
        
        tags = item.get("tags", item.get("标签", []))
        if isinstance(tags, list):
            rec.tags = [str(t) for t in tags]
        elif isinstance(tags, str):
            rec.tags = [t.strip() for t in tags.split(",") if t.strip()]

        if rec.duration_minutes is None and rec.start_time and rec.end_time:
            delta = rec.end_time - rec.start_time
            rec.duration_minutes = delta.total_seconds() / 60.0

        rec.confidence = _guess_confidence(rec)
        return rec

    @staticmethod
    def parse_csv(file_path: str) -> List[TimeRecord]:
        """从 CSV 文件解析"""
        records: List[TimeRecord] = []
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rec = TimeRecord()
                    rec.raw_source = f"csv:{Path(file_path).name}"
                    rec.project = row.get("project", row.get("项目", row.get("Project", ""))).strip()
                    rec.task = row.get("task", row.get("任务", row.get("Task", row.get("Description", "")))).strip()
                    rec.start_time = _parse_time(row.get("start", row.get("start_time", row.get("开始时间", ""))))
                    rec.end_time = _parse_time(row.get("end", row.get("end_time", row.get("结束时间", ""))))
                    rec.duration_minutes = _parse_duration(row.get("duration", row.get("duration_minutes", row.get("时长", ""))))
                    tags_raw = row.get("tags", row.get("标签", ""))
                    rec.tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

                    if rec.duration_minutes is None and rec.start_time and rec.end_time:
                        delta = rec.end_time - rec.start_time
                        rec.duration_minutes = delta.total_seconds() / 60.0

                    rec.confidence = _guess_confidence(rec)
                    if rec.project or rec.task:
                        records.append(rec)
        except FileNotFoundError:
            _fail("E002", f"文件不存在: {file_path}")
        except PermissionError:
            _fail("E002", f"文件无读取权限: {file_path}")
        except Exception as e:
            _fail("E005", f"CSV 解析失败: {e}")
        return records

    @staticmethod
    def parse_txt(file_path: str) -> List[TimeRecord]:
        """从 TXT 文件解析"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return DataParser.parse_text(content)
        except FileNotFoundError:
            _fail("E002", f"文件不存在: {file_path}")
        except PermissionError:
            _fail("E002", f"文件无读取权限: {file_path}")
        except Exception as e:
            _fail("E009", f"TXT 解析失败: {e}")
        return []

    @staticmethod
    def parse_json_file(file_path: str) -> List[TimeRecord]:
        """从 JSON 文件解析"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return DataParser.parse_json(data)
        except FileNotFoundError:
            _fail("E002", f"文件不存在: {file_path}")
        except PermissionError:
            _fail("E002", f"文件无读取权限: {file_path}")
        except json.JSONDecodeError as e:
            _fail("E004", f"JSON 解析失败: {e}")
        except Exception as e:
            _fail("E009", f"JSON 文件处理失败: {e}")
        return []


# ---------- URL 解析（仅识别格式，不访问网络） ----------

def parse_url(url: str) -> List[TimeRecord]:
    """URL 处理：仅校验格式，不发起网络请求"""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        _fail("E006", f"URL 格式不合法: {url}")

    # 根据扩展名尝试判断类型，但实际不下载
    path = parsed.path.lower()
    if path.endswith(".csv"):
        _fail("E009", f"URL 指向 CSV 文件，但本技能不发起网络请求，请先下载文件: {url}")
    elif path.endswith(".json"):
        _fail("E009", f"URL 指向 JSON 文件，但本技能不发起网络请求，请先下载文件: {url}")
    else:
        _fail("E009", f"URL 指向未知类型，本技能不发起网络请求，请提供本地文件或文本: {url}")
    return []


# ---------- 数据处理 ----------

def process_records(records: List[TimeRecord]) -> List[TimeRecord]:
    """批量处理：去重 + 排序"""
    # 去重（基于项目+任务+开始时间）
    seen = set()
    unique_records: List[TimeRecord] = []
    for rec in records:
        key = (
            rec.project.lower(),
            rec.task.lower(),
            rec.start_time.isoformat() if rec.start_time else "no_start",
        )
        if key not in seen:
            seen.add(key)
            unique_records.append(rec)

    # 排序：按开始时间，无时间的排最后
    def sort_key(rec: TimeRecord) -> Tuple[int, str]:
        if rec.start_time:
            return (0, rec.start_time.isoformat())
        return (1, "")

    unique_records.sort(key=sort_key)
    return unique_records


def format_output(records: List[TimeRecord], output_format: str = "markdown") -> str:
    """格式化输出"""
    if output_format == "json":
        return json.dumps([r.to_dict() for r in records], ensure_ascii=False, indent=2)

    # 默认 Markdown
    lines = [
        "| 项目 | 任务 | 开始时间 | 结束时间 | 时长(分钟) | 标签 | 置信度 |",
        "|------|------|----------|----------|------------|------|--------|",
    ]
    for rec in records:
        lines.append(rec.to_markdown_row())
    return "\n".join(lines)


# ---------- 主入口 ----------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="toggl-tally 工时数据整理工具 - 将工时数据转为结构化结果",
        epilog="示例: python main.py --file data.csv --format json",
    )
    parser.add_argument("--file", "-f", help="输入文件路径 (CSV/JSON/TXT)")
    parser.add_argument("--text", "-t", help="直接输入文本内容")
    parser.add_argument("--url", "-u", help="URL (仅校验格式，不访问网络)")
    parser.add_argument("--format", "-o", choices=["markdown", "json"], default="markdown", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    # 收集输入
    records: List[TimeRecord] = []

    if args.file:
        path = Path(args.file)
        if not path.exists():
            _fail("E002", f"文件不存在: {args.file}")
        suffix = path.suffix.lower()
        if suffix == ".csv":
            records.extend(DataParser.parse_csv(args.file))
        elif suffix == ".json":
            records.extend(DataParser.parse_json_file(args.file))
        elif suffix == ".txt":
            records.extend(DataParser.parse_txt(args.file))
        else:
            _fail("E003", f"不支持的文件格式: {suffix} (支持 CSV/JSON/TXT)")
    elif args.text:
        records.extend(DataParser.parse_text(args.text))
    elif args.url:
        records.extend(parse_url(args.url))
    else:
        _fail("E001", "请提供 --file 或 --text 或 --url 参数")

    if not records:
        _fail("E007", "未能从输入中解析出任何工时记录")

    # 处理
    processed = process_records(records)

    # 输出
    output = format_output(processed, args.format)
    print(output)


# ---------- 自检 ----------

def run_selftest() -> None:
    """内置自检：使用硬编码样例数据验证核心逻辑，不依赖外部环境"""
    print("=== toggl-tally 自检开始 ===")
    passed = 0
    total = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name}")

    # 测试 1: 文本解析
    print("\n[1] 文本解析测试")
    sample_text = """项目A, 开发登录功能, 2024-01-15 09:00, 2024-01-15 11:30, 150, 前端+后端
项目B, 修复bug, 2024-01-15 14:00, 2024-01-15 15:00, 60, 紧急
项目A, 代码审查, 2024-01-16 10:00, 2024-01-16 11:00, 60, 团队"""
    text_records = DataParser.parse_text(sample_text)
    check("文本解析出3条记录", len(text_records) == 3)
    if text_records:
        check("第一条项目名正确", text_records[0].project == "项目A")
        check("第一条时长正确", text_records[0].duration_minutes == 150.0)
        check("第一条置信度为高", text_records[0].confidence == "高")
        check("第一条标签解析正确", len(text_records[0].tags) == 2)

    # 测试 2: 时长解析
    print("\n[2] 时长解析测试")
    check("ISO8601 解析", abs(_parse_duration("PT1H30M") - 90.0) < 0.001)
    check("HH:MM 解析", abs(_parse_duration("02:15") - 135.0) < 0.001)
    check("纯数字(分钟)解析", abs(_parse_duration("3600") - 3600.0) < 0.001)
    check("带单位解析", abs(_parse_duration("1.5h") - 90.0) < 0.001)
    check("无效时长返回None", _parse_duration("abc") is None)

    # 测试 3: 时间解析
    print("\n[3] 时间解析测试")
    check("标准时间格式", _parse_time("2024-01-15 09:30") is not None)
    check("ISO格式", _parse_time("2024-01-15T09:30:00") is not None)
    check("斜杠格式", _parse_time("2024/01/15 09:30") is not None)
    check("无效时间返回None", _parse_time("not-a-time") is None)

    # 测试 4: JSON 解析
    print("\n[4] JSON 解析测试")
    sample_json = [
        {"project": "项目X", "task": "需求分析", "start": "2024-02-01 09:00", "end": "2024-02-01 10:30", "tags": ["分析"]},
        {"项目": "项目Y", "任务": "会议", "duration": "45", "标签": ["会议"]},
    ]
    json_records = DataParser.parse_json(sample_json)
    check("JSON解析出2条记录", len(json_records) == 2)
    if len(json_records) >= 2:
        check("JSON第二条时长解析", json_records[1].duration_minutes == 45.0)
        check("JSON第二条置信度为中", json_records[1].confidence == "中")

    # 测试 5: 去重与排序
    print("\n[5] 去重与排序测试")
    dup_records = [
        TimeRecord.__new__(TimeRecord) for _ in range(3)
    ]
    # 构造三条记录（两条重复）
    r1 = TimeRecord()
    r1.project, r1.task = "P1", "T1"
    r1.start_time = datetime(2024, 1, 1, 9, 0)
    r1.end_time = datetime(2024, 1, 1, 10, 0)
    r1.duration_minutes = 60.0
    r1.confidence = "高"

    r2 = TimeRecord()
    r2.project, r2.task = "P1", "T1"
    r2.start_time = datetime(2024, 1, 1, 9, 0)
    r2.end_time = datetime(2024, 1, 1, 10, 0)
    r2.duration_minutes = 60.0
    r2.confidence = "高"

    r3 = TimeRecord()
    r3.project, r3.task = "P2", "T2"
    r3.start_time = datetime(2024, 1, 2, 9, 0)
    r3.end_time = datetime(2024, 1, 2, 10, 0)
    r3.duration_minutes = 60.0
    r3.confidence = "高"

    processed = process_records([r1, r2, r3])
    check("去重后保留2条", len(processed) == 2)
    check("排序后第一条是P1", processed[0].project == "P1")

    # 测试 6: 输出格式
    print("\n[6] 输出格式测试")
    md_output = format_output([r1], "markdown")
    check("Markdown输出包含表头", "| 项目 |" in md_output)
    check("Markdown输出包含数据", "P1" in md_output)

    json_output = format_output([r1], "json")
    json_parsed = json.loads(json_output)
    check("JSON输出可解析", isinstance(json_parsed, list))
    check("JSON输出包含项目字段", json_parsed[0]["项目"] == "P1")

    # 测试 7: 缺失时长处理
    print("\n[7] 缺失时长处理测试")
    r4 = TimeRecord()
    r4.project, r4.task = "P3", "T3"
    r4.confidence = "低"
    r4_dict = r4.to_dict()
    check("缺失时长标记", r4_dict["时长(分钟)"] == "[需核实:时长]")
    check("缺失时间标记", r4_dict["开始时间"] == "[需核实:时间]")

    # 测试 8: CSV 解析（使用临时文件）
    print("\n[8] CSV 解析测试")
    import tempfile
    import os
    fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("project,task,start,end,duration,tags\n")
            f.write("项目C,测试任务,2024-03-01 09:00,2024-03-01 10:00,,测试\n")
        csv_records = DataParser.parse_csv(tmp_path)
        check("CSV解析出1条记录", len(csv_records) == 1)
        if csv_records:
            check("CSV项目名正确", csv_records[0].project == "项目C")
            check("CSV时长自动计算", csv_records[0].duration_minutes == 60.0)
    finally:
        os.unlink(tmp_path)

    # 汇总
    print(f"\n=== 自检完成: {passed}/{total} 通过 ===")
    if passed == total:
        print("全部通过 ✓")
    else:
        print(f"有 {total - passed} 项未通过 ✗")
        sys.exit(1)


if __name__ == "__main__":
    main()
