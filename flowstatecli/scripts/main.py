#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flowstatecli - 开发专注流 会话追踪 目标管理
=============================================
一个纯标准库实现的命令行效率工具，用于：
  * 解析原始工作日志为结构化会话记录
  * 从非结构化文本提取关键信息
  * 按目标聚合会话并计算进度
  * 对推断字段标注置信度

本脚本为 clean-room 重写实现，仅依据功能规格独立编写。
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 输入格式错误（无法解析的行或字段）
# E002: 时间格式错误（无法识别的时间戳）
# E003: 日期格式错误（无法识别的日期）
# E004: 数据缺失（必需字段缺失）
# E005: JSON 编码/解码错误
# E006: CSV 解析错误
# E007: 目标数据错误（目标字段缺失或无效）
# E008: 内部逻辑错误（不应发生的状态）
# E009: 参数错误（命令行参数不合法）
# E010: 未支持的输入类型


class FlowStateError(Exception):
    """技能基础异常，携带错误码与消息。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# 解析基础工具
# ---------------------------------------------------------------------------

def _parse_time(text: str) -> Optional[datetime]:
    """尝试解析多种常见时间格式，失败返回 None。"""
    text = text.strip()
    if not text:
        return None
    # 支持格式: HH:MM、HH:MM:SS、H:MM
    for fmt in ("%H:%M:%S", "%H:%M", "%H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    # 支持带 AM/PM 的格式（如 9:30 AM）
    for fmt in ("%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_date(text: str) -> Optional[datetime]:
    """尝试解析常见日期格式，失败返回 None。"""
    text = text.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_duration_minutes(text: str) -> Optional[int]:
    """从文本中提取时长（分钟），支持 '2小时'、'90分钟'、'1.5h' 等。"""
    text = text.strip()
    if not text:
        return None
    # 尝试直接数字（视为分钟）
    if text.isdigit():
        return int(text)
    # 小时+分钟组合，如 "1小时30分钟"
    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:小时|h|hr|hours?)", text, re.IGNORECASE)
    minute_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:分钟|min|mins|minutes?)", text, re.IGNORECASE)
    total = 0
    if hour_match:
        total += float(hour_match.group(1)) * 60
    if minute_match:
        total += float(minute_match.group(1))
    if total > 0:
        return int(round(total))
    # 单独的小时表示
    if hour_match:
        return int(round(float(hour_match.group(1)) * 60))
    return None


def _parse_priority(text: str) -> Tuple[str, float]:
    """从文本识别优先级，返回 (优先级, 置信度)。"""
    low = re.search(r"低|low|minor", text, re.IGNORECASE)
    mid = re.search(r"中|medium|normal", text, re.IGNORECASE)
    high = re.search(r"高|high|urgent|critical", text, re.IGNORECASE)
    if high:
        return ("high", 0.9)
    if mid:
        return ("medium", 0.8)
    if low:
        return ("low", 0.8)
    return ("unset", 0.5)


def _extract_task_id(text: str) -> Optional[str]:
    """提取 #数字 形式的任务编号。"""
    m = re.search(r"#(\d+)", text)
    return f"#{m.group(1)}" if m else None


def _extract_files(text: str) -> List[str]:
    """提取 .py/.js/.ts/.md 等常见文件引用。"""
    pattern = r"[\w\-./]+\.(?:py|js|ts|jsx|tsx|md|json|css|html|java|c|cpp|go|rs|rb)"
    return list(set(re.findall(pattern, text)))


def _classify_task_type(text: str) -> Tuple[str, float]:
    """简单任务类型分类，返回 (类型, 置信度)。"""
    if re.search(r"bug|fix|修复|缺陷", text, re.IGNORECASE):
        return ("bugfix", 0.85)
    if re.search(r"feature|功能|开发|实现", text, re.IGNORECASE):
        return ("feature", 0.8)
    if re.search(r"refactor|重构|优化", text, re.IGNORECASE):
        return ("refactor", 0.8)
    if re.search(r"doc|文档|注释", text, re.IGNORECASE):
        return ("documentation", 0.8)
    if re.search(r"test|测试", text, re.IGNORECASE):
        return ("testing", 0.8)
    return ("unset", 0.5)


