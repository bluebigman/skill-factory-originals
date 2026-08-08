#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - God 进程监控配置与运维辅助工具（独立实现）

本脚本根据功能规格独立编写，不参考任何既有实现。
提供配置生成、校验、状态巡检、操作指令、日志分析等辅助能力。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ========== 错误码定义 ==========
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "文件读取失败",
    "E004": "配置解析失败",
    "E005": "配置校验失败",
    "E006": "日志解析失败",
    "E007": "状态查询失败",
    "E008": "命令生成失败",
    "E009": "自检失败",
    "E010": "未知错误",
}


class GodToolError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ========== 核心数据结构 ==========

class GodProcess:
    """God 受管进程描述"""

    def __init__(self, name: str, command: str, **kwargs):
        self.name = name
        self.command = command
        self.log_file = kwargs.get("log_file", f"/var/log/god/{name}.log")
        self.pid_file = kwargs.get("pid_file", f"/var/run/god/{name}.pid")
        self.keep_alive = kwargs.get("keep_alive", True)
        self.interval = kwargs.get("interval", 30)  # 秒
        self.memory_limit = kwargs.get("memory_limit", None)  # MB
        self.cpu_limit = kwargs.get("cpu_limit", None)  # 百分比
        self.start_grace = kwargs.get("start_grace", 10)  # 秒
        self.stop_grace = kwargs.get("stop_grace", 10)  # 秒
        self.restart_grace = kwargs.get("restart_grace", 10)  # 秒
        self.group = kwargs.get("group", "default")
        self.env = kwargs.get("env", {})
        self.user = kwargs.get("user", None)
        self.directory = kwargs.get("directory", None)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "command": self.command,
            "log_file": self.log_file,
            "pid_file": self.pid_file,
            "keep_alive": self.keep_alive,
            "interval": self.interval,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "start_grace": self.start_grace,
            "stop_grace": self.stop_grace,
            "restart_grace": self.restart_grace,
            "group": self.group,
            "env": self.env,
            "user": self.user,
            "directory": self.directory,
        }


# ========== 配置生成 ==========

def generate_god_config(processes: list) -> str:
    """
    生成 God 配置文件内容（.god 格式）
    """
    lines = []
    lines.append("# God 配置文件 - 由 god 工具自动生成")
    lines.append(f"# 生成时间: {datetime.now().isoformat()}")
    lines.append("")

    # 全局配置
    lines.append("God.load do")
    lines.append("  # 全局设置")
    lines.append("  God.interval = 30  # 全局检查间隔（秒）")
    lines.append("")

    # 按分组组织进程
    groups = {}
    for p in processes:
        if p.group not in groups:
            groups[p.group] = []
        groups[p.group].append(p)

    for group_name, group_processes in groups.items():
        lines.append(f"  # ===== 组: {group_name} =====")
        lines.append(f"  God.group('{group_name}') do |group|")
        lines.append("    group.interval = 30")
        lines.append("")

        for p in group_processes:
            lines.append(f"    # ---- 进程: {p.name} ----")
            lines.append(f"    group.watch do |w|")
            lines.append(f"      w.name = '{p.name}'")
            lines.append(f"      w.group = '{p.group}'")
            if p.directory:
                lines.append(f"      w.dir = '{p.directory}'")
            else:
                lines.append("      # w.dir = '/path/to/app'")
            lines.append(f"      w.log = '{p.log_file}'")
            lines.append(f"      w.pid_file = '{p.pid_file}'")
            lines.append("")
            lines.append("      # 启动命令")
            lines.append(f"      w.start = '{p.command}'")
            lines.append("      w.stop = 'kill -QUIT %d'  # 默认停止命令")
            lines.append("      w.restart = 'kill -USR2 %d'  # 默认重启命令")
            lines.append("")
            lines.append("      # 生命周期配置")
            lines.append(f"      w.keepalive = {str(p.keep_alive).lower()}")
            lines.append(f"      w.interval = {p.interval}")
            lines.append(f"      w.start_grace = {p.start_grace}")
            lines.append(f"      w.stop_grace = {p.stop_grace}")
            lines.append(f"      w.restart_grace = {p.restart_grace}")
            lines.append("")
            lines.append("      # 资源限制（可选）")
            if p.memory_limit:
                lines.append(f"      w.memory_limit = {p.memory_limit}  # MB")
            if p.cpu_limit:
                lines.append(f"      w.cpu_limit = {p.cpu_limit}  # %")
            lines.append("")
            lines.append("      # 环境变量（可选）")
            if p.env:
                for k, v in p.env.items():
                    lines.append(f"      w.env['{k}'] = '{v}'")
            lines.append("")
            lines.append("      # 生命周期回调（示例）")
            lines.append("      w.transition(:up, :start) do |on|")
            lines.append("        on.condition(:process_running) do |c|")
            lines.append("          c.running = true")
            lines.append("          c.notify = 'ops@example.com'")
            lines.append("        end")
            lines.append("      end")
            lines.append("    end")
            lines.append("")
        lines.append("  end")
        lines.append("")

    lines.append("end")
    lines.append("")
    return "\n".join(lines)


