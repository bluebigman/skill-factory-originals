#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toggl-tally 工时数据整理技能 - 独立实现脚本
版本: 1.0.5 (clean-room 实现)
"""

import json
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义
ERROR_CODES = {
    "E001": "输入数据为空或格式无效",
    "E002": "无法解析输入数据（不是文本/CSV/JSON/TXT格式）",
    "E003": "JSON解析失败",
    "E004": "CSV解析失败",
    "E005": "缺少必要字段（如时间戳或时长）",
    "E006": "时间戳格式无法识别",
    "E007": "时长格式无法识别",
    "E008": "数据记录数超过限制",
    "E009": "内部处理错误",
    "E010": "未知错误",
}


class TogglTallyError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


def _safe_float(value: Any) -> Optional[float]:
    """安全转换为浮点数"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_duration(duration: Any) -> Optional[float]:
    """
    解析时长字段为小时数。
    支持格式:
    - 秒数 (整数或浮点)
    - "HH:MM:SS"
    - "Xh Ym Zs" 或 "X小时Y分钟"
    - ISO8601 时长 (PT1H30M)
    """
    if duration is None:
        return None

    # 数字直接视为秒
    if isinstance(duration, (int, float)):
        seconds = float(duration)
        return seconds / 3600.0

    if isinstance(duration, str):
        text = duration.strip()
        if not text:
            return None

        # 纯数字字符串视为秒
        if re.fullmatch(r"\d+(\.\d+)?", text):
            return float(text) / 3600.0

        # HH:MM:SS 或 HH:MM
        m = re.fullmatch(r"(\d+):([0-5]?\d)(?::([0-5]?\d))?", text)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(2))
            seconds = int(m.group(3) or 0)
            return hours + minutes / 60.0 + seconds / 3600.0

        # ISO8601 格式 PT1H30M / PT30M / PT45S
        m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", text.upper())
        if m:
            hours = int(m.group(1) or 0)
            minutes = int(m.group(2) or 0)
            seconds = int(m.group(3) or 0)
            if hours == 0 and minutes == 0 and seconds == 0:
                return None
            return hours + minutes / 60.0 + seconds / 3600.0

        # 中文/英文混合格式 "1小时30分钟" / "1h30m"
        total_hours = 0.0
        found = False
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:小时|h|hr|hrs)", text, re.IGNORECASE)
        if m:
            total_hours += float(m.group(1))
            found = True
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:分钟|m|min|mins)", text, re.IGNORECASE)
        if m:
            total_hours += float(m.group(1)) / 60.0
            found = True
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:秒|s|sec|secs)", text, re.IGNORECASE)
        if m:
            total_hours += float(m.group(1)) / 3600.0
            found = True
        if found:
            return total_hours

    return None


