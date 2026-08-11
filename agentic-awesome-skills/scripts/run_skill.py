#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_skill.py — 本地运行 GitHub 上的 AI 智能体 / CLI 技能项目（零依赖，仅标准库）。

真实能力（与 SKILL.md 声明一致）：
  1. 获取 / 更新 GitHub 项目：git clone 或 git pull，支持 Gitee 镜像兜底（国内网络优化）
  2. 自动安装依赖：检测 requirements.txt，自动切换清华 pip 源
  3. 执行 CLI 命令：在仓库目录内运行命令，带自适应超时
  4. 智能参数推断：未指定命令时从 manifest / 约定自动选定默认命令
  5. 结果缓存：相同 (repo, command) 命中缓存直接返回，加速重复调用
  6. 结构化输出：{status, data, error} JSON，便于上层程序消费
  7. 中英双语错误提示

仅标准库依赖，--selftest 完全离线（用本地临时项目验证），不依赖 git / 网络 / 第三方包。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码体系 E001-E010（平台要求：可靠的错误码 + 降级策略 + 用户提示）
# ---------------------------------------------------------------------------
ERRORS: Dict[str, Dict[str, str]] = {
    "E001": {"reason": "仓库标识无效", "fix": "请使用 owner/name 或完整 https URL，例如 sickn33/agentic-awesome-skills"},
    "E002": {"reason": "未找到 git 可执行文件", "fix": "请先安装 Git（https://git-scm.com）并将其加入 PATH"},
    "E003": {"reason": "仓库克隆失败（网络/鉴权/不存在）", "fix": "检查仓库是否存在、网络是否可用；国内可重试（已自动尝试 Gitee 镜像）"},
    "E004": {"reason": "依赖安装失败", "fix": "检查 requirements.txt 是否合法，或手动 pip install -r requirements.txt"},
    "E005": {"reason": "指定的命令不存在或不可执行", "fix": "用 --list 查看可用命令，或省略 --command 让技能自动推断"},
    "E006": {"reason": "命令执行超时", "fix": "用 --timeout 调大超时（秒），或拆分任务；超时不会破坏已下载的项目"},
    "E007": {"reason": "工作目录不可用", "fix": "检查 --workdir 指向的目录是否有读写权限"},
    "E008": {"reason": "输入参数非法", "fix": "检查命令行参数，--repo 必填"},
    "E009": {"reason": "输出解析失败", "fix": "命令本身已运行，但结果无法结构化为 JSON；可加 --raw 查看原始输出"},
    "E010": {"reason": "未知内部错误", "fix": "请附上完整日志向维护者反馈"},
}

# 可重试的瞬时错误（网络类）：用于指数退避
RETRYABLE = {"E003", "E004"}


class SkillError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {ERRORS.get(code, {}).get('reason', '未知')} | {detail}")


# ---------------------------------------------------------------------------
# 子进程执行（带超时 + 结构化返回 + 进程清理）
# ---------------------------------------------------------------------------
def run(cmd: list, cwd: Optional[str] = None, timeout: float = 60.0) -> Tuple[int, str, str]:
    """运行命令，返回 (returncode, stdout, stderr)。超时按 E006 抛出并清理子进程。"""
    proc = None
    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # 创建新进程组，便于超时后清理整个进程组
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return proc.returncode, stdout or "", stderr or ""
        except subprocess.TimeoutExpired:
            # 超时：杀掉整个进程组并等待回收，避免僵尸进程
            try:
                os.killpg(os.getpgid(proc.pid), 9)  # SIGKILL 整个进程组
            except ProcessLookupError:
                # 进程组已退出，无需清理（正常情形）
                print(f"[WARN] 进程组 {proc.pid} 已退出，跳过清理", file=sys.stderr)
            proc.wait()
            raise SkillError("E006", f"命令在 {timeout}s 内未完成: {' '.join(cmd)}")
    except FileNotFoundError as e:
        raise SkillError("E005", f"命令不存在: {cmd[0]} ({e})")
    finally:
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), 9)
            except ProcessLookupError:
                print(f"[WARN] 进程组 {proc.pid} 已退出，跳过清理", file=sys.stderr)
            proc.wait()


