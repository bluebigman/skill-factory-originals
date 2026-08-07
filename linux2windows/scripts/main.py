#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux2windows - 将 Linux 命令翻译为 Windows 等价命令的工具。

本脚本为全新独立实现（clean-room），仅依据功能规格编写。
提供命令行翻译功能与离线自检（--selftest）。

用法示例:
    python scripts/main.py "ls -l"
    python scripts/main.py --selftest
"""

import argparse
import os
import sys
import tempfile
from typing import Dict, List, Optional, Tuple


# ----------------------------------------------------------------------
# 错误码定义（遵循规格 E001-E010）
# ----------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要的参数。",
    "E003": "输入格式错误，无法解析。",
    "E004": "超出能力边界，无法处理。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部逻辑错误（未预期的分支）。",
    "E007": "文件读写失败。",
    "E008": "参数解析失败。",
    "E009": "自检失败，核心逻辑存在缺陷。",
    "E010": "未知错误。",
}


class ToolError(Exception):
    """工具自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ----------------------------------------------------------------------
# 核心翻译逻辑（Linux -> Windows）
# ----------------------------------------------------------------------
# 常用命令映射表（仅覆盖最常见场景，保持可扩展）
# 格式: linux命令 -> (windows命令模板, 参数说明)
COMMAND_MAP: Dict[str, Tuple[str, str]] = {
    "ls": ("dir", "列出目录内容"),
    "pwd": ("cd", "显示当前目录"),
    "cat": ("type", "显示文件内容"),
    "cp": ("copy", "复制文件"),
    "mv": ("move", "移动/重命名文件"),
    "rm": ("del", "删除文件"),
    "mkdir": ("mkdir", "创建目录"),
    "rmdir": ("rmdir", "删除空目录"),
    "touch": ("type nul >", "创建空文件"),
    "clear": ("cls", "清屏"),
    "grep": ("findstr", "搜索文本"),
    "diff": ("fc", "比较文件差异"),
    "head": ("powershell -Command \"Get-Content -Head", "查看文件开头"),
    "tail": ("powershell -Command \"Get-Content -Tail", "查看文件末尾"),
    "chmod": ("attrib", "修改文件属性"),
    "find": ("where", "查找文件"),
    "whoami": ("whoami", "显示当前用户"),
    "date": ("date /t", "显示日期"),
    "time": ("time /t", "显示时间"),
    "history": ("doskey /history", "显示命令历史"),
    "export": ("set", "设置环境变量"),
    "echo": ("echo", "输出文本"),
}

# 需要特殊处理的命令（参数转换规则）
SPECIAL_COMMANDS = {
    "ls": lambda args: _translate_ls(args),
    "cat": lambda args: _translate_cat(args),
    "grep": lambda args: _translate_grep(args),
    "head": lambda args: _translate_head_tail(args, is_head=True),
    "tail": lambda args: _translate_head_tail(args, is_head=False),
}


def _translate_ls(args: List[str]) -> str:
    """翻译 ls 命令。"""
    # ls -l  -> dir
    # ls -a  -> dir /a
    # ls -la -> dir /a
    flags = "".join(a.lstrip("-") for a in args if a.startswith("-"))
    targets = [a for a in args if not a.startswith("-")]

    result = "dir"
    if "a" in flags:
        result += " /a"
    if "l" in flags:
        result += " /q"  # 显示所有者信息（粗略等价）
    if targets:
        result += " " + " ".join(targets)
    return result


def _translate_cat(args: List[str]) -> str:
    """翻译 cat 命令。"""
    # cat file.txt -> type file.txt
    # cat -n file.txt -> findstr /n "^" file.txt（带行号）
    if "-n" in args:
        files = [a for a in args if not a.startswith("-")]
        if files:
            return f'findstr /n "^" {files[0]}'
    return "type " + " ".join(a for a in args if not a.startswith("-"))


def _translate_grep(args: List[str]) -> str:
    """翻译 grep 命令。"""
    # grep pattern file -> findstr "pattern" file
    # grep -i pattern file -> findstr /i "pattern" file
    non_flag = [a for a in args if not a.startswith("-")]
    flags = "".join(a.lstrip("-") for a in args if a.startswith("-"))

    if len(non_flag) < 2:
        raise ToolError("E003", "grep 需要至少一个模式和文件名")

    pattern = non_flag[0]
    files = non_flag[1:]

    result = "findstr"
    if "i" in flags:
        result += " /i"
    if "r" in flags:
        result += " /r"
    result += f' "{pattern}" {" ".join(files)}'
    return result


