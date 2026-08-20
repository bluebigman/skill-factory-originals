#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - haskell-relational-record 解析与操作工具

本脚本实现 haskell-relational-record 的核心功能：
1. 解析 Haskell 类型声明（data/newtype/type）
2. 生成对应的关系映射（字段名、类型、约束）
3. 生成 SQL 建表语句
4. 支持批量处理多个 Haskell 模块
5. 支持自定义输出模板

支持 --selftest 离线自检（真实调用核心处理链路）。
"""

import argparse
import json
import re
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量与配置
# ============================================================

# 错误码与标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理错误：{detail}",
    "E007": "文件读取失败：{detail}",
    "E008": "URL处理失败：{detail}",
    "E009": "输出写入失败：{detail}",
    "E010": "未知错误：{detail}",
    "E011": "Haskell类型解析失败：{detail}",
    "E012": "不支持的Haskell类型：{detail}",
}

# 置信度阈值
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85

# Haskell 类型到 SQL 类型的映射
HASKELL_TO_SQL_TYPES = {
    "Int": "INTEGER",
    "Integer": "BIGINT",
    "Float": "REAL",
    "Double": "DOUBLE PRECISION",
    "Bool": "BOOLEAN",
    "Char": "CHAR(1)",
    "String": "TEXT",
    "Text": "TEXT",
    "ByteString": "BYTEA",
    "UTCTime": "TIMESTAMP",
    "Day": "DATE",
}

# 默认输出模板
DEFAULT_TEMPLATE = {
    "status": "success",
    "confidence": 0,
    "data": [],
    "warnings": [],
    "errors": [],
    "generated_at": None,
}


# ============================================================
# 核心数据结构与工具函数
# ============================================================

class ProcessError(Exception):
    """处理流程异常，携带错误码。"""
    def __init__(self, code: str, **kwargs):
        self.code = code
        self.kwargs = kwargs
        self.message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"]).format(**kwargs)
        super().__init__(self.message)


def validate_input(raw_input: Any) -> None:
    """校验输入非空（错误码 E001）。"""
    if raw_input is None:
        raise ProcessError("E001")
    if isinstance(raw_input, str) and not raw_input.strip():
        raise ProcessError("E001")
    if isinstance(raw_input, (list, dict)) and len(raw_input) == 0:
        raise ProcessError("E001")


def validate_required_fields(data: Dict[str, Any], required: List[str]) -> None:
    """校验关键信息是否完整（错误码 E002）。"""
    missing = [f for f in required if f not in data or data[f] is None]
    if missing:
        raise ProcessError("E002", missing="、".join(missing))


def validate_format(data: Any, expected_type: type, example: str) -> None:
    """校验输入格式（错误码 E003）。"""
    if not isinstance(data, expected_type):
        raise ProcessError("E003", example=example)


def check_boundary(request: str) -> None:
    """检查是否超出能力边界（错误码 E004）。"""
    forbidden_keywords = ["网络", "外部服务", "实时查询", "在线", "互联网"]
    for kw in forbidden_keywords:
        if kw in request:
            raise ProcessError("E004", suggestion="请提供本地Haskell代码或文件进行处理")


def calculate_confidence(data: List[Dict[str, Any]]) -> int:
    """
    计算置信度（基于解析完整性和类型映射覆盖率）。
    """
    if not data:
        return 0
    
    total_fields = 0
    mapped_fields = 0
    for item in data:
        for field in item.get("fields", []):
            total_fields += 1
            if field.get("sql_type") and field["sql_type"] != "UNKNOWN":
                mapped_fields += 1
    
    ratio = mapped_fields / total_fields if total_fields > 0 else 0
    return int(ratio * 100)


def annotate_confidence(confidence: int) -> Tuple[int, Optional[str]]:
    """
    依据置信度标注结果。
    返回：(置信度, 标注信息)
    """
    if confidence >= HIGH_CONFIDENCE:
        return confidence, None
    elif confidence >= MEDIUM_CONFIDENCE:
        return confidence, "建议复核"
    else:
        return confidence, "[需核实]"


# ============================================================
# Haskell 类型解析核心逻辑
# ============================================================

def parse_haskell_type_declaration(code: str) -> List[Dict[str, Any]]:
    """
    解析 Haskell 类型声明（data/newtype/type）。
    返回结构化关系映射列表。
    
    支持格式：
    - data User = User { id :: Int, name :: String }
    - newtype UserId = UserId Int
    - type UserName = String
    """
    results = []
    
    # 匹配 data/newtype 声明（记录语法）
    record_pattern = re.compile(
        r'(?:data|newtype)\s+(\w+)\s*(?:=\s*\w+\s*)?\{([^}]+)\}',
        re.MULTILINE
    )
    
    # 匹配 data/newtype 声明（简单语法）
    simple_pattern = re.compile(
        r'(?:data|newtype)\s+(\w+)\s*=\s*(\w+)\s+([\w\s]+)',
        re.MULTILINE
    )
    
    # 匹配 type 别名
    type_pattern = re.compile(
        r'type\s+(\w+)\s*=\s*([\w\s]+)',
        re.MULTILINE
    )
    
    # 解析记录语法
    for match in record_pattern.finditer(code):
        type_name = match.group(1)
        fields_str = match.group(2)
        
        fields = []
        field_pattern = re.compile(r'(\w+)\s*::\s*([\w\s\[\]\(\)]+)')
        for field_match in field_pattern.finditer(fields_str):
            field_name = field_match.group(1)
            field_type = field_match.group(2).strip()
            
            # 处理 Maybe 类型（递归提取内部类型）
            is_nullable = False
            base_type = field_type
            if field_type.startswith("Maybe "):
                is_nullable = True
                base_type = field_type.replace("Maybe ", "").strip()
                # 递归处理内部类型（如 Maybe (Maybe Int)）
                while base_type.startswith("Maybe "):
                    base_type = base_type.replace("Maybe ", "").strip()
            
            # 处理列表类型
            is_list = base_type.startswith("[") and base_type.endswith("]")
            if is_list:
                base_type = base_type[1:-1].strip()
                # 递归处理列表内部类型
                while base_type.startswith("[") and base_type.endswith("]"):
                    base_type = base_type[1:-1].strip()
            
            # 映射 SQL 类型
            sql_type = HASKELL_TO_SQL_TYPES.get(base_type, "UNKNOWN")
            if sql_type == "UNKNOWN":
                raise ProcessError("E012", detail=f"无法解析类型: {field_type}")
            
            if is_nullable:
                sql_type = f"NULLABLE {sql_type}"
            if is_list:
                sql_type = f"ARRAY<{sql_type}>"
            
            fields.append({
                "name": field_name,
                "haskell_type": field_type,
                "sql_type": sql_type,
                "nullable": is_nullable,
                "is_list": is_list,
            })
        
        results.append({
            "type": "record",
            "name": type_name,
            "fields": fields,
            "source": "data/newtype record",
        })
    
    # 解析简单语法
    for match in simple_pattern.finditer(code):
        type_name = match.group(1)
        constructor = match.group(2)
        type_args = match.group(3).strip().split()
        
        fields = []
        for i, arg_type in enumerate(type_args):
            arg_type = arg_type.strip()
            
            # 处理 Maybe 类型
            is_nullable = False
            base_type = arg_type
            if arg_type.startswith("Maybe "):
                is_nullable = True
                base_type = arg_type.replace("Maybe ", "").strip()
                while base_type.startswith("Maybe "):
                    base_type = base_type.replace("Maybe ", "").strip()
            
            sql_type = HASKELL_TO_SQL_TYPES.get(base_type, "UNKNOWN")
            if sql_type == "UNKNOWN":
                raise ProcessError("E012", detail=f"无法解析类型: {arg_type}")
            
            if is_nullable:
                sql_type = f"NULLABLE {sql_type}"
            
            fields.append({
                "name": f"field{i+1}",
                "haskell_type": arg_type,
                "sql_type": sql_type,
                "nullable": is_nullable,
                "is_list": False,
            })
        
        results.append({
            "type": "simple",
            "name": type_name,
            "constructor": constructor,
            "fields": fields,
            "source": "data/newtype simple",
        })
    
    # 解析 type 别名
    for match in type_pattern.finditer(code):
        type_name = match.group(1)
        target_type = match.group(2).strip()
        
        # 处理 Maybe 类型
        is_nullable = False
        base_type = target_type
        if target_type.startswith("Maybe "):
            is_nullable = True
            base_type = target_type.replace("Maybe ", "").strip()
            while base_type.startswith("Maybe "):
                base_type = base_type.replace("Maybe ", "").strip()
        
        sql_type = HASKELL_TO_SQL_TYPES.get(base_type, "UNKNOWN")
        if sql_type == "UNKNOWN":
            raise ProcessError("E012", detail=f"无法解析类型: {target_type}")
        
        if is_nullable:
            sql_type = f"NULLABLE {sql_type}"
        
        results.append({
            "type": "alias",
            "name": type_name,
            "target_type": target_type,
            "sql_type": sql_type,
            "fields": [],
            "source": "type alias",
        })
    
    if not results:
        raise ProcessError("E011", detail="未找到有效的Haskell类型声明")
    
    return results


def generate_sql_create_table(relation: Dict[str, Any]) -> str:
    """
    根据关系映射生成 SQL 建表语句。
    """
    if relation["type"] == "alias":
        return f"-- {relation['name']} 是 {relation['target_type']} 的类型别名，无需建表"
    
    table_name = relation["name"].lower()
    columns = []
    
    for field in relation["fields"]:
        col_name = field["name"]
        sql_type = field["sql_type"]
        
        # 处理 NULLABLE
        if sql_type.startswith("NULLABLE "):
            sql_type = sql_type.replace("NULLABLE ", "")
            nullable_str = "NULL"
        else:
            nullable_str = "NOT NULL"
        
        # 处理 ARRAY
        if sql_type.startswith("ARRAY<"):
            sql_type = sql_type.replace("ARRAY<", "").replace(">", "")
        
        columns.append(f"    {col_name} {sql_type} {nullable_str}")
    
    if not columns:
        return f"-- {relation['name']} 无字段定义"
    
    sql = f"CREATE TABLE {table_name} (\n"
    sql += ",\n".join(columns)
    sql += "\n);"
    
    return sql


def generate_relation_mapping(relation: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成关系映射的 JSON 表示。
    """
    mapping = {
        "relation_name": relation["name"],
        "relation_type": relation["type"],
        "fields": [],
    }
    
    if relation["type"] == "alias":
        mapping["target_type"] = relation["target_type"]
        mapping["sql_type"] = relation["sql_type"]
    else:
        for field in relation["fields"]:
            mapping["fields"].append({
                "field_name": field["name"],
                "haskell_type": field["haskell_type"],
                "sql_type": field["sql_type"],
                "nullable": field["nullable"],
                "is_list": field["is_list"],
            })
    
    return mapping


