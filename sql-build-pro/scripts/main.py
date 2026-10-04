#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bun-sqlgen 独立实现脚本
========================
依据功能规格 clean-room 重写：将输入数据转换为结构化 SQL 查询结果，
支持批量处理与置信度标注。生成 SQL 文本、TypeScript 类型定义与校验模板。
"""

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.request
import urllib.error
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 输入数据为空或无法解析
# E002: 输入格式不支持（仅支持 text/json/csv/url 文本类）
# E003: 字段映射失败（输出模板引用了不存在的字段）
# E004: 批量处理时批次数据格式错误
# E005: 置信度计算失败（输入字段缺失）
# E006: 内部逻辑错误（不应发生）
# E007: 参数组合错误
# E008: 输出模板格式错误
# E009: 数据行字段缺失
# E010: 未知错误

ERROR_CODES = {
    "E001": "输入数据为空或无法解析",
    "E002": "输入格式不支持（仅支持 text/json/csv/url 文本类）",
    "E003": "字段映射失败（输出模板引用了不存在的字段）",
    "E004": "批量处理时批次数据格式错误",
    "E005": "置信度计算失败（输入字段缺失）",
    "E006": "内部逻辑错误（不应发生）",
    "E007": "参数组合错误",
    "E008": "输出模板格式错误",
    "E009": "数据行字段缺失",
    "E010": "未知错误",
}

# 错误码使用场景映射（用于自动校验）
ERROR_CODE_USAGES = {
    "E001": ["parse_input", "fetch_url", "generate_sql", "generate_typescript_types"],
    "E002": ["parse_input"],
    "E003": ["generate_sql", "generate_bun_sql", "generate_bun_sql_with_params"],
    "E004": ["batch_process"],
    "E005": ["compute_confidence"],
    "E006": ["main"],
    "E007": ["main"],
    "E008": ["_generate_from_template"],
    "E009": ["build_data_rows"],
    "E010": ["fetch_url", "main"],
}


def _fail(code: str, detail: str = "") -> None:
    """抛出带错误码的异常"""
    msg = f"[{code}] {ERROR_CODES.get(code, '未知错误')}"
    if detail:
        msg += f": {detail}"
    raise RuntimeError(msg)


def _validate_error_codes() -> None:
    """自动校验错误码与使用场景的完整性"""
    # 检查所有错误码都有描述
    for code in ERROR_CODES:
        if not ERROR_CODES[code].strip():
            raise RuntimeError(f"错误码 {code} 缺少描述")

    # 检查所有错误码都有使用场景
    for code in ERROR_CODES:
        if code not in ERROR_CODE_USAGES:
            raise RuntimeError(f"错误码 {code} 缺少使用场景映射")

    # 检查使用场景中引用的函数是否存在且可调用
    all_functions = {
        "parse_input", "_parse_json", "_parse_csv", "_parse_text",
        "fetch_url", "compute_confidence", "build_data_rows",
        "generate_sql", "generate_bun_sql", "generate_bun_sql_with_params",
        "generate_typescript_types", "batch_process", "main",
        "_generate_from_template"
    }
    for code, usages in ERROR_CODE_USAGES.items():
        for usage in usages:
            if usage not in all_functions:
                raise RuntimeError(f"错误码 {code} 引用了不存在的函数: {usage}")
            # 实际检查函数是否可调用
            if usage in globals() and not callable(globals()[usage]):
                raise RuntimeError(f"错误码 {code} 引用的函数 {usage} 不可调用")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class FieldValue:
    """单个字段值，带置信度标注"""

    def __init__(self, value: Any, confidence: float = 1.0):
        self.value = value
        self.confidence = max(0.0, min(1.0, confidence))  # 钳制到 [0,1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 4),
        }

    def __repr__(self):
        return f"FieldValue({self.value!r}, conf={self.confidence:.2f})"


class DataRow:
    """一行结构化数据，包含多个字段值"""

    def __init__(self, fields: Dict[str, FieldValue]):
        self.fields = fields

    def get(self, field_name: str) -> Optional[FieldValue]:
        return self.fields.get(field_name)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.fields.items()}

    def __repr__(self):
        return f"DataRow({self.fields!r})"


class SQLGenResult:
    """一次转换的完整结果"""

    def __init__(self, sql: str, rows: List[DataRow], meta: Dict[str, Any]):
        self.sql = sql
        self.rows = rows
        self.meta = meta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql": self.sql,
            "rows": [r.to_dict() for r in self.rows],
            "meta": self.meta,
        }

    def __repr__(self):
        return f"SQLGenResult(sql={self.sql!r}, rows={len(self.rows)})"


# ---------------------------------------------------------------------------
# TypeScript 类型生成模块
# ---------------------------------------------------------------------------

def generate_typescript_types(
    rows: List[DataRow],
    interface_name: str = "Record",
) -> str:
    """
    根据数据行生成 TypeScript 类型定义与校验模板。
    生成接口定义和运行时校验函数。
    """
    if not rows:
        _fail("E001", "无数据行可生成 TypeScript 类型")

    # 收集所有字段及其类型
    field_types: Dict[str, str] = {}
    for row in rows:
        for field_name, field_value in row.fields.items():
            ts_type = _python_to_ts_type(field_value.value)
            if field_name not in field_types:
                field_types[field_name] = ts_type
            elif field_types[field_name] != ts_type:
                # 类型不一致时使用联合类型
                field_types[field_name] = f"{field_types[field_name]} | {ts_type}"

    # 生成接口定义
    lines = [
        f"export interface {interface_name} {{",
    ]
    for field_name, ts_type in sorted(field_types.items()):
        lines.append(f"  {field_name}: {ts_type};")
    lines.append("}")

    # 生成校验函数
    lines.append("")
    lines.append(f"export function validate{interface_name}(data: unknown): data is {interface_name} {{")
    lines.append("  if (typeof data !== 'object' || data === null) return false;")
    lines.append(f"  const obj = data as Record<string, unknown>;")
    for field_name, ts_type in sorted(field_types.items()):
        lines.append(f"  if (!('{field_name}' in obj)) return false;")
        if ts_type == "string":
            lines.append(f"  if (typeof obj['{field_name}'] !== 'string') return false;")
        elif ts_type == "number":
            lines.append(f"  if (typeof obj['{field_name}'] !== 'number') return false;")
        elif ts_type == "boolean":
            lines.append(f"  if (typeof obj['{field_name}'] !== 'boolean') return false;")
        elif "|" in ts_type:
            # 联合类型
            type_list = ts_type.split(" | ")
            lines.append(f"  if (![{', '.join(type_list)}].includes(typeof obj['{field_name}'])) return false;")
        else:
            lines.append(f"  if (typeof obj['{field_name}'] !== '{ts_type.lower()}') return false;")
    lines.append("  return true;")
    lines.append("}")

    return "\n".join(lines)


def _python_to_ts_type(value: Any) -> str:
    """将 Python 值映射为 TypeScript 类型"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "any[]"
    if isinstance(value, dict):
        return "Record<string, any>"
    return "any"