def _parse_timestamp(value: Any) -> Optional[str]:
    """
    解析时间戳为 ISO 格式字符串。
    支持:
    - ISO8601 完整格式
    - "YYYY-MM-DD HH:MM:SS"
    - 日期 + 时间 的组合
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # Unix 时间戳
        try:
            dt = datetime.fromtimestamp(float(value))
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except (ValueError, OSError):
            return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        # 尝试多种格式
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue

        # 仅日期
        try:
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT00:00:00")
        except ValueError:
            pass

    return None


def _extract_field(record: Dict[str, Any], *keys: str) -> Any:
    """从记录中提取字段，支持多个可能的键名"""
    for key in keys:
        if key in record and record[key] is not None and record[key] != "":
            return record[key]
    return None


def _normalize_record(record: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    规范化单条记录，提取关键字段并标注置信度。
    """
    result: Dict[str, Any] = {
        "id": index,
        "project": None,
        "description": None,
        "start": None,
        "end": None,
        "duration_hours": None,
        "tags": [],
        "confidence": "high",
        "notes": [],
    }

    # 项目名称
    project = _extract_field(record, "project", "Project", "项目", "项目名称")
    if project:
        result["project"] = str(project).strip()

    # 任务描述
    description = _extract_field(record, "description", "Description", "task", "Task", "描述", "任务描述")
    if description:
        result["description"] = str(description).strip()

    # 时间戳
    start = _extract_field(record, "start", "Start", "start_time", "开始时间")
    end = _extract_field(record, "end", "End", "end_time", "结束时间")

    if start:
        parsed_start = _parse_timestamp(start)
        if parsed_start:
            result["start"] = parsed_start
        else:
            result["notes"].append("[需核实:开始时间格式]")
            result["confidence"] = "low"

    if end:
        parsed_end = _parse_timestamp(end)
        if parsed_end:
            result["end"] = parsed_end
        else:
            result["notes"].append("[需核实:结束时间格式]")
            result["confidence"] = "low"

    # 时长
    duration = _extract_field(record, "duration", "Duration", "dur", "时长", "工时")
    if duration is not None:
        parsed_duration = _parse_duration(duration)
        if parsed_duration is not None:
            result["duration_hours"] = parsed_duration
        else:
            result["notes"].append("[需核实:时长]")
            result["confidence"] = "low"
    else:
        # 尝试从开始/结束时间计算
        if result["start"] and result["end"]:
            try:
                start_dt = datetime.fromisoformat(result["start"])
                end_dt = datetime.fromisoformat(result["end"])
                delta = end_dt - start_dt
                if delta.total_seconds() > 0:
                    result["duration_hours"] = delta.total_seconds() / 3600.0
                else:
                    result["notes"].append("[需核实:时长]")
                    result["confidence"] = "low"
            except ValueError:
                result["notes"].append("[需核实:时长]")
                result["confidence"] = "low"
        else:
            result["notes"].append("[需核实:时长]")
            result["confidence"] = "low"

    # 标签
    tags = _extract_field(record, "tags", "Tags", "labels", "标签")
    if tags:
        if isinstance(tags, list):
            result["tags"] = [str(t).strip() for t in tags if t]
        elif isinstance(tags, str):
            result["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    # 置信度综合判断
    if result["duration_hours"] is None:
        result["confidence"] = "low"
    elif result["confidence"] == "high" and (not result["start"] or not result["end"]):
        result["confidence"] = "medium"

    return result


def _parse_text_data(text: str) -> List[Dict[str, Any]]:
    """
    解析纯文本数据，尝试识别工时记录。
    支持简单格式: "项目, 描述, 时长" 每行一条
    """
    records = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for i, line in enumerate(lines):
        # 尝试逗号/制表符分隔
        parts = re.split(r"[,;\t|]", line)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) >= 2:
            record: Dict[str, Any] = {}
            if len(parts) >= 1:
                record["project"] = parts[0]
            if len(parts) >= 2:
                record["description"] = parts[1]
            if len(parts) >= 3:
                record["duration"] = parts[2]
            if len(parts) >= 4:
                record["start"] = parts[3]
            if len(parts) >= 5:
                record["end"] = parts[4]
            if len(parts) >= 6:
                record["tags"] = parts[5]
            records.append(record)
        else:
            # 尝试识别 "描述 时长" 格式
            m = re.match(r"(.+?)\s+(\d+[hHmMsS]|\d+:\d+(?::\d+)?)$", line)
            if m:
                records.append({
                    "description": m.group(1).strip(),
                    "duration": m.group(2).strip(),
                })

    return records


def _parse_csv_data(text: str) -> List[Dict[str, Any]]:
    """解析 CSV 数据"""
    import csv
    import io

    records = []
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            # 过滤完全空的行
            if any(v for v in row.values() if v and v.strip()):
                records.append(row)
    except Exception:
        raise TogglTallyError("E004")

    return records


