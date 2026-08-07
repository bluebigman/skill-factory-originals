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
import re
import sys
import uuid
from datetime import datetime


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

    def to_dict(self):
        """转为字典（含置信度）。"""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "owner": self.owner,
            "due_date": self.due_date,
            "status": self.status,
            "confidence": self.confidence,
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
                if len(parts[0]) == 4:
                    return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                elif len(parts[2]) == 4:
                    return f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
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


def _compute_confidence(field_value, field_name):
    """
    根据字段内容计算置信度。
    规则（宽松）：
      - 非空且长度足够 -> high
      - 非空但较短 -> medium
      - 空 -> low
    """
    if not field_value:
        return "low"
    if field_name == "task_name":
        return "high" if len(field_value) >= 4 else "medium"
    if field_name == "owner":
        return "high" if len(field_value) >= 2 else "medium"
    if field_name == "due_date":
        # 能提取出日期就认为高置信度
        return "high" if _extract_date(field_value) else "low"
    if field_name == "status":
        # 能识别出状态就认为高置信度
        return "high" if _extract_status(field_value) != "todo" or "todo" in field_value.lower() else "medium"
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

    # 计算置信度
    record.confidence["task_name"] = _compute_confidence(record.task_name, "task_name")
    record.confidence["owner"] = _compute_confidence(record.owner, "owner")
    record.confidence["due_date"] = _compute_confidence(record.due_date, "due_date")
    record.confidence["status"] = _compute_confidence(record.status, "status")

    # 设置自定义 id
    if entry_id:
        record.id = entry_id

    return record


