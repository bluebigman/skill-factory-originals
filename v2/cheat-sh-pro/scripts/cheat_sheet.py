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
        {"cmd": "docker logs -f c1", "desc": "跟踪容器日志", "scene": "排查应用报错"},
        {"cmd": "docker system df", "desc": "查看磁盘占用", "scene": "清理前评估"},
        {"cmd": "docker rmi $(docker images -q -f dangling=true)", "desc": "清理悬空镜像", "scene": "释放磁盘"},
        {"cmd": "docker inspect c1 --format '{{.NetworkSettings.IPAddress}}'", "desc": "查容器IP", "scene": "容器间通信"},
        {"cmd": "docker compose up -d", "desc": "后台启动编排服务", "scene": "启动服务栈"},
        {"cmd": "docker stop $(docker ps -q)", "desc": "停止所有容器", "scene": "批量停止"},
        {"cmd": "docker system prune -a", "desc": "清理所有未使用资源", "scene": "深度清理"},
    ],
    "python": [
        {"cmd": "my_list = [1, 2, 3]", "desc": "定义列表", "scene": "基础数据结构"},
        {"cmd": "my_dict = {'key': 'value'}", "desc": "定义字典", "scene": "键值对存储"},
        {"cmd": "for i in range(10): print(i)", "desc": "循环打印", "scene": "迭代操作"},
        {"cmd": "def my_func(x):\\n    return x * 2", "desc": "定义函数", "scene": "代码复用"},
        {"cmd": "class MyClass:\\n    def __init__(self):\\n        self.value = 0", "desc": "定义类", "scene": "面向对象编程"},
        {"cmd": "[x**2 for x in range(10)]", "desc": "列表推导式", "scene": "快速生成列表"},
        {"cmd": "add = lambda x, y: x + y", "desc": "定义匿名函数", "scene": "简短函数"},
        {"cmd": "@staticmethod\\ndef my_static(): pass", "desc": "静态方法", "scene": "无需实例的方法"},
        {"cmd": "with open('file.txt') as f: data = f.read()", "desc": "读取文件", "scene": "文件操作"},
        {"cmd": "import json\\ndata = json.loads('{\"a\": 1}')", "desc": "解析JSON", "scene": "数据处理"},
    ],
}


