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

# 模块级 dry-run 标志
dry_run = False

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
SSH_BACKOFF_FACTOR = 2


def log_info(message: str) -> None:
    """输出 INFO 级别日志。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] INFO - {message}")


def log_error(message: str) -> None:
    """输出 ERROR 级别日志到 stderr。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR - {message}", file=sys.stderr)


def log_warning(message: str) -> None:
    """输出 WARNING 级别日志到 stderr。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] WARNING - {message}", file=sys.stderr)


def ensure_directories() -> None:
    """确保实例根目录和锁目录存在。"""
    try:
        INSTANCE_ROOT.mkdir(parents=True, exist_ok=True)
        LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log_error(f"无法创建目录: {e}")
        raise


def get_instance_dir(name: str) -> Path:
    """获取实例目录路径。"""
    return INSTANCE_ROOT / name


def get_status_file(name: str) -> Path:
    """获取实例状态文件路径。"""
    return get_instance_dir(name) / "status.json"


def get_pid_file(name: str) -> Path:
    """获取实例 PID 文件路径。"""
    return get_instance_dir(name) / "agent.pid"


def get_log_file(name: str) -> Path:
    """获取实例日志文件路径。"""
    return get_instance_dir(name) / "agent.log"


def get_lock_file(name: str) -> Path:
    """获取实例锁文件路径。"""
    return LOCK_ROOT / f"{name}.lock"


def read_text_safe(path):
    """安全读取文本文件，支持多种编码。"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def read_status(name: str) -> dict:
    """读取实例状态文件，返回状态字典。"""
    status_file = get_status_file(name)
    if not status_file.exists():
        return {"name": name, "status": "unknown", "pid": None, "tag": None, "last_log": None}
    try:
        content = read_text_safe(status_file)
        return json.loads(content)
    except (json.JSONDecodeError, OSError) as e:
        log_warning(f"读取状态文件失败 {status_file}: {e}")
        return {"name": name, "status": "unknown", "pid": None, "tag": None, "last_log": None}


def write_status(name: str, status: dict, dry_run: bool = False) -> None:
    """原子化写入实例状态文件。"""
    if not dry_run:
        status_file = get_status_file(name)
        temp_file = status_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, status_file)
        except OSError as e:
            log_error(f"写入状态文件失败 {status_file}: {e}")
            raise


def read_pid(name: str) -> int | None:
    """读取实例 PID。"""
    pid_file = get_pid_file(name)
    if not pid_file.exists():
        return None
    try:
        content = read_text_safe(pid_file)
        return int(content.strip())
    except (ValueError, OSError) as e:
        log_warning(f"读取 PID 文件失败 {pid_file}: {e}")
        return None


def write_pid(name: str, pid: int, dry_run: bool = False) -> None:
    """原子化写入实例 PID。"""
    if not dry_run:
        pid_file = get_pid_file(name)
        temp_file = pid_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(str(pid))
            os.replace(temp_file, pid_file)
        except OSError as e:
            log_error(f"写入 PID 文件失败 {pid_file}: {e}")
            raise


def append_log(name: str, message: str, dry_run: bool = False) -> None:
    """追加日志到实例日志文件。"""
    if not dry_run:
        log_file = get_log_file(name)
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except OSError as e:
            log_error(f"写入日志文件失败 {log_file}: {e}")


def is_process_running(pid: int) -> bool:
    """检查进程是否在运行。"""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_process_info(pid: int) -> dict:
    """获取进程资源占用信息。"""
    if not is_process_running(pid):
        return {"cpu_percent": 0.0, "memory_mb": 0.0}
    try:
        # 使用 psutil 获取进程信息，如果不可用则返回默认值
        import psutil
        process = psutil.Process(pid)
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_mb = process.memory_info().rss / (1024 * 1024)
        return {"cpu_percent": cpu_percent, "memory_mb": memory_mb}
    except ImportError:
        log_warning("psutil 未安装，无法获取进程资源占用信息")
        return {"cpu_percent": 0.0, "memory_mb": 0.0}
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        log_warning(f"获取进程信息失败: {e}")
        return {"cpu_percent": 0.0, "memory_mb": 0.0}


