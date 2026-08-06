#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-reach — AI 智能体远程运维工具（Agent-Reach 生产级实现）

通过 SSH 远程管理 AI 智能体实例：启停 / 状态监控 / 白名单命令执行。
- 真实 SSH 调用（sshpass 或免密，subprocess 调系统 ssh）
- 批量操作支持并发（ThreadPoolExecutor，--concurrency 1-20）
- 网络请求超时 + 指数退避重试
- 时间统一使用 datetime.now(timezone.utc)
- 文件写入原子化（临时文件 + rename）
- selftest 真实调用主流程/核心函数并断言关键输出

用法（对齐 SKILL.md）:
    python run.py status --all
    python run.py start --tag test-env --concurrency 10
    python run.py stop --file instances.txt
    python run.py exec agent-01 log_tail -n 100
    python run.py --selftest
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".agent_reach"
CONFIG_FILE = CONFIG_DIR / "config.json"
SSH_OPTS = [
    "-o", "ConnectTimeout=10",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", "HostKeyAlgorithms=+ssh-rsa,ssh-ed25519",
]
MAX_RETRIES = 3
BASE_TIMEOUT = 30
# 白名单命令集（SKILL.md：仅限白名单命令集，杜绝任意命令）
WHITELIST = {
    "log_tail": "tail -n {n} {path}",
    "restart": "systemctl restart {service}",
    "health": "curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{port}/health",
    "down": "systemctl stop {service}",
    "uptime": "uptime",
    "df": "df -h /",
}


def load_config() -> dict:
    """读取实例配置（真实文件）。格式: {"instances": [{"name","host","user","port","key_path","tag","service"}]}"""
    if not CONFIG_FILE.exists():
        return {"instances": []}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        if not isinstance(config, dict) or "instances" not in config:
            raise ValueError("Config must be a dict with 'instances' key")
        return config
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"ERROR: Failed to load config from {CONFIG_FILE}: {e}", file=sys.stderr)
        print("Config file is corrupted or invalid. Please fix it or remove it.", file=sys.stderr)
        return {"instances": []}


def _ssh_cmd(inst: dict, remote_cmd: str, timeout: int = BASE_TIMEOUT) -> list:
    """构造 ssh 命令（真实调用系统 ssh）"""
    key = inst.get("key_path", "")
    password = inst.get("password", "")
    base = ["ssh"]
    if password:
        # 使用 sshpass 处理密码认证
        base = ["sshpass", "-p", password] + base
    if key:
        base += ["-i", key]
    base += SSH_OPTS + [
        "-p", str(inst.get("port", 22)),
        "%s@%s" % (inst.get("user", "root"), inst["host"]),
        remote_cmd,
    ]
    return base


def run_ssh(inst: dict, remote_cmd: str, timeout: int = BASE_TIMEOUT) -> dict:
    """执行 SSH 命令，带超时和指数退避重试。返回 {"ok": bool, "output": str, "error": str}"""
    cmd = _ssh_cmd(inst, remote_cmd, timeout)
    for attempt in range(MAX_RETRIES):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode == 0:
                return {"ok": True, "output": proc.stdout.strip(), "error": ""}
            # 非零退出码，收集错误信息
            error_msg = proc.stderr.strip() if proc.stderr else f"Exit code: {proc.returncode}"
            if proc.stdout:
                error_msg = f"{error_msg}\nSTDOUT: {proc.stdout.strip()[:200]}"
            return {"ok": False, "output": proc.stdout.strip(), "error": error_msg}
        except subprocess.TimeoutExpired as e:
            if attempt < MAX_RETRIES - 1:
                sleep_time = 2 ** attempt  # 指数退避: 1, 2, 4
                time.sleep(sleep_time)
                continue
            error_msg = f"SSH timeout after {MAX_RETRIES} attempts"
            if e.stdout:
                error_msg += f"\nPartial output: {e.stdout.decode('utf-8', errors='replace')[:200]}"
            return {"ok": False, "output": "", "error": error_msg}
        except FileNotFoundError:
            return {"ok": False, "output": "", "error": "ssh or sshpass not found in PATH"}
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)
                continue
            return {"ok": False, "output": "", "error": f"SSH error: {str(e)}"}
    return {"ok": False, "output": "", "error": "Unexpected error"}


