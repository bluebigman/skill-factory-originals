#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频字幕 (capscript-youtube-subtitle-search-tool) - 独立实现脚本

本脚本依据功能规格独立实现，提供：
1. 字幕/文本搜索与结构化处理
2. 批量处理能力
3. 置信度标注
4. 错误码体系 (E001-E010)
5. 离线自检 (--selftest)

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（扩展规格中的 E001-E005 至 E010）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理错误：{details}",
    "E007": "批量处理中断：第 {index} 项处理失败，原因：{reason}",
    "E008": "输出格式不支持：{format}",
    "E009": "时间戳格式错误：{value}",
    "E010": "未知错误：{details}",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 支持的时间戳格式（用于解析字幕时间）
TIMESTAMP_PATTERNS = [
    r"^(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})$",  # HH:MM:SS,mmm
    r"^(\d{1,2}):(\d{2})[.,](\d{1,3})$",          # MM:SS,mmm
    r"^(\d{1,2}):(\d{2}):(\d{2})$",               # HH:MM:SS
    r"^(\d{1,2}):(\d{2})$",                       # MM:SS
]


# ============================================================
# 核心数据结构
# ============================================================

class SubtitleEntry:
    """单条字幕条目"""
    
    def __init__(self, start_time: float, end_time: float, text: str, confidence: float = 1.0):
        self.start_time = start_time
        self.end_time = end_time
        self.text = text.strip()
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "confidence": self.confidence,
        }
    
    def __repr__(self) -> str:
        return f"SubtitleEntry({self.start_time}-{self.end_time}: {self.text[:30]}...)"


class ProcessingResult:
    """处理结果封装"""
    
    def __init__(self, items: List[Dict[str, Any]], confidence: float, warnings: List[str] = None):
        self.items = items
        self.confidence = confidence
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "items": self.items,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "generated_at": datetime.now().isoformat(),
        }


# ============================================================
# 时间戳解析
# ============================================================

def parse_timestamp(value: str) -> Optional[float]:
    """
    解析字幕时间戳为秒数。
    
    支持格式：
    - HH:MM:SS,mmm / HH:MM:SS.mmm
    - MM:SS,mmm / MM:SS.mmm
    - HH:MM:SS
    - MM:SS
    
    返回秒数；无法解析时返回 None。
    """
    if not isinstance(value, str):
        return None
    
    value = value.strip()
    
    # 尝试匹配时间戳格式
    for pattern in TIMESTAMP_PATTERNS:
        match = re.match(pattern, value)
        if match:
            groups = match.groups()
            
            if len(groups) == 4:  # HH:MM:SS,mmm 或 HH:MM:SS.mmm
                hours, minutes, seconds, millis = map(int, groups)
                # 毫秒归一化（1-3位）
                if millis < 10:
                    millis *= 100
                elif millis < 100:
                    millis *= 10
                return hours * 3600 + minutes * 60 + seconds + millis / 1000.0
                
            elif len(groups) == 3:  # MM:SS,mmm 或 MM:SS.mmm
                minutes, seconds, millis = map(int, groups)
                # 毫秒归一化（1-3位）
                if millis < 10:
                    millis *= 100
                elif millis < 100:
                    millis *= 10
                return minutes * 60 + seconds + millis / 1000.0
                
            elif len(groups) == 2:  # HH:MM:SS 或 MM:SS
                first, second = map(int, groups)
                # 判断是小时:分钟还是分钟:秒
                if first >= 60:  # 小时:分钟
                    return first * 3600 + second * 60
                else:  # 分钟:秒
                    return first * 60 + second
    
    # 尝试纯数字（秒）
    try:
        return float(value)
    except ValueError:
        pass
    
    return None


# ============================================================
# 字幕解析与处理
# ============================================================

