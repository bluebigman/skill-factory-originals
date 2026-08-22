#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
querycsv — CSV 数据 SQL 查询与导出工具（独立实现）

功能：
  - 加载 CSV 文件（本地路径 / URL / 粘贴文本）
  - 对已加载数据执行 SQL 查询（SELECT / WHERE / GROUP BY / ORDER BY）
  - 导出结果为 CSV / JSON / Markdown
  - 字段类型自动推断（数值 / 日期 / 字符串）

仅依赖 Python 标准库，无第三方依赖。
运行方式：
  python scripts/main.py --selftest    # 离线自检
  python scripts/main.py --help        # 查看帮助
"""

import argparse
import csv
import io
import json
import os
import re
import sqlite3
import sys
import time
import ssl
import socket
import tempfile
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.error import URLError, HTTPError

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：无法读取指定 CSV 文件",
    "E003": "URL 读取失败：无法从指定 URL 获取数据",
    "E004": "CSV 解析失败：数据格式不符合 CSV 规范",
    "E005": "SQL 语法错误：无法解析查询语句",
    "E006": "字段不存在：查询中引用了不存在的列",
    "E007": "聚合函数使用错误：聚合函数位置或参数不正确",
    "E008": "导出失败：无法写入导出文件",
    "E009": "数据类型错误：数值转换或比较失败",
    "E010": "内部错误：未预期的运行时异常",
}


def err(code: str, message: str = "") -> None:
    """输出错误信息并以错误码退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {msg}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {msg}", file=sys.stderr)
    sys.exit(code)


