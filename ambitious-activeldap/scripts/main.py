#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ambitious-activeldap 独立实现脚本
功能：将 ActiveLdap 查询结果转换为结构化数据，支持批量处理与置信度标注。
仅依据功能规格实现，不复制任何既有代码。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义
class AppError(Exception):
    """应用自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _err(code: str, message: str) -> AppError:
    """快捷创建错误。"""
    return AppError(code, message)


# ---------------------------
# 核心数据模型
# ---------------------------

# 常用 LDAP 属性（用于识别与保留）
COMMON_ATTRS = [
    "dn", "uid", "cn", "sn", "givenName", "mail", "objectClass",
    "ou", "department", "title", "telephoneNumber", "mobile",
    "displayName", "sAMAccountName", "userPrincipalName", "memberOf"
]

# 敏感字段（默认跳过）
SENSITIVE_FIELDS = {"userpassword", "unicodepwd", "userpkcs12"}

# 推断字段的置信度常量
CONFIDENCE_HIGH = 0.95
CONFIDENCE_MEDIUM = 0.75
CONFIDENCE_LOW = 0.50


# ---------------------------
# 工具函数
# ---------------------------

def _normalize_key(key: str) -> str:
    """将属性名转为小写并去除空白。"""
    return str(key).strip().lower()


def _safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """安全获取字典值（大小写不敏感）。"""
    if data is None:
        return default
    if key in data:
        return data[key]
    lower_key = _normalize_key(key)
    for k, v in data.items():
        if _normalize_key(k) == lower_key:
            return v
    return default


def _is_sensitive(key: str) -> bool:
    """判断是否为敏感字段。"""
    return _normalize_key(key) in SENSITIVE_FIELDS


def _parse_dn(dn: str) -> Dict[str, str]:
    """
    解析 LDAP DN 字符串，提取 RDN 键值对。
    示例: "uid=alice,ou=people,dc=example,dc=com"
    -> {"uid": "alice", "ou": "people", "dc": "example", "dc": "com"}
    注意：重复键保留最后一个（简单处理）。
    """
    result: Dict[str, str] = {}
    if not dn or not isinstance(dn, str):
        return result
    # 处理转义逗号（简单处理，不处理转义符）
    parts = dn.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, _, value = part.partition("=")
            result[_normalize_key(key)] = value.strip()
    return result


def _infer_department_from_dn(dn: str) -> Tuple[Optional[str], float]:
    """
    从 DN 推断部门信息。
    返回 (部门名, 置信度)。无法推断时返回 (None, 0.0)。
    """
    if not dn:
        return None, 0.0
    parsed = _parse_dn(dn)
    # 优先从 ou 属性推断
    ou = parsed.get("ou")
    if ou:
        return ou, CONFIDENCE_HIGH
    # 尝试从 dc 推断（作为组织）
    dc = parsed.get("dc")
    if dc:
        return dc, CONFIDENCE_MEDIUM
    return None, 0.0


def _infer_uid_from_dn(dn: str) -> Tuple[Optional[str], float]:
    """从 DN 推断 uid。"""
    if not dn:
        return None, 0.0
    parsed = _parse_dn(dn)
    uid = parsed.get("uid")
    if uid:
        return uid, CONFIDENCE_HIGH
    cn = parsed.get("cn")
    if cn:
        return cn, CONFIDENCE_MEDIUM
    return None, 0.0


# ---------------------------
# 核心处理逻辑
# ---------------------------

def process_single_entry(
    entry: Dict[str, Any],
    skip_sensitive: bool = True,
    infer_fields: bool = True
) -> Dict[str, Any]:
    """
    处理单条 LDAP 记录，转换为结构化数据。
    - 保留所有非敏感字段
    - 可选推断字段（从 dn 推导）
    - 为推断字段添加置信度标注
    """
    if not isinstance(entry, dict):
        raise _err("E001", f"输入条目必须是字典类型，实际为 {type(entry).__name__}")

    result: Dict[str, Any] = {}
    inferred: Dict[str, Dict[str, Any]] = {}

    # 1. 复制原始字段（跳过敏感字段）
    for key, value in entry.items():
        if skip_sensitive and _is_sensitive(key):
            continue
        result[key] = value

    # 2. 确保 dn 存在
    dn = _safe_get(entry, "dn", "")
    if dn:
        result.setdefault("dn", dn)

    # 3. 推断字段（如果启用）
    if infer_fields:
        # 从 dn 推断 uid
        if not _safe_get(result, "uid"):
            uid, conf = _infer_uid_from_dn(dn)
            if uid:
                inferred["uid"] = {"value": uid, "confidence": conf}

        # 从 dn 推断部门
        if not _safe_get(result, "department"):
            dept, conf = _infer_department_from_dn(dn)
            if dept:
                inferred["department"] = {"value": dept, "confidence": conf}

    # 4. 将推断字段写入结果（带置信度标记）
    for field, info in inferred.items():
        result[field] = info["value"]
        result[f"{field}_confidence"] = info["confidence"]

    return result


def process_batch(
    entries: List[Dict[str, Any]],
    skip_sensitive: bool = True,
    infer_fields: bool = True
) -> List[Dict[str, Any]]:
    """批量处理多条记录。"""
    if not isinstance(entries, list):
        raise _err("E002", f"批量输入必须是列表，实际为 {type(entries).__name__}")

    results = []
    for i, entry in enumerate(entries):
        try:
            processed = process_single_entry(entry, skip_sensitive, infer_fields)
            results.append(processed)
        except AppError as e:
            raise _err("E003", f"第 {i+1} 条记录处理失败: {e.message}") from e
    return results


def format_output(
    entries: List[Dict[str, Any]],
    template: Optional[List[str]] = None,
    separator: str = "|",
    include_confidence: bool = False
) -> str:
    """
    按模板格式化输出。
    - template: 字段顺序列表，None 表示自动选择公共字段
    - separator: 字段分隔符
    - include_confidence: 是否包含置信度列
    """
    if not entries:
        return ""

    # 自动选择公共字段（按 COMMON_ATTRS 顺序）
    if template is None:
        template = []
        for attr in COMMON_ATTRS:
            if all(_safe_get(e, attr) is not None for e in entries):
                template.append(attr)
        # 补充其他字段（按出现顺序）
        seen = set(template)
        for entry in entries:
            for key in entry.keys():
                if key not in seen and not key.endswith("_confidence"):
                    template.append(key)
                    seen.add(key)

    # 构建输出行
    lines = []
    for entry in entries:
        row = []
        for field in template:
            value = _safe_get(entry, field, "")
            # 列表值转为逗号分隔
            if isinstance(value, (list, tuple)):
                value = ",".join(str(v) for v in value)
            row.append(str(value) if value is not None else "")
            # 如果启用置信度，且当前字段有对应置信度
            if include_confidence:
                conf_key = f"{field}_confidence"
                conf_value = _safe_get(entry, conf_key, "")
                row.append(str(conf_value) if conf_value is not None else "")
        lines.append(separator.join(row))

    return "\n".join(lines)


def parse_input(data: str, format_hint: str = "auto") -> List[Dict[str, Any]]:
    """
    解析输入数据（支持 JSON、CSV、LDIF 文本）。
    - format_hint: auto/json/csv/ldif
    """
    if not data or not data.strip():
        raise _err("E004", "输入数据为空")

    format_hint = format_hint.lower()
    stripped = data.strip()

    # 自动检测
    if format_hint == "auto":
        if stripped.startswith("{"):
            format_hint = "json"
        elif stripped.startswith("dn:"):
            format_hint = "ldif"
        else:
            format_hint = "json"  # 默认尝试 JSON

    # JSON 解析
    if format_hint == "json":
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise _err("E005", f"JSON 解析失败: {e}") from e
        if isinstance(parsed, dict):
            # 单条记录
            return [parsed]
        elif isinstance(parsed, list):
            return parsed
        else:
            raise _err("E006", f"JSON 数据必须是对象或数组，实际为 {type(parsed).__name__}")

    # CSV 解析
    if format_hint == "csv":
        try:
            reader = csv.DictReader(io.StringIO(stripped))
            return [dict(row) for row in reader]
        except Exception as e:
            raise _err("E007", f"CSV 解析失败: {e}") from e

    # LDIF 解析（简化）
    if format_hint == "ldif":
        return _parse_ldif(stripped)

    raise _err("E008", f"不支持的输入格式: {format_hint}")


def _parse_ldif(text: str) -> List[Dict[str, Any]]:
    """简化 LDIF 解析（仅处理基础格式）。"""
    entries = []
    current: Dict[str, Any] = {}
    dn = ""

    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("dn:"):
            # 新记录开始
            if current:
                current["dn"] = dn
                entries.append(current)
            dn = line[3:].strip()
            current = {}
        elif line.startswith(" ") and current:
            # 续行（简化处理）
            pass
        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key:
                if key in current:
                    if not isinstance(current[key], list):
                        current[key] = [current[key]]
                    current[key].append(value)
                else:
                    current[key] = value

    # 最后一条记录
    if current:
        current["dn"] = dn
        entries.append(current)

    return entries


# ---------------------------
# 命令行入口
# ---------------------------

def _run_selftest() -> int:
    """内置硬编码样例数据自检。"""
    print("运行自检...")

    # 样例 1：单条记录处理
    sample1 = {
        "dn": "uid=alice,ou=people,dc=example,dc=com",
        "uid": "alice",
        "cn": "Alice Smith",
        "mail": "alice@example.com",
        "objectClass": ["person", "organizationalPerson"],
        "userPassword": "secret"  # 敏感字段应被跳过
    }
    result1 = process_single_entry(sample1)
    assert result1.get("uid") == "alice", "E010: uid 处理失败"
    assert "userPassword" not in result1, "E010: 敏感字段未跳过"
    assert "department" in result1, "E010: 部门推断失败"
    assert result1.get("department") == "people", "E010: 部门推断值不正确"
    assert result1.get("department_confidence", 0) > 0.9, "E010: 置信度应较高"
    print("  [PASS] 单条记录处理")

    # 样例 2：批量处理
    sample2 = [
        {"dn": "uid=bob,ou=engineering,dc=example,dc=com", "uid": "bob", "cn": "Bob"},
        {"dn": "uid=carol,ou=sales,dc=example,dc=com", "uid": "carol", "cn": "Carol"},
    ]
    result2 = process_batch(sample2)
    assert len(result2) == 2, "E010: 批量处理数量错误"
    assert result2[0].get("department") == "engineering", "E010: 批量部门推断失败"
    assert result2[1].get("department") == "sales", "E010: 批量部门推断失败"
    print("  [PASS] 批量处理")

    # 样例 3：格式化输出
    sample3 = [
        {"dn": "uid=alice,ou=people,dc=example,dc=com", "uid": "alice", "mail": "alice@example.com"},
        {"dn": "uid=bob,ou=people,dc=example,dc=com", "uid": "bob", "mail": "bob@example.com"},
    ]
    output = format_output(sample3, template=["uid", "mail"], separator="|")
    lines = output.strip().split("\n")
    assert len(lines) == 2, "E010: 格式化输出行数错误"
    assert "alice@example.com" in lines[0], "E010: 格式化输出内容错误"
    print("  [PASS] 格式化输出")

    # 样例 4：JSON 解析
    sample4 = '[{"dn": "uid=test,dc=example,dc=com", "uid": "test"}]'
    parsed = parse_input(sample4, "json")
    assert len(parsed) == 1, "E010: JSON 解析数量错误"
    assert parsed[0].get("uid") == "test", "E010: JSON 解析内容错误"
    print("  [PASS] JSON 解析")

    # 样例 5：LDIF 解析
    sample5 = "dn: uid=user1,ou=people,dc=example,dc=com\nuid: user1\ncn: User One\n"
    parsed5 = parse_input(sample5, "ldif")
    assert len(parsed5) == 1, "E010: LDIF 解析数量错误"
    assert parsed5[0].get("uid") == "user1", "E010: LDIF 解析内容错误"
    print("  [PASS] LDIF 解析")

    print("全部自检通过 ✓")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="ActiveLdap 数据映射与结构化转换工具",
        epilog="示例: python main.py --input data.json --format json --template uid,mail --separator '|'"
    )
    parser.add_argument("--input", "-i", help="输入文件路径（默认从标准输入读取）")
    parser.add_argument("--format", "-f", choices=["auto", "json", "csv", "ldif"], default="auto",
                        help="输入格式（默认自动检测）")
    parser.add_argument("--template", "-t", help="输出字段模板（逗号分隔）")
    parser.add_argument("--separator", "-s", default="|", help="输出字段分隔符（默认 |）")
    parser.add_argument("--no-infer", action="store_true", help="禁用字段推断")
    parser.add_argument("--no-skip-sensitive", action="store_true", help="不跳过敏感字段")
    parser.add_argument("--include-confidence", "-c", action="store_true", help="输出包含置信度列")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return _run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 读取输入
    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                data = f.read()
        else:
            data = sys.stdin.read()
    except Exception as e:
        print(_err("E009", f"读取输入失败: {e}"), file=sys.stderr)
        return 1

    # 解析输入
    try:
        entries = parse_input(data, args.format)
    except AppError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # 处理数据
    try:
        processed = process_batch(
            entries,
            skip_sensitive=not args.no_skip_sensitive,
            infer_fields=not args.no_infer
        )
    except AppError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # 模板解析
    template = None
    if args.template:
        template = [t.strip() for t in args.template.split(",") if t.strip()]

    # 输出
    try:
        output = format_output(
            processed,
            template=template,
            separator=args.separator,
            include_confidence=args.include_confidence
        )
        print(output)
    except Exception as e:
        print(_err("E010", f"输出失败: {e}"), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
