#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cheat-sh-pro — 命令行速查手册

一条命令获取编程语言与工具示例，开发调试即时查阅。
支持模糊搜索、领域过滤、随机速查、Markdown/JSON 导出。
纯标准库，零第三方依赖。

用法示例:
    python run.py search python --query list
    python run.py random docker
    python run.py list-domains
    python run.py export --format markdown --output cheats.md
    python run.py --selftest
"""

from __future__ import annotations
dry_run = False  # v3.274 模块级 dry-run 标志

import argparse
import difflib
import json
import os
import random
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量与默认数据
# ---------------------------------------------------------------------------

DEFAULT_CHEATS: Dict[str, List[Dict[str, str]]] = {
    "git": [
        {"cmd": "git log --oneline -10", "desc": "查看最近10条提交（简洁）", "scene": "快速回顾提交历史"},
        {"cmd": "git status -sb", "desc": "查看工作区状态（短格式+分支）", "scene": "提交前检查"},
        {"cmd": "git diff --stat", "desc": "查看未暂存改动统计", "scene": "提交前概览改动量"},
        {"cmd": "git stash push -m 'wip'", "desc": "暂存当前改动", "scene": "临时切换分支"},
        {"cmd": "git branch -a", "desc": "查看全部分支（含远程）", "scene": "确认分支存在性"},
        {"cmd": "git checkout -b feat/xx", "desc": "新建并切换分支", "scene": "开始新功能"},
        {"cmd": "git commit --amend -m 'new msg'", "desc": "修改最近一次提交信息", "scene": "提交信息写错"},
        {"cmd": "git log --graph --oneline --all", "desc": "图形化查看全部分支提交", "scene": "梳理分支结构"},
        {"cmd": "git reset --soft HEAD~1", "desc": "撤销提交但保留改动", "scene": "提交错了要重来"},
        {"cmd": "git blame -L 10,20 file.py", "desc": "查看指定行历史归属", "scene": "排查代码来源"},
    ],
    "docker": [
        {"cmd": "docker ps -a", "desc": "查看所有容器（含停止）", "scene": "找容器"},
        {"cmd": "docker images", "desc": "查看本地镜像列表", "scene": "确认镜像"},
        {"cmd": "docker exec -it c1 bash", "desc": "进入容器终端", "scene": "容器内调试"},
        {"cmd": "docker logs -f c1", "desc": "跟踪容器日志", "scene": "排查容器问题"},
        {"cmd": "docker build -t myapp .", "desc": "构建镜像", "scene": "打包应用"},
        {"cmd": "docker run -d -p 8080:80 nginx", "desc": "后台运行容器并映射端口", "scene": "部署服务"},
        {"cmd": "docker stop c1", "desc": "停止容器", "scene": "停止服务"},
        {"cmd": "docker rm c1", "desc": "删除容器", "scene": "清理容器"},
        {"cmd": "docker rmi myapp", "desc": "删除镜像", "scene": "清理镜像"},
        {"cmd": "docker network ls", "desc": "查看网络列表", "scene": "网络管理"},
    ],
    "python": [
        {"cmd": "python -m venv venv", "desc": "创建虚拟环境", "scene": "隔离项目依赖"},
        {"cmd": "pip install -r requirements.txt", "desc": "安装依赖", "scene": "部署项目"},
        {"cmd": "python -m pip list", "desc": "查看已安装包", "scene": "检查依赖"},
        {"cmd": "python -c \"print('hi')\"", "desc": "执行单行代码", "scene": "快速测试"},
        {"cmd": "python -m json.tool data.json", "desc": "格式化 JSON 文件", "scene": "调试 JSON"},
        {"cmd": "python -m http.server 8000", "desc": "启动简易 HTTP 服务", "scene": "共享文件"},
        {"cmd": "python -m pdb script.py", "desc": "调试 Python 脚本", "scene": "排查 bug"},
        {"cmd": "python -m cProfile script.py", "desc": "性能分析", "scene": "优化性能"},
        {"cmd": "python -m unittest test.py", "desc": "运行单元测试", "scene": "测试代码"},
        {"cmd": "python -m pip freeze > requirements.txt", "desc": "导出依赖清单", "scene": "记录依赖"},
    ],
    "linux": [
        {"cmd": "grep -r 'pattern' /path", "desc": "递归搜索文件内容", "scene": "查找代码"},
        {"cmd": "find /path -name '*.py'", "desc": "按文件名查找", "scene": "定位文件"},
        {"cmd": "ps aux | grep python", "desc": "查看进程", "scene": "检查运行状态"},
        {"cmd": "kill -9 PID", "desc": "强制终止进程", "scene": "结束异常进程"},
        {"cmd": "df -h", "desc": "查看磁盘使用情况", "scene": "检查磁盘空间"},
        {"cmd": "du -sh *", "desc": "查看目录大小", "scene": "分析磁盘占用"},
        {"cmd": "tar -czf archive.tar.gz /path", "desc": "压缩文件", "scene": "打包备份"},
        {"cmd": "tar -xzf archive.tar.gz", "desc": "解压文件", "scene": "解压备份"},
        {"cmd": "chmod +x script.sh", "desc": "添加执行权限", "scene": "运行脚本"},
        {"cmd": "ln -s /target /link", "desc": "创建软链接", "scene": "快捷访问"},
    ],
    "mysql": [
        {"cmd": "mysql -u root -p", "desc": "连接 MySQL", "scene": "数据库管理"},
        {"cmd": "SHOW DATABASES;", "desc": "查看数据库列表", "scene": "浏览数据库"},
        {"cmd": "USE dbname;", "desc": "切换数据库", "scene": "选择数据库"},
        {"cmd": "SHOW TABLES;", "desc": "查看表列表", "scene": "浏览表"},
        {"cmd": "DESCRIBE tablename;", "desc": "查看表结构", "scene": "了解表字段"},
        {"cmd": "SELECT * FROM table LIMIT 10;", "desc": "查询前10条数据", "scene": "快速查看数据"},
        {"cmd": "EXPLAIN SELECT ...;", "desc": "查看执行计划", "scene": "优化查询"},
        {"cmd": "CREATE DATABASE dbname;", "desc": "创建数据库", "scene": "新建数据库"},
        {"cmd": "DROP TABLE tablename;", "desc": "删除表", "scene": "清理表"},
        {"cmd": "mysqldump -u root -p dbname > backup.sql", "desc": "备份数据库", "scene": "数据备份"},
    ],
}

# 领域别名映射（用于模糊匹配领域名）
DOMAIN_ALIASES: Dict[str, str] = {
    "py": "python",
    "pyth": "python",
    "dock": "docker",
    "container": "docker",
    "lin": "linux",
    "bash": "linux",
    "shell": "linux",
    "mysql": "mysql",
    "sql": "mysql",
    "maria": "mysql",
    "git": "git",
    "github": "git",
}

# 错误码定义
EXIT_OK = 0
EXIT_USAGE_ERROR = 2
EXIT_DATA_ERROR = 3
EXIT_IO_ERROR = 4
EXIT_UNKNOWN_ERROR = 5


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def utc_now_str() -> str:
    """返回 UTC 当前时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def normalize_domain(domain: str) -> str:
    """将用户输入的领域名标准化为内置领域名。

    支持别名映射和模糊匹配。若无法匹配，返回原字符串。
    """
    domain_lower = domain.strip().lower()
    if domain_lower in DEFAULT_CHEATS:
        return domain_lower
    if domain_lower in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[domain_lower]
    # 模糊匹配
    matches = difflib.get_close_matches(domain_lower, DEFAULT_CHEATS.keys(), n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return domain_lower


def load_cheats(data_dir: Optional[Path] = None) -> Dict[str, List[Dict[str, str]]]:
    """加载速查数据。

    优先从 data_dir 加载 JSON 数据文件，若不存在则使用内置默认数据。
    若 data_dir 中的文件损坏，降级使用内置数据并打印警告。

    Args:
        data_dir: 可选的数据目录。若为 None，使用内置数据。

    Returns:
        速查数据字典，格式为 {domain: [{cmd, desc, scene}, ...]}
    """
    if data_dir is None:
        return DEFAULT_CHEATS

    data_file = data_dir / "cheats.json"
    if not data_file.exists():
        return DEFAULT_CHEATS

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 校验数据格式
        if not isinstance(data, dict):
            print(f"[警告] 数据文件格式错误（应为字典），使用内置数据: {data_file}", file=sys.stderr)
            return DEFAULT_CHEATS
        for domain, items in data.items():
            if not isinstance(items, list):
                print(f"[警告] 领域 {domain} 数据格式错误（应为列表），使用内置数据", file=sys.stderr)
                return DEFAULT_CHEATS
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[警告] 读取数据文件失败（{e}），使用内置数据: {data_file}", file=sys.stderr)
        return DEFAULT_CHEATS


def save_cheats(data: Dict[str, List[Dict[str, str]]], data_dir: Path) -> bool:
    """保存速查数据到指定目录。

    原子化写入：先写临时文件，再替换目标文件。

    Args:
        data: 速查数据字典
        data_dir: 目标数据目录

    Returns:
        是否保存成功
    """
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        data_file = data_dir / "cheats.json"
        # 原子写入
        fd, tmp_path = tempfile.mkstemp(dir=str(data_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, data_file)
        except Exception:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        return True
    except OSError as e:
        print(f"[错误] 保存数据失败: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# 核心功能：搜索
# ---------------------------------------------------------------------------

def search_cheats(
    cheats: Dict[str, List[Dict[str, str]]],
    domain: str,
    query: str,
    verbose: bool = False,
) -> Tuple[int, List[Tuple[str, Dict[str, str], float]]]:
    """在指定领域中搜索速查条目。

    使用 difflib 模糊匹配，返回匹配度排序的结果。

    Args:
        cheats: 速查数据字典
        domain: 领域名（已标准化）
        query: 搜索关键词
        verbose: 是否输出详细匹配信息

    Returns:
        (匹配数量, 匹配结果列表)
        匹配结果列表元素为 (领域, 条目字典, 匹配度)
    """
    if domain not in cheats:
        return 0, []

    query_lower = query.strip().lower()
    if not query_lower:
        return 0, []

    results: List[Tuple[str, Dict[str, str], float]] = []
    for item in cheats[domain]:
        # 在 cmd、desc、scene 三个字段中搜索
        searchable_text = f"{item.get('cmd', '')} {item.get('desc', '')} {item.get('scene', '')}"
        searchable_lower = searchable_text.lower()

        # 精确匹配优先
        if query_lower in searchable_lower:
            score = 1.0
        else:
            # 模糊匹配
            ratio = difflib.SequenceMatcher(None, query_lower, searchable_lower).ratio()
            if ratio < 0.3:
                continue
            score = ratio

        results.append((domain, item, score))

    # 按匹配度降序排序
    results.sort(key=lambda x: x[2], reverse=True)

    if verbose:
        for domain_name, item, score in results:
            print(f"  [匹配度 {score:.2f}] {item.get('cmd', '')}")

    return len(results), results


# ---------------------------------------------------------------------------
# 核心功能：随机速查
# ---------------------------------------------------------------------------

def random_cheat(
    cheats: Dict[str, List[Dict[str, str]]],
    domain: Optional[str] = None,
) -> Optional[Tuple[str, Dict[str, str]]]:
    """随机获取一条速查条目。

    Args:
        cheats: 速查数据字典
        domain: 可选的领域名。若为 None，从所有领域中随机选择。

    Returns:
        (领域名, 条目字典) 或 None（无数据时）
    """
    if not cheats:
        return None

    if domain is not None:
        if domain not in cheats or not cheats[domain]:
            return None
        return domain, random.choice(cheats[domain])

    # 从所有非空领域中随机选择
    non_empty_domains = [d for d, items in cheats.items() if items]
    if not non_empty_domains:
        return None
    chosen_domain = random.choice(non_empty_domains)
    return chosen_domain, random.choice(cheats[chosen_domain])


# ---------------------------------------------------------------------------
# 核心功能：导出
# ---------------------------------------------------------------------------

def export_markdown(cheats: Dict[str, List[Dict[str, str]]]) -> str:
    """将速查数据导出为 Markdown 格式。

    Args:
        cheats: 速查数据字典

    Returns:
        Markdown 格式的字符串
    """
    lines: List[str] = []
    lines.append("# 命令行速查手册\n")
    lines.append(f"> 生成时间: {utc_now_str()}\n")
    lines.append(f"> 共 {len(cheats)} 个领域\n")

    for domain in sorted(cheats.keys()):
        items = cheats[domain]
        lines.append(f"\n## {domain}\n")
        lines.append("| 命令 | 描述 | 场景 |")
        lines.append("|------|------|------|")
        for item in items:
            cmd = item.get("cmd", "").replace("|", "\\|")
            desc = item.get("desc", "").replace("|", "\\|")
            scene = item.get("scene", "").replace("|", "\\|")
            lines.append(f"| `{cmd}` | {desc} | {scene} |")

    return "\n".join(lines) + "\n"


def export_json(cheats: Dict[str, List[Dict[str, str]]]) -> str:
    """将速查数据导出为 JSON 格式。

    Args:
        cheats: 速查数据字典

    Returns:
        JSON 格式的字符串
    """
    return json.dumps(cheats, ensure_ascii=False, indent=2)


def export_cheats(
    cheats: Dict[str, List[Dict[str, str]]],
    fmt: str,
    output: Optional[Path],
    dry_run: bool = False,
) -> bool:
    """导出速查数据到文件或标准输出。

    Args:
        cheats: 速查数据字典
        fmt: 导出格式（markdown 或 json）
        output: 输出文件路径。若为 None，输出到标准输出。
        dry_run: 是否仅预览（不写文件）

    Returns:
        是否成功
    """
    if fmt == "markdown":
        content = export_markdown(cheats)
    elif fmt == "json":
        content = export_json(cheats)
    else:
        print(f"[错误] 不支持的导出格式: {fmt}", file=sys.stderr)
        return False

    if output is None:
        # 输出到标准输出
        print(content)
        return True

    if dry_run:
        print(f"[dry-run] 将写入 {output}（{len(content)} 字节）")
        return True

    try:
        # 原子写入
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(output.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, output)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        print(f"[export] 已导出 {len(cheats)} 个领域到 {output}")
        return True
    except OSError as e:
        print(f"[错误] 导出失败: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# 核心功能：领域列表
# ---------------------------------------------------------------------------

def list_domains(cheats: Dict[str, List[Dict[str, str]]]) -> List[str]:
    """获取所有可用领域名列表。

    Args:
        cheats: 速查数据字典

    Returns:
        排序后的领域名列表
    """
    return sorted(cheats.keys())


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """运行自检，验证核心功能正常。

    真实调用核心函数并断言关键输出。

    Returns:
        退出码（0 表示成功，非 0 表示失败）
    """
    print("[selftest] 开始自检...")
    failures = 0

    # 1. 测试数据加载
    print("[selftest] 1. 测试数据加载...")
    cheats = load_cheats()
    if not cheats:
        print("[selftest] 失败: 数据加载为空", file=sys.stderr)
        failures += 1
    else:
        print(f"[selftest] 通过: 加载 {len(cheats)} 个领域")

    # 2. 测试领域标准化
    print("[selftest] 2. 测试领域标准化...")
    test_cases = [
        ("py", "python"),
        ("PY", "python"),
        ("dock", "docker"),
        ("git", "git"),
        ("unknown_domain_xyz", "unknown_domain_xyz"),
    ]
    for input_domain, expected in test_cases:
        result = normalize_domain(input_domain)
        if result != expected:
            print(f"[selftest] 失败: normalize_domain('{input_domain}') = '{result}', 期望 '{expected}'", file=sys.stderr)
            failures += 1
        else:
            print(f"[selftest] 通过: normalize_domain('{input_domain}') = '{result}'")

    # 3. 测试搜索功能
    print("[selftest] 3. 测试搜索功能...")
    count, results = search_cheats(cheats, "python", "list")
    if count == 0:
        print("[selftest] 失败: 搜索 'python list' 无结果", file=sys.stderr)
        failures += 1
    else:
        print(f"[selftest] 通过: 搜索 'python list' 返回 {count} 条结果")

    # 测试空查询
    count, results = search_cheats(cheats, "python", "")
    if count != 0:
        print("[selftest] 失败: 空查询应返回 0 条结果", file=sys.stderr)
        failures += 1
    else:
        print("[selftest] 通过: 空查询返回 0 条结果")

    # 测试不存在的领域
    count, results = search_cheats(cheats, "nonexistent", "test")
    if count != 0:
        print("[selftest] 失败: 不存在的领域应返回 0 条结果", file=sys.stderr)
        failures += 1
    else:
        print("[selftest] 通过: 不存在的领域返回 0 条结果")

    # 4. 测试随机速查
    print("[selftest] 4. 测试随机速查...")
    result = random_cheat(cheats, "git")
    if result is None:
        print("[selftest] 失败: 随机速查 git 返回 None", file=sys.stderr)
        failures += 1
    else:
        domain, item = result
        if domain != "git" or not item:
            print("[selftest] 失败: 随机速查 git 返回异常结果", file=sys.stderr)
            failures += 1
        else:
            print(f"[selftest] 通过: 随机速查 git 返回 '{item.get('cmd', '')}'")

    # 测试不存在的领域
    result = random_cheat(cheats, "nonexistent")
    if result is not None:
        print("[selftest] 失败: 随机速查不存在的领域应返回 None", file=sys.stderr)
        failures += 1
    else:
        print("[selftest] 通过: 随机速查不存在的领域返回 None")

    # 5. 测试导出功能
    print("[selftest] 5. 测试导出功能...")
    md_content = export_markdown(cheats)
    if not md_content or "# 命令行速查手册" not in md_content:
        print("[selftest] 失败: Markdown 导出内容异常", file=sys.stderr)
        failures += 1
    else:
        print(f"[selftest] 通过: Markdown 导出 {len(md_content)} 字符")

    json_content = export_json(cheats)
    try:
        parsed = json.loads(json_content)
        if not isinstance(parsed, dict):
            print("[selftest] 失败: JSON 导出格式错误", file=sys.stderr)
            failures += 1
        else:
            print(f"[selftest] 通过: JSON 导出 {len(json_content)} 字符")
    except json.JSONDecodeError as e:
        print(f"[selftest] 失败: JSON 导出解析失败: {e}", file=sys.stderr)
        failures += 1

    # 6. 测试领域列表
    print("[selftest] 6. 测试领域列表...")
    domains = list_domains(cheats)
    if not domains:
        print("[selftest] 失败: 领域列表为空", file=sys.stderr)
        failures += 1
    else:
        print(f"[selftest] 通过: 领域列表包含 {len(domains)} 个领域: {', '.join(domains[:3])}...")

    # 7. 测试导出到文件（临时目录）
    print("[selftest] 7. 测试导出到文件...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_export.md"
        success = export_cheats(cheats, "markdown", tmp_path, dry_run=False)
        if not success or not tmp_path.exists():
            print("[selftest] 失败: 导出到文件失败", file=sys.stderr)
            failures += 1
        else:
            print(f"[selftest] 通过: 导出到文件 {tmp_path} ({tmp_path.stat().st_size} 字节)")

        # 测试 dry-run
        tmp_path2 = Path(tmpdir) / "test_dryrun.md"
        success = export_cheats(cheats, "markdown", tmp_path2, dry_run=True)
        if not success or tmp_path2.exists():
            print("[selftest] 失败: dry-run 不应写文件", file=sys.stderr)
            failures += 1
        else:
            print("[selftest] 通过: dry-run 不写文件")

    # 8. 测试数据保存与加载
    print("[selftest] 8. 测试数据保存与加载...")
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        success = save_cheats(cheats, data_dir)
        if not success:
            print("[selftest] 失败: 保存数据失败", file=sys.stderr)
            failures += 1
        else:
            loaded = load_cheats(data_dir)
            if loaded != cheats:
                print("[selftest] 失败: 加载的数据与保存的数据不一致", file=sys.stderr)
                failures += 1
            else:
                print("[selftest] 通过: 数据保存与加载一致")

    # 汇总
    if failures == 0:
        print("[selftest] 全部通过 ✓")
        return EXIT_OK
    else:
        print(f"[selftest] {failures} 项失败 ✗", file=sys.stderr)
        return EXIT_UNKNOWN_ERROR


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="命令行速查手册 — 终端内即时获取编程语言与工具代码示例",
        epilog="示例: python run.py search python --query list",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # search 子命令
    search_parser = subparsers.add_parser("search", help="搜索速查条目")
    search_parser.add_argument("--domain", help="领域名（如 python、git、docker）")
    search_parser.add_argument("--query", "-q", required=False, help="搜索关键词")
    search_parser.add_argument("--verbose", "-v", action="store_true", help="显示匹配度详情")

    # random 子命令
    random_parser = subparsers.add_parser("random", help="随机获取一条速查")
    random_parser.add_argument("--domain", nargs="?", default=None, help="领域名（可选）")

    # list-domains 子命令
    subparsers.add_parser("list-domains", help="列出所有可用领域")

    # export 子命令
    export_parser = subparsers.add_parser("export", help="导出速查数据")
    export_parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="导出格式")
    export_parser.add_argument("--output", "-o", type=Path, default=None, help="输出文件路径（默认输出到标准输出）")
    export_parser.add_argument("--dry-run", action="store_true", help="仅预览，不写文件")

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--data-dir", type=Path, default=None, help="自定义数据目录")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。

    Args:
        argv: 命令行参数列表。若为 None，使用 sys.argv[1:]。

    Returns:
        退出码
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 加载数据
    cheats = load_cheats(args.data_dir)

    # 无子命令时显示帮助
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE_ERROR

    # 处理子命令
    if args.command == "search":
        domain = normalize_domain(args.domain)
        if domain not in cheats:
            print(f"[错误] 领域 '{args.domain}' 不存在。可用领域: {', '.join(list_domains(cheats))}", file=sys.stderr)
            return EXIT_DATA_ERROR

        count, results = search_cheats(cheats, domain, args.query, verbose=args.verbose)
        if count == 0:
            print(f"[提示] 在领域 '{domain}' 中未找到与 '{args.query}' 匹配的条目")
            return EXIT_OK

        print(f"[{domain}] 匹配到 {count} 条结果:")
        for domain_name, item, score in results:
            print(f"  • {item.get('cmd', '')}")
            print(f"    描述: {item.get('desc', '')}")
            print(f"    场景: {item.get('scene', '')}")
            if args.verbose:
                print(f"    匹配度: {score:.2f}")
        return EXIT_OK

    elif args.command == "random":
        domain = None
        if args.domain:
            domain = normalize_domain(args.domain)
            if domain not in cheats:
                print(f"[错误] 领域 '{args.domain}' 不存在。可用领域: {', '.join(list_domains(cheats))}", file=sys.stderr)
                return EXIT_DATA_ERROR

        result = random_cheat(cheats, domain)
        if result is None:
            print("[提示] 没有可用的速查数据")
            return EXIT_DATA_ERROR

        domain_name, item = result
        print(f"[{domain_name}] 随机速查:")
        print(f"  • {item.get('cmd', '')}")
        print(f"    描述: {item.get('desc', '')}")
        print(f"    场景: {item.get('scene', '')}")
        return EXIT_OK

    elif args.command == "list-domains":
        domains = list_domains(cheats)
        if not domains:
            print("[提示] 没有可用的领域")
            return EXIT_DATA_ERROR

        print(f"可用领域（{len(domains)} 个）:")
        for domain in domains:
            count = len(cheats[domain])
            print(f"  • {domain}（{count} 条速查）")
        return EXIT_OK

    elif args.command == "export":
        success = export_cheats(cheats, args.format, args.output, dry_run=args.dry_run)
        return EXIT_OK if success else EXIT_IO_ERROR

    # 未知命令（理论上不会到达这里）
    parser.print_help()
    return EXIT_USAGE_ERROR


if __name__ == "__main__":
    sys.exit(main())
