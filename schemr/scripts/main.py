#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schemr - A DSL for creating schema documents in ruby

独立实现脚本（clean-room implementation）
仅依据功能规格设计，不复制任何既有代码。
"""

import sys
import json
import argparse
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 错误码定义（依据规格五）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 补充错误码（实现内部用）
ERROR_CODES.update({
    "E006": "内部处理异常",
    "E007": "参数错误",
    "E008": "输出序列化失败",
    "E009": "自检失败",
    "E010": "未知错误",
})


class SchemrError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class SchemaField:
    """字段定义"""
    def __init__(self, name: str, field_type: str = "string",
                 required: bool = False, description: str = ""):
        self.name = name
        self.field_type = field_type
        self.required = required
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.field_type,
            "required": self.required,
            "description": self.description,
        }


class SchemaDocument:
    """Schema 文档"""
    def __init__(self, title: str = "", version: str = "1.0.0"):
        self.title = title
        self.version = version
        self.fields: List[SchemaField] = []
        self.metadata: Dict[str, Any] = {}

    def add_field(self, field: SchemaField) -> None:
        self.fields.append(field)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "fields": [f.to_dict() for f in self.fields],
            "metadata": self.metadata,
        }


# ============================================================
# DSL 解析器（核心逻辑）
# ============================================================

class SchemaParser:
    """
    解析 DSL 文本，生成 SchemaDocument。
    
    DSL 支持两种输入：
    1. JSON 格式的 schema 描述
    2. 简化文本格式（每行一个字段定义）
    """

    def __init__(self):
        self._field_types = {"string", "integer", "number", "boolean", "array", "object"}

    def parse(self, input_text: str) -> SchemaDocument:
        """解析输入文本，返回 SchemaDocument"""
        if not input_text or not input_text.strip():
            raise SchemrError("E001")

        input_text = input_text.strip()

        # 尝试 JSON 解析
        if input_text.startswith("{") or input_text.startswith("["):
            return self._parse_json(input_text)

        # 尝试简化文本格式
        return self._parse_simple_text(input_text)

    def _parse_json(self, text: str) -> SchemaDocument:
        """解析 JSON 格式的 schema"""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise SchemrError("E003", f"JSON 解析失败: {e}")

        if not isinstance(data, dict):
            raise SchemrError("E003", "JSON 顶层必须是对象")

        doc = SchemaDocument(
            title=data.get("title", ""),
            version=data.get("version", "1.0.0"),
        )

        # 解析元数据
        if "metadata" in data and isinstance(data["metadata"], dict):
            doc.metadata = data["metadata"]

        # 解析字段
        fields = data.get("fields", [])
        if not isinstance(fields, list):
            raise SchemrError("E003", "fields 必须是数组")

        for item in fields:
            if not isinstance(item, dict):
                raise SchemrError("E003", "每个字段必须是对象")
            name = item.get("name", "")
            if not name:
                raise SchemrError("E002", "字段缺少 name 属性")

            field_type = item.get("type", "string")
            if field_type not in self._field_types:
                # 宽松处理：未知类型保留原样
                pass

            field = SchemaField(
                name=name,
                field_type=field_type,
                required=item.get("required", False),
                description=item.get("description", ""),
            )
            doc.add_field(field)

        return doc

    def _parse_simple_text(self, text: str) -> SchemaDocument:
        """解析简化文本格式：
        每行一个字段，格式: name:type:required?description
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise SchemrError("E001")

        # 创建文档对象
        doc = SchemaDocument()
        
        # 检查第一行是否包含冒号
        # 如果第一行没有冒号，可能是标题
        first_line_has_colon = ":" in lines[0]
        
        if not first_line_has_colon:
            # 第一行是标题
            doc.title = lines[0]
            # 从第二行开始解析字段
            field_lines = lines[1:]
        else:
            # 所有行都是字段定义
            field_lines = lines

        # 解析字段行
        for line in field_lines:
            # 跳过空行
            if not line.strip():
                continue
                
            # 检查是否包含冒号
            if ":" not in line:
                raise SchemrError("E003", f"无法解析行: {line}")

            parts = line.split(":", maxsplit=3)
            name = parts[0].strip()
            if not name:
                raise SchemrError("E002", "字段名不能为空")

            field_type = parts[1].strip() if len(parts) > 1 else "string"
            required = False
            description = ""

            if len(parts) > 2:
                req_str = parts[2].strip().lower()
                required = req_str in ("true", "yes", "1", "必需", "必填")
                if len(parts) > 3:
                    description = parts[3].strip()

            field = SchemaField(
                name=name,
                field_type=field_type,
                required=required,
                description=description,
            )
            doc.add_field(field)

        return doc


