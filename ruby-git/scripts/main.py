#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruby-git 工具的全新独立 Python 实现（clean-room 重写）。

仅依据功能规格设计，不参考任何既有代码。
提供 Git 仓库的创建、读取、操作、远程管理和高级操作封装。
"""

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union


# ============================================================
# 错误码定义
# ============================================================
class GitToolError(Exception):
    """统一的工具异常基类，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _err_invalid_args(msg: str = "参数错误") -> GitToolError:
    """参数校验失败。"""
    return GitToolError("E001", msg)


def _err_repo_not_found(msg: str = "仓库不存在") -> GitToolError:
    """仓库路径无效或不存在。"""
    return GitToolError("E002", msg)


def _err_git_exec(msg: str = "Git 命令执行失败") -> GitToolError:
    """Git 命令执行失败。"""
    return GitToolError("E003", msg)


def _err_git_output(msg: str = "Git 输出解析失败") -> GitToolError:
    """Git 输出解析失败。"""
    return GitToolError("E004", msg)


def _err_unsupported(msg: str = "不支持的操作") -> GitToolError:
    """不支持的功能。"""
    return GitToolError("E005", msg)


def _err_config(msg: str = "配置错误") -> GitToolError:
    """配置相关错误。"""
    return GitToolError("E006", msg)


def _err_network(msg: str = "网络或远程仓库错误") -> GitToolError:
    """网络/远程仓库相关错误。"""
    return GitToolError("E007", msg)


def _err_state(msg: str = "仓库状态错误") -> GitToolError:
    """仓库状态不符合预期。"""
    return GitToolError("E008", msg)


def _err_permission(msg: str = "权限不足") -> GitToolError:
    """文件系统或 Git 权限问题。"""
    return GitToolError("E009", msg)


def _err_internal(msg: str = "内部错误") -> GitToolError:
    """未预期的内部错误。"""
    return GitToolError("E010", msg)


# ============================================================
# 数据模型（与 Ruby 版对象模型对应）
# ============================================================
@dataclass
class Branch:
    """分支信息。"""
    name: str
    is_current: bool = False
    is_remote: bool = False


@dataclass
class Commit:
    """提交信息。"""
    hash: str
    author: str
    date: str
    message: str


@dataclass
class Tag:
    """标签信息。"""
    name: str
    commit_hash: str
    message: str = ""


@dataclass
class FileChange:
    """文件变更记录。"""
    path: str
    status: str  # A=新增, M=修改, D=删除, R=重命名
    additions: int = 0
    deletions: int = 0


