#!/usr/bin/env python3
"""Main entry point for the tool."""

import argparse
import sys
import os


def run_selftest() -> int:
    """Run self-tests to verify the module works correctly."""
    tests = [
        ("basic_add", lambda: add(2, 3) == 5),
        ("basic_subtract", lambda: subtract(5, 3) == 2),
        ("multiply", lambda: multiply(4, 3) == 12),
        ("divide", lambda: divide(10, 2) == 5),
        ("divide_by_zero", lambda: divide(1, 0) is None),
        ("string_reverse", lambda: reverse_string("hello") == "olleh"),
        ("empty_string", lambda: reverse_string("") == ""),
        ("is_palindrome_true", lambda: is_palindrome("racecar")),
        ("is_palindrome_false", lambda: not is_palindrome("hello")),
        ("factorial_zero", lambda: factorial(0) == 1),
        ("factorial_five", lambda: factorial(5) == 120),
        ("fibonacci_ten", lambda: fibonacci(10) == 55),
        ("fibonacci_zero", lambda: fibonacci(0) == 0),
        ("fibonacci_one", lambda: fibonacci(1) == 1),
    ]

    passed = 0
    failed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"  PASS: {name}")
            else:
                failed += 1
                print(f"  FAIL: {name} (returned False)")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {name} (exception: {e})")

    print(f"\nSelf-test results: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


# --- Core utility functions ---

def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float | None:
    """Divide a by b. Return None if b is zero."""
    if b == 0:
        return None
    return a / b


def reverse_string(s: str) -> str:
    """Reverse a string."""
    return s[::-1]


def is_palindrome(s: str) -> bool:
    """Check if a string is a palindrome (case-insensitive)."""
    s = s.lower()
    return s == s[::-1]


def factorial(n: int) -> int:
    """Calculate factorial of n (n >= 0)."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number (F0=0, F1=1)."""
    if n < 0:
        raise ValueError("Fibonacci is not defined for negative indices")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# --- CLI entry point ---

def main(argv=None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="A simple utility with self-test capability",
        epilog="Run with --selftest to verify the module works correctly."
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run self-tests and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )
    parser.add_argument(
        "--add",
        nargs=2,
        type=float,
        metavar=("A", "B"),
        help="Add two numbers and print the result",
    )
    parser.add_argument(
        "--reverse",
        type=str,
        metavar="STRING",
        help="Reverse a string and print the result",
    )

    args = parser.parse_args(argv)

    if args.selftest:
        print("Running self-tests...")
        return run_selftest()

    # If no operation specified, show help
    if not (args.add or args.reverse):
        parser.print_help()
        return 0

    # Perform requested operations
    if args.add:
        a, b = args.add
        print(f"{a} + {b} = {add(a, b)}")

    if args.reverse is not None:
        print(f"Reversed: {reverse_string(args.reverse)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
