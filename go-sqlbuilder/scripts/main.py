#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — SQL查询（go-sqlbuilder 风格）独立实现

本脚本仅依据功能规格进行 clean-room 重写，不复制任何既有代码。
提供以下能力：
  1. 将输入内容解析为结构化 SQL 查询片段
  2. 识别关键信息（表名、字段、条件、排序、分页）
  3. 按约定格式输出 SQL 语句及置信度
  4. 支持 --selftest 离线自检（硬编码样例，不依赖外部环境）

错误码约定：
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 参数解析失败
  E007 自检失败
  E008 内部逻辑错误
  E009 输出生成失败
  E010 未知异常

依赖：仅标准库（无需 pip install）。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 置信度阈值
CONF_HIGH = 0.90       # 置信度 >= 90% 直接输出
CONF_MEDIUM = 0.85     # 85%-90% 标注"建议复核"
CONF_LOW = 0.85        # <85% 标注"[需核实]"

# 错误码与标准化话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：SELECT * FROM users WHERE age > 18",
    "E004": "这超出了本工具的能力范围，建议简化查询或使用专业数据库工具",
    "E005": "结果无法确定，建议：补充更多条件或明确查询意图",
    "E006": "参数解析失败，请检查命令行参数格式",
    "E007": "自检失败，核心逻辑存在缺陷",
    "E008": "内部逻辑错误，请联系开发者",
    "E009": "输出生成失败，请重试",
    "E010": "未知异常，请查看错误详情",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ParsedQuery:
    """解析后的查询结构体。"""

    def __init__(self) -> None:
        self.table: Optional[str] = None          # 表名
        self.fields: List[str] = []               # 查询字段
        self.conditions: List[str] = []           # WHERE 条件
        self.order_by: Optional[str] = None        # ORDER BY
        self.limit: Optional[int] = None           # LIMIT
        self.offset: Optional[int] = None          # OFFSET
        self.raw_input: str = ""                   # 原始输入
        self.confidence: float = 0.0               # 置信度 0~1
        self.warnings: List[str] = []              # 警告信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（便于 JSON 序列化）。"""
        return {
            "table": self.table,
            "fields": self.fields,
            "conditions": self.conditions,
            "order_by": self.order_by,
            "limit": self.limit,
            "offset": self.offset,
            "confidence": round(self.confidence, 4),
            "warnings": self.warnings,
            "raw_input": self.raw_input,
        }


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------

def _extract_table(sql_text: str) -> Optional[str]:
    """
    从 SQL 文本中提取表名。

    支持两种形式：
      1. FROM table_name
      2. UPDATE/DELETE INTO table_name
    """
    # 优先匹配 FROM 子句
    from_match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)", sql_text, re.IGNORECASE)
    if from_match:
        return from_match.group(1)

    # 匹配 UPDATE table_name
    update_match = re.search(r"\bUPDATE\s+([A-Za-z_][A-Za-z0-9_]*)", sql_text, re.IGNORECASE)
    if update_match:
        return update_match.group(1)

    # 匹配 DELETE FROM table_name（已包含在 FROM 匹配中）

    # 匹配 INSERT INTO table_name
    insert_match = re.search(r"\bINSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)", sql_text, re.IGNORECASE)
    if insert_match:
        return insert_match.group(1)

    return None


def _extract_fields(sql_text: str) -> List[str]:
    """提取查询字段列表。"""
    # 匹配 SELECT 与 FROM 之间的内容
    select_match = re.search(r"\bSELECT\s+(.+?)\bFROM\b", sql_text, re.IGNORECASE | re.DOTALL)
    if not select_match:
        return []

    fields_part = select_match.group(1).strip()
    if fields_part == "*":
        return ["*"]

    # 按逗号分割，去除多余空白
    fields = [f.strip() for f in fields_part.split(",") if f.strip()]
    return fields


def _extract_conditions(sql_text: str) -> List[str]:
    """提取 WHERE 条件列表。"""
    # 匹配 WHERE 与 ORDER BY / LIMIT / 结尾 之间的内容
    where_match = re.search(r"\bWHERE\s+(.+?)(?:\bORDER\s+BY\b|\bLIMIT\b|$)", sql_text, re.IGNORECASE | re.DOTALL)
    if not where_match:
        return []

    conditions_part = where_match.group(1).strip()
    # 按 AND 分割（支持大小写）
    parts = re.split(r"\bAND\b", conditions_part, flags=re.IGNORECASE)
    conditions = [p.strip() for p in parts if p.strip()]
    return conditions


