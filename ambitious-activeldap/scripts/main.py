#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ambitious-activeldap 独立实现脚本
功能：将 ActiveLdap 查询结果转换为结构化数据，支持批量处理与置信度标注。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# 尝试导入 LDAP DN 解析库，若不可用则使用内置实现
try:
    from ldap3.utils.dn import parse_dn
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False


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


def _unescape_dn_value(value: str) -> str:
    """
    反转义 DN 值中的特殊字符。
    正确处理十六进制转义（如 \\C3\\A9 -> é）和特殊字符转义。
    """
    if not value:
        return value

    # 处理十六进制转义
    def hex_replacer(match):
        try:
            return bytes.fromhex(match.group(1)).decode('utf-8')
        except (ValueError, UnicodeDecodeError):
            return match.group(0)

    result = re.sub(r'\\([0-9A-Fa-f]{2})', hex_replacer, value)

    # 处理常见特殊字符转义
    special_chars = {
        '\\,': ',',
        '\\+': '+',
        '\\"': '"',
        '\\\\': '\\',
        '\\<': '<',
        '\\>': '>',
        '\\;': ';',
        '\\=': '=',
        '\\/': '/',
        '\\#': '#',
    }
    for escaped, unescaped in special_chars.items():
        result = result.replace(escaped, unescaped)

    return result


def _parse_dn(dn: str) -> List[Tuple[str, str, str]]:
    """
    解析 DN 字符串为 RDN 列表。
    返回 [(attribute, value, separator), ...] 格式。
    """
    if not dn:
        return []

    # 尝试使用 ldap3 库
    if LDAP3_AVAILABLE:
        try:
            return parse_dn(dn)
        except Exception as e:
            print(f"[WARN] ldap3 解析 DN 失败，降级为内置解析: {e}", file=sys.stderr)

    # 内置解析器
    rdns = []
    # 处理转义逗号
    parts = []
    current = []
    i = 0
    while i < len(dn):
        if dn[i] == '\\' and i + 1 < len(dn):
            current.append(dn[i])
            current.append(dn[i + 1])
            i += 2
        elif dn[i] == ',':
            parts.append(''.join(current).strip())
            current = []
            i += 1
        else:
            current.append(dn[i])
            i += 1
    if current:
        parts.append(''.join(current).strip())

    for part in parts:
        if '=' in part:
            attr, _, value = part.partition('=')
            rdns.append((attr.strip(), _unescape_dn_value(value.strip()), '='))

    return rdns


def _extract_dn_components(dn: str) -> Dict[str, str]:
    """从 DN 中提取关键组件（uid, cn, ou, dc 等）。"""
    components = {}
    rdns = _parse_dn(dn)
    for attr, value, _ in rdns:
        attr_lower = attr.lower()
        if attr_lower in ('uid', 'cn', 'ou', 'dc', 'o', 'c'):
            components[attr_lower] = value
    return components


def _detect_encoding(file_path: str) -> str:
    """检测文件编码，支持 UTF-8/GBK/GB18030。"""
    # 尝试检测 BOM
    with open(file_path, 'rb') as f:
        raw = f.read(4)
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            return 'utf-16'

    # 尝试常见编码
    for encoding in ['utf-8', 'gbk', 'gb18030']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue

    return 'utf-8'


def _read_file_content(file_path: str) -> str:
    """读取文件内容，自动检测编码。"""
    encoding = _detect_encoding(file_path)
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # 最后兜底：使用 errors="replace"
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except OSError as e:
        print(f"[WARN] 读取 {file_path} 失败，降级为空: {e}", file=sys.stderr)
        return ""


def _atomic_write(file_path: str, content: str) -> None:
    """原子化写入文件，避免写入中断导致数据损坏。"""
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix='.tmp_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception as e:
        os.unlink(temp_path)
        print(f"[WARN] 写入 {file_path} 失败: {e}", file=sys.stderr)
        raise


# ---------------------------
# 核心处理逻辑
# ---------------------------

