#!/usr/bin/env python3
"""冒烟测试修复版"""

import sys
import json
import time
import argparse
from collections import Counter, defaultdict
from typing import List, Dict, Any


def analyze_logs(log_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析日志数据，返回统计信息"""
    if not log_data:
        return {
            "total": 0,
            "levels": {},
            "sources": {},
            "time_range": None,
            "avg_processing_time": 0,
            "error_rate": 0
        }

    total = len(log_data)
    levels = Counter()
    sources = Counter()
    timestamps = []
    processing_times = []
    errors = 0

    for entry in log_data:
        # 日志级别
        level = entry.get("level", "unknown")
        levels[level] += 1

        # 日志来源
        source = entry.get("source", "unknown")
        sources[source] += 1

        # 时间戳
        ts = entry.get("timestamp")
        if ts:
            try:
                # 尝试解析时间戳
                if isinstance(ts, (int, float)):
                    timestamps.append(float(ts))
                else:
                    # 尝试字符串时间戳
                    parsed = time.mktime(time.strptime(str(ts), "%Y-%m-%dT%H:%M:%S"))
                    timestamps.append(parsed)
            except (ValueError, TypeError):
                pass

        # 处理时间
        pt = entry.get("processing_time")
        if pt is not None:
            try:
                processing_times.append(float(pt))
            except (ValueError, TypeError):
                pass

        # 错误检测
        if level in ("ERROR", "CRITICAL") or entry.get("status") == "error":
            errors += 1

    # 时间范围
    time_range = None
    if len(timestamps) >= 2:
        time_range = {
            "start": min(timestamps),
            "end": max(timestamps),
            "duration": max(timestamps) - min(timestamps)
        }

    # 平均处理时间
    avg_processing = 0
    if processing_times:
        avg_processing = sum(processing_times) / len(processing_times)

    # 错误率
    error_rate = errors / total if total > 0 else 0

    return {
        "total": total,
        "levels": dict(levels),
        "sources": dict(sources),
        "time_range": time_range,
        "avg_processing_time": round(avg_processing, 3),
        "error_rate": round(error_rate, 3)
    }


def detect_anomalies(log_data: List[Dict[str, Any]], threshold: float = 0.1) -> List[Dict[str, Any]]:
    """检测异常日志条目"""
    anomalies = []
    if not log_data:
        return anomalies

    # 计算基准
    processing_times = []
    for entry in log_data:
        pt = entry.get("processing_time")
        if pt is not None:
            try:
                processing_times.append(float(pt))
            except (ValueError, TypeError):
                pass

    if not processing_times:
        return anomalies

    avg_time = sum(processing_times) / len(processing_times)
    max_time = max(processing_times)

    for i, entry in enumerate(log_data):
        reasons = []

        # 检查处理时间异常
        pt = entry.get("processing_time")
        if pt is not None:
            try:
                pt = float(pt)
                if pt > avg_time * 2 and pt > max_time * 0.8:
                    reasons.append("processing_time_high")
            except (ValueError, TypeError):
                pass

        # 检查错误级别
        level = entry.get("level", "")
        if level in ("ERROR", "CRITICAL"):
            reasons.append("error_level")

        # 检查状态
        if entry.get("status") == "error":
            reasons.append("error_status")

        # 检查缺失字段
        required_fields = ["timestamp", "message"]
        for field in required_fields:
            if field not in entry:
                reasons.append(f"missing_{field}")

        if reasons:
            anomalies.append({
                "index": i,
                "reasons": reasons,
                "entry": entry
            })

    return anomalies


def generate_report(log_data: List[Dict[str, Any]]) -> str:
    """生成可读报告"""
    stats = analyze_logs(log_data)
    anomalies = detect_anomalies(log_data)

    lines = []
    lines.append("=" * 60)
    lines.append("日志分析报告")
    lines.append("=" * 60)
    lines.append(f"总日志数: {stats['total']}")

    if stats['total'] > 0:
        lines.append(f"\n日志级别分布:")
        for level, count in sorted(stats['levels'].items()):
            lines.append(f"  {level}: {count} ({count/stats['total']*100:.1f}%)")

        lines.append(f"\n日志来源分布:")
        for source, count in sorted(stats['sources'].items()):
            lines.append(f"  {source}: {count}")

        if stats['time_range']:
            tr = stats['time_range']
            lines.append(f"\n时间范围: {tr['start']:.1f} - {tr['end']:.1f} (持续 {tr['duration']:.1f}s)")

        lines.append(f"平均处理时间: {stats['avg_processing_time']:.3f}s")
        lines.append(f"错误率: {stats['error_rate']*100:.1f}%")

        if anomalies:
            lines.append(f"\n检测到 {len(anomalies)} 条异常:")
            for i, anomaly in enumerate(anomalies[:10], 1):
                lines.append(f"  {i}. 索引 {anomaly['index']}: {', '.join(anomaly['reasons'])}")
            if len(anomalies) > 10:
                lines.append(f"  ... 还有 {len(anomalies)-10} 条异常")
        else:
            lines.append("\n未检测到异常")
    else:
        lines.append("无日志数据")

    lines.append("=" * 60)
    return "\n".join(lines)


def selftest():
    """自测试函数"""
    print("运行自测试...")

    # 测试数据
    test_data = [
        {
            "timestamp": "2024-01-01T10:00:00",
            "level": "INFO",
            "source": "api-server",
            "message": "Request processed",
            "processing_time": 0.05,
            "status": "success"
        },
        {
            "timestamp": "2024-01-01T10:00:01",
            "level": "ERROR",
            "source": "api-server",
            "message": "Database connection failed",
            "processing_time": 0.5,
            "status": "error"
        },
        {
            "timestamp": "2024-01-01T10:00:02",
            "level": "WARN",
            "source": "worker",
            "message": "High memory usage",
            "processing_time": 0.1,
            "status": "success"
        },
        {
            "timestamp": "2024-01-01T10:00:03",
            "level": "INFO",
            "source": "scheduler",
            "message": "Task completed",
            "processing_time": 0.02,
            "status": "success"
        }
    ]

    # 测试 analyze_logs
    stats = analyze_logs(test_data)
    assert stats["total"] == 4, f"total应为4，实际{stats['total']}"
    assert stats["levels"].get("INFO", 0) == 2, "INFO级别数量错误"
    assert stats["levels"].get("ERROR", 0) == 1, "ERROR级别数量错误"
    assert stats["error_rate"] > 0, "错误率应大于0"
    assert stats["avg_processing_time"] > 0, "平均处理时间应大于0"

    # 测试 detect_anomalies
    anomalies = detect_anomalies(test_data)
    assert len(anomalies) >= 1, "应至少检测到1条异常"
    assert any("error" in r for a in anomalies for r in a["reasons"]), "应包含错误相关异常"

    # 测试 generate_report
    report = generate_report(test_data)
    assert "日志分析报告" in report, "报告应包含标题"
    assert "总日志数" in report, "报告应包含总数"
    assert len(report) > 50, "报告长度应大于50字符"

    # 测试空数据
    empty_stats = analyze_logs([])
    assert empty_stats["total"] == 0, "空数据total应为0"
    assert empty_stats["error_rate"] == 0, "空数据错误率应为0"

    empty_anomalies = detect_anomalies([])
    assert len(empty_anomalies) == 0, "空数据应无异常"

    empty_report = generate_report([])
    assert "无日志数据" in empty_report, "空报告应提示无数据"

    print("所有自测试通过!")
    return True


def main():
    parser = argparse.ArgumentParser(description="日志分析工具")
    parser.add_argument("--selftest", action="store_true", help="运行自测试")
    parser.add_argument("--input", type=str, help="输入JSON文件路径")
    parser.add_argument("--output", type=str, help="输出报告文件路径")
    parser.add_argument("--threshold", type=float, default=0.1, help="异常检测阈值")

    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    # 读取输入
    log_data = []
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"读取输入文件失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 生成报告
    report = generate_report(log_data)

    # 输出
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
