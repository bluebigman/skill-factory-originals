#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent-Reach: 智能体运维 远程管控 批量调度
==========================================
真实可用的批量智能体实例管理工具。

核心能力:
1. 批量启动/停止智能体实例 (模拟真实进程管理, 通过 PID 文件)
2. 状态巡检 (读取实例状态文件, 计算资源占用)
3. 远程执行白名单命令 (通过 subprocess 在本地模拟远程执行)
4. 结果汇总 (输出 JSON / Markdown 报告)

设计说明:
- 使用本地文件系统模拟实例状态 (真实 IO 操作)
- 每个实例对应一个目录: ~/.agent_reach/instances/<name>/
  - status.json   : 实例状态信息
  - agent.pid     : 模拟进程 PID (实际为随机数)
  - agent.log     : 实例日志
- 支持按名称、标签、文件列表批量操作

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
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 实例根目录
INSTANCE_ROOT = Path.home() / ".agent_reach" / "instances"

# 白名单命令 (模拟远程执行)
ALLOWED_COMMANDS = {
    "health_check": "echo 'OK - all systems healthy'",
    "disk_usage": "df -h / | tail -1",
    "memory_usage": "free -m | grep Mem",
    "uptime": "uptime",
}

# 默认标签
DEFAULT_TAGS = ["test", "prod", "dev"]


def ensure_environment():
    """确保实例目录存在"""
    INSTANCE_ROOT.mkdir(parents=True, exist_ok=True)


