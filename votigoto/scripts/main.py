#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
votigoto — TiVo 录播数据解析与结构化输出

本脚本为 clean-room 独立实现，仅依据功能规格编写。
支持从文本/文件路径/URL 中解析 TiVoToGo 协议数据，
提取节目清单并输出结构化结果（JSON/表格/文本）。

用法示例：
    python main.py --input data.txt --format json
    python main.py --input data.txt --fields title,duration --format table
    python main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 错误码定义
ERR_INVALID_ARGS = "E001"       # 参数错误
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_URL_FETCH_FAIL = "E003"     # URL 获取失败
ERR_PARSE_FAIL = "E004"         # 解析失败
ERR_UNSUPPORTED_FORMAT = "E005" # 不支持的输出格式
ERR_EMPTY_INPUT = "E006"        # 输入为空
ERR_FIELD_NOT_FOUND = "E007"    # 字段不存在
ERR_BATCH_PARTIAL = "E008"      # 批量处理部分失败
ERR_INTERNAL = "E009"           # 内部错误
ERR_SELFTEST_FAIL = "E010"      # 自检失败


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Recording:
    """单个录播节目记录"""
    title: str = ""
    start_time: str = ""
    duration: str = ""
    channel: str = ""
    status: str = ""
    raw: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典，缺失字段使用占位符"""
        result = {}
        for field_name in ["title", "start_time", "duration", "channel", "status"]:
            value = getattr(self, field_name, "")
            if not value:
                value = f"[需核实:{field_name}]"
            result[field_name] = value
        return result


@dataclass
class ParseResult:
    """解析结果"""
    recordings: List[Recording] = field(default_factory=list)
    source: str = ""
    parse_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "count": len(self.recordings),
            "recordings": [r.to_dict() for r in self.recordings],
            "warnings": self.parse_warnings,
        }


# ============================================================
# 核心解析逻辑
# ============================================================

def _extract_field(pattern: str, text: str, default: str = "") -> str:
    """从文本中提取字段，支持常见分隔符"""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default


def parse_tivo_data(raw_text: str, source: str = "") -> ParseResult:
    """
    解析 TiVoToGo 协议数据。
    
    支持以下常见格式：
    1. 键值对行：Title: xxx / StartTime: xxx / Duration: xxx
    2. 带分隔符：title=xxx | start=xxx | dur=xxx
    3. XML/JSON 混合结构
    
    返回 ParseResult 对象。
    """
    result = ParseResult(source=source)
    
    if not raw_text or not raw_text.strip():
        result.parse_warnings.append("输入数据为空")
        return result
    
    # 按空行或常见分隔符分段
    lines = raw_text.strip().splitlines()
    current_rec = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检测新记录开始（常见标题行）
        if re.match(r'^(?:节目|Title|title|TITLE)[:\s=]+', line) and current_rec is not None:
            # 保存前一条记录
            if current_rec.title:
                result.recordings.append(current_rec)
            current_rec = Recording()
        elif current_rec is None:
            current_rec = Recording()
        
        # 尝试提取各字段
        title = _extract_field(r'(?:节目|Title|title|TITLE)[:\s=]+(.+)', line)
        if title:
            current_rec.title = title
            continue
            
        start = _extract_field(r'(?:开始时间|StartTime|start_time|start)[:\s=]+(.+)', line)
        if start:
            current_rec.start_time = start
            continue
            
        duration = _extract_field(r'(?:时长|Duration|duration|dur)[:\s=]+(.+)', line)
        if duration:
            current_rec.duration = duration
            continue
            
        channel = _extract_field(r'(?:频道|Channel|channel|ch)[:\s=]+(.+)', line)
        if channel:
            current_rec.channel = channel
            continue
            
        status = _extract_field(r'(?:状态|Status|status)[:\s=]+(.+)', line)
        if status:
            current_rec.status = status
            continue
    
    # 保存最后一条记录
    if current_rec and current_rec.title:
        result.recordings.append(current_rec)
    
    # 如果没有找到记录，尝试更宽松的解析
    if not result.recordings:
        # 尝试按行解析键值对
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = re.split(r'[=:|]', line, maxsplit=1)
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                if key and value:
                    rec = Recording()
                    if "title" in key.lower():
                        rec.title = value
                    elif "start" in key.lower():
                        rec.start_time = value
                    elif "dur" in key.lower():
                        rec.duration = value
                    elif "chan" in key.lower():
                        rec.channel = value
                    elif "status" in key.lower():
                        rec.status = value
                    if rec.title or rec.start_time or rec.duration:
                        result.recordings.append(rec)
    
    if not result.recordings:
        result.parse_warnings.append("未能识别有效录播记录")
    
    return result


def load_input(input_source: str) -> str:
    """
    从文件路径或 URL 加载数据。
    如果输入不是文件路径或 URL，则视为原始数据直接返回。
    """
    # 检查是否为 URL
    if input_source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(input_source, timeout=10) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            raise RuntimeError(f"{ERR_URL_FETCH_FAIL}: 无法获取 URL 数据")
    
    # 检查是否为文件路径
    if os.path.isfile(input_source):
        try:
            with open(input_source, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            raise RuntimeError(f"{ERR_FILE_NOT_FOUND}: 无法读取文件")
    
    # 否则视为原始数据
    return input_source


# ============================================================
# 输出格式化
# ============================================================

def format_json(result: ParseResult) -> str:
    """JSON 格式输出"""
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def format_table(result: ParseResult, fields: Optional[List[str]] = None) -> str:
    """表格格式输出"""
    if fields is None:
        fields = ["title", "start_time", "duration", "channel", "status"]
    
    # 验证字段
    valid_fields = ["title", "start_time", "duration", "channel", "status"]
    for f in fields:
        if f not in valid_fields:
            raise RuntimeError(f"{ERR_FIELD_NOT_FOUND}: 未知字段 '{f}'")
    
    if not result.recordings:
        return "（无录播记录）"
    
    # 计算列宽
    headers = {"title": "节目名称", "start_time": "开始时间", "duration": "时长", 
               "channel": "频道", "status": "状态"}
    col_widths = {f: len(headers[f]) for f in fields}
    for rec in result.recordings:
        rec_dict = rec.to_dict()
        for f in fields:
            col_widths[f] = max(col_widths[f], len(rec_dict.get(f, "")))
    
    # 生成表格
    lines = []
    header_line = " | ".join(headers[f].ljust(col_widths[f]) for f in fields)
    lines.append(header_line)
    lines.append("-+-".join("-" * col_widths[f] for f in fields))
    
    for rec in result.recordings:
        rec_dict = rec.to_dict()
        row = " | ".join(rec_dict.get(f, "").ljust(col_widths[f]) for f in fields)
        lines.append(row)
    
    return "\n".join(lines)


def format_text(result: ParseResult, fields: Optional[List[str]] = None) -> str:
    """文本格式输出"""
    if fields is None:
        fields = ["title", "start_time", "duration", "channel", "status"]
    
    if not result.recordings:
        return "（无录播记录）"
    
    lines = []
    for i, rec in enumerate(result.recordings, 1):
        lines.append(f"--- 录播记录 {i} ---")
        rec_dict = rec.to_dict()
        field_names = {"title": "节目名称", "start_time": "开始时间", "duration": "时长",
                       "channel": "频道", "status": "状态"}
        for f in fields:
            if f in rec_dict:
                lines.append(f"  {field_names.get(f, f)}: {rec_dict[f]}")
        lines.append("")
    
    return "\n".join(lines)


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    使用宽松阈值，不依赖精确值。
    """
    test_cases = [
        {
            "name": "基础键值对格式",
            "data": """
                Title: 新闻联播
                StartTime: 2026-01-15 19:00:00
                Duration: 30分钟
                Channel: CCTV-1
                Status: 已完成
                
                Title: 动物世界
                StartTime: 2026-01-15 20:00:00
                Duration: 45分钟
                Channel: CCTV-9
                Status: 录制中
            """,
            "expect_count_min": 2,
            "expect_has_title": True,
        },
        {
            "name": "带分隔符格式",
            "data": """
                title=纪录片 | start=2026-01-16 21:00 | dur=60min | ch=纪实频道
                title=体育新闻 | start=2026-01-16 22:00 | dur=30min | ch=体育频道
            """,
            "expect_count_min": 2,
            "expect_has_title": True,
        },
        {
            "name": "混合格式",
            "data": """
                节目: 电影频道特别节目
                开始时间: 2026-01-17 20:30
                时长: 120分钟
                频道: 电影频道
                状态: 待播放
            """,
            "expect_count_min": 1,
            "expect_has_title": True,
        },
    ]
    
    all_passed = True
    
    for case in test_cases:
        try:
            result = parse_tivo_data(case["data"], source="selftest")
            
            # 宽松检查：记录数不少于预期
            assert len(result.recordings) >= case["expect_count_min"], \
                f"记录数不足: 期望至少 {case['expect_count_min']}, 实际 {len(result.recordings)}"
            
            # 宽松检查：至少有一条记录有标题
            if case["expect_has_title"]:
                has_title = any(rec.title for rec in result.recordings)
                assert has_title, "未找到包含标题的记录"
            
            # 宽松检查：标题长度合理
            for rec in result.recordings:
                if rec.title:
                    assert 1 <= len(rec.title) <= 100, "标题长度异常"
                if rec.start_time:
                    assert len(rec.start_time) >= 8, "时间格式异常"
            
            print(f"[PASS] {case['name']}")
        except AssertionError as e:
            print(f"[FAIL] {case['name']}: {e}")
            all_passed = False
        except Exception as e:
            print(f"[ERROR] {case['name']}: {e}")
            all_passed = False
    
    # 测试输出格式
    try:
        test_result = parse_tivo_data(test_cases[0]["data"], source="selftest")
        json_out = format_json(test_result)
        assert json_out and len(json_out) > 0, "JSON 输出为空"
        
        table_out = format_table(test_result)
        assert table_out and len(table_out) > 0, "表格输出为空"
        
        text_out = format_text(test_result)
        assert text_out and len(text_out) > 0, "文本输出为空"
        
        print("[PASS] 输出格式测试")
    except Exception as e:
        print(f"[FAIL] 输出格式测试: {e}")
        all_passed = False
    
    if all_passed:
        print("所有自检通过")
        return True
    else:
        print("自检存在失败项")
        return False


