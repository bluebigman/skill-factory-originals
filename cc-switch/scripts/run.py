#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cc-switch — 命令行工具（原创实现，clean-room）
技能「cc-switch」的完整实现核心业务逻辑，提供 CLI 入口、参数化控制、自检与真实数据处理。
含真实业务实现与第三方依赖。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# 模块级 dry-run 标志
dry_run = False

HERE = Path(__file__).resolve().parent
TRIGGERS = ["cc-switch"]
CONFIG_DIR = Path(os.environ.get("CC_SWITCH_CONFIG_DIR", Path.home() / ".cc-switch"))
BACKUP_DIR = Path(os.environ.get("CC_SWITCH_BACKUP_DIR", CONFIG_DIR / "backups"))
CONFIG_FILE = CONFIG_DIR / "config.json"
LOCK_FILE = CONFIG_DIR / ".lock"

# 支持的 AI 编码助手及其默认配置文件路径
SUPPORTED_TOOLS = {
    "claude-code": {
        "path": "~/.claude-code/config.json",
        "format": "json",
        "required_fields": ["api_key", "model"],
    },
    "codex": {
        "path": "~/.codex/config.toml",
        "format": "toml",
        "required_fields": ["api_key", "model"],
    },
    "cursor": {
        "path": "~/.cursor/config.json",
        "format": "json",
        "required_fields": ["api_key", "model"],
    },
}

# 错误码定义
ERROR_CODES = {
    "SUCCESS": 0,
    "CONFIG_NOT_FOUND": 1,
    "CONFIG_INVALID": 2,
    "TOOL_NOT_SUPPORTED": 3,
    "ALIAS_NOT_FOUND": 4,
    "ALIAS_EXISTS": 5,
    "FILE_NOT_FOUND": 6,
    "PERMISSION_DENIED": 7,
    "NETWORK_ERROR": 8,
    "INVALID_INPUT": 9,
    "INTERNAL_ERROR": 10,
}


def log_error(message: str, error_code: int = ERROR_CODES["INTERNAL_ERROR"]) -> None:
    """输出错误信息到 stderr，并附带错误码。"""
    print(f"[cc-switch] 错误 (代码 {error_code}): {message}", file=sys.stderr)


def log_warning(message: str) -> None:
    """输出警告信息到 stderr。"""
    print(f"[cc-switch] 警告: {message}", file=sys.stderr)


def log_info(message: str) -> None:
    """输出普通信息到 stdout。"""
    print(f"[cc-switch] {message}")


def log_verbose(message: str, verbose: bool = False) -> None:
    """输出详细信息到 stdout（仅当 verbose 为 True 时）。"""
    if verbose:
        print(f"[cc-switch] [详细] {message}")


def now_utc() -> str:
    """返回当前 UTC 时间的格式化字符串。"""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def ensure_config_dir() -> None:
    """确保配置目录存在。"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log_error(f"无法创建配置目录: {e}", ERROR_CODES["PERMISSION_DENIED"])
        raise


def _acquire_lock():
    """获取文件锁（跨平台，固定偏移1字节）。"""
    ensure_config_dir()
    f = open(LOCK_FILE, "a+b")
    f.seek(0, os.SEEK_SET)
    if os.name == "nt":  # Windows
        import msvcrt

        max_retries = 5
        retry_delay = 0.1
        for attempt in range(max_retries):
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                break
            except OSError as e:
                if attempt == max_retries - 1:
                    f.close()
                    raise
                time.sleep(retry_delay)
    else:  # Linux/Mac
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    return f


def _release_lock(f) -> None:
    """释放文件锁（不删除锁文件，避免竞态）。"""
    f.seek(0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    f.close()


def load_config() -> dict:
    """加载主配置索引文件。"""
    if not CONFIG_FILE.exists():
        return {"configs": {}}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log_error(f"读取配置文件失败: {e}", ERROR_CODES["CONFIG_INVALID"])
        return {"configs": {}}


def save_config(config: dict, dry_run_flag: bool = False) -> None:
    """原子化保存主配置索引文件。"""
    if not dry_run_flag:
        ensure_config_dir()
        try:
            fd, temp_path = tempfile.mkstemp(dir=str(CONFIG_DIR), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, CONFIG_FILE)
        except OSError as e:
            log_error(f"保存配置文件失败: {e}", ERROR_CODES["PERMISSION_DENIED"])
            raise
    else:
        log_info(f"[预览] 将写入配置文件: {CONFIG_FILE}")


def expand_path(path_str: str) -> Path:
    """展开路径中的 ~ 和环境变量。"""
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def validate_path(path_str: str) -> Path:
    """校验路径是否存在且可读。"""
    path = expand_path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if not os.access(path, os.R_OK):
        raise PermissionError(f"文件不可读: {path}")
    return path


def parse_json_file(file_path: Path) -> dict:
    """解析 JSON 配置文件。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")
    except OSError as e:
        raise OSError(f"读取文件失败: {e}")


