#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lazygit 技能辅助脚本
功能：环境体检、键位速查、仓库诊断、配置生成（仅提供指导，不执行写操作）
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------- 错误码定义 ----------
# E001: 参数错误
# E002: 系统命令执行失败
# E003: 当前目录不是 Git 仓库
# E004: 配置文件写入失败
# E005: 内部数据异常
# E006: 输入数据格式错误
# E007: 自检失败
# E008: 不支持的平台
# E009: 资源不可用
# E010: 其他未知错误

ERROR_MESSAGES = {
    "E001": "参数错误",
    "E002": "系统命令执行失败",
    "E003": "当前目录不是 Git 仓库",
    "E004": "配置文件写入失败",
    "E005": "内部数据异常",
    "E006": "输入数据格式错误",
    "E007": "自检失败",
    "E008": "不支持的平台",
    "E009": "资源不可用",
    "E010": "其他未知错误",
}


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出"""
    msg = ERROR_MESSAGES.get(code, "未知错误")
    if detail:
        msg = f"{msg}: {detail}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------- 数据模型 ----------
@dataclass
class RepoStatus:
    """仓库状态信息"""
    is_repo: bool = False
    branch: str = ""
    has_conflicts: bool = False
    has_uncommitted: bool = False
    has_unpushed: bool = False
    detached_head: bool = False
    ahead_count: int = 0
    behind_count: int = 0


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    installed: bool
    version: str = ""


# ---------- 内置数据 ----------
# 键位速查表：场景词 -> lazygit 按键
KEY_MAP: Dict[str, str] = {
    "查看状态": "1",
    "查看日志": "L",
    "查看分支": "2",
    "查看提交": "c",
    "查看文件": "3",
    "暂存文件": "space",
    "取消暂存": "space",
    "提交更改": "c",
    "提交amend": "A",
    "推送": "P",
    "拉取": "p",
    "合并分支": "m",
    "切换分支": "b",
    "新建分支": "n",
    "删除分支": "d",
    "查看冲突": "x",
    "解决冲突": "e",
    "撤销提交": "u",
    "回退提交": "g",
    "查看远程": "r",
    "添加远程": "R",
    "删除远程": "D",
    "查看标签": "t",
    "新建标签": "T",
    "删除标签": "d",
    "查看stash": "s",
    "创建stash": "S",
    "应用stash": "a",
    "丢弃stash": "D",
    "刷新": "R",
    "搜索": "/",
    "过滤": "f",
    "展开/折叠": "enter",
    "返回上级": "esc",
    "退出": "q",
    "帮助": "?",
    "选择上一个": "↑",
    "选择下一个": "↓",
    "选择左侧": "←",
    "选择右侧": "→",
    "跳到顶部": "g",
    "跳到底部": "G",
    "全选": "a",
    "取消全选": "A",
    "复制": "y",
    "粘贴": "p",
    "重命名": "r",
    "删除": "d",
    "编辑": "e",
    "打开": "o",
    "查看差异": "v",
    "查看补丁": "p",
    "应用补丁": "a",
    "取消补丁": "c",
    "查看作者": "a",
    "查看日期": "t",
    "查看hash": "h",
    "复制hash": "H",
    "检出": "c",
    "变基": "r",
    "整理": "i",
    "压缩": "s",
    "修复": "f",
    "跳过": "k",
    "中止": "A",
    "继续": "c",
}

# 仓库诊断规则
DIAGNOSIS_RULES = [
    {
        "id": "conflict",
        "name": "合并冲突",
        "check": lambda status: status.has_conflicts,
        "advice": "按 x 查看冲突文件列表，按 e 进入合并编辑器解决冲突，解决后按 c 提交",
    },
    {
        "id": "detached",
        "name": "游离HEAD",
        "check": lambda status: status.detached_head,
        "advice": "按 2 查看分支列表，选择目标分支按 space 检出，或按 b 创建新分支保存当前工作",
    },
    {
        "id": "unpushed",
        "name": "未推送提交",
        "check": lambda status: status.has_unpushed,
        "advice": lambda status: f"当前有 {status.ahead_count} 个提交未推送，按 P 推送到远程仓库",
    },
    {
        "id": "uncommitted",
        "name": "未提交更改",
        "check": lambda status: status.has_uncommitted,
        "advice": "按 3 查看文件列表，按 space 暂存文件，按 c 提交更改",
    },
]


# ---------- 核心功能 ----------
def run_command(cmd: List[str], cwd: Optional[str] = None) -> Tuple[int, str]:
    """执行系统命令，返回 (返回码, 输出)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=10,
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, "命令执行超时"
    except Exception as e:
        error_exit("E002", f"执行 {' '.join(cmd)} 失败: {str(e)}")
        return -1, ""


