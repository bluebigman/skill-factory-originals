#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

God 进程监控技能 - 独立实现脚本
功能：生成 God 配置文件、解析命令、状态诊断、最佳实践建议、批量配置模板
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "配置文件生成失败：进程名称无效",
    "E003": "配置文件生成失败：命令为空",
    "E004": "配置文件生成失败：内存限制格式不正确",
    "E005": "配置文件生成失败：端口号无效",
    "E006": "状态诊断失败：日志内容为空",
    "E007": "状态诊断失败：无法识别日志格式",
    "E008": "模板生成失败：进程列表为空",
    "E009": "模板生成失败：进程名称重复",
    "E010": "内部错误：未预期的异常",
}


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        msg = f"{msg} - {detail}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 核心功能：God 配置生成
# ============================================================

def validate_process_name(name: str) -> bool:
    """校验进程名称合法性（仅允许字母、数字、下划线、中划线）"""
    return bool(re.match(r"^[A-Za-z0-9_-]+$", name))


def validate_memory_limit(mem: str) -> bool:
    """校验内存限制格式（如 200MB、1GB）"""
    return bool(re.match(r"^\d+(MB|GB|KB)$", mem, re.IGNORECASE))


def validate_port(port: int) -> bool:
    """校验端口号范围"""
    return isinstance(port, int) and 1 <= port <= 65535


def generate_god_config(
    process_name: str,
    command: str,
    *,
    log_file: str = "",
    pid_file: str = "",
    memory_limit: str = "",
    port: Optional[int] = None,
    restart_on_memory: bool = True,
    interval: int = 30,
) -> str:
    """
    生成 God 配置文件内容（.god 格式）

    参数:
        process_name: 进程名称
        command: 启动命令
        log_file: 日志文件路径
        pid_file: PID 文件路径
        memory_limit: 内存限制（如 200MB）
        port: 监听端口
        restart_on_memory: 内存超限是否自动重启
        interval: 监控间隔（秒）

    返回:
        God 配置文本

    错误码:
        E002: 进程名称无效
        E003: 命令为空
        E004: 内存限制格式错误
        E005: 端口号无效
    """
    # 参数校验
    if not validate_process_name(process_name):
        error_exit("E002", f"进程名称 '{process_name}' 包含非法字符")
    if not command or not command.strip():
        error_exit("E003", "启动命令不能为空")
    if memory_limit and not validate_memory_limit(memory_limit):
        error_exit("E004", f"内存限制格式错误: {memory_limit}（示例: 200MB）")
    if port is not None and not validate_port(port):
        error_exit("E005", f"端口号无效: {port}")

    # 构建配置
    lines = [
        f"# God 配置 - {process_name}",
        f"# 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"God.watch do |w|",
        f"  w.name = \"{process_name}\"",
        f"  w.start = \"{command}\"",
        f"  w.keepalive = true",
        f"  w.interval = {interval}",
    ]

    # 可选配置项
    if log_file:
        lines.append(f"  w.log = \"{log_file}\"")
    if pid_file:
        lines.append(f"  w.pid_file = \"{pid_file}\"")

    # 内存限制配置
    if memory_limit:
        mem_num = int(re.match(r"(\d+)", memory_limit).group(1))
        mem_unit = re.match(r"\d+(MB|GB|KB)", memory_limit, re.IGNORECASE).group(1).upper()
        if mem_unit == "GB":
            mem_mb = mem_num * 1024
        elif mem_unit == "KB":
            mem_mb = mem_num / 1024
        else:
            mem_mb = mem_num
        lines.append(f"  w.memory_limit = {int(mem_mb)}MB")
        if restart_on_memory:
            lines.append(f"  w.behavior(:memory) {{ |m| m.restart }}")

    # 端口监控配置
    if port is not None:
        lines.extend([
            f"  w.port = {port}",
            f"  w.behavior(:port) {{ |p| p.restart }}",
        ])

    # 结束
    lines.extend([
        "end",
        "",
    ])

    return "\n".join(lines)


# ============================================================
# 核心功能：命令解析
# ============================================================

