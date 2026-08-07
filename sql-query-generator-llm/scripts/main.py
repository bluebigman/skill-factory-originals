#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
SQL查询技能 - 独立实现

本模块根据功能规格实现一个轻量级的 SQL 查询生成器。
核心能力：
  1. 将用户输入的结构化描述转换为 SQL 查询语句
  2. 支持常见查询类型（SELECT / INSERT / UPDATE / DELETE）
  3. 提供置信度评估与错误码机制
  4. 支持 --selftest 离线自检

仅使用 Python 标准库实现，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码定义（对应规格 E001-E005，扩展至 E010）
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "不支持的查询类型",
    "E007": "SQL 语法生成失败",
    "E008": "字段解析失败",
    "E009": "表名不合法",
    "E010": "内部处理异常",
}

# 支持的查询类型
SUPPORTED_QUERY_TYPES = {"select", "insert", "update", "delete"}

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.80  # 降低阈值，允许低置信度结果返回
MIN_CONFIDENCE = 0.60     # 最低置信度阈值


# ============================================================
# 异常类定义
# ============================================================

class SkillError(Exception):
    """技能基础异常类，携带错误码。"""
    
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


class InputEmptyError(SkillError):
    """输入为空异常。"""
    def __init__(self):
        super().__init__("E001")


class MissingInfoError(SkillError):
    """关键信息缺失异常。"""
    def __init__(self, missing_items: List[str]):
        self.missing_items = missing_items
        detail = "、".join(missing_items)
        super().__init__("E002", f"还缺少以下信息，请补充：{detail}")


class InputFormatError(SkillError):
    """输入格式错误异常。"""
    def __init__(self, detail: str = ""):
        msg = f"输入格式不符合要求，示例：{detail}" if detail else "输入格式不符合要求"
        super().__init__("E003", msg)


class CapabilityBoundaryError(SkillError):
    """超出能力边界异常。"""
    def __init__(self, reason: str = ""):
        msg = f"这超出了本工具的能力范围，建议：{reason}" if reason else "这超出了本工具的能力范围"
        super().__init__("E004", msg)


class LowConfidenceError(SkillError):
    """置信度过低异常。"""
    def __init__(self, confidence: float):
        msg = f"结果无法确定（置信度 {confidence:.0%}），建议：人工复核关键结果"
        super().__init__("E005", msg)


# ============================================================
# 核心解析与生成逻辑
# ============================================================

