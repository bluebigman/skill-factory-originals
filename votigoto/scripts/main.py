#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
votigoto - TiVo录播数据提取与节目清单解析

本脚本根据功能规格独立实现（clean-room），不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能：
- 解析 TiVoToGo 协议数据文本
- 提取节目名称、录制时间、时长、频道、状态等核心字段
- 输出 JSON / 文本 / 表格格式
- 支持批量数据输入
- 内置 --selftest 离线自检

用法示例：
    python main.py --input data.txt --format json
    python main.py --selftest
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件错误：无法读取输入文件",
    "E003": "数据错误：输入数据为空或格式无效",
    "E004": "解析错误：无法解析 TiVoToGo 协议数据",
    "E005": "输出错误：无法生成输出内容",
    "E006": "自检错误：自检失败",
    "E007": "批量处理错误：批量数据中存在无效条目",
    "E008": "格式错误：不支持的输出格式",
    "E009": "字段错误：指定的输出字段不存在",
    "E010": "内部错误：未预期的异常",
}

# 输出格式支持列表
SUPPORTED_FORMATS = ["json", "text", "table"]

# 字段置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 默认输出字段（按规格 C3 约定）
DEFAULT_FIELDS = [
    "title",          # 节目名称
    "record_time",    # 录制时间
    "duration",       # 时长
    "channel",        # 频道
    "status",         # 状态
]

# 缺失字段占位符（按规格 L3）
MISSING_FIELD_PLACEHOLDER = "[需核实:{field}]"


# ============================================================
# 核心数据结构
# ============================================================

