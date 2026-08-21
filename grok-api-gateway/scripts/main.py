#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grok API 网关配置工具 - 独立实现脚本

本脚本依据功能规格独立实现，用于配置多账户 Grok API 网关，
支持 Grok Build、Web 和 Console 接口的负载均衡与密钥管理。

功能：
- 解析多账户配置（支持 JSON / YAML / 文本格式）
- 负载均衡策略（轮询 / 随机 / 最少连接）
- 密钥脱敏与安全校验
- 配置预览（--dry-run）与落盘（--force）
- 内置离线自检（--selftest）

错误码：
E001 输入为空
E002 关键信息缺失
E003 输入格式错误
E004 超出能力边界
E005 置信度过低
E006 文件读取失败
E007 配置解析失败
E008 密钥格式错误
E009 路径非法
E010 未知异常
"""

import argparse
import json
import os
import random
import re
import sys
import tempfile
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 内置样例数据（用于 --selftest 离线自检）
# ============================================================
SAMPLE_CONFIG_JSON = """
{
  "accounts": [
    {
      "name": "account-a",
      "api_key": "sk-ant-a1b2c3d4e5f6g7h8i9j0",
      "endpoint": "https://api.grok.example.com/v1",
      "weight": 3
    },
    {
      "name": "account-b",
      "api_key": "sk-ant-k2l3m4n5o6p7q8r9s0t1",
      "endpoint": "https://api.grok.example.com/v2",
      "weight": 1
    }
  ],
  "strategy": "round_robin",
  "timeout": 30
}
"""

SAMPLE_CONFIG_TEXT = """
account-a|sk-ant-a1b2c3d4e5f6g7h8i9j0|https://api.grok.example.com/v1|3
account-b|sk-ant-k2l3m4n5o6p7q8r9s0t1|https://api.grok.example.com/v2|1
"""

SAMPLE_CONFIG_YAML = """
accounts:
  - name: account-a
    api_key: sk-ant-a1b2c3d4e5f6g7h8i9j0
    endpoint: https://api.grok.example.com/v1
    weight: 3
  - name: account-b
    api_key: sk-ant-k2l3m4n5o6p7q8r9s0t1
    endpoint: https://api.grok.example.com/v2
    weight: 1
