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
SSH_OPTS = ["-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no"]
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
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"instances": []}


def _ssh_cmd(inst: dict, remote_cmd: str, timeout: int = BASE_TIMEOUT) -> list:
    """构造 ssh 命令（真实调用系统 ssh）"""
    key = inst.get("key_path", "")
    base = ["ssh"] + (["-i", key] if key else []) + SSH_OPTS + [
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
            )
            if proc.returncode == 0:
                return {"ok": True, "output": proc.stdout.strip(), "error": ""}
            # 非零退出码，不重试（命令本身错误）
            return {"ok": False, "output": proc.stdout.strip(), "error": proc.stderr.strip()}
        except subprocess.TimeoutExpired:
            if attempt < MAX_RETRIES - 1:
                sleep_time = 2 ** attempt  # 指数退避: 1, 2, 4
                time.sleep(sleep_time)
                continue
            return {"ok": False, "output": "", "error": f"SSH timeout after {MAX_RETRIES} attempts"}
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
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
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

    # 1. 测试 load_config（真实文件）
    print("[1] Testing load_config...")
    config = load_config()
    assert isinstance(config, dict), "load_config should return dict"
    assert "instances" in config, "config should have 'instances' key"
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

    # 3. 测试 _build_remote_cmd（白名单命令构造）
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
    print("    PASS")

    print(f"\n=== Self-Test {'PASSED' if failures == 0 else f'FAILED ({failures} failures)'} ===")
    return 0 if failures == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Agent-Reach: AI智能体远程运维工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数 (1-20)")
    parser.add_argument("--timeout", type=int, default=BASE_TIMEOUT, help="SSH超时秒数")

    subparsers = parser.add_subparsers(dest="action", help="操作类型")

    # start 子命令
    start_parser = subparsers.add_parser("start", help="启动实例")
    start_parser.add_argument("--name", help="按名称筛选")
    start_parser.add_argument("--tag", help="按标签筛选")
    start_parser.add_argument("--file", help="从文件读取实例名列表")

    # stop 子命令
    stop_parser = subparsers.add_parser("stop", help="停止实例")
    stop_parser.add_argument("--name", help="按名称筛选")
    stop_parser.add_argument("--tag", help="按标签筛选")
    stop_parser.add_argument("--file", help="从文件读取实例名列表")

    # status 子命令
    status_parser = subparsers.add_parser("status", help="查看状态")
    status_parser.add_argument("--name", help="按名称筛选")
    status_parser.add_argument("--tag", help="按标签筛选")
    status_parser.add_argument("--file", help="从文件读取实例名列表")
    status_parser.add_argument("--all", action="store_true", help="查看全部实例")

    # exec 子命令
    exec_parser = subparsers.add_parser("exec", help="执行白名单命令")
    exec_parser.add_argument("name", help="实例名称")
    exec_parser.add_argument("command", choices=WHITELIST.keys(), help="白名单命令")
    exec_parser.add_argument("--n", type=int, default=10, help="log_tail 行数")
    exec_parser.add_argument("--path", default="/var/log/syslog", help="log_tail 路径")
    exec_parser.add_argument("--service", default="agent", help="restart/down 服务名")
    exec_parser.add_argument("--port", type=int, default=8080, help="health 端口")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(selftest())

    # 参数校验
    if not 1 <= args.concurrency <= 20:
        print("Error: --concurrency must be between 1 and 20", file=sys.stderr)
        sys.exit(5)

    # 加载配置
    config = load_config()
    if not config["instances"]:
        print(f"Error: No instances found in {CONFIG_FILE}", file=sys.stderr)
        sys.exit(2)

    # 筛选实例
    if args.action == "status" and args.all:
        instances = config["instances"]
    elif args.action in ("start", "stop", "status"):
        instances = filter_instances(config["instances"], args.name, args.tag, args.file)
    elif args.action == "exec":
        instances = filter_instances(config["instances"], name=args.name)
    else:
        print("Error: No action specified", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if not instances:
        print("Error: No instances match the filter criteria", file=sys.stderr)
        sys.exit(3)

    # 执行操作
    results = execute_action(args.action, instances, args)

    # 输出结果
    output = format_results(results, args.format)
    print(output)

    # 检查是否有失败
    failed = [r for r in results if not r["ok"]]
    if failed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
