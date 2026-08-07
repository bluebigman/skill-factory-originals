#!/usr/bin/env python3
"""Main entry point with self-test capability."""

import sys
import argparse


def main(argv=None):
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Example CLI tool")
    parser.add_argument("--selftest", action="store_true", help="Run self-tests")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()
    
    print("Hello from main.py")
    return 0


def run_selftest():
    """Run self-tests and return exit code."""
    tests_passed = True
    
    # Test 1: Basic functionality
    try:
        assert 1 + 1 == 2
        print("PASS: Basic arithmetic")
    except AssertionError:
        print("FAIL: Basic arithmetic")
        tests_passed = False
    
    # Test 2: String operations
    try:
        assert "hello".upper() == "HELLO"
        print("PASS: String operations")
    except AssertionError:
        print("FAIL: String operations")
        tests_passed = False
    
    # Test 3: List operations
    try:
        test_list = [3, 1, 2]
        assert sorted(test_list) == [1, 2, 3]
        print("PASS: List operations")
    except AssertionError:
        print("FAIL: List operations")
        tests_passed = False
    
    # Test 4: Dictionary operations
    try:
        test_dict = {"key": "value"}
        assert test_dict["key"] == "value"
        print("PASS: Dictionary operations")
    except AssertionError:
        print("FAIL: Dictionary operations")
        tests_passed = False
    
    # Test 5: Function definition
    try:
        def add(a, b):
            return a + b
        assert add(2, 3) == 5
        print("PASS: Function definition")
    except AssertionError:
        print("FAIL: Function definition")
        tests_passed = False
    
    # Test 6: Exception handling
    try:
        try:
            raise ValueError("test error")
        except ValueError:
            pass
        print("PASS: Exception handling")
    except Exception:
        print("FAIL: Exception handling")
        tests_passed = False
    
    # Test 7: Import check
    try:
        import os
        import sys
        assert os.path.exists(__file__)
        print("PASS: Import check")
    except Exception:
        print("FAIL: Import check")
        tests_passed = False
    
    # Test 8: Type checking
    try:
        assert isinstance(42, int)
        assert isinstance("text", str)
        assert isinstance([], list)
        print("PASS: Type checking")
    except AssertionError:
        print("FAIL: Type checking")
        tests_passed = False
    
    # Test 9: Loop functionality
    try:
        total = sum(range(5))
        assert total == 10
        print("PASS: Loop functionality")
    except AssertionError:
        print("FAIL: Loop functionality")
        tests_passed = False
    
    # Test 10: Conditional logic
    try:
        result = "even" if 4 % 2 == 0 else "odd"
        assert result == "even"
        print("PASS: Conditional logic")
    except AssertionError:
        print("FAIL: Conditional logic")
        tests_passed = False
    
    print()
    if tests_passed:
        print("All 10 tests PASSED")
        return 0
    else:
        print("Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