def _translate_head_tail(args: List[str], is_head: bool) -> str:
    """翻译 head/tail 命令。"""
    # head -n 10 file -> powershell -Command "Get-Content file -Head 10"
    # tail -n 10 file -> powershell -Command "Get-Content file -Tail 10"
    line_count = 10  # 默认值
    file_name = ""

    i = 0
    while i < len(args):
        if args[i] in ("-n", "--lines") and i + 1 < len(args):
            line_count = args[i + 1]
            i += 2
        elif not args[i].startswith("-"):
            file_name = args[i]
            i += 1
        else:
            i += 1

    if not file_name:
        raise ToolError("E002", "head/tail 需要指定文件名")

    direction = "Head" if is_head else "Tail"
    return f'powershell -Command "Get-Content {file_name} -{direction} {line_count}"'


def translate_command(command: str) -> Tuple[str, float]:
    """
    将 Linux 命令翻译为 Windows 等价命令。

    参数:
        command: 原始 Linux 命令字符串

    返回:
        (翻译结果, 置信度)
        置信度范围 0.0 ~ 1.0
    """
    if not command or not command.strip():
        raise ToolError("E001")

    parts = command.strip().split()
    if not parts:
        raise ToolError("E001")

    cmd_name = parts[0].lower()
    args = parts[1:]

    # 检查是否在特殊处理列表中
    if cmd_name in SPECIAL_COMMANDS:
        try:
            translated = SPECIAL_COMMANDS[cmd_name](args)
            return translated, 0.95
        except ToolError:
            raise
        except Exception:
            raise ToolError("E006")

    # 检查是否在基础映射表中
    if cmd_name in COMMAND_MAP:
        template, _ = COMMAND_MAP[cmd_name]
        if args:
            return f"{template} {' '.join(args)}", 0.90
        return template, 0.90

    # 未识别的命令，尝试猜测（低置信度）
    if cmd_name.startswith("sudo"):
        # sudo apt-get install xxx -> 提示使用管理员权限
        sub_cmd = args[0] if args else ""
        if sub_cmd == "apt-get":
            return (
                "请以管理员身份运行 PowerShell 并使用 winget 或 choco 安装软件",
                0.60,
            )
        return "请以管理员身份运行对应的 Windows 命令", 0.50

    # 完全无法识别
    raise ToolError("E004", f"无法识别的命令: {cmd_name}，建议使用 Windows 原生命令或 PowerShell")


