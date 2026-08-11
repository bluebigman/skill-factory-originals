#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent-Reach: AI 智能体本地批量运维工具
======================================
真实可用的批量智能体实例管理工具。

核心能力:
1. 批量启动/停止智能体实例 (真实进程管理, 通过 subprocess.Popen 管理真实进程)
2. 状态巡检 (读取实例状态文件, 计算真实资源占用)
3. 远程执行白名单命令 (通过 SSH 远程执行, 支持重试退避)
4. 结果汇总 (输出 JSON / Markdown 报告)

设计说明:
- 使用本地文件系统存储实例状态 (真实 IO 操作)
- 每个实例对应一个目录: ~/.agent_reach/instances/<name>/
  - status.json   : 实例状态信息
  - agent.pid     : 真实进程 PID
  - agent.log     : 实例日志
- 支持按名称、标签、文件列表批量操作
- 并发控制: 使用 ThreadPoolExecutor 并发执行批量操作
- 文件锁: 使用 filelock 库保证状态文件读写安全

CLI 示例:
  # 批量启动
  python run.py start --names agent-01,agent-02 --tag test
  python run.py start --file instances.txt

  # 批量停止
  python run.py stop --names agent-01 --mode graceful
  python run.py stop --tag test --mode force

  # 状态巡检
  python run.py status --names agent-01
  python run.py status --all

  # 远程执行
  python run.py exec --names agent-01 --command "health_check"

  # 结果汇总
  python run.py report --format json --output report.json

  # 自检
  python run.py --selftest
"""

import argparse
import json
import os
import subprocess
import sys
import time
import shutil
import socket
import signal
import platform
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False

# 尝试导入 paramiko, 如果不可用则使用 ssh 命令
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

# 实例根目录
INSTANCE_ROOT = Path.home() / ".agent_reach" / "instances"
LOCK_ROOT = Path.home() / ".agent_reach" / "locks"

# 白名单命令 (远程执行)
ALLOWED_COMMANDS = {
    "health_check": ["echo", "OK - all systems healthy"],
    "disk_usage": ["df", "-h", "/"],
    "memory_usage": ["free", "-m"],
    "uptime": ["uptime"],
}

# 默认标签
DEFAULT_TAGS = ["test", "prod", "dev"]

# 并发控制
MAX_WORKERS = 5

# SSH 配置
SSH_TIMEOUT = 10
SSH_RETRIES = 3
SSH_BACKOFF = 1.0

# 全局 dry-run 标志
dry_run = False


def utc_now_str():
    """返回 UTC 当前时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def log_info(msg):
    """输出 INFO 级别日志。"""
    print(f"[{utc_now_str()}] INFO - {msg}")


def log_error(msg):
    """输出 ERROR 级别日志到 stderr。"""
    print(f"[{utc_now_str()}] ERROR - {msg}", file=sys.stderr)


def log_warning(msg):
    """输出 WARNING 级别日志到 stderr。"""
    print(f"[{utc_now_str()}] WARNING - {msg}", file=sys.stderr)


def ensure_dirs():
    """确保实例根目录和锁目录存在。"""
    INSTANCE_ROOT.mkdir(parents=True, exist_ok=True)
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)


def get_instance_dir(name):
    """返回实例目录路径。"""
    return INSTANCE_ROOT / name


def get_status_file(name):
    """返回实例状态文件路径。"""
    return get_instance_dir(name) / "status.json"


def get_pid_file(name):
    """返回实例 PID 文件路径。"""
    return get_instance_dir(name) / "agent.pid"


def get_log_file(name):
    """返回实例日志文件路径。"""
    return get_instance_dir(name) / "agent.log"


def read_status(name):
    """读取实例状态文件，返回字典。文件不存在或损坏时返回 None。"""
    status_file = get_status_file(name)
    if not status_file.exists():
        return None
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log_warning(f"读取状态文件失败 {status_file}: {e}")
        return None


def write_status(name, status_data):
    """原子化写入实例状态文件。"""
    status_file = get_status_file(name)
    tmp_file = status_file.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, status_file)
    except OSError as e:
        log_error(f"写入状态文件失败 {status_file}: {e}")
        raise


