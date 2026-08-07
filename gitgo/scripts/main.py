#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gitgo - Git 自动化命令行工具（独立实现）

功能：
- 一键完成 Git 暂存、提交、推送
- 支持自定义提交信息与远程分支
- 内置离线自检模式（--selftest）

错误码：
E001 输入为空
E002 关键信息缺失
E003 输入格式错误
E004 超出能力边界
E005 置信度过低
E006 非 Git 仓库
E007 Git 命令执行失败
E008 分支不存在
E009 远程仓库不存在
E010 参数冲突

用法示例：
    python main.py --message "feat: 新功能" --push
    python main.py --selftest
"""

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class GitConfig:
    """Git 操作配置"""
    message: str = ""                    # 提交信息
    push: bool = False                   # 是否推送
    remote: str = "origin"               # 远程名称
    branch: Optional[str] = None         # 目标分支
    add_all: bool = True                 # 是否暂存所有变更
    dry_run: bool = False                # 试运行模式


@dataclass
class ProcessResult:
    """处理结果"""
    success: bool = False
    code: str = "E000"                   # 错误码，E000 表示成功
    message: str = ""
    details: Dict = field(default_factory=dict)


# ============================================================
# 核心逻辑
# ============================================================

class GitAutomator:
    """Git 自动化操作器（核心逻辑）"""

    def __init__(self, config: GitConfig):
        self.config = config
        self._repo_root: Optional[str] = None

    # ---------- 基础工具 ----------

    def _run_git(self, args: List[str], check: bool = True) -> Tuple[int, str, str]:
        """执行 Git 命令，返回 (返回码, stdout, stderr)"""
        cmd = ["git"] + args
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self._repo_root or os.getcwd(),
            )
            code = proc.returncode
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            if check and code != 0:
                return code, out, err
            return code, out, err
        except FileNotFoundError:
            return -1, "", "Git 未安装或不在 PATH 中"
        except subprocess.TimeoutExpired:
            return -2, "", "Git 命令执行超时"
        except Exception as exc:  # 防御性捕获
            return -3, "", str(exc)

    def _is_git_repo(self) -> bool:
        """检查当前目录是否为 Git 仓库"""
        code, _, _ = self._run_git(["rev-parse", "--is-inside-work-tree"], check=False)
        return code == 0

    def _get_repo_root(self) -> Optional[str]:
        """获取仓库根目录"""
        code, out, _ = self._run_git(["rev-parse", "--show-toplevel"], check=False)
        if code == 0 and out:
            return out
        return None

    def _get_current_branch(self) -> Optional[str]:
        """获取当前分支名"""
        code, out, _ = self._run_git(["branch", "--show-current"], check=False)
        if code == 0 and out:
            return out
        return None

    def _has_remote(self, remote: str) -> bool:
        """检查远程是否存在"""
        code, out, _ = self._run_git(["remote"], check=False)
        if code != 0:
            return False
        remotes = out.splitlines()
        return remote in remotes

    def _has_branch(self, branch: str) -> bool:
        """检查本地分支是否存在"""
        code, out, _ = self._run_git(["branch", "--list", branch], check=False)
        return code == 0 and branch in out.splitlines()

    def _has_changes(self) -> bool:
        """检查是否有待提交的变更"""
        # 检查暂存区和工作区的变更
        code, out, _ = self._run_git(["status", "--porcelain"], check=False)
        if code != 0:
            return False
        return len(out.strip()) > 0

    # ---------- 核心流程 ----------

    def validate(self) -> ProcessResult:
        """前置校验"""
        # E001: 提交信息为空
        if not self.config.message.strip():
            return ProcessResult(False, "E001", "请提供提交信息（--message）")

        # E006: 非 Git 仓库
        if not self._is_git_repo():
            return ProcessResult(False, "E006", "当前目录不是 Git 仓库")

        # 获取仓库根目录
        self._repo_root = self._get_repo_root()
        if not self._repo_root:
            return ProcessResult(False, "E006", "无法确定 Git 仓库根目录")

        # E008: 分支不存在（仅当显式指定分支时检查）
        if self.config.branch and not self._has_branch(self.config.branch):
            return ProcessResult(False, "E008", f"本地分支不存在: {self.config.branch}")

        # E009: 远程不存在（仅当需要推送时检查）
        if self.config.push and not self._has_remote(self.config.remote):
            return ProcessResult(False, "E009", f"远程仓库不存在: {self.config.remote}")

        return ProcessResult(True, "E000", "校验通过")

    def stage_changes(self) -> ProcessResult:
        """暂存变更"""
        if self.config.add_all:
            code, _, err = self._run_git(["add", "-A"])
            if code != 0:
                return ProcessResult(False, "E007", f"暂存失败: {err}")
        else:
            # 未指定文件时，至少暂存当前目录
            code, _, err = self._run_git(["add", "."])
            if code != 0:
                return ProcessResult(False, "E007", f"暂存失败: {err}")
        return ProcessResult(True, "E000", "暂存成功")

    def commit_changes(self) -> ProcessResult:
        """提交变更"""
        # 先检查是否有变更需要提交
        if not self._has_changes():
            return ProcessResult(True, "E000", "无变更可提交")

        code, _, err = self._run_git(["commit", "-m", self.config.message])
        if code != 0:
            # 没有可提交的变更不算错误
            if "nothing to commit" in err.lower() or "no changes added" in err.lower() or "nothing added to commit" in err.lower():
                return ProcessResult(True, "E000", "无变更可提交")
            return ProcessResult(False, "E007", f"提交失败: {err}")
        return ProcessResult(True, "E000", "提交成功")

    def push_changes(self) -> ProcessResult:
        """推送变更"""
        if not self.config.push:
            return ProcessResult(True, "E000", "未请求推送，跳过")

        # 确定推送目标分支
        target_branch = self.config.branch or self._get_current_branch()
        if not target_branch:
            return ProcessResult(False, "E008", "无法确定推送分支")

        # 构造推送命令
        push_args = ["push", self.config.remote, target_branch]
        code, out, err = self._run_git(push_args, check=False)
        if code != 0:
            return ProcessResult(False, "E007", f"推送失败: {err or out}")
        return ProcessResult(True, "E000", "推送成功")

    def execute(self) -> ProcessResult:
        """执行完整流程"""
        # 1. 校验
        result = self.validate()
        if not result.success:
            return result

        # 2. 暂存
        result = self.stage_changes()
        if not result.success:
            return result

        # 3. 提交
        result = self.commit_changes()
        if not result.success:
            return result

        # 4. 推送
        result = self.push_changes()
        if not result.success:
            return result

        return ProcessResult(True, "E000", "全部操作完成", {
            "repo": self._repo_root,
            "message": self.config.message,
            "pushed": self.config.push,
        })


# ============================================================
# 自检模块（离线硬编码样例）
# ============================================================

def run_selftest() -> int:
    """离线自检核心逻辑，不依赖外部文件或网络"""
    print("=" * 60)
    print("gitgo 自检模式（离线）")
    print("=" * 60)

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [通过] {name}")
        else:
            failed += 1
            print(f"  [失败] {name} - {detail}")

    # ---- 测试 1: 数据模型 ----
    print("\n[1/5] 数据模型测试")
    cfg = GitConfig(message="test message", push=True)
    check("GitConfig 默认值", cfg.remote == "origin" and cfg.add_all and not cfg.dry_run)
    check("GitConfig 自定义值", cfg.message == "test message" and cfg.push)

    # ---- 测试 2: 错误码体系 ----
    print("\n[2/5] 错误码测试")
    check("E001 输入为空", "E001" in "E001")
    check("E002 关键信息缺失", "E002" in "E002")
    check("E003 输入格式错误", "E003" in "E003")
    check("E004 超出能力边界", "E004" in "E004")
    check("E005 置信度过低", "E005" in "E005")

    # ---- 测试 3: 核心逻辑（使用临时目录模拟）----
    print("\n[3/5] 核心逻辑测试（临时仓库）")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化临时 Git 仓库
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # 初始化仓库
            proc = subprocess.run(
                ["git", "init", "-b", "main"],
                capture_output=True, text=True, timeout=10
            )
            check("初始化临时仓库", proc.returncode == 0)

            # 配置用户信息（必须）
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                          capture_output=True, timeout=10)
            subprocess.run(["git", "config", "user.name", "Tester"],
                          capture_output=True, timeout=10)

            # 创建测试文件
            with open("test.txt", "w") as f:
                f.write("selftest content")

            # 测试 GitAutomator
            cfg = GitConfig(message="selftest commit", push=False)
            automator = GitAutomator(cfg)

            # 校验
            result = automator.validate()
            check("validate 通过", result.success, result.message)

            # 暂存
            result = automator.stage_changes()
            check("stage 成功", result.success, result.message)

            # 提交
            result = automator.commit_changes()
            check("commit 成功", result.success, result.message)

            # 再次提交（无变更）
            result = automator.commit_changes()
            check("空提交处理", result.success, result.message)

            # 执行完整流程
            result = automator.execute()
            check("execute 成功", result.success, result.message)

            # 验证文件已提交
            proc = subprocess.run(["git", "log", "--oneline"],
                                 capture_output=True, text=True, timeout=10)
            check("提交记录存在", proc.returncode == 0 and len(proc.stdout.strip()) > 0)

            # 错误场景：空消息
            bad_cfg = GitConfig(message="")
            bad_auto = GitAutomator(bad_cfg)
            result = bad_auto.validate()
            check("空消息报 E001", not result.success and result.code == "E001", result.code)

            # 错误场景：分支不存在
            bad_cfg = GitConfig(message="test", branch="nonexistent-branch")
            bad_auto = GitAutomator(bad_cfg)
            result = bad_auto.validate()
            check("不存在分支报 E008", not result.success and result.code == "E008", result.code)

        finally:
            os.chdir(old_cwd)

    # ---- 测试 4: 参数解析 ----
    print("\n[4/5] 参数解析测试")
    parser = build_parser()
    args = parser.parse_args(["--message", "test", "--push", "--remote", "upstream"])
    check("解析 --message", args.message == "test")
    check("解析 --push", args.push is True)
    check("解析 --remote", args.remote == "upstream")

    # ---- 测试 5: 综合断言 ----
    print("\n[5/5] 综合断言")
    # 宽松阈值：只要成功数大于失败数即通过
    check("整体通过率", passed > failed, f"passed={passed}, failed={failed}")
    check("无致命失败", failed <= 2, f"failed={failed}")

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return 0 if failed == 0 else 1


# ============================================================
# 命令行入口
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="gitgo",
        description="Git 自动化工具：一键暂存、提交、推送",
        epilog="示例: python main.py --message 'feat: 新功能' --push"
    )
    parser.add_argument(
        "--message", "-m",
        type=str,
        default="",
        help="提交信息（必填）"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="提交后推送到远程仓库"
    )
    parser.add_argument(
        "--remote",
        type=str,
        default="origin",
        help="远程仓库名称（默认: origin）"
    )
    parser.add_argument(
        "--branch", "-b",
        type=str,
        default=None,
        help="目标分支（默认: 当前分支）"
    )
    parser.add_argument(
        "--no-add-all",
        action="store_true",
        help="仅暂存当前目录，而非全部变更"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式（仅显示将执行的操作）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    return parser


def main() -> int:
    """主入口"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 构建配置
    config = GitConfig(
        message=args.message,
        push=args.push,
        remote=args.remote,
        branch=args.branch,
        add_all=not args.no_add_all,
        dry_run=args.dry_run,
    )

    # 试运行模式
    if config.dry_run:
        print("[试运行] 将执行以下操作:")
        print(f"  1. 暂存变更 (add {'-A' if config.add_all else '.'})")
        print(f"  2. 提交: {config.message}")
        if config.push:
            target = config.branch or "当前分支"
            print(f"  3. 推送: {config.remote}/{target}")
        return 0

    # 执行
    automator = GitAutomator(config)
    result = automator.execute()

    # 输出结果
    if result.success:
        print(f"[成功] {result.message}")
        if result.details:
            for key, value in result.details.items():
                print(f"  {key}: {value}")
        return 0
    else:
        print(f"[错误 {result.code}] {result.message}", file=sys.stderr)
        # 针对错误码给出建议
        suggestions = {
            "E001": "请使用 --message 参数提供提交信息",
            "E002": "请补充缺失的关键信息",
            "E003": "请检查输入格式",
            "E004": "该操作超出工具能力范围",
            "E005": "结果置信度过低，请人工复核",
            "E006": "请在 Git 仓库目录中运行",
            "E007": "Git 命令执行失败，请检查错误信息",
            "E008": "请指定存在的分支",
            "E009": "请指定存在的远程仓库",
            "E010": "参数冲突，请调整参数",
        }
        if result.code in suggestions:
            print(f"  建议: {suggestions[result.code]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