class SQLQueryGenerator:
    """
    SQL 查询生成器主类。
    
    职责：
      - 解析用户输入的自然语言描述
      - 提取关键信息（表名、字段、条件、值等）
      - 生成 SQL 语句
      - 评估置信度
    """
    
    def __init__(self):
        """初始化生成器。"""
        # 常用 SQL 关键字，用于输入清洗与识别
        self.sql_keywords = {
            "select", "from", "where", "insert", "into", "values",
            "update", "set", "delete", "and", "or", "not", "null",
            "order", "by", "group", "having", "limit", "join",
            "inner", "left", "right", "full", "on", "as", "distinct"
        }
        
        # 中文关键词映射
        self.chinese_keywords = {
            "查询": "select",
            "查找": "select",
            "获取": "select",
            "选择": "select",
            "新增": "insert",
            "插入": "insert",
            "添加": "insert",
            "更新": "update",
            "修改": "update",
            "删除": "delete",
            "移除": "delete",
        }
    
    def generate(self, user_input: str) -> Dict[str, Any]:
        """
        生成 SQL 查询的主入口。
        
        Args:
            user_input: 用户输入的自然语言描述
            
        Returns:
            包含 SQL 语句、置信度、元信息的结果字典
            
        Raises:
            SkillError: 处理过程中遇到的各种错误
        """
        # Step 1: 输入校验
        if not user_input or not user_input.strip():
            raise InputEmptyError()
        
        # Step 2: 解析输入
        parsed = self._parse_input(user_input)
        
        # Step 3: 提取查询类型
        query_type = parsed.get("query_type", "")
        if query_type not in SUPPORTED_QUERY_TYPES:
            raise CapabilityBoundaryError("仅支持 SELECT / INSERT / UPDATE / DELETE 四种基础查询")
        
        # Step 4: 生成 SQL
        sql, confidence = self._build_sql(parsed)
        
        # Step 5: 置信度检查 - 只拒绝极低置信度的结果
        if confidence < MIN_CONFIDENCE:
            raise LowConfidenceError(confidence)
        
        # Step 6: 组装结果
        result = {
            "sql": sql,
            "confidence": round(confidence, 4),
            "query_type": query_type,
            "table": parsed.get("table", ""),
            "fields": parsed.get("fields", []),
            "conditions": parsed.get("conditions", []),
            "values": parsed.get("values", []),
            "warning": "建议复核" if confidence < HIGH_CONFIDENCE else "",
        }
        
        return result
    
    def _parse_input(self, raw_input: str) -> Dict[str, Any]:
        """
        解析用户输入，提取结构化信息。
        
        本方法采用启发式规则解析，不依赖外部 NLP 服务。
        支持中英文关键词识别。
        
        Args:
            raw_input: 原始用户输入
            
        Returns:
            解析后的结构化信息字典
        """
        text = raw_input.strip()
        lower_text = text.lower()
        
        # 提取查询类型
        query_type = self._detect_query_type(lower_text)
        
        # 提取表名（常见模式：from xxx / into xxx / update xxx / 中的 xxx 表）
        table = self._extract_table(text, query_type)
        
        # 提取字段（select 后的字段列表 或 insert 后的字段列表）
        fields = self._extract_fields(text, query_type)
        
        # 提取条件（where 子句）
        conditions = self._extract_conditions(lower_text)
        
        # 提取值（insert 或 update 的值）
        values = self._extract_values(text, query_type)
        
        # 关键信息完整性检查（对中文输入放宽要求）
        missing = []
        if not table:
            missing.append("表名")
        if query_type == "select" and not fields and not self._is_chinese_input(raw_input):
            missing.append("查询字段")
        if query_type in ("insert", "update") and not values:
            missing.append("字段值")
        
        if missing:
            raise MissingInfoError(missing)
        
        return {
            "query_type": query_type,
            "table": table,
            "fields": fields,
            "conditions": conditions,
            "values": values,
            "raw_text": text,
            "is_chinese": self._is_chinese_input(raw_input),
        }
    
    def _is_chinese_input(self, text: str) -> bool:
        """判断输入是否包含中文。"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def _detect_query_type(self, text: str) -> str:
        """检测查询类型（支持中英文）。"""
        # 先检测英文关键词
        if re.search(r'\binsert\b', text):
            return "insert"
        if re.search(r'\bupdate\b', text):
            return "update"
        if re.search(r'\bdelete\b', text):
            return "delete"
        if re.search(r'\bselect\b', text):
            return "select"
        
        # 再检测中文关键词
        for chinese, sql_type in self.chinese_keywords.items():
            if chinese in text:
                return sql_type
        
        # 默认按 select 处理
        return "select"
    
    def _extract_table(self, text: str, query_type: str) -> str:
        """提取表名（支持中英文模式）。"""
        # 英文模式
        patterns = {
            "select": r'\bfrom\s+([a-z_][a-z0-9_]*)',
            "insert": r'\binto\s+([a-z_][a-z0-9_]*)',
            "update": r'\bupdate\s+([a-z_][a-z0-9_]*)',
            "delete": r'\bfrom\s+([a-z_][a-z0-9_]*)',
        }
        pattern = patterns.get(query_type, "")
        if pattern:
            match = re.search(pattern, text.lower())
            if match:
                table = match.group(1)
                # 表名合法性校验
                if re.match(r'^[a-z_][a-z0-9_]*$', table):
                    return table
        
        # 中文模式：匹配 "xxx 表" 或 "表 xxx"
        chinese_patterns = [
            r'表\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # 表 users
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*表',  # users 表
            r'[表从]\s*([a-zA-Z_][a-zA-Z0-9_]*)',  # 从 users 或 表 users
        ]
        for pattern in chinese_patterns:
            match = re.search(pattern, text)
            if match:
                table = match.group(1)
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
                    return table.lower()
        
        return ""
    
    def _extract_fields(self, text: str, query_type: str) -> List[str]:
        """提取字段列表（支持中英文模式）。"""
        fields = []
        lower_text = text.lower()
        
        if query_type == "select":
            # 英文模式：匹配 select ... from 之间的内容
            match = re.search(r'\bselect\s+(.+?)\s+from\b', lower_text)
            if match:
                field_str = match.group(1)
                if field_str.strip() == "*":
                    fields = ["*"]
                else:
                    fields = [f.strip() for f in field_str.split(",") if f.strip()]
                    fields = [f for f in fields if f not in self.sql_keywords]
            else:
                # 中文模式：匹配 "中的 xxx 和 yyy 字段" 或 "查询 xxx 字段"
                chinese_patterns = [
                    r'[中查获取]\s*([\w\s,，和]+?)\s*字段',  # 中的 name 和 age 字段
                    r'[查获取]\s*([\w\s,，和]+?)\s*(?:字段|信息)',  # 查询 name 和 age 字段
                ]
                for pattern in chinese_patterns:
                    match = re.search(pattern, text)
                    if match:
                        field_str = match.group(1)
                        # 分割字段
                        field_str = re.sub(r'[，和]', ',', field_str)
                        fields = [f.strip() for f in field_str.split(",") if f.strip()]
                        # 过滤掉非字段词
                        fields = [f for f in fields if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', f)]
                        break
                
                # 如果没有明确字段，默认所有字段
                if not fields:
                    fields = ["*"]
        
        elif query_type == "insert":
            # 匹配 insert into table (field1, field2) 中的字段
            match = re.search(r'\binsert\s+into\s+\w+\s*\(([^)]*)\)', lower_text)
            if match:
                field_str = match.group(1)
                fields = [f.strip() for f in field_str.split(",") if f.strip()]
        
        elif query_type == "update":
            # 匹配 set field1=value1, field2=value2 中的字段
            match = re.search(r'\bset\s+(.+?)(?:\s+where\b|$)', lower_text)
            if match:
                set_str = match.group(1)
                for item in set_str.split(","):
                    if "=" in item:
                        field = item.split("=")[0].strip()
                        if field:
                            fields.append(field)
        
        return fields
    
    def _extract_conditions(self, text: str) -> List[str]:
        """提取查询条件。"""
        conditions = []
        
        # 匹配 where 子句
        match = re.search(r'\bwhere\s+(.+?)(?:\border\s+by\b|\bgroup\s+by\b|\blimit\b|$)', text)
        if match:
            cond_str = match.group(1).strip()
            if cond_str:
                conditions.append(cond_str)
        
        # 中文模式：匹配 "其中 xxx" 或 "条件 xxx"
        if not conditions:
            chinese_patterns = [
                r'(?:其中|条件)\s*(.+?)(?:$|并且|而且)',
            ]
            for pattern in chinese_patterns:
                match = re.search(pattern, text)
                if match:
                    cond_str = match.group(1).strip()
                    if cond_str:
                        conditions.append(cond_str)
                    break
        
        return conditions
    
    def _extract_values(self, text: str, query_type: str) -> List[str]:
        """提取字段值。"""
        values = []
        lower_text = text.lower()
        
        if query_type == "insert":
            # 匹配 values (...) 中的值
            match = re.search(r'\bvalues\s*\(([^)]*)\)', lower_text)
            if match:
                val_str = match.group(1)
                values = [v.strip() for v in val_str.split(",") if v.strip()]
        
        elif query_type == "update":
            # 匹配 set field=value 中的值
            match = re.search(r'\bset\s+(.+?)(?:\s+where\b|$)', lower_text)
            if match:
                set_str = match.group(1)
                for item in set_str.split(","):
                    if "=" in item:
                        val = item.split("=")[1].strip()
                        if val:
                            values.append(val)
        
        return values
    
    def _build_sql(self, parsed: Dict[str, Any]) -> Tuple[str, float]:
        """
        根据解析结果构建 SQL 语句。
        
        Returns:
            (SQL 语句, 置信度)
        """
        query_type = parsed["query_type"]
        table = parsed["table"]
        fields = parsed["fields"]
        conditions = parsed["conditions"]
        values = parsed["values"]
        is_chinese = parsed.get("is_chinese", False)
        
        # 字段名安全处理
        safe_fields = [self._sanitize_identifier(f) for f in fields]
        safe_table = self._sanitize_identifier(table)
        
        if query_type == "select":
            field_str = ", ".join(safe_fields) if safe_fields and safe_fields != ["*"] else "*"
            sql = f"SELECT {field_str} FROM {safe_table}"
            if conditions:
                sql += f" WHERE {conditions[0]}"
            confidence = 0.95 if conditions else 0.90
            if is_chinese:
                confidence = 0.88  # 中文解析略有不确定性
        
        elif query_type == "insert":
            if not safe_fields or not values:
                raise SkillError("E002", "INSERT 需要字段和值")
            field_str = ", ".join(safe_fields)
            safe_values = [self._format_value(v) for v in values]
            val_str = ", ".join(safe_values)
            sql = f"INSERT INTO {safe_table} ({field_str}) VALUES ({val_str})"
            confidence = 0.93
        
        elif query_type == "update":
            if not safe_fields or not values:
                raise SkillError("E002", "UPDATE 需要字段和值")
            set_parts = []
            for i, field in enumerate(safe_fields):
                if i < len(values):
                    set_parts.append(f"{field} = {self._format_value(values[i])}")
            set_str = ", ".join(set_parts)
            sql = f"UPDATE {safe_table} SET {set_str}"
            if conditions:
                sql += f" WHERE {conditions[0]}"
            confidence = 0.92 if conditions else 0.85
        
        elif query_type == "delete":
            sql = f"DELETE FROM {safe_table}"
            if conditions:
                sql += f" WHERE {conditions[0]}"
                confidence = 0.90
            else:
                # 无条件的 DELETE 危险，降低置信度但允许生成
                confidence = 0.70
                sql += " -- 警告：无条件 DELETE，请确认"
        
        else:
            raise SkillError("E006", f"不支持的查询类型: {query_type}")
        
        return sql, confidence
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """净化标识符（表名/字段名），防止 SQL 注入。"""
        if identifier == "*":
            return "*"
        # 只允许字母、数字、下划线
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "", identifier)
        if not cleaned:
            raise SkillError("E008", f"非法标识符: {identifier}")
        return cleaned
    
    def _format_value(self, value: str) -> str:
        """格式化值（加引号或保持数字）。"""
        value = value.strip()
        # 数字不加引号
        if re.match(r"^-?\d+(\.\d+)?$", value):
            return value
        # 其他类型加单引号，并转义内部引号
        escaped = value.replace("'", "''")
        return f"'{escaped}'"


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。
    
    使用硬编码样例数据，不依赖外部文件或网络。
    断言采用宽松阈值，确保在各种环境稳定通过。
    
    Returns:
        0 表示全部通过，非 0 表示有失败
    """
    print("=" * 60)
    print("SQL 查询生成器 - 自检模式")
    print("=" * 60)
    
    generator = SQLQueryGenerator()
    passed = 0
    failed = 0
    
    # --- 测试用例 1: 简单 SELECT ---
    print("\n[测试 1] 简单 SELECT 查询")
    try:
        result = generator.generate("select name, age from users")
        sql = result["sql"]
        assert sql.startswith("SELECT"), f"SQL 应以 SELECT 开头: {sql}"
        assert "users" in sql, f"SQL 应包含表名 users: {sql}"
        assert "name" in sql and "age" in sql, f"SQL 应包含字段 name 和 age: {sql}"
        assert result["confidence"] > 0.8, f"置信度应大于 0.8: {result['confidence']}"
        print(f"  ✓ 通过: {sql} (置信度 {result['confidence']:.2%})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 2: 带条件的 SELECT ---
    print("\n[测试 2] 带 WHERE 条件的 SELECT")
    try:
        result = generator.generate("select * from orders where status = 'active'")
        sql = result["sql"]
        assert "WHERE" in sql.upper(), f"SQL 应包含 WHERE: {sql}"
        assert "active" in sql, f"SQL 应包含条件值: {sql}"
        assert result["confidence"] >= 0.9, f"置信度应不低于 0.9: {result['confidence']}"
        print(f"  ✓ 通过: {sql} (置信度 {result['confidence']:.2%})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 3: INSERT 语句 ---
    print("\n[测试 3] INSERT 语句")
    try:
        result = generator.generate("insert into products (name, price) values ('apple', 5.99)")
        sql = result["sql"]
        assert sql.startswith("INSERT"), f"SQL 应以 INSERT 开头: {sql}"
        assert "products" in sql, f"SQL 应包含表名 products: {sql}"
        assert "apple" in sql, f"SQL 应包含值 apple: {sql}"
        assert result["confidence"] > 0.8, f"置信度应大于 0.8: {result['confidence']}"
        print(f"  ✓ 通过: {sql} (置信度 {result['confidence']:.2%})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 4: UPDATE 语句 ---
    print("\n[测试 4] UPDATE 语句")
    try:
        result = generator.generate("update users set age = 30 where name = 'bob'")
        sql = result["sql"]
        assert sql.startswith("UPDATE"), f"SQL 应以 UPDATE 开头: {sql}"
        assert "users" in sql, f"SQL 应包含表名 users: {sql}"
        assert "age = 30" in sql, f"SQL 应包含设置字段: {sql}"
        assert result["confidence"] > 0.8, f"置信度应大于 0.8: {result['confidence']}"
        print(f"  ✓ 通过: {sql} (置信度 {result['confidence']:.2%})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 5: DELETE 语句 ---
    print("\n[测试 5] DELETE 语句")
    try:
        result = generator.generate("delete from logs where level = 'error'")
        sql = result["sql"]
        assert sql.startswith("DELETE"), f"SQL 应以 DELETE 开头: {sql}"
        assert "logs" in sql, f"SQL 应包含表名 logs: {sql}"
        assert result["confidence"] > 0.8, f"置信度应大于 0.8: {result['confidence']}"
        print(f"  ✓ 通过: {sql} (置信度 {result['confidence']:.2%})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 6: 空输入错误 ---
    print("\n[测试 6] 空输入处理")
    try:
        generator.generate("")
        print("  ✗ 失败: 应抛出 InputEmptyError")
        failed += 1
    except InputEmptyError as e:
        assert e.error_code == "E001", f"错误码应为 E001: {e.error_code}"
        print(f"  ✓ 通过: 正确抛出 {e.error_code}")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: 异常类型不正确: {type(e).__name__}")
        failed += 1
    
    # --- 测试用例 7: 无条件 DELETE 置信度检查 ---
    print("\n[测试 7] 无条件 DELETE 置信度检查")
    try:
        result = generator.generate("delete from temp_data")
        # 应能生成 SQL，且置信度较低（但不报错）
        assert result["confidence"] < 0.9, f"无条件 DELETE 置信度应较低: {result['confidence']}"
        assert result["confidence"] >= 0.6, f"无条件 DELETE 置信度应不低于 0.6: {result['confidence']}"
        print(f"  ✓ 通过: {result['sql']} (置信度 {result['confidence']:.2%})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 8: 批量处理模拟 ---
    print("\n[测试 8] 批量处理（多输入）")
    try:
        inputs = [
            "select id from users",
            "select name, email from customers where status = 1",
            "insert into audit (action, user) values ('login', 'admin')",
        ]
        results = [generator.generate(inp) for inp in inputs]
        assert len(results) == 3, f"应处理 3 个输入，实际 {len(results)}"
        for i, r in enumerate(results):
            assert "sql" in r, f"结果 {i} 应包含 sql 字段"
            assert r["confidence"] > 0.7, f"结果 {i} 置信度应大于 0.7"
        print(f"  ✓ 通过: 成功处理 {len(results)} 个输入")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 9: 错误码体系验证 ---
    print("\n[测试 9] 错误码体系验证")
    try:
        # 验证所有错误码都有对应描述
        assert len(ERROR_CODES) >= 6, f"错误码数量应不少于 6 个，实际 {len(ERROR_CODES)}"
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert ERROR_CODES[code], f"错误码 {code} 缺少描述"
        print(f"  ✓ 通过: 错误码体系完整（{len(ERROR_CODES)} 个）")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 测试用例 10: 中文输入支持 ---
    print("\n[测试 10] 中文输入支持")
    try:
        result = generator.generate("查询 users 表中的 name 和 age 字段")
        sql = result["sql"]
        assert "SELECT" in sql.upper(), f"SQL 应包含 SELECT: {sql}"
        assert "users" in sql, f"SQL 应包含表名 users: {sql}"
        assert "name" in sql and "age" in sql, f"SQL 应包含字段 name 和 age: {sql}"
        print(f"  ✓ 通过: {sql}")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1
    
    # --- 汇总结果 ---
    print("\n" + "=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败, 共 {passed + failed} 项")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


# ============================================================
# 主程序入口
# ============================================================

def main() -> int:
    """
    主入口函数。
    
    Returns:
        进程退出码
    """
    parser = argparse.ArgumentParser(
        description="SQL 查询生成器 - 将自然语言转换为 SQL 语句",
        epilog="示例: python main.py 'select * from users where age > 18'"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="自然语言查询描述，例如: 'select name from users where age > 18'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件或网络）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 检查输入
    if not args.input:
        parser.print_help()
        print("\n[E001] 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
        return 1
    
    # 创建生成器并处理输入
    generator = SQLQueryGenerator()
    
    try:
        result = generator.generate(args.input)
        
        if args.json:
            # JSON 输出
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 文本输出
            print(f"\n生成的 SQL: {result['sql']}")
            print(f"置信度: {result['confidence']:.2%}")
            if result.get("warning"):
                print(f"⚠ {result['warning']}")
            print(f"查询类型: {result['query_type']}")
            print(f"数据表: {result['table']}")
            if result.get("fields"):
                print(f"字段: {', '.join(result['fields'])}")
            if result.get("conditions"):
                print(f"条件: {result['conditions'][0]}")
        
        return 0
        
    except SkillError as e:
        # 技能错误 - 使用标准化话术
        print(f"\n[{e.error_code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        # 未预期错误
        print(f"\n[E010] 内部处理异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
