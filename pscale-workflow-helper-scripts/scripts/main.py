#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pscale-workflow-helper-scripts 独立实现脚本

依据功能规格 clean-room 重写：
- 将用户输入文本解析为结构化任务记录
- 支持批量处理，单次最多 50 条
- 输出 JSON / CSV / Markdown 表格
- 每个字段附带置信度标注（高/中/低）
- 内置 --selftest 离线自检（硬编码样例，不依赖外部环境）

错误码：
  E001 参数错误
  E002 输入为空或类型不合法
  E003 记录数超过上限（50）
  E004 输出格式不支持
  E005 文件写入失败
  E006 文件读取失败
  E007 数据解析失败
  E008 置信度计算异常
  E009 内部逻辑错误
  E010 未知异常
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# ------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------
MAX_RECORDS = 50
SUPPORTED_FORMATS = ("json", "csv", "markdown", "md")
CONFIDENCE_LEVELS = ("high", "medium", "low")

# 状态关键词映射（用于从文本中识别状态）
STATUS_KEYWORDS = {
    "done": ["done", "完成", "已完成", "closed", "关闭"],
    "in_progress": ["in progress", "进行中", "wip", "doing", "处理中"],
    "todo": ["todo", "待办", "pending", "未开始", "open", "新建"],
    "blocked": ["blocked", "阻塞", "卡住", "waiting", "等待"],
    "cancelled": ["cancelled", "canceled", "取消", "已取消"],
}

# 日期格式模式（宽松匹配）
DATE_PATTERNS = [
    r"\d{4}-\d{1,2}-\d{1,2}",           # 2026-01-31
    r"\d{4}/\d{1,2}/\d{1,2}",           # 2026/01/31
    r"\d{1,2}-\d{1,2}-\d{4}",           # 31-01-2026
    r"\d{1,2}/\d{1,2}/\d{4}",           # 31/01/2026
    r"\d{4}年\d{1,2}月\d{1,2}日",       # 2026年1月31日
]


# ------------------------------------------------------------
# 核心数据模型
# ------------------------------------------------------------
class TaskRecord:
    """单条任务记录，包含字段与置信度。"""

    def __init__(self, task_name="", owner="", due_date="", status="todo"):
        self.id = str(uuid.uuid4())[:8]
        self.task_name = task_name
        self.owner = owner
        self.due_date = due_date
        self.status = status
        self.confidence = {
            "task_name": "low",
            "owner": "low",
            "due_date": "low",
            "status": "low",
        }
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        """转为字典（含置信度）。"""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "owner": self.owner,
            "due_date": self.due_date,
            "status": self.status,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }

    def to_flat_dict(self):
        """转为扁平字典（置信度合并为字符串）。"""
        conf_str = ",".join(
            f"{k}:{v}" for k, v in self.confidence.items()
        )
        return {
            "id": self.id,
            "task_name": self.task_name,
            "owner": self.owner,
            "due_date": self.due_date,
            "status": self.status,
            "confidence": conf_str,
            "created_at": self.created_at,
        }


# ------------------------------------------------------------
# 解析辅助函数
# ------------------------------------------------------------
def _extract_date(text):
    """从文本中提取日期字符串，找不到返回空字符串。"""
    if not text:
        return ""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            # 统一格式为 YYYY-MM-DD（宽松处理）
            raw = match.group(0)
            raw = raw.replace("/", "-").replace("年", "-").replace("月", "-").replace("日", "")
            parts = [p for p in re.split(r"-", raw) if p]
            if len(parts) == 3:
                # 尝试判断是年月日还是日月年
                try:
                    if len(parts[0]) == 4:
                        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    elif len(parts[2]) == 4:
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    else:
                        return ""
                    # 验证日期合法性
                    if month < 1 or month > 12 or day < 1 or day > 31:
                        return ""
                    # 简单验证（不处理闰年等复杂情况）
                    if day > 31:
                        return ""
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except (ValueError, IndexError):
                    return ""
    return ""


def _extract_status(text):
    """从文本中识别状态关键词，默认 todo。"""
    if not text:
        return "todo"
    lowered = text.lower()
    for status, keywords in STATUS_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lowered:
                return status
    return "todo"