# ---------------------------------------------------------------------------
# 核心能力1: 会话数据解析
# ---------------------------------------------------------------------------

def parse_session_line(line: str, line_number: int = 1) -> Dict[str, Any]:
    """
    将一行原始工作日志解析为结构化会话记录。
    支持格式示例：
      "2024-01-15 09:30-11:45 重构登录模块"
      "2024-01-15 09:30 - 11:45 重构登录模块"
    """
    line = line.strip()
    if not line:
        raise FlowStateError("E004", f"第 {line_number} 行为空，缺少数据")

    # 提取日期
    date_match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", line)
    if not date_match:
        raise FlowStateError("E003", f"第 {line_number} 行未找到有效日期")
    date_str = date_match.group(1)
    date_obj = _parse_date(date_str)
    if date_obj is None:
        raise FlowStateError("E003", f"第 {line_number} 行日期格式无法识别: {date_str}")

    # 提取时间区间
    time_range_match = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[-~至]\s*(\d{1,2}:\d{2}(?::\d{2})?)", line)
    if not time_range_match:
        raise FlowStateError("E002", f"第 {line_number} 行未找到有效时间区间")
    start_text, end_text = time_range_match.group(1), time_range_match.group(2)
    start_dt = _parse_time(start_text)
    end_dt = _parse_time(end_text)
    if start_dt is None or end_dt is None:
        raise FlowStateError("E002", f"第 {line_number} 行时间格式无法识别")

    # 计算时长（分钟）
    duration_min = (end_dt - start_dt).seconds // 60
    if duration_min < 0:
        duration_min += 24 * 60  # 跨天

    # 提取任务描述（时间区间之后的部分）
    task_part = line[time_range_match.end():].strip()
    if not task_part:
        raise FlowStateError("E004", f"第 {line_number} 行缺少任务描述")

    # 生成会话ID
    session_id = f"S{line_number:03d}"

    return {
        "session_id": session_id,
        "date": date_obj.strftime("%Y-%m-%d"),
        "start": start_dt.strftime("%H:%M"),
        "end": end_dt.strftime("%H:%M"),
        "duration_min": duration_min,
        "task": task_part,
    }


def parse_sessions(text: str) -> List[Dict[str, Any]]:
    """批量解析多行会话文本。"""
    sessions = []
    for idx, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        sessions.append(parse_session_line(line, idx))
    return sessions


# ---------------------------------------------------------------------------
# 核心能力2: 关键信息提取
# ---------------------------------------------------------------------------

def extract_key_info(text: str) -> Dict[str, Any]:
    """
    从非结构化文本中提取任务关键信息。
    示例输入: "下午修了#42 bug，花了2小时，涉及auth.py"
    示例输出: {"task_id":"#42","type":"bugfix","duration_h":2,"files":["auth.py"],"priority":"unset"}
    """
    text = text.strip()
    result: Dict[str, Any] = {}

    # 任务编号
    task_id = _extract_task_id(text)
    if task_id:
        result["task_id"] = task_id

    # 任务类型分类
    task_type, type_conf = _classify_task_type(text)
    result["type"] = task_type
    result["type_confidence"] = type_conf

    # 时长提取
    dur_min = _parse_duration_minutes(text)
    if dur_min is not None:
        result["duration_min"] = dur_min
        result["duration_h"] = round(dur_min / 60.0, 2)
    else:
        result["duration_h"] = None

    # 关联文件
    files = _extract_files(text)
    if files:
        result["files"] = files

    # 优先级
    priority, conf = _parse_priority(text)
    result["priority"] = priority
    result["priority_confidence"] = conf

    # 原始文本保留
    result["raw_text"] = text

    return result


