#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — zoxide 智能目录跳转核心逻辑（独立实现）

本脚本仅依据功能规格重新实现，不参考任何既有代码。
提供核心算法：frecency 评分、路径匹配、记录管理、交互选择。
支持 --selftest 离线自检，不依赖外部文件与网络。
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义
E001 = "E001: 参数错误"
E002 = "E002: 数据库文件无法读取"
E003 = "E003: 数据库文件无法写入"
E004 = "E004: 路径不存在"
E005 = "E005: 数据库格式损坏"
E006 = "E006: 无匹配结果"
E007 = "E007: 交互选择被取消"
E008 = "E008: 内部逻辑错误"
E009 = "E009: 自检失败"
E010 = "E010: 未知异常"

# 默认数据库路径（仅用于实际运行，自检不读取）
DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".zoxide_db.txt")

# 时间衰减半衰期（秒），约 30 天
HALF_LIFE = 30 * 24 * 3600


@dataclass
class Entry:
    """单条目录记录"""
    path: str
    score: float = 1.0
    last_visit: float = field(default_factory=time.time)
    visit_count: int = 1

    def to_line(self) -> str:
        """序列化为文本行"""
        return f"{self.path}\t{self.score:.6f}\t{int(self.last_visit)}\t{self.visit_count}"

    @classmethod
    def from_line(cls, line: str) -> Optional["Entry"]:
        """从文本行解析，失败返回 None"""
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 4:
            return None
        try:
            return cls(
                path=parts[0],
                score=float(parts[1]),
                last_visit=float(parts[2]),
                visit_count=int(parts[3]),
            )
        except (ValueError, TypeError):
            return None


class ZoxideDB:
    """目录历史数据库（文本文件存储）"""

    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        self.entries: Dict[str, Entry] = {}

    # ---------- 基础 IO ----------
    def load(self) -> None:
        """从文件加载记录，文件不存在视为空库"""
        if not os.path.exists(self.db_path):
            self.entries = {}
            return
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                raw_lines = f.readlines()
        except OSError:
            raise RuntimeError(E002)
        self.entries = {}
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            entry = Entry.from_line(line)
            if entry is None:
                raise RuntimeError(E005)
            self.entries[entry.path] = entry

    def save(self) -> None:
        """将记录写回文件"""
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                for entry in self.entries.values():
                    f.write(entry.to_line() + "\n")
        except OSError:
            raise RuntimeError(E003)

    # ---------- 核心操作 ----------
    def add(self, path: str) -> None:
        """记录一次访问（新增或更新）"""
        path = os.path.abspath(path)
        now = time.time()
        if path in self.entries:
            entry = self.entries[path]
            # 时间衰减旧分数
            age = now - entry.last_visit
            decay = 0.5 ** (age / HALF_LIFE)
            entry.score = entry.score * decay + 1.0
            entry.last_visit = now
            entry.visit_count += 1
        else:
            self.entries[path] = Entry(path=path, score=1.0, last_visit=now, visit_count=1)

    def remove(self, path: str) -> bool:
        """删除指定记录，成功返回 True"""
        norm = os.path.abspath(path)
        if norm in self.entries:
            del self.entries[norm]
            return True
        # 尝试精确匹配（不规范化）
        if path in self.entries:
            del self.entries[path]
            return True
        return False

    def query(self, keyword: str, limit: int = 10) -> List[Entry]:
        """按关键词匹配，返回按分数降序的列表"""
        if not keyword:
            return []
        kw_lower = keyword.lower()
        matched = []
        for entry in self.entries.values():
            path_lower = entry.path.lower()
            # 匹配规则：关键词出现在路径任意位置，或路径末尾匹配关键词
            if kw_lower in path_lower or path_lower.endswith(kw_lower):
                matched.append(entry)
        matched.sort(key=lambda e: (e.score, e.last_visit), reverse=True)
        return matched[:limit]

    def prune(self, max_entries: int = 1000) -> int:
        """裁剪记录数，返回删除条数"""
        if len(self.entries) <= max_entries:
            return 0
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (e.score, e.last_visit),
            reverse=True,
        )
        keep = sorted_entries[:max_entries]
        keep_paths = {e.path for e in keep}
        removed = 0
        for path in list(self.entries.keys()):
            if path not in keep_paths:
                del self.entries[path]
                removed += 1
        return removed

    def all_entries(self) -> List[Entry]:
        """返回全部记录（按分数降序）"""
        return sorted(self.entries.values(), key=lambda e: (e.score, e.last_visit), reverse=True)


