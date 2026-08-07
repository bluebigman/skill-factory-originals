#!/usr/bin/env python3
"""Main entry point for the project."""

import argparse
import sys
import os


def run_selftest() -> int:
    """Run offline self-tests."""
    print("Running self-tests...")
    
    # Test 1: Basic arithmetic
    assert 1 + 1 == 2, "Basic arithmetic failed"
    
    # Test 2: String operations
    assert "hello".upper() == "HELLO", "String operations failed"
    
    # Test 3: List operations
    test_list = [1, 2, 3]
    assert sum(test_list) == 6, "List operations failed"
    
    # Test 4: Dictionary operations
    test_dict = {"key": "value"}
    assert test_dict["key"] == "value", "Dictionary operations failed"
    
    # Test 5: File operations (offline)
    test_file = os.path.join(os.path.dirname(__file__), "test_temp.txt")
    try:
        with open(test_file, "w") as f:
            f.write("test content")
        with open(test_file, "r") as f:
            content = f.read()
        assert content == "test content", "File operations failed"
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
    
    print("All self-tests passed!")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Project main script")
    parser.add_argument("--selftest", action="store_true", help="Run self-tests")
    args = parser.parse_args()
    
    if args.selftest:
        return run_selftest()
    
    print("Hello from main script!")
    print("Use --selftest to run offline self-tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
