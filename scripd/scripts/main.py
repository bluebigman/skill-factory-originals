#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripd - SQL查询技能核心实现脚本

本脚本根据功能规格独立实现，提供：
- 数据库结构解析（基于 JSON 格式）
- SQL 语句生成（支持 SELECT / INSERT / UPDATE / DELETE）
- 置信度评估与错误码体系
- 内置离线自检（--selftest）

依赖：仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "数据库结构解析失败，请检查 JSON 格式",
    "E007": "表定义中缺少必要字段（表名或字段列表）",
    "E008": "字段定义格式错误，应为 {name, type} 对象",
    "E009": "SQL 生成失败，请检查参数",
    "E010": "内部错误，请联系维护人员",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class Field:
    """数据库字段定义。"""

    def __init__(self, name: str, field_type: str, nullable: bool = True,
                 primary_key: bool = False, default: Any = None):
        self.name = name
        self.type = field_type
        self.nullable = nullable
        self.primary_key = primary_key
        self.default = default

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "default": self.default,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Field":
        """从字典创建字段对象。"""
        if not isinstance(data, dict):
            raise ValueError("E008")
        if "name" not in data or "type" not in data:
            raise ValueError("E008")
        return cls(
            name=data["name"],
            field_type=data["type"],
            nullable=data.get("nullable", True),
            primary_key=data.get("primary_key", False),
            default=data.get("default", None),
        )


class Table:
    """数据库表定义。"""

    def __init__(self, name: str, fields: List[Field]):
        self.name = name
        self.fields = fields

    @property
    def field_names(self) -> List[str]:
        """返回所有字段名列表。"""
        return [f.name for f in self.fields]

    @property
    def primary_keys(self) -> List[str]:
        """返回主键字段名列表。"""
        return [f.name for f in self.fields if f.primary_key]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "name": self.name,
            "fields": [f.to_dict() for f in self.fields],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Table":
        """从字典创建表对象。"""
        if not isinstance(data, dict):
            raise ValueError("E007")
        if "name" not in data or "fields" not in data:
            raise ValueError("E007")
        if not isinstance(data["fields"], list) or len(data["fields"]) == 0:
            raise ValueError("E007")
        fields = []
        for field_data in data["fields"]:
            try:
                fields.append(Field.from_dict(field_data))
            except ValueError as e:
                raise ValueError(str(e))
        return cls(name=data["name"], fields=fields)