def check_tool_installed(tool_name: str) -> ToolInfo:
    """检查工具是否安装"""
    path = shutil.which(tool_name)
    if not path:
        return ToolInfo(name=tool_name, installed=False)
    try:
        if tool_name == "git":
            code, output = run_command(["git", "--version"])
        else:
            code, output = run_command([tool_name, "--version"])
        version = output if code == 0 else ""
        return ToolInfo(name=tool_name, installed=True, version=version)
    except Exception:
        return ToolInfo(name=tool_name, installed=True)


def get_repo_status(cwd: str) -> RepoStatus:
    """获取仓库状态"""
    status = RepoStatus()

    # 检查是否在 git 仓库中
    code, _ = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd)
    if code != 0:
        return status

    status.is_repo = True

    # 获取当前分支
    code, branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if code == 0:
        if branch == "HEAD":
            status.detached_head = True
        else:
            status.branch = branch

    # 检查冲突
    code, output = run_command(["git", "diff", "--name-only", "--diff-filter=U"], cwd=cwd)
    status.has_conflicts = code == 0 and len(output) > 0

    # 检查未提交更改
    code, output = run_command(["git", "status", "--porcelain"], cwd=cwd)
    status.has_uncommitted = code == 0 and len(output) > 0

    # 检查未推送提交
    code, output = run_command(["git", "rev-list", "@{u}..HEAD", "--count"], cwd=cwd)
    if code == 0 and output.isdigit():
        status.ahead_count = int(output)
        status.has_unpushed = status.ahead_count > 0

    # 检查落后提交
    code, output = run_command(["git", "rev-list", "HEAD..@{u}", "--count"], cwd=cwd)
    if code == 0 and output.isdigit():
        status.behind_count = int(output)

    return status


def doctor(cwd: str) -> Dict:
    """环境体检"""
    result = {
        "tools": {},
        "repo": None,
        "status": "ok",
    }

    # 检查 git
    git_info = check_tool_installed("git")
    result["tools"]["git"] = {
        "installed": git_info.installed,
        "version": git_info.version,
    }

    # 检查 lazygit
    lazygit_info = check_tool_installed("lazygit")
    result["tools"]["lazygit"] = {
        "installed": lazygit_info.installed,
        "version": lazygit_info.version,
    }

    # 检查仓库状态
    repo_status = get_repo_status(cwd)
    result["repo"] = {
        "is_repo": repo_status.is_repo,
        "branch": repo_status.branch,
        "detached_head": repo_status.detached_head,
        "has_conflicts": repo_status.has_conflicts,
        "has_uncommitted": repo_status.has_uncommitted,
        "has_unpushed": repo_status.has_unpushed,
        "ahead_count": repo_status.ahead_count,
        "behind_count": repo_status.behind_count,
    }

    if not git_info.installed:
        result["status"] = "warning"
        result["message"] = "git 未安装"
    elif not lazygit_info.installed:
        result["status"] = "warning"
        result["message"] = "lazygit 未安装"
    elif not repo_status.is_repo:
        result["status"] = "warning"
        result["message"] = "当前目录不是 Git 仓库"

    return result


def keys(query: str = "") -> Dict:
    """键位速查"""
    result = {
        "total": len(KEY_MAP),
        "matches": [],
    }

    if query:
        # 模糊搜索
        query_lower = query.lower()
        matches = [(k, v) for k, v in KEY_MAP.items() if query_lower in k.lower()]
    else:
        # 全量列表
        matches = list(KEY_MAP.items())

    result["matches"] = [{"action": k, "key": v} for k, v in matches]
    result["count"] = len(matches)
    return result


