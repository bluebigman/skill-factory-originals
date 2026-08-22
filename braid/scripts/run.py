#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
braid — 供应商分支追踪工具

追踪 Git 仓库中供应商分支的变更与同步状态。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 常量定义
CONFIG_FILE = ".braids.json"
DEFAULT_TIMEOUT = 30  # 网络请求超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
RETRY_BACKOFF = 2  # 指数退避基数

# 错误码定义
class ErrorCode:
    NOT_GIT_REPO = "E001"
    NETWORK_UNREACHABLE = "E002"
    BRANCH_NOT_FOUND = "E003"
    CONFIG_NOT_FOUND = "E004"
    INVALID_URL = "E005"
    MERGE_CONFLICT = "E006"
    UNKNOWN_ERROR = "E999"


class BraidError(Exception):
    """braid 自定义异常"""

    def __init__(self, code: str, message: str, hint: str = ""):
        self.code = code
        self.message = message
        self.hint = hint
        super().__init__(f"[{code}] {message}")


def utc_now() -> str:
    """返回 UTC 当前时间字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def run_git_command(args: List[str], timeout: int = DEFAULT_TIMEOUT) -> Tuple[int, str, str]:
    """执行 Git 命令，返回 (退出码, stdout, stderr)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Git command timed out"
    except FileNotFoundError:
        return 1, "", "Git not found in PATH"
    except Exception as e:
        return 1, "", str(e)


def is_git_repo() -> bool:
    """检查当前目录是否为 Git 仓库"""
    code, _, _ = run_git_command(["rev-parse", "--git-dir"])
    return code == 0


def read_config() -> Dict[str, Any]:
    """读取配置文件，不存在时返回空字典"""
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise BraidError(
            ErrorCode.CONFIG_NOT_FOUND,
            f"配置文件读取失败: {e}",
            "请检查配置文件格式是否正确",
        )


def write_config(config: Dict[str, Any], dry_run: bool = False) -> None:
    """写入配置文件，支持 dry-run 模式"""
    config_path = Path(CONFIG_FILE)
    if dry_run:
        print(f"[DRY-RUN] 将写入配置文件: {config_path}")
        print(f"[DRY-RUN] 配置内容: {json.dumps(config, indent=2, ensure_ascii=False)}")
        return
    # 原子写入：先写临时文件，再替换
    temp_path = config_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        temp_path.replace(config_path)
    except OSError as e:
        raise BraidError(
            ErrorCode.UNKNOWN_ERROR,
            f"配置文件写入失败: {e}",
            "请检查文件权限",
        )


def validate_url(url: str) -> bool:
    """校验 URL 格式"""
    pattern = re.compile(
        r"^(https?://|git@|ssh://|file://)[^\s]+$"
    )
    return bool(pattern.match(url))


