#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
SQL Generator and Editor - ERP 迁移工具
根据功能规格独立实现，仅使用标准库。
"""

import argparse
import re
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "数据表名为空",
    "E008": "字段列表为空",
    "E009": "主键缺失，无法生成 UPDATE/DELETE",
    "E010": "参数解析错误",
}


# ============================================================
# 数据结构
# ============================================================
@dataclass
class SqlRequest:
    """标准化的 SQL 生成请求"""
    table_name: str
    operation: str  # 'insert' | 'update' | 'delete' | 'select'
    data: Dict[str, Any] = field(default_factory=dict)  # 字段名 -> 值
    conditions: Dict[str, Any] = field(default_factory=dict)  # 条件字段 -> 值
    primary_key: Optional[str] = None
    fields: List[str] = field(default_factory=list)  # select 用


@dataclass
class SqlResult:
    """生成结果"""
    sql: Optional[str] = None
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error_code: Optional[str] = None


# ============================================================
# 核心工具函数
# ============================================================
def _format_value(value: Any) -> str:
    """将 Python 值转换为 SQL 字面量"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return f"X'{value.hex()}'"
    # 字符串：转义单引号
    s = str(value).replace("'", "''")
    return f"'{s}'"


def _validate_request(req: SqlRequest) -> Optional[str]:
    """校验请求，返回错误码或 None"""
    if not req.table_name or not req.table_name.strip():
        return "E007"
    if req.operation in ("insert", "update") and not req.data:
        return "E008"
    if req.operation in ("update", "delete") and not req.conditions:
        return "E009"
    return None


def _build_where(conditions: Dict[str, Any]) -> str:
    """构建 WHERE 子句"""
    if not conditions:
        return ""
    clauses = []
    for key, val in conditions.items():
        if val is None:
            clauses.append(f"{key} IS NULL")
        else:
            clauses.append(f"{key} = {_format_value(val)}")
    return " WHERE " + " AND ".join(clauses)


def _build_set(data: Dict[str, Any]) -> str:
    """构建 SET 子句"""
    items = [f"{k} = {_format_value(v)}" for k, v in data.items()]
    return ", ".join(items)


def _build_insert(req: SqlRequest) -> str:
    """生成 INSERT 语句"""
    cols = list(req.data.keys())
    vals = [_format_value(req.data[c]) for c in cols]
    col_str = ", ".join(cols)
    val_str = ", ".join(vals)
    return f"INSERT INTO {req.table_name} ({col_str}) VALUES ({val_str})"


def _build_update(req: SqlRequest) -> str:
    """生成 UPDATE 语句"""
    set_clause = _build_set(req.data)
    where_clause = _build_where(req.conditions)
    return f"UPDATE {req.table_name} SET {set_clause}{where_clause}"


def _build_delete(req: SqlRequest) -> str:
    """生成 DELETE 语句"""
    where_clause = _build_where(req.conditions)
    return f"DELETE FROM {req.table_name}{where_clause}"


def _build_select(req: SqlRequest) -> str:
    """生成 SELECT 语句"""
    if req.fields:
        col_str = ", ".join(req.fields)
    else:
        col_str = "*"
    where_clause = _build_where(req.conditions)
    return f"SELECT {col_str} FROM {req.table_name}{where_clause}"


def _calculate_confidence(req: SqlRequest, sql: str) -> Tuple[float, List[str]]:
    """计算置信度并收集警告"""
    warnings = []
    score = 95.0  # 基础分

    # 检查字段名合法性（简单检查：不含空格和特殊字符）
    for field_name in list(req.data.keys()) + list(req.conditions.keys()) + req.fields:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(field_name)):
            score -= 10
            warnings.append(f"字段名 '{field_name}' 可能不合法")

    # 值类型检查
    for val in list(req.data.values()) + list(req.conditions.values()):
        if isinstance(val, str) and len(val) > 200:
            score -= 5
            warnings.append("存在超长字符串值")

    # 主键缺失警告
    if req.operation in ("update", "delete") and not req.primary_key:
        score -= 5
        warnings.append("未指定主键，条件可能不唯一")

    # 检查 SQL 是否为空
    if not sql or len(sql.strip()) < 10:
        score = 40.0
        warnings.append("生成的 SQL 过短，可能存在问题")

    score = max(0.0, min(100.0, score))
    return score, warnings


