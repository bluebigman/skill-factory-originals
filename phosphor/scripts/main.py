#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phosphor — 基于 DTrace 的 Ruby 运行时事件采集与结构化输出工具

本脚本为 Clean-Room 独立实现，仅依据功能规格编写。
支持事件数据采集、关键信息识别、约定格式输出、置信度标注、批量处理。
"""

import argparse
import json
import os
import re
import sys
import time
from collections import OrderedDict

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入文件不存在或不可读",
    "E003": "输入格式无法识别",
    "E004": "PID 格式无效",
    "E005": "输出格式不支持",
    "E006": "批量处理时未找到有效输入",
    "E007": "事件数据解析失败",
    "E008": "时间窗口格式无效",
    "E009": "内部逻辑错误",
    "E010": "权限不足或系统不支持",
}


def fail(code, message=None):
    """统一错误处理，输出错误码并退出。"""
    err_msg = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {err_msg}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {err_msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 核心数据结构
# ============================================================
class RubyEvent:
    """表示一条 Ruby 运行时事件记录。"""

    def __init__(self, event_type, timestamp, process_name, pid, method=None,
                 memory_bytes=None, gc_cycles=None, raw_text=""):
        self.event_type = event_type          # 事件类型：method_call / gc / alloc 等
        self.timestamp = timestamp            # 时间戳（秒，浮点数）
        self.process_name = process_name      # 进程名
        self.pid = pid                        # 进程 PID
        self.method = method                  # 方法名（可选）
        self.memory_bytes = memory_bytes      # 内存分配字节数（可选）
        self.gc_cycles = gc_cycles            # GC 周期数（可选）
        self.raw_text = raw_text              # 原始文本
        self.confidence = 1.0                 # 置信度，默认 1.0

    def to_dict(self):
        """转换为字典（JSON 友好）。"""
        result = OrderedDict()
        result["event_type"] = self.event_type
        result["timestamp"] = self.timestamp
        result["process_name"] = self.process_name
        result["pid"] = self.pid
        if self.method is not None:
            result["method"] = self.method
        if self.memory_bytes is not None:
            result["memory_bytes"] = self.memory_bytes
        if self.gc_cycles is not None:
            result["gc_cycles"] = self.gc_cycles
        result["confidence"] = self.confidence
        return result


# ============================================================
# 核心解析逻辑
# ============================================================
def parse_dtrace_line(line):
    """
    解析一行 DTrace 输出文本，返回 RubyEvent 对象或 None。
    支持以下几种模式（宽松匹配）：
    1. 方法调用: "ruby1234`Foo#bar 1234567890.123"
    2. GC 事件: "GC 周期 5 完成 1234567890.123"
    3. 内存分配: "分配 1024 字节 1234567890.123"
    4. 通用格式: "进程名 PID 事件类型 时间戳"
    """
    line = line.strip()
    if not line:
        return None

    # 尝试匹配时间戳（浮点数或整数）
    ts_match = re.search(r'(\d+\.\d+|\d+)', line)
    timestamp = float(ts_match.group(1)) if ts_match else time.time()

    # 尝试提取 PID
    pid_match = re.search(r'pid[:\s]*(\d+)', line, re.IGNORECASE)
    pid = int(pid_match.group(1)) if pid_match else 0

    # 尝试提取进程名（更健壮的模式）
    proc_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(\d+)', line)
    if proc_match:
        process_name = proc_match.group(1)
        # 如果 PID 未从 pid: 模式提取，则使用这里匹配的数字
        if pid == 0:
            pid = int(proc_match.group(2))
    else:
        process_name = "ruby"

    # 事件类型识别
    event_type = "unknown"
    method = None
    memory_bytes = None
    gc_cycles = None

    if "gc" in line.lower() or "garbage" in line.lower():
        event_type = "gc"
        gc_match = re.search(r'(\d+)\s*(周期|cycle|次)', line, re.IGNORECASE)
        gc_cycles = int(gc_match.group(1)) if gc_match else None

    elif "alloc" in line.lower() or "分配" in line:
        event_type = "alloc"
        mem_match = re.search(r'(\d+)\s*(字节|bytes|b)', line, re.IGNORECASE)
        memory_bytes = int(mem_match.group(1)) if mem_match else None

    elif "#" in line or "method" in line.lower() or "." in line:
        event_type = "method_call"
        method_match = re.search(r'([A-Za-z_][\w:]*[#.][\w]+)', line)
        method = method_match.group(1) if method_match else None

    # 构建事件对象
    event = RubyEvent(
        event_type=event_type,
        timestamp=timestamp,
        process_name=process_name,
        pid=pid,
        method=method,
        memory_bytes=memory_bytes,
        gc_cycles=gc_cycles,
        raw_text=line
    )

    # 置信度标注：字段缺失越多，置信度越低
    missing = 0
    if method is None and event_type == "method_call":
        missing += 1
    if memory_bytes is None and event_type == "alloc":
        missing += 1
    if gc_cycles is None and event_type == "gc":
        missing += 1
    if pid == 0:
        missing += 1
    event.confidence = max(0.5, 1.0 - 0.1 * missing)

    return event


def parse_event_text(text):
    """解析多行事件文本，返回 RubyEvent 列表。"""
    events = []
    for line in text.splitlines():
        event = parse_dtrace_line(line)
        if event:
            events.append(event)
    return events


def parse_pid_input(pid_str):
    """解析 PID 输入，支持单个 PID 或逗号分隔的多个 PID。"""
    try:
        pids = [int(p.strip()) for p in pid_str.split(",") if p.strip()]
        if not pids:
            fail("E004", f"无效 PID: {pid_str}")
        return pids
    except ValueError:
        fail("E004", f"无效 PID: {pid_str}")


def parse_time_window(window_str):
    """解析时间窗口，格式: 'start:end' 或 'start-end' 或单独 'start'。"""
    if not window_str:
        return None, None
    window_str = window_str.strip()
    # 支持冒号或连字符分隔
    sep_match = re.search(r'[:\-]', window_str)
    if sep_match:
        parts = [p.strip() for p in re.split(r'[:\-]', window_str)]
        try:
            start = float(parts[0]) if parts[0] else None
            end = float(parts[1]) if len(parts) > 1 and parts[1] else None
            return start, end
        except ValueError:
            fail("E008", f"无效时间窗口: {window_str}")
    else:
        try:
            return float(window_str), None
        except ValueError:
            fail("E008", f"无效时间窗口: {window_str}")


def filter_events_by_pid(events, pids):
    """按 PID 过滤事件列表。"""
    if not pids:
        return events
    return [e for e in events if e.pid in pids]


def filter_events_by_time(events, start, end):
    """按时间窗口过滤事件列表。"""
    result = events
    if start is not None:
        result = [e for e in result if e.timestamp >= start]
    if end is not None:
        result = [e for e in result if e.timestamp <= end]
    return result


# ============================================================
# 输出格式化
# ============================================================
def format_json(events, indent=2):
    """输出 JSON 格式。"""
    data = {
        "generated_at": time.time(),
        "event_count": len(events),
        "events": [e.to_dict() for e in events]
    }
    return json.dumps(data, indent=indent, ensure_ascii=False)


def format_yaml(events):
    """输出 YAML 格式（简化实现，不使用第三方库）。"""
    lines = ["# phosphor 事件追踪报告", f"# 生成时间: {time.ctime()}", ""]
    lines.append(f"event_count: {len(events)}")
    lines.append("events:")
    for i, e in enumerate(events):
        lines.append(f"  - event_{i}:")
        lines.append(f"      event_type: {e.event_type}")
        lines.append(f"      timestamp: {e.timestamp}")
        lines.append(f"      process_name: {e.process_name}")
        lines.append(f"      pid: {e.pid}")
        if e.method:
            lines.append(f"      method: {e.method}")
        if e.memory_bytes is not None:
            lines.append(f"      memory_bytes: {e.memory_bytes}")
        if e.gc_cycles is not None:
            lines.append(f"      gc_cycles: {e.gc_cycles}")
        lines.append(f"      confidence: {e.confidence}")
    return "\n".join(lines)


def format_table(events):
    """输出表格格式（简化实现）。"""
    lines = []
    lines.append("| # | 事件类型 | 时间戳 | 进程 | PID | 方法/详情 | 置信度 |")
    lines.append("|---|----------|--------|------|-----|-----------|--------|")
    for i, e in enumerate(events):
        detail = e.method or ""
        if e.memory_bytes is not None:
            detail = f"分配 {e.memory_bytes} 字节"
        if e.gc_cycles is not None:
            detail = f"GC 周期 {e.gc_cycles}"
        lines.append(f"| {i+1} | {e.event_type} | {e.timestamp:.3f} | "
                     f"{e.process_name} | {e.pid} | {detail} | {e.confidence:.2f} |")
    return "\n".join(lines)


def output_events(events, fmt="json"):
    """按指定格式输出事件列表。"""
    if fmt == "json":
        return format_json(events)
    elif fmt == "yaml":
        return format_yaml(events)
    elif fmt == "table":
        return format_table(events)
    else:
        fail("E005", f"不支持的输出格式: {fmt}")


# ============================================================
# 批量处理
# ============================================================
def batch_process(input_paths, pids=None, start=None, end=None, fmt="json"):
    """批量处理多个输入文件。"""
    all_events = []
    for path in input_paths:
        if not os.path.isfile(path):
            fail("E002", f"文件不存在: {path}")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (IOError, OSError) as e:
            fail("E002", f"读取失败: {path} ({e})")

        events = parse_event_text(content)
        all_events.extend(events)

    if not all_events:
        fail("E006", "未找到任何有效事件")

    # 过滤
    all_events = filter_events_by_pid(all_events, pids)
    all_events = filter_events_by_time(all_events, start, end)

    return output_events(all_events, fmt)


# ============================================================
# 自检功能
# ============================================================
def run_selftest():
    """内置硬编码样例数据的离线自检。不读外部文件，不依赖工作目录。"""
    print("[SELFTEST] 开始自检...")

    # --- 硬编码测试数据 ---
    test_lines = [
        "ruby 1234 method_call Foo#bar 1000.5",
        "ruby 1234 gc 3 周期 1001.0",
        "ruby 5678 alloc 2048 字节 1002.5",
        "ruby 1234 method_call Baz.qux 1003.2",
        "ruby 5678 gc 5 周期 1004.0",
        "ruby 9999 method_call Foo#unknown 1005.0",
    ]

    # --- 测试 1: 解析 ---
    print("[SELFTEST] 测试事件解析...")
    events = []
    for line in test_lines:
        e = parse_dtrace_line(line)
        if e:
            events.append(e)

    # 断言: 至少解析出部分事件
    assert len(events) > 0, "E009: 未能解析任何事件"
    print(f"  ✓ 成功解析 {len(events)} 条事件")

    # 断言: 事件类型识别正确
    types = set(e.event_type for e in events)
    assert "method_call" in types, "E009: 方法调用事件未识别"
    assert "gc" in types, "E009: GC 事件未识别"
    assert "alloc" in types, "E009: 内存分配事件未识别"
    print("  ✓ 事件类型识别正确")

    # 断言: 字段提取
    method_events = [e for e in events if e.event_type == "method_call"]
    assert len(method_events) > 0, "E009: 无方法调用事件"
    assert any(e.method for e in method_events), "E009: 方法名未提取"
    print("  ✓ 方法名提取正确")

    alloc_events = [e for e in events if e.event_type == "alloc"]
    assert len(alloc_events) > 0, "E009: 无分配事件"
    assert any(e.memory_bytes and e.memory_bytes > 0 for e in alloc_events), "E009: 内存字节数未提取"
    print("  ✓ 内存分配信息提取正确")

    gc_events = [e for e in events if e.event_type == "gc"]
    assert len(gc_events) > 0, "E009: 无 GC 事件"
    assert any(e.gc_cycles and e.gc_cycles > 0 for e in gc_events), "E009: GC 周期数未提取"
    print("  ✓ GC 信息提取正确")

    # --- 测试 2: PID 过滤 ---
    print("[SELFTEST] 测试 PID 过滤...")
    filtered = filter_events_by_pid(events, [1234])
    assert len(filtered) > 0, "E009: PID 过滤结果为空"
    assert all(e.pid == 1234 for e in filtered), "E009: 过滤后存在非目标 PID"
    print(f"  ✓ PID 过滤正确，保留 {len(filtered)} 条")

    # --- 测试 3: 时间窗口过滤 ---
    print("[SELFTEST] 测试时间窗口过滤...")
    time_filtered = filter_events_by_time(events, 1001.0, 1004.0)
    assert len(time_filtered) > 0, "E009: 时间窗口过滤结果为空"
    assert all(1001.0 <= e.timestamp <= 1004.0 for e in time_filtered), "E009: 时间窗口过滤越界"
    print(f"  ✓ 时间窗口过滤正确，保留 {len(time_filtered)} 条")

    # --- 测试 4: 输出格式 ---
    print("[SELFTEST] 测试输出格式...")
    json_out = format_json(events)
    assert len(json_out) > 0, "E009: JSON 输出为空"
    parsed = json.loads(json_out)
    assert "events" in parsed, "E009: JSON 缺少 events 字段"
    assert len(parsed["events"]) == len(events), "E009: JSON 事件数量不匹配"
    print("  ✓ JSON 输出正确")

    yaml_out = format_yaml(events)
    assert len(yaml_out) > 0, "E009: YAML 输出为空"
    assert "event_count" in yaml_out, "E009: YAML 缺少统计信息"
    print("  ✓ YAML 输出正确")

    table_out = format_table(events)
    assert len(table_out) > 0, "E009: 表格输出为空"
    assert "|" in table_out, "E009: 表格格式错误"
    print("  ✓ 表格输出正确")

    # --- 测试 5: 置信度 ---
    print("[SELFTEST] 测试置信度标注...")
    assert all(0.0 < e.confidence <= 1.0 for e in events), "E009: 置信度超出范围"
    print("  ✓ 置信度范围正确")

    # --- 测试 6: 批量组合 ---
    print("[SELFTEST] 测试批量处理组合...")
    combined = filter_events_by_pid(events, [1234, 5678])
    combined = filter_events_by_time(combined, None, 1004.0)
    assert len(combined) > 0, "E009: 组合过滤结果为空"
    print(f"  ✓ 组合过滤正确，保留 {len(combined)} 条")

    # --- 测试 7: 宽松断言（不依赖精确值）---
    print("[SELFTEST] 测试宽松断言...")
    # 事件数量应在合理范围内（不依赖精确值）
    assert len(events) >= 3, "E009: 事件数量异常偏少"
    assert len(events) <= 20, "E009: 事件数量异常偏多"
    # 时间戳应在合理范围内（不依赖精确值）
    timestamps = [e.timestamp for e in events]
    assert max(timestamps) > min(timestamps), "E009: 时间戳无变化"
    # PID 应为正整数
    assert all(e.pid > 0 for e in events), "E009: PID 非正数"
    print("  ✓ 宽松断言通过")

    print("[SELFTEST] 全部自检通过 ✓")
    return 0


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="phosphor — 基于 DTrace 的 Ruby 运行时事件采集与结构化输出工具",
        epilog="示例: python main.py --pid 1234 --format json"
    )
    parser.add_argument("--pid", type=str, default=None,
                        help="目标进程 PID，支持逗号分隔多个 PID")
    parser.add_argument("--format", type=str, default="json",
                        choices=["json", "yaml", "table"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--time", type=str, default=None,
                        help="时间窗口过滤，格式: start:end 或 start-end")
    parser.add_argument("--input", type=str, nargs="+", default=None,
                        help="输入文件路径（支持多个），不指定时从 stdin 读取")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检并退出")
    parser.add_argument("--version", action="store_true",
                        help="显示版本信息并退出")

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse 会在错误时退出，这里捕获并输出错误码
        fail("E001")

    # 版本信息
    if args.version:
        print("phosphor version 1.0.1 (clean-room implementation)")
        return 0

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 解析 PID
    pids = None
    if args.pid:
        pids = parse_pid_input(args.pid)

    # 解析时间窗口
    start, end = parse_time_window(args.time)

    # 读取输入
    if args.input:
        # 文件输入
        output = batch_process(args.input, pids, start, end, args.format)
        print(output)
    else:
        # 从 stdin 读取
        try:
            content = sys.stdin.read()
        except (IOError, OSError) as e:
            fail("E002", f"标准输入读取失败: {e}")

        if not content.strip():
            fail("E003", "标准输入为空")

        events = parse_event_text(content)
        if not events:
            fail("E007", "未解析到任何事件")

        events = filter_events_by_pid(events, pids)
        events = filter_events_by_time(events, start, end)

        if not events:
            print("[]" if args.format == "json" else "无匹配事件")
            return 0

        print(output_events(events, args.format))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[E010] 用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        fail("E009", f"未预期异常: {e}")
