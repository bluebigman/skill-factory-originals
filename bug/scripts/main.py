#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single log line into a structured format."""
    line = line.strip()
    if not line:
        return None

    # Try to parse as JSON first
    if line.startswith('{'):
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # Try common log formats
    # Format: timestamp level [module] message
    patterns = [
        # ISO timestamp with level
        r'^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+(\w+)\s+(?:\[([^\]]+)\]\s+)?(.*)$',
        # Simple timestamp with level
        r'^(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(?:\[([^\]]+)\]\s+)?(.*)$',
        # Level first
        r'^(\w+)\s+(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+(?:\[([^\]]+)\]\s+)?(.*)$',
    ]

    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            groups = match.groups()
            if len(groups) == 4:
                timestamp, level, module, message = groups
            else:
                timestamp, level, message = groups
                module = None

            return {
                'timestamp': timestamp,
                'level': level.upper(),
                'module': module,
                'message': message,
                'raw': line
            }

    # Try syslog format
    syslog_pattern = r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\w+)\[(?:(\d+))?\]:\s+(.*)$'
    match = re.match(syslog_pattern, line)
    if match:
        timestamp, host, process, pid, message = match.groups()
        return {
            'timestamp': timestamp,
            'level': 'INFO',  # syslog doesn't have levels by default
            'module': f'{process}[{pid}]' if pid else process,
            'message': message,
            'raw': line,
            'host': host
        }

    # Fallback: treat as message only
    return {
        'timestamp': None,
        'level': 'UNKNOWN',
        'module': None,
        'message': line,
        'raw': line
    }


