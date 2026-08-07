#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catacomb - 极简命令行工具，用于存储 Shell 命令。

本脚本依据功能规格独立实现（clean-room），
仅使用 Python 标准库，无任何第三方依赖。

用法示例：
    python main.py add "ls -la" --tag 文件管理
    python main.py list
    python main.py search 文件
    python main.py --selftest
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义（规格 E001-E005 为业务错误，E006-E010 为内部错误）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "存储目录不可用",
    "E007": "JSON 读写失败",
    "E008": "命令不存在",
    "E009": "参数冲突",
    "E010": "内部状态异常",
}


def fail(code: str, message: str = "") -> int:
    """以标准格式打印错误并返回错误码对应的退出码。"""
    desc = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {desc}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {desc}", file=sys.stderr)
    # 错误码数字部分作为退出码（E001 -> 1）
    return int(code[1:])


# ---------------------------------------------------------------------------
# 数据存储层（基于 JSON 文件）
# ---------------------------------------------------------------------------
class CommandStore:
    """负责命令的持久化存储，使用 JSON 格式。"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_file = data_dir / "commands.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """确保存储目录与文件存在且可写。"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if not self.data_file.exists():
                self._write([])
        except (OSError, PermissionError) as exc:
            raise RuntimeError(f"存储初始化失败: {exc}") from exc

    def _read(self) -> list:
        """从磁盘读取全部命令记录。"""
        try:
            with self.data_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                raise ValueError("数据格式错误")
            return data
        except FileNotFoundError:
            return []
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"读取数据失败: {exc}") from exc

    def _write(self, records: list) -> None:
        """将全部命令记录写入磁盘。"""
        try:
            tmp_file = self.data_file.with_suffix(".tmp")
            with tmp_file.open("w", encoding="utf-8") as fh:
                json.dump(records, fh, ensure_ascii=False, indent=2)
            tmp_file.replace(self.data_file)
        except (OSError, TypeError) as exc:
            raise RuntimeError(f"写入数据失败: {exc}") from exc

    def add(self, command: str, tag: str = "", note: str = "") -> dict:
        """新增一条命令记录，返回该记录。"""
        if not command or not command.strip():
            raise ValueError("命令内容不能为空")

        record = {
            "id": self._next_id(),
            "command": command.strip(),
            "tag": tag.strip() if tag else "",
            "note": note.strip() if note else "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        records = self._read()
        records.append(record)
        self._write(records)
        return record

    def _next_id(self) -> int:
        """生成递增 ID。"""
        records = self._read()
        if not records:
            return 1
        return max(r.get("id", 0) for r in records) + 1

    def list_all(self) -> list:
        """返回全部记录。"""
        return self._read()

    def search(self, keyword: str) -> list:
        """按关键字搜索命令、标签或备注。"""
        if not keyword:
            return []
        keyword = keyword.lower()
        results = []
        for r in self._read():
            haystack = " ".join(
                [
                    r.get("command", ""),
                    r.get("tag", ""),
                    r.get("note", ""),
                ]
            ).lower()
            if keyword in haystack:
                results.append(r)
        return results

    def remove(self, record_id: int) -> bool:
        """删除指定 ID 的记录，返回是否删除成功。"""
        records = self._read()
        remaining = [r for r in records if r.get("id") != record_id]
        if len(remaining) == len(records):
            return False
        self._write(remaining)
        return True


# ---------------------------------------------------------------------------
# 格式化输出
# ---------------------------------------------------------------------------
def format_record(record: dict) -> str:
    """将单条记录格式化为可读文本。"""
    lines = [
        f"ID: {record.get('id')}",
        f"命令: {record.get('command')}",
    ]
    if record.get("tag"):
        lines.append(f"标签: {record.get('tag')}")
    if record.get("note"):
        lines.append(f"备注: {record.get('note')}")
    lines.append(f"创建时间: {record.get('created_at')}")
    return "\n".join(lines)


def format_list(records: list) -> str:
    """将记录列表格式化为文本。"""
    if not records:
        return "（无记录）"
    return "\n\n".join(format_record(r) for r in records)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="catacomb",
        description="极简 Shell 命令存储工具",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读写外部文件）",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用子命令")

    # add 子命令
    add_parser = subparsers.add_parser("add", help="添加命令")
    add_parser.add_argument("command", help="要存储的命令")
    add_parser.add_argument("--tag", default="", help="标签")
    add_parser.add_argument("--note", default="", help="备注")

    # list 子命令
    subparsers.add_parser("list", help="列出全部命令")

    # search 子命令
    search_parser = subparsers.add_parser("search", help="搜索命令")
    search_parser.add_argument("keyword", help="搜索关键字")

    # remove 子命令
    remove_parser = subparsers.add_parser("remove", help="删除命令")
    remove_parser.add_argument("id", type=int, help="命令 ID")

    return parser


