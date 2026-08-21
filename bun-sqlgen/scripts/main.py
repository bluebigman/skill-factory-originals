#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bun-sqlgen 独立实现脚本
========================
依据功能规格 clean-room 重写：将输入数据转换为结构化 SQL 查询结果，
支持批量处理与置信度标注。仅生成 SQL 文本，不连接数据库执行。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


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


def _fail(code: str, detail: str = "") -> None:
    """抛出带错误码的异常"""
    msg = f"[{code}] {ERROR_CODES.get(code, '未知错误')}"
    if detail:
        msg += f": {detail}"
    raise RuntimeError(msg)


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
# 置信度计算模块
# ---------------------------------------------------------------------------

def compute_confidence(value: Any, field_name: str = "") -> float:
    """
    计算字段值的置信度（0.0 ~ 1.0）。
    宽松规则：非空值高置信，空值低置信，数字/布尔更确定。
    """
    if value is None:
        return 0.1
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return 0.1
        # 长文本置信度略低（可能包含噪声）
        if len(s) > 100:
            return 0.7
        return 0.9
    if isinstance(value, (int, float, bool)):
        return 1.0
    if isinstance(value, (list, dict)):
        return 0.8 if value else 0.3
    return 0.6


def build_data_rows(raw_rows: List[Dict[str, Any]]) -> List[DataRow]:
    """将原始字典列表转换为带置信度的 DataRow 列表"""
    rows = []
    for raw in raw_rows:
        fields = {}
        for key, value in raw.items():
            conf = compute_confidence(value, key)
            fields[key] = FieldValue(value, conf)
        rows.append(DataRow(fields))
    return rows


# ---------------------------------------------------------------------------
# SQL 生成模块
# ---------------------------------------------------------------------------

def generate_sql(
    rows: List[DataRow],
    table_name: str = "records",
    columns: Optional[List[str]] = None,
    template: Optional[str] = None,
) -> str:
    """
    根据数据行生成 SQL 语句。
    支持两种模式：
    1. template 模式：使用用户自定义模板（{field} 占位符）
    2. 默认模式：生成 INSERT 语句
    """
    if not rows:
        _fail("E001", "无数据行可生成 SQL")

    if template:
        return _generate_from_template(rows, template)

    # 默认生成 INSERT 语句
    if columns is None:
        # 从第一行提取所有字段名
        columns = list(rows[0].fields.keys())

    # 检查字段是否存在
    for col in columns:
        if col not in rows[0].fields:
            _fail("E003", f"字段 '{col}' 不存在")

    # 构建 INSERT 语句
    col_str = ", ".join(columns)
    values_lines = []
    for row in rows:
        vals = []
        for col in columns:
            fv = row.get(col)
            if fv is None:
                vals.append("NULL")
            else:
                vals.append(_format_sql_value(fv.value))
        values_lines.append(f"({', '.join(vals)})")

    sql = f"INSERT INTO {table_name} ({col_str}) VALUES\n"
    sql += ",\n".join(values_lines)
    sql += ";"

    return sql