strategy: round_robin
timeout: 30
"""


# ============================================================
# 输入校验（guard clause 风格）
# ============================================================
def validate_input(raw_text: str) -> str:
    """校验输入文本，空输入抛出 E001。"""
    if raw_text is None:
        raise ValueError("E001: 输入为空，请提供待处理的内容")
    if not isinstance(raw_text, str):
        raise ValueError("E003: 输入格式错误，需要字符串类型")
    if not raw_text.strip():
        raise ValueError("E001: 输入为空，请提供待处理的内容")
    return raw_text.strip()


def validate_output_path(path: str) -> str:
    """校验输出路径，防路径穿越。"""
    if not path or not isinstance(path, str):
        raise ValueError("E009: 路径非法，必须为非空字符串")
    # 白名单校验：只允许相对路径或当前目录下的文件
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or normalized.startswith("/"):
        raise ValueError("E009: 路径非法，禁止绝对路径或上级目录穿越")
    return normalized


def validate_api_key(api_key: str) -> bool:
    """校验 API 密钥格式（宽松校验，仅检查长度和字符集）。"""
    if not api_key or not isinstance(api_key, str):
        return False
    # 宽松规则：长度 >= 8，只包含字母数字和常见符号
    if len(api_key) < 8:
        return False
    if not re.match(r"^[A-Za-z0-9_\-\.]+$", api_key):
        return False
    return True


# ============================================================
# 核心逻辑：配置解析
# ============================================================
def parse_json_config(text: str) -> Dict[str, Any]:
    """解析 JSON 格式配置。"""
    try:
        data = json.loads(text, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError as exc:
        raise ValueError(f"E007: JSON 解析失败 - {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("E007: JSON 根节点必须是对象")
    return data


def parse_text_config(text: str) -> Dict[str, Any]:
    """解析管道分隔的文本配置。"""
    accounts = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            raise ValueError(f"E007: 文本行格式错误: {line}")
        account = {
            "name": parts[0],
            "api_key": parts[1],
            "endpoint": parts[2],
        }
        if len(parts) >= 4:
            try:
                account["weight"] = int(parts[3])
            except ValueError:
                account["weight"] = 1
        else:
            account["weight"] = 1
        accounts.append(account)
    if not accounts:
        raise ValueError("E007: 文本配置中未找到有效账户")
    return {"accounts": accounts, "strategy": "round_robin", "timeout": 30}


def parse_yaml_config(text: str) -> Dict[str, Any]:
    """解析 YAML 格式配置（简化实现，支持基础键值对）。"""
    accounts = []
    current_account = None
    strategy = "round_robin"
    timeout = 30
    in_accounts = False

    for line in text.strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            if stripped.startswith("accounts:"):
                in_accounts = True
                current_account = None
            elif stripped.startswith("strategy:"):
                strategy = stripped.split(":", 1)[1].strip()
                in_accounts = False
            elif stripped.startswith("timeout:"):
                try:
                    timeout = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    timeout = 30
                in_accounts = False
        elif in_accounts and indent == 2:
            if stripped.startswith("- name:"):
                if current_account:
                    accounts.append(current_account)
                current_account = {"name": stripped.split(":", 1)[1].strip()}
            elif current_account and ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "api_key":
                    current_account["api_key"] = value
                elif key == "endpoint":
                    current_account["endpoint"] = value
                elif key == "weight":
                    try:
                        current_account["weight"] = int(value)
                    except ValueError:
                        current_account["weight"] = 1
    if current_account:
        accounts.append(current_account)
    if not accounts:
        raise ValueError("E007: YAML 配置中未找到有效账户")
    return {"accounts": accounts, "strategy": strategy, "timeout": timeout}


def parse_config(text: str, fmt: str = "auto") -> Dict[str, Any]:
    """统一配置解析入口，自动检测格式或按指定格式解析。"""
    text = validate_input(text)
    if fmt == "json":
        return parse_json_config(text)
    if fmt == "text":
        return parse_text_config(text)
    if fmt == "yaml":
        return parse_yaml_config(text)
    # 自动检测
    stripped = text.strip()
    if stripped.startswith("{"):
        return parse_json_config(text)
    if "|" in stripped and "\n" in stripped:
        return parse_text_config(text)
    if stripped.startswith("accounts:"):
        return parse_yaml_config(text)
    raise ValueError("E003: 无法自动识别配置格式，请指定 --format")


# ============================================================
# 核心逻辑：负载均衡
# ============================================================
def normalize_accounts(accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化账户列表，填充默认值并校验密钥。"""
    if not accounts:
        raise ValueError("E002: 账户列表为空，缺少关键信息")
    normalized = []
    for idx, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            raise ValueError(f"E003: 第 {idx + 1} 个账户格式错误")
        name = acc.get("name", f"account-{idx + 1}")
        api_key = acc.get("api_key", "")
        endpoint = acc.get("endpoint", "")
        if not api_key:
            raise ValueError(f"E002: 账户 {name} 缺少 api_key")
        if not validate_api_key(api_key):
            raise ValueError(f"E008: 账户 {name} 的 api_key 格式错误")
        if not endpoint:
            raise ValueError(f"E002: 账户 {name} 缺少 endpoint")
        weight = acc.get("weight", 1)
        try:
            weight = int(weight)
        except (TypeError, ValueError):
            weight = 1
        weight = max(1, min(weight, 10))  # 权重限制 1-10
        normalized.append({
            "name": name,
            "api_key": api_key,
            "endpoint": endpoint,
            "weight": weight,
        })
    return normalized


def mask_api_key(api_key: str) -> str:
    """脱敏 API 密钥，只显示前 6 位和后 4 位。"""
    if len(api_key) <= 10:
        return api_key[:2] + "***" + api_key[-2:]
    return api_key[:6] + "***" + api_key[-4:]


def select_account(accounts: List[Dict[str, Any]], strategy: str, counter: int = 0) -> Dict[str, Any]:
    """按策略选择账户。"""
    if not accounts:
        raise ValueError("E002: 账户列表为空")
    if strategy == "random":
        return random.choice(accounts)
    if strategy == "least_conn":
        # 简化实现：均匀轮询（真实场景需连接计数）
        return accounts[counter % len(accounts)]
    # 默认 round_robin，按权重展开
    weighted = []
    for acc in accounts:
        weighted.extend([acc] * acc["weight"])
    return weighted[counter % len(weighted)]


