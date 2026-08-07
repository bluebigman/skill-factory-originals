#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - SQL查询技能（sql-query-generator-llm）独立实现

本脚本依据功能规格独立编写（clean-room），不复制任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能：
- 将用户输入解析为结构化查询信息
- 生成规范化的 SQL 查询语句（基于内置模板）
- 提供置信度评估与错误码体系（E001-E010）
- 支持 --selftest 离线自检（硬编码样例，不依赖外部环境）
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 技能元数据
SKILL_NAME = "sql-query-generator-llm"
DISPLAY_NAME = "SQL查询"
VERSION = "1.0.0"
AUTHOR = "skill-factory-auto"
LICENSE = "MIT"

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "表名不合法",
    "E007": "字段名不合法",
    "E008": "操作类型不支持",
    "E009": "参数解析失败",
    "E010": "内部处理异常",
}

# 支持的操作类型（能力边界）
SUPPORTED_OPERATIONS = {"select", "insert", "update", "delete"}

# 默认置信度阈值
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85

# ============================================================
# 核心数据结构
# ============================================================


class QueryRequest:
    """用户查询请求的解析结果"""

    def __init__(self) -> None:
        self.operation: str = ""          # 操作类型：select/insert/update/delete
        self.table: str = ""              # 目标表名
        self.fields: List[str] = []       # 字段列表
        self.conditions: List[str] = []   # 条件列表
        self.values: List[str] = []       # 插入/更新的值
        self.raw_input: str = ""          # 原始输入
        self.confidence: int = 0          # 置信度（0-100）
        self.notes: List[str] = []        # 备注/警告信息


# ============================================================
# 核心处理函数
# ============================================================


def parse_input(raw_input: str) -> Tuple[Optional[QueryRequest], Optional[str]]:
    """
    解析用户输入，提取结构化查询信息。

    参数:
        raw_input: 用户输入的原始字符串

    返回:
        (QueryRequest, None) 成功时
        (None, 错误码) 失败时
    """
    # E001: 输入为空
    if not raw_input or not raw_input.strip():
        return None, "E001"

    request = QueryRequest()
    request.raw_input = raw_input.strip()

    # 尝试解析 JSON 格式输入
    parsed = _try_parse_json(request.raw_input)
    if parsed is not None:
        # JSON 格式解析
        return _parse_json_request(parsed, request)

    # 尝试解析自然语言格式输入
    return _parse_nl_request(request.raw_input, request)


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """尝试将输入解析为 JSON 格式"""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _parse_json_request(data: Dict[str, Any], request: QueryRequest) -> Tuple[Optional[QueryRequest], Optional[str]]:
    """解析 JSON 格式的请求"""
    # E003: 输入格式错误 - 缺少必要字段
    operation = str(data.get("operation", "")).lower()
    if operation not in SUPPORTED_OPERATIONS:
        return None, "E003"

    table = str(data.get("table", "")).strip()
    if not table:
        return None, "E002"

    # E006: 表名不合法
    if not _validate_identifier(table):
        return None, "E006"

    request.operation = operation
    request.table = table

    # 解析字段
    fields = data.get("fields", [])
    if isinstance(fields, list):
        for f in fields:
            f_str = str(f).strip()
            if f_str and _validate_identifier(f_str):
                request.fields.append(f_str)
            else:
                return None, "E007"

    # 解析条件
    conditions = data.get("conditions", [])
    if isinstance(conditions, list):
        for c in conditions:
            c_str = str(c).strip()
            if c_str:
                request.conditions.append(c_str)

    # 解析值
    values = data.get("values", [])
    if isinstance(values, list):
        for v in values:
            request.values.append(str(v))

    # 计算置信度
    request.confidence = _calculate_confidence(request)
    _add_notes(request)

    return request, None


def _parse_nl_request(text: str, request: QueryRequest) -> Tuple[Optional[QueryRequest], Optional[str]]:
    """
    解析自然语言格式的请求。
    支持格式示例：
      - "查询 users 表中 name 为 '张三' 的记录"
      - "从 orders 表中选择 id, amount 字段"
      - "在 products 表插入 name='商品A', price=100"
    """
    text_lower = text.lower()

    # 识别操作类型
    if "查询" in text_lower or "选择" in text_lower or "select" in text_lower:
        request.operation = "select"
    elif "插入" in text_lower or "insert" in text_lower:
        request.operation = "insert"
    elif "更新" in text_lower or "update" in text_lower:
        request.operation = "update"
    elif "删除" in text_lower or "delete" in text_lower:
        request.operation = "delete"
    else:
        return None, "E003"

    # 识别表名
    table = _extract_table_name(text_lower)
    if not table:
        return None, "E002"

    request.table = table

    # 识别字段（在 "选择"/"select" 后跟字段列表）
    if request.operation == "select":
        fields = _extract_select_fields(text_lower)
        if fields:
            request.fields = fields

    # 识别条件（包含 "=" 或 "为" 的片段）
    conditions = _extract_conditions(text)
    if conditions:
        request.conditions = conditions

    # 识别值（插入/更新场景）
    if request.operation in ("insert", "update"):
        values = _extract_values(text)
        if values:
            request.values = values

    # 计算置信度
    request.confidence = _calculate_confidence(request)
    _add_notes(request)

    return request, None