def _extract_order_by(sql_text: str) -> Optional[str]:
    """提取 ORDER BY 子句。"""
    order_match = re.search(r"\bORDER\s+BY\s+(.+?)(?:\bLIMIT\b|$)", sql_text, re.IGNORECASE | re.DOTALL)
    if order_match:
        return order_match.group(1).strip()
    return None


def _extract_limit_offset(sql_text: str) -> Tuple[Optional[int], Optional[int]]:
    """提取 LIMIT 和 OFFSET。"""
    limit: Optional[int] = None
    offset: Optional[int] = None

    # 匹配 LIMIT
    limit_match = re.search(r"\bLIMIT\s+(\d+)", sql_text, re.IGNORECASE)
    if limit_match:
        limit = int(limit_match.group(1))

    # 匹配 OFFSET
    offset_match = re.search(r"\bOFFSET\s+(\d+)", sql_text, re.IGNORECASE)
    if offset_match:
        offset = int(offset_match.group(1))

    return limit, offset


def _calculate_confidence(parsed: ParsedQuery) -> float:
    """
    计算置信度（0~1）。

    规则：
      - 表名存在：+0.4
      - 字段非空：+0.3
      - 条件非空：+0.2
      - ORDER BY 存在：+0.05
      - LIMIT 存在：+0.05
    上限 1.0。
    """
    confidence = 0.0

    if parsed.table:
        confidence += 0.4
    if parsed.fields:
        confidence += 0.3
    if parsed.conditions:
        confidence += 0.2
    if parsed.order_by:
        confidence += 0.05
    if parsed.limit is not None:
        confidence += 0.05

    # 截断到 0~1
    return max(0.0, min(1.0, confidence))


def parse_sql_query(input_text: str) -> ParsedQuery:
    """
    解析用户输入的 SQL 查询文本，返回结构化结果。

    参数:
        input_text: 用户输入的 SQL 文本

    返回:
        ParsedQuery 对象

    异常:
        ValueError: 当输入为空或格式错误时抛出，携带错误码
    """
    # 输入校验
    if not input_text or not input_text.strip():
        raise ValueError("E001")

    sql_text = input_text.strip()

    # 检查是否为 SELECT/UPDATE/DELETE/INSERT 开头（宽松检查）
    sql_keywords = (r"\bSELECT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bINSERT\b")
    if not any(re.search(kw, sql_text, re.IGNORECASE) for kw in sql_keywords):
        raise ValueError("E003")

    # 创建解析结果对象
    parsed = ParsedQuery()
    parsed.raw_input = sql_text

    # 提取各部分
    parsed.table = _extract_table(sql_text)
    parsed.fields = _extract_fields(sql_text)
    parsed.conditions = _extract_conditions(sql_text)
    parsed.order_by = _extract_order_by(sql_text)
    parsed.limit, parsed.offset = _extract_limit_offset(sql_text)

    # 关键信息校验
    if not parsed.table:
        raise ValueError("E002")

    # 计算置信度
    parsed.confidence = _calculate_confidence(parsed)

    # 低置信度警告
    if parsed.confidence < CONF_LOW:
        parsed.warnings.append("输入信息不完整，结果可能不准确")

    return parsed


def generate_sql(parsed: ParsedQuery) -> str:
    """
    根据解析结果生成标准 SQL 语句。

    参数:
        parsed: 解析后的查询对象

    返回:
        标准 SQL 字符串
    """
    if not parsed.table:
        raise ValueError("E002")

    # 构建 SELECT 语句（默认处理 SELECT，其他类型可扩展）
    fields_str = ", ".join(parsed.fields) if parsed.fields else "*"
    sql = f"SELECT {fields_str} FROM {parsed.table}"

    # WHERE 条件
    if parsed.conditions:
        where_str = " AND ".join(parsed.conditions)
        sql += f" WHERE {where_str}"

    # ORDER BY
    if parsed.order_by:
        sql += f" ORDER BY {parsed.order_by}"

    # LIMIT
    if parsed.limit is not None:
        sql += f" LIMIT {parsed.limit}"

    # OFFSET
    if parsed.offset is not None:
        sql += f" OFFSET {parsed.offset}"

    return sql