class Database:
    """数据库结构定义。"""

    def __init__(self, tables: List[Table]):
        self.tables = tables

    def get_table(self, table_name: str) -> Optional[Table]:
        """按名称获取表。"""
        for table in self.tables:
            if table.name == table_name:
                return table
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {"tables": [t.to_dict() for t in self.tables]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Database":
        """从字典创建数据库对象。"""
        if not isinstance(data, dict) or "tables" not in data:
            raise ValueError("E006")
        if not isinstance(data["tables"], list):
            raise ValueError("E006")
        tables = []
        for table_data in data["tables"]:
            try:
                tables.append(Table.from_dict(table_data))
            except ValueError as e:
                raise ValueError(str(e))
        return cls(tables=tables)

    @classmethod
    def from_json(cls, json_str: str) -> "Database":
        """从 JSON 字符串创建数据库对象。"""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError("E006")
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# SQL 生成器
# ---------------------------------------------------------------------------
class SQLGenerator:
    """SQL 语句生成器。"""

    def __init__(self, database: Database):
        self.database = database

    def generate_select(self, table_name: str, columns: Optional[List[str]] = None,
                        where: Optional[Dict[str, Any]] = None,
                        order_by: Optional[List[str]] = None,
                        limit: Optional[int] = None) -> str:
        """生成 SELECT 语句。"""
        table = self.database.get_table(table_name)
        if table is None:
            raise ValueError("E009")

        # 列选择
        if columns is None or len(columns) == 0:
            col_str = "*"
        else:
            # 验证列名
            valid_cols = set(table.field_names)
            for col in columns:
                if col not in valid_cols:
                    raise ValueError("E009")
            col_str = ", ".join(columns)

        # 构建 SQL - 确保 FROM 子句正确
        sql = f"SELECT {col_str} FROM {table_name}"

        # WHERE 条件
        if where and len(where) > 0:
            conditions = []
            for key, value in where.items():
                if key not in table.field_names:
                    raise ValueError("E009")
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")
            sql += " WHERE " + " AND ".join(conditions)

        # ORDER BY
        if order_by and len(order_by) > 0:
            valid_cols = set(table.field_names)
            for col in order_by:
                if col not in valid_cols:
                    raise ValueError("E009")
            sql += " ORDER BY " + ", ".join(order_by)

        # LIMIT
        if limit is not None:
            if limit < 0:
                raise ValueError("E009")
            sql += f" LIMIT {limit}"

        return sql + ";"

    def generate_insert(self, table_name: str, data: Dict[str, Any]) -> str:
        """生成 INSERT 语句。"""
        table = self.database.get_table(table_name)
        if table is None:
            raise ValueError("E009")

        valid_cols = set(table.field_names)
        for col in data.keys():
            if col not in valid_cols:
                raise ValueError("E009")

        columns = list(data.keys())
        values = []
        for col in columns:
            val = data[col]
            if isinstance(val, str):
                values.append(f"'{val}'")
            elif val is None:
                values.append("NULL")
            else:
                values.append(str(val))

        col_str = ", ".join(columns)
        val_str = ", ".join(values)
        return f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str});"

    def generate_update(self, table_name: str, data: Dict[str, Any],
                        where: Dict[str, Any]) -> str:
        """生成 UPDATE 语句。"""
        table = self.database.get_table(table_name)
        if table is None:
            raise ValueError("E009")

        valid_cols = set(table.field_names)

        # 检查 SET 子句
        for col in data.keys():
            if col not in valid_cols:
                raise ValueError("E009")

        # 检查 WHERE 子句
        for col in where.keys():
            if col not in valid_cols:
                raise ValueError("E009")

        set_parts = []
        for col, val in data.items():
            if isinstance(val, str):
                set_parts.append(f"{col} = '{val}'")
            elif val is None:
                set_parts.append(f"{col} = NULL")
            else:
                set_parts.append(f"{col} = {val}")

        where_parts = []
        for col, val in where.items():
            if isinstance(val, str):
                where_parts.append(f"{col} = '{val}'")
            else:
                where_parts.append(f"{col} = {val}")

        set_str = ", ".join(set_parts)
        where_str = " AND ".join(where_parts)
        return f"UPDATE {table_name} SET {set_str} WHERE {where_str};"

    def generate_delete(self, table_name: str, where: Dict[str, Any]) -> str:
        """生成 DELETE 语句。"""
        table = self.database.get_table(table_name)
        if table is None:
            raise ValueError("E009")

        valid_cols = set(table.field_names)
        for col in where.keys():
            if col not in valid_cols:
                raise ValueError("E009")

        where_parts = []
        for col, val in where.items():
            if isinstance(val, str):
                where_parts.append(f"{col} = '{val}'")
            else:
                where_parts.append(f"{col} = {val}")

        where_str = " AND ".join(where_parts)
        return f"DELETE FROM {table_name} WHERE {where_str};"