class TiVoRecord:
    """TiVo 录播单条记录数据结构"""
    
    def __init__(self) -> None:
        self.title: str = ""
        self.record_time: Optional[datetime] = None
        self.duration_minutes: Optional[int] = None
        self.channel: str = ""
        self.status: str = ""
        self.raw_data: str = ""
        self.confidence: Dict[str, str] = {}  # 字段->置信度
        
    def to_dict(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """转换为字典输出"""
        result: Dict[str, Any] = {}
        
        # 确定要输出的字段
        output_fields = fields if fields else DEFAULT_FIELDS
        
        for field in output_fields:
            if field == "title":
                result["title"] = self.title or MISSING_FIELD_PLACEHOLDER.format(field="节目名称")
            elif field == "record_time":
                if self.record_time:
                    result["record_time"] = self.record_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    result["record_time"] = MISSING_FIELD_PLACEHOLDER.format(field="录制时间")
            elif field == "duration":
                if self.duration_minutes is not None:
                    hours = self.duration_minutes // 60
                    minutes = self.duration_minutes % 60
                    result["duration"] = f"{hours}小时{minutes}分钟"
                else:
                    result["duration"] = MISSING_FIELD_PLACEHOLDER.format(field="时长")
            elif field == "channel":
                result["channel"] = self.channel or MISSING_FIELD_PLACEHOLDER.format(field="频道")
            elif field == "status":
                result["status"] = self.status or MISSING_FIELD_PLACEHOLDER.format(field="状态")
            elif field == "confidence":
                # 输出置信度信息
                result["confidence"] = self.confidence
            else:
                # 按规格 L3，不猜测填充未知字段
                result[field] = MISSING_FIELD_PLACEHOLDER.format(field=field)
        
        return result


# ============================================================
# 解析器
# ============================================================

class TiVoParser:
    """TiVoToGo 协议数据解析器"""
    
    # 正则表达式模式
    PATTERN_TITLE = re.compile(r'(?:title|节目名称)\s*[=:]\s*"?([^",\n]+)"?')
    PATTERN_DATETIME = re.compile(
        r'(?:record[_\s]?time|录制时间)\s*[=:]\s*"?'
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})'
        r'[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?'
        r'"?'
    )
    PATTERN_DATETIME_ALT = re.compile(
        r'(?:record[_\s]?time|录制时间)\s*[=:]\s*"?'
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
        r'[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?'
        r'"?'
    )
    PATTERN_DURATION = re.compile(
        r'(?:duration|时长)\s*[=:]\s*"?(\d+)\s*(?:分钟|min|mins|m)?"?'
    )
    PATTERN_DURATION_HMS = re.compile(
        r'(?:duration|时长)\s*[=:]\s*"?'
        r'(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?'
        r'"?'
    )
    PATTERN_CHANNEL = re.compile(r'(?:channel|频道)\s*[=:]\s*"?([^",\n]+)"?')
    PATTERN_STATUS = re.compile(r'(?:status|状态)\s*[=:]\s*"?([^",\n]+)"?')
    PATTERN_RECORD_ENTRY = re.compile(r'(?:record|条目|entry)\s*[{[]')
    
    def parse(self, data: str) -> List[TiVoRecord]:
        """解析 TiVoToGo 协议数据"""
        if not data or not data.strip():
            raise ValueError("E003")
        
        records: List[TiVoRecord] = []
        
        # 尝试按条目分割
        entries = self._split_entries(data)
        
        if entries:
            # 多条目解析
            for entry in entries:
                record = self._parse_single(entry)
                if record.title or record.record_time:
                    records.append(record)
        else:
            # 单条目解析
            record = self._parse_single(data)
            if record.title or record.record_time:
                records.append(record)
        
        if not records:
            raise ValueError("E004")
        
        return records
    
    def _split_entries(self, data: str) -> List[str]:
        """将数据分割为多个条目"""
        # 查找条目分隔符
        matches = list(self.PATTERN_RECORD_ENTRY.finditer(data))
        if len(matches) <= 1:
            return []
        
        entries = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(data)
            entries.append(data[start:end])
        
        return entries
    
    def _parse_single(self, text: str) -> TiVoRecord:
        """解析单个条目"""
        record = TiVoRecord()
        record.raw_data = text.strip()
        
        # 解析节目名称
        title_match = self.PATTERN_TITLE.search(text)
        if title_match:
            record.title = title_match.group(1).strip()
            record.confidence["title"] = CONFIDENCE_HIGH
        else:
            record.confidence["title"] = CONFIDENCE_LOW
        
        # 解析录制时间（优先 ISO 格式）
        dt_match = self.PATTERN_DATETIME.search(text) or self.PATTERN_DATETIME_ALT.search(text)
        if dt_match:
            try:
                groups = dt_match.groups()
                if len(groups[0]) == 4:  # 年份在前
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    hour, minute = int(groups[3]), int(groups[4])
                    second = int(groups[5]) if groups[5] else 0
                else:  # 日期在前
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    hour, minute = int(groups[3]), int(groups[4])
                    second = int(groups[5]) if groups[5] else 0
                
                record.record_time = datetime(year, month, day, hour, minute, second)
                record.confidence["record_time"] = CONFIDENCE_HIGH
            except (ValueError, IndexError):
                record.confidence["record_time"] = CONFIDENCE_LOW
        else:
            record.confidence["record_time"] = CONFIDENCE_LOW
        
        # 解析时长
        dur_match = self.PATTERN_DURATION.search(text)
        if dur_match:
            try:
                record.duration_minutes = int(dur_match.group(1))
                record.confidence["duration"] = CONFIDENCE_HIGH
            except (ValueError, IndexError):
                record.confidence["duration"] = CONFIDENCE_LOW
        else:
            # 尝试时分秒格式
            dur_hms = self.PATTERN_DURATION_HMS.search(text)
            if dur_hms:
                try:
                    hours = int(dur_hms.group(1)) if dur_hms.group(1) else 0
                    minutes = int(dur_hms.group(2)) if dur_hms.group(2) else 0
                    seconds = int(dur_hms.group(3)) if dur_hms.group(3) else 0
                    record.duration_minutes = hours * 60 + minutes + (seconds // 60)
                    record.confidence["duration"] = CONFIDENCE_MEDIUM
                except (ValueError, IndexError):
                    record.confidence["duration"] = CONFIDENCE_LOW
            else:
                record.confidence["duration"] = CONFIDENCE_LOW
        
        # 解析频道
        ch_match = self.PATTERN_CHANNEL.search(text)
        if ch_match:
            record.channel = ch_match.group(1).strip()
            record.confidence["channel"] = CONFIDENCE_HIGH
        else:
            record.confidence["channel"] = CONFIDENCE_LOW
        
        # 解析状态
        st_match = self.PATTERN_STATUS.search(text)
        if st_match:
            record.status = st_match.group(1).strip()
            record.confidence["status"] = CONFIDENCE_HIGH
        else:
            record.confidence["status"] = CONFIDENCE_LOW
        
        return record


# ============================================================
# 输出格式化器
# ============================================================

class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format_records(records: List[TiVoRecord], fmt: str = "json", fields: Optional[List[str]] = None) -> str:
        """格式化输出记录列表"""
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError("E008")
        
        if fmt == "json":
            return OutputFormatter._to_json(records, fields)
        elif fmt == "text":
            return OutputFormatter._to_text(records, fields)
        elif fmt == "table":
            return OutputFormatter._to_table(records, fields)
        else:
            raise ValueError("E008")
    
    @staticmethod
    def _to_json(records: List[TiVoRecord], fields: Optional[List[str]] = None) -> str:
        """JSON 格式输出"""
        data = [record.to_dict(fields) for record in records]
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _to_text(records: List[TiVoRecord], fields: Optional[List[str]] = None) -> str:
        """文本格式输出"""
        lines = []
        for i, record in enumerate(records, 1):
            lines.append(f"=== 记录 {i} ===")
            data = record.to_dict(fields)
            for key, value in data.items():
                if key != "confidence":
                    lines.append(f"  {key}: {value}")
            if "confidence" in data:
                lines.append("  置信度:")
                for field, level in data["confidence"].items():
                    lines.append(f"    {field}: {level}")
            lines.append("")
        return "\n".join(lines)
    
    @staticmethod
    def _to_table(records: List[TiVoRecord], fields: Optional[List[str]] = None) -> str:
        """表格格式输出"""
        if not records:
            return "(空)"
        
        # 确定输出字段
        output_fields = fields if fields else DEFAULT_FIELDS
        
        # 收集表头
        headers = output_fields
        
        # 收集行数据
        rows = []
        for record in records:
            data = record.to_dict(output_fields)
            row = []
            for field in output_fields:
                value = data.get(field, "")
                # 格式化值
                if field == "record_time" and isinstance(value, str):
                    row.append(value)
                elif field == "duration" and isinstance(value, str):
                    row.append(value)
                else:
                    row.append(str(value))
            rows.append(row)
        
        # 计算列宽
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in rows:
                max_width = max(max_width, len(row[i]))
            col_widths.append(max_width + 2)
        
        # 生成表格
        lines = []
        # 表头
        header_line = "|" + "|".join(
            f" {header.center(col_widths[i] - 2)} " for i, header in enumerate(headers)
        ) + "|"
        lines.append(header_line)
        lines.append("|" + "|".join("-" * col_widths[i] for i in range(len(headers))) + "|")
        
        # 数据行
        for row in rows:
            line = "|" + "|".join(
                f" {cell.ljust(col_widths[i] - 2)} " for i, cell in enumerate(row)
            ) + "|"
            lines.append(line)
        
        return "\n".join(lines)


# ============================================================
# 主处理逻辑
# ============================================================

def process_data(data: str, fmt: str = "json", fields: Optional[List[str]] = None) -> str:
    """处理 TiVoToGo 数据并返回格式化结果"""
    try:
        # 解析数据
        parser = TiVoParser()
        records = parser.parse(data)
        
        # 格式化输出
        formatter = OutputFormatter()
        return formatter.format_records(records, fmt, fields)
    
    except ValueError as e:
        error_code = str(e) if str(e).startswith("E") else "E004"
        return json.dumps({"error": error_code, "message": ERROR_CODES.get(error_code, "未知错误")}, ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "E010", "message": ERROR_CODES["E010"]}, ensure_ascii=False)


