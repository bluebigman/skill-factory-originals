#!/usr/bin/env python3
"""Main entry point for the application."""

import argparse
import json
import sys
from pathlib import Path


def run_selftest() -> int:
    """Run self-tests to verify the module works correctly."""
    tests_passed = 0
    tests_failed = 0

    # Test 1: Basic JSON serialization/deserialization
    try:
        test_data = {"key": "value", "num": 42, "list": [1, 2, 3]}
        json_str = json.dumps(test_data)
        assert json.loads(json_str) == test_data
        tests_passed += 1
    except AssertionError:
        tests_failed += 1
        print("FAIL: JSON roundtrip failed")

    # Test 2: File operations
    try:
        test_file = Path("test_tmp.txt")
        test_file.write_text("hello")
        assert test_file.read_text() == "hello"
        test_file.unlink()
        tests_passed += 1
    except Exception as e:
        tests_failed += 1
        print(f"FAIL: File operation failed: {e}")

    # Test 3: Simple arithmetic
    try:
        assert 2 + 2 == 4
        assert 10 / 2 == 5
        tests_passed += 1
    except AssertionError:
        tests_failed += 1
        print("FAIL: Arithmetic test failed")

    print(f"\nSelf-test results: {tests_passed} passed, {tests_failed} failed")
    return 1 if tests_failed > 0 else 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Application entry point")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run self-tests to verify the installation",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="1.0.0",
    )
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    # Normal operation
    print("Application started successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