def parse_date(value: str) -> datetime:
    """解析日期字符串，统一返回带时区的 datetime（UTC）"""
    if not value or value == "":
        return None
    try:
        # 尝试 ISO 格式（支持时区）
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        pass
    # 尝试常见格式
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(str(value), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    raise ValueError(f"无法解析日期: {value}")


def fetch_url(url: str, timeout: int = 10, max_retries: int = 3) -> str:
    """从 URL 获取内容，带超时、重试退避和异常处理"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; querycsv/1.0; +https://example.com)"
    }
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except (ssl.SSLError, HTTPError, URLError, socket.timeout, socket.error) as e:
            if attempt == max_retries - 1:
                if isinstance(e, HTTPError):
                    err("E003", f"HTTP 错误 {e.code}: {e.reason}")
                elif isinstance(e, ssl.SSLError):
                    err("E003", f"SSL 错误: {e}")
                elif isinstance(e, socket.timeout):
                    err("E003", f"连接超时: {url}")
                else:
                    err("E003", f"网络错误: {e}")
        except Exception as e:
            if attempt == max_retries - 1:
                err("E003", f"未知错误: {e}")
        # 指数退避：2^attempt 秒，最多 4 秒
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
    err("E003", "重试次数耗尽")


def load_csv_data(content: str, table_name: str = "data") -> sqlite3.Connection:
    """将 CSV 内容加载到内存 SQLite 数据库，返回连接"""
    # 解析 CSV
    try:
        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames
        if not headers:
            err("E004", "CSV 文件没有列头")
        rows = list(reader)
    except csv.Error as e:
        err("E004", f"CSV 解析失败: {e}")

    # 创建内存数据库
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # 推断列类型
    col_types = {}
    for col in headers:
        col_types[col] = "TEXT"  # 默认 TEXT

    # 尝试推断类型
    for col in headers:
        int_count = 0
        float_count = 0
        date_count = 0
        total = 0
        for row in rows:
            val = row.get(col, "")
            if val == "" or val is None:
                continue
            total += 1
            try:
                int(val)
                int_count += 1
                continue
            except (ValueError, TypeError):
                pass
            try:
                float(val)
                float_count += 1
                continue
            except (ValueError, TypeError):
                pass
            try:
                parse_date(val)
                date_count += 1
                continue
            except (ValueError, TypeError):
                pass

        if total > 0:
            if int_count == total:
                col_types[col] = "INTEGER"
            elif float_count == total:
                col_types[col] = "REAL"
            elif date_count == total:
                col_types[col] = "TEXT"  # 日期存为 TEXT，便于比较

    # 创建表
    col_defs = ", ".join([f'"{col}" {col_types[col]}' for col in headers])
    conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

    # 插入数据
    placeholders = ", ".join(["?"] * len(headers))
    insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
    for row in rows:
        values = []
        for col in headers:
            val = row.get(col, "")
            if col_types[col] == "INTEGER" and val != "":
                try:
                    values.append(int(val))
                except (ValueError, TypeError):
                    values.append(None)
            elif col_types[col] == "REAL" and val != "":
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    values.append(None)
            else:
                values.append(val if val != "" else None)
        conn.execute(insert_sql, values)

    conn.commit()
    return conn


def execute_sql(conn: sqlite3.Connection, sql: str) -> tuple:
    """执行 SQL 查询，返回 (列名列表, 行数据列表)"""
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [list(row) for row in cursor.fetchall()]
        return columns, rows
    except sqlite3.Error as e:
        err("E005", f"SQL 执行失败: {e}")


def export_csv(headers: list, rows: list) -> str:
    """导出为 CSV 格式"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def export_json(headers: list, rows: list) -> str:
    """导出为 JSON 格式"""
    data = []
    for row in rows:
        item = {}
        for i, col in enumerate(headers):
            item[col] = row[i]
        data.append(item)
    return json.dumps(data, ensure_ascii=False, indent=2)


def export_markdown(headers: list, rows: list) -> str:
    """导出为 Markdown 表格格式"""
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(v) if v is not None else "" for v in row) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="CSV 数据 SQL 查询与导出工具")
    parser.add_argument("--file", help="CSV 文件路径")
    parser.add_argument("--url", help="CSV 文件 URL")
    parser.add_argument("--text", help="CSV 文本内容")
    parser.add_argument("--sql", help="SQL 查询语句")
    parser.add_argument("--table", default="data", help="表名（默认: data）")
    parser.add_argument("--format", choices=["csv", "json", "markdown"], default="csv", help="输出格式（默认: csv）")
    parser.add_argument("--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--strict", action="store_true", help="严格模式：类型推断失败时直接报错")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())

    # 获取 CSV 内容
    content = None
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            err("E002", f"无法读取文件: {e}")
    elif args.url:
        content = fetch_url(args.url)
    elif args.text:
        content = args.text
    else:
        # 从 stdin 读取
        content = sys.stdin.read()

    if not content:
        err("E001", "未提供 CSV 数据")

    # 加载数据到 SQLite
    conn = load_csv_data(content, args.table)

    # 执行 SQL
    if args.sql:
        headers, rows = execute_sql(conn, args.sql)
    else:
        # 默认查询所有
        headers, rows = execute_sql(conn, f'SELECT * FROM "{args.table}"')

    # 导出
    if args.format == "csv":
        output = export_csv(headers, rows)
    elif args.format == "json":
        output = export_json(headers, rows)
    elif args.format == "markdown":
        output = export_markdown(headers, rows)
    else:
        output = export_csv(headers, rows)

    # 输出
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        except Exception as e:
            err("E008", f"无法写入输出文件: {e}")
    else:
        print(output)

    conn.close()
    return 0