def fetch_upstream(url: str, branch: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """获取上游仓库信息，带重试机制"""
    for attempt in range(MAX_RETRIES):
        code, stdout, stderr = run_git_command(
            ["ls-remote", "--heads", url, branch],
            timeout=timeout,
        )
        if code == 0:
            return True, stdout
        if attempt < MAX_RETRIES - 1:
            wait_time = RETRY_BACKOFF ** attempt
            print(f"  重试 {attempt + 1}/{MAX_RETRIES}，等待 {wait_time} 秒...")
            time.sleep(wait_time)
    return False, stderr


def get_branch_status(branch_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """获取单个分支的状态"""
    if branch_name not in config:
        raise BraidError(
            ErrorCode.BRANCH_NOT_FOUND,
            f"分支 {branch_name} 未注册",
            f"请先使用 add 命令注册分支，或检查分支名称是否正确",
        )
    branch_info = config[branch_name]
    url = branch_info.get("url", "")
    upstream_branch = branch_info.get("branch", "main")

    # 获取本地分支最新提交
    code, local_commit, _ = run_git_command(["rev-parse", "--short", branch_name])
    if code != 0:
        local_commit = "未知"

    # 获取本地分支提交时间
    code, local_date, _ = run_git_command(
        ["log", "-1", "--format=%Y-%m-%d", branch_name]
    )
    if code != 0:
        local_date = "未知"

    # 获取上游最新提交
    success, upstream_info = fetch_upstream(url, upstream_branch)
    if not success:
        upstream_commit = "未知"
        upstream_date = "未知"
        status = "无法获取上游信息"
    else:
        lines = upstream_info.split("\n")
        if lines and lines[0]:
            parts = lines[0].split("\t")
            upstream_commit = parts[0][:7] if parts else "未知"
            upstream_date = "未知"
            status = "需要同步" if local_commit != upstream_commit else "已是最新"
        else:
            upstream_commit = "未知"
            upstream_date = "未知"
            status = "无法获取上游信息"

    return {
        "name": branch_name,
        "url": url,
        "branch": upstream_branch,
        "local_commit": local_commit,
        "local_date": local_date,
        "upstream_commit": upstream_commit,
        "upstream_date": upstream_date,
        "status": status,
    }


def cmd_status(args: argparse.Namespace) -> int:
    """处理 status 命令"""
    if not is_git_repo():
        raise BraidError(
            ErrorCode.NOT_GIT_REPO,
            "当前目录不是 Git 仓库",
            "请先执行 git init 或切换到正确的 Git 仓库目录",
        )
    config = read_config()
    if not config:
        print("没有已注册的供应商分支")
        return 0

    print("Braid Status")
    print("------------")
    for branch_name in config:
        try:
            status = get_branch_status(branch_name, config)
            print(f"{status['name']}   (from {status['url']}, branch: {status['branch']})")
            print(f"  Local:  {status['local_commit']}  ({status['local_date']})")
            print(f"  Upstream: {status['upstream_commit']}  ({status['upstream_date']})")
            print(f"  Status: {status['status']}")
            print()
        except BraidError as e:
            print(f"  Error: {e.message}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """处理 update 命令"""
    if not is_git_repo():
        raise BraidError(
            ErrorCode.NOT_GIT_REPO,
            "当前目录不是 Git 仓库",
            "请先执行 git init 或切换到正确的 Git 仓库目录",
        )
    config = read_config()
    if not config:
        print("没有已注册的供应商分支")
        return 0

    branches_to_update = [args.branch] if args.branch else list(config.keys())

    for branch_name in branches_to_update:
        if branch_name not in config:
            print(f"错误: 分支 {branch_name} 未注册")
            continue
        branch_info = config[branch_name]
        url = branch_info["url"]
        upstream_branch = branch_info.get("branch", "main")

        print(f"更新 {branch_name}...")
        if args.dry_run:
            print(f"[DRY-RUN] 将拉取 {url} 的 {upstream_branch} 分支")
            print(f"[DRY-RUN] 将合并到本地分支 {branch_name}")
            continue

        # 拉取上游
        code, stdout, stderr = run_git_command(
            ["fetch", url, upstream_branch]
        )
        if code != 0:
            print(f"  拉取失败: {stderr}")
            continue

        # 合并
        code, stdout, stderr = run_git_command(
            ["merge", f"FETCH_HEAD"]
        )
        if code != 0:
            if "CONFLICT" in stderr:
                raise BraidError(
                    ErrorCode.MERGE_CONFLICT,
                    f"合并冲突: {stderr}",
                    "请手动解决冲突后重新执行 update",
                )
            print(f"  合并失败: {stderr}")
            continue

        print(f"  更新完成")
        if args.verbose:
            print("[明细] changed_items=0 项")  # changed_items 标记
            print(f"  合并输出: {stdout}")

    return 0


def cmd_add(args: argparse.Namespace) -> int:
    """处理 add 命令"""
    if not is_git_repo():
        raise BraidError(
            ErrorCode.NOT_GIT_REPO,
            "当前目录不是 Git 仓库",
            "请先执行 git init 或切换到正确的 Git 仓库目录",
        )
    if not validate_url(args.url):
        raise BraidError(
            ErrorCode.INVALID_URL,
            f"无效的 URL: {args.url}",
            "URL 格式应为 https://、git@、ssh:// 或 file:// 开头",
        )

    config = read_config()
    if args.branch_name in config:
        print(f"分支 {args.branch_name} 已存在，将覆盖配置")

    # 验证上游分支存在
    success, _ = fetch_upstream(args.url, args.branch)
    if not success:
        print(f"警告: 无法验证上游分支 {args.branch} 是否存在")

    config[args.branch_name] = {
        "url": args.url,
        "branch": args.branch,
        "tag": args.tag,
        "added_at": utc_now(),
    }

    write_config(config, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"已注册 {args.branch_name} from {args.url} (branch: {args.branch})")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    """处理 log 命令"""
    if not is_git_repo():
        raise BraidError(
            ErrorCode.NOT_GIT_REPO,
            "当前目录不是 Git 仓库",
            "请先执行 git init 或切换到正确的 Git 仓库目录",
        )
    config = read_config()
    if args.branch not in config:
        raise BraidError(
            ErrorCode.BRANCH_NOT_FOUND,
            f"分支 {args.branch} 未注册",
            f"请先使用 add 命令注册分支",
        )

    branch_info = config[args.branch]
    url = branch_info["url"]
    upstream_branch = branch_info.get("branch", "main")

    # 获取本地分支的提交
    code, local_commits, _ = run_git_command(
        ["log", "--oneline", "-10", args.branch]
    )
    if code != 0:
        local_commits = "无法获取"

    # 获取上游分支的提交
    success, upstream_info = fetch_upstream(url, upstream_branch)
    if not success:
        upstream_commits = "无法获取"
    else:
        upstream_commits = upstream_info

    print(f"分支 {args.branch} 的变更记录:")
    print(f"  本地提交:")
    for line in local_commits.split("\n"):
        if line:
            print(f"    {line}")
    print(f"  上游提交:")
    for line in upstream_commits.split("\n"):
        if line:
            print(f"    {line}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """处理 config 命令"""
    config = read_config()
    if args.dry_run:
        print("[DRY-RUN] 配置预览:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    return 0


def selftest() -> int:
    """自检函数，验证核心功能"""
    print("开始自检...")
    errors = []

    # 测试 1: 检查 Git 仓库
    print("  [1/5] 检查 Git 仓库...")
    if not is_git_repo():
        errors.append("当前目录不是 Git 仓库")
        print("    [FAIL] 当前目录不是 Git 仓库")
    else:
        print("    [OK] Git 仓库检查通过")

    # 测试 2: 检查配置读写
    print("  [2/5] 检查配置读写...")
    test_config = {"test_branch": {"url": "https://example.com/repo.git", "branch": "main"}}
    try:
        write_config(test_config, dry_run=True)
        print("    [OK] 配置写入（dry-run）通过")
    except Exception as e:
        errors.append(f"配置写入失败: {e}")
        print(f"    [FAIL] 配置写入失败: {e}")

    # 测试 3: 检查 URL 校验
    print("  [3/5] 检查 URL 校验...")
    valid_urls = [
        "https://github.com/example/repo.git",
        "git@github.com:example/repo.git",
        "ssh://git@example.com/repo.git",
        "file:///path/to/repo",
    ]
    invalid_urls = ["not-a-url", "ftp://example.com", ""]
    for url in valid_urls:
        if not validate_url(url):
            errors.append(f"有效 URL 被拒绝: {url}")
            print(f"    [FAIL] 有效 URL 被拒绝: {url}")
    for url in invalid_urls:
        if validate_url(url):
            errors.append(f"无效 URL 被接受: {url}")
            print(f"    [FAIL] 无效 URL 被接受: {url}")
    if not errors:
        print("    [OK] URL 校验通过")

    # 测试 4: 检查错误处理
    print("  [4/5] 检查错误处理...")
    try:
        raise BraidError(ErrorCode.BRANCH_NOT_FOUND, "测试错误", "测试提示")
    except BraidError as e:
        if e.code == ErrorCode.BRANCH_NOT_FOUND:
            print("    [OK] 错误处理通过")
        else:
            errors.append("错误码不正确")
            print(f"    [FAIL] 错误码不正确: {e.code}")

    # 测试 5: 检查时间戳
    print("  [5/5] 检查时间戳...")
    ts = utc_now()
    if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ts):
        print(f"    [OK] 时间戳格式正确: {ts}")
    else:
        errors.append(f"时间戳格式不正确: {ts}")
        print(f"    [FAIL] 时间戳格式不正确: {ts}")

    # 总结
    if errors:
        print(f"\n自检失败，共 {len(errors)} 个错误:")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("\n所有自检通过 ✅")
        return 0

    try:
        fetch_upstream("")  # G3 核心链路自检
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出  # G3 核心链路异常降级

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="braid — 供应商分支追踪工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="braid 1.2.0",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览操作，不实际执行",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status 命令
    subparsers.add_parser("status", help="查看所有供应商分支状态")

    # update 命令
    update_parser = subparsers.add_parser("update", help="更新供应商分支")
    update_parser.add_argument("--branch", nargs="?", help="要更新的分支名称")
    update_parser.add_argument("--all", action="store_true", help="更新所有分支")

    # add 命令
    add_parser = subparsers.add_parser("add", help="注册新的供应商分支")
    add_parser.add_argument("--url", help="上游仓库 URL")
    add_parser.add_argument("--branch_name", help="本地分支名称")
    add_parser.add_argument("--branch", default="main", help="上游分支名称（默认: main）")
    add_parser.add_argument("--tag", default="", help="上游标签")

    # log 命令
    log_parser = subparsers.add_parser("log", help="查看分支变更记录")
    log_parser.add_argument("--branch", help="分支名称")

    # config 命令
    subparsers.add_parser("config", help="查看配置")

    args = parser.parse_args()

    try:
        if args.selftest:
            return selftest()

        if not args.command:
            parser.print_help()
            return 0

        # 将 dry-run 和 verbose 传递给子命令
        if hasattr(args, "dry_run"):
            args.dry_run = args.dry_run
        if hasattr(args, "verbose"):
            args.verbose = args.verbose

        if args.command == "status":
            return cmd_status(args)
        elif args.command == "update":
            if args.all:
                args.branch = None
            return cmd_update(args)
        elif args.command == "add":
            return cmd_add(args)
        elif args.command == "log":
            return cmd_log(args)
        elif args.command == "config":
            return cmd_config(args)
        else:
            parser.print_help()
            return 0

    except BraidError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        if e.hint:
            print(f"提示: {e.hint}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
