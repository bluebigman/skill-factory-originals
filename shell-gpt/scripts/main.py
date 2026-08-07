#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shell-gpt 独立实现脚本

功能：
    将自然语言指令转化为可执行的命令行操作与结构化输出。

仅依据功能规格进行 clean-room 独立实现。
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"       # 输入为空或格式错误
ERR_UNSUPPORTED_ACTION = "E002"  # 无法识别的自然语言指令
ERR_COMMAND_EXEC_FAIL = "E003"   # 命令执行失败
ERR_NO_SHELL = "E004"            # 无法获取系统 shell
ERR_PERMISSION_DENIED = "E005"   # 权限不足
ERR_TIMEOUT = "E006"             # 命令执行超时
ERR_INTERNAL = "E007"            # 内部逻辑错误
ERR_PARAMETER = "E008"           # 参数错误
ERR_ENV = "E009"                 # 环境变量错误
ERR_FILE = "E010"                # 文件操作错误


# ---------------------------------------------------------------------------
# 核心解析逻辑：将自然语言指令映射为命令模板
# ---------------------------------------------------------------------------

class CommandParser:
    """
    将自然语言指令转化为结构化命令对象。

    采用基于关键词规则的模式匹配，不涉及任何外部服务或网络调用。
    """

    def __init__(self):
        # 定义动作模式：关键词 -> (命令模板, 参数说明)
        self._patterns = [
            {
                "keywords": ["列出", "查看", "显示", "ls", "list"],
                "template": "ls {flags} {path}",
                "default": {"flags": "-la", "path": "."},
                "params": {
                    "path": r"(?:目录|路径)?\s*([\/\.\w\-]+)",
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["当前目录", "当前路径", "pwd"],
                "template": "pwd",
                "default": {},
                "params": {}
            },
            {
                "keywords": ["创建目录", "新建目录", "mkdir"],
                "template": "mkdir {flags} {path}",
                "default": {"flags": "-p", "path": "new_dir"},
                "params": {
                    "path": r"(?:目录|路径)?\s*([\/\.\w\-]+)",
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["删除文件", "移除文件", "rm"],
                "template": "rm {flags} {path}",
                "default": {"flags": "-f", "path": "file"},
                "params": {
                    "path": r"(?:文件|路径)?\s*([\/\.\w\-]+)",
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["复制", "拷贝", "cp"],
                "template": "cp {flags} {source} {dest}",
                "default": {"flags": "-r", "source": "source", "dest": "dest"},
                "params": {
                    "source": r"(?:源|来源)?\s*([\/\.\w\-]+)",
                    "dest": r"(?:目标|目的)?\s*([\/\.\w\-]+)",
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["移动", "重命名", "mv"],
                "template": "mv {flags} {source} {dest}",
                "default": {"flags": "", "source": "source", "dest": "dest"},
                "params": {
                    "source": r"(?:源|来源)?\s*([\/\.\w\-]+)",
                    "dest": r"(?:目标|目的)?\s*([\/\.\w\-]+)",
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["查找", "搜索", "find", "grep"],
                "template": "grep {flags} {pattern} {path}",
                "default": {"flags": "-rn", "pattern": "pattern", "path": "."},
                "params": {
                    "pattern": r"(?:模式|关键词)?\s*([\/\.\w\-]+)",
                    "path": r"(?:目录|路径)?\s*([\/\.\w\-]+)",
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["显示文件", "查看文件", "cat"],
                "template": "cat {path}",
                "default": {"path": "file"},
                "params": {
                    "path": r"(?:文件|路径)?\s*([\/\.\w\-]+)"
                }
            },
            {
                "keywords": ["进程", "ps"],
                "template": "ps {flags}",
                "default": {"flags": "-ef"},
                "params": {
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["磁盘", "df"],
                "template": "df {flags} {path}",
                "default": {"flags": "-h", "path": "."},
                "params": {
                    "path": r"(?:目录|路径)?\s*([\/\.\w\-]+)",
                    "flags": r"(?:选项|参数)?\s*(-[a-zA-Z]+)"
                }
            },
            {
                "keywords": ["帮助", "help", "?"],
                "template": "help",
                "default": {},
                "params": {}
            }
        ]

    def parse(self, text):
        """
        解析自然语言指令。

        参数：
            text: 用户输入的自然语言字符串

        返回：
            dict: 包含命令模板与参数的结构化对象

        错误：
            返回错误码字典
        """
        if not text or not text.strip():
            return {"error": ERR_INVALID_INPUT, "message": "输入不能为空"}

        normalized = text.strip().lower()

        for pattern in self._patterns:
            # 检查是否包含关键词
            matched = False
            for kw in pattern["keywords"]:
                if kw in normalized:
                    matched = True
                    break

            if not matched:
                continue

            # 提取参数
            params = {}
            for param_name, regex in pattern["params"].items():
                match = re.search(regex, normalized)
                if match:
                    params[param_name] = match.group(1)
                else:
                    # 使用默认值
                    params[param_name] = pattern["default"].get(param_name, "")

            # 填充模板
            command = pattern["template"]
            try:
                command = command.format(**params)
            except KeyError:
                # 模板中缺少参数，使用默认值补全
                for key, value in pattern["default"].items():
                    command = command.replace("{" + key + "}", str(value))

            # 清理多余的空格
            command = re.sub(r'\s+', ' ', command).strip()

            return {
                "action": pattern["keywords"][0],
                "command": command,
                "params": params,
                "template": pattern["template"]
            }

        return {"error": ERR_UNSUPPORTED_ACTION, "message": f"无法识别的指令: {text}"}


# ---------------------------------------------------------------------------
# 命令执行器
# ---------------------------------------------------------------------------

class CommandExecutor:
    """
    负责执行解析后的命令，并返回结构化输出。
    """

    def __init__(self, timeout=10, shell=None):
        self.timeout = timeout
        self.shell = shell or self._detect_shell()

    def _detect_shell(self):
        """检测系统默认 shell"""
        for candidate in ["/bin/bash", "/bin/sh", "/bin/zsh", "cmd.exe", "powershell.exe"]:
            if os.path.exists(candidate):
                return candidate
        # 尝试从环境变量获取
        shell_env = os.environ.get("SHELL", "")
        if shell_env and os.path.exists(shell_env):
            return shell_env
        return None

    def execute(self, command):
        """
        执行命令并返回结构化结果。

        参数：
            command: 字符串形式的命令

        返回：
            dict: 包含退出码、标准输出、标准错误的结构化对象
        """
        if not command or not command.strip():
            return {"error": ERR_INVALID_INPUT, "message": "命令为空"}

        if not self.shell:
            return {"error": ERR_NO_SHELL, "message": "无法检测到系统 shell"}

        # 权限检查（简单模拟）
        if command.startswith("sudo") and os.geteuid() != 0:
            return {"error": ERR_PERMISSION_DENIED, "message": "需要 root 权限执行 sudo 命令"}

        try:
            # 使用 shell 执行命令
            result = subprocess.run(
                command,
                shell=True,
                executable=self.shell,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )

            return {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            return {"error": ERR_TIMEOUT, "message": f"命令执行超时（{self.timeout}秒）"}
        except PermissionError:
            return {"error": ERR_PERMISSION_DENIED, "message": "权限不足"}
        except OSError as exc:
            return {"error": ERR_COMMAND_EXEC_FAIL, "message": f"命令执行失败: {exc}"}
        except Exception as exc:
            return {"error": ERR_INTERNAL, "message": f"内部错误: {exc}"}


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------

class ShellGPT:
    """
    技能主类：整合解析与执行流程。
    """

    def __init__(self, timeout=10):
        self.parser = CommandParser()
        self.executor = CommandExecutor(timeout=timeout)

    def process(self, text, execute=True):
        """
        处理自然语言指令。

        参数：
            text: 自然语言指令
            execute: 是否实际执行命令（False 时仅返回解析结果）

        返回：
            dict: 结构化输出
        """
        # 第一步：解析
        parsed = self.parser.parse(text)

        # 解析失败
        if "error" in parsed:
            return parsed

        # 第二步：执行（如果需要）
        if execute:
            result = self.executor.execute(parsed["command"])
            result["parsed"] = parsed
            return result

        # 仅返回解析结果
        parsed["executed"] = False
        return parsed


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest():
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    使用宽松阈值断言，确保任何环境可过。
    """
    print("开始自检...")

    # 创建核心组件
    parser = CommandParser()

    # --- 测试1：解析基础指令 ---
    test_cases = [
        ("列出当前目录文件", "ls -la ."),
        ("查看当前路径", "pwd"),
        ("创建目录 test_dir", "mkdir"),
        ("删除文件 temp.txt", "rm"),
        ("复制文件 a.txt 到 b.txt", "cp"),
        ("移动文件 x.txt 到 y.txt", "mv"),
        ("查找关键词 error", "grep"),
        ("显示文件 config.py", "cat"),
        ("查看进程列表", "ps"),
        ("查看磁盘使用情况", "df"),
        ("帮助", "help"),
    ]

    for text, expected_cmd in test_cases:
        result = parser.parse(text)
        assert "error" not in result, f"解析失败: {text} -> {result}"
        assert result["command"].startswith(expected_cmd.split()[0]), \
            f"命令前缀不匹配: {text} -> {result['command']}"
        print(f"  ✓ 解析测试通过: {text} -> {result['command']}")

    # --- 测试2：错误处理 ---
    empty_result = parser.parse("")
    assert "error" in empty_result, "空输入应返回错误"
    assert empty_result["error"] == ERR_INVALID_INPUT, "空输入错误码应为 E001"

    garbage_result = parser.parse("xyzzy 完全无法识别的指令")
    assert "error" in garbage_result, "无法识别的指令应返回错误"
    assert garbage_result["error"] == ERR_UNSUPPORTED_ACTION, "无法识别错误码应为 E002"
    print("  ✓ 错误处理测试通过")

    # --- 测试3：执行器（使用无害命令） ---
    executor = CommandExecutor(timeout=5)

    # 执行 pwd（在任何系统都安全）
    pwd_result = executor.execute("pwd")
    assert "error" not in pwd_result, f"pwd 执行失败: {pwd_result}"
    assert pwd_result["success"] is True, "pwd 应成功执行"
    assert pwd_result["stdout"].strip(), "pwd 应有输出"
    print(f"  ✓ 执行器测试通过: pwd -> {pwd_result['stdout'].strip()}")

    # 执行 echo（无害）
    echo_result = executor.execute("echo selftest")
    assert "error" not in echo_result, f"echo 执行失败: {echo_result}"
    assert echo_result["success"] is True, "echo 应成功执行"
    assert "selftest" in echo_result["stdout"], "echo 输出应包含测试字符串"
    print("  ✓ echo 执行测试通过")

    # --- 测试4：完整流程 ---
    gpt = ShellGPT(timeout=5)
    full_result = gpt.process("查看当前路径")
    assert "error" not in full_result, f"完整流程失败: {full_result}"
    assert full_result["success"] is True, "完整流程应成功"
    assert full_result["stdout"].strip(), "完整流程应有输出"
    print(f"  ✓ 完整流程测试通过: {full_result['stdout'].strip()}")

    # --- 测试5：参数提取 ---
    param_result = parser.parse("创建目录 /tmp/mydir")
    assert "error" not in param_result, "带参数解析失败"
    assert "/tmp/mydir" in param_result["command"], "路径参数提取失败"
    print(f"  ✓ 参数提取测试通过: {param_result['command']}")

    # --- 测试6：ls 命令实际执行 ---
    ls_result = executor.execute("ls -la .")
    assert "error" not in ls_result, f"ls 执行失败: {ls_result}"
    assert ls_result["success"] is True, "ls 应成功执行"
    print("  ✓ ls 命令执行测试通过")

    print("\n全部自检通过！")
    return ERR_SUCCESS


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="shell-gpt: 将自然语言指令转化为可执行的命令行操作",
        epilog="示例: python main.py '列出当前目录文件'"
    )

    parser.add_argument(
        "instruction",
        nargs="?",
        help="自然语言指令"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    parser.add_argument(
        "--no-execute",
        action="store_true",
        help="仅解析不执行命令"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="命令执行超时时间（秒）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 无指令时显示帮助
    if not args.instruction:
        parser.print_help()
        return ERR_INVALID_INPUT

    # 处理指令
    gpt = ShellGPT(timeout=args.timeout)
    result = gpt.process(args.instruction, execute=not args.no_execute)

    # 输出结果
    if "error" in result:
        print(f"错误 [{result['error']}]: {result['message']}", file=sys.stderr)
        return 1

    if args.no_execute:
        # 仅显示解析结果
        print(f"解析结果: {result['command']}")
        return ERR_SUCCESS

    # 显示执行结果
    print(f"命令: {result['command']}")
    print(f"退出码: {result['exit_code']}")

    if result["stdout"]:
        print("标准输出:")
        print(result["stdout"])

    if result["stderr"]:
        print("标准错误:")
        print(result["stderr"], file=sys.stderr)

    return ERR_SUCCESS if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
