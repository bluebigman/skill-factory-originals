#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spiral — 跨平台数据库客户端与 ERD 可视化操作（clean-room 独立实现）

本脚本仅依据功能规格实现核心逻辑，不含任何外部依赖。
支持 --selftest 参数进行离线自检。

错误码约定：
    E001 参数解析错误
    E002 未知命令或模式
    E003 连接配置校验失败
    E004 SQL 语句解析失败
    E005 NoSQL 操作失败
    E006 ERD 生成失败
    E007 数据导入导出失败
    E008 配置加密解密失败
    E009 自检断言失败
    E010 未预期的运行时错误
"""

import argparse
import json
import re
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 1. 数据模型与常量
# ============================================================

# 支持的数据库类型
SUPPORTED_DB_TYPES = ["mysql", "postgresql", "sqlite", "sqlserver", "mongodb", "redis"]

# 导出格式
EXPORT_FORMATS = ["csv", "json", "sql"]

# 连接配置最小字段要求
REQUIRED_CONN_FIELDS = {"name", "db_type", "host", "port", "database"}


class ConnectionConfig:
    """数据库连接配置对象"""

    def __init__(
        self,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str = "",
        password: str = "",
        group: str = "default",
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.db_type = db_type.lower()
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.group = group
        self.options = options or {}
        self.id = str(uuid.uuid4())
        self._validate()

    def _validate(self) -> None:
        """校验配置合法性，失败抛 ValueError（错误码 E003）"""
        if not self.name or not self.name.strip():
            raise ValueError("E003: 连接名称不能为空")
        if self.db_type not in SUPPORTED_DB_TYPES:
            raise ValueError(
                f"E003: 不支持的数据库类型 '{self.db_type}'，"
                f"支持: {', '.join(SUPPORTED_DB_TYPES)}"
            )
        if not self.host or not self.host.strip():
            raise ValueError("E003: 主机地址不能为空")
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ValueError("E003: 端口号必须在 1-65535 范围内")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（密码脱敏）"""
        return {
            "id": self.id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "group": self.group,
            "options": self.options,
            "password_masked": "******" if self.password else "",
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionConfig":
        """从字典创建配置对象"""
        try:
            return cls(
                name=data["name"],
                db_type=data["db_type"],
                host=data["host"],
                port=data["port"],
                database=data["database"],
                username=data.get("username", ""),
                password=data.get("password", ""),
                group=data.get("group", "default"),
                options=data.get("options"),
            )
        except KeyError as exc:
            raise ValueError(f"E003: 配置缺少必要字段: {exc}") from exc


class TableSchema:
    """表结构定义"""

    def __init__(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        primary_key: Optional[str] = None,
        foreign_keys: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        self.table_name = table_name
        self.columns = columns  # [{"name": str, "type": str, "nullable": bool, "default": Any}]
        self.primary_key = primary_key
        self.foreign_keys = foreign_keys or []  # [{"column": str, "ref_table": str, "ref_column": str}]
        self._validate()

    def _validate(self) -> None:
        """校验表结构合法性"""
        if not self.table_name or not self.table_name.strip():
            raise ValueError("E004: 表名不能为空")
        if not self.columns:
            raise ValueError(f"E004: 表 '{self.table_name}' 没有定义任何列")
        col_names = [c["name"] for c in self.columns]
        if len(col_names) != len(set(col_names)):
            raise ValueError(f"E004: 表 '{self.table_name}' 存在重复列名")
        if self.primary_key and self.primary_key not in col_names:
            raise ValueError(f"E004: 主键 '{self.primary_key}' 不在列定义中")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "table_name": self.table_name,
            "columns": self.columns,
            "primary_key": self.primary_key,
            "foreign_keys": self.foreign_keys,
        }


# ============================================================
# 2. 核心逻辑模块
# ============================================================


class SQLParser:
    """SQL 语句解析器（简化版，用于语法检查与语句拆分）"""

    @staticmethod
    def split_statements(sql_text: str) -> List[str]:
        """
        将多语句 SQL 文本拆分为单条语句列表。
        处理引号内的分号，支持单引号、双引号、反引号。
        """
        if not sql_text or not sql_text.strip():
            return []

        statements = []
        current = []
        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        i = 0

        while i < len(sql_text):
            ch = sql_text[i]

            # 处理转义字符
            if ch == "\\" and i + 1 < len(sql_text):
                current.append(ch)
                current.append(sql_text[i + 1])
                i += 2
                continue

            # 切换引号状态
            if ch == "'" and not in_double_quote and not in_backtick:
                in_single_quote = not in_single_quote
            elif ch == '"' and not in_single_quote and not in_backtick:
                in_double_quote = not in_double_quote
            elif ch == "`" and not in_single_quote and not in_double_quote:
                in_backtick = not in_backtick

            # 遇到分号且不在引号内 -> 语句结束
            if ch == ";" and not in_single_quote and not in_double_quote and not in_backtick:
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue

            current.append(ch)
            i += 1

        # 处理最后一条语句（无分号结尾）
        last_stmt = "".join(current).strip()
        if last_stmt:
            statements.append(last_stmt)

        return statements

    @staticmethod
    def is_select(sql: str) -> bool:
        """判断是否为 SELECT 查询语句"""
        cleaned = sql.strip().lstrip("(").strip().upper()
        return cleaned.startswith("SELECT")

    @staticmethod
    def extract_table_names(sql: str) -> List[str]:
        """从 SQL 中提取表名（简化实现）"""
        # 匹配 FROM 或 JOIN 后的表名
        pattern = r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.findall(pattern, sql, re.IGNORECASE)
        return list(dict.fromkeys(matches))  # 去重保序


class NoSQLClient:
    """NoSQL 数据操作模拟器（内存实现）"""

    def __init__(self) -> None:
        self._stores: Dict[str, Dict[str, Any]] = {}

    def create_collection(self, db_name: str, collection: str) -> bool:
        """创建集合"""
        key = f"{db_name}.{collection}"
        if key not in self._stores:
            self._stores[key] = {}
        return True

    def insert_document(self, db_name: str, collection: str, document: Dict[str, Any]) -> str:
        """插入文档，返回文档 ID"""
        key = f"{db_name}.{collection}"
        if key not in self._stores:
            self.create_collection(db_name, collection)
        doc_id = str(uuid.uuid4())
        doc = dict(document)
        doc["_id"] = doc_id
        self._stores[key][doc_id] = doc
        return doc_id

    def find_documents(self, db_name: str, collection: str, query: Optional[Dict] = None) -> List[Dict]:
        """查询文档"""
        key = f"{db_name}.{collection}"
        if key not in self._stores:
            return []
        docs = list(self._stores[key].values())
        if not query:
            return docs
        # 简单等值匹配
        result = []
        for doc in docs:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                result.append(doc)
        return result

    def update_document(self, db_name: str, collection: str, doc_id: str, updates: Dict[str, Any]) -> bool:
        """更新文档"""
        key = f"{db_name}.{collection}"
        if key not in self._stores or doc_id not in self._stores[key]:
            return False
        self._stores[key][doc_id].update(updates)
        return True

    def delete_document(self, db_name: str, collection: str, doc_id: str) -> bool:
        """删除文档"""
        key = f"{db_name}.{collection}"
        if key not in self._stores or doc_id not in self._stores[key]:
            return False
        del self._stores[key][doc_id]
        return True


class ERDGenerator:
    """ERD 图生成器（输出 DOT 格式描述）"""

    @staticmethod
    def generate(tables: List[TableSchema]) -> str:
        """
        根据表结构生成 ERD 描述（DOT 语言格式）。
        返回的字符串可直接用于 Graphviz 渲染。
        """
        if not tables:
            raise ValueError("E006: 没有可生成 ERD 的表")

        lines = ["digraph ERD {"]
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=record, fontname=\"Helvetica\"];")

        # 生成表节点
        for table in tables:
            cols = []
            for col in table.columns:
                col_def = f"<{col['name']}> {col['name']}: {col['type']}"
                if table.primary_key and col["name"] == table.primary_key:
                    col_def += " [PK]"
                cols.append(col_def)
            label = " | ".join(cols)
            lines.append(f'    "{table.table_name}" [label="{{{label}}}"];')

        # 生成外键关系
        for table in tables:
            for fk in table.foreign_keys:
                src = f'"{table.table_name}":{fk["column"]}'
                dst = f'"{fk["ref_table"]}":{fk["ref_column"]}'
                lines.append(f"    {src} -> {dst} [color=blue, label=\"FK\"];")

        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def count_relationships(tables: List[TableSchema]) -> int:
        """统计外键关系数量"""
        return sum(len(t.fk_count() if hasattr(t, 'fk_count') else t.foreign_keys) for t in tables)