def filter_instances(instances: list, name: str = None, tag: str = None, file: str = None) -> list:
    """根据 name/tag/file 筛选实例列表"""
    result = instances
    if name:
        result = [i for i in result if i.get("name") == name]
    if tag:
        result = [i for i in result if i.get("tag") == tag]
    if file:
        try:
            with open(file, "r", encoding="utf-8") as f:
                names = [line.strip() for line in f if line.strip()]
            result = [i for i in result if i.get("name") in names]
        except Exception as e:
            print(f"Error reading file {file}: {e}", file=sys.stderr)
            return []
    return result


def _build_remote_cmd(action: str, inst: dict, args) -> str:
    """根据操作类型构造远程命令"""
    if action == "start":
        service = inst.get("service", "")
        return f"systemctl start {service}"
    elif action == "stop":
        service = inst.get("service", "")
        return f"systemctl stop {service}"
    elif action == "status":
        service = inst.get("service", "")
        return f"systemctl status {service} --no-pager"
    elif action == "exec":
        cmd_template = WHITELIST.get(args.command)
        if not cmd_template:
            raise ValueError(f"Command '{args.command}' not in whitelist")
        # 构造参数映射
        params = {}
        if args.command == "log_tail":
            params = {"n": args.n, "path": args.path}
        elif args.command == "restart":
            params = {"service": args.service}
        elif args.command == "health":
            params = {"port": args.port}
        elif args.command == "down":
            params = {"service": args.service}
        return cmd_template.format(**params)
    else:
        raise ValueError(f"Unknown action: {action}")