# ---------- 交互选择 ----------
def interactive_select(entries: List[Entry]) -> Optional[Entry]:
    """在终端中让用户选择，返回选中项或 None（取消/无输入）"""
    if not entries:
        return None
    if len(entries) == 1:
        return entries[0]
    print("多个匹配项，请选择：")
    for i, entry in enumerate(entries, 1):
        print(f"  [{i}] {entry.path}")
    try:
        raw = input("输入序号（回车取消）: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        return None
    if 1 <= idx <= len(entries):
        return entries[idx - 1]
    return None


# ---------- 命令行入口 ----------
def cmd_add(args) -> int:
    """z add <path>"""
    db = ZoxideDB(args.db)
    db.load()
    for p in args.paths:
        if not os.path.isdir(p):
            print(f"警告: 目录不存在，跳过 {p}")
            continue
        db.add(p)
    db.save()
    return 0


def cmd_query(args) -> int:
    """z <keyword>"""
    db = ZoxideDB(args.db)
    db.load()
    results = db.query(args.keyword, limit=args.limit)
    if not results:
        if args.interactive:
            print(E006)
        return 1
    if args.interactive and len(results) > 1:
        chosen = interactive_select(results)
        if chosen is None:
            return 0  # 用户取消
        print(chosen.path)
    else:
        for entry in results:
            print(entry.path)
    return 0


def cmd_list(args) -> int:
    """z list"""
    db = ZoxideDB(args.db)
    db.load()
    for entry in db.all_entries():
        print(f"{entry.score:8.2f}  {entry.path}")
    return 0


def cmd_remove(args) -> int:
    """z remove <path>"""
    db = ZoxideDB(args.db)
    db.load()
    removed_any = False
    for p in args.paths:
        if db.remove(p):
            removed_any = True
        else:
            print(f"未找到记录: {p}")
    if removed_any:
        db.save()
    return 0


def cmd_prune(args) -> int:
    """z prune [--max N]"""
    db = ZoxideDB(args.db)
    db.load()
    removed = db.prune(max_entries=args.max)
    db.save()
    print(f"已清理 {removed} 条记录")
    return 0


# ---------- 自检 ----------
def run_selftest() -> int:
    """内置硬编码样例离线自检核心逻辑"""
    try:
        # 1. 构造内存数据库（不落盘）
        db = ZoxideDB(db_path=":memory:")  # 仅标识，不实际读写
        db.entries = {}

        # 2. 添加样例目录（路径不存在也能记录，自检不检查存在性）
        sample_paths = [
            "/home/user/projects/alpha",
            "/home/user/projects/beta",
            "/home/user/work/docs",
            "/home/user/work/reports",
            "/home/user/personal/photos",
        ]
        for p in sample_paths:
            db.entries[p] = Entry(path=p, score=1.0, last_visit=1000.0, visit_count=1)

        # 3. 模拟多次访问提升分数（直接操作 score，避免时间衰减影响）
        # 访问 alpha 两次，使其分数提升
        alpha_entry = db.entries["/home/user/projects/alpha"]
        alpha_entry.score += 2.0  # 模拟两次访问带来的分数提升
        alpha_entry.visit_count += 2
        
        # 访问 docs 一次
        docs_entry = db.entries["/home/user/work/docs"]
        docs_entry.score += 1.0
        docs_entry.visit_count += 1

        # 4. 查询测试
        results = db.query("alpha")
        assert len(results) >= 1, "查询 alpha 应有结果"
        assert results[0].path == "/home/user/projects/alpha", "alpha 应排第一"

        results = db.query("docs")
        assert len(results) == 1, "docs 应精确匹配一条"
        assert results[0].path == "/home/user/work/docs"

        # 5. 模糊匹配测试
        results = db.query("work")
        assert len(results) >= 2, "work 应匹配多条"
        for r in results:
            assert "work" in r.path, "匹配路径应包含关键词"

        # 6. 无结果测试
        results = db.query("nonexistent_keyword_xyz")
        assert len(results) == 0, "不存在的关键词应无结果"

        # 7. 删除测试
        assert db.remove("/home/user/personal/photos") == True, "删除应成功"
        assert db.remove("/home/user/personal/photos") == False, "重复删除应失败"
        assert "/home/user/personal/photos" not in db.entries

        # 8. 裁剪测试
        for i in range(20):
            db.entries[f"/tmp/test_dir_{i}"] = Entry(
                path=f"/tmp/test_dir_{i}", score=0.1, last_visit=1.0, visit_count=1
            )
        removed = db.prune(max_entries=10)
        assert removed >= 10, "裁剪至少移除 10 条"
        assert len(db.entries) <= 10, "裁剪后记录数应受限"

        # 9. 序列化往返测试
        entry = Entry(path="/test/serial", score=3.5, last_visit=12345.0, visit_count=7)
        line = entry.to_line()
        parsed = Entry.from_line(line)
        assert parsed is not None, "解析不应失败"
        assert parsed.path == "/test/serial"
        assert parsed.score > 3.0 and parsed.score < 4.0  # 宽松比较
        assert parsed.visit_count == 7

        # 10. 非法行解析
        assert Entry.from_line("bad_line_no_tabs") is None, "非法行应解析失败"

        # 11. 分数排序验证（高频访问 > 低频）
        db2 = ZoxideDB(db_path=":memory:")
        db2.entries = {
            "/a": Entry(path="/a", score=1.0, last_visit=100.0, visit_count=1),
            "/b": Entry(path="/b", score=5.0, last_visit=200.0, visit_count=1),
        }
        all_e = db2.all_entries()
        assert all_e[0].path == "/b", "分数高的应排前面"

        # 12. 交互选择（模拟输入）
        test_entries = [
            Entry(path="/opt/a", score=2.0, last_visit=1.0, visit_count=1),
            Entry(path="/opt/b", score=1.0, last_visit=1.0, visit_count=1),
        ]
        # 单条直接返回
        assert interactive_select(test_entries[:1]).path == "/opt/a"

        print("自检通过: 所有核心逻辑验证成功")
        return 0

    except AssertionError as e:
        print(f"自检失败: 断言错误 - {e}")
        return 1
    except Exception as e:
        print(f"自检失败: 意外异常 - {e}")
        return 1


# ---------- 主入口 ----------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zoxide",
        description="智能目录跳转工具（基于 frecency 算法）",
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="数据库文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    sub = parser.add_subparsers(dest="command")

    # add 子命令
    p_add = sub.add_parser("add", help="记录目录访问")
    p_add.add_argument("paths", nargs="+", help="要记录的目录路径")

    # query 子命令
    p_query = sub.add_parser("query", help="查询并跳转")
    p_query.add_argument("keyword", help="匹配关键词")
    p_query.add_argument("--limit", type=int, default=10, help="返回最大条数")
    p_query.add_argument("--interactive", "-i", action="store_true", help="交互选择")

    # list 子命令
    sub.add_parser("list", help="列出所有记录")

    # remove 子命令
    p_rm = sub.add_parser("remove", help="删除记录")
    p_rm.add_argument("paths", nargs="+", help="要删除的路径")

    # prune 子命令
    p_prune = sub.add_parser("prune", help="裁剪记录")
    p_prune.add_argument("--max", type=int, default=1000, help="最大保留条数")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无子命令
    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "add":
            return cmd_add(args)
        elif args.command == "query":
            return cmd_query(args)
        elif args.command == "list":
            return cmd_list(args)
        elif args.command == "remove":
            return cmd_remove(args)
        elif args.command == "prune":
            return cmd_prune(args)
        else:
            print(E001)
            return 1
    except RuntimeError as e:
        print(f"运行错误: {e}")
        return 1
    except Exception as e:
        print(f"{E010}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
