#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spiral — 跨平台数据库客户端与 ERD 可视化操作脚本

本脚本为 clean-room 独立实现，仅依据功能规格编写。
支持 SQL/NoSQL 连接串解析、ERD 结构解析、查询结果格式化输出等核心逻辑。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_OK = 0
ERR_INVALID_ARGS = "E001"       # 命令行参数错误
ERR_INVALID_INPUT = "E002"      # 输入数据格式错误
ERR_PARSE_CONN = "E003"         # 连接串解析失败
ERR_PARSE_ERD = "E004"          # ERD 描述解析失败
ERR_PARSE_SQL = "E005"          # SQL 语句解析失败
ERR_UNSUPPORTED_DB = "E006"     # 不支持的数据库类型
ERR_MISSING_FIELD = "E007"      # 缺少必要字段
ERR_INVALID_TYPE = "E008"       # 数据类型不合法
ERR_EXPORT_FAIL = "E009"        # 导出结果失败
ERR_INTERNAL = "E010"           # 内部错误


# ============================================================
# 核心数据结构
# ============================================================

class DatabaseConnInfo:
    """数据库连接信息"""
    def __init__(self, db_type: str, host: str, port: int,
                 database: str, username: str, password: str):
        self.db_type = db_type.lower()
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password

    def to_dict(self) -> Dict[str, Any]:
        return {
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": self.password,
        }


class TableField:
    """表字段定义"""
    def __init__(self, name: str, data_type: str, primary_key: bool = False,
                 foreign_key: bool = False, nullable: bool = True):
        self.name = name
        self.data_type = data_type
        self.primary_key = primary_key
        self.foreign_key = foreign_key
        self.nullable = nullable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.data_type,
            "primary_key": self.primary_key,
            "foreign_key": self.foreign_key,
            "nullable": self.nullable,
        }


class TableSchema:
    """数据库表结构"""
    def __init__(self, name: str, fields: List[TableField]):
        self.name = name
        self.fields = fields

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.name,
            "fields": [f.to_dict() for f in self.fields],
        }


class ERDModel:
    """ERD 实体关系模型"""
    def __init__(self):
        self.tables: Dict[str, TableSchema] = {}
        self.relations: List[Tuple[str, str]] = []  # (父表, 子表)

    def add_table(self, table: TableSchema) -> None:
        self.tables[table.name] = table

    def add_relation(self, parent: str, child: str) -> None:
        if parent in self.tables and child in self.tables:
            self.relations.append((parent, child))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tables": [t.to_dict() for t in self.tables.values()],
            "relations": [{"parent": p, "child": c} for p, c in self.relations],
        }


# ============================================================
# 解析器：连接串、ERD、SQL
# ============================================================

def parse_connection_string(conn_str: str) -> DatabaseConnInfo:
    """
    解析数据库连接串。

    支持格式示例：
      mysql://user:pass@host:3306/dbname
      postgresql://user:pass@host:5432/dbname
      sqlite:///path/to/db.sqlite
      mongodb://user:pass@host:27017/dbname
      redis://user:pass@host:6379/0

    返回 DatabaseConnInfo 对象。
    """
    if not conn_str or not isinstance(conn_str, str):
        raise ValueError(ERR_PARSE_CONN)

    # 匹配 scheme://[user[:pass]@]host[:port]/path
    pattern = re.compile(
        r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://"
        r"(?:(?P<user>[^:@/\s]+)(?::(?P<pass>[^@/\s]*))?@)?"
        r"(?P<host>[^:/@\s]+)?"
        r"(?::(?P<port>\d+))?"
        r"(?:/(?P<path>[^?\s]*))?"
    )
    m = pattern.match(conn_str.strip())
    if not m:
        raise ValueError(ERR_PARSE_CONN)

    scheme = m.group("scheme").lower()
    user = m.group("user") or ""
    password = m.group("pass") or ""
    host = m.group("host") or "localhost"
    port_str = m.group("port")
    path = m.group("path") or ""

    # 数据库类型映射
    db_type_map = {
        "mysql": "mysql",
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "sqlite": "sqlite",
        "mongodb": "mongodb",
        "mongo": "mongodb",
        "redis": "redis",
    }
    if scheme not in db_type_map:
        raise ValueError(ERR_UNSUPPORTED_DB)

    db_type = db_type_map[scheme]

    # 端口默认值
    default_ports = {
        "mysql": 3306,
        "postgresql": 5432,
        "sqlite": 0,
        "mongodb": 27017,
        "redis": 6379,
    }
    try:
        port = int(port_str) if port_str else default_ports.get(db_type, 0)
    except ValueError:
        raise ValueError(ERR_PARSE_CONN)

    # SQLite 特殊处理：host 和 port 无效
    if db_type == "sqlite":
        host = "local"
        port = 0
        database = path

    return DatabaseConnInfo(db_type, host, port, path, user, password)


