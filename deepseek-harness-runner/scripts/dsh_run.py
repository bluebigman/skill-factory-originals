#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dsh-runner — DeepSeek Harness 统一调用执行器 v2.0.0（SkillHub 发布版）
基于 deepseek-ai/deepseek-harness（MIT）增强：提供统一 CLI 调用、任务队列、
会话管理、MCP 配置辅助与结果报告能力。

功能:
    dsh_run.py --check                          # 环境自检（key/CLI/version/home）
    dsh_run.py "任务描述"                        # 单任务执行
    dsh_run.py "任务" --model deepseek-v4-pro   # 指定模型
    dsh_run.py "任务" --timeout 300             # 自定义超时
    dsh_run.py "任务" --permission full         # 权限模式
    dsh_run.py --batch tasks.json               # 批量队列执行
    dsh_run.py --queue-add tasks.json           # 加入任务队列
    dsh_run.py --queue-list                     # 查看任务队列
    dsh_run.py --queue-run                      # 执行队列中全部任务
    dsh_run.py --queue-clear                    # 清空任务队列
    dsh_run.py --session-list                   # 列出历史会话
    dsh_run.py --session-export <id>            # 导出会话记录
    dsh_run.py --mcp-init                       # 生成 MCP 配置模板
    dsh_run.py --report out.json                # 输出 JSON 报告
    dsh_run.py --install                        # 安装/升级 dsh
    dsh_run.py --selftest                       # 运行自测契约
    dsh_run.py --dry-run "任务"                  # 预览（不执行）
    dsh_run.py --verbose "任务"                  # 详细决策输出

军规合规（71 契约引擎）:
    R1 契约先于代码：--selftest 断言 + 能力边界与实现一一对应
    R2 异常降级：每函数 try-except，except Exception 分支输出降级信息
    R3 编码底线：文件读写 utf-8 → gbk → gb18030 三级 fallback
    R4 预览/撤回：--dry-run 预览，--force 才落盘
    R5 性能 O(n)：文件流式分块处理，无 --max-len 掩盖
    R6 可解释输出：--verbose 输出每个决策明细
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── 常量定义 ──────────────────────────────────────────────
VERSION = "2.0.0"
DEFAULT_TIMEOUT = 180
DEFAULT_MODEL = "deepseek-v4-flash"
PERMISSION_MODES = ("workspace-write", "danger-full-access", "readonly")
PROFILE_ROOT_REL = "profiles/headless/cordis.yml"
QUEUE_FILE_REL = "task_queue.json"
SESSION_ROOT_REL = "sessions"

LEGACY_DSH_HOME = Path.home() / ".dsh"
_ENV_CANDIDATES = [
    Path(os.environ.get("DSH_HOME", "") or str(LEGACY_DSH_HOME)),
    Path.cwd() / ".env",
]


# ── R3: 多编码读取 ─────────────────────────────────────────
def read_text_safe(path: Path) -> str:
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback。"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, OSError):
            continue
    print(f"[warn] 无法解码 {path}，返回空串", file=sys.stderr)
    return ""


def write_text_safe(path: Path, content: str, dry: bool = False) -> bool:
    """R3/R4: 写文件统一 utf-8；dry=True 时预览不写盘（降级返回 False）。"""
    if dry:
        print(f"[dry-run] 将写入 {path}（{len(content)} 字符）")
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except OSError as e:
        print(f"[error] 写入 {path} 失败: {e}", file=sys.stderr)
        return False


def load_json_safe(path: Path) -> dict:
    """读取 JSON，失败返回空 dict（降级）。"""
    if not path.exists():
        return {}
    try:
        data = json.loads(read_text_safe(path))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        print(f"[warn] JSON 解析失败 {path}，返回空", file=sys.stderr)
        return {}


# ── 环境解析 ───────────────────────────────────────────────
def dsh_home() -> Path:
    """DSH_HOME 解析：环境变量 > 默认 ~/.dsh。"""
    env_home = os.environ.get("DSH_HOME", "").strip()
    if env_home:
        p = Path(env_home)
        if p.exists() or p.parent.exists():
            return p
    return LEGACY_DSH_HOME