# ========== 配置校验 ==========

def validate_god_config(config_text: str) -> list:
    """
    校验 God 配置文件的语法和基本结构
    返回问题列表（空列表表示通过）
    """
    issues = []

    # 检查基本结构
    if "God.load" not in config_text:
        issues.append("缺少 God.load 块")

    if "watch" not in config_text:
        issues.append("未找到任何 watch 定义")

    # 检查括号配对
    open_count = config_text.count("do")
    close_count = config_text.count("end")
    if open_count != close_count:
        issues.append(f"do/end 数量不匹配: {open_count} do vs {close_count} end")

    # 检查关键配置项
    required_keys = ["w.name", "w.start", "w.pid_file", "w.log"]
    for key in required_keys:
        if key not in config_text:
            issues.append(f"缺少关键配置: {key}")

    # 检查命令是否包含必要信息
    start_match = re.search(r"w\.start\s*=\s*'([^']+)'", config_text)
    if start_match:
        cmd = start_match.group(1)
        if not cmd or len(cmd.strip()) < 3:
            issues.append("启动命令过于简单")
    else:
        issues.append("未找到启动命令")

    return issues


# ========== 状态巡检 ==========

def parse_god_status(status_text: str) -> dict:
    """
    解析 God 状态输出
    输入格式示例:
        web (pid 12345) [up] 运行正常
        worker (pid 12346) [down] 已停止
    """
    result = {
        "processes": [],
        "total": 0,
        "up": 0,
        "down": 0,
        "unknown": 0,
    }

    if not status_text:
        raise GodToolError("E007", "状态文本为空")

    lines = status_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 尝试解析: name (pid 123) [state] description
        match = re.match(r"^(\S+)\s+\(pid\s+(\d+)\)\s+\[(\w+)\]\s*(.*)$", line)
        if match:
            name, pid, state, desc = match.groups()
            proc = {
                "name": name,
                "pid": int(pid),
                "state": state,
                "description": desc.strip(),
            }
            result["processes"].append(proc)

            if state == "up":
                result["up"] += 1
            elif state == "down":
                result["down"] += 1
            else:
                result["unknown"] += 1
        else:
            # 尝试其他格式
            match2 = re.match(r"^(\S+)\s+\[(\w+)\]\s*(.*)$", line)
            if match2:
                name, state, desc = match2.groups()
                proc = {
                    "name": name,
                    "pid": None,
                    "state": state,
                    "description": desc.strip(),
                }
                result["processes"].append(proc)

                if state == "up":
                    result["up"] += 1
                elif state == "down":
                    result["down"] += 1
                else:
                    result["unknown"] += 1

    result["total"] = len(result["processes"])
    return result


# ========== 操作指令 ==========

def generate_commands(action: str, process_name: str = None, group: str = None) -> list:
    """
    生成 God 操作命令
    action: start|stop|restart|load|unload|status
    """
    commands = []

    if action == "load":
        commands.append("god load /etc/god/god.conf")
        commands.append("god -c /etc/god/god.conf")
    elif action == "unload":
        if process_name:
            commands.append(f"god unload {process_name}")
        elif group:
            commands.append(f"god unload --group {group}")
        else:
            commands.append("god unload")
    elif action in ("start", "stop", "restart"):
        target = ""
        if process_name:
            target = f" {process_name}"
        elif group:
            target = f" --group {group}"
        commands.append(f"god {action}{target}")
    elif action == "status":
        if process_name:
            commands.append(f"god status {process_name}")
        else:
            commands.append("god status")
    else:
        raise GodToolError("E008", f"不支持的操作: {action}")

    return commands