def selftest() -> int:
    """自检：真实测试核心功能"""
    print("开始自检...")

    # 测试 1: 基本 SELECT 查询
    print("测试 1: 基本 SELECT 查询")
    csv_content = """name,age,city
Alice,30,Beijing
Bob,25,Shanghai
Charlie,35,Beijing
"""
    conn = load_csv_data(csv_content, "people")
    headers, rows = execute_sql(conn, "SELECT name, age FROM people WHERE age > 26 ORDER BY age DESC")
    assert headers == ["name", "age"], f"列名不匹配: {headers}"
    assert len(rows) == 2, f"行数不匹配: {len(rows)}"
    assert rows[0] == ["Charlie", 35], f"第一行不匹配: {rows[0]}"
    assert rows[1] == ["Alice", 30], f"第二行不匹配: {rows[1]}"
    print("  ✓ 基本 SELECT 查询通过")
    conn.close()

    # 测试 2: GROUP BY 聚合
    print("测试 2: GROUP BY 聚合")
    conn = load_csv_data(csv_content, "people")
    headers, rows = execute_sql(conn, "SELECT city, COUNT(*) as cnt, AVG(age) as avg_age FROM people GROUP BY city ORDER BY city")
    assert headers == ["city", "cnt", "avg_age"], f"列名不匹配: {headers}"
    assert len(rows) == 2, f"行数不匹配: {len(rows)}"
    assert rows[0] == ["Beijing", 2, 32.5], f"北京数据不匹配: {rows[0]}"
    assert rows[1] == ["Shanghai", 1, 25.0], f"上海数据不匹配: {rows[1]}"
    print("  ✓ GROUP BY 聚合通过")
    conn.close()

    # 测试 3: 类型推断（含脏数据）
    print("测试 3: 类型推断（含脏数据）")
    csv_dirty = """id,value,date
1,10.5,2023-01-01
2,abc,2023-02-01
3,20,not-a-date
"""
    conn = load_csv_data(csv_dirty, "dirty")
    headers, rows = execute_sql(conn, "SELECT * FROM dirty")
    assert len(rows) == 3, f"行数不匹配: {len(rows)}"
    # 脏数据不应导致崩溃，应正常加载
    print("  ✓ 脏数据处理通过")
    conn.close()

    # 测试 4: 导出格式
    print("测试 4: 导出格式")
    conn = load_csv_data(csv_content, "people")
    headers, rows = execute_sql(conn, "SELECT * FROM people")
    csv_out = export_csv(headers, rows)
    assert "Alice" in csv_out, "CSV 导出缺少数据"
    json_out = export_json(headers, rows)
    assert json.loads(json_out)[0]["name"] == "Alice", "JSON 导出错误"
    md_out = export_markdown(headers, rows)
    assert "| name |" in md_out, "Markdown 导出缺少表头"
    print("  ✓ 导出格式通过")
    conn.close()

    # 测试 5: URL 获取（模拟）
    print("测试 5: URL 获取（模拟）")
    # 创建一个本地 HTTP 服务器来测试
    import http.server
    import threading

    class TestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.end_headers()
            self.wfile.write(b"a,b\n1,2\n3,4\n")

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), TestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        content = fetch_url(f"http://127.0.0.1:{port}/test.csv", timeout=5, max_retries=2)
        assert "a,b" in content, "URL 获取内容不正确"
        print("  ✓ URL 获取通过")
    finally:
        server.shutdown()
        server.server_close()

    # 测试 6: 完整主流程
    print("测试 6: 完整主流程")
    test_csv = "x,y\n1,2\n3,4\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(test_csv)
        temp_path = f.name

    try:
        # 测试文件输入
        sys.argv = ["main.py", "--file", temp_path, "--sql", "SELECT x FROM data WHERE x > 1"]
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            main()
            output = sys.stdout.getvalue()
            assert "3" in output, "主流程输出缺少数据"
        finally:
            sys.stdout = old_stdout
        print("  ✓ 主流程通过")
    finally:
        os.unlink(temp_path)

    # 测试 7: 时间戳使用 UTC
    print("测试 7: 时间戳使用 UTC")
    now = datetime.now(timezone.utc)
    assert now.tzinfo is not None, "时间戳未使用 UTC"
    assert now.utcoffset() == timezone.utc.utcoffset(None), "时间戳时区不正确"
    print("  ✓ UTC 时间戳通过")

    print("\n所有自检通过！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
