#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruby-git — 基于 Ruby 的 Git 仓库操作封装（clean-room 独立实现）

本脚本依据功能规格重新实现，不复制任何既有代码。
提供命令行接口，简化日常 Git 版本控制任务。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "Git 命令执行失败",
    "E003": "指定的路径不存在或不是有效目录",
    "E004": "指定的文件不存在",
    "E005": "远程仓库操作失败",
    "E006": "配置读取失败",
    "E007": "分支操作失败",
    "E008": "自检失败",
    "E009": "提交操作失败",
    "E010": "未知错误",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出程序"""
    err_msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        print(f"[错误 {code}] {err_msg}: {message}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {err_msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# Git 命令执行封装
# ============================================================
class GitRunner:
    """Git 命令执行器，封装所有 git 调用"""

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path

    def _build_cmd(self, args: List[str]) -> List[str]:
        """构建 git 命令列表"""
        cmd = ["git"]
        if self.repo_path:
            cmd.extend(["-C", self.repo_path])
        cmd.extend(args)
        return cmd

    def run(self, args: List[str], check: bool = True) -> Tuple[int, str, str]:
        """执行 git 命令，返回 (返回码, stdout, stderr)"""
        try:
            result = subprocess.run(
                self._build_cmd(args),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if check and result.returncode != 0:
                error_exit("E002", f"git {' '.join(args)} 失败: {result.stderr.strip()}")
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            error_exit("E002", "git 命令执行超时")
        except FileNotFoundError:
            error_exit("E002", "未找到 git 命令，请确认已安装 Git")
        except Exception as e:
            error_exit("E002", f"执行异常: {str(e)}")

    def run_simple(self, args: List[str]) -> str:
        """执行命令并返回 stdout，失败时自动报错退出"""
        _, stdout, _ = self.run(args)
        return stdout.strip()


# ============================================================
# 核心功能实现
# ============================================================
class GitOps:
    """Git 操作核心类"""

    def __init__(self, repo_path: Optional[str] = None):
        self.runner = GitRunner(repo_path)
        self.repo_path = repo_path

    def _resolve_path(self, path: str) -> str:
        """解析路径，如果指定了仓库目录则相对于仓库目录"""
        if self.repo_path:
            return str(Path(self.repo_path) / path)
        return path

    # ---------- 仓库初始化 ----------
    def init(self, path: str) -> str:
        """初始化新 Git 仓库"""
        target = Path(path)
        if target.exists() and not target.is_dir():
            error_exit("E003", f"{path} 不是有效目录")
        target.mkdir(parents=True, exist_ok=True)
        self.runner = GitRunner(str(target))
        self.runner.run(["init"])
        return f"已初始化空仓库: {target}"

    # ---------- 状态查询 ----------
    def status(self) -> str:
        """查看仓库状态"""
        return self.runner.run_simple(["status"])

    # ---------- 文件暂存 ----------
    def add(self, files: List[str]) -> str:
        """将文件加入暂存区"""
        if not files:
            error_exit("E001", "add 命令需要指定文件")
        resolved_files = []
        for f in files:
            resolved = self._resolve_path(f)
            if not Path(resolved).exists():
                error_exit("E004", f"文件不存在: {f}")
            resolved_files.append(f)  # 传给 git 命令时使用相对路径
        self.runner.run(["add"] + resolved_files)
        return f"已暂存: {', '.join(files)}"

    def add_all(self) -> str:
        """暂存所有变更"""
        self.runner.run(["add", "-A"])
        return "已暂存所有变更"

    # ---------- 提交创建 ----------
    def commit(self, message: str) -> str:
        """创建新提交"""
        if not message:
            error_exit("E001", "commit 命令需要 -m 参数提供提交信息")
        self.runner.run(["commit", "-m", message])
        return f"提交成功: {message}"

    # ---------- 分支管理 ----------
    def branch_list(self) -> str:
        """列出所有分支"""
        return self.runner.run_simple(["branch"])

    def branch_create(self, name: str) -> str:
        """创建新分支"""
        if not name:
            error_exit("E001", "branch -c 需要分支名称")
        self.runner.run(["branch", name])
        return f"分支已创建: {name}"

    def branch_switch(self, name: str) -> str:
        """切换分支"""
        if not name:
            error_exit("E001", "checkout 需要分支名称")
        self.runner.run(["checkout", name])
        return f"已切换到分支: {name}"

    def branch_delete(self, name: str) -> str:
        """删除分支"""
        if not name:
            error_exit("E001", "branch -d 需要分支名称")
        self.runner.run(["branch", "-d", name])
        return f"分支已删除: {name}"

    # ---------- 日志查看 ----------
    def log(self, limit: int = 10) -> str:
        """查看提交日志"""
        if limit <= 0:
            error_exit("E001", "log --limit 需要正整数")
        return self.runner.run_simple(["log", f"-{limit}", "--oneline"])

    # ---------- 差异对比 ----------
    def diff(self, staged: bool = False) -> str:
        """查看差异"""
        if staged:
            return self.runner.run_simple(["diff", "--staged"])
        return self.runner.run_simple(["diff"])

    # ---------- 远程操作 ----------
    def remote_add(self, name: str, url: str) -> str:
        """添加远程仓库"""
        if not name or not url:
            error_exit("E001", "remote add 需要名称和 URL")
        self.runner.run(["remote", "add", name, url])
        return f"远程仓库已添加: {name} -> {url}"

    def push(self, remote: str = "origin", branch: str = "HEAD") -> str:
        """推送到远程"""
        self.runner.run(["push", remote, branch])
        return f"已推送到 {remote}/{branch}"

    def pull(self, remote: str = "origin", branch: str = "HEAD") -> str:
        """从远程拉取"""
        self.runner.run(["pull", remote, branch])
        return f"已从 {remote}/{branch} 拉取"

    # ---------- 配置读取 ----------
    def config_get(self, key: str, global_cfg: bool = False) -> str:
        """读取配置项"""
        if not key:
            error_exit("E001", "config 需要配置键名")
        cmd = ["config"]
        if global_cfg:
            cmd.append("--global")
        cmd.append("--get")
        cmd.append(key)
        return self.runner.run_simple(cmd)


# ============================================================
# 命令行接口
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="ruby-git",
        description="Git 仓库命令行版本控制工具（clean-room 实现）",
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("-C", "--directory", help="指定仓库目录")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # init
    p_init = subparsers.add_parser("init", help="初始化仓库")
    p_init.add_argument("path", help="仓库路径")

    # status
    subparsers.add_parser("status", help="查看状态")

    # add
    p_add = subparsers.add_parser("add", help="暂存文件")
    p_add.add_argument("files", nargs="*", help="要暂存的文件")
    p_add.add_argument("-A", "--all", action="store_true", help="暂存所有")

    # commit
    p_commit = subparsers.add_parser("commit", help="创建提交")
    p_commit.add_argument("-m", "--message", required=True, help="提交信息")

    # branch
    p_branch = subparsers.add_parser("branch", help="分支管理")
    p_branch.add_argument("-l", "--list", action="store_true", help="列出分支")
    p_branch.add_argument("-c", "--create", metavar="NAME", help="创建分支")
    p_branch.add_argument("-d", "--delete", metavar="NAME", help="删除分支")

    # checkout
    p_checkout = subparsers.add_parser("checkout", help="切换分支")
    p_checkout.add_argument("branch", help="目标分支")

    # log
    p_log = subparsers.add_parser("log", help="查看日志")
    p_log.add_argument("--limit", type=int, default=10, help="日志条数")

    # diff
    p_diff = subparsers.add_parser("diff", help="查看差异")
    p_diff.add_argument("--staged", action="store_true", help="查看暂存区差异")

    # remote
    p_remote = subparsers.add_parser("remote", help="远程操作")
    p_remote.add_argument("action", choices=["add", "push", "pull"], help="远程操作")
    p_remote.add_argument("name", nargs="?", default="origin", help="远程名称")
    p_remote.add_argument("url", nargs="?", help="远程 URL（add 时需要）")

    # config
    p_config = subparsers.add_parser("config", help="配置读取")
    p_config.add_argument("key", help="配置键名")
    p_config.add_argument("--global", dest="global_cfg", action="store_true", help="读取全局配置")

    return parser


def handle_command(args: argparse.Namespace, ops: GitOps) -> str:
    """处理具体命令"""
    cmd = args.command

    if cmd == "init":
        return ops.init(args.path)
    elif cmd == "status":
        return ops.status()
    elif cmd == "add":
        if args.all:
            return ops.add_all()
        return ops.add(args.files)
    elif cmd == "commit":
        return ops.commit(args.message)
    elif cmd == "branch":
        if args.list:
            return ops.branch_list()
        elif args.create:
            return ops.branch_create(args.create)
        elif args.delete:
            return ops.branch_delete(args.delete)
        else:
            error_exit("E001", "branch 需要指定操作")
    elif cmd == "checkout":
        return ops.branch_switch(args.branch)
    elif cmd == "log":
        return ops.log(args.limit)
    elif cmd == "diff":
        return ops.diff(args.staged)
    elif cmd == "remote":
        if args.action == "add":
            if not args.url:
                error_exit("E001", "remote add 需要 URL")
            return ops.remote_add(args.name, args.url)
        elif args.action == "push":
            return ops.push(args.name)
        elif args.action == "pull":
            return ops.pull(args.name)
    elif cmd == "config":
        return ops.config_get(args.key, args.global_cfg)
    else:
        error_exit("E001", f"未知命令: {cmd}")


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> None:
    """内置自检：在临时目录中创建仓库并验证核心功能"""
    print("=== ruby-git 自检开始 ===")
    temp_dir = tempfile.mkdtemp(prefix="ruby_git_selftest_")
    try:
        # 1. 初始化仓库
        ops = GitOps()
        result = ops.init(temp_dir)
        assert "已初始化" in result, f"初始化失败: {result}"
        print("[PASS] 仓库初始化")

        # 2. 创建测试文件
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("测试内容\n", encoding="utf-8")
        print("[PASS] 创建测试文件")

        # 3. 暂存文件
        ops = GitOps(temp_dir)
        result = ops.add(["test.txt"])  # 使用相对路径
        assert "已暂存" in result, f"暂存失败: {result}"
        print("[PASS] 文件暂存")

        # 4. 创建提交
        result = ops.commit("自检提交")
        assert "提交成功" in result, f"提交失败: {result}"
        print("[PASS] 提交创建")

        # 5. 查看日志
        log_output = ops.log(limit=5)
        assert "自检提交" in log_output, f"日志异常: {log_output}"
        print("[PASS] 日志查看")

        # 6. 状态查询
        status_output = ops.status()
        assert "On branch" in status_output, f"状态异常: {status_output}"
        print("[PASS] 状态查询")

        # 7. 分支操作
        ops.branch_create("feature-test")
        ops.branch_switch("feature-test")
        branches = ops.branch_list()
        assert "feature-test" in branches, f"分支异常: {branches}"
        print("[PASS] 分支管理")

        # 8. 差异对比
        test_file.write_text("修改内容\n", encoding="utf-8")
        diff_output = ops.diff()
        assert "修改内容" in diff_output, f"差异异常: {diff_output}"
        print("[PASS] 差异对比")

        # 9. 配置读取
        ops.commit("配置测试提交")
        config_value = ops.config_get("user.name", global_cfg=True)
        print(f"[INFO] 全局配置 user.name = {config_value or '(未设置)'}")
        print("[PASS] 配置读取")

        print("\n=== 全部自检通过 ===")
    except AssertionError as e:
        print(f"\n[FAIL] 自检失败: {e}", file=sys.stderr)
        error_exit("E008", str(e))
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n[FAIL] 自检异常: {e}", file=sys.stderr)
        error_exit("E008", str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("[INFO] 清理临时目录完成")


# ============================================================
# 主入口
# ============================================================
def main() -> None:
    """主程序入口"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 需要子命令
    if not args.command:
        parser.print_help()
        error_exit("E001", "缺少子命令")

    # 根据 -C 参数决定仓库路径
    repo_path = args.directory

    try:
        ops = GitOps(repo_path)
        result = handle_command(args, ops)
        print(result)
    except SystemExit:
        raise
    except Exception as e:
        error_exit("E010", str(e))


if __name__ == "__main__":
    main()