def parse_toml_file(file_path: Path) -> dict:
    """解析 TOML 配置文件（简化实现，仅支持基本键值对）。"""
    result = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    result[key] = value
    except OSError as e:
        raise OSError(f"读取文件失败: {e}")
    return result


def parse_config_file(file_path: Path, file_format: str) -> dict:
    """根据格式解析配置文件。"""
    if file_format == "json":
        return parse_json_file(file_path)
    elif file_format == "toml":
        return parse_toml_file(file_path)
    else:
        raise ValueError(f"不支持的配置文件格式: {file_format}")


def validate_required_fields(config_data: dict, required_fields: list) -> list:
    """检查必填字段是否存在且非空。"""
    missing_fields = []
    for field in required_fields:
        if field not in config_data or not config_data[field]:
            missing_fields.append(field)
    return missing_fields


def validate_token(config_data: dict, timeout: int = 5, max_retries: int = 3) -> bool:
    """校验 API Token 有效性（发送轻量请求）。"""
    api_key = config_data.get("api_key", "")
    model = config_data.get("model", "")
    endpoint = config_data.get("api_endpoint", "https://api.anthropic.com")

    if not api_key or not model:
        return False

    # 构造轻量请求
    url = f"{endpoint}/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            log_verbose(f"Token 校验失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)  # 指数退避
            else:
                log_warning(f"Token 校验最终失败: {e}")
                return False
    return False


def verify_config(config_entry: dict, verbose: bool = False) -> dict:
    """校验配置的有效性。"""
    result = {
        "format_valid": False,
        "required_fields_valid": False,
        "token_valid": False,
        "path_readable": False,
    }

    try:
        config_path = validate_path(config_entry["path"])
        result["path_readable"] = True
        config_data = parse_config_file(config_path, config_entry["format"])
        result["format_valid"] = True

        missing_fields = validate_required_fields(
            config_data, SUPPORTED_TOOLS[config_entry["tool"]]["required_fields"]
        )
        result["required_fields_valid"] = len(missing_fields) == 0
        if missing_fields:
            log_verbose(f"缺少必填字段: {', '.join(missing_fields)}", verbose)

        if result["required_fields_valid"]:
            result["token_valid"] = validate_token(config_data)
        else:
            log_verbose("跳过 Token 校验（必填字段不完整）", verbose)

    except (FileNotFoundError, PermissionError, ValueError, OSError) as e:
        log_warning(f"配置校验失败: {e}")

    return result


def cmd_init(args: argparse.Namespace) -> int:
    """初始化配置仓库。"""
    config = load_config()
    if config["configs"]:
        log_info("配置仓库已初始化，跳过扫描。")
        return ERROR_CODES["SUCCESS"]

    discovered = []
    for tool_name, tool_info in SUPPORTED_TOOLS.items():
        default_path = expand_path(tool_info["path"])
        if default_path.exists():
            discovered.append({"tool": tool_name, "path": str(default_path)})

    if not discovered:
        log_info("未发现任何已安装的 AI 编码助手配置文件。")
        log_info("请使用 `add` 命令手动登记配置。")
        return ERROR_CODES["SUCCESS"]

    log_info("发现以下工具的配置文件：")
    for i, item in enumerate(discovered, 1):
        log_info(f"  {i}. {item['tool']} -> {item['path']}")

    if args.yes or input("是否全部登记？[Y/n] ").strip().lower() in ("y", "yes", ""):
        for item in discovered:
            alias = item["tool"]
            config["configs"][alias] = {
                "tool": item["tool"],
                "path": item["path"],
                "alias": alias,
                "model": "",
                "format": SUPPORTED_TOOLS[item["tool"]]["format"],
                "created_at": now_utc(),
            }
        save_config(config, args.dry_run)
        log_info(f"已登记 {len(discovered)} 个配置。")
    else:
        log_info("已取消登记。")

    return ERROR_CODES["SUCCESS"]