# ============================================================
# 核心逻辑：配置生成
# ============================================================
def build_gateway_config(config: Dict[str, Any], counter: int = 0) -> Dict[str, Any]:
    """构建网关配置，返回脱敏后的可展示配置。"""
    accounts = normalize_accounts(config.get("accounts", []))
    strategy = config.get("strategy", "round_robin")
    timeout = config.get("timeout", 30)
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        timeout = 30
    timeout = max(1, min(timeout, 120))

    selected = select_account(accounts, strategy, counter)

    result = {
        "gateway": {
            "strategy": strategy,
            "timeout_seconds": timeout,
            "total_accounts": len(accounts),
        },
        "selected": {
            "name": selected["name"],
            "endpoint": selected["endpoint"],
            "api_key_masked": mask_api_key(selected["api_key"]),
        },
        "accounts": [
            {
                "name": acc["name"],
                "endpoint": acc["endpoint"],
                "api_key_masked": mask_api_key(acc["api_key"]),
                "weight": acc["weight"],
            }
            for acc in accounts
        ],
    }
    return result


# ============================================================
# 输出格式化
# ============================================================
def format_output(config: Dict[str, Any], verbose: bool = False) -> str:
    """格式化输出为可读文本。"""
    lines = []
    lines.append("=" * 50)
    lines.append("Grok API 网关配置")
    lines.append("=" * 50)
    gw = config["gateway"]
    lines.append(f"负载均衡策略: {gw['strategy']}")
    lines.append(f"超时时间: {gw['timeout_seconds']} 秒")
    lines.append(f"账户总数: {gw['total_accounts']}")
    lines.append("")
    sel = config["selected"]
    lines.append(f"当前选中账户: {sel['name']}")
    lines.append(f"端点: {sel['endpoint']}")
    lines.append(f"API Key: {sel['api_key_masked']}")
    lines.append("")
    lines.append("账户列表:")
    for acc in config["accounts"]:
        lines.append(f"  - {acc['name']} | {acc['endpoint']} | {acc['api_key_masked']} | 权重={acc['weight']}")
    if verbose:
        lines.append("")
        lines.append("--- 详细决策说明 ---")
        lines.append(f"选择策略 '{gw['strategy']}'，从 {gw['total_accounts']} 个账户中选择")
        lines.append(f"选中账户 '{sel['name']}'，API Key 已脱敏")
        lines.append("密钥校验通过，格式合规")
    lines.append("=" * 50)
    return "\n".join(lines)


def format_diff(old_text: str, new_text: str) -> str:
    """生成简单的 diff 摘要（行级对比）。"""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff_lines = []
    max_len = max(len(old_lines), len(new_lines))
    for i in range(max_len):
        old_line = old_lines[i] if i < len(old_lines) else "(新增)"
        new_line = new_lines[i] if i < len(new_lines) else "(删除)"
        if old_line != new_line:
            diff_lines.append(f"行 {i + 1}:")
            diff_lines.append(f"  - {old_line}")
            diff_lines.append(f"  + {new_line}")
    if not diff_lines:
        return "（无差异）"
    return "\n".join(diff_lines)