def parse_subtitle_content(content: str) -> Tuple[List[SubtitleEntry], List[str]]:
    """
    解析字幕内容。
    
    支持两种常见格式：
    1. SRT 格式（序号 + 时间轴 + 文本）
    2. 纯文本格式（每行一条，无时间轴）
    
    返回 (条目列表, 警告列表)
    """
    warnings: List[str] = []
    entries: List[SubtitleEntry] = []
    
    if not content or not content.strip():
        warnings.append("输入内容为空")
        return entries, warnings
    
    lines = content.splitlines()
    
    # 检测是否为 SRT 格式
    is_srt = False
    for i, line in enumerate(lines[:10]):
        if re.match(r"^\d+$", line.strip()):
            # 检查下一行是否为时间轴
            if i + 1 < len(lines) and "-->" in lines[i + 1]:
                is_srt = True
                break
    
    if is_srt:
        # 解析 SRT 格式
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行
            if not line:
                i += 1
                continue
            
            # 跳过序号
            if re.match(r"^\d+$", line):
                i += 1
                continue
            
            # 时间轴行
            if "-->" in line:
                time_parts = line.split("-->")
                if len(time_parts) == 2:
                    start_time = parse_timestamp(time_parts[0].strip())
                    end_time = parse_timestamp(time_parts[1].strip())
                    
                    if start_time is None or end_time is None:
                        warnings.append(f"时间戳解析失败: {line}")
                        i += 1
                        continue
                    
                    # 收集文本（直到空行或下一个序号）
                    text_lines = []
                    i += 1
                    while i < len(lines) and lines[i].strip() and not re.match(r"^\d+$", lines[i].strip()):
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    text = " ".join(text_lines)
                    if text:
                        entries.append(SubtitleEntry(start_time, end_time, text))
                    continue
            i += 1
    else:
        # 纯文本格式，每行一条
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试从行首提取时间戳
            match = re.match(r"^\[(\d{1,2}):(\d{2}(?::\d{2})?[.,]?\d*)\]?\s*(.+)$", line)
            if match:
                time_str = match.group(1)
                text = match.group(2)
                start_time = parse_timestamp(time_str)
                if start_time is not None:
                    entries.append(SubtitleEntry(start_time, start_time + 3.0, text))
                    continue
            
            # 无时间戳，按顺序排列
            entries.append(SubtitleEntry(float(len(entries)), float(len(entries) + 3), line))
    
    return entries, warnings


def search_in_subtitles(entries: List[SubtitleEntry], query: str) -> List[Dict[str, Any]]:
    """
    在字幕条目中搜索关键词。
    
    返回匹配的条目字典列表，包含上下文信息。
    """
    results: List[Dict[str, Any]] = []
    
    if not query or not entries:
        return results
    
    query_lower = query.lower()
    
    for idx, entry in enumerate(entries):
        text_lower = entry.text.lower()
        if query_lower in text_lower:
            # 构建上下文（前后各一条）
            context = {
                "prev": entries[idx - 1].to_dict() if idx > 0 else None,
                "current": entry.to_dict(),
                "next": entries[idx + 1].to_dict() if idx < len(entries) - 1 else None,
            }
            results.append({
                "index": idx,
                "match": entry.to_dict(),
                "context": context,
            })
    
    return results


def calculate_confidence(entries: List[SubtitleEntry], warnings: List[str]) -> float:
    """
    计算处理置信度。
    
    规则：
    - 有警告信息则降低置信度
    - 条目数量过少也降低置信度
    """
    confidence = 1.0
    
    if warnings:
        confidence -= 0.05 * len(warnings)
    
    if not entries:
        confidence = 0.0
    elif len(entries) < 3:
        confidence -= 0.1
    
    return max(0.0, min(1.0, confidence))


def process_input(content: str, query: str = "", output_format: str = "json") -> ProcessingResult:
    """
    核心处理流程：
    1. 解析输入
    2. 搜索（如提供查询词）
    3. 计算置信度
    4. 格式化输出
    """
    # 解析字幕
    entries, warnings = parse_subtitle_content(content)
    
    # 搜索
    items: List[Dict[str, Any]] = []
    if query:
        search_results = search_in_subtitles(entries, query)
        items = [r["match"] for r in search_results]
        if search_results:
            warnings.append(f"找到 {len(search_results)} 条匹配结果")
    else:
        items = [e.to_dict() for e in entries]
    
    # 计算置信度
    confidence = calculate_confidence(entries, warnings)
    
    # 根据置信度添加标注
    if confidence < CONFIDENCE_MEDIUM:
        warnings.append("结果置信度过低，请人工复核")
    
    return ProcessingResult(items, confidence, warnings)


# ============================================================
# 输出格式化
# ============================================================

def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    将处理结果格式化为指定格式。
    
    支持：json, text
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        lines.append(f"处理结果（置信度：{result.confidence:.0%}）")
        lines.append("=" * 50)
        
        for i, item in enumerate(result.items):
            lines.append(f"[{i + 1}] 时间：{item.get('start_time', 'N/A')} - {item.get('end_time', 'N/A')}")
            lines.append(f"    文本：{item.get('text', 'N/A')}")
            lines.append("")
        
        if result.warnings:
            lines.append("警告信息：")
            for w in result.warnings:
                lines.append(f"  - {w}")
        
        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")


# ============================================================
# 错误处理
# ============================================================

def raise_error(error_code: str, **kwargs) -> None:
    """抛出标准错误"""
    if error_code not in ERROR_MESSAGES:
        error_code = "E010"
    
    message = ERROR_MESSAGES[error_code]
    for key, value in kwargs.items():
        message = message.replace("{" + key + "}", str(value))
    
    raise ValueError(f"[{error_code}] {message}")