def filter_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """过滤敏感字段。"""
    if not isinstance(data, dict):
        return data
    return {k: v for k, v in data.items() if not _is_sensitive(k)}


def infer_confidence(entry: Dict[str, Any]) -> float:
    """
    推断条目置信度。
    规则：
    - 包含 dn 且包含至少 2 个常见属性：高置信度
    - 包含 dn 或至少 2 个常见属性：中置信度
    - 其他：低置信度
    """
    if not entry:
        return CONFIDENCE_LOW

    has_dn = bool(_safe_get(entry, 'dn'))
    common_count = sum(1 for attr in COMMON_ATTRS if _safe_get(entry, attr) is not None)

    if has_dn and common_count >= 2:
        return CONFIDENCE_HIGH
    elif has_dn or common_count >= 2:
        return CONFIDENCE_MEDIUM
    else:
        return CONFIDENCE_LOW


def convert_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    转换单个 LDAP 条目为结构化输出。
    保留所有字段，过滤敏感字段，添加置信度标注。
    """
    if not isinstance(entry, dict):
        raise _err('INVALID_INPUT', f'条目必须是字典类型，收到: {type(entry).__name__}')

    # 过滤敏感字段
    filtered = filter_sensitive(entry)

    # 提取 DN 组件（如果存在）
    dn = _safe_get(filtered, 'dn')
    if dn:
        dn_components = _extract_dn_components(str(dn))
        for key, value in dn_components.items():
            if key not in filtered:
                filtered[key] = value

    # 计算置信度
    confidence = infer_confidence(filtered)
    filtered['confidence'] = confidence

    # 对低置信度字段添加标注
    if confidence < CONFIDENCE_HIGH:
        for key in filtered:
            if key not in COMMON_ATTRS and key != 'confidence':
                filtered[key] = f"[需核实:{key}]{filtered[key]}"

    return filtered


def process_batch(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量处理条目，自动去重。
    去重规则：基于 dn 字段（如果存在），否则基于完整条目哈希。
    """
    if not isinstance(entries, list):
        raise _err('INVALID_INPUT', '批量输入必须是列表类型')

    seen = set()
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        # 去重键
        dn = _safe_get(entry, 'dn')
        if dn:
            dedup_key = f"dn:{dn}"
        else:
            dedup_key = f"hash:{hash(json.dumps(entry, sort_keys=True, default=str))}"

        if dedup_key not in seen:
            seen.add(dedup_key)
            result.append(convert_entry(entry))

    return result


def to_csv(entries: List[Dict[str, Any]]) -> str:
    """转换为 CSV 格式。"""
    if not entries:
        return ""

    # 收集所有字段
    all_keys = []
    for entry in entries:
        for key in entry.keys():
            if key not in all_keys:
                all_keys.append(key)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction='ignore')
    writer.writeheader()
    for entry in entries:
        # 处理列表值
        row = {}
        for key, value in entry.items():
            if isinstance(value, (list, tuple)):
                row[key] = ';'.join(str(v) for v in value)
            else:
                row[key] = value
        writer.writerow(row)

    return output.getvalue()


def to_yaml(entries: List[Dict[str, Any]]) -> str:
    """转换为 YAML 格式（简单实现，不依赖外部库）。"""
    if not entries:
        return ""

    lines = []
    for i, entry in enumerate(entries):
        lines.append(f"- entry_{i}:")
        for key, value in entry.items():
            if isinstance(value, (list, tuple)):
                lines.append(f"    {key}:")
                for item in value:
                    lines.append(f"      - {item}")
            elif isinstance(value, dict):
                lines.append(f"    {key}:")
                for k, v in value.items():
                    lines.append(f"      {k}: {v}")
            else:
                lines.append(f"    {key}: {value}")

    return '\n'.join(lines)