# ============================================================
# 核心处理流程
# ============================================================

def parse_input(raw_input: Any) -> List[Dict[str, Any]]:
    """
    解析输入内容，识别 Haskell 类型声明。
    支持：Haskell 代码字符串、JSON 字符串、字典、列表。
    """
    if isinstance(raw_input, str):
        # 尝试解析JSON（可能是结构化输入）
        try:
            parsed = json.loads(raw_input)
            if isinstance(parsed, (dict, list)):
                return parse_input(parsed)
        except json.JSONDecodeError:
            pass
        
        # 作为 Haskell 代码解析
        try:
            return parse_haskell_type_declaration(raw_input)
        except ProcessError:
            raise
    
    if isinstance(raw_input, dict):
        # 可能是单个关系映射
        if "name" in raw_input and "fields" in raw_input:
            return [raw_input]
        # 可能是包含代码的字典
        if "code" in raw_input:
            return parse_haskell_type_declaration(raw_input["code"])
        return [raw_input]
    
    if isinstance(raw_input, list):
        result = []
        for item in raw_input:
            if isinstance(item, dict):
                if "code" in item:
                    result.extend(parse_haskell_type_declaration(item["code"]))
                else:
                    result.append(item)
            elif isinstance(item, str):
                result.extend(parse_haskell_type_declaration(item))
        return result
    
    raise ProcessError("E003", example="Haskell代码字符串或JSON数组")