def execute_action(action: str, instances: list, args) -> list:
    """并发执行操作，返回结果列表"""
    results = []
    # 限制并发数，防止资源耗尽
    max_workers = min(args.concurrency, 20)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_inst = {}
        for inst in instances:
            try:
                remote_cmd = _build_remote_cmd(action, inst, args)
            except ValueError as e:
                results.append({
                    "name": inst.get("name", "unknown"),
                    "action": action,
                    "ok": False,
                    "output": "",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue
            future = executor.submit(run_ssh, inst, remote_cmd, args.timeout)
            future_to_inst[future] = inst

        for future in as_completed(future_to_inst):
            inst = future_to_inst[future]
            try:
                ssh_result = future.result()
                results.append({
                    "name": inst.get("name", "unknown"),
                    "action": action,
                    "ok": ssh_result["ok"],
                    "output": ssh_result["output"],
                    "error": ssh_result["error"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                results.append({
                    "name": inst.get("name", "unknown"),
                    "action": action,
                    "ok": False,
                    "output": "",
                    "error": f"Unexpected error: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    return results


def format_results(results: list, fmt: str = "json") -> str:
    """格式化输出结果"""
    if fmt == "json":
        return json.dumps(results, indent=2, ensure_ascii=False)
    elif fmt == "markdown":
        lines = ["| 实例名 | 操作 | 状态 | 输出/错误 |", "|--------|------|------|-----------|"]
        for r in results:
            status = "✅" if r["ok"] else "❌"
            output = (r["output"] or r["error"]).replace("|", "\\|").replace("\n", " ")[:80]
            lines.append(f"| {r['name']} | {r['action']} | {status} | {output} |")
        return "\n".join(lines)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def atomic_write(path: Path, content: str) -> None:
    """原子化写入文件（临时文件 + rename）"""
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except Exception:
        os.unlink(tmp_path)
        raise


def selftest() -> int:
    """自检：真实调用核心函数并断言关键输出"""
    print("=== Agent-Reach Self-Test ===")
    failures = 0

    # 1. 测试 load_config（真实文件 + 非法 JSON）
    print("[1] Testing load_config...")
    config = load_config()
    assert isinstance(config, dict), "load_config should return dict"
    assert "instances" in config, "config should have 'instances' key"
    
    # 测试非法 JSON
    test_config_dir = Path(tempfile.mkdtemp())
    test_config_file = test_config_dir / "config.json"
    test_config_file.write_text("{invalid json", encoding="utf-8")
    old_config_file = CONFIG_FILE
    import runpy
    # 临时替换 CONFIG_FILE 路径
    globals()["CONFIG_FILE"] = test_config_file
    try:
        bad_config = load_config()
        assert bad_config == {"instances": []}, "Should return empty config for invalid JSON"
    finally:
        globals()["CONFIG_FILE"] = old_config_file
    print("    PASS")

    # 2. 测试 filter_instances（真实逻辑）
    print("[2] Testing filter_instances...")
    test_instances = [
        {"name": "agent-01", "tag": "test", "host": "localhost", "user": "root", "port": 22},
        {"name": "agent-02", "tag": "prod", "host": "localhost", "user": "root", "port": 22},
    ]
    filtered = filter_instances(test_instances, name="agent-01")
    assert len(filtered) == 1, "Should filter by name"
    assert filtered[0]["name"] == "agent-01", "Filtered name mismatch"
    filtered = filter_instances(test_instances, tag="prod")
    assert len(filtered) == 1, "Should filter by tag"
    print("    PASS")

    # 3. 测试 _build_remote_cmd（白名单命令构造 + 未授权命令拒绝）
    print("[3] Testing _build_remote_cmd...")
    class Args:
        command = "uptime"
        n = 10
        path = "/var/log/syslog"
        service = "agent"
        port = 8080
    args = Args()
    cmd = _build_remote_cmd("exec", test_instances[0], args)
    assert cmd == "uptime", f"Unexpected command: {cmd}"
    args.command = "log_tail"
    cmd = _build_remote_cmd("exec", test_instances[0], args)
    assert cmd == "tail -n 10 /var/log/syslog", f"Unexpected command: {cmd}"
    
    # 测试未授权命令
    try:
        _build_remote_cmd("exec", test_instances[0], type("A", (), {"command": "rm -rf /"})())
        assert False, "Should raise ValueError for unauthorized command"
    except ValueError:
        pass
    print("    PASS")

    # 4. 测试 format_results（真实格式化）
    print("[4] Testing format_results...")
    test_results = [
        {"name": "agent-01", "action": "status", "ok": True, "output": "active", "error": ""},
        {"name": "agent-02", "action": "status", "ok": False, "output": "", "error": "inactive"},
    ]
    json_out = format_results(test_results, "json")
    assert "agent-01" in json_out, "JSON output should contain instance name"
    md_out = format_results(test_results, "markdown")
    assert "| agent-01 |" in md_out, "Markdown output should contain table row"
    print("    PASS")

    # 5. 测试 atomic_write（真实文件写入）
    print("[5] Testing atomic_write...")
    test_file = Path(tempfile.mkdtemp()) / "test.txt"
    atomic_write(test_file, "test content")
    assert test_file.exists(), "File should exist after atomic write"
    assert test_file.read_text(encoding="utf-8") == "test content", "Content mismatch"
    print("    PASS")

    # 6. 测试 run_ssh（真实 SSH 调用，localhost 免密）
    print("[6] Testing run_ssh (localhost)...")
    local_inst = {"name": "localhost", "host": "127.0.0.1", "user": os.environ.get("USER", "root"), "port": 22}
    result = run_ssh(local_inst, "echo hello", timeout=10)
    if result["ok"]:
        assert "hello" in result["output"], f"Unexpected output: {result['output']}"
        print("    PASS")
    else:
        print(f"    SKIP (SSH not available): {result['error']}")

    # 7. 测试 execute_action（真实并发执行，localhost）
    print("[7] Testing execute_action (localhost)...")
    class Args2:
        concurrency = 2
        timeout = 10
        command = "uptime"
        n = 10
        path = "/var/log/syslog"
        service = "agent"
        port = 8080
    args2 = Args2()
    results = execute_action("exec", [local_inst], args2)
    assert len(results) == 1, "Should have 1 result"
    assert results[0]["name"] == "localhost", "Result name mismatch"
    if results[0]["ok"]:
        assert results[0]["output"], "Should have output"
        print("    PASS")
    else:
        print(f"    SKIP (SSH not available): {results[0]['error']}")

    # 8. 测试错误码路径
    print("[8] Testing error paths...")
    try:
        _build_remote_cmd("exec", test_instances[0], type("A", (), {"command": "invalid_cmd"})())
        assert False, "Should raise ValueError for invalid command"
    except ValueError:
        pass
    
    # 测试 run_ssh 错误处理
    bad_inst = {"name": "bad", "host": "nonexistent.invalid", "user": "root", "port": 22}
    result = run_ssh(bad_inst, "echo test", timeout=5)
    assert not result["ok"], "Should fail for nonexistent host"
    assert result["error"], "Should have error message"
    print("    PASS")

    print(f"\n=== Self-Test {'PASSED' if failures == 0 else f'FAILED ({failures} failures)'} ===")
    return 0 if failures == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Agent-Reach: AI智能体远程运维工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数 (1-20)")
    parser.add
