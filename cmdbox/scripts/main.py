#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmdbox - 命令收纳箱 别名管理 快捷执行
=====================================
独立实现脚本，基于功能规格 clean-room 编写。

功能概览：
- 存储/删除/查找别名命令（支持标签、描述）
- 命令中支持 {{var}} 占位符，执行时动态替换
- 支持将多个已存命令串联（&&）或并联（;）组合执行
- 支持 JSON 导入/导出（批量操作）
- 内置 --selftest 离线自检，不依赖外部文件/网络

错误码约定：
- E001: 参数解析错误
- E002: 命令不存在
- E003: 命令已存在（重复添加）
- E004: 命令格式非法（空命令）
- E005: 变量替换缺失
- E006: 文件读写失败
- E007: JSON 解析失败
- E008: 导入数据格式非法
- E009: 组合命令中存在不存在的别名
- E010: 内部逻辑错误（不应发生）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# 数据存储层（基于 JSON 文件，默认位置 ~/.cmdbox.json）
# ---------------------------------------------------------------------------

DEFAULT_STORE_FILE = os.path.join(
    os.path.expanduser("~"), ".cmdbox.json"
)

# 内存中的命令仓库：{name: {"cmd": str, "desc": str, "tags": [str]}}
COMMAND_STORE: dict = {}