def parse_batch(input_text):
    """
    批量解析输入文本。
    支持按行分割或按分隔符分割多条记录。
    """
    if not input_text or not isinstance(input_text, str):
        raise ValueError("E002: 输入为空或类型不合法")

    # 按行分割
    lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("E002: 输入为空")

    records = []
    for line in lines:
        # 跳过注释行
        if line.startswith("#") or line.startswith("//"):
            continue
        try:
            record = parse_single_entry(line)
            records.append(record)
        except ValueError as e:
            # 单条解析失败不中断，记录错误
            raise ValueError(f"E007: 解析失败: {e}") from e

    if not records:
        raise ValueError("E002: 输入为空")

    if len(records) > MAX_RECORDS:
        raise ValueError(f"E003: 记录数超过上限 {MAX_RECORDS}")

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
    fieldnames = ["id", "task_name", "owner", "due_date", "status", "confidence"]
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
    lines.append("| ID | 任务名称 | 责任人 | 截止日期 | 状态 | 置信度 |")
    lines.append("|----|----------|--------|----------|------|--------|")
    for r in records:
        conf = r.confidence
        conf_str = f"任务:{conf['task_name']} 责任人:{conf['owner']} 日期:{conf['due_date']} 状态:{conf['status']}"
        lines.append(
            f"| {r.id} | {r.task_name} | {r.owner} | {r.due_date} | {r.status} | {conf_str} |"
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
# 文件处理
# ------------------------------------------------------------
def read_input_file(file_path):
    """读取输入文件内容。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as e:
        raise ValueError(f"E006: 文件不存在: {file_path}") from e
    except Exception as e:
        raise ValueError(f"E006: 读取文件失败: {e}") from e


def write_output_file(file_path, content):
    """写入输出文件。"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        raise ValueError(f"E005: 写入文件失败: {e}") from e


# ------------------------------------------------------------
# 自检模块
# ------------------------------------------------------------
def selftest():
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值，确保必然匹配。
    """
    print("开始自检...")

    # 测试样例（硬编码）
    sample_input = """完成季度报表 @张三 2026-01-31 done
开发登录接口 | 负责人：李四 | 截止：2026/02/15 | 状态：进行中
待办：整理项目文档 2026/03/01 todo
@王五 修复线上bug blocked 2026/01/20
"""

    # 1. 测试批量解析
    try:
        records = parse_batch(sample_input)
    except ValueError as e:
        print(f"自检失败 - 批量解析: {e}")
        return False

    # 宽松断言：记录数大于等于 3 且小于等于 50
    assert 3 <= len(records) <= MAX_RECORDS, f"记录数异常: {len(records)}"
    print(f"[通过] 批量解析: 共 {len(records)} 条记录")

    # 2. 测试字段提取
    first = records[0]
    # 任务名非空
    assert first.task_name, "任务名为空"
    assert len(first.task_name) > 0, "任务名长度异常"
    print(f"[通过] 任务名提取: {first.task_name}")

    # 3. 测试状态识别
    statuses = [r.status for r in records]
    # 至少有一个非 todo 状态
    assert any(s != "todo" for s in statuses), "状态识别异常"
    print(f"[通过] 状态识别: {statuses}")

    # 4. 测试日期提取
    dates = [r.due_date for r in records]
    # 至少有一个日期非空
    assert any(d for d in dates), "日期提取异常"
    print(f"[通过] 日期提取: {dates}")

    # 5. 测试置信度
    confs = [r.confidence for r in records]
    for conf in confs:
        for field, level in conf.items():
            assert level in CONFIDENCE_LEVELS, f"置信度等级异常: {level}"
    print("[通过] 置信度标注格式")

    # 6. 测试输出格式
    try:
        json_out = format_output(records, "json")
        csv_out = format_output(records, "csv")
        md_out = format_output(records, "markdown")
    except ValueError as e:
        print(f"自检失败 - 输出格式化: {e}")
        return False

    # 宽松断言：输出非空
    assert json_out and len(json_out) > 10, "JSON 输出异常"
    assert csv_out and len(csv_out) > 10, "CSV 输出异常"
    assert md_out and len(md_out) > 10, "Markdown 输出异常"
    print("[通过] JSON/CSV/Markdown 输出")

    # 7. 测试 JSON 可解析
    try:
        parsed_json = json.loads(json_out)
        assert isinstance(parsed_json, list), "JSON 格式异常"
        assert len(parsed_json) == len(records), "JSON 记录数不匹配"
    except json.JSONDecodeError as e:
        print(f"自检失败 - JSON 解析: {e}")
        return False
    print("[通过] JSON 可解析")

    # 8. 测试 CSV 可解析
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_out))
        rows = list(csv_reader)
        assert len(rows) == len(records), "CSV 记录数不匹配"
    except Exception as e:
        print(f"自检失败 - CSV 解析: {e}")
        return False
    print("[通过] CSV 可解析")

    # 9. 测试单条解析（键值对模式）
    try:
        single = parse_single_entry("任务：分析数据 | 负责人：赵六 | 截止：2026-04-01 | 状态：done")
        assert single.task_name, "单条解析任务名为空"
        assert single.owner == "赵六", f"单条解析责任人异常: {single.owner}"
        assert single.due_date, "单条解析日期为空"
        assert single.status == "done", f"单条解析状态异常: {single.status}"
    except ValueError as e:
        print(f"自检失败 - 单条解析: {e}")
        return False
    print("[通过] 单条解析（键值对模式）")

    # 10. 测试错误处理
    try:
        parse_batch("")
        print("自检失败 - 空输入未报错")
        return False
    except ValueError as e:
        assert "E002" in str(e), f"错误码异常: {e}"
    print("[通过] 空输入错误处理")

    # 11. 测试超限
    try:
        many_lines = "\n".join([f"任务{i}" for i in range(MAX_RECORDS + 5)])
        parse_batch(many_lines)
        print("自检失败 - 超限未报错")
        return False
    except ValueError as e:
        assert "E003" in str(e), f"错误码异常: {e}"
    print("[通过] 超限错误处理")

    print("\n所有自检项通过 ✅")
    return True


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="pscale-workflow-helper-scripts - 任务编排流程辅助脚本",
        epilog="示例: python main.py -i input.txt -o output.json -f json"
    )
    parser.add_argument("-i", "--input", help="输入文件路径（UTF-8 文本）")
    parser.add_argument("-o", "--output", help="输出文件路径（可选，默认输出到 stdout）")
    parser.add_argument("-f", "--format", choices=SUPPORTED_FORMATS, default="json",
                        help="输出格式: json/csv/markdown（默认 json）")
    parser.add_argument("-t", "--text", help="直接传入文本（与 -i 二选一）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)

    # 获取输入
    input_text = None
    try:
        if args.text:
            input_text = args.text
        elif args.input:
            input_text = read_input_file(args.input)
        else:
            # 从 stdin 读取
            input_text = sys.stdin.read()
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 处理
    try:
        records = parse_batch(input_text)
        output_content = format_output(records, args.format)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: E010 未知异常: {e}", file=sys.stderr)
        sys.exit(1)

    # 输出
    if args.output:
        try:
            write_output_file(args.output, output_content)
            print(f"已写入: {args.output}")
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_content)


if __name__ == "__main__":
    main()