class DataExporter:
    """数据导出模块"""

    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]]) -> str:
        """导出为 CSV 格式字符串"""
        if not data:
            return ""
        headers = list(data[0].keys())
        lines = [",".join(headers)]
        for row in data:
            values = []
            for h in headers:
                v = row.get(h, "")
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                values.append(str(v).replace(",", "\\,"))
            lines.append(",".join(values))
        return "\n".join(lines)

    @staticmethod
    def export_to_json(data: List[Dict[str, Any]]) -> str:
        """导出为 JSON 格式字符串"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def export_to_sql(data: List[Dict[str, Any]], table_name: str = "exported_data") -> str:
        """导出为 SQL INSERT 语句"""
        if not data:
            return f"-- 无数据可导出到表 {table_name}"
        columns = list(data[0].keys())
        col_str = ", ".join(columns)
        lines = [f"INSERT INTO {table_name} ({col_str}) VALUES"]
        values_list = []
        for row in data:
            values = []
            for c in columns:
                v = row.get(c, "")
                if isinstance(v, str):
                    v = v.replace("'", "''")
                    values.append(f"'{v}'")
                elif v is None:
                    values.append("NULL")
                else:
                    values.append(str(v))
            values_list.append("(" + ", ".join(values) + ")")
        lines.append(",\n".join(values_list) + ";")
        return "\n".join(lines)

    @staticmethod
    def export(data: List[Dict[str, Any]], fmt: str, table_name: str = "exported_data") -> str:
        """统一导出入口"""
        if fmt not in EXPORT_FORMATS:
            raise ValueError(f"E007: 不支持的导出格式 '{fmt}'，支持: {', '.join(EXPORT_FORMATS)}")
        if fmt == "csv":
            return DataExporter.export_to_csv(data)
        elif fmt == "json":
            return DataExporter.export_to_json(data)
        else:  # sql
            return DataExporter.export_to_sql(data, table_name)


class ConfigManager:
    """连接配置管理（加密存储模拟）"""

    @staticmethod
    def encrypt(plain_text: str, key: str = "spiral-master-key") -> str:
        """简单加密（生产环境应使用更安全的算法）"""
        result = []
        for i, ch in enumerate(plain_text):
            result.append(chr(ord(ch) + (i % 7) + len(key)))
        return "".join(result)

    @staticmethod
    def decrypt(cipher_text: str, key: str = "spiral-master-key") -> str:
        """解密"""
        result = []
        for i, ch in enumerate(cipher_text):
            result.append(chr(ord(ch) - (i % 7) - len(key)))
        return "".join(result)

    @staticmethod
    def save_config(configs: List[ConnectionConfig], file_path: str) -> None:
        """保存配置到文件"""
        data = []
        for cfg in configs:
            cfg_dict = cfg.to_dict()
            # 加密密码
            if cfg.password:
                cfg_dict["password_encrypted"] = ConfigManager.encrypt(cfg.password)
            else:
                cfg_dict["password_encrypted"] = ""
            del cfg_dict["password_masked"]
            data.append(cfg_dict)
        try:
            with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise ValueError(f"E008: 保存配置失败: {exc}") from exc

    @staticmethod
    def load_config(file_path: str) -> List[ConnectionConfig]:
        """从文件加载配置"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"E008: 加载配置失败: {exc}") from exc

        configs = []
        for item in data:
            try:
                cfg = ConnectionConfig.from_dict(item)
                # 解密密码
                enc_pwd = item.get("password_encrypted", "")
                if enc_pwd:
                    cfg.password = ConfigManager.decrypt(enc_pwd)
                configs.append(cfg)
            except ValueError as exc:
                # 跳过无效配置
                continue
        return configs