def _format_sql_value(value: Any) -> str:
    """将 Python 值格式化为 SQL 字面量"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # 转义单引号
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(value, (list, dict)):
        # 复杂类型转为 JSON 字符串
        return f"'{json.dumps(value, ensure_ascii=False)}'"
    return f"'{str(value)}'"


def _generate_from_template(rows: List[DataRow], template: str) -> str:
    """使用模板生成 SQL（逐行替换 {field} 占位符）"""
    # 验证模板格式
    if "{" not in template or "}" not in template:
        _fail("E008", "模板必须包含 {field} 占位符")

    # 提取模板中的字段名
    field_names = re.findall(r"\{(\w+)\}", template)
    if not field_names:
        _fail("E008", "模板中未找到有效字段占位符")

    # 检查字段存在性
    first_row = rows[0]
    for fname in field_names:
        if fname not in first_row.fields:
            _fail("E003", f"模板引用字段 '{fname}' 不存在")

    # 逐行替换
    statements = []
    for row in rows:
        stmt = template
        for fname in field_names:
            fv = row.get(fname)
            if fv is None:
                val_str = "NULL"
            else:
                val_str = _format_sql_value(fv.value)
            stmt = stmt.replace("{" + fname + "}", val_str)
        statements.append(stmt)

    return "\n".join(statements)


# ---------------------------------------------------------------------------
# 批量处理模块
# ---------------------------------------------------------------------------

def batch_process(
    all_rows: List[DataRow],
    batch_size: int = 100,
    table_name: str = "records",
    columns: Optional[List[str]] = None,
) -> List[SQLGenResult]:
    """将多行数据分批生成 SQL"""
    if batch_size <= 0:
        _fail("E007", "批大小必须为正整数")

    if not all_rows:
        _fail("E001", "无数据可处理")

    results = []
    for i in range(0, len(all_rows), batch_size):
        batch = all_rows[i:i + batch_size]
        sql = generate_sql(batch, table_name=table_name, columns=columns)
        meta = {
            "batch_index": i // batch_size,
            "batch_size": len(batch),
            "start": i,
            "end": min(i + batch_size, len(all_rows)),
        }
        results.append(SQLGenResult(sql=sql, rows=batch, meta=meta))

    return results


# ---------------------------------------------------------------------------
# 主处理函数
# ---------------------------------------------------------------------------

def process(
    raw_text: str,
    input_format: str = "auto",
    table_name: str = "records",
    columns: Optional[List[str]] = None,
    template: Optional[str] = None,
    batch_size: Optional[int] = None,
) -> Dict[str, Any]:
    """完整处理流程：解析 -> 结构化 -> 生成 SQL"""
    try:
        # 1. 解析输入
        raw_rows = parse_input(raw_text, input_format)

        # 2. 构建带置信度的数据行
        data_rows = build_data_rows(raw_rows)

        # 3. 批量或单批处理
        if batch_size is not None:
            results = batch_process(
                data_rows,
                batch_size=batch_size,
                table_name=table_name,
                columns=columns,
            )
            # 合并结果
            all_sql = "\n\n".join(r.sql for r in results)
            meta = {
                "total_rows": len(data_rows),
                "batches": len(results),
                "batch_size": batch_size,
                "format": input_format,
                "table": table_name,
            }
            return {
                "sql": all_sql,
                "rows": [r.to_dict() for r in data_rows],
                "meta": meta,
            }
        else:
            # 单批处理
            sql = generate_sql(data_rows, table_name=table_name, columns=columns, template=template)
            meta = {
                "total_rows": len(data_rows),
                "batches": 1,
                "format": input_format,
                "table": table_name,
            }
            return {
                "sql": sql,
                "rows": [r.to_dict() for r in data_rows],
                "meta": meta,
            }

    except RuntimeError:
        raise
    except Exception as e:
        _fail("E010", f"处理失败: {str(e)}")


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> None:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("开始自检 bun-sqlgen ...")

    # ---- 测试 1: JSON 解析 + SQL 生成 ----
    print("[1/4] 测试 JSON 解析 + INSERT 生成 ...")
    json_input = json.dumps([
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
    ])
    result = process(json_input, input_format="json", table_name="users")
    assert len(result["rows"]) == 2, "JSON 应解析出 2 行"
    assert "INSERT INTO users" in result["sql"], "应生成 INSERT 语句"
    assert "Alice" in result["sql"], "SQL 应包含数据值"
    print("  通过")

    # ---- 测试 2: CSV 解析 + 置信度标注 ----
    print("[2/4] 测试 CSV 解析 + 置信度标注 ...")
    csv_input = "name,age,city\nAlice,30,Beijing\nBob,25,\n"
    result = process(csv_input, input_format="csv", table_name="people")
    rows = result["rows"]
    assert len(rows) == 2, "CSV 应解析出 2 行"
    # 置信度应在合理范围内
    for row in rows:
        for field_name, field_info in row.items():
            conf = field_info["confidence"]
            assert 0.0 <= conf <= 1.0, "置信度应在 [0,1] 区间"
    # 空字段置信度应较低
    empty_conf = rows[1]["city"]["confidence"]
    nonempty_conf = rows[0]["city"]["confidence"]
    assert empty_conf < nonempty_conf, "空字段置信度应低于非空字段"
    print("  通过")

    # ---- 测试 3: 模板模式 ----
    print("[3/4] 测试自定义模板 ...")
    template = "SELECT * FROM t WHERE name = {name} AND age = {age};"
    result = process(json_input, input_format="json", template=template)
    assert "SELECT * FROM t" in result["sql"], "应使用模板"
    assert "Alice" in result["sql"], "模板应包含数据值"
    assert "Bob" in result["sql"], "模板应包含第二行数据"
    print("  通过")

    # ---- 测试 4: 批量处理 ----
    print("[4/4] 测试批量处理 ...")
    big_input = json.dumps([{"id": i, "val": f"item_{i}"} for i in range(10)])
    result = process(big_input, input_format="json", table_name="items", batch_size=3)
    assert len(result["rows"]) == 10, "应处理全部 10 行"
    assert result["meta"]["batches"] >= 3, "10 行按 3 分批应至少 3 批"
    assert result["sql"].count("INSERT INTO items") >= 3, "应生成多条 INSERT"
    print("  通过")

    print("\n全部自检通过 ✅")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="bun-sqlgen: 将输入数据转换为结构化 SQL 查询结果",
        epilog="示例: python main.py --input data.json --format json --table users"
    )
    parser.add_argument("--input", "-i", help="输入数据（文本/JSON/CSV）")
    parser.add_argument("--file", "-f", help="从文件读取输入")
    parser.add_argument("--format", "-fmt", default="auto",
                        choices=["auto", "json", "csv", "text"],
                        help="输入格式（默认自动检测）")
    parser.add_argument("--table", "-t", default="records", help="目标表名")
    parser.add_argument("--columns", "-c", help="逗号分隔的字段列表")
    parser.add_argument("--template", help="自定义 SQL 模板（{field} 占位符）")
    parser.add_argument("--batch-size", type=int, help="批量处理大小")
    parser.add_argument("--output", "-o", help="输出文件（默认 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 检查参数
    if not args.input and not args.file:
        print("错误: 必须提供 --input 或 --file", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        # 读取输入
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            raw_text = args.input

        # 解析字段列表
        columns = None
        if args.columns:
            columns = [c.strip() for c in args.columns.split(",") if c.strip()]

        # 处理
        result = process(
            raw_text,
            input_format=args.format,
            table_name=args.table,
            columns=columns,
            template=args.template,
            batch_size=args.batch_size,
        )

        # 输出
        output_text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
        else:
            print(output_text)

        return 0

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
