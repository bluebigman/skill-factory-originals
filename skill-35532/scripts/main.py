#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Analysis Tool - Main Script
Analyzes log files and provides statistics
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Regular expressions for log parsing
LOG_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)'
    r'\s+(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)'
    r'\s+(?P<message>.+)$'
)

# Sample log lines for self-test
SAMPLE_LOGS = [
    "2024-01-15 10:30:00 INFO Application started successfully",
    "2024-01-15 10:30:01 DEBUG Loading configuration file",
    "2024-01-15 10:30:02 WARNING Configuration file not found, using defaults",
    "2024-01-15 10:30:03 ERROR Failed to connect to database",
    "2024-01-15 10:30:04 CRITICAL System shutdown initiated",
    "2024-01-15 10:30:05 INFO Database connection established",
    "2024-01-15 10:30:06 DEBUG Processing request #1234",
    "2024-01-15 10:30:07 INFO Request #1234 completed in 150ms",
    "2024-01-15 10:30:08 WARNING High memory usage detected",
    "2024-01-15 10:30:09 ERROR Timeout while waiting for response",
    "2024-01-15 10:30:10 INFO Retrying connection...",
    "2024-01-15 10:30:11 DEBUG Cache hit for key 'user:123'",
    "2024-01-15 10:30:12 INFO User login successful",
    "2024-01-15 10:30:13 WARNING Multiple failed login attempts detected",
    "2024-01-15 10:30:14 ERROR Invalid credentials provided",
    "2024-01-15 10:30:15 INFO Password reset requested",
    "2024-01-15 10:30:16 DEBUG Sending email notification",
    "2024-01-15 10:30:17 INFO Email sent successfully",
    "2024-01-15 10:30:18 WARNING Disk space below 20%",
    "2024-01-15 10:30:19 ERROR Failed to write to disk",
    "2024-01-15 10:30:20 INFO Cleanup process started",
    "2024-01-15 10:30:21 DEBUG Removing temporary files",
    "2024-01-15 10:30:22 INFO Cleanup completed",
    "2024-01-15 10:30:23 WARNING CPU usage above 80%",
    "2024-01-15 10:30:24 ERROR Process killed due to OOM",
    "2024-01-15 10:30:25 INFO Restarting service...",
    "2024-01-15 10:30:26 DEBUG Loading service configuration",
    "2024-01-15 10:30:27 INFO Service restarted successfully",
    "2024-01-15 10:30:28 WARNING SSL certificate expiring soon",
    "2024-01-15 10:30:29 ERROR SSL handshake failed",
    "2024-01-15 10:30:30 INFO Using fallback connection",
    "2024-01-15 10:30:31 DEBUG Connection pool size: 10",
    "2024-01-15 10:30:32 INFO Health check passed",
    "2024-01-15 10:30:33 WARNING Response time above threshold",
    "2024-01-15 10:30:34 ERROR Request timeout after 30s",
    "2024-01-15 10:30:35 INFO Retrying with backoff...",
    "2024-01-15 10:30:36 DEBUG Backoff delay: 5s",
    "2024-01-15 10:30:37 INFO Request succeeded",
    "2024-01-15 10:30:38 WARNING Memory leak suspected",
    "2024-01-15 10:30:39 ERROR Heap dump created",
    "2024-01-15 10:30:40 INFO Heap dump analysis started",
    "2024-01-15 10:30:41 DEBUG Analyzing memory usage",
    "2024-01-15 10:30:42 INFO Memory leak fixed",
    "2024-01-15 10:30:43 WARNING Cache eviction policy changed",
    "2024-01-15 10:30:44 ERROR Cache miss rate too high",
    "2024-01-15 10:30:45 INFO Cache configuration updated",
    "2024-01-15 10:30:46 DEBUG Cache hit rate: 95%",
    "2024-01-15 10:30:47 INFO Performance optimization completed",
    "2024-01-15 10:30:48 WARNING Log rotation scheduled",
    "2024-01-15 10:30:49 ERROR Log file corrupted",
    "2024-01-15 10:30:50 INFO Log recovery process started",
    "2024-01-15 10:30:51 DEBUG Recovering log entries",
    "2024-01-15 10:30:52 INFO Log recovery completed"
]