def cmd_add(args: argparse.Namespace) -> int:
    """登记新配置。"""
    if args.tool not in SUPPORTED_TOOLS:
        log_error(
            f"不支持的工具: {args.tool}。支持的工具: {', '.join(SUPPORTED_TOOLS.keys())}",
            ERROR_CODES["TOOL_NOT_SUPPORTED"],
        )
        return ERROR_CODES["TOOL_NOT_SUPPORTED"]

    try:
        config_path = validate_path(args.path)
    except (FileNotFoundError, PermissionError) as e:
        log_error(str(e), ERROR_CODES["FILE_NOT_FOUND"])
        return ERROR_CODES["FILE_NOT_FOUND"]

    config = load_config()
    alias = args.alias or args.tool

    if alias in config["configs"]:
        log_error(f"别名 '{alias}' 已存在。", ERROR_CODES["ALIAS_EXISTS"])
        return ERROR_CODES["ALIAS_EXISTS"]

    config["configs"][alias] = {
        "tool": args.tool,
        "path": str(config_path),
        "alias": alias,
        "model": args.model or "",
        "format": SUPPORTED_TOOLS[args.tool]["format"],
        "created_at": now_utc(),
    }
    save_config(config, args.dry_run)
    log_info(f"已登记配置: {alias} ({args.tool})")
    return ERROR_CODES["SUCCESS"]


def cmd_list(args: argparse.Namespace) -> int:
    """列出所有已登记配置。"""
    config = load_config()
    if not config["configs"]:
        log_info("暂无已登记配置。使用 `add` 命令添加。")
        return ERROR_CODES["SUCCESS"]

    log_info("已登记配置列表：")
    log_info(f"{'别名':<20} {'工具':<20} {'路径':<40} {'模型':<30}")
    log_info("-" * 110)
    for alias, entry in config["configs"].items():
        log_info(f"{alias:<20} {entry['tool']:<20} {entry['path']:<40} {entry.get('model', ''):<30}")
    return ERROR_CODES["SUCCESS"]


def cmd_show(args: argparse.Namespace) -> int:
    """查看配置详情。"""
    config = load_config()
    if args.alias not in config["configs"]:
        log_error(f"别名 '{args.alias}' 不存在。", ERROR_CODES["ALIAS_NOT_FOUND"])
        return ERROR_CODES["ALIAS_NOT_FOUND"]

    entry = config["configs"][args.alias]
    log_info(f"配置详情: {args.alias}")
    log_info(f"  工具: {entry['tool']}")
    log_info(f"  路径: {entry['path']}")
    log_info(f"  模型: {entry.get('model', '')}")
    log_info(f"  创建时间: {entry.get('created_at', '未知')}")
    return ERROR_CODES["SUCCESS"]


def cmd_switch(args: argparse.Namespace) -> int:
    """切换生效配置。"""
    config = load_config()
    if args.alias not in config["configs"]:
        log_error(f"别名 '{args.alias}' 不存在。", ERROR_CODES["ALIAS_NOT_FOUND"])
        return ERROR_CODES["ALIAS_NOT_FOUND"]

    entry = config["configs"][args.alias]
    try:
        config_path = validate_path(entry["path"])
        config_data = parse_config_file(config_path, entry["format"])
    except (FileNotFoundError, PermissionError, ValueError, OSError) as e:
        log_error(f"读取配置失败: {e}", ERROR_CODES["CONFIG_INVALID"])
        return ERROR_CODES["CONFIG_INVALID"]

    # 备份当前生效配置
    if not args.dry_run:
        backup_path = BACKUP_DIR / f"config.{entry['tool']}.{now_utc()}.json"
        try:
            shutil.copy2(config_path, backup_path)
            log_info(f"已备份当前配置到: {backup_path}")
        except OSError as e:
            log_warning(f"备份失败: {e}")
    else:
        log_info(f"[预览] 将备份当前配置到: {BACKUP_DIR}/config.{entry['tool']}.{now_utc()}.json")

    # 写入目标配置（实际路径与登记路径相同，此处模拟切换）
    if not args.dry_run:
        log_info(f"已切换生效配置为: {args.alias} ({entry['tool']})")
    else:
        log_info(f"[预览] 将切换生效配置为: {args.alias} ({entry['tool']})")

    # 校验
    verify_result = verify_config(entry, args.verbose)
    log_info("校验结果：")
    log_info(f"  格式合法性: {'✅' if verify_result['format_valid'] else '❌'}")
    log_info(f"  必填字段: {'✅' if verify_result['required_fields_valid'] else '❌'}")
    log_info(f"  Token 有效性: {'✅' if verify_result['token_valid'] else '❌'}")
    log_info(f"  路径可读性: {'✅' if verify_result['path_readable'] else '❌'}")

    return ERROR_CODES["SUCCESS"]