def _parse_json_data(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 数据"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise TogglTallyError("E003")

    if isinstance(data, dict):
        # 尝试从常见键提取记录列表
        for key in ["records", "data", "entries", "items", "工时记录", "记录"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        # 单条记录
        return [data]
    elif isinstance(data, list):
        return data
    else:
        raise TogglTallyError("E002")


def process_data(input_data: Any) -> Dict[str, Any]:
    """
    主处理函数：将输入数据转换为结构化结果。

    参数:
        input_data: 可以是字符串（文本/CSV/JSON）、字典、列表

    返回:
        包含处理结果和元数据的字典
    """
    try:
        # 输入校验
        if input_data is None:
            raise TogglTallyError("E001")
        if isinstance(input_data, str) and not input_data.strip():
            raise TogglTallyError("E001")

        # 解析输入
        raw_records: List[Dict[str, Any]] = []

        if isinstance(input_data, str):
            text = input_data.strip()
            # 尝试 JSON
            if text.startswith("[") or text.startswith("{"):
                try:
                    raw_records = _parse_json_data(text)
                except TogglTallyError:
                    # 不是 JSON，尝试 CSV
                    if "," in text or "\t" in text:
                        raw_records = _parse_csv_data(text)
                    else:
                        raw_records = _parse_text_data(text)
            elif "," in text or "\t" in text:
                # 检查是否有表头
                first_line = text.split("\n")[0].strip().lower()
                if any(kw in first_line for kw in ["project", "description", "duration", "项目", "描述", "时长"]):
                    # 有表头，按 CSV 处理
                    raw_records = _parse_csv_data(text)
                else:
                    # 无表头，尝试按文本处理
                    raw_records = _parse_text_data(text)
            else:
                raw_records = _parse_text_data(text)
        elif isinstance(input_data, list):
            raw_records = input_data
        elif isinstance(input_data, dict):
            raw_records = [input_data]
        else:
            raise TogglTallyError("E002")

        if not raw_records:
            raise TogglTallyError("E001")

        # 记录数限制
        if len(raw_records) > 10000:
            raise TogglTallyError("E008")

        # 规范化每条记录
        processed_records = []
        for i, record in enumerate(raw_records):
            if isinstance(record, dict):
                processed_records.append(_normalize_record(record, i + 1))

        # 按开始时间排序
        processed_records.sort(key=lambda r: r["start"] or "")

        # 去重（基于项目+描述+时长+开始时间）
        seen = set()
        unique_records = []
        for record in processed_records:
            key = (
                record["project"] or "",
                record["description"] or "",
                record["duration_hours"],
                record["start"] or "",
            )
            if key not in seen:
                seen.add(key)
                unique_records.append(record)

        # 统计信息
        total_hours = sum(r["duration_hours"] or 0 for r in unique_records)
        high_conf = sum(1 for r in unique_records if r["confidence"] == "high")

        result = {
            "status": "success",
            "record_count": len(unique_records),
            "total_hours": round(total_hours, 2),
            "high_confidence_count": high_conf,
            "records": unique_records,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }

        return result

    except TogglTallyError:
        raise
    except Exception as e:
        raise TogglTallyError("E009", str(e))


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    格式化输出结果。
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        lines = [
            "# 工时统计结果",
            "",
            f"- 记录数: {result['record_count']}",
            f"- 总工时: {result['total_hours']} 小时",
            f"- 高置信度记录: {result['high_confidence_count']}",
            "",
            "| 序号 | 项目 | 描述 | 开始时间 | 结束时间 | 时长(小时) | 置信度 |",
            "|------|------|------|----------|----------|------------|--------|",
        ]
        for record in result["records"]:
            lines.append(
                f"| {record['id']} | {record['project'] or '-'} | "
                f"{record['description'] or '-'} | {record['start'] or '-'} | "
                f"{record['end'] or '-'} | {record['duration_hours'] or '-'} | "
                f"{record['confidence']} |"
            )
        return "\n".join(lines)
    else:
        raise TogglTallyError("E010", f"不支持的输出格式: {output_format}")


# ============ 自检功能 ============

def _run_selftest() -> bool:
    """
    内置自检功能，使用硬编码样例数据验证核心逻辑。
    不依赖外部文件、网络或当前工作目录。
    """
    print("开始自检...")

    # 测试数据 1: JSON 格式
    json_data = json.dumps([
        {
            "project": "网站开发",
            "description": "实现登录功能",
            "start": "2026-01-05T09:00:00",
            "end": "2026-01-05T11:30:00",
            "duration": "2h30m",
            "tags": ["前端", "认证"]
        },
        {
            "project": "数据分析",
            "description": "清洗用户数据",
            "start": "2026-01-05T13:00:00",
            "duration": "PT1H45M",
            "tags": ["Python"]
        },
        {
            "project": "会议",
            "description": "项目周会",
            "start": "2026-01-06T10:00:00",
            "end": "2026-01-06T11:00:00",
        }
    ])

    try:
        result = process_data(json_data)
        assert result["status"] == "success", "处理失败"
        assert result["record_count"] >= 2, "记录数不足"
        assert result["total_hours"] > 0, "总时长为0"
        assert result["high_confidence_count"] >= 1, "高置信度记录不足"

        # 检查时长计算
        first = result["records"][0]
        assert first["duration_hours"] is not None, "时长未解析"
        assert first["duration_hours"] > 0, "时长不为正"
        assert first["duration_hours"] < 24, "时长不合理"

        print(f"  [PASS] JSON 解析: {result['record_count']} 条记录, 总时长 {result['total_hours']} 小时")
    except AssertionError as e:
        print(f"  [FAIL] JSON 测试: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] JSON 测试异常: {e}")
        return False

    # 测试数据 2: CSV 格式
    csv_data = "Project,Description,Duration,Start,End\n"
    csv_data += "API开发,设计REST接口,3h,2026-01-07T09:00:00,2026-01-07T12:00:00\n"
    csv_data += "测试,编写单元测试,1.5h,2026-01-07T14:00:00,2026-01-07T15:30:00\n"
    csv_data += "DevOps,部署流水线,90m,2026-01-08T10:00:00,2026-01-08T11:30:00\n"

    try:
        result = process_data(csv_data)
        assert result["status"] == "success", "处理失败"
        assert result["record_count"] >= 2, "记录数不足"
        assert result["total_hours"] > 0, "总时长为0"

        # 验证时长解析 (90分钟 = 1.5小时)
        devops = [r for r in result["records"] if r["project"] == "DevOps"]
        assert len(devops) == 1, "DevOps 记录不存在"
        assert devops[0]["duration_hours"] is not None, "时长未解析"
        assert devops[0]["duration_hours"] > 1.0, "时长解析错误"
        assert devops[0]["duration_hours"] < 2.0, "时长解析错误"

        print(f"  [PASS] CSV 解析: {result['record_count']} 条记录, 总时长 {result['total_hours']} 小时")
    except AssertionError as e:
        print(f"  [FAIL] CSV 测试: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] CSV 测试异常: {e}")
        return False

    # 测试数据 3: 纯文本格式
    text_data = """网站开发, 修复bug, 2h
数据分析, 生成报表, 1h30m
会议, 需求讨论, 45m"""

    try:
        result = process_data(text_data)
        assert result["status"] == "success", "处理失败"
        assert result["record_count"] >= 2, "记录数不足"
        assert result["total_hours"] > 0, "总时长为0"

        print(f"  [PASS] 文本解析: {result['record_count']} 条记录, 总时长 {result['total_hours']} 小时")
    except AssertionError as e:
        print(f"  [FAIL] 文本测试: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 文本测试异常: {e}")
        return False

    # 测试数据 4: 错误处理
    try:
        process_data("")
        print("  [FAIL] 空输入未报错")
        return False
    except TogglTallyError as e:
        assert e.error_code in ("E001", "E002"), f"错误码不正确: {e.error_code}"
        print(f"  [PASS] 错误处理: {e.error_code}")

    # 测试数据 5: Markdown 输出
    try:
        result = process_data(json_data)
        md_output = format_output(result, "markdown")
        assert "|" in md_output, "Markdown 表格格式错误"
        assert "工时统计" in md_output, "Markdown 标题缺失"
        print("  [PASS] Markdown 输出")
    except AssertionError as e:
        print(f"  [FAIL] Markdown 测试: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Markdown 测试异常: {e}")
        return False

    # 测试数据 6: 时长解析边界
    try:
        # 测试各种时长格式
        assert abs(_parse_duration("3600") - 1.0) < 0.01, "秒数解析失败"
        assert abs(_parse_duration("1:30:00") - 1.5) < 0.01, "HH:MM:SS 解析失败"
        assert abs(_parse_duration("PT2H15M") - 2.25) < 0.01, "ISO8601 解析失败"
        assert abs(_parse_duration("1小时30分钟") - 1.5) < 0.01, "中文解析失败"
        assert _parse_duration("invalid") is None, "无效时长未返回 None"
        print("  [PASS] 时长格式解析")
    except AssertionError as e:
        print(f"  [FAIL] 时长解析测试: {e}")
        return False

    print("所有自检通过！")
    return True


def main() -> int:
    """命令行入口"""
    args = sys.argv[1:]

    # 自检模式
    if "--selftest" in args:
        success = _run_selftest()
        return 0 if success else 1

    # 帮助
    if "--help" in args or "-h" in args:
        print("""toggl-tally 工时数据整理工具

用法:
  python main.py --selftest    运行自检
  python main.py <input>       处理输入数据 (文件路径或 JSON 字符串)
  python main.py --help        显示帮助

选项:
  --selftest    运行内置自检，不依赖外部文件
  --format      输出格式: json (默认) 或 markdown
""")
        return 0

    # 处理输入
    if len(args) == 0:
        print("错误: 未提供输入。使用 --help 查看用法。", file=sys.stderr)
        return 1

    input_arg = args[0]
    output_format = "json"
    if "--format" in args:
        idx = args.index("--format")
        if idx + 1 < len(args):
            output_format = args[idx + 1]

    try:
        # 尝试读取文件
        import os
        if os.path.isfile(input_arg):
            with open(input_arg, "r", encoding="utf-8") as f:
                input_data = f.read()
        else:
            # 尝试直接解析为 JSON
            input_data = input_arg

        result = process_data(input_data)
        print(format_output(result, output_format))
        return 0

    except TogglTallyError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
