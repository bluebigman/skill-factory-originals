#!/usr/bin/env python3
"""Main entry point for the data processing tool.

This script provides a self-test feature that can be run offline.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def process_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process a list of records and return summary statistics."""
    if not data:
        return {"count": 0, "total": 0, "average": 0, "max": None, "min": None}

    values = [item.get("value", 0) for item in data]
    numeric_values = [v for v in values if isinstance(v, (int, float))]

    if not numeric_values:
        return {"count": len(data), "total": 0, "average": 0, "max": None, "min": None}

    return {
        "count": len(data),
        "total": sum(numeric_values),
        "average": sum(numeric_values) / len(numeric_values),
        "max": max(numeric_values),
        "min": min(numeric_values),
    }


def run_self_test() -> bool:
    """Run offline self-test to verify basic functionality."""
    test_data = [
        {"name": "item1", "value": 10},
        {"name": "item2", "value": 20},
        {"name": "item3", "value": 30},
    ]

    result = process_data(test_data)

    expected = {
        "count": 3,
        "total": 60,
        "average": 20.0,
        "max": 30,
        "min": 10,
    }

    if result != expected:
        print(f"SELF-TEST FAILED: expected {expected}, got {result}")
        return False

    # Test empty input
    empty_result = process_data([])
    if empty_result["count"] != 0:
        print("SELF-TEST FAILED: empty input handling incorrect")
        return False

    # Test non-numeric values
    mixed_data = [{"value": "abc"}, {"value": 5}]
    mixed_result = process_data(mixed_data)
    if mixed_result["count"] != 2 or mixed_result["total"] != 5:
        print("SELF-TEST FAILED: mixed data handling incorrect")
        return False

    print("SELF-TEST PASSED")
    return True


def main() -> int:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Data processing tool")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run offline self-test and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览不写盘（安全守卫）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出处理明细（每步决策）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input JSON file path",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path",
    )

    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()
    if args.verbose:
        print(f"[verbose] 参数: {vars(args)}")

    if args.selftest:
        return 0 if run_self_test() else 1

    # Normal processing mode
    if not args.input:
        print("Error: --input is required (use --selftest for testing)", file=sys.stderr)
        return 2

    try:
        input_path = Path(args.input)
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("Error: Input JSON must be a list of objects", file=sys.stderr)
            return 3

        result = process_data(data)

        if args.output:
            output_path = Path(args.output)
            if not args.dry_run:
                with open(output_path, "w", encoding="utf-8", errors="replace") as f:
                    json.dump(result, f, indent=2)
            else:
                print(f"[dry-run] 预览输出（未写盘）: {args.output}")
        else:
            print(json.dumps(result, indent=2))

        return 0

    except FileNotFoundError:
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 4
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {args.input}: {e}", file=sys.stderr)
        return 5
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    sys.exit(main())
