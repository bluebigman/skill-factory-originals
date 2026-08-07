#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: sql-generator-and-editor
版本: 1.0.0
说明: 仅供学习与参考用途。提供 SQL 生成与编辑辅助能力。
"""

import argparse
import sys
import re
from typing import Dict, List, Optional, Any, Tuple


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "参数解析错误",
    "E008": "输出生成失败",
    "E009": "数据校验失败",
    "E010": "未知错误",
}

# 支持的 SQL 关键字（用于检测/识别）
SQL_KEYWORDS = {"select", "insert", "update", "delete", "from", "where", "set", "values", "into"}


# ============================================================
# 核心数据结构
# ============================================================
class InputData:
    """统一输入数据容器"""
    def __init__(self, source: str, content: str, output_format: str = "sql"):
        self.source = source          # 来源描述
        self.content = content        # 原始内容
        self.output_format = output_format  # 期望输出格式
        self.fields: List[str] = []   # 识别出的字段
        self.records: List[Dict[str, str]] = []  # 结构化记录
        self.confidence: float = 0.0  # 置信度


# ============================================================
# 核心处理函数
# ============================================================
def validate_input(raw_input: str) -> Tuple[bool, str]:
    """校验输入是否有效
    
    Args:
        raw_input: 用户输入的原始字符串
        
    Returns:
        (是否有效, 错误码或空字符串)
    """
    if not raw_input or not raw_input.strip():
        return False, "E001"
    if len(raw_input.strip()) < 3:
        return False, "E003"
    return True, ""


def parse_input(raw_input: str) -> InputData:
    """解析输入内容，识别关键信息
    
    支持两种格式：
    1. 简单SQL语句（如 "select * from users"）
    2. 结构化数据（如 "字段1|字段2|字段3 值1|值2|值3"）
    
    Args:
        raw_input: 用户输入
        
    Returns:
        InputData 对象
    """
    data = InputData(source="user_input", content=raw_input.strip())
    
    # 检测是否为 SQL 语句
    first_word = data.content.lower().split()[0] if data.content.split() else ""
    if first_word in SQL_KEYWORDS:
        data.output_format = "sql"
        data.fields = extract_sql_fields(data.content)
        data.confidence = 0.9 if data.fields else 0.7
        return data
    
    # 尝试解析为表格数据（竖线分隔）
    lines = data.content.split("\n")
    if len(lines) >= 2 and "|" in lines[0]:
        # 第一行为字段名
        data.fields = [f.strip() for f in lines[0].split("|") if f.strip()]
        for line in lines[1:]:
            if "|" in line:
                values = [v.strip() for v in line.split("|")]
                if len(values) == len(data.fields):
                    record = dict(zip(data.fields, values))
                    data.records.append(record)
        data.confidence = 0.85 if data.records else 0.5
        return data
    
    # 默认处理
    data.fields = ["content"]
    data.records = [{"content": data.content}]
    data.confidence = 0.6
    return data


def extract_sql_fields(sql: str) -> List[str]:
    """从 SQL 语句中提取字段名
    
    Args:
        sql: SQL 语句
        
    Returns:
        字段名列表
    """
    # 简单提取 SELECT 后的字段
    match = re.search(r"select\s+(.+?)\s+from", sql, re.IGNORECASE)
    if match:
        fields_part = match.group(1).strip()
        if fields_part == "*":
            return ["*"]
        # 拆分字段（考虑逗号）
        fields = []
        for f in fields_part.split(","):
            f = f.strip()
            if f:
                # 处理别名
                if " as " in f.lower():
                    f = f.lower().split(" as ")[1].strip()
                elif " " in f:
                    f = f.split()[-1].strip()
                fields.append(f)
        return fields
    return []


def generate_sql(data: InputData, operation: str = "select") -> str:
    """生成 SQL 语句
    
    Args:
        data: 解析后的输入数据
        operation: 操作类型 (select/insert/update/delete)
        
    Returns:
        SQL 语句字符串
    """
    if operation == "select":
        if data.fields:
            fields_str = ", ".join(data.fields)
            return f"SELECT {fields_str} FROM table_name"
        return "SELECT * FROM table_name"
    
    elif operation == "insert":
        if data.fields and data.records:
            fields_str = ", ".join(data.fields)
            placeholders = ", ".join(["?"] * len(data.fields))
            return f"INSERT INTO table_name ({fields_str}) VALUES ({placeholders})"
        return "INSERT INTO table_name (column1, column2) VALUES (?, ?)"
    
    elif operation == "update":
        if data.fields:
            set_clause = ", ".join([f"{f} = ?" for f in data.fields if f != "*"])
            if set_clause:
                return f"UPDATE table_name SET {set_clause} WHERE condition"
        return "UPDATE table_name SET column = ? WHERE condition"
    
    elif operation == "delete":
        return "DELETE FROM table_name WHERE condition"
    
    return ""


def estimate_confidence(data: InputData) -> float:
    """估算置信度
    
    Args:
        data: 输入数据
        
    Returns:
        置信度 (0-1)
    """
    if not data.content:
        return 0.0
    
    # 基础置信度
    confidence = 0.5
    
    # 有字段名加分
    if data.fields:
        confidence += 0.2
    
    # 有记录数据加分
    if data.records:
        confidence += 0.2
    
    # 格式完整度
    if len(data.content) > 20:
        confidence += 0.1
    
    return min(confidence, 1.0)


def format_output(data: InputData, sql: str) -> str:
    """格式化输出结果
    
    Args:
        data: 输入数据
        sql: 生成的 SQL
        
    Returns:
        格式化后的输出字符串
    """
    confidence = estimate_confidence(data)
    data.confidence = confidence
    
    lines = []
    lines.append("=" * 50)
    lines.append("SQL 生成结果")
    lines.append("=" * 50)
    lines.append(f"输入来源: {data.source}")
    lines.append(f"识别字段: {', '.join(data.fields) if data.fields else '未识别'}")
    lines.append(f"记录数量: {len(data.records)}")
    lines.append(f"置信度: {confidence:.0%}")
    
    if confidence < 0.85:
        lines.append("⚠️ [需核实] 部分信息可能不准确，请人工复核")
    elif confidence < 0.9:
        lines.append("建议复核")
    
    lines.append("-" * 50)
    lines.append("生成的 SQL:")
    lines.append(sql)
    lines.append("=" * 50)
    
    return "\n".join(lines)


def process_request(raw_input: str, operation: str = "select") -> Tuple[bool, str, str]:
    """处理用户请求的主流程
    
    Args:
        raw_input: 用户输入
        operation: 期望的 SQL 操作类型
        
    Returns:
        (是否成功, 错误码或空字符串, 输出结果)
    """
    # Step 1: 校验输入
    is_valid, error_code = validate_input(raw_input)
    if not is_valid:
        return False, error_code, ERROR_CODES.get(error_code, "未知错误")
    
    # Step 2: 解析输入
    try:
        data = parse_input(raw_input)
    except Exception:
        return False, "E006", ERROR_CODES["E006"]
    
    # Step 3: 检查能力边界
    if not data.fields and not data.records:
        return False, "E004", ERROR_CODES["E004"]
    
    # Step 4: 生成 SQL
    try:
        sql = generate_sql(data, operation)
    except Exception:
        return False, "E008", ERROR_CODES["E008"]
    
    if not sql:
        return False, "E005", ERROR_CODES["E005"]
    
    # Step 5: 格式化输出
    output = format_output(data, sql)
    
    return True, "", output


# ============================================================
# 自测功能
# ============================================================
def run_selftest() -> bool:
    """内置自测函数，使用硬编码样例数据
    
    Returns:
        是否全部通过
    """
    print("开始自测...")
    all_passed = True
    
    # 测试用例 1: 基本 SQL 生成
    test_inputs = [
        # (输入, 操作类型, 描述)
        ("select id, name from users", "select", "SELECT 语句解析"),
        ("id|name|age\n1|Alice|30\n2|Bob|25", "insert", "表格数据转 INSERT"),
        ("name|email\nJohn|john@example.com", "update", "数据转 UPDATE"),
    ]
    
    for i, (test_input, operation, desc) in enumerate(test_inputs, 1):
        try:
            success, error_code, output = process_request(test_input, operation)
            if success:
                print(f"  ✓ 测试 {i} ({desc}): 通过")
                # 验证输出包含关键内容
                assert "SQL" in output, "输出缺少 SQL 标识"
                assert "置信度" in output, "输出缺少置信度"
            else:
                print(f"  ✗ 测试 {i} ({desc}): 失败 - {error_code}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 测试 {i} ({desc}): 异常 - {e}")
            all_passed = False
    
    # 测试用例 2: 错误处理
    error_tests = [
        ("", "E001", "空输入处理"),
        ("ab", "E003", "过短输入处理"),
    ]
    
    for i, (test_input, expected_error, desc) in enumerate(error_tests, len(test_inputs) + 1):
        try:
            success, error_code, _ = process_request(test_input)
            if not success and error_code == expected_error:
                print(f"  ✓ 测试 {i} ({desc}): 通过")
            else:
                print(f"  ✗ 测试 {i} ({desc}): 期望 {expected_error}, 实际 {error_code}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 测试 {i} ({desc}): 异常 - {e}")
            all_passed = False
    
    # 测试用例 3: 功能完整性验证（宽松断言）
    try:
        # 验证 SELECT 生成
        data = parse_input("select id, name from users")
        sql = generate_sql(data, "select")
        assert "SELECT" in sql.upper(), "SELECT 关键字缺失"
        assert "id" in sql.lower() and "name" in sql.lower(), "字段名缺失"
        assert data.confidence > 0.5, "置信度应大于 50%"
        print("  ✓ 测试 (SELECT 生成完整性): 通过")
    except AssertionError as e:
        print(f"  ✗ 测试 (SELECT 生成完整性): 失败 - {e}")
        all_passed = False
    
    # 验证 INSERT 生成
    try:
        data = parse_input("col1|col2\nval1|val2")
        sql = generate_sql(data, "insert")
        assert "INSERT" in sql.upper(), "INSERT 关键字缺失"
        assert "col1" in sql and "col2" in sql, "字段名缺失"
        print("  ✓ 测试 (INSERT 生成完整性): 通过")
    except AssertionError as e:
        print(f"  ✗ 测试 (INSERT 生成完整性): 失败 - {e}")
        all_passed = False
    
    # 验证 UPDATE 生成
    try:
        data = parse_input("field1|field2")
        sql = generate_sql(data, "update")
        assert "UPDATE" in sql.upper(), "UPDATE 关键字缺失"
        assert "SET" in sql.upper(), "SET 关键字缺失"
        print("  ✓ 测试 (UPDATE 生成完整性): 通过")
    except AssertionError as e:
        print(f"  ✗ 测试 (UPDATE 生成完整性): 失败 - {e}")
        all_passed = False
    
    # 验证 DELETE 生成
    try:
        sql = generate_sql(InputData("test", "test"), "delete")
        assert "DELETE" in sql.upper(), "DELETE 关键字缺失"
        print("  ✓ 测试 (DELETE 生成完整性): 通过")
    except AssertionError as e:
        print(f"  ✗ 测试 (DELETE 生成完整性): 失败 - {e}")
        all_passed = False
    
    # 验证边界处理
    try:
        # 无字段数据
        data = InputData("test", "plain text")
        data.confidence = estimate_confidence(data)
        assert 0 <= data.confidence <= 1, "置信度应在 0-1 范围内"
        print("  ✓ 测试 (边界处理): 通过")
    except AssertionError as e:
        print(f"  ✗ 测试 (边界处理): 失败 - {e}")
        all_passed = False
    
    # 验证错误码体系
    try:
        for code in ERROR_CODES:
            assert code.startswith("E"), f"错误码 {code} 格式错误"
            assert len(code) == 4, f"错误码 {code} 长度错误"
            assert ERROR_CODES[code], f"错误码 {code} 缺少描述"
        print("  ✓ 测试 (错误码体系): 通过")
    except AssertionError as e:
        print(f"  ✗ 测试 (错误码体系): 失败 - {e}")
        all_passed = False
    
    # 总结
    if all_passed:
        print("\n✅ 所有自测通过！")
    else:
        print("\n❌ 部分自测失败，请检查实现")
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SQL Generator and Editor - SQL 生成与编辑工具",
        epilog="示例: python main.py --input \"select * from users\" --operation select"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（SQL 语句或表格数据）"
    )
    
    parser.add_argument(
        "--operation", "-o",
        type=str,
        choices=["select", "insert", "update", "delete"],
        default="select",
        help="SQL 操作类型 (默认: select)"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="sql-generator-and-editor 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自测模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 处理输入
    if not args.input:
        print("错误: 请提供输入内容 (使用 --input 参数)")
        print(f"错误码: E001 - {ERROR_CODES['E001']}")
        print("\n提示: 运行 --selftest 可进行功能自测")
        sys.exit(1)
    
    success, error_code, output = process_request(args.input, args.operation)
    
    if success:
        print(output)
        sys.exit(0)
    else:
        print(f"错误: {error_code} - {output}")
        sys.exit(1)


if __name__ == "__main__":
    main()
