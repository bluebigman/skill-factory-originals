#!/usr/bin/env python3
import sys
import re
from collections import Counter

def parse_log(log_text):
    """Parse log text and return line count and level counts."""
    lines = log_text.strip().split('\n')
    # Filter out empty lines
    lines = [line for line in lines if line.strip()]
    
    level_counts = Counter()
    for line in lines:
        # Match log level patterns (case-insensitive)
        match = re.search(r'\b(ERROR|INFO|WARNING|DEBUG)\b', line, re.IGNORECASE)
        if match:
            level_counts[match.group(1).upper()] += 1
    
    return len(lines), level_counts

def main():
    # Self-test mode
    if '--selftest' in sys.argv:
        print("[RUN] Running self-test...")
        
        # Test with sample data
        sample_log = """2024-01-01 10:00:00 INFO Starting application
2024-01-01 10:00:01 ERROR Database connection failed
2024-01-01 10:00:02 INFO Retrying connection
2024-01-01 10:00:03 WARNING High memory usage
2024-01-01 10:00:04 ERROR Timeout occurred
2024-01-01 10:00:05 INFO Shutting down"""
        
        line_count, level_counts = parse_log(sample_log)
        
        # Use loose assertions (comparisons and ranges)
        assert line_count > 0, "Sample log should have lines"
        assert line_count >= 5, f"Sample log should have at least 5 lines, got {line_count}"
        assert level_counts.get('ERROR', 0) >= 1, "Should have at least 1 ERROR"
        assert level_counts.get('INFO', 0) >= 1, "Should have at least 1 INFO"
        
        # Test with empty log
        empty_count, empty_levels = parse_log("")
        assert empty_count == 0, f"Empty log should have 0 lines, got {empty_count}"
        assert len(empty_levels) == 0, "Empty log should have no levels"
        
        # Calculate percentages for sample
        total = sum(level_counts.values())
        if total > 0:
            error_pct = (level_counts.get('ERROR', 0) / total) * 100
            info_pct = (level_counts.get('INFO', 0) / total) * 100
            assert error_pct > 0, "ERROR percentage should be positive"
            assert info_pct > 0, "INFO percentage should be positive"
            assert abs(error_pct + info_pct) <= 100, "Percentages should not exceed 100"
        
        print("✓ All self-tests passed!")
        return 0
    
    # Normal mode - read from stdin
    log_text = sys.stdin.read()
    line_count, level_counts = parse_log(log_text)
    
    # Output results
    print(f"Total lines: {line_count}")
    for level in ['ERROR', 'INFO', 'WARNING', 'DEBUG']:
        count = level_counts.get(level, 0)
        if count > 0:
            print(f"{level}: {count}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