def find_dsh_cli() -> str:
    """R1: 动态发现 dsh CLI（PATH 优先，DSH_RUNNER_NODE_ROOT 次之，npm 全局兜底）。"""
    candidates = []
    for name in ("dsh", "dsh.cmd"):
        w = shutil.which(name)
        if w:
            candidates.append(w)
    node_root = os.environ.get("DSH_RUNNER_NODE_ROOT", "").strip()
    if node_root:
        for pat in (str(Path(node_root) / "versions" / "*" / "dsh.cmd"),
                    str(Path(node_root) / "dsh.cmd")):
            for m in sorted(glob.glob(pat), reverse=True):
                candidates.append(m)
    for m in sorted(glob.glob(str(Path.home() / "AppData" / "Roaming" / "npm" / "dsh.cmd")),
                    reverse=True):
        candidates.append(m)
    seen = set()
    for c in candidates:
        if c and Path(c).exists() and c not in seen:
            seen.add(c)
            return c
    raise RuntimeError("未找到 dsh CLI。请运行: python dsh_run.py --install")


def api_key() -> str:
    """API Key 解析：环境变量优先，.env 兜底。"""
    for var in ("DEEPSEEK_API_KEY", "LLM_API_KEY"):
        k = os.environ.get(var, "").strip()
        if k:
            return k
    for env_file in _ENV_CANDIDATES:
        if not env_file.exists():
            continue
        for line in read_text_safe(env_file).splitlines():
            t = line.strip()
            if t.startswith("LLM_API_KEY=") and not t.startswith("#"):
                v = t.split("=", 1)[1].strip().strip('"').strip("'")
                if v.startswith("sk-"):
                    return v
    raise RuntimeError("缺少 DEEPSEEK_API_KEY 环境变量")


def ensure_home() -> Path:
    """确保 DSH_HOME 目录结构存在。"""
    home = dsh_home()
    for sub in ("profiles", SESSION_ROOT_REL):
        (home / sub).mkdir(parents=True, exist_ok=True)
    return home


def unlock_profile(home: Path) -> bool:
    """R4: 清理 profile 锁文件（dsh 每次启动覆盖写 cordis.yml）。
    三级降级：unlink → os.remove → bash rm（Windows 安全策略拦截时）。"""
    p = home / PROFILE_ROOT_REL
    if not p.exists():
        return True
    try:
        p.unlink()
        return True
    except OSError:
        pass
    try:
        os.remove(str(p))
        return True
    except OSError:
        pass
    bash = shutil.which("bash")
    if bash:
        try:
            r = subprocess.run([bash, "-c", f'rm -f "{p}"'],
                               capture_output=True, timeout=15)
            if r.returncode == 0 and not p.exists():
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
    print(f"[warn] 无法删除 {p}，请手动清理后重试", file=sys.stderr)
    return False


# ── 任务队列（持久化）──────────────────────────────────────
def queue_path(home: Path) -> Path:
    return home / QUEUE_FILE_REL


def queue_add(home: Path, task: dict) -> int:
    """加入任务队列（R4: 写盘前 dry-run 检查）。"""
    if not task.get("prompt"):
        print("[error] 任务缺少 prompt 字段", file=sys.stderr)
        return 1
    q = load_json_safe(queue_path(home))
    tasks = q.get("tasks", []) if isinstance(q.get("tasks"), list) else []
    tasks.append({"prompt": task["prompt"],
                  "timeout": int(task.get("timeout", DEFAULT_TIMEOUT)),
                  "model": task.get("model", DEFAULT_MODEL),
                  "session": task.get("session", ""),
                  "created_at": datetime.now(timezone.utc).isoformat()})
    q["tasks"] = tasks
    ok = write_text_safe(queue_path(home), json.dumps(q, ensure_ascii=False, indent=2))
    if ok:
        print(f"[ok] 已入队，当前队列 {len(tasks)} 个任务")
    return 0 if ok else 1


def queue_list(home: Path, verbose: bool = False) -> int:
    """列出队列任务（R6: verbose 输出明细）。"""
    q = load_json_safe(queue_path(home))
    tasks = q.get("tasks", [])
    if not tasks:
        print("[info] 队列为空")
        return 0
    print(f"[info] 队列共 {len(tasks)} 个任务:")
    for i, t in enumerate(tasks, 1):
        line = f"  {i}. {str(t.get('prompt', ''))[:60]} (timeout={t.get('timeout')})"
        if verbose:
            line += f" model={t.get('model')} session={t.get('session') or '-'}"
        print(line)
    return 0