# ============================================================
# 文件读写（多编码支持）
# ============================================================
def read_file_with_encoding(filepath: str) -> str:
    """读取文件，支持多编码 fallback。"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError as exc:
            raise ValueError(f"E006: 文件不存在 - {filepath}") from exc
        except OSError as exc:
            raise ValueError(f"E006: 文件读取失败 - {exc}") from exc
    # 最后用 replace 模式兜底
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as exc:
        raise ValueError(f"E006: 文件读取失败 - {exc}") from exc


def write_file_with_encoding(filepath: str, content: str) -> None:
    """写入文件，使用 UTF-8 编码。"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as exc:
        raise ValueError(f"E006: 文件写入失败 - {exc}") from exc


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> int:
    """运行内置离线自检，返回退出码。"""
    print("[SELFTEST] 开始离线自检...")
    failures = 0

    # 测试 1: JSON 配置解析
    try:
        config = parse_config(SAMPLE_CONFIG_JSON, "json")
        assert len(config["accounts"]) == 2, "JSON 解析账户数错误"
        assert config["strategy"] == "round_robin", "JSON 策略错误"
        print("[SELFTEST] JSON 解析: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] JSON 解析: FAIL - {exc}")

    # 测试 2: 文本配置解析
    try:
        config = parse_config(SAMPLE_CONFIG_TEXT, "text")
        assert len(config["accounts"]) == 2, "文本解析账户数错误"
        assert config["accounts"][0]["name"] == "account-a", "文本解析名称错误"
        print("[SELFTEST] 文本解析: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 文本解析: FAIL - {exc}")

    # 测试 3: YAML 配置解析
    try:
        config = parse_config(SAMPLE_CONFIG_YAML, "yaml")
        assert len(config["accounts"]) == 2, "YAML 解析账户数错误"
        assert config["accounts"][1]["name"] == "account-b", "YAML 解析名称错误"
        print("[SELFTEST] YAML 解析: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] YAML 解析: FAIL - {exc}")

    # 测试 4: 密钥脱敏
    try:
        masked = mask_api_key("sk-ant-a1b2c3d4e5f6g7h8i9j0")
        assert "***" in masked, "脱敏后应包含 ***"
        assert len(masked) < len("sk-ant-a1b2c3d4e5f6g7h8i9j0"), "脱敏后应更短"
        print("[SELFTEST] 密钥脱敏: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 密钥脱敏: FAIL - {exc}")

    # 测试 5: 负载均衡选择
    try:
        config = parse_config(SAMPLE_CONFIG_JSON, "json")
        accounts = normalize_accounts(config["accounts"])
        selected = select_account(accounts, "round_robin", 0)
        assert selected["name"] == "account-a", "轮询第一个应为 account-a"
        selected = select_account(accounts, "round_robin", 3)
        assert selected["name"] == "account-b", "权重轮询第 4 次应为 account-b"
        print("[SELFTEST] 负载均衡: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 负载均衡: FAIL - {exc}")

    # 测试 6: 空输入处理
    try:
        try:
            parse_config("", "json")
            failures += 1
            print("[SELFTEST] 空输入: FAIL - 未抛出异常")
        except ValueError as exc:
            assert "E001" in str(exc), f"错误码应为 E001，实际: {exc}"
            print("[SELFTEST] 空输入: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 空输入: FAIL - {exc}")

    # 测试 7: 中文标点输入（含中文注释的配置）
    try:
        chinese_config = """
        {
          "accounts": [
            {
              "name": "测试账户",
              "api_key": "sk-ant-abcdefgh12345678",
              "endpoint": "https://api.grok.example.com/v1",
              "weight": 2
            }
          ],
          "strategy": "random",
          "timeout": 15
        }
        """
        config = parse_config(chinese_config, "json")
        assert config["accounts"][0]["name"] == "测试账户", "中文账户名解析错误"
        print("[SELFTEST] 中文标点/中文内容: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 中文标点/中文内容: FAIL - {exc}")

    # 测试 8: 超长输入（性能验证 O(n)）
    try:
        long_text = "\n".join(
            f"account-{i}|sk-ant-abcdefgh{i:08d}|https://api.grok.example.com/v{i % 3 + 1}|{i % 5 + 1}"
            for i in range(1000)
        )
        config = parse_config(long_text, "text")
        assert len(config["accounts"]) == 1000, "超长输入解析账户数错误"
        print("[SELFTEST] 超长输入 (1000 账户): PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 超长输入: FAIL - {exc}")

    # 测试 9: 完整流程（配置生成 + 输出格式化）
    try:
        config = parse_config(SAMPLE_CONFIG_JSON, "json")
        result = build_gateway_config(config, counter=0)
        output = format_output(result, verbose=True)
        assert "Grok API 网关配置" in output, "输出缺少标题"
        assert "account-a" in output, "输出缺少账户名"
        assert "***" in output, "输出缺少脱敏密钥"
        print("[SELFTEST] 完整流程: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 完整流程: FAIL - {exc}")

    # 测试 10: 非法密钥检测
    try:
        bad_config = '{"accounts": [{"name": "bad", "api_key": "short", "endpoint": "https://x.com"}]}'
        try:
            normalize_accounts(parse_config(bad_config, "json")["accounts"])
            failures += 1
            print("[SELFTEST] 非法密钥: FAIL - 未抛出异常")
        except ValueError as exc:
            assert "E008" in str(exc), f"错误码应为 E008，实际: {exc}"
            print("[SELFTEST] 非法密钥: PASS")
    except Exception as exc:
        failures += 1
        print(f"[SELFTEST] 非法密钥: FAIL - {exc}")

    # 汇总
    if failures == 0:
        print("[SELFTEST] 全部通过 (10/10)")
        return 0
    print(f"[SELFTEST] 失败 {failures}/10")
    return 1