def format_output(parsed: ParsedQuery, sql: str) -> Dict[str, Any]:
    """
    按约定格式组织输出。

    参数:
        parsed: 解析后的查询对象
        sql: 生成的 SQL 语句

    返回:
        格式化输出字典
    """
    # 置信度标注
    if parsed.confidence >= CONF_HIGH:
        confidence_label = "直接输出"
    elif parsed.confidence >= CONF_MEDIUM:
        confidence_label = "建议复核"
    else:
        confidence_label = "[需核实]"

    return {
        "sql": sql,
        "parsed": parsed.to_dict(),
        "confidence_label": confidence_label,
        "warnings": parsed.warnings,
    }


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------

def process_input(input_text: str) -> Dict[str, Any]:
    """
    标准处理流程：解析 -> 生成 -> 校验 -> 输出。

    参数:
        input_text: 用户输入的 SQL 文本

    返回:
        格式化输出字典
    """
    try:
        # Step 1: 解析
        parsed = parse_sql_query(input_text)

        # Step 2: 生成 SQL
        sql = generate_sql(parsed)

        # Step 3: 输出格式化
        result = format_output(parsed, sql)

        # Step 4: 自查（字段完整性、格式正确性）
        if not result["sql"]:
            raise ValueError("E009")

        return result

    except ValueError as e:
        # 错误码处理
        error_code = str(e)
        if error_code in ERROR_MESSAGES:
            raise RuntimeError(f"{error_code}: {ERROR_MESSAGES[error_code]}")
        raise
    except Exception:
        # 兜底异常
        raise RuntimeError(f"E010: {ERROR_MESSAGES['E010']}")