def fix(cwd: str) -> Dict:
    """仓库诊断"""
    status = get_repo_status(cwd)
    if not status.is_repo:
        error_exit("E003", "当前目录不是 Git 仓库")

    issues = []
    for rule in DIAGNOSIS_RULES:
        if rule["check"](status):
            advice = rule["advice"]
            # 如果 advice 是函数，则调用它
            if callable(advice):
                advice = advice(status)
            issues.append({
                "id": rule["id"],
                "name": rule["name"],
                "advice": advice,
            })

    return {
        "issues": issues,
        "count": len(issues),
        "healthy": len(issues) == 0,
    }


def config() -> Dict:
    """生成 lazygit 配置文件内容"""
    config_content = """# lazygit 配置文件
# 生成时间: {timestamp}

gui:
  # 主题设置
  theme:
    activeBorderColor:
      - green
      - bold
    inactiveBorderColor:
      - white
    optionsTextColor:
      - blue

  # 显示设置
  showFileTree: true
  showListFooter: true
  showPanelJumps: true
  showCommandLog: true

git:
  # Git 设置
  paging:
    colorArg: always
  log:
    showGraph: always
    showWholeGraph: false

customCommands:
  # 自定义命令示例
  - key: "C"
    command: "git cz"
    description: "使用 commitizen 提交"
    context: "files"
    loadingText: "正在打开 commitizen..."
    subprocess: true

  - key: "F"
    command: "git fetch --all --prune"
    description: "拉取所有远程更新"
    context: "global"
    loadingText: "正在拉取远程更新..."

  - key: "L"
    command: "git log --oneline --graph --all -20"
    description: "查看最近 20 条提交图"
    context: "global"
    loadingText: "正在加载提交图..."

  - key: "S"
    command: "git stash push -m 'temp'"
    description: "快速暂存当前更改"
    context: "files"
    loadingText: "正在暂存更改..."

keybinding:
  # 快捷键绑定
  universal:
    quit: "q"
    quit-alt1: "<c-c>"
    return: "<esc>"
    confirm: "<enter>"
    togglePanel: "<tab>"
    prevItem: "↑"
    nextItem: "↓"
    prevPage: ","
    nextPage: "."
    scrollUp: "<pgup>"
    scrollDown: "<pgdn>"
""".format(timestamp=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return {
        "content": config_content,
        "path": os.path.join(os.path.expanduser("~"), ".config", "lazygit", "config.yml"),
        "description": "带中文注释的 lazygit 配置文件",
    }


# ---------- 自检功能 ----------
def selftest() -> bool:
    """离线自检核心逻辑"""
    print("开始自检...")

    # 测试键位速查
    print("测试键位速查...")
    result = keys()
    assert result["total"] >= 60, f"键位数量不足: {result['total']}"
    assert result["count"] == result["total"], "全量列表数量不一致"

    result = keys("提交")
    assert result["count"] > 0, "搜索'提交'无结果"
    assert all("提交" in m["action"] for m in result["matches"]), "搜索结果不匹配"

    print("  键位速查测试通过")

    # 测试仓库诊断（使用临时目录）
    print("测试仓库诊断...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化 git 仓库
        code, _ = run_command(["git", "init"], cwd=tmpdir)
        assert code == 0, "git init 失败"

        # 配置用户
        run_command(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
        run_command(["git", "config", "user.name", "Test User"], cwd=tmpdir)

        # 创建文件并提交
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("test content")
        run_command(["git", "add", "."], cwd=tmpdir)
        run_command(["git", "commit", "-m", "initial"], cwd=tmpdir)

        # 测试仓库状态
        status = get_repo_status(tmpdir)
        assert status.is_repo, "仓库检测失败"
        assert status.branch == "master" or status.branch == "main", f"分支名异常: {status.branch}"
        assert not status.has_conflicts, "冲突检测错误"
        assert not status.has_uncommitted, "未提交检测错误"

        # 测试诊断
        result = fix(tmpdir)
        assert result["healthy"], "健康仓库被诊断为有问题"

        print("  仓库诊断测试通过")

        # 测试冲突检测
        print("测试冲突检测...")
        # 创建冲突
        run_command(["git", "checkout", "-b", "feature"], cwd=tmpdir)
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("feature change")
        run_command(["git", "add", "."], cwd=tmpdir)
        run_command(["git", "commit", "-m", "feature"], cwd=tmpdir)
        run_command(["git", "checkout", "master"], cwd=tmpdir)
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("master change")
        run_command(["git", "add", "."], cwd=tmpdir)
        run_command(["git", "commit", "-m", "master"], cwd=tmpdir)
        run_command(["git", "merge", "feature"], cwd=tmpdir)

        status = get_repo_status(tmpdir)
        assert status.has_conflicts, "冲突检测失败"

        result = fix(tmpdir)
        assert not result["healthy"], "冲突仓库被诊断为健康"
        assert any(i["id"] == "conflict" for i in result["issues"]), "未找到冲突诊断"

        print("  冲突检测测试通过")

    # 测试配置生成
    print("测试配置生成...")
    result = config()
    assert "customCommands" in result["content"], "配置缺少自定义命令"
    assert "keybinding" in result["content"], "配置缺少快捷键绑定"
    assert "theme" in result["content"], "配置缺少主题设置"
    print("  配置生成测试通过")

    # 测试工具检测
    print("测试工具检测...")
    git_info = check_tool_installed("git")
    assert git_info.installed, "git 应已安装"
    assert git_info.version, "git 版本信息为空"
    print("  工具检测测试通过")

    print("\n全部自检通过！")
    return True


# ---------- 主入口 ----------
def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="lazygit 技能辅助工具",
        epilog="示例: python main.py doctor | keys [关键词] | fix | config | --selftest"
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["doctor", "keys", "fix", "config"],
        help="要执行的命令"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="keys 命令的搜索关键词"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    parser.add_argument(
        "--cwd",
        default=os.getcwd(),
        help="工作目录（默认当前目录）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            selftest()
        except AssertionError as e:
            error_exit("E007", str(e))
        except Exception as e:
            error_exit("E007", f"自检异常: {str(e)}")
        return

    # 检查命令参数
    if not args.command:
        parser.print_help()
        error_exit("E001", "未指定命令")

    # 执行命令
    try:
        if args.command == "doctor":
            result = doctor(args.cwd)
        elif args.command == "keys":
            result = keys(args.query or "")
        elif args.command == "fix":
            result = fix(args.cwd)
        elif args.command == "config":
            result = config()
        else:
            error_exit("E001", f"未知命令: {args.command}")

        # 输出结果
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if args.command == "doctor":
                print("=== 环境体检 ===")
                for tool, info in result["tools"].items():
                    status = "✓" if info["installed"] else "✗"
                    version = f" ({info['version']})" if info["installed"] else ""
                    print(f"  {tool}: {status}{version}")
                if result["repo"]:
                    repo = result["repo"]
                    print(f"  仓库: {'是' if repo['is_repo'] else '否'}")
                    if repo["is_repo"]:
                        print(f"  分支: {repo['branch'] or '(游离HEAD)'}")
                        if repo["has_conflicts"]:
                            print("  ⚠ 存在冲突")
                        if repo["has_uncommitted"]:
                            print("  ⚠ 有未提交更改")
                        if repo["has_unpushed"]:
                            print(f"  ⚠ 有 {repo['ahead_count']} 个未推送提交")
                if result["status"] != "ok":
                    print(f"  状态: {result.get('message', '')}")
            elif args.command == "keys":
                print(f"=== 键位速查 ({result['count']} 条) ===")
                for match in result["matches"]:
                    print(f"  {match['action']}: {match['key']}")
            elif args.command == "fix":
                print("=== 仓库诊断 ===")
                if result["healthy"]:
                    print("  仓库状态健康")
                else:
                    for issue in result["issues"]:
                        print(f"  ⚠ {issue['name']}: {issue['advice']}")
            elif args.command == "config":
                print("=== 配置生成 ===")
                print(f"  配置文件路径: {result['path']}")
                print(f"  说明: {result['description']}")
                print("\n配置内容预览:")
                print(result["content"][:500] + "...")

    except SystemExit:
        raise
    except Exception as e:
        error_exit("E010", str(e))


if __name__ == "__main__":
    main()