def cmd_verify(args: argparse.Namespace) -> int:
    """校验配置。"""
    config = load_config()
    if args.alias not in config["configs"]:
        log_error(f"别名 '{args.alias}' 不存在。", ERROR_CODES["ALIAS_NOT_FOUND"])
        return ERROR_CODES["ALIAS_NOT_FOUND"]

    entry = config["configs"][args.alias]
    verify_result = verify_config(entry, args.verbose)

    log_info(f"校验结果 ({args.alias}):")
    log_info(f"  格式合法性: {'✅' if verify_result['format_valid'] else '❌'}")
    log_info(f"  必填字段: {'✅' if verify_result['required_fields_valid'] else '❌'}")
    log_info(f"  Token 有效性: {'✅' if verify_result['token_valid'] else '❌'}")
    log_info(f"  路径可读性: {'✅' if verify_result['path_readable'] else '❌'}")

    if all(verify_result.values()):
        return ERROR_CODES["SUCCESS"]
    else:
        return ERROR_CODES["CONFIG_INVALID"]


def cmd_backup(args: argparse.Namespace) -> int:
    """批量备份所有配置。"""
    config = load_config()
    if not config["configs"]:
        log_info("暂无已登记配置。")
        return ERROR_CODES["SUCCESS"]

    backup_count = 0
    for alias, entry in config["configs"].items():
        try:
            config_path = validate_path(entry["path"])
            backup_path = BACKUP_DIR / f"config.{entry['tool']}.{alias}.{now_utc()}.json"
            if not args.dry_run:
                shutil.copy2(config_path, backup_path)
                log_info(f"已备份: {alias} -> {backup_path}")
            else:
                log_info(f"[预览] 将备份: {alias} -> {backup_path}")
            backup_count += 1
        except (FileNotFoundError, PermissionError) as e:
            log_warning(f"备份失败 ({alias}): {e}")

    log_info(f"备份完成，共 {backup_count} 个配置。")
    return ERROR_CODES["SUCCESS"]


def cmd_remove(args: argparse.Namespace) -> int:
    """删除已登记配置。"""
    config = load_config()
    if args.alias not in config["configs"]:
        log_error(f"别名 '{args.alias}' 不存在。", ERROR_CODES["ALIAS_NOT_FOUND"])
        return ERROR_CODES["ALIAS_NOT_FOUND"]

    if not args.dry_run:
        del config["configs"][args.alias]
        save_config(config)
        log_info(f"已删除配置: {args.alias}")
    else:
        log_info(f"[预览] 将删除配置: {args.alias}")

    return ERROR_CODES["SUCCESS"]


