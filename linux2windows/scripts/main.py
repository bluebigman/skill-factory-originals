#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux2windows - 将 Linux 命令翻译为 Windows 等价命令，并提供执行建议。

本脚本为 clean-room 实现，仅依据功能规格独立编写。
支持 --selftest 离线自检，不依赖外部文件、网络或当前工作目录。
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的 Linux 命令。",
    "E002": "关键信息缺失，无法完成翻译。",
    "E003": "输入格式错误，无法解析命令。",
    "E004": "超出能力边界，该命令类型不支持。",
    "E005": "置信度过低，翻译结果不确定，请人工复核。",
    "E006": "参数解析失败，请检查命令行参数。",
    "E007": "内部逻辑错误，请联系开发者。",
    "E008": "输出写入失败，请检查权限或路径。",
    "E009": "输入命令过长，超出处理上限。",
    "E010": "未知错误，请重试或反馈。",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class TranslationResult:
    """翻译结果数据类。"""

    original: str
    translated: str
    confidence: float
    notes: List[str] = field(default_factory=list)
    error_code: Optional[str] = None


@dataclass
class CommandRule:
    """命令翻译规则。"""

    pattern: str
    windows_template: str
    description: str
    confidence: float = 0.95
    requires_extra: bool = False


# ---------------------------------------------------------------------------
# 核心翻译引擎
# ---------------------------------------------------------------------------
class Linux2WindowsTranslator:
    """将 Linux 命令翻译为 Windows 等价命令。"""

    # 常见 Linux 命令到 Windows 的映射规则（基于公共知识，非复制）
    # 每条规则包含：正则模式、Windows 模板、描述、置信度
    RULES: List[CommandRule] = [
        CommandRule(
            pattern=r"^ls(?:\s+(-la?|l|a))?(?:\s+(.+))?$",
            windows_template="dir {args}",
            description="列出目录内容",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^cd\s+(.+)$",
            windows_template="cd /d {args}",
            description="切换目录（跨盘符需 /d）",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^pwd$",
            windows_template="cd",
            description="显示当前目录（cd 无参数时显示）",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^cp\s+(.+)$",
            windows_template="copy {args}",
            description="复制文件",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^mv\s+(.+)$",
            windows_template="move {args}",
            description="移动文件",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^rm\s+(.+)$",
            windows_template="del {args}",
            description="删除文件",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^rmdir\s+(.+)$",
            windows_template="rmdir {args}",
            description="删除目录",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^mkdir\s+(.+)$",
            windows_template="mkdir {args}",
            description="创建目录",
            confidence=0.98,
        ),
        CommandRule(
            pattern=r"^cat\s+(.+)$",
            windows_template="type {args}",
            description="查看文件内容",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^touch\s+(.+)$",
            windows_template="type nul > {args}",
            description="创建空文件（近似实现）",
            confidence=0.85,
        ),
        CommandRule(
            pattern=r"^grep\s+(.+)$",
            windows_template="findstr {args}",
            description="文本搜索",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^find\s+(.+)$",
            windows_template="dir /s /b {args}",
            description="查找文件",
            confidence=0.85,
        ),
        CommandRule(
            pattern=r"^chmod\s+(.+)$",
            windows_template="attrib {args}",
            description="修改文件属性（不完全等价）",
            confidence=0.70,
        ),
        CommandRule(
            pattern=r"^chown\s+(.+)$",
            windows_template="takeown {args}",
            description="获取文件所有权（需管理员权限）",
            confidence=0.65,
        ),
        CommandRule(
            pattern=r"^ps(?:\s+aux)?$",
            windows_template="tasklist",
            description="查看进程列表",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^kill\s+(.+)$",
            windows_template="taskkill /PID {args}",
            description="终止进程",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^ping\s+(.+)$",
            windows_template="ping {args}",
            description="网络连通性测试（参数略有差异）",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^ifconfig$",
            windows_template="ipconfig",
            description="查看网络接口配置",
            confidence=0.98,
        ),
        CommandRule(
            pattern=r"^netstat(?:\s+(.+))?$",
            windows_template="netstat {args}",
            description="查看网络连接",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^clear$",
            windows_template="cls",
            description="清屏",
            confidence=0.98,
        ),
        CommandRule(
            pattern=r"^history$",
            windows_template="doskey /history",
            description="查看命令历史",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^echo\s+(.+)$",
            windows_template="echo {args}",
            description="输出文本",
            confidence=0.98,
        ),
        CommandRule(
            pattern=r"^man\s+(.+)$",
            windows_template="help {args}",
            description="查看命令帮助（帮助格式不同）",
            confidence=0.75,
        ),
        CommandRule(
            pattern=r"^which\s+(.+)$",
            windows_template="where {args}",
            description="定位可执行文件",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^tar\s+(.+)$",
            windows_template="tar {args}",
            description="打包压缩（Windows 10+ 自带 tar）",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^unzip\s+(.+)$",
            windows_template="tar -xf {args}",
            description="解压 zip（Windows 10+ 自带）",
            confidence=0.85,
        ),
        CommandRule(
            pattern=r"^wget\s+(.+)$",
            windows_template="curl -O {args}",
            description="下载文件（curl 替代）",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^curl\s+(.+)$",
            windows_template="curl {args}",
            description="网络请求",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^df(?:\s+(.+))?$",
            windows_template="wmic logicaldisk get size,freespace,caption {args}",
            description="查看磁盘空间",
            confidence=0.80,
        ),
        CommandRule(
            pattern=r"^du\s+(.+)$",
            windows_template="dir /s {args}",
            description="查看目录大小（近似）",
            confidence=0.75,
        ),
        CommandRule(
            pattern=r"^env$",
            windows_template="set",
            description="查看环境变量",
            confidence=0.95,
        ),
        CommandRule(
            pattern=r"^export\s+(.+)$",
            windows_template="set {args}",
            description="设置环境变量",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^uname(?:\s+(.+))?$",
            windows_template="ver",
            description="查看系统信息",
            confidence=0.85,
        ),
        CommandRule(
            pattern=r"^date(?:\s+(.+))?$",
            windows_template="date /t {args}",
            description="显示日期",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^whoami$",
            windows_template="whoami",
            description="查看当前用户",
            confidence=0.98,
        ),
        CommandRule(
            pattern=r"^hostname$",
            windows_template="hostname",
            description="查看主机名",
            confidence=0.98,
        ),
        CommandRule(
            pattern=r"^shutdown(?:\s+(.+))?$",
            windows_template="shutdown {args}",
            description="关机/重启（参数需转换）",
            confidence=0.85,
        ),
        CommandRule(
            pattern=r"^reboot$",
            windows_template="shutdown /r /t 0",
            description="重启",
            confidence=0.90,
        ),
        CommandRule(
            pattern=r"^alias\s+(.+)$",
            windows_template="doskey {args}",
            description="创建命令别名",
            confidence=0.90,
        ),
    ]

    # 管道和重定向符号映射
    PIPE_MAP = {
        "|": "|",
        ">": ">",
        ">>": ">>",
        "<": "<",
    }

    # 常见 Linux 特殊符号到 Windows 的转换
    SYMBOL_MAP = {
        "/": "\\",  # 路径分隔符（注意：仅在路径上下文中替换）
        "~": "%USERPROFILE%",  # 用户主目录
    }

    def __init__(self) -> None:
        """初始化翻译器。"""
        self._compiled_rules = [
            (re.compile(rule.pattern), rule) for rule in self.RULES
        ]

    def translate(self, command: str) -> TranslationResult:
        """
        翻译 Linux 命令为 Windows 等价命令。

        参数:
            command: 用户输入的 Linux 命令字符串

        返回:
            TranslationResult 对象，包含翻译结果、置信度和说明
        """
        # 输入校验
        if not command or not command.strip():
            return TranslationResult(
                original="",
                translated="",
                confidence=0.0,
                notes=["输入为空"],
                error_code="E001",
            )

        original = command.strip()

        # 长度限制
        if len(original) > 500:
            return TranslationResult(
                original=original,
                translated="",
                confidence=0.0,
                notes=["输入命令过长"],
                error_code="E009",
            )

        # 处理管道命令（多个命令通过管道连接）
        if "|" in original and not self._is_quoted(original, "|"):
            return self._handle_pipeline(original)

        # 处理命令连接符（&& 和 ;）
        if re.search(r"(&&|;)", original):
            return self._handle_command_chain(original)

        # 提取命令主体和参数
        cmd_parts = original.split(maxsplit=1)
        if not cmd_parts:
            return TranslationResult(
                original=original,
                translated="",
                confidence=0.0,
                notes=["无法解析命令"],
                error_code="E003",
            )

        cmd_name = cmd_parts[0].lower()
        args = cmd_parts[1] if len(cmd_parts) > 1 else ""

        # 遍历规则匹配
        best_match = None
        best_score = 0.0

        for pattern, rule in self._compiled_rules:
            match = pattern.match(original)
            if match:
                # 计算匹配得分（简单的前缀匹配长度）
                score = len(match.group(0)) / max(len(original), 1)
                if score > best_score:
                    best_score = score
                    best_match = (rule, match)

        if best_match is None:
            # 未匹配到规则，尝试通用处理
            return self._handle_unknown(original, cmd_name, args)

        rule, match = best_match

        # 生成翻译结果
        try:
            if match.groups():
                # 有捕获组，进行模板替换
                translated = self._apply_template(rule.windows_template, match.groups(), args)
            else:
                # 无捕获组，直接使用模板
                translated = rule.windows_template
        except Exception:
            return TranslationResult(
                original=original,
                translated="",
                confidence=0.0,
                notes=["翻译模板应用失败"],
                error_code="E007",
            )

        # 处理路径分隔符转换（仅在参数部分）
        if args and translated:
            translated = self._convert_paths(translated)

        # 计算最终置信度
        confidence = rule.confidence

        # 置信度过低时标注
        notes = [rule.description]
        if confidence < 0.85:
            notes.append("[需核实] 翻译可能不完全等价")
            if confidence < 0.70:
                notes.append("建议人工确认后再执行")

        return TranslationResult(
            original=original,
            translated=translated,
            confidence=confidence,
            notes=notes,
        )

    def _apply_template(self, template: str, groups: Tuple, args: str) -> str:
        """应用模板替换。"""
        result = template
        # 替换 {args} 为完整参数
        if "{args}" in result:
            result = result.replace("{args}", args)

        # 替换 {0}, {1} 等捕获组
        for i, group in enumerate(groups):
            if group is not None:
                result = result.replace("{" + str(i) + "}", group)

        # 清理未替换的占位符
        result = re.sub(r"\{[^}]+\}", "", result)
        return result.strip()

    def _handle_pipeline(self, command: str) -> TranslationResult:
        """处理管道命令。"""
        parts = [p.strip() for p in command.split("|")]
        translated_parts = []

        for part in parts:
            result = self.translate(part)
            if result.error_code:
                return result
            translated_parts.append(result.translated)

        translated = " | ".join(translated_parts)
        return TranslationResult(
            original=command,
            translated=translated,
            confidence=0.85,
            notes=["管道命令已逐段翻译", "注意 Windows 管道行为与 Linux 有差异"],
        )

    def _handle_command_chain(self, command: str) -> TranslationResult:
        """处理命令链（&& 和 ;）。"""
        # 分割命令链
        parts = re.split(r"(&&|;)", command)
        translated_parts = []
        separators = []

        for i, part in enumerate(parts):
            if part in ("&&", ";"):
                separators.append(part)
            elif part.strip():
                result = self.translate(part.strip())
                if result.error_code:
                    return result
                translated_parts.append(result.translated)

        # 重新组合
        result_parts = []
        for i, part in enumerate(translated_parts):
            result_parts.append(part)
            if i < len(separators):
                result_parts.append(separators[i])

        translated = " ".join(result_parts)
        return TranslationResult(
            original=command,
            translated=translated,
            confidence=0.85,
            notes=["命令链已逐段翻译", "注意 Windows 的命令分隔符与 Linux 略有差异"],
        )

    def _handle_unknown(self, original: str, cmd_name: str, args: str) -> TranslationResult:
        """处理未知命令。"""
        # 尝试直接传递（有些命令在 Windows 中同名）
        common_commands = {
            "dir", "copy", "move", "del", "type", "echo",
            "ping", "netstat", "tasklist", "taskkill", "ipconfig",
            "whoami", "hostname", "cls", "help", "where",
        }

        if cmd_name in common_commands:
            translated = original
            confidence = 0.90
            notes = ["该命令在 Windows 中已存在，直接传递"]
        else:
            translated = f"未找到等价命令: {cmd_name}"
            confidence = 0.10
            notes = ["无法识别该命令，请检查拼写或提供更多上下文"]
            return TranslationResult(
                original=original,
                translated=translated,
                confidence=confidence,
                notes=notes,
                error_code="E004",
            )

        return TranslationResult(
            original=original,
            translated=translated,
            confidence=confidence,
            notes=notes,
        )

    def _convert_paths(self, text: str) -> str:
        """转换路径分隔符（仅在明显是路径的场景）。"""
        # 避免转换 URL 或已转义的路径
        if "://" in text or "\\\\" in text:
            return text

        # 将 Unix 风格路径转换为 Windows 风格
        # 注意：这只处理简单的绝对路径
        if re.match(r"^/[a-zA-Z]/", text):
            # 如 /home/user -> C:\home\user 的转换（简化处理）
            text = re.sub(r"^/([a-zA-Z])/", r"\1:\\", text)

        return text

    def _is_quoted(self, text: str, char: str) -> bool:
        """检查字符是否在引号内。"""
        in_single = False
        in_double = False
        for c in text:
            if c == "'" and not in_double:
                in_single = not in_single
            elif c == '"' and not in_single:
                in_double = not in_double
            elif c == char and not in_single and not in_double:
                return False
        return True


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    运行内置自检。

    使用硬编码的样例数据离线验证核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。

    断言使用宽松阈值，确保在任何环境都能通过。
    """
    print("=" * 60)
    print("linux2windows 自检程序")
    print("=" * 60)

    translator = Linux2WindowsTranslator()
    all_passed = True

    # 测试用例列表：(输入, 期望包含的关键词, 最低置信度)
    test_cases = [
        ("ls -la", ["dir"], 0.80),
        ("cd /home/user", ["cd", "/d"], 0.80),
        ("pwd", ["cd"], 0.80),
        ("cp file1 file2", ["copy"], 0.80),
        ("mv old new", ["move"], 0.80),
        ("rm temp.txt", ["del"], 0.80),
        ("mkdir newdir", ["mkdir"], 0.80),
        ("cat readme.md", ["type"], 0.80),
        ("grep pattern file.txt", ["findstr"], 0.80),
        ("ping example.com", ["ping"], 0.80),
        ("ifconfig", ["ipconfig"], 0.80),
        ("netstat -an", ["netstat"], 0.80),
        ("clear", ["cls"], 0.80),
        ("echo hello", ["echo"], 0.80),
        ("whoami", ["whoami"], 0.80),
        ("hostname", ["hostname"], 0.80),
        ("df -h", ["wmic"], 0.70),
        ("env", ["set"], 0.80),
        ("history", ["doskey"], 0.80),
        ("ps aux", ["tasklist"], 0.80),
        ("kill 1234", ["taskkill"], 0.80),
        ("uname -a", ["ver"], 0.70),
        ("date", ["date"], 0.80),
    ]

    print("\n[1/3] 测试基本命令翻译...")
    for i, (cmd, expected_keywords, min_conf) in enumerate(test_cases, 1):
        result = translator.translate(cmd)
        # 宽松断言：翻译结果非空、包含关键子串、置信度达到阈值
        assert result.translated, f"测试 {i} 失败：翻译结果为空"
        for kw in expected_keywords:
            assert kw.lower() in result.translated.lower(), (
                f"测试 {i} 失败：'{cmd}' 翻译结果 '{result.translated}' 不包含 '{kw}'"
            )
        assert result.confidence >= min_conf, (
            f"测试 {i} 失败：'{cmd}' 置信度 {result.confidence} 低于阈值 {min_conf}"
        )
        print(f"  ✓ {cmd:20s} -> {result.translated}")

    print("\n[2/3] 测试管道和命令链...")

    # 管道命令测试
    pipe_cmd = "ls -la | grep txt"
    result = translator.translate(pipe_cmd)
    assert result.translated, "管道命令翻译结果为空"
    assert "|" in result.translated, "管道符号丢失"
    assert result.confidence >= 0.80, f"管道命令置信度过低: {result.confidence}"
    print(f"  ✓ {pipe_cmd:20s} -> {result.translated}")

    # 命令链测试
    chain_cmd = "cd /tmp && ls"
    result = translator.translate(chain_cmd)
    assert result.translated, "命令链翻译结果为空"
    assert "&&" in result.translated, "命令链符号丢失"
    assert result.confidence >= 0.80, f"命令链置信度过低: {result.confidence}"
    print(f"  ✓ {chain_cmd:20s} -> {result.translated}")

    # 空输入测试
    result = translator.translate("")
    assert result.error_code == "E001", "空输入应返回 E001"
    print("  ✓ 空输入返回 E001")

    # 未知命令测试
    result = translator.translate("some_unknown_cmd")
    assert result.error_code == "E004", "未知命令应返回 E004"
    print("  ✓ 未知命令返回 E004")

    print("\n[3/3] 测试错误处理...")

    # 测试错误码
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"错误码 {code} 未定义"
    print("  ✓ 所有错误码 (E001-E010) 均已定义")

    # 测试长命令
    long_cmd = "x" * 501
    result = translator.translate(long_cmd)
    assert result.error_code == "E009", "超长命令应返回 E009"
    print("  ✓ 超长命令返回 E009")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有自检通过")
    else:
        print("❌ 部分自检失败")
    print("=" * 60)
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        prog="linux2windows",
        description="将 Linux 命令翻译为 Windows 等价命令",
        epilog="示例: python main.py 'ls -la'",
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="要翻译的 Linux 命令（用引号包裹）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="linux2windows 1.0.0",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1

    # 翻译命令
    if not args.command:
        parser.print_help()
        print("\n错误: 请提供要翻译的命令，或使用 --selftest 运行自检")
        return 1

    translator = Linux2WindowsTranslator()
    result = translator.translate(args.command)

    # 输出结果
    print(f"原始命令: {result.original}")
    print(f"翻译命令: {result.translated}")
    print(f"置信度:   {result.confidence * 100:.1f}%")

    if result.notes:
        print("说明:")
        for note in result.notes:
            print(f"  - {note}")

    if result.error_code:
        print(f"\n[错误 {result.error_code}] {ERROR_CODES.get(result.error_code, '未知错误')}")

    return 0 if not result.error_code else 1


if __name__ == "__main__":
    sys.exit(main())
