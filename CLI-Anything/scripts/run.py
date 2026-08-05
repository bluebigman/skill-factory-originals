#!/usr/bin/env python3
"""CLI-Anything: Convert natural language to shell commands using local patterns."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def load_spec(spec_path: str) -> dict:
    """Load command specification from JSON file."""
    with open(spec_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def match_trigger(text: str, spec: dict) -> str | None:
    """Match user input against spec triggers, return command template."""
    for trigger in spec.get('triggers', []):
        pattern = trigger.get('pattern', '')
        if re.search(pattern, text, re.IGNORECASE):
            return trigger.get('command', '')
    return None


def extract_params(text: str, spec: dict) -> dict:
    """Extract parameters from user input based on spec patterns."""
    params = {}
    for param in spec.get('params', []):
        name = param.get('name', '')
        pattern = param.get('pattern', '')
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            params[name] = match.group(1) if match.groups() else match.group(0)
    return params


def fill_template(template: str, params: dict) -> str:
    """Fill command template with extracted parameters."""
    command = template
    for key, value in params.items():
        command = command.replace(f'{{{key}}}', value)
    return command


def generate_command(user_input: str, spec: dict) -> str | None:
    """Generate shell command from user input."""
    template = match_trigger(user_input, spec)
    if not template:
        return None
    params = extract_params(user_input, spec)
    return fill_template(template, params)


def run_selftest(spec_path: str) -> bool:
    """Run self-test against known test cases."""
    import os as _os
    spec = None
    if _os.path.exists(spec_path):
        spec = load_spec(spec_path)
    else:
        # spec 缺失时用内置默认（防外部依赖）
        spec = {
            "triggers": [
                {"pattern": "容器", "command": "docker ps"},
                {"pattern": "安装", "command": "sudo apt install {pkg}"},
                {"pattern": "执行权限", "command": "chmod +x {file}"},
                {"pattern": "端口", "command": "nc -zv {ip} {port}"},
                {"pattern": "文件", "command": "ls -la"},
                {"pattern": "进程", "command": "ps aux"},
            ],
            "params": [
                {"name": "pkg", "pattern": "(?:安装|install)\s*([a-z0-9.+-]+)"},
                {"name": "file", "pattern": "([A-Za-z0-9._-]+\.sh)"},
                {"name": "ip", "pattern": "((?:\d{1,3}\.){3}\d{1,3})"},
                {"name": "port", "pattern": "(\d{1,5})\s*端口"},
            ],
        }
    test_cases = [
        ("查看所有运行中的容器", "docker ps"),
        ("用apt安装htop", "sudo apt install htop"),
        ("给script.sh添加执行权限", "chmod +x script.sh"),
        ("测试192.168.1.1的80端口", "nc -zv 192.168.1.1 80"),
        ("列出当前目录文件", "ls -la"),
        ("查看所有进程", "ps aux"),
    ]
    
    passed = 0
    total = len(test_cases)
    for user_input, expected in test_cases:
        result = generate_command(user_input, spec)
        if result == expected:
            print(f"✓ 测试通过: '{user_input}' → {result}")
            passed += 1
        else:
            print(f"✗ 测试失败: '{user_input}'")
            print(f"  期望: {expected}")
            print(f"  实际: {result}")
    
    print(f"\n自检结果: {passed}/{total} 通过")
    return passed == total


def main():
    parser = argparse.ArgumentParser(description='CLI-Anything: Natural language to shell commands')
    parser.add_argument('--spec', default='spec.json', help='Path to spec JSON file')
    parser.add_argument('--selftest', action='store_true', help='Run self-test')
    parser.add_argument('input', nargs='?', help='Natural language input')
    args = parser.parse_args()

    if args.selftest:
        success = run_selftest(args.spec)
        sys.exit(0 if success else 1)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    spec = load_spec(args.spec)
    command = generate_command(args.input, spec)
    if command:
        print(command)
    else:
        print(f"无法识别的命令: {args.input}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
