#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catacomb - 未命名工具
一个极简的 CLI 工具，用于存储 shell 命令。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
仅供学习与参考用途，使用前请阅读相关文档。
"""

import argparse
import json
import sys
from pathlib import Path


# ============================================================
# 错误码定义 (E001-E010)
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "文件读写失败，请检查路径和权限",
    "E008": "JSON 解析失败，请检查数据格式",
    "E009": "参数组合无效，请检查命令行参数",
    "E010": "未知错误，请查看日志",
}


def get_error_message(code: str, **kwargs) -> str:
    """根据错误码获取标准化话术，并填充动态内容。"""
    template = ERROR_CODES.get(code, ERROR_CODES["E010"])
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


# ============================================================
# 核心数据结构
# ============================================================
class CommandEntry:
    """单条 shell 命令条目。"""

    def __init__(self, command: str, description: str = "", tags: list = None, category: str = "通用"):
        self.command = command.strip()
        self.description = description.strip()
        self.tags = tags if tags else []
        self.category = category if category else "通用"
        self.confidence = 1.0  # 默认高置信度

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "command": self.command,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommandEntry":
        """从字典创建实例。"""
        entry = cls(
            command=data.get("command", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", "通用"),
        )
        entry.confidence = data.get("confidence", 1.0)
        return entry


class CommandStore:
    """命令存储库，负责增删改查。"""

    def __init__(self, file_path: str = None):
        self.file_path = file_path
        self.entries = []

    def add(self, entry: CommandEntry) -> None:
        """添加一条命令。"""
        self.entries.append(entry)

    def remove(self, index: int) -> bool:
        """移除指定索引的命令。"""
        if 0 <= index < len(self.entries):
            del self.entries[index]
            return True
        return False

    def search(self, keyword: str) -> list:
        """按关键词搜索命令（匹配命令内容、描述、标签）。"""
        keyword_lower = keyword.lower()
        results = []
        for entry in self.entries:
            if (
                keyword_lower in entry.command.lower()
                or keyword_lower in entry.description.lower()
                or any(keyword_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)
        return results

    def list_all(self) -> list:
        """返回所有命令。"""
        return list(self.entries)

    def save(self, file_path: str = None) -> bool:
        """保存到 JSON 文件。"""
        target = file_path or self.file_path
        if not target:
            return False
        try:
            data = {
                "version": "1.0.0",
                "entries": [entry.to_dict() for entry in self.entries],
            }
            Path(target).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except (OSError, IOError):
            return False

    def load(self, file_path: str = None) -> bool:
        """从 JSON 文件加载。"""
        target = file_path or self.file_path
        if not target:
            return False
        try:
            data = json.loads(Path(target).read_text(encoding="utf-8"))
            self.entries = [CommandEntry.from_dict(item) for item in data.get("entries", [])]
            return True
        except (OSError, IOError, json.JSONDecodeError):
            return False


# ============================================================
# 核心处理逻辑
# ============================================================
def parse_input(raw_input: str) -> dict:
    """
    解析用户输入，识别关键信息。
    支持格式：
    - "命令" -> 仅命令
    - "命令 | 描述" -> 命令 + 描述
    - "命令 | 描述 | 标签1,标签2" -> 命令 + 描述 + 标签
    - JSON 字符串
    """
    if not raw_input or not raw_input.strip():
        raise ValueError(get_error_message("E001"))

    raw_input = raw_input.strip()

    # 尝试 JSON 解析
    if raw_input.startswith("{"):
        try:
            data = json.loads(raw_input)
            return data
        except json.JSONDecodeError:
            raise ValueError(get_error_message("E008"))

    # 管道分隔解析
    parts = [part.strip() for part in raw_input.split("|")]

    if len(parts) == 1:
        return {"command": parts[0]}
    elif len(parts) == 2:
        return {"command": parts[0], "description": parts[1]}
    elif len(parts) >= 3:
        tags = [tag.strip() for tag in parts[2].split(",") if tag.strip()]
        return {"command": parts[0], "description": parts[1], "tags": tags}
    else:
        raise ValueError(get_error_message("E003", example="ls -la | 列出文件 | 系统,文件"))


def process_entry(data: dict) -> CommandEntry:
    """根据解析后的数据创建 CommandEntry，并计算置信度。"""
    command = data.get("command", "").strip()
    if not command:
        raise ValueError(get_error_message("E002", missing="命令内容"))

    description = data.get("description", "").strip()
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    if not isinstance(tags, list):
        tags = []

    category = data.get("category", "通用")

    entry = CommandEntry(command=command, description=description, tags=tags, category=category)

    # 置信度计算：命令存在 + 描述完整 + 标签数量
    confidence = 1.0
    if not description:
        confidence -= 0.1  # 缺描述降置信度
    if not tags:
        confidence -= 0.05  # 缺标签降置信度
    entry.confidence = max(0.0, min(1.0, confidence))

    return entry


def format_output(entry: CommandEntry, verbose: bool = False) -> str:
    """格式化输出单条命令。"""
    lines = []
    lines.append(f"命令: {entry.command}")
    if verbose:
        lines.append(f"描述: {entry.description if entry.description else '(无)'}")
        lines.append(f"标签: {', '.join(entry.tags) if entry.tags else '(无)'}")
        lines.append(f"分类: {entry.category}")
        conf = entry.confidence
        if conf >= 0.9:
            conf_note = "高置信度"
        elif conf >= 0.85:
            conf_note = "建议复核"
        else:
            conf_note = "[需核实]"
        lines.append(f"置信度: {conf:.0%} ({conf_note})")
    return "\n".join(lines)


def handle_batch(items: list) -> dict:
    """批量处理输入，返回统计结果。"""
    results = []
    success_count = 0
    error_count = 0

    for item in items:
        try:
            if isinstance(item, str):
                data = parse_input(item)
            elif isinstance(item, dict):
                data = item
            else:
                raise ValueError(get_error_message("E003", example="字符串或JSON对象"))

            entry = process_entry(data)
            results.append({"status": "success", "entry": entry})
            success_count += 1
        except ValueError as e:
            results.append({"status": "error", "message": str(e)})
            error_count += 1

    return {
        "results": results,
        "success_count": success_count,
        "error_count": error_count,
        "total": len(items),
    }


# ============================================================
# 自检模块 (--selftest)
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松阈值断言，不依赖精确值。
    """
    print("=== catacomb 自检开始 ===")
    failures = 0

    # 测试1: 解析输入
    print("[测试1] 解析输入...")
    try:
        data = parse_input("ls -la | 列出文件详细信息 | 系统,文件")
        assert data["command"] == "ls -la", "命令解析错误"
        assert data["description"] == "列出文件详细信息", "描述解析错误"
        assert len(data["tags"]) == 2, "标签解析错误"
        print("  ✓ 解析输入通过")
    except Exception as e:
        print(f"  ✗ 解析输入失败: {e}")
        failures += 1

    # 测试2: 创建条目
    print("[测试2] 创建条目...")
    try:
        entry = process_entry({"command": "grep -r 'TODO' .", "description": "递归搜索TODO", "tags": ["搜索", "开发"]})
        assert entry.command == "grep -r 'TODO' .", "命令内容错误"
        assert entry.description == "递归搜索TODO", "描述错误"
        assert len(entry.tags) == 2, "标签错误"
        assert entry.confidence >= 0.8, "置信度应较高"
        print("  ✓ 创建条目通过")
    except Exception as e:
        print(f"  ✗ 创建条目失败: {e}")
        failures += 1

    # 测试3: 存储与搜索
    print("[测试3] 存储与搜索...")
    try:
        store = CommandStore()
        store.add(process_entry({"command": "docker ps", "description": "查看容器", "tags": ["docker"]}))
        store.add(process_entry({"command": "git status", "description": "查看git状态", "tags": ["git"]}))
        store.add(process_entry({"command": "ls -la", "description": "列出文件", "tags": ["文件"]}))

        results = store.search("docker")
        assert len(results) >= 1, "应至少找到1条docker相关命令"

        results = store.search("git")
        assert len(results) >= 1, "应至少找到1条git相关命令"

        results = store.search("文件")
        assert len(results) >= 1, "应至少找到1条文件相关命令"

        assert len(store.list_all()) >= 3, "应有至少3条命令"
        print("  ✓ 存储与搜索通过")
    except Exception as e:
        print(f"  ✗ 存储与搜索失败: {e}")
        failures += 1

    # 测试4: 批量处理
    print("[测试4] 批量处理...")
    try:
        items = [
            "echo hello | 输出hello | 测试",
            "pwd | 显示当前目录",
            {"command": "date", "description": "显示日期"},
        ]
        result = handle_batch(items)
        assert result["success_count"] >= 2, "应至少有2条成功"
        assert result["total"] == 3, "总数应为3"
        print("  ✓ 批量处理通过")
    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        failures += 1

    # 测试5: 错误处理
    print("[测试5] 错误处理...")
    try:
        # 空输入
        try:
            parse_input("")
            print("  ✗ 空输入未抛出异常")
            failures += 1
        except ValueError as e:
            assert "E001" in str(e) or "输入为空" in str(e), "错误码不正确"
            print("  ✓ 空输入错误处理通过")

        # 缺命令
        try:
            process_entry({"description": "没有命令"})
            print("  ✗ 缺命令未抛出异常")
            failures += 1
        except ValueError as e:
            assert "E002" in str(e) or "命令" in str(e), "错误码不正确"
            print("  ✓ 缺命令错误处理通过")
    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        failures += 1

    # 测试6: 输出格式化
    print("[测试6] 输出格式化...")
    try:
        entry = process_entry({"command": "ls", "description": "列出文件"})
        output = format_output(entry, verbose=True)
        assert "ls" in output, "输出应包含命令"
        assert "列出文件" in output, "输出应包含描述"
        assert "置信度" in output, "输出应包含置信度"

        output_short = format_output(entry, verbose=False)
        assert "ls" in output_short, "简短输出应包含命令"
        assert "置信度" not in output_short, "简短输出不应包含置信度"
        print("  ✓ 输出格式化通过")
    except Exception as e:
        print(f"  ✗ 输出格式化失败: {e}")
        failures += 1

    # 测试7: 保存与加载
    print("[测试7] 保存与加载...")
    try:
        store = CommandStore()
        store.add(process_entry({"command": "test-cmd", "description": "测试命令"}))
        # 使用临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            assert store.save(tmp_path), "保存失败"
            store2 = CommandStore()
            assert store2.load(tmp_path), "加载失败"
            assert len(store2.entries) >= 1, "加载后应有条目"
            assert store2.entries[0].command == "test-cmd", "命令内容不一致"
            print("  ✓ 保存与加载通过")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"  ✗ 保存与加载失败: {e}")
        failures += 1

    print("=== 自检结束 ===")
    if failures == 0:
        print("全部测试通过 ✓")
        return 0
    else:
        print(f"{failures} 项测试失败 ✗")
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="catacomb - 极简 shell 命令存储工具（仅供学习与参考）",
        epilog="示例: python main.py add 'ls -la | 列出文件'",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加命令")
    add_parser.add_argument("input", help="命令内容，格式: '命令 | 描述 | 标签1,标签2' 或 JSON")
    add_parser.add_argument("-f", "--file", help="存储文件路径")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有命令")
    list_parser.add_argument("-f", "--file", help="存储文件路径")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索命令")
    search_parser.add_argument("keyword", help="搜索关键词")
    search_parser.add_argument("-f", "--file", help="存储文件路径")
    search_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    # remove 命令
    remove_parser = subparsers.add_parser("remove", help="移除命令")
    remove_parser.add_argument("index", type=int, help="命令索引（从0开始）")
    remove_parser.add_argument("-f", "--file", help="存储文件路径")

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量处理")
    batch_parser.add_argument("-f", "--file", help="存储文件路径")

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无子命令
    if not args.command:
        parser.print_help()
        return 0

    # 默认存储文件
    default_file = str(Path.home() / ".catacomb_store.json")

    # 处理各子命令
    try:
        if args.command == "add":
            data = parse_input(args.input)
            entry = process_entry(data)
            store = CommandStore(args.file or default_file)
            store.load()
            store.add(entry)
            if store.save():
                print(f"已添加命令: {entry.command}")
                print(format_output(entry, verbose=True))
            else:
                print(get_error_message("E007"))
                return 1

        elif args.command == "list":
            store = CommandStore(args.file or default_file)
            if not store.load():
                print("存储文件不存在或为空，使用空存储")
            entries = store.list_all()
            if not entries:
                print("暂无命令，使用 'add' 添加")
            else:
                print(f"共 {len(entries)} 条命令:")
                for i, entry in enumerate(entries):
                    print(f"[{i}] {format_output(entry, verbose=args.verbose)}")
                    if i < len(entries) - 1:
                        print()

        elif args.command == "search":
            store = CommandStore(args.file or default_file)
            if not store.load():
                print(get_error_message("E007"))
                return 1
            results = store.search(args.keyword)
            if not results:
                print(f"未找到包含 '{args.keyword}' 的命令")
            else:
                print(f"找到 {len(results)} 条匹配命令:")
                for i, entry in enumerate(results):
                    print(f"[{i}] {format_output(entry, verbose=args.verbose)}")
                    if i < len(results) - 1:
                        print()

        elif args.command == "remove":
            store = CommandStore(args.file or default_file)
            if not store.load():
                print(get_error_message("E007"))
                return 1
            if store.remove(args.index):
                if store.save():
                    print(f"已移除索引 {args.index} 的命令")
                else:
                    print(get_error_message("E007"))
                    return 1
            else:
                print(get_error_message("E002", missing=f"索引 {args.index} 不存在"))

        elif args.command == "batch":
            # 批量模式：从 stdin 读取多行输入
            print("请输入命令（每行一条，Ctrl+D 结束）:")
            lines = sys.stdin.read().strip().splitlines()
            if not lines:
                print(get_error_message("E001"))
                return 1
            result = handle_batch(lines)
            print(f"处理完成: 成功 {result['success_count']}, 失败 {result['error_count']}, 总计 {result['total']}")
            for item in result["results"]:
                if item["status"] == "success":
                    print(f"  ✓ {item['entry'].command}")
                else:
                    print(f"  ✗ {item['message']}")

        else:
            print(get_error_message("E009"))
            return 1

    except ValueError as e:
        print(f"错误: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