def parse_log_line(line):
    """Parse a single log line and return a dict or None if invalid."""
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None
    
    data = match.groupdict()
    # Convert timestamp to datetime object
    try:
        timestamp_str = data['timestamp'].replace('T', ' ')
        data['timestamp'] = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None
    
    return data


def analyze_logs(log_lines):
    """Analyze log lines and return statistics."""
    stats = {
        'total_lines': 0,
        'valid_lines': 0,
        'invalid_lines': 0,
        'levels': Counter(),
        'messages': [],
        'timestamps': [],
        'hourly_distribution': Counter(),
        'error_messages': [],
        'warning_messages': [],
        'avg_response_time': 0.0,
        'response_times': [],
        'unique_errors': set(),
        'time_span_seconds': 0,
        'start_time': None,
        'end_time': None,
        'top_errors': [],
        'error_rate': 0.0
    }
    
    response_time_pattern = re.compile(r'completed in (\d+)ms')
    timeout_pattern = re.compile(r'timeout after (\d+)s')
    
    for line in log_lines:
        stats['total_lines'] += 1
        parsed = parse_log_line(line)
        
        if parsed is None:
            stats['invalid_lines'] += 1
            continue
        
        stats['valid_lines'] += 1
        level = parsed['level']
        stats['levels'][level] += 1
        stats['messages'].append(parsed['message'])
        stats['timestamps'].append(parsed['timestamp'])
        
        # Track start and end times
        if stats['start_time'] is None or parsed['timestamp'] < stats['start_time']:
            stats['start_time'] = parsed['timestamp']
        if stats['end_time'] is None or parsed['timestamp'] > stats['end_time']:
            stats['end_time'] = parsed['timestamp']
        
        # Hourly distribution
        hour_key = parsed['timestamp'].strftime('%Y-%m-%d %H:00')
        stats['hourly_distribution'][hour_key] += 1
        
        # Collect errors and warnings
        if level == 'ERROR':
            stats['error_messages'].append(parsed['message'])
            stats['unique_errors'].add(parsed['message'])
        elif level == 'WARNING':
            stats['warning_messages'].append(parsed['message'])
        
        # Extract response times
        response_match = response_time_pattern.search(parsed['message'])
        if response_match:
            response_time = int(response_match.group(1))
            stats['response_times'].append(response_time)
        
        # Extract timeout values
        timeout_match = timeout_pattern.search(parsed['message'])
        if timeout_match:
            timeout_value = int(timeout_match.group(1)) * 1000  # Convert to ms
            stats['response_times'].append(timeout_value)
    
    # Calculate derived statistics
    if stats['valid_lines'] > 0:
        stats['error_rate'] = stats['levels'].get('ERROR', 0) / stats['valid_lines']
    
    if stats['response_times']:
        stats['avg_response_time'] = sum(stats['response_times']) / len(stats['response_times'])
    
    if stats['start_time'] and stats['end_time']:
        time_diff = stats['end_time'] - stats['start_time']
        stats['time_span_seconds'] = time_diff.total_seconds()
    
    # Get top errors
    error_counter = Counter(stats['error_messages'])
    stats['top_errors'] = error_counter.most_common(5)
    
    return stats


