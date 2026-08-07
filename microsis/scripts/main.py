#!/usr/bin/env python3
"""Utility to validate and analyze JSON data structures."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def validate_json(data: Any) -> Tuple[bool, List[str]]:
    """Validate JSON structure and return (is_valid, errors)."""
    errors = []

    if data is None:
        errors.append("Root value is null")
        return False, errors

    if isinstance(data, (dict, list)):
        return True, errors

    errors.append(f"Root must be object or array, got {type(data).__name__}")
    return False, errors


def analyze_structure(data: Any, depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """Analyze JSON structure recursively."""
    if depth > max_depth:
        return {"type": "max_depth_exceeded"}

    if isinstance(data, dict):
        keys = list(data.keys())
        types = Counter()
        for value in data.values():
            types[type(value).__name__] += 1
        return {
            "type": "object",
            "key_count": len(keys),
            "keys": keys[:50],  # Limit for display
            "value_types": dict(types),
            "children": {k: analyze_structure(v, depth + 1, max_depth) for k, v in list(data.items())[:20]}
        }
    elif isinstance(data, list):
        if not data:
            return {"type": "array", "length": 0}
        element_types = Counter(type(item).__name__ for item in data)
        return {
            "type": "array",
            "length": len(data),
            "element_types": dict(element_types),
            "first_elements": data[:10]
        }
    elif isinstance(data, str):
        return {"type": "string", "length": len(data), "sample": data[:100]}
    elif isinstance(data, bool):
        return {"type": "boolean", "value": data}
    elif isinstance(data, int):
        return {"type": "integer", "value": data}
    elif isinstance(data, float):
        return {"type": "float", "value": data}
    else:
        return {"type": type(data).__name__}


def find_issues(data: Any, path: str = "$") -> List[str]:
    """Find potential issues in JSON data."""
    issues = []

    if isinstance(data, dict):
        if not data:
            issues.append(f"{path}: Empty object")
        for key, value in data.items():
            new_path = f"{path}.{key}" if path != "$" else f"$.{key}"
            issues.extend(find_issues(value, new_path))
    elif isinstance(data, list):
        if not data:
            issues.append(f"{path}: Empty array")
        for i, item in enumerate(data[:100]):  # Limit check to first 100 items
            issues.extend(find_issues(item, f"{path}[{i}]"))
    elif isinstance(data, str):
        if len(data) > 10000:
            issues.append(f"{path}: Very long string ({len(data)} chars)")
        if not data.strip():
            issues.append(f"{path}: Empty/whitespace-only string")
    elif isinstance(data, (int, float)):
        if isinstance(data, float) and data != data:  # NaN check
            issues.append(f"{path}: NaN value")
        if isinstance(data, int) and data > 10**15:
            issues.append(f"{path}: Very large integer (possible precision loss)")

    return issues


def format_analysis(data: Any) -> str:
    """Format analysis result as readable text."""
    structure = analyze_structure(data)
    issues = find_issues(data)

    lines = []
    lines.append("=== JSON Analysis Report ===")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("")

    # Root structure
    lines.append("Root Type: " + structure.get("type", "unknown"))
    if structure.get("type") == "object":
        lines.append(f"Top-level Keys ({structure.get('key_count', 0)}):")
        for key in structure.get("keys", [])[:20]:
            lines.append(f"  - {key}")
    elif structure.get("type") == "array":
        lines.append(f"Array Length: {structure.get('length', 0)}")
        if structure.get("element_types"):
            lines.append("Element Types:")
            for elem_type, count in structure.get("element_types", {}).items():
                lines.append(f"  - {elem_type}: {count}")

    # Issues
    if issues:
        lines.append("\n=== Potential Issues ===")
        for issue in issues[:50]:  # Limit display
            lines.append(f"  [!] {issue}")
    else:
        lines.append("\nNo issues found.")

    # Statistics
    lines.append("\n=== Quick Stats ===")
    if isinstance(data, dict):
        lines.append(f"Total keys (top-level): {len(data)}")
    elif isinstance(data, list):
        lines.append(f"Total items: {len(data)}")

    return "\n".join(lines)


def process_file(file_path: str) -> int:
    """Process a JSON file and return exit code."""
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            return 1

        with open(path, "r", encoding="utf-8") as f:
            raw_data = f.read()

        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {file_path}: {e}", file=sys.stderr)
            return 1

        is_valid, errors = validate_json(data)
        if not is_valid:
            print(f"Invalid JSON structure: {errors}", file=sys.stderr)
            return 1

        report = format_analysis(data)
        print(report)
        return 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return 1


def selftest() -> int:
    """Run self-tests to verify functionality."""
    test_cases = [
        (json.dumps({"name": "test", "age": 30, "tags": ["a", "b"]}), True),
        (json.dumps([1, 2, 3, {"nested": True}]), True),
        (json.dumps({"empty": {}, "arr": []}), True),
        (json.dumps("just a string"), False),  # Root must be object/array
        ("invalid json", False),  # Not valid JSON
    ]

    for i, (json_str, should_pass) in enumerate(test_cases):
        try:
            data = json.loads(json_str)
            is_valid, _ = validate_json(data)
            if is_valid != should_pass:
                print(f"Self-test {i} failed: expected valid={should_pass}, got {is_valid}")
                return 1
        except json.JSONDecodeError:
            if should_pass:
                print(f"Self-test {i} failed: expected valid JSON but got parse error")
                return 1

    # Test analysis
    test_data = {
        "users": [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": False}
        ],
        "total": 2,
        "metadata": {"version": "1.0", "generated": "2024-01-01"}
    }
    report = format_analysis(test_data)
    if "JSON Analysis Report" not in report:
        print("Self-test failed: report not generated correctly")
        return 1

    # Test issue detection
    issue_data = {"empty_str": "", "long_str": "x" * 10001}
    issues = find_issues(issue_data)
    if len(issues) < 2:
        print("Self-test failed: expected at least 2 issues")
        return 1

    print("All self-tests passed.")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate and analyze JSON data structures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python main.py file.json          # Analyze a JSON file
  python main.py --selftest         # Run self-tests
"""
    )
    parser.add_argument("file", nargs="?", help="Path to JSON file to analyze")
    parser.add_argument("--selftest", action="store_true", help="Run self-tests and exit")

    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if not args.file:
        parser.print_help()
        return 2

    return process_file(args.file)


if __name__ == "__main__":
    sys.exit(main())