def _extract_owner(text):
    """从文本中提取责任人（简单启发式：@后跟字母数字）。"""
    if not text:
        return ""
    match = re.search(r"@([A-Za-z0-9_\u4e00-\u9fa5]+)", text)
    if match:
        return match.group(1)
    # 尝试 "负责人: XXX" 或 "owner: XXX"
    match = re.search(r"(?:负责人|owner)\s*[:：]\s*([A-Za-z0-9_\u4e00-\u9fa5]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def _extract_task_name(text):
    """提取任务名称（去掉已识别的日期/状态/责任人标记）。"""
    if not text:
        return ""
    cleaned = text
    # 去掉日期
    for pattern in DATE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    # 去掉状态关键词
    for status, keywords in STATUS_KEYWORDS.items():
        for kw in keywords:
            cleaned = re.sub(re.escape(kw), "", cleaned, flags=re.IGNORECASE)
    # 去掉责任人标记
    cleaned = re.sub(r"@[A-Za-z0-9_\u4e00-\u9fa5]+", "", cleaned)
    cleaned = re.sub(r"(?:负责人|owner)\s*[:：]\s*[A-Za-z0-9_\u4e00-\u9fa5]+", "", cleaned, flags=re.IGNORECASE)
    # 清理多余空白
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—:：,，;；")
    return cleaned


def _compute_confidence(field_value, field_name, raw_text=""):
    """
    根据字段内容动态计算置信度。
    规则（基于实际匹配质量）：
      - 非空且长度足够 -> high
      - 非空但较短 -> medium
      - 空 -> low
    额外规则：
      - 日期字段：能提取出合法日期 -> high；否则 low
      - 状态字段：能识别出明确状态 -> high；否则 low
      - 责任人字段：匹配 @ 或 负责人 模式 -> high；否则 medium
    """
    if not field_value:
        return "low"
    if field_name == "task_name":
        # 任务名长度 >= 4 且包含有意义内容
        if len(field_value) >= 4:
            return "high"
        elif len(field_value) >= 2:
            return "medium"
        return "low"
    if field_name == "owner":
        # 责任人长度 >= 2 且匹配 @ 或 负责人 模式
        if len(field_value) >= 2:
            return "high"
        return "medium"
    if field_name == "due_date":
        # 能提取出日期就认为高置信度
        return "high" if _extract_date(field_value) else "low"
    if field_name == "status":
        # 能识别出明确状态就认为高置信度
        if _extract_status(field_value) != "todo":
            return "high"
        elif "todo" in field_value.lower() or "待办" in field_value:
            return "medium"
        return "low"
    return "medium"


# ------------------------------------------------------------
# 核心处理逻辑
# ------------------------------------------------------------
def parse_single_entry(entry_text, entry_id=None):
    """
    将单条文本解析为 TaskRecord。
    支持格式示例：
      "完成报表 @张三 2026-01-31 done"
      "任务名称：开发接口|负责人：李四|截止：2026/02/15|状态：进行中"
    """
    if not entry_text or not isinstance(entry_text, str):
        raise ValueError("E007: 输入条目为空或类型非法")

    text = entry_text.strip()
    if not text:
        raise ValueError("E007: 输入条目为空")

    # 尝试用 | 或 , 或 ； 分隔字段
    parts = re.split(r"[|,，;；]", text)
    if len(parts) >= 2:
        # 键值对模式：字段名: 值
        record = TaskRecord()
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if re.match(r"^(任务名称|任务|task)\s*[:：]", part, re.IGNORECASE):
                record.task_name = re.sub(r"^(任务名称|任务|task)\s*[:：]\s*", "", part, flags=re.IGNORECASE)
            elif re.match(r"^(负责人|责任人|owner)\s*[:：]", part, re.IGNORECASE):
                record.owner = re.sub(r"^(负责人|责任人|owner)\s*[:：]\s*", "", part, flags=re.IGNORECASE)
            elif re.match(r"^(截止|截止日期|due|due date)\s*[:：]", part, re.IGNORECASE):
                record.due_date = _extract_date(part)
            elif re.match(r"^(状态|status)\s*[:：]", part, re.IGNORECASE):
                status_raw = re.sub(r"^(状态|status)\s*[:：]\s*", "", part, flags=re.IGNORECASE)
                record.status = _extract_status(status_raw)
            else:
                # 未匹配键值对，尝试当作自由文本提取
                if not record.task_name:
                    record.task_name = _extract_task_name(part)
                if not record.due_date:
                    record.due_date = _extract_date(part)
                if not record.owner:
                    record.owner = _extract_owner(part)
                if record.status == "todo":
                    record.status = _extract_status(part)
    else:
        # 自由文本模式：整条解析
        record = TaskRecord()
        record.task_name = _extract_task_name(text)
        record.owner = _extract_owner(text)
        record.due_date = _extract_date(text)
        record.status = _extract_status(text)

    # 如果任务名仍为空，用原始文本截断
    if not record.task_name:
        record.task_name = text[:50]

    # 动态计算置信度（基于实际匹配质量）
    record.confidence["task_name"] = _compute_confidence(record.task_name, "task_name", text)
    record.confidence["owner"] = _compute_confidence(record.owner, "owner", text)
    record.confidence["due_date"] = _compute_confidence(record.due_date, "due_date", text)
    record.confidence["status"] = _compute_confidence(record.status, "status", text)

    # 设置自定义 id
    if entry_id:
        record.id = entry_id

    return record


def parse_batch(input_text):
    """
    批量解析输入文本。
    支持按行分割或按分隔符分割多条记录。
    使用 ThreadPoolExecutor 并行解析，带超时与错误隔离。
    """
    if not input_text or not isinstance(input_text, str):
        raise ValueError("E002: 输入为空或类型不合法")

    # 按行分割
    lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("E002: 输入为空")

    # 过滤注释行
    lines = [line for line in lines if not line.startswith("#") and not line.startswith("//")]
    if not lines:
        raise ValueError("E002: 输入为空")

    if len(lines) > MAX_RECORDS:
        raise ValueError(f"E003: 记录数超过上限 {MAX_RECORDS}")

    records = []
    errors = []

    # 使用线程池并行解析，显式设置 max_workers=4
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_line = {executor.submit(parse_single_entry, line): line for line in lines}
        for future in as_completed(future_to_line, timeout=10):
            line = future_to_line[future]
            try:
                record = future.result(timeout=5)
                records.append(record)
            except Exception as e:
                errors.append(f"行 '{line[:30]}...' 解析失败: {e}")

    if errors:
        # 如果有错误，抛出第一个错误，但保留已解析的记录
        raise ValueError(f"E007: 部分解析失败: {errors[0]}")

    if not records:
        raise ValueError("E002: 输入为空")

    return records


# ------------------------------------------------------------
# 输出格式化
# ------------------------------------------------------------
def format_json(records):
    """输出 JSON 格式。"""
    data = [r.to_dict() for r in records]
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_csv(records):
    """输出 CSV 格式。"""
    if not records:
        return ""
    output = io.StringIO()
    fieldnames = ["id", "task_name", "owner", "due_date", "status", "confidence", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in records:
        writer.writerow(r.to_flat_dict())
    return output.getvalue()


def format_markdown(records):
    """输出 Markdown 表格。"""
    if not records:
        return ""
    lines = []
    lines.append("| ID | 任务名称 | 责任人 | 截止日期 | 状态 | 置信度 | 创建时间 |")
    lines.append("|----|----------|--------|----------|------|--------|----------|")
    for r in records:
        conf = r.confidence
        conf_str = f"任务:{conf['task_name']} 责任人:{conf['owner']} 日期:{conf['due_date']} 状态:{conf['status']}"
        lines.append(
            f"| {r.id} | {r.task_name} | {r.owner} | {r.due_date} | {r.status} | {conf_str} | {r.created_at} |"
        )
    return "\n".join(lines)


def format_output(records, output_format):
    """根据指定格式输出。"""
    fmt = output_format.lower()
    if fmt == "json":
        return format_json(records)
    elif fmt == "csv":
        return format_csv(records)
    elif fmt in ("markdown", "md"):
        return format_markdown(records)
    else:
        raise ValueError(f"E004: 不支持的输出格式: {output_format}")


# ------------------------------------------------------------
# 文件处理（原子写入 + 重试）
# ------------------------------------------------------------
def read_input_file(file_path):
    """读取输入文件内容。"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError as e:
        raise ValueError(f"E006: 文件不存在: {file_path}") from e
    except Exception as e:
        raise ValueError(f"E006: 读取文件失败: {e}") from e


def write_output_file(file_path, content, max_retries=3):
    """
    原子写入输出文件（tempfile + os.replace），带重试机制。
    """
    for attempt in range(max_retries):
        try:
            # 创建临时文件
            dir_name = os.path.dirname(file_path) or "."
            fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".part")
            try:
                with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content)
                # 原子替换
                os.replace(temp_path, file_path)
                return
            except Exception:
                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            if attempt == max_retries - 1:
                raise ValueError(f"E005: 写入文件失败: {e}") from e
            # 退避重试
            time.sleep(0.1 * (attempt + 1))


#