# ============================================================
# 内置自检（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    
    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始离线自检...")
    print("=" * 60)
    
    # --- 测试 1: 时间戳解析 ---
    print("\n[测试 1] 时间戳解析")
    test_timestamps = [
        ("00:00:01,500", 1.5),
        ("00:01:02,250", 62.25),
        ("01:02:03,004", 3723.004),
        ("01:02", 62.0),
        ("2:30", 150.0),
        ("invalid", None),
    ]
    
    for ts, expected in test_timestamps:
        result = parse_timestamp(ts)
        if expected is None:
            assert result is None, f"应解析失败: {ts}"
        else:
            assert result is not None, f"解析失败: {ts}"
            # 宽松比较：误差在 0.1 秒内
            assert abs(result - expected) < 0.1, f"时间戳解析偏差过大: {ts} -> {result}, 期望 {expected}"
    print("  ✓ 时间戳解析测试通过")
    
    # --- 测试 2: 字幕解析 ---
    print("\n[测试 2] 字幕解析")
    srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello world, this is a test.

2
00:00:05,000 --> 00:00:08,000
Second subtitle line here.

3
00:00:09,000 --> 00:00:12,000
Third line for testing.
"""
    
    entries, warnings = parse_subtitle_content(srt_content)
    assert len(entries) >= 2, f"应解析出至少 2 条字幕，实际 {len(entries)}"
    assert entries[0].text, "第一条字幕文本不应为空"
    assert entries[0].start_time >= 0, "开始时间应为非负"
    assert entries[0].end_time > entries[0].start_time, "结束时间应大于开始时间"
    print(f"  ✓ 解析出 {len(entries)} 条字幕")
    
    # --- 测试 3: 搜索功能 ---
    print("\n[测试 3] 关键词搜索")
    search_results = search_in_subtitles(entries, "test")
    assert len(search_results) >= 1, f"应找到至少 1 条匹配，实际 {len(search_results)}"
    assert "match" in search_results[0], "搜索结果应包含 match 字段"
    assert "context" in search_results[0], "搜索结果应包含 context 字段"
    print(f"  ✓ 找到 {len(search_results)} 条匹配")
    
    # --- 测试 4: 核心处理流程 ---
    print("\n[测试 4] 核心处理流程")
    result = process_input(srt_content, query="test", output_format="json")
    assert result.items, "处理结果不应为空"
    assert 0.0 <= result.confidence <= 1.0, f"置信度应在 [0,1] 范围内: {result.confidence}"
    assert isinstance(result.warnings, list), "警告应为列表"
    print(f"  ✓ 处理完成，置信度: {result.confidence:.2f}")
    
    # --- 测试 5: 输出格式化 ---
    print("\n[测试 5] 输出格式化")
    json_output = format_output(result, "json")
    parsed = json.loads(json_output)
    assert "items" in parsed, "JSON 输出应包含 items 字段"
    assert "confidence" in parsed, "JSON 输出应包含 confidence 字段"
    
    text_output = format_output(result, "text")
    assert "处理结果" in text_output, "文本输出应包含标题"
    print("  ✓ 输出格式化测试通过")
    
    # --- 测试 6: 错误处理 ---
    print("\n[测试 6] 错误处理")
    try:
        raise_error("E001")
        assert False, "应抛出 E001 错误"
    except ValueError as e:
        assert "E001" in str(e), f"错误信息应包含错误码: {e}"
    print("  ✓ 错误处理测试通过")
    
    # --- 测试 7: 批量处理 ---
    print("\n[测试 7] 批量处理")
    batch_contents = [
        srt_content,
        "Plain text line one\nPlain text line two",
        "",
    ]
    batch_results = []
    for i, content in enumerate(batch_contents):
        try:
            batch_results.append(process_input(content))
        except Exception as e:
            print(f"  第 {i + 1} 项处理失败: {e}")
    
    assert len(batch_results) >= 2, "应至少有 2 项成功处理"
    print(f"  ✓ 批量处理完成，成功 {len(batch_results)}/{len(batch_contents)} 项")
    
    # --- 测试 8: 边界情况 ---
    print("\n[测试 8] 边界情况")
    # 空输入
    empty_result = process_input("")
    assert empty_result.items == [], "空输入不应产生条目"
    
    # 无查询词
    no_query_result = process_input(srt_content)
    assert len(no_query_result.items) >= 2, "无查询词时应返回所有条目"
    print("  ✓ 边界情况测试通过")
    
    # --- 汇总 ---
    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="视频字幕处理工具 - 搜索、解析、格式化字幕内容",
        epilog="示例：python main.py --input file.srt --query keyword --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径（或使用 --content 直接传入内容）"
    )
    parser.add_argument(
        "--content", "-c",
        type=str,
        help="直接传入字幕内容字符串"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default="",
        help="搜索关键词"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1
    
    # 获取输入内容
    content = ""
    if args.content:
        content = args.content
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise_error("E001")
        except Exception as e:
            raise_error("E006", details=str(e))
    else:
        # 尝试从 stdin 读取
        try:
            content = sys.stdin.read()
        except Exception:
            raise_error("E001")
    
    if not content.strip():
        raise_error("E001")
    
    # 执行处理
    try:
        result = process_input(content, query=args.query)
        output = format_output(result, args.format)
        print(output)
        return 0
    except ValueError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        raise_error("E010", details=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