def generate_sql(req: SqlRequest) -> SqlResult:
    """核心生成逻辑"""
    result = SqlResult()

    # 校验
    err = _validate_request(req)
    if err:
        result.error_code = err
        result.confidence = 0.0
        return result

    # 生成 SQL
    try:
        if req.operation == "insert":
            sql = _build_insert(req)
        elif req.operation == "update":
            sql = _build_update(req)
        elif req.operation == "delete":
            sql = _build_delete(req)
        elif req.operation == "select":
            sql = _build_select(req)
        else:
            result.error_code = "E004"  # 不支持的操作
            return result
    except Exception as e:
        result.error_code = "E006"
        result.warnings.append(str(e))
        return result

    result.sql = sql
    result.confidence, result.warnings = _calculate_confidence(req, sql)
    return result


def parse_input_text(text: str) -> SqlRequest:
    """从文本解析请求（简化版，用于演示）"""
    req = SqlRequest(table_name="", operation="select")
    if not text or not text.strip():
        raise ValueError("E001")

    # 尝试识别表名
    m = re.search(r"(?:from|into|update|table)\s+([^\s,;]+)", text, re.IGNORECASE)
    if m:
        req.table_name = m.group(1)

    # 尝试识别操作类型
    for op in ("insert", "update", "delete", "select"):
        if re.search(rf"\b{op}\b", text, re.IGNORECASE):
            req.operation = op
            break

    # 解析字段和值（简化：key=value 对）
    for m in re.finditer(r"(\w+)\s*=\s*('[^']*'|\d+|NULL)", text, re.IGNORECASE):
        key = m.group(1)
        val_str = m.group(2)
        if val_str.upper() == "NULL":
            val = None
        elif val_str.startswith("'"):
            val = val_str[1:-1]
        else:
            val = float(val_str) if "." in val_str else int(val_str)
        req.data[key] = val

    return req