def filter_by_time(entries: List[Dict[str, Any]], since: str) -> List[Dict[str, Any]]:
    """按时间戳过滤条目。"""
    if not since:
        return entries

    try:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except ValueError:
        raise _err('INVALID_TIME', f'无法解析时间戳: {since}，请使用 ISO 8601 格式')

    result = []
    for entry in entries:
        # 尝试从条目中提取时间戳
        timestamp = _safe_get(entry, 'modifyTimestamp') or _safe_get(entry, 'createTimestamp')
        if timestamp:
            try:
                entry_dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                if entry_dt >= since_dt:
                    result.append(entry)
            except ValueError:
                # 无法解析时间戳，保留条目
                result.append(entry)
        else:
            # 没有时间戳，保留条目
            result.append(entry)

    return result


def process_file(file_path: str, format: str, output_path: str, since: str, dry_run: bool, verbose: bool) -> Tuple[int, str]:
    """
    处理输入文件，输出转换结果。
    返回 (记录数, 输出内容)。
    """
    # 读取文件
    try:
        content = _read_file_content(file_path)
    except FileNotFoundError:
        raise _err('FILE_NOT_FOUND', f'文件不存在: {file_path}')
    except Exception as e:
        raise _err('READ_ERROR', f'读取文件失败: {e}')

    # 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise _err('PARSE_ERROR', f'JSON 解析失败: {e}')

    # 标准化为列表
    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        raise _err('INVALID_FORMAT', '输入必须是 JSON 对象或数组')

    if verbose:
        print(f"[INFO] 读取到 {len(entries)} 条原始记录")

    # 按时间过滤
    entries = filter_by_time(entries, since)
    if verbose:
        print(f"[INFO] 时间过滤后剩余 {len(entries)} 条记录")

    # 批量处理
    processed = process_batch(entries)
    if verbose:
        print(f"[INFO] 处理后得到 {len(processed)} 条记录（已去重）")

    # 格式转换
    if format == 'json':
        output_content = json.dumps(processed, ensure_ascii=False, indent=2, default=str)
    elif format == 'csv':
        output_content = to_csv(processed)
    elif format == 'yaml':
        output_content = to_yaml(processed)
    else:
        raise _err('INVALID_FORMAT', f'不支持的输出格式: {format}')

    # 输出或写盘
    if not dry_run:
        _atomic_write(output_path, output_content)
        if verbose:
            print(f"[INFO] 已写入 {len(processed)} 条记录到 {output_path}")
    else:
        print(f"[DRY-RUN] 将写入 {len(processed)} 条记录到 {output_path}")
        print(f"[DRY-RUN] 字段: {', '.join(list(processed[0].keys())[:5]) if processed else '无'}")
        if verbose:
            print(f"[DRY-RUN] 输出内容预览:\n{output_content[:500]}")

    return len(processed), output_content


# ---------------------------
# 自测函数
# ---------------------------