@dataclass
class Repository:
    """Git 仓库对象。"""
    path: Path
    git_dir: Path = field(default=None, repr=False)
    _exists: bool = False

    def __post_init__(self):
        """初始化时校验路径。"""
        self.path = Path(self.path).resolve()
        self.git_dir = self.path / ".git"
        self._exists = self.git_dir.exists() or self._is_worktree()

    def _is_worktree(self) -> bool:
        """判断是否为 Git worktree。"""
        try:
            result = _run_git(self.path, ["rev-parse", "--is-inside-work-tree"])
            return result.strip() == "true"
        except GitToolError:
            return False

    # ---------- 创建类操作 ----------
    def init(self, bare: bool = False) -> "Repository":
        """初始化新仓库。"""
        if self._exists:
            raise _err_state(f"仓库已存在: {self.path}")
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            cmd = ["init"]
            if bare:
                cmd.append("--bare")
            _run_git(self.path, cmd)
            self._exists = True
            return self
        except GitToolError as e:
            raise e
        except Exception as e:
            raise _err_internal(f"初始化失败: {e}") from e

    @classmethod
    def clone(cls, url: str, dest: Optional[Union[str, Path]] = None) -> "Repository":
        """克隆远程仓库。"""
        dest_path = Path(dest) if dest else Path(url.rstrip("/")).name
        if dest_path.exists():
            raise _err_state(f"目标路径已存在: {dest_path}")
        try:
            _run_git(Path.cwd(), ["clone", url, str(dest_path)])
            return cls(dest_path)
        except GitToolError as e:
            raise e
        except Exception as e:
            raise _err_network(f"克隆失败: {e}") from e

    # ---------- 读取类操作 ----------
    def status(self) -> str:
        """获取仓库状态（简洁文本）。"""
        self._ensure_repo()
        try:
            return _run_git(self.path, ["status", "--short"])
        except GitToolError as e:
            raise e

    def log(self, max_count: int = 20) -> List[Commit]:
        """获取提交日志。"""
        self._ensure_repo()
        try:
            output = _run_git(self.path, [
                "log", f"--max-count={max_count}",
                "--pretty=format:%H|%an|%ad|%s", "--date=iso"
            ])
            commits: List[Commit] = []
            for line in output.strip().splitlines():
                if not line:
                    continue
                parts = line.split("|", 3)
                if len(parts) != 4:
                    raise _err_git_output(f"无法解析提交行: {line}")
                commits.append(Commit(
                    hash=parts[0], author=parts[1],
                    date=parts[2], message=parts[3]
                ))
            return commits
        except GitToolError as e:
            raise e

    def branches(self) -> List[Branch]:
        """列出所有分支。"""
        self._ensure_repo()
        try:
            output = _run_git(self.path, ["branch", "-a"])
            branches: List[Branch] = []
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                is_current = line.startswith("*")
                name = line.lstrip("* ").strip()
                is_remote = name.startswith("remotes/")
                branches.append(Branch(name=name, is_current=is_current, is_remote=is_remote))
            return branches
        except GitToolError as e:
            raise e

    def diff(self, target: str = "HEAD") -> List[FileChange]:
        """获取文件变更列表。"""
        self._ensure_repo()
        try:
            output = _run_git(self.path, ["diff", "--numstat", target])
            changes: List[FileChange] = []
            for line in output.splitlines():
                parts = line.split("\t")
                if len(parts) >= 3:
                    add, dele, path = parts[0], parts[1], parts[2]
                    status = "M"
                    if add == "-" and dele == "-":
                        status = "R"
                    elif int(dele or 0) > 0 and int(add or 0) == 0:
                        status = "D"
                    changes.append(FileChange(
                        path=path, status=status,
                        additions=int(add or 0), deletions=int(dele or 0)
                    ))
            return changes
        except GitToolError as e:
            raise e

    # ---------- 操作类 ----------
    def add(self, paths: Union[str, List[str]]) -> "Repository":
        """暂存文件。"""
        self._ensure_repo()
        if isinstance(paths, str):
            paths = [paths]
        try:
            _run_git(self.path, ["add"] + paths)
            return self
        except GitToolError as e:
            raise e

    def commit(self, message: str) -> str:
        """创建提交，返回提交哈希。"""
        self._ensure_repo()
        if not message:
            raise _err_invalid_args("提交信息不能为空")
        try:
            _run_git(self.path, ["commit", "-m", message])
            output = _run_git(self.path, ["rev-parse", "HEAD"])
            return output.strip()
        except GitToolError as e:
            raise e

    def checkout(self, branch: str, create: bool = False) -> "Repository":
        """切换分支。"""
        self._ensure_repo()
        try:
            cmd = ["checkout"]
            if create:
                cmd.append("-b")
            cmd.append(branch)
            _run_git(self.path, cmd)
            return self
        except GitToolError as e:
            raise e

    def merge(self, branch: str) -> str:
        """合并分支，返回结果信息。"""
        self._ensure_repo()
        try:
            return _run_git(self.path, ["merge", branch])
        except GitToolError as e:
            raise e

    # ---------- 远程管理 ----------
    def remotes(self) -> Dict[str, str]:
        """列出远程仓库。"""
        self._ensure_repo()
        try:
            output = _run_git(self.path, ["remote", "-v"])
            remotes: Dict[str, str] = {}
            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    remotes[parts[0]] = parts[1]
            return remotes
        except GitToolError as e:
            raise e

    def add_remote(self, name: str, url: str) -> "Repository":
        """添加远程仓库。"""
        self._ensure_repo()
        try:
            _run_git(self.path, ["remote", "add", name, url])
            return self
        except GitToolError as e:
            raise e

    def remove_remote(self, name: str) -> "Repository":
        """移除远程仓库。"""
        self._ensure_repo()
        try:
            _run_git(self.path, ["remote", "remove", name])
            return self
        except GitToolError as e:
            raise e

    def push(self, remote: str = "origin", branch: str = "HEAD") -> str:
        """推送到远程。"""
        self._ensure_repo()
        try:
            return _run_git(self.path, ["push", remote, branch])
        except GitToolError as e:
            raise e

    def pull(self, remote: str = "origin", branch: str = "HEAD") -> str:
        """从远程拉取。"""
        self._ensure_repo()
        try:
            return _run_git(self.path, ["pull", remote, branch])
        except GitToolError as e:
            raise e

    # ---------- 高级操作 ----------
    def tags(self) -> List[Tag]:
        """列出标签。"""
        self._ensure_repo()
        try:
            output = _run_git(self.path, ["tag", "-n"])
            tags: List[Tag] = []
            for line in output.splitlines():
                parts = line.split(" ", 1)
                name = parts[0]
                msg = parts[1] if len(parts) > 1 else ""
                try:
                    commit_hash = _run_git(self.path, ["rev-parse", name]).strip()
                except GitToolError:
                    commit_hash = ""
                tags.append(Tag(name=name, commit_hash=commit_hash, message=msg))
            return tags
        except GitToolError as e:
            raise e

    def create_tag(self, name: str, message: str = "") -> "Repository":
        """创建标签。"""
        self._ensure_repo()
        try:
            cmd = ["tag"]
            if message:
                cmd += ["-a", name, "-m", message]
            else:
                cmd.append(name)
            _run_git(self.path, cmd)
            return self
        except GitToolError as e:
            raise e

    # ---------- 内部工具 ----------
    def _ensure_repo(self) -> None:
        """确保仓库存在。"""
        if not self._exists:
            raise _err_repo_not_found(f"仓库不存在: {self.path}")