def process_data(raw_input: Any, custom_fields: Optional[List[str]] = None,
                 output_format: str = "json", template: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    执行核心处理流程。
    返回结构化结果，包含置信度标注。
    """
    result = dict(DEFAULT_TEMPLATE)
    if template:
        # 合并用户模板
        for key, value in template.items():
            if key not in ("data", "errors", "warnings"):
                result[key] = value
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    
    try:
        # 解析输入
        validate_input(raw_input)
        relations = parse_input(raw_input)
        
        # 处理每个关系
        processed_relations = []
        for relation in relations:
            # 生成 SQL 和映射
            relation_copy = dict(relation)
            relation_copy["sql_create"] = generate_sql_create_table(relation)
            relation_copy["mapping"] = generate_relation_mapping(relation)
            
            # 自定义字段过滤
            if custom_fields:
                if "fields" in relation_copy:
                    relation_copy["fields"] = [
                        f for f in relation_copy["fields"] 
                        if f.get("name") in custom_fields
                    ]
                if "mapping" in relation_copy and "fields" in relation_copy["mapping"]:
                    relation_copy["mapping"]["fields"] = [
                        f for f in relation_copy["mapping"]["fields"]
                        if f.get("field_name") in custom_fields
                    ]
            
            processed_relations.append(relation_copy)
        
        # 计算置信度
        confidence = calculate_confidence(processed_relations)
        result["confidence"] = confidence
        confidence_note = annotate_confidence(confidence)
        if confidence_note[1]:
            result["warnings"].append(confidence_note[1])
        
        # 组织输出
        result["data"] = processed_relations
        
        # 骨架模式：只保留关键信息
        if output_format == "skeleton":
            result["data"] = [
                {
                    "name": r["name"],
                    "type": r["type"],
                    "field_count": len(r.get("fields", [])),
                }
                for r in processed_relations
            ]
    
    except ProcessError as e:
        result["status"] = "error"
        result["errors"].append({"code": e.code, "message": e.message})
        result["confidence"] = 0
    
    return result


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """按指定格式输出结果。"""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        lines.append(f"状态: {result['status']}")
        lines.append(f"置信度: {result['confidence']}%")
        lines.append(f"生成时间: {result.get('generated_at', 'N/A')}")
        
        for warning in result["warnings"]:
            lines.append(f"警告: {warning}")
        
        for error in result["errors"]:
            lines.append(f"错误: {error['code']} - {error['message']}")
        
        for item in result["data"]:
            lines.append(f"\n关系: {item.get('name', 'N/A')} ({item.get('type', 'N/A')})")
            if "sql_create" in item:
                lines.append("SQL建表语句:")
                lines