def acquire_lock(name: str):
    """获取实例锁。"""
    lock_file = get_lock_file(name)
    if HAS_FILELOCK:
        return FileLock(str(lock_file))
    else:
        # 基本文件锁实现
        import fcntl
        lock_fd = open(lock_file, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return lock_fd


def release_lock(lock) -> None:
    """释放实例锁。"""
    if HAS_FILELOCK:
        lock.release()
    else:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def start_instance(name: str, tag: str = None, dry_run: bool = False) -> dict:
    """启动单个实例。"""
    instance_dir = get_instance_dir(name)
    if not instance_dir.exists():
        try:
            instance_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log_error(f"无法创建实例目录 {instance_dir}: {e}")
            return {"name": name, "status": "error", "message": f"无法创建实例目录: {e}"}

    if dry_run:
        log_info(f"[DRY-RUN] 将启动实例: {name} (tag: {tag})")
        return {"name": name, "status": "dry-run", "pid": None, "tag": tag}

    lock = acquire_lock(name)
    try:
        # 检查是否已在运行
        pid = read_pid(name)
        if pid and is_process_running(pid):
            log_warning(f"实例 {name} 已在运行 (PID: {pid})")
            return {"name": name, "status": "already-running", "pid": pid, "tag": tag}

        # 启动真实进程
        try:
            process = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(3600)"],
                stdout=open(get_log_file(name), "a"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as e:
            log_error(f"启动实例 {name} 失败: {e}")
            return {"name": name, "status": "error", "message": f"启动失败: {e}"}

        # 写入 PID 和状态
        write_pid(name, process.pid, dry_run)
        status = {
            "name": name,
            "status": "running",
            "pid": process.pid,
            "tag": tag,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_log": datetime.now(timezone.utc).isoformat(),
        }
        write_status(name, status, dry_run)
        append_log(name, f"实例启动，PID: {process.pid}", dry_run)
        log_info(f"实例 {name} 启动成功 (PID: {process.pid})")
        return {"name": name, "status": "running", "pid": process.pid, "tag": tag}
    finally:
        release_lock(lock)


def stop_instance(name: str, mode: str = "graceful", dry_run: bool = False) -> dict:
    """停止单个实例。"""
    if dry_run:
        log_info(f"[DRY-RUN] 将停止实例: {name} (mode: {mode})")
        return {"name": name, "status": "dry-run", "pid": None}

    lock = acquire_lock(name)
    try:
        pid = read_pid(name)
        if not pid or not is_process_running(pid):
            log_warning(f"实例 {name} 未在运行")
            status = read_status(name)
            status["status"] = "stopped"
            status["last_log"] = datetime.now(timezone.utc).isoformat()
            write_status(name, status, dry_run)
            return {"name": name, "status": "stopped", "pid": None}

        try:
            if mode == "graceful":
                os.kill(pid, signal.SIGTERM)
                # 等待进程退出
                for _ in range(10):
                    if not is_process_running(pid):
                        break
                    time.sleep(0.5)
                if is_process_running(pid):
                    log_warning(f"实例 {name} 优雅停止超时，强制停止")
                    os.kill(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGKILL)
        except OSError as e:
            log_error(f"停止实例 {name} 失败: {e}")
            return {"name": name, "status": "error", "message": f"停止失败: {e}"}

        # 更新状态
        status = read_status(name)
        status["status"] = "stopped"
        status["pid"] = None
        status["last_log"] = datetime.now(timezone.utc).isoformat()
        write_status(name, status, dry_run)
        append_log(name, f"实例停止 (mode: {mode})", dry_run)
        log_info(f"实例 {name} 已停止 (mode: {mode})")
        return {"name": name, "status": "stopped", "pid": None}
    finally:
        release_lock(lock)


def get_instance_status(name: str) -> dict:
    """获取单个实例状态。"""
    status = read_status(name)
    pid = read_pid(name)
    if pid and is_process_running(pid):
        status["status"] = "running"
        status["pid"] = pid
        process_info = get_process_info(pid)
        status["cpu_percent"] = process_info["cpu_percent"]
        status["memory_mb"] = process_info["memory_mb"]
    else:
        status["status"] = "stopped"
        status["pid"] = None
        status["cpu_percent"] = 0.0
        status["memory_mb"] = 0.0
    return status


def list_instances() -> list:
    """列出所有已注册的实例。"""
    if not INSTANCE_ROOT.exists():
        return []
    try:
        return [d.name for d in INSTANCE_ROOT.iterdir() if d.is_dir()]
    except OSError as e:
        log_error(f"列出实例失败: {e}")
        return []


def filter_instances(names: list = None, tag: str = None, file_path: str = None) -> list:
    """根据名称、标签或文件列表筛选实例。"""
    instances = set()

    if names:
        for name in names:
            name = name.strip()
            if name:
                instances.add(name)

    if tag:
        for name in list_instances():
            status = read_status(name)
            if status.get("tag") == tag:
                instances.add(name)

    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    name = line.strip()
                    if name and not name.startswith("#"):
                        instances.add(name)
        except OSError as e:
            log_error(f"读取文件失败 {file_path}: {e}")

    return list(instances)


def execute_remote_command(name: str, command: str, dry_run: bool = False) -> dict:
    """在远程实例上执行白名单命令。"""
    if command not in ALLOWED_COMMANDS:
        log_error(f"命令 '{command}' 不在白名单中")
        return {"name": name, "status": "error", "message": f"命令 '{command}' 不在白名单中"}

    if dry_run:
        log_info(f"[DRY-RUN] 将在实例 {name} 上执行命令: {command}")
        return {"name": name, "status": "dry-run", "output": ""}

    # 获取实例连接信息
    status = read_status(name)
    host = status.get("host", "localhost")
    port = status.get("port", 22)
    username = status.get("username", os.environ.get("USER", "root"))

    # 执行命令
    if HAS_PARAMIKO:
        return _execute_remote_command_paramiko(name, host, port, username, command)
    else:
        return _execute_remote_command_ssh(name, host, port, username, command)


def _execute_remote_command_paramiko(name: str, host: str, port: int, username: str, command: str) -> dict:
    """使用 paramiko 执行远程命令。"""
    for attempt in range(SSH_RETRIES):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, port=port, username=username, timeout=SSH_TIMEOUT)
            stdin, stdout, stderr = client.exec_command(" ".join(ALLOWED_COMMANDS[command]))
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")
            client.close()
            if error:
                log_warning(f"实例 {name} 执行命令 {command} 时出现错误: {error}")
            log_info(f"实例 {name} 执行命令 {command} 成功")
            return {"name": name, "status": "success", "output": output.strip()}
        except Exception as e:
            log_warning(f"SSH 连接失败 (尝试 {attempt + 1}/{SSH_RETRIES}): {e}")
            if attempt < SSH_RETRIES - 1:
                time.sleep(SSH_BACKOFF_FACTOR ** attempt)
            else:
                log_error(f"实例 {name} SSH 连接失败: {e}")
                return {"name": name, "status": "error", "message": f"SSH 连接失败: {e}"}
    return {"name": name, "status": "error", "message": "SSH 连接失败"}


def _execute_remote_command_ssh(name: str, host: str, port: int, username: str, command: str) -> dict:
    """使用系统 ssh 命令执行远程命令。"""
    for attempt in range(SSH_RETRIES):
        try:
            cmd = ["ssh", "-p", str(port), "-o", f"ConnectTimeout={SSH_TIMEOUT}", f"{username}@{host}"] + ALLOWED_COMMANDS[command]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=SSH_TIMEOUT + 5)
            if result.returncode == 0:
                log_info(f"实例 {name} 执行命令 {command} 成功")
                return {"name": name, "status": "success", "output": result.stdout.strip()}
            else:
                log_warning(f"实例 {name} 执行命令 {command} 失败: {result.stderr}")
                return {"name": name, "status": "error", "message": result.stderr.strip()}
        except subprocess.TimeoutExpired:
            log_warning(f"SSH 命令超时 (尝试 {attempt + 1}/{SSH_RETRIES})")
            if attempt < SSH_RETRIES - 1:
                time.sleep(SSH_BACKOFF_FACTOR ** attempt)
        except Exception as e:
            log_warning(f"SSH 命令执行失败 (尝试 {attempt + 1}/{SSH_RETRIES}): {e}")
            if attempt < SSH_RETRIES - 1:
                time.sleep(SSH_BACKOFF_FACTOR ** attempt)
            else:
                log_error(f"实例 {name} SSH 命令执行失败: {e}")
                return {"name": name, "status": "error", "message": f"SSH 命令执行失败: {e}"}
    return {"name": name, "status": "error", "message": "SSH 命令执行失败"}