def _load_store(store_path: str) -> None:
    """从磁盘加载命令仓库到内存。文件不存在时初始化为空仓库。"""
    global COMMAND_STORE
    if not os.path.exists(store_path):
        COMMAND_STORE = {}
        return
    try:
        with open(store_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # 简单校验：必须是 dict，且每个 value 含 "cmd" 字段
        if not isinstance(data, dict):
            COMMAND_STORE = {}
            return
        cleaned = {}
        for name, item in data.items():
            if isinstance(item, dict) and "cmd" in item:
                cleaned[name] = {
                    "cmd": str(item["cmd"]),
                    "desc": str(item.get("desc", "")),
                    "tags": list(item.get("tags", [])),
                }
        COMMAND_STORE = cleaned
    except (OSError, ValueError):
        # 读取失败时使用空仓库（E006/E007 由调用方决定是否提示）
        COMMAND_STORE = {}


def _save_store(store_path: str) -> None:
    """将内存仓库写回磁盘。"""
    try:
        with open(store_path, "w", encoding="utf-8") as fh:
            json.dump(COMMAND_STORE, fh, ensure_ascii=False, indent=2)
    except OSError:
        raise RuntimeError("E006: 无法写入命令存储文件")


def _add_command(name: str, cmd: str, desc: str = "", tags=None) -> None:
    """添加或更新一条命令。name 已存在时抛 E003。"""
    if name in COMMAND_STORE:
        raise RuntimeError(f"E003: 命令 '{name}' 已存在")
    if not cmd.strip():
        raise RuntimeError("E004: 命令内容不能为空")
    COMMAND_STORE[name] = {
        "cmd": cmd,
        "desc": desc,
        "tags": tags or [],
    }


def _remove_command(name: str) -> None:
    """删除一条命令。不存在时抛 E002。"""
    if name not in COMMAND_STORE:
        raise RuntimeError(f"E002: 命令 '{name}' 不存在")
    del COMMAND_STORE[name]


def _get_command(name: str) -> dict:
    """获取单条命令。不存在时抛 E002。"""
    if name not in COMMAND_STORE:
        raise RuntimeError(f"E002: 命令 '{name}' 不存在")
    return COMMAND_STORE[name]


def _find_commands(keyword: str = "", tag: str = "") -> list:
    """按名称/描述模糊搜索，以及按标签过滤。返回 (name, cmd, desc, tags) 列表。"""
    results = []
    kw = keyword.lower()
    for name, item in COMMAND_STORE.items():
        # 标签过滤
        if tag and tag not in item.get("tags", []):
            continue
        # 关键字模糊匹配（名称、描述、命令内容）
        if kw:
            haystack = " ".join([
                name,
                item.get("desc", ""),
                item.get("cmd", ""),
            ]).lower()
            if kw not in haystack:
                continue
        results.append((name, item["cmd"], item.get("desc", ""), item.get("tags", [])))
    return results


def _replace_variables(cmd_text: str, variables: dict) -> str:
    """将命令中的 {{var}} 替换为实际值。缺少变量时抛 E005。"""
    result = cmd_text
    import re
    pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")
    for match in pattern.finditer(cmd_text):
        var_name = match.group(1)
        if var_name not in variables:
            raise RuntimeError(f"E005: 缺少变量 '{var_name}'")
        result = result.replace(match.group(0), str(variables[var_name]))
    return result


def _execute_single(name: str, variables: dict) -> str:
    """执行单条命令（变量替换后返回命令字符串，不实际运行）。"""
    item = _get_command(name)
    return _replace_variables(item["cmd"], variables)


def _execute_chain(names: list, variables: dict, mode: str = "&&") -> str:
    """组合执行多条命令。mode 为 '&&'（串联）或 ';'（并联）。"""
    if not names:
        raise RuntimeError("E010: 组合命令列表为空")
    expanded = []
    for name in names:
        if name not in COMMAND_STORE:
            raise RuntimeError(f"E009: 组合命令中包含不存在的别名 '{name}'")
        cmd_text = _execute_single(name, variables)
        expanded.append(cmd_text)
    return f" {mode} ".join(expanded)


def _export_data() -> dict:
    """导出全部命令数据（用于备份/迁移）。"""
    return COMMAND_STORE


def _import_data(data: dict, overwrite: bool = False) -> int:
    """从 dict 导入命令。返回导入条数。overwrite=True 时覆盖同名。"""
    if not isinstance(data, dict):
        raise RuntimeError("E008: 导入数据必须是对象")
    count = 0
    for name, item in data.items():
        if not isinstance(item, dict) or "cmd" not in item:
            continue
        if name in COMMAND_STORE and not overwrite:
            continue
        COMMAND_STORE[name] = {
            "cmd": str(item["cmd"]),
            "desc": str(item.get("desc", "")),
            "tags": list(item.get("tags", [])),
        }
        count += 1
    return count


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cmdbox",
        description="命令收纳箱：存储、检索并组合执行别名命令",
    )
    sub = parser.add_subparsers(dest="action", help="子命令")

    # add
    p_add = sub.add_parser("add", help="添加命令")
    p_add.add_argument("name", help="别名名称")
    p_add.add_argument("--cmd", required=True, help="命令内容（支持 {{var}}）")
    p_add.add_argument("--desc", default="", help="描述")
    p_add.add_argument("--tag", action="append", default=[], help="标签（可多次）")

    # remove
    p_rm = sub.add_parser("remove", help="删除命令")
    p_rm.add_argument("name", help="别名名称")

    # find
    p_find = sub.add_parser("find", help="搜索命令")
    p_find.add_argument("keyword", nargs="?", default="", help="搜索关键字")
    p_find.add_argument("--tag", default="", help="按标签过滤")

    # run
    p_run = sub.add_parser("run", help="执行单条命令")
    p_run.add_argument("name", help="别名名称")
    p_run.add_argument("--var", action="append", default=[], help="变量 key=value")

    # chain
    p_chain = sub.add_parser("chain", help="组合执行多条命令")
    p_chain.add_argument("names", nargs="+", help="别名列表")
    p_chain.add_argument("--mode", choices=["&&", ";"], default="&&", help="组合方式")
    p_chain.add_argument("--var", action="append", default=[], help="变量 key=value")

    # export
    p_export = sub.add_parser("export", help="导出命令集")
    p_export.add_argument("--file", required=True, help="输出 JSON 文件")

    # import
    p_import = sub.add_parser("import", help="导入命令集")
    p_import.add_argument("--file", required=True, help="输入 JSON 文件")
    p_import.add_argument("--overwrite", action="store_true", help="覆盖同名命令")

    # selftest
    sub.add_parser("selftest", help="运行离线自检")

    return parser


def _parse_variables(var_list: list) -> dict:
    """将 ['key=value', ...] 解析为 dict。格式非法时抛 E001。"""
    variables = {}
    for item in var_list:
        if "=" not in item:
            raise RuntimeError(f"E001: 变量格式应为 key=value，收到: {item}")
        key, value = item.split("=", 1)
        variables[key.strip()] = value
    return variables


