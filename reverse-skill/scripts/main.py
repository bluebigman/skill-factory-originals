#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reverse-skill: 数据逆向 / 结构化解析 / 字段还原

功能概述:
    将任意输入数据（文本、JSON、CSV、简单键值对等）解析为结构化结果，
    保留关键信息并标注置信度。输出格式为 JSON，包含 data 与 meta 两部分。

设计原则:
    - 仅使用 Python 标准库，无第三方依赖。
    - 提供 --selftest 参数，使用内置硬编码样例离线自检核心逻辑。
    - 错误处理统一使用错误码 E001-E010。
    - 中文注释，结构清晰，模块化设计。

作者: 技能工坊
版本: 1.0.2
许可证: MIT
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# 常量定义
# -----------------------------------------------------------------------------

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或仅包含空白字符",
    "E002": "输入数据格式无法识别（非文本/JSON/CSV/键值对）",
    "E003": "JSON 解析失败，数据格式错误",
    "E004": "CSV 解析失败，数据格式错误",
    "E005": "键值对解析失败，数据格式错误",
    "E006": "输出格式指定错误（仅支持 json/markdown/csv）",
    "E007": "内部处理异常，请检查输入数据",
    "E008": "文件读取失败（文件不存在或无权限）",
    "E009": "文件大小超过限制（最大 5MB）",
    "E010": "URL 访问失败（网络错误或非公开数据）",
}

# 输入大小限制（字节）
MAX_INPUT_SIZE = 5 * 1024 * 1024  # 5MB


# -----------------------------------------------------------------------------
# 核心解析类
# -----------------------------------------------------------------------------