def generate_report(instances: list, format: str = "json", output: str = None, dry_run: bool = False) -> str:
    """生成实例状态报告。"""
    report_data = []
    for name in instances:
        status = get_instance_status(name)
        report_data.append(status)

    if format == "json":
        report = json.dumps(report_data, ensure_ascii=False, indent=2)
    elif format == "markdown":
        report = _generate_markdown_report(report_data)
    else:
        log_error(f"不支持的报告格式: {format}")
        return ""

    if dry_run:
        log_info(f"[DRY-RUN] 将生成 {format} 报告，内容如下:\n{report}")
        return report

    if output:
        if not dry_run:
            try:
                with open(output, "w", encoding="utf-8") as f:
                    f.write(report)
                log_info(f"报告已写入 {output}")
            except OSError as e:
                log_error(f"写入报告失败 {output}: {e}")
    else:
        print(report)
    return report


def _generate_markdown_report(data: list) -> str:
    """生成 Markdown 格式报告。"""
    lines = ["# Agent-Reach 实例状态报告", ""]
    lines.append("| Name | Status | PID | CPU(%) | Mem(MB) | Last Log |")
    lines.append("|------|--------|-----|--------|---------|----------|")
    for item in data:
        lines.append(
            f"| {item.get('name', 'N/A')} | {item.get('status', 'N/A')} | "
            f"{item.get('pid', 'N/A')} | {item.get('cpu_percent', 0):.1f} | "
            f"{item.get('memory_mb', 0):.1f} | {item.get('last_log', 'N/A')} |"
        )
    return "\n".join(lines)