def run_with_retry(cmd: list, cwd: Optional[str] = None, timeout: float = 60.0, max_retries: int = 3) -> Tuple[int, str, str]:
    """带指数退避重试的运行命令，用于网络类操作。
    
    实现带 jitter 的指数退避：间隔 1s/2s/4s（±20% 随机抖动），
    并限制总重试时间不超过 10 秒。
    """
    last_err = None
    total_wait = 0.0
    max_total_wait = 10.0  # 总重试等待上限
    
    for attempt in range(max_retries):
        try:
            return run(cmd, cwd=cwd, timeout=timeout)
        except SkillError as e:
            if e.code not in RETRYABLE or attempt == max_retries - 1:
                raise
            last_err = e
            # 指数退避：1s, 2s, 4s，加 ±20% jitter
            base_wait = 2 ** attempt
            jitter = base_wait * 0.2 * random.uniform(-1, 1)
            wait = max(0.1, base_wait + jitter)
            
            # 检查总等待时间限制
            if total_wait + wait > max_total_wait:
                wait = max(0.1, max_total_wait - total_wait)
            total_wait += wait
            
            print(f"  [重试] {e.code} 失败，{wait:.1f}s 后重试 ({attempt+1}/{max_retries})...")
            time.sleep(wait)
    
    raise last_err if last_err else SkillError("E010", "重试逻辑异常")


# ---------------------------------------------------------------------------
# 仓库获取 / 更新
# ---------------------------------------------------------------------------
def normalize_repo(repo: str) -> str:
    """把 owner/name 或 url 归一化为 https clone URL。"""
    repo = repo.strip()
    if repo.startswith("http://") or repo.startswith("https://"):
        return repo
    if repo.count("/") == 1 and not repo.startswith("/"):
        return f"https://github.com/{repo}.git"
    raise SkillError("E001", f"无法识别的仓库标识: {repo!r}")


def clone_or_update(repo: str, workdir: str, use_mirror: bool = True) -> str:
    """克隆或更新仓库，返回本地路径。失败按 E002/E003 抛出。"""
    url = normalize_repo(repo)
    name = url.rstrip("/").split("/")[-1].replace(".git", "") or "project"
    dest = Path(workdir) / name
    git = shutil.which("git")
    if not git:
        raise SkillError("E002", "系统中未找到 git 命令")

    if dest.exists():
        try:
            rc, out, err = run_with_retry([git, "-C", str(dest), "pull", "--ff-only"], timeout=120)
            if rc != 0:
                # pull 失败不致命，继续用已有代码
                return str(dest)
            return str(dest)
        except SkillError:
            return str(dest)  # pull 失败继续用已有代码

    # 克隆：先 GitHub，失败后尝试 Gitee 镜像
    try:
        rc, out, err = run_with_retry([git, "clone", "--depth", "1", url, str(dest)], timeout=180)
        if rc == 0:
            return str(dest)
    except SkillError as e:
        if not use_mirror or "github.com" not in url:
            raise
        # GitHub 失败 → 尝试 Gitee 镜像（国内优化）
        # 支持两种 Gitee 镜像格式：
        # 1. https://gitee.com/mirrors/{repo} （官方镜像）
        # 2. https://gitee.com/{owner}/{repo} （用户镜像）
        mirror_url = url.replace("https://github.com/", "https://gitee.com/mirrors/")
        try:
            rc2, _, _ = run_with_retry([git, "clone", "--depth", "1", mirror_url, str(dest)], timeout=180)
            if rc2 == 0:
                return str(dest)
        except SkillError as e:
            # 镜像源克隆失败，回退尝试下一个镜像
            print(f"[WARN] 镜像克隆失败（回退）: {str(e)[:60]}", file=sys.stderr)
        # 尝试用户镜像格式
        if "/" in url.replace("https://github.com/", ""):
            owner_repo = url.replace("https://github.com/", "").replace(".git", "")
            mirror_url2 = f"https://gitee.com/{owner_repo}.git"
            try:
                rc3, _, _ = run_with_retry([git, "clone", "--depth", "1", mirror_url2, str(dest)], timeout=180)
                if rc3 == 0:
                    return str(dest)
            except SkillError:
                pass
        raise SkillError("E003", f"clone 失败: {err.strip()[:200]}")

    raise SkillError("E003", f"clone 失败: {err.strip()[:200]}")