# ============================================================
# 主流程（CLI 入口）
# ============================================================
def process_input(raw_text: str, fmt: str, strategy: str, counter: int, verbose: bool) -> str:
    """处理输入文本，返回格式化输出。"""
    try:
        config = parse_config(raw_text, fmt)
        if strategy:
            config["strategy"] = strategy
        result = build_gateway_config(config, counter)
        return format_output(result, verbose)
    except ValueError as exc:
        # 逻辑错误：返回错误信息（不崩溃）
        print(f"[警告] 处理失败: {exc}", file=sys.stderr)
        return f"错误: {exc}"


def process_file(filepath: str, fmt: str, strategy: str, counter: int, verbose: bool) -> str:
    """处理文件输入，返回格式化输出。"""
    try:
        content = read_file_with_encoding(filepath)
        return process_input(content, fmt, strategy, counter, verbose)
    except ValueError as exc:
        print(f"[警告] 文件处理失败: {exc}", file=sys.stderr)
        return f"错误: {exc}"


def main() -> int:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        description="Grok API 网关配置工具 - 多账户负载均衡与密钥管理",
        epilog="示例: python main.py --file config.json --format json --strategy round_robin --dry-run",
    )
    parser.add_argument("--file", type=str, help="配置文件路径（支持 JSON/YAML/文本格式）")
    parser.add_argument("--text", type=str, help="直接传入配置文本")
    parser.add_argument("--format", type=str, choices=["auto", "json", "yaml", "text"], default="auto",
                        help="配置格式（默认自动检测）")
    parser.add_argument("--strategy", type=str, choices=["round_robin", "random", "least_conn"],
                        help="负载均衡策略（覆盖配置中的策略）")
    parser.add_argument("--counter", type=int, default=0, help="轮询计数器（用于 round_robin）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式：只输出结果，不写盘")
    parser.add_argument("--force", action="store_true", help="强制模式：配合 --output 真正写盘")
    parser.add_argument("--output", type=str, help="输出文件路径（需配合 --force 使用）")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策说明")
    parser.add_argument("--selftest", action="store_true", help="运行内置离线自检")
    args = parser.parse_args()
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 输入校验（guard clause）
    if not args.file and not args.text:
        print("E001: 请提供输入，使用 --file 或 --text 参数", file=sys.stderr)
        return 1

    # 处理输入
    if args.file:
        # 校验路径
        try:
            safe_path = validate_output_path(args.file)
        except ValueError as exc:
            print(f"[警告] {exc}", file=sys.stderr)
            return 1
        output = process_file(safe_path, args.format, args.strategy, args.counter, args.verbose)
    else:
        output = process_input(args.text, args.format, args.strategy, args.counter, args.verbose)

    # 输出处理
    if args.output:
        try:
            safe_out = validate_output_path(args.output)
        except ValueError as exc:
            print(f"[警告] {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            # 预览模式：打印 diff 摘要
            print("--- 预览模式（--dry-run），不写盘 ---")
            print(f"目标文件: {safe_out}")
            print("--- 输出内容预览 ---")
            print(output)
            print("--- 预览结束 ---")
        elif args.force:
            try:
                write_file_with_encoding(safe_out, output)
                print(f"已写入: {safe_out}")
            except ValueError as exc:
                print(f"[警告] {exc}", file=sys.stderr)
                return 1
        else:
            print("提示: 使用 --force 才能真正写盘，当前为预览模式", file=sys.stderr)
            print("--- 输出内容预览 ---")
            print(output)
            print("--- 预览结束 ---")
    else:
        # 无输出文件，直接打印到 stdout
        print(output)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[中断] 用户取消操作", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        # 未知异常：上报完整信息
        import traceback
        print(f"E010: 未知异常 - {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("建议: 请检查输入格式，或使用 --selftest 验证环境", file=sys.stderr)
        sys.exit(1)
