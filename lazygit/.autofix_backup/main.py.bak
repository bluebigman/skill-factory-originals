#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lazygit 技能辅助脚本（clean-room 独立实现）

功能：
- doctor   : 检测 git/lazygit 是否安装、版本、仓库状态
- keys     : 查询 lazygit 按键映射（中文场景词）
- fix      : 诊断仓库异常并给出操作建议
- config   : 生成带中文注释的 lazygit 配置文件
- --selftest : 内置样例数据离线自检

仅依据功能规格实现，不参考任何既有代码。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "命令执行失败（系统调用）",
    "E003": "git 未安装或不可用",
    "E004": "lazygit 未安装或不可用",
    "E005": "当前目录不是 Git 仓库",
    "E006": "配置文件写入失败",
    "E007": "内置键位数据加载失败",
    "E008": "自检失败（核心逻辑异常）",
    "E009": "无效的命令参数",
    "E010": "未知错误",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出。"""
    msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        msg = f"{msg}: {message}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 键位映射数据（内置，不依赖外部文件）
# ---------------------------------------------------------------------------
# 中文场景词 -> (按键, 说明)
KEY_MAP: Dict[str, Tuple[str, str]] = {
    # 基本操作
    "打开帮助": ("?", "显示帮助面板"),
    "退出": ("q", "退出 lazygit"),
    "退出弹窗": ("esc", "关闭当前弹窗/返回上层"),
    "切换面板": ("tab", "在主要面板间循环切换"),
    "展开/收起侧边栏": ("]", "切换侧边栏宽度"),
    "全屏切换": ("f", "切换当前面板全屏"),
    # 文件/暂存
    "查看文件状态": ("1", "切换到文件面板"),
    "暂存文件": ("space", "暂存/取消暂存当前文件"),
    "暂存所有": ("a", "暂存所有文件"),
    "取消暂存": ("v", "取消暂存当前文件"),
    "查看暂存内容": ("enter", "查看文件差异"),
    "打开文件": ("o", "用默认编辑器打开文件"),
    "丢弃更改": ("d", "丢弃当前文件的所有更改"),
    "编辑文件": ("e", "用编辑器打开文件"),
    "刷新文件": ("r", "刷新文件状态"),
    # 提交
    "提交代码": ("c", "打开提交信息输入"),
    "提交(不带钩子)": ("w", "跳过钩子提交"),
    "修改上次提交": ("c", "编辑上次提交信息"),
    "撤销上次提交": ("z", "撤销上次提交（保留更改）"),
    "撤销提交(软)": ("Z", "撤销提交并保留暂存"),
    "复制提交哈希": ("y", "复制当前提交哈希到剪贴板"),
    "复制提交信息": ("Y", "复制当前提交信息"),
    # 分支
    "查看分支": ("2", "切换到分支面板"),
    "新建分支": ("n", "创建新分支"),
    "切换分支": ("space", "切换到选中分支"),
    "删除分支": ("d", "删除选中分支"),
    "合并分支": ("m", "将选中分支合并到当前分支"),
    "变基分支": ("r", "将当前分支变基到选中分支"),
    "重命名分支": ("R", "重命名当前分支"),
    "检出分支": ("enter", "检出选中分支"),
    "查看分支图": ("g", "打开分支提交图"),
    # 日志/历史
    "查看提交日志": ("4", "切换到提交日志面板"),
    "查看所有提交": ("5", "查看所有分支的提交"),
    "搜索提交": ("/", "在当前列表搜索"),
    "查看提交详情": ("enter", "查看选中提交的详情"),
    "检出提交": ("space", "检出选中提交（detached HEAD）"),
    "cherry-pick": ("c", "将提交复制到当前分支"),
    "revert提交": ("r", "回滚选中提交"),
    # 冲突解决
    "解决冲突": ("enter", "打开冲突文件进行编辑"),
    "选择本地版本": ("<", "在冲突解决中选择本地版本"),
    "选择远程版本": (">", "在冲突解决中选择远程版本"),
    "合并所有冲突": ("|", "打开合并工具"),
    "查看冲突文件": ("1", "冲突文件会标记在文件列表"),
    # 交互式暂存
    "交互式暂存": ("enter", "进入补丁暂存模式"),
    "暂存行": ("space", "暂存当前行"),
    "暂存块": ("a", "暂存当前块"),
    "取消暂存行": ("v", "取消暂存当前行"),
    "暂存全部": ("A", "暂存所有更改"),
    "退出交互暂存": ("esc", "退出补丁暂存模式"),
    # 远程操作
    "推送": ("P", "推送到远程"),
    "拉取": ("p", "从远程拉取"),
    "强制推送": ("shift+P", "强制推送"),
    "查看远程": ("3", "切换到远程面板"),
    "添加远程": ("a", "添加新的远程仓库"),
    "删除远程": ("d", "删除选中远程"),
    # 其他
    "撤销操作": ("u", "撤销上一个操作"),
    "重做操作": ("ctrl+r", "重做被撤销的操作"),
    "复制文件名": ("Y", "复制当前文件名"),
    "在终端中打开": ("!", "在外部终端打开"),
    "自定义命令": (":", "执行自定义命令"),
    "刷新全部": ("R", "刷新所有面板"),
    "切换主题": ("ctrl+t", "切换主题"),
    "打开配置": ("e", "打开 lazygit 配置文件"),
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class RepoStatus:
    """仓库健康状态。"""
    is_repo: bool = False
    has_conflicts: bool = False
    is_detached: bool = False
    has_unpushed: bool = False
    has_uncommitted: bool = False
    current_branch: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------
def run_command(cmd: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """执行系统命令，返回 (返回码, stdout, stderr)。"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"命令不存在: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "命令执行超时"
    except Exception as exc:
        return 1, "", str(exc)