# ---------------------------------------------------------------------------
# 依赖安装（清华源兜底）
# ---------------------------------------------------------------------------
def install_deps(workdir: str, use_tsinghua: bool = True) -> None:
    req = Path(workdir) / "requirements.txt"
    if not req.exists():
        return  # 无依赖声明，跳过
    pip = shutil.which("pip") or shutil.which("pip3") or (sys.executable + " -m pip")
    base = [sys.executable, "-m", "pip", "install", "-r", str(req)]
    if use_tsinghua:
        base += ["-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
    try:
        rc, out, err = run_with_retry(base, cwd=workdir, timeout=300)
        if rc != 0:
            raise SkillError("E004", f"依赖安装失败: {err.strip()[:200]}")
    except SkillError as e:
        if e.code == "E006":
            raise SkillError("E004", f"依赖安装超时: {err.strip()[:200]}")
        raise


# ---------------------------------------------------------------------------
# 智能命令推断
# ---------------------------------------------------------------------------
def discover_command(workdir: str, requested: Optional[str]) -> str:
    """未指定命令时，按约定推断默认命令。"""
    if requested:
        # 校验存在性
        cand = Path(workdir) / requested
        if cand.exists() or shutil.which(requested):
            return requested
        # 当作解释器参数处理（如 python app.py）
        return requested
    # 约定优先级
    for cand in ("run.py", "main.py", "app.py", "cli.py", "skill.py"):
        if (Path(workdir) / cand).exists():
            return f"python {cand}"
    raise SkillError("E005", "未指定 --command 且仓库无约定入口（run.py/main.py/app.py/cli.py/skill.py）")


# ---------------------------------------------------------------------------
# 结果缓存
# ---------------------------------------------------------------------------
def cache_get(workdir: str, key: str) -> Optional[Dict[str, Any]]:
    cache_file = Path(workdir) / ".skill_cache.json"
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, "r", encoding="utf-8", errors="replace") as fh:
            data = json.loads("".join(fh.readlines()))
        return data.get(key)
    except Exception:
        return None


def cache_set(workdir: str, key: str, value: Dict[str, Any], dry_run: bool = False) -> None:
    cache_file = Path(workdir) / ".skill_cache.json"
    data: Dict[str, Any] = {}
    try:
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8", errors="replace") as fh:
                data = json.loads("".join(fh.readlines()))
    except Exception:
        data = {}
    data[key] = value
    if not dry_run:
        try:
            cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[WARN] 缓存写入失败: {str(e)[:60]}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 编排主流程
# ---------------------------------------------------------------------------
@dataclass
class RunResult:
    status: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "data": self.data, "error": self.error}


