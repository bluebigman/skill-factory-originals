#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
world-of-m365 — M365 运维自动化 脚本工具箱

本脚本为 clean-room 独立实现，仅依据功能规格编写。
提供基础的数据解析、字段识别、脚本骨架生成与批量处理能力。
"""

import argparse
import csv
import io
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# 错误码定义
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"      # 输入数据格式无效
ERR_MISSING_FIELD = "E002"      # 缺少必要字段
ERR_FILE_NOT_FOUND = "E003"     # 文件不存在
ERR_URL_INVALID = "E004"        # URL 格式无效
ERR_OUTPUT_FAILED = "E005"      # 输出失败
ERR_UNSUPPORTED_FORMAT = "E006" # 不支持的格式
ERR_INTERNAL = "E007"           # 内部错误
ERR_SELFTEST_FAILED = "E008"    # 自检失败
ERR_EMPTY_DATA = "E009"         # 数据为空
ERR_BATCH_FAILED = "E010"       # 批处理失败

# 关键字段识别模式（宽松匹配）
FIELD_PATTERNS = {
    "tenant": [r"tenant", r"租户", r"组织"],
    "user": [r"user", r"用户", r"账号"],
    "group": [r"group", r"组"],
    "license": [r"license", r"许可证", r"许可"],
    "email": [r"email", r"邮箱", r"mail"],
    "display_name": [r"display.?name", r"显示名"],
}


def _identify_field(header: str) -> str:
    """根据表头识别字段类别，返回标准字段名。"""
    header_lower = header.lower().strip()
    for field, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, header_lower):
                return field
    # 未匹配时返回原始表头的小写形式
    return header_lower


def parse_csv_data(content: str) -> List[Dict[str, Any]]:
    """解析 CSV 字符串为结构化字典列表。"""
    if not content or not content.strip():
        raise ValueError(ERR_EMPTY_DATA)
    try:
        reader = csv.DictReader(io.StringIO(content))
        # 标准化字段名
        rows = []
        for raw_row in reader:
            if raw_row is None:
                continue
            standardized = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                std_key = _identify_field(key)
                standardized[std_key] = value.strip() if value else ""
            rows.append(standardized)
        if not rows:
            raise ValueError(ERR_EMPTY_DATA)
        return rows
    except csv.Error as exc:
        raise ValueError(ERR_INVALID_INPUT) from exc


def parse_json_data(content: str) -> List[Dict[str, Any]]:
    """解析 JSON 字符串为结构化字典列表。"""
    if not content or not content.strip():
        raise ValueError(ERR_EMPTY_DATA)
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            # 尝试提取常见列表字段
            for key in ["users", "items", "data", "records", "value"]:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]
        if not isinstance(data, list):
            raise ValueError(ERR_INVALID_INPUT)
        # 标准化字段名
        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            standardized = {}
            for key, value in item.items():
                if value is None:
                    value = ""
                std_key = _identify_field(str(key))
                standardized[std_key] = str(value).strip()
            rows.append(standardized)
        if not rows:
            raise ValueError(ERR_EMPTY_DATA)
        return rows
    except json.JSONDecodeError as exc:
        raise ValueError(ERR_INVALID_INPUT) from exc


def parse_url_data(url: str) -> List[Dict[str, Any]]:
    """解析 URL 中的查询参数为结构化数据（离线模式仅解析参数）。"""
    if not url or not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValueError(ERR_URL_INVALID)
    # 提取查询参数
    query_start = url.find("?")
    if query_start == -1:
        raise ValueError(ERR_EMPTY_DATA)
    query_str = url[query_start + 1:]
    params = {}
    for pair in query_str.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[key] = value
    if not params:
        raise ValueError(ERR_EMPTY_DATA)
    return [params]


def parse_input(data: str, data_type: str = "csv") -> List[Dict[str, Any]]:
    """根据数据类型解析输入内容。"""
    data_type = data_type.lower()
    if data_type == "csv":
        return parse_csv_data(data)
    elif data_type == "json":
        return parse_json_data(data)
    elif data_type == "url":
        return parse_url_data(data)
    else:
        raise ValueError(ERR_UNSUPPORTED_FORMAT)


def generate_powershell_script(rows: List[Dict[str, Any]], action: str = "list") -> str:
    """根据结构化数据生成 PowerShell 脚本骨架。"""
    if not rows:
        raise ValueError(ERR_EMPTY_DATA)

    lines = [
        "# 由 world-of-m365 生成的 PowerShell 脚本骨架",
        "# 请人工审核后再执行",
        "",
        "$ErrorActionPreference = 'Stop'",
        "",
        "# 配置区",
        "Connect-MgGraph -Scopes 'User.Read.All', 'Group.Read.All'",
        "",
    ]

    if action == "list":
        lines.append("# 列出用户/组信息")
        for idx, row in enumerate(rows[:5], 1):
            user = row.get("user", "")
            group = row.get("group", "")
            if user:
                lines.append(f"# 用户 {idx}: {user}")
                lines.append(f"Get-MgUser -UserId '{user}' | Select-Object Id, DisplayName, Mail")
            elif group:
                lines.append(f"# 组 {idx}: {group}")
                lines.append(f"Get-MgGroup -GroupId '{group}' | Select-Object Id, DisplayName")
    elif action == "assign_license":
        lines.append("# 分配许可证")
        for idx, row in enumerate(rows[:5], 1):
            user = row.get("user", "")
            license_name = row.get("license", "")
            if user and license_name:
                lines.append(f"# 为用户 {user} 分配许可证 {license_name}")
                lines.append(
                    f"Set-MgUserLicense -UserId '{user}' "
                    f"-AddLicenses @({{SkuId = '{license_name}'}}) -RemoveLicenses @()"
                )
    else:
        lines.append(f"# 未知操作: {action}")

    lines.append("")
    lines.append("Write-Host '脚本执行完成（骨架）'")
    return "\n".join(lines)


def generate_cli_script(rows: List[Dict[str, Any]], action: str = "list") -> str:
    """根据结构化数据生成 Azure CLI 脚本骨架。"""
    if not rows:
        raise ValueError(ERR_EMPTY_DATA)

    lines = [
        "#!/bin/bash",
        "# 由 world-of-m365 生成的 Azure CLI 脚本骨架",
        "# 请人工审核后再执行",
        "",
        "set -e",
        "",
    ]

    if action == "list":
        lines.append("# 列出用户/组信息")
        for idx, row in enumerate(rows[:5], 1):
            user = row.get("user", "")
            if user:
                lines.append(f"# 用户 {idx}: {user}")
                lines.append(f"az ad user show --id '{user}' --query '[id, displayName, mail]'")
    elif action == "assign_license":
        lines.append("# 分配许可证")
        for idx, row in enumerate(rows[:5], 1):
            user = row.get("user", "")
            license_name = row.get("license", "")
            if user and license_name:
                lines.append(f"# 为用户 {user} 分配许可证 {license_name}")
                lines.append(
                    f"az user update --id '{user}' --licenses '[{{\"skuId\": \"{license_name}\"}}]'"
                )
    else:
        lines.append(f"# 未知操作: {action}")

    lines.append("")
    lines.append("echo '脚本执行完成（骨架）'")
    return "\n".join(lines)


def generate_script(rows: List[Dict[str, Any]], script_type: str = "powershell", action: str = "list") -> str:
    """生成指定类型的脚本骨架。"""
    if script_type.lower() == "powershell":
        return generate_powershell_script(rows, action)
    elif script_type.lower() in ("cli", "bash", "az"):
        return generate_cli_script(rows, action)
    else:
        raise ValueError(ERR_UNSUPPORTED_FORMAT)


def format_output(data: List[Dict[str, Any]], output_format: str = "json") -> str:
    """将结构化数据格式化为指定输出格式。"""
    if output_format.lower() == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format.lower() == "csv":
        if not data:
            return ""
        output = io.StringIO()
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    elif output_format.lower() == "markdown":
        if not data:
            return ""
        lines = []
        headers = list(data[0].keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "---|" * len(headers))
        for row in data:
            values = [str(row.get(h, "")) for h in headers]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)
    else:
        raise ValueError(ERR_UNSUPPORTED_FORMAT)


def batch_process(rows: List[Dict[str, Any]], batch_size: int = 10) -> List[List[Dict[str, Any]]]:
    """将数据分批处理。"""
    if not rows:
        raise ValueError(ERR_EMPTY_DATA)
    if batch_size <= 0:
        raise ValueError(ERR_INVALID_INPUT)
    return [rows[i:i + batch_size] for i in range(0, len(rows), batch_size)]


def extract_key_fields(rows: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """提取关键字段（租户、用户、组、许可证等）的汇总信息。"""
    result = {
        "tenant": [],
        "user": [],
        "group": [],
        "license": [],
        "email": [],
        "display_name": [],
    }
    for row in rows:
        for field in result.keys():
            value = row.get(field, "")
            if value and value not in result[field]:
                result[field].append(value)
    return result


def run_selftest() -> bool:
    """内置硬编码样例数据自检核心逻辑，不依赖外部环境。"""
    try:
        # 测试数据 1: CSV 样例
        csv_sample = """User,Group,License,Email