# ---------------------------------------------------------------------------
# 自检逻辑（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值（大小比较/区间判断），避免依赖精确值。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("[SELFTEST] 开始自检...")

    # 测试样例（硬编码）
    test_cases = [
        {
            "name": "完整 SELECT 查询",
            "input": "SELECT id, name, age FROM users WHERE age > 18 AND status = 'active' ORDER BY created_at DESC LIMIT 10",
            "expect_table": True,
            "expect_fields": True,
            "expect_conditions": True,
            "expect_order": True,
            "expect_limit": True,
            "expect_conf_high": True,  # 应接近 1.0
        },
        {
            "name": "简单查询",
            "input": "SELECT * FROM products",
            "expect_table": True,
            "expect_fields": True,
            "expect_conditions": False,
            "expect_order": False,
            "expect_limit": False,
            "expect_conf_medium": True,  # 0.7 左右
        },
        {
            "name": "UPDATE 语句",
            "input": "UPDATE users SET age = 30 WHERE id = 1",
            "expect_table": True,
            "expect_fields": False,      # SELECT 字段不存在
            "expect_conditions": True,
            "expect_order": False,
            "expect_limit": False,
            "expect_conf_medium": True,  # 0.6 左右
        },
        {
            "name": "无表名（应报错）",
            "input": "SELECT * FROM",
            "expect_error": True,
        },
        {
            "name": "空输入（应报错）",
            "input": "",
            "expect_error": True,
        },
    ]

    passed_count = 0

    for case in test_cases:
        case_name = case["name"]
        print(f"  [用例] {case_name}")

        try:
            # 执行解析
            parsed = parse_sql_query(case["input"])

            # 如果期望报错但未报错，则失败
            if case.get("expect_error", False):
                print(f"    [失败] 期望报错但未报错")
                return False

            # 生成 SQL
            sql = generate_sql(parsed)

            # 验证表名
            if case.get("expect_table") and not parsed.table:
                print(f"    [失败] 表名未提取")
                return False

            # 验证字段
            if case.get("expect_fields") and not parsed.fields:
                print(f"    [失败] 字段未提取")
                return False

            # 验证条件
            if case.get("expect_conditions") and not parsed.conditions:
                print(f"    [失败] 条件未提取")
                return False

            # 验证 ORDER BY
            if case.get("expect_order") and not parsed.order_by:
                print(f"    [失败] ORDER BY 未提取")
                return False

            # 验证 LIMIT
            if case.get("expect_limit") and parsed.limit is None:
                print(f"    [失败] LIMIT 未提取")
                return False

            # 验证置信度（宽松判断）
            if case.get("expect_conf_high"):
                # 高置信度应 >= 0.9
                if parsed.confidence < 0.9:
                    print(f"    [失败] 置信度 {parsed.confidence:.4f} 低于预期 0.9")
                    return False
            elif case.get("expect_conf_medium"):
                # 中等置信度应在 0.5 ~ 0.9 之间
                if not (0.5 <= parsed.confidence < 0.9):
                    print(f"    [失败] 置信度 {parsed.confidence:.4f} 不在预期区间 [0.5, 0.9)")
                    return False

            # 验证 SQL 生成成功
            if not sql or len(sql) < 10:
                print(f"    [失败] SQL 生成异常: {sql}")
                return False

            print(f"    [通过] SQL: {sql}, 置信度: {parsed.confidence:.4f}")
            passed_count += 1

        except ValueError as e:
            # 期望报错的情况
            if case.get("expect_error", False):
                error_code = str(e)
                if error_code in ERROR_MESSAGES:
                    print(f"    [通过] 正确抛出错误 {error_code}")
                    passed_count += 1
                    continue
                else:
                    print(f"    [失败] 未知错误码: {error_code}")
                    return False
            else:
                print(f"    [失败] 意外异常: {e}")
                return False
        except Exception as e:
            print(f"    [失败] 未预期异常: {e}")
            return False

    # 额外测试：生成 SQL 完整性
    print("  [用例] SQL 生成完整性")
    try:
        parsed = parse_sql_query("SELECT a, b FROM test WHERE x = 1 ORDER BY y LIMIT 5")
        sql = generate_sql(parsed)
        # 宽松验证：SQL 应包含关键子句
        if not sql or "SELECT" not in sql.upper():
            print("    [失败] SQL 缺少 SELECT")
            return False
        if "FROM" not in sql.upper():
            print("    [失败] SQL 缺少 FROM")
            return False
        if "WHERE" not in sql.upper():
            print("    [失败] SQL 缺少 WHERE")
            return False
        if "ORDER BY" not in sql.upper():
            print("    [失败] SQL 缺少 ORDER BY")
            return False
        if "LIMIT" not in sql.upper():
            print("    [失败] SQL 缺少 LIMIT")
            return False
        print(f"    [通过] SQL 完整: {sql}")
        passed_count += 1
    except Exception as e:
        print(f"    [失败] SQL 生成异常: {e}")
        return False

    # 汇总
    total = len(test_cases) + 1
    print(f"[SELFTEST] 完成: {passed_count}/{total} 用例通过")

    if passed_count == total:
        print("[SELFTEST] 全部通过 ✔")
        return True
    else:
        print("[SELFTEST] 存在失败用例 ✘")
        return False


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    命令行主入口。

    支持:
      --selftest: 运行离线自检
      直接传入 SQL 文本: 处理并输出结果
    """
    parser = argparse.ArgumentParser(
        description="SQL查询工具（go-sqlbuilder 风格）",
        epilog="示例: python main.py \"SELECT * FROM users WHERE age > 18\""
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    parser.add_argument(
        "--sql_text",
        nargs="?",
        default=None,
        help="待处理的 SQL 查询文本",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"E007: {ERROR_MESSAGES['E007']} - {e}")
            return 1

    # 处理模式
    if not args.sql_text:
        print(f"E001: {ERROR_MESSAGES['E001']}")
        print("提示: 使用 --selftest 运行自检，或提供 SQL 文本")
        return 1

    try:
        result = process_input(args.sql_text)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"SQL: {result['sql']}")
            print(f"置信度: {result['parsed']['confidence']:.2%} ({result['confidence_label']})")
            if result["warnings"]:
                print(f"警告: {'; '.join(result['warnings'])}")
            print(f"表: {result['parsed']['table']}")
            if result["parsed"]["fields"]:
                print(f"字段: {', '.join(result['parsed']['fields'])}")
            if result["parsed"]["conditions"]:
                print(f"条件: {', '.join(result['parsed']['conditions'])}")
            if result["parsed"]["order_by"]:
                print(f"排序: {result['parsed']['order_by']}")
            if result["parsed"]["limit"] is not None:
                print(f"限制: {result['parsed']['limit']}")

        return 0

    except RuntimeError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"E010: {ERROR_MESSAGES['E010']} - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