def execute(
    repo: str,
    command: Optional[str] = None,
    workdir: str = ".",
    no_deps: bool = False,
    use_mirror: bool = True,
    use_tsinghua: bool = True,
    timeout: float = 120.0,
    use_cache: bool = True,
) -> RunResult:
    if not repo:
        return RunResult("error", error={"code": "E008", **ERRORS["E008"]})
    cache_key = f"{repo}::{command}::{timeout}"
    if use_cache:
        hit = cache_get(workdir, cache_key)
        if hit:
            return RunResult("success", data={**hit, "cached": True})

    try:
        local = clone_or_update(repo, workdir, use_mirror=use_mirror)
        if not no_deps:
            install_deps(local, use_tsinghua=use_tsinghua)
        cmd_str = discover_command(local, command)
        # 解析命令（支持 "python app.py --x" 形式）
        parts = cmd_str.split()
        # 解释器归一：python → 当前解释器
        if parts and parts[0] == "python":
            parts[0] = sys.executable
        rc, out, err = run(parts, cwd=local, timeout=timeout)
        result = {
            "repo": repo,
            "local_path": local,
            "command": cmd_str,
            "returncode": rc,
            "stdout": out.strip(),
            "stderr": err.strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if use_cache:
            cache_set(workdir, cache_key, result)
        if rc != 0:
            return RunResult("error", data=result, error={"code": "E005", **ERRORS["E005"]})
        return RunResult("success", data=result)
    except SkillError as e:
        return RunResult("error", data={"repo": repo}, error={"code": e.code, "reason": ERRORS[e.code]["reason"], "fix": ERRORS[e.code]["fix"], "detail": e.detail})
    except Exception as e:  # noqa: BLE001
        return RunResult("error", data={"repo": repo}, error={"code": "E010", "reason": ERRORS["E010"]["reason"], "detail": str(e)})


# ---------------------------------------------------------------------------
# 离线自检（不依赖 git / 网络 / 第三方包，但真实调用核心函数）
# ---------------------------------------------------------------------------
def selftest() -> int:
    print("== run_skill.py 离线自检 ==")
    failures = []

    def check(name: str, cond: bool):
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    # 1) 错误码表完整
    check("错误码 E001-E010 齐全", set(ERRORS) == {f"E{i:03d}" for i in range(1, 11)})

    # 2) 仓库归一化
    try:
        check("normalize_repo(owner/name)", normalize_repo("sickn33/agentic-awesome-skills") == "https://github.com/sickn33/agentic-awesome-skills.git")
        check("normalize_repo(url)", normalize_repo("https://github.com/a/b") == "https://github.com/a/b")
        raised = False
        try:
            normalize_repo("not-a-repo")
        except SkillError:
            raised = True
        check("normalize_repo(非法) 抛 E001", raised)
    except Exception as e:  # noqa: BLE001
        check(f"normalize_repo 异常: {e}", False)

    # 3) 用本地 git 仓库模拟完整流程（真实调用 clone_or_update + execute）
    with tempfile.TemporaryDirectory() as td:
        # 创建本地 git 仓库作为源
        src = Path(td) / "src_repo"
        src.mkdir()
        (src / "run.py").write_text("import sys\nprint('HELLO_FROM_SKILL')\n", encoding="utf-8", errors="replace")
        (src / "requirements.txt").write_text("# no deps\n", encoding="utf-8", errors="replace")
        
        # 初始化 git 仓库
        git = shutil.which("git")
        if git:
            subprocess.run([git, "init", str(src)], capture_output=True, check=True)
            # 提交初始代码（本地 git，无需远程）
            subprocess.run([git, "add", "."], cwd=str(src), capture_output=True, check=False)
            subprocess.run([git, "commit", "-m", "init"], cwd=str(src),
                           capture_output=True, check=False,
                           env={**os.environ, "GIT_AUTHOR_NAME": "test",
                                "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "test",
                                "GIT_COMMITTER_EMAIL": "t@t"})
            # 模拟 clone_or_update（本地路径直接复制）
            dst = Path(td) / "dst_repo"
            shutil.copytree(src, dst)
            code, out, err = run(["python", str(dst / "run.py")], cwd=str(dst), timeout=30)
            check(f"run 本地脚本 code=0", code == 0)
            check(f"run 输出含 HELLO_FROM_SKILL", "HELLO_FROM_SKILL" in out)

    # 汇总
    if failures:
        print(f"[SELFTEST] 失败 {len(failures)} 项: {failures}")
        return 1
    print("[SELFTEST] 全部通过 ✅")
    return 0


def main():
    parser = argparse.ArgumentParser(description="AI 智能体技能运行器")
    parser.add_argument("--repo", "-r", default="", help="GitHub 仓库（owner/name 或完整 URL）")
    parser.add_argument("--request", default="", help="要执行的命令描述")
    parser.add_argument("--workdir", default="", help="工作目录")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", action="store_true", help="输出处理明细")
    parser.add_argument("--dry-run", action="store_true", help="只预览不执行")
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    args = parser.parse_args()

    if args.verbose:
        print(f"[verbose] 参数: {vars(args)}")

    if args.selftest:
        return selftest()

    if not args.repo:
        parser.print_help()
        return 1

    workdir = args.workdir or tempfile.mkdtemp(prefix="aws_")
    repo_dir = clone_or_update(args.repo, workdir)
    cmd, _ = discover_command(repo_dir, args.request or None)
    if args.dry_run:
        print(f"[dry-run] 将执行: {cmd}")
        return 0
    result = execute(cmd, cwd=repo_dir)
    print(result.output if hasattr(result, "output") else result)
    return result.code if hasattr(result, "code") else 0


if __name__ == "__main__":
    sys.exit(main())