# ========== 日志分析 ==========

def analyze_god_log(log_text: str) -> dict:
    """
    分析 God 日志，提取事件和告警
    """
    result = {
        "events": [],
        "warnings": [],
        "errors": [],
        "restarts": [],
        "summary": {},
    }

    if not log_text:
        return result

    lines = log_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 分析重启事件
        if "restart" in line.lower() or "restarting" in line.lower():
            result["restarts"].append(line)
            result["events"].append({"type": "restart", "content": line})

        # 分析错误
        if "error" in line.lower() or "fatal" in line.lower():
            result["errors"].append(line)
            result["events"].append({"type": "error", "content": line})

        # 分析警告
        if "warn" in line.lower() or "alert" in line.lower():
            result["warnings"].append(line)
            result["events"].append({"type": "warning", "content": line})

        # 分析启动/停止
        if "start" in line.lower() and "process" in line.lower():
            result["events"].append({"type": "start", "content": line})
        if "stop" in line.lower() and "process" in line.lower():
            result["events"].append({"type": "stop", "content": line})

    # 生成摘要
    result["summary"] = {
        "total_events": len(result["events"]),
        "warnings_count": len(result["warnings"]),
        "errors_count": len(result["errors"]),
        "restarts_count": len(result["restarts"]),
    }

    return result


# ========== 自检功能 ==========

def run_selftest() -> bool:
    """
    自检核心逻辑，使用内置硬编码样例数据
    """
    print("=" * 60)
    print("God 工具自检开始")
    print("=" * 60)

    all_passed = True

    # 1. 测试配置生成
    print("\n[1/5] 测试配置生成...")
    try:
        test_processes = [
            GodProcess(
                name="web_server",
                command="ruby /srv/web/server.rb",
                group="web",
                memory_limit=512,
                cpu_limit=80,
            ),
            GodProcess(
                name="worker",
                command="ruby /srv/worker/worker.rb",
                group="worker",
                env={"RAILS_ENV": "production"},
            ),
        ]
        config = generate_god_config(test_processes)
        assert len(config) > 100, "配置内容过短"
        assert "web_server" in config, "缺少进程名"
        assert "God.load" in config, "缺少 God.load"
        print("  ✓ 配置生成正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 配置生成失败: {e}")

    # 2. 测试配置校验
    print("\n[2/5] 测试配置校验...")
    try:
        valid_config = """
        God.load do
          God.watch do |w|
            w.name = 'test'
            w.start = 'ruby /tmp/app.rb'
            w.pid_file = '/tmp/test.pid'
            w.log = '/tmp/test.log'
          end
        end
        """
        issues = validate_god_config(valid_config)
        assert len(issues) == 0, f"有效配置被误报: {issues}"

        invalid_config = "this is not valid"
        issues = validate_god_config(invalid_config)
        assert len(issues) > 0, "无效配置未被识别"
        print("  ✓ 配置校验正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 配置校验失败: {e}")

    # 3. 测试状态解析
    print("\n[3/5] 测试状态解析...")
    try:
        sample_status = """
        web_server (pid 12345) [up] 运行正常
        worker (pid 12346) [down] 进程退出
        cron_job [unknown] 状态未知
        """
        status = parse_god_status(sample_status)
        assert status["total"] == 3, f"进程总数错误: {status['total']}"
        assert status["up"] == 1, f"运行数错误: {status['up']}"
        assert status["down"] == 1, f"停止数错误: {status['down']}"
        assert status["unknown"] == 1, f"未知数错误: {status['unknown']}"
        print("  ✓ 状态解析正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 状态解析失败: {e}")

    # 4. 测试命令生成
    print("\n[4/5] 测试命令生成...")
    try:
        cmds = generate_commands("start", process_name="web_server")
        assert len(cmds) > 0, "未生成命令"
        assert "god start" in cmds[0], "命令格式错误"

        cmds = generate_commands("load")
        assert len(cmds) > 0, "未生成加载命令"
        assert "god load" in cmds[0], "加载命令格式错误"
        print("  ✓ 命令生成正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 命令生成失败: {e}")

    # 5. 测试日志分析
    print("\n[5/5] 测试日志分析...")
    try:
        sample_log = """
        [2026-01-01 10:00:00] INFO  Starting process web_server
        [2026-01-01 10:00:05] WARN  CPU usage high for web_server
        [2026-01-01 10:00:10] ERROR Process web_server crashed
        [2026-01-01 10:00:15] INFO  Restarting process web_server
        [2026-01-01 10:00:20] ERROR Cannot restart web_server
        """
        analysis = analyze_god_log(sample_log)
        assert analysis["summary"]["errors_count"] >= 2, "错误数量错误"
        assert analysis["summary"]["warnings_count"] >= 1, "警告数量错误"
        assert len(analysis["restarts"]) >= 1, "重启事件未识别"
        print("  ✓ 日志分析正常")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 日志分析失败: {e}")

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过: 所有核心功能正常")
    else:
        print("自检失败: 存在功能异常")
    print("=" * 60)

    return all_passed