def process_file(filepath: str, fmt: str = "json", fields: Optional[List[str]] = None) -> str:
    """从文件读取并处理数据"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = f.read()
        return process_data(data, fmt, fields)
    except FileNotFoundError:
        return json.dumps({"error": "E002", "message": ERROR_CODES["E002"]}, ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "E010", "message": ERROR_CODES["E010"]}, ensure_ascii=False)


def process_batch(data_list: List[str], fmt: str = "json", fields: Optional[List[str]] = None) -> List[str]:
    """批量处理多条数据"""
    results = []
    for data in data_list:
        results.append(process_data(data, fmt, fields))
    return results


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """离线自检核心逻辑，使用硬编码样例数据"""
    print("开始自检...")
    
    # 测试数据 1：单条完整记录
    test_data_1 = """
    record {
        title: "科技前沿",
        record_time: "2025-01-15T20:30:00",
        duration: 45分钟,
        channel: "CCTV-10",
        status: "已完成"
    }
    """
    
    # 测试数据 2：多条记录，包含不同格式
    test_data_2 = """
    record {
        title: "自然探秘",
        record_time: 2025/02/01 19:00,
        duration: 30min,
        channel: "BBC",
        status: "录制中"
    }
    record {
        title: "历史解密",
        record_time: "2025-03-10 14:15:30",
        duration: 1h30m,
        channel: "历史频道",
        status: "已完成"
    }
    """
    
    # 测试数据 3：缺失字段的简单数据
    test_data_3 = """
    title: "简单测试节目"
    channel: "测试频道"
    """
    
    try:
        # 测试 1：解析单条记录
        print("测试 1：解析单条完整记录")
        parser = TiVoParser()
        records = parser.parse(test_data_1)
        assert len(records) == 1, f"预期 1 条记录，实际 {len(records)} 条"
        record = records[0]
        assert record.title == "科技前沿", f"标题解析错误: {record.title}"
        assert record.record_time is not None, "录制时间未解析"
        assert record.record_time.year == 2025, f"年份错误: {record.record_time.year}"
        assert record.record_time.month == 1, f"月份错误: {record.record_time.month}"
        assert record.duration_minutes == 45, f"时长错误: {record.duration_minutes}"
        assert record.channel == "CCTV-10", f"频道错误: {record.channel}"
        assert record.status == "已完成", f"状态错误: {record.status}"
        print("  ✓ 通过")
        
        # 测试 2：解析多条记录
        print("测试 2：解析多条记录")
        records = parser.parse(test_data_2)
        assert len(records) == 2, f"预期 2 条记录，实际 {len(records)} 条"
        # 第一条
        assert records[0].title == "自然探秘", f"第一条标题错误: {records[0].title}"
        assert records[0].duration_minutes == 30, f"第一条时长错误: {records[0].duration_minutes}"
        # 第二条
        assert records[1].title == "历史解密", f"第二条标题错误: {records[1].title}"
        assert records[1].duration_minutes == 90, f"第二条时长错误: {records[1].duration_minutes}"
        print("  ✓ 通过")
        
        # 测试 3：缺失字段处理
        print("测试 3：缺失字段处理")
        records = parser.parse(test_data_3)
        assert len(records) == 1, f"预期 1 条记录，实际 {len(records)} 条"
        record = records[0]
        assert record.title == "简单测试节目", f"标题错误: {record.title}"
        assert record.record_time is None, "缺失时间应为 None"
        assert record.duration_minutes is None, "缺失时长应为 None"
        assert record.channel == "测试频道", f"频道错误: {record.channel}"
        print("  ✓ 通过")
        
        # 测试 4：JSON 输出格式
        print("测试 4：JSON 输出格式")
        output = process_data(test_data_1, fmt="json")
        parsed_output = json.loads(output)
        assert isinstance(parsed_output, list), "JSON 输出应为列表"
        assert len(parsed_output) == 1, f"JSON 输出长度错误: {len(parsed_output)}"
        assert "title" in parsed_output[0], "JSON 输出缺少 title 字段"
        assert "record_time" in parsed_output[0], "JSON 输出缺少 record_time 字段"
        print("  ✓ 通过")
        
        # 测试 5：文本输出格式
        print("测试 5：文本输出格式")
        output = process_data(test_data_1, fmt="text")
        assert "科技前沿" in output, "文本输出缺少标题"
        assert "45" in output, "文本输出缺少时长"
        print("  ✓ 通过")
        
        # 测试 6：表格输出格式
        print("测试 6：表格输出格式")
        output = process_data(test_data_1, fmt="table")
        assert "title" in output, "表格输出缺少表头"
        assert "科技前沿" in output, "表格输出缺少数据"
        print("  ✓ 通过")
        
        # 测试 7：置信度标注
        print("测试 7：置信度标注")
        records = parser.parse(test_data_1)
        assert records[0].confidence["title"] == CONFIDENCE_HIGH, "标题置信度应为高"
        assert records[0].confidence["record_time"] == CONFIDENCE_HIGH, "时间置信度应为高"
        records = parser.parse(test_data_3)
        assert records[0].confidence["record_time"] == CONFIDENCE_LOW, "缺失时间置信度应为低"
        print("  ✓ 通过")
        
        # 测试 8：字段子集输出
        print("测试 8：字段子集输出")
        output = process_data(test_data_1, fmt="json", fields=["title", "channel"])
        parsed_output = json.loads(output)
        assert "title" in parsed_output[0], "子集输出缺少 title"
        assert "channel" in parsed_output[0], "子集输出缺少 channel"
        assert "record_time" not in parsed_output[0], "子集输出不应包含 record_time"
        print("  ✓ 通过")
        
        # 测试 9：错误处理
        print("测试 9：错误处理")
        # 空数据
        result = process_data("")
        assert "error" in result, "空数据应返回错误"
        # 无效格式
        result = process_data("无效数据", fmt="xml")
        assert "E008" in result, "无效格式应返回 E008"
        print("  ✓ 通过")
        
        # 测试 10：批量处理
        print("测试 10：批量处理")
        results = process_batch([test_data_1, test_data_3])
        assert len(results) == 2, f"批量处理结果数量错误: {len(results)}"
        assert json.loads(results[0])[0]["title"] == "科技前沿", "批量处理第一条结果错误"
        assert json.loads(results[1])[0]["title"] == "简单测试节目", "批量处理第二条结果错误"
        print("  ✓ 通过")
        
        print("\n全部自检通过 ✓")
        return True
        
    except AssertionError as e:
        print(f"自检失败: {e}")
        return False
    except Exception as e:
        print(f"自检异常: {e}")
        return False


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="votigoto - TiVo录播数据提取与节目清单解析",
        epilog="示例: python main.py --input data.txt --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径（TiVoToGo 协议数据文件）"
    )
    
    parser.add_argument(
        "--data", "-d",
        type=str,
        help="直接提供 TiVoToGo 协议数据字符串"
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=SUPPORTED_FORMATS,
        default="json",
        help=f"输出格式（默认: json，可选: {', '.join(SUPPORTED_FORMATS)}）"
    )
    
    parser.add_argument(
        "--fields",
        type=str,
        help="指定输出字段，逗号分隔（例如: title,channel,duration）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 解析字段参数
    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        # 验证字段
        valid_fields = DEFAULT_FIELDS + ["confidence"]
        for field in fields:
            if field not in valid_fields:
                print(f"错误 E009: 字段 '{field}' 不存在。可用字段: {', '.join(valid_fields)}")
                return 1
    
    # 处理输入
    try:
        if args.input:
            # 从文件读取
            result = process_file(args.input, args.format, fields)
            print(result)
        elif args.data:
            # 直接处理数据
            result = process_data(args.data, args.format, fields)
            print(result)
        else:
            # 无输入，显示帮助
            parser.print_help()
            return 1
    except Exception as e:
        print(f"错误 E010: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