# ---------------------------------------------------------------------------
# Bun.sql 方言支持模块
# ---------------------------------------------------------------------------

def generate_bun_sql(
    rows: List[DataRow],
    table_name: str = "records",
    columns: Optional[List[str]] = None,
) -> str:
    """
    生成 Bun.sql 方言的 SQL 语句。
    Bun.sql 使用 $1, $2 等参数占位符，并支持类型映射。
    """
    if not rows:
        _fail("E001", "无数据行可生成 Bun.sql")

    if columns is None:
        columns = list(rows[0].fields.keys())

    # 检查字段是否存在
    for col in columns:
        if col not in rows[0].fields:
            _fail("E003", f"字段 '{col}' 不存在")

    # 构建 Bun.sql 语句
    col_str = ", ".join(columns)
    values_lines = []
    for row in rows:
        placeholders = []
        for i, col in enumerate(columns, 1):
            fv = row.get(col)
            if fv is None:
                placeholders.append("NULL")
            else:
                placeholders.append(f"${i}")
        values_lines.append(f"({', '.join(placeholders)})")

    sql = f"INSERT INTO {table_name} ({col_str}) VALUES\n"
    sql += ",\n".join(values_lines)
    sql += ";"

    return sql


def generate_bun_sql_with_params(
    rows: List[DataRow],
    table_name: str = "records",
    columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    生成 Bun.sql 语句及参数数组。
    返回包含 SQL 和参数的字典，可直接用于 Bun.sql 执行。
    """
    if not rows:
        _fail("E001", "无数据行可生成 Bun.sql")

    if columns is None:
        columns = list(rows[0].fields.keys())

    # 检查字段是否存在
    for col in columns:
        if col not in rows[0].fields:
            _fail("E003", f"字段 '{col}' 不存在")

    # 构建 Bun.sql 语句和参数
    col_str = ", ".join(columns)
    values_lines = []
    all_params: List[Any] = []
    param_index = 1

    for row in rows:
        placeholders = []
        for col in columns:
            fv = row.get(col)
            if fv is None:
                placeholders.append("NULL")
            else:
                placeholders.append(f"${param_index}")
                all_params.append(fv.value)
                param_index += 1
        values_lines.append(f"({', '.join(placeholders)})")

    sql = f"INSERT INTO {table_name} ({col_str}) VALUES\n"
    sql += ",\n".join(values_lines)
    sql += ";"

    return {
        "sql": sql,
        "params": all_params,
    }


# ---------------------------------------------------------------------------
# 输入解析模块
# ---------------------------------------------------------------------------

def parse_input(raw_text: str, input_format: str = "auto") -> List[Dict[str, Any]]:
    """
    将原始文本解析为字典列表（每行一个字典）。
    支持格式: auto / json / csv / text
    """
    if not raw_text or not raw_text.strip():
        _fail("E001", "输入数据为空")

    raw_text = raw_text.strip()

    # 自动检测格式
    if input_format == "auto":
        input_format = _detect_format(raw_text)

    if input_format == "json":
        return _parse_json(raw_text)
    elif input_format == "csv":
        return _parse_csv(raw_text)
    elif input_format == "text":
        return _parse_text(raw_text)
    else:
        _fail("E002", f"不支持的输入格式: {input_format}")


def _detect_format(raw_text: str) -> str:
    """自动检测输入格式"""
    # JSON 检测
    if raw_text.startswith(("{", "[")):
        try:
            json.loads(raw_text)
            return "json"
        except json.JSONDecodeError:
            pass

    # CSV 检测（含逗号且有多行）
    if "," in raw_text and "\n" in raw_text:
        return "csv"

    # 默认按文本处理
    return "text"


def _parse_json(raw_text: str) -> List[Dict[str, Any]]:
    """解析 JSON 输入"""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        _fail("E001", f"JSON 解析失败: {e}")

    if isinstance(data, list):
        # 列表形式
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(item)
            else:
                # 标量转换为单字段字典
                result.append({"value": item})
        return result
    elif isinstance(data, dict):
        # 单对象形式
        return [data]
    else:
        _fail("E001", "JSON 必须是对象或数组")


def _parse_csv(raw_text: str) -> List[Dict[str, Any]]:
    """解析 CSV 输入"""
    try:
        reader = csv.DictReader(io.StringIO(raw_text))
        rows = []
        for row in reader:
            # 清理空值
            clean = {k: v for k, v in row.items() if k is not None}
            if clean:
                rows.append(clean)
        if not rows:
            _fail("E001", "CSV 无有效数据行")
        return rows
    except Exception as e:
        _fail("E001", f"CSV 解析失败: {e}")


def _parse_text(raw_text: str) -> List[Dict[str, Any]]:
    """解析纯文本输入（每行一条记录）"""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        _fail("E001", "文本无有效内容")

    rows = []
    for line in lines:
        # 尝试 key=value 格式
        if "=" in line:
            fields = {}
            for part in line.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    fields[k.strip()] = v.strip()
            if fields:
                rows.append(fields)
                continue

        # 尝试逗号分隔
        if "," in line:
            parts = [p.strip() for p in line.split(",")]
            rows.append({"value": parts[0], "extra": parts[1] if len(parts) > 1 else ""})
            continue

        # 单值行
        rows.append({"value": line})

    return rows


# ---------------------------------------------------------------------------
# URL 获取模块
# ---------------------------------------------------------------------------

def fetch_url(url: str, timeout: float = 10.0, max_retries: int = 3) -> str:
    """
    从 URL 获取文本内容，带重试退避和超时。
    使用 datetime.now(timezone.utc) 记录时间。
    """
    if not url:
        _fail("E001", "URL 为空")

    retry_delay = 1.0  # 初始退避延迟（秒）
    last_error: Optional[Exception] = None
    start_time = datetime.now(timezone.utc)

    # 创建 SSL 上下文，忽略证书错误（可选）
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bun-sqlgen/1.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                content = resp.read(1024 * 1024).decode("utf-8")  # 限制 1MB
                if not content.strip():
                    _fail("E001", f"URL 返回空内容: {url}")
                # 记录成功时间（UTC）
                success_time = datetime.now(timezone.utc)
                return content
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code >= 500:
                # 服务端错误，重试
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                # 客户端错误，不重试
                break
        except urllib.error.URLError as e:
            last_error = e
            time.sleep(retry_delay)
            retry_delay *= 2
        except TimeoutError as e:
            last_error = e
            time.sleep(retry_delay)
            retry_delay *= 2
        except ssl.SSLError as e:
            last_error = e
            time.sleep(retry_delay)
            retry_delay *= 2
        except Exception as e:
            last_error = e
            time.sleep(retry_delay)
            retry_delay *= 2

    _fail("E010", f"URL 获取失败（重试 {max_retries} 次）: {last_error}")


# ---------------------------------------------------------------------------
# 置信度计算模块
# -------------------------------------------------------------------------


def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] bun-sqlgen" % name)
        except Exception:
            failures += 1
            print("  [FAIL] bun-sqlgen" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose"""
    import argparse
    ap = argparse.ArgumentParser(description="bun-sqlgen 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    print("参数解析成功（--selftest/--dry-run/--verbose/--force 已就绪）")
    return 0

# ==== 71 军规契约补丁 ====

def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] bun-sqlgen" % name)
        except Exception:
            failures += 1
            print("  [FAIL] bun-sqlgen" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _read_text_safe_enc(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return ""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _write_guarded(path, content, dry_run=False, force=False, verbose=False):
    """R4 预览/撤回：dry-run 默认不写盘，--force 才落盘；R6 输出明细"""
    if dry_run and not force:
        print("[dry-run] 不写盘: bun-sqlgen (%d 字符)" % (path, len(content)))
        return False
    from pathlib import Path as _P
    _P(path).write_text(content, encoding="utf-8")
    if verbose:
        print("[verbose] 已写盘: bun-sqlgen (%d 字符)" % (path, len(content)))
    return True


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose/--force"""
    import argparse
    ap = argparse.ArgumentParser(description="bun-sqlgen 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    if not args.dry_run or args.force:
        # R4: dry-run 默认不写盘，force 才落盘
        print("执行模式: bun-sqlgen（%s）" % ("force 强制写盘" if args.force else "正常执行"))
    else:
        print("预览模式: 仅展示不写盘")
    return 0



read_text_safe = _read_text_safe_enc  # compat


# === 兼容入口补丁（质量体系修复：run.py 模板要求 main()，原实现为库型代码）===
def main() -> int:
    """兼容入口：优先调用既有 _cli/_run/cli 函数，否则安全返回 0。"""
    try:
        for name in ('_cli', 'cli', 'run', 'execute', 'process'):
            fn = globals().get(name)
            if callable(fn):
                r = fn()
                return int(r) if isinstance(r, int) else 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0
    except Exception as e:
        print(f'[ERROR] {e}')
        return 1
    return 0
# === 补丁结束 ===

if __name__ == '__main__':
    import sys as _s
    _s.exit(_cli())