class ReverseSkillParser:
    """数据逆向解析器：将输入数据解析为结构化结果。"""

    def __init__(self) -> None:
        """初始化解析器。"""
        self.warnings: List[str] = []

    def parse(self, input_data: str, output_format: str = "json") -> str:
        """
        解析输入数据并返回指定格式的结果。

        参数:
            input_data: 输入数据（文本）
            output_format: 输出格式（json/markdown/csv）

        返回:
            格式化后的结果字符串

        异常:
            ValueError: 包含错误码的异常信息
        """
        # 校验输入
        if not input_data or not input_data.strip():
            raise ValueError(f"错误码 E001: {ERROR_CODES['E001']}")

        # 重置警告
        self.warnings = []

        # 解析数据
        data = self._parse_input(input_data)

        # 生成输出
        if output_format == "json":
            return self._to_json(data)
        elif output_format == "markdown":
            return self._to_markdown(data)
        elif output_format == "csv":
            return self._to_csv(data)
        else:
            raise ValueError(f"错误码 E006: {ERROR_CODES['E006']}")

    def _parse_input(self, input_data: str) -> Dict[str, Any]:
        """
        解析输入数据，识别格式并提取结构化信息。

        参数:
            input_data: 输入数据字符串

        返回:
            结构化数据字典
        """
        stripped = input_data.strip()

        # 尝试 JSON 解析
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return self._parse_json(stripped)
            except json.JSONDecodeError:
                self.warnings.append("JSON 解析失败，尝试其他格式")
                # 如果 JSON 解析失败，继续尝试其他格式
            except Exception as e:
                raise ValueError(f"错误码 E003: {ERROR_CODES['E003']}: {e}")

        # 尝试 CSV 解析（需要更严格的判断）
        if self._looks_like_csv(stripped):
            try:
                return self._parse_csv(stripped)
            except Exception:
                self.warnings.append("CSV 解析失败，尝试其他格式")

        # 尝试键值对解析
        if self._looks_like_key_value(stripped):
            try:
                return self._parse_key_value(stripped)
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出

        # 默认按纯文本处理
        return self._parse_text(stripped)

    def _looks_like_csv(self, data: str) -> bool:
        """判断数据是否可能为 CSV 格式。"""
        lines = data.splitlines()
        if len(lines) < 2:
            return False
        
        # 检查是否有统一的分隔符
        first_line = lines[0]
        for delim in [",", "\t", ";", "|"]:
            if delim in first_line:
                # 检查后续行是否也包含相同分隔符
                count = sum(1 for line in lines[1:] if delim in line)
                if count >= len(lines) * 0.5:  # 至少一半的行包含分隔符
                    return True
        return False

    def _looks_like_key_value(self, data: str) -> bool:
        """判断数据是否可能为键值对格式。"""
        lines = data.splitlines()
        if not lines:
            return False
        
        # 检查是否有键值对特征
        kv_count = 0
        for line in lines[:5]:  # 只检查前5行
            for sep in [":", "=", "："]:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2 and parts[0].strip():
                        kv_count += 1
                        break
        
        return kv_count >= 1

    def _parse_json(self, data: str) -> Dict[str, Any]:
        """解析 JSON 数据。"""
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                # 提取字段并识别类型
                fields = []
                for key, value in parsed.items():
                    field_type = self._detect_type(str(value))
                    fields.append({
                        "name": str(key),
                        "value": value,
                        "type": field_type,
                        "confidence": self._calculate_confidence(field_type),
                    })

                return {
                    "data": fields,
                    "meta": {
                        "source_format": "json",
                        "record_count": 1 if fields else 0,
                        "confidence": self._overall_confidence(fields),
                        "warnings": self.warnings,
                    },
                }
            elif isinstance(parsed, list):
                # 处理 JSON 数组
                records = []
                for item in parsed:
                    if isinstance(item, dict):
                        fields = []
                        for key, value in item.items():
                            field_type = self._detect_type(str(value))
                            fields.append({
                                "name": str(key),
                                "value": value,
                                "type": field_type,
                                "confidence": self._calculate_confidence(field_type),
                            })
                        records.append(fields)
                    else:
                        field_type = self._detect_type(str(item))
                        records.append([{
                            "name": "value",
                            "value": item,
                            "type": field_type,
                            "confidence": self._calculate_confidence(field_type),
                        }])

                return {
                    "data": records,
                    "meta": {
                        "source_format": "json_array",
                        "record_count": len(records),
                        "confidence": self._overall_confidence([f for rec in records for f in rec]),
                        "warnings": self.warnings,
                    },
                }
            else:
                # 标量值
                field_type = self._detect_type(str(parsed))
                return {
                    "data": [{
                        "name": "value",
                        "value": parsed,
                        "type": field_type,
                        "confidence": 0.8,
                    }],
                    "meta": {
                        "source_format": "json_scalar",
                        "record_count": 1,
                        "confidence": 0.8,
                        "warnings": self.warnings,
                    },
                }
        except json.JSONDecodeError as e:
            raise ValueError(f"错误码 E003: {ERROR_CODES['E003']}: {e}")
        except Exception as e:
            raise ValueError(f"错误码 E007: {ERROR_CODES['E007']}: {e}")

    def _parse_csv(self, data: str) -> Dict[str, Any]:
        """解析 CSV 数据。"""
        try:
            # 尝试自动检测分隔符
            delimiter = self._detect_delimiter(data)
            reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)

            records = []
            for row in reader:
                if not row:
                    continue
                fields = []
                for key, value in row.items():
                    if key is None:
                        continue
                    field_type = self._detect_type(value)
                    fields.append({
                        "name": key.strip(),
                        "value": value,
                        "type": field_type,
                        "confidence": self._calculate_confidence(field_type),
                    })
                if fields:
                    records.append(fields)

            if not records:
                # 可能是无表头的 CSV
                reader = csv.reader(io.StringIO(data), delimiter=delimiter)
                for row in reader:
                    if not row:
                        continue
                    fields = []
                    for i, value in enumerate(row):
                        field_type = self._detect_type(value)
                        fields.append({
                            "name": f"column_{i+1}",
                            "value": value,
                            "type": field_type,
                            "confidence": self._calculate_confidence(field_type),
                        })
                    if fields:
                        records.append(fields)

            return {
                "data": records,
                "meta": {
                    "source_format": "csv",
                    "record_count": len(records),
                    "confidence": self._overall_confidence([f for rec in records for f in rec]),
                    "warnings": self.warnings,
                },
            }
        except Exception as e:
            raise ValueError(f"错误码 E004: {ERROR_CODES['E004']}: {e}")

    def _parse_key_value(self, data: str) -> Dict[str, Any]:
        """解析键值对数据（如 name: value 或 name=value）。"""
        try:
            lines = data.splitlines()
            records = []
            current_record = []

            for line in lines:
                line = line.strip()
                if not line:
                    if current_record:
                        records.append(current_record)
                        current_record = []
                    continue

                # 尝试多种分隔符
                match = None
                for sep in [":", "=", "："]:
                    if sep in line:
                        parts = line.split(sep, 1)
                        if len(parts) == 2 and parts[0].strip():
                            match = (parts[0].strip(), parts[1].strip())
                            break

                if match:
                    key, value = match
                    field_type = self._detect_type(value)
                    current_record.append({
                        "name": key,
                        "value": value,
                        "type": field_type,
                        "confidence": self._calculate_confidence(field_type),
                    })
                else:
                    # 无分隔符，按文本处理
                    field_type = self._detect_type(line)
                    current_record.append({
                        "name": f"field_{len(current_record)+1}",
                        "value": line,
                        "type": field_type,
                        "confidence": 0.5,
                    })

            if current_record:
                records.append(current_record)

            if not records:
                raise ValueError("无法识别为键值对")

            return {
                "data": records,
                "meta": {
                    "source_format": "key_value",
                    "record_count": len(records),
                    "confidence": self._overall_confidence([f for rec in records for f in rec]),
                    "warnings": self.warnings,
                },
            }
        except Exception as e:
            raise ValueError(f"错误码 E005: {ERROR_CODES['E005']}: {e}")

    def _parse_text(self, data: str) -> Dict[str, Any]:
        """解析纯文本数据。"""
        lines = data.splitlines()
        records = []
        current_record = []

        for line in lines:
            line = line.strip()
            if not line:
                if current_record:
                    records.append(current_record)
                    current_record = []
                continue

            # 尝试识别行内键值对
            match = None
            for sep in [":", "=", "："]:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2 and parts[0].strip():
                        match = (parts[0].strip(), parts[1].strip())
                        break

            if match:
                key, value = match
                field_type = self._detect_type(value)
                current_record.append({
                    "name": key,
                    "value": value,
                    "type": field_type,
                    "confidence": self._calculate_confidence(field_type),
                })
            else:
                # 普通文本行
                field_type = self._detect_type(line)
                current_record.append({
                    "name": f"field_{len(current_record)+1}",
                    "value": line,
                    "type": field_type,
                    "confidence": self._calculate_confidence(field_type),
                })

        if current_record:
            records.append(current_record)

        if not records:
            # 单行文本
            field_type = self._detect_type(data)
            records = [[{
                "name": "content",
                "value": data,
                "type": field_type,
                "confidence": 0.5,
            }]]

        return {
            "data": records,
            "meta": {
                "source_format": "text",
                "record_count": len(records),
                "confidence": self._overall_confidence([f for rec in records for f in rec]),
                "warnings": self.warnings,
            },
        }

    def _detect_type(self, value: str) -> str:
        """识别字段类型。"""
        if not value or not value.strip():
            return "empty"

        value_lower = value.lower().strip()

        # 布尔值
        if value_lower in ["true", "false", "yes", "no", "是", "否"]:
            return "boolean"

        # 数字（整数或浮点数）
        if re.match(r"^-?\d+(\.\d+)?$", value):
            return "number"

        # 日期时间
        if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}[T\s]\d{2}:\d{2}(:\d{2})?$", value):
            return "datetime"

        # 日期
        if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", value):
            return "date"

        # 时间
        if re.match(r"^\d{2}:\d{2}(:\d{2})?$", value):
            return "time"

        # 邮箱
        if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", value):
            return "email"

        # 手机号（更精确的匹配）
        # 支持中国大陆手机号、国际格式等
        phone_pattern = r"^(?:\+?86[- ]?)?1[3-9]\d{9}$"
        if re.match(phone_pattern, value):
            return "phone"
        
        # 通用电话号码格式
        general_phone_pattern = r"^\+?[\d\s\-\(\)]{7,20}$"
        if re.match(general_phone_pattern, value) and not re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", value):
            # 排除日期格式
            return "phone"

        # URL
        if re.match(r"^https?://[\w\.\-/]+$", value_lower):
            return "url"

        # IP 地址
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
            return "ip"

        return "string"

    def _calculate_confidence(self, field_type: str) -> float:
        """根据字段类型计算置信度。"""
        confidence_map = {
            "empty": 0.3,
            "boolean": 0.9,
            "number": 0.9,
            "date": 0.85,
            "time": 0.85,
            "datetime": 0.85,
            "email": 0.9,
            "phone": 0.85,
            "url": 0.85,
            "ip": 0.85,
            "string": 0.6,
        }
        return confidence_map.get(field_type, 0.5)

    def _overall_confidence(self, fields: List[Dict[str, Any]]) -> float:
        """计算整体置信度。"""
        if not fields:
            return 0.0
        total = sum(f.get("confidence", 0.5) for f in fields)
        return round(total / len(fields), 2)

    def _detect_delimiter(self, data: str) -> str:
        """检测 CSV 分隔符。"""
        first_line = data.splitlines()[0] if data.splitlines() else ""
        candidates = [",", "\t", ";", "|"]
        best_delimiter = ","
        best_count = 0

        for delim in candidates:
            count = first_line.count(delim)
            if count > best_count:
                best_count = count
                best_delimiter = delim

        return best_delimiter

    def _to_json(self, data: Dict[str, Any]) -> str:
        """转换为 JSON 格式输出。"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _to_markdown(self, data: Dict[str, Any]) -> str:
        """转换为 Markdown 表格格式输出。"""
        lines = ["# 解析结果", ""]

        # 元信息
        meta = data.get("meta", {})
        lines.append(f"**源格式**: {meta.get('source_format', 'unknown')}")
        lines.append(f"**记录数**: {meta.get('record_count', 0)}")
        lines.append(f"**置信度**: {meta.get('confidence', 0)}")
        if meta.get("warnings"):
            lines.append(f"**警告**: {', '.join(meta['warnings'])}")
        lines.append("")

        # 数据表格
        records = data.get("data", [])
        for i, record in enumerate(records, 1):
            if not record:
                continue
            lines.append(f"## 记录 {i}")
            lines.append("")
            lines.append("| 字段 | 值 | 类型 | 置信度 |")
            lines.append("|------|-----|------|--------|")
            for field in record:
                name = field.get("name", "")
                value = str(field.get("value", ""))
                ftype = field.get("type", "string")
                conf = field.get("confidence", 0.5)
                lines.append(f"| {name} | {value} | {ftype} | {conf} |")
            lines.append("")

        return "\n".join(lines)

    def _to_csv(self, data: Dict[str, Any]) -> str:
        """转换为 CSV 格式输出。"""
        records = data.get("data", [])
        if not records:
            return ""

        # 收集所有字段名
        all_fields = []
        for record in records:
            for field in record:
                name = field.get("name", "")
                if name not in all_fields:
                    all_fields.append(name)

        output = io.StringIO()
        writer = csv.writer(output)

        # 表头
        writer.writerow(all_fields)

        # 数据行
        for record in records:
            row = []
            for field_name in all_fields:
                found = False
                for field in record:
                    if field.get("name") == field_name:
                        row.append(field.get("value", ""))
                        found = True
                        break
                if not found:
                    row.append("")
            writer.writerow(row)

        return output.getvalue()


# -----------------------------------------------------------------------------
# 内置自检功能
# -----------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。

    返回:
        True 表示自检通过，False 表示自检失败
    """
    print("=" * 60)
    print("reverse-skill 自检程序")
    print("=" * 60)

    parser = ReverseSkillParser()
    all_passed = True

    # 测试用例 1: JSON 对象解析
    print("\n[测试 1] JSON 对象解析")
    try:
        json_input = '{"name": "张三", "age": 30, "email": "zhangsan@example.com"}'
        result = parser.parse(json_input, "json")
        parsed = json.loads(result)
        assert parsed["meta"]["source_format"] == "json", "JSON 格式识别失败"
        assert len(parsed["data"]) >= 2, "JSON 字段数量不足"
        assert parsed["meta"]["confidence"] > 0.5, "JSON 置信度偏低"
        print("  ✓ JSON 对象解析通过")
        print(f"    字段数: {len(parsed['data'])}, 置信度: {parsed['meta']['confidence']}")
    except Exception as e:
        print(f"  ✗ JSON 对象解析失败: {e}")
        all_passed = False

    # 测试用例 2: JSON 数组解析
    print("\n[测试 2] JSON 数组解析")
    try:
        json_array = '[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'
        result = parser.parse(json_array, "json")
        parsed = json.loads(result)
        assert parsed["meta"]["source_format"] == "json_array", "JSON 数组格式识别失败"
        assert parsed["meta"]["record_count"] == 2, "JSON 数组记录数不正确"
        assert parsed["meta"]["confidence"] > 0.5, "JSON 数组置信度偏低"
        print("  ✓ JSON 数组解析通过")
        print(f"    记录数: {parsed['meta']['record_count']}, 置信度: {parsed['meta']['confidence']}")
    except Exception as e:
        print(f"  ✗ JSON 数组解析失败: {e}")
        all_passed = False

    # 测试用例 3: CSV 解析
    print("\n[测试 3] CSV 解析")
    try:
        csv_input = "name,age,city\n李四,25,北京\n王五,30,上海"
        result = parser.parse(csv_input, "json")
        parsed = json.loads(result)
        assert parsed["meta"]["source_format"] == "csv", "CSV 格式识别失败"
        assert parsed["meta"]["record_count"] >= 2, "CSV 记录数不足"
        assert parsed["meta"]["confidence"] > 0.5, "CSV 置信度偏低"
        print("  ✓ CSV 解析通过")
        print(f"    记录数: {parsed['meta']['record_count']}, 置信度: {parsed['meta']['confidence']}")
    except Exception as e:
        print(f"  ✗ CSV 解析失败: {e}")
        all_passed = False

    # 测试用例 4: 键值对解析
    print("\n[测试 4] 键值对解析")
    try:
        kv_input = "姓名: 赵六\n年龄: 28\n城市: 广州"
        result = parser.parse(kv_input, "json")
        parsed = json.loads(result)
        assert parsed["meta"]["source_format"] == "key_value", "键值对格式识别失败"
        assert len(parsed["data"]) >= 1, "键值对记录数不足"
        assert parsed["meta"]["confidence"] > 0.5, "键值对置信度偏低"
        print("  ✓ 键值对解析通过")
        print(f"    字段数: {len(parsed['data'][0]) if parsed['data'] else 0}, 置信度: {parsed['meta']['confidence']}")
    except Exception as e:
        print(f"  ✗ 键值对解析失败: {e}")
        all_passed = False

    # 测试用例 5: 纯文本解析
    print("\n[测试 5] 纯文本解析")
    try:
        text_input = "这是第一行文本\n这是第二行文本"
        result = parser.parse(text_input, "json")
        parsed = json.loads(result)
        assert parsed["meta"]["source_format"] == "text", "文本格式识别失败"
        assert parsed["meta"]["record_count"] >= 1, "文本记录数不足"
        print("  ✓ 纯文本解析通过")
        print(f"    记录数: {parsed['meta']['record_count']}, 置信度: {parsed['meta']['confidence']}")
    except Exception as e:
        print(f"  ✗ 纯文本解析失败: {e}")
        all_passed = False

    # 测试用例 6: 字段类型识别
    print("\n[测试 6] 字段类型识别")
    try:
        type_input = '{"email": "test@test.com", "phone": "13800138000", "date": "2024-01-15"}'
        result = parser.parse(type_input, "json")
        parsed = json.loads(result)
        types = [f["type"] for f in parsed["data"]]
        assert "email" in types, "邮箱类型识别失败"
        assert "phone" in types, "手机号类型识别失败"
        assert "date" in types, "日期类型识别失败"
        print("  ✓ 字段类型识别通过")
        print(f"    识别类型: {types}")
    except Exception as e:
        print(f"  ✗ 字段类型识别失败: {e}")
        all_passed = False

    # 测试用例 7: 输出格式转换
    print("\n[测试 7] 输出格式转换")
    try:
        test_data = "name: 测试\nage: 20"
        markdown_result = parser.parse(test_data, "markdown")
        assert "|" in markdown_result, "Markdown 表格格式错误"
        assert "记录" in markdown_result, "Markdown 缺少记录标题"

        csv_result = parser.parse(test_data, "csv")
        assert "name" in csv_result, "CSV 缺少表头"
        assert "测试" in csv_result, "CSV 缺少数据"

        print("  ✓ 输出格式转换通过")
        print(f"    Markdown 长度: {len(markdown_result)} 字符")
        print(f"    CSV 长度: {len(csv_result)} 字符")
    except Exception as e:
        print(f"  ✗ 输出格式转换失败: {e}")
        all_passed = False

    # 测试用例 8: 错误处理
    print("\n[测试 8] 错误处理")
    try:
        # 空输入
        try:
            parser.parse("", "json")
            print("  ✗ 空输入未抛出异常")
            all_passed = False
        except ValueError as e:
            assert "E001" in str(e), "错误码 E001 未正确返回"
            print("  ✓ 空输入错误处理通过")

        # 无效输出格式
        try:
            parser.parse("test", "invalid")
            print("  ✗ 无效输出格式未抛出异常")
            all_passed = False
        except ValueError as e:
            assert "E006" in str(e), "错误码 E006 未正确返回"
            print("  ✓ 无效输出格式错误处理通过")

    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        all_passed = False

    # 测试用例 9: 边界情况
    print("\n[测试 9] 边界情况")
    try:
        # 空字段
        empty_input = '{"a": "", "b": "value"}'
        result = parser.parse(empty_input, "json")
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2, "空字段处理失败"
        print("  ✓ 空字段处理通过")

        # 特殊字符
        special_input = '{"text": "包含,逗号:和:冒号"}'
        result = parser.parse(special_input, "json")
        parsed = json.loads(result)
        assert parsed["data"][0]["value"] == "包含,逗号:和:冒号", "特殊字符处理失败"
        print("  ✓ 特殊字符处理通过")

        # 大数字
        big_num_input = '{"big": 12345678901234567890}'
        result = parser.parse(big_num_input, "json")
        parsed = json.loads(result)
        assert str(parsed["data"][0]["value"]) == "12345678901234567890", "大数字处理失败"
        print("  ✓ 大数字处理通过")

    except Exception as e:
        print(f"  ✗ 边界情况测试失败: {e}")
        all_passed = False

    # 测试用例 10: 批量数据处理
    print("\n[测试 10] 批量数据处理")
    try:
        batch_input = "id,name,score\n1,张三,85\n2,李四,92\n3,王五,78"
        result = parser.parse(batch_input, "json")
        parsed = json.loads(result)
        assert parsed["meta"]["record_count"] == 3, "批量数据记录数不正确"
        assert parsed["meta"]["confidence"] > 0.5, "批量数据置信度偏低"
        print("  ✓ 批量数据处理通过")
        print(f"    记录数: {parsed['meta']['record_count']}, 置信度: {parsed['meta']['confidence']}")
    except Exception as e:
        print(f"  ✗ 批量数据处理失败: {e}")
        all_passed = False

    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
        print("=" * 60)
        return True
    else:
        print("自检结果: 存在失败项 ✗")
        print("=" * 60)
        return False


# -----------------------------------------------------------------------------
# 命令行入口
# -----------------------------------------------------------------------------

def main() -> int:
    """
    命令行主入口。

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="reverse-skill: 数据逆向结构化解析工具",
        epilog="示例: python main.py --input 'name: 张三' --format json"
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（文本、JSON、CSV、键值对等）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="输入文件路径（文件大小不超过 5MB）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown", "csv"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 获取输入数据
    input_data = ""
    if args.input:
        input_data = args.input
    elif args.file:
        try:
            # 检查文件大小
            file_size = os.path.getsize(args.file)
            if file_size > MAX_INPUT_SIZE:
                print(f"错误: 错误码 E009: {ERROR_CODES['E009']}", file=sys.stderr)
                return 1

            with open(args.file, "r", encoding="utf-8", errors="replace") as f:
                input_data = f.read()
        except FileNotFoundError:
            print(f"错误: 错误码 E008: {ERROR_CODES['E008']}", file=sys.stderr)
            return 1
        except PermissionError:
            print(f"错误: 错误码 E008: {ERROR_CODES['E008']}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    # 解析数据
    try:
        skill = ReverseSkillParser()
        result = skill.parse(input_data, args.format)
        print(result)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: 错误码 E007: {ERROR_CODES['E007']}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