# ============================================================
# 底层 Git 命令执行器
# ============================================================
def _run_git(cwd: Path, args: List[str], check: bool = True) -> str:
    """执行 Git 命令，返回标准输出。"""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True,
            text=True, timeout=60
        )
    except FileNotFoundError as e:
        raise _err_git_exec("未找到 git 可执行文件，请先安装 Git") from e
    except subprocess.TimeoutExpired as e:
        raise _err_git_exec(f"Git 命令超时: {' '.join(cmd)}") from e
    except PermissionError as e:
        raise _err_permission(f"无权限执行 Git 命令: {cwd}") from e
    except Exception as e:
        raise _err_internal(f"执行 Git 命令异常: {e}") from e

    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        raise _err_git_exec(f"命令失败 (exit={result.returncode}): {' '.join(cmd)}\n{stderr}")

    return result.stdout


# ============================================================
# 命令行接口
# ============================================================
def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="ruby-git",
        description="Git 仓库操作封装工具（Python 实现）"
    )
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    parser.add_argument("--version", action="version", version="ruby-git 1.0.1 (python clean-room)")

    sub = parser.add_subparsers(dest="command", help="子命令")

    # init 命令
    p_init = sub.add_parser("init", help="初始化仓库")
    p_init.add_argument("path", nargs="?", default=".", help="仓库路径")
    p_init.add_argument("--bare", action="store_true", help="初始化裸仓库")

    # clone 命令
    p_clone = sub.add_parser("clone", help="克隆仓库")
    p_clone.add_argument("url", help="远程仓库 URL")
    p_clone.add_argument("dest", nargs="?", help="目标路径")

    # status 命令
    p_status = sub.add_parser("status", help="查看状态")
    p_status.add_argument("path", nargs="?", default=".", help="仓库路径")

    # log 命令
    p_log = sub.add_parser("log", help="查看日志")
    p_log.add_argument("path", nargs="?", default=".", help="仓库路径")
    p_log.add_argument("-n", type=int, default=20, help="日志条数")

    # branch 命令
    p_branch = sub.add_parser("branch", help="分支操作")
    p_branch.add_argument("path", nargs="?", default=".", help="仓库路径")
    p_branch.add_argument("--create", help="创建并切换分支")
    p_branch.add_argument("--list", action="store_true", help="列出分支")

    # commit 命令
    p_commit = sub.add_parser("commit", help="提交变更")
    p_commit.add_argument("path", nargs="?", default=".", help="仓库路径")
    p_commit.add_argument("-m", "--message", required=True, help="提交信息")

    # add 命令
    p_add = sub.add_parser("add", help="暂存文件")
    p_add.add_argument("path", nargs="?", default=".", help="仓库路径")
    p_add.add_argument("files", nargs="+", help="要暂存的文件")

    # remote 命令
    p_remote = sub.add_parser("remote", help="远程管理")
    p_remote.add_argument("path", nargs="?", default=".", help="仓库路径")
    p_remote.add_argument("--add", nargs=2, metavar=("NAME", "URL"), help="添加远程")
    p_remote.add_argument("--remove", metavar="NAME", help="移除远程")
    p_remote.add_argument("--list", action="store_true", help="列出远程")

    # tag 命令
    p_tag = sub.add_parser("tag", help="标签管理")
    p_tag.add_argument("path", nargs="?", default=".", help="仓库路径")
    p_tag.add_argument("--create", nargs="+", metavar="NAME", help="创建标签")
    p_tag.add_argument("--message", default="", help="标签信息")
    p_tag.add_argument("--list", action="store_true", help="列出标签")

    return parser.parse_args(argv)