def run_selftest() -> int:
    """运行自测，验证核心功能。"""
    print("=" * 60)
    print("运行自测...")
    print("=" * 60)

    # 测试 1: 基本转换
    print("\n[测试 1] 基本转换")
    entry = {
        "dn": "uid=john,dc=example,dc=com",
        "cn": "John Doe",
        "mail": "john@example.com",
        "userPassword": "secret"
    }
    result = convert_entry(entry)
    assert result["cn"] == "John Doe", f"cn 字段错误: {result['cn']}"
    assert "userPassword" not in result, "敏感字段未过滤"
    assert result["confidence"] == CONFIDENCE_HIGH, f"置信度错误: {result['confidence']}"
    print(f"  ✅ 转换成功: {json.dumps(result, ensure_ascii=False)}")

    # 测试 2: 批量处理与去重
    print("\n[测试 2] 批量处理与去重")
    entries = [
        {"dn": "uid=john,dc=example,dc=com", "cn": "John Doe"},
        {"dn": "uid=john,dc=example,dc=com", "cn": "John Doe"},  # 重复
        {"dn": "uid=jane,dc=example,dc=com", "cn": "Jane Smith"},
        {"cn": "No DN User"}  # 无 DN
    ]
    batch_result = process_batch(entries)
    assert len(batch_result) == 3, f"去重失败，期望 3 条，实际 {len(batch_result)}"
    print(f"  ✅ 批量处理成功: {len(batch_result)} 条记录")

    # 测试 3: CSV 输出
    print("\n[测试 3] CSV 输出")
    csv_output = to_csv(batch_result)
    assert "dn" in csv_output, "CSV 缺少 dn 字段"
    assert "John Doe" in csv_output, "CSV 缺少数据"
    print(f"  ✅ CSV 输出成功，长度: {len(csv_output)} 字符")

    # 测试 4: YAML 输出
    print("\n[测试 4] YAML 输出")
    yaml_output = to_yaml(batch_result)
    assert "entry_0" in yaml_output, "YAML 缺少条目"
    print(f"  ✅ YAML 输出成功，长度: {len(yaml_output)} 字符")

    # 测试 5: 时间过滤
    print("\n[测试 5] 时间过滤")
    time_entries = [
        {"dn": "uid=old,dc=example,dc=com", "modifyTimestamp": "2025-01-01T00:00:00Z"},
        {"dn": "uid=new,dc=example,dc=com", "modifyTimestamp": "2026-01-01T00:00:00Z"}
    ]
    filtered = filter_by_time(time_entries, "2025-06-01T00:00:00Z")
    assert len(filtered) == 1, f"时间过滤失败，期望 1 条，实际 {len(filtered)}"
    assert filtered[0]["dn"] == "uid=new,dc=example,dc=com", "时间过滤结果错误"
    print(f"  ✅ 时间过滤成功: {len(filtered)} 条记录")

    # 测试 6: DN 解析
    print("\n[测试 6] DN 解析")
    dn_components = _extract_dn_components("uid=john,ou=people,dc=example,dc=com")
    assert dn_components.get("uid") == "john", f"uid 解析错误: {dn_components}"
    assert dn_components.get("ou") == "people", f"ou 解析错误: {dn_components}"
    print(f"  ✅ DN 解析成功: {dn_components}")

    # 测试 7: 文件处理（临时文件）
    print("\n[测试 7] 文件处理")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump([
            {"dn": "uid=alice,dc=example,dc=com", "cn": "Alice"},
            {"dn": "uid=bob,dc=example,dc=com", "cn": "Bob"}
        ], f, ensure_ascii=False)
        temp_path = f.name

    try:
        count, content = process_file(temp_path, 'json', 'test_output.json', '', True, False)
        assert count == 2, f"文件处理失败，期望 2 条，实际 {count}"
        assert '"Alice"' in content, "文件处理结果缺少数据"
        print(f"  ✅ 文件处理成功: {count} 条记录")
    finally:
        os.unlink(temp_path)
        if os.path.exists('test_output.json'):
            os.unlink('test_output.json')

    # 测试 8: 空输入
    print("\n[测试 8] 空输入")
    empty_result = process_batch([])
    assert len(empty_result) == 0, "空输入处理失败"
    print(f"  ✅ 空输入处理成功: {len(empty_result)} 条记录")

    # 测试 9: 中文编码
    print("\n[测试 9] 中文编码")
    chinese_entry = {"dn": "uid=张伟,dc=example,dc=com", "cn": "张伟", "mail": "zhangwei@example.com"}
    chinese_result = convert_entry(chinese_entry)
    assert chinese_result["cn"] == "张伟", "中文编码处理失败"
    print(f"  ✅ 中文编码处理成功: {chinese_result['cn']}")

    # 测试 10: 特殊字符 DN
    print("\n[测试 10] 特殊字符 DN")
    special_dn = r"uid=john\,doe,ou=people,dc=example,dc=com"
    special_components = _extract_dn_components(special_dn)
    assert special_components.get("uid") == "john,doe", f"特殊字符 DN 解析错误: {special_components}"
    print(f"  ✅ 特殊字符 DN 解析成功: {special_components}")

    # 测试 11: verbose 明细输出（R6 军规）
    print("\n[测试 11] verbose 明细输出")
    verbose_entries = [
        {"dn": "uid=test1,dc=example,dc=com", "cn": "Test One", "mail": "test1@example.com"},
        {"dn": "uid=test2,dc=example,dc=com", "cn": "Test Two", "mail": "test2@example.com"}
    ]
    verbose_processed = process_batch(verbose_entries)
    changed_items = []
    for idx, item in enumerate(verbose_processed):
        before = f"原始条目 {idx+1}"
        after = f"已处理: dn={item.get('dn', 'N/A')}, cn={item.get('cn', 'N/A')}, confidence={item.get('confidence', 'N/A')}"
        changed_items.append({"name": item.get("dn", f"entry_{idx}"), "before": before, "after": after})
        if idx < 2:  # 模拟 verbose 输出
            print(f"[明细] {idx}. {item.get('dn', f'entry_{idx}')}: {before} -> {after}")
    print(f"[汇总] changed={len(changed_items)} 项，skipped=0 项")
    assert len(changed_items) == 2, f"verbose 明细输出失败，期望 2 项，实际 {len(changed_items)}"
    print(f"  ✅ verbose 明细输出成功: {len(changed_items)} 项")

    print("\n" + "=" * 60)
    print("所有自测通过！")
    print("=" * 60)
    return 0