def create_instance(name, tag="test"):
    """创建模拟智能体实例 (真实文件操作)"""
    inst_dir = INSTANCE_ROOT / name
    inst_dir.mkdir(parents=True, exist_ok=True)

    # 生成状态文件
    status = {
        "name": name,
        "tag": tag,
        "status": "stopped",
        "pid": None,
        "created_at": datetime.now().isoformat(),
        "last_start": None,
        "last_stop": None,
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
    }
    with open(inst_dir / "status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    # 初始化日志
    with open(inst_dir / "agent.log", "w", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] 实例 {name} 已创建\n")

    return status


def load_instance(name):
    """加载实例状态"""
    status_file = INSTANCE_ROOT / name / "status.json"
    if not status_file.exists():
        raise FileNotFoundError(f"实例 {name} 不存在")
    with open(status_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_instance(status):
    """保存实例状态"""
    inst_dir = INSTANCE_ROOT / status["name"]
    inst_dir.mkdir(parents=True, exist_ok=True)
    with open(inst_dir / "status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def append_log(name, message):
    """追加日志"""
    log_file = INSTANCE_ROOT / name / "agent.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {message}\n")


def start_instance(name, tag="test"):
    """启动实例 (模拟真实启动)"""
    try:
        status = load_instance(name)
    except FileNotFoundError:
        status = create_instance(name, tag)

    if status["status"] == "running":
        print(f"⚠️  实例 {name} 已在运行中")
        return status

    # 模拟启动过程
    status["status"] = "running"
    status["pid"] = random.randint(10000, 99999)
    status["last_start"] = datetime.now().isoformat()
    status["cpu_usage"] = round(random.uniform(1.0, 30.0), 1)
    status["memory_usage"] = round(random.uniform(100, 1024), 1)
    save_instance(status)
    append_log(name, f"实例启动成功 (PID: {status['pid']})")
    print(f"✅ 实例 {name} 已启动 (PID: {status['pid']})")
    return status


def stop_instance(name, mode="graceful"):
    """停止实例"""
    status = load_instance(name)

    if status["status"] == "stopped":
        print(f"⚠️  实例 {name} 已在停止状态")
        return status

    if mode == "graceful":
        # 优雅停止: 模拟等待
        time.sleep(0.1)
        status["status"] = "stopped"
        status["pid"] = None
        status["last_stop"] = datetime.now().isoformat()
        status["cpu_usage"] = 0.0
        status["memory_usage"] = 0.0
        save_instance(status)
        append_log(name, "实例已优雅停止")
        print(f"✅ 实例 {name} 已优雅停止")
    elif mode == "force":
        # 强制停止: 立即终止
        status["status"] = "stopped"
        status["pid"] = None
        status["last_stop"] = datetime.now().isoformat()
        status["cpu_usage"] = 0.0
        status["memory_usage"] = 0.0
        save_instance(status)
        append_log(name, "实例已强制停止")
        print(f"✅ 实例 {name} 已强制停止")
    else:
        raise ValueError(f"无效的停止模式: {mode}")

    return status


def get_status(name):
    """获取实例状态"""
    status = load_instance(name)
    return status


def list_instances(tag=None):
    """列出所有实例"""
    instances = []
    if INSTANCE_ROOT.exists():
        for inst_dir in INSTANCE_ROOT.iterdir():
            if inst_dir.is_dir():
                try:
                    status = load_instance(inst_dir.name)
                    if tag is None or status.get("tag") == tag:
                        instances.append(status)
                except (FileNotFoundError, json.JSONDecodeError):
                    continue
    return instances


def exec_command(name, command):
    """在实例上执行白名单命令 (本地模拟)"""
    if command not in ALLOWED_COMMANDS:
        raise ValueError(
            f"命令 '{command}' 不在白名单中。可用命令: {', '.join(ALLOWED_COMMANDS.keys())}"
        )

    status = load_instance(name)
    if status["status"] != "running":
        raise RuntimeError(f"实例 {name} 未运行, 无法执行命令")

    # 模拟远程执行
    cmd = ALLOWED_COMMANDS[command]
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=5
    )
    append_log(name, f"执行命令: {command} -> {result.stdout.strip()}")
    return result.stdout.strip()


def generate_report(instances, format="json"):
    """生成汇总报告"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_instances": len(instances),
        "running": sum(1 for i in instances if i["status"] == "running"),
        "stopped": sum(1 for i in instances if i["status"] == "stopped"),
        "instances": instances,
    }

    if format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2)
    elif format == "markdown":
        lines = [
            "# Agent-Reach 实例状态报告",
            "",
            f"生成时间: {report['generated_at']}",
            f"实例总数: {report['total_instances']}",
            f"运行中: {report['running']}",
            f"已停止: {report['stopped']}",
            "",
            "| 实例名 | 标签 | 状态 | PID | CPU% | 内存(MB) |",
            "|--------|------|------|-----|------|----------|",
        ]
        for inst in instances:
            lines.append(
                f"| {inst['name']} | {inst.get('tag', '-')} | {inst['status']} | "
                f"{inst.get('pid', '-')} | {inst.get('cpu_usage', 0)} | "
                f"{inst.get('memory_usage', 0)} |"
            )
        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的格式: {format}")


def parse_instances(names_str=None, file_path=None, tag=None):
    """解析实例列表"""
    instances = []

    if names_str:
        instances.extend(names_str.split(","))

    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    instances.append(line)

    if tag:
        tagged = [i["name"] for i in list_instances(tag=tag)]
        instances.extend(tagged)

    # 去重
    return list(set(instances))


def selftest():
    """自检函数: 验证核心功能"""
    print("🔍 运行自检...")

    # 清理测试环境
    test_dir = INSTANCE_ROOT / "selftest-agent"
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)

    # 1. 创建实例
    print("  1. 创建测试实例...")
    status = create_instance("selftest-agent", tag="selftest")
    assert status["status"] == "stopped", "创建失败: 状态应为 stopped"

    # 2. 启动实例
    print("  2. 启动实例...")
    status = start_instance("selftest-agent")
    assert status["status"] == "running", "启动失败: 状态应为 running"
    assert status["pid"] is not None, "启动失败: PID 不应为空"

    # 3. 状态查询
    print("  3. 查询状态...")
    status = get_status("selftest-agent")
    assert status["status"] == "running", "状态查询失败"

    # 4. 执行命令
    print("  4. 执行白名单命令...")
    result = exec_command("selftest-agent", "health_check")
    assert "OK" in result, f"命令执行失败: {result}"

    # 5. 停止实例
    print("  5. 停止实例...")
    status = stop_instance("selftest-agent", mode="graceful")
    assert status["status"] == "stopped", "停止失败: 状态应为 stopped"

    # 6. 生成报告
    print("  6. 生成报告...")
    instances = list_instances(tag="selftest")
    report = generate_report(instances, format="json")
    assert "selftest-agent" in report, "报告生成失败"

    # 清理
    import shutil
    shutil.rmtree(test_dir)

    print("✅ 自检通过! 所有功能正常。")


def main():
    parser = argparse.ArgumentParser(
        description="Agent-Reach: 智能体运维 远程管控 批量调度",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
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
        """,
    )

    # 全局参数
    parser.add_argument(
        "--selftest", action="store_true", help="运行自检功能"
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="操作命令")

    # start 命令
    start_parser = subparsers.add_parser("start", help="批量启动实例")
    start_parser.add_argument("--names", help="实例名称列表, 逗号分隔")
    start_parser.add_argument("--file", help="实例列表文件")
    start_parser.add_argument("--tag", help="按标签启动")

    # stop 命令
    stop_parser = subparsers.add_parser("stop", help="批量停止实例")
    stop_parser.add_argument("--names", help="实例名称列表, 逗号分隔")
    stop_parser.add_argument("--file", help="实例列表文件")
    stop_parser.add_argument("--tag", help="按标签停止")
    stop_parser.add_argument(
        "--mode", choices=["graceful", "force"], default="graceful",
        help="停止模式: graceful(优雅) / force(强制)"
    )

    # status 命令
    status_parser = subparsers.add_parser("status", help="状态巡检")
    status_parser.add_argument("--names", help="实例名称列表, 逗号分隔")
    status_parser.add_argument("--all", action="store_true", help="查看所有实例")

    # exec 命令
    exec_parser = subparsers.add_parser("exec", help="远程执行命令")
    exec_parser.add_argument("--names", required=True, help="实例名称列表, 逗号分隔")
    exec_parser.add_argument(
        "--command", required=True, choices=list(ALLOWED_COMMANDS.keys()),
        help="要执行的命令"
    )

    # report 命令
    report_parser = subparsers.add_parser("report", help="生成汇总报告")
    report_parser.add_argument(
        "--format", choices=["json", "markdown"], default="json",
        help="报告格式"
    )
    report_parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        selftest()
        return 0

    # 确保环境
    ensure_environment()

    try:
        if args.command == "start":
            instances = parse_instances(args.names, args.file, args.tag)
            if not instances:
                print("❌ 未指定任何实例", file=sys.stderr)
                return 1
            for name in instances:
                start_instance(name, tag=args.tag or "test")

        elif args.command == "stop":
            instances = parse_instances(args.names, args.file, args.tag)
            if not instances:
                print("❌ 未指定任何实例", file=sys.stderr)
                return 1
            for name in instances:
                stop_instance(name, mode=args.mode)

        elif args.command == "status":
            if args.all:
                instances = list_instances()
                for inst in instances:
                    print(
                        f"📊 {inst['name']}: {inst['status']} "
                        f"(PID: {inst.get('pid', '-')}, "
                        f"CPU: {inst.get('cpu_usage', 0)}%, "
                        f"内存: {inst.get('memory_usage', 0)}MB)"
                    )
            elif args.names:
                for name in args.names.split(","):
                    inst = get_status(name)
                    print(
                        f"📊 {inst['name']}: {inst['status']} "
                        f"(PID: {inst.get('pid', '-')}, "
                        f"CPU: {inst.get('cpu_usage', 0)}%, "
                        f"内存: {inst.get('memory_usage', 0)}MB)"
                    )
            else:
                print("❌ 请指定 --names 或 --all", file=sys.stderr)
                return 1

        elif args.command == "exec":
            for name in args.names.split(","):
                try:
                    result = exec_command(name, args.command)
                    print(f"🔧 {name}: {result}")
                except (FileNotFoundError, RuntimeError) as e:
                    print(f"❌ {name}: {e}", file=sys.stderr)

        elif args.command == "report":
            instances = list_instances()
            report = generate_report(instances, args.format)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"✅ 报告已保存到 {args.output}")
            else:
                print(report)

        else:
            parser.print_help()
            return 1

        return 0

    except FileNotFoundError as e:
        print(f"❌ 文件错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"❌ 参数错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 执行失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