def _do_selftest() -> None:
    """离线自检核心逻辑。使用硬编码样例，不依赖外部环境。"""
    # 重置存储（确保自检独立）
    global COMMAND_STORE
    COMMAND_STORE = {}

    # 1. 添加命令
    _add_command("deploy", "npm run build && scp dist/ {{target}}", "部署到服务器", ["prod", "build"])
    _add_command("test", "pytest tests/", "运行测试", ["dev"])
    _add_command("hello", "echo hello {{name}}", "问候", [])

    # 2. 查询验证
    assert len(COMMAND_STORE) == 3, "添加命令失败"
    found = _find_commands(keyword="deploy")
    assert len(found) == 1, "按名称搜索失败"
    assert found[0][0] == "deploy", "搜索结果错误"

    # 3. 变量替换
    cmd = _execute_single("deploy", {"target": "server:/var/www"})
    assert "server:/var/www" in cmd, "变量替换失败"
    assert "{{target}}" not in cmd, "变量替换未完全"

    # 4. 组合执行
    chain_cmd = _execute_chain(["test", "hello"], {"name": "world"}, mode="&&")
    assert "pytest tests/" in chain_cmd, "组合命令缺少第一部分"
    assert "echo hello world" in chain_cmd, "组合命令缺少第二部分"
    assert "&&" in chain_cmd, "组合模式错误"

    # 5. 删除
    _remove_command("hello")
    assert len(COMMAND_STORE) == 2, "删除失败"

    # 6. 导入导出
    exported = _export_data()
    assert "deploy" in exported, "导出数据缺失"
    _import_data({"newcmd": {"cmd": "echo new", "desc": "", "tags": []}})
    assert "newcmd" in COMMAND_STORE, "导入失败"

    # 7. 错误处理验证（宽松断言）
    try:
        _get_command("not_exist")
        assert False, "应该抛出 E002"
    except RuntimeError as e:
        assert "E002" in str(e), f"错误码错误: {e}"

    try:
        _execute_single("deploy", {})  # 缺少 target
        assert False, "应该抛出 E005"
    except RuntimeError as e:
        assert "E005" in str(e), f"错误码错误: {e}"

    # 8. 搜索结果数量宽松判断（>0 即可）
    search_results = _find_commands(keyword="test")
    assert len(search_results) > 0, "搜索 test 应有结果"

    # 9. 组合中不存在的命令
    try:
        _execute_chain(["deploy", "ghost"], {}, mode=";")
        assert False, "应该抛出 E009"
    except RuntimeError as e:
        assert "E009" in str(e), f"错误码错误: {e}"

    # 自检通过
    print("selftest: OK (all assertions passed)")


def main(argv=None) -> int:
    """主入口。返回进程退出码。"""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # 未指定动作时打印帮助
    if not args.action:
        parser.print_help()
        return 0

    # selftest 不需要加载存储文件
    if args.action == "selftest":
        _do_selftest()
        return 0

    # 其余动作需要加载存储
    store_file = os.environ.get("CMDBOX_STORE", DEFAULT_STORE_FILE)
    _load_store(store_file)

    try:
        if args.action == "add":
            _add_command(args.name, args.cmd, args.desc, args.tag)
            _save_store(store_file)
            print(f"已添加: {args.name}")

        elif args.action == "remove":
            _remove_command(args.name)
            _save_store(store_file)
            print(f"已删除: {args.name}")

        elif args.action == "find":
            results = _find_commands(args.keyword, args.tag)
            if not results:
                print("未找到匹配命令")
            else:
                for name, cmd, desc, tags in results:
                    print(f"[{name}] {cmd}  # {desc} (tags: {','.join(tags)})")

        elif args.action == "run":
            variables = _parse_variables(args.var)
            cmd_text = _execute_single(args.name, variables)
            print(cmd_text)

        elif args.action == "chain":
            variables = _parse_variables(args.var)
            cmd_text = _execute_chain(args.names, variables, mode=args.mode)
            print(cmd_text)

        elif args.action == "export":
            data = _export_data()
            try:
                with open(args.file, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False, indent=2)
                print(f"已导出 {len(data)} 条命令到 {args.file}")
            except OSError:
                raise RuntimeError("E006: 导出文件写入失败")

        elif args.action == "import":
            try:
                with open(args.file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except OSError:
                raise RuntimeError("E006: 导入文件读取失败")
            except ValueError:
                raise RuntimeError("E007: 导入文件不是合法 JSON")
            count = _import_data(data, overwrite=args.overwrite)
            _save_store(store_file)
            print(f"已导入 {count} 条命令")

        else:
            raise RuntimeError(f"E001: 未知动作 {args.action}")

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
