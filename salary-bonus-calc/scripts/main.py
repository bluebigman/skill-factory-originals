#!/usr/bin/env python3
"""Simple offline selftest for main.py"""

import sys
import json
import re


def parse_config(text):
    """Parse a simple key=value config text into a dict."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        # Try to parse as JSON (number, bool, null, etc.)
        try:
            result[key] = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            result[key] = value
    return result


def generate_report(config_dict):
    """Generate a simple text report from config dict."""
    lines = []
    lines.append("Configuration Report")
    lines.append("=" * 40)
    for key in sorted(config_dict.keys()):
        lines.append(f"{key}: {config_dict[key]}")
    return "\n".join(lines)


def run_selftest():
    """Run offline self-tests, return True on success."""
    tests = []

    # Test 1: parse_config handles comments, blanks, and values
    sample = """
    # This is a comment
    server_name = myhost
    port = 8080
    debug = true

    timeout = 30.5
    """
    cfg = parse_config(sample)
    tests.append(("parse_config basic", cfg.get("server_name") == "myhost"))
    tests.append(("parse_config int", cfg.get("port") == 8080))
    tests.append(("parse_config bool", cfg.get("debug") is True))
    tests.append(("parse_config float", abs(cfg.get("timeout") - 30.5) < 1e-9))

    # Test 2: parse_config converts JSON-like values
    cfg2 = parse_config("items = [1,2,3]\nname = \"hello\"")
    tests.append(("parse_config list", cfg2.get("items") == [1, 2, 3]))
    tests.append(("parse_config quoted string", cfg2.get("name") == "hello"))

    # Test 3: generate_report produces expected output
    report = generate_report({"a": 1, "b": "x"})
    lines = report.splitlines()
    tests.append(("report header", lines[0] == "Configuration Report"))
    tests.append(("report contains a", "a: 1" in report))
    tests.append(("report contains b", "b: x" in report))
    tests.append(("report sorted", lines.index("a: 1") < lines.index("b: x")))

    # Test 4: empty input
    cfg_empty = parse_config("")
    tests.append(("empty config", len(cfg_empty) == 0))

    # Run all tests
    all_passed = True
    for name, passed in tests:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
        if not passed:
            all_passed = False

    return all_passed


def main():
    if "--selftest" in sys.argv:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # Default behavior: read stdin, parse, print report
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
    else:
        input_text = ""

    cfg = parse_config(input_text)
    print(generate_report(cfg))


if __name__ == "__main__":
    main()