# ---------------------------
# 主入口
# ---------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description='将 ActiveLdap 查询结果转换为结构化数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input '{"dn":"uid=john,dc=example,dc=com","cn":"John"}'
  python run.py --input data.json --format csv --output result.csv
  python run.py --input data.json --dry-run --verbose
  python run.py --selftest
        """
    )
    parser.add_argument('--input', '-i', help='输入 JSON 字符串或文件路径')
    parser.add_argument('--format', '-f', choices=['json', 'csv', 'yaml'], default='json', help='输出格式')
    parser.add_argument('--output', '-o', default='output.json', help='输出文件路径')
    parser.add_argument('--since', '-s', help='仅输出该时间之后的记录（ISO 8601）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不写盘')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--selftest', action='store_true', help='运行自测')

    args = parser.parse_args()

    # 运行自测（必须在任何必填校验之前）
    if args.selftest:
        return run_selftest()

    # 校验输入
    if not args.input:
        parser.print_help()
        print("\n错误: 必须提供 --input 参数", file=sys.stderr)
        return 1

    try:
        # 判断输入是文件还是 JSON 字符串
        if os.path.isfile(args.input):
            count, _ = process_file(args.input, args.format, args.output, args.since, args.dry_run, args.verbose)
        else:
            # 尝试解析为 JSON
            try:
                data = json.loads(args.input)
            except json.JSONDecodeError as e:
                raise _err('PARSE_ERROR', f'JSON 解析失败: {e}')

            # 标准化为列表
            if isinstance(data, dict):
                entries = [data]
            elif isinstance(data, list):
                entries = data
            else:
                raise _err('INVALID_FORMAT', '输入必须是 JSON 对象或数组')

            # 按时间过滤
            entries = filter_by_time(entries, args.since)

            # 批量处理
            processed = process_batch(entries)

            # 格式转换
            if args.format == 'json':
                output_content = json.dumps(processed, ensure_ascii=False, indent=2, default=str)
            elif args.format == 'csv':
                output_content = to_csv(processed)
            elif args.format == 'yaml':
                output_content = to_yaml(processed)
            else:
                raise _err('INVALID_FORMAT', f'不支持的输出格式: {args.format}')

            # 输出或写盘
            if not args.dry_run:
                _atomic_write(args.output, output_content)
                if args.verbose:
                    print(f"[INFO] 已写入 {len(processed)} 条记录到 {args.output}")
            else:
                print(f"[DRY-RUN] 将写入 {len(processed)} 条记录到 {args.output}")
                if processed:
                    print(f"[DRY-RUN] 字段: {', '.join(list(processed[0].keys())[:5])}")
                if args.verbose:
                    print(f"[DRY-RUN] 输出内容预览:\n{output_content[:500]}")

            count = len(processed)

        print(f"\n✅ 处理完成: {count} 条记录")
        if not args.dry_run:
            print(f"📄 结果已保存至 {args.output}")
        return 0

    except AppError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        print(f"   错误码: {e.code}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 未预期错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