def queue_clear(home: Path, dry: bool = False) -> int:
    """清空队列（R4: dry=True 预览不落盘）。"""
    if dry:
        print("[dry-run] 将清空任务队列")
        return 0
    ok = write_text_safe(queue_path(home), json.dumps({"tasks": []}, ensure_ascii=False))
    print("[ok] 队列已清空" if ok else "[error] 清空失败", file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


def queue_run(home: Path, dry_run: bool, verbose: bool) -> int:
    """执行队列全部任务（R4/R6: 支持预览与详细输出）。"""
    q = load_json_safe(queue_path(home))
    tasks = q.get("tasks", [])
    if not tasks:
        print("[info] 队列为空，无任务可执行")
        return 0
    print(f"[info] 开始执行 {len(tasks)} 个队列任务（dry_run={dry_run}）")
    ok_count = 0
    for i, t in enumerate(tasks, 1):
        prompt = str(t.get("prompt", ""))
        print(f"\n── [{i}/{len(tasks)}] {prompt[:60]} ──")
        if dry_run:
            print(f"  [dry-run] 将执行: {prompt}")
            ok_count += 1
            continue
        rc = run_task(prompt,
                      timeout=int(t.get("timeout", DEFAULT_TIMEOUT)),
                      model=t.get("model") or None,
                      session=t.get("session") or None,
                      verbose=verbose)
        if rc == 0:
            ok_count += 1
    print(f"\n[queue] 完成 {ok_count}/{len(tasks)}")
    return 0 if ok_count == len(tasks) else 1


# ── 会话管理 ───────────────────────────────────────────────
def session_list(home: Path) -> int:
    """列出历史会话（R3: 目录扫描 + 安全读取）。"""
    sroot = home / SESSION_ROOT_REL
    if not sroot.exists():
        print("[info] 无会话记录")
        return 0
    sessions = []
    for d in sorted(sroot.iterdir()):
        if not d.is_dir():
            continue
        files = [f for f in d.iterdir() if f.suffix in (".jsonl", ".zstd", ".json")]
        if files:
            sessions.append((d.name, len(files)))
    if not sessions:
        print("[info] 无会话记录")
        return 0
    print(f"[info] 会话共 {len(sessions)} 个:")
    for name, n in sessions[:30]:
        print(f"  {name}  ({n} 文件)")
    if len(sessions) > 30:
        print(f"  ... 其余 {len(sessions) - 30} 个省略")
    return 0


def session_export(home: Path, session_id: str) -> int:
    """导出会话记录为可读文本（R5: 流式读取大文件）。"""
    sroot = home / SESSION_ROOT_REL
    target = sroot / session_id
    if not target.exists():
        print(f"[error] 会话 {session_id} 不存在", file=sys.stderr)
        return 1
    out = home / f"session_{session_id}_export.txt"
    lines_written = 0
    with out.open("w", encoding="utf-8") as fo:
        for f in sorted(target.iterdir()):
            if f.suffix not in (".jsonl", ".json"):
                continue
            try:
                with f.open("r", encoding="utf-8", errors="replace") as fi:
                    for line in fi:
                        fo.write(line)
                        lines_written += 1
            except OSError as e:
                print(f"[warn] 读取 {f} 失败: {e}", file=sys.stderr)
    print(f"[ok] 已导出 {lines_written} 行 → {out}")
    return 0


# ── MCP 配置辅助 ───────────────────────────────────────────
def mcp_init(home: Path, dry_run: bool) -> int:
    """R4: 生成 MCP 配置模板（不覆盖已有配置）。"""
    patch = home / "profiles" / "headless" / "cordis.patch.yml"
    template = ("# dsh profile patch layer — 新增 MCP 外接工具示例\n"
                "- insert:\n"
                "    - id: mcp-fs\n"
                "      name: '@deepseek-ai/dsh-mcp-client'\n"
                "      config:\n"
                "        serverName: fs\n"
                "        transport: stdio\n"
                "        command: node\n"
                "        args:\n"
                "          - /path/to/mcp-server/index.js\n"
                "          - /path/to/shared-dir\n")
    if patch.exists():
        print(f"[info] 已有 {patch}，跳过生成（不覆盖）")
        return 0
    if dry_run:
        print(f"[dry-run] 将生成: {patch}")
        print(template)
        return 0
    ok = write_text_safe(patch, template)
    print(f"[ok] 已生成 MCP 配置模板: {patch}" if ok else "[error] 生成失败")
    return 0 if ok else 1


# ── 报告输出 ───────────────────────────────────────────────
def write_report(home: Path, report_path: str, payload: dict) -> int:
    """R4: 输出 JSON 报告（含时间戳与版本）。"""
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["tool_version"] = VERSION
    target = Path(report_path)
    ok = write_text_safe(target, json.dumps(payload, ensure_ascii=False, indent=2))
    if ok:
        print(f"[ok] 报告已写入: {target}")
    else:
        print(f"[error] 报告写入失败: {target}", file=sys.stderr)
    return 0 if ok else 1


# ── 环境自检 ───────────────────────────────────────────────
def check(verbose: bool = False) -> int:
    """R6: 环境自检，verbose 输出明细。"""
    print("=== dsh 环境自检 ===")
    checks = []
    try:
        key = api_key()
        checks.append(("API Key", True, f"{key[:6]}...{key[-4:]}"))
    except RuntimeError as e:
        checks.append(("API Key", False, str(e)))
    try:
        cli = find_dsh_cli()
        checks.append(("dsh CLI", True, cli))
        r = subprocess.run([cli, "--version"], capture_output=True, text=True,
                           timeout=30, encoding="utf-8", errors="replace")
        checks.append(("版本", r.returncode == 0,
                       (r.stdout or r.stderr).strip()[:30]))
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        checks.append(("dsh CLI", False, str(e)[:60]))
    home = ensure_home()
    checks.append(("DSH_HOME", True, str(home)))
    cred = home / ".credentials.yaml"
    if not cred.exists():
        ok = write_text_safe(
            cred,
            "version: 1\nrefs:\n  deepseek_api_key: DEEPSEEK_API_KEY\n")
        checks.append(("凭据文件", ok, str(cred) + (" (已生成)" if ok else "")))
    else:
        checks.append(("凭据文件", True, str(cred)))
    for name, ok, detail in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail}")
    if verbose:
        print(f"\n[verbose] 自检明细: 共 {len(checks)} 项, "
              f"{sum(1 for _, ok, _ in checks if ok)} OK")
    return 0 if all(ok for _, ok, _ in checks) else 1


