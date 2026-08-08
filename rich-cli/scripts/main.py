#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import argparse

def format_yaml(data, indent=0):
    """Convert Python data structure to YAML-like format"""
    lines = []
    prefix = " " * indent
    
    if isinstance(data, dict):
        if not data:
            lines.append(f"{prefix}{{}}")
        else:
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.extend(format_yaml(value, indent + 2))
                else:
                    lines.append(f"{prefix}{key}: {value}")
    elif isinstance(data, list):
        if not data:
            lines.append(f"{prefix}[]")
        else:
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    lines.extend(format_yaml(item, indent + 2))
                else:
                    lines.append(f"{prefix}- {item}")
    else:
        lines.append(f"{prefix}{data}")
    
    return lines

def parse_input(input_str):
    """Parse input string to Python data structure"""
    # Try JSON first
    try:
        return json.loads(input_str)
    except json.JSONDecodeError:
        pass
    
    # Fallback: try eval for simple Python literals
    try:
        return eval(input_str)
    except:
        raise ValueError(f"Unable to parse input: {input_str}")

def main():
    parser = argparse.ArgumentParser(description='Convert JSON to YAML-like format')
    parser.add_argument('input', nargs='?', help='Input JSON string')
    parser.add_argument('--selftest', action='store_true', help='Run self-tests')
    args = parser.parse_args()
    
    if args.selftest:
        # Self-tests with loose assertions
        test_cases = [
            '{"a": 1, "b": 2}',
            '[1, 2, 3]',
            '{"a": [1, 2], "b": {"c": 3}}',
            '[{"a": 1}, {"b": 2}]',
            '{"nested": {"list": [1, 2], "dict": {"x": "y"}}}'
        ]
        
        for test_input in test_cases:
            try:
                data = parse_input(test_input)
                output = format_yaml(data)
                output_str = "\n".join(output)
                
                # Loose validation: output should not be empty
                assert len(output) > 0, f"Empty output for {test_input}"
                
                # Output should contain expected structure markers
                if "{" in test_input:
                    assert ":" in output_str, f"Missing colon in output for {test_input}"
                
                if "[" in test_input:
                    assert "-" in output_str, f"Missing dash for list items in {test_input}"
                
                print(f"[PASS] {test_input}")
                print("Output:")
                print(output_str)
                print()
                
            except Exception as e:
                print(f"[FAIL] {test_input}: {str(e)}")
                return 1
        
        print("All self-tests passed!")
        return 0
    
    if not args.input:
        # Read from stdin
        input_str = sys.stdin.read().strip()
    else:
        input_str = args.input
    
    try:
        data = parse_input(input_str)
        output = format_yaml(data)
        print("\n".join(output))
        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
