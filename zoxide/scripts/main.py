#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — zoxide 智能目录跳转核心逻辑（独立实现）

本脚本仅依据功能规格重新实现，不参考任何既有代码。
提供核心算法：frecency 评分、路径匹配、记录管理、交互选择。
支持 --selftest 离线自检，不依赖外部文件与网络。

注意：本脚本仅提供核心算法和命令行接口，不包含 Shell 集成（hook/别名）。
Shell 集成需由外部脚本（如 zoxide init 生成的代码）调用本程序的 add/query 子命令完成。
"""

import argparse
import os
import sys
import tempfile
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

# 损坏行阈值：超过此数量则抛出 E005
BAD_LINE_THRESHOLD = 10


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
            with open(self.db_path, "r", encoding="utf-8", errors="replace") as f:
                raw_lines = f.readlines()
        except OSError:
            raise RuntimeError(E002)
        self.entries = {}
        bad_lines = 0
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            entry = Entry.from_line(line)
            if entry is None:
                bad_lines += 1
                if bad_lines > BAD_LINE_THRESHOLD:
                    raise RuntimeError(E005)
                continue  # 跳过坏行，不中断加载
            self.entries[entry.path] = entry
        if bad_lines > 0:
            print(f"警告: 跳过 {bad_lines} 条损坏记录", file=sys.stderr)

    def save(self) -> None:
        """将记录写回文件（原子写入）"""
        try:
            # 使用临时文件 + os.replace() 实现原子写入
            fd, tmp_path = tempfile.mkstemp(
                dir=os.path.dirname(self.db_path) or ".",
                prefix=".zoxide_db_",
                suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
                    for entry in self.entries.values():
                        f.write(entry.to_line() + "\n")
                os.replace(tmp_path, self.db_path)
            except Exception:
                # 清理临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
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

        # 13. 原子写入测试（使用临时文件）
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        try:
            db3 = ZoxideDB(db_path=tmp_db_path)
            db3.entries = {
                "/test/atomic": Entry(path="/test/atomic", score=1.0, last_visit=1.0, visit_count=1)
            }
            db3.save()
            # 验证文件存在且内容正确
            assert os.path.exists(tmp_db_path), "数据库文件应存在"
            with open(tmp_db_path, "r") as f:
                content = f.read()
            assert "/test/atomic" in content, "内容应包含记录"
        finally:
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)

        # 14. 损坏行容错测试
        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as tmp:
            tmp.write("bad_line_no_tabs\n")
            tmp.write("/valid/path\t1.0\t1000\t1\n")
            tmp_db_path = tmp.name
        try:
            db4 = ZoxideDB(db_path=tmp_db_path)
            db4.load()
            assert len(db4.entries) == 1, "应跳过坏行，保留有效记录"
            assert "/valid/path" in db4.entries, "有效记录应被加载"
        finally:
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)

        # 15. 损坏行阈值测试（超过阈值应抛出 E005）
        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as tmp:
            for i in range(BAD_LINE_THRESHOLD + 1):
                tmp.write(f"bad_line_{i}\n")
            tmp_db_path = tmp.name
        try:
            db5 = ZoxideDB(db_path=tmp_db_path)
            try:
                db5.load()
                assert False, "应抛出 E005 错误"
            except RuntimeError as e:
                assert str(e) == E005, f"错误码应为 E005，实际: {e}"
        finally:
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)

        # 16. 核心链路测试：add → save → load → query
        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        try:
            db6 = ZoxideDB(db_path=tmp_db_path)
            db6.add("/tmp/core_test_dir")
            db6.save()
            
            db7 = ZoxideDB(db_path=tmp_db_path)
            db7.load()
            results = db7.query("core_test")
            assert len(results) == 1, "核心链路查询应有结果"
            assert results[0].path == "/tmp/core_test_dir", "核心链路路径应匹配"
        finally:
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)

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
    parser = argparse