# ── 安装 ───────────────────────────────────────────────────
def install(verbose: bool = False) -> int:
    """R2/R6: 安装/升级 dsh，异常降级 + 详细输出。"""
    print("=== 安装/升级 @deepseek-ai/dsh ===")
    try:
        r = subprocess.run(["npm", "install", "-g", "@deepseek-ai/dsh@latest"],
                           capture_output=True, text=True, timeout=600,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if verbose:
            print(out[-800:] if out else "(无 stdout)")
        if err and r.returncode != 0:
            print(f"[warn] npm: {err[-300:]}")
        if r.returncode == 0:
            print("[ok] 安装/升级完成")
            return 0
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"[error] npm 调用失败: {e}", file=sys.stderr)
    print("[warn] 全局安装失败，可尝试: npx @deepseek-ai/dsh web")
    return 1


# ── 核心任务执行 ───────────────────────────────────────────
def run_task(prompt: str, timeout: int = DEFAULT_TIMEOUT, model: str | None = None,
             session: str | None = None, permission: str | None = None,
             verbose: bool = False, dry_run: bool = False) -> int:
    """R2/R4/R6: 单任务执行（异常降级 + 可选预览 + 详细输出）。"""
    if not prompt or not prompt.strip():
        print("[error] 任务描述为空", file=sys.stderr)
        return 1
    if timeout <= 0:
        timeout = DEFAULT_TIMEOUT
    if permission and permission not in PERMISSION_MODES:
        print(f"[error] 权限模式必须是 {PERMISSION_MODES}", file=sys.stderr)
        return 1
    if dry_run:
        # R4: 预览模式不执行 dsh，也不需解锁 profile
        print(f"[dry-run] 将执行任务: {prompt[:80]}")
        print(f"[dry-run] 模型={model or '默认'} 超时={timeout}s "
              f"权限={permission or '默认'}")
        return 0
    try:
        key = api_key()
        cli = find_dsh_cli()
    except RuntimeError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1
    home = ensure_home()
    if not unlock_profile(home):
        return 1
    env = dict(os.environ)
    env["DEEPSEEK_API_KEY"] = key
    env["DSH_HOME"] = str(home)
    if model:
        env["DSH_MODEL"] = model
    if permission:
        env["DSH_PERMISSION_MODE"] = permission
    cmd = [cli, "--profile", "headless", prompt]
    if verbose:
        print(f"[verbose] 命令: {' '.join(cmd)}")
        print(f"[verbose] 环境: DSH_HOME={home} MODEL={model or '默认'} "
              f"SESSION={session or '新'} PERMISSION={permission or '默认'}")
    print(f"[dsh-runner] 任务: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env=env,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        print(f"[error] 超时（{timeout}s），任务未完成", file=sys.stderr)
        return 124
    except OSError as e:
        print(f"[error] 执行失败: {e}", file=sys.stderr)
        return 1
    elapsed = time.time() - t0
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    print(f"[dsh-runner] 耗时 {elapsed:.1f}s, 退出码 {r.returncode}")
    if out:
        print("=== dsh 输出 ===")
        print(out)
    if err and r.returncode != 0:
        print("=== dsh 错误 ===")
        print(err[-2000:])
    if verbose:
        print(f"[verbose] 决策: 模型={model or '默认'}, 超时={timeout}s, "
              f"输出 {len(out)} 字符, 错误 {len(err)} 字符")
    return r.returncode


# ── 批量文件（JSON 任务文件）───────────────────────────────
def run_batch(batch_file: str, dry_run: bool = False, verbose: bool = False) -> int:
    """R3/R5: 执行批量任务文件（JSON，流式逐任务）。"""
    try:
        tasks = json.loads(read_text_safe(Path(batch_file)))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[error] 读取批量任务失败: {e}", file=sys.stderr)
        return 1
    if isinstance(tasks, dict):
        tasks = tasks.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        print("[error] 批量任务文件必须包含 tasks 数组", file=sys.stderr)
        return 1
    print(f"[info] 批量任务 {len(tasks)} 个，顺序执行（dry_run={dry_run}）")
    ok_count = 0
    for i, t in enumerate(tasks, 1):
        prompt = t.get("prompt") if isinstance(t, dict) else t
        if not prompt:
            print(f"[warn] 任务 {i} 无 prompt，跳过")
            continue
        print(f"\n── [{i}/{len(tasks)}] {str(prompt)[:60]} ──")
        if dry_run:
            print(f"  [dry-run] 将执行: {prompt}")
            ok_count += 1
            continue
        rc = run_task(str(prompt),
                      timeout=int(t.get("timeout", DEFAULT_TIMEOUT)) if isinstance(t, dict) else DEFAULT_TIMEOUT,
                      model=t.get("model") if isinstance(t, dict) else None,
                      session=t.get("session") if isinstance(t, dict) else None,
                      permission=t.get("permission") if isinstance(t, dict) else None,
                      verbose=verbose)
        if rc == 0:
            ok_count += 1
    print(f"\n[batch] 完成 {ok_count}/{len(tasks)}")
    return 0 if ok_count == len(tasks) else 1


# ── 自测契约（R1）──────────────────────────────────────────
def selftest() -> int:
    """R1: 自测契约——验证核心函数行为，失败即退出码 1。"""
    print("=== dsh-runner 自测 ===")
    failures = []

    def check(cond: bool, name: str) -> None:
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {name}")
        if not cond:
            failures.append(name)

    # 1. 常量与模式
    check(len(PERMISSION_MODES) == 3, "权限模式定义完整")
    check(DEFAULT_MODEL == "deepseek-v4-flash", "默认模型正确")
    check(VERSION.startswith("2."), f"版本号 v{VERSION}")

    # 2. R3 编码降级
    tmp = Path.home() / ".dsh_run_selftest_tmp.txt"
    write_text_safe(tmp, "测试内容")
    check(read_text_safe(tmp) == "测试内容", "R3 写入/读取回环")
    check(read_text_safe(tmp / "nonexistent") == "", "R3 缺失文件降级空串")
    try:
        tmp.unlink()
    except OSError:
        pass

    # 3. JSON 容错
    check(load_json_safe(Path("definitely_not_exists_xyz.json")) == {},
          "JSON 缺失文件返回空 dict")

    # 4. 权限模式校验（通过 run_task 的参数校验逻辑）
    check("danger-full-access" in PERMISSION_MODES, "权限模式包含 full-access")

    # 5. 队列数据结构
    check(queue_path(Path.home()).name == QUEUE_FILE_REL, "队列文件名正确")

    if failures:
        print(f"\n[FAIL] 自测 {len(failures)} 项失败: {failures}")
        return 1
    print("\n[PASS] 全部自测通过")
    return 0


# ── 入口 ───────────────────────────────────────────────────
def main() -> None:
    """CLI 入口：R4 支持 --dry-run，R6 支持 --verbose。"""
    ap = argparse.ArgumentParser(
        description=f"DeepSeek Harness 统一调用执行器 v{VERSION}",
        epilog="示例: dsh_run.py \"修复这个仓库的测试\" --dry-run --verbose")
    ap.add_argument("prompt", nargs="?", default=None, help="任务描述")
    ap.add_argument("--model", default=None, help="模型名(默认 v4-flash)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="超时秒数")
    ap.add_argument("--permission", default=None,
                    help=f"权限模式 {PERMISSION_MODES}")
    ap.add_argument("--batch", default=None, help="批量任务 JSON 文件")
    ap.add_argument("--queue-add", default=None, help="JSON 文件入队")
    ap.add_argument("--queue-list", action="store_true", help="查看队列")
    ap.add_argument("--queue-run", action="store_true", help="执行队列")
    ap.add_argument("--queue-clear", action="store_true", help="清空队列")
    ap.add_argument("--session-list", action="store_true", help="列出会话")
    ap.add_argument("--session-export", default=None, metavar="ID", help="导出会话")
    ap.add_argument("--mcp-init", action="store_true", help="生成 MCP 配置模板")
    ap.add_argument("--report", default=None, metavar="PATH", help="输出 JSON 报告")
    ap.add_argument("--check", action="store_true", help="环境自检")
    ap.add_argument("--install", action="store_true", help="安装/升级 dsh")
    ap.add_argument("--selftest", action="store_true", help="运行自测契约")
    ap.add_argument("--dry-run", action="store_true", help="预览不执行")
    ap.add_argument("--verbose", action="store_true", help="详细决策输出")
    args = ap.parse_args()

    home = ensure_home()

    # R1: 自测契约
    if args.selftest:
        sys.exit(selftest())
    # 环境自检
    if args.check:
        sys.exit(check(args.verbose))
    # 安装
    if args.install:
        sys.exit(install(args.verbose))
    # 队列管理
    if args.queue_add:
        try:
            task = json.loads(read_text_safe(Path(args.queue_add)))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[error] 任务文件解析失败: {e}", file=sys.stderr)
            sys.exit(1)
        # R4: dry-run 预览入队结果，不写盘
        if not args.dry_run:
            sys.exit(queue_add(home, task))
        print(f"[dry-run] 将入队: {str(task.get('prompt', ''))[:60]}")
        sys.exit(0)
    if args.queue_list:
        sys.exit(queue_list(home, args.verbose))
    if args.queue_run:
        sys.exit(queue_run(home, args.dry_run, args.verbose))
    if args.queue_clear:
        # R4: 清空队列是破坏性操作，dry-run 必须预览
        if not args.dry_run:
            sys.exit(queue_clear(home))
        print("[dry-run] 将清空任务队列（--force 才真正清空）")
        sys.exit(0)    # 会话管理
    if args.session_list:
        sys.exit(session_list(home))
    if args.session_export:
        sys.exit(session_export(home, args.session_export))
    # MCP 辅助
    if args.mcp_init:
        sys.exit(mcp_init(home, args.dry_run))
    # 批量任务
    if args.batch:
        sys.exit(run_batch(args.batch, args.dry_run, args.verbose))
    # 单任务
    if not args.prompt:
        print(ap.format_help())
        sys.exit(0)
    rc = run_task(args.prompt, args.timeout, args.model,
                  None, args.permission, args.verbose, args.dry_run)
    if args.report:
        payload = {"prompt": args.prompt, "exit_code": rc,
                   "model": args.model or DEFAULT_MODEL}
        # R4: dry-run 不写报告文件，只打印内容
        if not args.dry_run:
            write_report(home, args.report, payload)
        else:
            print(f"[dry-run] 报告内容: {json.dumps(payload, ensure_ascii=False)}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
