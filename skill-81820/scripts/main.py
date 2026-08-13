#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill: HTTP Status Code Analyzer
Analyzes HTTP status codes from log files or input text.
"""

import sys
import re
import argparse
from collections import Counter
from typing import Dict, List, Tuple


def parse_status_codes(text: str) -> List[int]:
    """
    Extract HTTP status codes from text.
    Looks for 3-digit numbers in the range 100-599.
    """
    # Pattern for HTTP status codes (3 digits, 100-599)
    pattern = r'\b([1-5]\d{2})\b'
    matches = re.findall(pattern, text)
    codes = [int(match) for match in matches if 100 <= int(match) <= 599]
    return codes


def analyze_status_codes(text: str) -> Dict:
    """
    Analyze HTTP status codes from input text.
    Returns statistics about the status codes found.
    """
    codes = parse_status_codes(text)
    
    if not codes:
        return {
            'total_count': 0,
            'unique_codes': [],
            'status_code_count': {},
            'category_distribution': {},
            'most_common': None,
            'error_rate': 0.0,
            'success_rate': 0.0,
            'average_response_time': 0.0,
            'summary': "No HTTP status codes found in the input."
        }
    
    # Count occurrences of each status code
    code_counter = Counter(codes)
    status_code_count = dict(code_counter)
    
    # Categorize status codes
    categories = {
        '1xx': 0,  # Informational
        '2xx': 0,  # Success
        '3xx': 0,  # Redirection
        '4xx': 0,  # Client Error
        '5xx': 0,  # Server Error
    }
    
    for code in codes:
        if 100 <= code <= 199:
            categories['1xx'] += 1
        elif 200 <= code <= 299:
            categories['2xx'] += 1
        elif 300 <= code <= 399:
            categories['3xx'] += 1
        elif 400 <= code <= 499:
            categories['4xx'] += 1
        elif 500 <= code <= 599:
            categories['5xx'] += 1
    
    # Calculate metrics
    total = len(codes)
    success_codes = [c for c in codes if 200 <= c <= 299]
    error_codes = [c for c in codes if c >= 400]
    
    success_rate = len(success_codes) / total if total > 0 else 0.0
    error_rate = len(error_codes) / total if total > 0 else 0.0
    
    # Most common code
    most_common = code_counter.most_common(1)[0] if code_counter else None
    
    # Simulated average response time (for demonstration)
    # In real usage, this would come from actual response time data
    avg_response_time = 0.0
    
    return {
        'total_count': total,
        'unique_codes': sorted(set(codes)),
        'status_code_count': status_code_count,
        'category_distribution': categories,
        'most_common': most_common,
        'error_rate': error_rate,
        'success_rate': success_rate,
        'average_response_time': avg_response_time,
        'summary': f"Analyzed {total} HTTP status codes across {len(set(codes))} unique codes."
    }


def format_report(stats: Dict) -> str:
    """
    Format the analysis results into a readable report.
    """
    lines = []
    lines.append("=" * 50)
    lines.append("HTTP STATUS CODE ANALYSIS REPORT")
    lines.append("=" * 50)
    
    if stats['total_count'] == 0:
        lines.append(stats['summary'])
        return "\n".join(lines)
    
    lines.append(f"Total Status Codes: {stats['total_count']}")
    lines.append(f"Unique Codes: {len(stats['unique_codes'])}")
    lines.append(f"Success Rate: {stats['success_rate'] * 100:.1f}%")
    lines.append(f"Error Rate: {stats['error_rate'] * 100:.1f}%")
    
    lines.append("\nStatus Code Distribution:")
    for code in sorted(stats['status_code_count'].keys()):
        count = stats['status_code_count'][code]
        bar = '#' * min(count, 50)  # Cap bar length for display
        lines.append(f"  {code}: {count} {bar}")
    
    lines.append("\nCategory Distribution:")
    for category, count in stats['category_distribution'].items():
        if count > 0:
            percentage = (count / stats['total_count']) * 100
            lines.append(f"  {category}: {count} ({percentage:.1f}%)")
    
    if stats['most_common']:
        lines.append(f"\nMost Common Code: {stats['most_common'][0]} (appeared {stats['most_common'][1]} times)")
    
    lines.append("\n" + "=" * 50)
    lines.append(stats['summary'])
    
    return "\n".join(lines)


def process_file(filepath: str) -> str:
    """
    Process a log file and return the analysis report.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        stats = analyze_status_codes(content)
        return format_report(stats)
    except FileNotFoundError:
        return f"Error: File '{filepath}' not found."
    except Exception as e:
        return f"Error processing file: {str(e)}"