alice@contoso.com,TeamA,ENTERPRISEPACK,alice@contoso.com
bob@contoso.com,TeamB,ENTERPRISEPACK,bob@contoso.com
carol@contoso.com,TeamA,O365_BUSINESS,carol@contoso.com"""

        rows = parse_csv_data(csv_sample)
        assert len(rows) >= 2, "CSV 解析行数不足"
        assert any("user" in row for row in rows), "缺少用户字段"

        # 测试 JSON 解析
        json_sample = json.dumps([
            {"tenant": "contoso.onmicrosoft.com", "user": "admin@contoso.com"},
            {"tenant": "fabrikam.onmicrosoft.com", "user": "admin@fabrikam.com"},
        ])
        json_rows = parse_json_data(json_sample)
        assert len(json_rows) >= 1, "JSON 解析失败"

        # 测试 URL 解析
        url_sample = "https://graph.microsoft.com/users?tenant=contoso&role=admin&page=1"
        url_rows = parse_url_data(url_sample)
        assert len(url_rows) >= 1, "URL 解析失败"

        # 测试脚本生成
        ps_script = generate_powershell_script(rows, "list")
        assert "Connect-MgGraph" in ps_script, "PowerShell 脚本缺少连接命令"
        assert len(ps_script) > 100, "PowerShell 脚本过短"

        cli_script = generate_cli_script(rows, "list")
        assert "az ad user" in cli_script, "CLI 脚本缺少命令"

        # 测试输出格式
        json_out = format_output(rows, "json")
        assert json_out.startswith("["), "JSON 输出格式错误"
        csv_out = format_output(rows, "csv")
        assert "User" in csv_out or "user" in csv_out, "CSV 输出缺少表头"
        md_out = format_output(rows, "markdown")
        assert "|" in md_out, "Markdown 输出缺少表格"

        # 测试批处理
        batches = batch_process(rows, 2)
        assert len(batches) >= 1, "批处理失败"

        # 测试字段提取
        fields = extract_key_fields(rows)
        assert len(fields["user"]) >= 2, "用户字段提取不足"
        assert len(fields["license"]) >= 1, "许可证字段提取不足"

        # 宽松阈值断言：只要结果非空且数量合理即可
        assert len(fields["user"]) <= len(rows), "用户数量不合理"
        assert len(fields["license"]) <= len(rows), "许可证数量不合理"

        return True
    except (AssertionError, ValueError, KeyError, TypeError):
        return False


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="world-of-m365 — M365 运维自动化 脚本工具箱"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码数据，不依赖外部环境）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（文件路径或直接内容）",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["csv", "json", "url"],
        default="csv",
        help="输入数据类型",
    )
    parser.add_argument(
        "--script",
        type=str,
        choices=["powershell", "cli"],
        default="powershell",
        help="生成的脚本类型",
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["list", "assign_license"],
        default="list",
        help="脚本动作",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=0,
        help="批处理大小（0 表示不批处理）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        if ok:
            print("✅ 自检通过：核心逻辑验证成功")
            return ERR_SUCCESS
        else:
            print("❌ 自检失败：核心逻辑验证未通过")
            return ERR_SELFTEST_FAILED

    # 正常处理模式
    try:
        # 读取输入
        if args.input:
            input_path = Path(args.input)
            if input_path.exists() and input_path.is_file():
                # 从文件读取
                with open(input_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                # 视为直接内容
                content = args.input
        else:
            # 从标准输入读取
            content = sys.stdin.read()

        if not content or not content.strip():
            print(f"错误 {ERR_EMPTY_DATA}: 输入数据为空", file=sys.stderr)
            return ERR_EMPTY_DATA

        # 解析数据
        try:
            rows = parse_input(content, args.type)
        except ValueError as exc:
            print(f"错误 {exc}: 数据解析失败", file=sys.stderr)
            return ERR_INVALID_INPUT

        # 批处理
        if args.batch > 0:
            batches = batch_process(rows, args.batch)
            for idx, batch in enumerate(batches, 1):
                print(f"--- 批次 {idx}/{len(batches)} ---")
                print(format_output(batch, args.output))
        else:
            # 生成脚本
            if args.script:
                script_content = generate_script(rows, args.script, args.action)
                print(script_content)
            else:
                # 输出结构化数据
                print(format_output(rows, args.output))

        return ERR_SUCCESS

    except ValueError as exc:
        print(f"错误 {exc}: 处理失败", file=sys.stderr)
        return ERR_INVALID_INPUT
    except FileNotFoundError as exc:
        print(f"错误 {ERR_FILE_NOT_FOUND}: 文件不存在 {exc}", file=sys.stderr)
        return ERR_FILE_NOT_FOUND
    except Exception as exc:
        print(f"错误 {ERR_INTERNAL}: 内部错误 {exc}", file=sys.stderr)
        return ERR_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
