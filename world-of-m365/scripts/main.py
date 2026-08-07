#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
world-of-m365 — M365 运维自动化 脚本工具箱

本脚本为独立实现（clean-room implementation），仅依据功能规格文档编写，
不包含任何既有代码。提供 M365 运维相关的数据解析、字段识别、
脚本骨架生成与批量处理等核心能力。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或格式无效",
    "E002": "无法解析输入数据（CSV/JSON/URL）",
    "E003": "输入数据缺少必要的关键字段",
    "E004": "不支持的目标格式（仅支持 markdown/json/csv）",
    "E005": "批量处理失败：某条记录处理出错",
    "E006": "输入数据不是结构化的表格或 JSON 数组",
    "E007": "字段识别失败：无法识别租户/用户/组/许可证字段",
    "E008": "脚本骨架生成失败：目标类型不支持",
    "E009": "输出格式转换失败",
    "E010": "内部逻辑错误（未知异常）",
}


class M365ToolError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心工具函数
# ============================================================

def _is_non_empty_string(value: Any) -> bool:
    """判断是否为非空字符串。"""
    return isinstance(value, str) and value.strip() != ""


def _safe_strip(value: Any) -> str:
    """安全去除字符串首尾空白。"""
    if value is None:
        return ""
    return str(value).strip()


def _looks_like_email(value: str) -> bool:
    """粗略判断是否为邮箱地址。"""
    return "@" in value and "." in value.split("@")[-1]


def _looks_like_tenant_id(value: str) -> bool:
    """粗略判断是否为租户 ID（GUID 或域名形式）。"""
    # GUID 形式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    guid_pattern = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    if guid_pattern.match(value):
        return True
    # 域名形式: xxx.onmicrosoft.com 或 xxx.com
    if "." in value and not value.startswith("@"):
        return True
    return False


def _looks_like_upn(value: str) -> bool:
    """判断是否为用户主体名称（UPN，即用户邮箱）。"""
    return _looks_like_email(value)


def _looks_like_group_name(value: str) -> bool:
    """粗略判断是否为组名（不含 @ 的非空字符串）。"""
    return _is_non_empty_string(value) and "@" not in value


# ============================================================
# 数据解析模块
# ============================================================

class DataParser:
    """将 CSV / JSON / URL 内容解析为结构化数据。"""

    @staticmethod
    def parse_csv(text: str) -> List[Dict[str, str]]:
        """解析 CSV 文本为字典列表。"""
        if not _is_non_empty_string(text):
            raise M365ToolError("E001")
        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = [dict(row) for row in reader if any(row.values())]
        except Exception as exc:
            raise M365ToolError("E002", f"CSV 解析失败: {exc}") from exc

        if not rows:
            raise M365ToolError("E002", "CSV 无数据行")
        return rows

    @staticmethod
    def parse_json(text: str) -> List[Dict[str, Any]]:
        """解析 JSON 文本为对象列表。"""
        if not _is_non_empty_string(text):
            raise M365ToolError("E001")
        try:
            data = json.loads(text)
        except Exception as exc:
            raise M365ToolError("E002", f"JSON 解析失败: {exc}") from exc

        # 支持单对象或对象数组
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            return data
        raise M365ToolError("E006", "JSON 必须是对象或对象数组")

    @staticmethod
    def parse_url_like(text: str) -> List[Dict[str, str]]:
        """尝试从 URL 查询参数中提取字段（仅本地解析，不访问网络）。"""
        if not _is_non_empty_string(text):
            raise M365ToolError("E001")
        # 提取查询字符串部分
        query = text
        if "?" in text:
            query = text.split("?", 1)[1]
        params = {}
        for pair in query.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k.strip()] = v.strip()
        if params:
            return [params]
        raise M365ToolError("E002", "URL 中未找到查询参数")

    @classmethod
    def parse_auto(cls, text: str) -> List[Dict[str, Any]]:
        """自动识别输入类型并解析为结构化字典列表。"""
        if not _is_non_empty_string(text):
            raise M365ToolError("E001")

        stripped = text.strip()
        # 优先尝试 JSON
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return cls.parse_json(stripped)
            except M365ToolError:
                pass  # 继续尝试其他格式

        # 尝试 CSV
        if "," in stripped or "\t" in stripped:
            try:
                return cls.parse_csv(stripped)
            except M365ToolError:
                pass

        # 尝试 URL 查询参数
        if stripped.startswith("http") or "=" in stripped:
            try:
                return cls.parse_url_like(stripped)
            except M365ToolError:
                pass

        raise M365ToolError("E002", "无法自动识别输入格式")