def parse_erd_text(erd_text: str) -> ERDModel:
    """
    解析 ERD 描述文本。

    支持格式：
      TABLE users (
        id INT PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(255) NOT NULL
      )
      TABLE orders (
        id INT PRIMARY KEY,
        user_id INT FOREIGN KEY REFERENCES users(id),
        amount DECIMAL(10,2)
      )

    返回 ERDModel 对象。
    """
    if not erd_text or not isinstance(erd_text, str):
        raise ValueError(ERR_PARSE_ERD)

    model = ERDModel()
    
    # 使用更健壮的正则表达式来匹配 TABLE 定义
    # 匹配 TABLE 关键字后跟表名和括号内容
    table_pattern = re.compile(
        r'\bTABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)',
        re.IGNORECASE | re.DOTALL
    )
    
    matches = list(table_pattern.finditer(erd_text))
    if not matches:
        raise ValueError(ERR_PARSE_ERD)
    
    # 第一遍：解析所有表结构
    for match in matches:
        table_name = match.group(1)
        fields_content = match.group(2)
        
        # 解析每个字段
        fields: List[TableField] = []
        # 按逗号分割字段（忽略括号内逗号）
        field_parts = _split_top_level(fields_content, ',')
        for part in field_parts:
            part = part.strip()
            if not part:
                continue
            field = _parse_field_definition(part)
            if field:
                fields.append(field)

        if not fields:
            raise ValueError(ERR_PARSE_ERD)

        model.add_table(TableSchema(table_name, fields))
    
    # 第二遍：建立关系
    for table in model.tables.values():
        for field in table.fields:
            if field.foreign_key:
                # 尝试从字段名推断关系（如 user_id -> users）
                ref_table = _infer_reference_table(field.name)
                if ref_table and ref_table in model.tables:
                    model.add_relation(ref_table, table.name)

    if not model.tables:
        raise ValueError(ERR_PARSE_ERD)

    return model


def _split_top_level(text: str, delimiter: str) -> List[str]:
    """按分隔符分割，忽略括号内的分隔符"""
    parts = []
    depth = 0
    current = []
    for ch in text:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == delimiter and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current))
    return parts


def _parse_field_definition(text: str) -> Optional[TableField]:
    """
    解析单个字段定义。

    支持格式：
      id INT PRIMARY KEY
      name VARCHAR(100)
      email VARCHAR(255) NOT NULL
      user_id INT FOREIGN KEY REFERENCES users(id)
    """
    text = text.strip()
    if not text:
        return None

    name_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", text)
    if not name_match:
        return None
    name = name_match.group(1)
    rest = text[name_match.end():].strip()

    # 提取数据类型
    type_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*\s*(?:\(\s*\d+(?:\s*,\s*\d+)?\s*\))?)", rest)
    data_type = type_match.group(1).strip() if type_match else "TEXT"

    # 检查约束
    upper_rest = rest.upper()
    primary_key = "PRIMARY KEY" in upper_rest
    foreign_key = "FOREIGN KEY" in upper_rest or "REFERENCES" in upper_rest
    nullable = "NOT NULL" not in upper_rest

    return TableField(name, data_type, primary_key, foreign_key, nullable)


def _infer_reference_table(field_name: str) -> Optional[str]:
    """从字段名推断引用的表名（如 user_id -> users）"""
    # 规则：xxx_id -> xxxs（简单复数化）
    if field_name.endswith("_id"):
        base = field_name[:-3]
        # 简单复数规则
        if base.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return base + "es"
        if base.endswith('y') and len(base) > 1 and base[-2] not in 'aeiou':
            return base[:-1] + "ies"
        return base + "s"
    return None


def parse_sql_query(sql: str) -> Dict[str, Any]:
    """
    解析 SQL 查询语句，提取表名、字段列表等信息。

    支持 SELECT 语句的简单解析。
    """
    if not sql or not isinstance(sql, str):
        raise ValueError(ERR_PARSE_SQL)

    sql_clean = sql.strip().rstrip(';').strip()
    upper_sql = sql_clean.upper()

    if not upper_sql.startswith("SELECT"):
        raise ValueError(ERR_PARSE_SQL)

    # 提取 SELECT 字段
    from_match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)", sql_clean, re.IGNORECASE)
    if not from_match:
        raise ValueError(ERR_PARSE_SQL)

    table_name = from_match.group(1)
    select_part = sql_clean[6:from_match.start()].strip()

    # 解析字段列表
    if select_part == "*":
        fields = ["*"]
    else:
        fields = []
        for item in _split_top_level(select_part, ','):
            item = item.strip()
            # 处理别名
            alias_match = re.search(r"\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)$", item, re.IGNORECASE)
            if alias_match:
                fields.append(alias_match.group(1))
            else:
                # 去除表名前缀
                if '.' in item:
                    fields.append(item.split('.')[-1].strip())
                else:
                    fields.append(item)

    # 提取 WHERE 条件（简化）
    where_clause = ""
    where_match = re.search(r"\bWHERE\s+(.+)", sql_clean, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1).strip()

    return {
        "table": table_name,
        "fields": fields,
        "where": where_clause,
        "query": sql_clean,
    }