def run_selftest() -> int:
    """内置自检：使用内存中的临时目录验证核心逻辑，不依赖外部环境。"""
    print("正在运行自检...")

    # 使用系统临时目录，避免污染当前工作目录
    with tempfile.TemporaryDirectory(prefix="catacomb_selftest_") as tmp:
        store = CommandStore(Path(tmp))

        # 测试添加
        r1 = store.add("ls -la", tag="文件管理")
        r2 = store.add("git status", tag="版本控制", note="查看工作区状态")

        # 基本断言：宽松阈值，只验证类型和大小关系
        assert isinstance(r1, dict), "添加结果应为字典"
        assert r1["id"] < r2["id"], "ID 应递增"
        assert len(store.list_all()) == 2, "应有 2 条记录"

        # 测试搜索
        results = store.search("文件")
        assert len(results) >= 1, "应能搜索到至少 1 条记录"
        assert results[0]["command"] == "ls -la", "搜索结果应匹配"

        # 测试搜索不存在的关键字
        no_results = store.search("不存在的关键字xyz")
        assert len(no_results) == 0, "不应有搜索结果"

        # 测试删除
        success = store.remove(r1["id"])
        assert success is True, "删除应成功"
        assert len(store.list_all()) == 1, "删除后应剩 1 条记录"

        # 测试删除不存在的 ID
        not_found = store.remove(9999)
        assert not_found is False, "删除不存在的 ID 应返回 False"

        # 测试空命令处理
        try:
            store.add("   ")
            assert False, "空命令应抛出异常"
        except ValueError:
            pass  # 预期行为

        # 测试搜索空关键字
        assert store.search("") == [], "空关键字应返回空列表"

    print("自检通过 ✔")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式：优先处理
    if args.selftest:
        return run_selftest()

    # 无子命令时提示帮助
    if not args.command:
        parser.print_help()
        return fail("E002", "请指定操作（add/list/search/remove）")

    # 初始化存储（使用用户目录下的 .catacomb 目录）
    data_dir = Path.home() / ".catacomb"
    try:
        store = CommandStore(data_dir)
    except RuntimeError as exc:
        return fail("E006", str(exc))

    try:
        if args.command == "add":
            if not args.command:
                return fail("E001", "命令内容为空")
            record = store.add(args.command, tag=args.tag, note=args.note)
            print("已添加：")
            print(format_record(record))
            return 0

        elif args.command == "list":
            records = store.list_all()
            print(format_list(records))
            return 0

        elif args.command == "search":
            if not args.keyword:
                return fail("E001", "搜索关键字为空")
            records = store.search(args.keyword)
            if not records:
                print("未找到匹配记录")
                return 0
            print(f"找到 {len(records)} 条记录：")
            print(format_list(records))
            return 0

        elif args.command == "remove":
            removed = store.remove(args.id)
            if not removed:
                return fail("E008", f"ID {args.id} 不存在")
            print(f"已删除 ID {args.id}")
            return 0

        else:
            return fail("E004", f"未知命令: {args.command}")

    except ValueError as exc:
        return fail("E003", str(exc))
    except RuntimeError as exc:
        return fail("E007", str(exc))
    except Exception as exc:  # 兜底异常处理
        return fail("E010", f"未预期错误: {exc}")


if __name__ == "__main__":
    sys.exit(main())