# ========== 命令行入口 ==========

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="God 进程监控配置与运维辅助工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --generate --output god.conf
  %(prog)s --validate --file god.conf
  %(prog)s --status --input status.txt
  %(prog)s --command start --process web_server
  %(prog)s --analyze-log --file god.log
  %(prog)s --selftest
        """,
    )

    parser.add_argument("--version", action="version", version="god 1.0.2")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--generate", action="store_true", help="生成配置")
    parser.add_argument("--validate", action="store_true", help="校验配置")
    parser.add_argument("--status", action="store_true", help="解析状态")
    parser.add_argument("--command", choices=["start", "stop", "restart", "load", "unload", "status"], help="生成操作命令")
    parser.add_argument("--analyze-log", action="store_true", help="分析日志")
    parser.add_argument("--file", help="输入文件路径")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--process", help="进程名")
    parser.add_argument("--group", help="组名")
    parser.add_argument("--input", help="输入文本")

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            success = run_selftest()
            sys.exit(0 if success else 1)

        # 配置生成
        if args.generate:
            # 使用示例数据生成配置
            processes = [
                GodProcess(
                    name="web_server",
                    command="ruby /srv/web/server.rb",
                    group="web",
                    memory_limit=512,
                    cpu_limit=80,
                    directory="/srv/web",
                ),
                GodProcess(
                    name="worker",
                    command="ruby /srv/worker/worker.rb",
                    group="worker",
                    env={"RAILS_ENV": "production"},
                    directory="/srv/worker",
                ),
            ]
            config = generate_god_config(processes)

            if args.output:
                Path(args.output).write_text(config, encoding="utf-8")
                print(f"配置已生成: {args.output}")
            else:
                print(config)
            return

        # 配置校验
        if args.validate:
            if not args.file:
                raise GodToolError("E001", "--validate 需要 --file 参数")

            if not os.path.exists(args.file):
                raise GodToolError("E002", f"文件不存在: {args.file}")

            try:
                config_text = Path(args.file).read_text(encoding="utf-8")
            except Exception as e:
                raise GodToolError("E003", f"读取文件失败: {e}")

            issues = validate_god_config(config_text)
            if issues:
                print("配置校验未通过:")
                for issue in issues:
                    print(f"  - {issue}")
                sys.exit(1)
            else:
                print("配置校验通过")
            return

        # 状态解析
        if args.status:
            status_text = args.input
            if not status_text and args.file:
                try:
                    status_text = Path(args.file).read_text(encoding="utf-8")
                except Exception as e:
                    raise GodToolError("E003", f"读取文件失败: {e}")

            if not status_text:
                raise GodToolError("E001", "--status 需要 --input 或 --file")

            result = parse_god_status(status_text)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # 命令生成
        if args.command:
            commands = generate_commands(args.command, args.process, args.group)
            for cmd in commands:
                print(cmd)
            return

        # 日志分析
        if args.analyze_log:
            log_text = args.input
            if not log_text and args.file:
                try:
                    log_text = Path(args.file).read_text(encoding="utf-8")
                except Exception as e:
                    raise GodToolError("E003", f"读取文件失败: {e}")

            if not log_text:
                raise GodToolError("E001", "--analyze-log 需要 --input 或 --file")

            result = analyze_god_log(log_text)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # 无参数时显示帮助
        parser.print_help()

    except GodToolError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E010']}] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
