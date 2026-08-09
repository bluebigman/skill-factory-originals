#!/usr/bin/env python3
"""冒烟测试修复脚本"""

import sys
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict


def parse_log_line(line):
    """解析日志行，返回 (timestamp, level, message) 或 None"""
    try:
        # 格式: 2024-01-01 12:00:00 INFO message
        parts = line.strip().split(' ', 3)
        if len(parts) < 4:
            return None
        
        timestamp_str = f"{parts[0]} {parts[1]}"
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        level = parts[2].upper()
        message = parts[3]
        
        return timestamp, level, message
    except (ValueError, IndexError):
        return None


def analyze_logs(log_lines, window_minutes=5):
    """分析日志，统计错误并识别模式"""
    errors = []
    error_counts = defaultdict(int)
    error_timestamps = []
    
    for line in log_lines:
        parsed = parse_log_line(line)
        if parsed:
            timestamp, level, message = parsed
            if level == 'ERROR':
                errors.append({
                    'timestamp': timestamp.isoformat(),
                    'message': message
                })
                error_counts[message] += 1
                error_timestamps.append(timestamp)
    
    # 识别错误模式（在时间窗口内重复出现）
    patterns = []
    if len(error_timestamps) > 1:
        for i in range(len(error_timestamps) - 1):
            time_diff = (error_timestamps[i + 1] - error_timestamps[i]).total_seconds() / 60
            if time_diff <= window_minutes:
                patterns.append({
                    'window_minutes': window_minutes,
                    'error_count': 2,
                    'time_between': round(time_diff, 2)
                })
    
    # 统计信息
    stats = {
        'total_lines': len(log_lines),
        'error_count': len(errors),
        'unique_errors': len(error_counts),
        'top_errors': sorted(
            [{'message': msg, 'count': cnt} for msg, cnt in error_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:5]
    }
    
    return {
        'errors': errors,
        'patterns': patterns,
        'stats': stats
    }


def main():
    parser = argparse.ArgumentParser(description='日志分析工具')
    parser.add_argument('--file', '-f', help='日志文件路径')
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    args = parser.parse_args()
    
    if args.selftest:
        # 自测数据
        test_logs = [
            "2024-01-01 10:00:00 INFO Application started",
            "2024-01-01 10:00:05 ERROR Database connection failed",
            "2024-01-01 10:00:10 WARNING Retrying connection",
            "2024-01-01 10:00:15 ERROR Database connection failed",
            "2024-01-01 10:00:20 INFO Connection established",
            "2024-01-01 10:00:25 ERROR Timeout occurred",
        ]
        
        result = analyze_logs(test_logs)
        
        # 宽松断言
        assert result['stats']['total_lines'] > 0, "总行数应大于0"
        assert result['stats']['error_count'] > 0, "错误数应大于0"
        assert len(result['errors']) > 0, "错误列表不应为空"
        assert result['stats']['unique_errors'] > 0, "唯一错误数应大于0"
        assert len(result['patterns']) > 0, "应识别出错误模式"
        
        # 验证错误消息
        error_messages = [e['message'] for e in result['errors']]
        assert any('Database' in msg for msg in error_messages), "应包含数据库错误"
        assert any('Timeout' in msg for msg in error_messages), "应包含超时错误"
        
        print("✓ 自测通过")
        print(f"  总行数: {result['stats']['total_lines']}")
        print(f"  错误数: {result['stats']['error_count']}")
        print(f"  唯一错误: {result['stats']['unique_errors']}")
        print(f"  错误模式: {len(result['patterns'])}")
        return 0
    
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            result = analyze_logs(log_lines)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        except FileNotFoundError:
            print(f"错误: 文件 '{args.file}' 不存在", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    else:
        # 从标准输入读取
        log_lines = sys.stdin.readlines()
        if log_lines:
            result = analyze_logs(log_lines)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        else:
            print("用法: python main.py [--file 日志文件] 或通过管道传入日志", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