def parse_god_command(command_line: str) -> Dict:
    """
    解析 god 命令行参数

    支持: god, god --selftest, god --version, god start/stop/restart <app>

    返回:
        {"action": str, "target": str|None, "options": dict}
    """
    parts = command_line.strip().split()
    if not parts or parts[0] != "god":
        return {"action": "unknown", "target": None, "options": {}}

    # 无参数
    if len(parts) == 1:
        return {"action": "help", "target": None, "options": {}}

    # 解析选项
    options = {}
    target = None
    action = "unknown"

    i = 1
    while i < len(parts):
        arg = parts[i]
        if arg.startswith("--"):
            # 长选项
            if "=" in arg:
                key, val = arg[2:].split("=", 1)
                options[key] = val
            else:
                options[arg[2:]] = True
        elif arg.startswith("-"):
            # 短选项
            options[arg[1:]] = True
        else:
            # 位置参数
            if action == "unknown":
                action = arg
            else:
                target = arg
        i += 1

    return {"action": action, "target": target, "options": options}


def explain_god_command(command_line: str) -> str:
    """解释 god 命令的用途"""
    parsed = parse_god_command(command_line)
    action = parsed["action"]
    options = parsed["options"]
    target = parsed["target"]

    if action == "help":
        return "god 命令帮助：\n  god                 - 显示帮助\n  god --selftest      - 运行自检\n  god --version       - 显示版本\n  god start <app>     - 启动应用\n  god stop <app>      - 停止应用\n  god restart <app>   - 重启应用\n  god status          - 查看状态"

    if action == "selftest" or "selftest" in options:
        return "god --selftest: 运行 God 内置自检，验证配置和环境的正确性。输出 OK 表示通过。"

    if action == "version" or "version" in options:
        return "god --version: 显示当前安装的 God 版本号。用于确认工具版本兼容性。"

    if action in ("start", "stop", "restart"):
        if target:
            return f"god {action} {target}: {'启动' if action == 'start' else '停止' if action == 'stop' else '重启'}名为 '{target}' 的受监控进程。"
        return f"god {action}: 需要指定应用名称。用法: god {action} <app>"

    if action == "status":
        return "god status: 查看所有受监控进程的当前状态（运行/停止/重启中）。"

    return f"无法识别的 god 命令: {command_line}。使用 'god' 查看帮助。"


# ============================================================
# 核心功能：状态诊断
# ============================================================

def diagnose_god_status(log_text: str) -> Dict:
    """
    分析 god 日志或状态输出，定位常见问题

    返回:
        {
            "healthy": bool,
            "issues": list[str],
            "suggestions": list[str],
            "summary": str
        }
    """
    if not log_text or not log_text.strip():
        error_exit("E006", "日志内容为空")

    issues = []
    suggestions = []
    healthy = True

    # 检查常见问题模式
    lines = log_text.strip().split("\n")
    for line in lines:
        line_lower = line.lower()

        # 内存超限
        if "memory" in line_lower and ("limit" in line_lower or "exceed" in line_lower):
            issues.append("内存超限")
            suggestions.append("检查进程内存使用，考虑增加内存限制或优化代码")

        # 端口冲突
        if "port" in line_lower and ("conflict" in line_lower or "in use" in line_lower or "busy" in line_lower):
            issues.append("端口冲突")
            suggestions.append("检查端口占用，释放端口或更换端口号")

        # 进程崩溃
        if "crash" in line_lower or "terminated" in line_lower or "died" in line_lower:
            issues.append("进程异常退出")
            suggestions.append("检查进程日志，确认崩溃原因；考虑增加自动重启策略")

        # 启动失败
        if "fail" in line_lower and "start" in line_lower:
            issues.append("启动失败")
            suggestions.append("检查启动命令和依赖环境，确认路径和权限")

        # 配置错误
        if "config" in line_lower and ("error" in line_lower or "invalid" in line_lower):
            issues.append("配置错误")
            suggestions.append("检查 God 配置文件语法和参数")

        # 权限问题
        if "permission" in line_lower or "denied" in line_lower:
            issues.append("权限不足")
            suggestions.append("检查运行用户是否有足够权限访问文件/端口")

        # 依赖缺失
        if "gem" in line_lower and ("not found" in line_lower or "missing" in line_lower):
            issues.append("依赖缺失")
            suggestions.append("检查 Ruby Gems 依赖是否安装完整")

    if issues:
        healthy = False

    # 构建摘要
    if healthy:
        summary = "未检测到明显问题，God 运行状态正常。"
    else:
        summary = f"检测到 {len(issues)} 个潜在问题: {', '.join(issues)}"

    return {
        "healthy": healthy,
        "issues": issues,
        "suggestions": suggestions,
        "summary": summary,
    }


# ============================================================
# 核心功能：最佳实践建议
# ============================================================