# ============================================================
# 格式化输出
# ============================================================

def format_as_csv(data: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> str:
    """将数据格式化为 CSV 字符串"""
    if not data:
        return ""

    if fields is None:
        fields = list(data[0].keys())

    # 生成表头
    lines = [",".join(fields)]

    for row in data:
        values = []
        for f in fields:
            val = row.get(f, "")
            # 转义逗号和引号
            val_str = str(val) if val is not None else ""
            if ',' in val_str or '"' in val_str or '\n' in val_str:
                val_str = '"' + val_str.replace('"', '""') + '"'
            values.append(val_str)
        lines.append(",".join(values))

    return "\n".join(lines)


def format_as_json(data: Any) -> str:
    """将数据格式化为 JSON 字符串"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_as_markdown_table(data: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> str:
    """将数据格式化为 Markdown 表格"""
    if not data:
        return ""

    if fields is None:
        fields = list(data[0].keys())

    # 表头
    header = "| " + " | ".join(fields) + " |"
    separator = "| " + " | ".join(["---"] * len(fields)) + " |"
    lines = [header, separator]

    for row in data:
        values = [str(row.get(f, "")) for f in fields]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


# ============================================================
# 主流程
# ============================================================

def process_connection(conn_str: str) -> Dict[str, Any]:
    """处理数据库连接串解析"""
    try:
        info = parse_connection_string(conn_str)
        return {
            "status": "ok",
            "connection": info.to_dict(),
        }
    except ValueError as e:
        return {
            "status": "error",
            "error_code": str(e),
            "message": "连接串解析失败",
        }


def process_erd(erd_text: str) -> Dict[str, Any]:
    """处理 ERD 描述解析"""
    try:
        model = parse_erd_text(erd_text)
        return {
            "status": "ok",
            "erd": model.to_dict(),
        }
    except ValueError as e:
        return {
            "status": "error",
            "error_code": str(e),
            "message": "ERD 解析失败",
        }


def process_sql(sql: str, data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """处理 SQL 查询解析与结果格式化"""
    try:
        parsed = parse_sql_query(sql)
        result = {
            "status": "ok",
            "parsed": parsed,
        }
        if data is not None:
            result["data"] = data
            result["csv"] = format_as_csv(data, parsed["fields"])
            result["json"] = format_as_json(data)
            result["markdown"] = format_as_markdown_table(data, parsed["fields"])
        return result
    except ValueError as e:
        return {
            "status": "error",
            "error_code": str(e),
            "message": "SQL 解析失败",
        }


# ============================================================
# 自检（selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=== spiral selftest 开始 ===")

    # ---- 测试 1：连接串解析 ----
    print("\n[1] 连接串解析测试")
    conn_str = "mysql://user:pass@localhost:3306/mydb"
    info = parse_connection_string(conn_str)
    assert info.db_type == "mysql", f"数据库类型错误: {info.db_type}"
    assert info.host == "localhost", f"主机错误: {info.host}"
    assert info.port >= 3000, f"端口异常: {info.port}"
    assert info.database == "mydb", f"数据库名错误: {info.database}"
    print("  ✓ MySQL 连接串解析通过")

    conn_str2 = "mongodb://admin:secret@db.example.com:27017/prod"
    info2 = parse_connection_string(conn_str2)
    assert info2.db_type == "mongodb", f"数据库类型错误: {info2.db_type}"
    assert info2.port == 27017, f"MongoDB 端口错误: {info2.port}"
    print("  ✓ MongoDB 连接串解析通过")

    # ---- 测试 2：ERD 解析 ----
    print("\n[2] ERD 解析测试")
    erd_text = """
    TABLE users (
      id INT PRIMARY KEY,
      name VARCHAR(100),
      email VARCHAR(255) NOT NULL
    )
    TABLE orders (
      id INT PRIMARY KEY,
      user_id INT FOREIGN KEY REFERENCES users(id),
      amount DECIMAL(10,2)
    )
    """
    try:
        model = parse_erd_text(erd_text)
        assert "users" in model.tables, "缺少 users 表"
        assert "orders" in model.tables, "缺少 orders 表"
        users_table = model.tables["users"]
        assert len(users_table.fields) >= 3, f"users 表字段数异常: {len(users_table.fields)}"
        assert any(f.primary_key for f in users_table.fields), "users 表缺少主键"
        assert len(model.relations) >= 1, f"关系数异常: {len(model.relations)}"
        print("  ✓ ERD 解析通过，表数量:", len(model.tables), "关系数量:", len(model.relations))
    except Exception as e:
        print(f"  ✗ ERD 解析失败: {e}")
        print(f"    错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1

    # ---- 测试 3：SQL 解析 ----
    print("\n[3] SQL 解析测试")
    sql = "SELECT id, name, email FROM users WHERE id > 100"
    parsed = parse_sql_query(sql)
    assert parsed["table"] == "users", f"表名错误: {parsed['table']}"
    assert len(parsed["fields"]) >= 3, f"字段数异常: {parsed['fields']}"
    assert parsed["where"], "WHERE 条件缺失"
    print("  ✓ SQL 解析通过，字段:", parsed["fields"])

    # ---- 测试 4：格式化输出 ----
    print("\n[4] 格式化输出测试")
    sample_data = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob,test@example.com"},
    ]
    csv_out = format_as_csv(sample_data)
    assert "id,name,email" in csv_out, "CSV 表头错误"
    assert len(csv_out.split("\n")) >= 3, f"CSV 行数异常: {len(csv_out.split(chr(10)))}"
    print("  ✓ CSV 格式化通过")

    json_out = format_as_json(sample_data)
    json_parsed = json.loads(json_out)
    assert len(json_parsed) == 2, f"JSON 数据条数错误: {len(json_parsed)}"
    print("  ✓ JSON 格式化通过")

    md_out = format_as_markdown_table(sample_data)
    assert "| id |" in md_out, "Markdown 表头错误"
    assert "---" in md_out, "Markdown 分隔符错误"
    print("  ✓ Markdown 格式化通过")

    # ---- 测试 5：错误处理 ----
    print("\n[5] 错误处理测试")
    try:
        parse_connection_string("not-a-valid-conn")
        assert False, "应抛出异常但未抛出"
    except ValueError as e:
        assert str(e) == ERR_PARSE_CONN or str(e) == ERR_UNSUPPORTED_DB, f"错误码错误: {e}"
    print("  ✓ 连接串错误处理通过")

    try:
        parse_erd_text("")
        assert False, "应抛出异常但未抛出"
    except ValueError as e:
        assert str(e) == ERR_PARSE_ERD, f"错误码错误: {e}"
    print("  ✓ ERD 错误处理通过")

    print("\n=== spiral selftest 全部通过 ===")
    return ERR_OK


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="spiral — 跨平台数据库客户端与 ERD 可视化操作工具",
        epilog="示例: python main.py --conn 'mysql://user:pass@localhost:3306/db'"
    )

    parser.add_argument(
        "--conn", "-c",
        type=str,
        help="数据库连接串，如 mysql://user:pass@host:3306/dbname"
    )
    parser.add_argument(
        "--erd", "-e",
        type=str,
        help="ERD 描述文本（TABLE 定义）"
    )
    parser.add_argument(
        "--sql", "-s",
        type=str,
        help="SQL 查询语句"
    )
    parser.add_argument(
        "--data",
        type=str,
        help="JSON 格式的数据（与 --sql 配合使用）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 至少要有一个操作
    if not args.conn and not args.erd and not args.sql:
        parser.print_help()
        print(f"\n错误 [{ERR_INVALID_ARGS}]: 至少需要 --conn, --erd 或 --sql 之一", file=sys.stderr)
        return 1

    results: Dict[str, Any] = {"status": "ok"}

    # 处理连接串
    if args.conn:
        result = process_connection(args.conn)
        if result["status"] == "error":
            print(f"错误 [{result['error_code']}]: {result['message']}", file=sys.stderr)
            return 1
        results["connection"] = result["connection"]

    # 处理 ERD
    if args.erd:
        result = process_erd(args.erd)
        if result["status"] == "error":
            print(f"错误 [{result['error_code']}]: {result['message']}", file=sys.stderr)
            return 1
        results["erd"] = result["erd"]

    # 处理 SQL
    if args.sql:
        data = None
        if args.data:
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError:
                print(f"错误 [{ERR_INVALID_INPUT}]: --data 参数必须是合法 JSON", file=sys.stderr)
                return 1

        result = process_sql(args.sql, data)
        if result["status"] == "error":
            print(f"错误 [{result['error_code']}]: {result['message']}", file=sys.stderr)
            return 1
        results["sql"] = result["parsed"]
        if data is not None:
            if args.format == "csv":
                results["output"] = result["csv"]
            elif args.format == "markdown":
                results["output"] = result["markdown"]
            else:
                results["output"] = json.loads(result["json"])

    # 输出结果
    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.format == "csv" and "output" in results:
        print(results["output"])
    elif args.format == "markdown" and "output" in results:
        print(results["output"])
    else:
        # 默认输出 JSON
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return ERR_OK


if __name__ == "__main__":
    sys.exit(main())