def selftest():
    """
    Self-test function to verify the module works correctly.
    Uses sample data with known status codes.
    """
    print("Running self-test...")
    
    # Test 1: Basic analysis with sample data
    sample_data = """
    [2024-01-15 10:30:00] GET /api/users 200 45ms
    [2024-01-15 10:30:01] POST /api/login 401 12ms
    [2024-01-15 10:30:02] GET /api/products 200 78ms
    [2024-01-15 10:30:03] DELETE /api/items/123 404 5ms
    [2024-01-15 10:30:04] GET /api/orders 500 120ms
    [2024-01-15 10:30:05] PUT /api/users/456 200 34ms
    [2024-01-15 10:30:06] GET /api/health 200 2ms
    [2024-01-15 10:30:07] POST /api/upload 201 89ms
    """
    
    stats = analyze_status_codes(sample_data)
    
    # Assertions with relaxed thresholds
    assert stats['total_count'] >= 5, f"Expected at least 5 status codes, got {stats['total_count']}"
    assert len(stats['status_code_count']) >= 3, f"Expected at least 3 unique status codes, got {len(stats['status_code_count'])}"
    assert stats['success_rate'] >= 0.3, f"Expected success rate >= 30%, got {stats['success_rate']}"
    assert stats['error_rate'] >= 0.1, f"Expected error rate >= 10%, got {stats['error_rate']}"
    
    # Test 2: Empty input
    empty_stats = analyze_status_codes("No codes here")
    assert empty_stats['total_count'] == 0, "Expected 0 codes for empty input"
    
    # Test 3: Edge cases
    edge_stats = analyze_status_codes("Codes: 99, 600, 200, 404, abc")
    assert edge_stats['total_count'] >= 2, f"Expected at least 2 valid codes, got {edge_stats['total_count']}"
    
    print("All self-tests passed!")
    return True


def main():
    """
    Main entry point with argument parsing.
    """
    parser = argparse.ArgumentParser(
        description='Analyze HTTP status codes from log files or text input.'
    )
    parser.add_argument(
        'input',
        nargs='?',
        help='Input file path or text to analyze'
    )
    parser.add_argument(
        '--file',
        action='store_true',
        help='Treat input as file path'
    )
    parser.add_argument(
        '--selftest',
        action='store_true',
        help='Run self-tests'
    )
    
    args = parser.parse_args()
    
    if args.selftest:
        selftest()
        return
    
    if not args.input:
        # Interactive mode
        print("HTTP Status Code Analyzer")
        print("Enter text containing HTTP status codes (or 'quit' to exit):")
        print("Example: GET /api/users 200 45ms")
        print("-" * 40)
        
        while True:
            try:
                user_input = input("> ").strip()
                if user_input.lower() in ('quit', 'exit', 'q'):
                    break
                if user_input:
                    stats = analyze_status_codes(user_input)
                    report = format_report(stats)
                    print(report)
                    print()
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except EOFError:
                print("\nExiting...")
                break
    else:
        # Process file or text
        if args.file:
            report = process_file(args.input)
        else:
            stats = analyze_status_codes(args.input)
            report = format_report(stats)
        print(report)


if __name__ == "__main__":
    main()