# ============================================================
# 字段识别模块
# ============================================================

class FieldIdentifier:
    """识别数据中的租户、用户、组、许可证等关键字段。"""

    # 常见字段名映射（宽松匹配）
    TENANT_KEYS = ["tenant", "tenantid", "tenant_id", "租户", "租户id", "租户名称"]
    USER_KEYS = ["user", "userprincipalname", "upn", "username", "用户", "用户主体名称", "邮箱", "email"]
    GROUP_KEYS = ["group", "groupname", "group_name", "组", "组名", "组名称"]
    LICENSE_KEYS = ["license", "licensename", "license_name", "许可证", "许可", "sku"]

    @classmethod
    def _find_key(cls, row: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        """在字典中查找第一个匹配的键（不区分大小写）。"""
        row_lower = {str(k).lower(): k for k in row.keys()}
        for candidate in candidates:
            if candidate.lower() in row_lower:
                return row_lower[candidate.lower()]
        # 也检查原始键
        for key in row.keys():
            key_str = str(key).lower()
            for candidate in candidates:
                if candidate.lower() == key_str:
                    return key
        return None

    @classmethod
    def identify(cls, row: Dict[str, Any]) -> Dict[str, str]:
        """识别单行数据中的关键字段。"""
        result: Dict[str, str] = {}

        tenant_key = cls._find_key(row, cls.TENANT_KEYS)
        user_key = cls._find_key(row, cls.USER_KEYS)
        group_key = cls._find_key(row, cls.GROUP_KEYS)
        license_key = cls._find_key(row, cls.LICENSE_KEYS)

        if tenant_key:
            result["tenant"] = _safe_strip(row[tenant_key])
        if user_key:
            result["user"] = _safe_strip(row[user_key])
        if group_key:
            result["group"] = _safe_strip(row[group_key])
        if license_key:
            result["license"] = _safe_strip(row[license_key])

        # 如果未通过键名识别，尝试值内容识别
        if not result:
            for key, value in row.items():
                val_str = _safe_strip(value)
                if not val_str:
                    continue
                if _looks_like_tenant_id(val_str) and "tenant" not in result:
                    result["tenant"] = val_str
                elif _looks_like_upn(val_str) and "user" not in result:
                    result["user"] = val_str
                elif _looks_like_group_name(val_str) and "group" not in result:
                    result["group"] = val_str

        if not result:
            raise M365ToolError("E007", "无法识别任何关键字段")

        return result


# ============================================================
# 脚本骨架生成模块
# ============================================================

class ScriptGenerator:
    """生成 PowerShell / CLI 脚本骨架。"""

    @staticmethod
    def generate_powershell(operations: List[Dict[str, str]], script_type: str = "inspect") -> str:
        """生成 PowerShell 脚本骨架。"""
        if not operations:
            raise M365ToolError("E001")

        lines: List[str] = []
        lines.append("# 由 world-of-m365 自动生成的 PowerShell 脚本骨架")
        lines.append("# 请人工审核后再执行")
        lines.append("")
        lines.append("$ErrorActionPreference = 'Stop'")
        lines.append("")

        for idx, op in enumerate(operations, start=1):
            tenant = op.get("tenant", "")
            user = op.get("user", "")
            group = op.get("group", "")
            license_name = op.get("license", "")

            lines.append(f"# ---- 操作 {idx} ----")
            if user:
                lines.append(f"# 目标用户: {user}")
                lines.append(f"Get-MgUser -Filter \"UserPrincipalName eq '{user}'\"")
            if group:
                lines.append(f"# 目标组: {group}")
                lines.append(f"Get-MgGroup -Filter \"DisplayName eq '{group}'\"")
            if tenant:
                lines.append(f"# 目标租户: {tenant}")
            if license_name:
                lines.append(f"# 许可证: {license_name}")
            lines.append("")

        # 根据类型追加额外指令
        if script_type == "assign_license":
            lines.append("# 分配许可证示例（需人工确认 SKU ID）")
            lines.append("# Set-MgUserLicense -UserId '<user>' -AddLicenses @{SkuId='<sku-id>'} -RemoveLicenses @()")
        elif script_type == "add_user_to_group":
            lines.append("# 添加用户到组示例")
            lines.append("# Add-MgGroupMember -GroupId '<group-id>' -DirectoryObjectId '<user-id>'")
        elif script_type == "remove_user":
            lines.append("# 移除用户示例（危险操作，请谨慎）")
            lines.append("# Remove-MgUser -UserId '<user-id>'")

        lines.append("")
        lines.append("Write-Host '脚本骨架生成完毕，请审核后手动执行。'")
        return "\n".join(lines)

    @staticmethod
    def generate_azure_cli(operations: List[Dict[str, str]], script_type: str = "inspect") -> str:
        """生成 Azure CLI 脚本骨架。"""
        if not operations:
            raise M365ToolError("E001")

        lines: List[str] = []
        lines.append("# 由 world-of-m365 自动生成的 Azure CLI 脚本骨架")
        lines.append("# 请人工审核后再执行")
        lines.append("")

        for idx, op in enumerate(operations, start=1):
            tenant = op.get("tenant", "")
            user = op.get("user", "")
            group = op.get("group", "")

            lines.append(f"# ---- 操作 {idx} ----")
            if user:
                lines.append(f"# 目标用户: {user}")
                lines.append(f"az ad user show --id '{user}'")
            if group:
                lines.append(f"# 目标组: {group}")
                lines.append(f"az ad group show --group '{group}'")
            if tenant:
                lines.append(f"# 目标租户: {tenant}")
            lines.append("")

        if script_type == "assign_license":
            lines.append("# 分配许可证示例")
            lines.append("# az ad user update --id '<user>' --licenses '[{\"skuId\":\"<sku-id>\"}]'")
        elif script_type == "add_user_to_group":
            lines.append("# 添加用户到组示例")
            lines.append("# az ad group member add --group '<group>' --member-id '<user-id>'")
        elif script_type == "remove_user":
            lines.append("# 移除用户示例（危险操作，请谨慎）")
            lines.append("# az ad user delete --id '<user>'")

        lines.append("")
        lines.append("echo '脚本骨架生成完毕，请审核后手动执行。'")
        return "\n".join(lines)


# ============================================================
# 输出格式化模块
# ============================================================

class OutputFormatter:
    """将结构化数据输出为 Markdown / JSON / CSV。"""

    @staticmethod
    def to_markdown(data: List[Dict[str, Any]]) -> str:
        """转换为 Markdown 表格。"""
        if not data:
            raise M365ToolError("E001")
        headers = list(data[0].keys())
        lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in data:
            values = [str(row.get(h, "")) for h in headers]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    @staticmethod
    def to_json(data: List[Dict[str, Any]]) -> str:
        """转换为 JSON 字符串。"""
        if not data:
            raise M365ToolError("E001")
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise M365ToolError("E009", f"JSON 序列化失败: {exc}") from exc

    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        """转换为 CSV 字符串。"""
        if not data:
            raise M365ToolError("E001")
        try:
            output = io.StringIO()
            headers = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()
        except Exception as exc:
            raise M365ToolError("E009", f"CSV 序列化失败: {exc}") from exc

    @classmethod
    def format(cls, data: List[Dict[str, Any]], output_format: str) -> str:
        """按指定格式输出。"""
        fmt = output_format.lower()
        if fmt in ("md", "markdown"):
            return cls.to_markdown(data)
        if fmt == "json":
            return cls.to_json(data)
        if fmt == "csv":
            return cls.to_csv(data)
        raise M365ToolError("E004", f"不支持的目标格式: {output_format}")


# ============================================================
# 批处理模块
# ============================================================

class BatchProcessor:
    """批量处理同类输入。"""

    @staticmethod
    def process(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量识别字段并返回结构化结果。"""
        results: List[Dict[str, Any]] = []
        for idx, row in enumerate(data, start=1):
            try:
                identified = FieldIdentifier.identify(row)
                results.append({"index": idx, **identified})
            except M365ToolError as exc:
                raise M365ToolError("E005", f"第 {idx} 条记录处理失败: {exc}") from exc
        return results


# ============================================================
# 主流程封装
# ============================================================

class M365Tool:
    """M365 运维自动化核心工具类。"""

    def __init__(self, input_text: str, output_format: str = "json", script_type: str = "inspect"):
        self.input_text = input_text
        self.output_format = output_format
        self.script_type = script_type

    def run_parse(self) -> List[Dict[str, Any]]:
        """解析输入数据。"""
        return DataParser.parse_auto(self.input_text)

    def run_identify(self) -> List[Dict[str, Any]]:
        """解析并识别关键字段。"""
        parsed = self.run_parse()
        return BatchProcessor.process(parsed)

    def run_generate(self, target: str = "powershell") -> str:
        """解析、识别并生成脚本骨架。"""
        identified = self.run_identify()
        if target.lower() in ("ps", "powershell"):
            return ScriptGenerator.generate_powershell(identified, self.script_type)
        if target.lower() in ("cli", "az", "azure"):
            return ScriptGenerator.generate_azure_cli(identified, self.script_type)
        raise M365ToolError("E008", f"不支持的脚本目标: {target}")

    def run_format(self) -> str:
        """解析、识别并格式化输出。"""
        identified = self.run_identify()
        return OutputFormatter.format(identified, self.output_format)


# ============================================================
# 自检模块（离线、硬编码样例）
# ============================================================

def run_selftest() -> int:
    """内置硬编码样例数据，离线自检核心逻辑。"""
    print("正在运行自检（selftest）...")

    # ---- 测试 1: CSV 解析与字段识别 ----
    csv_data = """tenant,user,group,license
contoso.onmicrosoft.com,alice@contoso.com,Sales,Microsoft365_E5
fabrikam.com,bob@fabrikam.com,Marketing,Microsoft365_E3
"""
    try:
        parsed = DataParser.parse_csv(csv_data)
        assert len(parsed) == 2, "CSV 应解析出 2 行数据"
        assert "tenant" in parsed[0], "CSV 应包含 tenant 字段"
        assert "user" in parsed[0], "CSV 应包含 user 字段"
        print("  [OK] CSV 解析")
    except AssertionError as exc:
        print(f"  [FAIL] CSV 解析: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] CSV 解析异常: {exc}")
        return 1

    # ---- 测试 2: JSON 解析 ----
    json_data = """[
        {"tenant": "contoso.onmicrosoft.com", "user": "carol@contoso.com"},
        {"tenant": "fabrikam.com", "user": "dave@fabrikam.com"}
    ]"""
    try:
        parsed_json = DataParser.parse_json(json_data)
        assert len(parsed_json) == 2, "JSON 应解析出 2 条记录"
        assert parsed_json[0]["user"] == "carol@contoso.com", "JSON 用户字段不正确"
        print("  [OK] JSON 解析")
    except AssertionError as exc:
        print(f"  [FAIL] JSON 解析: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] JSON 解析异常: {exc}")
        return 1

    # ---- 测试 3: 自动识别解析 ----
    try:
        parsed_auto = DataParser.parse_auto(csv_data)
        assert len(parsed_auto) == 2, "自动识别应解析出 2 条记录"
        print("  [OK] 自动识别解析")
    except AssertionError as exc:
        print(f"  [FAIL] 自动识别解析: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] 自动识别解析异常: {exc}")
        return 1

    # ---- 测试 4: 字段识别 ----
    try:
        row = {"tenant": "contoso.onmicrosoft.com", "user": "alice@contoso.com", "group": "Sales"}
        identified = FieldIdentifier.identify(row)
        assert identified.get("tenant") == "contoso.onmicrosoft.com", "租户识别失败"
        assert identified.get("user") == "alice@contoso.com", "用户识别失败"
        assert identified.get("group") == "Sales", "组识别失败"
        print("  [OK] 字段识别")
    except AssertionError as exc:
        print(f"  [FAIL] 字段识别: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] 字段识别异常: {exc}")
        return 1

    # ---- 测试 5: 批量处理 ----
    try:
        batch = BatchProcessor.process(parsed)
        assert len(batch) == 2, "批量处理应返回 2 条结果"
        assert batch[0]["index"] == 1, "批量处理索引错误"
        assert batch[0]["user"] == "alice@contoso.com", "批量处理用户识别错误"
        print("  [OK] 批量处理")
    except AssertionError as exc:
        print(f"  [FAIL] 批量处理: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] 批量处理异常: {exc}")
        return 1

    # ---- 测试 6: 脚本骨架生成 ----
    try:
        ps_script = ScriptGenerator.generate_powershell(parsed)
        assert "Get-MgUser" in ps_script, "PowerShell 脚本应包含 Get-MgUser"
        assert "alice@contoso.com" in ps_script, "PowerShell 脚本应包含用户邮箱"
        cli_script = ScriptGenerator.generate_azure_cli(parsed)
        assert "az ad user show" in cli_script, "CLI 脚本应包含 az ad user show"
        print("  [OK] 脚本骨架生成")
    except AssertionError as exc:
        print(f"  [FAIL] 脚本骨架生成: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] 脚本骨架生成异常: {exc}")
        return 1

    # ---- 测试 7: 输出格式化 ----
    try:
        md = OutputFormatter.to_markdown(parsed)
        assert md.startswith("|"), "Markdown 输出应包含表格"
        assert "---" in md, "Markdown 输出应包含分隔行"
        json_out = OutputFormatter.to_json(parsed)
        assert json.loads(json_out), "JSON 输出应可解析"
        csv_out = OutputFormatter.to_csv(parsed)
        assert "tenant" in csv_out, "CSV 输出应包含表头"
        print("  [OK] 输出格式化")
    except AssertionError as exc:
        print(f"  [FAIL] 输出格式化: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] 输出格式化异常: {exc}")
        return 1

    # ---- 测试 8: 端到端流程 ----
    try:
        tool = M365Tool(csv_data, output_format="json")
        result = tool.run_format()
        assert "alice@contoso.com" in result, "端到端流程应包含用户信息"
        print("  [OK] 端到端流程")
    except AssertionError as exc:
        print(f"  [FAIL] 端到端流程: {exc}")
        return 1
    except M365ToolError as exc:
        print(f"  [FAIL] 端到端流程异常: {exc}")
        return 1

    # ---- 测试 9: 错误处理 ----
    try:
        DataParser.parse_csv("")
        print("  [FAIL] 空输入应抛出 E001")
        return 1
    except M365ToolError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"
        print("  [OK] 错误处理")

    # ---- 测试 10: 宽松断言（大小比较） ----
    try:
        # 验证输出长度大于某个宽松阈值
        md_output = OutputFormatter.to_markdown(parsed)
        assert len(md_output) > 50, "Markdown 输出应有一定长度"
        json_output = OutputFormatter.to_json(parsed)
        assert len(json_output) > 50, "JSON 输出应有一定长度"
        print("  [OK] 宽松断言")
    except AssertionError as exc:
        print(f"  [FAIL] 宽松断言: {exc}")
        return 1

    print("\n所有自检通过！")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="world-of-m365 — M365 运维自动化 脚本工具箱",
        epilog="示例: python main.py --input data.csv --format json --identify",
    )
    parser.add_argument(
        "--input", "-i", type=str, help="输入数据：CSV/JSON 文本或 URL 查询参数"
    )
    parser.add_argument(
        "--format", "-f", type=str, default="json", choices=["json", "csv", "markdown", "md"],
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--identify", action="store_true", help="识别关键字段并输出结构化结果"
    )
    parser.add_argument(
        "--generate", "-g", type=str, choices=["powershell", "cli"], help="生成脚本骨架"
    )
    parser.add_argument(
        "--script-type", type=str, default="inspect",
        choices=["inspect", "assign_license", "add_user_to_group", "remove_user"],
        help="脚本类型（默认: inspect）",
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行内置自检（离线）"
    )
    parser.add_argument(
        "--version", "-v", action="version", version="world-of-m365 1.0.1"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查必要参数
    if not args.input:
        parser.error("必须提供 --input 或使用 --selftest")
        return 2

    try:
        tool = M365Tool(args.input, output_format=args.format, script_type=args.script_type)

        if args.generate:
            result = tool.run_generate(target=args.generate)
            print(result)
        elif args.identify:
            result = tool.run_format()
            print(result)
        else:
            # 默认行为：解析并输出结构化结果
            result = tool.run_format()
            print(result)

        return 0

    except M365ToolError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底异常
        print(f"[E010] 内部逻辑错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