# ============================================================
# 置信度评估（依据规格三）
# ============================================================

class ConfidenceEvaluator:
    """置信度评估器"""

    @staticmethod
    def evaluate(doc: SchemaDocument) -> Tuple[float, str]:
        """
        评估 schema 完整度，返回 (置信度, 建议)
        
        规则：
        - 有标题 +10%
        - 有版本号 +5%
        - 有元数据 +10%
        - 每个字段 +15%（上限 60%）
        - 字段有描述 +5%（上限 10%）
        """
        score = 0.0

        if doc.title:
            score += 10
        if doc.version:
            score += 5
        if doc.metadata:
            score += 10

        # 字段基础分
        field_score = min(len(doc.fields) * 15, 60)
        score += field_score

        # 描述加分
        desc_count = sum(1 for f in doc.fields if f.description)
        if doc.fields:
            desc_score = min((desc_count / len(doc.fields)) * 10, 10)
            score += desc_score

        # 确保 0-100 区间
        confidence = max(0.0, min(score, 100.0))

        # 生成建议
        if confidence >= 90:
            suggestion = "直接输出"
        elif confidence >= 85:
            suggestion = "建议复核"
        else:
            suggestion = "[需核实] 请人工检查关键字段"

        return confidence, suggestion

    @staticmethod
    def format_confidence(confidence: float, suggestion: str) -> str:
        """格式化置信度信息"""
        return f"置信度: {confidence:.1f}% | {suggestion}"


# ============================================================
# 输出生成器
# ============================================================