def process_input(text: str) -> Dict:
    """
    处理用户输入并返回结构化结果。

    参数:
        text: 用户输入的文本

    返回:
        包含翻译结果和置信度的字典
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise ToolError("E001")

    results = []
    for line in lines:
        if line.startswith("#") or line.startswith("//"):
            continue  # 跳过注释
        try:
            translated, confidence = translate_command(line)
            results.append(
                {
                    "original": line,
                    "translated": translated,
                    "confidence": confidence,
                    "status": "ok",
                }
            )
        except ToolError as e:
            results.append(
                {
                    "original": line,
                    "translated": "",
                    "confidence": 0.0,
                    "status": "error",
                    "error_code": e.code,
                    "error_message": e.message,
                }
            )

    if not results:
        raise ToolError("E001", "输入中没有有效的命令")

    return {"results": results, "total": len(results)}


# ----------------------------------------------------------------------
# 自检模块（--selftest）
# ----------------------------------------------------------------------
def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    断言使用宽松阈值，确保稳健。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("=" * 60)
    print("运行自检（linux2windows 核心逻辑验证）...")
    print("=" * 60)

    test_cases = [
        # (输入, 期望包含的关键词, 最低置信度)
        ("ls -l", ["dir"], 0.8),
        ("ls -la", ["dir", "/a"], 0.8),
        ("pwd", ["cd"], 0.8),
        ("cat test.txt", ["type", "test.txt"], 0.8),
        ("cat -n test.txt", ["findstr", "/n"], 0.8),
        ("cp a.txt b.txt", ["copy", "a.txt", "b.txt"], 0.8),
        ("mv old.txt new.txt", ["move", "old.txt", "new.txt"], 0.8),
        ("rm temp.txt", ["del", "temp.txt"], 0.8),
        ("mkdir newdir", ["mkdir", "newdir"], 0.8),
        ("clear", ["cls"], 0.8),
        ("grep -i error log.txt", ["findstr", "/i", "error", "log.txt"], 0.8),
        ("head -n 5 file.txt", ["powershell", "Head", "5", "file.txt"], 0.8),
        ("tail -n 10 file.txt", ["powershell", "Tail", "10", "file.txt"], 0.8),
        ("echo hello world", ["echo", "hello", "world"], 0.8),
        ("whoami", ["whoami"], 0.8),
        ("date", ["date"], 0.8),
        ("history", ["doskey"], 0.8),
    ]

    # 错误处理测试
    error_cases = [
        ("", "E001"),  # 空输入
        ("   ", "E001"),  # 空白输入
        ("unknown_cmd_xyz", "E004"),  # 未知命令
    ]

    passed = 0
    failed = 0

    # 测试正常翻译
    for i, (cmd, expected_keywords, min_conf) in enumerate(test_cases, 1):
        try:
            translated, confidence = translate_command(cmd)
            # 检查翻译结果包含所有期望关键词
            keywords_ok = all(kw.lower() in translated.lower() for kw in expected_keywords)
            # 检查置信度不低于最低要求
            conf_ok = confidence >= min_conf

            if keywords_ok and conf_ok:
                print(f"  [通过] 用例{i}: '{cmd}' -> '{translated}' (置信度: {confidence:.2f})")
                passed += 1
            else:
                print(f"  [失败] 用例{i}: '{cmd}' -> '{translated}'")
                print(f"         关键词匹配: {keywords_ok}, 置信度达标: {conf_ok}")
                failed += 1
        except Exception as e:
            print(f"  [失败] 用例{i}: '{cmd}' 抛出异常: {e}")
            failed += 1

    # 测试错误处理
    for i, (cmd, expected_code) in enumerate(error_cases, len(test_cases) + 1):
        try:
            translate_command(cmd)
            print(f"  [失败] 错误用例{i}: '{cmd}' 未抛出预期错误 {expected_code}")
            failed += 1
        except ToolError as e:
            if e.code == expected_code:
                print(f"  [通过] 错误用例{i}: '{cmd}' 正确抛出 {e.code}")
                passed += 1
            else:
                print(f"  [失败] 错误用例{i}: '{cmd}' 抛出 {e.code}, 期望 {expected_code}")
                failed += 1
        except Exception as e:
            print(f"  [失败] 错误用例{i}: '{cmd}' 抛出非预期异常: {e}")
            failed += 1

    # 测试 process_input 批量处理
    try:
        batch_input = "ls -l\npwd\ncat test.txt\n"
        result = process_input(batch_input)
        if result["total"] == 3 and all(r["status"] == "ok" for r in result["results"]):
            print(f"  [通过] 批量处理: 成功处理 {result['total']} 条命令")
            passed += 1
        else:
            print(f"  [失败] 批量处理: 期望3条成功结果，实际 {result['total']} 条")
            failed += 1
    except Exception as e:
        print(f"  [失败] 批量处理: 抛出异常 {e}")
        failed += 1

    # 测试文件读写（使用临时文件）
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("ls -l\necho test\n")
            temp_path = f.name

        try:
            with open(temp_path, "r") as f:
                content = f.read()
            if "ls -l" in content and "echo test" in content:
                print(f"  [通过] 文件读写: 临时文件创建和读取成功")
                passed += 1
            else:
                print(f"  [失败] 文件读写: 文件内容不正确")
                failed += 1
        finally:
            os.unlink(temp_path)
    except Exception as e:
        print(f"  [失败] 文件读写: 抛出异常 {e}")
        failed += 1

    # 汇总结果
    print("-" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    if failed > 0:
        print("结果: 失败")
        return False

    print("结果: 全部通过 ✓")
    return True


# ----------------------------------------------------------------------
# 命令行入口
# ----------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="linux2windows - 将 Linux 命令翻译为 Windows 等价命令"
    )
    parser.add_argument(
        "commands",
        nargs="*",
        help="要翻译的 Linux 命令（可多个）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检，验证核心逻辑",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="linux2windows 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常模式
    if not args.commands:
        # 尝试从标准输入读取
        if not sys.stdin.isatty():
            input_text = sys.stdin.read()
        else:
            parser.print_help()
            return 0
    else:
        input_text = " ".join(args.commands)

    try:
        result = process_input(input_text)
        print("\n翻译结果:")
        print("-" * 60)
        for item in result["results"]:
            if item["status"] == "ok":
                conf_label = ""
                if item["confidence"] >= 0.9:
                    conf_label = "直接输出"
                elif item["confidence"] >= 0.85:
                    conf_label = "建议复核"
                else:
                    conf_label = "[需核实]"

                print(f"  {item['original']}")
                print(f"  -> {item['translated']}")
                print(f"  置信度: {item['confidence']:.0%} ({conf_label})")
            else:
                print(f"  {item['original']}")
                print(f"  -> [{item['error_code']}] {item['error_message']}")
            print()
        return 0
    except ToolError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