def _validate_identifier(ident: str) -> bool:
    """验证标识符（表名/字段名）是否合法"""
    if not ident:
        return False
    # 允许字母、数字、下划线，且不能以数字开头
    if not ident[0].isalpha() and ident[0] != "_":
        return False
    return all(c.isalnum() or c == "_" for c in ident)


def _extract_table_name(text: str) -> Optional[str]:
    """从文本中提取表名"""
    # 格式1: "XX表" 或 "XX 表"（空格分隔）
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*表'
    match = re.search(pattern, text)
    if match:
        candidate = match.group(1)
        if _validate_identifier(candidate):
            return candidate

    # 格式2: "table XX" 或 "表 XX"
    pattern = r'(?:table|表)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    match = re.search(pattern, text)
    if match:
        candidate = match.group(1)
        if _validate_identifier(candidate):
            return candidate

    # 格式3: "从XX表" 或 "在XX表" 或 "到XX表"
    pattern = r'(?:从|在|到)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*表'
    match = re.search(pattern, text)
    if match:
        candidate = match.group(1)
        if _validate_identifier(candidate):
            return candidate

    # 格式4: 从文本中查找第一个合法的标识符（作为备用）
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text)
    for word in words:
        if word not in ("select", "from", "where", "insert", "update", "delete", "table"):
            if _validate_identifier(word):
                return word

    return None


def _extract_select_fields(text: str) -> List[str]:
    """从 select 语句中提取字段列表"""
    fields = []
    markers = ["选择", "select", "查询"]
    for marker in markers:
        if marker in text:
            idx = text.index(marker) + len(marker)
            # 取后续内容直到 "从" 或 "from" 或 "表"
            rest = text[idx:]
            for end_marker in ["从", "from", "表"]:
                if end_marker in rest:
                    rest = rest[: rest.index(end_marker)]
                    break
            # 按逗号或空格分割
            for part in rest.replace(",", " ").split():
                part = part.strip()
                if part and _validate_identifier(part):
                    fields.append(part)
            break
    return fields