def _handle_command(args: argparse.Namespace) -> int:
    """分发处理子命令。"""
    try:
        if args.command == "init":
            repo = Repository(args.path)
            repo.init(bare=args.bare)
            print(f"已初始化仓库: {repo.path}")

        elif args.command == "clone":
            repo = Repository.clone(args.url, args.dest)
            print(f"已克隆仓库: {repo.path}")

        elif args.command == "status":
            repo = Repository(args.path)
            print(repo.status() or "工作区干净")

        elif args.command == "log":
            repo = Repository(args.path)
            commits = repo.log(args.n)
            for c in commits:
                print(f"{c.hash[:8]} {c.author} {c.date} {c.message}")

        elif args.command == "branch":
            repo = Repository(args.path)
            if args.create:
                repo.checkout(args.create, create=True)
                print(f"已创建并切换到分支: {args.create}")
            else:
                for b in repo.branches():
                    marker = "*" if b.is_current else " "
                    print(f" {marker} {b.name}")

        elif args.command == "commit":
            repo = Repository(args.path)
            hash_val = repo.commit(args.message)
            print(f"提交成功: {hash_val[:8]}")

        elif args.command == "add":
            repo = Repository(args.path)
            repo.add(args.files)
            print(f"已暂存: {', '.join(args.files)}")

        elif args.command == "remote":
            repo = Repository(args.path)
            if args.add:
                repo.add_remote(args.add[0], args.add[1])
                print(f"已添加远程: {args.add[0]} -> {args.add[1]}")
            elif args.remove:
                repo.remove_remote(args.remove)
                print(f"已移除远程: {args.remove}")
            else:
                for name, url in repo.remotes().items():
                    print(f"{name}\t{url}")

        elif args.command == "tag":
            repo = Repository(args.path)
            if args.create:
                repo.create_tag(args.create[0], args.message)
                print(f"已创建标签: {args.create[0]}")
            else:
                for t in repo.tags():
                    print(f"{t.name}\t{t.commit_hash[:8]}\t{t.message}")

        else:
            raise _err_invalid_args(f"未知命令: {args.command}")

        return 0

    except GitToolError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未预期错误: {e}", file=sys.stderr)
        return 1


# ============================================================
# 自检模块
# ============================================================
def _selftest() -> int:
    """运行内置自检，不依赖外部文件/网络。"""
    print("开始自检...")
    errors = 0

    # 测试 1: 初始化仓库
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo = Repository(repo_path)
            repo.init()

            # 测试 2: 提交文件
            test_file = repo_path / "hello.txt"
            test_file.write_text("Hello, ruby-git!\n", encoding="utf-8")
            repo.add("hello.txt")
            commit_hash = repo.commit("初始提交")
            assert len(commit_hash) == 40, f"提交哈希长度异常: {len(commit_hash)}"

            # 测试 3: 读取日志
            commits = repo.log()
            assert len(commits) == 1, f"日志条数异常: {len(commits)}"
            assert commits[0].message == "初始提交", f"提交信息异常: {commits[0].message}"

            # 测试 4: 分支操作
            repo.checkout("dev", create=True)
            branches = repo.branches()
            branch_names = [b.name for b in branches]
            assert "dev" in branch_names, "未找到 dev 分支"
            assert any(b.is_current for b in branches if b.name == "dev"), "dev 分支应为当前分支"

            # 测试 5: 状态检查
            status_text = repo.status()
            assert "hello.txt" in status_text, "状态应包含 hello.txt"

            # 测试 6: 标签操作
            repo.create_tag("v1.0", "版本 1.0")
            tags = repo.tags()
            assert len(tags) == 1, f"标签数量异常: {len(tags)}"
            assert tags[0].name == "v1.0", f"标签名异常: {tags[0].name}"

            # 测试 7: 远程管理
            repo.add_remote("origin", "https://example.com/repo.git")
            remotes = repo.remotes()
            assert "origin" in remotes, "未找到 origin 远程"
            assert remotes["origin"] == "https://example.com/repo.git", "远程 URL 异常"
            repo.remove_remote("origin")
            remotes = repo.remotes()
            assert "origin" not in remotes, "origin 远程应已移除"

            # 测试 8: 错误处理
            try:
                repo.commit("")  # 空提交信息
                print("  [FAIL] 空提交信息未报错")
                errors += 1
            except GitToolError as e:
                assert e.code == "E001", f"错误码异常: {e.code}"

            # 测试 9: 不存在的仓库
            try:
                bad_repo = Repository(Path(tmpdir) / "nonexistent")
                bad_repo.status()
                print("  [FAIL] 不存在的仓库未报错")
                errors += 1
            except GitToolError as e:
                assert e.code == "E002", f"错误码异常: {e.code}"

            print("  [PASS] 仓库生命周期测试通过")

    except AssertionError as e:
        print(f"  [FAIL] 断言失败: {e}")
        errors += 1
    except GitToolError as e:
        print(f"  [FAIL] Git 错误: {e}")
        errors += 1
    except Exception as e:
        print(f"  [FAIL] 未预期错误: {e}")
        errors += 1

    if errors == 0:
        print("全部自检通过 ✅")
        return 0
    else:
        print(f"自检失败: {errors} 个错误 ❌")
        return 1


# ============================================================
# 入口
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    args = _parse_args(argv)

    if args.selftest:
        return _selftest()

    if not args.command:
        print("请指定子命令 (--help 查看帮助)", file=sys.stderr)
        return 1

    return _handle_command(args)


if __name__ == "__main__":
    sys.exit(main())