def get_best_practices() -> Dict:
    """返回 God 配置最佳实践建议"""
    return {
        "watch_config": {
            "interval": "建议 30-60 秒，过高消耗资源，过低响应不及时",
            "keepalive": "始终开启 keepalive 实现自动重启",
            "log": "配置日志文件便于排查问题",
        },
        "memory": {
            "limit": "建议设置内存限制为正常使用的 1.5-2 倍",
            "behavior": "内存超限时自动重启，防止内存泄漏影响系统",
        },
        "restart": {
            "strategy": "使用 keepalive + 条件重启组合，避免无限重启",
            "backoff": "建议配置重启退避时间，避免频繁重启",
        },
        "port": {
            "monitor": "对关键服务监控端口，端口不可用时自动重启",
            "conflict": "启动前检查端口占用，避免冲突",
        },
        "batch": {
            "template": "使用模板统一管理多进程配置，减少重复",
            "naming": "进程命名遵循 '应用-环境-实例' 规范，便于识别",
        },
    }


# ============================================================
# 核心功能：批量配置模板
# ============================================================

def generate_batch_template(processes: List[Dict]) -> str:
    """
    为多进程场景生成可复用的配置模板

    参数:
        processes: 进程列表，每个元素为 dict:
            {
                "name": str,
                "command": str,
                "log": str (可选),
                "memory": str (可选),
                "port": int (可选)
            }

    返回:
        合并的 God 配置文本
    """
    if not processes:
        error_exit("E008", "进程列表为空")

    # 检查名称重复
    names = [p.get("name", "") for p in processes]
    if len(names) != len(set(names)):
        error_exit("E009", f"进程名称重复: {names}")

    # 为每个进程生成配置
    configs = []
    for p in processes:
        config = generate_god_config(
            p["name"],
            p["command"],
            log_file=p.get("log", ""),
            pid_file=p.get("pid_file", ""),
            memory_limit=p.get("memory", ""),
            port=p.get("port"),
        )
        configs.append(config)

    # 合并
    header = "# ============================================\n"
    header += f"# God 批量配置模板 - 共 {len(processes)} 个进程\n"
    header += "# 生成时间: " + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
    header += "# ============================================\n\n"

    return header + "\n".join(configs)


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> None:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("=" * 60)
    print("God Skill 自检开始")
    print("=" * 60)

    # ---- 测试1: 配置生成 ----
    print("\n[1/5] 测试配置生成...")
    try:
        config = generate_god_config(
            "sidekiq",
            "bundle exec sidekiq -e production",
            log_file="/var/log/sidekiq.log",
            memory_limit="200MB",
            port=3000,
        )
        assert "sidekiq" in config, "配置应包含进程名"
        assert "bundle exec sidekiq" in config, "配置应包含启动命令"
        assert "200MB" in config or "200" in config, "配置应包含内存限制"
        assert "3000" in config, "配置应包含端口"
        assert "God.watch" in config, "配置应包含 God.watch"
        print("    ✓ 配置生成正常")
    except AssertionError as e:
        error_exit("E010", f"配置生成测试失败: {e}")

    # ---- 测试2: 命令解析 ----
    print("[2/5] 测试命令解析...")
    try:
        r1 = parse_god_command("god --selftest")
        assert r1["action"] == "selftest" or "selftest" in r1["options"], "selftest 解析失败"
        print("    ✓ selftest 命令解析正常")

        r2 = parse_god_command("god start sidekiq")
        assert r2["action"] == "start" and r2["target"] == "sidekiq", "start 命令解析失败"
        print("    ✓ start 命令解析正常")

        r3 = parse_god_command("god --version")
        assert "version" in r3["options"] or r3["action"] == "version", "version 命令解析失败"
        print("    ✓ version 命令解析正常")
    except AssertionError as e:
        error_exit("E010", f"命令解析测试失败: {e}")

    # ---- 测试3: 状态诊断 ----
    print("[3/5] 测试状态诊断...")
    try:
        # 正常日志
        normal_log = "God started\nMonitoring sidekiq\nAll systems operational"
        r1 = diagnose_god_status(normal_log)
        assert r1["healthy"], "正常日志应判定为健康"
        print("    ✓ 正常日志诊断正常")

        # 异常日志
        bad_log = "Memory limit exceeded for sidekiq\nPort 3000 already in use\nProcess crashed"
        r2 = diagnose_god_status(bad_log)
        assert not r2["healthy"], "异常日志应判定为不健康"
        assert len(r2["issues"]) >= 2, "应检测到多个问题"
        print("    ✓ 异常日志诊断正常")
    except AssertionError as e:
        error_exit("E010", f"状态诊断测试失败: {e}")

    # ---- 测试4: 批量模板 ----
    print("[4/5] 测试批量模板生成...")
    try:
        processes = [
            {"name": "web", "command": "puma -p 3000", "port": 3000},
            {"name": "worker", "command": "sidekiq -q default", "memory": "100MB"},
        ]
        template = generate_batch_template(processes)
        assert "web" in template and "worker" in template, "模板应包含两个进程"
        assert "puma" in template and "sidekiq" in template, "模板应包含两个命令"
        print("    ✓ 批量模板生成正常")
    except AssertionError as e:
        error_exit("E010", f"批量模板测试失败: {e}")

    # ---- 测试5: 最佳实践 ----
    print("[5/5] 测试最佳实践建议...")
    try:
        practices = get_best_practices()
        assert "watch_config" in practices, "应包含 watch 配置建议"
        assert "memory" in practices, "应包含内存建议"
        assert "restart" in practices, "应包含重启建议"
        print("    ✓ 最佳实践建议正常")
    except AssertionError as e:
        error_exit("E010", f"最佳实践测试失败: {e}")

    # ---- 完成 ----
    print("\n" + "=" * 60)
    print("✓ 所有自检通过！")
    print("=" * 60)


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="God 进程监控技能 - 配置生成与运维辅助工具",
        epilog="示例:\n  python main.py generate --name sidekiq --command 'bundle exec sidekiq'\n  python main.py --selftest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部依赖）",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate 子命令
    gen_parser = subparsers.add_parser("generate", help="生成 God 配置文件")
    gen_parser.add_argument("--name", required=True, help="进程名称")
    gen_parser.add_argument("--command", required=True, help="启动命令")
    gen_parser.add_argument("--log", default="", help="日志文件路径")
    gen_parser.add_argument("--pid", default="", help="PID 文件路径")
    gen_parser.add_argument("--memory", default="", help="内存限制 (如 200MB)")
    gen_parser.add_argument("--port", type=int, default=None, help="监听端口")
    gen_parser.add_argument("--no-restart-memory", action="store_true", help="内存超限不自动重启")
    gen_parser.add_argument("--interval", type=int, default=30, help="监控间隔（秒）")

    # explain 子命令
    exp_parser = subparsers.add_parser("explain", help="解释 god 命令")
    exp_parser.add_argument("command_text", help="god 命令行文本")

    # diagnose 子命令
    diag_parser = subparsers.add_parser("diagnose", help="诊断 god 日志")
    diag_parser.add_argument("--file", help="日志文件路径（不提供则从 stdin 读取）")

    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="生成批量配置模板")
    batch_parser.add_argument("--json", required=True, help="JSON 格式的进程列表")

    # practices 子命令
    subparsers.add_parser("practices", help="查看最佳实践建议")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 无子命令
    if not args.command:
        parser.print_help()
        return

    # 执行子命令
    try:
        if args.command == "generate":
            config = generate_god_config(
                args.name,
                args.command,
                log_file=args.log,
                pid_file=args.pid,
                memory_limit=args.memory,
                port=args.port,
                restart_on_memory=not args.no_restart_memory,
                interval=args.interval,
            )
            print(config)

        elif args.command == "explain":
            explanation = explain_god_command(args.command_text)
            print(explanation)

        elif args.command == "diagnose":
            if args.file:
                try:
                    with open(args.file, "r", encoding="utf-8") as f:
                        log_text = f.read()
                except FileNotFoundError:
                    error_exit("E006", f"文件不存在: {args.file}")
                except Exception as e:
                    error_exit("E010", f"读取文件失败: {e}")
            else:
                log_text = sys.stdin.read()

            result = diagnose_god_status(log_text)
            print(f"健康状态: {'✓ 正常' if result['healthy'] else '✗ 异常'}")
            print(f"摘要: {result['summary']}")
            if result["issues"]:
                print("\n发现的问题:")
                for issue in result["issues"]:
                    print(f"  - {issue}")
            if result["suggestions"]:
                print("\n建议:")
                for suggestion in result["suggestions"]:
                    print(f"  - {suggestion}")

        elif args.command == "batch":
            try:
                processes = json.loads(args.json)
            except json.JSONDecodeError:
                error_exit("E001", "JSON 格式错误")
            template = generate_batch_template(processes)
            print(template)

        elif args.command == "practices":
            practices = get_best_practices()
            for category, items in practices.items():
                print(f"\n【{category}】")
                for key, advice in items.items():
                    print(f"  {key}: {advice}")

    except SystemExit:
        raise
    except Exception as e:
        error_exit("E010", str(e))


if __name__ == "__main__":
    main()