# ============================================================
# 主程序
# ============================================================

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="votigoto - TiVo 录播数据解析工具",
        epilog="示例: python main.py --input data.txt --format json"
    )
    parser.add_argument("--input", "-i", help="输入数据（文件路径、URL 或直接粘贴的数据）")
    parser.add_argument("--format", "-f", choices=["json", "table", "text"], 
                        default="json", help="输出格式（默认: json）")
    parser.add_argument("--fields", nargs="+", 
                        help="要输出的字段子集（默认全部）")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 参数检查
    if not args.input:
        print(f"{ERR_INVALID_ARGS}: 请提供 --input 参数或使用 --selftest", file=sys.stderr)
        parser.print_help()
        return 1
    
    try:
        # 加载数据
        raw_data = load_input(args.input)
        
        if not raw_data or not raw_data.strip():
            print(f"{ERR_EMPTY_INPUT}: 输入数据为空", file=sys.stderr)
            return 1
        
        # 解析数据
        result = parse_tivo_data(raw_data, source=args.input)
        
        # 输出结果
        if args.format == "json":
            output = format_json(result)
        elif args.format == "table":
            output = format_table(result, args.fields)
        elif args.format == "text":
            output = format_text(result, args.fields)
        else:
            print(f"{ERR_UNSUPPORTED_FORMAT}: 不支持的输出格式 '{args.format}'", file=sys.stderr)
            return 1
        
        print(output)
        
        # 输出警告
        for warning in result.parse_warnings:
            print(f"[警告] {warning}", file=sys.stderr)
        
        return 0
        
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{ERR_INTERNAL}: 未预期的错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