def check_git_installed() -> Tuple[bool, str]:
    """检测 git 是否安装，返回 (是否安装, 版本)。"""
    code, out, _ = run_command(["git", "--version"])
    if code != 0:
        return False, ""
    return True, out


def check_lazygit_installed() -> Tuple[bool, str]:
    """检测 lazygit 是否安装，返回 (是否安装, 版本)。"""
    code, out, _ = run_command(["lazygit", "--version"])
    if code != 0:
        return False, ""
    return True, out


def get_repo_status(cwd: str) -> RepoStatus:
    """获取当前目录的 git 仓库状态。"""
    status = RepoStatus()

    # 检查是否为 git 仓库
    code, _, _ = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    if code != 0:
        status.is_repo = False
        return status
    status.is_repo = True

    # 获取当前分支
    code, out, _ = run_command(["git", "branch", "--show-current"], cwd)
    if code == 0:
        status.current_branch = out

    # 检查是否有未提交更改
    code, out, _ = run_command(["git", "status", "--porcelain"], cwd)
    if code == 0 and out:
        status.has_uncommitted = True

    # 检查是否有冲突
    code, out, _ = run_command(["git", "diff", "--name-only", "--diff-filter=U"], cwd)
    if code == 0 and out:
        status.has_conflicts = True

    # 检查是否 detached HEAD
    code, out, _ = run_command(["git", "symbolic-ref", "-q", "HEAD"], cwd)
    if code != 0:
        status.is_detached = True

    # 检查是否有未推送提交
    code, _, _ = run_command(["git", "rev-parse", "--abbrev-ref", "@{upstream}"], cwd)
    if code == 0:
        code, out, _ = run_command(["git", "log", "@{upstream}..HEAD", "--oneline"], cwd)
        if code == 0 and out:
            status.has_unpushed = True

    return status