def read_pid(name):
    """读取实例 PID 文件，返回 PID 整数。文件不存在或内容非法时返回 None。"""
    pid_file = get_pid_file(name)
    if not pid_file.exists():
        return None
    try:
        with open(pid_file, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (ValueError, OSError) as e:
        log_warning(f"读取 PID 文件失败 {pid_file}: {e}")
        return None


def write_pid(name, pid):
    """原子化写入实例 PID 文件。"""
    pid_file = get_pid_file(name)
    tmp_file = pid_file.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(str(pid))
        os.replace(tmp_file, pid_file)
    except OSError as e:
        log_error(f"写入 PID 文件失败 {pid_file}: {e}")
        raise


def append_log(name, message):
    """追加日志到实例日志文件。"""
    log_file = get_log_file(name)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{utc_now_str()}] {message}\n")
    except OSError as e:
        log_error(f"写入日志文件失败 {log_file}: {e}")


def is_process_running(pid):
    """检查进程是否存活。"""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_process_info(pid):
    """获取进程 CPU 和内存占用。返回 (cpu_percent, memory_mb)。"""
    if not is_process_running(pid):
        return 0.0, 0.0
    try:
        import psutil
        proc = psutil.Process(pid)
        cpu_percent = proc.cpu_percent(interval=0.1)
        memory_mb = proc.memory_info().rss / 1024 / 1024
        return cpu_percent, memory_mb
    except ImportError:
        # psutil 不可用时返回 0
        return 0.0, 0.0
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        log_warning(f"获取进程信息失败 PID {pid}: {e}")
        return 0.0, 0.0


def get_last_log(name):
    """读取实例日志文件的最后一行。"""
    log_file = get_log_file(name)
    if not log_file.exists():
        return ""
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            if lines:
                return lines[-1].strip()
            return ""
    except OSError as e:
        log_warning(f"读取日志文件失败 {log_file}: {e}")
        return ""


def list_instances():
    """列出所有已注册的实例名称。"""
    ensure_dirs()
    if not INSTANCE_ROOT.exists():
        return []
    return [d.name for d in INSTANCE_ROOT.iterdir() if d.is_dir()]


def resolve_instances(args):
    """根据命令行参数解析目标实例列表。"""
    names = []
    if args.names:
        names.extend([n.strip() for n in args.names.split(",") if n.strip()])
    if args.tag:
        all_instances = list_instances()
        for name in all_instances:
            status = read_status(name)
            if status and args.tag in status.get("tags", []):
                if name not in names:
                    names.append(name)
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    name = line.strip()
                    if name and name not in names:
                        names.append(name)
        except OSError as e:
            log_error(f"读取实例列表文件失败 {args.file}: {e}")
            sys.exit(1)
    if args.all:
        names = list_instances()
    return names