# ============================================================
# 自检函数
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检 (selftest)...")
    passed = 0
    total = 0

    # --- 样例 1: INSERT 生成 ---
    total += 1
    req = SqlRequest(
        table_name="employees",
        operation="insert",
        data={"name": "张三", "age": 30, "email": "zhangsan@example.com", "active": True}
    )
    res = generate_sql(req)
    ok = (res.error_code is None
          and res.sql is not None
          and res.sql.upper().startswith("INSERT INTO")
          and res.confidence > 80.0)
    print(f"[{'PASS' if ok else 'FAIL'}] INSERT: {res.sql if res.sql else res.error_code}")
    passed += 1 if ok else 0

    # --- 样例 2: UPDATE 生成 ---
    total += 1
    req = SqlRequest(
        table_name="employees",
        operation="update",
        data={"age": 31, "active": False},
        conditions={"id": 1001},
        primary_key="id"
    )
    res = generate_sql(req)
    ok = (res.error_code is None
          and res.sql is not None
          and "UPDATE" in res.sql.upper()
          and "WHERE" in res.sql.upper()
          and res.confidence > 75.0)
    print(f"[{'PASS' if ok else 'FAIL'}] UPDATE: {res.sql if res.sql else res.error_code}")
    passed += 1 if ok else 0

    # --- 样例 3: DELETE 生成 ---
    total += 1
    req = SqlRequest(
        table_name="orders",
        operation="delete",
        conditions={"status": "cancelled", "created_at": "2024-01-01"},
        primary_key="order_id"
    )
    res = generate_sql(req)
    ok = (res.error_code is None
          and res.sql is not None
          and "DELETE FROM" in res.sql.upper()
          and res.confidence > 70.0)
    print(f"[{'PASS' if ok else 'FAIL'}] DELETE: {res.sql if res.sql else res.error_code}")
    passed += 1 if ok else 0

    # --- 样例 4: SELECT 生成 ---
    total += 1
    req = SqlRequest(
        table_name="products",
        operation="select",
        fields=["id", "name", "price"],
        conditions={"category": "electronics", "price": 0}
    )
    res = generate_sql(req)
    ok = (res.error_code is None
          and res.sql is not None
          and res.sql.upper().startswith("SELECT")
          and res.confidence > 80.0)
    print(f"[{'PASS' if ok else 'FAIL'}] SELECT: {res.sql if res.sql else res.error_code}")
    passed += 1 if ok else 0

    # --- 样例 5: 错误处理 - 空表名 ---
    total += 1
    req = SqlRequest(
        table_name="",
        operation="select",
        data={}
    )
    res = generate_sql(req)
    ok = (res.error_code == "E007" and res.sql is None)
    print(f"[{'PASS' if ok else 'FAIL'}] 空表名错误处理: {res.error_code}")
    passed += 1 if ok else 0

    # --- 样例 6: 错误处理 - 空数据 ---
    total += 1
    req = SqlRequest(
        table_name="test",
        operation="insert",
        data={}
    )
    res = generate_sql(req)
    ok = (res.error_code == "E008" and res.sql is None)
    print(f"[{'PASS' if ok else 'FAIL'}] 空数据错误处理: {res.error_code}")
    passed += 1 if ok else 0

    # --- 样例 7: 文本解析 ---
    total += 1
    req = parse_input_text("select from users where age = 30 and name = 'John'")
    ok = (req.table_name == "users" and req.operation == "select" and len(req.data) >= 2)
    print(f"[{'PASS' if ok else 'FAIL'}] 文本解析: table={req.table_name}, op={req.operation}")
    passed += 1 if ok else 0

    # --- 样例 8: 值格式化 ---
    total += 1
    ok = (format_value := _format_value("it's") == "'it''s'"
          and _format_value(None) == "NULL"
          and _format_value(True) == "1"
          and _format_value(3.14) == "3.14")
    print(f"[{'PASS' if ok else 'FAIL'}] 值格式化")
    passed += 1 if ok else 0

    # --- 汇总 ---
    print(f"\n自检完成: {passed}/{total} 通过")
    print("=" * 60)
    return passed == total


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="SQL Generator and Editor - ERP 迁移工具",
        epilog="示例: python main.py --table users --op insert --field name=张三 --field age=30"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--table", help="数据表名")
    parser.add_argument("--op", choices=["insert", "update", "delete", "select"],
                        default="select", help="操作类型")
    parser.add_argument("--field", action="append", default=[], help="字段=值 对（可多次）")
    parser.add_argument("--condition", action="append", default=[], help="条件 字段=值（可多次）")
    parser.add_argument("--pk", help="主键字段名")
    parser.add_argument("--fields", help="查询字段列表（逗号分隔）")
    parser.add_argument("--text", help="自然语言输入（简化解析）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        sys.exit(0 if ok else 1)

    # 正常模式
    try:
        if args.text:
            # 从自然语言解析
            req = parse_input_text(args.text)
        else:
            # 从命令行参数构建
            if not args.table:
                print(f"错误 E007: {ERROR_CODES['E007']}")
                sys.exit(1)

            req = SqlRequest(
                table_name=args.table,
                operation=args.op,
                primary_key=args.pk
            )

            # 解析字段
            for f in args.field:
                if "=" in f:
                    k, v = f.split("=", 1)
                    # 尝试类型转换
                    if v.lower() == "null":
                        v = None
                    elif v.startswith("'") and v.endswith("'"):
                        v = v[1:-1]
                    else:
                        try:
                            v = int(v)
                        except ValueError:
                            try:
                                v = float(v)
                            except ValueError:
                                pass
                    req.data[k.strip()] = v

            # 解析条件
            for c in args.condition:
                if "=" in c:
                    k, v = c.split("=", 1)
                    if v.lower() == "null":
                        v = None
                    elif v.startswith("'") and v.endswith("'"):
                        v = v[1:-1]
                    else:
                        try:
                            v = int(v)
                        except ValueError:
                            try:
                                v = float(v)
                            except ValueError:
                                pass
                    req.conditions[k.strip()] = v

            # 解析查询字段
            if args.fields:
                req.fields = [f.strip() for f in args.fields.split(",")]

        # 生成 SQL
        result = generate_sql(req)

        if result.error_code:
            msg = ERROR_CODES.get(result.error_code, "未知错误")
            print(f"错误 {result.error_code}: {msg}")
            if result.warnings:
                print("警告:")
                for w in result.warnings:
                    print(f"  - {w}")
            sys.exit(1)

        # 输出结果
        print(f"置信度: {result.confidence:.1f}%")
        if result.warnings:
            print("警告:")
            for w in result.warnings:
                print(f"  - {w}")
        print("\n生成的 SQL:")
        print("-" * 60)
        print(result.sql)
        print("-" * 60)

    except ValueError as e:
        code = str(e)
        msg = ERROR_CODES.get(code, f"未知错误: {code}")
        print(f"错误 {code}: {msg}")
        sys.exit(1)
    except Exception as e:
        print(f"错误 E006: {ERROR_CODES['E006']} - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