def _extract_conditions(text: str) -> List[str]:
    """从文本中提取条件表达式"""
    conditions = []
    
    # 格式1: "field = 'value'" 或 "field='value'"
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*[\'"]?([^\'",\s]+)[\'"]?'
    matches = re.findall(pattern, text)
    for field, value in matches:
        if _validate_identifier(field):
            conditions.append(f"{field} = '{value}'")
    
    # 格式2: "field 为 'value'" 或 "field为'value'"
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*为\s*[\'"]?([^\'",\s]+)[\'"]?'
    matches = re.findall(pattern, text)
    for field, value in matches:
        if _validate_identifier(field):
            conditions.append(f"{field} = '{value}'")
    
    # 格式3: 支持运算符条件（>、<、>=、<=、!=）
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(>=|<=|!=|>|<)\s*[\'"]?([^\'",\s]+)[\'"]?'
    matches = re.findall(pattern, text)
    for field, op, value in matches:
        if _validate_identifier(field):
            conditions.append(f"{field} {op} '{value}'")
    
    return conditions


def _extract_values(text: str) -> List[str]:
    """从文本中提取值列表"""
    values = []
    # 查找包含 "=" 或 "为" 的片段，取等号后的值
    pattern = r'(?:=|为)\s*[\'"]?([^\'",\s]+)[\'"]?'
    matches = re.findall(pattern, text)
    for value in matches:
        if value:
            values.append(value)
    return values


def _calculate_confidence(request: QueryRequest) -> int:
    """根据请求完整性计算置信度"""
    score = 0

    # 操作类型明确 +20
    if request.operation:
        score += 20

    # 表名明确 +30
    if request.table:
        score += 30

    # 字段明确 +20
    if request.fields:
        score += 20
    elif request.operation == "select":
        # select 无字段时使用 *，仍可接受
        score += 10

    # 条件明确 +15
    if request.conditions:
        score += 15

    # 值明确（insert/update）+15
    if request.values:
        score += 15

    return min(score, 100)


def _add_notes(request: QueryRequest) -> None:
    """根据置信度添加备注"""
    if request.confidence >= HIGH_CONFIDENCE:
        pass  # 高置信度，无需备注
    elif request.confidence >= MEDIUM_CONFIDENCE:
        request.notes.append("建议复核")
    else:
        request.notes.append("[需核实] 输入信息不完整，结果可能存在偏差")


def generate_sql(request: QueryRequest) -> Tuple[Optional[str], Optional[str]]:
    """
    根据解析后的请求生成 SQL 查询语句。

    参数:
        request: 解析后的查询请求

    返回:
        (sql语句, None) 成功时
        (None, 错误码) 失败时
    """
    # E008: 操作类型不支持
    if request.operation not in SUPPORTED_OPERATIONS:
        return None, "E008"

    # E006/E007: 标识符校验
    if not _validate_identifier(request.table):
        return None, "E006"
    for field in request.fields:
        if not _validate_identifier(field):
            return None, "E007"

    # 根据操作类型生成 SQL
    if request.operation == "select":
        return _generate_select_sql(request), None
    elif request.operation == "insert":
        return _generate_insert_sql(request), None
    elif request.operation == "update":
        return _generate_update_sql(request), None
    elif request.operation == "delete":
        return _generate_delete_sql(request), None

    return None, "E008"


def _generate_select_sql(request: QueryRequest) -> str:
    """生成 SELECT 语句"""
    fields = ", ".join(request.fields) if request.fields else "*"
    sql = f"SELECT {fields} FROM {request.table}"

    if request.conditions:
        where_clause = " AND ".join(request.conditions)
        sql += f" WHERE {where_clause}"

    sql += ";"
    return sql


def _generate_insert_sql(request: QueryRequest) -> str:
    """生成 INSERT 语句"""
    if not request.fields:
        # 没有字段时使用默认占位符
        fields = "*"
        values = ", ".join(f"'{v}'" for v in request.values)
        sql = f"INSERT INTO {request.table} VALUES ({values});"
    else:
        fields = ", ".join(request.fields)
        values = ", ".join(f"'{v}'" for v in request.values)
        sql = f"INSERT INTO {request.table} ({fields}) VALUES ({values});"
    return sql


def _generate_update_sql(request: QueryRequest) -> str:
    """生成 UPDATE 语句"""
    if not request.fields:
        # 无字段时使用 values 作为 SET 内容
        set_clause = ", ".join(f"col{i+1} = '{v}'" for i, v in enumerate(request.values))
    else:
        set_clause = ", ".join(f"{f} = '{v}'" for f, v in zip(request.fields, request.values))

    sql = f"UPDATE {request.table} SET {set_clause}"

    if request.conditions:
        where_clause = " AND ".join(request.conditions)
        sql += f" WHERE {where_clause}"

    sql += ";"
    return sql


def _generate_delete_sql(request: QueryRequest) -> str:
    """生成 DELETE 语句"""
    sql = f"DELETE FROM {request.table}"

    if request.conditions:
        where_clause = " AND ".join(request.conditions)
        sql += f" WHERE {where_clause}"

    sql += ";"
    return sql


def format_output(request: QueryRequest, sql: str) -> Dict[str, Any]:
    """格式化输出结果"""
    result = {
        "skill": DISPLAY_NAME,
        "version": VERSION,
        "operation": request.operation,
        "table": request.table,
        "sql": sql,
        "confidence": request.confidence,
        "notes": request.notes,
    }

    # 根据置信度添加提示
    if request.confidence >= HIGH_CONFIDENCE:
        result["status"] = "success"
    elif request.confidence >= MEDIUM_CONFIDENCE:
        result["status"] = "review_recommended"
    else:
        result["status"] = "needs_verification"

    return result


def process_request(raw_input: str) -> Dict[str, Any]:
    """
    处理用户请求的完整流程。

    参数:
        raw_input: 用户输入的原始字符串

    返回:
        结构化输出结果
    """
    # Step 1: 解析输入
    request, error_code = parse_input(raw_input)
    if error_code:
        return _build_error_response(error_code, raw_input)

    # Step 2: 生成 SQL
    sql, error_code = generate_sql(request)
    if error_code:
        return _build_error_response(error_code, raw_input)

    # Step 3: 格式化输出
    return format_output(request, sql)


def _build_error_response(error_code: str, raw_input: str) -> Dict[str, Any]:
    """构建错误响应"""
    error_message = ERROR_CODES.get(error_code, "未知错误")

    # 根据错误码提供标准化话术
    if error_code == "E001":
        message = "请提供待处理的内容，格式为：用户提供的数据/文件/URL"
    elif error_code == "E002":
        message = "还缺少以下信息，请补充：表名"
    elif error_code == "E003":
        message = "输入格式不符合要求，示例：查询 users 表中 name 为 '张三' 的记录"
    elif error_code == "E004":
        message = "这超出了本工具的能力范围，建议使用专业数据库客户端"
    elif error_code == "E005":
        message = "结果无法确定，建议提供更完整的查询条件"
    else:
        message = error_message

    return {
        "skill": DISPLAY_NAME,
        "version": VERSION,
        "error": error_code,
        "message": message,
        "raw_input": raw_input,
        "status": "error",
    }


# ============================================================
# 自检功能
# ============================================================


def run_selftest() -> bool:
    """
    运行内置自检样例，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值（大小比较/区间判断），确保稳健。

    返回:
        True 表示所有测试通过
    """
    print("=" * 60)
    print(f"自检开始：{DISPLAY_NAME} v{VERSION}")
    print("=" * 60)

    all_passed = True

    # ---- 测试用例 1: 空输入 ----
    print("\n[测试 1] 空输入处理")
    result = process_request("")
    assert result["status"] == "error", "空输入应返回错误"
    assert result["error"] == "E001", "空输入应返回 E001"
    print("  ✓ 通过")

    # ---- 测试用例 2: JSON 格式 select 请求 ----
    print("\n[测试 2] JSON 格式 select 请求")
    json_input = json.dumps(
        {
            "operation": "select",
            "table": "users",
            "fields": ["id", "name", "email"],
            "conditions": ["age > 18"],
        }
    )
    result = process_request(json_input)
    assert result["status"] != "error", f"JSON select 请求不应失败: {result}"
    assert result["operation"] == "select", "操作类型应为 select"
    assert result["table"] == "users", "表名应为 users"
    assert "SELECT" in result["sql"].upper(), "SQL 应包含 SELECT"
    assert "users" in result["sql"], "SQL 应包含表名 users"
    assert result["confidence"] >= 70, f"置信度应较高，实际: {result['confidence']}"
    print(f"  ✓ 通过 (SQL: {result['sql']})")

    # ---- 测试用例 3: 自然语言 select 请求 ----
    print("\n[测试 3] 自然语言 select 请求")
    result = process_request("查询 users 表中 name 为 '张三' 的记录")
    assert result["status"] != "error", f"自然语言 select 不应失败: {result}"
    assert result["operation"] == "select", "操作类型应为 select"
    assert result["table"] == "users", "表名应为 users"
    assert "SELECT" in result["sql"].upper(), "SQL 应包含 SELECT"
    assert "users" in result["sql"], "SQL 应包含表名 users"
    assert "name" in result["sql"], "SQL 应包含条件字段 name"
    print(f"  ✓ 通过 (SQL: {result['sql']})")

    # ---- 测试用例 4: JSON 格式 insert 请求 ----
    print("\n[测试 4] JSON 格式 insert 请求")
    json_input = json.dumps(
        {
            "operation": "insert",
            "table": "products",
            "fields": ["name", "price"],
            "values": ["商品A", 100],
        }
    )
    result = process_request(json_input)
    assert result["status"] != "error", f"JSON insert 不应失败: {result}"
    assert result["operation"] == "insert", "操作类型应为 insert"
    assert "INSERT" in result["sql"].upper(), "SQL 应包含 INSERT"
    assert "products" in result["sql"], "SQL 应包含表名 products"
    print(f"  ✓ 通过 (SQL: {result['sql']})")

    # ---- 测试用例 5: 不支持的操作类型 ----
    print("\n[测试 5] 不支持的操作类型")
    json_input = json.dumps({"operation": "drop", "table": "users"})
    result = process_request(json_input)
    assert result["status"] == "error", "drop 操作应返回错误"
    assert result["error"] in ("E003", "E008"), "应返回格式错误或操作不支持"
    print(f"  ✓ 通过 (错误码: {result['error']})")

    # ---- 测试用例 6: 缺失表名 ----
    print("\n[测试 6] 缺失表名")
    json_input = json.dumps({"operation": "select", "fields": ["id"]})
    result = process_request(json_input)
    assert result["status"] == "error", "缺失表名应返回错误"
    assert result["error"] == "E002", "应返回关键信息缺失"
    print(f"  ✓ 通过 (错误码: {result['error']})")

    # ---- 测试用例 7: 非法表名 ----
    print("\n[测试 7] 非法表名")
    json_input = json.dumps({"operation": "select", "table": "123invalid"})
    result = process_request(json_input)
    assert result["status"] == "error", "非法表名应返回错误"
    assert result["error"] == "E006", "应返回表名不合法"
    print(f"  ✓ 通过 (错误码: {result['error']})")

    # ---- 测试用例 8: 置信度评估 ----
    print("\n[测试 8] 置信度评估")
    # 完整请求应获得较高置信度
    json_input = json.dumps(
        {
            "operation": "update",
            "table": "orders",
            "fields": ["status"],
            "values": ["completed"],
            "conditions": ["id = 1"],
        }
    )
    result = process_request(json_input)
    assert result["confidence"] >= 80, f"完整请求置信度应较高，实际: {result['confidence']}"
    print(f"  ✓ 通过 (置信度: {result['confidence']}%)")

    # ---- 测试用例 9: SQL 生成正确性 ----
    print("\n[测试 9] SQL 生成正确性")
    json_input = json.dumps(
        {
            "operation": "select",
            "table": "employees",
            "fields": ["id", "name"],
            "conditions": ["department = 'IT'"],
        }
    )
    result = process_request(json_input)
    sql = result["sql"]
    assert sql.startswith("SELECT"), "SQL 应以 SELECT 开头"
    assert "FROM employees" in sql, "SQL 应包含 FROM employees"
    assert "WHERE" in sql, "SQL 应包含 WHERE"
    assert "department" in sql, "SQL 应包含条件字段"
    print(f"  ✓ 通过 (SQL: {sql})")

    # ---- 测试用例 10: 错误码完整性 ----
    print("\n[测试 10] 错误码完整性")
    assert len(ERROR_CODES) >= 5, "应至少包含 5 个错误码"
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_CODES, f"缺少错误码 {code}"
    print(f"  ✓ 通过 (共 {len(ERROR_CODES)} 个错误码)")

    # ---- 测试用例 11: 批量处理能力 ----
    print("\n[测试 11] 批量处理能力")
    batch_inputs = [
        json.dumps({"operation": "select", "table": "t1", "fields": ["a"]}),
        json.dumps({"operation": "insert", "table": "t2", "fields": ["b"], "values": ["v"]}),
        json.dumps({"operation": "update", "table": "t3", "fields": ["c"], "values": ["w"], "conditions": ["d = 1"]}),
        json.dumps({"operation": "delete", "table": "t4", "conditions": ["e = 2"]}),
    ]
    success_count = 0
    for input_str in batch_inputs:
        result = process_request(input_str)
        if result["status"] != "error":
            success_count += 1
    assert success_count == len(batch_inputs), f"批量处理应有 {len(batch_inputs)} 个成功，实际 {success_count}"
    print(f"  ✓ 通过 ({success_count}/{len(batch_inputs)} 个成功)")

    # ---- 测试用例 12: 能力边界 ----
    print("\n[测试 12] 能力边界")
    # 超出能力范围的操作（如 join 多表）应返回错误或低置信度
    result = process_request("执行跨表 join 查询")
    # 不强制要求错误，但置信度应不高
    if result["status"] != "error":
        assert result["confidence"] < 85, "复杂查询置信度应较低"
    print("  ✓ 通过")

    print("\n" + "=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================


def main() -> int:
    """命令行入口函数"""
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - SQL查询生成工具 v{VERSION}"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检样例，验证核心逻辑",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入查询请求（JSON 格式或自然语言）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"\n❌ 自检失败: {e}")
            return 1
        except Exception as e:
            print(f"\n❌ 自检异常: {e}")
            return 1

    # 处理输入
    if args.input:
        result = process_request(args.input)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_human_readable(result)
        return 0

    # 无输入时显示帮助
    parser.print_help()
    return 0


def _print_human_readable(result: Dict[str, Any]) -> None:
    """以人类可读格式打印结果"""
    print(f"\n{DISPLAY_NAME} v{VERSION}")
    print("-" * 40)

    if result["status"] == "error":
        print(f"❌ 错误 [{result['error']}]: {result['message']}")
        return

    print(f"操作: {result['operation']}")
    print(f"表名: {result['table']}")
    print(f"SQL:  {result['sql']}")
    print(f"置信度: {result['confidence']}%")

    if result["notes"]:
        print("提示:")
        for note in result["notes"]:
            print(f"  - {note}")

    if result["status"] == "review_recommended":
        print("\n⚠️ 建议复核")
    elif result["status"] == "needs_verification":
        print("\n⚠️ [需核实] 请人工复核关键结果")


if __name__ == "__main__":
    sys.exit(main())