def doctor(cwd: str) -> Dict:
    """环境体检。"""
    result = {"git": {}, "lazygit": {}, "repo": {}}

    # 检测 git
    git_ok, git_ver = check_git_installed()
    result["git"]["installed"] = git_ok
    result["git"]["version"] = git_ver
    if not git_ok:
        result["git"]["error"] = "未检测到 git，请先安装 git"
        return result

    # 检测 lazygit
    lg_ok, lg_ver = check_lazygit_installed()
    result["lazygit"]["installed"] = lg_ok
    result["lazygit"]["version"] = lg_ver
    if not lg_ok:
        result["lazygit"]["error"] = "未检测到 lazygit，请先安装 lazygit"

    # 检测仓库状态
    status = get_repo_status(cwd)
    result["repo"]["is_repo"] = status.is_repo
    if status.is_repo:
        result["repo"]["current_branch"] = status.current_branch
        result["repo"]["has_conflicts"] = status.has_conflicts
        result["repo"]["is_detached"] = status.is_detached
        result["repo"]["has_unpushed"] = status.has_unpushed
        result["repo"]["has_uncommitted"] = status.has_uncommitted

    return result


def search_keys(keyword: str) -> List[Dict]:
    """搜索键位映射。"""
    results = []
    keyword_lower = keyword.lower()

    for scene, (key, desc) in KEY_MAP.items():
        # 模糊匹配：场景词或描述包含关键词
        if keyword_lower in scene.lower() or keyword_lower in desc.lower():
            results.append({
                "scene": scene,
                "key": key,
                "description": desc,
            })

    return results


def list_all_keys() -> List[Dict]:
    """列出所有键位映射。"""
    return [
        {"scene": scene, "key": key, "description": desc}
        for scene, (key, desc) in sorted(KEY_MAP.items())
    ]


def diagnose(cwd: str) -> List[Dict]:
    """仓库诊断，返回问题列表及建议。"""
    status = get_repo_status(cwd)
    issues = []

    if not status.is_repo:
        issues.append({
            "level": "error",
            "issue": "当前目录不是 Git 仓库",
            "suggestion": "在 Git 仓库目录中运行 lazygit",
            "code": "E005",
        })
        return issues

    # 检查冲突
    if status.has_conflicts:
        issues.append({
            "level": "critical",
            "issue": "存在合并冲突",
            "suggestion": "在 lazygit 中按 1 进入文件面板，冲突文件标记为红色，按 Enter 打开进行解决",
            "code": "CONFLICT",
        })

    # 检查 detached HEAD
    if status.is_detached:
        issues.append({
            "level": "warning",
            "issue": "处于 detached HEAD 状态",
            "suggestion": "在 lazygit 中按 2 进入分支面板，选择分支按 Space 检出，或创建新分支",
            "code": "DETACHED",
        })

    # 检查未推送提交
    if status.has_unpushed:
        issues.append({
            "level": "info",
            "issue": "存在未推送的提交",
            "suggestion": "在 lazygit 中按 P 推送到远程",
            "code": "UNPUSHED",
        })

    # 检查未提交更改
    if status.has_uncommitted:
        issues.append({
            "level": "info",
            "issue": "存在未提交的更改",
            "suggestion": "在 lazygit 中按 1 进入文件面板，按 Space 暂存，按 c 提交",
            "code": "UNCOMMITTED",
        })

    if not issues:
        issues.append({
            "level": "ok",
            "issue": "仓库状态健康",
            "suggestion": "无异常，可以正常使用",
            "code": "OK",
        })

    return issues


