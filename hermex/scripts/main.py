#!/usr/bin/env python3
"""Main entry point for the project."""

import argparse
import sys
import os

def run_selftest():
    """Run offline self-tests to verify basic functionality."""
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Basic arithmetic
    try:
        assert 2 + 2 == 4
        tests_passed += 1
    except AssertionError:
        tests_failed += 1
    
    # Test 2: String operations
    try:
        assert "hello".upper() == "HELLO"
        tests_passed += 1
    except AssertionError:
        tests_failed += 1
    
    # Test 3: List operations
    try:
        assert [1, 2, 3] == [1, 2, 3]
        tests_passed += 1
    except AssertionError:
        tests_failed += 1
    
    # Test 4: Dictionary operations
    try:
        d = {"key": "value"}
        assert d["key"] == "value"
        tests_passed += 1
    except AssertionError:
        tests_failed += 1
    
    # Test 5: File system check
    try:
        assert os.path.exists(__file__)
        tests_passed += 1
    except AssertionError:
        tests_failed += 1
    
    print(f"Self-test results: {tests_passed} passed, {tests_failed} failed")
    
    if tests_failed > 0:
        return 1
    return 0

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description="Project main script")
    parser.add_argument("--selftest", action="store_true", help="Run self-tests")
    parser.add_argument("--version", action="version", version="1.0.0")
    
    args = parser.parse_args()
    
    if args.selftest:
        return run_selftest()
    
    # Default behavior if no other arguments
    print("No command specified. Use --selftest to run tests or --help for usage.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