def parse_time(timestamp: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object."""
    if not timestamp:
        return None

    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d %H:%M:%S',
        '%b %d %H:%M:%S',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue

    return None


def analyze_logs(file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze log file and return statistics."""
    results = {
        'file': file_path,
        'total_lines': 0,
        'parsed_lines': 0,
        'failed_lines': 0,
        'levels': Counter(),
        'modules': Counter(),
        'errors': [],
        'warnings': [],
        'time_range': {'start': None, 'end': None},
        'error_rate': 0.0,
        'top_errors': [],
        'top_modules': [],
        'keywords': Counter(),
        'ip_addresses': Counter(),
        'user_agents': Counter(),
        'http_codes': Counter(),
        'response_times': [],
        'summary': {}
    }

    path = Path(file_path)
    if not path.exists():
        results['error'] = f'File not found: {file_path}'
        return results

    # Read file with proper encoding
    try:
        content = path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        results['error'] = f'Failed to read file: {str(e)}'
        return results

    lines = content.splitlines()
    results['total_lines'] = len(lines)

    # Parse each line
    for line in lines:
        parsed = parse_log_line(line)
        if parsed:
            results['parsed_lines'] += 1

            # Update level counts
            level = parsed.get('level', 'UNKNOWN')
            results['levels'][level] += 1

            # Update module counts
            module = parsed.get('module')
            if module:
                results['modules'][module] += 1

            # Track time range
            timestamp = parsed.get('timestamp')
            dt = parse_time(timestamp) if timestamp else None
            if dt:
                if results['time_range']['start'] is None or dt < results['time_range']['start']:
                    results['time_range']['start'] = dt
                if results['time_range']['end'] is None or dt > results['time_range']['end']:
                    results['time_range']['end'] = dt

            # Collect errors and warnings
            message = parsed.get('message', '')
            if level in ('ERROR', 'FATAL', 'CRITICAL'):
                results['errors'].append({
                    'timestamp': timestamp,
                    'module': module,
                    'message': message[:200]
                })
                # Extract error patterns
                for pattern in ['Exception', 'Error', 'Failed', 'Timeout', 'Connection refused']:
                    if pattern.lower() in message.lower():
                        results['keywords'][pattern] += 1

            elif level == 'WARN':
                results['warnings'].append({
                    'timestamp': timestamp,
                    'module': module,
                    'message': message[:200]
                })

            # Extract IP addresses
            ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
            ips = re.findall(ip_pattern, message)
            for ip in ips:
                results['ip_addresses'][ip] += 1

            # Extract HTTP status codes
            http_pattern = r'\b(?:HTTP|Status|status)[^0-9]*(\d{3})\b'
            codes = re.findall(http_pattern, message)
            for code in codes:
                results['http_codes'][code] += 1

            # Extract response times
            time_pattern = r'(?:response|latency|duration|time)[^0-9]*(\d+(?:\.\d+)?)\s*(?:ms|s|sec|seconds)?'
            times = re.findall(time_pattern, message, re.IGNORECASE)
            for t in times:
                try:
                    results['response_times'].append(float(t))
                except ValueError:
                    pass

            # Extract user agents
            ua_pattern = r'(?:User-Agent|user_agent|user-agent)[^:]*:\s*([^\s,;]+)'
            uas = re.findall(ua_pattern, message, re.IGNORECASE)
            for ua in uas:
                results['user_agents'][ua] += 1

        else:
            results['failed_lines'] += 1

    # Calculate error rate
    if results['parsed_lines'] > 0:
        error_count = results['levels'].get('ERROR', 0) + results['levels'].get('FATAL', 0) + results['levels'].get('CRITICAL', 0)
        results['error_rate'] = error_count / results['parsed_lines']

    # Get top errors (most frequent error messages)
    error_messages = [e['message'] for e in results['errors']]
    error_counter = Counter(error_messages)
    results['top_errors'] = [{'message': msg, 'count': count} for msg, count in error_counter.most_common(10)]

    # Get top modules
    results['top_modules'] = [{'module': mod, 'count': count} for mod, count in results['modules'].most_common(10)]

    # Calculate response time statistics
    if results['response_times']:
        times = results['response_times']
        results['response_time_stats'] = {
            'count': len(times),
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'p50': sorted(times)[len(times) // 2] if times else 0,
            'p90': sorted(times)[int(len(times) * 0.9)] if times else 0,
            'p99': sorted(times)[int(len(times) * 0.99)] if times else 0
        }

    # Build summary
    results['summary'] = {
        'total_lines': results['total_lines'],
        'parsed_lines': results['parsed_lines'],
        'error_count': len(results['errors']),
        'warning_count': len(results['warnings']),
        'error_rate': f"{results['error_rate']:.2%}",
        'unique_modules': len(results['modules']),
        'time_span': str(results['time_range']['end'] - results['time_range']['start']) if results['time_range']['start'] and results['time_range']['end'] else 'N/A',
        'top_error': results['top_errors'][0] if results['top_errors'] else None
    }

    return results


def generate_report(results: Dict[str, Any], format: str = 'text') -> str:
    """Generate report in specified format."""
    if format == 'json':
        # Convert datetime objects to strings
        report = dict(results)
        if report.get('time_range'):
            report['time_range'] = {
                'start': report['time_range']['start'].isoformat() if report['time_range']['start'] else None,
                'end': report['time_range']['end'].isoformat() if report['time_range']['end'] else None
            }
        return json.dumps(report, indent=2, default=str)

    # Text format
    lines = []
    lines.append("=" * 60)
    lines.append(f"LOG ANALYSIS REPORT")
    lines.append(f"File: {results.get('file', 'N/A')}")
    lines.append("=" * 60)

    lines.append(f"\nOVERVIEW:")
    lines.append(f"  Total lines: {results.get('total_lines', 0)}")
    lines.append(f"  Parsed lines: {results.get('parsed_lines', 0)}")
    lines.append(f"  Failed lines: {results.get('failed_lines', 0)}")
    lines.append(f"  Error rate: {results.get('error_rate', 0):.2%}")

    if results.get('time_range'):
        lines.append(f"  Time range: {results['time_range'].get('start')} to {results['time_range'].get('end')}")

    lines.append(f"\nLOG LEVELS:")
    for level, count in results.get('levels', {}).most_common():
        lines.append(f"  {level}: {count}")

    lines.append(f"\nTOP MODULES:")
    for mod_info in results.get('top_modules', [])[:5]:
        lines.append(f"  {mod_info['module']}: {mod_info['count']}")

    lines.append(f"\nTOP ERRORS:")
    for err_info in results.get('top_errors', [])[:5]:
        lines.append(f"  [{err_info['count']}x] {err_info['message'][:100]}")

    if results.get('response_time_stats'):
        stats = results['response_time_stats']
        lines.append(f"\nRESPONSE TIMES (ms):")
        lines.append(f"  Count: {stats['count']}")
        lines.append(f"  Min: {stats['min']:.2f}")
        lines.append(f"  Max: {stats['max']:.2f}")
        lines.append(f"  Avg: {stats['avg']:.2f}")
        lines.append(f"  P50: {stats['p50']:.2f}")
        lines.append(f"  P90: {stats['p90']:.2f}")
        lines.append(f"  P99: {stats['p99']:.2f}")

    if results.get('ip_addresses'):
        lines.append(f"\nTOP IP ADDRESSES:")
        for ip, count in results['ip_addresses'].most_common(5):
            lines.append(f"  {ip}: {count}")

    if results.get('http_codes'):
        lines.append(f"\nHTTP STATUS CODES:")
        for code, count in results['http_codes'].most_common():
            lines.append(f"  {code}: {count}")

    if results.get('keywords'):
        lines.append(f"\nKEYWORD FREQUENCY:")
        for keyword, count in results['keywords'].most_common(10):
            lines.append(f"  {keyword}: {count}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def run_selftest() -> bool:
    """Run self-test with sample data."""
    print("Running self-test...")
    
    # Create sample log data
    sample_logs = [
        '{"timestamp": "2024-01-15T10:30:00Z", "level": "INFO", "module": "api", "message": "Request processed successfully"}',
        '{"timestamp": "2024-01-15T10:31:00Z", "level": "ERROR", "module": "database", "message": "Connection failed: timeout after 5000ms"}',
        '2024-01-15 10:32:00 ERROR [auth] Authentication failed for user admin from 192.168.1.100',
        '2024-01-15 10:33:00 WARN [cache] Cache miss for key: user_123',
        '{"timestamp": "2024-01-15T10:34:00Z", "level": "INFO", "module": "api", "message": "User-Agent: Mozilla/5.0, response time: 250ms, HTTP 200"}',
        '2024-01-15 10:35:00 ERROR [api] Internal Server Error: NullPointerException at line 42',
        '2024-01-15 10:36:00 INFO [worker] Job completed successfully in 1.5s',
        '{"timestamp": "2024-01-15T10:37:00Z", "level": "ERROR", "module": "database", "message": "Query failed: syntax error near SELECT"}',
        '2024-01-15 10:38:00 WARN [api] Rate limit exceeded for IP 10.0.0.1',
        '2024-01-15 10:39:00 INFO [worker] Processing batch of 100 items',
    ]

    # Write sample logs to temp file
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('\n'.join(sample_logs))
        temp_file = f.name

    try:
        # Analyze the sample logs
        options = {'verbose': False}
        results = analyze_logs(temp_file, options)

        # Verify results
        assert results['total_lines'] == 10, f"Expected 10 lines, got {results['total_lines']}"
        assert results['parsed_lines'] >= 8, f"Expected at least 8 parsed lines, got {results['parsed_lines']}"
        assert results['levels'].get('ERROR', 0) >= 3, f"Expected at least 3 errors, got {results['levels'].get('ERROR', 0)}"
        assert results['levels'].get('WARN', 0) >= 2, f"Expected at least 2 warnings, got {results['levels'].get('WARN', 0)}"
        assert len(results['errors']) >= 3, f"Expected at least 3 error entries, got {len(results['errors'])}"
        assert len(results['warnings']) >= 2, f"Expected at least 2 warning entries, got {len(results['warnings'])}"
        assert results['error_rate'] > 0, "Error rate should be greater than 0"
        assert len(results['top_errors']) > 0, "Should have top errors"
        assert len(results['top_modules']) > 0, "Should have top modules"
        assert results['time_range']['start'] is not None, "Should have start time"
        assert results['time_range']['end'] is not None, "Should have end time"
        assert results['time_range']['end'] > results['time_range']['start'], "End time should be after start time"
        assert len(results['ip_addresses']) > 0, "Should have IP addresses"
        assert len(results['response_times']) > 0, "Should have response times"

        # Test report generation
        text_report = generate_report(results, 'text')
        assert len(text_report) > 100, "Text report should be substantial"
        
        json_report = generate_report(results, 'json')
        json_data = json.loads(json_report)
        assert json_data['total_lines'] == 10, "JSON report should have correct total lines"

        print("Self-test passed!")
        return True

    except AssertionError as e:
        print(f"Self-test failed: {e}")
        return False
    except Exception as e:
        print(f"Self-test error: {e}")
        return False
    finally:
        # Clean up temp file
        os.unlink(temp_file)


def main():
    parser = argparse.ArgumentParser(description='Advanced Log Analyzer')
    parser.add_argument('file', nargs='?', help='Log file to analyze')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--selftest', action='store_true', help='Run self-test')
    parser.add_argument('--level', help='Filter by log level')
    parser.add_argument('--module', help='Filter by module')
    parser.add_argument('--since', help='Only analyze logs after this timestamp')
    parser.add_argument('--until', help='Only analyze logs before this timestamp')
    parser.add_argument('--top', type=int, default=10, help='Number of top items to show')

    args = parser.parse_args()

    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    if not args.file:
        parser.print_help()
        sys.exit(1)

    # Analyze the log file
    options = {
        'verbose': args.verbose,
        'level': args.level,
        'module': args.module,
        'since': args.since,
        'until': args.until,
        'top': args.top
    }

    results = analyze_logs(args.file, options)

    if 'error' in results:
        print(f"Error: {results['error']}", file=sys.stderr)
        sys.exit(1)

    # Generate and print report
    report = generate_report(results, args.format)
    print(report)


if __name__ == '__main__':
    main()