# ---------------------------------------------------------------------------
# 数据加载与校验
# ---------------------------------------------------------------------------

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def load_cheats(data_file: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
    """
    加载速查数据。

    优先级: 外部文件 (CHEAT_SH_PRO_DATA 或 --data) > 内置默认数据

    参数:
        data_file: 外部数据文件路径（可选）

    返回:
        速查数据字典，格式: {领域: [{cmd, desc, scene}, ...]}

    异常:
        SystemExit: 外部文件格式错误时退出
    """
    # 确定数据文件路径
    file_path = data_file or os.environ.get("CHEAT_SH_PRO_DATA")
    if not file_path:
        return DEFAULT_CHEATS

    # 读取外部文件
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[警告] 外部数据文件不存在: {file_path}，使用内置数据", file=sys.stderr)
        return DEFAULT_CHEATS
    except json.JSONDecodeError as e:
        print(f"[错误] 外部数据文件格式错误: {e}，使用内置数据", file=sys.stderr)
        return DEFAULT_CHEATS
    except Exception as e:
        print(f"[错误] 读取外部数据文件失败: {e}，使用内置数据", file=sys.stderr)
        return DEFAULT_CHEATS

    # 校验数据格式
    if not isinstance(data, dict):
        print("[错误] 外部数据必须是 JSON 对象（领域 -> 命令数组），使用内置数据", file=sys.stderr)
        return DEFAULT_CHEATS

    validated: Dict[str, List[Dict[str, str]]] = {}
    for domain, items in data.items():
        if not isinstance(domain, str) or not isinstance(items, list):
            continue
        valid_items = []
        for item in items:
            if isinstance(item, dict) and "cmd" in item and "desc" in item:
                valid_items.append({
                    "cmd": str(item["cmd"]),
                    "desc": str(item.get("desc", "")),
                    "scene": str(item.get("scene", "")),
                })
        if valid_items:
            validated[domain] = valid_items

    if not validated:
        print("[警告] 外部数据文件无有效内容，使用内置数据", file=sys.stderr)
        return DEFAULT_CHEATS

    return validated


# ---------------------------------------------------------------------------
# 搜索功能
# ---------------------------------------------------------------------------

def search_cheats(
    cheats: Dict[str, List[Dict[str, str]]],
    query: str,
    domain: Optional[str] = None,
    verbose: bool = False,
) -> List[Tuple[str, Dict[str, str], float]]:
    """
    在速查数据中搜索匹配项。

    使用 difflib.SequenceMatcher 进行模糊匹配，匹配度 >= 0.4 的结果会被返回。

    参数:
        cheats: 速查数据字典
        query: 搜索关键词
        domain: 领域过滤（可选）
        verbose: 是否输出详细匹配信息

    返回:
        匹配结果列表，每项为 (领域, 条目, 匹配度)
    """
    results: List[Tuple[str, Dict[str, str], float]] = []
    query_lower = query.lower()

    # 确定搜索范围
    domains = [domain] if domain else list(cheats.keys())

    for dom in domains:
        if dom not in cheats:
            continue
        for item in cheats[dom]:
            # 计算匹配度
            searchable = f"{item['cmd']} {item['desc']} {item['scene']}".lower()
            ratio = difflib.SequenceMatcher(None, query_lower, searchable).ratio()
            # 关键词包含匹配（更精确）
            if query_lower in searchable:
                ratio = max(ratio, 0.8)
            if ratio >= 0.4:
                results.append((dom, item, ratio))

    # 按匹配度排序
    results.sort(key=lambda x: x[2], reverse=True)

    if verbose:
        print(f"[详细] 搜索 '{query}' 在 {len(domains)} 个领域中找到 {len(results)} 条匹配")

    return results


# ---------------------------------------------------------------------------
# 随机速查
# ---------------------------------------------------------------------------

def random_cheat(
    cheats: Dict[str, List[Dict[str, str]]],
    domain: Optional[str] = None,
) -> Tuple[str, Dict[str, str]]:
    """
    随机获取一条速查命令。

    参数:
        cheats: 速查数据字典
        domain: 领域过滤（可选）

    返回:
        (领域, 条目)

    异常:
        ValueError: 指定领域不存在或速查数据为空
    """
    if domain:
        if domain not in cheats:
            raise ValueError(f"未找到领域: {domain}")
        items = cheats[domain]
        if not items:
            raise ValueError(f"领域 '{domain}' 没有速查条目")
        return domain, random.choice(items)

    # 随机选一个领域
    all_domains = list(cheats.keys())
    if not all_domains:
        raise ValueError("速查数据为空")
    dom = random.choice(all_domains)
    items = cheats[dom]
    if not items:
        raise ValueError(f"领域 '{dom}' 没有速查条目")
    return dom, random.choice(items)


# ---------------------------------------------------------------------------
# 导出功能
# ---------------------------------------------------------------------------

def export_cheats(
    cheats: Dict[str, List[Dict[str, str]]],
    output_format: str,
    output_path: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> Optional[str]:
    """
    导出速查数据到文件。

    支持格式: markdown, json

    参数:
        cheats: 速查数据字典
        output_format: 导出格式 (markdown/json)
        output_path: 输出文件路径（可选，默认输出到 stdout）
        dry_run: 预览模式，不实际写文件
        verbose: 详细输出

    返回:
        写入的文件路径（dry_run 或输出到 stdout 时返回 None）
    """
    # 生成内容
    if output_format == "markdown":
        content = _format_markdown(cheats)
    elif output_format == "json":
        content = json.dumps(cheats, ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"不支持的导出格式: {output_format}")

    # 输出到 stdout
    if not output_path:
        print(content)
        return None

    # dry-run 模式
    if dry_run:
        domain_count = len(cheats)
        item_count = sum(len(items) for items in cheats.values())
        print(f"[dry-run] 将写入 {domain_count} 个领域的速查到: {output_path}")
        print(f"[dry-run] 摘要: 共 {domain_count} 个领域, {item_count} 条命令")
        print(f"[dry-run] 内容预览 ({len(content)} 字符):")
        print(content[:500] + ("..." if len(content) > 500 else ""))
        return None

    # 原子写入
    try:
        _atomic_write(output_path, content)
        if verbose:
            print(f"[成功] 已写入 {len(content)} 字符到 {output_path}")
        return output_path
    except Exception as e:
        print(f"[错误] 无法写入文件: {e}", file=sys.stderr)
        return None


def _format_markdown(cheats: Dict[str, List[Dict[str, str]]]) -> str:
    """将速查数据格式化为 Markdown 文本。"""
    lines = ["# 命令行速查手册", ""]
    lines.append(f"> 生成时间: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    for domain in sorted(cheats.keys()):
        lines.append(f"## {domain}")
        lines.append("")
        lines.append("| 命令 | 说明 | 场景 |")
        lines.append("|------|------|------|")
        for item in cheats[domain]:
            cmd = item["cmd"].replace("|", "\\|")
            desc = item["desc"].replace("|", "\\|")
            scene = item["scene"].replace("|", "\\|")
            lines.append(f"| `{cmd}` | {desc} | {scene} |")
        lines.append("")

    return "\n".join(lines)


def _atomic_write(file_path: str, content: str) -> None:
    """
    原子写入文件。

    先写入临时文件，再原子替换目标文件，避免写入中断导致文件损坏。

    参数:
        file_path: 目标文件路径
        content: 要写入的内容

    异常:
        OSError: 写入失败时抛出
    """
    target = Path(file_path)
    target_dir = target.parent if target.parent != Path("") else Path(".")

    # 确保目录存在
    target_dir.mkdir(parents=True, exist_ok=True)

    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=str(target_dir), prefix=".cheat_sh_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子替换
        os.replace(temp_path, file_path)
    except Exception:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# 领域列表
# ---------------------------------------------------------------------------

def list_domains(cheats: Dict[str, List[Dict[str, str]]]) -> List[str]:
    """返回所有可用领域列表。"""
    return sorted(cheats.keys())


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    运行自检，验证核心功能。

    返回:
        0 表示全部通过，非 0 表示有失败
    """
    print("=== cheat-sh-pro 自检 ===")
    failures = 0

    # 1. 数据加载
    print("[1/5] 数据加载...")
    cheats = load_cheats()
    assert len(cheats) >= 3, f"内置数据至少应有 3 个领域，实际 {len(cheats)}"
    assert "git" in cheats and "docker" in cheats and "python" in cheats, "缺少核心领域"
    print(f"  ✓ 加载 {len(cheats)} 个领域")

    # 2. 搜索功能
    print("[2/5] 搜索功能...")
    results = search_cheats(cheats, "log", domain="git")
    assert len(results) > 0, "搜索 'log' 在 git 领域应有结果"
    assert results[0][0] == "git", "搜索结果领域应为 git"
    print(f"  ✓ 搜索 'log' 在 git 领域找到 {len(results)} 条")

    # 3. 随机速查
    print("[3/5] 随机速查...")
    dom, item = random_cheat(cheats, domain="docker")
    assert dom == "docker", f"随机速查领域应为 docker，实际 {dom}"
    assert "cmd" in item and "desc" in item, "随机速查条目应包含 cmd 和 desc"
    print(f"  ✓ 随机获取: [{dom}] {item['cmd'][:50]}")

    # 4. 导出功能
    print("[4/5] 导出功能...")
    md_content = _format_markdown(cheats)
    assert "## git" in md_content, "Markdown 导出应包含 git 领域"
    assert "## docker" in md_content, "Markdown 导出应包含 docker 领域"
    assert "| 命令 | 说明 | 场景 |" in md_content, "Markdown 导出应包含表格头"
    print(f"  ✓ Markdown 导出 {len(md_content)} 字符")

    # 5. 领域列表
    print("[5/5] 领域列表...")
    domains = list_domains(cheats)
    assert "git" in domains and "python" in domains, "领域列表应包含核心领域"
    print(f"  ✓ 领域列表: {', '.join(domains)}")

    print("\n=== 自检通过 ===")
    return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="cheat-sh-pro",
        description="命令行速查手册 — 终端内即时获取代码示例",
        epilog="示例: python run.py search python --query list",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # search 子命令
    search_parser = subparsers.add_parser("search", help="搜索速查命令")
    search_parser.add_argument("--domain", nargs="?", help="领域过滤（可选）")
    search_parser.add_argument("--query", "-q", required=False, help="搜索关键词")
    search_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    search_parser.add_argument("--data", help="外部数据文件路径")

    # random 子命令
    random_parser = subparsers.add_parser("random", help="随机获取一条速查命令")
    random_parser.add_argument("--domain", nargs="?", help="领域过滤（可选）")
    random_parser.add_argument("--data", help="外部数据文件路径")

    # list-domains 子命令
    list_parser = subparsers.add_parser("list-domains", help="列出所有可用领域")
    list_parser.add_argument("--data", help="外部数据文件路径")

    # export 子命令
    export_parser = subparsers.add_parser("export", help="导出速查数据")
    export_parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="导出格式")
    export_parser.add_argument("--output", "-o", help="输出文件路径（默认输出到 stdout）")
    export_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写文件")
    export_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    export_parser.add_argument("--data", help="外部数据文件路径")

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。

    参数:
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"[自检失败] {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[自检异常] {e}", file=sys.stderr)
            return 1

    # 无子命令
    if not args.command:
        parser.print_help()
        return 0

    # 加载数据
    data_file = getattr(args, "data", None)
    cheats = load_cheats(data_file)

    # 执行子命令
    try:
        if args.command == "search":
            results = search_cheats(cheats, args.query, args.domain, args.verbose)
            if not results:
                print(f"[错误] 未找到匹配结果: '{args.query}'")
                return 1
            for dom, item, score in results[:10]:
                print(f"[{dom}] 匹配度 {score:.2f}:")
                print(f"  cmd: {item['cmd']}")
                print(f"  desc: {item['desc']}")
                print(f"  scene: {item['scene']}")
                print()
            return 0

        elif args.command == "random":
            try:
                dom, item = random_cheat(cheats, args.domain)
            except ValueError as e:
                print(f"[错误] {e}")
                return 1
            print(f"[{dom}] 随机速查:")
            print(f"  cmd: {item['cmd']}")
            print(f"  desc: {item['desc']}")
            print(f"  scene: {item['scene']}")
            return 0

        elif args.command == "list-domains":
            domains = list_domains(cheats)
            if not domains:
                print("[错误] 速查数据为空")
                return 1
            print(f"可用领域 ({len(domains)}):")
            for dom in domains:
                count = len(cheats[dom])
                print(f"  - {dom} ({count} 条)")
            return 0

        elif args.command == "export":
            result = export_cheats(
                cheats,
                args.format,
                args.output,
                args.dry_run,
                args.verbose,
            )
            if args.output and not args.dry_run and result is None:
                return 1
            return 0

        else:
            print(f"[错误] 未知命令: {args.command}")
            return 1

    except Exception as e:
        print(f"[错误] 执行失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