def format_report(stats):
    """Format statistics into a readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("LOG ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append(f"Total lines processed: {stats['total_lines']}")
    lines.append(f"Valid lines: {stats['valid_lines']}")
    lines.append(f"Invalid lines: {stats['invalid_lines']}")
    lines.append("")
    lines.append("Log Levels:")
    for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        count = stats['levels'].get(level, 0)
        lines.append(f"  {level}: {count}")
    
    lines.append("")
    lines.append(f"Error rate: {stats['error_rate']:.2%}")
    
    if stats['response_times']:
        lines.append(f"Average response time: {stats['avg_response_time']:.2f} ms")
        lines.append(f"Response time samples: {len(stats['response_times'])}")
        lines.append(f"Min response time: {min(stats['response_times'])} ms")
        lines.append(f"Max response time: {max(stats['response_times'])} ms")
    
    lines.append("")
    lines.append("Hourly Distribution:")
    for hour, count in sorted(stats['hourly_distribution'].items()):
        lines.append(f"  {hour}: {count} entries")
    
    if stats['top_errors']:
        lines.append("")
        lines.append("Top Errors:")
        for error, count in stats['top_errors']:
            lines.append(f"  [{count}x] {error[:80]}")
    
    lines.append("")
    lines.append(f"Time span: {stats['time_span_seconds']:.1f} seconds")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def run_selftest():
    """Run self-test with sample data."""
    print("Running selftest...")
    
    # Use sample logs
    log_lines = SAMPLE_LOGS
    print(f"Generated {len(log_lines)} sample log lines")
    
    # Analyze the logs
    stats = analyze_logs(log_lines)
    
    # Basic assertions with relaxed thresholds
    assert stats['total_lines'] > 0, "Should have processed some lines"
    assert stats['valid_lines'] > 0, "Should have valid lines"
    assert stats['invalid_lines'] >= 0, "Invalid lines should be non-negative"
    assert stats['valid_lines'] <= stats['total_lines'], "Valid lines cannot exceed total"
    
    # Level distribution checks
    total_levels = sum(stats['levels'].values())
    assert total_levels == stats['valid_lines'], "Level counts should match valid lines"
    assert stats['levels'].get('INFO', 0) > 0, "Should have INFO logs"
    assert stats['levels'].get('ERROR', 0) > 0, "Should have ERROR logs"
    
    # Response time checks
    if stats['response_times']:
        assert stats['avg_response_time'] > 0, "Average response time should be positive"
        assert stats['avg_response_time'] < 60000, "Average response time should be reasonable"
        assert len(stats['response_times']) > 0, "Should have response time samples"
    
    # Error rate checks
    assert 0.0 <= stats['error_rate'] <= 1.0, "Error rate should be between 0 and 1"
    
    # Time span checks
    assert stats['time_span_seconds'] >= 0, "Time span should be non-negative"
    assert stats['time_span_seconds'] < 3600, "Time span should be less than an hour"
    
    # Message checks
    assert len(stats['messages']) == stats['valid_lines'], "Messages count should match valid lines"
    assert len(stats['timestamps']) == stats['valid_lines'], "Timestamps count should match valid lines"
    
    # Error message checks
    assert len(stats['error_messages']) == stats['levels'].get('ERROR', 0), "Error messages should match ERROR count"
    assert len(stats['unique_errors']) <= len(stats['error_messages']), "Unique errors cannot exceed total errors"
    
    # Top errors check
    assert len(stats['top_errors']) <= 5, "Should have at most 5 top errors"
    if stats['top_errors']:
        assert stats['top_errors'][0][1] > 0, "Top error should have positive count"
    
    # Hourly distribution checks
    assert len(stats['hourly_distribution']) > 0, "Should have hourly distribution data"
    total_hourly = sum(stats['hourly_distribution'].values())
    assert total_hourly == stats['valid_lines'], "Hourly distribution should sum to valid lines"
    
    print("All assertions passed!")
    print(f"Analysis complete: {stats['valid_lines']} valid lines, "
          f"{stats['levels'].get('ERROR', 0)} errors, "
          f"avg response time: {stats['avg_response_time']:.1f}ms")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Log Analysis Tool')
    parser.add_argument('--file', '-f', help='Path to log file to analyze')
    parser.add_argument('--selftest', action='store_true', help='Run self-test')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    if not args.file:
        print("Error: Please provide a log file path or use --selftest", file=sys.stderr)
        sys.exit(1)
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    stats = analyze_logs(log_lines)
    
    if args.json:
        # Convert sets to lists for JSON serialization
        stats['unique_errors'] = list(stats['unique_errors'])
        stats['top_errors'] = [[err, count] for err, count in stats['top_errors']]
        # Convert datetime objects to strings
        if stats['start_time']:
            stats['start_time'] = stats['start_time'].isoformat()
        if stats['end_time']:
            stats['end_time'] = stats['end_time'].isoformat()
        print(json.dumps(stats, indent=2))
    else:
        report = format_report(stats)
        print(report)


if __name__ == '__main__':
    main()