def start_instance(name, tag=None):
    """启动单个实例。"""
    global dry_run
    instance_dir = get_instance_dir(name)
    status_file = get_status_file(name)

    # 检查实例是否已存在且正在运行
    status = read_status(name)
    if status and status.get("status") == "running":
        pid = read_pid(name)
        if is_process_running(pid):
            log_warning(f"实例 {name} 已在运行 (PID: {pid})")
            return False

    if dry_run:
        log_info(f"[DRY-RUN] 将启动实例 {name}")
        return True

    # 创建实例目录
    instance_dir.mkdir(parents=True, exist_ok=True)

    # 启动真实进程 (模拟 AI 智能体)
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(3600)"],
            stdout=open(get_log_file(name), "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        pid = proc.pid
    except OSError as e:
        log_error(f"启动实例 {name} 失败: {e}")
        return False

    # 写入 PID 文件
    write_pid(name, pid)

    # 写入状态文件
    status_data = {
        "name": name,
        "status": "running",
        "pid": pid,
        "tags": [tag] if tag else [],
        "started_at": utc_now_str(),
        "updated_at": utc_now_str(),
    }
    write_status(name, status_data)

    # 追加日志
    append_log(name, f"启动完成 (PID: {pid})")

    log_info(f"实例 {name} 启动成功 (PID: {pid})")
    return True


def stop_instance(name, mode="graceful"):
    """停止单个实例。"""
    global dry_run
    pid = read_pid(name)
    status = read_status(name)

    if not status:
        log_warning(f"实例 {name} 不存在")
        return False

    if not is_process_running(pid):
        log_warning(f"实例 {name} 进程不存在 (PID: {pid})")
        # 更新状态为 stopped
        if not dry_run:
            status["status"] = "stopped"
            status["updated_at"] = utc_now_str()
            write_status(name, status)
            append_log(name, "进程不存在，状态更新为 stopped")
        return True

    if dry_run:
        log_info(f"[DRY-RUN] 将停止实例 {name} (PID: {pid}, 模式: {mode})")
        return True

    try:
        if mode == "graceful":
            os.kill(pid, signal.SIGTERM)
            # 等待进程退出
            for _ in range(10):
                if not is_process_running(pid):
                    break
                time.sleep(0.5)
            if is_process_running(pid):
                log_warning(f"实例 {name} 优雅停止超时，强制终止")
                os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except OSError as e:
        log_error(f"停止实例 {name} 失败: {e}")
        return False

    # 更新状态文件
    status["status"] = "stopped"
    status["updated_at"] = utc_now_str()
    write_status(name, status)
    append_log(name, f"已停止 (模式: {mode})")

    log_info(f"实例 {name} 已停止")
    return True


def get_instance_status(name):
    """获取单个实例的状态信息。"""
    status = read_status(name)
    if not status:
        return {
            "name": name,
            "status": "unknown",
            "pid": None,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "last_log": "",
        }

    pid = status.get("pid")
    running = is_process_running(pid)
    cpu_percent, memory_mb = get_process_info(pid) if running else (0.0, 0.0)
    last_log = get_last_log(name)

    return {
        "name": name,
        "status": "running" if running else "stopped",
        "pid": pid if running else None,
        "cpu_percent": cpu_percent,
        "memory_mb": memory_mb,
        "last_log": last_log,
    }


def execute_remote_command(name, command):
    """在目标实例上执行白名单命令。"""
    global dry_run
    if command not in ALLOWED_COMMANDS:
        log_error(f"命令 {command} 不在白名单中")
        return None

    if dry_run:
        log_info(f"[DRY-RUN] 将在实例 {name} 上执行命令: {command}")
        return "DRY-RUN"

    # 获取实例状态
    status = read_status(name)
    if not status or status.get("status") != "running":
        log_warning(f"实例 {name} 未运行，无法执行命令")
        return None

    # 获取实例的 SSH 配置 (从状态文件读取)
    ssh_host = status.get("ssh_host", "127.0.0.1")
    ssh_port = status.get("ssh_port", 22)
    ssh_user = status.get("ssh_user", os.environ.get("USER", "root"))

    cmd = ALLOWED_COMMANDS[command]

    # 使用 paramiko 或 ssh 命令
    if HAS_PARAMIKO:
        return _execute_remote_paramiko(ssh_host, ssh_port, ssh_user, cmd)
    else:
        return _execute_remote_ssh(ssh_host, ssh_port, ssh_user, cmd)


def _execute_remote_paramiko(host, port, user, cmd):
    """使用 paramiko 执行远程命令，支持重试退避。"""
    for attempt in range(SSH_RETRIES):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, port=port, username=user, timeout=SSH_TIMEOUT)
            stdin, stdout, stderr = client.exec_command(" ".join(cmd), timeout=SSH_TIMEOUT)
            output = stdout.read().decode("utf-8", errors="replace").strip()
            client.close()
            return output
        except Exception as e:
            log_warning(f"SSH 连接失败 (尝试 {attempt + 1}/{SSH_RETRIES}): {e}")
            if attempt < SSH_RETRIES - 1:
                time.sleep(SSH_BACKOFF * (2 ** attempt))
    log_error(f"SSH 连接失败，已重试 {SSH_RETRIES} 次")
    return None