def generate_config() -> str:
    """生成带中文注释的 lazygit 配置文件。"""
    config = r"""# lazygit 配置文件（自动生成）
# 配置文件位置: ~/.config/lazygit/config.yml
# 更多配置选项: https://github.com/jesseduffield/lazygit/blob/master/docs/Config.md

# 用户界面设置
gui:
  # 主题颜色
  theme:
    # 选中项背景色
    selectedLineBgColor:
      - blue
    # 活动边框颜色
    activeBorderColor:
      - green
      - bold

  # 是否显示图标
  showIcons: true

  # 语言设置
  language: auto

# Git 相关设置
git:
  # 是否显示分支图
  paging:
    colorArg: always

  # 提交信息模板
  commitPrefixes:
    # 按分支名匹配提交前缀
    'feat/':
      pattern: '^feat/'
      replace: 'feat: '

# 自定义命令
customCommands:
  # 快速提交（跳过钩子）
  - key: "W"
    command: "git commit --no-verify"
    description: "跳过钩子提交"

  # 查看文件历史
  - key: "H"
    command: "git log --oneline -- {{filename}}"
    description: "查看文件历史"

  # 清理本地已合并分支
  - key: "C"
    command: "git branch --merged | grep -v '\\*' | xargs -n 1 git branch -d"
    description: "清理已合并分支"

# 按键绑定
keybinding:
  # 通用按键
  universal:
    # 退出
    quit: "q"
    # 返回
    return: "esc"
    # 确认
    confirm: "enter"
    # 刷新
    refresh: "R"

  # 文件面板按键
  files:
    # 暂存文件
    stage: "space"
    # 暂存全部
    stageAll: "a"
    # 丢弃更改
    discard: "d"

  # 提交面板按键
  commits:
    # 提交
    commit: "c"
    # 修改提交
    amend: "A"

  # 分支面板按键
  branches:
    # 新建分支
    newBranch: "n"
    # 切换分支
    checkout: "space"
    # 合并分支
    merge: "m"
"""
    return config


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """离线自检核心逻辑，不依赖外部文件/网络。"""
    try:
        # 1. 测试键位搜索
        results = search_keys("冲突")
        assert len(results) > 0, "键位搜索失败：未找到冲突相关键位"
        assert any("冲突" in r["scene"] for r in results), "键位搜索返回结果异常"

        # 2. 测试全量键位列表
        all_keys = list_all_keys()
        assert len(all_keys) >= 60, f"键位数据异常：只有 {len(all_keys)} 条"
        assert all(k["key"] for k in all_keys), "存在空键位"

        # 3. 测试配置生成
        config = generate_config()
        assert "lazygit" in config, "配置生成失败"
        assert "customCommands" in config, "配置缺少自定义命令"

        # 4. 测试仓库状态检测（使用临时目录模拟）
        with tempfile.TemporaryDirectory() as tmpdir:
            # 非 git 仓库
            status = get_repo_status(tmpdir)
            assert not status.is_repo, "非 git 目录被误判为 git 仓库"

            # 初始化 git 仓库
            code, _, _ = run_command(["git", "init"], cwd=tmpdir)
            if code == 0:
                status = get_repo_status(tmpdir)
                assert status.is_repo, "git 仓库未被正确识别"

                # 创建文件并检查未提交状态
                test_file = os.path.join(tmpdir, "test.txt")
                with open(test_file, "w") as f:
                    f.write("test content")
                status = get_repo_status(tmpdir)
                assert status.has_uncommitted, "未提交更改未被检测"

                # 提交文件
                code, _, _ = run_command(["git", "add", "."], cwd=tmpdir)
                code, _, _ = run_command(["git", "commit", "-m", "test"], cwd=tmpdir)
                if code == 0:
                    status = get_repo_status(tmpdir)
                    assert not status.has_uncommitted, "提交后仍有未提交更改"

        # 5. 测试诊断功能
        with tempfile.TemporaryDirectory() as tmpdir:
            issues = diagnose(tmpdir)
            assert len(issues) > 0, "诊断功能未返回结果"
            assert issues[0]["code"] == "E005", "非仓库目录诊断错误码异常"

        # 6. 测试错误码
        assert ERROR_CODES["E001"] == "参数解析失败", "错误码定义异常"
        assert len(ERROR_CODES) == 10, f"错误码数量异常: {len(ERROR_CODES)}"

        print("✅ 自检通过：所有核心逻辑正常")
        return True

    except AssertionError as exc:
        print(f"❌ 自检失败: {exc}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"❌ 自检异常: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_doctor(result: Dict) -> str:
    """格式化 doctor 输出。"""
    lines = []
    lines.append("=" * 50)
    lines.append("lazygit 环境体检报告")
    lines.append("=" * 50)

    # Git 检测
    git = result["git"]
    lines.append(f"\n[Git]")
    if git["installed"]:
        lines.append(f"  状态: ✅ 已安装")
        lines.append(f"  版本: {git['version']}")
    else:
        lines.append(f"  状态: ❌ 未安装")
        lines.append(f"  提示: {git.get('error', '')}")

    # lazygit 检测
    lg = result["lazygit"]
    lines.append(f"\n[lazygit]")
    if lg["installed"]:
        lines.append(f"  状态: ✅ 已安装")
        lines.append(f"  版本: {lg['version']}")
    else:
        lines.append(f"  状态: ❌ 未安装")
        lines.append(f"  提示: {lg.get('error', '')}")

    # 仓库状态
    repo = result["repo"]
    lines.append(f"\n[仓库状态]")
    if not repo.get("is_repo"):
        lines.append(f"  状态: ❌ 当前目录不是 Git 仓库")
        lines.append(f"  提示: 请切换到 Git 仓库目录")
    else:
        lines.append(f"  状态: ✅ Git 仓库")
        if repo.get("current_branch"):
            lines.append(f"  当前分支: {repo['current_branch']}")
        if repo.get("has_conflicts"):
            lines.append(f"  冲突: ⚠️ 存在冲突")
        if repo.get("is_detached"):
            lines.append(f"  HEAD: ⚠️ detached 状态")
        if repo.get("has_unpushed"):
            lines.append(f"  未推送: ⚠️ 有未推送提交")
        if repo.get("has_uncommitted"):
            lines.append(f"  未提交: ⚠️ 有未提交更改")
        if not any([repo.get("has_conflicts"), repo.get("is_detached"),
                    repo.get("has_unpushed"), repo.get("has_uncommitted")]):
            lines.append(f"  健康: ✅ 无异常")

    return "\n".join(lines)


def format_keys(keys_list: List[Dict]) -> str:
    """格式化键位列表输出。"""
    if not keys_list:
        return "未找到匹配的键位"

    lines = []
    lines.append(f"找到 {len(keys_list)} 条键位映射：")
    lines.append("-" * 60)
    lines.append(f"{'场景':<20} {'按键':<15} {'说明'}")
    lines.append("-" * 60)

    for item in keys_list:
        lines.append(f"{item['scene']:<20} {item['key']:<15} {item['description']}")

    return "\n".join(lines)


def format_fix(issues: List[Dict]) -> str:
    """格式化诊断输出。"""
    lines = []
    lines.append("=" * 50)
    lines.append("lazygit 仓库诊断报告")
    lines.append("=" * 50)

    for issue in issues:
        level_icon = {
            "critical": "🔴",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "ok": "✅",
        }.get(issue["level"], "❓")

        lines.append(f"\n[{level_icon} {issue['level'].upper()}] {issue['issue']}")
        lines.append(f"  建议: {issue['suggestion']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> None:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="lazygit 技能辅助工具",
        epilog="示例: python main.py doctor | python main.py keys 冲突 | python main.py fix",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # doctor 命令
    subparsers.add_parser("doctor", help="环境体检：检测 git/lazygit 安装与仓库状态")

    # keys 命令
    keys_parser = subparsers.add_parser("keys", help="键位速查")
    keys_parser.add_argument("keyword", nargs="?", default="", help="搜索关键词（留空显示全部）")

    # fix 命令
    subparsers.add_parser("fix", help="仓库诊断：识别问题并给出操作建议")

    # config 命令
    subparsers.add_parser("config", help="生成 lazygit 配置文件")

    # selftest 参数
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 无子命令
    if not args.command:
        parser.print_help()
        return

    # 获取当前工作目录
    cwd = os.getcwd()

    try:
        # 执行子命令
        if args.command == "doctor":
            result = doctor(cwd)
            print(format_doctor(result))

        elif args.command == "keys":
            if args.keyword:
                results = search_keys(args.keyword)
            else:
                results = list_all_keys()
            print(format_keys(results))

        elif args.command == "fix":
            issues = diagnose(cwd)
            print(format_fix(issues))

        elif args.command == "config":
            config = generate_config()
            print(config)
            print("\n# 保存到 ~/.config/lazygit/config.yml 即可生效")

        else:
            error_exit("E009", f"未知命令: {args.command}")

    except KeyboardInterrupt:
        error_exit("E002", "用户中断操作")
    except Exception as exc:
        error_exit("E010", str(exc))


if __name__ == "__main__":
    main()
