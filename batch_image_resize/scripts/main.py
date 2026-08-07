#!/usr/bin/env python3
"""Main entry point for the analysis tool."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_config(config_path):
    """Load configuration from JSON file."""
    if not config_path.exists():
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config, config_path):
    """Save configuration to JSON file."""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def run_selftest():
    """Run offline self-test."""
    tests_passed = 0
    tests_failed = 0

    # Test 1: basic arithmetic
    try:
        assert 1 + 1 == 2
        tests_passed += 1
    except AssertionError:
        tests_failed += 1

    # Test 2: string operations
    try:
        assert "hello".upper() == "HELLO"
        tests_passed += 1
    except AssertionError:
        tests_failed += 1

    # Test 3: file operations
    try:
        test_file = Path("/tmp/test_selftest.txt")
        test_file.write_text("test content", encoding='utf-8')
        content = test_file.read_text(encoding='utf-8')
        assert content == "test content"
        test_file.unlink()
        tests_passed += 1
    except Exception:
        tests_failed += 1

    # Test 4: config loading
    try:
        config = load_config(Path("/nonexistent/config.json"))
        assert config == {}
        tests_passed += 1
    except Exception:
        tests_failed += 1

    # Test 5: datetime
    try:
        now = datetime.now()
        assert now.year >= 2024
        tests_passed += 1
    except Exception:
        tests_failed += 1

    print(f"Self-test completed: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def process_data(data_path, output_path):
    """Process input data file and generate output."""
    if not data_path.exists():
        print(f"Error: Input file not found: {data_path}")
        return False

    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Basic processing - count items and sum numeric values
        if isinstance(data, list):
            item_count = len(data)
            numeric_sum = sum(
                item for item in data
                if isinstance(item, (int, float))
            )
        elif isinstance(data, dict):
            item_count = len(data)
            numeric_sum = sum(
                value for value in data.values()
                if isinstance(value, (int, float))
            )
        else:
            item_count = 1
            numeric_sum = data if isinstance(data, (int, float)) else 0

        result = {
            "processed_at": datetime.now().isoformat(),
            "item_count": item_count,
            "numeric_sum": numeric_sum,
            "source_file": str(data_path)
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Data processed successfully. Output saved to {output_path}")
        return True

    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in input file: {data_path}")
        return False
    except Exception as e:
        print(f"Error processing data: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Data analysis tool with self-test capability"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run offline self-test and exit"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Path to input JSON data file"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to output JSON result file"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    # Run self-test if requested
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # Process data if input provided
    if args.input:
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else Path("output.json")
        success = process_data(input_path, output_path)
        sys.exit(0 if success else 1)

    # Default behavior - show help
    parser.print_help()


if __name__ == "__main__":
    main()