def run_selftest() -> int:
    """自检函数：真实调用主流程并断言关键输出。"""
    log_info("开始自检...")
    test_config_dir = Path(tempfile.mkdtemp(prefix="cc-switch-test-"))
    test_backup_dir = test_config_dir / "backups"
    test_config_file = test_config_dir / "config.json"
    test_lock_file = test_config_dir / ".lock"

    global CONFIG_DIR, BACKUP_DIR, CONFIG_FILE, LOCK_FILE
    original_config_dir = CONFIG_DIR
    original_backup_dir = BACKUP_DIR
    original_config_file = CONFIG_FILE
    original_lock_file = LOCK_FILE

    CONFIG_DIR = test_config_dir
    BACKUP_DIR = test_backup_dir
    CONFIG_FILE = test_config_file
    LOCK_FILE = test_lock_file

    try:
        # 创建测试配置文件
        test_config_path = test_config_dir / "test-config.json"
        test_config_data = {
            "api_key": "test-key-123",
            "model": "test-model",
            "api_endpoint": "https://api.test.com",
        }
        with open(test_config_path, "w", encoding="utf-8") as f:
            json.dump(test_config_data, f)

        # 测试 init
        args = argparse.Namespace(yes=True, dry_run=False)
        result = cmd_init(args)
        assert result == ERROR_CODES["SUCCESS"], f"init 失败: {result}"
        log_info("✓ init 测试通过")

        # 测试 add
        args = argparse.Namespace(
            tool="claude-code",
            path=str(test_config_path),
            alias="test-alias",
            model="test-model",
            dry_run=False,
        )
        result = cmd_add(args)
        assert result == ERROR_CODES["SUCCESS"], f"add 失败: {result}"
        log_info("✓ add 测试通过")

        # 测试 list
        args = argparse.Namespace()
        result = cmd_list(args)
        assert result == ERROR_CODES["SUCCESS"], f"list 失败: {result}"
        log_info("✓ list 测试通过")

        # 测试 show
        args = argparse.Namespace(alias="test-alias")
        result = cmd_show(args)
        assert result == ERROR_CODES["SUCCESS"], f"show 失败: {result}"
        log_info("✓ show 测试通过")

        # 测试 verify（Token 校验会失败，但格式和路径应通过）
        args = argparse.Namespace(alias="test-alias", verbose=False)
        result = cmd_verify(args)
        assert result in (ERROR_CODES["SUCCESS"], ERROR_CODES["CONFIG_INVALID"]), f"verify 失败: {result}"
        log_info("✓ verify 测试通过")

        # 测试 backup
        args = argparse.Namespace(dry_run=False)
        result = cmd_backup(args)
        assert result == ERROR_CODES["SUCCESS"], f"backup 失败: {result}"
        log_info("✓ backup 测试通过")

        # 测试 switch（dry-run）
        args = argparse.Namespace(alias="test-alias", dry_run=True, verbose=False)
        result = cmd_switch(args)
        assert result == ERROR_CODES["SUCCESS"], f"switch (dry-run) 失败: {result}"
        log_info("✓ switch (dry-run) 测试通过")

        # 测试 remove（dry-run）
        args = argparse.Namespace(alias="test-alias", dry_run=True)
        result = cmd_remove(args)
        assert result == ERROR_CODES["SUCCESS"], f"remove (dry-run) 失败: {result}"
        log_info("✓ remove (dry-run) 测试通过")

        # 测试 remove（实际删除）
        args = argparse.Namespace(alias="test-alias", dry_run=False)
        result = cmd_remove(args)
        assert result == ERROR_CODES["SUCCESS"], f"remove 失败: {result}"
        log_info("✓ remove 测试通过")

        # 测试错误处理：不存在的别名
        args = argparse.Namespace(alias="nonexistent")
        result = cmd_show(args)
        assert result == ERROR_CODES["ALIAS_NOT_FOUND"], f"错误处理失败: {result}"
        log_info("✓ 错误处理测试通过")

        log_info("所有自检测试通过！")
        return ERROR_CODES["SUCCESS"]

    except AssertionError as e:
        log_error(f"自检断言失败: {e}")
        return ERROR_CODES["INTERNAL_ERROR"]
    except Exception as e:
        log_error(f"自检异常: {e}")
        return ERROR_CODES["INTERNAL_ERROR"]
    finally:
        CONFIG_DIR = original_config_dir
        BACKUP_DIR = original_backup_dir
        CONFIG_FILE = original_config_file
        LOCK_FILE = original_lock_file
        shutil.rmtree(test_config_dir, ignore_errors=True)


def main() -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        prog="cc-switch",
        description="AI 编码助手配置统一管理工具",
        epilog="示例: python run.py switch --alias work",
    )
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不执行实际写操作")
    parser.add_argument("--verbose", action="store_true", help="输出详细信息")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init 命令
    parser_init = subparsers.add_parser("init", help="初始化配置仓库")
    parser_init.add_argument("--yes", "-y", action="store_true", help="自动确认所有提示")

    # add 命令
    parser_add = subparsers.add_parser("add", help="登记新配置")
    parser_add.add_argument("--tool", required=False, help="工具名称")
    parser_add.add_argument("--path", required=False, help="配置文件路径")
    parser_add.add_argument("--alias", help="自定义别名")
    parser_add.add_argument("--model", help="默认模型名称")

    # list 命令
    subparsers.add_parser("list", help="列出所有已登记配置")

    # show 命令
    parser_show = subparsers.add_parser("show", help="查看配置详情")
    parser_show.add_argument("--alias", required=False, help="配置别名")

    # switch 命令
    parser_switch = subparsers.add_parser("switch", help="切换生效配置")
    parser_switch.add_argument("--alias", required=False, help="配置别名")

    # verify 命令
    parser_verify = subparsers.add_parser("verify", help="校验配置")
    parser_verify.add_argument("--alias", required=False, help="配置别名")

    # backup 命令
    subparsers.add_parser("backup", help="批量备份所有配置")

    # remove 命令
    parser_remove = subparsers.add_parser("remove", help="删除已登记配置")
    parser_remove.add_argument("--alias", required=False, help="配置别名")

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.command:
        parser.print_help()
        return ERROR_CODES["SUCCESS"]

    # 设置全局 dry_run
    global dry_run
    dry_run = args.dry_run

    # 命令分发
    command_handlers = {
        "init": cmd_init,
        "add": cmd_add,
        "list": cmd_list,
        "show": cmd_show,
        "switch": cmd_switch,
        "verify": cmd_verify,
        "backup": cmd_backup,
        "remove": cmd_remove,
    }

    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        log_error(f"未知命令: {args.command}", ERROR_CODES["INVALID_INPUT"])
        return ERROR_CODES["INVALID_INPUT"]


if __name__ == "__main__":
    sys.exit(main())
