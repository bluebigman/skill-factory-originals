#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

一个完全独立、全新实现的脚本，依据功能规格构建。
仅使用 Python 标准库，无任何第三方依赖。

功能概要：
- 将用户提供的数据（文本/文件路径/URL字符串）解析为结构化字段。
- 根据输入内容生成结构化的 SQL 查询类型定义（模拟 Bun.sql 的 Types generator）。
- 支持置信度评估与错误码体系（E001-E010）。
- 提供 --selftest 参数，使用内置硬编码样例数据离线自检核心逻辑。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（依据规格 E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入。",
    "E007": "文件读取失败，请检查路径或权限。",
    "E008": "JSON 解析失败，请检查格式。",
    "E009": "输出写入失败，请检查目标路径。",
    "E010": "参数错误，请检查命令行参数。",
}


@dataclass
class ProcessingResult:
    """处理结果的数据结构。"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心逻辑：解析、结构化、置信度评估、输出生成
# ---------------------------------------------------------------------------
class SQLTypeGenerator:
    """将输入内容转换为 SQL 查询类型定义的核心处理器。"""

    # 常见 SQL 类型映射（用于推断字段类型）
    SQL_TYPE_MAP = {
        "int": "integer",
        "integer": "integer",
        "bigint": "bigint",
        "text": "text",
        "varchar": "varchar",
        "boolean": "boolean",
        "bool": "boolean",
        "timestamp": "timestamp",
        "date": "date",
        "float": "double precision",
        "double": "double precision",
        "json": "jsonb",
        "uuid": "uuid",
    }

    def __init__(self) -> None:
        """初始化处理器。"""
        self._field_counter = 0

    def process(self, raw_input: str) -> ProcessingResult:
        """
        主处理入口。

        参数:
            raw_input: 用户提供的输入（文本、文件路径或 URL 字符串）。

        返回:
            ProcessingResult 对象，包含成功状态、结果数据、错误信息、置信度。
        """
        # 1. 输入为空检查
        if raw_input is None or not raw_input.strip():
            return ProcessingResult(
                success=False,
                error_code="E001",
                error_message=ERROR_CODES["E001"],
            )

        # 2. 判断输入类型并提取内容
        content, source_type, warnings = self._extract_content(raw_input)
        if content is None:
            return ProcessingResult(
                success=False,
                error_code="E003",
                error_message=ERROR_CODES["E003"],
            )

        # 3. 解析内容为结构化字段
        fields, parse_warnings, parse_ok = self._parse_content(content)
        if not parse_ok:
            return ProcessingResult(
                success=False,
                error_code="E003",
                error_message=ERROR_CODES["E003"],
            )
        warnings.extend(parse_warnings)

        # 4. 评估置信度
        confidence = self._evaluate_confidence(fields, source_type)

        # 5. 生成输出
        output = self._generate_output(fields, source_type, confidence)

        # 6. 构建最终结果
        result_data = {
            "source_type": source_type,
            "fields": fields,
            "sql_type_definitions": output,
            "confidence": confidence,
            "warnings": warnings,
        }

        return ProcessingResult(
            success=True,
            data=result_data,
            confidence=confidence,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _extract_content(self, raw_input: str) -> Tuple[Optional[str], str, List[str]]:
        """
        从输入中提取实际内容。

        返回:
            (内容, 来源类型, 警告列表)
            来源类型: 'text' | 'file' | 'url'
        """
        warnings: List[str] = []
        trimmed = raw_input.strip()

        # 判断是否为文件路径（存在且可读）
        if os.path.isfile(trimmed):
            try:
                with open(trimmed, "r", encoding="utf-8") as f:
                    content = f.read()
                return content, "file", warnings
            except Exception:
                # 文件读取失败，但继续尝试其他方式
                warnings.append("文件读取失败，尝试作为文本处理。")

        # 判断是否为 URL（简单正则匹配）
        url_pattern = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
        if url_pattern.match(trimmed):
            # 根据规格，不访问网络，仅返回提示
            warnings.append("URL 输入：不访问网络，将 URL 作为文本处理。")
            return trimmed, "url", warnings

        # 默认作为文本处理
        return trimmed, "text", warnings

    def _parse_content(self, content: str) -> Tuple[List[Dict[str, Any]], List[str], bool]:
        """
        解析内容为结构化字段列表。

        支持两种格式：
        1. JSON 格式：包含字段定义
        2. 简单文本格式：每行一个字段，格式为 "名称:类型" 或 "名称"

        返回:
            (字段列表, 警告列表, 是否成功)
        """
        warnings: List[str] = []
        fields: List[Dict[str, Any]] = []

        # 尝试 JSON 解析
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "fields" in parsed:
                # 标准 JSON 格式
                raw_fields = parsed["fields"]
                for item in raw_fields:
                    if isinstance(item, dict):
                        field_info = self._normalize_field(item)
                        if field_info:
                            fields.append(field_info)
                    else:
                        warnings.append(f"忽略非字典字段定义: {item}")
                return fields, warnings, True
            elif isinstance(parsed, list):
                # JSON 数组格式
                for item in parsed:
                    if isinstance(item, dict):
                        field_info = self._normalize_field(item)
                        if field_info:
                            fields.append(field_info)
                    else:
                        warnings.append(f"忽略非字典字段定义: {item}")
                return fields, warnings, True
            else:
                warnings.append("JSON 格式不符合预期，尝试文本解析。")
        except json.JSONDecodeError:
            warnings.append("JSON 解析失败，尝试文本解析。")

        # 文本格式解析：每行一个字段
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 支持 "名称:类型" 或 "名称" 格式
            if ":" in line:
                name, ftype = line.split(":", 1)
                name = name.strip()
                ftype = ftype.strip()
            else:
                name = line
                ftype = "text"  # 默认类型

            if not name:
                continue

            field_info = self._normalize_field({"name": name, "type": ftype})
            if field_info:
                fields.append(field_info)

        if not fields:
            return [], ["未提取到任何字段"], False

        return fields, warnings, True

    def _normalize_field(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        规范化单个字段定义。

        参数:
            item: 字段字典，包含 'name' 和 'type' 键。

        返回:
            规范化后的字段字典，或 None 如果无效。
        """
        name = item.get("name", "")
        if not name:
            return None

        # 清理名称，转为 snake_case
        name = self._to_snake_case(str(name))

        # 获取类型并映射
        raw_type = item.get("type", "text")
        sql_type = self.SQL_TYPE_MAP.get(str(raw_type).lower(), str(raw_type))

        # 获取描述（可选）
        description = item.get("description", "")

        # 获取是否可空（可选）
        nullable = item.get("nullable", True)

        # 获取默认值（可选）
        default_value = item.get("default", None)

        return {
            "name": name,
            "type": sql_type,
            "description": description,
            "nullable": nullable,
            "default": default_value,
        }

    def _to_snake_case(self, name: str) -> str:
        """将字段名转换为 snake_case。"""
        # 处理驼峰命名
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
        # 处理空格和特殊字符
        s3 = re.sub(r"[^a-zA-Z0-9]+", "_", s2)
        # 转为小写并清理
        return s3.strip("_").lower()

    def _evaluate_confidence(self, fields: List[Dict[str, Any]], source_type: str) -> float:
        """
        根据字段数量和来源类型评估置信度。

        规则（宽松估计）：
        - 字段数 >= 5: 高置信度
        - 字段数 >= 3: 中等置信度
        - 字段数 < 3: 低置信度
        - 来源为 'file' 或 'text' 时置信度略高
        """
        base_confidence = 0.0

        if len(fields) >= 5:
            base_confidence = 0.9
        elif len(fields) >= 3:
            base_confidence = 0.8
        elif len(fields) >= 1:
            base_confidence = 0.6
        else:
            base_confidence = 0.3

        # 来源类型调整
        if source_type in ("file", "text"):
            base_confidence += 0.05
        elif source_type == "url":
            base_confidence -= 0.1

        # 限制范围 [0, 1]
        return max(0.0, min(1.0, base_confidence))

    def _generate_output(
        self,
        fields: List[Dict[str, Any]],
        source_type: str,
        confidence: float,
    ) -> str:
        """
        生成 SQL 类型定义输出。

        返回:
            格式化的 SQL 类型定义字符串。
        """
        lines: List[str] = []
        lines.append("-- 生成的 SQL 类型定义")
        lines.append(f"-- 来源类型: {source_type}")
        lines.append(f"-- 置信度: {confidence:.0%}")
        lines.append("")

        # 生成 CREATE TYPE 语句
        type_name = "generated_type"
        lines.append(f"CREATE TYPE {type_name} AS (")
        for i, field in enumerate(fields):
            field_def = f"    {field['name']} {field['type']}"
            if not field["nullable"]:
                field_def += " NOT NULL"
            if field["default"] is not None:
                field_def += f" DEFAULT {field['default']}"
            if i < len(fields) - 1:
                field_def += ","
            lines.append(field_def)
        lines.append(");")
        lines.append("")

        # 生成注释
        lines.append("-- 字段说明:")
        for field in fields:
            if field["description"]:
                lines.append(f"-- {field['name']}: {field['description']}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    运行内置硬编码样例数据的离线自检。

    返回:
        0 表示全部通过，1 表示有失败。
    """
    print("=" * 60)
    print("开始离线自检 (--selftest)")
    print("=" * 60)

    generator = SQLTypeGenerator()
    failures = 0

    # ------------------------------------------------------------------
    # 测试用例 1: 标准 JSON 输入（字段较多，高置信度）
    # ------------------------------------------------------------------
    print("\n[测试 1] 标准 JSON 输入")
    json_input = json.dumps({
        "fields": [
            {"name": "user_id", "type": "integer", "nullable": False, "description": "用户ID"},
            {"name": "username", "type": "varchar", "nullable": False},
            {"name": "email", "type": "varchar"},
            {"name": "created_at", "type": "timestamp"},
            {"name": "is_active", "type": "boolean"},
        ]
    })
    result = generator.process(json_input)
    assert result.success, f"测试 1 失败: 期望成功，但得到错误 {result.error_code}"
    assert result.data is not None, "测试 1 失败: 数据为空"
    assert len(result.data["fields"]) == 5, f"测试 1 失败: 字段数应为 5，实际 {len(result.data['fields'])}"
    assert result.confidence >= 0.8, f"测试 1 失败: 置信度应 >= 0.8，实际 {result.confidence}"
    print(f"  通过 (字段数: {len(result.data['fields'])}, 置信度: {result.confidence:.0%})")

    # ------------------------------------------------------------------
    # 测试用例 2: 文本格式输入（每行一个字段）
    # ------------------------------------------------------------------
    print("\n[测试 2] 文本格式输入")
    text_input = "id:int\nname:text\ncreated_at:timestamp"
    result = generator.process(text_input)
    assert result.success, f"测试 2 失败: 期望成功，但得到错误 {result.error_code}"
    assert result.data is not None, "测试 2 失败: 数据为空"
    assert len(result.data["fields"]) == 3, f"测试 2 失败: 字段数应为 3，实际 {len(result.data['fields'])}"
    assert result.data["fields"][0]["name"] == "id", "测试 2 失败: 第一个字段名应为 id"
    assert result.data["fields"][0]["type"] == "integer", "测试 2 失败: 类型映射错误"
    print(f"  通过 (字段数: {len(result.data['fields'])}, 置信度: {result.confidence:.0%})")

    # ------------------------------------------------------------------
    # 测试用例 3: 空输入（应返回 E001）
    # ------------------------------------------------------------------
    print("\n[测试 3] 空输入")
    result = generator.process("")
    assert not result.success, "测试 3 失败: 期望失败但成功"
    assert result.error_code == "E001", f"测试 3 失败: 错误码应为 E001，实际 {result.error_code}"
    print(f"  通过 (错误码: {result.error_code})")

    # ------------------------------------------------------------------
    # 测试用例 4: 单字段输入（低置信度）
    # ------------------------------------------------------------------
    print("\n[测试 4] 单字段输入")
    result = generator.process("name")
    assert result.success, f"测试 4 失败: 期望成功，但得到错误 {result.error_code}"
    assert result.data is not None, "测试 4 失败: 数据为空"
    assert len(result.data["fields"]) == 1, "测试 4 失败: 字段数应为 1"
    assert result.confidence < 0.9, f"测试 4 失败: 置信度应 < 0.9，实际 {result.confidence}"
    print(f"  通过 (字段数: {len(result.data['fields'])}, 置信度: {result.confidence:.0%})")

    # ------------------------------------------------------------------
    # 测试用例 5: 文件输入（使用临时文件）
    # ------------------------------------------------------------------
    print("\n[测试 5] 文件输入")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"fields": [{"name": "a", "type": "int"}, {"name": "b", "type": "text"}]}, f)
        temp_filename = f.name
    try:
        result = generator.process(temp_filename)
        assert result.success, f"测试 5 失败: 期望成功，但得到错误 {result.error_code}"
        assert result.data is not None, "测试 5 失败: 数据为空"
        assert len(result.data["fields"]) == 2, "测试 5 失败: 字段数应为 2"
        assert result.data["source_type"] == "file", "测试 5 失败: 来源类型应为 file"
        print(f"  通过 (来源: {result.data['source_type']}, 字段数: {len(result.data['fields'])})")
    finally:
        os.unlink(temp_filename)

    # ------------------------------------------------------------------
    # 测试用例 6: URL 输入（不访问网络）
    # ------------------------------------------------------------------
    print("\n[测试 6] URL 输入")
    result = generator.process("https://example.com/data.json")
    assert result.success, f"测试 6 失败: 期望成功，但得到错误 {result.error_code}"
    assert result.data is not None, "测试 6 失败: 数据为空"
    assert result.data["source_type"] == "url", "测试 6 失败: 来源类型应为 url"
    print(f"  通过 (来源: {result.data['source_type']})")

    # ------------------------------------------------------------------
    # 测试用例 7: 字段名驼峰转换
    # ------------------------------------------------------------------
    print("\n[测试 7] 驼峰命名转换")
    result = generator.process('{"fields": [{"name": "userName", "type": "text"}]}')
    assert result.success, f"测试 7 失败: 期望成功"
    assert result.data is not None, "测试 7 失败: 数据为空"
    field_name = result.data["fields"][0]["name"]
    assert field_name == "user_name", f"测试 7 失败: 应转换为 user_name，实际 {field_name}"
    print(f"  通过 (转换结果: {field_name})")

    # ------------------------------------------------------------------
    # 测试用例 8: 批量处理（多个输入）
    # ------------------------------------------------------------------
    print("\n[测试 8] 批量处理")
    inputs = [
        '{"fields": [{"name": "x", "type": "int"}]}',
        "y:text\nz:boolean",
    ]
    for i, inp in enumerate(inputs):
        result = generator.process(inp)
        assert result.success, f"测试 8 失败: 第 {i+1} 个输入处理失败"
        assert result.data is not None, f"测试 8 失败: 第 {i+1} 个输入数据为空"
    print(f"  通过 (处理了 {len(inputs)} 个输入)")

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检全部通过 ✅")
        return 0
    else:
        print(f"自检失败 {failures} 项 ❌")
        return 1


def process_input(input_text: str) -> int:
    """
    处理用户输入并输出结果。

    参数:
        input_text: 用户提供的输入。

    返回:
        0 表示成功，非 0 表示失败。
    """
    generator = SQLTypeGenerator()
    result = generator.process(input_text)

    if not result.success:
        print(f"错误 [{result.error_code}]: {result.error_message}", file=sys.stderr)
        return 1

    # 输出结果
    assert result.data is not None, "处理成功但数据为空"
    print(json.dumps(result.data, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    """
    主入口函数。

    返回:
        进程退出码。
    """
    parser = argparse.ArgumentParser(
        description="SQL查询类型生成器 (bun-sqlgen)",
        epilog="示例: python main.py '{\"fields\": [{\"name\": \"id\", \"type\": \"int\"}]}'",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="待处理的内容（文本、文件路径或 URL）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="bun-sqlgen 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理输入
    if args.input is None:
        print(f"错误 [E010]: {ERROR_CODES['E010']}", file=sys.stderr)
        print("请提供输入内容，或使用 --selftest 运行自检。", file=sys.stderr)
        return 1

    return process_input(args.input)


if __name__ == "__main__":
    sys.exit(main())