# ---------------------------------------------------------------------------
# 核心能力3: 目标进度汇总
# ---------------------------------------------------------------------------

def summarize_goal(sessions: List[Dict[str, Any]], target_hours: float) -> Dict[str, Any]:
    """
    将会话记录按目标聚合，计算总投入与进度百分比。
    sessions: 结构化会话记录列表
    target_hours: 目标总时长（小时）
    """
    if target_hours <= 0:
        raise FlowStateError("E007", f"目标时长必须为正数，收到: {target_hours}")

    total_minutes = sum(s.get("duration_min", 0) for s in sessions)
    total_hours = total_minutes / 60.0
    progress_pct = min(100.0, round(total_hours / target_hours * 100, 1))

    # 按任务名聚合
    task_hours: Dict[str, float] = {}
    for s in sessions:
        task = s.get("task", "未命名任务")
        task_hours[task] = task_hours.get(task, 0.0) + s.get("duration_min", 0) / 60.0

    # 按日期聚合
    date_hours: Dict[str, float] = {}
    for s in sessions:
        d = s.get("date", "未知日期")
        date_hours[d] = date_hours.get(d, 0.0) + s.get("duration_min", 0) / 60.0

    return {
        "total_sessions": len(sessions),
        "total_hours": round(total_hours, 2),
        "target_hours": target_hours,
        "progress_pct": progress_pct,
        "by_task": {k: round(v, 2) for k, v in sorted(task_hours.items(), key=lambda x: -x[1])},
        "by_date": {k: round(v, 2) for k, v in sorted(date_hours.items())},
    }


# ---------------------------------------------------------------------------
# 批量处理 / 文件输入
# ---------------------------------------------------------------------------

def process_text_input(text: str) -> Dict[str, Any]:
    """处理纯文本输入，自动识别会话行并提取关键信息。"""
    sessions = parse_sessions(text)
    key_info = [extract_key_info(s["task"]) for s in sessions]
    return {
        "sessions": sessions,
        "key_info": key_info,
        "session_count": len(sessions),
    }


def process_json_input(data: str) -> Dict[str, Any]:
    """处理 JSON 输入，期望为会话记录数组。"""
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        raise FlowStateError("E005", f"JSON 解析失败: {e}")

    if not isinstance(parsed, list):
        raise FlowStateError("E010", "JSON 输入必须为会话记录数组")

    sessions = []
    for item in parsed:
        if not isinstance(item, dict):
            raise FlowStateError("E010", "JSON 数组元素必须为对象")
        # 兼容字段名差异
        session = {
            "session_id": item.get("session_id", item.get("id", "S?")),
            "date": item.get("date", item.get("日期", "")),
            "start": item.get("start", item.get("开始", "")),
            "end": item.get("end", item.get("结束", "")),
            "duration_min": item.get("duration_min", item.get("时长分钟", 0)),
            "task": item.get("task", item.get("任务", "")),
        }
        sessions.append(session)
    return {"sessions": sessions, "session_count": len(sessions)}


def process_csv_input(data: str) -> Dict[str, Any]:
    """处理 CSV 输入，期望包含会话字段。"""
    try:
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)
    except Exception as e:
        raise FlowStateError("E006", f"CSV 解析失败: {e}")

    sessions = []
    for row in rows:
        session = {
            "session_id": row.get("session_id", row.get("id", "S?")),
            "date": row.get("date", row.get("日期", "")),
            "start": row.get("start", row.get("开始", "")),
            "end": row.get("end", row.get("结束", "")),
            "duration_min": int(row.get("duration_min", row.get("时长分钟", 0) or 0)),
            "task": row.get("task", row.get("任务", "")),
        }
        sessions.append(session)
    return {"sessions": sessions, "session_count": len(sessions)}


def process_markdown_input(text: str) -> Dict[str, Any]:
    """处理 Markdown 输入，提取表格或代码块中的会话数据。"""
    # 提取表格行
    table_lines = []
    in_code_block = False
    for line in text.splitlines():
        if line.strip().startswith("