# ============================================================
# 3. 主应用类
# ============================================================


class SpiralApp:
    """spiral 主应用"""

    def __init__(self) -> None:
        self.configs: List[ConnectionConfig] = []
        self.no_sql_client = NoSQLClient()
        self.current_config: Optional[ConnectionConfig] = None

    def add_connection(self, config: ConnectionConfig) -> str:
        """添加连接配置"""
        self.configs.append(config)
        return config.id

    def list_connections(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出连接配置"""
        result = []
        for cfg in self.configs:
            if group and cfg.group != group:
                continue
            result.append(cfg.to_dict())
        return result

    def connect(self, config_id: str) -> bool:
        """模拟建立数据库连接"""
        for cfg in self.configs:
            if cfg.id == config_id:
                self.current_config = cfg
                return True
        return False

    def disconnect(self) -> None:
        """断开当前连接"""
        self.current_config = None

    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """执行 SQL 语句（模拟）"""
        if not self.current_config:
            raise ValueError("E003: 未建立数据库连接")

        statements = SQLParser.split_statements(sql)
        if not statements:
            raise ValueError("E004: SQL 语句为空")

        results = []
        for stmt in statements:
            if SQLParser.is_select(stmt):
                tables = SQLParser.extract_table_names(stmt)
                # 模拟返回数据
                results.append({
                    "type": "SELECT",
                    "tables": tables,
                    "row_count": 0,
                    "columns": [],
                    "data": [],
                })
            else:
                results.append({
                    "type": "EXECUTE",
                    "affected_rows": 0,
                })
        return {"statements": len(statements), "results": results}

    def generate_erd(self, db_name: str) -> str:
        """生成指定数据库的 ERD"""
        if not self.current_config:
            raise ValueError("E003: 未建立数据库连接")

        # 模拟从数据库读取表结构
        tables = self._mock_get_tables(db_name)
        if not tables:
            raise ValueError(f"E006: 数据库 '{db_name}' 中没有表")

        return ERDGenerator.generate(tables)

    def _mock_get_tables(self, db_name: str) -> List[TableSchema]:
        """模拟从数据库读取表结构（实际实现应查询 information_schema）"""
        # 生成一些示例表
        users = TableSchema(
            table_name="users",
            columns=[
                {"name": "id", "type": "INT", "nullable": False, "default": None},
                {"name": "username", "type": "VARCHAR(50)", "nullable": False, "default": None},
                {"name": "email", "type": "VARCHAR(100)", "nullable": True, "default": None},
            ],
            primary_key="id",
        )
        orders = TableSchema(
            table_name="orders",
            columns=[
                {"name": "id", "type": "INT", "nullable": False, "default": None},
                {"name": "user_id", "type": "INT", "nullable": False, "default": None},
                {"name": "amount", "type": "DECIMAL(10,2)", "nullable": False, "default": 0},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": True, "default": None},
            ],
            primary_key="id",
            foreign_keys=[
                {"column": "user_id", "ref_table": "users", "ref_column": "id"},
            ],
        )
        return [users, orders]


# ============================================================
# 4. 自检模块
# ============================================================


def run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。
    返回 0 表示全部通过，非 0 表示有失败项。
    """
    print("=" * 60)
    print("spiral 自检开始（离线模式）")
    print("=" * 60)

    failures = 0

    # --- 测试 1: SQL 语句拆分 ---
    print("\n[1/6] 测试 SQL 语句拆分...")
    sql_text = "SELECT * FROM users; SELECT id, name FROM orders WHERE id = 1;"
    stmts = SQLParser.split_statements(sql_text)
    assert len(stmts) == 2, f"E009: 期望 2 条语句，实际 {len(stmts)}"
    assert "SELECT * FROM users" in stmts[0], "E009: 第一条语句内容不正确"
    assert "SELECT id, name FROM orders" in stmts[1], "E009: 第二条语句内容不正确"
    # 引号内分号不应拆分
    quoted_sql = "SELECT 'a;b' AS x; SELECT 1;"
    stmts2 = SQLParser.split_statements(quoted_sql)
    assert len(stmts2) == 2, f"E009: 引号内分号被错误拆分，实际 {len(stmts2)} 条"
    print("  PASS")

    # --- 测试 2: 连接配置 ---
    print("\n[2/6] 测试连接配置管理...")
    cfg = ConnectionConfig(
        name="dev-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database="mydb",
        username="root",
        password="secret123",
        group="dev",
    )
    assert cfg.db_type == "mysql", "E009: 数据库类型错误"
    assert cfg.port == 3306, "E009: 端口错误"
    assert cfg.password == "secret123", "E009: 密码保存错误"
    # 测试无效配置
    try:
        ConnectionConfig(name="", db_type="mysql", host="h", port=1, database="d")
        assert False, "E009: 空名称应抛出异常"
    except ValueError as e:
        assert "E003" in str(e), f"E009: 错误码应为 E003，实际: {e}"
    print("  PASS")

    # --- 测试 3: 加密解密 ---
    print("\n[3/6] 测试配置加密...")
    original = "SuperSecretPassword123!"
    encrypted = ConfigManager.encrypt(original)
    decrypted = ConfigManager.decrypt(encrypted)
    assert encrypted != original, "E009: 加密后不应等于原文"
    assert decrypted == original, "E009: 解密结果应与原文一致"
    print("  PASS")

    # --- 测试 4: NoSQL 操作 ---
    print("\n[4/6] 测试 NoSQL 数据操作...")
    client = NoSQLClient()
    doc_id = client.insert_document("testdb", "users", {"name": "Alice", "age": 30})
    assert doc_id, "E009: 插入文档应返回 ID"
    docs = client.find_documents("testdb", "users", {"name": "Alice"})
    assert len(docs) == 1, f"E009: 期望 1 条文档，实际 {len(docs)}"
    assert docs[0]["age"] == 30, "E009: 文档字段值错误"
    # 更新
    updated = client.update_document("testdb", "users", doc_id, {"age": 31})
    assert updated, "E009: 更新文档应成功"
    docs = client.find_documents("testdb", "users", {"name": "Alice"})
    assert docs[0]["age"] == 31, "E009: 更新后字段值错误"
    # 删除
    deleted = client.delete_document("testdb", "users", doc_id)
    assert deleted, "E009: 删除文档应成功"
    docs = client.find_documents("testdb", "users")
    assert len(docs) == 0, f"E009: 删除后应无文档，实际 {len(docs)}"
    print("  PASS")

    # --- 测试 5: ERD 生成 ---
    print("\n[5/6] 测试 ERD 生成...")
    tables = [
        TableSchema(
            table_name="users",
            columns=[
                {"name": "id", "type": "INT", "nullable": False, "default": None},
                {"name": "name", "type": "VARCHAR", "nullable": True, "default": None},
            ],
            primary_key="id",
        ),
        TableSchema(
            table_name="orders",
            columns=[
                {"name": "id", "type": "INT", "nullable": False, "default": None},
                {"name": "user_id", "type": "INT", "nullable": False, "default": None},
            ],
            primary_key="id",
            foreign_keys=[{"column": "user_id", "ref_table": "users", "ref_column": "id"}],
        ),
    ]
    erd = ERDGenerator.generate(tables)
    assert "digraph ERD" in erd, "E009: ERD 应包含 digraph 声明"
    assert "users" in erd and "orders" in erd, "E009: ERD 应包含所有表名"
    assert "->" in erd, "E009: ERD 应包含关系连线"
    print("  PASS")

    # --- 测试 6: 数据导出 ---
    print("\n[6/6] 测试数据导出...")
    sample_data = [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False},
    ]
    csv_out = DataExporter.export(sample_data, "csv")
    assert "id,name,active" in csv_out, "E009: CSV 应包含表头"
    assert "Alice" in csv_out and "Bob" in csv_out, "E009: CSV 应包含数据行"

    json_out = DataExporter.export(sample_data, "json")
    parsed = json.loads(json_out)
    assert len(parsed) == 2, "E009: JSON 解析后应有 2 条记录"
    assert parsed[0]["name"] == "Alice", "E009: JSON 数据内容错误"

    sql_out = DataExporter.export(sample_data, "sql", "test_table")
    assert "INSERT INTO test_table" in sql_out, "E009: SQL 导出应包含 INSERT 语句"
    assert "Alice" in sql_out, "E009: SQL 导出应包含数据值"
    print("  PASS")

    # --- 汇总 ---
    print("\n" + "=" * 60)
    if failures == 0:
        print("所有自检项通过 ✅")
        print("=" * 60)
        return 0
    else:
        print(f"自检失败: {failures} 项未通过 ❌")
        print("=" * 60)
        return 1


# ============================================================
# 5. 命令行入口
# ============================================================


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="spiral",
        description="跨平台数据库客户端与 ERD 可视化工具",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="spiral 1.0.2",
    )
    return parser


def main() -> int:
    """主入口函数"""
    parser = build_parser()
    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        parser.add_argument("--force", action="store_true")  # R4 强制写盘

        parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
        args = parser.parse_args()
        global dry_run
        dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    except SystemExit as e:
        # argparse 在 --help 或 --version 时会抛出 SystemExit
        if e.code == 0:
            return 0
        return 1

    try:
        if args.selftest:
            return run_selftest()
        else:
            # 无参数时打印帮助信息
            parser.print_help()
            return 0
    except AssertionError as exc:
        print(f"E009: 自检断言失败: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底异常处理
        print(f"E010: 未预期的错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