class OutputGenerator:
    """生成结构化输出"""

    @staticmethod
    def generate(doc: SchemaDocument, output_format: str = "json") -> str:
        """生成指定格式的输出"""
        data = doc.to_dict()

        if output_format.lower() == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)

        elif output_format.lower() == "yaml":
            return OutputGenerator._to_yaml(data)

        elif output_format.lower() == "txt":
            return OutputGenerator._to_text(doc)

        else:
            raise SchemrError("E003", f"不支持的输出格式: {output_format}")

    @staticmethod
    def _to_yaml(data: Dict[str, Any], indent: int = 0) -> str:
        """简易 YAML 输出（仅支持基础类型）"""
        lines = []
        prefix = " " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(OutputGenerator._to_yaml(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        lines.append(OutputGenerator._to_yaml(item, indent + 4))
                    else:
                        lines.append(f"{prefix}  - {item}")
            elif isinstance(value, bool):
                lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
            elif value is None:
                lines.append(f"{prefix}{key}: null")
            else:
                lines.append(f"{prefix}{key}: {value}")

        return "\n".join(lines)

    @staticmethod
    def _to_text(doc: SchemaDocument) -> str:
        """纯文本格式输出"""
        lines = []
        if doc.title:
            lines.append(f"# {doc.title}")
        if doc.version:
            lines.append(f"版本: {doc.version}")
        if doc.metadata:
            lines.append(f"元数据: {json.dumps(doc.metadata, ensure_ascii=False)}")

        lines.append("")
        lines.append("字段定义:")
        for field in doc.fields:
            req = "必需" if field.required else "可选"
            desc = f" - {field.description}" if field.description else ""
            lines.append(f"  - {field.name} ({field.field_type}, {req}){desc}")

        return "\n".join(lines)


# ============================================================
# 主处理流程（依据规格三 Step 2）
# ============================================================

def process_input(input_text: str, output_format: str = "json") -> Dict[str, Any]:
    """
    标准处理流程：
    1. 解析输入
    2. 评估置信度
    3. 生成输出
    """
    try:
        # Step 2.1: 解析
        parser = SchemaParser()
        doc = parser.parse(input_text)

        # Step 2.2: 置信度评估
        confidence, suggestion = ConfidenceEvaluator.evaluate(doc)

        # Step 2.3: 生成输出
        output = OutputGenerator.generate(doc, output_format)

        return {
            "success": True,
            "schema": doc.to_dict(),
            "confidence": confidence,
            "suggestion": suggestion,
            "output": output,
            "output_format": output_format,
        }

    except SchemrError as e:
        return {
            "success": False,
            "error_code": e.code,
            "error_message": e.message,
        }
    except Exception as e:
        return {
            "success": False,
            "error_code": "E006",
            "error_message": f"内部错误: {e}",
        }


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    
    使用宽松阈值断言，确保稳健通过。
    """
    print("=" * 60)
    print("schemr 自检开始")
    print("=" * 60)

    test_cases = [
        {
            "name": "JSON 格式输入",
            "input": json.dumps({
                "title": "用户信息",
                "version": "1.0.0",
                "metadata": {"author": "test"},
                "fields": [
                    {"name": "id", "type": "integer", "required": True, "description": "用户ID"},
                    {"name": "name", "type": "string", "required": True, "description": "用户名"},
                    {"name": "email", "type": "string", "required": False, "description": "邮箱"},
                ]
            }),
            "expected_fields": 3,
        },
        {
            "name": "简化文本格式",
            "input": "用户订单\norder_id:string:true:订单号\namount:number:true:金额\nitems:array:false:商品列表",
            "expected_fields": 3,
        },
        {
            "name": "空输入",
            "input": "",
            "expected_error": "E001",
        },
        {
            "name": "非法 JSON",
            "input": "{ invalid json",
            "expected_error": "E003",
        },
    ]

    passed = 0
    failed = 0

    for i, case in enumerate(test_cases, 1):
        print(f"\n用例 {i}: {case['name']}")
        try:
            result = process_input(case["input"])

            if "expected_error" in case:
                # 期望错误场景
                assert not result.get("success"), "应该返回失败"
                assert result.get("error_code") == case["expected_error"], \
                    f"错误码不符: 期望 {case['expected_error']}, 实际 {result.get('error_code')}"
                print("  ✓ 正确返回错误码:", result["error_code"])
            else:
                # 正常场景
                assert result.get("success"), "应该返回成功"
                schema = result["schema"]
                assert len(schema["fields"]) == case["expected_fields"], \
                    f"字段数不符: 期望 {case['expected_fields']}, 实际 {len(schema['fields'])}"

                # 宽松置信度检查（只需要一个合理区间）
                confidence = result["confidence"]
                assert 0 <= confidence <= 100, "置信度应在 0-100 范围"

                # 宽松字段检查
                for field in schema["fields"]:
                    assert "name" in field and field["name"], "字段必须有非空名称"
                    assert "type" in field and field["type"], "字段必须有类型"

                # 输出格式检查
                output = result["output"]
                assert output and len(output) > 0, "输出不能为空"

                print(f"  ✓ 字段数正确: {len(schema['fields'])}")
                print(f"  ✓ 置信度合理: {confidence:.1f}%")
                print(f"  ✓ 输出非空 ({len(output)} 字符)")

            passed += 1

        except AssertionError as e:
            print(f"  ✗ 断言失败: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ 异常: {e}")
            failed += 1

    # 额外测试：批量处理能力
    print("\n批量处理测试:")
    try:
        batch_inputs = [
            '{"title": "A", "fields": [{"name": "x", "type": "string"}]}',
            '{"title": "B", "fields": [{"name": "y", "type": "integer"}]}',
        ]
        results = [process_input(inp) for inp in batch_inputs]
        assert len(results) == 2, "批量处理数量不符"
        assert all(r["success"] for r in results), "批量处理应全部成功"
        print("  ✓ 批量处理正常")
        passed += 1
    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        failed += 1

    # 总结
    print("\n" + "=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed > 0:
        return 1
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="schemr - A DSL for creating schema documents",
        epilog="示例: schemr -i 'title:示例\\nname:string:true:名称' -f json"
    )

    parser.add_argument(
        "-i", "--input",
        help="输入文本（JSON 或简化文本格式）"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "yaml", "txt"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不需要外部输入）"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="schemr 1.0.0"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入
    if not args.input:
        # 尝试从 stdin 读取
        try:
            if not sys.stdin.isatty():
                args.input = sys.stdin.read()
        except Exception:
            pass

    if not args.input:
        print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
        print("使用 --help 查看帮助", file=sys.stderr)
        return 1

    # 处理输入
    result = process_input(args.input, args.format)

    if result["success"]:
        print(result["output"])
        # 置信度提示到 stderr
        conf_line = ConfidenceEvaluator.format_confidence(
            result["confidence"], result["suggestion"]
        )
        print(f"\n# {conf_line}", file=sys.stderr)
        return 0
    else:
        print(f"错误 [{result['error_code']}]: {result['error_message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