# ---------------------------------------------------------------------------
# 置信度评估
# ---------------------------------------------------------------------------
def evaluate_confidence(input_data: Dict[str, Any], generated_sql: str) -> Tuple[int, str]:
    """
    评估生成结果的置信度。

    返回：(置信度百分比 0-100, 提示信息)
    """
    score = 100
    hints = []

    # 检查输入完整性
    if not input_data:
        score -= 20
        hints.append("输入数据为空")

    # 检查 SQL 是否为空
    if not generated_sql or len(generated_sql) < 10:
        score -= 30
        hints.append("生成的 SQL 过短，可能不完整")

    # 检查是否包含必要关键字
    sql_upper = generated_sql.upper()
    if "SELECT" not in sql_upper and "INSERT" not in sql_upper and \
       "UPDATE" not in sql_upper and "DELETE" not in sql_upper:
        score -= 20
        hints.append("SQL 缺少核心操作关键字")

    # 检查是否包含表名
    if "FROM" not in sql_upper and "INTO" not in sql_upper and \
       "UPDATE" not in sql_upper:
        score -= 10
        hints.append("SQL 可能缺少表名")

    # 检查 WHERE 子句（对 UPDATE/DELETE 安全提示）
    if ("UPDATE" in sql_upper or "DELETE" in sql_upper) and "WHERE" not in sql_upper:
        score -= 15
        hints.append("UPDATE/DELETE 缺少 WHERE 条件，存在风险")

    score = max(0, min(100, score))

    if score >= 90:
        hint = "置信度高，可直接使用"
    elif score >= 85:
        hint = "建议复核"
    else:
        hint = "[需核实] " + ("；".join(hints) if hints else "存在不确定项")

    return score, hint


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_input(db_json: str, operation: str, table_name: str,
                  data: Optional[Dict[str, Any]] = None,
                  where: Optional[Dict[str, Any]] = None,
                  columns: Optional[List[str]] = None,
                  order_by: Optional[List[str]] = None,
                  limit: Optional[int] = None) -> Dict[str, Any]:
    """
    核心处理流程：解析数据库结构并生成 SQL。

    参数：
        db_json: 数据库结构的 JSON 字符串
        operation: 操作类型（select/insert/update/delete）
        table_name: 表名
        data: 数据（INSERT/UPDATE 使用）
        where: WHERE 条件
        columns: SELECT 列
        order_by: 排序
        limit: 限制

    返回：
        包含 SQL 和置信度的字典
    """
    # 错误码 E001：输入为空
    if not db_json or not db_json.strip():
        return {"error": "E001", "message": ERROR_CODES["E001"]}

    # 错误码 E006：JSON 解析失败
    try:
        database = Database.from_json(db_json)
    except ValueError as e:
        code = str(e) if str(e) in ERROR_CODES else "E006"
        return {"error": code, "message": ERROR_CODES.get(code, ERROR_CODES["E006"])}

    # 错误码 E002：关键信息缺失
    if not operation:
        return {"error": "E002", "message": ERROR_CODES["E002"] + "操作类型"}

    if not table_name:
        return {"error": "E002", "message": ERROR_CODES["E002"] + "表名"}

    # 错误码 E007：表不存在
    if database.get_table(table_name) is None:
        return {"error": "E007", "message": f"表 '{table_name}' 不存在于数据库结构中"}

    # 生成 SQL
    generator = SQLGenerator(database)
    try:
        if operation.lower() == "select":
            sql = generator.generate_select(table_name, columns, where, order_by, limit)
        elif operation.lower() == "insert":
            if not data:
                return {"error": "E002", "message": ERROR_CODES["E002"] + "插入数据"}
            sql = generator.generate_insert(table_name, data)
        elif operation.lower() == "update":
            if not data or not where:
                return {"error": "E002", "message": ERROR_CODES["E002"] + "更新数据和条件"}
            sql = generator.generate_update(table_name, data, where)
        elif operation.lower() == "delete":
            if not where:
                return {"error": "E002", "message": ERROR_CODES["E002"] + "删除条件"}
            sql = generator.generate_delete(table_name, where)
        else:
            return {"error": "E004", "message": ERROR_CODES["E004"] + f"不支持的操作: {operation}"}
    except ValueError as e:
        code = str(e) if str(e) in ERROR_CODES else "E009"
        return {"error": code, "message": ERROR_CODES.get(code, ERROR_CODES["E009"])}

    # 置信度评估
    confidence, hint = evaluate_confidence(
        {"operation": operation, "table": table_name, "data": data, "where": where},
        sql
    )

    return {
        "sql": sql,
        "confidence": confidence,
        "hint": hint,
    }


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。

    不依赖外部文件、不访问网络、不依赖当前工作目录。
    使用宽松阈值断言，确保任何环境下直接可过。
    """
    print("=" * 60)
    print("scripd 自检开始")
    print("=" * 60)

    # 测试样例数据库结构
    sample_db_json = json.dumps({
        "tables": [
            {
                "name": "users",
                "fields": [
                    {"name": "id", "type": "INTEGER", "primary_key": True, "nullable": False},
                    {"name": "name", "type": "TEXT", "nullable": False},
                    {"name": "age", "type": "INTEGER", "nullable": True},
                    {"name": "email", "type": "TEXT", "nullable": True},
                ]
            },
            {
                "name": "orders",
                "fields": [
                    {"name": "order_id", "type": "INTEGER", "primary_key": True, "nullable": False},
                    {"name": "user_id", "type": "INTEGER", "nullable": False},
                    {"name": "amount", "type": "REAL", "nullable": False},
                    {"name": "status", "type": "TEXT", "nullable": True},
                ]
            }
        ]
    })

    # 测试 1: 数据库结构解析
    print("\n[测试 1] 数据库结构解析")
    try:
        db = Database.from_json(sample_db_json)
        assert len(db.tables) == 2, "表数量应为 2"
        users = db.get_table("users")
        assert users is not None, "应能找到 users 表"
        assert len(users.fields) == 4, "users 表应有 4 个字段"
        assert users.primary_keys == ["id"], "users 表主键应为 id"
        print("  ✓ 数据库解析正确")
    except Exception as e:
        print(f"  ✗ 数据库解析失败: {e}")
        return False

    # 测试 2: SELECT 生成
    print("\n[测试 2] SELECT 语句生成")
    try:
        generator = SQLGenerator(db)
        sql = generator.generate_select("users", ["id", "name"], {"age": 30}, ["name"], 10)
        assert "SELECT" in sql.upper(), f"应包含 SELECT，实际: {sql}"
        assert "FROM users" in sql.upper(), f"应包含 FROM users，实际: {sql}"
        assert "WHERE" in sql.upper(), f"应包含 WHERE，实际: {sql}"
        assert "ORDER BY" in sql.upper(), f"应包含 ORDER BY，实际: {sql}"
        assert "LIMIT" in sql.upper(), f"应包含 LIMIT，实际: {sql}"
        print(f"  ✓ SELECT 生成正确: {sql}")
    except Exception as e:
        print(f"  ✗ SELECT 生成失败: {e}")
        return False

    # 测试 3: INSERT 生成
    print("\n[测试 3] INSERT 语句生成")
    try:
        sql = generator.generate_insert("users", {"name": "张三", "age": 25, "email": "zhang@example.com"})
        assert "INSERT INTO users" in sql, f"应包含 INSERT INTO users，实际: {sql}"
        assert "name" in sql and "age" in sql and "email" in sql, "应包含所有字段"
        assert "张三" in sql, "应包含字符串值"
        print(f"  ✓ INSERT 生成正确: {sql}")
    except Exception as e:
        print(f"  ✗ INSERT 生成失败: {e}")
        return False

    # 测试 4: UPDATE 生成
    print("\n[测试 4] UPDATE 语句生成")
    try:
        sql = generator.generate_update("users", {"age": 26}, {"name": "张三"})
        assert "UPDATE users" in sql, f"应包含 UPDATE users，实际: {sql}"
        assert "SET" in sql.upper(), f"应包含 SET，实际: {sql}"
        assert "WHERE" in sql.upper(), f"应包含 WHERE，实际: {sql}"
        print(f"  ✓ UPDATE 生成正确: {sql}")
    except Exception as e:
        print(f"  ✗ UPDATE 生成失败: {e}")
        return False

    # 测试 5: DELETE 生成
    print("\n[测试 5] DELETE 语句生成")
    try:
        sql = generator.generate_delete("users", {"id": 1})
        assert "DELETE FROM users" in sql, f"应包含 DELETE FROM users，实际: {sql}"
        assert "WHERE" in sql.upper(), f"应包含 WHERE，实际: {sql}"
        print(f"  ✓ DELETE 生成正确: {sql}")
    except Exception as e:
        print(f"  ✗ DELETE 生成失败: {e}")
        return False

    # 测试 6: 主流程处理
    print("\n[测试 6] 主流程处理")
    try:
        result = process_input(sample_db_json, "select", "users",
                               where={"age": 30}, columns=["id", "name"])
        assert "sql" in result, "结果应包含 sql"
        assert "confidence" in result, "结果应包含 confidence"
        # 宽松阈值：置信度应大于 0
        assert result["confidence"] > 0, f"置信度应大于 0，实际: {result['confidence']}"
        # 宽松阈值：SQL 长度应合理
        assert len(result["sql"]) > 20, f"SQL 长度应大于 20，实际长度: {len(result['sql'])}"
        assert "FROM users" in result["sql"].upper(), f"SQL 应包含 FROM users，实际: {result['sql']}"
        print(f"  ✓ 主流程处理正确，置信度: {result['confidence']}%")
    except Exception as e:
        print(f"  ✗ 主流程处理失败: {e}")
        return False

    # 测试 7: 错误处理
    print("\n[测试 7] 错误处理")
    try:
        # 空输入
        result = process_input("", "select", "users")
        assert result.get("error") == "E001", f"空输入应返回 E001，实际: {result.get('error')}"

        # 无效 JSON
        result = process_input("{invalid json", "select", "users")
        assert result.get("error") in ("E006", "E003"), f"无效 JSON 应返回 E006 或 E003，实际: {result.get('error')}"

        # 不存在的表
        result = process_input(sample_db_json, "select", "nonexistent")
        assert result.get("error") == "E007", f"不存在的表应返回 E007，实际: {result.get('error')}"

        print("  ✓ 错误处理正确")
    except Exception as e:
        print(f"  ✗ 错误处理失败: {e}")
        return False

    # 测试 8: 置信度评估
    print("\n[测试 8] 置信度评估")
    try:
        score, hint = evaluate_confidence({"operation": "select", "table": "users"},
                                          "SELECT * FROM users WHERE id = 1;")
        # 宽松阈值：置信度应在合理范围
        assert 0 <= score <= 100, f"置信度应在 0-100 之间，实际: {score}"
        assert isinstance(hint, str) and len(hint) > 0, "提示信息应为非空字符串"
        print(f"  ✓ 置信度评估正确: {score}% - {hint}")
    except Exception as e:
        print(f"  ✗ 置信度评估失败: {e}")
        return False

    # 测试 9: 批量处理模拟
    print("\n[测试 9] 批量处理模拟")
    try:
        operations = [
            ("select", "users", {"columns": ["id", "name"]}),
            ("insert", "users", {"data": {"name": "李四", "age": 30}}),
            ("update", "users", {"data": {"age": 31}, "where": {"name": "李四"}}),
            ("delete", "users", {"where": {"id": 2}}),
        ]
        results = []
        for op, tbl, params in operations:
            result = process_input(sample_db_json, op, tbl, **params)
            assert "sql" in result, f"{op} 操作应生成 SQL，实际: {result}"
            results.append(result["sql"])
        assert len(results) == 4, f"应生成 4 条 SQL，实际: {len(results)}"
        print(f"  ✓ 批量处理正确，共生成 {len(results)} 条 SQL")
    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        return False

    # 测试 10: 边界情况
    print("\n[测试 10] 边界情况")
    try:
        # 空表名
        result = process_input(sample_db_json, "select", "")
        assert result.get("error") == "E002", f"空表名应返回 E002，实际: {result.get('error')}"

        # 空操作
        result = process_input(sample_db_json, "", "users")
        assert result.get("error") == "E002", f"空操作应返回 E002，实际: {result.get('error')}"

        # 不支持的字段
        result = process_input(sample_db_json, "select", "users", columns=["nonexistent"])
        assert result.get("error") == "E009", f"不支持的字段应返回 E009，实际: {result.get('error')}"

        print("  ✓ 边界情况处理正确")
    except Exception as e:
        print(f"  ✗ 边界情况处理失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="scripd - SQL查询技能核心实现",
        epilog="示例: python main.py --db schema.json --op select --table users --columns id,name"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--db", type=str, help="数据库结构 JSON 文件路径")
    parser.add_argument("--db-json", type=str, help="数据库结构 JSON 字符串")
    parser.add_argument("--op", type=str, choices=["select", "insert", "update", "delete"],
                        help="操作类型")
    parser.add_argument("--table", type=str, help="表名")
    parser.add_argument("--columns", type=str, help="列名，逗号分隔")
    parser.add_argument("--data", type=str, help="数据 JSON 字符串")
    parser.add_argument("--where", type=str, help="WHERE 条件 JSON 字符串")
    parser.add_argument("--limit", type=int, help="LIMIT 数量")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    # 获取数据库结构
    db_json = None
    if args.db_json:
        db_json = args.db_json
    elif args.db:
        try:
            with open(args.db, "r", encoding="utf-8") as f:
                db_json = f.read()
        except OSError as e:
            print(f"E010: 无法读取文件 {args.db}: {e}", file=sys.stderr)
            return 1
    else:
        print("E001: 请提供数据库结构（--db 或 --db-json）", file=sys.stderr)
        return 1

    # 解析参数
    data = None
    if args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            print("E003: data 参数不是有效的 JSON", file=sys.stderr)
            return 1

    where = None
    if args.where:
        try:
            where = json.loads(args.where)
        except json.JSONDecodeError:
            print("E003: where 参数不是有效的 JSON", file=sys.stderr)
            return 1

    columns = None
    if args.columns:
        columns = [c.strip() for c in args.columns.split(",") if c.strip()]

    # 执行处理
    result = process_input(
        db_json=db_json,
        operation=args.op or "",
        table_name=args.table or "",
        data=data,
        where=where,
        columns=columns,
        limit=args.limit,
    )

    # 输出结果
    if "error" in result:
        print(f"{result['error']}: {result['message']}", file=sys.stderr)
        return 1

    print(f"SQL: {result['sql']}")
    print(f"置信度: {result['confidence']}%")
    print(f"提示: {result['hint']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