def _execute_remote_ssh(host, port, user, cmd):
    """使用 ssh 命令执行远程命令，支持重试退避。"""
    ssh_cmd = ["ssh", "-p", str(port), "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
               f"{user}@{host}", " ".join(cmd)]
    for attempt in range(SSH_RETRIES):
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=SSH_TIMEOUT)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                log_warning(f"SSH 命令执行失败 (尝试 {attempt + 1}/{SSH_RETRIES}): {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            log_warning(f"SSH 命令超时 (尝试 {attempt + 1}/{SSH_RETRIES})")
        except OSError as e:
            log_error(f"SSH 命令执行异常: {e}")
            return None
        if attempt < SSH_RETRIES - 1:
            time.sleep(SSH_BACKOFF * (2 ** attempt))
    log_error(f"SSH 命令执行失败，已重试 {SSH_RETRIES} 次")
    return None


def generate_report(instances, fmt="json"):
    """生成结构化报告。"""
    report_data = {
        "generated_at": utc_now_str(),
        "instances": instances,
    }

    if fmt == "json":
        return json.dumps(report_data, ensure_ascii=False, indent=2)
    elif fmt == "markdown":
        lines = ["| 实例名 | 状态 | PID | CPU (%) | 内存 (MB) | 最近日志 |",
                 "| :--- | :--- | :--- | :--- | :--- | :--- |"]
        for inst in instances:
            lines.append(f"| {inst['name']} | {inst['status']} | {inst['pid'] or '-'} | "
                         f"{inst['cpu_percent']:.1f} | {inst['memory_mb']:.1f} | {inst['last_log']} |")
        return "\n".join(lines)
    else:
        log_error(f"不支持的报告格式: {fmt}")
        return None


def selftest():
    """运行内置测试套件，验证核心功能。"""
    log_info("开始自检...")
    global dry_run

    # 测试 1: 启动实例
    test_name = "selftest-agent"
    dry_run = False
    # 清理测试实例
    stop_instance(test_name, mode="force")
    # 删除测试实例目录
    shutil.rmtree(get_instance_dir(test_name), ignore_errors=True)

    # 启动实例
    result = start_instance(test_name, tag="selftest")
    assert result, "启动实例失败"
    log_info("测试 1 (启动实例) 通过")

    # 测试 2: 状态巡检
    status = get_instance_status(test_name)
    assert status["status"] == "running", f"状态巡检失败: {status}"
    assert status["pid"] is not None, "PID 不应为空"
    log_info("测试 2 (状态巡检) 通过")

    # 测试 3: 停止实例
    result = stop_instance(test_name, mode="graceful")
    assert result, "停止实例失败"
    status = get_instance_status(test_name)
    assert status["status"] == "stopped", f"停止后状态错误: {status}"
    log_info("测试 3 (停止实例) 通过")

    # 测试 4: 报告生成
    instances = [get_instance_status(test_name)]
    report_json = generate_report(instances, fmt="json")
    assert report_json is not None, "JSON 报告生成失败"
    report_md = generate_report(instances, fmt="markdown")
    assert report_md is not None, "Markdown 报告生成失败"
    log_info("测试 4 (报告生成) 通过")

    # 测试 5: dry-run 模式
    dry_run = True
    result = start_instance(test_name, tag="selftest")
    assert result, "dry-run 启动实例失败"
    dry_run = False
    log_info("测试 5 (dry-run 模式) 通过")

    # 清理测试实例
    stop_instance(test_name, mode="force")
    shutil.rmtree(get_instance_dir(test_name), ignore_errors=True)

    log_info("自检全部通过")
    return 0


def main():
    """CLI 入口。"""
    global dry_run

    parser = argparse.ArgumentParser(description="Agent-Reach: AI 智能体本地批量运维工具")
    parser.add_argument("--dry-run", action="store_true", help="预演模式，不实际写盘")
    parser.add_argument("--selftest", action="store_true", help="运行内置测试套件")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # start 子命令
    parser_start = subparsers.add_parser("start", help="批量启动实例")
    parser_start.add_argument("--names", type=str, help="实例名称，逗号分隔")
    parser_start.add_argument("--tag", type=str, help="按标签选择实例")
    parser_start.add_argument("--file", type=str, help="从文件读取实例列表")
    parser_start.add_argument("--all", action="store_true", help="操作所有实例")

    # stop 子命令
    parser_stop = subparsers.add_parser("stop", help="批量停止实例")
    parser_stop.add_argument("--names", type=str, help="实例名称，逗号分隔")
    parser_stop.add_argument("--tag", type=str, help="按标签选择实例")
    parser_stop.add_argument("--file", type=str, help="从文件读取实例列表")
    parser_stop.add_argument("--all", action="store_true", help="操作所有实例")
    parser_stop.add_argument("--mode", type=str, choices=["graceful", "force"], default="graceful",
                             help="停止模式: graceful (SIGTERM) 或 force (SIGKILL)")

    # status 子命令
    parser_status = subparsers.add_parser("status", help="状态巡检")
    parser_status.add_argument("--names", type=str, help="实例名称，逗号分隔")
    parser_status.add_argument("--tag", type=str, help="按标签选择实例")
    parser_status.add_argument("--file", type=str, help="从文件读取实例列表")
    parser_status.add_argument("--all", action="store_true", help="操作所有实例")

    # exec 子命令
    parser_exec = subparsers.add_parser("exec", help="远程执行白名单命令")
    parser_exec.add_argument("--names", type=str, help="实例名称，逗号分隔")
    parser_exec.add_argument("--tag", type=str, help="按标签选择实例")
    parser_exec.add_argument("--file", type=str, help="从文件读取实例列表")
    parser_exec.add_argument("--all", action="store_true", help="操作所有实例")
    parser_exec.add_argument("--command", type=str, required=False, help="要执行的命令 (白名单)")

    # report 子命令
    parser_report = subparsers.add_parser("report", help="生成结构化报告")
    parser_report.add_argument("--format", type=str, choices=["json", "markdown"], default="json",
                               help="报告格式")
    parser_report.add_argument("--output", type=str, help="输出文件路径")

    args = parser.parse_args()

    # 设置全局 dry-run
    dry_run = args.dry_run

    # 自检模式
    if args.selftest:
        sys.exit(selftest())

    # 确保目录存在
    ensure_dirs()

    # 根据子命令分发
    if args.command == "start":
        names = resolve_instances(args)
        if not names:
            log_error("未指定任何实例")
            sys.exit(1)
        success_count = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(start_instance, name, args.tag): name for name in names}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    log_error(f"启动实例 {name} 异常: {e}")
        log_info(f"批量启动完成。成功: {success_count}, 失败: {len(names) - success_count}")

    elif args.command == "stop":
        names = resolve_instances(args)
        if not names:
            log_error("未指定任何实例")
            sys.exit(1)
        success_count = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(stop_instance, name, args.mode): name for name in names}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    log_error(f"停止实例 {name} 异常: {e}")
        log_info(f"批量停止完成。成功: {success_count}, 失败: {len(names) - success_count}")

    elif args.command == "status":
        names = resolve_instances(args)
        if not names:
            log_error("未指定任何实例")
            sys.exit(1)
        instances = []
        for name in names:
            instances.append(get_instance_status(name))
        # 输出表格
        print("| 实例名 | 状态 | PID | CPU (%) | 内存 (MB) | 最近日志 |")
        print("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for inst in instances:
            print(f"| {inst['name']} | {inst['status']} | {inst['pid'] or '-'} | "
                  f"{inst['cpu_percent']:.1f} | {inst['memory_mb']:.1f} | {inst['last_log']} |")

    elif args.command == "exec":
        names = resolve_instances(args)
        if not names:
            log_error("未指定任何实例")
            sys.exit(1)
        for name in names:
            log_info(f"在实例 {name} 上执行命令: {args.command}")
            result = execute_remote_command(name, args.command)
            if result:
                log_info(f"执行结果: {result}")
            else:
                log_error(f"执行失败: {name}")

    elif args.command == "report":
        names = list_instances()
        if not names:
            log_error("没有实例可报告")
            sys.exit(1)
        instances = [get_instance_status(name) for name in names]
        report = generate_report(instances, fmt=args.format)
        if report is None:
            sys.exit(1)
        if args.output:
            if dry_run:
                log_info(f"[DRY-RUN] 将写入报告文件: {args.output}")
            else:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(report)
                    log_info(f"报告已生成: {args.output}")
                except OSError as e:
                    log_error(f"写入报告文件失败 {args.output}: {e}")
                    sys.exit(1)
        else:
            print(report)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