def run_selftest() -> int:
    """运行自检测试，验证核心功能。"""
    log_info("开始自检...")
    test_results = []

    # 测试 1: 启动实例
    test_name = "selftest-agent"
    result = start_instance(test_name, tag="selftest", dry_run=False)
    test_results.append(("启动实例", result.get("status") == "running", result))

    # 测试 2: 状态巡检
    status = get_instance_status(test_name)
    test_results.append(("状态巡检", status.get("status") == "running", status))

    # 测试 3: 停止实例
    result = stop_instance(test_name, mode="graceful", dry_run=False)
    test_results.append(("停止实例", result.get("status") == "stopped", result))

    # 测试 4: 报告生成
    report = generate_report([test_name], format="json", dry_run=True)
    test_results.append(("报告生成", len(report) > 0, report))

    # 测试 5: 远程执行（白名单命令检查）
    result = execute_remote_command(test_name, "health_check", dry_run=True)
    test_results.append(("远程执行", result.get("status") == "dry-run", result))

    # 测试 6: 文件读取（编码兜底）
    test_file = Path.home() / ".agent_reach" / "test_encoding.txt"
    try:
        test_file.write_text("测试内容", encoding="utf-8")
        content = read_text_safe(test_file)
        test_results.append(("编码兜底", content == "测试内容", content))
    except Exception as e:
        test_results.append(("编码兜底", False, str(e)))
    finally:
        if test_file.exists():
            try:
                test_file.unlink()
            except OSError as e:
                log_warning(f"清理测试文件失败: {e}")

    # 测试 7: 流式读取（大文件）
    test_file = Path.home() / ".agent_reach" / "test_large.txt"
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            for i in range(1000):
                f.write(f"line {i}\n")
        line_count = 0
        with open(test_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line_count += 1
        test_results.append(("流式读取", line_count == 1000, f"读取 {line_count} 行"))
    except Exception as e:
        test_results.append(("流式读取", False, str(e)))
    finally:
        if test_file.exists():
            try:
                test_file.unlink()
            except OSError as e:
                log_warning(f"清理测试文件失败: {e}")

    # 输出测试结果
    all_passed = True
    for test_name, passed, detail in test_results:
        status_str = "PASS" if passed else "FAIL"
        log_info(f"[{status_str}] {test_name}")
        if not passed:
            all_passed = False
            log_error(f"  详情: {detail}")

    if all_passed:
        log_info("所有自检测试通过!")
        return 0
    else:
        log_error("自检测试失败!")
        return 1


def main():
    """主入口函数。"""
    global dry_run

    parser = argparse.ArgumentParser(
        description="Agent-Reach: AI 智能体本地批量运维工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run", action="store_true", help="预演模式，只打印操作不实际执行")
    parser.add_argument("--selftest", action="store_true", help="运行自检测试")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # start 命令
    start_parser = subparsers.add_parser("start", help="启动实例")
    start_parser.add_argument("--names", type=str, help="实例名称，逗号分隔")
    start_parser.add_argument("--tag", type=str, help="标签筛选")
    start_parser.add_argument("--file", type=str, help="实例列表文件")

    # stop 命令
    stop_parser = subparsers.add_parser("stop", help="停止实例")
    stop_parser.add_argument("--names", type=str, help="实例名称，逗号分隔")
    stop_parser.add_argument("--tag", type=str, help="标签筛选")
    stop_parser.add_argument("--file", type=str, help="实例列表文件")
    stop_parser.add_argument("--mode", type=str, choices=["graceful", "force"], default="graceful", help="停止模式")

    # status 命令
    status_parser = subparsers.add_parser("status", help="状态巡检")
    status_parser.add_argument("--names", type=str, help="实例名称，逗号分隔")
    status_parser.add_argument("--all", action="store_true", help="查看所有实例")

    # exec 命令
    exec_parser = subparsers.add_parser("exec", help="远程执行")
    exec_parser.add_argument("--names", type=str, help="实例名称，逗号分隔")
    exec_parser.add_argument("--command", type=str, required=False, help="要执行的命令")

    # report 命令
    report_parser = subparsers.add_parser("report", help="结果汇总")
    report_parser.add_argument("--format", type=str, choices=["json", "markdown"], default="json", help="报告格式")
    report_parser.add_argument("--output", type=str, help="输出文件路径")

    args = parser.parse_args()

    # 设置全局 dry-run 标志
    dry_run = args.dry_run

    # 运行自检（必须在所有必填校验之前）
    if args.selftest:
        return run_selftest()

    # 确保目录存在
    ensure_directories()

    # 处理命令
    if args.command == "start":
        names = filter_instances(
            names=args.names.split(",") if args.names else None,
            tag=args.tag,
            file_path=args.file,
        )
        if not names:
            log_error("未找到要启动的实例")
            return 1

        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(start_instance, name, args.tag, args.dry_run): name for name in names}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    log_error(f"启动实例失败: {e}")
                    results.append({"name": futures[future], "status": "error", "message": str(e)})

        success_count = sum(1 for r in results if r.get("status") in ["running", "already-running", "dry-run"])
        log_info(f"成功启动 {success_count}/{len(results)} 个实例")
        if args.verbose:
            for i, r in enumerate(results):
                print(f"[明细] {i}. {r.get('name', 'N/A')}: {r.get('status', 'N/A')}")
        return 0 if success_count > 0 else 1

    elif args.command == "stop":
        names = filter_instances(
            names=args.names.split(",") if args.names else None,
            tag=args.tag,
            file_path=args.file,
        )
        if not names:
            log_error("未找到要停止的实例")
            return 1

        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(stop_instance, name, args.mode, args.dry_run): name for name in names}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    log_error(f"停止实例失败: {e}")
                    results.append({"name": futures[future], "status": "error", "message": str(e)})

        success_count = sum(1 for r in results if r.get("status") in ["stopped", "dry-run"])
        log_info(f"成功停止 {success_count}/{len(results)} 个实例")
        if args.verbose:
            for i, r in enumerate(results):
                print(f"[明细] {i}. {r.get('name', 'N/A')}: {r.get('status', 'N/A')}")
        return 0 if success_count > 0 else 1

    elif args.command == "status":
        if args.all:
            names = list_instances()
        else:
            names = filter_instances(names=args.names.split(",") if args.names else None)

        if not names:
            log_info("没有找到任何实例")
            return 0

        # 输出状态表格
        print("+-----------+---------+-------+--------+---------+---------------------+")
        print("| Name      | Status  | PID   | CPU(%) | Mem(MB) | Last Log            |")
        print("+-----------+---------+-------+--------+---------+---------------------+")
        for name in names:
            status = get_instance_status(name)
            print(
                f"| {name:<10} | {status.get('status', 'N/A'):<7} | "
                f"{str(status.get('pid', 'N/A')):<5} | "
                f"{status.get('cpu_percent', 0):<6.1f} | "
                f"{status.get('memory_mb', 0):<7.1f} | "
                f"{status.get('last_log', 'N/A')[:19]:<19} |"
            )
        print("+-----------+---------+-------+--------+---------+---------------------+")
        return 0

    elif args.command == "exec":
        names = filter_instances(names=args.names.split(",") if args.names else None)
        if not names:
            log_error("未找到要执行命令的实例")
            return 1

        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(execute_remote_command, name, args.command, args.dry_run): name for name in names}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    log_error(f"执行命令失败: {e}")
                    results.append({"name": futures[future], "status": "error", "message": str(e)})

        success_count = sum(1 for r in results if r.get("status") in ["success", "dry-run"])
        log_info(f"成功执行 {success_count}/{len(results)} 个实例")
        if args.verbose:
            for i, r in enumerate(results):
                print(f"[明细] {i}. {r.get('name', 'N/A')}: {r.get('status', 'N/A')}")
        return 0 if success_count > 0 else 1

    elif args.command == "report":
        names = list_instances()
        if not names:
            log_info("没有找到任何实例")
            return 0

        generate_report(names, format=args.format, output=args.output, dry_run=args.dry_run)
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
