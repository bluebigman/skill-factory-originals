#!/usr/bin/env python3
"""Main entry point for the CLI application."""

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in {file_path}: {e}")
        raise


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the input data and return a result dictionary."""
    if not isinstance(data, dict):
        raise ValueError("Input data must be a dictionary")

    result = {
        "keys": list(data.keys()),
        "count": len(data),
        "string_values": [],
        "numeric_values": [],
    }

    for key, value in data.items():
        if isinstance(value, str):
            result["string_values"].append({key: value})
        elif isinstance(value, (int, float)):
            result["numeric_values"].append({key: value})
        elif isinstance(value, list):
            result["keys"].extend([f"{key}[{i}]" for i in range(len(value))])
            result["count"] += len(value)
        elif isinstance(value, dict):
            nested = process_data(value)
            result["keys"].extend([f"{key}.{k}" for k in nested["keys"]])
            result["count"] += nested["count"]

    return result


def run_selftest() -> int:
    """Run self-tests to verify the script works correctly offline."""
    logging.info("Running self-tests...")

    # Test 1: Basic data processing
    test_data = {
        "name": "test",
        "age": 30,
        "tags": ["python", "cli"],
        "metadata": {"version": "1.0", "active": True},
    }

    expected_result = {
        "keys": ["name", "age", "tags", "metadata", "tags[0]", "tags[1]", "metadata.version", "metadata.active"],
        "count": 7,
        "string_values": [{"name": "test"}, {"version": "1.0"}],
        "numeric_values": [{"age": 30}],
    }

    actual_result = process_data(test_data)
    if actual_result != expected_result:
        logging.error(f"Test 1 failed.\nExpected: {expected_result}\nGot: {actual_result}")
        return 1

    # Test 2: JSON file loading and processing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump({"a": 1, "b": "hello"}, tmp)
        tmp_path = tmp.name

    try:
        loaded_data = load_json_file(tmp_path)
        result = process_data(loaded_data)
        if result["count"] != 2 or len(result["keys"]) != 2:
            logging.error(f"Test 2 failed: Unexpected result {result}")
            return 1
    finally:
        os.unlink(tmp_path)

    # Test 3: Error handling for invalid JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp.write("{invalid json")
        tmp_path = tmp.name

    try:
        try:
            load_json_file(tmp_path)
            logging.error("Test 3 failed: Should have raised an exception")
            return 1
        except json.JSONDecodeError:
            pass  # Expected
    finally:
        os.unlink(tmp_path)

    logging.info("All self-tests passed!")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="A CLI application for processing JSON data."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to input JSON file (optional for --selftest)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Path to output JSON file (optional, defaults to stdout)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run self-tests and exit",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.selftest:
        return run_selftest()

    if not args.input:
        parser.error("Input file is required unless --selftest is used")

    try:
        data = load_json_file(args.input)
        result = process_data(data)

        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
            logging.info(f"Output written to {output_path}")
        else:
            print(output)

        return 0
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
